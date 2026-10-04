-- ==============================================================================
-- GoldBot24 — RLS Patch 01 (v2026.1004)  รันต่อจาก supabase_security_rls.sql
--
-- ปัญหา: PostgREST upsert (merge-duplicates) ต้องมีสิทธิ์ SELECT ทั้งตาราง
--        ถ้าให้ anon อ่านได้ จะเห็นยอดเงิน/ออเดอร์ของทุกคน
-- แก้:   Desktop Bot เขียนผ่านฟังก์ชัน SECURITY DEFINER (เขียนได้อย่างเดียว อ่านไม่ได้)
--        และถอนสิทธิ์ INSERT/UPDATE/SELECT ตรงของ anon บน 2 ตารางนี้
-- (รันซ้ำได้)
-- ==============================================================================

-- 1) Telemetry พอร์ตสด (1 แถวต่อ 1 บัญชี GoldBot24)
CREATE OR REPLACE FUNCTION public.bot_upsert_telemetry(p jsonb)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_id INTEGER := NULLIF(p->>'id', '')::INTEGER;
BEGIN
  IF v_id IS NULL OR v_id <= 1 THEN
    RAISE EXCEPTION 'invalid telemetry id';
  END IF;
  IF pg_column_size(p) > 200000 THEN
    RAISE EXCEPTION 'telemetry payload too large';
  END IF;

  INSERT INTO bot_telemetry (id, status, balance, equity, floating_profit, margin_free, open_positions, radar_signals, last_heartbeat)
  VALUES (
    v_id,
    LEFT(COALESCE(p->>'status', 'ONLINE'), 60),
    COALESCE((p->>'balance')::NUMERIC, 0),
    COALESCE((p->>'equity')::NUMERIC, 0),
    COALESCE((p->>'floating_profit')::NUMERIC, 0),
    COALESCE((p->>'margin_free')::NUMERIC, 0),
    COALESCE(p->'open_positions', '[]'::jsonb),
    COALESCE(p->'radar_signals', '[]'::jsonb),
    NOW()
  )
  ON CONFLICT (id) DO UPDATE SET
    status          = EXCLUDED.status,
    balance         = EXCLUDED.balance,
    equity          = EXCLUDED.equity,
    floating_profit = EXCLUDED.floating_profit,
    margin_free     = EXCLUDED.margin_free,
    open_positions  = EXCLUDED.open_positions,
    radar_signals   = EXCLUDED.radar_signals,
    last_heartbeat  = EXCLUDED.last_heartbeat;
END;
$$;

-- 2) สถิติรายแผนของผู้ใช้
CREATE OR REPLACE FUNCTION public.bot_upsert_plan_stats(p jsonb)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_user TEXT := NULLIF(p->>'user_id', '');
  v_plan TEXT := NULLIF(p->>'plan_name', '');
BEGIN
  IF v_user IS NULL OR v_plan IS NULL OR v_user !~ '^[0-9]+$' OR v_user::BIGINT <= 1 THEN
    RAISE EXCEPTION 'invalid user_id / plan_name';
  END IF;

  INSERT INTO user_plan_stats (user_id, email, plan_name, total_trades, win_trades, loss_trades,
                               win_rate_pct, total_profit_usd, profit_factor, updated_at)
  VALUES (
    v_user,
    LEFT(COALESCE(p->>'email', ''), 200),
    LEFT(v_plan, 80),
    COALESCE((p->>'total_trades')::INTEGER, 0),
    COALESCE((p->>'win_trades')::INTEGER, 0),
    COALESCE((p->>'loss_trades')::INTEGER, 0),
    LEAST(COALESCE((p->>'win_rate_pct')::NUMERIC, 0), 100),
    COALESCE((p->>'total_profit_usd')::NUMERIC, 0),
    LEAST(COALESCE((p->>'profit_factor')::NUMERIC, 0), 9999),
    NOW()
  )
  ON CONFLICT (user_id, plan_name) DO UPDATE SET
    email            = EXCLUDED.email,
    total_trades     = EXCLUDED.total_trades,
    win_trades       = EXCLUDED.win_trades,
    loss_trades      = EXCLUDED.loss_trades,
    win_rate_pct     = EXCLUDED.win_rate_pct,
    total_profit_usd = EXCLUDED.total_profit_usd,
    profit_factor    = EXCLUDED.profit_factor,
    updated_at       = EXCLUDED.updated_at;
END;
$$;

REVOKE ALL ON FUNCTION public.bot_upsert_telemetry(jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.bot_upsert_plan_stats(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.bot_upsert_telemetry(jsonb) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.bot_upsert_plan_stats(jsonb) TO anon, authenticated;

-- 3) ถอนสิทธิ์เขียน/อ่านตรงของ anon บน 2 ตารางนี้ (ใช้ผ่านฟังก์ชันด้านบนเท่านั้น)
DROP POLICY IF EXISTS "Bot insert bot_telemetry"         ON bot_telemetry;
DROP POLICY IF EXISTS "Bot update bot_telemetry"         ON bot_telemetry;
DROP POLICY IF EXISTS "Bot upsert check bot_telemetry"   ON bot_telemetry;
DROP POLICY IF EXISTS "Bot insert user_plan_stats"       ON user_plan_stats;
DROP POLICY IF EXISTS "Bot update user_plan_stats"       ON user_plan_stats;
DROP POLICY IF EXISTS "Bot upsert check user_plan_stats" ON user_plan_stats;
REVOKE ALL ON bot_telemetry   FROM anon, authenticated;
REVOKE ALL ON user_plan_stats FROM anon, authenticated;

-- ให้ PostgREST โหลดฟังก์ชันใหม่ทันที
NOTIFY pgrst, 'reload schema';
