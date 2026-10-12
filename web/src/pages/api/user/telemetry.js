import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireUser } from '../../../lib/server/auth';

// สถานะพอร์ต MT5 สด ของผู้ใช้คนนี้เท่านั้น (ประวัติการเทรดอยู่ที่ /api/user/trades)
// (Desktop App เขียน bot_telemetry โดยใช้ id = id บัญชี GoldBot24 ของผู้ใช้)
function shape(t) {
  return {
    status: t.status,
    balance: Number(t.balance) || 0,
    equity: Number(t.equity) || 0,
    floating_profit: Number(t.floating_profit) || 0,
    margin_free: Number(t.margin_free) || 0,
    open_positions: Array.isArray(t.open_positions) ? t.open_positions : [],
    radar_signals: Array.isArray(t.radar_signals) ? t.radar_signals : [],
    last_heartbeat: t.last_heartbeat,
  };
}

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  const supabase = getAdminClient();
  const { data: telemetry } = await supabase.from('bot_telemetry').select('*').eq('id', Number(auth.user.id)).maybeSingle();

  // แยกตามบัญชี MT5 (Patch 08) — ยังไม่ได้รัน Patch → error → ถือว่าไม่มี
  const { data: accRows, error: accErr } = await supabase
    .from('bot_telemetry_accounts')
    .select('*')
    .eq('user_id', Number(auth.user.id))
    .gte('last_heartbeat', new Date(Date.now() - 24 * 3600 * 1000).toISOString())
    .order('last_heartbeat', { ascending: false });
  const accounts = accErr ? [] : (accRows || []).map((a) => ({ login: Number(a.login), profile: a.profile || 'default', ...shape(a) }));

  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({
    success: true,
    telemetry: telemetry ? shape(telemetry) : null,
    accounts,
  });
}
