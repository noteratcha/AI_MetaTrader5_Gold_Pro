// ปฏิทินเศรษฐกิจรายสัปดาห์ (สาธารณะ) — ใช้ร่วมกันทั้งเว็บและ Desktop App
// ต้นทางจำกัดจำนวนครั้ง (HTTP 429) จึง cache ทั้งในหน่วยความจำและที่ CDN ของ Vercel 30 นาที
// ค่าจริง (Actual): feed ForexFactory ไม่มี → เติมจาก JBlanked News API (แหล่ง ForexFactory เดียวกัน · env JBLANKED_API_KEY)
//   ช่วง 2 ชม. หลังข่าวผลกระทบสูง/กลางออก ดึงใหม่ทุก 5 นาที (โควตาฟรีของ JBlanked ≈ 1 ครั้ง/5 นาที)
const FEED_URL = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json';
const JB_URL = 'https://www.jblanked.com/news/api/forex-factory/calendar/week/';
const CACHE_MS = 30 * 60 * 1000;
const FAST_MS = 5 * 60 * 1000;
const MATCH_MS = 14 * 60 * 60 * 1000;   // ไม่รู้เขตเวลาของ JBlanked แน่ชัด → จับคู่ชื่อเดียวกันที่ใกล้เวลาที่สุดภายใน 14 ชม.

let cache = { events: null, fetchedAt: 0 };
let jb = { list: null, fetchedAt: 0, error: '', sample: null };

function normalize(list) {
  return (Array.isArray(list) ? list : [])
    .map((e) => ({
      title: String(e.title || '').trim(),
      currency: String(e.country || e.currency || '').toUpperCase(),
      date: e.date,
      impact: String(e.impact || 'Low'),
      forecast: String(e.forecast || ''),
      previous: String(e.previous || ''),
      actual: '',
    }))
    .filter((e) => e.title && e.date && !Number.isNaN(new Date(e.date).getTime()))
    .sort((a, b) => new Date(a.date) - new Date(b.date));
}

const nameKey = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '');

function jbTime(v) {
  // "2024.02.08 15:30:00" หรือ ISO → epoch ms (ไม่มีเขตเวลา = ถือเป็น UTC แล้วใช้ช่วงจับคู่กว้าง)
  const s = String(v || '').trim().replace(/^(\d{4})\.(\d{2})\.(\d{2})/, '$1-$2-$3').replace(' ', 'T');
  const t = Date.parse(/[zZ]|[+-]\d{2}:?\d{2}$/.test(s) ? s : `${s}Z`);
  return Number.isNaN(t) ? null : t;
}

/** ค่าจริงจาก JBlanked เป็นตัวเลขหรือข้อความ → ใส่หน่วยตาม forecast/previous ของข่าวนั้น (%, K, M, B, T) */
function formatActual(v, ref) {
  if (v === null || v === undefined || v === '') return '';
  if (typeof v === 'string' && /[^\d.+-]/.test(v.trim())) return v.trim();
  const n = Number(v);
  if (!Number.isFinite(n)) return '';
  const unit = (/([%KMBT])\s*$/i.exec(ref || '') || [])[1] || '';
  const dec = (/\.(\d+)/.exec(String(ref || '').replace(/[%KMBT]\s*$/i, '')) || [])[1];
  const txt = dec !== undefined ? n.toFixed(dec.length) : String(n);
  return `${txt}${unit}`;
}

async function refreshActuals() {
  const key = String(process.env.JBLANKED_API_KEY || '').trim();
  if (!key) {
    jb.error = 'no key';
    return;
  }
  try {
    const r = await fetch(JB_URL, { headers: { 'Content-Type': 'application/json', Authorization: `Api-Key ${key}` } });
    if (!r.ok) throw new Error(`HTTP ${r.status} ${(await r.text().catch(() => '')).slice(0, 160)}`);
    const j = await r.json();
    const list = Array.isArray(j) ? j : j?.data || j?.results || j?.events || [];
    if (!Array.isArray(list)) throw new Error('unexpected format');
    jb = { list, fetchedAt: Date.now(), error: '', sample: list.find((x) => x && (x.Actual ?? x.actual) !== undefined) || list[0] || null };
  } catch (err) {
    jb.error = err.message;
    jb.fetchedAt = Date.now();   // ไม่ยิงซ้ำถี่ ๆ เมื่อพัง
    console.warn('[api/calendar] JBlanked fetch failed:', err.message);
  }
}

