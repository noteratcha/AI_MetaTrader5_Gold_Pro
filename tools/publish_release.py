"""
สร้าง GitHub Release + อัปโหลดตัวติดตั้ง Setup.exe และ ZIP อัตโนมัติ
ใช้ Git Credential Manager เพื่อดึง GitHub Token ในเครื่อง
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.request

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from version import APP_VERSION

REPO = "noteratcha/AI_MetaTrader5_Gold_Pro"
TAG = f"v{APP_VERSION}"
ZIP = os.path.join(ROOT, "dist", f"AI_Gold_Commander_Pro_{TAG}.zip")
SETUP = os.path.join(ROOT, "dist", f"GoldBot24_Setup_{TAG}.exe")

RELEASE_NOTES = f"""## AI Gold Commander Pro {TAG}

### ⚡ แสดงสถานะเงื่อนไขเข้าไม้เรียลไทม์ของแต่ละแผน (Live Entry Conditions)
- **หน้าต่างกราฟสด (`GoldCandleDialog`)**:
  - บนปุ่มเลือกดูตามแผนมีป้ายระบุจำนวนเงื่อนไขที่เข้าแล้วแบบเรียลไทม์ เช่น `P1 · M15 (2/4)`, `P2 · H1 (3/4)` พร้อมไฟไฮไลต์สีเขียวสดใส `★ (4/4)` เมื่อเข้าเงื่อนไขครบ 100% สัญญาณพร้อมยิง
  - แถบสถานะเงื่อนไขการเข้าไม้ใหม่ (`Condition Status Bar`):
    - เมื่อเลือกดู "รวมทุกแผน": แสดงสรุปชิปทุกแผน (P1-P6) คู่กับทิศทาง ▲/▼ และจำนวนข้อที่เข้า (สามารถคลิกที่ชิปเพื่อข้ามไปยังแผนนั้นได้ทันที)
    - เมื่อเลือกดูแผนเฉพาะ (P1-P6): แสดงทิศทางไม้ (BUY/SELL) พร้อมแถบ Checklist ชิปแต่ละข้อ มีเครื่องหมาย `[✓ ผ่าน]`/`[✗ ไม่ผ่าน]` และตัวเลขค่าจริงทางเทคนิค (RSI, MA, S&R, ไส้เทียน, AI %) พร้อมอัปเดตคำอธิบายเมื่อชี้เมาส์ (Hover)
- **ตารางแผนเทรดบน Dashboard หลัก**: แสดงจำนวนข้อที่เข้า ณ ราคาปัจจุบัน (เช่น `▲ 3/4 ข้อ`) แทนช่องว่างเมื่อยังไม่มีไม้เปิดของแผนนั้น

### 🔴/🟢 ข้อมูลสถานะตลาดทองคำเปิด-ปิดสด (Market Hours & Realtime Status)
- **ระบบคำนวณตารางเวลาตลาดทองคำ (XAUUSD)**: คำนวณตามเวลาประเทศไทย (UTC+7) เที่ยงตรง 100% (เปิด จันทร์ 05:00 น. ถึง เสาร์ 04:00 น. · พักเบรก อังคาร–ศุกร์ 04:00–05:00 น. · ปิดสุดสัปดาห์ เสาร์ 04:00 น. ถึง จันทร์ 05:00 น.)
- **แสดงสถานะตลาดครบทุกจุดในโปรแกรม**:
  - การ์ดราคาทองคำ XAUUSD: มีป้ายกำกับสด `● ตลาดเปิด` (เขียว) หรือ `● ตลาดปิด` (แดง) พร้อมระบุเวลาเปิดรอบถัดไป
  - แถบเครื่องมือคอนโซล: มีป้ายสถานะตลาดสด เช่น `🔴 ตลาดปิด · เปิด จ. 05:00 น.`
  - แบนเนอร์หัวคอนโซล: แสดงสถานะตลาดพร้อมเวลานับถอยหลัง เช่น `🔴 ตลาดทองคำปิดทำการ (วันหยุดสุดสัปดาห์) · เปิดวันจันทร์ เวลา 05:00 น. (ในอีก 1 วัน 16 ชม.)`
  - เมื่อกดปุ่มเริ่มบอทช่วงตลาดปิด: แจ้งเตือน `[MARKET]` อัตโนมัติในคอนโซลพร้อมยืนยันว่าระบบเข้าสู่โหมดสแตนด์บายและไม่หักชั่วโมงการใช้งาน

