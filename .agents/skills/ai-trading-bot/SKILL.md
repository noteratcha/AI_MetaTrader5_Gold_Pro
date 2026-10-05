---
name: ai-trading-bot
description: Comprehensive knowledge, skills, technical indicators, execution styles, trading plans (SMC Sweep, Bounce, BB-H1, MA-Cross M15/H1), dynamic TP/SL, risk management, desktop GUI (positions, history, economic calendar, smart console), and GoldBot24 web/Supabase/payment integrations for the AI MetaTrader 5 Gold bot.
---

# AI MetaTrader 5 Trading Bot v2026.1005.1414: XAUUSD Gold Specialist

คู่มือมาตรฐานสำหรับระบบเทรดอัตโนมัติ **AI MetaTrader 5 Gold Pro v2026.1005.1414** ที่มุ่งเน้นการดัน **Win Rate และผลตอบแทนสุทธิสูงสุด** ในสินทรัพย์ทองคำ (**XAUUSD Only 100%**) ด้วยสถาปัตยกรรม **Pure Gold Specialization**, **RRR 1:1.50**, **Breathing Room SL 0.75 ATR**, **Plan 1: SMC Liquidity Hunt + H1 Trend Anchor**, **Plan 3: H1 Bollinger Bands Reversion**, **Plan 4: M15 MA(5, 10) Cross + H1 Trend Anchor**, **Plan 5: H1 MA(5, 10) Cross + H4 Trend Anchor** และ **Strict Pro-Trend Only**

> 📌 **กฎมาตรฐานการกำหนดเลขเวอร์ชัน (Versioning Rule)**: รูปแบบ **`ปี.เดือนวันที่.ชั่วโมงนาที` (`YYYY.MMDD.HHMM`)**

---

## 1. สกิลและทักษะหลักของระบบ (Core Skills & System Capabilities)

1. **Pure Gold Specialization Engine (โฟกัสทองคำ 100%)**
   - **XAUUSD (Gold Only)**: โฟกัส **Plan 1 (SMC-LiquidityHunt + H1 Trend)**, **Plan 2 (SR-SwingBounce)**, **Plan 3 (BB-H1-Reversion)**, **Plan 4 (MA-Cross-Trend M15)** และ **Plan 5 (MA-Cross-H1-Trend H1)** นำแผน Breakout ออกจากระบบ และปิดสินทรัพย์อื่นทั้งหมด
2. **Multi-Timeframe Market Vision (การวิเคราะห์หลายกรอบเวลาประสานกัน)**
   - **H4**: กำหนดทิศทางเทรนด์หลัก (Strict Pro-Trend Filter) ด้วย `ma_fast_h4 (10)` / `ma_slow_h4 (30)`
   - **H1**: กำหนดกรอบแนวรับ-แนวต้านโครงสร้างหลัก (Structure Support & Resistance 20 ชม. ย้อนหลัง), **กรอบความผันผวนใหญ่ระดับวัน (H1 Bollinger Bands SMA 20, 2 STD) + H1 MACD** และ **สัญญาณเข้าไม้ Plan 5 (H1 MA5 x MA10)**
   - **M15**: จังหวะคัดกรองสัญญาณ เข้าออเดอร์ คำนวณฟีเจอร์แท่งเทียน และวิเคราะห์ความผันผวน (ATR, Divergence, Wick Rejection, MA 5 x MA 10 Crossover สำหรับ Plan 4)
3. **Machine Learning Directional Intelligence (ความฉลาดด้านความน่าจะเป็น)**
   - ใช้โมเดล **RandomForestClassifier (n_estimators=100, max_depth=5)**
   - คำนวณความน่าจะเป็นของทิศทางราคาในแท่งถัดไป เกณฑ์ความมั่นใจขั้นต่ำ $\ge 54\%$
   - **Continuous Learning**: รีเทรนโมเดลอัตโนมัติทุกๆ 24 ชั่วโมง เพื่อปรับตัวเข้ากับสภาวะตลาดปัจจุบัน
4. **Wick & Divergence Analytics (SMC + RSI Divergence)**
   - คำนวณสัดส่วนไส้เทียนบนและล่างต่อ ATR (`lower_wick_ratio`, `upper_wick_ratio` $\ge 0.30$)
   - ระบบตรวจจับ **RSI Divergence 4 มิติ**: Regular Bullish/Bearish Divergence และ Hidden Bullish/Bearish Divergence
