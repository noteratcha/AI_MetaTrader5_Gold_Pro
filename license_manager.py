import os
import sys
import json
import time
import re
import urllib.request
import urllib.error
import hashlib
from datetime import datetime

# คีย์การเข้ารหัสและโฟลเดอร์เก็บข้อมูลลิขสิทธิ์
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "license_store.json")
ENV_LOCAL_PATH = os.path.join(BASE_DIR, "web", ".env.local")

# API URL ของ GoldBot24 Cloud Production
API_BASE_URL = os.environ.get("GOLDBOT_API_URL", "https://goldbot24-4jnnk2of7-noteratchas-projects.vercel.app")
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

    def login(self, email: str, password: str) -> tuple[bool, str]:
        """
        เข้าสู่ระบบด้วย Email + Password กับ GoldBot24 Cloud API (ปิดโหมด Demo เด็ดขาด)
        """
        email = email.strip().lower()
        password = password.strip()
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
            # Fallback direct Supabase check
            return self._fallback_supabase_login(email, password)

    def _fallback_supabase_login(self, email: str, password: str) -> tuple[bool, str]:
        """ตรวจสอบรหัสผ่านโดยตรงกับ Supabase bot_config ในกรณีเน็ตสะดุด"""
        try:
            query_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/bot_config?mt5_server=eq.{urllib.parse.quote(email)}&select=*"
            headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            req = urllib.request.Request(query_url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=6) as resp:
                rows = json.loads(resp.read().decode("utf-8"))
                if not rows:
                    return False, "ไม่พบบัญชีผู้ใช้นี้ในระบบ กรุณาสมัครสมาชิกก่อน"
                row = rows[0]
                stored_pwd = row.get("mt5_password", "")
                if not stored_pwd.startswith("v1$"):
                    return False, "รหัสผ่านไม่ถูกต้อง"
                parts = stored_pwd.split("$")
                salt = parts[1].encode("utf-8")
                expected = parts[2]
                actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(parts[1]), 10000, 32).hex()
                if actual != expected:
                    return False, "รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง"

                hrs = float(row.get("lot_size", 0.0))
                self.session_data["email"] = email
                self.session_data["username"] = email.split("@")[0]
                self.session_data["user_id"] = str(row.get("id", ""))
                self.session_data["token"] = "offline_session"
                self.session_data["hours_remaining_minutes"] = int(round(hrs * 60))
                self.session_data["status"] = "AUTHENTICATED"
                self.session_data["last_sync"] = int(time.time())
                self.is_authenticated = True
                self.save_local_store()
                return True, "เข้าสู่ระบบสำเร็จ (เชื่อมต่อ Cloud Direct)"
        except Exception as err:
            return False, f"ไม่สามารถเชื่อมต่ออินเทอร์เน็ตได้: {err}"

    def register(self, email: str, password: str, display_name: str = "") -> tuple[bool, str]:
        """
        สมัครสมาชิกบัญชีใหม่ผ่าน GoldBot24 Cloud API (รับทันที 48 ชั่วโมงทดลองใช้)
        """
        email = email.strip().lower()
        password = password.strip()
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

    def logout(self):
        """ออกจากระบบและล้างเซสชันในเครื่อง"""
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

    def sync_latest_hours(self):
        """ดึงยอดเวลาคงเหลือล่าสุดจาก Cloud"""
        if not self.session_data.get("email"):
            return
        email = self.session_data["email"]
        me_url = f"{API_BASE_URL.rstrip('/')}/api/auth/me?email={urllib.parse.quote(email)}"
        try:
            req = urllib.request.Request(me_url, headers={"User-Agent": "GoldBot24-Desktop"}, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success") and data.get("user"):
                    hrs = float(data["user"].get("hoursRemaining", 0.0))
                    self.session_data["hours_remaining_minutes"] = int(round(hrs * 60))
                    self.session_data["last_sync"] = int(time.time())
                    self.save_local_store()
        except Exception:
            pass

    def deduct_trading_minute(self, minutes_elapsed: int = 1):
        """
        ตัดเวลาการใช้งานจริงเมื่อบอทเปิดทำงาน (เรียกทุกๆ 1 นาที)
        """
        curr = self.session_data.get("hours_remaining_minutes", 0)
        new_val = max(0, curr - minutes_elapsed)
        self.session_data["hours_remaining_minutes"] = new_val
        self.save_local_store()

        # อัปเดต Cloud ทุกๆ 5 นาที หรือเมื่อเวลาหมด
        if new_val == 0 or (int(time.time()) - self.session_data.get("last_sync", 0)) > 300:
            self._update_cloud_hours(new_val / 60.0)

    def _update_cloud_hours(self, hours_val: float):
        """บันทึกเวลาที่ลดลงกลับไปยัง Supabase bot_config"""
        user_id = self.session_data.get("user_id")
        if not user_id:
            return
        try:
            patch_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/bot_config?id=eq.{user_id}"
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            }
            payload = json.dumps({"lot_size": hours_val, "updated_at": datetime.utcnow().isoformat()}).encode("utf-8")
            req = urllib.request.Request(patch_url, data=payload, headers=headers, method="PATCH")
            with urllib.request.urlopen(req, timeout=4) as _:
                self.session_data["last_sync"] = int(time.time())
        except Exception:
            pass

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
        payload = json.dumps({
            "email": self.session_data["email"],
            "keyCode": key
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        try:
            req = urllib.request.Request(redeem_url, data=payload, headers=headers, method="POST")
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
            try:
                err_data = json.loads(he.read().decode("utf-8"))
                return False, err_data.get("error", f"รหัสคีย์ไม่ถูกต้อง (HTTP {he.code})"), 0
            except Exception:
                return False, f"ไม่สามารถเติมคีย์ได้ (HTTP {he.code})", 0
        except Exception as e:
            return False, f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}", 0


# Global Singleton instance
license_mgr = LicenseManager()
