-- ==============================================================================
-- GoldBot24 — Patch 05: จัดเลขแผนเทรดใหม่ + นำ Plan 2 (Trend-Breakout) ออก (รันซ้ำได้)
--   Plan 0: SMC-LiquidityHunt → Plan 1: SMC-LiquidityHunt
--   Plan 1: SR-SwingBounce    → Plan 2: SR-SwingBounce
--   Plan 2: Trend-Breakout    → ลบออก
--   Plan 3 / 4 / 5            → เหมือนเดิม
-- ถ้าโปรแกรมเวอร์ชันใหม่เขียนสถิติชื่อใหม่ไว้ก่อนแล้ว จะรวมยอดเข้าแถวเดียวกัน
-- ==============================================================================
BEGIN;

DELETE FROM user_plan_stats WHERE plan_name ILIKE '%Breakout%';

-- ต้องย้าย Bounce (1 → 2) ก่อน SMC (0 → 1) เพื่อไม่ให้ชื่อชนกัน
DO $$
DECLARE
  pairs TEXT[][] := ARRAY[
    ARRAY['Plan 1: SR-SwingBounce', 'Plan 2: SR-SwingBounce'],
    ARRAY['Plan 0: SMC-LiquidityHunt', 'Plan 1: SMC-LiquidityHunt']
  ];
  i INT;
  old_name TEXT;
  new_name TEXT;
BEGIN
  FOR i IN 1 .. array_length(pairs, 1) LOOP
    old_name := pairs[i][1];
    new_name := pairs[i][2];

    -- มีทั้งชื่อเก่าและชื่อใหม่ของผู้ใช้เดียวกัน → รวมยอดเข้าแถวชื่อใหม่
    UPDATE user_plan_stats n
    SET total_trades     = n.total_trades + o.total_trades,
        win_trades       = n.win_trades + o.win_trades,
        loss_trades      = n.loss_trades + o.loss_trades,
        total_profit_usd = n.total_profit_usd + o.total_profit_usd,
        gross_profit_usd = n.gross_profit_usd + o.gross_profit_usd,
        gross_loss_usd   = n.gross_loss_usd + o.gross_loss_usd,
        last_trade_at    = GREATEST(n.last_trade_at, o.last_trade_at),
        updated_at       = NOW()
    FROM user_plan_stats o
    WHERE o.plan_name = old_name AND n.plan_name = new_name AND n.user_id = o.user_id;

    DELETE FROM user_plan_stats o
    WHERE o.plan_name = old_name
      AND EXISTS (SELECT 1 FROM user_plan_stats n WHERE n.plan_name = new_name AND n.user_id = o.user_id);

    -- ที่เหลือ (มีแต่ชื่อเก่า) → เปลี่ยนชื่อ
    UPDATE user_plan_stats SET plan_name = new_name, updated_at = NOW() WHERE plan_name = old_name;
  END LOOP;
END $$;

-- คำนวณ Win Rate / Profit Factor ใหม่ของแถวที่ถูกรวมยอด
UPDATE user_plan_stats
SET win_rate_pct  = CASE WHEN total_trades > 0 THEN ROUND(win_trades::NUMERIC / total_trades * 100, 2) ELSE 0 END,
    profit_factor = CASE WHEN ABS(gross_loss_usd) > 0 THEN LEAST(ROUND(gross_profit_usd / ABS(gross_loss_usd), 2), 9999.99) ELSE 0 END
WHERE plan_name IN ('Plan 1: SMC-LiquidityHunt', 'Plan 2: SR-SwingBounce');

COMMIT;

-- ตรวจผล: ไม่ควรเหลือ Plan 0 / Breakout
SELECT plan_name, COUNT(*) AS users, SUM(total_trades) AS trades
FROM user_plan_stats GROUP BY plan_name ORDER BY plan_name;
