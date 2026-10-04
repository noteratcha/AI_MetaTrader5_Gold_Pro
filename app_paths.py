"""
ตำแหน่งเก็บข้อมูลผู้ใช้ของ Desktop App
- เก็บใน %APPDATA%\\GoldBot24 เพื่อให้อยู่รอดเมื่ออัปเดตโปรแกรม (โฟลเดอร์โปรแกรม/dist ถูกลบสร้างใหม่ทุกครั้งที่ build)
- ย้ายไฟล์เดิมจากโฟลเดอร์โปรแกรมมาให้อัตโนมัติครั้งแรก
"""
import os
import shutil
import sys

APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "GoldBot24")

try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError:
    DATA_DIR = APP_DIR


def data_path(name: str) -> str:
    """คืน path ไฟล์ข้อมูลใน DATA_DIR (ย้ายไฟล์เก่าจากโฟลเดอร์โปรแกรมมาให้ถ้ายังไม่มี)"""
    target = os.path.join(DATA_DIR, name)
    if not os.path.exists(target):
        for legacy_dir in (APP_DIR, os.path.join(APP_DIR, "_internal")):
            legacy = os.path.join(legacy_dir, name)
            if legacy != target and os.path.exists(legacy):
                try:
                    shutil.copy2(legacy, target)
                except OSError:
                    pass
                break
    return target
