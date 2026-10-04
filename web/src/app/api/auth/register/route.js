import { NextResponse } from 'next/server';
import crypto from 'crypto';
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.pbkdf2Sync(password, salt, 10000, 32, 'sha256').toString('hex');
  return `v1$${salt}$${hash}`;
}

export async function POST(req) {
  try {
    const body = await req.json();
    const email = (body.email || '').trim().toLowerCase();
    const password = body.password || '';
    const displayName = (body.displayName || body.username || email.split('@')[0] || 'Trader').trim();

    if (!email || !email.includes('@')) {
      return NextResponse.json({ success: false, error: 'กรุณากรอกอีเมลที่ถูกต้อง' }, { status: 400 });
    }

    if (!password || password.length < 6) {
      return NextResponse.json({ success: false, error: 'รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร' }, { status: 400 });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    // 1. ตรวจสอบว่ามีอีเมลนี้ลงทะเบียนไว้แล้วหรือไม่
    const { data: existing, error: checkErr } = await supabase
      .from('bot_config')
      .select('id, mt5_server')
      .eq('mt5_server', email);

    if (existing && existing.length > 0) {
      return NextResponse.json({ 
        success: false, 
        error: 'อีเมลนี้ได้ลงทะเบียนไว้ในระบบแล้ว กรุณาเข้าสู่ระบบ' 
      }, { status: 400 });
    }

    // 2. สร้างบัญชีใหม่ใน bot_config (id > 1000)
    // ให้ชั่วโมงเริ่มต้นทดลองใช้งานจริง 48.00 ชั่วโมง (เก็บใน lot_size)
    const newAccountId = Math.floor(Math.random() * 100000000) + 10000;
    const passwordHash = hashPassword(password);
    const initialHours = 48.0;

    const { data: created, error: insertErr } = await supabase
      .from('bot_config')
      .insert({
        id: newAccountId,
        mt5_login: 0,
        mt5_password: passwordHash,
        mt5_server: email,
        is_bot_active: true,
        lot_size: initialHours,
        symbols_trading: [`name:${displayName}`, 'role:user', `registered:${new Date().toISOString()}`]
      })
      .select();

    if (insertErr) {
      console.error('Registration insert error:', insertErr);
      return NextResponse.json({ success: false, error: 'ไม่สามารถสร้างบัญชีได้: ' + insertErr.message }, { status: 500 });
    }

    // สร้าง Token สรุปข้อมูลสำหรับ Session
    const userPayload = {
      id: String(newAccountId),
      email,
      displayName,
      hoursRemaining: initialHours,
      role: 'user',
      createdAt: new Date().toISOString()
    };

    const token = Buffer.from(JSON.stringify(userPayload)).toString('base64');

    return NextResponse.json({
      success: true,
      message: 'สมัครสมาชิกสำเร็จ! ได้รับโควต้าเริ่มต้น 48 ชั่วโมง',
      user: userPayload,
      token
    });
  } catch (err) {
    console.error('Registration error:', err);
    return NextResponse.json({ success: false, error: 'เกิดข้อผิดพลาดภายในระบบ: ' + err.message }, { status: 500 });
  }
}
