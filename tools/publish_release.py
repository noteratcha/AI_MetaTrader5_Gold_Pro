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

### 📈 ใหม่: แสดงอินดิเคเตอร์ตามแผนที่เปิดใช้งานบนกราฟ M15 เรียลไทม์
- **อินดิเคเตอร์ไดนามิกตามแผนที่ติ๊กเปิดใช้งาน**:
  - **Plan 1 (MA M15)**: เส้น MA5 (ฟ้า), MA13 (ทอง), MA50 (ม่วง)
  - **Plan 2 (MA H1)**: เส้น H1 MA5 (เขียวมิ้นต์), H1 MA10 (เหลืองอำพัน), H1 MA20 (คราม)
  - **Plan 3 & Plan 4 (SMC / SR Bounce)**: เส้นแนวต้าน H1 (แดง), เส้นแนวรับ H1 (เขียว)
  - **Plan 5 (BB H1)**: Bollinger Bands H1 บน/กลาง/ล่าง (ม่วงอ่อน/เทา)
  - **Plan 6 (SAR H1)**: จุด Parabolic SAR H1 (ชมพู) และเส้น EMA100 H1 (ฟ้าคราม)
- **แถบ Legend ไดนามิก**: ปรับแสดงเฉพาะอินดิเคเตอร์ของแผนที่เปิดใช้งานจริงอัตโนมัติ
- **Hover Tooltip**: ชี้ที่แท่งเทียนเพื่อดูค่าตัวเลขจริงของอินดิเคเตอร์ทุกแผนที่เปิดใช้งานแบบ Real-time

### 💰 ปรับปรุง: กำหนดหลักประกัน 100 USD ต่อไม้
- ปรับสูตรหลักประกันต่อไม้เป็น 100 USD ต่อ 1 ไม้ (ที่ Lot 0.01)
- รองรับการกระจายไม้และเปิดออเดอร์ตามแผนได้อย่างยืดหยุ่นภายใต้การคุมความเสี่ยง

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
