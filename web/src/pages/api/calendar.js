// ปฏิทินเศรษฐกิจรายสัปดาห์ (สาธารณะ) — ใช้ร่วมกันทั้งเว็บและ Desktop App
// ต้นทางจำกัดจำนวนครั้ง (HTTP 429) จึง cache ทั้งในหน่วยความจำและที่ CDN ของ Vercel 30 นาที
const FEED_URL = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json';
const CACHE_MS = 30 * 60 * 1000;

let cache = { events: null, fetchedAt: 0 };

function normalize(list) {
  return (Array.isArray(list) ? list : [])
    .map((e) => ({
      title: String(e.title || '').trim(),
      currency: String(e.country || e.currency || '').toUpperCase(),
      date: e.date,
      impact: String(e.impact || 'Low'),
      forecast: String(e.forecast || ''),
      previous: String(e.previous || ''),
    }))
    .filter((e) => e.title && e.date && !Number.isNaN(new Date(e.date).getTime()))
    .sort((a, b) => new Date(a.date) - new Date(b.date));
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

  res.setHeader('Cache-Control', 'public, s-maxage=1800, stale-while-revalidate=86400');
  return res.status(200).json({
    success: true,
    updatedAt: new Date(cache.fetchedAt).toISOString(),
    events: cache.events,
  });
}
