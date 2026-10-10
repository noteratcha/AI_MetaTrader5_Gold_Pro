# ==============================================================================
# in_place_updater.py — ระบบอัปเดตแพตช์ทับ Path เดิมอัตโนมัติ (1-Click In-App Updater)
# AI Gold Commander Pro (GoldBot24)
# ==============================================================================

import os
import sys
import time
import tempfile
import subprocess
import urllib.request
import threading
from typing import Callable, Optional


def download_file_with_progress(
    url: str,
    dest_path: str,
    progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> bool:
    """
    ดาวน์โหลดไฟล์พร้อมรายงานความคืบหน้า:
    progress_callback(downloaded_bytes, total_bytes, percent_float, speed_mb_s)
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "GoldBot24-AutoUpdater"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            total = int(resp.headers.get("content-length", 0) or 0)
            downloaded = 0
            start_t = time.time()
            chunk_size = 128 * 1024  # 128 KB
            
            with open(dest_path, "wb") as f:
                while True:
                    if cancel_event and cancel_event.is_set():
                        return False
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    elapsed = max(0.1, time.time() - start_t)
                    speed = (downloaded / (1024 * 1024)) / elapsed
                    pct = (downloaded / total * 100.0) if total > 0 else 0.0
                    if progress_callback:
                        progress_callback(downloaded, total, pct, speed)
            return True
    except Exception as e:
        print(f"[UPDATER ERROR] ดาวน์โหลดล้มเหลว: {e}")
        return False


def launch_in_place_patch(patch_file: str, is_installer: bool = True) -> tuple[bool, str]:
    """
    เรียกใช้ตัวติดตั้งหรือแพตช์ทับ Path เดิม และเริ่มโปรแกรมใหม่:
    1. ตรวจหาตำแหน่ง executable และ working directory ที่ถูกต้อง
    2. สร้าง Batch updater script ในโฟลเดอร์ Temp
    3. รอให้กระบวนการเดิมปิดตัวลงอย่างสมบูรณ์ (loop ตรวจ tasklist + taskkill ป้องกันค้าง)
    4. รันตัวติดตั้งทับ Path เดิมแบบ Silent (/SP- /SILENT /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="...")
    5. สลับ Working Directory ไปที่โฟลเดอร์โปรแกรม และรันโปรแกรมใหม่ขึ้นมาทันที (start /d + fallback PowerShell)
    6. รันสคริปต์แบบ Background Process และปิดโปรแกรมเดิม
    """
    try:
        current_exe = os.path.abspath(sys.executable)
        current_dir = os.path.dirname(current_exe)
        installed_exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\GoldBot24\AI_Gold_Commander_Pro.exe")
        installed_dir = os.path.dirname(installed_exe)

        is_frozen = getattr(sys, "frozen", False)
        if is_frozen and os.path.basename(current_exe).lower() == "ai_gold_commander_pro.exe":
            target_exe = current_exe
            target_dir = current_dir
        else:
            target_exe = installed_exe
            target_dir = installed_dir

        bat_fd, bat_path = tempfile.mkstemp(suffix="_goldbot_patch.bat")
        os.close(bat_fd)

        if is_installer:
            bat_content = f"""@echo off
chcp 65001 > nul
echo [GoldBot24 Updater] รอให้โปรแกรมเดิมปิดการทำงาน...
ping 127.0.0.1 -n 3 > nul

set wait_count=0
:wait_closed
tasklist /fi "imagename eq AI_Gold_Commander_Pro.exe" 2>nul | find /i "AI_Gold_Commander_Pro.exe" > nul
if not errorlevel 1 (
    set /a wait_count+=1
    if %wait_count% geq 8 (
        taskkill /f /im "AI_Gold_Commander_Pro.exe" > nul 2>&1
        goto do_install
    )
    ping 127.0.0.1 -n 2 > nul
    goto wait_closed
)
:do_install

echo [GoldBot24 Updater] กำลังติดตั้งแพตช์อัปเดตเวอร์ชันใหม่ทับ Path เดิม...
start /wait "" "{patch_file}" /SP- /SILENT /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="{target_dir}"

echo [GoldBot24 Updater] รอให้ไฟล์ถูกเขียนเสร็จสิ้น...
ping 127.0.0.1 -n 3 > nul

echo [GoldBot24 Updater] กำลังเปิดโปรแกรมเวอร์ชันใหม่...
set "APP_EXE={target_exe}"
set "APP_DIR={target_dir}"
if not exist "%APP_EXE%" (
    set "APP_EXE={installed_exe}"
    set "APP_DIR={installed_dir}"
)
if not exist "%APP_EXE%" (
    set "APP_EXE={current_exe}"
    set "APP_DIR={current_dir}"
)

cd /d "%APP_DIR%"
start "" /d "%APP_DIR%" "%APP_EXE%"

ping 127.0.0.1 -n 3 > nul
tasklist /fi "imagename eq AI_Gold_Commander_Pro.exe" 2>nul | find /i "AI_Gold_Commander_Pro.exe" > nul
if errorlevel 1 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%APP_EXE%' -WorkingDirectory '%APP_DIR%'"
)

