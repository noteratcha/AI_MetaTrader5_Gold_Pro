"""
วิเคราะห์ไม้ที่เปิดค้างอยู่: แนะนำ "ถือต่อ" / "ถือต่อแบบระวัง" / "แนะนำปิด" พร้อมเหตุผล
- ใช้ปัจจัยเดียวกับแท็บ AI คาดการณ์ (เทรนด์ H1/H4, MA200 H4, โมเมนตัม M15, แนวรับ/ต้าน H1) เทียบกับทิศของไม้
- สัญญาณออกของแผนเอง (P1: MA5/13 M15 · P2: MA5/20 H1 ตัดกลับ), AI 1 ชม./4 ชม., ระยะ SL/TP, ล็อกกำไร, ข่าวแรงใกล้ ๆ
- รันในเธรดเบื้องหลัง (เรียก MT5) — GUI อ่านผลจาก latest() เท่านั้น
"""
import threading
import time
from datetime import datetime, timedelta, timezone

REFRESH_SEC = 30
_state = {"result": {}, "updated": 0.0, "error": ""}
_lock = threading.Lock()
_started = False

HOLD, CAUTION, CLOSE = "hold", "caution", "close"
VERDICT_TEXT = {HOLD: "แนะนำถือต่อ", CAUTION: "ถือต่อแบบระวัง", CLOSE: "แนะนำปิดไม้"}


def latest() -> dict:
    """{ticket: {...}} ผลวิเคราะห์ล่าสุด"""
    return _state["result"]


def _load():
    import MetaTrader5 as mt5
    import multi_asset_ai_bot as bot
    if mt5.terminal_info() is None and not mt5.initialize():
        raise RuntimeError("เชื่อมต่อ MT5 ไม่ได้")
    m15 = bot.get_data("XAUUSD", mt5.TIMEFRAME_M15, 300)
    h1 = bot.get_data("XAUUSD", mt5.TIMEFRAME_H1, 600)
    h4 = bot.get_data("XAUUSD", mt5.TIMEFRAME_H4, 300)
    if m15 is None or h1 is None or h4 is None:
        raise RuntimeError("ดึงข้อมูลราคาไม่ได้")
    positions = mt5.positions_get(symbol="XAUUSD") or []
    return bot, mt5, m15, h1, h4, positions


