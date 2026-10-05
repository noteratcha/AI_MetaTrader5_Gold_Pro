import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, normalizeEmail, requireUser } from '../../../lib/server/auth';
import { backfillReceipts, emailReceipt, findReceipt, receiptsReady, toPublicReceipt } from '../../../lib/server/receipts';
import { getOrder } from '../../../lib/server/orders';

const SETUP_ERROR = 'ระบบใบเสร็จยังไม่พร้อม — แอดมินต้องรัน supabase_receipts_patch_04.sql ใน Supabase ก่อน';

const RESEND_COOLDOWN_MS = 60 * 1000;

// GET              → ใบเสร็จทั้งหมดของฉัน
// GET ?id=<เลขที่ใบเสร็จหรือเลขคำสั่งซื้อ> → ใบเสร็จใบเดียว (เจ้าของหรือแอดมิน)
// POST { id }      → ส่งอีเมลใบเสร็จอีกครั้ง (เจ้าของหรือแอดมิน, เว้น 60 วินาที)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET', 'POST'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;
  res.setHeader('Cache-Control', 'no-store');

  const canSee = (r) => auth.user.isAdmin || normalizeEmail(r.email) === normalizeEmail(auth.user.email);
  const id = req.method === 'GET' ? req.query.id : req.body?.id;

  if (!(await receiptsReady())) {
    if (req.method === 'GET' && !id) return res.status(200).json({ success: true, receipts: [], setupRequired: true, error: SETUP_ERROR });
    return res.status(503).json({ success: false, error: SETUP_ERROR });
  }

  if (req.method === 'GET' && !id) {
    // ออกใบเสร็จย้อนหลังให้คำสั่งซื้อที่ชำระแล้วของฉันที่ยังไม่มีใบเสร็จ
    const { data: myOrders } = await getAdminClient()
      .from('orders')
      .select('*')
      .eq('owner_email', normalizeEmail(auth.user.email))
      .eq('status', 'PAID')
      .order('paid_at', { ascending: false })
      .limit(50);
    await backfillReceipts(myOrders);

    const { data, error } = await getAdminClient()
      .from('receipts')
      .select('*')
      .eq('email', normalizeEmail(auth.user.email))
      .order('issued_at', { ascending: false })
      .limit(100);
    if (error) return res.status(200).json({ success: true, receipts: [], setupRequired: true });
    return res.status(200).json({ success: true, receipts: (data || []).map(toPublicReceipt) });
  }

  let receipt = await findReceipt(id);
  if (!receipt) {
    // ลิงก์จากเลขคำสั่งซื้อที่ยังไม่มีใบเสร็จ → ออกให้ย้อนหลังถ้าชำระแล้วและเป็นเจ้าของ/แอดมิน
    const order = await getOrder(String(id));
    const ownsOrder = order && (auth.user.isAdmin || normalizeEmail(order.owner_email) === normalizeEmail(auth.user.email));
    if (order && ownsOrder && order.status === 'PAID') {
      await backfillReceipts([order]);
      receipt = await findReceipt(order.order_id);
    } else if (order && ownsOrder) {
      return res.status(404).json({ success: false, error: 'คำสั่งซื้อนี้ยังไม่ได้ชำระเงิน จึงยังไม่มีใบเสร็จ' });
    }
  }
  if (!receipt || !canSee(receipt)) return res.status(404).json({ success: false, error: 'ไม่พบใบเสร็จ' });

  if (req.method === 'GET') return res.status(200).json({ success: true, receipt: toPublicReceipt(receipt) });

  if (receipt.emailed_at && Date.now() - new Date(receipt.emailed_at).getTime() < RESEND_COOLDOWN_MS) {
    return res.status(429).json({ success: false, error: 'เพิ่งส่งไปเมื่อสักครู่ กรุณารอ 1 นาทีแล้วลองใหม่' });
  }
  const result = await emailReceipt(receipt);
  if (!result.ok) return res.status(502).json({ success: false, error: result.error });
  return res.status(200).json({ success: true, message: `ส่งใบเสร็จไปที่ ${receipt.email} แล้ว` });
}
