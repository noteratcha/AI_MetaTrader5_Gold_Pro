import { adjustHours, allowMethods, requireUser } from '../../../lib/server/auth';

// หักเวลาการใช้งานบอท (เรียกจาก Desktop App ทุก ~5 นาที พร้อมจำนวนนาทีที่ใช้ไป)
const MAX_MINUTES_PER_CALL = 24 * 60;

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  const minutes = Math.floor(Number(req.body?.minutes));
  if (!Number.isFinite(minutes) || minutes <= 0 || minutes > MAX_MINUTES_PER_CALL) {
    return res.status(400).json({ success: false, error: 'จำนวนนาทีไม่ถูกต้อง' });
  }

  try {
    const hoursRemaining = await adjustHours(auth.row.id, -(minutes / 60));
    return res.status(200).json({ success: true, minutesDeducted: minutes, hoursRemaining });
  } catch (err) {
    console.error('[auth/meter] error:', err);
    return res.status(500).json({ success: false, error: err.message || 'ไม่สามารถหักเวลาได้' });
  }
}
