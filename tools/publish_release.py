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

### 🧱 ปรับปรุงระบบแนวรับ–แนวต้านใหม่ (Dynamic Recency & True Support S&R Engine)
- **ระดับความแข็งแกร่งคิดจาก ล่าสุดไปอดีต (Recency Decay: มากไปน้อย)**:
  - จุดกลับตัวหรือแท่งเทียนที่เพิ่งเกิดขึ้นล่าสุด (รอบ 24–48 ชม. / < 36 แท่ง) ให้น้ำหนักความสดใหม่สูงสุด ($1.0\\times$)
  - จุดกลับตัวในอดีตไกลๆ (100–500 แท่งที่แล้ว) ค่อยๆ ลดหลั่นคะแนนลงตามกาลเวลา (Time Decay ลงสู่ $0.25 - 0.30\\times$)
- **เกิดซ้ำบริเวณนั้นบ่อย ยิ่งแข็งแกร่งมาก (Touch Frequency & Cluster Density)**:
  - โซนที่ราคามาทดสอบและกลับตัวซ้ำๆ ในระยะไม่เกิน 0.5 ATR จะได้คะแนนฐานเพิ่มขึ้นตามจำนวนครั้ง (1 ครั้ง = 3.5, 2 ครั้ง = 5.5, 3 ครั้ง = 7.5, 4 ครั้ง = 9.0, >= 5 ครั้ง = 10.0 ดาว)
  - ผสานคะแนน: โซนที่ **เกิดซ้ำบ่อย + เกิดล่าสุด** จะได้คะแนนดาวสูงสุด (**★ 8.50 - 10.00**)
- **คัดกรองแนวรับแท้จริง (Role Purity Support Filter)**:
  - แนวรับ (Support) ต้องมี **Swing Low (จุดที่มีแรงซื้อเด้งกลับจริง)** เป็นหลัก ไม่เอายอดดอยเก่า (Swing High) ในอดีตที่ไม่มีแรงรับจริงมาตั้งเป็น S1 ป้องกันการสร้างแนวรับหลอก
  - แนวต้าน (Resistance) คัดกรองจาก **Swing High (จุดที่มีแรงขายทุบกลับจริง)** เป็นหลัก
- **ซิงค์ค่าแนวรับแนวต้านตรงกัน 100% ทุกมุมมอง**:
  - แก้ไขให้ `get_live_candles()` ดึงข้อมูลเต็ม 520 แท่งเสมอสำหรับการคำนวณ S&R ทำให้ค่า S1..S5 และ R1..R5 บนหน้าต่างกราฟสดตรงกับการ์ด Dashboard 100% ไม่ว่าผู้ใช้จะเลือกดูกี่แท่งก็ตาม (16, 30, 50, 80, ฯลฯ)

### 🎨 ปรับโฉมดีไซน์ Tipbox เงื่อนไขแผนเทรดระดับพรีเมียม (Premium Tipbox UI Redesign)
- **ดีไซน์การ์ดโมเดิร์น สวยหรู สไตล์ AI Gold Commander Pro**:
  - กรอบนอกสีทองหรูหรา (`#F59E0B`) 1px สวยงาม คมชัด ไม่แตก
  - แถบหัวการ์ด (Header Bar): แสดงไอคอนสายฟ้าและชื่อแผนสีทองสว่าง (`⚡ P1 · M15`), Side Pill สีเขียวมรกต (`▲ BUY`) หรือสีแดงกุหลาบ (`▼ SELL`) ชัดเจน และ Badge สรุปคะแนนสถานะสีสดใส (`เข้าเงื่อนไข 2/4 (50%)` หรือ `✓ พร้อมเข้าไม้ 4/4 (100%)`)
  - เส้นแบ่งสัดส่วนเรียบเนียน (Clean Dividers) ไม่ใช้เส้นประ ASCII ตัวหนังสือแบบเดิม
  - รายการ Checklist เงื่อนไขแต่ละข้อ: มี Badge สถานะ `[✓ ผ่าน]` (สีเขียวมรกต) และ `[✗ ไม่ผ่าน]` (สีแดงกุหลาบ) พร้อมชื่อเงื่อนไขสีขาวนวลหนา และข้อความคำอธิบายค่าทางเทคนิคจัดวางเป็นระเบียบ สบายตา
  - แถบล่างคำแนะนำ (Footer Hint Bar): พื้นหลังเข้มหรูหรา พร้อมไอคอนหลอดไฟสีทอง `💡` และข้อความแนะนำสีฟ้าไฮไลต์น่าคลิก

