"""
ตำแหน่งเก็บข้อมูลผู้ใช้ของ Desktop App
- เก็บใน %APPDATA%\\GoldBot24 เพื่อให้อยู่รอดเมื่ออัปเดตโปรแกรม (โฟลเดอร์โปรแกรม/dist ถูกลบสร้างใหม่ทุกครั้งที่ build)
- ย้ายไฟล์เดิมจากโฟลเดอร์โปรแกรมมาให้อัตโนมัติครั้งแรก
"""
import json
import os
import shutil
import sys

APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "GoldBot24")

try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError:
    DATA_DIR = APP_DIR

# ตรวจจับชื่อ Profile เริ่มต้นจาก Environment หรือ CLI Arguments (--profile <name> หรือ -p <name>)
_ACTIVE_PROFILE = "default"


def _detect_initial_profile() -> str:
    env_prof = (os.environ.get("GOLDBOT_PROFILE") or "").strip()
    if env_prof:
        return env_prof
    for i, arg in enumerate(sys.argv):
        if arg in ("--profile", "-p") and i + 1 < len(sys.argv):
            candidate = sys.argv[i + 1].strip()
            if candidate and not candidate.startswith("-"):
                return candidate
        if arg.startswith("--profile="):
            candidate = arg.split("=", 1)[1].strip()
            if candidate:
                return candidate
    return "default"


_ACTIVE_PROFILE = _detect_initial_profile()


def get_active_profile() -> str:
    """คืนชื่อ Profile ที่กำลังทำงานอยู่ (default หรือชื่อที่กำหนด)"""
    global _ACTIVE_PROFILE
    return _ACTIVE_PROFILE or "default"


def set_active_profile(name: str) -> None:
    """สลับ Profile ที่กำลังทำงานอยู่ และสร้างโฟลเดอร์สำหรับ Profile นั้นทันที"""
    global _ACTIVE_PROFILE
    name_clean = (name or "").strip()
    if not name_clean:
        name_clean = "default"
    _ACTIVE_PROFILE = name_clean
    p_dir = get_active_profile_dir()
    try:
        os.makedirs(p_dir, exist_ok=True)
    except OSError:
        pass


def get_active_profile_dir() -> str:
    """คืนโฟลเดอร์เก็บข้อมูลของ Profile ปัจจุบัน (ถ้าเป็น default จะอยู่ที่ DATA_DIR หลัก)"""
    prof = get_active_profile()
    if prof == "default":
        return DATA_DIR
    p_dir = os.path.join(DATA_DIR, "profiles", prof)
    try:
        os.makedirs(p_dir, exist_ok=True)
    except OSError:
        pass
    return p_dir


def list_profiles() -> list[str]:
    """คืนรายชื่อ Profile ทั้งหมดที่มีในระบบ"""
    profiles = ["default"]
    p_base = os.path.join(DATA_DIR, "profiles")
    if os.path.exists(p_base):
        try:
            for entry in os.listdir(p_base):
                if os.path.isdir(os.path.join(p_base, entry)):
                    profiles.append(entry)
        except OSError:
            pass
    return sorted(list(set(profiles)))


def data_path(name: str) -> str:
    """คืน path ไฟล์ข้อมูลใน Profile ปัจจุบัน (ย้าย/ซิงค์ไฟล์ตั้งต้นมาให้ถ้ายังไม่มี)"""
    prof_dir = get_active_profile_dir()
    target = os.path.join(prof_dir, name)
    need_copy = not os.path.exists(target) or os.path.getsize(target) <= 100
    if need_copy:
        # หากเป็น Profile ใหม่ ให้คัดลอก bot_settings.json จาก default เป็นเทมเพลตเริ่มต้น
        if prof_dir != DATA_DIR:
            default_target = os.path.join(DATA_DIR, name)
            if name in ("bot_settings.json",) and os.path.exists(default_target) and os.path.getsize(default_target) > 100:
                try:
                    # คัดลอกค่าตั้งต้น (Lot, แผน, เป้ากำไร ฯลฯ) แต่ไม่เอาค่าประจำ Profile — magic_number / terminal_path
                    # (เดิมคัดลอกทั้งไฟล์ ทำให้ Profile ใหม่ได้ Magic 888999 ซ้ำกับ default · แก้ 13 ต.ค. 2026)
                    with open(default_target, encoding="utf-8") as f:
                        tpl = json.load(f)
                    if isinstance(tpl, dict):
                        for k in ("magic_number", "terminal_path"):
                            tpl.pop(k, None)
                        with open(target, "w", encoding="utf-8") as f:
                            json.dump(tpl, f, ensure_ascii=False, indent=2)
                    else:
                        shutil.copy2(default_target, target)
                    return target
                except (OSError, ValueError):
                    pass

        # ตรวจสอบไฟล์เก่าจาก APP_DIR สำหรับ default profile
        for legacy_dir in (APP_DIR, os.path.join(APP_DIR, "_internal")):
            legacy = os.path.join(legacy_dir, name)
            if legacy != target and os.path.exists(legacy) and os.path.getsize(legacy) > 100:
                try:
                    shutil.copy2(legacy, target)
                except OSError:
                    pass
                break
    return target

