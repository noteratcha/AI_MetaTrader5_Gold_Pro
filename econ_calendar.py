"""
ปฏิทินเศรษฐกิจ (Economic Calendar) สำหรับ Desktop App
- ดึงจาก GoldBot24 API (/api/calendar — cache บน Vercel) และ fallback ไป feed สาธารณะโดยตรง
- แปลงเวลาเป็นเวลาไทย (UTC+7) และจัดลำดับข่าวที่มีผลต่อทองคำ (USD) ก่อน
"""
import json
import os
import sys
import threading
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from license_manager import API_BASE_URL

FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
INVESTING_URL = "https://th.investing.com/economic-calendar/"
BANGKOK = timezone(timedelta(hours=7))
CACHE_SECONDS = 30 * 60
IMPACT_ORDER = {"High": 3, "Medium": 2, "Low": 1, "Holiday": 0}

_cache = {"events": [], "fetched_at": 0.0, "error": ""}
_BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
DISK_CACHE = os.path.join(_BASE_DIR, "calendar_cache.json")


def _load_disk_cache():
    try:
        with open(DISK_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_disk_cache(raw_events):
    try:
        with open(DISK_CACHE, "w", encoding="utf-8") as f:
            json.dump(raw_events, f, ensure_ascii=False)
    except Exception:
        pass
_lock = threading.Lock()


def _get_json(url: str, timeout: int = 10):
    req = urllib.request.Request(url, headers={"User-Agent": "GoldBot24-Desktop", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _normalize(raw: dict):
    try:
        when = datetime.fromisoformat(str(raw.get("date")).replace("Z", "+00:00")).astimezone(BANGKOK)
    except Exception:
        return None
    return {
        "title": str(raw.get("title") or "").strip(),
        "currency": str(raw.get("currency") or raw.get("country") or "").upper(),
        "impact": str(raw.get("impact") or "Low"),
        "forecast": str(raw.get("forecast") or ""),
        "previous": str(raw.get("previous") or ""),
        "time": when,
    }


def fetch_events(force: bool = False) -> list:
    """คืนรายการข่าวของสัปดาห์นี้ (cache 30 นาที) — ไม่ throw"""
    with _lock:
        if not force and _cache["events"] and time.time() - _cache["fetched_at"] < CACHE_SECONDS:
            return _cache["events"]

    raw_events, error = None, ""
    try:
        data = _get_json(f"{API_BASE_URL.rstrip('/')}/api/calendar")
        raw_events = data.get("events") if isinstance(data, dict) else None
    except Exception as e:
        error = str(e)
    if not raw_events:
        try:
            raw_events = _get_json(FEED_URL)
            error = ""
        except Exception as e:
            error = error or str(e)
    if raw_events:
        _save_disk_cache(raw_events)
    else:
        # ออฟไลน์ / ต้นทางจำกัดจำนวนครั้ง — ใช้ข้อมูลล่าสุดที่เคยโหลดได้
        raw_events = _load_disk_cache()

    events = [ev for ev in (_normalize(r) for r in (raw_events or [])) if ev]
    events.sort(key=lambda ev: ev["time"])
    with _lock:
        if events:
            _cache.update(events=events, fetched_at=time.time(), error="")
        else:
            _cache["error"] = error or "ไม่พบข้อมูลข่าว"
        return _cache["events"]


def last_error() -> str:
    return _cache.get("error", "")


def filter_events(events: list, usd_only: bool = True, min_impact: str = "Medium") -> list:
    floor = IMPACT_ORDER.get(min_impact, 0)
    return [
        ev for ev in events
        if (not usd_only or ev["currency"] == "USD") and IMPACT_ORDER.get(ev["impact"], 0) >= floor
    ]


def next_high_impact(events: list, currency: str = "USD"):
    """ข่าวสำคัญสูงถัดไปที่ยังไม่ถึงเวลา (ใช้แสดงตัวนับถอยหลัง)"""
    now = datetime.now(BANGKOK)
    for ev in events:
        if ev["currency"] == currency and ev["impact"] == "High" and ev["time"] > now - timedelta(minutes=5):
            return ev
    return None


def format_countdown(target: datetime) -> str:
    secs = int((target - datetime.now(BANGKOK)).total_seconds())
    if secs <= 0:
        return "กำลังประกาศ"
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"อีก {days} วัน {hours} ชม."
    if hours:
        return f"อีก {hours} ชม. {minutes} นาที"
    return f"อีก {minutes} นาที"


THAI_DAYS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


def format_day(dt: datetime) -> str:
    return f"{THAI_DAYS[dt.weekday()]} {dt.day:02d}/{dt.month:02d}"
