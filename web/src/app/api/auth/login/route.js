export const runtime = 'nodejs';

import crypto from 'crypto';

export async function POST(req) {
  try {
    const body = await req.json();
    const email = (body.email || '').trim().toLowerCase();
    const password = body.password || '';

    if (!email || !password) {
      return Response.json({ success: false, error: 'กรุณากรอกอีเมลและรหัสผ่าน' }, { status: 400 });
    }

    // Test crypto
    const hash = crypto.createHash('sha256').update(password).digest('hex');
    
    return Response.json({ 
      success: true, 
      message: 'Test login with crypto working!',
      email,
      hashLength: hash.length,
      timestamp: new Date().toISOString()
    });
  } catch (err) {
    return Response.json({ success: false, error: err.message }, { status: 500 });
  }
}