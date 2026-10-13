"""
Plan 9: Fib-H1-Counter — Fibonacci ย่อสวนเทรนด์ใหญ่ H1 (ผู้ใช้กำหนดระดับ 13 ต.ค. 2026)
- คลื่น = swing H1 (fractal 3 แท่งซ้าย-ขวา · ยืนยันเมื่อผ่าน 3 แท่ง) ยาว >= 3 ATR(14) H1
- ระดับ: 0 = ต้นคลื่น · 1 = ปลายคลื่น (คลื่นลง: 0 = ราคาสูงสุด · 1 = ราคาต่ำสุด)
- SELL: คลื่นลง + H1 MA100/150/200 เรียง "ขึ้น" ตอนคลื่นยืนยัน → รอราคาเด้งถึง 0.3 แล้ว SELL
  BUY:  คลื่นขึ้น + H1 MA100/150/200 เรียง "ลง" → รอราคาย่อถึง 0.3 แล้ว BUY
- SL เริ่ม = ระดับ 0 · TP = 1.75 · ออเดอร์รอไม่เกิน 48 แท่ง H1 · ยกเลิกเมื่อราคาทำจุดใหม่เลยปลายคลื่นก่อนเข้า
- เลื่อน SL ขั้นบันไดหลวม (ราคาปิด H1 ผ่าน): 1 → 0.15 · 1.27 → 0.6 · 1.5 → 1.0
- ตัวกรองสัญญาณหลอก (ตอนราคาแตะ 0.3 · แท่ง H1 ที่ปิดล่าสุด): ADX(14) > 20 และ MACD histogram ยังไม่หันตามทิศไม้
  ไม่ผ่าน = ทิ้งคลื่นนั้น (ไม่รอเข้าซ้ำ) · Backtest: FBS +1,897 · PF 2.66 · DD 176 (เดิม +1,545 · 1.75 · 247)
Backtest H1 2.7 ปี (FBS): 184 ไม้ · ชนะ 24% · +1,545 จุด · PF 1.75 · DD 247 · ไตรมาสบวก 10/12 (XM: +1,441 · PF 1.68 · 11/12)
ใช้ร่วมกันทั้งบอท (multi_asset_ai_bot) · กราฟสด (bot_controller) · หน้าต่างไม้ (position_chart) · tools/backtest_all.py
"""
import json

import numpy as np
import pandas as pd

from app_paths import data_path

NAME = "Fib-H1-Counter"
LABEL = "P9 · Fib H1"
FRACTAL = 3
LEG_ATR = 3.0
ENTRY = 0.3
SL0 = 0.0
TP = 1.75
WAIT_BARS = 48
LADDER = ((1.0, 0.15), (1.27, 0.6), (1.5, 1.0))   # (ราคาปิด H1 ผ่านระดับ, ย้าย SL ไประดับ)
LEVELS_SHOWN = (-0.2, 0.0, 0.3, 0.6, 1.0, 1.27, 1.5, 1.75)
STATE_FILE = data_path("fib_plan_state.json")


def level(a: float, b: float, x: float) -> float:
    """ราคาของระดับ x (0 = ต้นคลื่น a · 1 = ปลายคลื่น b)"""
    return a + x * (b - a)


def _atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).rolling(n).mean().values


def pending_orders(df_h1: pd.DataFrame, need_stack: bool = True):
    """ออเดอร์รอที่ยังใช้ได้ตอนนี้ {side: {...}} — จำลองตามแท่ง H1 ที่ปิดแล้วเหมือน Backtest
    (คลื่นใหม่แทนออเดอร์ฝั่งเดิม · หมดอายุ 48 แท่ง · ราคาเลยปลายคลื่น = ยกเลิก · ราคาแตะจุดเข้าแล้ว = ใช้ไปแล้ว)
    df_h1: แท่ง H1 เรียงเก่า → ใหม่ แท่งสุดท้าย = แท่งที่ยังไม่ปิด (ไม่ใช้)"""
    if df_h1 is None or len(df_h1) < 260:
        return {}
    h, l, c = (df_h1[k].values.astype(float) for k in ("high", "low", "close"))
    tt = df_h1["time"]
    t = (pd.to_datetime(tt, unit="s") if np.issubdtype(tt.dtype, np.number) else pd.to_datetime(tt)).values
    n = len(df_h1) - 1                     # จำนวนแท่งที่ปิดแล้ว (index 0..n-1)
    atr = _atr(h, l, c)
    cs = pd.Series(c)
    m100, m150, m200 = (cs.rolling(k).mean().values for k in (100, 150, 200))
    stack = np.where((m100 > m150) & (m150 > m200), 1, np.where((m100 < m150) & (m150 < m200), -1, 0))
    F = FRACTAL
    last_lo = last_hi = None
    orders = {}
    start = max(210, n - 400)              # คลื่นที่เกี่ยวข้องอยู่ในช่วง ~400 แท่งล่าสุด
    for i in range(start - 60, n):
        j = i - F
        if j < F:
            continue
        new = None
        if l[j] == l[j - F:j + F + 1].min():
            last_lo = (j, l[j])
            if last_hi and last_hi[0] < j and last_hi[1] - l[j] >= LEG_ATR * atr[i]:
                new = (-1, last_hi[1], l[j])
        if h[j] == h[j - F:j + F + 1].max():
            last_hi = (j, h[j])
            if last_lo and last_lo[0] < j and h[j] - last_lo[1] >= LEG_ATR * atr[i]:
                new = (1, last_lo[1], h[j])
        if i < start:
            continue
        if new:
            dr, a, b = new
            if stack[i] == -dr or not need_stack:   # SELL บนคลื่นลงต้องให้ H1 เรียงขึ้น · BUY บนคลื่นขึ้นต้องให้ H1 เรียงลง
                orders[dr] = {"side": dr, "a": float(a), "b": float(b), "entry": level(a, b, ENTRY), "sl": level(a, b, SL0),
                              "tp": level(a, b, TP), "conf_i": i, "conf_time": pd.Timestamp(t[i]), "expire_i": i + WAIT_BARS}
            else:
                orders.pop(dr, None)
        for s in list(orders):
            od = orders[s]
            if i > od["expire_i"] or ((h[i] > od["b"]) if s == 1 else (l[i] < od["b"])):
                del orders[s]
            elif l[i] <= od["entry"] <= h[i]:
                del orders[s]              # แตะจุดเข้าไปแล้วในอดีต (ไม่ไล่เข้าย้อนหลัง)
    for od in orders.values():
        od["bars_left"] = int(od["expire_i"] - (n - 1))
    return orders


