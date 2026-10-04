// แพ็กเกจชั่วโมง (อัตรา 1 บาท/ชม.) — ใช้ร่วมกันทั้งหน้าร้านและ API
// ราคา/ชั่วโมงที่ใช้คิดเงินจริงอ่านจากไฟล์นี้ฝั่ง Server เสมอ (ไม่เชื่อค่าที่ส่งมาจาก Browser)
export const PACKAGES = [
  {
    id: 1,
    name: 'Starter 50',
    hours: 50,
    bonus: 0,
    price: 50,
    badge: null,
    desc: 'ทดลองรันบอททองคำจริงต่อเนื่อง 2–3 วัน',
    accent: 'sky',
  },
  {
    id: 2,
    name: 'Popular 100',
    hours: 100,
    bonus: 0,
    price: 100,
    badge: 'ขายดี',
    desc: 'รันได้ครบ 1 สัปดาห์ ไม่พลาดรอบสวิง H1',
    accent: 'orange',
    featured: true,
  },
  {
    id: 3,
    name: 'Value 300',
    hours: 300,
    bonus: 20,
    price: 300,
    badge: 'แถม 20 ชม.',
    desc: 'คุ้มขึ้น ได้เวลารวม 320 ชั่วโมง',
    accent: 'emerald',
  },
  {
    id: 4,
    name: 'Marathon 500',
    hours: 500,
    bonus: 50,
    price: 500,
    badge: 'แถม 50 ชม.',
    desc: 'สำหรับรันบน VPS ยาว ๆ ได้เวลารวม 550 ชั่วโมง',
    accent: 'gold',
  },
];

export function findPackage(id) {
  return PACKAGES.find((p) => p.id === Number(id)) || null;
}

export const PLAN_LIST = [
  { key: 'SMC-LiquidityHunt', label: 'Plan 0 · SMC-LiquidityHunt', tag: 'H1 S&R Sweep' },
  { key: 'SR-SwingBounce', label: 'Plan 1 · SR-SwingBounce', tag: 'Divergence' },
  { key: 'BB-H1-Reversion', label: 'Plan 3 · BB-H1-Reversion', tag: 'BB 2STD + MACD' },
  { key: 'MA-Cross-Trend', label: 'Plan 4 · MA-Cross-Trend', tag: 'M15 · H1 Anchor' },
  { key: 'MA-Cross-H1-Trend', label: 'Plan 5 · MA-Cross-H1-Trend', tag: 'H1 · H4 Anchor' },
];
