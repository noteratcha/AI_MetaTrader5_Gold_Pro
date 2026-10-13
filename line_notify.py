"""
แจ้งเตือนเข้าไม้ / ปิดไม้ / สรุปกำไรรายวัน ไปที่ LINE OA ของผู้ใช้เอง (Messaging API · Broadcast)
- ผู้ใช้สร้าง LINE OA ฟรีของตัวเอง → เปิด Messaging API → ใส่ Channel access token ในโปรแกรม → แอดเพื่อน OA นั้น
- Token เก็บในเครื่องเท่านั้น เข้ารหัส Windows DPAPI (secure_store) · ไม่ส่งขึ้น Server · แยกตาม Profile (data_path)
- ส่งผ่านคิว + เธรดเบื้องหลัง (ไม่ทำให้ลูปเทรดหน่วง) · ลองซ้ำ 3 ครั้ง · กันส่งซ้ำด้วย (เหตุการณ์, ticket)
"""
import json
import queue
import threading
import time
import urllib.error
import urllib.request

import secure_store
import thai_time
from app_paths import data_path

API = "https://api.line.me/v2/bot"
SETTINGS_FILE = data_path("line_oa.json")
DEFAULTS = {"enabled": False, "token": "", "events": {"open": True, "close": True, "daily": True}, "daily_time": "00:05", "last_daily": ""}

_q = queue.Queue(maxsize=200)
_sent = {}          # (event, ticket) → เวลา — กันส่งซ้ำ
_lock = threading.Lock()
_worker_started = False
_scheduler_started = False
last_error = ""     # ข้อความ error ล่าสุด (แสดงในหน้าต่างตั้งค่า)


# ------------------------------------------------------------------ ตั้งค่า
def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            d = json.load(f) or {}
    except Exception:
        d = {}
    out = {**DEFAULTS, **d, "events": {**DEFAULTS["events"], **(d.get("events") or {})}}
    return out


def save_settings(enabled=None, token=None, events=None, daily_time=None, last_daily=None):
    """บันทึกเฉพาะค่าที่ส่งมา · token = ข้อความธรรมดา (เข้ารหัสก่อนเขียนไฟล์) · token="" = ลบ"""
    d = load_settings()
    if enabled is not None:
        d["enabled"] = bool(enabled)
    if token is not None:
        d["token"] = secure_store.protect_text(token.strip()) if token.strip() else ""
    if events is not None:
        d["events"] = {**d["events"], **events}
    if daily_time is not None:
        d["daily_time"] = daily_time
    if last_daily is not None:
        d["last_daily"] = last_daily
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    return d


def get_token() -> str:
    return secure_store.unprotect_text(load_settings().get("token") or "")


def _active(event: str) -> bool:
    s = load_settings()
    return bool(s.get("enabled") and s.get("token") and s["events"].get(event, False))


# ------------------------------------------------------------------ ส่งข้อความ
def _request(method, path, token, body=None, timeout=10):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8") or "{}"
        return json.loads(raw)


def _explain(e) -> str:
    if isinstance(e, urllib.error.HTTPError):
        try:
            msg = json.loads(e.read().decode("utf-8")).get("message", "")
        except Exception:
            msg = ""
        if e.code == 401:
            return "Channel access token ไม่ถูกต้องหรือหมดอายุ"
        if e.code == 429:
            return "โควตาข้อความของ LINE OA เดือนนี้หมดแล้ว (หรือส่งถี่เกินไป)"
        if e.code == 403:
            return "OA นี้ไม่มีสิทธิ์ส่ง Broadcast — ตรวจว่าเปิด Messaging API แล้ว"
        return f"LINE ตอบกลับ HTTP {e.code} {msg}".strip()
    return f"เชื่อมต่อ LINE ไม่ได้: {e}"


def _broadcast(messages, token=None) -> tuple:
    """ส่งทันที (ใช้ในเธรดเบื้องหลัง / ปุ่มทดสอบ) → (สำเร็จ, ข้อความ)"""
    global last_error
    token = token or get_token()
    if not token:
        return False, "ยังไม่ได้ใส่ Channel access token"
    err = ""
    for attempt in range(3):
        try:
            _request("POST", "/message/broadcast", token, {"messages": messages})
            last_error = ""
            return True, "ส่งสำเร็จ"
        except urllib.error.HTTPError as e:
            err = _explain(e)
            if e.code in (400, 401, 403, 429):
                break   # ลองซ้ำไม่ช่วย
        except Exception as e:
            err = _explain(e)
        time.sleep(2 * (attempt + 1))
    last_error = err
    print(f"[LINE OA] ส่งแจ้งเตือนไม่สำเร็จ: {err}")
    return False, err


def _worker():
    while True:
        messages = _q.get()
        try:
            _broadcast(messages)
        except Exception:
            pass


def _enqueue(key, messages):
    global _worker_started
    with _lock:
        now = time.time()
        for k, t in list(_sent.items()):
            if now - t > 6 * 3600:
                _sent.pop(k, None)
        if key in _sent:
            return
        _sent[key] = now
        if not _worker_started:
            threading.Thread(target=_worker, daemon=True).start()
            _worker_started = True
    try:
        _q.put_nowait(messages)
    except queue.Full:
        pass


