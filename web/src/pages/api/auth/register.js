import crypto from 'crypto';
import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { logActivity } from '../../../lib/server/activity';
import {
  allowMethods,
  clientIp,
  hashPassword,
  isReservedEmail,
  isValidEmail,
  normalizeEmail,
  signToken,
  toUserPayload,
  isDisabledRow,
} from '../../../lib/server/auth';
import { isMailConfigured, sendAlreadyRegisteredEmail, sendRegisterCodeEmail } from '../../../lib/server/mailer';
import { notifyNewMember } from '../../../lib/server/lineNotify';
import {
  CODE_TTL_MINUTES,
  codeMatches,
  generateCode,
  hashCode,
  MAX_CODE_ATTEMPTS,
  MAX_REQUESTS_PER_EMAIL_HOUR,
  MAX_REQUESTS_PER_IP_HOUR,
  REGISTER_MARKER,
} from '../../../lib/server/passwordReset';

const STARTER_HOURS = 48.0;
// ลิงก์ในอีเมลใช้โดเมนคงที่ (ไม่อ่านจาก Host header กันการปลอมลิงก์)
const SITE_URL = process.env.SITE_URL || 'https://goldbot24.vercel.app';
const GENERIC_SENT = `ส่งรหัสยืนยัน 6 หลักไปที่อีเมลของคุณแล้ว (ใช้ได้ ${CODE_TTL_MINUTES} นาที) — ตรวจกล่องจดหมายขยะด้วย`;
const INVALID_CODE = 'รหัสยืนยันไม่ถูกต้องหรือหมดอายุ กรุณาขอรหัสใหม่';

/**
 * ขั้นที่ 1 (ไม่มี code): ส่งรหัสยืนยัน 6 หลักไปที่อีเมล
 *   - ตอบข้อความเดียวกันเสมอ ไม่ว่าอีเมลจะมีบัญชีอยู่แล้วหรือไม่ (กันสุ่มหาอีเมลสมาชิก)
 *   - ถ้ามีบัญชีอยู่แล้ว ส่งอีเมลแจ้งเจ้าของแทนรหัสยืนยัน
 */
async function sendCode(supabase, { email, displayName, ip }, res) {
  if (!isMailConfigured()) {
    return res.status(503).json({ success: false, error: 'ระบบส่งอีเมลยังไม่พร้อม กรุณาลองใหม่ภายหลัง' });
  }
  const hourAgo = new Date(Date.now() - 3600000).toISOString();
  const [byEmail, byIp] = await Promise.all([
    supabase.from('password_resets').select('id', { count: 'exact', head: true }).eq('email', email).gte('created_at', hourAgo),
    supabase.from('password_resets').select('id', { count: 'exact', head: true }).eq('ip', ip).gte('created_at', hourAgo),
  ]);
  if (byEmail.error) {
    console.error('[auth/register] password_resets missing?', byEmail.error.message);
    return res.status(503).json({ success: false, error: 'ระบบยืนยันอีเมลยังไม่พร้อม (ต้องรัน supabase_password_reset_patch_03.sql)' });
  }
  if ((byEmail.count || 0) >= MAX_REQUESTS_PER_EMAIL_HOUR || (byIp.count || 0) >= MAX_REQUESTS_PER_IP_HOUR) {
    return res.status(429).json({ success: false, error: 'ขอรหัสบ่อยเกินไป กรุณารอ 1 ชั่วโมงแล้วลองใหม่' });
  }

  const { data: rows, error: checkErr } = await supabase.from('bot_config').select('*').eq('mt5_server', email).limit(1);
  if (checkErr) return res.status(500).json({ success: false, error: 'ระบบฐานข้อมูลขัดข้อง กรุณาลองใหม่' });
  const existing = rows?.[0];
  const now = new Date().toISOString();

  if (existing) {
    // บันทึกไว้นับ rate limit (ไม่มีรหัสให้ใช้) แล้วแจ้งเจ้าของอีเมลแทน
    await supabase.from('password_resets').insert({ user_id: REGISTER_MARKER, email, code_hash: 'none', expires_at: now, used_at: now, ip });
    if (!isDisabledRow(existing)) {
      try {
        await sendAlreadyRegisteredEmail(email, toUserPayload(existing).displayName, SITE_URL);
      } catch (err) {
        console.error('[auth/register] notice mail failed:', err.message);
      }
    }
    return res.status(200).json({ success: true, step: 'verify', message: GENERIC_SENT });
  }

  await supabase.from('password_resets').update({ used_at: now }).eq('email', email).eq('user_id', REGISTER_MARKER).is('used_at', null);
  const code = generateCode();
  const { error: insErr } = await supabase.from('password_resets').insert({
    user_id: REGISTER_MARKER,
    email,
    code_hash: hashCode(email, code),
    expires_at: new Date(Date.now() + CODE_TTL_MINUTES * 60000).toISOString(),
    ip,
  });
  if (insErr) return res.status(500).json({ success: false, error: 'สร้างรหัสยืนยันไม่สำเร็จ กรุณาลองใหม่' });

  try {
    await sendRegisterCodeEmail(email, code, displayName);
  } catch (err) {
    console.error('[auth/register] send mail failed:', err.message);
    return res.status(502).json({ success: false, error: 'ส่งอีเมลไม่สำเร็จ กรุณาตรวจสอบอีเมลแล้วลองใหม่' });
  }
  return res.status(200).json({ success: true, step: 'verify', message: GENERIC_SENT });
}

