# 🛠️ แผนการพัฒนาตัวโปรแกรมฉบับสมบูรณ์ (Trading Engine Engineering Roadmap)
**โครงการ**: AI MetaTrader 5 (FBS) Gold Pro - Core Trading Engine Architecture  
**เวอร์ชันเป้าหมาย**: `2026.1003.0025+` | **ประเภทเอกสาร**: แผนพัฒนาสถาปัตยกรรมซอฟต์แวร์ (Technical Architecture Blueprint)  
**วันที่จัดทำ**: 3 ตุลาคม 2026  

---

## 🎯 วัตถุประสงค์ของการพัฒนาตัวโปรแกรม (Engine Objectives)
จากเดิมที่ระบบทำงานอยู่ในไฟล์เดี่ยว [multi_asset_ai_bot.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/multi_asset_ai_bot.py) (ขนาด 1,747 บรรทัด) เมื่อนำไปใช้ในเชิงพาณิชย์ที่มีลูกค้าจำนวนมาก ตัวโปรแกรมจะต้อง:
1. **แยกโมดูลชัดเจน (Clean Modular Architecture)**: แยกสมอง AI, การคำนวณอินดิเคเตอร์, แผนเทรด, การส่งคำสั่ง และการเช็ค License ออกจากกัน
2. **ความเสถียรระดับสูงสุด (Broker Fault-Tolerance)**: ดักจับ Error จาก MetaTrader 5 / FBS โบรกเกอร์ เช่น Requote, Off-quotes, No Money, Context Busy และเน็ตหลุด
3. **การคอมไพล์แบบไร้รอยต่อ (Seamless Binary Build)**: เตรียมโครงสร้างให้พร้อมสำหรับการคอมไพล์เป็น `.pyd` หรือ `.exe` ผ่าน Nuitka โดยไม่กระทบต่อประสิทธิภาพการคำนวณ

---

## 🏗️ 1. การปรับโครงสร้างโค้ดแบบแยกโมดูล (Modular Architecture)

จะทำการแยกโครงสร้างจาก monolithic 1 ไฟล์ ออกเป็นโครงสร้างแพ็กเกจ `engine/` ดังนี้:

```
d:/โปรเจค/AI_MetaTrader5_FBS/
├── 🚀 run_gui.bat               (ดับเบิลคลิกเปิดหน้าจอ Desktop GUI)
├── 🖥️ gui_app.py               (หน้าจอโปรแกรมหลัก: Login, Dashboard, Redeem, Console, Stats Modal)
├── 🔐 license_manager.py        (ระบบสิทธิ์, จัดการชั่วโมง HH.MM, เติมคีย์บวกเพิ่ม +)
├── 📊 stats_manager.py          (ระบบบันทึกและคำนวณสถิติรายบุคคลและรายแผน 5 แผน)
├── 🎮 bot_controller.py         (ตัวเชื่อมต่อควบคุมการรันบอท, ตัดเวลา และดักจับ Log สด)
├── 🚀 run_bot.bat               (รันสำหรับ Console Mode)
├── 📦 build_dist.py             (สคริปต์คอมไพล์ Nuitka เป็นไบนารีสำหรับแจกลูกค้า)
├── 📄 multi_asset_ai_bot.py     (Main Entry Point สำหรับรัน)
└── 📁 engine/                   (โฟลเดอร์โมดูลหลัก)
    ├── __init__.py
    ├── config.py                (ค่าคงที่ SL 0.75 ATR, TP 1.50, Cooldown, Symbol)
    ├── indicators.py            (คำนวณ ATR, RSI, Bollinger Bands H1, MA 5/10/30)
    ├── divergence.py            (ระบบตรวจจับ RSI Divergence 4 มิติ)
    ├── regime.py                (ตัวกรองเทรนด์ใหญ่ H4: Bullish / Bearish / Sideway)
    ├── ai_brain.py              (RandomForest, Feature Engineering 16 ตัว, Retrain 24 ชม.)
    ├── order_manager.py         (ส่งคำสั่ง BUY/SELL, Dynamic TP, Early Profit Lock)
    ├── risk_guard.py            (Circuit Breaker 2 ไม้, Same-Plan Loss Block, Margin Check)
    ├── license_guard.py         (เช็ค License, นับเวลาถอยหลัง, Heartbeat 60s)
    ├── telemetry.py             (สตรีมข้อมูลพอร์ตและเรดาร์ขึ้น Supabase ทุก 5s)
    └── plans/                   (ชุดแผนการเทรดเฉพาะทองคำ)
        ├── __init__.py
        ├── plan0_smc.py         (SMC Liquidity Hunt + H1 Trend Anchor)
        ├── plan1_bounce.py      (SR Swing Bounce + Divergence)
        ├── plan3_bb_reversion.py(Bollinger Bands H1 + MACD Exhaustion)
        ├── plan4_macross_m15.py (MA 5x10 M15 + Opposite Cross Exit)
        └── plan5_macross_h1.py  (MA 5x10 H1 + Opposite Cross Exit)
```

