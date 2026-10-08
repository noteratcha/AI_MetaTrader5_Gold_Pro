-- ==============================================================================
-- GoldBot24 — Patch 07: รางวัลออนไลน์ครบ 100 ชม./สัปดาห์ → ส่วนลด 10% ซื้อชั่วโมงครั้งถัดไป 1 รายการ (รันซ้ำได้)
-- - นับเฉพาะนาทีที่โปรแกรมหักเวลาจริง (/api/auth/meter = บอททำงาน + ตลาดเปิด)
-- - สัปดาห์ = อาทิตย์ 00:00 – เสาร์ 23:59 เวลาไทย (week_start = วันอาทิตย์)
-- - ส่วนลดใช้ได้ภายใน 5 วันนับจากวันที่ได้รับ · 1 สัปดาห์ได้ 1 สิทธิ์
-- - อ่าน/เขียนได้เฉพาะ Service Role ผ่าน API ฝั่ง Server
-- ==============================================================================
CREATE TABLE IF NOT EXISTS online_weekly (
    user_id TEXT NOT NULL,
    week_start DATE NOT NULL,
    email TEXT,
    minutes INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, week_start)
);

CREATE TABLE IF NOT EXISTS online_discounts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    email TEXT,
    week_start DATE NOT NULL,
    percent INTEGER NOT NULL DEFAULT 10,
    earned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE · RESERVED (ผูกกับคำสั่งซื้อที่รอชำระ) · USED
    order_id TEXT,
    used_at TIMESTAMPTZ,
    UNIQUE (user_id, week_start)
);
CREATE INDEX IF NOT EXISTS idx_online_discounts_user ON online_discounts (user_id, expires_at DESC);

-- คำสั่งซื้อที่ใช้ส่วนลด
ALTER TABLE orders ADD COLUMN IF NOT EXISTS discount_id BIGINT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS discount_pct INTEGER;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS original_amount_thb NUMERIC(10, 2);

-- บวกนาทีออนไลน์แบบ atomic → คืนยอดรวมของสัปดาห์
CREATE OR REPLACE FUNCTION add_online_minutes(p_user TEXT, p_email TEXT, p_week DATE, p_minutes INTEGER)
RETURNS INTEGER LANGUAGE sql AS $$
    INSERT INTO online_weekly (user_id, email, week_start, minutes, updated_at)
    VALUES (p_user, p_email, p_week, GREATEST(p_minutes, 0), NOW())
    ON CONFLICT (user_id, week_start)
    DO UPDATE SET minutes = online_weekly.minutes + GREATEST(EXCLUDED.minutes, 0), updated_at = NOW()
    RETURNING minutes;
$$;

ALTER TABLE online_weekly ENABLE ROW LEVEL SECURITY;
ALTER TABLE online_discounts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON online_weekly FROM anon, authenticated;
REVOKE ALL ON online_discounts FROM anon, authenticated;
REVOKE EXECUTE ON FUNCTION add_online_minutes(TEXT, TEXT, DATE, INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION add_online_minutes(TEXT, TEXT, DATE, INTEGER) TO service_role;

NOTIFY pgrst, 'reload schema';
