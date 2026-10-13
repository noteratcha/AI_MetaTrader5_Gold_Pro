// สมาชิกรายเดือน — ปลดล็อกแผน P6–P8 (ผู้ใช้ทั่วไปใช้ได้ P1–P5) · ยังหักชั่วโมงตามปกติ
// เก็บวันหมดอายุเป็น tag `member_until:<ISO UTC>` ใน bot_config.symbols_trading (ไม่ต้องมีตารางใหม่)
// ราคา/จำนวนวันอ่านจากไฟล์นี้ฝั่ง Server เสมอ (ไม่เชื่อค่าจาก Browser)

// แพ็กเกจสมาชิก (ผู้ใช้กำหนด 13 ต.ค. 2026) — package_id 900–903 (ไม่ชนกับแพ็กเกจชั่วโมงในตาราง packages)
// ราคาเต็ม = 99 บาท / 30 วัน · 360 วันลด 5% · ส่วนลด Lv./ออนไลน์ไม่ใช้กับค่าสมาชิก
const plan = (id, days, label, fullPrice, discountPct = 0, featured = false) => ({
  featured, // แพ็กเกจแนะนำ (เลือกไว้เป็นค่าเริ่มต้น + ไฮไลต์)
  id,
  kind: 'membership',
  name: `สมาชิก ${label}`,
  label,
  days,
  fullPrice,
  discountPct,
  price: Math.round(fullPrice * (100 - discountPct)) / 100,
  hours: 0,
  bonus: 0,
});
export const MEMBERSHIP_PLANS = [
  plan(900, 30, '30 วัน', 99),
  plan(901, 90, '90 วัน', 297),
  plan(902, 180, '180 วัน', 594),
  plan(903, 360, '360 วัน', 1188, 5, true),   // แนะนำ (ผู้ใช้กำหนด 13 ต.ค. 2026)
];
export const MEMBERSHIP = { ...MEMBERSHIP_PLANS[0], name: 'สมาชิกรายเดือน' }; // แพ็กเกจพื้นฐาน (ใช้แสดงชื่อ/ราคาเริ่มต้น)

/** แพ็กเกจสมาชิกจาก package_id (ไม่ใช่สมาชิก = null) */
export function membershipPlan(id) {
  return MEMBERSHIP_PLANS.find((p) => p.id === Number(id)) || null;
}

// แผนที่ต้องเป็นสมาชิก (ชื่อหลักแบบเดียวกับ plan_config.BASE_PLANS ในโปรแกรม)
export const MEMBER_PLANS = ['PSAR-H1-Trend', 'BB-H4-Reversion', 'BB-H4-Free'];
export const MEMBER_PLAN_NUMBERS = [6, 7, 8];
export const MEMBER_TAG = 'member_until:';
export const MEMBER_WARN_DAYS = 3;

export function isMembershipPackage(id) {
  return membershipPlan(id) !== null;
}

/** วันหมดอายุจาก tag (Date หรือ null) */
export function memberUntil(tags) {
  const tag = (Array.isArray(tags) ? tags : []).find((t) => typeof t === 'string' && t.startsWith(MEMBER_TAG));
  if (!tag) return null;
  const d = new Date(tag.slice(MEMBER_TAG.length));
  return Number.isNaN(d.getTime()) ? null : d;
}

// ---- นับตามวันปฏิทิน (เวลาไทย UTC+7 ไม่มี DST) · วันที่ซื้อ = วันที่ 1 · หมดอายุ 23:59:59 น. ของวันสุดท้าย ----
const DAY = 86400000;
const TH_OFFSET = 7 * 3600000;
/** ลำดับวันตามปฏิทินไทยของเวลา ms */
export function thaiDay(ms) {
  return Math.floor((ms + TH_OFFSET) / DAY);
}
/** เวลาสิ้นวัน (23:59:59.999 น. เวลาไทย) ของลำดับวัน */
export function thaiDayEnd(day) {
  return (day + 1) * DAY - TH_OFFSET - 1;
}

/** สถานะสมาชิกจาก tags: { active, until (ISO|null), daysLeft = จำนวนวันปฏิทินที่เหลือ รวมวันนี้ } */
export function memberInfo(tags, now = Date.now()) {
  const until = memberUntil(tags);
  if (!until) return { active: false, until: null, daysLeft: 0 };
  const active = until.getTime() > now;
  return { active, until: until.toISOString(), daysLeft: active ? thaiDay(until.getTime()) - thaiDay(now) + 1 : 0 };
}

/**
 * วันหมดอายุใหม่หลังต่ออายุ `days` วัน (นับตามวันปฏิทินไทย)
 * - ยังไม่หมด: บวกต่อจากวันสุดท้ายเดิม (เช่น ถึง 11 พ.ย. + 30 วัน → ถึง 11 ธ.ค.)
 * - หมดแล้ว/ยังไม่เคยเป็น: วันนี้ = วันที่ 1 → ถึงสิ้นวันที่ (วันนี้ + days − 1)  เช่น ซื้อ 13 ต.ค. → ถึง 11 พ.ย. 23:59 น.
 */
export function extendedUntil(tags, days, now = Date.now()) {
  const cur = memberUntil(tags);
  if (cur && cur.getTime() > now) return new Date(thaiDayEnd(thaiDay(cur.getTime()) + Number(days)));
  return new Date(thaiDayEnd(thaiDay(now) + Number(days) - 1));
}