5. **H1 Bollinger Bands & MACD Exhaustion Edge**
   - ดักจับจังหวะราคาทองคำหลุดกรอบความผันผวนใหญ่ระดับวันของ H1 แล้วดีดกลับพร้อมไส้ปฏิเสธราคา ผสานการยืนยันการหมดแรงของโมเมนตัมด้วย **H1 MACD Histogram Exhaustion** (Win Rate เฉพาะแผนนี้สูงถึง **66.7% - 75.0%**)
6. **M15 Moving Average Crossover with H1 Trend Anchor (Plan 4)**
   - ตรวจจับ MA 5 ตัดขึ้น/ตัดลง MA 10 บน M15 ผสานตัวกรองเทรนด์ใหญ่ H1 เพื่อลด False Crossover ปิดไม้ด้วย MA Cross ขั้วตรงข้าม
7. **H1 Moving Average Crossover with H4 Trend Anchor (Plan 5)**
   - ตรวจจับ MA 5 ตัดขึ้น/ตัดลง MA 10 บน H1 ผสานตัวกรองเทรนด์ใหญ่ H4 เพื่อดักจับรอบสวิงใหญ่ระดับวัน ปล่อยให้กำไรวิ่งสุดเทรนด์ และปิดไม้ด้วย H1 Opposite MA Cross
8. **Strict Pro-Trend & Sideway Market Regime Adaptation**
   - คำนวณเปอร์เซ็นต์ส่วนต่างของเส้นค่าเฉลี่ย H4: `h4_diff_pct = ((ma10 / ma30) - 1.0) * 100.0`
   - หาก `abs(h4_diff_pct) < 0.20%` ➔ ตลาดเข้าสู่สภาวะ **`SIDEWAY [~]`** (Range Play เข้าได้ทั้งสองฝั่ง)
   - หากมีแนวโน้มชัดเจน ➔ บังคับ **Strict Pro-Trend 100%** ห้ามเทรดสวนเทรนด์เด็ดขาดเพื่อตัดการรับมีด
9. **Comprehensive Signal History Auditing (`signal_history.csv` & Supabase)**
   - บันทึกประวัติการส่งสัญญาณสำคัญทุกประเภทลงไฟล์ CSV และฐานข้อมูล Cloud Supabase พร้อม Smart Debounce (180s)
10. **Real-time Telemetry & Cloud Synchronization**
   - สตรีมสถานะพอร์ตและเรดาร์สัญญาณสดขึ้น Supabase / Vercel ทุกๆ 5 วินาที
11. **Automated 1-Year Data Retention & File Size Control (`prune_old_csv_records`)**
   - ระบบควบคุมขนาดไฟล์ประวัติอัตโนมัติ ตรวจสอบและลบรายการที่เก่าเกินกว่า 1 ปี (365 วัน)
12. **Live Open Positions Monitor**
   - แท็บ "ออเดอร์ที่เปิดอยู่" อัปเดตทุก 1 วินาที: ราคาเข้า/ปัจจุบัน, SL (🔒 เมื่อเลื่อนมาล็อกกำไรแล้ว), TP หรือ "รันเทรนด์", เวลาที่ถือ, กำไรรวม swap และปุ่มปิดทีละไม้ (`bot_ctrl.close_position_by_ticket`)
13. **MT5 Paired Trade History**
   - `bot_ctrl.get_trade_history()` จับคู่ Deal เข้า (`entry=0`) / ออก (`entry=1`) ด้วย `position_id` แสดงหน้าละ 5 รายการ + สรุป 90 วัน; บนเว็บใช้ `trade_logs` (`OPEN_BUY/OPEN_SELL/CLOSE/TP_HIT/SL_HIT`) ผ่าน `/api/user/trades`
14. **Economic Calendar & News Countdown**
   - `econ_calendar.py` / `/api/calendar` (cache 30 นาที เพราะต้นทางจำกัดจำนวนครั้ง) แสดงเวลาไทย กรอง USD + ระดับผลกระทบ และนับถอยหลังข่าว USD ผลกระทบสูงถัดไป — ช่วง 15–30 นาทีรอบข่าวสเปรดทองกว้างและราคาสะบัดแรง
15. **Smart Event Console**
   - `console_format.ConsoleFormatter` ซ่อน countdown/เส้นคั่น/log ภายใน ย่อบล็อกสแกนเหลือ 1 บรรทัด (แสดงเมื่อสถานะเปลี่ยน) แยกสี BUY/SELL/TP/SL/Exit/Lock/Error และแปล error MT5 (10018 ตลาดปิด, 10019 มาร์จิ้นไม่พอ, 10027 AutoTrading ปิด)
