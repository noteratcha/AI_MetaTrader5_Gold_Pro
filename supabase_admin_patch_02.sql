-- ==============================================================================
-- GoldBot24 — Admin Patch 02 (v2026.1005)  รันต่อจาก supabase_security_rls_patch_01.sql
-- ระบบแอดมิน: แพ็กเกจในฐานข้อมูล, ตั้งค่าระบบ (เปิด/ปิดแผนเทรด), Log กิจกรรมผู้ใช้,
-- ผูก log สัญญาณ/ความเสี่ยงกับผู้ใช้, View สรุปการเทรดรายผู้ใช้
-- (รันซ้ำได้ ไม่ทำลายข้อมูล)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1) แพ็กเกจชั่วโมง (แก้ไขได้จากหน้าแอดมิน)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS packages (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    hours NUMERIC(10, 2) NOT NULL,
    bonus_hours NUMERIC(10, 2) DEFAULT 0.00,
    price_thb NUMERIC(10, 2) NOT NULL,
    badge TEXT DEFAULT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE packages ADD COLUMN IF NOT EXISTS accent TEXT DEFAULT 'gold';
ALTER TABLE packages ADD COLUMN IF NOT EXISTS featured BOOLEAN DEFAULT FALSE;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS badge TEXT;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 1;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- ใส่แพ็กเกจเริ่มต้นเฉพาะเมื่อยังไม่มีข้อมูล
INSERT INTO packages (id, name, hours, bonus_hours, price_thb, badge, description, sort_order, accent, featured)
SELECT * FROM (VALUES
  (1, 'Starter 50',   50::NUMERIC,  0::NUMERIC,  50::NUMERIC,  NULL,          'ทดลองรันบอททองคำจริงต่อเนื่อง 2–3 วัน',      1, 'sky',     FALSE),
  (2, 'Popular 100',  100,          0,           100,          'ขายดี',        'รันได้ครบ 1 สัปดาห์ ไม่พลาดรอบสวิง H1',       2, 'orange',  TRUE),
  (3, 'Value 300',    300,          20,          300,          'แถม 20 ชม.',   'คุ้มขึ้น ได้เวลารวม 320 ชั่วโมง',              3, 'emerald', FALSE),
  (4, 'Marathon 500', 500,          50,          500,          'แถม 50 ชม.',   'สำหรับรันบน VPS ยาว ๆ ได้เวลารวม 550 ชั่วโมง', 4, 'gold',    FALSE)
) AS v(id, name, hours, bonus_hours, price_thb, badge, description, sort_order, accent, featured)
WHERE NOT EXISTS (SELECT 1 FROM packages);
SELECT setval(pg_get_serial_sequence('packages', 'id'), GREATEST((SELECT COALESCE(MAX(id), 1) FROM packages), 1));

-- ------------------------------------------------------------------------------
-- 2) ตั้งค่าระบบ (เช่น enabled_plans) — Server อ่าน/เขียนด้วย Service Role เท่านั้น
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_by TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO app_settings (key, value) VALUES
  ('enabled_plans', '{"SMC-LiquidityHunt": true, "SR-SwingBounce": true, "BB-H1-Reversion": true, "MA-Cross-Trend": true, "MA-Cross-H1-Trend": true}'::jsonb)
ON CONFLICT (key) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 3) Log กิจกรรมผู้ใช้ (ล็อกอิน, เติมคีย์, ซื้อแพ็กเกจ, การแก้ไขโดยแอดมิน ฯลฯ)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_activity (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT,
    email TEXT,
    event TEXT NOT NULL,
    detail TEXT,
    actor TEXT,                 -- ผู้กระทำ (อีเมลแอดมิน กรณีแก้ไขโดยแอดมิน)
    ip TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_activity_email ON user_activity (email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_event ON user_activity (event, created_at DESC);

-- ------------------------------------------------------------------------------
-- 4) ผูก log สัญญาณ/ความเสี่ยงกับผู้ใช้
-- ------------------------------------------------------------------------------
ALTER TABLE signal_logs ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE signal_logs ADD COLUMN IF NOT EXISTS email   TEXT;
ALTER TABLE risk_events ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE risk_events ADD COLUMN IF NOT EXISTS email   TEXT;
CREATE INDEX IF NOT EXISTS idx_signal_logs_email ON signal_logs (email, time DESC);
CREATE INDEX IF NOT EXISTS idx_risk_events_email ON risk_events (email, time DESC);

-- ------------------------------------------------------------------------------
-- 5) สรุปการเทรดรายผู้ใช้ (ใช้ในหน้าแอดมิน)
--    CLOSE ที่ comment มี "Manual" / "Emergency" = ผู้ใช้ปิดเอง, CLOSE อื่น = บอทปิดตามสัญญาณ
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW admin_user_trade_summary AS
SELECT
    lower(email)                                                                AS email,
    COUNT(*) FILTER (WHERE action IN ('OPEN_BUY', 'OPEN_SELL'))                 AS opens,
    COUNT(*) FILTER (WHERE action = 'TP_HIT')                                   AS tp_hits,
    COUNT(*) FILTER (WHERE action = 'SL_HIT')                                   AS sl_hits,
    COUNT(*) FILTER (WHERE action = 'CLOSE' AND (comment ILIKE '%manual%' OR comment ILIKE '%emergency%')) AS manual_closes,
    COUNT(*) FILTER (WHERE action = 'CLOSE' AND NOT (comment ILIKE '%manual%' OR comment ILIKE '%emergency%')) AS bot_closes,
    COALESCE(SUM(profit) FILTER (WHERE action IN ('TP_HIT', 'SL_HIT', 'CLOSE')), 0) AS net_profit,
    MAX(time)                                                                   AS last_trade_at
FROM trade_logs
WHERE email IS NOT NULL
GROUP BY lower(email);

-- ------------------------------------------------------------------------------
-- 6) สิทธิ์: ตารางใหม่อ่าน/เขียนได้เฉพาะ Service Role (ผ่าน API ฝั่ง Server)
-- ------------------------------------------------------------------------------
ALTER TABLE packages      ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_settings  ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_activity ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON packages, app_settings, user_activity FROM anon, authenticated;
REVOKE ALL ON admin_user_trade_summary FROM anon, authenticated;

NOTIFY pgrst, 'reload schema';
