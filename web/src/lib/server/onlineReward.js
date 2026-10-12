import { getAdminClient } from './supabaseAdmin';
import { ONLINE_GOAL_HOURS, ONLINE_DISCOUNT_PCT, ONLINE_DISCOUNT_DAYS, levelInfo } from '../onlineReward';

// รางวัลออนไลน์: นาทีที่หักจริงจาก /api/auth/meter สะสมเป็นรอบ (supabase_online_reward_patch_07.sql)
// ครบ 100 ชม. → ส่วนลด 5% ซื้อชั่วโมงครั้งถัดไป 1 รายการ ใช้ได้ภายใน 3 วัน (เมื่อได้รับแล้วเริ่มนับชั่วโมงใหม่ทันที)
const GOAL_MIN = ONLINE_GOAL_HOURS * 60;
const DAY_MS = 24 * 60 * 60 * 1000;
/** บวกนาทีออนไลน์ (atomic ใน Postgres) · ครบ 100 ชม. → ออกส่วนลด (อายุ 3 วัน) และเริ่มนับรอบใหม่ทันที (เศษยกไป) */
export async function addOnlineMinutes(user, minutes, login = 0) {
  try {
    const { data, error } = await getAdminClient().rpc('add_online_minutes', {
      p_user: String(user.id), p_email: user.email, p_minutes: Math.floor(minutes), p_goal: GOAL_MIN,
    });
    if (error) throw error;
    // ประวัติรายวัน (เวลาไทย) สำหรับหน้าประวัติการสะสมชั่วโมง — Patch 09 · ยังไม่ได้รัน = ข้าม
    const day = new Date(Date.now() + 7 * 3600000).toISOString().slice(0, 10);
    await getAdminClient().rpc('add_online_daily', { p_user: String(user.id), p_day: day, p_minutes: Math.floor(minutes) }).then(() => {}, () => {});
    // แยกตามบัญชี MT5 (Patch 12) — โปรแกรมรุ่นเก่าไม่ส่งเลขบัญชี = ข้าม
    if (login > 0) {
      await getAdminClient()
        .rpc('add_online_daily_account', { p_user: String(user.id), p_day: day, p_login: login, p_minutes: Math.floor(minutes) })
        .then(() => {}, () => {});
    }
    const r = Array.isArray(data) ? data[0] : data;
    const earned = Number(r?.earned) || 0;
    const cycles = Number(r?.cycles) || 0;
    for (let i = 0; i < earned; i++) {
      const at = new Date();
      // cycle_no ไม่ซ้ำต่อผู้ใช้ (unique index) — กันออกส่วนลดซ้ำรอบเดียวกัน
      await getAdminClient().from('online_discounts').upsert(
        {
          user_id: String(user.id), email: user.email, cycle_no: cycles - i, percent: ONLINE_DISCOUNT_PCT,
          earned_at: at.toISOString(), expires_at: new Date(at.getTime() + ONLINE_DISCOUNT_DAYS * DAY_MS).toISOString(),
          status: 'ACTIVE',
        },
        { onConflict: 'user_id,cycle_no', ignoreDuplicates: true }
      );
    }
  } catch (err) {
    console.error('[onlineReward] add minutes failed:', err?.message || err);
  }
}

/** ส่วนลดที่ยังใช้ได้ (ยังไม่หมดอายุ · ยังไม่ใช้) → แถว หรือ null */
async function usableDiscount(userId) {
  const { data } = await getAdminClient()
    .from('online_discounts')
    .select('*')
    .eq('user_id', String(userId))
    .in('status', ['ACTIVE', 'RESERVED'])
    .gt('expires_at', new Date().toISOString())
    .order('expires_at', { ascending: true })
    .limit(1);
  return data?.[0] || null;
}

/** สถานะสำหรับแสดงผล (เว็บ/โปรแกรม) */
export async function getRewardStatus(userId) {
  try {
    const { data: row, error } = await getAdminClient()
      .from('online_progress').select('minutes, cycles').eq('user_id', String(userId)).maybeSingle();
    if (error) return null;   // ยังไม่ได้รัน supabase_online_reward_patch_07.sql — ซ่อนส่วนนี้
    const d = await usableDiscount(userId);
    return {
      minutes: Number(row?.minutes) || 0,
      goalMinutes: GOAL_MIN,
      cycles: Number(row?.cycles) || 0,
      discount: d ? { percent: Number(d.percent), expiresAt: d.expires_at, earnedAt: d.earned_at } : null,
      level: levelInfo((Number(row?.cycles) || 0) * GOAL_MIN + (Number(row?.minutes) || 0)),
    };
  } catch {
    return null;
  }
}

