import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';

export async function GET(req) {
  try {
    const { searchParams } = new URL(req.url);
    const email = (searchParams.get('email') || '').trim().toLowerCase();

    if (!email) {
      return NextResponse.json({ success: false, error: 'Email required' }, { status: 400 });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);
    const { data: users, error } = await supabase
      .from('bot_config')
      .select('*')
      .eq('mt5_server', email);

    if (error || !users || users.length === 0) {
      return NextResponse.json({ success: false, error: 'User not found' }, { status: 404 });
    }

    const user = users[0];
    let displayName = email.split('@')[0];
    let role = 'user';
    if (Array.isArray(user.symbols_trading)) {
      for (const item of user.symbols_trading) {
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

    return NextResponse.json({
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
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}
