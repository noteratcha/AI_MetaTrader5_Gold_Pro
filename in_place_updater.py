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
    1. สร้าง Batch updater script ในโฟลเดอร์ Temp
    2. รันสคริปต์แบบ Detached Background Process
    3. ปิดโปรแกรมปัจจุบัน (os._exit(0))
    """
    try:
        current_exe = os.path.abspath(sys.executable)
        current_dir = os.path.dirname(current_exe)
        is_frozen = getattr(sys, "frozen", False)
        
        target_exe_to_restart = current_exe
        if not is_frozen:
            installed_exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\GoldBot24\AI_Gold_Commander_Pro.exe")
            if os.path.exists(installed_exe):
                target_exe_to_restart = installed_exe
            else:
                target_exe_to_restart = current_exe

        bat_fd, bat_path = tempfile.mkstemp(suffix="_goldbot_patch.bat")
        os.close(bat_fd)

        if is_installer:
            # ใช้ Inno Setup installer รันแบบเงียบกริบ (Silent In-Place Update)
            bat_content = f"""@echo off
chcp 65001 > nul
echo [GoldBot24 Updater] รอให้โปรแกรมเดิมปิดการทำงาน...
timeout /t 2 /nobreak > nul

echo [GoldBot24 Updater] กำลังติดตั้งแพตช์อัปเดตเวอร์ชันใหม่ทับ Path เดิม...
start /wait "" "{patch_file}" /SILENT /VERYSILENT /SUPPRESSMSGBOXES /NORESTART

echo [GoldBot24 Updater] กำลังเปิดโปรแกรมเวอร์ชันใหม่...
start "" "{target_exe_to_restart}"

timeout /t 2 /nobreak > nul
del /f /q "{patch_file}" > nul 2>&1
del /f /q "%~f0" > nul 2>&1
exit
"""
        else:
            # ถ้าเป็น ZIP: แตกไฟล์และ copy ทับ
            staging_dir = tempfile.mkdtemp(prefix="goldbot_zip_")
            bat_content = f"""@echo off
chcp 65001 > nul
echo [GoldBot24 Updater] รอให้โปรแกรมเดิมปิดการทำงาน...
timeout /t 2 /nobreak > nul

echo [GoldBot24 Updater] กำลังแตกไฟล์แพตช์...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '{patch_file}' -DestinationPath '{staging_dir}' -Force"

echo [GoldBot24 Updater] กำลังคัดลอกไฟล์แพตช์ทับ...
if exist "{staging_dir}\\AI_Gold_Commander_Pro" (
    robocopy "{staging_dir}\\AI_Gold_Commander_Pro" "{current_dir}" /E /IS /IT /NP /R:2 /W:1 > nul
) else (
    robocopy "{staging_dir}" "{current_dir}" /E /IS /IT /NP /R:2 /W:1 > nul
)

echo [GoldBot24 Updater] กำลังเปิดโปรแกรมเวอร์ชันใหม่...
start "" "{target_exe_to_restart}"

timeout /t 2 /nobreak > nul
rd /s /q "{staging_dir}" > nul 2>&1
del /f /q "{patch_file}" > nul 2>&1
del /f /q "%~f0" > nul 2>&1
exit
"""

        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        flags = DETACHED_PROCESS | CREATE_NO_WINDOW
        
        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=flags,
            close_fds=True
        )

        return True, "กำลังเริ่มขั้นตอนอัปเดตและรีสตาร์ทโปรแกรม..."
    except Exception as e:
        return False, f"ไม่สามารถเริ่มการอัปเดตได้: {e}"
