"""
AI คาดการณ์ทิศทางราคาทอง (XAUUSD) ล่วงหน้า 1 ชม. / 4 ชม. / 1 วัน — รวมข้อมูลทุกด้าน
- โมเดล: Random Forest แยกตามระยะเวลา ใช้ Features 24 ตัวชุดเดียวกับบอท (build_ai_features: M15 + H1 + H4 แท่งที่ปิดแล้ว)
  เทรนใหม่ทุก 6 ชม. ในเธรดเบื้องหลัง · ทายจากแท่ง M15 ที่ปิดแล้วล่าสุด
- ปัจจัยประกอบ: เทรนด์ H1 MA100/150/200, เทรนด์ H4 MA10/30, ราคาเทียบ MA200 H4, MA5/MA13 + RSI M15,
  ตำแหน่งเทียบแนวรับ/แนวต้าน H1, ข่าว USD ผลกระทบสูงใน 24 ชม. (จาก news_impact)
- ความแม่นในอดีต: วัดแบบ Walk-forward 2.5 ปี (6 ต.ค. 2026) — แสดงคู่กับคำทำนายเสมอ เพื่อไม่ให้เชื่อเกินจริง
ผลล่าสุดเก็บใน latest() — โปรแกรมแสดงในแท็บ "AI คาดการณ์" และ Telemetry ส่งชุดเดียวกันขึ้นเว็บ
"""
import threading
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

HORIZONS = (("1h", "1 ชม.", 4, 5000), ("4h", "4 ชม.", 16, 8000), ("1d", "1 วัน", 96, 15000))
RETRAIN_SEC = 6 * 3600
REFRESH_SEC = 60

# ความแม่นจาก Walk-forward 2.5 ปี (tools: bt_outlook) — {horizon: {ระดับ: %}}
#   base = ทุกครั้ง · c55/c60 = AI มั่นใจ ≥55%/≥60% · a55/a60 = มั่นใจและเทรนด์ (กฎ) ตรงกัน
BACKTEST_ACC = {
    "1h": {"base": 52.0, "c55": 53.0, "c60": 54.9, "a55": 54.8, "a60": 59.5},
    "4h": {"base": 52.9, "c55": 53.8, "c60": 52.4, "a55": 56.1, "a60": 54.2},
    "1d": {"base": 54.2, "c55": 54.4, "c60": 57.6, "a55": 59.8, "a60": 63.7},
}

_state = {"models": {}, "trained_at": 0.0, "result": None, "error": "", "running": False}
_lock = threading.Lock()


def latest():
    """ผลคาดการณ์ล่าสุด (dict) หรือ None"""
    return _state["result"]


def _load():
    import MetaTrader5 as mt5
    import multi_asset_ai_bot as bot
    if mt5.terminal_info() is None and not mt5.initialize():
        raise RuntimeError("เชื่อมต่อ MT5 ไม่ได้")
    m15 = bot.get_data("XAUUSD", mt5.TIMEFRAME_M15, 17000)
    h1 = bot.get_data("XAUUSD", mt5.TIMEFRAME_H1, 4800)
    h4 = bot.get_data("XAUUSD", mt5.TIMEFRAME_H4, 1400)
    if m15 is None or h1 is None or h4 is None:
        raise RuntimeError("ดึงข้อมูลราคาไม่ได้")
    return bot, m15, h1, h4


def _train(bot, ai):
    from sklearn.ensemble import RandomForestClassifier
    F = bot.AI_FEATURES
    models = {}
    for key, _label, H, n_train in HORIZONS:
        y = (ai["close"].shift(-H) > ai["close"]).astype(int)
        ok = ai[F].notna().all(axis=1) & ai["close"].shift(-H).notna()
        d = ai[ok].tail(n_train)
        m = RandomForestClassifier(n_estimators=150, max_depth=5, min_samples_leaf=50, random_state=42, n_jobs=-1)
        m.fit(d[F], y[d.index])
        models[key] = m
    return models


