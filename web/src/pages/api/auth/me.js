import { allowMethods, requireUser } from '../../../lib/server/auth';
import { getRewardStatus } from '../../../lib/server/onlineReward';

// ข้อมูลบัญชีของผู้ใช้ที่ล็อกอินอยู่ (ต้องส่ง Authorization: Bearer <token>)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;
  res.setHeader('Cache-Control', 'no-store');
  const online = await getRewardStatus(auth.user.id);
  return res.status(200).json({ success: true, user: { ...auth.user, online } });
}
