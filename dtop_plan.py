"""Plan 12 · DoubleTop-H1 — ทำยอดซ้ำนอกกรอบ Bollinger H1 ตามเทรนด์ H4 (ผู้ใช้ออกแบบ 15 ต.ค. 2026)

กฎ (ฝั่ง SELL · BUY กลับด้าน) — ใช้ร่วมกันทั้งบอทและ tools/backtest_all.py:
1. เทรนด์ H4 (แท่งปิด): MA10 < MA30 → SELL เท่านั้น · MA10 > MA30 → BUY เท่านั้น
2. แท่ง H1 ทะลุเส้น BB บน (20, 2 SD) → จด High แรก (ถ้ายังไม่ย่อแต่ทำ High ต่อ = เลื่อน High แรกตาม)
3. มีแท่งย่อ (ไม่ทำ High ใหม่) แล้วราคาขึ้นไปทำ High ใหม่สูงกว่า High แรก (ภายใน 20 แท่งนับจากทะลุ)
4. แท่งถัดไปปิดแดงและไม่ทำ High ใหม่ = ยืนยัน → SELL ที่ราคาเปิดแท่งถัดไป (ยังทำ High ต่อ = เลื่อนยอดใหม่ รอแท่งยืนยัน ·
   แท่งถัดไปไม่ยืนยัน = ยกเลิกรูปแบบ)
5. SL = High ใหม่ + 0.1 ATR(14) H1 · ไม่ตั้ง TP · ปิดทุกไม้เมื่อราคาแตะเส้น BB ล่าง
6. ไม้เพิ่ม (สูงสุด 2 ไม้): ระหว่างที่ยังถือไม้อยู่ ถ้าราคาเด้งทำยอดใหม่ที่ไม่สูงกว่ายอดเดิม (แท่งยอดสูงกว่าแท่งก่อนหน้า
   และแท่งถัดไปทำ High ต่ำกว่า) แล้วแท่งนั้นปิดแดง → SELL เพิ่ม · ใช้ SL เดียวกัน
   ยอดนั้นต้องอยู่เหนือเส้นกลาง BB (ผู้ใช้สั่ง · ยอดต่ำกว่าเส้นกลาง = ไม่เข้า)
Backtest H1 ก.พ. 2024 – ต.ค. 2026 (แบบเพิ่มได้ 2 ไม้): 337 ไม้ · ชนะ 51% · +1,339 · PF 1.49 · DD 422 · ช่วง ก.ย. 2022 – ม.ค. 2024 PF 1.07
"""
import json
import os

import numpy as np
import pandas as pd

NAME = "DoubleTop-H1"
BB_N, BB_K = 20, 2.0
WINDOW = 20          # รูปแบบต้องจบภายในกี่แท่งนับจากแท่งที่ทะลุ
MAX_ADD = 2          # ไม้เพิ่มสูงสุด (รวมไม้แรก = 3 ไม้)
SL_BUF_ATR = 0.1


def indicators(df):
    """BB บน/ล่าง/กลาง และ ATR(14) ธรรมดา ของแท่ง H1 (ทุกแท่ง รวมแท่งที่กำลังวิ่งถ้ามี)"""
    o, h, l, c = (df[k].values.astype(float) for k in ("open", "high", "low", "close"))
    cs = pd.Series(c)
    mid, sd = cs.rolling(BB_N).mean().values, cs.rolling(BB_N).std().values
    pc = np.r_[c[0], c[:-1]]
    atr = pd.Series(np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))).rolling(14).mean().values
    return o, h, l, c, mid + BB_K * sd, mid - BB_K * sd, atr, mid


def to_sec(times):
    """เวลา (epoch วินาที หรือ datetime) → array epoch วินาที"""
    v = np.asarray(times)
    if np.issubdtype(v.dtype, np.datetime64):
        return v.astype("datetime64[s]").astype("int64")
    return v.astype("int64")


