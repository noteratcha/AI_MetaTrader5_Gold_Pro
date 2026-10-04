import { NextResponse } from 'next/server';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const order_id = searchParams.get('order_id');

    if (!order_id) {
      return NextResponse.json({ error: 'Missing order_id' }, { status: 400 });
    }

    const res = await fetch(`${SUPABASE_URL}/rest/v1/orders?order_id=eq.${order_id}&select=*`, {
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': `Bearer ${SUPABASE_KEY}`
      }
    });

    if (!res.ok) {
      return NextResponse.json({ error: 'Failed to fetch order status' }, { status: 500 });
    }

    const orders = await res.json();
    if (!orders || orders.length === 0) {
      return NextResponse.json({ error: 'Order not found' }, { status: 404 });
    }

    const order = orders[0];
    return NextResponse.json({
      success: true,
      order_id: order.order_id,
      status: order.status,
      is_paid: order.status === 'PAID',
      generated_key_code: order.generated_key_code,
      amount_thb: order.amount_thb,
      paid_at: order.paid_at
    });
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
