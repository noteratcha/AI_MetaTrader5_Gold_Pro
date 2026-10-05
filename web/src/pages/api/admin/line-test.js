import { allowMethods, requireAdmin } from '../../../lib/server/auth';
import { bangkokTime, isLineConfigured, notifyAdmins } from '../../../lib/server/lineNotify';

// POST ส่งข้อความทดสอบไปที่ LINE OA ของแอดมิน
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  if (!isLineConfigured()) {
    return res.status(400).json({ success: false, error: 'ยังไม่ได้ตั้งค่า LINE_CHANNEL_ACCESS_TOKEN และ LINE_ADMIN_TO บน Vercel' });
  }
  const result = await notifyAdmins(`✅ ทดสอบการแจ้งเตือน GoldBot24\nโดย: ${auth.user.email}\nเวลา: ${bangkokTime()}`);
  if (!result.sent) return res.status(502).json({ success: false, error: `ส่งไม่สำเร็จ: ${result.errors.join(' | ')}` });
  return res.status(200).json({ success: true, message: `ส่งข้อความทดสอบแล้ว (${result.sent} ปลายทาง)${result.errors.length ? ` · ล้มเหลว ${result.errors.length}` : ''}` });
}
