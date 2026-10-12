"""
หน้าต่างจัดการ Profile และเชื่อมต่อ MT5 Terminal สำหรับระบบ Multi-Instance
(Gold Bot 24)
- สลับ / สร้าง Profile เพื่อรันบอทหลายบัญชีพร้อมกันบนเครื่องเดียวกัน
- กำหนด MT5 Terminal Path (เช่น FBS MetaTrader 5, XM Global MT5) ประจำ Profile
- กำหนด Magic Number ประจำ Profile ไม่ให้ออเดอร์ชนกัน
- เปิดหน้าต่างบอทใหม่ (New Instance) สำหรับ Profile อื่นได้ในคลิกเดียว
"""
import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

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

# ธีมสีสอดคล้องกับ GoldBot24
COLOR_BG_DARK = "#0D1117"
COLOR_CARD_BG = "#161B22"
COLOR_CARD_BORDER = "#30363D"
COLOR_GOLD_PRIMARY = "#F59E0B"
COLOR_GOLD_WARM = "#D97706"
COLOR_GOLD_DARK = "#B45309"
COLOR_TEXT_PRIMARY = "#F0F6FC"
COLOR_TEXT_MUTED = "#8B949E"
COLOR_SUCCESS_GREEN = "#10B981"
COLOR_DANGER_RED = "#EF4444"


class ProfileManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("⚙️ จัดการ Profile & MT5 Terminal (Multi-Instance)")
        self.geometry("720x680")
        self.minsize(640, 600)
        self.configure(fg_color=COLOR_BG_DARK)

        # จัดให้อยู่กลางจอ parent
        try:
            self.transient(parent)
            self.grab_set()
        except Exception:
            pass

        self._active_prof = get_active_profile()
        self._installed_terminals = scan_installed_terminals()
        self._current_term_path = get_configured_terminal_path()

        self._build_ui()

    def _build_ui(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=0, height=65)
        header.pack(fill="x", side="top")
        h_box = ctk.CTkFrame(header, fg_color="transparent")
        h_box.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            h_box,
            text="⚙️ จัดการ Profile & MT5 Terminal (Multi-Instance)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_GOLD_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            h_box,
            text="รันบอทหลายบัญชี / หลายโบรกเกอร์ (เช่น FBS + XM) พร้อมกันในเครื่องเดียว ข้อมูลและออเดอร์แยกกัน 100%",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        # Scrollable content
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=16, pady=12)

        # -------------------------------------------------------------
        # การ์ดที่ 1: Profile ปัจจุบันของหน้าต่างนี้
        # -------------------------------------------------------------
        card_active = ctk.CTkFrame(content, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        card_active.pack(fill="x", pady=(0, 12), padx=4)

        c1_head = ctk.CTkFrame(card_active, fg_color="transparent")
        c1_head.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            c1_head,
            text=f"📌 Profile ปัจจุบัน:  [{self._active_prof}]",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        ).pack(side="left")

        # โฟลเดอร์เก็บข้อมูล
        p_dir = get_active_profile_dir()
        dir_row = ctk.CTkFrame(card_active, fg_color="transparent")
        dir_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(dir_row, text="📁 ที่เก็บข้อมูล:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left")
        lbl_dir = ctk.CTkLabel(dir_row, text=p_dir, font=ctk.CTkFont(size=11), text_color="#93C5FD", wraplength=480, justify="left")
        lbl_dir.pack(side="left", padx=8)
        ctk.CTkButton(
            dir_row, text="เปิดโฟลเดอร์", width=80, height=24, font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#1F2937", hover_color="#374151", text_color=COLOR_TEXT_PRIMARY,
            command=lambda: os.startfile(p_dir) if sys.platform == "win32" else None,
        ).pack(side="right")

        # Magic Number
        magic_row = ctk.CTkFrame(card_active, fg_color="transparent")
        magic_row.pack(fill="x", padx=14, pady=(4, 12))
        ctk.CTkLabel(magic_row, text="🔢 Magic Number:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_magic = ctk.CTkEntry(magic_row, width=120, height=26, font=ctk.CTkFont(size=12))
        self.entry_magic.insert(0, str(get_profile_magic_number()))
        self.entry_magic.pack(side="left", padx=8)
        ctk.CTkButton(
            magic_row, text="บันทึก Magic", width=90, height=24, font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK, text_color="#1A1406",
            command=self._save_magic,
        ).pack(side="left")
        ctk.CTkLabel(
            magic_row, text="(บอทจะคุมเฉพาะไม้ที่มี Magic Number นี้ ไม่กวนไม้อื่น)",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED,
        ).pack(side="left", padx=8)

        # -------------------------------------------------------------
        # การ์ดที่ 2: ผูก MT5 Terminal ประจำ Profile
        # -------------------------------------------------------------
        card_mt5 = ctk.CTkFrame(content, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        card_mt5.pack(fill="x", pady=(0, 12), padx=4)

        c2_head = ctk.CTkFrame(card_mt5, fg_color="transparent")
        c2_head.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            c2_head,
            text="💻 MetaTrader 5 Terminal ประจำ Profile นี้",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            card_mt5,
            text="เลือกว่าต้องการให้ Profile นี้เชื่อมต่อและสั่งการ MT5 ตัวไหนเป็นหลัก:",
            font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=14, pady=(0, 8))

        # ตัวเลือก MT5
        self.term_choice_var = tk.StringVar()
        cfg_path_norm = os.path.normcase(os.path.normpath(self._current_term_path)) if self._current_term_path else ""

        # Default / System Active
        r_auto = ctk.CTkRadioButton(
            card_mt5,
            text="⚡ ค่าเริ่มต้น (Auto Detect / ใช้ตัวที่เปิดอยู่)",
            variable=self.term_choice_var,
            value="",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_PRIMARY,
        )
        r_auto.pack(anchor="w", padx=20, pady=3)

        matched_any = False
        for term in self._installed_terminals:
            t_path = term["path"]
            t_norm = os.path.normcase(os.path.normpath(t_path))
            is_cur = (t_norm == cfg_path_norm) if cfg_path_norm else False
            if is_cur:
                matched_any = True
                self.term_choice_var.set(t_path)

            disp_text = f"🏢 {term['name']}  ({term['path']})"
            rb = ctk.CTkRadioButton(
                card_mt5,
                text=disp_text,
                variable=self.term_choice_var,
                value=t_path,
                font=ctk.CTkFont(size=12),
                text_color=COLOR_TEXT_PRIMARY,
            )
            rb.pack(anchor="w", padx=20, pady=3)

        # Custom Path
        self.r_custom = ctk.CTkRadioButton(
            card_mt5,
            text="📂 กำหนด Path อื่นด้วยตนเอง (Browse...)",
            variable=self.term_choice_var,
            value="CUSTOM",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.r_custom.pack(anchor="w", padx=20, pady=3)

        custom_row = ctk.CTkFrame(card_mt5, fg_color="transparent")
        custom_row.pack(fill="x", padx=40, pady=(2, 10))
        self.entry_custom_path = ctk.CTkEntry(custom_row, placeholder_text="เลือกไฟล์ terminal64.exe...", height=28, font=ctk.CTkFont(size=11))
        self.entry_custom_path.pack(side="left", fill="x", expand=True, padx=(0, 8))
        if cfg_path_norm and not matched_any:
            self.term_choice_var.set("CUSTOM")
            self.entry_custom_path.insert(0, self._current_term_path or "")

        ctk.CTkButton(
            custom_row, text="เลือกไฟล์...", width=80, height=28, font=ctk.CTkFont(size=11),
            fg_color="#1F2937", hover_color="#374151", text_color=COLOR_TEXT_PRIMARY,
            command=self._browse_custom_terminal,
        ).pack(side="right")

        # ปุ่มบันทึกการตั้งค่า Terminal
        term_btn_row = ctk.CTkFrame(card_mt5, fg_color="transparent")
        term_btn_row.pack(fill="x", padx=14, pady=(0, 12))
        self.btn_save_term = ctk.CTkButton(
            term_btn_row, text="💾 บันทึกและทดสอบเชื่อมต่อ Terminal",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK, text_color="#1A1406",
            height=30, command=self._save_and_test_terminal,
        )
        self.btn_save_term.pack(side="left")
        self.lbl_term_status = ctk.CTkLabel(term_btn_row, text="", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED)
        self.lbl_term_status.pack(side="left", padx=12)

        # -------------------------------------------------------------
        # การ์ดที่ 3: จัดการ Profile & เปิดบอทหลายตัว (Multi-Instance Launcher)
        # -------------------------------------------------------------
        card_multi = ctk.CTkFrame(content, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        card_multi.pack(fill="x", pady=(0, 8), padx=4)

        c3_head = ctk.CTkFrame(card_multi, fg_color="transparent")
        c3_head.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(
            c3_head,
            text="🚀 สลับ หรือ เปิดบอท Profile อื่น (Multi-Instance)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
        ).pack(side="left")

        # รายการ Profile ทั้งหมด
        profs_all = list_profiles()
        p_list_row = ctk.CTkFrame(card_multi, fg_color="transparent")
        p_list_row.pack(fill="x", padx=14, pady=6)
        ctk.CTkLabel(p_list_row, text="เลือก Profile ที่มีอยู่:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left")

        self.combo_profiles = ctk.CTkComboBox(
            p_list_row,
            values=profs_all,
            width=160,
            height=28,
            font=ctk.CTkFont(size=12),
        )
        self.combo_profiles.set(self._active_prof)
        self.combo_profiles.pack(side="left", padx=10)

        ctk.CTkButton(
            p_list_row, text="🚀 เปิดหน้าต่างใหม่ (Launch)", width=160, height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_SUCCESS_GREEN, hover_color="#059669", text_color="#FFFFFF",
            command=self._launch_selected_profile,
        ).pack(side="left", padx=(0, 8))

        # สร้าง Profile ใหม่
        new_row = ctk.CTkFrame(card_multi, fg_color="transparent")
        new_row.pack(fill="x", padx=14, pady=(6, 12))
        ctk.CTkLabel(new_row, text="สร้าง Profile ใหม่:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.entry_new_prof = ctk.CTkEntry(new_row, placeholder_text="เช่น XM, FBS2, Real-Cent...", width=160, height=28, font=ctk.CTkFont(size=12))
        self.entry_new_prof.pack(side="left", padx=10)

        ctk.CTkButton(
            new_row, text="➕ สร้างและเปิดทันที", width=160, height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK, text_color="#1A1406",
            command=self._create_and_launch_profile,
        ).pack(side="left", padx=(0, 8))

        # ปุ่มสร้าง Shortcut .bat
        bat_row = ctk.CTkFrame(card_multi, fg_color="transparent")
        bat_row.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(
            bat_row, text="⚡ สร้างไฟล์ Shortcut (.bat) สำหรับเปิดด่วนแยก Profile",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1F2937", hover_color="#374151", text_color=COLOR_GOLD_PRIMARY,
            height=28, command=self._generate_desktop_shortcuts,
        ).pack(side="left")

    def _save_magic(self):
        val = self.entry_magic.get().strip()
        try:
            m = int(val)
            if m <= 0:
                raise ValueError
            set_profile_magic_number(m)
            messagebox.showinfo("บันทึกสำเร็จ", f"บันทึก Magic Number = {m} สำหรับ Profile [{self._active_prof}] เรียบร้อยแล้ว")
        except Exception:
            messagebox.showerror("ข้อผิดพลาด", "กรุณาระบุ Magic Number เป็นตัวเลขจำนวนเต็มบวก เช่น 888999")

    def _browse_custom_terminal(self):
        f = filedialog.askopenfilename(
            title="เลือกไฟล์ terminal64.exe ของ MetaTrader 5",
            filetypes=[("MT5 Terminal Executable", "terminal64.exe;terminal.exe"), ("All Executables", "*.exe")],
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
            messagebox.showerror("ไม่พบไฟล์", f"ไม่พบไฟล์ Terminal ตาม Path ที่ระบุ:\n{chosen}")
            return

        set_configured_terminal_path(chosen if chosen else None)
        self.lbl_term_status.configure(text="กำลังทดสอบเชื่อมต่อ…", text_color=COLOR_GOLD_PRIMARY)
        self.update_idletasks()

        ok = initialize_mt5(path=chosen if chosen else None)
        if ok:
            self.lbl_term_status.configure(text="✓ เชื่อมต่อสำเร็จ", text_color=COLOR_SUCCESS_GREEN)
            messagebox.showinfo("สำเร็จ", f"บันทึกและเชื่อมต่อกับ MetaTrader 5 เรียบร้อยแล้ว!\nPath: {chosen or 'Auto-Detect'}")
        else:
            self.lbl_term_status.configure(text="⚠ เชื่อมต่อไม่สำเร็จ", text_color=COLOR_DANGER_RED)
            messagebox.showwarning("แจ้งเตือน", f"บันทึกแล้ว แต่ไม่สามารถเชื่อมต่อ MT5 ได้ในขณะนี้\nกรุณาเปิด MT5 แล้วลองใหม่อีกครั้ง")

    def _launch_selected_profile(self):
        prof = self.combo_profiles.get().strip()
        if not prof:
            return
        self._spawn_instance(prof)

    def _create_and_launch_profile(self):
        name = self.entry_new_prof.get().strip()
        if not name:
            messagebox.showwarning("แจ้งเตือน", "กรุณากรอกชื่อ Profile ที่ต้องการสร้าง")
            return
        # ทำความสะอาดชื่อ
        clean = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip()
        if not clean:
            messagebox.showerror("ข้อผิดพลาด", "ชื่อ Profile ควรประกอบด้วยตัวอักษรหรือตัวเลขภาษาอังกฤษ")
            return

        # สร้าง directory ของ profile
        set_active_profile(clean)
        # สลับกลับมา profile เดิมของหน้าต่างนี้
        set_active_profile(self._active_prof)

        # อัปเดต combobox
        self.combo_profiles.configure(values=list_profiles())
        self.combo_profiles.set(clean)

        # เปิดหน้าต่างใหม่
        self._spawn_instance(clean)

    def _spawn_instance(self, profile_name: str):
        """สั่งเปิดโปรเซส GUI บอทใหม่สำหรับ Profile นั้นๆ"""
        try:
            if getattr(sys, "frozen", False):
                exe = sys.executable
                args = [exe, "--profile", profile_name]
            else:
                exe = sys.executable
                script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui_app.py")
                args = [exe, script, "--profile", profile_name]

            subprocess.Popen(args, close_fds=True)
            messagebox.showinfo(
                "เปิดหน้าต่างใหม่สำเร็จ",
                f"กำลังเปิด Gold Bot 24 สำหรับ Profile [{profile_name}] ขึ้นมาอีกหน้าต่าง...\n"
                f"โปรแกรมจะทำงานคู่ขนานโดยไม่กระทบหน้าต่างนี้",
            )
        except Exception as e:
            messagebox.showerror("เปิดโปรแกรมไม่สำเร็จ", f"เกิดข้อผิดพลาดในการเปิดโปรเซสใหม่:\n{e}")

    def _generate_desktop_shortcuts(self):
        """สร้างไฟล์ .bat สำหรับดับเบิลคลิกเปิดแต่ละ Profile ให้ผู้ใช้"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            profs = list_profiles()
            created_files = []

            for p in profs:
                bat_name = f"Launch_GoldBot_{p}.bat"
                bat_path = os.path.join(script_dir, bat_name)
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write("@echo off\n")
                    f.write(f"title GoldBot24 [{p}]\n")
                    f.write(f"cd /d \"%~dp0\"\n")
                    if getattr(sys, "frozen", False):
                        f.write(f"start \"\" \"{sys.executable}\" --profile {p}\n")
                    else:
                        f.write(f"start \"\" python gui_app.py --profile {p}\n")
                created_files.append(bat_path)

            msg = "สร้างไฟล์เปิดด่วน (.bat) สำเร็จ:\n\n" + "\n".join(f"- {os.path.basename(p)}" for p in created_files)
            msg += "\n\nท่านสามารถคัดลอกไฟล์เหล่านี้ไปวางบน Desktop เพื่อดับเบิลคลิกเปิดแต่ละบัญชีได้ทันที!"
            messagebox.showinfo("สร้างไฟล์สำเร็จ", msg)
            os.startfile(script_dir)
        except Exception as e:
            messagebox.showerror("เกิดข้อผิดพลาด", f"สร้างไฟล์ Shortcut ไม่สำเร็จ:\n{e}")