---

## 🛡️ 2. แผนการเพิ่มความแข็งแกร่งในการเชื่อมต่อ MT5 (Execution Hardening)

ในสภาวะตลาดทองคำจริง โบรกเกอร์ FBS และตลาดมักมีอาการ Slippage หรือปฏิเสธคำสั่งช่วงข่าวแรง:

### 2.1 ระบบ Retry อัตโนมัติเมื่อเกิด Trade Context Busy / Requote
* หากส่งคำสั่ง `mt5.order_send()` แล้วได้ผลลัพธ์เป็น Error ชั่วคราว:
  * `10004`: `TRADE_RETCODE_REQUOTE` (ราคาวิ่งเปลี่ยน) ➔ ดึงราคา Tick ใหม่ทันทีแล้วยิงซ้ำภายใน 0.5 วินาที (ไม่เกิน 3 ครั้ง)
  * `10006`: `TRADE_RETCODE_REJECT` (คำสั่งถูกปฏิเสธ) ➔ บันทึก Log และข้ามรอบ
  * `10018`: `TRADE_RETCODE_MARKET_CLOSED` (ตลาดปิดเสาร์-อาทิตย์) ➔ เข้าสู่ Sleep Mode อัตโนมัติ ไม่เปลือง CPU
  * `10019`: `TRADE_RETCODE_NO_MONEY` (หลักประกันไม่พอ) ➔ แจ้งเตือนลูกค้าบน Terminal และหยุดออกไม้ใหม่

### 2.2 ระบบ Auto-Reconnect เมื่อสัญญาณเน็ตหลุด
* หาก `mt5.terminal_info().connected == False` หรือดึง `mt5.copy_rates_from_pos()` ล้มเหลว:
  * บอทจะไม่แคชหรือแฮงก์
  * แสดงข้อความสีเหลือง `[NETWORK] Lost connection to broker. Re-establishing link in 5s...`
  * วนลูปตรวจสอบทุก 5 วินาทีจนกว่าการเชื่อมต่อจะกลับมา แล้วเริ่มสแกนต่อทันทีโดยไม่ต้องเปิดโปรแกรมใหม่

---

## 🧠 3. แผนการพัฒนาสมองกล AI และฟังก์ชันวิเคราะห์ราคา (AI & Analytics)

### 3.1 การปรับปรุง AI Model (RandomForest Engine)
- [ ] **ฟีเจอร์แท่งเทียน 16 ตัว**: รักษาชุดฟีเจอร์เฉพาะทองคำที่พิสูจน์แล้วว่าทำกำไรสูงสุด
- [ ] **Automated Continuous Retraining (ทุก 24 ชั่วโมง)**:
  * รันการเทรนใน Background Thread แยกอิสระ เพื่อไม่ให้กระตุกการทำงานของ Main Trade Loop
  * ตรวจสอบว่าโมเดลใหม่มี Test Accuracy $\ge 50\%$ ก่อนนำมาสลับใช้งานจริง (Hot Swap)
- [ ] **AI Confidence Dynamic Thresholding**:
  * เมื่อตรวจพบ Divergence สอดคล้อง ➔ ลดเกณฑ์ AI Confidence เหลือ $\ge 48\%$
  * สภาวะปกติ ➔ ใช้เกณฑ์ $\ge 50\% - 54\%$

### 3.2 การรักษาความคมชัดของแผนเทรดทองคำ (Plan 0, 1, 3, 4, 5)
- [ ] **Plan 0**: กรอง H1 Trend 100% ตัดการรับมีด
- [ ] **Plan 1**: บังคับ Divergence Confluence เสมอ
- [ ] **Plan 3**: บังคับ H1 MACD Histogram Exhaustion ยืนยันการหมดแรง
- [ ] **Plan 4 & Plan 5**: รันเทรนด์ไร้ TP และปิดรอบทันทีเมื่อ MA ตัดกลับขั้วตรงข้าม

---

## 📊 4. ชุดทดสอบและจำลองผลย้อนหลัง (Backtesting & Verification Suite)

