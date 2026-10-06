# 🤖 AI MetaTrader 5 (FBS) Gold Pro v2026.1006.2339 - Project Master Guide

คู่มือมาตรฐานโครงการ (เวอร์ชัน 2026.1006.2339): **สกิล เทคนิค ทักษะ สไตล์ และแผนการเทรดเฉพาะทองคำ (XAUUSD Gold Specialist)** สำหรับระบบเทรด AI อัตโนมัติเชื่อมต่อ MetaTrader 5 (FBS Broker) มุ่งเน้นการดัน **Win Rate และกำไรสุทธิสูงสุด** ด้วยการโฟกัสสภาพคล่องทองคำแบบ 100%

> 📌 **กฎมาตรฐานการกำหนดเลขเวอร์ชัน (Versioning Rule)**:  
> โครงสร้างเลขเวอร์ชันกำหนดในรูปแบบ **`ปี.เดือนวันที่.ชั่วโมงนาที` (`YYYY.MMDD.HHMM`)** เสมอ เช่น `2026.1005.2244`  
> **ทุกครั้งที่แก้โค้ด ต้องอัปเดตเลขเวอร์ชันก่อน commit** ด้วย `python tools/bump_version.py` (แหล่งเดียวคือ `version.py` — ห้ามพิมพ์เลขเวอร์ชันลงไฟล์โค้ดอื่นโดยตรง)

---

## 1. 🎯 สไตล์และปรัชญาการเทรด (Trading Style & Philosophy)

- **ความเชี่ยวชาญเฉพาะทองคำ 100% (XAUUSD Gold Specialist Architecture)**:
  - **XAUUSD (Gold Only)**: โฟกัสเฉพาะสินทรัพย์ทองคำ 100% (ปิด BTCUSD และคู่เงิน Forex ทั้งหมด) เพื่อรวบรวมมาร์จิ้น สมาธิ และคัดกรองเฉพาะชุดแผนเทรดที่สถิติดีที่สุดสำหรับพฤติกรรมทองคำ:
    - 📈 **Plan 1: `MA-Cross-Trend`** (MA5 ตัด MA13 บน M15 + เทรนด์ H1 MA100/150/200 เรียงตัว + กรองสัญญาณหลอก RSI/MA50)
    - 👑 **Plan 2: `MA-Cross-H1-Trend`** (MA5 ตัด MA10 บน H1 + H4 MA10/30 + ความชัน MA5 H4 + ราคาเทียบ MA200 H4)
    - ⚡ **Plan 3: `SMC-LiquidityHunt`** (ดักกวาดสภาพคล่องนอกแนวรับต้าน H1 + กรองเทรนด์ H1 100%)
    - 🎯 **Plan 4: `SR-SwingBounce`** (เด้งแนวรับต้าน H1 พร้อม Divergence Confluence)
    - 🌊 **Plan 5: `BB-H1-Reversion`** (ดักจังหวะหลุดกรอบ Bollinger Bands H1 พร้อม Divergence + MACD Exhaustion)
- **สไตล์การเทรดแบบปรับตัวตามสภาวะตลาด (Market Regime Adaptation)**:
  - **Trending Market (ตลาดมีแนวโน้มชัดเจน)**: บังคับ **Strict Pro-Trend 100%** เทรดฝั่งเดียวกับเทรนด์ H4 MA เท่านั้น ห้ามสวนเทรนด์เด็ดขาดเพื่อตัดการรับมีด
  - **Sideway / Range-Bound Market (ตลาดแกว่งตัวในกรอบ)**: เมื่อ `|h4_diff_pct| < 0.20%` สลับสู่โหมด Range Play อนุมัติการเข้าเทรดได้ทั้ง BUY และ SELL
- **Zero Emotion & Realistic Asymmetric RRR (Sweet Spot)**:
  - อัตราผลตอบแทนต่อความเสี่ยง **RRR 1:1.50** สำหรับแผนที่มี TP ชัดเจน (Plan 3, 4, 5)
  - SL ตามแผน: **Plan 1 = 1.0 ATR (M15)** · **Plan 2 = 0.75 ATR (H1)** · **Plan 3–5 = 0.75 ATR (M15)** — ให้พื้นที่ราคาหายใจ ไม่โดนไส้เทียนสะบัด
  - **ปรับทีละแผนและทดสอบย้อนหลังก่อนเสมอ** — ตั้งแต่ 6 ต.ค. 2026 ผู้ใช้ปรับเฉพาะแผนที่ระบุชื่อ (เริ่มที่ Plan 1) แผนอื่นห้ามแตะจนกว่าผู้ใช้จะสั่ง
  - แผนรันเทรนด์ **Plan 1 (M15)** และ **Plan 2 (H1)** ไม่ต้องตั้ง TP เพื่อ Let Profit Run เต็มรอบ และตัดรอบด้วย **Opposite MA Crossover Exit**

---

## 2. 🧠 สกิลและทักษะหลักของระบบ (Core Skills & Competencies)

