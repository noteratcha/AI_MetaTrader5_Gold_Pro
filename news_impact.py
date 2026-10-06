"""
วิเคราะห์ผลกระทบข่าวเศรษฐกิจ (USD) ต่อราคาทอง XAUUSD
- ทิศทาง: กฎเศรษฐกิจตามประเภทข่าว — ตัวเลขที่ทำให้ดอลลาร์แข็ง (ดีกว่าคาด) มักกดทองลง และกลับกัน
- แนวโน้มก่อนข่าวออก: เทียบตัวเลขคาดการณ์ (forecast) กับครั้งก่อน (previous)
- ขนาด: สถิติจริงจาก MT5 — ทองขยับเฉลี่ยกี่ % ใน 60 นาที ณ วัน/เวลาเดียวกันตามเวลานิวยอร์ก (ย้อนหลัง ~2 ปี)
- ผลจริง: ข่าวที่ประกาศไปแล้ว วัดว่าทองขยับกี่ % ใน 60 นาทีหลังข่าว
ข้อมูลข่าวจาก feed ไม่มีตัวเลขจริง (actual) จึงวัดผลจากราคาทองแทน
"""
import re
import threading
import time
from datetime import datetime, timedelta, timezone

import json

import MetaTrader5 as mt5

from app_paths import data_path

SYMBOL = "XAUUSD"
WINDOW_MIN = 60
HISTORY_BARS = 50000          # M15 ประมาณ 2 ปี
STATS_TTL = 6 * 3600
HISTORY_FILE = data_path("news_history.json")   # ผลจริงของข่าวที่ผ่านมา {title: {iso_time: %move}} สะสมทุกสัปดาห์

# (คำค้น, ชนิด) — "usd_up": ตัวเลขสูงกว่าคาด = ดอลลาร์แข็ง = ทองลง · "usd_down": สูงกว่าคาด = ทองขึ้น
_RULES = [
    (("unemployment claims", "jobless claims", "continuing claims", "unemployment rate", "challenger job cuts"), "usd_down"),
    (("fomc", "fed chair", "federal funds", "powell", "speaks", "testifies", "minutes", "monetary policy", "press conference",
      "beige book"), "speech"),
    (("non-farm", "nonfarm", "employment change", "adp", "average hourly earnings", "jolts", "job openings",
      "cpi", "ppi", "pce", "inflation", "gdp", "retail sales", "pmi", "ism", "consumer confidence",
      "consumer sentiment", "durable goods", "industrial production", "factory orders", "housing starts",
      "building permits", "home sales", "productivity", "labor cost", "empire state", "philly fed", "manufacturing index",
      "trade balance", "wholesale", "business inventories", "personal spending", "personal income", "capacity utilization",
      "treasury", "bond auction"), "usd_up"),
]
TH_TYPES = {
    "usd_up": "ตัวเลขสูงกว่าคาด → ดอลลาร์แข็ง → ทองมักลง · ต่ำกว่าคาด → ทองมักขึ้น",
    "usd_down": "ตัวเลขสูงกว่าคาด (ตลาดแรงงานอ่อน) → ดอลลาร์อ่อน → ทองมักขึ้น · ต่ำกว่าคาด → ทองมักลง",
    "speech": "ไม่มีตัวเลข — ท่าทีเข้มงวด (Hawkish) → ทองมักลง · ท่าทีผ่อนคลาย (Dovish) → ทองมักขึ้น",
    "other": "ยังไม่มีกฎสำหรับข่าวประเภทนี้ — ดูสถิติการขยับของทองประกอบ",
}


def classify(title: str) -> str:
    t = str(title or "").lower()
    for keys, kind in _RULES:
        if any(k in t for k in keys):
            return kind
    return "other"


def parse_num(text: str):
    """'55.1' → 55.1 · '200K' → 200000 · '4.6%' → 4.6 · '-0.3%' → -0.3 · ว่าง → None"""
    m = re.search(r"-?\d+(?:\.\d+)?", str(text or "").replace(",", ""))
    if not m:
        return None
    v = float(m.group())
    suffix = str(text).strip()[-1:].upper()
    return v * {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}.get(suffix, 1)


def pre_release_lean(ev: dict) -> int:
    """แนวโน้มก่อนข่าวออก (+1 ทองขึ้น / -1 ทองลง / 0 ไม่ชัด) จากคาดการณ์เทียบครั้งก่อน"""
    kind = classify(ev.get("title"))
    f, p = parse_num(ev.get("forecast")), parse_num(ev.get("previous"))
    if kind not in ("usd_up", "usd_down") or f is None or p is None or abs(f - p) < 1e-12:
        return 0
    usd_stronger = (f > p) if kind == "usd_up" else (f < p)
    return -1 if usd_stronger else 1


