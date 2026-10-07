"""
แผนเทรดที่แอดมินเปิด/ปิด (ตั้งค่าที่เว็บ /admin/plans)
- ดึงจาก GoldBot24 API (/api/config) ทุก 5 นาทีในเธรดเบื้องหลัง
- จำค่าล่าสุดไว้ใน %APPDATA%\\GoldBot24\\plan_config.json — ถ้าเน็ตหลุดใช้ค่าล่าสุดที่รู้
- ยังไม่เคยโหลดได้เลย = เปิดทุกแผน (ไม่ให้บอทหยุดทำงานเพราะเน็ต)
"""
import json
import math
import threading
import time
import urllib.request

from app_paths import data_path
from license_manager import API_BASE_URL

REFRESH_SECONDS = 300
CACHE_FILE = data_path("plan_config.json")
BASE_PLANS = ("SMC-LiquidityHunt", "SR-SwingBounce", "BB-H1-Reversion", "MA-Cross-Trend", "MA-Cross-H1-Trend", "PSAR-H1-Trend")

_state = {"plans": {}, "fetched_at": 0.0}
_lock = threading.Lock()


def _load_cache():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            _state["plans"] = {k: bool(v) for k, v in data.items() if k in BASE_PLANS}
    except Exception:
        pass


def refresh() -> bool:
    """ดึงค่าล่าสุดจากเว็บ (คืน True ถ้าสำเร็จ)"""
    try:
        req = urllib.request.Request(f"{API_BASE_URL.rstrip('/')}/api/config", headers={"User-Agent": "GoldBot24-Desktop"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            plans = (json.loads(resp.read().decode("utf-8")) or {}).get("enabledPlans") or {}
        plans = {k: bool(plans.get(k, True)) for k in BASE_PLANS}
        with _lock:
            _state["plans"] = plans
            _state["fetched_at"] = time.time()
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(plans, f)
        except OSError:
            pass
        return True
    except Exception:
        return False


def _worker():
    while True:
        refresh()
        time.sleep(REFRESH_SECONDS)


def start():
    """เริ่มเธรดอัปเดตค่า (เรียกซ้ำได้ — เริ่มครั้งเดียว)"""
    if getattr(start, "_started", False):
        return
    start._started = True
    _load_cache()
    threading.Thread(target=_worker, daemon=True).start()


def base_plan(plan_name: str) -> str:
    """ชื่อแผนหลัก เช่น 'SMC-LiquidityHunt+Div' → 'SMC-LiquidityHunt'"""
    return str(plan_name or "").split("+")[0].strip()


def admin_enabled(plan_name: str) -> bool:
    base = base_plan(plan_name)
    if base not in BASE_PLANS:
        return True  # แผนที่ไม่ได้อยู่ในรายการควบคุม
    with _lock:
        return _state["plans"].get(base, True)


# ---- ผู้ใช้เลือกเปิด/ปิดแผนเอง (จำแยกตามอีเมลใน %APPDATA%\GoldBot24\bot_settings.json คีย์ user_plans) ----
SETTINGS_FILE = data_path("bot_settings.json")
_user_cache = {"mtime": None, "data": {}}


def _settings() -> dict:
    try:
        import os
        mtime = os.path.getmtime(SETTINGS_FILE)
        if mtime != _user_cache["mtime"]:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                _user_cache.update(mtime=mtime, data=json.load(f) or {})
    except Exception:
        _user_cache.update(mtime=None, data={})
    return _user_cache["data"]


def _current_email() -> str:
    try:
        from license_manager import license_mgr
        return str(license_mgr.get_current_user().get("email") or "").lower()
    except Exception:
        return ""


def user_enabled(plan_name: str, email: str = None) -> bool:
    base = base_plan(plan_name)
    if base not in BASE_PLANS:
        return True
    prefs = (_settings().get("user_plans") or {}).get((email or _current_email()) or "_local", {})
    return bool(prefs.get(base, True))  # ค่าเริ่มต้น: เปิดทุกแผน


def set_user_enabled(plan_name: str, enabled: bool, email: str = None):
    base = base_plan(plan_name)
    key = (email or _current_email()) or "_local"
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        data = {}
    data.setdefault("user_plans", {}).setdefault(key, {})[base] = bool(enabled)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


DEFAULT_MARGIN_PER_TRADE = 400.0   # มาร์จิ้นว่างทุก 400 เปิดได้ 1 ไม้ (ที่ Lot 0.01)


def get_margin_per_trade(email: str = None) -> float:
    """มาร์จิ้นที่ต้องมีต่อ 1 ไม้ (ที่ Lot 0.01) ของผู้ใช้คนนี้ — ค่าเริ่มต้น 400 · บันทึกใน bot_settings.json คีย์ margin_per_trade[email]"""
    try:
        v = float((_settings().get("margin_per_trade") or {}).get((email or _current_email()) or "_local", DEFAULT_MARGIN_PER_TRADE))
        return v if v >= 10 else DEFAULT_MARGIN_PER_TRADE
    except Exception:
        return DEFAULT_MARGIN_PER_TRADE


def set_margin_per_trade(value: float, email: str = None):
    key = (email or _current_email()) or "_local"
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        data = {}
    data.setdefault("margin_per_trade", {})[key] = round(float(value), 2)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


MIN_BALANCE_USD = 25.0   # ยอดเงินขั้นต่ำ (Equity) ที่ระบบยอมเริ่มบอท/เปิดไม้ใหม่ (ผู้ใช้กำหนด 8 ต.ค. 2026)


def account_usd(acc) -> float:
    """Equity ของบัญชี MT5 เป็น USD (บัญชีเซ็นต์ USC/USc หาร 100) — 0 ถ้าอ่านไม่ได้"""
    if acc is None:
        return 0.0
    eq = float(getattr(acc, "equity", 0.0) or 0.0)
    cur = str(getattr(acc, "currency", "") or "").upper()
    return eq / 100.0 if cur in ("USC", "USCENT", "CENT") else eq


def max_positions(free_margin: float, lot: float, email: str = None, margin: float = None) -> int:
    """จำนวนไม้สูงสุดที่เปิดได้ = มาร์จิ้นว่าง ÷ (มาร์จิ้นต่อไม้ × Lot/0.01) ปัดเศษขึ้น — อย่างน้อย 1 ไม้"""
    per = (margin or get_margin_per_trade(email)) * max(float(lot or 0.01), 0.01) / 0.01
    # ทุก `per` ปัดเศษขึ้น: ไม่เกิน 400 = 1 ไม้, 401–800 = 2 ไม้, 960 = 3 ไม้
    return max(1, math.ceil(float(free_margin or 0) / per - 1e-9)) if per > 0 else 1


def disabled_reason(plan_name: str):
    """None = ใช้งานได้ · 'admin' = แอดมินปิด · 'user' = ผู้ใช้ปิดเอง"""
    if not admin_enabled(plan_name):
        return "admin"
    if not user_enabled(plan_name):
        return "user"
    return None


def is_enabled(plan_name: str) -> bool:
    """แผนนี้เข้าไม้ได้ไหม (แอดมินเปิด และ ผู้ใช้เลือกใช้)"""
    return disabled_reason(plan_name) is None


def disabled_plans() -> list:
    with _lock:
        return [k for k in BASE_PLANS if _state["plans"].get(k) is False]


_load_cache()
