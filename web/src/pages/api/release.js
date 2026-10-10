import { getAdminClient } from '../../lib/server/supabaseAdmin';

// เวอร์ชันล่าสุดของ Desktop App (สาธารณะ)
// แหล่งหลัก: GitHub Releases (อัปโหลด ZIP ที่นั่นที่เดียวพอ) — สำรอง: ตาราง app_releases
const GITHUB_REPO = process.env.GITHUB_RELEASES_REPO || 'noteratcha/AI_MetaTrader5_Gold_Pro';
const RELEASES_PAGE = `https://github.com/${GITHUB_REPO}/releases/latest`;
const CACHE_MS = 60 * 1000; // แคชสั้น 60 วินาที เพื่อให้ผู้ใช้เห็นแพตช์ใหม่ได้รวดเร็วทันใจ

let cache = { release: null, at: 0 };

const isPublicUrl = (url) => typeof url === 'string' && /^https:\/\//i.test(url) && !/localhost|127\.0\.0\.1/i.test(url);

function versionKey(v) {
  return String(v || '')
    .replace(/^v/i, '')
    .split('.')
    .map((n) => String(parseInt(n, 10) || 0).padStart(6, '0'))
    .join('.');
}

async function fromGitHub() {
  const r = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases/latest`, {
    headers: { Accept: 'application/vnd.github+json', 'User-Agent': 'GoldBot24' },
  });
  if (!r.ok) throw new Error(`GitHub HTTP ${r.status}`);
  const d = await r.json();
  // ตัวติดตั้ง (Setup .exe) เป็นไฟล์หลัก · ZIP เป็นทางเลือกแบบไม่ต้องติดตั้ง
  const assets = d.assets || [];
  const zip = assets.find((a) => /\.zip$/i.test(a.name));
  const asset = assets.find((a) => /setup.*\.exe$/i.test(a.name)) || zip || assets[0];
  if (!asset) return null;
  const sha = /SHA-256:\s*`?([a-f0-9]{64})`?/i.exec(d.body || '');
  return {
    version: String(d.tag_name || '').replace(/^v/i, ''),
    download_url: asset.browser_download_url,
    file_name: asset.name,
    size_bytes: asset.size,
    is_installer: /\.exe$/i.test(asset.name),
    zip_url: zip && zip !== asset ? zip.browser_download_url : null,
    checksum_sha256: sha ? sha[1] : null,
    changelog: d.body || '',
    released_at: d.published_at,
    page_url: d.html_url,
  };
}

// สำรองเมื่อ GitHub API ใช้ไม่ได้ (เช่น ติด rate limit 60 ครั้ง/ชม. ต่อ IP ที่ Vercel ใช้ร่วมกัน):
// อ่านแท็กล่าสุดจาก redirect ของหน้า releases/latest (ไม่นับ rate limit) แล้วสร้างลิงก์จากชื่อไฟล์มาตรฐานของ build_dist.py
async function fromGitHubRedirect() {
  const r = await fetch(RELEASES_PAGE, { method: 'HEAD', redirect: 'manual', headers: { 'User-Agent': 'GoldBot24' } });
  const tag = /\/releases\/tag\/([^/?#]+)/.exec(r.headers.get('location') || '')?.[1];
  if (!tag) return null;
  const v = decodeURIComponent(tag).replace(/^v/i, '');
  const base = `https://github.com/${GITHUB_REPO}/releases/download/v${v}`;
  return {
    version: v,
    download_url: `${base}/GoldBot24_Setup_v${v}.exe`,
    file_name: `GoldBot24_Setup_v${v}.exe`,
    is_installer: true,
    zip_url: `${base}/AI_Gold_Commander_Pro_v${v}.zip`,
    changelog: '',
    page_url: `https://github.com/${GITHUB_REPO}/releases/tag/v${v}`,
  };
}

async function fromDatabase() {
  const { data } = await getAdminClient()
    .from('app_releases')
    .select('version, download_url, checksum_sha256, changelog, released_at')
    .order('released_at', { ascending: false })
    .limit(1)
    .maybeSingle();
  if (!data) return null;
  return { ...data, download_url: isPublicUrl(data.download_url) ? data.download_url : null };
}

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ success: false, error: 'Method not allowed' });

  const force = req.query.force || req.query.t || req.headers['cache-control']?.includes('no-cache');
  if (force || !cache.release || Date.now() - cache.at > CACHE_MS) {
    const [api, db] = await Promise.all([fromGitHub().catch(() => null), fromDatabase().catch(() => null)]);
    const gh = api || (await fromGitHubRedirect().catch(() => null));
    const candidates = [gh, db].filter((r) => r && isPublicUrl(r.download_url));
    candidates.sort((a, b) => (versionKey(b.version) > versionKey(a.version) ? 1 : -1));
    const best = candidates[0] || (gh || db ? { ...(gh || db), download_url: RELEASES_PAGE } : null);
    if (best) cache = { release: { ...best, releases_page: RELEASES_PAGE }, at: Date.now() };
  }

  res.setHeader('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=120');
  return res.status(200).json({ success: true, release: cache.release || { download_url: RELEASES_PAGE, releases_page: RELEASES_PAGE } });
}
