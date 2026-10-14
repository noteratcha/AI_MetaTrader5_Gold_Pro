// ปฏิทินเศรษฐกิจรายสัปดาห์ (สาธารณะ) — ใช้ร่วมกันทั้งเว็บและ Desktop App
// ต้นทางจำกัดจำนวนครั้ง (HTTP 429) จึง cache ทั้งในหน่วยความจำและที่ CDN ของ Vercel 30 นาที
// ค่าจริง (actual): feed ForexFactory ไม่มี → คำนวณจากข้อมูลทางการสหรัฐบน FRED (ฟรี · env FRED_API_KEY)
//   เฉพาะข่าว USD ที่มีซีรีส์ตรงกัน (CPI · PPI · ยอดค้าปลีก · การจ้างงาน · Claims · PCE · GDP · ฯลฯ)
//   ใช้ค่าล่าสุดเมื่อ FRED อัปเดตตั้งแต่วันที่ข่าวออก (realtime_start) — ยังไม่อัปเดต = ยังไม่แสดง
//   ช่วง 3 ชม. หลังข่าวออกที่ยังไม่มีค่าจริง ดึงใหม่ทุก 1 นาที (โปรแกรมโหลดปฏิทินทุก 1 นาทีช่วงนี้ · ผู้ใช้สั่ง 14 ต.ค. 2026)
const FEED_URL = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json';
const FRED_URL = 'https://api.stlouisfed.org/fred/series/observations';
const CACHE_MS = 30 * 60 * 1000;
const FAST_MS = 60 * 1000;
const SERIES_MS = 6 * 60 * 60 * 1000;

let cache = { events: null, fetchedAt: 0 };
const seriesCache = new Map();   // id → { obs: [{date, value, rt}], fetchedAt }

// ชื่อข่าว ForexFactory → ซีรีส์ FRED + วิธีคิด (mom = % เทียบเดือนก่อน · yoy = % เทียบปีก่อน · diff = ส่วนต่าง · level = ค่าล่าสุด · rate = รายวัน)
// unit: K = FRED เป็นหน่วยคน → แสดงหลักพัน · Kth = FRED เป็นหลักพันอยู่แล้ว · Mth = FRED เป็นหลักพัน → แสดงเป็นล้าน · % = ร้อยละ
const FRED_MAP = [
  [/^CPI m\/m$/i, 'CPIAUCSL', 'mom'],
  [/^Core CPI m\/m$/i, 'CPILFESL', 'mom'],
  [/^CPI y\/y$/i, 'CPIAUCNS', 'yoy'],
  [/^Core CPI y\/y$/i, 'CPILFENS', 'yoy'],
  [/^PPI m\/m$/i, 'PPIFIS', 'mom'],
  [/^Core PPI m\/m$/i, 'PPIFES', 'mom'],
  [/^Retail Sales m\/m$/i, 'RSAFS', 'mom'],
  [/^Core Retail Sales m\/m$/i, 'RSFSXMV', 'mom'],
  [/^Unemployment Claims$/i, 'ICSA', 'level', 'K'],
  [/^Non-Farm Employment Change$/i, 'PAYEMS', 'diff', 'Kth'],
  [/^Unemployment Rate$/i, 'UNRATE', 'level', '%'],
  [/^Average Hourly Earnings m\/m$/i, 'CES0500000003', 'mom'],
  [/^Core PCE Price Index m\/m$/i, 'PCEPILFE', 'mom'],
  [/^PCE Price Index m\/m$/i, 'PCEPI', 'mom'],
  [/^Personal Spending m\/m$/i, 'PCE', 'mom'],
  [/^Personal Income m\/m$/i, 'PI', 'mom'],
  [/^(Advance|Prelim|Final) GDP q\/q$/i, 'A191RL1Q225SBEA', 'level', '%'],
  [/^Philly Fed Manufacturing Index$/i, 'GACDFSA066MSFRBPHI', 'level'],
  [/^Empire State Manufacturing Index$/i, 'GACDINA066MNFRBNY', 'level'],
  [/^Durable Goods Orders m\/m$/i, 'DGORDER', 'mom'],
  [/^Core Durable Goods Orders m\/m$/i, 'ADXTNO', 'mom'],
  [/^Industrial Production m\/m$/i, 'INDPRO', 'mom'],
  [/^JOLTS Job Openings$/i, 'JTSJOL', 'level', 'Mth'],
  [/^Building Permits$/i, 'PERMIT', 'level', 'Mth'],
  [/^Housing Starts$/i, 'HOUST', 'level', 'Mth'],
  [/^Federal Funds Rate$/i, 'DFEDTARU', 'rate', '%'],
];

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

