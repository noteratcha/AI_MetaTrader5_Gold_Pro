import json
import urllib.request
import urllib.error
import time
import os

# โหลดค่า Supabase URL และ Key: Environment -> web/.env.local (เครื่องนักพัฒนา) -> ค่าเดียวกับ license_manager (เครื่องลูกค้า)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    env_local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", ".env.local")
    if os.path.exists(env_local_path):
        with open(env_local_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("NEXT_PUBLIC_SUPABASE_URL="):
                    SUPABASE_URL = line.split("=", 1)[1].strip()
                elif line.startswith("NEXT_PUBLIC_SUPABASE_ANON_KEY="):
                    SUPABASE_KEY = line.split("=", 1)[1].strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    # ใน build .exe ไม่มี web/.env.local — ใช้ค่า public (anon) ชุดเดียวกับ license_manager
    try:
        from license_manager import SUPABASE_URL as _LM_URL, SUPABASE_KEY as _LM_KEY
        SUPABASE_URL = SUPABASE_URL or _LM_URL
        SUPABASE_KEY = SUPABASE_KEY or _LM_KEY
    except Exception:
        pass

def _json_serial(obj):
    if hasattr(obj, 'item'):
        return obj.item()
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if hasattr(obj, 'tolist'):
        return obj.tolist()
    return str(obj)

def _make_request(endpoint, method="GET", payload=None, extra_headers=None):
    if not SUPABASE_URL or not SUPABASE_KEY or "your-project" in SUPABASE_URL:
        return None
        
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if extra_headers:
        headers.update(extra_headers)

    data = json.dumps(payload, default=_json_serial).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode("utf-8")
            if res_body:
                return json.loads(res_body)
            return True
    except Exception as e:
        # เงียบไว้เพื่อไม่ให้รบกวนลูปเทรดหลักกรณีเน็ตหลุดชั่วคราว
        return None

def update_telemetry(balance, equity, floating_profit, margin_free, open_positions, radar_signals, status="ONLINE", row_id=1):
    """ส่งสถานะพอร์ตและสัญญาณ AI ล่าสุดขึ้นไปแสดงบนเว็บ Dashboard (1 แถวต่อ 1 บัญชีผู้ใช้ GoldBot24)"""
    payload = {
        "id": int(row_id),
        "status": status,
        "balance": float(balance),
        "equity": float(equity),
        "floating_profit": float(floating_profit),
        "margin_free": float(margin_free),
        "open_positions": open_positions,
        "radar_signals": radar_signals,
        "last_heartbeat": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    extra_headers = {"Prefer": "resolution=merge-duplicates"}
    return _make_request("bot_telemetry", method="POST", payload=payload, extra_headers=extra_headers)

def log_trade(ticket, symbol, action, plan, price, lot, sl=0, tp=0, profit=0, comment="", user_id=None, email=None):
    """บันทึกประวัติการเทรดลงตาราง trade_logs บน Supabase พร้อมระบุ User ID"""
    payload = {
        "ticket": ticket,
        "symbol": symbol,
        "action": action,
        "plan": plan,
        "price": float(price),
        "lot": float(lot),
        "sl": float(sl),
        "tp": float(tp),
        "profit": float(profit),
        "comment": comment,
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    if user_id:
        payload["user_id"] = str(user_id)
    if email:
        payload["email"] = str(email)
    res = _make_request("trade_logs", method="POST", payload=payload)
    if res is None and ("user_id" in payload or "email" in payload):
        # ฐานข้อมูลที่ยังไม่ได้รัน migration จะไม่มีคอลัมน์ user_id/email — ส่งซ้ำแบบไม่ระบุผู้ใช้
        payload.pop("user_id", None)
        payload.pop("email", None)
        res = _make_request("trade_logs", method="POST", payload=payload)
    return res

def sync_user_plan_stats(user_id, email, plan_name, total_trades, win_trades, loss_trades, win_rate, total_profit, profit_factor=0.0):
    """บันทึกหรืออัปเดตสถิติการเทรดรายแผนของ User ลงตาราง user_plan_stats บน Supabase"""
    if not user_id or not plan_name:
        return None
    payload = {
        "user_id": str(user_id),
        "email": str(email or f"{user_id}@aitrade24.local"),
        "plan_name": str(plan_name),
        "total_trades": int(total_trades),
        "win_trades": int(win_trades),
        "loss_trades": int(loss_trades),
        "win_rate_pct": float(win_rate),
        "total_profit_usd": float(total_profit),
        "profit_factor": float(profit_factor),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    extra_headers = {"Prefer": "resolution=merge-duplicates"}
    return _make_request("user_plan_stats?on_conflict=user_id,plan_name", method="POST", payload=payload, extra_headers=extra_headers)

def log_risk_event(symbol, event_type, direction, message, loss=0.0):
    """บันทึก Risk Event (Circuit Breaker, Loss Block) ลงตาราง risk_events"""
    payload = {
        "symbol": symbol,
        "event_type": event_type,
        "direction": direction,
        "message": message,
        "loss_amount": float(loss),
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    return _make_request("risk_events", method="POST", payload=payload)

def log_signal(symbol, signal_type, plan, direction, price, ai_up, ai_down, h4_trend, status, detail=""):
    """บันทึกประวัติการส่งสัญญาณสำคัญลงตาราง signal_logs บน Supabase"""
    try:
        up_val = float(ai_up) if isinstance(ai_up, (int, float)) else 0.0
        down_val = float(ai_down) if isinstance(ai_down, (int, float)) else 0.0
        payload = {
            "symbol": str(symbol),
            "signal_type": str(signal_type),
            "plan": str(plan),
            "direction": str(direction),
            "price": float(price),
            "ai_up": round(up_val * 100.0, 2) if up_val <= 1.0 else round(up_val, 2),
            "ai_down": round(down_val * 100.0, 2) if down_val <= 1.0 else round(down_val, 2),
            "h4_trend": str(h4_trend),
            "status": str(status),
            "detail": str(detail),
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        return _make_request("signal_logs", method="POST", payload=payload)
    except Exception:
        return None
