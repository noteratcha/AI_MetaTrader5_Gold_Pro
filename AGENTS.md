# 🤖 AI MetaTrader 5 (FBS) Gold Pro v2026.1005.1414 - Project Master Guide

คู่มือมาตรฐานโครงการ (เวอร์ชัน 2026.1005.1414): **สกิล เทคนิค ทักษะ สไตล์ และแผนการเทรดเฉพาะทองคำ (XAUUSD Gold Specialist)** สำหรับระบบเทรด AI อัตโนมัติเชื่อมต่อ MetaTrader 5 (FBS Broker) มุ่งเน้นการดัน **Win Rate และกำไรสุทธิสูงสุด** ด้วยการโฟกัสสภาพคล่องทองคำแบบ 100%

> 📌 **กฎมาตรฐานการกำหนดเลขเวอร์ชัน (Versioning Rule)**:  
> โครงสร้างเลขเวอร์ชันกำหนดในรูปแบบ **`ปี.เดือนวันที่.ชั่วโมงนาที` (`YYYY.MMDD.HHMM`)** เสมอ เช่น `2026.1005.1414`  
> **ทุกครั้งที่แก้โค้ด ต้องอัปเดตเลขเวอร์ชันก่อน commit** ด้วย `python tools/bump_version.py` (แหล่งเดียวคือ `version.py` — ห้ามพิมพ์เลขเวอร์ชันลงไฟล์โค้ดอื่นโดยตรง)

---

## 1. 🎯 สไตล์และปรัชญาการเทรด (Trading Style & Philosophy)

- **ความเชี่ยวชาญเฉพาะทองคำ 100% (XAUUSD Gold Specialist Architecture)**:
  - **XAUUSD (Gold Only)**: โฟกัสเฉพาะสินทรัพย์ทองคำ 100% (ปิด BTCUSD และคู่เงิน Forex ทั้งหมด) เพื่อรวบรวมมาร์จิ้น สมาธิ และคัดกรองเฉพาะชุดแผนเทรดที่สถิติดีที่สุดสำหรับพฤติกรรมทองคำ:
    - ⚡ **Plan 1: `SMC-LiquidityHunt`** (ดักกวาดสภาพคล่องนอกแนวรับต้าน H1 + กรองเทรนด์ H1 100%)
    - 🎯 **Plan 2: `SR-SwingBounce`** (เด้งแนวรับต้าน H1 พร้อม Divergence Confluence)
    - 🌊 **Plan 3: `BB-H1-Reversion`** (ดักจังหวะหลุดกรอบ Bollinger Bands H1 พร้อม Divergence + MACD Exhaustion)
    - 📈 **Plan 4: `MA-Cross-Trend`** (Moving Average 5 ตัด 10 บนแท่ง M15 พร้อมกรองเทรนด์ใหญ่ H1 100%)
    - 👑 **Plan 5: `MA-Cross-H1-Trend`** (Moving Average 5 ตัด 10 บนแท่ง H1 พร้อมกรองเทรนด์ใหญ่ H4 100%)
- **สไตล์การเทรดแบบปรับตัวตามสภาวะตลาด (Market Regime Adaptation)**:
  - **Trending Market (ตลาดมีแนวโน้มชัดเจน)**: บังคับ **Strict Pro-Trend 100%** เทรดฝั่งเดียวกับเทรนด์ H4 MA เท่านั้น ห้ามสวนเทรนด์เด็ดขาดเพื่อตัดการรับมีด
  - **Sideway / Range-Bound Market (ตลาดแกว่งตัวในกรอบ)**: เมื่อ `|h4_diff_pct| < 0.20%` สลับสู่โหมด Range Play อนุมัติการเข้าเทรดได้ทั้ง BUY และ SELL
- **Zero Emotion & Realistic Asymmetric RRR (Sweet Spot)**:
  - อัตราผลตอบแทนต่อความเสี่ยง **RRR 1:1.50** สำหรับแผนที่มี TP ชัดเจน (Plan 1, 2, 3)
  - ขยายระยะตัดขาดทุนให้มีพื้นที่หายใจ **SL 0.75 ATR** ป้องกัน Market Noise และไส้เทียนสะบัดหลุดก่อนเวลา
  - แผนรันเทรนด์ **Plan 4 (M15)** และ **Plan 5 (H1)** ไม่ต้องตั้ง TP เพื่อ Let Profit Run เต็มรอบ และตัดรอบด้วย **Opposite MA Crossover Exit**

---

## 2. 🧠 สกิลและทักษะหลักของระบบ (Core Skills & Competencies)