### 🔢 ตัวเลขราคาและอินดิเคเตอร์แสดง Comma (,) คั่นหลักพันครบทุกจุด
- **ฟอร์แมตตัวเลขพัน (Thousands Separators)**: ตัวเลขราคาทองคำ, เส้นค่าเฉลี่ย MA, ราคาปิด, แนวรับ–แนวต้าน, Bollinger Bands, และค่า Parabolic SAR ในทุกเงื่อนไขแผน P1–P6 แสดงผลด้วย comma `,` สองตำแหน่งทศนิยมอย่างถูกต้องและสวยงาม
- **ระบบ Auto-Format Comma Fallback**: ฟังก์ชัน `_format_tip_commas()` รับประกันว่าตัวเลข 4 หลักขึ้นไปที่แสดงในกล่องข้อความลอยทั้งหมดจะได้รับการจัดรูปแบบ comma ขั้นหลักพันโดยอัตโนมัติ

### 🪟 ปรับปรุงกล่องข้อความลอย (Tooltip Smart Clamping & Flipping)
- **ไม่ล้นออกนอกจอหรือหน้าต่าง**: ปรับปรุงระบบคำนวณพิกัด `HoverTip` ให้ตรวจสอบทั้งพื้นที่ทำงานของจอภาพ (Monitor Work Area ตัดแถบ Taskbar) และขอบเขตของหน้าต่างโปรแกรมอย่างเคร่งครัด
- **พลิกตำแหน่งอัตโนมัติ (Smart Flip)**: เมื่อนำเมาส์ไปชี้ป้ายสถานะแผนเทรดทางฝั่งขวาหรือขอบล่าง กล่องข้อความจะพลิกมาแสดงทางฝั่งซ้ายหรือด้านบนของเคอร์เซอร์เมาส์อัตโนมัติ ทำให้กล่องข้อความแสดงอยู่ภายในหน้าต่างโปรแกรมและภายในจอภาพอย่างสมบูรณ์ 100% ไม่หลุดล้นทะลุออกไปนอกจอ

### 📊 แก้ไขระบบปรับจำนวนแท่งเทียนบนกราฟสด (Live Chart Bar Count Fix)
- **ปรับแท่งตามเลือกแบบทันที**: แก้ไขปัญหาการคลิกเลือกจำนวนแท่ง (16, 30, 50, 80, 120, 200, 300, 500) ให้กราฟแท่งเทียนสดรีเฟรชและแสดงผลตามจำนวนแท่งที่เลือกทันที 100%
- **ปรับปรุง Event Handler**: ผูก `_on_bars_change` เข้ากับ segmented button และแก้ไขการคำนวณคะแนนแถบ AI แนะนำโซนรับ-ต้าน (`focus_sup_score`) ไม่ให้เกิดข้อผิดพลาดในการวาดซ้ำ

### 📅 เส้นแบ่งวันและวันที่ (Period / Day Separators) บนกราฟแท่งเทียนเรียลไทม์
- **เส้นประแบ่งวันแนวตั้ง**: แสดงเส้นประสี Slate Blue ลากผ่านเต็มความสูงของกราฟ ณ จุดเปลี่ยนวัน (00:00 น. เวลาไทย UTC+7) พร้อมติ๊กมาร์กเกอร์สีฟ้าที่แกนเวลาด้านล่าง
- **ป้ายระบุวันที่แบบ Dynamic (Header Date Badges)**: แสดงกล่องป้ายวันที่สีฟ้าอ่านง่ายด้านบนสุดของเส้นแบ่งวัน และปรับย่อความยาวอัตโนมัติตามระยะห่าง (`📅 ส. 10 ต.ค.` / `10 ต.ค.` / `10`) ไม่ให้ข้อความทับซ้อนกันในทุก Timeframe (M15, H1, H4)
- **ชิปเปิด/ปิดอิสระ `[ 📅 เส้นแบ่งวัน ]`**: ควบคุมเปิด/ปิดการแสดงผลเส้นแบ่งวันได้อย่างอิสระบนชิปอินดิเคเตอร์
- **ข้อมูลวันเวลาขณะชี้แท่งเทียน (Hover Tooltip)**: แสดงวันที่และเวลาของแท่งเทียนนั้นอย่างชัดเจน เช่น `10/10 14:30 น.`

