import os
import sys
import json
import time
import re
import urllib.request
import urllib.error


# คีย์การเข้ารหัสและโฟลเดอร์เก็บข้อมูลลิขสิทธิ์
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
from app_paths import data_path
CONFIG_FILE = data_path("license_store.json")  # %APPDATA%\GoldBot24 — อยู่รอดเมื่ออัปเดตโปรแกรม
ENV_LOCAL_PATH = os.path.join(BASE_DIR, "web", ".env.local")

# API URL ของ GoldBot24 Cloud Production
API_BASE_URL = os.environ.get("GOLDBOT_API_URL", "https://goldbot24.vercel.app")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://isliehicmtpsnuyxedln.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg")

if os.path.exists(ENV_LOCAL_PATH):
    try:
        with open(ENV_LOCAL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("NEXT_PUBLIC_SUPABASE_URL="):
                    SUPABASE_URL = line.split("=", 1)[1].strip()
                elif line.startswith("NEXT_PUBLIC_SUPABASE_ANON_KEY="):
                    SUPABASE_KEY = line.split("=", 1)[1].strip()
    except Exception:
        pass


def format_hours_minutes(total_minutes: int) -> str:
    """
    แปลงจำนวนนาทีทั้งหมดให้อยู่ในรูปแบบ 'ชั่วโมง.นาที' (HH.MM) เสมอ
    ตัวอย่าง:
      - 2880 นาที -> '48.00' (48 ชั่วโมง 0 นาที)
      - 60 นาที   -> '1.00'  (1 ชั่วโมง 0 นาที)
    """
    if total_minutes < 0:
        total_minutes = 0
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}.{minutes:02d}"


def normalize_key_input(raw: str) -> str:
    """จัดรูปแบบ Product Key: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"""
    if not raw:
        return ""
    clean = re.sub(r'[^A-Za-z0-9]', '', str(raw)).upper()[:24]
    chunks = [clean[i:i+4] for i in range(0, len(clean), 4)]
    return "-".join(chunks)


def validate_key_format(key: str) -> bool:
    """ตรวจสอบรูปแบบ Product Key 24 หลัก"""
    pattern = r'^[A-Z0-9]{4}(-[A-Z0-9]{4}){5}$'
    return bool(re.match(pattern, key.strip()))


