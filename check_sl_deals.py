import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)

def main():
    if not mt5.initialize():
        print("MT5 Init Failed")
        return
    
    from_date = datetime.now() - timedelta(days=14)
    deals = mt5.history_deals_get(from_date, datetime.now())
    if deals:
        df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
        close_deals = df[df['entry'] == 1].copy()
        total_closed = len(close_deals)
        sl_deals = close_deals[close_deals['comment'].str.contains('sl', case=False, na=False)]
        tp_deals = close_deals[close_deals['comment'].str.contains('tp', case=False, na=False)]
        so_deals = close_deals[close_deals['comment'].str.contains('so', case=False, na=False)]
        
        print("="*60)
        print("ประวัติการปิดไม้จริงในพอร์ต MT5 (รอบ 14 วันล่าสุด):")
        print(f"- จำนวนไม้ที่ปิดทั้งหมด : {total_closed} ไม้")
        print(f"- ปิดด้วย Stop Loss (SL): {len(sl_deals)} ไม้")
        print(f"- ปิดด้วย Take Profit (TP): {len(tp_deals)} ไม้")
        print(f"- ปิดด้วย Stop Out / อื่นๆ : {len(so_deals)} ไม้")
        print("="*60)
        print("\nรายการไม้ที่ปิดล่าสุด 10 ไม้:")
        for _, d in close_deals.tail(10).iterrows():
            time_str = datetime.fromtimestamp(d['time']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{time_str}] {d['symbol']} | P/L: ${d['profit']:+.2f} | Comment: {d['comment']}")
    else:
        print("ไม่พบข้อมูล Deals")
        
    mt5.shutdown()

if __name__ == '__main__':
    main()