16. **Secure Session & Self-Update**
   - จดจำอีเมล/รหัสผ่านด้วย Windows DPAPI (`secure_store.py`), ข้อมูลผู้ใช้ใน `%APPDATA%\GoldBot24` (`app_paths.py`), ตรวจเวอร์ชันใหม่อัตโนมัติจาก GitHub Releases ทุก 6 ชม.

---

## 2. สไตล์การเทรด (Trading Style & Identity)

- **Pure Gold Focus Asset Allocation**: โฟกัสเฉพาะทองคำ **XAUUSD** 100% ปิดสินทรัพย์อื่นๆ ทั้งหมด เพื่อไม่ให้กระจายมาร์จิ้น
- **High Win-Rate & Dynamic Trend Catching**: ปรับอัตราผลตอบแทนต่อความเสี่ยงให้อยู่ในจุด Sweet Spot ที่ 1:1.50 (SL 0.75 ATR, TP 1.125 ATR) สำหรับแผนแกว่งตัวในกรอบ และปล่อยให้กำไรวิ่งไร้ขีดจำกัด (No TP) สำหรับแผนรันเทรนด์ MA Cross
- **Breathing Room Capital Preservation**: ขยายระยะ SL เป็น **0.75 ATR** ป้องกันไม่ให้โดนสะบัดหลุดจากความผันผวนธรรมชาติของแท่งเทียน

---

## 3. แผนการเทรดเฉพาะสินทรัพย์ (Asset-Specialized Trading Plans)

### Plan 1: `SMC-LiquidityHunt` (การกวาดสภาพคล่อง + Divergence + H1 Trend Anchor)
* **คอนเซปต์**: ตามรอยสถาบันการเงิน (Smart Money) เมื่อราคาวิ่งหลุดแนวรับหรือแนวต้านเพื่อกวาด Stop Loss แล้วดึงกลับเข้าสู่โซนอย่างรวดเร็ว โดยต้องบังคับเข้าตามทิศทางเทรนด์ใหญ่ H1 เท่านั้นเพื่อตัดปัญหาการรับมีดตก
* **เงื่อนไข BUY**: `low < support H1` และ `close >= support H1` พร้อม `lower_wick_ratio >= 0.30` + AI UP $\ge 50\%$ *(หากมี Bullish Divergence ลดเกณฑ์เป็น $\ge 0.48$)* **และบังคับต้องอยู่ในแนวโน้มขาขึ้น H1 (`is_uptrend_h1 == True`)**
* **เงื่อนไข SELL**: `high > resistance H1` และ `close <= resistance H1` พร้อม `upper_wick_ratio >= 0.30` + AI DOWN $\ge 50\%$ *(หากมี Bearish Divergence ลดเกณฑ์เป็น $\ge 0.48$)* **และบังคับต้องอยู่ในแนวโน้มขาลง H1 (`is_uptrend_h1 == False`)**
* **การตั้ง SL/TP**: SL = 0.75 ATR, TP = RRR 1:1.50 (1.125 ATR)

### Plan 2: `SR-SwingBounce` (การเด้งจากแนวรับ-แนวต้านหลัก + Divergence)
* **คอนเซปต์**: เข้าออเดอร์ตามรอบการแกว่งตัวในกรอบแนวรับ/ต้าน H1 (Mean Reversion - Win Rate 53.3% - 57.1%)
* **เงื่อนไข BUY**: ราคาแตะโซนแนวรับ (`|close - support| <= 1.0 * ATR`) + มีแท่งปฏิเสธราคา + **ต้องมี Bullish/Hidden Bullish Div Confluence** + AI UP $\ge 51\%$
* **เงื่อนไข SELL**: ราคาแตะโซนแนวต้าน (`|resistance - close| <= 1.0 * ATR`) + มีแท่งปฏิเสธราคา + **ต้องมี Bearish/Hidden Bearish Div Confluence** + AI DOWN $\ge 51\%$
* **การตั้ง SL/TP**: SL = 0.75 ATR, TP = RRR 1:1.50 (1.125 ATR)

