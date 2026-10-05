-- ==============================================================================
-- GoldBot24 — Patch 06: เรียงเลขแผนเทรดใหม่ (รันซ้ำได้)
--   Plan 1 = MA-Cross-Trend (M15) · Plan 2 = MA-Cross-H1-Trend (H1)
--   Plan 3 = SMC-LiquidityHunt · Plan 4 = SR-SwingBounce · Plan 5 = BB-H1-Reversion
-- จับคู่จากชื่อแผน (ไม่ขึ้นกับเลขเดิม) และรวมยอดถ้าผู้ใช้คนเดียวมีหลายแถวของแผนเดียวกัน
-- ==============================================================================
BEGIN;

DELETE FROM user_plan_stats WHERE plan_name ILIKE '%Breakout%';

DO $$
DECLARE
  m TEXT[][] := ARRAY[
    ARRAY['%MA-Cross-Trend%',   'Plan 1: MA-Cross-Trend'],
    ARRAY['%Cross-H1-Trend%',   'Plan 2: MA-Cross-H1-Trend'],
    ARRAY['%SMC%',              'Plan 3: SMC-LiquidityHunt'],
    ARRAY['%SwingBounce%',      'Plan 4: SR-SwingBounce'],
    ARRAY['%BB-H1-Reversion%',  'Plan 5: BB-H1-Reversion']
  ];
  i INT;
BEGIN
  FOR i IN 1 .. array_length(m, 1) LOOP
    CREATE TEMP TABLE _agg ON COMMIT DROP AS
      SELECT user_id,
             MAX(email) AS email,
             SUM(total_trades) AS total_trades,
             SUM(win_trades) AS win_trades,
             SUM(loss_trades) AS loss_trades,
             SUM(total_profit_usd) AS total_profit_usd,
             SUM(gross_profit_usd) AS gross_profit_usd,
             SUM(gross_loss_usd) AS gross_loss_usd,
             MAX(last_trade_at) AS last_trade_at
      FROM user_plan_stats
      WHERE plan_name ILIKE m[i][1]
      GROUP BY user_id;

    DELETE FROM user_plan_stats WHERE plan_name ILIKE m[i][1];

    INSERT INTO user_plan_stats (user_id, email, plan_name, total_trades, win_trades, loss_trades, win_rate_pct,
                                 total_profit_usd, gross_profit_usd, gross_loss_usd, profit_factor, last_trade_at, updated_at)
    SELECT user_id, email, m[i][2], total_trades, win_trades, loss_trades,
           CASE WHEN total_trades > 0 THEN ROUND(win_trades::NUMERIC / total_trades * 100, 2) ELSE 0 END,
           total_profit_usd, gross_profit_usd, gross_loss_usd,
           CASE WHEN ABS(gross_loss_usd) > 0 THEN LEAST(ROUND(gross_profit_usd / ABS(gross_loss_usd), 2), 9999.99) ELSE 0 END,
           last_trade_at, NOW()
    FROM _agg;

    DROP TABLE _agg;
  END LOOP;
END $$;

COMMIT;

-- ตรวจผล: ควรเห็นเฉพาะ Plan 1–5 ชื่อใหม่
SELECT plan_name, COUNT(*) AS users, SUM(total_trades) AS trades
FROM user_plan_stats GROUP BY plan_name ORDER BY plan_name;
