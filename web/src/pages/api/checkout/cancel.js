import { allowMethods, requireUser } from '../../../lib/server/auth';
import { cancelOrder, getOrder, isOrderOwner } from '../../../lib/server/orders';

// ยกเลิกคำสั่งซื้อของตัวเองที่ยังไม่ชำระ (เรียกเมื่อ QR หมดเวลา)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  const order = await getOrder(String(req.body?.order_id || ''));
  if (!order || !isOrderOwner(order, auth.user)) return res.status(404).json({ success: false, error: 'ไม่พบคำสั่งซื้อ' });
  if (order.status === 'PAID') return res.status(409).json({ success: false, error: 'คำสั่งซื้อนี้ชำระเงินแล้ว' });

  const cancelled = order.status === 'CANCELLED' || (await cancelOrder(order.order_id));
  return res.status(200).json({ success: true, cancelled, status: cancelled ? 'CANCELLED' : order.status });
}
