"""
AI MetaTrader 5 (FBS) Gold Pro - Desktop GUI Application
เวอร์ชัน: v2026.1004.2030
หน้าจอ UI สำหรับเข้าใช้งานระบบ, ตรวจสอบสิทธิ์ชั่วโมง (Hours Metering), เติมชั่วโมงด้วย Product Key,
และควบคุมการเปิด/ปิดระบบเทรดอัตโนมัติ 100% Pure Gold Specialist (XAUUSD)
"""

import os
import sys
import time
import queue
import webbrowser
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

        self.title("AI Gold Commander Pro - GoldBot24 (v2026.1004.2030)")
        self.geometry("1180x820")
        self.minsize(1050, 720)
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
            text="v2026.1004.2030 • GoldBot24 Cloud Service (1.00 THB/hr)",
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

        saved_user = license_mgr.session_data.get("email") or ""
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
        self.remember_var = tk.BooleanVar(value=license_mgr.session_data.get("remember_me", True))
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

        self._build_top_header()
        self._build_metric_cards()
        self._build_plans_and_controls()
        self._build_terminal_console()

        # ตรวจสอบอัปเดตเวอร์ชันซอฟต์แวร์อัตโนมัติแบบเงียบๆ หลังเปิดหน้าจอ 3 วินาที
        self.after(3000, lambda: self._check_app_updates(silent_if_latest=True))

    def _build_top_header(self):
        """แถบหัวด้านบน: โลโก้, เวลาคงเหลือ (ชั่วโมง.นาที) และโปรไฟล์ผู้ใช้"""
        header = ctk.CTkFrame(self.dashboard_view, fg_color=COLOR_CARD_BG, height=68, corner_radius=0)
        header.pack(fill="x", side="top", pady=(0, 10))

        h_inner = ctk.CTkFrame(header, fg_color="transparent")
        h_inner.pack(fill="both", expand=True, padx=20, pady=10)

        # โลโก้ซ้ายมือ
        brand_frame = ctk.CTkFrame(h_inner, fg_color="transparent")
        brand_frame.pack(side="left")

        ctk.CTkLabel(
            brand_frame,
            text="👑",
            font=ctk.CTkFont(size=24)
        ).pack(side="left", padx=(0, 8))

        brand_text_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        brand_text_box.pack(side="left")

        ctk.CTkLabel(
            brand_text_box,
            text="AI Gold Commander Pro",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=COLOR_GOLD_PRIMARY
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand_text_box,
            text="v2026.1004.2030 • 🪙 100% PURE GOLD SPECIALIST (XAUUSD) • GoldBot24",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="w")

        # ส่วนขวามือ: เวลาคงเหลือ (ชั่วโมง.นาที) และปุ่มเติมชั่วโมง
        right_frame = ctk.CTkFrame(h_inner, fg_color="transparent")
        right_frame.pack(side="right")

        # การ์ดแสดงชั่วโมงแบบเรืองแสง
        self.time_pill_frame = ctk.CTkFrame(
            right_frame,
            fg_color=COLOR_GOLD_BG,
            corner_radius=10,
            border_width=1,
            border_color="#785B12"
        )
        self.time_pill_frame.pack(side="left", padx=(0, 12))

        time_inner = ctk.CTkFrame(self.time_pill_frame, fg_color="transparent")
        time_inner.pack(padx=14, pady=6)

        ctk.CTkLabel(
            time_inner,
            text="⏳ เวลาคงเหลือ:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#FDE68A"
        ).pack(side="left", padx=(0, 6))

        # ตัวนับเวลาคงเหลือในรูปแบบ ชั่วโมง.นาที (HH.MM)
        hrs_str = license_mgr.get_remaining_time_display()
        self.lbl_header_hours = ctk.CTkLabel(
            time_inner,
            text=f"{hrs_str} ชม.",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=COLOR_GOLD_PRIMARY
        )
        self.lbl_header_hours.pack(side="left", padx=(0, 8))

        # ป้ายสถานะการตัดเวลา (Active / Deducting หรือ Idle)
        self.lbl_metering_status = ctk.CTkLabel(
            time_inner,
            text="⏸️ หยุดนับเวลา",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.lbl_metering_status.pack(side="left")

        # ปุ่มเติมชั่วโมงด้วย Key
        btn_redeem = ctk.CTkButton(
            right_frame,
            text="🔑 + เติมชั่วโมง",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLOR_GOLD_WARM,
            hover_color=COLOR_GOLD_DARK,
            text_color="#1A1406",
            height=36,
            corner_radius=8,
            command=self._open_redeem_modal
        )
        btn_redeem.pack(side="left", padx=(0, 8))

        # ปุ่มเช็คอัปเดตเวอร์ชัน
        btn_update = ctk.CTkButton(
            right_frame,
            text="🔄 อัปเดต",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#1A1E27",
            hover_color="#262B36",
            text_color="#60A5FA",
            width=70,
            height=36,
            corner_radius=8,
            command=self._check_app_updates
        )
        btn_update.pack(side="left", padx=(0, 10))

        # ป้ายชื่อผู้ใช้ และปุ่มออกจากระบบ
        user_name = license_mgr.session_data.get("username") or "User"
        user_chip = ctk.CTkFrame(right_frame, fg_color="#1A1E27", corner_radius=8)
        user_chip.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            user_chip,
            text=f"👤 {user_name}",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#E2E8F0"
        ).pack(padx=10, pady=6)

        btn_logout = ctk.CTkButton(
            right_frame,
            text="🚪 ออก",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#262B36",
            hover_color="#475569",
            width=50,
            height=34,
            corner_radius=6,
            command=self._do_logout
        )
        btn_logout.pack(side="left")

    def _build_metric_cards(self):
        """การ์ดสรุปสถานะพอร์ตและราคาทองคำ 4 กล่องแนวนอน"""
        grid_frame = ctk.CTkFrame(self.dashboard_view, fg_color="transparent")
        grid_frame.pack(fill="x", padx=20, pady=(0, 12))

        # ตั้งค่า Grid 4 คอลัมน์
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="metric_cards")

        # การ์ด 1: บัญชี MT5
        self.card_mt5 = self._create_stat_card(
            grid_frame, 0,
            icon="🖥️",
            title="บัญชี MT5 (Terminal)",
            val_text="รอเชื่อมต่อ...",
            sub_text="Server: กำลังตรวจสอบ",
            accent_color=COLOR_CYAN_ACCENT
        )

        # การ์ด 2: พอร์ตและ Balance
        self.card_balance = self._create_stat_card(
            grid_frame, 1,
            icon="💰",
            title="ยอดเงินในพอร์ต (Balance)",
            val_text="$0.00",
            sub_text="Equity: $0.00 | Free: $0.00",
            accent_color=COLOR_SUCCESS_GREEN
        )

        # การ์ด 3: ราคาทองคำ XAUUSD
        self.card_gold = self._create_stat_card(
            grid_frame, 2,
            icon="🪙",
            title="ราคาทองคำ (XAUUSD)",
            val_text="0.00",
            sub_text="Spread: 0 pts | M15 Active",
            accent_color=COLOR_GOLD_PRIMARY
        )

        # การ์ด 4: เทรนด์ใหญ่ H4 & H1
        self.card_trend = self._create_stat_card(
            grid_frame, 3,
            icon="📊",
            title="สภาวะตลาด (Market Regime)",
            val_text="ANALYZING...",
            sub_text="H1 Trend: กำลังคำนวณ",
            accent_color=COLOR_GOLD_WARM
        )

    def _create_stat_card(self, parent, col, icon, title, val_text, sub_text, accent_color):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        card.grid(row=0, column=col, padx=6, sticky="nsew")

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=12)

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(top_row, text=icon, font=ctk.CTkFont(size=18)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            top_row,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        ).pack(side="left")

        val_label = ctk.CTkLabel(
            inner,
            text=val_text,
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=accent_color
        )
        val_label.pack(anchor="w", pady=(6, 2))

        sub_label = ctk.CTkLabel(
            inner,
            text=sub_text,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED
        )
        sub_label.pack(anchor="w")

        return {"val_lbl": val_label, "sub_lbl": sub_label}

    def _build_plans_and_controls(self):
        """ส่วนแสดงแผนการเทรดเฉพาะทองคำ 5 แผน และแผงปุ่ม Master Control"""
        control_container = ctk.CTkFrame(self.dashboard_view, fg_color="transparent")
        control_container.pack(fill="x", padx=20, pady=(0, 12))

        control_container.grid_columnconfigure(0, weight=3) # แผนการเทรด 5 แผน
        control_container.grid_columnconfigure(1, weight=2) # ปุ่มควบคุม Master Start/Stop

        # 1. กล่องแผนการเทรดเฉพาะทองคำ (Trading Plans)
        plans_box = ctk.CTkFrame(control_container, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        plans_box.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        p_inner = ctk.CTkFrame(plans_box, fg_color="transparent")
        p_inner.pack(fill="both", expand=True, padx=14, pady=12)

        # หัวเรื่องและปุ่มดูสถิติ
        p_hdr = ctk.CTkFrame(p_inner, fg_color="transparent")
        p_hdr.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            p_hdr,
            text="⚡ แผนการเทรดเฉพาะทองคำ (Active Trading Plans)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(side="left")

        btn_my_stats = ctk.CTkButton(
            p_hdr,
            text="📊 ดูสถิติรายแผน (My Stats)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#1A1E27",
            hover_color="#262B36",
            text_color=COLOR_GOLD_PRIMARY,
            height=28,
            corner_radius=6,
            command=self._open_user_stats_modal
        )
        btn_my_stats.pack(side="right")

        badges_row = ctk.CTkFrame(p_inner, fg_color="transparent")
        badges_row.pack(fill="x")

        plans = [
            ("⚡ Plan 0", "SMC-LiquidityHunt", "กวาดสภาพคล่อง H1", "Plan 0: SMC-LiquidityHunt"),
            ("🎯 Plan 1", "SR-SwingBounce", "เด้งแนวรับต้าน + Div", "Plan 1: SR-SwingBounce"),
            ("🌊 Plan 3", "BB-H1-Reversion", "หลุดกรอบ H1 + MACD", "Plan 3: BB-H1-Reversion"),
            ("📈 Plan 4", "MA-Cross-Trend", "M15 MA5x10 (Run Trend)", "Plan 4: MA-Cross-Trend"),
            ("👑 Plan 5", "MA-Cross-H1", "H1 MA5x10 (Swing Run)", "Plan 5: MA-Cross-H1-Trend")
        ]

        self.plan_stat_badges = {}
        for p_code, p_name, p_desc, full_plan_name in plans:
            badge = ctk.CTkFrame(badges_row, fg_color="#1A1E27", corner_radius=8, border_width=1, border_color="#2D3B55")
            badge.pack(side="left", padx=4, expand=True, fill="x")

            ctk.CTkLabel(
                badge,
                text=p_code,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=COLOR_GOLD_PRIMARY
            ).pack(anchor="w", padx=8, pady=(4, 0))

            ctk.CTkLabel(
                badge,
                text=p_name,
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color=COLOR_TEXT_PRIMARY
            ).pack(anchor="w", padx=8)

            stat_lbl = ctk.CTkLabel(
                badge,
                text="เข้า: 0 | WR: 0% | $0.00",
                font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                text_color=COLOR_CYAN_ACCENT
            )
            stat_lbl.pack(anchor="w", padx=8, pady=(2, 4))
            self.plan_stat_badges[full_plan_name] = stat_lbl

        # 2. กล่องควบคุมการทำงานบอท (Master Bot Controls)
        master_box = ctk.CTkFrame(control_container, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        master_box.grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        m_inner = ctk.CTkFrame(master_box, fg_color="transparent")
        m_inner.pack(fill="both", expand=True, padx=14, pady=12)

        ctk.CTkLabel(
            m_inner,
            text="🎮 แผงควบคุมระบบ (Master Control)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 8))

        btn_row = ctk.CTkFrame(m_inner, fg_color="transparent")
        btn_row.pack(fill="x")

        # ปุ่ม Start / Pause บอทหลัก
        self.btn_master_toggle = ctk.CTkButton(
            btn_row,
            text="▶️ เริ่มต้นการทำงานบอท (START)",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=COLOR_SUCCESS_GREEN,
            hover_color="#059669",
            text_color="#FFFFFF",
            height=44,
            corner_radius=8,
            command=self._on_toggle_bot
        )
        self.btn_master_toggle.pack(side="left", expand=True, fill="x", padx=(0, 6))

        # ปุ่ม Emergency ปิดทุกออเดอร์
        self.btn_close_all = ctk.CTkButton(
            btn_row,
            text="⚠️ ปิดทุกไม้",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=COLOR_DANGER_RED,
            hover_color="#DC2626",
            text_color="#FFFFFF",
            width=90,
            height=44,
            corner_radius=8,
            command=self._on_click_close_all
        )
        self.btn_close_all.pack(side="left", padx=(0, 6))

        # ปุ่มเปิด/ปิดเสียง
        self.btn_sound_toggle = ctk.CTkButton(
            btn_row,
            text="🔊",
            font=ctk.CTkFont(size=16),
            fg_color="#262B36",
            hover_color="#475569",
            width=44,
            height=44,
            corner_radius=8,
            command=self._on_toggle_sound
        )
        self.btn_sound_toggle.pack(side="left")

    def _build_terminal_console(self):
        """คอนโซลแสดงผลสดการทำงานของบอท (Live Trading Terminal Console)"""
        console_frame = ctk.CTkFrame(self.dashboard_view, fg_color=COLOR_CARD_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        console_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        c_header = ctk.CTkFrame(console_frame, fg_color="transparent")
        c_header.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            c_header,
            text="🖥️ บันทึกการทำงานและสัญญาณเทรดสด (Live Terminal Console)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(side="left")

        # ตัวเลือกควบคุมคอนโซล
        c_controls = ctk.CTkFrame(c_header, fg_color="transparent")
        c_controls.pack(side="right")

        self.chk_autoscroll = ctk.CTkCheckBox(
            c_controls,
            text="เลื่อนอัตโนมัติ (Auto-scroll)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED,
            fg_color=COLOR_GOLD_WARM,
            hover_color=COLOR_GOLD_DARK,
            command=self._on_toggle_autoscroll
        )
        self.chk_autoscroll.select()
        self.chk_autoscroll.pack(side="left", padx=(0, 10))

        btn_clear = ctk.CTkButton(
            c_controls,
            text="ล้างข้อความ",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#1A1E27",
            hover_color="#262B36",
            width=70,
            height=26,
            corner_radius=6,
            command=self._clear_console
        )
        btn_clear.pack(side="left")

        # กล่อง Textbox แสดงผลคอนโซล
        self.txt_console = ctk.CTkTextbox(
            console_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0A0D14",
            text_color="#E2E8F0",
            corner_radius=8,
            border_width=1,
            border_color="#1E2638",
            wrap="word"
        )
        self.txt_console.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # ข้อความเริ่มต้น
        self.txt_console.insert(
            "end",
            f"=== 🪙 AI MetaTrader 5 (FBS) Gold Pro v2026.1004.2030 Started ===\n"
            f"• ระบบโฟกัสทองคำ XAUUSD แบบ 100% Specialist | Sweet Spot RRR 1:1.50 | SL 0.75 ATR\n"
            f"• ระบบคิดค่าบริการ 1 บาท/ชั่วโมง (นับเฉพาะเวลาเปิดบอท) | รูปแบบเวลาคงเหลือ: ชั่วโมง.นาที (HH.MM)\n"
            f"• กดปุ่ม '▶️ เริ่มต้นการทำงานบอท' เพื่อเริ่มการวิเคราะห์แท่งเทียน M15/H1 และเข้าเทรดอัตโนมัติ\n\n"
        )

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
        """อัปเดตสีและข้อความของปุ่ม Master เมื่อสถานะเปลี่ยน"""
        if status == "RUNNING":
            self.btn_master_toggle.configure(
                text="⏸️ หยุดชั่วคราว (PAUSE)",
                fg_color=COLOR_GOLD_WARM,
                hover_color=COLOR_GOLD_DARK,
                text_color="#1A1406"
            )
            self.lbl_metering_status.configure(
                text="🟢 กำลังตัดเวลา (-1 นาที/รอบ)",
                text_color=COLOR_SUCCESS_GREEN
            )
        elif status == "PAUSED":
            self.btn_master_toggle.configure(
                text="▶️ ทำงานต่อ (RESUME)",
                fg_color=COLOR_SUCCESS_GREEN,
                hover_color="#059669",
                text_color="#FFFFFF"
            )
            self.lbl_metering_status.configure(
                text="⏸️ หยุดนับเวลา (บอทพัก)",
                text_color=COLOR_TEXT_MUTED
            )
        else: # STOPPED
            self.btn_master_toggle.configure(
                text="▶️ เริ่มต้นการทำงานบอท (START)",
                fg_color=COLOR_SUCCESS_GREEN,
                hover_color="#059669",
                text_color="#FFFFFF"
            )
            self.lbl_metering_status.configure(
                text="⏸️ หยุดนับเวลา",
                text_color=COLOR_TEXT_MUTED
            )

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
            self.btn_sound_toggle.configure(text="🔇", fg_color=COLOR_DANGER_RED)

    def _on_toggle_autoscroll(self):
        self.auto_scroll_logs = self.chk_autoscroll.get()

    def _clear_console(self):
        self.txt_console.delete("1.0", "end")

    def _open_redeem_modal(self):
        """เปิดหน้าต่างเติมชั่วโมง Product Key"""
        RedeemKeyDialog(self, on_redeemed_callback=self._on_hours_updated)

    def _open_user_stats_modal(self):
        """เปิดหน้าต่างดูสถิติการเทรดละเอียดรายบุคคลและรายแผน"""
        UserStatsDialog(self)

    def _check_app_updates(self, silent_if_latest=False):
        """ตรวจสอบเวอร์ชันใหม่จาก Supabase app_releases"""
        current_ver = "2026.1004.2030"
        try:
            res = license_mgr.check_app_version(current_ver)
            if res.get("has_update"):
                latest_v = res.get("latest_version")
                notes = res.get("changelog") or "มีการปรับปรุงประสิทธิภาพและความแม่นยำของระบบ AI"
                url = res.get("download_url") or "https://goldbot24.vercel.app/store"
                msg = (
                    f"🎉 ตรวจพบเวอร์ชันใหม่ล่าสุด: v{latest_v}\n"
                    f"(เวอร์ชันที่ใช้งานอยู่: v{current_ver})\n\n"
                    f"บันทึกการเปลี่ยนแปลง (Changelog):\n{notes}\n\n"
                    f"ท่านต้องการเปิดลิงก์ดาวน์โหลดอัปเดตทันทีหรือไม่?"
                )
                if messagebox.askyesno("ตรวจพบการอัปเดตใหม่ - AI Gold Pro", msg):
                    webbrowser.open(url)
            else:
                if not silent_if_latest:
                    messagebox.showinfo(
                        "ตรวจสอบการอัปเดต - AI Gold Pro",
                        f"✨ ท่านกำลังใช้งานเวอร์ชันล่าสุดแล้ว\n\nเวอร์ชันปัจจุบัน: v{current_ver}\nสถานะ: พร้อมเทรดทองคำ 100%"
                    )
        except Exception as e:
            if not silent_if_latest:
                messagebox.showerror("เกิดข้อผิดพลาด", f"ไม่สามารถตรวจสอบอัปเดตได้: {e}")

    def _on_hours_updated(self, new_hrs_str: str):
        """อัปเดตเวลาบน Header เมื่อเติมชั่วโมงสำเร็จ"""
        self.lbl_header_hours.configure(text=f"{new_hrs_str} ชม.")

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
                full_chunk = "".join(lines)
                self.txt_console.insert("end", full_chunk)
                if self.auto_scroll_logs:
                    self.txt_console.see("end")

            # 2. ถ้าล็อกอินอยู่ ให้อัปเดตสถานะ Telemetry
            if self.is_logged_in and self.dashboard_view:
                telemetry = bot_ctrl.get_telemetry()

                # อัปเดตชั่วโมงคงเหลือ (ชั่วโมง.นาที)
                hrs_str = telemetry.get("remaining_time", "0.00")
                if hasattr(self, 'lbl_header_hours'):
                    self.lbl_header_hours.configure(text=f"{hrs_str} ชม.")

                # อัปเดตสถานะ MT5
                is_conn = telemetry.get("is_connected", False)
                acc_num = telemetry.get("login", 0)
                srv = telemetry.get("server", "N/A")
                if hasattr(self, 'card_mt5'):
                    if is_conn:
                        self.card_mt5["val_lbl"].configure(text=f"🟢 #{acc_num}", text_color=COLOR_SUCCESS_GREEN)
                        self.card_mt5["sub_lbl"].configure(text=f"Server: {srv} (Connected)")
                    else:
                        self.card_mt5["val_lbl"].configure(text="🔴 Disconnected", text_color=COLOR_DANGER_RED)
                        self.card_mt5["sub_lbl"].configure(text="กรุณาเปิด MT5 Terminal")

                # อัปเดต Balance & Equity
                bal = telemetry.get("balance", 0.0)
                eq = telemetry.get("equity", 0.0)
                free = telemetry.get("free_margin", 0.0)
                flt = telemetry.get("floating_profit", 0.0)
                if hasattr(self, 'card_balance'):
                    flt_sign = "+" if flt >= 0 else ""
                    self.card_balance["val_lbl"].configure(text=f"${bal:,.2f}")
                    self.card_balance["sub_lbl"].configure(text=f"Eq: ${eq:,.2f} | Float: {flt_sign}${flt:.2f}")

                # อัปเดตราคาทองคำ XAUUSD
                bid = telemetry.get("xau_bid", 0.0)
                ask = telemetry.get("xau_ask", 0.0)
                spd = telemetry.get("spread_pts", 0)
                if hasattr(self, 'card_gold') and bid > 0:
                    self.card_gold["val_lbl"].configure(text=f"{bid:,.2f}")
                    self.card_gold["sub_lbl"].configure(text=f"Ask: {ask:,.2f} | Spread: {spd} pts")

                # อัปเดตสภาวะตลาด H4 และ H1
                radar = telemetry.get("radar", {})
                h4_trend = radar.get("h4_trend", "ANALYZING...")
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
                    self.card_trend["sub_lbl"].configure(text=f"H4 Diff: {h4_pct:+.2f}% | Pro-Trend Active")

                # อัปเดตสถิติการเทรดสดบนป้ายแผนการเทรด 5 แผน
                if hasattr(self, 'plan_stat_badges'):
                    cur_u = license_mgr.get_current_user()
                    u_stats = stats_mgr.get_user_stats(cur_u.get("user_id"))
                    u_plans = u_stats.get("plans", {})
                    for full_pname, stat_lbl in self.plan_stat_badges.items():
                        ps = u_plans.get(full_pname, {})
                        tr = ps.get("total_trades", 0)
                        wr = ps.get("win_rate_pct", 0.0)
                        prof = ps.get("total_profit_usd", 0.0)
                        prof_sign = "+" if prof >= 0 else ""
                        stat_lbl.configure(text=f"เข้า: {tr} | WR: {wr:.0f}% | {prof_sign}${prof:.2f}")

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
