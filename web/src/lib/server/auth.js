import crypto from 'crypto';
import { getAdminClient } from './supabaseAdmin';

// =============================================================================
// GoldBot24 Auth (Server-only)
// - ผู้ใช้เก็บในตาราง bot_config: mt5_server = อีเมล, mt5_password = hash, lot_size = ชั่วโมงคงเหลือ
// - Token = base64url(payload).base64url(HMAC-SHA256) ลงลายเซ็นด้วย AUTH_SECRET (ปลอมแปลงไม่ได้)
// =============================================================================

const TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30; // 30 วัน
const PBKDF2_V2_ITERATIONS = 210000;
const PBKDF2_V1_ITERATIONS = 10000;
const DEV_FALLBACK_SECRET = 'goldbot24-dev-only-secret-change-me';

const DEFAULT_ADMIN_EMAILS = ['admin@goldbot24.com', 'admin@aitrade24.com'];

function getAuthSecret() {
  const secret = process.env.AUTH_SECRET || process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (secret) return secret;
  if (process.env.VERCEL_ENV === 'production' || process.env.NODE_ENV === 'production') {
    throw new Error('AUTH_SECRET is not configured on the server');
  }
  return DEV_FALLBACK_SECRET;
}

function b64url(buf) {
  return Buffer.from(buf).toString('base64').replace(/=+$/, '').replace(/\+/g, '-').replace(/\//g, '_');
}

function fromB64url(str) {
  return Buffer.from(String(str).replace(/-/g, '+').replace(/_/g, '/'), 'base64');
}

export function signToken(userId, email) {
  const now = Math.floor(Date.now() / 1000);
  const body = b64url(JSON.stringify({ sub: String(userId), email, iat: now, exp: now + TOKEN_TTL_SECONDS }));
  const sig = b64url(crypto.createHmac('sha256', getAuthSecret()).update(body).digest());
  return `${body}.${sig}`;
}

export function verifyToken(token) {
  if (!token || typeof token !== 'string' || !token.includes('.')) return null;
  const [body, sig] = token.split('.');
  const expected = b64url(crypto.createHmac('sha256', getAuthSecret()).update(body).digest());
  const a = Buffer.from(sig || '');
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  try {
    const payload = JSON.parse(fromB64url(body).toString('utf8'));
    if (!payload.sub || !payload.exp || payload.exp < Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Password hashing (PBKDF2-HMAC-SHA256)
// v1$salt$hash = 10,000 รอบ (บัญชีเก่า) | v2$salt$hash = 210,000 รอบ (บัญชีใหม่)
// ---------------------------------------------------------------------------
export function hashPassword(password) {
  const salt = crypto.randomBytes(16);
  const hash = crypto.pbkdf2Sync(password, salt, PBKDF2_V2_ITERATIONS, 32, 'sha256');
  return `v2$${salt.toString('hex')}$${hash.toString('hex')}`;
}

export function verifyPassword(password, stored) {
  if (!stored || typeof stored !== 'string') return false;
  const parts = stored.split('$');
  if (parts.length !== 3) return false;
  const [version, saltHex, hashHex] = parts;
  const iterations = version === 'v2' ? PBKDF2_V2_ITERATIONS : version === 'v1' ? PBKDF2_V1_ITERATIONS : 0;
  if (!iterations) return false;
  try {
    const expected = Buffer.from(hashHex, 'hex');
    const matches = (salt) => {
      const derived = crypto.pbkdf2Sync(password, salt, iterations, 32, 'sha256');
      return derived.length === expected.length && crypto.timingSafeEqual(derived, expected);
    };
    if (matches(Buffer.from(saltHex, 'hex'))) return true;
    // บัญชี v1 ที่สมัครจากเว็บรุ่นเก่าใช้ "ข้อความ hex" ของ salt เป็น salt โดยตรง (ไม่ได้ decode)
    return version === 'v1' && matches(Buffer.from(saltHex, 'utf8'));
  } catch {
    return false;
  }
}

export function needsRehash(stored) {
  return typeof stored === 'string' && !stored.startsWith('v2$');
}

// ---------------------------------------------------------------------------
// User helpers
// ---------------------------------------------------------------------------
function adminEmails() {
  const fromEnv = (process.env.ADMIN_EMAILS || '')
    .split(',')
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
  return fromEnv.length ? fromEnv : DEFAULT_ADMIN_EMAILS;
}

export function isAdminRow(row) {
  if (!row) return false;
  const tags = Array.isArray(row.symbols_trading) ? row.symbols_trading : [];
  if (tags.includes('role:admin')) return true;
  return adminEmails().includes(String(row.mt5_server || '').toLowerCase());
}

export function toUserPayload(row) {
  let displayName = String(row.mt5_server || '').split('@')[0];
  const tags = Array.isArray(row.symbols_trading) ? row.symbols_trading : [];
  for (const item of tags) {
    if (typeof item === 'string' && item.startsWith('name:')) displayName = item.substring(5);
  }
  const isAdmin = isAdminRow(row);
  return {
    id: String(row.id),
    email: row.mt5_server,
    displayName,
    mt5Login: row.mt5_login || 0,
    hoursRemaining: Number(row.lot_size) || 0,
    role: isAdmin ? 'admin' : 'user',
    isAdmin,
  };
}

export function normalizeEmail(email) {
  return String(email || '').trim().toLowerCase();
}

export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/** ดึงแถวผู้ใช้จาก id (ตัด id=1 ซึ่งเป็นแถว config ระบบออก) */
export async function getUserRowById(id) {
  const numericId = Number(id);
  if (!Number.isInteger(numericId) || numericId <= 1) return null;
  const { data, error } = await getAdminClient().from('bot_config').select('*').eq('id', numericId).maybeSingle();
  if (error || !data) return null;
  return data;
}

function readBearer(req) {
  const header = req.headers.authorization || req.headers.Authorization || '';
  const match = /^Bearer\s+(.+)$/i.exec(header);
  return match ? match[1].trim() : null;
}

/**
 * ตรวจ Token จาก Header "Authorization: Bearer <token>"
 * คืนค่า { row, user } หรือส่ง 401 แล้วคืน null
 */
export async function requireUser(req, res) {
  let payload = null;
  try {
    payload = verifyToken(readBearer(req));
  } catch (err) {
    res.status(500).json({ success: false, error: 'ระบบยืนยันตัวตนยังไม่ได้ตั้งค่า (AUTH_SECRET)' });
    return null;
  }
  if (!payload) {
    res.status(401).json({ success: false, error: 'เซสชันหมดอายุหรือไม่ถูกต้อง กรุณาเข้าสู่ระบบใหม่' });
    return null;
  }
  const row = await getUserRowById(payload.sub);
  if (!row || normalizeEmail(row.mt5_server) !== normalizeEmail(payload.email)) {
    res.status(401).json({ success: false, error: 'ไม่พบบัญชีผู้ใช้ กรุณาเข้าสู่ระบบใหม่' });
    return null;
  }
  return { row, user: toUserPayload(row) };
}

export async function requireAdmin(req, res) {
  const auth = await requireUser(req, res);
  if (!auth) return null;
  if (!auth.user.isAdmin) {
    res.status(403).json({ success: false, error: 'ต้องเป็นผู้ดูแลระบบ (Admin) เท่านั้น' });
    return null;
  }
  return auth;
}

/**
 * ปรับยอดชั่วโมงแบบ Optimistic Concurrency (กันการเขียนทับกันระหว่าง Meter กับ Redeem)
 * deltaHours: บวก = เติม, ลบ = หัก — ยอดไม่ต่ำกว่า 0
 */
export async function adjustHours(userId, deltaHours) {
  const supabase = getAdminClient();
  for (let attempt = 0; attempt < 5; attempt++) {
    const { data: row, error } = await supabase.from('bot_config').select('id, lot_size').eq('id', userId).maybeSingle();
    if (error || !row) throw new Error('ไม่พบบัญชีผู้ใช้');
    const current = Number(row.lot_size) || 0;
    const next = Math.max(0, Math.round((current + deltaHours) * 100) / 100);
    const { data: updated, error: updErr } = await supabase
      .from('bot_config')
      .update({ lot_size: next, updated_at: new Date().toISOString() })
      .eq('id', userId)
      .eq('lot_size', row.lot_size)
      .select('id');
    if (updErr) throw new Error('ไม่สามารถอัปเดตชั่วโมงได้');
    if (updated && updated.length === 1) return next;
  }
  throw new Error('ระบบไม่ว่าง กรุณาลองใหม่อีกครั้ง');
}

export function allowMethods(req, res, methods) {
  if (!methods.includes(req.method)) {
    res.setHeader('Allow', methods.join(', '));
    res.status(405).json({ success: false, error: 'Method not allowed' });
    return false;
  }
  return true;
}