1. **Pure Gold Focus Engine**: มุ่งเน้นวิเคราะห์พฤติกรรมราคาทองคำ XAUUSD โดยเฉพาะ ไม่กระจายมาร์จิ้น
2. **Candle Wick & Divergence Analytics (SMC + Momentum)**: ตรวจสอบความยาวไส้เทียน (`lower_wick_ratio`, `upper_wick_ratio` $\ge 0.30$) ผสานกับระบบตรวจจับ **RSI Divergence 4 มิติ** (Regular & Hidden Bullish/Bearish)
3. **H1 Bollinger Bands & MACD Exhaustion Edge**: อ้างอิงกรอบความผันผวนใหญ่ระดับวันจาก Timeframe H1 (SMA 20, 2 STD) ผสานการยืนยันการหมดแรงของโมเมนตัมด้วย **H1 MACD Histogram Exhaustion** ดัน Win Rate แตะระดับสูง
4. **M15 MA Crossover with H1 Trend Anchor (Plan 4)**: ระบบตรวจจับ MA 5 ตัดขึ้น/ตัดลง MA 10 บน M15 พร้อมบังคับให้สอดคล้องกับทิศทางเทรนด์ H1 (MA10 vs MA30)
5. **H1 MA Crossover with H4 Trend Anchor (Plan 5)**: ระบบตรวจจับ MA 5 ตัดขึ้น/ตัดลง MA 10 บน H1 พร้อมบังคับให้สอดคล้องกับเทรนด์ใหญ่ H4 (MA10 vs MA30) ปล่อยให้กำไรวิ่งรอบสวิงใหญ่ระดับหลายร้อยจุด
6. **H1 Trend Confluence on SMC Liquidity Hunt**: บังคับให้ Plan 1 เทรดตามทิศทางหลักของแท่งเทียนชั่วโมง H1 เสมอ (BUY เมื่อ H1 Uptrend, SELL เมื่อ H1 Downtrend) ตัดการรับมีดตก 85%
7. **Continuous AI Retraining**: รีเทรนโมเดลใหม่ทุก 24 ชั่วโมง พร้อม Features พิเศษ 16 ตัว เพื่อปรับความเข้าใจต่อพฤติกรรมทองคำล่าสุด
8. **Market Regime Classification & Strict Pro-Trend Filter**: ระบบตรวจจับสภาวะตลาด H4 MA10 vs MA30 แบบ Real-time หากมีแนวโน้มชัดเจนจะบังคับเทรดตามเทรนด์ 100%
9. **Gold Real-time Terminal Dashboard**: แสดงผลข้อมูลราคาทองคำ, ATR, H4 Regime, H1 Trend, MA(5/10) M15, MA(5/10) H1, AI Predict, S&R Zone H1, Bollinger Bands H1 และ H1 MACD Histogram อย่างชัดเจน
10. **Comprehensive Signal History Auditing (`signal_history.csv` & Supabase)**: ระบบบันทึกประวัติการส่งสัญญาณสำคัญทุกประเภท บันทึกพร้อมกันทั้งไฟล์ CSV และ Cloud Database พร้อม Smart Debounce (180s)
11. **Cloud Telemetry Streaming**: สตรีมข้อมูลพอร์ต, ไม้ที่เปิด, เรดาร์สัญญาณสด และสภาวะตลาด H4 ขึ้น Supabase / Vercel ทุกๆ 5 วินาที
12. **Selective Auditory Sensory Feedback (Sound Manager)**: ระบบแจ้งเตือนด้วยเสียงเฉพาะตัว เช่น เสียงดีใจ (เปิดไม้), กระดิ่ง (ชน TP), อ๊อด (ชน SL), นกร้อง (เลื่อน SL)
13. **Automated 1-Year Data Retention & File Size Control (`prune_old_csv_records`)**: ควบคุมขนาดไฟล์ประวัติอัตโนมัติ ลบรายการเก่าเกิน 1 ปี (365 วัน)
14. **Production Auth & Login Gate (Zero Demo Bypass)**: ปิดโหมด Demo ถาวร ต้อง Register/Login ก่อนใช้งานทั้ง Web และ Desktop (สมาชิกใหม่รับฟรี 48 ชม., รหัสผ่าน PBKDF2-HMAC-SHA256)
15. **Admin RBAC (GoldBot24 Web)**: ปุ่มและหน้า `Admin Analytics` แสดงเฉพาะ User Admin (`role:admin` ใน `symbols_trading` หรืออีเมลที่อยู่ใน env `ADMIN_EMAILS` — อีเมลขึ้นต้น `admin@` เฉย ๆ **ไม่ใช่** Admin) และทุก API ฝั่ง Admin ตรวจสิทธิ์จาก Token ที่ลงลายเซ็นบน Server
16. **Hours Metering & Auto Payment**: คิดเงิน 1 บาท/ชม. ตัดเวลาทุก 60 วิเฉพาะตอนบอททำงาน (หักจริงบน Server ผ่าน `/api/auth/meter`), ชำระผ่าน PromptPay QR + ตรวจสลิป SlipOK อัตโนมัติ และเติมเวลาด้วย Product Key 24 หลัก — หน้าชำระเงินรองรับวางสลิป (Ctrl+V)/ลากวาง/แตะเลือกรูป ตรวจทันที, สลิป SCB/BBL ที่ธนาคารให้รอ (SlipOK 1010) นับถอยหลังแล้วตรวจซ้ำเอง และเติมชั่วโมงเข้าบัญชีอัตโนมัติ · *Beam ปฏิเสธ (ประเภทธุรกิจ forex/gold) 5 ต.ค. 2026*
17. **Live Open Positions Monitor**: แท็บ "ออเดอร์ที่เปิดอยู่" แสดงทุกไม้แบบเรียลไทม์ (ราคาเข้า/ปัจจุบัน, SL พร้อม 🔒 เมื่อล็อกกำไรแล้ว, TP หรือ "รันเทรนด์", เวลาที่ถือ, กำไรรวม swap) และปิดทีละไม้ได้ผ่าน `close_position()` ตัวเดียวกับบอท
18. **MT5 Trade History (Paired Deals)**: ดึงประวัติจาก MT5 โดยตรง จับคู่ Deal เข้า/ออกด้วย `position_id` แสดงหน้าละ 5 รายการ พร้อมสรุปชนะ/แพ้/กำไรสุทธิ 90 วัน (Desktop) และ `trade_logs` แบ่งหน้า (เว็บ)
19. **Economic Calendar Awareness**: ปฏิทินเศรษฐกิจรายสัปดาห์ (เวลาไทย) กรอง USD/ผลกระทบ และนับถอยหลังข่าว USD ผลกระทบสูงถัดไป (NFP/CPI/FOMC) ทั้งใน Desktop และหน้า `/calendar` บนเว็บ
20. **Smart Console (Event-Colored Log)**: `console_format.py` ซ่อนข้อความไม่จำเป็น ย่อบล็อกสแกน 10 บรรทัดเหลือ 1 บรรทัด แยกสีตามเหตุการณ์ (BUY/SELL/TP/SL/Exit/Lock/Error) กรองข้อความซ้ำ 5 นาที และอธิบาย error MT5 เป็นภาษาไทย
21. **Secure Remembered Login**: จดจำอีเมล/รหัสผ่านล่าสุดเมื่อติ๊ก "จดจำ" โดยเข้ารหัสด้วย Windows DPAPI (`secure_store.py`) และเก็บข้อมูลผู้ใช้ทั้งหมดใน `%APPDATA%\GoldBot24` ให้อยู่รอดเมื่ออัปเดตโปรแกรม
22. **Self-Updating Release Channel**: ตรวจเวอร์ชันใหม่อัตโนมัติเบื้องหลัง (ทุก 6 ชม.) จาก `/api/release` ← GitHub Releases และแจ้งเป็นป้ายบนแถบหัวโปรแกรม

