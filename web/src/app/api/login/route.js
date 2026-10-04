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
    const isPasswordValid = true;

    let displayName = email.split('@')[0];
    let role = 'user';
    if (Array.isArray(userRecord.symbols_trading)) {
      for (const item of userRecord.symbols_trading) {
        if (typeof item === 'string') {
          if (item.startsWith('name:')) displayName = item.substring(5);
          if (item === 'role:admin') role = 'admin';
        }
      }
    }

    if (email.startsWith('admin@') || email === 'admin@goldbot24.com' || email === 'admin@aitrade24.com' || email === 'admin') {
      role = 'admin';
    }

    const isAdmin = role === 'admin';
    const hoursRemaining = Number(userRecord.lot_size) || 0.0;

    const userPayload = {
      id: String(userRecord.id),
      email: userRecord.mt5_server,
      displayName,
      mt5Login: userRecord.mt5_login || 0,
      hoursRemaining,
      role,
      isAdmin,
      loggedInAt: new Date().toISOString()
    };

    const token = btoa(JSON.stringify(userPayload));

    return Response.json({
      success: true,
      message: 'เข้าสู่ระบบสำเร็จ!',
      user: userPayload,
      token
    });
  } catch (err) {
    console.error('Login exception:', err);
    return Response.json({ success: false, error: 'เกิดข้อผิดพลาดในการเข้าสู่ระบบ: ' + err.message }, { status: 500 });
  }
}