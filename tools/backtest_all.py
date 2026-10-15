"""Backtest ทุกแผนตามกฎปัจจุบัน บนข้อมูล MT5 จริง (XAUUSD) แล้วบันทึกผลเป็น web/public/backtest.json ให้หน้า /backtest
วิธีใช้: เปิด MT5 ค้างไว้ แล้วรัน  python tools/backtest_all.py  (ประมาณ 3–4 นาที) จากนั้น deploy เว็บ
P1 MA M15 · P2 MA H1 · P3 SMC · P4 SR-Bounce · P5 BB-H1 · P6 SAR H1 · P7 BB-H4 · P8 BB-H4 Free · P9 Fib H1 · P10 RSI H1 · P11 News · P12 BB DoubleTop
- AI: Walk-forward (เทรน 5000 แท่ง M15 → ทายแท่งถัดไป 500 แท่ง แล้วเลื่อน) ด้วย build_ai_features / AI_FEATURES ของบอท
- ข้อมูลที่ใช้ตัดสินใจ = แท่งที่ปิดแล้ว (เข้าไม้ที่ราคาเปิดแท่งถัดไป) · หักสเปรด 0.35 จุด/ไม้ · 1 ไม้ต่อแผนในเวลาเดียวกัน
- ไม่จำลอง: Cooldown, Circuit Breaker, Loss Block, การแย่งเข้าไม้ระหว่างแผน
"""
import sys, time
import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import os, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import multi_asset_ai_bot as bot  # noqa: E402

SPREAD = 0.35
t0 = time.time()
mt5.initialize()
def get(tf, n):
    d = pd.DataFrame(mt5.copy_rates_from_pos("XAUUSD", tf, 0, n)); d["time"] = pd.to_datetime(d["time"], unit="s"); return d
m15, h1, h4 = get(mt5.TIMEFRAME_M15, 60000), get(mt5.TIMEFRAME_H1, 16000), get(mt5.TIMEFRAME_H4, 5000)
mt5.shutdown()
A = bot._atr_series

# ---------------------------------------------------------------- AI walk-forward
ai = bot.build_ai_features(m15, h1, h4)
y = (ai.close.shift(-bot.AI_HORIZON_BARS) > ai.close).astype(float)
ok = ai[bot.AI_FEATURES].notna().all(axis=1).values
prob_up = np.full(len(ai), np.nan)
idx = np.where(ok)[0]
TRAIN, TEST = 5000, 500
start = 0
while start + TRAIN < len(idx):
    tr = idx[start:start + TRAIN - bot.AI_HORIZON_BARS]
    te = idx[start + TRAIN:start + TRAIN + TEST]
    m = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, n_jobs=-1)
    m.fit(ai.loc[tr, bot.AI_FEATURES], y.iloc[tr])
    prob_up[te] = m.predict_proba(ai.loc[te, bot.AI_FEATURES])[:, 1]
    start += TEST
ai["p_up"] = prob_up
print(f"AI walk-forward done {time.time() - t0:.0f}s", flush=True)

# ---------------------------------------------------------------- M15 base features
b = m15.copy()
b["close_time"] = b.time + pd.Timedelta(minutes=15)
b["atr"] = A(b)
b["ma5"], b["ma13"] = b.close.rolling(5).mean(), b.close.rolling(13).mean()
b["lw"] = (np.minimum(b.open, b.close) - b.low) / (b.atr + 1e-9)
b["uw"] = (b.high - np.maximum(b.open, b.close)) / (b.atr + 1e-9)
_dl = b.close.diff()
_g = _dl.where(_dl > 0, 0).rolling(14).mean(); _ls = (-_dl.where(_dl < 0, 0)).rolling(14).mean()
b["rsi"] = 100 - (100 / (1 + (_g / (_ls + 1e-9))))
b = bot.add_divergence_features(b, lookback=14)
print("divergence counts:", int(b.bull_div.sum()), int(b.bear_div.sum()), int(b.hidden_bull.sum()), int(b.hidden_bear.sum()), flush=True)
b["p_up"] = ai.set_index("time").reindex(b.time)["p_up"].values

# H1 features (แท่งที่ปิดแล้ว)
hx = pd.DataFrame({"avail": h1.time + pd.Timedelta(minutes=60)})
m10, m30 = h1.close.rolling(10).mean(), h1.close.rolling(30).mean()
hx["h1_up"] = (m10 > m30).astype(float)
s100, s150, s200 = (h1.close.rolling(k).mean() for k in (100, 150, 200))
hx["h1_stack"] = np.where((s100 < s150) & (s150 < s200), -1, np.where((s100 > s150) & (s150 > s200), 1, 0))
mid, sd = h1.close.rolling(20).mean(), h1.close.rolling(20).std()
hx["bb_up"], hx["bb_lo"] = mid + 2 * sd, mid - 2 * sd
ema12, ema26 = h1.close.ewm(span=12, adjust=False).mean(), h1.close.ewm(span=26, adjust=False).mean()
macd = ema12 - ema26
hx["macd_h"] = macd - macd.ewm(span=9, adjust=False).mean()
hx["macd_h_prev"] = hx["macd_h"].shift(1)
# แนวรับ/ต้าน 1,000 แท่ง ณ แท่ง H1 ที่ปิด พร้อมผสาน H4 Confluence (1,000 แท่ง)
h4_close_times = (h4.time + pd.Timedelta(hours=4)).values
h1_close_times = (h1.time + pd.Timedelta(hours=1)).values
h4_indices = np.searchsorted(h4_close_times, h1_close_times, side="right")
cached_h4_zones, cached_h4_atr = None, None
last_h4_idx = -1

