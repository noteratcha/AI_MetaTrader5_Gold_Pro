"""ระบบดูเทรนด์ของ Gold Bot 24 (ผู้ใช้สั่ง 16 ต.ค. 2026) — รวม 5 วิธีที่นักเทรดมืออาชีพใช้ · ใช้ร่วมกันทั้งบอท · Backtest · การ์ดสภาวะตลาด

ต่อไทม์เฟรม (คิดจากแท่งที่ปิดแล้ว) ให้คะแนน 5 ข้อ ข้อละ +1 ขึ้น / -1 ลง / 0 กลาง:
  1) โครงสร้างราคา (Dow Theory): Swing High/Low (สูง/ต่ำสุดเทียบซ้าย-ขวา 3 แท่ง)
     ยอดสูงขึ้น + ฐานยกตัว = +1 · ยอดต่ำลง + ฐานต่ำลง = -1 · ราคาปิดหลุดฐาน/ทะลุยอดล่าสุดสวนทาง = โครงสร้างพัง (0)
  2) ราคาปิดเทียบ MA200
  3) EMA20 / 50 / 200 เรียงตัว
  4) ความชันของ EMA50 (เทียบ 10 แท่งก่อน) เกิน 0.25 ATR — เส้นแบน = 0
  5) ADX(14) ≥ 20 → ทิศจาก +DI / -DI (ต่ำกว่า 20 = แกว่งในกรอบ 0)
  คะแนนไทม์เฟรม = ผลรวม (-5..+5) → ≥ +3 ขาขึ้น · ≤ -3 ขาลง · ที่เหลือ = ไซด์เวย์

ภาพรวมแบบ Top-down = D1 ×3 + H4 ×2 + H1 ×1 (คะแนน ÷ 5) + ดอลลาร์ ×1 (EURUSD H4 MA10/30: ดอลลาร์อ่อน = +1 หนุนทอง)
  → -100..+100 · ≥ +40 ขาขึ้น · ≤ -40 ขาลง · |คะแนน| ≥ 70 = แรง

ตัวกรองทุกไม้ (ผู้ใช้สั่ง 16 ต.ค. 2026) = เสียงข้างมาก D1/H4/H1: ≥ 2 ไทม์เฟรมขาขึ้น → ห้าม SELL · ≥ 2 ขาลง → ห้าม BUY
  ยกเว้น P9 (สวนเทรนด์โดยตั้งใจ) และ P11 (เข้าตามตัวเลขข่าว) — Backtest: รวม +10,337 → +10,389 · P9 ถ้าบังคับ +1,872 → +718
"""
import numpy as np
import pandas as pd

SWING = 3
ADX_N, ADX_MIN = 14, 20.0
SLOPE_BARS, SLOPE_ATR = 10, 0.25
TF_MIN_SCORE = 3
WEIGHTS = {"D1": 3, "H4": 2, "H1": 1}
USD_WEIGHT = 1
USD_BAND_PCT = 0.10
OVERALL_MIN, OVERALL_STRONG = 40, 70
BARS_NEEDED = 600            # แท่งที่บอทควรดึงต่อไทม์เฟรม (EMA200 นิ่ง · MA200 ครบ)
MTF_EXEMPT = ("Fib-H1-Counter", "News-USD")   # แผนที่ไม่ใช้ตัวกรองเสียงข้างมาก D1/H4/H1
ITEMS = (("structure", "โครงสร้างราคา"), ("ma200", "ราคาเทียบ MA200"), ("ema", "EMA20/50/200"),
         ("slope", "ความชัน EMA50"), ("adx", "ADX"))


def structure_series(h, l, c, swing=SWING, with_last=False):
    """สถานะโครงสร้างราคาทุกแท่ง (Swing ยืนยันเมื่อผ่านไปอีก `swing` แท่ง — ไม่มีข้อมูลอนาคต)"""
    n = len(c)
    out = np.zeros(n, dtype=int)
    hs, ls = [], []
    for i in range(n):
        j = i - swing
        if j >= swing:
            if h[j] >= h[j - swing:j + swing + 1].max():
                hs.append(float(h[j]))
            if l[j] <= l[j - swing:j + swing + 1].min():
                ls.append(float(l[j]))
        if len(hs) >= 2 and len(ls) >= 2:
            st = 1 if (hs[-1] > hs[-2] and ls[-1] > ls[-2]) else (-1 if (hs[-1] < hs[-2] and ls[-1] < ls[-2]) else 0)
            if st == 1 and c[i] < ls[-1]:
                st = 0
            elif st == -1 and c[i] > hs[-1]:
                st = 0
            out[i] = st
    if with_last:
        return out, hs[-2:], ls[-2:]
    return out


