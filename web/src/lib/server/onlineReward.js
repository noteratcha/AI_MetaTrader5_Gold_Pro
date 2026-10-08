import { getAdminClient } from './supabaseAdmin';
import { ONLINE_GOAL_HOURS, ONLINE_DISCOUNT_PCT, ONLINE_DISCOUNT_DAYS } from '../onlineReward';

// รางวัลออนไลน์: นาทีที่หักจริงจาก /api/auth/meter สะสมรายสัปดาห์ (อาทิตย์–เสาร์ เวลาไทย)
// ครบ 100 ชม. → ส่วนลด 10% ซื้อชั่วโมงครั้งถัดไป 1 รายการ ใช้ได้ภายใน 5 วัน (supabase_online_reward_patch_07.sql)
const GOAL_MIN = ONLINE_GOAL_HOURS * 60;
const DAY_MS = 24 * 60 * 60 * 1000;
const BKK_MS = 7 * 60 * 60 * 1000;

/** วันอาทิตย์ที่เริ่มสัปดาห์ (เวลาไทย) → 'YYYY-MM-DD' */
export function weekStartBkk(date = new Date()) {
  const bkk = new Date(date.getTime() + BKK_MS);
  const start = new Date(Date.UTC(bkk.getUTCFullYear(), bkk.getUTCMonth(), bkk.getUTCDate() - bkk.getUTCDay()));
  return start.toISOString().slice(0, 10);
}

/** สิ้นสุดสัปดาห์ = เสาร์ 23:59:59 เวลาไทย (ISO) */
function weekEndIso(weekStart) {
  return new Date(Date.parse(`${weekStart}T00:00:00Z`) + 7 * DAY_MS - BKK_MS - 1000).toISOString();
}

/** บวกนาทีออนไลน์ของสัปดาห์นี้ · ข้ามเกณฑ์ 100 ชม. → ออกส่วนลด (สัปดาห์ละ 1 สิทธิ์) — ล้มเหลวได้โดยไม่กระทบการหักเวลา */
export async function addOnlineMinutes(user, minutes) {
  try {
    const week = weekStartBkk();
    const { data: total, error } = await getAdminClient().rpc('add_online_minutes', {
      p_user: String(user.id), p_email: user.email, p_week: week, p_minutes: Math.floor(minutes),
    });
    if (error) throw error;
    const now = Number(total) || 0;
    if (now >= GOAL_MIN && now - minutes < GOAL_MIN) {
      const earned = new Date();
      await getAdminClient().from('online_discounts').upsert(
        {
          user_id: String(user.id), email: user.email, week_start: week, percent: ONLINE_DISCOUNT_PCT,
          earned_at: earned.toISOString(), expires_at: new Date(earned.getTime() + ONLINE_DISCOUNT_DAYS * DAY_MS).toISOString(),
        },
        { onConflict: 'user_id,week_start', ignoreDuplicates: true }
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
    const week = weekStartBkk();
    const { data: row, error } = await getAdminClient()
      .from('online_weekly').select('minutes').eq('user_id', String(userId)).eq('week_start', week).maybeSingle();
    if (error) return null;   // ยังไม่ได้รัน supabase_online_reward_patch_07.sql — ซ่อนส่วนนี้
    const d = await usableDiscount(userId);
    return {
      weekStart: week,
      weekEnd: weekEndIso(week),
      minutes: Number(row?.minutes) || 0,
      goalMinutes: GOAL_MIN,
      discount: d ? { percent: Number(d.percent), expiresAt: d.expires_at, earnedAt: d.earned_at } : null,
    };
  } catch {
    return null;   // ยังไม่ได้รัน migration — ไม่แสดงส่วนนี้
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

export function discountedPrice(price, percent) {
  return Math.round(Number(price) * (100 - percent)) / 100;
}
