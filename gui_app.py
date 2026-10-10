"""
AI MetaTrader 5 (FBS) Gold Pro - Desktop GUI Application
เวอร์ชัน: ดู version.py
หน้าจอ UI สำหรับเข้าใช้งานระบบ, ตรวจสอบสิทธิ์ชั่วโมง (Hours Metering), เติมชั่วโมงด้วย Product Key,
และควบคุมการเปิด/ปิดระบบเทรดอัตโนมัติ 100% Pure Gold Specialist (XAUUSD)
"""

import os
import json
import sys
import ctypes
import time
import math
import queue
import threading
import webbrowser
import app_fonts   # Anuphan + JetBrains Mono (โหลดก่อนสร้างหน้าต่างใด ๆ)
import thai_time
import mt5_algo
import urllib.parse
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from license_manager import (
    license_mgr,
    format_hours_minutes,
    normalize_key_input,
    validate_key_format
)
from bot_controller import bot_ctrl
import sound_manager
import econ_calendar
import news_impact
import news_th
import ai_outlook
import position_advisor
import position_chart
from version import APP_VERSION
import secure_store
import plan_config
from app_paths import data_path
from collections import deque
from console_format import ConsoleFormatter, TAG_COLORS
from stats_manager import stats_mgr, STANDARD_PLANS

# ตั้งค่ารูปลักษณ์และธีม CustomTkinter เป็น Dark Mode ระดับพรีเมียม
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
ctk.ThemeManager.theme["CTkFont"]["family"] = app_fonts.UI   # วิดเจ็ตที่ไม่ได้ระบุฟอนต์ใช้ Anuphan ด้วย

# กำหนด Palette สีระดับพรีเมียม (Gold & Obsidian Theme)
COLOR_BG_DARK = "#0A0B0F"          # พื้นหลังหลักโทนดำสนิท
COLOR_CARD_BG = "#14171E"          # สีพื้นกล่องการ์ด
COLOR_CARD_BORDER = "#252A35"      # เส้นขอบการ์ด
COLOR_CARD_HOVER = "#1F2430"       # สีเมื่อเมาส์ชี้การ์ด

COLOR_GOLD_PRIMARY = "#F2C14E"     # สีทองสว่าง
COLOR_GOLD_WARM = "#E0A92B"        # สีทองอำพัน
COLOR_GOLD_DARK = "#9A6B12"        # สีทองเข้ม
COLOR_GOLD_BG = "#221B0D"          # พื้นหลังเรืองแสงสีทอง

COLOR_SUCCESS_GREEN = "#34D399"    # สีเขียวสำเร็จ
COLOR_DANGER_RED = "#F87171"       # สีแดงแจ้งเตือน
COLOR_CYAN_ACCENT = "#60A5FA"      # สีฟ้าไฮไลท์
COLOR_TEXT_PRIMARY = "#ECEEF3"     # ข้อความหลักสีขาวนวล
COLOR_TEXT_MUTED = "#A3ABBA"       # ข้อความรองสีเทา


class _HintProxy:
    """ป้ายแจ้ง "บันทึกแล้ว ✓" แบบไม่เพิ่มพื้นที่ — ต่อท้ายข้อความของวิดเจ็ตเดิมชั่วคราว (รองรับ .configure(text=, text_color=))"""

    def __init__(self, widget, base_text):
        self.widget, self.base = widget, base_text
        self.base_color = widget.cget("text_color")

    def configure(self, text="", text_color=None):
        short = {"บันทึกแล้ว ✓": "✓", "ปิดใช้งาน": "(ปิด)"}.get(text, "✗" if text else "")
        self.widget.configure(text=f"{self.base} {short}".strip() if short else self.base,
                              text_color=(text_color or self.base_color) if short else self.base_color)


def status_pill_style(d, up="▲ หนุน", down="▼ สวน", mid="• กลาง"):
    """ป้ายสถานะแบบแท็บ AI คาดการณ์: (ข้อความ, สีตัวอักษร, สีพื้น) ตามทิศ +1/-1/0"""
    if d > 0:
        return f" {up} ", COLOR_SUCCESS_GREEN, "#0F2A20"
    if d < 0:
        return f" {down} ", COLOR_DANGER_RED, "#2A1215"
    return f" {mid} ", COLOR_TEXT_MUTED, "#262B36"


class HoverTip:
    """กล่องข้อความลอยเมื่อชี้เมาส์ (เช่น คำแปลชื่อข่าวภาษาไทย)"""

    def __init__(self, widget, text_fn, delay=350):
        self.widget, self.text_fn, self.delay = widget, text_fn, delay
        self.tip, self.job = None, None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _e=None):
        self._cancel()
        self.job = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self.job:
            try:
                self.widget.after_cancel(self.job)
            except Exception:
                pass
            self.job = None

    def _show(self):
        text = self.text_fn() if callable(self.text_fn) else self.text_fn
        if not text or self.tip:
            return
        x = self.widget.winfo_pointerx() + 14
        y = self.widget.winfo_pointery() + 18
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.attributes("-topmost", True)
        frame = tk.Frame(tw, bg=COLOR_GOLD_DARK, bd=0)
        frame.pack()
        tk.Label(frame, text=text, justify="left", bg="#1A1E27", fg=COLOR_TEXT_PRIMARY, font=(app_fonts.UI, 10),
                 padx=10, pady=6, wraplength=420).pack(padx=1, pady=1)
        tw.wm_geometry(f"+{x}+{y}")

    def _hide(self, _e=None):
        self._cancel()
        if self.tip:
            self.tip.destroy()
            self.tip = None


def _app_icon_path():
    base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "assets", "app_icon.ico")


def apply_dark_title_bar(window, bg_hex=COLOR_BG_DARK, text_hex=COLOR_TEXT_PRIMARY):
    """
    บังคับใช้แถบไตเติ้ลบาร์สีเข้ม (Dark Theme / Immersive Dark Mode) สำหรับ Windows 10/11
    ป้องกันการหลุดเป็นไตเติ้ลบาร์สีขาวเมื่อถูกเรียก self.transient(parent) หรือเปิดหน้าต่างป๊อปอัป
    """
    if sys.platform != "win32":
        return

    def _apply():
        try:
            if not window.winfo_exists():
                return
            wid = window.winfo_id()
            p = ctypes.windll.user32.GetParent(wid)
            hwnd = p if p else wid
            if not hwnd:
                return

            val = ctypes.c_int(1)
            # 1) Windows 10 (20H1+ / Build 19041+) & Windows 11 Immersive Dark Mode
            res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(val), ctypes.sizeof(val)
            )
            # 2) Fallback สำหรับ Windows 10 รุ่นก่อน 20H1 (Build < 19041)
            if res != 0:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 19, ctypes.byref(val), ctypes.sizeof(val)
                )

            # 3) Windows 11 build 22000+: สีพื้นหลังไตเติ้ลบาร์ (COLORREF / BGR)
            if bg_hex and len(bg_hex) == 7 and bg_hex.startswith("#"):
                r, g, b = int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)
                c_bgr = ctypes.c_int(r | (g << 8) | (b << 16))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 35, ctypes.byref(c_bgr), ctypes.sizeof(c_bgr)
                )

            # 4) Windows 11 build 22000+: สีตัวอักษรไตเติ้ลบาร์ (COLORREF / BGR)
            if text_hex and len(text_hex) == 7 and text_hex.startswith("#"):
                r, g, b = int(text_hex[1:3], 16), int(text_hex[3:5], 16), int(text_hex[5:7], 16)
                t_bgr = ctypes.c_int(r | (g << 8) | (b << 16))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 36, ctypes.byref(t_bgr), ctypes.sizeof(t_bgr)
                )

            # บังคับให้ Windows DWM รีเฟรชกรอบหน้าต่างทันที ป้องกันจังหวะกะพริบขาว
            flags = 0x0020 | 0x0002 | 0x0001 | 0x0004 | 0x0010  # FRAMECHANGED | NOMOVE | NOSIZE | NOZORDER | NOACTIVATE
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, flags)
        except Exception:
            pass

    _apply()
    try:
        window.after(20, _apply)
        window.after(100, _apply)
        window.after(300, _apply)
    except Exception:
        pass


# หน้าต่างย่อยทุกอัน (CTkToplevel) ใช้โลโก้เดียวกับโปรแกรมหลัก และบังคับใช้ Dark Title Bar
# CustomTkinter ตั้งไอคอนเริ่มต้นของตัวเองหลังสร้าง ~200ms จึงต้องตั้งทับหลังจากนั้น
# และอยู่หน้าสุดเสมอ (topmost) — ไม่ถูกโปรแกรมอื่น เช่น MT5 / เบราว์เซอร์ บังขณะเปิดอยู่
_ctk_toplevel_init = ctk.CTkToplevel.__init__


def _toplevel_init_with_icon(self, *args, **kwargs):
    _ctk_toplevel_init(self, *args, **kwargs)
    apply_dark_title_bar(self)
    try:
        self.bind("<Map>", lambda _e: apply_dark_title_bar(self), add="+")
    except Exception:
        pass
    try:
        self.attributes("-topmost", True)
        self.after(60, self.lift)
    except Exception:
        pass
    icon = _app_icon_path()
    if os.path.exists(icon):
        def _set():
            try:
                self.iconbitmap(icon)
            except Exception:
                pass
        self.after(250, _set)


ctk.CTkToplevel.__init__ = _toplevel_init_with_icon

# เมื่อหน้าต่างย่อยเรียก self.transient(parent) หรือ wm_transient Windows OS จะรีเซ็ตไตเติ้ลบาร์กลับเป็นสีขาว
# ดักจับและบังคับใช้ Dark Title Bar ซ้ำเสมอ
_orig_ctk_transient = ctk.CTkToplevel.transient


def _toplevel_transient(self, *args, **kwargs):
    res = _orig_ctk_transient(self, *args, **kwargs)
    apply_dark_title_bar(self)
    return res


ctk.CTkToplevel.transient = _toplevel_transient
ctk.CTkToplevel.wm_transient = _toplevel_transient


class RedeemKeyDialog(ctk.CTkToplevel):
    """
    หน้าต่างป๊อปอัปสำหรับเติมชั่วโมงด้วย Product Key
    รองรับการจัดรูปแบบอัตโนมัติ: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
    และคำนวณการบวกเพิ่ม (+) ชั่วโมงสะสมจากของเดิมทันที
    """
    def __init__(self, parent, on_redeemed_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.on_redeemed_callback = on_redeemed_callback

        self.title("เติมชั่วโมงการใช้งาน - AI Gold Pro")
        self.geometry("560x420")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        # วางกึ่งกลางหน้าต่างหลัก
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        x = px + max(0, (pw - 560) // 2)
        y = py + max(0, (ph - 420) // 2)
        self.geometry(f"560x420+{x}+{y}")
        apply_dark_title_bar(self)

        self._build_ui()

    def _build_ui(self):
        # หัวเรื่อง
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=28, pady=(24, 12))

        ctk.CTkLabel(
            header_frame,
            text="🔑 เติมชั่วโมงการใช้งาน",
            font=ctk.CTkFont(family=app_fonts.UI, size=22, weight="bold"),
            text_color=COLOR_GOLD_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_frame,
            text="กรอกรหัส Product Key (บัตรเติมชั่วโมง) เพื่อเพิ่มเวลาเทรดให้กับบอท",
            font=ctk.CTkFont(family=app_fonts.UI, size=13),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(4, 0))

        # การ์ดแสดงชั่วโมงปัจจุบัน
        current_hrs_str = license_mgr.get_remaining_time_display()
        info_card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        info_card.pack(fill="x", padx=28, pady=(0, 16))

        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(
            info_inner,
            text="เวลาใช้งานคงเหลือปัจจุบัน:",
            font=ctk.CTkFont(family=app_fonts.UI, size=13),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left")

        self.lbl_current_time = ctk.CTkLabel(
            info_inner,
            text=f"{current_hrs_str} ชม. (ชั่วโมง.นาที)",
            font=ctk.CTkFont(family=app_fonts.UI, size=15, weight="bold"),
            text_color=COLOR_GOLD_WARM
        )
        self.lbl_current_time.pack(side="right")

        # กล่องกรอกรหัส Product Key
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=28, pady=0)

        ctk.CTkLabel(
            input_frame,
            text="รหัส Product Key (รูปแบบ: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX):",
            font=ctk.CTkFont(family=app_fonts.UI, size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 6))

        self.key_var = tk.StringVar()
        self.key_var.trace_add("write", self._on_key_typing)

        self.key_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.key_var,
            font=ctk.CTkFont(family=app_fonts.MONO, size=15, weight="bold"),
            height=48,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_GOLD_WARM,
            fg_color="#101218",
            placeholder_text="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"
        )
        self.key_entry.pack(fill="x")
        self.key_entry.focus()

        # คำแนะนำเกี่ยวกับการบวกเพิ่ม (+) เวลา
        tip_frame = ctk.CTkFrame(self, fg_color=COLOR_GOLD_BG, corner_radius=8, border_width=1, border_color="#523E15")
        tip_frame.pack(fill="x", padx=28, pady=(12, 16))

        ctk.CTkLabel(
            tip_frame,
            text="✨ หมายเหตุ: การเติมชั่วโมงจะ '+' บวกเพิ่มจากเวลาเดิมที่เหลืออยู่เสมอ (ไม่ทับของเก่า)",
            font=ctk.CTkFont(family=app_fonts.UI, size=12),
            text_color="#FDE68A"
        ).pack(padx=12, pady=8, anchor="w")

        # ข้อความผลลัพธ์แจ้งเตือน
        self.lbl_result = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family=app_fonts.UI, size=13, weight="bold"),
            text_color=COLOR_SUCCESS_GREEN
        )
        self.lbl_result.pack(padx=28, pady=(0, 10))

        # ปุ่มกดยืนยัน และยกเลิก
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=28, pady=(0, 20))

        self.btn_cancel = ctk.CTkButton(
            btn_frame,
            text="ปิดหน้าต่าง",
            font=ctk.CTkFont(family=app_fonts.UI, size=14),
            fg_color="#252A35",
            hover_color="#323846",
            height=42,
            corner_radius=8,
            command=self.destroy
        )
        self.btn_cancel.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.btn_submit = ctk.CTkButton(
            btn_frame,
            text="✅ ยืนยันการเติมชั่วโมง",
            font=ctk.CTkFont(family=app_fonts.UI, size=14, weight="bold"),
            fg_color=COLOR_GOLD_WARM,
            hover_color=COLOR_GOLD_DARK,
            text_color="#1A1406",
            height=42,
            corner_radius=8,
            command=self._do_redeem
        )
        self.btn_submit.pack(side="right", expand=True, fill="x", padx=(8, 0))

    def _on_key_typing(self, *args):
        """ระบบช่วยจัดรูปแบบ XXXX-XXXX-XXXX-XXXX-XXXX-XXXX อัตโนมัติขณะพิมพ์"""
        raw = self.key_var.get()
        # ป้องกัน recursive trace
        normalized = normalize_key_input(raw)
        if raw != normalized:
            self.key_var.set(normalized)

    def _do_redeem(self):
        """ดำเนินการตรวจสอบและเติมชั่วโมง"""
        key_code = self.key_var.get().strip()
        if not key_code:
            self.lbl_result.configure(text="กรุณากรอกรหัส Product Key", text_color=COLOR_DANGER_RED)
            return

        success, msg, added = license_mgr.redeem_product_key(key_code)
        if success:
            sound_manager.play_tp_hit() # เล่นเสียงกระดิ่งฉลอง
            new_time_str = license_mgr.get_remaining_time_display()
            self.lbl_current_time.configure(text=f"{new_time_str} ชม. (ชั่วโมง.นาที)")
            self.lbl_result.configure(
                text=f"🎉 {msg}",
                text_color=COLOR_SUCCESS_GREEN
            )
            self.btn_submit.configure(state="disabled")
            if self.on_redeemed_callback:
                self.on_redeemed_callback(new_time_str)
        else:
            sound_manager.play_sl_hit() # เสียงแจ้งเตือนผิดพลาด
            self.lbl_result.configure(text=f"❌ {msg}", text_color=COLOR_DANGER_RED)


class UpdateDialog(ctk.CTkToplevel):
    """แจ้งเวอร์ชันใหม่: เวอร์ชันเดิม → ใหม่ · สิ่งที่เปลี่ยนแยกหัวข้อ · ระบบอัปเดตแพตช์ทับ Path เดิมอัตโนมัติ (1-Click In-App Updater)"""

    def __init__(self, parent, info, download_url):
        super().__init__(parent)
        import re
        import threading
        self.title("มีเวอร์ชันใหม่ - AI Gold Commander Pro")
        w, h = 580, 600
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.resizable(False, False)
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        apply_dark_title_bar(self)
        self.info = info or {}
        self.url = download_url
        self.direct_url = self.info.get("direct_download_url") or download_url
        self.is_installer = bool(self.info.get("is_installer", True))
        self.file_name = self.info.get("file_name") or ("GoldBot24_Setup.exe" if self.is_installer else "update.zip")
        self._download_thread = None
        self._is_updating = False
        self._cancel_event = threading.Event()

        def f(size, weight="normal"):
            return ctk.CTkFont(family=app_fonts.UI, size=size, weight=weight)

        # ส่วนหัว: ไอคอน + เวอร์ชันเดิม → ใหม่
        head = ctk.CTkFrame(self, fg_color=COLOR_GOLD_BG, corner_radius=0)
        head.pack(fill="x")
        inner = ctk.CTkFrame(head, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=16)
        # ไอคอนลูกศรวาดเอง
        icon = tk.Canvas(inner, width=46, height=46, bg=COLOR_GOLD_BG, highlightthickness=0, bd=0)
        icon.create_oval(1, 1, 45, 45, fill="#3A2E14", outline="")
        icon.create_polygon(23, 10, 35, 24, 27, 24, 27, 35, 19, 35, 19, 24, 11, 24, fill=COLOR_GOLD_PRIMARY, outline="")
        icon.pack(side="left")
        txt = ctk.CTkFrame(inner, fg_color="transparent")
        txt.pack(side="left", padx=14)
        ctk.CTkLabel(txt, text="มีเวอร์ชันใหม่พร้อมอัปเดต", font=f(18, "bold"), text_color=COLOR_GOLD_PRIMARY).pack(anchor="w")
        chips = ctk.CTkFrame(txt, fg_color="transparent")
        chips.pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(chips, text=f"  ใช้งานอยู่ v{APP_VERSION}  ", font=f(11), text_color=COLOR_TEXT_MUTED,
                     fg_color=COLOR_CARD_BG, corner_radius=6, height=22).pack(side="left")
        ctk.CTkLabel(chips, text="→", font=f(13, "bold"), text_color=COLOR_GOLD_PRIMARY).pack(side="left", padx=6)
        ctk.CTkLabel(chips, text=f"  ใหม่ v{info.get('latest_version')}  ", font=f(11, "bold"), text_color="#1A1406",
                     fg_color=COLOR_GOLD_PRIMARY, corner_radius=6, height=22).pack(side="left")
        size_mb = (self.info.get("size_bytes", 0) or 0) / (1024 * 1024)
        if size_mb > 0:
            ctk.CTkLabel(chips, text=f"({size_mb:.1f} MB)", font=f(11), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(6, 0))

        # มีอะไรใหม่ — แยกตามหัวข้อ ### ใน Release notes
        ctk.CTkLabel(self, text="มีอะไรใหม่", font=f(13, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=22, pady=(12, 6))
        box = ctk.CTkScrollableFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        box.pack(fill="both", expand=True, padx=22)
        sections, cur = [], None
        for ln in (info.get("changelog") or "").splitlines():
            t = ln.strip()
            if t.startswith("#"):
                title = t.lstrip("#").strip()
                cur = None if ("sha" in title.lower() or "ติดตั้ง" in title or "ดาวน์โหลด" in title) else [title, []]
                if cur:
                    sections.append(cur)
            elif t.startswith("- ") and cur is not None:
                cur[1].append(re.sub(r"[`*]", "", t[2:]))
        sections = [x for x in sections if x[1]][:6] or [["ปรับปรุง", ["ปรับปรุงประสิทธิภาพและแก้ไขข้อผิดพลาด"]]]
        for i, (title, items) in enumerate(sections):
            ctk.CTkLabel(box, text=title, font=f(12, "bold"), text_color=COLOR_GOLD_PRIMARY, anchor="w", justify="left",
                         wraplength=490).pack(anchor="w", padx=12, pady=(12 if i == 0 else 12, 4))
            for it in items[:6]:
                row = ctk.CTkFrame(box, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=1)
                ctk.CTkLabel(row, text="•", font=f(12, "bold"), text_color=COLOR_SUCCESS_GREEN, width=14).pack(side="left", anchor="n")
                ctk.CTkLabel(row, text=it, font=f(12), text_color=COLOR_TEXT_PRIMARY, anchor="w", justify="left",
                             wraplength=470).pack(side="left", fill="x")

        # แถบ Progress Bar สำหรับดาวน์โหลด (ซ่อนไว้ก่อน)
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_lbl = ctk.CTkLabel(self.progress_frame, text="กำลังเตรียมดาวน์โหลดแพตช์...", font=f(11), text_color=COLOR_GOLD_PRIMARY)
        self.progress_lbl.pack(anchor="w", pady=(0, 4))
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=10, corner_radius=5,
                                              progress_color=COLOR_GOLD_PRIMARY, fg_color="#1E232C")
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x")

        self.tip_lbl = ctk.CTkLabel(self, text="⚡ อัปเดตทับ Path เดิมอัตโนมัติ · การตั้งค่าและประวัติพอร์ตยังอยู่ครบ 100%",
                                    font=f(11), text_color=COLOR_TEXT_MUTED)
        self.tip_lbl.pack(anchor="w", padx=22, pady=(8, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=22, pady=(8, 16))
        self.btn_cancel = ctk.CTkButton(btns, text="ภายหลัง", width=90, height=38, font=f(12), fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_HOVER,
                                        border_width=1, border_color=COLOR_CARD_BORDER, text_color=COLOR_TEXT_MUTED, command=self._on_cancel)
        self.btn_cancel.pack(side="right")

        self.btn_web = ctk.CTkButton(btns, text="เปิดหน้าเว็บ", width=95, height=38, font=f(12), fg_color="#1A2232", hover_color="#243048",
                                     border_width=1, border_color="#2E3C54", text_color=COLOR_CYAN_ACCENT, command=lambda: webbrowser.open(self.url))
        self.btn_web.pack(side="right", padx=(0, 8))

        self.btn_update = ctk.CTkButton(btns, text="🚀 อัปเดตแพตช์ทันที (1-Click)", height=38, font=f(13, "bold"), fg_color=COLOR_GOLD_PRIMARY,
                                        hover_color=COLOR_GOLD_WARM, text_color="#1A1406", command=self._start_in_place_update)
        self.btn_update.pack(side="right", fill="x", expand=True, padx=(0, 8))

    def _start_in_place_update(self):
        if self._is_updating:
            return
        self._is_updating = True
        self.btn_update.configure(state="disabled", text="กำลังดาวน์โหลด...")
        self.btn_web.configure(state="disabled")
        self.btn_cancel.configure(text="ยกเลิก")
        self.tip_lbl.pack_forget()
        self.progress_frame.pack(fill="x", padx=22, pady=(6, 2))

        def _worker():
            import tempfile
            import in_place_updater

            url = self.direct_url
            fname = self.file_name or "update_package.exe"
            tmp_dir = tempfile.gettempdir()
            dest_file = os.path.join(tmp_dir, f"goldbot_update_{int(time.time())}_{fname}")

            def _on_prog(dl, tot, pct, spd):
                dl_mb = dl / (1024 * 1024)
                tot_mb = tot / (1024 * 1024) if tot > 0 else dl_mb
                txt = f"กำลังดาวน์โหลดแพตช์... {dl_mb:.1f} MB / {tot_mb:.1f} MB ({pct:.0f}%) · {spd:.1f} MB/s"
                self.after(0, lambda: self._update_progress_ui(pct / 100.0, txt))

            ok = in_place_updater.download_file_with_progress(url, dest_file, _on_prog, self._cancel_event)
            if not ok:
                if not self._cancel_event.is_set():
                    self.after(0, lambda: self._update_failed("ดาวน์โหลดแพตช์ไม่สำเร็จ กรุณาลองใหม่หรือดาวน์โหลดผ่านหน้าเว็บ"))
                return

            self.after(0, lambda: self._update_complete_and_launch(dest_file))

        self._download_thread = threading.Thread(target=_worker, daemon=True)
        self._download_thread.start()

    def _update_progress_ui(self, fraction, text):
        try:
            self.progress_bar.set(fraction)
            self.progress_lbl.configure(text=text)
        except Exception:
            pass

    def _update_failed(self, msg):
        self._is_updating = False
        self.progress_frame.pack_forget()
        self.tip_lbl.pack(anchor="w", padx=22, pady=(8, 0))
        self.btn_update.configure(state="normal", text="ลองใหม่อีกครั้ง")
        self.btn_web.configure(state="normal")
        self.btn_cancel.configure(text="ปิด")
        messagebox.showerror("อัปเดตแพตช์ล้มเหลว", msg)

    def _update_complete_and_launch(self, dest_file):
        import in_place_updater
        self.progress_bar.set(1.0)
        self.progress_lbl.configure(text="✓ ดาวน์โหลดสมบูรณ์ กำลังเริ่มอัปเดตทับ Path เดิมและรีสตาร์ทโปรแกรม...")
        self.btn_update.configure(text="กำลังรีสตาร์ท...")

        def _do_launch():
            ok, msg = in_place_updater.launch_in_place_patch(dest_file, self.is_installer)
            if ok:
                os._exit(0)
            else:
                self._update_failed(msg)

        self.after(1200, _do_launch)

    def _on_cancel(self):
        if self._is_updating:
            self._cancel_event.set()
        self.destroy()


class NewsImpactDialog(ctk.CTkToplevel):
    """รายละเอียดการวิเคราะห์ผลกระทบของข่าว 1 รายการต่อราคาทอง"""

    def __init__(self, parent, ev, analysis, gold_price=0.0):
        super().__init__(parent)
        self.title("ผลกระทบข่าวต่อทองคำ")
        w, h = 580, 520
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        apply_dark_title_bar(self)
        f = lambda size, weight="normal": ctk.CTkFont(family=app_fonts.UI, size=size, weight=weight)
        a = analysis or {}

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(16, 4))
        ctk.CTkLabel(head, text=ev["title"], font=f(17, "bold"), text_color=COLOR_GOLD_PRIMARY, anchor="w",
                     wraplength=500, justify="left").pack(anchor="w")
        th = news_th.translate(ev["title"])
        if th:
            ctk.CTkLabel(head, text=th, font=f(13), text_color=COLOR_TEXT_PRIMARY, anchor="w",
                         wraplength=500, justify="left").pack(anchor="w")
        ctk.CTkLabel(head, text=f"{econ_calendar.format_day(ev['time'])} · {ev['time'].strftime('%H:%M')} น. · {ev['currency']} · "
                                f"ผลกระทบ{'สูง' if ev['impact'] == 'High' else 'กลาง' if ev['impact'] == 'Medium' else 'ต่ำ'}"
                                f" · คาด {ev['forecast'] or '—'} · ครั้งก่อน {ev['previous'] or '—'}",
                     font=f(12), text_color=COLOR_TEXT_MUTED).pack(anchor="w")

        def card(title, value, sub, color, size=16):
            c = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
            c.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(c, text=title, font=f(11), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=14, pady=(8, 0))
            ctk.CTkLabel(c, text=value, font=f(size, "bold"), text_color=color, anchor="w", justify="left", wraplength=480).pack(anchor="w", padx=14)
            if sub:
                ctk.CTkLabel(c, text=sub, font=f(11), text_color=COLOR_TEXT_MUTED, anchor="w", justify="left", wraplength=480).pack(anchor="w", padx=14, pady=(0, 8))
            else:
                ctk.CTkFrame(c, height=6, fg_color="transparent").pack()

        actual = a.get("actual")
        lean = a.get("lean", 0)
        if actual is not None:
            pts = abs(actual) / 100 * gold_price if gold_price else 0
            card("ผลจริงหลังข่าวออก (60 นาที)", f"ทอง{'ขึ้น' if actual > 0 else 'ลง'} {actual:+.2f}%" + (f" (~{pts:.1f} จุด)" if pts else ""),
                 "วัดจากราคาทองจริงใน MT5 ตั้งแต่เวลาประกาศถึง 60 นาทีหลังจากนั้น", COLOR_SUCCESS_GREEN if actual > 0 else COLOR_DANGER_RED)
        else:
            if lean > 0:
                val, col = "▲ แนวโน้มทองขึ้น", COLOR_SUCCESS_GREEN
            elif lean < 0:
                val, col = "▼ แนวโน้มทองลง", COLOR_DANGER_RED
            else:
                val, col = "ไม่ชัดเจน — รอดูตัวเลขจริง", COLOR_TEXT_PRIMARY
            why = ""
            if lean:
                why = (f"ตลาดคาด {ev['forecast']} เทียบครั้งก่อน {ev['previous']} → "
                       + ("ดอลลาร์มีแนวโน้มอ่อนลง" if lean > 0 else "ดอลลาร์มีแนวโน้มแข็งขึ้น")
                       + " · ถ้าตัวเลขจริงออกตามคาด ทองมัก" + ("ขึ้น" if lean > 0 else "ลง") + " แต่ถ้าออกผิดคาดมาก ทิศอาจกลับได้")
            card("แนวโน้มก่อนข่าวออก (จากตัวเลขคาดการณ์)", val, why, col)

        card("หลักการของข่าวประเภทนี้", a.get("rule") or "—", "", COLOR_TEXT_PRIMARY, size=13)

        st = a.get("stats")
        if st:
            pts = st["median_abs"] / 100 * gold_price if gold_price else 0
            src = (f"จากข่าว {ev['title']} ที่ผ่านมา {st['n']} ครั้ง" if st.get("source") == "title"
                   else f"สถิติทองย้อนหลัง ~2 ปี ช่วงวัน/เวลาเดียวกับข่าวนี้ ({st['n']} ครั้ง) — รวมสัปดาห์ที่ไม่มีข่าวนี้ด้วย ตัวเลขจริงตอนมีข่าวมักสูงกว่า")
            card("ทองมักขยับใน 60 นาทีหลังเวลานี้",
                 f"ปกติ ±{st['median_abs']:.2f}%" + (f" (~{pts:.1f} จุด)" if pts else "") + f" · แรง ±{st['p80_abs']:.2f}%",
                 src, COLOR_GOLD_PRIMARY)
        else:
            card("ทองมักขยับใน 60 นาทีหลังเวลานี้", "ยังไม่มีสถิติ", "ต้องเชื่อมต่อ MT5 เพื่อคำนวณ", COLOR_TEXT_MUTED)

        ctk.CTkLabel(self, text="เป็นการประเมินจากกฎเศรษฐกิจและสถิติในอดีต ไม่ใช่การรับประกันทิศทางราคา",
                     font=f(10), text_color=COLOR_TEXT_MUTED).pack(pady=(6, 10))


class StyledMessage(ctk.CTkToplevel):
    """กล่องข้อความ/ยืนยันในธีมโปรแกรม (แทน messagebox ของ Windows) — kind: confirm / info / success / warning / error"""

    KINDS = {
        "confirm": ("?", COLOR_GOLD_PRIMARY, "#2A2210"),
        "danger": ("!", COLOR_DANGER_RED, "#2A1215"),
        "info": ("i", COLOR_CYAN_ACCENT, "#132036"),
        "success": ("✓", COLOR_SUCCESS_GREEN, "#0F2A20"),
        "warning": ("!", COLOR_GOLD_PRIMARY, "#2A2210"),
        "error": ("✗", COLOR_DANGER_RED, "#2A1215"),
    }

    def __init__(self, parent, title, message, kind="info", ok_text="ตกลง", cancel_text=None):
        super().__init__(parent)
        self.result = False
        sym, color, bg = self.KINDS.get(kind, self.KINDS["info"])
        self.title(title)
        self.configure(fg_color=COLOR_BG_DARK)
        self.resizable(False, False)
        self.transient(parent)
        apply_dark_title_bar(self)

        def f(size, weight="normal"):
            return ctk.CTkFont(family=app_fonts.UI, size=size, weight=weight)

        msg = str(message or "").replace("⚠️", "").replace("⚠", "").strip()
        head, _, detail = msg.partition("\n")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=22, pady=(20, 8))
        icon = tk.Canvas(body, width=48, height=48, bg=COLOR_BG_DARK, highlightthickness=0, bd=0)
        icon.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 14))
        icon.create_oval(2, 2, 46, 46, fill=bg, outline=color, width=2)
        icon.create_text(24, 24, text=sym, fill=color, font=(app_fonts.UI, 18, "bold"))
        ctk.CTkLabel(body, text=title, font=f(15, "bold"), text_color=color, anchor="w", justify="left").grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(body, text=head.strip(), font=f(13), text_color=COLOR_TEXT_PRIMARY, anchor="w", justify="left",
                     wraplength=360).grid(row=1, column=1, sticky="w", pady=(4, 0))
        if detail.strip():
            ctk.CTkLabel(body, text=detail.strip().strip("()"), font=f(11), text_color=COLOR_TEXT_MUTED, anchor="w", justify="left",
                         wraplength=360).grid(row=2, column=1, sticky="w", pady=(4, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=22, pady=(10, 18))
        ok_fg = COLOR_DANGER_RED if kind in ("danger", "error") else COLOR_SUCCESS_GREEN if kind == "success" else COLOR_GOLD_PRIMARY
        ok_hv = "#E05A5A" if kind in ("danger", "error") else "#2BB383" if kind == "success" else COLOR_GOLD_WARM
        ok = ctk.CTkButton(btns, text=ok_text, height=38, width=140, font=f(13, "bold"), fg_color=ok_fg, hover_color=ok_hv,
                           text_color="#0A0B0F", command=self._ok)
        ok.pack(side="right")
        if cancel_text:
            ctk.CTkButton(btns, text=cancel_text, height=38, width=110, font=f(13), fg_color=COLOR_CARD_BG,
                          hover_color=COLOR_CARD_HOVER, border_width=1, border_color=COLOR_CARD_BORDER,
                          text_color=COLOR_TEXT_MUTED, command=self.destroy).pack(side="right", padx=(0, 10))
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        w, h = max(self.winfo_reqwidth(), 460), self.winfo_reqheight()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.grab_set()
        ok.focus_set()

    def _ok(self):
        self.result = True
        self.destroy()


class _StyledMessagebox:
    """แทน tkinter.messagebox ทั้งไฟล์: askyesno / showinfo / showwarning / showerror → StyledMessage (ทำงานแบบรอผลเหมือนเดิม)"""

    @staticmethod
    def _root():
        return tk._default_root

    def _run(self, title, message, kind, ok_text="ตกลง", cancel_text=None):
        root = self._root()
        if root is None:
            return False
        dlg = StyledMessage(root, title, message, kind, ok_text, cancel_text)
        root.wait_window(dlg)
        return dlg.result

    def askyesno(self, title, message, **_kw):
        danger = any(k in f"{title} {message}" for k in ("ปิด", "หยุด", "ลบ", "ยกเลิกไม่ได้", "ไม่สามารถยกเลิก"))
        return self._run(title, message, "danger" if danger else "confirm", ok_text="ยืนยัน", cancel_text="ยกเลิก")

    def showinfo(self, title, message, **_kw):
        ok = any(k in str(message) for k in ("สำเร็จ", "เรียบร้อย", "ล่าสุดแล้ว"))
        return self._run(title, message, "success" if ok else "info")

    def showwarning(self, title, message, **_kw):
        return self._run(title, message, "warning")

    def showerror(self, title, message, **_kw):
        return self._run(title, message, "error")


messagebox = _StyledMessagebox()


class ContactDialog(ctk.CTkToplevel):
    """ติดต่อแอดมินทาง LINE OA — QR + ปุ่มเปิด LINE + คัดลอกไอดี"""
    LINE_ID = "@887aczyq"
    LINE_URL = "https://line.me/R/ti/p/@887aczyq"

    def __init__(self, parent):
        super().__init__(parent)
        self.title("ติดต่อแอดมิน")
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.resizable(False, False)
        apply_dark_title_bar(self)

        def f(size, weight="normal", family=app_fonts.UI):
            return ctk.CTkFont(family=family, size=size, weight=weight)

        ctk.CTkLabel(self, text="ติดต่อแอดมิน", font=f(17, "bold"), text_color=COLOR_GOLD_PRIMARY).pack(anchor="w", padx=20, pady=(16, 0))
        ctk.CTkLabel(self, text="สแกน QR ด้วยแอป LINE ในมือถือ หรือกดปุ่มเปิด LINE", font=f(11),
                     text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(2, 10))
        try:
            from PIL import Image
            img = Image.open(os.path.join(os.path.dirname(_app_icon_path()), "line_qr.png"))
            self._qr = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 200))
            ctk.CTkLabel(self, text="", image=self._qr).pack(pady=(4, 8))
        except Exception:
            pass
        idrow = ctk.CTkFrame(self, fg_color="transparent")
        idrow.pack(pady=(0, 4))
        ctk.CTkLabel(idrow, text=self.LINE_ID, font=f(18, "bold", app_fonts.MONO), text_color=COLOR_TEXT_PRIMARY).pack(side="left", padx=(0, 10))
        self.btn_copy = ctk.CTkButton(idrow, text="คัดลอก", width=70, height=28, font=f(11), fg_color=COLOR_CARD_BG,
                                      hover_color=COLOR_CARD_HOVER, border_width=1, border_color=COLOR_CARD_BORDER,
                                      text_color=COLOR_TEXT_PRIMARY, command=self._copy)
        self.btn_copy.pack(side="left")
        ctk.CTkLabel(self, text="แจ้งอีเมลที่ใช้สมัคร + ภาพหน้าจอ/สลิป · แอดมินไม่ขอรหัสผ่านหรือรหัส MT5 ทุกกรณี",
                     font=f(10), text_color=COLOR_TEXT_MUTED).pack(padx=20, pady=(6, 0))
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=(12, 18))
        ctk.CTkButton(btns, text="ปิด", width=90, height=40, font=f(13), fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_HOVER,
                      border_width=1, border_color=COLOR_CARD_BORDER, text_color=COLOR_TEXT_MUTED, command=self.destroy).pack(side="right")
        ctk.CTkButton(btns, text="เปิด LINE ทักแชท", height=40, font=f(14, "bold"), fg_color="#06C755", hover_color="#05A647",
                      text_color="#FFFFFF", command=self._open_line).pack(side="right", fill="x", expand=True, padx=(0, 10))
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        w, h = 440, self.winfo_reqheight()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _open_line(self):
        # หน้าต่างนี้อยู่หน้าสุด — ปิดก่อน ไม่ให้บังเบราว์เซอร์/LINE ที่เปิดขึ้นมา
        webbrowser.open(self.LINE_URL)
        self.destroy()

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.LINE_ID)
        self.btn_copy.configure(text="✓ แล้ว", text_color=COLOR_SUCCESS_GREEN)


class QuickOrderDialog(ctk.CTkToplevel):
    """ยืนยันการเข้าไม้ทันที (BUY/SELL) — ราคาสด · ตั้ง SL/TP ด้วยปุ่ม −/+ หรือปุ่มลัด ATR · สรุปเสี่ยง/เป้า/RRR ก่อนส่งคำสั่งจริง"""

    def __init__(self, parent, side):
        super().__init__(parent)
        self.parent, self.side = parent, side
        buy = side == "BUY"
        self.buy = buy
        self.color = COLOR_SUCCESS_GREEN if buy else COLOR_DANGER_RED
        self.dark = "#0F2A20" if buy else "#2A1215"
        self.title(f"เข้าไม้ทันที — {side}")
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.resizable(False, False)
        apply_dark_title_bar(self)

        def f(size, weight="normal", family=app_fonts.UI):
            return ctk.CTkFont(family=family, size=size, weight=weight)
        self.f = f

        d = bot_ctrl.quick_order_defaults()
        # ── หัว: ทิศ + ราคาสด
        head = ctk.CTkFrame(self, fg_color=self.dark, corner_radius=0)
        head.pack(fill="x")
        hrow = ctk.CTkFrame(head, fg_color="transparent")
        hrow.pack(fill="x", padx=20, pady=14)
        icon = tk.Canvas(hrow, width=40, height=40, bg=self.dark, highlightthickness=0, bd=0)
        icon.pack(side="left", padx=(0, 12))
        icon.create_oval(1, 1, 39, 39, fill=self.color, outline="")
        if buy:
            icon.create_polygon(20, 10, 30, 25, 10, 25, fill="#0A0B0F", outline="")
        else:
            icon.create_polygon(10, 15, 30, 15, 20, 30, fill="#0A0B0F", outline="")
        tbox = ctk.CTkFrame(hrow, fg_color="transparent")
        tbox.pack(side="left")
        ctk.CTkLabel(tbox, text=f"เปิด {side} XAUUSD ทันที", font=f(18, "bold"), text_color=self.color).pack(anchor="w")
        ctk.CTkLabel(tbox, text=f"Lot {d['lot']:.2f} (ตั้งที่แผงควบคุม)" if d else "", font=f(11), text_color=COLOR_TEXT_MUTED).pack(anchor="w")
        pbox = ctk.CTkFrame(hrow, fg_color="transparent")
        pbox.pack(side="right")
        self.lbl_px = ctk.CTkLabel(pbox, text="—", font=f(20, "bold", app_fonts.MONO), text_color=COLOR_TEXT_PRIMARY)
        self.lbl_px.pack(anchor="e")
        self.lbl_spread = ctk.CTkLabel(pbox, text="", font=f(10), text_color=COLOR_TEXT_MUTED)
        self.lbl_spread.pack(anchor="e")
        if not d:
            ctk.CTkLabel(self, text="เชื่อมต่อ MT5 ไม่ได้ — เปิด MetaTrader 5 ค้างไว้แล้วลองใหม่", font=f(12),
                         text_color=COLOR_DANGER_RED).pack(padx=30, pady=30)
            self._place(460)
            return
        self.d = d

        # ── ตั้ง SL / TP
        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        card.pack(fill="x", padx=18, pady=(14, 0))
        card.grid_columnconfigure(1, weight=1)
        self.sl_var = tk.StringVar(value=f"{d['sl_pts']:.2f}")
        self.tp_var = tk.StringVar(value=f"{d['tp_pts']:.2f}")
        self._stepper(card, 0, "Stop Loss", "ระยะ (จุด)", self.sl_var, COLOR_DANGER_RED)
        self.tp_row = self._stepper(card, 1, "Take Profit", "ระยะ (จุด)", self.tp_var, COLOR_SUCCESS_GREEN)
        chips = ctk.CTkFrame(card, fg_color="transparent")
        chips.grid(row=2, column=0, columnspan=3, sticky="w", padx=14, pady=(2, 4))
        ctk.CTkLabel(chips, text="SL ด่วน:", font=f(11), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))
        for mult in (0.5, 1.0, 1.5):
            ctk.CTkButton(chips, text=f"{mult:g} ATR", width=62, height=24, font=f(11, "bold"), corner_radius=12,
                          fg_color="#1A1E27", hover_color="#262B36", border_width=1, border_color=COLOR_CARD_BORDER,
                          text_color=COLOR_TEXT_PRIMARY, command=lambda m=mult: self._preset(m)).pack(side="left", padx=2)
        self.no_tp = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(card, text="ไม่ตั้ง TP — ปล่อยกำไรวิ่ง (ปิดเองหรือให้บอทดูแล)", variable=self.no_tp, font=f(11),
                        text_color=COLOR_TEXT_MUTED, fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK,
                        checkbox_width=17, checkbox_height=17, command=self._refresh
                        ).grid(row=3, column=0, columnspan=3, sticky="w", padx=14, pady=(2, 12))
        for v in (self.sl_var, self.tp_var):
            v.trace_add("write", lambda *_: self._refresh())

        # ── สรุปก่อนยืนยัน
        summ = ctk.CTkFrame(self, fg_color="#101218", corner_radius=12)
        summ.pack(fill="x", padx=18, pady=(10, 0))
        summ.grid_columnconfigure((0, 1, 2), weight=1, uniform="q_sum")
        self.sum_cells = {}
        for col, (key, title, color) in enumerate((("sl", "SL", COLOR_DANGER_RED), ("entry", "ราคาเข้า", COLOR_TEXT_PRIMARY),
                                                   ("tp", "TP", COLOR_SUCCESS_GREEN))):
            box = ctk.CTkFrame(summ, fg_color="transparent")
            box.grid(row=0, column=col, sticky="nsew", pady=10)
            ctk.CTkLabel(box, text=title, font=f(10), text_color=COLOR_TEXT_MUTED).pack()
            v = ctk.CTkLabel(box, text="—", font=f(14, "bold", app_fonts.MONO), text_color=color)
            v.pack()
            sub = ctk.CTkLabel(box, text="", font=f(10, "bold"), text_color=color)
            sub.pack()
            self.sum_cells[key] = (v, sub)
        self.lbl_rrr = ctk.CTkLabel(self, text="", font=f(11, "bold"), text_color=COLOR_GOLD_PRIMARY)
        self.lbl_rrr.pack(pady=(8, 0))
        ctk.CTkLabel(self, text="บอทดูแลไม้นี้ต่อ: เลื่อน SL ทุกกำไร 5 จุด (50% / 40%) · ล็อกกำไร · AI กลับทิศ · ปิดเมื่อกำไรถึงเป้า",
                     font=f(10), text_color=COLOR_TEXT_MUTED).pack(pady=(2, 0))
        self.lbl_status = ctk.CTkLabel(self, text="", font=f(12, "bold"), text_color=COLOR_TEXT_MUTED, wraplength=420)
        self.lbl_status.pack(pady=(4, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=(10, 18))
        ctk.CTkButton(btns, text="ยกเลิก", width=100, height=42, font=f(13), fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_HOVER,
                      border_width=1, border_color=COLOR_CARD_BORDER, text_color=COLOR_TEXT_MUTED, command=self.destroy).pack(side="right")
        self.btn_ok = ctk.CTkButton(btns, text=f"ยืนยันเปิด {side}", height=42, font=f(14, "bold"),
                                    fg_color=self.color, hover_color="#2BB383" if buy else "#E05A5A", text_color="#0A0B0F",
                                    command=self._confirm)
        self.btn_ok.pack(side="right", fill="x", expand=True, padx=(0, 10))
        self.bind("<Escape>", lambda e: self.destroy())
        self._place(470)
        self.grab_set()
        self._refresh()
        self._tick()

    def _place(self, w):
        self.update_idletasks()
        h = self.winfo_reqheight()
        x = self.parent.winfo_rootx() + max(0, (self.parent.winfo_width() - w) // 2)
        y = self.parent.winfo_rooty() + max(0, (self.parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _stepper(self, parent, row, title, sub, var, color):
        f = self.f
        lab = ctk.CTkFrame(parent, fg_color="transparent")
        lab.grid(row=row, column=0, sticky="w", padx=14, pady=(12 if row == 0 else 6, 0))
        ctk.CTkLabel(lab, text=title, font=f(13, "bold"), text_color=color).pack(anchor="w")
        ctk.CTkLabel(lab, text=sub, font=f(10), text_color=COLOR_TEXT_MUTED).pack(anchor="w")
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=2, sticky="e", padx=14, pady=(12 if row == 0 else 6, 0))

        def step(delta):
            try:
                v = max(0.1, float(var.get()) + delta)
            except ValueError:
                v = 1.0
            var.set(f"{v:.2f}")
        btn = dict(width=32, height=32, font=f(16, "bold"), fg_color="#1A1E27", hover_color="#262B36",
                   border_width=1, border_color=COLOR_CARD_BORDER, text_color=COLOR_TEXT_PRIMARY)
        b1 = ctk.CTkButton(box, text="−", command=lambda: step(-0.5), **btn)
        b1.pack(side="left")
        ent = ctk.CTkEntry(box, textvariable=var, width=86, height=32, justify="center", font=f(14, "bold", app_fonts.MONO))
        ent.pack(side="left", padx=4)
        b2 = ctk.CTkButton(box, text="+", command=lambda: step(0.5), **btn)
        b2.pack(side="left")
        return (b1, ent, b2)

    def _preset(self, mult):
        sl = self.d["atr"] * mult
        self.sl_var.set(f"{sl:.2f}")
        if not self.no_tp.get():
            self.tp_var.set(f"{sl * 1.5:.2f}")

    def _vals(self):
        try:
            sl = float(self.sl_var.get())
        except ValueError:
            sl = -1
        try:
            tp = 0.0 if self.no_tp.get() else float(self.tp_var.get())
        except ValueError:
            tp = -1
        return sl, tp

    def _tick(self):
        """อัปเดตราคา Bid/Ask ทุก 1 วินาที"""
        try:
            if not self.winfo_exists():
                return   # ปิดหน้าต่างแล้ว
        except Exception:
            return
        try:
            import MetaTrader5 as _mt5
            t = _mt5.symbol_info_tick("XAUUSD")
            if t:
                self.d["bid"], self.d["ask"] = float(t.bid), float(t.ask)
                self._refresh()
        except Exception:
            pass
        try:
            self.after(1000, self._tick)   # ตั้งรอบถัดไปเสมอ (เดิม error ครั้งเดียวทำให้ราคาในหน้าต่างยืนยันค้าง)
        except Exception:
            pass

    def _refresh(self):
        if not hasattr(self, "sum_cells"):
            return
        state = "disabled" if self.no_tp.get() else "normal"
        for w in self.tp_row:
            w.configure(state=state)
        price = self.d["ask"] if self.buy else self.d["bid"]
        self.lbl_px.configure(text=f"{price:,.2f}")
        self.lbl_spread.configure(text=f"{'Ask' if self.buy else 'Bid'} · Spread {round((self.d['ask'] - self.d['bid']) * 100)} pts")
        sl, tp = self._vals()
        if sl <= 0 or tp < 0:
            self.lbl_rrr.configure(text="ใส่ระยะ SL / TP เป็นตัวเลขมากกว่า 0", text_color=COLOR_DANGER_RED)
            self.btn_ok.configure(state="disabled")
            return
        lot = self.d["lot"]
        d = 1 if self.buy else -1
        sl_px, tp_px = price - d * sl, (price + d * tp) if tp > 0 else 0
        risk, reward = sl * lot * 100, tp * lot * 100   # XAUUSD: 1 จุด × 0.01 lot ≈ 1 หน่วยเงิน
        self.sum_cells["sl"][0].configure(text=f"{sl_px:,.2f}")
        self.sum_cells["sl"][1].configure(text=f"เสี่ยง -{risk:,.2f}")
        self.sum_cells["entry"][0].configure(text=f"{price:,.2f}")
        self.sum_cells["entry"][1].configure(text=self.side, text_color=self.color)
        self.sum_cells["tp"][0].configure(text=f"{tp_px:,.2f}" if tp > 0 else "ไม่ตั้ง")
        self.sum_cells["tp"][1].configure(text=f"เป้า +{reward:,.2f}" if tp > 0 else "ปล่อยกำไรวิ่ง")
        self.lbl_rrr.configure(text=(f"Risk : Reward = 1 : {tp / sl:.2f}" if tp > 0 else "Risk : Reward = ไม่จำกัด (ไม่ตั้ง TP)") +
                               f"  ·  ATR M15 = {self.d['atr']:.2f}", text_color=COLOR_GOLD_PRIMARY)
        self.btn_ok.configure(state="normal")

    def _confirm(self):
        sl, tp = self._vals()
        self.btn_ok.configure(state="disabled", text="กำลังส่งคำสั่ง...")
        self.update_idletasks()
        ok, msg = bot_ctrl.quick_order(self.side, sl, tp)
        if ok:
            self.lbl_status.configure(text=f"✓ {msg}", text_color=COLOR_SUCCESS_GREEN)
            self.after(1500, self.destroy)
        else:
            self.lbl_status.configure(text=f"✗ {msg}", text_color=COLOR_DANGER_RED)
            self.btn_ok.configure(state="normal", text=f"ยืนยันเปิด {self.side}")
            self._place(470)


class MarketExplainDialog(ctk.CTkToplevel):
    """อธิบายว่าทำไมสภาวะตลาด H1/H4 เป็น Uptrend / Downtrend / Sideway และแต่ละแผนใช้ค่าไหน"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("สภาวะตลาด — ทำไมถึงเป็นแบบนี้")
        w, h = 640, 600
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        apply_dark_title_bar(self)

        def f(size, weight="normal", family=app_fonts.UI):
            return ctk.CTkFont(family=family, size=size, weight=weight)

        ctk.CTkLabel(self, text="สภาวะตลาด — ทำไมถึงเป็นแบบนี้", font=f(17, "bold"), text_color=COLOR_GOLD_PRIMARY).pack(anchor="w", padx=20, pady=(16, 0))
        ctk.CTkLabel(self, text="คำนวณจากแท่งที่ปิดแล้ว · ตัวเลขเป็นค่าเฉลี่ยเคลื่อนที่ (MA) ของราคาปิด", font=f(11),
                     text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=20, pady=(0, 8))
        box = ctk.CTkScrollableFrame(self, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        data = bot_ctrl.get_market_explain()
        if not data:
            ctk.CTkLabel(box, text="เชื่อมต่อ MT5 ไม่ได้ — เปิด MetaTrader 5 ค้างไว้แล้วลองใหม่", font=f(12), text_color=COLOR_DANGER_RED).pack(pady=30)
            return
        green, red, cyan, muted = COLOR_SUCCESS_GREEN, COLOR_DANGER_RED, COLOR_CYAN_ACCENT, COLOR_TEXT_MUTED

        def card(title):
            c = ctk.CTkFrame(box, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
            c.pack(fill="x", pady=5, padx=4)
            ctk.CTkLabel(c, text=title, font=f(13, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(10, 2))
            return c

        def line(parent, text, color=COLOR_TEXT_PRIMARY, size=12, mono=False):
            ctk.CTkLabel(parent, text=text, font=f(size, "normal", app_fonts.MONO if mono else app_fonts.UI), text_color=color,
                         anchor="w", justify="left", wraplength=570).pack(anchor="w", padx=14)

        # 1) ป้ายบนการ์ด: MA50 / MA100 / MA150
        for tf in ("H1", "H4"):
            d = data.get(tf)
            if not d:
                continue
            m = d["ma"]
            up = m[50] > m[100] > m[150]
            dn = m[50] < m[100] < m[150]
            word, col = ("▲ Uptrend", green) if up else ("▼ Downtrend", red) if dn else ("◆ Sideway", cyan)
            c = card(f"{tf} : {word}")
            c.winfo_children()[0].configure(text_color=col)
            line(c, f"MA50  {m[50]:,.2f}   {'>' if m[50] > m[100] else '<'}   MA100  {m[100]:,.2f}   {'>' if m[100] > m[150] else '<'}   MA150  {m[150]:,.2f}", mono=True)
            if up:
                why = "MA50 > MA100 > MA150 เรียงจากเร็วไปช้าครบ = ราคาเฉลี่ยระยะสั้นสูงกว่าระยะยาวทุกช่วง → ขาขึ้น"
            elif dn:
                why = "MA50 < MA100 < MA150 เรียงลงครบ = ราคาเฉลี่ยระยะสั้นต่ำกว่าระยะยาวทุกช่วง → ขาลง"
            else:
                why = "เส้น MA ยังไม่เรียงตัวทางเดียวกันครบ (สลับกัน) = ตลาดยังไม่มีทิศชัด → ไซด์เวย์"
            line(c, why, muted, 11)
            line(c, f"% บนการ์ด = MA50 ห่างจาก MA150 {(m[50] / m[150] - 1) * 100:+.2f}% (ยิ่งห่าง เทรนด์ยิ่งแรง)", muted, 11)
            ctk.CTkFrame(c, height=8, fg_color="transparent").pack()

        # 2) สิ่งที่แต่ละแผนใช้จริง
        c = card("แต่ละแผนใช้เทรนด์อะไรตัดสินใจ")
        h1, h4 = data.get("H1"), data.get("H4")
        if h1:
            m = h1["ma"]
            st = 1 if m[100] > m[150] > m[200] else (-1 if m[100] < m[150] < m[200] else 0)
            line(c, f"Plan 1 (MA M15) — H1 MA100 {m[100]:,.2f} · MA150 {m[150]:,.2f} · MA200 {m[200]:,.2f}", COLOR_TEXT_PRIMARY, 12)
            line(c, ("→ เรียงขาขึ้น: เข้าได้เฉพาะ BUY" if st > 0 else "→ เรียงขาลง: เข้าได้เฉพาะ SELL" if st < 0
                     else "→ ยังไม่เรียงตัว: Plan 1 ยังไม่เข้าไม้"), green if st > 0 else red if st < 0 else muted, 11)
        if h4:
            m = h4["ma"]
            dp = h4["diff_pct"]
            line(c, f"Plan 3–5 (ป้ายมุมขวาของการ์ด) — H4 MA10 {m[10]:,.2f} เทียบ MA30 {m[30]:,.2f} ห่าง {dp:+.2f}%", COLOR_TEXT_PRIMARY, 12)
            if abs(dp) < 0.20:
                line(c, "→ ห่างไม่ถึง ±0.20% = ไซด์เวย์ เทรดได้ทั้ง BUY / SELL", cyan, 11)
            else:
                line(c, f"→ ห่างเกิน ±0.20% = {'ขาขึ้น: BUY เท่านั้น' if dp > 0 else 'ขาลง: SELL เท่านั้น'} (Strict Pro-Trend ห้ามสวนเทรนด์)",
                     green if dp > 0 else red, 11)
            above = h4["close"] > m[200]
            line(c, f"Plan 2 (MA H1) / ป้าย MA200 — ราคาปิด H4 {h4['close']:,.2f} {'เหนือ' if above else 'ใต้'} MA200 {m[200]:,.2f}", COLOR_TEXT_PRIMARY, 12)
            line(c, "→ Plan 2 BUY ได้เมื่อราคาอยู่เหนือ MA200 และ SELL ได้เมื่ออยู่ใต้ MA200 (ร่วมกับ MA10/30 และความชัน MA5 H4)", muted, 11)
        ctk.CTkFrame(c, height=8, fg_color="transparent").pack()
        ctk.CTkLabel(box, text="ป้าย Uptrend / Downtrend / Sideway บนการ์ดใช้แสดงภาพรวมเท่านั้น — การเข้าไม้ใช้กฎของแต่ละแผนด้านบน",
                     font=f(10), text_color=muted, wraplength=580, justify="left").pack(anchor="w", padx=8, pady=(6, 0))


class GoldCandleDialog(ctk.CTkToplevel):
    """กราฟแท่งเทียน XAUUSD เรียลไทม์: เลือก Timeframe M15 / H1 / H4 พร้อมอินดิเคเตอร์แยกตามแผน และปุ่มคลิกเปิด/ปิดแสดงผลแต่ละตัว"""

    BARS = 120   # ค่าเริ่มต้น (ปรับได้ที่ตัวเลือก "จำนวนแท่ง")
    BAR_CHOICES = ("16", "30", "50", "80", "120", "200", "300", "500")
    REFRESH_MS = 1000

    PLAN_SPECS = [
        ("ALL", "รวมทุกแผน", None, None),
        ("P1", "P1 · M15", "M15", ["ma5", "ma13", "ma50"]),
        ("P2", "P2 · H1", "H1", ["h1_ma5", "h1_ma10", "h1_ma20"]),
        ("P3", "P3 · H1 (SMC)", "H1", ["resistance", "support"]),
        ("P4", "P4 · H1 (SR)", "H1", ["resistance", "support"]),
        ("P5", "P5 · H1 (BB)", "H1", ["h1_bb"]),
        ("P6", "P6 · H1 (PSAR)", "H1", ["h1_sar", "h1_ema100"]),
        ("H4", "เทรนด์ H4", "H4", ["h4_ma10", "h4_ma30", "h4_ma200", "resistance", "support"]),
    ]

    INDICATOR_DEFS = {
        "M15": [
            ("ma5", "P1 · ━ MA5", COLOR_CYAN_ACCENT),
            ("ma13", "P1 · ━ MA13", COLOR_GOLD_WARM),
            ("ma50", "P1 · ┅ MA50", "#A78BFA"),
            ("orders", "┅ ไม้เปิด & TP/SL", COLOR_CYAN_ACCENT),
        ],
        "H1": [
            ("h1_ma5", "P2 · ━ MA5", "#34D399"),
            ("h1_ma10", "P2 · ━ MA10", "#FBBF24"),
            ("h1_ma20", "P2 · ┅ MA20", "#818CF8"),
            ("resistance", "P3/P4 · ┅ แนวต้าน", COLOR_DANGER_RED),
            ("support", "P3/P4 · ┅ แนวรับ", COLOR_SUCCESS_GREEN),
            ("h1_bb", "P5 · ━ BB H1", "#C084FC"),
            ("h1_sar", "P6 · • SAR H1", "#FB7185"),
            ("h1_ema100", "P6 · ┅ EMA100", "#60A5FA"),
            ("orders", "┅ ไม้เปิด & TP/SL", COLOR_CYAN_ACCENT),
        ],
        "H4": [
            ("h4_ma10", "H4 · ━ MA10", "#FBBF24"),
            ("h4_ma30", "H4 · ━ MA30", "#FB923C"),
            ("h4_ma200", "H4 · ┅ MA200", "#A78BFA"),
            ("resistance", "H4 · ┅ แนวต้าน", COLOR_DANGER_RED),
            ("support", "H4 · ┅ แนวรับ", COLOR_SUCCESS_GREEN),
            ("orders", "┅ ไม้เปิด & TP/SL", COLOR_CYAN_ACCENT),
        ],
    }

    def __init__(self, parent, default_tf=None, default_bars=None, default_plan=None):
        super().__init__(parent)
        w, h = 1100, 680
        self.configure(fg_color=COLOR_BG_DARK)
        self.after(10, self.lift)
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(720, 460)
        apply_dark_title_bar(self)
        self.data, self.slots, self._job = None, [], None

        # สถานะเปิด/ปิดแสดงผลของแต่ละอินดิเคเตอร์ตามแผนที่เปิดใช้งานจริง
        p1 = plan_config.is_enabled("MA-Cross-Trend")
        p2 = plan_config.is_enabled("MA-Cross-H1-Trend")
        p3 = plan_config.is_enabled("SMC-LiquidityHunt")
        p4 = plan_config.is_enabled("SR-SwingBounce")
        p5 = plan_config.is_enabled("BB-H1-Reversion")
        p6 = plan_config.is_enabled("PSAR-H1-Trend")

        # เลือกแผนเริ่มต้นตามพารามิเตอร์ หรือตามแผนที่เปิดใช้งานจริง
        if default_plan:
            self.selected_plan = default_plan
            spec = next((item for item in self.PLAN_SPECS if item[0] == default_plan), None)
            init_tf = default_tf or (spec[2] if spec and spec[2] else "H1")
        elif default_tf:
            init_tf = default_tf
            if init_tf == "H1":
                self.selected_plan = "P3" if (p3 or p4) else ("P2" if p2 else "ALL")
            elif init_tf == "H4":
                self.selected_plan = "H4"
            else:
                self.selected_plan = "P1"
        else:
            if p1:
                self.selected_plan = "P1"
                init_tf = "M15"
            elif p2:
                self.selected_plan = "P2"
                init_tf = "H1"
            elif p3:
                self.selected_plan = "P3"
                init_tf = "H1"
            elif p4:
                self.selected_plan = "P4"
                init_tf = "H1"
            elif p5:
                self.selected_plan = "P5"
                init_tf = "H1"
            elif p6:
                self.selected_plan = "P6"
                init_tf = "H1"
            else:
                self.selected_plan = "ALL"
                init_tf = "M15"

        plan_desc = ""
        for pk, plabel, _, _ in self.PLAN_SPECS:
            if pk == self.selected_plan:
                plan_desc = f" ({plabel})"
                break
        self.title(f"XAUUSD · {init_tf} เรียลไทม์{plan_desc}")

        # ปรับเปิด/ปิดอินดิเคเตอร์ตามแผนที่เลือก
        target_spec = next((item for item in self.PLAN_SPECS if item[0] == self.selected_plan), None)
        ind_keys = target_spec[3] if target_spec and target_spec[3] is not None else None

        self.ind_toggles = {
            "ma5": True, "ma13": True, "ma50": True,
            "h1_ma5": p2, "h1_ma10": p2, "h1_ma20": p2,
            "resistance": (p3 or p4), "support": (p3 or p4),
            "h1_bb": p5,
            "h1_sar": p6, "h1_ema100": p6,
            "h4_ma10": True, "h4_ma30": True, "h4_ma200": True,
            "orders": True,
        }
        if ind_keys is not None:
            for k in list(self.ind_toggles.keys()):
                if k != "orders":
                    self.ind_toggles[k] = (k in ind_keys)

        self.plan_buttons = {}
        self.ind_buttons = {}
        self.ind_colors = {}
        self.tf_var = tk.StringVar(value=init_tf)
        self.bars_var = tk.StringVar(value=str(default_bars or self.BARS))

        # --- แถวบน: สัญลักษณ์, Timeframe, ราคา, จำนวนแท่ง, ไม้เปิด, เต็มจอ ---
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(10, 4))

        # กลุ่มซ้าย: XAUUSD + เลือก Timeframe + ราคา Live + การเปลี่ยนแปลง
        left_grp = ctk.CTkFrame(top, fg_color="transparent")
        left_grp.pack(side="left", fill="y")

        self.lbl_sym = ctk.CTkLabel(left_grp, text="XAUUSD", font=ctk.CTkFont(family=app_fonts.UI, size=18, weight="bold"),
                                    text_color=COLOR_GOLD_PRIMARY)
        self.lbl_sym.pack(side="left", padx=(0, 10))

        self.seg_tf = ctk.CTkSegmentedButton(left_grp, values=["M15", "H1", "H4"], variable=self.tf_var,
                                            font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"),
                                            height=26, selected_color=COLOR_GOLD_WARM, selected_hover_color=COLOR_GOLD_DARK,
                                            command=self._on_tf_change)
        self.seg_tf.pack(side="left", padx=(0, 12))

        self.lbl_price = ctk.CTkLabel(left_grp, text="—", font=ctk.CTkFont(family=app_fonts.UI, size=18, weight="bold"),
                                      text_color=COLOR_TEXT_PRIMARY)
        self.lbl_price.pack(side="left", padx=(0, 8))

        self.lbl_change = ctk.CTkLabel(left_grp, text="", font=ctk.CTkFont(family=app_fonts.UI, size=12))
        self.lbl_change.pack(side="left")

        # กลุ่มขวา: ปุ่มเต็มจอ + นาฬิกา + กำไรไม้ + จำนวนแท่ง
        right_grp = ctk.CTkFrame(top, fg_color="transparent")
        right_grp.pack(side="right", fill="y")

        self.btn_full = ctk.CTkButton(right_grp, text="ขยายเต็มจอ", width=92, height=26,
                                      font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"),
                                      fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_HOVER, border_width=1,
                                      border_color=COLOR_CARD_BORDER, text_color=COLOR_GOLD_PRIMARY,
                                      command=self._toggle_full)
        self.btn_full.pack(side="right", padx=(8, 0))
        self.bind("<F11>", lambda e: self._toggle_full())
        self.bind("<Escape>", lambda e: self.state() == "zoomed" and self._toggle_full())

        self.lbl_clock = ctk.CTkLabel(right_grp, text="", font=ctk.CTkFont(family=app_fonts.UI, size=11), text_color=COLOR_TEXT_MUTED)
        self.lbl_clock.pack(side="right", padx=(8, 4))

        self.lbl_pnl = ctk.CTkLabel(right_grp, text="", font=ctk.CTkFont(family=app_fonts.UI, size=12, weight="bold"),
                                    corner_radius=8, height=26)
        self.lbl_pnl.pack(side="right", padx=(8, 4))

        ctk.CTkSegmentedButton(right_grp, values=list(self.BAR_CHOICES), variable=self.bars_var,
                               font=ctk.CTkFont(family=app_fonts.UI, size=11), height=26,
                               selected_color=COLOR_GOLD_WARM, selected_hover_color=COLOR_GOLD_DARK,
                               command=lambda v: self._tick(reschedule=False)).pack(side="right", padx=(4, 0))
        ctk.CTkLabel(right_grp, text="แท่ง:", font=ctk.CTkFont(family=app_fonts.UI, size=11), text_color=COLOR_TEXT_MUTED).pack(side="right")

        # --- แถวสอง: แถบเลือกตามแผน (Plan Selector Bar) ---
        plan_bar = ctk.CTkFrame(self, fg_color="transparent")
        plan_bar.pack(fill="x", padx=18, pady=(2, 3))

        ctk.CTkLabel(plan_bar, text="เลือกดูตามแผน:", font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"),
                     text_color=COLOR_GOLD_PRIMARY).pack(side="left", padx=(0, 8))

        self.plan_box = ctk.CTkFrame(plan_bar, fg_color="transparent")
        self.plan_box.pack(side="left", fill="x", expand=True)

        self._build_plan_buttons()

        # --- แถวสาม: แถบอินดิเคเตอร์แบบคลิกเปิด/ปิดได้ (Indicator Toolbar) ---
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=18, pady=(2, 6))

        ctk.CTkLabel(toolbar, text="อินดิเคเตอร์:", font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"),
                     text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 8))

        self.legend_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        self.legend_box.pack(side="left", fill="x", expand=True)

        # ปุ่มเปิด/ปิดทั้งหมด
        all_box = ctk.CTkFrame(toolbar, fg_color="transparent")
        all_box.pack(side="right")
        ctk.CTkButton(all_box, text="เปิดหมด", width=52, height=22, font=ctk.CTkFont(family=app_fonts.UI, size=10),
                      fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_HOVER, border_width=1, border_color=COLOR_CARD_BORDER,
                      text_color=COLOR_TEXT_MUTED, command=lambda: self._set_all_indicators(True)).pack(side="left", padx=(0, 4))
        ctk.CTkButton(all_box, text="ปิดหมด", width=52, height=22, font=ctk.CTkFont(family=app_fonts.UI, size=10),
                      fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_HOVER, border_width=1, border_color=COLOR_CARD_BORDER,
                      text_color=COLOR_TEXT_MUTED, command=lambda: self._set_all_indicators(False)).pack(side="left")

        # สร้างปุ่มอินดิเคเตอร์เริ่มต้น
        self._rebuild_legend_chips()

        # --- แถวสี่: แถบสถานะเงื่อนไขการเข้าไม้เรียลไทม์ (Condition Status Bar) ---
        self.cond_frame = ctk.CTkFrame(self, fg_color="#0F131C", corner_radius=8, border_width=1, border_color="#1E2638", height=30)
        self.cond_frame.pack(fill="x", padx=18, pady=(0, 3))

        self.cond_left = ctk.CTkFrame(self.cond_frame, fg_color="transparent")
        self.cond_left.pack(side="left", padx=(10, 6), fill="y")

        self.lbl_cond_title = ctk.CTkLabel(
            self.cond_left, text="⚡ เงื่อนไขเข้าไม้:",
            font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"),
            text_color=COLOR_GOLD_PRIMARY
        )
        self.lbl_cond_title.pack(side="left", padx=(0, 4))

        self.lbl_cond_score = ctk.CTkLabel(
            self.cond_left, text=" กำลังโหลด... ",
            font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY,
            corner_radius=4, height=20
        )
        self.lbl_cond_score.pack(side="left")

        self.cond_chips_box = ctk.CTkFrame(self.cond_frame, fg_color="transparent")
        self.cond_chips_box.pack(side="left", fill="both", expand=True, padx=(4, 8))

        # --- แถวห้า: แถบ AI แนะนำแนวรับแนวต้านสำคัญที่ต้องโฟกัส (AI S&R Focus Bar) ---
        self.ai_sr_frame = ctk.CTkFrame(self, fg_color="#101520", corner_radius=8, border_width=1, border_color="#2D2415", height=28)
        self.ai_sr_frame.pack(fill="x", padx=18, pady=(0, 4))

        self.lbl_ai_sr_title = ctk.CTkLabel(
            self.ai_sr_frame, text="🤖 AI โฟกัสแนวรับ–ต้าน:",
            font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"),
            text_color=COLOR_GOLD_PRIMARY
        )
        self.lbl_ai_sr_title.pack(side="left", padx=(10, 8))

        self.lbl_ai_res_badge = ctk.CTkLabel(
            self.ai_sr_frame, text=" 🎯 ต้าน: — ",
            font=ctk.CTkFont(family=app_fonts.UI, size=10, weight="bold"),
            fg_color="#261215", text_color="#FCA5A5", corner_radius=5, height=20,
            padx=8
        )
        self.lbl_ai_res_badge.pack(side="left", padx=(0, 6))

        self.lbl_ai_sup_badge = ctk.CTkLabel(
            self.ai_sr_frame, text=" 🎯 รับ: — ",
            font=ctk.CTkFont(family=app_fonts.UI, size=10, weight="bold"),
            fg_color="#0D261B", text_color="#6EE7B7", corner_radius=5, height=20,
            padx=8
        )
        self.lbl_ai_sup_badge.pack(side="left", padx=(0, 8))

        self.lbl_ai_action = ctk.CTkLabel(
            self.ai_sr_frame, text="กำลังวิเคราะห์โซนราคา...",
            font=ctk.CTkFont(family=app_fonts.UI, size=10),
            text_color="#94A3B8"
        )
        self.lbl_ai_action.pack(side="left", padx=(0, 8))

        # --- กล่องกราฟ Canvas ---
        box = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        box.pack(fill="both", expand=True, padx=18, pady=4)
        self.canvas = tk.Canvas(box, bg=COLOR_CARD_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<Motion>", self._hover)
        self.canvas.bind("<Leave>", lambda e: self.lbl_tip.configure(text=self.tip_default))
        self.tip_default = "อัปเดตทุก 1 วินาที · เลือกดูตามแผน (P1-P6) หรือคลิกเปิด/ปิดแต่ละอินดิเคเตอร์ · ชี้ที่แท่งเพื่อดูราคาและค่า"
        self.lbl_tip = ctk.CTkLabel(self, text=self.tip_default, font=ctk.CTkFont(family=app_fonts.UI, size=12), text_color=COLOR_TEXT_MUTED)
        self.lbl_tip.pack(pady=(2, 8))
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._tick()

    def _build_plan_buttons(self):
        for w in self.plan_box.winfo_children():
            w.destroy()
        self.plan_buttons = {}

        for plan_key, label, tf, _ in self.PLAN_SPECS:
            is_active = (self.selected_plan == plan_key)
            btn = ctk.CTkButton(
                self.plan_box,
                text=label,
                width=0,
                height=24,
                corner_radius=6,
                font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold" if is_active else "normal"),
                fg_color="#3B2E15" if is_active else COLOR_CARD_BG,
                hover_color=COLOR_CARD_HOVER,
                border_width=1.5 if is_active else 1,
                border_color=COLOR_GOLD_PRIMARY if is_active else COLOR_CARD_BORDER,
                text_color=COLOR_GOLD_PRIMARY if is_active else COLOR_TEXT_MUTED,
                command=lambda pk=plan_key: self._select_plan(pk)
            )
            btn.pack(side="left", padx=(0, 5))
            self.plan_buttons[plan_key] = btn

    def _refresh_plan_buttons(self, plans_status=None):
        if plans_status:
            self._last_plans_status = plans_status
        else:
            plans_status = getattr(self, "_last_plans_status", {}) or {}

        for plan_key, btn in self.plan_buttons.items():
            is_active = (self.selected_plan == plan_key)
            spec = next((item for item in self.PLAN_SPECS if item[0] == plan_key), None)
            base_label = spec[1] if spec else plan_key

            pinfo = plans_status.get(plan_key)
            badge_text = ""
            is_ready = False
            if pinfo and plan_key not in ("ALL", "H4"):
                m = pinfo.get("matched", 0)
                tot = pinfo.get("total", 4)
                is_ready = (m == tot and tot > 0)
                badge_text = f" (★ {m}/{tot})" if is_ready else f" ({m}/{tot})"

            full_label = f"{base_label}{badge_text}"

            if is_ready:
                btn.configure(
                    text=full_label,
                    fg_color="#0F2E22" if is_active else "#081E15",
                    border_color=COLOR_SUCCESS_GREEN,
                    border_width=2 if is_active else 1.5,
                    text_color=COLOR_SUCCESS_GREEN,
                    font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold")
                )
            elif is_active:
                btn.configure(
                    text=full_label,
                    fg_color="#3B2E15",
                    border_color=COLOR_GOLD_PRIMARY,
                    border_width=1.5,
                    text_color=COLOR_GOLD_PRIMARY,
                    font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold")
                )
            else:
                btn.configure(
                    text=full_label,
                    fg_color=COLOR_CARD_BG,
                    border_color=COLOR_CARD_BORDER,
                    border_width=1,
                    text_color=COLOR_TEXT_MUTED,
                    font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="normal")
                )

    def _update_condition_bar(self, plans_status=None):
        if not hasattr(self, "cond_frame"):
            return
        if plans_status:
            self._last_plans_status = plans_status
        else:
            plans_status = getattr(self, "_last_plans_status", {}) or {}

        if not plans_status:
            self.lbl_cond_title.configure(text="⚡ เงื่อนไขเข้าไม้:", text_color=COLOR_GOLD_PRIMARY)
            self.lbl_cond_score.configure(text=" กำลังวิเคราะห์สัญญาณ... ", fg_color="#18202F", text_color=COLOR_TEXT_MUTED)
            return

        for w in self.cond_chips_box.winfo_children():
            w.destroy()

        cur_plan = self.selected_plan

        if cur_plan == "ALL":
            self.lbl_cond_title.configure(text="⚡ สถานะทุกแผน:", text_color=COLOR_GOLD_PRIMARY)
            self.lbl_cond_score.configure(text=" (คลิกดูรายละเอียด) ", fg_color="transparent", text_color=COLOR_TEXT_MUTED)

            for pk in ("P1", "P2", "P3", "P4", "P5", "P6"):
                pinfo = plans_status.get(pk)
                if not pinfo:
                    continue
                m = pinfo["matched"]
                tot = pinfo["total"]
                pct = pinfo["pct"]
                side = pinfo["side"]
                side_tag = "▲" if side == "BUY" else "▼"
                is_ready = (m == tot and tot > 0)
                if is_ready:
                    chip_fg = "#064E3B"
                    chip_border = COLOR_SUCCESS_GREEN
                    chip_text = COLOR_SUCCESS_GREEN
                    label_txt = f"★ {pk} {side_tag}: {m}/{tot} (ครบ)"
                elif pct >= 50:
                    chip_fg = "#231F10"
                    chip_border = COLOR_GOLD_PRIMARY
                    chip_text = COLOR_GOLD_PRIMARY
                    label_txt = f"{pk} {side_tag}: {m}/{tot} ({pct}%)"
                else:
                    chip_fg = "#141722"
                    chip_border = "#2A3447"
                    chip_text = "#94A3B8"
                    label_txt = f"{pk} {side_tag}: {m}/{tot}"

                btn = ctk.CTkButton(
                    self.cond_chips_box,
                    text=label_txt,
                    height=22,
                    width=0,
                    corner_radius=6,
                    fg_color=chip_fg,
                    hover_color=COLOR_CARD_HOVER,
                    border_width=1,
                    border_color=chip_border,
                    text_color=chip_text,
                    font=ctk.CTkFont(family=app_fonts.UI, size=10, weight="bold" if (is_ready or pct >= 50) else "normal"),
                    command=lambda p=pk: self._select_plan(p)
                )
                btn.pack(side="left", padx=(0, 6))

        elif cur_plan in ("P1", "P2", "P3", "P4", "P5", "P6"):
            pinfo = plans_status.get(cur_plan)
            if not pinfo:
                return

            m = pinfo["matched"]
            tot = pinfo["total"]
            pct = pinfo["pct"]
            side = pinfo["side"]
            is_ready = (m == tot and tot > 0)
            side_col = COLOR_SUCCESS_GREEN if side == "BUY" else COLOR_DANGER_RED
            side_icon = "▲ BUY" if side == "BUY" else "▼ SELL"

            self.lbl_cond_title.configure(text=f"⚡ {pinfo['label']} ({side_icon}):", text_color=side_col)

            if is_ready:
                score_txt = f" ★ เข้าครบ {m}/{tot} ข้อ (100% สัญญาณพร้อม) "
                score_bg = "#064E3B"
                score_text_col = COLOR_SUCCESS_GREEN
            elif pct >= 50:
                score_txt = f" เข้าแล้ว {m}/{tot} ข้อ ({pct}%) "
                score_bg = "#231F10"
                score_text_col = COLOR_GOLD_PRIMARY
            else:
                score_txt = f" เข้าแล้ว {m}/{tot} ข้อ ({pct}%) "
                score_bg = "#1A1D27"
                score_text_col = COLOR_TEXT_MUTED

            self.lbl_cond_score.configure(text=score_txt, fg_color=score_bg, text_color=score_text_col)

            for it in pinfo.get("items", []):
                ok = it["ok"]
                mark = "✓" if ok else "✗"
                chip_bg = "#0D2818" if ok else "#251215"
                chip_text_col = "#34D399" if ok else "#F87171"
                chip_label = f"{mark} {it['name']}: {it['desc']}"

                lbl = ctk.CTkLabel(
                    self.cond_chips_box,
                    text=chip_label,
                    height=22,
                    corner_radius=6,
                    fg_color=chip_bg,
                    text_color=chip_text_col,
                    font=ctk.CTkFont(family=app_fonts.UI, size=10, weight="bold" if ok else "normal"),
                    padx=7,
                )
                lbl.pack(side="left", padx=(0, 6))
                lbl.bind("<Enter>", lambda e, d=it["desc"], n=it["name"]: self.lbl_tip.configure(text=f"📌 {n}: {d}"))
                lbl.bind("<Leave>", lambda e: self.lbl_tip.configure(text=self.tip_default))

        elif cur_plan == "H4":
            self.lbl_cond_title.configure(text="⚡ วิเคราะห์เทรนด์ H4:", text_color=COLOR_GOLD_PRIMARY)
            self.lbl_cond_score.configure(text=" (กรอบใหญ่ H4) ", fg_color="transparent", text_color=COLOR_TEXT_MUTED)
            p2_info = plans_status.get("P2", {})
            for it in p2_info.get("items", []):
                if "H4" in it.get("name", ""):
                    ok = it["ok"]
                    mark = "✓" if ok else "✗"
                    lbl = ctk.CTkLabel(
                        self.cond_chips_box,
                        text=f"{mark} {it['name']}: {it['desc']}",
                        height=22,
                        corner_radius=6,
                        fg_color="#0D2818" if ok else "#251215",
                        text_color="#34D399" if ok else "#F87171",
                        font=ctk.CTkFont(family=app_fonts.UI, size=10),
                        padx=7,
                    )
                    lbl.pack(side="left", padx=(0, 6))
                    lbl.bind("<Enter>", lambda e, d=it["desc"], n=it["name"]: self.lbl_tip.configure(text=f"📌 {n}: {d}"))
                    lbl.bind("<Leave>", lambda e: self.lbl_tip.configure(text=self.tip_default))

    def _select_plan(self, plan_key):
        self.selected_plan = plan_key
        target_spec = next((item for item in self.PLAN_SPECS if item[0] == plan_key), None)
        if not target_spec:
            return

        _, label, target_tf, ind_keys = target_spec

        # 1. สลับ Timeframe ให้ตรงกับแผน
        if target_tf and self.tf_var.get() != target_tf:
            self.tf_var.set(target_tf)
            self.seg_tf.set(target_tf)

        cur_tf = self.tf_var.get()

        # 2. ปรับการเปิด/ปิดอินดิเคเตอร์
        if plan_key == "ALL":
            for k, _, _ in self.INDICATOR_DEFS.get(cur_tf, []):
                self.ind_toggles[k] = True
        else:
            tf_keys = [k for k, _, _ in self.INDICATOR_DEFS.get(cur_tf, []) if k != "orders"]
            for k in tf_keys:
                self.ind_toggles[k] = (k in (ind_keys or []))
            self.ind_toggles["orders"] = True

        # 3. อัปเดต Title
        plan_desc = f" ({label})" if plan_key != "ALL" else " (รวมทุกแผน)"
        self.title(f"XAUUSD · {cur_tf} เรียลไทม์{plan_desc}")

        # 4. รีเฟรชปุ่มแผน, ชิปอินดิเคเตอร์, แถบเงื่อนไข และวาดใหม่
        self._refresh_plan_buttons()
        self._rebuild_legend_chips()
        self._update_condition_bar()
        self._tick(reschedule=False)

    def _sync_selected_plan_from_toggles(self):
        cur_tf = self.tf_var.get()
        active_keys = set(k for k, _, _ in self.INDICATOR_DEFS.get(cur_tf, [])
                          if k != "orders" and self.ind_toggles.get(k, False))
        all_keys = set(k for k, _, _ in self.INDICATOR_DEFS.get(cur_tf, []) if k != "orders")

        if active_keys == all_keys:
            self.selected_plan = "ALL"
            return

        for pk, _, ptf, pkeys in self.PLAN_SPECS:
            if ptf == cur_tf and pkeys and set(pkeys) == active_keys:
                self.selected_plan = pk
                return

        self.selected_plan = "CUSTOM"

    def _toggle_full(self):
        """ขยายเต็มจอ ↔ ขนาดปกติ (F11 / Esc)"""
        if self.state() == "zoomed":
            self.state("normal")
            self.btn_full.configure(text="ขยายเต็มจอ")
        else:
            self.state("zoomed")
            self.btn_full.configure(text="ย่อหน้าต่าง")

    def _close(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        self.destroy()

    def _on_tf_change(self, new_tf):
        cur_spec = next((item for item in self.PLAN_SPECS if item[0] == self.selected_plan), None)
        if cur_spec and cur_spec[2] and cur_spec[2] != new_tf:
            if new_tf == "M15":
                self.selected_plan = "P1"
                self.ind_toggles["ma5"] = True
                self.ind_toggles["ma13"] = True
                self.ind_toggles["ma50"] = True
            elif new_tf == "H4":
                self.selected_plan = "H4"
                self.ind_toggles["h4_ma10"] = True
                self.ind_toggles["h4_ma30"] = True
                self.ind_toggles["h4_ma200"] = True
                self.ind_toggles["resistance"] = True
                self.ind_toggles["support"] = True
            elif new_tf == "H1":
                self.selected_plan = "ALL"
                for k, _, _ in self.INDICATOR_DEFS.get("H1", []):
                    self.ind_toggles[k] = True

        plan_desc = ""
        for pk, plabel, ptf, _ in self.PLAN_SPECS:
            if pk == self.selected_plan:
                plan_desc = f" ({plabel})"
                break
        self.title(f"XAUUSD · {new_tf} เรียลไทม์{plan_desc}")
        self._refresh_plan_buttons()
        self._rebuild_legend_chips()
        self._tick(reschedule=False)

    def _rebuild_legend_chips(self):
        for w in self.legend_box.winfo_children():
            w.destroy()
        self.ind_buttons = {}
        self.ind_colors = {}
        tf = self.tf_var.get()
        defs = self.INDICATOR_DEFS.get(tf, self.INDICATOR_DEFS["M15"])
        for key, label, col in defs:
            self.ind_colors[key] = col
            is_on = self.ind_toggles.get(key, True)
            btn = ctk.CTkButton(
                self.legend_box,
                text=label,
                width=0,
                height=22,
                corner_radius=6,
                font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"),
                fg_color="#18202F" if is_on else COLOR_CARD_BG,
                hover_color=COLOR_CARD_HOVER,
                border_width=1,
                border_color=col if is_on else COLOR_CARD_BORDER,
                text_color=col if is_on else "#64748B",
                command=lambda k=key: self._toggle_indicator(k)
            )
            btn.pack(side="left", padx=(0, 6))
            self.ind_buttons[key] = btn

    def _toggle_indicator(self, key):
        self.ind_toggles[key] = not self.ind_toggles.get(key, True)
        self._sync_selected_plan_from_toggles()
        self._refresh_plan_buttons()
        self._refresh_chip_style(key)
        self._draw()

    def _refresh_chip_style(self, key):
        btn = self.ind_buttons.get(key)
        if not btn:
            return
        is_on = self.ind_toggles.get(key, True)
        col = self.ind_colors.get(key, COLOR_TEXT_PRIMARY)
        if is_on:
            btn.configure(fg_color="#18202F", border_color=col, text_color=col, border_width=1)
        else:
            btn.configure(fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, text_color="#64748B", border_width=1)

    def _set_all_indicators(self, state: bool):
        tf = self.tf_var.get()
        for key, _, _ in self.INDICATOR_DEFS.get(tf, []):
            self.ind_toggles[key] = state
            self._refresh_chip_style(key)
        self.selected_plan = "ALL" if state else "NONE"
        self._refresh_plan_buttons()
        self._draw()

    @staticmethod
    def _format_bar_time(server_ts, offset, tf):
        from datetime import datetime, timedelta, timezone
        dt = datetime.fromtimestamp(server_ts - offset, timezone(timedelta(hours=7)))
        if tf == "H4":
            return dt.strftime("%d/%m %H:%M")
        return dt.strftime("%H:%M")

    def _tick(self, reschedule=True):
        try:
            self._tick_once()
        except Exception:
            pass   # ข้อมูลชั่วคราวผิดพลาด — ไม่ให้กราฟค้างถาวร ลองใหม่รอบหน้า
        if reschedule:
            try:
                self._job = self.after(self.REFRESH_MS, self._tick)
            except Exception:
                pass   # หน้าต่างถูกปิดแล้ว

    def _tick_once(self):
        try:
            n = int(self.bars_var.get())
        except Exception:
            n = self.BARS
        tf = self.tf_var.get()
        data = bot_ctrl.get_live_candles(n, timeframe=tf)
        if data:
            self.data = data
            # เวลาเซิร์ฟเวอร์ MT5 → เวลาไทย (thai_time: ตลาดปิด/tick เก่าก็ยังถูก)
            self.offset = thai_time.server_offset()
            c = data["candles"]
            if not c:
                return
            last = c[-1]
            chg = last["close"] - last["open"]
            self.lbl_price.configure(text=f"{data['bid']:,.2f}", text_color=COLOR_SUCCESS_GREEN if chg >= 0 else COLOR_DANGER_RED)
            self.lbl_change.configure(text=f"แท่งนี้ {chg:+.2f} · Ask {data['ask']:,.2f} · Spread {data.get('spread_pts', 0)} pts",
                                      text_color=COLOR_SUCCESS_GREEN if chg >= 0 else COLOR_DANGER_RED)
            pos = data.get("positions", [])
            if pos:
                total = sum(p["profit"] for p in pos)
                good = total >= 0
                self.lbl_pnl.configure(
                    text=f"  ไม้เปิด {len(pos)} · {'กำไร' if good else 'ขาดทุน'}รวม {'+' if good else '-'}{abs(total):,.2f}  ",
                    text_color=COLOR_SUCCESS_GREEN if good else COLOR_DANGER_RED, fg_color="#0F2A20" if good else "#2A1215")
            else:
                self.lbl_pnl.configure(text="  ไม่มีไม้เปิด  ", text_color=COLOR_TEXT_MUTED, fg_color=COLOR_CARD_BG)
            bar_sec = data.get("bar_seconds", 900)
            remain = max(0, last["time"] + bar_sec - data["server_time"])
            hrs = remain // 3600
            mins = (remain % 3600) // 60
            secs = remain % 60
            if hrs > 0:
                self.lbl_clock.configure(text=f"แท่งปิดในอีก {hrs:02d}:{mins:02d}:{secs:02d}")
            else:
                self.lbl_clock.configure(text=f"แท่งปิดในอีก {mins:02d}:{secs:02d}")

            # ประเมินและแสดงผลสถานะเงื่อนไขการเข้าไม้เรียลไทม์
            plans_status = bot_ctrl.get_plans_condition_status("XAUUSD")
            self._refresh_plan_buttons(plans_status)
            self._update_condition_bar(plans_status)
            self._update_ai_sr_bar()

            self._draw()
        else:
            self.lbl_tip.configure(text="เชื่อมต่อ MT5 ไม่ได้ — ตรวจว่าเปิด MetaTrader 5 ค้างไว้")

    def _update_ai_sr_bar(self):
        """อัปเดตแถบคำแนะนำ AI วิเคราะห์แนวรับแนวต้านสำคัญที่ต้องโฟกัส"""
        if not hasattr(self, "ai_sr_frame"):
            return
        focus_res = self.data.get("focus_res", "R1")
        focus_sup = self.data.get("focus_sup", "S1")
        focus_res_price = self.data.get("focus_res_price") or self.data.get("resistance") or 0.0
        focus_sup_price = self.data.get("focus_sup_price") or self.data.get("support") or 0.0
        focus_res_score = self.data.get("focus_res_score") or float(self.data.get("res_stars", 6.0) or 6.0)
        focus_sup_score = self.data.get("focus_sup_score") or float(self.data.get("sup_stars", 6.0) or 6.0)
        action = self.data.get("focus_action") or ""

        if focus_res_price > 0:
            self.lbl_ai_res_badge.configure(text=f" 🎯 ต้าน {focus_res}: {focus_res_price:,.2f} (★ {focus_res_score:.2f}) ")
        else:
            self.lbl_ai_res_badge.configure(text=" 🎯 ต้าน: — ")

        if focus_sup_price > 0:
            self.lbl_ai_sup_badge.configure(text=f" 🎯 รับ {focus_sup}: {focus_sup_price:,.2f} (★ {focus_sup_score:.2f}) ")
        else:
            self.lbl_ai_sup_badge.configure(text=" 🎯 รับ: — ")

        if action:
            self.lbl_ai_action.configure(text=f"📌 {action}")
        else:
            self.lbl_ai_action.configure(text="📌 ติดตามการเคลื่อนไหวของราคาเทียบกับโซนสำคัญ")

    def _draw(self):
        cv = self.canvas
        cv.delete("all")
        self.slots = []
        if not self.data:
            return
        W, H = cv.winfo_width(), cv.winfo_height()
        if W < 60:
            return
        candles = self.data["candles"]
        if not candles:
            return

        tf = self.tf_var.get()
        left, right, top, bottom = 10, 70, 16, 28

        # คำนวณช่วงราคา (hi/lo) เฉพาะอินดิเคเตอร์ที่เปิดแสดงผลอยู่
        vals = [v for c in candles for v in (c["high"], c["low"])]
        if tf == "M15":
            if self.ind_toggles.get("ma5", True):
                vals += [c["ma5"] for c in candles if c.get("ma5") is not None]
            if self.ind_toggles.get("ma13", True):
                vals += [c["ma13"] for c in candles if c.get("ma13") is not None]
            if self.ind_toggles.get("ma50", True):
                vals += [c["ma50"] for c in candles if c.get("ma50") is not None]
        elif tf == "H1":
            if self.ind_toggles.get("h1_ma5", True):
                vals += [c["h1_ma5"] for c in candles if c.get("h1_ma5") is not None]
            if self.ind_toggles.get("h1_ma10", True):
                vals += [c["h1_ma10"] for c in candles if c.get("h1_ma10") is not None]
            if self.ind_toggles.get("h1_ma20", True):
                vals += [c["h1_ma20"] for c in candles if c.get("h1_ma20") is not None]
            if self.ind_toggles.get("h1_bb", True):
                vals += [c["h1_bb_up"] for c in candles if c.get("h1_bb_up") is not None]
                vals += [c["h1_bb_lo"] for c in candles if c.get("h1_bb_lo") is not None]
            if self.ind_toggles.get("h1_sar", True):
                vals += [c["h1_sar"] for c in candles if c.get("h1_sar") is not None]
            if self.ind_toggles.get("h1_ema100", True):
                vals += [c["h1_ema100"] for c in candles if c.get("h1_ema100") is not None]
        elif tf == "H4":
            if self.ind_toggles.get("h4_ma10", True):
                vals += [c["h4_ma10"] for c in candles if c.get("h4_ma10") is not None]
            if self.ind_toggles.get("h4_ma30", True):
                vals += [c["h4_ma30"] for c in candles if c.get("h4_ma30") is not None]
            if self.ind_toggles.get("h4_ma200", True):
                vals += [c["h4_ma200"] for c in candles if c.get("h4_ma200") is not None]

        cur_price = self.data["bid"]

        # รายการระดับแนวต้าน 5 ระดับ (R1..R5) พร้อมคะแนนความแข็งแกร่ง (เต็ม 10.00)
        res_list = [
            ("R1", self.data.get("resistance"), float(self.data.get("res_stars", 6.0) or 6.0), COLOR_DANGER_RED, (6, 3), 1.5, "bold"),
            ("R2", self.data.get("resistance2"), float(self.data.get("res2_stars", 5.0) or 5.0), "#FB923C", (4, 3), 1.2, "bold"),
            ("R3", self.data.get("resistance3"), float(self.data.get("res3_stars", 4.0) or 4.0), "#F59E0B", (3, 3), 1.0, "normal"),
            ("R4", self.data.get("resistance4"), float(self.data.get("res4_stars", 4.0) or 4.0), "#F43F5E", (2, 2), 1.0, "normal"),
            ("R5", self.data.get("resistance5"), float(self.data.get("res5_stars", 3.0) or 3.0), "#E11D48", (2, 2), 1.0, "normal"),
        ]

        # รายการระดับแนวรับ 5 ระดับ (S1..S5) พร้อมคะแนนความแข็งแกร่ง (เต็ม 10.00)
        sup_list = [
            ("S1", self.data.get("support"), float(self.data.get("sup_stars", 6.0) or 6.0), COLOR_SUCCESS_GREEN, (6, 3), 1.5, "bold"),
            ("S2", self.data.get("support2"), float(self.data.get("sup2_stars", 5.0) or 5.0), "#34D399", (4, 3), 1.2, "bold"),
            ("S3", self.data.get("support3"), float(self.data.get("sup3_stars", 4.0) or 4.0), "#2DD4BF", (3, 3), 1.0, "normal"),
            ("S4", self.data.get("support4"), float(self.data.get("sup4_stars", 4.0) or 4.0), "#06B6D4", (2, 2), 1.0, "normal"),
            ("S5", self.data.get("support5"), float(self.data.get("sup5_stars", 3.0) or 3.0), "#38BDF8", (2, 2), 1.0, "normal"),
        ]

        if tf in ("H1", "H4"):
            try:
                n_bars = int(self.bars_var.get())
            except Exception:
                n_bars = 120
            sr_range_limit = 600 if tf == "H4" else (250 if n_bars >= 200 else 60)
            if self.ind_toggles.get("support", True):
                for _, s_val, _, _, _, _, _ in sup_list:
                    if s_val and not (isinstance(s_val, float) and math.isnan(s_val)) and abs(s_val - cur_price) <= sr_range_limit:
                        vals.append(s_val)
            if self.ind_toggles.get("resistance", True):
                for _, r_val, _, _, _, _, _ in res_list:
                    if r_val and not (isinstance(r_val, float) and math.isnan(r_val)) and abs(r_val - cur_price) <= sr_range_limit:
                        vals.append(r_val)

        vals.append(self.data["ask"])
        if self.ind_toggles.get("orders", True):
            for p in self.data.get("positions", []):  # ให้เห็นเส้นราคาเข้า/TP/SL ในกรอบเสมอ
                vals += [v for v in (p["price"], p["sl"], p["tp"]) if v and v > 0]

        hi, lo = max(vals), min(vals)
        pad = max((hi - lo) * 0.08, 0.5)
        hi, lo = hi + pad, lo - pad
        ch = H - top - bottom

        def y_of(v):
            return top + (hi - v) / (hi - lo) * ch

        # เส้นราคาแนวนอน
        for k in range(6):
            v = lo + (hi - lo) * k / 5
            y = y_of(v)
            cv.create_line(left, y, W - right, y, fill="#1E232C")
            cv.create_text(W - right + 6, y, text=f"{v:,.2f}", anchor="w", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 9))

        n = len(candles)
        slot = (W - left - right - 24) / n   # เว้น 24px ระหว่างแท่งสุดท้ายกับแถบราคา
        bw = max(3, min(26, slot * 0.62))

        def draw_series(key, col, width=2, dash=None, smooth=True):
            pts = []
            for i, c in enumerate(candles):
                v = c.get(key)
                if v is not None and not (isinstance(v, float) and math.isnan(v)):
                    pts += [left + slot * (i + 0.5), y_of(v)]
            if len(pts) >= 4:
                kw = {"fill": col, "width": width}
                if dash:
                    kw["dash"] = dash
                elif smooth and len(pts) >= 6:
                    kw["smooth"] = True
                cv.create_line(*pts, **kw)

        def _draw_vector_stars(start_x, cy, stars, r_out=5.0, r_in=2.4, color='#FBBF24', empty_bg='#1A2232', empty_border='#475569'):
            full_count = int(stars)
            has_half = (stars - full_count) >= 0.5
            for i in range(5):
                cx = start_x + i * 12
                all_p = []
                for j in range(10):
                    r = r_out if j % 2 == 0 else r_in
                    angle = math.pi / 2 - j * (math.pi / 5)
                    all_p.extend([cx + r * math.cos(angle), cy - r * math.sin(angle)])
                if i < full_count:
                    cv.create_polygon(all_p, fill=color, outline=color)
                elif i == full_count and has_half:
                    cv.create_polygon(all_p, fill=empty_bg, outline=empty_border)
                    left_p = [all_p[0], all_p[1], all_p[18], all_p[19], all_p[16], all_p[17],
                              all_p[14], all_p[15], all_p[12], all_p[13], all_p[10], all_p[11]]
                    cv.create_polygon(left_p, fill=color, outline=color)
                else:
                    cv.create_polygon(all_p, fill=empty_bg, outline=empty_border)

        # 1. วาดแนวรับ–แนวต้าน 5 ระดับ (R1..R5 & S1..S5) สำหรับ Timeframe H1 และ H4
        if tf in ("H1", "H4"):
            focus_res = self.data.get("focus_res", "R1")
            focus_sup = self.data.get("focus_sup", "S1")

            # 1.1 แนวต้าน 5 ระดับ (R1..R5) พร้อมคะแนนความแข็งแกร่ง (เต็ม 10.00 ทศนิยม 2 ตำแหน่ง)
            if self.ind_toggles.get("resistance", True):
                for name, r_val, r_stars, col, dash, width, weight in res_list:
                    if r_val and not (isinstance(r_val, float) and math.isnan(r_val)) and lo <= r_val <= hi:
                        is_focus = (name == focus_res)
                        yr = y_of(r_val)
                        line_w = 2.5 if is_focus else width
                        line_dash = None if is_focus else dash
                        cv.create_line(left, yr, W - right, yr, fill=col, dash=line_dash, width=line_w)
                        lbl_y = yr + 8 if yr < top + 16 else yr - 8
                        name_txt = f"แนวต้าน {name} {r_val:,.2f}"
                        cv.create_text(left + 6, lbl_y, text=name_txt, anchor="w", fill=col, font=(app_fonts.UI, 9, "bold" if is_focus else weight))
                        r_score = max(0.0, min(10.0, float(r_stars or 0.0)))
                        cv.create_text(left + 128, lbl_y, text=f"★ {r_score:.2f}", anchor="w", fill=COLOR_GOLD_PRIMARY, font=(app_fonts.UI, 8, weight))
                        if is_focus:
                            cv.create_text(left + 175, lbl_y, text="🎯 AI FOCUS", anchor="w", fill=COLOR_GOLD_PRIMARY, font=(app_fonts.UI, 8, "bold"))

            # 1.2 แนวรับ 5 ระดับ (S1..S5) พร้อมคะแนนความแข็งแกร่ง (เต็ม 10.00 ทศนิยม 2 ตำแหน่ง)
            if self.ind_toggles.get("support", True):
                for name, s_val, s_stars, col, dash, width, weight in sup_list:
                    if s_val and not (isinstance(s_val, float) and math.isnan(s_val)) and lo <= s_val <= hi:
                        is_focus = (name == focus_sup)
                        ys = y_of(s_val)
                        line_w = 2.5 if is_focus else width
                        line_dash = None if is_focus else dash
                        cv.create_line(left, ys, W - right, ys, fill=col, dash=line_dash, width=line_w)
                        lbl_y = ys - 8 if ys > top + 16 else ys + 8
                        name_txt = f"แนวรับ {name} {s_val:,.2f}"
                        cv.create_text(left + 6, lbl_y, text=name_txt, anchor="w", fill=col, font=(app_fonts.UI, 9, "bold" if is_focus else weight))
                        s_score = max(0.0, min(10.0, float(s_stars or 0.0)))
                        cv.create_text(left + 124, lbl_y, text=f"★ {s_score:.2f}", anchor="w", fill=COLOR_GOLD_PRIMARY, font=(app_fonts.UI, 8, weight))
                        if is_focus:
                            cv.create_text(left + 171, lbl_y, text="🎯 AI FOCUS", anchor="w", fill=COLOR_GOLD_PRIMARY, font=(app_fonts.UI, 8, "bold"))

        # 2. วาดอินดิเคเตอร์เฉพาะตาม Timeframe ที่เลือก
        if tf == "M15":
            # Plan 1 (MA-Cross-Trend M15)
            if self.ind_toggles.get("ma50", True):
                draw_series("ma50", "#A78BFA", width=1, dash=(4, 2), smooth=True)
            if self.ind_toggles.get("ma13", True):
                draw_series("ma13", COLOR_GOLD_WARM, width=2, smooth=True)
            if self.ind_toggles.get("ma5", True):
                draw_series("ma5", COLOR_CYAN_ACCENT, width=2, smooth=True)
        elif tf == "H1":
            # Bollinger Bands H1 (Plan 5)
            if self.ind_toggles.get("h1_bb", True):
                draw_series("h1_bb_up", "#C084FC", width=1, dash=(4, 2), smooth=True)
                draw_series("h1_bb_mid", "#94A3B8", width=1, dash=(2, 2), smooth=True)
                draw_series("h1_bb_lo", "#C084FC", width=1, dash=(4, 2), smooth=True)

            # 3. EMA100 H1 (Plan 6)
            if self.ind_toggles.get("h1_ema100", True):
                draw_series("h1_ema100", "#60A5FA", width=1, dash=(4, 2), smooth=True)

            # 4. Parabolic SAR H1 (Plan 6)
            if self.ind_toggles.get("h1_sar", True):
                for i, c in enumerate(candles):
                    sar = c.get("h1_sar")
                    if sar is not None and not (isinstance(sar, float) and math.isnan(sar)):
                        cx = left + slot * (i + 0.5)
                        cy = y_of(sar)
                        cv.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill="#FB7185", outline="")

            # 5. Moving Averages H1 (Plan 2)
            if self.ind_toggles.get("h1_ma20", True):
                draw_series("h1_ma20", "#818CF8", width=1, dash=(5, 3), smooth=True)
            if self.ind_toggles.get("h1_ma10", True):
                draw_series("h1_ma10", "#FBBF24", width=2, smooth=True)
            if self.ind_toggles.get("h1_ma5", True):
                draw_series("h1_ma5", "#34D399", width=2, smooth=True)
        elif tf == "H4":
            # H4 Trend Regimes: MA10, MA30, MA200
            if self.ind_toggles.get("h4_ma200", True):
                draw_series("h4_ma200", "#A78BFA", width=2, dash=(4, 2), smooth=True)
            if self.ind_toggles.get("h4_ma30", True):
                draw_series("h4_ma30", "#FB923C", width=2, smooth=True)
            if self.ind_toggles.get("h4_ma10", True):
                draw_series("h4_ma10", "#FBBF24", width=2, smooth=True)

        # แท่งเทียน Candlesticks
        for i, c in enumerate(candles):
            cx = left + slot * (i + 0.5)
            up = c["close"] >= c["open"]
            col = COLOR_SUCCESS_GREEN if up else COLOR_DANGER_RED
            cv.create_line(cx, y_of(c["high"]), cx, y_of(c["low"]), fill=col, width=1)
            y1, y2 = y_of(c["open"]), y_of(c["close"])
            if abs(y1 - y2) < 1:
                y2 = y1 + 1
            live = i == n - 1
            cv.create_rectangle(cx - bw / 2, min(y1, y2), cx + bw / 2, max(y1, y2), fill=col,
                                outline=COLOR_GOLD_PRIMARY if live else col, width=2 if live else 1)
            every = max(1, int(round(n / max(1, (W - left - right) / 58))))
            if (i % every == 0 and i < n - max(2, int(every * 0.8))) or live:
                t_str = "ตอนนี้" if live else self._format_bar_time(c["time"], self.offset, tf)
                cv.create_text(cx, H - bottom + 13, text=t_str,
                               fill=COLOR_GOLD_PRIMARY if live else COLOR_TEXT_MUTED,
                               font=(app_fonts.UI, 9, "bold" if live else "normal"))
            self.slots.append((cx - slot / 2, cx + slot / 2, c))

        # ไม้ที่เปิดอยู่: ราคาเข้า / TP / SL / Lot
        if self.ind_toggles.get("orders", True):
            for p in self.data.get("positions", []):
                for val, col, txt in ((p["price"], COLOR_CYAN_ACCENT, f"{p['type']} {p['lot']:.2f} lot @ {p['price']:,.2f} ({p['profit']:+.2f})"),
                                      (p["tp"], COLOR_SUCCESS_GREEN, f"TP {p['tp']:,.2f}"), (p["sl"], COLOR_DANGER_RED, f"SL {p['sl']:,.2f}")):
                    if not val or val <= 0:
                        continue
                    yy = y_of(val)
                    cv.create_line(left, yy, W - right, yy, fill=col, dash=(6, 3))
                    cv.create_text(left + 4, yy - 7, text=txt, anchor="w", fill=col, font=(app_fonts.UI, 9, "bold"))

        # เส้น Ask
        ya = y_of(self.data["ask"])
        cv.create_line(left, ya, W - right, ya, fill="#5B6270", dash=(2, 4))
        cv.create_text(W - right + 6, ya - 12 if abs(ya - y_of(self.data["bid"])) < 18 else ya, text=f"A {self.data['ask']:,.2f}", anchor="w", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 8))

        # เส้นราคาล่าสุด (Bid)
        yb = y_of(self.data["bid"])
        cv.create_line(left, yb, W - right, yb, fill=COLOR_TEXT_MUTED, dash=(3, 3))
        cv.create_rectangle(W - right + 2, yb - 9, W - 2, yb + 9, fill=COLOR_GOLD_PRIMARY, outline="")
        cv.create_text(W - right + 6, yb, text=f"{self.data['bid']:,.2f}", anchor="w", fill="#111111", font=(app_fonts.UI, 9, "bold"))

    def _hover(self, event):
        for x0, x1, c in self.slots:
            if x0 <= event.x < x1:
                tf = self.tf_var.get()
                extras = []
                if tf == "M15":
                    if self.ind_toggles.get("ma5", True) and c.get("ma5") is not None:
                        extras.append(f"MA5 {c['ma5']:,.2f}")
                    if self.ind_toggles.get("ma13", True) and c.get("ma13") is not None:
                        extras.append(f"MA13 {c['ma13']:,.2f}")
                    if self.ind_toggles.get("ma50", True) and c.get("ma50") is not None:
                        extras.append(f"MA50 {c['ma50']:,.2f}")
                elif tf == "H1":
                    if self.ind_toggles.get("h1_ma5", True) and c.get("h1_ma5") is not None:
                        extras.append(f"MA5 {c['h1_ma5']:,.2f}")
                    if self.ind_toggles.get("h1_ma10", True) and c.get("h1_ma10") is not None:
                        extras.append(f"MA10 {c['h1_ma10']:,.2f}")
                    if self.ind_toggles.get("h1_ma20", True) and c.get("h1_ma20") is not None:
                        extras.append(f"MA20 {c['h1_ma20']:,.2f}")
                    if self.ind_toggles.get("h1_bb", True) and c.get("h1_bb_lo") is not None and c.get("h1_bb_up") is not None:
                        extras.append(f"BB [{c['h1_bb_lo']:,.1f}–{c['h1_bb_up']:,.1f}]")
                    if self.ind_toggles.get("h1_sar", True) and c.get("h1_sar") is not None:
                        extras.append(f"SAR {c['h1_sar']:,.2f}")
                    if self.ind_toggles.get("h1_ema100", True) and c.get("h1_ema100") is not None:
                        extras.append(f"EMA100 {c['h1_ema100']:,.2f}")
                elif tf == "H4":
                    if self.ind_toggles.get("h4_ma10", True) and c.get("h4_ma10") is not None:
                        extras.append(f"MA10 {c['h4_ma10']:,.2f}")
                    if self.ind_toggles.get("h4_ma30", True) and c.get("h4_ma30") is not None:
                        extras.append(f"MA30 {c['h4_ma30']:,.2f}")
                    if self.ind_toggles.get("h4_ma200", True) and c.get("h4_ma200") is not None:
                        extras.append(f"MA200 {c['h4_ma200']:,.2f}")

                extra_str = (" · " + " · ".join(extras)) if extras else ""
                t_str = self._format_bar_time(c['time'], self.offset, tf)
                self.lbl_tip.configure(text=f"{t_str} น. · O {c['open']:,.2f}  H {c['high']:,.2f}  "
                                            f"L {c['low']:,.2f}  C {c['close']:,.2f} ({c['close'] - c['open']:+.2f}){extra_str}")
                return


class PositionDetailDialog(ctk.CTkToplevel):
    """คลิกไม้ในแท็บออเดอร์ที่เปิดอยู่ → กราฟ M15 80 แท่งเรียลไทม์ + Lot / ราคาเข้า / ราคาปัจจุบัน / SL / TP
    + อินดิเคเตอร์ที่แผนของไม้นั้นใช้จริง (position_chart.get) + คำแนะนำถือต่อ/ปิด (position_advisor)
    trade=แถวจากประวัติการเทรด → ภาพ ณ ตอนปิดไม้ (position_chart.get_closed) + สรุปไม้ · ไม่อัปเดตต่อ"""

    BARS = 80
    REFRESH_MS = 1000
    STYLE_COLORS = {"fast": COLOR_CYAN_ACCENT, "slow": COLOR_GOLD_WARM, "ma50": "#A78BFA", "band": "#A78BFA",
                    "mid": "#8A93A6", "sup": COLOR_SUCCESS_GREEN, "res": COLOR_DANGER_RED}
    PLAN_RULES = {
        "P1": "MA5 ตัด MA13 (M15) + H1 MA100/150/200 เรียงตัว · กรอง RSI + MA50 · SL 1.0 ATR · ไม่ตั้ง TP · ออกเมื่อ MA ตัดกลับ · เลื่อน SL ทุก +5 จุด",
        "P2": "MA5 ตัด MA10 (H1) + H4 MA10/30 + ความชัน MA5 H4 + MA200 H4 · SL 1.25 ATR H1 · ไม่ตั้ง TP · ออกเมื่อ MA5 ตัด MA20 กลับ",
        "P3": "ราคากวาดแนวรับ/ต้าน H1 แล้วดึงกลับ + ไส้เทียน 0.4–1.0 ATR + เทรนด์ H1 + MA100/150/200 H1 เรียงตามทิศ + AI · SL 1.0 ATR · TP 2.0 ATR · เลื่อน SL ทุก +5 จุด",
        "P4": "เด้งโซนแนวรับ/ต้าน H1 (≤ 0.75 ATR) + RSI Divergence + H1 MA100/150/200 ไม่สวนทิศ + AI ≥ 55% · SL 1.0 ATR · TP 2.0 ATR · เลื่อน SL ทุก +5 จุด",
        "P5": "หลุดกรอบ Bollinger H1 แล้วกลับเข้า + Divergence + AI ≥ 55% · SL 0.75 ATR · TP 1.5 เท่า · เลื่อน SL ทุก +5 จุด",
        "P6": "Parabolic SAR H1 สลับข้างมาทางเทรนด์ H4 (MA10/30 + MA200) · SL = จุด SAR (ไม่เกิน 3 ATR H1) เลื่อนตาม SAR ทุกชั่วโมง · กำไรถึง 2 ATR เลื่อนเร็วขึ้น · ไม่ตั้ง TP · ออกเมื่อเทรนด์ H4 เปลี่ยนหรือราคาปิดผิดฝั่ง EMA100",
        "M": "ไม้ที่เข้าเอง (ปุ่มในโปรแกรมหรือใน MT5) · ไม่มี SL บอทตั้งให้ 1.0 ATR · เลื่อน SL ทุกกำไร 5 จุด (ขั้นแรก 50% / ถัดไป 40%) · ล็อกกำไร / AI กลับทิศ / ปิดเมื่อกำไรถึงเป้า",
    }

    @staticmethod
    def _f(size, weight="normal", family=app_fonts.UI):
        return ctk.CTkFont(family=family, size=size, weight=weight)

    def __init__(self, parent, pos, trade=None):
        super().__init__(parent)
        self.ticket = int(pos["ticket"])
        self.trade, self.closed = trade, trade is not None
        self.fallback = {"type": pos.get("type"), "comment": pos.get("comment")}
        self.data, self.last_pos, self.slots, self._job, self.offset = None, None, [], None, 0
        self._ind_names, self._ind_rows, self._legend_sig, self._adv_sig = None, [], None, None
        self.title(f"ประวัติไม้ #{self.ticket} · ภาพตอนปิดไม้ (M15)" if self.closed else f"ไม้ #{self.ticket} · XAUUSD M15 เรียลไทม์")
        self.configure(fg_color=COLOR_BG_DARK)
        # ไม่ใช้ transient เพื่อให้มีปุ่มขยาย/ย่อ บนแถบหัวหน้าต่าง
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(1140, sw - 40), min(700, sh - 80)
        self.after(10, self.lift)
        self.update_idletasks()
        x = max(0, parent.winfo_rootx() + (parent.winfo_width() - w) // 2)
        y = max(0, parent.winfo_rooty() + (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(820, 520)
        apply_dark_title_bar(self)
        f = self._f

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 6))
        self.lbl_side = ctk.CTkLabel(top, text="", font=f(13, "bold"), corner_radius=6, height=26, width=58)
        self.lbl_side.pack(side="left")
        ctk.CTkLabel(top, text=f"#{self.ticket}", font=f(16, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left", padx=10)
        self.lbl_plan = ctk.CTkLabel(top, text="", font=f(15, "bold"), text_color=COLOR_GOLD_PRIMARY)
        self.lbl_plan.pack(side="left")
        ctk.CTkLabel(top, text="   XAUUSD · M15 · 80 แท่ง · " + ("ภาพ ณ ตอนปิดไม้" if self.closed else "อัปเดตทุก 1 วินาที"),
                     font=f(11), text_color=COLOR_TEXT_MUTED).pack(side="left")
        self.btn_full = ctk.CTkButton(top, text="ขยายเต็มจอ", width=96, height=28, font=f(12, "bold"), fg_color=COLOR_CARD_BG,
                                      hover_color=COLOR_CARD_HOVER, border_width=1, border_color=COLOR_CARD_BORDER,
                                      text_color=COLOR_GOLD_PRIMARY, command=self._toggle_full)
        self.btn_full.pack(side="right", padx=(10, 0))
        self.lbl_pnl = ctk.CTkLabel(top, text="", font=f(16, "bold"), corner_radius=8, height=30)
        self.lbl_pnl.pack(side="right")
        self.lbl_clock = ctk.CTkLabel(top, text="", font=f(11), text_color=COLOR_TEXT_MUTED)
        self.lbl_clock.pack(side="right", padx=12)
        self.bind("<F11>", lambda e: self._toggle_full())
        self.bind("<Escape>", lambda e: self.state() == "zoomed" and self._toggle_full())

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=12)
        self.stat = {}
        for i, (key, title) in enumerate((("lot", "Lot"), ("entry", "ราคาเข้า"), ("price", "ราคาตอนปิด" if self.closed else "ราคาปัจจุบัน"),
                                          ("sl", "Stop Loss ตอนปิด" if self.closed else "Stop Loss"),
                                          ("tp", "Take Profit ตอนปิด" if self.closed else "Take Profit"),
                                          ("held", "ถือไว้" if self.closed else "ถือมา"))):
            stats.grid_columnconfigure(i, weight=1, uniform="st")
            box = ctk.CTkFrame(stats, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
            box.grid(row=0, column=i, sticky="ew", padx=4)
            ctk.CTkLabel(box, text=title, font=f(10), text_color=COLOR_TEXT_MUTED, height=16).pack(anchor="w", padx=10, pady=(6, 0))
            v = ctk.CTkLabel(box, text="—", font=f(16, "bold", app_fonts.MONO), text_color=COLOR_TEXT_PRIMARY, height=24)
            v.pack(anchor="w", padx=10)
            s = ctk.CTkLabel(box, text="", font=f(10), text_color=COLOR_TEXT_MUTED, height=16)
            s.pack(anchor="w", padx=10, pady=(0, 6))
            self.stat[key] = (v, s)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(8, 4))
        side = ctk.CTkFrame(body, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER, width=340)
        side.pack(side="right", fill="y", padx=(8, 4))
        side.pack_propagate(False)
        ctk.CTkLabel(side, text="อินดิเคเตอร์ของแผน", font=f(14, "bold"), text_color=COLOR_GOLD_PRIMARY).pack(anchor="w", padx=14, pady=(10, 0))
        self.lbl_rule = ctk.CTkLabel(side, text="", font=f(10), text_color=COLOR_TEXT_MUTED, justify="left", wraplength=306)
        self.lbl_rule.pack(anchor="w", padx=14, pady=(0, 4))
        leg = ctk.CTkFrame(side, fg_color="transparent")
        leg.pack(anchor="w", padx=14)
        self.lbl_ind_counts = ctk.CTkFrame(leg, fg_color="transparent")   # ป้ายสรุป หนุน / สวน / กลาง
        self.lbl_ind_counts.pack(side="left")
        self.adv_box = ctk.CTkFrame(side, fg_color="#14171E", corner_radius=10)
        self.adv_box.pack(side="bottom", fill="x", padx=10, pady=10)
        self.ind_list = ctk.CTkScrollableFrame(side, fg_color="transparent")
        self.ind_list.pack(fill="both", expand=True, padx=4, pady=(4, 0))

        chart = ctk.CTkFrame(body, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        chart.pack(side="left", fill="both", expand=True, padx=(4, 0))
        self.legend = ctk.CTkFrame(chart, fg_color="transparent")
        self.legend.pack(fill="x", padx=12, pady=(8, 0))
        self.canvas = tk.Canvas(chart, bg=COLOR_CARD_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=(2, 6))
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<Motion>", self._hover)
        self.canvas.bind("<Leave>", lambda e: self.lbl_tip.configure(text=self.tip_default))
        self.tip_default = "ชี้ที่แท่งเพื่อดู Open / High / Low / Close และค่าอินดิเคเตอร์ของแท่งนั้น"
        self.lbl_tip = ctk.CTkLabel(self, text=self.tip_default, font=f(12), text_color=COLOR_TEXT_MUTED)
        self.lbl_tip.pack(pady=(0, 8))
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._tick()

    def _toggle_full(self):
        if self.state() == "zoomed":
            self.state("normal")
            self.btn_full.configure(text="ขยายเต็มจอ")
        else:
            self.state("zoomed")
            self.btn_full.configure(text="ย่อหน้าต่าง")

    def _close(self):
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        self.destroy()

    def _hhmm(self, server_ts):
        from datetime import datetime, timedelta, timezone
        return datetime.fromtimestamp(server_ts - self.offset, timezone(timedelta(hours=7))).strftime("%H:%M")

    def _dt(self, server_ts):
        from datetime import datetime, timedelta, timezone
        return datetime.fromtimestamp(server_ts - self.offset, timezone(timedelta(hours=7))).strftime("%d/%m %H:%M")

    def _tick(self):
        try:
            self._tick_once()
        except Exception:
            pass   # เช่น ไม้ปิดระหว่างอัปเดต — ไม่ให้หน้าต่างค้างถาวร ลองใหม่รอบหน้า
        if not self.closed:   # ไม้ที่ปิดแล้ว = ภาพนิ่ง ณ ตอนปิด
            try:
                self._job = self.after(self.REFRESH_MS, self._tick)
            except Exception:
                pass   # หน้าต่างถูกปิดแล้ว

    def _tick_once(self):
        try:
            if self.closed:
                d = position_chart.get_closed(self.trade, self.BARS)
            else:
                d = position_chart.get(self.ticket, self.BARS, fallback=self.fallback)
        except Exception:
            d = None
        if d:
            self.data = d
            self.offset = d.get("server_offset", 0)
            if d["position"]:
                self.last_pos = d["position"]
            self._update_header(d)
            self._update_legend(d)
            self._update_indicators(d)
            if self.closed:
                self._update_summary(d)
            else:
                self._update_advice()
            self._draw()
        else:
            self.lbl_tip.configure(text="ไม่พบข้อมูลราคาช่วงเวลาของไม้นี้ใน MT5" if self.closed
                                   else "เชื่อมต่อ MT5 ไม่ได้ — ตรวจว่าเปิด MetaTrader 5 ค้างไว้")

    # ---- ส่วนหัว + การ์ดตัวเลข ----
    def _update_header(self, d):
        buy = d["side"] > 0
        self.lbl_side.configure(text="BUY" if buy else "SELL", text_color=COLOR_SUCCESS_GREEN if buy else COLOR_DANGER_RED,
                                fg_color="#12261C" if buy else "#2C1618")
        self.lbl_plan.configure(text=d["plan_name"])
        self.lbl_rule.configure(text=self.PLAN_RULES.get(d["plan_key"], ""))
        if self.closed:
            reason, rcol = MainTradingApp._close_reason(self.trade)
            self.lbl_clock.configure(text=f"ปิด {self._dt(self.trade['close_time'])} น. · {reason}", text_color=rcol)
        else:
            remain = max(0, d["candles"][-1]["time"] + 900 - d["server_time"])
            self.lbl_clock.configure(text=f"แท่งปัจจุบันปิดในอีก {remain // 60:02d}:{remain % 60:02d}")
        lp = d["position"] or self.last_pos
        if not lp:
            self.lbl_pnl.configure(text="  ไม้นี้ปิดแล้ว  ", text_color=COLOR_TEXT_MUTED, fg_color=COLOR_CARD_BG)
            return
        side, mpp = d["side"], d["money_per_pt"]
        profit = lp["profit"]
        good = profit >= 0
        if d["position"] is None:
            self.lbl_pnl.configure(text="  ไม้นี้ปิดแล้ว (ค่าล่าสุดก่อนปิด)  ", text_color=COLOR_TEXT_MUTED, fg_color=COLOR_CARD_BG)
        else:
            self.lbl_pnl.configure(text=f"  {'กำไร' if good else 'ขาดทุน'} {'+' if good else '-'}{abs(profit):,.2f}  ",
                                   text_color=COLOR_SUCCESS_GREEN if good else COLOR_DANGER_RED, fg_color="#0F2A20" if good else "#2A1215")
        entry, price, sl, tp = lp["entry"], lp["price"], lp["sl"], lp["tp"]
        moved = (price - entry) * side

        def put(key, val, sub, col=COLOR_TEXT_PRIMARY, sub_col=COLOR_TEXT_MUTED):
            v, s = self.stat[key]
            v.configure(text=val, text_color=col)
            s.configure(text=sub, text_color=sub_col)

        put("lot", f"{lp['lot']:.2f}", f"{mpp:,.2f} ต่อราคา 1 จุด")
        put("entry", f"{entry:,.2f}", f"เปิด {self._dt(lp['time'])} น." if self.closed else f"Spread ตอนนี้ {d['spread_pts']} pts")
        put("price", f"{price:,.2f}", f"{'+' if moved >= 0 else '-'}{abs(moved):,.2f} จุดจากราคาเข้า",
            COLOR_SUCCESS_GREEN if moved > 0 else (COLOR_DANGER_RED if moved < 0 else COLOR_GOLD_PRIMARY),
            COLOR_SUCCESS_GREEN if moved > 0 else (COLOR_DANGER_RED if moved < 0 else COLOR_TEXT_MUTED))
        code = lp.get("close_code", -1) if self.closed else -1
        if sl > 0 and code == 4:   # ปิดเพราะชน SL
            locked = (sl - entry) * side > 0
            put("sl", f"{sl:,.2f}", "ปิดที่ SL" + (f" · ล็อกกำไร +{(sl - entry) * side * mpp:,.2f}" if locked else ""),
                COLOR_CYAN_ACCENT if locked else COLOR_DANGER_RED, COLOR_CYAN_ACCENT if locked else COLOR_DANGER_RED)
        elif sl > 0:
            locked = (sl - entry) * side > 0
            if locked:
                put("sl", f"{sl:,.2f}", f"ล็อกกำไรแล้ว +{(sl - entry) * side * mpp:,.2f}", COLOR_CYAN_ACCENT, COLOR_CYAN_ACCENT)
            else:
                put("sl", f"{sl:,.2f}", f"ห่าง {abs(price - sl):,.2f} จุด · เสี่ยง -{abs(entry - sl) * mpp:,.2f}", COLOR_DANGER_RED)
        else:
            put("sl", "ไม่มี", "ไม่มี Stop Loss", COLOR_DANGER_RED, COLOR_DANGER_RED)
        if tp > 0 and code == 5:   # ปิดเพราะชน TP
            put("tp", f"{tp:,.2f}", f"ปิดที่ TP · +{abs(tp - entry) * mpp:,.2f}", COLOR_SUCCESS_GREEN, COLOR_SUCCESS_GREEN)
        elif tp > 0:
            put("tp", f"{tp:,.2f}", (f"ห่าง {max(0.0, (tp - price) * side):,.2f} จุดตอนปิด" if self.closed else
                                     f"อีก {max(0.0, (tp - price) * side):,.2f} จุด") + f" · เป้า +{abs(tp - entry) * mpp:,.2f}", COLOR_SUCCESS_GREEN)
        else:
            put("tp", "รันเทรนด์", "ไม่ตั้ง TP · ออกเมื่อ MA ตัดกลับ" if d["plan_key"] in ("P1", "P2") else "ไม่ตั้ง TP", COLOR_GOLD_PRIMARY)
        if self.closed:
            put("held", MainTradingApp._fmt_duration(lp["close_time"] - lp["time"]), f"ปิด {self._dt(lp['close_time'])} น.")
        else:
            put("held", MainTradingApp._fmt_duration(d["server_time"] - lp["time"]), f"เปิด {self._hhmm(lp['time'])} น. (เวลาไทย)")

    def _update_legend(self, d):
        items = [(f"━ {ln['label']}", self.STYLE_COLORS.get(ln["style"], COLOR_TEXT_MUTED)) for ln in d["lines"]]
        items += [(f"┅ {lv['label'].split(' ')[0]} {lv['label'].split(' ')[1]}", self.STYLE_COLORS[lv["style"]]) for lv in d["levels"]]
        items += [("┅ ราคาเข้า", COLOR_CYAN_ACCENT), ("┅ SL", COLOR_DANGER_RED), ("┅ TP", COLOR_SUCCESS_GREEN)]
        if d.get("paths"):
            items.append(("━ การเลื่อน SL/TP", "#C7CDD8"))
        if self.closed:
            items.append(("◆ จุดปิดไม้", COLOR_GOLD_PRIMARY))
        if items == self._legend_sig:
            return
        self._legend_sig = items
        for w in self.legend.winfo_children():
            w.destroy()
        for txt, col in items:
            ctk.CTkLabel(self.legend, text=txt, font=self._f(11), text_color=col, height=18).pack(side="left", padx=(0, 12))

    # ---- รายการอินดิเคเตอร์ (สร้างแถวครั้งเดียว อัปเดตข้อความในที่เดิม) ----
    def _update_indicators(self, d):
        inds = d["indicators"]
        names = [i["name"] for i in inds]
        if names != self._ind_names:
            self._ind_names = names
            for w in self.ind_list.winfo_children():
                w.destroy()
            self._ind_rows = []
            for i, _ in enumerate(inds):
                row = ctk.CTkFrame(self.ind_list, fg_color="#171B23" if i % 2 == 0 else "transparent", corner_radius=8)
                row.pack(fill="x", padx=4, pady=1)
                head = ctk.CTkFrame(row, fg_color="transparent")
                head.pack(fill="x", padx=6, pady=(5, 0))
                dot = ctk.CTkLabel(head, text="", font=self._f(10, "bold"), width=58, height=20, corner_radius=6)
                dot.pack(side="left")
                name = ctk.CTkLabel(head, text="", font=self._f(11, "bold"), text_color=COLOR_TEXT_PRIMARY, height=20)
                name.pack(side="left", padx=(8, 0))
                val = ctk.CTkLabel(row, text="", font=self._f(13, "bold", app_fonts.MONO), anchor="w", height=20)
                val.pack(fill="x", padx=(72, 8))
                note = ctk.CTkLabel(row, text="", font=self._f(10), text_color=COLOR_TEXT_MUTED, justify="left", anchor="w", wraplength=240)
                self._ind_rows.append((dot, name, val, note))
        counts = (sum(1 for it in inds if it["dir"] > 0), sum(1 for it in inds if it["dir"] < 0), sum(1 for it in inds if not it["dir"]))
        if getattr(self, "_ind_counts", None) != counts:
            self._ind_counts = counts
            for w in self.lbl_ind_counts.winfo_children():
                w.destroy()
            for txt, n, col in (("หนุนไม้", counts[0], COLOR_SUCCESS_GREEN), ("สวนไม้", counts[1], COLOR_DANGER_RED), ("กลาง", counts[2], COLOR_TEXT_MUTED)):
                ctk.CTkLabel(self.lbl_ind_counts, text=f" {txt} {n} ", font=self._f(10, "bold"), corner_radius=6, height=20,
                             fg_color="#101218", text_color=col).pack(side="left", padx=(0, 6))
        for (dot, name, val, note), it in zip(self._ind_rows, inds):
            col = COLOR_SUCCESS_GREEN if it["dir"] > 0 else (COLOR_DANGER_RED if it["dir"] < 0 else COLOR_TEXT_MUTED)
            ptxt, pfg, pbg = status_pill_style(it["dir"])
            dot.configure(text=ptxt, text_color=pfg, fg_color=pbg)
            name.configure(text=it["name"])
            val.configure(text=it["value"], text_color=col if it["dir"] else COLOR_TEXT_PRIMARY)
            if note.cget("text") != it["note"]:
                note.configure(text=it["note"])
            if it["note"] and not note.winfo_manager():
                note.pack(fill="x", padx=(72, 8), pady=(0, 5))
            elif not it["note"] and note.winfo_manager():
                note.pack_forget()

    def _update_summary(self, d):
        """ไม้ที่ปิดแล้ว: สรุปผล / ปิดโดย / กำไรสูงสุด-ติดลบสูงสุดระหว่างถือ / SL-TP ตอนเข้าเทียบตอนปิด"""
        for w in self.adv_box.winfo_children():
            w.destroy()
        s, lp = d.get("summary") or {}, d["position"]
        reason, rcol = MainTradingApp._close_reason(self.trade)
        head = ctk.CTkFrame(self.adv_box, fg_color="transparent")
        head.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(head, text="สรุปไม้", font=self._f(12, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(head, text=f" {reason} ", font=self._f(11, "bold"), text_color=rcol, fg_color="#1A1E27",
                     corner_radius=6, height=22).pack(side="right")
        pf = lp["profit"]
        rows = [("ผลลัพธ์", f"{'+' if pf >= 0 else '-'}{abs(pf):,.2f}",
                 COLOR_SUCCESS_GREEN if pf > 0 else (COLOR_DANGER_RED if pf < 0 else COLOR_TEXT_MUTED))]
        if s.get("mfe") is not None:
            rows.append(("กำไรสูงสุดระหว่างถือ", f"+{s['mfe']:,.2f} จุด (+{s['mfe_money']:,.2f})", COLOR_SUCCESS_GREEN))
            rows.append(("ติดลบสูงสุดระหว่างถือ", f"-{s['mae']:,.2f} จุด (-{s['mae_money']:,.2f})", COLOR_DANGER_RED))
        if s.get("initial_sl"):
            rows.append(("SL เข้า → ปิด", f"{s['initial_sl']:,.2f} → {lp['sl']:,.2f}" + (f" · เลื่อน {s['sl_moves']}" if s.get("sl_moves") else ""),
                         COLOR_TEXT_PRIMARY))
        if s.get("initial_tp"):
            rows.append(("TP เข้า → ปิด", f"{s['initial_tp']:,.2f} → {lp['tp']:,.2f}" + (f" · ขยาย {s['tp_moves']}" if s.get("tp_moves") else ""),
                         COLOR_TEXT_PRIMARY))
        for name, val, col in rows:
            r = ctk.CTkFrame(self.adv_box, fg_color="transparent")
            r.pack(fill="x", padx=10)
            ctk.CTkLabel(r, text=name, font=self._f(10), text_color=COLOR_TEXT_MUTED, height=19).pack(side="left")
            ctk.CTkLabel(r, text=val, font=self._f(11, "bold"), text_color=col, height=19).pack(side="right")
        ctk.CTkLabel(self.adv_box, text="ค่าอินดิเคเตอร์ด้านบน = ค่า ณ ตอนปิดไม้", font=self._f(10),
                     text_color=COLOR_TEXT_MUTED, anchor="w").pack(fill="x", padx=10, pady=(2, 8))

    def _update_advice(self):
        a = position_advisor.latest().get(self.ticket)
        sig = (a or {}).get("verdict"), (a or {}).get("score"), (a or {}).get("advice")
        if sig == self._adv_sig:
            return
        self._adv_sig = sig
        for w in self.adv_box.winfo_children():
            w.destroy()
        head = ctk.CTkFrame(self.adv_box, fg_color="transparent")
        head.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(head, text="AI แนะนำ", font=self._f(12, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        if not a:
            ctk.CTkLabel(self.adv_box, text="กำลังวิเคราะห์… (ทุก 30 วินาที)", font=self._f(11), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=10, pady=(0, 8))
            return
        fg, bg = MainTradingApp.ADVICE_STYLE[a["verdict"]]
        ctk.CTkLabel(head, text=f" {a['verdict_text']} ", font=self._f(12, "bold"), text_color=fg, fg_color=bg,
                     corner_radius=6, height=22).pack(side="right")
        ctk.CTkLabel(self.adv_box, text=a["advice"], font=self._f(11), text_color=fg, justify="left", anchor="w",
                     wraplength=300).pack(fill="x", padx=10, pady=(0, 2))
        ctk.CTkLabel(self.adv_box, text=f"คะแนน {a['score']:+.1f} · เหตุผลทั้งหมดดูที่แท็บ \"ออเดอร์ที่เปิดอยู่\"", font=self._f(10),
                     text_color=COLOR_TEXT_MUTED, anchor="w").pack(fill="x", padx=10, pady=(0, 8))

    # ---- กราฟ ----
    def _draw(self):
        cv = self.canvas
        cv.delete("all")
        self.slots = []
        d = self.data
        if not d:
            return
        W, H = cv.winfo_width(), cv.winfo_height()
        if W < 120 or H < 120:
            return
        candles = d["candles"]
        n = len(candles)
        left, right, top, bottom = 10, 74, 12, 22
        pane = d.get("pane")
        pane_h = int((H - top - bottom) * 0.24) if pane else 0
        gap = 16 if pane else 0
        main_bottom = H - bottom - pane_h - gap
        lp = d["position"] or self.last_pos
        vals = [v for c in candles for v in (c["high"], c["low"])]
        for ln in d["lines"]:
            vals += [v for v in ln["values"] if v is not None]
        vals += [lv["price"] for lv in d["levels"]]
        vals += [v for v in (d["ask"], d["bid"]) if v]
        if lp:
            vals += [v for v in (lp["entry"], lp["sl"], lp["tp"]) if v and v > 0]
        for pth in d.get("paths") or []:
            vals += [v for _, v in pth["points"]]
        hi, lo = max(vals), min(vals)
        pad = max((hi - lo) * 0.06, 0.5)
        hi, lo = hi + pad, lo - pad

        def y_of(v):
            return top + (hi - v) / (hi - lo) * (main_bottom - top)

        yb_tag = y_of(d["bid"])
        ya_tag = y_of(d["ask"]) if d["ask"] else -999
        if abs(ya_tag - yb_tag) < 18:
            ya_tag -= 12
        for k in range(6):
            v = lo + (hi - lo) * k / 5
            y = y_of(v)
            cv.create_line(left, y, W - right, y, fill="#1E232C")
            if abs(y - yb_tag) > 12 and abs(y - ya_tag) > 10:   # ไม่ทับป้าย Bid / Ask
                cv.create_text(W - right + 6, y, text=f"{v:,.2f}", anchor="w", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 9))
        slot = (W - left - right - 24) / n   # เว้น 24px ระหว่างแท่งสุดท้ายกับแถบราคา (ผู้ใช้ขอ 8 ต.ค. 2026)
        bw = max(2, min(18, slot * 0.62))

        def xs(i):
            return left + slot * (i + 0.5)

        left_labels, right_labels = [], []   # ป้ายเส้นราคา — วางทีหลังแบบไม่ให้ทับกัน
        # แนวรับ/แนวต้าน
        for lv in d["levels"]:
            y = y_of(lv["price"])
            col = self.STYLE_COLORS.get(lv["style"], COLOR_TEXT_MUTED)
            cv.create_line(left, y, W - right, y, fill=col, dash=(8, 4))
            right_labels.append((y, lv["label"], col))
        # เส้นอินดิเคเตอร์ของแผน
        for ln in d["lines"]:
            col = self.STYLE_COLORS.get(ln["style"], COLOR_TEXT_MUTED)
            kw = {"dash": (5, 3)} if ln["style"] == "mid" else {}
            pts = []
            for i, v in enumerate(ln["values"] + [None]):
                if v is None:
                    if len(pts) >= 4:
                        cv.create_line(*pts, fill=col, width=2, **kw)
                    pts = []
                    continue
                pts += [xs(i), y_of(v)]
        # แท่งเทียน
        for i, c in enumerate(candles):
            cx = xs(i)
            up = c["close"] >= c["open"]
            col = COLOR_SUCCESS_GREEN if up else COLOR_DANGER_RED
            cv.create_line(cx, y_of(c["high"]), cx, y_of(c["low"]), fill=col)
            y1, y2 = y_of(c["open"]), y_of(c["close"])
            if abs(y1 - y2) < 1:
                y2 = y1 + 1
            live = i == n - 1
            cv.create_rectangle(cx - bw / 2, min(y1, y2), cx + bw / 2, max(y1, y2), fill=col,
                                outline=COLOR_GOLD_PRIMARY if live else col, width=2 if live else 1)
            every = max(1, int(round(n / max(1, (W - left - right) / 60))))
            if (i % every == 0 and i < n - max(2, int(every * 0.8))) or live:
                cv.create_text(cx, H - bottom + 11, text=("ปิดไม้" if self.closed else "ตอนนี้") if live else self._hhmm(c["time"]),
                               fill=COLOR_GOLD_PRIMARY if live else COLOR_TEXT_MUTED, font=(app_fonts.UI, 9, "bold" if live else "normal"))
            self.slots.append((cx - slot / 2, cx + slot / 2, i))
        # เส้นทางการเลื่อน SL/TP ระหว่างถือ (ไม้ที่ปิดแล้ว) — เส้นขั้นบันไดตามเวลา
        for pth in d.get("paths") or []:
            col = self.STYLE_COLORS.get(pth["style"], COLOR_TEXT_MUTED)
            pts = pth["points"]
            seg = []
            for i, c in enumerate(candles):
                t_end = c["time"] + 899
                if t_end < pts[0][0] or c["time"] > pts[-1][0]:
                    continue
                v = next((vv for tt, vv in reversed(pts) if tt <= t_end), pts[0][1])
                seg += [xs(i) - slot / 2, y_of(v), xs(i) + slot / 2, y_of(v)]
            if len(seg) >= 4:
                cv.create_line(*seg, fill=col, width=2)
        # ไม้: ราคาเข้า / SL / TP + จุดเข้าไม้บนแท่งที่เปิด
        if lp:
            side = d["side"]
            for val, col, txt in ((lp["entry"], COLOR_CYAN_ACCENT, f"{lp['type']} {lp['lot']:.2f} lot @ {lp['entry']:,.2f}"),
                                  (lp["tp"], COLOR_SUCCESS_GREEN, f"TP {lp['tp']:,.2f}"),
                                  (lp["sl"], COLOR_DANGER_RED, f"SL {lp['sl']:,.2f}" + (" (ล็อกกำไร)" if (lp["sl"] - lp["entry"]) * side > 0 else ""))):
                if not val or val <= 0:
                    continue
                yy = y_of(val)
                cv.create_line(left, yy, W - right, yy, fill=col, dash=(6, 3), width=2 if col == COLOR_CYAN_ACCENT else 1)
                left_labels.append((yy, txt, col))
            for i, c in enumerate(candles):
                if c["time"] <= lp["time"] < c["time"] + 900:
                    cx, ye = xs(i), y_of(lp["entry"])
                    s = 9
                    if side > 0:
                        cv.create_polygon(cx, ye + 3, cx - s, ye + 3 + s * 1.4, cx + s, ye + 3 + s * 1.4, fill=COLOR_CYAN_ACCENT, outline="#0B0D12")
                    else:
                        cv.create_polygon(cx, ye - 3, cx - s, ye - 3 - s * 1.4, cx + s, ye - 3 - s * 1.4, fill=COLOR_CYAN_ACCENT, outline="#0B0D12")
                    break
        # Ask / Bid (ไม้ที่ปิดแล้ว: ราคาตอนปิด + จุดปิดไม้)
        yb = y_of(d["bid"])
        if d["ask"]:
            ya = y_of(d["ask"])
            cv.create_line(left, ya, W - right, ya, fill="#5B6270", dash=(2, 4))
            cv.create_text(W - right + 6, ya - 12 if abs(ya - yb) < 18 else ya, text=f"A {d['ask']:,.2f}", anchor="w", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 8))
        if self.closed:
            cx, s = xs(n - 1), 8
            cv.create_polygon(cx, yb - s, cx + s, yb, cx, yb + s, cx - s, yb, fill=COLOR_GOLD_PRIMARY, outline="#0B0D12", width=2)
        cv.create_line(left, yb, W - right, yb, fill=COLOR_TEXT_MUTED, dash=(3, 3))
        cv.create_rectangle(W - right + 2, yb - 9, W - 2, yb + 9, fill=COLOR_GOLD_PRIMARY, outline="")
        cv.create_text(W - right + 6, yb, text=f"{d['bid']:,.2f}", anchor="w", fill="#111111", font=(app_fonts.UI, 9, "bold"))
        self._place_labels(left_labels, left + 4, "w", top, main_bottom)
        self._place_labels(right_labels, W - right - 4, "e", top, main_bottom)
        # หน้าต่างย่อย: RSI / MACD Histogram
        if pane:
            pt, pb = main_bottom + gap, H - bottom
            cv.create_rectangle(left, pt, W - right, pb, outline="#232833")
            pv = pane["values"]
            if pane["kind"] == "rsi":
                def py(v):
                    return pb - v / 100.0 * (pb - pt)
                if pane.get("band"):
                    b0, b1 = pane["band"]
                    cv.create_rectangle(left + 1, py(b1), W - right - 1, py(b0), fill="#14241C" if d["side"] > 0 else "#2A1719", outline="")
                for lvl in (30, 50, 70):
                    y = py(lvl)
                    cv.create_line(left, y, W - right, y, fill="#2A303C", dash=(2, 3))
                    cv.create_text(W - right + 6, y, text=str(lvl), anchor="w", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 8))
                pts = []
                for i, v in enumerate(pv):
                    if v is not None:
                        pts += [xs(i), py(max(0.0, min(100.0, v)))]
                if len(pts) >= 4:
                    cv.create_line(*pts, fill=COLOR_GOLD_PRIMARY, width=2)
                last = next((v for v in reversed(pv) if v is not None), None)
            else:
                mx = max([abs(v) for v in pv if v is not None] or [1.0]) or 1.0
                zero = (pt + pb) / 2
                sc = (pb - pt) / 2 * 0.9 / mx
                cv.create_line(left, zero, W - right, zero, fill="#2A303C")
                for i, v in enumerate(pv):
                    if v is None:
                        continue
                    cx = xs(i)
                    cv.create_rectangle(cx - bw / 2, min(zero, zero - v * sc), cx + bw / 2, max(zero, zero - v * sc),
                                        fill=COLOR_SUCCESS_GREEN if v >= 0 else COLOR_DANGER_RED, outline="")
                last = next((v for v in reversed(pv) if v is not None), None)
            cv.create_text(left + 6, pt + 3, text=pane["label"] + (f"  {last:,.2f}" if last is not None else ""), anchor="nw",
                           fill=COLOR_TEXT_PRIMARY, font=(app_fonts.UI, 9, "bold"))

    def _place_labels(self, items, x, anchor, y_min, y_max, gap=15):
        """วางป้ายเส้นราคาเรียงจากบนลงล่าง ดันลงเมื่อใกล้กันเกินไป + พื้นหลังทึบให้อ่านออกแม้ทับแท่งเทียน"""
        cv = self.canvas
        placed = []
        for y, txt, col in sorted(items):
            y = max(y - 8, y_min + 7)
            if placed and y - placed[-1] < gap:
                y = placed[-1] + gap
            y = min(y, y_max - 7)
            placed.append(y)
            t = cv.create_text(x, y, text=txt, anchor=anchor, fill=col, font=(app_fonts.UI, 9, "bold"))
            x0, y0, x1, y1 = cv.bbox(t)
            r = cv.create_rectangle(x0 - 3, y0, x1 + 3, y1, fill=COLOR_CARD_BG, outline=col)
            cv.tag_raise(t, r)

    def _hover(self, event):
        d = self.data
        if not d:
            return
        for x0, x1, i in self.slots:
            if x0 <= event.x < x1:
                c = d["candles"][i]
                extra = [f"{ln['label']} {ln['values'][i]:,.2f}" for ln in d["lines"] if ln["values"][i] is not None]
                pane = d.get("pane")
                if pane and pane["values"][i] is not None:
                    extra.append(f"{pane['label'].split(' ·')[0]} {pane['values'][i]:,.2f}")
                self.lbl_tip.configure(text=f"{self._hhmm(c['time'])} น. · O {c['open']:,.2f}  H {c['high']:,.2f}  L {c['low']:,.2f}  "
                                            f"C {c['close']:,.2f} ({c['close'] - c['open']:+.2f})" + (" · " + " · ".join(extra) if extra else ""))
                return


class PnlHistoryDialog(ctk.CTkToplevel):
    """กราฟแท่งกำไร/ขาดทุนสุทธิรายวัน และกราฟวงกลมวิเคราะห์ความสำเร็จรายแผน (ดึงจาก MT5)"""

    PRESETS = (("7 วัน", 7), ("14 วัน", 14), ("30 วัน", 30), ("เดือนนี้", "month"), ("90 วัน", 90))
    TH_MONTHS = ("ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.")

    PLAN_META = {
        "MA-Cross-Trend": {"label": "Plan 1 (MA M15)", "icon": "📈", "color": "#06B6D4"},
        "MA-Cross-H1-Trend": {"label": "Plan 2 (MA H1)", "icon": "👑", "color": "#8B5CF6"},
        "SMC-LiquidityHunt": {"label": "Plan 3 (SMC Hunt)", "icon": "⚡", "color": "#F59E0B"},
        "SR-SwingBounce": {"label": "Plan 4 (SR Bounce)", "icon": "🎯", "color": "#10B981"},
        "BB-H1-Reversion": {"label": "Plan 5 (BB Reversion)", "icon": "🌊", "color": "#3B82F6"},
        "PSAR-H1-Trend": {"label": "Plan 6 (PSAR H1)", "icon": "◆", "color": "#EC4899"},
        "เข้าเอง": {"label": "เข้าเอง (Manual)", "icon": "✋", "color": "#F97316"},
        "Manual-Quick": {"label": "เข้าเอง (Manual)", "icon": "✋", "color": "#F97316"},
    }

    @classmethod
    def _plan_info(cls, p_name: str) -> dict:
        if p_name in cls.PLAN_META:
            return cls.PLAN_META[p_name]
        if "Bounce" in p_name:
            return {"label": p_name, "icon": "🎯", "color": "#10B981"}
        if "Breakout" in p_name or "Trend" in p_name:
            return {"label": p_name, "icon": "📈", "color": "#06B6D4"}
        if "SMC" in p_name:
            return {"label": p_name, "icon": "⚡", "color": "#F59E0B"}
        if "BB" in p_name:
            return {"label": p_name, "icon": "🌊", "color": "#3B82F6"}
        if "PSAR" in p_name or "SAR" in p_name:
            return {"label": p_name, "icon": "◆", "color": "#EC4899"}
        return {"label": p_name, "icon": "🏷️", "color": "#64748B"}

    def __init__(self, parent):
        super().__init__(parent)
        from datetime import date, timedelta
        self._date, self._td = date, timedelta
        self.title("ประวัติกำไร / ขาดทุนรายวัน และสถิติความสำเร็จรายแผน")
        w, h = 980, 640
        self.configure(fg_color=COLOR_BG_DARK)
        # ไม่ใช้ transient เพื่อให้มีปุ่มขยายเต็มจอ/ย่อ บนแถบหัวหน้าต่าง
        self.after(10, self.lift)
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(800, 520)
        apply_dark_title_bar(self)
        self.rows, self.bars, self.weekly = [], [], False
        self.daily = []
        self.plans_stats = {"overall": {}, "plans": {}}
        self.overall_plans_dict = {}
        self.cur_hover_idx = None
        self.view_mode = "bar"  # "bar" | "pie"
        self._build()
        self.after(50, lambda: self._apply_preset(14))

    @staticmethod
    def _f(size, weight="normal"):
        return ctk.CTkFont(family=app_fonts.UI, size=size, weight=weight)

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 6))
        ctk.CTkLabel(top, text="ประวัติกำไร / ขาดทุน และสถิติความสำเร็จรายแผน", font=self._f(18, "bold"), text_color=COLOR_GOLD_PRIMARY).pack(side="left")
        ctk.CTkLabel(top, text="ทั้งบัญชี MT5 · รวม commission/swap · เวลาไทย · แยกตามแผนการเทรด", font=self._f(11), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=12)

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(0, 8))
        self.preset_btns = {}
        for label, key in self.PRESETS:
            b = ctk.CTkButton(bar, text=label, width=64, height=28, font=self._f(12), fg_color=COLOR_CARD_BG,
                              hover_color=COLOR_CARD_HOVER, border_width=1, border_color=COLOR_CARD_BORDER,
                              command=lambda k=key: self._apply_preset(k))
            b.pack(side="left", padx=(0, 6))
            self.preset_btns[key] = b
        ctk.CTkLabel(bar, text="จาก", font=self._f(12), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(14, 4))
        self.ent_from = ctk.CTkEntry(bar, width=96, height=28, font=self._f(12), placeholder_text="YYYY-MM-DD")
        self.ent_from.pack(side="left")
        ctk.CTkLabel(bar, text="ถึง", font=self._f(12), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=6)
        self.ent_to = ctk.CTkEntry(bar, width=96, height=28, font=self._f(12), placeholder_text="YYYY-MM-DD")
        self.ent_to.pack(side="left")
        ctk.CTkButton(bar, text="แสดง", width=56, height=28, font=self._f(12, "bold"), fg_color=COLOR_GOLD_PRIMARY,
                      text_color="#111111", hover_color=COLOR_GOLD_WARM, command=self._apply_custom).pack(side="left", padx=8)

        # สลับมุมมอง: กราฟแท่งรายวัน vs กราฟวงกลมความสำเร็จ
        view_box = ctk.CTkFrame(bar, fg_color=COLOR_CARD_BG, corner_radius=8, border_width=1, border_color=COLOR_CARD_BORDER)
        view_box.pack(side="right")
        self.btn_view_bar = ctk.CTkButton(
            view_box, text="📊 กราฟแท่งรายวัน", width=110, height=26, font=self._f(11, "bold"),
            fg_color=COLOR_GOLD_PRIMARY, text_color="#111111", hover_color=COLOR_GOLD_WARM, corner_radius=6,
            command=lambda: self._set_view_mode("bar")
        )
        self.btn_view_bar.pack(side="left", padx=2, pady=2)
        self.btn_view_pie = ctk.CTkButton(
            view_box, text="🍩 กราฟวงกลมความสำเร็จ", width=140, height=26, font=self._f(11),
            fg_color="transparent", text_color=COLOR_TEXT_MUTED, hover_color=COLOR_CARD_HOVER, corner_radius=6,
            command=lambda: self._set_view_mode("pie")
        )
        self.btn_view_pie.pack(side="left", padx=2, pady=2)

        self.summary = ctk.CTkFrame(self, fg_color="transparent")
        self.summary.pack(fill="x", padx=20, pady=(0, 8))
        self.summary.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="pnl_sum")
        self.sum_lbls = []
        for i, title in enumerate(("กำไรสุทธิช่วงนี้", "วันกำไร / ขาดทุน", "วันที่ดีที่สุด", "วันที่แย่ที่สุด")):
            c = ctk.CTkFrame(self.summary, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
            c.grid(row=0, column=i, padx=4, sticky="nsew")
            lbl_title = ctk.CTkLabel(c, text=title, font=self._f(11), text_color=COLOR_TEXT_MUTED)
            lbl_title.pack(anchor="w", padx=12, pady=(8, 0))
            v = ctk.CTkLabel(c, text="—", font=self._f(17, "bold"), text_color=COLOR_TEXT_PRIMARY)
            v.pack(anchor="w", padx=12)
            s = ctk.CTkLabel(c, text="", font=self._f(10), text_color=COLOR_TEXT_MUTED)
            s.pack(anchor="w", padx=12, pady=(0, 8))
            self.sum_lbls.append((lbl_title, v, s))

        box = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        self.canvas = tk.Canvas(box, bg=COLOR_CARD_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<Motion>", self._hover)
        self.canvas.bind("<Leave>", self._leave)

        # แถบด้านล่าง: สรุปข้อมูล และ Badges แผนการเทรดในแท่ง
        bot_frame = ctk.CTkFrame(self, fg_color="transparent")
        bot_frame.pack(fill="x", padx=20, pady=(0, 8))

        self.tip_default = "ชี้ที่แท่งเพื่อดูแผนการเทรดและจำนวนเหรียญในแท่งนั้น"
        self.lbl_tip = ctk.CTkLabel(bot_frame, text=self.tip_default, font=self._f(12, "bold"), text_color=COLOR_TEXT_MUTED)
        self.lbl_tip.pack(anchor="center", pady=(0, 3))

        self.pills_container = ctk.CTkFrame(bot_frame, fg_color="transparent")
        self.pills_container.pack(anchor="center")

    @staticmethod
    def _money(v, dp=2):
        """+26.34 / -22.46 / 0 (ไม่ใส่สัญลักษณ์ $ ตามสไตล์โปรแกรม)"""
        if abs(v) < 0.005:
            return "0"
        return f"{'+' if v > 0 else '-'}{abs(v):,.{dp}f}"

    def _fmt_date(self, d, year=False):
        return f"{d.day} {self.TH_MONTHS[d.month - 1]}" + (f" {d.year + 543}" if year else "")

    def _set_view_mode(self, mode):
        self.view_mode = mode
        if mode == "bar":
            self.btn_view_bar.configure(fg_color=COLOR_GOLD_PRIMARY, text_color="#111111", font=self._f(11, "bold"))
            self.btn_view_pie.configure(fg_color="transparent", text_color=COLOR_TEXT_MUTED, font=self._f(11))
            self.pills_container.pack(anchor="center")
            self._render_plan_pills(self.overall_plans_dict, title="ภาพรวมรายแผนทั้งช่วง:")
        else:
            self.btn_view_pie.configure(fg_color=COLOR_GOLD_PRIMARY, text_color="#111111", font=self._f(11, "bold"))
            self.btn_view_bar.configure(fg_color="transparent", text_color=COLOR_TEXT_MUTED, font=self._f(11))
            self.lbl_tip.configure(text="🍩 กราฟวงกลมความสำเร็จภาพรวม และสถิติวิเคราะห์รายแผนการเทรด", text_color=COLOR_GOLD_PRIMARY)
            self._render_plan_pills({}, title=None)

        self._summary(self.daily, self.plans_stats)
        self._draw()

    def _apply_preset(self, key):
        today = self._date.today()
        start = today.replace(day=1) if key == "month" else today - self._td(days=int(key) - 1)
        for k, b in self.preset_btns.items():
            b.configure(border_color=COLOR_GOLD_PRIMARY if k == key else COLOR_CARD_BORDER)
        self._load(start, today)

    def _apply_custom(self):
        from datetime import datetime
        try:
            start = datetime.strptime(self.ent_from.get().strip(), "%Y-%m-%d").date()
            end = datetime.strptime(self.ent_to.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            self.lbl_tip.configure(text="รูปแบบวันที่ไม่ถูกต้อง — ใช้ ปี-เดือน-วัน (ค.ศ.) เช่น 2026-10-01", text_color=COLOR_DANGER_RED)
            return
        if start > end:
            start, end = end, start
        if (end - start).days > 366:
            start = end - self._td(days=366)
        for b in self.preset_btns.values():
            b.configure(border_color=COLOR_CARD_BORDER)
        self._load(start, end)

    def _load(self, start, end):
        self.ent_from.delete(0, "end")
        self.ent_from.insert(0, start.isoformat())
        self.ent_to.delete(0, "end")
        self.ent_to.insert(0, end.isoformat())
        self.lbl_tip.configure(text="กำลังโหลดข้อมูลจาก MT5...", text_color=COLOR_TEXT_MUTED)
        self.update_idletasks()
        daily = bot_ctrl.get_daily_pnl(start, end)
        stats = bot_ctrl.get_plans_summary_stats(start, end)
        self.daily = daily
        self.plans_stats = stats

        # รวมรายแผนทั้งช่วง
        overall_plans = {}
        for r in daily:
            for p_name, p_stat in r.get("plans", {}).items():
                op = overall_plans.setdefault(p_name, {"profit": 0.0, "closed": 0, "wins": 0, "losses": 0})
                op["profit"] += p_stat.get("profit", 0.0)
                op["closed"] += p_stat.get("closed", 0)
                op["wins"] += p_stat.get("wins", 0)
                op["losses"] += p_stat.get("losses", 0)
        self.overall_plans_dict = overall_plans

        # ช่วงยาวเกิน 62 วัน → รวมเป็นรายสัปดาห์ให้แท่งอ่านง่าย
        if len(daily) > 62:
            weeks = {}
            for r in daily:
                k = r["date"] - self._td(days=r["date"].weekday())
                w = weeks.setdefault(k, {"date": k, "end": k + self._td(days=6), "profit": 0.0, "closed": 0, "plans": {}})
                w["profit"] += r["profit"]
                w["closed"] += r["closed"]
                for p_name, p_stat in r.get("plans", {}).items():
                    wp = w["plans"].setdefault(p_name, {"profit": 0.0, "closed": 0, "wins": 0, "losses": 0})
                    wp["profit"] += p_stat.get("profit", 0.0)
                    wp["closed"] += p_stat.get("closed", 0)
                    wp["wins"] += p_stat.get("wins", 0)
                    wp["losses"] += p_stat.get("losses", 0)
            self.rows, self.weekly = list(weeks.values()), True
        else:
            self.rows, self.weekly = daily, False

        self.tip_default = (f"{self._fmt_date(start, True)} – {self._fmt_date(end, True)} · "
                            + ("รวมรายสัปดาห์" if self.weekly else "รายวัน") + " · ชี้ที่แท่งเพื่อดูแผนและจำนวนเหรียญ")
        if self.view_mode == "bar":
            self.lbl_tip.configure(text=self.tip_default, text_color=COLOR_TEXT_MUTED)
            self._render_plan_pills(self.overall_plans_dict, title="ภาพรวมรายแผนทั้งช่วง:")
        self._summary(daily, stats)
        self._draw()

    def _summary(self, daily, stats):
        total = sum(r["profit"] for r in daily)
        pos = [r for r in daily if r["profit"] > 0.005]
        neg = [r for r in daily if r["profit"] < -0.005]
        best = max(daily, key=lambda r: r["profit"], default=None)
        worst = min(daily, key=lambda r: r["profit"], default=None)
        (c0, v0, s0), (c1, v1, s1), (c2, v2, s2), (c3, v3, s3) = self.sum_lbls

        c0.configure(text="กำไรสุทธิช่วงนี้")
        v0.configure(text=self._money(total), text_color=COLOR_SUCCESS_GREEN if total >= 0 else COLOR_DANGER_RED)
        s0.configure(text=f"ปิดไม้ {sum(r['closed'] for r in daily)} ไม้")

        if self.view_mode == "bar":
            c1.configure(text="วันกำไร / ขาดทุน")
            v1.configure(text=f"{len(pos)} / {len(neg)} วัน", text_color=COLOR_TEXT_PRIMARY)
            s1.configure(text=f"ไม่มีกำไร/ขาดทุน {len(daily) - len(pos) - len(neg)} วัน")

            c2.configure(text="วันที่ดีที่สุด")
            if best and best["profit"] > 0.005:
                v2.configure(text=self._money(best["profit"]), text_color=COLOR_SUCCESS_GREEN)
                s2.configure(text=self._fmt_date(best["date"], True))
            else:
                v2.configure(text="—", text_color=COLOR_TEXT_MUTED)
                s2.configure(text="")

            c3.configure(text="วันที่แย่ที่สุด")
            if worst and worst["profit"] < -0.005:
                v3.configure(text=self._money(worst["profit"]), text_color=COLOR_DANGER_RED)
                s3.configure(text=self._fmt_date(worst["date"], True))
            else:
                v3.configure(text="—", text_color=COLOR_TEXT_MUTED)
                s3.configure(text="")
        else:
            ov = stats.get("overall", {})
            c1.configure(text="Win Rate รวม")
            v1.configure(text=f"{ov.get('win_rate', 0.0):.1f}%", text_color=COLOR_GOLD_PRIMARY)
            s1.configure(text=f"ชนะ {ov.get('wins', 0)} / แพ้ {ov.get('losses', 0)} ไม้")

            c2.configure(text="Profit Factor (PF)")
            pf = ov.get("profit_factor", 0.0)
            v2.configure(text=f"{pf:.2f}", text_color=COLOR_SUCCESS_GREEN if pf >= 1.0 else COLOR_DANGER_RED)
            s2.configure(text=f"กำไร +{ov.get('gross_profit', 0):.2f} / ขาดทุน -{ov.get('gross_loss', 0):.2f}")

            c3.configure(text="แผนยอดกำไรสูงสุด")
            plans = stats.get("plans", {})
            best_plan = max(plans.items(), key=lambda x: x[1].get("profit", 0.0), default=(None, {}))
            if best_plan[0] and best_plan[1].get("profit", 0.0) > 0.005:
                bp_info = self._plan_info(best_plan[0])
                v3.configure(text=f"{self._money(best_plan[1]['profit'])} $", text_color=COLOR_SUCCESS_GREEN)
                s3.configure(text=f"{bp_info['icon']} {bp_info['label']}")
            else:
                v3.configure(text="—", text_color=COLOR_TEXT_MUTED)
                s3.configure(text="")

    def _render_plan_pills(self, plans_dict, title=None):
        for w in self.pills_container.winfo_children():
            w.destroy()
        if not plans_dict:
            return
        if title:
            ctk.CTkLabel(self.pills_container, text=title, font=self._f(10, "bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))

        # เรียงตามกำไรสุทธิสูงสุดก่อน
        sorted_plans = sorted(plans_dict.items(), key=lambda x: x[1].get("profit", 0.0), reverse=True)
        for p_name, p_stat in sorted_plans[:6]:
            p = p_stat.get("profit", 0.0)
            closed = p_stat.get("closed", 0)
            wins = p_stat.get("wins", 0)
            info = self._plan_info(p_name)

            pill = ctk.CTkFrame(self.pills_container, fg_color="#181C26", corner_radius=6, border_width=1, border_color="#242B38")
            pill.pack(side="left", padx=3, pady=2)

            p_color = COLOR_SUCCESS_GREEN if p > 0.005 else (COLOR_DANGER_RED if p < -0.005 else COLOR_TEXT_MUTED)
            txt = f"{info['icon']} {info['label']}: {self._money(p)} $"
            if closed > 0:
                txt += f" ({wins}/{closed} ชนะ)"
            lbl = ctk.CTkLabel(pill, text=txt, font=self._f(10, "bold"), text_color=p_color)
            lbl.pack(padx=8, pady=2)

    def _draw(self):
        cv = self.canvas
        cv.delete("all")
        if self.view_mode == "bar":
            self._draw_bar_chart()
        else:
            self._draw_pie_charts()

    def _draw_bar_chart(self):
        cv = self.canvas
        cv.delete("all")
        self.bars = []
        W, H = cv.winfo_width(), cv.winfo_height()
        if W < 50 or not self.rows:
            return
        left, right, top, bottom = 64, 14, 22, 34
        vals = [r["profit"] for r in self.rows]
        vmax, vmin = max(0.0, max(vals)), min(0.0, min(vals))
        if vmax - vmin < 1e-9:
            vmax, vmin = 1.0, -1.0
        pad = (vmax - vmin) * 0.12
        vmax, vmin = vmax + (pad if vmax > 0 else 0), vmin - (pad if vmin < 0 else 0)
        ch = H - top - bottom

        def y_of(v):
            return top + (vmax - v) / (vmax - vmin) * ch

        # เส้นตารางที่เลขกลม (มีเส้น 0 เสมอ)
        import math
        raw = (vmax - vmin) / 5
        mag = 10 ** math.floor(math.log10(raw))
        step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
        v = math.ceil(vmin / step) * step
        while v <= vmax + 1e-9:
            y = y_of(v)
            cv.create_line(left, y, W - right, y, fill="#20252F")
            cv.create_text(left - 8, y, text=self._money(v, 0 if step >= 1 else 2), anchor="e", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 9))
            v += step
        y0 = y_of(0)
        cv.create_line(left, y0, W - right, y0, fill="#4B5263")
        n = len(self.rows)
        slot = (W - left - right - 24) / n
        bw = max(2, min(38, slot * 0.68))
        label_every = max(1, int(round(n / max(1, (W - left - right) / 58))))

        for i, r in enumerate(self.rows):
            cx = left + slot * (i + 0.5)
            v = r["profit"]
            y = y_of(v)
            is_hovered = (i == self.cur_hover_idx)
            color = COLOR_SUCCESS_GREEN if v > 0 else COLOR_DANGER_RED

            if abs(v) < 0.005:
                cv.create_line(cx - bw / 2, y0, cx + bw / 2, y0, fill="#FFFFFF" if is_hovered else "#3A4050", width=3 if is_hovered else 2)
            else:
                rect_outline = "#FFFFFF" if is_hovered else ""
                rect_width = 2 if is_hovered else 0
                cv.create_rectangle(cx - bw / 2, min(y, y0), cx + bw / 2, max(y, y0), fill=color, outline=rect_outline, width=rect_width)
                if slot >= 34 or is_hovered:
                    lbl_y = y - 11 if v > 0 else y + 11
                    cv.create_text(cx, lbl_y, text=self._money(v), fill="#FFFFFF" if is_hovered else color, font=(app_fonts.UI, 8, "bold"))

            if i % label_every == 0:
                cv.create_text(cx, H - bottom + 14, text=self._fmt_date(r["date"]), fill="#FFFFFF" if is_hovered else COLOR_TEXT_MUTED, font=(app_fonts.UI, 9))
            self.bars.append((cx - slot / 2, cx + slot / 2, r))

    def _draw_pie_charts(self):
        cv = self.canvas
        cv.delete("all")
        W, H = cv.winfo_width(), cv.winfo_height()
        if W < 100 or H < 100:
            return

        ov = self.plans_stats.get("overall", {})
        plans = self.plans_stats.get("plans", {})

        # 1. ฝั่งซ้าย: ภาพรวมความสำเร็จ (Overall Success Donut)
        card1_w = int(W * 0.40)
        cv.create_rectangle(8, 8, card1_w, H - 8, fill="#12151D", outline="#1F2430", width=1)
        cv.create_text(24, 28, text="🍩 ภาพรวมความสำเร็จ (Overall Win Rate)", anchor="w", fill=COLOR_GOLD_PRIMARY, font=(app_fonts.UI, 12, "bold"))
        cv.create_text(24, 46, text="อัตราส่วนไม้ชนะ / แพ้ และ Profit Factor ของพอร์ต", anchor="w", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 9))

        cx1 = card1_w // 2
        cy1 = int(H * 0.38)
        R1 = min(card1_w // 2 - 30, int(H * 0.22), 85)
        r1 = int(R1 * 0.62)

        closed = ov.get("closed", 0)
        wins = ov.get("wins", 0)
        losses = ov.get("losses", 0)

        if closed > 0:
            cur = 90.0
            ext_win = (wins / closed) * 360.0
            cv.create_arc(cx1 - R1, cy1 - R1, cx1 + R1, cy1 + R1, start=cur, extent=-ext_win, fill=COLOR_SUCCESS_GREEN, outline="", style="pieslice")
            cur -= ext_win
            ext_loss = (losses / closed) * 360.0
            cv.create_arc(cx1 - R1, cy1 - R1, cx1 + R1, cy1 + R1, start=cur, extent=-ext_loss, fill=COLOR_DANGER_RED, outline="", style="pieslice")
        else:
            cv.create_oval(cx1 - R1, cy1 - R1, cx1 + R1, cy1 + R1, fill="#1E222D", outline="")

        cv.create_oval(cx1 - r1, cy1 - r1, cx1 + r1, cy1 + r1, fill="#12151D", outline="")
        cv.create_text(cx1, cy1 - 10, text=f"{ov.get('win_rate', 0.0):.1f}%", fill="#FFFFFF", font=(app_fonts.UI, 16, "bold"))
        cv.create_text(cx1, cy1 + 8, text="Win Rate รวม", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 9))
        p_val = ov.get("profit", 0.0)
        p_color = COLOR_SUCCESS_GREEN if p_val >= 0 else COLOR_DANGER_RED
        cv.create_text(cx1, cy1 + 22, text=f"{self._money(p_val)} $", fill=p_color, font=(app_fonts.UI, 9, "bold"))

        # Left Metrics Box
        my = cy1 + R1 + 22
        bw = (card1_w - 48) // 2
        # Chip 1 (Wins)
        cv.create_rectangle(24, my, 24 + bw, my + 38, fill="#10251E", outline="#1A3B30", width=1)
        cv.create_text(24 + bw // 2, my + 12, text=f"🏆 ชนะ {wins} ไม้", fill=COLOR_SUCCESS_GREEN, font=(app_fonts.UI, 10, "bold"))
        cv.create_text(24 + bw // 2, my + 26, text=f"อัตราส่วน {ov.get('win_rate', 0.0):.1f}%", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 8))

        # Chip 2 (Losses)
        cv.create_rectangle(24 + bw + 8, my, 24 + bw * 2 + 8, my + 38, fill="#2A1618", outline="#441E22", width=1)
        loss_pct = round(losses / closed * 100, 1) if closed > 0 else 0
        cv.create_text(24 + bw + 8 + bw // 2, my + 12, text=f"❌ แพ้ {losses} ไม้", fill=COLOR_DANGER_RED, font=(app_fonts.UI, 10, "bold"))
        cv.create_text(24 + bw + 8 + bw // 2, my + 26, text=f"อัตราส่วน {loss_pct:.1f}%", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 8))

        # Chip 3 (Summary Bottom)
        my2 = my + 44
        cv.create_rectangle(24, my2, card1_w - 16, my2 + 42, fill="#181C26", outline="#232836", width=1)
        cv.create_text(34, my2 + 13, text=f"⚖️ Profit Factor: {ov.get('profit_factor', 0.0):.2f}", anchor="w", fill="#FFFFFF", font=(app_fonts.UI, 9, "bold"))
        cv.create_text(34, my2 + 28, text=f"💰 กำไรรวม: +{ov.get('gross_profit', 0.0):.2f} $  |  ขาดทุน: -{ov.get('gross_loss', 0.0):.2f} $", anchor="w", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 8))

        # 2. ฝั่งขวา: ความสำเร็จรายแผน (Plans Success Donut & Cards)
        card2_x = card1_w + 12
        card2_w = W - card2_x - 8
        cv.create_rectangle(card2_x, 8, W - 8, H - 8, fill="#12151D", outline="#1F2430", width=1)
        cv.create_text(card2_x + 16, 28, text="🍩 ความสำเร็จรายแผนการเทรด (Trading Plans Analytics)", anchor="w", fill=COLOR_GOLD_PRIMARY, font=(app_fonts.UI, 12, "bold"))
        cv.create_text(card2_x + 16, 46, text="สัดส่วนการปิดไม้, Win Rate %, และกำไรสุทธิแยกตามแผน", anchor="w", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 9))

        cx2 = card2_x + 95
        cy2 = int(H * 0.44)
        R2 = min(75, int(H * 0.20))
        r2 = int(R2 * 0.58)

        tot_plan_trades = sum(p.get("closed", 0) for p in plans.values())
        if tot_plan_trades > 0:
            cur = 90.0
            for pname, pstat in sorted(plans.items(), key=lambda x: x[1].get("closed", 0), reverse=True):
                c_cnt = pstat.get("closed", 0)
                if c_cnt <= 0:
                    continue
                ext = (c_cnt / tot_plan_trades) * 360.0
                c = self._plan_info(pname)["color"]
                cv.create_arc(cx2 - R2, cy2 - R2, cx2 + R2, cy2 + R2, start=cur, extent=-ext, fill=c, outline="", style="pieslice")
                cur -= ext
        else:
            cv.create_oval(cx2 - R2, cy2 - R2, cx2 + R2, cy2 + R2, fill="#1E222D", outline="")

        cv.create_oval(cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2, fill="#12151D", outline="")
        best_p = max(plans.items(), key=lambda x: x[1].get("profit", 0.0), default=(None, {}))
        cv.create_text(cx2, cy2 - 8, text=f"{best_p[1].get('profit', 0.0):+.2f} $", fill=COLOR_SUCCESS_GREEN, font=(app_fonts.UI, 11, "bold"))
        cv.create_text(cx2, cy2 + 8, text="ยอดสูงสุด", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 8))

        # Legend & Cards on Right
        lx = cx2 + R2 + 28
        ly = 72
        for pname, pstat in sorted(plans.items(), key=lambda x: x[1].get("profit", 0.0), reverse=True)[:8]:
            info = self._plan_info(pname)
            p = pstat.get("profit", 0.0)
            wr = pstat.get("win_rate", 0.0)
            wins_p = pstat.get("wins", 0)
            closed_p = pstat.get("closed", 0)
            pf = pstat.get("profit_factor", 0.0)

            # Row card
            cv.create_rectangle(lx, ly, W - 24, ly + 32, fill="#181C26", outline="#232732", width=1)
            # Color dot & Name
            cv.create_rectangle(lx + 8, ly + 11, lx + 18, ly + 21, fill=info["color"], outline="")
            cv.create_text(lx + 24, ly + 11, text=f"{info['icon']} {info['label']}", anchor="w", fill="#FFFFFF", font=(app_fonts.UI, 9, "bold"))
            # Subtext (Trades & WR)
            cv.create_text(lx + 24, ly + 23, text=f"{wins_p}/{closed_p} ไม้ ({wr:.1f}%) · PF {pf:.2f}", anchor="w", fill=COLOR_TEXT_MUTED, font=(app_fonts.UI, 8))
            # Profit text
            p_col = COLOR_SUCCESS_GREEN if p > 0.005 else (COLOR_DANGER_RED if p < -0.005 else COLOR_TEXT_MUTED)
            cv.create_text(W - 36, ly + 11, text=f"{self._money(p)} $", anchor="e", fill=p_col, font=(app_fonts.UI, 10, "bold"))
            # Mini bar
            bar_w = 64
            rx = W - 36
            cv.create_rectangle(rx - bar_w, ly + 21, rx, ly + 25, fill="#232732", outline="")
            filled_w = max(0, min(bar_w, int(bar_w * wr / 100)))
            if filled_w > 0:
                cv.create_rectangle(rx - bar_w, ly + 21, rx - bar_w + filled_w, ly + 25, fill=info["color"], outline="")
            ly += 36

    def _hover(self, event):
        if self.view_mode != "bar":
            return
        for idx, (x0, x1, r) in enumerate(self.bars):
            if x0 <= event.x < x1:
                if self.cur_hover_idx != idx:
                    self.cur_hover_idx = idx
                    when = (f"สัปดาห์ {self._fmt_date(r['date'])} – {self._fmt_date(r['end'], True)}" if self.weekly
                            else self._fmt_date(r["date"], True))
                    v = r["profit"]
                    word = "กำไร" if v > 0.005 else ("ขาดทุน" if v < -0.005 else "ไม่มีกำไร/ขาดทุน")
                    self.lbl_tip.configure(
                        text=f"📅 {when} · {word} {self._money(v)} $ · ปิดไม้ {r['closed']} ไม้",
                        text_color=COLOR_SUCCESS_GREEN if v > 0.005 else COLOR_DANGER_RED if v < -0.005 else COLOR_TEXT_MUTED
                    )
                    self._render_plan_pills(r.get("plans", {}), title=f"แผนในแท่ง {self._fmt_date(r['date'])}:")
                    self._draw_bar_chart()
                return
        if self.cur_hover_idx is not None:
            self._leave()

    def _leave(self, event=None):
        if self.cur_hover_idx is not None:
            self.cur_hover_idx = None
            if self.view_mode == "bar":
                self.lbl_tip.configure(text=self.tip_default, text_color=COLOR_TEXT_MUTED)
                self._render_plan_pills(self.overall_plans_dict, title="ภาพรวมรายแผนทั้งช่วง:")
                self._draw_bar_chart()


class UserStatsDialog(ctk.CTkToplevel):
    """
    หน้าต่างแสดงสถิติการเทรดละเอียดแยกตาม User และแยกตาม Trading Plan (5 แผนทองคำ)
    แสดงจำนวนการเข้าไม้ (Total Trades), ชนะ/แพ้ (Win/Loss), Win Rate %, กำไรสุทธิ ($ Net Profit), และ Profit Factor
    """
    def __init__(self, parent, user_id=None, email=None):
        super().__init__(parent)
        self.parent = parent
        cur_u = license_mgr.get_current_user()
        self.user_id = user_id or cur_u.get("user_id", "local_user")
        self.email = email or cur_u.get("email", "Trader")

        self.title(f"📊 สถิติการเทรดรายแผน (Trading Plan Analytics) - {self.email}")
        self.geometry("860x600")
        self.minsize(780, 520)
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        # วางกึ่งกลางหน้าต่างหลัก
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        x = px + max(0, (pw - 860) // 2)
        y = py + max(0, (ph - 600) // 2)
        self.geometry(f"860x600+{x}+{y}")
        apply_dark_title_bar(self)

        self._build_ui()

    def _build_ui(self):
        # ส่วนหัว (Header)
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 10))

        ctk.CTkLabel(
            hdr,
            text="📊 สถิติการเทรดรายบุคคลและประสิทธิภาพรายแผน",
            font=ctk.CTkFont(family=app_fonts.UI, size=20, weight="bold"),
            text_color=COLOR_GOLD_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            hdr,
            text=f"บัญชีผู้ใช้: {self.email} (ID: {self.user_id}) • อัปเดตข้อมูลแบบ Real-time",
            font=ctk.CTkFont(family=app_fonts.UI, size=12),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(2, 0))

        # โหลดสถิติของ User คนนี้
        u_data = stats_mgr.get_user_stats(self.user_id)
        ov = u_data.get("overall", {})
        total_t = ov.get("total_trades", 0)
        win_t = ov.get("win_trades", 0)
        loss_t = ov.get("loss_trades", 0)
        wr = ov.get("win_rate_pct", 0.0)
        tot_prof = ov.get("total_profit_usd", 0.0)
        pf = ov.get("profit_factor", 0.0)

        # การ์ดสรุปรวม 4 กล่อง (Overall Performance)
        summary_grid = ctk.CTkFrame(self, fg_color="transparent")
        summary_grid.pack(fill="x", padx=24, pady=(0, 14))
        summary_grid.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="summary_cards")

        cards = [
            ("เข้าไม้รวมทั้งหมด", f"{total_t} ไม้", f"ชนะ: {win_t} | แพ้: {loss_t}", COLOR_CYAN_ACCENT),
            ("อัตราการชนะ (Win Rate)", f"{wr:.1f}%", f"เกณฑ์เป้าหมาย: > 50%", COLOR_GOLD_PRIMARY if wr >= 50 else COLOR_TEXT_MUTED),
            ("กำไรสุทธิรวม (Net Profit)", f"{tot_prof:+,.2f}", "คำนวณจากทุกไม้ที่ปิด", COLOR_SUCCESS_GREEN if tot_prof >= 0 else COLOR_DANGER_RED),
            ("อัตรากำไร (Profit Factor)", f"{pf:.2f}", "Gross Win / Gross Loss", COLOR_GOLD_WARM if pf >= 1.5 else COLOR_TEXT_MUTED)
        ]

        for col, (title, val, sub, colr) in enumerate(cards):
            c_frame = ctk.CTkFrame(summary_grid, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
            c_frame.grid(row=0, column=col, padx=5, sticky="nsew")
            c_inner = ctk.CTkFrame(c_frame, fg_color="transparent")
            c_inner.pack(padx=12, pady=10)
            ctk.CTkLabel(c_inner, text=title, font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(anchor="w")
            ctk.CTkLabel(c_inner, text=val, font=ctk.CTkFont(family=app_fonts.UI, size=18, weight="bold"), text_color=colr).pack(anchor="w", pady=(4, 2))
            ctk.CTkLabel(c_inner, text=sub, font=ctk.CTkFont(family=app_fonts.UI, size=10), text_color=COLOR_TEXT_MUTED).pack(anchor="w")

        # ตารางเปรียบเทียบแต่ละแผน (Plan Breakdown Table)
        tbl_container = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        tbl_container.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        # หัวตาราง (Table Header)
        th_frame = ctk.CTkFrame(tbl_container, fg_color="#1A1E27", height=38, corner_radius=8)
        th_frame.pack(fill="x", padx=12, pady=10)
        th_frame.grid_columnconfigure(0, weight=3) # Plan Name
        th_frame.grid_columnconfigure((1, 2, 3, 4, 5), weight=2)

        headers = [("แผนการเทรด (Trading Plan)", 0, "w"), ("เข้าไม้ (Trades)", 1, "center"), ("ชนะ / แพ้ (W/L)", 2, "center"),
                   ("Win Rate (%)", 3, "center"), ("กำไรสุทธิ ($ Profit)", 4, "center"), ("Profit Factor", 5, "center")]
        for title, col, anc in headers:
            lbl = ctk.CTkLabel(th_frame, text=title, font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"), text_color=COLOR_GOLD_PRIMARY)
            lbl.grid(row=0, column=col, padx=8, pady=8, sticky="" if anc == "center" else anc)  # Tk ไม่รับ sticky="center"

        # รายการแต่ละแผน (Plan Rows)
        scroll_rows = ctk.CTkScrollableFrame(tbl_container, fg_color="transparent")
        scroll_rows.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        plans_dict = u_data.get("plans", {})
        for idx, p_name in enumerate(STANDARD_PLANS):
            p_stat = plans_dict.get(p_name, {})
            p_trades = p_stat.get("total_trades", 0)
            p_win = p_stat.get("win_trades", 0)
            p_loss = p_stat.get("loss_trades", 0)
            p_wr = p_stat.get("win_rate_pct", 0.0)
            p_profit = p_stat.get("total_profit_usd", 0.0)
            p_pf = p_stat.get("profit_factor", 0.0)

            bg_row = "#12151B" if idx % 2 == 0 else "#161A21"
            row_frame = ctk.CTkFrame(scroll_rows, fg_color=bg_row, corner_radius=6)
            row_frame.pack(fill="x", pady=2)
            row_frame.grid_columnconfigure(0, weight=3)
            row_frame.grid_columnconfigure((1, 2, 3, 4, 5), weight=2)

            # 1. ชื่อแผน
            ctk.CTkLabel(row_frame, text=p_name, font=ctk.CTkFont(family=app_fonts.UI, size=12, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=8, pady=8, sticky="w")
            # 2. จำนวนเข้าไม้
            ctk.CTkLabel(row_frame, text=f"{p_trades} ไม้", font=ctk.CTkFont(family=app_fonts.UI, size=12), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=1, padx=8)
            # 3. ชนะ/แพ้
            ctk.CTkLabel(row_frame, text=f"{p_win}W / {p_loss}L", font=ctk.CTkFont(family=app_fonts.UI, size=12), text_color=COLOR_TEXT_MUTED).grid(row=0, column=2, padx=8)
            # 4. Win Rate %
            wr_colr = COLOR_SUCCESS_GREEN if p_wr >= 50 else (COLOR_GOLD_WARM if p_wr >= 40 else COLOR_TEXT_MUTED)
            ctk.CTkLabel(row_frame, text=f"{p_wr:.1f}%", font=ctk.CTkFont(family=app_fonts.UI, size=12, weight="bold"), text_color=wr_colr).grid(row=0, column=3, padx=8)
            # 5. Profit USD
            prof_colr = COLOR_SUCCESS_GREEN if p_profit > 0 else (COLOR_DANGER_RED if p_profit < 0 else COLOR_TEXT_MUTED)
            ctk.CTkLabel(row_frame, text=f"{p_profit:+,.2f}", font=ctk.CTkFont(family=app_fonts.UI, size=12, weight="bold"), text_color=prof_colr).grid(row=0, column=4, padx=8)
            # 6. Profit Factor
            ctk.CTkLabel(row_frame, text=f"{p_pf:.2f}", font=ctk.CTkFont(family=app_fonts.UI, size=12), text_color=COLOR_GOLD_WARM if p_pf >= 1.5 else COLOR_TEXT_MUTED).grid(row=0, column=5, padx=8)

        # ปุ่มปิดหน้าต่าง
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 18))

        ctk.CTkButton(
            btn_frame,
            text="ปิดหน้าต่าง",
            font=ctk.CTkFont(family=app_fonts.UI, size=13),
            fg_color="#252A35",
            hover_color="#323846",
            height=38,
            corner_radius=8,
            command=self.destroy
        ).pack(side="right")


class MainTradingApp(ctk.CTk):
    """
    หน้าต่างโปรแกรมหลัก AI MetaTrader 5 Gold Pro
    ประกอบด้วยระบบ Login, Dashboard ตรวจสอบพอร์ต, สัญญาณทองคำสด และ Terminal Console
    """
    def __init__(self):
        super().__init__()

        self.title(f"AI Gold Commander Pro - GoldBot24 (v{APP_VERSION})")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{min(1320, sw - 40)}x{min(840, sh - 90)}")
        self.minsize(min(1040, sw - 40), min(620, sh - 90))
        if sh <= 900 or sw <= 1400:
            # จอโน้ตบุ๊ก (เช่น 1366x768) — เปิดเต็มจอเพื่อไม่ให้ส่วนล่างถูกตัด
            self.after(0, lambda: self.state("zoomed"))
        self.configure(fg_color=COLOR_BG_DARK)
        apply_dark_title_bar(self)

        # ตั้งค่าไอคอนหน้าต่าง Windows
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "app_icon.ico")
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            icon_path = os.path.join(base_dir, "assets", "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # ตัวแปรสถานะ
        self.is_logged_in = False
        self.auto_scroll_logs = True

        # ผูก Callback กับ Bot Controller
        bot_ctrl.set_status_callback(self._on_bot_status_changed)
        bot_ctrl.set_time_expired_callback(self._on_time_expired)
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

        # สร้าง Container หลักสำหรับการสลับหน้าระหว่าง Login กับ Dashboard
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.login_view = None
        self.dashboard_view = None

        # ตรวจสอบว่าเคยเข้าสู่ระบบและจดจำไว้หรือไม่
        if license_mgr.is_authenticated and license_mgr.session_data.get("remember_me"):
            self.show_dashboard_view()
        else:
            self.show_login_view()

        # เริ่มต้นลูปอัปเดต UI เรียลไทม์
        self.after(500, self._realtime_ui_loop)

    def _on_window_close(self):
        """เมื่อผู้ใช้ปิดหน้าต่างโปรแกรม"""
        try:
            sound_manager.stop_volatility_siren()
            if bot_ctrl.is_active:
                bot_ctrl.stop_bot()
        except Exception:
            pass
        self.destroy()

    # =========================================================================
    # 1. หน้าจอเข้าสู่ระบบและสมัครสมาชิก (LOGIN & REGISTER VIEW)
    # =========================================================================
    def show_login_view(self):
        """แสดงหน้าจอเข้าสู่ระบบ / สมัครสมาชิกใหม่"""
        self.is_logged_in = False
        if self.dashboard_view:
            self.dashboard_view.destroy()
            self.dashboard_view = None

        self.login_view = ctk.CTkFrame(self.container, fg_color="transparent")
        self.login_view.pack(fill="both", expand=True)

        # กล่องการ์ดเข้าสู่ระบบจัดกึ่งกลาง
        card_wrapper = ctk.CTkFrame(self.login_view, fg_color="transparent")
        card_wrapper.place(relx=0.5, rely=0.5, anchor="center")

        login_card = ctk.CTkFrame(
            card_wrapper,
            fg_color=COLOR_CARD_BG,
            corner_radius=16,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            width=480
        )
        login_card.pack(padx=20, pady=20)

        inner = ctk.CTkFrame(login_card, fg_color="transparent")
        inner.pack(padx=32, pady=28, fill="both")

        # ตราสัญลักษณ์และชื่อโปรแกรม
        ctk.CTkLabel(
            inner,
            text="👑",
            font=ctk.CTkFont(size=40)
        ).pack(pady=(0, 2))

        ctk.CTkLabel(
            inner,
            text="AI Gold Commander Pro",
            font=ctk.CTkFont(family=app_fonts.UI, size=22, weight="bold"),
            text_color=COLOR_GOLD_PRIMARY
        ).pack()

        ctk.CTkLabel(
            inner,
            text="Next-Gen Autonomous Gold Specialist (XAUUSD) • GoldBot24",
            font=ctk.CTkFont(family=app_fonts.UI, size=12),
            text_color=COLOR_TEXT_MUTED
        ).pack(pady=(2, 4))

        version_badge = ctk.CTkFrame(inner, fg_color=COLOR_GOLD_BG, corner_radius=6, border_width=1, border_color="#523E15")
        version_badge.pack(pady=(0, 16))
        ctk.CTkLabel(
            version_badge,
            text=f"v{APP_VERSION} • GoldBot24 Cloud Service (1.00 THB/hr)",
            font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"),
            text_color=COLOR_GOLD_WARM
        ).pack(padx=10, pady=4)

        # แถบสลับโหมด Login vs Register
        self.auth_mode = "login"
        self.seg_auth = ctk.CTkSegmentedButton(
            inner,
            values=["🔑 เข้าสู่ระบบ (Sign In)", "✨ สมัครสมาชิกใหม่ (รับฟรี 48 ชม.)"],
            font=ctk.CTkFont(family=app_fonts.UI, size=12, weight="bold"),
            selected_color=COLOR_GOLD_WARM,
            selected_hover_color=COLOR_GOLD_DARK,
            unselected_color="#1A1E27",
            unselected_hover_color="#262B36",
            text_color="#FFFFFF",
            command=self._on_auth_tab_change
        )
        self.seg_auth.set("🔑 เข้าสู่ระบบ (Sign In)")
        self.seg_auth.pack(fill="x", pady=(0, 16))

        # โซนฟอร์มกรอกข้อมูล
        self.form_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self.form_frame.pack(fill="x")

        # 1) ชื่อแสดงผล (สำหรับ Register)
        self.lbl_reg_name = ctk.CTkLabel(
            self.form_frame,
            text="ชื่อแสดงผล (Display Name):",
            font=ctk.CTkFont(family=app_fonts.UI, size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.entry_reg_name = ctk.CTkEntry(
            self.form_frame,
            font=ctk.CTkFont(family=app_fonts.UI, size=13),
            height=40,
            corner_radius=8,
            border_width=1,
            border_color="#252A35",
            fg_color="#101218",
            placeholder_text="เช่น GoldTrader99"
        )

        # 2) อีเมล
        self.lbl_email = ctk.CTkLabel(
            self.form_frame,
            text="อีเมลสำหรับใช้งาน (Email):",
            font=ctk.CTkFont(family=app_fonts.UI, size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.lbl_email.pack(anchor="w", pady=(0, 4))

        # อีเมล/รหัสผ่านล่าสุดที่ติ๊ก "จดจำ" ไว้ (รหัสผ่านเข้ารหัสด้วย Windows DPAPI)
        remembered_email, remembered_pwd = secure_store.load_login()
        saved_user = remembered_email or license_mgr.session_data.get("email") or ""
        self.entry_email = ctk.CTkEntry(
            self.form_frame,
            font=ctk.CTkFont(family=app_fonts.UI, size=13),
            height=40,
            corner_radius=8,
            border_width=1,
            border_color="#252A35",
            fg_color="#101218",
            placeholder_text="user@example.com"
        )
        self.entry_email.pack(fill="x", pady=(0, 10))
        if saved_user:
            self.entry_email.insert(0, saved_user)

        # 3) รหัสผ่าน
        self.lbl_pwd = ctk.CTkLabel(
            self.form_frame,
            text="รหัสผ่าน (Password):",
            font=ctk.CTkFont(family=app_fonts.UI, size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.lbl_pwd.pack(anchor="w", pady=(0, 4))

        self.entry_pwd = ctk.CTkEntry(
            self.form_frame,
            font=ctk.CTkFont(family=app_fonts.UI, size=13),
            height=40,
            corner_radius=8,
            border_width=1,
            border_color="#252A35",
            fg_color="#101218",
            show="•",
            placeholder_text="รหัสผ่านอย่างน้อย 6 ตัวอักษร"
        )
        self.entry_pwd.pack(fill="x", pady=(0, 6))
        self.entry_pwd.bind("<Return>", lambda e: self._on_auth_submit())

        # แสดง/ซ่อนรหัสผ่าน — ช่วยเช็คว่าพิมพ์ด้วยแป้นภาษาไทยหรือ Caps Lock อยู่หรือไม่
        self.show_pwd_var = tk.BooleanVar(value=False)
        self.chk_show_pwd = ctk.CTkCheckBox(
            self.form_frame,
            text="แสดงรหัสผ่าน",
            variable=self.show_pwd_var,
            command=self._toggle_show_password,
            font=ctk.CTkFont(family=app_fonts.UI, size=11),
            text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_GOLD_WARM,
            hover_color=COLOR_GOLD_DARK,
            checkbox_width=16,
            checkbox_height=16
        )
        self.chk_show_pwd.pack(anchor="w", pady=(0, 10))

        # ลืมรหัสผ่าน → หน้าเว็บรีเซ็ตรหัสผ่าน (ส่งรหัสยืนยันทางอีเมล)
        self.lbl_forgot = ctk.CTkLabel(
            self.form_frame,
            text="ลืมรหัสผ่าน?",
            font=ctk.CTkFont(family=app_fonts.UI, size=11, underline=True),
            text_color=COLOR_CYAN_ACCENT,
            cursor="hand2",
        )
        self.lbl_forgot.place(relx=1.0, y=0, anchor="ne")
        self.lbl_forgot.bind("<Button-1>", lambda e: self._open_forgot_password())

        # 4) ยืนยันรหัสผ่าน (สำหรับ Register)
        self.lbl_reg_confirm = ctk.CTkLabel(
            self.form_frame,
            text="ยืนยันรหัสผ่านอีกครั้ง (Confirm Password):",
            font=ctk.CTkFont(family=app_fonts.UI, size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.entry_reg_confirm = ctk.CTkEntry(
            self.form_frame,
            font=ctk.CTkFont(family=app_fonts.UI, size=13),
            height=40,
            corner_radius=8,
            border_width=1,
            border_color="#252A35",
            fg_color="#101218",
            show="•",
            placeholder_text="••••••••"
        )

        # ป้ายของขวัญต้อนรับสมาชิกใหม่
        self.bonus_frame = ctk.CTkFrame(
            inner,
            fg_color=COLOR_GOLD_BG,
            corner_radius=8,
            border_width=1,
            border_color=COLOR_GOLD_DARK
        )
        ctk.CTkLabel(
            self.bonus_frame,
            text="🎁 สิทธิพิเศษ: สมาชิกใหม่รับสิทธิ์ทดลองเทรดจริงฟรี 48 ชั่วโมงทันที!",
            font=ctk.CTkFont(family=app_fonts.UI, size=11, weight="bold"),
            text_color="#FDE68A"
        ).pack(padx=10, pady=6)

        # ตัวเลือกจดจำการล็อกอิน (เฉพาะโหมดเข้าสู่ระบบ)
        if remembered_pwd:
            self.entry_pwd.insert(0, remembered_pwd)
        self.remember_var = tk.BooleanVar(value=bool(remembered_email) or license_mgr.session_data.get("remember_me", True))
        self.chk_remember = ctk.CTkCheckBox(
            inner,
            text="จดจำการเข้าสู่ระบบในเครื่องนี้",
            variable=self.remember_var,
            font=ctk.CTkFont(family=app_fonts.UI, size=12),
            text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_GOLD_WARM,
            hover_color=COLOR_GOLD_DARK
        )
        self.chk_remember.pack(anchor="w", pady=(0, 12))

        # ข้อความแสดงสถานะ
        self.lbl_login_status = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(family=app_fonts.UI, size=12, weight="bold"),
            text_color=COLOR_DANGER_RED
        )
        self.lbl_login_status.pack(pady=(0, 10))

        # ปุ่มดำเนินการหลัก
        self.btn_auth_submit = ctk.CTkButton(
            inner,
            text="🚀 เข้าสู่ระบบ (Sign In)",
            font=ctk.CTkFont(family=app_fonts.UI, size=14, weight="bold"),
            fg_color=COLOR_GOLD_WARM,
            hover_color=COLOR_GOLD_DARK,
            text_color="#1A1406",
            height=44,
            corner_radius=8,
            command=self._on_auth_submit
        )
        self.btn_auth_submit.pack(fill="x", pady=(0, 14))

        # ลิงก์ไปยังหน้าเว็บ
        link_frame = ctk.CTkFrame(inner, fg_color="transparent")
        link_frame.pack(fill="x")
        
        lbl_web = ctk.CTkLabel(
            link_frame,
            text="🌐 เติมชั่วโมงและดูเรดาร์สดผ่านเว็บ: GoldBot24 (goldbot24.vercel.app)",
            font=ctk.CTkFont(family=app_fonts.UI, size=11, underline=True),
            text_color=COLOR_CYAN_ACCENT,
            cursor="hand2"
        )
        lbl_web.pack()
        lbl_web.bind("<Button-1>", lambda e: webbrowser.open("https://goldbot24.vercel.app"))

    def _on_auth_tab_change(self, selected_value: str):
        """สลับหน้าระหว่างโหมดเข้าสู่ระบบ และ สมัครสมาชิกใหม่"""
        self.lbl_login_status.configure(text="")
        if "สมัครสมาชิก" in selected_value:
            self.auth_mode = "register"
            # แสดงช่อง Display Name ไว้บนสุด
            self.lbl_reg_name.pack(before=self.lbl_email, anchor="w", pady=(0, 4))
            self.entry_reg_name.pack(before=self.lbl_email, fill="x", pady=(0, 10))

            # แสดงช่อง Confirm Password
            self.lbl_reg_confirm.pack(before=self.chk_show_pwd, anchor="w", pady=(0, 4))
            self.entry_reg_confirm.pack(before=self.chk_show_pwd, fill="x", pady=(0, 10))

            # แสดง Bonus frame และซ่อน Remember Me
            self.bonus_frame.pack(before=self.lbl_login_status, fill="x", pady=(0, 10))
            self.chk_remember.pack_forget()

            self.btn_auth_submit.configure(text="✨ ยืนยันการสมัครสมาชิก (รับฟรี 48 ชม.)")
        else:
            self.auth_mode = "login"
            # ซ่อนช่อง Register
            self.lbl_reg_name.pack_forget()
            self.entry_reg_name.pack_forget()
            self.lbl_reg_confirm.pack_forget()
            self.entry_reg_confirm.pack_forget()
            self.bonus_frame.pack_forget()

            # แสดง Remember Me
            self.chk_remember.pack(before=self.lbl_login_status, anchor="w", pady=(0, 12))

            self.btn_auth_submit.configure(text="🚀 เข้าสู่ระบบ (Sign In)")

    def _open_forgot_password(self):
        email = self.entry_email.get().strip()
        url = "https://goldbot24.vercel.app/forgot-password"
        if email:
            url += "?email=" + urllib.parse.quote(email)
        webbrowser.open(url)

    def _toggle_show_password(self):
        """สลับการแสดงรหัสผ่านแบบตัวอักษรจริง / จุด"""
        mask = "" if self.show_pwd_var.get() else "•"
        self.entry_pwd.configure(show=mask)
        self.entry_reg_confirm.configure(show=mask)

    @staticmethod
    def _password_hint(pwd: str) -> str:
        """คำแนะนำเพิ่มเติมเมื่อรหัสผ่านมีอักษรภาษาไทย/ช่องว่าง (มักเกิดจากลืมสลับแป้นพิมพ์)"""
        if any(ord(ch) > 127 for ch in pwd):
            return "\n(รหัสผ่านมีอักษรภาษาไทย — แป้นพิมพ์อาจอยู่ในโหมดภาษาไทย กด ~ หรือ Alt+Shift เพื่อสลับ)"
        if pwd != pwd.strip():
            return "\n(รหัสผ่านมีช่องว่างที่ต้นหรือท้าย)"
        return ""

    def _on_auth_submit(self):
        """ดำเนินการเมื่อกดปุ่ม Submit ตามโหมดที่เลือก"""
        if self.auth_mode == "register":
            self._do_register()
        else:
            self._do_login()

    def _do_login(self):
        """ดำเนินการเข้าสู่ระบบจริง"""
        email = self.entry_email.get().strip()
        pwd = self.entry_pwd.get()
        remember = self.remember_var.get()

        if not email or not pwd:
            self.lbl_login_status.configure(text="กรุณากรอกอีเมลและรหัสผ่านให้ครบถ้วน", text_color=COLOR_DANGER_RED)
            return

        self.lbl_login_status.configure(text="กำลังตรวจสอบข้อมูลบัญชี...", text_color=COLOR_GOLD_PRIMARY)
        self.update_idletasks()

        success, msg = license_mgr.login(email, pwd, remember_me=remember)
        if success:
            if remember:
                secure_store.save_login(email, pwd)
            else:
                secure_store.clear_login()
            sound_manager.play_tp_hit()
            self.lbl_login_status.configure(text="เข้าสู่ระบบสำเร็จ!", text_color=COLOR_SUCCESS_GREEN)
            self.after(350, self.show_dashboard_view)
        else:
            sound_manager.play_sl_hit()
            self.lbl_login_status.configure(text=f"เข้าสู่ระบบไม่สำเร็จ: {msg}{self._password_hint(pwd)}", text_color=COLOR_DANGER_RED)

    def _do_register(self):
        """ดำเนินการสมัครสมาชิกใหม่จริง (รับฟรี 48 ชม.)"""
        display_name = self.entry_reg_name.get().strip()
        email = self.entry_email.get().strip()
        pwd = self.entry_pwd.get()
        confirm_pwd = self.entry_reg_confirm.get()

        if not email or not pwd:
            self.lbl_login_status.configure(text="กรุณากรอกอีเมลและรหัสผ่านให้ครบถ้วน", text_color=COLOR_DANGER_RED)
            return

        if len(pwd) < 6:
            self.lbl_login_status.configure(text="รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร", text_color=COLOR_DANGER_RED)
            return

        if pwd != confirm_pwd:
            self.lbl_login_status.configure(text="รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน", text_color=COLOR_DANGER_RED)
            return

        self.lbl_login_status.configure(text="กำลังส่งรหัสยืนยันไปที่อีเมล...", text_color=COLOR_GOLD_PRIMARY)
        self.update_idletasks()

        # ขั้นที่ 1: ขอรหัสยืนยัน 6 หลักทางอีเมล (กันการสมัครด้วยอีเมลที่ไม่ใช่ของตัวเอง)
        sent, msg = license_mgr.request_register_code(email, pwd, display_name=display_name)
        if not sent:
            sound_manager.play_sl_hit()
            self.lbl_login_status.configure(text=f"การสมัครสมาชิกล้มเหลว: {msg}", text_color=COLOR_DANGER_RED)
            return
        self.lbl_login_status.configure(text=msg, text_color=COLOR_GOLD_PRIMARY)

        # ขั้นที่ 2: กรอกรหัสจากอีเมล (ผิดได้หลายครั้งตามที่เซิร์ฟเวอร์อนุญาต)
        success = False
        prompt = f"กรอกรหัสยืนยัน 6 หลักที่ส่งไปที่\n{email}\n(ตรวจกล่องจดหมายขยะด้วย)"
        while True:
            dialog = ctk.CTkInputDialog(title="ยืนยันอีเมล", text=prompt)
            code = "".join(ch for ch in (dialog.get_input() or "") if ch.isdigit())
            if not code:
                self.lbl_login_status.configure(text="ยกเลิกการยืนยันอีเมล — กดสมัครอีกครั้งเพื่อขอรหัสใหม่", text_color=COLOR_DANGER_RED)
                return
            self.lbl_login_status.configure(text="กำลังตรวจสอบรหัสและสร้างบัญชี...", text_color=COLOR_GOLD_PRIMARY)
            self.update_idletasks()
            success, msg = license_mgr.register(email, pwd, display_name=display_name, code=code)
            if success or "เหลืออีก" not in msg:
                break
            prompt = f"{msg}\nกรอกรหัสยืนยัน 6 หลักที่ส่งไปที่\n{email}"

        if success:
            if self.remember_var.get():
                secure_store.save_login(email, pwd)
            sound_manager.play_tp_hit()
            self.lbl_login_status.configure(text="🎉 สมัครสมาชิกสำเร็จ! ได้รับโควตาฟรี 48 ชม.", text_color=COLOR_SUCCESS_GREEN)
            self.after(600, self.show_dashboard_view)
        else:
            sound_manager.play_sl_hit()
            self.lbl_login_status.configure(text=f"การสมัครสมาชิกล้มเหลว: {msg}", text_color=COLOR_DANGER_RED)

    # =========================================================================
    # 2. หน้าจอควบคุมหลัก (DASHBOARD VIEW)
    # =========================================================================
    def show_dashboard_view(self):
        """แสดงแดชบอร์ดควบคุมการเทรดและมอนิเตอร์สัญญาณ"""
        self.is_logged_in = True
        license_mgr.track_event("app_open")  # สถิติการเข้าใช้โปรแกรม (ซ้ำใน 5 นาทีนับครั้งเดียว)
        if self.login_view:
            self.login_view.destroy()
            self.login_view = None

        self.dashboard_view = ctk.CTkFrame(self.container, fg_color="transparent")
        self.dashboard_view.pack(fill="both", expand=True)

        # สถานะข้อมูลที่โหลดจากเธรดเบื้องหลัง
        self._history_rows = []
        self._history_page = 0
        self._history_dirty = False
        self._history_loading = False
        self._calendar_events = []
        self._calendar_dirty = False
        self._calendar_loading = False
        self._ui_tick = 0

        plan_config.start()  # แผนเทรดที่แอดมินเปิด/ปิด
        self._build_top_header()
        self._build_metric_cards()

        body = ctk.CTkFrame(self.dashboard_view, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        body.grid_columnconfigure(0, weight=7, uniform="body")
        body.grid_columnconfigure(1, weight=3, uniform="body")
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._build_main_tabs(left)
        self._build_control_panel(right)
        self._build_plans_card(right)

        self._refresh_history_async()
        self._refresh_calendar_async()

        # ตรวจสอบอัปเดตเวอร์ชันซอฟต์แวร์อัตโนมัติแบบเงียบๆ หลังเปิดหน้าจอ 3 วินาที
        self._update_result = None
        self._last_update_check = 0.0
        self.after(800, self._start_update_check)
        # เปิดปุ่ม Algo Trading ใน MT5 ให้อัตโนมัติถ้ายังปิดอยู่ (ผู้ใช้สั่ง 8 ต.ค. 2026)
        self.after(2500, self._auto_algo_trading)

        # เริ่มนับถอยหลัง 20 วินาทีเมื่อเปิดโปรแกรมครั้งแรก เพื่อเริ่มการทำงานบอทอัตโนมัติ
        if not getattr(self, "_autostart_done", False):
            self._autostart_done = True
            self.after(500, lambda: self._start_autostart_countdown(20))

    # ---------------------------------------------------------------------
    # ส่วนประกอบ UI ใช้ซ้ำ
    # ---------------------------------------------------------------------
    @staticmethod
    def _font(size=12, weight="normal", family=app_fonts.UI):
        return ctk.CTkFont(family=family, size=size, weight=weight)

    def _card(self, parent, **pack_kwargs):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        card.pack(**pack_kwargs)
        return card

    def _card_title(self, parent, text, right_widget_factory=None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(14, 8))
        ctk.CTkLabel(row, text=text, font=self._font(13, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        if right_widget_factory:
            right_widget_factory(row).pack(side="right")
        return row

    def _refresh_button(self, parent, command):
        """ปุ่มรีเฟรชมาตรฐาน: ↻ + ข้อความ สีฟ้า มีขอบ"""
        return ctk.CTkButton(parent, text="↻  รีเฟรช", font=self._font(11, "bold"), width=78, height=28, corner_radius=8,
                             fg_color="#132036", hover_color="#1A2C4A", border_width=1, border_color="#2D4A75",
                             text_color=COLOR_CYAN_ACCENT, command=command)

    def _small_button(self, parent, text, command, width=90, accent=False):
        return ctk.CTkButton(
            parent,
            text=text,
            font=self._font(11, "bold"),
            fg_color=COLOR_GOLD_WARM if accent else "#1A1E27",
            hover_color=COLOR_GOLD_DARK if accent else "#262B36",
            text_color="#1A1406" if accent else COLOR_TEXT_PRIMARY,
            width=width,
            height=28,
            corner_radius=7,
            command=command,
        )

    # ---------------------------------------------------------------------
    # Header + การ์ดสรุป
    # ---------------------------------------------------------------------
    STORE_URL = "https://goldbot24.vercel.app/store"
    DOWNLOAD_URL = "https://goldbot24.vercel.app/download"
    WEB_URL = "https://goldbot24.vercel.app"
    LOW_HOURS_MINUTES = 5 * 60
    LOW_HOURS_ALERTS = (5 * 60, 60)   # เตือนด้วยหน้าต่าง + เสียงเมื่อเหลือ 5 ชม. และ 1 ชม. (ครั้งละครั้ง)

    def _build_top_header(self):
        """แถบบน: แบรนด์ + สถานะเวอร์ชัน | กระเป๋าเวลา (เติมคีย์/ซื้อชั่วโมง) | เมนูผู้ใช้"""
        header = ctk.CTkFrame(self.dashboard_view, fg_color=COLOR_CARD_BG, height=60, corner_radius=0)
        header.pack(fill="x", side="top", pady=(0, 10))
        h_inner = ctk.CTkFrame(header, fg_color="transparent")
        h_inner.pack(fill="both", expand=True, padx=20, pady=8)

        # --- ซ้าย: แบรนด์ + เวอร์ชัน/สถานะอัปเดต
        brand = ctk.CTkFrame(h_inner, fg_color="transparent")
        brand.pack(side="left")
        ctk.CTkLabel(brand, text="👑", font=ctk.CTkFont(size=24)).pack(side="left", padx=(0, 10))
        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left")
        ctk.CTkLabel(brand_text, text="AI Gold Commander Pro", font=self._font(17, "bold"), text_color=COLOR_GOLD_PRIMARY, height=24).pack(anchor="w")
        ver_row = ctk.CTkFrame(brand_text, fg_color="transparent")
        ver_row.pack(anchor="w")
        ctk.CTkLabel(ver_row, text=f"v{APP_VERSION} · XAUUSD Gold", font=self._font(11), text_color=COLOR_TEXT_MUTED, height=18).pack(side="left")
        self.btn_update_status = ctk.CTkButton(
            ver_row, text="กำลังตรวจสอบเวอร์ชัน…", font=self._font(10, "bold"), height=18, width=10,
            corner_radius=9, fg_color="#1F2430", hover_color="#262B36", text_color=COLOR_TEXT_MUTED,
            command=self._on_update_chip_clicked,
        )
        self.btn_update_status.pack(side="left", padx=(8, 0))
        self._update_info = None

        # --- ขวา: เมนูผู้ใช้
        user_name = license_mgr.session_data.get("username") or "User"
        # รูปย่อ + ชื่อ + ▾ รวมเป็นปุ่มเดียว (ทั้งก้อนคลิกเปิดเมนูได้)
        self.btn_user_menu = ctk.CTkFrame(h_inner, fg_color="transparent", corner_radius=21, height=42)
        self.btn_user_menu.pack(side="right")
        # ป้ายสีทองแสดงชื่อเต็ม (คลิกเปิดเมนู) — ไม่มีป้ายชื่อแยกอีกอัน
        avatar = ctk.CTkLabel(
            self.btn_user_menu, text=f"  {user_name}  ▾  ", font=self._font(13, "bold"), height=34,
            corner_radius=17, fg_color=COLOR_GOLD_WARM, text_color="#1A1406",
        )
        avatar.pack(side="left", padx=4, pady=4)
        for w in (self.btn_user_menu, avatar):
            w.bind("<Button-1>", lambda e: self._open_user_menu())
            w.configure(cursor="hand2")
            w.bind("<Enter>", lambda e: avatar.configure(fg_color=COLOR_GOLD_PRIMARY))
            w.bind("<Leave>", lambda e: avatar.configure(fg_color=COLOR_GOLD_WARM))

        # --- ขวา: กระเป๋าเวลา (เวลาคงเหลือ + เติมคีย์ + ซื้อชั่วโมง)
        self.time_pill_frame = ctk.CTkFrame(h_inner, fg_color=COLOR_GOLD_BG, corner_radius=12, border_width=1, border_color="#5A4519")
        self.time_pill_frame.pack(side="right", padx=(0, 16))
        wallet = ctk.CTkFrame(self.time_pill_frame, fg_color="transparent")
        wallet.pack(padx=(14, 6), pady=5)

        hours_box = ctk.CTkFrame(wallet, fg_color="transparent")
        hours_box.pack(side="left", padx=(0, 12))
        self.lbl_header_hours = ctk.CTkLabel(
            hours_box, text=f"⏳ {license_mgr.get_remaining_time_display()} ชม.",
            font=self._font(16, "bold"), text_color=COLOR_GOLD_PRIMARY, height=22,
        )
        self.lbl_header_hours.pack(anchor="w")
        self.lbl_metering_status = ctk.CTkLabel(hours_box, text="⏸ หยุดนับเวลา", font=self._font(10), text_color=COLOR_TEXT_MUTED, height=14)
        self.lbl_metering_status.pack(anchor="w")

        # รางวัลออนไลน์: สะสมครบ 100 ชม. → ส่วนลด 10% ซื้อชั่วโมงครั้งถัดไป (ใช้ได้ 3 วัน · เริ่มรอบใหม่ทันที) คลิกเปิดหน้าร้าน
        self.reward_box = ctk.CTkFrame(wallet, fg_color="transparent", cursor="hand2")
        self.lbl_reward = ctk.CTkLabel(self.reward_box, text="", font=self._font(11, "bold"), text_color=COLOR_GOLD_PRIMARY, height=16)
        self.lbl_reward.pack(anchor="w")
        self.cv_reward = tk.Canvas(self.reward_box, width=118, height=6, bg=COLOR_GOLD_BG, highlightthickness=0, bd=0)
        self.cv_reward.pack(anchor="w", pady=(4, 0))
        for w in (self.reward_box, self.lbl_reward, self.cv_reward):
            w.bind("<Button-1>", lambda e: webbrowser.open(self.STORE_URL))
        HoverTip(self.reward_box, self._reward_tip)
        self._reward_shown = None

        # ปุ่ม "เติมคีย์" ซ่อนไว้ (ผู้ใช้ซื้อชั่วโมงผ่านเว็บ — ระบบเติมเข้าบัญชีอัตโนมัติ)
        ctk.CTkButton(
            wallet, text="🛒 ซื้อชั่วโมง", font=self._font(12, "bold"), fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK,
            text_color="#1A1406", height=32, width=104, corner_radius=8,
            command=lambda: webbrowser.open(self.STORE_URL),
        ).pack(side="left")

        # --- ขวา: ข่าว USD ผลกระทบสูงถัดไป (ย้ายจากคอลัมน์ขวามาแถบบน 8 ต.ค. 2026)
        self._build_header_news(h_inner)

    def _open_user_menu(self):
        """เมนูผู้ใช้: เปิดเว็บ / สถิติ / ตรวจอัปเดต / ออกจากระบบ"""
        email = license_mgr.session_data.get("email") or ""
        menu = tk.Menu(
            self, tearoff=0, bg="#1A1E27", fg=COLOR_TEXT_PRIMARY, activebackground="#2A303C",
            activeforeground=COLOR_GOLD_PRIMARY, disabledforeground=COLOR_TEXT_MUTED, bd=0, relief="flat",
            font=(app_fonts.UI, 11),
        )
        if email:
            menu.add_command(label=f"  {email}", state="disabled")
            menu.add_separator()
        menu.add_command(label="  🌐  เปิดเว็บ GoldBot24 (พอร์ตสด)", command=lambda: webbrowser.open(self.WEB_URL))
        menu.add_command(label="  🛒  ซื้อชั่วโมงเพิ่ม", command=lambda: webbrowser.open(self.STORE_URL))
        menu.add_command(label="  📊  สถิติรายแผนแบบละเอียด", command=self._open_user_stats_modal)
        menu.add_command(label="  💬  ติดต่อแอดมิน (LINE)", command=lambda: ContactDialog(self))
        menu.add_command(label="  ตรวจสอบเวอร์ชันใหม่", command=lambda: self._start_update_check(manual=True))
        menu.add_separator()
        menu.add_command(label="  ⎋  ออกจากระบบ", foreground=COLOR_DANGER_RED, command=self._do_logout)
        x = self.btn_user_menu.winfo_rootx()
        y = self.btn_user_menu.winfo_rooty() + self.btn_user_menu.winfo_height() + 4
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    # ---- ตรวจสอบเวอร์ชันอัตโนมัติ (เธรดเบื้องหลัง ไม่ให้ UI ค้าง) ----
    UPDATE_CHECK_INTERVAL_SEC = 6 * 3600

    def _start_update_check(self, manual=False):
        if getattr(self, "_update_checking", False):
            return
        self._update_checking = True
        self._update_manual = manual
        if hasattr(self, "btn_update_status"):
            self.btn_update_status.configure(text="กำลังตรวจสอบเวอร์ชัน…", fg_color="#1F2430", text_color=COLOR_TEXT_MUTED)

        def worker():
            try:
                self._update_result = ("ok", license_mgr.check_app_version(APP_VERSION))
            except Exception as e:
                self._update_result = ("error", str(e))
            self._update_checking = False

        threading.Thread(target=worker, daemon=True).start()

    def _apply_update_result(self):
        """เรียกจาก UI loop เมื่อเธรดตรวจเวอร์ชันทำงานเสร็จ"""
        status, info = self._update_result
        self._update_result = None
        self._last_update_check = time.time()
        manual = getattr(self, "_update_manual", False)
        if status != "ok":
            self._update_info = None
            self.btn_update_status.configure(text="⚠ ตรวจเวอร์ชันไม่ได้ · ลองใหม่", fg_color="#1F2430", text_color=COLOR_TEXT_MUTED)
            if manual:
                messagebox.showerror("ตรวจสอบเวอร์ชัน", f"ไม่สามารถตรวจสอบเวอร์ชันได้\n{info}")
            return

        self._update_info = info
        if info.get("has_update"):
            latest = info.get("latest_version")
            self.btn_update_status.configure(text=f"▲ มีเวอร์ชันใหม่ v{latest} · ดาวน์โหลด", fg_color=COLOR_GOLD_WARM, text_color="#1A1406")
            if manual or info.get("mandatory"):
                self._prompt_update(info)
        else:
            self.btn_update_status.configure(text="✓ เวอร์ชันล่าสุด", fg_color="#12301F", text_color=COLOR_SUCCESS_GREEN)
            if manual:
                messagebox.showinfo("ตรวจสอบเวอร์ชัน", f"ท่านใช้เวอร์ชันล่าสุดแล้ว (v{APP_VERSION})")

    def _on_update_chip_clicked(self):
        info = self._update_info
        if info and info.get("has_update"):
            self._prompt_update(info)
        else:
            self._start_update_check(manual=True)

    def _prompt_update(self, info):
        dlg = getattr(self, "_update_dialog", None)
        try:
            if dlg is not None and dlg.winfo_exists():
                dlg.lift()
                return
        except Exception:
            pass
        self._update_dialog = UpdateDialog(self, info, info.get("download_url") or self.DOWNLOAD_URL)

    def _build_metric_cards(self):
        """การ์ดสรุปสถานะพอร์ตและราคาทองคำ 4 กล่องแนวนอน"""
        grid_frame = ctk.CTkFrame(self.dashboard_view, fg_color="transparent")
        grid_frame.pack(fill="x", padx=14, pady=(0, 10))
        grid_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="metric_cards")

        self.card_mt5 = self._create_stat_card(grid_frame, 0, "🖥", "บัญชี MT5", "รอเชื่อมต่อ...", "Server: กำลังตรวจสอบ", COLOR_CYAN_ACCENT)
        self.card_balance = self._create_stat_card(grid_frame, 1, "💰", "ยอดเงินในพอร์ต", "0.00", "Equity 0.00 · Float 0.00", COLOR_SUCCESS_GREEN)
        self._make_clickable(self.card_balance, lambda: PnlHistoryDialog(self), hint="ดูกราฟ ›")
        self.card_gold = self._create_stat_card(grid_frame, 2, "🏆", "ราคาทองคำ XAUUSD", "0.00", "Spread 0 pts", COLOR_GOLD_PRIMARY)
        self._make_clickable(self.card_gold, lambda: GoldCandleDialog(self), hint="ดูกราฟ ›")
        # สภาวะตลาด: 2 แถว H1 / H4 + ป้ายทิศที่อนุญาตให้เทรด (Strict Pro-Trend)
        self.card_trend = self._create_dual_card(grid_frame, 3, "📊", "สภาวะตลาด")
        self.card_trend["rows"] = {tf: self._create_trend_row(self.card_trend["body"], tf) for tf in ("H1", "H4")}
        self._make_clickable(self.card_trend, lambda: MarketExplainDialog(self))
        self.after(1500, self._ma_order_tick)

        # แนวรับ–แนวต้าน: 2 แถว H1 / H4 พร้อมแถบตำแหน่งราคาปัจจุบันในกรอบ
        self.card_sr = self._create_dual_card(grid_frame, 4, "🧱", "แนวรับ – แนวต้าน")
        sr_body = self.card_sr["body"]
        sr_body.grid_columnconfigure((0, 1), weight=1, uniform="sr_cols")
        self.card_sr["rows"] = {tf: self._create_sr_row(sr_body, tf, col) for col, tf in enumerate(("H1", "H4"))}
        self._make_clickable(self.card_sr, lambda: GoldCandleDialog(self, default_tf="H1", default_bars=500, default_plan="P3"), hint="ดูกราฟ H1 ›")

    # ---------------------------------------------------------------------
    # การ์ด 2 แถว (สภาวะตลาด / แนวรับ–แนวต้าน)
    # ---------------------------------------------------------------------
    def _create_dual_card(self, parent, col, icon, title):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        card.grid(row=0, column=col, padx=6, sticky="nsew")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=7)

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(top_row, text=icon, font=ctk.CTkFont(size=15)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(top_row, text=title, font=self._font(12), text_color=COLOR_TEXT_MUTED).pack(side="left")
        badge = ctk.CTkLabel(top_row, text="", font=self._font(10, "bold"), text_color=COLOR_TEXT_MUTED,
                             fg_color="transparent", corner_radius=8, height=18)
        badge.pack(side="right")
        hint_lbl = ctk.CTkLabel(top_row, text="", font=self._font(10, "bold"), text_color=COLOR_GOLD_PRIMARY,
                                fg_color="transparent", corner_radius=6, height=18)
        hint_lbl.pack(side="right", padx=(0, 4))

        body = ctk.CTkFrame(inner, fg_color="transparent")
        body.pack(fill="x", pady=(3, 0))
        return {"card": card, "badge": badge, "hint_lbl": hint_lbl, "body": body, "top_row": top_row}

    @staticmethod
    def _set_badge(badge, text, fg="#1F2430", color=COLOR_TEXT_MUTED):
        if text:
            badge.configure(text=f"  {text}  ", fg_color=fg, text_color=color)
        else:
            badge.configure(text="", fg_color="transparent")

    def _tf_tag(self, parent, tf):
        tag = ctk.CTkLabel(parent, text=tf, width=30, height=18, corner_radius=6, fg_color="#1F2430",
                           font=self._font(10, "bold"), text_color=COLOR_TEXT_MUTED)
        tag.pack(side="left", padx=(0, 8))
        return tag

    def _create_trend_row(self, parent, tf):
        row = ctk.CTkFrame(parent, fg_color="transparent", height=24)
        row.pack(fill="x", pady=1)
        self._tf_tag(row, tf)
        val = ctk.CTkLabel(row, text="—", font=self._font(13, "bold"), text_color=COLOR_TEXT_MUTED, height=22)
        val.pack(side="left")
        pct = ctk.CTkLabel(row, text="", font=self._font(11, "bold", app_fonts.MONO), text_color=COLOR_TEXT_MUTED, height=22)
        pct.pack(side="right")
        # ลำดับเส้น MA50 / MA100 / MA150 (แท่งปิด) เช่น 50<100<150 = ขาลง — อัปเดตทุก 30 วินาที (_ma_order_tick)
        lt = ctk.CTkLabel(row, text="", font=self._font(10, "bold", app_fonts.MONO), text_color=COLOR_TEXT_MUTED, height=22)
        lt.pack(side="right", padx=(0, 6))
        return {"val": val, "pct": pct, "lt": lt}

    @staticmethod
    def _format_sr_stars(stars: float) -> str:
        """แปลงคะแนนความแข็งแกร่งเป็นตัวเลขแสดงผล 0.00 - 10.00 (ทศนิยม 2 ตำแหน่ง) เช่น 7.0 -> '★ 7.00'"""
        if stars is None or stars < 0:
            return ""
        try:
            val = float(stars)
            val = max(0.0, min(10.0, val))
            return f"★ {val:.2f}"
        except Exception:
            return ""

    def _create_sr_row(self, parent, tf, col=0):
        """คอลัมน์ต่อ Timeframe (H1 ซ้าย · H4 ขวา): ▲ ต้าน / บาร์ระยะห่าง / ▼ รับ
        บาร์: ช่วงเขียว = ระยะจากแนวรับถึงราคา · ช่วงแดง = ระยะจากราคาถึงแนวต้าน · จุดทอง = ราคาปัจจุบัน"""
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=0, column=col, sticky="nsew", padx=(0, 6) if col == 0 else (6, 0))
        head = ctk.CTkFrame(box, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkLabel(head, text=tf, width=28, height=16, corner_radius=5, fg_color="#1F2430",
                     font=self._font(9, "bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))
        res = ctk.CTkLabel(head, text="▲ —", font=self._font(11, "bold", app_fonts.MONO), text_color=COLOR_DANGER_RED, height=16)
        res.pack(side="left")
        res_star = ctk.CTkLabel(head, text="", font=self._font(9, "bold"), text_color=COLOR_GOLD_PRIMARY, height=16)
        res_star.pack(side="right")

        bar = tk.Canvas(box, height=10, bg=COLOR_CARD_BG, highlightthickness=0, bd=0)
        bar.pack(fill="x", pady=(3, 3))

        sup_frame = ctk.CTkFrame(box, fg_color="transparent")
        sup_frame.pack(fill="x")
        sup = ctk.CTkLabel(sup_frame, text="▼ —", font=self._font(11, "bold", app_fonts.MONO), text_color=COLOR_SUCCESS_GREEN, height=16, anchor="w")
        sup.pack(side="left", padx=(34, 0))
        sup_star = ctk.CTkLabel(sup_frame, text="", font=self._font(9, "bold"), text_color=COLOR_GOLD_PRIMARY, height=16)
        sup_star.pack(side="right")

        state = {"sup": 0.0, "res": 0.0, "price": 0.0}
        bar.bind("<Configure>", lambda e, b=bar, st=state: self._draw_sr_bar(b, st))
        return {"sup": sup, "res": res, "bar": bar, "sup_star": sup_star, "res_star": res_star, "state": state}

    @staticmethod
    def _sr_position(sup, res, price):
        """ตำแหน่งราคาในกรอบ 0..1 (None ถ้าข้อมูลไม่ครบ) — อาจ < 0 หรือ > 1 เมื่อหลุดกรอบ"""
        if sup <= 0 or res <= sup or price <= 0:
            return None
        return (price - sup) / (res - sup)

    def _draw_sr_bar(self, bar, st):
        bar.delete("all")
        w = max(bar.winfo_width(), 20)
        y, x0, x1 = 5, 4, w - 4
        pos = self._sr_position(st["sup"], st["res"], st["price"])
        if pos is None:
            bar.create_line(x0, y, x1, y, fill="#2A303C", width=6, capstyle="round")
            return
        clamped = min(max(pos, 0.0), 1.0)
        x = x0 + clamped * (x1 - x0)
        bar.create_line(x0, y, x1, y, fill=COLOR_DANGER_RED, width=6, capstyle="round")   # ราคา → แนวต้าน
        if x > x0:
            bar.create_line(x0, y, x, y, fill=COLOR_SUCCESS_GREEN, width=6, capstyle="round")  # แนวรับ → ราคา
        dot = COLOR_DANGER_RED if pos > 1 else COLOR_SUCCESS_GREEN if pos < 0 else COLOR_GOLD_PRIMARY
        bar.create_oval(x - 5, y - 5, x + 5, y + 5, fill=dot, outline=COLOR_CARD_BG, width=2)

    def _create_stat_card(self, parent, col, icon, title, val_text, sub_text, accent_color):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        card.grid(row=0, column=col, padx=6, sticky="nsew")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=7)

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")

        # ตรวจสอบฟอนต์สำหรับไอคอนการ์ด (ใช้ Segoe MDL2 Assets เพื่อให้ไอคอนเปลี่ยนสีเขียว/แดง/ขาวตามสถานะตลาดได้คมชัด)
        try:
            has_mdl2 = "Segoe MDL2 Assets" in self.tk.call("font", "families")
        except Exception:
            has_mdl2 = False
        if icon == "🖥" and has_mdl2:
            icon_char = "\uE7F4"
            icon_font = ctk.CTkFont(family="Segoe MDL2 Assets", size=15)
        else:
            icon_char = icon
            icon_font = ctk.CTkFont(size=15)

        icon_lbl = ctk.CTkLabel(top_row, text=icon_char, font=icon_font, text_color=COLOR_TEXT_PRIMARY)
        icon_lbl.pack(side="left", padx=(0, 6))
        ctk.CTkLabel(top_row, text=title, font=self._font(12), text_color=COLOR_TEXT_MUTED).pack(side="left")
        badge = ctk.CTkLabel(top_row, text="", font=self._font(10, "bold"), text_color=COLOR_TEXT_MUTED,
                             fg_color="transparent", corner_radius=8, height=18)
        badge.pack(side="right")
        hint_lbl = ctk.CTkLabel(top_row, text="", font=self._font(10, "bold"), text_color=COLOR_GOLD_PRIMARY,
                                fg_color="transparent", corner_radius=6, height=18)
        hint_lbl.pack(side="right", padx=(0, 4))

        val_label = ctk.CTkLabel(inner, text=val_text, font=self._font(19, "bold"), text_color=accent_color, height=26)
        val_label.pack(anchor="w", pady=(2, 0))
        sub_label = ctk.CTkLabel(inner, text=sub_text, font=self._font(11), text_color=COLOR_TEXT_MUTED, height=18)
        sub_label.pack(anchor="w")
        return {"card": card, "val_lbl": val_label, "sub_lbl": sub_label, "badge": badge, "hint_lbl": hint_lbl, "icon_lbl": icon_lbl, "top_row": top_row}

    def _make_clickable(self, card_info, command, hint=""):
        """ทำให้ทั้งการ์ดกดได้ (เคอร์เซอร์มือ + ขอบสีทองเมื่อชี้ + ป้ายบอกทาง)"""
        card = card_info["card"]
        hint_lbl = card_info.get("hint_lbl")
        state = {"win": None}

        if hint and hint_lbl:
            hint_lbl.configure(text=f" {hint} ", text_color=COLOR_GOLD_PRIMARY, fg_color="#201C12")

        def open_once(_e=None):
            # คลิกโดนหลายวิดเจ็ตซ้อนกันจะยิงหลายครั้ง → เปิดหน้าต่างเดียว ถ้าเปิดอยู่แล้วให้ดึงขึ้นมาหน้าสุด
            w = state["win"]
            if w is not None:
                try:
                    if w.winfo_exists():
                        w.deiconify(); w.lift(); w.focus_force()
                        return
                except Exception:
                    pass
            state["win"] = command()

        def on_enter(_e=None):
            card.configure(border_color=COLOR_GOLD_PRIMARY)
            if hint_lbl and hint:
                hint_lbl.configure(text_color=COLOR_GOLD_WARM, fg_color="#2E2614")

        def on_leave(_e=None):
            card.configure(border_color=COLOR_CARD_BORDER)
            if hint_lbl and hint:
                hint_lbl.configure(text_color=COLOR_GOLD_PRIMARY, fg_color="#201C12")

        def bind_all(w):
            w.bind("<Button-1>", open_once, add="+")
            w.bind("<Enter>", on_enter, add="+")
            w.bind("<Leave>", on_leave, add="+")
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass
            for ch in w.winfo_children():
                bind_all(ch)

        bind_all(card)

    # ---------------------------------------------------------------------
    # คอลัมน์ขวา: ควบคุมบอท / ข่าวถัดไป / แผนเทรด
    # ---------------------------------------------------------------------
    @staticmethod
    def _load_lot() -> float:
        try:
            with open(data_path("bot_settings.json"), "r", encoding="utf-8") as f:
                return max(0.01, float(json.load(f).get("lot", 0.01)))
        except Exception:
            return 0.01

    def _save_tp_usd(self):
        """บันทึกเป้าปิดไม้ตามกำไร $ (ทุกไม้ของบอท ทุกแผน)"""
        try:
            amount = round(float(str(self.tp_usd_var.get()).replace("$", "").replace(",", "").strip()), 2)
            if not (0.1 <= amount <= 100000):
                raise ValueError
        except ValueError:
            self.tp_usd_var.set(f"{float(self._load_setting('tp_usd', 5.0)):.2f}")
            self.lbl_tp_hint.configure(text="0.10 ขึ้นไป", text_color=COLOR_DANGER_RED)
            return
        self.tp_usd_var.set(f"{amount:.2f}")
        enabled = bool(self.tp_usd_enabled_var.get())
        if amount == float(self._load_setting("tp_usd", -1)) and enabled == bool(self._load_setting("tp_usd_enabled", False)):
            return
        try:
            self._save_setting("tp_usd", amount)
            self._save_setting("tp_usd_enabled", enabled)
            self.lbl_tp_hint.configure(text="บันทึกแล้ว ✓" if enabled else "ปิดใช้งาน", text_color=COLOR_SUCCESS_GREEN if enabled else COLOR_TEXT_MUTED)
            self.after(2500, lambda: self.lbl_tp_hint.configure(text=""))
        except Exception:
            self.lbl_tp_hint.configure(text="บันทึกไม่สำเร็จ", text_color=COLOR_DANGER_RED)

    def _save_manual_tp_pts(self, value=None):
        """บันทึกเป้ากำไรเป็นจุดสำหรับไม้เข้าเอง (100-500 จุด หรือระบุอิสระ)"""
        val_str = str(value if value is not None else self.manual_tp_pts_var.get()).replace("จุด", "").replace(",", "").strip()
        try:
            pts = float(val_str)
            if not (10 <= pts <= 50000):
                raise ValueError
        except ValueError:
            pts = float(self._load_setting("manual_tp_pts", 100))
            self.manual_tp_pts_var.set(f"{int(pts) if pts.is_integer() else pts:g}")
            if hasattr(self, "lbl_manual_tp_hint"):
                self.lbl_manual_tp_hint.configure(text="10 จุดขึ้นไป", text_color=COLOR_DANGER_RED)
            return

        pts_clean = int(pts) if pts.is_integer() else pts
        self.manual_tp_pts_var.set(f"{pts_clean:g}")
        enabled = bool(self.manual_tp_pts_enabled_var.get())
        if pts == float(self._load_setting("manual_tp_pts", -1)) and enabled == bool(self._load_setting("manual_tp_pts_enabled", False)):
            return
        try:
            self._save_setting("manual_tp_pts", pts)
            self._save_setting("manual_tp_pts_enabled", enabled)
            if hasattr(self, "lbl_manual_tp_hint"):
                self.lbl_manual_tp_hint.configure(
                    text="บันทึกแล้ว ✓" if enabled else "ปิดใช้งาน",
                    text_color=COLOR_SUCCESS_GREEN if enabled else COLOR_TEXT_MUTED
                )
                self.after(2500, lambda: self.lbl_manual_tp_hint.configure(text=""))
        except Exception:
            if hasattr(self, "lbl_manual_tp_hint"):
                self.lbl_manual_tp_hint.configure(text="บันทึกไม่สำเร็จ", text_color=COLOR_DANGER_RED)

    def _save_lot(self, value):
        """ตรวจและบันทึกขนาดไม้ — บอทอ่านค่าใหม่ทันทีตอนเปิดออเดอร์ถัดไป"""
        try:
            lot = round(float(str(value).strip()), 2)
            if not (0.01 <= lot <= 100):
                raise ValueError
        except ValueError:
            self.lot_var.set(f"{self._load_lot():.2f}")
            self.lbl_lot_hint.configure(text="0.01 – 100 เท่านั้น", text_color=COLOR_DANGER_RED)
            return
        if abs(lot - self._load_lot()) < 1e-9:
            self.lot_var.set(f"{lot:.2f}")
            return
        try:
            self._save_setting("lot", lot)
            self.lot_var.set(f"{lot:.2f}")
            self.lbl_lot_hint.configure(text="บันทึกแล้ว ✓", text_color=COLOR_SUCCESS_GREEN)
            self.after(2500, lambda: self.lbl_lot_hint.configure(text=""))
        except Exception as e:
            self.lbl_lot_hint.configure(text=f"บันทึกไม่ได้: {e}", text_color=COLOR_DANGER_RED)

    def _build_control_panel(self, parent):
        card = self._card(parent, fill="x", pady=(0, 8))

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(10, 8))
        ctk.CTkLabel(head, text="🎮 ควบคุมบอท", font=self._font(13, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        self.lbl_bot_state = ctk.CTkLabel(
            head, text="  ● หยุดทำงาน  ", font=self._font(11, "bold"),
            text_color=COLOR_TEXT_MUTED, fg_color="#1F2430", corner_radius=10, height=22,
        )
        self.lbl_bot_state.pack(side="right")
        self.lbl_bot_state.bind("<Button-1>", self._cancel_autostart_manual)

        self.btn_master_toggle = ctk.CTkButton(
            card,
            text="▶  เริ่มการทำงานบอท",
            font=self._font(15, "bold"),
            fg_color=COLOR_SUCCESS_GREEN,
            hover_color="#10A374",
            text_color="#06281C",
            height=42,
            corner_radius=10,
            command=self._on_toggle_bot,
        )
        self.btn_master_toggle.pack(fill="x", padx=14)

        # แถวเดียว (ประหยัดความสูงให้พอดีจอ 1366×768): Lot [▾] | ☐ ปิดเมื่อกำไรถึง [x.xx]
        #   Lot บันทึกใน %APPDATA%\GoldBot24\bot_settings.json (ค่าเริ่มต้น 0.01) · เป้ากำไรค่าเริ่มต้นปิด
        opt_row = ctk.CTkFrame(card, fg_color="transparent")
        opt_row.pack(fill="x", padx=14, pady=(6, 0))
        lbl_lot = ctk.CTkLabel(opt_row, text="Lot", font=self._font(12, "bold"), text_color=COLOR_TEXT_MUTED)
        lbl_lot.pack(side="left", padx=(0, 6))
        self.lot_var = tk.StringVar(value=f"{self._load_lot():.2f}")
        self.cmb_lot = ctk.CTkComboBox(
            opt_row, width=78, height=28, variable=self.lot_var,
            values=["0.01", "0.02", "0.03", "0.05", "0.10", "0.20", "0.50", "1.00"],
            command=lambda v: self._save_lot(v), font=self._font(12, "bold"),
        )
        self.cmb_lot.pack(side="left")
        self.cmb_lot.bind("<Return>", lambda e: self._save_lot(self.lot_var.get()))
        self.cmb_lot.bind("<FocusOut>", lambda e: self._save_lot(self.lot_var.get()))
        self.lbl_lot_hint = _HintProxy(lbl_lot, "Lot")

        self.tp_usd_var = tk.StringVar(value=f"{float(self._load_setting('tp_usd', 5.0)):.2f}")
        ent = ctk.CTkEntry(opt_row, width=70, height=28, textvariable=self.tp_usd_var, font=self._font(12, "bold"), justify="right")
        ent.pack(side="right")
        self.tp_usd_enabled_var = tk.BooleanVar(value=bool(self._load_setting("tp_usd_enabled", False)))
        chk_tp = ctk.CTkCheckBox(
            opt_row, text="ปิดเมื่อกำไรถึง", variable=self.tp_usd_enabled_var, font=self._font(12, "bold"), text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK, checkbox_width=18, checkbox_height=18,
            command=self._save_tp_usd,
        )
        chk_tp.pack(side="right", padx=(0, 6))
        self.lbl_tp_hint = _HintProxy(chk_tp, "ปิดเมื่อกำไรถึง")
        ent.bind("<Return>", lambda e: self._save_tp_usd())
        ent.bind("<FocusOut>", lambda e: self._save_tp_usd())

        # แถวเป้ากำไรเป็นจุด: ☐ ปิดไม้เข้าเองกำไรถึง [ 100 ▾ ] จุด
        #   ค่าเริ่มต้น 100 จุด (ตัวเลือก 100, 150, 200, 250, 300, 350, 400, 450, 500 หรือพิมพ์ระบุอิสระ)
        #   *หากราคาผันผวนแรงผิดปกติ ระบบจะบังคับเปิดใช้เสมอและมีผลต่อทุกแผน
        opt_row_pts = ctk.CTkFrame(card, fg_color="transparent")
        opt_row_pts.pack(fill="x", padx=14, pady=(5, 0))

        self.manual_tp_pts_enabled_var = tk.BooleanVar(value=bool(self._load_setting("manual_tp_pts_enabled", False)))
        chk_manual_tp = ctk.CTkCheckBox(
            opt_row_pts, text="ปิดไม้เข้าเองกำไรถึง", variable=self.manual_tp_pts_enabled_var,
            font=self._font(12, "bold"), text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK, checkbox_width=18, checkbox_height=18,
            command=self._save_manual_tp_pts,
        )
        chk_manual_tp.pack(side="left")
        self.lbl_manual_tp_hint = _HintProxy(chk_manual_tp, "ปิดไม้เข้าเองกำไรถึง")

        lbl_pts_unit = ctk.CTkLabel(opt_row_pts, text="จุด", font=self._font(12, "bold"), text_color=COLOR_TEXT_MUTED)
        lbl_pts_unit.pack(side="right", padx=(4, 0))

        cur_pts = float(self._load_setting("manual_tp_pts", 100))
        cur_pts_str = f"{int(cur_pts) if cur_pts.is_integer() else cur_pts:g}"
        self.manual_tp_pts_var = tk.StringVar(value=cur_pts_str)
        self.cmb_manual_tp_pts = ctk.CTkComboBox(
            opt_row_pts, width=82, height=28, variable=self.manual_tp_pts_var,
            values=["100", "150", "200", "250", "300", "350", "400", "450", "500"],
            command=lambda v: self._save_manual_tp_pts(v), font=self._font(12, "bold"),
        )
        self.cmb_manual_tp_pts.pack(side="right")
        self.cmb_manual_tp_pts.bind("<Return>", lambda e: self._save_manual_tp_pts(self.manual_tp_pts_var.get()))
        self.cmb_manual_tp_pts.bind("<FocusOut>", lambda e: self._save_manual_tp_pts(self.manual_tp_pts_var.get()))

        HoverTip(chk_manual_tp, lambda: "ปิดไม้ที่เข้าเองทันทีเมื่อกำไรถึงจำนวนจุดที่ตั้ง (คำนวณจากราคาเข้าไม้)\n*ถ้าราคาผันผวนแรงผิดปกติ ระบบจะบังคับเปิดใช้เสมอและมีผลต่อทุกแผน")
        HoverTip(self.cmb_manual_tp_pts, lambda: "เลือกจำนวนจุดเป้าหมาย (100–500) หรือพิมพ์ระบุอิสระตามต้องการ")


        # สถิติย่อ 3 ช่อง: ออเดอร์เปิดอยู่ / กำไรลอยตัว / เวลาทำงาน
        stats = ctk.CTkFrame(card, fg_color="#101218", corner_radius=10)
        stats.pack(fill="x", padx=14, pady=(6, 0))
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="ctl_stats")
        self.ctl_stat_labels = {}
        for col, (key, title, init) in enumerate((("open", "ออเดอร์ / สูงสุด", "0 / 0"), ("float", "กำไรลอยตัว", "0.00"),
                                                  ("margin", "หลักประกันว่าง", "0.00"), ("uptime", "เวลาทำงาน", "--:--:--"))):
            box = ctk.CTkFrame(stats, fg_color="transparent")
            box.grid(row=0, column=col, sticky="nsew", pady=5)
            ttl = ctk.CTkLabel(box, text=title, font=self._font(10), height=16, text_color=COLOR_TEXT_MUTED)
            ttl.pack()
            val = ctk.CTkLabel(box, text=init, font=self._font(14, "bold"), text_color=COLOR_TEXT_PRIMARY, height=22)
            val.pack()
            self.ctl_stat_labels[key] = val
            if key == "open":  # กดจำนวนออเดอร์ → ไปแท็บออเดอร์ที่เปิดอยู่
                for w in (box, val, ttl):
                    w.configure(cursor="hand2")
                    w.bind("<Button-1>", lambda e: self.main_tabs.set(self.TAB_POSITIONS))
            if key == "margin":  # หลักประกันล็อก 400 ต่อไม้ (ตั้งเองไม่ได้) — ชี้ดูวิธีคิดจำนวนไม้
                HoverTip(box, lambda: "จำนวนไม้สูงสุด = หลักประกันว่าง ÷ 400 ต่อไม้ (ที่ Lot 0.01 · เศษปัดขึ้น)")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(8, 12))
        row.grid_columnconfigure(2, weight=1)
        # เข้าไม้ทันที (เปิดหน้าต่างยืนยัน SL/TP ก่อนส่งคำสั่งจริง)
        for col, (side, fg, hv, tx) in enumerate((("BUY", "#0F2A20", "#143826", COLOR_SUCCESS_GREEN), ("SELL", "#2A1215", "#38181C", COLOR_DANGER_RED))):
            ctk.CTkButton(row, text=f"{'▲' if side == 'BUY' else '▼'} {side}", font=self._font(12, "bold"), width=70, height=32,
                          corner_radius=8, fg_color=fg, hover_color=hv, border_width=1, border_color=tx, text_color=tx,
                          command=lambda s=side: self._open_quick_order(s)).grid(row=0, column=col, padx=(0, 6))
        self.btn_close_all = ctk.CTkButton(
            row,
            text="ไม่มีออเดอร์",
            font=self._font(12, "bold"),
            fg_color="#1A1E27",
            hover_color="#4A2A2F",
            text_color=COLOR_DANGER_RED,
            text_color_disabled="#5A6070",
            border_width=1,
            border_color="#2A303C",
            height=32,
            corner_radius=8,
            state="disabled",
            command=self._on_click_close_all,
        )
        self.btn_close_all.grid(row=0, column=2, sticky="ew", padx=(0, 6))
        # ปุ่มเสียงแบบข้อความ + สีสถานะ (เห็นชัดกว่าอีโมจีเล็ก ๆ)
        self.btn_sound_toggle = ctk.CTkButton(
            row, text="", font=self._font(11, "bold"), width=86, height=32, corner_radius=8, border_width=1,
            command=self._on_toggle_sound,
        )
        self._style_sound_button()
        self.btn_sound_toggle.grid(row=0, column=3)
        self._bot_started_at = None

    NEWS_PILL_BG = "#191D26"

    def _build_header_news(self, parent):
        """ข้อความวิ่งข่าว USD ผลกระทบสูงที่กำลังจะมาถึง เต็มพื้นที่ว่างของแถบบน (ผู้ใช้ขอ 8 ต.ค. 2026) · คลิกเปิดแท็บปฏิทินข่าว"""
        box = ctk.CTkFrame(parent, fg_color=self.NEWS_PILL_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER, height=34)
        box.pack(side="right", fill="x", expand=True, padx=(24, 12))
        box.pack_propagate(False)
        ctk.CTkLabel(box, text="  ข่าวสำคัญ USD  ", font=self._font(10, "bold"), text_color="#101218", fg_color=self.IMPACT_COLORS["High"],
                     corner_radius=6, height=20).pack(side="left", padx=(8, 6))
        self._mq = tk.Canvas(box, bg=self.NEWS_PILL_BG, highlightthickness=0, height=24, cursor="hand2")
        self._mq.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._mq_item = self._mq.create_text(0, 12, text="กำลังโหลดปฏิทินข่าว...", anchor="w", fill=COLOR_TEXT_PRIMARY,
                                             font=(app_fonts.UI, 11, "bold"))
        self._mq_x = None

        def open_calendar(_e=None):
            if hasattr(self, "main_tabs"):
                self.main_tabs.set(self.TAB_CALENDAR)
        for w in (box, self._mq):
            w.bind("<Button-1>", open_calendar)
        HoverTip(self._mq, lambda: "คลิกเพื่อดูปฏิทินข่าวทั้งหมด")
        self._mq_gen = getattr(self, "_mq_gen", 0) + 1   # สร้างแถบหัวใหม่ → รอบวิ่งของตัวเก่าหยุดเอง (ไม่วิ่งซ้อนเร็วขึ้น 2 เท่า)
        self.after(500, lambda g=self._mq_gen: self._marquee_tick(g))

    def _marquee_tick(self, gen=None):
        """เลื่อนข้อความวิ่งจากขวาไปซ้าย (~50 px/วินาที) · ชี้เมาส์ค้างไว้เพื่อหยุดอ่าน"""
        if gen != getattr(self, "_mq_gen", None):
            return
        cv = getattr(self, "_mq", None)
        try:
            if cv is None or not cv.winfo_exists():
                return   # แถบหัวถูกสร้างใหม่ (ออกจากระบบ/สลับหน้า) — ตัวใหม่เริ่มรอบของตัวเอง
        except Exception:
            return
        try:
            w = cv.winfo_width()
            x0, _, x1, _ = cv.bbox(self._mq_item) or (0, 0, 0, 0)
            tw = x1 - x0
            if self._mq_x is None or self._mq_x + tw < 0:
                self._mq_x = w
            try:
                under = cv.winfo_containing(cv.winfo_pointerx(), cv.winfo_pointery()) is cv
            except Exception:
                under = False   # เมาส์อยู่บนเมนู dropdown/หน้าต่างอื่น — Tk หา widget ไม่เจอ (KeyError)
            if not under:
                self._mq_x -= 1.5
            cv.coords(self._mq_item, self._mq_x, 12)
        except Exception:
            pass
        try:
            self.after(30, lambda: self._marquee_tick(gen))   # ตั้งรอบถัดไปเสมอ (เดิม error ครั้งเดียวทำให้ข้อความหยุดวิ่งถาวร)
        except Exception:
            pass

    PLAN_ROWS = [
        ("📈", "P1 · MA M15", "Plan 1: MA-Cross-Trend"),
        ("👑", "P2 · MA H1", "Plan 2: MA-Cross-H1-Trend"),
        ("⚡", "P3 · SMC Hunt", "Plan 3: SMC-LiquidityHunt"),
        ("🎯", "P4 · SR Bounce", "Plan 4: SR-SwingBounce"),
        ("🌊", "P5 · BB-H1", "Plan 5: BB-H1-Reversion"),
        ("◆", "P6 · SAR H1", "Plan 6: PSAR-H1-Trend"),
    ]

    def _build_plans_card(self, parent):
        card = self._card(parent, fill="both", expand=True)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(4, 2))
        self.lbl_plans_title = ctk.CTkLabel(head, text="⚡ แผนเทรด", font=self._font(13, "bold"), text_color=COLOR_TEXT_PRIMARY)
        self.lbl_plans_title.pack(side="left")
        ctk.CTkLabel(head, text="ติ๊กเลือกแผนที่ใช้", font=self._font(10), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=8)
        ctk.CTkButton(
            head, text="ละเอียด ›", font=self._font(11, "bold"), fg_color="transparent", hover_color="#1F2430",
            text_color=COLOR_CYAN_ACCENT, width=64, height=24, corner_radius=6, command=self._open_user_stats_modal,
        ).pack(side="right")

        table = ctk.CTkFrame(card, fg_color="#101218", corner_radius=10)
        table.pack(fill="x", padx=14, pady=(0, 6))
        table.grid_columnconfigure(0, weight=1)
        for col, (title, anchor) in enumerate((("แผน", "w"), ("ไม้", "e"), ("WR", "e"), ("กำไร", "e"))):
            ctk.CTkLabel(table, text=title, font=self._font(10, "bold"), text_color=COLOR_TEXT_MUTED, anchor=anchor, height=18).grid(
                row=0, column=col, sticky="ew", padx=(12 if col == 0 else 4, 12 if col == 3 else 4), pady=(4, 0)
            )

        # plan_stat_badges: {ชื่อแผนเต็ม: (label ไม้, label WR, label กำไร)}
        self.plan_stat_badges = {}
        self.plan_checks = {}
        self.plan_live_badges = {}
        self._plan_row_bg = {}   # สีพื้นแถว (สลับอ่อน/เข้ม) — ใช้คืนสีป้าย ● BUY/SELL ตอนไม่มีไม้

        def stripe(row):
            """พื้นสลับสีทีละแถว: แถวคี่มีแถบเต็มแถวด้านหลัง (ช่องในแถวใช้สีเดียวกันให้ต่อเนื่อง)"""
            if row % 2 == 1:
                ctk.CTkFrame(table, fg_color="#1A1F29", corner_radius=6, height=20).grid(row=row, column=0, columnspan=4, sticky="nsew", padx=6)
                return "#1A1F29"
            return "#101218"

        for r, (icon, short, full) in enumerate(self.PLAN_ROWS, start=1):
            last = r == len(self.PLAN_ROWS)
            pady = 0
            bg = stripe(r)
            self._plan_row_bg[full] = bg
            # ติ๊กเลือกใช้แผนนี้ (จำแยกตามบัญชีผู้ใช้) — แผนที่แอดมินปิดจะติ๊กไม่ได้
            var = tk.BooleanVar(value=plan_config.user_enabled(full.split(": ", 1)[-1]))
            chk = ctk.CTkCheckBox(
                table, text=f"{icon}  {short}", variable=var, font=self._font(11, "bold"), text_color=COLOR_TEXT_PRIMARY,
                fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK, checkbox_width=14, checkbox_height=14, height=17,
                bg_color=bg, command=lambda f=full, v=var: self._toggle_user_plan(f, v),
            )
            chk.grid(row=r, column=0, sticky="w", padx=(10, 4), pady=pady)
            self.plan_checks[full] = (chk, var)
            # ป้ายไม้ที่เปิดอยู่ของแผนนี้ (เช่น "● SELL") — อัปเดตทุก 2 วินาที
            live = ctk.CTkLabel(table, text="", font=self._font(10, "bold"), text_color=COLOR_GOLD_PRIMARY, corner_radius=6, height=16,
                                fg_color=bg, bg_color=bg)
            live.grid(row=r, column=0, sticky="e", padx=(4, 0), pady=pady)
            self.plan_live_badges[full] = live
            cells = []
            for col in (1, 2, 3):
                lbl = ctk.CTkLabel(table, text="0" if col == 1 else ("—" if col == 2 else "0.00"), font=self._font(11), text_color=COLOR_TEXT_MUTED, anchor="e", height=17, width=40 if col < 3 else 64,
                                   fg_color=bg)
                lbl.grid(row=r, column=col, sticky="e", padx=(4, 12 if col == 3 else 4), pady=pady)
                cells.append(lbl)
            self.plan_stat_badges[full] = tuple(cells)
        # แถวไม้ที่เข้าเอง (ปุ่ม BUY/SELL ในแผงควบคุม → comment "Manual-Quick") — ไม่มีช่องติ๊ก
        n = len(self.PLAN_ROWS) + 1
        mkey = bot_ctrl.QUICK_PLAN
        mbg = stripe(n)
        self._plan_row_bg[mkey] = mbg
        self.manual_plan_label = ctk.CTkLabel(table, text="✋  เข้าไม้เอง", font=self._font(11, "bold"), text_color=COLOR_TEXT_PRIMARY,
                                              anchor="w", height=18, fg_color=mbg)
        self.manual_plan_label.grid(row=n, column=0, sticky="w", padx=(31, 4), pady=(0, 2))
        live = ctk.CTkLabel(table, text="", font=self._font(10, "bold"), text_color=COLOR_GOLD_PRIMARY, corner_radius=6, height=16,
                            fg_color=mbg, bg_color=mbg)
        live.grid(row=n, column=0, sticky="e", padx=(4, 0), pady=(0, 4))
        self.plan_live_badges[mkey] = live
        cells = []
        for col in (1, 2, 3):
            lbl = ctk.CTkLabel(table, text="0" if col == 1 else ("—" if col == 2 else "0.00"), font=self._font(11),
                               text_color=COLOR_TEXT_MUTED, anchor="e", height=18, width=40 if col < 3 else 64, fg_color=mbg)
            lbl.grid(row=n, column=col, sticky="e", padx=(4, 12 if col == 3 else 4), pady=(0, 4))
            cells.append(lbl)
        self.plan_stat_badges[mkey] = tuple(cells)
        # แถวผลรวมทุกแผน (รวมไม้ที่เข้าเอง)
        ctk.CTkFrame(table, fg_color=COLOR_CARD_BORDER, height=1).grid(row=n + 1, column=0, columnspan=4, sticky="ew", padx=10, pady=(1, 1))
        ctk.CTkLabel(table, text="รวมทุกแผน", font=self._font(11, "bold"), text_color=COLOR_GOLD_PRIMARY, anchor="w", height=18).grid(
            row=n + 2, column=0, sticky="ew", padx=(12, 4), pady=(0, 3))
        self.plan_total_labels = []
        for col in (1, 2, 3):
            lbl = ctk.CTkLabel(table, text="0" if col == 1 else ("—" if col == 2 else "0.00"), font=self._font(11, "bold"),
                               text_color=COLOR_TEXT_MUTED, anchor="e", height=18, width=40 if col < 3 else 64)
            lbl.grid(row=n + 2, column=col, sticky="e", padx=(4, 12 if col == 3 else 4), pady=(0, 3))
            self.plan_total_labels.append(lbl)
        self.after(300, self._plan_checks_tick)
        self.after(1000, self._plan_live_tick)

    def _plan_live_tick(self):
        """แสดงป้าย ● BUY / ● SELL ที่แผนที่มีไม้เปิดอยู่ตอนนี้"""
        try:
            import MetaTrader5 as _mt5
            open_by_plan = {}
            for p in _mt5.positions_get(symbol="XAUUSD") or []:
                base = plan_config.base_plan(p.comment)
                open_by_plan.setdefault(base, []).append(("BUY" if p.type == 0 else "SELL", float(p.profit)))
            for full, lbl in self.plan_live_badges.items():
                items = open_by_plan.get(full.split(": ", 1)[-1], [])
                if full in self.plan_checks:
                    chk, var = self.plan_checks[full]
                    if plan_config.admin_enabled(full.split(": ", 1)[-1]):
                        chk.configure(text_color=COLOR_SUCCESS_GREEN if items else (COLOR_TEXT_PRIMARY if var.get() else COLOR_TEXT_MUTED))
                elif getattr(self, "manual_plan_label", None) is not None:   # แถวเข้าไม้เอง
                    self.manual_plan_label.configure(text_color=COLOR_SUCCESS_GREEN if items else COLOR_TEXT_PRIMARY)
                if items:
                    side = items[0][0] if len({i[0] for i in items}) == 1 else "BUY/SELL"
                    prof = sum(i[1] for i in items)
                    lbl.configure(text=f" ● {side}{' ×' + str(len(items)) if len(items) > 1 else ''} ",
                                  fg_color="#0F2A20" if side == "BUY" else "#2A1215" if side == "SELL" else COLOR_GOLD_BG,
                                  text_color=COLOR_SUCCESS_GREEN if prof >= 0 else COLOR_DANGER_RED)
                else:
                    plan_code = None
                    if "Plan 1" in full: plan_code = "P1"
                    elif "Plan 2" in full: plan_code = "P2"
                    elif "Plan 3" in full: plan_code = "P3"
                    elif "Plan 4" in full: plan_code = "P4"
                    elif "Plan 5" in full: plan_code = "P5"
                    elif "Plan 6" in full: plan_code = "P6"
                    pinfo = plans_status.get(plan_code) if plan_code else None
                    if pinfo:
                        m, tot = pinfo["matched"], pinfo["total"]
                        side_s = "▲" if pinfo["side"] == "BUY" else "▼"
                        if m == tot and tot > 0:
                            lbl.configure(text=f" ★ {side_s} {m}/{tot} ", fg_color="#064E3B", text_color=COLOR_SUCCESS_GREEN)
                        elif pinfo["pct"] >= 50:
                            lbl.configure(text=f" {side_s} {m}/{tot} ข้อ ", fg_color=getattr(self, "_plan_row_bg", {}).get(full, "transparent"), text_color=COLOR_GOLD_PRIMARY)
                        else:
                            lbl.configure(text=f" {side_s} {m}/{tot} ข้อ ", fg_color=getattr(self, "_plan_row_bg", {}).get(full, "transparent"), text_color=COLOR_TEXT_MUTED)
                    else:
                        lbl.configure(text="", fg_color=getattr(self, "_plan_row_bg", {}).get(full, "transparent"))
        except Exception:
            pass
        self.after(2000, self._plan_live_tick)

    def _ma_order_tick(self):
        """อ่านลำดับ MA50/100/150 ของ H1/H4 จาก MT5 ในเธรดเบื้องหลังทุก 30 วิ — เธรดหลักตรวจผลทุก 1 วิแล้วแสดงบนการ์ด
        (Tk ห้ามเรียกจากเธรดอื่น จึงส่งผลผ่านตัวแปรแทน self.after)"""
        st = self.__dict__.setdefault("_ma_state", {"data": None, "busy": False, "next": 0.0})
        if st["data"] is not None:
            data, st["data"] = st["data"], None
            try:
                self._apply_ma_order(data)
            except Exception:
                pass   # ค่า MA ไม่ครบ (ข้อมูลแท่งไม่พอ) — ไม่ให้ลูปหยุด
        if not st["busy"] and time.time() >= st["next"]:
            st["busy"], st["next"] = True, time.time() + 30

            def work():
                try:
                    st["data"] = bot_ctrl.get_market_explain()
                finally:
                    st["busy"] = False
            threading.Thread(target=work, daemon=True).start()
        self.after(1000, self._ma_order_tick)

    def _apply_ma_order(self, data):
        if not data:
            return
        rows = getattr(self, "card_trend", {}).get("rows", {})
        for tf, row in rows.items():
            d = data.get(tf)
            if not d:
                continue
            m = d["ma"]
            op1 = "<" if m[50] < m[100] else ">"
            op2 = "<" if m[100] < m[150] else ">"
            color = COLOR_DANGER_RED if op1 == op2 == "<" else COLOR_SUCCESS_GREEN if op1 == op2 == ">" else COLOR_CYAN_ACCENT
            row["lt"].configure(text=f"50{op1}100{op2}150", text_color=color)

    def _plan_checks_tick(self):
        """อัปเดตสถานะช่องติ๊กแผน (แอดมินอาจเปิด/ปิดแผนจากเว็บ) ทุก 30 วินาที"""
        try:
            self._sync_plan_checks()
        except Exception:
            pass
        self.after(30000, self._plan_checks_tick)

    def _toggle_user_plan(self, full_name, var):
        base = full_name.split(": ", 1)[-1]
        try:
            plan_config.set_user_enabled(base, bool(var.get()))
        except Exception:
            var.set(not var.get())
            return
        enabled = sum(1 for _c, v in self.plan_checks.values() if v.get())
        print(f"[PLAN SELECT] {'เปิดใช้' if var.get() else 'ปิด'}แผน {base} — ใช้งาน {enabled}/{len(self.plan_checks)} แผน")
        self._sync_plan_checks()

    def _sync_plan_checks(self):
        """แผนที่แอดมินปิด: เอาเครื่องหมายติ๊กออก + กดไม่ได้ + สีเทา + ป้าย "แอดมินปิด"
        (ไม่แตะค่าที่ผู้ใช้เลือกไว้ — เมื่อแอดมินเปิดคืน ช่องติ๊กกลับเป็นค่าเดิมของผู้ใช้)"""
        if not getattr(self, "plan_checks", None):
            return
        active = 0
        for full, (chk, var) in self.plan_checks.items():
            base = full.split(": ", 1)[-1]
            admin_on = plan_config.admin_enabled(base)
            label = next((f"{ic}  {sh}" for ic, sh, fl in self.PLAN_ROWS if fl == full), base)
            if admin_on:
                if chk.cget("state") == "disabled":          # แอดมินเพิ่งเปิดคืน → คืนค่าที่ผู้ใช้เลือก
                    var.set(plan_config.user_enabled(base))
                chk.configure(state="normal", text=label, fg_color=COLOR_GOLD_WARM, border_color="#949A9F",
                              text_color=COLOR_TEXT_PRIMARY if var.get() else COLOR_TEXT_MUTED)
                active += 1 if var.get() else 0
            else:
                var.set(False)                                  # แสดงเป็นไม่ได้เลือก (ไม่บันทึกทับค่าผู้ใช้)
                chk.configure(state="disabled", text=f"{label}  · แอดมินปิด", fg_color="#3A3F4A",
                              border_color="#3A3F4A", text_color="#5A6070", text_color_disabled="#5A6070")
        if hasattr(self, "lbl_plans_title"):
            self.lbl_plans_title.configure(text=f"⚡ แผนเทรด (ใช้ {active}/{len(self.plan_checks)})")

    # ---------------------------------------------------------------------
    # คอลัมน์ซ้าย: แท็บ Console / ประวัติเทรด / ปฏิทินข่าว
    # ---------------------------------------------------------------------
    TAB_CONSOLE = "🖥  Console"
    TAB_POSITIONS = "📌  ออเดอร์ที่เปิดอยู่"
    TAB_HISTORY = "📋  ประวัติการเทรด"
    TAB_CALENDAR = "📅  ปฏิทินเศรษฐกิจ"
    TAB_AI = "🔮  AI คาดการณ์"

    def _build_main_tabs(self, parent):
        self.main_tabs = ctk.CTkTabview(
            parent,
            fg_color=COLOR_CARD_BG,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            corner_radius=12,
            segmented_button_fg_color="#101218",
            segmented_button_selected_color=COLOR_GOLD_WARM,
            segmented_button_selected_hover_color=COLOR_GOLD_DARK,
            segmented_button_unselected_color="#101218",
            segmented_button_unselected_hover_color="#1F2430",
            text_color=COLOR_TEXT_PRIMARY,
            anchor="w",
        )
        self.main_tabs.pack(fill="both", expand=True)
        self.main_tabs._segmented_button.configure(font=self._font(13, "bold"))
        for name in (self.TAB_CONSOLE, self.TAB_POSITIONS, self.TAB_HISTORY, self.TAB_CALENDAR, self.TAB_AI):
            self.main_tabs.add(name)

        self._build_terminal_console(self.main_tabs.tab(self.TAB_CONSOLE))
        self._build_positions_tab(self.main_tabs.tab(self.TAB_POSITIONS))
        self._build_history_tab(self.main_tabs.tab(self.TAB_HISTORY))
        self._build_calendar_tab(self.main_tabs.tab(self.TAB_CALENDAR))
        self._build_ai_tab(self.main_tabs.tab(self.TAB_AI))
        self.main_tabs.set(self.TAB_CONSOLE)

    def _build_terminal_console(self, parent):
        """คอนโซลแสดงผลสดการทำงานของบอท (จัดสีตามความสำคัญ + ซ่อนข้อความที่ไม่จำเป็น)"""
        self._console_formatter = ConsoleFormatter()
        self._console_entries = deque(maxlen=3000)
        self.show_detail_var = tk.BooleanVar(value=False)

        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", padx=6, pady=(0, 6))
        legend = ctk.CTkFrame(bar, fg_color="transparent")
        legend.pack(side="left")
        for text, tag in (("● เปิด BUY", "buy"), ("● เปิด SELL", "sell"), ("● ปิด/TP", "close"), ("● ล็อกกำไร", "lock"), ("● ผิดพลาด", "error")):
            ctk.CTkLabel(legend, text=text, font=self._font(11), text_color=TAG_COLORS[tag]).pack(side="left", padx=(0, 10))

        # ป้ายสถานะตลาดทองคำสด (เปิด/ปิด/พักเบรก)
        self.lbl_market_status = ctk.CTkLabel(
            legend, text="", font=self._font(11, "bold"), height=22, corner_radius=6,
            fg_color="#2A1414", text_color=COLOR_DANGER_RED
        )
        self.lbl_market_status.pack(side="left", padx=(4, 0))

        ctk.CTkButton(bar, text="ล้าง", font=self._font(11, "bold"), width=56, height=26, corner_radius=8,
                      fg_color="#2E2410", hover_color="#3A2E14", border_width=1, border_color="#7A5A1C",
                      text_color=COLOR_GOLD_PRIMARY, command=self._clear_console).pack(side="right")
        # ล้างคอนโซลอัตโนมัติทุก 1 ชม. (ค่าเริ่มต้น: เปิด · จำค่าไว้ใน bot_settings.json)
        self.console_autoclear_var = tk.BooleanVar(value=bool(self._load_setting("console_autoclear", True)))
        ctk.CTkCheckBox(
            bar, text="ล้างอัตโนมัติทุก 1 ชม.", variable=self.console_autoclear_var, font=self._font(11), text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK, checkbox_width=16, checkbox_height=16,
            command=lambda: self._save_setting("console_autoclear", bool(self.console_autoclear_var.get())),
        ).pack(side="right", padx=(0, 10))
        self._console_cleared_at = time.time()
        self.after(60000, self._console_autoclear_tick)
        self.chk_autoscroll = ctk.CTkCheckBox(
            bar, text="เลื่อนอัตโนมัติ", font=self._font(11), text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK, checkbox_width=16, checkbox_height=16,
            command=self._on_toggle_autoscroll,
        )
        self.chk_autoscroll.select()
        self.chk_autoscroll.pack(side="right", padx=(0, 10))
        ctk.CTkCheckBox(
            bar, text="รายละเอียดการสแกน", variable=self.show_detail_var, font=self._font(11), text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK, checkbox_width=16, checkbox_height=16,
            command=self._rerender_console,
        ).pack(side="right", padx=(0, 10))

        self.txt_console = ctk.CTkTextbox(
            parent,
            font=ctk.CTkFont(family=app_fonts.MONO, size=12),
            fg_color="#0B0D12",
            text_color=TAG_COLORS["text"],
            corner_radius=8,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            wrap="word",
        )
        self.txt_console.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        for tag, color in TAG_COLORS.items():
            self.txt_console.tag_config(tag, foreground=color)

        self.txt_console.configure(state="disabled")
        self._console_banner()

    def _get_console_banner(self):
        mkt = thai_time.get_gold_market_status()
        status_tag = "profit" if mkt.get("is_open") else ("warn" if mkt.get("state") == "DAILY_BREAK" else "error")
        return [
            (f"🏆 AI Gold Commander Pro v{APP_VERSION}\n", "close"),
            ("XAUUSD · P1 SL 1.0 ATR ไม่ตั้ง TP · P2 SL 1.25 ATR (H1) ไม่ตั้ง TP · P3–P4 SL 1.0 / TP 2.0 ATR · P5 SL 0.75 ATR · TP RRR 1:1.5 · P6 SL ตาม SAR ไม่ตั้ง TP\n", "muted"),
            (f"{mkt['headline']} · {mkt['subtext']}\n", status_tag),
            ("คิดเวลาเฉพาะตอนบอททำงาน (ช่วงตลาดปิดไม่หักชั่วโมงการใช้งาน)\n", "muted"),
            ("กด ▶ เริ่มการทำงานบอท ด้านขวาเพื่อเริ่มสแกนตลาด — ที่นี่จะแสดงเฉพาะเหตุการณ์สำคัญ (เปิด/ปิดออเดอร์ ฯลฯ)\n\n", "profit"),
        ]

    def _console_banner(self, note=""):
        self.txt_console.configure(state="normal")
        banner_items = self._get_console_banner()
        if note:
            banner_items.append((note, "muted"))
        for text, tag in banner_items:
            self._console_entries.append((text, tag, "key"))
            self.txt_console.insert("end", text, tag)
        self.txt_console.configure(state="disabled")

    def _console_autoclear_tick(self):
        """ทุก 1 นาที: ถ้าเปิด 'ล้างอัตโนมัติ' และครบ 1 ชม. นับจากล้างครั้งล่าสุด → ล้างคอนโซล"""
        try:
            if self.console_autoclear_var.get() and time.time() - self._console_cleared_at >= 3600:
                self._clear_console(note=f"ล้างประวัติอัตโนมัติเมื่อ {thai_time.fmt_now('%H:%M')} น. (ปิดได้ที่ช่อง 'ล้างอัตโนมัติทุก 1 ชม.')\n\n")
        except Exception:
            pass
        self.after(60000, self._console_autoclear_tick)

    @staticmethod
    def _load_setting(key, default):
        try:
            with open(data_path("bot_settings.json"), "r", encoding="utf-8") as f:
                return json.load(f).get(key, default)
        except Exception:
            return default

    @staticmethod
    def _save_setting(key, value):
        """บันทึกค่าตั้งลง bot_settings.json โดยไม่ทับค่าอื่น (เช่น lot)"""
        path = data_path("bot_settings.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        data[key] = value
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def _auto_algo_trading(self, reason="", warn=True):
        """ตรวจปุ่ม Algo Trading ใน MT5 — ปิดอยู่ → กด Ctrl+E ให้ (เธรดเบื้องหลัง) แล้วแจ้งผลใน Console
        เรียกตอนเปิดโปรแกรม และเมื่อ MT5 เปลี่ยนบัญชี (MT5 มักปิด Algo Trading เองเมื่อสลับบัญชี)"""
        if getattr(self, "_algo_busy", False):
            return
        self._algo_busy = True

        def worker():
            try:
                ok, msg = mt5_algo.ensure_enabled()
            except Exception as e:
                ok, msg = False, f"ตรวจ Algo Trading ไม่สำเร็จ ({e})"
            def done():
                self._algo_busy = False
                try:
                    self._append_console(self._console_formatter.feed(f"[ALGO TRADING] {reason}{msg}\n"))
                except Exception:
                    pass
                if not ok and warn:
                    messagebox.showwarning("Algo Trading ใน MT5 ยังปิดอยู่", msg + "\nบอทเทรดไม่ได้จนกว่าปุ่ม Algo Trading ใน MT5 จะเป็นสีเขียว")
            self.after(0, done)
        threading.Thread(target=worker, daemon=True).start()

    def _append_console(self, entries):
        """เพิ่มข้อความที่จัดรูปแบบแล้วลงคอนโซล (เคารพตัวเลือก 'รายละเอียดการสแกน')"""
        show_detail = self.show_detail_var.get()
        visible = [(t, tag) for (t, tag, level) in entries if level == "key" or show_detail]
        self._console_entries.extend(entries)
        if not visible:
            return
        self.txt_console.configure(state="normal")
        for text, tag in visible:
            self.txt_console.insert("end", text, tag)
        # จำกัดความยาวไม่ให้กินหน่วยความจำ
        line_count = int(self.txt_console.index("end-1c").split(".")[0])
        if line_count > 2500:
            self.txt_console.delete("1.0", f"{line_count - 2000}.0")
        self.txt_console.configure(state="disabled")
        if self.auto_scroll_logs:
            self.txt_console.see("end")

    def _rerender_console(self):
        show_detail = self.show_detail_var.get()
        self.txt_console.configure(state="normal")
        self.txt_console.delete("1.0", "end")
        for text, tag, level in self._console_entries:
            if level == "key" or show_detail:
                self.txt_console.insert("end", text, tag)
        self.txt_console.configure(state="disabled")
        self.txt_console.see("end")

    # ---- ออเดอร์ที่เปิดอยู่ (เรียลไทม์) ----
    POSITION_COLUMNS = [
        ("Ticket", 74, "w"),
        ("ฝั่ง", 40, "center"),
        ("แผน", 96, "w"),
        ("Lot", 34, "e"),
        ("ราคาเข้า", 68, "e"),
        ("ราคาปัจจุบัน", 76, "e"),
        ("Stop Loss", 80, "e"),
        ("ถ้าชน SL", 66, "e"),
        ("Take Profit", 74, "e"),
        ("ถือมา", 54, "e"),
        ("กำไร", 64, "e"),
        ("AI แนะนำ", 72, "center"),
        ("", 42, "center"),
    ]
    POS_AI_COL = 11          # คอลัมน์ป้ายคำแนะนำ AI (ถือต่อ / ระวัง / ควรปิด)
    ADVICE_SHORT = {"hold": "ถือต่อ", "caution": "ระวัง", "close": "ควรปิด"}

    def _build_positions_tab(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=6, pady=(0, 8))
        self.lbl_positions_summary = ctk.CTkLabel(top, text="ไม่มีออเดอร์ที่เปิดอยู่", font=self._font(12, "bold"), text_color=COLOR_TEXT_MUTED)
        self.lbl_positions_summary.pack(side="left")
        ctk.CTkLabel(top, text="คลิกที่ไม้เพื่อดูกราฟ M15 + อินดิเคเตอร์ของแผน · อัปเดตอัตโนมัติ", font=self._font(10), text_color=COLOR_TEXT_MUTED).pack(side="right")

        adv = ctk.CTkFrame(parent, fg_color="#101218", corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        adv.pack(side="bottom", fill="x", padx=6, pady=(4, 4))
        ahead = ctk.CTkFrame(adv, fg_color="transparent")
        ahead.pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(ahead, text="AI วิเคราะห์ไม้ที่ถืออยู่ · ถือต่อหรือปิด?", font=self._font(13, "bold"),
                     text_color=COLOR_GOLD_PRIMARY).pack(side="left")
        self.lbl_advice_meta = ctk.CTkLabel(ahead, text="", font=self._font(10), text_color=COLOR_TEXT_MUTED)
        self.lbl_advice_meta.pack(side="right")
        self.advice_body = ctk.CTkScrollableFrame(adv, fg_color="transparent", height=230)
        self.advice_body.pack(fill="x", padx=4, pady=(0, 4))
        ctk.CTkLabel(adv, text="วิเคราะห์จากกฎ: เทรนด์ H1/H4 · MA200 · โมเมนตัม M15 · แนวรับ/ต้าน · AI 1-4 ชม. · สัญญาณออกของแผน · SL/TP · ข่าวแรง "
                               "— ใช้ประกอบการตัดสินใจ ไม่รับประกันผล",
                     font=self._font(10), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=12, pady=(0, 6))
        self._advice_sig = None
        position_advisor.start_background()

        table = ctk.CTkFrame(parent, fg_color="#101218", corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        table.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        head = ctk.CTkFrame(table, fg_color="transparent")
        head.pack(fill="x", padx=6, pady=(8, 0))
        self._configure_position_grid(head)
        for col, (title, _, anchor) in enumerate(self.POSITION_COLUMNS):
            ctk.CTkLabel(head, text=title, font=self._font(11, "bold"), text_color=COLOR_TEXT_MUTED, anchor=anchor, height=22).grid(row=0, column=col, sticky="ew", padx=4)
        ctk.CTkFrame(table, fg_color=COLOR_CARD_BORDER, height=1).pack(fill="x", padx=10, pady=(4, 0))

        self.positions_body = ctk.CTkScrollableFrame(table, fg_color="transparent")
        self.positions_body.pack(fill="both", expand=True, padx=0, pady=(0, 6))
        self.lbl_positions_empty = ctk.CTkLabel(
            self.positions_body, text="ยังไม่มีออเดอร์ที่เปิดอยู่ — บอทกำลังรอสัญญาณที่เข้าเงื่อนไข",
            font=self._font(12), text_color=COLOR_TEXT_MUTED,
        )
        self.lbl_positions_empty.pack(pady=40)
        self._position_rows = {}

    def _configure_position_grid(self, frame):
        for col, (_, width, _) in enumerate(self.POSITION_COLUMNS):
            frame.grid_columnconfigure(col, minsize=width, weight=1 if col == 2 else 0)

    @staticmethod
    def _fmt_duration(seconds):
        seconds = max(0, int(seconds))
        d, rem = divmod(seconds, 86400)
        h, rem = divmod(rem, 3600)
        m = rem // 60
        if d:
            return f"{d}ว {h}ชม"
        if h:
            return f"{h}ชม {m}น"
        return f"{m} นาที"

    def _render_positions(self, positions, server_time):
        positions = sorted(positions or [], key=lambda p: p.get("time", 0), reverse=True)
        tickets = [p["ticket"] for p in positions]
        self._positions_by_ticket = {p["ticket"]: p for p in positions}

        # สร้าง/ลบแถวเฉพาะเมื่อรายการ ticket เปลี่ยน (นอกนั้นอัปเดตข้อความในที่เดิม)
        if tickets != list(self._position_rows.keys()):
            for row in self._position_rows.values():
                row["frame"].destroy()
            self._position_rows = {}
            for t in tickets:
                frame = ctk.CTkFrame(self.positions_body, fg_color="#14171E", corner_radius=8)
                frame.pack(fill="x", padx=4, pady=2)
                self._configure_position_grid(frame)
                cells = []
                for col, (_, _, anchor) in enumerate(self.POSITION_COLUMNS[:-1]):
                    if col == self.POS_AI_COL:   # ป้ายคำแนะนำ AI — ชี้เพื่อดูเหตุผล
                        lbl = ctk.CTkLabel(frame, text="…", font=self._font(11, "bold"), corner_radius=6, height=24, width=64,
                                           fg_color="#1A1E27", text_color=COLOR_TEXT_MUTED)
                        lbl.grid(row=0, column=col, padx=4)
                        HoverTip(lbl, lambda tk_=t: self._advice_tip(tk_))
                    else:
                        lbl = ctk.CTkLabel(frame, text="", font=self._font(12), anchor=anchor, height=32)
                        lbl.grid(row=0, column=col, sticky="ew", padx=4)
                    cells.append(lbl)
                btn = ctk.CTkButton(
                    frame, text="ปิด", width=40, height=24, corner_radius=6, font=self._font(11, "bold"),
                    fg_color="#3A2226", hover_color="#4A2A2F", text_color=COLOR_DANGER_RED,
                    command=lambda tk_=t: self._on_close_single(tk_),
                )
                btn.grid(row=0, column=len(self.POSITION_COLUMNS) - 1, padx=4)
                for wdg in [frame] + cells:   # คลิกที่แถว → กราฟ M15 + อินดิเคเตอร์ของแผน
                    wdg.bind("<Button-1>", lambda e, tk_=t: self._open_position_detail(tk_), add="+")
                    try:
                        wdg.configure(cursor="hand2")
                    except Exception:
                        pass
                self._position_rows[t] = {"frame": frame, "cells": cells}
            if tickets:
                self.lbl_positions_empty.pack_forget()
            else:
                self.lbl_positions_empty.pack(pady=40)
            position_advisor.request_refresh()
        self._render_advice(tickets)

        total_profit = 0.0
        total_lot = 0.0
        buys = sells = 0
        for p in positions:
            is_buy = p.get("type") == "BUY"
            buys += is_buy
            sells += not is_buy
            profit = float(p.get("profit", 0.0)) + float(p.get("swap", 0.0))
            total_profit += profit
            total_lot += float(p.get("volume", 0.0))
            open_price = float(p.get("price_open", 0.0))
            sl, tp = float(p.get("sl", 0.0)), float(p.get("tp", 0.0))
            # SL ล็อกกำไรแล้ว = SL อยู่ฝั่งกำไรของราคาเข้า (Early Profit Lock)
            locked = sl > 0 and ((is_buy and sl > open_price) or (not is_buy and sl < open_price))
            sl_text = "ไม่มี" if sl <= 0 else (f"🔒 {sl:,.2f}" if locked else f"{sl:,.2f}")
            held = self._fmt_duration(server_time - p.get("time", server_time)) if server_time and p.get("time") else "—"
            # ถ้าราคาชน SL ตอนนี้จะได้/เสียเท่าไร (บวก = ล็อกกำไรแล้ว · ลบ = ยังเสี่ยงขาดทุน)
            sl_pnl = p.get("sl_pnl")
            if sl_pnl is None:
                sl_pnl_text, sl_pnl_col = "ไม่มี SL", COLOR_DANGER_RED
            else:
                sl_pnl_text = f"{'+' if sl_pnl >= 0 else '-'}{abs(sl_pnl):,.2f}"
                sl_pnl_col = COLOR_CYAN_ACCENT if sl_pnl > 0 else (COLOR_DANGER_RED if sl_pnl < 0 else COLOR_TEXT_MUTED)
            values = [
                f"#{p['ticket']}",
                p.get("type", ""),
                position_chart.plan_of(p.get("comment"))[1][:16],
                f"{float(p.get('volume', 0)):.2f}",
                f"{open_price:,.2f}",
                f"{float(p.get('price_current', 0)):,.2f}",
                sl_text,
                sl_pnl_text,
                f"{tp:,.2f}" if tp > 0 else "รันเทรนด์",
                held,
                f"{'+' if profit >= 0 else '-'}{abs(profit):,.2f}",
            ]
            colors = [
                COLOR_TEXT_MUTED,
                COLOR_SUCCESS_GREEN if is_buy else COLOR_DANGER_RED,
                COLOR_TEXT_PRIMARY,
                COLOR_TEXT_PRIMARY,
                COLOR_TEXT_PRIMARY,
                COLOR_GOLD_PRIMARY,
                COLOR_CYAN_ACCENT if locked else COLOR_TEXT_MUTED,
                sl_pnl_col,
                COLOR_TEXT_MUTED,
                COLOR_TEXT_MUTED,
                COLOR_SUCCESS_GREEN if profit > 0 else (COLOR_DANGER_RED if profit < 0 else COLOR_TEXT_MUTED),
            ]
            cells = self._position_rows[p["ticket"]]["cells"]
            for lbl, v, c in zip(cells, values, colors):
                if lbl.cget("text") != v:
                    lbl.configure(text=v, text_color=c)
            # ป้ายคำแนะนำ AI ท้ายแถว (ผลจาก position_advisor — อัปเดตทุก 30 วิ)
            a = position_advisor.latest().get(p["ticket"])
            ai_lbl = cells[self.POS_AI_COL]
            if a:
                fg, bg = self.ADVICE_STYLE[a["verdict"]]
                ai_text = self.ADVICE_SHORT[a["verdict"]]
            else:
                fg, bg, ai_text = COLOR_TEXT_MUTED, "#1A1E27", "…"
            if ai_lbl.cget("text") != ai_text:
                ai_lbl.configure(text=ai_text, text_color=fg, fg_color=bg)

        if positions:
            self.lbl_positions_summary.configure(
                text=f"{len(positions)} ไม้ (BUY {buys} · SELL {sells}) · รวม {total_lot:.2f} Lot · กำไรลอยตัว {'+' if total_profit >= 0 else '-'}{abs(total_profit):,.2f}",
                text_color=COLOR_SUCCESS_GREEN if total_profit > 0 else (COLOR_DANGER_RED if total_profit < 0 else COLOR_TEXT_PRIMARY),
            )
        else:
            self.lbl_positions_summary.configure(text="ไม่มีออเดอร์ที่เปิดอยู่", text_color=COLOR_TEXT_MUTED)

    def _advice_tip(self, ticket):
        """ข้อความเมื่อชี้ป้าย AI แนะนำ: คำแนะนำ + เหตุผลหลัก 4 ข้อ"""
        a = position_advisor.latest().get(ticket)
        if not a:
            return "AI กำลังวิเคราะห์ไม้นี้ (อัปเดตทุก 30 วินาที)"
        lines = [f"{a['verdict_text']} (คะแนน {a['score']:+.1f})", a["advice"], ""]
        for r in a["reasons"][:4]:
            mark = "✓" if r["w"] > 0 else ("✗" if r["w"] < 0 else "•")
            lines.append(f"{mark} {r['text']}")
        return "\n".join(lines)

    ADVICE_STYLE = {
        "hold": (COLOR_SUCCESS_GREEN, "#12261C"),
        "caution": (COLOR_GOLD_PRIMARY, "#2A2412"),
        "close": (COLOR_DANGER_RED, "#2C1618"),
    }

    def _render_advice(self, tickets):
        """การ์ดคำแนะนำ ถือต่อ/ปิด ต่อไม้ (อ่านผลจากเธรด position_advisor — วาดใหม่เมื่อผลเปลี่ยน)"""
        res = position_advisor.latest()
        upd = position_advisor._state.get("updated", 0)
        sig = (tuple(tickets), upd, tuple(t in res for t in tickets))
        if sig == self._advice_sig:
            return
        self._advice_sig = sig
        for w in self.advice_body.winfo_children():
            w.destroy()
        if not tickets:
            self.lbl_advice_meta.configure(text="")
            ctk.CTkLabel(self.advice_body, text="ไม่มีไม้ที่ถืออยู่", font=self._font(11), text_color=COLOR_TEXT_MUTED).pack(pady=8)
            return
        err = position_advisor._state.get("error")
        self.lbl_advice_meta.configure(text=(f"อัปเดต {thai_time.from_epoch(upd)} · ทุก 30 วิ" if upd else "กำลังวิเคราะห์…")
                                       + (f" · {err[:40]}" if err else ""))
        for t in tickets:
            a = res.get(t)
            card = ctk.CTkFrame(self.advice_body, fg_color="#14171E", corner_radius=8)
            card.pack(fill="x", padx=4, pady=3)
            if not a:
                ctk.CTkLabel(card, text=f"#{t} · กำลังวิเคราะห์…", font=self._font(11), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=10, pady=6)
                continue
            fg, bg = self.ADVICE_STYLE[a["verdict"]]
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=10, pady=(6, 0))
            ctk.CTkLabel(top, text=f" {a['verdict_text']} ", font=self._font(12, "bold"), text_color=fg, fg_color=bg,
                         corner_radius=6, height=24).pack(side="left")
            ctk.CTkLabel(top, text=f"  #{t} · {a['side']} · {a['plan'][:22]}", font=self._font(12, "bold"),
                         text_color=COLOR_SUCCESS_GREEN if a["side"] == "BUY" else COLOR_DANGER_RED).pack(side="left")
            pf = a["profit"]
            ctk.CTkLabel(top, text=f"คะแนน {a['score']:+.1f} · กำไร {'+' if pf >= 0 else '-'}{abs(pf):,.2f}", font=self._font(11),
                         text_color=COLOR_TEXT_MUTED).pack(side="right")
            ctk.CTkLabel(card, text=a["advice"], font=self._font(11, "bold"), text_color=fg, anchor="w").pack(fill="x", padx=12, pady=(2, 0))
            for i, r in enumerate(a["reasons"]):
                w = r["w"]
                ptxt, pfg, pbg = status_pill_style(w)
                row = ctk.CTkFrame(card, fg_color="#171B23" if i % 2 == 0 else "transparent", corner_radius=6)
                row.pack(fill="x", padx=8, pady=1)
                ctk.CTkLabel(row, text=ptxt, width=58, font=self._font(10, "bold"), text_color=pfg, fg_color=pbg,
                             corner_radius=6, height=20).pack(side="left", padx=(4, 8), pady=3)
                ctk.CTkLabel(row, text=r["text"], font=self._font(11), text_color=COLOR_TEXT_PRIMARY if w else COLOR_TEXT_MUTED,
                             anchor="w", height=20).pack(side="left", fill="x")
            ctk.CTkFrame(card, fg_color="transparent", height=4).pack()

    def _open_position_detail(self, ticket):
        """หน้าต่างรายละเอียดไม้ (1 หน้าต่างต่อ 1 ไม้ — คลิกซ้ำดึงอันเดิมขึ้นมา)"""
        wins = self.__dict__.setdefault("_pos_detail_wins", {})
        w = wins.get(ticket)
        if w is not None:
            try:
                if w.winfo_exists():
                    w.deiconify(); w.lift(); w.focus_force()
                    return
            except Exception:
                pass
        pos = getattr(self, "_positions_by_ticket", {}).get(ticket)
        if pos:
            wins[ticket] = PositionDetailDialog(self, pos)

    def _on_close_single(self, ticket):
        if not messagebox.askyesno("ยืนยันการปิดออเดอร์", f"ต้องการปิดออเดอร์ #{ticket} ทันทีหรือไม่?"):
            return
        ok, msg = bot_ctrl.close_position_by_ticket(ticket)
        (messagebox.showinfo if ok else messagebox.showwarning)("ผลการปิดออเดอร์", msg)

    # ---- ประวัติการเทรด (5 รายการต่อหน้า) ----
    HISTORY_PAGE_SIZE = 10                      # จำนวนแถวเริ่มต้น — ปรับตามพื้นที่จริงด้วย _fit_history()
    HISTORY_MIN_ROWS, HISTORY_MAX_ROWS = 5, 40
    @staticmethod
    def _close_reason(r):
        """ไม้ปิดด้วยอะไร → (ข้อความ, สี) จาก reason ของ Deal ปิดใน MT5 + คอมเมนต์ที่บอทใส่"""
        code = r.get("close_code", -1)
        cm = str(r.get("close_reason") or "")
        profit = r.get("profit", 0.0)
        if code == 5 or cm.startswith("[tp"):
            return "🎯 ชน TP", COLOR_SUCCESS_GREEN
        if code == 4 or cm.startswith("[sl"):
            # SL ที่ถูกเลื่อนมาล็อกกำไรแล้ว = ปิดกำไร
            return ("🔒 ชน SL (ล็อกกำไร)", COLOR_SUCCESS_GREEN) if profit > 0 else ("⛔ ชน SL", COLOR_DANGER_RED)
        if code == 6 or cm.startswith("[so"):
            return "⚠ Stop Out", COLOR_DANGER_RED
        if code == 3 or cm:
            low = cm.lower()
            if "take profit $" in low:
                return "💰 ถึงเป้ากำไร $", COLOR_SUCCESS_GREEN
            if "manual tp" in low:
                return "🎯 ถึงเป้าจุด (เข้าเอง)", COLOR_SUCCESS_GREEN
            if "vol tp" in low or "volatility tp" in low:
                return "⚡ ปิดช่วงผันผวนแรง", COLOR_SUCCESS_GREEN
            if "cross" in low:
                return "🤖 บอทปิด · MA ตัดกลับ", COLOR_GOLD_PRIMARY
            if "reversal" in low:
                return "🤖 บอทปิด · AI กลับทิศ", COLOR_GOLD_PRIMARY
            if "manual" in low:
                return "✋ ปิดเอง (ในโปรแกรม)", COLOR_CYAN_ACCENT
            if "emergency" in low or "close all" in low:
                return "✋ ปิดทุกออเดอร์", COLOR_CYAN_ACCENT
            if code == 3:
                return "🤖 บอทปิด", COLOR_GOLD_PRIMARY
        if code in (0, 1, 2):
            return "✋ ปิดเอง (MT5)", COLOR_CYAN_ACCENT
        return "ปิดแล้ว", COLOR_TEXT_MUTED

    HISTORY_COLUMNS = [
        ("เวลาเปิด (ไทย)", 96, "w"),
        ("ฝั่ง", 40, "center"),
        ("แผน", 140, "w"),
        ("Lot", 36, "e"),
        ("ราคาเข้า", 72, "e"),
        ("ราคาออก", 72, "e"),
        ("ปิดโดย", 116, "w"),
        ("กำไร", 76, "e"),
    ]

    def _build_history_tab(self, parent):
        self._hist_parent = parent
        self._hist_size = self.HISTORY_PAGE_SIZE
        self._hist_fit_job = None
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=6, pady=(0, 8))
        self.lbl_history_summary = ctk.CTkLabel(top, text="กำลังโหลดประวัติจาก MT5...", font=self._font(12), text_color=COLOR_TEXT_MUTED)
        self.lbl_history_summary.pack(side="left")
        self._refresh_button(top, lambda: self._refresh_history_async(force=True)).pack(side="right")
        ctk.CTkLabel(top, text="คลิกรายการเพื่อดูกราฟ M15 + อินดิเคเตอร์ ณ ตอนปิดไม้", font=self._font(10),
                     text_color=COLOR_TEXT_MUTED).pack(side="right", padx=10)

        # แถบเปลี่ยนหน้าชิดขอบล่าง — พื้นที่ระหว่างตารางกับแถบนี้ใช้เพิ่มจำนวนแถว (ไม่ปล่อยว่าง)
        pager = ctk.CTkFrame(parent, fg_color="transparent")
        pager.pack(side="bottom", fill="x", padx=6, pady=(6, 4))
        self._hist_pager = pager
        self.btn_history_prev = self._small_button(pager, "◀ ใหม่กว่า", lambda: self._change_history_page(-1), width=90)
        self.btn_history_prev.pack(side="left")
        self.lbl_history_page = ctk.CTkLabel(pager, text="หน้า 1 / 1", font=self._font(12, "bold"), text_color=COLOR_TEXT_PRIMARY)
        self.lbl_history_page.pack(side="left", expand=True)
        self.btn_history_next = self._small_button(pager, "เก่ากว่า ▶", lambda: self._change_history_page(1), width=90)
        self.btn_history_next.pack(side="right")

        table = ctk.CTkFrame(parent, fg_color="#101218", corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        table.pack(fill="x", padx=6)
        self._hist_table = table
        for col, (_, width, _) in enumerate(self.HISTORY_COLUMNS):
            table.grid_columnconfigure(col, minsize=width, weight=1 if col == 2 else 0)

        for col, (title, _, anchor) in enumerate(self.HISTORY_COLUMNS):
            ctk.CTkLabel(table, text=f"  {title}  ", font=self._font(11, "bold"), text_color=COLOR_TEXT_MUTED, anchor=anchor).grid(
                row=0, column=col, sticky="ew", padx=(6 if col == 0 else 0, 6 if col == len(self.HISTORY_COLUMNS) - 1 else 0), pady=(10, 6)
            )
        ctk.CTkFrame(table, fg_color=COLOR_CARD_BORDER, height=1).grid(row=1, column=0, columnspan=len(self.HISTORY_COLUMNS), sticky="ew", padx=6)

        # แถวสร้างครั้งเดียวแล้วอัปเดตข้อความ (ลื่นกว่า) · จำนวนแถวที่แสดง = พื้นที่ที่เหลือ (_fit_history)
        self.history_cells = []
        ctk.CTkFrame(table, fg_color="transparent", height=6, width=1).grid(row=999, column=0)   # ระยะขอบล่างของตาราง
        self._ensure_history_rows(self._hist_size)

        self.lbl_history_empty = ctk.CTkLabel(parent, text="", font=self._font(12), text_color=COLOR_TEXT_MUTED, height=20)
        self.lbl_history_empty.pack(pady=(4, 0))
        parent.bind("<Configure>", lambda e: self._schedule_history_fit(), add="+")

    def _ensure_history_rows(self, n):
        """ให้ตารางประวัติแสดง n แถว: สร้างแถวที่ยังไม่มี · ซ่อนแถวเกิน (grid_remove จำตำแหน่งเดิมไว้)"""
        while len(self.history_cells) < n:
            r = len(self.history_cells)
            cells = []
            for col, (_, _, anchor) in enumerate(self.HISTORY_COLUMNS):
                # แถวสลับสีอ่อน/เข้มทั้งแถว (ช่องชิดกัน padx=0 · เว้นขอบด้วยช่องว่างในข้อความ)
                lbl = ctk.CTkLabel(self._hist_table, text="", font=self._font(12), text_color=COLOR_TEXT_PRIMARY, anchor=anchor, height=28,
                                   fg_color="#1A1F29" if r % 2 == 0 else "#101218", corner_radius=0)
                lbl.grid(row=r + 2, column=col, sticky="ew", padx=(6 if col == 0 else 0, 6 if col == len(self.HISTORY_COLUMNS) - 1 else 0))
                lbl.bind("<Button-1>", lambda e, i=r: self._open_history_detail(i), add="+")   # คลิกแถว → กราฟตอนปิดไม้
                try:
                    lbl.configure(cursor="hand2")
                except Exception:
                    pass
                cells.append(lbl)
            self.history_cells.append(cells)
        for r, cells in enumerate(self.history_cells):
            for c in cells:
                if r < n:
                    c.grid()
                else:
                    c.grid_remove()

    def _schedule_history_fit(self):
        if self._hist_fit_job is not None:
            try:
                self.after_cancel(self._hist_fit_job)
            except Exception:
                pass
        self._hist_fit_job = self.after(120, self._fit_history)

    def _fit_history(self):
        """ปรับจำนวนแถวให้เต็มพื้นที่ระหว่างตารางกับแถบเปลี่ยนหน้า (5–40 แถว) — คงไม้แรกของหน้าที่ดูอยู่"""
        self._hist_fit_job = None
        try:
            if not self._hist_parent.winfo_ismapped() or not self.history_cells:
                return
            row_h = self.history_cells[0][0].winfo_height()
            if row_h < 10:
                return
            table_bottom = self._hist_table.winfo_y() + self._hist_table.winfo_reqheight()   # ความสูงที่ต้องการจริง (ตอนล้น Tk จะบีบความสูงที่แสดง)
            empty_h = self.lbl_history_empty.winfo_height() + 4 if self.lbl_history_empty.winfo_ismapped() else 0
            free = self._hist_pager.winfo_y() - table_bottom - empty_h - 8
            n = max(self.HISTORY_MIN_ROWS, min(self.HISTORY_MAX_ROWS, self._hist_size + int(free // row_h)))
        except Exception:
            return
        if n == self._hist_size:
            return
        first = self._history_page * self._hist_size
        self._hist_size = n
        self._ensure_history_rows(n)
        self._history_page = first // n
        self._render_history()
        self._schedule_history_fit()   # ตรวจซ้ำหลังจัดวางใหม่ (ขนาดแถวจริงอาจต่างเล็กน้อย)

    def _refresh_history_async(self, force=False):
        if self._history_loading and not force:
            return
        self._history_loading = True

        def worker():
            rows = bot_ctrl.get_trade_history(days=90)
            self._history_rows = rows
            self._history_dirty = True
            self._history_loading = False

        threading.Thread(target=worker, daemon=True).start()

    def _open_history_detail(self, i):
        """คลิกแถวประวัติ: ไม้ที่ปิดแล้ว → ภาพ ณ ตอนปิด · ไม้ที่ยังเปิดอยู่ → กราฟเรียลไทม์ (1 หน้าต่างต่อ 1 ไม้)"""
        idx = self._history_page * self._hist_size + i
        if idx >= len(self._history_rows):
            return
        r = self._history_rows[idx]
        if r.get("status") != "CLOSED":
            if r["ticket"] not in getattr(self, "_positions_by_ticket", {}):
                self.__dict__.setdefault("_positions_by_ticket", {})[r["ticket"]] = {
                    "ticket": r["ticket"], "type": r.get("side"), "comment": r.get("plan")}
            self._open_position_detail(r["ticket"])
            return
        wins = self.__dict__.setdefault("_pos_detail_wins", {})
        key = ("closed", r["ticket"])
        w = wins.get(key)
        if w is not None:
            try:
                if w.winfo_exists():
                    w.deiconify(); w.lift(); w.focus_force()
                    return
            except Exception:
                pass
        wins[key] = PositionDetailDialog(self, {"ticket": r["ticket"], "type": r.get("side"), "comment": r.get("plan")}, trade=r)

    def _change_history_page(self, delta):
        pages = max(1, -(-len(self._history_rows) // self._hist_size))
        self._history_page = min(max(0, self._history_page + delta), pages - 1)
        self._render_history()

    @staticmethod
    def _fmt_mt5_time(epoch):
        if not epoch:
            return "—"
        return thai_time.from_server(epoch, "%d/%m %H:%M")  # เวลาเซิร์ฟเวอร์ MT5 → เวลาไทย

    def _render_history(self):
        rows = self._history_rows
        total = len(rows)
        pages = max(1, -(-total // self._hist_size))
        self._history_page = min(self._history_page, pages - 1)
        start = self._history_page * self._hist_size
        page_rows = rows[start:start + self._hist_size]

        closed = [r for r in rows if r.get("status") == "CLOSED"]
        wins = sum(1 for r in closed if r["profit"] > 0)
        net = sum(r["profit"] for r in closed)
        open_count = total - len(closed)
        self.lbl_history_summary.configure(
            text=f"90 วันล่าสุด · ปิดแล้ว {len(closed)} ไม้ (ชนะ {wins} / แพ้ {len(closed) - wins})"
            f" · เปิดอยู่ {open_count} · กำไรสุทธิ {'+' if net >= 0 else '-'}{abs(net):,.2f}",
            text_color=COLOR_SUCCESS_GREEN if net > 0 else (COLOR_DANGER_RED if net < 0 else COLOR_TEXT_MUTED),
        )

        for i, cells in enumerate(self.history_cells[:self._hist_size]):
            if i >= len(page_rows):   # แถวว่าง: พื้นเดียวกับตาราง (สลับสีเฉพาะแถวที่มีรายการ)
                for c in cells:
                    c.configure(text="", fg_color="#101218")
                continue
            for c in cells:
                c.configure(fg_color="#1A1F29" if i % 2 == 0 else "#101218")
            r = page_rows[i]
            is_open = r.get("status") != "CLOSED"
            profit = r.get("profit", 0.0)
            values = [
                self._fmt_mt5_time(r.get("open_time")),
                r.get("side", ""),
                (r.get("plan") or "—")[:22],
                f"{r.get('volume', 0):.2f}",
                f"{r.get('open_price', 0):,.2f}",
                "—" if is_open else f"{r.get('close_price', 0):,.2f}",
                "● เปิดอยู่" if is_open else self._close_reason(r)[0],
                f"{'+' if profit >= 0 else '-'}{abs(profit):,.2f}",
            ]
            colors = [
                COLOR_TEXT_MUTED,
                COLOR_SUCCESS_GREEN if r.get("side") == "BUY" else COLOR_DANGER_RED,
                COLOR_TEXT_PRIMARY,
                COLOR_TEXT_PRIMARY,
                COLOR_TEXT_PRIMARY,
                COLOR_TEXT_PRIMARY,
                COLOR_CYAN_ACCENT if is_open else self._close_reason(r)[1],
                COLOR_SUCCESS_GREEN if profit > 0 else (COLOR_DANGER_RED if profit < 0 else COLOR_TEXT_MUTED),
            ]
            values = [f"  {v}  " for v in values]   # ระยะห่างในช่อง (ช่องติดกันเพื่อให้สีพื้นต่อเนื่องทั้งแถว)
            for c, v, color in zip(cells, values, colors):
                c.configure(text=v, text_color=color)

        self.lbl_history_empty.configure(text="" if total else "ยังไม่มีประวัติการเทรด XAUUSD ใน 90 วันที่ผ่านมา")
        if total:   # มีข้อมูล → ซ่อนป้ายว่าง ให้พื้นที่ไปเป็นแถว
            self.lbl_history_empty.pack_forget()
        elif not self.lbl_history_empty.winfo_ismapped():
            self.lbl_history_empty.pack(pady=(4, 0), after=self._hist_table)
        self.lbl_history_page.configure(text=f"หน้า {self._history_page + 1} / {pages}  ·  ทั้งหมด {total} ไม้")
        self.btn_history_prev.configure(state="normal" if self._history_page > 0 else "disabled")
        self.btn_history_next.configure(state="normal" if self._history_page < pages - 1 else "disabled")

    # ---- AI คาดการณ์ทิศทางราคา ----
    def _build_ai_tab(self, parent):
        self._ai_shown_at = None
        self.ai_box = ctk.CTkScrollableFrame(parent, fg_color="#101218", corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        self.ai_box.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        self.ai_box.grid_columnconfigure((0, 1, 2), weight=1, uniform="ai_h")
        ctk.CTkLabel(self.ai_box, text="กำลังวิเคราะห์ข้อมูล... (ครั้งแรกประมาณ 15 วินาที)", font=self._font(12),
                     text_color=COLOR_TEXT_MUTED).grid(row=0, column=0, columnspan=3, pady=30)
        ai_outlook.start_background()

    def _render_ai_outlook(self):
        r = ai_outlook.latest()
        if not r or r["updated_at"] == self._ai_shown_at:
            return
        self._ai_shown_at = r["updated_at"]
        box = self.ai_box
        for w in box.winfo_children():
            w.destroy()
        green, red, gold, muted = COLOR_SUCCESS_GREEN, COLOR_DANGER_RED, COLOR_GOLD_PRIMARY, COLOR_TEXT_MUTED
        tone = lambda d: green if d > 0 else red if d < 0 else gold
        dark = lambda d: "#0F2A20" if d > 0 else "#2A1215" if d < 0 else "#2A2210"
        main = r["horizons"][-1]
        md = main["direction"]

        # ── 1) แถบสรุปหลัก (Hero)
        hero = ctk.CTkFrame(box, fg_color=dark(md), corner_radius=14, border_width=1, border_color=tone(md))
        hero.grid(row=0, column=0, columnspan=3, sticky="ew", padx=4, pady=(6, 8))
        hero.grid_columnconfigure(1, weight=1)
        badge = tk.Canvas(hero, width=56, height=56, bg=dark(md), highlightthickness=0, bd=0)
        badge.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=14)
        badge.create_oval(2, 2, 54, 54, fill=tone(md), outline="")
        if md > 0:
            badge.create_polygon(28, 13, 42, 33, 14, 33, fill="#0A0B0F", outline="")
        elif md < 0:
            badge.create_polygon(14, 22, 42, 22, 28, 42, fill="#0A0B0F", outline="")
        else:
            badge.create_rectangle(15, 25, 41, 31, fill="#0A0B0F", outline="")
        head = "ทองมีแนวโน้มขึ้น" if md > 0 else "ทองมีแนวโน้มลง" if md < 0 else "ยังไม่มีทิศชัดเจน"
        ctk.CTkLabel(hero, text=head, font=self._font(20, "bold"), text_color=tone(md), anchor="w").grid(row=0, column=1, sticky="sw", pady=(14, 0))
        sub = f"มุมมอง 1 วัน · AI {main['confidence']:.0f}%" + (" · เทรนด์ยืนยัน" if main["trend_agree"] and md else "") + \
              f" · แม่นในอดีต {main['hist_acc']:.0f}%"
        ctk.CTkLabel(hero, text=sub, font=self._font(12), text_color=COLOR_TEXT_PRIMARY, anchor="w").grid(row=1, column=1, sticky="nw", pady=(0, 14))
        upd = econ_calendar.datetime.fromisoformat(r["updated_at"]).astimezone(econ_calendar.BANGKOK)
        # ภาพรวมเสียงปัจจัยทั้งหมด (ย้ายจากการ์ดปัจจัยมาไว้ในแถบสรุป — ผู้ใช้ขอ 8 ต.ค. 2026)
        allf = r["factors"]
        n_up = sum(1 for f in allf if f["dir"] > 0)
        n_dn = sum(1 for f in allf if f["dir"] < 0)
        n_mid = len(allf) - n_up - n_dn
        if n_up > n_dn and n_up >= n_mid:
            verdict, vcol = f"ส่วนใหญ่ชี้ขึ้น {n_up}/{len(allf)}", green
        elif n_dn > n_up and n_dn >= n_mid:
            verdict, vcol = f"ส่วนใหญ่ชี้ลง {n_dn}/{len(allf)}", red
        else:
            verdict, vcol = "ปัจจัยยังขัดกัน", gold
        vote = ctk.CTkFrame(hero, fg_color="#101218", corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER, width=300)
        vote.grid(row=0, column=2, rowspan=2, sticky="ns", padx=(8, 0), pady=10)
        vh = ctk.CTkFrame(vote, fg_color="transparent")
        vh.pack(fill="x", padx=12, pady=(8, 0))
        ctk.CTkLabel(vh, text=f"ปัจจัยทั้งหมด {len(allf)} ตัว", font=self._font(10, "bold"), text_color=muted, height=16).pack(side="left")
        ctk.CTkLabel(vh, text=verdict, font=self._font(13, "bold"), text_color=vcol, height=18).pack(side="right", padx=(16, 0))
        vb = tk.Canvas(vote, width=276, height=12, bg="#101218", highlightthickness=0, bd=0)
        vb.pack(fill="x", padx=12, pady=(5, 0))

        def draw_votes(e, b=vb, u=n_up, dn=n_dn, m=n_mid):
            b.delete("all")
            w, tot = max(e.width, 20), max(u + dn + m, 1)
            x = 0
            for n, col_ in ((u, green), (m, "#3A4150"), (dn, red)):
                if n:
                    b.create_rectangle(x, 1, x + w * n / tot, 11, fill=col_, outline="#101218", width=2)
                    x += w * n / tot
        vb.bind("<Configure>", draw_votes)
        lg = ctk.CTkFrame(vote, fg_color="transparent")
        lg.pack(fill="x", padx=12, pady=(3, 8))
        for txt, col_ in ((f"▲ ขึ้น {n_up}", green), (f"• กลาง {n_mid}", muted), (f"▼ ลง {n_dn}", red)):
            ctk.CTkLabel(lg, text=txt, font=self._font(10, "bold"), text_color=col_, height=16).pack(side="left", padx=(0, 12))
        HoverTip(vote, lambda: "นับเสียงอย่างเดียว ไม่ได้ถ่วงน้ำหนัก · ใช้ประกอบกับ AI")
        right = ctk.CTkFrame(hero, fg_color="transparent")
        right.grid(row=0, column=3, rowspan=2, padx=16)
        ctk.CTkLabel(right, text=f"{r['price']:,.2f}", font=self._font(20, "bold", app_fonts.MONO), text_color=COLOR_TEXT_PRIMARY).pack(anchor="e")
        ctk.CTkLabel(right, text=f"อัปเดต {upd.strftime('%H:%M')} น. · ทุก 1 นาที", font=self._font(10), text_color=muted).pack(anchor="e")

        # ── 2) การ์ด 3 ช่วงเวลา (ดีไซน์ใหม่ 8 ต.ค. 2026: ไม่ชัด = สีเทาล้วน · แถบมีเข็ม + ขีดเกณฑ์ 45/55%)
        for col, h in enumerate(r["horizons"]):
            d = h["direction"]
            lean = h["lean"]
            pu = h["p_up"]
            pct = pu * 100 if lean > 0 else (1 - pu) * 100
            c = ctk.CTkFrame(box, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1,
                             border_color=tone(d) if d else COLOR_CARD_BORDER)
            c.grid(row=1, column=col, sticky="nsew", padx=4, pady=4)
            top = ctk.CTkFrame(c, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(12, 0))
            ctk.CTkLabel(top, text=f"อีก {h['label']}", font=self._font(13, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
            # ไม่มีป้ายสถานะมุมขวา — สถานะแสดงที่ตัวใหญ่ด้านล่างแล้ว (ผู้ใช้ไม่ต้องการแสดงซ้ำ)
            if d:
                ctk.CTkLabel(c, text=f"{'▲ ขึ้น' if d > 0 else '▼ ลง'} {pct:.0f}%", font=self._font(24, "bold"), text_color=tone(d), height=30
                             ).pack(anchor="w", padx=14, pady=(2, 0))
                ctk.CTkLabel(c, text=f"AI มั่นใจเกินเกณฑ์ 55% · โอกาส{'ขึ้น' if d > 0 else 'ลง'}", font=self._font(11),
                             text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=14)
            else:
                ctk.CTkLabel(c, text="ยังไม่ชัด", font=self._font(20, "bold"), text_color=muted, height=28).pack(anchor="w", padx=14, pady=(2, 0))
                ctk.CTkLabel(c, text=f"เอียง{'ขึ้น' if lean > 0 else 'ลง'} {pct:.0f}% · ต้องถึง 55% จึงนับเป็นสัญญาณ",
                             font=self._font(11), text_color=muted).pack(anchor="w", padx=14)
            bar = tk.Canvas(c, height=24, bg=COLOR_CARD_BG, highlightthickness=0, bd=0)
            bar.pack(fill="x", padx=14, pady=(6, 0))

            def draw(e, b=bar, up=pu, clear=d):
                b.delete("all")
                w = max(e.width, 40)
                x0, x1, y = 6, w - 6, 13
                xp = lambda v: x0 + v * (x1 - x0)
                b.create_line(x0, y, x1, y, fill="#3A2226" if not clear else red, width=8, capstyle="round")
                gcol = "#1E3B30" if not clear else green
                # ปลายฝั่งขวาตัดตรง (butt) ให้รอยต่อเขียว/แดงตรงกับปลายเข็มพอดี — ปลายมนเดิมยื่นเกินไป 4px
                b.create_oval(x0 - 4, y - 4, x0 + 4, y + 4, fill=gcol, outline="")
                b.create_line(x0, y, xp(up), y, fill=gcol, width=8, capstyle="butt")
                for v in (0.45, 0.55):   # เกณฑ์สัญญาณ
                    b.create_line(xp(v), y - 8, xp(v), y + 8, fill=COLOR_GOLD_PRIMARY, width=1, dash=(2, 2))
                b.create_line(xp(0.5), y - 6, xp(0.5), y + 6, fill="#6E7687", width=1)
                xm = xp(up)   # เข็ม
                b.create_polygon(xm - 6, y - 12, xm + 6, y - 12, xm, y - 4, fill=COLOR_TEXT_PRIMARY, outline="")
            bar.bind("<Configure>", draw)
            leg = ctk.CTkFrame(c, fg_color="transparent")
            leg.pack(fill="x", padx=14, pady=(2, 0))
            ctk.CTkLabel(leg, text=f"ขึ้น {pu * 100:.0f}%", font=self._font(10, "bold"), text_color=green, height=16).pack(side="left")
            ctk.CTkLabel(leg, text=f"ลง {(1 - pu) * 100:.0f}%", font=self._font(10, "bold"), text_color=red, height=16).pack(side="right")
            foot = ctk.CTkFrame(c, fg_color="transparent")
            foot.pack(fill="x", padx=12, pady=(6, 10))
            ctk.CTkLabel(foot, text=f" แม่นในอดีต {h['hist_acc']:.0f}% ", font=self._font(10, "bold"), corner_radius=6, height=20,
                         fg_color="#101218", text_color=COLOR_TEXT_PRIMARY).pack(side="left")
            if d:
                ok = h["trend_agree"]
                ctk.CTkLabel(foot, text=" ✓ เทรนด์ยืนยัน " if ok else " เทรนด์ไม่ยืนยัน ", font=self._font(10, "bold"), corner_radius=6,
                             height=20, fg_color="#0F2A20" if ok else "#2A2210", text_color=green if ok else gold).pack(side="right")

        # ── 3) ปัจจัยที่นำมาวิเคราะห์ — 2 การ์ด: ปัจจัยหลักของบอท | อินดิเคเตอร์ยอดนิยม (แสดงประกอบ)
        core_keys = ("เทรนด์", "ราคาเทียบ", "โมเมนตัม", "แนวรับ")
        groups = (("ปัจจัยหลักของบอท", "ใช้คิดเทรนด์ยืนยันและคำแนะนำถือ/ปิดไม้", [f for f in r["factors"] if f["name"].startswith(core_keys)]),
                  ("อินดิเคเตอร์ยอดนิยม", "นักเทรดนิยมใช้ · แสดงประกอบ", [f for f in r["factors"] if not f["name"].startswith(core_keys)]))
        pair = ctk.CTkFrame(box, fg_color="transparent")
        pair.grid(row=2, column=0, columnspan=3, sticky="ew", padx=0, pady=(8, 4))
        pair.grid_columnconfigure((0, 1), weight=1, uniform="fac")
        for gi, (title, sub, items) in enumerate(groups):
            fac = ctk.CTkFrame(pair, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
            fac.grid(row=0, column=gi, sticky="nsew", padx=4)
            ups = sum(1 for f in items if f["dir"] > 0)
            dns = sum(1 for f in items if f["dir"] < 0)
            mids = len(items) - ups - dns
            fh = ctk.CTkFrame(fac, fg_color="transparent")
            fh.pack(fill="x", padx=12, pady=(10, 0))
            ctk.CTkLabel(fh, text=title, font=self._font(13, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
            for txt, n, col_ in (("กลาง", mids, muted), ("ลง", dns, red), ("ขึ้น", ups, green)):  # pack ขวา → เรียงกลับ
                ctk.CTkLabel(fh, text=f" {txt} {n} ", font=self._font(10, "bold"), corner_radius=6, height=20,
                             fg_color="#101218", text_color=col_).pack(side="right", padx=(4, 0))
            ctk.CTkLabel(fac, text=sub, font=self._font(10), text_color=muted, anchor="w").pack(fill="x", padx=12, pady=(0, 6))
            # การ์ดอินดิเคเตอร์ยอดนิยมมีหลายรายการ → แบ่ง 2 คอลัมน์ (ผู้ใช้ขอ 8 ต.ค. 2026)
            ncol = 2 if gi == 1 else 1
            grid_f = ctk.CTkFrame(fac, fg_color="transparent")
            grid_f.pack(fill="x", padx=8)
            for cc in range(ncol):
                grid_f.grid_columnconfigure(cc, weight=1, uniform="fc")
            for i, f in enumerate(items):
                d = f["dir"]
                ri, ci = divmod(i, ncol)
                rowf = ctk.CTkFrame(grid_f, fg_color="#171B23" if ri % 2 == 0 else "transparent", corner_radius=8)
                rowf.grid(row=ri, column=ci, sticky="nsew", padx=(0, 4) if ncol > 1 and ci == 0 else 0, pady=1)
                ctk.CTkLabel(rowf, text=" ▲ ขึ้น " if d > 0 else " ▼ ลง " if d < 0 else " • กลาง ", font=self._font(10, "bold"),
                             width=58, corner_radius=6, height=20, fg_color=dark(d) if d else "#262B36",
                             text_color=tone(d) if d else muted).pack(side="left", padx=(6, 8), pady=4, anchor="n")
                txtf = ctk.CTkFrame(rowf, fg_color="transparent")
                txtf.pack(side="left", fill="x", expand=True, pady=2)
                ctk.CTkLabel(txtf, text=f["name"], font=self._font(12, "bold"), text_color=COLOR_TEXT_PRIMARY, anchor="w", height=18).pack(fill="x")
                ctk.CTkLabel(txtf, text=f["detail"], font=self._font(10), text_color=muted, anchor="w", justify="left",
                             wraplength=300 if ncol == 1 else 200, height=16).pack(fill="x")
            ctk.CTkFrame(fac, height=8, fg_color="transparent").pack()

        row = 3
        if r["news"]:
            nf = ctk.CTkFrame(box, fg_color="#2A2210", corner_radius=12, border_width=1, border_color="#7A5A1C")
            nf.grid(row=row, column=0, columnspan=3, sticky="ew", padx=4, pady=4)
            ctk.CTkLabel(nf, text="ข่าว USD ผลกระทบสูงใน 24 ชม. — ราคาอาจสะบัดแรงทั้งสองทาง", font=self._font(12, "bold"),
                         text_color=gold).pack(anchor="w", padx=14, pady=(10, 4))
            for n in r["news"]:
                lean = " · ▲ แนวโน้มทองขึ้น" if n["lean"] > 0 else " · ▼ แนวโน้มทองลง" if n["lean"] < 0 else ""
                th = f" ({n['title_th']})" if n.get("title_th") else ""
                ctk.CTkLabel(nf, text=f"{n['time']} น.  {n['title']}{th}{lean}", font=self._font(11), text_color=COLOR_TEXT_PRIMARY,
                             anchor="w", justify="left", wraplength=620).pack(anchor="w", padx=14)
            ctk.CTkFrame(nf, height=8, fg_color="transparent").pack()
            row += 1
        ctk.CTkLabel(box, text=r["note"], font=self._font(10), text_color=muted, wraplength=640, justify="left"
                     ).grid(row=row, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 8))

    # ---- ปฏิทินเศรษฐกิจ ----
    IMPACT_COLORS = {"High": "#F87171", "Medium": "#FB923C", "Low": "#A3ABBA", "Holiday": "#6E7687"}
    IMPACT_TH = {"High": "สูง", "Medium": "กลาง", "Low": "ต่ำ", "Holiday": "วันหยุด"}

    def _build_calendar_tab(self, parent):
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", padx=6, pady=(0, 8))

        self.cal_currency = ctk.CTkSegmentedButton(
            bar,
            values=["USD (มีผลต่อทอง)", "ทุกสกุลเงิน"],
            font=self._font(12),
            selected_color=COLOR_GOLD_WARM,
            selected_hover_color=COLOR_GOLD_DARK,
            unselected_color="#1A1E27",
            unselected_hover_color="#262B36",
            command=lambda _v: self._render_calendar(),
        )
        self.cal_currency.set("USD (มีผลต่อทอง)")
        self.cal_currency.pack(side="left")

        self.cal_impact = ctk.CTkSegmentedButton(
            bar,
            values=["สูง", "กลาง+สูง", "ทั้งหมด"],
            font=self._font(12),
            selected_color=COLOR_GOLD_WARM,
            selected_hover_color=COLOR_GOLD_DARK,
            unselected_color="#1A1E27",
            unselected_hover_color="#262B36",
            command=lambda _v: self._render_calendar(),
        )
        self.cal_impact.set("กลาง+สูง")
        self.cal_impact.pack(side="left", padx=10)

        self._small_button(bar, "🌐 Investing.com", lambda: webbrowser.open(econ_calendar.INVESTING_URL), width=120).pack(side="right")
        self._refresh_button(bar, lambda: self._refresh_calendar_async(force=True)).pack(side="right", padx=(0, 8))

        self.cal_list = ctk.CTkScrollableFrame(parent, fg_color="#101218", corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        self.cal_list.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        self.cal_list.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            parent,
            text="เวลาไทย (UTC+7) · อัปเดตทุก 30 นาที · คอลัมน์ขวา = ผลต่อทอง (แนวโน้มจากตัวเลขคาด · ±% ที่ทองมักขยับใน 1 ชม.) — คลิกข่าวเพื่อดูรายละเอียด",
            font=self._font(10),
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=8)

    def _refresh_calendar_async(self, force=False):
        if self._calendar_loading:
            return
        self._calendar_loading = True

        def worker():
            self._calendar_events = econ_calendar.fetch_events(force=force)
            # วิเคราะห์ผลกระทบข่าว USD ต่อทอง (ใช้ข้อมูล MT5 — ทำในเธรดเบื้องหลัง)
            analyses = {}
            for ev in self._calendar_events:
                if ev["currency"] == "USD" and ev["impact"] in ("High", "Medium"):
                    try:
                        analyses[(ev["title"], ev["time"])] = news_impact.analyze(ev)
                    except Exception:
                        pass
            self._news_analysis = analyses
            news_impact.publish(self._calendar_events, analyses)  # ส่งชุดเดียวกันขึ้นเว็บผ่าน Telemetry
            self._calendar_dirty = True
            self._calendar_loading = False

        threading.Thread(target=worker, daemon=True).start()

    def _render_calendar(self):
        for w in self.cal_list.winfo_children():
            w.destroy()

        usd_only = self.cal_currency.get().startswith("USD")
        impact = {"สูง": "High", "กลาง+สูง": "Medium", "ทั้งหมด": "Low"}[self.cal_impact.get()]
        events = econ_calendar.filter_events(self._calendar_events, usd_only=usd_only, min_impact=impact)

        if not events:
            msg = econ_calendar.last_error() and "โหลดปฏิทินข่าวไม่สำเร็จ — ตรวจสอบอินเทอร์เน็ตแล้วกด 🔄" or "ไม่มีข่าวตามตัวกรองในสัปดาห์นี้"
            ctk.CTkLabel(self.cal_list, text=msg, font=self._font(12), text_color=COLOR_TEXT_MUTED).grid(row=0, column=0, columnspan=6, pady=30)
            return

        now = econ_calendar.datetime.now(econ_calendar.BANGKOK)
        row = 0
        current_day = None
        for idx, ev in enumerate(events):
            day = econ_calendar.format_day(ev["time"])
            if day != current_day:
                current_day = day
                is_today = ev["time"].date() == now.date()
                ctk.CTkLabel(
                    self.cal_list,
                    text=f"{day}{'  · วันนี้' if is_today else ''}",
                    font=self._font(12, "bold"),
                    text_color=COLOR_GOLD_PRIMARY if is_today else COLOR_TEXT_PRIMARY,
                    anchor="w",
                ).grid(row=row, column=0, columnspan=6, sticky="ew", padx=10, pady=(10, 2))
                row += 1

            past = ev["time"] < now
            fg = COLOR_TEXT_MUTED if past else COLOR_TEXT_PRIMARY
            # พื้นสลับสีอ่อน/เข้มทีละรายการ (แถบเต็มแถวอยู่หลังช่องข้อความ)
            bg = "#1A1F29" if idx % 2 == 0 else "transparent"
            if idx % 2 == 0:
                ctk.CTkFrame(self.cal_list, fg_color=bg, corner_radius=6, height=28).grid(row=row, column=0, columnspan=7, sticky="nsew", padx=4)
            ctk.CTkLabel(self.cal_list, text=ev["time"].strftime("%H:%M"), font=self._font(12, "bold"), text_color=fg, fg_color=bg, width=48, anchor="w").grid(row=row, column=0, padx=(12, 4), sticky="w")
            ctk.CTkLabel(self.cal_list, text=ev["currency"], font=self._font(11, "bold"), text_color=fg, fg_color=bg, width=36).grid(row=row, column=1, padx=4)
            ctk.CTkLabel(
                self.cal_list,
                text=self.IMPACT_TH.get(ev["impact"], ev["impact"]),
                font=self._font(10, "bold"),
                text_color="#101218",
                fg_color=self.IMPACT_COLORS.get(ev["impact"], "#A3ABBA"),
                corner_radius=6,
                width=48,
                height=20,
            ).grid(row=row, column=2, padx=4, pady=3)
            a = getattr(self, "_news_analysis", {}).get((ev["title"], ev["time"]))
            title_lbl = ctk.CTkLabel(self.cal_list, text=ev["title"], font=self._font(12), text_color=fg, fg_color=bg, anchor="w")
            title_lbl.grid(row=row, column=3, sticky="ew", padx=6)
            th = news_th.translate(ev["title"])
            if th:
                HoverTip(title_lbl, th)
            if a:
                txt, tone = news_impact.short_text(a)
                col = {"up": COLOR_SUCCESS_GREEN, "down": COLOR_DANGER_RED}.get(tone, COLOR_TEXT_MUTED)
                imp_lbl = ctk.CTkLabel(self.cal_list, text=txt + "  ›", font=self._font(11, "bold"), text_color=col, fg_color=bg, width=128, anchor="e")
                imp_lbl.grid(row=row, column=6, padx=(4, 12))
                open_detail = lambda e, ev=ev, a=a: NewsImpactDialog(self, ev, a, self._last_gold_price())
                for w in (title_lbl, imp_lbl):
                    w.configure(cursor="hand2")
                    w.bind("<Button-1>", open_detail)
            ctk.CTkLabel(self.cal_list, text=f"คาด {ev['forecast'] or '—'}", font=self._font(11), text_color=COLOR_TEXT_MUTED, fg_color=bg, width=80, anchor="e").grid(row=row, column=4, padx=4)
            ctk.CTkLabel(self.cal_list, text=f"ก่อน {ev['previous'] or '—'}", font=self._font(11), text_color=COLOR_TEXT_MUTED, fg_color=bg, width=84, anchor="e").grid(row=row, column=5, padx=4)
            row += 1

    def _last_gold_price(self) -> float:
        try:
            import MetaTrader5 as _mt5
            t = _mt5.symbol_info_tick("XAUUSD")
            return float(t.bid) if t else 0.0
        except Exception:
            return 0.0

    def _render_next_news(self):
        """ข้อความวิ่ง: ข่าว USD ผลกระทบสูงถัดไปสูงสุด 3 ข่าว + วัน/เวลา (ไทย) + นับถอยหลัง · เหลือไม่ถึง 1 ชม. เป็นสีแดง"""
        if not hasattr(self, "_mq"):
            return
        now = econ_calendar.datetime.now(econ_calendar.BANGKOK)
        evs = [e for e in (self._calendar_events or []) if e["currency"] == "USD" and e["impact"] == "High"
               and e["time"] > now - econ_calendar.timedelta(minutes=5)][:3]
        if not evs:
            text = "ไม่มีข่าว USD ผลกระทบสูงในสัปดาห์นี้" if self._calendar_events else "กำลังโหลดปฏิทินข่าว..."
            color = COLOR_TEXT_MUTED
        else:
            parts = [f"{e['title']} · {econ_calendar.format_day(e['time'])} {e['time'].strftime('%H:%M')} น. · {econ_calendar.format_countdown(e['time'])}"
                     for e in evs]
            text = "        ◆        ".join(parts)
            color = COLOR_DANGER_RED if (evs[0]["time"] - now).total_seconds() < 3600 else COLOR_GOLD_PRIMARY
        if self._mq.itemcget(self._mq_item, "text") != text:
            self._mq.itemconfigure(self._mq_item, text=text)
        self._mq.itemconfigure(self._mq_item, fill=color)

    # =========================================================================
    # 3. การควบคุมบอท และเหตุการณ์ต่างๆ (BOT ACTIONS & EVENTS)
    # =========================================================================
    # ---------------------------------------------------------------------
    # การนับถอยหลัง 20 วินาทีเพื่อเริ่มการทำงานบอทอัตโนมัติเมื่อเปิดโปรแกรมครั้งแรก
    # ---------------------------------------------------------------------
    def _start_autostart_countdown(self, seconds=20):
        """นับถอยหลังเมื่อเปิดโปรแกรมครั้งแรก เพื่อเริ่มการทำงานบอทอัตโนมัติ"""
        if bot_ctrl.is_active:
            return
        self._cancel_autostart_countdown()
        self._autostart_seconds_left = seconds
        self._autostart_tick()

    def _autostart_tick(self):
        """ทิกเกอร์นับถอยหลังทุก 1 วินาที"""
        self._autostart_timer_id = None
        if not hasattr(self, "btn_master_toggle") or bot_ctrl.is_active:
            self._cancel_autostart_countdown()
            return

        if getattr(self, "_autostart_seconds_left", 0) > 0:
            secs = self._autostart_seconds_left
            self.btn_master_toggle.configure(
                text=f"▶  เริ่มการทำงานบอท ({secs}s)",
                fg_color=COLOR_SUCCESS_GREEN,
                hover_color="#10A374",
                text_color="#06281C",
            )
            if hasattr(self, "lbl_bot_state") and not bot_ctrl.is_active:
                self.lbl_bot_state.configure(
                    text=f"  ⏳ เริ่มอัตโนมัติ {secs}s  ",
                    text_color=COLOR_GOLD_PRIMARY,
                    fg_color="#2E2410",
                )
            self._autostart_seconds_left -= 1
            self._autostart_timer_id = self.after(1000, self._autostart_tick)
        else:
            # ครบ 20 วินาที → เริ่มการทำงานบอทอัตโนมัติ
            self._cancel_autostart_countdown()
            if not bot_ctrl.is_active:
                self._on_toggle_bot()

    def _cancel_autostart_countdown(self):
        """ยกเลิกตัวจับเวลานับถอยหลัง"""
        tid = getattr(self, "_autostart_timer_id", None)
        if tid is not None:
            try:
                self.after_cancel(tid)
            except Exception:
                pass
            self._autostart_timer_id = None
        self._autostart_seconds_left = 0

    def _cancel_autostart_manual(self, _e=None):
        """ผู้ใช้กดยกเลิกการเริ่มบอทอัตโนมัติ (คลิกที่ป้ายสถานะ)"""
        if getattr(self, "_autostart_seconds_left", 0) > 0:
            self._cancel_autostart_countdown()
            if hasattr(self, "btn_master_toggle") and not bot_ctrl.is_active:
                self.btn_master_toggle.configure(
                    text="▶  เริ่มการทำงานบอท",
                    fg_color=COLOR_SUCCESS_GREEN,
                    hover_color="#10A374",
                    text_color="#06281C",
                )
            if hasattr(self, "lbl_bot_state") and not bot_ctrl.is_active:
                self.lbl_bot_state.configure(
                    text="  ● หยุดทำงาน  ",
                    text_color=COLOR_TEXT_MUTED,
                    fg_color="#1F2430",
                )

    def _on_toggle_bot(self):
        """กดปุ่ม Start/Pause บอท"""
        self._cancel_autostart_countdown()
        if not license_mgr.is_authenticated:
            messagebox.showwarning("ยังไม่ได้เข้าสู่ระบบ", "กรุณาเข้าสู่ระบบก่อนเริ่มต้นใช้งานบอท")
            self.show_login_view()
            return

        if not license_mgr.has_active_hours():
            sound_manager.play_sl_hit()
            messagebox.showwarning(
                "ชั่วโมงการใช้งานหมด", 
                "เวลาใช้งานของท่านหมดแล้ว (0.00 ชม.)\n"
                "กรุณาเติมชั่วโมงด้วย Product Key เพื่อเริ่มต้นใช้งาน"
            )
            self._open_redeem_modal()
            return

        if not bot_ctrl.is_active:
            # เริ่มต้นบอท
            success, msg = bot_ctrl.start_bot()
            if success:
                license_mgr.track_event("bot_start")
                mkt = thai_time.get_gold_market_status()
                if not mkt["is_open"]:
                    self._append_console(self._console_formatter.feed(
                        f"[MARKET] {mkt['headline']} — {mkt['subtext']} (ระบบสแตนด์บายอัตโนมัติ ไม่หักชั่วโมงใช้งาน)\n"
                    ))
            else:
                messagebox.showwarning("ไม่สามารถเริ่มบอทได้", msg)
        elif bot_ctrl.is_paused:
            # กลับมาทำงานต่อ
            success, msg = bot_ctrl.resume_bot()
            if not success:
                messagebox.showwarning("ไม่สามารถดำเนินการได้", msg)
        else:
            # หยุดชั่วคราว
            bot_ctrl.pause_bot()
            license_mgr.track_event("bot_stop")

    def _on_bot_status_changed(self, status: str):
        """อัปเดตปุ่มหลักและป้ายสถานะเมื่อสถานะบอทเปลี่ยน"""
        if not hasattr(self, "btn_master_toggle"):
            return
        if status == "RUNNING":
            self._bot_started_at = self._bot_started_at or time.time()
            self.btn_master_toggle.configure(text="⏸  หยุดชั่วคราว", fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK, text_color="#1A1406")
            self.lbl_metering_status.configure(text="● กำลังนับเวลา", text_color=COLOR_SUCCESS_GREEN)
            self.lbl_bot_state.configure(text="  ● กำลังทำงาน  ", text_color=COLOR_SUCCESS_GREEN, fg_color="#12301F")
        elif status == "PAUSED":
            self.btn_master_toggle.configure(text="▶  ทำงานต่อ", fg_color=COLOR_SUCCESS_GREEN, hover_color="#10A374", text_color="#06281C")
            self.lbl_metering_status.configure(text="⏸ หยุดนับเวลา", text_color=COLOR_TEXT_MUTED)
            self.lbl_bot_state.configure(text="  ⏸ หยุดชั่วคราว  ", text_color=COLOR_GOLD_PRIMARY, fg_color="#2E2410")
        else:  # STOPPED
            self._bot_started_at = None
            self.btn_master_toggle.configure(text="▶  เริ่มการทำงานบอท", fg_color=COLOR_SUCCESS_GREEN, hover_color="#10A374", text_color="#06281C")
            self.lbl_metering_status.configure(text="⏸ หยุดนับเวลา", text_color=COLOR_TEXT_MUTED)
            self.lbl_bot_state.configure(text="  ● หยุดทำงาน  ", text_color=COLOR_TEXT_MUTED, fg_color="#1F2430")

    ONLINE_GOAL_HOURS = 100   # ค่าเดียวกับเว็บ web/src/lib/onlineReward.js

    def _update_reward(self, low=False):
        """ป้ายรางวัลออนไลน์ในกระเป๋าเวลา: ความคืบหน้ารอบปัจจุบัน หรือส่วนลดที่ได้รับ"""
        if not hasattr(self, "reward_box"):
            return
        o = license_mgr.online_status()
        key = (None if not o else (o["minutes"], bool(o.get("discount"))), low)
        if key == self._reward_shown:
            return
        self._reward_shown = key
        if not o:
            self.reward_box.pack_forget()
            return
        if not self.reward_box.winfo_ismapped():
            self.reward_box.pack(side="left", padx=(0, 12), before=self.reward_box.master.winfo_children()[-1])
        goal = max(1, int(o.get("goalMinutes") or self.ONLINE_GOAL_HOURS * 60))
        d = o.get("discount")
        bg = "#2A1518" if low else COLOR_GOLD_BG
        cv = self.cv_reward
        cv.configure(bg=bg)
        cv.delete("all")
        cv.create_rectangle(0, 0, 118, 6, fill="#3A3220", outline="")
        frac = min(1.0, o["minutes"] / goal)
        cv.create_rectangle(0, 0, 118 * frac, 6, fill=COLOR_SUCCESS_GREEN if frac >= 1 else COLOR_GOLD_PRIMARY, outline="")
        if d:
            self.lbl_reward.configure(text=f"ส่วนลด {d['percent']}% พร้อมใช้ ›", text_color=COLOR_SUCCESS_GREEN)
        else:
            self.lbl_reward.configure(text=f"ออนไลน์ {o['minutes'] / 60:.1f}/{goal // 60} ชม.", text_color=COLOR_GOLD_PRIMARY)

    def _reward_tip(self):
        o = license_mgr.online_status()
        if not o:
            return ""
        goal = int(o.get("goalMinutes") or self.ONLINE_GOAL_HOURS * 60) // 60
        tip = (f"ออนไลน์ครบ {goal} ชม. รับส่วนลด 10% ซื้อชั่วโมงครั้งถัดไป 1 รายการ\n"
               f"นับเฉพาะเวลาที่บอททำงานและถูกหักชั่วโมง · รอบปัจจุบัน {o['minutes'] / 60:.1f} ชม.")
        d = o.get("discount")
        if d:
            try:
                from datetime import datetime
                exp = thai_time.from_epoch(datetime.fromisoformat(str(d["expiresAt"]).replace("Z", "+00:00")).timestamp(), "%d/%m %H:%M")
            except Exception:
                exp = "-"
            tip += f"\nมีส่วนลด {d['percent']}% ใช้ได้ถึง {exp} น. (ภายใน 3 วัน) — คลิกเพื่อซื้อชั่วโมง\nเมื่อได้รับส่วนลดแล้ว ระบบจะเริ่มนับชั่วโมงใหม่ทันที"
        return tip

    def _check_low_hours_alert(self, mins_left):
        """เตือนเวลาใกล้หมด: หน้าต่าง + เสียง + Console ครั้งเดียวต่อเกณฑ์ (เติมชั่วโมงจนเกินเกณฑ์แล้วจะเตือนใหม่ได้)"""
        warned = getattr(self, "_low_hours_warned", None)
        if warned is None:
            warned = self._low_hours_warned = set()
        for th in self.LOW_HOURS_ALERTS:
            if mins_left > th:
                warned.discard(th)
        if mins_left <= 0 or getattr(self, "_low_hours_dialog_open", False):
            return
        due = [th for th in self.LOW_HOURS_ALERTS if mins_left <= th and th not in warned]
        if not due:
            return
        warned.update(due)   # เกณฑ์ที่ผ่านมาแล้วทั้งหมดนับว่าเตือนแล้ว (เปิดโปรแกรมตอนเหลือ 40 นาที เตือนครั้งเดียว)
        h, m = divmod(int(mins_left), 60)
        left = f"{h} ชม. {m:02d} นาที" if h else f"{m} นาที"
        print(f"[LICENSE] เวลาใช้งานใกล้หมด — เหลือ {left} เมื่อหมดบอทจะหยุดอัตโนมัติ")
        self.after(50, lambda: self._show_low_hours_dialog(left))

    def _show_low_hours_dialog(self, left):
        self._low_hours_dialog_open = True
        try:
            sound_manager.play_sl_hit()
            buy = messagebox._run(
                "เวลาใช้งานใกล้หมด",
                f"ชั่วโมงใช้งานเหลือ {left}\n"
                "เมื่อหมดบอทจะหยุดเอง · ไม้ที่เปิดอยู่ยังอยู่ใน MT5 พร้อม SL/TP เดิม",
                "warning", ok_text="ซื้อชั่วโมง", cancel_text="ไว้ทีหลัง",
            )
            if buy:
                webbrowser.open(self.STORE_URL)
        finally:
            self._low_hours_dialog_open = False

    def _on_time_expired(self):
        """เมื่อชั่วโมงการใช้งานหมดลง"""
        sound_manager.play_sl_hit()
        messagebox.showwarning(
            "ชั่วโมงการใช้งานหมดลงแล้ว!",
            "เวลาการใช้งานของท่านหมดลงแล้ว (0.00 ชม.)\n"
            "ระบบได้หยุดการทำงานของบอทอัตโนมัติเพื่อความปลอดภัย\n\n"
            "กรุณาเติมชั่วโมงด้วย Product Key เพื่อกลับมาเทรดต่อ"
        )
        self._open_redeem_modal()

    def _open_quick_order(self, side):
        if not license_mgr.is_authenticated:
            messagebox.showwarning("ยังไม่ได้เข้าสู่ระบบ", "กรุณาเข้าสู่ระบบก่อนเข้าไม้")
            return
        dlg = getattr(self, "_quick_dialog", None)
        try:
            if dlg is not None and dlg.winfo_exists():
                dlg.destroy()
        except Exception:
            pass
        self._quick_dialog = QuickOrderDialog(self, side)

    def _on_click_close_all(self):
        """กดปุ่ม Emergency ปิดทุกออเดอร์ทันที"""
        n = len(bot_ctrl.get_telemetry().get("open_positions") or [])
        confirm = messagebox.askyesno(
            "ปิดออเดอร์ทั้งหมด",
            f"ต้องการปิดออเดอร์ทองคำ XAUUSD ทั้งหมด{f' {n} ไม้' if n else ''} ทันทีหรือไม่?\n"
            "ปิดที่ราคาตลาดตอนนี้ · คำสั่งนี้ยกเลิกไม่ได้"
        )
        if confirm:
            count, msg = bot_ctrl.close_all_positions()
            (messagebox.showinfo if count else messagebox.showwarning)("ปิดออเดอร์ทั้งหมด", msg)

    def _on_toggle_sound(self):
        """เปิดหรือปิดเสียงแจ้งเตือน"""
        bot_ctrl.sound_enabled = not bot_ctrl.sound_enabled
        sound_manager.set_sound_enabled(bot_ctrl.sound_enabled)
        self._style_sound_button()
        if bot_ctrl.sound_enabled:
            sound_manager.play_tp_hit()
        else:
            sound_manager.stop_volatility_siren()

    def _style_sound_button(self):
        if bot_ctrl.sound_enabled:
            self.btn_sound_toggle.configure(text="● เสียง: เปิด", fg_color="#0F2A20", hover_color="#143826",
                                            border_color="#2F7A55", text_color=COLOR_SUCCESS_GREEN)
        else:
            self.btn_sound_toggle.configure(text="● เสียง: ปิด", fg_color="#2A1215", hover_color="#38181C",
                                            border_color="#7A2F36", text_color=COLOR_DANGER_RED)

    def _on_toggle_autoscroll(self):
        self.auto_scroll_logs = self.chk_autoscroll.get()

    def _clear_console(self, note=""):
        self._console_entries.clear()
        self.txt_console.configure(state="normal")
        self.txt_console.delete("1.0", "end")
        self.txt_console.configure(state="disabled")
        self._console_cleared_at = time.time()
        if note:
            self._console_banner(note)

    def _open_redeem_modal(self):
        """เปิดหน้าต่างเติมชั่วโมง Product Key"""
        RedeemKeyDialog(self, on_redeemed_callback=self._on_hours_updated)

    def _open_user_stats_modal(self):
        """เปิดหน้าต่างดูสถิติการเทรดละเอียดรายบุคคลและรายแผน"""
        UserStatsDialog(self)

    def _check_app_updates(self, silent_if_latest=False):
        """คงไว้เพื่อความเข้ากันได้ — ใช้การตรวจแบบเธรดเบื้องหลัง"""
        self._start_update_check(manual=not silent_if_latest)

    def _on_hours_updated(self, new_hrs_str: str):
        """อัปเดตเวลาบน Header เมื่อเติมชั่วโมงสำเร็จ"""
        self.lbl_header_hours.configure(text=f"⏳ {new_hrs_str} ชม.")

    def _do_logout(self):
        """ออกจากระบบและกลับไปยังหน้าล็อกอิน"""
        if bot_ctrl.is_active:
            confirm = messagebox.askyesno("ยืนยัน", "บอทกำลังทำงานอยู่ ต้องการหยุดบอทและออกจากระบบหรือไม่?")
            if not confirm:
                return
            bot_ctrl.stop_bot()

        license_mgr.logout()
        self.show_login_view()

    # =========================================================================
    # 4. ลูปอัปเดตสถานะเรียลไทม์ (REALTIME UI LOOP)
    # =========================================================================
    def _realtime_ui_loop(self):
        """ดึงข้อความจาก Queue และอัปเดตค่าสถิติต่างๆ ขึ้นหน้าจอทุก 500ms"""
        try:
            # 1. ระบายข้อความ Log จากบอทขึ้นคอนโซล
            lines = []
            while not bot_ctrl.log_queue.empty():
                try:
                    lines.append(bot_ctrl.log_queue.get_nowait())
                except queue.Empty:
                    break

            if lines and self.dashboard_view and hasattr(self, 'txt_console'):
                self._append_console(self._console_formatter.feed("".join(lines)))

            # 2. ถ้าล็อกอินอยู่ ให้อัปเดตสถานะ Telemetry
            if self.is_logged_in and self.dashboard_view:
                if hasattr(self, "ai_box"):
                    self._render_ai_outlook()
                telemetry = bot_ctrl.get_telemetry()

                # MT5 เปลี่ยนบัญชี → ตรวจ/เปิด Algo Trading ให้บัญชีใหม่ (รอ MT5 สลับเสร็จ 3 วิ แล้วตรวจซ้ำที่ 10 วิ)
                login_now = int(telemetry.get("login") or 0)
                if login_now:
                    prev_login = getattr(self, "_algo_login", None)
                    self._algo_login = login_now
                    if prev_login is not None and prev_login != login_now:
                        why = f"เปลี่ยนเป็นบัญชี #{login_now} · "
                        self.after(3000, lambda w=why: self._auto_algo_trading(w, warn=False))   # MT5 อาจยังสลับไม่เสร็จ — ไม่เตือน
                        self.after(10000, lambda w=why: self._auto_algo_trading(w))

                # อัปเดตชั่วโมงคงเหลือ (ชั่วโมง.นาที)
                hrs_str = telemetry.get("remaining_time", "0.00")
                if hasattr(self, 'lbl_header_hours'):
                    mins_left = license_mgr.get_remaining_minutes()
                    low = mins_left <= self.LOW_HOURS_MINUTES
                    self._check_low_hours_alert(mins_left)
                    self.lbl_header_hours.configure(
                        text=f"⏳ {hrs_str} ชม.",
                        text_color=COLOR_DANGER_RED if low else COLOR_GOLD_PRIMARY,
                    )
                    self.time_pill_frame.configure(
                        fg_color="#2A1518" if low else COLOR_GOLD_BG,
                        border_color="#6B2A30" if low else "#5A4519",
                    )

                self._update_reward(low)

                # ตลาดปิด = ไม่นับชั่วโมง (แสดงสถานะให้ผู้ใช้เห็น)
                if bot_ctrl.is_active and not bot_ctrl.is_paused:
                    if bot_ctrl.market_open:
                        meter = ("● กำลังนับเวลา", COLOR_SUCCESS_GREEN)
                        pill = ("  ● กำลังทำงาน  ", COLOR_SUCCESS_GREEN, "#12301F")
                    else:
                        meter = ("⏸ ตลาดปิด · ไม่นับเวลา", COLOR_DANGER_RED)
                        pill = ("  ⏸ รอตลาดเปิด  ", COLOR_GOLD_PRIMARY, "#2E2410")
                    if self.lbl_metering_status.cget("text") != meter[0]:
                        self.lbl_metering_status.configure(text=meter[0], text_color=meter[1])
                        self.lbl_bot_state.configure(text=pill[0], text_color=pill[1], fg_color=pill[2])

                # ผลการตรวจเวอร์ชันจากเธรดเบื้องหลัง + ตรวจซ้ำทุก 6 ชั่วโมง
                if getattr(self, "_update_result", None):
                    self._apply_update_result()
                elif time.time() - getattr(self, "_last_update_check", time.time()) > self.UPDATE_CHECK_INTERVAL_SEC:
                    self._last_update_check = time.time()
                    self._start_update_check()

                # อัปเดตสถานะ MT5
                is_conn = telemetry.get("is_connected", False)
                acc_num = telemetry.get("login", 0)
                srv = telemetry.get("server", "N/A")
                is_mkt_open = telemetry.get("is_market_open", False)
                if hasattr(self, 'card_mt5'):
                    if is_conn:
                        self.card_mt5["val_lbl"].configure(text=f"#{acc_num}", text_color=COLOR_SUCCESS_GREEN)
                        self.card_mt5["sub_lbl"].configure(text=f"● เชื่อมต่อแล้ว · {srv}")
                        if is_mkt_open:
                            # ตลาดเปิดปกติ: ไอคอนสีเขียว + ป้าย "● ตลาดเปิด" สีเขียว
                            if "icon_lbl" in self.card_mt5:
                                self.card_mt5["icon_lbl"].configure(text_color=COLOR_SUCCESS_GREEN)
                            self._set_badge(self.card_mt5.get("badge"), "● ตลาดเปิด", "#12301F", COLOR_SUCCESS_GREEN)
                        else:
                            # ตลาดปิด: ไอคอนสีแดง + ป้าย "⏸ ตลาดปิด" สีแดง
                            if "icon_lbl" in self.card_mt5:
                                self.card_mt5["icon_lbl"].configure(text_color=COLOR_DANGER_RED)
                            self._set_badge(self.card_mt5.get("badge"), "⏸ ตลาดปิด", "#2A1414", COLOR_DANGER_RED)
                    else:
                        # ยังไม่ได้เชื่อมต่อ MT5: ไอคอนสีขาว (สีดั้งเดิม) + ซ่อนป้าย
                        self.card_mt5["val_lbl"].configure(text="ไม่ได้เชื่อมต่อ", text_color=COLOR_DANGER_RED)
                        self.card_mt5["sub_lbl"].configure(text="กรุณาเปิด MT5 Terminal")
                        if "icon_lbl" in self.card_mt5:
                            self.card_mt5["icon_lbl"].configure(text_color=COLOR_TEXT_PRIMARY)
                        self._set_badge(self.card_mt5.get("badge"), "")

                # อัปเดต Balance & Equity
                bal = telemetry.get("balance", 0.0)
                eq = telemetry.get("equity", 0.0)
                free = telemetry.get("free_margin", 0.0)
                flt = telemetry.get("floating_profit", 0.0)
                if hasattr(self, 'card_balance'):
                    flt_sign = "+" if flt >= 0 else ""
                    self.card_balance["val_lbl"].configure(text=f"{bal:,.2f}")
                    self.card_balance["sub_lbl"].configure(text=f"Equity {eq:,.2f} · Float {flt_sign}{flt:,.2f}")

                # อัปเดตสถานะตลาดทองคำสด (Market Hours)
                mkt = thai_time.get_gold_market_status()
                if hasattr(self, 'lbl_market_status'):
                    color = COLOR_SUCCESS_GREEN if mkt["is_open"] else (COLOR_GOLD_WARM if mkt["state"] == "DAILY_BREAK" else COLOR_DANGER_RED)
                    bg = "#0F2A20" if mkt["is_open"] else ("#261E10" if mkt["state"] == "DAILY_BREAK" else "#2A1414")
                    self.lbl_market_status.configure(text=f"  {mkt['short_desc']}  ", text_color=color, fg_color=bg)

                # อัปเดตราคาทองคำ XAUUSD
                bid = telemetry.get("xau_bid", 0.0)
                ask = telemetry.get("xau_ask", 0.0)
                spd = telemetry.get("spread_pts", 0)
                if hasattr(self, 'card_gold'):
                    if bid > 0:
                        self.card_gold["val_lbl"].configure(text=f"{bid:,.2f}")
                    if mkt["is_open"]:
                        if bid > 0:
                            self.card_gold["sub_lbl"].configure(text=f"Ask {ask:,.2f} · Spread {spd} pts")
                    else:
                        if bid > 0:
                            self.card_gold["sub_lbl"].configure(text=f"Ask {ask:,.2f} · Spread {spd} pts · {mkt['short_desc']}")
                        else:
                            self.card_gold["sub_lbl"].configure(text=mkt["short_desc"])

                # อัปเดตสภาวะตลาด H4 และ H1
                radar = telemetry.get("radar", {})
                h4_trend = radar.get("h4_trend", "ANALYZING...")
                if h4_trend == "ANALYZING...":
                    h4_trend = "รอเริ่มบอท" if not bot_ctrl.is_active else "กำลังวิเคราะห์"
                h4_pct = float(radar.get("h4_diff_pct", 0.0) or 0.0)
                h1_pct = float(radar.get("h1_diff_pct", 0.0) or 0.0)
                h1_trend = str(radar.get("h1_trend", "ANALYZING..."))
                analyzed = "BULL" in h4_trend or "BEAR" in h4_trend or "SIDEWAY" in h4_trend
                if hasattr(self, 'card_trend'):
                    rows = self.card_trend["rows"]
                    pct_color = lambda v: COLOR_SUCCESS_GREEN if v > 0 else COLOR_DANGER_RED if v < 0 else COLOR_TEXT_MUTED
                    # ป้ายมุมขวา = ทิศที่ Plan 3–5 อนุญาต (กฎ Strict Pro-Trend จาก H4 MA10/30)
                    if not analyzed:
                        self._set_badge(self.card_trend["badge"], "")
                    elif "BULL" in h4_trend:
                        self._set_badge(self.card_trend["badge"], "BUY เท่านั้น", "#0F2A20", COLOR_SUCCESS_GREEN)
                    elif "BEAR" in h4_trend:
                        self._set_badge(self.card_trend["badge"], "SELL เท่านั้น", "#2A1414", COLOR_DANGER_RED)
                    else:
                        self._set_badge(self.card_trend["badge"], "BUY / SELL", "#132036", COLOR_CYAN_ACCENT)

                    # สภาวะตลาด H1/H4: MA50 < MA100 < MA150 = ขาลง · MA50 > MA100 > MA150 = ขาขึ้น · แบบอื่น = ไซด์เวย์
                    for tf, key in (("H1", "h1_cond"), ("H4", "h4_cond")):
                        cond = radar.get(key)
                        if cond is None or not analyzed:
                            rows[tf]["val"].configure(text="รอเริ่มบอท" if tf == "H4" and not analyzed else "—", text_color=COLOR_TEXT_MUTED)
                            rows[tf]["pct"].configure(text="")
                            continue
                        cond = int(cond)
                        if cond == 1:
                            rows[tf]["val"].configure(text="▲ Uptrend", text_color=COLOR_SUCCESS_GREEN)
                        elif cond == -1:
                            rows[tf]["val"].configure(text="▼ Downtrend", text_color=COLOR_DANGER_RED)
                        else:
                            rows[tf]["val"].configure(text="◆ Sideway", text_color=COLOR_CYAN_ACCENT)
                        cpct = float(radar.get(f"{key}_pct", 0.0) or 0.0)  # ระยะ MA50 เทียบ MA150 (%)
                        rows[tf]["pct"].configure(text=f"{cpct:+.2f}%", text_color=pct_color(cpct))
                    # ป้าย MA100-200 / MA200 ถูกเอาออกจากการ์ด (ดูรายละเอียดได้ในหน้าต่างอธิบายเมื่อคลิกการ์ด)

                if hasattr(self, 'card_sr'):
                    price = float(bid or radar.get("price", 0.0) or 0.0)
                    for tf, row in self.card_sr["rows"].items():
                        sup = float(radar.get(f"{tf.lower()}_support", 0.0) or 0.0)
                        res = float(radar.get(f"{tf.lower()}_resistance", 0.0) or 0.0)
                        sup_stars = float(radar.get(f"{tf.lower()}_sup_stars", 0.0) or 0.0)
                        res_stars = float(radar.get(f"{tf.lower()}_res_stars", 0.0) or 0.0)
                        ok = sup > 0 and res > 0
                        row["res"].configure(text=f"▲ {res:,.2f}" if ok else "▲ —")
                        row["sup"].configure(text=f"▼ {sup:,.2f}" if ok else "▼ —")
                        if "res_star" in row:
                            row["res_star"].configure(text=self._format_sr_stars(res_stars) if (ok and res_stars >= 0) else "")
                        if "sup_star" in row:
                            row["sup_star"].configure(text=self._format_sr_stars(sup_stars) if (ok and sup_stars >= 0) else "")
                        st = row["state"]
                        if (st["sup"], st["res"], st["price"]) != (sup, res, price):
                            st.update(sup=sup, res=res, price=price)
                            self._draw_sr_bar(row["bar"], st)

                    # ป้ายสรุปตำแหน่งราคาเทียบกรอบ H1 (กรอบที่บอทใช้เข้าไม้ Plan 3/4)
                    h1_state = self.card_sr["rows"]["H1"]["state"]
                    pos = self._sr_position(h1_state["sup"], h1_state["res"], price)
                    if pos is None:
                        self._set_badge(self.card_sr["badge"], "")
                    elif pos > 1:
                        self._set_badge(self.card_sr["badge"], "เหนือแนวต้าน", "#0F2A20", COLOR_SUCCESS_GREEN)
                    elif pos < 0:
                        self._set_badge(self.card_sr["badge"], "หลุดแนวรับ", "#2A1414", COLOR_DANGER_RED)
                    elif pos <= 0.25:
                        self._set_badge(self.card_sr["badge"], "ใกล้แนวรับ", "#0F2A20", COLOR_SUCCESS_GREEN)
                    elif pos >= 0.75:
                        self._set_badge(self.card_sr["badge"], "ใกล้แนวต้าน", "#2A1414", COLOR_DANGER_RED)
                    else:
                        self._set_badge(self.card_sr["badge"], "กลางกรอบ")

                # อัปเดตสถิติ 5 แผน (ตาราง: ไม้ / WR / กำไร)
                if hasattr(self, 'plan_stat_badges'):
                    cur_u = license_mgr.get_current_user()
                    u_plans = stats_mgr.get_user_stats(cur_u.get("user_id")).get("plans", {})
                    tot_tr = tot_win = 0
                    tot_prof = 0.0
                    for full_pname, (lbl_tr, lbl_wr, lbl_pf) in self.plan_stat_badges.items():
                        ps = u_plans.get(full_pname, {})
                        tot_tr += int(ps.get("total_trades", 0) or 0)
                        tot_win += int(ps.get("win_trades", 0) or 0)
                        tot_prof += float(ps.get("total_profit_usd", 0.0) or 0.0)
                        tr = ps.get("total_trades", 0)
                        wr = ps.get("win_rate_pct", 0.0)
                        prof = ps.get("total_profit_usd", 0.0)
                        lbl_tr.configure(text=str(tr), text_color=COLOR_TEXT_PRIMARY if tr else COLOR_TEXT_MUTED)
                        if not plan_config.is_enabled(full_pname.split(": ", 1)[-1]):
                            lbl_wr.configure(text="ปิด", text_color=COLOR_DANGER_RED)  # ปิดโดยผู้ดูแลระบบ
                        else:
                            lbl_wr.configure(text=f"{wr:.0f}%" if tr else "—", text_color=COLOR_GOLD_PRIMARY if tr else COLOR_TEXT_MUTED)
                        lbl_pf.configure(
                            text=f"{'+' if prof >= 0 else '-'}{abs(prof):,.2f}",
                            text_color=COLOR_SUCCESS_GREEN if prof > 0 else (COLOR_DANGER_RED if prof < 0 else COLOR_TEXT_MUTED),
                        )
                    if getattr(self, "plan_total_labels", None):
                        t_tr, t_wr, t_pf = self.plan_total_labels
                        t_tr.configure(text=str(tot_tr), text_color=COLOR_TEXT_PRIMARY if tot_tr else COLOR_TEXT_MUTED)
                        t_wr.configure(text=f"{tot_win / tot_tr * 100:.0f}%" if tot_tr else "—", text_color=COLOR_GOLD_PRIMARY if tot_tr else COLOR_TEXT_MUTED)
                        t_pf.configure(text=f"{'+' if tot_prof >= 0 else '-'}{abs(tot_prof):,.2f}",
                                       text_color=COLOR_SUCCESS_GREEN if tot_prof > 0 else (COLOR_DANGER_RED if tot_prof < 0 else COLOR_TEXT_MUTED))

                # ออเดอร์ที่เปิดอยู่ (อัปเดตทุก ~1 วินาที)
                if hasattr(self, 'positions_body') and self._ui_tick % 2 == 0:
                    self._render_positions(telemetry.get("open_positions"), telemetry.get("server_time", 0))

                # สถิติย่อในแผงควบคุม
                if hasattr(self, 'ctl_stat_labels'):
                    n_open = len(telemetry.get("open_positions") or [])
                    free_m = float(telemetry.get("free_margin", 0.0) or 0.0)
                    n_max = plan_config.max_positions(free_m, self._load_lot()) if telemetry.get("is_connected") else 0
                    self.ctl_stat_labels["open"].configure(
                        text=f"{n_open} / {n_max}",
                        text_color=COLOR_DANGER_RED if n_max and n_open >= n_max else (COLOR_CYAN_ACCENT if n_open else COLOR_TEXT_PRIMARY))
                    self.ctl_stat_labels["margin"].configure(text=f"{free_m:,.2f}", text_color=COLOR_TEXT_PRIMARY)
                    self.ctl_stat_labels["float"].configure(
                        text=f"{'+' if flt >= 0 else '-'}{abs(flt):,.2f}",
                        text_color=COLOR_SUCCESS_GREEN if flt > 0 else (COLOR_DANGER_RED if flt < 0 else COLOR_TEXT_PRIMARY),
                    )
                    if self._bot_started_at and bot_ctrl.is_active and not bot_ctrl.is_paused:
                        el = int(time.time() - self._bot_started_at)
                        self.ctl_stat_labels["uptime"].configure(text=f"{el // 3600:02d}:{el % 3600 // 60:02d}:{el % 60:02d}", text_color=COLOR_SUCCESS_GREEN)
                    elif not bot_ctrl.is_active:
                        self.ctl_stat_labels["uptime"].configure(text="--:--:--", text_color=COLOR_TEXT_MUTED)
                    # มีไม้: ปุ่มแดงเด่น (เตือนว่ากดแล้วปิดทุกไม้) · ไม่มีไม้: ปุ่มเทาเรียบ
                    if n_open:
                        self.btn_close_all.configure(state="normal", text=f"ปิดทั้งหมด ({n_open})", fg_color="#3A1418",
                                                     hover_color="#52191F", border_color=COLOR_DANGER_RED, text_color=COLOR_DANGER_RED)
                    else:
                        self.btn_close_all.configure(state="disabled", text="ไม่มีออเดอร์", fg_color="#1A1E27", border_color="#2A303C")

                # ประวัติการเทรด / ปฏิทินข่าว (โหลดในเธรดเบื้องหลัง แล้ววาดบน UI thread)
                self._ui_tick += 1
                if getattr(self, "_history_dirty", False):
                    self._history_dirty = False
                    self._render_history()
                if getattr(self, "_calendar_dirty", False):
                    self._calendar_dirty = False
                    self._render_calendar()
                    self._render_next_news()
                if self._ui_tick % 40 == 0:      # ~20 วินาที
                    self._refresh_history_async()
                if self._ui_tick % 30 == 0:      # ~15 วินาที (ตัวนับถอยหลังข่าว)
                    self._render_next_news()
                if self._ui_tick % 3600 == 0:    # ~30 นาที
                    self._refresh_calendar_async(force=True)

        except Exception as e:
            pass

        # วนลูปทุกๆ 500ms
        self.after(500, self._realtime_ui_loop)


MUTEX_NAME = "Local\\GoldBot24_AI_Gold_Commander_Pro_SingleInstance"


def _focus_existing_window():
    """ค้นหาหน้าต่างโปรแกรมที่เปิดอยู่แล้ว และนำขึ้นมาแสดงข้างหน้า (Foreground)"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        SW_RESTORE = 9

        current_pid = os.getpid()
        found_hwnd = [None]

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def enum_windows_callback(hwnd, lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    if "AI Gold Commander Pro" in title or "GoldBot24" in title:
                        pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        if pid.value != current_pid:
                            found_hwnd[0] = hwnd
                            return False
            return True

        cb = WNDENUMPROC(enum_windows_callback)
        user32.EnumWindows(cb, 0)

        target_hwnd = found_hwnd[0]
        if target_hwnd:
            user32.ShowWindow(target_hwnd, SW_RESTORE)
            user32.SetForegroundWindow(target_hwnd)
    except Exception:
        pass


def check_single_instance() -> tuple[bool, any]:
    """
    ตรวจสอบว่ามี Instance ของโปรแกรมกำลังรันอยู่แล้วหรือไม่ (Single Instance Guard)
    คืนค่า (is_already_running, mutex_handle)
    """
    if sys.platform != "win32":
        return False, None
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ERROR_ALREADY_EXISTS = 183

        mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        last_error = kernel32.GetLastError()

        if last_error == ERROR_ALREADY_EXISTS:
            _focus_existing_window()
            if mutex:
                kernel32.CloseHandle(mutex)
            return True, None

        return False, mutex
    except Exception:
        return False, None


def launch_gui():
    """ฟังก์ชันเปิดใช้งานหน้าจอ Desktop GUI พร้อมระบบป้องกันเปิดซ้ำซ้อน (Single Instance Guard)"""
    is_running, mutex = check_single_instance()
    if is_running:
        print("[GoldBot24] พบโปรแกรมเปิดใช้งานอยู่แล้ว กำลังสลับไปยังหน้าต่างเดิม...")
        sys.exit(0)

    try:
        app = MainTradingApp()
        app.mainloop()
    finally:
        if mutex:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(mutex)
            except Exception:
                pass


if __name__ == "__main__":
    launch_gui()