def _news_soon(minutes=90):
    """ข่าว USD ผลกระทบสูงภายใน N นาทีข้างหน้า → [(ชื่อไทย, นาทีที่เหลือ)]"""
    try:
        import econ_calendar
        import news_th
        now = datetime.now(timezone.utc)
        out = []
        for ev in econ_calendar.fetch_events():
            t = ev["time"].astimezone(timezone.utc)
            if ev["currency"] == "USD" and ev["impact"] == "High" and now <= t <= now + timedelta(minutes=minutes):
                out.append((news_th.translate(ev["title"]) or ev["title"], int((t - now).total_seconds() // 60)))
        return out
    except Exception:
        return []


def _plan_exit(comment, side, m15, h1):
    """สัญญาณออกของแผนเอง (ตัดกลับขั้วบนแท่งที่ปิดแล้ว) → ข้อความ หรือ None"""
    c = (comment or "")
    if c.startswith("MA-Cross-Trend"):
        cm = m15["close"]
        f, s, tf, pair = cm.rolling(5).mean().iloc[-2], cm.rolling(13).mean().iloc[-2], "M15", "MA5/MA13"
    elif c.startswith("PSAR"):
        ch = h1["close"]
        e100 = ch.ewm(span=100, adjust=False).mean().iloc[-2]
        if (ch.iloc[-2] - e100) * side < 0:
            return "ราคาปิด H1 ผิดฝั่ง EMA100 = สัญญาณออกของแผนนี้ (บอทจะปิดเองเมื่อทำงานอยู่)"
        return None
    elif c.startswith("MA-Cross-H1"):
        ch = h1["close"]
        m5, m20 = ch.rolling(5).mean(), ch.rolling(20).mean()
        # P2 ออกเมื่อ MA5 ตัด MA20 กลับ (เหตุการณ์ตัดบนแท่งปิดล่าสุด — ตอนเข้า MA5 อาจยังอยู่ผิดฝั่ง MA20 ได้)
        crossed = (m5.iloc[-3] - m20.iloc[-3]) * side > 0 and (m5.iloc[-2] - m20.iloc[-2]) * side < 0
        return "MA5/MA20 H1 ตัดกลับขั้วแล้ว = สัญญาณออกของแผนนี้ (บอทจะปิดเองเมื่อทำงานอยู่)" if crossed else None
    else:
        return None
    if (side > 0 and f < s) or (side < 0 and f > s):
        return f"{pair} {tf} ตัดกลับขั้วแล้ว = สัญญาณออกของแผนนี้ (บอทจะปิดเองเมื่อทำงานอยู่)"
    return None


def _analyze_one(bot, pos, m15, h1, h4, factors, outlook, news, atr):
    import MetaTrader5 as mt5
    side = 1 if pos.type == mt5.ORDER_TYPE_BUY else -1
    word = "BUY" if side > 0 else "SELL"
    price, entry = float(pos.price_current), float(pos.price_open)
    sl, tp = float(pos.sl or 0), float(pos.tp or 0)
    profit = float(pos.profit) + float(pos.swap)
    reasons = []  # (น้ำหนัก +ถือ/−ปิด, ข้อความ)

    exit_msg = _plan_exit(pos.comment, side, m15, h1)
    if exit_msg:
        reasons.append((-3.0, exit_msg))

    weights = {"เทรนด์ H1": 1.0, "เทรนด์ H4": 1.0, "ราคาเทียบ MA200": 0.5, "โมเมนตัม M15": 1.0, "แนวรับ/แนวต้าน": 1.0}
    for name, d, detail in factors:
        w = next((v for k, v in weights.items() if name.startswith(k)), 0.5)
        if d == 0:
            reasons.append((0.0, f"{name}: {detail.replace(' — ', ' · ')} — ยังไม่ชี้ทิศ"))
        elif d == side:
            reasons.append((w, f"{name}: {detail.replace(' — ', ' · ')} — หนุนไม้ {word}"))
        else:
            reasons.append((-w, f"{name}: {detail.replace(' — ', ' · ')} — สวนไม้ {word}"))

    for h in (outlook or {}).get("horizons", []):
        if h["key"] not in ("1h", "4h"):
            continue
        w = 1.0 if h["key"] == "4h" else 0.5
        acc = f" (แม่นในอดีต ~{h['hist_acc']:.0f}%)" if h.get("hist_acc") else ""
        if h["direction"] == 0:
            reasons.append((0.0, f"AI {h['label']}: ยังไม่ชัด ({h['confidence']:.0f}%){acc}"))
        elif h["direction"] == side:
            reasons.append((w, f"AI {h['label']}: คาดว่า{'ขึ้น' if side > 0 else 'ลง'} {h['confidence']:.0f}% — ตรงกับไม้{acc}"))
        else:
            reasons.append((-w, f"AI {h['label']}: คาดว่า{'ลง' if side > 0 else 'ขึ้น'} {h['confidence']:.0f}% — สวนไม้{acc}"))

    locked = sl > 0 and ((side > 0 and sl > entry) or (side < 0 and sl < entry))
    if sl <= 0:
        reasons.append((-1.5, "ไม้นี้ไม่มี Stop Loss — ความเสี่ยงไม่จำกัด"))
    elif locked:
        reasons.append((1.0, f"SL ล็อกกำไรแล้วที่ {sl:,.2f} — ถ้าราคากลับตัวยังปิดได้กำไร"))
    elif atr and abs(price - sl) < 0.25 * atr:
        reasons.append((-1.0, f"ราคาเหลืออีก {abs(price - sl):,.2f} จุดจะชน SL ({sl:,.2f})"))
    if tp > 0 and atr and abs(tp - price) < 0.3 * atr and (tp - price) * side > 0:
        reasons.append((1.0, f"ใกล้ TP อีก {abs(tp - price):,.2f} จุด ({tp:,.2f})"))
    for title, mins in news:
        reasons.append((-1.0, f"ข่าวแรง USD \"{title}\" อีก {mins} นาที — ราคาอาจสะบัดแรง"
                              + (" ควรพิจารณาเก็บกำไร/ล็อกกำไรก่อน" if profit > 0 else "")))

    score = sum(w for w, _ in reasons)
    if exit_msg or score <= -2.5:
        verdict = CLOSE
    elif score < 1.0:
        verdict = CAUTION
    else:
        verdict = HOLD
    reasons.sort(key=lambda r: -abs(r[0]))
    if verdict == CLOSE:
        advice = "ปัจจัยส่วนใหญ่สวนทางไม้นี้ — " + ("ปิดเก็บกำไรที่มีอยู่" if profit > 0 else "ปิดเพื่อจำกัดการขาดทุน")
    elif verdict == CAUTION:
        advice = "ปัจจัยยังขัดกัน — ถือต่อได้แต่เฝ้าดูใกล้ชิด" + (" หรือปิดเก็บกำไรบางส่วน" if profit > 0 else "")
    else:
        advice = "ปัจจัยส่วนใหญ่หนุนทิศของไม้ — ถือต่อและให้ SL/การเลื่อน SL ทำงาน"
    return {
        "ticket": int(pos.ticket), "side": word, "plan": pos.comment or "Manual", "profit": round(profit, 2),
        "verdict": verdict, "verdict_text": VERDICT_TEXT[verdict], "score": round(score, 1), "advice": advice,
        "reasons": [{"w": w, "text": t} for w, t in reasons],
    }


def refresh():
    import ai_outlook
    bot, mt5, m15, h1, h4, positions = _load()
    if not positions:
        _state["result"] = {}
        return {}
    factors = ai_outlook._factors(bot, m15, h1, h4, None)
    try:
        atr = float(bot._atr_series(m15).iloc[-2])
    except Exception:
        atr = 0.0
    outlook, news = ai_outlook.latest(), _news_soon()
    res = {int(p.ticket): _analyze_one(bot, p, m15, h1, h4, factors, outlook, news, atr) for p in positions}
    _state["updated"] = time.time()   # ตั้งเวลาก่อนผล — หน้าจอที่อ่านผลจะไม่เห็นผลใหม่คู่กับเวลาเก่า
    _state["result"] = res
    return res


def request_refresh():
    """ขอวิเคราะห์ใหม่ทันที (เช่น เมื่อมีไม้ใหม่)"""
    _state["updated"] = 0.0


def start_background():
    global _started
    with _lock:
        if _started:
            return
        _started = True

    def loop():
        while True:
            if time.time() - _state["updated"] >= REFRESH_SEC:
                try:
                    refresh()
                    _state["error"] = ""
                except Exception as e:
                    _state["error"] = str(e)
                    _state["updated"] = time.time()
            time.sleep(2)

    threading.Thread(target=loop, daemon=True, name="position-advisor").start()