def _factors(bot, m15, h1, h4, ai_row):
    """ปัจจัยประกอบ: [(ชื่อ, ทิศ +1/-1/0, คำอธิบาย)]"""
    out = []
    c = h1["close"]
    if len(c) >= 202:
        m100, m150, m200 = (c.rolling(k).mean().iloc[-2] for k in (100, 150, 200))
        d = -1 if m100 < m150 < m200 else (1 if m100 > m150 > m200 else 0)
        out.append(("เทรนด์ H1 (MA100/150/200)", d, "เรียงตัวขาขึ้น" if d > 0 else "เรียงตัวขาลง" if d < 0 else "ยังไม่เรียงตัว (ไซด์เวย์)"))
    c4 = h4["close"]
    if len(c4) >= 32:
        f10, f30 = c4.rolling(10).mean().iloc[-2], c4.rolling(30).mean().iloc[-2]
        pct = (f10 / f30 - 1) * 100
        d = 0 if abs(pct) < 0.2 else (1 if pct > 0 else -1)
        out.append(("เทรนด์ H4 (MA10/30)", d, f"ห่างกัน {pct:+.2f}%" + (" · ไซด์เวย์" if d == 0 else "")))
    if len(c4) >= 202:
        m200 = c4.rolling(200).mean().iloc[-2]
        d = 1 if c4.iloc[-2] > m200 else -1
        out.append(("ราคาเทียบ MA200 (H4)", d, f"{'เหนือ' if d > 0 else 'ใต้'} MA200 ({m200:,.2f})"))
    cm = m15["close"]
    if len(cm) >= 20:
        ma5, ma13 = cm.rolling(5).mean().iloc[-2], cm.rolling(13).mean().iloc[-2]
        dl = cm.diff()
        g, l = dl.where(dl > 0, 0).rolling(14).mean(), (-dl.where(dl < 0, 0)).rolling(14).mean()
        rsi = float((100 - 100 / (1 + g / (l + 1e-9))).iloc[-2])
        d = 1 if ma5 > ma13 and rsi > 50 else (-1 if ma5 < ma13 and rsi < 50 else 0)
        out.append(("โมเมนตัม M15 (MA5/13 + RSI)", d, f"MA5 {'>' if ma5 > ma13 else '<'} MA13 · RSI {rsi:.0f}"))
    try:
        price = float(cm.iloc[-1])
        sr = bot.find_sr_levels(h1.iloc[-502:], price)
        atr = float(bot._atr_series(h1).iloc[-2])
        sup, res = sr.get("support"), sr.get("resistance")
        if res and atr and not np.isnan(res) and (res - price) < 0.5 * atr:
            out.append(("แนวรับ/แนวต้าน H1", -1, f"ใกล้แนวต้าน {res:,.2f} — เสี่ยงถูกกดลง"))
        elif sup and atr and not np.isnan(sup) and (price - sup) < 0.5 * atr:
            out.append(("แนวรับ/แนวต้าน H1", 1, f"ใกล้แนวรับ {sup:,.2f} — มีโอกาสเด้ง"))
        elif sup and res and not np.isnan(sup) and not np.isnan(res):
            out.append(("แนวรับ/แนวต้าน H1", 0, f"อยู่กลางกรอบ {sup:,.2f} – {res:,.2f}"))
    except Exception:
        pass
    try:
        out.extend(_popular_factors(bot, h1, h4))
    except Exception:
        pass
    return out


def _rsi(c, n=14):
    dl = c.diff()
    g, l = dl.where(dl > 0, 0).rolling(n).mean(), (-dl.where(dl < 0, 0)).rolling(n).mean()
    return 100 - 100 / (1 + g / (l + 1e-9))


