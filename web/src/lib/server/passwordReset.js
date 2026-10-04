import crypto from 'crypto';

export const CODE_TTL_MINUTES = 15;
export const MAX_CODE_ATTEMPTS = 5;
export const MAX_REQUESTS_PER_EMAIL_HOUR = 3;
export const MAX_REQUESTS_PER_IP_HOUR = 10;
// แถวรหัสยืนยันการสมัครใช้ตาราง password_resets ร่วมกัน โดยใส่ user_id เป็นค่านี้
export const REGISTER_MARKER = 'register';

function secret() {
  return process.env.AUTH_SECRET || process.env.SUPABASE_SERVICE_ROLE_KEY || 'goldbot24-dev-only-secret-change-me';
}

export function generateCode() {
  return String(crypto.randomInt(0, 1000000)).padStart(6, '0');
}

/** เก็บเฉพาะ HMAC ของรหัส (ผูกกับอีเมล) — รหัสจริงอยู่ในอีเมลผู้ใช้เท่านั้น */
export function hashCode(email, code) {
  return crypto.createHmac('sha256', secret()).update(`${String(email).toLowerCase()}:${code}`).digest('hex');
}

export function codeMatches(email, code, storedHash) {
  const a = Buffer.from(hashCode(email, code));
  const b = Buffer.from(String(storedHash || ''));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
