import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireUser } from '../../../lib/server/auth';

const MAX_PAGE_SIZE = 50;

// ประวัติการเข้าไม้/ปิดไม้ของผู้ใช้ (แบ่งหน้า) — Desktop บันทึก OPEN_BUY/OPEN_SELL/CLOSE/TP_HIT/SL_HIT ลง trade_logs
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  const pageSize = Math.min(MAX_PAGE_SIZE, Math.max(1, parseInt(req.query.pageSize, 10) || 5));
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const from = (page - 1) * pageSize;

  const { data, count, error } = await getAdminClient()
    .from('trade_logs')
    .select('id, ticket, time, symbol, action, plan, price, lot, sl, tp, profit, comment', { count: 'exact' })
    .eq('email', auth.user.email)
    .order('time', { ascending: false })
    .range(from, from + pageSize - 1);

  if (error) {
    console.error('[user/trades] query error:', error.message);
    return res.status(500).json({ success: false, error: 'โหลดประวัติการเทรดไม่สำเร็จ' });
  }

  const total = count || 0;
  return res.status(200).json({
    success: true,
    page,
    pageSize,
    total,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
    items: (data || []).map((r) => ({
      id: r.id,
      ticket: r.ticket,
      time: r.time,
      symbol: r.symbol,
      action: r.action,
      plan: r.plan,
      price: Number(r.price) || 0,
      lot: Number(r.lot) || 0,
      sl: Number(r.sl) || 0,
      tp: Number(r.tp) || 0,
      profit: Number(r.profit) || 0,
      comment: r.comment || '',
    })),
  });
}
