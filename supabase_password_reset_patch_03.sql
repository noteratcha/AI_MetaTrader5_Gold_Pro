-- ==============================================================================
-- GoldBot24 — Patch 03: ลืมรหัสผ่าน (รหัสยืนยัน 6 หลักทางอีเมล)
-- (รันซ้ำได้) — อ่าน/เขียนได้เฉพาะ Service Role ผ่าน API ฝั่ง Server
-- ==============================================================================
CREATE TABLE IF NOT EXISTS password_resets (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    email TEXT NOT NULL,
    code_hash TEXT NOT NULL,          -- HMAC ของรหัส (ไม่เก็บรหัสจริง)
    expires_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER DEFAULT 0,       -- จำนวนครั้งที่กรอกผิด
    used_at TIMESTAMPTZ,
    ip TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_password_resets_email ON password_resets (email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_password_resets_ip ON password_resets (ip, created_at DESC);

ALTER TABLE password_resets ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON password_resets FROM anon, authenticated;

NOTIFY pgrst, 'reload schema';
