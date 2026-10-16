import { allowMethods, clientIp, getUserRowById, isDisabledRow, normalizeEmail, verifyToken } from '../../../lib/server/auth';
import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { logActivity } from '../../../lib/server/activity';

/**
 * บันทึกการถามผู้ช่วย (FAB) ลง user_activity — สาธารณะ (ไม่ต้องล็อกอิน · ล็อกอินแล้วผูกกับผู้ใช้)
 *   event 'help_ask'      detail = JSON { q, top, t, s, ok, page, sid }  (คำถาม · id คำตอบ · หัวข้อ · คะแนน · พบ/ไม่พบ · หน้าที่ถาม · รหัสแชท)
 *   event 'help_feedback' detail = JSON { q, top, v: 'up'|'down', sid }
 * ใช้ที่ /admin/help เพื่อหาคำถามที่ตอบไม่ได้/ไม่ช่วย แล้วปรับคู่มือ · ฐานความรู้ · โปรแกรม
 * จำกัด 40 ครั้ง / 10 นาที / IP (กันสแปม)
 */
const LIMIT = 40;
const WINDOW_MS = 10 * 60 * 1000;
const txt = (v, max) => String(v ?? '').replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, max);

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  const b = req.body || {};
  const kind = b.kind === 'feedback' ? 'help_feedback' : 'help_ask';
  const q = txt(b.q, 300);
  if (!q) return res.status(400).json({ success: false, error: 'ไม่มีคำถาม' });

  const ip = clientIp(req);
  try {
    const { count } = await getAdminClient()
      .from('user_activity')
      .select('id', { count: 'exact', head: true })
      .in('event', ['help_ask', 'help_feedback'])
      .eq('ip', String(ip).slice(0, 64))
      .gte('created_at', new Date(Date.now() - WINDOW_MS).toISOString());
    if ((count || 0) >= LIMIT) return res.status(200).json({ success: true, limited: true });
  } catch {
    /* ข้าม */
  }

  let row = null;
  try {
    const m = /^Bearer\s+(.+)$/i.exec(req.headers.authorization || '');
    const payload = m ? verifyToken(m[1].trim()) : null;
    if (payload) {
      const r = await getUserRowById(payload.sub);
      if (r && !isDisabledRow(r) && normalizeEmail(r.mt5_server) === normalizeEmail(payload.email)) row = r;
    }
  } catch {
    /* ไม่ระบุตัวตน */
  }

  const detail =
    kind === 'help_ask'
      ? { q, top: txt(b.top, 40), t: txt(b.t, 120), s: Math.round(Number(b.s || 0) * 100) / 100, ok: !!b.ok, page: txt(b.page, 80), sid: txt(b.sid, 24) }
      : { q, top: txt(b.top, 40), v: b.v === 'up' ? 'up' : 'down', sid: txt(b.sid, 24) };
  await logActivity({ userId: row?.id, email: row?.mt5_server, event: kind, detail: JSON.stringify(detail), ip });
  return res.status(200).json({ success: true });
}
