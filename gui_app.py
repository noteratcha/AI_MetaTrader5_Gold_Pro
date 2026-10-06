"""
AI MetaTrader 5 (FBS) Gold Pro - Desktop GUI Application
เวอร์ชัน: ดู version.py
หน้าจอ UI สำหรับเข้าใช้งานระบบ, ตรวจสอบสิทธิ์ชั่วโมง (Hours Metering), เติมชั่วโมงด้วย Product Key,
และควบคุมการเปิด/ปิดระบบเทรดอัตโนมัติ 100% Pure Gold Specialist (XAUUSD)
"""

import os
import json
import sys
import time
import queue
import threading
import webbrowser
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
        tk.Label(frame, text=text, justify="left", bg="#1A1E27", fg=COLOR_TEXT_PRIMARY, font=("Segoe UI", 10),
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


# หน้าต่างย่อยทุกอัน (CTkToplevel) ใช้โลโก้เดียวกับโปรแกรมหลัก
# CustomTkinter ตั้งไอคอนเริ่มต้นของตัวเองหลังสร้าง ~200ms จึงต้องตั้งทับหลังจากนั้น
_ctk_toplevel_init = ctk.CTkToplevel.__init__


def _toplevel_init_with_icon(self, *args, **kwargs):
    _ctk_toplevel_init(self, *args, **kwargs)
    icon = _app_icon_path()
    if os.path.exists(icon):
        def _set():
            try:
                self.iconbitmap(icon)
            except Exception:
                pass
        self.after(250, _set)


ctk.CTkToplevel.__init__ = _toplevel_init_with_icon


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

        self._build_ui()

    def _build_ui(self):
        # หัวเรื่อง
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=28, pady=(24, 12))

        ctk.CTkLabel(
            header_frame,
            text="🔑 เติมชั่วโมงการใช้งาน",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=COLOR_GOLD_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_frame,
            text="กรอกรหัส Product Key (บัตรเติมชั่วโมง) เพื่อเพิ่มเวลาเทรดให้กับบอท",
            font=ctk.CTkFont(family="Segoe UI", size=13),
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
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left")

        self.lbl_current_time = ctk.CTkLabel(
            info_inner,
            text=f"{current_hrs_str} ชม. (ชั่วโมง.นาที)",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_GOLD_WARM
        )
        self.lbl_current_time.pack(side="right")

        # กล่องกรอกรหัส Product Key
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=28, pady=0)

        ctk.CTkLabel(
            input_frame,
            text="รหัส Product Key (รูปแบบ: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX):",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 6))

        self.key_var = tk.StringVar()
        self.key_var.trace_add("write", self._on_key_typing)

        self.key_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.key_var,
            font=ctk.CTkFont(family="Consolas", size=15, weight="bold"),
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
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#FDE68A"
        ).pack(padx=12, pady=8, anchor="w")

        # ข้อความผลลัพธ์แจ้งเตือน
        self.lbl_result = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_SUCCESS_GREEN
        )
        self.lbl_result.pack(padx=28, pady=(0, 10))

        # ปุ่มกดยืนยัน และยกเลิก
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=28, pady=(0, 20))

        self.btn_cancel = ctk.CTkButton(
            btn_frame,
            text="ปิดหน้าต่าง",
            font=ctk.CTkFont(family="Segoe UI", size=14),
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
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
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
    """แจ้งเวอร์ชันใหม่: เวอร์ชันเดิม → ใหม่ · สิ่งที่เปลี่ยนแยกหัวข้อ · ปุ่มดาวน์โหลด"""

    def __init__(self, parent, info, download_url):
        super().__init__(parent)
        import re
        self.title("มีเวอร์ชันใหม่ - AI Gold Commander Pro")
        w, h = 560, 560
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.resizable(False, False)
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.url = download_url

        def f(size, weight="normal"):
            return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)

        # ส่วนหัว: ไอคอน + เวอร์ชันเดิม → ใหม่
        head = ctk.CTkFrame(self, fg_color=COLOR_GOLD_BG, corner_radius=0)
        head.pack(fill="x")
        inner = ctk.CTkFrame(head, fg_color="transparent")
        inner.pack(fill="x", padx=22, pady=16)
        # ไอคอนลูกศรวาดเอง (อักขระ ⬆ บางเครื่องไม่มีฟอนต์ → ขึ้นเป็นกล่อง □)
        icon = tk.Canvas(inner, width=46, height=46, bg=COLOR_GOLD_BG, highlightthickness=0, bd=0)
        icon.create_oval(1, 1, 45, 45, fill="#3A2E14", outline="")
        icon.create_polygon(23, 10, 35, 24, 27, 24, 27, 35, 19, 35, 19, 24, 11, 24, fill=COLOR_GOLD_PRIMARY, outline="")
        icon.pack(side="left")
        txt = ctk.CTkFrame(inner, fg_color="transparent")
        txt.pack(side="left", padx=14)
        ctk.CTkLabel(txt, text="มีเวอร์ชันใหม่พร้อมติดตั้ง", font=f(18, "bold"), text_color=COLOR_GOLD_PRIMARY).pack(anchor="w")
        chips = ctk.CTkFrame(txt, fg_color="transparent")
        chips.pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(chips, text=f"  ใช้งานอยู่ v{APP_VERSION}  ", font=f(11), text_color=COLOR_TEXT_MUTED,
                     fg_color=COLOR_CARD_BG, corner_radius=6, height=22).pack(side="left")
        ctk.CTkLabel(chips, text="→", font=f(13, "bold"), text_color=COLOR_GOLD_PRIMARY).pack(side="left", padx=6)
        ctk.CTkLabel(chips, text=f"  ใหม่ v{info.get('latest_version')}  ", font=f(11, "bold"), text_color="#1A1406",
                     fg_color=COLOR_GOLD_PRIMARY, corner_radius=6, height=22).pack(side="left")

        # มีอะไรใหม่ — แยกตามหัวข้อ ### ใน Release notes
        ctk.CTkLabel(self, text="มีอะไรใหม่", font=f(13, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=22, pady=(14, 6))
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
                         wraplength=470).pack(anchor="w", padx=12, pady=(12 if i == 0 else 12, 4))
            for it in items[:6]:
                row = ctk.CTkFrame(box, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=1)
                ctk.CTkLabel(row, text="•", font=f(12, "bold"), text_color=COLOR_SUCCESS_GREEN, width=14).pack(side="left", anchor="n")
                ctk.CTkLabel(row, text=it, font=f(12), text_color=COLOR_TEXT_PRIMARY, anchor="w", justify="left",
                             wraplength=450).pack(side="left", fill="x")

        ctk.CTkLabel(self, text="ปิดโปรแกรมก่อนติดตั้งทับ · การตั้งค่าและบัญชีของคุณจะยังอยู่ครบ",
                     font=f(11), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=22, pady=(10, 0))
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=22, pady=(10, 18))
        ctk.CTkButton(btns, text="ภายหลัง", width=110, height=38, font=f(13), fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_HOVER,
                      border_width=1, border_color=COLOR_CARD_BORDER, text_color=COLOR_TEXT_MUTED, command=self.destroy).pack(side="right")
        ctk.CTkButton(btns, text="ดาวน์โหลดเวอร์ชันใหม่", height=38, font=f(13, "bold"), fg_color=COLOR_GOLD_PRIMARY,
                      hover_color=COLOR_GOLD_WARM, text_color="#1A1406", command=self._download
                      ).pack(side="right", fill="x", expand=True, padx=(0, 10))

    def _download(self):
        webbrowser.open(self.url)
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
        f = lambda size, weight="normal": ctk.CTkFont(family="Segoe UI", size=size, weight=weight)
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

        def f(size, weight="normal"):
            return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)

        msg = str(message or "").replace("⚠️", "").replace("⚠", "").strip()
        head, _, detail = msg.partition("\n")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=22, pady=(20, 8))
        icon = tk.Canvas(body, width=48, height=48, bg=COLOR_BG_DARK, highlightthickness=0, bd=0)
        icon.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 14))
        icon.create_oval(2, 2, 46, 46, fill=bg, outline=color, width=2)
        icon.create_text(24, 24, text=sym, fill=color, font=("Segoe UI", 18, "bold"))
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

        def f(size, weight="normal", family="Segoe UI"):
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
        ctk.CTkLabel(idrow, text=self.LINE_ID, font=f(18, "bold", "Consolas"), text_color=COLOR_TEXT_PRIMARY).pack(side="left", padx=(0, 10))
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
                      text_color="#FFFFFF", command=lambda: webbrowser.open(self.LINE_URL)).pack(side="right", fill="x", expand=True, padx=(0, 10))
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        w, h = 440, self.winfo_reqheight()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.LINE_ID)
        self.btn_copy.configure(text="✓ แล้ว", text_color=COLOR_SUCCESS_GREEN)


