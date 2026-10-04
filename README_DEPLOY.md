# 🌐 คู่มือการติดตั้ง Web Dashboard (Vercel) & Supabase สำหรับ AI MT5 Commander

ระบบเว็บ Dashboard พัฒนาด้วย **Next.js (React 19)** เชื่อมต่อฐานข้อมูลคลาวด์ **Supabase** เพื่อให้คุณสามารถดูพอร์ตการลงทุน และเซ็ตค่า **User / Password / Server** ของ MT5 รวมถึงเปิด/ปิดบอทได้จากระยะไกลผ่านมือถือหรือคอมพิวเตอร์

---

## 🔗 **Vercel Project Settings (บันทึกไว้เผื่ออ้างอิง)**

| ข้อมูล | ค่า |
|--------|-----|
| **Vercel Project URL** | https://vercel.com/noteratchas-projects/goldbot24 |
| **Git Integration Settings** | https://vercel.com/noteratchas-projects/goldbot24/settings/git |
| **Production Domain** | **https://goldbot24.vercel.app** ✅ |
| **Project ID** | `prj_e3MpPY5dfKa9ZIjtHpfBqR1Ob0ZG` |
| **Team/Org ID** | `team_7mZ7uSVTYfzo93wt2d6ftnJ9` |
| **Project Name** | `goldbot24` |
| **Framework** | Next.js 16 (Auto-detected) |
| **Root Directory** | `web` |
| **GitHub Repository** | https://github.com/noteratcha/AI_MetaTrader5_Gold_Pro |
| **Git Branch** | `main` |
| **Auto-deploy** | Enabled (Push to main → Auto deploy) |

> ✅ **อัปเดตล่าสุด**: โปรเจค Team ได้รับ domain `goldbot24.vercel.app` แล้ว (Vercel อนุญาตในบางกรณี)

---

## 🏛️ สถาปัตยกรรมการทำงาน (v2026.1004.2030)

```
[🌐 Browser]  ──(Authorization: Bearer <signed token>)──▶  [Next.js /api/* บน Vercel]
                                                                │ Service Role Key (ฝั่ง Server เท่านั้น)
                                                                ▼
[🖥️ Desktop App] ──login/me/meter/redeem──▶ /api/auth/*   [☁️ Supabase]
       │  └──telemetry / trade_logs / stats (anon: เขียนอย่างเดียว)──────▲
       ▼
[📈 MetaTrader 5 (FBS)] — รหัสผ่าน MT5 เก็บใน credentials.json บนเครื่องเท่านั้น
```

* Browser **ไม่เรียก Supabase ตรงอีกต่อไป** — ทุกการอ่าน/เขียนผ่าน API ที่ตรวจ Token
* พอร์ตสด (`bot_telemetry`) แยกแถวตาม id บัญชี GoldBot24 — ลูกค้าแต่ละคนเห็นเฉพาะพอร์ตตัวเอง

---

## 🔐 Environment Variables (Vercel → Settings → Environment Variables)

| ตัวแปร | จำเป็น | หมายเหตุ |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | publishable key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Supabase → Settings → API → service_role (ห้ามขึ้นต้นด้วย `NEXT_PUBLIC_`) |
| `AUTH_SECRET` | ✅ | สุ่มยาว ≥ 32 ตัว: `node -e "console.log(require('crypto').randomBytes(48).toString('base64url'))"` — **ถ้าไม่ตั้ง Production จะล็อกอินไม่ได้** |
| `PROMPTPAY_ID` | ✅ | เบอร์/เลขผู้เสียภาษีรับเงิน |
| `SLIPOK_BRANCH_ID`, `SLIPOK_API_KEY` | ✅ | ถ้าไม่ตั้ง ระบบจะไม่ออกคีย์ให้ (ไม่มีโหมดจำลองบน Production) |
| `ADMIN_EMAILS` | ⬜ | ค่าเริ่มต้น `admin@goldbot24.com,admin@aitrade24.com` |
| `PAYMENT_WEBHOOK_SECRET` | ⬜ | ถ้าใช้ Webhook ผู้ให้บริการต้องส่ง Header `x-webhook-secret` |

## 🚀 ลำดับการอัปเดตจากเวอร์ชันเก่า (สำคัญ)

1. ตั้ง Environment Variables ด้านบนให้ครบ
2. Deploy เว็บ: `cd web && npm run build && npx vercel --prod --yes`
3. รัน [`supabase_security_rls.sql`](supabase_security_rls.sql) ใน Supabase SQL Editor (เพิ่มคอลัมน์เจ้าของข้อมูล + ล็อก RLS + ปิด Realtime ของ `bot_config`)
4. Build Desktop ใหม่: `python build_dist.py` แล้วแจกให้ลูกค้า — **Desktop รุ่นเก่าจะล็อกอินไม่ได้** เพราะ Token รูปแบบเดิมถูกยกเลิก (ลูกค้าต้องล็อกอินใหม่ 1 ครั้งหลังอัปเดต)
5. ทดสอบ: สมัคร → ล็อกอิน (เว็บ + Desktop) → เริ่มบอท 6 นาที แล้วดูว่าชั่วโมงลดบนเว็บ → ซื้อแพ็กเกจเล็กสุด + แนบสลิป → เติมคีย์

> 📌 Desktop เรียก API ที่ `https://goldbot24.vercel.app` (เปลี่ยนได้ด้วย env `GOLDBOT_API_URL`)

---

## 🧪 รันเว็บบนเครื่อง (Localhost)

```bash
cd web
cp .env.example .env.local   # ใส่ค่าให้ครบ
npm install
npm run dev                  # http://localhost:3000
```

ตอนพัฒนาสามารถตั้ง `ALLOW_MOCK_SLIP=true` เพื่อข้ามการตรวจสลิปจริงได้ (ไม่มีผลบน Production)
