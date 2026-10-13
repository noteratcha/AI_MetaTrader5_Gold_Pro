// ชื่อแผนแบบเดียวกับโปรแกรม Gold Bot 24 (P1 · MA M15 …) — แปลงจากชื่อเต็ม/คอมเมนต์ใน MT5 ทุกรูปแบบ
export const PLAN_NAMES = {
  1: 'P1 · MA M15',
  2: 'P2 · MA H1',
  3: 'P3 · SMC Hunt',
  4: 'P4 · SR Bounce',
  5: 'P5 · BB-H1',
  6: 'P6 · SAR H1',
  7: 'P7 · BB-H4',
  8: 'P8 · BB-H4 Free',
};

/** เลขแผนจากชื่อใด ๆ เช่น "MA-Cross-Trend", "Plan 3: SMC-LiquidityHunt", "BB-H1-Reversion+Div" — ไม่รู้จักคืน 0 */
export function planNumber(raw) {
  const p = String(raw || '').toLowerCase();
  if (p.includes('psar') || p.includes('sar h1')) return 6;
  if (p.includes('bb-h4-free') || p.includes('bb-h4 free')) return 8; // ต้องเช็คก่อน bb-h4 (P7)
  if (p.includes('bb-h4')) return 7;
  if (p.includes('ma-cross-h1') || p.includes('ma h1')) return 2;
  if (p.includes('ma-cross') || p.includes('ma m15')) return 1;
  if (p.includes('smc') || p.includes('liquidity')) return 3;
  if (p.includes('bounce') || p.includes('sr-swing')) return 4;
  if (p.includes('bb-h1') || p.includes('bollinger')) return 5;
  return 0;
}

/** ชื่อแผนสำหรับแสดงผล — ข้อความที่ไม่ใช่ชื่อแผน (เช่น "SL Hit", "Manual") คืนค่าเดิม */
export function planDisplay(raw) {
  const n = planNumber(raw);
  return n ? PLAN_NAMES[n] : raw || '—';
}
