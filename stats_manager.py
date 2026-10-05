"""
AI MetaTrader 5 Gold Pro - User & Plan Performance Analytics Engine
โมดูลเก็บและวิเคราะห์สถิติการเทรดแยกตาม User และแยกตาม Trading Plan (Plan 1–5)
เก็บบันทึกทั้งแบบ Local JSON, CSV และซิงค์ขึ้น Supabase Cloud Real-time
"""

import os
import json
import time
import csv
from datetime import datetime
import supabase_sync
import sys
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(BASE_DIR, "user_stats_store.json")
TRADE_CSV_FILE = os.path.join(BASE_DIR, "user_trade_history.csv")

# รายชื่อแผนการเทรดมาตรฐาน 5 แผนเฉพาะทองคำ
STANDARD_PLANS = [
    "Plan 1: SMC-LiquidityHunt",
    "Plan 2: SR-SwingBounce",
    "Plan 3: BB-H1-Reversion",
    "Plan 4: MA-Cross-Trend",
    "Plan 5: MA-Cross-H1-Trend"
]

def clean_plan_name(raw_plan: str) -> str:
    """จัดกลุ่มชื่อแผนให้ตรงกับมาตรฐาน 5 แผนหลัก"""
    p = str(raw_plan).strip()
    # จับจากชื่อแผนก่อน (ชื่ออย่าง "BB-H1-Reversion" / "MA-Cross-H1-Trend" มีเลข 1 อยู่ในคำว่า H1
    # ถ้าเช็คตัวเลขก่อนจะถูกจัดเป็น Plan 1 ผิด)
    if "SMC" in p or "Sweep" in p or "Hunt" in p:
        return "Plan 1: SMC-LiquidityHunt"
    if "Bounce" in p or "Swing" in p:
        return "Plan 2: SR-SwingBounce"
    if "BB" in p or "Reversion" in p:
        return "Plan 3: BB-H1-Reversion"
    if "Cross-H1" in p:
        return "Plan 5: MA-Cross-H1-Trend"
    if "Cross-Trend" in p or "MA-Cross" in p:
        return "Plan 4: MA-Cross-Trend"
    if "Breakout" in p:
        return "Manual/Other"  # แผน Breakout เดิมถูกนำออกจากระบบแล้ว
    # รูปแบบ "Plan N" เปล่า ๆ เป็นข้อมูลยุคเลขแผนเก่า (0 = SMC, 1 = Bounce)
    for n, name in (("0", "Plan 2: SMC-LiquidityHunt"), ("1", "Plan 2: SR-SwingBounce"),
                    ("3", "Plan 3: BB-H1-Reversion"), ("4", "Plan 4: MA-Cross-Trend"),
                    ("5", "Plan 5: MA-Cross-H1-Trend")):
        if f"Plan {n}" in p:
            return name
    return p or "Manual/Other"


_SUM_FIELDS = ("total_trades", "win_trades", "loss_trades", "total_profit_usd", "gross_profit_usd", "gross_loss_usd")


def migrate_plan_keys(plans: dict) -> dict:
    """
    ย้ายสถิติจากชื่อแผนเลขเก่า (Plan 1: SMC / Plan 2: Bounce) ไปชื่อใหม่ (Plan 2 / Plan 2)
    และตัดแผน Breakout ที่นำออกจากระบบแล้ว — รวมยอดถ้ามีทั้งชื่อเก่าและใหม่
    """
    out = {}
    for key, st in (plans or {}).items():
        if "Breakout" in key:
            continue
        new_key = clean_plan_name(key) if key.startswith("Plan ") else key
        st = dict(st or {})
        st["plan_name"] = new_key
        if new_key not in out:
            out[new_key] = st
            continue
        cur = out[new_key]
        for f in _SUM_FIELDS:
            cur[f] = (cur.get(f) or 0) + (st.get(f) or 0)
        cur["last_trade_time"] = max(str(cur.get("last_trade_time") or ""), str(st.get("last_trade_time") or ""))
        tt = cur.get("total_trades") or 0
        cur["win_rate_pct"] = round((cur.get("win_trades") or 0) / tt * 100, 2) if tt else 0.0
        gl = abs(cur.get("gross_loss_usd") or 0)
        cur["profit_factor"] = round((cur.get("gross_profit_usd") or 0) / gl, 2) if gl else 0.0
    return out


