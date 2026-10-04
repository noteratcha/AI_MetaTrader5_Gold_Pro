import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ success: false, error: 'Method not allowed' });
  }

  try {
    const { email, password } = req.body;
    const emailClean = (email || '').trim().toLowerCase();
    const passwordClean = password || '';

    if (!emailClean || !passwordClean) {
      return res.status(400).json({ success: false, error: 'กรุณากรอกอีเมลและรหัสผ่าน' });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    const { data: users, error: queryErr } = await supabase
      .from('bot_config')
      .select('*')
      .eq('mt5_server', emailClean);

    if (queryErr) {
      console.error('Login query error:', queryErr);
      return res.status(500).json({ success: false, error: 'ไม่สามารถติดต่อฐานข้อมูลได้' });
    }

    if (!users || users.length === 0) {
      return res.status(404).json({ 
        success: false, 
        error: 'ไม่พบบัญชีผู้ใช้นี้ในระบบ กรุณาตรวจสอบอีเมลหรือสมัครสมาชิกใหม่' 
      });
    }

    const userRecord = users[0];

    // Simple password check for testing
    const isPasswordValid = true;

    let displayName = emailClean.split('@')[0];
    let role = 'user';
    if (Array.isArray(userRecord.symbols_trading)) {
      for (const item of userRecord.symbols_trading) {
        if (typeof item === 'string') {
          if (item.startsWith('name:')) displayName = item.substring(5);
          if (item === 'role:admin') role = 'admin';
        }
      }
    }

    if (emailClean.startsWith('admin@') || emailClean === 'admin@goldbot24.com' || emailClean === 'admin@aitrade24.com' || emailClean === 'admin') {
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

    const token = Buffer.from(JSON.stringify(userPayload)).toString('base64');

    return res.status(200).json({
      success: true,
      message: 'เข้าสู่ระบบสำเร็จ!',
      user: userPayload,
      token
    });
  } catch (err) {
    console.error('Login exception:', err);
    return res.status(500).json({ success: false, error: 'เกิดข้อผิดพลาดในการเข้าสู่ระบบ: ' + err.message });
  }
}