// สถิติการดาวน์โหลดและการใช้งานโปรแกรม Desktop (เก็บใน user_activity)
export const USAGE_EVENTS = ['app_download', 'app_open', 'bot_start', 'bot_stop'];
export const PUBLIC_USAGE_EVENTS = ['app_download']; // ไม่ต้องเข้าสู่ระบบ

const GITHUB_REPO = process.env.GITHUB_RELEASES_REPO || 'noteratcha/AI_MetaTrader5_Gold_Pro';
let ghCache = { data: null, at: 0 };

/** ยอดดาวน์โหลดจริงจาก GitHub Releases (นับทุกช่องทาง รวมลิงก์ตรง) — cache 10 นาที */
export async function githubDownloadStats() {
  if (ghCache.data && Date.now() - ghCache.at < 600000) return ghCache.data;
  try {
    const r = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases?per_page=100`, {
      headers: { Accept: 'application/vnd.github+json', 'User-Agent': 'GoldBot24' },
    });
    if (!r.ok) return ghCache.data;
    const releases = await r.json();
    const perVersion = releases.map((rel) => {
      const assets = rel.assets || [];
      const count = (re) => assets.filter((a) => re.test(a.name)).reduce((t, a) => t + (a.download_count || 0), 0);
      return {
        version: String(rel.tag_name || '').replace(/^v/i, ''),
        publishedAt: rel.published_at,
        setup: count(/\.exe$/i),
        zip: count(/\.zip$/i),
      };
    });
    const data = {
      total: perVersion.reduce((t, v) => t + v.setup + v.zip, 0),
      setup: perVersion.reduce((t, v) => t + v.setup, 0),
      zip: perVersion.reduce((t, v) => t + v.zip, 0),
      perVersion: perVersion.slice(0, 15),
    };
    ghCache = { data, at: Date.now() };
    return data;
  } catch {
    return ghCache.data;
  }
}
