import { allowMethods, requireUser } from '../../../lib/server/auth';
import { membershipHistory } from '../../../lib/server/membership';

// สถานะสมาชิกรายเดือน + ประวัติ (สมัคร / ต่ออายุ / แอดมินปรับ / ยกเลิก) ของผู้ใช้เอง
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;
  const history = await membershipHistory(auth.user.id);
  return res.status(200).json({ success: true, membership: auth.user.membership, history });
}
