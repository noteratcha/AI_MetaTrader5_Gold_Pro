"""
แผนเทรดที่แอดมินเปิด/ปิด (ตั้งค่าที่เว็บ /admin/plans)
- ดึงจาก GoldBot24 API (/api/config) ทุก 5 นาทีในเธรดเบื้องหลัง
- จำค่าล่าสุดไว้ใน %APPDATA%\\GoldBot24\\plan_config.json — ถ้าเน็ตหลุดใช้ค่าล่าสุดที่รู้
- ยังไม่เคยโหลดได้เลย = เปิดทุกแผน (ไม่ให้บอทหยุดทำงานเพราะเน็ต)
"""
import json
import threading
import time
import urllib.request

from app_paths import data_path
from license_manager import API_BASE_URL

REFRESH_SECONDS = 300
CACHE_FILE = data_path("plan_config.json")
BASE_PLANS = ("SMC-LiquidityHunt", "SR-SwingBounce", "BB-H1-Reversion", "MA-Cross-Trend", "MA-Cross-H1-Trend")

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


def is_enabled(plan_name: str) -> bool:
    base = base_plan(plan_name)
    if base not in BASE_PLANS:
        return True  # แผนที่ไม่ได้อยู่ในรายการควบคุม (เช่น Breakout ที่ปิดถาวรอยู่แล้ว)
    with _lock:
        return _state["plans"].get(base, True)


def disabled_plans() -> list:
    with _lock:
        return [k for k in BASE_PLANS if _state["plans"].get(k) is False]


_load_cache()
