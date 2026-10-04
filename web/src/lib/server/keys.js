import crypto from 'crypto';

// ไม่มี 0/O/1/I เพื่อกันพิมพ์ผิด
const KEY_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

/** สร้าง Product Key 24 หลัก (XXXX-XXXX-XXXX-XXXX-XXXX-XXXX) ด้วย CSPRNG */
export function generateProductKey() {
  const groups = [];
  for (let g = 0; g < 6; g++) {
    let group = '';
    for (let i = 0; i < 4; i++) group += KEY_ALPHABET[crypto.randomInt(KEY_ALPHABET.length)];
    groups.push(group);
  }
  return groups.join('-');
}

export function normalizeKey(raw) {
  const clean = String(raw || '').replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 24);
  const chunks = [];
  for (let i = 0; i < clean.length; i += 4) chunks.push(clean.slice(i, i + 4));
  return chunks.join('-');
}

export function isValidKeyFormat(key) {
  return /^[A-Z0-9]{4}(-[A-Z0-9]{4}){5}$/.test(key);
}

/** Order ID เดาไม่ได้ (เดิมเป็นเลขสุ่ม 6 หลัก ซึ่งไล่เดาเพื่อขโมยคีย์ได้) */
export function generateOrderId() {
  return `ORD-${crypto.randomBytes(9).toString('base64url').toUpperCase()}`;
}
