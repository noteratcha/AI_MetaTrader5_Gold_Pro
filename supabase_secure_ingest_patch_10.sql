-- GoldBot24 — Patch 10: โปรแกรมเขียนข้อมูลขึ้นคลาวด์ต้องยืนยันตัวตนด้วย Token (12 ต.ค. 2026) — รันซ้ำได้ · ผู้ใช้รันเองใน Supabase SQL Editor
-- ปัญหาเดิม: โปรแกรมใช้ anon key (สาธารณะ ฝังในโปรแกรม) เขียน Telemetry / สถิติรายแผน / trade_logs / signal_logs / risk_events
--            โดยระบุ user id เอง → ใครก็ปลอมพอร์ตสด/สถิติ/ประวัติของผู้ใช้คนอื่นได้ (และปั่นสถิติรวมหน้า "แผนเทรด")
-- ทางแก้: RPC bot_ingest(token, type, payload) ตรวจลายเซ็น Token (HMAC-SHA256 ชุดเดียวกับ /api/auth/*) ในฐานข้อมูลเอง
--         แล้วบังคับ user id / email จาก Token — ไม่เพิ่มโหลดให้ Vercel
-- ความลับ (AUTH_SECRET) ถูกเขียนลงตาราง bot_ingest_secret อัตโนมัติโดย Server (/api/auth/me, /api/auth/login) — ไม่ต้องคัดลอกเอง
-- หลังผู้ใช้ส่วนใหญ่อัปเดตโปรแกรมแล้ว ให้รัน Patch 11 (supabase_revoke_anon_write_patch_11.sql) เพื่อปิดทางเขียนแบบเดิม

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

CREATE TABLE IF NOT EXISTS bot_ingest_secret (
    id         INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    secret     TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE bot_ingest_secret ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON bot_ingest_secret FROM anon, authenticated;

CREATE OR REPLACE FUNCTION public.bot_verify_token(p_token TEXT)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_secret TEXT;
  v_body   TEXT;
  v_sig    TEXT;
  v_expect TEXT;
  v_b64    TEXT;
  v_claims jsonb;
BEGIN
  SELECT secret INTO v_secret FROM bot_ingest_secret WHERE id = 1;
  IF v_secret IS NULL OR p_token IS NULL OR position('.' IN p_token) = 0 THEN
    RETURN NULL;
  END IF;
  v_body := split_part(p_token, '.', 1);
  v_sig  := split_part(p_token, '.', 2);
  v_expect := translate(rtrim(encode(extensions.hmac(convert_to(v_body, 'UTF8'), convert_to(v_secret, 'UTF8'), 'sha256'), 'base64'), '='), '+/', '-_');
  IF v_sig IS DISTINCT FROM v_expect THEN
    RETURN NULL;
  END IF;
  v_b64 := translate(v_body, '-_', '+/');
  v_b64 := v_b64 || repeat('=', (4 - length(v_b64) % 4) % 4);
  v_claims := convert_from(decode(v_b64, 'base64'), 'UTF8')::jsonb;
  IF (v_claims->>'exp')::BIGINT < EXTRACT(EPOCH FROM NOW())::BIGINT THEN
    RETURN NULL;
  END IF;
  IF COALESCE(v_claims->>'sub', '') !~ '^[0-9]+$' OR (v_claims->>'sub')::BIGINT <= 1 THEN
    RETURN NULL;
  END IF;
  RETURN v_claims;
EXCEPTION WHEN OTHERS THEN
  RETURN NULL;
END;
$$;
REVOKE ALL ON FUNCTION public.bot_verify_token(TEXT) FROM PUBLIC, anon, authenticated;

CREATE OR REPLACE FUNCTION public.bot_ingest(p_token TEXT, p_type TEXT, p jsonb)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  c       jsonb := public.bot_verify_token(p_token);
  v_uid   TEXT;
  v_email TEXT;
  v_login BIGINT;
BEGIN
  IF c IS NULL THEN
    RAISE EXCEPTION 'unauthorized';
  END IF;
  IF pg_column_size(p) > 200000 THEN
    RAISE EXCEPTION 'payload too large';
  END IF;
  v_uid   := c->>'sub';
  v_email := LEFT(COALESCE(c->>'email', ''), 200);

  IF p_type = 'telemetry' THEN
    INSERT INTO bot_telemetry (id, status, balance, equity, floating_profit, margin_free, open_positions, radar_signals, last_heartbeat)
    VALUES (v_uid::INTEGER, LEFT(COALESCE(p->>'status', 'ONLINE'), 60),
            COALESCE((p->>'balance')::NUMERIC, 0), COALESCE((p->>'equity')::NUMERIC, 0),
            COALESCE((p->>'floating_profit')::NUMERIC, 0), COALESCE((p->>'margin_free')::NUMERIC, 0),
            COALESCE(p->'open_positions', '[]'::jsonb), COALESCE(p->'radar_signals', '[]'::jsonb), NOW())
    ON CONFLICT (id) DO UPDATE SET
      status = EXCLUDED.status, balance = EXCLUDED.balance, equity = EXCLUDED.equity,
      floating_profit = EXCLUDED.floating_profit, margin_free = EXCLUDED.margin_free,
      open_positions = EXCLUDED.open_positions, radar_signals = EXCLUDED.radar_signals, last_heartbeat = NOW();

    v_login := NULLIF(p->>'login', '')::BIGINT;
    IF v_login IS NOT NULL AND v_login > 0 AND to_regclass('public.bot_telemetry_accounts') IS NOT NULL THEN
      EXECUTE $q$
        INSERT INTO bot_telemetry_accounts (user_id, login, profile, status, balance, equity, floating_profit, margin_free, open_positions, radar_signals, last_heartbeat)
        VALUES ($1, $2, LEFT(COALESCE($3->>'profile', 'default'), 40), LEFT(COALESCE($3->>'status', 'ONLINE'), 60),
                COALESCE(($3->>'balance')::NUMERIC, 0), COALESCE(($3->>'equity')::NUMERIC, 0),
                COALESCE(($3->>'floating_profit')::NUMERIC, 0), COALESCE(($3->>'margin_free')::NUMERIC, 0),
                COALESCE($3->'open_positions', '[]'::jsonb), COALESCE($3->'radar_signals', '[]'::jsonb), NOW())
        ON CONFLICT (user_id, login) DO UPDATE SET
          profile = EXCLUDED.profile, status = EXCLUDED.status, balance = EXCLUDED.balance, equity = EXCLUDED.equity,
          floating_profit = EXCLUDED.floating_profit, margin_free = EXCLUDED.margin_free,
          open_positions = EXCLUDED.open_positions, radar_signals = EXCLUDED.radar_signals, last_heartbeat = NOW()
      $q$ USING v_uid::INTEGER, v_login, p;
    END IF;

  ELSIF p_type = 'plan_stats' THEN
    IF COALESCE(p->>'plan_name', '') = '' THEN
      RAISE EXCEPTION 'invalid plan_name';
    END IF;
    INSERT INTO user_plan_stats (user_id, email, plan_name, total_trades, win_trades, loss_trades,
                                 win_rate_pct, total_profit_usd, profit_factor, updated_at)
    VALUES (v_uid, v_email, LEFT(p->>'plan_name', 80),
            GREATEST(COALESCE((p->>'total_trades')::INTEGER, 0), 0), GREATEST(COALESCE((p->>'win_trades')::INTEGER, 0), 0),
            GREATEST(COALESCE((p->>'loss_trades')::INTEGER, 0), 0), LEAST(GREATEST(COALESCE((p->>'win_rate_pct')::NUMERIC, 0), 0), 100),
            COALESCE((p->>'total_profit_usd')::NUMERIC, 0), LEAST(GREATEST(COALESCE((p->>'profit_factor')::NUMERIC, 0), 0), 9999), NOW())
    ON CONFLICT (user_id, plan_name) DO UPDATE SET
      email = EXCLUDED.email, total_trades = EXCLUDED.total_trades, win_trades = EXCLUDED.win_trades,
      loss_trades = EXCLUDED.loss_trades, win_rate_pct = EXCLUDED.win_rate_pct,
      total_profit_usd = EXCLUDED.total_profit_usd, profit_factor = EXCLUDED.profit_factor, updated_at = NOW();

  ELSIF p_type = 'trade' THEN
    INSERT INTO trade_logs (ticket, time, symbol, action, plan, price, lot, sl, tp, profit, comment, user_id, email)
    VALUES (NULLIF(p->>'ticket', '')::BIGINT, COALESCE((p->>'time')::TIMESTAMPTZ, NOW()), LEFT(COALESCE(p->>'symbol', ''), 20),
            LEFT(COALESCE(p->>'action', ''), 20), LEFT(p->>'plan', 80), COALESCE((p->>'price')::NUMERIC, 0),
            COALESCE((p->>'lot')::NUMERIC, 0), COALESCE((p->>'sl')::NUMERIC, 0), COALESCE((p->>'tp')::NUMERIC, 0),
            COALESCE((p->>'profit')::NUMERIC, 0), LEFT(p->>'comment', 300), v_uid, v_email);

  ELSIF p_type = 'signal' THEN
    INSERT INTO signal_logs (time, symbol, signal_type, plan, direction, price, ai_up, ai_down, h4_trend, status, detail, user_id, email)
    VALUES (COALESCE((p->>'time')::TIMESTAMPTZ, NOW()), LEFT(COALESCE(p->>'symbol', ''), 20), LEFT(COALESCE(p->>'signal_type', ''), 40),
            LEFT(p->>'plan', 80), LEFT(p->>'direction', 10), COALESCE((p->>'price')::NUMERIC, 0),
            COALESCE((p->>'ai_up')::NUMERIC, 0), COALESCE((p->>'ai_down')::NUMERIC, 0), LEFT(p->>'h4_trend', 40),
            LEFT(p->>'status', 40), LEFT(p->>'detail', 500), v_uid, v_email);

  ELSIF p_type = 'risk' THEN
    INSERT INTO risk_events (time, symbol, event_type, direction, message, loss_amount, user_id, email)
    VALUES (COALESCE((p->>'time')::TIMESTAMPTZ, NOW()), LEFT(COALESCE(p->>'symbol', ''), 20), LEFT(COALESCE(p->>'event_type', ''), 40),
            LEFT(COALESCE(p->>'direction', 'N/A'), 10), LEFT(p->>'message', 500), COALESCE((p->>'loss_amount')::NUMERIC, 0), v_uid, v_email);
  ELSE
    RAISE EXCEPTION 'unknown type';
  END IF;
END;
$$;

REVOKE ALL ON FUNCTION public.bot_ingest(TEXT, TEXT, jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.bot_ingest(TEXT, TEXT, jsonb) TO anon, authenticated;
NOTIFY pgrst, 'reload schema';
