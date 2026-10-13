import threading
import time
import sys
import queue
import re
import MetaTrader5 as mt5
import multi_asset_ai_bot as bot_core
import mt5_algo
import instance_guard
import thai_time
import sound_manager
from license_manager import license_mgr
from mt5_terminal_manager import get_profile_magic_number, initialize_mt5, scan_installed_terminals, get_configured_terminal_path, set_configured_terminal_path
from app_paths import get_active_profile, list_profiles

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
        # สถานะตลาด (ดูจากความเคลื่อนไหวของ tick) — ตลาดปิดไม่นับชั่วโมง
        self.market_open = False
        self._last_tick_msc = 0
        self._last_tick_change = 0.0
        self.sound_enabled = True
        self._plans_status_cache = None
        self._plans_status_time = 0.0

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

        if getattr(license_mgr, "update_required", None):
            return False, license_mgr.update_required["message"]

        if not license_mgr.has_active_hours():
            return False, "เวลาใช้งานหมดแล้ว! กรุณาเติมชั่วโมงด้วย Product Key ก่อนเริ่มต้น"

        low = self._min_balance_message()
        if low:
            return False, low

        lock = self.account_lock_message()
        if lock:
            return False, lock

        # ปุ่ม Algo Trading ใน MT5 ต้องเปิด (ปิดอยู่ → กด Ctrl+E ให้อัตโนมัติ) — ไม่งั้นบอทส่งคำสั่ง/เลื่อน SL ไม่ได้
        algo_ok, algo_msg = mt5_algo.ensure_enabled()
        if not algo_ok:
            return False, algo_msg

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
        sound_manager.stop_volatility_siren()

        if self.status_callback:
            self.status_callback("PAUSED")

        return True, "หยุดการทำงานชั่วคราวแล้ว (หยุดตัดเวลา)"

    def resume_bot(self) -> tuple[bool, str]:
        """กลับมาทำงานต่อหลังจากหยุดชั่วคราว"""
        if not self.is_active:
            return self.start_bot()

        if not license_mgr.is_authenticated:
            return False, "กรุณาเข้าสู่ระบบก่อนเริ่มต้นใช้งานบอท"

        if getattr(license_mgr, "update_required", None):
            return False, license_mgr.update_required["message"]

        if not license_mgr.has_active_hours():
            return False, "เวลาใช้งานหมดแล้ว! กรุณาเติมชั่วโมงก่อนกลับมาทำงาน"

        low = self._min_balance_message()
        if low:
            return False, low

        lock = self.account_lock_message()
        if lock:
            return False, lock

        algo_ok, algo_msg = mt5_algo.ensure_enabled()
        if not algo_ok:
            return False, algo_msg

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
        sound_manager.stop_volatility_siren()

        # คืนค่า stdout เดิม
        sys.stdout = self.orig_stdout

        if self.status_callback:
            self.status_callback("STOPPED")

    def account_lock_message(self):
        """1 บัญชี MT5 ให้บอททำงานได้ 1 หน้าต่าง (กันหลาย Profile เข้าไม้ซ้ำบนบัญชีเดียวกัน) — คืนข้อความ หรือ None ถ้าจองได้"""
        try:
            if mt5.terminal_info() is None and not initialize_mt5():
                return None
            acc = mt5.account_info()
            if acc is None:
                return None
            ok, msg = instance_guard.acquire_account(acc.login)
            return None if ok else msg
        except Exception:
            return None

    def _min_balance_message(self):
        """ยอดเงิน (Equity) ต้องมีอย่างน้อย 25 USD ระบบถึงจะทำงาน — คืนข้อความเตือน หรือ None ถ้าผ่าน/อ่าน MT5 ไม่ได้"""
        try:
            import plan_config
            if mt5.terminal_info() is None and not initialize_mt5():
                return None   # ยังเชื่อม MT5 ไม่ได้ — ให้บอทแจ้งเรื่องการเชื่อมต่อเอง
            acc = mt5.account_info()
            if acc is None:
                return None
            usd = plan_config.account_usd(acc)
            if usd < plan_config.MIN_BALANCE_USD:
                return (f"ยอดเงินในบัญชี MT5 ต้องมีอย่างน้อย {plan_config.MIN_BALANCE_USD:.0f} USD ระบบถึงจะทำงาน\n"
                        f"บัญชี #{acc.login} มี {usd:,.2f} USD — กรุณาเติมเงินหรือเปลี่ยนบัญชีใน MT5")
        except Exception:
            return None
        return None

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

    MARKET_SYMBOL = "XAUUSD"
    MARKET_IDLE_SECONDS = 120  # ไม่มี tick ใหม่เกิน 2 นาที = ตลาดปิด (เสาร์-อาทิตย์/วันหยุด/ช่วงพักรายวัน)

    def get_gold_symbol(self) -> str:
        """คืนค่าสัญลักษณ์ทองคำที่ใช้งานอยู่ โดยซิงค์กับ bot_core อัตโนมัติ"""
        try:
            sym = bot_core.get_gold_symbol()
            self.MARKET_SYMBOL = sym
            return sym
        except Exception:
            return self.MARKET_SYMBOL

    def _check_market_open(self) -> bool:
        """ตลาดเปิด = โบรกเกอร์เปิดการเทรด และราคามี tick ใหม่อยู่ภายใน 2 นาที (ทองมี tick ตลอดเมื่อตลาดเปิด)"""
        try:
            sym_name = self.get_gold_symbol()
            tick = mt5.symbol_info_tick(sym_name)
            sym = mt5.symbol_info(sym_name)
        except Exception:
            tick = None
            sym = None
        if not tick or not sym:
            return False

        trade_mode = getattr(sym, "trade_mode", 4)
        if trade_mode == 0:  # SYMBOL_TRADE_MODE_DISABLED (ปิดเทรด)
            return False

        now = time.time()
        tick_epoch = thai_time.server_to_epoch(tick.time) if getattr(tick, "time", 0) else 0
        tick_age = (now - tick_epoch) if tick_epoch else 999999.0

        stamp = int(getattr(tick, "time_msc", 0) or 0)
        if stamp and stamp != self._last_tick_msc:
            if self._last_tick_msc or tick_age < self.MARKET_IDLE_SECONDS:
                self._last_tick_change = now
            self._last_tick_msc = stamp

        return (tick_age < self.MARKET_IDLE_SECONDS) and ((now - self._last_tick_change) < self.MARKET_IDLE_SECONDS)

    def _run_metering_loop(self):
        """
        ลูปหักเวลาการใช้งานจริง: หัก 1 นาที ทุก 60 วินาที
        เฉพาะตอนบอททำงาน (ไม่ Pause) และตลาดเปิดอยู่ — ตลาดปิดไม่นับชั่วโมง
        """
        while True:
            time.sleep(1)
            if not self.is_active or self.is_paused:
                self.last_meter_time = 0  # เริ่มนับใหม่เมื่อกลับมาทำงาน (ไม่หักทันทีหลัง Resume)
                continue

            was_open = self.market_open
            self.market_open = self._check_market_open()
            if self.market_open != was_open:
                if self.market_open:
                    print("[MARKET OPEN] ตลาดทองคำเปิดแล้ว — เริ่มนับชั่วโมงการใช้งาน")
                else:
                    print("[MARKET CLOSED] ตลาดทองคำปิดอยู่ — หยุดนับชั่วโมงการใช้งานชั่วคราว")
            if not self.market_open:
                self.last_meter_time = 0
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
            "has_time": license_mgr.has_active_hours(),
            "is_market_open": False
        }

        try:
            if not initialize_mt5():
                return data

            term = mt5.terminal_info()
            acc = mt5.account_info()
            if acc and term and term.connected:
                data["is_connected"] = True
                data["login"] = acc.login
                data["server"] = acc.server
                data["balance"] = acc.balance
                data["equity"] = acc.equity
                data["free_margin"] = acc.margin_free
                data["floating_profit"] = acc.profit
                self.market_open = self._check_market_open()
                data["is_market_open"] = self.market_open
            else:
                self.market_open = False
                data["is_market_open"] = False

            sym = self.get_gold_symbol()
            tick = mt5.symbol_info_tick(sym)
            if tick:
                data["xau_bid"] = float(tick.bid)
                data["xau_ask"] = float(tick.ask)
                sym_info = mt5.symbol_info(sym)
                if sym_info and sym_info.point > 0:
                    data["spread_pts"] = int(round((tick.ask - tick.bid) / sym_info.point))
            if not tick or data["xau_bid"] <= 0:
                rates_last = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 1)
                if rates_last is not None and len(rates_last) > 0:
                    last_c = float(rates_last[0]["close"])
                    data["xau_bid"] = last_c
                    data["xau_ask"] = last_c
            data["gold_symbol"] = sym
            data["radar"] = bot_core.latest_radar_cache.get(sym) or bot_core.latest_radar_cache.get("XAUUSD", {})

            # รายการ Position ค้างอยู่
            positions = mt5.positions_get(symbol=sym)
            if not positions:
                all_p = mt5.positions_get()
                if all_p:
                    gold_syms = {sym.upper(), "XAUUSD", "GOLD"}
                    positions = [p for p in all_p if p.symbol.upper() in gold_syms]
            if positions:
                si = mt5.symbol_info(sym)
                per_pt = (float(si.trade_tick_value) / float(si.trade_tick_size)) if si and si.trade_tick_size else 100.0
                for pos in positions:
                    side = 1 if pos.type == mt5.ORDER_TYPE_BUY else -1
                    data["open_positions"].append({
                        # กำไร/ขาดทุนถ้าราคาชน SL ตอนนี้ (บวก = SL ล็อกกำไรแล้ว) — None = ไม่มี SL
                        "sl_pnl": round((float(pos.sl) - float(pos.price_open)) * side * per_pt * float(pos.volume), 2) if pos.sl else None,
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
                tick_now = mt5.symbol_info_tick(sym)
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
            if not initialize_mt5():
                return 0, "ไม่สามารถเชื่อมต่อ MT5 ได้"

            sym = self.get_gold_symbol()
            positions = mt5.positions_get(symbol=sym)
            if not positions:
                all_p = mt5.positions_get()
                if all_p:
                    gold_syms = {sym.upper(), "XAUUSD", "GOLD"}
                    positions = [p for p in all_p if p.symbol.upper() in gold_syms]
            if not positions:
                return 0, f"ไม่มีออเดอร์ {sym} ที่เปิดค้างอยู่"

            closed_count = 0
            for pos in positions:
                # ใช้ close_position ของบอท (เลือก filling type ตามโบรกเกอร์ + บันทึกประวัติ/สถิติ)
                if bot_core.close_position(pos, comment="Emergency Close All"):
                    closed_count += 1

            return closed_count, f"ปิดออเดอร์สำเร็จทั้งหมด {closed_count} ไม้"
        except Exception as e:
            return 0, f"เกิดข้อผิดพลาดในการปิดออเดอร์: {e}"

    def get_trade_history(self, days: int = 90, symbol: str = None) -> list[dict]:
        """
        ประวัติการเข้าไม้/ปิดไม้จาก MT5 โดยตรง (จับคู่ Deal เข้า-ออกด้วย position_id)
        ผสานประวัติจาก user_trade_history.csv สำหรับไม้ที่ไม่อยู่ในประวัติ MT5 ปัจจุบัน (เช่น สลับโบรกเกอร์)
        รวมไม้ที่ยังเปิดอยู่ — เรียงจากใหม่ไปเก่า
        """
        if symbol is None or symbol == "XAUUSD":
            symbol = self.get_gold_symbol()
        gold_syms = {symbol.upper(), "XAUUSD", "GOLD"}
        from datetime import datetime, timedelta
        trades = {}
        try:
            if mt5.terminal_info() is not None or initialize_mt5():
                deals = mt5.history_deals_get(datetime.now() - timedelta(days=days), datetime.now() + timedelta(days=1)) or []
                for d in deals:
                    if d.symbol.upper() not in gold_syms or d.entry not in (0, 1, 2):
                        continue
                    t = trades.setdefault(d.position_id, {
                        "ticket": int(d.position_id), "side": "", "plan": "", "volume": 0.0,
                        "open_time": None, "open_price": 0.0, "close_time": None, "close_price": 0.0,
                        "profit": 0.0, "status": "OPEN",
                    })
                    t["profit"] += float(d.profit) + float(getattr(d, "commission", 0.0)) + float(getattr(d, "swap", 0.0))
                    if d.entry == 0:  # DEAL_ENTRY_IN
                        t["side"] = "BUY" if d.type == 0 else "SELL"
                        t["plan"] = d.comment or ("Manual" if d.magic == 0 else "")
                        t["volume"] = float(d.volume)
                        t["open_time"] = int(d.time)
                        t["open_price"] = float(d.price)
                    else:  # DEAL_ENTRY_OUT / INOUT
                        t["close_time"] = int(d.time)
                        t["close_price"] = float(d.price)
                        t["close_reason"] = d.comment or ""
                        t["close_code"] = int(getattr(d, "reason", -1))  # 0-2 ปิดเอง · 3 บอท · 4 SL · 5 TP · 6 Stop Out
                        t["status"] = "CLOSED"

                # ไม้ที่ยังเปิดอยู่: ใช้กำไรลอยตัวปัจจุบัน
                for p in mt5.positions_get() or []:
                    if p.symbol.upper() not in gold_syms:
                        continue
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
            pass

        # ผสานประวัติจาก user_trade_history.csv สำหรับไม้ที่ยังไม่มีใน trades
        try:
            import csv
            import os
            import thai_time
            from app_paths import data_path
            cur_user_id = ""
            try:
                from license_manager import license_mgr
                cur_user_id = str(license_mgr.get_current_user().get("user_id") or "").strip()
            except Exception:
                pass

            csv_path = data_path("user_trade_history.csv")
            if os.path.exists(csv_path) and os.path.getsize(csv_path) > 100:
                mt5_tickets = set(trades.keys())
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        u_id = str(r.get("User_ID") or "").strip()
                        if cur_user_id and u_id and u_id != cur_user_id:
                            continue
                        try:
                            ticket = int(r.get("Ticket") or 0)
                        except Exception:
                            continue
                        if not ticket or ticket in mt5_tickets:
                            continue

                        action = (r.get("Action") or "").strip()
                        time_str = (r.get("Time") or "").strip()
                        try:
                            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=thai_time.TH)
                            if (datetime.now(thai_time.TH) - dt).days > days:
                                continue
                            utc_ts = dt.timestamp()
                            server_ts = int(utc_ts + thai_time.server_offset_at(utc_ts))
                        except Exception:
                            continue

                        t = trades.setdefault(ticket, {
                            "ticket": ticket, "side": "", "plan": "", "volume": 0.01,
                            "open_time": None, "open_price": 0.0, "close_time": None, "close_price": 0.0,
                            "profit": 0.0, "status": "OPEN"
                        })
                        if action in ("BUY", "SELL"):
                            t["side"] = action
                            t["plan"] = r.get("Plan") or ""
                            try: t["volume"] = float(r.get("Lot") or 0.01)
                            except Exception: pass
                            t["open_time"] = server_ts
                            try: t["open_price"] = float(r.get("Price") or 0.0)
                            except Exception: pass
                        elif action in ("CLOSE", "TP_HIT", "SL_HIT"):
                            t["close_time"] = server_ts
                            try: t["profit"] = float(r.get("Profit") or 0.0)
                            except Exception: pass
                            try:
                                cp = float(r.get("Price") or 0.0)
                                if cp > 0: t["close_price"] = cp
                            except Exception: pass
                            if not t.get("plan"):
                                t["plan"] = r.get("Plan") or ""
                            t["status"] = "CLOSED"
                            t["close_reason"] = action
                            if t.get("open_time") is None:
                                t["open_time"] = server_ts
        except Exception:
            pass

        rows = [t for t in trades.values() if t.get("open_time")]
        rows.sort(key=lambda t: t["close_time"] or t["open_time"], reverse=True)
        return rows

    def get_live_candles(self, count: int = 16, symbol: str = None, extra: int = 50, timeframe: str = "M15"):
        """แท่งราคาล่าสุด count แท่ง (แท่งสุดท้าย = แท่งที่กำลังวิ่ง) พร้อมอินดิเคเตอร์ตาม Timeframe ที่เลือก (M15, H1, H4) + Bid/Ask ปัจจุบัน — None ถ้าเชื่อม MT5 ไม่ได้"""
        if symbol is None or symbol == "XAUUSD":
            symbol = self.get_gold_symbol()
        try:
            import math
            import pandas as pd
            if mt5.terminal_info() is None and not initialize_mt5():
                return None

            tf_upper = (timeframe or "M15").upper()
            if tf_upper == "H1":
                mt5_tf = mt5.TIMEFRAME_H1
                bar_seconds = 3600
                warmup = max(extra, 220)   # MA200 H1 (Plan 10) ต้องการ 200 แท่งก่อนแท่งแรกที่แสดง
            elif tf_upper == "H4":
                mt5_tf = mt5.TIMEFRAME_H4
                bar_seconds = 14400
                warmup = max(extra, 220)
            else:
                tf_upper = "M15"
                mt5_tf = mt5.TIMEFRAME_M15
                bar_seconds = 900
                warmup = max(extra, 60)

            rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, count + warmup)
            tick = mt5.symbol_info_tick(symbol)
            if rates is None or len(rates) == 0:
                return None

            df = pd.DataFrame(rates)
            closes = [float(r["close"]) for r in rates]
            highs = [float(r["high"]) for r in rates]
            lows = [float(r["low"]) for r in rates]
            if tick and tick.bid:
                closes[-1] = float(tick.bid)
                highs[-1] = max(highs[-1], closes[-1])
                lows[-1] = min(lows[-1], closes[-1])
            df["close"] = closes
            df["high"] = highs
            df["low"] = lows

            # บริบท S&R จาก position_chart
            ctx = None
            try:
                import position_chart
                ctx = position_chart._context()
            except Exception:
                pass

            def _clean(val):
                if val is None:
                    return None
                try:
                    v = float(val)
                    return None if (math.isnan(v) or math.isinf(v)) else v
                except Exception:
                    return None

            candles = []
            if tf_upper == "M15":
                # Plan 1 (MA-Cross-Trend): MA5, MA13, MA50
                ma5_s = df["close"].rolling(5).mean()
                ma13_s = df["close"].rolling(13).mean()
                ma50_s = df["close"].rolling(50).mean()
                for i in range(max(0, len(rates) - count), len(rates)):
                    r = rates[i]
                    c = closes[i]
                    candles.append({
                        "time": int(r["time"]),
                        "open": float(r["open"]),
                        "high": highs[i],
                        "low": lows[i],
                        "close": c,
                        "ma5": _clean(ma5_s.iloc[i]),
                        "ma13": _clean(ma13_s.iloc[i]),
                        "ma50": _clean(ma50_s.iloc[i]),
                    })
            elif tf_upper == "H1":
                # Plan 2: MA5, MA10, MA20
                ma5_s = df["close"].rolling(5).mean()
                ma10_s = df["close"].rolling(10).mean()
                ma20_s = df["close"].rolling(20).mean()
                # Plan 5: BB (SMA 20, 2 STD)
                bb_mid_s = df["close"].rolling(20).mean()
                bb_std_s = df["close"].rolling(20).std()
                bb_up_s = bb_mid_s + 2 * bb_std_s
                bb_lo_s = bb_mid_s - 2 * bb_std_s
                # Plan 6: SAR & EMA100
                sar_vals, _ = bot_core.psar_series(df["high"].values, df["low"].values, *bot_core.P6_SAR)
                ema100_s = df["close"].ewm(span=bot_core.P6_EXIT_EMA, adjust=False).mean()
                ma200_h1_s = df["close"].rolling(200).mean()        # Plan 10: เทรนด์ MA200 H1

                for i in range(max(0, len(rates) - count), len(rates)):
                    r = rates[i]
                    c = closes[i]
                    sar_v = sar_vals[i] if i < len(sar_vals) else None
                    candles.append({
                        "time": int(r["time"]),
                        "open": float(r["open"]),
                        "high": highs[i],
                        "low": lows[i],
                        "close": c,
                        "h1_ma5": _clean(ma5_s.iloc[i]),
                        "h1_ma10": _clean(ma10_s.iloc[i]),
                        "h1_ma20": _clean(ma20_s.iloc[i]),
                        "h1_bb_mid": _clean(bb_mid_s.iloc[i]),
                        "h1_bb_up": _clean(bb_up_s.iloc[i]),
                        "h1_bb_lo": _clean(bb_lo_s.iloc[i]),
                        "h1_sar": _clean(sar_v),
                        "h1_ema100": _clean(ema100_s.iloc[i]),
                        "h1_ma200": _clean(ma200_h1_s.iloc[i]),
                    })
            else:  # H4
                # H4 Trend: MA10, MA30, MA200
                ma10_s = df["close"].rolling(10).mean()
                ma30_s = df["close"].rolling(30).mean()
                ma200_s = df["close"].rolling(200).mean()
                # Plan 7 / 8: Bollinger H4 (SMA 20, 2 STD)
                bb4_mid_s = df["close"].rolling(20).mean()
                bb4_std_s = df["close"].rolling(20).std()
                for i in range(max(0, len(rates) - count), len(rates)):
                    r = rates[i]
                    c = closes[i]
                    candles.append({
                        "time": int(r["time"]),
                        "open": float(r["open"]),
                        "high": highs[i],
                        "low": lows[i],
                        "close": c,
                        "h4_ma10": _clean(ma10_s.iloc[i]),
                        "h4_ma30": _clean(ma30_s.iloc[i]),
                        "h4_ma200": _clean(ma200_s.iloc[i]),
                        "h4_bb_mid": _clean(bb4_mid_s.iloc[i]),
                        "h4_bb_up": _clean(bb4_mid_s.iloc[i] + 2 * bb4_std_s.iloc[i]),
                        "h4_bb_lo": _clean(bb4_mid_s.iloc[i] - 2 * bb4_std_s.iloc[i]),
                    })

            # Plan 9: คลื่น Fibonacci H1 — ออเดอร์รอ (pending) + คลื่นของไม้ P9 ที่ถืออยู่ (active) ให้กราฟวาดเส้นระดับ
            fib = []
            if tf_upper == "H1":
                try:
                    import fib_plan
                    r9 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 700)
                    if r9 is not None and len(r9) >= 300:
                        for od in fib_plan.pending_orders(pd.DataFrame(r9)).values():
                            fib.append({"side": int(od["side"]), "a": float(od["a"]), "b": float(od["b"]), "state": "pending",
                                        "bars_left": int(od["bars_left"])})
                    for p9 in (mt5.positions_get(symbol=symbol) or ()):
                        if (p9.comment or "").startswith(fib_plan.NAME):
                            s9 = 1 if p9.type == 0 else -1
                            lg = fib_plan.leg_of(s9, float(p9.price_open), float(p9.tp or 0))
                            if lg:
                                fib.insert(0, {"side": s9, "a": float(lg[0]), "b": float(lg[1]), "state": "active"})
                except Exception:
                    fib = []

            info = mt5.symbol_info(symbol)
            point = float(info.point) if info and info.point else 0.01
            positions = [{
                "type": "BUY" if p.type == 0 else "SELL", "price": float(p.price_open), "sl": float(p.sl), "tp": float(p.tp),
                "lot": float(p.volume), "profit": float(p.profit) + float(getattr(p, "swap", 0.0) or 0.0), "plan": p.comment or "",
            } for p in (mt5.positions_get(symbol=symbol) or [])]
            res_dict = {
                "timeframe": tf_upper,
                "bar_seconds": bar_seconds,
                "candles": candles,
                "positions": positions,
                "spread_pts": int(round((float(tick.ask) - float(tick.bid)) / point)) if tick else 0,
                "bid": float(tick.bid) if tick else candles[-1]["close"],
                "ask": float(tick.ask) if tick else candles[-1]["close"],
                "server_time": int(tick.time) if tick else candles[-1]["time"],
                "support": ctx.get("sup") if ctx else None,
                "resistance": ctx.get("res") if ctx else None,
                "support2": ctx.get("sup2") if ctx else None,
                "resistance2": ctx.get("res2") if ctx else None,
                "support3": ctx.get("sup3") if ctx else None,
                "resistance3": ctx.get("res3") if ctx else None,
                "support4": ctx.get("sup4") if ctx else None,
                "resistance4": ctx.get("res4") if ctx else None,
                "support5": ctx.get("sup5") if ctx else None,
                "resistance5": ctx.get("res5") if ctx else None,
                "sup_stars": ctx.get("sup_stars", 6.0) if ctx else 6.0,
                "res_stars": ctx.get("res_stars", 6.0) if ctx else 6.0,
                "sup2_stars": ctx.get("sup2_stars", 6.0) if ctx else 6.0,
                "res2_stars": ctx.get("res2_stars", 6.0) if ctx else 6.0,
                "sup3_stars": ctx.get("sup3_stars", 6.0) if ctx else 6.0,
                "res3_stars": ctx.get("res3_stars", 6.0) if ctx else 6.0,
                "sup4_stars": ctx.get("sup4_stars", 6.0) if ctx else 6.0,
                "res4_stars": ctx.get("res4_stars", 6.0) if ctx else 6.0,
                "sup5_stars": ctx.get("sup5_stars", 6.0) if ctx else 6.0,
                "res5_stars": ctx.get("res5_stars", 6.0) if ctx else 6.0,
                "fib": fib,
            }

            # คำนวณแนวรับ–แนวต้าน 5 ระดับ (S1..S5, R1..R5) จากกราฟแท่ง 1,000 แท่ง พร้อม H1 + H4 Confluence
            try:
                import multi_asset_ai_bot
                df_sr = None
                df_h4_sr = None
                # ดึง H4 1,050 แท่งสำหรับ Confluence เสมอ
                if tf_upper == "H4":
                    if len(df) >= 1002:
                        df_sr = df
                    else:
                        h4_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 1050)
                        if h4_rates is not None and len(h4_rates) >= 60:
                            df_sr = pd.DataFrame(h4_rates)
                else:
                    # ดึง H1 สำหรับ SR หลัก
                    if tf_upper == "H1" and len(df) >= 1002:
                        df_sr = df
                    else:
                        h1_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1050)
                        if h1_rates is not None and len(h1_rates) >= 60:
                            df_sr = pd.DataFrame(h1_rates)
                    # ดึง H4 ประกอบ Confluence
                    h4_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 1050)
                    if h4_rates is not None and len(h4_rates) >= 60:
                        df_h4_sr = pd.DataFrame(h4_rates)

                if df_sr is not None and len(df_sr) >= 60:
                    sr_calc = multi_asset_ai_bot.find_sr_levels(
                        df_sr, float(closes[-1]),
                        lookback=min(1000, len(df_sr) - 2),
                        df_h4=df_h4_sr
                    )
                    for i in range(1, 6):
                        s_k = "support" if i == 1 else f"support{i}"
                        r_k = "resistance" if i == 1 else f"resistance{i}"
                        star_s = "sup_stars" if i == 1 else f"sup{i}_stars"
                        star_r = "res_stars" if i == 1 else f"res{i}_stars"
                        conf_s = "sup_h4_conf" if i == 1 else f"sup{i}_h4_conf"
                        conf_r = "res_h4_conf" if i == 1 else f"res{i}_h4_conf"
                        h4_star_s = "sup_h4_stars" if i == 1 else f"sup{i}_h4_stars"
                        h4_star_r = "res_h4_stars" if i == 1 else f"res{i}_h4_stars"
                        if s_k in sr_calc and not math.isnan(sr_calc[s_k]):
                            res_dict[s_k] = sr_calc[s_k]
                            res_dict[star_s] = sr_calc.get(star_s, 6.0)
                            res_dict[conf_s] = sr_calc.get(conf_s, False)
                            res_dict[h4_star_s] = sr_calc.get(h4_star_s, 0.0)
                        if r_k in sr_calc and not math.isnan(sr_calc[r_k]):
                            res_dict[r_k] = sr_calc[r_k]
                            res_dict[star_r] = sr_calc.get(star_r, 6.0)
                            res_dict[conf_r] = sr_calc.get(conf_r, False)
                            res_dict[h4_star_r] = sr_calc.get(h4_star_r, 0.0)
                    for fk in ("focus_sup", "focus_res", "focus_sup_price", "focus_res_price",
                               "focus_sup_score", "focus_res_score", "focus_sup_h4_conf", "focus_res_h4_conf",
                               "focus_action", "focus_summary", "dist_sup_pts", "dist_res_pts", "dist_sup_atr", "dist_res_atr"):
                        if fk in sr_calc:
                            res_dict[fk] = sr_calc[fk]
            except Exception:
                pass

            return res_dict
        except Exception:
            return None

    QUICK_PLAN = "Manual-Quick"   # comment ของไม้ที่กดเข้าเอง (แยกในประวัติ/สถิติ)

    def quick_order_defaults(self, symbol: str = None):
        """ค่าเริ่มต้นสำหรับหน้าต่างเข้าไม้ทันที: ATR(14) M15 แท่งปิด · SL 1.0 ATR · TP 1.5 เท่าของ SL"""
        if symbol is None or symbol == "XAUUSD":
            symbol = self.get_gold_symbol()
        try:
            import pandas as pd
            if mt5.terminal_info() is None and not initialize_mt5():
                return None
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 40)
            tick = mt5.symbol_info_tick(symbol)
            if rates is None or tick is None:
                return None
            d = pd.DataFrame(rates)
            atr = float(bot_core._atr_series(d).iloc[-2])
            return {"bid": float(tick.bid), "ask": float(tick.ask), "atr": atr,
                    "sl_pts": round(atr * 1.0, 2), "tp_pts": round(atr * 1.5, 2), "lot": float(bot_core.current_lot())}
        except Exception:
            return None

    def quick_order(self, side: str, sl_pts: float, tp_pts: float, symbol: str = None) -> tuple[bool, str]:
        """เปิดออเดอร์ทันทีจากปุ่มในโปรแกรม (ใช้ send_order ตัวเดียวกับบอท: Lot ที่ตั้งไว้, เช็กหลักประกัน, บันทึกประวัติ)
        sl_pts / tp_pts = ระยะเป็นจุดราคา (tp_pts <= 0 = ไม่ตั้ง TP)"""
        if symbol is None or symbol == "XAUUSD":
            symbol = self.get_gold_symbol()
        if not license_mgr.is_authenticated:
            return False, "กรุณาเข้าสู่ระบบก่อน"
        if not license_mgr.has_active_hours():
            return False, "ชั่วโมงใช้งานหมดแล้ว — เติมชั่วโมงก่อนเข้าไม้"
        try:
            if mt5.terminal_info() is None and not initialize_mt5():
                return False, "เชื่อมต่อ MT5 ไม่ได้ — เปิด MetaTrader 5 ค้างไว้"
            tick = mt5.symbol_info_tick(symbol)
            info = mt5.symbol_info(symbol)
            if tick is None or info is None:
                return False, "อ่านราคาไม่ได้ (ตลาดอาจปิด)"
            if sl_pts <= 0:
                return False, "ต้องตั้ง SL มากกว่า 0"
            # เพดานจำนวนไม้เดียวกับบอท (ยอดเงิน ÷ หลักประกันต่อไม้ × Lot) — นับทุกไม้ในบัญชี
            import plan_config
            acc = mt5.account_info()
            if acc is not None:
                n_open = len(mt5.positions_get() or [])
                n_max = plan_config.max_positions(float(acc.balance), bot_core.current_lot())
                if n_open >= n_max:
                    return False, (f"เปิดไม้ครบเพดานแล้ว ({n_open} / {n_max} ไม้)\n"
                                   f"ยอดเงิน {float(acc.balance):,.2f} ที่ Lot {bot_core.current_lot():.2f} เปิดได้สูงสุด {n_max} ไม้ — ปิดไม้เดิมหรือลด Lot ก่อน")
            digits = int(info.digits)
            if side == "BUY":
                price, otype = float(tick.ask), mt5.ORDER_TYPE_BUY
                sl = round(price - sl_pts, digits)
                tp = round(price + tp_pts, digits) if tp_pts > 0 else 0.0
            else:
                price, otype = float(tick.bid), mt5.ORDER_TYPE_SELL
                sl = round(price + sl_pts, digits)
                tp = round(price - tp_pts, digits) if tp_pts > 0 else 0.0
            print(f"[MANUAL ORDER] {side} {symbol} @ {price:.2f} SL {sl:.2f} TP {tp:.2f} (กดเข้าไม้ทันทีจากโปรแกรม)")
            ok = bot_core.send_order(symbol, otype, price, sl, tp, plan_name=self.QUICK_PLAN)
            if ok:
                return True, f"เปิด {side} สำเร็จ @ {price:,.2f} · SL {sl:,.2f}" + (f" · TP {tp:,.2f}" if tp else " · ไม่ตั้ง TP")
            err = mt5.last_error()
            return False, f"ส่งคำสั่งไม่สำเร็จ ({err[1] if err else 'ไม่ทราบสาเหตุ'}) — ดูรายละเอียดใน Console"
        except Exception as e:
            return False, f"เกิดข้อผิดพลาด: {e}"

    def get_market_explain(self, symbol: str = None):
        """ค่าที่ใช้ตัดสินสภาวะตลาด H1/H4 จากแท่งที่ปิดแล้ว (สำหรับหน้าต่างอธิบาย) — None ถ้าเชื่อม MT5 ไม่ได้"""
        if symbol is None or symbol == "XAUUSD":
            symbol = self.get_gold_symbol()
        try:
            import pandas as pd
            if mt5.terminal_info() is None and not initialize_mt5():
                return None
            out = {}
            dfs = {}
            for tf_name, tf in (("H1", mt5.TIMEFRAME_H1), ("H4", mt5.TIMEFRAME_H4)):
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, 260)
                if rates is None or len(rates) < 210:
                    continue
                df_cur = pd.DataFrame(rates)
                dfs[tf_name] = df_cur
                c = df_cur["close"]
                ma = {n: float(c.rolling(n).mean().iloc[-2]) for n in (10, 30, 50, 100, 150, 200)}
                out[tf_name] = {"close": float(c.iloc[-2]), "ma": ma,
                                "diff_pct": (ma[10] / ma[30] - 1.0) * 100.0}

            # อัปเดต latest_radar_cache ล่วงหน้า เพื่อให้การ์ดสภาวะตลาดและแนวรับ-ต้านแสดงผลได้ทันทีแม้ยังไม่เริ่มบอท
            if "H1" in dfs and "H4" in dfs:
                try:
                    df_h1 = dfs["H1"]
                    df_h4 = dfs["H4"]
                    cached = bot_core.latest_radar_cache.get(symbol, {})
                    if not self.is_active or cached.get("h1_support", 0.0) == 0.0 or cached.get("h4_trend") in ("ANALYZING...", None):
                        cur_price = float(df_h1["close"].iloc[-1])
                        sr_h1 = bot_core.find_sr_levels(df_h1, cur_price, df_h4=df_h4)
                        sr_h4 = bot_core.find_sr_levels(df_h4, cur_price)
                        h1_cond, h1_cond_pct = bot_core.ma_condition(df_h1["close"])
                        h4_cond, h4_cond_pct = bot_core.ma_condition(df_h4["close"])

                        df_h4["ma_fast_h4"] = df_h4["close"].rolling(10).mean()
                        df_h4["ma_slow_h4"] = df_h4["close"].rolling(30).mean()
                        atr_h4 = bot_core._atr_series(df_h4)
                        is_up_h4, diff_pct_h4, _ = bot_core.closed_trend(df_h4["ma_fast_h4"], df_h4["ma_slow_h4"], atr=atr_h4)
                        h4_cloud = f"SIDEWAY ({diff_pct_h4:+.2f}%)" if abs(diff_pct_h4) < 0.20 else (f"BULLISH (+{diff_pct_h4:.2f}%)" if is_up_h4 else f"BEARISH ({diff_pct_h4:.2f}%)")

                        df_h1["ma_fast_h1"] = df_h1["close"].rolling(10).mean()
                        df_h1["ma_slow_h1"] = df_h1["close"].rolling(30).mean()
                        atr_h1 = bot_core._atr_series(df_h1)
                        is_up_h1, diff_pct_h1, _ = bot_core.closed_trend(df_h1["ma_fast_h1"], df_h1["ma_slow_h1"], atr=atr_h1)
                        h1_cloud = f"SIDEWAY ({diff_pct_h1:+.2f}%)" if abs(diff_pct_h1) < 0.20 else (f"BULLISH (+{diff_pct_h1:.2f}%)" if is_up_h1 else f"BEARISH ({diff_pct_h1:.2f}%)")

                        bot_core.latest_radar_cache[symbol] = {
                            "symbol": symbol,
                            "status": "[STANDBY]" if not self.is_active else "[WAIT OUTSIDE ZONE]",
                            "up_prob": 0.50,
                            "price": cur_price,
                            "is_in_zone": False,
                            "h4_trend": h4_cloud,
                            "h4_diff_pct": round(diff_pct_h4, 2),
                            "h1_trend": h1_cloud,
                            "h1_diff_pct": round(diff_pct_h1, 2),
                            "h1_support": round(float(sr_h1.get("support", 0.0) or 0.0), 2),
                            "h1_resistance": round(float(sr_h1.get("resistance", 0.0) or 0.0), 2),
                            "h1_sup_stars": float(sr_h1.get("sup_stars", 6.0) or 6.0),
                            "h1_res_stars": float(sr_h1.get("res_stars", 6.0) or 6.0),
                            "h4_support": round(float(sr_h4.get("support", 0.0) or 0.0), 2),
                            "h4_resistance": round(float(sr_h4.get("resistance", 0.0) or 0.0), 2),
                            "h4_sup_stars": float(sr_h4.get("sup_stars", 6.0) or 6.0),
                            "h4_res_stars": float(sr_h4.get("res_stars", 6.0) or 6.0),
                            "h1_cond": int(h1_cond),
                            "h1_cond_pct": round(h1_cond_pct, 2),
                            "h4_cond": int(h4_cond),
                            "h4_cond_pct": round(h4_cond_pct, 2),
                        }
                except Exception:
                    pass

            return out or None
        except Exception:
            return None

    @staticmethod
    def _normalize_plan_name(raw_plan: str) -> str:
        s = str(raw_plan or "").strip()
        if not s or "Manual" in s or s in ("เข้าเอง", "อื่นๆ"):
            return "เข้าเอง"
        for base in ("MA-Cross-H1-Trend", "MA-Cross-Trend", "SMC-LiquidityHunt", "SR-SwingBounce", "BB-H1-Reversion", "PSAR-H1-Trend",
                     "BB-H4-Reversion", "BB-H4-Free", "Fib-H1-Counter", "RSI-H1-Trend"):
            if base in s:
                return base
        if "Plan 1" in s: return "MA-Cross-Trend"
        if "Plan 2" in s: return "MA-Cross-H1-Trend"
        if "Plan 3" in s: return "SMC-LiquidityHunt"
        if "Plan 4" in s: return "SR-SwingBounce"
        if "Plan 5" in s: return "BB-H1-Reversion"
        if "Plan 6" in s: return "PSAR-H1-Trend"
        if "Plan 7" in s: return "BB-H4-Reversion"
        if "Plan 8" in s: return "BB-H4-Free"
        if "Plan 9" in s: return "Fib-H1-Counter"
        if "Plan 10" in s: return "RSI-H1-Trend"
        try:
            import plan_config
            return plan_config.base_plan(s) or "อื่นๆ"
        except Exception:
            return "อื่นๆ"

    def get_daily_pnl(self, start_date, end_date) -> list[dict]:
        """
        กำไร/ขาดทุนสุทธิรายวันของทั้งบัญชี (profit + commission + swap ของทุก Deal เทรด) ตามวันเวลาไทย
        ผสานประวัติจาก user_trade_history.csv สำหรับไม้ที่ไม่อยู่ในประวัติ MT5 ปัจจุบัน (เช่น สลับโบรกเกอร์)
        start_date / end_date = datetime.date (รวมทั้งสองวัน) · คืน [{"date", "profit", "closed", "plans"}] ครบทุกวันในช่วง
        """
        from datetime import datetime, timedelta, timezone
        days = {}
        d = start_date
        while d <= end_date:
            days[d] = {"date": d, "profit": 0.0, "closed": 0, "plans": {}}
            d += timedelta(days=1)
        seen_tickets = set()
        try:
            if mt5.terminal_info() is not None or initialize_mt5():
                # เวลา Deal ของ MT5 = เวลาเซิร์ฟเวอร์ → แปลงเป็นเวลาจริงด้วย thai_time (ตลาดปิดก็ยังถูก · คิดตาม DST ของวันนั้น)
                th = timezone(timedelta(hours=7))
                fetch_start = datetime.combine(start_date - timedelta(days=90), datetime.min.time())
                fetch_end = datetime.combine(end_date + timedelta(days=2), datetime.min.time())
                deals = mt5.history_deals_get(fetch_start, fetch_end) or []

                import plan_config
                pos_plan_map = {}
                for dl in deals:
                    if dl.entry == 0 and dl.comment:
                        pos_plan_map[dl.position_id] = plan_config.base_plan(dl.comment)

                for dl in deals:
                    if dl.type not in (0, 1):  # เฉพาะ Deal ซื้อ/ขาย (ไม่นับฝาก-ถอน/โบนัส)
                        continue
                    if dl.position_id:
                        seen_tickets.add(int(dl.position_id))
                    day = datetime.fromtimestamp(thai_time.server_to_epoch(int(dl.time)), th).date()
                    if day not in days:
                        continue
                    p = float(dl.profit) + float(getattr(dl, "commission", 0.0)) + float(getattr(dl, "swap", 0.0))
                    days[day]["profit"] += p

                    plan = pos_plan_map.get(dl.position_id)
                    if not plan and dl.comment:
                        plan = plan_config.base_plan(dl.comment)
                    plan = self._normalize_plan_name(plan)

                    dp = days[day]["plans"].setdefault(plan, {"profit": 0.0, "closed": 0, "wins": 0, "losses": 0})
                    dp["profit"] += p

                    if dl.entry in (1, 2):
                        days[day]["closed"] += 1
                        dp["closed"] += 1
                        if p > 0.005:
                            dp["wins"] += 1
                        elif p < -0.005:
                            dp["losses"] += 1
        except Exception:
            pass

        # ผสานประวัติการเทรดที่บันทึกไว้ใน user_trade_history.csv
        try:
            import csv
            import os
            from app_paths import data_path
            cur_user_id = ""
            try:
                from license_manager import license_mgr
                cur_user_id = str(license_mgr.get_current_user().get("user_id") or "").strip()
            except Exception:
                pass

            csv_path = data_path("user_trade_history.csv")
            if os.path.exists(csv_path) and os.path.getsize(csv_path) > 100:
                csv_seen = set()
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        u_id = str(row.get("User_ID") or "").strip()
                        if cur_user_id and u_id and u_id != cur_user_id:
                            continue
                        action = (row.get("Action") or "").strip()
                        if action not in ("CLOSE", "TP_HIT", "SL_HIT"):
                            continue
                        try:
                            ticket = int(row.get("Ticket") or 0)
                        except Exception:
                            ticket = 0
                        if ticket:
                            if ticket in seen_tickets or ticket in csv_seen:
                                continue
                            csv_seen.add(ticket)

                        time_str = (row.get("Time") or "").strip()
                        if not time_str:
                            continue
                        try:
                            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            continue
                        day = dt.date()
                        if day not in days:
                            continue

                        try:
                            p = float(row.get("Profit") or 0.0)
                        except Exception:
                            p = 0.0

                        raw_plan = (row.get("Plan") or "").strip()
                        plan = self._normalize_plan_name(raw_plan)

                        days[day]["profit"] += p
                        days[day]["closed"] += 1

                        dp = days[day]["plans"].setdefault(plan, {"profit": 0.0, "closed": 0, "wins": 0, "losses": 0})
                        dp["profit"] += p
                        dp["closed"] += 1
                        if p > 0.005:
                            dp["wins"] += 1
                        elif p < -0.005:
                            dp["losses"] += 1
        except Exception:
            pass

        return list(days.values())

    def get_plans_summary_stats(self, start_date, end_date) -> dict:
        """
        สรุปสถิติความสำเร็จรายแผน และภาพรวมทั้งหมด ในช่วงวันที่กำหนด
        ผสานประวัติจาก user_trade_history.csv สำหรับไม้ที่ไม่อยู่ในประวัติ MT5 ปัจจุบัน (เช่น สลับโบรกเกอร์)
        คืน dict {"overall": {...}, "plans": {...}}
        """
        from datetime import datetime, timedelta, timezone
        res = {
            "overall": {
                "profit": 0.0, "closed": 0, "wins": 0, "losses": 0, "be": 0,
                "win_rate": 0.0, "gross_profit": 0.0, "gross_loss": 0.0, "profit_factor": 0.0
            },
            "plans": {}
        }
        seen_tickets = set()
        try:
            if mt5.terminal_info() is not None or initialize_mt5():
                th = timezone(timedelta(hours=7))
                fetch_start = datetime.combine(start_date - timedelta(days=90), datetime.min.time())
                fetch_end = datetime.combine(end_date + timedelta(days=2), datetime.min.time())
                deals = mt5.history_deals_get(fetch_start, fetch_end) or []

                import plan_config
                pos_plan_map = {}
                for dl in deals:
                    if dl.entry == 0 and dl.comment:
                        pos_plan_map[dl.position_id] = plan_config.base_plan(dl.comment)

                for dl in deals:
                    if dl.type not in (0, 1):
                        continue
                    if dl.position_id:
                        seen_tickets.add(int(dl.position_id))
                    day = datetime.fromtimestamp(thai_time.server_to_epoch(int(dl.time)), th).date()
                    if day < start_date or day > end_date:
                        continue
                    p = float(dl.profit) + float(getattr(dl, "commission", 0.0)) + float(getattr(dl, "swap", 0.0))

                    plan = pos_plan_map.get(dl.position_id)
                    if not plan and dl.comment:
                        plan = plan_config.base_plan(dl.comment)
                    plan = self._normalize_plan_name(plan)

                    st = res["plans"].setdefault(plan, {
                        "profit": 0.0, "closed": 0, "wins": 0, "losses": 0, "be": 0,
                        "gross_profit": 0.0, "gross_loss": 0.0, "win_rate": 0.0, "profit_factor": 0.0
                    })
                    st["profit"] += p
                    res["overall"]["profit"] += p

                    if dl.entry in (1, 2):
                        res["overall"]["closed"] += 1
                        st["closed"] += 1
                        if p > 0.005:
                            res["overall"]["wins"] += 1
                            res["overall"]["gross_profit"] += p
                            st["wins"] += 1
                            st["gross_profit"] += p
                        elif p < -0.005:
                            res["overall"]["losses"] += 1
                            res["overall"]["gross_loss"] += abs(p)
                            st["losses"] += 1
                            st["gross_loss"] += abs(p)
                        else:
                            res["overall"]["be"] += 1
                            st["be"] += 1
        except Exception:
            pass

        # ผสานประวัติจาก user_trade_history.csv
        try:
            import csv
            import os
            from app_paths import data_path
            cur_user_id = ""
            try:
                from license_manager import license_mgr
                cur_user_id = str(license_mgr.get_current_user().get("user_id") or "").strip()
            except Exception:
                pass

            csv_path = data_path("user_trade_history.csv")
            if os.path.exists(csv_path) and os.path.getsize(csv_path) > 100:
                csv_seen = set()
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        u_id = str(row.get("User_ID") or "").strip()
                        if cur_user_id and u_id and u_id != cur_user_id:
                            continue
                        action = (row.get("Action") or "").strip()
                        if action not in ("CLOSE", "TP_HIT", "SL_HIT"):
                            continue
                        try:
                            ticket = int(row.get("Ticket") or 0)
                        except Exception:
                            ticket = 0
                        if ticket:
                            if ticket in seen_tickets or ticket in csv_seen:
                                continue
                            csv_seen.add(ticket)

                        time_str = (row.get("Time") or "").strip()
                        if not time_str:
                            continue
                        try:
                            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                        except Exception:
                            continue
                        day = dt.date()
                        if day < start_date or day > end_date:
                            continue

                        try:
                            p = float(row.get("Profit") or 0.0)
                        except Exception:
                            p = 0.0

                        raw_plan = (row.get("Plan") or "").strip()
                        plan = self._normalize_plan_name(raw_plan)

                        st = res["plans"].setdefault(plan, {
                            "profit": 0.0, "closed": 0, "wins": 0, "losses": 0, "be": 0,
                            "gross_profit": 0.0, "gross_loss": 0.0, "win_rate": 0.0, "profit_factor": 0.0
                        })
                        st["profit"] += p
                        st["closed"] += 1
                        res["overall"]["profit"] += p
                        res["overall"]["closed"] += 1

                        if p > 0.005:
                            res["overall"]["wins"] += 1
                            res["overall"]["gross_profit"] += p
                            st["wins"] += 1
                            st["gross_profit"] += p
                        elif p < -0.005:
                            res["overall"]["losses"] += 1
                            res["overall"]["gross_loss"] += abs(p)
                            st["losses"] += 1
                            st["gross_loss"] += abs(p)
                        else:
                            res["overall"]["be"] += 1
                            st["be"] += 1
        except Exception:
            pass

        ov = res["overall"]
        if ov["closed"] > 0:
            ov["win_rate"] = round(ov["wins"] / ov["closed"] * 100, 1)
        if ov["gross_loss"] > 0:
            ov["profit_factor"] = round(ov["gross_profit"] / ov["gross_loss"], 2)
        elif ov["gross_profit"] > 0:
            ov["profit_factor"] = 99.9

        for p_info in res["plans"].values():
            if p_info["closed"] > 0:
                p_info["win_rate"] = round(p_info["wins"] / p_info["closed"] * 100, 1)
            if p_info["gross_loss"] > 0:
                p_info["profit_factor"] = round(p_info["gross_profit"] / p_info["gross_loss"], 2)
            elif p_info["gross_profit"] > 0:
                p_info["profit_factor"] = 99.9

        return res

    def get_plans_condition_status(self, symbol: str = None) -> dict:
        """
        ประเมินสถานะเงื่อนไขการเข้าไม้เรียลไทม์ของทั้ง 6 แผนเทรด (P1-P6) ณ ราคาปัจจุบัน
        คืนค่า dict ข้อมูลแต่ละแผน: label, side, matched (เข้าแล้วกี่ข้อ), total, pct, items ([✓/✗ ข้อความ])
        มีระบบแคช 1.5 วินาทีเพื่อป้องกันความหน่วง
        """
        if symbol is None or symbol == "XAUUSD":
            symbol = self.get_gold_symbol()
        now = time.time()
        if self._plans_status_cache and (now - self._plans_status_time < 1.5):
            return self._plans_status_cache

        try:
            res = bot_core.evaluate_plans_condition_status(symbol)
            if res:
                self._plans_status_cache = res
                self._plans_status_time = now
                return res
        except Exception:
            pass
        return self._plans_status_cache or {}

# Singleton Controller Instance
bot_ctrl = BotController()
