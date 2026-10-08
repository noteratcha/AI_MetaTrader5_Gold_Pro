"""
ฟอนต์ของโปรแกรม — ชุดเดียวกับเว็บ (เปลี่ยน 8 ต.ค. 2026 ตามที่ผู้ใช้ขอ "ฟอนต์ที่นิยมตอนนี้")
- UI   = Anuphan (Cadson Demak · ไทย + อังกฤษ · OFL) — ข้อความทั้งหมด
- MONO = JetBrains Mono (OFL) — ตัวเลข/ราคา/Console (อักษรไทยใน Console Windows สลับไปฟอนต์ไทยของระบบให้เอง)
- ไฟล์อยู่ใน assets/fonts (แปลงจากไฟล์ Variable ของ Google Fonts เป็น Regular/Bold แบบ static เพราะ Tk/GDI ใช้ได้เสถียรกว่า)
- โหลดแบบ private (เฉพาะโปรเซสนี้ ไม่ติดตั้งลงเครื่องผู้ใช้) — โหลดไม่ได้จะใช้ Segoe UI / Consolas เหมือนเดิม
"""
import os
import sys

import customtkinter as ctk


def _fonts_dir() -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "assets", "fonts")


def _load(files) -> bool:
    ok = True
    for name in files:
        path = os.path.join(_fonts_dir(), name)
        try:
            ok = bool(os.path.exists(path) and ctk.FontManager.load_font(path)) and ok
        except Exception:
            ok = False
    return ok


UI = "Anuphan" if _load(("Anuphan-Regular.ttf", "Anuphan-Bold.ttf")) else "Segoe UI"
# ผู้ใช้ขอให้ทั้งโปรแกรมเป็นฟอนต์เดียว (8 ต.ค. 2026) — ตัวเลข/Console ใช้ Anuphan ด้วย (JetBrains Mono ไม่มีอักษรไทย ทำให้ไทยใน Console เป็นฟอนต์ระบบ)
MONO = UI