### 🚫 ป้องกันข้อมูลสแกนซ้ำซ้อนในคอนโซล (Smart Deduplication)
- **ไม่แสดงข้อความซ้ำเดิม**: หากข้อมูลการสแกน (ราคา, AI %, ทิศทาง H4, สถานะ) ซ้ำกับรอบที่แล้ว ระบบจะไม่พิมพ์ข้อความซ้ำรัวๆ ทุก 20 วินาทีในคอนโซล
- **อัปเดตทันทีเมื่อมีการเปลี่ยนแปลง**: แสดงผลทันทีที่มีการขยับของราคา, สัญญาณใหม่, หรือสถานะเปลี่ยนแปลง ช่วยให้หน้าจอสะอาดตา สบายตา และอ่านง่าย

### 🛡️ ป้องกันการเปิดโปรแกรมซ้ำซ้อน (Single Instance Guard)
- ล็อกด้วย Windows Named Mutex หากมีหน้าต่างโปรแกรมเปิดอยู่แล้ว ระบบจะไม่เปิดซ้อน แต่จะดึงหน้าต่างเดิมขึ้นมาใช้งานทันที

### 🧱 แนวรับ–แนวต้าน 5 ระดับ (R1..R5 & S1..S5) บนกราฟแท่ง H1 และ H4 (500 แท่ง)
- **รองรับแนวรับ–แนวต้านบน Timeframe H4**: คำนวณจากแท่งเทียน H4 ย้อนหลัง 500 แท่ง แสดงโครงสร้างสวิงระดับรอบใหญ่ของ H4 ครบ 5 ระดับ (R1..R5 และ S1..S5) พร้อมดาวความแข็งแกร่ง (1.0 - 5.0 ดาว)
- **ชิปเปิด/ปิดอินดิเคเตอร์แยกอิสระบน H4**: บนกราฟ H4 มีปุ่ม `[ H4 · ┅ แนวต้าน ]` และ `[ H4 · ┅ แนวรับ ]` สามารถคลิกเปิด/ปิดได้อย่างอิสระ
- **เปิดดูกราฟ 500 แท่งอัตโนมัติ**: ระบบเปิดหน้าต่างกราฟแท่งเทียนสดพร้อมแนวรับแนวต้านคำนวณจาก 500 แท่งปิดเสมอ เพื่อภาพรวมโครงสร้างราคาที่ชัดเจนที่สุด

### 🚀 ระบบอัปเดตแพตช์ทับ Path เดิมอัตโนมัติ (1-Click In-App In-Place Updater)
- อัปเดตแพตช์ทับ Path เดิมแบบ Silent Update พร้อมเปิดโปรแกรมเวอร์ชันใหม่ให้อัตโนมัติ ข้อมูลผู้ใช้ไม่สูญหาย
- **สลับไทม์เฟรม M15 / H1 / H4 อิสระ**: กราฟแท่งเทียนเรียลไทม์พร้อมนับถอยหลังปิดแท่ง และคำนวณสเกลราคาอัตโนมัติตามเฉพาะอินดิเคเตอร์ที่เปิดอยู่

### 🔴 สถานะตลาดปิดเป็นสีแดง & ไอคอนเปลี่ยนสีตามสถานะ
- ปรับป้าย `[⏸ ตลาดปิด]` และไอคอนบนการ์ดบัญชี MT5 ให้เป็นสีแดง (`COLOR_DANGER_RED`) พื้นหลังแดงเข้ม (`#2A1414`) เมื่อตลาดปิดทำการ

