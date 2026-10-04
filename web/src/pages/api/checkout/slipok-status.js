import { allowMethods, requireAdmin } from '../../../lib/server/auth';

const SLIPOK_BRANCH_ID = process.env.SLIPOK_BRANCH_ID || '';
const SLIPOK_API_KEY = process.env.SLIPOK_API_KEY || '';

// ตรวจการเชื่อมต่อ/โควต้า SlipOK (Admin เท่านั้น)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  if (!SLIPOK_BRANCH_ID || !SLIPOK_API_KEY) {
    return res.status(200).json({ success: true, connected: false, error: 'ยังไม่ได้ตั้งค่า SLIPOK_BRANCH_ID / SLIPOK_API_KEY' });
  }

  try {
    const r = await fetch(`https://api.slipok.com/api/line/apikey/${SLIPOK_BRANCH_ID}/quota`, {
      headers: { 'x-authorization': SLIPOK_API_KEY },
    });
    const data = await r.json().catch(() => ({}));
    return res.status(200).json({ success: true, connected: Boolean(r.ok && data.success), quota: data.data || null });
  } catch (err) {
    return res.status(200).json({ success: true, connected: false, error: err.message });
  }
}
