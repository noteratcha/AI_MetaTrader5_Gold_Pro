import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import {
  allowMethods,
  hashPassword,
  needsRehash,
  normalizeEmail,
  signToken,
  toUserPayload,
  verifyPassword,
} from '../../../lib/server/auth';

const INVALID_CREDENTIALS = 'อีเมลหรือรหัสผ่านไม่ถูกต้อง';

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;

  try {
    const email = normalizeEmail(req.body?.email);
    const password = String(req.body?.password || '');

    if (!email || !password) {
      return res.status(400).json({ success: false, error: 'กรุณากรอกอีเมลและรหัสผ่านให้ครบถ้วน' });
    }

    const supabase = getAdminClient();
    const { data: rows, error } = await supabase
      .from('bot_config')
      .select('*')
      .eq('mt5_server', email)
      .gt('id', 1)
      .limit(1);

    if (error) {
      console.error('[auth/login] query error:', error.message);
      return res.status(500).json({ success: false, error: 'ระบบฐานข้อมูลขัดข้อง กรุณาลองใหม่' });
    }

    const row = rows?.[0];
    if (!row || !verifyPassword(password, row.mt5_password)) {
      return res.status(401).json({ success: false, error: INVALID_CREDENTIALS });
    }

    // อัปเกรด hash เก่า (v1 = 10k รอบ) เป็น v2 อัตโนมัติเมื่อล็อกอินสำเร็จ
    if (needsRehash(row.mt5_password)) {
      await supabase.from('bot_config').update({ mt5_password: hashPassword(password) }).eq('id', row.id);
    }

    const user = toUserPayload(row);
    return res.status(200).json({
      success: true,
      message: 'เข้าสู่ระบบสำเร็จ!',
      user,
      token: signToken(row.id, user.email),
    });
  } catch (err) {
    console.error('[auth/login] exception:', err);
    return res.status(500).json({ success: false, error: 'เกิดข้อผิดพลาดในการเข้าสู่ระบบ' });
  }
}
