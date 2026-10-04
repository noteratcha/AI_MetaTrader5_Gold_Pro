import { getAdminClient } from '../../../../../lib/server/supabaseAdmin';
import { allowMethods, hashPassword, requireAdmin } from '../../../../../lib/server/auth';
import { enrichUsers, isAdminRow, loadUserRow, rowTags, setTag, toggleTag } from '../../../../../lib/server/adminUsers';
import { logActivity } from '../../../../../lib/server/activity';

// GET    รายละเอียดผู้ใช้ + สรุปการใช้งาน
// PATCH  แก้ไข: displayName, hours (ตั้งค่า), addHours (บวก/ลบ), disabled, newPassword
// DELETE ลบผู้ใช้ (ห้ามแก้/ลบบัญชีแอดมิน)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET', 'PATCH', 'DELETE'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  const row = await loadUserRow(req.query.id);
  if (!row) return res.status(404).json({ success: false, error: 'ไม่พบผู้ใช้' });

  if (req.method === 'GET') {
    const [user] = await enrichUsers([row]);
    return res.status(200).json({ success: true, user });
  }

  if (isAdminRow(row)) {
    return res.status(403).json({ success: false, error: 'ไม่สามารถแก้ไขหรือลบบัญชีผู้ดูแลระบบได้' });
  }

  const supabase = getAdminClient();
  const email = row.mt5_server;

  if (req.method === 'DELETE') {
    if (String(req.body?.confirmEmail || '').toLowerCase() !== email) {
      return res.status(400).json({ success: false, error: 'กรุณายืนยันโดยพิมพ์อีเมลของผู้ใช้ให้ถูกต้อง' });
    }
    const { error } = await supabase.from('bot_config').delete().eq('id', row.id);
    if (error) return res.status(500).json({ success: false, error: 'ลบผู้ใช้ไม่สำเร็จ' });
    await supabase.from('bot_telemetry').delete().eq('id', row.id);
    await logActivity({ userId: row.id, email, event: 'admin_delete', detail: 'ลบบัญชีโดยแอดมิน', actor: auth.user.email });
    return res.status(200).json({ success: true });
  }

  // PATCH
  const body = req.body || {};
  const update = {};
  const changes = [];
  let tags = rowTags(row);

  if (typeof body.displayName === 'string' && body.displayName.trim()) {
    tags = setTag(tags, 'name:', body.displayName.trim().slice(0, 40));
    changes.push(`ชื่อ → ${body.displayName.trim().slice(0, 40)}`);
  }
  if (typeof body.disabled === 'boolean') {
    tags = toggleTag(tags, 'status:disabled', body.disabled);
    changes.push(body.disabled ? 'ระงับบัญชี' : 'เปิดใช้งานบัญชี');
  }
  if (tags.join('|') !== rowTags(row).join('|')) update.symbols_trading = tags;

  let newHours = null;
  if (body.hours !== undefined && body.hours !== null && body.hours !== '') {
    newHours = Number(body.hours);
  } else if (body.addHours !== undefined && body.addHours !== null && body.addHours !== '') {
    newHours = (Number(row.lot_size) || 0) + Number(body.addHours);
  }
  if (newHours !== null) {
    if (!Number.isFinite(newHours) || newHours < 0 || newHours > 9999) {
      return res.status(400).json({ success: false, error: 'ชั่วโมงต้องอยู่ระหว่าง 0–9,999' });
    }
    update.lot_size = Math.round(newHours * 100) / 100;
    changes.push(`ชั่วโมง ${Number(row.lot_size).toFixed(2)} → ${update.lot_size.toFixed(2)}`);
  }

  if (typeof body.newPassword === 'string' && body.newPassword) {
    if (body.newPassword.length < 6) return res.status(400).json({ success: false, error: 'รหัสผ่านใหม่ต้องมีอย่างน้อย 6 ตัวอักษร' });
    update.mt5_password = hashPassword(body.newPassword);
    changes.push('รีเซ็ตรหัสผ่าน');
  }

  if (!Object.keys(update).length) return res.status(400).json({ success: false, error: 'ไม่มีข้อมูลที่ต้องแก้ไข' });
  update.updated_at = new Date().toISOString();

  const { data, error } = await supabase.from('bot_config').update(update).eq('id', row.id).select().maybeSingle();
  if (error || !data) return res.status(500).json({ success: false, error: 'บันทึกไม่สำเร็จ' });

  await logActivity({ userId: row.id, email, event: 'admin_update', detail: changes.join(' · '), actor: auth.user.email });
  const [user] = await enrichUsers([data]);
  return res.status(200).json({ success: true, user });
}
