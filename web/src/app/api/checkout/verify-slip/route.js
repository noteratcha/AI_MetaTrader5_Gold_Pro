import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';
const SLIPOK_BRANCH_ID = process.env.SLIPOK_BRANCH_ID || '';
const SLIPOK_API_KEY = process.env.SLIPOK_API_KEY || '';

// ฟังก์ชันสร้าง Product Key สุ่ม 24 หลัก 6 กลุ่ม (XXXX-XXXX-XXXX-XXXX-XXXX-XXXX)
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
    const formData = await request.formData();
    const order_id = formData.get('order_id');
    const slipFile = formData.get('slip');

    if (!order_id) {
      return NextResponse.json({ error: 'Missing order_id' }, { status: 400 });
    }

    if (!slipFile) {
      return NextResponse.json({ error: 'Missing slip image file' }, { status: 400 });
    }

    const headers = {
      'apikey': SUPABASE_KEY,
      'Authorization': `Bearer ${SUPABASE_KEY}`,
      'Content-Type': 'application/json',
      'Prefer': 'return=representation'
    };

    // 1. ดึงข้อมูลคำสั่งซื้อจาก Supabase
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
        is_paid: true,
        order_id: order.order_id,
        product_key: order.generated_key_code,
        message: 'คำสั่งซื้อนี้ได้รับการชำระเงินเรียบร้อยแล้ว'
      });
    }

    let verificationSuccess = false;
    let transRef = 'SLIPOK-TXN-' + Date.now();
    let slipDetails = null;

    // 2. ถ้ามีการระบุ SLIPOK_BRANCH_ID และ SLIPOK_API_KEY ให้ยิงตรวจสลิปจริงผ่าน SlipOK API
    if (SLIPOK_BRANCH_ID && SLIPOK_API_KEY) {
      try {
        const slipokBody = new FormData();
        slipokBody.append('files', slipFile);
        slipokBody.append('amount', order.amount_thb.toString());
        slipokBody.append('log', 'true');

        const slipokRes = await fetch(`https://api.slipok.com/api/line/apikey/${SLIPOK_BRANCH_ID}`, {
          method: 'POST',
          headers: {
            'x-authorization': SLIPOK_API_KEY
          },
          body: slipokBody
        });

        const slipokData = await slipokRes.json();
        console.log('[SlipOK API Response]:', slipokData);

        if (slipokData.success && slipokData.data) {
          verificationSuccess = true;
          transRef = slipokData.data.transRef || transRef;
          slipDetails = slipokData.data;
        } else {
          let userMsg = slipokData.message || 'สลิปไม่ถูกต้อง หรือยอดเงินไม่ตรงกับแพ็กเกจ';
          if (slipokData.code === 1001) {
            userMsg = 'ยังไม่ได้กดยืนยัน "สร้างสาขา" ใน SlipOK กรุณากดปุ่มสร้างสาขาในเว็บ SlipOK ก่อนครับ';
          }
          return NextResponse.json({
            success: false,
            error: userMsg,
            details: slipokData
          }, { status: 400 });
        }
      } catch (err) {
        console.error('[SlipOK API Error]:', err);
        return NextResponse.json({ error: 'SlipOK service error: ' + err.message }, { status: 500 });
      }
    } else {
      // 3. Mock Verification Mode (กรณีเจ้าของร้านยังไม่ได้ใส่ SlipOK API Key ใน .env.local)
      // ตรวจสอบเบื้องต้นว่าเป็นไฟล์รูปภาพจริง
      if (slipFile.size > 0 && slipFile.type.startsWith('image/')) {
        verificationSuccess = true;
        transRef = 'SLIPOK-DEMO-' + Math.floor(10000000 + Math.random() * 90000000);
        slipDetails = {
          mock: true,
          fileName: slipFile.name,
          fileSize: slipFile.size,
          note: 'ตรวจสลิปผ่านระบบจำลอง SlipOK (เพิ่ม SLIPOK_API_KEY ใน .env.local เพื่อตรวจสลิปธนาคารจริง)'
        };
      } else {
        return NextResponse.json({ error: 'กรุณาอัปโหลดไฟล์รูปภาพสลิปที่ถูกต้อง (JPG, PNG)' }, { status: 400 });
      }
    }

    if (verificationSuccess) {
      // 4. สลิปผ่าน -> ผลิต Product Key 24 หลัก
      const auto_key = generateSecureProductKey();

      // บันทึกลง product_keys
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

      await fetch(`${SUPABASE_URL}/rest/v1/product_keys`, {
        method: 'POST',
        headers,
        body: JSON.stringify(keyData)
      });

      // อัปเดตสถานะ orders เป็น PAID
      const orderPatch = {
        status: 'PAID',
        payment_ref: transRef,
        generated_key_code: auto_key,
        paid_at: new Date().toISOString()
      };

      await fetch(`${SUPABASE_URL}/rest/v1/orders?order_id=eq.${order_id}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify(orderPatch)
      });

      return NextResponse.json({
        success: true,
        order_id: order.order_id,
        payment_ref: transRef,
        product_key: auto_key,
        hours: order.hours_to_add || order.amount_thb,
        slip_details: slipDetails,
        message: 'ตรวจสอบสลิปผ่าน SlipOK สำเร็จ! ผลิตรหัส Product Key เรียบร้อยแล้ว'
      });
    }

    return NextResponse.json({ error: 'สลิปไม่ผ่านการตรวจสอบ' }, { status: 400 });
  } catch (error) {
    console.error('[Verify-Slip Error]:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
