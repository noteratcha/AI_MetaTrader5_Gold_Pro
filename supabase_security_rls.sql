-- ==============================================================================
-- GoldBot24 — Security & Ownership Migration (v2026.1004)
-- รันใน Supabase Dashboard → SQL Editor  (รันซ้ำได้ ไม่ทำลายข้อมูล)
--
-- ⚠️ ลำดับการ Deploy:
--   1) ตั้ง Environment บน Vercel: SUPABASE_SERVICE_ROLE_KEY, AUTH_SECRET (+ PAYMENT_WEBHOOK_SECRET ถ้าใช้ Webhook)
--   2) Deploy เว็บเวอร์ชันใหม่ (API ทั้งหมดใช้ Service Role ฝั่ง Server)
--   3) รันไฟล์นี้ — หลังจากนี้ Browser/anon key จะอ่านตารางผู้ใช้/คีย์/คำสั่งซื้อไม่ได้อีก
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 0) สร้างตารางที่ยังไม่มีในฐานข้อมูลจริง (ตารางที่มีอยู่แล้วจะไม่ถูกแตะ)
--    ไม่ใส่ Foreign Key ไป users_profile เพราะผู้ใช้จริงอยู่ใน bot_config
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trade_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket BIGINT,
    time TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    plan TEXT,
    price NUMERIC(14, 5) NOT NULL,
    lot NUMERIC(6, 2) NOT NULL,
    sl NUMERIC(14, 5) DEFAULT 0,
    tp NUMERIC(14, 5) DEFAULT 0,
    profit NUMERIC(10, 2) DEFAULT 0,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_telemetry (
    id INTEGER PRIMARY KEY DEFAULT 1,
    status TEXT DEFAULT 'ONLINE',
    balance NUMERIC(12, 2) DEFAULT 0.0,
    equity NUMERIC(12, 2) DEFAULT 0.0,
    floating_profit NUMERIC(10, 2) DEFAULT 0.0,
    margin_free NUMERIC(12, 2) DEFAULT 0.0,
    open_positions JSONB DEFAULT '[]'::jsonb,
    radar_signals JSONB DEFAULT '[]'::jsonb,
    last_heartbeat TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    time TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    event_type TEXT NOT NULL,
    direction TEXT NOT NULL,
    message TEXT,
    loss_amount NUMERIC(10, 2) DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_risk_events_time ON risk_events (time DESC);

CREATE TABLE IF NOT EXISTS signal_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    time TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    plan TEXT,
    direction TEXT,
    price NUMERIC(14, 5) NOT NULL,
    ai_up NUMERIC(5, 2) DEFAULT 0.0,
    ai_down NUMERIC(5, 2) DEFAULT 0.0,
    h4_trend TEXT,
    status TEXT,
    detail TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_signal_logs_time ON signal_logs (time DESC);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    user_id UUID,
    package_id INTEGER,
    amount_thb NUMERIC(10, 2) NOT NULL,
    hours_to_add NUMERIC(10, 2) NOT NULL,
    status TEXT DEFAULT 'PENDING',
    payment_method TEXT DEFAULT 'PROMPTPAY',
    qr_payload TEXT,
    qr_image_url TEXT,
    payment_ref TEXT,
    generated_key_code TEXT,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_keys (
    key_code TEXT PRIMARY KEY,
    hours NUMERIC(10, 2) NOT NULL,
    bonus_hours NUMERIC(10, 2) DEFAULT 0.00,
    price_thb NUMERIC(10, 2) DEFAULT 0.00,
    status TEXT DEFAULT 'UNUSED',
    is_used BOOLEAN DEFAULT FALSE,
    purchased_by_user_id UUID,
    order_id TEXT,
    purchased_at TIMESTAMPTZ DEFAULT NOW(),
    redeemed_by_user_id UUID,
    redeemed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_plan_stats (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT,
    email TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    total_trades INTEGER DEFAULT 0,
    win_trades INTEGER DEFAULT 0,
    loss_trades INTEGER DEFAULT 0,
    win_rate_pct NUMERIC(5, 2) DEFAULT 0.0,
    total_profit_usd NUMERIC(12, 2) DEFAULT 0.0,
    gross_profit_usd NUMERIC(12, 2) DEFAULT 0.0,
    gross_loss_usd NUMERIC(12, 2) DEFAULT 0.0,
    profit_factor NUMERIC(6, 2) DEFAULT 0.0,
    last_trade_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_plan UNIQUE (user_id, plan_name)
);

CREATE TABLE IF NOT EXISTS app_releases (
    version TEXT PRIMARY KEY,
    download_url TEXT NOT NULL,
    checksum_sha256 TEXT NOT NULL DEFAULT '',
    mandatory BOOLEAN DEFAULT TRUE,
    changelog TEXT,
    released_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 1) คอลัมน์ใหม่สำหรับระบุเจ้าของข้อมูล
-- ------------------------------------------------------------------------------
ALTER TABLE orders       ADD COLUMN IF NOT EXISTS owner_user_id TEXT;
ALTER TABLE orders       ADD COLUMN IF NOT EXISTS owner_email   TEXT;
CREATE INDEX IF NOT EXISTS idx_orders_owner_email ON orders(owner_email);

ALTER TABLE product_keys ADD COLUMN IF NOT EXISTS owner_email       TEXT;
ALTER TABLE product_keys ADD COLUMN IF NOT EXISTS redeemed_by_email TEXT;

ALTER TABLE trade_logs   ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE trade_logs   ADD COLUMN IF NOT EXISTS email   TEXT;
CREATE INDEX IF NOT EXISTS idx_trade_logs_email ON trade_logs(email, time DESC);

-- promo_keys (ถ้ายังไม่มีตาราง)
CREATE TABLE IF NOT EXISTS promo_keys (
    key_code   TEXT PRIMARY KEY,
    hours      NUMERIC(10, 2) NOT NULL,
    used       BOOLEAN DEFAULT FALSE,
    used_by    TEXT,
    used_at    TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE promo_keys ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE promo_keys ADD COLUMN IF NOT EXISTS created_by TEXT;
ALTER TABLE promo_keys ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- user_plan_stats.user_id เดิมเป็น UUID อ้างอิง users_profile แต่ผู้ใช้จริงอยู่ใน bot_config (id ตัวเลข)
ALTER TABLE user_plan_stats DROP CONSTRAINT IF EXISTS user_plan_stats_user_id_fkey;
ALTER TABLE user_plan_stats ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;

-- ------------------------------------------------------------------------------
-- 2) Row Level Security
--    Service Role (ฝั่ง Server) ข้าม RLS ได้เสมอ — policy ด้านล่างคือสิทธิ์ของ anon key เท่านั้น
-- ------------------------------------------------------------------------------
ALTER TABLE bot_config      ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders          ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_keys    ENABLE ROW LEVEL SECURITY;
ALTER TABLE promo_keys      ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_plan_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_telemetry   ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_logs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_events     ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_logs     ENABLE ROW LEVEL SECURITY;

-- ลบ policy เปิดสาธารณะเดิม (อ่าน/แก้ hash รหัสผ่านและชั่วโมงของทุกคนได้)
DROP POLICY IF EXISTS "Allow public read bot_config"    ON bot_config;
DROP POLICY IF EXISTS "Allow public update bot_config"  ON bot_config;
DROP POLICY IF EXISTS "Allow public insert bot_config"  ON bot_config;
DROP POLICY IF EXISTS "Allow public read bot_telemetry" ON bot_telemetry;
DROP POLICY IF EXISTS "Allow public read trade_logs"    ON trade_logs;
DROP POLICY IF EXISTS "Allow public read risk_events"   ON risk_events;
DROP POLICY IF EXISTS "Allow public read signal_logs"   ON signal_logs;

-- ลบ policy ใด ๆ ที่เหลือ (รวมที่สร้างจาก Dashboard ด้วยชื่ออื่น) แล้วสร้างเฉพาะที่จำเป็นใหม่ด้านล่าง
DO $$
DECLARE pol RECORD;
BEGIN
  FOR pol IN
    SELECT policyname, tablename FROM pg_policies
    WHERE schemaname = 'public' AND tablename IN ('orders', 'product_keys', 'promo_keys', 'user_plan_stats', 'bot_config',
                                                 'bot_telemetry', 'trade_logs', 'risk_events', 'signal_logs', 'app_releases')
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', pol.policyname, pol.tablename);
  END LOOP;
END $$;

-- Desktop Bot (anon key) ยังเขียนข้อมูลสดได้ แต่ "อ่าน" ไม่ได้ — เว็บอ่านผ่าน API (Service Role) แทน
DROP POLICY IF EXISTS "Bot insert bot_telemetry" ON bot_telemetry;
DROP POLICY IF EXISTS "Bot update bot_telemetry" ON bot_telemetry;
CREATE POLICY "Bot insert bot_telemetry" ON bot_telemetry FOR INSERT WITH CHECK (id > 1);
CREATE POLICY "Bot update bot_telemetry" ON bot_telemetry FOR UPDATE USING (id > 1) WITH CHECK (id > 1);
-- PostgREST upsert (merge-duplicates) ต้องมีสิทธิ์ SELECT แถวที่ชนกันด้วย — จำกัดไว้เฉพาะคอลัมน์ id
REVOKE SELECT ON bot_telemetry FROM anon;
GRANT SELECT (id) ON bot_telemetry TO anon;
DROP POLICY IF EXISTS "Bot upsert check bot_telemetry" ON bot_telemetry;
CREATE POLICY "Bot upsert check bot_telemetry" ON bot_telemetry FOR SELECT USING (id > 1);

DROP POLICY IF EXISTS "Allow public insert trade_logs"  ON trade_logs;
DROP POLICY IF EXISTS "Allow public insert risk_events" ON risk_events;
DROP POLICY IF EXISTS "Allow public insert signal_logs" ON signal_logs;
CREATE POLICY "Allow public insert trade_logs"  ON trade_logs  FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public insert risk_events" ON risk_events FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public insert signal_logs" ON signal_logs FOR INSERT WITH CHECK (true);

-- user_plan_stats: Desktop upsert สถิติของตัวเอง (ไม่มีสิทธิ์อ่าน)
CREATE POLICY "Bot insert user_plan_stats" ON user_plan_stats FOR INSERT WITH CHECK (true);
CREATE POLICY "Bot update user_plan_stats" ON user_plan_stats FOR UPDATE USING (true) WITH CHECK (true);
REVOKE SELECT ON user_plan_stats FROM anon;
GRANT SELECT (user_id, plan_name) ON user_plan_stats TO anon;
CREATE POLICY "Bot upsert check user_plan_stats" ON user_plan_stats FOR SELECT USING (true);

-- app_releases เป็นข้อมูลสาธารณะ (Desktop ตรวจอัปเดต)
ALTER TABLE app_releases ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read app_releases" ON app_releases;
CREATE POLICY "Public read app_releases" ON app_releases FOR SELECT USING (true);

-- ------------------------------------------------------------------------------
-- 3) ปิด Realtime ของ bot_config (เดิม broadcast ทุกแถว รวม hash รหัสผ่าน ไปยังทุก Browser)
-- ------------------------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_publication_tables WHERE pubname = 'supabase_realtime' AND tablename = 'bot_config') THEN
    ALTER PUBLICATION supabase_realtime DROP TABLE bot_config;
  END IF;
END $$;

-- ------------------------------------------------------------------------------
-- 4) ล้างรหัสผ่าน MT5 แบบ plaintext ที่เคยซิงค์ขึ้นแถว config (id = 1)
-- ------------------------------------------------------------------------------
UPDATE bot_config SET mt5_password = '' WHERE id = 1;
