'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { BookOpen, Clock, ExternalLink, Gift, MessageCircle, MonitorSmartphone } from 'lucide-react';
import { CopyButton, PageHeader, StatCard } from './ui';
import { PACKAGES } from '../lib/packages';
import { PLAN_NAMES } from '../lib/plans';
import { LINE_ID, LINE_URL } from '../lib/contact';
import { formatThb } from '../lib/format';

// คู่มือการใช้งานโปรแกรม AI Gold Commander Pro (หน้า /guide) — อ้างอิงพฤติกรรมของโปรแกรมเวอร์ชัน 2026.1007.0830
const SECTIONS = [
  ['prepare', 'สิ่งที่ต้องเตรียม'],
  ['start', 'เริ่มต้นใช้งาน 6 ขั้นตอน'],
  ['screen', 'รู้จักหน้าจอหลัก'],
  ['control', 'แผงควบคุมบอท'],
  ['plans', 'เลือกแผนเทรด'],
  ['margin', 'มาร์จิ้นและจำนวนไม้'],
  ['manual', 'เข้าไม้เอง (BUY / SELL)'],
  ['positions', 'ติดตามไม้ที่เปิดอยู่'],
  ['history', 'ประวัติการเทรด'],
  ['news', 'ข่าวและปฏิทินเศรษฐกิจ'],
  ['ai', 'AI คาดการณ์'],
  ['protect', 'ระบบป้องกันความเสี่ยง'],
  ['hours', 'ซื้อชั่วโมงใช้งาน'],
  ['web', 'เว็บไซต์ GoldBot24'],
  ['update', 'อัปเดตโปรแกรม'],
  ['faq', 'ปัญหาที่พบบ่อย'],
  ['contact', 'ติดต่อแอดมิน'],
  ['risk', 'คำเตือนความเสี่ยง'],
];

const num = (i) => String(i + 1).padStart(2, '0');

function Section({ id, children }) {
  const i = SECTIONS.findIndex(([k]) => k === id);
  return (
    <section id={id} className="card guide-section">
      <div className="card-header">
        <h2>
          <span className="guide-num">{num(i)}</span>
          {SECTIONS[i][1]}
        </h2>
      </div>
      <div className="card-body guide-body">{children}</div>
    </section>
  );
}

/** ปุ่ม/ป้ายที่อ้างถึงในโปรแกรม */
function Ui({ tone, children }) {
  return <span className={`guide-ui ${tone ? `guide-ui-${tone}` : ''}`}>{children}</span>;
}

