// สมาชิกรายเดือน — ปลดล็อกแผน P6–P8 (ผู้ใช้ทั่วไปใช้ได้ P1–P5) · ยังหักชั่วโมงตามปกติ
// เก็บวันหมดอายุเป็น tag `member_until:<ISO UTC>` ใน bot_config.symbols_trading (ไม่ต้องมีตารางใหม่)
// ราคา/จำนวนวันอ่านจากไฟล์นี้ฝั่ง Server เสมอ (ไม่เชื่อค่าจาก Browser)

export const MEMBERSHIP = {
  id: 900, // package_id ของคำสั่งซื้อสมาชิก (ไม่ชนกับแพ็กเกจชั่วโมงในตาราง packages)
  kind: 'membership',
  name: 'สมาชิกรายเดือน',
  days: 30,
  price: 99,
  hours: 0,
  bonus: 0,
};

// แผนที่ต้องเป็นสมาชิก (ชื่อหลักแบบเดียวกับ plan_config.BASE_PLANS ในโปรแกรม)
export const MEMBER_PLANS = ['PSAR-H1-Trend', 'BB-H4-Reversion', 'BB-H4-Free'];
export const MEMBER_PLAN_NUMBERS = [6, 7, 8];
export const MEMBER_TAG = 'member_until:';
export const MEMBER_WARN_DAYS = 3;

export function isMembershipPackage(id) {
  return Number(id) === MEMBERSHIP.id;
}

/** วันหมดอายุจาก tag (Date หรือ null) */
export function memberUntil(tags) {
  const tag = (Array.isArray(tags) ? tags : []).find((t) => typeof t === 'string' && t.startsWith(MEMBER_TAG));
  if (!tag) return null;
  const d = new Date(tag.slice(MEMBER_TAG.length));
  return Number.isNaN(d.getTime()) ? null : d;
}

/** สถานะสมาชิกจาก tags: { active, until (ISO|null), daysLeft } */
export function memberInfo(tags, now = Date.now()) {
  const until = memberUntil(tags);
  if (!until) return { active: false, until: null, daysLeft: 0 };
  const ms = until.getTime() - now;
  return { active: ms > 0, until: until.toISOString(), daysLeft: ms > 0 ? Math.ceil(ms / 86400000) : 0 };
}

/** วันหมดอายุใหม่หลังต่ออายุ `days` วัน — ยังไม่หมด = ต่อจากวันเดิม · หมดแล้ว = นับจากตอนนี้ */
export function extendedUntil(tags, days, now = Date.now()) {
  const cur = memberUntil(tags);
  const base = cur && cur.getTime() > now ? cur.getTime() : now;
  return new Date(base + days * 86400000);
}
