@echo off
chcp 65001 > nul
title AI Gold Commander Pro Launcher (GoldBot24) v2026.1003.0025
cd /d "%~dp0"
echo ============================================================
echo  Starting AI Gold Commander Pro (GoldBot24) Desktop GUI...
echo ============================================================
python gui_app.py
if errorlevel 1 (
    echo.
    echo [ERROR] Application closed with an error.
    pause
)
