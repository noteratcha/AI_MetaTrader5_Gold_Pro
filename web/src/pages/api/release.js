import { getAdminClient } from '../../lib/server/supabaseAdmin';

// เวอร์ชันล่าสุดของ Desktop App (สาธารณะ) — ใช้แสดงปุ่มดาวน์โหลดบนเว็บ
export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ success: false, error: 'Method not allowed' });
  const { data } = await getAdminClient()
    .from('app_releases')
    .select('version, download_url, changelog, released_at')
    .order('released_at', { ascending: false })
    .limit(1)
    .maybeSingle();
  res.setHeader('Cache-Control', 'public, max-age=300');
  return res.status(200).json({ success: true, release: data || null });
}
