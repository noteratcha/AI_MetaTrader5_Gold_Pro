import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ success: false, error: 'Method not allowed' });
  }

  try {
    const { email } = req.query;
    const emailClean = (email || '').trim().toLowerCase();

    if (!emailClean) {
      return res.status(400).json({ success: false, error: 'Email required' });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
    const { data: users, error } = await supabase
      .from('bot_config')
      .select('*')
      .eq('mt5_server', emailClean);

    if (error || !users || users.length === 0) {
      return res.status(404).json({ success: false, error: 'User not found' });
    }

    const user = users[0];
    let displayName = emailClean.split('@')[0];
    let role = 'user';
    if (Array.isArray(user.symbols_trading)) {
      for (const item of user.symbols_trading) {
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

    return res.status(200).json({
      success: true,
      user: {
        id: String(user.id),
        email: user.mt5_server,
        displayName,
        hoursRemaining: Number(user.lot_size) || 0.0,
        mt5Login: user.mt5_login || 0,
        role,
        isAdmin
      }
    });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
}