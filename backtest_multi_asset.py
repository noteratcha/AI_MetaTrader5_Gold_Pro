import MetaTrader5 as mt5
import pandas as pd
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)
import numpy as np
from sklearn.ensemble import RandomForestClassifier

SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
TIMEFRAME_H1 = mt5.TIMEFRAME_H1
TIMEFRAME_H4 = mt5.TIMEFRAME_H4
TOTAL_BARS = 30000    # ดึงราคาย้อนหลังเพื่อหาสัญญาณให้ครบ 100 ไม้
TRAIN_BARS = 5000     # ใช้ 5,000 แท่งแรกเพื่อสอน AI
TP_RRR_XAU = 1.50          # Sweet Spot RRR สำหรับทองคำ (1:1.50 เพื่อ Win Rate 47-50%)
TP_RRR_BTC = 1.50          # Sweet Spot RRR สำหรับบิตคอยน์ (1:1.50 + Unlimited Dynamic TP)
TP_RRR_DEFAULT = 1.50      # สำหรับคู่เงินอื่นๆ
CONFIDENCE = 0.54         # ความมั่นใจ AI ขั้นต่ำ 54%
BACKTEST_VERSION = "2026.1003.0025" # เลขเวอร์ชันระบบ Engine Backtest (XAUUSD Gold Specialist + Plan 4 M15 + Plan 5 H1 MA Cross)
SL_ATR_MULT = 0.75        # ขยายพื้นที่หายใจ SL = 0.75 ATR (ป้องกัน Market Noise ในแท่ง M15)

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

