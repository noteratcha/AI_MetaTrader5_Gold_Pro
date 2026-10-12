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

### แสดง Magic Number บนการ์ดบัญชี MT5 (Card 1)
- แสดงป้าย Magic Number บนการ์ดบัญชี MT5 (การ์ดที่ 1) ฝั่งขวาของเลขที่บัญชี MT5 อย่างเด่นชัดและสวยงามด้วยสไตล์ Gold Pill Badge
- อัปเดต Magic Number แบบเรียลไทม์ตาม Profile ที่กำลังใช้งานอยู่ (แยกอิสระระหว่างหลายโปรไฟล์)
- สามารถคลิกที่การ์ดบัญชี MT5 เพื่อเปิดหน้าต่าง Profile & Magic Number Manager ได้ทันที

### ระบบ Profile และ Multi-Instance (รันบอทหลาย MT5 พร้อมกันในเครื่องเดียว)
- รองรับการเปิดบอทหลายตัวขนานกันบนเครื่องเดียวกัน (เช่น บัญชี FBS และบัญชี XM Global) ข้อมูลแยกขาดจากกัน 100%
- **Isolated Data Storage**: แยกโฟลเดอร์จัดเก็บข้อมูลประจำแต่ละ Profile (`%APPDATA%\\GoldBot24\\profiles\\<name>\\`) ไม่ทับเซสชั่นหรือประวัติการเทรด
- **Per-Profile MT5 Binding**: ระบุและเชื่อมต่อ MT5 Terminal เฉพาะตัว (สแกนพบ FBS MT5 และ XM Global MT5 อัตโนมัติ)
- **Independent Magic Numbers**: Magic Number แยกอิสระตามแต่ละ Profile ป้องกันการแทรกแซงหรือแย่งปิดออเดอร์ของกันและกัน
- **Single Instance Guard per Profile**: อนุญาตให้รันขนานกันคนละ Profile แต่ยังคงป้องกันการเปิดซ้ำซ้อนใน Profile เดียวกัน
- **Profile Manager GUI & Launcher**: มีปุ่มชิปและหน้าต่างจัดการ Profile สามารถสลับ Terminal, สร้าง Profile ใหม่ และกดเปิดหน้าต่างบอทตัวใหม่ (Launch Instance) ได้ในคลิกเดียว

### ตัวกรองกำจัดสัญญาณแนวรับ–แนวต้านหลอก (False S&R Signals Elimination Filter)
- เพิ่มระบบตัวกรองอัจฉริยะ 5 มิติเพื่อเอาสัญญาณแนวรับและแนวต้านหลอกออกโดยอัตโนมัติ:
  1. **Proximity Buffer Filter**: คัดกรองแนวที่อยู่ชิดราคาปัจจุบันเกินไป (< 0.15 ATR)
  2. **Clean Invalidation / Breached Levels**: ตัดแนวต้าน/แนวรับที่ถูกแท่งเทียนปิดทะลุผ่านเกิน 0.35 ATR
  3. **Exhaustion / Chop Filter**: ตัดโซนที่มีแท่งเทียนวิ่งพาดผ่านไปมาจนพรุน (used_hits >= 15 ครั้ง)
  4. **Role Purity**: กรองให้แนวรับต้องมีประวัติเป็น Swing Low และแนวต้านต้องมีประวัติเป็น Swing High ที่พิสูจน์แล้ว
  5. **Minimum Quality & Spacing**: คัดกรองโซนขยะที่คะแนนต่ำ (< 2.2 ดาว) ออก พร้อมปรับระยะห่างขั้นต่ำ `min_gap >= 1.0 ATR`

### ระบบคำนวณความแข็งแกร่งแนวรับ–แนวต้านตามหลัก SMC (SMC S&R Liquidity Mitigation Engine)
- **Fresh Zone (Untested / 1 Touch)**: โซนสดใหม่ได้คะแนนสูงสุด (Base 9.0–9.5 ดาว)
- **Tested / Retested Decay**: แนวที่ถูกราคาชนซ้ำ คะแนนจะลดหลั่นลงตามจำนวนครั้ง (Touch Decay)
- **Mitigation by Subsequent Price Action (Used Mitigation)**: ตรวจจับว่าราคาเคยแตะหรือใช้งานโซนหรือไม่ หากถูกใช้แล้วจะหักคะแนนความแข็งแกร่งลง
- **AI S&R Focus Recommendation**: ระบบ AI แนะนำระดับแนวรับแนวต้านที่สำคัญ จัดลำดับและโฟกัสแนวที่สดใหม่และแข็งแกร่งจริง

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
