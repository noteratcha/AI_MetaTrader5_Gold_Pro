/** กติการางวัลออนไลน์ (ใช้ทั้งฝั่ง Server และหน้าเว็บ) — โปรแกรมมีค่าเดียวกันใน gui_app (ONLINE_GOAL_HOURS) */
export const ONLINE_GOAL_HOURS = 100;     // ออนไลน์ครบกี่ชั่วโมง (ครบแล้วรับส่วนลดและเริ่มนับรอบใหม่ทันที)
export const ONLINE_DISCOUNT_PCT = 5;     // ส่วนลดเติมชั่วโมงครั้งถัดไป 1 รายการ
export const ONLINE_DISCOUNT_DAYS = 3;    // ใช้ได้ภายใน 3 วันหลังได้รับ (เริ่มนับชั่วโมงใหม่ทันที)

/** ระดับสมาชิก (Lv.) — ชั่วโมงที่บอททำงานสะสมตลอดอายุบัญชี ไม่รีเซ็ต (ผู้ใช้กำหนด 12 ต.ค. 2026)
 *  ทุก 1,000 ชม. = 1 Lv. (เริ่ม Lv.0 · สูงสุด Lv.100) · ทุก 10 Lv. = ส่วนลดถาวร +1% ทุกการซื้อ (Lv.100 = 10%)
 *  บวกกับสิทธิ์ออนไลน์ 100 ชม. ได้ */
export const LEVEL_HOURS = 1000;
export const LEVEL_MAX = 100;
export const LEVEL_TIER = 10;

export function levelInfo(totalMinutes) {
  const hours = Math.max(0, Number(totalMinutes) || 0) / 60;
  const level = Math.min(LEVEL_MAX, Math.floor(hours / LEVEL_HOURS));
  const maxed = level >= LEVEL_MAX;
  const into = maxed ? LEVEL_HOURS : hours - level * LEVEL_HOURS;
  const discountPct = Math.floor(level / LEVEL_TIER);
  const nextTierLevel = maxed ? null : (Math.floor(level / LEVEL_TIER) + 1) * LEVEL_TIER;
  return {
    level,
    maxed,
    totalHours: Math.floor(hours * 10) / 10,
    hoursIntoLevel: Math.floor(into * 10) / 10,
    levelHours: LEVEL_HOURS,
    discountPct,
    nextTierLevel,
    nextTierPct: maxed ? null : discountPct + 1,
  };
}