พัฒนาชุดสคริปต์สำหรับตรวจสอบและประเมินคุณภาพของบอทก่อนปล่อยเวอร์ชันใหม่ให้ลูกค้า:
* [scratch_backtest_plans.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/scratch_backtest_plans.py): ทดสอบผลงานของทั้ง 5 แผนพร้อมกัน
* [test_plan4_macross_exit.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/test_plan4_macross_exit.py): ทดสอบความแม่นยำของ Plan 4 M15
* [test_plan5_h1_macross.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/test_plan5_h1_macross.py): ทดสอบรอบสวิงใหญ่ระดับวันของ Plan 5 H1
* [compare_sl_levels.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/compare_sl_levels.py): เปรียบเทียบระยะ SL 0.75 ATR vs ระดับอื่น

---

## 📝 5. ระบบบันทึก Log และการตรวจสอบประวัติ (Production Logging & Stats Engine)

### 5.1 ระบบบันทึก Log การทำงาน
* **Rotating File Handler (`logs/bot_runtime.log`)**:
  * จำกัดขนาดไฟล์ละ 10 MB สูงสุด 5 ไฟล์ย้อนหลัง เพื่อไม่ให้เปลืองพื้นที่ฮาร์ดดิสก์ของลูกค้า
* **`signal_history.csv`**:
  * มีระบบ `prune_old_csv_records` ลบประวัติที่เก่าเกิน 1 ปี (365 วัน) อัตโนมัติ
* **Console Ticker Display**:
  * Ticker นับถอยหลังแบบบรรทัดเดียว (20s) ไม่ทำให้ Terminal สแปมข้อความยาวจนรกตา

### 5.2 ระบบสถิติการเทรดรายบุคคลและรายแผน ([stats_manager.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/stats_manager.py))
* **การบันทึกผูกกับ User**: ทุกการเปิดและปิดไม้จะดึง `user_id` และ `email` จาก [license_manager.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/license_manager.py) มาบันทึกกำกับไว้
* **การแจกแจงสถิติแยกตาม 5 แผน**:
  * บันทึกจำนวนครั้งที่เข้าไม้ (Total Trades), ชนะ (Win), แพ้ (Loss)
  * คำนวณอัตราการชนะ (Win Rate %) = `(win / total) * 100`
  * คำนวณกำไรสุทธิรวม (Total Profit USD) และอัตรากำไร (Profit Factor) = `gross_profit / abs(gross_loss)`
