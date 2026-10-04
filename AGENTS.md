# 🤖 AI MetaTrader 5 (FBS) Gold Pro v2026.1004.2305 - Project Master Guide

คู่มือมาตรฐานโครงการ (เวอร์ชัน 2026.1004.2305): **สกิล เทคนิค ทักษะ สไตล์ และแผนการเทรดเฉพาะทองคำ (XAUUSD Gold Specialist)** สำหรับระบบเทรด AI อัตโนมัติเชื่อมต่อ MetaTrader 5 (FBS Broker) มุ่งเน้นการดัน **Win Rate และกำไรสุทธิสูงสุด** ด้วยการโฟกัสสภาพคล่องทองคำแบบ 100%

> 📌 **กฎมาตรฐานการกำหนดเลขเวอร์ชัน (Versioning Rule)**:  
> โครงสร้างเลขเวอร์ชันกำหนดในรูปแบบ **`ปี.เดือนวันที่.ชั่วโมงนาที` (`YYYY.MMDD.HHMM`)** เสมอ เช่น `2026.1004.2305`  
> **ทุกครั้งที่แก้โค้ด ต้องอัปเดตเลขเวอร์ชันก่อน commit** ด้วย `python tools/bump_version.py` (แหล่งเดียวคือ `version.py` — ห้ามพิมพ์เลขเวอร์ชันลงไฟล์โค้ดอื่นโดยตรง)

---

## 1. 🎯 สไตล์และปรัชญาการเทรด (Trading Style & Philosophy)

- **ความเชี่ยวชาญเฉพาะทองคำ 100% (XAUUSD Gold Specialist Architecture)**:
  - **XAUUSD (Gold Only)**: โฟกัสเฉพาะสินทรัพย์ทองคำ 100% (ปิด BTCUSD และคู่เงิน Forex ทั้งหมด) เพื่อรวบรวมมาร์จิ้น สมาธิ และคัดกรองเฉพาะชุดแผนเทรดที่สถิติดีที่สุดสำหรับพฤติกรรมทองคำ:
    - ⚡ **Plan 0: `SMC-LiquidityHunt`** (ดักกวาดสภาพคล่องนอกแนวรับต้าน H1 + กรองเทรนด์ H1 100%)
    - 🎯 **Plan 1: `SR-SwingBounce`** (เด้งแนวรับต้าน H1 พร้อม Divergence Confluence)
    - 🌊 **Plan 3: `BB-H1-Reversion`** (ดักจังหวะหลุดกรอบ Bollinger Bands H1 พร้อม Divergence + MACD Exhaustion)
    - 📈 **Plan 4: `MA-Cross-Trend`** (Moving Average 5 ตัด 10 บนแท่ง M15 พร้อมกรองเทรนด์ใหญ่ H1 100%)
    - 👑 **Plan 5: `MA-Cross-H1-Trend`** (Moving Average 5 ตัด 10 บนแท่ง H1 พร้อมกรองเทรนด์ใหญ่ H4 100%)
    - 🚫 *ปิด Plan 2 Breakout ถาวรเพื่อตัดกับดัก False Breakout ของทองคำ*
- **สไตล์การเทรดแบบปรับตัวตามสภาวะตลาด (Market Regime Adaptation)**:
  - **Trending Market (ตลาดมีแนวโน้มชัดเจน)**: บังคับ **Strict Pro-Trend 100%** เทรดฝั่งเดียวกับเทรนด์ H4 MA เท่านั้น ห้ามสวนเทรนด์เด็ดขาดเพื่อตัดการรับมีด
  - **Sideway / Range-Bound Market (ตลาดแกว่งตัวในกรอบ)**: เมื่อ `|h4_diff_pct| < 0.20%` สลับสู่โหมด Range Play อนุมัติการเข้าเทรดได้ทั้ง BUY และ SELL
- **Zero Emotion & Realistic Asymmetric RRR (Sweet Spot)**:
  - อัตราผลตอบแทนต่อความเสี่ยง **RRR 1:1.50** สำหรับแผนที่มี TP ชัดเจน (Plan 0, 1, 3)
  - ขยายระยะตัดขาดทุนให้มีพื้นที่หายใจ **SL 0.75 ATR** ป้องกัน Market Noise และไส้เทียนสะบัดหลุดก่อนเวลา
  - แผนรันเทรนด์ **Plan 4 (M15)** และ **Plan 5 (H1)** ไม่ต้องตั้ง TP เพื่อ Let Profit Run เต็มรอบ และตัดรอบด้วย **Opposite MA Crossover Exit**

---

## 2. 🧠 สกิลและทักษะหลักของระบบ (Core Skills & Competencies)

