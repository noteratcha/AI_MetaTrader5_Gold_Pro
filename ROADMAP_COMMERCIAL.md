# 📋 แผนการพัฒนาโครงการเชิงพาณิชย์ฉบับสมบูรณ์ (Master Commercial Specification & Roadmap)
**โครงการ**: AI MetaTrader 5 (FBS) Gold Pro - Commercial Bot-as-a-Service Edition  
**เวอร์ชันระบบ**: `2026.1003.0025` | **สถานะ**: ฉบับสมบูรณ์ละเอียดสูง (High-Detail Blueprint)  
**วันที่จัดทำ**: 3 ตุลาคม 2026  

---

## 📑 สารบัญแผนงาน (Table of Contents)
1. [ภาพรวมโมเดลธุรกิจและข้อกำหนดทางเทคนิค (Business & Technical Specs)](#1-ภาพรวมโมเดลธุรกิจและข้อกำหนดทางเทคนิค)
2. [สถาปัตยกรรมระบบภาพรวม (System Architecture Diagram)](#2-สถาปัตยกรรมระบบภาพรวม)
3. [เฟสที่ 1: โครงสร้างฐานข้อมูล Supabase & ฟังก์ชันคำนวณเวลา (Cloud Database & RPC)](#เฟสที่-1-โครงสร้างฐานข้อมูล-supabase--ฟังก์ชันคำนวณเวลา)
4. [เฟสที่ 2: ระบบชำระเงิน Dynamic PromptPay QR & Webhook ตรวจจับเงินเข้า](#เฟสที่-2-ระบบชำระเงิน-dynamic-promptpay-qr--webhook-ตรวจจับเงินเข้า)
5. [เฟสที่ 3: ระบบหน้าเว็บหน้าร้าน (Storefront), ตรวจเช็คเวลา & Admin Panel](#เฟสที่-3-ระบบหน้าเว็บหน้าร้าน-storefront-ตรวจเช็คเวลา--admin-panel)
6. [เฟสที่ 4: การเชื่อมต่อ License Guard เข้ากับตัวบอท Python](#เฟสที่-4-การเชื่อมต่อ-license-guard-เข้ากับตัวบอท-python)
7. [เฟสที่ 5: ระบบ Launcher และอัปเดตอัตโนมัติ (OTA Auto-Updater)](#เฟสที่-5-ระบบ-launcher-และอัปเดตอัตโนมัติ-ota-auto-updater)
8. [เฟสที่ 6: การป้องกันโค้ด (Binary Compilation) และขั้นตอนส่งมอบ](#เฟสที่-6-การป้องกันโค้ด-binary-compilation-และขั้นตอนส่งมอบ)
9. [การจัดการเคสข้อยกเว้นและกรณีฉุกเฉิน (Edge Cases & Fault Tolerance)](#9-การจัดการเคสข้อยกเว้นและกรณีฉุกเฉิน)
10. [ตารางตรวจสอบความคืบหน้ารายเฟส (Master Execution Checklist)](#10-ตารางตรวจสอบความคืบหน้ารายเฟส)

---

## 1. ภาพรวมโมเดลธุรกิจและข้อกำหนดทางเทคนิค

### 1.1 นโยบายราคาและการคิดเวลา (Pricing & Metering Policy)
* **อัตราค่าบริการพื้นฐาน**: **1 บาท ต่อ 1 ชั่วโมงการใช้งานจริง** (1 THB / 1 Hour Active Time)
* **หน่วยการนับเวลา**: นับเวลาละเอียดระดับวินาที โดยทำการหักยอดทุกๆ **60 วินาที** รอบละ $\frac{60}{3600} = 0.0167$ ชั่วโมง
* **การนับเวลาเฉพาะตอนเปิดบอท**: จะนับเวลาเฉพาะช่วงที่บอทกำลังรันสแกนตลาดเท่านั้น หากลูกค้าปิดโปรแกรม เวลาจะหยุดนับทันที
* **รูปแบบการแสดงผลตัวนับเวลา (Time Display Format)**:
  * แสดงผลในรูปแบบ **"ชั่วโมง.นาที" (HH.MM)** เสมอ เพื่อให้ลูกค้าอ่านเข้าใจง่ายและไม่สับสนกับเลขทศนิยม:
    * ตัวอย่าง: **`48.30`** หมายถึง **48 ชั่วโมง 30 นาที** *(แปลงจาก 48.50 ชม. ในฐานข้อมูล)*
    * ตัวอย่าง: **`99.45`** หมายถึง **99 ชั่วโมง 45 นาที**
    * ตัวอย่าง: **`1.05`** หมายถึง **1 ชั่วโมง 05 นาที**
  * บนหน้าเว็บและ Terminal แสดงคู่กัน: `48.30 (48 ชม. 30 นาที)`

### 1.2 ระบบยืนยันตัวตนสมาชิก (User & Password Authentication)
* **การเข้าใช้งาน**: ลูกค้าลงทะเบียนด้วย **Username / Email + Password** ผ่านระบบ Supabase Auth
* **การใช้งานบนเว็บ (Web Portal)**: ใช้ดูข้อมูลพอร์ต, ประวัติการซื้อ, ชั่วโมงคงเหลือ และหน้าต่าง Redeem เติมเวลา
* **การใช้งานบนตัวบอท (Desktop Bot)**: กรอก Username + Password ตอนเปิดใช้งานครั้งแรก ระบบจะบันทึก Session Token ลงในเครื่องให้อัตโนมัติ (ครั้งต่อไปเปิดบอทจะเข้าสู่ระบบทันที ไม่ต้องกรอกซ้ำ)

### 1.3 สิทธิ์การใช้งานพร้อมกัน (Concurrency & Device Access Model)
* 🔒 **โหมดมาตรฐาน (Standard - Single Concurrent Session)**:
  * ลูกค้าสามารถนำโปรแกรมไปติดตั้งที่เครื่องใดก็ได้ (คอมบ้าน, โน้ตบุ๊ก, VPS) และใช้กับพอร์ตใดก็ได้ (Demo / Real)
  * **จำกัดการรันพร้อมกัน 1 จอในเวลาเดียวกัน**: หากมีการเปิดใช้งานบอทจากเครื่องใหม่ ระบบจะยอมให้เครื่องใหม่ทำงาน และสั่งระงับ (Kick out) จอเดิมทันที พร้อมแจ้งเตือนชัดเจน
* 🌐 **โหมดแชร์เวลาได้ (Shared Pool - Admin Configured)**:
  * หาก Admin ทำการเปิดสิทธิ์ `allow_shared_pool = TRUE` ให้กับลูกค้ารายนั้น
  * ลูกค้าจะสามารถเปิดรันพร้อมกันได้หลายจอ (ตามจำนวน `max_concurrent_sessions` ที่ Admin อนุญาต เช่น 2, 3 หรือ 5 จอ)
  * **กติกาการตัดเวลา**: ทุกจอจะรุมหักเวลาออกจาก **"ถังชั่วโมงเดียวกันของบัญชีผู้ใช้"** (เช่น รันพร้อมกัน 2 จอ เป็นเวลา 1 ชม.จริง จะถูกหักจากถังรวม 2 ชม.)

### 1.4 มาตรฐานรูปแบบ Product Key สำหรับเติมชั่วโมง (Redeem Voucher Specification)
* **บทบาทของ Product Key**: ทำหน้าที่เป็น **"รหัสบัตรเติมเงิน / คูปองแลกชั่วโมง (Voucher Code)"**
  * เมื่อลูกค้าซื้อแพ็กเกจชั่วโมงผ่านหน้าเว็บ หรือ Admin สร้างแจก ระบบจะผลิต Product Key ออกมา
  * ลูกค้านำ Product Key มากด **Redeem (แลกเวลา)** บนหน้าเว็บ หรือ ในตัวบอท เพื่อบวกชั่วโมงเข้าบัญชีของตนเอง
  * รหัสแต่ละชุดสามารถใช้งานได้ **1 ครั้งเท่านั้น** (เมื่อ Redeem สำเร็จ รหัสจะถูกทำเครื่องหมายเป็น `is_used = TRUE` ทันที)
* **รูปแบบมาตรฐานทางการ**: **`XXXX-XXXX-XXXX-XXXX-XXXX-XXXX`** (6 ชุด คั่นด้วยเครื่องหมายขีด `-`)
  * **โครงสร้าง**: รหัสสุ่มความปลอดภัยสูง ตัวเลขและตัวอักษรพิมพ์ใหญ่ บล็อกละ 4 หลัก จำนวน 6 ชุด (รวม 24 ตัวอักษร) สร้างด้วยระบบสุ่ม Cryptographically Secure Random (CSPRNG)
  * **ความยาวรวม**: 24 ตัวอักษร (ไม่รวมขีด) หรือ 29 ตัวอักษร (รวมขีด)
  * **ตัวอย่างรหัสจริง**:
    * `7F9A-B23C-88DE-99A1-4F2K-5M8N`
    * `8899-C4BA-55F9-11E0-7A3M-2X4W`
    * `A1B2-C3D4-E5F6-9Z8W-2345-6789`
  * **สูตรการตรวจสอบรูปแบบ (Client-Side Regex)**:  
    `^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$`

---

## 2. สถาปัตยกรรมระบบภาพรวม

```
┌────────────────────────────────────────────────────────────────────────┐
│                        🌐 CLIENT INTERFACES                            │
│  ┌───────────────────────────┐      ┌───────────────────────────────┐  │
│  │   📱 Web Store / Portal   │      │  💻 Desktop Client (Customer) │  │
│  │   - เลือกซื้อแพ็กเกจ (1บ/ชม) │      │  - Launcher.exe (Auto-Update) │  │
│  │   - สแกน QR PromptPay      │      │  - LicenseGuard (Heartbeat)   │  │
│  │   - เช็คเวลา / Admin Panel │      │  - Core Bot Engine (AI/MT5)   │  │
│  └─────────────┬─────────────┘      └──────────────┬────────────────┘  │
└────────────────┼───────────────────────────────────┼───────────────────┘
                 │                                   │
                 │ REST / Webhook                    │ HTTPS RPC (Heartbeat 60s)
                 ▼                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 ☁️ CLOUD BACKEND (SUPABASE PLATFORM)                   │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ PostgreSQL Tables:                                               │  │
│  │  ├── licenses          (รหัสสิทธิ์, ชั่วโมงคงเหลือ, สิทธิ์แชร์)    │  │
│  │  ├── license_sessions  (สถานะจอที่กำลังออนไลน์สด)                 │  │
│  │  ├── packages          (แพ็กเกจราคา 1บ/ชม ที่ Admin จัดการ)      │  │
│  │  ├── orders            (คำสั่งซื้อ, QR Payload, สถานะการชำระ)     │  │
│  │  └── app_releases      (เวอร์ชันบอทล่าสุด, ลิงก์ดาวน์โหลด Patch)   │  │
│  ├──────────────────────────────────────────────────────────────────┤  │
│  │ RPC Functions:                                                   │  │
│  │  ├── start_bot_session()  ➔ ยืนยันสิทธิ์ / จัดการสิทธิ์ 1 จอ     │  │
│  │  ├── heartbeat_session()  ➔ ตัดเวลาถอยหลัง & เช็คสถานะ Kick      │  │
│  │  └── mark_order_paid()    ➔ เติมชั่วโมงอัตโนมัติเมื่อเงินเข้า     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                 ▲
                 │ Webhook แจ้งเตือนเงินเข้าทันที
┌────────────────┴────────────────┐
│ 💳 PROMPTPAY PAYMENT GATEWAY     │
│ (GB Prime Pay / Omise / SlipOK) │
└─────────────────────────────────┘
```

---

## เฟสที่ 1: โครงสร้างฐานข้อมูล Supabase & ฟังก์ชันคำนวณเวลา

### 1.1 รายละเอียดตารางฐานข้อมูล (Database Schema)

```sql
-- ==============================================================================
-- 1. ตารางข้อมูลโปรไฟล์และกระเป๋าเวลาของผู้ใช้ (users_profile)
-- เชื่อมต่อกับระบบ Supabase Auth (auth.users)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS users_profile (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    phone_number TEXT,
    hours_remaining NUMERIC(10, 3) DEFAULT 0.000,       -- กระเป๋าชั่วโมงคงเหลือ (ทศนิยม 3 ตำแหน่ง)
    
    -- การกำหนดสิทธิ์จาก Admin:
    allow_shared_pool BOOLEAN DEFAULT FALSE,            -- TRUE = เปิดให้แชร์เวลาหลายจอได้
    max_concurrent_sessions INTEGER DEFAULT 1,          -- จำนวนจอสูงสุดที่เปิดพร้อมกันได้ (ค่าเริ่มต้น 1 จอ)
    
    is_suspended BOOLEAN DEFAULT FALSE,                 -- TRUE = ระงับการใช้งานชั่วคราว
    suspend_reason TEXT,                                -- เหตุผลที่ระงับ
    total_hours_purchased NUMERIC(10, 2) DEFAULT 0.0,   -- สถิติยอดซื้อชั่วโมงสะสมทั้งหมด
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- 2. ตารางเก็บบัตรเติมชั่วโมง Product Key 6 ชุด (product_keys)
-- รูปแบบ: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
-- ==============================================================================
CREATE TABLE IF NOT EXISTS product_keys (
    key_code TEXT PRIMARY KEY,                             -- เช่น '7F9A-B23C-88DE-99A1-4F2K-5M8N'
    hours NUMERIC(10, 2) NOT NULL,                         -- จำนวนชั่วโมงหลัก (เช่น 50, 100, 300)
    bonus_hours NUMERIC(10, 2) DEFAULT 0.00,               -- ชั่วโมงแถมโปรโมชั่น
    price_thb NUMERIC(10, 2) NOT NULL,                     -- มูลค่าราคาบาท (ชั่วโมงละ 1 บาท)
    status TEXT DEFAULT 'UNUSED',                          -- 'UNUSED' (ยังไม่ใช้งาน), 'REDEEMED' (ใช้งานแล้ว)
    is_used BOOLEAN DEFAULT FALSE,                         -- TRUE = ถูกใช้งานเติมไปแล้ว (ป้องกันเติมซ้ำ)
    
    -- ข้อมูลประวัติการสั่งซื้อของ User (Buyer History):
    purchased_by_user_id UUID REFERENCES users_profile(id),-- บัญชี User ที่เป็นคนสั่งซื้อ Product Key นี้
    order_id TEXT,                                         -- รหัสออเดอร์คำสั่งซื้อ
    purchased_at TIMESTAMPTZ DEFAULT NOW(),                -- วันเวลาที่สั่งซื้อ
    
    -- ข้อมูลการนำไปใช้งาน (Redemption Tracking):
    redeemed_by_user_id UUID REFERENCES users_profile(id), -- User ที่นำรหัสไปเติม (อาจเป็นคนซื้อเอง หรือส่งต่อให้เพื่อน)
    redeemed_at TIMESTAMPTZ DEFAULT NULL                   -- วันเวลาที่กดเติมเวลา
);

CREATE INDEX IF NOT EXISTS idx_product_keys_buyer ON product_keys(purchased_by_user_id);
CREATE INDEX IF NOT EXISTS idx_product_keys_used ON product_keys(is_used);
CREATE INDEX IF NOT EXISTS idx_product_keys_status ON product_keys(status);

-- ==============================================================================
-- 3. ตารางติดตาม Session สดที่กำลังรันอยู่ (license_sessions)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS license_sessions (
    session_id TEXT PRIMARY KEY,                        -- UUID สุ่มประจำจอนั้นๆ
    user_id UUID REFERENCES users_profile(id) ON DELETE CASCADE,
    device_name TEXT DEFAULT 'Windows-PC',              -- ชื่อคอมพิวเตอร์ของลูกค้า
    mt5_account BIGINT DEFAULT 0,                       -- เลขพอร์ต MT5 ที่เปิดใช้งาน
    ip_address TEXT,                                    -- IP ของเครื่องลูกค้า
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_heartbeat TIMESTAMPTZ DEFAULT NOW()            -- อัปเดตทุกๆ 60 วินาที
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON license_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_hb ON license_sessions(last_heartbeat);

-- ==============================================================================
-- 4. ตารางแพ็กเกจชั่วโมงสำหรับขาย (packages) - Admin จัดการได้อิสระ
-- ==============================================================================
CREATE TABLE IF NOT EXISTS packages (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,                                 -- เช่น 'แพ็กเกจเริ่มต้น 50 ชม.'
    hours NUMERIC(10, 2) NOT NULL,                      -- จำนวนชั่วโมงหลัก
    bonus_hours NUMERIC(10, 2) DEFAULT 0.00,            -- ชั่วโมงแถมพิเศษสำหรับโปรโมชั่น
    price_thb NUMERIC(10, 2) NOT NULL,                  -- ราคาขาย (คิดชม.ละ 1 บาท)
    badge TEXT DEFAULT NULL,                            -- ป้าย เช่น 'ขายดี 🔥', 'สุดคุ้ม ✨'
    description TEXT,                                   -- คำอธิบายสิทธิประโยชน์
    sort_order INTEGER DEFAULT 1,                       -- ลำดับการแสดงผลหน้าเว็บ
    is_active BOOLEAN DEFAULT TRUE,                     -- สวิตช์ เปิด/ปิด การขาย
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ข้อมูลตั้งต้นแพ็กเกจ (ชั่วโมงละ 1 บาท)
INSERT INTO packages (name, hours, bonus_hours, price_thb, badge, sort_order) VALUES
('Starter 50', 50, 0, 50.00, NULL, 1),
('Popular 100', 100, 0, 100.00, 'ขายดี 🔥', 2),
('Value 300', 300, 20, 300.00, 'แถมฟรี 20 ชม. ✨', 3),
('Marathon 500', 500, 50, 500.00, 'แถมฟรี 50 ชม. 👑', 4)
ON CONFLICT DO NOTHING;

-- ==============================================================================
-- 5. ตารางคำสั่งซื้อและการชำระเงิน (orders)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,                          -- เช่น 'ORD-20261003-9988'
    user_id UUID REFERENCES users_profile(id),          -- บัญชีผู้ซื้อ (ถ้าล็อกอิน)
    package_id INTEGER REFERENCES packages(id),
    amount_thb NUMERIC(10, 2) NOT NULL,
    hours_to_add NUMERIC(10, 2) NOT NULL,               -- ชั่วโมงที่จะได้รับ (hours + bonus)
    status TEXT DEFAULT 'PENDING',                      -- 'PENDING', 'PAID', 'EXPIRED', 'FAILED'
    payment_method TEXT DEFAULT 'PROMPTPAY',
    qr_payload TEXT,                                    -- ข้อความ EMVCo สำหรับสร้าง QR
    qr_image_url TEXT,                                  -- ลิงก์รูป QR Code
    generated_key_code TEXT,                            -- Product Key ที่ถูกสร้างขึ้นเมื่อชำระสำเร็จ
    paid_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);

-- ==============================================================================
-- 6. ตารางเวอร์ชันซอฟต์แวร์และการปล่อย Patch อัปเดต (app_releases)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS app_releases (
    version TEXT PRIMARY KEY,                           -- เช่น '2026.1003.0025'
    download_url TEXT NOT NULL,                         -- ลิงก์ดาวน์โหลดไฟล์ Patch (.zip)
    checksum_sha256 TEXT NOT NULL,                      -- Hash ตรวจสอบความถูกต้องของไฟล์
    mandatory BOOLEAN DEFAULT TRUE,                     -- บังคับให้อัปเดตก่อนเข้าใช้งานหรือไม่
    changelog TEXT,                                     -- รายละเอียดการเปลี่ยนแปลง
    released_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- 7. ตารางสถิติการเทรดรายบุคคลและรายแผน (user_plan_stats)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS user_plan_stats (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID REFERENCES users_profile(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    plan_name TEXT NOT NULL,                            -- เช่น 'Plan 0: SMC-LiquidityHunt', 'Plan 1: SR-SwingBounce', etc.
    total_trades INTEGER DEFAULT 0,                     -- จำนวนครั้งที่เข้าไม้ทั้งหมด
    win_trades INTEGER DEFAULT 0,                       -- จำนวนไม้ที่ชนะ
    loss_trades INTEGER DEFAULT 0,                      -- จำนวนไม้ที่แพ้
    win_rate_pct NUMERIC(5, 2) DEFAULT 0.0,             -- อัตราการชนะ (%)
    total_profit_usd NUMERIC(12, 2) DEFAULT 0.0,         -- กำไรสุทธิรวม (USD)
    gross_profit_usd NUMERIC(12, 2) DEFAULT 0.0,         -- กำไรรวมของไม้ที่ได้
    gross_loss_usd NUMERIC(12, 2) DEFAULT 0.0,           -- ขาดทุนรวมของไม้ที่เสีย
    profit_factor NUMERIC(6, 2) DEFAULT 0.0,             -- อัตรากำไร (Profit Factor)
    last_trade_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_plan UNIQUE (user_id, plan_name)
);

CREATE INDEX IF NOT EXISTS idx_user_plan_stats_user ON user_plan_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_user_plan_stats_plan ON user_plan_stats(plan_name);
```

### 1.2 ฟังก์ชันคำนวณและควบคุมสิทธิ์ (PostgreSQL RPC Functions)

#### 🔹 ฟังก์ชันที่ 1: `redeem_product_key` (นำ Product Key มาแลกเป็นชั่วโมง)
```sql
CREATE OR REPLACE FUNCTION redeem_product_key(p_user_id UUID, p_key_code TEXT)
RETURNS JSONB AS $$
DECLARE
    v_key RECORD;
    v_total_hours NUMERIC(10, 2);
    v_new_balance NUMERIC(10, 3);
BEGIN
    -- ค้นหาและล็อกแถว Product Key ป้องกัน Race Condition
    SELECT * INTO v_key FROM product_keys WHERE key_code = p_key_code FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'reason', 'INVALID_KEY', 'message', 'ไม่พบรหัส Product Key นี้ในระบบ');
    END IF;
    
    IF v_key.is_used THEN
        RETURN jsonb_build_object('success', false, 'reason', 'ALREADY_USED', 'message', 'Product Key นี้ถูกใช้งานไปแล้ว');
    END IF;

    v_total_hours := v_key.hours + COALESCE(v_key.bonus_hours, 0);

    -- บันทึกว่าถูกใช้งานแล้ว
    UPDATE product_keys 
    SET is_used = TRUE,
        status = 'REDEEMED',
        redeemed_by_user_id = p_user_id,
        redeemed_at = NOW()
    WHERE key_code = p_key_code;

    -- เติมเวลาเข้ากระเป๋าของ User
    UPDATE users_profile 
    SET hours_remaining = hours_remaining + v_total_hours,
        total_hours_purchased = total_hours_purchased + v_total_hours,
        updated_at = NOW()
    WHERE id = p_user_id
    RETURNING hours_remaining INTO v_new_balance;

    RETURN jsonb_build_object(
        'success', true, 
        'hours_added', v_total_hours,
        'new_balance', round(v_new_balance::numeric, 2),
        'message', 'เติมชั่วโมงการใช้งานสำเร็จเรียบร้อยแล้ว!'
    );
END;
$$ LANGUAGE plpgsql;
```

#### 🔹 ฟังก์ชันที่ 2: `start_bot_session` (ยืนยันสิทธิ์ตอนเปิดบอท)
```sql
CREATE OR REPLACE FUNCTION start_bot_session(
    p_user_id UUID, 
    p_session_id TEXT, 
    p_device_name TEXT DEFAULT 'Windows-PC',
    p_mt5_account BIGINT DEFAULT 0
)
RETURNS JSONB AS $$
DECLARE
    v_usr RECORD;
    v_active_count INTEGER;
BEGIN
    SELECT * INTO v_usr FROM users_profile WHERE id = p_user_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'reason', 'USER_NOT_FOUND');
    END IF;

    IF v_usr.is_suspended THEN
        RETURN jsonb_build_object('success', false, 'reason', 'ACCOUNT_SUSPENDED', 'message', v_usr.suspend_reason);
    END IF;

    IF v_usr.hours_remaining <= 0 THEN
        RETURN jsonb_build_object('success', false, 'reason', 'HOURS_EXPIRED', 'hours_left', 0);
    END IF;

    -- เคลียร์ Session ที่ขาด Heartbeat เกิน 90 วินาทีออกอัตโนมัติ
    DELETE FROM license_sessions 
    WHERE last_heartbeat < (NOW() - INTERVAL '90 seconds');

    -- ตรวจสอบโหมด Concurrency
    IF NOT v_usr.allow_shared_pool THEN
        -- [โหมดมาตรฐาน 1 จอ]: เตะจอเก่าของ User คนนี้ออกทันที
        DELETE FROM license_sessions WHERE user_id = p_user_id;
        
        INSERT INTO license_sessions (session_id, user_id, device_name, mt5_account, last_heartbeat)
        VALUES (p_session_id, p_user_id, p_device_name, p_mt5_account, NOW());

        RETURN jsonb_build_object(
            'success', true, 
            'mode', 'SINGLE', 
            'customer', COALESCE(v_usr.display_name, v_usr.email),
            'hours_left', round(v_usr.hours_remaining::numeric, 2),
            'active_screens', 1
        );
    ELSE
        -- [โหมดแชร์เวลา Shared Pool]: ตรวจสอบจำนวนจอที่เปิดอยู่
        SELECT COUNT(*) INTO v_active_count FROM license_sessions WHERE user_id = p_user_id;
        
        IF v_active_count >= v_usr.max_concurrent_sessions THEN
            RETURN jsonb_build_object(
                'success', false, 
                'reason', 'MAX_SCREENS_REACHED', 
                'limit', v_usr.max_concurrent_sessions
            );
        END IF;

        INSERT INTO license_sessions (session_id, user_id, device_name, mt5_account, last_heartbeat)
        VALUES (p_session_id, p_user_id, p_device_name, p_mt5_account, NOW());

        RETURN jsonb_build_object(
            'success', true, 
            'mode', 'SHARED_POOL', 
            'customer', COALESCE(v_usr.display_name, v_usr.email),
            'hours_left', round(v_usr.hours_remaining::numeric, 2),
            'active_screens', v_active_count + 1,
            'max_screens', v_usr.max_concurrent_sessions
        );
    END IF;
END;
$$ LANGUAGE plpgsql;
```

#### 🔹 ฟังก์ชันที่ 3: `heartbeat_session` (ตัดเวลาทุก 60 วิ และเช็คการเตะหลุด)
```sql
CREATE OR REPLACE FUNCTION heartbeat_session(
    p_user_id UUID, 
    p_session_id TEXT, 
    p_seconds_elapsed INT
)
RETURNS JSONB AS $$
DECLARE
    v_usr RECORD;
    v_new_hours NUMERIC(10, 3);
    v_active_count INTEGER;
BEGIN
    SELECT * INTO v_usr FROM users_profile WHERE id = p_user_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('status', 'USER_NOT_FOUND');
    END IF;

    -- ตรวจสอบว่า Session นี้ยังอยู่หรือไม่ (ถ้าไม่อยู่แสดงว่าโดนจอใหม่เตะออกไปแล้ว)
    IF NOT EXISTS (SELECT 1 FROM license_sessions WHERE session_id = p_session_id) THEN
        RETURN jsonb_build_object('status', 'KICKED_OUT', 'message', 'มีการเปิดใช้งานจากอุปกรณ์อื่นในโหมดจอเดี่ยว');
    END IF;

    UPDATE license_sessions SET last_heartbeat = NOW() WHERE session_id = p_session_id;

    -- คำนวณหักเวลาตามจริงที่จอนี้ใช้ (เช่น 60 วินาที / 3600 = 0.0167 ชม.)
    v_new_hours := GREATEST(0.0, v_usr.hours_remaining - (p_seconds_elapsed::numeric / 3600.0));
    UPDATE users_profile SET hours_remaining = v_new_hours, updated_at = NOW() WHERE id = p_user_id;

    -- ถ้าถังเวลาหมด
    IF v_new_hours <= 0 THEN
        DELETE FROM license_sessions WHERE user_id = p_user_id;
        RETURN jsonb_build_object('status', 'HOURS_EXPIRED', 'hours_left', 0);
    END IF;

    SELECT COUNT(*) INTO v_active_count FROM license_sessions WHERE user_id = p_user_id;

    RETURN jsonb_build_object(
        'status', 'OK', 
        'hours_left', round(v_new_hours::numeric, 2),
        'mode', CASE WHEN v_usr.allow_shared_pool THEN 'SHARED_POOL' ELSE 'SINGLE' END,
        'active_screens', v_active_count
    );
END;
$$ LANGUAGE plpgsql;
```

#### 🔹 ฟังก์ชันที่ 4: `mark_order_paid` (ผลิต Product Key เมื่อชำระเงินสำเร็จ)
```sql
CREATE OR REPLACE FUNCTION mark_order_paid(
    p_order_id TEXT, 
    p_payment_ref TEXT DEFAULT '',
    p_auto_generated_key TEXT DEFAULT ''
)
RETURNS JSONB AS $$
DECLARE
    v_ord RECORD;
    v_pkg RECORD;
    v_key_to_use TEXT;
BEGIN
    SELECT * INTO v_ord FROM orders WHERE order_id = p_order_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'reason', 'ORDER_NOT_FOUND');
    END IF;

    IF v_ord.status = 'PAID' THEN
        RETURN jsonb_build_object('success', true, 'message', 'ALREADY_PAID', 'key_code', v_ord.generated_key_code);
    END IF;

    SELECT * INTO v_pkg FROM packages WHERE id = v_ord.package_id;

    v_key_to_use := p_auto_generated_key;

    -- 1. บันทึก Product Key ลงตาราง product_keys พร้อมผูกกับ User ผู้สั่งซื้อ
    INSERT INTO product_keys (
        key_code, hours, bonus_hours, price_thb, status, is_used, 
        purchased_by_user_id, order_id, purchased_at
    )
    VALUES (
        v_key_to_use, v_pkg.hours, COALESCE(v_pkg.bonus_hours, 0), v_ord.amount_thb, 'UNUSED', FALSE, 
        v_ord.user_id, p_order_id, NOW()
    );

    -- 2. อัปเดตสถานะออเดอร์
    UPDATE orders 
    SET status = 'PAID', 
        payment_ref = p_payment_ref, 
        generated_key_code = v_key_to_use,
        paid_at = NOW() 
    WHERE order_id = p_order_id;

    RETURN jsonb_build_object(
        'success', true, 
        'order_id', p_order_id,
        'product_key', v_key_to_use,
        'hours', v_pkg.hours + COALESCE(v_pkg.bonus_hours, 0)
    );
END;
$$ LANGUAGE plpgsql;
```

---

## เฟสที่ 2: ระบบชำระเงิน Dynamic PromptPay QR & Webhook ตรวจจับเงินเข้า

### 2.1 วงจรการสร้าง QR Code และตรวจเงินเข้า (Payment Life-Cycle)
1. **การขอสร้างออเดอร์**: ลูกค้าเลือกแพ็กเกจ (เช่น 100 ชม. 100 บาท) ➔ ใส่ License Key ➔ กดชำระเงิน
2. **การเจน PromptPay Dynamic QR**:
   * เซิร์ฟเวอร์ Next.js API (`/api/checkout/create-qr`) เรียก Gateway หรือใช้ไลบรารีเจนมาตรฐาน EMVCo PromptPay QR Code ระบุยอดเงินตรงเป๊ะ (เช่น `100.00`) และหมายเลขอ้างอิง `order_id`
   * บันทึกรายการลงตาราง `orders` สถานะ `PENDING`
3. **การชำระเงิน**: ลูกค้าใช้แอปธนาคารใดก็ได้ (KPlus, SCB Easy, Krungthai NEXT ฯลฯ) สแกน QR
4. **การยืนยันเงินเข้าอัตโนมัติ**:
   * **กรณีใช้ Payment Gateway (GB Prime Pay / Omise)**: Gateway ตรวจพบเงินเข้า ➔ ยิง HTTP POST Webhook มาที่ `/api/webhook/payment` ภายใน 1–2 วินาที ➔ ระบบเรียกฟังก์ชัน `mark_order_paid(order_id)`
   * **กรณีใช้ Slip Verification (SlipOK)**: ลูกค้าอัปโหลดสลิป ➔ API ตรวจ Mini-QR ของสลิปกับฐานข้อมูลธนาคาร ➔ ถ้ายอดตรงและเข้าบัญชีจริง ➔ เรียก `mark_order_paid(order_id)` ทันที
5. **Realtime UI Feedback**: หน้าเว็บที่เปิดค้างอยู่ตรวจพบสถานะออเดอร์เปลี่ยนเป็น `PAID` ผ่าน **Supabase Realtime** ➔ เปลี่ยนหน้าจอเป็นความสำเร็จทันที ไม่ต้องกดรีเฟรช

---

## เฟสที่ 3: ระบบหน้าเว็บหน้าร้าน (Storefront), ตรวจเช็คเวลา & Admin Panel

ไฟล์และเส้นทางในโฟลเดอร์ [`web/`](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web):

| เส้นทาง (Route) | หน้าที่การทำงาน | องค์ประกอบสำคัญ |
| :--- | :--- | :--- |
| **`/` หรือ `/store`** | หน้าร้านค้าเลือกซื้อชั่วโมง | • การ์ดแพ็กเกจ (50, 100, 300, 500 ชม. อัตรา 1 บ./ชม.)<br>• ป้ายราคาและชั่วโมงแถมพิเศษ<br>• ปุ่มสั่งซื้อผ่าน QR PromptPay |
| **`/checkout/[orderId]`** | หน้าต่างชำระเงิน QR Code | • รูป Dynamic PromptPay QR Code<br>• ตัวนับเวลาถอยหลัง 10 นาที<br>• Realtime Listener ผลิต Product Key ทันทีเมื่อเงินเข้า |
| **`/dashboard`** | หน้าจัดการบัญชี, กระเป๋าเวลา & สถิติของฉัน | • แสดงชั่วโมงคงเหลือแบบ Real-time<br>• ช่องกรอกรหัส Product Key เพื่อกด **Redeem เติมเวลา**<br>• ดูจำนวนจอที่กำลังออนไลน์ และปุ่มรีเซ็ตเซสชัน<br>• **ดูสถิติการเทรดรายบุคคลและรายแผนของฉัน (My Plan Stats: จำนวนไม้ที่เข้า, Win Rate %, กำไรสุทธิ USD, Profit Factor)** |
| **`/my-keys`** | ประวัติและคลัง Product Key ของฉัน | • รายการ Product Key 6 ชุด ทั้งหมดที่เคยสั่งซื้อ<br>• ป้ายสถานะชัดเจน: 🟢 `UNUSED (พร้อมใช้งาน)` vs ⚪ `REDEEMED (ใช้งานแล้ว)`<br>• ปุ่มคัดลอกรหัส หรือปุ่มกดเติมเข้าบัญชีนี้ทันที |
| **`/admin`** | แผงควบคุมระบบสำหรับ Admin | • จัดการแพ็กเกจ: เพิ่ม/ลบ/แก้ไขราคา/ชั่วโมงแถม<br>• ผลิต Product Key แจกโปรโมชั่นพิเศษ<br>• เปิด/ปิดสิทธิ์ `allow_shared_pool` รายบุคคล และดูสถิติรายได้ |
| **`/admin/analytics`** | แดชบอร์ดวิเคราะห์สถิติภาพรวมทุก User และทุกแผน | • **วิเคราะห์สถิติภาพรวมทุก User และทุกแผนเทรด (All Users & Plans Performance)**<br>• ตรวจสอบจำนวนไม้ที่เข้าแต่ละแผนของลูกค้าทุกคน<br>• สถิติ Win Rate และอัตรากำไรสุทธิเปรียบเทียบระหว่าง Plan 0, 1, 3, 4, 5<br>• ส่งออกรายงานประวัติการเทรดของทุกลูกค้า (CSV Export) |

---

## เฟสที่ 4: ระบบควบคุมสิทธิ์, มิเตอร์เวลา และการเชื่อมต่อ Client Core

### 4.1 ตัวจัดการสิทธิ์และการเติมชั่วโมง ([license_manager.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/license_manager.py))
โมดูลสำหรับจัดการระบบผู้ใช้และการจำกัดสิทธิ์ชั่วโมง รองรับทั้ง Supabase Cloud Auth และโหมด Offline / Local Fallback:
* **รูปแบบการแสดงเวลา**: บังคับแสดงผลในรูปแบบ **`ชั่วโมง.นาที` (`HH.MM`)** เสมอ เช่น `48.30` (48 ชม. 30 นาที) หรือ `72.00`
* **รูปแบบ Product Key**: กำหนดรหัส 6 กลุ่ม กลุ่มละ 4 ตัวอักษร คั่นด้วยขีด **`XXXX-XXXX-XXXX-XXXX-XXXX-XXXX`** (24 หลัก ตัวพิมพ์ใหญ่ Base-32 ปลอดภัย)
* **พฤติกรรมการเติมชั่วโมง**: เป็นแบบ **`+` บวกเพิ่มสะสมจากยอดคงเหลือเดิมเสมอ (Additive Top-up)** ไม่เขียนทับเวลาเดิม
* **ระบบจัดเก็บเซสชันในเครื่อง**: บันทึกข้อมูลลง [license_store.json](file:///d:/โปรเจค/AI_MetaTrader5_FBS/license_store.json) พร้อมตัวเลือก Remember Me
* **Context ผู้ใช้ปัจจุบัน (`get_current_user()`)**: ส่งคืน `{user_id, email, username}` ให้กับโมดูลอื่นๆ เพื่อนำไปผูกกับประวัติการเทรด

### 4.2 ตัวควบคุมและการเชื่อมต่อเครื่องยนต์บอท ([bot_controller.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/bot_controller.py))
ตัวเชื่อมต่อระหว่าง UI กับ [multi_asset_ai_bot.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/multi_asset_ai_bot.py):
* รันการสแกนและเทรดใน Background Daemon Thread ไม่ให้บล็อกหน้าจอ
* **ระบบตัดเวลาตามจริง (Fair Metering Loop)**: ทำงานทุก 60 วินาที ตัดเวลาออก 1 นาที **เฉพาะขณะที่เปิดบอทเทรดจริงเท่านั้น** (เมื่อหยุดบอทชั่วคราวจะหยุดตัดเวลาทันที)
* **ดักจับข้อความ Console (Stdout Redirection)**: ส่งต่อข้อความการวิเคราะห์กราฟและคำสั่งเทรดสดเข้าสู่ Queue เพื่อแสดงผลบนหน้าต่าง GUI
* **ระบบ Emergency Close All**: ปิดทุก Position ของทองคำ XAUUSD ในคลิกเดียว

### 4.3 ระบบบันทึกและคำนวณสถิติรายบุคคลและรายแผน ([stats_manager.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/stats_manager.py))
โมดูลศูนย์กลางสำหรับรวบรวม วิเคราะห์ และจัดเก็บสถิติการเทรดแยกตาม **User ID / Email** และแยกตาม **แผนการเทรดเฉพาะทองคำ 5 แผน**:
* **การระบุตัวตนรายบุคคล (User Trade Attribution)**: ทุกไม้ที่เปิดและปิดจะถูกประทับตรา `user_id` และ `email` ของบัญชีที่ล็อกอินอยู่ ณ ขณะนั้น บันทึกว่าไม้ไหนเป็นของลูกค้าคนใด
* **การติดตามสถิติแยกรายแผน 5 แผนหลัก (Plan-by-Plan Granularity)**:
  * `Plan 0: SMC-LiquidityHunt`
  * `Plan 1: SR-SwingBounce`
  * `Plan 3: BB-H1-Reversion`
  * `Plan 4: MA-Cross-Trend`
  * `Plan 5: MA-Cross-H1-Trend`
* **ตัวชี้วัดประสิทธิภาพครบวงจร (Key Performance Metrics)**:
  * `total_trades`: จำนวนครั้งที่เข้าไม้ทั้งหมดของแผนนั้นๆ
  * `win_trades` / `loss_trades`: จำนวนไม้ที่ชนะและแพ้
  * `win_rate_pct`: อัตราการชนะ (%) = `(win / total) * 100`
  * `total_profit_usd`: กำไรสุทธิรวม (USD)
  * `gross_profit_usd` / `gross_loss_usd`: กำไรก้อนรวมและขาดทุนก้อนรวม
  * `profit_factor`: อัตราส่วนกำไรต่อขาดทุน = `gross_profit / abs(gross_loss)`
* **ระบบจัดเก็บข้อมูลสองระดับ (Dual Persistence Engine)**:
  * **Local Persistence**: บันทึกสถิติรวมลง [user_stats_store.json](file:///d:/โปรเจค/AI_MetaTrader5_FBS/user_stats_store.json) และบันทึกประวัติการเข้าไม้ทุกไม้ลง [user_trade_history.csv](file:///d:/โปรเจค/AI_MetaTrader5_FBS/user_trade_history.csv) ทำให้เปิดดูสถิติได้ทันทีแม้ในโหมดออฟไลน์
  * **Cloud Sync (Supabase)**: ซิงค์สถิติขึ้นตาราง `user_plan_stats` และบันทึกประวัติไม้ลง `trade_logs` ผ่าน [supabase_sync.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/supabase_sync.py) อัตโนมัติทุกครั้งที่มีการเปิดและปิดไม้

---

## เฟสที่ 5: หน้าจอแอปพลิเคชัน Desktop GUI ระดับพรีเมียม ([gui_app.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/gui_app.py))

ระบบหน้าต่างเดสก์ท็อปพัฒนาด้วย **CustomTkinter** ธีม **Dark Obsidian & Gold** สไตล์พรีเมียม รองรับการเปิดผ่าน [run_gui.bat](file:///d:/โปรเจค/AI_MetaTrader5_FBS/run_gui.bat):

### 5.1 หน้าจอเข้าสู่ระบบและสมัครสมาชิก (Login & Register View)
* **ตราสัญลักษณ์และเวอร์ชัน**: `👑 AI MetaTrader 5 Gold Pro v2026.1003.0025`
* **ระบบสลับโหมด Segmented Control**: สลับได้อย่างราบรื่นระหว่าง `[ 🔑 เข้าสู่ระบบ ]` และ `[ ✨ สมัครสมาชิกใหม่ (รับฟรี 48 ชม.) ]`
* **โหมดเข้าสู่ระบบ (Sign In)**: กรอก Email + Password พร้อมตัวเลือก "จดจำการเข้าสู่ระบบในเครื่องนี้ (Remember Me)" เพื่อความสะดวกในการเปิดครั้งถัดไป
* **โหมดสมัครสมาชิกใหม่ (Register)**: กรอก Display Name, Email, Password (ขั้นต่ำ 6 ตัวอักษร) และ Confirm Password พร้อมสร้างบัญชีผู้ใช้จริงบน Supabase Cloud และมอบ **เวลาเริ่มต้นใช้งานจริงฟรีทันที 48.00 ชั่วโมง**
* **ปิดโหมด Demo ถาวร (Zero Demo Bypass)**: ถอนปุ่มทดลองออฟไลน์ออก 100% บังคับยืนยันตัวตนจริงเพื่อความถูกต้องในการคิดชั่วโมงและการบันทึกสถิติ
* **เกราะป้องกันการเริ่มบอท (Auth & License Guard)**: ต้องเข้าสู่ระบบก่อนเท่านั้นจึงจะเข้าสู่หน้า Dashboard ได้ และเมื่อกดปุ่มเริ่มบอท ระบบจะตรวจสอบสิทธิ์และเวลาคงเหลือ (`has_active_hours`) หากหมดเวลาจะหยุดบอทและเปิดหน้าต่างเติมชั่วโมงทันที
* **ลิงก์หน้าเว็บทางการ**: นำทางสู่เว็บสั่งซื้อชั่วโมงและดูประวัติคีย์ `https://goldbot24-4jnnk2of7-noteratchas-projects.vercel.app`

### 5.2 หน้าจอแดชบอร์ดหลัก (Dashboard View)
* **Header Bar**:
  * โลโก้และป้ายระบุสินทรัพย์ `🪙 100% PURE GOLD SPECIALIST (XAUUSD)`
  * **ป้ายตัวนับเวลาคงเหลือ**: แสดงเป็น `XX.YY ชม.` (ชั่วโมง.นาที) พร้อมป้ายสถานะ `🟢 กำลังตัดเวลา (-1 นาที/รอบ)` หรือ `⏸️ หยุดนับเวลา`
  * ปุ่ม **`[ 🔑 + เติมชั่วโมง ]`** เปิดหน้าต่าง Redeem Modal
  * ป้ายโปรไฟล์ผู้ใช้และปุ่ม **`[ 🚪 ออกจากระบบ ]`**
* **แถบการ์ดสถิติสด 4 กล่อง (Top Metric Cards)**:
  1. `🖥️ บัญชี MT5`: เลขที่บัญชี, เซิร์ฟเวอร์โบรกเกอร์ (เช่น `FBS-Demo`), และสถานะการเชื่อมต่อ
  2. `💰 ยอดเงินในพอร์ต`: Balance, Equity, และกำไรลอยตัว (Floating P&L)
  3. `🪙 ราคาทองคำ XAUUSD`: ราคา Bid/Ask สด และค่า Spread (pts)
  4. `📊 สภาวะตลาด (Market Regime)`: H4 Regime (`🐂 BULLISH`, `🐻 BEARISH`, `⚖️ SIDEWAY`) และ H1 Trend
* **แถบแผนการเทรดเฉพาะทองคำ 5 แผน (Gold Specialized Trading Plans Suite)**:
  * ปุ่ม **`[ 📊 ดูสถิติรายแผน (My Stats) ]`** ที่หัวการ์ด สำหรับเปิดหน้าต่างดูสถิติการเทรดแบบละเอียด
  * **ป้ายสถิติสดรายแผน (Live Plan Badges)** ใต้ชื่อแต่ละแผน: แสดง `เข้า: X | WR: Y% | $Z.ZZ` (เช่น `เข้า: 12 | WR: 66.7% | +$145.20`) อัปเดตสดแบบเรียลไทม์ตามผลงานจริงของ User นั้นๆ
* **แผงควบคุม Master Control**:
  * ปุ่มสลับสถานะ: `[ ▶️ เริ่มต้นการทำงานบอท (START) ]` ➔ `[ ⏸️ หยุดชั่วคราว (PAUSE) ]`
  * ปุ่ม Emergency: `[ ⚠️ ปิดทุกไม้ ]`
  * สวิตช์เสียง: `🔊` / `🔇` ควบคุมระบบเสียงของ [sound_manager.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/sound_manager.py)
* **หน้าต่างคอนโซลสด (Live Terminal Console)**:
  * แสดง Log แบบเรียลไทม์พร้อมปุ่ม Auto-scroll และปุ่มล้างข้อความ

### 5.3 หน้าต่างป๊อปอัปเติมชั่วโมง ([RedeemKeyDialog](file:///d:/โปรเจค/AI_MetaTrader5_FBS/gui_app.py))
* **ระบบช่วยจัดรูปแบบอัตโนมัติ (Live Auto-Formatter)**: ตัดช่องว่าง/สัญลักษณ์ และจัดกลุ่มเป็น `XXXX-XXXX-XXXX-XXXX-XXXX-XXXX` ขณะพิมพ์อัตโนมัติ
* **คำนวณเวลาสะสมทันที**: แสดงยอดเวลาเดิม และเวลาใหม่ที่จะได้รับหลังบวกเพิ่ม (+)
* **เสียงแจ้งเตือนความสำเร็จ**: เล่นเสียงกระดิ่งฉลอง 🔔 เมื่อเติมชั่วโมงสำเร็จ

### 5.4 หน้าต่างป๊อปอัปสถิติการเทรดรายบุคคล ([UserStatsDialog](file:///d:/โปรเจค/AI_MetaTrader5_FBS/gui_app.py))
หน้าต่าง Modal แสดงสถิติการเทรดเฉพาะของผู้ใช้ที่กำลังล็อกอินอยู่:
* **กล่องสรุปภาพรวม 4 มิติ (Overall KPI Cards)**:
  1. `จำนวนไม้ทั้งหมด (Total Trades)`
  2. `อัตราการชนะรวม (Overall Win Rate %)`
  3. `กำไรสุทธิรวม (Net Profit USD)`
  4. `อัตรากำไร (Profit Factor)`
* **ตารางแจกแจงสถิติแยกตามแผนทั้ง 5 แผน (5-Plan Detailed Breakdown Table)**:
  * แถวข้อมูลแยกตาม `Plan 0: SMC-LiquidityHunt`, `Plan 1: SR-SwingBounce`, `Plan 3: BB-H1-Reversion`, `Plan 4: MA-Cross-Trend`, `Plan 5: MA-Cross-H1-Trend`
  * คอลัมน์แสดงผล: ชื่อแผน, จำนวนครั้งที่เข้าไม้ (Trades), ชนะ (Win), แพ้ (Loss), Win Rate %, กำไรสุทธิ ($), และ Profit Factor
  * แยกสีชัดเจน: กำไรเป็นสีเขียวมรกต (`#26a69a`) ขาดทุนเป็นสีแดง (`#ef5350`)

---

## เฟสที่ 6: การป้องกันโค้ด (Binary Compilation) และขั้นตอนส่งมอบ

### 6.1 การเข้ารหัสและป้องกัน Reverse Engineering
* **ห้ามส่งไฟล์ `.py` ให้ลูกค้าเด็ดขาด**
* ใช้ **Nuitka** คอมไพล์ [multi_asset_ai_bot.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/multi_asset_ai_bot.py) และโมดูลที่เกี่ยวข้องให้เป็นไฟล์ไบนารี C-Extension (`.pyd` หรือ `.exe` แบบ Standalone)
* กำหนด Flag ป้องกัน Debugger และห้าม Dump Memory เพื่อป้องกันการแกะสูตรเทรด AI และป้องกันการ Bypass ระบบเช็คชั่วโมง

### 6.2 การแพ็กเกจส่งมอบ (Distribution)
* จัดทำไฟล์ Zip สำหรับติดตั้งครั้งแรก (`AI_MT5_Gold_Pro_Setup.zip`)
* ลูกค้าแตกไฟล์ ➔ ใส่ License Key ลงใน `license.key` ➔ ดับเบิ้ลคลิก `Launcher.exe` ➔ บอทพร้อมทำงานทันที

---

## 9. การจัดการเคสข้อยกเว้นและกรณีฉุกเฉิน

| สถานการณ์ | ผลกระทบที่อาจเกิด | วิธีการรับมือที่ออกแบบไว้ (Fail-Safe Protocol) |
| :--- | :--- | :--- |
| **เน็ตของลูกค้าหลุดชั่วคราว (10–30 วินาที)** | Heartbeat อาจส่งไม่สำเร็จ | บอทจะยอมให้ Retry ได้สูงสุด 3 ครั้ง (180 วินาที) ก่อนจะตัดสินใจหยุดรัน เพื่อไม่ให้เด้งหลุดจากเน็ตกระตุก |
| **คอมลูกค้าไฟดับกะทันหัน** | Session ค้างในระบบ | ฟังก์ชัน `start_bot_session` มีระบบกวาดล้าง Session ที่เก่าเกิน 90 วินาทีทิ้งอัตโนมัติ ทำให้ลูกค้าเปิดเครื่องใหม่รันต่อได้ทันที ไม่ติดล็อค |
| **ลูกค้าเปิดเครื่องใหม่ตอนเครื่องเดิมยังรันอยู่** | จอเดิมรันค้างไว้ที่บ้าน | ระบบจะให้สิทธิ์เครื่องใหม่ทันที และส่งสัญญาณ `KICKED_OUT` ไปสั่งปิดเครื่องเดิมอัตโนมัติใน Heartbeat รอบถัดไป |
| **ชั่วโมงหมดขณะมีออเดอร์เปิดค้างอยู่** | เสี่ยงเรื่องออเดอร์ค้าง | บอทจะหยุดส่งสัญญาณเปิดไม้ใหม่ทันที แต่จะ **คงคำสั่ง SL/TP เดิมไว้บนเซิร์ฟเวอร์โบรกเกอร์ MT5** เพื่อปกป้องเงินทุนของลูกค้า |
| **ลูกค้าโอนเงินผิดเศษสตางค์** | ออเดอร์อาจไม่ Match | ระบบ Dynamic QR จะล็อกยอดเงินให้อัตโนมัติในแอปธนาคาร ลูกค้าไม่ต้องกรอกตัวเลขเอง ป้องกันข้อผิดพลาดมนุษย์ 100% |

---

## 10. ตารางตรวจสอบความคืบหน้ารายเฟส

### 🗄️ เฟสที่ 1: Supabase Database & RPC Functions
- [x] 1.1 จัดทำไฟล์ SQL สคริปต์รวมสมบูรณ์พร้อมรันบน Supabase ([supabase_commercial_schema.sql](file:///d:/โปรเจค/AI_MetaTrader5_FBS/supabase_commercial_schema.sql))
- [x] 1.2 สร้างตาราง `users_profile` พร้อม Trigger อัตโนมัติเมื่อสมัครสมาชิก
- [x] 1.3 สร้างตาราง `product_keys` (เก็บบัตรเติมเวลา 6 กลุ่ม 24 หลัก)
- [x] 1.4 สร้างตาราง `license_sessions` (ติดตามจอที่กำลังรันอยู่)
- [x] 1.5 สร้างตาราง `packages` (แพ็กเกจราคา 1 บ./ชม. สำหรับขาย)
- [x] 1.6 สร้างตาราง `orders` (ประวัติการสั่งซื้อและสแกน QR)
- [x] 1.7 สร้างตาราง `app_releases` (เวอร์ชันและ Patch อัปเดต)
- [x] 1.8 สร้างตาราง `user_plan_stats` (สถิติการเทรดรายบุคคลและรายแผน 5 แผน)
- [x] 1.9 สร้างฟังก์ชัน `redeem_product_key()` (แลกเวลาเข้าบัญชีแบบ Atomic)
- [x] 1.10 สร้างฟังก์ชัน `start_bot_session()` (ยืนยันสิทธิ์จอเดี่ยว/แชร์เวลา)
- [x] 1.11 สร้างฟังก์ชัน `heartbeat_session()` (ตัดเวลาถอยหลังทุก 60 วิ)
- [x] 1.12 สร้างฟังก์ชัน `mark_order_paid()` (ผลิต Product Key เมื่อเงินเข้า)
- [x] 1.13 รันคำสั่ง SQL บน Supabase Dashboard จริง และยืนยันการเชื่อมต่อตารางทั้งหมดสำเร็จ 100%

### 💳 เฟสที่ 2: Payment Gateway & SlipOK PromptPay Integration
- [x] 2.1 เลือกผู้ให้บริการชำระเงิน: **SlipOK** (แบรนด์ร้านค้า: **GoldBot24** | ชื่อโปรแกรม: **AI Gold Commander Pro**)
- [x] 2.2 สร้าง API Route เจน PromptPay QR Code บน Next.js (`/api/checkout/create-qr`) เชื่อมโยงรูป QR และบันทึก Orders บน Supabase
- [x] 2.3 สร้าง Webhook Endpoint รับแจ้งเงินเข้าจริงจากธนาคาร (`/api/webhook/payment`) พร้อมตรวจสอบและผลิต Product Key 24 หลักอัตโนมัติ
- [x] 2.4 ระบบตรวจจับสลิปธนาคารอัตโนมัติ (`/api/checkout/verify-slip`) รองรับอัปโหลดสลิปตรวจ QR กับ SlipOK และผลิต Product Key 24 หลักทันที
- [x] 2.5 ยืนยันการเชื่อมต่อ SlipOK จริงสำเร็จ 100% (Branch ID: `77585`, โควต้า: `100 รายการ`, สิทธิการตรวจ: PromptPay 0881232388 / KBank 1198696834 / TrueMoney)

### 🌐 เฟสที่ 3: Web Storefront & Admin Panel (`web/`)
- [x] 3.1 พัฒนา Navigation Bar กลางเชื่อมโยงทุกหน้า ([Navbar.jsx](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/src/components/Navbar.jsx))
- [x] 3.2 หน้าร้านค้าเลือกซื้อแพ็กเกจ 4 แบบ 50-500 ชม. อัตรา 1 บาท/ชม. ([/store](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/src/app/store/page.jsx))
- [x] 3.3 Modal สแกน Dynamic PromptPay QR Code พร้อมตัวนับถอยหลัง 10 นาที
- [x] 3.4 หน้าต่างแสดงรหัส Product Key 24 หลักพร้อมปุ่มคัดลอกเมื่อชำระสำเร็จ
- [x] 3.5 หน้าคลัง Product Key ของฉัน ([/my-keys](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/src/app/my-keys/page.jsx)) แสดงป้าย 🟢 UNUSED vs ⚪ REDEEMED
- [x] 3.6 หน้าแดชบอร์ดกระเป๋าเวลา ([/dashboard](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/src/app/dashboard/page.jsx)) แสดงตัวนับเวลา `ชั่วโมง.นาที` และฟอร์ม Redeem เติมเวลา
- [x] 3.7 แสดงตารางสถิติผลงานรายแผนของฉัน (My Plan Performance) ทั้ง 5 แผนบนหน้า Dashboard
- [x] 3.8 หน้า Admin Analytics ([/admin/analytics](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/src/app/admin/analytics/page.jsx)) ภาพรวมสถิติทุกลูกค้า, ตารางเทียบ 5 แผน และเครื่องผลิต Promo Key
- [x] 3.9 พัฒนาระบบ Authentication เต็มรูปแบบบนเว็บ (`/api/auth/register`, `/api/auth/login`, `/api/auth/me`, `/api/auth/redeem`) พร้อม React Context ([AuthContext.jsx](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/src/context/AuthContext.jsx)) และ Luxury Modal ([AuthModal.jsx](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/src/components/AuthModal.jsx))
- [x] 3.10 ปิดโหมด Demo บนเว็บถาวร: ติดตั้ง **Login Gate Barrier** บล็อกหน้า `/dashboard` และ `/my-keys` ต้องเข้าสู่ระบบก่อนเท่านั้นจึงจะเข้าถึงข้อมูลได้
- [x] 3.11 ทำความสะอาดหน้าจอและซ่อนปุ่มระบบเดิม (รูปที่ 1): ซ่อนปุ่ม `[ 🔑 เซ็ตค่า User / Password ]`, `[ 🗄️ Supabase เชื่อมต่อแล้ว ]` และ `[ || หยุดบอทชั่วคราว ]` ออกจากแถบหัวเว็บ โดยแทนที่ด้วย User Profile Chip `[👤 Name | ⏱️ 48.00 ชม.]`, ปุ่ม `[+ ซื้อชั่วโมง]` และ `[🚪 ออกจากระบบ]`
- [x] 3.12 คอมไพล์และทดสอบ Next.js Production Build ผ่าน 100% ไร้ข้อผิดพลาด
- [x] 3.13 Deploy เว็บขึ้น Vercel Production สำเร็จ 100% (Production URL: `https://goldbot24-4jnnk2of7-noteratchas-projects.vercel.app` เชื่อมต่อ Supabase และ SlipOK เรียบร้อย)
- [x] 3.14 ระบบสิทธิ์ผู้ดูแล (Admin RBAC): API `/api/auth/login` และ `/api/auth/me` ส่งค่า `role` / `isAdmin` (ตรวจจาก `symbols_trading` มี `role:admin` หรืออีเมลขึ้นต้น `admin@`) พร้อมสร้างบัญชีแอดมินแรก `admin@goldbot24.com`
- [x] 3.15 ซ่อนปุ่ม `[ 🛡️ Admin Analytics ]` บน [Navbar.jsx](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/src/components/Navbar.jsx) และลิงก์ใน [Footer.jsx](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/src/components/Footer.jsx) — แสดงเฉพาะเมื่อ Login ด้วย User Admin เท่านั้น
- [x] 3.16 ติดตั้ง **Admin Access Barrier** ในหน้า [/admin/analytics](file:///d:/โปรเจค/AI_MetaTrader5_FBS/web/src/app/admin/analytics/page.jsx) ป้องกันการเข้าผ่าน URL โดยตรง (ผู้ไม่ได้ล็อกอิน/ลูกค้าทั่วไปเห็นการ์ด 🔒 "ต้อง Login ด้วย User Admin เท่านั้น" พร้อมปุ่ม Admin Login / สลับบัญชี)
- [ ] 3.17 ย้ายการตรวจสิทธิ์ Admin ไปฝั่ง Server (API ที่ส่งข้อมูลสถิติ/ผลิต Promo Key ต้องตรวจ Session + Role ก่อนตอบกลับ) และเปลี่ยนข้อมูล Mock ในหน้า Admin เป็นข้อมูลจริงจาก Supabase
- [ ] 3.18 เปลี่ยนรหัสผ่านบัญชีแอดมินเริ่มต้น (`admin123456`) ก่อนเปิดขายจริง

### 🤖 เฟสที่ 4: Client Core & Metering Engine (`license_manager.py` & `bot_controller.py`)
- [x] 4.1 พัฒนาระบบล็อกอิน User + Password และบันทึก Session ในเครื่อง ([license_manager.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/license_manager.py))
- [x] 4.2 ระบบสมัครสมาชิกใหม่ (Register) จากในโปรแกรม พร้อมเข้ารหัสความปลอดภัยสูง PBKDF2-HMAC-SHA256 และมอบ 48 ชั่วโมงฟรี
- [x] 4.3 ระบบ Redeem เติมเวลาด้วย Product Key 24 หลัก `XXXX-XXXX-XXXX-XXXX-XXXX-XXXX` แบบบวกเพิ่ม (+)
- [x] 4.4 ตัวนับเวลาคงเหลือในรูปแบบ `ชั่วโมง.นาที` (`HH.MM`) เสมอ
- [x] 4.5 ฝังตัวเชื่อมต่อและระบบความคุมเข้ากับ [multi_asset_ai_bot.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/multi_asset_ai_bot.py) ผ่าน [bot_controller.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/bot_controller.py)
- [x] 4.6 ทดสอบการตัดชั่วโมงจริงทุกๆ 60 วินาทีเฉพาะตอนเปิดบอท (Fair Metering Loop)
- [x] 4.7 เพิ่มเกราะป้องกันการเริ่มบอท: บังคับตรวจ `license_mgr.is_authenticated` และ `license_mgr.has_active_hours()` ใน `start_bot()` และ `resume_bot()` อย่างเคร่งครัด
- [x] 4.8 พัฒนาระบบบันทึกและรวบรวมสถิติรายบุคคลและรายแผน ([stats_manager.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/stats_manager.py))
- [x] 4.9 เชื่อมโยงการบันทึกไม้เปิด-ปิด (Entry & Exit) และกำไรสุทธิ USD จากบอทเข้าสู่ประวัติ User อัตโนมัติ

### 🚀 เฟสที่ 5: Desktop GUI Suite & Launcher (`gui_app.py` & `run_gui.bat`)
- [x] 5.1 พัฒนาหน้าต่างเดสก์ท็อปพรีเมียม CustomTkinter ธีม Dark Obsidian & Gold ([gui_app.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/gui_app.py))
- [x] 5.2 ปิดโหมด Demo ถาวรบน Desktop: ถอนปุ่ม `⚡ ทดลองใช้งานโหมดออฟไลน์ / Local Demo` และโค้ด Demo Bypass ออก 100%
- [x] 5.3 หน้าจอ Sign In & Register View พร้อมปุ่ม Segmented สลับโหมด `[ 🔑 เข้าสู่ระบบ ]` และ `[ ✨ สมัครสมาชิกใหม่ (รับฟรี 48 ชม.) ]`
- [x] 5.4 ระบบ Login Gate บน Desktop: บล็อกไม่ให้เข้าถึงหน้า Dashboard จนกว่าจะยืนยันตัวตนสำเร็จ
- [x] 5.5 หน้าต่างป๊อปอัปเติมชั่วโมง `RedeemKeyDialog` พร้อม Live Auto-Formatter
- [x] 5.6 แดชบอร์ดตรวจสอบพอร์ต MT5 สด, เรดาร์ทองคำ XAUUSD, และ 5 แผนการเทรด
- [x] 5.7 แผงควบคุม Master Control: Start, Pause, Emergency Close All และ Sound Toggle
- [x] 5.8 กล่อง Live Terminal Console สตรีม Log การทำงานจริงจากบอท
- [x] 5.9 หน้าต่างป๊อปอัปดูสถิติส่วนบุคคล `UserStatsDialog` พร้อมป้ายสถิติสดรายแผนบนการ์ดแดชบอร์ด
- [x] 5.10 สร้าง Batch Launcher สำหรับดับเบิลคลิกเปิดใช้งานบน Windows ([run_gui.bat](file:///d:/โปรเจค/AI_MetaTrader5_FBS/run_gui.bat))
- [x] 5.11 เชื่อมต่อระบบเช็คเวอร์ชันกับ Supabase `app_releases` พร้อมปุ่ม "🔄 อัปเดต" และ Auto-check ใน Desktop GUI
- [x] 5.12 เตรียมข้อมูลเวอร์ชัน Release พร้อม Checksum SHA-256 บน Cloud Database เรียบร้อย
- [x] 5.13 Hotfix: แก้ `_tkinter.TclError: unknown color name "rgba(...)"` ในหน้า Login/Register (กรอบโบนัส 48 ชม.) โดยเปลี่ยนเป็นสี Hex `COLOR_GOLD_BG` / `COLOR_GOLD_DARK` — **กฎ: CustomTkinter รับเฉพาะสี Hex `#RRGGBB` หรือชื่อสี Tk เท่านั้น ห้ามใช้ `rgba()`**

### 🛡️ เฟสที่ 6: Compilation & Deployment
- [x] 6.1 พัฒนาสคริปต์คอมไพล์ไบนารีอัตโนมัติ ([build_dist.py](file:///d:/โปรเจค/AI_MetaTrader5_FBS/build_dist.py)) รองรับ Nuitka / PyInstaller
- [x] 6.2 คอมไพล์โปรแกรมเดสก์ท็อปเป็น Machine Code ไบนารีสำเร็จ (`dist/AI_Gold_Commander_Pro/AI_Gold_Commander_Pro.exe`) ป้องกันการแกะโค้ด 100%
- [x] 6.3 สร้างแพ็กเกจส่งมอบลูกค้าไฟล์ ZIP สมบูรณ์ (`dist/AI_Gold_Commander_Pro_v2026.1003.0025.zip` ขนาด 80.31 MB) พร้อมแนบโฟลเดอร์เสียงและไอคอนครบถ้วน
- [x] 6.4 จัดทำคู่มือเริ่มต้นใช้งานฉบับย่อ ([QUICK_START_GUIDE.txt](file:///d:/โปรเจค/AI_MetaTrader5_FBS/dist/AI_Gold_Commander_Pro/QUICK_START_GUIDE.txt)) ระบุสิทธิ์ฟรี 48 ชม. และลิงก์ร้านค้า Production Vercel เรียบร้อย
- [x] 6.5 คอมไพล์ใหม่หลัง Hotfix สี GUI และทดสอบเปิดหน้าต่าง `MainTradingApp` ผ่าน 100% (ZIP 80.31 MB)
