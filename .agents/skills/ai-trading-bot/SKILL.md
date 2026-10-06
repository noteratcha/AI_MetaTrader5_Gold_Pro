---
name: ai-trading-bot
description: Knowledge, skills, techniques, execution style, the 5 XAUUSD trading plans (MA-Cross M15/H1, SMC Sweep, SR-Bounce, BB-H1), SL/TP and trailing rules, risk management, AI direction model + AI Outlook, news-impact analysis, desktop GUI (AI Gold Commander Pro) UI/UX rules, and GoldBot24 web/Supabase/payment integrations for the AI MetaTrader 5 Gold bot.
---

# AI Gold Commander Pro — XAUUSD Gold Specialist (อัปเดต 6 ต.ค. 2026)

บอทเทรดทองคำ **XAUUSD อย่างเดียว** เชื่อม MetaTrader 5 (FBS) ด้วย Python + โปรแกรม **AI Gold Commander Pro** (CustomTkinter) + เว็บ **GoldBot24** (Next.js บน Vercel + Supabase)
รายละเอียดเต็มและกฎวิศวกรรมทั้งหมดอยู่ใน `AGENTS.md` — ไฟล์นี้คือสรุปสกิล/เทคนิค/สไตล์ที่ต้องใช้ทุกครั้งที่ทำงานกับโปรเจกต์

> 📌 เลขเวอร์ชัน `YYYY.MMDD.HHMM` แหล่งเดียวคือ `version.py` — แก้โค้ดทุกครั้งรัน `python tools/bump_version.py` ก่อน commit

---

## 1. สไตล์การทำงานกับผู้ใช้ (Working Style)

1. **ตอบและสรุปเป็นภาษาไทยเสมอ** คงศัพท์เทรด/โค้ดเป็นภาษาอังกฤษ
2. **ปรับแผนเทรดทีละแผน** — แก้เฉพาะแผนที่ผู้ใช้ระบุชื่อ (ตั้งแต่ 6 ต.ค. 2026 เริ่มที่ Plan 1; Plan 5 ได้รับอนุญาตเฉพาะเรื่อง Step Trailing) แผนอื่นให้แค่ "ข้อสังเกต"
3. **Backtest ก่อนแก้กฎเสมอ** แล้วเสนอเป็นตาราง (ไม้ · ชนะ% · กำไร · PF · Max DD · กำไรรายไตรมาส) ให้ผู้ใช้เลือก — ถ้าผู้ใช้เลือกทางที่ผลแย่กว่า ทำตามแต่บอกตัวเลขตรง ๆ
4. **ซื่อตรงเรื่องความแม่น**: ทองทายทิศยาก (AI ≈ 52–64% แล้วแต่ระยะ) — ทุกคำทำนายต้องแสดงความแม่นจากการทดสอบย้อนหลังคู่กัน ห้ามสัญญากำไร
5. **ส่งงานครบวงจร**: แก้โค้ด → bump version → smoke test (จับภาพหน้าจอจริง) → commit/push (เว็บ deploy อัตโนมัติ) → `build_dist.py` → GitHub Release (Setup.exe + ZIP + SHA-256 + Release notes ภาษาไทยหัวข้อ `###`)
6. **ห้าม**: commit โฟลเดอร์ `SlipOK api guide`, ใส่คีย์ลับในแชท/โค้ด, อ่าน DB production เอง (ผู้ใช้รัน SQL เอง), ปิดโปรแกรม/ไม้ของผู้ใช้โดยไม่ถาม, แชร์ข้อมูลการเทรดข้ามบัญชี (ผู้ใช้ปฏิเสธแล้ว)

---

## 2. แผนเทรด 5 แผน (XAUUSD)

