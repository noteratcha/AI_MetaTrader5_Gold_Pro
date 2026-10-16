import { allowMethods, requireUser } from '../../../lib/server/auth';
import { ensureReferralCode, referralSummary } from '../../../lib/server/referral';
import { REFERRAL_HOURS, REFERRAL_MONTHLY_CAP, REFERRAL_RUN_HOURS } from '../../../lib/referral';

// ชวนเพื่อนของฉัน: รหัส/ลิงก์แนะนำ (สุ่ม สร้างครั้งแรก) + เพื่อนที่สมัคร (สถานะ/ความคืบหน้าการรันบอท) + ชั่วโมงที่ได้
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;
  try {
    const code = await ensureReferralCode(auth.row);
    const s = await referralSummary(auth.user.id);
    return res.status(200).json({ success: true, code, rewardHours: REFERRAL_HOURS, runHours: REFERRAL_RUN_HOURS, monthlyCap: REFERRAL_MONTHLY_CAP, ...s });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message || 'โหลดข้อมูลชวนเพื่อนไม่สำเร็จ' });
  }
}
