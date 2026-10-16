import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireAdmin } from '../../../lib/server/auth';

const DAY_MS = 86400000;
const parse = (s) => {
  try {
    return JSON.parse(s || '{}');
  } catch {
    return {};
  }
};
// รวมคำถามที่พิมพ์ต่างกันเล็กน้อย (ช่องว่าง/เครื่องหมาย/ตัวพิมพ์)
const key = (q) => String(q || '').toLowerCase().replace(/[^฀-๿a-z0-9]+/g, '');

/** สรุปการถามผู้ช่วย (FAB) ย้อนหลัง N วัน — แอดมินเท่านั้น */
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;
  const days = Math.min(365, Math.max(1, Number(req.query.days) || 30));
  const since = new Date(Date.now() - days * DAY_MS).toISOString();
  const { data, error } = await getAdminClient()
    .from('user_activity')
    .select('email, event, detail, created_at')
    .in('event', ['help_ask', 'help_feedback'])
    .gte('created_at', since)
    .order('created_at', { ascending: false })
    .limit(20000);
  if (error) return res.status(500).json({ success: false, error: 'อ่านข้อมูลไม่สำเร็จ' });

  const asks = [];
  const fb = [];
  for (const r of data || []) {
    const d = parse(r.detail);
    if (r.event === 'help_ask') asks.push({ ...d, email: r.email, at: r.created_at });
    else fb.push({ ...d, email: r.email, at: r.created_at });
  }
  // คำถามยอดนิยม (รวมคำถามเดียวกัน)
  const groups = new Map();
  for (const a of asks) {
    const k = key(a.q);
    const g = groups.get(k) || { q: a.q, n: 0, ok: 0, top: a.top, t: a.t, last: a.at };
    g.n += 1;
    g.ok += a.ok ? 1 : 0;
    groups.set(k, g);
  }
  const top = [...groups.values()].sort((a, b) => b.n - a.n);
  // หัวข้อที่ถูกตอบบ่อย
  const topics = new Map();
  for (const a of asks.filter((x) => x.ok)) {
    const g = topics.get(a.top) || { top: a.top, t: a.t, n: 0, up: 0, down: 0 };
    g.n += 1;
    topics.set(a.top, g);
  }
  for (const f of fb) {
    const g = topics.get(f.top) || { top: f.top, t: f.top, n: 0, up: 0, down: 0 };
    g[f.v === 'up' ? 'up' : 'down'] += 1;
    topics.set(f.top, g);
  }
  const sessions = new Set(asks.map((a) => a.sid).filter(Boolean)).size;
  return res.status(200).json({
    success: true,
    days,
    summary: {
      asks: asks.length,
      sessions,
      found: asks.filter((a) => a.ok).length,
      up: fb.filter((f) => f.v === 'up').length,
      down: fb.filter((f) => f.v === 'down').length,
    },
    unanswered: top.filter((g) => g.ok === 0).slice(0, 200),
    disliked: fb.filter((f) => f.v === 'down').slice(0, 200),
    top: top.slice(0, 200),
    topics: [...topics.values()].sort((a, b) => b.n - a.n),
    recent: asks.slice(0, 300),
  });
}