class LicenseManager:
    """
    ระบบจัดการสิทธิ์การใช้งานจริง 100% (ปิดโหมด Demo)
    ผู้ใช้งานต้องลงทะเบียนและเข้าสู่ระบบด้วยบัญชี GoldBot24 จริงเท่านั้น
    """

    def __init__(self):
        self.session_data = {
            "email": "",
            "username": "",
            "user_id": "",
            "token": "",
            "hours_remaining_minutes": 0,
            "status": "LOGGED_OUT",
            "last_sync": 0
        }
        self.is_authenticated = False
        self.load_local_store()

    def load_local_store(self):
        """โหลดสถานะบัญชีที่เคยล็อกอินไว้จาก license_store.json"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if saved.get("email") and saved.get("token"):
                        self.session_data.update(saved)
                        self.is_authenticated = True
                        # ซิงค์ชั่วโมงล่าสุดจาก Cloud ในเบื้องหลัง
                        self.sync_latest_hours()
            except Exception as e:
                print(f"[LicenseManager] Warning reading license store: {e}")

    def save_local_store(self):
        """บันทึกสถานะบัญชีลง license_store.json"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.session_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[LicenseManager] Error saving license store: {e}")

    def get_remaining_time_display(self) -> str:
        """ส่งคืนเวลาคงเหลือในรูปแบบ 'ชั่วโมง.นาที' (HH.MM)"""
        return format_hours_minutes(self.session_data.get("hours_remaining_minutes", 0))

    def get_current_user(self) -> dict:
        """ส่งคืนข้อมูลผู้ใช้งานปัจจุบัน"""
        return {
            "user_id": self.session_data.get("user_id") or "",
            "email": self.session_data.get("email") or "",
            "username": self.session_data.get("username") or "Trader"
        }

    def get_remaining_minutes(self) -> int:
        return self.session_data.get("hours_remaining_minutes", 0)

    def has_active_hours(self) -> bool:
        """ตรวจสอบว่าเข้าสู่ระบบแล้ว และยังมีเวลาคงเหลือมากกว่า 0 หรือไม่"""
        return self.is_authenticated and self.session_data.get("hours_remaining_minutes", 0) > 0

    def login(self, email: str, password: str, remember_me: bool = True) -> tuple[bool, str]:
        """
        เข้าสู่ระบบด้วย Email + Password กับ GoldBot24 Cloud API (ปิดโหมด Demo เด็ดขาด)
        """
        email = email.strip().lower()
        # ไม่ตัดช่องว่างของรหัสผ่าน (ต้องตรงกับเว็บ — เว็บส่งรหัสผ่านตามที่พิมพ์)
        if not email or not password:
            return False, "กรุณากรอกอีเมลและรหัสผ่านให้ครบถ้วน"

        # 1. เรียก API Endpoint /api/auth/login
        login_url = f"{API_BASE_URL.rstrip('/')}/api/auth/login"
        payload = json.dumps({"email": email, "password": password}).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        try:
            req = urllib.request.Request(login_url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success") and data.get("user"):
                    u = data["user"]
                    hrs = float(u.get("hoursRemaining", 0.0))
                    self.session_data["email"] = u.get("email", email)
                    self.session_data["username"] = u.get("displayName") or email.split("@")[0]
                    self.session_data["user_id"] = str(u.get("id", ""))
                    self.session_data["token"] = data.get("token", "")
                    self.session_data["hours_remaining_minutes"] = int(round(hrs * 60))
                    self.session_data["status"] = "AUTHENTICATED"
                    self.session_data["last_sync"] = int(time.time())
                    self.session_data["remember_me"] = bool(remember_me)
                    self.is_authenticated = True
                    self.save_local_store()
                    return True, f"เข้าสู่ระบบสำเร็จ! ยินดีต้อนรับ {self.session_data['username']}"
                else:
                    return False, data.get("error", "เข้าสู่ระบบไม่สำเร็จ")
        except urllib.error.HTTPError as he:
            try:
                err_data = json.loads(he.read().decode("utf-8"))
                return False, err_data.get("error", f"เกิดข้อผิดพลาดในการตรวจสอบ (HTTP {he.code})")
            except Exception:
                return False, f"เข้าสู่ระบบไม่สำเร็จ: รหัสผ่านไม่ถูกต้อง (HTTP {he.code})"
        except Exception as e:
            return False, f"ไม่สามารถเชื่อมต่อ GoldBot24 Cloud ได้: {e}"

    def register(self, email: str, password: str, display_name: str = "") -> tuple[bool, str]:
        """
        สมัครสมาชิกบัญชีใหม่ผ่าน GoldBot24 Cloud API (รับทันที 48 ชั่วโมงทดลองใช้)
        """
        email = email.strip().lower()
        # ไม่ตัดช่องว่างของรหัสผ่าน (ต้องตรงกับเว็บ — เว็บส่งรหัสผ่านตามที่พิมพ์)
        display_name = display_name.strip() or email.split("@")[0]

        if not email or "@" not in email:
            return False, "กรุณากรอกอีเมลที่ถูกต้อง"
        if len(password) < 6:
            return False, "รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร"

        reg_url = f"{API_BASE_URL.rstrip('/')}/api/auth/register"
        payload = json.dumps({
            "email": email,
            "password": password,
            "displayName": display_name
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        try:
            req = urllib.request.Request(reg_url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success") and data.get("user"):
                    u = data["user"]
                    hrs = float(u.get("hoursRemaining", 48.0))
                    self.session_data["email"] = email
                    self.session_data["username"] = display_name
                    self.session_data["user_id"] = str(u.get("id", ""))
                    self.session_data["token"] = data.get("token", "")
                    self.session_data["hours_remaining_minutes"] = int(round(hrs * 60))
                    self.session_data["status"] = "AUTHENTICATED"
                    self.session_data["last_sync"] = int(time.time())
                    self.session_data["remember_me"] = True
                    self.is_authenticated = True
                    self.save_local_store()
                    return True, "สมัครสมาชิกสำเร็จ! ได้รับโควต้าเริ่มต้น 48 ชั่วโมงเรียบร้อยแล้ว"
                else:
                    return False, data.get("error", "สมัครสมาชิกไม่สำเร็จ")
        except urllib.error.HTTPError as he:
            try:
                err_data = json.loads(he.read().decode("utf-8"))
                return False, err_data.get("error", f"เกิดข้อผิดพลาดในการสมัครสมาชิก (HTTP {he.code})")
            except Exception:
                return False, f"สมัครสมาชิกไม่สำเร็จ (HTTP {he.code})"
        except Exception as e:
            return False, f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}"

    def logout(self, flush: bool = True):
        """ออกจากระบบและล้างเซสชันในเครื่อง (ส่งนาทีที่ค้างหักให้ Server ก่อน)"""
        if flush:
            self._flush_meter()
        self.session_data = {
            "email": "",
            "username": "",
            "user_id": "",
            "token": "",
            "hours_remaining_minutes": 0,
            "status": "LOGGED_OUT",
            "last_sync": 0
        }
        self.is_authenticated = False
        if os.path.exists(CONFIG_FILE):
            try:
                os.remove(CONFIG_FILE)
            except Exception:
                pass

    def _auth_headers(self) -> dict:
        headers = {"Content-Type": "application/json", "User-Agent": "GoldBot24-Desktop"}
        token = self.session_data.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _handle_auth_error(self, code: int):
        """Token หมดอายุ/ไม่ถูกต้อง (เช่น token รุ่นเก่าที่ไม่มีลายเซ็น) — บังคับล็อกอินใหม่"""
        if code == 401:
            self.logout(flush=False)

    def sync_latest_hours(self):
        """ดึงยอดเวลาคงเหลือล่าสุดจาก Cloud (ยืนยันตัวตนด้วย Token)"""
        if not self.session_data.get("token"):
            return
        me_url = f"{API_BASE_URL.rstrip('/')}/api/auth/me"
        try:
            req = urllib.request.Request(me_url, headers=self._auth_headers(), method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success") and data.get("user"):
                    hrs = float(data["user"].get("hoursRemaining", 0.0))
                    # หักนาทีที่ใช้ไปแล้วแต่ยังไม่ได้ส่งขึ้น Server ออกด้วย
                    pending = int(self.session_data.get("pending_meter_minutes", 0))
                    self.session_data["hours_remaining_minutes"] = max(0, int(round(hrs * 60)) - pending)
                    self.session_data["last_sync"] = int(time.time())
                    self.save_local_store()
        except urllib.error.HTTPError as he:
            self._handle_auth_error(he.code)
        except Exception:
            pass

    def deduct_trading_minute(self, minutes_elapsed: int = 1) -> tuple[bool, int, str]:
        """
        ตัดเวลาการใช้งานจริงเมื่อบอทเปิดทำงาน (เรียกทุกๆ 1 นาที)
        - ตัดในเครื่องทันที แล้วส่งยอดที่ค้างไปให้ Server หักจริงทุก 5 นาที (หรือเมื่อเวลาหมด)
        - คืนค่า (ยังมีเวลาเหลือหรือไม่, นาทีคงเหลือ, ข้อความ HH.MM)
        """
        curr = self.session_data.get("hours_remaining_minutes", 0)
        new_val = max(0, curr - minutes_elapsed)
        self.session_data["hours_remaining_minutes"] = new_val
        self.session_data["pending_meter_minutes"] = int(self.session_data.get("pending_meter_minutes", 0)) + (curr - new_val)
        self.save_local_store()

        if new_val == 0 or (int(time.time()) - self.session_data.get("last_sync", 0)) > 300:
            self._flush_meter()

        remaining = self.session_data.get("hours_remaining_minutes", 0)
        return remaining > 0, remaining, format_hours_minutes(remaining)

    def _flush_meter(self):
        """ส่งนาทีที่ใช้ไปให้ Server หักออกจากบัญชี (/api/auth/meter) แล้วรับยอดคงเหลือที่ถูกต้องกลับมา"""
        pending = int(self.session_data.get("pending_meter_minutes", 0))
        if pending <= 0 or not self.session_data.get("token"):
            return
        meter_url = f"{API_BASE_URL.rstrip('/')}/api/auth/meter"
        payload = json.dumps({"minutes": pending}).encode("utf-8")
        try:
            req = urllib.request.Request(meter_url, data=payload, headers=self._auth_headers(), method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success"):
                    hrs = float(data.get("hoursRemaining", 0.0))
                    self.session_data["hours_remaining_minutes"] = int(round(hrs * 60))
                    self.session_data["pending_meter_minutes"] = 0
                    self.session_data["last_sync"] = int(time.time())
                    self.save_local_store()
        except urllib.error.HTTPError as he:
            self._handle_auth_error(he.code)
        except Exception:
            pass  # เน็ตหลุด — เก็บยอดค้างไว้ส่งรอบถัดไป

    def check_app_version(self, current_version: str) -> dict:
        """ตรวจสอบว่ามีเวอร์ชันใหม่กว่าที่ใช้งานอยู่หรือไม่"""
        return fetch_app_version_info(current_version)

    def redeem_product_key(self, raw_key: str) -> tuple[bool, str, int]:
        """
        เติมชั่วโมงด้วย Product Key:
        - ติดต่อ API /api/auth/redeem
        - บวกเพิ่มชั่วโมง (+) เข้ากระเป๋าบัญชีนี้ทันที
        """
        if not self.is_authenticated or not self.session_data.get("email"):
            return False, "กรุณาเข้าสู่ระบบก่อนเติม Product Key", 0

        key = normalize_key_input(raw_key)
        if not validate_key_format(key):
            return False, "รูปแบบรหัสไม่ถูกต้อง! ต้องเป็น: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX (24 หลัก)", 0

        redeem_url = f"{API_BASE_URL.rstrip('/')}/api/auth/redeem"
        payload = json.dumps({"keyCode": key}).encode("utf-8")

        try:
            req = urllib.request.Request(redeem_url, data=payload, headers=self._auth_headers(), method="POST")
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success"):
                    hrs_added = int(data.get("hoursAdded", 0))
                    new_bal = float(data.get("hoursRemaining", 0.0))
                    self.session_data["hours_remaining_minutes"] = int(round(new_bal * 60))
                    self.save_local_store()
                    return True, data.get("message", "เติมเวลาสำเร็จ!"), hrs_added
                else:
                    return False, data.get("error", "ไม่สามารถเติมคีย์ได้"), 0
        except urllib.error.HTTPError as he:
            if he.code == 401:
                self.logout(flush=False)
                return False, "เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่อีกครั้ง", 0
            try:
                err_data = json.loads(he.read().decode("utf-8"))
                return False, err_data.get("error", f"รหัสคีย์ไม่ถูกต้อง (HTTP {he.code})"), 0
            except Exception:
                return False, f"ไม่สามารถเติมคีย์ได้ (HTTP {he.code})", 0
        except Exception as e:
            return False, f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}", 0


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in str(v).strip().lstrip("v").split("."))
    except Exception:
        return (0,)


def fetch_app_version_info(current_version: str) -> dict:
    """
    ตรวจสอบเวอร์ชันล่าสุด: GoldBot24 API (/api/release ← GitHub Releases) แล้ว fallback ตาราง app_releases
    """
    latest = None
    try:
        req = urllib.request.Request(f"{API_BASE_URL.rstrip('/')}/api/release", headers={"User-Agent": "GoldBot24-Desktop"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            latest = (json.loads(resp.read().decode("utf-8")) or {}).get("release")
    except Exception:
        latest = None

    if not latest or not latest.get("version"):
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/app_releases?select=version,download_url,changelog,mandatory&order=released_at.desc&limit=1"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=6) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
        latest = rows[0] if rows else None

    if not latest:
        return {"has_update": False, "latest_version": current_version}
    return {
        "has_update": _version_tuple(latest.get("version")) > _version_tuple(current_version),
        "latest_version": latest.get("version"),
        # หน้าเว็บดาวน์โหลดมีวิธีติดตั้ง + checksum
        "download_url": f"{API_BASE_URL.rstrip('/')}/download",
        "changelog": latest.get("changelog"),
        "mandatory": bool(latest.get("mandatory")),
    }


# Global Singleton instance
license_mgr = LicenseManager()
