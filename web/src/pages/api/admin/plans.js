import { allowMethods, requireAdmin } from '../../../lib/server/auth';
import { getEnabledPlans, PLAN_KEYS, setEnabledPlans } from '../../../lib/server/catalog';
import { logActivity } from '../../../lib/server/activity';
import { getAdminClient } from '../../../lib/server/supabaseAdmin';

const PLAN_STAT_NAMES = {
  'MA-Cross-Trend': 'Plan 1: MA-Cross-Trend',
  'MA-Cross-H1-Trend': 'Plan 2: MA-Cross-H1-Trend',
  'SMC-LiquidityHunt': 'Plan 3: SMC-LiquidityHunt',
  'SR-SwingBounce': 'Plan 4: SR-SwingBounce',
  'BB-H1-Reversion': 'Plan 5: BB-H1-Reversion',
  'PSAR-H1-Trend': 'Plan 6: PSAR-H1-Trend',
};

// GET สถานะเปิด/ปิดแผนเทรด + ผลงานรวมรายแผน · PUT บันทึกการเปิด/ปิด (บอททุกเครื่องอ่านภายใน ~5 นาที)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET', 'PUT'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  if (req.method === 'PUT') {
    const input = req.body?.plans || {};
    const before = (await getEnabledPlans()).plans;
    try {
      const saved = await setEnabledPlans(input, auth.user.email);
      const changed = PLAN_KEYS.filter((k) => before[k] !== saved[k]).map((k) => `${k} ${saved[k] ? 'เปิด' : 'ปิด'}`);
      if (changed.length) await logActivity({ event: 'admin_plans', detail: changed.join(' · '), actor: auth.user.email });
    } catch (err) {
      return res.status(500).json({ success: false, error: 'บันทึกไม่สำเร็จ (รัน supabase_admin_patch_02.sql แล้วหรือยัง?)' });
    }
  }

  const { plans, updatedAt, updatedBy } = await getEnabledPlans();
  const { data: stats } = await getAdminClient().from('user_plan_stats').select('user_id, plan_name, total_trades, win_trades, loss_trades, total_profit_usd').limit(20000);
  const perf = {};
  for (const key of PLAN_KEYS) {
    const rows = (stats || []).filter((r) => r.plan_name === PLAN_STAT_NAMES[key]);
    const win = rows.reduce((s, r) => s + (Number(r.win_trades) || 0), 0);
    const loss = rows.reduce((s, r) => s + (Number(r.loss_trades) || 0), 0);
    perf[key] = {
      users: rows.filter((r) => Number(r.total_trades) > 0).length,
      trades: rows.reduce((s, r) => s + (Number(r.total_trades) || 0), 0),
      winRate: win + loss ? (win / (win + loss)) * 100 : 0,
      profit: rows.reduce((s, r) => s + (Number(r.total_profit_usd) || 0), 0),
    };
  }
  return res.status(200).json({ success: true, plans, perf, updatedAt, updatedBy });
}
