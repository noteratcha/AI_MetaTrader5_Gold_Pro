// ระบบชวนเพื่อน (Referral · ผู้ใช้สั่ง 16 ต.ค. 2026): เพื่อนสมัครผ่านลิงก์ของเรา แล้วรันบอทจริงครบ 48 ชม. → เราได้ +48 ชม. ต่อคน
// ใช้ได้ทั้งฝั่งเบราว์เซอร์และ Server
export const REFERRAL_HOURS = 48; // ชั่วโมงที่ผู้แนะนำได้ต่อเพื่อน 1 คน
export const REFERRAL_RUN_HOURS = 48; // เพื่อนต้องรันบอท (ชั่วโมงที่หักจริง) ครบเท่านี้ก่อน
export const REFERRAL_MONTHLY_CAP = 20; // ได้รางวัลสูงสุดกี่คน / 30 วัน
export const REF_STORAGE_KEY = 'gb24_ref'; // รหัสผู้แนะนำที่จำไว้ในเบราว์เซอร์ (จากลิงก์ ?ref=)
export const REF_TTL_DAYS = 30;

/** รหัสแนะนำรูปแบบ GB-XXXXXX (สุ่ม · ไม่เปิดเผย id) → ตัวพิมพ์ใหญ่ หรือ '' ถ้าไม่ถูกรูปแบบ */
export function normalizeRefCode(code) {
  const m = /^GB-?([A-Z2-9]{6})$/i.exec(String(code || '').trim());
  return m ? `GB-${m[1].toUpperCase()}` : '';
}

export function referralLink(code, origin = 'https://goldbot24.vercel.app') {
  return code ? `${origin}/?ref=${code}` : '';
}

/** เบราว์เซอร์: รหัสผู้แนะนำที่ยังไม่หมดอายุ */
export function storedRef() {
  try {
    const v = JSON.parse(localStorage.getItem(REF_STORAGE_KEY) || 'null');
    if (v && v.code && Date.now() - v.at < REF_TTL_DAYS * 86400000) return v.code;
  } catch {
    /* ข้าม */
  }
  return '';
}

/** อีเมลแบบปิดบางส่วน เช่น jo***@gmail.com */
export function maskEmail(email) {
  const [u, d] = String(email || '').split('@');
  if (!d) return '***';
  return `${u.slice(0, 2)}***@${d}`;
}

/** อีเมลรูปแบบเดียว — Gmail ไม่สนจุดและส่วนหลัง + (a.b+1@gmail.com = ab@gmail.com) · ใช้กันแนะนำตัวเอง */
export function canonicalEmail(email) {
  let [u, d] = String(email || '').trim().toLowerCase().split('@');
  if (!d) return String(email || '').toLowerCase();
  u = u.split('+')[0];
  if (d === 'gmail.com' || d === 'googlemail.com') {
    u = u.replace(/\./g, '');
    d = 'gmail.com';
  }
  return `${u}@${d}`;
}

// โดเมนอีเมลชั่วคราวที่พบบ่อย (ไม่นับเป็นเพื่อนที่แนะนำ)
const DISPOSABLE = [
  'mailinator.com', 'guerrillamail.com', 'guerrillamail.net', 'sharklasers.com', '10minutemail.com', 'temp-mail.org', 'tempmail.com',
  'tempmail.net', 'tempmailo.com', 'tempail.com', 'yopmail.com', 'yopmail.net', 'trashmail.com', 'getnada.com', 'nada.email',
  'dispostable.com', 'maildrop.cc', 'mintemail.com', 'throwawaymail.com', 'fakeinbox.com', 'emailondeck.com', 'mohmal.com',
  'moakt.com', 'tmail.ws', 'mail.tm', 'mailpoof.com', 'spamgourmet.com', 'tempinbox.com', 'burnermail.io', 'inboxkitten.com',
  'emailfake.com', 'tmpmail.org', 'tmpmail.net', 'linshiyouxiang.net', '1secmail.com', '1secmail.org', '1secmail.net', 'dropmail.me',
];
export function isDisposableEmail(email) {
  const d = String(email || '').toLowerCase().split('@')[1] || '';
  return DISPOSABLE.some((x) => d === x || d.endsWith(`.${x}`));
}
