"""
ข้อมูลหน้าต่าง "รายละเอียดไม้"
- get(ticket)        : ไม้ที่เปิดอยู่ (คลิกแถวในแท็บออเดอร์ที่เปิดอยู่) — แท่งสุดท้ายใช้ราคา Bid ล่าสุด · เรียกทุก 1 วินาที
- get_closed(trade)  : ไม้ที่ปิดแล้ว (คลิกแถวในประวัติการเทรด) — ภาพ ณ ตอนปิดไม้: แท่ง M15 ถึงแท่งที่ปิด (ตัดที่เวลาปิดจริง),
                       SL/TP ตอนปิด, เส้นทางการเลื่อน SL/TP, กำไรสูงสุด/ติดลบสูงสุดระหว่างถือ
ทั้งสองแบบแสดงเส้นอินดิเคเตอร์ที่แผนของไม้นั้นใช้จริง + ค่าที่แผนใช้ตัดสินใจ (เทียบกับทิศของไม้)
ข้อมูล H1/H4 ของไม้ที่เปิดอยู่แคชไว้ 15 วินาที
"""
import csv
import math
import re
import time

import MetaTrader5 as mt5
import pandas as pd

import multi_asset_ai_bot as bot
import thai_time

SYMBOL = "XAUUSD"
CTX_TTL = 15
WARMUP = 220   # แท่งเผื่อคำนวณ MA50 / RSI / Divergence ให้ครบตั้งแต่แท่งแรกที่แสดง
_ctx = {"t": 0.0, "data": None}

PLANS = (  # (ขึ้นต้น comment, key, ชื่อสั้น) — MA-Cross-H1 ต้องมาก่อน MA-Cross-Trend
    ("MA-Cross-H1", "P2", "P2 · MA H1"),
    ("MA-Cross-Trend", "P1", "P1 · MA M15"),
    ("SMC", "P3", "P3 · SMC Hunt"),
    ("SR-Swing", "P4", "P4 · SR Bounce"),
    ("BB-H1", "P5", "P5 · BB-H1"),
    ("PSAR", "P6", "P6 · SAR H1"),
)


def plan_of(comment):
    c = comment or ""
    for prefix, key, name in PLANS:
        if c.startswith(prefix):
            return key, name
    return "M", ("เข้าไม้เอง" if c.startswith("Manual") or not c else c)


def _f(v):
    try:
        v = float(v)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def _server_offset(server_ts=None):
    """เวลาเซิร์ฟเวอร์ MT5 − เวลาจริง (วินาที) ณ เวลานั้น — ใช้ thai_time (ตลาดปิด/tick เก่าก็ยังถูก)"""
    return thai_time.server_offset_at(server_ts)


def _rates_df(rates):
    """rates ของ MT5 → DataFrame แบบเดียวกับ bot.get_data (คอลัมน์ time เป็น datetime)"""
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df


def _set_last(df, price):
    """แทนแท่งสุดท้าย (แท่งที่กำลังวิ่ง/แท่งที่ปิดไม้) ด้วยราคา ณ เวลานั้น"""
    i = df.index[-1]
    df.loc[i, "close"] = float(price)
    df.loc[i, "high"] = max(float(df.loc[i, "high"]), float(price))
    df.loc[i, "low"] = min(float(df.loc[i, "low"]), float(price))