sup, res = np.full(len(h1), np.nan), np.full(len(h1), np.nan)
for i in range(1020, len(h1)):
    idx_h4 = h4_indices[i]
    if idx_h4 != last_h4_idx and idx_h4 >= 60:
        h4_slice = h4.iloc[max(0, idx_h4 - 1000):idx_h4]
        cached_h4_zones, cached_h4_atr = bot._extract_sr_zones(h4_slice, lookback=1000)
        last_h4_idx = idx_h4
    h1_slice = h1.iloc[i - 1001:i + 2] if i + 2 <= len(h1) else pd.concat([h1.iloc[i - 1001:i + 1], h1.iloc[[i]]])
    r = bot.find_sr_levels(h1_slice, float(h1.close.iloc[i]), lookback=1000, raw_zones_h4=cached_h4_zones, atr_h4=cached_h4_atr)
    sup[i], res[i] = r["support"], r["resistance"]
hx["sup"], hx["res"] = sup, res
print(f"H1 S/R (1,000 bars + H4 confluence) done {time.time() - t0:.0f}s", flush=True)

# H4 regime (MA10/30, ±0.20%) + H4 stack
vx = pd.DataFrame({"avail": h4.time + pd.Timedelta(minutes=240)})
f10, f30 = h4.close.rolling(10).mean(), h4.close.rolling(30).mean()
vx["h4_up"] = (f10 > f30).astype(float)
vx["h4_side"] = ((f10 / f30 - 1).abs() * 100 < 0.20).astype(float)
t100, t150, t200 = (h4.close.rolling(k).mean() for k in (100, 150, 200))
vx["h4_stack"] = np.where((t100 < t150) & (t150 < t200), -1, np.where((t100 > t150) & (t150 > t200), 1, 0))
_m5 = h4.close.rolling(5).mean(); _a4 = A(h4); _sl5 = (_m5 - _m5.shift(2)) / _a4; _up = f10 > f30
vx["p6_dir"] = np.where(_up == (h4.close > t200), np.where(_up, 1, -1), 0)   # Plan 6: H4 MA10/30 ตรงกับราคาเทียบ MA200
_m4, _s4 = h4.close.rolling(20).mean(), h4.close.rolling(20).std()
vx["bb4_up"], vx["bb4_lo"] = _m4 + 2 * _s4, _m4 - 2 * _s4   # Plan 7/8: Bollinger H4
vx["p2_dir"] = np.where(_up & (_sl5 > 0) & (h4.close > t200), 1, np.where(~_up & (_sl5 < 0) & (h4.close < t200), -1, 0))

b = pd.merge_asof(b.sort_values("close_time"), hx, left_on="close_time", right_on="avail", direction="backward").drop(columns="avail")
b = pd.merge_asof(b, vx, left_on="close_time", right_on="avail", direction="backward").drop(columns="avail").reset_index(drop=True)


def h4_ok(i, d):
    if b.h4_side.values[i] == 1:
        return True
    return (b.h4_up.values[i] == 1) == (d == 1)


