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

def run_comparison():
    if not mt5.initialize():
        print("MT5 Init Failed")
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

    # H1
    df_h1['ma_fast_h1'] = df_h1['close'].rolling(10).mean()
    df_h1['ma_slow_h1'] = df_h1['close'].rolling(30).mean()
    df_h1['trend_h1'] = df_h1['ma_fast_h1'] / df_h1['ma_slow_h1']
    df_h1['time_h1'] = df_h1['time'].dt.floor('h')
    df_h1_features = df_h1[['time_h1', 'trend_h1']].dropna()

    # H4
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

    sl_levels = [0.75, 1.00, 1.50]

    # --- ส่วนที่ 1: Plan 4 Isolated (เต็มประวัติ 507 ไม้) ---
    print("=" * 85)
    print("📊 ผลการเปรียบเทียบ Plan 4 (MA-Cross-Trend) แบบเฉพาะเจาะจง (ประวัติทั้งหมด)")
    print(f"สเปรดจำลอง: {spread_pts} pts | จำนวนแท่งเทียน: {len(df)} แท่ง M15")
    print("=" * 85)

    plan4_results = []
    for sl_mult in sl_levels:
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

            if current_trade is not None:
                entry_p = current_trade['entry_price']
                trade_type = current_trade['type']
                sl_p = current_trade['sl']

                hit_sl = False
                if trade_type == 'BUY' and bar['low'] <= sl_p:
                    hit_sl = True
                    exit_p = sl_p
                elif trade_type == 'SELL' and bar['high'] >= sl_p:
                    hit_sl = True
                    exit_p = sl_p

                if hit_sl:
                    pnl = (exit_p - entry_p if trade_type == 'BUY' else entry_p - exit_p) * lot_size * contract_size
                    balance += pnl
                    trades.append({'result': 'LOSS', 'pnl': pnl, 'reason': 'SL'})
                    current_trade = None
                else:
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
                        trades.append({'result': 'WIN' if pnl > 0 else 'LOSS', 'pnl': pnl, 'reason': 'MA_CROSS'})
                        current_trade = None

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
                    sl_p = entry_p - (atr_val * sl_mult) - gap_buffer
                    current_trade = {'type': 'BUY', 'entry_price': entry_p, 'sl': sl_p}
                elif ma_cross_down and (not is_uptrend_h1) and h4_sell_ok:
                    entry_p = close_p - gap_buffer
                    sl_p = entry_p + (atr_val * sl_mult) + gap_buffer
                    current_trade = {'type': 'SELL', 'entry_price': entry_p, 'sl': sl_p}

        total_trades = len(trades)
        wins = [t for t in trades if t['result'] == 'WIN']
        losses = [t for t in trades if t['result'] == 'LOSS']
        sl_hits = len([t for t in trades if t['reason'] == 'SL'])
        ma_exits = len([t for t in trades if t['reason'] == 'MA_CROSS'])
        ma_wins = len([t for t in trades if t['reason'] == 'MA_CROSS' and t['result'] == 'WIN'])
        ma_losses = ma_exits - ma_wins
        win_rate = (len(wins) / total_trades * 100.0) if total_trades else 0.0
        net_profit = balance - 1000.0
        gross_win = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        pf = gross_win / gross_loss if gross_loss > 0 else 0
        avg_win = (gross_win / len(wins)) if wins else 0
        avg_loss = (gross_loss / len(losses)) if losses else 0

        # Calculate Max Drawdown
        equity = 1000.0
        peak = 1000.0
        max_dd = 0.0
        for t in trades:
            equity += t['pnl']
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd

        plan4_results.append({
            'sl_mult': sl_mult,
            'total': total_trades,
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'sl_hits': sl_hits,
            'sl_pct': (sl_hits / total_trades * 100.0),
            'ma_wins': ma_wins,
            'ma_losses': ma_losses,
            'net_profit': net_profit,
            'pf': pf,
            'max_dd': max_dd,
            'avg_win': avg_win,
            'avg_loss': avg_loss
        })

    # --- ส่วนที่ 2: Plan 4 ใน 100 ไม้ล่าสุด ---
    recent_results = []
    for sl_mult in sl_levels:
        balance = 1000.0
        trades = []
        current_trade = None
        lot_size = 0.01

        for i in range(1, len(df)):
            if len(trades) >= 100:
                break
            bar = df.iloc[i]
            prev_bar = df.iloc[i-1]
            ma5 = bar['ma5']
            ma10 = bar['ma10']
            prev_ma5 = prev_bar['ma5']
            prev_ma10 = prev_bar['ma10']
            ma_cross_up = (prev_ma5 <= prev_ma10) and (ma5 > ma10)
            ma_cross_down = (prev_ma5 >= prev_ma10) and (ma5 < ma10)

            if current_trade is not None:
                entry_p = current_trade['entry_price']
                trade_type = current_trade['type']
                sl_p = current_trade['sl']

                hit_sl = False
                if trade_type == 'BUY' and bar['low'] <= sl_p:
                    hit_sl = True
                    exit_p = sl_p
                elif trade_type == 'SELL' and bar['high'] >= sl_p:
                    hit_sl = True
                    exit_p = sl_p

                if hit_sl:
                    pnl = (exit_p - entry_p if trade_type == 'BUY' else entry_p - exit_p) * lot_size * contract_size
                    balance += pnl
                    trades.append({'result': 'LOSS', 'pnl': pnl, 'reason': 'SL'})
                    current_trade = None
                else:
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
                        trades.append({'result': 'WIN' if pnl > 0 else 'LOSS', 'pnl': pnl, 'reason': 'MA_CROSS'})
                        current_trade = None

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
                    sl_p = entry_p - (atr_val * sl_mult) - gap_buffer
                    current_trade = {'type': 'BUY', 'entry_price': entry_p, 'sl': sl_p}
                elif ma_cross_down and (not is_uptrend_h1) and h4_sell_ok:
                    entry_p = close_p - gap_buffer
                    sl_p = entry_p + (atr_val * sl_mult) + gap_buffer
                    current_trade = {'type': 'SELL', 'entry_price': entry_p, 'sl': sl_p}

        total_trades = len(trades)
        wins = [t for t in trades if t['result'] == 'WIN']
        losses = [t for t in trades if t['result'] == 'LOSS']
        sl_hits = len([t for t in trades if t['reason'] == 'SL'])
        win_rate = (len(wins) / total_trades * 100.0) if total_trades else 0.0
        net_profit = balance - 1000.0

        recent_results.append({
            'sl_mult': sl_mult,
            'total': total_trades,
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'sl_hits': sl_hits,
            'sl_pct': (sl_hits / total_trades * 100.0),
            'net_profit': net_profit
        })

    print("\n[มิติที่ 1: สถิติ Plan 4 ประวัติเต็ม 507 ไม้]")
    print(f"{'SL Setting':<12} | {'ชน SL (ไม้)':<13} | {'Win Rate':<10} | {'กำไรสุทธิ ($)':<14} | {'PF':<5} | {'Max DD ($)':<12} | {'Avg Win / Loss':<15}")
    print("-" * 95)
    for r in plan4_results:
        sl_str = f"{r['sl_hits']} ไม้ ({r['sl_pct']:.1f}%)"
        wr_str = f"{r['win_rate']:.1f}% ({r['wins']}W/{r['losses']}L)"
        pnl_str = f"${r['net_profit']:+,.2f} ({r['net_profit']/10:+.1f}%)"
        dd_str = f"${r['max_dd']:.1f} ({r['max_dd']/10:.1f}%)"
        avg_str = f"${r['avg_win']:.2f} / ${r['avg_loss']:.2f}"
        print(f"{r['sl_mult']:.2f} ATR    | {sl_str:<13} | {wr_str:<10} | {pnl_str:<14} | {r['pf']:.2f} | {dd_str:<12} | {avg_str:<15}")

    print("\n[มิติที่ 2: สถิติ Plan 4 ใน 100 ไม้แรก]")
    print(f"{'SL Setting':<12} | {'ชน SL (ไม้)':<13} | {'Win Rate':<10} | {'กำไรสุทธิ ($)':<14}")
    print("-" * 55)
    for r in recent_results:
        sl_str = f"{r['sl_hits']} ไม้ ({r['sl_pct']:.1f}%)"
        wr_str = f"{r['win_rate']:.1f}% ({r['wins']}W/{r['losses']}L)"
        pnl_str = f"${r['net_profit']:+,.2f}"
        print(f"{r['sl_mult']:.2f} ATR    | {sl_str:<13} | {wr_str:<10} | {pnl_str:<14}")

    mt5.shutdown()

if __name__ == '__main__':
    run_comparison()
