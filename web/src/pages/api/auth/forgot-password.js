import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, clientIp, isDisabledRow, isValidEmail, normalizeEmail, toUserPayload } from '../../../lib/server/auth';
import { logActivity } from '../../../lib/server/activity';
import { isMailConfigured, sendResetCodeEmail } from '../../../lib/server/mailer';
import { CODE_TTL_MINUTES, generateCode, hashCode, MAX_REQUESTS_PER_EMAIL_HOUR, MAX_REQUESTS_PER_IP_HOUR, REGISTER_MARKER } from '../../../lib/server/passwordReset';

// ขอรหัสยืนยันรีเซ็ตรหัสผ่านทางอีเมล
// ตอบข้อความเดียวกันเสมอ ไม่ว่าจะมีบัญชีหรือไม่ (กันการสุ่มหาอีเมลสมาชิก)
const GENERIC_OK = `หากอีเมลนี้มีบัญชีอยู่ เราได้ส่งรหัสยืนยัน 6 หลักไปให้แล้ว (ใช้ได้ ${CODE_TTL_MINUTES} นาที) — ตรวจกล่องจดหมายขยะด้วย`;

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;

  const email = normalizeEmail(req.body?.email);
  const ip = clientIp(req);
  if (!isValidEmail(email)) return res.status(400).json({ success: false, error: 'กรุณากรอกอีเมลที่ถูกต้อง' });
  if (!isMailConfigured()) {
    return res.status(503).json({ success: false, error: 'ระบบส่งอีเมลยังไม่พร้อม กรุณาติดต่อผู้ดูแลระบบเพื่อรีเซ็ตรหัสผ่าน' });
  }

  const supabase = getAdminClient();
  const hourAgo = new Date(Date.now() - 3600000).toISOString();
  const [byEmail, byIp] = await Promise.all([
    supabase.from('password_resets').select('id', { count: 'exact', head: true }).eq('email', email).gte('created_at', hourAgo),
    supabase.from('password_resets').select('id', { count: 'exact', head: true }).eq('ip', ip).gte('created_at', hourAgo),
  ]);
  if (byEmail.error) {
    console.error('[forgot-password] table missing?', byEmail.error.message);
    return res.status(503).json({ success: false, error: 'ระบบลืมรหัสผ่านยังไม่พร้อม (ต้องรัน supabase_password_reset_patch_03.sql)' });
  }
  if ((byEmail.count || 0) >= MAX_REQUESTS_PER_EMAIL_HOUR || (byIp.count || 0) >= MAX_REQUESTS_PER_IP_HOUR) {
    return res.status(429).json({ success: false, error: 'ขอรหัสบ่อยเกินไป กรุณารอ 1 ชั่วโมงแล้วลองใหม่' });
  }

  const { data: rows } = await supabase.from('bot_config').select('*').eq('mt5_server', email).gt('id', 1).limit(1);
  const row = rows?.[0];

  // ไม่มีบัญชี / ถูกระงับ → บันทึกคำขอไว้ (นับ rate limit) แต่ไม่ส่งอีเมล และตอบเหมือนเดิม
  if (!row || isDisabledRow(row)) {
    await supabase.from('password_resets').insert({ user_id: '0', email, code_hash: 'none', expires_at: new Date().toISOString(), used_at: new Date().toISOString(), ip });
    return res.status(200).json({ success: true, message: GENERIC_OK });
  }

  // ยกเลิกรหัสเดิมที่ยังไม่ใช้ แล้วออกรหัสใหม่
  await supabase.from('password_resets').update({ used_at: new Date().toISOString() }).eq('email', email).neq('user_id', REGISTER_MARKER).is('used_at', null);
  const code = generateCode();
  const { error: insErr } = await supabase.from('password_resets').insert({
    user_id: String(row.id),
    email,
    code_hash: hashCode(email, code),
    expires_at: new Date(Date.now() + CODE_TTL_MINUTES * 60000).toISOString(),
    ip,
  });
  if (insErr) return res.status(500).json({ success: false, error: 'สร้างรหัสยืนยันไม่สำเร็จ กรุณาลองใหม่' });

  try {
    await sendResetCodeEmail(email, code, toUserPayload(row).displayName);
  } catch (err) {
    console.error('[forgot-password] send mail failed:', err.message);
    return res.status(502).json({ success: false, error: 'ส่งอีเมลไม่สำเร็จ กรุณาลองใหม่ภายหลัง' });
  }

  await logActivity({ userId: row.id, email, event: 'password_reset_requested', detail: 'ขอรหัสรีเซ็ตรหัสผ่านทางอีเมล', ip });
  return res.status(200).json({ success: true, message: GENERIC_OK });
}
