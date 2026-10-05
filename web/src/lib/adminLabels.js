// ป้ายภาษาไทยสำหรับเหตุการณ์ใน user_activity
export const ACTIVITY_LABELS = {
  login: { label: 'เข้าสู่ระบบ', badge: 'badge-green' },
  login_failed: { label: 'ล็อกอินผิด', badge: 'badge-red' },
  login_blocked: { label: 'ล็อกอินถูกบล็อก', badge: 'badge-red' },
  account_locked: { label: 'บัญชีถูกล็อก (รหัสผิด)', badge: 'badge-red' },
  account_unlocked: { label: 'แอดมินปลดล็อก', badge: 'badge-green' },
  register: { label: 'สมัครสมาชิก', badge: 'badge-sky' },
  redeem: { label: 'เติมคีย์', badge: 'badge-gold' },
  purchase_paid: { label: 'ชำระเงิน', badge: 'badge-gold' },
  password_changed: { label: 'เปลี่ยนรหัสผ่าน', badge: 'badge-sky' },
  password_reset_requested: { label: 'ขอรีเซ็ตรหัสผ่าน', badge: 'badge-gold' },
  password_reset: { label: 'รีเซ็ตรหัสผ่านสำเร็จ', badge: 'badge-sky' },
  admin_create: { label: 'แอดมินสร้างบัญชี', badge: 'badge-muted' },
  admin_update: { label: 'แอดมินแก้ไข', badge: 'badge-muted' },
  admin_delete: { label: 'แอดมินลบบัญชี', badge: 'badge-red' },
  admin_plans: { label: 'เปิด/ปิดแผน', badge: 'badge-muted' },
  admin_package_create: { label: 'เพิ่มแพ็กเกจ', badge: 'badge-muted' },
  admin_package_update: { label: 'แก้แพ็กเกจ', badge: 'badge-muted' },
  admin_package_delete: { label: 'ลบแพ็กเกจ', badge: 'badge-muted' },
  admin_package_disable: { label: 'ปิดขายแพ็กเกจ', badge: 'badge-muted' },
};

export const TRADE_ACTION_LABELS = {
  OPEN_BUY: { label: 'เปิด BUY', badge: 'badge-green' },
  OPEN_SELL: { label: 'เปิด SELL', badge: 'badge-red' },
  TP_HIT: { label: 'ชน TP', badge: 'badge-green' },
  SL_HIT: { label: 'ชน SL', badge: 'badge-red' },
  CLOSE: { label: 'ปิดไม้', badge: 'badge-gold' },
};

export const PLAN_SHORT = {
  'Plan 1: SMC-LiquidityHunt': 'P1 SMC',
  'Plan 2: SR-SwingBounce': 'P2 Bounce',
  'Plan 3: BB-H1-Reversion': 'P3 BB-H1',
  'Plan 4: MA-Cross-Trend': 'P4 MA M15',
  'Plan 5: MA-Cross-H1-Trend': 'P5 MA H1',
};