def adx_series(h, l, c, n=ADX_N):
    """ADX / +DI / -DI แบบ Wilder"""
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    up = np.r_[0.0, np.diff(h)]
    dn = np.r_[0.0, -np.diff(l)]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = 1.0 / n
    trs = pd.Series(tr).ewm(alpha=a, adjust=False).mean()
    pdi = 100 * pd.Series(pdm).ewm(alpha=a, adjust=False).mean() / trs
    ndi = 100 * pd.Series(ndm).ewm(alpha=a, adjust=False).mean() / trs
    adx = (100 * (pdi - ndi).abs() / (pdi + ndi + 1e-9)).ewm(alpha=a, adjust=False).mean()
    return adx.to_numpy(), pdi.to_numpy(), ndi.to_numpy()


def components(df):
    """คะแนน 5 ข้อ + คะแนนรวม + สถานะ ของทุกแท่ง (ค่าแท่ง i ใช้ข้อมูลถึงแท่ง i เท่านั้น)"""
    h, l, c = (df[k].to_numpy(dtype=float) for k in ("high", "low", "close"))
    cs = pd.Series(c)
    ma200 = cs.rolling(200).mean().to_numpy()
    e20, e50, e200 = (cs.ewm(span=k, adjust=False).mean().to_numpy() for k in (20, 50, 200))
    pc = np.r_[c[0], c[:-1]]
    atr = pd.Series(np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))).rolling(14).mean().to_numpy()
    adx, pdi, ndi = adx_series(h, l, c)
    st = structure_series(h, l, c)
    m2 = np.where(np.isnan(ma200), 0, np.sign(c - ma200)).astype(int)
    ema = np.where((e20 > e50) & (e50 > e200), 1, np.where((e20 < e50) & (e50 < e200), -1, 0))
    d50 = e50 - np.r_[np.full(SLOPE_BARS, np.nan), e50[:-SLOPE_BARS]]
    with np.errstate(invalid="ignore"):
        slope = np.where(np.isnan(d50) | np.isnan(atr), 0, np.where(d50 > SLOPE_ATR * atr, 1, np.where(d50 < -SLOPE_ATR * atr, -1, 0)))
    adx_d = np.where(adx >= ADX_MIN, np.where(pdi > ndi, 1, -1), 0)
    score = st + m2 + ema + slope + adx_d
    state = np.where(score >= TF_MIN_SCORE, 1, np.where(score <= -TF_MIN_SCORE, -1, 0))
    return {"structure": st, "ma200": m2, "ema": ema, "slope": slope, "adx": adx_d, "score": score, "state": state,
            "ma200_val": ma200, "e20": e20, "e50": e50, "e200": e200, "atr": atr, "d50": d50, "adx_val": adx, "pdi": pdi, "ndi": ndi}


def usd_series(eurusd_h4):
    """ดอลลาร์จาก EURUSD H4 MA10/30: EURUSD ขึ้น = ดอลลาร์อ่อน = +1 (หนุนทอง) · ห่างไม่ถึง 0.10% = 0"""
    c = eurusd_h4["close"].astype(float)
    pct = ((c.rolling(10).mean() / c.rolling(30).mean() - 1) * 100).to_numpy()
    with np.errstate(invalid="ignore"):
        return np.where(np.isnan(pct), 0, np.where(pct >= USD_BAND_PCT, 1, np.where(pct <= -USD_BAND_PCT, -1, 0))), pct


def overall_score(d1, h4, h1, usd):
    """คะแนนภาพรวม -100..+100 (รับเป็นตัวเลขหรือ array ของคะแนนไทม์เฟรม -5..+5 และดอลลาร์ -1..+1)"""
    tot = sum(WEIGHTS.values()) + USD_WEIGHT
    v = (WEIGHTS["D1"] * np.asarray(d1) / 5 + WEIGHTS["H4"] * np.asarray(h4) / 5 + WEIGHTS["H1"] * np.asarray(h1) / 5
         + USD_WEIGHT * np.asarray(usd)) / tot
    return np.rint(v * 100).astype(int)


