import crypto from 'crypto';
import { getAdminClient } from './supabaseAdmin';
import { adjustHoursDetailed, isDisabledRow, normalizeEmail, rowTags } from './auth';
import { logActivity } from './activity';
import { notifyAdmins } from './lineNotify';
import { REFERRAL_HOURS, REFERRAL_MONTHLY_CAP, REFERRAL_RUN_HOURS, canonicalEmail, isDisposableEmail, maskEmail, normalizeRefCode } from '../referral';

/*
 * ระบบชวนเพื่อน (ผู้ใช้สั่ง 16 ต.ค. 2026 · ปิดช่องโหว่ตามที่ตรวจ):
 *   1) สมัครผ่าน ?ref= → ผูกเพื่อนกับผู้แนะนำ (tag ref_by:<id>) — ยังไม่ให้ชั่วโมง
 *   2) เพื่อนรันบอทจริงครบ REFERRAL_RUN_HOURS (48 ชม. · นับจากชั่วโมงที่หักจริง /api/auth/meter) → ผู้แนะนำได้ +48 ชม. (settleReferral)
 *   กัน: แนะนำตัวเอง (อีเมลเดียวกันแบบ Gmail จุด/+) · อีเมลชั่วคราว · บัญชี MT5 ของเพื่อนซ้ำกับผู้แนะนำ · โควตา 20 คน/30 วัน
 *        · รับรางวัลซ้ำ (tag ref_paid) · รหัสแนะนำสุ่ม (ไม่เปิดเผย id) · แจ้ง LINE แอดมินทุกครั้งที่จ่าย
 */
const DAY_MS = 86400000;
const CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

/** รหัสแนะนำของผู้ใช้ (สร้างครั้งแรกแบบสุ่ม เก็บเป็น tag ref_code:XXXXXX) */
export async function ensureReferralCode(row) {
  const has = rowTags(row).find((t) => t.startsWith('ref_code:'));
  if (has) return has.slice(9);
  const supabase = getAdminClient();
  for (let i = 0; i < 5; i += 1) {
    const code = `GB-${Array.from(crypto.randomBytes(6), (b) => CODE_CHARS[b % CODE_CHARS.length]).join('')}`;
    const { data: clash } = await supabase.from('bot_config').select('id').contains('symbols_trading', [`ref_code:${code}`]).limit(1);
    if (clash?.length) continue;
    const { data: fresh } = await supabase.from('bot_config').select('symbols_trading').eq('id', row.id).maybeSingle();
    const tags = rowTags(fresh || row);
    const again = tags.find((t) => t.startsWith('ref_code:'));
    if (again) return again.slice(9);
    await supabase.from('bot_config').update({ symbols_trading: [...tags, `ref_code:${code}`] }).eq('id', row.id);
    return code;
  }
  throw new Error('สร้างรหัสแนะนำไม่สำเร็จ ลองใหม่อีกครั้ง');
}

async function referrerByCode(code) {
  const c = normalizeRefCode(code);
  if (!c) return null;
  const { data } = await getAdminClient().from('bot_config').select('id, mt5_server, symbols_trading').contains('symbols_trading', [`ref_code:${c}`]).limit(1);
  const r = data?.[0];
  return r && Number(r.id) > 1 && !isDisabledRow(r) ? r : null;
}

/** ตอนสมัคร: ผูกเพื่อนกับผู้แนะนำ (ยังไม่ให้ชั่วโมง) → { status: 'linked' | 'invalid' | 'self' | 'disposable' } */
export async function linkReferral({ friend, refCode, ip }) {
  const ref = await referrerByCode(refCode);
  if (!ref || !friend || Number(ref.id) === Number(friend.id)) return { status: 'invalid' };
  if (canonicalEmail(ref.mt5_server) === canonicalEmail(friend.mt5_server)) return { status: 'self' };
  if (isDisposableEmail(friend.mt5_server)) {
    await logActivity({ userId: friend.id, email: friend.mt5_server, event: 'referred', detail: `ลิงก์แนะนำของ ${maskEmail(ref.mt5_server)} ไม่นับ (อีเมลชั่วคราว)`, ip });
    return { status: 'disposable' };
  }
  const tags = rowTags(friend).filter((t) => !t.startsWith('ref_by:'));
  await getAdminClient().from('bot_config').update({ symbols_trading: [...tags, `ref_by:${ref.id}`] }).eq('id', friend.id);
  await logActivity({ userId: friend.id, email: friend.mt5_server, event: 'referred', detail: `สมัครผ่านลิงก์แนะนำของ ${maskEmail(ref.mt5_server)} · รอรันบอทครบ ${REFERRAL_RUN_HOURS} ชม.`, ip });
  return { status: 'linked', referrerId: ref.id };
}