# ---------------------------------------------------------------- simulators
def stats(name, trades):
    t = np.array([x["pnl"] for x in trades])
    if not len(t):
        return dict(plan=name, n=0)
    eq = np.r_[0.0, np.cumsum(t)]; dd = float(np.max(np.maximum.accumulate(eq) - eq))   # DD นับจากจุดเริ่ม (0)
    w, ls = t[t > 0].sum(), -t[t < 0].sum()
    last = t[-100:]
    h1_, h2_ = t[:len(t) // 2], t[len(t) // 2:]
    wr = lambda a: round((a > 0).mean() * 100, 1) if len(a) else None   # noqa: E731
    return dict(plan=name, n=len(t), win=round((t > 0).mean() * 100, 1), net=round(t.sum(), 1), pf=round(w / ls, 2) if ls else 0,
                maxdd=round(dd, 1), avg=round(t.mean(), 2), half1=round(h1_.sum(), 1), half2=round(h2_.sum(), 1),
                half1_n=len(h1_), half1_win=wr(h1_), half2_n=len(h2_), half2_win=wr(h2_),   # จำนวนไม้ / % ชนะ แต่ละครึ่ง (หน้าเว็บ)
                last100_net=round(last.sum(), 1), last100_win=round((last > 0).mean() * 100, 1), last100_n=len(last))


def sim_ma(frame, fast, slow, trend_col, atr_col="atr", step=5.0, frac=0.4, entry_ok=None, sl_mult=0.75, trail="sl", first_frac=None, exit_slow=None, confirm=False):
    """step=None → ไม่เลื่อน SL · entry_ok(i, d) = ตัวกรองเพิ่มเติมก่อนเข้าไม้
    trail="sl": เลื่อน frac ของระยะ SL → ราคาของขั้น · trail="entry": เลื่อน (first_frac ขั้นแรก / frac ขั้นถัดไป) ของระยะ ราคาเข้า → ราคาของขั้น"""
    o, h, l, a, t = frame.open.values, frame.high.values, frame.low.values, frame[atr_col].values, frame.time.values
    c = frame.close.values
    mf, ms, td = frame[fast].values, frame[slow].values, frame[trend_col].values
    mx = frame[exit_slow].values if exit_slow else ms   # เส้นที่ใช้ออกไม้ (ค่าเริ่มต้น = เส้นเดียวกับตอนเข้า)
    out, pos, start = [], None, 0
    for i in range(3, len(frame) - 2):
        up = mf[i - 1] <= ms[i - 1] and mf[i] > ms[i]
        dn = mf[i - 1] >= ms[i - 1] and mf[i] < ms[i]
        xup = mf[i - 1] <= mx[i - 1] and mf[i] > mx[i]
        xdn = mf[i - 1] >= mx[i - 1] and mf[i] < mx[i]
        if pos and i >= start:
            d, e, sl, k, te = pos
            if (d == 1 and l[i] <= sl) or (d == -1 and h[i] >= sl):
                out.append(dict(time=te, pnl=(sl - e) * d - SPREAD)); pos = None
            elif (d == 1 and xdn) or (d == -1 and xup):
                out.append(dict(time=te, pnl=(o[i + 1] - e) * d - SPREAD)); pos = None
            elif step:
                best = (h[i] - e) if d == 1 else (e - l[i])
                while best >= k * step:
                    step_px = e + d * k * step
                    f_k = first_frac if (first_frac is not None and k == 1) else frac
                    if trail == "entry":
                        ns = sl + d * f_k * abs(step_px - e)
                        ns = min(ns, step_px - SPREAD) if d == 1 else max(ns, step_px + SPREAD)   # ไม่ให้ SL เลยราคา (บอทบีบไว้ที่ราคา ± สเปรด)
                    else:
                        ns = sl + d * f_k * abs(step_px - sl)
                    sl = max(sl, ns) if d == 1 else min(sl, ns); k += 1
                pos = (d, e, sl, k, te)
        if not pos and (up or dn) and not np.isnan(a[i]):
            d = 1 if up else -1
            if td[i] == d and (entry_ok is None or entry_ok(i, d)):
                # confirm: แท่งถัดไป (i+1) ต้องปิดไปทางเดียวกับไม้ และตัวแท่งทั้งตัวอยู่ฝั่งเดียวกับเส้น slow (MA13) → เข้า open[i+2] (P1 · 15 ต.ค. 2026)
                ok_c = (c[i + 1] - o[i + 1]) * d > 0 and ((min(o[i + 1], c[i + 1]) > ms[i + 1]) if d == 1 else (max(o[i + 1], c[i + 1]) < ms[i + 1]))
                k0 = i + 1 if not confirm else (i + 2 if ok_c else None)
                if k0 is not None:
                    e = o[k0]
                    pos = (d, e, e - d * sl_mult * a[i], 1, t[k0]); start = k0
    return out


def sim_ai_plan(signal_fn, step=None, frac=0.4, first_frac=None, slm=0.75, tpm=1.125, use_h4=True):
    """Plan 3–5: SL 0.75 ATR · TP 1.125 ATR · ล็อกกำไร +0.35 ATR ที่ 70% · ขยาย TP +1 ATR ที่ 80% เมื่อ AI ≥54% · AI กลับทิศ ≥60% และติดลบ → ปิด"""
    o, h, l, c, a, p = b.open.values, b.high.values, b.low.values, b.close.values, b.atr.values, b.p_up.values
    t = b.time.values
    out, pos = [], None
    for i in range(30, len(b) - 1):
        if pos:
            d, e, sl, tp, at, locked, te, k = pos
            if (d == 1 and l[i] <= sl) or (d == -1 and h[i] >= sl):
                out.append(dict(time=te, pnl=(sl - e) * d - SPREAD)); pos = None
            elif (d == 1 and h[i] >= tp) or (d == -1 and l[i] <= tp):
                out.append(dict(time=te, pnl=(tp - e) * d - SPREAD)); pos = None
            else:
                pu = p[i]
                pd_same = pu if d == 1 else 1 - pu
                if not np.isnan(pu) and (1 - pd_same) >= 0.60 and (c[i] - e) * d < 0:
                    out.append(dict(time=te, pnl=(o[i + 1] - e) * d - SPREAD)); pos = None
                else:
                    if step:  # Step Trailing: ทุกกำไร step จุด เลื่อน SL (first_frac ขั้นแรก / frac ขั้นถัดไป) ของระยะ SL → ราคา
                        best = (h[i] - e) if d == 1 else (e - l[i])
                        while best >= k * step:
                            ns = sl + d * (first_frac if (first_frac is not None and k == 1) else frac) * abs(e + d * k * step - sl)
                            sl = max(sl, ns) if d == 1 else min(sl, ns); k += 1
                    target = abs(tp - e)
                    prog = ((h[i] - e) if d == 1 else (e - l[i])) / target if target else 0
                    if prog >= 0.80 and not np.isnan(pu) and pd_same >= 0.54:
                        tp = tp + d * at; sl = max(sl, e + 0.35 * at) if d == 1 else min(sl, e - 0.35 * at); locked = True
                    elif prog >= 0.70 and not locked:
                        new_sl = e + d * 0.35 * at
                        if abs(c[i] - new_sl) >= 0.4 * at:
                            sl = max(sl, new_sl) if d == 1 else min(sl, new_sl); locked = True
                    pos = (d, e, sl, tp, at, locked, te, k)
        if pos or np.isnan(a[i]) or np.isnan(p[i]):
            continue
        d = signal_fn(i)
        if d and (h4_ok(i, d) if use_h4 else True):   # P8 ไม่ใช้ตัวกรองเทรนด์ H4
            e = o[i + 1]; at = a[i]
            pos = (d, e, e - d * slm * at, e + d * tpm * at, at, False, t[i + 1], 1)
    return out


V = {k: b[k].values for k in ("h1_stack", "low", "high", "close", "open", "atr", "lw", "uw", "sup", "res", "h1_up", "p_up", "bb_lo", "bb_up", "bb4_lo", "bb4_up",
                              "macd_h", "macd_h_prev", "bull_div", "bear_div", "hidden_bull", "hidden_bear")}


def sig_smc(i):
    s, r, c = V["sup"][i], V["res"][i], V["close"][i]
    if np.isnan(s):
        return 0
    pu = V["p_up"][i]
    if V["low"][i] < s <= c and 0.40 <= V["lw"][i] <= 1.0 and V["h1_up"][i] == 1 and V["h1_stack"][i] == 1 and pu >= 0.50:
        return 1
    if V["high"][i] > r >= c and 0.40 <= V["uw"][i] <= 1.0 and V["h1_up"][i] == 0 and V["h1_stack"][i] == -1 and (1 - pu) >= 0.50:
        return -1
    return 0


def sig_bounce(i):
    s, r, c, a = V["sup"][i], V["res"][i], V["close"][i], V["atr"][i]
    if np.isnan(s):
        return 0
    pu = V["p_up"][i]
    bdiv = V["bull_div"][i] or V["hidden_bull"][i]
    sdiv = V["bear_div"][i] or V["hidden_bear"][i]
    if c >= s and c - s <= 0.75 * a and bdiv and (V["lw"][i] >= 0.20 or c > V["open"][i]) and V["h1_stack"][i] != -1 and pu >= bot.P4_AI_MIN:
        return 1
    if c <= r and r - c <= 0.75 * a and sdiv and (V["uw"][i] >= 0.20 or c < V["open"][i]) and V["h1_stack"][i] != 1 and (1 - pu) >= bot.P4_AI_MIN:
        return -1
    return 0


def sig_bb(i):
    lo, upb, c = V["bb_lo"][i], V["bb_up"][i], V["close"][i]
    if np.isnan(lo) or np.isnan(V["macd_h_prev"][i]):
        return 0
    pu = V["p_up"][i]
    # 13 ต.ค. 2026: ห้ามเข้าเมื่อ H1 MA100/150/200 เรียงตามทิศไม้ (สัญญาณหลอกกลางเทรนด์แรง)
    if V["low"][i] < lo <= c and V["lw"][i] >= 0.20 and (V["bull_div"][i] or V["hidden_bull"][i]) and pu >= 0.55 and V["h1_stack"][i] != 1:
        return 1
    if V["high"][i] > upb >= c and V["uw"][i] >= 0.20 and (V["bear_div"][i] or V["hidden_bear"][i]) and (1 - pu) >= 0.55 and V["h1_stack"][i] != -1:
        return -1
    return 0


def sig_bb4(i):
    """Plan 7/8: กฎเดียวกับ P5 แต่ขอบเป็น Bollinger H4 (P7 ผ่าน h4_ok ใน sim_ai_plan · P8 ไม่ใช้)"""
    lo, upb, c = V["bb4_lo"][i], V["bb4_up"][i], V["close"][i]
    if np.isnan(lo):
        return 0
    pu = V["p_up"][i]
    if V["low"][i] < lo <= c and V["lw"][i] >= 0.20 and (V["bull_div"][i] or V["hidden_bull"][i]) and pu >= 0.55 and V["h1_stack"][i] != 1:
        return 1
    if V["high"][i] > upb >= c and V["uw"][i] >= 0.20 and (V["bear_div"][i] or V["hidden_bear"][i]) and (1 - pu) >= 0.55 and V["h1_stack"][i] != -1:
        return -1
    return 0


rows, ALL = [], {}
def keep(key, tr):
    ALL[key] = tr
    return tr
b["ma50"] = b.close.rolling(50).mean()
_rsi, _c, _m50 = b.rsi.values, b.close.values, b.ma50.values
def p1_filter(i, d):  # ตัวกรองสัญญาณหลอก: RSI 50–70 (BUY) / 30–50 (SELL) + ราคาปิดฝั่งเดียวกับ MA50 M15
    return ((50 < _rsi[i] < 70) if d == 1 else (30 < _rsi[i] < 50)) and (_c[i] - _m50[i]) * d > 0
rows.append(stats("P1 MA M15", keep(1, sim_ma(b, "ma5", "ma13", "h1_stack", entry_ok=p1_filter, sl_mult=1.0,
                                                trail="sl", first_frac=0.50, frac=0.40, confirm=True))))
f = h1.copy(); f["close_time"] = f.time + pd.Timedelta(minutes=60)
f["atr"] = A(f); f["ma5"], f["ma10"], f["ma20"] = f.close.rolling(5).mean(), f.close.rolling(10).mean(), f.close.rolling(20).mean()
f = pd.merge_asof(f.sort_values("close_time"), vx[["avail", "p2_dir", "p6_dir"]], left_on="close_time", right_on="avail", direction="backward").reset_index(drop=True)
rows.append(stats("P2 MA H1", keep(2, sim_ma(f, "ma5", "ma10", "p2_dir", step=None, sl_mult=1.25, exit_slow="ma20"))))
rows.append(stats("P3 SMC", keep(3, sim_ai_plan(sig_smc, step=5.0, frac=0.4, first_frac=0.5, slm=1.0, tpm=2.0))))
rows.append(stats("P4 SR-Bounce", keep(4, sim_ai_plan(sig_bounce, step=5.0, frac=0.4, first_frac=0.5, slm=1.0, tpm=2.0))))


def sim_psar(fr):
    """Plan 6: SAR(0.01/0.1) H1 สลับมาทางเทรนด์ H4 → SL = SAR (ไม่เกิน 3 ATR) เลื่อนตาม SAR ·
    กำไรสูงสุด ≥ 2 ATR → SAR เร็ว (0.02/0.2) · ออกเมื่อเทรนด์เปลี่ยน / ราคาปิดผิดฝั่ง EMA100 · SL มี gap: ปิดที่ราคาเปิด"""
    o, h, l, c, a, t = fr.open.values, fr.high.values, fr.low.values, fr.close.values, fr.atr.values, fr.time.values
    T6 = fr.p6_dir.fillna(0).values.astype(int)
    sar, dr = bot.psar_series(h, l, *bot.P6_SAR)
    sf, df_ = bot.psar_series(h, l, *bot.P6_SAR_FAST)
    ema = fr.close.ewm(span=bot.P6_EXIT_EMA, adjust=False).mean().values
    out, pos = [], None
    for i in range(3, len(fr) - 1):
        if pos:
            d, e, sl, a0, mfe, te = pos
            xp = None
            if d == 1 and o[i] <= sl: xp = o[i]
            elif d == 1 and l[i] <= sl: xp = sl
            elif d == -1 and o[i] >= sl: xp = o[i]
            elif d == -1 and h[i] >= sl: xp = sl
            if xp is None:
                mfe = max(mfe, (h[i] - e) if d == 1 else (e - l[i]))
                if T6[i] != d or (c[i] - ema[i]) * d < 0:
                    xp = o[i + 1]
            if xp is not None:
                out.append(dict(time=te, pnl=(xp - e) * d - SPREAD)); pos = None
            else:
                if dr[i] == d: sl = max(sl, sar[i]) if d == 1 else min(sl, sar[i])
                if mfe >= bot.P6_FAST_AFTER_ATR * a0 and df_[i] == d: sl = max(sl, sf[i]) if d == 1 else min(sl, sf[i])
                pos = (d, e, sl, a0, mfe, te)
        if pos is None and dr[i] != dr[i - 1] and T6[i] != 0 and dr[i] == T6[i] and not np.isnan(a[i]):
            d = int(T6[i]); e = o[i + 1]; sl = sar[i]
            if (sl - e) * d >= 0: sl = e - d * a[i]
            if abs(e - sl) > bot.P6_SL_CAP_ATR * a[i]: sl = e - d * bot.P6_SL_CAP_ATR * a[i]
            pos = (d, e, sl, a[i], 0.0, t[i + 1])
    return out


rows.append(stats("P5 BB-H1", keep(5, sim_ai_plan(sig_bb, step=5.0, frac=0.4, first_frac=0.5))))
rows.append(stats("P6 SAR H1", keep(6, sim_psar(f))))
def sim_fib(df):
    """Plan 9: Fib-H1-Counter (กฎใน fib_plan.py) — คลื่น H1 ≥ 3 ATR · SELL บนคลื่นลงเมื่อ H1 MA100/150/200 เรียงขึ้น
    (BUY กลับกัน) · เข้า 0.3 · SL 0 · TP 1.75 · ออเดอร์รอ 48 แท่ง · เลื่อน SL ขั้นบันไดหลวมตามราคาปิด H1 · แผนละ 1 ไม้"""
    import fib_plan as fp
    o_, h_, l_, c_ = (df[k].values for k in ("open", "high", "low", "close"))
    t_ = df.time.values; n_ = len(df)
    pc = np.r_[c_[0], c_[:-1]]
    atr_ = pd.Series(np.maximum(h_ - l_, np.maximum(abs(h_ - pc), abs(l_ - pc)))).rolling(14).mean().values
    cs = pd.Series(c_)
    m1, m2, m3 = (cs.rolling(k).mean().values for k in (100, 150, 200))
    stk = np.where((m1 > m2) & (m2 > m3), 1, np.where((m1 < m2) & (m2 < m3), -1, 0))
    F = fp.FRACTAL
    adx_, hist_ = fp.adx_macd_series(df)      # ตัวกรองสัญญาณหลอก ADX > 20 + MACD ยังไม่หันตามทิศไม้
    out, orders, pos = [], {}, None
    last_lo = last_hi = None
    for i in range(210, n_ - 1):
        j = i - F; new = None
        if l_[j] == l_[j - F:j + F + 1].min():
            last_lo = (j, l_[j])
            if last_hi and last_hi[0] < j and last_hi[1] - l_[j] >= fp.LEG_ATR * atr_[i]:
                new = (-1, last_hi[1], l_[j])
        if h_[j] == h_[j - F:j + F + 1].max():
            last_hi = (j, h_[j])
            if last_lo and last_lo[0] < j and h_[j] - last_lo[1] >= fp.LEG_ATR * atr_[i]:
                new = (1, last_lo[1], h_[j])
        if pos:
            s_, e, sl, tp, ei, a, b = pos
            rr = None
            if (l_[i] <= sl) if s_ == 1 else (h_[i] >= sl): rr = (sl - e) * s_
            elif (h_[i] >= tp) if s_ == 1 else (l_[i] <= tp): rr = (tp - e) * s_
            elif i - ei >= 240: rr = (c_[i] - e) * s_
            if rr is not None:
                out.append(dict(time=t_[ei], pnl=rr - SPREAD)); pos = None
            else:
                nsl = fp.ladder_sl(s_, a, b, c_[i], sl)
                if nsl is not None:
                    pos = (s_, e, nsl, tp, ei, a, b)
        if new:
            dr, a, b = new
            if stk[i] == -dr:
                orders[dr] = dict(e=fp.level(a, b, fp.ENTRY), sl=fp.level(a, b, fp.SL0), tp=fp.level(a, b, fp.TP), exp=i + fp.WAIT_BARS, a=a, b=b)
            else:
                orders.pop(dr, None)
        for s_ in list(orders):
            od = orders[s_]
            if i > od["exp"] or ((h_[i] > od["b"]) if s_ == 1 else (l_[i] < od["b"])):
                del orders[s_]; continue
            if pos:
                continue
            if l_[i] <= od["e"] <= h_[i]:
                if not fp.entry_filter(adx_, hist_, i - 1, s_)[0]:
                    del orders[s_]; continue       # ไม่ผ่านตัวกรอง = ทิ้งคลื่นนี้
                if (l_[i] <= od["sl"]) if s_ == 1 else (h_[i] >= od["sl"]):
                    out.append(dict(time=t_[i], pnl=(od["sl"] - od["e"]) * s_ - SPREAD))
                else:
                    pos = (s_, od["e"], od["sl"], od["tp"], i, od["a"], od["b"])
                del orders[s_]
    return out


rows.append(stats("P7 BB-H4", keep(7, sim_ai_plan(sig_bb4, step=5.0, frac=0.4, first_frac=0.5))))
rows.append(stats("P8 BB-H4 Free", keep(8, sim_ai_plan(sig_bb4, step=5.0, frac=0.4, first_frac=0.5, use_h4=False))))
rows.append(stats("P9 Fib H1", keep(9, sim_fib(h1))))


def sim_rsi(df):
    """Plan 10: RSI-H1-Trend (กฎใน rsi_plan.py) — RSI(14) แตะ 30/70 ตามเทรนด์ MA200 H1 · SL 2 / TP 3 ATR · ถือไม่เกิน 48 แท่ง"""
    import rsi_plan as rp
    o_, h_, l_, c_ = (df[k].values for k in ("open", "high", "low", "close"))
    t_ = df.time.values
    rsi_, ma_, atr_ = rp.indicators(df)
    out, pos = [], None
    for i in range(210, len(df) - 1):
        if pos:
            s_, e, sl, tp, ei = pos
            rr = None
            if (l_[i] <= sl) if s_ == 1 else (h_[i] >= sl): rr = (sl - e) * s_
            elif (h_[i] >= tp) if s_ == 1 else (l_[i] <= tp): rr = (tp - e) * s_
            elif i - ei >= rp.HOLD_HOURS: rr = (o_[i + 1] - e) * s_
            if rr is not None:
                out.append(dict(time=t_[ei], pnl=rr - SPREAD)); pos = None
            continue
        sg = rp.signal_at(rsi_, ma_, c_, i)
        if sg and not np.isnan(atr_[i]):
            e = o_[i + 1]
            sl, tp = e - sg * rp.SL_ATR * atr_[i], e + sg * rp.TP_ATR * atr_[i]
            pos = (sg, e, sl, tp, i + 1)
    return out


rows.append(stats("P10 RSI H1", keep(10, sim_rsi(h1))))


# ---------------------------------------------------------------- Plan 11: News-USD (Tick จริง · ปฏิทิน MetaQuotes)
import news_plan  # noqa: E402
import thai_time  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
P11_LATENCY = 10   # วินาทีหลังข่าวออก (ค่าจริงมาถึง + ส่งออเดอร์) — ใช้ค่ากลางที่สมจริง ไม่ใช่ 2 วิ


def sim_news():
    """กฎจาก news_plan.decide (ตัวเดียวกับบอท) · เข้า Tick แรกหลังข่าว P11_LATENCY วิ (BUY=Ask / SELL=Bid)
    15 นาทีแรกตรวจ SL ทุก Tick แล้วต่อด้วยแท่ง M15 · SL 3 ATR M15 ก่อนข่าว · ไม่ตั้ง TP · ถือ 8 ชม. · ผลคูณจำนวน Lot"""
    mt5.initialize()
    ti = mt5.terminal_info()
    path = os.path.join(ti.data_path, "MQL5", "Files", "goldbot24_calendar_usd.csv") if ti else ""
    if not os.path.isfile(path):
        print("P11: ไม่พบ goldbot24_calendar_usd.csv — รันสคริปต์ GoldBot24_CalendarExport ใน MT5 ก่อน (ข้าม P11)")
        mt5.shutdown()
        return []
    cal = pd.read_csv(path, sep="	", encoding="cp874", encoding_errors="replace")
    cal = cal[cal.code.isin(news_plan.CODES) & cal.actual.notna() & cal.forecast.notna() & cal.prev.notna()]
    t15 = m15.time.values.astype("datetime64[s]").astype("int64")   # เวลาเซิร์ฟเวอร์ (วินาที)
    o_, h_, l_, c_ = m15.open.values, m15.high.values, m15.low.values, m15.close.values
    a_ = A(m15).values
    out = []
    for ts, g in cal.groupby("time_server"):
        d, mult, _ = news_plan.decide([(r.code, r.actual, r.forecast, r.prev) for r in g.itertuples()])
        if not d:
            continue
        utc = pd.Timestamp(ts.replace(".", "-")).tz_localize("UTC").timestamp()
        srv = int(utc) + int(thai_time.eu_offset(utc))
        i = int(np.searchsorted(t15, srv))
        if i >= len(t15) - 40 or t15[i] != srv or i < 20:
            continue
        tk = mt5.copy_ticks_range("XAUUSD", datetime.fromtimestamp(srv - 5, timezone.utc), datetime.fromtimestamp(srv + 15 * 60, timezone.utc), mt5.COPY_TICKS_ALL)
        if tk is None or not len(tk):
            continue
        tk = pd.DataFrame(tk)
        tk = tk[tk.time_msc >= (srv + P11_LATENCY) * 1000]
        if not len(tk):
            continue
        e = float(tk.ask.iloc[0] if d > 0 else tk.bid.iloc[0])
        sl = e - d * news_plan.SL_ATR * a_[i - 1]
        pnl = None
        for px in (tk.bid.values if d > 0 else tk.ask.values):
            if (px - sl) * d <= 0:
                pnl = (sl - e) * d
                break
        end = i + 1 + news_plan.HOLD_HOURS * 4
        if pnl is None:
            for j in range(i + 1, end):
                if (l_[j] <= sl) if d > 0 else (h_[j] >= sl):
                    pnl = (sl - e) * d
                    break
        if pnl is None:
            pnl = (c_[end - 1] - e) * d - 0.25
        out.append(dict(time=pd.Timestamp(srv, unit="s"), pnl=pnl * mult))
    mt5.shutdown()
    return out

rows.append(stats("P11 News", keep(11, sim_news())))


# ---------------------------------------------------------------- Plan 12: DoubleTop-H1 (กฎใน dtop_plan.py · ตัวเดียวกับบอท)
import dtop_plan  # noqa: E402


def sim_dtop(df, df4):
    """BB H1 ทำยอดซ้ำตามเทรนด์ H4 MA10/30 · SL ยอดใหม่ ± 0.1 ATR · ปิดทุกไม้เมื่อแตะ BB อีกฝั่ง · ไม้เพิ่ม ≤ 2 (ยอดไม่เลยยอดเดิม · อยู่ฝั่งนอกเส้นกลาง)"""
    o, h, l, c, up, lo, atr, mid = dtop_plan.indicators(df)
    tsec = dtop_plan.to_sec(df.time)
    tr = dtop_plan.h4_trend_at(tsec + 3600, df4)
    setups, grp, out = dtop_plan.new_setups(), None, []
    for i in range(30, len(df) - 1):
        if grp:
            d = grp["d"]
            if (h[i] >= grp["sl"]) if d == -1 else (l[i] <= grp["sl"]):
                xp = grp["sl"]
            else:
                hit, px = dtop_plan.tp_hit(d, i, h, l, up, lo)
                xp = px if hit else None
            if xp is not None:
                for e, ei in grp["entries"]:
                    out.append(dict(time=df.time.values[ei], pnl=(xp - e) * d - SPREAD))
                grp = None
            elif len(grp["entries"]) - 1 < dtop_plan.MAX_ADD and dtop_plan.addon_ok(i, d, grp["top"], grp["entries"][-1][1], o, h, l, c, mid):
                grp["entries"].append((o[i + 1], i + 1))
        sig = dtop_plan.step(setups, i, o, h, l, c, up, lo, tr[i])
        if sig and grp is None:
            d, top = sig
            e = o[i + 1]; sl = dtop_plan.sl_price(d, top, atr[i])
            if (e - sl) * d > 0:
                grp = {"d": d, "top": top, "sl": sl, "entries": [(e, i + 1)]}
    return out


rows.append(stats("P12 BB DoubleTop", keep(12, sim_dtop(h1, h4))))
pd.set_option("display.width", 220)
print(f"ช่วงข้อมูล {b.time.iloc[0]} → {b.time.iloc[-1]} · ใช้เวลา {time.time() - t0:.0f}s")
print(pd.DataFrame(rows).to_string(index=False))


# ---------------------------------------------------------------- JSON สำหรับหน้าเว็บ /backtest
from version import APP_VERSION  # noqa: E402
NAMES = {1: ("Plan 1", "MA-Cross-Trend", "แท่งยืนยัน (ปิดตามทิศ + ทั้งตัวพ้น MA13) · MA5×MA13 M15 · H1 MA100/150/200 · กรอง RSI + MA50 · เลื่อน SL ทุก 5 จุด (ขั้นแรก 50% / ถัดไป 40%)"),
         2: ("Plan 2", "MA-Cross-H1-Trend", "MA5×MA10 H1 · H4 MA10/30 + MA200 · SL 1.25 ATR · ออกเมื่อ MA5 ตัด MA20"),
         3: ("Plan 3", "SMC-LiquidityHunt", "กวาดแนวรับ/ต้าน H1 1,000 แท่ง + H4 Confluence (ไส้ 0.4–1.0 ATR) + MA100/150/200 H1 + AI · SL 1.0 / TP 2.0 ATR · เลื่อน SL 50%/40%"),
         4: ("Plan 4", "SR-SwingBounce", "เด้งแนวรับ/ต้าน H1 1,000 แท่ง + H4 Confluence (≤ 0.75 ATR) + Divergence + MA100/150/200 ไม่สวน + AI ≥ 58% · SL 1.0 / TP 2.0 ATR"),
         5: ("Plan 5", "BB-H1-Reversion", "หลุดกรอบ BB H1 + Divergence + AI ≥ 55% · H1 MA100/150/200 ไม่เรียงตามทิศ · เลื่อน SL ทุก 5 จุด (50%/40%)"),
         6: ("Plan 6", "PSAR-H1-Trend", "SAR H1 สลับตามเทรนด์ H4 + MA200 · SL ตาม SAR (เร็วขึ้นเมื่อกำไร 2 ATR) · ออกเมื่อเทรนด์เปลี่ยน/ผิดฝั่ง EMA100"),
         7: ("Plan 7", "BB-H4-Reversion", "หลุดกรอบ BB H4 (แท่ง M15) + Divergence + AI ≥ 55% · H1 MA100/150/200 ไม่เรียงตามทิศ · เทรนด์ H4 MA10/30 ไม่สวน · เลื่อน SL ทุก 5 จุด"),
         8: ("Plan 8", "BB-H4-Free", "หลุดกรอบ BB H4 (แท่ง M15) + Divergence + AI ≥ 55% · H1 MA100/150/200 ไม่เรียงตามทิศ · ไม่ใช้ตัวกรองเทรนด์ H4 · เลื่อน SL ทุก 5 จุด"),
         9: ("Plan 9", "Fib-H1-Counter", "Fibonacci คลื่น H1 ≥ 3 ATR สวนเทรนด์ใหญ่ H1 MA100/150/200 · เข้า 0.3 · ADX > 20 + MACD ยังไม่หันตามทิศไม้ · SL 0 · TP 1.75 · เลื่อน SL ขั้นบันได (1→0.15 · 1.27→0.6 · 1.5→1)"),
         10: ("Plan 10", "RSI-H1-Trend", "RSI(14) H1 แตะ 30/70 ตามเทรนด์ MA200 (ซื้อ Oversold ในขาขึ้น / ขาย Overbought ในขาลง) · SL 2 ATR · TP 3 ATR · ถือไม่เกิน 48 ชม."),
         12: ("Plan 12", "DoubleTop-H1", "BB H1 ทำยอดซ้ำนอกกรอบตามเทรนด์ H4 MA10/30: ทะลุ BB → ย่อ → ทำยอดใหม่ → แท่งถัดไปปิดสวน = เข้า · SL ยอดใหม่ ± 0.1 ATR · ปิดทุกไม้เมื่อแตะ BB อีกฝั่ง · ไม้เพิ่มสูงสุด 2 ไม้ (ยอดต่ำกว่าเดิมแต่อยู่นอกเส้นกลาง)"),
         11: ("Plan 11", "News-USD", "ข่าว USD: คาดเทียบครั้งก่อนบอกแนวโน้มทอง → ค่าจริงไม่สวน = ยืนยัน → เข้าทันที (Tick จริง เข้า 10 วิหลังข่าว) · ข่าวพร้อมกันหักกลบ Lot ≤ 3 เท่า · SL 3 ATR M15 · ไม่ตั้ง TP · ถือ 8 ชม.")}
plans_out, events = [], []
for k in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
    tr = ALL[k]
    st = stats(NAMES[k][1], tr)
    df_t = pd.DataFrame(tr)
    monthly, monthly_n, monthly_w = {}, {}, {}
    if len(df_t):
        df_t["month"] = pd.to_datetime(df_t.time).dt.strftime("%Y-%m")
        gm = df_t.groupby("month").pnl
        monthly = {m: round(float(v), 1) for m, v in gm.sum().items()}
        monthly_n = {m: int(v) for m, v in gm.size().items()}                     # จำนวนไม้รายเดือน
        monthly_w = {m: int(v) for m, v in gm.apply(lambda x: int((x > 0).sum())).items()}   # ไม้ชนะรายเดือน (หน้าเว็บคิด % ชนะ)
        for x in tr:
            events.append((pd.Timestamp(x["time"]), k, float(x["pnl"])))
    plans_out.append(dict(key=k, label=NAMES[k][0], name=NAMES[k][1], rule=NAMES[k][2], **{kk: (None if (isinstance(v, float) and np.isnan(v)) else v) for kk, v in st.items() if kk != "plan"}, monthly=monthly, monthly_n=monthly_n, monthly_w=monthly_w))
events.sort(key=lambda e: e[0])
eq, curve, cum = {}, [], {k: 0.0 for k in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)}
total = 0.0
for t, k, pnl in events:
    cum[k] += pnl; total += pnl
    eq[t.strftime("%Y-%m-%d")] = (round(total, 1), {str(kk): round(v, 1) for kk, v in cum.items()})
