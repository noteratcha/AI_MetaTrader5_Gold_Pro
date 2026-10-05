// แจ้งเตือนแอดมินผ่าน LINE Official Account (Messaging API · Push Message)
// ตั้งค่าด้วย env:
//   LINE_CHANNEL_ACCESS_TOKEN — Channel access token (long-lived) จาก LINE Developers → Messaging API
//   LINE_ADMIN_TO             — userId (U...) / groupId (C...) ที่จะรับแจ้งเตือน คั่นด้วย , ได้หลายปลายทาง
//   LINE_CHANNEL_SECRET       — (ไม่บังคับ) ใช้ตรวจลายเซ็น Webhook /api/webhook/line สำหรับหา groupId
// ส่งไม่สำเร็จจะไม่ทำให้การสมัคร/ชำระเงินล้ม — แค่บันทึก log

const PUSH_URL = 'https://api.line.me/v2/bot/message/push';
const TIMEOUT_MS = 4000;

function targets() {
  return (process.env.LINE_ADMIN_TO || '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

export function isLineConfigured() {
  return Boolean(process.env.LINE_CHANNEL_ACCESS_TOKEN && targets().length);
}

export function bangkokTime(date = new Date()) {
  return new Date(date).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', dateStyle: 'short', timeStyle: 'short' });
}

async function push(to, text) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(PUSH_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.LINE_CHANNEL_ACCESS_TOKEN}`,
      },
      body: JSON.stringify({ to, messages: [{ type: 'text', text: text.slice(0, 4900) }] }),
      signal: controller.signal,
    });
    if (!res.ok) {
      const body = await res.text().catch(() => '');
      throw new Error(`HTTP ${res.status} ${body.slice(0, 200)}`);
    }
  } finally {
    clearTimeout(timer);
  }
}

/** ส่งข้อความหาแอดมินทุกปลายทาง — คืน { sent, errors } และไม่ throw */
export async function notifyAdmins(text) {
  if (!isLineConfigured()) return { sent: 0, errors: ['LINE ยังไม่ได้ตั้งค่า (LINE_CHANNEL_ACCESS_TOKEN / LINE_ADMIN_TO)'] };
  const results = await Promise.allSettled(targets().map((to) => push(to, text)));
  const errors = results.filter((r) => r.status === 'rejected').map((r) => String(r.reason?.message || r.reason));
  if (errors.length) console.error('[line] push failed:', errors.join(' | '));
  return { sent: results.length - errors.length, errors };
}

export function notifyNewMember({ email, displayName, hours, ip }) {
  return notifyAdmins(
    [
      '🎉 สมาชิกใหม่ GoldBot24',
      `ชื่อ: ${displayName || '-'}`,
      `อีเมล: ${email}`,
      `เวลาฟรี: ${hours} ชม.`,
      ip ? `IP: ${ip}` : null,
      `เวลา: ${bangkokTime()}`,
    ]
      .filter(Boolean)
      .join('\n')
  );
}

export function notifyPurchase({ email, amountThb, hours, orderId, productKey, method }) {
  return notifyAdmins(
    [
      '💰 ซื้อชั่วโมงสำเร็จ',
      `ผู้ซื้อ: ${email || '-'}`,
      `ยอดชำระ: ฿${Number(amountThb).toLocaleString('th-TH')}`,
      `ชั่วโมง: +${hours} ชม.`,
      `คำสั่งซื้อ: ${orderId}`,
      productKey ? `คีย์: ${productKey}` : null,
      method ? `ช่องทาง: ${method}` : null,
      `เวลา: ${bangkokTime()}`,
    ]
      .filter(Boolean)
      .join('\n')
  );
}
