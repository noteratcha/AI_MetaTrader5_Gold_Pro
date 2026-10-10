"""
เวลาที่แสดงในโปรแกรมทั้งหมดเป็นเวลาประเทศไทย (UTC+7) เสมอ — ไม่ขึ้นกับโซนเวลาของเครื่อง/VPS (ผู้ใช้กำหนด 8 ต.ค. 2026)
- เวลาจาก MT5 (Deal/Position/แท่งเทียน) เป็นเวลาเซิร์ฟเวอร์โบรกเกอร์ → แปลงด้วย server_to_epoch() / from_server() ก่อนแสดง
- ส่วนต่างเวลาเซิร์ฟเวอร์ (แหล่งเดียวของทั้งโปรแกรม): กฎ EET/EEST ของ FBS (+3 ชม. ช่วง DST ยุโรป ไม่งั้น +2 ชม.)
  คิดตามวันที่ของแต่ละเวลา (ดีลก่อน/หลังเปลี่ยน DST แสดงถูกทั้งคู่)
- วัดจาก tick ได้เฉพาะตอนยืนยันว่า tick สด — ตลาดปิด (เสาร์–อาทิตย์/ช่วงพักรายวัน) tick ล่าสุดเก่าหลายชั่วโมง
  ถ้าเอามาคำนวณตรง ๆ จะได้ส่วนต่างผิด (เช่น วันเสาร์ได้ −3 แทน +3 → เวลาเพี้ยน 6 ชม.) — บั๊กที่แก้ 8 ต.ค. 2026
"""
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache

TH = timezone(timedelta(hours=7))
_srv = {"mode": "eu", "fixed": 0, "checked": 0.0, "tick_msc": None, "tick_at": 0.0}
_CHECK_EVERY = 300        # วัดซ้ำทุก 5 นาที
_FRESH_WINDOW = 900       # มี tick ใหม่เข้ามาภายใน 15 นาทีนับจากการวัดครั้งก่อน = tick สด (อายุ < 0.25 ชม. ปัดเป็นชั่วโมงได้ถูก)


def now() -> datetime:
    return datetime.now(TH)


def fmt_now(fmt: str = "%H:%M:%S") -> str:
    return now().strftime(fmt)


def from_epoch(ts: float, fmt: str = "%H:%M:%S") -> str:
    """เวลาจริง (epoch UTC เช่น time.time()) → ข้อความเวลาไทย"""
    return datetime.fromtimestamp(float(ts), TH).strftime(fmt)


@lru_cache(maxsize=None)
def _eu_dst_bounds(year: int):
    """ช่วง DST ยุโรปของปีนั้น (epoch UTC): อาทิตย์สุดท้ายของ มี.ค. 01:00 UTC → อาทิตย์สุดท้ายของ ต.ค. 01:00 UTC"""
    def last_sunday(month):
        d = datetime(year, month + 1, 1) - timedelta(days=1)
        return d - timedelta(days=(d.weekday() + 1) % 7)
    start = (last_sunday(3) + timedelta(hours=1)).replace(tzinfo=timezone.utc).timestamp()
    end = (last_sunday(10) + timedelta(hours=1)).replace(tzinfo=timezone.utc).timestamp()
    return start, end


def eu_offset(utc_ts: float) -> int:
    """ส่วนต่างเวลาเซิร์ฟเวอร์แบบ EET/EEST (วินาที) ณ เวลาจริงนั้น"""
    start, end = _eu_dst_bounds(datetime.fromtimestamp(float(utc_ts), timezone.utc).year)
    return 3 * 3600 if start <= float(utc_ts) < end else 2 * 3600