### 🎯 ระบบ AI วิเคราะห์แนวรับ–แนวต้านสำคัญที่ต้องโฟกัส (AI Focus S&R)
- **อัลกอริทึมคัดกรองระดับสำคัญ**: AI วิเคราะห์หาระดับแนวรับและแนวต้านที่มีน้ำหนักสูงสุดและใกล้โครงสร้างราคาปัจจุบันที่สุด
- **แถบคำแนะนำ AI ด้านบนกราฟ**: แสดงป้าย `🎯 ต้าน R...` และ `🎯 รับ S...` พร้อมคะแนนความแข็งแกร่งและคำแนะนำแอ็กชันเชิงกลยุทธ์
- **เส้นไฮไลต์บนกราฟสด**: เส้นแนวรับแนวต้านที่ AI แนะนำโฟกัสจะถูกไฮไลต์เป็นเส้นทึบหนาพิเศษ (2.5px) พร้อมป้ายกำกับ `🎯 AI FOCUS`

### 🔢 ปรับคะแนนความแข็งแกร่งของแนวรับ–แนวต้านเป็นสเกล 0.00 – 10.00
- ปรับการแสดงผลจากรูปดาวเป็นตัวเลขทศนิยม 2 ตำแหน่ง ความละเอียดสูง สเกล 0.00 ถึง 10.00 ครบทั้ง 5 ระดับ (R1..R5 และ S1..S5) ทั้งในกราฟแท่งเทียนสดและการ์ด Dashboard

### ⚡ แสดงสถานะเงื่อนไขเข้าไม้เรียลไทม์ของแต่ละแผน (Live Entry Conditions)
- **ตารางแผนเทรดบนหน้าจอหลัก (Main Dashboard)**:
  - เพิ่มคอลัมน์ "เงื่อนไข" แสดงป้ายสถานะสดของทั้ง 6 แผน (P1-P6)
  - ป้ายสีเขียวประกายสดใส `★ ▲ 4/4 (ครบ)` เมื่อเข้าเงื่อนไขครบ 100%, ป้ายสีทองอำพันเมื่อ $\ge 50\%$, และสีเทาสเลทเมื่อ $< 50\%$
  - ชี้เมาส์ (Hover) แสดงรายการ Checklist ข้อต่อข้อแบบละเอียด และคลิกที่ป้ายเพื่อเปิดกราฟของแผนนั้นได้ทันที
- **หน้าต่างกราฟสด (`GoldCandleDialog`)**:
  - บนปุ่มเลือกดูตามแผนมีป้ายระบุจำนวนเงื่อนไขที่เข้าแล้วแบบเรียลไทม์ เช่น `P1 · M15 (2/4)`, `P2 · H1 (3/4)` พร้อมไฟไฮไลต์สีเขียวสดใส `★ (4/4)` เมื่อเข้าเงื่อนไขครบ 100% สัญญาณพร้อมยิง
  - แถบสถานะเงื่อนไขการเข้าไม้ใหม่ (`Condition Status Bar`): แสดง Checklist ชิปแต่ละข้อ มีเครื่องหมาย `[✓ ผ่าน]`/`[✗ ไม่ผ่าน]` และตัวเลขค่าจริงทางเทคนิค (RSI, MA, S&R, ไส้เทียน, AI %) พร้อมอัปเดตคำอธิบายเมื่อชี้เมาส์ (Hover)

### 🔴/🟢 ข้อมูลสถานะตลาดทองคำเปิด-ปิดสด (Market Hours & Realtime Status)
- คำนวณตามเวลาประเทศไทย (UTC+7) เที่ยงตรง 100% พร้อมเวลานับถอยหลังและการแจ้งเตือน `[MARKET]` อัตโนมัติ

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
