"""
AI MetaTrader 5 (FBS) Gold Pro - Desktop GUI Application
เวอร์ชัน: ดู version.py
หน้าจอ UI สำหรับเข้าใช้งานระบบ, ตรวจสอบสิทธิ์ชั่วโมง (Hours Metering), เติมชั่วโมงด้วย Product Key,
และควบคุมการเปิด/ปิดระบบเทรดอัตโนมัติ 100% Pure Gold Specialist (XAUUSD)
"""

import os
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
from version import APP_VERSION
import secure_store
import plan_config
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
            ("กำไรสุทธิรวม (Net Profit)", f"${tot_prof:+,.2f}", "คำนวณจากทุกไม้ที่ปิด", COLOR_SUCCESS_GREEN if tot_prof >= 0 else COLOR_DANGER_RED),
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
            ctk.CTkLabel(row_frame, text=f"${p_profit:+,.2f}", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=prof_colr).grid(row=0, column=4, padx=8)
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

        self.lbl_login_status.configure(text="กำลังสร้างบัญชีผู้ใช้ใหม่...", text_color=COLOR_GOLD_PRIMARY)
        self.update_idletasks()

        success, msg = license_mgr.register(email, pwd, display_name=display_name)
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
        self.btn_user_menu = ctk.CTkButton(
            h_inner,
            text=f"  {user_name}  ▾",
            font=self._font(12, "bold"),
            fg_color="#1A1E27",
            hover_color="#262B36",
            text_color=COLOR_TEXT_PRIMARY,
            height=38,
            width=40,
            corner_radius=19,
            command=self._open_user_menu,
        )
        self.btn_user_menu.pack(side="right")
        avatar = ctk.CTkLabel(
            h_inner, text=user_name[:1].upper(), font=self._font(14, "bold"), width=34, height=34,
            corner_radius=17, fg_color=COLOR_GOLD_WARM, text_color="#1A1406",
        )
        avatar.pack(side="right", padx=(0, 6))
        avatar.bind("<Button-1>", lambda e: self._open_user_menu())

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

        ctk.CTkButton(
            wallet, text="🔑 เติมคีย์", font=self._font(12, "bold"), fg_color="#2E2410", hover_color="#3A2E14",
            text_color=COLOR_GOLD_PRIMARY, border_width=1, border_color="#5A4519", height=32, width=86, corner_radius=8,
            command=self._open_redeem_modal,
        ).pack(side="left", padx=(0, 6))
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
        menu.add_command(label="  🔄  ตรวจสอบเวอร์ชันใหม่", command=lambda: self._start_update_check(manual=True))
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
            self.btn_update_status.configure(text=f"⬆ มีเวอร์ชันใหม่ v{latest} · ดาวน์โหลด", fg_color=COLOR_GOLD_WARM, text_color="#1A1406")
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
        notes = (info.get("changelog") or "").strip()
        bullets = [ln.strip()[2:] for ln in notes.splitlines() if ln.strip().startswith("- ")][:6]
        summary = "\n".join(f"• {b}" for b in bullets) or "ปรับปรุงประสิทธิภาพและแก้ไขข้อผิดพลาด"
        msg = (
            f"มีเวอร์ชันใหม่ v{info.get('latest_version')} (ใช้งานอยู่ v{APP_VERSION})\n\n"
            f"{summary}\n\nเปิดหน้าดาวน์โหลดตอนนี้หรือไม่?"
        )
        if messagebox.askyesno("มีเวอร์ชันใหม่ - AI Gold Commander Pro", msg):
            webbrowser.open(info.get("download_url") or self.DOWNLOAD_URL)

    def _build_metric_cards(self):
        """การ์ดสรุปสถานะพอร์ตและราคาทองคำ 4 กล่องแนวนอน"""
        grid_frame = ctk.CTkFrame(self.dashboard_view, fg_color="transparent")
        grid_frame.pack(fill="x", padx=14, pady=(0, 10))
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="metric_cards")

        self.card_mt5 = self._create_stat_card(grid_frame, 0, "🖥", "บัญชี MT5", "รอเชื่อมต่อ...", "Server: กำลังตรวจสอบ", COLOR_CYAN_ACCENT)
        self.card_balance = self._create_stat_card(grid_frame, 1, "💰", "ยอดเงินในพอร์ต", "$0.00", "Equity $0.00 · Float $0.00", COLOR_SUCCESS_GREEN)
        self.card_gold = self._create_stat_card(grid_frame, 2, "🏆", "ราคาทองคำ XAUUSD", "0.00", "Spread 0 pts", COLOR_GOLD_PRIMARY)
        self.card_trend = self._create_stat_card(grid_frame, 3, "📊", "สภาวะตลาด H4", "รอเริ่มบอท", "วิเคราะห์เมื่อบอททำงาน", COLOR_GOLD_WARM)

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
        return {"val_lbl": val_label, "sub_lbl": sub_label}

    # ---------------------------------------------------------------------
    # คอลัมน์ขวา: ควบคุมบอท / ข่าวถัดไป / แผนเทรด
    # ---------------------------------------------------------------------
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

        # สถิติย่อ 3 ช่อง: ออเดอร์เปิดอยู่ / กำไรลอยตัว / เวลาทำงาน
        stats = ctk.CTkFrame(card, fg_color="#101218", corner_radius=10)
        stats.pack(fill="x", padx=14, pady=(8, 0))
        stats.grid_columnconfigure((0, 1, 2), weight=1, uniform="ctl_stats")
        self.ctl_stat_labels = {}
        for col, (key, title, init) in enumerate((("open", "ออเดอร์", "0"), ("float", "กำไรลอยตัว", "$0.00"), ("uptime", "เวลาทำงาน", "--:--:--"))):
            box = ctk.CTkFrame(stats, fg_color="transparent")
            box.grid(row=0, column=col, sticky="nsew", pady=5)
            ctk.CTkLabel(box, text=title, font=self._font(10), text_color=COLOR_TEXT_MUTED, height=16).pack()
            val = ctk.CTkLabel(box, text=init, font=self._font(14, "bold"), text_color=COLOR_TEXT_PRIMARY, height=22)
            val.pack()
            self.ctl_stat_labels[key] = val
            if key == "open":  # กดจำนวนออเดอร์ → ไปแท็บออเดอร์ที่เปิดอยู่
                for w in (box, val):
                    w.configure(cursor="hand2")
                    w.bind("<Button-1>", lambda e: self.main_tabs.set(self.TAB_POSITIONS))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(8, 12))
        row.grid_columnconfigure(0, weight=1)
        self.btn_close_all = ctk.CTkButton(
            row,
            text="⚠ ปิดทุกออเดอร์",
            font=self._font(12, "bold"),
            fg_color="#3A2226",
            hover_color="#4A2A2F",
            text_color=COLOR_DANGER_RED,
            text_color_disabled="#6E5458",
            height=32,
            corner_radius=8,
            state="disabled",
            command=self._on_click_close_all,
        )
        self.btn_close_all.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.btn_sound_toggle = ctk.CTkButton(
            row,
            text="🔊",
            font=ctk.CTkFont(size=15),
            fg_color="#262B36",
            hover_color="#323846",
            width=42,
            height=32,
            corner_radius=8,
            command=self._on_toggle_sound,
        )
        self.btn_sound_toggle.grid(row=0, column=1)
        self._bot_started_at = None

    def _build_next_news_card(self, parent):
        card = self._card(parent, fill="x", pady=(0, 8))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=14, pady=(8, 10))
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
        ("⚡", "P0 · SMC Hunt", "Plan 0: SMC-LiquidityHunt"),
        ("🎯", "P1 · SR Bounce", "Plan 1: SR-SwingBounce"),
        ("🌊", "P3 · BB-H1", "Plan 3: BB-H1-Reversion"),
        ("📈", "P4 · MA M15", "Plan 4: MA-Cross-Trend"),
        ("👑", "P5 · MA H1", "Plan 5: MA-Cross-H1-Trend"),
    ]

    def _build_plans_card(self, parent):
        card = self._card(parent, fill="both", expand=True)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(8, 4))
        ctk.CTkLabel(head, text="⚡ ผลงาน 5 แผนเทรด", font=self._font(13, "bold"), text_color=COLOR_TEXT_PRIMARY).pack(side="left")
        ctk.CTkButton(
            head, text="ละเอียด ›", font=self._font(11, "bold"), fg_color="transparent", hover_color="#1F2430",
            text_color=COLOR_CYAN_ACCENT, width=64, height=24, corner_radius=6, command=self._open_user_stats_modal,
        ).pack(side="right")

        table = ctk.CTkFrame(card, fg_color="#101218", corner_radius=10)
        table.pack(fill="x", padx=14, pady=(0, 10))
        table.grid_columnconfigure(0, weight=1)
        for col, (title, anchor) in enumerate((("แผน", "w"), ("ไม้", "e"), ("WR", "e"), ("กำไร", "e"))):
            ctk.CTkLabel(table, text=title, font=self._font(10, "bold"), text_color=COLOR_TEXT_MUTED, anchor=anchor, height=18).grid(
                row=0, column=col, sticky="ew", padx=(12 if col == 0 else 4, 12 if col == 3 else 4), pady=(4, 0)
            )

        # plan_stat_badges: {ชื่อแผนเต็ม: (label ไม้, label WR, label กำไร)}
        self.plan_stat_badges = {}
        for r, (icon, short, full) in enumerate(self.PLAN_ROWS, start=1):
            last = r == len(self.PLAN_ROWS)
            pady = (0, 4) if last else 0
            ctk.CTkLabel(table, text=f"{icon}  {short}", font=self._font(11, "bold"), text_color=COLOR_TEXT_PRIMARY, anchor="w", height=21).grid(
                row=r, column=0, sticky="ew", padx=(12, 4), pady=pady
            )
            cells = []
            for col in (1, 2, 3):
                lbl = ctk.CTkLabel(table, text="0" if col == 1 else ("—" if col == 2 else "$0.00"), font=self._font(11), text_color=COLOR_TEXT_MUTED, anchor="e", height=21, width=40 if col < 3 else 64)
                lbl.grid(row=r, column=col, sticky="e", padx=(4, 12 if col == 3 else 4), pady=pady)
                cells.append(lbl)
            self.plan_stat_badges[full] = tuple(cells)

    # ---------------------------------------------------------------------
    # คอลัมน์ซ้าย: แท็บ Console / ประวัติเทรด / ปฏิทินข่าว
    # ---------------------------------------------------------------------
    TAB_CONSOLE = "🖥  Console"
    TAB_POSITIONS = "📌  ออเดอร์ที่เปิดอยู่"
    TAB_HISTORY = "📋  ประวัติการเทรด"
    TAB_CALENDAR = "📅  ปฏิทินเศรษฐกิจ"

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
        for name in (self.TAB_CONSOLE, self.TAB_POSITIONS, self.TAB_HISTORY, self.TAB_CALENDAR):
            self.main_tabs.add(name)

        self._build_terminal_console(self.main_tabs.tab(self.TAB_CONSOLE))
        self._build_positions_tab(self.main_tabs.tab(self.TAB_POSITIONS))
        self._build_history_tab(self.main_tabs.tab(self.TAB_HISTORY))
        self._build_calendar_tab(self.main_tabs.tab(self.TAB_CALENDAR))
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

        self._small_button(bar, "ล้าง", self._clear_console, width=48).pack(side="right")
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

        for text, tag in (
            (f"🏆 AI Gold Commander Pro v{APP_VERSION}\n", "close"),
            ("XAUUSD · RRR 1:1.50 · SL 0.75 ATR · คิดเวลา 1 บาท/ชม. เฉพาะตอนบอททำงาน\n", "muted"),
            ("กด ▶ เริ่มการทำงานบอท ด้านขวาเพื่อเริ่มสแกนตลาด — ที่นี่จะแสดงเฉพาะเหตุการณ์สำคัญ (เปิด/ปิดออเดอร์ ฯลฯ)\n\n", "muted"),
        ):
            self._console_entries.append((text, tag, "key"))
            self.txt_console.insert("end", text, tag)
        self.txt_console.configure(state="disabled")

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
                f"{'+' if profit >= 0 else '-'}${abs(profit):,.2f}",
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
                text=f"{len(positions)} ไม้ (BUY {buys} · SELL {sells}) · รวม {total_lot:.2f} Lot · กำไรลอยตัว {'+' if total_profit >= 0 else '-'}${abs(total_profit):,.2f}",
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
    HISTORY_PAGE_SIZE = 5
    HISTORY_COLUMNS = [
        ("เวลาเปิด (MT5)", 96, "w"),
        ("ฝั่ง", 40, "center"),
        ("แผน", 140, "w"),
        ("Lot", 36, "e"),
        ("ราคาเข้า", 72, "e"),
        ("ราคาออก", 72, "e"),
        ("สถานะ", 64, "center"),
        ("กำไร", 76, "e"),
    ]

    def _build_history_tab(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=6, pady=(0, 8))
        self.lbl_history_summary = ctk.CTkLabel(top, text="กำลังโหลดประวัติจาก MT5...", font=self._font(12), text_color=COLOR_TEXT_MUTED)
        self.lbl_history_summary.pack(side="left")
        self._small_button(top, "🔄 รีเฟรช", lambda: self._refresh_history_async(force=True), width=80).pack(side="right")

        table = ctk.CTkFrame(parent, fg_color="#101218", corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        table.pack(fill="x", padx=6)
        for col, (_, width, _) in enumerate(self.HISTORY_COLUMNS):
            table.grid_columnconfigure(col, minsize=width, weight=1 if col == 2 else 0)

        for col, (title, _, anchor) in enumerate(self.HISTORY_COLUMNS):
            ctk.CTkLabel(table, text=title, font=self._font(11, "bold"), text_color=COLOR_TEXT_MUTED, anchor=anchor).grid(
                row=0, column=col, sticky="ew", padx=6, pady=(10, 6)
            )
        ctk.CTkFrame(table, fg_color=COLOR_CARD_BORDER, height=1).grid(row=1, column=0, columnspan=len(self.HISTORY_COLUMNS), sticky="ew", padx=6)

        # สร้างแถวไว้ล่วงหน้า 5 แถว แล้วอัปเดตข้อความแทนการสร้างใหม่ (ลื่นกว่า)
        self.history_cells = []
        for r in range(self.HISTORY_PAGE_SIZE):
            cells = []
            for col, (_, _, anchor) in enumerate(self.HISTORY_COLUMNS):
                lbl = ctk.CTkLabel(table, text="", font=self._font(12), text_color=COLOR_TEXT_PRIMARY, anchor=anchor, height=34)
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
            f" · เปิดอยู่ {open_count} · กำไรสุทธิ {'+' if net >= 0 else '-'}${abs(net):,.2f}",
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
                "เปิดอยู่" if is_open else "ปิดแล้ว",
                f"{'+' if profit >= 0 else '-'}${abs(profit):,.2f}",
            ]
            colors = [
                COLOR_TEXT_MUTED,
                COLOR_SUCCESS_GREEN if r.get("side") == "BUY" else COLOR_DANGER_RED,
                COLOR_TEXT_PRIMARY,
                COLOR_TEXT_PRIMARY,
                COLOR_TEXT_PRIMARY,
                COLOR_TEXT_PRIMARY,
                COLOR_CYAN_ACCENT if is_open else COLOR_TEXT_MUTED,
                COLOR_SUCCESS_GREEN if profit > 0 else (COLOR_DANGER_RED if profit < 0 else COLOR_TEXT_MUTED),
            ]
            for c, v, color in zip(cells, values, colors):
                c.configure(text=v, text_color=color)

        self.lbl_history_empty.configure(text="" if total else "ยังไม่มีประวัติการเทรด XAUUSD ใน 90 วันที่ผ่านมา")
        self.lbl_history_page.configure(text=f"หน้า {self._history_page + 1} / {pages}  ·  ทั้งหมด {total} ไม้")
        self.btn_history_prev.configure(state="normal" if self._history_page > 0 else "disabled")
        self.btn_history_next.configure(state="normal" if self._history_page < pages - 1 else "disabled")

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
        self._small_button(bar, "🔄", lambda: self._refresh_calendar_async(force=True), width=36).pack(side="right", padx=(0, 8))

        self.cal_list = ctk.CTkScrollableFrame(parent, fg_color="#101218", corner_radius=10, border_width=1, border_color=COLOR_CARD_BORDER)
        self.cal_list.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        self.cal_list.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            parent,
            text="เวลาไทย (UTC+7) · ข้อมูลข่าวเศรษฐกิจรายสัปดาห์ อัปเดตทุก 30 นาที",
            font=self._font(10),
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w", padx=8)

    def _refresh_calendar_async(self, force=False):
        if self._calendar_loading:
            return
        self._calendar_loading = True

        def worker():
            self._calendar_events = econ_calendar.fetch_events(force=force)
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
            ctk.CTkLabel(self.cal_list, text=ev["title"], font=self._font(12), text_color=fg, anchor="w").grid(row=row, column=3, sticky="ew", padx=6)
            ctk.CTkLabel(self.cal_list, text=f"คาด {ev['forecast'] or '—'}", font=self._font(11), text_color=COLOR_TEXT_MUTED, width=80, anchor="e").grid(row=row, column=4, padx=4)
            ctk.CTkLabel(self.cal_list, text=f"ก่อน {ev['previous'] or '—'}", font=self._font(11), text_color=COLOR_TEXT_MUTED, width=84, anchor="e").grid(row=row, column=5, padx=(4, 12))
            row += 1

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
            if not success:
                messagebox.showwarning("ไม่สามารถเริ่มบอทได้", msg)
        elif bot_ctrl.is_paused:
            # กลับมาทำงานต่อ
            success, msg = bot_ctrl.resume_bot()
            if not success:
                messagebox.showwarning("ไม่สามารถดำเนินการได้", msg)
        else:
            # หยุดชั่วคราว
            bot_ctrl.pause_bot()

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

    def _on_click_close_all(self):
        """กดปุ่ม Emergency ปิดทุกออเดอร์ทันที"""
        confirm = messagebox.askyesno(
            "ยืนยันการปิดออเดอร์ทั้งหมด",
            "⚠️ ท่านต้องการสั่งปิดทุกออเดอร์ของทองคำ XAUUSD ทันทีหรือไม่?\n(คำสั่งนี้ไม่สามารถยกเลิกได้)"
        )
        if confirm:
            count, msg = bot_ctrl.close_all_positions()
            messagebox.showinfo("ผลการดำเนินการ", msg)

    def _on_toggle_sound(self):
        """เปิดหรือปิดเสียงแจ้งเตือน"""
        bot_ctrl.sound_enabled = not bot_ctrl.sound_enabled
        if bot_ctrl.sound_enabled:
            self.btn_sound_toggle.configure(text="🔊", fg_color="#262B36")
            sound_manager.play_tp_hit()
        else:
            self.btn_sound_toggle.configure(text="🔇", fg_color="#3A2226")

    def _on_toggle_autoscroll(self):
        self.auto_scroll_logs = self.chk_autoscroll.get()

    def _clear_console(self):
        self._console_entries.clear()
        self.txt_console.configure(state="normal")
        self.txt_console.delete("1.0", "end")
        self.txt_console.configure(state="disabled")

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
                    self.card_balance["val_lbl"].configure(text=f"${bal:,.2f}")
                    self.card_balance["sub_lbl"].configure(text=f"Equity ${eq:,.2f} · Float {flt_sign}${flt:.2f}")

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
                h4_pct = radar.get("h4_diff_pct", 0.0)
                if hasattr(self, 'card_trend'):
                    trend_color = COLOR_GOLD_WARM
                    if "BULL" in h4_trend:
                        trend_color = COLOR_SUCCESS_GREEN
                    elif "BEAR" in h4_trend:
                        trend_color = COLOR_DANGER_RED
                    elif "SIDEWAY" in h4_trend:
                        trend_color = COLOR_CYAN_ACCENT

                    self.card_trend["val_lbl"].configure(text=h4_trend, text_color=trend_color)
                    self.card_trend["sub_lbl"].configure(text=f"H4 MA10/30 {h4_pct:+.2f}% · Strict Pro-Trend")

                # อัปเดตสถิติ 5 แผน (ตาราง: ไม้ / WR / กำไร)
                if hasattr(self, 'plan_stat_badges'):
                    cur_u = license_mgr.get_current_user()
                    u_plans = stats_mgr.get_user_stats(cur_u.get("user_id")).get("plans", {})
                    for full_pname, (lbl_tr, lbl_wr, lbl_pf) in self.plan_stat_badges.items():
                        ps = u_plans.get(full_pname, {})
                        tr = ps.get("total_trades", 0)
                        wr = ps.get("win_rate_pct", 0.0)
                        prof = ps.get("total_profit_usd", 0.0)
                        lbl_tr.configure(text=str(tr), text_color=COLOR_TEXT_PRIMARY if tr else COLOR_TEXT_MUTED)
                        if not plan_config.is_enabled(full_pname.split(": ", 1)[-1]):
                            lbl_wr.configure(text="ปิด", text_color=COLOR_DANGER_RED)  # ปิดโดยผู้ดูแลระบบ
                        else:
                            lbl_wr.configure(text=f"{wr:.0f}%" if tr else "—", text_color=COLOR_GOLD_PRIMARY if tr else COLOR_TEXT_MUTED)
                        lbl_pf.configure(
                            text=f"{'+' if prof >= 0 else '-'}${abs(prof):.2f}",
                            text_color=COLOR_SUCCESS_GREEN if prof > 0 else (COLOR_DANGER_RED if prof < 0 else COLOR_TEXT_MUTED),
                        )

                # ออเดอร์ที่เปิดอยู่ (อัปเดตทุก ~1 วินาที)
                if hasattr(self, 'positions_body') and self._ui_tick % 2 == 0:
                    self._render_positions(telemetry.get("open_positions"), telemetry.get("server_time", 0))

                # สถิติย่อในแผงควบคุม
                if hasattr(self, 'ctl_stat_labels'):
                    n_open = len(telemetry.get("open_positions") or [])
                    self.ctl_stat_labels["open"].configure(text=str(n_open), text_color=COLOR_CYAN_ACCENT if n_open else COLOR_TEXT_PRIMARY)
                    self.ctl_stat_labels["float"].configure(
                        text=f"{'+' if flt >= 0 else '-'}${abs(flt):,.2f}",
                        text_color=COLOR_SUCCESS_GREEN if flt > 0 else (COLOR_DANGER_RED if flt < 0 else COLOR_TEXT_PRIMARY),
                    )
                    if self._bot_started_at and bot_ctrl.is_active and not bot_ctrl.is_paused:
                        el = int(time.time() - self._bot_started_at)
                        self.ctl_stat_labels["uptime"].configure(text=f"{el // 3600:02d}:{el % 3600 // 60:02d}:{el % 60:02d}", text_color=COLOR_SUCCESS_GREEN)
                    elif not bot_ctrl.is_active:
                        self.ctl_stat_labels["uptime"].configure(text="--:--:--", text_color=COLOR_TEXT_MUTED)
                    self.btn_close_all.configure(
                        state="normal" if n_open else "disabled",
                        text=f"⚠ ปิดทุกออเดอร์ ({n_open})" if n_open else "⚠ ปิดทุกออเดอร์",
                    )

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