def _refresh():
    """ตรวจว่าเซิร์ฟเวอร์ใช้กฎ EET/EEST จริงไหม (วัดจาก tick ล่าสุดของทอง/BTC ที่ซื้อขาย 24 ชม.) — ทุก 5 นาที"""
    now_ts = time.time()
    if now_ts - _srv["checked"] < _CHECK_EVERY:
        return
    _srv["checked"] = now_ts
    try:
        import MetaTrader5 as mt5
        best = None
        for sym in ("XAUUSD", "BTCUSD"):
            t = mt5.symbol_info_tick(sym)
            if t and t.time and (best is None or t.time_msc > best.time_msc):
                best = t
    except Exception:
        return
    if best is None:
        return
    measured = round((best.time - now_ts) / 3600) * 3600
    prev_msc, prev_at = _srv["tick_msc"], _srv["tick_at"]
    _srv.update(tick_msc=best.time_msc, tick_at=now_ts)
    if abs(measured) > 14 * 3600:
        return
    if measured == eu_offset(now_ts):
        _srv["mode"] = "eu"
    elif prev_msc is not None and best.time_msc != prev_msc and now_ts - prev_at <= _FRESH_WINDOW:
        # tick สดยืนยันแล้วว่าไม่ตรงกฎ EET/EEST → ใช้ส่วนต่างคงที่ที่วัดได้ (โบรกเกอร์/เซิร์ฟเวอร์อื่น)
        _srv.update(mode="fixed", fixed=int(measured))


def server_offset_at(server_ts: float = None) -> int:
    """เวลาเซิร์ฟเวอร์ − เวลาจริง (วินาที) ณ เวลาเซิร์ฟเวอร์นั้น (ไม่ระบุ = ตอนนี้)"""
    _refresh()
    if _srv["mode"] == "fixed":
        return _srv["fixed"]
    return eu_offset(time.time() if server_ts is None else float(server_ts) - 3 * 3600)


def server_offset() -> int:
    """ส่วนต่างเวลาเซิร์ฟเวอร์ ณ ตอนนี้ (วินาที)"""
    return server_offset_at(None)


def server_to_epoch(server_ts: float) -> float:
    """เวลาเซิร์ฟเวอร์ MT5 (epoch แบบเวลาโบรกเกอร์) → epoch จริง (UTC)"""
    return float(server_ts) - server_offset_at(server_ts)


def from_server(server_ts: float, fmt: str = "%d/%m %H:%M") -> str:
    """เวลาเซิร์ฟเวอร์ MT5 → ข้อความเวลาไทย"""
    return datetime.fromtimestamp(server_to_epoch(server_ts), TH).strftime(fmt)


