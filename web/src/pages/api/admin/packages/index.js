import { getAdminClient } from '../../../../lib/server/supabaseAdmin';
import { allowMethods, requireAdmin } from '../../../../lib/server/auth';
import { listPackages, packageToRow, rowToPackage, validatePackage } from '../../../../lib/server/catalog';
import { logActivity } from '../../../../lib/server/activity';

// GET  แพ็กเกจทั้งหมด (รวมที่ปิดขาย) · POST เพิ่มแพ็กเกจ
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET', 'POST'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  if (req.method === 'GET') {
    const { packages, source } = await listPackages({ includeInactive: true });
    return res.status(200).json({ success: true, packages, source });
  }

  const err = validatePackage(req.body || {});
  if (err) return res.status(400).json({ success: false, error: err });
  const { data, error } = await getAdminClient().from('packages').insert(packageToRow(req.body)).select().maybeSingle();
  if (error) return res.status(500).json({ success: false, error: 'เพิ่มแพ็กเกจไม่สำเร็จ (รัน supabase_admin_patch_02.sql แล้วหรือยัง?)' });
  await logActivity({ event: 'admin_package_create', detail: `เพิ่มแพ็กเกจ ${data.name} (${data.hours}+${data.bonus_hours} ชม. ฿${data.price_thb})`, actor: auth.user.email });
  return res.status(201).json({ success: true, package: rowToPackage(data) });
}