async function mt5Logins(userId) {
  const { data } = await getAdminClient().from('online_daily_accounts').select('login').eq('user_id', String(userId)).limit(5000);
  return new Set((data || []).map((r) => Number(r.login)).filter((x) => x > 0));
}

/**
 * เรียกจาก /api/auth/meter หลังหักชั่วโมง: เพื่อนที่ถูกแนะนำรันบอทครบ REFERRAL_RUN_HOURS → จ่ายรางวัลผู้แนะนำ (ครั้งเดียว)
 * friendRow = แถว bot_config ของผู้ที่กำลังรันบอท · runHours = ชั่วโมงสะสมตลอดอายุ (online_progress)
 */
export async function settleReferral(friendRow, runHours) {
  const tags = rowTags(friendRow);
  const refTag = tags.find((t) => t.startsWith('ref_by:'));
  if (!refTag || tags.some((t) => t.startsWith('ref_paid:')) || Number(runHours) < REFERRAL_RUN_HOURS) return null;
  const supabase = getAdminClient();
  // จองก่อนจ่าย (กันสองคำขอพร้อมกันจ่ายซ้ำ): อ่านแถวล่าสุดแล้วติด tag ref_paid
  const { data: fresh } = await supabase.from('bot_config').select('id, mt5_server, symbols_trading').eq('id', friendRow.id).maybeSingle();
  const ft = rowTags(fresh || friendRow);
  if (ft.some((t) => t.startsWith('ref_paid:'))) return null;
  const now = new Date().toISOString();
  await supabase.from('bot_config').update({ symbols_trading: [...ft, `ref_paid:${now}`] }).eq('id', friendRow.id);

  const refId = Number(refTag.slice(7));
  const { data: ref } = await supabase.from('bot_config').select('id, mt5_server, symbols_trading').eq('id', refId).maybeSingle();
  const who = maskEmail(friendRow.mt5_server);
  const block = async (why) => {
    await logActivity({ userId: refId, email: ref?.mt5_server, event: 'referral_blocked', detail: `เพื่อน ${who} รันบอทครบ ${REFERRAL_RUN_HOURS} ชม. · ไม่ได้รับชั่วโมง (${why}) · friend:${friendRow.id}` });
    return { status: 'blocked', why };
  };
  if (!ref || isDisabledRow(ref)) return block('บัญชีผู้แนะนำถูกระงับ');

  // บัญชี MT5 ของเพื่อนซ้ำกับของผู้แนะนำ = น่าจะเป็นคนเดียวกัน
  const [mine, theirs] = await Promise.all([mt5Logins(refId), mt5Logins(friendRow.id)]);
  if ([...theirs].some((l) => mine.has(l))) {
    await notifyAdmins(`⚠️ ชวนเพื่อนถูกบล็อก: ${who} ใช้บัญชี MT5 เดียวกับผู้แนะนำ ${maskEmail(ref.mt5_server)}`).catch(() => {});
    return block('ใช้บัญชี MT5 เดียวกับผู้แนะนำ');
  }
  const since = new Date(Date.now() - 30 * DAY_MS).toISOString();
  const countPaid = async () =>
    (await supabase.from('user_activity').select('id', { count: 'exact', head: true }).eq('user_id', String(refId)).eq('event', 'referral_reward').gte('created_at', since)).count || 0;
  if ((await countPaid()) >= REFERRAL_MONTHLY_CAP) return block(`ครบ ${REFERRAL_MONTHLY_CAP} คนใน 30 วัน`);

  const { after } = await adjustHoursDetailed(refId, REFERRAL_HOURS);
  await logActivity({ userId: refId, email: ref.mt5_server, event: 'referral_reward', detail: `เพื่อน ${who} รันบอทครบ ${REFERRAL_RUN_HOURS} ชม. · +${REFERRAL_HOURS} ชม. (คงเหลือ ${after} ชม.) · friend:${friendRow.id}` });
  // ตรวจซ้ำหลังจ่าย (สองคำขอพร้อมกันอาจผ่านโควตาพร้อมกัน) → เกินโควตา = ดึงคืน
  if ((await countPaid()) > REFERRAL_MONTHLY_CAP) {
    await adjustHoursDetailed(refId, -REFERRAL_HOURS);
    await logActivity({ userId: refId, email: ref.mt5_server, event: 'referral_blocked', detail: `ดึงคืน ${REFERRAL_HOURS} ชม. (เกินโควตา ${REFERRAL_MONTHLY_CAP} คน/30 วัน) · friend:${friendRow.id}` });
    return { status: 'blocked', why: 'cap' };
  }
  await notifyAdmins(`🎁 ชวนเพื่อน: ${maskEmail(ref.mt5_server)} ได้ +${REFERRAL_HOURS} ชม. (เพื่อน ${who} รันบอทครบ ${REFERRAL_RUN_HOURS} ชม.)`).catch(() => {});
  return { status: 'rewarded' };
}

