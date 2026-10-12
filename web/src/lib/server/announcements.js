import { getAdminClient } from './supabaseAdmin';

// ข่าวสาร/โปรโมชัน (supabase_announcements_patch_09.sql) — ใช้ร่วมกันทั้งเว็บและโปรแกรม
export const BUCKET = 'announcements';
const COLS = 'id, title, body, image_url, link_url, link_label, active, popup, starts_at, ends_at, created_at, updated_at';

export function shape(a) {
  return {
    id: Number(a.id),
    title: a.title || '',
    body: a.body || '',
    imageUrl: a.image_url || null,
    linkUrl: a.link_url || null,
    linkLabel: a.link_label || null,
    active: Boolean(a.active),
    popup: Boolean(a.popup),
    startsAt: a.starts_at,
    endsAt: a.ends_at,
    createdAt: a.created_at,
    updatedAt: a.updated_at,
  };
}

/** ข่าวที่กำลังแสดง (เปิดอยู่ · ถึงเวลาเริ่มแล้ว · ยังไม่หมดเวลา) ใหม่สุดก่อน */
export async function listPublic(limit = 20) {
  const now = new Date().toISOString();
  const { data, error } = await getAdminClient()
    .from('announcements')
    .select(COLS)
    .eq('active', true)
    .lte('starts_at', now)
    .or(`ends_at.is.null,ends_at.gt.${now}`)
    .order('starts_at', { ascending: false })
    .limit(limit);
  if (error) return { error };
  return { items: (data || []).map(shape) };
}

export async function listAll() {
  const { data, error } = await getAdminClient().from('announcements').select(COLS).order('created_at', { ascending: false }).limit(200);
  if (error) return { error };
  return { items: (data || []).map(shape) };
}

/** รูปจาก data URL (base64) → Supabase Storage → URL สาธารณะ */
export async function uploadImage(dataUrl) {
  const m = /^data:(image\/(png|jpe?g|webp|gif));base64,(.+)$/i.exec(String(dataUrl || ''));
  if (!m) throw new Error('รองรับเฉพาะรูป PNG / JPG / WEBP / GIF');
  const buf = Buffer.from(m[3], 'base64');
  if (buf.length > 3 * 1024 * 1024) throw new Error('รูปต้องไม่เกิน 3 MB');
  const ext = m[2].toLowerCase().replace('jpeg', 'jpg');
  const path = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${ext}`;
  const sb = getAdminClient();
  const { error } = await sb.storage.from(BUCKET).upload(path, buf, { contentType: m[1], upsert: false, cacheControl: '31536000' });
  if (error) throw new Error(`อัปโหลดรูปไม่สำเร็จ: ${error.message}`);
  return sb.storage.from(BUCKET).getPublicUrl(path).data.publicUrl;
}
