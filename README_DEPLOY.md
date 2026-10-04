# 🌐 คู่มือการติดตั้ง Web Dashboard (Vercel) & Supabase สำหรับ AI MT5 Commander

ระบบเว็บ Dashboard พัฒนาด้วย **Next.js (React 19)** เชื่อมต่อฐานข้อมูลคลาวด์ **Supabase** เพื่อให้คุณสามารถดูพอร์ตการลงทุน และเซ็ตค่า **User / Password / Server** ของ MT5 รวมถึงเปิด/ปิดบอทได้จากระยะไกลผ่านมือถือหรือคอมพิวเตอร์

---

## 🔗 **Vercel Project Settings (บันทึกไว้เผื่ออ้างอิง)**

| ข้อมูล | ค่า |
|--------|-----|
| **Vercel Project URL** | https://vercel.com/noteratchas-projects/aitrade24 |
| **Git Integration Settings** | https://vercel.com/noteratchas-projects/aitrade24/settings/git |
| **Production Domain** | https://goldbot24-4jnnk2of7-noteratchas-projects.vercel.app |
| **Project ID** | `prj_AlzfccPhRSjMN1uH8TtqG6y7BAMf` |
| **Team/Org ID** | `team_7mZ7uSVTYfzo93wt2d6ftnJ9` |
| **Project Name** | `aitrade24` |
| **Framework** | Next.js 16 (Auto-detected) |
| **Root Directory** | `web` |

> 💡 **หมายเหตุ**: โปรเจคนี้เป็น **Team Project** (`noteratchas-projects`) ไม่ใช่ Personal Account จึงไม่ได้รับ domain `goldbot24.vercel.app` (Reserved ให้ Personal Account เท่านั้น) ต้องใช้ `goldbot24-4jnnk2of7-noteratchas-projects.vercel.app` แทน

---

## 🏛️ สถาปัตยกรรมการทำงาน (Cloud Architecture)

```
[🌐 Web Dashboard บน Vercel] 
          ▲
          │ (REST / Realtime Webhook)
          ▼
[☁️ Supabase Cloud Database] (เก็บ User, Pass, Server, Logs, Telemetry)
          ▲
          │ (ซิงค์สถานะพอร์ต & คำสั่งเทรดทุก 60 วิ)
          ▼
[🤖 MT5 Python Bot บนเครื่อง PC] ➔ [📈 MetaTrader 5 (FBS)]
```

---

## 🚀 ขั้นตอนที่ 1: สร้างฐานข้อมูลบน Supabase (ฟรี 100%)