/** สรุปการชวนเพื่อนของผู้ใช้ → { invited, rewarded, pending, hours, friends: [{ name, email, at, status, progress }] } */
export async function referralSummary(userId) {
  const supabase = getAdminClient();
  const [{ data: friends }, { data: acts }] = await Promise.all([
    supabase.from('bot_config').select('id, mt5_server, symbols_trading').contains('symbols_trading', [`ref_by:${userId}`]).limit(500),
    supabase
      .from('user_activity')
      .select('event, detail, created_at')
      .eq('user_id', String(userId))
      .in('event', ['referral_reward', 'referral_blocked'])
      .order('created_at', { ascending: false })
      .limit(1000),
  ]);
  const ids = (friends || []).map((f) => String(f.id));
  const { data: prog } = ids.length
    ? await supabase.from('online_progress').select('user_id, minutes, cycles').in('user_id', ids)
    : { data: [] };
  const runH = Object.fromEntries((prog || []).map((p) => [String(p.user_id), ((Number(p.cycles) || 0) * 6000 + (Number(p.minutes) || 0)) / 60]));
  const result = {};
  for (const a of [...(acts || [])].reverse()) {
    const m = /friend:(\d+)/.exec(a.detail || '');
    if (m) result[m[1]] = { status: a.event === 'referral_reward' ? 'rewarded' : 'blocked', why: (/\(([^)]*)\)/.exec(a.detail || '') || [])[1] || '', at: a.created_at };
  }
  const list = (friends || []).map((f) => {
    const tags = rowTags(f);
    const reg = tags.find((t) => t.startsWith('registered:'));
    const nameTag = tags.find((t) => t.startsWith('name:'));
    const name = nameTag ? nameTag.slice(5) : String(f.mt5_server || '').split('@')[0];
    const r = result[String(f.id)];
    const h = Math.floor((runH[String(f.id)] || 0) * 10) / 10;
    return {
      name: name.length > 2 ? `${name.slice(0, Math.max(2, Math.ceil(name.length / 2)))}***` : name,
      email: maskEmail(f.mt5_server),
      at: reg ? reg.slice(11) : null,
      status: r ? r.status : 'pending',
      why: r?.why || '',
      progress: Math.min(h, REFERRAL_RUN_HOURS),
    };
  });
  list.sort((a, b) => String(b.at).localeCompare(String(a.at)));
  const rewarded = (acts || []).filter((a) => a.event === 'referral_reward').length - (acts || []).filter((a) => /^ดึงคืน/.test(a.detail || '')).length;
  return {
    invited: list.length,
    rewarded: Math.max(0, rewarded),
    pending: list.filter((f) => f.status === 'pending').length,
    hours: Math.max(0, rewarded) * REFERRAL_HOURS,
    friends: list,
  };
}

export { normalizeEmail };