function mergeActuals(events) {
  if (!Array.isArray(jb.list) || !jb.list.length) return events;
  const now = Date.now();
  const byName = new Map();
  for (const x of jb.list) {
    const k = `${String(x.Currency ?? x.currency ?? '').toUpperCase()}|${nameKey(x.Name ?? x.name ?? x.title)}`;
    const t = jbTime(x.Date ?? x.date);
    if (t === null) continue;
    if (!byName.has(k)) byName.set(k, []);
    byName.get(k).push({ t, actual: x.Actual ?? x.actual });
  }
  return events.map((e) => {
    const t = new Date(e.date).getTime();
    if (t > now) return { ...e, actual: '' };   // ข่าวยังไม่ออก — บางแหล่งใส่ 0 ไว้ล่วงหน้า
    const cands = byName.get(`${e.currency}|${nameKey(e.title)}`) || [];
    let best = null;
    for (const c of cands) {
      const d = Math.abs(c.t - t);
      if (d <= MATCH_MS && (!best || d < best.d)) best = { ...c, d };
    }
    return { ...e, actual: best ? formatActual(best.actual, e.forecast || e.previous) : '' };
  });
}

/** มีข่าว USD ผลกระทบสูง/กลางที่เพิ่งออกใน 2 ชม. → ดึงค่าจริงถี่ขึ้น */
function newsJustReleased(events) {
  const now = Date.now();
  return (events || []).some((e) => {
    const t = new Date(e.date).getTime();
    return /high|medium/i.test(e.impact) && t <= now && now - t <= 2 * 60 * 60 * 1000;
  });
}

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ success: false, error: 'Method not allowed' });

  const fresh = cache.events && Date.now() - cache.fetchedAt < CACHE_MS;
  if (!fresh) {
    try {
      const r = await fetch(FEED_URL, { headers: { 'User-Agent': 'GoldBot24/1.0 (+https://goldbot24.vercel.app)' } });
      if (!r.ok) throw new Error(`feed HTTP ${r.status}`);
      const events = normalize(await r.json());
      if (events.length) cache = { events, fetchedAt: Date.now() };
    } catch (err) {
      console.warn('[api/calendar] feed fetch failed:', err.message);
    }
  }

  if (!cache.events) {
    res.setHeader('Cache-Control', 'no-store');
    return res.status(503).json({ success: false, error: 'ยังโหลดปฏิทินข่าวไม่ได้ กรุณาลองใหม่ภายหลัง' });
  }

  const hot = newsJustReleased(cache.events);
  if (Date.now() - jb.fetchedAt >= (hot ? FAST_MS : CACHE_MS)) await refreshActuals();
  const events = mergeActuals(cache.events);

  if (req.query.probe === 'fred') {   // ชั่วคราว: ทดสอบ FRED
    const key = String(process.env.FRED_API_KEY || '').trim();
    const out = { keyLen: key.length };
    for (const id of ['CPIAUCSL', 'CPILFESL', 'CPIAUCNS', 'CPILFENS', 'PPIFIS', 'RSAFS', 'ICSA', 'PAYEMS']) {
      try {
        const r = await fetch(`https://api.stlouisfed.org/fred/series/observations?series_id=${id}&api_key=${encodeURIComponent(key)}&file_type=json&sort_order=desc&limit=14`);
        const j = await r.json();
        out[id] = r.ok ? (j.observations || []).map((o) => `${o.date}=${o.value} (rt ${o.realtime_start})`) : j;
      } catch (e) { out[id] = e.message; }
    }
    res.setHeader('Cache-Control', 'no-store');
    return res.status(200).json(out);
  }
  if (req.query.debug === '1') {
    res.setHeader('Cache-Control', 'no-store');
    return res.status(200).json({
      success: true, jbError: jb.error, keyLen: String(process.env.JBLANKED_API_KEY || '').trim().length, jbCount: Array.isArray(jb.list) ? jb.list.length : 0,
      withActual: events.filter((e) => e.actual).length,
    });
  }

  res.setHeader('Cache-Control', `public, s-maxage=${hot ? 300 : 1800}, stale-while-revalidate=86400`);
  return res.status(200).json({
    success: true,
    updatedAt: new Date(Math.max(cache.fetchedAt, jb.fetchedAt || 0)).toISOString(),
    actualSource: Array.isArray(jb.list) && jb.list.length ? 'jblanked' : null,
    events,
  });
}
