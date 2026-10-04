import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireUser } from '../../../lib/server/auth';

// สถานะพอร์ต MT5 สด + ประวัติการเทรดล่าสุด ของผู้ใช้คนนี้เท่านั้น
// (Desktop App เขียน bot_telemetry โดยใช้ id = id บัญชี GoldBot24 ของผู้ใช้)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  const supabase = getAdminClient();
  const [{ data: telemetry }, { data: logs }] = await Promise.all([
    supabase.from('bot_telemetry').select('*').eq('id', Number(auth.user.id)).maybeSingle(),
    supabase
      .from('trade_logs')
      .select('id, ticket, time, symbol, action, plan, price, lot, sl, tp, profit, comment')
      .eq('email', auth.user.email)
      .order('time', { ascending: false })
      .limit(30),
  ]);

  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({
    success: true,
    telemetry: telemetry
      ? {
          status: telemetry.status,
          balance: Number(telemetry.balance) || 0,
          equity: Number(telemetry.equity) || 0,
          floating_profit: Number(telemetry.floating_profit) || 0,
          margin_free: Number(telemetry.margin_free) || 0,
          open_positions: Array.isArray(telemetry.open_positions) ? telemetry.open_positions : [],
          radar_signals: Array.isArray(telemetry.radar_signals) ? telemetry.radar_signals : [],
          last_heartbeat: telemetry.last_heartbeat,
        }
      : null,
    trade_logs: logs || [],
  });
}
