import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, clientIp, hashPassword, requireUser, verifyPassword } from '../../../lib/server/auth';
import { logActivity } from '../../../lib/server/activity';

// เปลี่ยนรหัสผ่านของตัวเอง (ต้องยืนยันรหัสเดิม)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  const current = String(req.body?.currentPassword || '');
  const next = String(req.body?.newPassword || '');
  if (!verifyPassword(current, auth.row.mt5_password)) {
    return res.status(400).json({ success: false, error: 'รหัสผ่านเดิมไม่ถูกต้อง' });
  }
  const minLen = auth.user.isAdmin ? 10 : 6;
  if (next.length < minLen) {
    return res.status(400).json({ success: false, error: `รหัสผ่านใหม่ต้องมีอย่างน้อย ${minLen} ตัวอักษร` });
  }
  if (auth.user.isAdmin && /^\d+$/.test(next)) {
    return res.status(400).json({ success: false, error: 'รหัสผ่านแอดมินต้องมีตัวอักษรผสม ไม่ใช่ตัวเลขล้วน' });
  }
  if (next === current) {
    return res.status(400).json({ success: false, error: 'รหัสผ่านใหม่ต้องไม่ซ้ำรหัสเดิม' });
  }

  const { error } = await getAdminClient().from('bot_config').update({ mt5_password: hashPassword(next) }).eq('id', auth.row.id);
  if (error) return res.status(500).json({ success: false, error: 'เปลี่ยนรหัสผ่านไม่สำเร็จ' });
  await logActivity({ userId: auth.row.id, email: auth.user.email, event: 'password_changed', detail: 'เปลี่ยนรหัสผ่านด้วยตัวเอง', ip: clientIp(req) });
  return res.status(200).json({ success: true, message: 'เปลี่ยนรหัสผ่านสำเร็จ' });
}