---

## 3. 📋 แผนการเทรดเฉพาะทองคำ (XAUUSD Trading Plans)

```
┌────────────────────────────────────────────────────────────────────────┐
│                   XAUUSD (GOLD) EXCLUSIVE SUITE                        │
├────────────────────────────────────────────────────────────────────────┤
│ ⚡ Plan 1: SMC-LiquidityHunt (กวาดสภาพคล่องแนวรับ/ต้าน H1 + เทรนด์ H1)    │
│ 🎯 Plan 2: SR-SwingBounce (เด้งโซนแนวรับ/ต้าน H1 + RSI Divergence)     │
│ 🌊 Plan 3: BB-H1-Reversion (เด้งขอบแบนด์ H1 2STD + MACD Confluence)    │
│ 📈 Plan 4: MA-Cross-Trend (MA5 x MA10 M15 + ตัวกรองเทรนด์ใหญ่ H1)      │
│ 👑 Plan 5: MA-Cross-H1-Trend (MA5 x MA10 H1 + ตัวกรองเทรนด์ใหญ่ H4)   │
└────────────────────────────────────────────────────────────────────────┘
```

### 🔹 Plan 1: `SMC-LiquidityHunt` (กวาดสภาพคล่อง + เทรนด์ H1 Confluence)
* **จุดประสงค์**: ดักเก็บจังหวะ Fakeout ที่ราคากวาด Stop Loss นอกแนวรับ/ต้าน แล้วดึงกลับ โดยต้องสอดคล้องกับเทรนด์ใหญ่ H1 เท่านั้น
* **เงื่อนไข BUY**: `Low < Support H1` และ `Close >= Support H1` พร้อมไส้ล่าง `lower_wick_ratio >= 0.30` + **เทรนด์ H1 ต้องเป็น Uptrend (`H1 MA10 > MA30`)** + AI UP $\ge 50\%$ *(หากมี Bullish Divergence ลดเกณฑ์ AI เป็น $\ge 48\%$)*
* **เงื่อนไข SELL**: `High > Resistance H1` และ `Close <= Resistance H1` พร้อมไส้บน `upper_wick_ratio >= 0.30` + **เทรนด์ H1 ต้องเป็น Downtrend (`H1 MA10 < MA30`)** + AI DOWN $\ge 50\%$ *(หากมี Bearish Divergence ลดเกณฑ์ AI เป็น $\ge 48\%$)*
* **ความเสี่ยง/เป้าหมาย**: SL = 0.75 ATR | TP = RRR 1:1.50 (1.125 ATR)

### 🔹 Plan 2: `SR-SwingBounce` (เด้งแนวรับ-ต้าน + Divergence Confluence)
* **จุดประสงค์**: เข้าออเดอร์ตามรอบการแกว่งตัวในกรอบแนวรับ/ต้านหลัก H1 (Mean Reversion - Win Rate 53.3% - 57.1%)
* **เงื่อนไข BUY**: ราคาแตะโซนแนวรับ (`|Close - Support| <= 1.0 ATR`) + สัญญาณแท่งเทียนปฏิเสธราคา + **ต้องมี Bullish/Hidden Bullish Div Confluence** + AI UP $\ge 51\%$
* **เงื่อนไข SELL**: ราคาแตะโซนแนวต้าน (`|Resistance - Close| <= 1.0 ATR`) + สัญญาณแท่งเทียนปฏิเสธราคา + **ต้องมี Bearish/Hidden Bearish Div Confluence** + AI DOWN $\ge 51\%$
* **ความเสี่ยง/เป้าหมาย**: SL = 0.75 ATR | TP = RRR 1:1.50 (1.125 ATR)