1. **Pure Gold Focus Engine**: มุ่งเน้นวิเคราะห์พฤติกรรมราคาทองคำ XAUUSD โดยเฉพาะ ไม่กระจายมาร์จิ้น
2. **Candle Wick & Divergence Analytics (SMC + Momentum)**: ตรวจสอบความยาวไส้เทียน (`lower_wick_ratio`, `upper_wick_ratio` $\ge 0.30$) ผสานกับระบบตรวจจับ **RSI Divergence 4 มิติ** (Regular & Hidden Bullish/Bearish)
3. **H1 Bollinger Bands & MACD Exhaustion Edge**: อ้างอิงกรอบความผันผวนใหญ่ระดับวันจาก Timeframe H1 (SMA 20, 2 STD) ผสานการยืนยันการหมดแรงของโมเมนตัมด้วย **H1 MACD Histogram Exhaustion** ดัน Win Rate แตะระดับสูง
4. **M15 MA Crossover with H1 Trend Anchor (Plan 1)**: ระบบตรวจจับ MA5 ตัด MA13 บน M15 เมื่อ H1 MA100/MA150/MA200 เรียงตัวตามทิศ (ขาลง MA100<150<200 / ขาขึ้น MA100>150>200)
5. **H1 MA Crossover with H4 Trend Anchor (Plan 2)**: ระบบตรวจจับ MA 5 ตัดขึ้น/ตัดลง MA 10 บน H1 พร้อมบังคับให้สอดคล้องกับเทรนด์ใหญ่ H4 (MA10 vs MA30) ปล่อยให้กำไรวิ่งรอบสวิงใหญ่ระดับหลายร้อยจุด
6. **H1 Trend Confluence on SMC Liquidity Hunt**: บังคับให้ Plan 3 เทรดตามทิศทางหลักของแท่งเทียนชั่วโมง H1 เสมอ (BUY เมื่อ H1 Uptrend, SELL เมื่อ H1 Downtrend) ตัดการรับมีดตก 85%
7. **Continuous AI Retraining**: Random Forest (100 ต้น, ลึก 5) รีเทรนทุก 24 ชั่วโมงด้วย M15 5,000 แท่ง · **ทายทิศราคาล่วงหน้า 2 ชั่วโมง (8 แท่ง)** · Features 24 ตัวปรับด้วย ATR (`build_ai_features()`) ใช้ H1/H4 จากแท่งที่ปิดแล้ว (ไม่มีข้อมูลอนาคต) และทายจากแท่ง M15 ที่ปิดแล้ว · วัดผลกับ Holdout 20% ทุกครั้งที่เทรน แสดง `[AI QUALITY]` ใน Console · Walk-forward 2.5 ปี: AUC 0.515 → 0.525, แม่นตอนมั่นใจ 52.7% → 54.0% (ทองทายทิศยาก — AI เป็นตัวยืนยันประกอบ ไม่ใช่ตัวตัดสินหลัก)
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
18. **MT5 Trade History (Paired Deals)**: ดึงประวัติจาก MT5 โดยตรง จับคู่ Deal เข้า/ออกด้วย `position_id` แสดงหน้าละ 10 รายการ พร้อมสรุปชนะ/แพ้/กำไรสุทธิ 90 วัน (Desktop) และ `trade_logs` แบ่งหน้า (เว็บ)
19. **Economic Calendar Awareness**: ปฏิทินเศรษฐกิจรายสัปดาห์ (เวลาไทย) กรอง USD/ผลกระทบ และนับถอยหลังข่าว USD ผลกระทบสูงถัดไป (NFP/CPI/FOMC) ทั้งใน Desktop และหน้า `/calendar` บนเว็บ
20. **Smart Console (Event-Colored Log)**: `console_format.py` ซ่อนข้อความไม่จำเป็น ย่อบล็อกสแกน 10 บรรทัดเหลือ 1 บรรทัด แยกสีตามเหตุการณ์ (BUY/SELL/TP/SL/Exit/Lock/Error) กรองข้อความซ้ำ 5 นาที และอธิบาย error MT5 เป็นภาษาไทย
21. **Secure Remembered Login**: จดจำอีเมล/รหัสผ่านล่าสุดเมื่อติ๊ก "จดจำ" โดยเข้ารหัสด้วย Windows DPAPI (`secure_store.py`) และเก็บข้อมูลผู้ใช้ทั้งหมดใน `%APPDATA%\GoldBot24` ให้อยู่รอดเมื่ออัปเดตโปรแกรม
22. **News Impact on Gold (`news_impact.py`)**: แท็บปฏิทินข่าวมีคอลัมน์ "ผลต่อทอง" สำหรับข่าว USD กลาง/สูง — ทิศทางจากกฎเศรษฐกิจตามประเภทข่าว (`classify`: ตัวเลขสูงกว่าคาด = ดอลลาร์แข็ง = ทองลง ยกเว้นข่าวว่างงาน/Jobless Claims กลับทิศ · สุนทรพจน์/FOMC ขึ้นกับท่าที) + แนวโน้มก่อนข่าวออกจาก Forecast เทียบ Previous · ขนาดการขยับ = ค่ากลาง |%| ของทองใน 60 นาที ณ วัน/เวลานิวยอร์กเดียวกันย้อนหลัง ~2 ปีจาก MT5 M15 (แปลงเวลา DST สหรัฐ/ยุโรปเองไม่พึ่ง tzdata) · ข่าวที่ผ่านไปแล้ว ≥ 60 นาทีวัด "ผลจริง" จากราคา MT5 แล้วสะสมใน `%APPDATA%\GoldBot24\news_history.json` — ข่าวชื่อเดียวกันครบ 3 ครั้งใช้สถิติของข่าวนั้นแทน · คลิกข่าวเปิด `NewsImpactDialog` (feed ไม่มีตัวเลข Actual จึงวัดผลจากราคาทอง)
23. **Clickable Metric Cards**: การ์ด "ยอดเงินในพอร์ต" → `PnlHistoryDialog` กราฟแท่งกำไร/ขาดทุนสุทธิรายวันทั้งบัญชี (`bot_ctrl.get_daily_pnl`, เวลาไทย, เลือก 7/14/30 วัน/เดือนนี้/90 วัน หรือกำหนดวันที่เอง, เกิน 62 วันรวมรายสัปดาห์) · การ์ด "ราคาทองคำ" → `GoldCandleDialog` แท่งเทียน M15 เรียลไทม์ (เลือก 16–500 แท่ง ค่าเริ่มต้น 120) + MA5/MA13 + เส้น Bid/Ask/Spread + ไม้ที่เปิดอยู่ (ราคาเข้า·Lot·กำไร, TP, SL) + กำไร/ขาดทุนรวม อัปเดตทุก 1 วินาที · ขยายเต็มจอได้ (ปุ่ม/F11/Esc) (`bot_ctrl.get_live_candles`)
24. **AI Outlook (`ai_outlook.py`)**: แท็บ "AI คาดการณ์" (ดีไซน์: แถบสรุปหลักสีตามทิศ + ไอคอนวาดเอง · การ์ด 3 ช่วงเวลาตัวเลข % ใหญ่ + บาร์ขึ้น/ลง + ป้ายชัด/ไม่ชัด · ปัจจัยเป็นแถวสลับสีพร้อมป้าย ▲ขึ้น/▼ลง/•กลาง และสรุปจำนวน · ปุ่มรีเฟรชมาตรฐาน `_refresh_button` "↻ รีเฟรช") — Random Forest แยก 3 ระยะ (1 ชม./4 ชม./1 วัน) จาก Features 24 ตัวของบอท เทรนใหม่ทุก 6 ชม. อัปเดตทุก 1 นาที (เธรดเบื้องหลัง) + ปัจจัยประกอบ (เทรนด์ H1 MA100/150/200, H4 MA10/30, MA200 H4, MA5/13+RSI M15, แนวรับ/ต้าน H1, ข่าว USD สูงใน 24 ชม.) · แสดง "แม่นในอดีต" จาก Walk-forward 2.5 ปี (`BACKTEST_ACC`): 1 วัน + AI ≥60% + เทรนด์ตรงกัน = 63.7%, 1 ชม. ≈ 52% (ใกล้เดาสุ่ม) — ทิศ "ไม่ชัด" เมื่อ AI < 55%
25. **Web = Desktop Data**: Telemetry `radar_signals[0]` ส่ง `outlook` / `news` (`news_impact.publish`) / `candles` (M15 16 แท่ง + `label` เวลาไทย — บนเว็บแสดง 16 แท่งเสมอ) / `daily_pnl` (14 วัน) — หน้าพอร์ตสดแสดงการ์ด AI คาดการณ์, แท่งเทียน M15, กำไรรายวัน, ข่าว+ผลต่อทอง (`components/LiveInsights.jsx`) และหน้า `/calendar` เพิ่มคอลัมน์ "ผลต่อทอง" เมื่อล็อกอิน · ประวัติการเทรดบนเว็บแสดงเวลาถือไม้ (จับคู่ OPEN_* กับ CLOSE/TP_HIT/SL_HIT ด้วย ticket ใน `/api/user/trades`)
26. **Console Auto-Clear**: ล้างคอนโซลอัตโนมัติทุก 1 ชม. (ค่าเริ่มต้นเปิด ปิดได้ จำใน `bot_settings.json` คีย์ `console_autoclear` — `_save_setting` รวมค่ากับ `lot` ไม่ทับกัน) · ประวัติการเทรดในโปรแกรมหน้าละ 10 รายการ
27. **User Plan Selection + $ Take Profit**: ผู้ใช้ติ๊กเลือกแผนที่ใช้ในการ์ดแผนเทรด (`plan_config.user_enabled/set_user_enabled` → `bot_settings.json` คีย์ `user_plans[email]`; `is_enabled` = แอดมินเปิด และ ผู้ใช้เลือก; แผนที่แอดมินปิดติ๊กไม่ได้) · "ปิดไม้เมื่อกำไรถึง $X" (`tp_usd_enabled`/`tp_usd`, ค่าเริ่มต้นปิด) บอทปิดทุกไม้ของบอทเมื่อ profit+swap ≥ X (`[TAKE PROFIT $]`) · ปุ่มเติมคีย์ถูกซ่อน · เรียกชื่อโปรแกรมว่า "โปรแกรม AI Gold Commander Pro" ทั้งเว็บและโปรแกรม
28. **Self-Updating Release Channel**: ตรวจเวอร์ชันใหม่อัตโนมัติเบื้องหลัง (ทุก 6 ชม.) จาก `/api/release` ← GitHub Releases และแจ้งเป็นป้ายบนแถบหัวโปรแกรม
29. **Close-Reason History**: ประวัติการเทรดในโปรแกรมมีคอลัมน์ "ปิดโดย" จาก `deal.reason` + คอมเมนต์ Deal ปิด (`MainTradingApp._close_reason`): 🎯 ชน TP · ⛔ ชน SL · 🔒 ชน SL (ล็อกกำไร) · 💰 ถึงเป้ากำไร $ · 🤖 บอทปิด (MA ตัดกลับ / AI กลับทิศ) · ✋ ปิดเอง (ในโปรแกรม / MT5) · ⚠ Stop Out
30. **Live Plan Markers + Totals**: แถว "รวมทุกแผน" ท้ายการ์ด (ไม้รวม · WR = ชนะรวม/ไม้รวม · กำไรรวม) · การ์ดแผนเทรดแสดงแผนที่ถือไม้อยู่ — ชื่อแผนเป็นสีเขียว + ป้าย ● BUY / ● SELL (สีตามกำไร/ขาดทุน, ×N เมื่อหลายไม้) อัปเดตทุก 2 วินาที (`_plan_live_tick`)
31. **Readable Market Cards**: การ์ดสภาวะตลาดใช้คำ ▲ Uptrend / ▼ Downtrend / ◆ Sideway + ลำดับเส้น `50<100<150` (แดง = เรียงลง), `50>100>150` (เขียว = เรียงขึ้น), สลับกัน (ฟ้า = ไซด์เวย์) ต่อท้ายแต่ละแถว (`_ma_order_tick`: เธรดอ่าน MT5 ทุก 30 วิ เธรดหลักรับผลทุก 1 วิ — ห้ามเรียก Tk จากเธรดอื่น) · การ์ดแนวรับ–แนวต้าน H1 (ซ้าย) | H4 (ขวา): ▲ ต้าน ราคา / บาร์สีระยะห่าง (เขียว = แนวรับ→ราคา · แดง = ราคา→แนวต้าน · จุดทอง = ราคาปัจจุบัน) / ▼ รับ ราคา
33. **Thai News Titles (`news_th.py`)**: พจนานุกรมแปลชื่อข่าวเศรษฐกิจเป็นภาษาไทยในเครื่อง (ชื่อเต็ม → รูปแบบผู้กล่าวสุนทรพจน์ → แปลทีละวลี + ประเทศ + ช่วงเวลา m/m, y/y, q/q) · ชี้ชื่อข่าวในปฏิทินแสดง `HoverTip` ภาษาไทย · หน้าต่างรายละเอียดข่าวแสดงชื่อไทย · Telemetry ส่ง `title_th` → เว็บแสดงเมื่อชี้/เปิดรายละเอียด (Tk แสดงอีโมจีธงไม่ได้ — ห้ามใส่ 🇹🇭 ในโปรแกรม)
34. **Market Explain Dialog**: คลิกการ์ดสภาวะตลาด → `MarketExplainDialog` แสดงค่า MA50/100/150 ของ H1/H4 (แท่งปิด) พร้อมเหตุผลว่าทำไมเป็น Uptrend/Downtrend/Sideway และกฎที่แต่ละแผนใช้จริง (P1: H1 MA100/150/200 · P3–5: H4 MA10/30 ±0.20% · P2: ราคา H4 เทียบ MA200) (`bot_ctrl.get_market_explain`) · แผงควบคุมรวม Lot + "ปิดเมื่อกำไรถึง" ไว้บรรทัดเดียว (`_HintProxy` แสดง ✓/✗ ต่อท้ายแทนป้ายแยก) เพื่อให้การ์ดแผนเทรดไม่ล้นจอ
35. **Quick Manual Entry**: ปุ่ม ▲ BUY / ▼ SELL ในแผงควบคุม → `QuickOrderDialog` ยืนยันก่อนส่ง (ราคาสด, Lot ที่ตั้งไว้, SL ค่าเริ่มต้น 1.0 ATR M15, TP 1.5 เท่า หรือไม่ตั้ง TP, แสดงเงินเสี่ยง/เป้า) → `bot_ctrl.quick_order()` ใช้ `send_order` ตัวเดียวกับบอท (comment `Manual-Quick`, ต้องล็อกอิน + มีชั่วโมง) · บอทดูแลไม้ต่อด้วยล็อกกำไร/AI กลับทิศ/ปิดเมื่อกำไรถึง $ · มุมขวาบนเป็นป้ายสีทองชื่อผู้ใช้เต็ม (คลิกเปิดเมนู)
32. **Styled Update Dialog**: แจ้งเวอร์ชันใหม่ด้วย `UpdateDialog` (ป้าย ใช้งานอยู่ → ใหม่, Release notes แยกหัวข้อ `###`, ปุ่มดาวน์โหลด) แทน messagebox

