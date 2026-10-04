import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export const runtime = 'nodejs';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';

function normalizeKey(raw) {
  if (!raw) return '';
  const clean = String(raw).replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 24);
  const chunks = [];
  for (let i = 0; i < clean.length; i += 4) {
    chunks.push(clean.slice(i, i + 4));
  }
  return chunks.join('-');
}

export async function POST(req) {
  try {
    const body = await req.json();
    const email = (body.email || '').trim().toLowerCase();
    const rawKey = body.keyCode || body.key || '';
    const keyCode = normalizeKey(rawKey);

    if (!email) {
      return NextResponse.json({ success: false, error: 'กรุณาระบุบัญชีอีเมลของผู้ใช้งาน' }, { status: 400 });
    }

    if (!keyCode || keyCode.length !== 29) {
      return NextResponse.json({ success: false, error: 'รูปแบบ Product Key ไม่ถูกต้อง (ต้องเป็น 24 ตัวอักษร เช่น XXXX-XXXX-XXXX-XXXX-XXXX-XXXX)' }, { status: 400 });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    // 1. ตรวจสอบว่าคีย์มีจริงและยังไม่ได้ใช้
    const { data: keyRecords, error: keyErr } = await supabase
      .from('product_keys')
      .select('*')
      .eq('key_code', keyCode);

    if (keyErr || !keyRecords || keyRecords.length === 0) {
      return NextResponse.json({ success: false, error: 'ไม่พบรหัส Product Key นี้ในระบบ' }, { status: 404 });
    }

    const keyObj = keyRecords[0];
    if (keyObj.is_used || keyObj.status === 'REDEEMED') {
      return NextResponse.json({ success: false, error: 'รหัส Product Key นี้ถูกใช้งานไปแล้ว' }, { status: 400 });
    }

    const hoursToAdd = (Number(keyObj.hours) || 0) + (Number(keyObj.bonus_hours) || 0);

    // 2. ดึงข้อมูล User จาก bot_config
    const { data: users, error: userErr } = await supabase
      .from('bot_config')
      .select('*')
      .eq('mt5_server', email);

    if (userErr || !users || users.length === 0) {
      return NextResponse.json({ success: false, error: 'ไม่พบบัญชีผู้ใช้งานที่ระบุ' }, { status: 404 });
    }

    const userObj = users[0];
    const currentHours = Number(userObj.lot_size) || 0.0;
    const newBalance = Math.round((currentHours + hoursToAdd) * 100) / 100;

    // 3. อัปเดตสถานะคีย์ว่าถูกใช้งานแล้ว
    await supabase
      .from('product_keys')
      .update({
        is_used: true,
        status: 'REDEEMED',
        order_id: keyObj.order_id || `REDEEMED-${email}`,
        redeemed_at: new Date().toISOString()
      })
      .eq('key_code', keyCode);

    // 4. บวกเพิ่มชั่วโมงเข้าบัญชีผู้ใช้ (Additive Top-up)
    await supabase
      .from('bot_config')
      .update({
        lot_size: newBalance,
        updated_at: new Date().toISOString()
      })
      .eq('id', userObj.id);

    return NextResponse.json({
      success: true,
      message: `เติมเวลาสำเร็จ! ได้รับเพิ่ม +${hoursToAdd} ชั่วโมง รวมเป็น ${newBalance.toFixed(2)} ชั่วโมง`,
      hoursAdded: hoursToAdd,
      hoursRemaining: newBalance
    });
  } catch (err) {
    console.error('Redeem error:', err);
    return NextResponse.json({ success: false, error: 'เกิดข้อผิดพลาดในการเติมชั่วโมง: ' + err.message }, { status: 500 });
  }
}
