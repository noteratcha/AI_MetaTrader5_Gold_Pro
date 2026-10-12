-- GoldBot24 — Patch 11: ปิดทางเขียนข้อมูลแบบเดิมด้วย anon key (ปลอมตัวเป็นผู้ใช้อื่นได้)
-- ⚠ รันหลังจากผู้ใช้ส่วนใหญ่อัปเดตโปรแกรมเป็นเวอร์ชันที่ใช้ bot_ingest แล้ว (Patch 10)
--   โปรแกรมเวอร์ชันเก่าจะส่งพอร์ตสด/ประวัติขึ้นเว็บไม่ได้อีก (การเทรดในเครื่องไม่กระทบ)

REVOKE EXECUTE ON FUNCTION public.bot_upsert_telemetry(jsonb)  FROM anon, authenticated;
REVOKE EXECUTE ON FUNCTION public.bot_upsert_plan_stats(jsonb) FROM anon, authenticated;
DO $$ BEGIN
  IF to_regprocedure('public.bot_upsert_telemetry_account(jsonb)') IS NOT NULL THEN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION public.bot_upsert_telemetry_account(jsonb) FROM anon, authenticated';
  END IF;
END $$;

DROP POLICY IF EXISTS "Allow public insert trade_logs"  ON trade_logs;
DROP POLICY IF EXISTS "Allow public insert risk_events" ON risk_events;
DROP POLICY IF EXISTS "Allow public insert signal_logs" ON signal_logs;
REVOKE INSERT ON trade_logs, risk_events, signal_logs FROM anon, authenticated;

NOTIFY pgrst, 'reload schema';
