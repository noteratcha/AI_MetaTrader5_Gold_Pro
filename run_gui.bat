@echo off
chcp 65001 > nul
title Gold Bot 24 Launcher v2026.1003.0025
cd /d "%~dp0"
echo ============================================================
echo  Starting Gold Bot 24 Desktop GUI...
echo ============================================================
python gui_app.py
if errorlevel 1 (
    echo.
    echo [ERROR] Application closed with an error.
    pause
)
