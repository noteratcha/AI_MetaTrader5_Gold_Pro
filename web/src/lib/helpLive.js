// ผู้ช่วย (FAB) ตอบด้วยข้อมูลสดจากหน้าเว็บ (ผู้ใช้สั่ง 16 ต.ค. 2026): ผล Backtest รายแผน (/backtest.json) · เวอร์ชันล่าสุด (/api/release)
// · แพ็กเกจชั่วโมง/สมาชิก (lib/packages · lib/membership) · ข่าว USD ถัดไป (/api/calendar) · ชั่วโมง/สมาชิกของฉัน (ผู้ใช้ที่ล็อกอิน) · หน้าต่าง ๆ ของเว็บ
// รายการ LIVE ถูกค้นรวมกับ KB (helpSearch) · คำถามที่ชัดเจน (เช่น "P6 กำไรเท่าไหร่") จับด้วย liveIntent ก่อน
import { PACKAGES } from './packages';
import { MEMBERSHIP_PLANS, MEMBER_PLAN_NUMBERS } from './membership';
import { PLAN_NAMES } from './plans';

export const LIVE = [
  { id: 'live-plan', live: 'plan', t: 'ผลทดสอบย้อนหลังรายแผน', href: '/backtest',
    k: ['ผลทดสอบ', 'backtest', 'กำไรกี่จุด', 'ชนะกี่เปอร์เซ็นต์', 'win rate', 'pf', 'max dd', 'ผลแผน', 'แผนนี้กำไร', 'แผนไหนกำไรมากสุด'],
    a: 'ดูผลทดสอบย้อนหลังทุกแผนได้ที่หน้าแผนเทรด' },
  { id: 'live-version', live: 'version', t: 'เวอร์ชันล่าสุดของโปรแกรม', href: '/download',
    k: ['เวอร์ชันล่าสุด', 'version ล่าสุด', 'รุ่นล่าสุด', 'เวอร์ชันอะไร', 'ตัวล่าสุด', 'ขนาดไฟล์'],
    a: 'ดูเวอร์ชันล่าสุดได้ที่หน้าดาวน์โหลด' },
  { id: 'live-packages', live: 'packages', t: 'แพ็กเกจชั่วโมงและราคา', href: '/store',
    k: ['แพ็กเกจ', 'package', 'ราคาแพ็กเกจ', 'ซื้อกี่ชั่วโมง', 'เติมกี่บาท', 'โบนัส', 'ราคาชั่วโมง'],
    a: 'ดูแพ็กเกจได้ที่หน้าเติมชั่วโมง' },
  { id: 'live-member-price', live: 'member', t: 'ราคาสมาชิกรายเดือน', href: '/store?member=1',
    k: ['ราคาสมาชิก', 'สมาชิกกี่บาท', 'สมาชิก 1 ปี', 'สมาชิก 90 วัน', 'ค่าสมาชิก', 'แพ็กเกจสมาชิก'],
    a: 'ดูราคาสมาชิกได้ที่หน้าเติมชั่วโมง' },
  { id: 'live-news', live: 'news', t: 'ข่าว USD สำคัญถัดไป', href: '/calendar',
    k: ['ข่าวถัดไป', 'ข่าววันนี้', 'ข่าวคืนนี้', 'ข่าวแรง', 'nfp เมื่อไหร่', 'cpi เมื่อไหร่', 'ข่าวสัปดาห์นี้', 'ข่าวออกกี่โมง'],
    a: 'ดูปฏิทินข่าวได้ที่หน้าปฏิทิน' },
  { id: 'live-my-hours', live: 'myhours', t: 'ชั่วโมงคงเหลือของฉัน', href: '/dashboard',
    k: ['ชั่วโมงเหลือ', 'เหลือกี่ชั่วโมง', 'ชั่วโมงของฉัน', 'เวลาคงเหลือ', 'ใช้ได้อีกกี่ชั่วโมง', 'เครดิตเหลือ'],
    a: 'ดูชั่วโมงคงเหลือได้ที่กระเป๋าเวลา' },
  { id: 'live-my-member', live: 'mymember', t: 'สถานะสมาชิกของฉัน', href: '/dashboard',
    k: ['สมาชิกหมดเมื่อไหร่', 'สมาชิกของฉัน', 'เป็นสมาชิกไหม', 'หมดอายุวันไหน', 'สถานะสมาชิก'],
    a: 'ดูสถานะสมาชิกได้ที่กระเป๋าเวลา' },
  { id: 'live-pages', live: 'pages', t: 'เว็บ GoldBot24 มีหน้าอะไรบ้าง', href: '/',
    k: ['เว็บมีอะไร', 'หน้าเว็บ', 'เมนูเว็บ', 'หน้าไหน', 'อยู่ตรงไหน', 'หาไม่เจอ', 'แผนที่เว็บ'],
    a: '' },
];

