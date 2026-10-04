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

/** จำนวนครั้งที่ล็อกอินผิดของอีเมลนี้ในช่วงเวลาล่าสุด (ใช้ล็อกบัญชีชั่วคราวกันเดารหัส) */
export async function countRecentFailedLogins(email, minutes = 15) {
  try {
    const since = new Date(Date.now() - minutes * 60000).toISOString();
    const { count, error } = await getAdminClient()
      .from('user_activity')
      .select('id', { count: 'exact', head: true })
      .eq('email', String(email).toLowerCase())
      .eq('event', 'login_failed')
      .gte('created_at', since);
    return error ? 0 : count || 0;
  } catch {
    return 0;
  }
}
