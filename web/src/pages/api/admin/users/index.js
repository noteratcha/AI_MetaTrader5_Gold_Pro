import crypto from 'crypto';
import { getAdminClient } from '../../../../lib/server/supabaseAdmin';
import { allowMethods, hashPassword, isReservedEmail, isValidEmail, normalizeEmail, requireAdmin } from '../../../../lib/server/auth';
import { enrichUsers } from '../../../../lib/server/adminUsers';
import { logActivity } from '../../../../lib/server/activity';

const MAX_PAGE_SIZE = 100;

// GET  รายชื่อผู้ใช้ (ค้นหา/กรอง/แบ่งหน้า) พร้อมสรุปการใช้งาน
// POST สร้างผู้ใช้ใหม่ (ผู้ใช้ทั่วไปเท่านั้น)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET', 'POST'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;
  const supabase = getAdminClient();

  if (req.method === 'GET') {
    const pageSize = Math.min(MAX_PAGE_SIZE, Math.max(1, parseInt(req.query.pageSize, 10) || 20));
    const page = Math.max(1, parseInt(req.query.page, 10) || 1);
    const q = String(req.query.q || '').trim().toLowerCase().replace(/[%,()]/g, '');
    const filter = String(req.query.filter || 'all');

    let query = supabase.from('bot_config').select('*', { count: 'exact' }).gt('id', 1);
    if (q) query = query.ilike('mt5_server', `%${q}%`);
    if (filter === 'disabled') query = query.contains('symbols_trading', ['status:disabled']);
    if (filter === 'admin') query = query.contains('symbols_trading', ['role:admin']);
    if (filter === 'low') query = query.lte('lot_size', 5);
    query = query.order('updated_at', { ascending: false }).range((page - 1) * pageSize, page * pageSize - 1);

    const { data, count, error } = await query;
    if (error) return res.status(500).json({ success: false, error: 'โหลดรายชื่อผู้ใช้ไม่สำเร็จ' });
    const users = await enrichUsers(data || []);
    return res.status(200).json({ success: true, users, total: count || 0, page, pageSize, totalPages: Math.max(1, Math.ceil((count || 0) / pageSize)) });
  }

  // POST
  const email = normalizeEmail(req.body?.email);
  const password = String(req.body?.password || '');
  const displayName = String(req.body?.displayName || '').trim().slice(0, 40) || email.split('@')[0];
  const hours = Number(req.body?.hours ?? 0);

  if (!isValidEmail(email)) return res.status(400).json({ success: false, error: 'อีเมลไม่ถูกต้อง' });
  if (isReservedEmail(email)) return res.status(403).json({ success: false, error: 'อีเมลนี้สงวนไว้สำหรับผู้ดูแลระบบ' });
  if (password.length < 6) return res.status(400).json({ success: false, error: 'รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร' });
  if (!(hours >= 0) || hours > 9999) return res.status(400).json({ success: false, error: 'ชั่วโมงต้องอยู่ระหว่าง 0–9,999' });

  const { data: existing } = await supabase.from('bot_config').select('id').eq('mt5_server', email).limit(1);
  if (existing?.length) return res.status(409).json({ success: false, error: 'อีเมลนี้มีในระบบแล้ว' });

  let created = null;
  for (let attempt = 0; attempt < 3 && !created; attempt++) {
    const { data, error } = await supabase
      .from('bot_config')
      .insert({
        id: crypto.randomInt(10000, 100000000),
        mt5_login: 0,
        mt5_password: hashPassword(password),
        mt5_server: email,
        is_bot_active: true,
        lot_size: Math.round(hours * 100) / 100,
        symbols_trading: [`name:${displayName}`, 'role:user', `registered:${new Date().toISOString()}`, `created_by:${auth.user.email}`],
      })
      .select()
      .maybeSingle();
    if (!error) created = data;
    else if (error.code !== '23505') return res.status(500).json({ success: false, error: 'สร้างผู้ใช้ไม่สำเร็จ' });
  }
  if (!created) return res.status(500).json({ success: false, error: 'สร้างผู้ใช้ไม่สำเร็จ' });

  await logActivity({ userId: created.id, email, event: 'admin_create', detail: `สร้างบัญชีโดยแอดมิน (+${hours} ชม.)`, actor: auth.user.email });
  const [user] = await enrichUsers([created]);
  return res.status(201).json({ success: true, user });
}
