import { getAdminClient } from './supabaseAdmin';
import { PACKAGES as DEFAULT_PACKAGES, PLAN_LIST } from '../packages';

// =============================================================================
// แพ็กเกจชั่วโมง + ตั้งค่าระบบ (อ่านจากฐานข้อมูล, fallback ค่าเริ่มต้นในโค้ดถ้าตารางยังไม่ถูกสร้าง)
// =============================================================================

export function rowToPackage(r) {
  return {
    id: r.id,
    name: r.name,
    hours: Number(r.hours) || 0,
    bonus: Number(r.bonus_hours) || 0,
    price: Number(r.price_thb) || 0,
    badge: r.badge || null,
    desc: r.description || '',
    accent: r.accent || 'gold',
    featured: Boolean(r.featured),
    sortOrder: Number(r.sort_order) || 0,
    isActive: r.is_active !== false,
  };
}

export function packageToRow(p) {
  return {
    name: String(p.name || '').trim().slice(0, 60),
    hours: Number(p.hours),
    bonus_hours: Number(p.bonus) || 0,
    price_thb: Number(p.price),
    badge: p.badge ? String(p.badge).slice(0, 30) : null,
    description: p.desc ? String(p.desc).slice(0, 200) : null,
    accent: ['sky', 'orange', 'emerald', 'gold'].includes(p.accent) ? p.accent : 'gold',
    featured: Boolean(p.featured),
    sort_order: Number.isFinite(Number(p.sortOrder)) ? Number(p.sortOrder) : 1,
    is_active: p.isActive !== false,
    updated_at: new Date().toISOString(),
  };
}

export function validatePackage(p) {
  if (!String(p.name || '').trim()) return 'กรุณาตั้งชื่อแพ็กเกจ';
  if (!(Number(p.hours) > 0) || Number(p.hours) > 10000) return 'จำนวนชั่วโมงต้องอยู่ระหว่าง 1–10,000';
  if (Number(p.bonus) < 0 || Number(p.bonus) > 10000) return 'ชั่วโมงโบนัสไม่ถูกต้อง';
  if (!(Number(p.price) >= 20) || Number(p.price) > 150000) return 'ราคาต้องอยู่ระหว่าง ฿20–150,000 (ขั้นต่ำของ PromptPay Gateway)';
  return null;
}

/** รายการแพ็กเกจ (ค่าเริ่มต้น: เฉพาะที่เปิดขาย เรียงตาม sort_order) */
export async function listPackages({ includeInactive = false } = {}) {
  try {
    let q = getAdminClient().from('packages').select('*').order('sort_order', { ascending: true }).order('id', { ascending: true });
    if (!includeInactive) q = q.eq('is_active', true);
    const { data, error } = await q;
    if (error) throw error;
    return { packages: (data || []).map(rowToPackage), source: 'db' };
  } catch {
    return { packages: DEFAULT_PACKAGES.map((p) => ({ ...p, isActive: true, sortOrder: p.id })), source: 'default' };
  }
}

export async function getPackage(id) {
  const { packages } = await listPackages({ includeInactive: false });
  return packages.find((p) => Number(p.id) === Number(id)) || null;
}

// ---------------------------------------------------------------------------
// แผนเทรด (เปิด/ปิดทั้งระบบ)
// ---------------------------------------------------------------------------
export const PLAN_KEYS = PLAN_LIST.map((p) => p.key);

export async function getEnabledPlans() {
  const defaults = Object.fromEntries(PLAN_KEYS.map((k) => [k, true]));
  try {
    const { data } = await getAdminClient().from('app_settings').select('value, updated_at, updated_by').eq('key', 'enabled_plans').maybeSingle();
    const value = data?.value && typeof data.value === 'object' ? data.value : {};
    const plans = Object.fromEntries(PLAN_KEYS.map((k) => [k, value[k] !== false]));
    return { plans, updatedAt: data?.updated_at || null, updatedBy: data?.updated_by || null };
  } catch {
    return { plans: defaults, updatedAt: null, updatedBy: null };
  }
}

export async function setEnabledPlans(plans, actorEmail) {
  const value = Object.fromEntries(PLAN_KEYS.map((k) => [k, plans[k] !== false]));
  const { error } = await getAdminClient()
    .from('app_settings')
    .upsert({ key: 'enabled_plans', value, updated_by: actorEmail, updated_at: new Date().toISOString() });
  if (error) throw new Error(error.message);
  return value;
}