### Plan 3: `BB-H1-Reversion` (เด้งขอบแบนด์ H1 + Divergence + MACD Exhaustion)
* **คอนเซปต์**: ดักจังหวะราคาทองคำหลุดกรอบความผันผวนใหญ่ระดับวันของ H1 (SMA 20, 2 STD) แล้วถูกปฏิเสธดีดกลับเข้าหากึ่งกลาง ผสานการยืนยันการหมดแรงของโมเมนตัมด้วย H1 MACD (**Win Rate สูงถึง 66.7% - 75.0%**)
* **เงื่อนไข BUY**: `Low < Lower Band H1` และ `Close >= Lower Band H1` พร้อมไส้ล่าง `lower_wick_ratio >= 0.20` + **RSI Divergence Confluence** + **MACD Histogram H1 เริ่มยกตัวขึ้น (Exhaustion)** + AI UP $\ge 50\%$
* **เงื่อนไข SELL**: `High > Upper Band H1` และ `Close <= Upper Band H1` พร้อมไส้บน `upper_wick_ratio >= 0.20` + **RSI Divergence Confluence** + **MACD Histogram H1 เริ่มกดตัวลง (Exhaustion)** + AI DOWN $\ge 50\%$
* **การตั้ง SL/TP**: SL = 0.75 ATR, TP = RRR 1:1.50 (1.125 ATR)

### Plan 4: `MA-Cross-Trend` (MA 5 x MA 10 Crossover บน M15 + กรองเทรนด์ H1 + ปิดไม้ด้วย MA Cross ขั้วตรงข้าม)
* **คอนเซปต์**: เข้าออเดอร์ตามการตัดกันของเส้น Moving Average ระยะสั้น (5 และ 10) บนกรอบเวลา M15 โดยต้องสอดคล้องกับทิศทางเทรนด์ใหญ่ H1 100% ปล่อยให้กำไรวิ่งตามเทรนด์เต็มที่ (Let Profit Run) และปิดไม้ทันทีเมื่อเส้น MA ตัดกลับขั้วตรงข้าม
* **เงื่อนไข BUY**: เส้น MA 5 ตัดขึ้นเหนือ MA 10 บนแท่ง M15 **และ** แท่งเทียนชั่วโมง H1 อยู่ในแนวโน้มขาขึ้น (H1 Uptrend: `H1 MA10 > H1 MA30`)
* **เงื่อนไข SELL**: เส้น MA 5 ตัดลงใต้ MA 10 บนแท่ง M15 **และ** แท่งเทียนชั่วโมง H1 อยู่ในแนวโน้มขาลง (H1 Downtrend: `H1 MA10 < H1 MA30`)
* **เงื่อนไขการปิดไม้ (Exit Condition - ไม่ต้องตั้ง TP)**:
  - 🔄 **สำหรับไม้ BUY**: เมื่อเข้าไม้อยู่ แล้ว MA 5 ตัดลงใต้ MA 10 บน M15 ➔ **ปิดไม้ทันที (Market Close)!**
  - 🔄 **สำหรับไม้ SELL**: เมื่อเข้าไม้อยู่ แล้ว MA 5 ตัดขึ้นเหนือ MA 10 บน M15 ➔ **ปิดไม้ทันที (Market Close)!**
* **การตั้ง SL/TP**: **ไม่ต้องตั้ง TP** (TP = 0.0) | **Swing SL** เลย High/Low ของ 2 แท่ง M15 ที่ปิดแล้ว + 0.1 ATR (ไม่น้อยกว่า 0.75 ATR)

### Plan 5: `MA-Cross-H1-Trend` (MA 5 x MA 10 Crossover บน H1 + กรองเทรนด์ H4 + ปิดไม้ด้วย H1 MA Cross ขั้วตรงข้าม)
* **คอนเซปต์**: เข้าออเดอร์ตามการตัดกันของเส้น Moving Average (5 และ 10) บนกรอบเวลาแท่งชั่วโมง H1 โดยต้องสอดคล้องกับทิศทางเทรนด์ใหญ่ H4 100% ปล่อยให้กำไรวิ่งตามรอบสวิงใหญ่ระดับวัน (Daily Swing) และปิดไม้ทันทีเมื่อ MA ตัดกลับขั้วตรงข้ามบน H1
* **เงื่อนไข BUY**: เส้น MA 5 ตัดขึ้นเหนือ MA 10 บนแท่ง H1 **และ** แนวโน้มใหญ่ H4 เป็นขาขึ้นหรือไซด์เวย์บูลลิช (`H4 MA10 > H4 MA30` เสมอ)
* **เงื่อนไข SELL**: เส้น MA 5 ตัดลงใต้ MA 10 บนแท่ง H1 **และ** แนวโน้มใหญ่ H4 เป็นขาลงหรือไซด์เวย์แบร์ริช (`H4 MA10 < H4 MA30` เสมอ)
* **เงื่อนไขการปิดไม้ (Exit Condition - ไม่ต้องตั้ง TP)**:
  - 🌊 **สำหรับไม้ BUY**: เมื่อถือไม้อยู่ แล้ว MA 5 ตัดลงใต้ MA 10 บน H1 ➔ **ปิดไม้ทันที (Market Close)!**
  - 🌊 **สำหรับไม้ SELL**: เมื่อถือไม้อยู่ แล้ว MA 5 ตัดขึ้นเหนือ MA 10 บน H1 ➔ **ปิดไม้ทันที (Market Close)!**
