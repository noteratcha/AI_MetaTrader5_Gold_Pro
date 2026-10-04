import { allowMethods, requireUser } from '../../../lib/server/auth';
import { fulfillOrder, getOrder, isOrderOwner, ORDER_MAX_AGE_MS } from '../../../lib/server/orders';

const SLIPOK_BRANCH_ID = process.env.SLIPOK_BRANCH_ID || '';
const SLIPOK_API_KEY = process.env.SLIPOK_API_KEY || '';
// โหมดจำลอง (ไม่ตรวจสลิปจริง) ใช้ได้เฉพาะตอนพัฒนาเท่านั้น — ห้ามเปิดบน Production
const ALLOW_MOCK_SLIP = process.env.ALLOW_MOCK_SLIP === 'true' && process.env.VERCEL_ENV !== 'production';

const ALLOWED_MIME = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SLIP_BYTES = 3 * 1024 * 1024;

export const config = {
  api: { bodyParser: { sizeLimit: '4.5mb' } },
};

const SLIPOK_ERRORS = {
  1001: 'ระบบตรวจสลิปยังไม่พร้อม (ยังไม่ได้สร้างสาขาใน SlipOK)',
  1007: 'ไม่พบ QR Code ในรูปสลิป กรุณาใช้รูปสลิปที่ชัดเจน',
  1008: 'รูปนี้ไม่ใช่สลิปการโอนเงิน',
  1012: 'สลิปนี้เคยถูกใช้งานแล้ว',
  1013: 'ยอดเงินในสลิปไม่ตรงกับยอดที่ต้องชำระ',
  1014: 'บัญชีผู้รับเงินในสลิปไม่ตรงกับร้านค้า',
};

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
        const msg = SLIPOK_ERRORS[slipokData.code] || slipokData.message || 'สลิปไม่ผ่านการตรวจสอบ';
        return res.status(400).json({ success: false, error: msg });
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
