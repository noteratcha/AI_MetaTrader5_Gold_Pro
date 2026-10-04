# ✅ Checklist: เปิดใช้ Beam Payment Gateway (PromptPay อัตโนมัติ ไม่ต้องแนบสลิป)

> สมัครแล้ว **4 ต.ค. 2026** · Merchant: `goldbot24-8prs6f` · Beam แจ้งตรวจเอกสาร **1–3 วันทำการ**
> → คาดว่าจะได้ผลประมาณ **7–9 ต.ค. 2026** (เสาร์–อาทิตย์ไม่นับ)
>
> เมื่ออนุมัติแล้ว พิมพ์บอก Claude ว่า **"Beam อนุมัติแล้ว"** เพื่อเริ่มขั้นตอนที่ 3

---

## 1. รอ Beam อนุมัติ — *ฝั่งคุณ*
- [x] สมัครบัญชีที่ Beam Lighthouse และส่งโปรไฟล์ร้าน
- [x] อัปโหลดเอกสารธุรกิจ
- [ ] ได้รับอีเมล/แจ้งเตือนว่าบัญชีร้านค้าอนุมัติแล้ว (ภายใน 1–3 วันทำการ)
- [ ] ถ้าเกิน 3 วันทำการยังเงียบ → ติดต่อ Beam ผ่านแชทใน Lighthouse
- [ ] ถามยืนยันกับ Beam: เปิดช่องทาง **QR PromptPay** แล้ว และค่าธรรมเนียม PromptPay ของบัญชีนี้ **0%** จริง
- [ ] ถามยืนยัน: เงินเข้าบัญชีร้าน **T+3 วันทำการ** และบัญชีรับเงินถูกต้อง

## 2. เก็บค่าจาก Beam Lighthouse และใส่ใน Vercel — *ฝั่งคุณ*
> ⚠️ **ห้ามส่ง API Key / HMAC Key ในแชท** — ใส่เข้า Vercel เองด้วยคำสั่งด้านล่าง (เหมือนตอนใส่ Service Role Key)

- [ ] คัดลอก **Merchant ID**
- [ ] สร้าง **API Key** — เริ่มจาก **Playground (ทดสอบ)** ก่อน
- [ ] สร้าง **Webhook** ใน Lighthouse
  - URL: `https://goldbot24.vercel.app/api/webhook/beam`
  - Events: `charge.succeeded`, `charge.failed`
  - คัดลอก **HMAC Key** ของ Webhook
- [ ] ใส่ค่าใน Vercel (รันในโฟลเดอร์ `web`):
  ```
  npx vercel env add BEAM_MERCHANT_ID production
  npx vercel env add BEAM_API_KEY production --sensitive
  npx vercel env add BEAM_WEBHOOK_HMAC_KEY production --sensitive
  npx vercel env add BEAM_ENV production          # พิมพ์ playground ก่อน แล้วค่อยเปลี่ยนเป็น production
  ```

## 3. เชื่อมระบบ — *Claude*
- [ ] Adapter Beam: `POST /api/v1/charges` (`paymentMethodType: QR_PROMPT_PAY`, `referenceId` = เลขคำสั่งซื้อ)
- [ ] หน้าร้านแสดง QR จาก Beam (`encodedImage.imageBase64Encoded`) + นับถอยหลังตาม `encodedImage.expiry`
- [ ] Webhook `/api/webhook/beam` ตรวจลายเซ็น `X-Beam-Signature` (HMAC-SHA256, Base64) แล้วดึงสถานะ charge ซ้ำจาก Beam ก่อนออกคีย์
- [ ] หน้าร้านเปลี่ยนเป็น "ชำระเงินสำเร็จ" + แสดง Product Key อัตโนมัติ (ไม่ต้องแนบสลิป)
- [ ] เก็บ SlipOK ไว้เป็นช่องทางสำรอง (เลือกผู้ให้บริการด้วย env `PAYMENT_PROVIDER`)
- [ ] อัปเดตเลขเวอร์ชัน → `npm run build` → deploy

## 4. ทดสอบใน Playground — *ร่วมกัน*
- [ ] ซื้อแพ็กเกจทดสอบ → Beam ส่ง webhook → ได้ Product Key → เติมเข้าบัญชีสำเร็จ
- [ ] ทดสอบ charge ล้มเหลว → หน้าร้านแจ้งให้ลองใหม่ ไม่ออกคีย์
- [ ] ทดสอบ webhook ปลอม (ลายเซ็นผิด) → ถูกปฏิเสธ 401
- [ ] ทดสอบ webhook ซ้ำ → ไม่ออกคีย์ซ้ำ

## 5. เปิดใช้งานจริง — *ฝั่งคุณ + Claude*
- [ ] เปลี่ยน `BEAM_API_KEY` เป็น Production key และ `BEAM_ENV=production` แล้ว redeploy
- [ ] ซื้อจริงแพ็กเล็กสุด ฿50 ด้วยบัญชีตัวเอง → ได้คีย์ทันที
- [ ] ตรวจยอดใน Beam Lighthouse และเงินเข้าบัญชีภายใน T+3
- [ ] ตัดสินใจ: ปิด SlipOK หรือเก็บไว้เป็นช่องทางสำรอง

---

## 📌 งานค้างอื่น ๆ (จากรอบก่อน)
- [ ] ทดสอบเต็ม flow: รันบอท ≥ 6 นาที → ชั่วโมงบนเว็บลดลง + หน้า "พอร์ตสด" ขึ้นยอด/สถานะออนไลน์
- [ ] ลบข้อมูลทดสอบใน Supabase Table Editor:
  - `bot_telemetry` แถว `id = 2`
  - `user_plan_stats` แถว `plan_name = 'RLS-TEST'`
  - `risk_events` แถว `event_type = 'RLS_TEST'`
- [ ] ลองเปิดแท็บ **Investing.com** ในหน้า `/calendar` บนเบราว์เซอร์จริง (widget ถูกบล็อกตอนทดสอบอัตโนมัติ)
- [ ] เปลี่ยนรหัสผ่านที่เคยแสดงในภาพหน้าจอ หากใช้ซ้ำกับบริการอื่น
