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
        self.geometry("780x760")
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
        # ---------- Header ----------
        header = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=0)
        header.pack(fill="x", side="top")
        h_box = ctk.CTkFrame(header, fg_color="transparent")
        h_box.pack(fill="x", padx=22, pady=(14, 12))
        top = ctk.CTkFrame(h_box, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text="จัดการ Profile และ MT5", font=_font(18, "bold"),
                     text_color=COLOR_GOLD_PRIMARY).pack(side="left")
        self._pill(top, f"หน้าต่างนี้ · {self._active_prof}", COLOR_GOLD_PRIMARY, COLOR_GOLD_BG).pack(side="right")
        rules = ctk.CTkFrame(h_box, fg_color="transparent")
        rules.pack(fill="x", pady=(8, 0))
        for txt in ("1 Profile = 1 หน้าต่างบอท", "แยกข้อมูลและไม้กันเด็ดขาด", "1 บัญชี MT5 บอททำงานได้ 1 หน้าต่าง"):
            chip = ctk.CTkFrame(rules, fg_color=COLOR_BTN_DARK, corner_radius=10)
            chip.pack(side="left", padx=(0, 6))
            ctk.CTkLabel(chip, text=f"✓  {txt}", font=_font(11), text_color=COLOR_TEXT_MUTED, height=22).pack(padx=10)
        ctk.CTkFrame(self, height=1, fg_color=COLOR_CARD_BORDER, corner_radius=0).pack(fill="x")

        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=14, pady=12)

        # ---------- การ์ด 1: Profile ทั้งหมด ----------
        card_list = self._card(content, "Profile ทั้งหมด", "กด เปิด เพื่อเริ่มบอทอีกหน้าต่างสำหรับ Profile นั้น")
        self.list_box = ctk.CTkFrame(card_list, fg_color="transparent")
        self.list_box.pack(fill="x", padx=16, pady=(0, 4))
        self.issue_box = ctk.CTkFrame(card_list, fg_color="transparent")
        self.issue_box.pack(fill="x", padx=16)
        self._build_profile_rows()

        ctk.CTkFrame(card_list, height=1, fg_color=COLOR_CARD_BORDER, corner_radius=0).pack(fill="x", padx=16, pady=(10, 0))
        new_row = ctk.CTkFrame(card_list, fg_color="transparent")
        new_row.pack(fill="x", padx=16, pady=(10, 14))
        ctk.CTkLabel(new_row, text="+ Profile ใหม่", font=_font(12, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        self.entry_new_prof = ctk.CTkEntry(new_row, placeholder_text="ชื่อภาษาอังกฤษ เช่น XM2, Cent", width=200, height=30,
                                           font=_font(12), fg_color=COLOR_BG_DARK, border_color=COLOR_CARD_BORDER)
        self.entry_new_prof.pack(side="left", padx=10)
        self.entry_new_prof.bind("<Return>", lambda e: self._create_and_launch_profile())
        self._btn(new_row, "สร้างและเปิด", self._create_and_launch_profile, "gold", 110).pack(side="left")
        ctk.CTkButton(new_row, text="สร้างไฟล์เปิดด่วน (.bat) ›", command=self._generate_desktop_shortcuts, width=10, height=30,
                      fg_color="transparent", hover_color=COLOR_BTN_DARK, text_color=COLOR_CYAN_ACCENT,
                      font=_font(11, "bold")).pack(side="right")

        # ---------- การ์ด 2: ตั้งค่า Profile ของหน้าต่างนี้ (Magic + MT5 + ที่เก็บข้อมูล) ----------
        card_me = self._card(content, f"ตั้งค่า Profile นี้  ·  {self._active_prof}")
        body = ctk.CTkFrame(card_me, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=(4, 14))

        # (ก) บัญชี MT5 ที่ต่ออยู่ตอนนี้
        acc = self._current_account_text()
        acc_row = ctk.CTkFrame(body, fg_color=COLOR_BG_DARK, corner_radius=10)
        acc_row.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(acc_row, text="บัญชี MT5 ตอนนี้", font=_font(11, "bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(12, 8), pady=8)
        ctk.CTkLabel(acc_row, text=acc[0], font=_font(12, "bold"), text_color=acc[1]).pack(side="left", pady=8)

        # (ข) Magic Number
        self._section(body, "Magic Number", "บอทของหน้าต่างนี้ดูแลเฉพาะไม้ที่มี Magic นี้ และไม้ที่เข้าเอง (Magic 0)")
        m_box = ctk.CTkFrame(body, fg_color="transparent")
        m_box.pack(fill="x", pady=(4, 12))
        self.entry_magic = ctk.CTkEntry(m_box, width=130, height=32, font=_font(14, "bold"),
                                        fg_color=COLOR_BG_DARK, border_color=COLOR_CARD_BORDER, text_color=COLOR_GOLD_PRIMARY)
        self.entry_magic.insert(0, str(get_profile_magic_number()))
        self.entry_magic.pack(side="left")
        self._btn(m_box, "บันทึก", self._save_magic, "gold", 80).pack(side="left", padx=(8, 4))
        self._btn(m_box, "ใช้เลขที่ไม่ซ้ำ", self._fill_unique_magic, "dark", 120).pack(side="left", padx=4)
        self.lbl_magic_state = ctk.CTkLabel(m_box, text="", font=_font(11, "bold"))
        self.lbl_magic_state.pack(side="left", padx=8)

        # (ค) MetaTrader 5 ของ Profile นี้ — ตัวเลือกเป็นแถว (ชื่อ + path จาง)
        self._section(body, "MetaTrader 5 ที่ใช้", "Profile ต่างกันควรใช้ MT5 คนละตัว (คนละบัญชี)")
        self.term_choice_var = tk.StringVar(value="")
        cfg_norm = os.path.normcase(os.path.normpath(self._current_term_path)) if self._current_term_path else ""
        opts = ctk.CTkFrame(body, fg_color="transparent")
        opts.pack(fill="x", pady=(4, 0))

        def option(title, sub, value):
            row = ctk.CTkFrame(opts, fg_color=COLOR_BG_DARK, corner_radius=8)
            row.pack(fill="x", pady=2)
            rb = ctk.CTkRadioButton(row, text=title, variable=self.term_choice_var, value=value, font=_font(12, "bold"),
                                    text_color=COLOR_TEXT_PRIMARY, fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_PRIMARY,
                                    border_color="#4B5263", radiobutton_width=16, radiobutton_height=16,
                                    command=self._on_term_choice)
            rb.pack(side="left", padx=(12, 8), pady=8)
            if sub:
                ctk.CTkLabel(row, text=sub, font=_font(10), text_color="#6B7385", anchor="w").pack(side="left", padx=(0, 10))
            for w in (row,):
                w.bind("<Button-1>", lambda e, v=value: (self.term_choice_var.set(v), self._on_term_choice()))

        option("อัตโนมัติ", "ใช้ MT5 ที่ Python เชื่อมได้ (ตัวที่เปิดอยู่)", "")
        matched = False
        for term in self._installed_terminals:
            if cfg_norm and os.path.normcase(os.path.normpath(term["path"])) == cfg_norm:
                matched = True
                self.term_choice_var.set(term["path"])
            option(term["name"], self._short_path(term["path"]), term["path"])
        option("กำหนดเอง", "เลือกไฟล์ terminal64.exe", "CUSTOM")

        self.custom_row = ctk.CTkFrame(body, fg_color="transparent")
        self.entry_custom_path = ctk.CTkEntry(self.custom_row, placeholder_text="ไฟล์ terminal64.exe", height=30, font=_font(12),
                                              fg_color=COLOR_BG_DARK, border_color=COLOR_CARD_BORDER)
        self.entry_custom_path.pack(side="left", fill="x", expand=True, padx=(28, 8))
        self._btn(self.custom_row, "เลือกไฟล์", self._browse_custom_terminal, "dark", 90).pack(side="right")
        if cfg_norm and not matched:
            self.term_choice_var.set("CUSTOM")
            self.entry_custom_path.insert(0, self._current_term_path or "")

        self.save_row = ctk.CTkFrame(body, fg_color="transparent")
        self.save_row.pack(fill="x", pady=(10, 12))
        self._btn(self.save_row, "บันทึกและทดสอบเชื่อมต่อ", self._save_and_test_terminal, "gold", 190).pack(side="left")
        self.lbl_term_status = ctk.CTkLabel(self.save_row, text="", font=_font(12, "bold"), text_color=COLOR_TEXT_MUTED)
        self.lbl_term_status.pack(side="left", padx=12)
        self._on_term_choice()

        # (ง) ที่เก็บข้อมูล
        p_dir = get_active_profile_dir()
        data_row = ctk.CTkFrame(body, fg_color="transparent")
        data_row.pack(fill="x")
        ctk.CTkLabel(data_row, text="ที่เก็บข้อมูล", font=_font(11, "bold"), text_color=COLOR_TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(data_row, text=self._short_path(p_dir, 52), font=_font(11), text_color="#6B7385").pack(side="left", padx=10)
        ctk.CTkButton(data_row, text="เปิดโฟลเดอร์ ›", width=10, height=26, fg_color="transparent", hover_color=COLOR_BTN_DARK,
                      text_color=COLOR_CYAN_ACCENT, font=_font(11, "bold"),
                      command=lambda: os.startfile(p_dir) if sys.platform == "win32" else None).pack(side="right")
        self._update_magic_state()

    def _section(self, parent, title, sub):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text=title, font=_font(13, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(row, text=f"  ·  {sub}", font=_font(11), text_color=COLOR_TEXT_MUTED).pack(side="left")

    @staticmethod
    def _short_path(path, limit=60):
        path = str(path or "")
        return path if len(path) <= limit else "…" + path[-(limit - 1):]

    def _current_account_text(self):
        """บัญชีที่ Python เชื่อม MT5 อยู่ตอนนี้ (หน้าต่างนี้)"""
        try:
            import MetaTrader5 as mt5
            a = mt5.account_info()
            if a is not None:
                return (f"#{a.login}  ·  {a.server}", COLOR_SUCCESS_GREEN)
        except Exception:
            pass
        return ("ยังไม่ได้เชื่อมต่อ", COLOR_TEXT_MUTED)

    def _on_term_choice(self):
        """แสดงช่องกรอก path เฉพาะเมื่อเลือก กำหนดเอง"""
        if self.term_choice_var.get() == "CUSTOM":
            if not self.custom_row.winfo_ismapped():
                self.custom_row.pack(fill="x", pady=(4, 0), before=self.save_row)
        elif self.custom_row.winfo_ismapped():
            self.custom_row.pack_forget()

    def _unique_magic(self):
        """Magic ที่ไม่ซ้ำกับ Profile อื่น — เริ่มจากค่าคำนวณตามชื่อ Profile"""
        used = {inf["magic"] for n, (_s, _b, inf) in self._rows.items() if n != self._active_prof}
        used |= getattr(self, "_hidden_magics", set())
        m = 888000 + sum(ord(c) for c in self._active_prof) % 900
        while m in used or m == 0:
            m += 1
        return m

    def _fill_unique_magic(self):
        self.entry_magic.delete(0, "end")
        self.entry_magic.insert(0, str(self._unique_magic()))
        self._update_magic_state(pending=True)

    def _update_magic_state(self, pending=False):
        if not hasattr(self, "lbl_magic_state"):
            return
        cur = get_profile_magic_number()
        others = [n for n, (_s, _b, inf) in self._rows.items() if n != self._active_prof and inf["magic"] == cur]
        if pending:
            self.lbl_magic_state.configure(text="กด บันทึก เพื่อใช้เลขนี้", text_color=COLOR_GOLD_PRIMARY)
        elif others:
            self.lbl_magic_state.configure(text=f"! ซ้ำกับ {', '.join(others)}", text_color="#FBBF24")
        else:
            self.lbl_magic_state.configure(text="✓ ไม่ซ้ำ", text_color=COLOR_SUCCESS_GREEN)

    def _build_profile_rows(self):
        for w in self.list_box.winfo_children():
            w.destroy()
        for w in self.issue_box.winfo_children():
            w.destroy()
        self._rows = {}
        names = list_profiles()
        infos = {n: _profile_info(n) for n in names}
        # Profile ที่ใช้ Magic เดียวกับ default = ซ้ำกับ default → ซ่อนจากรายการ (ผู้ใช้สั่ง 14 ต.ค. 2026)
        # ยกเว้นตอนที่ Profile นั้นเปิดอยู่ / เป็นหน้าต่างนี้ (ต้องเห็นสถานะจริง)
        hidden = []
        if "default" in infos:
            dm = infos["default"]["magic"]
            hidden = [n for n in names if n != "default" and infos[n]["magic"] == dm
                      and n != self._active_prof and not instance_guard.is_profile_running(n)]
        self._hidden_magics = {infos[n]["magic"] for n in hidden}
        names = [n for n in names if n not in hidden]
        infos = {n: infos[n] for n in names}
        by_magic, by_term = {}, {}
        for n, inf in infos.items():
            by_magic.setdefault(inf["magic"], []).append(n)
            key = os.path.normcase(os.path.normpath(inf["terminal"])) if inf["terminal"] else ""
            by_term.setdefault(key, []).append(n)

        # ตารางเดียว (หัวตาราง + แถวอยู่ใน grid เดียวกัน คอลัมน์จึงตรงกัน)
        table = ctk.CTkFrame(self.list_box, fg_color="transparent")
        table.pack(fill="x")
        for col, w in enumerate((1, 1, 0, 0, 0)):
            table.grid_columnconfigure(col, weight=w)
        for col, txt in enumerate(("Profile", "MT5", "Magic", "สถานะ", "")):
            ctk.CTkLabel(table, text=txt, anchor="w", font=_font(11, "bold"), text_color=COLOR_TEXT_MUTED, height=20).grid(
                row=0, column=col, padx=(12 if col == 0 else 8, 8), pady=(0, 2), sticky="w")
        for i, name in enumerate(names, start=1):
            info = infos[name]
            dup_magic = len(by_magic[info["magic"]]) > 1
            tkey = os.path.normcase(os.path.normpath(info["terminal"])) if info["terminal"] else ""
            dup_term = len(by_term[tkey]) > 1
            bg = COLOR_ROW_ALT if i % 2 else COLOR_CARD_BG
            ctk.CTkFrame(table, fg_color=bg, corner_radius=8, height=40).grid(row=i, column=0, columnspan=5, sticky="nsew", pady=1)
            is_me = name == self._active_prof
            ctk.CTkLabel(table, text=name, anchor="w", font=_font(13, "bold"), fg_color=bg,
                         text_color=COLOR_GOLD_PRIMARY if is_me else COLOR_TEXT_PRIMARY).grid(row=i, column=0, padx=(12, 8), sticky="w")
            ctk.CTkLabel(table, text=_terminal_label(info["terminal"], self._installed_terminals) + ("  !" if dup_term else ""),
                         anchor="w", font=_font(12), fg_color=bg,
                         text_color="#FBBF24" if dup_term else COLOR_TEXT_PRIMARY).grid(row=i, column=1, padx=8, sticky="w")
            ctk.CTkLabel(table, text=str(info["magic"]) + ("  !" if dup_magic else ""), anchor="w", font=_font(12, "bold"), fg_color=bg,
                         text_color="#FBBF24" if dup_magic else COLOR_TEXT_MUTED).grid(row=i, column=2, padx=8, sticky="w")
            status = ctk.CTkLabel(table, text="", anchor="center", font=_font(11, "bold"), corner_radius=8, height=22, width=104, bg_color=bg)
            status.grid(row=i, column=3, padx=8, sticky="w")
            btn = self._btn(table, "เปิด", lambda n=name: self._spawn_instance(n), "green", 76)
            btn.configure(bg_color=bg)
            btn.grid(row=i, column=4, padx=(8, 10), pady=5, sticky="e")
            self._rows[name] = (status, btn, info)

        # ปัญหาที่ควรแก้ (สีเหลือง = ควรแก้ ไม่ใช่ error) — บอกชัดว่าซ้ำอะไร กับใคร และแก้ที่ไหน
        issues = [f"Magic {m} ใช้ร่วมกัน: {', '.join(ns)}" for m, ns in by_magic.items() if len(ns) > 1]
        issues += [f"MT5 {'อัตโนมัติ' if not k else _terminal_label(infos[ns[0]]['terminal'], self._installed_terminals)} ใช้ร่วมกัน: {', '.join(ns)}"
                   for k, ns in by_term.items() if len(ns) > 1]
        if issues:
            box = ctk.CTkFrame(self.issue_box, fg_color="#2A2110", corner_radius=8, border_width=1, border_color="#6B4E12")
            box.pack(fill="x", pady=(8, 0))
            ctk.CTkLabel(box, text="!  ควรแก้: " + "  ·  ".join(issues), font=_font(11, "bold"), text_color="#FBBF24",
                         anchor="w", justify="left", wraplength=640).pack(fill="x", padx=12, pady=(8, 2))
            ctk.CTkLabel(box, text="ใช้ร่วมกันได้ถ้าแต่ละ Profile ต่อคนละบัญชี MT5 — แต่ถ้าเปิดบนบัญชีเดียวกัน บอทจะดูแลไม้ทับกัน · "
                                   "แก้ที่ ตั้งค่า Profile นี้ ด้านล่าง (ปุ่ม ใช้เลขที่ไม่ซ้ำ) ในหน้าต่างของ Profile นั้น",
                         font=_font(11), text_color=COLOR_TEXT_MUTED, anchor="w", justify="left", wraplength=640).pack(fill="x", padx=12, pady=(0, 8))
        self._update_magic_state()

    def _refresh_status(self):
        """สถานะเปิดอยู่/ปิดอยู่ของทุก Profile (ตรวจ Mutex ทุก 2 วิ)"""
        if not self.winfo_exists():
            return
        for name, (status, btn, _info) in self._rows.items():
            if name == self._active_prof:
                status.configure(text="● หน้าต่างนี้", text_color=COLOR_GOLD_PRIMARY, fg_color=COLOR_GOLD_BG)
                btn.configure(state="disabled", text="เปิดอยู่", fg_color=COLOR_BTN_DARK)
            elif instance_guard.is_profile_running(name):
                status.configure(text="● เปิดอยู่", text_color=COLOR_SUCCESS_GREEN, fg_color="#0F2A20")
                btn.configure(state="disabled", text="เปิดอยู่", fg_color=COLOR_BTN_DARK)
            else:
                status.configure(text="ปิดอยู่", text_color=COLOR_TEXT_MUTED, fg_color=COLOR_BTN_DARK)
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
        old = get_profile_magic_number()
        if m != old:
            try:
                import MetaTrader5 as mt5
                n_open = sum(1 for x in (mt5.positions_get() or ()) if x.magic == old)
            except Exception:
                n_open = 0
            if n_open and not self._show("askyesno", "มีไม้เปิดอยู่ด้วย Magic เดิม",
                                         f"มี {n_open} ไม้ที่เปิดด้วย Magic {old} — หลังเปลี่ยน บอทจะไม่ดูแลไม้เหล่านี้ต่อ (เลื่อน SL / ปิดตามแผน)\n"
                                         "แนะนำให้รอปิดไม้ก่อนแล้วค่อยเปลี่ยน · ยืนยันเปลี่ยนตอนนี้?"):
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