### 🔹 Plan 3: `BB-H1-Reversion` (เด้งขอบแบนด์ H1 + Divergence + MACD Exhaustion)
* **จุดประสงค์**: ดักจังหวะราคาทองคำหลุดกรอบความผันผวนใหญ่ระดับวันของ H1 (SMA 20, 2 STD) แล้วถูกปฏิเสธดีดกลับเข้าหากึ่งกลาง ผสานการยืนยันการหมดแรงของโมเมนตัมด้วย MACD (**Win Rate สูงถึง 66.7% - 75.0%**)
* **เงื่อนไข BUY**: `Low < Lower Band H1` และ `Close >= Lower Band H1` พร้อมไส้ล่าง `lower_wick_ratio >= 0.20` + **RSI Divergence Confluence** + **MACD Histogram H1 เริ่มยกตัวขึ้น (Exhaustion)** + AI UP $\ge 50\%$
* **เงื่อนไข SELL**: `High > Upper Band H1` และ `Close <= Upper Band H1` พร้อมไส้บน `upper_wick_ratio >= 0.20` + **RSI Divergence Confluence** + **MACD Histogram H1 เริ่มกดตัวลง (Exhaustion)** + AI DOWN $\ge 50\%$
* **ความเสี่ยง/เป้าหมาย**: SL = 0.75 ATR | TP = RRR 1:1.50 (1.125 ATR)

### 🔹 Plan 4: `MA-Cross-Trend` (MA5 x MA10 M15 + H1 Trend Anchor + Opposite Cross Exit)
* **จุดประสงค์**: ตามรอบโมเมนตัมระยะสั้น M15 ที่สอดคล้องกับเทรนด์ใหญ่ H1 โดยปล่อยให้กำไรวิ่งตามเทรนด์เต็มที่ (Let Profit Run) และปิดไม้ทันทีเมื่อเส้น MA ตัดกลับขั้วตรงข้าม เพื่อดักรอบกำไรก้อนใหญ่ (Big Wins)
* **เงื่อนไข BUY**: MA 5 ตัดขึ้นเหนือ MA 10 บนแท่ง M15 (`MA5[t-1] <= MA10[t-1]` และ `MA5[t] > MA10[t]`) **และ** เทรนด์ใหญ่ H1 ต้องเป็นขาขึ้น (`H1 MA10 > H1 MA30`)
* **เงื่อนไข SELL**: MA 5 ตัดลงใต้ MA 10 บนแท่ง M15 (`MA5[t-1] >= MA10[t-1]` และ `MA5[t] < MA10[t]`) **และ** เทรนด์ใหญ่ H1 ต้องเป็นขาลง (`H1 MA10 < H1 MA30`)
* **เงื่อนไขการปิดไม้ (Exit Condition - ไม่ต้องตั้ง TP)**:
  - 🔄 **สำหรับไม้ BUY**: เมื่อเข้าไม้อยู่ แล้ว MA 5 ตัดลงใต้ MA 10 บน M15 ➔ **ปิดไม้ทันที (Market Close)!**
  - 🔄 **สำหรับไม้ SELL**: เมื่อเข้าไม้อยู่ แล้ว MA 5 ตัดขึ้นเหนือ MA 10 บน M15 ➔ **ปิดไม้ทันที (Market Close)!**
* **การควบคุมความเสี่ยง**: **ไม่ต้องตั้ง TP** (TP = 0.0) เพื่อปล่อยให้กำไรวิ่งสุดเทรนด์ | **Swing SL**: วาง SL เลย High (SELL) / Low (BUY) ของ 2 แท่ง M15 ที่ปิดแล้ว + 0.1 ATR และไม่น้อยกว่า **0.75 ATR** (Backtest 2.5 ปี: กำไรสุทธิ 496 → 952 จุด, PF 1.07 → 1.11, Max DD 405 → 372)

### 🔹 Plan 5: `MA-Cross-H1-Trend` (MA5 x MA10 H1 + H4 Trend Anchor + Opposite Cross Exit)
* **จุดประสงค์**: ตามรอบโมเมนตัมแท่งเทียนระดับชั่วโมง H1 ที่สอดคล้องกับเทรนด์ใหญ่ H4 โดยเข้าไม้บน H1 และปล่อยให้กำไรวิ่งตามแนวโน้มระดับวัน (Swing Trend) พร้อมปิดทันทีเมื่อ MA ตัดกลับขั้วตรงข้ามบน H1
* **เงื่อนไข BUY**: MA 5 ตัดขึ้นเหนือ MA 10 บนแท่ง H1 (`MA5_H1[t-1] <= MA10_H1[t-1]` และ `MA5_H1[t] > MA10_H1[t]`) **และ** เทรนด์ใหญ่ H4 ต้องเป็นขาขึ้นหรือไซด์เวย์บูลลิช (`H4 MA10 > H4 MA30` เสมอ — ไซด์เวย์ที่ MA10 < MA30 ห้าม BUY)
* **เงื่อนไข SELL**: MA 5 ตัดลงใต้ MA 10 บนแท่ง H1 (`MA5_H1[t-1] >= MA10_H1[t-1]` และ `MA5_H1[t] < MA10_H1[t]`) **และ** เทรนด์ใหญ่ H4 ต้องเป็นขาลงหรือไซด์เวย์แบร์ริช (`H4 MA10 < H4 MA30` เสมอ — ไซด์เวย์ที่ MA10 > MA30 ห้าม SELL · Backtest: กำไร 386 → 757 จุด, DD 374 → 297)
* **เงื่อนไขการปิดไม้ (Exit Condition - ไม่ต้องตั้ง TP)**:
  - 🌊 **สำหรับไม้ BUY**: เมื่อถือไม้อยู่ แล้ว MA 5 ตัดลงใต้ MA 10 บนแท่ง H1 ➔ **ปิดไม้ทันที (Market Close)!**
  - 🌊 **สำหรับไม้ SELL**: เมื่อถือไม้อยู่ แล้ว MA 5 ตัดขึ้นเหนือ MA 10 บนแท่ง H1 ➔ **ปิดไม้ทันที (Market Close)!**
