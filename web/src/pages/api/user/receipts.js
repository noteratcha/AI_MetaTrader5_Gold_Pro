import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, normalizeEmail, requireUser } from '../../../lib/server/auth';
import { emailReceipt, findReceipt, toPublicReceipt } from '../../../lib/server/receipts';

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

  if (req.method === 'GET' && !id) {
    const { data, error } = await getAdminClient()
      .from('receipts')
      .select('*')
      .eq('email', normalizeEmail(auth.user.email))
      .order('issued_at', { ascending: false })
      .limit(100);
    if (error) return res.status(200).json({ success: true, receipts: [], setupRequired: true });
    return res.status(200).json({ success: true, receipts: (data || []).map(toPublicReceipt) });
  }

  const receipt = await findReceipt(id);
  if (!receipt || !canSee(receipt)) return res.status(404).json({ success: false, error: 'ไม่พบใบเสร็จ' });

  if (req.method === 'GET') return res.status(200).json({ success: true, receipt: toPublicReceipt(receipt) });

  if (receipt.emailed_at && Date.now() - new Date(receipt.emailed_at).getTime() < RESEND_COOLDOWN_MS) {
    return res.status(429).json({ success: false, error: 'เพิ่งส่งไปเมื่อสักครู่ กรุณารอ 1 นาทีแล้วลองใหม่' });
  }
  const result = await emailReceipt(receipt);
  if (!result.ok) return res.status(502).json({ success: false, error: result.error });
  return res.status(200).json({ success: true, message: `ส่งใบเสร็จไปที่ ${receipt.email} แล้ว` });
}