def run_backtest(symbol, custom_gap=None):
    mt5.symbol_select(symbol, True)
    info = mt5.symbol_info(symbol)
    spread_pts = info.spread if info is not None else 0
    point = info.point if info is not None else 0.01
    digits = info.digits if info is not None else 2
    
    # buffer = spread ของแต่ละอันตามที่กำหนด
    if custom_gap is not None:
        gap_buffer = custom_gap
    else:
        gap_buffer = spread_pts * point

    print(f"\n=============================================")
    print(f"🚀 เริ่มต้นการ Backtest สำหรับ {symbol} (Engine v{BACKTEST_VERSION})")
    print(f"🎯 Spread ปัจจุบัน: {spread_pts} pts | Buffer ที่ใช้: {gap_buffer:.{digits}f}")
    print(f"=============================================")
    print(f"📥 กำลังดึงข้อมูล {symbol} M15 {TOTAL_BARS} แท่งเทียนย้อนหลัง...")
    df_m15 = get_data(symbol, TIMEFRAME, TOTAL_BARS)
    
    print(f"📥 กำลังดึงข้อมูล {symbol} H1 เพื่อดูเทรนด์ใหญ่...")
    df_h1 = get_data(symbol, TIMEFRAME_H1, (TOTAL_BARS // 4) + 100)
    
    print(f"📥 กำลังดึงข้อมูล {symbol} H4 เพื่อดูเทรนด์ระยะยาว...")
    df_h4 = get_data(symbol, TIMEFRAME_H4, (TOTAL_BARS // 16) + 100)

    if df_m15 is None or df_h1 is None or df_h4 is None:
        print("❌ ดึงข้อมูลไม่สำเร็จ")
        return

    # ==========================================
    # การเตรียมข้อมูล Multi-timeframe (H1)
    # ==========================================
    df_h1['ma_fast_h1'] = df_h1['close'].rolling(10).mean()
    df_h1['ma_slow_h1'] = df_h1['close'].rolling(30).mean()
    df_h1['trend_h1'] = df_h1['ma_fast_h1'] / df_h1['ma_slow_h1']
    
    # สร้าง Support & Resistance บน H1 จาก 20 ชั่วโมงก่อนหน้า (ไม่รวมแท่งปัจจุบัน)
    df_h1['resistance'] = df_h1['high'].shift(1).rolling(20).max()
    df_h1['support'] = df_h1['low'].shift(1).rolling(20).min()
    
    # H1 Bollinger Bands (SMA 20, 2 STD) - Shift 1 ป้องกัน Repaint ระหว่างชั่วโมง
    df_h1['bb_mid_h1'] = df_h1['close'].shift(1).rolling(20).mean()
    df_h1['bb_std_h1'] = df_h1['close'].shift(1).rolling(20).std()
    df_h1['bb_upper_h1'] = df_h1['bb_mid_h1'] + (2.0 * df_h1['bb_std_h1'])
    df_h1['bb_lower_h1'] = df_h1['bb_mid_h1'] - (2.0 * df_h1['bb_std_h1'])

    # H1 MACD (12, 26, 9) เพื่อดักจับการหมดแรง (Exhaustion) ของโมเมนตัม
    ema12_h1 = df_h1['close'].ewm(span=12, adjust=False).mean()
    ema26_h1 = df_h1['close'].ewm(span=26, adjust=False).mean()
    df_h1['macd_h1'] = ema12_h1 - ema26_h1
    df_h1['macd_sig_h1'] = df_h1['macd_h1'].ewm(span=9, adjust=False).mean()
    df_h1['macd_hist_h1'] = df_h1['macd_h1'] - df_h1['macd_sig_h1']

    # Moving Average 5 & 10 บนแท่ง H1 สำหรับ Plan 5 (MA-Cross-H1-Trend)
    df_h1['ma5_h1'] = df_h1['close'].rolling(5).mean()
    df_h1['ma10_h1'] = df_h1['close'].rolling(10).mean()

    # สร้าง column 'time_h1' แบบปัดเศษชั่วโมงเพื่อไป join กับ M15
    df_h1['time_h1'] = df_h1['time'].dt.floor('h')
    df_h1_features = df_h1[['time_h1', 'trend_h1', 'resistance', 'support', 'bb_mid_h1', 'bb_upper_h1', 'bb_lower_h1', 'macd_hist_h1', 'ma5_h1', 'ma10_h1']].dropna()

    # ==========================================
    # การเตรียมข้อมูล Multi-timeframe (H4)
    # ==========================================
    df_h4['ma_fast_h4'] = df_h4['close'].rolling(10).mean()
    df_h4['ma_slow_h4'] = df_h4['close'].rolling(30).mean()
    df_h4['trend_h4'] = df_h4['ma_fast_h4'] / df_h4['ma_slow_h4']
    df_h4['h4_diff_pct'] = ((df_h4['ma_fast_h4'] / df_h4['ma_slow_h4']) - 1.0) * 100.0
    
    df_h4['time_h4'] = df_h4['time'].dt.floor('4h')
    df_h4_features = df_h4[['time_h4', 'trend_h4', 'h4_diff_pct']].dropna()

    # ==========================================
    # จัดการข้อมูลหลัก M15 และรวม H1, H4
    # ==========================================
    df = df_m15.copy()
    df['time_h1'] = df['time'].dt.floor('h')
    
    # รวมข้อมูล H1 เข้ากับ M15
    df = pd.merge(df, df_h1_features, on='time_h1', how='left')
    # เติมค่าว่าง (Forward fill) กรณีแท่ง H1 ยังไม่ปิด
    df['trend_h1'] = df['trend_h1'].ffill()
    df['resistance'] = df['resistance'].ffill()
    df['support'] = df['support'].ffill()
    df['bb_mid_h1'] = df['bb_mid_h1'].ffill()
    df['bb_upper_h1'] = df['bb_upper_h1'].ffill()
    df['bb_lower_h1'] = df['bb_lower_h1'].ffill()
    df['macd_hist_h1'] = df['macd_hist_h1'].ffill()
    df['ma5_h1'] = df['ma5_h1'].ffill()
    df['ma10_h1'] = df['ma10_h1'].ffill()
    
    # รวมข้อมูล H4 เข้ากับ M15
    df['time_h4'] = df['time'].dt.floor('4h')
    df = pd.merge(df, df_h4_features, on='time_h4', how='left')
    df['trend_h4'] = df['trend_h4'].ffill()
    df['h4_diff_pct'] = df['h4_diff_pct'].ffill()

    # ==========================================
    # คำนวณ Technical Features (M15)
    # ==========================================
    df['return'] = df['close'].pct_change()
    df['ma_fast'] = df['close'].rolling(10).mean()
    df['ma_slow'] = df['close'].rolling(30).mean()
    df['trend'] = df['ma_fast'] / df['ma_slow']
    
    # Moving Average 5 & 10 (M15) สำหรับ Plan 4 (MA-Cross-Trend)
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    
    # RSI (Momentum)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    
    # ATR (Average True Range - Volatility) สำหรับทำ Dynamic SL
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
    
    # Smart Money / Liquidity Sweep Features สำหรับทองคำ (Wick Analysis)
    body_size = np.abs(df['close'] - df['open'])
    lower_wick = np.minimum(df['open'], df['close']) - df['low']
    upper_wick = df['high'] - np.maximum(df['open'], df['close'])
    df['lower_wick_ratio'] = lower_wick / (df['atr'] + 1e-9)
    df['upper_wick_ratio'] = upper_wick / (df['atr'] + 1e-9)
    df['body_ratio'] = body_size / (df['atr'] + 1e-9)
    
    # Session / Time Feature
    df['hour'] = df['time'].dt.hour
    # ตลาดลอนดอน และ นิวยอร์ก (ตามเวลาเซิร์ฟเวอร์ MT5 ประมาณ 08:00 - 22:00)
    df['is_liquid_session'] = ((df['hour'] >= 8) & (df['hour'] <= 22)).astype(int)
    
    # Target สำหรับสอน AI
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    
    # นำระยะห่างจากแนวรับแนวต้านให้ AI เรียนรู้ด้วย
    df['dist_to_res'] = df['resistance'] - df['close']
    df['dist_to_sup'] = df['close'] - df['support']
    
    # ตรวจจับ Divergence (Regular & Hidden)
    df = add_divergence_features(df, lookback=14)
    
    df.dropna(inplace=True)

    # เพิ่ม Feature ใหม่ให้ AI (trend_h1, atr, bb_width, แนวรับแนวต้าน, wick ratios, session, divergence)
    features = ['return', 'trend', 'rsi', 'trend_h1', 'trend_h4', 'atr', 'bb_width', 
                'dist_to_res', 'dist_to_sup', 'lower_wick_ratio', 'upper_wick_ratio', 'is_liquid_session',
                'bull_div', 'bear_div', 'hidden_bull', 'hidden_bear']

    # 2. แบ่งข้อมูล Train และ Test
    train_df = df.iloc[:TRAIN_BARS]
    test_df = df.iloc[TRAIN_BARS:].reset_index(drop=True)

    print(f"🧠 กำลังฝึก AI ด้วยข้อมูล {len(train_df)} แท่ง (ใช้ Features มืออาชีพ + SMC)...")
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(train_df[features], train_df['target'])

    print(f"⚡ กำลังประมวลผล AI Predictions ทั้งหมดล่วงหน้า (Vectorized)...")
    probs = model.predict_proba(test_df[features])

    print(f"📊 กำลังเริ่มจำลองการเทรดจริงบน {len(test_df)} แท่งย้อนหลัง...")

    # 3. จำลองการเทรดทีละแท่ง (Simulation)
    balance = 1000.0  # สมมติเงินทุนเริ่มต้น 1,000 USD
    initial_balance = balance
    trades = []
    current_trade = None

    lot_size = 0.01
    info = mt5.symbol_info(symbol)
    contract_size = info.trade_contract_size if info is not None else (100.0 if "XAU" in symbol else 1.0)
    digits = info.digits if info is not None else 2

    for i in range(len(test_df)):
        bar = test_df.iloc[i]

        # ถ้าถือออเดอร์อยู่ ให้เช็คว่าชน TP หรือ SL หรือยัง
        if current_trade is not None:
            pos_type = current_trade['type']
            entry_price = current_trade['entry_price']
            sl_price = current_trade['sl']
            tp_price = current_trade['tp']
            
            # ดึง prediction ของแท่งปัจจุบันเพื่อทำ Dynamic Exit
            prob = probs[i]
            
            # --- Dynamic Exit (AI Reversal) ---
            ai_reversal_exit = False
            if pos_type == 'BUY' and prob[0] >= 0.60 and bar['close'] < entry_price:
                ai_reversal_exit = True
            elif pos_type == 'SELL' and prob[1] >= 0.60 and bar['close'] > entry_price:
                ai_reversal_exit = True
                
            if ai_reversal_exit:
                exit_price = bar['close']
                if pos_type == 'BUY':
                    pnl = (exit_price - entry_price) * lot_size * contract_size
                else:
                    pnl = (entry_price - exit_price) * lot_size * contract_size
                
                balance += pnl
                res = 'WIN' if pnl > 0 else 'LOSS'
                trades.append({'result': res, 'pnl': pnl, 'balance': balance, 'reason': 'AI Reversal', 'plan': current_trade.get('plan')})
                current_trade = None
            # --- Plan 4 Exit Logic: ปิดไม้ทันทีเมื่อ MA5 ตัดกลับขั้วตรงข้าม (ไม่ต้องตั้ง TP) ---
            if current_trade.get('plan') == 'MA-Cross-Trend':
                ma5 = bar['ma5']
                ma10 = bar['ma10']
                prev_ma5 = test_df.iloc[i-1]['ma5'] if i > 0 else ma5
                prev_ma10 = test_df.iloc[i-1]['ma10'] if i > 0 else ma10
                ma_cross_up = (prev_ma5 <= prev_ma10) and (ma5 > ma10)
                ma_cross_down = (prev_ma5 >= prev_ma10) and (ma5 < ma10)

                # ตรวจ SL ป้องกันกระชากแรง (Safety Stop 0.75 ATR)
                eff_sl = sl_price
                if pos_type == 'BUY' and bar['low'] <= eff_sl:
                    pnl = (eff_sl - entry_price) * lot_size * contract_size
                    balance += pnl
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    trades.append({'result': res, 'pnl': pnl, 'balance': balance, 'reason': 'SL', 'plan': 'MA-Cross-Trend'})
                    current_trade = None
                    continue
                elif pos_type == 'SELL' and bar['high'] >= eff_sl:
                    pnl = (entry_price - eff_sl) * lot_size * contract_size
                    balance += pnl
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    trades.append({'result': res, 'pnl': pnl, 'balance': balance, 'reason': 'SL', 'plan': 'MA-Cross-Trend'})
                    current_trade = None
                    continue

                # เงื่อนไขหลัก: MA5 ตัดกลับขั้วตรงข้าม -> ปิดไม้ทันที
                if pos_type == 'BUY' and ma_cross_down:
                    exit_price = bar['close']
                    pnl = (exit_price - entry_price) * lot_size * contract_size
                    balance += pnl
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    trades.append({'result': res, 'pnl': pnl, 'balance': balance, 'reason': 'MA Cross Exit', 'plan': 'MA-Cross-Trend'})
                    current_trade = None
                    continue
                elif pos_type == 'SELL' and ma_cross_up:
                    exit_price = bar['close']
                    pnl = (entry_price - exit_price) * lot_size * contract_size
                    balance += pnl
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    trades.append({'result': res, 'pnl': pnl, 'balance': balance, 'reason': 'MA Cross Exit', 'plan': 'MA-Cross-Trend'})
                    current_trade = None
                    continue

            # --- Plan 5 Exit Logic: ปิดไม้ทันทีเมื่อ MA5 บน H1 ตัดกลับขั้วตรงข้าม (ไม่ต้องตั้ง TP) ---
            if current_trade.get('plan') == 'MA-Cross-H1-Trend':
                ma5_h1 = bar['ma5_h1']
                ma10_h1 = bar['ma10_h1']
                prev_ma5_h1 = test_df.iloc[i-1]['ma5_h1'] if i > 0 else ma5_h1
                prev_ma10_h1 = test_df.iloc[i-1]['ma10_h1'] if i > 0 else ma10_h1
                ma_cross_h1_up = (prev_ma5_h1 <= prev_ma10_h1) and (ma5_h1 > ma10_h1)
                ma_cross_h1_down = (prev_ma5_h1 >= prev_ma10_h1) and (ma5_h1 < ma10_h1)

                # ตรวจ SL ป้องกันกระชากแรง (Safety Stop 0.75 ATR)
                eff_sl = sl_price
                if pos_type == 'BUY' and bar['low'] <= eff_sl:
                    pnl = (eff_sl - entry_price) * lot_size * contract_size
                    balance += pnl
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    trades.append({'result': res, 'pnl': pnl, 'balance': balance, 'reason': 'SL', 'plan': 'MA-Cross-H1-Trend'})
                    current_trade = None
                    continue
                elif pos_type == 'SELL' and bar['high'] >= eff_sl:
                    pnl = (entry_price - eff_sl) * lot_size * contract_size
                    balance += pnl
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    trades.append({'result': res, 'pnl': pnl, 'balance': balance, 'reason': 'SL', 'plan': 'MA-Cross-H1-Trend'})
                    current_trade = None
                    continue

                # เงื่อนไขหลัก: MA5 บน H1 ตัดกลับขั้วตรงข้าม -> ปิดไม้ทันที
                if pos_type == 'BUY' and ma_cross_h1_down:
                    exit_price = bar['close']
                    pnl = (exit_price - entry_price) * lot_size * contract_size
                    balance += pnl
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    trades.append({'result': res, 'pnl': pnl, 'balance': balance, 'reason': 'H1 MA Cross Exit', 'plan': 'MA-Cross-H1-Trend'})
                    current_trade = None
                    continue
                elif pos_type == 'SELL' and ma_cross_h1_up:
                    exit_price = bar['close']
                    pnl = (entry_price - exit_price) * lot_size * contract_size
                    balance += pnl
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    trades.append({'result': res, 'pnl': pnl, 'balance': balance, 'reason': 'H1 MA Cross Exit', 'plan': 'MA-Cross-H1-Trend'})
                    current_trade = None
                    continue

            # --- Early Profit Lock (เมื่อราคาไปได้ 70% ของเป้า ขยับ SL มาล็อคกำไรที่ +0.35 ATR) ---
            atr_val = bar['atr']
            if pos_type == 'BUY':
                target_dist = tp_price - entry_price
                current_gain = bar['high'] - entry_price
                
                # ล็อคกำไรเมื่อกำไรเกิน 70% ของเป้า
                if current_gain >= (target_dist * 0.70):
                    be_sl = entry_price + (atr_val * 0.35)
                    if be_sl > current_trade.get('locked_sl', 0):
                        current_trade['locked_sl'] = be_sl

                # Unlimited Dynamic TP เมื่อราคาไปถึง 80% และ AI ยังมองขึ้นต่อเนื่อง
                if target_dist > 0 and current_gain >= (0.80 * target_dist) and prob[1] >= CONFIDENCE:
                    new_tp = tp_price + (atr_val * 1.0)
                    lock_sl = max(entry_price + (atr_val * 0.5), bar['close'] - (atr_val * 0.8))
                    if new_tp > tp_price:
                        current_trade['tp'] = new_tp
                        tp_price = new_tp
                        current_trade['extended'] = current_trade.get('extended', 0) + 1
                    if lock_sl > current_trade.get('locked_sl', 0):
                        current_trade['locked_sl'] = lock_sl

                # Check Exit on Bar
                eff_sl = current_trade.get('locked_sl', sl_price)
                hit_tp = bar['high'] >= tp_price
                hit_sl = bar['low'] <= eff_sl
                if hit_tp and hit_sl:
                    hit_exit = 'TP' if bar['close'] >= bar['open'] else 'SL'
                elif hit_tp:
                    hit_exit = 'TP'
                elif hit_sl:
                    hit_exit = 'SL'
                else:
                    hit_exit = None

                if hit_exit == 'TP':
                    profit_amount = (tp_price - entry_price) * lot_size * contract_size
                    balance += profit_amount
                    reason = 'TP (Extended)' if current_trade.get('extended') else 'TP'
                    trades.append({'result': 'WIN', 'pnl': profit_amount, 'balance': balance, 'reason': reason, 'plan': current_trade.get('plan')})
                    current_trade = None
                elif hit_exit == 'SL':
                    pnl = (eff_sl - entry_price) * lot_size * contract_size
                    balance += pnl
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    reason = 'Trailing SL (Lock Profit)' if pnl > 0 else 'SL'
                    trades.append({'result': res, 'pnl': pnl, 'balance': balance, 'reason': reason, 'plan': current_trade.get('plan')})
                    current_trade = None

            elif pos_type == 'SELL':
                target_dist = entry_price - tp_price
                current_gain = entry_price - bar['low']
                
                # ล็อคกำไรเมื่อกำไรเกิน 70% ของเป้า
                if current_gain >= (target_dist * 0.70):
                    be_sl = entry_price - (atr_val * 0.35)
                    if current_trade.get('locked_sl') is None or be_sl < current_trade['locked_sl']:
                        current_trade['locked_sl'] = be_sl

                # Unlimited Dynamic TP เมื่อราคาลงมาถึง 80% และ AI ยังมองลงต่อเนื่อง
                if target_dist > 0 and current_gain >= (0.80 * target_dist) and prob[0] >= CONFIDENCE:
                    new_tp = tp_price - (atr_val * 1.0)
                    lock_sl = min(entry_price - (atr_val * 0.5), bar['close'] + (atr_val * 0.8))
                    if new_tp < tp_price:
                        current_trade['tp'] = new_tp
                        tp_price = new_tp
                        current_trade['extended'] = current_trade.get('extended', 0) + 1
                    if current_trade.get('locked_sl') is None or lock_sl < current_trade['locked_sl']:
                        current_trade['locked_sl'] = lock_sl

                # Check Exit on Bar
                eff_sl = current_trade.get('locked_sl', sl_price)
                hit_tp = bar['low'] <= tp_price
                hit_sl = bar['high'] >= eff_sl
                if hit_tp and hit_sl:
                    hit_exit = 'TP' if bar['close'] <= bar['open'] else 'SL'
                elif hit_tp:
                    hit_exit = 'TP'
                elif hit_sl:
                    hit_exit = 'SL'
                else:
                    hit_exit = None

                if hit_exit == 'TP':
                    profit_amount = (entry_price - tp_price) * lot_size * contract_size
                    balance += profit_amount
                    reason = 'TP (Extended)' if current_trade.get('extended') else 'TP'
                    trades.append({'result': 'WIN', 'pnl': profit_amount, 'balance': balance, 'reason': reason, 'plan': current_trade.get('plan')})
                    current_trade = None
                elif hit_exit == 'SL':
                    pnl = (entry_price - eff_sl) * lot_size * contract_size
                    balance += pnl
                    res = 'WIN' if pnl > 0 else 'LOSS'
                    reason = 'Trailing SL (Lock Profit)' if pnl > 0 else 'SL'
                    trades.append({'result': res, 'pnl': pnl, 'balance': balance, 'reason': reason, 'plan': current_trade.get('plan')})
                    current_trade = None

        # ถ้าไม่มีออเดอร์ค้างอยู่ ให้ AI ตัดสินใจเข้าไม้ใหม่
        if current_trade is None and i < len(test_df) - 1:
            if len(trades) >= 100:
                print("🎯 จำลองการเทรดครบ 100 ไม้แล้ว! กำลังสรุปผล...")
                break
                
            # ตัวกรองช่วงเวลาเทรด (Session Filter): ไม่เข้าเทรดช่วงตลาดปิดหรือสภาพคล่องต่ำ (สำหรับ BTC เทรดได้ 24/7)
            if "BTC" not in symbol and bar['is_liquid_session'] == 0:
                continue

            # กำหนด RRR เฉพาะตามสินทรัพย์ (ทองคำใช้ 2.5, BTC ใช้ 2.0)
            if "XAU" in symbol:
                symbol_rrr = TP_RRR_XAU
            elif "BTC" in symbol:
                symbol_rrr = TP_RRR_BTC
            else:
                symbol_rrr = TP_RRR_DEFAULT
                
            prob = probs[i]
            
            # การเข้าเทรดแบบ Smart Money Concepts & Multi-Timeframe
            support = bar['support']
            resistance = bar['resistance']
            atr_val = bar['atr']
            close_price = bar['close']
            lower_wick_ratio = bar['lower_wick_ratio']
            upper_wick_ratio = bar['upper_wick_ratio']
            
            # 1. เงื่อนไข Liquidity Sweep (กวาดสภาพคล่องแล้วดีดกลับ - แผนเด็ดของทองคำ)
            is_sweep_buy = (bar['low'] < support) and (close_price >= support) and (lower_wick_ratio >= 0.30)
            is_sweep_sell = (bar['high'] > resistance) and (close_price <= resistance) and (upper_wick_ratio >= 0.30)
            
            # 2. เงื่อนไข Bounce (ชนแนวรับ/ต้าน แล้วมีแท่งปฏิเสธราคา ไม่ใช่มีดตก)
            near_support = abs(close_price - support) <= (atr_val * 1.0) and (close_price >= support)
            near_resistance = abs(resistance - close_price) <= (atr_val * 1.0) and (close_price <= resistance)
            
            is_uptrend_h1 = bar['trend_h1'] > 1.0
            is_uptrend_h4 = bar['trend_h4'] > 1.0
            bull_div_active = bool(bar.get('bull_div', 0) > 0.5)
            bear_div_active = bool(bar.get('bear_div', 0) > 0.5)
            hidden_bull_active = bool(bar.get('hidden_bull', 0) > 0.5)
            hidden_bear_active = bool(bar.get('hidden_bear', 0) > 0.5)

            # Confluence rules ตามเวอร์ชัน v2026.1002.2225:
            h4_diff_pct = bar.get('h4_diff_pct', 0.0)
            is_sideway_h4 = abs(h4_diff_pct) < 0.20
            
            if is_sideway_h4:
                h4_buy_ok = True
                h4_sell_ok = True
            else:
                # Strict Pro-Trend: เทรดเฉพาะทิศเดียวกับเทรนด์ H4 เพื่อดัน Win Rate สู่ 45-50%
                h4_buy_ok = is_uptrend_h4
                h4_sell_ok = not is_uptrend_h4
            
            # 3. เงื่อนไข Bollinger Bands Mean-Reversion (Plan 3)
            bb_lower = bar['bb_lower']
            bb_upper = bar['bb_upper']
            has_div_bb_buy = bull_div_active or hidden_bull_active
            has_div_bb_sell = bear_div_active or hidden_bear_active

            if "BTC" in symbol:
                # BTC: ปิด Bounce (Plan 1) และปิด BB-Reversion (Plan 3) ตาม Asset Specialization
                bounce_buy_confirm = False
                bounce_sell_confirm = False
                bb_buy_confirm = False
                bb_sell_confirm = False
                bo_mult = 0.20
                breakout_buy = (close_price > resistance + (atr_val * bo_mult)) and (close_price <= resistance + (atr_val * 3.0)) and (upper_wick_ratio < 0.35)
                breakout_sell = (close_price < support - (atr_val * bo_mult)) and (close_price >= support - (atr_val * 3.0)) and (lower_wick_ratio < 0.35)
            else:
                # XAU: Bounce ต้องมี Divergence ยืนยัน, ปิด Breakout, เปิด Plan 3 (BB-MeanReversion)
                has_div_bounce_buy = bull_div_active or hidden_bull_active
                has_div_bounce_sell = bear_div_active or hidden_bear_active
                bounce_buy_confirm = near_support and has_div_bounce_buy and (lower_wick_ratio >= 0.20 or close_price > bar['open'])
                bounce_sell_confirm = near_resistance and has_div_bounce_sell and (upper_wick_ratio >= 0.20 or close_price < bar['open'])
                breakout_buy = False
                breakout_sell = False
                # XAUUSD: เปิด Plan 3 (BB-H1-Reversion) โฟกัสกรอบ H1 + ไส้เทียน + Divergence + MACD Exhaustion
                bb_lower_h1 = bar['bb_lower_h1']
                bb_upper_h1 = bar['bb_upper_h1']
                macd_hist_h1 = bar['macd_hist_h1']
                prev_macd_hist_h1 = test_df.iloc[i-1]['macd_hist_h1'] if i > 0 else macd_hist_h1

                macd_buy_exhaustion = macd_hist_h1 >= prev_macd_hist_h1
                macd_sell_exhaustion = macd_hist_h1 <= prev_macd_hist_h1

                bb_buy_confirm = (bar['low'] < bb_lower_h1) and (close_price >= bb_lower_h1) and (lower_wick_ratio >= 0.20) and has_div_bb_buy and macd_buy_exhaustion
                bb_sell_confirm = (bar['high'] > bb_upper_h1) and (close_price <= bb_upper_h1) and (upper_wick_ratio >= 0.20) and has_div_bb_sell and macd_sell_exhaustion

                # Plan 4: MA-Cross-Trend (Moving Average 5 x 10 บน M15 + กรองด้วยเทรนด์ H1)
                ma5 = bar['ma5']
                ma10 = bar['ma10']
                prev_ma5 = test_df.iloc[i-1]['ma5'] if i > 0 else ma5
                prev_ma10 = test_df.iloc[i-1]['ma10'] if i > 0 else ma10
                ma_cross_up = (prev_ma5 <= prev_ma10) and (ma5 > ma10)
                ma_cross_down = (prev_ma5 >= prev_ma10) and (ma5 < ma10)
                ma_cross_buy_confirm = ma_cross_up and is_uptrend_h1
                ma_cross_sell_confirm = ma_cross_down and (not is_uptrend_h1)

                # Plan 5: MA-Cross-H1-Trend (Moving Average 5 x 10 บน H1 + กรองด้วยเทรนด์ H4)
                ma5_h1 = bar['ma5_h1']
                ma10_h1 = bar['ma10_h1']
                prev_ma5_h1 = test_df.iloc[i-1]['ma5_h1'] if i > 0 else ma5_h1
                prev_ma10_h1 = test_df.iloc[i-1]['ma10_h1'] if i > 0 else ma10_h1
                ma_cross_h1_up = (prev_ma5_h1 <= prev_ma10_h1) and (ma5_h1 > ma10_h1)
                ma_cross_h1_down = (prev_ma5_h1 >= prev_ma10_h1) and (ma5_h1 < ma10_h1)
            
            req_bo_p = 0.58 if is_sideway_h4 else 0.54

            # SL ตายตัว = 0.75 ATR
            sl_dist = atr_val * SL_ATR_MULT

            # แผน 0: BUY Liquidity Sweep (SMC-LiquidityHunt) + บังคับ H1 Uptrend
            if is_sweep_buy and prob[1] >= (0.48 if bull_div_active else 0.50) and h4_buy_ok and is_uptrend_h1:
                entry_price = close_price + gap_buffer
                sl_price = entry_price - sl_dist - gap_buffer
                risk = entry_price - sl_price
                tp_price = entry_price + (risk * symbol_rrr) + gap_buffer
                current_trade = {'type': 'BUY', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'SMC-LiquidityHunt'}
                
            # แผน 0: SELL Liquidity Sweep (SMC-LiquidityHunt) + บังคับ H1 Downtrend
            elif is_sweep_sell and prob[0] >= (0.48 if bear_div_active else 0.50) and h4_sell_ok and (not is_uptrend_h1):
                entry_price = close_price - gap_buffer
                sl_price = entry_price + sl_dist + gap_buffer
                risk = sl_price - entry_price
                tp_price = entry_price - (risk * symbol_rrr) - gap_buffer
                current_trade = {'type': 'SELL', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'SMC-LiquidityHunt'}

            # แผน 1: BUY Bounce (SR-SwingBounce)
            elif prob[1] >= CONFIDENCE and bounce_buy_confirm and h4_buy_ok:  
                entry_price = close_price + gap_buffer 
                sl_price = entry_price - sl_dist - gap_buffer
                risk = entry_price - sl_price
                tp_price = entry_price + (risk * symbol_rrr) + gap_buffer
                current_trade = {'type': 'BUY', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'SR-SwingBounce'}

            # แผน 1: SELL Bounce (SR-SwingBounce)
            elif prob[0] >= CONFIDENCE and bounce_sell_confirm and h4_sell_ok:  
                entry_price = close_price - gap_buffer 
                sl_price = entry_price + sl_dist + gap_buffer
                risk = sl_price - entry_price
                tp_price = entry_price - (risk * symbol_rrr) - gap_buffer
                current_trade = {'type': 'SELL', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'SR-SwingBounce'}
                
            # แผน 2: BUY Breakout (Trend-Breakout)
            elif breakout_buy and prob[1] >= req_bo_p and h4_buy_ok:
                entry_price = close_price + gap_buffer
                sl_price = entry_price - sl_dist - gap_buffer
                risk = entry_price - sl_price
                tp_price = entry_price + (risk * symbol_rrr) + gap_buffer
                current_trade = {'type': 'BUY', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'Trend-Breakout'}
                
            # แผน 2: SELL Breakout (Trend-Breakout)
            elif breakout_sell and prob[0] >= req_bo_p and h4_sell_ok:
                entry_price = close_price - gap_buffer
                sl_price = entry_price + sl_dist + gap_buffer
                risk = sl_price - entry_price
                tp_price = entry_price - (risk * symbol_rrr) - gap_buffer
                current_trade = {'type': 'SELL', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'Trend-Breakout'}

            # แผน 3: BUY BB-H1-Reversion (Plan 3) - เปิดเฉพาะ XAUUSD
            elif bb_buy_confirm and prob[1] >= 0.50 and h4_buy_ok:
                entry_price = close_price + gap_buffer
                sl_price = entry_price - sl_dist - gap_buffer
                risk = entry_price - sl_price
                tp_price = entry_price + (risk * symbol_rrr) + gap_buffer
                current_trade = {'type': 'BUY', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'BB-H1-Reversion'}

            # แผน 3: SELL BB-H1-Reversion (Plan 3) - เปิดเฉพาะ XAUUSD
            elif bb_sell_confirm and prob[0] >= 0.50 and h4_sell_ok:
                entry_price = close_price - gap_buffer
                sl_price = entry_price + sl_dist + gap_buffer
                risk = sl_price - entry_price
                tp_price = entry_price - (risk * symbol_rrr) - gap_buffer
                current_trade = {'type': 'SELL', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'BB-H1-Reversion'}

            # แผน 4: BUY MA-Cross-Trend (MA 5 ตัดขึ้น MA 10 บน M15 + H1 Uptrend - ไม่ต้องตั้ง TP)
            elif ma_cross_buy_confirm and h4_buy_ok:
                entry_price = close_price + gap_buffer
                sl_price = entry_price - sl_dist - gap_buffer
                current_trade = {'type': 'BUY', 'entry_price': entry_price, 'sl': sl_price, 'tp': 999999.0, 'plan': 'MA-Cross-Trend'}

            # แผน 4: SELL MA-Cross-Trend (MA 5 ตัดลง MA 10 บน M15 + H1 Downtrend - ไม่ต้องตั้ง TP)
            elif ma_cross_sell_confirm and h4_sell_ok:
                entry_price = close_price - gap_buffer
                sl_price = entry_price + sl_dist + gap_buffer
                current_trade = {'type': 'SELL', 'entry_price': entry_price, 'sl': sl_price, 'tp': -999999.0, 'plan': 'MA-Cross-Trend'}

            # แผน 5: BUY MA-Cross-H1-Trend (MA 5 ตัดขึ้น MA 10 บน H1 + H4 Bullish - ไม่ต้องตั้ง TP)
            elif ma_cross_h1_up and h4_buy_ok:
                entry_price = close_price + gap_buffer
                sl_price = entry_price - sl_dist - gap_buffer
                current_trade = {'type': 'BUY', 'entry_price': entry_price, 'sl': sl_price, 'tp': 999999.0, 'plan': 'MA-Cross-H1-Trend'}

            # แผน 5: SELL MA-Cross-H1-Trend (MA 5 ตัดลง MA 10 บน H1 + H4 Bearish - ไม่ต้องตั้ง TP)
            elif ma_cross_h1_down and h4_sell_ok:
                entry_price = close_price - gap_buffer
                sl_price = entry_price + sl_dist + gap_buffer
                current_trade = {'type': 'SELL', 'entry_price': entry_price, 'sl': sl_price, 'tp': -999999.0, 'plan': 'MA-Cross-H1-Trend'}

    # 4. สรุปผลลัพธ์
    total_trades = len(trades)
    if total_trades == 0:
        print("⚠️ ไม่มีการเข้าออเดอร์เลย (อาจติดตัวกรองเทรนด์ H1 ทำให้เข้าเทรดยากขึ้น)")
        return

    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    win_rate = (len(wins) / total_trades) * 100
    total_profit = balance - initial_balance
    
    tp_count = len([t for t in trades if t['reason'] == 'TP'])
    tp_ext_count = len([t for t in trades if t['reason'] == 'TP (Extended)'])
    trail_count = len([t for t in trades if t['reason'] == 'Trailing SL (Lock Profit)'])
    sl_count = len([t for t in trades if t['reason'] == 'SL'])
    ai_count = len([t for t in trades if t['reason'] == 'AI Reversal'])
    ma_exit_count = len([t for t in trades if t['reason'] == 'MA Cross Exit'])
    ma_h1_exit_count = len([t for t in trades if t['reason'] == 'H1 MA Cross Exit'])

    print("\n" + "="*45)
    print("📈 สรุปผลการทดสอบย้อนหลัง (Backtest Report) - XAUUSD Gold Specialist")
    print("="*45)
    print(f"💰 เงินทุนเริ่มต้น:            ${initial_balance:,.2f}")
    print(f"💵 เงินทุนคงเหลือ:            ${balance:,.2f}")
    print(f"🎯 กำไร/ขาดทุนสุทธิ:          {'+' if total_profit >= 0 else ''}${total_profit:,.2f} ({(total_profit/initial_balance)*100:.2f}%)")
    plan_0_trades = [t for t in trades if t.get('plan') == 'SMC-LiquidityHunt']
    plan_0_wins = [t for t in plan_0_trades if t['result'] == 'WIN']
    plan_1_trades = [t for t in trades if t.get('plan') == 'SR-SwingBounce']
    plan_1_wins = [t for t in plan_1_trades if t['result'] == 'WIN']
    plan_2_trades = [t for t in trades if t.get('plan') == 'Trend-Breakout']
    plan_2_wins = [t for t in plan_2_trades if t['result'] == 'WIN']
    plan_3_trades = [t for t in trades if t.get('plan') in ['BB-H1-Reversion', 'BB-MeanReversion']]
    plan_3_wins = [t for t in plan_3_trades if t['result'] == 'WIN']
    plan_4_trades = [t for t in trades if t.get('plan') == 'MA-Cross-Trend']
    plan_4_wins = [t for t in plan_4_trades if t['result'] == 'WIN']
    plan_5_trades = [t for t in trades if t.get('plan') == 'MA-Cross-H1-Trend']
    plan_5_wins = [t for t in plan_5_trades if t['result'] == 'WIN']

    print(f"🔢 จำนวนออเดอร์ทั้งหมด:      {total_trades} ไม้")
    print(f"   🟢 ปิดด้วย TP ปกติ:             {tp_count} ไม้")
    print(f"   🚀 ปิดด้วย TP ขยายเพิ่ม (Extended): {tp_ext_count} ไม้")
    print(f"   🛡️ ปิดด้วย Trailing SL (ล็อคกำไร): {trail_count} ไม้")
    print(f"   🔄 ปิดด้วย MA Cross Exit (M15):   {ma_exit_count} ไม้")
    print(f"   🌊 ปิดด้วย H1 MA Cross Exit:      {ma_h1_exit_count} ไม้")
    print(f"   🔴 ปิดด้วย SL (ขาดทุน):          {sl_count} ไม้")
    print(f"   🤖 ปิดด้วย AI (Dynamic Exit):     {ai_count} ไม้")
    print(f"📊 สถิติตามแผน:")
    if len(plan_0_trades) > 0:
        print(f"   ⚡ Plan 0 (SMC-LiquidityHunt)   : {len(plan_0_trades)} ไม้ (Win: {len(plan_0_wins)}, WR: {len(plan_0_wins)/len(plan_0_trades)*100:.1f}%)")
    if len(plan_1_trades) > 0:
        print(f"   🎯 Plan 1 (SR-SwingBounce)      : {len(plan_1_trades)} ไม้ (Win: {len(plan_1_wins)}, WR: {len(plan_1_wins)/len(plan_1_trades)*100:.1f}%)")
    if len(plan_2_trades) > 0:
        print(f"   🚀 Plan 2 (Trend-Breakout)      : {len(plan_2_trades)} ไม้ (Win: {len(plan_2_wins)}, WR: {len(plan_2_wins)/len(plan_2_trades)*100:.1f}%)")
    if len(plan_3_trades) > 0:
        print(f"   🌊 Plan 3 (BB-H1-Reversion)     : {len(plan_3_trades)} ไม้ (Win: {len(plan_3_wins)}, WR: {len(plan_3_wins)/len(plan_3_trades)*100:.1f}%)")
    if len(plan_4_trades) > 0:
        print(f"   📈 Plan 4 (MA-Cross-Trend M15)  : {len(plan_4_trades)} ไม้ (Win: {len(plan_4_wins)}, WR: {len(plan_4_wins)/len(plan_4_trades)*100:.1f}%)")
    if len(plan_5_trades) > 0:
        print(f"   👑 Plan 5 (MA-Cross-H1-Trend H1): {len(plan_5_trades)} ไม้ (Win: {len(plan_5_wins)}, WR: {len(plan_5_wins)/len(plan_5_trades)*100:.1f}%)")
    print(f"✅ ชนะ (Win):                 {len(wins)} ไม้")
    print(f"❌ แพ้ (Loss):                {len(losses)} ไม้")
    print(f"🏆 Win Rate:                  {win_rate:.2f}%")
    print("="*45)

if __name__ == "__main__":
    if not mt5.initialize():
        print("❌ เชื่อมต่อ MT5 ไม่สำเร็จ กรุณาเปิด MT5 ทิ้งไว้")
        sys.exit(1)
        
    symbols_to_test = ["XAUUSD"]
    for sym in symbols_to_test:
        run_backtest(sym)
        
    mt5.shutdown()