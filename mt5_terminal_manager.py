"""
ระบบจัดการและสลับการเชื่อมต่อ MetaTrader 5 Terminal สำหรับระบบ Multi-Instance & Profile
- สแกนหา MT5 ที่ติดตั้งในเครื่องอัตโนมัติ (เช่น FBS, XM Global, MetaQuotes ฯลฯ)
- จัดการกำหนด Terminal Path และสลับ Terminal ประจำ Profile
- จัดการ Magic Number แยกตาม Profile เพื่อป้องกันออเดอร์ชนกัน
"""
import glob
import json
import os
import sys
import MetaTrader5 as mt5

from app_paths import data_path, get_active_profile


DEFAULT_MAGIC_NUMBER = 888999


def scan_installed_terminals() -> list[dict]:
    """
    สแกนหาไฟล์ terminal64.exe ของ MetaTrader 5 ทั้งหมดที่ติดตั้งอยู่ในเครื่อง
    คืนค่ารายการ dict: [{"name": str, "path": str, "broker": str, "exists": bool}]
    """
    candidates = []
    seen_paths = set()

    search_roots = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
        os.path.expandvars(r"%APPDATA%"),
    ]

    for base in search_roots:
        if not os.path.exists(base):
            continue
        try:
            # ค้นหา terminal64.exe ในระดับโฟลเดอร์ลูก
            pattern = os.path.join(base, "*", "terminal64.exe")
            for p in glob.glob(pattern):
                norm = os.path.normcase(os.path.abspath(p))
                if norm in seen_paths:
                    continue
                seen_paths.add(norm)
                parent_name = os.path.basename(os.path.dirname(p))
                broker = parent_name
                for suffix in [" MetaTrader 5", " MT5", " MetaTrader", " 5"]:
                    if broker.endswith(suffix):
                        broker = broker[:-len(suffix)].strip()
                candidates.append({
                    "name": parent_name,
                    "path": p,
                    "broker": broker or parent_name,
                    "exists": True
                })
        except Exception:
            pass

    return candidates


def get_configured_terminal_path() -> str | None:
    """
    ดึง Path ของ MT5 Terminal ที่ถูกตั้งค่าไว้สำหรับ Profile ปัจจุบัน
    ลำดับความสำคัญ:
    1. CLI Argument: --terminal-path <path> หรือ --path <path>
    2. ไฟล์ bot_settings.json (คีย์ 'terminal_path')
    """
    # 1. เช็คจาก sys.argv
    for i, arg in enumerate(sys.argv):
        if arg in ("--terminal-path", "--path") and i + 1 < len(sys.argv):
            candidate = sys.argv[i + 1].strip()
            if os.path.isfile(candidate):
                return candidate
        if arg.startswith("--terminal-path="):
            candidate = arg.split("=", 1)[1].strip()
            if os.path.isfile(candidate):
                return candidate
        if arg.startswith("--path="):
            candidate = arg.split("=", 1)[1].strip()
            if os.path.isfile(candidate):
                return candidate

    # 2. เช็คจาก bot_settings.json
    try:
        settings_path = data_path("bot_settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                configured = data.get("terminal_path")
                if configured and os.path.isfile(configured):
                    return configured
    except Exception:
        pass

    return None


def set_configured_terminal_path(path: str | None) -> None:
    """บันทึก Path ของ MT5 Terminal ลงใน bot_settings.json ประจำ Profile"""
    try:
        settings_path = data_path("bot_settings.json")
        data = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        if path:
            data["terminal_path"] = path
        else:
            data.pop("terminal_path", None)
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] set_configured_terminal_path error: {e}")


def get_profile_magic_number() -> int:
    """
    ดึง Magic Number ประจำ Profile ปัจจุบัน
    - หากกำหนดใน bot_settings.json ('magic_number') ให้ใช้ค่านั้น
    - หากเป็น profile 'default' ใช้ 888999
    - หากเป็น profile อื่น และยังไม่ได้ตั้งค่า ให้คำนวณ offset ตาม profile hash เพื่อไม่ให้ซ้ำกัน
    """
    try:
        settings_path = data_path("bot_settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                custom_magic = data.get("magic_number")
                if custom_magic and isinstance(custom_magic, int) and custom_magic > 0:
                    return custom_magic
    except Exception:
        pass

    prof = get_active_profile()
    if prof == "default" or not prof:
        return DEFAULT_MAGIC_NUMBER

    # คำนวณ offset สำหรับ profile อื่นๆ
    prof_hash = sum(ord(c) for c in prof) % 900
    return 888000 + prof_hash


def set_profile_magic_number(magic: int) -> None:
    """บันทึก Magic Number ประจำ Profile"""
    try:
        settings_path = data_path("bot_settings.json")
        data = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data["magic_number"] = int(magic)
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] set_profile_magic_number error: {e}")


def initialize_mt5(path: str = None, **kwargs) -> bool:
    """
    เชื่อมต่อ MT5 โดยคำนึงถึง Terminal Path ที่ผูกไว้กับ Profile
    - หากไม่ได้ระบุ path จะดึงจาก get_configured_terminal_path()
    - หากเชื่อมต่ออยู่แล้วกับ path ที่ตรงกัน จะไม่ตัดการเชื่อมต่อ
    - หาก path ปัจจุบันไม่ตรง จะ shutdown แล้ว initialize ใหม่ด้วย path ที่ถูกต้อง
    """
    target_path = path or get_configured_terminal_path()

    # ตรวจสอบว่า terminal ปัจจุบันเชื่อมต่ออยู่แล้วหรือไม่
    term = mt5.terminal_info()
    if term is not None:
        if not target_path:
            return True
        # เปรียบเทียบ folder ของ target_path กับ term.path
        cur_dir = os.path.normcase(os.path.normpath(term.path))
        target_dir = os.path.normcase(os.path.normpath(os.path.dirname(target_path)))
        if cur_dir == target_dir:
            return True
        # ถ้าคนละ terminal ให้ shutdown ก่อนเพื่อเชื่อมต่อไปยังตัวใหม่
        try:
            mt5.shutdown()
        except Exception:
            pass

    # เรียก mt5.initialize()
    if target_path and os.path.isfile(target_path):
        success = mt5.initialize(path=target_path, **kwargs)
        if success:
            return True
        print(f"[WARN] Failed to initialize MT5 at path: {target_path}, attempting default initialize...")

    # Fallback
    return bool(mt5.initialize(**kwargs))