---

## 3. 📋 แผนการเทรดเฉพาะทองคำ (XAUUSD Trading Plans)

```
┌────────────────────────────────────────────────────────────────────────┐
│                   XAUUSD (GOLD) EXCLUSIVE SUITE                        │
├────────────────────────────────────────────────────────────────────────┤
│ 📈 Plan 1: MA-Cross-Trend (MA5 x MA13 M15 + H1 MA100/150/200)         │
│ 👑 Plan 2: MA-Cross-H1-Trend (MA5 x MA10 H1 + ตัวกรองเทรนด์ใหญ่ H4)   │
│ ⚡ Plan 3: SMC-LiquidityHunt (กวาดสภาพคล่องแนวรับ/ต้าน H1 + เทรนด์ H1)    │
│ 🎯 Plan 4: SR-SwingBounce (เด้งโซนแนวรับ/ต้าน H1 + RSI Divergence)     │
│ 🌊 Plan 5: BB-H1-Reversion (เด้งขอบแบนด์ H1 2STD + MACD Confluence)    │
└────────────────────────────────────────────────────────────────────────┘
```

### 🔹 Plan 1: `MA-Cross-Trend` (กำหนดโดยผู้ใช้ 5 ต.ค. 2026 — 2 กฎ)
* **เงื่อนไข SELL**: (1) เทรนด์ H1 ขาลงยืนยัน **MA100 < MA150 < MA200** (แท่งที่ปิดแล้ว) **และ** (2) **MA5 ตัดลงใต้ MA13** บนแท่ง M15 ที่ปิดแล้ว
* **เงื่อนไข BUY**: (1) **MA100 > MA150 > MA200** บน H1 **และ** (2) **MA5 ตัดขึ้นเหนือ MA13** บน M15
* **ตัวกรองสัญญาณหลอก (6 ต.ค. 2026)**: แท่ง M15 ที่ปิดแล้วต้องมี **RSI(14) 50–70 สำหรับ BUY / 30–50 สำหรับ SELL** และ **ราคาปิดอยู่ฝั่งเดียวกับ MA50 M15** (BUY เหนือ / SELL ใต้) — ไม่ผ่านพิมพ์ `[FAKE SIGNAL FILTER]` · Backtest 2.5 ปี: ไม้ 2027 → 739, PF 1.16 → 1.37, Max DD 245 → 92, กำไร 850 → 690 จุด (กำไรทุกไตรมาส) · ทดสอบแล้วไม่ช่วย: ADX, ความชัน MA5, ระยะห่าง MA, ขนาดแท่ง, รอแท่งยืนยัน, ATR ต่ำ
* **ออกไม้**: MA5 ตัด MA13 กลับขั้วตรงข้ามบน M15 ➔ ปิดทันที (ไม่ตั้ง TP)
* **ความเสี่ยง**: **SL คงที่ 1.0 ATR (M15)** (`P1_SL_ATR_MULT`, 6 ต.ค. 2026 — Backtest 0.5/0.75/1.0/1.25/1.5/2.0/2.5 ATR: 1.0 ดีที่สุด กำไร 690 → 931 จุด, PF 1.37 → 1.44, ชนะ 32% → 35%, Max DD 92 → 131; ≥ 1.5 ATR กำไรลด DD เพิ่ม) · เดิม 0.75 ATR (Backtest กับกฎนี้: กำไร 241 → 898 จุด, Max DD 634 → 346 เทียบ Swing SL)
* **เลื่อน SL แบบขั้นบันได (Step Trailing)**: ทุกกำไร 5 จุด (= $5 ที่ 0.01 lot) วัดระยะ SL → ราคา แล้วเลื่อน SL เข้าหาราคา **40%** (`apply_p4_step_trailing`, จำขั้นไว้ใน `%APPDATA%\GoldBot24\p4_trail_state.json`) · Backtest: กำไร 898 → 885, PF 1.13 → 1.17, Max DD 346 → 245 (ผู้ใช้เสนอ 60% — ทดสอบแล้วกำไรลด 54% จึงเลือก 40%)
* ยังใช้ Cooldown / Circuit Breaker / Loss Block ตามปกติ · ไม่ใช้ตัวกรอง H4 และไม่ใช้ AI
* **หมายเหตุ Backtest 2.5 ปี** (ผู้ใช้เลือกใช้กฎนี้แทนชุดเดิมโดยรับทราบผล): กำไร 241 จุด, PF 1.03, Max DD 634 เทียบกฎชุดก่อน 1834 จุด / DD 197 — ทางเลือกที่ทดสอบแล้วดีกว่า: กฎเดิม + MA13 + MA100/150/200 (กำไร 1797, DD 117)

