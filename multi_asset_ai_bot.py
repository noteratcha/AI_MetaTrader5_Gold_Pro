import time
import threading
import json
import MetaTrader5 as mt5
import pandas as pd
import re
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import csv
import os
import winsound
import sys
import io
import builtins
import colorama
import supabase_sync
import sound_manager
import stats_manager
import plan_config
from license_manager import license_mgr
from datetime import datetime, timedelta

# เริ่มต้นระบบสี Colorama สำหรับ Windows Console ให้แสดงสีจริง ไม่ขึ้น [96m [1m
colorama.init(autoreset=False)

# เปิดระบบ ANSI VT100 ของ Windows 10/11
def enable_windows_ansi():
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_conout = kernel32.CreateFileW("CONOUT$", 0xC0000000, 3, None, 3, 0, None)
        if h_conout and h_conout != -1:
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(h_conout, ctypes.byref(mode)):
                kernel32.SetConsoleMode(h_conout, mode.value | 0x0004) # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.CloseHandle(h_conout)
    except Exception:
        pass
    os.system('') # กระตุ้น Windows Console ANSI Driver

enable_windows_ansi()

# บังคับ Flush และกำหนด Encoding UTF-8 ทันทีทุกครั้งที่มีการพิมพ์ ป้องกัน Terminal ค้าง
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
except Exception:
    pass

_orig_print = builtins.print
def _safe_print(*a, **k):
    try:
        _orig_print(*a, **dict(k, flush=True))
    except Exception:
        pass
builtins.print = _safe_print

# ฟังก์ชันป้องกันบอทค้าง: ปิด QuickEdit Mode ของ Windows Console อัตโนมัติ (ป้องกันเผลอคลิกเมาส์แล้วหยุดทำงาน)
def disable_quick_edit():
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_conin = kernel32.CreateFileW("CONIN$", 0xC0000000, 3, None, 3, 0, None)
        if h_conin and h_conin != -1:
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(h_conin, ctypes.byref(mode)):
                # 0x0040 คือ ENABLE_QUICK_EDIT_MODE, 0x0080 คือ ENABLE_EXTENDED_FLAGS (ต้องใส่คู่กัน Windows ถึงจะยอมปลดล็อค)
                new_mode = (mode.value & ~0x0040) | 0x0080
                kernel32.SetConsoleMode(h_conin, new_mode)
            kernel32.CloseHandle(h_conin)
    except Exception:
        pass

disable_quick_edit()

# เวอร์ชันและข้อมูลระบบ (System Info) - รูปแบบ: ปี.เดือนวันที่.ชั่วโมงนาที (YYYY.MMDD.HHMM)
BOT_NAME = "AI MetaTrader 5 (FBS) Gold Pro"
from version import APP_VERSION
BOT_VERSION = APP_VERSION  # แหล่งเดียว: version.py

# ตั้งค่าสำหรับระบบ AI Trading (เทรดเฉพาะ XAUUSD ทองคำ 100%)
TRADE_SYMBOLS = ["XAUUSD"] # โฟกัสเฉพาะทองคำ XAUUSD 100%
WATCH_SYMBOLS = []         # ปิดคู่เงินอื่นๆ และสินทรัพย์อื่นทั้งหมด
SYMBOLS = ["XAUUSD"]
TIMEFRAME = mt5.TIMEFRAME_M15   # กราฟ 15 นาที
TIMEFRAME_H1 = mt5.TIMEFRAME_H1  # กราฟ 1 ชั่วโมงเพื่อดูแนวรับแนวต้าน
TIMEFRAME_H4 = mt5.TIMEFRAME_H4  # กราฟ 4 ชั่วโมงเพื่อดูเทรนด์ระยะยาว
LOT = 0.01                     # ขนาด Lot เริ่มต้น
TP_RRR_XAU = 1.50              # Sweet Spot RRR สำหรับทองคำ (1:1.50 เพื่อ Win Rate 50%+)
CONFIDENCE = 0.54              # ความมั่นใจ AI ขั้นต่ำ 54%
COOLDOWN_MINUTES_XAU = 10      # Cooldown พักหลังปิดไม้สำหรับทองคำ (10 นาที)
last_exit_time = {}            # บันทึกเวลาปิดไม้ล่าสุดเพื่อคำนวณ Cooldown {sym: timestamp}

# ==================== แผนการปรับปรุงความแม่นยำสูง (v2026.1002.2225) ====================
SL_ATR_MULT = 0.75                # ขยายพื้นที่หายใจ SL = 0.75 ATR (ป้องกัน Market Noise ในแท่ง M15)
BE_LOCK_BUFFER_ATR = 0.4          # Break-Even Lock ต้องมี buffer ≥ 0.4 ATR จากราคาตลาดก่อน lock
LOCK_SL_THROTTLE_SECS = 60       # [Priority 2] ห้าม modify position ซ้ำภายใน 60 วินาที (ป้องกัน double-lock)
SAME_PLAN_COOLDOWN_MINUTES = 60  # [Priority 4] ห้ามเข้าแผนเดิม + สกุลเดิม (ทิศเดิม) ภายใน 60 นาที
MAX_CONSECUTIVE_LOSS = 2          # [Priority 1] Circuit Breaker: ขาดทุนติดกันกี่ไม้ถึงหยุด
CIRCUIT_BREAKER_MINUTES = 60     # [Priority 1] Circuit Breaker: หยุดกี่นาทีหลังโดน Circuit Breaker
MARGIN_PER_TRADE = 400            # Max Positions: มาจินทุก $400 เปิดได้ 1 ไม้ (free margin based)

# State variables สำหรับระบบ Risk Management
consecutive_loss = {}             # {sym: int} นับขาดทุนติดต่อกัน
last_lock_time = {}               # {ticket: timestamp} ป้องกัน Lock SL ซ้ำใน 60 วินาที
_p1_filter_logged = {}           # {sym: bar_key} พิมพ์เหตุผลตัวกรองสัญญาณหลอก Plan 1 ครั้งเดียวต่อแท่ง
last_loss_plan = {}               # {sym: {direction: (plan_name, timestamp)}} บันทึกเฉพาะไม้ขาดทุน — block 60 นาที
from app_paths import data_path as _data_path
# ไฟล์ประวัติทั้งหมดเก็บใน %APPDATA%\GoldBot24 (ไม่ขึ้นกับโฟลเดอร์ที่เปิดโปรแกรม และไม่หายเมื่ออัปเดต/ถอนการติดตั้ง)
TRADE_HISTORY_CSV = _data_path('trade_history.csv')
TRADE_MODS_CSV = _data_path('trade_modifications.csv')
SIGNAL_HISTORY_CSV = _data_path('signal_history.csv')
last_cross_entry_bar = {}         # {(sym, plan, direction): bar_time} กันเข้าไม้ Plan 1/2 ซ้ำบนแท่ง Cross เดิม

# Step Trailing SL (แผน MA M15 + MA H1): ทุกกำไร 5 จุด (= $5 ที่ 0.01 lot) เลื่อน SL เข้าหาราคา 40% ของระยะ SL → ราคา
# Backtest 2.5 ปี (กฎ MA100/150/200 + MA5×MA13): กำไร 898 → 885 จุด (เท่าเดิม), PF 1.13 → 1.17, Max DD 346 → 245
P4_TRAIL_STEP_POINTS = 5.0
P4_TRAIL_FRACTION = 0.40
P4_TRAIL_STATE_FILE = _data_path('p4_trail_state.json')


def _load_p4_trail_state():
    try:
        with open(P4_TRAIL_STATE_FILE, 'r', encoding='utf-8') as f:
            return {int(k): int(v) for k, v in json.load(f).items()}
    except Exception:
        return {}