* **การควบคุมความเสี่ยง**: **ไม่ต้องตั้ง TP** (TP = 0.0) ปล่อยให้กำไรไหลตามรอบสวิง H1 | ตั้ง Safety Stop Loss = **0.75 ATR (H1)** ป้องกันความผันผวนผิดปกติ

---

## 4. ⚙️ เทคนิคการบริหารออเดอร์ขั้นสูง (Execution Techniques)

1. **Unlimited Dynamic TP**:
   - เมื่อกำไรวิ่งถึง **80% ของเป้า** และโมเดล AI ยังมั่นใจในทิศทางเดิม $\ge 54\%$
   - ดัน TP ไกลออกไปอีก `+1.0 ATR` และดึง SL มาล็อกกำไรด้านหลังทันที
2. **Early Profit Lock (70% Target / +0.35 ATR)**:
   - เมื่อกำไรวิ่งถึง **70% ของเป้าหมาย**
   - เลื่อน SL มาล็อกกำไรที่ **`+0.35 ATR`** จากราคาเปิดทันที เพื่อการันตีกำไรจริงเมื่อราคาแกว่งกลับ
   - มี **Buffer Guard** $\ge 0.4\text{ ATR}$ จากราคาตลาด และ **Throttle Guard** 60 วินาที
3. **AI Dynamic Reversal Close**:
   - หากตรวจพบสัญญาณกลับทิศของ AI อย่างรุนแรง ($\ge 60\%$) และราคาย้อนผ่านจุดเปิด บอทจะปิดไม้ออกทันทีเพื่อลดความสูญเสีย
4. **Closed-Candle Cross Confirmation (Anti-Repaint)**:
   - Plan 4/5 ตรวจ MA Cross จาก**แท่งที่ปิดแล้ว** (`iloc[-2]` เทียบ `iloc[-3]`) ไม่ใช้แท่งที่ยังวิ่งอยู่
   - **Cross-Bar Re-entry Guard**: จดเวลาแท่ง Cross ที่เข้าไม้แล้วใน `last_cross_entry_bar[(sym, plan, direction)]` — ห้ามเข้าซ้ำบนแท่ง Cross เดิม (สัญญาณค้างตลอดอายุแท่ง 15 นาที/1 ชม.)
5. **Timeframe-Matched Safety SL**:
   - Plan 5 ใช้ **ATR(14) ของ H1 จริง** (แท่งที่ปิดแล้ว) × 0.75 — ถ้าข้อมูลไม่พอจึงใช้ ATR M15 × 2 เป็นค่าสำรอง
6. **Single-Count Close Accounting**:
   - ไม้ที่บอทปิดเองผ่าน `close_position()` ถูกจดใน `_self_closed_tickets` เพื่อไม่ให้ส่วนตรวจจับ SL/TP นับขาดทุน/Circuit Breaker/สถิติซ้ำ
   - ทิศของไม้ที่ปิด = **ฝั่งตรงข้ามของ Deal ปิด** (ปิด BUY คือ Deal SELL) — ใช้กำหนด Same-Plan Loss Block ให้ถูกทิศ
7. **Unified Close Path**:
   - ปิดไม้ทุกช่องทาง (AI Reversal, MA Cross Exit, ปุ่มปิดทีละไม้, ปุ่มปิดทุกออเดอร์) ผ่าน `close_position()` เดียว — เลือก filling mode ตามโบรกเกอร์ และบันทึก `trade_logs`/สถิติครบ

---

## 5. 🛡️ เกราะป้องกันความเสี่ยง (Risk Management Protocols)

| กฎการควบคุมความเสี่ยง | พารามิเตอร์ | วัตถุประสงค์ |
| :--- | :--- | :--- |
| **Breathing Room SL** | `0.75 * ATR` | ให้พื้นที่ราคาหายใจ ป้องกันไส้เทียนสะบัดกิน SL ใน Timeframe M15 |
| **Sweet Spot RRR** | `1:1.50` | สร้างความสมดุลระหว่าง Win Rate สูง (45-50%) และกำไรสุทธิ |
| **Strict Pro-Trend** | บล็อกสวนเทรนด์ 100% | ห้ามเข้าออเดอร์สวนทิศ H4 MA เด็ดขาดเมื่อตลาดมีแนวโน้ม |
| **Asset Specialization** | คัดแผนเฉพาะทาง | นำแผน Breakout ออกจากระบบ (กับดัก False Breakout ของทองคำ) และใช้เฉพาะ 5 แผนที่สถิติดี |
| **Circuit Breaker** | ขาดทุนติดกัน 2 ไม้ ➔ พัก 60 นาที | ป้องกัน Drawdown รุนแรงในสภาวะตลาดผิดปกติ (นับไม้ละ 1 ครั้งเท่านั้น — ดูเทคนิคข้อ 6) |
| **Same-Plan Loss Block** | บล็อกทิศเดิม 60 นาทีเมื่อแพ้ | ป้องกันการเข้าซ้ำสวนแนวโน้มที่กำลังวิ่งแรง (ปลดล็อกเมื่อชนะ) |
| **Margin per Trade** | $400 ต่อ 1 ไม้ (Free Margin) | คุมขนาดพอร์ตและป้องกัน Overtrading / Margin Call |
| **Cooldown Rest** | BTC 15 นาที / XAU 10 นาที | พักรอบแท่งเทียนป้องกันอาการ Whipsaw หลังปิดออเดอร์ |
| **Cross-Bar Guard** | 1 ไม้ ต่อ 1 แท่ง Cross | Plan 4/5 ห้ามเข้าซ้ำบนสัญญาณ Cross เดิมหลัง Cooldown หมด |
| **News Awareness** | นับถอยหลังข่าว USD ผลกระทบสูง | เตือนช่วงสเปรดกว้าง/ราคาสะบัดแรง 15–30 นาทีรอบข่าว |