const fredSpec = (e) => (e.currency === 'USD' ? FRED_MAP.find(([re]) => re.test(e.title)) : null);
// วันที่ข่าวออกตามเวลานิวยอร์ก (feed ให้ ISO พร้อม offset เช่น 2026-10-14T08:30:00-04:00)
const etDate = (iso) => String(iso).slice(0, 10);

async function fredSeries(id, force) {
  const c = seriesCache.get(id);
  if (c && Date.now() - c.fetchedAt < (force ? FAST_MS : SERIES_MS)) return c.obs;
  const key = String(process.env.FRED_API_KEY || '').trim();
  if (!key) return null;
  try {
    const r = await fetch(`${FRED_URL}?series_id=${id}&api_key=${encodeURIComponent(key)}&file_type=json&sort_order=desc&limit=15`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const j = await r.json();
    const obs = (j.observations || []).map((o) => ({ date: o.date, value: Number(o.value), rt: o.realtime_start }))
      .filter((o) => Number.isFinite(o.value));
    seriesCache.set(id, { obs, fetchedAt: Date.now() });
    return obs;
  } catch (err) {
    console.warn(`[api/calendar] FRED ${id} failed:`, err.message);
    if (c) c.fetchedAt = Date.now();
    return c ? c.obs : null;
  }
}

/** ทศนิยมตามตัวเลขคาด/ครั้งก่อนของข่าวนั้น (เช่น 0.25% → 2 ตำแหน่ง) */
function decimalsOf(e, fallback) {
  const m = /\.(\d+)/.exec(String(e.forecast || e.previous || '').replace(/[%KMBT]\s*$/i, ''));
  return m ? m[1].length : fallback;
}

function computeActual(e, spec, obs) {
  const [, , how, unit] = spec;
  if (!obs || !obs.length) return '';
  const last = obs[0];
  const day = etDate(e.date);
  // ต้องเป็นตัวเลขรอบใหม่: FRED อัปเดตตั้งแต่วันข่าวออก (รายวัน: ข้อมูลของวันนั้นขึ้นไป)
  if (how === 'rate' ? last.date < day : last.rt < day) return '';
  let v;
  if (how === 'mom' || how === 'diff') {
    const prev = obs.find((o) => o.date < last.date);
    if (!prev) return '';
    v = how === 'mom' ? (last.value / prev.value - 1) * 100 : last.value - prev.value;
  } else if (how === 'yoy') {
    const d = new Date(`${last.date}T00:00:00Z`);
    d.setUTCFullYear(d.getUTCFullYear() - 1);
    const ago = obs.find((o) => o.date === d.toISOString().slice(0, 10));
    if (!ago) return '';
    v = (last.value / ago.value - 1) * 100;
  } else {
    v = last.value;
  }
  if (unit === 'K') return `${Math.round(v / 1000)}K`;
  if (unit === 'Kth') return `${Math.round(v)}K`;
  if (unit === 'Mth') return `${(v / 1000).toFixed(2)}M`;
  const pct = how === 'mom' || how === 'yoy' || unit === '%';
  return `${v.toFixed(decimalsOf(e, 1))}${pct ? '%' : ''}`;
}

async function fillActuals(events) {
  const now = Date.now();
  const need = new Map();   // id → ดึงถี่ (ข่าวเพิ่งออกใน 3 ชม.)
  for (const e of events) {
    const spec = fredSpec(e);
    const t = new Date(e.date).getTime();
    if (!spec || t > now) continue;
    need.set(spec[1], need.get(spec[1]) || now - t <= 3 * 60 * 60 * 1000);
  }
  const got = new Map();
  await Promise.all([...need].map(async ([id, force]) => got.set(id, await fredSeries(id, force))));
  return events.map((e) => {
    const spec = fredSpec(e);
    if (!spec) return e;
    // fred: true = ข่าวนี้จะมีค่าจริงจาก FRED (โปรแกรมโหลดถี่เฉพาะข่าวเหล่านี้)
    if (new Date(e.date).getTime() > now) return { ...e, fred: true };
    return { ...e, fred: true, actual: computeActual(e, spec, got.get(spec[1])) };
  });
}

/** ข่าวที่ออกแล้วใน 3 ชม. แต่ยังไม่มีค่าจริง → ให้ CDN เก็บแค่ 1 นาที */
function waitingActual(events) {
  const now = Date.now();
  return events.some((e) => {
    const t = new Date(e.date).getTime();
    return fredSpec(e) && t <= now && now - t <= 3 * 60 * 60 * 1000 && !e.actual;
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

  const events = await fillActuals(cache.events);
  res.setHeader('Cache-Control', waitingActual(events) ? 'public, s-maxage=60' : 'public, s-maxage=1800, stale-while-revalidate=86400');
  return res.status(200).json({
    success: true,
    updatedAt: new Date(cache.fetchedAt).toISOString(),
    actualSource: 'FRED (Federal Reserve Bank of St. Louis)',
    events,
  });
}