### 🔹 Plan 2: `MA-Cross-H1-Trend` (ปรับกลับเป็นชุดที่ Backtest ดีที่สุด — 6 ต.ค. 2026)
* **เงื่อนไข BUY**: MA5 ตัดขึ้น MA10 บน H1 (แท่งปิด) **และ** H4 MA10 > MA30 (Strict Pro-Trend; ไซด์เวย์ต้องเอียงขึ้น) **และ** MA5 H4 ชันขึ้น (เทียบ 2 แท่ง) **และ** ราคาปิด H4 อยู่เหนือ MA200
* **เงื่อนไข SELL**: กลับกันทั้งหมด (MA5 ตัดลง MA10 · H4 MA10 < MA30 · MA5 H4 ชันลง · ราคาใต้ MA200)
* **ออกไม้**: MA5 ตัด MA10 กลับขั้วบน H1 · **SL 0.75 ATR (H1)** · ไม่ตั้ง TP · **ไม่เลื่อน SL** (ทดสอบแล้วการเลื่อน SL ทุกขนาดทำให้ Plan 2 แย่ลง)
* **Backtest 2.5 ปี**: กำไร **+1113 จุด**, PF 1.59, Max DD 219 (กำไรทั้ง 2 ครึ่ง) — เทียบหลักการแบบ Plan 1 (H4 MA100/150/200 + MA13 + เลื่อน SL $5) ที่ −186 จุด

### 🔹 Plan 3: `SMC-LiquidityHunt` (กวาดสภาพคล่อง + เทรนด์ H1 Confluence)
* **จุดประสงค์**: ดักเก็บจังหวะ Fakeout ที่ราคากวาด Stop Loss นอกแนวรับ/ต้าน แล้วดึงกลับ โดยต้องสอดคล้องกับเทรนด์ใหญ่ H1 เท่านั้น
* **เงื่อนไข BUY**: `Low < Support H1` และ `Close >= Support H1` พร้อมไส้ล่าง `lower_wick_ratio >= 0.30` + **เทรนด์ H1 ต้องเป็น Uptrend (`H1 MA10 > MA30`)** + AI UP $\ge 50\%$ *(หากมี Bullish Divergence ลดเกณฑ์ AI เป็น $\ge 48\%$)*
* **เงื่อนไข SELL**: `High > Resistance H1` และ `Close <= Resistance H1` พร้อมไส้บน `upper_wick_ratio >= 0.30` + **เทรนด์ H1 ต้องเป็น Downtrend (`H1 MA10 < MA30`)** + AI DOWN $\ge 50\%$ *(หากมี Bearish Divergence ลดเกณฑ์ AI เป็น $\ge 48\%$)*
* **ความเสี่ยง/เป้าหมาย**: SL = 0.75 ATR | TP = RRR 1:1.50 (1.125 ATR)