---

## 6. 🐂🐻 ตัวกรองเทรนด์ใหญ่ H4 (Strict Pro-Trend Confluence)

ระบบวิเคราะห์ทิศทางเทรนด์และสภาวะตลาดจาก Timeframe H4 โดยใช้ Moving Average Fast (10) และ Slow (30):
* **🐂 BULLISH [^]**: `MA Fast > MA Slow` และ `h4_diff_pct >= +0.20%` ➔ **BUY เท่านั้น (ห้าม SELL 100%)**
* **🐻 BEARISH [v]**: `MA Fast < MA Slow` และ `h4_diff_pct <= -0.20%` ➔ **SELL เท่านั้น (ห้าม BUY 100%)**
* **⚖️ SIDEWAY [~]**: `abs(h4_diff_pct) < 0.20%` ➔ **Range Play (อนุญาตทั้ง BUY และ SELL)**

---

## 7. 🔐 ระบบเชิงพาณิชย์และกฎวิศวกรรม (GoldBot24 Platform & Engineering Rules)

| หัวข้อ | กฎ / มาตรฐาน |
| :--- | :--- |
| **Login Gate** | ห้ามมี Demo Bypass — Dashboard และ `start_bot()` / `resume_bot()` ต้องผ่าน `is_authenticated` + `has_active_hours()` |
| **Auth Token** | Token = HMAC-SHA256 (`AUTH_SECRET`) ส่งผ่าน `Authorization: Bearer` — API ห้ามรับ `email` จาก Body/Query เป็นตัวระบุผู้ใช้ และ Browser ห้ามเรียก Supabase ตรง (อ่าน/เขียนผ่าน `/api/*` ด้วย Service Role เท่านั้น) |
| **Hours Metering** | Desktop หักเวลาในเครื่องแล้วส่งยอดให้ `/api/auth/meter` หักจริงบน Server ทุก 5 นาที — ห้าม PATCH `bot_config.lot_size` ตรงจาก Client |
| **Register** | ยืนยันอีเมลด้วยรหัส 6 หลักก่อนสร้างบัญชี (ตอบข้อความเดียวกันเสมอ ถ้ามีบัญชีอยู่แล้วส่งอีเมลแจ้งเจ้าของแทน — กันสุ่มหาอีเมล) · สมาชิกใหม่รับฟรี 48 ชม. รหัสผ่านเข้ารหัส PBKDF2-HMAC-SHA256 |
| **Admin RBAC** | `Admin Analytics` (Navbar/Footer/หน้า `/admin/analytics`) แสดงเฉพาะ Admin เท่านั้น ห้ามเปิดเผยสถิติทุกลูกค้าและเครื่องผลิต Promo Key ต่อลูกค้าทั่วไป · แอดมินสลับ **โหมดการดู ผู้ใช้ ↔ แอดมิน** ได้ที่ Navbar (`viewMode` ใน `AuthContext`, จำไว้ใน `localStorage`) — โหมดผู้ใช้ซ่อนเมนูแอดมินทั้งหมด (`isAdminView`) แต่สิทธิ์จริงยังตรวจที่ Server เสมอ |
| **Payment** | ราคา/ชั่วโมงคิดจาก `web/src/lib/packages.js` ฝั่ง Server เท่านั้น · Order ID สุ่มแบบเดาไม่ได้ · PromptPay QR → SlipOK ตรวจสลิป (`log: true` กันสลิปซ้ำ + `amount` ตรวจยอด) → ผลิต Product Key อัตโนมัติ · Webhook ต้องมี `x-webhook-secret` · ห้ามโหมดจำลองบน Production · ข้อผิดพลาด SlipOK แปลเป็นข้อความ+คำแนะนำภาษาไทย (`code`, `hint`, `retryAfterSec`) · ปัญหาฝั่งร้าน (แพ็กเกจ/โควตา SlipOK 1000–1004, 1015) แจ้งแอดมินทาง LINE · **ใบเสร็จ**: ชำระสำเร็จ → `issueReceipt()` บันทึกตาราง `receipts` (เลขที่ `GB24-YYYYMM-000001`, 1 คำสั่งซื้อ = 1 ใบ) + ส่งอีเมลผู้ซื้อ · ดู/พิมพ์ที่ `/receipts` (`supabase_receipts_patch_04.sql`) |
| **Database Security** | RLS เปิดทุกตาราง — anon key อ่านตารางผู้ใช้/คีย์/คำสั่งซื้อ/พอร์ตไม่ได้ · Desktop เขียน Telemetry/สถิติผ่าน RPC `bot_upsert_telemetry` / `bot_upsert_plan_stats` (SECURITY DEFINER, เขียนอย่างเดียว) · Migration: `supabase_security_rls.sql` + `supabase_security_rls_patch_01.sql` |
| **Secrets** | ห้าม commit/ส่งคีย์ลับในแชท — ใส่ผ่าน `npx vercel env add <NAME> production --sensitive` · รหัส MT5 อยู่ในเครื่องเท่านั้น (`%APPDATA%\GoldBot24\credentials.json`) ไม่ซิงค์ขึ้น Cloud |
| **Desktop Data Dir** | ไฟล์ผู้ใช้ทั้งหมดผ่าน `app_paths.data_path()` → `%APPDATA%\GoldBot24` (ห้ามเก็บข้างไฟล์ .exe เพราะถูกลบทุกครั้งที่ build) |
| **Desktop GUI Colors** | CustomTkinter รับเฉพาะ Hex `#RRGGBB` — **ห้ามใช้ `rgba()`** (ทำให้ `TclError` โปรแกรมเปิดไม่ขึ้น) |
| **Release Flow** | 1) `python tools/bump_version.py` 2) Smoke Test GUI 3) `python build_dist.py` (ต้องปิดโปรแกรมก่อน ไม่งั้นไฟล์ถูกล็อก) 4) สร้าง GitHub Release `v<เวอร์ชัน>` แนบ ZIP + SHA-256 → หน้า `/download` และการแจ้งอัปเดตในโปรแกรมอัปเดตเอง · Web: `cd web && npm run build` → `git push` (Vercel Root Directory = `web` deploy อัตโนมัติ) · เปลี่ยน env บน Vercel แล้วต้อง redeploy: `cd web && npx vercel redeploy <URL production ล่าสุด> --target production` (โฟลเดอร์ `web` คือที่ link กับ Vercel) |
| **Responsive Desktop** | ออกแบบให้พอดีจอ 1366×768 (เปิดเต็มจออัตโนมัติเมื่อจอเล็ก) · Tk แสดงอีโมจีสีไม่ได้ ให้ใช้ Label สี/ป้ายแทน และหลีกเลี่ยงอีโมจี Unicode ใหม่ (เช่น 🪙) ที่ Windows 10 ไม่มี |
| **Tk Grid** | `sticky` ใช้ได้เฉพาะ n/s/e/w — ห้าม `sticky="center"` (TclError) |

