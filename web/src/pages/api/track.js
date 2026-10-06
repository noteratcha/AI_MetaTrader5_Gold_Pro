import { allowMethods, clientIp, getUserRowById, isDisabledRow, normalizeEmail, verifyToken } from '../../lib/server/auth';
import { getAdminClient } from '../../lib/server/supabaseAdmin';
import { logActivity } from '../../lib/server/activity';
import { PUBLIC_USAGE_EVENTS, USAGE_EVENTS } from '../../lib/server/usage';

const clean = (v, max = 40) => String(v || '').replace(/[^\w.\-· ]/g, '').slice(0, max);
const DEDUPE_MS = 5 * 60 * 1000; // กดดาวน์โหลด/เปิดโปรแกรมซ้ำใน 5 นาทีนับครั้งเดียว

/**
 * บันทึกสถิติการใช้งาน: app_download (หน้า /download, ไม่ต้องล็อกอิน) ·
 * app_open / bot_start / bot_stop (โปรแกรม Desktop, ต้องมี Bearer)
 */
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['POST'])) return;
  const { event, version, file, machine, source } = req.body || {};
  if (!USAGE_EVENTS.includes(event)) return res.status(400).json({ success: false, error: 'event ไม่ถูกต้อง' });

  let row = null;
  try {
    const m = /^Bearer\s+(.+)$/i.exec(req.headers.authorization || '');
    const payload = m ? verifyToken(m[1].trim()) : null;
    if (payload) {
      const r = await getUserRowById(payload.sub);
      if (r && !isDisabledRow(r) && normalizeEmail(r.mt5_server) === normalizeEmail(payload.email)) row = r;
    }
  } catch {
    /* token ไม่ถูกต้อง → นับแบบไม่ระบุตัวตน (เฉพาะดาวน์โหลด) */
  }
  if (!row && !PUBLIC_USAGE_EVENTS.includes(event)) return res.status(401).json({ success: false, error: 'ต้องเข้าสู่ระบบ' });

  const ip = clientIp(req);
  const detail = [
    version ? `v${clean(version, 20)}` : null,
    file ? clean(file, 60) : null,
    machine ? `เครื่อง ${clean(machine, 12)}` : null,
    event === 'app_download' ? (source === 'desktop' ? 'อัปเดตจากโปรแกรม' : 'เว็บ') : null,
  ]
    .filter(Boolean)
    .join(' · ');

  if (event === 'app_download' || event === 'app_open') {
    try {
      let q = getAdminClient()
        .from('user_activity')
        .select('id')
        .eq('event', event)
        .gte('created_at', new Date(Date.now() - DEDUPE_MS).toISOString())
        .limit(1);
      q = row ? q.eq('user_id', String(row.id)) : q.eq('ip', String(ip).slice(0, 64));
      const { data } = await q;
      if (data?.length) return res.status(200).json({ success: true, deduped: true });
    } catch {
      /* ข้าม */
    }
  }

  await logActivity({ userId: row?.id, email: row?.mt5_server, event, detail, ip });
  return res.status(200).json({ success: true });
}
