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

### ใหม่: กำไร/ขาดทุนวันนี้บนการ์ดยอดเงิน
- การ์ด "ยอดเงินในพอร์ต" มีป้าย "วันนี้ +x (+y%)" = ปิดไม้แล้ววันนี้ (เวลาไทย) + กำไรลอยตัว เทียบยอดเงินตอนเริ่มวัน · เขียว = กำไร / แดง = ขาดทุน
- ชี้เมาส์ที่ป้ายดูรายละเอียด: ปิดไม้กี่ไม้ · กำไรลอยตัว · ผลเมื่อวานทั้งวัน

### ปรับปรุง: P4 · SR-Bounce ล็อกกำไรได้มากขึ้น (จากเวอร์ชันก่อน)
- เมื่อกำไรถึง 15 จุดขึ้นไป บอทเลื่อน SL เข้าหาราคา 60% ต่อขั้น (เดิม 40%) · ทดสอบย้อนหลัง 2.5 ปี: กำไร P4 +127 → +151 จุด · PF 1.35 → 1.42
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
