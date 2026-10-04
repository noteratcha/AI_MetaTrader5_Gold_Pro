import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, clientIp, hashPassword, isAdminRow, normalizeEmail, signToken, toUserPayload } from '../../../lib/server/auth';
import { logActivity } from '../../../lib/server/activity';
import { codeMatches, MAX_CODE_ATTEMPTS } from '../../../lib/server/passwordReset';

const INVALID = 'รหัสยืนยันไม่ถูกต้องหรือหมดอายุ กรุณาขอรหัสใหม่';

// ตั้งรหัสผ่านใหม่ด้วยรหัสยืนยัน 6 หลัก แล้วเข้าสู่ระบบให้ทันที
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;

  const email = normalizeEmail(req.body?.email);
  const code = String(req.body?.code || '').replace(/\D/g, '');
  const newPassword = String(req.body?.newPassword || '');
  const ip = clientIp(req);

  if (!email || code.length !== 6) return res.status(400).json({ success: false, error: 'กรุณากรอกอีเมลและรหัสยืนยัน 6 หลัก' });

  const supabase = getAdminClient();
  const { data: resets } = await supabase
    .from('password_resets')
    .select('*')
    .eq('email', email)
    .is('used_at', null)
    .gt('expires_at', new Date().toISOString())
    .order('created_at', { ascending: false })
    .limit(1);
  const reset = resets?.[0];
  if (!reset || reset.attempts >= MAX_CODE_ATTEMPTS) return res.status(400).json({ success: false, error: INVALID });

  if (!codeMatches(email, code, reset.code_hash)) {
    const attempts = (reset.attempts || 0) + 1;
    await supabase
      .from('password_resets')
      .update({ attempts, ...(attempts >= MAX_CODE_ATTEMPTS ? { used_at: new Date().toISOString() } : {}) })
      .eq('id', reset.id);
    const left = MAX_CODE_ATTEMPTS - attempts;
    return res.status(400).json({ success: false, error: left > 0 ? `รหัสยืนยันไม่ถูกต้อง (เหลืออีก ${left} ครั้ง)` : INVALID });
  }

  const { data: row } = await supabase.from('bot_config').select('*').eq('id', Number(reset.user_id)).maybeSingle();
  if (!row || normalizeEmail(row.mt5_server) !== email) return res.status(400).json({ success: false, error: INVALID });

  const minLen = isAdminRow(row) ? 10 : 6;
  if (newPassword.length < minLen) return res.status(400).json({ success: false, error: `รหัสผ่านใหม่ต้องมีอย่างน้อย ${minLen} ตัวอักษร` });
  if (isAdminRow(row) && /^\d+$/.test(newPassword)) return res.status(400).json({ success: false, error: 'รหัสผ่านแอดมินต้องมีตัวอักษรผสม ไม่ใช่ตัวเลขล้วน' });

  // ใช้รหัสได้ครั้งเดียว: จองแบบ atomic ก่อนเปลี่ยนรหัสผ่าน
  const { data: claimed } = await supabase.from('password_resets').update({ used_at: new Date().toISOString() }).eq('id', reset.id).is('used_at', null).select('id');
  if (!claimed?.length) return res.status(400).json({ success: false, error: INVALID });

  const { error } = await supabase.from('bot_config').update({ mt5_password: hashPassword(newPassword), updated_at: new Date().toISOString() }).eq('id', row.id);
  if (error) return res.status(500).json({ success: false, error: 'ตั้งรหัสผ่านใหม่ไม่สำเร็จ กรุณาลองใหม่' });

  await logActivity({ userId: row.id, email, event: 'password_reset', detail: 'ตั้งรหัสผ่านใหม่ด้วยรหัสยืนยันทางอีเมล', ip });
  const user = toUserPayload(row);
  return res.status(200).json({ success: true, message: 'ตั้งรหัสผ่านใหม่สำเร็จ', user, token: signToken(row.id, user.email) });
}
