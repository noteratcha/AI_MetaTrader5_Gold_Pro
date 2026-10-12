@echo off
chcp 65001 >nul
title GoldBot24 [Profile: FBS]
cd /d "%~dp0"
echo ========================================================
echo   Starting Gold Bot 24 - Profile [FBS]
echo ========================================================
if exist "dist\AI_Gold_Commander_Pro.exe" (
    start "" "dist\AI_Gold_Commander_Pro.exe" --profile FBS
) else (
    start "" python gui_app.py --profile FBS
)
