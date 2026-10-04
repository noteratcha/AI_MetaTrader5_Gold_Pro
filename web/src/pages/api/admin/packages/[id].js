import { getAdminClient } from '../../../../lib/server/supabaseAdmin';
import { allowMethods, requireAdmin } from '../../../../lib/server/auth';
import { packageToRow, rowToPackage, validatePackage } from '../../../../lib/server/catalog';
import { logActivity } from '../../../../lib/server/activity';

// PATCH แก้ไขแพ็กเกจ · DELETE ลบ (ถ้ามีคำสั่งซื้ออ้างอิงอยู่ จะปิดการขายแทนการลบ)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['PATCH', 'DELETE'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  const id = Number(req.query.id);
  if (!Number.isInteger(id) || id < 1) return res.status(400).json({ success: false, error: 'รหัสแพ็กเกจไม่ถูกต้อง' });
  const supabase = getAdminClient();
  const { data: current } = await supabase.from('packages').select('*').eq('id', id).maybeSingle();
  if (!current) return res.status(404).json({ success: false, error: 'ไม่พบแพ็กเกจ' });

  if (req.method === 'DELETE') {
    const { count } = await supabase.from('orders').select('order_id', { count: 'exact', head: true }).eq('package_id', id);
    if (count) {
      await supabase.from('packages').update({ is_active: false, updated_at: new Date().toISOString() }).eq('id', id);
      await logActivity({ event: 'admin_package_disable', detail: `ปิดการขาย ${current.name} (มีคำสั่งซื้ออ้างอิง ${count} รายการ)`, actor: auth.user.email });
      return res.status(200).json({ success: true, deactivated: true, message: 'แพ็กเกจนี้มีคำสั่งซื้ออ้างอิงอยู่ จึงปิดการขายแทนการลบ' });
    }
    const { error } = await supabase.from('packages').delete().eq('id', id);
    if (error) return res.status(500).json({ success: false, error: 'ลบแพ็กเกจไม่สำเร็จ' });
    await logActivity({ event: 'admin_package_delete', detail: `ลบแพ็กเกจ ${current.name}`, actor: auth.user.email });
    return res.status(200).json({ success: true });
  }

  const merged = { ...rowToPackage(current), ...(req.body || {}) };
  const err = validatePackage(merged);
  if (err) return res.status(400).json({ success: false, error: err });
  const { data, error } = await supabase.from('packages').update(packageToRow(merged)).eq('id', id).select().maybeSingle();
  if (error || !data) return res.status(500).json({ success: false, error: 'บันทึกแพ็กเกจไม่สำเร็จ' });
  await logActivity({ event: 'admin_package_update', detail: `แก้ไขแพ็กเกจ ${data.name}`, actor: auth.user.email });
  return res.status(200).json({ success: true, package: rowToPackage(data) });
}