* **การตั้ง SL/TP**: **ไม่ต้องตั้ง TP** (TP = 0.0) | ตั้ง Safety Stop Loss = **0.75 ATR (H1)** ป้องกันความผันผวนผิดปกติ

---

## 4. เทคนิคชั้นสูงในการบริหารจัดการออเดอร์ (Advanced Order Management)

### 1. Unlimited Dynamic TP & ATR Extension (ปลดล็อกกำไรไร้ขีดจำกัด)
- เมื่อราคาทำกำไรถึง **80% ของเป้าหมาย TP** และ AI ยังยืนยันความน่าจะเป็นในทิศทางเดิม $\ge 54\%$
- ขยับ TP ไกลออกไปอีก `+1.0 * ATR`
- ดึง SL ตามมาล็อกกำไรที่ค่าที่สูงกว่าระหว่าง `Entry + 0.3 ATR` กับ `Current Price - 1.0 ATR` (ฝั่ง SELL กลับด้าน) และไม่ถอย SL เดิม
- ใช้กับแผนที่มี TP เท่านั้น — Plan 4/5 (TP = 0) ข้ามขั้นตอนนี้และปิดด้วย Opposite MA Cross

### 2. Early Profit Lock (ล็อกกำไรที่ 70% ของเป้าหมาย / +0.35 ATR)
- เมื่อราคาวิ่งมาได้ **70% ของเป้าหมาย**
- ขยับ SL มาล็อกกำไรที่ **`+0.35 ATR`** จากราคาเปิดทันที เพื่อการันตีกำไรจริงเมื่อราคาแกว่งกลับ
- **Buffer Check**: SL ที่ล็อกต้องอยู่ห่างจากราคาตลาดปัจจุบัน $\ge 0.4\text{ ATR}$
- **Throttle Control**: ห้ามแก้ไข SL ซ้ำภายใน 60 วินาที

### 3. AI Dynamic Reversal Exit (ตัดขาดทุนเชิงรุกเมื่อทิศทางกลับลำ)
- หากถือสถานะอยู่ แต่โมเดล AI ตรวจพบสัญญาณกลับตัวชัดเจน ($\ge 60\%$) และราคาย้อนผ่านราคาเปิด
- บอทจะทำการปิดไม้ทันที ไม่รอให้ชน Stop Loss เต็มจำนวน

---

### 4. Closed-Candle Cross + Cross-Bar Re-entry Guard (Plan 4/5)
- ตรวจ MA5 x MA10 จากแท่งที่ปิดแล้ว (`iloc[-2]` vs `iloc[-3]`) กัน Repaint
- จดแท่ง Cross ที่เข้าไม้แล้วใน `last_cross_entry_bar[(sym, plan, direction)]` — ห้ามเข้าซ้ำบนแท่งเดิมแม้ Cooldown หมด

### 5. Timeframe-Matched Safety SL
- Plan 5 ใช้ **ATR(14) H1** จริง × 0.75 (สำรอง: ATR M15 × 2 เมื่อข้อมูล H1 ไม่พอ)

### 6. Single-Count Close Accounting
- ไม้ที่บอทปิดเอง (`close_position`) ถูกจดใน `_self_closed_tickets` เพื่อไม่ให้ส่วนตรวจจับ SL/TP นับขาดทุน/Circuit Breaker ซ้ำ
- ทิศของไม้ที่ปิด = ฝั่งตรงข้ามของ Deal ปิด → Same-Plan Loss Block บล็อกถูกทิศ
- ทุกช่องทางปิดไม้ (AI Reversal, MA Exit, ปิดทีละไม้, ปิดทั้งหมด) ใช้ `close_position()` เดียว: filling mode ตามโบรกเกอร์ + บันทึก `trade_logs`/สถิติ