1. **Pure Gold Focus Engine**: มุ่งเน้นวิเคราะห์พฤติกรรมราคาทองคำ XAUUSD โดยเฉพาะ ไม่กระจายมาร์จิ้น
2. **Candle Wick & Divergence Analytics (SMC + Momentum)**: ตรวจสอบความยาวไส้เทียน (`lower_wick_ratio`, `upper_wick_ratio` $\ge 0.30$) ผสานกับระบบตรวจจับ **RSI Divergence 4 มิติ** (Regular & Hidden Bullish/Bearish)
3. **H1 Bollinger Bands & MACD Exhaustion Edge**: อ้างอิงกรอบความผันผวนใหญ่ระดับวันจาก Timeframe H1 (SMA 20, 2 STD) ผสานการยืนยันการหมดแรงของโมเมนตัมด้วย **H1 MACD Histogram Exhaustion** ดัน Win Rate แตะระดับสูง
4. **M15 MA Crossover with H1 Trend Anchor (Plan 4)**: ระบบตรวจจับ MA 5 ตัดขึ้น/ตัดลง MA 10 บน M15 พร้อมบังคับให้สอดคล้องกับทิศทางเทรนด์ H1 (MA10 vs MA30)
5. **H1 MA Crossover with H4 Trend Anchor (Plan 5)**: ระบบตรวจจับ MA 5 ตัดขึ้น/ตัดลง MA 10 บน H1 พร้อมบังคับให้สอดคล้องกับเทรนด์ใหญ่ H4 (MA10 vs MA30) ปล่อยให้กำไรวิ่งรอบสวิงใหญ่ระดับหลายร้อยจุด
6. **H1 Trend Confluence on SMC Liquidity Hunt**: บังคับให้ Plan 0 เทรดตามทิศทางหลักของแท่งเทียนชั่วโมง H1 เสมอ (BUY เมื่อ H1 Uptrend, SELL เมื่อ H1 Downtrend) ตัดการรับมีดตก 85%
7. **Continuous AI Retraining**: รีเทรนโมเดลใหม่ทุก 24 ชั่วโมง พร้อม Features พิเศษ 16 ตัว เพื่อปรับความเข้าใจต่อพฤติกรรมทองคำล่าสุด
8. **Market Regime Classification & Strict Pro-Trend Filter**: ระบบตรวจจับสภาวะตลาด H4 MA10 vs MA30 แบบ Real-time หากมีแนวโน้มชัดเจนจะบังคับเทรดตามเทรนด์ 100%
9. **Gold Real-time Terminal Dashboard**: แสดงผลข้อมูลราคาทองคำ, ATR, H4 Regime, H1 Trend, MA(5/10) M15, MA(5/10) H1, AI Predict, S&R Zone H1, Bollinger Bands H1 และ H1 MACD Histogram อย่างชัดเจน
10. **Comprehensive Signal History Auditing (`signal_history.csv` & Supabase)**: ระบบบันทึกประวัติการส่งสัญญาณสำคัญทุกประเภท บันทึกพร้อมกันทั้งไฟล์ CSV และ Cloud Database พร้อม Smart Debounce (180s)
11. **Cloud Telemetry Streaming**: สตรีมข้อมูลพอร์ต, ไม้ที่เปิด, เรดาร์สัญญาณสด และสภาวะตลาด H4 ขึ้น Supabase / Vercel ทุกๆ 5 วินาที
12. **Selective Auditory Sensory Feedback (Sound Manager)**: ระบบแจ้งเตือนด้วยเสียงเฉพาะตัว เช่น เสียงดีใจ (เปิดไม้), กระดิ่ง (ชน TP), อ๊อด (ชน SL), นกร้อง (เลื่อน SL)
13. **Automated 1-Year Data Retention & File Size Control (`prune_old_csv_records`)**: ควบคุมขนาดไฟล์ประวัติอัตโนมัติ ลบรายการเก่าเกิน 1 ปี (365 วัน)
14. **Production Auth & Login Gate (Zero Demo Bypass)**: ปิดโหมด Demo ถาวร ต้อง Register/Login ก่อนใช้งานทั้ง Web และ Desktop (สมาชิกใหม่รับฟรี 48 ชม., รหัสผ่าน PBKDF2-HMAC-SHA256)
15. **Admin RBAC (GoldBot24 Web)**: ปุ่มและหน้า `Admin Analytics` แสดงเฉพาะ User Admin (`role:admin` ใน `symbols_trading` หรืออีเมลที่อยู่ใน env `ADMIN_EMAILS` — อีเมลขึ้นต้น `admin@` เฉย ๆ **ไม่ใช่** Admin) และทุก API ฝั่ง Admin ตรวจสิทธิ์จาก Token ที่ลงลายเซ็นบน Server
16. **Hours Metering & Auto Payment**: คิดเงิน 1 บาท/ชม. ตัดเวลาทุก 60 วิเฉพาะตอนบอททำงาน, ชำระผ่าน PromptPay QR + ตรวจสลิป SlipOK อัตโนมัติ และเติมเวลาด้วย Product Key 24 หลัก

