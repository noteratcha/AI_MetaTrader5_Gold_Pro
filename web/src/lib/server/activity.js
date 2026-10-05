import { getAdminClient } from './supabaseAdmin';

/**
 * บันทึกกิจกรรมผู้ใช้ลงตาราง user_activity (ไม่ทำให้ request หลักล้มถ้าตารางยังไม่ถูกสร้าง)
 * event ตัวอย่าง: login, login_failed, register, redeem, purchase_paid, admin_update, admin_create, admin_delete
 */
export async function logActivity({ userId = null, email = null, event, detail = '', actor = null, ip = null }) {
  try {
    await getAdminClient()
      .from('user_activity')
      .insert({
        user_id: userId ? String(userId) : null,
        email: email ? String(email).toLowerCase() : null,
        event,
        detail: String(detail || '').slice(0, 1000),
        actor,
        ip: ip ? String(ip).slice(0, 64) : null,
      });
  } catch {
    /* ตาราง user_activity ยังไม่ถูกสร้าง — ข้าม */
  }
}

// ล็อกบัญชีชั่วคราวเมื่อใส่รหัสผิดครบ LOGIN_MAX_FAILED ครั้งภายใน LOGIN_LOCK_MINUTES นาที
// แอดมินปลดล็อกได้ → บันทึก event 'account_unlocked' และนับรหัสผิดเฉพาะหลังเวลาปลดล็อก
export const LOGIN_MAX_FAILED = 5;
export const LOGIN_LOCK_MINUTES = 15;

/**
 * สถานะล็อกของหลายอีเมลพร้อมกัน → { [email]: { locked, failed, unlockAt } }
 * unlockAt = เวลาที่จะปลดล็อกเองอัตโนมัติ (เมื่อรหัสผิดเก่าสุดใน 5 ครั้งล่าสุดหลุดหน้าต่าง 15 นาที)
 */
export async function getLoginLockStatus(emails) {
  const list = [...new Set((emails || []).map((e) => String(e || '').toLowerCase()).filter(Boolean))];
  const result = Object.fromEntries(list.map((e) => [e, { locked: false, failed: 0, unlockAt: null }]));
  if (!list.length) return result;
  try {
    const windowMs = LOGIN_LOCK_MINUTES * 60000;
    const since = new Date(Date.now() - windowMs).toISOString();
    const { data, error } = await getAdminClient()
      .from('user_activity')
      .select('email, event, created_at')
      .in('email', list)
      .in('event', ['login_failed', 'account_unlocked'])
      .gte('created_at', since)
      .order('created_at', { ascending: true })
      .limit(5000);
    if (error) return result;
    const failsBy = {};
    for (const r of data || []) {
      if (r.event === 'account_unlocked') failsBy[r.email] = [];
      else (failsBy[r.email] ||= []).push(new Date(r.created_at).getTime());
    }
    for (const [email, fails] of Object.entries(failsBy)) {
      if (!result[email]) continue;
      const locked = fails.length >= LOGIN_MAX_FAILED;
      result[email] = {
        locked,
        failed: fails.length,
        unlockAt: locked ? new Date(fails[fails.length - LOGIN_MAX_FAILED] + windowMs).toISOString() : null,
      };
    }
  } catch {
    /* ตาราง user_activity ยังไม่ถูกสร้าง */
  }
  return result;
}

/** จำนวนครั้งที่ล็อกอินผิดของอีเมลนี้ในช่วงเวลาล่าสุด (นับเฉพาะหลังแอดมินปลดล็อกครั้งล่าสุด) */
export async function countRecentFailedLogins(email) {
  const key = String(email || '').toLowerCase();
  return (await getLoginLockStatus([key]))[key]?.failed || 0;
}