---

## 5. ระบบควบคุมความเสี่ยงและความปลอดภัย (Risk Management & Circuit Breakers)

1. **Breathing Room SL**: ตั้งค่า SL ที่ `0.75 * ATR` ป้องกัน Market Noise กวาดก่อนถึงเป้าหมาย
2. **Sweet Spot RRR**: กำหนด RRR พื้นฐานที่ `1:1.50` เพื่อดัน Win Rate สู่ 45-50%
3. **Strict Pro-Trend Only**: ห้ามเปิดไม้สวนแนวโน้มใหญ่ H4 เด็ดขาดเมื่อตลาดมีทิศทาง
4. **Circuit Breaker**: หากขาดทุนติดต่อกันครบ **2 ไม้** พัก 60 นาที
5. **Same-Plan Loss Block**: บล็อกทิศเดิม 60 นาทีเมื่อแพ้ (ปลดล็อกทันทีเมื่อชนะ)
6. **Free Margin Position Sizing**: มาจินทุกๆ **$400** ต่อ 1 ไม้
7. **Cooldown หลังปิดออเดอร์**: พัก 15 นาที สำหรับ BTCUSD และ 10 นาที สำหรับ XAUUSD
8. **Cross-Bar Guard**: Plan 4/5 เข้าได้ 1 ไม้ต่อ 1 แท่ง Cross
9. **News Awareness**: แสดงนับถอยหลังข่าว USD ผลกระทบสูง ให้ระวังออเดอร์ที่เปิดอยู่ช่วงประกาศข่าว

---

## 6. ระบบเชิงพาณิชย์และการควบคุมสิทธิ์ (GoldBot24 Commercial Platform & Access Control)

1. **Zero Demo Bypass**: ปิดโหมด Demo ถาวรทั้ง Web และ Desktop — ต้อง Login ก่อนเข้าถึง Dashboard และก่อนเริ่มบอทเสมอ
2. **Register + 48h Starter Bonus**: สมัครสมาชิกได้ทั้งเว็บและโปรแกรม ต้องยืนยันอีเมลด้วยรหัส 6 หลัก (กันสุ่มหาอีเมล) รหัสผ่านเข้ารหัส **PBKDF2-HMAC-SHA256** และรับฟรี 48 ชม.
3. **Hours Metering (1 บาท/ชม.)**: ตัดเวลาทุก 60 วินาทีเฉพาะตอนบอททำงาน แสดงผลรูปแบบ `HH.MM` เสมอ; `start_bot()` / `resume_bot()` ต้องผ่าน `is_authenticated` + `has_active_hours()`
4. **Product Key 24 หลัก**: รูปแบบ `XXXX-XXXX-XXXX-XXXX-XXXX-XXXX` เติมแบบบวกเพิ่ม (+) ผ่าน `RedeemKeyDialog` หรือหน้า `/dashboard`
5. **PromptPay QR + SlipOK Auto-Verify**: สร้าง QR (`/api/checkout/create-qr`, ราคาคิดฝั่ง Server) → ตรวจสลิป (`/api/checkout/verify-slip`, SlipOK `log: true` + `amount`) / Webhook (`/api/webhook/payment` ต้องมี `x-webhook-secret`) → ผลิต Product Key อัตโนมัติ (ล็อกคำสั่งซื้อด้วยสถานะ `PROCESSING` กันออกคีย์ซ้ำ)
   - **ถัดไป: Beam Payment Gateway** — QR PromptPay จาก Beam + Webhook `charge.succeeded` (ลายเซ็น `X-Beam-Signature` HMAC-SHA256) → ออกคีย์อัตโนมัติไม่ต้องแนบสลิป (ดู `CHECKLIST_BEAM.md`)
6. **Admin RBAC (Role-Based Access)**:
   - Admin = `symbols_trading` มี `role:admin` หรืออีเมลอยู่ใน env `ADMIN_EMAILS` (อีเมลขึ้นต้น `admin@` เฉย ๆ ไม่นับ); API `/api/auth/login` และ `/api/auth/me` คืนค่า `role` / `isAdmin` และ `/api/admin/*` ตรวจสิทธิ์ฝั่ง Server
   - ปุ่ม `[ 🛡️ Admin Analytics ]` ใน Navbar/Footer แสดง **เฉพาะ Admin เท่านั้น**
   - หน้า `/admin/analytics` มี **Admin Access Barrier** (กันการเข้าผ่าน URL ตรง) — ข้อมูลสถิติทุกลูกค้าและเครื่องผลิต Promo Key ห้ามเปิดเผยต่อลูกค้าทั่วไป