class StatsManager:
    """ระบบจัดการและบันทึกสถิติการเทรดแยกตาม User และแยกตาม Trading Plan"""
    def __init__(self):
        self.stats_data = {}
        self.load_stats()

    def load_stats(self):
        """โหลดข้อมูลสถิติจากไฟล์ JSON"""
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    self.stats_data = json.load(f)
                # ย้ายชื่อแผนเลขเก่า → เลขใหม่ (ครั้งเดียว แล้วบันทึกกลับ)
                changed = False
                for udata in self.stats_data.values():
                    if isinstance(udata, dict) and isinstance(udata.get("plans"), dict):
                        migrated = migrate_plan_keys(udata["plans"])
                        if migrated != udata["plans"]:
                            udata["plans"] = migrated
                            changed = True
                if changed:
                    self.save_stats()
            except Exception as e:
                print(f"[StatsManager] Error loading stats: {e}")
                self.stats_data = {}

    def save_stats(self):
        """บันทึกข้อมูลสถิติลงไฟล์ JSON"""
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.stats_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[StatsManager] Error saving stats: {e}")

    def _ensure_user_structure(self, user_id: str, email: str = ""):
        """สร้างโครงสร้างสถิติเริ่มต้นของ User หากยังไม่มี"""
        user_id = str(user_id or "local_user")
        if user_id not in self.stats_data:
            self.stats_data[user_id] = {
                "user_id": user_id,
                "email": email or f"{user_id}@aitrade24.local",
                "plans": {},
                "open_tickets": {},
                "overall": {
                    "total_trades": 0,
                    "win_trades": 0,
                    "loss_trades": 0,
                    "win_rate_pct": 0.0,
                    "total_profit_usd": 0.0,
                    "gross_profit_usd": 0.0,
                    "gross_loss_usd": 0.0,
                    "profit_factor": 0.0
                }
            }
        elif email and not self.stats_data[user_id].get("email"):
            self.stats_data[user_id]["email"] = email

        user_plans = self.stats_data[user_id].setdefault("plans", {})
        for p in STANDARD_PLANS:
            if p not in user_plans:
                user_plans[p] = {
                    "plan_name": p,
                    "total_trades": 0,
                    "win_trades": 0,
                    "loss_trades": 0,
                    "win_rate_pct": 0.0,
                    "total_profit_usd": 0.0,
                    "gross_profit_usd": 0.0,
                    "gross_loss_usd": 0.0,
                    "profit_factor": 0.0,
                    "last_trade_time": ""
                }

    def record_entry(self, user_id: str, email: str, ticket: int, symbol: str, raw_plan: str,
                     action: str, volume: float, price: float, sl: float = 0, tp: float = 0):
        """
        บันทึกการเข้าไม้ (Trade Entry):
        - นับจำนวนเข้าไม้ total_trades เพิ่มขึ้น 1
        - จดจำ Ticket ไว้ใน open_tickets เพื่อรอคำนวณผลตอนปิดไม้
        - บันทึกลง user_trade_history.csv
        - ส่ง Log ขึ้น Supabase Cloud พร้อม user_id
        """
        user_id = str(user_id or "local_user")
        plan_name = clean_plan_name(raw_plan)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._ensure_user_structure(user_id, email)

        # 1. อัปเดตสถิติการเข้าไม้
        p_stats = self.stats_data[user_id]["plans"].setdefault(plan_name, {
            "plan_name": plan_name,
            "total_trades": 0,
            "win_trades": 0,
            "loss_trades": 0,
            "win_rate_pct": 0.0,
            "total_profit_usd": 0.0,
            "gross_profit_usd": 0.0,
            "gross_loss_usd": 0.0,
            "profit_factor": 0.0,
            "last_trade_time": ""
        })
        p_stats["total_trades"] += 1
        p_stats["last_trade_time"] = now_str

        self.stats_data[user_id]["overall"]["total_trades"] += 1

        # 2. บันทึก Ticket ที่เปิดอยู่
        try:
            t_int = int(ticket or 0)
        except (ValueError, TypeError):
            t_int = 0

        if t_int > 0:
            self.stats_data[user_id]["open_tickets"][str(ticket)] = {
                "ticket": ticket,
                "plan_name": plan_name,
                "symbol": symbol,
                "action": action,
                "volume": volume,
                "open_price": price,
                "sl": sl,
                "tp": tp,
                "open_time": now_str
            }

        self.save_stats()

        # 3. บันทึกลงไฟล์ CSV สำหรับตรวจสอบ
        try:
            file_exists = os.path.exists(TRADE_CSV_FILE)
            with open(TRADE_CSV_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Time", "User_ID", "Email", "Ticket", "Symbol", "Action", "Plan", "Price", "Lot", "SL", "TP", "Profit"])
                writer.writerow([now_str, user_id, email, ticket, symbol, action, plan_name, price, volume, sl, tp, 0.0])
        except Exception as e:
            print(f"[StatsManager] CSV Error: {e}")

        # 4. ส่งข้อมูลขึ้น Cloud Supabase
        supabase_sync.log_trade(
            ticket=ticket, symbol=symbol, action=action, plan=plan_name,
            price=price, lot=volume, sl=sl, tp=tp, profit=0,
            comment=f"Entry {plan_name} | User: {email}",
            user_id=user_id, email=email
        )

    def record_close(self, ticket: int, profit: float, close_price: float = 0, reason: str = "",
                     user_id: str = None, fallback_plan: str = "Plan 1: SMC-LiquidityHunt"):
        """
        บันทึกผลเมื่อปิดไม้ (Trade Exit / TP Hit / SL Hit):
        - คำนวณ กำไร/ขาดทุน สุทธิ
        - นับ Win/Loss และคำนวณ Win Rate %
        - คำนวณ Profit Factor
        - อัปเดตสถิติทั้งระดับ User, Plan และบันทึกลง Cloud
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_user = None
        plan_name = clean_plan_name(fallback_plan)

        # 1. ค้นหา Ticket ใน open_tickets
        str_ticket = str(ticket)
        if user_id and str(user_id) in self.stats_data:
            target_user = str(user_id)
            if str_ticket in self.stats_data[target_user]["open_tickets"]:
                t_info = self.stats_data[target_user]["open_tickets"].pop(str_ticket)
                plan_name = t_info.get("plan_name", plan_name)
        else:
            # ค้นหาจากทุก User
            for uid, udata in self.stats_data.items():
                if str_ticket in udata.get("open_tickets", {}):
                    target_user = uid
                    t_info = udata["open_tickets"].pop(str_ticket)
                    plan_name = t_info.get("plan_name", plan_name)
                    break

        if not target_user:
            target_user = user_id or list(self.stats_data.keys())[0] if self.stats_data else "local_user"

        self._ensure_user_structure(target_user)
        email = self.stats_data[target_user].get("email", "")

        # 2. อัปเดตสถิติ Plan
        p_stats = self.stats_data[target_user]["plans"].setdefault(plan_name, {
            "plan_name": plan_name,
            "total_trades": 1,
            "win_trades": 0,
            "loss_trades": 0,
            "win_rate_pct": 0.0,
            "total_profit_usd": 0.0,
            "gross_profit_usd": 0.0,
            "gross_loss_usd": 0.0,
            "profit_factor": 0.0,
            "last_trade_time": now_str
        })

        if profit > 0:
            p_stats["win_trades"] += 1
            p_stats["gross_profit_usd"] = round(p_stats.get("gross_profit_usd", 0.0) + profit, 2)
            self.stats_data[target_user]["overall"]["win_trades"] += 1
            self.stats_data[target_user]["overall"]["gross_profit_usd"] = round(self.stats_data[target_user]["overall"].get("gross_profit_usd", 0.0) + profit, 2)
        elif profit < 0:
            p_stats["loss_trades"] += 1
            p_stats["gross_loss_usd"] = round(p_stats.get("gross_loss_usd", 0.0) + abs(profit), 2)
            self.stats_data[target_user]["overall"]["loss_trades"] += 1
            self.stats_data[target_user]["overall"]["gross_loss_usd"] = round(self.stats_data[target_user]["overall"].get("gross_loss_usd", 0.0) + abs(profit), 2)

        p_stats["total_profit_usd"] = round(p_stats.get("total_profit_usd", 0.0) + profit, 2)
        self.stats_data[target_user]["overall"]["total_profit_usd"] = round(self.stats_data[target_user]["overall"].get("total_profit_usd", 0.0) + profit, 2)

        # คำนวณ Win Rate %
        decided_trades = p_stats["win_trades"] + p_stats["loss_trades"]
        p_stats["win_rate_pct"] = round((p_stats["win_trades"] / decided_trades) * 100.0, 1) if decided_trades > 0 else 0.0

        # คำนวณ Profit Factor
        g_loss = p_stats.get("gross_loss_usd", 0.0)
        g_prof = p_stats.get("gross_profit_usd", 0.0)
        p_stats["profit_factor"] = round(g_prof / g_loss, 2) if g_loss > 0 else (round(g_prof, 2) if g_prof > 0 else 0.0)

        # คำนวณ Overall Win Rate & Profit Factor
        ov = self.stats_data[target_user]["overall"]
        ov_decided = ov["win_trades"] + ov["loss_trades"]
        ov["win_rate_pct"] = round((ov["win_trades"] / ov_decided) * 100.0, 1) if ov_decided > 0 else 0.0
        ov_gloss = ov.get("gross_loss_usd", 0.0)
        ov_gprof = ov.get("gross_profit_usd", 0.0)
        ov["profit_factor"] = round(ov_gprof / ov_gloss, 2) if ov_gloss > 0 else (round(ov_gprof, 2) if ov_gprof > 0 else 0.0)

        self.save_stats()

        # 3. บันทึก Close Row ลง CSV
        try:
            with open(TRADE_CSV_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([now_str, target_user, email, ticket, "XAUUSD", "CLOSE", plan_name, close_price, 0.0, 0.0, 0.0, round(profit, 2)])
        except Exception:
            pass

        # 4. ซิงค์สถิติขึ้น Supabase Cloud
        supabase_sync.sync_user_plan_stats(
            user_id=target_user,
            email=email,
            plan_name=plan_name,
            total_trades=p_stats["total_trades"],
            win_trades=p_stats["win_trades"],
            loss_trades=p_stats["loss_trades"],
            win_rate=p_stats["win_rate_pct"],
            total_profit=p_stats["total_profit_usd"],
            profit_factor=p_stats["profit_factor"]
        )

    def get_user_stats(self, user_id: str) -> dict:
        """ดึงสถิติของ User รายบุคคล สำหรับแสดงบน Dashboard"""
        user_id = str(user_id or "local_user")
        self._ensure_user_structure(user_id)
        return self.stats_data.get(user_id, {})

    def get_all_users_stats(self) -> dict:
        """ดึงสถิติของทุก User สำหรับ Admin Panel"""
        return self.stats_data

# Singleton Instance
stats_mgr = StatsManager()
