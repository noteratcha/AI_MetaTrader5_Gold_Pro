"""
👑 AI MetaTrader 5 Gold Pro - Automated Binary Compiler (Nuitka / PyInstaller)
เวอร์ชัน: ดู version.py
สคริปต์คอมไพล์โค้ดเป็น Machine Code ไบนารีเพื่อป้องกันการ Reverse Engineering และป้องกันการแกะสูตรเทรด AI
พร้อมสร้างแพ็กเกจ .ZIP สำหรับแจกจ่ายลูกค้าใช้งานเชิงพาณิชย์
"""

import os
import sys
import subprocess
import shutil
import zipfile

# ตั้งค่า stdout/stderr เป็น UTF-8 ป้องกันปัญหารหัส CP874 บน Windows
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build_tmp")
APP_NAME = "AI_Gold_Commander_Pro"
from version import APP_VERSION  # noqa: E402
VERSION_STR = f"v{APP_VERSION}"

def check_compiler():
    """ตรวจสอบเครื่องมือคอมไพล์ในเครื่อง"""
    has_nuitka = shutil.which("nuitka") is not None
    has_pyinstaller = shutil.which("pyinstaller") is not None
    return has_nuitka, has_pyinstaller

def create_quickstart_guide(out_dir):
    """สร้างคู่มือเริ่มต้นใช้งานฉบับย่อใส่ในโฟลเดอร์สำหรับผู้ใช้"""
    guide_text = f"""=======================================================
👑 AI Gold Commander Pro (GoldBot24) {VERSION_STR}
คู่มือเริ่มต้นใช้งานฉบับย่อ (Quick Start Guide)
=======================================================

1. การเปิดใช้งาน:
   - ดับเบิ้ลคลิกที่ไฟล์ AI_Gold_Commander_Pro.exe เพื่อเปิดหน้าต่างควบคุม

2. สิทธิ์การใช้งาน (Trial & Product Key):
   - สมาชิกใหม่ที่เข้าสู่ระบบครั้งแรก รับฟรีทันที 48.00 ชั่วโมง!
   - เมื่อชั่วโมงหมด สามารถซื้อ Product Key ได้ที่ร้านค้า GoldBot24:
     https://goldbot24.vercel.app/store (รองรับสแกนสลิปผ่าน SlipOK และ PromptPay)
   - นำ Product Key (รูปแบบ: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX) 
     มากดปุ่ม "เติมชั่วโมง" ในโปรแกรมเพื่อบวกเพิ่มชั่วโมงทันที

3. แผนการเทรด 100% Pure Gold Specialist (XAUUSD):
   - Plan 0: SMC-LiquidityHunt (กวาดสภาพคล่องแนวรับ/ต้าน H1 + เทรนด์ H1)
   - Plan 1: SR-SwingBounce (เด้งโซนแนวรับ/ต้าน H1 + RSI Divergence)
   - Plan 3: BB-H1-Reversion (เด้งขอบแบนด์ H1 2STD + MACD Confluence)
   - Plan 4: MA-Cross-Trend (MA5 x MA10 M15 + ตัวกรองเทรนด์ใหญ่ H1)
   - Plan 5: MA-Cross-H1-Trend (MA5 x MA10 H1 + ตัวกรองเทรนด์ใหญ่ H4)

4. คำแนะนำความปลอดภัย:
   - ตรวจสอบให้แน่ใจว่าได้เปิดโปรแกรม MetaTrader 5 และล็อกอินบัญชี FBS เรียบร้อยแล้ว
   - เปิดใช้งานปุ่ม "Algo Trading" บน MT5 ให้เป็นสีเขียว
=======================================================
"""
    guide_path = os.path.join(out_dir, "QUICK_START_GUIDE.txt")
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(guide_text)

def package_zip(source_dir, output_zip):
    """บีบอัดโฟลเดอร์ผลลัพธ์เป็นไฟล์ ZIP สำหรับส่งมอบ"""
    print(f"\n📦 กำลังสร้างไฟล์ ZIP สำหรับแจกจ่าย: {output_zip}...")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, os.path.dirname(source_dir))
                zipf.write(abs_path, rel_path)
    zip_size_mb = os.path.getsize(output_zip) / (1024 * 1024)
    print(f"🎉 สร้างแพ็กเกจ ZIP สำเร็จ! ขนาด: {zip_size_mb:.2f} MB")

