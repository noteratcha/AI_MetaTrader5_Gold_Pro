import { getAdminClient } from './supabaseAdmin';
import { isAdminRow, rowTags, toUserPayload } from './auth';

// =============================================================================
// รวมข้อมูลสรุปรายผู้ใช้สำหรับหน้าแอดมิน (ชั่วโมง, การเทรด, แผนที่ใช้, สถานะออนไลน์)
// =============================================================================

const ONLINE_SECONDS = 120;

export function setTag(tags, prefix, value) {
  const rest = tags.filter((t) => !t.startsWith(prefix));
  return value === null || value === undefined ? rest : [...rest, `${prefix}${value}`];
}

export function toggleTag(tags, tag, on) {
  const rest = tags.filter((t) => t !== tag);
  return on ? [...rest, tag] : rest;
}

/** เติมสรุปการเทรด/แผน/ออนไลน์ ให้รายการแถว bot_config */
export async function enrichUsers(rows) {
  const supabase = getAdminClient();
  const users = rows.map((row) => ({ ...toUserPayload(row), updatedAt: row.updated_at }));
  if (!users.length) return users;

  const emails = users.map((u) => u.email);
  const ids = users.map((u) => u.id);

  const [summaryRes, statsRes, teleRes] = await Promise.all([
    supabase.from('admin_user_trade_summary').select('*').in('email', emails),
    supabase.from('user_plan_stats').select('user_id, plan_name, total_trades, win_trades, loss_trades, total_profit_usd').in('user_id', ids),
    supabase.from('bot_telemetry').select('id, status, last_heartbeat, balance, equity, open_positions').in('id', ids.map(Number)),
  ]);

  const summaryBy = Object.fromEntries((summaryRes.data || []).map((s) => [s.email, s]));
  const statsBy = {};
  for (const s of statsRes.data || []) (statsBy[s.user_id] ||= []).push(s);
  const teleBy = Object.fromEntries((teleRes.data || []).map((t) => [String(t.id), t]));

  return users.map((u) => {
    const s = summaryBy[u.email] || {};
    const plans = (statsBy[u.id] || [])
      .map((p) => ({
        name: p.plan_name,
        trades: Number(p.total_trades) || 0,
        win: Number(p.win_trades) || 0,
        loss: Number(p.loss_trades) || 0,
        profit: Number(p.total_profit_usd) || 0,
      }))
      .filter((p) => p.trades > 0)
      .sort((a, b) => b.trades - a.trades);
    const t = teleBy[u.id];
    const lastBeat = t?.last_heartbeat ? new Date(t.last_heartbeat).getTime() : 0;
    return {
      ...u,
      trades: {
        opens: Number(s.opens) || 0,
        tp: Number(s.tp_hits) || 0,
        sl: Number(s.sl_hits) || 0,
        botClose: Number(s.bot_closes) || 0,
        manualClose: Number(s.manual_closes) || 0,
        netProfit: Number(s.net_profit) || 0,
        lastTradeAt: s.last_trade_at || null,
      },
      plans,
      bot: t
        ? {
            online: Date.now() - lastBeat < ONLINE_SECONDS * 1000,
            paused: String(t.status || '').startsWith('PAUSED'),
            lastHeartbeat: t.last_heartbeat,
            balance: Number(t.balance) || 0,
            equity: Number(t.equity) || 0,
            openPositions: Array.isArray(t.open_positions) ? t.open_positions.length : 0,
          }
        : null,
    };
  });
}

export async function loadUserRow(id) {
  const numericId = Number(id);
  if (!Number.isInteger(numericId) || numericId <= 1) return null;
  const { data } = await getAdminClient().from('bot_config').select('*').eq('id', numericId).maybeSingle();
  return data || null;
}

export { isAdminRow, rowTags };