def _context_from(h1, h4, price):
    """ค่าจาก H1/H4 (แท่งปิด) ที่แผนใช้ — h1/h4 = แท่งจนถึงเวลาที่ต้องการ (แท่งสุดท้าย = แท่งที่ยังไม่ปิด)"""
    if h1 is None or h4 is None or len(h1) < 60 or len(h4) < 40:
        return None
    c1, c4 = h1["close"], h4["close"]
    h1s = pd.DataFrame({"time": h1["time"]})
    h1s["ma5"], h1s["ma10"], h1s["ma20"] = c1.rolling(5).mean(), c1.rolling(10).mean(), c1.rolling(20).mean()
    mid, sd = c1.shift(1).rolling(20).mean(), c1.shift(1).rolling(20).std()   # เหมือนบอท: Shift 1 ไม่ Repaint
    h1s["bb_mid"], h1s["bb_up"], h1s["bb_lo"] = mid, mid + 2 * sd, mid - 2 * sd
    macd = c1.ewm(span=12, adjust=False).mean() - c1.ewm(span=26, adjust=False).mean()
    h1s["macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    h1s["sar"], sdir = bot.psar_series(h1["high"].values, h1["low"].values, *bot.P6_SAR)
    h1s["sar_fast"], fdir = bot.psar_series(h1["high"].values, h1["low"].values, *bot.P6_SAR_FAST)
    h1s["ema100"] = c1.ewm(span=bot.P6_EXIT_EMA, adjust=False).mean()
    atr_h1, atr_h4 = bot._atr_series(h1), bot._atr_series(h4)
    d = {"h1s": h1s.set_index("time"), "atr_h1": _f(atr_h1.iloc[-2])}
    _, d["h1_diff"], d["h1_dir"] = bot.closed_trend(c1.rolling(10).mean(), c1.rolling(30).mean(), atr=atr_h1)
    d["h4_up"], d["h4_diff"], d["h4_dir"] = bot.closed_trend(c4.rolling(10).mean(), c4.rolling(30).mean(), atr=atr_h4)
    ma5_4 = c4.rolling(5).mean()
    a4 = _f(atr_h4.iloc[-2])
    d["h4_slope"] = _f((ma5_4.iloc[-2] - ma5_4.iloc[-4]) / a4) if a4 else None
    d["h4_lt_dir"], d["h4_ma200"] = bot.long_term_dir(c4)
    d["h4_close"] = _f(c4.iloc[-2])
    st = [_f(c1.rolling(n).mean().iloc[-2]) for n in (100, 150, 200)]
    d["h1_stack"] = st
    d["h1_stack_dir"] = 0 if None in st else (-1 if st[0] < st[1] < st[2] else (1 if st[0] > st[1] > st[2] else 0))
    d["h1_ma5"], d["h1_ma10"], d["h1_ma20"] = _f(h1s["ma5"].iloc[-2]), _f(h1s["ma10"].iloc[-2]), _f(h1s["ma20"].iloc[-2])
    d["macd_now"], d["macd_prev"] = _f(h1s["macd_hist"].iloc[-2]), _f(h1s["macd_hist"].iloc[-3])
    d["p6_sar"], d["p6_dir"] = _f(h1s["sar"].iloc[-2]), int(sdir[-2])
    d["p6_sar_fast"], d["p6_dir_fast"] = _f(h1s["sar_fast"].iloc[-2]), int(fdir[-2])
    d["h1_ema100"], d["h1_close"] = _f(h1s["ema100"].iloc[-2]), _f(c1.iloc[-2])
    _t4 = 1 if c4.rolling(10).mean().iloc[-2] > c4.rolling(30).mean().iloc[-2] else -1
    _l4 = 1 if c4.iloc[-2] > c4.rolling(200).mean().iloc[-2] else -1
    d["p6_trend"] = _t4 if _t4 == _l4 else 0
    sr = bot.find_sr_levels(h1, float(price))
    d["sup"], d["res"] = _f(sr["support"]), _f(sr["resistance"])
    d["sup_t"], d["res_t"] = int(sr["sup_touches"]), int(sr["res_touches"])
    return d


def _context():
    """บริบท H1/H4 ปัจจุบัน — แคช 15 วินาที"""
    now = time.time()
    if _ctx["data"] is not None and now - _ctx["t"] < CTX_TTL:
        return _ctx["data"]
    h1 = bot.get_data(SYMBOL, mt5.TIMEFRAME_H1, 620)
    h4 = bot.get_data(SYMBOL, mt5.TIMEFRAME_H4, 320)
    d = _context_from(h1, h4, float(h1["close"].iloc[-1])) if h1 is not None else None
    if d is not None:
        _ctx.update(t=now, data=d)
    return d


def _m15_frame(rates, last_price):
    """แท่ง M15 + MA5/13/50, RSI(14), ATR(14) — แท่งสุดท้ายแทนด้วย last_price"""
    m = pd.DataFrame(rates)
    _set_last(m, last_price)
    c = m["close"]
    m["ma5"], m["ma13"], m["ma50"] = c.rolling(5).mean(), c.rolling(13).mean(), c.rolling(50).mean()
    dl = c.diff()
    g, l_ = dl.where(dl > 0, 0).rolling(14).mean(), (-dl.where(dl < 0, 0)).rolling(14).mean()
    m["rsi"] = 100 - 100 / (1 + g / (l_ + 1e-9))
    m["atr"] = bot._atr_series(m)
    return m


def _map_h1(m, ctx):
    """วางค่า H1 (MA5/10, BB, MACD) ลงแท่ง M15 ตามชั่วโมงของแท่ง"""
    if ctx is None:
        return
    hkey = pd.to_datetime(m["time"], unit="s").dt.floor("h")
    for col in ("ma5", "ma10", "ma20", "bb_up", "bb_mid", "bb_lo", "macd_hist", "sar", "ema100"):
        m["h1_" + col] = hkey.map(ctx["h1s"][col]).astype(float)


def _money_per_pt(lot):
    info = mt5.symbol_info(SYMBOL)
    if info and info.trade_tick_size:
        return float(info.trade_tick_value) / float(info.trade_tick_size) * float(lot or 0.01)
    return 100.0 * float(lot or 0.01)


def _ind(name, value, d=0, note=""):
    return {"name": name, "value": value, "dir": int(d), "note": note}


def _agree(x, side):
    """x>0 = หนุนขึ้น → เทียบกับทิศของไม้: +1 หนุน / -1 สวน / 0 กลาง"""
    if x is None or x == 0:
        return 0
    return 1 if (x > 0) == (side > 0) else -1


def _fmt(v, nd=2):
    return "—" if v is None else f"{v:,.{nd}f}"


def _build(m, ctx, pos, side, comment, count, live=True, mfe=None):
    """เส้นบนกราฟ + ค่าที่แผนใช้ ณ แท่งสุดท้ายของ m (แท่งที่กำลังวิ่ง หรือแท่งที่ปิดไม้)"""
    plan_key, plan_name = plan_of(comment)
    tail = m.iloc[-count:]

    def ser(col):
        if col not in tail:
            return [None] * len(tail)
        return [None if pd.isna(v) else round(float(v), 3) for v in tail[col]]

    candles = [{"time": int(r.time), "open": float(r.open), "high": float(r.high), "low": float(r.low), "close": float(r.close)}
               for r in tail.itertuples()]

    # ---- เส้นบนกราฟ / แนวราคา / หน้าต่างย่อย ตามแผน ----
    lines, levels, pane = [], [], None
    cb = m.iloc[-2]   # แท่ง M15 ที่ปิดแล้วล่าสุด (แผนตัดสินจากแท่งนี้)
    atr = _f(cb["atr"])
    if plan_key in ("P1", "M"):
        lines = [{"label": "MA5", "style": "fast", "values": ser("ma5")},
                 {"label": "MA13", "style": "slow", "values": ser("ma13")}]
        if plan_key == "P1":
            lines.append({"label": "MA50", "style": "ma50", "values": ser("ma50")})
        pane = {"kind": "rsi", "label": "RSI(14) M15", "values": ser("rsi"),
                "band": ((50, 70) if side > 0 else (30, 50)) if plan_key == "P1" else None}
    elif plan_key == "P2":
        lines = [{"label": "MA5 H1", "style": "fast", "values": ser("h1_ma5")},
                 {"label": "MA10 H1", "style": "slow", "values": ser("h1_ma10")},
                 {"label": "MA20 H1 (ออก)", "style": "ma50", "values": ser("h1_ma20")}]
    elif plan_key == "P6":
        lines = [{"label": "SAR H1", "style": "fast", "values": ser("h1_sar")},
                 {"label": "EMA100 H1 (ออก)", "style": "ma50", "values": ser("h1_ema100")}]
    elif plan_key == "P5":
        lines = [{"label": "BB บน H1", "style": "band", "values": ser("h1_bb_up")},
                 {"label": "BB กลาง H1", "style": "mid", "values": ser("h1_bb_mid")},
                 {"label": "BB ล่าง H1", "style": "band", "values": ser("h1_bb_lo")}]
        pane = {"kind": "hist", "label": "MACD Histogram H1", "values": ser("h1_macd_hist")}
    if plan_key in ("P3", "P4") and ctx:
        if ctx["res"]:
            levels.append({"label": f"แนวต้าน H1 {ctx['res']:,.2f}", "price": ctx["res"], "style": "res"})
        if ctx["sup"]:
            levels.append({"label": f"แนวรับ H1 {ctx['sup']:,.2f}", "price": ctx["sup"], "style": "sup"})
        if plan_key == "P4":
            pane = {"kind": "rsi", "label": "RSI(14) M15 · ใช้หา Divergence", "values": ser("rsi"), "band": None}

    # ---- ค่าที่แผนใช้ ----
    inds = []
    close_c = _f(cb["close"])
    ma5c, ma13c, ma50c, rsic = _f(cb["ma5"]), _f(cb["ma13"]), _f(cb["ma50"]), _f(cb["rsi"])
    price = pos["price"] if pos else float(m["close"].iloc[-1])
    entry = pos["entry"] if pos else None

    def step_trail():
        if not pos:
            return
        step = bot.P4_TRAIL_STEP_POINTS
        rule = (f"ทุก +{step:g} จุด เลื่อน SL {bot.TRAIL_FIRST_FRACTION:.0%} (ขั้นแรก) / {bot.P4_TRAIL_FRACTION:.0%} (ขั้นถัดไป)"
                " ของระยะ SL → ราคา")
        if live:
            gain = (price - entry) * side
            k = int(gain // step) if gain > 0 else 0
            nk, npx, sl = k + 1, entry + side * (k + 1) * step, pos["sl"]
            fr = bot.TRAIL_FIRST_FRACTION if nk == 1 else bot.P4_TRAIL_FRACTION
            nsl = sl + side * fr * abs(npx - sl)
            inds.append(_ind("เลื่อน SL ขั้นบันได", f"ผ่านแล้ว {k} ขั้น", 1 if k else 0,
                             f"{rule} · ขั้นถัดไปเมื่อราคาถึง {npx:,.2f} → SL {nsl:,.2f}" if sl > 0 else rule))
        elif mfe is not None:
            k = int(mfe // step) if mfe > 0 else 0
            inds.append(_ind("เลื่อน SL ขั้นบันได", f"ผ่าน {k} ขั้นระหว่างถือ", 1 if k else 0,
                             f"{rule} · กำไรสูงสุดระหว่างถือ {mfe:,.2f} จุด"))

    def tp_progress():
        if not pos or pos["tp"] <= 0:
            return
        target = abs(pos["tp"] - entry)
        pct = (price - entry) * side / target * 100 if target else 0
        inds.append(_ind("ความคืบหน้าสู่ TP" + ("" if live else " ตอนปิด"), f"{pct:.0f}%", 1 if pct >= 70 else (0 if pct >= 0 else -1),
                         "ถึง 70% บอทล็อกกำไร +0.35 ATR · ถึง 80% และ AI ยืนยัน ขยาย TP อีก 1 ATR"))

    def ai_prob():
        if not live:   # ไม่มีบันทึกค่า AI ย้อนหลัง
            return
        up = _f((bot.latest_radar_cache.get(SYMBOL) or {}).get("up_prob"))
        if up is None:
            inds.append(_ind("AI (โมเดลของบอท)", "—", 0, "เริ่มบอทเพื่อให้ AI คำนวณ"))
            return
        pr = up if side > 0 else 1 - up
        inds.append(_ind("AI (โมเดลของบอท)", f"{'ขึ้น' if side > 0 else 'ลง'} {pr:.0%}", 1 if pr > 0.5 else (-1 if pr < 0.5 else 0),
                         "ใช้ยืนยันตอนเข้าไม้ (≥ 50%) · กลับทิศ ≥ 60% และราคาย้อนผ่านจุดเข้า → บอทปิดไม้"))

    def divergence():
        try:
            dv = bot.add_divergence_features(m[["open", "high", "low", "close", "rsi"]].copy(), lookback=14)
            names = {"bull_div": ("Bullish Divergence", 1), "hidden_bull": ("Hidden Bullish", 1),
                     "bear_div": ("Bearish Divergence", -1), "hidden_bear": ("Hidden Bearish", -1)}
            found = [(n, s) for col, (n, s) in names.items() if dv[col].iloc[-3:].max() > 0.5]
            if found:
                n, s = found[0]
                inds.append(_ind("RSI Divergence (M15)", n, _agree(s, side), "พบใน 3 แท่งล่าสุด"))
            else:
                inds.append(_ind("RSI Divergence (M15)", "ไม่พบ", 0, "ใช้ยืนยันตอนเข้าไม้"))
        except Exception:
            pass

    exit_word = "บอทปิดไม้" if live else "ตรงกับจังหวะที่ปิด"
    if plan_key in ("P1", "M"):
        if ma5c is not None and ma13c is not None:
            dd = _agree(ma5c - ma13c, side)
            inds.append(_ind("MA5 / MA13 (M15 แท่งปิด)", f"{ma5c:,.2f} / {ma13c:,.2f}", dd,
                             ("ยังไม่ตัดกลับ — ถือตามแผน" if dd > 0 else f"ตัดกลับแล้ว = สัญญาณออก ({exit_word})") if plan_key == "P1" else ""))
        if rsic is not None:
            inds.append(_ind("RSI(14) M15", f"{rsic:.1f}", _agree(rsic - 50, side),
                             "เกณฑ์ตอนเข้า: BUY 50–70 · SELL 30–50" if plan_key == "P1" else "เหนือ 50 = แรงซื้อ · ใต้ 50 = แรงขาย"))
    if plan_key == "P1":
        if ma50c is not None and close_c is not None:
            inds.append(_ind("ราคาปิด vs MA50 M15", f"{close_c:,.2f} / {ma50c:,.2f}", _agree(close_c - ma50c, side),
                             "BUY ต้องอยู่เหนือ · SELL ต้องอยู่ใต้"))
        if ctx:
            s = ctx["h1_stack"]
            word = {1: "เรียงขึ้น", -1: "เรียงลง", 0: "ไม่เรียง"}[ctx["h1_stack_dir"]]
            inds.append(_ind("H1 MA100 / 150 / 200", f"{word}", _agree(ctx["h1_stack_dir"], side),
                             " / ".join(_fmt(v) for v in s)))
        step_trail()
    elif plan_key == "P2" and ctx:
        inds.append(_ind("MA5 / MA10 (H1 แท่งปิด)", f"{_fmt(ctx['h1_ma5'])} / {_fmt(ctx['h1_ma10'])}",
                         _agree((ctx["h1_ma5"] or 0) - (ctx["h1_ma10"] or 0), side), "ใช้ตอนเข้าไม้ (MA5 ตัด MA10)"))
        dd = _agree((ctx["h1_ma5"] or 0) - (ctx["h1_ma20"] or 0), side)
        inds.append(_ind("MA5 / MA20 (H1 แท่งปิด)", f"{_fmt(ctx['h1_ma5'])} / {_fmt(ctx['h1_ma20'])}", dd,
                         "MA5 อยู่ฝั่งไม้ — ถือตามแผน" if dd > 0 else f"MA5 อยู่ผิดฝั่ง MA20 · ออกเมื่อ MA5 ตัด MA20 กลับ ({exit_word})"))
        inds.append(_ind("H4 MA10 vs MA30", f"{ctx['h4_diff']:+.2f}%", _agree(ctx["h4_diff"], side), "ต้องตรงทิศตอนเข้า (Strict Pro-Trend)"))
        if ctx["h4_slope"] is not None:
            inds.append(_ind("ความชัน MA5 H4 (2 แท่ง)", f"{ctx['h4_slope']:+.2f} ATR", _agree(ctx["h4_slope"], side), ""))
        if ctx["h4_ma200"] and ctx["h4_close"]:
            inds.append(_ind("ราคาปิด H4 vs MA200", f"{ctx['h4_close']:,.2f} / {ctx['h4_ma200']:,.2f}",
                             _agree(ctx["h4_close"] - ctx["h4_ma200"], side), ""))
        if ctx["atr_h1"]:
            inds.append(_ind("ATR(14) H1", f"{ctx['atr_h1']:,.2f}", 0, "SL = 1.25 ATR H1 · ไม่ตั้ง TP · ไม่เลื่อน SL"))
    elif plan_key in ("P3", "P4") and ctx:
        if ctx["sup"] and ctx["res"]:
            inds.append(_ind("แนวรับ / แนวต้าน H1", f"{ctx['sup']:,.2f} / {ctx['res']:,.2f}", 0,
                             f"แตะ {ctx['sup_t']} / {ctx['res_t']} ครั้ง · ห่างราคา {price - ctx['sup']:,.2f} / {ctx['res'] - price:,.2f} จุด"))
        if plan_key == "P3":
            inds.append(_ind("เทรนด์ H1 (MA10/30)", f"{ctx['h1_diff']:+.2f}%", _agree(ctx["h1_dir"], side), "ต้องตรงทิศตอนเข้า"))
            word = {1: "เรียงขึ้น", -1: "เรียงลง", 0: "ไม่เรียง"}[ctx["h1_stack_dir"]]
            inds.append(_ind("H1 MA100 / 150 / 200", word, _agree(ctx["h1_stack_dir"], side), "ต้องเรียงตามทิศตอนเข้า · SL 1.0 ATR · TP 2.0 ATR"))
            lw = _f((float(min(cb["open"], cb["close"])) - float(cb["low"])) / atr) if atr else None
            uw = _f((float(cb["high"]) - float(max(cb["open"], cb["close"]))) / atr) if atr else None
            if lw is not None and uw is not None:
                inds.append(_ind("ไส้เทียนแท่งปิดล่าสุด", f"ล่าง {lw:.2f} · บน {uw:.2f} ATR", 0, "ตอนเข้าต้อง 0.40–1.00 ATR ฝั่งที่กวาด"))
        else:
            word = {1: "เรียงขึ้น", -1: "เรียงลง", 0: "ไม่เรียง"}[ctx["h1_stack_dir"]]
            inds.append(_ind("H1 MA100 / 150 / 200", word, -1 if ctx["h1_stack_dir"] == -side else (1 if ctx["h1_stack_dir"] == side else 0),
                             "ห้ามเรียงสวนทิศตอนเข้า · ห่างแนว ≤ 0.75 ATR · AI ≥ 55% · SL 1.0 / TP 2.0 ATR"))
            if rsic is not None:
                inds.append(_ind("RSI(14) M15", f"{rsic:.1f}", _agree(rsic - 50, side), ""))
            divergence()
        ai_prob()
        step_trail()
        tp_progress()
    elif plan_key == "P5":
        if ctx:
            hb = m.iloc[-1]
            inds.append(_ind("Bollinger H1 บน / กลาง / ล่าง",
                             f"{_fmt(_f(hb.get('h1_bb_up')))} / {_fmt(_f(hb.get('h1_bb_mid')))} / {_fmt(_f(hb.get('h1_bb_lo')))}", 0,
                             "เป้าหมายแผน = ราคากลับเข้าหาเส้นกลาง"))
            if ctx["macd_now"] is not None and ctx["macd_prev"] is not None:
                ch = ctx["macd_now"] - ctx["macd_prev"]
                inds.append(_ind("MACD Histogram H1", f"{ctx['macd_now']:+.2f} ({'ยกตัว' if ch > 0 else 'กดตัว'})", _agree(ch, side),
                                 "ข้อมูลประกอบ (ไม่ใช่เงื่อนไขเข้า) · ยกตัว = หนุน BUY · กดตัว = หนุน SELL"))
        divergence()
        ai_prob()
        step_trail()
        tp_progress()
    elif plan_key == "P6" and ctx:
        word = {1: "ขาขึ้น", -1: "ขาลง", 0: "ไม่ชัด (MA10/30 กับ MA200 ไม่ตรงกัน)"}[ctx["p6_trend"]]
        inds.append(_ind("เทรนด์ H4 (MA10/30 + MA200)", word, _agree(ctx["p6_trend"], side),
                         "ต้องตรงทิศตอนเข้า · เทรนด์เปลี่ยน = สัญญาณออก" + (f" ({exit_word})" if ctx["p6_trend"] != side else "")))
        if ctx["p6_sar"] is not None:
            inds.append(_ind("SAR H1 (0.01/0.1 · แท่งปิด)", _fmt(ctx["p6_sar"]), _agree(ctx["p6_dir"], side),
                             "SL เลื่อนตามจุดนี้ทุกชั่วโมง (ขยับเฉพาะทิศที่ดีขึ้น)"))
        if ctx["p6_sar_fast"] is not None:
            inds.append(_ind("SAR เร็ว H1 (0.02/0.2)", _fmt(ctx["p6_sar_fast"]), _agree(ctx["p6_dir_fast"], side),
                             "ใช้เมื่อกำไรสูงสุดถึง 2 ATR H1 — เลื่อน SL แน่นขึ้น"))
        if ctx["h1_ema100"] is not None and ctx["h1_close"] is not None:
            dd6 = _agree(ctx["h1_close"] - ctx["h1_ema100"], side)
            inds.append(_ind("ราคาปิด H1 vs EMA100", f"{ctx['h1_close']:,.2f} / {ctx['h1_ema100']:,.2f}", dd6,
                             "อยู่ฝั่งไม้ — ถือต่อ" if dd6 >= 0 else f"ปิดผิดฝั่ง = สัญญาณออก ({exit_word})"))
        if ctx["atr_h1"]:
            inds.append(_ind("ATR(14) H1", f"{ctx['atr_h1']:,.2f}", 0, "SL เริ่มไม่เกิน 3 ATR H1 · ไม่ตั้ง TP"))
    if plan_key == "M":
        step_trail()
    if plan_key == "M" and ctx:
        inds.append(_ind("เทรนด์ H4 (MA10/30)", f"{ctx['h4_diff']:+.2f}%", _agree(ctx["h4_dir"], side), ""))
    if atr:
        inds.append(_ind("ATR(14) M15", f"{atr:,.2f}", 0, "ความผันผวนต่อแท่ง 15 นาที"))

    return {"plan_key": plan_key, "plan_name": plan_name, "side": side, "candles": candles,
            "lines": lines, "levels": levels, "pane": pane, "indicators": inds}


def get(ticket, count=80, fallback=None):
    """
    ไม้ที่เปิดอยู่: กราฟ + อินดิเคเตอร์ของไม้ `ticket` — None ถ้าเชื่อม MT5 ไม่ได้
    fallback = dict ไม้จากหน้าจอ (comment/type) ใช้เมื่อไม้ถูกปิดไปแล้วระหว่างเปิดหน้าต่าง
    """
    if mt5.terminal_info() is None and not mt5.initialize():
        return None
    tick = mt5.symbol_info_tick(SYMBOL)
    info = mt5.symbol_info(SYMBOL)
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, count + WARMUP)
    if tick is None or rates is None or len(rates) < count:
        return None
    m = _m15_frame(rates, float(tick.bid))   # แท่งปัจจุบันใช้ราคาล่าสุด
    ctx = _context()
    _map_h1(m, ctx)

    plist = mt5.positions_get(ticket=int(ticket)) or []
    p = plist[0] if plist else None
    if p is not None:
        side = 1 if p.type == mt5.ORDER_TYPE_BUY else -1
        comment = p.comment or ""
        pos = {
            "ticket": int(p.ticket), "type": "BUY" if side > 0 else "SELL", "lot": float(p.volume),
            "entry": float(p.price_open), "price": float(tick.bid) if side > 0 else float(tick.ask),   # ราคาที่ใช้ปิดไม้
            "sl": float(p.sl or 0), "tp": float(p.tp or 0),
            "profit": float(p.profit) + float(p.swap), "time": int(p.time), "comment": comment,
        }
    else:
        fb = fallback or {}
        side = 1 if fb.get("type") == "BUY" else -1
        comment = fb.get("comment") or ""
        pos = None
    point = float(info.point) if info and info.point else 0.01
    out = _build(m, ctx, pos, side, comment, count, live=True)
    out.update({
        "position": pos, "money_per_pt": _money_per_pt(pos["lot"] if pos else 0.01),
        "bid": float(tick.bid), "ask": float(tick.ask),
        "spread_pts": int(round((float(tick.ask) - float(tick.bid)) / point)),
        "server_time": int(tick.time), "server_offset": _server_offset(), "closed": False,
    })
    return out


def _sl_tp_at_close(pid, open_time, close_time, close_comment, offset):
    """
    SL/TP ตอนปิดไม้ + เส้นทางการเลื่อน [(เวลาเซิร์ฟเวอร์, sl, tp)]
    1) ค่าเริ่มต้นจาก Order เปิดไม้ 2) การเลื่อนที่บอทบันทึกใน trade_modifications.csv (เวลาเครื่อง → เวลาเซิร์ฟเวอร์)
    3) ราคาที่ชนจริงจากคอมเมนต์ Deal ปิด เช่น "[sl 4168.67]" / "[tp 4161.38]"
    """
    sl = tp = 0.0
    orders = mt5.history_orders_get(position=int(pid)) or []
    first = next((o for o in orders if int(o.ticket) == int(pid)), None) or (min(orders, key=lambda o: o.time_setup) if orders else None)
    if first is not None:
        sl, tp = float(first.sl or 0), float(first.tp or 0)
    path = [(int(open_time), sl, tp)]
    try:
        with open(bot.TRADE_MODS_CSV, encoding="utf-8-sig", errors="replace") as f:
            for row in csv.DictReader(f):
                if str(row.get("Ticket", "")).strip() != str(pid):
                    continue
                t_srv = int(time.mktime(time.strptime(row["Time"].strip(), "%Y-%m-%d %H:%M:%S")) + offset)
                if t_srv > close_time + 60:
                    continue
                sl, tp = float(row.get("New_SL") or 0), float(row.get("New_TP") or 0)
                path.append((t_srv, sl, tp))
    except Exception:
        pass
    mt = re.match(r"\[(sl|tp)\s+([\d.]+)\]", (close_comment or "").strip())
    if mt:
        if mt.group(1) == "sl":
            sl = float(mt.group(2))
        else:
            tp = float(mt.group(2))
    path.sort()
    return sl, tp, path


def get_closed(trade, count=80):
    """
    ไม้ที่ปิดแล้ว (แถวจาก BotController.get_trade_history): ภาพ ณ ตอนปิดไม้ — None ถ้าเชื่อม MT5 ไม่ได้/ไม่มีข้อมูลราคา
    แท่งสุดท้าย = แท่ง M15 ที่ปิดไม้ ตัดที่เวลาปิดจริง (สูง/ต่ำจากแท่ง M1 ถึงนาทีที่ปิด · ราคาปิด = ราคาออก)
    """
    if mt5.terminal_info() is None and not mt5.initialize():
        return None
    pid = int(trade["ticket"])
    side = 1 if trade.get("side") == "BUY" else -1
    open_t, close_t = int(trade["open_time"]), int(trade["close_time"])
    entry, exit_px = float(trade["open_price"]), float(trade["close_price"])
    lot = float(trade.get("volume") or 0.01)
    rates = mt5.copy_rates_from(SYMBOL, mt5.TIMEFRAME_M15, close_t, count + WARMUP)
    if rates is None or len(rates) < count:
        return None
    m = pd.DataFrame(rates)
    bar_open = int(m["time"].iloc[-1])
    m1 = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, bar_open, close_t)
    if m1 is not None and len(m1):   # แท่งที่ปิดไม้: ตัดที่นาทีที่ปิด
        i = m.index[-1]
        m.loc[i, "high"] = max(float(x["high"]) for x in m1)
        m.loc[i, "low"] = min(float(x["low"]) for x in m1)
    m = _m15_frame(m.to_records(index=False), exit_px)

    h1 = _rates_df(mt5.copy_rates_from(SYMBOL, mt5.TIMEFRAME_H1, close_t, 620))
    h4 = _rates_df(mt5.copy_rates_from(SYMBOL, mt5.TIMEFRAME_H4, close_t, 320))
    if h1 is not None and h4 is not None:
        _set_last(h1, exit_px)
        _set_last(h4, exit_px)
    ctx = _context_from(h1, h4, exit_px)
    _map_h1(m, ctx)

    offset = _server_offset(close_t)
    sl, tp, path = _sl_tp_at_close(pid, open_t, close_t, trade.get("close_reason"), offset)

    # กำไรสูงสุด / ติดลบสูงสุดระหว่างถือ (จากแท่ง M1 — ถ้าไม่มีใช้ M15)
    span = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, open_t, close_t)
    if span is None or len(span) == 0:
        span = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M15, open_t - open_t % 900, close_t)
    mfe = mae = None
    if span is not None and len(span):
        hi, lo = max(float(x["high"]) for x in span), min(float(x["low"]) for x in span)
        hi, lo = max(hi, exit_px), min(lo, exit_px)
        mfe, mae = ((hi - entry), (entry - lo)) if side > 0 else ((entry - lo), (hi - entry))
        mfe, mae = max(0.0, mfe), max(0.0, mae)

    pos = {
        "ticket": pid, "type": "BUY" if side > 0 else "SELL", "lot": lot, "entry": entry, "price": exit_px,
        "sl": sl, "tp": tp, "profit": float(trade.get("profit") or 0.0), "time": open_t, "comment": trade.get("plan") or "",
        "close_time": close_t, "close_code": int(trade.get("close_code", -1)), "close_reason": trade.get("close_reason") or "",
    }
    mpp = _money_per_pt(lot)
    out = _build(m, ctx, pos, side, pos["comment"], count, live=False, mfe=mfe)
    sl_moves = sum(1 for a, b in zip(path, path[1:]) if abs(a[1] - b[1]) > 1e-6)
    tp_moves = sum(1 for a, b in zip(path, path[1:]) if abs(a[2] - b[2]) > 1e-6)
    paths = []
    if len(path) > 1:   # เส้นทางการเลื่อน SL/TP ระหว่างถือ
        pts_sl = [(t, s) for t, s, _ in path if s > 0] + [(close_t, sl)] if sl > 0 else []
        pts_tp = [(t, v) for t, _, v in path if v > 0] + [(close_t, tp)] if tp > 0 else []
        if sl_moves and len(pts_sl) > 1:
            paths.append({"label": "SL", "style": "res", "points": pts_sl})
        if tp_moves and len(pts_tp) > 1:
            paths.append({"label": "TP", "style": "sup", "points": pts_tp})
    out.update({
        "position": pos, "money_per_pt": mpp, "bid": exit_px, "ask": None, "spread_pts": 0,
        "server_time": close_t, "server_offset": offset, "closed": True, "paths": paths,
        "summary": {
            "mfe": mfe, "mae": mae, "mfe_money": None if mfe is None else mfe * mpp,
            "mae_money": None if mae is None else mae * mpp,
            "sl_moves": sl_moves, "tp_moves": tp_moves, "held": close_t - open_t,
            "initial_sl": path[0][1], "initial_tp": path[0][2],
        },
    })
    return out