def get_quota(token=None) -> dict:
    """{limit, used, type} ของเดือนนี้ — limit None = ไม่จำกัด (แพ็กเกจเสียเงิน)"""
    token = token or get_token()
    q = _request("GET", "/message/quota", token)
    c = _request("GET", "/message/quota/consumption", token)
    return {"type": q.get("type"), "limit": q.get("value"), "used": c.get("totalUsage", 0)}


# ------------------------------------------------------------------ ข้อความ (Flex)
GREEN, RED, GOLD, GREY, DARK, TEXT = "#16A34A", "#DC2626", "#D49A16", "#8A93A3", "#14171E", "#1F2937"


def _money(v):
    return f"{'+' if v > 0 else '-' if v < 0 else ''}{abs(v):,.2f}"


def _price(v):
    return f"{float(v):,.2f}" if v else "—"


def _plan_name(plan):
    try:
        import position_chart
        return position_chart.plan_of(plan)[1]
    except Exception:
        return plan or "เข้าไม้เอง"


def _row(label, value, color=TEXT, bold=False):
    return {"type": "box", "layout": "horizontal", "margin": "sm", "contents": [
        {"type": "text", "text": label, "size": "sm", "color": GREY, "flex": 4},
        {"type": "text", "text": value, "size": "sm", "color": color, "flex": 6, "align": "end", "weight": "bold" if bold else "regular", "wrap": True},
    ]}


def _bubble(title, subtitle, color, rows, alt):
    return [{
        "type": "flex", "altText": alt[:400],
        "contents": {
            "type": "bubble", "size": "kilo",
            "header": {"type": "box", "layout": "vertical", "backgroundColor": color, "paddingAll": "12px", "contents": [
                {"type": "text", "text": title, "color": "#FFFFFF", "weight": "bold", "size": "md", "wrap": True},
                {"type": "text", "text": subtitle, "color": "#FFFFFFCC", "size": "xs", "wrap": True},
            ]},
            "body": {"type": "box", "layout": "vertical", "paddingAll": "12px", "contents": rows},
            "footer": {"type": "box", "layout": "vertical", "paddingAll": "8px", "contents": [
                {"type": "text", "text": "Gold Bot 24", "size": "xxs", "color": GREY, "align": "center"},
            ]},
        },
    }]


def close_reason(code, comment, profit):
    """เหตุผลการปิดไม้ (ใช้ร่วมกับประวัติการเทรดในโปรแกรม) → (ข้อความ, tone: green/red/gold/cyan/muted)"""
    code = -1 if code is None else int(code)
    cm = str(comment or "")
    low = cm.lower()
    if code == 5 or cm.startswith("[tp"):
        return "🎯 ชน TP", "green"
    if code == 4 or cm.startswith("[sl"):
        return ("🔒 ชน SL (ล็อกกำไร)", "green") if (profit or 0) > 0 else ("⛔ ชน SL", "red")
    if code == 6 or cm.startswith("[so"):
        return "⚠ Stop Out", "red"
    if code == 3 or cm:
        if "take profit $" in low:
            return "💰 ถึงเป้ากำไร $", "green"
        if "manual tp" in low:
            return "🎯 ถึงเป้าจุด (เข้าเอง)", "green"
        if "vol tp" in low or "volatility tp" in low:
            return "⚡ ปิดช่วงผันผวนแรง", "green"
        if "cross" in low or "exit" in low:
            return "🤖 บอทปิด · MA ตัดกลับ", "gold"
        if "reversal" in low:
            return "🤖 บอทปิด · AI กลับทิศ", "gold"
        if "manual" in low:
            return "✋ ปิดเอง (ในโปรแกรม)", "cyan"
        if "emergency" in low or "close all" in low:
            return "✋ ปิดทุกออเดอร์", "cyan"
        if code == 3:
            return "🤖 บอทปิด", "gold"
    if code in (0, 1, 2):
        return "✋ ปิดเอง (MT5)", "cyan"
    return "ปิดแล้ว", "muted"