### 🔹 Plan 4: `SR-SwingBounce` (เด้งแนวรับ-ต้าน + Divergence Confluence)
* **จุดประสงค์**: เข้าออเดอร์ตามรอบการแกว่งตัวในกรอบแนวรับ/ต้านหลัก H1 (Mean Reversion - Win Rate 53.3% - 57.1%)
* **เงื่อนไข BUY**: ราคาแตะโซนแนวรับ (`|Close - Support| <= 1.0 ATR`) + สัญญาณแท่งเทียนปฏิเสธราคา + **ต้องมี Bullish/Hidden Bullish Div Confluence** + AI UP $\ge 51\%$
* **เงื่อนไข SELL**: ราคาแตะโซนแนวต้าน (`|Resistance - Close| <= 1.0 ATR`) + สัญญาณแท่งเทียนปฏิเสธราคา + **ต้องมี Bearish/Hidden Bearish Div Confluence** + AI DOWN $\ge 51\%$
* **ความเสี่ยง/เป้าหมาย**: SL = 0.75 ATR | TP = RRR 1:1.50 (1.125 ATR)

### 🔹 Plan 5: `BB-H1-Reversion` (เด้งขอบแบนด์ H1 + Divergence + MACD Exhaustion)
* **จุดประสงค์**: ดักจังหวะราคาทองคำหลุดกรอบความผันผวนใหญ่ระดับวันของ H1 (SMA 20, 2 STD) แล้วถูกปฏิเสธดีดกลับเข้าหากึ่งกลาง ผสานการยืนยันการหมดแรงของโมเมนตัมด้วย MACD (**Win Rate สูงถึง 66.7% - 75.0%**)
* **เงื่อนไข BUY**: `Low < Lower Band H1` และ `Close >= Lower Band H1` พร้อมไส้ล่าง `lower_wick_ratio >= 0.20` + **RSI Divergence Confluence** + **MACD Histogram H1 เริ่มยกตัวขึ้น (Exhaustion)** + AI UP $\ge 50\%$
* **เงื่อนไข SELL**: `High > Upper Band H1` และ `Close <= Upper Band H1` พร้อมไส้บน `upper_wick_ratio >= 0.20` + **RSI Divergence Confluence** + **MACD Histogram H1 เริ่มกดตัวลง (Exhaustion)** + AI DOWN $\ge 50\%$
* **ความเสี่ยง/เป้าหมาย**: SL = 0.75 ATR | TP = RRR 1:1.50 (1.125 ATR)
* **เลื่อน SL ทุก $5 (6 ต.ค. 2026 — ผู้ใช้เลือก)**: ใช้ `apply_p4_step_trailing` เหมือน Plan 1 — ทุกกำไร 5 จุด เลื่อน SL เข้าหาราคา 40% (ทำงานร่วมกับ Early Profit Lock 70% / Dynamic TP 80% — SL ขยับเฉพาะทิศที่ดีขึ้น) · Backtest มีเพียง ~32 ไม้ใน 2.5 ปี: ไม่เลื่อน +31 จุด PF 1.32 vs เลื่อน $5/40% +17 จุด PF 1.20 (ต่างกัน 2–3 ไม้ สรุปไม่ได้), ขาดทุนเฉลี่ยต่อไม้ลด $5.94 → $4.57

---

### 🔸 แนวรับ/แนวต้าน และสภาวะตลาด (อัปเดต 5 ต.ค. 2026)
* **แนวรับ/แนวต้าน H1 และ H4** (`find_sr_levels`): ดูแท่งที่ปิดแล้วย้อนหลัง **500 แท่ง** → หา Swing High/Low (สูง/ต่ำสุดเทียบ 3 แท่งซ้าย-ขวา) → รวมจุดที่อยู่ในช่วง 0.5 ATR เป็นโซน → แนวรับ = โซนใต้ราคาที่ใกล้ที่สุด, แนวต้าน = โซนเหนือราคาที่ใกล้ที่สุด (เลือกโซนที่ราคาแตะ ≥ 2 ครั้งก่อน) · **Plan 3 (SMC) และ Plan 4 (SR-Bounce) ใช้แนวรับ/ต้าน H1 ชุดนี้** (แทน Low/High 20 แท่งเดิม) · H4 ใช้แสดงผล
* **สภาวะตลาดบนการ์ด (แสดงผลอย่างเดียว)** (`ma_condition`): **MA50 < MA100 < MA150 = ขาลง · MA50 > MA100 > MA150 = ขาขึ้น · แบบอื่น = ไซด์เวย์** ทั้ง H1 และ H4 (ตัวเลข % = ระยะ MA50 เทียบ MA150) · (ป้าย MA100-200 / MA200 เอาออกจากการ์ดแล้ว — ดูในหน้าต่างอธิบาย) · ป้ายมุมขวา = ทิศที่ Plan 3–5 อนุญาต (H4 MA10/30 Strict Pro-Trend)

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
   - Plan 1/2 ตรวจ MA Cross จาก**แท่งที่ปิดแล้ว** (`iloc[-2]` เทียบ `iloc[-3]`) ไม่ใช้แท่งที่ยังวิ่งอยู่
   - **Cross-Bar Re-entry Guard**: จดเวลาแท่ง Cross ที่เข้าไม้แล้วใน `last_cross_entry_bar[(sym, plan, direction)]` — ห้ามเข้าซ้ำบนแท่ง Cross เดิม (สัญญาณค้างตลอดอายุแท่ง 15 นาที/1 ชม.)
5. **Timeframe-Matched Safety SL**:
   - Plan 2 ใช้ **ATR(14) ของ H1 จริง** (แท่งที่ปิดแล้ว) × 0.75 — ถ้าข้อมูลไม่พอจึงใช้ ATR M15 × 2 เป็นค่าสำรอง
6. **Single-Count Close Accounting**:
   - ไม้ที่บอทปิดเองผ่าน `close_position()` ถูกจดใน `_self_closed_tickets` เพื่อไม่ให้ส่วนตรวจจับ SL/TP นับขาดทุน/Circuit Breaker/สถิติซ้ำ
   - ทิศของไม้ที่ปิด = **ฝั่งตรงข้ามของ Deal ปิด** (ปิด BUY คือ Deal SELL) — ใช้กำหนด Same-Plan Loss Block ให้ถูกทิศ
