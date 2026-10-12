"""
หน้าต่างจัดการ Profile และเชื่อมต่อ MT5 Terminal สำหรับระบบ Multi-Instance (Gold Bot 24)
- Profile ปัจจุบัน: ที่เก็บข้อมูล + Magic Number
- MT5 Terminal ประจำ Profile (FBS / XM / กำหนดเอง)
- รายการ Profile ทั้งหมด พร้อมสถานะเปิดอยู่/ปิดอยู่ และปุ่มเปิด — กันเปิดซ้ำ (12 ต.ค. 2026):
  Profile ที่เปิดอยู่แล้วกดเปิดไม่ได้ · เตือนเมื่อ Profile ที่จะเปิดใช้ MT5 ตัวเดียวกับ Profile ที่เปิดอยู่ (บัญชีซ้ำ)
กล่องข้อความใช้ StyledMessage ของโปรแกรม (ห้ามใช้ messagebox ของ Windows) · ห้ามใช้อีโมจี (Tk แสดงเป็นกล่อง)
"""
import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

import app_fonts
import instance_guard
from app_paths import (
    DATA_DIR,
    get_active_profile,
    get_active_profile_dir,
    list_profiles,
    set_active_profile,
)
from mt5_terminal_manager import (
    DEFAULT_MAGIC_NUMBER,
    get_configured_terminal_path,
    get_profile_magic_number,
    initialize_mt5,
    scan_installed_terminals,
    set_configured_terminal_path,
    set_profile_magic_number,
)

# ธีมเดียวกับหน้าต่างหลัก (gui_app.py)
COLOR_BG_DARK = "#0A0B0F"
COLOR_CARD_BG = "#14171E"
COLOR_CARD_BORDER = "#252A35"
COLOR_ROW_ALT = "#171B23"
COLOR_GOLD_PRIMARY = "#F2C14E"
COLOR_GOLD_WARM = "#E0A92B"
COLOR_GOLD_DARK = "#9A6B12"
COLOR_GOLD_BG = "#221B0D"
COLOR_TEXT_PRIMARY = "#ECEEF3"
COLOR_TEXT_MUTED = "#A3ABBA"
COLOR_SUCCESS_GREEN = "#34D399"
COLOR_DANGER_RED = "#F87171"
COLOR_CYAN_ACCENT = "#60A5FA"
COLOR_BTN_DARK = "#1F2430"
COLOR_BTN_DARK_HOVER = "#2A3040"


def _font(size, weight="normal"):
    return ctk.CTkFont(family=app_fonts.UI, size=size, weight=weight)


def _profile_dir(name: str) -> str:
    return DATA_DIR if name == "default" else os.path.join(DATA_DIR, "profiles", name)


