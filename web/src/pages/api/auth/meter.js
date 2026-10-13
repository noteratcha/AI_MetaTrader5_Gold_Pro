import { rejectOutdatedDesktop } from '../../../lib/server/clientVersion';
import { adjustHoursDetailed, allowMethods, requireUser } from '../../../lib/server/auth';
import { isMailConfigured, sendLowHoursEmail } from '../../../lib/server/mailer';
import { LOW_HOURS } from '../../../lib/hours';
import { addOnlineMinutes, getRewardStatus } from '../../../lib/server/onlineReward';

// หักเวลาการใช้งานบอท (เรียกจาก Desktop App ทุก ~5 นาที พร้อมจำนวนนาทีที่ใช้ไป)
const MAX_MINUTES_PER_CALL = 24 * 60;

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  if (rejectOutdatedDesktop(req, res)) return;   // บังคับอัปเดตโปรแกรม (ไม่หักชั่วโมงให้รุ่นเก่า)
  const auth = await requireUser(req, res);
  if (!auth) return;

  const minutes = Math.floor(Number(req.body?.minutes));
  if (!Number.isFinite(minutes) || minutes <= 0 || minutes > MAX_MINUTES_PER_CALL) {
    return res.status(400).json({ success: false, error: 'จำนวนนาทีไม่ถูกต้อง' });
  }

  try {
    const { before, after: hoursRemaining } = await adjustHoursDetailed(auth.row.id, -(minutes / 60));
    // นับรางวัล/ระดับเฉพาะนาทีที่หักได้จริง (ชั่วโมงหมดแล้ว = ไม่ได้นาทีสะสม — กันส่งนาทีปลอมเพื่อปั๊ม Lv./ส่วนลด)
    const credited = Math.max(0, Math.min(minutes, Math.round((before - hoursRemaining) * 60)));
    // เวลาลดลงข้ามเกณฑ์ใกล้หมดในการหักครั้งนี้ → อีเมลเตือนครั้งเดียว (เติมชั่วโมงแล้วลดลงมาใหม่จะเตือนอีกครั้ง)
    if (before > LOW_HOURS && hoursRemaining <= LOW_HOURS && hoursRemaining > 0 && isMailConfigured()) {
      try {
        await sendLowHoursEmail(auth.user.email, auth.user.displayName, hoursRemaining);
      } catch (mailErr) {
        console.error('[auth/meter] low-hours email failed:', mailErr?.message || mailErr);
      }
    }
    // สะสมชั่วโมงออนไลน์รายสัปดาห์ (ครบ 100 ชม. ได้ส่วนลด 5%) — นับเฉพาะนาทีที่หักจริง
    // เลขบัญชี MT5 ที่บอทใช้อยู่ (โปรแกรมส่งมา) — ใช้แยกชั่วโมงสะสมตามบัญชี
    const login = Math.floor(Number(req.body?.login) || 0);
    if (credited > 0) await addOnlineMinutes(auth.user, credited, login > 0 && login < 1e12 ? login : 0);
    const online = await getRewardStatus(auth.user.id);
    return res.status(200).json({ success: true, minutesDeducted: credited, hoursRemaining, online });
  } catch (err) {
    console.error('[auth/meter] error:', err);
    return res.status(500).json({ success: false, error: err.message || 'ไม่สามารถหักเวลาได้' });
  }
}
