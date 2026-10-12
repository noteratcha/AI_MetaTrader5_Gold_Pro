import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)

SYMBOL = "XAUUSD"
TIMEFRAME_H1 = mt5.TIMEFRAME_H1
TIMEFRAME_H4 = mt5.TIMEFRAME_H4
TOTAL_BARS_H1 = 8000  # ประมาณ 1-1.5 ปี

def get_data(symbol, timeframe, n_bars):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_bars)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def test():
    if not mt5.initialize():
        print("MT5 Init Failed")
        return
    mt5.symbol_select(SYMBOL, True)
    sym_info = mt5.symbol_info(SYMBOL)
    spread_pts = sym_info.spread
    point = sym_info.point
    contract_size = sym_info.trade_contract_size
    gap_buffer = spread_pts * point

    df_h1 = get_data(SYMBOL, TIMEFRAME_H1, TOTAL_BARS_H1)
    df_h4 = get_data(SYMBOL, TIMEFRAME_H4, (TOTAL_BARS_H1 // 4) + 100)

    if df_h1 is None or df_h4 is None:
        print("ดึงข้อมูลไม่สำเร็จ")
        return

    # H4 Indicators (Trend Anchor)
    df_h4['ma_fast_h4'] = df_h4['close'].rolling(10).mean()
    df_h4['ma_slow_h4'] = df_h4['close'].rolling(30).mean()
    df_h4['h4_diff_pct'] = ((df_h4['ma_fast_h4'] / df_h4['ma_slow_h4']) - 1.0) * 100.0
    df_h4['time_h4'] = df_h4['time'].dt.floor('4h')
    df_h4_features = df_h4[['time_h4', 'ma_fast_h4', 'ma_slow_h4', 'h4_diff_pct']].dropna()

    # H1 Indicators (Entry & Opposite Exit)
    df_h1['ma5_h1'] = df_h1['close'].rolling(5).mean()
    df_h1['ma10_h1'] = df_h1['close'].rolling(10).mean()

    high_low = df_h1['high'] - df_h1['low']
    high_close = (df_h1['high'] - df_h1['close'].shift()).abs()
    low_close = (df_h1['low'] - df_h1['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df_h1['atr_h1'] = tr.rolling(14).mean()

    df_h1['time_h4'] = df_h1['time'].dt.floor('4h')
    df = pd.merge(df_h1, df_h4_features, on='time_h4', how='left')
    df['ma_fast_h4'] = df['ma_fast_h4'].ffill()
    df['ma_slow_h4'] = df['ma_slow_h4'].ffill()
    df['h4_diff_pct'] = df['h4_diff_pct'].ffill()

    df = df.dropna().reset_index(drop=True)
    print(f"โหลดข้อมูลสำเร็จ: {len(df)} แท่งเทียน H1 (~ {len(df)//24} วันทำการ)")

    # ทดสอบ Plan 5: เข้าไม้บน H1 (MA5 ตัด 10) + กรองเทรนด์ H4
    # ทดสอบ SL: 0.75 ATR (H1 ATR)
    for sl_setting in [0.75, 1.00, 1.50]:
        balance = 1000.0
        trades = []
        current_trade = None
        lot_size = 0.01

        for i in range(1, len(df)):
            bar = df.iloc[i]
            prev_bar = df.iloc[i-1]

            ma5 = bar['ma5_h1']
            ma10 = bar['ma10_h1']
            prev_ma5 = prev_bar['ma5_h1']
            prev_ma10 = prev_bar['ma10_h1']

            ma_cross_up = (prev_ma5 <= prev_ma10) and (ma5 > ma10)
            ma_cross_down = (prev_ma5 >= prev_ma10) and (ma5 < ma10)

            # ตรวจสอบไม้ที่ถืออยู่
            if current_trade is not None:
                entry_p = current_trade['entry_price']
                trade_type = current_trade['type']
                sl_p = current_trade['sl']

                # ตรวจ SL
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
                    trades.append({'result': 'WIN' if pnl > 0 else 'LOSS', 'pnl': pnl, 'reason': 'SL'})
                    current_trade = None
                else:
                    # ตรวจ MA Cross Exit (ขั้วตรงข้ามบน H1)
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
                        trades.append({'result': 'WIN' if pnl > 0 else 'LOSS', 'pnl': pnl, 'reason': 'MA_CROSS_H1'})
                        current_trade = None

            # พิจารณาเปิดไม้ใหม่บน H1
            if current_trade is None and i < len(df) - 1:
                is_uptrend_h4 = bar['ma_fast_h4'] > bar['ma_slow_h4']
                is_sideway_h4 = abs(bar['h4_diff_pct']) < 0.20

                if is_sideway_h4:
                    h4_buy_ok = True
                    h4_sell_ok = True
                else:
                    h4_buy_ok = is_uptrend_h4
                    h4_sell_ok = not is_uptrend_h4

                atr_val = bar['atr_h1']
                close_p = bar['close']

                if ma_cross_up and h4_buy_ok:
                    entry_p = close_p + gap_buffer
                    sl_p = entry_p - (atr_val * sl_setting) - gap_buffer
                    current_trade = {'type': 'BUY', 'entry_price': entry_p, 'sl': sl_p}
                elif ma_cross_down and h4_sell_ok:
                    entry_p = close_p - gap_buffer
                    sl_p = entry_p + (atr_val * sl_setting) + gap_buffer
                    current_trade = {'type': 'SELL', 'entry_price': entry_p, 'sl': sl_p}

        wins = [t for t in trades if t['result'] == 'WIN']
        losses = [t for t in trades if t['result'] == 'LOSS']
        wr = (len(wins) / len(trades) * 100.0) if trades else 0.0
        net = balance - 1000.0
        gross_w = sum(t['pnl'] for t in wins)
        gross_l = abs(sum(t['pnl'] for t in losses))
        pf = gross_w / gross_l if gross_l > 0 else 0
        sl_hits = len([t for t in trades if t['reason'] == 'SL'])
        ma_exits = len([t for t in trades if t['reason'] == 'MA_CROSS_H1'])
        ma_wins = len([t for t in trades if t['reason'] == 'MA_CROSS_H1' and t['result'] == 'WIN'])

        print(f"SL Setting: {sl_setting:.2f} ATR | ไม้ทั้งหมด: {len(trades):3d} | Win Rate: {wr:5.1f}% | Net Profit: ${net:+8.2f} | PF: {pf:4.2f} | ปิดด้วย MA Exit: {ma_exits} (ชนะ {ma_wins}) | ชน SL: {sl_hits}")

    mt5.shutdown()

if __name__ == '__main__':
    test()
