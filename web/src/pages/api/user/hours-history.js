import { allowMethods, requireUser } from '../../../lib/server/auth';
import { getHoursHistory } from '../../../lib/server/onlineReward';

// ประวัติการสะสมชั่วโมง (นาทีที่บอททำงานและถูกหักจริง) รายวันย้อนหลัง + ระดับสมาชิก — เว็บและโปรแกรมใช้ร่วมกัน
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;
  const days = Math.min(365, Math.max(7, Math.floor(Number(req.query.days) || 90)));
  const { rows, accounts, status } = await getHoursHistory(auth.user.id, days);
  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({ success: true, days, rows: rows || [], available: rows !== null, accounts, online: status });
}
