"""Plan 11 · News-USD — เข้าไม้ทันทีเมื่อค่าจริงข่าว USD ออก (ผู้ใช้ออกแบบ 15 ต.ค. 2026 · "แผน ข ยืนยันแบบหลวม")

กฎ (ใช้ร่วมกันทั้งบอทและ tools/backtest_all.py — ผลตรงกัน):
1. ก่อนข่าว: แต่ละข่าวเทียบ คาด กับ ครั้งก่อน → ทิศทอง (ตัวเลขสูงขึ้น = ดอลลาร์แข็ง = ทองลง ·
   อัตราว่างงาน / Initial Jobless Claims กลับทิศ) · คาด = ครั้งก่อน → ข่าวนั้นไม่นับ
2. ค่าจริงออก: "ยืนยัน" เมื่อค่าจริงไม่สวนแนวโน้ม (ตามคาด หรือเลยคาดไปทางเดียวกัน)
3. ข่าวที่ออกเวลาเดียวกัน: รวม ±1 ของข่าวที่ยืนยัน → ทิศ = เครื่องหมาย · Lot = ปกติ × |ผลรวม| (สูงสุด 3) · 0 = ไม่เข้า
4. ออก: SL 3 ATR M15 (แท่งปิดก่อนข่าว) · ไม่ตั้ง TP · ปิดเมื่อถือครบ 8 ชม.

ข้อมูลข่าวสด: EA GoldBot24_NewsBridge ใน MT5 อ่านปฏิทิน MetaQuotes ทุก 0.5 วิ → Common\\Files\\goldbot24_news_live.json
(Python เข้าถึงปฏิทินของ MT5 โดยตรงไม่ได้) · เวลาในปฏิทิน = UTC
Backtest Tick FBS เม.ย. 2024 – ต.ค. 2026: เข้า 2 วิ 167 ไม้ +863 PF 1.51 · เข้า 10 วิ +541 PF 1.31 · กำไรส่วนใหญ่ปี 2026
"""
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone

NAME = "News-USD"
SL_ATR = 3.0
HOLD_HOURS = 8
MAX_MULT = 3
MAX_DELAY_SEC = 120        # เข้าไม้ได้ไม่เกิน 2 นาทีหลังข่าวออก (ช้ากว่านั้นตลาดซึมซับข่าวไปแล้ว)
SETTLE_SEC = 15            # รอค่าจริงของข่าวที่ออกเวลาเดียวกันครบ (สูงสุด 15 วิ หลังค่าแรกมาถึง)
BRIDGE_STALE_SEC = 30      # EA ไม่เขียนไฟล์เกิน 30 วิ = ไม่ได้เชื่อมต่อ
EA_NAME = "GoldBot24_NewsBridge"

# code ในปฏิทิน MetaQuotes → ทิศทอง เมื่อตัวเลขสูงขึ้น (-1 = ทองลง · +1 = ทองขึ้น)
CODES = {
    "consumer-price-index-ex-food-energy-mm": -1, "consumer-price-index-mm": -1, "consumer-price-index-yy": -1,
    "nonfarm-payrolls": -1, "unemployment-rate": +1, "average-hourly-earnings-mm": -1,
    "retail-sales-mm": -1, "retail-sales-ex-autos-mm": -1, "producer-price-index-mm": -1,
    "core-pce-price-index-mm": -1, "gross-domestic-product-qq": -1,
    "ism-manufacturing-pmi": -1, "ism-non-manufacturing-pmi": -1, "jolts-job-openings": -1,
    "adp-nonfarm-employment-change": -1, "philadelphia-fed-manufacturing-index": -1,
    "durable-goods-orders": -1, "consumer-confidence-index": -1, "initial-jobless-claims": +1,
    "markit-manufacturing-pmi": -1, "markit-services-pmi": -1,
}
TH = {
    "consumer-price-index-ex-food-energy-mm": "Core CPI m/m", "consumer-price-index-mm": "CPI m/m", "consumer-price-index-yy": "CPI y/y",
    "nonfarm-payrolls": "Non-Farm", "unemployment-rate": "อัตราว่างงาน", "average-hourly-earnings-mm": "ค่าจ้าง m/m",
    "retail-sales-mm": "Retail Sales", "retail-sales-ex-autos-mm": "Core Retail", "producer-price-index-mm": "PPI m/m",
    "core-pce-price-index-mm": "Core PCE", "gross-domestic-product-qq": "GDP", "ism-manufacturing-pmi": "ISM ภาคผลิต",
    "ism-non-manufacturing-pmi": "ISM ภาคบริการ", "jolts-job-openings": "JOLTS", "adp-nonfarm-employment-change": "ADP",
    "philadelphia-fed-manufacturing-index": "Philly Fed", "durable-goods-orders": "Durable Goods",
    "consumer-confidence-index": "CB Confidence", "initial-jobless-claims": "Jobless Claims",
    "markit-manufacturing-pmi": "S&P PMI ผลิต", "markit-services-pmi": "S&P PMI บริการ",
}


def _sign(x):
    return (x > 0) - (x < 0)


def lean(code, forecast, prev):
    """แนวโน้มทองก่อนข่าว: +1 ขึ้น / -1 ลง / 0 ไม่นับ"""
    if code not in CODES or forecast is None or prev is None:
        return 0
    return _sign(round(forecast - prev, 9)) * CODES[code]


