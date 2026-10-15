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
  { key: 'MA-Cross-Trend', label: 'P1 · MA M15', tag: 'M15 · H1 Anchor' },
  { key: 'MA-Cross-H1-Trend', label: 'P2 · MA H1', tag: 'H1 · H4 Anchor' },
  { key: 'SMC-LiquidityHunt', label: 'P3 · SMC Hunt', tag: 'H1 S&R Sweep' },
  { key: 'SR-SwingBounce', label: 'P4 · SR Bounce', tag: 'Divergence' },
  { key: 'BB-H1-Reversion', label: 'P5 · BB-H1', tag: 'BB 2STD + Divergence' },
  { key: 'PSAR-H1-Trend', label: 'P6 · SAR H1', tag: 'Parabolic SAR · H4 Trend' },
  { key: 'BB-H4-Reversion', label: 'P7 · BB-H4', tag: 'BB H4 + Divergence · H4 Trend' },
  { key: 'BB-H4-Free', label: 'P8 · BB-H4 Free', tag: 'BB H4 + Divergence · ไม่กรอง H4' },
  { key: 'Fib-H1-Counter', label: 'P9 · Fib H1', tag: 'Fibonacci 0.3 · สวนเทรนด์ใหญ่ H1' },
  { key: 'RSI-H1-Trend', label: 'P10 · RSI H1', tag: 'RSI 30/70 · ตามเทรนด์ MA200' },
  { key: 'News-USD', label: 'P11 · News', tag: 'ข่าว USD · เข้าทันทีเมื่อค่าจริงยืนยัน' },
  { key: 'DoubleTop-H1', label: 'P12 · BB High Low', tag: 'BB H1 ทำยอดซ้ำ · ตามเทรนด์ H4 · ไม้เพิ่ม ≤ 2' },
];
