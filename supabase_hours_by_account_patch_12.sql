-- GoldBot24 — Patch 12: ชั่วโมงสะสมแยกตามบัญชี MT5 (12 ต.ค. 2026) — รันซ้ำได้ · ผู้ใช้รันเองใน Supabase SQL Editor
-- โปรแกรมส่งเลขบัญชี MT5 มากับ /api/auth/meter → บันทึกนาทีรายวันต่อบัญชี (เวลาไทย)
-- ข้อมูลก่อนรัน Patch นี้ไม่มีเลขบัญชี — แสดงเป็น "ไม่ระบุบัญชี" (ส่วนต่างจากยอดรวมใน online_daily)
CREATE TABLE IF NOT EXISTS online_daily_accounts (
    user_id TEXT    NOT NULL,
    day     DATE    NOT NULL,
    login   BIGINT  NOT NULL,
    minutes INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day, login)
);
ALTER TABLE online_daily_accounts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON online_daily_accounts FROM anon, authenticated;

CREATE OR REPLACE FUNCTION add_online_daily_account(p_user TEXT, p_day DATE, p_login BIGINT, p_minutes INTEGER)
RETURNS void LANGUAGE sql AS $$
    INSERT INTO online_daily_accounts (user_id, day, login, minutes) VALUES (p_user, p_day, p_login, GREATEST(p_minutes, 0))
    ON CONFLICT (user_id, day, login) DO UPDATE SET minutes = online_daily_accounts.minutes + GREATEST(EXCLUDED.minutes, 0);
$$;
REVOKE ALL ON FUNCTION add_online_daily_account(TEXT, DATE, BIGINT, INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION add_online_daily_account(TEXT, DATE, BIGINT, INTEGER) TO service_role;

NOTIFY pgrst, 'reload schema';