def overall_state(score):
    s = np.asarray(score)
    return np.where(s >= OVERALL_MIN, 1, np.where(s <= -OVERALL_MIN, -1, 0))


def tf_label(score):
    """ป้ายของไทม์เฟรมจากคะแนน -5..+5"""
    s = int(score)
    if s >= 5:
        return "▲ Strong Uptrend"
    if s >= TF_MIN_SCORE:
        return "▲ Uptrend"
    if s <= -5:
        return "▼ Strong Downtrend"
    if s <= -TF_MIN_SCORE:
        return "▼ Downtrend"
    return "◆ Sideway"


def overall_label(score):
    s = int(score)
    if s >= OVERALL_STRONG:
        return "▲ Strong Uptrend"
    if s >= OVERALL_MIN:
        return "▲ Uptrend"
    if s <= -OVERALL_STRONG:
        return "▼ Strong Downtrend"
    if s <= -OVERALL_MIN:
        return "▼ Downtrend"
    return "◆ Sideway"


# ---------------------------------------------------------------- ค่าล่าสุด (บอท · การ์ด · เว็บ)
def _fmt(v):
    return f"{v:,.2f}"


def tf_snapshot(df):
    """ค่าล่าสุดของแท่งที่ปิดแล้ว (df มีแท่งที่กำลังวิ่งต่อท้าย → ใช้แถวรองสุดท้าย) พร้อมคำอธิบายแต่ละข้อ"""
    if df is None or len(df) < 230:
        return None
    d = df.iloc[:-1]                      # ตัดแท่งที่กำลังวิ่ง
    comp = components(d)
    h, l, c = (d[k].to_numpy(dtype=float) for k in ("high", "low", "close"))
    _, hs, ls = structure_series(h, l, c, with_last=True)
    k = -1
    px = float(c[k])
    st = int(comp["structure"][k])
    if len(hs) == 2 and len(ls) == 2:
        sd = f"ยอด {_fmt(hs[0])} → {_fmt(hs[1])} · ฐาน {_fmt(ls[0])} → {_fmt(ls[1])}"
        sd = ("ยอดสูงขึ้น + ฐานยกตัว · " if st > 0 else "ยอดต่ำลง + ฐานต่ำลง · " if st < 0 else
              ("โครงสร้างพัง/ไม่ชัด · ")) + sd
    else:
        sd = "Swing ยังไม่พอ"
    m = float(comp["ma200_val"][k])
    e20, e50, e200 = (float(comp[x][k]) for x in ("e20", "e50", "e200"))
    ema = int(comp["ema"][k])
    op1, op2 = (">" if e20 > e50 else "<"), (">" if e50 > e200 else "<")
    d50, atr = float(comp["d50"][k]), float(comp["atr"][k])
    slope_atr = d50 / atr if atr else 0.0
    a, p_, n_ = float(comp["adx_val"][k]), float(comp["pdi"][k]), float(comp["ndi"][k])
    items = [
        {"key": "structure", "name": "โครงสร้างราคา", "v": st, "desc": sd},
        {"key": "ma200", "name": "ราคาเทียบ MA200", "v": int(comp["ma200"][k]),
         "desc": f"ราคา {_fmt(px)} {'เหนือ' if px > m else 'ใต้'} MA200 {_fmt(m)}"},
        {"key": "ema", "name": "EMA20/50/200", "v": ema,
         "desc": f"EMA20 {_fmt(e20)} {op1} EMA50 {_fmt(e50)} {op2} EMA200 {_fmt(e200)}" + ("" if ema else " · ยังไม่เรียงตัว")},
        {"key": "slope", "name": "ความชัน EMA50", "v": int(comp["slope"][k]),
         "desc": f"{SLOPE_BARS} แท่ง เปลี่ยน {slope_atr:+.2f} ATR (เกณฑ์ ±{SLOPE_ATR})" + (" · เส้นแบน" if not comp["slope"][k] else "")},
        {"key": "adx", "name": "ADX", "v": int(comp["adx"][k]),
         "desc": f"ADX {a:.0f} · +DI {p_:.0f} / −DI {n_:.0f}" + (" · ต่ำกว่า 20 = แกว่งในกรอบ" if a < ADX_MIN else "")},
    ]
    score = int(comp["score"][k])
    return {"score": score, "state": int(comp["state"][k]), "label": tf_label(score), "items": items}