/** ผูกส่วนลดกับคำสั่งซื้อใหม่ (ย้ายจากคำสั่งซื้อเดิมที่ยังไม่ชำระได้) → { id, percent } หรือ null */
export async function reserveDiscount(userId, orderId) {
  try {
    const d = await usableDiscount(userId);
    if (!d) return null;
    if (d.status === 'RESERVED' && d.order_id) {
      const { data: prev } = await getAdminClient().from('orders').select('status').eq('order_id', d.order_id).maybeSingle();
      if (prev && ['PAID', 'PROCESSING'].includes(prev.status)) return null;   // กำลังใช้กับคำสั่งซื้อที่ชำระแล้ว
    }
    let q = getAdminClient().from('online_discounts').update({ status: 'RESERVED', order_id: orderId }).eq('id', d.id).eq('status', d.status);
    q = d.order_id ? q.eq('order_id', d.order_id) : q.is('order_id', null);
    const { data: locked } = await q.select('id');
    if (!locked || locked.length !== 1) return null;
    return { id: d.id, percent: Number(d.percent) };
  } catch {
    return null;
  }
}

/** ชำระสำเร็จ → ส่วนลดถูกใช้แล้ว */
export async function markDiscountUsed(order) {
  if (!order?.discount_id) return;
  try {
    await getAdminClient()
      .from('online_discounts')
      .update({ status: 'USED', used_at: new Date().toISOString(), order_id: order.order_id })
      .eq('id', order.discount_id);
  } catch (err) {
    console.error('[onlineReward] mark used failed:', err?.message || err);
  }
}

/** ส่วนลดถาวรจากระดับสมาชิก (Lv.) — ชั่วโมงสะสมทั้งหมด = รอบที่ครบ × 100 ชม. + นาทีรอบปัจจุบัน */
export async function levelDiscountPct(userId) {
  try {
    const { data: row, error } = await getAdminClient()
      .from('online_progress').select('minutes, cycles').eq('user_id', String(userId)).maybeSingle();
    if (error || !row) return 0;
    return levelInfo((Number(row.cycles) || 0) * GOAL_MIN + (Number(row.minutes) || 0)).discountPct;
  } catch {
    return 0;
  }
}

export function discountedPrice(price, percent) {
  return Math.round(Number(price) * (100 - percent)) / 100;
}

/** ประวัติการสะสมชั่วโมงรายวัน (ย้อนหลัง n วัน, เวลาไทย) + สรุประดับ */
export async function getHoursHistory(userId, days = 90) {
  const since = new Date(Date.now() + 7 * 3600000 - days * DAY_MS).toISOString().slice(0, 10);
  const { data, error } = await getAdminClient()
    .from('online_daily').select('day, minutes').eq('user_id', String(userId)).gte('day', since).order('day', { ascending: true });
  // แยกตามบัญชี MT5: รายวันในช่วงที่เลือก + ยอดสะสมทั้งหมดต่อบัญชี (Patch 12 · ยังไม่ได้รัน = null)
  let accounts = null;
  const sb = getAdminClient();
  const { data: accRows, error: accErr } = await sb
    .from('online_daily_accounts').select('day, login, minutes').eq('user_id', String(userId)).gte('day', since).order('day', { ascending: true });
  if (!accErr) {
    const { data: allRows } = await sb.from('online_daily_accounts').select('login, minutes').eq('user_id', String(userId));
    const lifetime = {};
    for (const r of allRows || []) lifetime[r.login] = (lifetime[r.login] || 0) + (Number(r.minutes) || 0);
    const inRange = {};
    for (const r of accRows || []) inRange[r.login] = (inRange[r.login] || 0) + (Number(r.minutes) || 0);
    // ชื่อโบรกเกอร์/Profile ล่าสุดของแต่ละบัญชี (จาก bot_telemetry_accounts · Patch 08)
    const { data: tel } = await sb.from('bot_telemetry_accounts').select('login, profile, radar_signals').eq('user_id', Number(userId));
    const meta = {};
    for (const t of tel || []) {
      const acc = Array.isArray(t.radar_signals) ? t.radar_signals[0]?.account : null;
      meta[t.login] = { profile: t.profile || null, server: acc?.server || null, mode: acc?.mode || null };
    }
    accounts = {
      days: (accRows || []).map((r) => ({ day: r.day, login: Number(r.login), minutes: Number(r.minutes) || 0 })),
      list: Object.keys(lifetime)
        .map((k) => ({ login: Number(k), minutesInRange: inRange[k] || 0, minutesTotal: lifetime[k], ...(meta[k] || {}) }))
        .sort((a, b) => b.minutesTotal - a.minutesTotal),
    };
  }
  return { rows: error ? null : (data || []).map((r) => ({ day: r.day, minutes: Number(r.minutes) || 0 })), accounts, status: await getRewardStatus(userId) };
}
