import crypto from 'crypto';
import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import {
  allowMethods,
  hashPassword,
  isValidEmail,
  normalizeEmail,
  signToken,
  toUserPayload,
} from '../../../lib/server/auth';

const STARTER_HOURS = 48.0;

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;

  try {
    const email = normalizeEmail(req.body?.email);
    const password = String(req.body?.password || '');
    const displayName = String(req.body?.displayName || '').trim().slice(0, 40) || email.split('@')[0] || 'Trader';

    if (!isValidEmail(email)) {
      return res.status(400).json({ success: false, error: 'กรุณากรอกอีเมลที่ถูกต้อง' });
    }
    if (password.length < 6) {
      return res.status(400).json({ success: false, error: 'รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร' });
    }

    const supabase = getAdminClient();
    const { data: existing, error: checkErr } = await supabase.from('bot_config').select('id').eq('mt5_server', email).limit(1);
    if (checkErr) {
      console.error('[auth/register] check error:', checkErr.message);
      return res.status(500).json({ success: false, error: 'ระบบฐานข้อมูลขัดข้อง กรุณาลองใหม่' });
    }
    if (existing && existing.length > 0) {
      return res.status(409).json({ success: false, error: 'อีเมลนี้ลงทะเบียนไว้แล้ว กรุณาเข้าสู่ระบบ' });
    }

    const passwordHash = hashPassword(password);
    let created = null;
    // id สุ่ม 8 หลัก (>= 10,000 เสมอ ไม่ชนแถว config id=1) — ลองใหม่ถ้าชน Primary Key
    for (let attempt = 0; attempt < 3 && !created; attempt++) {
      const id = crypto.randomInt(10000, 100000000);
      const { data, error } = await supabase
        .from('bot_config')
        .insert({
          id,
          mt5_login: 0,
          mt5_password: passwordHash,
          mt5_server: email,
          is_bot_active: true,
          lot_size: STARTER_HOURS,
          symbols_trading: [`name:${displayName}`, 'role:user', `registered:${new Date().toISOString()}`],
        })
        .select()
        .maybeSingle();
      if (!error) {
        created = data;
      } else if (error.code !== '23505') {
        console.error('[auth/register] insert error:', error.message);
        return res.status(500).json({ success: false, error: 'ไม่สามารถสร้างบัญชีได้ กรุณาลองใหม่' });
      }
    }

    if (!created) {
      return res.status(500).json({ success: false, error: 'ไม่สามารถสร้างบัญชีได้ กรุณาลองใหม่' });
    }

    const user = toUserPayload(created);
    return res.status(200).json({
      success: true,
      message: `สมัครสมาชิกสำเร็จ! ได้รับโควต้าเริ่มต้น ${STARTER_HOURS} ชั่วโมง`,
      user,
      token: signToken(created.id, user.email),
    });
  } catch (err) {
    console.error('[auth/register] exception:', err);
    return res.status(500).json({ success: false, error: 'เกิดข้อผิดพลาดภายในระบบ' });
  }
}
