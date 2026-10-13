import { allowMethods } from '../../lib/server/auth';
import { getAdminClient } from '../../lib/server/supabaseAdmin';

// ตัวเลขสะสมสาธารณะ (แสดงท้ายเว็บ): จำนวนครั้งที่เริ่มบอท (นับทุกบอท/ทุกหน้าต่าง) · จำนวนครั้งที่เข้าชมเว็บ
// นับจาก user_activity (bot_start / web_visit) · cache ที่ CDN 5 นาที
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const sb = getAdminClient();
  const count = async (event) => {
    const { count: n, error } = await sb.from('user_activity').select('id', { count: 'exact', head: true }).eq('event', event);
    return error ? null : n || 0;
  };
  const [botRuns, webVisits] = await Promise.all([count('bot_start'), count('web_visit')]);
  res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
  return res.status(200).json({ success: true, botRuns, webVisits });
}
