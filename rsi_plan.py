"""
Plan 10: RSI-H1-Trend — Oversold / Overbought ตามเทรนด์ MA200 H1 (ผู้ใช้เลือก 13 ต.ค. 2026)
- BUY:  แท่ง H1 ที่ปิดแล้ว ราคาปิดอยู่เหนือ MA200 และ RSI(14) เพิ่งลงต่ำกว่า 30 (แท่งก่อนหน้ายัง ≥ 30)
- SELL: ราคาปิดอยู่ใต้ MA200 และ RSI(14) เพิ่งขึ้นเกิน 70 (แท่งก่อนหน้ายัง ≤ 70)
- SL 2 ATR(14) H1 · TP 3 ATR · ถือไม่เกิน 48 ชม. (ครบแล้วปิด) · ไม่เลื่อน SL · ไม่ใช้ AI
- 1 ไม้ต่อ 1 สัญญาณ (แท่ง H1 ที่เกิดสัญญาณ)
Backtest H1 2.7 ปี: FBS 49 ไม้ · ชนะ 57% · +848 จุด · PF 2.53 · DD 118 · XM +849 · PF 2.52 · DD 120
(⚠ กำไรส่วนใหญ่มาจากปี 2026 — 2024: −33 · 2025: +32 · 2026: +438)
ใช้ร่วมกัน: multi_asset_ai_bot (เข้า/ออก) · รายการเงื่อนไข · tools/backtest_all.py
"""
import numpy as np
import pandas as pd

NAME = "RSI-H1-Trend"
LABEL = "P10 · RSI H1"
RSI_N = 14
OVERSOLD = 30.0
OVERBOUGHT = 70.0
TREND_MA = 200
SL_ATR = 2.0
TP_ATR = 3.0
HOLD_HOURS = 48


def indicators(df_h1: pd.DataFrame):
    """RSI(14) แบบ Wilder · MA200 · ATR(14) (ค่าเฉลี่ยธรรมดาของ True Range) — สูตรเดียวกับ Backtest"""
    c = df_h1["close"].astype(float)
    h, l = df_h1["high"].astype(float), df_h1["low"].astype(float)
    dl = c.diff()
    g = dl.clip(lower=0).ewm(alpha=1 / RSI_N, adjust=False).mean()
    ls = (-dl.clip(upper=0)).ewm(alpha=1 / RSI_N, adjust=False).mean()
    rsi = (100 - 100 / (1 + g / (ls + 1e-9))).values
    ma = c.rolling(TREND_MA).mean().values
    pc = np.r_[c.values[0], c.values[:-1]]
    tr = np.maximum(h.values - l.values, np.maximum(np.abs(h.values - pc), np.abs(l.values - pc)))
    atr = pd.Series(tr).rolling(14).mean().values
    return rsi, ma, atr


def signal_at(rsi, ma, close, k: int) -> int:
    """สัญญาณ ณ แท่งที่ปิด k: +1 BUY · -1 SELL · 0 ไม่มี"""
    if k < 1 or np.isnan(ma[k]) or np.isnan(rsi[k - 1]):
        return 0
    up = close[k] > ma[k]
    if up and rsi[k] < OVERSOLD <= rsi[k - 1]:
        return 1
    if not up and rsi[k] > OVERBOUGHT >= rsi[k - 1]:
        return -1
    return 0


def sl_tp(side: int, price: float, atr_k: float):
    return price - side * SL_ATR * atr_k, price + side * TP_ATR * atr_k