| แผน | ชื่อในโค้ด / ชื่อแสดง | จุดเข้า | SL / TP / การออก |
| :--- | :--- | :--- | :--- |
| **P1** | `MA-Cross-Trend` · `P1 · MA M15` | H1 MA100/150/200 เรียงตัวตามทิศ + MA5 ตัด MA13 บน M15 (แท่งปิด) + **กรองสัญญาณหลอก**: RSI 50–70 (BUY) / 30–50 (SELL) และราคาปิดฝั่งเดียวกับ MA50 M15 | SL **1.0 ATR** M15 · ไม่ตั้ง TP · Step Trailing ทุก +5 จุด เลื่อน 40% · ออกเมื่อ MA5 ตัด MA13 กลับ |
| **P2** | `MA-Cross-H1-Trend` · `P2 · MA H1` | MA5 ตัด MA10 บน H1 + H4 MA10/30 (Strict Pro-Trend) + ความชัน MA5 H4 (2 แท่ง) + ราคาปิด H4 เทียบ MA200 | SL 0.75 ATR (H1) · ไม่ตั้ง TP · ไม่เลื่อน SL · ออกเมื่อ MA5 ตัด MA10 H1 กลับ |
| **P3** | `SMC-LiquidityHunt` · `P3 · SMC Hunt` | ไส้กวาดแนวรับ/ต้าน H1 (500 แท่ง) แล้วปิดกลับ + ไส้ ≥ 0.30 ATR + เทรนด์ H1 MA10/30 + AI ≥ 50% (มี Div ≥ 48%) | SL 0.75 ATR · TP 1.125 ATR (RRR 1:1.5) |
| **P4** | `SR-SwingBounce` · `P4 · SR Bounce` | ห่างแนวรับ/ต้าน H1 ≤ 1 ATR + แท่งปฏิเสธ + RSI Divergence + AI ≥ 51% | SL 0.75 ATR · TP 1.125 ATR — *Backtest ล่าสุดติดลบ (ข้อสังเกต รอผู้ใช้สั่ง)* |
| **P5** | `BB-H1-Reversion` · `P5 · BB-H1` | หลุดขอบ BB H1 (20, 2SD) แล้วปิดกลับ + ไส้ ≥ 0.20 + Divergence + MACD H1 หมดแรง + AI ≥ 50% | SL 0.75 ATR · TP 1.125 ATR · Step Trailing ทุก +5 จุด เลื่อน 40% |

- **Backtest 2.5 ปี (6 ต.ค. 2026)**: P1 739 ไม้ ชนะ 35.3% +931 จุด PF 1.44 DD 131 · P2 312 ไม้ +1,107 PF 1.58 DD 219 · P5 ~32 ไม้ (น้อยเกินสรุป)
- **ทดสอบแล้วไม่ช่วย (P1)**: ADX, ความชัน MA5, ระยะห่าง MA, ขนาดแท่ง, รอแท่งยืนยัน, ATR ต่ำ, ช่วงเวลาเทรด, ออกเร็วเมื่อปิดกลับ MA13, ย้าย SL มาทุน, เลื่อน SL ขั้นอื่น (3/4/6/8/10 จุด หรือ 30/50/60%)
- **แนวรับ/ต้าน** (`find_sr_levels`): Swing High/Low ±3 แท่ง ย้อนหลัง 500 แท่ง รวมโซน 0.5 ATR เลือกโซนที่แตะ ≥ 2 ครั้ง
- **สภาวะตลาดบนการ์ด** (`ma_condition`, แสดงผลอย่างเดียว): MA50/100/150 เรียงขึ้น = Uptrend · เรียงลง = Downtrend · อื่น ๆ = Sideway

---

## 3. เทคนิคบริหารออเดอร์ (Execution Techniques)

1. **Closed-Candle Signals (Anti-Repaint)** — ทุกเงื่อนไขใช้แท่งที่ปิดแล้ว (`iloc[-2]`) · **Cross-Bar Guard** 1 ไม้ต่อ 1 แท่ง Cross
2. **Step Trailing SL** (`apply_p4_step_trailing`, P1 + P5) — ทุก +5 จุด (= $5 ที่ 0.01 lot) เลื่อน SL เข้าหาราคา 40% · จำขั้นใน `p4_trail_state.json` · เคารพ stops level
3. **Early Profit Lock** (P3–P5) — ถึง 70% ของ TP เลื่อน SL ไป +0.35 ATR (Buffer ≥ 0.4 ATR, Throttle 60 วิ)
4. **Unlimited Dynamic TP** — ถึง 80% ของ TP และ AI ยังมั่นใจ ≥ 54% ดัน TP +1 ATR และล็อก SL
5. **AI Reversal Close** — AI กลับทิศ ≥ 60% และราคาย้อนผ่านจุดเปิด → ปิด
6. **Take Profit $ (ผู้ใช้ตั้ง)** — ติ๊ก "ปิดไม้เมื่อกำไรถึง $X" → ปิดทุกไม้ของบอทเมื่อ profit + swap ≥ X (ตรวจก่อนกฎอื่น)
7. **Unified Close Path** — ทุกการปิดผ่าน `close_position()` พร้อมคอมเมนต์ที่สื่อความหมาย (`MA5 Cross Down Exit`, `Take Profit $5`, `AI Reversal Close`, `Manual Close (GUI)`, `Emergency Close All`) → ใช้แยก "ปิดโดย" ในประวัติร่วมกับ `deal.reason` (3 = บอท, 4 = SL, 5 = TP, 0–2 = ปิดเอง, 6 = Stop Out)
8. **Single-Count Accounting** — ไม้ที่บอทปิดเองจดใน `_self_closed_tickets` กันนับขาดทุน/Circuit Breaker ซ้ำ · ทิศไม้ = ฝั่งตรงข้ามของ Deal ปิด
9. **Plan Gate 2 ชั้น** — `plan_config.is_enabled()` = แอดมินเปิด (`/admin/plans`) และผู้ใช้ติ๊กใช้ (`user_plans[email]` ใน `bot_settings.json`)