def get_gold_market_status(dt: datetime = None) -> dict:
    """
    คำนวณสถานะตลาดทองคำ (XAUUSD) ตามเวลาประเทศไทย (UTC+7):
    - เปิดทำการ: วันจันทร์ 05:00 น. ถึง วันเสาร์ 04:00 น.
    - พักเบรกประจำวัน: อังคาร–ศุกร์ 04:00 – 05:00 น.
    - ปิดสุดสัปดาห์: วันเสาร์ 04:00 น. ถึง วันจันทร์ 05:00 น.
    """
    t = dt if dt is not None else now()
    if t.tzinfo is None:
        t = t.replace(tzinfo=TH)
    else:
        t = t.astimezone(TH)

    weekday = t.weekday()  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    hm = t.hour * 60 + t.minute

    # 1. วันเสาร์ (5): หลัง 04:00 น. ปิดยาวจนถึงเช้าวันจันทร์
    if weekday == 5:
        if hm >= 4 * 60:
            next_open = (t + timedelta(days=2)).replace(hour=5, minute=0, second=0, microsecond=0)
            diff = next_open - t
            total_sec = max(0, int(diff.total_seconds()))
            days = total_sec // 86400
            hours = (total_sec % 86400) // 3600
            mins = (total_sec % 3600) // 60
            countdown = f"ในอีก {days} วัน {hours} ชม. {mins} นาที" if days > 0 else f"ในอีก {hours} ชม. {mins} นาที"
            return {
                "is_open": False,
                "state": "WEEKEND_CLOSED",
                "badge_text": "🔴 ตลาดปิด (เสาร์–อาทิตย์)",
                "headline": "🔴 ตลาดทองคำปิดทำการ (วันหยุดสุดสัปดาห์ เสาร์–อาทิตย์)",
                "subtext": f"เปิดวันจันทร์ เวลา 05:00 น. ({countdown})",
                "short_desc": "🔴 ตลาดปิด · เปิด จ. 05:00 น.",
                "countdown": countdown,
                "next_open_dt": next_open,
            }
        else:
            # ก่อน 04:00 น. วันเสาร์: ยังเปิดอยู่ กำลังจะปิดสุดสัปดาห์
            next_close = t.replace(hour=4, minute=0, second=0, microsecond=0)
            diff = next_close - t
            total_sec = max(0, int(diff.total_seconds()))
            hours = total_sec // 3600
            mins = (total_sec % 3600) // 60
            return {
                "is_open": True,
                "state": "OPEN",
                "badge_text": "🟢 ตลาดเปิดทำการ",
                "headline": "🟢 ตลาดทองคำเปิดทำการปกติ",
                "subtext": f"จะปิดสุดสัปดาห์ในอีก {hours} ชม. {mins} นาที (เวลา 04:00 น.)",
                "short_desc": "🟢 ตลาดเปิดปกติ",
                "countdown": f"{hours} ชม. {mins} นาที",
                "next_open_dt": None,
            }

    # 2. วันอาทิตย์ (6): ปิดตลอดทั้งวัน
    if weekday == 6:
        next_open = (t + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
        diff = next_open - t
        total_sec = max(0, int(diff.total_seconds()))
        hours = total_sec // 3600
        mins = (total_sec % 3600) // 60
        countdown = f"ในอีก {hours} ชม. {mins} นาที"
        return {
            "is_open": False,
            "state": "WEEKEND_CLOSED",
            "badge_text": "🔴 ตลาดปิด (วันอาทิตย์)",
            "headline": "🔴 ตลาดทองคำปิดทำการ (วันหยุดสุดสัปดาห์)",
            "subtext": f"เปิดวันจันทร์ เวลา 05:00 น. ({countdown})",
            "short_desc": "🔴 ตลาดปิด · เปิด จ. 05:00 น.",
            "countdown": countdown,
            "next_open_dt": next_open,
        }

    # 3. วันจันทร์ (0): เช้ามืดก่อน 05:00 น. ยังไม่เปิด
    if weekday == 0 and hm < 5 * 60:
        next_open = t.replace(hour=5, minute=0, second=0, microsecond=0)
        diff = next_open - t
        total_sec = max(0, int(diff.total_seconds()))
        hours = total_sec // 3600
        mins = (total_sec % 3600) // 60
        countdown = f"ในอีก {hours} ชม. {mins} นาที"
        return {
            "is_open": False,
            "state": "PRE_OPEN",
            "badge_text": "🔴 รอเปิดตลาด (เช้าวันจันทร์)",
            "headline": "🔴 ตลาดทองคำยังไม่เปิดทำการ",
            "subtext": f"จะเปิดทำการเช้านี้ เวลา 05:00 น. ({countdown})",
            "short_desc": "🔴 รอเปิด 05:00 น.",
            "countdown": countdown,
            "next_open_dt": next_open,
        }

    # 4. วันอังคาร - ศุกร์ (1, 2, 3, 4): ช่วงพักเบรกประจำวัน 04:00 - 05:00 น.
    if weekday in (1, 2, 3, 4) and 4 * 60 <= hm < 5 * 60:
        next_open = t.replace(hour=5, minute=0, second=0, microsecond=0)
        diff = next_open - t
        mins = max(1, int(diff.total_seconds()) // 60)
        return {
            "is_open": False,
            "state": "DAILY_BREAK",
            "badge_text": "🟡 พักเบรกประจำวัน",
            "headline": "🟡 ตลาดทองคำพักเบรกประจำวัน (04:00 – 05:00 น.)",
            "subtext": f"จะเปิดทำการต่อในอีก {mins} นาที (เวลา 05:00 น.)",
            "short_desc": "🟡 พักเบรก · เปิด 05:00 น.",
            "countdown": f"{mins} นาที",
            "next_open_dt": next_open,
        }

    # 5. เวลาเปิดทำการปกติ (วันจันทร์ 05:00 ถึง วันเสาร์ 04:00)
    if weekday == 4:
        close_desc = "ปิดตลาดสุดสัปดาห์ วันเสาร์ เวลา 04:00 น."
    elif hm < 4 * 60:
        close_desc = "พักเบรกประจำวัน เวลา 04:00 น."
    else:
        close_desc = "พักเบรกประจำวัน เวลา 04:00 น."

    return {
        "is_open": True,
        "state": "OPEN",
        "badge_text": "🟢 ตลาดเปิดทำการ",
        "headline": "🟢 ตลาดทองคำเปิดทำการปกติ (ซื้อขายได้ 24 ชม.)",
        "subtext": close_desc,
        "short_desc": "🟢 ตลาดเปิดปกติ",
        "countdown": "",
        "next_open_dt": None,
    }

