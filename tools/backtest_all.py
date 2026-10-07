"""Backtest ทุกแผนตามกฎปัจจุบัน บนข้อมูล MT5 จริง (XAUUSD) แล้วบันทึกผลเป็น web/public/backtest.json ให้หน้า /backtest
วิธีใช้: เปิด MT5 ค้างไว้ แล้วรัน  python tools/backtest_all.py  (ประมาณ 3–4 นาที) จากนั้น deploy เว็บ
P1 MA M15 · P2 MA H1 · P3 SMC · P4 SR-Bounce · P5 BB-H1
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
# แนวรับ/ต้าน 500 แท่ง ณ แท่ง H1 ที่ปิด
sup, res = np.full(len(h1), np.nan), np.full(len(h1), np.nan)
for i in range(520, len(h1)):
    r = bot.find_sr_levels(h1.iloc[i - 501:i + 2] if i + 2 <= len(h1) else pd.concat([h1.iloc[i - 501:i + 1], h1.iloc[[i]]]), float(h1.close.iloc[i]))
    sup[i], res[i] = r["support"], r["resistance"]
hx["sup"], hx["res"] = sup, res
print(f"H1 S/R done {time.time() - t0:.0f}s", flush=True)

# H4 regime (MA10/30, ±0.20%) + H4 stack
vx = pd.DataFrame({"avail": h4.time + pd.Timedelta(minutes=240)})
f10, f30 = h4.close.rolling(10).mean(), h4.close.rolling(30).mean()
vx["h4_up"] = (f10 > f30).astype(float)
vx["h4_side"] = ((f10 / f30 - 1).abs() * 100 < 0.20).astype(float)
t100, t150, t200 = (h4.close.rolling(k).mean() for k in (100, 150, 200))
vx["h4_stack"] = np.where((t100 < t150) & (t150 < t200), -1, np.where((t100 > t150) & (t150 > t200), 1, 0))
_m5 = h4.close.rolling(5).mean(); _a4 = A(h4); _sl5 = (_m5 - _m5.shift(2)) / _a4; _up = f10 > f30
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
    eq = np.cumsum(t); dd = float(np.max(np.maximum.accumulate(eq) - eq))
    w, ls = t[t > 0].sum(), -t[t < 0].sum()
    last = t[-100:]
    return dict(plan=name, n=len(t), win=round((t > 0).mean() * 100, 1), net=round(t.sum(), 1), pf=round(w / ls, 2) if ls else 0,
                maxdd=round(dd, 1), avg=round(t.mean(), 2), half1=round(t[:len(t) // 2].sum(), 1), half2=round(t[len(t) // 2:].sum(), 1),
                last100_net=round(last.sum(), 1), last100_win=round((last > 0).mean() * 100, 1))


def sim_ma(frame, fast, slow, trend_col, atr_col="atr", step=5.0, frac=0.4, entry_ok=None, sl_mult=0.75, trail="sl", first_frac=None, exit_slow=None):
    """step=None → ไม่เลื่อน SL · entry_ok(i, d) = ตัวกรองเพิ่มเติมก่อนเข้าไม้
    trail="sl": เลื่อน frac ของระยะ SL → ราคาของขั้น · trail="entry": เลื่อน (first_frac ขั้นแรก / frac ขั้นถัดไป) ของระยะ ราคาเข้า → ราคาของขั้น"""
    o, h, l, a, t = frame.open.values, frame.high.values, frame.low.values, frame[atr_col].values, frame.time.values
    mf, ms, td = frame[fast].values, frame[slow].values, frame[trend_col].values
    mx = frame[exit_slow].values if exit_slow else ms   # เส้นที่ใช้ออกไม้ (ค่าเริ่มต้น = เส้นเดียวกับตอนเข้า)
    out, pos = [], None
    for i in range(3, len(frame) - 1):
        up = mf[i - 1] <= ms[i - 1] and mf[i] > ms[i]
        dn = mf[i - 1] >= ms[i - 1] and mf[i] < ms[i]
        xup = mf[i - 1] <= mx[i - 1] and mf[i] > mx[i]
        xdn = mf[i - 1] >= mx[i - 1] and mf[i] < mx[i]
        if pos:
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
                e = o[i + 1]
                pos = (d, e, e - d * sl_mult * a[i], 1, t[i + 1])
    return out


def sim_ai_plan(signal_fn, step=None, frac=0.4, first_frac=None, slm=0.75, tpm=1.125):
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
        if d and h4_ok(i, d):
            e = o[i + 1]; at = a[i]
            pos = (d, e, e - d * slm * at, e + d * tpm * at, at, False, t[i + 1], 1)
    return out


V = {k: b[k].values for k in ("h1_stack", "low", "high", "close", "open", "atr", "lw", "uw", "sup", "res", "h1_up", "p_up", "bb_lo", "bb_up",
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
    if c >= s and c - s <= 0.75 * a and bdiv and (V["lw"][i] >= 0.20 or c > V["open"][i]) and V["h1_stack"][i] != -1 and pu >= 0.55:
        return 1
    if c <= r and r - c <= 0.75 * a and sdiv and (V["uw"][i] >= 0.20 or c < V["open"][i]) and V["h1_stack"][i] != 1 and (1 - pu) >= 0.55:
        return -1
    return 0


def sig_bb(i):
    lo, upb, c = V["bb_lo"][i], V["bb_up"][i], V["close"][i]
    if np.isnan(lo) or np.isnan(V["macd_h_prev"][i]):
        return 0
    pu = V["p_up"][i]
    if V["low"][i] < lo <= c and V["lw"][i] >= 0.20 and (V["bull_div"][i] or V["hidden_bull"][i]) and pu >= 0.55:
        return 1
    if V["high"][i] > upb >= c and V["uw"][i] >= 0.20 and (V["bear_div"][i] or V["hidden_bear"][i]) and (1 - pu) >= 0.55:
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
                                                trail="sl", first_frac=0.50, frac=0.40))))
f = h1.copy(); f["close_time"] = f.time + pd.Timedelta(minutes=60)
f["atr"] = A(f); f["ma5"], f["ma10"], f["ma20"] = f.close.rolling(5).mean(), f.close.rolling(10).mean(), f.close.rolling(20).mean()
f = pd.merge_asof(f.sort_values("close_time"), vx[["avail", "p2_dir"]], left_on="close_time", right_on="avail", direction="backward").reset_index(drop=True)
rows.append(stats("P2 MA H1", keep(2, sim_ma(f, "ma5", "ma10", "p2_dir", step=None, sl_mult=1.25, exit_slow="ma20"))))
rows.append(stats("P3 SMC", keep(3, sim_ai_plan(sig_smc, step=5.0, frac=0.4, first_frac=0.5, slm=1.0, tpm=2.0))))
rows.append(stats("P4 SR-Bounce", keep(4, sim_ai_plan(sig_bounce, step=5.0, frac=0.4, first_frac=0.5, slm=1.0, tpm=2.0))))
rows.append(stats("P5 BB-H1", keep(5, sim_ai_plan(sig_bb, step=5.0, frac=0.4, first_frac=0.5))))
pd.set_option("display.width", 220)
print(f"ช่วงข้อมูล {b.time.iloc[0]} → {b.time.iloc[-1]} · ใช้เวลา {time.time() - t0:.0f}s")
print(pd.DataFrame(rows).to_string(index=False))


# ---------------------------------------------------------------- JSON สำหรับหน้าเว็บ /backtest
from version import APP_VERSION  # noqa: E402
NAMES = {1: ("Plan 1", "MA-Cross-Trend", "MA5×MA13 M15 · H1 MA100/150/200 · กรอง RSI + MA50 · เลื่อน SL ทุก 5 จุด (ขั้นแรก 50% / ถัดไป 40%)"),
         2: ("Plan 2", "MA-Cross-H1-Trend", "MA5×MA10 H1 · H4 MA10/30 + MA200 · SL 1.25 ATR · ออกเมื่อ MA5 ตัด MA20"),
         3: ("Plan 3", "SMC-LiquidityHunt", "กวาดแนวรับ/ต้าน H1 (ไส้ 0.4–1.0 ATR) + MA100/150/200 H1 + AI · SL 1.0 / TP 2.0 ATR · เลื่อน SL 50%/40%"),
         4: ("Plan 4", "SR-SwingBounce", "เด้งแนวรับ/ต้าน H1 (≤ 0.75 ATR) + Divergence + MA100/150/200 ไม่สวน + AI ≥ 55% · SL 1.0 / TP 2.0 ATR"),
         5: ("Plan 5", "BB-H1-Reversion", "หลุดกรอบ BB H1 + Divergence + AI ≥ 55% · เลื่อน SL ทุก 5 จุด (50%/40%)")}
plans_out, events = [], []
for k in (1, 2, 3, 4, 5):
    tr = ALL[k]
    st = stats(NAMES[k][1], tr)
    df_t = pd.DataFrame(tr)
    monthly = {}
    if len(df_t):
        df_t["month"] = pd.to_datetime(df_t.time).dt.strftime("%Y-%m")
        monthly = {m: round(float(v), 1) for m, v in df_t.groupby("month").pnl.sum().items()}
        for x in tr:
            events.append((pd.Timestamp(x["time"]), k, float(x["pnl"])))
    plans_out.append(dict(key=k, label=NAMES[k][0], name=NAMES[k][1], rule=NAMES[k][2], **{kk: (None if (isinstance(v, float) and np.isnan(v)) else v) for kk, v in st.items() if kk != "plan"}, monthly=monthly))
events.sort(key=lambda e: e[0])
eq, curve, cum = {}, [], {k: 0.0 for k in (1, 2, 3, 4, 5)}
total = 0.0
for t, k, pnl in events:
    cum[k] += pnl; total += pnl
    eq[t.strftime("%Y-%m-%d")] = (round(total, 1), {str(kk): round(v, 1) for kk, v in cum.items()})
curve = [dict(date=d, total=v[0], plans=v[1]) for d, v in eq.items()]
tt = np.array([e[2] for e in events])
eqv = np.cumsum(tt) if len(tt) else np.array([0.0])
summary = dict(net=round(float(tt.sum()), 1), trades=int(len(tt)), win=round(float((tt > 0).mean() * 100), 1) if len(tt) else 0,
               pf=round(float(tt[tt > 0].sum() / -tt[tt < 0].sum()), 2) if (tt < 0).any() else None,
               maxdd=round(float(np.max(np.maximum.accumulate(eqv) - eqv)), 1))
out = dict(generated_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), app_version=APP_VERSION, symbol="XAUUSD",
           period=[curve[0]["date"] if curve else str(b.time.iloc[0])[:10], str(b.time.iloc[-1])[:10]], lot=0.01, spread_points=SPREAD,
           summary=summary, plans=plans_out, equity=curve,
           assumptions=["ข้อมูลราคา XAUUSD จริงจาก MT5 (M15/H1/H4) ใช้แท่งที่ปิดแล้ว เข้าไม้ที่ราคาเปิดแท่งถัดไป",
                        "หักสเปรด 0.35 จุดต่อไม้ · 1 จุด ≈ $1 ที่ 0.01 lot",
                        "AI (Plan 3–5) จำลองแบบ Walk-forward: เทรนด้วยอดีต 5,000 แท่ง แล้วทายช่วงถัดไปที่ไม่เคยเห็น",
                        "จำลองแยกทีละแผน 1 ไม้ต่อแผน · ไม่รวม Cooldown / Circuit Breaker / Loss Block",
                        "ผลในอดีตไม่ได้รับประกันผลในอนาคต"])
dst = os.path.join(ROOT, "web", "public", "backtest.json")
with open(dst, "w", encoding="utf-8") as fp:
    json.dump(out, fp, ensure_ascii=False)
print("saved", dst, "equity points", len(curve))
