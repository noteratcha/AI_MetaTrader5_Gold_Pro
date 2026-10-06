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

  // ระยะเวลาถือไม้: จับคู่แถวเปิด (OPEN_*) กับแถวปิด (CLOSE / TP_HIT / SL_HIT) ด้วยเลข ticket เดียวกัน
  const CLOSE_ACTIONS = ['CLOSE', 'TP_HIT', 'SL_HIT'];
  const tickets = [...new Set((data || []).filter((r) => r.ticket && (String(r.action).startsWith('OPEN_') || CLOSE_ACTIONS.includes(r.action))).map((r) => r.ticket))];
  const opened = {};
  const closed = {};
  if (tickets.length) {
    const { data: pairs } = await getAdminClient()
      .from('trade_logs')
      .select('ticket, action, time')
      .eq('email', auth.user.email)
      .in('ticket', tickets)
      .or(`action.like.OPEN_%,action.in.(${CLOSE_ACTIONS.join(',')})`)
      .limit(1000);
    for (const p of pairs || []) {
      if (String(p.action).startsWith('OPEN_')) opened[p.ticket] = p.time;
      else if (!closed[p.ticket] || p.time < closed[p.ticket]) closed[p.ticket] = p.time;
    }
  }
  const holdOf = (r) => {
    const isOpenRow = String(r.action).startsWith('OPEN_');
    if (!isOpenRow && !CLOSE_ACTIONS.includes(r.action)) return { holdSec: null, holding: false };
    const start = opened[r.ticket];
    const end = closed[r.ticket];
    if (!start) return { holdSec: null, holding: false };
    if (end) return { holdSec: Math.max(0, Math.round((new Date(end) - new Date(start)) / 1000)), holding: false };
    // ยังไม่มีแถวปิด → ไม้ยังเปิดอยู่ (นับถึงตอนนี้ ไม่เกิน 30 วัน)
    const sec = Math.round((Date.now() - new Date(start)) / 1000);
    return sec < 30 * 86400 ? { holdSec: sec, holding: true } : { holdSec: null, holding: false };
  };

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
      ...holdOf(r),
    })),
  });
}