def _save_p4_trail_state(state):
    try:
        with open(P4_TRAIL_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({str(k): v for k, v in state.items()}, f)
    except Exception:
        pass


p4_trail_steps = _load_p4_trail_state()   # {ticket: จำนวนขั้นที่เลื่อน SL ไปแล้ว} — เก็บลงไฟล์ กันเลื่อนซ้ำเมื่อรีสตาร์ทบอท


def apply_p4_step_trailing(pos, tick, info):
    """เลื่อน SL ของไม้ Plan 1 ตามขั้นกำไร (คืน True ถ้ามีการเลื่อน)"""
    if pos.sl is None or pos.sl <= 0 or tick is None:
        return False
    d = 1 if pos.type == mt5.ORDER_TYPE_BUY else -1
    price = tick.bid if d == 1 else tick.ask
    profit_pts = (price - pos.price_open) * d
    reached = int(profit_pts // P4_TRAIL_STEP_POINTS) if profit_pts > 0 else 0
    done = p4_trail_steps.get(pos.ticket, 0)
    if reached <= done:
        return False
    new_sl = float(pos.sl)
    for k in range(done + 1, reached + 1):
        step_px = pos.price_open + d * k * P4_TRAIL_STEP_POINTS        # ราคาตอนกำไรถึงขั้นที่ k
        new_sl = new_sl + d * P4_TRAIL_FRACTION * abs(step_px - new_sl)  # เลื่อน 40% ของระยะ SL → ราคา
    # ระยะห่างขั้นต่ำจากราคาตามที่โบรกเกอร์กำหนด (stops level)
    min_gap = 0.0
    if info is not None:
        min_gap = max(float(getattr(info, 'trade_stops_level', 0) or 0), float(getattr(info, 'spread', 0) or 0)) * float(info.point)
    if d == 1:
        new_sl = min(new_sl, price - min_gap)
        improved = new_sl > float(pos.sl)
    else:
        new_sl = max(new_sl, price + min_gap)
        improved = new_sl < float(pos.sl)
    p4_trail_steps[pos.ticket] = reached
    _save_p4_trail_state(p4_trail_steps)
    if not improved:
        return False
    modify_position(pos, round(new_sl, 2), pos.tp, reason=f"P4 Step Trail +{reached * P4_TRAIL_STEP_POINTS:.0f} pts")
    return True

_telemetry_thread = None          # เธรดสตรีม Telemetry (เริ่มครั้งเดียวต่อโปรเซส)
_self_closed_tickets = set()      # ticket ที่บอทปิดเองผ่าน close_position() — กันนับขาดทุน/Circuit Breaker ซ้ำ
_plan_disabled_logged = {}        # {(sym, plan): timestamp} แจ้งเตือนแผนที่ถูกปิดไม่เกินทุก 10 นาที

# Bot Running & Pause Controls (สำหรับการเชื่อมต่อกับ GUI Launcher)
BOT_RUNNING_FLAG = True
BOT_PAUSED_FLAG = False

# ที่เก็บข้อมูลสัญญาณเรดาร์แบบ Real-time ให้ Background Thread ดึงไปสตรีมขึ้นเว็บ
latest_radar_cache = {
    "XAUUSD": {"symbol": "XAUUSD", "status": "[WAIT OUTSIDE ZONE]", "up_prob": 0.50, "price": 0.0, "is_in_zone": False, "h4_trend": "ANALYZING...", "h4_diff_pct": 0.0, "h1_trend": "ANALYZING...", "h1_diff_pct": 0.0}
}

def telemetry_background_worker():
    """เธรดเบื้องหลัง: สตรีมยอดเงิน, กำไรลอยตัว (Floating P&L) และเรดาร์ AI สดไปยัง Supabase Cloud ทุกๆ 5 วินาที"""
    global latest_radar_cache
    while True:
        try:
            acc_info = mt5.account_info()
            if acc_info is not None:
                open_pos_list = []
                all_positions = mt5.positions_get()
                if all_positions:
                    for p in all_positions:
                        open_pos_list.append({
                            "ticket": int(p.ticket),
                            "symbol": str(p.symbol),
                            "type": "BUY" if p.type == 0 else "SELL",
                            "price_open": float(p.price_open),
                            "sl": float(p.sl),
                            "tp": float(p.tp),
                            "volume": float(p.volume),
                            "profit": round(float(p.profit), 2),
                            "plan": str(p.comment)
                        })
                
                # ประกอบข้อมูลเรดาร์ AI เฉพาะ BTCUSD และ XAUUSD
                current_radar = []
                for s in TRADE_SYMBOLS:
                    cached = latest_radar_cache.get(s, {})
                    t = mt5.symbol_info_tick(s)
                    p_val = cached.get("price") if cached.get("price") else (t.bid if t else 0.0)
                    status_text = cached.get("status", "[WAIT OUTSIDE ZONE]")
                    up_p = cached.get("up_prob", 0.50)
                    is_in = bool(cached.get("is_in_zone", False))
                    h4_tr = str(cached.get("h4_trend", "ANALYZING..."))
                    h4_df = float(cached.get("h4_diff_pct", 0.0))
                    h1_tr = str(cached.get("h1_trend", "ANALYZING..."))
                    h1_df = float(cached.get("h1_diff_pct", 0.0))
                    sr_fields = {k: round(float(cached.get(k, 0.0) or 0.0), 2) for k in ("h1_support", "h1_resistance", "h4_support", "h4_resistance")}
                    sr_fields.update({k: int(cached.get(k, 0) or 0) for k in ("h1_lt_dir", "h4_lt_dir", "h1_dir", "h4_dir", "h1_stack_dir", "h4_stack_dir", "h1_cond", "h4_cond")})
                    sr_fields.update({k: round(float(cached.get(k, 0.0) or 0.0), 2) for k in ("h1_cond_pct", "h4_cond_pct")})
                    
                    current_radar.append({
                        "symbol": str(s),
                        "price": float(p_val),
                        "up_prob": round(float(up_p), 4),
                        "status": str(status_text),
                        "in_zone": is_in,
                        "h4_trend": h4_tr,
                        "h4_diff_pct": round(h4_df, 2),
                        "h1_trend": h1_tr,
                        "h1_diff_pct": round(h1_df, 2),
                        **sr_fields,
                        # บัญชี MT5 ที่บอทกำลังเชื่อมต่อ (แสดงบนเว็บ)
                        "account": {
                            "login": int(acc_info.login),
                            "server": str(acc_info.server),
                            "name": str(acc_info.name),
                            "company": str(acc_info.company),
                            "currency": str(acc_info.currency),
                            "leverage": int(acc_info.leverage),
                            "mode": "DEMO" if int(acc_info.trade_mode) == 0 else ("CONTEST" if int(acc_info.trade_mode) == 1 else "REAL"),
                            "lot": float(current_lot()),
                        },
                    })

                # แยกแถว Telemetry ตามบัญชีผู้ใช้ GoldBot24 (id ใน bot_config) — ลูกค้าแต่ละคนเห็นเฉพาะพอร์ตตัวเอง
                cur_user = license_mgr.get_current_user()
                try:
                    row_id = int(cur_user.get("user_id") or 0)
                except (TypeError, ValueError):
                    row_id = 0
                if row_id <= 1:
                    time.sleep(5)
                    continue  # ยังไม่ได้ล็อกอิน — ไม่สตรีมขึ้นแถวรวม

                supabase_sync.update_telemetry(
                    balance=float(acc_info.balance),
                    equity=float(acc_info.equity),
                    floating_profit=float(acc_info.profit),
                    margin_free=float(acc_info.margin_free),
                    open_positions=open_pos_list,
                    radar_signals=current_radar,
                    status=f"{'PAUSED' if BOT_PAUSED_FLAG else 'ONLINE'} v{BOT_VERSION}",
                    row_id=row_id
                )
        except Exception as telem_err:
            pass
        time.sleep(5) # อัปเดตข้อมูลขึ้นคลาวด์ทุกๆ 5 วินาทีสดๆ

# สีสำหรับ Terminal UI (ทำงานร่วมกับ Colorama บน Windows 100%)
class Colors:
    RESET = colorama.Style.RESET_ALL
    GREEN = colorama.Fore.GREEN
    RED = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    CYAN = colorama.Fore.CYAN
    BOLD = colorama.Style.BRIGHT

def get_data(symbol, timeframe, n_bars):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_bars)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def add_divergence_features(df, lookback=14):
    """
    วิเคราะห์สัญญาณ Divergence ระหว่าง Price Action และ RSI (M15)
    - bull_div: Regular Bullish Divergence (ราคาทำ Lower Low แต่ RSI ทำ Higher Low -> สัญญาณกลับตัวขึ้น)
    - bear_div: Regular Bearish Divergence (ราคาทำ Higher High แต่ RSI ทำ Lower High -> สัญญาณกลับตัวลง)
    - hidden_bull: Hidden Bullish Divergence (ราคาทำ Higher Low แต่ RSI ทำ Lower Low -> ย่อเพื่อไปต่อ)
    - hidden_bear: Hidden Bearish Divergence (ราคาทำ Lower High แต่ RSI ทำ Higher High -> เด้งเพื่อลงต่อ)
    """
    n = len(df)
    bull_div = np.zeros(n)
    bear_div = np.zeros(n)
    hidden_bull = np.zeros(n)
    hidden_bear = np.zeros(n)
    
    rec_size = 3
    if n < lookback + rec_size + 2:
        df['bull_div'] = 0.0
        df['bear_div'] = 0.0
        df['hidden_bull'] = 0.0
        df['hidden_bear'] = 0.0
        return df

    try:
        from numpy.lib.stride_tricks import sliding_window_view
        low = df['low'].values
        high = df['high'].values
        rsi = df['rsi'].values
        
        pri_low_wins = sliding_window_view(low[:-rec_size], lookback)
        pri_high_wins = sliding_window_view(high[:-rec_size], lookback)
        pri_rsi_wins = sliding_window_view(rsi[:-rec_size], lookback)
        
        rec_low_wins = sliding_window_view(low[lookback:], rec_size)
        rec_high_wins = sliding_window_view(high[lookback:], rec_size)
        rec_rsi_wins = sliding_window_view(rsi[lookback:], rec_size)
        
        num_windows = min(len(pri_low_wins), len(rec_low_wins))
        
        pri_min_idx = np.argmin(pri_low_wins[:num_windows], axis=1)
        pri_low = np.take_along_axis(pri_low_wins[:num_windows], pri_min_idx[:, None], axis=1).squeeze()
        pri_low_rsi = np.take_along_axis(pri_rsi_wins[:num_windows], pri_min_idx[:, None], axis=1).squeeze()
        
        pri_max_idx = np.argmax(pri_high_wins[:num_windows], axis=1)
        pri_high = np.take_along_axis(pri_high_wins[:num_windows], pri_max_idx[:, None], axis=1).squeeze()
        pri_high_rsi = np.take_along_axis(pri_rsi_wins[:num_windows], pri_max_idx[:, None], axis=1).squeeze()
        
        rec_min_idx = np.argmin(rec_low_wins[:num_windows], axis=1)
        rec_low = np.take_along_axis(rec_low_wins[:num_windows], rec_min_idx[:, None], axis=1).squeeze()
        rec_low_rsi = np.take_along_axis(rec_rsi_wins[:num_windows], rec_min_idx[:, None], axis=1).squeeze()
        
        rec_max_idx = np.argmax(rec_high_wins[:num_windows], axis=1)
        rec_high = np.take_along_axis(rec_high_wins[:num_windows], rec_max_idx[:, None], axis=1).squeeze()
        rec_high_rsi = np.take_along_axis(rec_rsi_wins[:num_windows], rec_max_idx[:, None], axis=1).squeeze()
        
        b_div = (rec_low < pri_low) & (rec_low_rsi > pri_low_rsi + 1.0) & (rec_low_rsi < 60)
        be_div = (rec_high > pri_high) & (rec_high_rsi < pri_high_rsi - 1.0) & (rec_high_rsi > 40)
        h_bull = (rec_low > pri_low) & (rec_low_rsi < pri_low_rsi - 1.0) & (rec_low_rsi < 60)
        h_bear = (rec_high < pri_high) & (rec_high_rsi > pri_high_rsi + 1.0) & (rec_high_rsi > 40)
        
        offset = lookback + rec_size - 1
        bull_div[offset:offset+num_windows] = b_div.astype(float)
        bear_div[offset:offset+num_windows] = be_div.astype(float)
        hidden_bull[offset:offset+num_windows] = h_bull.astype(float)
        hidden_bear[offset:offset+num_windows] = h_bear.astype(float)
    except Exception:
        pass
        
    df['bull_div'] = bull_div
    df['bear_div'] = bear_div
    df['hidden_bull'] = hidden_bull
    df['hidden_bear'] = hidden_bear
    return df

# =============================================================================
# AI ทำนายทิศราคา (Random Forest)
#   - ทายว่า "อีก 2 ชั่วโมง (8 แท่ง M15) ราคาปิดจะสูงกว่าตอนนี้ไหม" → prob[1] = ขึ้น, prob[0] = ลง
#   - Features 24 ตัว ปรับด้วย ATR ทั้งหมด (ไม่ขึ้นกับระดับราคาทอง) และใช้ H1/H4 จาก "แท่งที่ปิดแล้ว" เท่านั้น
#     (เดิม merge ด้วยชั่วโมงของแท่ง ทำให้ตอนเทรนเห็นราคาปิดในอนาคต และตอนใช้จริงอ่านแท่งที่ยังไม่ปิด)
#   - Walk-forward 2.5 ปี: เดิม AUC 0.515 / แม่นตอนมั่นใจ 52.7% → ใหม่ AUC 0.525 / 54.0%
#     (ราคาทองทายทิศยากมาก — AI เป็นตัวช่วยประกอบ ไม่ใช่ตัวตัดสินหลัก)
# =============================================================================
AI_HORIZON_BARS = 8
AI_FEATURES = ['r1', 'r4', 'r16', 'r64', 'trend', 'slope10', 'rsi', 'bb_pos', 'atr_rel', 'atr_ratio',
               'h1_trend', 'h1_slope', 'h1_r4', 'h4_trend', 'h4_slope', 'h4_r4', 'h4_p200',
               'res_atr', 'sup_atr', 'lower_wick_ratio', 'upper_wick_ratio', 'hour_sin', 'hour_cos', 'dow']
last_ai_quality = {}  # {symbol: {"auc": float, "acc": float, "n": int}} ผลวัดล่าสุดตอนเทรน


def _atr_series(d, n=14):
    tr = pd.concat([d['high'] - d['low'], (d['high'] - d['close'].shift()).abs(), (d['low'] - d['close'].shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def _htf_ai_features(d, minutes, prefix):
    """ค่าของ Timeframe ใหญ่ที่ "รู้ได้" เมื่อแท่งนั้นปิดแล้ว (avail = เวลาเปิด + ความยาวแท่ง)"""
    v = pd.DataFrame({'avail': d['time'] + pd.Timedelta(minutes=minutes)})
    m10, m30, m200 = d['close'].rolling(10).mean(), d['close'].rolling(30).mean(), d['close'].rolling(200).mean()
    a = _atr_series(d)
    v[prefix + 'trend'] = m10 / m30 - 1
    v[prefix + 'slope'] = (m10 - m10.shift(3)) / a
    v[prefix + 'r4'] = (d['close'] - d['close'].shift(4)) / a
    v[prefix + 'p200'] = (d['close'] - m200) / a
    if prefix == 'h1_':
        v['res_h1'] = d['high'].shift(1).rolling(20).max()
        v['sup_h1'] = d['low'].shift(1).rolling(20).min()
    return v


def build_ai_features(df_m15, df_h1, df_h4):
    """สร้าง Features ของ AI สำหรับทุกแท่ง M15 (ไม่มีข้อมูลอนาคต) — ใช้ร่วมกันทั้งตอนเทรนและตอนใช้งานจริง"""
    df = df_m15[['time', 'open', 'high', 'low', 'close']].copy()
    df['close_time'] = df['time'] + pd.Timedelta(minutes=15)
    a = _atr_series(df)
    for k in (1, 4, 16, 64):
        df[f'r{k}'] = (df['close'] - df['close'].shift(k)) / a
    ma10, ma30 = df['close'].rolling(10).mean(), df['close'].rolling(30).mean()
    df['trend'] = ma10 / ma30
    df['slope10'] = (ma10 - ma10.shift(4)) / a
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    mid, sd = df['close'].rolling(20).mean(), df['close'].rolling(20).std()
    df['bb_pos'] = (df['close'] - mid) / (2 * sd + 1e-9)
    df['atr_rel'] = a / df['close'] * 100
    df['atr_ratio'] = a / a.rolling(96).mean()
    df['lower_wick_ratio'] = (np.minimum(df['open'], df['close']) - df['low']) / (a + 1e-9)
    df['upper_wick_ratio'] = (df['high'] - np.maximum(df['open'], df['close'])) / (a + 1e-9)
    hr = df['time'].dt.hour + df['time'].dt.minute / 60
    df['hour_sin'], df['hour_cos'] = np.sin(2 * np.pi * hr / 24), np.cos(2 * np.pi * hr / 24)
    df['dow'] = df['time'].dt.dayofweek
    df['atr_m15'] = a
    df = df.sort_values('close_time')
    df = pd.merge_asof(df, _htf_ai_features(df_h1, 60, 'h1_').sort_values('avail'), left_on='close_time', right_on='avail', direction='backward').drop(columns='avail')
    df = pd.merge_asof(df, _htf_ai_features(df_h4, 240, 'h4_').sort_values('avail'), left_on='close_time', right_on='avail', direction='backward').drop(columns='avail')
    df['res_atr'] = (df['res_h1'] - df['close']) / df['atr_m15']
    df['sup_atr'] = (df['close'] - df['sup_h1']) / df['atr_m15']
    return df.reset_index(drop=True)


def get_data_and_train(symbol):
    """เทรน AI ด้วยข้อมูลล่าสุด + วัดความแม่นยำกับช่วงท้ายที่โมเดลไม่เคยเห็น (Holdout 20%)"""
    df_m15 = get_data(symbol, TIMEFRAME, 5000)
    df_h1 = get_data(symbol, TIMEFRAME_H1, 1500)
    df_h4 = get_data(symbol, TIMEFRAME_H4, 600)
    if df_m15 is None or df_h1 is None or df_h4 is None:
        return None, None

    df = build_ai_features(df_m15, df_h1, df_h4)
    future = df['close'].shift(-AI_HORIZON_BARS)
    df['target'] = (future > df['close']).astype(int)
    df = df[future.notna()]
    df = df.dropna(subset=AI_FEATURES)
    if len(df) < 1000:
        return None, None
    X, y = df[AI_FEATURES], df['target']

    # วัดผลกับ 20% ล่าสุด (เว้นช่องว่างเท่าระยะทาย กันคำตอบซ้อนกัน)
    try:
        from sklearn.metrics import roc_auc_score
        cut = int(len(df) * 0.8)
        probe = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, n_jobs=-1)
        probe.fit(X.iloc[:cut - AI_HORIZON_BARS], y.iloc[:cut - AI_HORIZON_BARS])
        p_hold = probe.predict_proba(X.iloc[cut:])[:, 1]
        y_hold = y.iloc[cut:]
        auc = float(roc_auc_score(y_hold, p_hold)) if y_hold.nunique() > 1 else 0.5
        acc = float(((p_hold >= 0.5) == (y_hold == 1)).mean())
        last_ai_quality[symbol] = {"auc": round(auc, 3), "acc": round(acc * 100, 1), "n": int(len(y_hold))}
        grade = "ใช้ได้" if auc >= 0.55 else ("พอใช้" if auc >= 0.52 else "อ่อน (ใกล้เดาสุ่ม)")
        print(f"{Colors.CYAN}[AI QUALITY] {symbol} ทายล่วงหน้า {AI_HORIZON_BARS * 15} นาที · Holdout {len(y_hold)} แท่ง: "
              f"แม่นยำ {acc:.1%} · AUC {auc:.3f} → {grade}{Colors.RESET}")
    except Exception as e:
        print(f"[WARN] วัดคุณภาพ AI ไม่สำเร็จ: {e}")

    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, n_jobs=-1)
    model.fit(X, y)
    return model, AI_FEATURES

def get_filling_type(symbol_info):
    if symbol_info is None:
        return mt5.ORDER_FILLING_IOC
    filling = symbol_info.filling_mode
    if (filling & 2) != 0:
        return mt5.ORDER_FILLING_IOC
    elif (filling & 1) != 0:
        return mt5.ORDER_FILLING_FOK
    else:
        return mt5.ORDER_FILLING_RETURN

BOT_SETTINGS_FILE = _data_path('bot_settings.json')   # {"lot": 0.01} — ตั้งจากหน้าโปรแกรม
_lot_cache = {"mtime": None, "lot": LOT}


def current_lot():
    """ขนาดไม้ที่ผู้ใช้ตั้งไว้ (ค่าเริ่มต้น 0.01) — อ่านใหม่เมื่อไฟล์ตั้งค่าเปลี่ยน"""
    try:
        mtime = os.path.getmtime(BOT_SETTINGS_FILE)
        if mtime != _lot_cache["mtime"]:
            with open(BOT_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                lot = float(json.load(f).get("lot", LOT))
            _lot_cache.update(mtime=mtime, lot=min(max(lot, 0.01), 100.0))
    except Exception:
        _lot_cache.update(mtime=None, lot=LOT)
    return _lot_cache["lot"]


def get_valid_lot(symbol_info, base_lot=None):
    if base_lot is None:
        base_lot = current_lot()
    if symbol_info is None:
        return base_lot
    min_vol = symbol_info.volume_min
    max_vol = symbol_info.volume_max
    step = symbol_info.volume_step if symbol_info.volume_step > 0 else 0.01
    vol = max(base_lot, min_vol)
    vol = min(vol, max_vol)
    vol = round(round(vol / step) * step, 2)
    return vol

def play_celebration_sound():
    """เล่นเสียงดีใจเมื่อเข้าไม้ออเดอร์สำเร็จ (Joyful Victory Fanfare 🎺✨)"""
    try:
        # ทำนองเพลงยินดี/ฉลองเข้าไม้: โด - มี - ซอล - โด๊ววว!
        notes = [
            (523, 120),  # C5 (โด)
            (659, 120),  # E5 (มี)
            (784, 120),  # G5 (ซอล)
            (1046, 380), # C6 (โด๊ววว ไฮโน้ตยาว)
        ]
        for freq, dur in notes:
            winsound.Beep(freq, dur)
            time.sleep(0.04)
    except Exception:
        pass

_ANSI_RE = re.compile(r"\[[0-9;]*m")


def strip_ansi(text) -> str:
    """ตัดรหัสสีของ Console (ANSI) ออก ก่อนส่งข้อความขึ้นเว็บ/ฐานข้อมูล"""
    return _ANSI_RE.sub("", str(text or ""))


TREND_SLOPE_TOL_ATR = 0.1  # ยอมให้ MA10 แบน/สวนเล็กน้อยได้ไม่เกิน 0.1 ATR (Backtest: P4 กำไร 1336 → 1463, P5 991 → 1107)


def closed_trend(ma_fast, ma_slow, slope_bars=3, atr=None, tol=TREND_SLOPE_TOL_ATR):
    """
    เทรนด์จาก "แท่งที่ปิดแล้ว" (ไม่ Repaint ตามราคาที่วิ่งอยู่ในแท่ง)
    คืน (is_up, diff_pct, direction) — direction = +1 ขาขึ้นจริง (MA10 > MA30 และ MA10 ชันขึ้น),
    -1 ขาลงจริง (MA10 < MA30 และ MA10 ชันลง), 0 = MA10 กำลังกลับตัว (ยังไม่ยืนยันเทรนด์)
    ถ้าส่ง atr มา: ความชันวัดเป็นหน่วย ATR และยอมให้ MA10 สวนทางได้ไม่เกิน tol (แบนถือว่ายังเป็นเทรนด์เดิม)
    Backtest 2.5 ปี: อ่านจากแท่งที่ปิด + ความชัน ทำให้ Plan 1 กำไร 816 → 1228 จุด (DD 413 → 264)
    """
    if len(ma_fast) < slope_bars + 2:
        return False, 0.0, 0
    f, sl, f_prev = ma_fast.iloc[-2], ma_slow.iloc[-2], ma_fast.iloc[-2 - slope_bars]
    if pd.isna(f) or pd.isna(sl) or sl == 0:
        return False, 0.0, 0
    is_up = bool(f > sl)
    diff = float((f / sl - 1.0) * 100.0)
    if pd.isna(f_prev):
        return is_up, diff, 0
    slope = f - f_prev
    if atr is not None and len(atr) >= 2 and pd.notna(atr.iloc[-2]) and atr.iloc[-2] > 0:
        slope = slope / atr.iloc[-2]
        direction = 1 if (is_up and slope > -tol) else (-1 if (not is_up and slope < tol) else 0)
    else:
        direction = 1 if (is_up and slope > 0) else (-1 if (not is_up and slope < 0) else 0)
    return is_up, diff, direction


def long_term_dir(close, fast=None, slow=200):
    """
    เทรนด์ระยะยาวจาก 200 แท่ง (แท่งที่ปิดแล้ว):
      fast=None → ราคาปิดเหนือ MA200 = +1 / ใต้ = -1
      fast=50   → MA50 เหนือ MA200 = +1 / ใต้ = -1
    ข้อมูลไม่พอ (น้อยกว่า 200 แท่ง) คืน 0 = ไม่อนุญาตเข้าไม้
    """
    if close is None or len(close) < slow + 2:
        return 0, float('nan')
    ma_slow = close.rolling(slow).mean().iloc[-2]
    ref = close.iloc[-2] if fast is None else close.rolling(fast).mean().iloc[-2]
    if pd.isna(ma_slow) or pd.isna(ref):
        return 0, float('nan')
    return (1 if ref > ma_slow else -1), float(ma_slow)


SR_LOOKBACK_BARS = 500   # แนวรับ/ต้าน: ดูย้อนหลัง 500 แท่ง (H1 และ H4)
SR_PIVOT_K = 3           # Swing High/Low = สูง/ต่ำสุดเมื่อเทียบ 3 แท่งซ้าย-ขวา
SR_ZONE_ATR = 0.5        # รวมจุดกลับตัวที่ห่างกันไม่เกิน 0.5 ATR เป็นโซนเดียวกัน
SR_MIN_TOUCHES = 2       # โซนที่ใช้ได้ต้องมีราคากลับตัวอย่างน้อย 2 ครั้ง


def find_sr_levels(df, price, lookback=SR_LOOKBACK_BARS, k=SR_PIVOT_K, zone_atr=SR_ZONE_ATR):
    """
    หาแนวรับ/แนวต้านจากโซนที่ราคาเคยกลับตัวในแท่งที่ปิดแล้วย้อนหลัง `lookback` แท่ง
    คืน dict: support / resistance (ราคากลางโซนที่ใกล้ราคาปัจจุบันที่สุด) และจำนวนครั้งที่ราคาแตะ
    - แนวรับ = โซนที่อยู่ใต้ราคา, แนวต้าน = โซนที่อยู่เหนือราคา (เลือกโซนที่แตะ >= 2 ครั้งก่อน)
    - ถ้าไม่พบโซน ใช้ Low ต่ำสุด / High สูงสุดของช่วงแทน
    """
    out = {"support": float('nan'), "resistance": float('nan'), "sup_touches": 0, "res_touches": 0}
    if df is None or len(df) < 2 * k + 10 or not price or pd.isna(price):
        return out
    d = df.iloc[-(lookback + 1):-1]  # เฉพาะแท่งที่ปิดแล้ว
    atr = _atr_series(df).iloc[-2]
    if pd.isna(atr) or atr <= 0:
        atr = float((d['high'] - d['low']).mean() or 1.0)
    win = 2 * k + 1
    piv_hi = d['high'][d['high'] == d['high'].rolling(win, center=True).max()]
    piv_lo = d['low'][d['low'] == d['low'].rolling(win, center=True).min()]
    pts = sorted([float(x) for x in pd.concat([piv_hi, piv_lo]).dropna().values])
    zones = []  # [ราคากลาง, จำนวนครั้ง, ราคาต่ำสุดของโซน] — ความกว้างโซนทั้งหมดไม่เกิน zone_atr × ATR
    for x in pts:
        if zones and x - zones[-1][2] <= zone_atr * atr:
            z = zones[-1]
            z[1] += 1
            z[0] = z[0] + (x - z[0]) / z[1]
        else:
            zones.append([x, 1, x])
    below = [z for z in zones if z[0] < price]
    above = [z for z in zones if z[0] > price]
    strong_below = [z for z in below if z[1] >= SR_MIN_TOUCHES] or below
    strong_above = [z for z in above if z[1] >= SR_MIN_TOUCHES] or above
    if strong_below:
        z = max(strong_below, key=lambda z: z[0])
        out["support"], out["sup_touches"] = round(z[0], 2), int(z[1])
    else:
        out["support"] = float(d['low'].min())
    if strong_above:
        z = min(strong_above, key=lambda z: z[0])
        out["resistance"], out["res_touches"] = round(z[0], 2), int(z[1])
    else:
        out["resistance"] = float(d['high'].max())
    return out


def ma_condition(close, periods=(50, 100, 150)):
    """สภาวะตลาด (แสดงผล): MA50 < MA100 < MA150 = ขาลง (-1) · MA50 > MA100 > MA150 = ขาขึ้น (+1) · แบบอื่น = ไซด์เวย์ (0)"""
    if close is None or len(close) < max(periods) + 2:
        return 0, 0.0
    vals = [close.rolling(n).mean().iloc[-2] for n in periods]
    if any(pd.isna(v) for v in vals):
        return 0, 0.0
    pct = float((vals[0] / vals[-1] - 1.0) * 100.0)
    if vals[0] < vals[1] < vals[2]:
        return -1, pct
    if vals[0] > vals[1] > vals[2]:
        return 1, pct
    return 0, pct


def check_h4_confluence(direction, is_uptrend_h4, prob_up, prob_down, bull_div, bear_div, hidden_bull=False, hidden_bear=False, is_sideway_h4=False, h4_diff_pct=0.0):
    """
    Dynamic H4 Market Regime & Trend Confluence Filter (v2026.1002.2225)
    - สภาวะ Sideway (is_sideway_h4=True): ตลาดแกว่งตัวในกรอบ อนุมัติการเทรดแบบ Range Play ทั้งสองฝั่ง
    - ทิศทางเดียวกับ H4 (Pro-trend): ผ่านฉลุยตามเกณฑ์ปกติ
    - ทิศทางสวน H4 (Counter-trend): บล็อก 100% (Strict Pro-Trend Only เพื่อกำจัดความเสี่ยงรับมีดและดัน Win Rate สู่ 45-50%)
    """
    if is_sideway_h4:
        return True, "SIDEWAY REGIME [~] (Range Play Approved)"

    if direction == 'BUY':
        if is_uptrend_h4:
            return True, "PRO-TREND (H4 Bullish [^])"
        return False, f"STRICT PRO-TREND: Blocked Counter-Trend BUY in H4 Bearish ({h4_diff_pct:.2f}%)"
    else: # SELL
        if not is_uptrend_h4:
            return True, "PRO-TREND (H4 Bearish [v])"
        return False, f"STRICT PRO-TREND: Blocked Counter-Trend SELL in H4 Bullish (+{h4_diff_pct:.2f}%)"

_last_logged_signals = {}  # key: (symbol, signal_type, plan, direction) -> (timestamp, status, divergence)

def log_signal_event(symbol, signal_type, plan, direction, price, ai_up, ai_down, h4_trend, divergence="None", status="ALERT", detail="", throttle_secs=180):
    """
    บันทึกประวัติการส่งสัญญาณสำคัญ (Signal History Logging)
    ลงทั้งไฟล์ CSV 'signal_history.csv' และ Supabase Cloud:
    - signal_type: 'ZONE_ALERT', 'ENTRY_SIGNAL', 'H4_FILTERED', 'RISK_BLOCKED', 'DIVERGENCE', 'POSITION_MGMT'
    - status: 'ORDER_SENT', 'WAIT_AI_CONFIRM', 'H4_BLOCKED', 'PLAN_BLOCKED', 'COOLDOWN_BLOCKED', 'CIRCUIT_BREAKER', 'MAX_POS_BLOCKED', 'REVERSAL_EXIT', 'LOCK_SL'
    """
    plan, detail, status, divergence = strip_ansi(plan), strip_ansi(detail), strip_ansi(status), strip_ansi(divergence)
    global _last_logged_signals
    now = time.time()
    key = (symbol, signal_type, plan, direction)
    
    # สำหรับ ENTRY_SIGNAL (ยิงออเดอร์) ไม่ throttle บันทึกทันที 100%
    if signal_type != 'ENTRY_SIGNAL':
        if key in _last_logged_signals:
            last_time, last_status, last_div = _last_logged_signals[key]
            # ถ้าสถานะเดิม ไดเวอร์เจนซ์เดิม และยังไม่พ้น throttle -> ข้ามการบันทึกซ้ำ ป้องกันไฟล์บวม
            if status == last_status and divergence == last_div and (now - last_time) < throttle_secs:
                return False
                
    _last_logged_signals[key] = (now, status, divergence)
    time_str = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 1. บันทึกลงไฟล์ signal_history.csv
    sig_file = SIGNAL_HISTORY_CSV
    sig_exists = os.path.isfile(sig_file)
    try:
        with open(sig_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not sig_exists:
                writer.writerow([
                    'Time', 'Symbol', 'Signal_Type', 'Plan', 'Direction', 
                    'Price', 'AI_Up', 'AI_Down', 'H4_Trend', 'Divergence', 'Status', 'Detail'
                ])
            up_str = f"{ai_up:.2%}" if isinstance(ai_up, float) and ai_up <= 1.0 else str(ai_up)
            down_str = f"{ai_down:.2%}" if isinstance(ai_down, float) and ai_down <= 1.0 else str(ai_down)
            try:
                price_str = f"{float(price):.2f}"
            except Exception:
                price_str = str(price)
            writer.writerow([
                time_str,
                symbol,
                signal_type,
                plan,
                direction,
                price_str,
                up_str,
                down_str,
                h4_trend,
                divergence,
                status,
                detail
            ])
    except Exception as e:
        print(f"[ERROR] Failed to write signal_history.csv: {e}")

    # 2. ส่งขึ้น Supabase Cloud (ถ้ามีการเชื่อมต่อ)
    try:
        supabase_sync.log_signal(symbol, signal_type, plan, direction, price, ai_up, ai_down, h4_trend, status, detail)
    except Exception:
        pass
        
    # 3. แสดงข้อความสั้นใน Terminal ให้ทราบว่าได้บันทึกสัญญาณสำคัญแล้ว
    tag_color = Colors.GREEN if signal_type == 'ENTRY_SIGNAL' else (Colors.YELLOW if signal_type == 'H4_FILTERED' else (Colors.RED if signal_type == 'RISK_BLOCKED' else Colors.CYAN))
    print(f"{tag_color}[SIGNAL LOGGED] Saved to signal_history.csv: {symbol} {signal_type} ({plan} {direction}) -> {status} @ {price_str}{Colors.RESET}")
    return True

def send_order(symbol, order_type, price, sl, tp, plan_name="SR-SwingBounce"):
    info = mt5.symbol_info(symbol)
    filling_type = get_filling_type(info)
    volume = get_valid_lot(info)
    # ตรวจสอบ Margin ก่อนส่งคำสั่งซื้อขาย (Margin Pre-check Guard)
    try:
        acc = mt5.account_info()
        if acc is not None and acc.margin_free < 25.0:
            print(f"{Colors.RED}[FAILED - AUTO TRADE {symbol}] มาร์จิ้นคงเหลือไม่เพียงพอ (${acc.margin_free:.2f} < $25.00){Colors.RESET}")
            return False
    except Exception:
        pass

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": float(sl),
        "tp": float(tp),
        "deviation": 30,
        "magic": 888999,
        "comment": plan_name,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_type,
    }

    # ระบบ Retry อัตโนมัติเมื่อเกิด TRADE_RETCODE_REQUOTE (10004) สูงสุด 3 ครั้ง
    res = None
    for attempt in range(1, 4):
        res = mt5.order_send(request)
        if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
            break
        elif res is not None and res.retcode == getattr(mt5, 'TRADE_RETCODE_REQUOTE', 10004):
            print(f"{Colors.YELLOW}[REQUOTE RETRY #{attempt}] ราคาวิ่งเปลี่ยน ดึงราคา Tick ใหม่ทันที...{Colors.RESET}")
            time.sleep(0.2)
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                price = tick.ask if order_type == 0 else tick.bid
                request["price"] = price
        else:
            break

    if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"{Colors.GREEN}[SUCCESS - AUTO TRADE] Opened {'BUY' if order_type == 0 else 'SELL'} {symbol} Lot {volume:.2f} @ {price:.2f}{Colors.RESET}")
        print(f"   -> SL: {sl:.2f} | TP: {tp:.2f} ({plan_name})")
        
        # 1. เล่นเสียงดีใจเมื่อเข้าไม้ออเดอร์สำเร็จ (Joyful Victory Fanfare 🎺✨)
        sound_manager.play_order_entry()
        
        # บันทึกประวัติการเทรดลงไฟล์ CSV
        file_exists = os.path.isfile(TRADE_HISTORY_CSV)
        with open(TRADE_HISTORY_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Time', 'Symbol', 'Action', 'Plan', 'Price', 'Lot', 'SL', 'TP', 'Profit', 'Risk_Event'])
            writer.writerow([
                time.strftime('%Y-%m-%d %H:%M:%S'),
                symbol,
                'BUY' if order_type == 0 else 'SELL',
                plan_name,
                f"{float(price):.2f}",
                f"{float(volume):.2f}",
                f"{float(sl):.2f}",
                f"{float(tp):.2f}",
                "0.00",
                ''
            ])
        
        # ส่งประวัติขึ้น Supabase Cloud Dashboard และบันทึกสถิติแยกตาม User และ Plan
        ticket = res.order if hasattr(res, 'order') else 0
        cur_user = license_mgr.get_current_user()
        side = 'BUY' if order_type == 0 else 'SELL'
        supabase_sync.log_trade(ticket, symbol, f'OPEN_{side}', plan_name, float(price), float(volume), float(sl), float(tp),
                                profit=0, comment=f'เปิด {side} · {plan_name}', user_id=cur_user.get("user_id"), email=cur_user.get("email"))
        stats_manager.stats_mgr.record_entry(
            user_id=cur_user.get("user_id"),
            email=cur_user.get("email"),
            ticket=ticket,
            symbol=symbol,
            raw_plan=plan_name,
            action='BUY' if order_type == 0 else 'SELL',
            volume=volume,
            price=price,
            sl=sl,
            tp=tp
        )
        return True
    else:
        err_msg = res.comment if res is not None else "No response from MT5"
        err_code = res.retcode if res is not None else -1
        print(f"{Colors.RED}[FAILED - AUTO TRADE {symbol}] {err_msg} (Code: {err_code}){Colors.RESET}")

def close_position(position, comment="AI Reversal Close"):
    global consecutive_loss, last_loss_plan
    tick = mt5.symbol_info_tick(position.symbol)
    if tick is None:
        return False
    info = mt5.symbol_info(position.symbol)
    filling_type = get_filling_type(info)
    digits = 2  # บังคับทศนิยม 2 ตำแหน่งตามมาตรฐานระบบ
        
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
        "position": position.ticket,
        "price": tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask,
        "deviation": 30,
        "magic": 888999,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_type,
    }
    res = mt5.order_send(request)
    if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
        sym = position.symbol
        _self_closed_tickets.add(position.ticket)
        print(f"{Colors.YELLOW}[ORDER CLOSED] {sym} Ticket #{position.ticket} Closed Successfully{Colors.RESET}")
        last_exit_time[sym] = time.time()

        # [Priority 4] Same-Plan Cooldown: block 60 นาที เฉพาะเมื่อไม้ขาดทุนเท่านั้น
        closed_dir = 'BUY' if position.type == mt5.ORDER_TYPE_BUY else 'SELL'
        if position.profit < 0:
            if sym not in last_loss_plan:
                last_loss_plan[sym] = {}
            last_loss_plan[sym][closed_dir] = (position.comment or 'unknown', time.time())
            print(f"{Colors.YELLOW}[LOSS BLOCK] {sym} {closed_dir} ขาดทุน — block ทิศนี้ 60 นาที{Colors.RESET}")
            supabase_sync.log_risk_event(sym, 'LOSS_BLOCK', closed_dir, f'ขาดทุน ${abs(position.profit):.2f} — block {SAME_PLAN_COOLDOWN_MINUTES}m', loss=round(position.profit, 2))
        else:
            # ปิดกำไร → ลบ lock ออก เพื่อให้เข้าใหม่ได้ทันที
            if sym in last_loss_plan and closed_dir in last_loss_plan[sym]:
                del last_loss_plan[sym][closed_dir]
                print(f"{Colors.GREEN}[LOSS BLOCK CLEARED] {sym} {closed_dir} ปิดกำไร — ลบ block ออก เข้าใหม่ได้ทันที{Colors.RESET}")

        # [Priority 1] Circuit Breaker: นับขาดทุนติดต่อกัน
        if position.profit < 0:
            consecutive_loss[sym] = consecutive_loss.get(sym, 0) + 1
            loss_count = consecutive_loss[sym]
            if loss_count >= MAX_CONSECUTIVE_LOSS:
                ban_until = time.time() + (CIRCUIT_BREAKER_MINUTES * 60)
                last_exit_time[sym] = ban_until
                print(f"{Colors.RED}{Colors.BOLD}[CIRCUIT BREAKER] {sym} ขาดทุน {loss_count} ไม้ติดต่อกัน! หยุดเทรด {CIRCUIT_BREAKER_MINUTES} นาที จนถึง {time.strftime('%H:%M:%S', time.localtime(ban_until))}{Colors.RESET}")
                sound_manager.play_sl_hit()
                supabase_sync.log_risk_event(sym, 'CIRCUIT_BREAKER', 'N/A', f'ขาดทุน {loss_count} ไม้ติดต่อกัน — หยุด {CIRCUIT_BREAKER_MINUTES}m', loss=round(position.profit, 2))
        else:
            consecutive_loss[sym] = 0  # reset เมื่อได้กำไร
        
        # เล่นเสียงตามผลการปิดไม้: ปิดกำไร (กระดิ่ง) / ปิดขาดทุน (อ๊อด)
        if position.profit > 0:
            sound_manager.play_tp_hit()  # 2. เมื่อชน TP เป็นเสียงกระดิ่ง
        else:
            sound_manager.play_sl_hit()  # 3. เมื่อชน SL เป็นเสียงอ๊อด
        
        # บันทึกประวัติการปิดไม้ (เพิ่ม Profit + Risk_Event)
        final_profit = round(float(position.profit), 2)
        risk_event = ''
        if position.profit < 0:
            risk_event = 'LOSS_BLOCK'
        with open(TRADE_HISTORY_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                time.strftime('%Y-%m-%d %H:%M:%S'),
                sym,
                'CLOSE',
                'AI Reversal',
                f"{float(request['price']):.2f}",
                f"{float(position.volume):.2f}",
                "0.00",
                "0.00",
                f"{float(final_profit):.2f}",
                risk_event
            ])
        
        # ส่งประวัติปิดไม้ขึ้น Supabase Cloud Dashboard (พร้อม profit จริง) และอัปเดตสถิติ
        cur_user = license_mgr.get_current_user()
        supabase_sync.log_trade(position.ticket, sym, 'CLOSE', position.comment or 'Manual', float(request['price']), float(position.volume),
                                0, 0, profit=final_profit, comment=f'{comment} | {"+" if final_profit >= 0 else ""}${final_profit:.2f}',
                                user_id=cur_user.get("user_id"), email=cur_user.get("email"))
        stats_manager.stats_mgr.record_close(
            ticket=position.ticket,
            profit=final_profit,
            close_price=request['price'],
            reason="AI Reversal Close",
            user_id=cur_user.get("user_id"),
            fallback_plan=getattr(position, 'comment', 'Plan 3: SMC-LiquidityHunt')
        )
        return True
    else:
        err_msg = res.comment if res is not None else "No response"
        print(f"{Colors.RED}[FAILED - CLOSE] {err_msg}{Colors.RESET}")
        return False

def modify_position(position, new_sl, new_tp, reason="Break-Even Lock"):
    """ฟังก์ชันขยับ TP และเลื่อน SL เพื่อล็อคกำไร (Dynamic TP Extension & Profit Lock) พร้อมบันทึกประวัติแบบละเอียด"""
    old_sl = position.sl
    old_tp = position.tp
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": position.symbol,
        "position": position.ticket,
        "sl": float(new_sl),
        "tp": float(new_tp),
    }
    res = mt5.order_send(request)
    if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
        time_str = time.strftime('%Y-%m-%d %H:%M:%S')
        action_name = "LOCK_SL" if float(new_sl) != float(old_sl) else "EXTEND_TP"
        tick = mt5.symbol_info_tick(position.symbol)
        curr_price = tick.bid if tick else position.price_open
        info = mt5.symbol_info(position.symbol)
        digits = 2  # บังคับทศนิยม 2 ตำแหน่งตามมาตรฐานระบบ

        print(f"{Colors.CYAN}[SL/TP UPDATED] Ticket #{position.ticket} ({reason}) -> SL: {old_sl:.2f} -> {new_sl:.2f} | TP: {old_tp:.2f} -> {new_tp:.2f} (Profit: +${position.profit:.2f}){Colors.RESET}")
        
        # 5. เมื่อมีการขยับ SL ให้เล่นเสียงนกร้อง (Bird Chirp / จิ๊บๆ)
        if float(new_sl) != float(old_sl):
            sound_manager.play_sl_moved()
        
        # 1. บันทึกลง trade_history.csv (เพิ่ม Profit + Risk_Event)
        with open(TRADE_HISTORY_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                time_str,
                position.symbol,
                action_name,
                reason,
                f"{float(curr_price):.2f}",
                f"{float(position.volume):.2f}",
                f"{float(new_sl):.2f}",
                f"{float(new_tp):.2f}",
                f"{float(position.profit):.2f}",
                ''
            ])

        # 2. บันทึกลง trade_modifications.csv (ไฟล์ประวัติการปรับ SL/TP ละเอียดทุกครั้ง)
        mod_file = TRADE_MODS_CSV
        mod_exists = os.path.isfile(mod_file)
        with open(mod_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not mod_exists:
                writer.writerow(['Time', 'Ticket', 'Symbol', 'Type', 'Open_Price', 'Current_Price', 'Current_Profit_USD', 'Old_SL', 'New_SL', 'Old_TP', 'New_TP', 'Reason'])
            writer.writerow([
                time_str,
                position.ticket,
                position.symbol,
                'BUY' if position.type == 0 else 'SELL',
                f"{float(position.price_open):.2f}",
                f"{float(curr_price):.2f}",
                f"{float(position.profit):.2f}",
                f"{float(old_sl):.2f}",
                f"{float(new_sl):.2f}",
                f"{float(old_tp):.2f}",
                f"{float(new_tp):.2f}",
                reason
            ])

        # 3. ส่งข้อมูลการปรับ SL/TP ขึ้น Supabase Cloud Dashboard
        supabase_sync.log_trade(
            ticket=position.ticket,
            symbol=position.symbol,
            action=action_name,
            plan=f"{reason} (SL: {old_sl:.2f} -> {new_sl:.2f})",
            price=curr_price,
            lot=position.volume,
            sl=new_sl,
            tp=new_tp,
            profit=round(position.profit, 2),
            comment=f"{reason}: SL จาก {old_sl:.2f} เป็น {new_sl:.2f}"
        )
        
        # 4. บันทึกลง signal_history.csv
        log_signal_event(position.symbol, 'POSITION_MGMT', reason, 'BUY' if position.type == 0 else 'SELL', curr_price, 0.0, 0.0, 'N/A', 'None', 'LOCK_SL', f'New SL: {float(new_sl):.2f} | New TP: {float(new_tp):.2f} | Profit: ${float(position.profit):.2f}')
        return True
    else:
        err_msg = res.comment if res is not None else "No response"
        err_code = res.retcode if res is not None else -1
        print(f"[WARN] [ปรับ TP/SL ไม่สำเร็จ]: {err_msg} (Code: {err_code})")
        return False

def prune_old_csv_records(days=365):
    """
    ควบคุมขนาดไฟล์ประวัติ (Data Retention Policy):
    ตรวจสอบและลบรายการที่มีอายุเกิน 1 ปี (365 วัน)
    ครอบคลุม trade_history.csv, trade_modifications.csv, signal_history.csv
    """
    cutoff_time = datetime.now() - timedelta(days=days)
    target_files = [TRADE_HISTORY_CSV, TRADE_MODS_CSV, SIGNAL_HISTORY_CSV]

    for filepath in target_files:
        filename = os.path.basename(filepath)
        if not os.path.isfile(filepath):
            continue
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = list(csv.reader(f))
            if not reader or len(reader) <= 1:
                continue

            header = reader[0]
            kept_rows = [header]
            pruned_count = 0

            for row in reader[1:]:
                if not row or not row[0].strip():
                    continue
                try:
                    row_time = datetime.strptime(row[0].strip(), '%Y-%m-%d %H:%M:%S')
                    if row_time >= cutoff_time:
                        kept_rows.append(row)
                    else:
                        pruned_count += 1
                except Exception:
                    # ถ้าแปลงวันที่ไม่ได้ ให้เก็บไว้เพื่อความปลอดภัย
                    kept_rows.append(row)

            if pruned_count > 0:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(kept_rows)
                print(f"{Colors.YELLOW}[DATA RETENTION] {filename}: ลบประวัติเก่าเกิน 1 ปี ({days} วัน) ออกจำนวน {pruned_count} รายการ (รักษาขนาดไฟล์){Colors.RESET}")
        except Exception as e:
            print(f"[WARN] ข้อผิดพลาดในการคลีนไฟล์ {filename}: {e}")

def main():
    if not mt5.initialize():
        print(f"{Colors.RED}[ERROR] MT5 connection failed. Please ensure MT5 terminal is open.{Colors.RESET}")
        return

    # ตรวจสอบและลบประวัติที่เก่าเกิน 1 ปี (Data Retention Policy: 365 Days)
    prune_old_csv_records(days=365)
        
    # เริ่มต้นเธรดสตรีมข้อมูลขึ้น Supabase แบบ Real-time ทุก 5 วินาที (เริ่มครั้งเดียวต่อโปรเซส)
    global _telemetry_thread
    if _telemetry_thread is None or not _telemetry_thread.is_alive():
        plan_config.start()  # แผนเทรดที่แอดมินเปิด/ปิด (อัปเดตทุก 5 นาที)
        _telemetry_thread = threading.Thread(target=telemetry_background_worker, daemon=True)
        _telemetry_thread.start()
    print(f"{Colors.CYAN}[STREAM] Real-time telemetry streaming to GoldBot24 Cloud active (5s interval){Colors.RESET}")

    # ระบบจดจำข้อมูลบัญชีเทรด (User, Password, Server) — เก็บในเครื่องนี้เท่านั้น
    # (ไม่ส่งรหัสผ่าน MT5 ขึ้น Cloud: ตาราง bot_config ถูกใช้ร่วมกันหลายผู้ใช้ อ่านได้จาก anon key)
    from app_paths import data_path
    creds_path = data_path("credentials.json")  # %APPDATA%\GoldBot24 — ไม่หายเมื่ออัปเดตโปรแกรม
    local_creds = {}
    if os.path.exists(creds_path):
        try:
            with open(creds_path, "r", encoding="utf-8") as f:
                local_creds = json.load(f)
        except Exception:
            pass

    c_login = local_creds.get('mt5_login')
    c_pass = local_creds.get('mt5_password')
    c_server = local_creds.get('mt5_server') or 'FBS-Real'

    if c_login and c_pass and int(c_login) > 0:
        print(f"[ACCOUNT] Checking MT5 login for #{c_login} ({c_server})...")
        if mt5.login(login=int(c_login), password=c_pass, server=c_server):
            print(f"{Colors.GREEN}[SUCCESS] Logged in to MT5 Account #{c_login}!{Colors.RESET}")
            # เซฟลง credentials.json ไว้ใช้ถาวร
            try:
                with open(creds_path, "w", encoding="utf-8") as f:
                    json.dump({"mt5_login": int(c_login), "mt5_password": c_pass, "mt5_server": c_server}, f, indent=2)
            except Exception:
                pass
        else:
            print(f"{Colors.YELLOW}[WARNING] Login failed. Using currently active MT5 terminal account.{Colors.RESET}")
    else:
        # ถ้ายังไม่มีรหัสผ่าน ให้จำพอร์ตที่เปิดค้างอยู่ใน MT5 Terminal ไว้ในเครื่อง
        acc = mt5.account_info()
        if acc:
            print(f"[ACCOUNT] Current active MT5 Account #{acc.login} ({acc.server}) saved.{Colors.RESET}")
            try:
                with open(creds_path, "w", encoding="utf-8") as f:
                    json.dump({"mt5_login": acc.login, "mt5_password": local_creds.get("mt5_password", ""), "mt5_server": acc.server}, f, indent=2)
            except Exception:
                pass

    # ตั้งชื่อหน้าต่าง Windows Console Title ชัดเจนพร้อมเลขเวอร์ชัน
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(f"{BOT_NAME} v{BOT_VERSION} | XAUUSD Gold Specialist (SMC + Bounce + BB-H1 + MA-Cross M15/H1)")
    except Exception:
        pass

    print(f"\n{Colors.BOLD}{Colors.CYAN}============================================================{Colors.RESET}")
    print(f"{Colors.BOLD}🏆 [AI BOT] {BOT_NAME} v{BOT_VERSION} Started{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}[ASSET FOCUS]: XAUUSD (Gold Specialist 100%){Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}[ACTIVE PLANS]: Plan 1 (MA-Cross M15), Plan 2 (MA-Cross H1), Plan 3 (SMC), Plan 4 (Bounce), Plan 5 (BB-H1 Reversion){Colors.RESET}")
    print(f"{Colors.YELLOW}{Colors.BOLD}[RISK/RRR]: RRR 1:1.50 | SL 0.75 ATR | Early Profit Lock +0.35 ATR{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}============================================================{Colors.RESET}\n")

    models = {}
    model_features = {}
    last_h1_bar = {} # เอาไว้เช็คว่าขึ้นแท่งชั่วโมงใหม่หรือยัง
    last_h4_bar = {} # เอาไว้เช็คว่าขึ้นแท่ง 4 ชั่วโมงใหม่หรือยัง
    last_train_time = time.time() # จดจำเวลาที่เทรน AI ล่าสุด
    last_tick_time = {} # เอาไว้เช็คว่าตลาดเปิดไหม (ถ้า tick.time ไม่เปลี่ยนแสดงว่าตลาดปิด)
    last_pos_count = {} # เอาไว้เช็คว่ามีออเดอร์ปิดไปเอง (ชน SL/TP) หรือไม่ เพื่อเริ่มนับ Cooldown
    global consecutive_loss, last_lock_time, last_loss_plan
    consecutive_loss = {sym: 0 for sym in SYMBOLS}
    last_lock_time = {}
    last_loss_plan = {}
    
    for sym in SYMBOLS:
        mt5.symbol_select(sym, True)
        print(f"[AI TRAINING] Learning {sym} price action with S&R H1...")
        model, features = get_data_and_train(sym)
        if model is None:
            print(f"{Colors.RED}[ERROR] Failed to fetch data for {sym}. Check Market Watch.{Colors.RESET}")
        else:
            models[sym] = model
            model_features[sym] = features
            print(f"{Colors.GREEN}[OK] {sym} Model Trained Successfully!{Colors.RESET}")
            
    if len(models) == 0:
        print(f"{Colors.RED}[ERROR] No AI models ready. Shutting down.{Colors.RESET}")
        mt5.shutdown()
        return
        
    print(f"\n{Colors.GREEN}{Colors.BOLD}[AI READY] AI Multi-Asset Bot Ready! Auto-Trading Active for {', '.join(TRADE_SYMBOLS)}...{Colors.RESET}\n")
    
    while BOT_RUNNING_FLAG:
        if BOT_PAUSED_FLAG:
            time.sleep(1)
            continue
        try:
            # ปิดเสียงตอนสแกนและแจ้งเตือน AI Signal Alert ตามความต้องการ (เงียบสบายหู)
            # sound_manager.play_data_update()
            
            interesting_symbols = [] # เอาไว้เก็บคู่เงินที่น่าสนใจในรอบนี้
            
            # ระบบ Continuous Learning: รีเทรน AI ใหม่ทุกๆ 24 ชั่วโมง
            if time.time() - last_train_time > 86400:
                print(f"\n{Colors.YELLOW}[*] [Continuous Learning] ครบ 24 ชั่วโมง! กำลังอัปเดตสมอง AI ให้เข้ากับพฤติกรรมกราฟล่าสุด...{Colors.RESET}")
                for sym in SYMBOLS:
                    model, features = get_data_and_train(sym)
                    if model is not None:
                        models[sym] = model
                        model_features[sym] = features
                last_train_time = time.time()
                print(f"{Colors.GREEN}[OK] อัปเดตสมอง AI เสร็จสิ้น!{Colors.RESET}\n")
                # ทำความสะอาดและควบคุมขนาดไฟล์ประวัติทุกๆ 24 ชั่วโมง
                prune_old_csv_records(days=365)

            for sym in models.keys():
                tick = mt5.symbol_info_tick(sym)
                if tick is None:
                    continue
                    
                # บันทึกเวลา tick ล่าสุด
                last_tick_time[sym] = tick.time
                
                model = models[sym]
                features = model_features[sym]
                
                df_m15 = get_data(sym, TIMEFRAME, 300)   # 300 แท่ง: พอสำหรับ Features AI (เช่น ATR เฉลี่ย 96 แท่ง)
                df_h1 = get_data(sym, TIMEFRAME_H1, 600)   # 600 แท่ง: แนวรับ/ต้าน 500 แท่ง + MA200
                df_h4 = get_data(sym, TIMEFRAME_H4, 600)
                if df_m15 is None or df_h1 is None or df_h4 is None:
                    continue
                
                df_h1['ma_fast_h1'] = df_h1['close'].rolling(10).mean()
                df_h1['ma_slow_h1'] = df_h1['close'].rolling(30).mean()
                df_h1['trend_h1'] = df_h1['ma_fast_h1'] / df_h1['ma_slow_h1']
                df_h1['resistance'] = df_h1['high'].shift(1).rolling(20).max()
                df_h1['support'] = df_h1['low'].shift(1).rolling(20).min()
                
                # Bollinger Bands บน H1 (SMA 20, 2 STD) - Shift 1 ล็อคระดับราคาไม่ Repaint ระหว่างชั่วโมง
                df_h1['bb_mid_h1'] = df_h1['close'].shift(1).rolling(20).mean()
                df_h1['bb_std_h1'] = df_h1['close'].shift(1).rolling(20).std()
                df_h1['bb_upper_h1'] = df_h1['bb_mid_h1'] + (df_h1['bb_std_h1'] * 2.0)
                df_h1['bb_lower_h1'] = df_h1['bb_mid_h1'] - (df_h1['bb_std_h1'] * 2.0)
                
                # MACD บน H1 (12, 26, 9) เพื่อดักจับการหมดแรง (Exhaustion) ของโมเมนตัม
                ema12_h1 = df_h1['close'].ewm(span=12, adjust=False).mean()
                ema26_h1 = df_h1['close'].ewm(span=26, adjust=False).mean()
                df_h1['macd_h1'] = ema12_h1 - ema26_h1
                df_h1['macd_sig_h1'] = df_h1['macd_h1'].ewm(span=9, adjust=False).mean()
                df_h1['macd_hist_h1'] = df_h1['macd_h1'] - df_h1['macd_sig_h1']
                
                # Moving Average 5 & 10 บนแท่ง H1 สำหรับ Plan 2 (MA-Cross-H1-Trend)
                df_h1['ma5_h1'] = df_h1['close'].rolling(5).mean()
                df_h1['ma10_h1'] = df_h1['close'].rolling(10).mean()
                ma5_h1_val = float(df_h1['ma5_h1'].iloc[-1])
                ma10_h1_val = float(df_h1['ma10_h1'].iloc[-1])
                # Fix repainting: check cross on closed candles (iloc[-2] and iloc[-3])
                closed_ma5_h1 = float(df_h1['ma5_h1'].iloc[-2]) if len(df_h1) >= 2 else ma5_h1_val
                closed_ma10_h1 = float(df_h1['ma10_h1'].iloc[-2]) if len(df_h1) >= 2 else ma10_h1_val
                prev_closed_ma5_h1 = float(df_h1['ma5_h1'].iloc[-3]) if len(df_h1) >= 3 else closed_ma5_h1
                prev_closed_ma10_h1 = float(df_h1['ma10_h1'].iloc[-3]) if len(df_h1) >= 3 else closed_ma10_h1

                # Plan 2: MA5 ตัด MA10 บน H1 — แท่งที่ปิดแล้ว
                ma_cross_h1_up = bool((prev_closed_ma5_h1 <= prev_closed_ma10_h1) and (closed_ma5_h1 > closed_ma10_h1))
                ma_cross_h1_down = bool((prev_closed_ma5_h1 >= prev_closed_ma10_h1) and (closed_ma5_h1 < closed_ma10_h1))
                # เวลาแท่ง H1 ที่เกิด Cross (ใช้กันเข้าไม้ซ้ำบนสัญญาณ Cross เดิมตลอดทั้งชั่วโมง)
                ma_cross_h1_bar_time = df_h1['time'].iloc[-2] if len(df_h1) >= 2 else df_h1['time'].iloc[-1]

                # ATR(14) บน H1 สำหรับ Safety SL ของ Plan 2 (0.75 ATR H1) — ใช้แท่งที่ปิดแล้ว
                tr_h1 = pd.concat([
                    df_h1['high'] - df_h1['low'],
                    (df_h1['high'] - df_h1['close'].shift()).abs(),
                    (df_h1['low'] - df_h1['close'].shift()).abs()
                ], axis=1).max(axis=1)
                atr_h1_series = tr_h1.rolling(14).mean()
                atr_h1_val = float(atr_h1_series.iloc[-2]) if len(df_h1) >= 2 and pd.notna(atr_h1_series.iloc[-2]) else float('nan')
                ma_h1_status_str = f"{Colors.GREEN}MA5 > MA10 (+{(ma5_h1_val - ma10_h1_val):.2f}){Colors.RESET}" if ma5_h1_val >= ma10_h1_val else f"{Colors.RED}MA5 < MA10 ({(ma5_h1_val - ma10_h1_val):.2f}){Colors.RESET}"
                
                # เทรนด์ H1 จากแท่งที่ปิดแล้ว (เดิมใช้แท่งที่กำลังวิ่ง ทำให้เทรนด์กระพริบตามราคา)
                is_uptrend_h1, h1_diff_pct, h1_dir = closed_trend(df_h1['ma_fast_h1'], df_h1['ma_slow_h1'], atr=atr_h1_series)
                h1_cloud_status = f"UPTREND ({h1_diff_pct:+.2f}%)" if is_uptrend_h1 else f"DOWNTREND ({h1_diff_pct:+.2f}%)"
                
                # เช็คการเริ่มแท่ง H1 ใหม่ (แสดงเฉพาะคู่ที่เข้าเทรดจริง BTC/XAU)
                current_h1_time = df_h1['time'].iloc[-1]
                if sym not in last_h1_bar or last_h1_bar[sym] != current_h1_time:
                    trend_str = f"{Colors.GREEN}UPTREND [^]{Colors.RESET}" if is_uptrend_h1 else f"{Colors.RED}DOWNTREND [v]{Colors.RESET}"
                    if sym in TRADE_SYMBOLS:
                        print(f"\n[NEW H1 BAR] {sym} New 1-Hour Candle | Trend: {trend_str} | H1 MA5/10: {ma_h1_status_str}")
                    last_h1_bar[sym] = current_h1_time

                df_h1['time_h1'] = df_h1['time'].dt.floor('h')
                df_h1_features = df_h1[['time_h1', 'trend_h1', 'resistance', 'support', 'bb_mid_h1', 'bb_upper_h1', 'bb_lower_h1', 'macd_hist_h1', 'ma5_h1', 'ma10_h1']].dropna()
                
                # วิเคราะห์เทรนด์ระยะยาว H4 (Bullish 🐂 vs Bearish 🐻)
                df_h4['ma_fast_h4'] = df_h4['close'].rolling(10).mean()
                df_h4['ma_slow_h4'] = df_h4['close'].rolling(30).mean()
                df_h4['trend_h4'] = df_h4['ma_fast_h4'] / df_h4['ma_slow_h4']
                
                # แนวรับ/ต้าน H4 = Low ต่ำสุด / High สูงสุด 20 แท่งก่อนหน้า (วิธีเดียวกับ H1) — ใช้แสดงผลบน Dashboard
                h4_res_series = df_h4['high'].shift(1).rolling(20).max()
                h4_sup_series = df_h4['low'].shift(1).rolling(20).min()
                h4_resistance = float(h4_res_series.iloc[-1]) if pd.notna(h4_res_series.iloc[-1]) else 0.0
                h4_support = float(h4_sup_series.iloc[-1]) if pd.notna(h4_sup_series.iloc[-1]) else 0.0
                # สภาวะตลาด H4 จากแท่งที่ปิดแล้ว (ไม่ Repaint) + ทิศความชัน MA10
                atr_h4_series = _atr_series(df_h4)
                is_uptrend_h4, h4_diff_pct, h4_dir = closed_trend(df_h4['ma_fast_h4'], df_h4['ma_slow_h4'], atr=atr_h4_series)
                is_sideway_h4 = bool(abs(h4_diff_pct) < 0.20)

                if is_sideway_h4:
                    h4_trend_text = f"SIDEWAY [~] ({h4_diff_pct:+.2f}%)"
                    h4_trend_color = Colors.CYAN
                    h4_badge = f"{Colors.CYAN}[H4: SIDEWAY {h4_diff_pct:+.1f}%]{Colors.RESET}"
                    h4_cloud_status = f"SIDEWAY ({h4_diff_pct:+.2f}%)"
                    h4_buy_ok = True
                    h4_sell_ok = True
                elif is_uptrend_h4:
                    h4_trend_text = f"BULLISH [^] (+{h4_diff_pct:.2f}%)"
                    h4_trend_color = Colors.GREEN
                    h4_badge = f"{Colors.GREEN}[H4: BULL +{h4_diff_pct:.1f}%]{Colors.RESET}"
                    h4_cloud_status = f"BULLISH (+{h4_diff_pct:.2f}%)"
                    h4_buy_ok = True
                    h4_sell_ok = False
                else:
                    h4_trend_text = f"BEARISH [v] ({h4_diff_pct:.2f}%)"
                    h4_trend_color = Colors.RED
                    h4_badge = f"{Colors.RED}[H4: BEAR {h4_diff_pct:.1f}%]{Colors.RESET}"
                    h4_cloud_status = f"BEARISH ({h4_diff_pct:.2f}%)"
                    h4_buy_ok = False
                    h4_sell_ok = True

                # เช็คการเริ่มแท่ง H4 ใหม่
                current_h4_time = df_h4['time'].iloc[-1]
                if sym not in last_h4_bar or last_h4_bar[sym] != current_h4_time:
                    if is_sideway_h4:
                        h4_ann = f"{Colors.CYAN}SIDEWAY [~] ({h4_diff_pct:+.2f}%){Colors.RESET}"
                    else:
                        h4_ann = f"{Colors.GREEN}BULLISH [^] (+{h4_diff_pct:.2f}%){Colors.RESET}" if is_uptrend_h4 else f"{Colors.RED}BEARISH [v] ({h4_diff_pct:.2f}%){Colors.RESET}"
                    if sym in TRADE_SYMBOLS:
                        print(f"\n{Colors.BOLD}[NEW H4 BAR] {sym} New 4-Hour Candle | H4 Regime: {h4_ann}{Colors.RESET}")
                    last_h4_bar[sym] = current_h4_time

                df_h4['time_h4'] = df_h4['time'].dt.floor('4h')
                df_h4_features = df_h4[['time_h4', 'trend_h4']].dropna()
                
                df = df_m15.copy()
                df['time_h1'] = df['time'].dt.floor('h')
                df = pd.merge(df, df_h1_features, on='time_h1', how='left')
                df['trend_h1'] = df['trend_h1'].ffill()
                df['resistance'] = df['resistance'].ffill()
                df['support'] = df['support'].ffill()
                df['bb_mid_h1'] = df['bb_mid_h1'].ffill()
                df['bb_upper_h1'] = df['bb_upper_h1'].ffill()
                df['bb_lower_h1'] = df['bb_lower_h1'].ffill()
                df['macd_hist_h1'] = df['macd_hist_h1'].ffill()
                df['ma5_h1'] = df['ma5_h1'].ffill()
                df['ma10_h1'] = df['ma10_h1'].ffill()
                
                df['time_h4'] = df['time'].dt.floor('4h')
                df = pd.merge(df, df_h4_features, on='time_h4', how='left')
                df['trend_h4'] = df['trend_h4'].ffill()
                
                df['return'] = df['close'].pct_change()
                df['ma_fast'] = df['close'].rolling(10).mean()
                df['ma_slow'] = df['close'].rolling(30).mean()
                df['trend'] = df['ma_fast'] / df['ma_slow']
                
                # Moving Average 5 & 10 (M15) สำหรับ Plan 1 (MA-Cross-Trend)
                df['ma5'] = df['close'].rolling(5).mean()
                df['ma10'] = df['close'].rolling(10).mean()
                df['ma13'] = df['close'].rolling(13).mean()   # Plan 1: MA5 ตัด MA13
                
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                df['rsi'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                
                df['high_low'] = df['high'] - df['low']
                df['high_close'] = np.abs(df['high'] - df['close'].shift())
                df['low_close'] = np.abs(df['low'] - df['close'].shift())
                df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
                df['atr'] = df['tr'].rolling(14).mean()
                
                # Bollinger Bands (SMA 20, 2 STD)
                df['bb_mid'] = df['close'].rolling(20).mean()
                df['std'] = df['close'].rolling(20).std()
                df['bb_upper'] = df['bb_mid'] + (df['std'] * 2)
                df['bb_lower'] = df['bb_mid'] - (df['std'] * 2)
                df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / (df['bb_mid'] + 1e-9)
                
                # Smart Money Concepts / Liquidity Sweep Features (Wick Analysis)
                lower_wick = np.minimum(df['open'], df['close']) - df['low']
                upper_wick = df['high'] - np.maximum(df['open'], df['close'])
                df['lower_wick_ratio'] = lower_wick / (df['atr'] + 1e-9)
                df['upper_wick_ratio'] = upper_wick / (df['atr'] + 1e-9)
                
                # Session / Hour
                df['hour'] = df['time'].dt.hour
                df['is_liquid_session'] = ((df['hour'] >= 8) & (df['hour'] <= 22)).astype(int)
                
                df['dist_to_res'] = df['resistance'] - df['close']
                df['dist_to_sup'] = df['close'] - df['support']
                
                # ตรวจจับ Divergence สดสำหรับแท่ง M15
                df = add_divergence_features(df, lookback=14)

                df.dropna(inplace=True)
                if len(df) == 0:
                    continue
                    
                last_bar = df.iloc[-1]

                # AI: ทายจากแท่ง M15 ที่ปิดแล้วล่าสุด ด้วย Features ชุดเดียวกับตอนเทรน (ไม่มีข้อมูลอนาคต)
                ai_df = build_ai_features(df_m15, df_h1, df_h4)
                ai_row = ai_df[features].iloc[[-2]] if len(ai_df) >= 2 else None
                if ai_row is None or ai_row.isna().any(axis=1).iloc[0]:
                    prob = np.array([0.5, 0.5])  # ข้อมูลไม่พอ → เป็นกลาง (ไม่ช่วยยืนยันฝั่งไหน)
                else:
                    prob = model.predict_proba(ai_row)[0]
                
                # ข้อมูลราคาและตัวแปรทางเทคนิค
                # แนวรับ/แนวต้านจากโซนกลับตัวย้อนหลัง 500 แท่ง (แทน Low/High 20 แท่งเดิม) — Plan 3 (SMC) / Plan 4 (SR-Bounce) ใช้ H1
                sr_price = float(last_bar['close'])
                sr_h1 = find_sr_levels(df_h1, sr_price)
                sr_h4 = find_sr_levels(df_h4, sr_price)
                support = sr_h1["support"] if pd.notna(sr_h1["support"]) else last_bar['support']
                resistance = sr_h1["resistance"] if pd.notna(sr_h1["resistance"]) else last_bar['resistance']
                h4_support = sr_h4["support"] if pd.notna(sr_h4["support"]) else h4_support
                h4_resistance = sr_h4["resistance"] if pd.notna(sr_h4["resistance"]) else h4_resistance
                # สภาวะตลาดสำหรับแสดงผล (MA50/100/150 เรียงตัว)
                h1_cond, h1_cond_pct = ma_condition(df_h1['close'])
                h4_cond, h4_cond_pct = ma_condition(df_h4['close'])
                atr_val = last_bar['atr']
                close_price = last_bar['close']
                lower_wick_ratio = last_bar['lower_wick_ratio']
                upper_wick_ratio = last_bar['upper_wick_ratio']
                
                # ตัวแปรสถานะ Divergence
                bull_div_active = bool(last_bar.get('bull_div', 0) > 0.5)
                bear_div_active = bool(last_bar.get('bear_div', 0) > 0.5)
                hidden_bull_active = bool(last_bar.get('hidden_bull', 0) > 0.5)
                hidden_bear_active = bool(last_bar.get('hidden_bear', 0) > 0.5)

                div_tag = ""
                div_name = "None"
                if bull_div_active:
                    div_tag = f" {Colors.GREEN}[BULL DIV ^]{Colors.RESET}"
                    div_name = "BULL DIV ^"
                elif bear_div_active:
                    div_tag = f" {Colors.RED}[BEAR DIV v]{Colors.RESET}"
                    div_name = "BEAR DIV v"
                elif hidden_bull_active:
                    div_tag = f" {Colors.GREEN}[H-BULL ^]{Colors.RESET}"
                    div_name = "H-BULL ^"
                elif hidden_bear_active:
                    div_tag = f" {Colors.RED}[H-BEAR v]{Colors.RESET}"
                    div_name = "H-BEAR v"
                
                # 1. เงื่อนไข Liquidity Sweep (SMC: กวาดสภาพคล่องแล้วดึงกลับ ไส้ปฏิเสธชัดเจน >= 0.30 ATR + บังคับทิศทางเทรนด์ H1 100%)
                is_sweep_buy = (last_bar['low'] < support) and (close_price >= support) and (lower_wick_ratio >= 0.30) and is_uptrend_h1
                is_sweep_sell = (last_bar['high'] > resistance) and (close_price <= resistance) and (upper_wick_ratio >= 0.30) and (not is_uptrend_h1)
                
                # 2. เงื่อนไข Bounce (ชนแนวรับ/ต้าน แล้วมีแท่งปฏิเสธราคา)
                near_support = abs(close_price - support) <= (atr_val * 1.0) and (close_price >= support)
                near_resistance = abs(resistance - close_price) <= (atr_val * 1.0) and (close_price <= resistance)
                
                # 3. เงื่อนไข Bollinger Bands Mean-Reversion (Plan 5: โฟกัส H1 + Divergence + MACD Confluence)
                bb_lower_h1 = last_bar['bb_lower_h1']
                bb_upper_h1 = last_bar['bb_upper_h1']
                bb_mid_h1 = last_bar['bb_mid_h1']
                macd_hist_h1 = float(last_bar.get('macd_hist_h1', 0.0))
                prev_macd_hist_h1 = float(df.iloc[-2]['macd_hist_h1']) if len(df) >= 2 else macd_hist_h1

                macd_buy_exhaustion = bool(macd_hist_h1 >= prev_macd_hist_h1)
                macd_sell_exhaustion = bool(macd_hist_h1 <= prev_macd_hist_h1)

                has_div_bb_buy = bull_div_active or hidden_bull_active
                has_div_bb_sell = bear_div_active or hidden_bear_active

                # สำหรับ XAUUSD (Gold Specialist):
                # Plan 3 (SMC-LiquidityHunt) เปิด + กรองเทรนด์ใหญ่ H1
                # Plan 4 (SR-SwingBounce) เปิดพร้อม Divergence Confluence
                has_div_bounce_buy = bull_div_active or hidden_bull_active
                has_div_bounce_sell = bear_div_active or hidden_bear_active
                bounce_buy_confirm = near_support and has_div_bounce_buy and (lower_wick_ratio >= 0.20 or close_price > last_bar['open'])
                bounce_sell_confirm = near_resistance and has_div_bounce_sell and (upper_wick_ratio >= 0.20 or close_price < last_bar['open'])
                # Plan 5 (BB-H1-Reversion) โฟกัสกรอบ H1 + ไส้เทียน + Divergence + MACD Exhaustion (Win Rate สูงถึง 60%)
                bb_buy_confirm = (last_bar['low'] < bb_lower_h1) and (close_price >= bb_lower_h1) and (lower_wick_ratio >= 0.20) and has_div_bb_buy and macd_buy_exhaustion
                bb_sell_confirm = (last_bar['high'] > bb_upper_h1) and (close_price <= bb_upper_h1) and (upper_wick_ratio >= 0.20) and has_div_bb_sell and macd_sell_exhaustion

                # Plan 1 (MA-Cross-Trend) Moving Average 5 ตัด 10 บนแท่ง M15 กรองด้วยเทรนด์ใหญ่ H1
                ma5_val = float(last_bar['ma5'])
                ma10_val = float(last_bar['ma10'])
                # Fix repainting: check cross on closed candles (iloc[-2] and iloc[-3])
                closed_ma5 = float(df.iloc[-2]['ma5']) if len(df) >= 2 else ma5_val
                closed_ma10 = float(df.iloc[-2]['ma10']) if len(df) >= 2 else ma10_val
                prev_closed_ma5 = float(df.iloc[-3]['ma5']) if len(df) >= 3 else closed_ma5
                prev_closed_ma10 = float(df.iloc[-3]['ma10']) if len(df) >= 3 else closed_ma10

                ma_cross_up = bool((prev_closed_ma5 <= prev_closed_ma10) and (closed_ma5 > closed_ma10))
                ma_cross_down = bool((prev_closed_ma5 >= prev_closed_ma10) and (closed_ma5 < closed_ma10))
                # เวลาแท่ง M15 ที่เกิด Cross (ใช้กันเข้าไม้ซ้ำบนสัญญาณ Cross เดิม)
                ma_cross_bar_time = df.iloc[-2]['time'] if len(df) >= 2 else df.iloc[-1]['time']

                # ===== Plan 1 (กำหนดโดยผู้ใช้ 2026-10-05) =====
                #   1) เทรนด์ H1 ยืนยัน: MA100 < MA150 < MA200 = ขาลง (SELL) · MA100 > MA150 > MA200 = ขาขึ้น (BUY) — แท่งที่ปิดแล้ว
                #   2) MA5 ตัด MA13 บน M15 (แท่งที่ปิดแล้ว) · ออกเมื่อ MA5 ตัด MA13 กลับ
                h1_c = df_h1['close']
                if len(h1_c) >= 202:
                    h1_ma100 = h1_c.rolling(100).mean().iloc[-2]
                    h1_ma150 = h1_c.rolling(150).mean().iloc[-2]
                    h1_ma200_p4 = h1_c.rolling(200).mean().iloc[-2]
                    if h1_ma100 < h1_ma150 < h1_ma200_p4:
                        h1_stack_dir = -1
                    elif h1_ma100 > h1_ma150 > h1_ma200_p4:
                        h1_stack_dir = 1
                    else:
                        h1_stack_dir = 0
                else:
                    h1_stack_dir = 0
                closed_ma13 = float(df.iloc[-2]['ma13']) if len(df) >= 2 else float('nan')
                prev_closed_ma13 = float(df.iloc[-3]['ma13']) if len(df) >= 3 else closed_ma13
                p4_cross_up = bool((prev_closed_ma5 <= prev_closed_ma13) and (closed_ma5 > closed_ma13))
                p4_cross_down = bool((prev_closed_ma5 >= prev_closed_ma13) and (closed_ma5 < closed_ma13))
                ma_cross_buy_confirm = p4_cross_up and h1_stack_dir == 1
                ma_cross_sell_confirm = p4_cross_down and h1_stack_dir == -1

                # ตัวกรองสัญญาณหลอก Plan 1 (แท่ง M15 ที่ปิดแล้ว): โมเมนตัม RSI ต้องหนุนทิศ แต่ยังไม่ Overbought/Oversold
                # และราคาปิดต้องอยู่ฝั่งเดียวกับ MA50 M15 — Backtest 2.5 ปี: ไม้ 2027 → 739, PF 1.16 → 1.37,
                # Max DD 245 → 92 จุด, กำไร 850 → 690 จุด (กำไรทุกไตรมาส จากเดิมกระจุกช่วงท้าย)
                if ma_cross_buy_confirm or ma_cross_sell_confirm:
                    p1_dir = 1 if ma_cross_buy_confirm else -1
                    p1_rsi = float(df['rsi'].iloc[-2]) if len(df) >= 2 else float('nan')
                    p1_ma50 = float(df['close'].rolling(50).mean().iloc[-2]) if len(df) >= 51 else float('nan')
                    p1_close = float(df['close'].iloc[-2])
                    rsi_ok = (50 < p1_rsi < 70) if p1_dir == 1 else (30 < p1_rsi < 50)
                    ma50_ok = pd.notna(p1_ma50) and (p1_close - p1_ma50) * p1_dir > 0
                    if not (rsi_ok and ma50_ok):
                        ma_cross_buy_confirm = ma_cross_sell_confirm = False
                        bar_key = (sym, str(df['time'].iloc[-2]) if 'time' in df else p1_close)
                        if _p1_filter_logged.get(sym) != bar_key:
                            _p1_filter_logged[sym] = bar_key
                            why = []
                            if not rsi_ok:
                                why.append(f"RSI {p1_rsi:.1f} (ต้อง {'50–70' if p1_dir == 1 else '30–50'})")
                            if not ma50_ok:
                                why.append(f"ราคา {'ต่ำกว่า' if p1_dir == 1 else 'สูงกว่า'} MA50 M15 ({p1_ma50:.2f})")
                            print(f"{Colors.YELLOW}[FAKE SIGNAL FILTER] {sym} Plan 1 {'BUY' if p1_dir == 1 else 'SELL'} ข้าม — {' · '.join(why)}{Colors.RESET}")

                # เทรนด์ระยะยาว 200 แท่ง สำหรับ Plan 2 + Dashboard
                #   Plan 2: ราคาปิด H4 เทียบ MA200 ต้องตรงทิศ — กำไร 767 → 991 จุด, PF 1.20 → 1.37, Max DD 315 → 268
                h1_lt_dir, h1_ma200 = long_term_dir(df_h1['close'], fast=50)
                h4_lt_dir, h4_ma200 = long_term_dir(df_h4['close'])

                # (A) Plan 2: ช่วง H4 ไซด์เวย์ ต้องเทรดตามฝั่งที่ MA10/MA30 H4 เอียง
                #     ไซด์เวย์บูลลิช (MA10 > MA30) = BUY เท่านั้น · ไซด์เวย์แบร์ริช (MA10 < MA30) = SELL เท่านั้น
                #     Backtest 2.5 ปี (P5): กำไรสุทธิ 386 → 757 จุด, Max DD 374 → 297
                #     + MA10 H4 ต้องชันไปทางเดียวกัน (กันซื้อตอน MA10 H4 กำลังม้วนลง) — Backtest: PF 1.13 → 1.20
                # ===== Plan 2 (MA H1) — Backtest 2.5 ปี ดีที่สุด: กำไร 1113 จุด, PF 1.59, Max DD 219 =====
                #   H4 MA10/30 (Strict Pro-Trend, ไซด์เวย์ต้องเอียงตามฝั่ง) + ความชัน MA5 H4 (2 แท่ง) + ราคาปิด H4 เทียบ MA200
                h4_c = df_h4['close']
                if len(h4_c) >= 202:
                    m100, m150, m200 = (h4_c.rolling(k).mean().iloc[-2] for k in (100, 150, 200))
                    h4_stack_dir = -1 if m100 < m150 < m200 else (1 if m100 > m150 > m200 else 0)  # แสดงผลบนการ์ด
                else:
                    h4_stack_dir = 0
                ma5_h4 = df_h4['close'].rolling(5).mean()
                if len(ma5_h4) >= 5 and pd.notna(ma5_h4.iloc[-4]) and pd.notna(atr_h4_series.iloc[-2]) and atr_h4_series.iloc[-2] > 0:
                    h4_ma5_slope = (ma5_h4.iloc[-2] - ma5_h4.iloc[-4]) / atr_h4_series.iloc[-2]
                    h4_dir_p2 = 1 if (is_uptrend_h4 and h4_ma5_slope > 0) else (-1 if (not is_uptrend_h4 and h4_ma5_slope < 0) else 0)
                else:
                    h4_dir_p2 = 0
                plan5_buy_ok = bool(h4_buy_ok and h4_dir_p2 == 1 and h4_lt_dir == 1)
                plan5_sell_ok = bool(h4_sell_ok and h4_dir_p2 == -1 and h4_lt_dir == -1)

                ma_status_str = f"{Colors.GREEN}MA5 > MA10 (+{(ma5_val - ma10_val):.2f}){Colors.RESET}" if ma5_val >= ma10_val else f"{Colors.RED}MA5 < MA10 ({(ma5_val - ma10_val):.2f}){Colors.RESET}"
                
                # กำหนดสถานะและสีสำหรับ Terminal UI
                status_color = Colors.RESET
                status_text = "[WAIT OUTSIDE ZONE]"
                if is_sweep_buy:
                    status_text = "[SMC-HUNT BUY + BULL DIV]" if bull_div_active else "[SMC-HUNT BUY] Swept + H1 Up"
                    status_color = Colors.GREEN
                elif is_sweep_sell:
                    status_text = "[SMC-HUNT SELL + BEAR DIV]" if bear_div_active else "[SMC-HUNT SELL] Swept + H1 Down"
                    status_color = Colors.RED
                elif bounce_buy_confirm:
                    status_text = "[SR-BOUNCE BUY] + Bull Div" if bull_div_active else "[SR-BOUNCE BUY] Support"
                    status_color = Colors.GREEN
                elif bounce_sell_confirm:
                    status_text = "[SR-BOUNCE SELL] + Bear Div" if bear_div_active else "[SR-BOUNCE SELL] Resistance"
                    status_color = Colors.RED
                elif bb_buy_confirm:
                    status_text = "[BB-H1 REVERSION BUY] + Div + MACD" if has_div_bb_buy else "[BB-H1 REVERSION BUY] Lower Band"
                    status_color = Colors.GREEN
                elif bb_sell_confirm:
                    status_text = "[BB-H1 REVERSION SELL] + Div + MACD" if has_div_bb_sell else "[BB-H1 REVERSION SELL] Upper Band"
                    status_color = Colors.RED
                elif ma_cross_buy_confirm:
                    status_text = "[MA-CROSS BUY] MA5 > MA13 (M15) + H1 MA100>150>200"
                    status_color = Colors.GREEN
                elif ma_cross_sell_confirm:
                    status_text = "[MA-CROSS SELL] MA5 < MA13 (M15) + H1 MA100<150<200"
                    status_color = Colors.RED
                elif ma_cross_h1_up and plan5_buy_ok:
                    status_text = "[MA-CROSS-H1 BUY] MA5 > MA10 (H1) + H4 Bullish + MA200"
                    status_color = Colors.GREEN
                elif ma_cross_h1_down and plan5_sell_ok:
                    status_text = "[MA-CROSS-H1 SELL] MA5 < MA10 (H1) + H4 Bearish + MA200"
                    status_color = Colors.RED

                # แสดงผลแบบ Dashboard สวยงาม โดยปรับจุดทศนิยมอัตโนมัติ
                info = mt5.symbol_info(sym)
                digits = 2  # บังคับทศนิยม 2 ตำแหน่งตามมาตรฐานระบบ
                volume = get_valid_lot(info)
                spread_pts = info.spread if info is not None else 0
                symbol_rrr = TP_RRR_XAU
                sym_mode_tag = f"{Colors.GREEN}{Colors.BOLD}[GOLD AUTO-TRADE]{Colors.RESET}"
                
                positions = mt5.positions_get(symbol=sym)
                has_position = positions is not None and len(positions) > 0
                current_pos_count = len(positions) if positions is not None else 0
                prev_pos_count = last_pos_count.get(sym, 0)
                
                # ตรวจจับกรณีออเดอร์ปิดไปเอง (ชน SL หรือ TP จาก MT5 server) เพื่อเริ่มนับ Cooldown
                if current_pos_count < prev_pos_count:
                    last_exit_time[sym] = time.time()
                    cd_show = COOLDOWN_MINUTES_XAU
                    
                    # เช็คประวัติ Deal ล่าสุดจาก MT5 เพื่อดูว่าปิดด้วยกำไร (TP) หรือ ขาดทุน (SL)
                    closed_deal_profit = None
                    closed_deal_type = None
                    closed_deal_ticket = 0
                    closed_deal_price = 0.0
                    closed_deal_volume = 0.0
                    try:
                        # เวลา Server ของโบรกเกอร์ต่างจากเวลาเครื่อง — ใช้ช่วงกว้างแล้วเลือก Deal ล่าสุด
                        deals = mt5.history_deals_get(datetime.now() - timedelta(days=2), datetime.now() + timedelta(days=1))
                        if deals:
                            # entry == 1 คือ DEAL_ENTRY_OUT (Deal ปิดสัญญา)
                            out_deals = sorted([d for d in deals if d.symbol == sym and d.entry == 1], key=lambda d: d.time_msc)
                            if out_deals:
                                last_out = out_deals[-1]
                                closed_deal_profit = last_out.profit + getattr(last_out, 'commission', 0.0) + getattr(last_out, 'swap', 0.0)
                                # Deal ปิดเป็นฝั่งตรงข้ามกับไม้ (ปิด BUY = Deal SELL) → ทิศของไม้คือฝั่งตรงข้ามของ Deal
                                closed_deal_type = 'SELL' if last_out.type == 0 else 'BUY'
                                closed_deal_ticket = getattr(last_out, 'position_id', 0) or getattr(last_out, 'order', 0)
                                closed_deal_price = float(last_out.price)
                                closed_deal_volume = float(last_out.volume)
                    except Exception:
                        pass

                    # ไม้ที่บอทปิดเองผ่าน close_position() ถูกนับขาดทุน/บันทึกสถิติไปแล้ว — ไม่นับซ้ำ
                    handled_by_bot = bool(closed_deal_ticket) and closed_deal_ticket in _self_closed_tickets
                    if handled_by_bot:
                        _self_closed_tickets.discard(closed_deal_ticket)

                    if not handled_by_bot:
                        # [Priority 4] Same-Plan Cooldown: block 60 นาที เฉพาะเมื่อขาดทุน (SL Hit)
                        if closed_deal_type:
                            if closed_deal_profit is not None and closed_deal_profit < 0:
                                # ไม้ขาดทุน → block 60 นาที
                                if sym not in last_loss_plan:
                                    last_loss_plan[sym] = {}
                                last_loss_plan[sym][closed_deal_type] = ('SL Hit', time.time())
                                print(f"{Colors.YELLOW}[LOSS BLOCK] {sym} {closed_deal_type} ชน SL — block ทิศนี้ 60 นาที{Colors.RESET}")
                                supabase_sync.log_risk_event(sym, 'LOSS_BLOCK', closed_deal_type, f'ชน SL — ขาดทุน ${abs(closed_deal_profit):.2f} — block {SAME_PLAN_COOLDOWN_MINUTES}m', loss=round(closed_deal_profit, 2))
                                cur_user = license_mgr.get_current_user()
                                supabase_sync.log_trade(closed_deal_ticket, sym, 'SL_HIT', 'SL Hit', closed_deal_price, closed_deal_volume, 0, 0, profit=round(closed_deal_profit, 2), comment=f'SL Hit | Loss: ${closed_deal_profit:+.2f}', user_id=cur_user.get("user_id"), email=cur_user.get("email"))
                                stats_manager.stats_mgr.record_close(ticket=closed_deal_ticket, profit=closed_deal_profit, reason="SL Hit", user_id=cur_user.get("user_id"))
                            elif closed_deal_profit is not None and closed_deal_profit > 0:
                                # ไม้กำไร (TP Hit) → ลบ lock ออก
                                if sym in last_loss_plan and closed_deal_type in last_loss_plan[sym]:
                                    del last_loss_plan[sym][closed_deal_type]
                                    print(f"{Colors.GREEN}[LOSS BLOCK CLEARED] {sym} {closed_deal_type} ชน TP — ลบ block เข้าใหม่ได้ทันที{Colors.RESET}")
                                cur_user = license_mgr.get_current_user()
                                supabase_sync.log_trade(closed_deal_ticket, sym, 'TP_HIT', 'TP Hit', closed_deal_price, closed_deal_volume, 0, 0, profit=round(closed_deal_profit, 2), comment=f'TP Hit | Profit: ${closed_deal_profit:+.2f}', user_id=cur_user.get("user_id"), email=cur_user.get("email"))
                                stats_manager.stats_mgr.record_close(ticket=closed_deal_ticket, profit=closed_deal_profit, reason="TP Hit", user_id=cur_user.get("user_id"))

                        # [Priority 1] Circuit Breaker: นับขาดทุนจาก SL Hit
                        if closed_deal_profit is not None and closed_deal_profit < 0:
                            consecutive_loss[sym] = consecutive_loss.get(sym, 0) + 1
                            loss_count = consecutive_loss[sym]
                            if loss_count >= MAX_CONSECUTIVE_LOSS:
                                ban_until = time.time() + (CIRCUIT_BREAKER_MINUTES * 60)
                                last_exit_time[sym] = ban_until
                                print(f"{Colors.RED}{Colors.BOLD}[CIRCUIT BREAKER] {sym} ขาดทุน {loss_count} ไม้ติดกัน! หยุดเทรด {CIRCUIT_BREAKER_MINUTES} นาที จนถึง {time.strftime('%H:%M:%S', time.localtime(ban_until))}{Colors.RESET}")
                                supabase_sync.log_risk_event(sym, 'CIRCUIT_BREAKER', 'N/A', f'ขาดทุน {loss_count} ไม้ติดต่อกัน (SL Hit) - หยุด {CIRCUIT_BREAKER_MINUTES}m', loss=round(closed_deal_profit, 2))
                        elif closed_deal_profit is not None and closed_deal_profit > 0:
                            consecutive_loss[sym] = 0  # reset เมื่อได้กำไร
                        
                        if closed_deal_profit is not None and closed_deal_profit > 0:
                            print(f"\n{Colors.GREEN}{Colors.BOLD}[TP HIT] {sym} Order closed in PROFIT: +${closed_deal_profit:.2f}! (เสียงกระดิ่ง){Colors.RESET}")
                            sound_manager.play_tp_hit()  # 2. เมื่อชน TP เป็นเสียงกระดิ่ง
                        elif closed_deal_profit is not None and closed_deal_profit <= 0:
                            print(f"\n{Colors.RED}{Colors.BOLD}[SL HIT] {sym} Order closed with LOSS: -${abs(closed_deal_profit):.2f}! (เสียงอ๊อด){Colors.RESET}")
                            sound_manager.play_sl_hit()  # 3. เมื่อชน SL เป็นเสียงอ๊อด
                        else:
                            print(f"\n[COOLDOWN] {sym} Order closed (TP/SL Hit) -> Starting cooldown rest for {cd_show}m")
                            sound_manager.play_tp_hit()
                last_pos_count[sym] = current_pos_count
                
                is_in_zone = (status_text != "[WAIT OUTSIDE ZONE]")

                # แสดงผลแบบ Real-time Dashboard ทุกรอบการสแกน (เน้นทองคำ XAUUSD ชัดเจน 100%)
                if is_in_zone or has_position:
                    h1_trend_label = f"{Colors.GREEN}UPTREND [^]{Colors.RESET}" if is_uptrend_h1 else f"{Colors.RED}DOWNTREND [v]{Colors.RESET}"
                    print(f"{Colors.BOLD}{Colors.CYAN}============================================================{Colors.RESET}")
                    print(f"[TIME: {time.strftime('%H:%M:%S')}] 🏆 ASSET: {Colors.YELLOW}XAUUSD (GOLD){Colors.RESET} {sym_mode_tag} | v{BOT_VERSION} | Spread: {spread_pts} pts | RRR: 1:{symbol_rrr:.1f}")
                    print(f"{Colors.CYAN}------------------------------------------------------------{Colors.RESET}")
                    print(f"Gold Price   : {Colors.BOLD}{close_price:.{digits}f}{Colors.RESET} | ATR(14): {atr_val:.{digits}f}")
                    print(f"H4 Regime    : {h4_trend_color}{Colors.BOLD}{h4_trend_text}{Colors.RESET} | H1 Trend: {h1_trend_label}")
                    print(f"AI Predict   : UP {Colors.GREEN}{prob[1]:.2%}{Colors.RESET} | DOWN {Colors.RED}{prob[0]:.2%}{Colors.RESET}")
                    print(f"S&R Zone H1  : Support {support:.{digits}f} | Resistance {resistance:.{digits}f}")
                    print(f"Bollinger H1 : Lower {bb_lower_h1:.{digits}f} | Mid {bb_mid_h1:.{digits}f} | Upper {bb_upper_h1:.{digits}f} | MACD Hist: {macd_hist_h1:+.2f}")
                    print(f"MA(5/10) M15 : MA5: {ma5_val:.{digits}f} | MA10: {ma10_val:.{digits}f} | State: {ma_status_str}")
                    print(f"MA(5/10) H1  : MA5: {ma5_h1_val:.{digits}f} | MA10: {ma10_h1_val:.{digits}f} | State: {ma_h1_status_str}")
                    print(f"Status       : {status_color}{Colors.BOLD}{status_text}{Colors.RESET}{div_tag}")
                    if has_position:
                        for p in positions:
                            pos_type_str = "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL"
                            p_color = Colors.GREEN if p.profit >= 0 else Colors.RED
                            print(f"[POSITION] {pos_type_str} {p.volume:.2f} Lot @ {p.price_open:.{digits}f} | SL: {p.sl:.{digits}f} | TP: {p.tp:.{digits}f} | Profit: {p_color}${p.profit:.2f}{Colors.RESET}")
                    print(f"{Colors.BOLD}{Colors.CYAN}============================================================{Colors.RESET}\n")
                else:
                    # ถ้ารอนอกโซน แสดงรายงานกระชับ 1 บรรทัดสดๆ สำหรับทองคำ
                    print(f"[{time.strftime('%H:%M:%S')}] 🏆 {Colors.YELLOW}XAUUSD{Colors.RESET} Price: {Colors.BOLD}{close_price:>{digits+7}.{digits}f}{Colors.RESET} | {h4_badge} | AI: UP {Colors.GREEN}{prob[1]:.1%}{Colors.RESET} | DOWN {Colors.RED}{prob[0]:.1%}{Colors.RESET} | {status_text}{div_tag} (M15: {ma5_val:.1f}/{ma10_val:.1f} | H1: {ma5_h1_val:.1f}/{ma10_h1_val:.1f} | Sup: {support:.{digits}f} | Res: {resistance:.{digits}f})")
                
                # แคชสถานะเรดาร์แบบ Real-time ให้สตรีมขึ้นเว็บอัตโนมัติ
                is_alert_zone = bool(is_sweep_buy or is_sweep_sell or near_support or near_resistance or bb_buy_confirm or bb_sell_confirm or ma_cross_buy_confirm or ma_cross_sell_confirm or ma_cross_h1_up or ma_cross_h1_down or is_in_zone or bull_div_active or bear_div_active)
                latest_radar_cache[sym] = {
                    "symbol": sym,
                    "status": strip_ansi(status_text if not div_tag else f"{status_text} {div_tag.strip()}"),
                    "up_prob": round(float(prob[1]), 4),
                    "price": float(close_price),
                    "is_in_zone": is_alert_zone,
                    "h4_trend": h4_cloud_status,
                    "h4_diff_pct": round(h4_diff_pct, 2),
                    "h1_trend": h1_cloud_status,
                    "h1_diff_pct": round(h1_diff_pct, 2),
                    "h1_support": round(float(support), 2) if pd.notna(support) else 0.0,
                    "h1_resistance": round(float(resistance), 2) if pd.notna(resistance) else 0.0,
                    "h4_support": round(h4_support, 2),
                    "h1_lt_dir": int(h1_lt_dir),
                    "h1_dir": int(h1_dir),
                    "h1_stack_dir": int(h1_stack_dir),
                    "h4_stack_dir": int(h4_stack_dir),
                    "h1_cond": int(h1_cond),
                    "h4_cond": int(h4_cond),
                    "h1_cond_pct": round(h1_cond_pct, 2),
                    "h4_cond_pct": round(h4_cond_pct, 2),
                    "h1_sr_touches": [int(sr_h1["sup_touches"]), int(sr_h1["res_touches"])],
                    "h4_sr_touches": [int(sr_h4["sup_touches"]), int(sr_h4["res_touches"])],
                    "h4_dir": int(h4_dir),
                    "h4_lt_dir": int(h4_lt_dir),
                    "h4_ma200": round(h4_ma200, 2) if pd.notna(h4_ma200) else 0.0,
                    "h4_resistance": round(h4_resistance, 2),
                }
                
                # เก็บข้อมูลสินทรัพย์ที่น่าสนใจ (เข้าใกล้โซนเทรด)
                if is_in_zone:
                    interesting_symbols.append(f"{sym} (UP: {prob[1]:.2%}, DOWN: {prob[0]:.2%}) - {status_text}")
                    log_signal_event(sym, 'ZONE_ALERT', status_text, 'BUY' if 'BUY' in status_text else ('SELL' if 'SELL' in status_text else 'N/A'), close_price, prob[1], prob[0], h4_cloud_status, div_name, 'WAIT_AI_CONFIRM', f'{sym} in zone: {status_text}')
                elif near_support:
                    interesting_symbols.append(f"{sym} (UP: {prob[1]:.2%}, DOWN: {prob[0]:.2%}) - Near Support H1 (Waiting confirmation)")
                elif near_resistance:
                    interesting_symbols.append(f"{sym} (UP: {prob[1]:.2%}, DOWN: {prob[0]:.2%}) - Near Resistance H1 (Waiting confirmation)")
                
                if sym not in TRADE_SYMBOLS:
                    continue  # ถ้าเป็นคู่เงินโหมดดูเฉยๆ ให้ข้ามการยิงคำสั่งเทรดไปเลย
                
                # โหมดไม่สนสเปรด (ตามคำขอ): เข้าเทรดได้ทุกสภาวะตลาดโดยไม่มีข้อจำกัดเรื่องสเปรด
                
                if not has_position:
                    # ตรวจสอบระบบ Cooldown หลังปิดไม้ / Circuit Breaker
                    cd_minutes = COOLDOWN_MINUTES_XAU
                    cd_seconds = cd_minutes * 60
                    elapsed_time = time.time() - last_exit_time.get(sym, 0)
                    
                    if elapsed_time < cd_seconds:
                        rem_sec = int(cd_seconds - elapsed_time)
                        rem_m = rem_sec // 60
                        rem_s = rem_sec % 60
                        if is_in_zone:
                            label = "CIRCUIT BREAKER" if (last_exit_time.get(sym, 0) - time.time()) > cd_seconds else "COOLDOWN"
                            print(f"{Colors.YELLOW}[{label}] {sym} waiting {rem_m:02d}:{rem_s:02d}m before next trade (Loss streak: {consecutive_loss.get(sym, 0)}){Colors.RESET}")
                            log_signal_event(sym, 'RISK_BLOCKED', status_text, 'N/A', close_price, prob[1], prob[0], h4_cloud_status, div_name, label, f'Waiting {rem_m:02d}:{rem_s:02d}m before next trade (Loss streak: {consecutive_loss.get(sym, 0)})')
                        continue

                    # ---- Max Positions by Free Margin ----
                    # มาจินทุก $400 เปิดได้ 1 ไม้ (คำนวณจาก Free Margin ปัจจุบัน)
                    acc_info = mt5.account_info()
                    all_open_pos = mt5.positions_get()
                    total_open_pos = len(all_open_pos) if all_open_pos else 0
                    free_margin = float(acc_info.margin_free) if acc_info else 0.0
                    # มาร์จิ้นต่อไม้ปรับตามขนาดไม้ ($400 ต่อ 0.01 lot)
                    max_allowed = max(1, int(free_margin / (MARGIN_PER_TRADE * max(current_lot(), 0.01) / 0.01)))  # อย่างน้อย 1 ไม้
                    if total_open_pos >= max_allowed:
                        if is_in_zone:
                            print(f"{Colors.YELLOW}[MAX POSITIONS] {sym} มาจิน ${free_margin:.0f} → เปิดได้สูงสุด {max_allowed} ไม้ (เปิดอยู่แล้ว {total_open_pos} ไม้) — รอเปิดมาจินเพิ่มหรือปิดไม้เดิมก่อน{Colors.RESET}")
                            log_signal_event(sym, 'RISK_BLOCKED', status_text, 'N/A', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'MAX_POS_BLOCKED', f'Margin ${free_margin:.0f} max allowed {max_allowed} (Already open {total_open_pos})')
                        continue

                    # ---- Same Plan + Same Symbol Cooldown (60 นาที — เฉพาะไม้ขาดทุน) ----
                    # ห้ามเข้าทิศเดิมที่สกุลเดิมภายใน 60 นาที เฉพาะเมื่อไม้นั้นเคยขาดทุน
                    def _is_plan_blocked(direction, plan_name):
                        # แผนที่แอดมินปิดไว้ (เว็บ /admin/plans) — ห้ามเข้าไม้ใหม่
                        if not plan_config.is_enabled(plan_name):
                            key = (sym, plan_config.base_plan(plan_name))
                            if time.time() - _plan_disabled_logged.get(key, 0) > 600:
                                _plan_disabled_logged[key] = time.time()
                                print(f"{Colors.YELLOW}[PLAN DISABLED] {sym} {plan_config.base_plan(plan_name)} ถูกปิดโดยผู้ดูแลระบบ — ข้ามสัญญาณ {direction}{Colors.RESET}")
                            return True
                        sym_plans = last_loss_plan.get(sym, {})
                        if direction in sym_plans:
                            last_plan, last_ts = sym_plans[direction]
                            elapsed_p = time.time() - last_ts
                            if elapsed_p < SAME_PLAN_COOLDOWN_MINUTES * 60:
                                rem = int(SAME_PLAN_COOLDOWN_MINUTES * 60 - elapsed_p)
                                if is_in_zone:
                                    print(f"{Colors.YELLOW}[PLAN BLOCK] {sym} ไม้ขาดทุน ({last_plan} {direction}) เมื่อ {int(elapsed_p//60)}m - รอ {rem//60:02d}:{rem%60:02d}m ก่อนเข้า {plan_name} {direction} อีกครั้ง{Colors.RESET}")
                                    log_signal_event(sym, 'RISK_BLOCKED', plan_name, direction, close_price, prob[1], prob[0], h4_cloud_status, div_name, 'PLAN_BLOCKED', f'Loss on {last_plan} {direction} - waiting {rem//60:02d}:{rem%60:02d}m')
                                return True
                        # Plan 1/2: สัญญาณ Cross ค้างอยู่ตลอดอายุแท่ง (15 นาที / 1 ชม.) — ห้ามเข้าซ้ำบนแท่ง Cross เดิม
                        cross_bar = _cross_bar_for(plan_name)
                        if cross_bar is not None and last_cross_entry_bar.get((sym, plan_name, direction)) == cross_bar:
                            return True
                        return False  # ไม่มี loss block → เข้าได้เลย

                    def _cross_bar_for(plan_name):
                        if plan_name == "MA-Cross-Trend":
                            return ma_cross_bar_time
                        if plan_name == "MA-Cross-H1-Trend":
                            return ma_cross_h1_bar_time
                        return None

                    def _record_plan(direction, plan_name):
                        # loss block สร้างตอนปิดไม้ขาดทุนเท่านั้น — ที่นี่จดเฉพาะแท่ง Cross ที่เข้าไม้แล้ว (Plan 1/2)
                        cross_bar = _cross_bar_for(plan_name)
                        if cross_bar is not None:
                            last_cross_entry_bar[(sym, plan_name, direction)] = cross_bar
                    
                    tick = mt5.symbol_info_tick(sym)
                    if tick is None:
                        continue

                    # SL = 0.75 ATR (M15) สำหรับ Plan 3/4/5 · 0.75 ATR (H1) สำหรับ Plan 2
                    sl_dist = round(atr_val * SL_ATR_MULT, digits)
                    # Plan 1 (H1 MA100/150/200 + MA5×MA13 M15): SL คงที่ 0.75 ATR M15
                    # Backtest 2.5 ปี เทียบ Swing SL: กำไร 241 → 898 จุด, PF 1.03 → 1.13, Max DD 634 → 346
                    sl_dist_p4 = sl_dist
                    # ถ้ายังคำนวณ ATR H1 ไม่ได้ (ข้อมูลไม่พอ) ใช้ ATR M15 x2 เป็นค่าประมาณสำรอง
                    sl_dist_h1 = round((atr_h1_val if pd.notna(atr_h1_val) and atr_h1_val > 0 else atr_val * 2.0) * SL_ATR_MULT, digits)

                    # แผน 3: SMC Liquidity Sweep (SMC-LiquidityHunt)
                    if is_sweep_buy:
                        p_min = 0.48 if bull_div_active else 0.50
                        p_label = "SMC-LiquidityHunt+Div" if bull_div_active else "SMC-LiquidityHunt"
                        if prob[1] >= p_min:
                            h4_ok, h4_msg = check_h4_confluence('BUY', is_uptrend_h4, prob[1], prob[0], bull_div_active, bear_div_active, hidden_bull_active, hidden_bear_active, is_sideway_h4=is_sideway_h4, h4_diff_pct=h4_diff_pct)
                            if not h4_ok:
                                print(f"{Colors.YELLOW}[H4 CONFLUENCE FILTER] {sym} {p_label} BUY Skipped -> {h4_msg}{Colors.RESET}")
                                log_signal_event(sym, 'H4_FILTERED', p_label, 'BUY', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'H4_BLOCKED', h4_msg)
                            elif not _is_plan_blocked('BUY', p_label):
                                price = tick.ask
                                sl = round(price - sl_dist, digits)
                                risk = price - sl
                                tp = round(price + (risk * symbol_rrr), digits)
                                div_note = " + BULL DIVERGENCE (Grade A+)" if bull_div_active else ""
                                print(f"{Colors.GREEN}[SIGNAL] {sym} {p_label}: SMC Sweep Below Support + H1 UPTREND + AI UP ({prob[1]:.2%}){div_note} [{h4_msg}] -> SENDING BUY ORDER (SL={sl_dist:.{digits}f} / 0.75ATR){Colors.RESET}")
                                send_order(sym, mt5.ORDER_TYPE_BUY, price, sl, tp, plan_name=p_label)
                                log_signal_event(sym, 'ENTRY_SIGNAL', p_label, 'BUY', price, prob[1], prob[0], h4_cloud_status, div_name, 'ORDER_SENT', f'Lot {volume} | SL: {sl:.{digits}f} | TP: {tp:.{digits}f} ({h4_msg})')
                                _record_plan('BUY', p_label)
                        else:
                            log_signal_event(sym, 'ZONE_ALERT', p_label, 'BUY', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'WAIT_AI_CONFIRM', f'SMC Sweep Support | AI UP {prob[1]:.1%} < {p_min:.1%}')

                    elif is_sweep_sell:
                        p_min = 0.48 if bear_div_active else 0.50
                        p_label = "SMC-LiquidityHunt+Div" if bear_div_active else "SMC-LiquidityHunt"
                        if prob[0] >= p_min:
                            h4_ok, h4_msg = check_h4_confluence('SELL', is_uptrend_h4, prob[1], prob[0], bull_div_active, bear_div_active, hidden_bull_active, hidden_bear_active, is_sideway_h4=is_sideway_h4, h4_diff_pct=h4_diff_pct)
                            if not h4_ok:
                                print(f"{Colors.YELLOW}[H4 CONFLUENCE FILTER] {sym} {p_label} SELL Skipped -> {h4_msg}{Colors.RESET}")
                                log_signal_event(sym, 'H4_FILTERED', p_label, 'SELL', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'H4_BLOCKED', h4_msg)
                            elif not _is_plan_blocked('SELL', p_label):
                                price = tick.bid
                                sl = round(price + sl_dist, digits)
                                risk = sl - price
                                tp = round(price - (risk * symbol_rrr), digits)
                                div_note = " + BEAR DIVERGENCE (Grade A+)" if bear_div_active else ""
                                print(f"{Colors.RED}[SIGNAL] {sym} {p_label}: SMC Sweep Above Resistance + H1 DOWNTREND + AI DOWN ({prob[0]:.2%}){div_note} [{h4_msg}] -> SENDING SELL ORDER (SL={sl_dist:.{digits}f} / 0.75ATR){Colors.RESET}")
                                send_order(sym, mt5.ORDER_TYPE_SELL, price, sl, tp, plan_name=p_label)
                                log_signal_event(sym, 'ENTRY_SIGNAL', p_label, 'SELL', price, prob[1], prob[0], h4_cloud_status, div_name, 'ORDER_SENT', f'Lot {volume} | SL: {sl:.{digits}f} | TP: {tp:.{digits}f} ({h4_msg})')
                                _record_plan('SELL', p_label)
                        else:
                            log_signal_event(sym, 'ZONE_ALERT', p_label, 'SELL', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'WAIT_AI_CONFIRM', f'SMC Sweep Resistance | AI DOWN {prob[0]:.1%} < {p_min:.1%}')

                    # แผน 4: BUY Bounce (SR-SwingBounce)
                    elif bounce_buy_confirm:
                        has_div_boost = bull_div_active or hidden_bull_active
                        req_conf = (CONFIDENCE - 0.03) if has_div_boost else CONFIDENCE
                        p_label = "SR-SwingBounce+Div" if has_div_boost else "SR-SwingBounce"
                        if prob[1] >= req_conf:
                            h4_ok, h4_msg = check_h4_confluence('BUY', is_uptrend_h4, prob[1], prob[0], bull_div_active, bear_div_active, hidden_bull_active, hidden_bear_active, is_sideway_h4=is_sideway_h4, h4_diff_pct=h4_diff_pct)
                            if not h4_ok:
                                print(f"{Colors.YELLOW}[H4 CONFLUENCE FILTER] {sym} {p_label} BUY Skipped -> {h4_msg}{Colors.RESET}")
                                log_signal_event(sym, 'H4_FILTERED', p_label, 'BUY', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'H4_BLOCKED', h4_msg)
                            elif not _is_plan_blocked('BUY', p_label):
                                price = tick.ask
                                sl = round(price - sl_dist, digits)
                                risk = price - sl
                                tp = round(price + (risk * symbol_rrr), digits)
                                div_note = " + DIVERGENCE CONFLUENCE" if has_div_boost else ""
                                print(f"{Colors.GREEN}[SIGNAL] {sym} {p_label}: Bounce Support H1 + Wick Confirm + AI UP ({prob[1]:.2%}){div_note} [{h4_msg}] -> SENDING BUY ORDER (SL={sl_dist:.{digits}f} / 0.75ATR){Colors.RESET}")
                                send_order(sym, mt5.ORDER_TYPE_BUY, price, sl, tp, plan_name=p_label)
                                log_signal_event(sym, 'ENTRY_SIGNAL', p_label, 'BUY', price, prob[1], prob[0], h4_cloud_status, div_name, 'ORDER_SENT', f'Lot {volume} | SL: {sl:.{digits}f} | TP: {tp:.{digits}f} ({h4_msg})')
                                _record_plan('BUY', p_label)
                        else:
                            log_signal_event(sym, 'ZONE_ALERT', p_label, 'BUY', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'WAIT_AI_CONFIRM', f'Bounce Support H1 | AI UP {prob[1]:.1%} < {req_conf:.1%}')
                        
                    # แผน 4: SELL Bounce (SR-SwingBounce)
                    elif bounce_sell_confirm:
                        has_div_boost = bear_div_active or hidden_bear_active
                        req_conf = (CONFIDENCE - 0.03) if has_div_boost else CONFIDENCE
                        p_label = "SR-SwingBounce+Div" if has_div_boost else "SR-SwingBounce"
                        if prob[0] >= req_conf:
                            h4_ok, h4_msg = check_h4_confluence('SELL', is_uptrend_h4, prob[1], prob[0], bull_div_active, bear_div_active, hidden_bull_active, hidden_bear_active, is_sideway_h4=is_sideway_h4, h4_diff_pct=h4_diff_pct)
                            if not h4_ok:
                                print(f"{Colors.YELLOW}[H4 CONFLUENCE FILTER] {sym} {p_label} SELL Skipped -> {h4_msg}{Colors.RESET}")
                                log_signal_event(sym, 'H4_FILTERED', p_label, 'SELL', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'H4_BLOCKED', h4_msg)
                            elif not _is_plan_blocked('SELL', p_label):
                                price = tick.bid
                                sl = round(price + sl_dist, digits)
                                risk = sl - price
                                tp = round(price - (risk * symbol_rrr), digits)
                                div_note = " + DIVERGENCE CONFLUENCE" if has_div_boost else ""
                                print(f"{Colors.RED}[SIGNAL] {sym} {p_label}: Bounce Resistance H1 + Wick Confirm + AI DOWN ({prob[0]:.2%}){div_note} [{h4_msg}] -> SENDING SELL ORDER (SL={sl_dist:.{digits}f} / 0.75ATR){Colors.RESET}")
                                send_order(sym, mt5.ORDER_TYPE_SELL, price, sl, tp, plan_name=p_label)
                                log_signal_event(sym, 'ENTRY_SIGNAL', p_label, 'SELL', price, prob[1], prob[0], h4_cloud_status, div_name, 'ORDER_SENT', f'Lot {volume} | SL: {sl:.{digits}f} | TP: {tp:.{digits}f} ({h4_msg})')
                                _record_plan('SELL', p_label)
                        else:
                            log_signal_event(sym, 'ZONE_ALERT', p_label, 'SELL', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'WAIT_AI_CONFIRM', f'Bounce Resistance H1 | AI DOWN {prob[0]:.1%} < {req_conf:.1%}')

                    # แผน 5: BUY BB-H1-Reversion (Plan 5) - เปิดเฉพาะ XAUUSD
                    elif bb_buy_confirm:
                        req_bb_p = 0.50
                        p_label = "BB-H1-Reversion+Div"
                        if prob[1] >= req_bb_p:
                            h4_ok, h4_msg = check_h4_confluence('BUY', is_uptrend_h4, prob[1], prob[0], bull_div_active, bear_div_active, hidden_bull_active, hidden_bear_active, is_sideway_h4=is_sideway_h4, h4_diff_pct=h4_diff_pct)
                            if not h4_ok:
                                print(f"{Colors.YELLOW}[H4 CONFLUENCE FILTER] {sym} {p_label} BUY Skipped -> {h4_msg}{Colors.RESET}")
                                log_signal_event(sym, 'H4_FILTERED', p_label, 'BUY', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'H4_BLOCKED', h4_msg)
                            elif not _is_plan_blocked('BUY', p_label):
                                price = tick.ask
                                sl = round(price - sl_dist, digits)
                                risk = price - sl
                                tp = round(price + (risk * symbol_rrr), digits)
                                div_note = " + DIVERGENCE + MACD CONFLUENCE"
                                print(f"{Colors.GREEN}[SIGNAL] {sym} {p_label}: H1 Lower Band Rejection + AI UP ({prob[1]:.2%}){div_note} [{h4_msg}] -> SENDING BUY ORDER (SL={sl_dist:.{digits}f} / 0.75ATR){Colors.RESET}")
                                send_order(sym, mt5.ORDER_TYPE_BUY, price, sl, tp, plan_name=p_label)
                                log_signal_event(sym, 'ENTRY_SIGNAL', p_label, 'BUY', price, prob[1], prob[0], h4_cloud_status, div_name, 'ORDER_SENT', f'Lot {volume} | SL: {sl:.{digits}f} | TP: {tp:.{digits}f} ({h4_msg})')
                                _record_plan('BUY', p_label)
                        else:
                            log_signal_event(sym, 'ZONE_ALERT', p_label, 'BUY', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'WAIT_AI_CONFIRM', f'H1 BB Lower Band Rejection | AI UP {prob[1]:.1%} < {req_bb_p:.1%}')

                    # แผน 5: SELL BB-H1-Reversion (Plan 5) - เปิดเฉพาะ XAUUSD
                    elif bb_sell_confirm:
                        req_bb_p = 0.50
                        p_label = "BB-H1-Reversion+Div"
                        if prob[0] >= req_bb_p:
                            h4_ok, h4_msg = check_h4_confluence('SELL', is_uptrend_h4, prob[1], prob[0], bull_div_active, bear_div_active, hidden_bull_active, hidden_bear_active, is_sideway_h4=is_sideway_h4, h4_diff_pct=h4_diff_pct)
                            if not h4_ok:
                                print(f"{Colors.YELLOW}[H4 CONFLUENCE FILTER] {sym} {p_label} SELL Skipped -> {h4_msg}{Colors.RESET}")
                                log_signal_event(sym, 'H4_FILTERED', p_label, 'SELL', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'H4_BLOCKED', h4_msg)
                            elif not _is_plan_blocked('SELL', p_label):
                                price = tick.bid
                                sl = round(price + sl_dist, digits)
                                risk = sl - price
                                tp = round(price - (risk * symbol_rrr), digits)
                                div_note = " + DIVERGENCE + MACD CONFLUENCE"
                                print(f"{Colors.RED}[SIGNAL] {sym} {p_label}: H1 Upper Band Rejection + AI DOWN ({prob[0]:.2%}){div_note} [{h4_msg}] -> SENDING SELL ORDER (SL={sl_dist:.{digits}f} / 0.75ATR){Colors.RESET}")
                                send_order(sym, mt5.ORDER_TYPE_SELL, price, sl, tp, plan_name=p_label)
                                log_signal_event(sym, 'ENTRY_SIGNAL', p_label, 'SELL', price, prob[1], prob[0], h4_cloud_status, div_name, 'ORDER_SENT', f'Lot {volume} | SL: {sl:.{digits}f} | TP: {tp:.{digits}f} ({h4_msg})')
                                _record_plan('SELL', p_label)
                        else:
                            log_signal_event(sym, 'ZONE_ALERT', p_label, 'SELL', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'WAIT_AI_CONFIRM', f'H1 BB Upper Band Rejection | AI DOWN {prob[0]:.1%} < {req_bb_p:.1%}')

                    # แผน 1: BUY MA-Cross-Trend (MA 5 ตัดขึ้น MA 10 บนแท่ง M15 + เทรนด์ H1 Uptrend)
                    elif ma_cross_buy_confirm:
                        p_label = "MA-Cross-Trend"
                        h4_ok, h4_msg = True, "H1 MA100/150/200 ขาขึ้น"  # Plan 1 ใช้เฉพาะ 2 กฎที่กำหนด
                        if not h4_ok:
                            print(f"{Colors.YELLOW}[H4 CONFLUENCE FILTER] {sym} {p_label} BUY Skipped -> {h4_msg}{Colors.RESET}")
                            log_signal_event(sym, 'H4_FILTERED', p_label, 'BUY', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'H4_BLOCKED', h4_msg)
                        elif not _is_plan_blocked('BUY', p_label):
                            price = tick.ask
                            sl = round(price - sl_dist_p4, digits)
                            tp = 0.0  # Plan 1: ไม่ต้องตั้ง TP (รันตามเทรนด์ ปิดทันทีเมื่อ MA5 ตัดลง MA10)
                            print(f"{Colors.GREEN}[SIGNAL] {sym} {p_label}: MA5 Crossed Above MA13 + [{h4_msg}] -> SENDING BUY ORDER (SL={sl_dist_p4:.{digits}f} / 0.75ATR, NO TP - Exit on MA5 Cross Below MA13){Colors.RESET}")
                            send_order(sym, mt5.ORDER_TYPE_BUY, price, sl, tp, plan_name=p_label)
                            log_signal_event(sym, 'ENTRY_SIGNAL', p_label, 'BUY', price, prob[1], prob[0], h4_cloud_status, div_name, 'ORDER_SENT', f'Lot {volume} | SL: {sl:.{digits}f} | No TP (Exit on Cross) ({h4_msg})')
                            _record_plan('BUY', p_label)

                    # แผน 1: SELL MA-Cross-Trend (MA 5 ตัดลง MA 10 บนแท่ง M15 + เทรนด์ H1 Downtrend)
                    elif ma_cross_sell_confirm:
                        p_label = "MA-Cross-Trend"
                        h4_ok, h4_msg = True, "H1 MA100/150/200 ขาลง"  # Plan 1 ใช้เฉพาะ 2 กฎที่กำหนด
                        if not h4_ok:
                            print(f"{Colors.YELLOW}[H4 CONFLUENCE FILTER] {sym} {p_label} SELL Skipped -> {h4_msg}{Colors.RESET}")
                            log_signal_event(sym, 'H4_FILTERED', p_label, 'SELL', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'H4_BLOCKED', h4_msg)
                        elif not _is_plan_blocked('SELL', p_label):
                            price = tick.bid
                            sl = round(price + sl_dist_p4, digits)
                            tp = 0.0  # Plan 1: ไม่ต้องตั้ง TP (รันตามเทรนด์ ปิดทันทีเมื่อ MA5 ตัดขึ้น MA10)
                            print(f"{Colors.RED}[SIGNAL] {sym} {p_label}: MA5 Crossed Below MA13 + [{h4_msg}] -> SENDING SELL ORDER (SL={sl_dist_p4:.{digits}f} / 0.75ATR, NO TP - Exit on MA5 Cross Above MA13){Colors.RESET}")
                            send_order(sym, mt5.ORDER_TYPE_SELL, price, sl, tp, plan_name=p_label)
                            log_signal_event(sym, 'ENTRY_SIGNAL', p_label, 'SELL', price, prob[1], prob[0], h4_cloud_status, div_name, 'ORDER_SENT', f'Lot {volume} | SL: {sl:.{digits}f} | No TP (Exit on Cross) ({h4_msg})')
                            _record_plan('SELL', p_label)

                    # แผน 2: BUY MA-Cross-H1-Trend (MA 5 ตัดขึ้น MA 10 บนแท่ง H1 + เทรนด์ H4 Bullish - เข้าไม้ H1 กรองเทรนด์ H4)
                    elif ma_cross_h1_up and plan5_buy_ok:
                        p_label = "MA-Cross-H1-Trend"
                        h4_ok, h4_msg = True, "H4 ขาขึ้น + MA5 ชันขึ้น + เหนือ MA200"
                        if not h4_ok:
                            print(f"{Colors.YELLOW}[H4 CONFLUENCE FILTER] {sym} {p_label} BUY Skipped -> {h4_msg}{Colors.RESET}")
                            log_signal_event(sym, 'H4_FILTERED', p_label, 'BUY', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'H4_BLOCKED', h4_msg)
                        elif not _is_plan_blocked('BUY', p_label):
                            price = tick.ask
                            sl = round(price - sl_dist_h1, digits)
                            tp = 0.0  # Plan 2: ไม่ต้องตั้ง TP (รันตามเทรนด์ H1 ปิดทันทีเมื่อ MA5 ตัดลง MA10 บน H1)
                            print(f"{Colors.GREEN}[SIGNAL] {sym} {p_label}: MA5 Crossed Above MA10 on H1 + [{h4_msg}] -> SENDING BUY ORDER (SL={sl_dist_h1:.{digits}f} / 0.75ATR H1, NO TP - Exit on H1 MA5 Cross Below MA10){Colors.RESET}")
                            send_order(sym, mt5.ORDER_TYPE_BUY, price, sl, tp, plan_name=p_label)
                            log_signal_event(sym, 'ENTRY_SIGNAL', p_label, 'BUY', price, prob[1], prob[0], h4_cloud_status, div_name, 'ORDER_SENT', f'Lot {volume} | SL: {sl:.{digits}f} | No TP (Exit on H1 Cross) ({h4_msg})')
                            _record_plan('BUY', p_label)

                    # แผน 2: SELL MA-Cross-H1-Trend (MA 5 ตัดลง MA 10 บนแท่ง H1 + เทรนด์ H4 Bearish - เข้าไม้ H1 กรองเทรนด์ H4)
                    elif ma_cross_h1_down and plan5_sell_ok:
                        p_label = "MA-Cross-H1-Trend"
                        h4_ok, h4_msg = True, "H4 ขาลง + MA5 ชันลง + ใต้ MA200"
                        if not h4_ok:
                            print(f"{Colors.YELLOW}[H4 CONFLUENCE FILTER] {sym} {p_label} SELL Skipped -> {h4_msg}{Colors.RESET}")
                            log_signal_event(sym, 'H4_FILTERED', p_label, 'SELL', close_price, prob[1], prob[0], h4_cloud_status, div_name, 'H4_BLOCKED', h4_msg)
                        elif not _is_plan_blocked('SELL', p_label):
                            price = tick.bid
                            sl = round(price + sl_dist_h1, digits)
                            tp = 0.0  # Plan 2: ไม่ต้องตั้ง TP (รันตามเทรนด์ H1 ปิดทันทีเมื่อ MA5 ตัดขึ้น MA10 บน H1)
                            print(f"{Colors.RED}[SIGNAL] {sym} {p_label}: MA5 Crossed Below MA10 on H1 + [{h4_msg}] -> SENDING SELL ORDER (SL={sl_dist_h1:.{digits}f} / 0.75ATR H1, NO TP - Exit on H1 MA5 Cross Above MA10){Colors.RESET}")
                            send_order(sym, mt5.ORDER_TYPE_SELL, price, sl, tp, plan_name=p_label)
                            log_signal_event(sym, 'ENTRY_SIGNAL', p_label, 'SELL', price, prob[1], prob[0], h4_cloud_status, div_name, 'ORDER_SENT', f'Lot {volume} | SL: {sl:.{digits}f} | No TP (Exit on H1 Cross) ({h4_msg})')
                            _record_plan('SELL', p_label)
                else:
                    # เช็คเงื่อนไขการจัดการ Position (Plan 1 MA Exit + Plan 2 H1 MA Exit + AI Reversal + Early BE Lock + Unlimited Dynamic TP)
                    open_tickets = {p.ticket for p in positions}
                    stale = [t for t in p4_trail_steps if t not in open_tickets]
                    if stale:
                        for t in stale:
                            p4_trail_steps.pop(t, None)
                        _save_p4_trail_state(p4_trail_steps)
                    for pos in positions:
                        # 0.1 Plan 1 Opposite MA Cross Exit (เงื่อนไขปิดไม้เฉพาะ Plan 1: MA5 ตัดกลับขั้วตรงข้าม M15)
                        # - ถ้าถือ BUY: เมื่อ MA 5 ตัดลง MA 10 บนแท่ง M15 ให้ปิดไม้ทันที
                        # - ถ้าถือ SELL: เมื่อ MA 5 ตัดขึ้น MA 10 บนแท่ง M15 ให้ปิดไม้ทันที
                        if pos.comment == "MA-Cross-Trend":
                            if pos.type == mt5.ORDER_TYPE_BUY and p4_cross_down:
                                p_color = Colors.GREEN if pos.profit >= 0 else Colors.RED
                                print(f"{Colors.YELLOW}[PLAN 1 EXIT] {sym} MA5 Crossed Below MA13. Closing BUY position immediately! Profit: {p_color}${pos.profit:.2f}{Colors.RESET}")
                                log_signal_event(sym, 'POSITION_MGMT', 'MA-Cross-Trend', 'SELL', tick.bid, prob[1], prob[0], h4_cloud_status, div_name, 'MA_CROSS_EXIT', f'MA5 crossed below MA13 (Profit: ${pos.profit:.2f})')
                                close_position(pos, comment="MA5 Cross Down Exit")
                                continue
                            elif pos.type == mt5.ORDER_TYPE_SELL and p4_cross_up:
                                p_color = Colors.GREEN if pos.profit >= 0 else Colors.RED
                                print(f"{Colors.YELLOW}[PLAN 1 EXIT] {sym} MA5 Crossed Above MA13. Closing SELL position immediately! Profit: {p_color}${pos.profit:.2f}{Colors.RESET}")
                                log_signal_event(sym, 'POSITION_MGMT', 'MA-Cross-Trend', 'BUY', tick.ask, prob[1], prob[0], h4_cloud_status, div_name, 'MA_CROSS_EXIT', f'MA5 crossed above MA13 (Profit: ${pos.profit:.2f})')
                                close_position(pos, comment="MA5 Cross Up Exit")
                                continue
                            # Step Trailing: ทุกกำไร 5 จุด เลื่อน SL 40% ของระยะ SL → ราคา
                            if apply_p4_step_trailing(pos, tick, mt5.symbol_info(sym)):
                                continue

                        # 0.2 Plan 2 Opposite MA Cross Exit on H1 (เงื่อนไขปิดไม้เฉพาะ Plan 2: MA5 ตัดกลับขั้วตรงข้าม H1)
                        # - ถ้าถือ BUY: เมื่อ MA 5 ตัดลง MA 10 บนแท่ง H1 ให้ปิดไม้ทันที
                        # - ถ้าถือ SELL: เมื่อ MA 5 ตัดขึ้น MA 10 บนแท่ง H1 ให้ปิดไม้ทันที
                        if pos.comment == "MA-Cross-H1-Trend":
                            if pos.type == mt5.ORDER_TYPE_BUY and ma_cross_h1_down:
                                p_color = Colors.GREEN if pos.profit >= 0 else Colors.RED
                                print(f"{Colors.YELLOW}[PLAN 2 EXIT] {sym} MA5 Crossed Below MA10 on H1. Closing BUY position immediately! Profit: {p_color}${pos.profit:.2f}{Colors.RESET}")
                                log_signal_event(sym, 'POSITION_MGMT', 'MA-Cross-H1-Trend', 'SELL', tick.bid, prob[1], prob[0], h4_cloud_status, div_name, 'MA_CROSS_H1_EXIT', f'H1 MA5 crossed below MA10 (Profit: ${pos.profit:.2f})')
                                close_position(pos, comment="H1 MA5 Cross Down Exit")
                                continue
                            elif pos.type == mt5.ORDER_TYPE_SELL and ma_cross_h1_up:
                                p_color = Colors.GREEN if pos.profit >= 0 else Colors.RED
                                print(f"{Colors.YELLOW}[PLAN 2 EXIT] {sym} MA5 Crossed Above MA10 on H1. Closing SELL position immediately! Profit: {p_color}${pos.profit:.2f}{Colors.RESET}")
                                log_signal_event(sym, 'POSITION_MGMT', 'MA-Cross-H1-Trend', 'BUY', tick.ask, prob[1], prob[0], h4_cloud_status, div_name, 'MA_CROSS_H1_EXIT', f'H1 MA5 crossed above MA10 (Profit: ${pos.profit:.2f})')
                                close_position(pos, comment="H1 MA5 Cross Up Exit")
                                continue

                        # 1. เช็คเงื่อนไขการตัดขาดทุนเมื่อทิศทางเปลี่ยน (AI Dynamic Exit พร้อม Whipsaw Protection)
                        if pos.type == mt5.ORDER_TYPE_BUY and prob[0] >= 0.60 and (tick.bid < pos.price_open):
                            print(f"{Colors.YELLOW}[AI REVERSAL] {sym} Reversal detected! AI DOWN ({prob[0]:.2%}). Closing BUY position.{Colors.RESET}")
                            log_signal_event(sym, 'POSITION_MGMT', 'AI-Reversal', 'SELL', tick.bid, prob[1], prob[0], h4_cloud_status, div_name, 'REVERSAL_EXIT', f'AI DOWN {prob[0]:.1%} >= 60%')
                            close_position(pos)
                            continue
                        
                        elif pos.type == mt5.ORDER_TYPE_SELL and prob[1] >= 0.60 and (tick.ask > pos.price_open):
                            print(f"{Colors.YELLOW}[AI REVERSAL] {sym} Reversal detected! AI UP ({prob[1]:.2%}). Closing SELL position.{Colors.RESET}")
                            log_signal_event(sym, 'POSITION_MGMT', 'AI-Reversal', 'BUY', tick.ask, prob[1], prob[0], h4_cloud_status, div_name, 'REVERSAL_EXIT', f'AI UP {prob[1]:.1%} >= 60%')
                            close_position(pos)
                            continue

                        # 2. Early Break-Even Lock & Unlimited Dynamic TP
                        if pos.tp <= 0.0:
                            continue

                        if pos.type == mt5.ORDER_TYPE_BUY:
                            target_dist = pos.tp - pos.price_open
                            current_gain = tick.bid - pos.price_open
                            
                            # Early Break-Even: ถ้าราคาไปได้ 70% ของเป้า ขยับ SL มาล็อคกำไรที่ +0.35 ATR
                            # [Priority 2] Throttle: ห้าม lock ซ้ำภายใน 60 วินาที
                            # [Priority 3] Buffer: SL ที่ lock ต้องอยู่ห่างจากราคาตลาดอย่างน้อย 0.4 ATR
                            if current_gain >= (target_dist * 0.70):
                                be_sl = round(pos.price_open + (atr_val * 0.35), digits)
                                min_sl_dist_from_market = atr_val * BE_LOCK_BUFFER_ATR
                                throttle_ok = (time.time() - last_lock_time.get(pos.ticket, 0)) >= LOCK_SL_THROTTLE_SECS
                                buffer_ok = be_sl < (tick.bid - min_sl_dist_from_market)
                                if be_sl > pos.sl and throttle_ok and buffer_ok:
                                    print(f"{Colors.CYAN}[PROFIT LOCK 70%] {sym} Moved SL to +0.35 ATR: {pos.sl:.{digits}f} -> {be_sl:.{digits}f} (Buffer: {min_sl_dist_from_market:.{digits}f} ATR, Market: {tick.bid:.{digits}f}){Colors.RESET}")
                                    modify_position(pos, be_sl, pos.tp, reason="Early Profit Lock (70% Target / +0.35 ATR)")
                                    last_lock_time[pos.ticket] = time.time()
                                elif not throttle_ok:
                                    print(f"{Colors.YELLOW}[LOCK THROTTLE] {sym} รอ {int(LOCK_SL_THROTTLE_SECS - (time.time()-last_lock_time.get(pos.ticket,0)))}s ก่อน lock ซ้ำ{Colors.RESET}")
                                elif not buffer_ok:
                                    print(f"{Colors.YELLOW}[LOCK BUFFER] {sym} be_sl={be_sl:.{digits}f} ใกล้ตลาดเกินไป (buffer < {BE_LOCK_BUFFER_ATR} ATR) — ข้ามไปก่อน{Colors.RESET}")

                            # Unlimited Dynamic TP: เมื่อราคาใกล้เป้า 80% และ AI ยังมองขึ้นต่อเนื่อง
                            if target_dist > 0 and current_gain >= (0.80 * target_dist) and prob[1] >= CONFIDENCE:
                                new_tp = round(pos.tp + (atr_val * 1.0), digits) # ดัน TP ขึ้นอีก 1 ATR
                                lock_sl = max(pos.price_open + (atr_val * 0.3), tick.bid - (atr_val * 1.0))
                                new_sl = round(max(pos.sl, lock_sl), digits)
                                if new_sl >= tick.bid:
                                    new_sl = round(tick.bid - (atr_val * 0.2), digits)
                                throttle_ok = (time.time() - last_lock_time.get(pos.ticket, 0)) >= LOCK_SL_THROTTLE_SECS
                                if new_tp > pos.tp and throttle_ok:
                                    print(f"{Colors.GREEN}[DYNAMIC TP] {sym} Extending TP: {pos.tp:.{digits}f} -> {new_tp:.{digits}f} | Lock SL: {new_sl:.{digits}f}{Colors.RESET}")
                                    modify_position(pos, new_sl, new_tp, reason="Unlimited Dynamic TP")
                                    last_lock_time[pos.ticket] = time.time()

                        elif pos.type == mt5.ORDER_TYPE_SELL:
                            target_dist = pos.price_open - pos.tp
                            current_gain = pos.price_open - tick.ask
                            
                            # Early Break-Even: ถ้าราคาลงมาได้ 70% ของเป้า ขยับ SL มาล็อคกำไรที่ -0.35 ATR
                            # [Priority 2] Throttle: ห้าม lock ซ้ำภายใน 60 วินาที
                            # [Priority 3] Buffer: SL ที่ lock ต้องอยู่ห่างจากราคาตลาดอย่างน้อย 0.4 ATR
                            if current_gain >= (target_dist * 0.70):
                                be_sl = round(pos.price_open - (atr_val * 0.35), digits)
                                min_sl_dist_from_market = atr_val * BE_LOCK_BUFFER_ATR
                                throttle_ok = (time.time() - last_lock_time.get(pos.ticket, 0)) >= LOCK_SL_THROTTLE_SECS
                                buffer_ok = be_sl > (tick.ask + min_sl_dist_from_market)
                                if (pos.sl == 0 or be_sl < pos.sl) and throttle_ok and buffer_ok:
                                    print(f"{Colors.CYAN}[PROFIT LOCK 70%] {sym} Moved SL to -0.35 ATR: {pos.sl:.{digits}f} -> {be_sl:.{digits}f} (Buffer: {min_sl_dist_from_market:.{digits}f} ATR, Market: {tick.ask:.{digits}f}){Colors.RESET}")
                                    modify_position(pos, be_sl, pos.tp, reason="Early Profit Lock (70% Target / -0.35 ATR)")
                                    last_lock_time[pos.ticket] = time.time()
                                elif not throttle_ok:
                                    print(f"{Colors.YELLOW}[LOCK THROTTLE] {sym} รอ {int(LOCK_SL_THROTTLE_SECS - (time.time()-last_lock_time.get(pos.ticket,0)))}s ก่อน lock ซ้ำ{Colors.RESET}")
                                elif not buffer_ok:
                                    print(f"{Colors.YELLOW}[LOCK BUFFER] {sym} be_sl={be_sl:.{digits}f} ใกล้ตลาดเกินไป (buffer < {BE_LOCK_BUFFER_ATR} ATR) — ข้ามไปก่อน{Colors.RESET}")

                            # Unlimited Dynamic TP: เมื่อราคาลงมาใกล้เป้า 80% และ AI ยังมองลงต่อเนื่อง
                            if target_dist > 0 and current_gain >= (0.80 * target_dist) and prob[0] >= CONFIDENCE:
                                new_tp = round(pos.tp - (atr_val * 1.0), digits) # ดัน TP ลงอีก 1 ATR
                                lock_sl = min(pos.price_open - (atr_val * 0.3), tick.ask + (atr_val * 1.0))
                                new_sl = round(min(pos.sl, lock_sl) if pos.sl > 0 else lock_sl, digits)
                                if new_sl <= tick.ask:
                                    new_sl = round(tick.ask + (atr_val * 0.2), digits)
                                throttle_ok = (time.time() - last_lock_time.get(pos.ticket, 0)) >= LOCK_SL_THROTTLE_SECS
                                if new_tp < pos.tp and throttle_ok:
                                    print(f"{Colors.GREEN}[DYNAMIC TP] {sym} Extending TP: {pos.tp:.{digits}f} -> {new_tp:.{digits}f} | Lock SL: {new_sl:.{digits}f}{Colors.RESET}")
                                    modify_position(pos, new_sl, new_tp, reason="Unlimited Dynamic TP")
                                    last_lock_time[pos.ticket] = time.time()
                            
            # --- สรุปคู่เงินที่น่าสนใจท้ายรอบ ---
            # --- สรุปสินทรัพย์ที่น่าสนใจท้ายรอบ ---
            if len(interesting_symbols) > 0:
                print(f"\n{Colors.BOLD}{Colors.YELLOW}*** AI SIGNAL ALERT: Assets In/Near Trading Zone ***{Colors.RESET}")
                # สรุปเรดาร์แสดงผลบนหน้าจอ (ปิดเสียงเตือนตามความต้องการ)
                
                for item in interesting_symbols:
                    print(f"  -> {item}")
                print(f"{Colors.CYAN}------------------------------------------------------------{Colors.RESET}\n")
            
            # ระบบนับถอยหลัง Real-time Ticker แสดงวินาทีวิ่งสดบนหน้าจอ ป้องกัน Terminal นิ่ง/ค้าง
            COUNTDOWN_SECONDS = 20
            for sec in range(COUNTDOWN_SECONDS, 0, -1):
                if not BOT_RUNNING_FLAG or BOT_PAUSED_FLAG:
                    break
                print(f"\r[AI SCANNER] Next market scan in {sec:02d}s... (Press Ctrl+C to stop)  ", end="", flush=True)
                time.sleep(1)
            print("\r" + " " * 85 + "\r", end="", flush=True)
            
        except KeyboardInterrupt:
            print("\n[STOP] Bot stopped by user (Ctrl+C). Shutting down cleanly.")
            break
            
    mt5.shutdown()

if __name__ == "__main__":
    main()