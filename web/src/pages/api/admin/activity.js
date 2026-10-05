import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireAdmin } from '../../../lib/server/auth';

const PAGE_SIZE = 10;

// GET ?page=N → กิจกรรมล่าสุดของทั้งระบบ หน้าละ 10 รายการ (ใหม่สุดก่อน)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  const page = Math.max(1, Math.min(1000, parseInt(req.query.page, 10) || 1));
  const from = (page - 1) * PAGE_SIZE;
  const { data, count, error } = await getAdminClient()
    .from('user_activity')
    .select('id, email, event, detail, actor, created_at', { count: 'exact' })
    .order('created_at', { ascending: false })
    .range(from, from + PAGE_SIZE - 1);

  res.setHeader('Cache-Control', 'no-store');
  if (error) return res.status(200).json({ success: true, items: [], total: 0, page: 1, totalPages: 1, setupRequired: true });
  const total = count || 0;
  return res.status(200).json({ success: true, items: data || [], total, page, pageSize: PAGE_SIZE, totalPages: Math.max(1, Math.ceil(total / PAGE_SIZE)) });
}