def confirmed(code, actual, forecast, prev):
    """ยืนยัน (แบบหลวม): ค่าจริงไม่สวนแนวโน้ม → คืนทิศทอง ไม่งั้น 0"""
    ln = lean(code, forecast, prev)
    if not ln or actual is None:
        return 0
    surprise = _sign(round(actual - forecast, 9)) * CODES[code]
    return ln if surprise != -ln else 0


def decide(rows):
    """rows: [(code, actual, forecast, prev)] ของข่าวที่ออกเวลาเดียวกัน → (ทิศ +1/-1/0, ตัวคูณ Lot 0–3, รายละเอียด)"""
    net, detail = 0, []
    for code, a, f, p in rows:
        ln = lean(code, f, p)
        if not ln:
            continue
        c = confirmed(code, a, f, p)
        net += c
        detail.append((code, ln, c, a, f, p))
    return _sign(net), min(abs(net), MAX_MULT), detail


# ---------------------------------------------------------------- ข้อมูลสดจาก EA
def live_path():
    return os.path.join(os.environ.get("APPDATA", ""), "MetaQuotes", "Terminal", "Common", "Files", "goldbot24_news_live.json")


_cache = {"mtime": 0.0, "data": None}


def read_live():
    """อ่านไฟล์จาก EA (แคชตามเวลาแก้ไขไฟล์) → dict หรือ None"""
    p = live_path()
    try:
        m = os.path.getmtime(p)
        if m != _cache["mtime"]:
            with open(p, "r", encoding="ascii", errors="ignore") as fh:
                _cache.update(mtime=m, data=json.load(fh))
        return _cache["data"]
    except Exception:
        return None


def bridge_age(data=None):
    """วินาทีนับจาก EA เขียนไฟล์ล่าสุด (ใช้เวลาแก้ไขไฟล์ · ไม่มีไฟล์ = None)"""
    try:
        return time.time() - os.path.getmtime(live_path())
    except Exception:
        return None


def bridge_ok():
    age = bridge_age()
    return age is not None and age <= BRIDGE_STALE_SEC


def _utc(s):
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _groups(data):
    g = {}
    for ev in (data or {}).get("events", []):
        if ev.get("code") in CODES:
            try:
                g.setdefault(_utc(ev["t"]), []).append(ev)
            except Exception:
                pass
    return g


def pending_signal(data, now_utc, done):
    """ข่าวที่เพิ่งออก (≤ MAX_DELAY_SEC) และมีค่าจริงครบ (หรือรอครบ SETTLE_SEC แล้ว) → dict สัญญาณ หรือ None
    done: set ของเวลาข่าวที่ตัดสินไปแล้ว (กันเข้าซ้ำ)"""
    for t, evs in sorted(_groups(data).items()):
        age = (now_utc - t).total_seconds()
        if t in done or age < 0 or age > MAX_DELAY_SEC:
            continue
        rel = [e for e in evs if lean(e["code"], e.get("f"), e.get("p"))]
        if not rel:
            done.add(t)
            continue
        have = [e for e in rel if e.get("a") is not None]
        if not have or (len(have) < len(rel) and age < SETTLE_SEC):
            continue      # รอค่าจริงให้ครบก่อน (สูงสุด SETTLE_SEC วินาที)
        d, mult, detail = decide([(e["code"], e.get("a"), e.get("f"), e.get("p")) for e in have])
        return {"time": t, "dir": d, "mult": mult, "detail": detail, "age": age}
    return None


def next_group(data, now_utc):
    """ข่าวกลุ่มถัดไปที่แผนใช้ได้ → (เวลา UTC, แนวโน้มสุทธิ, รายการ [(code, lean)]) หรือ None"""
    for t, evs in sorted(_groups(data).items()):
        if (now_utc - t).total_seconds() > MAX_DELAY_SEC:
            continue
        items = [(e["code"], lean(e["code"], e.get("f"), e.get("p"))) for e in evs]
        items = [x for x in items if x[1]]
        if items:
            return t, sum(x[1] for x in items), items
    return None


def describe(detail):
    """ข้อความสั้นของรายละเอียดการตัดสิน เช่น 'Core CPI m/m ✓ลง · CPI y/y ✗'"""
    out = []
    for code, ln, c, a, f, p in detail:
        out.append(f"{TH.get(code, code)} {'✓' if c else '✗'}{'ขึ้น' if ln > 0 else 'ลง'} (จริง {a:g} คาด {f:g} ก่อน {p:g})" if a is not None
                   else f"{TH.get(code, code)} รอค่าจริง")
    return " · ".join(out)


# ---------------------------------------------------------------- ติดตั้ง EA ลง MT5
def _asset_ex5():
    base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "assets", "mql5", f"{EA_NAME}.ex5")


def install_bridge(terminal_data_path):
    """คัดลอก EA ไปที่ <MT5>\\MQL5\\Experts\\GoldBot24 (ไม่เขียนทับถ้าเหมือนเดิม) → path หรือ None"""
    try:
        src = _asset_ex5()
        if not terminal_data_path or not os.path.isfile(src):
            return None
        dst_dir = os.path.join(terminal_data_path, "MQL5", "Experts", "GoldBot24")
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, f"{EA_NAME}.ex5")
        if not os.path.isfile(dst) or os.path.getsize(dst) != os.path.getsize(src):
            shutil.copy2(src, dst)
        return dst
    except Exception:
        return None