def h4_trend_at(times_close, df_h4):
    """ทิศเทรนด์ H4 (MA10 เทียบ MA30 ของแท่ง H4 ที่ปิดแล้ว ณ เวลานั้น) สำหรับแต่ละเวลา (epoch วินาที) → array ±1 / 0"""
    hc = df_h4["close"].astype(float)
    m10, m30 = hc.rolling(10).mean(), hc.rolling(30).mean()
    tr = pd.DataFrame({"avail": to_sec(df_h4["time"]) + 4 * 3600,
                       "T": np.where(m10 > m30, 1, np.where(m10 < m30, -1, 0))})
    tr.loc[m30.isna().values, "T"] = 0
    q = pd.DataFrame({"t": np.asarray(times_close, dtype="int64")})
    return pd.merge_asof(q, tr, left_on="t", right_on="avail")["T"].fillna(0).astype(int).values


def new_setups():
    return {1: None, -1: None}


def step(setups, i, o, h, l, c, up, lo, trend_i):
    """อัปเดตรูปแบบด้วยแท่งปิด i → คืน (ทิศ, ยอดใหม่) เมื่อแท่ง i ยืนยันตามทิศเทรนด์ ไม่งั้น None
    การยืนยันใช้รูปแบบไปแล้ว (รีเซ็ตทั้งสองฝั่ง) แม้จะเข้าไม้ไม่ได้ (เช่น ถือไม้ของแผนนี้อยู่)"""
    for d in (-1, 1):
        st = setups[d]
        out_now = (h[i] > up[i]) if d == -1 else (l[i] < lo[i])
        ext = h[i] if d == -1 else l[i]
        if st is None:
            if out_now:
                setups[d] = {"x1": ext, "i1": i, "pull": False, "x2": None}
            continue
        if i - st["i1"] > WINDOW:
            setups[d] = {"x1": ext, "i1": i, "pull": False, "x2": None} if out_now else None
            continue
        if st["x2"] is None:
            beyond = (ext > st["x1"]) if d == -1 else (ext < st["x1"])
            if not st["pull"]:
                if beyond:
                    st["x1"] = ext
                else:
                    st["pull"] = True
            elif beyond:
                st["x2"] = ext
            continue
        more = (ext > st["x2"]) if d == -1 else (ext < st["x2"])
        if (c[i] - o[i]) * d > 0 and not more and trend_i == d:
            top = st["x2"]
            setups[1] = setups[-1] = None
            return d, top
        if more:
            st["x2"] = ext
        else:
            setups[d] = None
    return None


def addon_ok(i, d, top, last_entry_i, o, h, l, c, mid=None):
    """ไม้เพิ่มที่แท่งปิด i: แท่ง i-1 เป็นยอด (ไม่เลยยอดเดิม · อยู่ฝั่งนอกของเส้นกลาง BB) · แท่ง i ไม่ทำยอดต่อและปิดตามทิศ · ยอดเกิดหลังไม้ล่าสุด"""
    if i - 1 <= last_entry_i or i < 2:
        return False
    if d == -1:
        return (h[i - 1] > h[i - 2] and h[i] < h[i - 1] and h[i - 1] <= top and c[i] < o[i]
                and (mid is None or h[i - 1] > mid[i - 1]))
    return (l[i - 1] < l[i - 2] and l[i] > l[i - 1] and l[i - 1] >= top and c[i] > o[i]
            and (mid is None or l[i - 1] < mid[i - 1]))


def sl_price(d, top, atr_i):
    return top - d * SL_BUF_ATR * atr_i


def tp_hit(d, i, h, l, up, lo):
    """ราคาแตะเส้น BB อีกฝั่ง → (True, ราคาเส้น)"""
    if d == -1:
        return (l[i] <= lo[i]), lo[i]
    return (h[i] >= up[i]), up[i]


# ---------------------------------------------------------------- สถานะกลุ่มไม้ในบอท (ยอดเดิม / SL / แท่งที่เข้าล่าสุด)
_STATE_FILE = None


def _state_path():
    global _STATE_FILE
    if _STATE_FILE is None:
        try:
            from app_paths import data_path
            _STATE_FILE = data_path("dtop_plan_state.json")
        except Exception:
            _STATE_FILE = "dtop_plan_state.json"
    return _STATE_FILE


def load_group():
    try:
        with open(_state_path(), encoding="utf-8") as f:
            return json.load(f) or None
    except Exception:
        return None


def save_group(g):
    try:
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(g, f)
    except Exception:
        pass
