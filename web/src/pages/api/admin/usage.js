import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireAdmin } from '../../../lib/server/auth';
import { githubDownloadStats, USAGE_EVENTS } from '../../../lib/server/usage';

const DAY_MS = 86400000;
const bkkDay = (iso) => new Date(new Date(iso).getTime() + 7 * 3600000).toISOString().slice(0, 10);

// สถิติดาวน์โหลด + การเข้าใช้โปรแกรม AI Gold Commander Pro ย้อนหลัง 30 วัน (แอดมินเท่านั้น)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  const now = Date.now();
  const since = new Date(now - 30 * DAY_MS).toISOString();
  const supabase = getAdminClient();
  const head = { count: 'exact', head: true };
  const [rows, allDownloads, allOpens, github] = await Promise.all([
    supabase
      .from('user_activity')
      .select('user_id, email, event, detail, created_at')
      .in('event', USAGE_EVENTS)
      .gte('created_at', since)
      .order('created_at', { ascending: false })
      .limit(20000),
    supabase.from('user_activity').select('id', head).eq('event', 'app_download'),
    supabase.from('user_activity').select('id', head).eq('event', 'app_open'),
    githubDownloadStats(),
  ]);
  if (rows.error) return res.status(500).json({ success: false, error: 'อ่านข้อมูลกิจกรรมไม่สำเร็จ' });

  const data = rows.data || [];
  const todayKey = bkkDay(new Date(now).toISOString());
  const inDays = (r, d) => new Date(r.created_at).getTime() >= now - d * DAY_MS;
  const of = (ev) => data.filter((r) => r.event === ev);
  const uniq = (list) => new Set(list.map((r) => r.user_id || r.email).filter(Boolean)).size;
  const opens = of('app_open');
  const downloads = of('app_download');
  const starts = of('bot_start');

  // กราฟรายวัน 14 วัน (เวลาไทย)
  const daily = [];
  for (let i = 13; i >= 0; i--) {
    const key = bkkDay(new Date(now - i * DAY_MS).toISOString());
    const dayRows = data.filter((r) => bkkDay(r.created_at) === key);
    daily.push({
      day: key,
      downloads: dayRows.filter((r) => r.event === 'app_download').length,
      opens: dayRows.filter((r) => r.event === 'app_open').length,
      users: uniq(dayRows.filter((r) => r.event === 'app_open' || r.event === 'bot_start')),
    });
  }

  // เวอร์ชันที่ผู้ใช้เปิดล่าสุด (1 คน นับ 1 ครั้ง)
  const latestVersionByUser = {};
  for (const r of opens) {
    const who = r.user_id || r.email;
    const v = /v(\d{4}\.\d{4}\.\d{4})/.exec(r.detail || '')?.[1];
    if (who && v && !latestVersionByUser[who]) latestVersionByUser[who] = v;
  }
  const versionCounts = {};
  Object.values(latestVersionByUser).forEach((v) => (versionCounts[v] = (versionCounts[v] || 0) + 1));

  return res.status(200).json({
    success: true,
    downloads: {
      allTime: allDownloads.count || 0,
      today: downloads.filter((r) => bkkDay(r.created_at) === todayKey).length,
      last7: downloads.filter((r) => inDays(r, 7)).length,
      last30: downloads.length,
      github,
    },
    usage: {
      opensAllTime: allOpens.count || 0,
      opensToday: opens.filter((r) => bkkDay(r.created_at) === todayKey).length,
      usersToday: uniq(data.filter((r) => bkkDay(r.created_at) === todayKey && r.event !== 'app_download')),
      users7: uniq(data.filter((r) => inDays(r, 7) && r.event !== 'app_download')),
      users30: uniq(data.filter((r) => r.event !== 'app_download')),
      botStarts7: starts.filter((r) => inDays(r, 7)).length,
      machines30: new Set(opens.map((r) => /เครื่อง (\w+)/.exec(r.detail || '')?.[1]).filter(Boolean)).size,
      versions: Object.entries(versionCounts)
        .map(([version, users]) => ({ version, users }))
        .sort((a, b) => (a.version < b.version ? 1 : -1)),
    },
    daily,
    recent: data.slice(0, 15),
  });
}