const PAGES = [
  ['/', 'พอร์ตสด', 'ยอดเงิน ไม้ที่เปิด สภาวะตลาด AI กำไรรายวันจากโปรแกรม (ต้องล็อกอินและเปิดโปรแกรมไว้)'],
  ['/dashboard', 'กระเป๋าเวลา', 'ชั่วโมงคงเหลือ · เติมคีย์ · สมาชิก · รางวัล/Lv. · ประวัติชั่วโมง · คีย์ของฉัน'],
  ['/calendar', 'ปฏิทินข่าว', 'ข่าวเศรษฐกิจรายสัปดาห์ (เวลาไทย) + ผลต่อทอง'],
  ['/backtest', 'แผนเทรด', 'ผลทดสอบย้อนหลังทุกแผน · กำไรรายเดือน · ผลเทรดจริงของผู้ใช้ทุกคน'],
  ['/store', 'เติมชั่วโมง', 'แพ็กเกจชั่วโมง · สมาชิกรายเดือน · ชำระผ่าน PromptPay'],
  ['/guide', 'คู่มือ', 'วิธีใช้โปรแกรมและเว็บทุกขั้นตอน'],
  ['/download', 'ดาวน์โหลด', 'ตัวติดตั้งโปรแกรมเวอร์ชันล่าสุด'],
  ['/news', 'ข่าวสาร', 'ประกาศและโปรโมชันจากแอดมิน'],
  ['/receipts', 'ใบเสร็จ', 'ใบเสร็จการชำระเงิน (ดู/พิมพ์)'],
  ['/contact', 'ติดต่อ', 'LINE แอดมิน'],
];

const thb = (v) => `${Number(v).toLocaleString('th-TH', { maximumFractionDigits: 2 })} บาท`;
const pts = (v) => `${v >= 0 ? '+' : ''}${Number(v).toLocaleString('th-TH', { maximumFractionDigits: 0 })}`;
const thaiDT = (iso) =>
  new Date(iso).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

/** เลขแผนในคำถาม: "P6" / "แผน 6" / "แผนที่ 6" / ชื่อสั้น เช่น "SAR" → 0 ถ้าไม่มี */
export function planInQuestion(q) {
  const s = String(q || '').toLowerCase();
  const m = /(?:\bp|แผน(?:ที่)?\s*)(1[0-2]|[1-9])(?!\d)/.exec(s);
  if (m) return Number(m[1]);
  const names = { sar: 6, psar: 6, fib: 9, rsi: 10, news: 11, smc: 3, 'bb high': 12, 'high low': 12, 'sr bounce': 4 };
  for (const [k, v] of Object.entries(names)) if (s.includes(k)) return v;
  return 0;
}

/** คำถามที่ชัดเจนพอจะตอบด้วยข้อมูลสดเลย (ก่อนค้นแบบใกล้เคียง) */
export function liveIntent(q) {
  const s = String(q || '').toLowerCase();
  if (planInQuestion(s) && /กำไร|ขาดทุน|ผล|ชนะ|win|pf|dd|drawdown|ไม้|ดีไหม|เป็นยังไง|กี่จุด|backtest/.test(s)) return 'live-plan';
  if (/แผนไหน.*(กำไร|ดี|เงิน|เด่น|เยอะ|มาก)|(กำไร|เงิน)(ได้)?(มาก|สูง|เยอะ)(ที่)?สุด/.test(s)) return 'live-plan';
  if (/(เวอร์ชัน|เวอร์ชั่น|version|รุ่น).*(ล่าสุด|ใหม่สุด|ตอนนี้)|ล่าสุด.*(เวอร์ชัน|เวอร์ชั่น)/.test(s)) return 'live-version';
  if (/(ชั่วโมง|เวลา|เครดิต).*(เหลือ|คงเหลือ)|เหลือ.*ชั่วโมง/.test(s) && /ฉัน|ผม|เรา|ของ|เหลือ/.test(s)) return 'live-my-hours';
  if (/สมาชิก.*(หมด|เหลือ|ของฉัน|ของผม|สถานะ)|(ฉัน|ผม).*สมาชิก/.test(s)) return 'live-my-member';
  if (/สมาชิก/.test(s) && /ราคา|กี่บาท|แพ็กเกจ|ค่า/.test(s)) return 'live-member-price';
  if (/แพ็กเกจ|package|โบนัส/.test(s)) return 'live-packages';
  if (/(เว็บ|เมนู).*(หน้า|มีอะไร|เมนู)|หน้า.*อยู่ตรงไหน/.test(s)) return 'live-pages';
  if (/ข่าว.*(ถัดไป|วันนี้|คืนนี้|พรุ่งนี้|สัปดาห์นี้|กี่โมง|เมื่อไหร่)|(nfp|cpi|fomc|ดอกเบี้ย).*(เมื่อไหร่|วันไหน|กี่โมง)/.test(s)) return 'live-news';
  return null;
}

