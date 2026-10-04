import crypto from 'crypto';
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.pbkdf2Sync(password, salt, 10000, 32, 'sha256').toString('hex');
  return `v1$${salt}$${hash}`;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ success: false, error: 'Method not allowed' });
  }

  try {
    const { email, password, displayName } = req.body;
    const emailClean = (email || '').trim().toLowerCase();
    const passwordClean = password || '';
    const nameClean = (displayName || emailClean.split('@')[0] || 'Trader').trim();

    if (!emailClean || !emailClean.includes('@')) {
      return res.status(400).json({ success: false, error: 'กรุณากรอกอีเมลที่ถูกต้อง' });
    }

    if (!passwordClean || passwordClean.length < 6) {
      return res.status(400).json({ success: false, error: 'รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร' });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    const { data: existing, error: checkErr } = await supabase
      .from('bot_config')
      .select('id, mt5_server')
      .eq('mt5_server', emailClean);

    if (existing && existing.length > 0) {
      return res.status(400).json({ 
        success: false, 
        error: 'อีเมลนี้ได้ลงทะเบียนไว้ในระบบแล้ว กรุณาเข้าสู่ระบบ' 
      });
    }

    const newAccountId = Math.floor(Math.random() * 100000000) + 10000;
    const passwordHash = hashPassword(passwordClean);
    const initialHours = 48.0;

    const { data: created, error: insertErr } = await supabase
      .from('bot_config')
      .insert({
        id: newAccountId,
        mt5_login: 0,
        mt5_password: passwordHash,
        mt5_server: emailClean,
        is_bot_active: true,
        lot_size: initialHours,
        symbols_trading: [`name:${nameClean}`, 'role:user', `registered:${new Date().toISOString()}`]
      })
      .select();

    if (insertErr) {
      console.error('Registration insert error:', insertErr);
      return res.status(500).json({ success: false, error: 'ไม่สามารถสร้างบัญชีได้: ' + insertErr.message });
    }

    const userPayload = {
      id: String(newAccountId),
      email: emailClean,
      displayName: nameClean,
      hoursRemaining: initialHours,
      role: 'user',
      createdAt: new Date().toISOString()
    };

    const token = Buffer.from(JSON.stringify(userPayload)).toString('base64');

    return res.status(200).json({
      success: true,
      message: 'สมัครสมาชิกสำเร็จ! ได้รับโควต้าเริ่มต้น 48 ชั่วโมง',
      user: userPayload,
      token
    });
  } catch (err) {
    console.error('Registration error:', err);
    return res.status(500).json({ success: false, error: 'เกิดข้อผิดพลาดภายในระบบ: ' + err.message });
  }
}