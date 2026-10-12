import { getAdminClient } from '../../lib/server/supabaseAdmin';
import { allowMethods } from '../../lib/server/auth';
import { planNumber } from '../../lib/plans';

// ผลเทรดจริงรายแผนของผู้ใช้ทุกคนรวมกัน (สาธารณะ · ไม่ระบุตัวตน) — จาก user_plan_stats ที่โปรแกรมซิงค์ขึ้นมา
// ส่งเฉพาะยอดรวมต่อแผน ห้ามส่งอีเมล/ID หรือข้อมูลรายคน · cache ที่ CDN 5 นาที
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;

  const { data: rows, error } = await getAdminClient()
    .from('user_plan_stats')
    .select('user_id, plan_name, total_trades, win_trades, loss_trades, total_profit_usd, gross_profit_usd, gross_loss_usd, last_trade_at');
  if (error) return res.status(500).json({ success: false, error: 'โหลดสถิติไม่สำเร็จ' });

  const plans = {};
  const allUsers = new Set();
  for (const r of rows || []) {
    const trades = Number(r.total_trades) || 0;
    if (!trades) continue;
    const n = planNumber(r.plan_name);
    const key = n || (/manual/i.test(r.plan_name || '') ? 'manual' : null);
    if (!key) continue;
    const p = (plans[key] ||= { key, users: new Set(), trades: 0, win: 0, loss: 0, net: 0, gp: 0, gl: 0, last: null });
    p.users.add(r.user_id);
    allUsers.add(r.user_id);
    p.trades += trades;
    p.win += Number(r.win_trades) || 0;
    p.loss += Number(r.loss_trades) || 0;
    p.net += Number(r.total_profit_usd) || 0;
    p.gp += Math.abs(Number(r.gross_profit_usd) || 0);
    p.gl += Math.abs(Number(r.gross_loss_usd) || 0);
    if (r.last_trade_at && (!p.last || r.last_trade_at > p.last)) p.last = r.last_trade_at;
  }

  const out = Object.values(plans).map((p) => {
    const decided = p.win + p.loss;
    return {
      key: p.key,
      users: p.users.size,
      trades: p.trades,
      win: p.win,
      loss: p.loss,
      winRate: decided ? Math.round((p.win / decided) * 1000) / 10 : null,
      net: Math.round(p.net * 100) / 100,
      avg: p.trades ? Math.round((p.net / p.trades) * 100) / 100 : 0,
      pf: p.gl > 0 ? Math.round((p.gp / p.gl) * 100) / 100 : null,
      lastTradeAt: p.last,
    };
  });
  out.sort((a, b) => (a.key === 'manual') - (b.key === 'manual') || a.key - b.key);

  const t = out.reduce((a, p) => ({ trades: a.trades + p.trades, win: a.win + p.win, loss: a.loss + p.loss, net: a.net + p.net }), { trades: 0, win: 0, loss: 0, net: 0 });
  const gp = Object.values(plans).reduce((a, p) => a + p.gp, 0);
  const gl = Object.values(plans).reduce((a, p) => a + p.gl, 0);

  res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
  return res.status(200).json({
    success: true,
    users: allUsers.size,
    total: {
      ...t,
      net: Math.round(t.net * 100) / 100,
      winRate: t.win + t.loss ? Math.round((t.win / (t.win + t.loss)) * 1000) / 10 : null,
      pf: gl > 0 ? Math.round((gp / gl) * 100) / 100 : null,
    },
    plans: out,
    generatedAt: new Date().toISOString(),
  });
}
