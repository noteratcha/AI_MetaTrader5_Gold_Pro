import { getAdminClient } from '../../../lib/server/supabaseAdmin';
import { allowMethods, requireAdmin } from '../../../lib/server/auth';
import { listAll, shape, uploadImage } from '../../../lib/server/announcements';

export const config = { api: { bodyParser: { sizeLimit: '4.5mb' } } };

const clean = (v, max) => String(v ?? '').trim().slice(0, max);
const isLink = (v) => !v || /^https?:\/\//i.test(v) || v.startsWith('/');

/** ฟอร์มจากหน้าแอดมิน → คอลัมน์ (อัปโหลดรูปถ้าส่งมาเป็น data URL) */
async function toRow(b) {
  const row = {
    title: clean(b.title, 160),
    body: clean(b.body, 4000),
    link_url: clean(b.linkUrl, 500) || null,
    link_label: clean(b.linkLabel, 60) || null,
    active: b.active !== false,
    popup: b.popup !== false,
    starts_at: b.startsAt ? new Date(b.startsAt).toISOString() : new Date().toISOString(),
    ends_at: b.endsAt ? new Date(b.endsAt).toISOString() : null,
    updated_at: new Date().toISOString(),
  };
  if (!row.title) throw new Error('กรุณาใส่หัวข้อข่าว');
  if (!isLink(row.link_url)) throw new Error('ลิงก์ต้องขึ้นต้นด้วย https:// หรือ /');
  if (b.imageData) row.image_url = await uploadImage(b.imageData);
  else if (b.imageUrl !== undefined) {
    const u = clean(b.imageUrl, 1000) || null;
    if (u && !/^https:\/\//i.test(u)) throw new Error('ลิงก์รูปต้องขึ้นต้นด้วย https://');
    row.image_url = u;
  }
  return row;
}

// จัดการข่าวสาร/โปรโมชัน (แอดมินเท่านั้น)
export default async function handler(req, res) {
  if (!allowMethods(req, res, ['GET', 'POST', 'PUT', 'DELETE'])) return;
  const auth = await requireAdmin(req, res);
  if (!auth) return;
  const sb = getAdminClient();
  try {
    if (req.method === 'GET') {
      const { items, error } = await listAll();
      if (error) return res.status(200).json({ success: true, items: [], setupRequired: true });
      return res.status(200).json({ success: true, items });
    }
    if (req.method === 'POST') {
      const row = { ...(await toRow(req.body || {})), created_by: auth.user.email };
      const { data, error } = await sb.from('announcements').insert(row).select('*').single();
      if (error) throw new Error(error.message);
      return res.status(200).json({ success: true, item: shape(data) });
    }
    const id = Number(req.body?.id || req.query.id);
    if (!id) return res.status(400).json({ success: false, error: 'ไม่พบรหัสข่าว' });
    if (req.method === 'PUT') {
      const { data, error } = await sb.from('announcements').update(await toRow(req.body || {})).eq('id', id).select('*').single();
      if (error) throw new Error(error.message);
      return res.status(200).json({ success: true, item: shape(data) });
    }
    const { error } = await sb.from('announcements').delete().eq('id', id);
    if (error) throw new Error(error.message);
    return res.status(200).json({ success: true });
  } catch (err) {
    return res.status(400).json({ success: false, error: err.message || 'ทำรายการไม่สำเร็จ' });
  }
}