function Steps({ items, compact }) {
  return (
    <ol className={`guide-steps ${compact ? 'is-compact' : ''}`}>
      {items.map((it, i) => (
        <li key={i}>
          <span className="step-num">{i + 1}</span>
          <div>
            {it.title && <div className="guide-step-title">{it.title}</div>}
            <div className={it.title ? 'muted' : ''}>{it.body}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}

function Note({ tone = 'info', label, children }) {
  return (
    <div className={`guide-note guide-note-${tone}`}>
      <div className="guide-note-label">{label}</div>
      <div>{children}</div>
    </div>
  );
}

function Toc() {
  const [active, setActive] = useState(SECTIONS[0][0]);
  useEffect(() => {
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) return undefined;
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setActive(e.target.id)),
      { rootMargin: '-20% 0px -70% 0px' },
    );
    SECTIONS.forEach(([id]) => {
      const el = document.getElementById(id);
      if (el) io.observe(el);
    });
    return () => io.disconnect();
  }, []);
  return (
    <nav className="card guide-toc" aria-label="สารบัญคู่มือ">
      <div className="guide-toc-title">สารบัญ</div>
      <ol>
        {SECTIONS.map(([id, title], i) => (
          <li key={id}>
            <a href={`#${id}`} className={active === id ? 'is-active' : ''}>
              <span className="mono">{num(i)}</span>
              {title}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

/** จำนวนไม้สูงสุด = มาร์จิ้นว่าง ÷ (มาร์จิ้นต่อไม้ × Lot/0.01) ปัดขึ้น อย่างน้อย 1 ไม้ — สูตรเดียวกับ plan_config.max_positions */
function MarginCalc() {
  const [free, setFree] = useState('960');
  const [per, setPer] = useState('400');
  const [lot, setLot] = useState('0.01');
  const f = parseFloat(free) || 0;
  const perTrade = Math.max(parseFloat(per) || 0, 0) * Math.max(parseFloat(lot) || 0.01, 0.01) / 0.01;
  const n = perTrade > 0 ? Math.max(1, Math.ceil(f / perTrade - 1e-9)) : 1;
  const fmt = (v) => Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 });
  return (
    <form className="guide-calc" onSubmit={(e) => e.preventDefault()} autoComplete="off">
      <div className="guide-calc-inputs">
        <label className="field" htmlFor="calc-free">
          <span className="label">มาร์จิ้นว่าง</span>
          <input id="calc-free" className="input mono" type="number" inputMode="decimal" min="0" step="1" value={free} onChange={(e) => setFree(e.target.value)} />
        </label>
        <label className="field" htmlFor="calc-margin">
          <span className="label">มาร์จิ้นต่อไม้ (ที่ Lot 0.01)</span>
          <input id="calc-margin" className="input mono" type="number" inputMode="decimal" min="10" step="10" value={per} onChange={(e) => setPer(e.target.value)} />
        </label>
        <label className="field" htmlFor="calc-lot">
          <span className="label">Lot</span>
          <input id="calc-lot" className="input mono" type="number" inputMode="decimal" min="0.01" step="0.01" value={lot} onChange={(e) => setLot(e.target.value)} />
        </label>
      </div>
      <div className="guide-calc-result">
        <span className="muted">บอทเปิดได้สูงสุด</span>
        <output htmlFor="calc-free calc-margin calc-lot" className="text-green">{n} ไม้</output>
        <span className="small faint">
          {fmt(f)} ÷ {fmt(perTrade)} ต่อไม้ (ปัดขึ้น)
        </span>
      </div>
    </form>
  );
}

function ScreenMap() {
  return (
    <div className="guide-screen-wrap">
      <div className="guide-screen" role="img" aria-label="แผนผังหน้าจอหลักของโปรแกรม แบ่งเป็นส่วน A ถึง F">
        <div className="guide-zone z-head">
          <span className="guide-zone-key">A</span>
          <b>AI Gold Commander Pro</b>
          <div className="guide-chips">
            <span className="y">32.37 ชม.</span>
            <span className="y">ซื้อชั่วโมง</span>
            <span className="y">ชื่อผู้ใช้ ▾</span>
          </div>
        </div>
        <div className="guide-zone z-cards">
          <span className="guide-zone-key">B</span>
          การ์ดภาพรวม
          <div className="guide-cards">
            <span>บัญชี MT5</span>
            <span>ยอดเงินในพอร์ต</span>
            <span>ราคาทองคำ</span>
            <span>สภาวะตลาด</span>
            <span>แนวรับ–แนวต้าน</span>
          </div>
        </div>
        <div className="guide-zone z-tabs">
          <span className="guide-zone-key">C</span>
          <div className="guide-chips">
            <span className="y">Console</span>
            <span>ออเดอร์ที่เปิดอยู่</span>
            <span>ประวัติการเทรด</span>
            <span>ปฏิทินเศรษฐกิจ</span>
            <span>AI คาดการณ์</span>
          </div>
          <div className="guide-lines">
            <i style={{ width: '92%' }} />
            <i style={{ width: '70%' }} />
            <i style={{ width: '84%' }} />
            <i style={{ width: '58%' }} />
            <i style={{ width: '76%' }} />
          </div>
        </div>
        <div className="z-right">
          <div className="guide-zone">
            <span className="guide-zone-key">D</span>
            <b>ควบคุมบอท</b>
            <div className="guide-chips">
              <span className="go">▶ เริ่มการทำงานบอท</span>
            </div>
            <div className="guide-chips">
              <span>Lot 0.01</span>
              <span>ปิดเมื่อกำไรถึง</span>
            </div>
            <div className="guide-chips">
              <span className="g">▲ BUY</span>
              <span className="r">▼ SELL</span>
              <span>ปิดทั้งหมด</span>
            </div>
          </div>
          <div className="guide-zone">
            <span className="guide-zone-key">E</span>
            <b>ข่าวสำคัญถัดไป</b>
            <div className="guide-chips">
              <span className="r">ผลกระทบสูง</span>
              <span className="y">อีก 16 ชม.</span>
            </div>
          </div>
          <div className="guide-zone">
            <span className="guide-zone-key">F</span>
            <b>แผนเทรด</b>
            <div className="guide-chips">
              {[1, 2, 3, 4, 5].map((n) => (
                <span key={n}>P{n}</span>
              ))}
              <span>เข้าไม้เอง</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const ZONES = [
  ['A', 'แถบหัว', 'ชั่วโมงคงเหลือ (ลดลงเฉพาะตอนบอททำงาน) ปุ่มซื้อชั่วโมง และป้ายชื่อผู้ใช้ คลิกป้ายชื่อเพื่อเปิดเมนู: เปิดเว็บพอร์ตสด, ซื้อชั่วโมงเพิ่ม, สถิติรายแผน, ติดต่อแอดมิน (LINE), ตรวจสอบเวอร์ชันใหม่ และออกจากระบบ'],
  ['B', 'การ์ดภาพรวม', 'บัญชี MT5 ที่เชื่อมต่อ, ยอดเงินและกำไรลอยตัว, ราคาทองพร้อม Ask/Spread, สภาวะตลาด H1/H4 และแนวรับ–แนวต้าน H1/H4 พร้อมแถบสีบอกว่าราคาอยู่ใกล้ฝั่งไหน'],
  ['C', 'แท็บข้อมูล', 'Console (เหตุการณ์สำคัญ เช่น เปิด/ปิดไม้), ออเดอร์ที่เปิดอยู่ (ข้อ 8), ประวัติการเทรด (ข้อ 9), ปฏิทินเศรษฐกิจ (ข้อ 10) และ AI คาดการณ์ (ข้อ 11)'],
  ['D', 'แผงควบคุมบอท', 'เริ่ม/หยุดบอท ตั้ง Lot ตั้งเป้ากำไร และเข้าไม้เอง (ข้อ 4)'],
  ['E', 'ข่าวสำคัญถัดไป', 'ข่าว USD ผลกระทบสูงที่ใกล้ที่สุด พร้อมนับถอยหลัง'],
  ['F', 'แผนเทรด', 'ติ๊กเลือกแผนที่ใช้ และดูจำนวนไม้ อัตราชนะ (WR) และกำไรของแต่ละแผน (ข้อ 5)'],
];

const PLAN_ROWS = [
  [1, 'MA5 ตัด MA13 บนกราฟ 15 นาที ตามเทรนด์ใหญ่ H1 (MA100/150/200 เรียงตัว) และผ่านตัวกรองสัญญาณหลอก (RSI + MA50)', 'SL 1.0 ATR · ไม่ตั้ง TP ปล่อยกำไรวิ่ง ออกเมื่อ MA ตัดกลับ · เลื่อน SL ทุกกำไร 5 จุด (ขั้นแรก 50% / ขั้นถัดไป 40% ของระยะ SL ถึงราคา)'],
  [2, 'MA5 ตัด MA10 บนกราฟ 1 ชม. ตามเทรนด์ H4 และราคาเทียบ MA200', 'SL 0.75 ATR (H1) · ไม่ตั้ง TP · ออกเมื่อ MA ตัดกลับ'],
  [3, 'ราคาหลุดแนวรับ/ต้าน H1 เพื่อกวาด Stop แล้วดึงกลับพร้อมไส้เทียน 0.4–1.0 ATR ตามเทรนด์ H1 (MA100/150/200 เรียงตามทิศ) และ AI ยืนยัน', 'SL 1.0 ATR · TP 2.0 ATR · เลื่อน SL ทุกกำไร 5 จุด (ขั้นแรก 50% / ขั้นถัดไป 40%)'],
  [4, 'ราคาเด้งจากโซนแนวรับ/ต้าน H1 พร้อมสัญญาณ RSI Divergence และ AI ยืนยัน', 'SL 0.75 ATR · TP 1.5 เท่า · เลื่อน SL ทุกกำไร 5 จุด (ขั้นแรก 50% / ขั้นถัดไป 40%)'],
  [5, 'ราคาหลุดขอบ Bollinger Bands H1 แล้วกลับเข้ากรอบ พร้อม Divergence, MACD หมดแรง และ AI ยืนยัน', 'SL 0.75 ATR · TP 1.5 เท่า · เลื่อน SL ทุกกำไร 5 จุด (ขั้นแรก 50% / ขั้นถัดไป 40%)'],
];

const CLOSE_REASONS = [
  ['🎯', 'ชน TP'],
  ['⛔', 'ชน SL'],
  ['🔒', 'ชน SL ที่ล็อกกำไรไว้แล้ว'],
  ['💰', 'ถึงเป้า “ปิดเมื่อกำไรถึง”'],
  ['🤖', 'บอทปิด (MA ตัดกลับ หรือ AI กลับทิศ)'],
  ['✋', 'ปิดเอง ในโปรแกรมหรือใน MT5'],
  ['⚠', 'Stop Out (มาร์จิ้นไม่พอ)'],
];

const PROTECTIONS = [
  ['พักเมื่อแพ้ติดกัน', 'แพ้ 2 ไม้ติดกัน หยุดเข้าไม้ใหม่ 60 นาที'],
  ['บล็อกทิศเดิม', 'แผนใดแพ้ จะไม่เข้าทิศเดิมซ้ำ 60 นาที (ปลดเมื่อชนะ)'],
  ['พักหลังปิดไม้', 'เว้น 10 นาทีหลังปิดไม้ กันการเข้าซ้ำตอนราคาสะบัด'],
  ['1 ไม้ต่อ 1 สัญญาณ', 'P1/P2 ไม่เข้าซ้ำบนสัญญาณ MA ตัดเดิม'],
  ['จำกัดจำนวนไม้', 'ตามมาร์จิ้นว่าง (ข้อ 6)'],
  ['ล็อกกำไร', 'กำไรถึง 70% ของเป้า เลื่อน SL มาล็อกกำไร +0.35 ATR'],
  ['ขยาย TP', 'กำไรถึง 80% ของเป้าและ AI ยังมั่นใจ ≥ 54% ขยาย TP อีก 1 ATR'],
  ['เลื่อน SL ขั้นบันได', 'P1, P3, P4, P5: ทุกกำไร 5 จุด เลื่อน SL เข้าหาราคา ขั้นแรก 50% ขั้นถัดไป 40% ของระยะ SL ถึงราคา (เช่น SELL เข้า 4,125.57 SL 4,131.85: กำไร +5 → SL 4,126.21 · +10 → 4,121.95 · +15 → 4,117.40)'],
  ['AI กลับทิศ', 'AI กลับทิศแรง (≥ 60%) และราคาย้อนผ่านจุดเข้า บอทปิดไม้เพื่อจำกัดขาดทุน'],
  ['ตามเทรนด์ใหญ่', 'P3–P5 ไม่เข้าสวนเทรนด์ H4 เมื่อตลาดมีแนวโน้มชัด'],
];

const WEB_PAGES = [
  ['/', 'พอร์ตสด', 'บัญชี ไม้ที่เปิด AI คาดการณ์ แท่งเทียน กำไรรายวัน และข่าว'],
  ['/dashboard', 'กระเป๋าเวลา & สถิติ', 'ชั่วโมงคงเหลือ เติม Product Key และสถิติรายแผน'],
  ['/calendar', 'ปฏิทินข่าว', 'ข่าวเศรษฐกิจรายสัปดาห์ พร้อมผลต่อทอง'],
  ['/backtest', 'แผนเทรด', 'ผลทดสอบย้อนหลังของแต่ละแผน'],
  ['/store', 'ซื้อชั่วโมง', 'เลือกแพ็กเกจและชำระผ่านพร้อมเพย์'],
  ['/my-keys', 'คีย์ของฉัน', 'Product Key ที่ซื้อไว้'],
  ['/receipts', 'ใบเสร็จ', 'ดูและพิมพ์ใบเสร็จย้อนหลัง'],
  ['/download', 'ดาวน์โหลด', 'ตัวติดตั้งโปรแกรมเวอร์ชันล่าสุด'],
];

const FAQ = [
  ['โปรแกรมขึ้นว่าเชื่อมต่อ MT5 ไม่ได้', 'เปิด MetaTrader 5 และล็อกอินบัญชี FBS ทิ้งไว้ก่อนเปิดโปรแกรม และตรวจว่าเปิด Algo Trading แล้ว'],
  ['เริ่มบอทแล้ว แต่ยังไม่เข้าไม้', 'เป็นเรื่องปกติ บอทเข้าไม้เฉพาะเมื่อเงื่อนไขครบ บางวันอาจไม่มีไม้เลย ให้ตรวจว่าติ๊กเลือกแผนไว้แล้ว ช่อง “ออเดอร์ / สูงสุด” ยังไม่เต็ม และบอทไม่ได้อยู่ในช่วงพักหลังแพ้ติดกัน เหตุผลที่บอทข้ามสัญญาณจะแสดงใน Console'],
  ['ปิดโปรแกรมหรือปิดคอมแล้ว ไม้ที่เปิดอยู่จะเป็นอย่างไร', 'ไม้ยังอยู่ใน MT5 พร้อม SL/TP เดิม แต่การดูแลของบอท เช่น ล็อกกำไร เลื่อน SL และปิดเมื่อ MA ตัดกลับ จะหยุดจนกว่าจะเปิดบอทอีกครั้ง ไม้ของ P1 และ P2 ไม่มี TP ระหว่างนั้นจึงออกได้ทาง SL เท่านั้น ถ้าต้องการให้บอททำงานตลอด แนะนำใช้ VPS'],
  ['ชั่วโมงหมดระหว่างบอททำงาน', 'บอทจะหยุดทำงาน ไม้ที่เปิดอยู่ยังอยู่ใน MT5 พร้อม SL/TP เดิม ซื้อชั่วโมงเพิ่มแล้วกดเริ่มบอทอีกครั้ง'],
  ['Windows เตือนตอนติดตั้ง', 'กด More info แล้ว Run anyway ดาวน์โหลดไฟล์จากหน้าดาวน์โหลดของเว็บ GoldBot24 เท่านั้น'],
  ['ลืมรหัสผ่าน', 'กด “ลืมรหัสผ่าน” ที่หน้าเข้าสู่ระบบ ระบบจะส่งรหัส 6 หลักทางอีเมล (ใช้ได้ 15 นาที) แล้วตั้งรหัสใหม่ได้ทันที'],
  ['ใส่รหัสผ่านผิดหลายครั้งจนเข้าไม่ได้', 'ใส่ผิด 5 ครั้ง บัญชีจะถูกล็อกชั่วคราว 15 นาที รอแล้วลองใหม่ หรือติดต่อแอดมินให้ปลดล็อก'],
  ['ชำระเงินแล้ว แต่ชั่วโมงไม่เข้า', 'ตรวจว่าแนบสลิปในหน้าชำระเงินแล้ว ถ้ายังไม่เข้า ให้ส่งสลิปพร้อมอีเมลที่ใช้สมัครมาทาง LINE'],
  ['ตัวเลขบนเว็บไม่ตรงกับในโปรแกรม', 'เว็บรับข้อมูลจากโปรแกรมทุก 5 วินาที ตรวจว่าเปิดโปรแกรมไว้และเชื่อมต่ออินเทอร์เน็ตอยู่'],
];

export default function GuideContent() {
  return (
    <div className="container page">
      <PageHeader
        eyebrow="คู่มือการใช้งาน"
        icon={BookOpen}
        title="คู่มือการใช้งาน AI Gold Commander Pro"
        description="ตั้งแต่สมัครสมาชิก ติดตั้งโปรแกรม เริ่มบอท ไปจนถึงการติดตามไม้และการซื้อชั่วโมงใช้งาน"
      />

      <div className="grid grid-4" style={{ marginBottom: 28 }}>
        <StatCard icon={Clock} label="ค่าบริการ" value="1 บาท/ชม." sub="คิดเฉพาะตอนบอททำงาน" tone="gold" />
        <StatCard icon={Gift} label="สมาชิกใหม่" value="ฟรี 48 ชม." sub="หลังยืนยันอีเมล" tone="green" />
        <StatCard icon={MonitorSmartphone} label="ใช้งานกับ" value="Windows + MT5" sub="Windows 10/11 หรือ VPS · บัญชี FBS" />
        <StatCard icon={MessageCircle} label="ติดต่อแอดมิน" value={`LINE ${LINE_ID}`} sub="ดูข้อ 17" tone="green" />
      </div>

      <div className="guide-layout">
        <aside className="guide-aside">
          <Toc />
        </aside>

        <div className="guide-doc">
          <Section id="prepare">
            <ul>
              <li>คอมพิวเตอร์ <strong>Windows 10 หรือ 11</strong> ที่เปิดทิ้งไว้ได้ระหว่างบอททำงาน หรือ <strong>VPS</strong> ถ้าต้องการให้บอทรันตลอด 24 ชั่วโมง</li>
              <li>โปรแกรม <strong>MetaTrader 5</strong> และบัญชีเทรดของ <strong>FBS</strong> (แนะนำให้เริ่มจากบัญชี Demo)</li>
              <li><strong>อีเมลที่ใช้งานได้</strong> สำหรับรับรหัสยืนยันตอนสมัครและตอนลืมรหัสผ่าน</li>
              <li>อินเทอร์เน็ตที่เสถียร</li>
            </ul>
          </Section>

          <Section id="start">
            <Steps
              items={[
                { title: 'สมัครสมาชิก', body: 'สมัครที่เว็บนี้ (ปุ่มเข้าสู่ระบบมุมขวาบน) หรือที่หน้าเข้าสู่ระบบของโปรแกรม จากนั้นใส่รหัสยืนยัน 6 หลักที่ส่งไปทางอีเมล สมาชิกใหม่ได้เวลาใช้งานฟรี 48 ชม.' },
                { title: 'ดาวน์โหลดตัวติดตั้ง', body: <>เปิดหน้า <Link href="/download">ดาวน์โหลด</Link> แล้วกดดาวน์โหลดไฟล์ <span className="mono">GoldBot24_Setup_v….exe</span> (ประมาณ 57 MB)</> },
                { title: 'ติดตั้งโปรแกรม', body: <>ดับเบิลคลิกไฟล์ แล้วกด Next จนเสร็จ ไม่ต้องใช้สิทธิ์ Admin ถ้า Windows ขึ้น “Windows protected your PC” ให้กด <Ui>More info</Ui> แล้ว <Ui>Run anyway</Ui> ติดตั้งเสร็จจะมีไอคอนบน Desktop และใน Start Menu</> },
                { title: 'เปิด MetaTrader 5', body: <>ล็อกอินบัญชี FBS ใน MT5 ทิ้งไว้ และกดปุ่ม <Ui>Algo Trading</Ui> บนแถบเครื่องมือให้เป็นสีเขียว</> },
                { title: 'เข้าสู่ระบบโปรแกรม', body: <>เปิดโปรแกรม <strong>AI Gold Commander Pro</strong> แล้วเข้าสู่ระบบด้วยอีเมลและรหัสผ่านเดียวกับเว็บ ถ้าติ๊ก <Ui>จดจำการเข้าสู่ระบบในเครื่องนี้</Ui> ครั้งต่อไปไม่ต้องกรอกใหม่ ข้อมูลถูกเข้ารหัสเก็บไว้ในเครื่อง</> },
                { title: 'ตั้งค่า แล้วเริ่มบอท', body: <>ตรวจขนาดไม้ (Lot) และแผนเทรดที่ติ๊กไว้ แล้วกด <Ui tone="gold">▶ เริ่มการทำงานบอท</Ui> ที่แผงควบคุมด้านขวา บอทจะเริ่มสแกนตลาดและเข้าไม้เองเมื่อเงื่อนไขครบ</> },
              ]}
            />
            <Note tone="gold" label="คำแนะนำ">เริ่มด้วยบัญชี Demo และ Lot 0.01 ดูการทำงานสัก 1–2 สัปดาห์ก่อนใช้เงินจริง</Note>
          </Section>

          <Section id="screen">
            <p>หน้าจอแบ่งเป็น 6 ส่วน ตัวอักษรในแผนผังตรงกับคำอธิบายด้านล่าง</p>
            <ScreenMap />
            <ul className="guide-legend">
              {ZONES.map(([k, title, text]) => (
                <li key={k}>
                  <span className="guide-zone-key">{k}</span>
                  <div>
                    <strong>{title}</strong> <span className="muted">{text}</span>
                  </div>
                </li>
              ))}
            </ul>

            <h3>อ่านการ์ดสภาวะตลาด</h3>
            <p>บอกทิศของตลาดจากการเรียงตัวของเส้นค่าเฉลี่ย MA50, MA100 และ MA150 ทั้งกราฟ 1 ชม. (H1) และ 4 ชม. (H4)</p>
            <ul>
              <li><strong className="text-green">▲ Uptrend</strong>: MA50 &gt; MA100 &gt; MA150 (เรียงขึ้น)</li>
              <li><strong className="text-red">▼ Downtrend</strong>: MA50 &lt; MA100 &lt; MA150 (เรียงลง)</li>
              <li><strong className="text-sky">◆ Sideway</strong>: เส้นเรียงสลับกัน ตลาดแกว่งในกรอบ</li>
            </ul>
            <p>ป้ายมุมขวาของการ์ด เช่น <Ui tone="sell">SELL เท่านั้น</Ui> คือทิศที่แผน P3–P5 อนุญาตให้เข้าตามเทรนด์ใหญ่ H4</p>

            <h3>การ์ดและแถวที่คลิกได้</h3>
            <div className="table-wrap guide-table-wrap">
              <table className="table guide-table">
                <thead>
                  <tr><th>คลิกที่</th><th>จะเห็น</th></tr>
                </thead>
                <tbody>
                  <tr><td className="nowrap">ยอดเงินในพอร์ต</td><td>กราฟแท่งกำไร/ขาดทุนรายวัน เลือกช่วง 7, 14, 30 วัน, เดือนนี้, 90 วัน หรือกำหนดวันที่เอง</td></tr>
                  <tr><td className="nowrap">ราคาทองคำ</td><td>กราฟแท่งเทียน M15 เรียลไทม์ เลือกได้ 16–500 แท่ง (ค่าเริ่มต้น 120) พร้อมเส้น MA5/MA13, Bid/Ask และไม้ที่เปิดอยู่</td></tr>
                  <tr><td className="nowrap">สภาวะตลาด</td><td>คำอธิบายว่าทำไมตอนนี้เป็น Uptrend, Downtrend หรือ Sideway และกฎที่แต่ละแผนใช้</td></tr>
                  <tr><td className="nowrap">มาร์จิ้นว่าง ›</td><td>ตั้งมาร์จิ้นต่อ 1 ไม้ (ข้อ 6)</td></tr>
                  <tr><td className="nowrap">แถวในออเดอร์ที่เปิดอยู่</td><td>กราฟ M15 80 แท่งของไม้นั้นแบบเรียลไทม์ พร้อมอินดิเคเตอร์ของแผน (ข้อ 8)</td></tr>
                  <tr><td className="nowrap">แถวในประวัติการเทรด</td><td>กราฟและอินดิเคเตอร์ ณ ตอนที่ปิดไม้ (ข้อ 9)</td></tr>
                </tbody>
              </table>
            </div>
            <Note tone="info" label="หน้าต่างกราฟ">
              ขยายเต็มจอได้ด้วยปุ่ม <Ui>ขยายเต็มจอ</Ui> หรือกด <kbd>F11</kbd> และกด <kbd>Esc</kbd> เพื่อกลับ หน้าต่างย่อยทุกอันจะอยู่ด้านหน้าสุดเสมอ ถ้าต้องการใช้โปรแกรมอื่นระหว่างนั้น ให้กดย่อหน้าต่าง
            </Note>
          </Section>

          <Section id="control">
            <div className="table-wrap guide-table-wrap">
              <table className="table guide-table">
                <thead>
                  <tr><th>ส่วน</th><th>ใช้ทำอะไร</th></tr>
                </thead>
                <tbody>
                  <tr><td className="nowrap"><Ui tone="gold">▶ เริ่มการทำงานบอท</Ui></td><td>เริ่มบอท ระหว่างทำงานปุ่มจะเปลี่ยนเป็น <Ui>⏸ หยุดชั่วคราว</Ui> กดแล้วเป็น <Ui>▶ ทำงานต่อ</Ui> ระบบหักชั่วโมงเฉพาะตอนบอททำงาน</td></tr>
                  <tr><td className="nowrap">Lot</td><td>ขนาดไม้ที่บอทใช้เปิดไม้ใหม่ ค่าเริ่มต้น 0.01 และจำค่าที่ตั้งไว้</td></tr>
                  <tr><td className="nowrap">ปิดเมื่อกำไรถึง</td><td>ติ๊กเพื่อเปิดใช้แล้วใส่จำนวนเงิน เมื่อไม้ใดมีกำไร (รวม swap) ถึงค่าที่ตั้ง บอทจะปิดไม้นั้นทันที ใช้กับทุกแผนและไม้ที่เข้าเอง ค่าเริ่มต้นคือปิดใช้งาน</td></tr>
                  <tr><td className="nowrap">ออเดอร์ / สูงสุด</td><td>จำนวนไม้ที่เปิดอยู่เทียบกับจำนวนสูงสุดที่มาร์จิ้นรองรับ ตัวเลขเป็นสีแดงเมื่อเต็ม</td></tr>
                  <tr><td className="nowrap">กำไรลอยตัว</td><td>กำไร/ขาดทุนรวมของไม้ที่ยังเปิดอยู่</td></tr>
                  <tr><td className="nowrap">มาร์จิ้นว่าง ›</td><td>มาร์จิ้นที่เหลือ คลิกเพื่อตั้งมาร์จิ้นต่อไม้ (ข้อ 6)</td></tr>
                  <tr><td className="nowrap">เวลาทำงาน</td><td>เวลาที่บอททำงานในรอบนี้</td></tr>
                  <tr><td className="nowrap"><Ui tone="buy">▲ BUY</Ui> <Ui tone="sell">▼ SELL</Ui></td><td>เข้าไม้เองทันที (ข้อ 7)</td></tr>
                  <tr><td className="nowrap">ปิดทั้งหมด (n)</td><td>ปิดทุกไม้ที่เปิดอยู่ ต้องกดยืนยันก่อน</td></tr>
                  <tr><td className="nowrap">เสียง</td><td>เปิด/ปิดเสียงแจ้งเตือน เช่น เปิดไม้, ชน TP, ชน SL และเลื่อน SL</td></tr>
                </tbody>
              </table>
            </div>
            <p>แท็บ <strong>Console</strong> แสดงเฉพาะเหตุการณ์สำคัญแยกสีตามประเภท และล้างข้อความอัตโนมัติทุก 1 ชม. ถ้าไม่ต้องการ ให้เอาติ๊ก <Ui>ล้างอัตโนมัติทุก 1 ชม.</Ui> ออก</p>
          </Section>

          <Section id="plans">
            <p>ติ๊กช่องหน้าชื่อแผนในการ์ด <strong>แผนเทรด</strong> เพื่อเลือกแผนที่ให้บอทใช้ ระบบจำการเลือกแยกตามบัญชี ถ้าแอดมินปิดแผนใด ช่องของแผนนั้นจะเป็นสีเทา ติ๊กไม่ได้ และมีคำว่า “แอดมินปิด” ต่อท้าย</p>
            <div className="table-wrap guide-table-wrap">
              <table className="table guide-table">
                <thead>
                  <tr><th>แผน</th><th>เข้าไม้เมื่อ</th><th>ออกจากไม้</th></tr>
                </thead>
                <tbody>
                  {PLAN_ROWS.map(([n, entry, exit]) => (
                    <tr key={n}>
                      <td className="nowrap guide-plan">{PLAN_NAMES[n]}</td>
                      <td>{entry}</td>
                      <td>{exit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul>
              <li>แถว <strong>เข้าไม้เอง</strong> แสดงสถิติไม้ที่กด BUY/SELL เอง และแถว <strong>รวมทุกแผน</strong> สรุปจำนวนไม้ อัตราชนะ และกำไรรวม</li>
              <li>เมื่อแผนใดกำลังถือไม้ ชื่อแผนจะเป็นสีเขียวและมีป้าย <Ui tone="buy">● BUY</Ui> หรือ <Ui tone="sell">● SELL</Ui></li>
              <li>P3–P5 เข้าไม้ตามทิศเทรนด์ H4 เท่านั้นเมื่อตลาดมีแนวโน้มชัด และเข้าได้ทั้งสองฝั่งเมื่อตลาดไซด์เวย์</li>
            </ul>
            <Note tone="info" label="ATR คืออะไร">
              ATR คือความผันผวนเฉลี่ยต่อแท่ง บอทใช้กำหนดระยะ SL ให้เหมาะกับสภาพตลาดในตอนนั้น ดูผลทดสอบย้อนหลังของแต่ละแผนได้ที่หน้า <Link href="/backtest">แผนเทรด</Link>
            </Note>
          </Section>

          <Section id="margin">
            <p>บอทจำกัดจำนวนไม้ที่เปิดพร้อมกันตามมาร์จิ้นว่าง ค่าเริ่มต้นคือ <strong>มาร์จิ้น 400 ต่อ 1 ไม้ที่ Lot 0.01</strong> นับแบบปัดเศษขึ้น และเปิดได้อย่างน้อย 1 ไม้เสมอ</p>
            <div className="table-wrap guide-table-wrap">
              <table className="table guide-table">
                <thead>
                  <tr><th>มาร์จิ้นว่าง (ตั้งไว้ 400 ต่อไม้)</th><th className="num">เปิดได้สูงสุด</th></tr>
                </thead>
                <tbody>
                  <tr><td>ไม่เกิน 400</td><td className="num">1 ไม้</td></tr>
                  <tr><td>401 – 800</td><td className="num">2 ไม้</td></tr>
                  <tr><td>801 – 1,200 (เช่น 960)</td><td className="num">3 ไม้</td></tr>
                </tbody>
              </table>
            </div>
            <p>ถ้าใช้ Lot ใหญ่ขึ้น มาร์จิ้นต่อไม้จะคูณตาม เช่น Lot 0.02 นับ 800 ต่อไม้</p>
            <h3>ลองคำนวณ</h3>
            <MarginCalc />
            <h3>เปลี่ยนมาร์จิ้นต่อไม้</h3>
            <Steps
              compact
              items={[
                { body: <>คลิกช่อง <Ui>มาร์จิ้นว่าง ›</Ui> ในแผงควบคุม</> },
                { body: 'พิมพ์ค่าเอง หรือกดปุ่มลัด 200, 300, 400, 500, 800 หน้าต่างจะคำนวณจำนวนไม้สูงสุดให้ทันที' },
                { body: <>กด <Ui tone="gold">บันทึก</Ui> ระบบจำค่าแยกตามบัญชี</> },
              ]}
            />
            <p className="muted">ตั้งค่าสูงขึ้น บอทจะเปิดพร้อมกันได้น้อยไม้ลงและปลอดภัยขึ้น ตั้งต่ำลงจะเปิดได้หลายไม้แต่เสี่ยงขึ้น มาร์จิ้นว่างลดลงทุกครั้งที่เปิดไม้ จำนวนสูงสุดจึงลดลงตามได้</p>
          </Section>

          <Section id="manual">
            <Steps
              compact
              items={[
                { body: <>กด <Ui tone="buy">▲ BUY</Ui> หรือ <Ui tone="sell">▼ SELL</Ui> ที่แผงควบคุม</> },
                { body: 'หน้าต่างยืนยันแสดงราคาสด Lot ที่ตั้งไว้ SL (ค่าเริ่มต้น 1.0 ATR) และ TP (1.5 เท่าของ SL) พร้อมจำนวนเงินที่เสี่ยงและเป้ากำไร' },
                { body: 'ปรับ SL/TP ด้วยปุ่ม − / + (ครั้งละ 0.5 จุด) หรือปุ่มลัด SL 0.5 / 1 / 1.5 ATR หรือเลือกไม่ตั้ง TP' },
                { body: 'กดยืนยันเพื่อส่งคำสั่ง' },
              ]}
            />
            <ul>
              <li>ต้องเข้าสู่ระบบและมีชั่วโมงคงเหลือ</li>
              <li>ระหว่างบอททำงาน บอทดูแลไม้นี้ต่อด้วยการล็อกกำไร การปิดเมื่อ AI กลับทิศ และ “ปิดเมื่อกำไรถึง” (ถ้าเปิดใช้)</li>
              <li>ไม้ที่เข้าเองแสดงในการ์ดแผนเทรดแถว “เข้าไม้เอง” และในประวัติเป็นแผน <span className="mono">Manual-Quick</span></li>
            </ul>
          </Section>

          <Section id="positions">
            <p>แท็บ <strong>ออเดอร์ที่เปิดอยู่</strong> แสดงทุกไม้แบบเรียลไทม์: ฝั่ง แผน Lot ราคาเข้า ราคาปัจจุบัน SL TP เวลาที่ถือ และกำไร (รวม swap) พร้อมปุ่ม <Ui tone="sell">ปิด</Ui> สำหรับปิดทีละไม้</p>
            <ul>
              <li>สัญลักษณ์กุญแจหน้า SL หมายถึงบอทเลื่อน SL มาล็อกกำไรแล้ว ถ้าราคากลับตัวก็ยังปิดได้กำไร</li>
              <li>TP ที่ขึ้นว่า “รันเทรนด์” คือไม้ที่ไม่ตั้ง TP (P1, P2) บอทจะปิดเมื่อเส้น MA ตัดกลับ</li>
              <li>คอลัมน์ <strong>ถ้าชน SL</strong> บอกว่าถ้าราคาชน SL ตอนนี้จะได้หรือเสียเท่าไร สีฟ้า = ล็อกกำไรแล้ว สีแดง = ยังเสี่ยงขาดทุน</li>
              <li>คอลัมน์ <strong>AI แนะนำ</strong> ท้ายแถวแสดง <Ui tone="buy">ถือต่อ</Ui> <Ui tone="gold">ระวัง</Ui> หรือ <Ui tone="sell">ควรปิด</Ui> ชี้ที่ป้ายเพื่อดูเหตุผลหลัก</li>
            </ul>
            <h3>AI วิเคราะห์ไม้ที่ถืออยู่</h3>
            <p>แผงใต้ตารางให้คำแนะนำแต่ละไม้เป็น <Ui tone="buy">แนะนำถือต่อ</Ui> <Ui tone="gold">ถือต่อแบบระวัง</Ui> หรือ <Ui tone="sell">แนะนำปิดไม้</Ui> พร้อมคะแนนและเหตุผล ✓ หนุนไม้, ✗ สวนไม้ และ • กลาง โดยดูจาก:</p>
            <ul>
              <li>เทรนด์ H1/H4, MA200, โมเมนตัม M15 และแนวรับ/ต้าน</li>
              <li>AI คาดการณ์ 1–4 ชม. และสัญญาณออกของแผนเอง</li>
              <li>ระยะ SL/TP และข่าวแรงที่ใกล้จะออก</li>
            </ul>
            <p>คำแนะนำอัปเดตทุก 30 วินาที เป็นข้อมูลประกอบการตัดสินใจ บอทไม่ปิดไม้ตามคำแนะนำนี้เอง</p>
            <h3>คลิกไม้เพื่อดูกราฟ</h3>
            <p>คลิกที่แถวไม้เพื่อเปิดกราฟ M15 80 แท่งแบบเรียลไทม์ ในหน้าต่างมี:</p>
            <ul>
              <li>การ์ด Lot, ราคาเข้า, ราคาปัจจุบัน, SL (ล็อกกำไรหรือเสี่ยงเท่าไร), TP (เหลืออีกกี่จุด) และเวลาที่ถือ</li>
              <li>เส้นราคาเข้า, SL, TP และจุดเข้าไม้บนกราฟ</li>
              <li>อินดิเคเตอร์ที่แผนนั้นใช้ จุดเขียวคือค่าที่หนุนไม้ และจุดแดงคือค่าที่สวนไม้</li>
            </ul>
          </Section>

          <Section id="history">
            <p>ดึงจาก MT5 โดยตรง ย้อนหลัง 90 วัน หน้าละ 10 รายการ ด้านบนสรุปจำนวนไม้ ชนะ/แพ้ และกำไรสุทธิ กด <Ui>↻ รีเฟรช</Ui> เพื่อโหลดใหม่ คอลัมน์ <strong>ปิดโดย</strong> บอกวิธีที่ไม้ถูกปิด:</p>
            <ul className="guide-reasons">
              {CLOSE_REASONS.map(([icon, text]) => (
                <li key={text}>
                  <span aria-hidden="true">{icon}</span>
                  <span>{text}</span>
                </li>
              ))}
            </ul>
            <h3>คลิกรายการเพื่อดูภาพตอนปิดไม้</h3>
            <ul>
              <li>กราฟ M15 80 แท่งจนถึงแท่งที่ปิด</li>
              <li>SL/TP ตอนปิด, เส้นการเลื่อน SL/TP ระหว่างถือ และจุดปิดไม้</li>
              <li>อินดิเคเตอร์ของแผน ณ เวลาที่ปิด</li>
              <li>สรุปไม้: ผลลัพธ์, กำไรสูงสุดและติดลบสูงสุดระหว่างถือ, SL/TP ตอนเข้าเทียบตอนปิด</li>
            </ul>
            <p className="muted">เวลาในตารางเป็นเวลาเซิร์ฟเวอร์ MT5 ส่วนหน้าต่างกราฟแสดงเป็นเวลาไทย</p>
          </Section>

          <Section id="news">
            <ul>
              <li>แท็บ <strong>ปฏิทินเศรษฐกิจ</strong> แสดงข่าวทั้งสัปดาห์เป็นเวลาไทย กรองเฉพาะ USD และระดับผลกระทบได้</li>
              <li>คอลัมน์ <strong>ผลต่อทอง</strong> บอกทิศที่ข่าวน่าจะส่งผลต่อราคาทอง และขนาดการขยับโดยเฉลี่ยใน 60 นาที จากสถิติราคาทองย้อนหลังประมาณ 2 ปี</li>
              <li>ชี้ที่ชื่อข่าวเพื่อดูคำแปลภาษาไทย คลิกข่าวเพื่อดูรายละเอียดและที่มาของตัวเลข</li>
              <li>การ์ด <strong>ข่าวสำคัญถัดไป</strong> นับถอยหลังข่าว USD ผลกระทบสูง เช่น NFP, CPI และ FOMC</li>
            </ul>
            <p>ดูปฏิทินบนเว็บได้ที่หน้า <Link href="/calendar">ปฏิทินข่าว</Link></p>
            <Note tone="red" label="ข้อควรระวัง">ช่วง 15–30 นาทีรอบข่าวแรง สเปรดมักกว้างและราคาสะบัดแรง ไม้อาจชน SL เร็วกว่าปกติ</Note>
          </Section>

          <Section id="ai">
            <p>แท็บ <strong>AI คาดการณ์</strong> ทายทิศราคาทอง 3 ช่วงเวลา คือ 1 ชม., 4 ชม. และ 1 วัน แต่ละช่วงแสดงความมั่นใจและความแม่นในอดีตจากการทดสอบย้อนหลัง 2.5 ปี พร้อมปัจจัยประกอบ ▲ ขึ้น, ▼ ลง และ • กลาง ได้แก่ เทรนด์ H1/H4, MA200, โมเมนตัม M15, แนวรับ/ต้าน และข่าวแรงใน 24 ชม.</p>
            <div className="table-wrap guide-table-wrap">
              <table className="table guide-table">
                <thead>
                  <tr><th>กรณี</th><th className="num">แม่นในอดีต</th></tr>
                </thead>
                <tbody>
                  <tr><td>1 ชม. (ใกล้เคียงการเดา)</td><td className="num">≈ 52%</td></tr>
                  <tr><td>1 วัน เมื่อ AI มั่นใจ ≥ 60% และเทรนด์ไปทางเดียวกัน</td><td className="num">≈ 63.7%</td></tr>
                </tbody>
              </table>
            </div>
            <p>ถ้า AI มั่นใจต่ำกว่า 55% ทิศจะขึ้นว่า “ไม่ชัด” ข้อมูลอัปเดตทุก 1 นาที ใช้ประกอบการตัดสินใจเท่านั้น ไม่ใช่สัญญาณซื้อขาย</p>
          </Section>

          <Section id="protect">
            <div className="table-wrap guide-table-wrap">
              <table className="table guide-table">
                <thead>
                  <tr><th>ระบบ</th><th>ทำงานอย่างไร</th></tr>
                </thead>
                <tbody>
                  {PROTECTIONS.map(([name, text]) => (
                    <tr key={name}>
                      <td className="nowrap">{name}</td>
                      <td>{text}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          <Section id="hours">
            <div className="table-wrap guide-table-wrap">
              <table className="table guide-table">
                <thead>
                  <tr><th>แพ็กเกจ</th><th className="num">ชั่วโมงที่ได้</th><th className="num">ราคา</th></tr>
                </thead>
                <tbody>
                  {PACKAGES.map((p) => (
                    <tr key={p.id}>
                      <td className="nowrap">{p.name}</td>
                      <td className="num">
                        {(p.hours + (p.bonus || 0)).toLocaleString('th-TH')} ชม.{p.bonus ? ` (แถม ${p.bonus})` : ''}
                      </td>
                      <td className="num">{formatThb(p.price)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Steps
              compact
              items={[
                { body: <>กดปุ่ม <Ui tone="gold">ซื้อชั่วโมง</Ui> มุมขวาบนของโปรแกรม หรือเปิดหน้า <Link href="/store">ซื้อชั่วโมง</Link> แล้วเลือกแพ็กเกจ</> },
                { body: 'สแกน QR พร้อมเพย์และโอนตามยอดภายใน 15 นาที' },
                { body: <>แนบสลิป: กด <kbd>Ctrl</kbd>+<kbd>V</kbd> วางรูป ลากไฟล์มาวาง หรือแตะเพื่อเลือกรูป</> },
                { body: <>ระบบตรวจสลิปอัตโนมัติ ผ่านแล้วชั่วโมงเข้าบัญชีทันที และส่งใบเสร็จทางอีเมล ดูย้อนหลังได้ที่หน้า <Link href="/receipts">ใบเสร็จ</Link></> },
              ]}
            />
            <ul>
              <li>QR หมดเวลาแล้ว ยังแนบสลิปได้อีก 10 นาที ถ้าโอนแล้วแต่คำสั่งซื้อถูกยกเลิก ยังแนบสลิปได้ภายใน 24 ชม.</li>
              <li>สลิปบางธนาคาร เช่น SCB และ BBL ธนาคารอาจให้รอสักครู่ ระบบจะนับถอยหลังและตรวจซ้ำให้เอง</li>
              <li>มี Product Key 24 หลัก (เช่น ได้รับจากแอดมิน) ให้เติมที่หน้า <Link href="/dashboard">กระเป๋าเวลา</Link></li>
            </ul>
          </Section>

          <Section id="web">
            <p>เว็บใช้บัญชีเดียวกับโปรแกรม ข้อมูลพอร์ตบนเว็บส่งมาจากโปรแกรมทุก 5 วินาที จึงต้องเปิดโปรแกรมไว้</p>
            <ul className="guide-links">
              {WEB_PAGES.map(([href, title, text]) => (
                <li key={href}>
                  <Link href={href}>{title}</Link>
                  <span className="small muted">{text}</span>
                </li>
              ))}
            </ul>
          </Section>

          <Section id="update">
            <Steps
              compact
              items={[
                { body: <>โปรแกรมตรวจเวอร์ชันใหม่อัตโนมัติทุก 6 ชม. ถ้ามีจะขึ้นป้ายบนแถบหัวโปรแกรม หรือตรวจเองได้จากเมนูชื่อผู้ใช้ → <Ui>ตรวจสอบเวอร์ชันใหม่</Ui></> },
                { body: <>กด <Ui tone="gold">ดาวน์โหลดเวอร์ชันใหม่</Ui> แล้วปิดโปรแกรมเดิม</> },
                { body: 'ติดตั้งทับได้เลย การตั้งค่า การจดจำการเข้าสู่ระบบ และประวัติในเครื่องยังอยู่ครบ' },
              ]}
            />
          </Section>

          <Section id="faq">
            <dl className="guide-faq">
              {FAQ.map(([q, a]) => (
                <div key={q}>
                  <dt>{q}</dt>
                  <dd className="muted">{a}</dd>
                </div>
              ))}
            </dl>
          </Section>

          <Section id="contact">
            <div className="guide-contact">
              <span className="small muted">LINE Official Account</span>
              <span className="guide-contact-id mono">{LINE_ID}</span>
              <CopyButton text={LINE_ID} />
              <a className="btn btn-sm guide-line-btn" href={LINE_URL} target="_blank" rel="noopener noreferrer">
                เพิ่มเพื่อนใน LINE <ExternalLink size={14} />
              </a>
            </div>
            <ul>
              <li>ในโปรแกรม: คลิกป้ายชื่อผู้ใช้มุมขวาบน → <Ui>ติดต่อแอดมิน (LINE)</Ui> จะมี QR ให้สแกน</li>
              <li>บนเว็บ: หน้า <Link href="/contact">ติดต่อแอดมิน</Link> มี QR Code ให้สแกน</li>
              <li>แจ้งอีเมลที่ใช้สมัคร พร้อมภาพหน้าจอหรือสลิป จะช่วยให้ตรวจสอบได้เร็วขึ้น</li>
            </ul>
            <Note tone="red" label="ความปลอดภัย">แอดมินไม่ขอรหัสผ่านของเว็บหรือรหัสบัญชี MT5 ทุกกรณี</Note>
          </Section>

          <Section id="risk">
            <ul>
              <li>การเทรดทองคำมีความเสี่ยงสูง และอาจขาดทุนมากกว่าที่คาดไว้</li>
              <li>ผลทดสอบย้อนหลังและความแม่นของ AI เป็นสถิติในอดีต ไม่รับประกันผลในอนาคต</li>
              <li>เริ่มจากบัญชี Demo และ Lot เล็ก และใช้เฉพาะเงินที่ยอมเสียได้</li>
              <li>โปรแกรมเป็นเครื่องมือช่วยเทรด ผู้ใช้เป็นผู้ตัดสินใจและรับผิดชอบผลการเทรดเอง</li>
            </ul>
          </Section>

          <p className="tiny faint">คู่มือฉบับวันที่ 7 ต.ค. 2569 · อ้างอิงโปรแกรมเวอร์ชัน 2026.1007.0830</p>
        </div>
      </div>
    </div>
  );
}
