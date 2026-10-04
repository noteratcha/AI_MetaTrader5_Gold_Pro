import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireAdmin } from '../../../lib/server/auth';

// ภาพรวมระบบสำหรับแอดมิน: ผู้ใช้, บอทออนไลน์, รายได้, คีย์, การเทรดรวม, กิจกรรมล่าสุด
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  const supabase = getAdminClient();
  const head = { count: 'exact', head: true };
  const onlineSince = new Date(Date.now() - 120000).toISOString();

  const [users, disabled, lowHours, online, paidOrders, pendingOrders, unusedKeys, unusedPromo, summary, activity, hoursRows] = await Promise.all([
    supabase.from('bot_config').select('id', head).gt('id', 1),
    supabase.from('bot_config').select('id', head).gt('id', 1).contains('symbols_trading', ['status:disabled']),
    supabase.from('bot_config').select('id', head).gt('id', 1).lte('lot_size', 5),
    supabase.from('bot_telemetry').select('id', head).gt('id', 1).gte('last_heartbeat', onlineSince),
    supabase.from('orders').select('amount_thb, hours_to_add').eq('status', 'PAID').limit(20000),
    supabase.from('orders').select('order_id', head).in('status', ['PENDING', 'PROCESSING']),
    supabase.from('product_keys').select('key_code', head).eq('is_used', false),
    supabase.from('promo_keys').select('key_code', head).eq('used', false),
    supabase.from('admin_user_trade_summary').select('*').limit(20000),
    supabase.from('user_activity').select('id, email, event, detail, actor, created_at').order('created_at', { ascending: false }).limit(12),
    supabase.from('bot_config').select('lot_size').gt('id', 1).limit(20000),
  ]);

  const paid = paidOrders.data || [];
  const s = summary.data || [];
  const sum = (k) => s.reduce((t, r) => t + (Number(r[k]) || 0), 0);
  const tp = sum('tp_hits');
  const sl = sum('sl_hits');

  return res.status(200).json({
    success: true,
    metrics: {
      totalUsers: users.count || 0,
      disabledUsers: disabled.count || 0,
      lowHoursUsers: lowHours.count || 0,
      onlineBots: online.count || 0,
      revenueThb: paid.reduce((t, o) => t + (Number(o.amount_thb) || 0), 0),
      paidOrders: paid.length,
      pendingOrders: pendingOrders.count || 0,
      unusedKeys: (unusedKeys.count || 0) + (unusedPromo.count || 0),
      hoursOutstanding: (hoursRows.data || []).reduce((t, r) => t + (Number(r.lot_size) || 0), 0),
      trades: {
        opens: sum('opens'),
        tp,
        sl,
        botClose: sum('bot_closes'),
        manualClose: sum('manual_closes'),
        netProfit: sum('net_profit'),
        tpRate: tp + sl ? (tp / (tp + sl)) * 100 : 0,
      },
    },
    recentActivity: activity.data || [],
    setupRequired: Boolean(summary.error || activity.error),
  });
}