def _profile_info(name: str) -> dict:
    """Magic / MT5 ของ Profile ใดก็ได้ (อ่าน bot_settings.json ของ Profile นั้นตรง ๆ — ไม่สลับ Profile ของหน้าต่างนี้)"""
    data = {}
    try:
        with open(os.path.join(_profile_dir(name), "bot_settings.json"), encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        pass
    magic = data.get("magic_number")
    if not (isinstance(magic, int) and magic > 0):
        magic = DEFAULT_MAGIC_NUMBER if name == "default" else 888000 + sum(ord(c) for c in name) % 900
    term = data.get("terminal_path") or ""
    return {"magic": magic, "terminal": term}


def _terminal_label(path: str, installed: list) -> str:
    if not path:
        return "อัตโนมัติ"
    norm = os.path.normcase(os.path.normpath(path))
    for t in installed:
        if os.path.normcase(os.path.normpath(t["path"])) == norm:
            return t["name"]
    return os.path.basename(os.path.dirname(path)) or path


class ProfileManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        # กล่องข้อความธีมโปรแกรม (gui_app.messagebox = _StyledMessagebox) — import ตรงไม่ได้ (วนกัน)
        self.msg = getattr(sys.modules.get(type(parent).__module__), "messagebox", None)

        self.title("จัดการ Profile และ MT5")
        self.geometry("760x700")
        self.minsize(680, 560)
        self.configure(fg_color=COLOR_BG_DARK)
        # ไม่ใช้ grab_set — ไม่งั้นกล่องข้อความของโปรแกรม (ลูกของหน้าต่างหลัก) กดไม่ได้

        self._active_prof = get_active_profile()
        self._installed_terminals = scan_installed_terminals()
        self._current_term_path = get_configured_terminal_path()
        self._rows = {}

        self._build_ui()
        self._refresh_status()

    # ---------- กล่องข้อความ ----------
    def _show(self, kind, title, message):
        if self.msg is not None:
            return getattr(self.msg, kind)(title, message)
        print(f"[{title}] {message}")
        return True

    # ---------- ส่วนประกอบ ----------
    def _card(self, parent, title, subtitle=None):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        card.pack(fill="x", pady=(0, 12), padx=2)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(14, 2))
        ctk.CTkFrame(head, width=4, height=18, corner_radius=2, fg_color=COLOR_GOLD_PRIMARY).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(head, text=title, font=_font(15, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        if subtitle:
            ctk.CTkLabel(card, text=subtitle, font=_font(12), text_color=COLOR_TEXT_MUTED,
                         justify="left", anchor="w", wraplength=640).pack(fill="x", padx=30, pady=(0, 8))
        return card

    def _pill(self, parent, text, fg, bg):
        return ctk.CTkLabel(parent, text=f" {text} ", font=_font(11, "bold"), text_color=fg,
                            fg_color=bg, corner_radius=8, height=22)

    def _btn(self, parent, text, cmd, kind="dark", width=120):
        styles = {
            "gold": (COLOR_GOLD_WARM, COLOR_GOLD_PRIMARY, "#1A1406"),
            "green": ("#059669", "#10B981", "#FFFFFF"),
            "dark": (COLOR_BTN_DARK, COLOR_BTN_DARK_HOVER, COLOR_TEXT_PRIMARY),
        }
        fg, hover, tc = styles[kind]
        return ctk.CTkButton(parent, text=text, command=cmd, width=width, height=30, corner_radius=8,
                             font=_font(12, "bold"), fg_color=fg, hover_color=hover, text_color=tc,
                             text_color_disabled="#5B6270")

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=0)
        header.pack(fill="x", side="top")
        h_box = ctk.CTkFrame(header, fg_color="transparent")
        h_box.pack(fill="x", padx=22, pady=14)
        top = ctk.CTkFrame(h_box, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text="จัดการ Profile และ MT5", font=_font(18, "bold"),
                     text_color=COLOR_GOLD_PRIMARY).pack(side="left")
        self._pill(top, f"หน้าต่างนี้: {self._active_prof}", COLOR_GOLD_PRIMARY, COLOR_GOLD_BG).pack(side="right")
        ctk.CTkLabel(h_box, text="เปิดบอทหลายบัญชี / หลายโบรกเกอร์พร้อมกัน แต่ละ Profile แยกข้อมูลและไม้กันเด็ดขาด · 1 Profile เปิดได้ 1 หน้าต่าง · 1 บัญชี MT5 ให้บอททำงานได้ 1 หน้าต่าง",
                     font=_font(12), text_color=COLOR_TEXT_MUTED, justify="left", anchor="w",
                     wraplength=700).pack(fill="x", pady=(4, 0))
        ctk.CTkFrame(self, height=1, fg_color=COLOR_CARD_BORDER, corner_radius=0).pack(fill="x")

        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=14, pady=12)

        # ---------- การ์ด 1: Profile ทั้งหมด ----------
        card_list = self._card(content, "Profile ทั้งหมด",
                               "กดเปิดเพื่อเริ่มโปรแกรมอีกหน้าต่างสำหรับ Profile นั้น · Profile ที่เปิดอยู่แล้วเปิดซ้ำไม่ได้")
        self.list_box = ctk.CTkFrame(card_list, fg_color="transparent")
        self.list_box.pack(fill="x", padx=16, pady=(0, 6))
        self._build_profile_rows()

        new_row = ctk.CTkFrame(card_list, fg_color="transparent")
        new_row.pack(fill="x", padx=16, pady=(6, 14))
        ctk.CTkLabel(new_row, text="สร้าง Profile ใหม่", font=_font(12, "bold"),
                     text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_new_prof = ctk.CTkEntry(new_row, placeholder_text="เช่น XM, FBS2, Cent", width=180, height=30,
                                           font=_font(12), fg_color=COLOR_BG_DARK, border_color=COLOR_CARD_BORDER)
        self.entry_new_prof.pack(side="left", padx=10)
        self._btn(new_row, "+ สร้างและเปิด", self._create_and_launch_profile, "gold", 130).pack(side="left")
        self._btn(new_row, "สร้างไฟล์เปิดด่วน (.bat)", self._generate_desktop_shortcuts, "dark", 170).pack(side="right")

        # ---------- การ์ด 2: Profile ปัจจุบัน ----------
        card_active = self._card(content, f"Profile ของหน้าต่างนี้  ·  {self._active_prof}")
        p_dir = get_active_profile_dir()
        grid = ctk.CTkFrame(card_active, fg_color="transparent")
        grid.pack(fill="x", padx=30, pady=(4, 14))
        grid.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(grid, text="ที่เก็บข้อมูล", font=_font(12, "bold"), text_color=COLOR_TEXT_MUTED).grid(row=0, column=0, sticky="w", pady=4)
        ctk.CTkLabel(grid, text=p_dir, font=_font(12), text_color=COLOR_CYAN_ACCENT, anchor="w", justify="left",
                     wraplength=420).grid(row=0, column=1, sticky="w", padx=12)
        self._btn(grid, "เปิดโฟลเดอร์", lambda: os.startfile(p_dir) if sys.platform == "win32" else None,
                  "dark", 110).grid(row=0, column=2, sticky="e")

        ctk.CTkLabel(grid, text="Magic Number", font=_font(12, "bold"), text_color=COLOR_TEXT_MUTED).grid(row=1, column=0, sticky="w", pady=4)
        m_box = ctk.CTkFrame(grid, fg_color="transparent")
        m_box.grid(row=1, column=1, columnspan=2, sticky="w", padx=12)
        self.entry_magic = ctk.CTkEntry(m_box, width=120, height=30, font=_font(13, "bold"),
                                        fg_color=COLOR_BG_DARK, border_color=COLOR_CARD_BORDER, text_color=COLOR_GOLD_PRIMARY)
        self.entry_magic.insert(0, str(get_profile_magic_number()))
        self.entry_magic.pack(side="left")
        self._btn(m_box, "บันทึก", self._save_magic, "gold", 80).pack(side="left", padx=8)
        ctk.CTkLabel(grid, text="บอทดูแลเฉพาะไม้ที่มี Magic Number นี้ และไม้ที่เข้าเอง (Magic 0) — ตั้งให้ไม่ซ้ำกับ Profile อื่น",
                     font=_font(11), text_color=COLOR_TEXT_MUTED, anchor="w", justify="left",
                     wraplength=560).grid(row=2, column=0, columnspan=3, sticky="w", pady=(2, 0))

        # ---------- การ์ด 3: MT5 Terminal ----------
        card_mt5 = self._card(content, "MetaTrader 5 ของ Profile นี้",
                              "เลือก MT5 ที่ Profile นี้ใช้ — Profile ต่างกันควรใช้ MT5 คนละตัว (คนละบัญชี) ไม่งั้นบอทจะทำงานซ้ำบนบัญชีเดียวกัน")
        self.term_choice_var = tk.StringVar(value="")
        cfg_norm = os.path.normcase(os.path.normpath(self._current_term_path)) if self._current_term_path else ""

        opts = ctk.CTkFrame(card_mt5, fg_color="transparent")
        opts.pack(fill="x", padx=30, pady=(0, 4))

        def radio(text, value):
            ctk.CTkRadioButton(opts, text=text, variable=self.term_choice_var, value=value, font=_font(12),
                               text_color=COLOR_TEXT_PRIMARY, fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_PRIMARY,
                               border_color="#4B5263").pack(anchor="w", pady=4)

        radio("อัตโนมัติ (ใช้ MT5 ที่เปิดอยู่)", "")
        matched = False
        for term in self._installed_terminals:
            if cfg_norm and os.path.normcase(os.path.normpath(term["path"])) == cfg_norm:
                matched = True
                self.term_choice_var.set(term["path"])
            radio(f"{term['name']}   ·   {term['path']}", term["path"])
        radio("กำหนดเอง", "CUSTOM")

        custom_row = ctk.CTkFrame(card_mt5, fg_color="transparent")
        custom_row.pack(fill="x", padx=56, pady=(0, 8))
        self.entry_custom_path = ctk.CTkEntry(custom_row, placeholder_text="ไฟล์ terminal64.exe", height=30, font=_font(12),
                                              fg_color=COLOR_BG_DARK, border_color=COLOR_CARD_BORDER)
        self.entry_custom_path.pack(side="left", fill="x", expand=True, padx=(0, 8))
        if cfg_norm and not matched:
            self.term_choice_var.set("CUSTOM")
            self.entry_custom_path.insert(0, self._current_term_path or "")
        self._btn(custom_row, "เลือกไฟล์", self._browse_custom_terminal, "dark", 90).pack(side="right")

        save_row = ctk.CTkFrame(card_mt5, fg_color="transparent")
        save_row.pack(fill="x", padx=30, pady=(2, 14))
        self._btn(save_row, "บันทึกและทดสอบเชื่อมต่อ", self._save_and_test_terminal, "gold", 200).pack(side="left")
        self.lbl_term_status = ctk.CTkLabel(save_row, text="", font=_font(12, "bold"), text_color=COLOR_TEXT_MUTED)
        self.lbl_term_status.pack(side="left", padx=12)

    def _build_profile_rows(self):
        for w in self.list_box.winfo_children():
            w.destroy()
        self._rows = {}
        head = ctk.CTkFrame(self.list_box, fg_color="transparent")
        head.pack(fill="x", pady=(0, 2))
        for col, (txt, w) in enumerate((("Profile", 150), ("MT5", 170), ("Magic", 90), ("สถานะ", 120), ("", 90))):
            ctk.CTkLabel(head, text=txt, width=w, anchor="w", font=_font(11, "bold"),
                         text_color=COLOR_TEXT_MUTED).grid(row=0, column=col, padx=(10 if col == 0 else 4, 4), sticky="w")
        names = list_profiles()
        infos = {n: _profile_info(n) for n in names}
        magic_count, term_count = {}, {}
        for n, inf in infos.items():
            magic_count[inf["magic"]] = magic_count.get(inf["magic"], 0) + 1
            key = os.path.normcase(os.path.normpath(inf["terminal"])) if inf["terminal"] else ""
            term_count[key] = term_count.get(key, 0) + 1
        dup_names = []
        for i, name in enumerate(names):
            info = infos[name]
            dup_magic = magic_count[info["magic"]] > 1
            tkey = os.path.normcase(os.path.normpath(info["terminal"])) if info["terminal"] else ""
            dup_term = term_count[tkey] > 1
            if dup_magic or dup_term:
                dup_names.append(name)
            row = ctk.CTkFrame(self.list_box, fg_color=COLOR_ROW_ALT if i % 2 == 0 else "transparent", corner_radius=8, height=40)
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=name, width=150, anchor="w", font=_font(13, "bold"),
                         text_color=COLOR_GOLD_PRIMARY if name == self._active_prof else COLOR_TEXT_PRIMARY
                         ).grid(row=0, column=0, padx=(10, 4), pady=6, sticky="w")
            ctk.CTkLabel(row, text=_terminal_label(info["terminal"], self._installed_terminals), width=170, anchor="w",
                         font=_font(12), text_color=COLOR_DANGER_RED if dup_term else COLOR_TEXT_PRIMARY).grid(row=0, column=1, padx=4, sticky="w")
            ctk.CTkLabel(row, text=str(info["magic"]), width=90, anchor="w", font=_font(12, "bold" if dup_magic else "normal"),
                         text_color=COLOR_DANGER_RED if dup_magic else COLOR_TEXT_MUTED).grid(row=0, column=2, padx=4, sticky="w")
            status = ctk.CTkLabel(row, text="", width=120, anchor="w", font=_font(11, "bold"), corner_radius=8, height=22)
            status.grid(row=0, column=3, padx=4, sticky="w")
            btn = self._btn(row, "เปิด", lambda n=name: self._spawn_instance(n), "green", 80)
            btn.grid(row=0, column=4, padx=(4, 8), pady=5, sticky="e")
            self._rows[name] = (status, btn, info)
        if dup_names:
            warn = ctk.CTkFrame(self.list_box, fg_color="#2A1215", corner_radius=8, border_width=1, border_color="#7F1D1D")
            warn.pack(fill="x", pady=(8, 0))
            ctk.CTkLabel(warn, text=f"✗ Profile [{', '.join(dup_names)}] ใช้ MT5 หรือ Magic Number ซ้ำกัน (ตัวสีแดง) — ถ้าเปิดพร้อมกันบนบัญชีเดียวกัน บอทจะเข้าไม้ซ้ำ · "
                                    "ระบบให้บอทเริ่มทำงานได้หน้าต่างเดียวต่อ 1 บัญชี MT5 แต่ควรแก้ให้แต่ละ Profile ใช้ MT5 และ Magic ของตัวเอง",
                         font=_font(11), text_color="#FCA5A5", justify="left", anchor="w", wraplength=640).pack(fill="x", padx=12, pady=8)

    def _refresh_status(self):
        """สถานะเปิดอยู่/ปิดอยู่ของทุก Profile (ตรวจ Mutex ทุก 2 วิ)"""
        if not self.winfo_exists():
            return
        for name, (status, btn, _info) in self._rows.items():
            if name == self._active_prof:
                status.configure(text=" ● หน้าต่างนี้ ", text_color=COLOR_GOLD_PRIMARY, fg_color=COLOR_GOLD_BG)
                btn.configure(state="disabled", text="เปิดอยู่", fg_color=COLOR_BTN_DARK)
            elif instance_guard.is_profile_running(name):
                status.configure(text=" ● เปิดอยู่ ", text_color=COLOR_SUCCESS_GREEN, fg_color="#0F2A20")
                btn.configure(state="disabled", text="เปิดอยู่", fg_color=COLOR_BTN_DARK)
            else:
                status.configure(text=" ปิดอยู่ ", text_color=COLOR_TEXT_MUTED, fg_color=COLOR_BTN_DARK)
                btn.configure(state="normal", text="เปิด", fg_color="#059669")
        self.after(2000, self._refresh_status)

    # ---------- การทำงาน ----------
    def _save_magic(self):
        val = self.entry_magic.get().strip()
        try:
            m = int(val)
            if m <= 0:
                raise ValueError
        except Exception:
            self._show("showerror", "Magic Number ไม่ถูกต้อง", "กรุณาใส่ตัวเลขจำนวนเต็มบวก\nเช่น 888999")
            return
        for name, (_s, _b, info) in self._rows.items():
            if name != self._active_prof and info["magic"] == m:
                self._show("showerror", "Magic Number ซ้ำ", f"Magic {m} ถูกใช้โดย Profile [{name}] แล้ว\nตั้งเลขอื่นเพื่อไม่ให้บอทดูแลไม้ทับกัน")
                return
        set_profile_magic_number(m)
        self._build_profile_rows()
        self._show("showinfo", "บันทึกสำเร็จ", f"บันทึก Magic Number {m} เรียบร้อยแล้ว\nProfile [{self._active_prof}]")

    def _browse_custom_terminal(self):
        f = filedialog.askopenfilename(
            parent=self,
            title="เลือกไฟล์ terminal64.exe ของ MetaTrader 5",
            filetypes=[("MT5 Terminal", "terminal64.exe;terminal.exe"), ("Program", "*.exe")],
        )
        if f:
            self.term_choice_var.set("CUSTOM")
            self.entry_custom_path.delete(0, "end")
            self.entry_custom_path.insert(0, f)

    def _save_and_test_terminal(self):
        chosen = self.term_choice_var.get()
        if chosen == "CUSTOM":
            chosen = self.entry_custom_path.get().strip()
        if chosen and not os.path.isfile(chosen):
            self._show("showerror", "ไม่พบไฟล์", f"ไม่พบไฟล์ MT5 ตามที่ระบุ\n{chosen}")
            return

        # MT5 ตัวเดียวกับ Profile อื่นที่เปิดอยู่ = บัญชีเดียวกัน → เตือนก่อน
        clash = self._running_profiles_with_terminal(chosen, exclude=self._active_prof)
        if clash and not self._show("askyesno", "MT5 ตัวนี้ถูกใช้อยู่",
                                    f"Profile [{', '.join(clash)}] ที่เปิดอยู่ใช้ MT5 ตัวนี้แล้ว ยืนยันใช้ร่วมกัน?\n"
                                    "บอทจะเริ่มทำงานได้เพียงหน้าต่างเดียวต่อ 1 บัญชี MT5"):
            return

        set_configured_terminal_path(chosen if chosen else None)
        self.lbl_term_status.configure(text="กำลังทดสอบเชื่อมต่อ…", text_color=COLOR_GOLD_PRIMARY)
        self.update_idletasks()
        if initialize_mt5(path=chosen if chosen else None):
            self.lbl_term_status.configure(text="✓ เชื่อมต่อสำเร็จ", text_color=COLOR_SUCCESS_GREEN)
            self._build_profile_rows()
            self._show("showinfo", "บันทึกสำเร็จ", f"เชื่อมต่อ MetaTrader 5 เรียบร้อยแล้ว\n{chosen or 'อัตโนมัติ (MT5 ที่เปิดอยู่)'}")
        else:
            self.lbl_term_status.configure(text="✗ เชื่อมต่อไม่สำเร็จ", text_color=COLOR_DANGER_RED)
            self._show("showwarning", "บันทึกแล้ว แต่เชื่อมต่อไม่ได้", "ยังเชื่อมต่อ MT5 ไม่ได้ในขณะนี้\nเปิด MT5 แล้วลองใหม่อีกครั้ง")

    def _running_profiles_with_terminal(self, path, exclude):
        """Profile อื่นที่กำลังเปิดอยู่และใช้ MT5 ตัวเดียวกัน (ทั้งคู่ 'อัตโนมัติ' ก็ถือว่าตัวเดียวกัน)"""
        norm = os.path.normcase(os.path.normpath(path)) if path else ""
        out = []
        for name in list_profiles():
            if name == exclude:
                continue
            running = name == self._active_prof or instance_guard.is_profile_running(name)
            if not running:
                continue
            t = _profile_info(name)["terminal"]
            if name == self._active_prof:
                t = self._current_term_path or ""
            if (os.path.normcase(os.path.normpath(t)) if t else "") == norm:
                out.append(name)
        return out

    def _create_and_launch_profile(self):
        name = self.entry_new_prof.get().strip()
        if not name:
            self._show("showwarning", "ยังไม่ได้ใส่ชื่อ", "กรุณากรอกชื่อ Profile ที่ต้องการสร้าง")
            return
        clean = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip()
        if not clean or not clean.isascii():
            self._show("showerror", "ชื่อ Profile ไม่ถูกต้อง", "ใช้ตัวอักษรภาษาอังกฤษ ตัวเลข - หรือ _ เท่านั้น")
            return
        if clean.lower() in (p.lower() for p in list_profiles()):
            self._show("showwarning", "มี Profile นี้แล้ว", f"Profile [{clean}] มีอยู่แล้ว\nกดปุ่ม \"เปิด\" ในรายการแทน")
            return
        set_active_profile(clean)            # สร้างโฟลเดอร์ของ Profile ใหม่
        set_active_profile(self._active_prof)  # แล้วสลับกลับเป็น Profile ของหน้าต่างนี้
        self.entry_new_prof.delete(0, "end")
        self._build_profile_rows()
        self._refresh_once()
        self._spawn_instance(clean)

    def _refresh_once(self):
        for name, (status, btn, _i) in self._rows.items():
            if name != self._active_prof and not instance_guard.is_profile_running(name):
                status.configure(text=" ปิดอยู่ ", text_color=COLOR_TEXT_MUTED, fg_color=COLOR_BTN_DARK)

    def _spawn_instance(self, profile_name: str):
        """เปิดโปรแกรมอีกหน้าต่างสำหรับ Profile นั้น — กันเปิดซ้ำ"""
        if profile_name == self._active_prof:
            self._show("showinfo", "เปิดอยู่แล้ว", f"Profile [{profile_name}] คือหน้าต่างนี้")
            return
        if instance_guard.is_profile_running(profile_name):
            self._show("showwarning", "เปิดอยู่แล้ว", f"Profile [{profile_name}] เปิดอยู่แล้ว\nเปิดซ้ำไม่ได้ — ใช้หน้าต่างเดิม")
            return
        info = _profile_info(profile_name)
        clash = self._running_profiles_with_terminal(info["terminal"], exclude=profile_name)
        if clash and not self._show("askyesno", "ใช้ MT5 ตัวเดียวกัน",
                                    f"Profile [{profile_name}] ใช้ MT5 ตัวเดียวกับ [{', '.join(clash)}] ที่เปิดอยู่ ยืนยันเปิด?\n"
                                    "บัญชี MT5 เดียวกันให้บอทเริ่มทำงานได้หน้าต่างเดียว — ควรตั้ง MT5 ของ Profile นี้ก่อน"):
            return
        try:
            if getattr(sys, "frozen", False):
                args = [sys.executable, "--profile", profile_name]
            else:
                script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui_app.py")
                args = [sys.executable, script, "--profile", profile_name]
            subprocess.Popen(args, close_fds=True)
            btn = self._rows.get(profile_name, (None, None))[1]
            if btn is not None:
                btn.configure(state="disabled", text="กำลังเปิด", fg_color=COLOR_BTN_DARK)
            self._show("showinfo", "กำลังเปิดหน้าต่างใหม่", f"เปิด Gold Bot 24 สำหรับ Profile [{profile_name}] เรียบร้อย\nทำงานคู่กันโดยไม่กระทบหน้าต่างนี้")
        except Exception as e:
            self._show("showerror", "เปิดโปรแกรมไม่สำเร็จ", f"เปิดหน้าต่างใหม่ไม่ได้\n{e}")

    def _generate_desktop_shortcuts(self):
        """สร้างไฟล์ .bat สำหรับดับเบิลคลิกเปิดแต่ละ Profile"""
        try:
            script_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
            created = []
            for p in list_profiles():
                bat_path = os.path.join(script_dir, f"Launch_GoldBot_{p}.bat")
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write("@echo off\n")
                    f.write(f"title Gold Bot 24 [{p}]\n")
                    f.write("cd /d \"%~dp0\"\n")
                    if getattr(sys, "frozen", False):
                        f.write(f"start \"\" \"{sys.executable}\" --profile {p}\n")
                    else:
                        f.write(f"start \"\" python gui_app.py --profile {p}\n")
                created.append(os.path.basename(bat_path))
            self._show("showinfo", "สร้างไฟล์สำเร็จ",
                       f"สร้างไฟล์เปิดด่วน {len(created)} ไฟล์เรียบร้อย\n" + " · ".join(created) + " — คัดลอกไปวางบนหน้าจอเพื่อดับเบิลคลิกเปิดแต่ละ Profile")
            if sys.platform == "win32":
                os.startfile(script_dir)
        except Exception as e:
            self._show("showerror", "สร้างไฟล์ไม่สำเร็จ", f"สร้างไฟล์เปิดด่วนไม่ได้\n{e}")
