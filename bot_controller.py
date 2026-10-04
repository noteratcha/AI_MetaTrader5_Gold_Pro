import threading
import time
import sys
import queue
import re
import MetaTrader5 as mt5
import multi_asset_ai_bot as bot_core
from license_manager import license_mgr

class OutputRedirector:
    """ดักจับและส่งต่อข้อความ print() จากบอทไปยัง Queue ของ GUI"""
    def __init__(self, log_queue, orig_stdout):
        self.log_queue = log_queue
        self.orig_stdout = orig_stdout
        self.ansi_regex = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def write(self, text):
        if text:
            # พิมพ์ลงคอนโซลจริงคู่ขนานไปด้วย
            try:
                self.orig_stdout.write(text)
                self.orig_stdout.flush()
            except Exception:
                pass
            # ตัด ANSI escape code สำหรับ GUI
            clean_text = self.ansi_regex.sub('', text)
            if clean_text:
                self.log_queue.put(clean_text)

    def flush(self):
        try:
            self.orig_stdout.flush()
        except Exception:
            pass


class BotController:
    """ตัวควบคุมการทำงานของบอทเทรด สำหรับเชื่อมต่อกับ GUI"""
    def __init__(self):
        self.bot_thread = None
        self.metering_thread = None
        self.log_queue = queue.Queue()
        self.is_active = False
        self.is_paused = False
        self.time_expired_callback = None
        self.status_callback = None
        self.last_meter_time = 0
        self.sound_enabled = True

        # ติดตั้งตัวดักจับ stdout
        self.orig_stdout = sys.stdout
        self.redirector = OutputRedirector(self.log_queue, self.orig_stdout)

    def set_time_expired_callback(self, cb):
        self.time_expired_callback = cb

    def set_status_callback(self, cb):
        self.status_callback = cb

    def start_bot(self) -> tuple[bool, str]:
        """เริ่มต้นการทำงานของบอทในเธรดเบื้องหลัง"""
        if self.is_active and not self.is_paused:
            return False, "บอทกำลังทำงานอยู่แล้ว"

        if not license_mgr.is_authenticated:
            return False, "กรุณาเข้าสู่ระบบก่อนเริ่มต้นใช้งานบอท"

        if not license_mgr.has_active_hours():
            return False, "เวลาใช้งานหมดแล้ว! กรุณาเติมชั่วโมงด้วย Product Key ก่อนเริ่มต้น"

        # เปลี่ยนเส้นทาง stdout ไปยัง GUI
        sys.stdout = self.redirector

        bot_core.BOT_RUNNING_FLAG = True
        bot_core.BOT_PAUSED_FLAG = False
        self.is_active = True
        self.is_paused = False

        if self.bot_thread is None or not self.bot_thread.is_alive():
            self.bot_thread = threading.Thread(target=self._run_bot_thread, daemon=True)
            self.bot_thread.start()

        # เริ่มต้นเธรดตัดชั่วโมงการใช้งาน (Metering Thread - 60s per minute)
        if self.metering_thread is None or not self.metering_thread.is_alive():
            self.metering_thread = threading.Thread(target=self._run_metering_loop, daemon=True)
            self.metering_thread.start()

        if self.status_callback:
            self.status_callback("RUNNING")

        return True, "เริ่มต้นระบบบอท AI สำเร็จ"

    def pause_bot(self) -> tuple[bool, str]:
        """หยุดการทำงานชั่วคราว (บอทจะพักรอบและหยุดตัดชั่วโมง)"""
        if not self.is_active:
            return False, "บอทยังไม่ได้เริ่มต้นทำงาน"

        bot_core.BOT_PAUSED_FLAG = True
        self.is_paused = True

        if self.status_callback:
            self.status_callback("PAUSED")

        return True, "หยุดการทำงานชั่วคราวแล้ว (หยุดตัดเวลา)"

    def resume_bot(self) -> tuple[bool, str]:
        """กลับมาทำงานต่อหลังจากหยุดชั่วคราว"""
        if not self.is_active:
            return self.start_bot()

        if not license_mgr.is_authenticated:
            return False, "กรุณาเข้าสู่ระบบก่อนเริ่มต้นใช้งานบอท"

        if not license_mgr.has_active_hours():
            return False, "เวลาใช้งานหมดแล้ว! กรุณาเติมชั่วโมงก่อนกลับมาทำงาน"

        bot_core.BOT_PAUSED_FLAG = False
        self.is_paused = False

        if self.status_callback:
            self.status_callback("RUNNING")

        return True, "บอทกลับมาทำงานต่อแล้ว"

    def stop_bot(self):
        """สั่งปิดการทำงานของบอทโดยสมบูรณ์"""
        bot_core.BOT_RUNNING_FLAG = False
        bot_core.BOT_PAUSED_FLAG = False
        self.is_active = False
        self.is_paused = False

        # คืนค่า stdout เดิม
        sys.stdout = self.orig_stdout

        if self.status_callback:
            self.status_callback("STOPPED")

    def _run_bot_thread(self):
        """ฟังก์ชันรันเธรดหลักของบอท"""
        try:
            bot_core.main()
        except Exception as e:
            print(f"[BOT ENGINE ERROR] {e}")
        finally:
            self.is_active = False
            self.is_paused = False
            if self.status_callback:
                self.status_callback("STOPPED")

    def _run_metering_loop(self):
        """ลูปหักเวลาการใช้งานจริง (Metering Loop): หัก 1 นาที ทุกๆ 60 วินาทีขณะที่บอทเทรดจริง"""
        while True:
            time.sleep(1)
            if not self.is_active or self.is_paused:
                continue

            current_now = time.time()
            if self.last_meter_time == 0:
                self.last_meter_time = current_now

            # ครบ 60 วินาที ตัด 1 นาที
            if current_now - self.last_meter_time >= 60.0:
                self.last_meter_time = current_now
                has_time, remaining_mins, time_str = license_mgr.deduct_trading_minute()
                if not has_time:
                    print(f"\n[LICENSE] เวลาการใช้งานหมดลงแล้ว ({time_str} ชม.)! กำลังหยุดบอทอัตโนมัติ...")
                    self.pause_bot()
                    if self.time_expired_callback:
                        self.time_expired_callback()

    def get_telemetry(self) -> dict:
        """ดึงข้อมูลสถานะเรียลไทม์ของ MT5, พอร์ต และตลาดทองคำ"""
        data = {
            "is_connected": False,
            "login": 0,
            "server": "N/A",
            "balance": 0.0,
            "equity": 0.0,
            "free_margin": 0.0,
            "floating_profit": 0.0,
            "xau_bid": 0.0,
            "xau_ask": 0.0,
            "spread_pts": 0,
            "open_positions": [],
            "radar": bot_core.latest_radar_cache.get("XAUUSD", {}),
            "remaining_time": license_mgr.get_remaining_time_display(),
            "has_time": license_mgr.has_active_hours()
        }

        try:
            if not mt5.initialize():
                return data

            acc = mt5.account_info()
            if acc:
                data["is_connected"] = True
                data["login"] = acc.login
                data["server"] = acc.server
                data["balance"] = acc.balance
                data["equity"] = acc.equity
                data["free_margin"] = acc.margin_free
                data["floating_profit"] = acc.profit

            tick = mt5.symbol_info_tick("XAUUSD")
            if tick:
                data["xau_bid"] = tick.bid
                data["xau_ask"] = tick.ask
                sym_info = mt5.symbol_info("XAUUSD")
                if sym_info and sym_info.point > 0:
                    data["spread_pts"] = int(round((tick.ask - tick.bid) / sym_info.point))

            # รายการ Position ค้างอยู่
            positions = mt5.positions_get(symbol="XAUUSD")
            if positions:
                for pos in positions:
                    data["open_positions"].append({
                        "ticket": pos.ticket,
                        "type": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                        "volume": pos.volume,
                        "price_open": pos.price_open,
                        "profit": pos.profit,
                        "sl": pos.sl,
                        "tp": pos.tp,
                        "comment": pos.comment,
                        "price_current": pos.price_current,
                        "swap": pos.swap,
                        "time": int(pos.time),  # เวลาเปิดไม้ (เวลาเซิร์ฟเวอร์ MT5)
                    })
                tick_now = mt5.symbol_info_tick("XAUUSD")
                data["server_time"] = int(tick_now.time) if tick_now else 0
        except Exception:
            pass

        return data

    def close_position_by_ticket(self, ticket: int) -> tuple[bool, str]:
        """ปิดออเดอร์เดียวตาม ticket (ใช้ close_position ของบอท: บันทึกประวัติ/สถิติครบ)"""
        try:
            positions = mt5.positions_get(ticket=int(ticket))
            if not positions:
                return False, f"ไม่พบออเดอร์ #{ticket} (อาจถูกปิดไปแล้ว)"
            if bot_core.close_position(positions[0], comment="Manual Close (GUI)"):
                return True, f"ปิดออเดอร์ #{ticket} สำเร็จ"
            return False, f"ปิดออเดอร์ #{ticket} ไม่สำเร็จ — ดูรายละเอียดใน Console"
        except Exception as e:
            return False, f"เกิดข้อผิดพลาด: {e}"

    def close_all_positions(self) -> tuple[int, str]:
        """ฟังก์ชัน Emergency: ปิดทุกออเดอร์ในพอร์ตทันที"""
        try:
            if not mt5.initialize():
                return 0, "ไม่สามารถเชื่อมต่อ MT5 ได้"

            positions = mt5.positions_get(symbol="XAUUSD")
            if not positions:
                return 0, "ไม่มีออเดอร์ XAUUSD ที่เปิดค้างอยู่"

            closed_count = 0
            for pos in positions:
                # ใช้ close_position ของบอท (เลือก filling type ตามโบรกเกอร์ + บันทึกประวัติ/สถิติ)
                if bot_core.close_position(pos, comment="Emergency Close All"):
                    closed_count += 1

            return closed_count, f"ปิดออเดอร์สำเร็จทั้งหมด {closed_count} ไม้"
        except Exception as e:
            return 0, f"เกิดข้อผิดพลาดในการปิดออเดอร์: {e}"

    def get_trade_history(self, days: int = 90, symbol: str = "XAUUSD") -> list[dict]:
        """
        ประวัติการเข้าไม้/ปิดไม้จาก MT5 โดยตรง (จับคู่ Deal เข้า-ออกด้วย position_id)
        รวมไม้ที่ยังเปิดอยู่ — เรียงจากใหม่ไปเก่า
        """
        from datetime import datetime, timedelta
        trades = {}
        try:
            if mt5.terminal_info() is None and not mt5.initialize():
                return []
            deals = mt5.history_deals_get(datetime.now() - timedelta(days=days), datetime.now() + timedelta(days=1)) or []
            for d in deals:
                if d.symbol != symbol or d.entry not in (0, 1, 2):
                    continue
                t = trades.setdefault(d.position_id, {
                    "ticket": int(d.position_id), "side": "", "plan": "", "volume": 0.0,
                    "open_time": None, "open_price": 0.0, "close_time": None, "close_price": 0.0,
                    "profit": 0.0, "status": "OPEN",
                })
                t["profit"] += float(d.profit) + float(getattr(d, "commission", 0.0)) + float(getattr(d, "swap", 0.0))
                if d.entry == 0:  # DEAL_ENTRY_IN
                    t["side"] = "BUY" if d.type == 0 else "SELL"
                    t["plan"] = d.comment or ("Manual" if d.magic != 888999 else "")
                    t["volume"] = float(d.volume)
                    t["open_time"] = int(d.time)
                    t["open_price"] = float(d.price)
                else:  # DEAL_ENTRY_OUT / INOUT
                    t["close_time"] = int(d.time)
                    t["close_price"] = float(d.price)
                    t["close_reason"] = d.comment or ""
                    t["status"] = "CLOSED"

            # ไม้ที่ยังเปิดอยู่: ใช้กำไรลอยตัวปัจจุบัน
            for p in mt5.positions_get(symbol=symbol) or []:
                t = trades.setdefault(p.ticket, {"ticket": int(p.ticket), "close_time": None, "close_price": 0.0})
                t.update({
                    "side": "BUY" if p.type == 0 else "SELL",
                    "plan": p.comment or "Manual",
                    "volume": float(p.volume),
                    "open_time": int(p.time),
                    "open_price": float(p.price_open),
                    "profit": float(p.profit),
                    "status": "OPEN",
                })
        except Exception:
            return []

        rows = [t for t in trades.values() if t.get("open_time")]
        rows.sort(key=lambda t: t["close_time"] or t["open_time"], reverse=True)
        return rows

# Singleton Controller Instance
bot_ctrl = BotController()
