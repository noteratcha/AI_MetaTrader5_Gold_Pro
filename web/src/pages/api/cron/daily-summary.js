import crypto from 'crypto';
import { requireAdmin } from '../../../lib/server/auth';
import { sendDailySummary } from '../../../lib/server/dailySummary';

// สรุปยอดรายวันส่ง LINE OA — Vercel Cron รันหลังเที่ยงคืนเวลาไทย (17:00 UTC, ดู web/vercel.json)
//   แล้วสรุป "เมื่อวาน" เต็มวัน 00:00–23:59 น. (แพ็กเกจฟรีของ Vercel รัน Cron ไม่ตรงนาที จึงไม่ตั้ง 23:59 ตรง ๆ)
//   Vercel ส่ง Authorization: Bearer <CRON_SECRET> มาให้อัตโนมัติ · แอดมินกดส่งเองจากหน้า Admin ได้ (POST)
function isCron(req) {
  const secret = process.env.CRON_SECRET;
  const header = String(req.headers.authorization || '');
  if (!secret || !header.startsWith('Bearer ')) return false;
  const a = Buffer.from(header.slice(7));
  const b = Buffer.from(secret);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

export default async function handler(req, res) {
  if (req.method === 'GET' && isCron(req)) {
    const result = await sendDailySummary({ completedDay: true });
    return res.status(200).json({ success: result.sent > 0, sent: result.sent, errors: result.errors });
  }
  if (req.method !== 'POST') return res.status(401).json({ success: false, error: 'Unauthorized' });

  const auth = await requireAdmin(req, res);
  if (!auth) return;
  const result = await sendDailySummary();
  if (!result.sent) return res.status(502).json({ success: false, error: `ส่งไม่สำเร็จ: ${result.errors.join(' | ')}` });
  return res.status(200).json({ success: true, message: 'ส่งสรุปยอดวันนี้ไปที่ LINE แล้ว', metrics: result.metrics });
}
