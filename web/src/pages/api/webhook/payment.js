import crypto from 'crypto';
import { allowMethods } from '../../../lib/server/auth';
import { fulfillOrder, getOrder } from '../../../lib/server/orders';

// Webhook จากผู้ให้บริการชำระเงิน — ต้องส่ง Header "x-webhook-secret" ตรงกับ PAYMENT_WEBHOOK_SECRET
const WEBHOOK_SECRET = process.env.PAYMENT_WEBHOOK_SECRET || '';

function secretMatches(provided) {
  if (!WEBHOOK_SECRET || !provided) return false;
  const a = Buffer.from(String(provided));
  const b = Buffer.from(WEBHOOK_SECRET);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;

  if (!WEBHOOK_SECRET) {
    return res.status(503).json({ success: false, error: 'Webhook is not configured' });
  }
  if (!secretMatches(req.headers['x-webhook-secret'])) {
    return res.status(401).json({ success: false, error: 'Invalid webhook secret' });
  }

  const payload = req.body || {};
  const orderId = payload.order_id || payload.orderId || payload.referenceNo || payload.data?.order_id;
  const paymentRef = payload.payment_ref || payload.transaction_id || payload.data?.transRef || `BANK-${Date.now()}`;
  const status = String(payload.status || payload.resultCode || payload.data?.status || '').toUpperCase();

  if (!orderId) {
    return res.status(400).json({ success: false, error: 'Missing order_id' });
  }
  if (!['SUCCESS', '00', 'PAID'].includes(status)) {
    return res.status(200).json({ success: true, ignored: true, status });
  }

  const order = await getOrder(String(orderId));
  if (!order) {
    return res.status(404).json({ success: false, error: 'Order not found' });
  }

  const result = await fulfillOrder(order, paymentRef);
  if (!result.ok) {
    return res.status(409).json({ success: false, error: result.error });
  }
  return res.status(200).json({ success: true, order_id: order.order_id, already_paid: result.alreadyPaid });
}
