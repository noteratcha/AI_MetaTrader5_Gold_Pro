import { createClient } from '@supabase/supabase-js';

// ใช้เฉพาะฝั่ง Server (API Routes) เท่านั้น — ห้าม import จาก Client Component
const SUPABASE_URL = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://isliehicmtpsnuyxedln.supabase.co';
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || '';
const ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_a0D8-j-yM-a3SNx2mig7vw_dvwAOBkg';

let client = null;

/**
 * Supabase client สำหรับ API Routes
 * - ถ้าตั้ง SUPABASE_SERVICE_ROLE_KEY แล้ว จะข้าม RLS ได้ (ต้องใช้หลังรัน supabase_security_rls.sql)
 * - ถ้ายังไม่ตั้ง จะ fallback เป็น anon key (ทำงานได้กับฐานข้อมูลที่ยังไม่ล็อก RLS)
 */
export function getAdminClient() {
  if (!client) {
    if (!SERVICE_ROLE_KEY) {
      console.warn('[supabaseAdmin] SUPABASE_SERVICE_ROLE_KEY is not set — falling back to anon key.');
    }
    client = createClient(SUPABASE_URL, SERVICE_ROLE_KEY || ANON_KEY, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
  }
  return client;
}

/** Insert ที่ทนต่อฐานข้อมูลที่ยังไม่ได้รัน migration: ถ้าคอลัมน์ใหม่ไม่มี จะลองใหม่โดยตัดคอลัมน์นั้นออก */
export async function insertTolerant(table, row, optionalColumns = []) {
  const supabase = getAdminClient();
  let attempt = { ...row };
  for (let i = 0; i <= optionalColumns.length; i++) {
    const { error } = await supabase.from(table).insert(attempt);
    if (!error) return { error: null };
    const missing = optionalColumns.find((col) => col in attempt && String(error.message || '').includes(col));
    if (!missing) return { error };
    delete attempt[missing];
  }
  return { error: new Error(`insert into ${table} failed`) };
}
