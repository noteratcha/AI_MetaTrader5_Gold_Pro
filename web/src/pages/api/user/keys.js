import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireUser } from '../../../lib/server/auth';
import { findPackage } from '../../../lib/packages';

// คลัง Product Key ของผู้ใช้ — เฉพาะคีย์จากคำสั่งซื้อของตัวเอง + คีย์โปรโมที่ตัวเองใช้
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireUser(req, res);
  if (!auth) return;

  const supabase = getAdminClient();
  const email = auth.user.email;
  const keys = [];

  const { data: orders, error: ordersErr } = await supabase
    .from('orders')
    .select('order_id, package_id, amount_thb, hours_to_add, generated_key_code, paid_at, created_at, status')
    .eq('owner_email', email)
    .eq('status', 'PAID')
    .order('paid_at', { ascending: false })
    .limit(100);

  if (!ordersErr && orders?.length) {
    const codes = orders.map((o) => o.generated_key_code).filter(Boolean);
    const { data: productKeys } = codes.length
      ? await supabase.from('product_keys').select('key_code, is_used, status, redeemed_at').in('key_code', codes)
      : { data: [] };
    const byCode = Object.fromEntries((productKeys || []).map((k) => [k.key_code, k]));

    for (const o of orders) {
      if (!o.generated_key_code) continue;
      const pk = byCode[o.generated_key_code];
      const used = pk ? pk.is_used || pk.status === 'REDEEMED' : false;
      keys.push({
        keyCode: o.generated_key_code,
        source: 'purchase',
        packageName: findPackage(o.package_id)?.name || 'Package',
        hours: Number(o.hours_to_add) || 0,
        price: Number(o.amount_thb) || 0,
        orderId: o.order_id,
        status: used ? 'REDEEMED' : 'UNUSED',
        createdAt: o.paid_at || o.created_at,
        redeemedAt: pk?.redeemed_at || null,
      });
    }
  }

  const { data: promos } = await supabase
    .from('promo_keys')
    .select('key_code, hours, used_at')
    .eq('used_by', email)
    .order('used_at', { ascending: false })
    .limit(50);

  for (const p of promos || []) {
    keys.push({
      keyCode: p.key_code,
      source: 'promo',
      packageName: 'Promo Key',
      hours: Number(p.hours) || 0,
      price: 0,
      orderId: null,
      status: 'REDEEMED',
      createdAt: p.used_at,
      redeemedAt: p.used_at,
    });
  }

  res.setHeader('Cache-Control', 'no-store');
  return res.status(200).json({ success: true, keys, ownershipTracked: !ordersErr });
}
