import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireUser } from '../../../lib/server/auth';

const PLAN_ORDER = [
  'Plan 1: MA-Cross-Trend',
  'Plan 2: MA-Cross-H1-Trend',
  'Plan 3: SMC-LiquidityHunt',
  'Plan 4: SR-SwingBounce',
  'Plan 5: BB-H1-Reversion',
];

// สถิติการเทรดรายแผนของผู้ใช้ (ซิงค์จาก Desktop App → user_plan_stats)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  const { data: rows } = await getAdminClient()
    .from('user_plan_stats')
    .select('plan_name, total_trades, win_trades, loss_trades, win_rate_pct, total_profit_usd, profit_factor, updated_at')
    .eq('user_id', auth.user.id);

  const byPlan = Object.fromEntries((rows || []).map((r) => [r.plan_name, r]));
  const plans = PLAN_ORDER.map((name) => {
    const r = byPlan[name] || {};
    return {
      name,
      trades: Number(r.total_trades) || 0,
      win: Number(r.win_trades) || 0,
      loss: Number(r.loss_trades) || 0,
      winRate: Number(r.win_rate_pct) || 0,
      profit: Number(r.total_profit_usd) || 0,
      pf: Number(r.profit_factor) || 0,
      updatedAt: r.updated_at || null,
    };
  });

  const total = plans.reduce(
    (acc, p) => ({ trades: acc.trades + p.trades, win: acc.win + p.win, loss: acc.loss + p.loss, profit: acc.profit + p.profit }),
    { trades: 0, win: 0, loss: 0, profit: 0 }
  );
  const decided = total.win + total.loss;

  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({
    success: true,
    overall: { ...total, winRate: decided ? (total.win / decided) * 100 : 0 },
    plans,
  });
}
