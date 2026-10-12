import { allowMethods } from '../../lib/server/auth';
import { listPublic } from '../../lib/server/announcements';

// ข่าวสาร/โปรโมชันที่กำลังแสดง (สาธารณะ) — เว็บ + โปรแกรม Gold Bot 24 ดึงจากที่นี่ · cache ที่ CDN 1 นาที
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const { items, error } = await listPublic(30);
  res.setHeader('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=300');
  if (error) return res.status(200).json({ success: true, items: [] });   // ยังไม่ได้รัน Patch 09
  return res.status(200).json({ success: true, items });
}
