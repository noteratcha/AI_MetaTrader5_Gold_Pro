import { getAdminClient } from './supabaseAdmin';
import { listPackages } from './catalog';
import { toUserPayload } from './auth';
import { isMailConfigured, sendReceiptEmail } from './mailer';

// ใบเสร็จรับเงิน: ออกอัตโนมัติ 1 ใบต่อ 1 คำสั่งซื้อที่ชำระแล้ว (ตาราง receipts — supabase_receipts_patch_04.sql)
// ข้อมูลผู้ขายตั้งได้ด้วย env: RECEIPT_SELLER_NAME, RECEIPT_SELLER_ADDRESS, RECEIPT_SELLER_TAX_ID, RECEIPT_SELLER_CONTACT

export function sellerInfo() {
  return {
    name: process.env.RECEIPT_SELLER_NAME || 'GoldBot24',
    address: process.env.RECEIPT_SELLER_ADDRESS || '',
    taxId: process.env.RECEIPT_SELLER_TAX_ID || '',
    contact: process.env.RECEIPT_SELLER_CONTACT || 'goldbot24.vercel.app',
  };
}

const METHOD_LABELS = { PROMPTPAY: 'PromptPay QR', BEAM: 'PromptPay (Beam)', PROMO: 'Promo' };

export function toPublicReceipt(r) {
  return {
    receiptNo: r.receipt_no,
    orderId: r.order_id,
    email: r.email,
    customerName: r.customer_name,
    itemName: r.item_name,
    hours: Number(r.hours) || 0,
    amountThb: Number(r.amount_thb) || 0,
    paymentMethod: METHOD_LABELS[r.payment_method] || r.payment_method || 'PromptPay QR',
    paymentRef: r.payment_ref,
    productKey: r.product_key,
    issuedAt: r.issued_at,
    emailedAt: r.emailed_at,
    emailError: r.email_error,
    seller: sellerInfo(),
  };
}

/** ค้นหาใบเสร็จจากเลขที่ใบเสร็จหรือเลขคำสั่งซื้อ */
export async function findReceipt(idOrNo) {
  const key = String(idOrNo || '').trim();
  if (!/^[A-Za-z0-9_-]{4,80}$/.test(key)) return null;
  const { data, error } = await getAdminClient().from('receipts').select('*').or(`receipt_no.eq.${key},order_id.eq.${key}`).limit(1);
  if (error) return null;
  return data?.[0] || null;
}

/** ส่งอีเมลใบเสร็จ แล้วบันทึกผลการส่งลงตาราง */
export async function emailReceipt(receipt) {
  const supabase = getAdminClient();
  if (!receipt.email) return { ok: false, error: 'ไม่มีอีเมลผู้ซื้อ' };
  if (!isMailConfigured()) {
    await supabase.from('receipts').update({ email_error: 'SMTP ยังไม่ได้ตั้งค่า' }).eq('id', receipt.id);
    return { ok: false, error: 'ระบบส่งอีเมลยังไม่พร้อม' };
  }
  try {
    await sendReceiptEmail(receipt.email, toPublicReceipt(receipt));
    await supabase.from('receipts').update({ emailed_at: new Date().toISOString(), email_error: null }).eq('id', receipt.id);
    return { ok: true };
  } catch (err) {
    console.error('[receipts] email failed:', err.message);
    await supabase.from('receipts').update({ email_error: String(err.message).slice(0, 300) }).eq('id', receipt.id);
    return { ok: false, error: 'ส่งอีเมลไม่สำเร็จ' };
  }
}

/**
 * ออกใบเสร็จสำหรับคำสั่งซื้อที่ชำระแล้ว (ทำซ้ำได้ — ถ้ามีใบเสร็จอยู่แล้วจะใช้ใบเดิม) แล้วส่งอีเมลถ้ายังไม่เคยส่ง
 * ไม่ throw — ข้อผิดพลาดใด ๆ ต้องไม่ทำให้การชำระเงินล้ม
 */
export async function issueReceipt(order, { productKey, paymentRef } = {}) {
  try {
    const supabase = getAdminClient();
    let receipt = await findReceipt(order.order_id);

    if (!receipt) {
      let customerName = null;
      if (order.owner_user_id) {
        const { data: row } = await supabase.from('bot_config').select('*').eq('id', Number(order.owner_user_id)).maybeSingle();
        if (row) customerName = toUserPayload(row).displayName;
      }
      const hours = Number(order.hours_to_add) || 0;
      const pkg = order.package_id
        ? (await listPackages({ includeInactive: true })).packages.find((p) => Number(p.id) === Number(order.package_id))
        : null;
      const { data, error } = await supabase
        .from('receipts')
        .insert({
          order_id: order.order_id,
          user_id: order.owner_user_id ? String(order.owner_user_id) : null,
          email: order.owner_email || null,
          customer_name: customerName || (order.owner_email || '').split('@')[0] || null,
          item_name: pkg?.name ? `${pkg.name} (${hours} ชั่วโมง)` : `เวลาใช้งาน GoldBot24 ${hours} ชั่วโมง`,
          hours,
          amount_thb: Number(order.amount_thb) || 0,
          payment_method: order.payment_method || 'PROMPTPAY',
          payment_ref: String(paymentRef || order.payment_ref || '').slice(0, 120) || null,
          product_key: productKey || order.generated_key_code || null,
        })
        .select()
        .maybeSingle();
      if (error) {
        if (error.code === '23505') receipt = await findReceipt(order.order_id);
        else {
          console.error('[receipts] insert failed (รัน supabase_receipts_patch_04.sql แล้วหรือยัง?):', error.message);
          return null;
        }
      } else {
        receipt = data;
      }
    }

    if (receipt && !receipt.emailed_at) await emailReceipt(receipt);
    return receipt;
  } catch (err) {
    console.error('[receipts] issue failed:', err.message);
    return null;
  }
}