7. **Unified Close Path**:
   - ปิดไม้ทุกช่องทาง (AI Reversal, MA Cross Exit, Take Profit $, ปุ่มปิดทีละไม้, ปุ่มปิดทุกออเดอร์) ผ่าน `close_position()` เดียว — เลือก filling mode ตามโบรกเกอร์ และบันทึก `trade_logs`/สถิติครบ · คอมเมนต์ปิดไม้ต้องสื่อความหมาย (ใช้แยกเหตุผลการปิดในประวัติ)
8. **Step Trailing SL (Plan 1 + Plan 5)**:
   - `apply_p4_step_trailing`: ทุกกำไร 5 จุด (= $5 ที่ 0.01 lot) เลื่อน SL เข้าหาราคา 40% ของระยะ SL → ราคา · จำขั้นใน `p4_trail_state.json` · SL ขยับเฉพาะทิศที่ดีขึ้นและเคารพ stops level ของโบรกเกอร์
9. **Take Profit by USD (ผู้ใช้ตั้งเอง)**:
   - ติ๊ก "ปิดไม้เมื่อกำไรถึง $X" ที่แผงควบคุม → บอทปิดทุกไม้ของบอท (magic 888999) เมื่อ profit + swap ≥ X ก่อนกฎอื่นทั้งหมด (`take_profit_usd()`, `[TAKE PROFIT $]`)
10. **Fake-Signal Filter (Plan 1)**:
   - แท่ง M15 ที่ปิดแล้วต้องมี RSI 50–70 (BUY) / 30–50 (SELL) และราคาปิดฝั่งเดียวกับ MA50 M15 — ไม่ผ่านพิมพ์ `[FAKE SIGNAL FILTER]` ครั้งเดียวต่อแท่ง
11. **Plan Gate 2 ชั้น**:
   - `plan_config.is_enabled()` = แอดมินเปิด (เว็บ `/admin/plans`) **และ** ผู้ใช้เลือกใช้ (ติ๊กในการ์ดแผนเทรด) · ข้อความ `[PLAN DISABLED]` บอกว่าใครปิด

---

## 5. 🛡️ เกราะป้องกันความเสี่ยง (Risk Management Protocols)

| กฎการควบคุมความเสี่ยง | พารามิเตอร์ | วัตถุประสงค์ |
| :--- | :--- | :--- |
| **Breathing Room SL** | P1 `1.0 ATR` · P2 `0.75 ATR (H1)` · P3–P5 `0.75 ATR` | ให้พื้นที่ราคาหายใจ ป้องกันไส้เทียนสะบัดกิน SL |
| **Sweet Spot RRR** | `1:1.50` | สร้างความสมดุลระหว่าง Win Rate สูง (45-50%) และกำไรสุทธิ |
| **Strict Pro-Trend** | บล็อกสวนเทรนด์ 100% | ห้ามเข้าออเดอร์สวนทิศ H4 MA เด็ดขาดเมื่อตลาดมีแนวโน้ม |
| **Asset Specialization** | คัดแผนเฉพาะทาง | นำแผน Breakout ออกจากระบบ (กับดัก False Breakout ของทองคำ) และใช้เฉพาะ 5 แผนที่สถิติดี |
| **Circuit Breaker** | ขาดทุนติดกัน 2 ไม้ ➔ พัก 60 นาที | ป้องกัน Drawdown รุนแรงในสภาวะตลาดผิดปกติ (นับไม้ละ 1 ครั้งเท่านั้น — ดูเทคนิคข้อ 6) |
| **Same-Plan Loss Block** | บล็อกทิศเดิม 60 นาทีเมื่อแพ้ | ป้องกันการเข้าซ้ำสวนแนวโน้มที่กำลังวิ่งแรง (ปลดล็อกเมื่อชนะ) |
| **Margin per Trade** | $400 ต่อ 1 ไม้ที่ 0.01 lot (ปรับตามขนาดไม้ที่ตั้ง) | คุมขนาดพอร์ตและป้องกัน Overtrading / Margin Call |
| **Cooldown Rest** | BTC 15 นาที / XAU 10 นาที | พักรอบแท่งเทียนป้องกันอาการ Whipsaw หลังปิดออเดอร์ |
| **Cross-Bar Guard** | 1 ไม้ ต่อ 1 แท่ง Cross | Plan 1/2 ห้ามเข้าซ้ำบนสัญญาณ Cross เดิมหลัง Cooldown หมด |
| **News Awareness** | นับถอยหลังข่าว USD ผลกระทบสูง + ผลต่อทอง | เตือนช่วงสเปรดกว้าง/ราคาสะบัดแรง 15–30 นาทีรอบข่าว · AI คาดการณ์เตือนข่าวแรงใน 24 ชม. |
| **Step Trailing** | ทุก +5 จุด เลื่อน SL 40% (P1, P5) | ล็อกกำไรเป็นขั้น ลดการคืนกำไรเมื่อราคากลับตัว |
| **Take Profit $ (ผู้ใช้)** | ปิดเมื่อกำไร ≥ $X (ค่าเริ่มต้นปิด) | ให้ผู้ใช้กำหนดเป้ากำไรต่อไม้เอง |
| **User Plan Selection** | ผู้ใช้เลือกแผนที่ใช้ (จำแยกตามบัญชี) | เปิดเฉพาะแผนที่ผู้ใช้เชื่อมั่น ภายใต้แผนที่แอดมินอนุญาต |

---

## 6. 🐂🐻 ตัวกรองเทรนด์ใหญ่ H4 (Strict Pro-Trend Confluence)