---

## 3. 📋 แผนการเทรดเฉพาะทองคำ (XAUUSD Trading Plans)

```
┌────────────────────────────────────────────────────────────────────────┐
│                   XAUUSD (GOLD) EXCLUSIVE SUITE                        │
├────────────────────────────────────────────────────────────────────────┤
│ ⚡ Plan 0: SMC-LiquidityHunt (กวาดสภาพคล่องแนวรับ/ต้าน H1 + เทรนด์ H1)    │
│ 🎯 Plan 1: SR-SwingBounce (เด้งโซนแนวรับ/ต้าน H1 + RSI Divergence)     │
│ 🌊 Plan 3: BB-H1-Reversion (เด้งขอบแบนด์ H1 2STD + MACD Confluence)    │
│ 📈 Plan 4: MA-Cross-Trend (MA5 x MA10 M15 + ตัวกรองเทรนด์ใหญ่ H1)      │
│ 👑 Plan 5: MA-Cross-H1-Trend (MA5 x MA10 H1 + ตัวกรองเทรนด์ใหญ่ H4)   │
│       *(ปิด Plan 2 Breakout ถาวร เพื่อป้องกัน False Breakout)*         │
└────────────────────────────────────────────────────────────────────────┘
```

### 🔹 Plan 0: `SMC-LiquidityHunt` (กวาดสภาพคล่อง + เทรนด์ H1 Confluence)
* **จุดประสงค์**: ดักเก็บจังหวะ Fakeout ที่ราคากวาด Stop Loss นอกแนวรับ/ต้าน แล้วดึงกลับ โดยต้องสอดคล้องกับเทรนด์ใหญ่ H1 เท่านั้น
* **เงื่อนไข BUY**: `Low < Support H1` และ `Close >= Support H1` พร้อมไส้ล่าง `lower_wick_ratio >= 0.30` + **เทรนด์ H1 ต้องเป็น Uptrend (`H1 MA10 > MA30`)** + AI UP $\ge 50\%$ *(หากมี Bullish Divergence ลดเกณฑ์ AI เป็น $\ge 48\%$)*
* **เงื่อนไข SELL**: `High > Resistance H1` และ `Close <= Resistance H1` พร้อมไส้บน `upper_wick_ratio >= 0.30` + **เทรนด์ H1 ต้องเป็น Downtrend (`H1 MA10 < MA30`)** + AI DOWN $\ge 50\%$ *(หากมี Bearish Divergence ลดเกณฑ์ AI เป็น $\ge 48\%$)*
* **ความเสี่ยง/เป้าหมาย**: SL = 0.75 ATR | TP = RRR 1:1.50 (1.125 ATR)

### 🔹 Plan 1: `SR-SwingBounce` (เด้งแนวรับ-ต้าน + Divergence Confluence)
* **จุดประสงค์**: เข้าออเดอร์ตามรอบการแกว่งตัวในกรอบแนวรับ/ต้านหลัก H1 (Mean Reversion - Win Rate 53.3% - 57.1%)
* **เงื่อนไข BUY**: ราคาแตะโซนแนวรับ (`|Close - Support| <= 1.0 ATR`) + สัญญาณแท่งเทียนปฏิเสธราคา + **ต้องมี Bullish/Hidden Bullish Div Confluence** + AI UP $\ge 51\%$
* **เงื่อนไข SELL**: ราคาแตะโซนแนวต้าน (`|Resistance - Close| <= 1.0 ATR`) + สัญญาณแท่งเทียนปฏิเสธราคา + **ต้องมี Bearish/Hidden Bearish Div Confluence** + AI DOWN $\ge 51\%$
* **ความเสี่ยง/เป้าหมาย**: SL = 0.75 ATR | TP = RRR 1:1.50 (1.125 ATR)

### 🔹 Plan 2: `Trend-Breakout` (ปิดถาวรบนทองคำ)
* *หมายเหตุ: ปิดการทำงานบน XAUUSD ถาวรเพื่อป้องกันการติดกับดัก False Breakout*

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
* **การควบคุมความเสี่ยง**: **ไม่ต้องตั้ง TP** (TP = 0.0) เพื่อปล่อยให้กำไรวิ่งสุดเทรนด์ | ตั้ง Safety Stop Loss = **0.75 ATR** ป้องกันข่าวกระชากรุนแรง