class MarginSettingDialog(ctk.CTkToplevel):
    """ตั้งมาร์จิ้นต่อ 1 ไม้ (จำแยกตามบัญชี) — ยิ่งตั้งสูง บอทยิ่งเปิดไม้พร้อมกันได้น้อยลง (ปลอดภัยขึ้น)"""

    PRESETS = (200, 300, 400, 500, 800)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("มาร์จิ้นต่อไม้")
        self.configure(fg_color=COLOR_BG_DARK)
        self.transient(parent)
        self.resizable(False, False)

        def f(size, weight="normal", family="Segoe UI"):
            return ctk.CTkFont(family=family, size=size, weight=weight)
        self.f = f
        t = bot_ctrl.get_telemetry()
        self.free = float(t.get("free_margin", 0.0) or 0.0)
        self.lot = float(parent._load_lot())
        self.n_open = len(t.get("open_positions") or [])

        ctk.CTkLabel(self, text="มาร์จิ้นต่อ 1 ไม้", font=f(17, "bold"), text_color=COLOR_GOLD_PRIMARY).pack(anchor="w", padx=20, pady=(16, 0))
        for txt, color, pad in (("จำนวนไม้สูงสุด = มาร์จิ้นว่าง ÷ มาร์จิ้นต่อไม้ (เศษปัดขึ้น)", COLOR_TEXT_MUTED, (2, 0)),
                                ("เช่น ตั้ง 400: ไม่เกิน 400 = 1 ไม้ · 401–800 = 2 ไม้ · 960 = 3 ไม้", COLOR_GOLD_PRIMARY, (0, 0)),
                                ("ตั้งสูง = เปิดได้น้อยไม้ (ปลอดภัยขึ้น) · ตั้งต่ำ = เปิดได้หลายไม้ (เสี่ยงขึ้น)", COLOR_TEXT_MUTED, (0, 10))):
            ctk.CTkLabel(self, text=txt, font=f(11), text_color=color, justify="left", height=20).pack(anchor="w", padx=20, pady=pad)

        card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        card.pack(fill="x", padx=18)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(top, text="มาร์จิ้นว่างตอนนี้", font=f(12), text_color=COLOR_TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(top, text=f"{self.free:,.2f}", font=f(15, "bold", "Consolas"), text_color=COLOR_TEXT_PRIMARY).pack(side="right")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(2, 4))
        ctk.CTkLabel(row, text="มาร์จิ้นต่อ 1 ไม้ (ที่ Lot 0.01)", font=f(12, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        self.var = tk.StringVar(value=f"{plan_config.get_margin_per_trade():g}")
        ent = ctk.CTkEntry(row, textvariable=self.var, width=100, height=32, justify="center", font=f(14, "bold", "Consolas"))
        ent.pack(side="right")
        chips = ctk.CTkFrame(card, fg_color="transparent")
        chips.pack(fill="x", padx=14, pady=(4, 12))
        for v in self.PRESETS:
            ctk.CTkButton(chips, text=f"{v:,}" + (" (ค่าเริ่มต้น)" if v == 400 else ""), height=26,
                          width=112 if v == 400 else 58, font=f(11, "bold"), corner_radius=13,
                          fg_color="#1A1E27", hover_color="#262B36", border_width=1, border_color=COLOR_CARD_BORDER,
                          text_color=COLOR_GOLD_PRIMARY if v == 400 else COLOR_TEXT_PRIMARY,
                          command=lambda x=v: self.var.set(str(x))).pack(side="left", padx=2)

        self.lbl_calc = ctk.CTkLabel(self, text="", font=f(13, "bold"), text_color=COLOR_SUCCESS_GREEN, justify="left")
        self.lbl_calc.pack(anchor="w", padx=20, pady=(10, 0))
        self.lbl_note = ctk.CTkLabel(self, text="", font=f(10), text_color=COLOR_TEXT_MUTED, justify="left")
        self.lbl_note.pack(anchor="w", padx=20)
        self.var.trace_add("write", lambda *_: self._refresh())

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=(12, 18))
        ctk.CTkButton(btns, text="ยกเลิก", width=100, height=40, font=f(13), fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_HOVER,
                      border_width=1, border_color=COLOR_CARD_BORDER, text_color=COLOR_TEXT_MUTED, command=self.destroy).pack(side="right")
        self.btn_ok = ctk.CTkButton(btns, text="บันทึก", height=40, font=f(14, "bold"), fg_color=COLOR_GOLD_PRIMARY,
                                    hover_color=COLOR_GOLD_WARM, text_color="#1A1406", command=self._save)
        self.btn_ok.pack(side="right", fill="x", expand=True, padx=(0, 10))
        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        self._refresh()
        self.update_idletasks()
        w, h = 460, self.winfo_reqheight()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.grab_set()
        ent.focus_set()

    def _value(self):
        try:
            v = float(str(self.var.get()).replace(",", "").strip())
            return v if 10 <= v <= 1000000 else None
        except ValueError:
            return None

    def _refresh(self):
        v = self._value()
        if v is None:
            self.lbl_calc.configure(text="ใส่ตัวเลข 10 ขึ้นไป", text_color=COLOR_DANGER_RED)
            self.lbl_note.configure(text="")
            self.btn_ok.configure(state="disabled")
            return
        per = v * max(self.lot, 0.01) / 0.01
        n = plan_config.max_positions(self.free, self.lot, margin=v)
        self.lbl_calc.configure(text=f"มาร์จิ้นว่าง {self.free:,.2f} ÷ {per:,.0f} (ปัดขึ้น) → เปิดได้สูงสุด {n} ไม้ (เปิดอยู่ {self.n_open})",
                                text_color=COLOR_SUCCESS_GREEN)
        lot_note = f"Lot ตอนนี้ {self.lot:.2f} → ใช้ {per:,.0f} ต่อไม้" if abs(self.lot - 0.01) > 1e-9 else "Lot 0.01 → ใช้ตามค่าที่ตั้ง"
        self.lbl_note.configure(text=f"{lot_note} · อย่างน้อยเปิดได้ 1 ไม้เสมอ · จำค่าแยกตามบัญชี")
        self.btn_ok.configure(state="normal")

    def _save(self):
        v = self._value()
        if v is None:
            return
        try:
            plan_config.set_margin_per_trade(v)
            print(f"[MARGIN SETTING] มาร์จิ้นต่อไม้ = {v:,.0f} (ที่ Lot 0.01)")
        except Exception as e:
            self.lbl_calc.configure(text=f"บันทึกไม่สำเร็จ: {e}", text_color=COLOR_DANGER_RED)
            return
        self.destroy()


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

        def f(size, weight="normal", family="Segoe UI"):
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
        self.lbl_px = ctk.CTkLabel(pbox, text="—", font=f(20, "bold", "Consolas"), text_color=COLOR_TEXT_PRIMARY)
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
            v = ctk.CTkLabel(box, text="—", font=f(14, "bold", "Consolas"), text_color=color)
            v.pack()
            sub = ctk.CTkLabel(box, text="", font=f(10, "bold"), text_color=color)
            sub.pack()
            self.sum_cells[key] = (v, sub)
        self.lbl_rrr = ctk.CTkLabel(self, text="", font=f(11, "bold"), text_color=COLOR_GOLD_PRIMARY)
        self.lbl_rrr.pack(pady=(8, 0))
        ctk.CTkLabel(self, text="บอทดูแลไม้นี้ต่อด้วยล็อกกำไร / AI กลับทิศ / ปิดเมื่อกำไรถึง $ ตามปกติ",
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
        ent = ctk.CTkEntry(box, textvariable=var, width=86, height=32, justify="center", font=f(14, "bold", "Consolas"))
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
            import MetaTrader5 as _mt5
            t = _mt5.symbol_info_tick("XAUUSD")
            if t:
                self.d["bid"], self.d["ask"] = float(t.bid), float(t.ask)
                self._refresh()
            self.after(1000, self._tick)
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

        def f(size, weight="normal", family="Segoe UI"):
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
            ctk.CTkLabel(parent, text=text, font=f(size, "normal", "Consolas" if mono else "Segoe UI"), text_color=color,
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
    """กราฟแท่งเทียน XAUUSD M15 แบบเรียลไทม์: แท่งปัจจุบัน + ย้อนหลัง 15 แท่ง พร้อม MA5 / MA13 (เส้นที่ Plan 1 ใช้)"""

    BARS = 120   # ค่าเริ่มต้น (ปรับได้ที่ตัวเลือก "จำนวนแท่ง")
    BAR_CHOICES = ("16", "30", "50", "80", "120", "200", "300", "500")
    REFRESH_MS = 1000

    def __init__(self, parent):
        super().__init__(parent)
        self.title("XAUUSD · M15 เรียลไทม์")
        w, h = 980, 600
        self.configure(fg_color=COLOR_BG_DARK)
        # ไม่ใช้ transient เพื่อให้มีปุ่มขยายเต็มจอ/ย่อ บนแถบหัวหน้าต่าง
        self.after(10, self.lift)
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(560, 380)
        self.data, self.slots, self._job = None, [], None

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(14, 4))
        ctk.CTkLabel(top, text="XAUUSD · M15", font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
                     text_color=COLOR_GOLD_PRIMARY).pack(side="left")
        self.lbl_price = ctk.CTkLabel(top, text="—", font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
                                      text_color=COLOR_TEXT_PRIMARY)
        self.lbl_price.pack(side="left", padx=14)
        self.lbl_change = ctk.CTkLabel(top, text="", font=ctk.CTkFont(family="Segoe UI", size=12))
        self.lbl_change.pack(side="left")
        self.btn_full = ctk.CTkButton(top, text="ขยายเต็มจอ", width=96, height=26, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                      fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_HOVER, border_width=1, border_color=COLOR_CARD_BORDER,
                                      text_color=COLOR_GOLD_PRIMARY, command=self._toggle_full)
        self.btn_full.pack(side="right", padx=(10, 0))
        self.bind("<F11>", lambda e: self._toggle_full())
        self.bind("<Escape>", lambda e: self.state() == "zoomed" and self._toggle_full())
        self.lbl_clock = ctk.CTkLabel(top, text="", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=COLOR_TEXT_MUTED)
        self.lbl_clock.pack(side="right")
        # กำไร/ขาดทุนรวมของไม้ที่เปิดอยู่ (รวม swap)
        self.lbl_pnl = ctk.CTkLabel(top, text="", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                                    corner_radius=8, height=26)
        self.lbl_pnl.pack(side="right", padx=12)

        legend = ctk.CTkFrame(self, fg_color="transparent")
        legend.pack(fill="x", padx=18)
        self.bars_var = tk.StringVar(value=str(self.BARS))
        ctk.CTkSegmentedButton(legend, values=list(self.BAR_CHOICES), variable=self.bars_var, font=ctk.CTkFont(family="Segoe UI", size=11),
                               selected_color=COLOR_GOLD_WARM, selected_hover_color=COLOR_GOLD_DARK,
                               command=lambda v: self._tick(reschedule=False)).pack(side="right")
        ctk.CTkLabel(legend, text="จำนวนแท่ง", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=COLOR_TEXT_MUTED).pack(side="right", padx=6)
        for txt, col in (("━ MA5", COLOR_CYAN_ACCENT), ("━ MA13", COLOR_GOLD_WARM), ("┅ Bid / Ask", COLOR_TEXT_MUTED),
                         ("┅ ราคาเข้า", COLOR_CYAN_ACCENT), ("┅ TP", COLOR_SUCCESS_GREEN), ("┅ SL", COLOR_DANGER_RED)):
            ctk.CTkLabel(legend, text=txt, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=col).pack(side="left", padx=(0, 14))

        box = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        box.pack(fill="both", expand=True, padx=18, pady=8)
        self.canvas = tk.Canvas(box, bg=COLOR_CARD_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<Motion>", self._hover)
        self.canvas.bind("<Leave>", lambda e: self.lbl_tip.configure(text=self.tip_default))
        self.tip_default = "อัปเดตทุก 1 วินาที · ชี้ที่แท่งเพื่อดู Open / High / Low / Close"
        self.lbl_tip = ctk.CTkLabel(self, text=self.tip_default, font=ctk.CTkFont(family="Segoe UI", size=12), text_color=COLOR_TEXT_MUTED)
        self.lbl_tip.pack(pady=(0, 10))
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._tick()

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

    @staticmethod
    def _hhmm(server_ts, offset):
        from datetime import datetime, timedelta, timezone
        return datetime.fromtimestamp(server_ts - offset, timezone(timedelta(hours=7))).strftime("%H:%M")

    def _tick(self, reschedule=True):
        try:
            n = int(self.bars_var.get())
        except Exception:
            n = self.BARS
        data = bot_ctrl.get_live_candles(n)
        if data:
            self.data = data
            # เวลาเซิร์ฟเวอร์ MT5 → เวลาไทย (ปัดส่วนต่างเป็นชั่วโมง)
            off = round((data["server_time"] - time.time()) / 3600) * 3600
            self.offset = off if abs(off) <= 14 * 3600 else 0
            c = data["candles"]
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
            remain = max(0, last["time"] + 900 - data["server_time"])
            self.lbl_clock.configure(text=f"แท่งปัจจุบันปิดในอีก {remain // 60:02d}:{remain % 60:02d}")
            self._draw()
        else:
            self.lbl_tip.configure(text="เชื่อมต่อ MT5 ไม่ได้ — ตรวจว่าเปิด MetaTrader 5 ค้างไว้")
        if reschedule:
            self._job = self.after(self.REFRESH_MS, self._tick)

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
        left, right, top, bottom = 10, 70, 16, 28
        vals = [v for c in candles for v in (c["high"], c["low"], c["ma5"], c["ma13"]) if v is not None]
        vals.append(self.data["ask"])
        for p in self.data.get("positions", []):  # ให้เห็นเส้นราคาเข้า/TP/SL ในกรอบเสมอ
            vals += [v for v in (p["price"], p["sl"], p["tp"]) if v and v > 0]
        hi, lo = max(vals), min(vals)
        pad = max((hi - lo) * 0.08, 0.5)
        hi, lo = hi + pad, lo - pad
        ch = H - top - bottom

        def y_of(v):
            return top + (hi - v) / (hi - lo) * ch

        for k in range(6):  # เส้นราคาแนวนอน
            v = lo + (hi - lo) * k / 5
            y = y_of(v)
            cv.create_line(left, y, W - right, y, fill="#1E232C")
            cv.create_text(W - right + 6, y, text=f"{v:,.2f}", anchor="w", fill=COLOR_TEXT_MUTED, font=("Segoe UI", 9))
        n = len(candles)
        slot = (W - left - right) / n
        bw = max(3, min(26, slot * 0.62))
        for name, col in (("ma5", COLOR_CYAN_ACCENT), ("ma13", COLOR_GOLD_WARM)):
            pts = []
            for i, c in enumerate(candles):
                if c[name] is not None:
                    pts += [left + slot * (i + 0.5), y_of(c[name])]
            if len(pts) >= 4:
                cv.create_line(*pts, fill=col, width=2, smooth=True)
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
            every = max(1, int(round(n / max(1, (W - left - right) / 52))))
            if (i % every == 0 and i < n - max(2, int(every * 0.8))) or live:
                cv.create_text(cx, H - bottom + 13, text="ตอนนี้" if live else self._hhmm(c["time"], self.offset),
                               fill=COLOR_GOLD_PRIMARY if live else COLOR_TEXT_MUTED, font=("Segoe UI", 9, "bold" if live else "normal"))
            self.slots.append((cx - slot / 2, cx + slot / 2, c))
        # ไม้ที่เปิดอยู่: ราคาเข้า / TP / SL / Lot
        for p in self.data.get("positions", []):
            for val, col, txt in ((p["price"], COLOR_CYAN_ACCENT, f"{p['type']} {p['lot']:.2f} lot @ {p['price']:,.2f} ({p['profit']:+.2f})"),
                                  (p["tp"], COLOR_SUCCESS_GREEN, f"TP {p['tp']:,.2f}"), (p["sl"], COLOR_DANGER_RED, f"SL {p['sl']:,.2f}")):
                if not val or val <= 0:
                    continue
                yy = y_of(val)
                cv.create_line(left, yy, W - right, yy, fill=col, dash=(6, 3))
                cv.create_text(left + 4, yy - 7, text=txt, anchor="w", fill=col, font=("Segoe UI", 9, "bold"))
        # เส้น Ask
        ya = y_of(self.data["ask"])
        cv.create_line(left, ya, W - right, ya, fill="#5B6270", dash=(2, 4))
        cv.create_text(W - right + 6, ya - 12 if abs(ya - y_of(self.data["bid"])) < 18 else ya, text=f"A {self.data['ask']:,.2f}", anchor="w", fill=COLOR_TEXT_MUTED, font=("Segoe UI", 8))
        # เส้นราคาล่าสุด
        yb = y_of(self.data["bid"])
        cv.create_line(left, yb, W - right, yb, fill=COLOR_TEXT_MUTED, dash=(3, 3))
        cv.create_rectangle(W - right + 2, yb - 9, W - 2, yb + 9, fill=COLOR_GOLD_PRIMARY, outline="")
        cv.create_text(W - right + 6, yb, text=f"{self.data['bid']:,.2f}", anchor="w", fill="#111111", font=("Segoe UI", 9, "bold"))

    def _hover(self, event):
        for x0, x1, c in self.slots:
            if x0 <= event.x < x1:
                ma = ""
                if c["ma5"] is not None and c["ma13"] is not None:
                    ma = f" · MA5 {c['ma5']:,.2f} / MA13 {c['ma13']:,.2f}"
                self.lbl_tip.configure(text=f"{self._hhmm(c['time'], self.offset)} น. · O {c['open']:,.2f}  H {c['high']:,.2f}  "
                                            f"L {c['low']:,.2f}  C {c['close']:,.2f} ({c['close'] - c['open']:+.2f}){ma}")
                return


class PnlHistoryDialog(ctk.CTkToplevel):
    """กราฟแท่งกำไร/ขาดทุนสุทธิรายวันของพอร์ต (ดึงจาก MT5) พร้อมเลือกช่วงวันที่"""

    PRESETS = (("7 วัน", 7), ("14 วัน", 14), ("30 วัน", 30), ("เดือนนี้", "month"), ("90 วัน", 90))
    TH_MONTHS = ("ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.")

    def __init__(self, parent):
        super().__init__(parent)
        from datetime import date, timedelta
        self._date, self._td = date, timedelta
        self.title("ประวัติกำไร / ขาดทุนรายวัน")
        w, h = 900, 560
        self.configure(fg_color=COLOR_BG_DARK)
        # ไม่ใช้ transient เพื่อให้มีปุ่มขยายเต็มจอ/ย่อ บนแถบหัวหน้าต่าง
        self.after(10, self.lift)
        self.update_idletasks()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(720, 460)
        self.rows, self.bars, self.weekly = [], [], False
        self._build()
        self.after(50, lambda: self._apply_preset(14))

    @staticmethod
    def _f(size, weight="normal"):
        return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 6))
        ctk.CTkLabel(top, text="ประวัติกำไร / ขาดทุนรายวัน", font=self._f(18, "bold"), text_color=COLOR_GOLD_PRIMARY).pack(side="left")
        ctk.CTkLabel(top, text="ทั้งบัญชี MT5 · รวม commission/swap · เวลาไทย", font=self._f(11), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=12)

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
        self.ent_from = ctk.CTkEntry(bar, width=100, height=28, font=self._f(12), placeholder_text="YYYY-MM-DD")
        self.ent_from.pack(side="left")
        ctk.CTkLabel(bar, text="ถึง", font=self._f(12), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=6)
        self.ent_to = ctk.CTkEntry(bar, width=100, height=28, font=self._f(12), placeholder_text="YYYY-MM-DD")
        self.ent_to.pack(side="left")
        ctk.CTkButton(bar, text="แสดง", width=60, height=28, font=self._f(12, "bold"), fg_color=COLOR_GOLD_PRIMARY,
                      text_color="#111111", hover_color=COLOR_GOLD_WARM, command=self._apply_custom).pack(side="left", padx=8)

        self.summary = ctk.CTkFrame(self, fg_color="transparent")
        self.summary.pack(fill="x", padx=20, pady=(0, 8))
        self.summary.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="pnl_sum")
        self.sum_lbls = []
        for i, title in enumerate(("กำไรสุทธิช่วงนี้", "วันกำไร / ขาดทุน", "วันที่ดีที่สุด", "วันที่แย่ที่สุด")):
            c = ctk.CTkFrame(self.summary, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
            c.grid(row=0, column=i, padx=4, sticky="nsew")
            ctk.CTkLabel(c, text=title, font=self._f(11), text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=12, pady=(8, 0))
            v = ctk.CTkLabel(c, text="—", font=self._f(17, "bold"), text_color=COLOR_TEXT_PRIMARY)
            v.pack(anchor="w", padx=12)
            s = ctk.CTkLabel(c, text="", font=self._f(10), text_color=COLOR_TEXT_MUTED)
            s.pack(anchor="w", padx=12, pady=(0, 8))
            self.sum_lbls.append((v, s))

        box = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        self.canvas = tk.Canvas(box, bg=COLOR_CARD_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<Motion>", self._hover)
        self.canvas.bind("<Leave>", lambda e: self.lbl_tip.configure(text=self.tip_default, text_color=COLOR_TEXT_MUTED))
        self.tip_default = "ชี้ที่แท่งเพื่อดูรายละเอียด"
        self.lbl_tip = ctk.CTkLabel(self, text=self.tip_default, font=self._f(12), text_color=COLOR_TEXT_MUTED)
        self.lbl_tip.pack(pady=(0, 10))

    @staticmethod
    def _money(v, dp=2):
        """+26.34 / -22.46 / 0 (ไม่ใส่สัญลักษณ์ $ ตามสไตล์โปรแกรม)"""
        if abs(v) < 0.005:
            return "0"
        return f"{'+' if v > 0 else '-'}{abs(v):,.{dp}f}"

    def _fmt_date(self, d, year=False):
        return f"{d.day} {self.TH_MONTHS[d.month - 1]}" + (f" {d.year + 543}" if year else "")

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
        # ช่วงยาวเกิน 62 วัน → รวมเป็นรายสัปดาห์ให้แท่งอ่านง่าย
        if len(daily) > 62:
            weeks = {}
            for r in daily:
                k = r["date"] - self._td(days=r["date"].weekday())
                w = weeks.setdefault(k, {"date": k, "end": k + self._td(days=6), "profit": 0.0, "closed": 0})
                w["profit"] += r["profit"]
                w["closed"] += r["closed"]
            self.rows, self.weekly = list(weeks.values()), True
        else:
            self.rows, self.weekly = daily, False
        self.tip_default = (f"{self._fmt_date(start, True)} – {self._fmt_date(end, True)} · "
                            + ("รวมรายสัปดาห์" if self.weekly else "รายวัน") + " · ชี้ที่แท่งเพื่อดูรายละเอียด")
        self.lbl_tip.configure(text=self.tip_default, text_color=COLOR_TEXT_MUTED)
        self._summary(daily)
        self._draw()

    def _summary(self, daily):
        total = sum(r["profit"] for r in daily)
        pos = [r for r in daily if r["profit"] > 0.005]
        neg = [r for r in daily if r["profit"] < -0.005]
        best = max(daily, key=lambda r: r["profit"], default=None)
        worst = min(daily, key=lambda r: r["profit"], default=None)
        (v0, s0), (v1, s1), (v2, s2), (v3, s3) = self.sum_lbls
        v0.configure(text=self._money(total), text_color=COLOR_SUCCESS_GREEN if total >= 0 else COLOR_DANGER_RED)
        s0.configure(text=f"ปิดไม้ {sum(r['closed'] for r in daily)} ไม้")
        v1.configure(text=f"{len(pos)} / {len(neg)} วัน", text_color=COLOR_TEXT_PRIMARY)
        s1.configure(text=f"ไม่มีกำไร/ขาดทุน {len(daily) - len(pos) - len(neg)} วัน")
        for v, s, r, good in ((v2, s2, best, True), (v3, s3, worst, False)):
            if r and ((good and r["profit"] > 0.005) or (not good and r["profit"] < -0.005)):
                v.configure(text=self._money(r["profit"]), text_color=COLOR_SUCCESS_GREEN if good else COLOR_DANGER_RED)
                s.configure(text=self._fmt_date(r["date"], True))
            else:
                v.configure(text="—", text_color=COLOR_TEXT_MUTED)
                s.configure(text="")

    def _draw(self):
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
            cv.create_text(left - 8, y, text=self._money(v, 0 if step >= 1 else 2), anchor="e", fill=COLOR_TEXT_MUTED, font=("Segoe UI", 9))
            v += step
        y0 = y_of(0)
        cv.create_line(left, y0, W - right, y0, fill="#4B5263")
        n = len(self.rows)
        slot = (W - left - right) / n
        bw = max(2, min(38, slot * 0.68))
        label_every = max(1, int(round(n / max(1, (W - left - right) / 58))))
        for i, r in enumerate(self.rows):
            cx = left + slot * (i + 0.5)
            v = r["profit"]
            y = y_of(v)
            color = COLOR_SUCCESS_GREEN if v > 0 else COLOR_DANGER_RED
            if abs(v) < 0.005:
                cv.create_line(cx - bw / 2, y0, cx + bw / 2, y0, fill="#3A4050", width=2)
            else:
                cv.create_rectangle(cx - bw / 2, min(y, y0), cx + bw / 2, max(y, y0), fill=color, outline="")
                if slot >= 34:
                    cv.create_text(cx, y - 9 if v > 0 else y + 9, text=self._money(v), fill=color, font=("Segoe UI", 8, "bold"))
            if i % label_every == 0:
                cv.create_text(cx, H - bottom + 14, text=self._fmt_date(r["date"]), fill=COLOR_TEXT_MUTED, font=("Segoe UI", 9))
            self.bars.append((cx - slot / 2, cx + slot / 2, r))

    def _hover(self, event):
        for x0, x1, r in self.bars:
            if x0 <= event.x < x1:
                when = (f"สัปดาห์ {self._fmt_date(r['date'])} – {self._fmt_date(r['end'], True)}" if self.weekly
                        else self._fmt_date(r["date"], True))
                v = r["profit"]
                word = "กำไร" if v > 0.005 else ("ขาดทุน" if v < -0.005 else "ไม่มีกำไร/ขาดทุน")
                self.lbl_tip.configure(text=f"{when} · {word} {self._money(v)} · ปิดไม้ {r['closed']} ไม้",
                                       text_color=COLOR_SUCCESS_GREEN if v > 0.005 else COLOR_DANGER_RED if v < -0.005 else COLOR_TEXT_MUTED)
                return


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

        self._build_ui()

    def _build_ui(self):
        # ส่วนหัว (Header)
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 10))

        ctk.CTkLabel(
            hdr,
            text="📊 สถิติการเทรดรายบุคคลและประสิทธิภาพรายแผน",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLOR_GOLD_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            hdr,
            text=f"บัญชีผู้ใช้: {self.email} (ID: {self.user_id}) • อัปเดตข้อมูลแบบ Real-time",
            font=ctk.CTkFont(family="Segoe UI", size=12),
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
            ctk.CTkLabel(c_inner, text=title, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(anchor="w")
            ctk.CTkLabel(c_inner, text=val, font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=colr).pack(anchor="w", pady=(4, 2))
            ctk.CTkLabel(c_inner, text=sub, font=ctk.CTkFont(family="Segoe UI", size=10), text_color=COLOR_TEXT_MUTED).pack(anchor="w")

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
            lbl = ctk.CTkLabel(th_frame, text=title, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=COLOR_GOLD_PRIMARY)
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
            ctk.CTkLabel(row_frame, text=p_name, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=8, pady=8, sticky="w")
            # 2. จำนวนเข้าไม้
            ctk.CTkLabel(row_frame, text=f"{p_trades} ไม้", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=1, padx=8)
            # 3. ชนะ/แพ้
            ctk.CTkLabel(row_frame, text=f"{p_win}W / {p_loss}L", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=COLOR_TEXT_MUTED).grid(row=0, column=2, padx=8)
            # 4. Win Rate %
            wr_colr = COLOR_SUCCESS_GREEN if p_wr >= 50 else (COLOR_GOLD_WARM if p_wr >= 40 else COLOR_TEXT_MUTED)
            ctk.CTkLabel(row_frame, text=f"{p_wr:.1f}%", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=wr_colr).grid(row=0, column=3, padx=8)
            # 5. Profit USD
            prof_colr = COLOR_SUCCESS_GREEN if p_profit > 0 else (COLOR_DANGER_RED if p_profit < 0 else COLOR_TEXT_MUTED)
            ctk.CTkLabel(row_frame, text=f"{p_profit:+,.2f}", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=prof_colr).grid(row=0, column=4, padx=8)
            # 6. Profit Factor
            ctk.CTkLabel(row_frame, text=f"{p_pf:.2f}", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=COLOR_GOLD_WARM if p_pf >= 1.5 else COLOR_TEXT_MUTED).grid(row=0, column=5, padx=8)

        # ปุ่มปิดหน้าต่าง
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 18))

        ctk.CTkButton(
            btn_frame,
            text="ปิดหน้าต่าง",
            font=ctk.CTkFont(family="Segoe UI", size=13),
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
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=COLOR_GOLD_PRIMARY
        ).pack()

        ctk.CTkLabel(
            inner,
            text="Next-Gen Autonomous Gold Specialist (XAUUSD) • GoldBot24",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED
        ).pack(pady=(2, 4))

        version_badge = ctk.CTkFrame(inner, fg_color=COLOR_GOLD_BG, corner_radius=6, border_width=1, border_color="#523E15")
        version_badge.pack(pady=(0, 16))
        ctk.CTkLabel(
            version_badge,
            text=f"v{APP_VERSION} • GoldBot24 Cloud Service (1.00 THB/hr)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_GOLD_WARM
        ).pack(padx=10, pady=4)

        # แถบสลับโหมด Login vs Register
        self.auth_mode = "login"
        self.seg_auth = ctk.CTkSegmentedButton(
            inner,
            values=["🔑 เข้าสู่ระบบ (Sign In)", "✨ สมัครสมาชิกใหม่ (รับฟรี 48 ชม.)"],
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
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
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.entry_reg_name = ctk.CTkEntry(
            self.form_frame,
            font=ctk.CTkFont(family="Segoe UI", size=13),
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
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.lbl_email.pack(anchor="w", pady=(0, 4))

        # อีเมล/รหัสผ่านล่าสุดที่ติ๊ก "จดจำ" ไว้ (รหัสผ่านเข้ารหัสด้วย Windows DPAPI)
        remembered_email, remembered_pwd = secure_store.load_login()
        saved_user = remembered_email or license_mgr.session_data.get("email") or ""
        self.entry_email = ctk.CTkEntry(
            self.form_frame,
            font=ctk.CTkFont(family="Segoe UI", size=13),
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
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.lbl_pwd.pack(anchor="w", pady=(0, 4))

        self.entry_pwd = ctk.CTkEntry(
            self.form_frame,
            font=ctk.CTkFont(family="Segoe UI", size=13),
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
            font=ctk.CTkFont(family="Segoe UI", size=11),
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
            font=ctk.CTkFont(family="Segoe UI", size=11, underline=True),
            text_color=COLOR_CYAN_ACCENT,
            cursor="hand2",
        )
        self.lbl_forgot.place(relx=1.0, y=0, anchor="ne")
        self.lbl_forgot.bind("<Button-1>", lambda e: self._open_forgot_password())

        # 4) ยืนยันรหัสผ่าน (สำหรับ Register)
        self.lbl_reg_confirm = ctk.CTkLabel(
            self.form_frame,
            text="ยืนยันรหัสผ่านอีกครั้ง (Confirm Password):",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        )
        self.entry_reg_confirm = ctk.CTkEntry(
            self.form_frame,
            font=ctk.CTkFont(family="Segoe UI", size=13),
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
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
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
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_GOLD_WARM,
            hover_color=COLOR_GOLD_DARK
        )
        self.chk_remember.pack(anchor="w", pady=(0, 12))

        # ข้อความแสดงสถานะ
        self.lbl_login_status = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_DANGER_RED
        )
        self.lbl_login_status.pack(pady=(0, 10))

        # ปุ่มดำเนินการหลัก
        self.btn_auth_submit = ctk.CTkButton(
            inner,
            text="🚀 เข้าสู่ระบบ (Sign In)",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
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
            font=ctk.CTkFont(family="Segoe UI", size=11, underline=True),
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
        self._build_next_news_card(right)
        self._build_plans_card(right)

        self._refresh_history_async()
        self._refresh_calendar_async()

        # ตรวจสอบอัปเดตเวอร์ชันซอฟต์แวร์อัตโนมัติแบบเงียบๆ หลังเปิดหน้าจอ 3 วินาที
        self._update_result = None
        self._last_update_check = 0.0
        self.after(800, self._start_update_check)

    # ---------------------------------------------------------------------
    # ส่วนประกอบ UI ใช้ซ้ำ
    # ---------------------------------------------------------------------
    @staticmethod
    def _font(size=12, weight="normal", family="Segoe UI"):
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

        # ปุ่ม "เติมคีย์" ซ่อนไว้ (ผู้ใช้ซื้อชั่วโมงผ่านเว็บ — ระบบเติมเข้าบัญชีอัตโนมัติ)
        ctk.CTkButton(
            wallet, text="🛒 ซื้อชั่วโมง", font=self._font(12, "bold"), fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK,
            text_color="#1A1406", height=32, width=104, corner_radius=8,
            command=lambda: webbrowser.open(self.STORE_URL),
        ).pack(side="left")

    def _open_user_menu(self):
        """เมนูผู้ใช้: เปิดเว็บ / สถิติ / ตรวจอัปเดต / ออกจากระบบ"""
        email = license_mgr.session_data.get("email") or ""
        menu = tk.Menu(
            self, tearoff=0, bg="#1A1E27", fg=COLOR_TEXT_PRIMARY, activebackground="#2A303C",
            activeforeground=COLOR_GOLD_PRIMARY, disabledforeground=COLOR_TEXT_MUTED, bd=0, relief="flat",
            font=("Segoe UI", 11),
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
        self._make_clickable(self.card_gold, lambda: GoldCandleDialog(self), hint="กราฟ M15 ›")
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

        body = ctk.CTkFrame(inner, fg_color="transparent")
        body.pack(fill="x", pady=(3, 0))
        return {"card": card, "badge": badge, "body": body}

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
        pct = ctk.CTkLabel(row, text="", font=self._font(11, "bold", "Consolas"), text_color=COLOR_TEXT_MUTED, height=22)
        pct.pack(side="right")
        # ลำดับเส้น MA50 / MA100 / MA150 (แท่งปิด) เช่น 50<100<150 = ขาลง — อัปเดตทุก 30 วินาที (_ma_order_tick)
        lt = ctk.CTkLabel(row, text="", font=self._font(10, "bold", "Consolas"), text_color=COLOR_TEXT_MUTED, height=22)
        lt.pack(side="right", padx=(0, 6))
        return {"val": val, "pct": pct, "lt": lt}

    def _create_sr_row(self, parent, tf, col=0):
        """คอลัมน์ต่อ Timeframe (H1 ซ้าย · H4 ขวา): ▲ ต้าน / บาร์ระยะห่าง / ▼ รับ
        บาร์: ช่วงเขียว = ระยะจากแนวรับถึงราคา · ช่วงแดง = ระยะจากราคาถึงแนวต้าน · จุดทอง = ราคาปัจจุบัน"""
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=0, column=col, sticky="nsew", padx=(0, 6) if col == 0 else (6, 0))
        head = ctk.CTkFrame(box, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkLabel(head, text=tf, width=28, height=16, corner_radius=5, fg_color="#1F2430",
                     font=self._font(9, "bold"), text_color=COLOR_TEXT_MUTED).pack(side="left", padx=(0, 6))
        res = ctk.CTkLabel(head, text="▲ —", font=self._font(11, "bold", "Consolas"), text_color=COLOR_DANGER_RED, height=16)
        res.pack(side="left")
        bar = tk.Canvas(box, height=10, bg=COLOR_CARD_BG, highlightthickness=0, bd=0)
        bar.pack(fill="x", pady=(3, 3))
        sup = ctk.CTkLabel(box, text="▼ —", font=self._font(11, "bold", "Consolas"), text_color=COLOR_SUCCESS_GREEN, height=16, anchor="w")
        sup.pack(anchor="w", padx=(34, 0))
        state = {"sup": 0.0, "res": 0.0, "price": 0.0}
        bar.bind("<Configure>", lambda e, b=bar, st=state: self._draw_sr_bar(b, st))
        return {"sup": sup, "res": res, "bar": bar, "state": state}

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
        ctk.CTkLabel(top_row, text=icon, font=ctk.CTkFont(size=15)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(top_row, text=title, font=self._font(12), text_color=COLOR_TEXT_MUTED).pack(side="left")

        val_label = ctk.CTkLabel(inner, text=val_text, font=self._font(19, "bold"), text_color=accent_color, height=26)
        val_label.pack(anchor="w", pady=(2, 0))
        sub_label = ctk.CTkLabel(inner, text=sub_text, font=self._font(11), text_color=COLOR_TEXT_MUTED, height=18)
        sub_label.pack(anchor="w")
        return {"card": card, "val_lbl": val_label, "sub_lbl": sub_label}

    def _make_clickable(self, card_info, command, hint=""):
        """ทำให้ทั้งการ์ดกดได้ (เคอร์เซอร์มือ + ขอบสีทองเมื่อชี้)"""
        card = card_info["card"]
        state = {"win": None}

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

        def bind_all(w):
            w.bind("<Button-1>", open_once, add="+")
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass
            for ch in w.winfo_children():
                bind_all(ch)

        if hint:
            ctk.CTkLabel(card, text=hint, font=self._font(10), text_color=COLOR_GOLD_WARM, height=14).place(relx=1.0, x=-12, y=9, anchor="ne")
        bind_all(card)
        card.bind("<Enter>", lambda e: card.configure(border_color=COLOR_GOLD_DARK), add="+")
        card.bind("<Leave>", lambda e: card.configure(border_color=COLOR_CARD_BORDER), add="+")

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


        # สถิติย่อ 3 ช่อง: ออเดอร์เปิดอยู่ / กำไรลอยตัว / เวลาทำงาน
        stats = ctk.CTkFrame(card, fg_color="#101218", corner_radius=10)
        stats.pack(fill="x", padx=14, pady=(6, 0))
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="ctl_stats")
        self.ctl_stat_labels = {}
        for col, (key, title, init) in enumerate((("open", "ออเดอร์ / สูงสุด", "0 / 0"), ("float", "กำไรลอยตัว", "0.00"),
                                                  ("margin", "มาร์จิ้นว่าง ›", "0.00"), ("uptime", "เวลาทำงาน", "--:--:--"))):
            box = ctk.CTkFrame(stats, fg_color="transparent")
            box.grid(row=0, column=col, sticky="nsew", pady=5)
            ttl = ctk.CTkLabel(box, text=title, font=self._font(10), height=16,
                               text_color=COLOR_GOLD_WARM if key == "margin" else COLOR_TEXT_MUTED)
            ttl.pack()
            val = ctk.CTkLabel(box, text=init, font=self._font(14, "bold"), text_color=COLOR_TEXT_PRIMARY, height=22)
            val.pack()
            self.ctl_stat_labels[key] = val
            if key == "open":  # กดจำนวนออเดอร์ → ไปแท็บออเดอร์ที่เปิดอยู่
                for w in (box, val, ttl):
                    w.configure(cursor="hand2")
                    w.bind("<Button-1>", lambda e: self.main_tabs.set(self.TAB_POSITIONS))
            if key == "margin":  # กดมาร์จิ้น → ตั้งมาร์จิ้นต่อไม้
                for w in (box, val, ttl):
                    w.configure(cursor="hand2")
                    w.bind("<Button-1>", lambda e: self._open_margin_setting())

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

    def _build_next_news_card(self, parent):
        card = self._card(parent, fill="x", pady=(0, 8))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=14, pady=(6, 6))
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(body, text="📅 ข่าวสำคัญถัดไป · USD", font=self._font(11, "bold"), text_color=COLOR_TEXT_MUTED, anchor="w", height=20).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            body, text="ดูทั้งหมด ›", font=self._font(11, "bold"), fg_color="transparent", hover_color="#1F2430",
            text_color=COLOR_CYAN_ACCENT, width=66, height=20, corner_radius=6,
            command=lambda: self.main_tabs.set(self.TAB_CALENDAR),
        ).grid(row=0, column=1, sticky="e")

        self.lbl_news_title = ctk.CTkLabel(body, text="กำลังโหลดปฏิทินข่าว...", font=self._font(13, "bold"), text_color=COLOR_TEXT_PRIMARY, anchor="w", height=22)
        self.lbl_news_title.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.lbl_news_badge = ctk.CTkLabel(body, text="", font=self._font(10, "bold"), text_color="#101218", fg_color=COLOR_CARD_BG, corner_radius=6, height=18)
        self.lbl_news_badge.grid(row=1, column=1, sticky="e", pady=(2, 0))

        self.lbl_news_time = ctk.CTkLabel(body, text="", font=self._font(11), text_color=COLOR_TEXT_MUTED, anchor="w", height=20)
        self.lbl_news_time.grid(row=2, column=0, sticky="w")
        self.lbl_news_countdown = ctk.CTkLabel(body, text="", font=self._font(13, "bold"), text_color=COLOR_GOLD_PRIMARY, height=20)
        self.lbl_news_countdown.grid(row=2, column=1, sticky="e")

    PLAN_ROWS = [
        ("📈", "P1 · MA M15", "Plan 1: MA-Cross-Trend"),
        ("👑", "P2 · MA H1", "Plan 2: MA-Cross-H1-Trend"),
        ("⚡", "P3 · SMC Hunt", "Plan 3: SMC-LiquidityHunt"),
        ("🎯", "P4 · SR Bounce", "Plan 4: SR-SwingBounce"),
        ("🌊", "P5 · BB-H1", "Plan 5: BB-H1-Reversion"),
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
        for r, (icon, short, full) in enumerate(self.PLAN_ROWS, start=1):
            last = r == len(self.PLAN_ROWS)
            pady = 0
            # ติ๊กเลือกใช้แผนนี้ (จำแยกตามบัญชีผู้ใช้) — แผนที่แอดมินปิดจะติ๊กไม่ได้
            var = tk.BooleanVar(value=plan_config.user_enabled(full.split(": ", 1)[-1]))
            chk = ctk.CTkCheckBox(
                table, text=f"{icon}  {short}", variable=var, font=self._font(11, "bold"), text_color=COLOR_TEXT_PRIMARY,
                fg_color=COLOR_GOLD_WARM, hover_color=COLOR_GOLD_DARK, checkbox_width=14, checkbox_height=14, height=17,
                command=lambda f=full, v=var: self._toggle_user_plan(f, v),
            )
            chk.grid(row=r, column=0, sticky="w", padx=(10, 4), pady=pady)
            self.plan_checks[full] = (chk, var)
            # ป้ายไม้ที่เปิดอยู่ของแผนนี้ (เช่น "● SELL") — อัปเดตทุก 2 วินาที
            live = ctk.CTkLabel(table, text="", font=self._font(10, "bold"), text_color=COLOR_GOLD_PRIMARY, corner_radius=6, height=16)
            live.grid(row=r, column=0, sticky="e", padx=(4, 0), pady=pady)
            self.plan_live_badges[full] = live
            cells = []
            for col in (1, 2, 3):
                lbl = ctk.CTkLabel(table, text="0" if col == 1 else ("—" if col == 2 else "0.00"), font=self._font(11), text_color=COLOR_TEXT_MUTED, anchor="e", height=17, width=40 if col < 3 else 64)
                lbl.grid(row=r, column=col, sticky="e", padx=(4, 12 if col == 3 else 4), pady=pady)
                cells.append(lbl)
            self.plan_stat_badges[full] = tuple(cells)
        # แถวไม้ที่เข้าเอง (ปุ่ม BUY/SELL ในแผงควบคุม → comment "Manual-Quick") — ไม่มีช่องติ๊ก
        n = len(self.PLAN_ROWS) + 1
        mkey = bot_ctrl.QUICK_PLAN
        self.manual_plan_label = ctk.CTkLabel(table, text="✋  เข้าไม้เอง", font=self._font(11, "bold"), text_color=COLOR_TEXT_PRIMARY,
                                              anchor="w", height=18)
        self.manual_plan_label.grid(row=n, column=0, sticky="w", padx=(31, 4), pady=(0, 2))
        live = ctk.CTkLabel(table, text="", font=self._font(10, "bold"), text_color=COLOR_GOLD_PRIMARY, corner_radius=6, height=16)
        live.grid(row=n, column=0, sticky="e", padx=(4, 0), pady=(0, 4))
        self.plan_live_badges[mkey] = live
        cells = []
        for col in (1, 2, 3):
            lbl = ctk.CTkLabel(table, text="0" if col == 1 else ("—" if col == 2 else "0.00"), font=self._font(11),
                               text_color=COLOR_TEXT_MUTED, anchor="e", height=18, width=40 if col < 3 else 64)
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
                    lbl.configure(text="", fg_color="transparent")
        except Exception:
            pass
        self.after(2000, self._plan_live_tick)

    def _ma_order_tick(self):
        """อ่านลำดับ MA50/100/150 ของ H1/H4 จาก MT5 ในเธรดเบื้องหลังทุก 30 วิ — เธรดหลักตรวจผลทุก 1 วิแล้วแสดงบนการ์ด
        (Tk ห้ามเรียกจากเธรดอื่น จึงส่งผลผ่านตัวแปรแทน self.after)"""
        st = self.__dict__.setdefault("_ma_state", {"data": None, "busy": False, "next": 0.0})
        if st["data"] is not None:
            self._apply_ma_order(st["data"])
            st["data"] = None
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
            font=ctk.CTkFont(family="Consolas", size=12),
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

    CONSOLE_BANNER = (
        (f"🏆 AI Gold Commander Pro v{APP_VERSION}\n", "close"),
        ("XAUUSD · P1 SL 1.0 ATR ไม่ตั้ง TP · P2 SL 0.75 ATR (H1) ไม่ตั้ง TP · P3–P5 SL 0.75 ATR · TP RRR 1:1.5\n", "muted"),
        ("คิดเวลาเฉพาะตอนบอททำงาน\n", "muted"),
        ("กด ▶ เริ่มการทำงานบอท ด้านขวาเพื่อเริ่มสแกนตลาด — ที่นี่จะแสดงเฉพาะเหตุการณ์สำคัญ (เปิด/ปิดออเดอร์ ฯลฯ)\n\n", "profit"),
    )

    def _console_banner(self, note=""):
        self.txt_console.configure(state="normal")
        for text, tag in self.CONSOLE_BANNER + (((note, "muted"),) if note else ()):
            self._console_entries.append((text, tag, "key"))
            self.txt_console.insert("end", text, tag)
        self.txt_console.configure(state="disabled")

    def _console_autoclear_tick(self):
        """ทุก 1 นาที: ถ้าเปิด 'ล้างอัตโนมัติ' และครบ 1 ชม. นับจากล้างครั้งล่าสุด → ล้างคอนโซล"""
        try:
            if self.console_autoclear_var.get() and time.time() - self._console_cleared_at >= 3600:
                self._clear_console(note=f"ล้างประวัติอัตโนมัติเมื่อ {time.strftime('%H:%M')} น. (ปิดได้ที่ช่อง 'ล้างอัตโนมัติทุก 1 ชม.')\n\n")
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
        ("Ticket", 78, "w"),
        ("ฝั่ง", 44, "center"),
        ("แผน", 120, "w"),
        ("Lot", 36, "e"),
        ("ราคาเข้า", 70, "e"),
        ("ราคาปัจจุบัน", 80, "e"),
        ("Stop Loss", 86, "e"),
        ("Take Profit", 78, "e"),
        ("ถือมา", 56, "e"),
        ("กำไร", 72, "e"),
        ("", 46, "center"),
    ]

    def _build_positions_tab(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=6, pady=(0, 8))
        self.lbl_positions_summary = ctk.CTkLabel(top, text="ไม่มีออเดอร์ที่เปิดอยู่", font=self._font(12, "bold"), text_color=COLOR_TEXT_MUTED)
        self.lbl_positions_summary.pack(side="left")
        ctk.CTkLabel(top, text="อัปเดตอัตโนมัติ · เวลาเปิดตามเซิร์ฟเวอร์ MT5", font=self._font(10), text_color=COLOR_TEXT_MUTED).pack(side="right")

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
                    lbl = ctk.CTkLabel(frame, text="", font=self._font(12), anchor=anchor, height=32)
                    lbl.grid(row=0, column=col, sticky="ew", padx=4)
                    cells.append(lbl)
                btn = ctk.CTkButton(
                    frame, text="ปิด", width=40, height=24, corner_radius=6, font=self._font(11, "bold"),
                    fg_color="#3A2226", hover_color="#4A2A2F", text_color=COLOR_DANGER_RED,
                    command=lambda tk_=t: self._on_close_single(tk_),
                )
                btn.grid(row=0, column=len(self.POSITION_COLUMNS) - 1, padx=4)
                self._position_rows[t] = {"frame": frame, "cells": cells}
            if tickets:
                self.lbl_positions_empty.pack_forget()
            else:
                self.lbl_positions_empty.pack(pady=40)

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
            values = [
                f"#{p['ticket']}",
                p.get("type", ""),
                (p.get("comment") or "Manual")[:20],
                f"{float(p.get('volume', 0)):.2f}",
                f"{open_price:,.2f}",
                f"{float(p.get('price_current', 0)):,.2f}",
                sl_text,
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
                COLOR_TEXT_MUTED,
                COLOR_TEXT_MUTED,
                COLOR_SUCCESS_GREEN if profit > 0 else (COLOR_DANGER_RED if profit < 0 else COLOR_TEXT_MUTED),
            ]
            for lbl, v, c in zip(self._position_rows[p["ticket"]]["cells"], values, colors):
                if lbl.cget("text") != v:
                    lbl.configure(text=v, text_color=c)

        if positions:
            self.lbl_positions_summary.configure(
                text=f"{len(positions)} ไม้ (BUY {buys} · SELL {sells}) · รวม {total_lot:.2f} Lot · กำไรลอยตัว {'+' if total_profit >= 0 else '-'}{abs(total_profit):,.2f}",
                text_color=COLOR_SUCCESS_GREEN if total_profit > 0 else (COLOR_DANGER_RED if total_profit < 0 else COLOR_TEXT_PRIMARY),
            )
        else:
            self.lbl_positions_summary.configure(text="ไม่มีออเดอร์ที่เปิดอยู่", text_color=COLOR_TEXT_MUTED)

    def _on_close_single(self, ticket):
        if not messagebox.askyesno("ยืนยันการปิดออเดอร์", f"ต้องการปิดออเดอร์ #{ticket} ทันทีหรือไม่?"):
            return
        ok, msg = bot_ctrl.close_position_by_ticket(ticket)
        (messagebox.showinfo if ok else messagebox.showwarning)("ผลการปิดออเดอร์", msg)

    # ---- ประวัติการเทรด (5 รายการต่อหน้า) ----
    HISTORY_PAGE_SIZE = 10
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
        ("เวลาเปิด (MT5)", 96, "w"),
        ("ฝั่ง", 40, "center"),
        ("แผน", 140, "w"),
        ("Lot", 36, "e"),
        ("ราคาเข้า", 72, "e"),
        ("ราคาออก", 72, "e"),
        ("ปิดโดย", 116, "w"),
        ("กำไร", 76, "e"),
    ]

    def _build_history_tab(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=6, pady=(0, 8))
        self.lbl_history_summary = ctk.CTkLabel(top, text="กำลังโหลดประวัติจาก MT5...", font=self._font(12), text_color=COLOR_TEXT_MUTED)
        self.lbl_history_summary.pack(side="left")
        self._refresh_button(top, lambda: self._refresh_history_async(force=True)).pack(side="right")

        table = ctk.CTkFrame(parent, fg_color="#101218", corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        table.pack(fill="x", padx=6)
        for col, (_, width, _) in enumerate(self.HISTORY_COLUMNS):
            table.grid_columnconfigure(col, minsize=width, weight=1 if col == 2 else 0)

        for col, (title, _, anchor) in enumerate(self.HISTORY_COLUMNS):
            ctk.CTkLabel(table, text=title, font=self._font(11, "bold"), text_color=COLOR_TEXT_MUTED, anchor=anchor).grid(
                row=0, column=col, sticky="ew", padx=6, pady=(10, 6)
            )
        ctk.CTkFrame(table, fg_color=COLOR_CARD_BORDER, height=1).grid(row=1, column=0, columnspan=len(self.HISTORY_COLUMNS), sticky="ew", padx=6)

        # สร้างแถวไว้ล่วงหน้า 10 แถว แล้วอัปเดตข้อความแทนการสร้างใหม่ (ลื่นกว่า) · สูงแถวละ 28 ให้พอดีจอ 1366×768
        self.history_cells = []
        for r in range(self.HISTORY_PAGE_SIZE):
            cells = []
            for col, (_, _, anchor) in enumerate(self.HISTORY_COLUMNS):
                lbl = ctk.CTkLabel(table, text="", font=self._font(12), text_color=COLOR_TEXT_PRIMARY, anchor=anchor, height=28)
                last = r == self.HISTORY_PAGE_SIZE - 1
                lbl.grid(row=r + 2, column=col, sticky="ew", padx=6, pady=(0, 6) if last else 0)
                cells.append(lbl)
            self.history_cells.append(cells)

        self.lbl_history_empty = ctk.CTkLabel(parent, text="", font=self._font(12), text_color=COLOR_TEXT_MUTED)
        self.lbl_history_empty.pack(pady=(8, 0))

        pager = ctk.CTkFrame(parent, fg_color="transparent")
        pager.pack(fill="x", padx=6, pady=(6, 0))
        self.btn_history_prev = self._small_button(pager, "◀ ใหม่กว่า", lambda: self._change_history_page(-1), width=90)
        self.btn_history_prev.pack(side="left")
        self.lbl_history_page = ctk.CTkLabel(pager, text="หน้า 1 / 1", font=self._font(12, "bold"), text_color=COLOR_TEXT_PRIMARY)
        self.lbl_history_page.pack(side="left", expand=True)
        self.btn_history_next = self._small_button(pager, "เก่ากว่า ▶", lambda: self._change_history_page(1), width=90)
        self.btn_history_next.pack(side="right")

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

    def _change_history_page(self, delta):
        pages = max(1, -(-len(self._history_rows) // self.HISTORY_PAGE_SIZE))
        self._history_page = min(max(0, self._history_page + delta), pages - 1)
        self._render_history()

    @staticmethod
    def _fmt_mt5_time(epoch):
        if not epoch:
            return "—"
        return time.strftime("%d/%m %H:%M", time.gmtime(epoch))  # เวลา MT5 เก็บเป็นเวลาเซิร์ฟเวอร์

    def _render_history(self):
        rows = self._history_rows
        total = len(rows)
        pages = max(1, -(-total // self.HISTORY_PAGE_SIZE))
        self._history_page = min(self._history_page, pages - 1)
        start = self._history_page * self.HISTORY_PAGE_SIZE
        page_rows = rows[start:start + self.HISTORY_PAGE_SIZE]

        closed = [r for r in rows if r.get("status") == "CLOSED"]
        wins = sum(1 for r in closed if r["profit"] > 0)
        net = sum(r["profit"] for r in closed)
        open_count = total - len(closed)
        self.lbl_history_summary.configure(
            text=f"90 วันล่าสุด · ปิดแล้ว {len(closed)} ไม้ (ชนะ {wins} / แพ้ {len(closed) - wins})"
            f" · เปิดอยู่ {open_count} · กำไรสุทธิ {'+' if net >= 0 else '-'}{abs(net):,.2f}",
            text_color=COLOR_SUCCESS_GREEN if net > 0 else (COLOR_DANGER_RED if net < 0 else COLOR_TEXT_MUTED),
        )

        for i, cells in enumerate(self.history_cells):
            if i >= len(page_rows):
                for c in cells:
                    c.configure(text="")
                continue
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
            for c, v, color in zip(cells, values, colors):
                c.configure(text=v, text_color=color)

        self.lbl_history_empty.configure(text="" if total else "ยังไม่มีประวัติการเทรด XAUUSD ใน 90 วันที่ผ่านมา")
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
        right = ctk.CTkFrame(hero, fg_color="transparent")
        right.grid(row=0, column=2, rowspan=2, padx=16)
        ctk.CTkLabel(right, text=f"{r['price']:,.2f}", font=self._font(20, "bold", "Consolas"), text_color=COLOR_TEXT_PRIMARY).pack(anchor="e")
        ctk.CTkLabel(right, text=f"อัปเดต {upd.strftime('%H:%M')} น. · ทุก 1 นาที", font=self._font(10), text_color=muted).pack(anchor="e")

        # ── 2) การ์ด 3 ช่วงเวลา
        for col, h in enumerate(r["horizons"]):
            d = h["direction"]
            lean = h["lean"]
            c = ctk.CTkFrame(box, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1,
                             border_color=tone(d) if d else COLOR_CARD_BORDER)
            c.grid(row=1, column=col, sticky="nsew", padx=4, pady=4)
            top = ctk.CTkFrame(c, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(12, 0))
            ctk.CTkLabel(top, text=f"อีก {h['label']}", font=self._font(12, "bold"), text_color=muted).pack(side="left")
            ctk.CTkLabel(top, text=" ชัด " if d else " ไม่ชัด ", font=self._font(10, "bold"), corner_radius=6, height=18,
                         fg_color=dark(d) if d else "#262B36", text_color=tone(d) if d else muted).pack(side="right")
            pct = h["p_up"] * 100 if lean > 0 else (1 - h["p_up"]) * 100
            ctk.CTkLabel(c, text=f"{'▲' if lean > 0 else '▼'} {pct:.0f}%", font=self._font(26, "bold"),
                         text_color=tone(lean) if d else gold).pack(anchor="w", padx=14, pady=(2, 0))
            ctk.CTkLabel(c, text=f"โอกาส{'ขึ้น' if lean > 0 else 'ลง'}" + ("" if d else " (ยังไม่ถึง 55%)"), font=self._font(11),
                         text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=14)
            bar = tk.Canvas(c, height=8, bg=COLOR_CARD_BG, highlightthickness=0, bd=0)
            bar.pack(fill="x", padx=14, pady=(8, 2))

            def draw(e, b=bar, up=h["p_up"]):
                b.delete("all")
                w = max(e.width, 10)
                x = 4 + up * (w - 8)
                b.create_line(4, 4, w - 4, 4, fill=red, width=8, capstyle="round")
                b.create_line(4, 4, x, 4, fill=green, width=8, capstyle="round")
            bar.bind("<Configure>", draw)
            leg = ctk.CTkFrame(c, fg_color="transparent")
            leg.pack(fill="x", padx=14)
            ctk.CTkLabel(leg, text=f"ขึ้น {h['p_up'] * 100:.0f}%", font=self._font(10), text_color=green).pack(side="left")
            ctk.CTkLabel(leg, text=f"ลง {(1 - h['p_up']) * 100:.0f}%", font=self._font(10), text_color=red).pack(side="right")
            foot = ctk.CTkFrame(c, fg_color="#101218", corner_radius=8)
            foot.pack(fill="x", padx=10, pady=(8, 10))
            ctk.CTkLabel(foot, text=f"แม่นในอดีต {h['hist_acc']:.0f}%", font=self._font(10, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left", padx=8, pady=4)
            if h["trend_agree"] and d:
                ctk.CTkLabel(foot, text="✓ เทรนด์ยืนยัน", font=self._font(10, "bold"), text_color=green).pack(side="right", padx=8)

        # ── 3) ปัจจัยที่นำมาวิเคราะห์
        fac = ctk.CTkFrame(box, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        fac.grid(row=2, column=0, columnspan=3, sticky="ew", padx=4, pady=(8, 4))
        ups = sum(1 for f in r["factors"] if f["dir"] > 0)
        dns = sum(1 for f in r["factors"] if f["dir"] < 0)
        mids = len(r["factors"]) - ups - dns
        fh = ctk.CTkFrame(fac, fg_color="transparent")
        fh.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(fh, text="ปัจจัยที่นำมาวิเคราะห์", font=self._font(13, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        for txt, n, col_ in (("กลาง", mids, muted), ("กดลง", dns, red), ("หนุนขึ้น", ups, green)):  # pack ขวา → เรียงกลับ
            ctk.CTkLabel(fh, text=f" {txt} {n} ", font=self._font(10, "bold"), corner_radius=6, height=20,
                         fg_color="#101218", text_color=col_).pack(side="right", padx=(6, 0))
        for i, f in enumerate(r["factors"]):
            d = f["dir"]
            rowf = ctk.CTkFrame(fac, fg_color="#171B23" if i % 2 == 0 else "transparent", corner_radius=8)
            rowf.pack(fill="x", padx=10, pady=1)
            ctk.CTkLabel(rowf, text=" ▲ ขึ้น " if d > 0 else " ▼ ลง " if d < 0 else " • กลาง ", font=self._font(10, "bold"),
                         width=62, corner_radius=6, height=20, fg_color=dark(d) if d else "#262B36",
                         text_color=tone(d) if d else muted).pack(side="left", padx=(6, 10), pady=5)
            ctk.CTkLabel(rowf, text=f["name"], font=self._font(12, "bold"), text_color=COLOR_TEXT_PRIMARY, width=220, anchor="w").pack(side="left")
            ctk.CTkLabel(rowf, text=f["detail"], font=self._font(11), text_color=muted, anchor="w").pack(side="left", padx=(6, 8))
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
        for ev in events:
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
            ctk.CTkLabel(self.cal_list, text=ev["time"].strftime("%H:%M"), font=self._font(12, "bold"), text_color=fg, width=48, anchor="w").grid(row=row, column=0, padx=(12, 4), sticky="w")
            ctk.CTkLabel(self.cal_list, text=ev["currency"], font=self._font(11, "bold"), text_color=fg, width=36).grid(row=row, column=1, padx=4)
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
            title_lbl = ctk.CTkLabel(self.cal_list, text=ev["title"], font=self._font(12), text_color=fg, anchor="w")
            title_lbl.grid(row=row, column=3, sticky="ew", padx=6)
            th = news_th.translate(ev["title"])
            if th:
                HoverTip(title_lbl, th)
            if a:
                txt, tone = news_impact.short_text(a)
                col = {"up": COLOR_SUCCESS_GREEN, "down": COLOR_DANGER_RED}.get(tone, COLOR_TEXT_MUTED)
                imp_lbl = ctk.CTkLabel(self.cal_list, text=txt + "  ›", font=self._font(11, "bold"), text_color=col, width=128, anchor="e")
                imp_lbl.grid(row=row, column=6, padx=(4, 12))
                open_detail = lambda e, ev=ev, a=a: NewsImpactDialog(self, ev, a, self._last_gold_price())
                for w in (title_lbl, imp_lbl):
                    w.configure(cursor="hand2")
                    w.bind("<Button-1>", open_detail)
            ctk.CTkLabel(self.cal_list, text=f"คาด {ev['forecast'] or '—'}", font=self._font(11), text_color=COLOR_TEXT_MUTED, width=80, anchor="e").grid(row=row, column=4, padx=4)
            ctk.CTkLabel(self.cal_list, text=f"ก่อน {ev['previous'] or '—'}", font=self._font(11), text_color=COLOR_TEXT_MUTED, width=84, anchor="e").grid(row=row, column=5, padx=4)
            row += 1

    def _last_gold_price(self) -> float:
        try:
            import MetaTrader5 as _mt5
            t = _mt5.symbol_info_tick("XAUUSD")
            return float(t.bid) if t else 0.0
        except Exception:
            return 0.0

    def _render_next_news(self):
        ev = econ_calendar.next_high_impact(self._calendar_events)
        if not ev:
            self.lbl_news_title.configure(text="ไม่มีข่าว USD ผลกระทบสูงในสัปดาห์นี้" if self._calendar_events else "กำลังโหลดปฏิทินข่าว...")
            self.lbl_news_time.configure(text="")
            self.lbl_news_countdown.configure(text="")
            self.lbl_news_badge.configure(text="", fg_color=COLOR_CARD_BG)
            return
        self.lbl_news_badge.configure(text="  ผลกระทบสูง  ", fg_color=self.IMPACT_COLORS["High"])
        self.lbl_news_title.configure(text=ev["title"] if len(ev["title"]) <= 30 else ev["title"][:29] + "…")
        detail = f"{econ_calendar.format_day(ev['time'])} · {ev['time'].strftime('%H:%M')} น."
        self.lbl_news_time.configure(text=detail)
        countdown = econ_calendar.format_countdown(ev["time"])
        soon = (ev["time"] - econ_calendar.datetime.now(econ_calendar.BANGKOK)).total_seconds() < 3600
        self.lbl_news_countdown.configure(text=countdown, text_color=COLOR_DANGER_RED if soon else COLOR_GOLD_PRIMARY)

    # =========================================================================
    # 3. การควบคุมบอท และเหตุการณ์ต่างๆ (BOT ACTIONS & EVENTS)
    # =========================================================================
    def _on_toggle_bot(self):
        """กดปุ่ม Start/Pause บอท"""
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

    def _open_margin_setting(self):
        dlg = getattr(self, "_margin_dialog", None)
        try:
            if dlg is not None and dlg.winfo_exists():
                dlg.lift()
                return
        except Exception:
            pass
        self._margin_dialog = MarginSettingDialog(self)

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
        self._style_sound_button()
        if bot_ctrl.sound_enabled:
            sound_manager.play_tp_hit()

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

                # อัปเดตชั่วโมงคงเหลือ (ชั่วโมง.นาที)
                hrs_str = telemetry.get("remaining_time", "0.00")
                if hasattr(self, 'lbl_header_hours'):
                    mins_left = license_mgr.get_remaining_minutes()
                    low = mins_left <= self.LOW_HOURS_MINUTES
                    self.lbl_header_hours.configure(
                        text=f"⏳ {hrs_str} ชม.",
                        text_color=COLOR_DANGER_RED if low else COLOR_GOLD_PRIMARY,
                    )
                    self.time_pill_frame.configure(
                        fg_color="#2A1518" if low else COLOR_GOLD_BG,
                        border_color="#6B2A30" if low else "#5A4519",
                    )

                # ตลาดปิด = ไม่นับชั่วโมง (แสดงสถานะให้ผู้ใช้เห็น)
                if bot_ctrl.is_active and not bot_ctrl.is_paused:
                    if bot_ctrl.market_open:
                        meter = ("● กำลังนับเวลา", COLOR_SUCCESS_GREEN)
                        pill = ("  ● กำลังทำงาน  ", COLOR_SUCCESS_GREEN, "#12301F")
                    else:
                        meter = ("⏸ ตลาดปิด · ไม่นับเวลา", COLOR_GOLD_PRIMARY)
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
                if hasattr(self, 'card_mt5'):
                    if is_conn:
                        self.card_mt5["val_lbl"].configure(text=f"#{acc_num}", text_color=COLOR_SUCCESS_GREEN)
                        self.card_mt5["sub_lbl"].configure(text=f"● เชื่อมต่อแล้ว · {srv}")
                    else:
                        self.card_mt5["val_lbl"].configure(text="ไม่ได้เชื่อมต่อ", text_color=COLOR_DANGER_RED)
                        self.card_mt5["sub_lbl"].configure(text="กรุณาเปิด MT5 Terminal")

                # อัปเดต Balance & Equity
                bal = telemetry.get("balance", 0.0)
                eq = telemetry.get("equity", 0.0)
                free = telemetry.get("free_margin", 0.0)
                flt = telemetry.get("floating_profit", 0.0)
                if hasattr(self, 'card_balance'):
                    flt_sign = "+" if flt >= 0 else ""
                    self.card_balance["val_lbl"].configure(text=f"{bal:,.2f}")
                    self.card_balance["sub_lbl"].configure(text=f"Equity {eq:,.2f} · Float {flt_sign}{flt:,.2f}")

                # อัปเดตราคาทองคำ XAUUSD
                bid = telemetry.get("xau_bid", 0.0)
                ask = telemetry.get("xau_ask", 0.0)
                spd = telemetry.get("spread_pts", 0)
                if hasattr(self, 'card_gold') and bid > 0:
                    self.card_gold["val_lbl"].configure(text=f"{bid:,.2f}")
                    self.card_gold["sub_lbl"].configure(text=f"Ask {ask:,.2f} · Spread {spd} pts")

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
                        ok = sup > 0 and res > 0
                        row["res"].configure(text=f"▲ {res:,.2f}" if ok else "▲ —")
                        row["sup"].configure(text=f"▼ {sup:,.2f}" if ok else "▼ —")
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


def launch_gui():
    """ฟังก์ชันเปิดใช้งานหน้าจอ Desktop GUI"""
    app = MainTradingApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