def _popular_factors(bot, h1, h4):
    """อินดิเคเตอร์ยอดนิยมของนักเทรด (แสดงผลประกอบเท่านั้น — ไม่ใช้คิด 'เทรนด์ยืนยัน' / คะแนนถือ-ปิดไม้)
    ชื่อห้ามขึ้นต้นด้วย 'เทรนด์' หรือ 'ราคาเทียบ' (กลุ่มนั้นผูกกับความแม่นจาก Backtest) · ใช้แท่งที่ปิดแล้ว"""
    import MetaTrader5 as mt5
    out = []
    c4, h4h, h4l = h4["close"], h4["high"], h4["low"]
    c1 = h1["close"]
    # 1) EMA50/200 รายวัน — Golden / Death Cross
    d1 = bot.get_data("XAUUSD", mt5.TIMEFRAME_D1, 400)
    if d1 is not None and len(d1) >= 210:
        e50, e200 = (d1["close"].ewm(span=k, adjust=False).mean().iloc[-2] for k in (50, 200))
        d = 1 if e50 > e200 else -1
        out.append(("EMA50/200 รายวัน", d, f"{'Golden Cross (EMA50 เหนือ EMA200)' if d > 0 else 'Death Cross (EMA50 ใต้ EMA200)'}"))
    # 2) ADX H4 + DI — ความแรงเทรนด์
    up, dn = h4h.diff(), -h4l.diff()
    plus = up.where((up > dn) & (up > 0), 0.0)
    minus = dn.where((dn > up) & (dn > 0), 0.0)
    tr = (h4h - h4l).combine((h4h - c4.shift()).abs(), max).combine((h4l - c4.shift()).abs(), max)
    aw = tr.ewm(alpha=1 / 14, adjust=False).mean()
    pdi = 100 * plus.ewm(alpha=1 / 14, adjust=False).mean() / aw
    mdi = 100 * minus.ewm(alpha=1 / 14, adjust=False).mean() / aw
    adx = (100 * (pdi - mdi).abs() / (pdi + mdi + 1e-9)).ewm(alpha=1 / 14, adjust=False).mean()
    a, p_, m_ = float(adx.iloc[-2]), float(pdi.iloc[-2]), float(mdi.iloc[-2])
    d = (1 if p_ > m_ else -1) if a >= 25 else 0
    out.append(("ADX H4 (ความแรงเทรนด์)", d, f"ADX {a:.0f} · {'เทรนด์แรง' if a >= 25 else 'เทรนด์อ่อน/ไซด์เวย์'} · +DI {p_:.0f} / −DI {m_:.0f}"))
    # 3) Ichimoku Cloud H4
    if len(c4) >= 90:
        ten = (h4h.rolling(9).max() + h4l.rolling(9).min()) / 2
        kij = (h4h.rolling(26).max() + h4l.rolling(26).min()) / 2
        sa = ((ten + kij) / 2).shift(26).iloc[-2]
        sb = ((h4h.rolling(52).max() + h4l.rolling(52).min()) / 2).shift(26).iloc[-2]
        px, top, bot_ = float(c4.iloc[-2]), max(sa, sb), min(sa, sb)
        d = 1 if px > top else (-1 if px < bot_ else 0)
        out.append(("Ichimoku Cloud H4", d, "ราคาอยู่เหนือเมฆ" if d > 0 else "ราคาอยู่ใต้เมฆ" if d < 0 else f"ราคาอยู่ในเมฆ ({bot_:,.2f} – {top:,.2f})"))
    # 4) Parabolic SAR H1 (มาตรฐาน 0.02/0.2)
    sar, sdir = bot.psar_series(h1["high"].values, h1["low"].values, 0.02, 0.2)
    d = int(sdir[-2])
    out.append(("Parabolic SAR H1", d, f"จุด SAR {'ใต้' if d > 0 else 'เหนือ'}ราคา ({sar[-2]:,.2f})"))
    # 5) RSI(14) H4
    r = float(_rsi(c4).iloc[-2])
    if r >= 70:
        d, t = -1, "ซื้อมากเกินไป (Overbought) — เสี่ยงย่อตัว"
    elif r <= 30:
        d, t = 1, "ขายมากเกินไป (Oversold) — มีโอกาสเด้ง"
    elif r >= 55:
        d, t = 1, "โมเมนตัมขาขึ้น"
    elif r <= 45:
        d, t = -1, "โมเมนตัมขาลง"
    else:
        d, t = 0, "กลาง ๆ"
    out.append(("RSI(14) H4", d, f"RSI {r:.0f} · {t}"))
    # 6) MACD H4 (12,26,9)
    macd = c4.ewm(span=12, adjust=False).mean() - c4.ewm(span=26, adjust=False).mean()
    hist = macd - macd.ewm(span=9, adjust=False).mean()
    h_now, h_prev = float(hist.iloc[-2]), float(hist.iloc[-3])
    d = 1 if h_now > 0 and h_now >= h_prev else (-1 if h_now < 0 and h_now <= h_prev else 0)
    out.append(("MACD H4 (12,26,9)", d, f"ฮิสโตแกรม {h_now:+.2f} · {'เพิ่มขึ้น' if h_now > h_prev else 'ลดลง'}"))
    # 7) Stochastic H1 (14,3,3)
    ll, hh = h1["low"].rolling(14).min(), h1["high"].rolling(14).max()
    k = (100 * (c1 - ll) / (hh - ll + 1e-9)).rolling(3).mean()
    dd = k.rolling(3).mean()
    kv, dv = float(k.iloc[-2]), float(dd.iloc[-2])
    if kv >= 80:
        d, t = -1, "Overbought"
    elif kv <= 20:
        d, t = 1, "Oversold"
    else:
        d, t = (1 if kv > dv else -1), ("%K อยู่เหนือ %D" if kv > dv else "%K อยู่ใต้ %D")
    out.append(("Stochastic H1 (14,3,3)", d, f"%K {kv:.0f} · %D {dv:.0f} · {t}"))
    # 8) Bollinger Bands H1 (20, 2)
    mid, sd = c1.rolling(20).mean(), c1.rolling(20).std()
    upb, lob = float((mid + 2 * sd).iloc[-2]), float((mid - 2 * sd).iloc[-2])
    pb = (float(c1.iloc[-2]) - lob) / (upb - lob + 1e-9)
    d = -1 if pb >= 0.9 else (1 if pb <= 0.1 else 0)
    out.append(("Bollinger Bands H1", d, f"ตำแหน่งในกรอบ {pb * 100:.0f}% · " + ("ชิดขอบบน เสี่ยงย่อ" if d < 0 else "ชิดขอบล่าง มีโอกาสเด้ง" if d > 0 else f"กรอบ {lob:,.2f} – {upb:,.2f}")))
    # 9) Pivot Point รายวัน (Classic)
    if d1 is not None and len(d1) >= 3:
        pd_ = d1.iloc[-2]
        pv = (pd_["high"] + pd_["low"] + pd_["close"]) / 3
        r1, s1 = 2 * pv - pd_["low"], 2 * pv - pd_["high"]
        px = float(c1.iloc[-1])
        d = 1 if px > pv else -1
        out.append(("Pivot Point รายวัน", d, f"ราคา{'เหนือ' if d > 0 else 'ใต้'} Pivot {pv:,.2f} · R1 {r1:,.2f} · S1 {s1:,.2f}"))
    # 10) ดอลลาร์สหรัฐ (ประมาณจาก EURUSD — ดอลลาร์อ่อน = ทองมักขึ้น)
    mt5.symbol_select("EURUSD", True)
    eu = bot.get_data("EURUSD", mt5.TIMEFRAME_H4, 80)
    if eu is not None and len(eu) >= 32:
        f10, f30 = (eu["close"].rolling(k).mean().iloc[-2] for k in (10, 30))
        pct = (f10 / f30 - 1) * 100
        d = 0 if abs(pct) < 0.1 else (1 if pct > 0 else -1)
        out.append(("ดอลลาร์สหรัฐ (จาก EURUSD H4)", d, ("ดอลลาร์อ่อนค่า — หนุนทอง" if d > 0 else "ดอลลาร์แข็งค่า — กดทอง" if d < 0 else "ดอลลาร์ทรงตัว") + f" · EURUSD MA10/30 {pct:+.2f}%"))
    return out


