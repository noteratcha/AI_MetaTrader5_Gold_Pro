"""
ข่าวสาร/โปรโมชันจากแอดมิน (/api/announcements — ชุดเดียวกับเว็บ) + ประวัติการสะสมชั่วโมง (/api/user/hours-history)
- เรียกจากเธรดเบื้องหลังเท่านั้น (เครือข่าย) — หน้าจอรับผลผ่านตัวแปร (ห้ามเรียก Tk จากเธรดอื่น)
- จำข่าวที่ผู้ใช้เห็นแล้วใน %APPDATA%\\GoldBot24\\seen_news.json (เด้งป๊อปอัปเฉพาะข่าวใหม่)
"""
import io
import json
import os
import urllib.request

from app_paths import data_path
from license_manager import API_BASE_URL, license_mgr

_SEEN_FILE = data_path("seen_news.json")
_UA = {"User-Agent": "GoldBot24-Desktop"}


def _get_json(path, auth=False, timeout=8):
    headers = license_mgr._auth_headers() if auth else dict(_UA)
    req = urllib.request.Request(f"{API_BASE_URL.rstrip('/')}{path}", headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_announcements():
    """รายการข่าวที่กำลังแสดง ใหม่สุดก่อน — [] ถ้าดึงไม่ได้"""
    try:
        return _get_json("/api/announcements").get("items") or []
    except Exception:
        return []


def fetch_image(url, max_w=520):
    """ดาวน์โหลดรูปข่าว (https เท่านั้น · ไม่เกิน 5 MB) → PIL Image ย่อให้กว้างไม่เกิน max_w หรือ None"""
    if not url or not str(url).lower().startswith("https://"):
        return None
    try:
        from PIL import Image
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            return None
        img = Image.open(io.BytesIO(raw))
        img.load()
        if img.width > max_w:
            img = img.resize((max_w, int(img.height * max_w / img.width)), Image.LANCZOS)
        return img.convert("RGBA")
    except Exception:
        return None


def seen_ids():
    try:
        with open(_SEEN_FILE, encoding="utf-8") as f:
            return set(int(x) for x in json.load(f))
    except Exception:
        return set()


def mark_seen(ids):
    s = seen_ids() | {int(i) for i in ids}
    try:
        with open(_SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(s)[-300:], f)
    except Exception:
        pass


def fetch_hours_history(days=30):
    """{rows: [{day, minutes}], available, online} หรือ None ถ้าดึงไม่ได้"""
    try:
        d = _get_json(f"/api/user/hours-history?days={int(days)}", auth=True)
        return d if d.get("success") else None
    except Exception:
        return None
