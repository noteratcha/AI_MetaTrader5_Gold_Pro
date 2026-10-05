import { getAdminClient, insertTolerant } from './supabaseAdmin';
import { generateProductKey } from './keys';
import { logActivity } from './activity';
import { notifyPurchase } from './lineNotify';
import { issueReceipt } from './receipts';

export const ORDER_MAX_AGE_MS = 24 * 60 * 60 * 1000;
// เวลาชำระตาม QR (ตรงกับตัวนับถอยหลังหน้าร้าน) — เกินแล้วยกเลิกคำสั่งซื้อ
export const ORDER_PAY_WINDOW_MS = 15 * 60 * 1000;

/** ยกเลิกคำสั่งซื้อที่ยังไม่ชำระและเกินเวลา QR (ทั้งระบบ) — คืนจำนวนที่ยกเลิก */
export async function expireStaleOrders() {
  try {
    const cutoff = new Date(Date.now() - ORDER_PAY_WINDOW_MS).toISOString();
    const { data } = await getAdminClient()
      .from('orders')
      .update({ status: 'CANCELLED' })
      .eq('status', 'PENDING')
      .lt('created_at', cutoff)
      .select('order_id');
    return data?.length || 0;
  } catch {
    return 0;
  }
}

/** ยกเลิกคำสั่งซื้อเดียว (เฉพาะที่ยังรอชำระ) */
export async function cancelOrder(orderId) {
  const { data } = await getAdminClient()
    .from('orders')
    .update({ status: 'CANCELLED' })
    .eq('order_id', orderId)
    .eq('status', 'PENDING')
    .select('order_id');
  return Boolean(data?.length);
}

export async function getOrder(orderId) {
  if (!orderId || typeof orderId !== 'string' || orderId.length > 64) return null;
  const { data } = await getAdminClient().from('orders').select('*').eq('order_id', orderId).maybeSingle();
  return data || null;
}

/** คำสั่งซื้อนี้เป็นของผู้ใช้คนนี้หรือไม่ (ฐานข้อมูลก่อน migration ไม่มีคอลัมน์เจ้าของ — ใช้ order_id ที่เดาไม่ได้แทน) */
export function isOrderOwner(order, user) {
  if (!order) return false;
  if (order.owner_user_id === undefined && order.owner_email === undefined) return true;
  return String(order.owner_user_id) === String(user.id) || String(order.owner_email || '').toLowerCase() === user.email;
}

export function publicOrder(order) {
  const isPaid = order.status === 'PAID';
  return {
    order_id: order.order_id,
    status: order.status,
    is_paid: isPaid,
    is_cancelled: order.status === 'CANCELLED',
    amount_thb: Number(order.amount_thb),
    hours_to_add: Number(order.hours_to_add),
    package_id: order.package_id,
    qr_image_url: order.qr_image_url,
    created_at: order.created_at,
    paid_at: order.paid_at,
    generated_key_code: isPaid ? order.generated_key_code : null,
  };
}

/**
 * ยืนยันการชำระเงินและออก Product Key (ทำครั้งเดียวต่อคำสั่งซื้อ)
 * ใช้สถานะ PROCESSING เป็นตัวล็อก กันการออกคีย์ซ้ำเมื่อมี request พร้อมกัน (Webhook + ตรวจสลิป)
 */
export async function fulfillOrder(order, paymentRef) {
  const supabase = getAdminClient();

  if (order.status === 'PAID') {
    return { ok: true, productKey: order.generated_key_code, alreadyPaid: true };
  }

  const { data: locked } = await supabase
    .from('orders')
    .update({ status: 'PROCESSING' })
    .eq('order_id', order.order_id)
    .in('status', ['PENDING', 'CANCELLED'])
    .select('order_id');

  if (!locked || locked.length !== 1) {
    const latest = await getOrder(order.order_id);
    if (latest?.status === 'PAID') return { ok: true, productKey: latest.generated_key_code, alreadyPaid: true };
    return { ok: false, error: 'คำสั่งซื้อนี้กำลังถูกดำเนินการ กรุณารอสักครู่' };
  }

  // ชั่วโมงอ้างอิงจากคำสั่งซื้อ (บันทึกตอนสร้าง QR) — แพ็กเกจอาจถูกแก้ไขภายหลัง
  const baseHours = Number(order.hours_to_add) || 0;
  const bonusHours = 0;
  const productKey = generateProductKey();

  const { error: keyErr } = await insertTolerant(
    'product_keys',
    {
      key_code: productKey,
      hours: baseHours,
      bonus_hours: bonusHours,
      price_thb: Number(order.amount_thb),
      status: 'UNUSED',
      is_used: false,
      order_id: order.order_id,
      purchased_at: new Date().toISOString(),
      owner_email: order.owner_email || null,
    },
    ['owner_email']
  );

  if (keyErr) {
    console.error('[orders] product key insert failed:', keyErr.message);
    await supabase.from('orders').update({ status: order.status === 'CANCELLED' ? 'CANCELLED' : 'PENDING' }).eq('order_id', order.order_id);
    return { ok: false, error: 'ออกรหัส Product Key ไม่สำเร็จ กรุณาติดต่อแอดมิน' };
  }

  await supabase
    .from('orders')
    .update({
      status: 'PAID',
      payment_ref: String(paymentRef || '').slice(0, 120),
      generated_key_code: productKey,
      paid_at: new Date().toISOString(),
    })
    .eq('order_id', order.order_id);

  await logActivity({
    userId: order.owner_user_id,
    email: order.owner_email,
    event: 'purchase_paid',
    detail: `ชำระ ฿${Number(order.amount_thb)} (${order.order_id}) → คีย์ ${productKey} +${baseHours} ชม.`,
  });
  // ใบเสร็จ: บันทึกลงตาราง receipts + ส่งอีเมลให้ผู้ซื้อ (ล้มเหลวได้โดยไม่กระทบการออกคีย์)
  await issueReceipt({ ...order, payment_ref: paymentRef, generated_key_code: productKey }, { productKey, paymentRef });
  await notifyPurchase({
    email: order.owner_email,
    amountThb: order.amount_thb,
    hours: baseHours,
    orderId: order.order_id,
    productKey,
  });
  return { ok: true, productKey, alreadyPaid: false };
}
