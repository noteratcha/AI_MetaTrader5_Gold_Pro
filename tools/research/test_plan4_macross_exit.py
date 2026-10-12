import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)

SYMBOL = "XAUUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
TIMEFRAME_H1 = mt5.TIMEFRAME_H1
TIMEFRAME_H4 = mt5.TIMEFRAME_H4
TOTAL_BARS = 30000

def get_data(symbol, timeframe, n_bars):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_bars)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def run():
    if not mt5.initialize():
        return
    mt5.symbol_select(SYMBOL, True)
    sym_info = mt5.symbol_info(SYMBOL)
    spread_pts = sym_info.spread
    point = sym_info.point
    contract_size = sym_info.trade_contract_size
    gap_buffer = spread_pts * point

    df = get_data(SYMBOL, TIMEFRAME, TOTAL_BARS)
    df_h1 = get_data(SYMBOL, TIMEFRAME_H1, (TOTAL_BARS // 4) + 100)
    df_h4 = get_data(SYMBOL, TIMEFRAME_H4, (TOTAL_BARS // 16) + 100)

    # H1 Trend
    df_h1['ma_fast_h1'] = df_h1['close'].rolling(10).mean()
    df_h1['ma_slow_h1'] = df_h1['close'].rolling(30).mean()
    df_h1['trend_h1'] = df_h1['ma_fast_h1'] / df_h1['ma_slow_h1']
    df_h1['time_h1'] = df_h1['time'].dt.floor('h')
    df_h1_features = df_h1[['time_h1', 'trend_h1']].dropna()

    # H4 Trend
    df_h4['ma_fast_h4'] = df_h4['close'].rolling(10).mean()
    df_h4['ma_slow_h4'] = df_h4['close'].rolling(30).mean()
    df_h4['h4_diff_pct'] = ((df_h4['ma_fast_h4'] / df_h4['ma_slow_h4']) - 1.0) * 100.0
    df_h4['time_h4'] = df_h4['time'].dt.floor('4h')
    df_h4_features = df_h4[['time_h4', 'h4_diff_pct', 'ma_fast_h4', 'ma_slow_h4']].dropna()

    # Merge
    df['time_h1'] = df['time'].dt.floor('h')
    df['time_h4'] = df['time'].dt.floor('4h')
    df = pd.merge(df, df_h1_features, on='time_h1', how='left')
    df['trend_h1'] = df['trend_h1'].ffill()
    df = pd.merge(df, df_h4_features, on='time_h4', how='left')
    df['h4_diff_pct'] = df['h4_diff_pct'].ffill()
    df['ma_fast_h4'] = df['ma_fast_h4'].ffill()
    df['ma_slow_h4'] = df['ma_slow_h4'].ffill()

    # M15
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()

    hour = df['time'].dt.hour
    df['is_liquid_session'] = np.where((hour >= 13) & (hour <= 22), 1.0, 0.0)

    df = df.dropna().reset_index(drop=True)

    print(f"Loaded {len(df)} bars. Testing Plan 4 (No TP, Opposite MA Cross Exit)...")

    # Simulation with different SL settings (0.75 ATR vs 1.0 ATR vs No SL)
    for sl_setting in [0.75, 1.0, 1.5, 999.0]:
        balance = 1000.0
        trades = []
        current_trade = None
        lot_size = 0.01

        for i in range(1, len(df)):
            bar = df.iloc[i]
            prev_bar = df.iloc[i-1]

            ma5 = bar['ma5']
            ma10 = bar['ma10']
            prev_ma5 = prev_bar['ma5']
            prev_ma10 = prev_bar['ma10']

            ma_cross_up = (prev_ma5 <= prev_ma10) and (ma5 > ma10)
            ma_cross_down = (prev_ma5 >= prev_ma10) and (ma5 < ma10)

            # Manage open trade
            if current_trade is not None:
                entry_p = current_trade['entry_price']
                trade_type = current_trade['type']
                sl_p = current_trade['sl']

                # Check SL
                hit_sl = False
                if sl_setting < 100:
                    if trade_type == 'BUY' and bar['low'] <= sl_p:
                        hit_sl = True
                        exit_p = sl_p
                    elif trade_type == 'SELL' and bar['high'] >= sl_p:
                        hit_sl = True
                        exit_p = sl_p

                if hit_sl:
                    pnl = (exit_p - entry_p if trade_type == 'BUY' else entry_p - exit_p) * lot_size * contract_size
                    balance += pnl
                    trades.append({'result': 'WIN' if pnl > 0 else 'LOSS', 'pnl': pnl, 'reason': 'SL'})
                    current_trade = None
                else:
                    # Check Opposite MA Cross Exit (เงื่อนไขใหม่!)
                    exit_signal = False
                    if trade_type == 'BUY' and ma_cross_down:
                        exit_signal = True
                        exit_p = bar['close']
                    elif trade_type == 'SELL' and ma_cross_up:
                        exit_signal = True
                        exit_p = bar['close']

                    if exit_signal:
                        pnl = (exit_p - entry_p if trade_type == 'BUY' else entry_p - exit_p) * lot_size * contract_size
                        balance += pnl
                        trades.append({'result': 'WIN' if pnl > 0 else 'LOSS', 'pnl': pnl, 'reason': 'MA_CROSS_EXIT'})
                        current_trade = None

            # Open trade if flat
            if current_trade is None and i < len(df) - 1:
                if bar['is_liquid_session'] == 0:
                    continue

                is_uptrend_h1 = bar['trend_h1'] > 1.0
                is_uptrend_h4 = bar['ma_fast_h4'] > bar['ma_slow_h4']
                is_sideway_h4 = abs(bar['h4_diff_pct']) < 0.20

                if is_sideway_h4:
                    h4_buy_ok = True
                    h4_sell_ok = True
                else:
                    h4_buy_ok = is_uptrend_h4
                    h4_sell_ok = not is_uptrend_h4

                atr_val = bar['atr']
                close_p = bar['close']

                if ma_cross_up and is_uptrend_h1 and h4_buy_ok:
                    entry_p = close_p + gap_buffer
                    sl_p = entry_p - (atr_val * sl_setting) - gap_buffer if sl_setting < 100 else 0.0
                    current_trade = {'type': 'BUY', 'entry_price': entry_p, 'sl': sl_p}
                elif ma_cross_down and (not is_uptrend_h1) and h4_sell_ok:
                    entry_p = close_p - gap_buffer
                    sl_p = entry_p + (atr_val * sl_setting) + gap_buffer if sl_setting < 100 else 999999.0
                    current_trade = {'type': 'SELL', 'entry_price': entry_p, 'sl': sl_p}

        wins = [t for t in trades if t['result'] == 'WIN']
        wr = (len(wins) / len(trades) * 100.0) if trades else 0.0
        net = balance - 1000.0
        gross_w = sum(t['pnl'] for t in wins)
        gross_l = abs(sum(t['pnl'] for t in trades if t['result'] == 'LOSS'))
        pf = gross_w / gross_l if gross_l > 0 else 0
        sl_hits = len([t for t in trades if t['reason'] == 'SL'])
        ma_exits = len([t for t in trades if t['reason'] == 'MA_CROSS_EXIT'])
        ma_wins = len([t for t in trades if t['reason'] == 'MA_CROSS_EXIT' and t['result'] == 'WIN'])

        print(f"SL Setting: {sl_setting:4.2f} ATR | Trades: {len(trades):3d} | Win Rate: {wr:5.1f}% | Net: ${net:+8.2f} | PF: {pf:4.2f} | MA Exits: {ma_exits} (Win: {ma_wins}) | SL Hits: {sl_hits}")

    mt5.shutdown()

if __name__ == '__main__':
    run()