---

## 8. 🔌 สถาปัตยกรรมและการเชื่อมต่อ (Architecture & Integrations)

```
┌──────────────── Desktop (Windows) ────────────────┐        ┌────────── GoldBot24 Web (Vercel) ──────────┐
│ gui_app.py ── bot_controller.py ── multi_asset_ai_bot│        │ Next.js 16 · App Router (หน้าเว็บ)            │
│      │              │   (MT5 Python API)          │ Bearer │ Pages Router `/api/*` (Service Role)        │
│ license_manager ────┼───── login/me/meter/redeem ─┼───────▶│ auth · checkout · user · admin · calendar   │
│ econ_calendar ──────┼───── /api/calendar, /api/release ───▶│ release (← GitHub Releases)                 │
│ supabase_sync ──────┼── RPC/insert (anon, เขียนอย่างเดียว) ─┐ └───────────────┬────────────────────────────┘
└──────────┬──────────┘                                    │                 │ Service Role
           ▼                                               ▼                 ▼
   MetaTrader 5 (FBS)                                   Supabase Postgres (RLS เปิดทุกตาราง)
```

### 8.1 Web API (`web/src/pages/api`)
| Endpoint | สิทธิ์ | หน้าที่ |
| :--- | :--- | :--- |
| `POST /api/auth/login`, `/register` | สาธารณะ | คืน Token ลงลายเซ็น (30 วัน) · hash v2 (210k รอบ) · อัปเกรด v1 อัตโนมัติ |
| `GET /api/auth/me` · `POST /meter` · `POST /redeem` | Bearer | ข้อมูลบัญชี · หักนาทีใช้งาน · เติมคีย์ (จองคีย์แบบ atomic) |
| `POST /api/auth/forgot-password` · `/reset-password` | สาธารณะ (จำกัดความถี่) | ส่งรหัสยืนยัน 6 หลักทางอีเมล (15 นาที, 3 ครั้ง/ชม., ผิดได้ 5 ครั้ง) · ตั้งรหัสใหม่ + เข้าสู่ระบบ |
| `POST /api/auth/change-password` | Bearer | เปลี่ยนรหัสผ่านของตัวเอง (แอดมิน ≥ 10 ตัว ไม่ใช่ตัวเลขล้วน) |
| `POST /api/checkout/create-qr` · `GET /check-status` · `POST /verify-slip` | Bearer + เจ้าของคำสั่งซื้อ | สร้างคำสั่งซื้อ/QR · ตรวจสถานะ · ตรวจสลิป SlipOK |
| `POST /api/webhook/payment` | `x-webhook-secret` | แจ้งชำระจากผู้ให้บริการ |
| `POST /api/webhook/line` | ลายเซ็น `x-line-signature` | LINE OA Webhook — พิมพ์ `id` เพื่อรับ userId/groupId สำหรับ `LINE_ADMIN_TO` |
| `POST /api/admin/line-test` | Admin | ส่งข้อความทดสอบไป LINE OA |
| `POST /api/admin/users/[id]/unlock` | Admin | ปลดล็อกการเข้าสู่ระบบ (รหัสผิด 5 ครั้ง/15 นาที) — บันทึก `account_unlocked` แล้วนับรหัสผิดใหม่จากศูนย์ |
| `GET/POST /api/cron/daily-summary` | Vercel Cron (`CRON_SECRET`) / Admin | สรุปยอดรายวันเต็มวัน 00:00–23:59 น. ส่ง LINE หลังเที่ยงคืน (`web/vercel.json` → `0 17 * * *` UTC = 00:00 น. ไทย, แพ็กเกจฟรีคลาดได้ภายใน 1 ชม.) · แอดมินกด "ส่งสรุปวันนี้" = ยอดตั้งแต่ 00:00 ถึงตอนกด |
| `GET/POST /api/user/receipts` | Bearer (เจ้าของ/แอดมิน) | ใบเสร็จของฉัน · ใบเดียว `?id=` (เลขใบเสร็จหรือเลขคำสั่งซื้อ) · ส่งอีเมลซ้ำ (เว้น 60 วิ) |
| `GET /api/user/telemetry` · `/trades` · `/stats` · `/keys` | Bearer | พอร์ตสด · ประวัติ (แบ่งหน้า) · สถิติรายแผน · คีย์ของฉัน |
| `GET /api/admin/overview` · `POST /promo-key` | Admin | ภาพรวมระบบ · ผลิต Promo Key |
| `GET /api/calendar` · `/api/release` | สาธารณะ (CDN cache) | ปฏิทินเศรษฐกิจ (30 นาที) · เวอร์ชันล่าสุด (10 นาที) |

### 8.2 Environment Variables (Vercel)
`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `AUTH_SECRET`, `ADMIN_EMAILS`, `PROMPTPAY_ID`, `SLIPOK_BRANCH_ID`, `SLIPOK_API_KEY`, `PAYMENT_WEBHOOK_SECRET`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `MAIL_FROM` (ลืมรหัสผ่าน/ยืนยันสมัคร), `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_ADMIN_TO`, `LINE_CHANNEL_SECRET` (แจ้งเตือนแอดมินทาง LINE OA) · `CRON_SECRET` (Vercel Cron) · `RECEIPT_SELLER_NAME`, `RECEIPT_SELLER_ADDRESS`, `RECEIPT_SELLER_TAX_ID`, `RECEIPT_SELLER_CONTACT` (หัวใบเสร็จ) · *(ถัดไป)* `PAYMENT_PROVIDER`, `BEAM_MERCHANT_ID`, `BEAM_API_KEY`, `BEAM_WEBHOOK_HMAC_KEY`, `BEAM_ENV`

### 8.3 ผู้ใช้และข้อมูลใน Supabase
* ผู้ใช้อยู่ในตาราง `bot_config` (`mt5_server` = อีเมล, `mt5_password` = hash, `lot_size` = ชั่วโมงคงเหลือ, `symbols_trading` = tag เช่น `name:`, `role:admin`) — แถว `id = 1` เป็น config ระบบ
* `bot_telemetry` 1 แถวต่อ 1 บัญชี (`id` = id ผู้ใช้) · `trade_logs` แยกด้วย `email` · `user_plan_stats` แยกด้วย `user_id` (TEXT)

### 8.4 บริการภายนอก
| บริการ | ใช้ทำอะไร | หมายเหตุ |
| :--- | :--- | :--- |
| **MetaTrader 5 (FBS)** | ข้อมูลราคา/ส่งคำสั่ง/ประวัติ Deal | magic `888999` · comment = ชื่อแผน |
| **Supabase** | ฐานข้อมูล + RLS + RPC | Desktop ใช้ anon key เขียนอย่างเดียว |
| **Vercel** | เว็บ + API | `goldbot24.vercel.app` |
| **GitHub Releases** | แจกไฟล์ติดตั้ง Desktop | `noteratcha/AI_MetaTrader5_Gold_Pro` (public) |
| **SlipOK** | ตรวจสลิปโอนเงิน | ต้องมีสลิปเสมอ (ไม่มี API ตรวจยอดเข้าเอง) |
| **LINE OA (Messaging API)** | แจ้งเตือนแอดมิน: สมาชิกใหม่ · ซื้อชั่วโมงสำเร็จ · บัญชีถูกล็อก (รหัสผิด 5 ครั้ง เฉพาะบัญชีที่มีจริง) · สรุปยอดรายวันเต็มวัน (`lib/server/lineNotify.js`, `dailySummary.js`) | Push Message นับโควตารายเดือนของ OA · ส่งไม่สำเร็จไม่กระทบการสมัคร/ชำระเงิน |
| **Beam** *(ปฏิเสธ 5 ต.ค. 2026)* | — | ไม่รองรับธุรกิจ forex/gold trading (Omise มีข้อห้ามเดียวกัน) · ไม่ต้องแนบสลิปจริงต้องใช้ API ธนาคาร (มักต้องเป็นนิติบุคคล) |
| **Economic Calendar Feed** | ปฏิทินข่าวรายสัปดาห์ | จำกัดจำนวนครั้ง (429) → ใช้ผ่าน `/api/calendar` ที่ cache ไว้ |
| **Investing.com Widget** | ปฏิทินแบบฝัง (เว็บ) | มีปุ่มเปิดหน้า Investing.com สำรอง |

### 8.5 ไฟล์สำคัญฝั่ง Desktop
`version.py` (เลขเวอร์ชันแหล่งเดียว) · `app_paths.py` (โฟลเดอร์ข้อมูลผู้ใช้) · `secure_store.py` (DPAPI) · `console_format.py` (Console สี) · `econ_calendar.py` · `tools/bump_version.py` · `tools/admin_reset_password.py` (สร้าง SQL รีเซ็ตรหัสผ่านลูกค้า)
