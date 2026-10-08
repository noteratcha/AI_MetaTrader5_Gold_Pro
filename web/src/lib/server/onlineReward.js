import { getAdminClient } from './supabaseAdmin';
import { ONLINE_GOAL_HOURS, ONLINE_DISCOUNT_PCT, ONLINE_DISCOUNT_DAYS } from '../onlineReward';

// รางวัลออนไลน์: นาทีที่หักจริงจาก /api/auth/meter สะสมเป็นรอบ (supabase_online_reward_patch_07.sql)
// ครบ 100 ชม. → ส่วนลด 10% ซื้อชั่วโมงครั้งถัดไป 1 รายการ ใช้ได้ภายใน 3 วัน (เมื่อได้รับแล้วเริ่มนับชั่วโมงใหม่ทันที)
const GOAL_MIN = ONLINE_GOAL_HOURS * 60;
const DAY_MS = 24 * 60 * 60 * 1000;
/** บวกนาทีออนไลน์ (atomic ใน Postgres) · ครบ 100 ชม. → ออกส่วนลด (อายุ 3 วัน) และเริ่มนับรอบใหม่ทันที (เศษยกไป) */
export async function addOnlineMinutes(user, minutes) {
  try {
    const { data, error } = await getAdminClient().rpc('add_online_minutes', {
      p_user: String(user.id), p_email: user.email, p_minutes: Math.floor(minutes), p_goal: GOAL_MIN,
    });
    if (error) throw error;
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

export function discountedPrice(price, percent) {
  return Math.round(Number(price) * (100 - percent)) / 100;
}