/** คำตอบสด → { t, a, href } (เรียกฝั่งเบราว์เซอร์) */
export async function resolveLive(key, q, ctx = {}) {
  const user = ctx.user || null;
  try {
    if (key === 'plan') {
      const bt = await (await fetch('/backtest.json', { cache: 'no-store' })).json();
      const plans = bt.plans || [];
      const k = planInQuestion(q);
      const per = `ช่วงทดสอบ ${bt.period?.[0] || ''} – ${bt.period?.[1] || ''} · Lot 0.01 · หน่วยเป็นจุดราคา (1 จุด ≈ $1)`;
      if (k) {
        const p = plans.find((x) => Number(x.key) === k);
        if (!p) return { t: `ผลทดสอบ ${PLAN_NAMES[k] || `P${k}`}`, a: 'ยังไม่มีผลทดสอบของแผนนี้', href: '/backtest' };
        const member = MEMBER_PLAN_NUMBERS?.includes?.(k) ? ' · ใช้ได้เฉพาะสมาชิกรายเดือน' : '';
        return {
          t: `ผลทดสอบย้อนหลัง ${PLAN_NAMES[k]}`,
          a: `${p.n} ไม้ · ชนะ ${p.win}% · กำไร ${pts(p.net)} จุด · PF ${p.pf} · Max DD ${Math.round(p.maxdd)} จุด\n` +
            `ครึ่งแรก ${pts(p.half1)} / ครึ่งหลัง ${pts(p.half2)} · 100 ไม้ล่าสุด ${pts(p.last100_net)} (ชนะ ${p.last100_win}%)\n` +
            `กฎ: ${p.rule}${member}\n${per}`,
          href: '/backtest',
        };
      }
      const top = [...plans].sort((a, b) => b.net - a.net).slice(0, 3);
      const s = bt.summary || {};
      // ช่วงล่าสุด = 3 เดือนปฏิทินล่าสุดในตารางกำไรรายเดือน (ตอบคำถาม "ตอนนี้" / "ช่วงนี้")
      const months = [...new Set(plans.flatMap((p) => Object.keys(p.monthly || {})))].sort().slice(-3);
      const recent = plans
        .map((p) => ({ key: p.key, net: months.reduce((t, m) => t + Number(p.monthly?.[m] || 0), 0) }))
        .sort((a, b) => b.net - a.net)
        .slice(0, 3);
      const mLabel = months.length ? `${months[0]} ถึง ${months[months.length - 1]}` : '';
      return {
        t: 'แผนที่กำไรมากที่สุด (ผลทดสอบย้อนหลัง)',
        a: `ช่วงล่าสุด 3 เดือน (${mLabel}): ${recent.map((p, i) => `${i + 1}. ${PLAN_NAMES[p.key]} ${pts(p.net)}`).join(' · ')}\n` +
          `ทั้งช่วงทดสอบ: ${top.map((p, i) => `${i + 1}. ${PLAN_NAMES[p.key]} ${pts(p.net)} (PF ${p.pf})`).join(' · ')}\n` +
          `รวมทุกแผน ${s.trades?.toLocaleString()} ไม้ · ชนะ ${s.win}% · ${pts(s.net)} จุด · PF ${s.pf} · Max DD ${Math.round(s.maxdd || 0)}\n` +
          `ถามเจาะรายแผนได้ เช่น "P6 กำไรเท่าไหร่" · ${per} · ผลในอดีตไม่รับประกันอนาคต`,
        href: '/backtest',
      };
    }
    if (key === 'version') {
      const r = (await (await fetch('/api/release')).json()).release || {};
      const mb = r.size_bytes ? ` · ขนาด ${(r.size_bytes / 1048576).toFixed(1)} MB` : '';
      return { t: 'เวอร์ชันล่าสุดของโปรแกรม', a: `เวอร์ชันล่าสุดคือ ${r.version || '—'}${mb}\nอัปเดตได้จากป้าย "มีเวอร์ชันใหม่" ในโปรแกรม (1-Click) หรือดาวน์โหลดตัวติดตั้งที่หน้าดาวน์โหลด`, href: '/download' };
    }
    if (key === 'packages') {
      const lines = PACKAGES.map((p) => `• ${p.name}: ${p.hours.toLocaleString()} ชม.${p.bonus ? ` + โบนัส ${p.bonus} ชม.` : ''} — ${thb(p.price)}`);
      return { t: 'แพ็กเกจชั่วโมง', a: `${lines.join('\n')}\nคิด 1 บาท/ชม. ที่บอททำงาน · ชำระผ่าน PromptPay แนบสลิปแล้วชั่วโมงเข้าอัตโนมัติ · ส่วนลด Lv./ออนไลน์ใช้ได้`, href: '/store' };
    }
    if (key === 'member') {
      const lines = MEMBERSHIP_PLANS.map((p) => `• ${p.label}: ${thb(p.price)}${p.discountPct ? ` (ลด ${p.discountPct}% จาก ${thb(p.fullPrice)})` : ''}${p.featured ? ' — แนะนำ' : ''}`);
      return { t: 'ราคาสมาชิกรายเดือน', a: `${lines.join('\n')}\nปลดล็อกแผน P6 ขึ้นไป · ยังหักชั่วโมงตามปกติ · ราคาเต็ม (ส่วนลด Lv./ออนไลน์ไม่ใช้กับค่าสมาชิก)`, href: '/store?member=1' };
    }
    if (key === 'news') {
      const ev = ((await (await fetch('/api/calendar')).json()).events || [])
        .filter((e) => e.currency === 'USD' && e.impact === 'High' && new Date(e.date).getTime() > Date.now() - 30 * 60000)
        .slice(0, 5);
      if (!ev.length) return { t: 'ข่าว USD สำคัญถัดไป', a: 'สัปดาห์นี้ไม่มีข่าว USD ผลกระทบสูงที่เหลือแล้ว', href: '/calendar' };
      return {
        t: 'ข่าว USD สำคัญถัดไป (เวลาไทย)',
        a: `${ev.map((e) => `• ${thaiDT(e.date)} น. — ${e.title}${e.forecast ? ` (คาด ${e.forecast} · ก่อน ${e.previous})` : ''}${e.actual ? ` · จริง ${e.actual}` : ''}`).join('\n')}\nช่วง ±15 นาทีรอบข่าวราคามักกระชากและสเปรดถ่าง`,
        href: '/calendar',
      };
    }
    if (key === 'myhours') {
      if (!user) return { t: 'ชั่วโมงคงเหลือของฉัน', a: 'เข้าสู่ระบบก่อน แล้วถามอีกครั้ง หรือดูที่หน้ากระเป๋าเวลา', href: '/dashboard', needLogin: true };
      const h = Number(user.hoursRemaining || 0);
      return { t: 'ชั่วโมงคงเหลือของฉัน', a: `คุณเหลือ ${h.toLocaleString('th-TH', { maximumFractionDigits: 2 })} ชั่วโมง${h <= 5 ? ' — ใกล้หมดแล้ว เติมได้ที่หน้าเติมชั่วโมง' : ''}`, href: h <= 5 ? '/store' : '/dashboard' };
    }
    if (key === 'mymember') {
      if (!user) return { t: 'สถานะสมาชิกของฉัน', a: 'เข้าสู่ระบบก่อน แล้วถามอีกครั้ง หรือดูที่หน้ากระเป๋าเวลา', href: '/dashboard', needLogin: true };
      const m = user.membership || {};
      if (m.viaAdmin) return { t: 'สถานะสมาชิกของฉัน', a: 'บัญชีแอดมินใช้ได้ทุกแผน', href: '/dashboard' };
      if (!m.active) return { t: 'สถานะสมาชิกของฉัน', a: 'ยังไม่ได้เป็นสมาชิกรายเดือน — ใช้ได้ P1–P5 · สมัครเพื่อปลดล็อก P6 ขึ้นไป เริ่ม 99 บาท / 30 วัน', href: '/store?member=1' };
      const until = m.until ? new Date(m.until).toLocaleDateString('th-TH', { timeZone: 'Asia/Bangkok', day: 'numeric', month: 'short', year: 'numeric' }) : '—';
      return { t: 'สถานะสมาชิกของฉัน', a: `เป็นสมาชิกถึง ${until} (เหลือ ${m.daysLeft} วัน)${m.daysLeft <= 3 ? ' — ใกล้หมดอายุ ต่ออายุได้ที่หน้าเติมชั่วโมง' : ''}`, href: '/dashboard' };
    }
    if (key === 'pages') {
      return { t: 'เว็บ GoldBot24 มีหน้าอะไรบ้าง', a: PAGES.map(([, n, d]) => `• ${n} — ${d}`).join('\n'), href: '/' };
    }
  } catch {
    /* ดึงข้อมูลไม่สำเร็จ → ใช้คำตอบสำรอง */
  }
  const doc = LIVE.find((d) => d.live === key);
  return { t: doc?.t || 'ข้อมูล', a: `${doc?.a || ''} (ดึงข้อมูลล่าสุดไม่สำเร็จ ลองใหม่อีกครั้ง)`, href: doc?.href || '/' };
}