/** ขั้นที่ 2: ตรวจรหัสยืนยัน (ใช้ได้ครั้งเดียว, ผิดได้ 5 ครั้ง) — คืน null ถ้าผ่าน หรือข้อความ error */
async function consumeCode(supabase, email, code) {
  const { data: rows } = await supabase
    .from('password_resets')
    .select('*')
    .eq('email', email)
    .eq('user_id', REGISTER_MARKER)
    .is('used_at', null)
    .gt('expires_at', new Date().toISOString())
    .order('created_at', { ascending: false })
    .limit(1);
  const row = rows?.[0];
  if (!row || row.attempts >= MAX_CODE_ATTEMPTS) return INVALID_CODE;

  if (!codeMatches(email, code, row.code_hash)) {
    const attempts = (row.attempts || 0) + 1;
    await supabase
      .from('password_resets')
      .update({ attempts, ...(attempts >= MAX_CODE_ATTEMPTS ? { used_at: new Date().toISOString() } : {}) })
      .eq('id', row.id);
    const left = MAX_CODE_ATTEMPTS - attempts;
    return left > 0 ? `รหัสยืนยันไม่ถูกต้อง (เหลืออีก ${left} ครั้ง)` : INVALID_CODE;
  }

  const { data: claimed } = await supabase.from('password_resets').update({ used_at: new Date().toISOString() }).eq('id', row.id).is('used_at', null).select('id');
  return claimed?.length ? null : INVALID_CODE;
}

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
    if (isReservedEmail(email)) {
      return res.status(403).json({ success: false, error: 'อีเมลนี้สงวนไว้สำหรับผู้ดูแลระบบ' });
    }

    const supabase = getAdminClient();
    const ip = clientIp(req);
    const code = String(req.body?.code || '').replace(/\D/g, '');
    if (!code) return await sendCode(supabase, { email, displayName, ip }, res);
    if (code.length !== 6) return res.status(400).json({ success: false, error: 'กรุณากรอกรหัสยืนยัน 6 หลัก' });

    const codeError = await consumeCode(supabase, email, code);
    if (codeError) return res.status(400).json({ success: false, error: codeError });

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
    await logActivity({ userId: created.id, email, event: 'register', detail: `สมัครสมาชิก (ยืนยันอีเมลแล้ว) รับฟรี ${STARTER_HOURS} ชม.`, ip });
    await notifyNewMember({ email, displayName: user.displayName, hours: STARTER_HOURS, ip });
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
