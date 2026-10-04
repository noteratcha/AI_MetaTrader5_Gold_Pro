import { listPackages } from '../../lib/server/catalog';

// แพ็กเกจชั่วโมงที่เปิดขาย (สาธารณะ) — หน้าร้านอ่านจากที่นี่
export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ success: false, error: 'Method not allowed' });
  const { packages } = await listPackages();
  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({ success: true, packages });
}
