import { allowMethods } from '../../lib/server/auth';
import { getAdminClient } from '../../lib/server/supabaseAdmin';

// ตัวเลขสะสมสาธารณะ (ความน่าเชื่อถือ — แสดงหน้าแรกและท้ายเว็บ) · cache ที่ CDN 5 นาที
// - botRuns: จำนวนครั้งที่เริ่มบอท (นับทุกบอท/ทุกหน้าต่าง · user_activity bot_start)
// - webVisits: จำนวนครั้งที่เข้าชมเว็บ (1 ครั้งต่อการเปิดแท็บ · user_activity web_visit)
// - totalHours: ชั่วโมงที่บอทของผู้ใช้ทุกคนทำงานสะสม (online_progress: รอบละ 100 ชม. + นาทีรอบปัจจุบัน)
const GOAL_MIN = 100 * 60;

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const sb = getAdminClient();
  const count = async (event) => {
    const { count: n, error } = await sb.from('user_activity').select('id', { count: 'exact', head: true }).eq('event', event);
    return error ? null : n || 0;
  };
  const hours = async () => {
    const { data, error } = await sb.from('online_progress').select('minutes, cycles');
    if (error) return null;
    const minutes = (data || []).reduce((a, r) => a + (Number(r.cycles) || 0) * GOAL_MIN + (Number(r.minutes) || 0), 0);
    return Math.floor(minutes / 60);
  };
  const [botRuns, webVisits, totalHours] = await Promise.all([count('bot_start'), count('web_visit'), hours()]);
  res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
  return res.status(200).json({ success: true, botRuns, webVisits, totalHours });
}