1. สมัครหรือล็อกอินที่ [supabase.com](https://supabase.com)
2. กด **New Project** ตั้งชื่อโปรเจกต์ (เช่น `mt5-ai-bot`) และรหัสผ่านฐานข้อมูล
3. เมื่อระบบสร้างโปรเจกต์เสร็จ ให้ไปที่เมนู **SQL Editor** (ไอคอนรูป `>_` ด้านซ้าย)
4. เปิดไฟล์ [`supabase_schema.sql`](file:///d:/โปรเจค/AI_MetaTrader5_FBS/supabase_schema.sql) ในโปรเจกต์นี้ ก๊อปปี้คำสั่ง SQL ทั้งหมดไปวางในช่อง SQL Editor แล้วกดปุ่ม **RUN**
   * *ระบบจะสร้างตาราง `bot_config`, `trade_logs`, `bot_telemetry` พร้อมตั้งค่าความปลอดภัย RLS ให้ครบถ้วน*
5. ไปที่เมนู **Project Settings** (รูปฟันเฟืองด้านล่างซ้าย) ➔ เลือกแท็บ **API**
6. ก๊อปปี้ค่าสำคัญ 2 ตัวเก็บไว้:
   * **Project URL** (เช่น `https://abcdefghijklmnop.supabase.co`)
   * **anon public Key** (ชุดตัวอักษรยาวๆ ที่ขึ้นต้นด้วย `eyJhbGci...`)

---

## 💻 ขั้นตอนที่ 2: ทดสอบรันหน้าเว็บบนเครื่องตัวเอง (Localhost)

1. เปิดไฟล์ [`web/.env.local`](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/.env.local) แล้วนำค่าจากข้อ 1.6 มาใส่:
   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```
2. เปิด Terminal เข้าไปที่โฟลเดอร์ `web`:
   ```bash
   cd web
   npm run dev
   ```
3. เปิดเว็บเบราว์เซอร์ไปที่: **`http://localhost:3000`**
4. คุณจะเห็นหน้าจอ Cyber-Trading Dashboard:
   * กดปุ่ม **"เซ็ตค่า User / Password"** เพื่อกรอกเลขพอร์ต MT5, Trading Password และ Server โบรกเกอร์
   * หรือกดปุ่ม **"ตั้งค่า Supabase"** บนหน้าเว็บเพื่อเชื่อมต่อได้ทันที

---

## ☁️ ขั้นตอนที่ 3: Deploy หน้าเว็บขึ้น Vercel (ออนไลน์ตลอด 24 ชม.)

### วิธีที่ 1: Deploy ผ่าน Vercel CLI (ง่ายและเร็วที่สุดใน 1 นาที)
1. เปิด Terminal ในโฟลเดอร์ `web`:
   ```bash
   cd web
   npx vercel
   ```
2. ตอบคำถามใน Terminal (กดยืนยันค่าเริ่มต้นได้เลย):
   * Set up and deploy? ➔ **y**
   * Which scope? ➔ **เลือกบัญชีของคุณ**
   * Link to existing project? ➔ **n**
   * What's your project's name? ➔ **ai-mt5-dashboard**
   * In which directory is your code located? ➔ **./**
3. เมื่อเสร็จสิ้น รันคำสั่งดีพลอย Production:
   ```bash
   npx vercel --prod
   ```
4. ไปที่ Vercel Dashboard ➔ **Settings** ➔ **Environment Variables** เพิ่ม 2 ค่า:
   * `NEXT_PUBLIC_SUPABASE_URL`
   * `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   แล้วกด **Redeploy** 1 ครั้ง

### วิธีที่ 2: Deploy ผ่าน GitHub
1. อัปโหลดโฟลเดอร์โปรเจกต์ขึ้น GitHub
2. ไปที่ [vercel.com](https://vercel.com) ➔ กด **Add New Project**
3. เลือก Repository ของคุณ ➔ กำหนด **Root Directory** เป็น `web`
4. ใส่ Environment Variables (`NEXT_PUBLIC_SUPABASE_URL` และ `NEXT_PUBLIC_SUPABASE_ANON_KEY`)
5. กด **Deploy** ➔ คุณจะได้ URL เช่น `https://ai-mt5-dashboard.vercel.app` เข้าดูและตั้งค่าผ่านมือถือได้ทันที!

---

## 🤖 ขั้นตอนที่ 4: เชื่อมต่อบอท Python กับ Cloud

1. บอท Python (`multi_asset_ai_bot.py`) มีโมดูล [`supabase_sync.py`](file:///d:/โปรเจค/AI_MetaTrader5_FBS/supabase_sync.py) ติดตั้งไว้เรียบร้อยแล้ว
2. เมื่อคุณใส่ค่าใน [`web/.env.local`](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/.env.local) บอทจะอ่านค่า Supabase อัตโนมัติ
3. เมื่อรันบอท:
   ```bash
   python multi_asset_ai_bot.py
   ```
   * บอทจะดึง User / Password / Server ที่คุณตั้งไว้บนเว็บมาใช้ล็อกอินเข้า MT5 อัตโนมัติ
   * ส่งยอด Balance, Equity, กำไรลอยตัว และรายการไม้ที่เปิดอยู่ขึ้นแสดงบนเว็บ Dashboard ทุกนาที
   * ส่งประวัติการเทรดทุกครั้งที่มีการเปิดหรือปิดไม้ขึ้น Supabase แบบ Real-time!