---

## 4. ความเสี่ยง (Risk Management)

| กฎ | ค่า |
| :--- | :--- |
| Strict Pro-Trend (P3–P5) | H4 MA10/30 ห่าง ≥ 0.20% → เทรดฝั่งเดียว · < 0.20% = Range Play |
| Circuit Breaker | ขาดทุนติดกัน 2 ไม้ → พัก 60 นาที |
| Same-Plan Loss Block | แพ้ทิศไหน บล็อกทิศนั้น 60 นาที (ชนะแล้วปลด) |
| Cooldown | XAU 10 นาทีหลังปิดไม้ |
| Margin per Trade | $400 ต่อ 0.01 lot (ปรับตาม Lot ที่ผู้ใช้ตั้ง ค่าเริ่มต้น 0.01) |
| News Awareness | นับถอยหลังข่าว USD แรง + ผลต่อทอง + เตือนใน AI คาดการณ์ |

---

## 5. AI และการวิเคราะห์

1. **AI ทิศทางของบอท** — RandomForest (100 ต้น, ลึก 5) · 24 Features ปรับด้วย ATR (`build_ai_features`, M15 + H1/H4 แท่งปิด) · ทายล่วงหน้า 8 แท่ง (2 ชม.) · รีเทรนทุก 24 ชม. · พิมพ์ `[AI QUALITY]` จาก Holdout 20% (AUC ~0.52–0.54)
2. **AI Outlook** (`ai_outlook.py`, แท็บ "AI คาดการณ์") — RF แยก 1 ชม. / 4 ชม. / 1 วัน (เทรนทุก 6 ชม., อัปเดตทุก 1 นาที) + ปัจจัย: เทรนด์ H1 MA100/150/200, H4 MA10/30, MA200 H4, MA5/13 + RSI M15, แนวรับ/ต้าน H1, ข่าว USD แรงใน 24 ชม. · ความแม่น Walk-forward (`BACKTEST_ACC`): 1 วัน + AI ≥ 60% + เทรนด์ตรงกัน = **63.7%**, 1 ชม. ≈ 52% · AI < 55% แสดง "ไม่ชัด"
3. **News Impact** (`news_impact.py`) — ทิศ: ตัวเลขสูงกว่าคาด = USD แข็ง = ทองลง (ยกเว้น Jobless Claims/Unemployment กลับทิศ; สุนทรพจน์/FOMC ขึ้นกับท่าที) + แนวโน้มจาก Forecast vs Previous · ขนาด: ค่ากลาง |%| ทองใน 60 นาที ณ วัน/เวลานิวยอร์กเดียวกัน ~2 ปี (แปลง DST เอง ไม่ใช้ tzdata) · ข่าวที่ออกแล้ววัด "ผลจริง" สะสมใน `news_history.json` (ครบ 3 ครั้งใช้สถิติของข่าวนั้น) · feed ไม่มี Actual
4. **Research workflow** — สคริปต์ทดลองเก็บใน scratchpad (`bt_p1_filters.py`, `bt_outlook.py` ฯลฯ) · ผลที่ใช้จริงอัปเดตใน `tools/backtest_all.py` → `web/public/backtest.json` → หน้า `/backtest` (แผนเทรด)

---

## 6. โปรแกรม AI Gold Commander Pro (UI/UX)

