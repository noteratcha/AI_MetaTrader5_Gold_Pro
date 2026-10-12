"""
ป้องกันการเปิดซ้ำ (12 ต.ค. 2026)
1) Profile เดียวกันเปิดได้หน้าต่างเดียว — Mutex ชื่อตาม Profile (ใช้ร่วมกับ gui_app.check_single_instance)
2) บัญชี MT5 เดียวกันให้บอททำงานได้หน้าต่างเดียว — Mutex ตามเลขบัญชี + ไฟล์บอกว่า Profile ไหนถืออยู่
   (หลาย Profile ชี้ MT5 ตัวเดียวกัน/บัญชีเดียวกัน = บอทซ้ำ เข้าไม้ซ้ำ ดูแลไม้ทับกัน)
Mutex ถูกปล่อยเองเมื่อโปรเซสปิด (รวมกรณีโปรแกรมค้าง/ถูก kill) จึงไม่มีล็อกค้าง
"""
import json
import os
import sys

from app_paths import get_active_profile

_SYNCHRONIZE = 0x00100000
_ERROR_ALREADY_EXISTS = 183

_account_handle = None
_account_login = None


def _clean(name: str) -> str:
    return "".join(c for c in (name or "") if c.isalnum() or c in ("_", "-")) or "default"


def profile_mutex_name(profile: str = None) -> str:
    # ชื่อเดิม (ก่อนเปลี่ยนชื่อโปรแกรม) — ห้ามเปลี่ยน ไม่งั้นเวอร์ชันเก่า/ใหม่กันซ้ำกันไม่ได้
    return f"Local\\GoldBot24_AI_Gold_Commander_Pro_{_clean(profile or get_active_profile())}"


def _account_mutex_name(login: int) -> str:
    return f"Local\\GoldBot24_Account_{int(login)}"


def _mutex_exists(name: str) -> bool:
    if sys.platform != "win32":
        return False
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenMutexW(_SYNCHRONIZE, False, name)
    if h:
        k.CloseHandle(h)
        return True
    return False


def is_profile_running(profile: str) -> bool:
    """Profile นี้มีหน้าต่างเปิดอยู่แล้วหรือไม่"""
    try:
        return _mutex_exists(profile_mutex_name(profile))
    except Exception:
        return False


def _owner_file(login: int) -> str:
    base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "GoldBot24", "account_locks")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{int(login)}.json")


def account_owner(login: int) -> str:
    """ชื่อ Profile ที่ถือบัญชีนี้อยู่ (อ่านจากไฟล์ — ใช้แสดงผลเท่านั้น)"""
    try:
        with open(_owner_file(login), encoding="utf-8") as f:
            return json.load(f).get("profile") or "?"
    except Exception:
        return "?"


def acquire_account(login: int) -> tuple:
    """
    จองบัญชี MT5 ให้หน้าต่างนี้ — คืน (True, "") ถ้าได้ หรือ (False, ข้อความ) ถ้าหน้าต่าง/Profile อื่นใช้อยู่
    เปลี่ยนบัญชี → ปล่อยบัญชีเดิมแล้วจองบัญชีใหม่
    """
    global _account_handle, _account_login
    login = int(login or 0)
    if not login or sys.platform != "win32":
        return True, ""
    if _account_login == login and _account_handle:
        return True, ""
    import ctypes
    k = ctypes.windll.kernel32
    h = k.CreateMutexW(None, False, _account_mutex_name(login))
    err = k.GetLastError()
    if not h:
        return True, ""          # สร้างไม่ได้ (ไม่ควรเกิด) — ไม่บล็อกการใช้งาน
    if err == _ERROR_ALREADY_EXISTS:
        k.CloseHandle(h)
        owner = account_owner(login)
        return False, (f"บัญชี MT5 #{login} มีบอทเปิดใช้งานอยู่แล้วใน Profile [{owner}]\n"
                       "ปิดบอทในหน้าต่างนั้นก่อน หรือให้ Profile นี้เชื่อม MT5 บัญชีอื่น (ป้องกันเข้าไม้ซ้ำ)")
    release_account()
    _account_handle, _account_login = h, login
    try:
        with open(_owner_file(login), "w", encoding="utf-8") as f:
            json.dump({"profile": get_active_profile(), "pid": os.getpid()}, f)
    except Exception:
        pass
    return True, ""


def release_account():
    global _account_handle, _account_login
    if _account_handle and sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(_account_handle)
        except Exception:
            pass
    _account_handle, _account_login = None, None


def held_login():
    return _account_login