* **แหล่งจัดเก็บข้อมูลสองชั้น**:
  * บันทึกรวมใน [user_stats_store.json](file:///d:/โปรเจค/AI_MetaTrader5_FBS/user_stats_store.json) และประวัติแยกไม้ใน [user_trade_history.csv](file:///d:/โปรเจค/AI_MetaTrader5_FBS/user_trade_history.csv)
  * ซิงค์ขึ้นตาราง `user_plan_stats` และ `trade_logs` บน Supabase อัตโนมัติผ่าน [supabase_sync.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/supabase_sync.py)
* **การแสดงผลบนหน้าจอ GUI**:
  * แสดงสรุปบน Header และแสดงป้ายสถิติสด `เข้า: X | WR: Y% | $Z.ZZ` ใต้การ์ดของแต่ละแผน
  * หน้าต่างป๊อปอัป `UserStatsDialog` แสดงตารางแจกแจงละเอียด 5 แผนพร้อม KPI รวม

---

## ⚙️ 6. ขั้นตอนการคอมไพล์โปรแกรมแจกลูกค้า (Automated Build Pipeline)

สร้างสคริปต์ `build_dist.py` เพื่อคอมไพล์โค้ด Python เป็นไฟล์ Binary ที่แฮกไม่ได้:

```python
# ตัวอย่างสคริปต์ build_dist.py
# ใช้คำสั่ง Nuitka เพื่อคอมไพล์โค้ดเป็น Machine Code
# nuitka --standalone --remove-output --include-package=engine --windows-icon-from-ico=assets/icon.ico multi_asset_ai_bot.py
```

* ผลลัพธ์: ได้ไฟล์ไบนารีที่ทำงานได้ทันทีโดยที่เครื่องลูกค้าไม่ต้องลง Python และไม่มีใครสามารถเปิดดูโค้ดสูตรเทรดข้างในได้ 100%

---

## 📋 แผนงานการพัฒนาตัวโปรแกรม (Engineering Tasks Checklist)

### 🔹 สปรินต์ที่ 1: การแตกไฟล์และจัดโครงสร้างโมดูล (Refactoring)
- [ ] 1.1 สร้างโฟลเดอร์ `engine/` และย้ายค่าคงที่ไปไว้ที่ `engine/config.py`
- [ ] 1.2 แยกฟังก์ชันคำนวณอินดิเคเตอร์ไปไว้ที่ `engine/indicators.py` และ `engine/divergence.py`
- [ ] 1.3 แยกสมองกล AI ไปไว้ที่ `engine/ai_brain.py`
- [ ] 1.4 แยกตรรกะแผน 0, 1, 3, 4, 5 ออกเป็นไฟล์เฉพาะใน `engine/plans/`
- [ ] 1.5 สร้าง `engine/order_manager.py` และ `engine/risk_guard.py`
- [ ] 1.6 ทดสอบรัน `multi_asset_ai_bot.py` เพื่อยืนยันว่าการส่งคำสั่งทำงานสมบูรณ์ 100% เหมือนเดิม

### 🔹 สปรินต์ที่ 2: เสริมเกราะป้องกันข้อผิดพลาด MT5 (Hardening)
- [x] 2.1 เพิ่มฟังก์ชัน `send_order` ป้องกัน Requote (10004) ด้วยระบบ Retry 3 ครั้งพร้อมดึงราคา Tick ใหม่ทันที
- [ ] 2.2 เพิ่มระบบ Auto-Reconnect เมื่อสัญญาณเน็ตขาดหาย
- [x] 2.3 เพิ่มการตรวจจับ Margin Call ก่อนส่งคำสั่ง (Margin Pre-check Guard < $25)

### 🔹 สปรินต์ที่ 3: ระบบบันทึก Log และการตัดขนาดไฟล์ (Logging & Retention)
- [ ] 3.1 ติดตั้ง `RotatingFileHandler` สำหรับบันทึก Runtime Logs
- [x] 3.2 ปรับปรุงระบบแจ้งเตือนเสียง (Sound Manager) ให้ทำงานแบบ Non-blocking ไม่ทำให้บอทหน่วง (winsound.SND_ASYNC)
- [x] 3.3 พัฒนาโมดูล `stats_manager.py` บันทึกสถิติการเข้าไม้และกำไรสุทธิแยกตาม User และตามแผน 5 แผน
- [x] 3.4 เชื่อมต่อ `multi_asset_ai_bot.py` เข้ากับ `stats_manager.py` เพื่อดักจับทุกการเปิดไม้และการปิดไม้ (SL, TP, Manual, Opposite Cross)
- [x] 3.5 เชื่อมต่อการแสดงผลสถิติสดและหน้าต่างสรุปผล `UserStatsDialog` บน Desktop GUI

### 🔹 สปรินต์ที่ 4: การคอมไพล์ทดสอบ (Build & Distribute Test)
- [x] 4.1 พัฒนาสคริปต์คอมไพล์อัตโนมัติ `build_dist.py` รองรับ Nuitka และ PyInstaller
- [x] 4.2 ทดสอบคอมไพล์ไบนารีสำเร็จ (`dist/AI_Gold_Commander_Pro/AI_Gold_Commander_Pro.exe`) และสร้างแพ็กเกจ `.zip` พร้อมแจกจ่าย ([AI_Gold_Commander_Pro_v2026.1003.0025.zip](file:///d:/โปรเจค/AI_MetaTrader5_FBS/dist/AI_Gold_Commander_Pro_v2026.1003.0025.zip))
- [x] 4.3 Hotfix หน้าจอ Login/Register ของ Desktop: แก้ `TclError: unknown color name "rgba(...)"` ด้วยสี Hex และคอมไพล์ใหม่ผ่าน 100%
- [ ] 4.4 เพิ่ม Smoke Test อัตโนมัติก่อนคอมไพล์ (สร้าง `MainTradingApp()` → `update()` → `destroy()`) ใน `build_dist.py` เพื่อดักบั๊ก UI ก่อนส่งลูกค้า

### 🔹 สปรินต์ที่ 5: ระบบใช้งานจริง (Production Auth & Access Control)
- [x] 5.1 ปิดโหมด Demo ถาวรทั้ง Web และ Desktop (Zero Demo Bypass)
- [x] 5.2 ระบบสมัครสมาชิก (Register) ทั้ง Web และ Desktop พร้อมโบนัส 48 ชม. และ PBKDF2-HMAC-SHA256
- [x] 5.3 Login Gate: ต้องเข้าสู่ระบบก่อนเปิด Dashboard / เริ่มบอท (`start_bot()` / `resume_bot()` ตรวจสิทธิ์และชั่วโมงคงเหลือ)
- [x] 5.4 Admin RBAC บนเว็บ: ปุ่มและหน้า `Admin Analytics` แสดงเฉพาะ User Admin พร้อม Access Barrier กันเข้าผ่าน URL ตรง
