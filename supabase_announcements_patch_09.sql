-- GoldBot24 — Patch 09: ข่าวสาร/โปรโมชัน (รูป + ข้อความ) แสดงทั้งเว็บและโปรแกรม — รันซ้ำได้ · ผู้ใช้รันเองใน Supabase SQL Editor
CREATE TABLE IF NOT EXISTS announcements (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title       TEXT NOT NULL,
    body        TEXT DEFAULT '',
    image_url   TEXT,
    link_url    TEXT,
    link_label  TEXT,
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    popup       BOOLEAN NOT NULL DEFAULT TRUE,     -- เด้งหน้าต่างครั้งแรกที่ผู้ใช้ยังไม่เคยเห็น
    starts_at   TIMESTAMPTZ DEFAULT NOW(),
    ends_at     TIMESTAMPTZ,
    created_by  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_announcements_active ON announcements (active, starts_at DESC);
ALTER TABLE announcements ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON announcements FROM anon, authenticated;   -- อ่าน/เขียนผ่าน /api/* (Service Role) เท่านั้น

-- ที่เก็บรูปข่าวสาร (อ่านได้สาธารณะ · อัปโหลดผ่าน /api/admin/announcements เท่านั้น)
INSERT INTO storage.buckets (id, name, public)
VALUES ('announcements', 'announcements', TRUE)
ON CONFLICT (id) DO UPDATE SET public = TRUE;

-- ประวัติการสะสมชั่วโมงรายวัน (นาทีที่หักจริงจาก /api/auth/meter · วันตามเวลาไทย) — แสดงในเว็บ/โปรแกรม
CREATE TABLE IF NOT EXISTS online_daily (
    user_id TEXT NOT NULL,
    day     DATE NOT NULL,
    minutes INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day)
);
ALTER TABLE online_daily ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON online_daily FROM anon, authenticated;

CREATE OR REPLACE FUNCTION add_online_daily(p_user TEXT, p_day DATE, p_minutes INTEGER)
RETURNS void LANGUAGE sql AS $$
    INSERT INTO online_daily (user_id, day, minutes) VALUES (p_user, p_day, GREATEST(p_minutes, 0))
    ON CONFLICT (user_id, day) DO UPDATE SET minutes = online_daily.minutes + GREATEST(EXCLUDED.minutes, 0);
$$;
REVOKE ALL ON FUNCTION add_online_daily(TEXT, DATE, INTEGER) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION add_online_daily(TEXT, DATE, INTEGER) TO service_role;

NOTIFY pgrst, 'reload schema';
