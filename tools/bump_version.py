"""
อัปเดตเลขเวอร์ชันของโปรเจกต์เป็นเวลาปัจจุบัน (รูปแบบ YYYY.MMDD.HHMM ตาม AGENTS.md)
ใช้ทุกครั้งที่แก้โค้ด ก่อน commit:

    python tools/bump_version.py            # ใช้เวลาปัจจุบัน
    python tools/bump_version.py 2026.1005.0930   # กำหนดเอง

แหล่งเวอร์ชันหลักคือ version.py — ไฟล์โค้ดอื่น import จากที่นั่น
สคริปต์นี้อัปเดต version.py และเลขเวอร์ชันในเอกสาร (AGENTS.md, SKILL.md)
"""
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(ROOT, "version.py")
DOC_FILES = [
    os.path.join(ROOT, "AGENTS.md"),
    os.path.join(ROOT, ".agents", "skills", "ai-trading-bot", "SKILL.md"),
]
PATTERN = re.compile(r"^\d{4}\.\d{4}\.\d{4}$")


def read_current() -> str:
    with open(VERSION_FILE, encoding="utf-8") as f:
        m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', f.read())
    return m.group(1) if m else ""


def main():
    new = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y.%m%d.%H%M")
    if not PATTERN.match(new):
        sys.exit(f"รูปแบบเวอร์ชันไม่ถูกต้อง: {new} (ต้องเป็น YYYY.MMDD.HHMM)")
    old = read_current()
    if old == new:
        print(f"เวอร์ชันเป็น {new} อยู่แล้ว")
        return

    with open(VERSION_FILE, encoding="utf-8") as f:
        src = f.read()
    src = re.sub(r'APP_VERSION\s*=\s*"[^"]+"', f'APP_VERSION = "{new}"', src)
    with open(VERSION_FILE, "w", encoding="utf-8", newline="") as f:
        f.write(src)

    for path in DOC_FILES:
        if not os.path.exists(path) or not old:
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if old in text:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text.replace(old, new))

    print(f"{old or '-'} -> {new}")


if __name__ == "__main__":
    main()
