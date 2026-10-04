import { getAdminClient } from '../../lib/server/supabaseAdmin';

// เวอร์ชันล่าสุดของ Desktop App (สาธารณะ)
// แหล่งหลัก: GitHub Releases (อัปโหลด ZIP ที่นั่นที่เดียวพอ) — สำรอง: ตาราง app_releases
const GITHUB_REPO = process.env.GITHUB_RELEASES_REPO || 'noteratcha/AI_MetaTrader5_Gold_Pro';
const RELEASES_PAGE = `https://github.com/${GITHUB_REPO}/releases/latest`;
const CACHE_MS = 10 * 60 * 1000;

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
  const asset = (d.assets || []).find((a) => /\.zip$/i.test(a.name)) || (d.assets || [])[0];
  if (!asset) return null;
  const sha = /SHA-256:\s*`?([a-f0-9]{64})`?/i.exec(d.body || '');
  return {
    version: String(d.tag_name || '').replace(/^v/i, ''),
    download_url: asset.browser_download_url,
    file_name: asset.name,
    size_bytes: asset.size,
    checksum_sha256: sha ? sha[1] : null,
    changelog: d.body || '',
    released_at: d.published_at,
    page_url: d.html_url,
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

  if (!cache.release || Date.now() - cache.at > CACHE_MS) {
    const [gh, db] = await Promise.all([fromGitHub().catch(() => null), fromDatabase().catch(() => null)]);
    const candidates = [gh, db].filter((r) => r && isPublicUrl(r.download_url));
    candidates.sort((a, b) => (versionKey(b.version) > versionKey(a.version) ? 1 : -1));
    const best = candidates[0] || (gh || db ? { ...(gh || db), download_url: RELEASES_PAGE } : null);
    if (best) cache = { release: { ...best, releases_page: RELEASES_PAGE }, at: Date.now() };
  }

  res.setHeader('Cache-Control', 'public, s-maxage=600, stale-while-revalidate=3600');
  return res.status(200).json({ success: true, release: cache.release || { download_url: RELEASES_PAGE, releases_page: RELEASES_PAGE } });
}
