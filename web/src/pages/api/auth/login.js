import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import {
  allowMethods,
  clientIp,
  hashPassword,
  isDisabledRow,
  needsRehash,
  normalizeEmail,
  signToken,
  toUserPayload,
  verifyPassword,
} from '../../../lib/server/auth';
import { countRecentFailedLogins, logActivity } from '../../../lib/server/activity';

const INVALID_CREDENTIALS = 'อีเมลหรือรหัสผ่านไม่ถูกต้อง';
const MAX_FAILED = 5;
const LOCK_MINUTES = 15;

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;

  try {
    const email = normalizeEmail(req.body?.email);
    const password = String(req.body?.password || '');
    const ip = clientIp(req);

    if (!email || !password) {
      return res.status(400).json({ success: false, error: 'กรุณากรอกอีเมลและรหัสผ่านให้ครบถ้วน' });
    }

    // กันการเดารหัสผ่าน: ผิดเกิน 5 ครั้งใน 15 นาที → ล็อกชั่วคราว
    if ((await countRecentFailedLogins(email, LOCK_MINUTES)) >= MAX_FAILED) {
      return res.status(429).json({ success: false, error: `ใส่รหัสผ่านผิดหลายครั้ง กรุณารอ ${LOCK_MINUTES} นาทีแล้วลองใหม่` });
    }

    const supabase = getAdminClient();
    const { data: rows, error } = await supabase.from('bot_config').select('*').eq('mt5_server', email).gt('id', 1).limit(1);

    if (error) {
      console.error('[auth/login] query error:', error.message);
      return res.status(500).json({ success: false, error: 'ระบบฐานข้อมูลขัดข้อง กรุณาลองใหม่' });
    }

    const row = rows?.[0];
    if (!row || !verifyPassword(password, row.mt5_password)) {
      await logActivity({ userId: row?.id, email, event: 'login_failed', detail: row ? 'รหัสผ่านไม่ถูกต้อง' : 'ไม่พบบัญชี', ip });
      return res.status(401).json({ success: false, error: INVALID_CREDENTIALS });
    }
    if (isDisabledRow(row)) {
      await logActivity({ userId: row.id, email, event: 'login_blocked', detail: 'บัญชีถูกระงับ', ip });
      return res.status(403).json({ success: false, error: 'บัญชีนี้ถูกระงับการใช้งาน กรุณาติดต่อผู้ดูแลระบบ' });
    }

    // อัปเกรด hash เก่า (v1 = 10k รอบ) เป็น v2 อัตโนมัติเมื่อล็อกอินสำเร็จ
    if (needsRehash(row.mt5_password)) {
      await supabase.from('bot_config').update({ mt5_password: hashPassword(password) }).eq('id', row.id);
    }

    const user = toUserPayload(row);
    // แจ้งให้แอดมินเปลี่ยนรหัสผ่านที่สั้น/เดาง่าย
    if (user.isAdmin && (password.length < 10 || /^\d+$/.test(password))) user.weakPassword = true;

    await logActivity({ userId: row.id, email, event: 'login', detail: req.headers['user-agent']?.includes('GoldBot24-Desktop') ? 'Desktop' : 'Web', ip });
    return res.status(200).json({ success: true, message: 'เข้าสู่ระบบสำเร็จ!', user, token: signToken(row.id, user.email) });
  } catch (err) {
    console.error('[auth/login] exception:', err);
    return res.status(500).json({ success: false, error: 'เกิดข้อผิดพลาดในการเข้าสู่ระบบ' });
  }
}
