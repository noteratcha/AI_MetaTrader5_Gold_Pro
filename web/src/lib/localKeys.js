// สำเนาคีย์ที่ซื้อในเบราว์เซอร์นี้ (สำรองไว้แสดงในหน้า "คีย์ของฉัน" กรณีฐานข้อมูลยังไม่ได้ผูกเจ้าของคำสั่งซื้อ)
const storageKey = (email) => `goldbot_keys:${String(email || '').toLowerCase()}`;

export function readLocalKeys(email) {
  try {
    const list = JSON.parse(localStorage.getItem(storageKey(email)) || '[]');
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

export function rememberLocalKey(email, record) {
  try {
    const list = readLocalKeys(email).filter((k) => k.keyCode !== record.keyCode);
    list.unshift({ ...record, source: 'purchase', status: 'UNUSED', createdAt: new Date().toISOString() });
    localStorage.setItem(storageKey(email), JSON.stringify(list.slice(0, 100)));
  } catch {
    /* storage ใช้ไม่ได้ */
  }
}

export function markLocalKeyRedeemed(email, keyCode) {
  try {
    const list = readLocalKeys(email).map((k) => (k.keyCode === keyCode ? { ...k, status: 'REDEEMED' } : k));
    localStorage.setItem(storageKey(email), JSON.stringify(list));
  } catch {
    /* storage ใช้ไม่ได้ */
  }
}
