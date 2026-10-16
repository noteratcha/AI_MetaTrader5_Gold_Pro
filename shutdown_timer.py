"""ตั้งเวลาปิดเครื่อง (ผู้ใช้สั่ง 16 ต.ค. 2026) — กำหนดวัน + เวลา (เวลาไทย) และเลือกให้ทำซ้ำทุกสัปดาห์ได้

ถึงเวลา: โปรแกรมเตือนนับถอยหลัง 60 วิ (ยกเลิกครั้งนี้ได้) → หยุดบอท → สั่ง Windows ปิดเครื่อง
ไม้ที่เปิดอยู่ถือไว้ตามเดิม (SL/TP อยู่ที่โบรกเกอร์) — แต่ไม่มีการเลื่อน SL / ปิดตามสัญญาณจนกว่าจะเปิดบอทใหม่
เครื่องหลับ/ปิดโปรแกรมอยู่จนเลยเวลาเกิน LATE_MAX = ข้ามรอบนั้น (ไม่ปิดเครื่องทันทีตอนเปิดใช้งานทีหลัง)
ค่าเก็บใน bot_settings.json คีย์ "shutdown_timer" ของ Profile นั้น
"""
import json
import subprocess
from datetime import datetime, timedelta, timezone

from app_paths import data_path

TH = timezone(timedelta(hours=7))
KEY = "shutdown_timer"
LATE_MAX = timedelta(minutes=10)
WARN_SEC = 60
DAYS_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


def now():
    return datetime.now(TH)


def load():
    try:
        with open(data_path("bot_settings.json"), "r", encoding="utf-8") as f:
            v = json.load(f).get(KEY) or {}
    except Exception:
        v = {}
    return {"enabled": bool(v.get("enabled")), "date": v.get("date") or "", "time": v.get("time") or "",
            "weekly": bool(v.get("weekly")), "last_fired": v.get("last_fired") or "", "auto_market": bool(v.get("auto_market"))}


def save(cfg):
    path = data_path("bot_settings.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data[KEY] = cfg
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def parse(date_s, time_s):
    """'dd/mm/yyyy' หรือ 'yyyy-mm-dd' + 'HH:MM' → datetime เวลาไทย (ผิดรูปแบบ = ValueError)"""
    date_s, time_s = (date_s or "").strip(), (time_s or "").strip()
    fmt = "%d/%m/%Y" if "/" in date_s else "%Y-%m-%d"
    d = datetime.strptime(date_s, fmt)
    t = datetime.strptime(time_s, "%H:%M")
    return datetime(d.year, d.month, d.day, t.hour, t.minute, tzinfo=TH)


def target(cfg, ref=None):
    """เวลาปิดเครื่องครั้งถัดไป (ยังไม่ถึง หรือเลยมาไม่เกิน LATE_MAX) — None ถ้าปิดใช้งาน/ไม่มีรอบถัดไป"""
    if not cfg.get("enabled"):
        return None
    if cfg.get("auto_market"):   # หลังตลาดปิดสุดสัปดาห์ทุกสัปดาห์ — คิดใหม่ทุกรอบ จึงเลื่อนตามฤดูเอง
        ref = ref or now()
        fired = cfg.get("last_fired") or ""
        for k in range(3):
            t = weekly_close_info(ref - LATE_MAX + timedelta(days=7 * k))["suggest"]
            if t + LATE_MAX >= ref and t.isoformat() != fired:
                return t
        return None
    try:
        t = parse(cfg["date"], cfg["time"])
    except Exception:
        return None
    ref = ref or now()
    fired = cfg.get("last_fired") or ""
    if cfg.get("weekly"):
        while t + LATE_MAX < ref or t.isoformat() == fired:
            t += timedelta(days=7)
        return t
    if t + LATE_MAX < ref or t.isoformat() == fired:
        return None
    return t


def due(cfg, ref=None):
    """ถึงเวลาแล้วหรือยัง → เวลาเป้าหมาย หรือ None"""
    ref = ref or now()
    t = target(cfg, ref)
    return t if t is not None and t <= ref else None


def mark_fired(cfg, t):
    """บันทึกว่ารอบ t ทำแล้ว · ครั้งเดียว = ปิดใช้งาน"""
    cfg = dict(cfg)
    cfg["last_fired"] = t.isoformat()
    if not cfg.get("weekly"):
        cfg["enabled"] = False
    save(cfg)
    return cfg


def describe(cfg):
    t = target(cfg)
    if t is None:
        return "ไม่ได้ตั้งเวลา"
    rep = (" · ทุกสัปดาห์หลังตลาดปิด (ปรับตามฤดูอัตโนมัติ)" if cfg.get("auto_market")
           else f" · ทุกวัน{DAYS_TH[t.weekday()]}" if cfg.get("weekly") else "")
    return f"วัน{DAYS_TH[t.weekday()]} {t:%d/%m/%Y} เวลา {t:%H:%M} น.{rep}"


def shutdown_windows(delay_sec=15):
    """สั่ง Windows ปิดเครื่อง (ยกเลิกได้ด้วย shutdown /a ภายใน delay_sec)"""
    subprocess.Popen(["shutdown", "/s", "/t", str(int(delay_sec)), "/c", "Gold Bot 24: ปิดเครื่องตามเวลาที่ตั้งไว้"],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


# ---------------------------------------------------------------- เวลาตลาดทอง (FBS) → เวลาไทย · ปรับตามฤดู (EET/EEST) อัตโนมัติ
MKT_CLOSE_SRV = (23, 55)   # ปิดทุกวัน/ศุกร์ เวลาเซิร์ฟเวอร์ (วัดจากแท่ง M1 จริง)
MKT_OPEN_SRV = (1, 5)      # เปิดอีกครั้ง เวลาเซิร์ฟเวอร์


def _srv_to_th(d, hm):
    """วันที่ d (date) + เวลาเซิร์ฟเวอร์ hm → datetime เวลาไทย (ส่วนต่างเซิร์ฟเวอร์ +3 ช่วง DST ยุโรป / +2 นอกช่วง)"""
    import thai_time
    naive = datetime(d.year, d.month, d.day, hm[0], hm[1])
    utc_guess = naive.replace(tzinfo=timezone.utc).timestamp() - 3 * 3600
    off = thai_time.eu_offset(utc_guess)
    return datetime.fromtimestamp(naive.replace(tzinfo=timezone.utc).timestamp() - off, TH)


def weekly_close_info(ref=None):
    """ตลาดปิดสุดสัปดาห์ครั้งถัดไป (เวลาไทย) + เวลาแนะนำให้ปิดเครื่อง (ปัดขึ้นเป็นชั่วโมงถัดไปหลังตลาดปิด)
    → {"close": dt, "open": dt (จันทร์), "suggest": dt, "daily": (เริ่มพัก, เปิด) ของวันนี้}"""
    ref = ref or now()
    d = (ref - timedelta(days=1)).date()   # วันศุกร์ของเซิร์ฟเวอร์ = เสาร์เช้าเวลาไทย
    for _ in range(10):
        if d.weekday() == 4:   # ศุกร์ (วันที่ของเซิร์ฟเวอร์)
            close = _srv_to_th(d, MKT_CLOSE_SRV)
            if close > ref - timedelta(hours=1):
                break
        d += timedelta(days=1)
    opn = _srv_to_th(d + timedelta(days=3), MKT_OPEN_SRV)
    sug = (close + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    daily = (_srv_to_th(ref.date(), MKT_CLOSE_SRV), _srv_to_th(ref.date() + timedelta(days=1), MKT_OPEN_SRV))
    return {"close": close, "open": opn, "suggest": sug, "daily": daily}
