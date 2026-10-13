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

RELEASE_NOTES = f"""## Gold Bot 24 {TAG}

### สัญลักษณ์สมาชิก
- สมาชิกรายเดือนมีป้าย MEMBER พร้อมมงกุฎข้างชื่อผู้ใช้ (ชี้ดูวันหมดอายุ · คลิกเพื่อต่ออายุ) — บนเว็บแสดงที่เมนูบนเช่นกัน

### ใหม่: สมาชิกรายเดือน (99 บาท / 30 วัน)
- ผู้ใช้ทั่วไปใช้ได้แผน P1–P5 · **สมาชิกรายเดือนปลดล็อก P6–P8** (ยังหักชั่วโมงตามปกติ)
- สมัคร/ต่ออายุที่หน้าเติมชั่วโมง (PromptPay + แนบสลิป) — ส่วนลด Lv. และออนไลน์ 100 ชม. ใช้ได้ · ต่อก่อนหมดนับต่อจากวันเดิม
- การ์ดแผนเทรด: แผนที่ต้องเป็นสมาชิกแสดงสีเทา "· สมาชิก" (คลิกเพื่อสมัคร) · กระเป๋าเวลาแสดงวันหมดอายุ · เหลือ ≤ 3 วันมีหน้าต่างเตือน
- ไม้ของ P6–P8 ที่เปิดอยู่ตอนสมาชิกหมดอายุ บอทยังดูแลจนปิด (ไม่เปิดไม้ใหม่)

### ปรับหน้าจอ: การ์ดแผนเทรด
- แถวแผนเกินพื้นที่การ์ด (จอเล็ก) → มีสกรอลบาร์ให้เลื่อนลง และเลื่อนด้วยลูกล้อเมาส์ได้ · พื้นที่พอจะซ่อนสกรอลบาร์เอง
- Console แสดงหัวข้อ P7 / P8 ในสรุปความพร้อมเงื่อนไขตอนเริ่มบอทครบ

### ใหม่: แผน P7 และ P8 (Bollinger H4)
- หลักการเดียวกับ P5 แต่ใช้ขอบ Bollinger Bands H4: ราคาหลุดขอบ H4 แล้วแท่ง M15 ปิดกลับเข้ากรอบ + ไส้เทียน + Divergence + AI ≥ 55% + H1 MA100/150/200 ไม่เรียงตามทิศไม้
- **P7 · BB-H4**: ไม่เข้าสวนเทรนด์ H4 MA10/30 (สัญญาณน้อย คัดมาก)
- **P8 · BB-H4 Free**: ไม่ใช้ตัวกรองเทรนด์ H4 (เข้าบ่อยกว่า) — สัญญาณของ P7 เป็นสัญญาณของ P8 ด้วย เปิดทั้งคู่อาจเข้า 2 ไม้พร้อมกัน
- SL 0.75 ATR · TP 1.5 เท่า · เลื่อน SL ทุก 5 จุด เหมือน P5 · ติ๊กเลือกใช้/ไม่ใช้ได้ในการ์ดแผนเทรด
- กราฟสดมีแท็บ P7 / P8 แสดงเส้น Bollinger H4 บนกราฟ H4

### ปรับหน้าจอ
- เอาข้อความ "XAUUSD Gold" ใต้ชื่อโปรแกรมออก (ซ้ำกับการ์ดราคาทองที่แสดงชื่อสัญลักษณ์ของโบรกเกอร์อยู่แล้ว)

### แก้ไข: แจ้งเตือน LINE OA
- Token ใช้ร่วมกันทุกโปรไฟล์ — ตั้งครั้งเดียวใช้ได้ทุกหน้าต่าง (เดิมหน้าต่างโปรไฟล์อื่นไม่เห็น Token)
- กด "ส่งข้อความทดสอบ" สำเร็จ ระบบบันทึก Token และเปิดใช้งานให้อัตโนมัติ

### ปรับปรุงแผน P5 (BB-H1-Reversion) — ตัดสัญญาณหลอก
- ไม่เข้าไม้เมื่อ H1 MA100/150/200 เรียงตัวตามทิศไม้ (หลุดขอบ Bollinger กลางเทรนด์แรงมักไม่เด้งกลับ)
- Backtest 2.5 ปี: PF 1.17 → 1.54 · ชนะ 43% → 51% · Max DD 55 → 26 จุด
- รายการเงื่อนไข P5 ในการ์ด/กราฟแสดงตรงกับกฎจริง (Divergence ปกติ/ซ่อน · H1 ไม่เรียงตามทิศ · AI ≥ 55%)

### แจ้งเตือนโควตา LINE OA
- ใช้โควตาข้อความไปถึง 90% → หน้าต่างเตือน · เต็มแล้ว → หน้าต่างเตือนพร้อมเสียง และหยุดส่งจนถึงต้นเดือนหน้า (บอทยังเทรดตามปกติ)
- Token หมดอายุ/ไม่ถูกต้อง → หน้าต่างเตือน · อัปเกรดแพ็กเกจแล้วกด "ตรวจโควตา" ส่งต่อได้ทันที

### ใหม่: แจ้งเตือนไปที่ LINE OA ของคุณเอง
- แจ้งเข้าไม้ (แผน · ฝั่ง · ราคา · SL/TP) · ปิดไม้ (กำไร/ขาดทุน · ปิดโดย · ระยะเวลาถือ) · สรุปกำไรรายวัน
- ตั้งค่าที่เมนูชื่อผู้ใช้ → "แจ้งเตือน LINE OA" — ใส่ Channel access token ของ OA ตัวเอง กดทดสอบ และตรวจโควตาได้
- Token เก็บในเครื่องเท่านั้น (เข้ารหัส) · แต่ละโปรไฟล์ตั้งค่าแยกกันได้

### ความปลอดภัย
- รหัสผ่าน MT5 ที่จำไว้ในเครื่องถูกเข้ารหัสด้วย Windows DPAPI (เดิมเก็บเป็นข้อความธรรมดา) — แปลงให้อัตโนมัติ
- ตรวจแหล่งข้อมูลเวอร์ชันสำรองให้รับเฉพาะลิงก์ดาวน์โหลดทางการ

### กราฟกำไร/ขาดทุนรายวันบนเว็บ
- ส่งข้อมูลย้อนหลัง 90 วัน · เว็บเลือกช่วง 7 / 14 / 30 (ค่าเริ่มต้น) / 90 วัน หรือกำหนดวันเอง

### ช่องทางดาวน์โหลด/อัปเดตเวอร์ชันล่าสุด
- หน้าเข้าสู่ระบบตรวจเวอร์ชันอัตโนมัติ — มีเวอร์ชันใหม่แสดงแถบพร้อมปุ่ม "อัปเดต 1-Click" และ "ดาวน์โหลด"
- ลิงก์ "ดาวน์โหลดเวอร์ชันล่าสุด" บนหน้าเข้าสู่ระบบ และในเมนูผู้ใช้
- แก้: ปุ่ม "อัปเดตเลย" บนหน้าเข้าสู่ระบบไม่เปิดหน้าต่างอัปเดต

### ปรับปรุงหน้าเข้าสู่ระบบ
- ดีไซน์ใหม่ อ่านง่าย ช่องกรอกเรียบ ลิงก์รวมแถวเดียว
- เมื่อต้องอัปเดต แสดงกล่องพร้อมปุ่ม "อัปเดตเลย (1-Click)" และ "ดาวน์โหลดจากเว็บ"

### ⚠ ต้องอัปเดตเวอร์ชันนี้ก่อนใช้งานต่อ
- ตั้งแต่เวอร์ชันนี้ ระบบตรวจเวอร์ชันโปรแกรมทุกครั้งที่เชื่อมต่อ — เวอร์ชันเก่าจะถูกออกจากระบบและเข้าสู่ระบบไม่ได้จนกว่าจะอัปเดต
- เพื่อความปลอดภัยของข้อมูลพอร์ตและประวัติการเทรดบนเว็บ
- เมื่อมีเวอร์ชันบังคับในอนาคต โปรแกรมจะหยุดบอทและเปิดหน้าต่างอัปเดต 1-Click ให้อัตโนมัติ

### จากเวอร์ชันก่อนหน้า
- เว็บแสดงสภาวะตลาด / เงื่อนไขเข้าไม้รายแผน / AI วิเคราะห์ไม้ที่ถืออยู่ · ผลการเทรดแยกตามบัญชี MT5
- "เติมชั่วโมง" · ประวัติชั่วโมงแยกสีตามบัญชี · ระดับสมาชิก Lv. · ข่าวสารและโปรโมชัน · แก้เปิดไม้เกินเพดาน

วิธีติดตั้ง: ดาวน์โหลด GoldBot24_Setup_{TAG}.exe แล้วดับเบิลคลิกติดตั้ง หรืออัปเดตผ่านปุ่ม 1-Click ในโปรแกรม"""


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
        "name": f"Gold Bot 24 {TAG}",
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