def _news(now_utc):
    """ข่าว USD ผลกระทบสูงใน 24 ชม. ข้างหน้า + แนวโน้มของข่าว"""
    try:
        import econ_calendar
        import news_impact
        items = []
        for ev in econ_calendar.fetch_events():
            t = ev["time"].astimezone(timezone.utc)
            if ev["currency"] == "USD" and ev["impact"] == "High" and now_utc <= t <= now_utc + timedelta(hours=24):
                import news_th
                items.append({"title": ev["title"], "title_th": news_th.translate(ev["title"]),
                              "time": ev["time"].strftime("%d/%m %H:%M"), "lean": news_impact.pre_release_lean(ev)})
        return items
    except Exception:
        return []


def _acc_for(key, conf, agree):
    t = BACKTEST_ACC[key]
    if conf >= 0.60:
        return t["a60"] if agree else t["c60"]
    if conf >= 0.55:
        return t["a55"] if agree else t["c55"]
    return t["base"]


def refresh(force_retrain=False):
    """คำนวณคาดการณ์ใหม่ (เรียกจากเธรดเบื้องหลัง)"""
    bot, m15, h1, h4 = _load()
    ai = bot.build_ai_features(m15, h1, h4)
    with _lock:
        if force_retrain or not _state["models"] or time.time() - _state["trained_at"] > RETRAIN_SEC:
            _state["models"] = _train(bot, ai)
            _state["trained_at"] = time.time()
        models = dict(_state["models"])
    F = bot.AI_FEATURES
    row = ai[F].iloc[[-2]]  # แท่ง M15 ที่ปิดแล้วล่าสุด
    if row.isna().any(axis=None):
        row = ai[F].dropna().iloc[[-1]]
    factors = _factors(bot, m15, h1, h4, row)
    trend_score = sum(d for name, d, _ in factors if name.startswith(("เทรนด์", "ราคาเทียบ")))
    now_utc = datetime.now(timezone.utc)
    horizons = []
    for key, label, H, _n in HORIZONS:
        p_up = float(models[key].predict_proba(row)[0][1])
        d = 1 if p_up >= 0.5 else -1
        conf = max(p_up, 1 - p_up)
        agree = trend_score * d >= 2
        direction = d if conf >= 0.55 else 0
        horizons.append({
            "key": key, "label": label, "p_up": round(p_up, 4), "direction": direction, "lean": d,
            "confidence": round(conf * 100, 1), "trend_agree": bool(agree),
            "hist_acc": _acc_for(key, conf, agree),
        })
    news = _news(now_utc)
    main = horizons[-1]
    if main["direction"] == 0:
        summary = "ยังไม่ชัดเจน — AI และปัจจัยต่าง ๆ ยังขัดกัน"
    else:
        word = "ขึ้น" if main["direction"] > 0 else "ลง"
        summary = f"1 วันข้างหน้า ทองมีแนวโน้ม{word} (AI {main['confidence']:.0f}%" + (" · เทรนด์ยืนยัน)" if main["trend_agree"] else ")")
    if news:
        summary += f" · ระวังข่าวแรง {len(news)} ข่าวใน 24 ชม."
    result = {
        "updated_at": now_utc.isoformat(timespec="seconds"),
        "trained_at": datetime.fromtimestamp(_state["trained_at"], timezone.utc).isoformat(timespec="seconds"),
        "price": round(float(m15["close"].iloc[-1]), 2),
        "summary": summary,
        "horizons": horizons,
        "factors": [{"name": n, "dir": int(d), "detail": t} for n, d, t in factors],
        "news": news,
        "note": "ความแม่นวัดจากการทดสอบย้อนหลัง 2.5 ปี — ทองทายทิศยาก ใช้ประกอบการตัดสินใจ ไม่ใช่คำแนะนำการลงทุน",
    }
    _state["result"] = result
    return result


def start_background():
    """เริ่มเธรดอัปเดตคาดการณ์ทุก 60 วินาที (ครั้งเดียวต่อโปรเซส)"""
    if _state["running"]:
        return
    _state["running"] = True

    def loop():
        while True:
            try:
                refresh()
                _state["error"] = ""
            except Exception as e:
                _state["error"] = str(e)
            time.sleep(REFRESH_SEC)

    threading.Thread(target=loop, daemon=True, name="ai-outlook").start()


def last_error():
    return _state["error"]
