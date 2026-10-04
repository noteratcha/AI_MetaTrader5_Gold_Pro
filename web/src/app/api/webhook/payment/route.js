import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';

// ฟังก์ชันผลิต Product Key 24 หลัก 6 กลุ่ม (XXXX-XXXX-XXXX-XXXX-XXXX-XXXX)
function generateSecureProductKey() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let result = '';
  for (let g = 0; g < 6; g++) {
    let group = '';
    for (let i = 0; i < 4; i++) {
      group += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    result += (g === 0 ? '' : '-') + group;
  }
  return result;
}

export async function POST(request) {
  try {
    const payload = await request.json();
    console.log('[Payment Webhook] Received notification:', payload);

    const order_id = payload.order_id || payload.orderId || payload.referenceNo || payload.data?.order_id;
    const payment_ref = payload.payment_ref || payload.transaction_id || payload.data?.transRef || 'BANK-TXN-' + Date.now();
    const status = (payload.status || payload.resultCode || payload.data?.status || 'SUCCESS').toUpperCase();

    if (!order_id) {
      return NextResponse.json({ error: 'Missing order_id' }, { status: 400 });
    }

    if (status !== 'SUCCESS' && status !== '00' && status !== 'PAID') {
      return NextResponse.json({ message: 'Ignored non-success status', status }, { status: 200 });
    }

    const headers = {
      'apikey': SUPABASE_KEY,
      'Authorization': `Bearer ${SUPABASE_KEY}`,
      'Content-Type': 'application/json',
      'Prefer': 'return=representation'
    };

    // 1. ดึงข้อมูล Order จาก Supabase
    const orderRes = await fetch(`${SUPABASE_URL}/rest/v1/orders?order_id=eq.${order_id}&select=*`, { headers });
    if (!orderRes.ok) {
      return NextResponse.json({ error: 'Failed to query order' }, { status: 500 });
    }

    const orders = await orderRes.json();
    if (!orders || orders.length === 0) {
      return NextResponse.json({ error: 'Order not found' }, { status: 404 });
    }

    const order = orders[0];
    if (order.status === 'PAID') {
      return NextResponse.json({
        success: true,
        message: 'Order already paid',
        order_id: order.order_id,
        product_key: order.generated_key_code
      });
    }

    // 2. สร้างรหัส Product Key 24 หลัก
    const auto_key = generateSecureProductKey();

    // 3. บันทึกเข้าตาราง product_keys
    const keyData = {
      key_code: auto_key,
      hours: order.hours_to_add || order.amount_thb,
      bonus_hours: 0,
      price_thb: order.amount_thb,
      status: 'UNUSED',
      is_used: false,
      purchased_by_user_id: order.user_id,
      order_id: order.order_id,
      purchased_at: new Date().toISOString()
    };

    const keyInsertRes = await fetch(`${SUPABASE_URL}/rest/v1/product_keys`, {
      method: 'POST',
      headers,
      body: JSON.stringify(keyData)
    });

    if (!keyInsertRes.ok) {
      const err = await keyInsertRes.text();
      console.error('[Payment Webhook] Failed to insert product_key:', err);
      return NextResponse.json({ error: 'Failed to issue product key', details: err }, { status: 500 });
    }

    // 4. อัปเดตสถานะคำสั่งซื้อเป็น PAID
    const orderPatch = {
      status: 'PAID',
      payment_ref: String(payment_ref),
      generated_key_code: auto_key,
      paid_at: new Date().toISOString()
    };

    await fetch(`${SUPABASE_URL}/rest/v1/orders?order_id=eq.${order_id}`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(orderPatch)
    });

    console.log(`[Payment Webhook] Order ${order_id} marked PAID with key: ${auto_key}`);

    return NextResponse.json({
      success: true,
      order_id: order.order_id,
      payment_ref,
      product_key: auto_key,
      hours: order.hours_to_add || order.amount_thb,
      message: 'Payment verified and Product Key generated successfully'
    });
  } catch (error) {
    console.error('[Payment Webhook] Exception:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
