import { insertTolerant } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireUser } from '../../../lib/server/auth';
import { generateOrderId } from '../../../lib/server/keys';
import { getPackage } from '../../../lib/server/catalog';
import { expireStaleOrders } from '../../../lib/server/orders';
import { discountedPrice, levelDiscountPct, reserveDiscount } from '../../../lib/server/onlineReward';
import { MEMBERSHIP, isMembershipPackage } from '../../../lib/membership';
import { ensureMembershipPackageRow } from '../../../lib/server/membership';

const PROMPTPAY_ID = process.env.PROMPTPAY_ID || '';

// สร้างคำสั่งซื้อ + PromptPay QR — ราคา/ชั่วโมงอ้างอิงจากแพ็กเกจฝั่ง Server เท่านั้น
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  // ยกเลิกคำสั่งซื้อที่หมดเวลา QR แล้วค้างอยู่ (เช่น ลูกค้าปิดหน้าต่างไปก่อน)
  await expireStaleOrders();

  // สมาชิกรายเดือน (id 900) ราคาจากโค้ดฝั่ง Server · แพ็กเกจชั่วโมงอ่านจากตาราง packages
  const pkg = isMembershipPackage(req.body?.package_id) ? MEMBERSHIP : await getPackage(req.body?.package_id);
  if (!pkg) {
    return res.status(400).json({ success: false, error: 'ไม่พบแพ็กเกจที่เลือก' });
  }
  if (!PROMPTPAY_ID) {
    return res.status(503).json({ success: false, error: 'ร้านค้ายังไม่ได้ตั้งค่าบัญชีพร้อมเพย์ (PROMPTPAY_ID)' });
  }

  if (isMembershipPackage(pkg.id)) await ensureMembershipPackageRow();   // FK orders.package_id → packages(id)

  const orderId = generateOrderId();
  // ค่าสมาชิกรายเดือนราคาเต็มเสมอ — ส่วนลด Lv./ออนไลน์ใช้กับการเติมชั่วโมงเท่านั้น (ผู้ใช้กำหนด 13 ต.ค. 2026)
  const isMember = isMembershipPackage(pkg.id);
  // ส่วนลดรางวัลออนไลน์ (ครบ 100 ชม./สัปดาห์) — ผูกกับคำสั่งซื้อนี้ ใช้จริงเมื่อชำระสำเร็จ
  const discount = isMember ? null : await reserveDiscount(auth.user.id, orderId);
  // + ส่วนลดถาวรจากระดับสมาชิก (ทุก 10 Lv. = 1%) — บวกกับสิทธิ์ออนไลน์ได้
  const levelPct = isMember ? 0 : await levelDiscountPct(auth.user.id);
  const totalPct = (discount ? discount.percent : 0) + levelPct;
  const price = totalPct > 0 ? discountedPrice(pkg.price, totalPct) : pkg.price;
  const amount = price.toFixed(2);
  const qrImageUrl = `https://promptpay.io/${encodeURIComponent(PROMPTPAY_ID)}/${amount}.png`;
  const createdAt = new Date().toISOString();

  const { error } = await insertTolerant(
    'orders',
    {
      order_id: orderId,
      package_id: pkg.id,
      amount_thb: price,
      hours_to_add: pkg.hours + pkg.bonus,
      status: 'PENDING',
      payment_method: 'PROMPTPAY',
      qr_image_url: qrImageUrl,
      created_at: createdAt,
      owner_user_id: auth.user.id,
      owner_email: auth.user.email,
      ...(totalPct > 0 ? { discount_id: discount ? discount.id : null, discount_pct: totalPct, original_amount_thb: pkg.price } : {}),
    },
    ['owner_user_id', 'owner_email']
  );

  if (error) {
    console.error('[checkout/create-qr] insert error:', error.message);
    return res.status(500).json({ success: false, error: 'สร้างคำสั่งซื้อไม่สำเร็จ กรุณาลองใหม่' });
  }

  return res.status(200).json({
    success: true,
    order_id: orderId,
    package_id: pkg.id,
    amount_thb: price,
    original_amount_thb: pkg.price,
    discount_pct: totalPct,
    level_discount_pct: levelPct,
    online_discount_pct: discount ? discount.percent : 0,
    hours_to_add: pkg.hours + pkg.bonus,
    is_membership: isMembershipPackage(pkg.id),
    membership_days: isMembershipPackage(pkg.id) ? MEMBERSHIP.days : 0,
    qr_image_url: qrImageUrl,
    created_at: createdAt,
  });
}
