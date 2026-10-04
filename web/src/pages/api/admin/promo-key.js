import { insertTolerant } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireAdmin } from '../../../lib/server/auth';
import { generateProductKey } from '../../../lib/server/keys';

const MAX_PROMO_HOURS = 2000;

// ผลิต Promo Key และบันทึกลงฐานข้อมูลจริง (Admin เท่านั้น) — เดิมสุ่มเฉพาะบนหน้าจอ เติมใช้ไม่ได้
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  const hours = Math.floor(Number(req.body?.hours));
  const expiresInDays = Math.floor(Number(req.body?.expiresInDays || 0));
  if (!Number.isFinite(hours) || hours < 1 || hours > MAX_PROMO_HOURS) {
    return res.status(400).json({ success: false, error: `จำนวนชั่วโมงต้องอยู่ระหว่าง 1–${MAX_PROMO_HOURS}` });
  }

  const keyCode = generateProductKey();
  const expiresAt = expiresInDays > 0 ? new Date(Date.now() + expiresInDays * 86400000).toISOString() : null;

  const { error } = await insertTolerant(
    'promo_keys',
    { key_code: keyCode, hours, used: false, expires_at: expiresAt, created_by: auth.user.email },
    ['created_by', 'expires_at']
  );
  if (error) {
    console.error('[admin/promo-key] insert error:', error.message);
    return res.status(500).json({ success: false, error: 'บันทึก Promo Key ไม่สำเร็จ' });
  }

  return res.status(200).json({ success: true, keyCode, hours, expiresAt });
}
