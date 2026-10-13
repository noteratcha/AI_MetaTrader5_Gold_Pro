import { getAdminClient } from './supabaseAdmin';
import { rowTags } from './auth';
import { logActivity } from './activity';
import { MEMBERSHIP, MEMBER_TAG, extendedUntil, memberInfo } from '../membership';

/**
 * orders.package_id มี Foreign Key ไปตาราง packages → ต้องมีแถว id 900 ก่อนสร้างคำสั่งซื้อสมาชิก
 * สร้างให้อัตโนมัติ (is_active = false → ไม่โผล่ในหน้าร้าน/หน้าจัดการแพ็กเกจ) · มีอยู่แล้วไม่แตะ
 */
export async function ensureMembershipPackageRow() {
  const { error } = await getAdminClient()
    .from('packages')
    .upsert(
      {
        id: MEMBERSHIP.id,
        name: `${MEMBERSHIP.name} (ระบบ)`,
        hours: 0,
        bonus_hours: 0,
        price_thb: MEMBERSHIP.price,
        description: 'แถวระบบสำหรับคำสั่งซื้อสมาชิกรายเดือน — ราคาจริงอ่านจากโค้ด (lib/membership.js)',
        sort_order: 999,
        is_active: false,
      },
      { onConflict: 'id', ignoreDuplicates: true }
    );
  if (error) console.error('[membership] ensure package row failed:', error.message);
  return !error;
}

/**
 * ต่ออายุสมาชิก `days` วัน (ลบได้ = ลดวัน) หรือยกเลิก (days = null) ให้ผู้ใช้ — คืน memberInfo ใหม่ หรือ null ถ้าไม่สำเร็จ
 * อ่าน tag ล่าสุดก่อนเขียนเสมอ (กันทับการต่ออายุที่เกิดพร้อมกัน เช่น จ่าย 2 รายการติดกัน)
 */
export async function extendMembership(userId, days, { actor = null, reason = '' } = {}) {
  const supabase = getAdminClient();
  const id = Number(userId);
  if (!Number.isInteger(id) || id <= 1) return null;
  const { data: row } = await supabase.from('bot_config').select('id, mt5_server, symbols_trading').eq('id', id).maybeSingle();
  if (!row) return null;

  const tags = rowTags(row);
  const rest = tags.filter((t) => !t.startsWith(MEMBER_TAG));
  let next = rest;
  let detail;
  if (days === null) {
    detail = 'ยกเลิกสมาชิกรายเดือน';
  } else {
    const until = extendedUntil(tags, Number(days));
    next = until.getTime() > Date.now() ? [...rest, `${MEMBER_TAG}${until.toISOString()}`] : rest;
    detail = `สมาชิกรายเดือน ${days > 0 ? '+' : ''}${days} วัน → ${until.getTime() > Date.now() ? `ถึง ${until.toISOString().slice(0, 10)}` : 'หมดอายุ'}`;
  }
  const { error } = await supabase
    .from('bot_config')
    .update({ symbols_trading: next, updated_at: new Date().toISOString() })
    .eq('id', id);
  if (error) {
    console.error('[membership] update failed:', error.message);
    return null;
  }
  await logActivity({ userId: id, email: row.mt5_server, event: 'membership', detail: reason ? `${detail} · ${reason}` : detail, actor });
  return memberInfo(next);
}