# ---------------------------------------------------------------- เวลา (ไม่พึ่ง tzdata)
def _nth_sunday(year, month, n):
    d = datetime(year, month, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_sunday(year, month):
    d = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year, 12, 31)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def ny_offset_hours(utc_dt: datetime) -> int:
    """เวลานิวยอร์ก: -4 ช่วง DST (อาทิตย์ที่ 2 มี.ค. – อาทิตย์แรก พ.ย.) ไม่งั้น -5"""
    y = utc_dt.year
    start = _nth_sunday(y, 3, 2) + timedelta(hours=7)   # 02:00 EST = 07:00 UTC
    end = _nth_sunday(y, 11, 1) + timedelta(hours=6)    # 02:00 EDT = 06:00 UTC
    naive = utc_dt.replace(tzinfo=None)
    return -4 if start <= naive < end else -5


def eu_server_offset_hours(utc_dt: datetime) -> int:
    """เวลาเซิร์ฟเวอร์โบรกเกอร์ส่วนใหญ่ (EET/EEST): +3 ช่วง DST ยุโรป ไม่งั้น +2"""
    y = utc_dt.year
    start = _last_sunday(y, 3) + timedelta(hours=1)
    end = _last_sunday(y, 10) + timedelta(hours=1)
    naive = utc_dt.replace(tzinfo=None)
    return 3 if start <= naive < end else 2


# ---------------------------------------------------------------- สถิติราคาทองจาก MT5
_stats = {"at": 0.0, "slots": {}, "server_mode": "eu", "fixed_offset": 0, "rates": None}
_lock = threading.Lock()


def _server_to_utc(ts: int) -> datetime:
    raw = datetime.fromtimestamp(ts, timezone.utc)
    if _stats["server_mode"] == "eu":
        return raw - timedelta(hours=eu_server_offset_hours(raw - timedelta(hours=3)))
    return raw - timedelta(seconds=_stats["fixed_offset"])


def _ensure_stats():
    """โหลดแท่ง M15 ~2 ปี แล้วคำนวณ % การขยับใน 60 นาที แยกตาม (วันในสัปดาห์, เวลานิวยอร์ก)"""
    with _lock:
        if _stats["slots"] and time.time() - _stats["at"] < STATS_TTL:
            return True
        try:
            if mt5.terminal_info() is None and not mt5.initialize():
                return False
            tick = mt5.symbol_info_tick(SYMBOL)
            rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, HISTORY_BARS)
            if rates is None or len(rates) < 1000:
                return False
            # ตรวจว่าเวลาเซิร์ฟเวอร์ตรงกฎ EET/EEST หรือไม่ ไม่ตรงใช้ส่วนต่างคงที่
            if tick and tick.time and abs(tick.time - time.time()) < 3 * 86400:
                measured = round((tick.time - time.time()) / 3600)
                now_utc = datetime.now(timezone.utc)
                if measured == eu_server_offset_hours(now_utc):
                    _stats["server_mode"] = "eu"
                else:
                    _stats["server_mode"], _stats["fixed_offset"] = "fixed", measured * 3600
            slots = {}
            n = len(rates)
            for i in range(n - 4):
                t_utc = _server_to_utc(int(rates[i]["time"]))
                ny = t_utc + timedelta(hours=ny_offset_hours(t_utc))
                o = float(rates[i]["open"])
                c = float(rates[i + 3]["close"])  # 4 แท่ง M15 = 60 นาที
                if int(rates[i + 3]["time"]) - int(rates[i]["time"]) != 45 * 60 or o <= 0:
                    continue  # ข้ามช่วงที่แท่งไม่ต่อเนื่อง (ตลาดปิด)
                slots.setdefault((ny.weekday(), ny.hour, ny.minute), []).append((c - o) / o * 100)
            _stats.update(slots=slots, at=time.time(), rates=rates)
            return True
        except Exception:
            return False


def _median(xs):
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2


def slot_move(ev_time: datetime):
    """สถิติ 60 นาทีหลังเวลาข่าว (ช่วงเวลาเดียวกันตามเวลานิวยอร์ก) → dict หรือ None"""
    if not _ensure_stats():
        return None
    t_utc = ev_time.astimezone(timezone.utc)
    ny = t_utc + timedelta(hours=ny_offset_hours(t_utc))
    minute = ny.minute - ny.minute % 15
    xs = _stats["slots"].get((ny.weekday(), ny.hour, minute))
    if not xs or len(xs) < 20:
        return None
    absx = [abs(x) for x in xs]
    big = sorted(absx)[int(len(absx) * 0.8)]
    return {"median_abs": _median(absx), "p80_abs": big, "n": len(xs), "up_pct": sum(1 for x in xs if x > 0) / len(xs) * 100,
            "source": "slot"}


