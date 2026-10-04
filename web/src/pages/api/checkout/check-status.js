import { allowMethods, requireUser } from '../../../lib/server/auth';
import { getOrder, isOrderOwner, publicOrder } from '../../../lib/server/orders';

// ตรวจสถานะคำสั่งซื้อ (เฉพาะเจ้าของคำสั่งซื้อ) — คืน Product Key เมื่อชำระแล้ว
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  const order = await getOrder(String(req.query.order_id || ''));
  if (!order || !isOrderOwner(order, auth.user)) {
    return res.status(404).json({ success: false, error: 'ไม่พบคำสั่งซื้อ' });
  }

  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({ success: true, ...publicOrder(order) });
}
