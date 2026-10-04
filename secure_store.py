"""
จดจำอีเมล/รหัสผ่านล่าสุดของหน้าเข้าสู่ระบบ (เมื่อผู้ใช้ติ๊ก "จดจำการเข้าสู่ระบบ")
รหัสผ่านเข้ารหัสด้วย Windows DPAPI (CryptProtectData) — ถอดรหัสได้เฉพาะบัญชี Windows เดิมบนเครื่องเดิม
ถ้า DPAPI ใช้ไม่ได้ (ไม่ใช่ Windows) จะจำเฉพาะอีเมล ไม่เก็บรหัสผ่าน
"""
import base64
import ctypes
import json
import os
import sys

from app_paths import data_path

REMEMBER_FILE = data_path("remember_login.json")
_ENTROPY = b"GoldBot24-remember-login-v1"


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _to_blob(data: bytes) -> _Blob:
    buf = ctypes.create_string_buffer(data, len(data))
    blob = _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob._buf = buf  # กัน GC
    return blob


def _dpapi(data: bytes, protect: bool) -> bytes:
    if sys.platform != "win32":
        raise OSError("DPAPI requires Windows")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    src, entropy, out = _to_blob(data), _to_blob(_ENTROPY), _Blob()
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    # dwFlags 0x1 = CRYPTPROTECT_UI_FORBIDDEN
    ok = fn(ctypes.byref(src), None, ctypes.byref(entropy), None, None, 0x1, ctypes.byref(out))
    if not ok:
        raise OSError("DPAPI call failed")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        kernel32.LocalFree(out.pbData)


def save_login(email: str, password: str) -> None:
    record = {"email": email}
    try:
        record["password_dpapi"] = base64.b64encode(_dpapi(password.encode("utf-8"), True)).decode("ascii")
    except Exception:
        pass  # เก็บเฉพาะอีเมล
    try:
        with open(REMEMBER_FILE, "w", encoding="utf-8") as f:
            json.dump(record, f)
    except OSError:
        pass


def load_login() -> tuple[str, str]:
    """คืน (อีเมล, รหัสผ่าน) ที่จำไว้ — ค่าว่างถ้าไม่มี/ถอดรหัสไม่ได้"""
    try:
        with open(REMEMBER_FILE, encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, ValueError):
        return "", ""
    password = ""
    if record.get("password_dpapi"):
        try:
            password = _dpapi(base64.b64decode(record["password_dpapi"]), False).decode("utf-8")
        except Exception:
            password = ""
    return str(record.get("email") or ""), password


def clear_login() -> None:
    try:
        os.remove(REMEMBER_FILE)
    except OSError:
        pass