### 💰 กำหนดหลักประกัน 100 USD ต่อไม้
- ปรับสูตรหลักประกันต่อไม้เป็น 100 USD ต่อ 1 ไม้ (ที่ Lot 0.01)

**วิธีติดตั้ง:** ดาวน์โหลด `GoldBot24_Setup_{TAG}.exe` แล้วดับเบิลคลิกติดตั้ง หรือใช้ไฟล์ ZIP แบบไม่ต้องติดตั้ง
"""


def get_github_token():
    try:
        out = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            cwd=ROOT,
        ).stdout
        for line in out.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    except Exception as e:
        print(f"Error getting git credential: {e}")
    return os.environ.get("GITHUB_TOKEN", "")


def github_api(url, token, data=None, content_type="application/json", method=None):
    req = urllib.request.Request(
        url,
        data=data,
        method=method or ("POST" if data else "GET"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": content_type,
            "User-Agent": "GoldBot24-Release",
        },
    )
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    token = get_github_token()
    if not token:
        sys.exit("❌ ไม่พบ GitHub Token (ตรวจสอบ git credential หรือ GITHUB_TOKEN)")

    if not os.path.exists(ZIP) and not os.path.exists(SETUP):
        sys.exit(f"❌ ไม่พบไฟล์ build ใน dist/ (ต้องมี {ZIP} หรือ {SETUP})")

    print(f"🚀 กำลังสร้าง GitHub Release สำหรับเวอร์ชัน: {TAG}...")
    sha_setup = hashlib.sha256(open(SETUP, "rb").read()).hexdigest() if os.path.exists(SETUP) else ""
    sha_zip = hashlib.sha256(open(ZIP, "rb").read()).hexdigest() if os.path.exists(ZIP) else ""

    body_text = RELEASE_NOTES
    if sha_setup:
        body_text += f"\nSHA-256 (Setup): `{sha_setup}`"
    if sha_zip:
        body_text += f"\nSHA-256 (ZIP): `{sha_zip}`"

    payload = {
        "tag_name": TAG,
        "target_commitish": "main",
        "name": f"AI Gold Commander Pro {TAG}",
        "body": body_text,
        "draft": False,
        "prerelease": False,
        "make_latest": "true",
    }

    try:
        rel = github_api(
            f"https://api.github.com/repos/{REPO}/releases",
            token,
            data=json.dumps(payload).encode("utf-8"),
        )
        print(f"✅ สร้าง Release สำเร็จ: {rel.get('html_url')}")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        if "already_exists" in err_msg:
            print(f"⚠️ Tag {TAG} มีอยู่แล้ว กำลังดึง release ที่มีอยู่...")
            rel = github_api(f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}", token)
        else:
            sys.exit(f"❌ สร้าง Release ไม่สำเร็จ: {e} | {err_msg}")

    # อัปโหลด Assets
    rel_id = rel["id"]
    for file_path, ctype in (
        (SETUP, "application/vnd.microsoft.portable-executable"),
        (ZIP, "application/zip"),
    ):
        if not os.path.exists(file_path):
            continue
        fname = os.path.basename(file_path)
        print(f"📦 กำลังอัปโหลด {fname} ({os.path.getsize(file_path) / (1024*1024):.2f} MB)...")
        upload_url = f"https://uploads.github.com/repos/{REPO}/releases/{rel_id}/assets?name={fname}"
        try:
            with open(file_path, "rb") as f:
                asset_data = f.read()
            asset = github_api(upload_url, token, data=asset_data, content_type=ctype)
            print(f"   ✓ อัปโหลดสำเร็จ: {asset.get('browser_download_url')}")
        except Exception as e:
            print(f"   ❌ อัปโหลด {fname} ล้มเหลว: {e}")

    print("\n🎉 เผยแพร่เวอร์ชันใหม่สำเร็จเรียบร้อยแล้ว 100%!")


if __name__ == "__main__":
    main()
