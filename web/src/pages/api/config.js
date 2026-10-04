import { getEnabledPlans } from '../../lib/server/catalog';

// ค่าที่ Desktop Bot ต้องใช้ (สาธารณะ อ่านอย่างเดียว): แผนเทรดที่แอดมินเปิด/ปิด
export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ success: false, error: 'Method not allowed' });
  const { plans, updatedAt } = await getEnabledPlans();
  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({ success: true, enabledPlans: plans, updatedAt });
}