- **แท็บ**: Console · ออเดอร์ที่เปิดอยู่ · ประวัติการเทรด (10 รายการ/หน้า + คอลัมน์ "ปิดโดย") · ปฏิทินเศรษฐกิจ (+ ผลต่อทอง คลิกดูรายละเอียด) · AI คาดการณ์
- **การ์ดคลิกได้** (`_make_clickable`, เปิดหน้าต่างเดียว): ยอดเงินในพอร์ต → กราฟแท่งกำไร/ขาดทุนรายวัน (7/14/30/เดือนนี้/90 วัน/กำหนดเอง) · ราคาทองคำ → แท่งเทียน M15 เรียลไทม์ (16–500 แท่ง ค่าเริ่มต้น 120, MA5/13, Bid/Ask/Spread, เส้นราคาเข้า/TP/SL/Lot, กำไรรวม, เต็มจอ F11)
- **แผงควบคุม**: เริ่ม/หยุดบอท · Lot · ปิดไม้เมื่อกำไรถึง $X · ปิดทุกออเดอร์ · การ์ดแผนเทรดติ๊กเลือกแผน + ป้าย ● BUY/SELL และชื่อสีเขียวเมื่อมีไม้
- **Console**: ล้างอัตโนมัติทุก 1 ชม. (ค่าเริ่มต้นเปิด) · หัวแสดง SL/TP แยกตามแผน · บรรทัดแนะนำสีเขียว
- **กฎสไตล์**:
  - สี Hex `#RRGGBB` เท่านั้น (ห้าม `rgba()`) · ห้าม `sticky="center"` · พอดีจอ 1366×768 (เช็กว่าการ์ดขวาไม่โดนตัด)
  - หน้าต่างย่อยทุกอันได้โลโก้โปรแกรมผ่าน patch `CTkToplevel.__init__` · หน้าต่างกราฟไม่ใช้ `transient()` เพื่อให้ขยายเต็มจอได้
  - คำเทรนด์ภาษาอังกฤษ (Uptrend/Downtrend/Sideway) · ชื่อแผน `P1 · MA M15` … · เรียก "โปรแกรม AI Gold Commander Pro" · ค่าบริการ "บาท/ชม."
  - ตัวเลขมีคอมมา · การ์ดแผนเทรดไม่ใส่ $ · ข้อความแจ้งเวอร์ชันใหม่ใช้ `UpdateDialog`
  - ค่าตั้งของผู้ใช้เก็บใน `%APPDATA%\GoldBot24\bot_settings.json` ผ่าน `_save_setting` (รวมค่า ไม่ทับ) — คีย์: `lot`, `tp_usd_enabled`, `tp_usd`, `console_autoclear`, `user_plans`
- **Smoke test**: สร้างหน้าต่างจริง + `attributes("-topmost", True)` แล้ว `PIL.ImageGrab` — ระวังจับภาพโปรแกรมของผู้ใช้ที่เปิดอยู่

---

## 7. เว็บ GoldBot24 และการเชื่อมต่อ

| ระบบ | สาระสำคัญ |
| :--- | :--- |
| **เว็บ = ข้อมูลโปรแกรม** | Telemetry ทุก 5 วิ `radar_signals[0]` มี `outlook`, `news`, `candles` (16 แท่ง + label เวลาไทย), `daily_pnl` (14 วัน), `account` → การ์ดหน้าพอร์ตสด (`LiveInsights.jsx`) + คอลัมน์ผลต่อทองใน `/calendar` · เว็บห้ามคำนวณซ้ำแยก |
| **ประวัติบนเว็บ** | `/api/user/trades` จับคู่ OPEN_* กับ CLOSE/TP_HIT/SL_HIT ด้วย ticket → คอลัมน์ "ถือไม้" |
| **สถิติการใช้งาน** | `/api/track` (app_download / app_open / bot_start / bot_stop, ซ้ำใน 5 นาทีนับครั้งเดียว) → หน้า `/admin/usage` + ยอด GitHub |
| **Auth / ความปลอดภัย** | Token HMAC (`AUTH_SECRET`) ผ่าน Bearer · Browser ไม่เรียก Supabase ตรง · RLS ทุกตาราง · Desktop เขียนผ่าน RPC เท่านั้น |
| **ชั่วโมง / ชำระเงิน** | หักทุกนาที ส่ง `/api/auth/meter` ทุก ~1 นาที · เว็บรีเฟรชชั่วโมงทุก 60 วิ · PromptPay QR + SlipOK (Beam ปฏิเสธ) · ใบเสร็จอีเมล · หน้าร้านแสดงราคาต่อชั่วโมงของแต่ละแพ็กเกจ |
| **แจ้งเตือนแอดมิน** | LINE OA: สมาชิกใหม่ · ซื้อสำเร็จ · บัญชีถูกล็อก · สรุปรายวัน (รวมดาวน์โหลด/เปิดโปรแกรม) |
| **MetaTrader 5** | magic `888999` · comment = ชื่อแผน · เวลา Deal เป็นเวลาเซิร์ฟเวอร์ (FBS = EET/EEST) แปลงเป็นเวลาไทยก่อนแสดง |
| **Release** | GitHub `noteratcha/AI_MetaTrader5_Gold_Pro` · ตัวติดตั้ง Inno Setup (`installer/goldbot24.iss`) · แจ้งอัปเดตในโปรแกรมผ่าน `/api/release` |