def _duration(sec):
    sec = max(0, int(sec or 0))
    d, rem = divmod(sec, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    return f"{d} วัน {h} ชม." if d else (f"{h} ชม. {m} นาที" if h else f"{m} นาที")


def notify_open(ticket, side, plan, lot, price, sl, tp, login=None):
    if not _active("open"):
        return
    name = _plan_name(plan)
    color = GREEN if side == "BUY" else RED
    rows = [
        _row("แผน", name, bold=True),
        _row("ราคาเข้า", _price(price), bold=True),
        _row("Lot", f"{float(lot):.2f}"),
        _row("Stop Loss", _price(sl), RED),
        _row("Take Profit", _price(tp) if tp else "รันเทรนด์ (ไม่ตั้ง TP)", GREEN if tp else GREY),
        _row("เวลา", thai_time.fmt_now("%d/%m/%Y %H:%M")),
    ]
    if login:
        rows.append(_row("บัญชี MT5", f"#{login}"))
    alt = f"เข้าไม้ {side} {name} @ {_price(price)} · SL {_price(sl)} · Lot {float(lot):.2f}"
    _enqueue(("open", ticket), _bubble(f"{'▲' if side == 'BUY' else '▼'} เข้าไม้ {side} · XAUUSD", f"Ticket #{ticket}", color, rows, alt))


def notify_close(ticket, side, plan, lot, open_price, close_price, profit, reason_code=None, reason_comment="",
                 opened_at=None, closed_at=None, login=None):
    if not _active("close"):
        return
    name = _plan_name(plan)
    reason, _tone = close_reason(reason_code, reason_comment, profit)
    color = GREEN if profit > 0 else RED if profit < 0 else GREY
    rows = [
        _row("ผลลัพธ์", _money(profit), color, bold=True),
        _row("ปิดโดย", reason),
        _row("แผน", f"{name} · {side}"),
        _row("ราคาเข้า → ออก", f"{_price(open_price)} → {_price(close_price)}"),
        _row("Lot", f"{float(lot):.2f}"),
    ]
    if opened_at and closed_at:
        rows.append(_row("ถือไม้", _duration(closed_at - opened_at)))
    rows.append(_row("เวลาปิด", thai_time.fmt_now("%d/%m/%Y %H:%M")))
    if login:
        rows.append(_row("บัญชี MT5", f"#{login}"))
    word = "กำไร" if profit > 0 else "ขาดทุน" if profit < 0 else "เสมอตัว"
    alt = f"ปิดไม้ {side} {name} · {word} {_money(profit)} · {reason}"
    _enqueue(("close", ticket), _bubble(f"ปิดไม้ · {word} {_money(profit)}", f"Ticket #{ticket}", color, rows, alt))


def build_daily_summary(day):
    """สรุปของวันที่ day (date, เวลาไทย) → messages หรือ None ถ้าดึงข้อมูลไม่ได้"""
    from bot_controller import bot_ctrl
    rows = bot_ctrl.get_daily_pnl(day, day) or []
    if not rows:
        return None
    r = rows[0]
    profit, closed = float(r.get("profit") or 0.0), int(r.get("closed") or 0)
    plans = r.get("plans") or {}   # {แผน: {profit, closed, wins, losses}}
    wins = sum(int(v.get("wins") or 0) for v in plans.values())
    losses = sum(int(v.get("losses") or 0) for v in plans.values())
    best = max(plans.items(), key=lambda kv: kv[1].get("profit", 0.0)) if plans else None
    best = (best[0], float(best[1].get("profit", 0.0))) if best else None
    color = GREEN if profit > 0 else RED if profit < 0 else GOLD
    lines = [
        _row("กำไร/ขาดทุนสุทธิ", _money(profit), GREEN if profit > 0 else RED if profit < 0 else TEXT, bold=True),
        _row("ปิดไม้", f"{closed} ไม้"),
        _row("ชนะ / แพ้", f"{wins} / {losses}"),
    ]
    if wins + losses:
        lines.append(_row("อัตราชนะ", f"{wins / (wins + losses) * 100:.0f}%"))
    if best and best[1] != 0:
        lines.append(_row("แผนที่ทำได้ดีสุด", f"{_plan_name(best[0])} ({_money(best[1])})"))
    alt = f"สรุป {day.strftime('%d/%m/%Y')} · {_money(profit)} · ปิด {closed} ไม้ (ชนะ {wins}/แพ้ {losses})"
    return _bubble(f"สรุปผลวันที่ {day.strftime('%d/%m/%Y')}", "ทั้งบัญชี MT5 · รวม commission/swap", color, lines, alt)


def _scheduler():
    """ทุก 1 นาที: ถึงเวลาที่ตั้ง (เวลาไทย) และวันนี้ยังไม่ส่ง → ส่งสรุปของเมื่อวาน"""
    from datetime import timedelta
    while True:
        try:
            s = load_settings()
            now = thai_time.now()
            today = now.strftime("%Y-%m-%d")
            if s.get("enabled") and s.get("token") and s["events"].get("daily") and s.get("last_daily") != today \
                    and now.strftime("%H:%M") >= (s.get("daily_time") or "00:05"):
                msgs = build_daily_summary((now - timedelta(days=1)).date())
                if msgs:
                    ok, _ = _broadcast(msgs)
                    if ok:
                        save_settings(last_daily=today)
        except Exception:
            pass
        time.sleep(60)


def start_scheduler():
    global _scheduler_started
    if not _scheduler_started:
        _scheduler_started = True
        threading.Thread(target=_scheduler, daemon=True).start()


def send_test(token=None):
    msgs = _bubble("ทดสอบการแจ้งเตือน", "Gold Bot 24 เชื่อมต่อ LINE OA ของคุณแล้ว", GOLD,
                   [_row("สถานะ", "พร้อมแจ้งเข้าไม้ / ปิดไม้ / สรุปรายวัน", GREEN, bold=True),
                    _row("เวลา", thai_time.fmt_now("%d/%m/%Y %H:%M"))],
                   "Gold Bot 24 เชื่อมต่อ LINE OA ของคุณแล้ว")
    return _broadcast(msgs, token=token)
