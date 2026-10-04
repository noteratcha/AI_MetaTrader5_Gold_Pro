import { getAdminClient } from '../../../../../lib/server/supabaseAdmin';
import { allowMethods, requireAdmin } from '../../../../../lib/server/auth';
import { loadUserRow } from '../../../../../lib/server/adminUsers';

// Log ของผู้ใช้แต่ละคน: activity (กิจกรรมบัญชี) | trades | signals | risk  — แบ่งหน้า
const SOURCES = {
  activity: { table: 'user_activity', columns: 'id, event, detail, actor, ip, created_at', order: 'created_at' },
  trades: { table: 'trade_logs', columns: 'id, time, action, plan, price, lot, sl, tp, profit, comment', order: 'time' },
  signals: { table: 'signal_logs', columns: 'id, time, signal_type, plan, direction, price, ai_up, ai_down, h4_trend, status, detail', order: 'time' },
  risk: { table: 'risk_events', columns: 'id, time, event_type, direction, message, loss_amount', order: 'time' },
};

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  const row = await loadUserRow(req.query.id);
  if (!row) return res.status(404).json({ success: false, error: 'ไม่พบผู้ใช้' });

  const type = SOURCES[req.query.type] ? req.query.type : 'activity';
  const src = SOURCES[type];
  const pageSize = Math.min(100, Math.max(1, parseInt(req.query.pageSize, 10) || 20));
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);

  const { data, count, error } = await getAdminClient()
    .from(src.table)
    .select(src.columns, { count: 'exact' })
    .eq('email', row.mt5_server)
    .order(src.order, { ascending: false })
    .range((page - 1) * pageSize, page * pageSize - 1);

  if (error) {
    // ตาราง/คอลัมน์ยังไม่ถูกสร้าง (ยังไม่ได้รัน supabase_admin_patch_02.sql)
    return res.status(200).json({ success: true, type, items: [], total: 0, page, pageSize, totalPages: 1, notice: 'ยังไม่มีข้อมูล (ต้องรัน supabase_admin_patch_02.sql)' });
  }
  return res.status(200).json({ success: true, type, items: data || [], total: count || 0, page, pageSize, totalPages: Math.max(1, Math.ceil((count || 0) / pageSize)) });
}
