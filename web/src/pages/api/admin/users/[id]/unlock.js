import { allowMethods, requireAdmin } from '../../../../../lib/server/auth';
import { enrichUsers, loadUserRow } from '../../../../../lib/server/adminUsers';
import { logActivity } from '../../../../../lib/server/activity';

// POST ปลดล็อกการเข้าสู่ระบบที่ถูกล็อกจากการใส่รหัสผิดหลายครั้ง (ล้างตัวนับรหัสผิด)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  const row = await loadUserRow(req.query.id);
  if (!row) return res.status(404).json({ success: false, error: 'ไม่พบผู้ใช้' });

  await logActivity({
    userId: row.id,
    email: row.mt5_server,
    event: 'account_unlocked',
    detail: `แอดมินปลดล็อกการเข้าสู่ระบบ`,
    actor: auth.user.email,
  });
  const [user] = await enrichUsers([row]);
  return res.status(200).json({ success: true, message: `ปลดล็อก ${row.mt5_server} แล้ว — ผู้ใช้เข้าสู่ระบบได้ทันที`, user });
}
