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

### 🚀 ระบบอัปเดตแพตช์ทับ Path เดิมอัตโนมัติ (1-Click In-App In-Place Updater)
- **อัปเดตง่ายไม่ต้องติดตั้งใหม่เอง**: เมื่อมีเวอร์ชันใหม่ เพียงคลิกปุ่ม `[ 🚀 อัปเดตแพตช์ทันที (1-Click) ]` ในโปรแกรม
- **ดาวน์โหลดพร้อม Progress Bar สด**: แสดง % ความคืบหน้า, จำนวน MB ที่โหลด และความเร็ว (MB/s) แบบเรียลไทม์
- **In-Place Patching & Auto-Restart**: โปรแกรมจะปิดและแตกไฟล์/ติดตั้งแพตช์ทับ Path เดิมอย่างเงียบกริบ (Silent Update) แล้วสตาร์ทโปรแกรมเวอร์ชันใหม่ขึ้นมาทันทีอัตโนมัติ
- **ปลอดภัย ข้อมูลอยู่ครบ 100%**: การตั้งค่าบอททั้งหมด, บัญชีผู้ใช้, ข้อมูล MT5 และประวัติพอร์ตยังคงอยู่ครบถ้วน ไม่ต้องตั้งค่าใหม่

### ⭐ แนวรับ–แนวต้าน 2 ระดับ (S1/S2 และ R1/R2) พร้อมดาวความแข็งแกร่ง (1.0 - 5.0 ดาว)
- **ระบบคำนวณแนวรับ–แนวต้าน 2 ระดับ**:
  - `R1 / S1`: โซนระดับราคาใกล้เคียงปัจจุบันที่สุด
  - `R2 / S2`: โครงสร้างจุดกลับตัวสวิงหลักถัดไป (คัดกรองระยะห่างขั้นต่ำ >= 0.75 ATR เพื่อป้องกันโซนซ้ำซ้อน)
- **ประเมินระดับความแข็งแกร่งด้วยดาว (Support & Resistance Strength)**:
  - คำนวณระดับความแข็งแกร่ง 1.0 - 5.0 ดาว (ปัดขั้นละ 0.5) จากจำนวนครั้งที่ราคาเคยทดสอบและเด้งกลับตัวในโซน
  - กราฟแท่งเทียนสด: วาดเส้น R1 (แดง), R2 (ส้มแดง), S1 (เขียว), S2 (เขียวมรกต) พร้อมวาดดาวเวกเตอร์ 5 แฉก (Vector Polygon) คมชัดระดับพิกเซล รองรับทั้งดาวเต็มดวงและระบายสีครึ่งดวง (Half Star) พร้อมกำกับตัวเลข เช่น `(2.5★)`
  - การ์ด Dashboard `🧱 แนวรับ – แนวต้าน`: แสดงดาวความแข็งแกร่ง (เช่น `★★½`, `★★★`) และสามารถคลิกการ์ดเพื่อเปิดดูกราฟแท่งเทียนสดพร้อมตำแหน่ง S&R ได้ทันที

### 🎯 เลือกดูอินดิเคเตอร์ตรงตามแผนแต่ละไทม์เฟรมได้ทันที (P1, P2, P3, P4, P5, P6, เทรนด์ H4)
- **แถบเลือกตามแผน (Plan Selector Bar)**: คลิกเลือกแผนที่ต้องการดูได้ทันที:
  - `[ P1 · M15 ]`: สลับเข้า M15 แสดงเฉพาะ MA5, MA13, MA50 (แผน MA-Cross-Trend)
  - `[ P2 · H1 ]`: สลับเข้า H1 แสดงเฉพาะ H1 MA5, MA10, MA20 (แผน MA-Cross-H1-Trend)
  - `[ P3 · H1 (SMC) ]`: สลับเข้า H1 แสดงเฉพาะแนวรับ-แนวต้าน H1 (แผน SMC-LiquidityHunt)
  - `[ P4 · H1 (SR) ]`: สลับเข้า H1 แสดงเฉพาะแนวรับ-แนวต้าน H1 (แผน SR-SwingBounce)
  - `[ P5 · H1 (BB) ]`: สลับเข้า H1 แสดงเฉพาะ Bollinger Bands H1 (แผน BB-H1-Reversion)
  - `[ P6 · H1 (PSAR) ]`: สลับเข้า H1 แสดงเฉพาะ Parabolic SAR H1 & EMA100 H1 (แผน PSAR-H1-Trend)
  - `[ เทรนด์ H4 ]`: สลับเข้า H4 แสดงเฉพาะสภาวะเทรนด์ใหญ่ MA10, MA30, MA200
  - `[ รวมทุกแผน ]`: แสดงอินดิเคเตอร์ทั้งหมดในไทม์เฟรมที่กำลังเลือก
- **ปุ่มชิปอินดิเคเตอร์ติดป้ายรหัสแผนชัดเจน**: เช่น `P1 · ━ MA5`, `P2 · ━ MA5`, `P3/P4 · ┅ แนวต้าน`, `P5 · ━ BB H1`, `P6 · • SAR H1` คลิกเปิด/ปิดแต่ละเส้นได้อย่างอิสระ
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
