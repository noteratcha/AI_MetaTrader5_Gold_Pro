import { getAdminClient } from './supabaseAdmin';
import { notifyAdmins } from './lineNotify';

const DAY_MS = 24 * 60 * 60 * 1000;
const BKK_OFFSET_MS = 7 * 60 * 60 * 1000;

/** เวลาเริ่มต้นของ "วันนี้" ตามเวลาไทย (00:00 Asia/Bangkok) เป็น Date UTC */
export function bangkokDayStart(now = Date.now()) {
  return new Date(Math.floor((now + BKK_OFFSET_MS) / DAY_MS) * DAY_MS - BKK_OFFSET_MS);
}

const n = (v) => Number(v || 0).toLocaleString('th-TH');
const thb = (v) => `฿${Number(v || 0).toLocaleString('th-TH', { maximumFractionDigits: 2 })}`;
const usd = (v) => `${v >= 0 ? '+' : '-'}$${Math.abs(Number(v || 0)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** รวบรวมตัวเลขของวันนี้ (เวลาไทย) */
export async function collectDailySummary(now = Date.now()) {
  const supabase = getAdminClient();
  const since = bangkokDayStart(now).toISOString();
  const online = new Date(now - 120000).toISOString();
  const head = { count: 'exact', head: true };
  const activityCount = (event) => supabase.from('user_activity').select('id', head).eq('event', event).gte('created_at', since);

  const [users, registers, paid, pending, onlineNow, activeToday, logins, failed, locked, redeems, trades] = await Promise.all([
    supabase.from('bot_config').select('id', head).gt('id', 1),
    activityCount('register'),
    supabase.from('orders').select('amount_thb, hours_to_add').eq('status', 'PAID').gte('paid_at', since).limit(5000),
    supabase.from('orders').select('order_id', head).in('status', ['PENDING', 'PROCESSING']).gte('created_at', since),
    supabase.from('bot_telemetry').select('id', head).gt('id', 1).gte('last_heartbeat', online),
    supabase.from('bot_telemetry').select('id', head).gt('id', 1).gte('last_heartbeat', since),
    supabase.from('user_activity').select('email').eq('event', 'login').gte('created_at', since).limit(5000),
    activityCount('login_failed'),
    activityCount('account_locked'),
    activityCount('redeem'),
    supabase.from('trade_logs').select('action, profit').gte('time', since).limit(20000),
  ]);

  const paidRows = paid.data || [];
  const tradeRows = trades.data || [];
  const closes = tradeRows.filter((t) => !String(t.action || '').startsWith('OPEN'));
  return {
    date: new Date(now).toLocaleDateString('th-TH', { timeZone: 'Asia/Bangkok', dateStyle: 'long' }),
    totalUsers: users.count || 0,
    newMembers: registers.count || 0,
    salesCount: paidRows.length,
    salesThb: paidRows.reduce((t, o) => t + (Number(o.amount_thb) || 0), 0),
    hoursSold: paidRows.reduce((t, o) => t + (Number(o.hours_to_add) || 0), 0),
    pendingOrders: pending.count || 0,
    redeems: redeems.count || 0,
    onlineBots: onlineNow.count || 0,
    activeBotsToday: activeToday.count || 0,
    uniqueLogins: new Set((logins.data || []).map((r) => r.email)).size,
    failedLogins: failed.count || 0,
    lockedAccounts: locked.count || 0,
    tradesOpened: tradeRows.filter((t) => String(t.action || '').startsWith('OPEN')).length,
    tp: closes.filter((t) => t.action === 'TP_HIT').length,
    sl: closes.filter((t) => t.action === 'SL_HIT').length,
    netProfit: closes.reduce((t, r) => t + (Number(r.profit) || 0), 0),
  };
}

export function formatDailySummary(m) {
  return [
    `📊 สรุปประจำวัน GoldBot24`,
    `${m.date}`,
    ``,
    `👥 สมาชิก`,
    `• สมัครใหม่: ${n(m.newMembers)} คน (รวม ${n(m.totalUsers)})`,
    `• เข้าสู่ระบบ: ${n(m.uniqueLogins)} คน`,
    ``,
    `💰 ยอดขาย`,
    `• ชำระสำเร็จ: ${n(m.salesCount)} รายการ · ${thb(m.salesThb)}`,
    `• ชั่วโมงที่ขาย: ${n(m.hoursSold)} ชม. · เติมคีย์ ${n(m.redeems)} ครั้ง`,
    m.pendingOrders ? `• ค้างชำระวันนี้: ${n(m.pendingOrders)} รายการ` : null,
    ``,
    `🤖 บอท`,
    `• ออนไลน์ตอนนี้: ${n(m.onlineBots)} เครื่อง · ทำงานวันนี้ ${n(m.activeBotsToday)} เครื่อง`,
    `• เปิดไม้: ${n(m.tradesOpened)} · TP ${n(m.tp)} · SL ${n(m.sl)}`,
    `• กำไรสุทธิรวม: ${usd(m.netProfit)}`,
    ``,
    `🔐 ความปลอดภัย`,
    `• รหัสผิด: ${n(m.failedLogins)} ครั้ง · บัญชีถูกล็อก ${n(m.lockedAccounts)} ครั้ง`,
  ]
    .filter((line) => line !== null)
    .join('\n');
}

export async function sendDailySummary() {
  const metrics = await collectDailySummary();
  const result = await notifyAdmins(formatDailySummary(metrics));
  return { metrics, ...result };
}