7. **Desktop GUI Color Rule**: CustomTkinter/Tkinter รับเฉพาะสี Hex `#RRGGBB` หรือชื่อสี Tk — **ห้ามใช้ `rgba()` แบบ CSS** (ทำให้ `TclError` และโปรแกรมเปิดไม่ขึ้น) ให้ใช้ค่าคงที่สีในธีม เช่น `COLOR_GOLD_BG`, `COLOR_GOLD_DARK`
8. **Release Discipline**: ทุกครั้งที่แก้โค้ด `python tools/bump_version.py` (แหล่งเดียว `version.py`) → Smoke Test GUI (`MainTradingApp()` → `update()` → `destroy()`) → ปิดโปรแกรมแล้ว `python build_dist.py` → GitHub Release `v<เวอร์ชัน>` + ZIP + SHA-256 (หน้า `/download` และป้ายอัปเดตในโปรแกรมอ่านจากที่นี่); หลังแก้เว็บให้ `npm run build` แล้ว `git push` (Root Directory = `web` deploy อัตโนมัติ)
9. **Auth & Data Security**: Token ลงลายเซ็น HMAC (`AUTH_SECRET`) ผ่าน `Authorization: Bearer` · Browser ไม่เรียก Supabase ตรง · RLS เปิดทุกตาราง · Desktop เขียน Telemetry/สถิติผ่าน RPC `bot_upsert_telemetry` / `bot_upsert_plan_stats` (เขียนอย่างเดียว) · หักชั่วโมงผ่าน `/api/auth/meter` เท่านั้น · รหัส MT5 อยู่ในเครื่องเท่านั้น · คีย์ลับใส่ผ่าน `npx vercel env add ... --sensitive` ห้ามส่งในแชท
10. **Desktop UI Rules**: พอดีจอ 1366×768 · ห้าม `sticky="center"` ใน Tk grid · ห้ามอีโมจี Unicode ใหม่ที่ Windows 10 ไม่มี (เช่น 🪙) · งานเครือข่าย/MT5 ที่ช้าให้ทำในเธรดเบื้องหลังแล้วอัปเดต UI จาก UI loop เท่านั้น

---

## 7. การเชื่อมต่อ (Integrations)

| ระบบ | การเชื่อมต่อ |
| :--- | :--- |
| **MetaTrader 5 (FBS)** | Python `MetaTrader5` · magic `888999` · `comment` = ชื่อแผน · เวลา Deal/Position เป็นเวลาเซิร์ฟเวอร์ |
| **GoldBot24 Web (Vercel)** | `https://goldbot24.vercel.app` · Desktop เรียก `/api/auth/{login,register,me,meter,redeem}`, `/api/calendar`, `/api/release` (env `GOLDBOT_API_URL` เปลี่ยนได้) |
| **Supabase** | ผู้ใช้ใน `bot_config` (`mt5_server`=อีเมล, `lot_size`=ชั่วโมง) · `bot_telemetry` 1 แถว/บัญชี · `trade_logs` แยกด้วย `email` · `user_plan_stats` แยกด้วย `user_id` · Migration: `supabase_security_rls.sql`, `supabase_security_rls_patch_01.sql` |
| **GitHub Releases** | `noteratcha/AI_MetaTrader5_Gold_Pro` — ไฟล์ติดตั้ง + changelog + SHA-256 |
| **SlipOK** | ตรวจสลิป (ต้องมีสลิปเสมอ) · error สำคัญ: 1010 รอธนาคาร, 1012 สลิปซ้ำ, 1013 ยอดไม่ตรง, 1014 บัญชีผู้รับไม่ตรง |
| **Beam** *(รออนุมัติ)* | `POST /api/v1/charges` (`QR_PROMPT_PAY`) · Basic auth `merchantId:apiKey` · Webhook `charge.succeeded/failed` |
| **Economic Calendar** | Feed รายสัปดาห์ผ่าน `/api/calendar` (cache) + Investing.com widget บนหน้า `/calendar` |