curve = [dict(date=d, total=v[0], plans=v[1]) for d, v in eq.items()]
tt = np.array([e[2] for e in events])
eqv = np.r_[0.0, np.cumsum(tt)]   # DD พอร์ตรวมนับจากจุดเริ่ม (0)
summary = dict(net=round(float(tt.sum()), 1), trades=int(len(tt)), win=round(float((tt > 0).mean() * 100), 1) if len(tt) else 0,
               pf=round(float(tt[tt > 0].sum() / -tt[tt < 0].sum()), 2) if (tt < 0).any() else None,
               maxdd=round(float(np.max(np.maximum.accumulate(eqv) - eqv)), 1))
out = dict(generated_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), app_version=APP_VERSION, symbol="XAUUSD",
           period=[curve[0]["date"] if curve else str(b.time.iloc[0])[:10], str(b.time.iloc[-1])[:10]], lot=0.01, spread_points=SPREAD,
           summary=summary, plans=plans_out, equity=curve,
           assumptions=["ข้อมูลราคา XAUUSD จริงจาก MT5 (M15/H1/H4) ใช้แท่งที่ปิดแล้ว เข้าไม้ที่ราคาเปิดแท่งถัดไป · Multi-Timeframe S&R 1,000 แท่ง H1 + H4 Confluence",
                        "หักสเปรด 0.35 จุดต่อไม้ · 1 จุด ≈ $1 ที่ 0.01 lot",
                        "AI (Plan 3–5, 7–8) จำลองแบบ Walk-forward: เทรนด้วยอดีต 5,000 แท่ง แล้วทายช่วงถัดไปที่ไม่เคยเห็น",
                        "จำลองแยกทีละแผน 1 ไม้ต่อแผน · ไม่รวม Cooldown / Circuit Breaker / Loss Block",
                        "ผลในอดีตไม่ได้รับประกันผลในอนาคต"])
dst = os.path.join(ROOT, "web", "public", "backtest.json")
with open(dst, "w", encoding="utf-8") as fp:
    json.dump(out, fp, ensure_ascii=False)
print("saved", dst, "equity points", len(curve))