ADX_MIN = 20.0   # ตัวกรองสัญญาณหลอก (ผู้ใช้เลือก 13 ต.ค. 2026): ADX ≤ 20 = ตลาดไม่มีแรง คลื่นมักหลอก (66 ไม้ −314 จุด)


def adx_macd_series(df_h1: pd.DataFrame):
    """ADX(14) แบบ Wilder และ MACD histogram (12/26/9) ของแท่ง H1 ทั้งชุด — ใช้ทั้งบอทและ Backtest (สูตรเดียวกัน)"""
    h, l, c = (df_h1[k].values.astype(float) for k in ("high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    up = pd.Series(h).diff(); dn = -pd.Series(l).diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    trs = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean()
    pdi = 100 * pd.Series(pdm).ewm(alpha=1 / 14, adjust=False).mean() / trs
    ndi = 100 * pd.Series(ndm).ewm(alpha=1 / 14, adjust=False).mean() / trs
    adx = (100 * (pdi - ndi).abs() / (pdi + ndi + 1e-9)).ewm(alpha=1 / 14, adjust=False).mean().values
    cs = pd.Series(c)
    macd = cs.ewm(span=12, adjust=False).mean() - cs.ewm(span=26, adjust=False).mean()
    hist = (macd - macd.ewm(span=9, adjust=False).mean()).values
    return adx, hist


def entry_filter(adx, hist, k: int, side: int):
    """ผ่านตัวกรองไหม ณ แท่งที่ปิด k (แท่งก่อนแท่งที่เข้าไม้): (ผ่าน, ADX, ทิศ MACD เทียบทิศไม้)
    1) ADX > 20 · 2) MACD histogram ยังไม่หันตามทิศไม้ (BUY: ไม่ได้ยกตัว · SELL: ไม่ได้กดตัว เทียบแท่งก่อนหน้า)
    Backtest H1 2.7 ปี: FBS +1,545 → +1,897 · PF 1.75 → 2.66 · DD 247 → 176 · XM PF 1.68 → 2.46"""
    a = float(adx[k])
    turn = float(np.sign(hist[k] - hist[k - 1])) * side
    return (a > ADX_MIN and turn <= 0), a, turn


def ladder_sl(side: int, a: float, b: float, close: float, cur_sl: float):
    """SL ใหม่ตามขั้นบันไดหลวม จากราคาปิด H1 ล่าสุด (คืน None ถ้าไม่ต้องเลื่อน) — ขยับเฉพาะทิศที่ดีขึ้น"""
    new = None
    for pas, to in LADDER:
        if (close - level(a, b, pas)) * side >= 0:
            new = level(a, b, to)
    if new is None:
        return None
    if cur_sl and cur_sl > 0 and (new - cur_sl) * side <= 0.005:
        return None
    return round(new, 2)


# ---------- จำคลื่นของไม้ที่เปิด (บอทใช้เลื่อน SL ตามระดับของคลื่นนั้น) ----------
def _load():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def remember(side: int, a: float, b: float, tp: float):
    st = _load()
    st[f"{side}:{tp:.2f}"] = {"a": a, "b": b}
    if len(st) > 50:
        st = dict(list(st.items())[-50:])
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f)
    except OSError:
        pass


def leg_of(side: int, price_open: float, tp: float):
    """(a, b) ของไม้ — จากไฟล์สถานะ หรือคำนวณย้อนจาก TP และราคาเข้า (TP = 1.75 · เข้า = 0.3)"""
    rec = _load().get(f"{side}:{tp:.2f}")
    if rec:
        return float(rec["a"]), float(rec["b"])
    if not tp:
        return None
    span = (tp - price_open) / (TP - ENTRY)        # = b - a
    a = price_open - ENTRY * span
    return a, a + span
