import { allowMethods, requireUser } from '../../../lib/server/auth';
import { fulfillOrder, getOrder, isOrderOwner, ORDER_MAX_AGE_MS } from '../../../lib/server/orders';
import { notifyAdmins } from '../../../lib/server/lineNotify';

const SLIPOK_BRANCH_ID = process.env.SLIPOK_BRANCH_ID || '';
const SLIPOK_API_KEY = process.env.SLIPOK_API_KEY || '';
// โหมดจำลอง (ไม่ตรวจสลิปจริง) ใช้ได้เฉพาะตอนพัฒนาเท่านั้น — ห้ามเปิดบน Production
const ALLOW_MOCK_SLIP = process.env.ALLOW_MOCK_SLIP === 'true' && process.env.VERCEL_ENV !== 'production';

const ALLOWED_MIME = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SLIP_BYTES = 3 * 1024 * 1024;

export const config = {
  api: { bodyParser: { sizeLimit: '4.5mb' } },
};

// รหัสผิดพลาดของ SlipOK → ข้อความ + คำแนะนำสำหรับลูกค้า (อ้างอิง SlipOK API Guide)
const SLIPOK_ERRORS = {
  1005: { error: 'ไฟล์นี้ไม่ใช่รูปภาพ', hint: 'แนบรูปสลิป .jpg .png หรือ .webp' },
  1006: { error: 'รูปภาพไม่ถูกต้อง', hint: 'ลองแคปหน้าจอสลิปใหม่ให้เห็นทั้งใบแล้วแนบอีกครั้ง' },
  1007: { error: 'ไม่พบ QR Code ในรูปสลิป', hint: 'ใช้สลิปจากแอปธนาคารที่เห็น QR Code มุมสลิปชัดเจน ไม่ครอปหรือเบลอ' },
  1008: { error: 'QR ในรูปไม่ใช่ QR ของสลิปโอนเงิน', hint: 'แนบสลิปการโอนเงิน ไม่ใช่รูป QR สำหรับจ่ายเงิน' },
  1009: { error: 'ระบบธนาคารขัดข้องชั่วคราว', hint: 'กรุณาแนบสลิปเดิมอีกครั้งใน 15 นาที (เงินที่โอนแล้วไม่หาย)' },
  1011: { error: 'QR ในสลิปหมดอายุ หรือไม่พบรายการโอน', hint: 'ตรวจว่าโอนสำเร็จแล้ว และใช้สลิปล่าสุดจากแอปธนาคาร' },
  1012: { error: 'สลิปนี้เคยถูกใช้งานแล้ว', hint: 'สลิป 1 ใบใช้ได้ครั้งเดียว ถ้ายังไม่ได้รับชั่วโมงกรุณาติดต่อแอดมิน' },
  1013: { error: 'ยอดเงินในสลิปไม่ตรงกับยอดที่ต้องชำระ', hint: null },
  1014: { error: 'บัญชีผู้รับเงินในสลิปไม่ตรงกับร้านค้า', hint: 'โปรดโอนผ่าน QR ในหน้านี้เท่านั้น' },
};
// ปัญหาฝั่งร้านค้า (ตั้งค่า/แพ็กเกจ SlipOK) — แจ้งแอดมินทาง LINE ไม่เกินชั่วโมงละครั้งต่อ instance
const MERCHANT_SIDE_CODES = new Set([1000, 1001, 1002, 1003, 1004, 1015]);
let lastMerchantAlert = 0;

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  const order = await getOrder(String(req.body?.order_id || ''));
  if (!order || !isOrderOwner(order, auth.user)) {
    return res.status(404).json({ success: false, error: 'ไม่พบคำสั่งซื้อ' });
  }
  if (order.status === 'PAID') {
    return res.status(200).json({ success: true, product_key: order.generated_key_code, message: 'คำสั่งซื้อนี้ชำระเงินแล้ว' });
  }
  if (order.created_at && Date.now() - new Date(order.created_at).getTime() > ORDER_MAX_AGE_MS) {
    return res.status(410).json({ success: false, error: 'คำสั่งซื้อนี้หมดอายุแล้ว กรุณาสร้างคำสั่งซื้อใหม่' });
  }

  const mime = String(req.body?.mime || '');
  const base64 = String(req.body?.slip_base64 || '').replace(/^data:[^;]+;base64,/, '');
  const slipBuffer = Buffer.from(base64, 'base64');
  if (!ALLOWED_MIME.includes(mime) || slipBuffer.length === 0) {
    return res.status(400).json({ success: false, error: 'กรุณาแนบรูปสลิปเป็นไฟล์ JPG, PNG หรือ WEBP' });
  }
  if (slipBuffer.length > MAX_SLIP_BYTES) {
    return res.status(413).json({ success: false, error: 'ไฟล์สลิปใหญ่เกินไป (สูงสุด 3MB)' });
  }

  let paymentRef = null;

  if (SLIPOK_BRANCH_ID && SLIPOK_API_KEY) {
    try {
      const form = new FormData();
      form.append('files', new Blob([slipBuffer], { type: mime }), 'slip');
      form.append('amount', String(Number(order.amount_thb)));
      form.append('log', 'true'); // ให้ SlipOK จดจำสลิป — กันใช้สลิปเดิมซ้ำ (code 1012)

      const slipokRes = await fetch(`https://api.slipok.com/api/line/apikey/${SLIPOK_BRANCH_ID}`, {
        method: 'POST',
        headers: { 'x-authorization': SLIPOK_API_KEY },
        body: form,
      });
      const slipokData = await slipokRes.json().catch(() => ({}));

      if (!slipokData.success || !slipokData.data) {
        const code = Number(slipokData.code) || 0;
        // สลิป SCB/BBL บางรายการ ธนาคารให้รอหลังโอนก่อนตรวจได้ → ให้หน้าเว็บนับถอยหลังแล้วตรวจซ้ำอัตโนมัติ
        if (code === 1010) {
          const delayMin = Math.max(1, Number(slipokData.data?.delay ?? slipokData.delay) || 5);
          const bank = slipokData.data?.bankName || slipokData.bankName || 'ธนาคารนี้';
          return res.status(425).json({
            success: false,
            code,
            error: `สลิปจาก${bank} ต้องรอประมาณ ${delayMin} นาทีหลังโอนก่อนตรวจได้`,
            retryAfterSec: delayMin * 60,
          });
        }
        if (MERCHANT_SIDE_CODES.has(code)) {
          console.error('[checkout/verify-slip] SlipOK merchant error:', code, slipokData.message);
          if (Date.now() - lastMerchantAlert > 3600000) {
            lastMerchantAlert = Date.now();
            await notifyAdmins(`⚠️ ระบบตรวจสลิป SlipOK ขัดข้อง\nรหัส ${code}: ${slipokData.message || '-'}\nลูกค้าซื้อชั่วโมงไม่ได้ — ตรวจแพ็กเกจ/โควตา SlipOK`);
          }
          return res.status(503).json({
            success: false,
            code,
            error: 'ระบบตรวจสลิปขัดข้องชั่วคราว',
            hint: 'แจ้งแอดมินแล้ว กรุณาเก็บสลิปไว้แล้วลองใหม่ภายหลัง (เงินที่โอนแล้วไม่หาย)',
          });
        }
        const known = SLIPOK_ERRORS[code];
        const hint = code === 1013 ? `ต้องโอน ฿${Number(order.amount_thb).toLocaleString('th-TH', { minimumFractionDigits: 2 })} พอดี ถ้าโอนผิดยอดกรุณาติดต่อแอดมิน` : known?.hint;
        return res.status(400).json({ success: false, code, error: known?.error || slipokData.message || 'สลิปไม่ผ่านการตรวจสอบ', hint });
      }
      paymentRef = slipokData.data.transRef || `SLIPOK-${Date.now()}`;
    } catch (err) {
      console.error('[checkout/verify-slip] SlipOK error:', err);
      return res.status(502).json({ success: false, error: 'เชื่อมต่อระบบตรวจสลิปไม่สำเร็จ กรุณาลองใหม่' });
    }
  } else if (ALLOW_MOCK_SLIP) {
    paymentRef = `MOCK-${Date.now()}`;
  } else {
    return res.status(503).json({ success: false, error: 'ระบบตรวจสลิปอัตโนมัติยังไม่เปิดใช้งาน กรุณาติดต่อแอดมิน' });
  }

  const result = await fulfillOrder(order, paymentRef);
  if (!result.ok) {
    return res.status(409).json({ success: false, error: result.error });
  }

  return res.status(200).json({
    success: true,
    order_id: order.order_id,
    product_key: result.productKey,
    hours: Number(order.hours_to_add),
    message: 'ตรวจสลิปสำเร็จ! ออกรหัส Product Key เรียบร้อยแล้ว',
  });
}
