@echo off
chcp 65001 >nul
title GoldBot24 Multi-Instance Launcher
cd /d "%~dp0"
echo ========================================================
echo   Gold Bot 24 Multi-Instance
echo ========================================================
echo   [1] เปิด Profile: FBS
echo   [2] เปิด Profile: XM
echo   [3] เปิดพร้อมกันทั้ง 2 ตัว (FBS + XM)
echo   [4] เปิด Profile เริ่มต้น (Default)
echo ========================================================
set /p choice="กรุณาเลือก (1-4): "

if "%choice%"=="1" (
    call "Launch_FBS.bat"
)
if "%choice%"=="2" (
    call "Launch_XM.bat"
)
if "%choice%"=="3" (
    echo กำลังเปิด Profile FBS...
    call "Launch_FBS.bat"
    timeout /t 2 >nul
    echo กำลังเปิด Profile XM...
    call "Launch_XM.bat"
)
if "%choice%"=="4" (
    if exist "dist\AI_Gold_Commander_Pro.exe" (
        start "" "dist\AI_Gold_Commander_Pro.exe"
    ) else (
        start "" python gui_app.py
    )
)