ping 127.0.0.1 -n 3 > nul
del /f /q "{patch_file}" > nul 2>&1
del /f /q "%~f0" > nul 2>&1
exit
"""
        else:
            staging_dir = tempfile.mkdtemp(prefix="goldbot_zip_")
            bat_content = f"""@echo off
chcp 65001 > nul
echo [GoldBot24 Updater] รอให้โปรแกรมเดิมปิดการทำงาน...
ping 127.0.0.1 -n 3 > nul

set wait_count=0
:wait_closed_zip
tasklist /fi "imagename eq AI_Gold_Commander_Pro.exe" 2>nul | find /i "AI_Gold_Commander_Pro.exe" > nul
if not errorlevel 1 (
    set /a wait_count+=1
    if %wait_count% geq 8 (
        taskkill /f /im "AI_Gold_Commander_Pro.exe" > nul 2>&1
        goto do_extract
    )
    ping 127.0.0.1 -n 2 > nul
    goto wait_closed_zip
)
:do_extract

echo [GoldBot24 Updater] กำลังแตกไฟล์แพตช์...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '{patch_file}' -DestinationPath '{staging_dir}' -Force"

echo [GoldBot24 Updater] กำลังคัดลอกไฟล์แพตช์ทับ...
if exist "{staging_dir}\\AI_Gold_Commander_Pro" (
    robocopy "{staging_dir}\\AI_Gold_Commander_Pro" "{target_dir}" /E /IS /IT /NP /R:2 /W:1 > nul
) else (
    robocopy "{staging_dir}" "{target_dir}" /E /IS /IT /NP /R:2 /W:1 > nul
)

ping 127.0.0.1 -n 2 > nul

echo [GoldBot24 Updater] กำลังเปิดโปรแกรมเวอร์ชันใหม่...
set "APP_EXE={target_exe}"
set "APP_DIR={target_dir}"
if not exist "%APP_EXE%" (
    set "APP_EXE={installed_exe}"
    set "APP_DIR={installed_dir}"
)

cd /d "%APP_DIR%"
start "" /d "%APP_DIR%" "%APP_EXE%"

ping 127.0.0.1 -n 3 > nul
tasklist /fi "imagename eq AI_Gold_Commander_Pro.exe" 2>nul | find /i "AI_Gold_Commander_Pro.exe" > nul
if errorlevel 1 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%APP_EXE%' -WorkingDirectory '%APP_DIR%'"
)

ping 127.0.0.1 -n 3 > nul
rd /s /q "{staging_dir}" > nul 2>&1
del /f /q "{patch_file}" > nul 2>&1
del /f /q "%~f0" > nul 2>&1
exit
"""

        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=CREATE_NO_WINDOW,
            close_fds=True
        )

        time.sleep(0.5)
        return True, "กำลังเริ่มขั้นตอนอัปเดตและรีสตาร์ทโปรแกรม..."
    except Exception as e:
        return False, f"ไม่สามารถเริ่มการอัปเดตได้: {e}"