def actual_move(ev_time: datetime):
    """ข่าวที่ประกาศไปแล้วอย่างน้อย 60 นาที: ทองขยับกี่ % ใน 60 นาทีหลังข่าว (จาก MT5) → float หรือ None"""
    if datetime.now(timezone.utc) < ev_time.astimezone(timezone.utc) + timedelta(minutes=WINDOW_MIN):
        return None
    if not _ensure_stats():
        return None
    rates = _stats["rates"]
    target = ev_time.astimezone(timezone.utc)
    # หาแท่งที่เริ่มตรงเวลาข่าว (ปัดลงทีละ 15 นาที) — ข้อมูลใหม่กว่า cache ให้โหลดเพิ่ม
    try:
        recent = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 800)
    except Exception:
        recent = None
    for src in (recent, rates):
        if src is None:
            continue
        for i in range(len(src) - 4):
            t = _server_to_utc(int(src[i]["time"]))
            if t <= target < t + timedelta(minutes=15):
                o, c = float(src[i]["open"]), float(src[i + 3]["close"])
                return (c - o) / o * 100 if o else None
    return None


def _load_history() -> dict:
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _record(ev: dict, move: float):
    try:
        hist = _load_history()
        key = ev["time"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        if hist.get(ev["title"], {}).get(key) == round(move, 4):
            return
        hist.setdefault(ev["title"], {})[key] = round(move, 4)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(hist, f, ensure_ascii=False)
    except Exception:
        pass


def title_stats(title: str):
    """สถิติจากข่าวชื่อเดียวกันที่บันทึกไว้ (ต้องมี ≥ 3 ครั้ง)"""
    xs = list(_load_history().get(title, {}).values())
    if len(xs) < 3:
        return None
    absx = [abs(x) for x in xs]
    return {"median_abs": _median(absx), "p80_abs": sorted(absx)[int(len(absx) * 0.8)], "n": len(xs),
            "up_pct": sum(1 for x in xs if x > 0) / len(xs) * 100, "source": "title"}


def analyze(ev: dict) -> dict:
    """สรุปผลกระทบของข่าว 1 รายการ สำหรับแสดงผล"""
    kind = classify(ev.get("title"))
    lean = pre_release_lean(ev)
    usd = ev.get("currency") == "USD"
    stats = (title_stats(ev["title"]) or slot_move(ev["time"])) if usd else None
    actual = actual_move(ev["time"]) if usd else None
    if actual is not None:
        _record(ev, actual)
    return {"kind": kind, "rule": TH_TYPES[kind], "lean": lean, "stats": stats, "actual": actual}


_published = {"items": []}


def _th(title):
    try:
        import news_th
        return news_th.translate(title)
    except Exception:
        return ""


def publish(events: list, analyses: dict):
    """เก็บผลวิเคราะห์ข่าวแบบ JSON ให้ Telemetry ส่งขึ้นเว็บ (เรียกจากโปรแกรมหลังคำนวณเสร็จ)"""
    items = []
    for ev in events:
        a = analyses.get((ev["title"], ev["time"]))
        if not a:
            continue
        st = a.get("stats") or {}
        items.append({
            "title": ev["title"], "title_th": _th(ev["title"]), "time": ev["time"].isoformat(), "impact": ev["impact"],
            "forecast": ev.get("forecast", ""), "previous": ev.get("previous", ""),
            "kind": a["kind"], "rule": a["rule"], "lean": a["lean"],
            "actual": round(a["actual"], 3) if a.get("actual") is not None else None,
            "move": round(st["median_abs"], 3) if st else None, "move_big": round(st["p80_abs"], 3) if st else None,
            "move_n": st.get("n") if st else None, "move_src": st.get("source") if st else None,
        })
    _published["items"] = items


def published() -> list:
    return _published["items"]


def short_text(a: dict) -> tuple[str, str]:
    """ข้อความสั้นสำหรับแถวปฏิทิน + ระดับสี ('up' / 'down' / 'muted')"""
    if a["actual"] is not None:
        v = a["actual"]
        return (f"ผลจริง {'▲' if v > 0 else '▼'} {v:+.2f}%", "up" if v > 0 else "down")
    size = f"±{a['stats']['median_abs']:.2f}%" if a["stats"] else ""
    if a["lean"] > 0:
        return (f"▲ ทองขึ้น {size}".strip(), "up")
    if a["lean"] < 0:
        return (f"▼ ทองลง {size}".strip(), "down")
    return ((f"ขยับ {size}" if size else "—"), "muted")
