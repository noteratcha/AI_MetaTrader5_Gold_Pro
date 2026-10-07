"""
เวลาที่แสดงในโปรแกรมทั้งหมดเป็นเวลาประเทศไทย (UTC+7) เสมอ — ไม่ขึ้นกับโซนเวลาของเครื่อง/VPS (ผู้ใช้กำหนด 8 ต.ค. 2026)
- เวลาจาก MT5 (Deal/Position/แท่งเทียน) เป็นเวลาเซิร์ฟเวอร์โบรกเกอร์ → ลบส่วนต่างเซิร์ฟเวอร์ (คำนวณจาก tick ล่าสุด) ก่อนแสดง
"""
import time
from datetime import datetime, timedelta, timezone

TH = timezone(timedelta(hours=7))
_off = {"value": None, "at": 0.0}
_DEFAULT_SERVER_OFFSET = 3 * 3600   # FBS ใช้ UTC+3 — ใช้เมื่อยังอ่าน tick จาก MT5 ไม่ได้


def now() -> datetime:
    return datetime.now(TH)


def fmt_now(fmt: str = "%H:%M:%S") -> str:
    return now().strftime(fmt)


def from_epoch(ts: float, fmt: str = "%H:%M:%S") -> str:
    """เวลาจริง (epoch UTC เช่น time.time()) → ข้อความเวลาไทย"""
    return datetime.fromtimestamp(float(ts), TH).strftime(fmt)


def server_offset() -> int:
    """เวลาเซิร์ฟเวอร์ MT5 − เวลาจริง (วินาที ปัดเป็นชั่วโมง) · แคช 5 นาที"""
    if _off["value"] is not None and time.time() - _off["at"] < 300:
        return _off["value"]
    try:
        import MetaTrader5 as mt5
        tick = mt5.symbol_info_tick("XAUUSD")
        if tick and tick.time and time.time() - tick.time < 7 * 86400 + 14 * 3600:
            off = round((tick.time - time.time()) / 3600) * 3600
            if abs(off) <= 14 * 3600:
                _off.update(value=int(off), at=time.time())
                return int(off)
    except Exception:
        pass
    return _off["value"] if _off["value"] is not None else _DEFAULT_SERVER_OFFSET


def from_server(server_ts: float, fmt: str = "%d/%m %H:%M") -> str:
    """เวลาเซิร์ฟเวอร์ MT5 (epoch แบบเวลาโบรกเกอร์) → ข้อความเวลาไทย"""
    return datetime.fromtimestamp(float(server_ts) - server_offset(), TH).strftime(fmt)
