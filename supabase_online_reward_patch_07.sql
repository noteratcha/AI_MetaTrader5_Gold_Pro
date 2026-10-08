-- ==============================================================================
-- GoldBot24 — Patch 07: รางวัลออนไลน์ครบ 100 ชม. → ส่วนลด 10% ซื้อชั่วโมงครั้งถัดไป 1 รายการ (รันซ้ำได้)
-- - นับเฉพาะนาทีที่โปรแกรมหักเวลาจริง (/api/auth/meter = บอททำงาน + ตลาดเปิด)
-- - สะสมเป็นรอบ: ครบ 100 ชม. ได้ส่วนลด 1 สิทธิ์ แล้วเริ่มนับรอบใหม่ทันที (เศษเกินยกไปรอบถัดไป)
-- - ส่วนลดใช้ได้ภายใน 3 วันนับจากเวลาที่ได้รับ
-- - อ่าน/เขียนได้เฉพาะ Service Role ผ่าน API ฝั่ง Server
-- ==============================================================================
CREATE TABLE IF NOT EXISTS online_progress (
    user_id TEXT PRIMARY KEY,
    email TEXT,
    minutes INTEGER NOT NULL DEFAULT 0,        -- นาทีสะสมของรอบปัจจุบัน (0 – 5,999)
    cycles INTEGER NOT NULL DEFAULT 0,         -- จำนวนรอบที่ครบแล้วทั้งหมด
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS online_discounts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    email TEXT,
    cycle_no INTEGER,
    percent INTEGER NOT NULL DEFAULT 10,
    earned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',   -- ACTIVE · RESERVED (ผูกกับคำสั่งซื้อที่รอชำระ) · USED
    order_id TEXT,
    used_at TIMESTAMPTZ
);
-- กรณีเคยรันฉบับรายสัปดาห์ไปแล้ว
ALTER TABLE online_discounts ADD COLUMN IF NOT EXISTS cycle_no INTEGER;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'online_discounts' AND column_name = 'week_start') THEN
        ALTER TABLE online_discounts ALTER COLUMN week_start DROP NOT NULL;
        ALTER TABLE online_discounts DROP CONSTRAINT IF EXISTS online_discounts_user_id_week_start_key;
    END IF;
END $$;
CREATE UNIQUE INDEX IF NOT EXISTS uq_online_discounts_cycle ON online_discounts (user_id, cycle_no);
CREATE INDEX IF NOT EXISTS idx_online_discounts_user ON online_discounts (user_id, expires_at DESC);

-- คำสั่งซื้อที่ใช้ส่วนลด
ALTER TABLE orders ADD COLUMN IF NOT EXISTS discount_id BIGINT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS discount_pct INTEGER;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS original_amount_thb NUMERIC(10, 2);

-- บวกนาทีแบบ atomic: ครบ p_goal นาทีตัดเป็นรอบ (เศษยกไป) → คืน (นาทีรอบปัจจุบัน, รอบที่ครบในครั้งนี้, จำนวนรอบรวม)
DROP FUNCTION IF EXISTS add_online_minutes(TEXT, TEXT, DATE, INTEGER);
CREATE OR REPLACE FUNCTION add_online_minutes(p_user TEXT, p_email TEXT, p_minutes INTEGER, p_goal INTEGER)
RETURNS TABLE (minutes INTEGER, earned INTEGER, cycles INTEGER) LANGUAGE plpgsql AS $$
DECLARE
    total INTEGER;
BEGIN
    INSERT INTO online_progress AS p (user_id, email, minutes, updated_at)
    VALUES (p_user, p_email, GREATEST(p_minutes, 0), NOW())
    ON CONFLICT (user_id) DO UPDATE SET minutes = p.minutes + GREATEST(EXCLUDED.minutes, 0), email = EXCLUDED.email, updated_at = NOW()
    RETURNING p.minutes INTO total;
    earned := total / p_goal;
    UPDATE online_progress AS p SET minutes = total % p_goal, cycles = p.cycles + earned
    WHERE p.user_id = p_user
    RETURNING p.minutes, p.cycles INTO minutes, cycles;
    RETURN NEXT;
END;
$$;

ALTER TABLE online_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE online_discounts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON online_progress FROM anon, authenticated;
REVOKE ALL ON online_discounts FROM anon, authenticated;
REVOKE EXECUTE ON FUNCTION add_online_minutes(TEXT, TEXT, INTEGER, INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION add_online_minutes(TEXT, TEXT, INTEGER, INTEGER) TO service_role;

NOTIFY pgrst, 'reload schema';
