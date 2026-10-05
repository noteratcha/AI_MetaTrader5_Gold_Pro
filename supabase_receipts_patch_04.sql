-- ==============================================================================
-- GoldBot24 — Patch 04: ใบเสร็จรับเงิน (ออกอัตโนมัติเมื่อชำระเงินสำเร็จ + ส่งอีเมล)
-- (รันซ้ำได้) — อ่าน/เขียนได้เฉพาะ Service Role ผ่าน API ฝั่ง Server
-- เลขที่ใบเสร็จ: GB24-YYYYMM-000001 (เรียงต่อเนื่องจาก sequence)
-- ==============================================================================
CREATE SEQUENCE IF NOT EXISTS receipt_no_seq START 1;

CREATE TABLE IF NOT EXISTS receipts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    receipt_no TEXT NOT NULL UNIQUE DEFAULT (
        'GB24-' || to_char(NOW() AT TIME ZONE 'Asia/Bangkok', 'YYYYMM') || '-' || lpad(nextval('receipt_no_seq')::text, 6, '0')
    ),
    order_id TEXT NOT NULL UNIQUE,      -- 1 คำสั่งซื้อ = 1 ใบเสร็จ
    user_id TEXT,
    email TEXT,
    customer_name TEXT,
    item_name TEXT NOT NULL,
    hours NUMERIC(10, 2) NOT NULL DEFAULT 0,
    amount_thb NUMERIC(10, 2) NOT NULL DEFAULT 0,
    payment_method TEXT,
    payment_ref TEXT,
    product_key TEXT,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    emailed_at TIMESTAMPTZ,             -- ส่งอีเมลสำเร็จล่าสุด
    email_error TEXT,                   -- ข้อความ error ถ้าส่งไม่สำเร็จ
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_receipts_email ON receipts (email, issued_at DESC);

ALTER TABLE receipts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON receipts FROM anon, authenticated;
REVOKE ALL ON SEQUENCE receipt_no_seq FROM anon, authenticated;

NOTIFY pgrst, 'reload schema';
