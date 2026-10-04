import { createClient } from '@supabase/supabase-js';

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

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ success: false, error: 'Method not allowed' });
  }

  try {
    const { email, keyCode } = req.body;
    const emailClean = (email || '').trim().toLowerCase();
    const keyClean = normalizeKey(keyCode);

    if (!emailClean) {
      return res.status(400).json({ success: false, error: 'Email required' });
    }

    if (keyClean.length < 29) {
      return res.status(400).json({ success: false, error: 'กรุณากรอกรหัสให้ครบ 24 หลัก (6 กลุ่ม)!' });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    const { data: keys, error: keyErr } = await supabase
      .from('promo_keys')
      .select('*')
      .eq('key_code', keyClean)
      .single();

    if (keyErr || !keys) {
      return res.status(404).json({ success: false, error: 'ไม่พบรหัสนี้ในระบบ' });
    }

    if (keys.used) {
      return res.status(400).json({ success: false, error: 'รหัสนี้ถูกใช้งานไปแล้ว' });
    }

    if (keys.expires_at && new Date(keys.expires_at) < new Date()) {
      return res.status(400).json({ success: false, error: 'รหัสนี้หมดอายุแล้ว' });
    }

    const { data: users, error: userErr } = await supabase
      .from('bot_config')
      .select('*')
      .eq('mt5_server', emailClean)
      .single();

    if (userErr || !users) {
      return res.status(404).json({ success: false, error: 'ไม่พบบัญชีผู้ใช้นี้' });
    }

    const currentHours = Number(users.lot_size) || 0;
    const newHours = currentHours + Number(keys.hours);

    const { error: updateErr } = await supabase
      .from('bot_config')
      .update({ lot_size: newHours })
      .eq('mt5_server', emailClean);

    if (updateErr) {
      return res.status(500).json({ success: false, error: 'ไม่สามารถอัปเดตชั่วโมงได้' });
    }

    const { error: keyUpdateErr } = await supabase
      .from('promo_keys')
      .update({ used: true, used_by: emailClean, used_at: new Date().toISOString() })
      .eq('key_code', keyClean);

    if (keyUpdateErr) {
      return res.status(500).json({ success: false, error: 'ไม่สามารถอัปเดตรหัสได้' });
    }

    return res.status(200).json({
      success: true,
      message: `เติมชั่วโมงสำเร็จ! ได้รับ ${keys.hours} ชั่วโมง (รวม ${newHours.toFixed(2)} ชม.)`,
      hoursRemaining: newHours
    });
  } catch (err) {
    console.error('Redeem exception:', err);
    return res.status(500).json({ success: false, error: 'เกิดข้อผิดพลาด: ' + err.message });
  }
}