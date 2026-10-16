// ค้นคำตอบจากฐานความรู้ (helpKb.js) แบบไม่ใช้ AI — ภาษาไทยไม่เว้นวรรค จึงเทียบด้วยกลุ่มตัวอักษร 2–3 ตัว (n-gram)
// คำถามที่ใช้คำต่างจากคู่มือแต่ความหมายใกล้กันยังเจอ (ผู้ใช้ขอ 16 ต.ค. 2026) · คะแนน 0–1+ · ต่ำกว่า MIN_SCORE = ไม่พบ
import { FAQ, KB } from './helpKb';

export const MIN_SCORE = 0.45;

// คำสะกดต่างที่ผู้ใช้พิมพ์บ่อย → รูปเดียวกับฐานความรู้
const ALIASES = [
  [/อัพเดท|อัพเดต|อัปเดท|update/g, 'อัปเดต'],
  [/ล็อท|ล๊อต|ลอต/g, 'lot'],
  [/ออร์เดอร์|ออเดอ/g, 'ออเดอร์'],
  [/เทรน(?!ด์)/g, 'เทรนด์'],
  [/ไลน์/g, 'line'],
  [/พาสเวิร์ด|พาส/g, 'รหัสผ่าน'],
  [/ดอลล่าร์|ดอล|usd|\$/g, 'เหรียญ'],
  [/โปรแกรมบอท|บอทเทรด/g, 'บอท'],
  [/ยังไง|อย่างไร|ไง|ทำไง/g, 'ยังไง'],
  [/เท่าไร|เท่าไหร่|กี่บาท/g, 'เท่าไหร่'],
];
// คำเติมที่ไม่ช่วยแยกคำถาม
const STOP = /ครับ|ค่ะ|คะ|นะ|หน่อย|ได้ไหม|ได้มั้ย|ไหม|มั้ย|อยากรู้|สอบถาม|ช่วย|บอก|ว่า|คือ|อะไร|ที่|การ|ของ|และ|หรือ/g;

export function norm(s) {
  let t = String(s || '').toLowerCase();
  for (const [re, rep] of ALIASES) t = t.replace(re, rep);
  return t.replace(/[^฀-๿a-z0-9]+/g, '');
}

function grams(s) {
  const g = new Set();
  for (let n = 2; n <= 3; n += 1) for (let i = 0; i + n <= s.length; i += 1) g.add(s.slice(i, i + n));
  return g;
}

const overlap = (q, d) => {
  if (!q.size) return 0;
  let hit = 0;
  q.forEach((x) => {
    if (d.has(x)) hit += 1;
  });
  return hit / q.size;
};

// เตรียมเอกสาร (ครั้งเดียว)
const DOCS = [
  ...KB.map((e) => ({ ...e, src: 'kb' })),
  ...FAQ.map(([t, a], i) => ({ id: `faq-${i}`, t, k: [], a, href: '/guide#faq', src: 'faq' })),
].map((d) => {
  const head = norm([d.t, ...(d.k || [])].join(' '));
  return { ...d, keys: (d.k || []).map(norm).filter((k) => k.length >= 2), gHead: grams(head), gBody: grams(norm(d.a)) };
});

/** ค้นคำถาม → [{ doc, score }] เรียงคะแนนมากไปน้อย (สูงสุด limit รายการ) */
export function searchHelp(question, limit = 4) {
  const qn = norm(question);
  const core = qn.replace(STOP, '') || qn;
  const gq = grams(core.length >= 2 ? core : qn);
  if (!gq.size) return [];
  const out = DOCS.map((d) => {
    let score = overlap(gq, d.gHead) * 0.75 + overlap(gq, d.gBody) * 0.35;
    // คำค้นของรายการอยู่ในคำถามตรง ๆ (หรือกลับกัน) = เกี่ยวข้องชัด
    const kw = d.keys.filter((k) => qn.includes(k) || (core.length >= 3 && k.includes(core)));
    if (kw.length) score += 0.25 + Math.min(0.15, (kw.reduce((m, k) => Math.max(m, k.length), 0) - 2) * 0.03);
    if (d.src === 'faq') score *= 0.95;
    return { doc: d, score };
  });
  return out.sort((a, b) => b.score - a.score).slice(0, limit);
}

/** คำตอบสำหรับหน้าต่างแชท: { found, best, related[] } */
export function answerHelp(question) {
  const res = searchHelp(question, 4);
  const best = res[0];
  if (!best || best.score < MIN_SCORE) return { found: false, best: best || null, related: res.filter((r) => r.score >= MIN_SCORE * 0.6).slice(0, 3) };
  return { found: true, best, related: res.slice(1).filter((r) => r.score >= Math.max(MIN_SCORE, best.score * 0.6)).slice(0, 2) };
}