> **อ่านเทรนด์จากแท่งที่ปิดแล้วเท่านั้น** (`closed_trend()` — ไม่ใช้แท่งที่กำลังวิ่งซึ่ง Repaint ตามราคา) และกำหนด **ทิศเทรนด์ยืนยัน** (`h1_dir` / `h4_dir`): +1 = MA10 > MA30 และ MA10 ไม่สวนทางเกิน 0.1 ATR (เทียบ 3 แท่งก่อน, `TREND_SLOPE_TOL_ATR`), −1 = MA10 < MA30 และไม่สวนทางเกิน 0.1 ATR, 0 = MA10 สวนทางชัด (เทรนด์ชะลอ — การ์ดแสดง "· ชะลอ" สีทอง) · Backtest tol 0 → 0.1: P4 กำไร 1336 → 1463, P5 991 → 1107
> - Plan 1 ใช้เฉพาะ H1 MA100/150/200 เรียงตัว (ดูหัวข้อ Plan 1) · Plan 2 ต้องมี `h4_dir_p5` ตรงทิศเสมอ (H4 MA10 vs MA30 + **ความชัน MA5 H4 เทียบ 2 แท่งก่อน** — Backtest: กำไรเท่าเดิม, PF 1.38 → 1.58, DD 255 → 219)
> - **เทรนด์ระยะยาว 200 แท่ง** (`long_term_dir()`, ดึงข้อมูล H1/H4 ครั้งละ 300 แท่ง): Plan 1 ต้องให้ **H1 MA50 เทียบ MA200** ตรงทิศ · Plan 2 ต้องให้ **ราคาปิด H4 เทียบ MA200** ตรงทิศ — Backtest: Plan 1 กำไร 1228 → 1336 จุด / DD 264 → 188 · Plan 2 กำไร 767 → 991 จุด / DD 315 → 268 · ดูค่าได้ในหน้าต่างอธิบายสภาวะตลาด (คลิกการ์ด)
> - Backtest 2.5 ปี (เทียบแบบเดิมที่อ่านแท่งที่กำลังวิ่ง): Plan 1 กำไร 816 → 1228 จุด, PF 1.10 → 1.24, Max DD 413 → 264 · Plan 2 กำไร 555 → 767 จุด, PF 1.10 → 1.20

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
| **Hours Metering** | Desktop หักเวลาในเครื่องแล้วส่งยอดให้ `/api/auth/meter` หักจริงบน Server ทุก ~1 นาที (เว็บดึงชั่วโมงใหม่ทุก 60 วินาที) — ห้าม PATCH `bot_config.lot_size` ตรงจาก Client |
| **Register** | ยืนยันอีเมลด้วยรหัส 6 หลักก่อนสร้างบัญชี (ตอบข้อความเดียวกันเสมอ ถ้ามีบัญชีอยู่แล้วส่งอีเมลแจ้งเจ้าของแทน — กันสุ่มหาอีเมล) · สมาชิกใหม่รับฟรี 48 ชม. รหัสผ่านเข้ารหัส PBKDF2-HMAC-SHA256 |
| **Admin RBAC** | `Admin Analytics` (Navbar/Footer/หน้า `/admin/analytics`) แสดงเฉพาะ Admin เท่านั้น ห้ามเปิดเผยสถิติทุกลูกค้าและเครื่องผลิต Promo Key ต่อลูกค้าทั่วไป · แอดมินสลับ **โหมดการดู ผู้ใช้ ↔ แอดมิน** ได้ที่ Navbar (`viewMode` ใน `AuthContext`, จำไว้ใน `localStorage`) — โหมดผู้ใช้ซ่อนเมนูแอดมินทั้งหมด (`isAdminView`) แต่สิทธิ์จริงยังตรวจที่ Server เสมอ |
| **Payment** | ราคา/ชั่วโมงคิดจาก `web/src/lib/packages.js` ฝั่ง Server เท่านั้น · Order ID สุ่มแบบเดาไม่ได้ · PromptPay QR → SlipOK ตรวจสลิป (`log: true` กันสลิปซ้ำ + `amount` ตรวจยอด) → ผลิต Product Key อัตโนมัติ · Webhook ต้องมี `x-webhook-secret` · ห้ามโหมดจำลองบน Production · **QR หมดเวลา 15 นาที** → ซ่อน QR แล้วให้เวลาแนบสลิปต่ออีก **10 นาที** → ครบแล้วยกเลิกคำสั่งซื้อ (`CANCELLED`) จากหน้าร้าน + เก็บกวาดฝั่ง Server เมื่อเกิน 25 นาที (`expireStaleOrders()` ตอนสร้าง QR ใหม่/Cron) · คำสั่งซื้อที่ยกเลิกยังแนบสลิปได้ภายใน 24 ชม. (กันเงินค้างกรณีโอนวินาทีสุดท้าย) · ข้อผิดพลาด SlipOK แปลเป็นข้อความ+คำแนะนำภาษาไทย (`code`, `hint`, `retryAfterSec`) · ปัญหาฝั่งร้าน (แพ็กเกจ/โควตา SlipOK 1000–1004, 1015) แจ้งแอดมินทาง LINE · **ใบเสร็จ**: ชำระสำเร็จ → `issueReceipt()` บันทึกตาราง `receipts` (เลขที่ `GB24-YYYYMM-000001`, 1 คำสั่งซื้อ = 1 ใบ) + ส่งอีเมลผู้ซื้อ · ดู/พิมพ์ที่ `/receipts` (`supabase_receipts_patch_04.sql`) |
| **Database Security** | RLS เปิดทุกตาราง — anon key อ่านตารางผู้ใช้/คีย์/คำสั่งซื้อ/พอร์ตไม่ได้ · Desktop เขียน Telemetry/สถิติผ่าน RPC `bot_upsert_telemetry` / `bot_upsert_plan_stats` (SECURITY DEFINER, เขียนอย่างเดียว) · Migration: `supabase_security_rls.sql` + `supabase_security_rls_patch_01.sql` |
| **Secrets** | ห้าม commit/ส่งคีย์ลับในแชท — ใส่ผ่าน `npx vercel env add <NAME> production --sensitive` · รหัส MT5 อยู่ในเครื่องเท่านั้น (`%APPDATA%\GoldBot24\credentials.json`) ไม่ซิงค์ขึ้น Cloud |
| **Desktop Data Dir** | ไฟล์ผู้ใช้ทั้งหมดผ่าน `app_paths.data_path()` → `%APPDATA%\GoldBot24` (รวม `trade_history.csv`, `trade_modifications.csv`, `signal_history.csv`) (ห้ามเก็บข้างไฟล์ .exe เพราะถูกลบทุกครั้งที่ build) |
| **Desktop GUI Colors** | CustomTkinter รับเฉพาะ Hex `#RRGGBB` — **ห้ามใช้ `rgba()`** (ทำให้ `TclError` โปรแกรมเปิดไม่ขึ้น) |
| **Release Flow** | 1) `python tools/bump_version.py` 2) Smoke Test GUI 3) `python build_dist.py` (ต้องปิดโปรแกรมก่อน ไม่งั้นไฟล์ถูกล็อก) → ได้ทั้ง ZIP และ**ตัวติดตั้ง `GoldBot24_Setup_v<เวอร์ชัน>.exe`** (Inno Setup จาก `installer/goldbot24.iss`: ติดตั้งแบบผู้ใช้ไม่ต้อง Admin, ไอคอน Desktop + Start Menu, อัปเดตทับได้, ไม่ลบ %APPDATA%\GoldBot24 · ติดตั้ง ISCC: `winget install JRSoftware.InnoSetup --scope user`) 4) สร้าง GitHub Release `v<เวอร์ชัน>` แนบ Setup .exe + ZIP + SHA-256 (`/api/release` เลือก Setup เป็นไฟล์หลัก) → หน้า `/download` และการแจ้งอัปเดตในโปรแกรมอัปเดตเอง · Web: `cd web && npm run build` → `git push` (Vercel Root Directory = `web` deploy อัตโนมัติ) · เปลี่ยน env บน Vercel แล้วต้อง redeploy: `cd web && npx vercel redeploy <URL production ล่าสุด> --target production` (โฟลเดอร์ `web` คือที่ link กับ Vercel) |
| **Backtest บนเว็บ** | `python tools/backtest_all.py` (เปิด MT5 ค้างไว้ ~3–4 นาที) → จำลองทุกแผนตามกฎปัจจุบัน 2.5 ปี (AI แบบ Walk-forward) → เขียน `web/public/backtest.json` → หน้า `/backtest` แสดงผลรวม/กราฟกำไรสะสม/รายแผน/รายเดือน · **รันใหม่ทุกครั้งที่เปลี่ยนกฎแผน** แล้ว deploy เว็บ |
| **ขนาดไม้ (Lot)** | ผู้ใช้ตั้งได้ที่แผงควบคุมบอท (ค่าเริ่มต้น 0.01) → `%APPDATA%\GoldBot24\bot_settings.json` · บอทอ่านค่าใหม่ทุกครั้งที่เปิดออเดอร์ (`current_lot()`) · Step Trailing ของ Plan 1 นับเป็นจุดราคา (5 จุด = $5 ที่ 0.01 lot, $10 ที่ 0.02 lot) |
| **บัญชี MT5 บนเว็บ** | Telemetry ส่ง `radar_signals[0].account` (login, server, name, โหมด Demo/Real, leverage, lot) → หน้าพอร์ตสดแสดงแถบบัญชีที่เชื่อมต่อ |
| **Responsive Desktop** | ออกแบบให้พอดีจอ 1366×768 (เปิดเต็มจออัตโนมัติเมื่อจอเล็ก) · Tk แสดงอีโมจีสีไม่ได้ ให้ใช้ Label สี/ป้ายแทน และหลีกเลี่ยงอีโมจี Unicode ใหม่ (เช่น 🪙) ที่ Windows 10 ไม่มี · **ห้ามใช้อักขระลูกศร/สัญลักษณ์พิเศษ** เช่น ⬆ ⬇ ⛶ 🗗 🇹🇭 (บางเครื่องขึ้นเป็นกล่อง □) — ใช้ไอคอนวาดด้วย Canvas หรือข้อความแทน · สัญลักษณ์ที่ใช้ได้: ▲ ▼ ◆ ● • ✓ ✗ › |
| **Tk Grid** | `sticky` ใช้ได้เฉพาะ n/s/e/w — ห้าม `sticky="center"` (TclError) |
| **ไอคอนหน้าต่างย่อย** | `CTkToplevel.__init__` ถูก patch ให้ตั้ง `assets/app_icon.ico` หลังสร้าง 250ms (CustomTkinter ตั้งไอคอนตัวเองทับที่ ~200ms) — หน้าต่างใหม่ทุกอันได้โลโก้เดียวกับโปรแกรมหลักอัตโนมัติ |
| **หน้าต่างกราฟ** | กราฟ (M15, กำไรรายวัน) **ไม่ใช้ `transient()`** เพื่อให้มีปุ่มขยาย/ย่อ + ปุ่ม ⛶ เต็มจอ / F11 / Esc · การ์ดที่คลิกเปิดหน้าต่าง (`_make_clickable`) เปิดได้ **หน้าต่างเดียว** คลิกซ้ำดึงอันเดิมขึ้นมา |
| **ภาษาบนหน้าจอ** | ข้อความหลักภาษาไทย · คำเทรนด์ใช้ภาษาอังกฤษ (Uptrend / Downtrend / Sideway) · ชื่อแผนแบบสั้น `P1 · MA M15` … `P5 · BB-H1` เหมือนกันทั้งโปรแกรมและเว็บ (`web/src/lib/plans.js`) · เรียกโปรแกรมว่า "โปรแกรม AI Gold Commander Pro" (ห้ามใช้คำว่า Desktop ในข้อความถึงผู้ใช้) · ค่าบริการพูดว่า "บาท/ชม." |
| **รูปแบบตัวเลข** | ใส่คอมมา (4,171.83) · กำไรมีเครื่องหมาย +/- · **ค่าเงินในโปรแกรมไม่ใส่สัญลักษณ์ $ ทุกจุด** (ยอดเงิน, Equity/Float, ประวัติ, ออเดอร์, กราฟ, แผนเทรด — ผู้ใช้สั่ง 6 ต.ค. 2026) · เว็บยังใช้ $ ได้ |
| **ข้อมูลเว็บ = โปรแกรม** | ค่าวิเคราะห์ (AI คาดการณ์, ผลข่าว, แท่งเทียน, กำไรรายวัน) คำนวณในโปรแกรมแล้วส่งผ่าน Telemetry เท่านั้น — เว็บห้ามคำนวณซ้ำแยก เพื่อให้ตัวเลขตรงกัน |
| **ทดสอบ GUI** | Smoke test ด้วยการสร้างหน้าต่างจริง + `attributes("-topmost", True)` แล้วจับภาพ (`PIL.ImageGrab`) — ระวังจับภาพโปรแกรมที่ผู้ใช้เปิดอยู่ |
| **AI / สถิติต้องซื่อตรง** | คำทำนายต้องแสดงความแม่นจากการทดสอบย้อนหลังคู่กันเสมอ · ตัวเลข % ของข่าวบอกที่มา (สถิติช่วงเวลา vs ข่าวชื่อเดียวกัน) · ห้ามสัญญาผลกำไร |

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
| `GET /api/admin/overview` · `POST /promo-key` | Admin | ภาพรวมระบบ · ผลิต Promo Key · หน้า `/admin/keys` มีคอลัมน์ลำดับ (#) และปุ่มพิมพ์/PDF ต่อคีย์หรือทั้งหน้า (`lib/printKeys.js`: A5 แนวนอน หน้าละ 1 ใบ, ลายน้ำโลโก้ + GoldBot24, วันที่สร้าง/หมดอายุ/ชั่วโมง/วิธีใช้ → เบราว์เซอร์ "Save as PDF") |
| `GET /api/calendar` · `/api/release` | สาธารณะ (CDN cache) | ปฏิทินเศรษฐกิจ (30 นาที) · เวอร์ชันล่าสุด (10 นาที) |
| `POST /api/track` | `app_download` สาธารณะ · `app_open`/`bot_start`/`bot_stop` ต้อง Bearer | สถิติดาวน์โหลด/การใช้โปรแกรม → `user_activity` (ซ้ำใน 5 นาทีนับครั้งเดียว · Desktop ส่งเวอร์ชัน + รหัสเครื่องแบบแฮช 10 ตัว) |
| `GET /api/admin/usage` | Admin | หน้า `/admin/usage`: ยอดดาวน์โหลดเว็บ + GitHub (ทุกช่องทาง/รายเวอร์ชัน) · เปิดโปรแกรม · ผู้ใช้รายวัน/7/30 วัน · จำนวนเครื่อง · เวอร์ชันที่ผู้ใช้เปิด · กราฟ 14 วัน (สรุปรายวันทาง LINE มียอดนี้ด้วย) |

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
