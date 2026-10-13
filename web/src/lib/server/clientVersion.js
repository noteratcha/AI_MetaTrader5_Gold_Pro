// บังคับอัปเดตโปรแกรม (13 ต.ค. 2026) — โปรแกรมที่ต่ำกว่า MIN_DESKTOP_VERSION ใช้งานไม่ได้จนกว่าจะอัปเดต
// - โปรแกรมรุ่นใหม่ส่ง header `X-App-Version` · รุ่นเก่าไม่ส่ง (ระบุจาก User-Agent ของโปรแกรม: GoldBot24-Desktop / Python-urllib)
// - เว็บเบราว์เซอร์ไม่ถูกตรวจ
// ตั้งค่าได้ด้วย env MIN_DESKTOP_VERSION บน Vercel (ไม่ต้อง deploy โค้ดใหม่) · ค่าว่าง/"0" = ไม่บังคับ
export const MIN_DESKTOP_VERSION = process.env.MIN_DESKTOP_VERSION ?? '2026.1013.0720';
export const DOWNLOAD_URL = 'https://goldbot24.vercel.app/download';

const nums = (v) => String(v || '').split('.').map((x) => Number(x) || 0);
export function versionLess(a, b) {
  const x = nums(a);
  const y = nums(b);
  for (let i = 0; i < Math.max(x.length, y.length); i++) {
    if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) < (y[i] || 0);
  }
  return false;
}

/** คำขอนี้มาจากโปรแกรม Gold Bot 24 หรือไม่ (รุ่นเก่าส่งล็อกอินด้วย User-Agent ของ Python) */
export function isDesktop(req) {
  const ua = String(req.headers['user-agent'] || '');
  return Boolean(req.headers['x-app-version']) || ua.includes('GoldBot24-Desktop') || ua.startsWith('Python-urllib');
}

/** null = ใช้งานได้ · ไม่งั้นคืน { version, min, legacy } (legacy = รุ่นที่ไม่ส่งเลขเวอร์ชัน) */
export function desktopUpdateRequired(req) {
  if (!MIN_DESKTOP_VERSION || MIN_DESKTOP_VERSION === '0' || !isDesktop(req)) return null;
  const version = String(req.headers['x-app-version'] || '').trim();
  if (!version) return { version: null, min: MIN_DESKTOP_VERSION, legacy: true };
  return versionLess(version, MIN_DESKTOP_VERSION) ? { version, min: MIN_DESKTOP_VERSION, legacy: false } : null;
}

export function updateMessage(min) {
  return `โปรแกรมเวอร์ชันนี้หยุดให้บริการแล้ว — กรุณาอัปเดตเป็นเวอร์ชัน ${min} ขึ้นไป (เมนูผู้ใช้ → ตรวจสอบเวอร์ชันใหม่ → อัปเดต 1-Click หรือดาวน์โหลดที่ ${DOWNLOAD_URL})`;
}

/**
 * ตอบกลับเมื่อโปรแกรมต้องอัปเดต — คืน true ถ้าตอบไปแล้ว (ผู้เรียกต้อง return)
 * - รุ่นเก่ามาก (ไม่ส่งเลขเวอร์ชัน) บน /me /meter → 401 ให้โปรแกรมออกจากระบบ แล้วล็อกอินใหม่จะเห็นข้อความให้อัปเดต
 * - หน้าล็อกอิน / รุ่นที่ส่งเลขเวอร์ชัน → 426 พร้อมข้อความ (รุ่นใหม่เปิดหน้าต่างอัปเดตให้อัตโนมัติ)
 */
export function rejectOutdatedDesktop(req, res, { isLogin = false } = {}) {
  const need = desktopUpdateRequired(req);
  if (!need) return false;
  const body = { success: false, updateRequired: true, minVersion: need.min, downloadUrl: DOWNLOAD_URL, error: updateMessage(need.min) };
  res.status(need.legacy && !isLogin ? 401 : 426).json(body);
  return true;
}
