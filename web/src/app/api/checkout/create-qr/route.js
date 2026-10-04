import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';

// PromptPay Default Recipient (สามารถตั้งค่าผ่าน ENV PROMPTPAY_ID ได้)
const PROMPTPAY_ID = process.env.PROMPTPAY_ID || '0812345678';

export async function POST(request) {
  try {
    const body = await request.json();
    const { package_id, user_id, amount_thb, hours_to_add } = body;

    if (!package_id || !amount_thb) {
      return NextResponse.json({ error: 'Missing package_id or amount_thb' }, { status: 400 });
    }

    const order_id = 'ORD-' + Math.floor(100000 + Math.random() * 900000);
    const amountNum = parseFloat(amount_thb).toFixed(2);

    // PromptPay.io QR image URL (มาตรฐาน QR PromptPay สแกนผ่านแอปธนาคารไทยได้จริง)
    const qr_image_url = `https://promptpay.io/${PROMPTPAY_ID}/${amountNum}.png`;

    // บันทึกลงตาราง orders บน Supabase
    const orderData = {
      order_id,
      package_id: parseInt(package_id),
      amount_thb: parseFloat(amountNum),
      hours_to_add: parseFloat(hours_to_add || amount_thb),
      status: 'PENDING',
      payment_method: 'PROMPTPAY',
      qr_image_url,
      user_id: user_id && user_id.length === 36 ? user_id : null,
      created_at: new Date().toISOString()
    };

    const res = await fetch(`${SUPABASE_URL}/rest/v1/orders`, {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': `Bearer ${SUPABASE_KEY}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
      },
      body: JSON.stringify(orderData)
    });

    if (!res.ok) {
      const errText = await res.text();
      console.error('[API Create-QR] Supabase error:', errText);
    }

    return NextResponse.json({
      success: true,
      order_id,
      amount_thb: amountNum,
      hours_to_add: orderData.hours_to_add,
      qr_image_url,
      promptpay_id: PROMPTPAY_ID,
      created_at: orderData.created_at
    });
  } catch (error) {
    console.error('[API Create-QR] Server exception:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