def build_gui_app(mode="pyinstaller"):
    """คอมไพล์หน้าต่าง Desktop GUI (gui_app.py)"""
    print(f"\n🚀 เริ่มต้นคอมไพล์ Desktop GUI ในโหมด: {mode.upper()}...")
    
    output_app_dir = os.path.join(DIST_DIR, APP_NAME)

    if mode == "nuitka":
        cmd = [
            sys.executable, "-m", "nuitka",
            "--standalone",
            "--windows-disable-console",
            f"--output-dir={DIST_DIR}",
            "--remove-output",
            "--enable-plugin=tk-inter",
            "--include-data-dir=sounds=sounds",
            "gui_app.py"
        ]
    else:
        # กำหนดคำสั่ง PyInstaller พร้อมเก็บ customtkinter และ darkdetect ครบถ้วน
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--onedir",
            "--windowed",
            f"--distpath={DIST_DIR}",
            f"--workpath={BUILD_DIR}",
            "--icon=assets/app_icon.ico",
            "--add-data=sounds;sounds",
            "--add-data=assets;assets",
            "--collect-all=customtkinter",
            "--collect-all=darkdetect",
            "--hidden-import=MetaTrader5",
            "--hidden-import=sklearn",
            "--hidden-import=scipy",
            "--hidden-import=pandas",
            "--hidden-import=numpy",
            "--hidden-import=colorama",
            "--hidden-import=license_manager",
            "--hidden-import=stats_manager",
            "--hidden-import=sound_manager",
            "--hidden-import=bot_controller",
            "--hidden-import=supabase_sync",
            "--hidden-import=multi_asset_ai_bot",
            f"--name={APP_NAME}",
            "gui_app.py"
        ]

    print(f"รันคำสั่ง: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode == 0:
        print(f"\n✅ คอมไพล์สำเร็จ! ไฟล์ผลลัพธ์อยู่ที่: {output_app_dir}")
        
        # คัดลอกโฟลเดอร์เสียง sounds ไปวางใน output folder ให้ชัวร์ 100%
        target_sounds = os.path.join(output_app_dir, "sounds")
        if os.path.exists(os.path.join(PROJECT_ROOT, "sounds")) and not os.path.exists(target_sounds):
            shutil.copytree(os.path.join(PROJECT_ROOT, "sounds"), target_sounds)
            print("🔊 คัดลอกโฟลเดอร์เสียง sounds ไปยังไดเรกทอรีปลายทางเรียบร้อย")

        # สร้าง Quick Start Guide
        create_quickstart_guide(output_app_dir)
        print("📄 สร้าง QUICK_START_GUIDE.txt เรียบร้อย")

        # สร้างไฟล์ ZIP สำหรับแจกจ่าย
        zip_output = os.path.join(DIST_DIR, f"{APP_NAME}_{VERSION_STR}.zip")
        package_zip(output_app_dir, zip_output)
        
        print(f"\n🏆 การคอมไพล์และสร้างแพ็กเกจเสร็จสมบูรณ์ 100%!")
        print(f"• Executable: {os.path.join(output_app_dir, f'{APP_NAME}.exe')}")
        print(f"• Distribution ZIP: {zip_output}")
    else:
        print(f"❌ เกิดข้อผิดพลาดในการคอมไพล์ (Code: {result.returncode})")

if __name__ == "__main__":
    has_nuitka, has_pyinstaller = check_compiler()
    print("==================================================")
    print(f"👑 AI MetaTrader 5 Gold Pro - Binary Build Tool ({VERSION_STR})")
    print(f"• สถานะ Nuitka: {'พร้อมใช้งาน ✅' if has_nuitka else 'ยังไม่ได้ติดตั้ง ⚠️'}")
    print(f"• สถานะ PyInstaller: {'พร้อมใช้งาน ✅' if has_pyinstaller else 'ยังไม่ได้ติดตั้ง ⚠️'}")
    print("==================================================")

    chosen_mode = "pyinstaller" if has_pyinstaller else ("nuitka" if has_nuitka else None)
    if not chosen_mode:
        print("\n💡 แนะนำให้ติดตั้งคอมไพเลอร์ก่อนด้วยคำสั่ง:")
        print("   pip install pyinstaller")
    else:
        build_gui_app(mode=chosen_mode)
