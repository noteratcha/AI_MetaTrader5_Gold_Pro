-- GoldBot24 — Patch 08: พอร์ตสดแยกตามบัญชี MT5 (Multi-Profile) — รันซ้ำได้ · ผู้ใช้รันเองใน Supabase SQL Editor
-- 1 แถวต่อ (บัญชีผู้ใช้ GoldBot24, เลขบัญชี MT5) · โปรแกรมเขียนผ่าน RPC (SECURITY DEFINER, เขียนอย่างเดียว) · เว็บอ่านผ่าน /api/user/telemetry (Service Role)

CREATE TABLE IF NOT EXISTS bot_telemetry_accounts (
    user_id         INTEGER NOT NULL,
    login           BIGINT  NOT NULL,
    profile         TEXT,
    status          TEXT,
    balance         NUMERIC DEFAULT 0,
    equity          NUMERIC DEFAULT 0,
    floating_profit NUMERIC DEFAULT 0,
    margin_free     NUMERIC DEFAULT 0,
    open_positions  JSONB DEFAULT '[]'::jsonb,
    radar_signals   JSONB DEFAULT '[]'::jsonb,
    last_heartbeat  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, login)
);
CREATE INDEX IF NOT EXISTS idx_bta_user ON bot_telemetry_accounts (user_id, last_heartbeat DESC);
ALTER TABLE bot_telemetry_accounts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON bot_telemetry_accounts FROM anon, authenticated;

CREATE OR REPLACE FUNCTION public.bot_upsert_telemetry_account(p jsonb)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_id    INTEGER := NULLIF(p->>'id', '')::INTEGER;
  v_login BIGINT  := NULLIF(p->>'login', '')::BIGINT;
BEGIN
  IF v_id IS NULL OR v_id <= 1 OR v_login IS NULL OR v_login <= 0 THEN
    RAISE EXCEPTION 'invalid telemetry id/login';
  END IF;
  IF pg_column_size(p) > 200000 THEN
    RAISE EXCEPTION 'telemetry payload too large';
  END IF;

  INSERT INTO bot_telemetry_accounts (user_id, login, profile, status, balance, equity, floating_profit, margin_free, open_positions, radar_signals, last_heartbeat)
  VALUES (
    v_id, v_login,
    LEFT(COALESCE(p->>'profile', 'default'), 40),
    LEFT(COALESCE(p->>'status', 'ONLINE'), 60),
    COALESCE((p->>'balance')::NUMERIC, 0),
    COALESCE((p->>'equity')::NUMERIC, 0),
    COALESCE((p->>'floating_profit')::NUMERIC, 0),
    COALESCE((p->>'margin_free')::NUMERIC, 0),
    COALESCE(p->'open_positions', '[]'::jsonb),
    COALESCE(p->'radar_signals', '[]'::jsonb),
    NOW()
  )
  ON CONFLICT (user_id, login) DO UPDATE SET
    profile         = EXCLUDED.profile,
    status          = EXCLUDED.status,
    balance         = EXCLUDED.balance,
    equity          = EXCLUDED.equity,
    floating_profit = EXCLUDED.floating_profit,
    margin_free     = EXCLUDED.margin_free,
    open_positions  = EXCLUDED.open_positions,
    radar_signals   = EXCLUDED.radar_signals,
    last_heartbeat  = NOW();

  -- เก็บกวาดบัญชีที่เงียบเกิน 30 วัน
  DELETE FROM bot_telemetry_accounts WHERE user_id = v_id AND last_heartbeat < NOW() - INTERVAL '30 days';
END;
$$;

REVOKE ALL ON FUNCTION public.bot_upsert_telemetry_account(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.bot_upsert_telemetry_account(jsonb) TO anon, authenticated;
NOTIFY pgrst, 'reload schema';
