import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import sys
import io
from sklearn.ensemble import RandomForestClassifier

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)

SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
TIMEFRAME_H1 = mt5.TIMEFRAME_H1
TIMEFRAME_H4 = mt5.TIMEFRAME_H4
TOTAL_BARS = 30000
TRAIN_BARS = 5000
TP_RRR_XAU = 1.50
CONFIDENCE = 0.54
SL_ATR_MULT = 0.75

def get_data(symbol, timeframe, n_bars):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_bars)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def add_divergence_features(df, lookback=14):
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

def prepare_data(symbol):
    if not mt5.initialize():
        print("❌ MT5 Init failed")
        return None, None, None, None, None

    mt5.symbol_select(symbol, True)
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"❌ Symbol {symbol} not found")
        return None, None, None, None, None
        
    spread_pts = info.spread
    point = info.point
    contract_size = info.trade_contract_size
    gap_buffer = spread_pts * point

    df_m15 = get_data(symbol, TIMEFRAME, TOTAL_BARS)
    df_h1 = get_data(symbol, TIMEFRAME_H1, (TOTAL_BARS // 4) + 100)
    df_h4 = get_data(symbol, TIMEFRAME_H4, (TOTAL_BARS // 16) + 100)

    if df_m15 is None or df_h1 is None or df_h4 is None:
        return None, None, None, None, None

    # H1
    df_h1['ma_fast_h1'] = df_h1['close'].rolling(10).mean()
    df_h1['ma_slow_h1'] = df_h1['close'].rolling(30).mean()
    df_h1['trend_h1'] = df_h1['ma_fast_h1'] / df_h1['ma_slow_h1']
    df_h1['resistance'] = df_h1['high'].shift(1).rolling(20).max()
    df_h1['support'] = df_h1['low'].shift(1).rolling(20).min()
    df_h1['bb_mid_h1'] = df_h1['close'].shift(1).rolling(20).mean()
    df_h1['bb_std_h1'] = df_h1['close'].shift(1).rolling(20).std()
    df_h1['bb_upper_h1'] = df_h1['bb_mid_h1'] + (2.0 * df_h1['bb_std_h1'])
    df_h1['bb_lower_h1'] = df_h1['bb_mid_h1'] - (2.0 * df_h1['bb_std_h1'])

    ema12_h1 = df_h1['close'].ewm(span=12, adjust=False).mean()
    ema26_h1 = df_h1['close'].ewm(span=26, adjust=False).mean()
    df_h1['macd_h1'] = ema12_h1 - ema26_h1
    df_h1['macd_sig_h1'] = df_h1['macd_h1'].ewm(span=9, adjust=False).mean()
    df_h1['macd_hist_h1'] = df_h1['macd_h1'] - df_h1['macd_sig_h1']
    df_h1['time_h1'] = df_h1['time'].dt.floor('h')
    df_h1_features = df_h1[['time_h1', 'trend_h1', 'resistance', 'support', 'bb_mid_h1', 'bb_upper_h1', 'bb_lower_h1', 'macd_hist_h1']].dropna()

    # H4
    df_h4['ma_fast_h4'] = df_h4['close'].rolling(10).mean()
    df_h4['ma_slow_h4'] = df_h4['close'].rolling(30).mean()
    df_h4['trend_h4'] = df_h4['ma_fast_h4'] / df_h4['ma_slow_h4']
    df_h4['h4_diff_pct'] = ((df_h4['ma_fast_h4'] / df_h4['ma_slow_h4']) - 1.0) * 100.0
    df_h4['time_h4'] = df_h4['time'].dt.floor('4h')
    df_h4_features = df_h4[['time_h4', 'trend_h4', 'h4_diff_pct']].dropna()

    # M15
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

    df['time_h4'] = df['time'].dt.floor('4h')
    df = pd.merge(df, df_h4_features, on='time_h4', how='left')
    df['trend_h4'] = df['trend_h4'].ffill()
    df['h4_diff_pct'] = df['h4_diff_pct'].ffill()

    df['return'] = df['close'].pct_change()
    df['ma_fast'] = df['close'].rolling(10).mean()
    df['ma_slow'] = df['close'].rolling(30).mean()
    df['trend'] = df['ma_fast'] / df['ma_slow']
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma50'] = df['close'].rolling(50).mean()

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    df['rsi'] = 100 - (100 / (1 + rs))

    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    body = (df['close'] - df['open']).abs()
    candle_range = df['high'] - df['low'] + 1e-9
    df['body_ratio'] = body / candle_range
    df['lower_wick'] = np.minimum(df['open'], df['close']) - df['low']
    df['upper_wick'] = df['high'] - np.maximum(df['open'], df['close'])
    df['lower_wick_ratio'] = df['lower_wick'] / (df['atr'] + 1e-9)
    df['upper_wick_ratio'] = df['upper_wick'] / (df['atr'] + 1e-9)

    hour = df['time'].dt.hour
    df['is_liquid_session'] = np.where((hour >= 13) & (hour <= 22), 1.0, 0.0)

    df = add_divergence_features(df)

    features = [
        'return', 'trend', 'rsi', 'atr',
        'lower_wick_ratio', 'upper_wick_ratio', 'body_ratio',
        'trend_h1', 'trend_h4', 'h4_diff_pct',
        'bull_div', 'bear_div', 'hidden_bull', 'hidden_bear',
        'ma5', 'ma10'
    ]
    df['target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0)
    df = df.dropna().reset_index(drop=True)

    train_df = df.iloc[:TRAIN_BARS]
    test_df = df.iloc[TRAIN_BARS:].reset_index(drop=True)

    X_train = train_df[features]
    y_train = train_df['target']

    clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    clf.fit(X_train, y_train)

    X_test = test_df[features]
    probs = clf.predict_proba(X_test)

    return test_df, probs, gap_buffer, contract_size, spread_pts

def run_simulation(test_df, probs, gap_buffer, contract_size, plan_mode=None, max_trades=100):
    initial_balance = 1000.0
    balance = initial_balance
    trades = []
    current_trade = None
    lot_size = 0.01

    n_bars = len(test_df)
    for i in range(1, n_bars - 1):
        if max_trades and len(trades) >= max_trades:
            break

        bar = test_df.iloc[i]

        # 1. จัดการไม้เปิด
        if current_trade is not None:
            close_price = bar['close']
            atr_val = bar['atr']
            entry_price = current_trade['entry_price']
            sl_price = current_trade['sl']
            tp_price = current_trade['tp']
            trade_type = current_trade['type']

            # AI Dynamic Exit
            prob_now = probs[i]
            if trade_type == 'BUY' and prob_now[0] >= 0.60 and close_price < entry_price:
                loss_amount = (entry_price - close_price) * lot_size * contract_size
                balance -= loss_amount
                trades.append({'result': 'LOSS', 'pnl': -loss_amount, 'balance': balance, 'reason': 'AI Reversal', 'plan': current_trade.get('plan')})
                current_trade = None
                continue
            elif trade_type == 'SELL' and prob_now[1] >= 0.60 and close_price > entry_price:
                loss_amount = (close_price - entry_price) * lot_size * contract_size
                balance -= loss_amount
                trades.append({'result': 'LOSS', 'pnl': -loss_amount, 'balance': balance, 'reason': 'AI Reversal', 'plan': current_trade.get('plan')})
                current_trade = None
                continue

            if trade_type == 'BUY':
                curr_profit = bar['high'] - entry_price
                target_dist = abs(tp_price - entry_price)
                if curr_profit >= (target_dist * 0.70):
                    lock_sl = entry_price + (0.35 * atr_val)
                    if lock_sl > current_trade.get('locked_sl', sl_price) and (close_price - lock_sl) >= (0.4 * atr_val):
                        current_trade['locked_sl'] = lock_sl

                if curr_profit >= (target_dist * 0.80) and prob_now[1] >= 0.54 and not current_trade.get('extended', False):
                    current_trade['tp'] = tp_price + (1.0 * atr_val)
                    current_trade['locked_sl'] = max(current_trade.get('locked_sl', sl_price), entry_price + (0.5 * atr_val))
                    current_trade['extended'] = True

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

            elif trade_type == 'SELL':
                curr_profit = entry_price - bar['low']
                target_dist = abs(entry_price - tp_price)
                if curr_profit >= (target_dist * 0.70):
                    lock_sl = entry_price - (0.35 * atr_val)
                    if lock_sl < current_trade.get('locked_sl', sl_price) and (lock_sl - close_price) >= (0.4 * atr_val):
                        current_trade['locked_sl'] = lock_sl

                if curr_profit >= (target_dist * 0.80) and prob_now[0] >= 0.54 and not current_trade.get('extended', False):
                    current_trade['tp'] = tp_price - (1.0 * atr_val)
                    current_trade['locked_sl'] = min(current_trade.get('locked_sl', sl_price), entry_price - (0.5 * atr_val))
                    current_trade['extended'] = True

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

        # 2. พิจารณาเปิดไม้ใหม่
        if current_trade is None and i < n_bars - 1:
            if bar['is_liquid_session'] == 0:
                continue

            symbol_rrr = TP_RRR_XAU
            prob = probs[i]
            support = bar['support']
            resistance = bar['resistance']
            atr_val = bar['atr']
            close_price = bar['close']
            lower_wick_ratio = bar['lower_wick_ratio']
            upper_wick_ratio = bar['upper_wick_ratio']

            is_uptrend_h1 = bar['trend_h1'] > 1.0
            is_uptrend_h4 = bar['trend_h4'] > 1.0
            bull_div_active = bool(bar.get('bull_div', 0) > 0.5)
            bear_div_active = bool(bar.get('bear_div', 0) > 0.5)
            hidden_bull_active = bool(bar.get('hidden_bull', 0) > 0.5)
            hidden_bear_active = bool(bar.get('hidden_bear', 0) > 0.5)

            h4_diff_pct = bar.get('h4_diff_pct', 0.0)
            is_sideway_h4 = abs(h4_diff_pct) < 0.20
            if is_sideway_h4:
                h4_buy_ok = True
                h4_sell_ok = True
            else:
                h4_buy_ok = is_uptrend_h4
                h4_sell_ok = not is_uptrend_h4

            sl_dist = atr_val * SL_ATR_MULT

            # Plan 0 Check
            is_sweep_buy = (bar['low'] < support) and (close_price >= support) and (lower_wick_ratio >= 0.30)
            is_sweep_sell = (bar['high'] > resistance) and (close_price <= resistance) and (upper_wick_ratio >= 0.30)

            # Plan 1 Check
            near_support = abs(close_price - support) <= (atr_val * 1.0) and (close_price >= support)
            near_resistance = abs(resistance - close_price) <= (atr_val * 1.0) and (close_price <= resistance)
            has_div_bounce_buy = bull_div_active or hidden_bull_active
            has_div_bounce_sell = bear_div_active or hidden_bear_active
            bounce_buy_confirm = near_support and has_div_bounce_buy and (lower_wick_ratio >= 0.20 or close_price > bar['open'])
            bounce_sell_confirm = near_resistance and has_div_bounce_sell and (upper_wick_ratio >= 0.20 or close_price < bar['open'])

            # Plan 3 Check
            bb_lower_h1 = bar['bb_lower_h1']
            bb_upper_h1 = bar['bb_upper_h1']
            macd_hist_h1 = bar['macd_hist_h1']
            prev_macd_hist_h1 = test_df.iloc[i-1]['macd_hist_h1'] if i > 0 else macd_hist_h1
            macd_buy_exhaustion = macd_hist_h1 >= prev_macd_hist_h1
            macd_sell_exhaustion = macd_hist_h1 <= prev_macd_hist_h1
            has_div_bb_buy = bull_div_active or hidden_bull_active
            has_div_bb_sell = bear_div_active or hidden_bear_active
            bb_buy_confirm = (bar['low'] < bb_lower_h1) and (close_price >= bb_lower_h1) and (lower_wick_ratio >= 0.20) and has_div_bb_buy and macd_buy_exhaustion
            bb_sell_confirm = (bar['high'] > bb_upper_h1) and (close_price <= bb_upper_h1) and (upper_wick_ratio >= 0.20) and has_div_bb_sell and macd_sell_exhaustion

            # Plan 4 Check
            ma5 = bar['ma5']
            ma10 = bar['ma10']
            prev_ma5 = test_df.iloc[i-1]['ma5'] if i > 0 else ma5
            prev_ma10 = test_df.iloc[i-1]['ma10'] if i > 0 else ma10
            ma_cross_up = (prev_ma5 <= prev_ma10) and (ma5 > ma10)
            ma_cross_down = (prev_ma5 >= prev_ma10) and (ma5 < ma10)
            ma_cross_buy_confirm = ma_cross_up and is_uptrend_h1
            ma_cross_sell_confirm = ma_cross_down and (not is_uptrend_h1)

            # Match criteria by plan_mode
            # --- Plan 0 ---
            if plan_mode in [None, 'Plan 0']:
                if is_sweep_buy and prob[1] >= (0.48 if bull_div_active else 0.50) and h4_buy_ok and is_uptrend_h1:
                    entry_price = close_price + gap_buffer
                    sl_price = entry_price - sl_dist - gap_buffer
                    risk = entry_price - sl_price
                    tp_price = entry_price + (risk * symbol_rrr) + gap_buffer
                    current_trade = {'type': 'BUY', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'SMC-LiquidityHunt'}
                    continue
                elif is_sweep_sell and prob[0] >= (0.48 if bear_div_active else 0.50) and h4_sell_ok and (not is_uptrend_h1):
                    entry_price = close_price - gap_buffer
                    sl_price = entry_price + sl_dist + gap_buffer
                    risk = sl_price - entry_price
                    tp_price = entry_price - (risk * symbol_rrr) - gap_buffer
                    current_trade = {'type': 'SELL', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'SMC-LiquidityHunt'}
                    continue

            # --- Plan 1 ---
            if plan_mode in [None, 'Plan 1']:
                if prob[1] >= CONFIDENCE and bounce_buy_confirm and h4_buy_ok:
                    entry_price = close_price + gap_buffer
                    sl_price = entry_price - sl_dist - gap_buffer
                    risk = entry_price - sl_price
                    tp_price = entry_price + (risk * symbol_rrr) + gap_buffer
                    current_trade = {'type': 'BUY', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'SR-SwingBounce'}
                    continue
                elif prob[0] >= CONFIDENCE and bounce_sell_confirm and h4_sell_ok:
                    entry_price = close_price - gap_buffer
                    sl_price = entry_price + sl_dist + gap_buffer
                    risk = sl_price - entry_price
                    tp_price = entry_price - (risk * symbol_rrr) - gap_buffer
                    current_trade = {'type': 'SELL', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'SR-SwingBounce'}
                    continue

            # --- Plan 3 ---
            if plan_mode in [None, 'Plan 3']:
                if bb_buy_confirm and prob[1] >= 0.50 and h4_buy_ok:
                    entry_price = close_price + gap_buffer
                    sl_price = entry_price - sl_dist - gap_buffer
                    risk = entry_price - sl_price
                    tp_price = entry_price + (risk * symbol_rrr) + gap_buffer
                    current_trade = {'type': 'BUY', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'BB-H1-Reversion'}
                    continue
                elif bb_sell_confirm and prob[0] >= 0.50 and h4_sell_ok:
                    entry_price = close_price - gap_buffer
                    sl_price = entry_price + sl_dist + gap_buffer
                    risk = sl_price - entry_price
                    tp_price = entry_price - (risk * symbol_rrr) - gap_buffer
                    current_trade = {'type': 'SELL', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'BB-H1-Reversion'}
                    continue

            # --- Plan 4 ---
            if plan_mode in [None, 'Plan 4']:
                if ma_cross_buy_confirm and h4_buy_ok:
                    entry_price = close_price + gap_buffer
                    sl_price = entry_price - sl_dist - gap_buffer
                    risk = entry_price - sl_price
                    tp_price = entry_price + (risk * symbol_rrr) + gap_buffer
                    current_trade = {'type': 'BUY', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'MA-Cross-Trend'}
                    continue
                elif ma_cross_sell_confirm and h4_sell_ok:
                    entry_price = close_price - gap_buffer
                    sl_price = entry_price + sl_dist + gap_buffer
                    risk = sl_price - entry_price
                    tp_price = entry_price - (risk * symbol_rrr) - gap_buffer
                    current_trade = {'type': 'SELL', 'entry_price': entry_price, 'sl': sl_price, 'tp': tp_price, 'plan': 'MA-Cross-Trend'}
                    continue

    total_trades = len(trades)
    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
    net_profit = balance - initial_balance

    gross_win = sum(t['pnl'] for t in wins) if wins else 0.0
    gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 0 else (99.9 if gross_win > 0 else 0.0)

    equity_curve = [initial_balance]
    curr = initial_balance
    for t in trades:
        curr += t['pnl']
        equity_curve.append(curr)

    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

    max_dd_pct = (max_dd / peak) * 100.0 if peak > 0 else 0.0

    return {
        'total': total_trades,
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': win_rate,
        'net_profit': net_profit,
        'gross_win': gross_win,
        'gross_loss': gross_loss,
        'pf': pf,
        'max_dd': max_dd,
        'max_dd_pct': max_dd_pct,
        'tp_count': len([t for t in trades if t['reason'] in ['TP', 'TP (Extended)']]),
        'trail_count': len([t for t in trades if t['reason'] == 'Trailing SL (Lock Profit)']),
        'sl_count': len([t for t in trades if t['reason'] == 'SL']),
        'ai_count': len([t for t in trades if t['reason'] == 'AI Reversal']),
        'trades': trades
    }

def main():
    test_df, probs, gap_buffer, contract_size, spread_pts = prepare_data(SYMBOL)
    if test_df is None:
        return

    print("=" * 80)
    print(f"🚀 รายงานผลการทดสอบ Backtest แยกตามแผนการเทรด (Engine v2026.1002.2331)")
    print(f"สินทรัพย์: {SYMBOL} | สเปรด: {spread_pts} pts | RRR: 1:{TP_RRR_XAU} | SL: {SL_ATR_MULT} ATR")
    print(f"จำนวนแท่งเทียนที่นำมาทดสอบ: {len(test_df)} แท่ง M15")
    print("=" * 80)

    # 1. รันแบบแยกเดี่ยวอิสระ (Single-Plan Isolated Mode) จนครบข้อมูล
    print("\n[PART 1: การทดสอบแบบแยกเดี่ยวอิสระ (Isolated Pure Backtest) บนประวัติทั้งหมด]")
    print("แต่ละแผนทำงานเดี่ยวๆ โดยไม่ถูกแผนอื่นแย่งเปิดไม้ เพื่อดูศักยภาพที่แท้จริงของแต่ละระบบ:")
    print("-" * 80)

    plans = [
        ('Plan 0', '⚡ Plan 0: SMC-LiquidityHunt (กวาดสภาพคล่อง H1 + เทรนด์ H1)'),
        ('Plan 1', '🎯 Plan 1: SR-SwingBounce (เด้งแนวรับต้าน H1 + Divergence)'),
        ('Plan 3', '🌊 Plan 3: BB-H1-Reversion (เด้ง Bollinger Bands H1 2STD + MACD)'),
        ('Plan 4', '📈 Plan 4: MA-Cross-Trend (MA 5 x 10 Crossover M15 + เทรนด์ H1)')
    ]

    isolated_results = {}
    for p_code, p_desc in plans:
        # รันเต็มประวัติ ไม่จำกัด 100 ไม้ เพื่อดูสถิติที่แท้จริง
        res = run_simulation(test_df, probs, gap_buffer, contract_size, plan_mode=p_code, max_trades=None)
        isolated_results[p_code] = {'desc': p_desc, 'res': res}
        print(f"✓ {p_desc} เสร็จสิ้น: {res['total']} ไม้ | Win Rate: {res['win_rate']:.1f}% | Net: ${res['net_profit']:+,.2f} | PF: {res['pf']:.2f}")

    # ตาราง Part 1
    print("\n" + "=" * 90)
    print("🏆 ตารางสรุปศักยภาพรายแผน (Pure Isolated Plan Performance - ทั้งหมดในประวัติ)")
    print("=" * 90)
    header = f"{'แผนการเทรด':<38} | {'Trades':<7} | {'Win Rate':<9} | {'Net P/L ($)':<12} | {'PF':<5} | {'Max DD ($)':<11}"
    print(header)
    print("-" * 90)
    for p_code, item in isolated_results.items():
        r = item['res']
        wr_str = f"{r['win_rate']:.1f}%"
        pnl_str = f"${r['net_profit']:+,.2f}"
        pf_str = f"{r['pf']:.2f}"
        dd_str = f"${r['max_dd']:.1f} ({r['max_dd_pct']:.1f}%)"
        print(f"{item['desc']:<38} | {r['total']:<7} | {wr_str:<9} | {pnl_str:<12} | {pf_str:<5} | {dd_str:<11}")
    print("=" * 90)

    # 2. รันแบบ Multi-Plan Co-existing (100 ไม้ล่าสุดในบอทจริง)
    print("\n\n[PART 2: การทดสอบร่วมกันในระบบบอทจริง (Multi-Plan Co-existing - 100 ไม้ล่าสุด)]")
    print("ทุกแผนทำงานพร้อมกันในพอร์ตเดียวเพื่อกระจายความเสี่ยง:")
    print("-" * 80)
    combined_res = run_simulation(test_df, probs, gap_buffer, contract_size, plan_mode=None, max_trades=100)
    
    # เจาะลึกไม้ใน 100 ไม้ล่าสุด
    plan_trades = {}
    for t in combined_res['trades']:
        p = t.get('plan', 'Unknown')
        if p not in plan_trades:
            plan_trades[p] = {'wins': 0, 'losses': 0, 'pnl': 0.0}
        if t['result'] == 'WIN':
            plan_trades[p]['wins'] += 1
        else:
            plan_trades[p]['losses'] += 1
        plan_trades[p]['pnl'] += t['pnl']

    print(f"\n📊 ผลรวมระบบ 100 ไม้ล่าสุด: Win Rate = {combined_res['win_rate']:.2f}% (ชนะ {combined_res['wins']} / แพ้ {combined_res['losses']})")
    print(f"💰 กำไรสุทธิ: ${combined_res['net_profit']:+,.2f} | Profit Factor: {combined_res['pf']:.2f} | Max Drawdown: ${combined_res['max_dd']:.1f} ({combined_res['max_dd_pct']:.1f}%)")
    print("\nสัดส่วนและประสิทธิภาพในระบบรวม (100 ไม้ล่าสุด):")
    for p_name, stat in plan_trades.items():
        total_p = stat['wins'] + stat['losses']
        wr_p = (stat['wins'] / total_p * 100.0) if total_p > 0 else 0.0
        print(f"   • {p_name:<22}: {total_p:>2} ไม้ ({total_p/combined_res['total']*100:>4.1f}%) | Win: {stat['wins']:>2} | Loss: {stat['losses']:>2} | WR: {wr_p:>5.1f}% | P/L: ${stat['pnl']:+,.2f}")

    # สรุปรูปแบบการปิดออเดอร์ในระบบรวม
    print("\n🔍 สรุปรูปแบบการปิดออเดอร์ในระบบรวม 100 ไม้:")
    print(f"   🟢 ชน Take Profit ปกติ/ขยาย : {combined_res['tp_count']} ไม้ ({combined_res['tp_count']/combined_res['total']*100:.1f}%)")
    print(f"   🛡️ ล็อกกำไร Trailing SL (+0.35 ATR): {combined_res['trail_count']} ไม้ ({combined_res['trail_count']/combined_res['total']*100:.1f}%)")
    print(f"   🔴 ชน Stop Loss (SL 0.75 ATR)    : {combined_res['sl_count']} ไม้ ({combined_res['sl_count']/combined_res['total']*100:.1f}%)")
    print(f"   🤖 ปิดฉุกเฉินด้วย AI Reversal     : {combined_res['ai_count']} ไม้ ({combined_res['ai_count']/combined_res['total']*100:.1f}%)")

    mt5.shutdown()

if __name__ == '__main__':
    main()
