import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireAdmin } from '../../../lib/server/auth';

// คีย์และคำสั่งซื้อทั้งหมด (แบ่งหน้า) — แยกหมวด:
//   unused   = Product/Promo Key ที่ยังไม่ถูกใช้
//   redeemed = คีย์ที่ผู้ใช้เติมแล้ว
//   promo    = คีย์ที่แอดมินสร้าง (ทุกสถานะ)
//   pending  = คำสั่งซื้อที่ยังไม่ชำระ
//   paid     = คำสั่งซื้อที่ชำระแล้ว (ได้ Product Key)
const FILTERS = ['unused', 'redeemed', 'promo', 'pending', 'paid'];

function keyRow(k, source) {
  const used = source === 'promo' ? Boolean(k.used) : Boolean(k.is_used || k.status === 'REDEEMED');
  return {
    kind: 'key',
    source,
    keyCode: k.key_code,
    hours: Number(k.hours || 0) + Number(k.bonus_hours || 0),
    price: Number(k.price_thb || 0),
    status: used ? 'REDEEMED' : 'UNUSED',
    owner: source === 'promo' ? k.created_by || null : k.owner_email || null,
    redeemedBy: source === 'promo' ? k.used_by || null : k.redeemed_by_email || null,
    createdAt: source === 'promo' ? k.created_at || null : k.purchased_at || null,
    redeemedAt: source === 'promo' ? k.used_at || null : k.redeemed_at || null,
    expiresAt: k.expires_at || null,
    orderId: k.order_id || null,
  };
}

function orderRow(o) {
  return {
    kind: 'order',
    orderId: o.order_id,
    packageId: o.package_id,
    amount: Number(o.amount_thb) || 0,
    hours: Number(o.hours_to_add) || 0,
    status: o.status,
    owner: o.owner_email || null,
    keyCode: o.generated_key_code || null,
    paymentRef: o.payment_ref || null,
    createdAt: o.created_at,
    paidAt: o.paid_at,
  };
}

async function counts(supabase) {
  const head = { count: 'exact', head: true };
  const q = await Promise.all([
    supabase.from('product_keys').select('key_code', head).eq('is_used', false),
    supabase.from('promo_keys').select('key_code', head).eq('used', false),
    supabase.from('product_keys').select('key_code', head).eq('is_used', true),
    supabase.from('promo_keys').select('key_code', head).eq('used', true),
    supabase.from('promo_keys').select('key_code', head),
    supabase.from('orders').select('order_id', head).in('status', ['PENDING', 'PROCESSING']),
    supabase.from('orders').select('order_id', head).eq('status', 'PAID'),
  ]);
  const c = q.map((r) => r.count || 0);
  return { unused: c[0] + c[1], redeemed: c[2] + c[3], promo: c[4], pending: c[5], paid: c[6] };
}

export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;

  const supabase = getAdminClient();
  const filter = FILTERS.includes(req.query.filter) ? req.query.filter : 'unused';
  const pageSize = Math.min(100, Math.max(1, parseInt(req.query.pageSize, 10) || 20));
  const page = Math.max(1, parseInt(req.query.page, 10) || 1);
  const from = (page - 1) * pageSize;
  const to = from + pageSize - 1;
  const q = String(req.query.q || '').trim().toUpperCase().replace(/[%,()]/g, '');

  let items = [];
  let total = 0;
  let cachedCounts = null;

  if (filter === 'pending' || filter === 'paid') {
    let query = supabase.from('orders').select('*', { count: 'exact' });
    query = filter === 'paid' ? query.eq('status', 'PAID') : query.in('status', ['PENDING', 'PROCESSING', 'CANCELLED']);
    if (q) query = query.or(`order_id.ilike.%${q}%,generated_key_code.ilike.%${q}%`);
    const { data, count } = await query.order('created_at', { ascending: false }).range(from, to);
    items = (data || []).map(orderRow);
    total = count || 0;
  } else if (filter === 'promo') {
    let query = supabase.from('promo_keys').select('*', { count: 'exact' });
    if (q) query = query.ilike('key_code', `%${q}%`);
    const { data, count } = await query.order('created_at', { ascending: false, nullsFirst: false }).range(from, to);
    items = (data || []).map((k) => keyRow(k, 'promo'));
    total = count || 0;
  } else {
    // unused / redeemed: รวม product_keys + promo_keys (เรียงใหม่ → เก่า แล้วตัดหน้า)
    const used = filter === 'redeemed';
    let pq = supabase.from('product_keys').select('*').eq('is_used', used);
    let mq = supabase.from('promo_keys').select('*').eq('used', used);
    if (q) {
      pq = pq.ilike('key_code', `%${q}%`);
      mq = mq.ilike('key_code', `%${q}%`);
    }
    const limit = to + 1;
    const [{ data: pk }, { data: mk }] = await Promise.all([
      pq.order(used ? 'redeemed_at' : 'purchased_at', { ascending: false, nullsFirst: false }).limit(limit),
      mq.order(used ? 'used_at' : 'created_at', { ascending: false, nullsFirst: false }).limit(limit),
    ]);
    const merged = [...(pk || []).map((k) => keyRow(k, 'purchase')), ...(mk || []).map((k) => keyRow(k, 'promo'))];
    const ts = (r) => new Date((used ? r.redeemedAt : r.createdAt) || 0).getTime();
    merged.sort((a, b) => ts(b) - ts(a));
    items = merged.slice(from, to + 1);
    cachedCounts = await counts(supabase);
    total = cachedCounts[filter];
  }

  return res.status(200).json({
    success: true,
    filter,
    items,
    total,
    page,
    pageSize,
    totalPages: Math.max(1, Math.ceil(total / pageSize)),
    counts: cachedCounts || (await counts(supabase)),
  });
}
