import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireAdmin, toUserPayload } from '../../../lib/server/auth';

const PLAN_ORDER = [
  'Plan 0: SMC-LiquidityHunt',
  'Plan 1: SR-SwingBounce',
  'Plan 3: BB-H1-Reversion',
  'Plan 4: MA-Cross-Trend',
  'Plan 5: MA-Cross-H1-Trend',
];

// ภาพรวมระบบสำหรับ Admin: ลูกค้า, รายได้, คีย์, สถิติรวมรายแผน (ข้อมูลจริงจากฐานข้อมูล)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  const supabase = getAdminClient();
  const [usersRes, ordersRes, keysRes, promoRes, statsRes] = await Promise.all([
    supabase
      .from('bot_config')
      .select('id, mt5_server, mt5_login, lot_size, symbols_trading, updated_at', { count: 'exact' })
      .gt('id', 1)
      .order('updated_at', { ascending: false })
      .limit(25),
    supabase.from('orders').select('amount_thb, hours_to_add, status, paid_at').eq('status', 'PAID').limit(10000),
    supabase.from('product_keys').select('is_used', { count: 'exact' }).limit(10000),
    supabase.from('promo_keys').select('key_code, hours, used, used_by, used_at, expires_at').order('used_at', { ascending: false, nullsFirst: true }).limit(15),
    supabase.from('user_plan_stats').select('plan_name, total_trades, win_trades, loss_trades, total_profit_usd').limit(10000),
  ]);

  const paidOrders = ordersRes.data || [];
  const revenue = paidOrders.reduce((s, o) => s + (Number(o.amount_thb) || 0), 0);
  const hoursSold = paidOrders.reduce((s, o) => s + (Number(o.hours_to_add) || 0), 0);
  const productKeys = keysRes.data || [];

  const planAgg = Object.fromEntries(PLAN_ORDER.map((p) => [p, { trades: 0, win: 0, loss: 0, profit: 0 }]));
  for (const r of statsRes.data || []) {
    const agg = planAgg[r.plan_name];
    if (!agg) continue;
    agg.trades += Number(r.total_trades) || 0;
    agg.win += Number(r.win_trades) || 0;
    agg.loss += Number(r.loss_trades) || 0;
    agg.profit += Number(r.total_profit_usd) || 0;
  }
  const plans = PLAN_ORDER.map((name) => {
    const a = planAgg[name];
    const decided = a.win + a.loss;
    return { name, ...a, winRate: decided ? (a.win / decided) * 100 : 0 };
  });
  const totals = plans.reduce((t, p) => ({ trades: t.trades + p.trades, win: t.win + p.win, loss: t.loss + p.loss, profit: t.profit + p.profit }), {
    trades: 0,
    win: 0,
    loss: 0,
    profit: 0,
  });

  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({
    success: true,
    metrics: {
      totalUsers: usersRes.count ?? (usersRes.data || []).length,
      paidOrders: paidOrders.length,
      revenueThb: revenue,
      hoursSold,
      productKeysIssued: keysRes.count ?? productKeys.length,
      productKeysRedeemed: productKeys.filter((k) => k.is_used).length,
      systemTrades: totals.trades,
      systemWinRate: totals.win + totals.loss ? (totals.win / (totals.win + totals.loss)) * 100 : 0,
      systemProfitUsd: totals.profit,
    },
    plans,
    recentUsers: (usersRes.data || []).map((row) => {
      const u = toUserPayload(row);
      return { id: u.id, email: u.email, displayName: u.displayName, hoursRemaining: u.hoursRemaining, role: u.role, updatedAt: row.updated_at };
    }),
    promoKeys: promoRes.data || [],
  });
}