### 🔹 Plan 5: `MA-Cross-H1-Trend` (MA5 x MA10 H1 + H4 Trend Anchor + Opposite Cross Exit)
* **จุดประสงค์**: ตามรอบโมเมนตัมแท่งเทียนระดับชั่วโมง H1 ที่สอดคล้องกับเทรนด์ใหญ่ H4 โดยเข้าไม้บน H1 และปล่อยให้กำไรวิ่งตามแนวโน้มระดับวัน (Swing Trend) พร้อมปิดทันทีเมื่อ MA ตัดกลับขั้วตรงข้ามบน H1
* **เงื่อนไข BUY**: MA 5 ตัดขึ้นเหนือ MA 10 บนแท่ง H1 (`MA5_H1[t-1] <= MA10_H1[t-1]` และ `MA5_H1[t] > MA10_H1[t]`) **และ** เทรนด์ใหญ่ H4 ต้องเป็นขาขึ้น/ไซด์เวย์บูลลิช (`H4 MA10 > H4 MA30` หรือ `is_sideway_h4`)
* **เงื่อนไข SELL**: MA 5 ตัดลงใต้ MA 10 บนแท่ง H1 (`MA5_H1[t-1] >= MA10_H1[t-1]` และ `MA5_H1[t] < MA10_H1[t]`) **และ** เทรนด์ใหญ่ H4 ต้องเป็นขาลง/ไซด์เวย์แบร์ริช (`H4 MA10 < H4 MA30` หรือ `is_sideway_h4`)
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

---

## 5. 🛡️ เกราะป้องกันความเสี่ยง (Risk Management Protocols)

| กฎการควบคุมความเสี่ยง | พารามิเตอร์ | วัตถุประสงค์ |
| :--- | :--- | :--- |
| **Breathing Room SL** | `0.75 * ATR` | ให้พื้นที่ราคาหายใจ ป้องกันไส้เทียนสะบัดกิน SL ใน Timeframe M15 |
| **Sweet Spot RRR** | `1:1.50` | สร้างความสมดุลระหว่าง Win Rate สูง (45-50%) และกำไรสุทธิ |
| **Strict Pro-Trend** | บล็อกสวนเทรนด์ 100% | ห้ามเข้าออเดอร์สวนทิศ H4 MA เด็ดขาดเมื่อตลาดมีแนวโน้ม |
| **Asset Specialization** | คัดแผนเฉพาะทาง | ปิด Breakout บน XAU และปิด Bounce บน BTC เพื่อตัดไม้แพ้ซ้ำซาก |
| **Circuit Breaker** | ขาดทุนติดกัน 2 ไม้ ➔ พัก 60 นาที | ป้องกัน Drawdown รุนแรงในสภาวะตลาดผิดปกติ |
| **Same-Plan Loss Block** | บล็อกทิศเดิม 60 นาทีเมื่อแพ้ | ป้องกันการเข้าซ้ำสวนแนวโน้มที่กำลังวิ่งแรง (ปลดล็อกเมื่อชนะ) |
| **Margin per Trade** | $400 ต่อ 1 ไม้ (Free Margin) | คุมขนาดพอร์ตและป้องกัน Overtrading / Margin Call |
| **Cooldown Rest** | BTC 15 นาที / XAU 10 นาที | พักรอบแท่งเทียนป้องกันอาการ Whipsaw หลังปิดออเดอร์ |

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
| **Register** | สมาชิกใหม่รับฟรี 48 ชม. รหัสผ่านเข้ารหัส PBKDF2-HMAC-SHA256 |
| **Admin RBAC** | `Admin Analytics` (Navbar/Footer/หน้า `/admin/analytics`) แสดงเฉพาะ Admin เท่านั้น ห้ามเปิดเผยสถิติทุกลูกค้าและเครื่องผลิต Promo Key ต่อลูกค้าทั่วไป |
| **Payment** | PromptPay QR → SlipOK ตรวจสลิป/Webhook → ผลิต Product Key `XXXX-XXXX-XXXX-XXXX-XXXX-XXXX` อัตโนมัติ |
| **Desktop GUI Colors** | CustomTkinter รับเฉพาะ Hex `#RRGGBB` — **ห้ามใช้ `rgba()`** (ทำให้ `TclError` โปรแกรมเปิดไม่ขึ้น) |
| **Release Flow** | GUI: Smoke Test → `python build_dist.py` / Web: `npm run build` → `npx vercel --prod --yes` |