def usd_snapshot(eurusd_h4):
    if eurusd_h4 is None or len(eurusd_h4) < 32:
        return None
    s, pct = usd_series(eurusd_h4.iloc[:-1])
    v, p = int(s[-1]), float(pct[-1])
    desc = ("ดอลลาร์อ่อนค่า — หนุนทอง" if v > 0 else "ดอลลาร์แข็งค่า — กดทอง" if v < 0 else "ดอลลาร์ทรงตัว") + f" · EURUSD H4 MA10/30 {p:+.2f}%"
    return {"v": v, "pct": round(p, 3), "desc": desc}


def snapshot(frames):
    """frames = {'H1': df, 'H4': df, 'D1': df, 'USD': df EURUSD H4} (แต่ละตัวมีแท่งที่กำลังวิ่งต่อท้าย)
    → {'H1': {...}, 'H4': {...}, 'D1': {...}, 'USD': {...}, 'overall': {score, state, label}}"""
    out = {tf: tf_snapshot(frames.get(tf)) for tf in ("H1", "H4", "D1")}
    out["USD"] = usd_snapshot(frames.get("USD"))
    if all(out[tf] for tf in ("H1", "H4", "D1")):
        sc = int(overall_score(out["D1"]["score"], out["H4"]["score"], out["H1"]["score"], (out["USD"] or {}).get("v", 0)))
        out["overall"] = {"score": sc, "state": int(overall_state(sc)), "label": overall_label(sc)}
        mj = majority(out["D1"]["state"], out["H4"]["state"], out["H1"]["state"])
        out["majority"] = {"state": mj, "label": majority_label(mj)}
    else:
        out["overall"] = None
        out["majority"] = None
    return out


def majority(d1, h4, h1):
    """เสียงข้างมากของสถานะ D1/H4/H1 (-1/0/+1): ≥ 2 ไทม์เฟรมขาขึ้น = +1 · ≥ 2 ขาลง = -1 · ที่เหลือ 0 (รับตัวเลขหรือ array)"""
    a = [np.asarray(x) for x in (d1, h4, h1)]
    up = sum((x == 1).astype(int) for x in a)
    dn = sum((x == -1).astype(int) for x in a)
    r = np.where(up >= 2, 1, np.where(dn >= 2, -1, 0))
    return int(r) if r.ndim == 0 else r


def mtf_exempt(plan_name):
    return any(str(plan_name or "").startswith(n) for n in MTF_EXEMPT)


def mtf_blocks(plan_name, direction, maj):
    """True = ไม้นี้สวนเสียงข้างมาก D1/H4/H1 → ห้ามเข้า · direction = 'BUY'/'SELL' หรือ +1/-1"""
    if mtf_exempt(plan_name) or not maj:
        return False
    d = {"BUY": 1, "SELL": -1}.get(direction, direction)
    return int(d) == -int(maj)


def majority_label(maj):
    return {1: "▲ ขาขึ้น", -1: "▼ ขาลง"}.get(int(maj or 0), "◆ ไม่ชัด")


def align(src_times_close, values, dst_times):
    """วางค่าของไทม์เฟรมหนึ่ง (พร้อมใช้ ณ เวลาปิดแท่ง) ลงเวลาอีกชุด — แท่งที่ปิดล่าสุด ณ เวลานั้น (Backtest)"""
    a = pd.DataFrame({"t": pd.to_datetime(np.asarray(src_times_close)).astype("datetime64[ns]"), "v": np.asarray(values)}).sort_values("t")
    q = pd.DataFrame({"q": pd.to_datetime(np.asarray(dst_times)).astype("datetime64[ns]")})
    q["_i"] = np.arange(len(q))
    m = pd.merge_asof(q.sort_values("q"), a, left_on="q", right_on="t", direction="backward").sort_values("_i")
    return m["v"].fillna(0).to_numpy()
