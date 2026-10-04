export const runtime = 'nodejs';

import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';

export async function POST(req) {
  try {
    const body = await req.json();
    const email = (body.email || '').trim().toLowerCase();
    const password = body.password || '';

    if (!email || !password) {
      return Response.json({ success: false, error: 'กรุณากรอกอีเมลและรหัสผ่าน' }, { status: 400 });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    const { data: users, error: queryErr } = await supabase
      .from('bot_config')
      .select('*')
      .eq('mt5_server', email);

    if (queryErr) {
      console.error('Login query error:', queryErr);
      return Response.json({ success: false, error: 'ไม่สามารถติดต่อฐานข้อมูลได้' }, { status: 500 });
    }

    if (!users || users.length === 0) {
      return Response.json({ 
        success: false, 
        error: 'ไม่พบบัญชีผู้ใช้นี้ในระบบ กรุณาตรวจสอบอีเมลหรือสมัครสมาชิกใหม่' 
      }, { status: 404 });
    }

    const userRecord = users[0];

    return Response.json({ 
      success: true, 
      message: 'Login query working!',
      email,
      userId: userRecord.id,
      timestamp: new Date().toISOString()
    });
  } catch (err) {
    console.error('Login exception:', err);
    return Response.json({ success: false, error: 'เกิดข้อผิดพลาด: ' + err.message }, { status: 500 });
  }
}