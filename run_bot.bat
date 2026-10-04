@echo off
chcp 65001 > nul
title AI MetaTrader 5 (FBS) Auto-Trade Bot
cd /d "%~dp0"
echo ============================================================
echo  Starting AI MetaTrader 5 Auto-Trade Bot...
echo ============================================================
python -u multi_asset_ai_bot.py
pause
