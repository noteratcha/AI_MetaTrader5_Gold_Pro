import threading
import time
import sys
import queue
import re
import MetaTrader5 as mt5
import multi_asset_ai_bot as bot_core
import mt5_algo
import thai_time
import sound_manager
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

        if not license_mgr.has_active_hours():
            return False, "เวลาใช้งานหมดแล้ว! กรุณาเติมชั่วโมงด้วย Product Key ก่อนเริ่มต้น"

        low = self._min_balance_message()
        if low:
            return False, low

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

        if not license_mgr.has_active_hours():
            return False, "เวลาใช้งานหมดแล้ว! กรุณาเติมชั่วโมงก่อนกลับมาทำงาน"

        low = self._min_balance_message()
        if low:
            return False, low

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

    def _min_balance_message(self):
        """ยอดเงิน (Equity) ต้องมีอย่างน้อย 25 USD ระบบถึงจะทำงาน — คืนข้อความเตือน หรือ None ถ้าผ่าน/อ่าน MT5 ไม่ได้"""
        try:
            import plan_config
            if mt5.terminal_info() is None and not mt5.initialize():
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

    def _check_market_open(self) -> bool:
        """ตลาดเปิด = โบรกเกอร์เปิดการเทรด และราคามี tick ใหม่อยู่ภายใน 2 นาที (ทองมี tick ตลอดเมื่อตลาดเปิด)"""
        try:
            tick = mt5.symbol_info_tick(self.MARKET_SYMBOL)
            sym = mt5.symbol_info(self.MARKET_SYMBOL)
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
            if not mt5.initialize():
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
                si = mt5.symbol_info("XAUUSD")
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
                    t["close_code"] = int(getattr(d, "reason", -1))  # 0-2 ปิดเอง · 3 บอท · 4 SL · 5 TP · 6 Stop Out
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

    def get_live_candles(self, count: int = 16, symbol: str = "XAUUSD", extra: int = 50, timeframe: str = "M15"):
        """แท่งราคาล่าสุด count แท่ง (แท่งสุดท้าย = แท่งที่กำลังวิ่ง) พร้อมอินดิเคเตอร์ตาม Timeframe ที่เลือก (M15, H1, H4) + Bid/Ask ปัจจุบัน — None ถ้าเชื่อม MT5 ไม่ได้"""
        try:
            import math
            import pandas as pd
            if mt5.terminal_info() is None and not mt5.initialize():
                return None

            tf_upper = (timeframe or "M15").upper()
            if tf_upper == "H1":
                mt5_tf = mt5.TIMEFRAME_H1
                bar_seconds = 3600
                warmup = max(extra, 150)
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
                    })
            else:  # H4
                # H4 Trend: MA10, MA30, MA200
                ma10_s = df["close"].rolling(10).mean()
                ma30_s = df["close"].rolling(30).mean()
                ma200_s = df["close"].rolling(200).mean()
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
                    })

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
            }

            # คำนวณแนวรับ–แนวต้าน 5 ระดับ (S1..S5, R1..R5) จากกราฟแท่ง 500 แท่ง
            try:
                import multi_asset_ai_bot
                df_sr = None
                if tf_upper == "H4":
                    if len(df) >= 60:
                        df_sr = df
                    else:
                        h4_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 520)
                        if h4_rates is not None and len(h4_rates) >= 60:
                            df_sr = pd.DataFrame(h4_rates)
                elif tf_upper == "H1":
                    if len(df) >= 60:
                        df_sr = df
                    else:
                        h1_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 520)
                        if h1_rates is not None and len(h1_rates) >= 60:
                            df_sr = pd.DataFrame(h1_rates)
                else:
                    h1_rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 520)
                    if h1_rates is not None and len(h1_rates) >= 60:
                        df_sr = pd.DataFrame(h1_rates)

                if df_sr is not None and len(df_sr) >= 60:
                    sr_calc = multi_asset_ai_bot.find_sr_levels(df_sr, float(closes[-1]), lookback=min(500, len(df_sr) - 2))
                    for i in range(1, 6):
                        s_k = "support" if i == 1 else f"support{i}"
                        r_k = "resistance" if i == 1 else f"resistance{i}"
                        star_s = "sup_stars" if i == 1 else f"sup{i}_stars"
                        star_r = "res_stars" if i == 1 else f"res{i}_stars"
                        if s_k in sr_calc and not math.isnan(sr_calc[s_k]):
                            res_dict[s_k] = sr_calc[s_k]
                            res_dict[star_s] = sr_calc.get(star_s, 6.0)
                        if r_k in sr_calc and not math.isnan(sr_calc[r_k]):
                            res_dict[r_k] = sr_calc[r_k]
                            res_dict[star_r] = sr_calc.get(star_r, 6.0)
                    for fk in ("focus_sup", "focus_res", "focus_sup_price", "focus_res_price",
                               "focus_sup_score", "focus_res_score", "focus_action", "focus_summary",
                               "dist_sup_pts", "dist_res_pts", "dist_sup_atr", "dist_res_atr"):
                        if fk in sr_calc:
                            res_dict[fk] = sr_calc[fk]
            except Exception:
                pass

            return res_dict
        except Exception:
            return None

    QUICK_PLAN = "Manual-Quick"   # comment ของไม้ที่กดเข้าเอง (แยกในประวัติ/สถิติ)

    def quick_order_defaults(self, symbol: str = "XAUUSD"):
        """ค่าเริ่มต้นสำหรับหน้าต่างเข้าไม้ทันที: ATR(14) M15 แท่งปิด · SL 1.0 ATR · TP 1.5 เท่าของ SL"""
        try:
            import pandas as pd
            if mt5.terminal_info() is None and not mt5.initialize():
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

    def quick_order(self, side: str, sl_pts: float, tp_pts: float, symbol: str = "XAUUSD") -> tuple[bool, str]:
        """เปิดออเดอร์ทันทีจากปุ่มในโปรแกรม (ใช้ send_order ตัวเดียวกับบอท: Lot ที่ตั้งไว้, เช็กหลักประกัน, บันทึกประวัติ)
        sl_pts / tp_pts = ระยะเป็นจุดราคา (tp_pts <= 0 = ไม่ตั้ง TP)"""
        if not license_mgr.is_authenticated:
            return False, "กรุณาเข้าสู่ระบบก่อน"
        if not license_mgr.has_active_hours():
            return False, "ชั่วโมงใช้งานหมดแล้ว — เติมชั่วโมงก่อนเข้าไม้"
        try:
            if mt5.terminal_info() is None and not mt5.initialize():
                return False, "เชื่อมต่อ MT5 ไม่ได้ — เปิด MetaTrader 5 ค้างไว้"
            tick = mt5.symbol_info_tick(symbol)
            info = mt5.symbol_info(symbol)
            if tick is None or info is None:
                return False, "อ่านราคาไม่ได้ (ตลาดอาจปิด)"
            if sl_pts <= 0:
                return False, "ต้องตั้ง SL มากกว่า 0"
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

    def get_market_explain(self, symbol: str = "XAUUSD"):
        """ค่าที่ใช้ตัดสินสภาวะตลาด H1/H4 จากแท่งที่ปิดแล้ว (สำหรับหน้าต่างอธิบาย) — None ถ้าเชื่อม MT5 ไม่ได้"""
        try:
            import pandas as pd
            if mt5.terminal_info() is None and not mt5.initialize():
                return None
            out = {}
            for tf_name, tf in (("H1", mt5.TIMEFRAME_H1), ("H4", mt5.TIMEFRAME_H4)):
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, 260)
                if rates is None or len(rates) < 210:
                    continue
                c = pd.Series([float(r["close"]) for r in rates])
                ma = {n: float(c.rolling(n).mean().iloc[-2]) for n in (10, 30, 50, 100, 150, 200)}
                out[tf_name] = {"close": float(c.iloc[-2]), "ma": ma,
                                "diff_pct": (ma[10] / ma[30] - 1.0) * 100.0}
            return out or None
        except Exception:
            return None

    def get_daily_pnl(self, start_date, end_date) -> list[dict]:
        """
        กำไร/ขาดทุนสุทธิรายวันของทั้งบัญชี (profit + commission + swap ของทุก Deal เทรด) ตามวันเวลาไทย
        start_date / end_date = datetime.date (รวมทั้งสองวัน) · คืน [{"date", "profit", "closed", "plans"}] ครบทุกวันในช่วง
        """
        from datetime import datetime, timedelta, timezone
        days = {}
        d = start_date
        while d <= end_date:
            days[d] = {"date": d, "profit": 0.0, "closed": 0, "plans": {}}
            d += timedelta(days=1)
        try:
            if mt5.terminal_info() is None and not mt5.initialize():
                return list(days.values())
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
                day = datetime.fromtimestamp(thai_time.server_to_epoch(int(dl.time)), th).date()
                if day not in days:
                    continue
                p = float(dl.profit) + float(getattr(dl, "commission", 0.0)) + float(getattr(dl, "swap", 0.0))
                days[day]["profit"] += p

                plan = pos_plan_map.get(dl.position_id)
                if not plan and dl.comment:
                    plan = plan_config.base_plan(dl.comment)
                if not plan:
                    plan = "เข้าเอง" if getattr(dl, "magic", 0) == 0 else "อื่นๆ"
                elif plan in ("Manual-Quick", "Manual"):
                    plan = "เข้าเอง"

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
        return list(days.values())

    def get_plans_summary_stats(self, start_date, end_date) -> dict:
        """
        สรุปสถิติความสำเร็จรายแผน และภาพรวมทั้งหมด ในช่วงวันที่กำหนด
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
        try:
            if mt5.terminal_info() is None and not mt5.initialize():
                return res
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
                day = datetime.fromtimestamp(thai_time.server_to_epoch(int(dl.time)), th).date()
                if day < start_date or day > end_date:
                    continue
                p = float(dl.profit) + float(getattr(dl, "commission", 0.0)) + float(getattr(dl, "swap", 0.0))

                plan = pos_plan_map.get(dl.position_id)
                if not plan and dl.comment:
                    plan = plan_config.base_plan(dl.comment)
                if not plan:
                    plan = "เข้าเอง" if getattr(dl, "magic", 0) == 0 else "อื่นๆ"
                elif plan in ("Manual-Quick", "Manual"):
                    plan = "เข้าเอง"

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
        except Exception:
            pass
        return res

    def get_plans_condition_status(self, symbol: str = "XAUUSD") -> dict:
        """
        ประเมินสถานะเงื่อนไขการเข้าไม้เรียลไทม์ของทั้ง 6 แผนเทรด (P1-P6) ณ ราคาปัจจุบัน
        คืนค่า dict ข้อมูลแต่ละแผน: label, side, matched (เข้าแล้วกี่ข้อ), total, pct, items ([✓/✗ ข้อความ])
        มีระบบแคช 1.5 วินาทีเพื่อป้องกันความหน่วง
        """
        now = time.time()
        if self._plans_status_cache and (now - self._plans_status_time < 1.5):
            return self._plans_status_cache

        try:
            import pandas as pd
            import numpy as np

            if mt5.terminal_info() is None and not mt5.initialize():
                return self._plans_status_cache or {}

            rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
            rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 260)
            rates_h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 260)
            tick = mt5.symbol_info_tick(symbol)

            if rates_m15 is None or rates_h1 is None or rates_h4 is None or len(rates_m15) < 55 or len(rates_h1) < 205:
                return self._plans_status_cache or {}

            df_m15 = pd.DataFrame(rates_m15)
            df_h1 = pd.DataFrame(rates_h1)
            df_h4 = pd.DataFrame(rates_h4)

            cur_price = float(tick.bid) if (tick and tick.bid) else float(df_m15['close'].iloc[-1])

            # --- H4 Indicators ---
            h4_c = df_h4['close']
            h4_ma10 = float(h4_c.rolling(10).mean().iloc[-2])
            h4_ma30 = float(h4_c.rolling(30).mean().iloc[-2])
            is_uptrend_h4 = h4_ma10 > h4_ma30
            h4_diff_pct = ((h4_ma10 - h4_ma30) / h4_ma30) * 100 if h4_ma30 else 0
            h4_ma200 = float(h4_c.rolling(200).mean().iloc[-2]) if len(h4_c) >= 202 else float('nan')
            h4_close = float(h4_c.iloc[-2])
            h4_lt_dir = 1 if h4_close > h4_ma200 else (-1 if h4_close < h4_ma200 else 0)

            tr_h4 = pd.concat([
                df_h4['high'] - df_h4['low'],
                (df_h4['high'] - df_h4['close'].shift()).abs(),
                (df_h4['low'] - df_h4['close'].shift()).abs()
            ], axis=1).max(axis=1)
            atr_h4 = float(tr_h4.rolling(14).mean().iloc[-2])

            ma5_h4 = h4_c.rolling(5).mean()
            h4_ma5_slope = (ma5_h4.iloc[-2] - ma5_h4.iloc[-4]) / atr_h4 if (atr_h4 and atr_h4 > 0 and len(ma5_h4) >= 5) else 0.0

            # --- H1 Indicators ---
            h1_c = df_h1['close']
            h1_ma5 = float(h1_c.rolling(5).mean().iloc[-2])
            h1_ma10 = float(h1_c.rolling(10).mean().iloc[-2])
            prev_h1_ma5 = float(h1_c.rolling(5).mean().iloc[-3])
            prev_h1_ma10 = float(h1_c.rolling(10).mean().iloc[-3])

            if len(h1_c) >= 202:
                a, b, c = (h1_c.rolling(k).mean().iloc[-2] for k in (100, 150, 200))
                h1_stack_dir = -1 if a < b < c else (1 if a > b > c else 0)
            else:
                h1_stack_dir = 0

            is_uptrend_h1 = h1_ma5 >= h1_ma10

            sr_h1 = bot_core.find_sr_levels(df_h1, cur_price)
            support = float(sr_h1.get("support", 0.0))
            resistance = float(sr_h1.get("resistance", 0.0))

            bb_mid_h1 = float(h1_c.rolling(20).mean().iloc[-2])
            bb_std_h1 = float(h1_c.rolling(20).std().iloc[-2])
            bb_upper_h1 = bb_mid_h1 + 2 * bb_std_h1
            bb_lower_h1 = bb_mid_h1 - 2 * bb_std_h1

            ema12 = h1_c.ewm(span=12, adjust=False).mean()
            ema26 = h1_c.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            macd_hist_h1 = float((macd_line - signal_line).iloc[-2])
            prev_macd_hist_h1 = float((macd_line - signal_line).iloc[-3])

            p6_sar, p6_dir = bot_core.psar_series(df_h1['high'].values, df_h1['low'].values, *bot_core.P6_SAR)
            sar_val = float(p6_sar[-2])
            sar_dir = int(p6_dir[-2])

            # --- M15 Indicators ---
            m15_c = df_m15['close']
            m15_ma5 = float(m15_c.rolling(5).mean().iloc[-2])
            m15_ma13 = float(m15_c.rolling(13).mean().iloc[-2])
            prev_m15_ma5 = float(m15_c.rolling(5).mean().iloc[-3])
            prev_m15_ma13 = float(m15_c.rolling(13).mean().iloc[-3])
            m15_ma50 = float(m15_c.rolling(50).mean().iloc[-2])

            delta = m15_c.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi_m15 = float((100 - (100 / (1 + (gain / (loss + 1e-9))))).iloc[-2])

            tr_m15 = pd.concat([
                df_m15['high'] - df_m15['low'],
                (df_m15['high'] - df_m15['close'].shift()).abs(),
                (df_m15['low'] - df_m15['close'].shift()).abs()
            ], axis=1).max(axis=1)
            atr_m15 = float(tr_m15.rolling(14).mean().iloc[-2])

            last_closed_m15 = df_m15.iloc[-2]
            m15_open = float(last_closed_m15['open'])
            m15_high = float(last_closed_m15['high'])
            m15_low = float(last_closed_m15['low'])
            m15_close = float(last_closed_m15['close'])
            lower_wick = min(m15_open, m15_close) - m15_low
            upper_wick = m15_high - max(m15_open, m15_close)
            lower_wick_ratio = lower_wick / (atr_m15 + 1e-9)
            upper_wick_ratio = upper_wick / (atr_m15 + 1e-9)

            df_div = bot_core.add_divergence_features(df_m15.copy(), lookback=14)
            bull_div = bool(df_div['bull_div'].iloc[-2] > 0.5) if 'bull_div' in df_div else False
            bear_div = bool(df_div['bear_div'].iloc[-2] > 0.5) if 'bear_div' in df_div else False

            ai_prob_up = 0.50
            ai_prob_down = 0.50
            try:
                import ai_outlook
                out = ai_outlook.get_cached_outlook()
                if out and "horizons" in out:
                    h1_hz = out["horizons"].get("1h", {})
                    ai_prob_up = h1_hz.get("prob_up", 50.0) / 100.0
                    ai_prob_down = h1_hz.get("prob_down", 50.0) / 100.0
            except Exception:
                pass

            results = {}

            # ===== Plan 1: MA-Cross-Trend (M15) =====
            p1_side = "BUY" if h1_stack_dir == 1 else ("SELL" if h1_stack_dir == -1 else ("BUY" if m15_ma5 >= m15_ma13 else "SELL"))
            p1_items = []
            if p1_side == "BUY":
                c1 = h1_stack_dir == 1
                p1_items.append({"name": "เทรนด์ H1", "ok": c1, "desc": "MA100>150>200 เรียงตัวขาขึ้น" if c1 else "ยังไม่เรียงตัวขาขึ้น (MA100>150>200)"})
                c2 = (prev_m15_ma5 <= prev_m15_ma13 and m15_ma5 > m15_ma13) or (m15_ma5 > m15_ma13)
                p1_items.append({"name": "MA5/13 M15", "ok": c2, "desc": f"MA5 ({m15_ma5:.2f}) > MA13 ({m15_ma13:.2f})" if c2 else f"MA5 ({m15_ma5:.2f}) < MA13 ({m15_ma13:.2f})"})
                c3 = 50 < rsi_m15 < 70
                p1_items.append({"name": "RSI M15", "ok": c3, "desc": f"RSI อยู่ช่วง 50–70 ({rsi_m15:.1f})" if c3 else f"RSI ({rsi_m15:.1f}) ไม่อยู่ใน 50–70"})
                c4 = m15_close > m15_ma50
                p1_items.append({"name": "MA50 M15", "ok": c4, "desc": f"ราคา {m15_close:.2f} > MA50 {m15_ma50:.2f}" if c4 else f"ราคา {m15_close:.2f} < MA50 {m15_ma50:.2f}"})
            else:
                c1 = h1_stack_dir == -1
                p1_items.append({"name": "เทรนด์ H1", "ok": c1, "desc": "MA100<150<200 เรียงตัวขาลง" if c1 else "ยังไม่เรียงตัวขาลง (MA100<150<200)"})
                c2 = (prev_m15_ma5 >= prev_m15_ma13 and m15_ma5 < m15_ma13) or (m15_ma5 < m15_ma13)
                p1_items.append({"name": "MA5/13 M15", "ok": c2, "desc": f"MA5 ({m15_ma5:.2f}) < MA13 ({m15_ma13:.2f})" if c2 else f"MA5 ({m15_ma5:.2f}) > MA13 ({m15_ma13:.2f})"})
                c3 = 30 < rsi_m15 < 50
                p1_items.append({"name": "RSI M15", "ok": c3, "desc": f"RSI อยู่ช่วง 30–50 ({rsi_m15:.1f})" if c3 else f"RSI ({rsi_m15:.1f}) ไม่อยู่ใน 30–50"})
                c4 = m15_close < m15_ma50
                p1_items.append({"name": "MA50 M15", "ok": c4, "desc": f"ราคา {m15_close:.2f} < MA50 {m15_ma50:.2f}" if c4 else f"ราคา {m15_close:.2f} > MA50 {m15_ma50:.2f}"})

            m1 = sum(1 for it in p1_items if it["ok"])
            results["P1"] = {
                "name": "MA-Cross-Trend", "label": "P1 · M15", "side": p1_side,
                "matched": m1, "total": 4, "pct": int(m1 / 4 * 100), "items": p1_items
            }

            # ===== Plan 2: MA-Cross-H1-Trend (H1) =====
            p2_side = "BUY" if is_uptrend_h4 else "SELL"
            p2_items = []
            if p2_side == "BUY":
                c1 = is_uptrend_h4
                p2_items.append({"name": "เทรนด์ H4", "ok": c1, "desc": f"H4 MA10>MA30 (+{h4_diff_pct:.2f}%)" if c1 else f"H4 ยังไม่ใช่ขาขึ้น ({h4_diff_pct:.2f}%)"})
                c2 = (prev_h1_ma5 <= prev_h1_ma10 and h1_ma5 > h1_ma10) or (h1_ma5 > h1_ma10)
                p2_items.append({"name": "MA5/10 H1", "ok": c2, "desc": f"H1 MA5 ({h1_ma5:.2f}) > MA10 ({h1_ma10:.2f})" if c2 else f"H1 MA5 ({h1_ma5:.2f}) < MA10 ({h1_ma10:.2f})"})
                c3 = h4_ma5_slope > 0
                p2_items.append({"name": "ความชัน H4", "ok": c3, "desc": f"MA5 H4 ชันขึ้น (+{h4_ma5_slope:.2f})" if c3 else f"MA5 H4 ชันลง ({h4_ma5_slope:.2f})"})
                c4 = h4_lt_dir == 1
                p2_items.append({"name": "MA200 H4", "ok": c4, "desc": f"ราคา {h4_close:.2f} > MA200 {h4_ma200:.2f}" if c4 else f"ราคาต่ำกว่า MA200 H4 ({h4_ma200:.2f})"})
            else:
                c1 = not is_uptrend_h4
                p2_items.append({"name": "เทรนด์ H4", "ok": c1, "desc": f"H4 MA10<MA30 ({h4_diff_pct:.2f}%)" if c1 else f"H4 ยังไม่ใช่ขาลง (+{h4_diff_pct:.2f}%)"})
                c2 = (prev_h1_ma5 >= prev_h1_ma10 and h1_ma5 < h1_ma10) or (h1_ma5 < h1_ma10)
                p2_items.append({"name": "MA5/10 H1", "ok": c2, "desc": f"H1 MA5 ({h1_ma5:.2f}) < MA10 ({h1_ma10:.2f})" if c2 else f"H1 MA5 ({h1_ma5:.2f}) > MA10 ({h1_ma10:.2f})"})
                c3 = h4_ma5_slope < 0
                p2_items.append({"name": "ความชัน H4", "ok": c3, "desc": f"MA5 H4 ชันลง ({h4_ma5_slope:.2f})" if c3 else f"MA5 H4 ชันขึ้น (+{h4_ma5_slope:.2f})"})
                c4 = h4_lt_dir == -1
                p2_items.append({"name": "MA200 H4", "ok": c4, "desc": f"ราคา {h4_close:.2f} < MA200 {h4_ma200:.2f}" if c4 else f"ราคาสูงกว่า MA200 H4 ({h4_ma200:.2f})"})

            m2 = sum(1 for it in p2_items if it["ok"])
            results["P2"] = {
                "name": "MA-Cross-H1-Trend", "label": "P2 · H1", "side": p2_side,
                "matched": m2, "total": 4, "pct": int(m2 / 4 * 100), "items": p2_items
            }

            # ===== Plan 3: SMC-LiquidityHunt (H1) =====
            dist_sup = abs(cur_price - support) if support else 9999
            dist_res = abs(resistance - cur_price) if resistance else 9999
            p3_side = "BUY" if dist_sup <= dist_res else "SELL"
            p3_items = []
            if p3_side == "BUY":
                c1 = m15_low < support and m15_close >= support
                p3_items.append({"name": "กวาดแนวรับ (Sweep)", "ok": c1, "desc": f"Low กวาดแนวรับ {support:.2f} แล้วดึงกลับ" if c1 else f"ยังไม่กวาดแนวรับ {support:.2f}"})
                c2 = 0.25 <= lower_wick_ratio <= 2.50
                p3_items.append({"name": "ไส้ล่างปฏิเสธ", "ok": c2, "desc": f"ไส้ล่างยาว {lower_wick_ratio:.2f} ATR (≥0.25)" if c2 else f"ไส้ล่าง {lower_wick_ratio:.2f} ATR (<0.25)"})
                c3 = is_uptrend_h1 and h1_stack_dir == 1
                p3_items.append({"name": "เทรนด์ H1", "ok": c3, "desc": "H1 ขาขึ้น + MA100>150>200" if c3 else "เทรนด์ H1 ยังไม่เป็นขาขึ้นสมบูรณ์"})
                c4 = ai_prob_up >= 0.50
                p3_items.append({"name": "AI ทายขึ้น ≥50%", "ok": c4, "desc": f"AI UP {ai_prob_up:.1%}" if c4 else f"AI UP {ai_prob_up:.1%} (<50%)"})
            else:
                c1 = m15_high > resistance and m15_close <= resistance
                p3_items.append({"name": "กวาดแนวต้าน (Sweep)", "ok": c1, "desc": f"High กวาดแนวต้าน {resistance:.2f} แล้วดึงกลับ" if c1 else f"ยังไม่กวาดแนวต้าน {resistance:.2f}"})
                c2 = 0.25 <= upper_wick_ratio <= 2.50
                p3_items.append({"name": "ไส้บนปฏิเสธ", "ok": c2, "desc": f"ไส้บนยาว {upper_wick_ratio:.2f} ATR (≥0.25)" if c2 else f"ไส้บน {upper_wick_ratio:.2f} ATR (<0.25)"})
                c3 = (not is_uptrend_h1) and h1_stack_dir == -1
                p3_items.append({"name": "เทรนด์ H1", "ok": c3, "desc": "H1 ขาลง + MA100<150<200" if c3 else "เทรนด์ H1 ยังไม่เป็นขาลงสมบูรณ์"})
                c4 = ai_prob_down >= 0.50
                p3_items.append({"name": "AI ทายลง ≥50%", "ok": c4, "desc": f"AI DOWN {ai_prob_down:.1%}" if c4 else f"AI DOWN {ai_prob_down:.1%} (<50%)"})

            m3 = sum(1 for it in p3_items if it["ok"])
            results["P3"] = {
                "name": "SMC-LiquidityHunt", "label": "P3 · H1 (SMC)", "side": p3_side,
                "matched": m3, "total": 4, "pct": int(m3 / 4 * 100), "items": p3_items
            }

            # ===== Plan 4: SR-SwingBounce (H1) =====
            p4_side = "BUY" if dist_sup <= dist_res else "SELL"
            p4_items = []
            if p4_side == "BUY":
                c1 = (abs(cur_price - support) <= (atr_m15 * 1.0)) and (cur_price >= support)
                p4_items.append({"name": "ประชิดแนวรับ (≤1 ATR)", "ok": c1, "desc": f"ห่างแนวรับ {dist_sup:.2f} (≤{atr_m15:.2f})" if c1 else f"ห่างแนวรับ {dist_sup:.2f} (>1 ATR)"})
                c2 = (lower_wick_ratio >= 0.20) or (m15_close > m15_open)
                p4_items.append({"name": "แท่งเด้งกลับ / ไส้ล่าง", "ok": c2, "desc": "แท่งเขียวหรือมีไส้ล่างปฏิเสธราคา" if c2 else "ยังไม่มีแท่งปฏิเสธราคา"})
                c3 = bull_div
                p4_items.append({"name": "Bullish Divergence", "ok": c3, "desc": "พบ RSI Bullish Divergence" if c3 else "ไม่พบ Bullish Divergence"})
                c4 = ai_prob_up >= 0.51 and h1_stack_dir != -1
                p4_items.append({"name": "AI ยืนยัน ≥51%", "ok": c4, "desc": f"AI UP {ai_prob_up:.1%} และ H1 ไม่ใช่ขาลง" if c4 else f"AI UP {ai_prob_up:.1%} หรือ H1 ขาลง"})
            else:
                c1 = (abs(resistance - cur_price) <= (atr_m15 * 1.0)) and (cur_price <= resistance)
                p4_items.append({"name": "ประชิดแนวต้าน (≤1 ATR)", "ok": c1, "desc": f"ห่างแนวต้าน {dist_res:.2f} (≤{atr_m15:.2f})" if c1 else f"ห่างแนวต้าน {dist_res:.2f} (>1 ATR)"})
                c2 = (upper_wick_ratio >= 0.20) or (m15_close < m15_open)
                p4_items.append({"name": "แท่งเด้งกลับ / ไส้บน", "ok": c2, "desc": "แท่งแดงหรือมีไส้บนปฏิเสธราคา" if c2 else "ยังไม่มีแท่งปฏิเสธราคา"})
                c3 = bear_div
                p4_items.append({"name": "Bearish Divergence", "ok": c3, "desc": "พบ RSI Bearish Divergence" if c3 else "ไม่พบ Bearish Divergence"})
                c4 = ai_prob_down >= 0.51 and h1_stack_dir != 1
                p4_items.append({"name": "AI ยืนยัน ≥51%", "ok": c4, "desc": f"AI DOWN {ai_prob_down:.1%} และ H1 ไม่ใช่ขาขึ้น" if c4 else f"AI DOWN {ai_prob_down:.1%} หรือ H1 ขาขึ้น"})

            m4 = sum(1 for it in p4_items if it["ok"])
            results["P4"] = {
                "name": "SR-SwingBounce", "label": "P4 · H1 (SR)", "side": p4_side,
                "matched": m4, "total": 4, "pct": int(m4 / 4 * 100), "items": p4_items
            }

            # ===== Plan 5: BB-H1-Reversion (H1) =====
            dist_bb_low = abs(cur_price - bb_lower_h1)
            dist_bb_up = abs(bb_upper_h1 - cur_price)
            p5_side = "BUY" if dist_bb_low <= dist_bb_up else "SELL"
            p5_items = []
            if p5_side == "BUY":
                c1 = m15_low < bb_lower_h1 and m15_close >= bb_lower_h1
                p5_items.append({"name": "หลุด BB ล่างแล้วดีดกลับ", "ok": c1, "desc": f"Low หลุด {bb_lower_h1:.2f} แล้วปิดกลับขึ้นมา" if c1 else f"ยังไม่หลุดกรอบ BB ล่าง ({bb_lower_h1:.2f})"})
                c2 = lower_wick_ratio >= 0.20
                p5_items.append({"name": "ไส้ล่างปฏิเสธ", "ok": c2, "desc": f"ไส้ล่างยาว {lower_wick_ratio:.2f} ATR (≥0.20)" if c2 else f"ไส้ล่าง {lower_wick_ratio:.2f} (<0.20)"})
                c3 = macd_hist_h1 >= prev_macd_hist_h1
                p5_items.append({"name": "MACD H1 หมดแรง", "ok": c3, "desc": "MACD Histogram เริ่มยกตัวขึ้น" if c3 else "MACD Histogram ยังทำ New Low"})
                c4 = bull_div
                p5_items.append({"name": "Bullish Divergence", "ok": c4, "desc": "พบ Bullish Divergence" if c4 else "ไม่พบ Divergence"})
                c5 = ai_prob_up >= 0.50
                p5_items.append({"name": "AI ทายขึ้น ≥50%", "ok": c5, "desc": f"AI UP {ai_prob_up:.1%}" if c5 else f"AI UP {ai_prob_up:.1%} (<50%)"})
            else:
                c1 = m15_high > bb_upper_h1 and m15_close <= bb_upper_h1
                p5_items.append({"name": "หลุด BB บนแล้วดึงกลับ", "ok": c1, "desc": f"High ทะลุ {bb_upper_h1:.2f} แล้วปิดกลับลงมา" if c1 else f"ยังไม่หลุดกรอบ BB บน ({bb_upper_h1:.2f})"})
                c2 = upper_wick_ratio >= 0.20
                p5_items.append({"name": "ไส้บนปฏิเสธ", "ok": c2, "desc": f"ไส้บนยาว {upper_wick_ratio:.2f} ATR (≥0.20)" if c2 else f"ไส้บน {upper_wick_ratio:.2f} (<0.20)"})
                c3 = macd_hist_h1 <= prev_macd_hist_h1
                p5_items.append({"name": "MACD H1 หมดแรง", "ok": c3, "desc": "MACD Histogram เริ่มชะลอลง" if c3 else "MACD Histogram ยังทำ New High"})
                c4 = bear_div
                p5_items.append({"name": "Bearish Divergence", "ok": c4, "desc": "พบ Bearish Divergence" if c4 else "ไม่พบ Divergence"})
                c5 = ai_prob_down >= 0.50
                p5_items.append({"name": "AI ทายลง ≥50%", "ok": c5, "desc": f"AI DOWN {ai_prob_down:.1%}" if c5 else f"AI DOWN {ai_prob_down:.1%} (<50%)"})

            m5 = sum(1 for it in p5_items if it["ok"])
            results["P5"] = {
                "name": "BB-H1-Reversion", "label": "P5 · H1 (BB)", "side": p5_side,
                "matched": m5, "total": 5, "pct": int(m5 / 5 * 100), "items": p5_items
            }

            # ===== Plan 6: PSAR-H1-Trend (H1) =====
            p6_side = "BUY" if sar_dir == 1 else "SELL"
            p6_items = []
            if p6_side == "BUY":
                c1 = sar_dir == 1
                p6_items.append({"name": "SAR อยู่ใต้ราคา", "ok": c1, "desc": f"SAR {sar_val:.2f} อยู่ใต้ราคา (ขาขึ้น)" if c1 else f"SAR อยู่เหนือราคา ({sar_val:.2f})"})
                c2 = is_uptrend_h4
                p6_items.append({"name": "เทรนด์ H4", "ok": c2, "desc": f"H4 ขาขึ้น (MA10>MA30 +{h4_diff_pct:.2f}%)" if c2 else "H4 ไม่ใช่ขาขึ้น"})
                c3 = h4_lt_dir == 1
                p6_items.append({"name": "เหนือ MA200 H4", "ok": c3, "desc": f"ราคา {h4_close:.2f} > MA200 {h4_ma200:.2f}" if c3 else "ราคาต่ำกว่า MA200 H4"})
            else:
                c1 = sar_dir == -1
                p6_items.append({"name": "SAR อยู่เหนือราคา", "ok": c1, "desc": f"SAR {sar_val:.2f} อยู่เหนือราคา (ขาลง)" if c1 else f"SAR อยู่ใต้ราคา ({sar_val:.2f})"})
                c2 = not is_uptrend_h4
                p6_items.append({"name": "เทรนด์ H4", "ok": c2, "desc": f"H4 ขาลง (MA10<MA30 {h4_diff_pct:.2f}%)" if c2 else "H4 ไม่ใช่ขาลง"})
                c3 = h4_lt_dir == -1
                p6_items.append({"name": "ใต้ MA200 H4", "ok": c3, "desc": f"ราคา {h4_close:.2f} < MA200 {h4_ma200:.2f}" if c3 else "ราคาสูงกว่า MA200 H4"})

            m6 = sum(1 for it in p6_items if it["ok"])
            results["P6"] = {
                "name": "PSAR-H1-Trend", "label": "P6 · H1 (PSAR)", "side": p6_side,
                "matched": m6, "total": 3, "pct": int(m6 / 3 * 100), "items": p6_items
            }

            self._plans_status_cache = results
            self._plans_status_time = now
            return results
        except Exception:
            return self._plans_status_cache or {}

# Singleton Controller Instance
bot_ctrl = BotController()
