'use client';

import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { FlaskConical, Info, LineChart, ShieldAlert, Target, TrendingDown, TrendingUp, Users } from 'lucide-react';
import { Alert, EmptyState, PageHeader, PageLoading, StatCard } from '../../components/ui';
import { PLAN_NAMES, planDisplay } from '../../lib/plans';
import { MEMBER_PLAN_NUMBERS } from '../../lib/membership';
import Link from 'next/link';

const PLAN_COLORS = { 1: '#f2c14e', 2: '#60a5fa', 3: '#34d399', 4: '#f472b6', 5: '#a78bfa', 6: '#fb923c', 7: '#c084fc', 8: '#2dd4bf', 9: '#f59e0b', 10: '#f472b6', 11: '#38bdf8', 12: '#a3e635' };

// หลักการของแต่ละแผน (ตรงกับกฎในโปรแกรมเวอร์ชันล่าสุด)
const PLAN_INFO = {
  1: {
    type: 'ตามเทรนด์ · M15',
    rules: [
      'เทรนด์ H1 จากระบบดูเทรนด์ (โครงสร้างราคา · MA200 · EMA20/50/200 · ความชัน · ADX): คะแนน ≥ +3 = ขาขึ้น (BUY) · ≤ −3 = ขาลง (SELL)',
      'จุดเข้า: MA5 ตัด MA13 บนแท่ง M15 ที่ปิดแล้ว ตามทิศเทรนด์ → แท่งถัดไปต้องปิดตามทิศและทั้งตัวพ้น MA13 (แท่งยืนยัน) จึงเข้า',
      'กรองสัญญาณหลอก: RSI 50–70 (BUY) / 30–50 (SELL) และราคาปิดอยู่ฝั่งเดียวกับ MA50 M15',
      'SL 1.0 ATR · เลื่อน SL ทุกกำไร 5 จุด (ขั้นแรก 50% / ถัดไป 40%) · ปิดเมื่อ MA5 ตัด MA13 กลับ (ไม่ตั้ง TP)',
    ],
  },
  2: {
    type: 'ตามเทรนด์ · H1',
    rules: [
      'เทรนด์ H4: MA10/MA30 + ความชัน MA5 + ราคาอยู่ฝั่งเดียวกับ MA200',
      'จุดเข้า: MA5 ตัด MA10 บนแท่ง H1 ที่ปิดแล้ว ตามทิศเทรนด์',
      'SL 1.25 ATR (H1) · ปิดเมื่อ MA5 ตัด MA20 กลับ (ไม่ตั้ง TP · ปล่อยกำไรวิ่ง)',
    ],
  },
  3: {
    type: 'กวาดสภาพคล่อง · M15',
    rules: [
      'ราคาทะลุแนวรับ/ต้าน H1 (โซนกลับตัว 1,000 แท่ง + ยืนยันด้วย H4) แล้วดึงกลับ พร้อมไส้เทียน 0.4–1.0 ATR',
      'ต้องตามเทรนด์ H1 (MA10/30 และ MA100/150/200 เรียงตามทิศ) และ AI ยืนยันทิศ ≥ 50%',
      'SL 1.0 ATR · TP 2.0 ATR · เลื่อน SL ทุกกำไร 5 จุด (50% / 40%) · ล็อกกำไรที่ 70% ของเป้า',
    ],
  },
  4: {
    type: 'เด้งแนวรับ/ต้าน · M15',
    rules: [
      'ราคาเข้าใกล้แนวรับ/ต้าน H1 (1,000 แท่ง + ยืนยันด้วย H4) ไม่เกิน 0.75 ATR + แท่งปฏิเสธราคา',
      'ต้องมี RSI Divergence · H1 MA100/150/200 ไม่เรียงสวนทิศ และ AI ยืนยันทิศ ≥ 58% (ปรับจาก 55% เมื่อ 14 ต.ค. 2026)',
      'SL 1.0 ATR · TP 2.0 ATR · เลื่อน SL ทุกกำไร 5 จุด (50% / 40%) · ล็อกกำไรที่ 70% ของเป้า',
    ],
  },
  5: {
    type: 'กลับตัวขอบ Bollinger · H1',
    rules: [
      'ราคาหลุดขอบ Bollinger Bands H1 (20, 2 SD) แล้วปิดกลับเข้ากรอบ + ไส้เทียน ≥ 0.2 ATR',
      'ต้องมี RSI Divergence และ AI ยืนยันทิศ ≥ 55%',
      'ห้ามเข้าเมื่อ H1 MA100/150/200 เรียงตัวตามทิศไม้ (กลางเทรนด์แรงมักไม่เด้งกลับ) — เหมาะกับตลาดแกว่งในกรอบ',
      'SL 0.75 ATR · TP 1.125 ATR · เลื่อน SL ทุกกำไร 5 จุด (50% / 40%) + ล็อกกำไรที่ 70% ของเป้า',
    ],
  },
  6: {
    type: 'ตามเทรนด์ · Parabolic SAR H1',
    rules: [
      'เทรนด์ H4 จากระบบดูเทรนด์ (5 ข้อ): คะแนน ≥ +3 = ขาขึ้น · ≤ −3 = ขาลง · ไซด์เวย์ไม่เข้า',
      'จุดเข้า: Parabolic SAR (0.01/0.1) บนแท่ง H1 ที่ปิดแล้วสลับข้างมาทางเทรนด์ (ไม่ใช้ AI)',
      'SL เริ่มที่จุด SAR (ไม่เกิน 3 ATR H1) และเลื่อนตาม SAR ทุกชั่วโมง · กำไรถึง 2 ATR เปลี่ยนไปตาม SAR เร็ว (0.02/0.2)',
      'ไม่ตั้ง TP · ปิดเมื่อเทรนด์ H4 เปลี่ยน หรือราคาปิด H1 ผิดฝั่ง EMA100',
    ],
  },
  7: {
    type: 'กลับตัวขอบ Bollinger · H4 (ตามเทรนด์ H4)',
    rules: [
      'ราคาหลุดขอบ Bollinger Bands H4 (20, 2 SD) แล้วแท่ง M15 ปิดกลับเข้ากรอบ + ไส้เทียน ≥ 0.2 ATR',
      'ต้องมี RSI Divergence · AI ยืนยันทิศ ≥ 55% · H1 MA100/150/200 ไม่เรียงตามทิศไม้',
      'ไม่เข้าสวนเทรนด์ H4 MA10/30 (ไซด์เวย์เข้าได้ทั้งสองฝั่ง) — สัญญาณน้อยแต่คัดมาก',
      'SL 0.75 ATR · TP 1.125 ATR · เลื่อน SL ทุกกำไร 5 จุด (50% / 40%) + ล็อกกำไรที่ 70% ของเป้า',
    ],
  },
  8: {
    type: 'กลับตัวขอบ Bollinger · H4 (ไม่กรองเทรนด์ H4)',
    rules: [
      'กฎเดียวกับ P7: หลุดขอบ Bollinger Bands H4 แล้วแท่ง M15 ปิดกลับเข้ากรอบ + ไส้เทียน + Divergence + AI ≥ 55%',
      'H1 MA100/150/200 ไม่เรียงตามทิศไม้',
      'ไม่ใช้ตัวกรองเทรนด์ H4 MA10/30 จึงเข้าได้บ่อยกว่า P7 (สัญญาณของ P7 เป็นส่วนหนึ่งของ P8 — เปิดทั้งคู่อาจเข้า 2 ไม้พร้อมกัน)',
      'SL 0.75 ATR · TP 1.125 ATR · เลื่อน SL ทุกกำไร 5 จุด (50% / 40%) + ล็อกกำไรที่ 70% ของเป้า',
    ],
  },
  9: {
    type: 'Fibonacci ย่อสวนเทรนด์ใหญ่ · H1',
    rules: [
      'คลื่น H1 (swing 3 แท่ง) ยาว ≥ 3 ATR · ระดับ 0 = ต้นคลื่น (คลื่นลง = ราคาสูงสุด) · 1 = ปลายคลื่น',
      'SELL บนคลื่นลงเฉพาะตอน H1 MA100/150/200 เรียงขึ้น · BUY บนคลื่นขึ้นเฉพาะตอน H1 เรียงลง — เข้าเมื่อราคาย้อนถึงระดับ 0.3 (ออเดอร์รอ 48 ชม.)',
      'SL ระดับ 0 · TP 1.75 · เลื่อน SL ขั้นบันได: ราคาปิด H1 ผ่าน 1 → SL 0.15 · ผ่าน 1.27 → SL 0.6 · ผ่าน 1.5 → SL 1',
      'กรองสัญญาณหลอก: ADX H1 > 20 และ MACD H1 ยังไม่หันตามทิศไม้ (ไม่ผ่าน = ข้ามคลื่นนั้น)',
      'ไม่ใช้ AI · ชนะราว 1 ใน 3 แต่กำไรต่อไม้สูง',
    ],
  },
  10: {
    type: 'Oversold / Overbought ตามเทรนด์ · H1',
    rules: [
      'BUY: ราคาปิด H1 เหนือ MA200 และ RSI(14) เพิ่งลงต่ำกว่า 30 (ซื้อตอนย่อในขาขึ้น)',
      'SELL: ราคาปิด H1 ใต้ MA200 และ RSI(14) เพิ่งขึ้นเกิน 70 (ขายตอนเด้งในขาลง)',
      'SL 2 ATR H1 · TP 3 ATR · ถือไม่เกิน 48 ชม. · ไม่เลื่อน SL · ไม่ใช้ AI',
      'ทดสอบแล้ว: Overbought/Oversold แบบสวนเทรนด์ขาดทุนทุกเครื่องมือ (RSI · Stochastic · Williams %R · CCI) — ใช้ได้เฉพาะตามเทรนด์',
    ],
  },
  11: {
    type: 'ข่าว USD · เข้าทันทีเมื่อค่าจริงออก',
    rules: [
      'ก่อนข่าว: ตัวเลขคาดเทียบครั้งก่อนบอกแนวโน้มทอง (สูงขึ้น = ดอลลาร์แข็ง = ทองลง · อัตราว่างงาน / Claims กลับทิศ)',
      'ค่าจริงออกไม่สวนแนวโน้ม = ยืนยัน · ข่าวที่ออกพร้อมกันหักกลบเป็นไม้เดียว Lot = ปกติ × จำนวนสุทธิ (สูงสุด 3 เท่า)',
      'เข้าไม้ทันที (EA ใน MT5 อ่านปฏิทินทุก 0.5 วินาที) · SL 3 ATR M15 · ไม่ตั้ง TP · ถือ 8 ชม.',
      'Backtest ใช้ Tick จริง เข้า 10 วินาทีหลังข่าวออก (ราคา Ask/Bid รวมสเปรดช่วงข่าว) · ตัวเลขคาดจากปฏิทิน MetaQuotes · กำไรส่วนใหญ่ปี 2026',
    ],
  },
  12: {
    type: 'BB ทำยอดซ้ำ ตามเทรนด์ H4 · H1',
    rules: [
      'ทิศจากเทรนด์ H4: MA10 < MA30 = SELL เท่านั้น · MA10 > MA30 = BUY เท่านั้น',
      'SELL: แท่ง H1 ทะลุเส้น BB บน → ราคาย่อ → ขึ้นไปทำ High ใหม่สูงกว่า High แรก → แท่งถัดไปปิดแดง = เข้า (BUY กลับด้าน)',
      'SL เหนือ High ใหม่ 0.1 ATR · ไม่ตั้ง TP ปิดทุกไม้เมื่อราคาแตะเส้น BB อีกฝั่ง',
      'ไม้เพิ่มสูงสุด 2 ไม้: ทำยอดใหม่ที่ไม่สูงกว่ายอดเดิมและอยู่เหนือเส้นกลาง BB แล้วแท่งถัดไปปิดแดง (ใช้ SL เดียวกัน)',
      'ช่วงก่อนปี 2024 ยังไม่ชัด — ค่าเริ่มต้นปิด แนะนำทดลองบนบัญชี Demo ก่อน',
    ],
  },
};
const pts = (v) => (v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${Number(v).toLocaleString('th-TH', { maximumFractionDigits: 1 })}`);
const tone = (v) => (v > 0 ? 'text-green' : v < 0 ? 'text-red' : 'muted');

/** ชื่อแผน + กฎของแผนเป็น tooltip (ชี้เมาส์ / แตะ / โฟกัสด้วยคีย์บอร์ด) · วาดลง body เพื่อไม่ถูกตัดโดยกรอบตารางที่เลื่อนได้ */
function RuleTip({ text, children, icon = true, estH = 160, width = 440 }) {
  const ref = useRef(null);
  const id = useId();
  const [pos, setPos] = useState(null);
  const show = () => {
    const r = ref.current?.getBoundingClientRect();
    if (!r) return;
    const w = Math.min(width, window.innerWidth - 32);
    const left = Math.max(16, Math.min(r.left, window.innerWidth - 16 - w));
    setPos(r.bottom + estH < window.innerHeight || r.top < estH ? { left, width: w, top: r.bottom + 8 } : { left, width: w, bottom: window.innerHeight - r.top + 8 });
  };
  const hide = () => setPos(null);
  useEffect(() => {
    if (!pos) return undefined;
    window.addEventListener('scroll', hide, true);
    window.addEventListener('resize', hide);
    return () => {
      window.removeEventListener('scroll', hide, true);
      window.removeEventListener('resize', hide);
    };
  }, [pos]);
  if (!text) return children;
  return (
    <span
      ref={ref}
      className="rule-tip-anchor"
      tabIndex={0}
      aria-describedby={pos ? id : undefined}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      onClick={show}
    >
      {children}
      {icon && <Info size={13} className="rule-tip-icon" aria-hidden="true" />}
      {pos &&
        createPortal(
          <div id={id} role="tooltip" className="rule-tip" style={pos}>
            {text}
          </div>,
          document.body,
        )}
    </span>
  );
}

/** รายการไม้ของเดือนนั้น (tooltip): ฝั่ง · เวลาเข้า → ปิด (เวลาไทย) · กำไร/ขาดทุน (จุด ที่ Lot 0.01) */
function TradeList({ title, trades }) {
  return (
    <div>
      <div className="rule-tip-title">{title} · {trades.length} ไม้</div>
      {trades.map(([tin, side, pnl, tout, mult], i) => (
        <div key={i} className="rule-tip-row mono">
          <span className={side === 'BUY' ? 'text-green' : 'text-red'}>{side === 'BUY' ? '▲ BUY' : '▼ SELL'}{mult > 1 ? ` ×${mult}` : ''}</span>
          <span>{tin}{tout ? ` → ${tout.slice(0, 10) === tin.slice(0, 10) ? tout.slice(11) : tout}` : ''}</span>
          <span className={pnl > 0 ? 'text-green' : pnl < 0 ? 'text-red' : ''}>{pnl > 0 ? '+' : ''}{pnl.toLocaleString('th-TH', { maximumFractionDigits: 1 })}</span>
        </div>
      ))}
      <div className="tiny faint" style={{ marginTop: 6 }}>เวลาไทย · กำไร/ขาดทุนเป็นจุด (≈ $ ที่ Lot 0.01)</div>
    </div>
  );
}

/** กราฟกำไรสะสม (SVG) — รวมทุกแผน + แยกรายแผน */
function EquityChart({ equity, plans, visible }) {
  const W = 900;
  const H = 260;
  const P = 36;
  const series = useMemo(() => {
    const lines = [{ key: 'total', color: '#eceef3', width: 2.4, values: equity.map((e) => e.total) }];
    for (const p of plans) {
      if (visible[p.key]) lines.push({ key: p.key, color: PLAN_COLORS[p.key], width: 1.4, values: equity.map((e) => e.plans?.[String(p.key)] ?? 0) });
    }
    return lines;
  }, [equity, plans, visible]);
  if (!equity.length) return null;
  const all = series.flatMap((s) => s.values);
  const min = Math.min(0, ...all);
  const max = Math.max(0, ...all);
  const span = max - min || 1;
  const x = (i) => P + (i / Math.max(1, equity.length - 1)) * (W - P * 2);
  const y = (v) => H - P - ((v - min) / span) * (H - P * 2);
  const path = (vals) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const ticks = [min, (min + max) / 2, max];
  const dates = [0, Math.floor(equity.length / 2), equity.length - 1];
  return (
    <div className="table-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', minWidth: 520, height: 'auto' }} role="img" aria-label="กราฟกำไรสะสม">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={P} x2={W - P} y1={y(t)} y2={y(t)} stroke="#262b36" strokeDasharray="4 4" />
            <text x={4} y={y(t) + 4} fill="#6b7385" fontSize="11">
              {Math.round(t)}
            </text>
          </g>
        ))}
        <line x1={P} x2={W - P} y1={y(0)} y2={y(0)} stroke="#3a4150" />
        {series.map((s) => (
          <path key={s.key} d={path(s.values)} fill="none" stroke={s.color} strokeWidth={s.width} strokeLinejoin="round" />
        ))}
        {dates.map((i) => (
          <text key={i} x={x(i)} y={H - 10} fill="#6b7385" fontSize="11" textAnchor={i === 0 ? 'start' : i === equity.length - 1 ? 'end' : 'middle'}>
            {equity[i]?.date}
          </text>
        ))}
      </svg>
    </div>
  );
}

const usd = (v) => (v === null || v === undefined ? '—' : `${v > 0 ? '+' : v < 0 ? '−' : ''}$${Math.abs(Number(v)).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
const ago = (iso) => {
  if (!iso) return '—';
  const m = Math.max(0, (Date.now() - new Date(iso).getTime()) / 60000);
  if (m < 60) return `${Math.round(m)} นาทีที่แล้ว`;
  if (m < 1440) return `${Math.round(m / 60)} ชม.ที่แล้ว`;
  return `${Math.round(m / 1440)} วันที่แล้ว`;
};

/** ผลเทรดจริงของผู้ใช้ทุกคนรวมกัน (จาก /api/plan-stats · ไม่ระบุตัวตน) */
function LiveResults() {
  const [live, setLive] = useState(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    fetch('/api/plan-stats')
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => (d.success ? setLive(d) : setFailed(true)))
      .catch(() => setFailed(true));
  }, []);
  if (failed) return null;
  if (!live) return <div className="card section card-pad muted small">กำลังโหลดผลเทรดจริงของผู้ใช้…</div>;
  const t = live.total;
  return (
    <>
      <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '8px 0 12px' }}>ผลเทรดจริงของผู้ใช้ทุกคน</h2>
      <div className="grid grid-4">
        <StatCard icon={Users} label="ผู้ใช้ที่มีไม้ปิดแล้ว" value={live.users.toLocaleString()} tone="sky" sub="นับเฉพาะบัญชีที่โปรแกรมซิงค์สถิติขึ้นมา" />
        <StatCard icon={Target} label="ไม้ที่ปิดแล้ว / ชนะ" value={t.trades.toLocaleString()} tone="gold" sub={`อัตราชนะ ${t.winRate ?? '—'}%`} />
        <StatCard icon={LineChart} label="Profit Factor" value={t.pf ?? '—'} tone="sky" sub="กำไรรวม ÷ ขาดทุนรวม ของทุกบัญชี" />
        <StatCard icon={TrendingUp} label="กำไรสุทธิรวม" value={usd(t.net)} tone={t.net >= 0 ? 'green' : 'red'} sub="รวมทุก Lot ทุกบัญชี" />
      </div>
      <div className="card section">
        <div className="card-header">
          <h3>
            <Users size={17} className="text-gold" /> ผลจริงแยกตามแผน
          </h3>
          <span className="tiny faint">อัปเดตทุก 5 นาที</span>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>แผน</th>
                <th className="num">ผู้ใช้</th>
                <th className="num">ไม้</th>
                <th className="num">ชนะ / แพ้</th>
                <th className="num">อัตราชนะ</th>
                <th className="num">PF</th>
                <th className="num">กำไรสุทธิ</th>
                <th className="num">เฉลี่ย/ไม้</th>
                <th className="num">ไม้ล่าสุด</th>
              </tr>
            </thead>
            <tbody>
              {live.plans.length === 0 && (
                <tr>
                  <td colSpan={9} className="muted">ยังไม่มีไม้ที่ปิดแล้ว</td>
                </tr>
              )}
              {live.plans.map((p) => (
                <tr key={p.key}>
                  <td className="nowrap">
                    <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 3, marginRight: 8, background: PLAN_COLORS[p.key] || '#6b7385' }} />
                    {PLAN_NAMES[p.key]}
                  </td>
                  <td className="num">{p.users}</td>
                  <td className="num">{p.trades.toLocaleString()}</td>
                  <td className="num">
                    <span className="text-green">{p.win}</span> / <span className="text-red">{p.loss}</span>
                  </td>
                  <td className="num">{p.winRate ?? '—'}%</td>
                  <td className="num">{p.pf ?? '—'}</td>
                  <td className={`num ${tone(p.net)}`}>{usd(p.net)}</td>
                  <td className={`num ${tone(p.avg)}`}>{usd(p.avg)}</td>
                  <td className="num muted nowrap">{ago(p.lastTradeAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card-body">
          <p className="tiny faint" style={{ margin: 0 }}>
            ข้อมูลจริงจากโปรแกรม Gold Bot 24 ของผู้ใช้ทุกคนรวมกัน แสดงเฉพาะยอดรวม ไม่ระบุตัวตน · ผู้ใช้แต่ละคนใช้ Lot และโบรกเกอร์ต่างกัน กำไรเป็นเงินจึงเปรียบเทียบข้ามแผนได้ไม่ตรงนัก ให้ดูอัตราชนะและ PF ประกอบ · ผลในอดีตไม่รับประกันผลในอนาคต
          </p>
        </div>
      </div>
    </>
  );
}

export default function BacktestPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [visible, setVisible] = useState({ 1: true, 2: true, 3: false, 4: false, 5: false, 6: true });

  useEffect(() => {
    fetch('/backtest.json', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('ยังไม่มีผล Backtest'))))
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  const months = useMemo(() => {
    if (!data) return [];
    const set = new Set();
    data.plans.forEach((p) => Object.keys(p.monthly || {}).forEach((m) => set.add(m)));
    return [...set].sort().slice(-12);
  }, [data]);

  if (error) {
    return (
      <div className="container page">
        <div className="card">
          <EmptyState icon={FlaskConical} title="ยังไม่มีผล Backtest">
            {error}
          </EmptyState>
        </div>
      </div>
    );
  }
  if (!data) return <PageLoading />;
  const s = data.summary;
  const sum = (key) => data.plans.reduce((a, p) => a + (Number(p[key]) || 0), 0);
  const monthTotal = (m) => data.plans.reduce((a, p) => a + (Number(p.monthly?.[m]) || 0), 0);
  const planYear = (p) => months.reduce((a, m) => a + (Number(p.monthly?.[m]) || 0), 0);
  const grandYear = months.reduce((a, m) => a + monthTotal(m), 0);
  // จำนวนไม้ / % ชนะ ใต้ตัวเลขกำไร (ไฟล์ Backtest รุ่นเก่าไม่มีข้อมูลนี้ → ไม่แสดง)
  const nw = (n, w) => (n ? `${n.toLocaleString()} ไม้ · ชนะ ${Math.round((w / n) * 100)}%` : null);
  const mN = (p, m) => Number(p.monthly_n?.[m]) || 0;
  const mW = (p, m) => Number(p.monthly_w?.[m]) || 0;
  const planYearNW = (p) => months.reduce((a, m) => [a[0] + mN(p, m), a[1] + mW(p, m)], [0, 0]);
  const monthNW = (m) => data.plans.reduce((a, p) => [a[0] + mN(p, m), a[1] + mW(p, m)], [0, 0]);
  const grandNW = months.reduce((a, m) => { const x = monthNW(m); return [a[0] + x[0], a[1] + x[1]]; }, [0, 0]);
  const halfW = (k) => data.plans.reduce((a, p) => a + (Number(p[`${k}_n`]) || 0) * (Number(p[`${k}_win`]) || 0) / 100, 0);
  const Sub = ({ children }) => (children ? <div className="tiny faint" style={{ whiteSpace: 'nowrap', fontWeight: 400 }}>{children}</div> : null);

  return (
    <div className="container container-wide page">
      <PageHeader
        eyebrow="Trading Plans"
        icon={FlaskConical}
        title="แผนเทรดทองคำ (XAUUSD)"
        description={`หลักการเข้า-ออกของบอททั้ง ${data.plans.length} แผน พร้อมผลทดสอบย้อนหลัง ${data.period[0]} ถึง ${data.period[1]} (กฎเวอร์ชัน v${data.app_version})`}
      />

      <div className="grid grid-3" style={{ marginBottom: 24 }}>
        {data.plans.map((p) => {
          const info = PLAN_INFO[p.key] || { type: '', rules: [p.rule] };
          return (
            <div key={p.key} className="card card-pad" style={{ borderTop: `3px solid ${PLAN_COLORS[p.key]}` }}>
              <div className="row-between" style={{ marginBottom: 8, gap: 8 }}>
                <strong>
                  {planDisplay(p.name)}
                  {MEMBER_PLAN_NUMBERS.includes(Number(p.key)) && (
                    <Link href="/store?member=1" className="badge badge-gold" style={{ marginLeft: 8 }} title="ใช้ได้เฉพาะสมาชิกรายเดือน">
                      สมาชิก
                    </Link>
                  )}
                </strong>
                <span className="badge badge-muted">{info.type}</span>
              </div>
              <ul className="small muted" style={{ margin: '0 0 12px 18px', padding: 0 }}>
                {info.rules.map((r) => (
                  <li key={r} style={{ marginBottom: 4 }}>
                    {r}
                  </li>
                ))}
              </ul>
              <div className="row wrap small" style={{ gap: 12 }}>
                <span>
                  ย้อนหลัง <strong className={tone(p.net)}>{pts(p.net)} จุด</strong>
                </span>
                <span className="muted">PF {p.pf ?? '—'}</span>
                <span className="muted">ชนะ {p.n ? `${p.win}%` : '—'}</span>
                <span className="muted">{p.n ?? 0} ไม้</span>
              </div>
            </div>
          );
        })}
      </div>

      <LiveResults />

      <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '24px 0 12px' }}>ผลทดสอบย้อนหลังรวมทุกแผน</h2>

      <div className="grid grid-4">
        <StatCard icon={TrendingUp} label="กำไรสุทธิรวม (0.01 lot)" value={`${pts(s.net)} จุด`} tone={s.net >= 0 ? 'green' : 'red'} sub={`≈ $${Math.round(s.net).toLocaleString()}`} />
        <StatCard icon={Target} label="จำนวนไม้ / ชนะ" value={s.trades.toLocaleString()} tone="gold" sub={`อัตราชนะ ${s.win}%`} />
        <StatCard icon={LineChart} label="Profit Factor" value={s.pf ?? '—'} tone="sky" sub="กำไรรวม ÷ ขาดทุนรวม" />
        <StatCard icon={TrendingDown} label="Max Drawdown" value={`${pts(-s.maxdd)} จุด`} tone="red" sub="ช่วงที่พอร์ตลดลงหนักสุด" />
      </div>

      <div className="card section">
        <div className="card-header">
          <h3>
            <LineChart size={17} className="text-gold" /> กำไรสะสม (จุด)
          </h3>
          <div className="row wrap" style={{ gap: 6 }}>
            {data.plans.map((p) => (
              <button
                key={p.key}
                type="button"
                className={`btn btn-sm ${visible[p.key] ? 'btn-secondary' : 'btn-ghost'}`}
                onClick={() => setVisible((v) => ({ ...v, [p.key]: !v[p.key] }))}
                style={{ borderColor: visible[p.key] ? PLAN_COLORS[p.key] : undefined }}
              >
                <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 3, background: PLAN_COLORS[p.key] }} /> {planDisplay(p.name)}
              </button>
            ))}
          </div>
        </div>
        <div className="card-body">
          <EquityChart equity={data.equity} plans={data.plans} visible={visible} />
          <p className="tiny faint" style={{ marginTop: 6 }}>เส้นขาว = รวมทุกแผน · กดปุ่มด้านบนเพื่อแสดง/ซ่อนเส้นของแต่ละแผน</p>
        </div>
      </div>

      <div className="card section">
        <div className="card-header">
          <h3>ผลแยกตามแผน</h3>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>แผน</th>
                <th className="num">ไม้</th>
                <th className="num">ชนะ</th>
                <th className="num">กำไรสุทธิ</th>
                <th className="num">PF</th>
                <th className="num">Max DD</th>
                <th className="num">ครึ่งแรก</th>
                <th className="num">ครึ่งหลัง</th>
                <th className="num">100 ไม้ล่าสุด</th>
              </tr>
            </thead>
            <tbody>
              {data.plans.map((p) => (
                <tr key={p.key}>
                  <td>
                    <div className="row" style={{ gap: 8 }}>
                      <span style={{ width: 10, height: 10, borderRadius: 3, background: PLAN_COLORS[p.key], flexShrink: 0 }} />
                      <RuleTip text={p.rule}>
                        <strong style={{ whiteSpace: 'nowrap' }}>{planDisplay(p.name)}</strong>
                      </RuleTip>
                    </div>
                  </td>
                  <td className="num">{p.n ?? 0}</td>
                  <td className="num">{p.n ? `${p.win}%` : '—'}</td>
                  <td className={`num ${tone(p.net)}`}>
                    <strong>{pts(p.net)}</strong>
                  </td>
                  <td className="num">{p.pf ?? '—'}</td>
                  <td className="num text-red">{p.maxdd ? pts(-p.maxdd) : '—'}</td>
                  <td className={`num ${tone(p.half1)}`}>
                    {pts(p.half1)}
                    <Sub>{p.half1_n ? `${p.half1_n} ไม้ · ชนะ ${p.half1_win}%` : null}</Sub>
                  </td>
                  <td className={`num ${tone(p.half2)}`}>
                    {pts(p.half2)}
                    <Sub>{p.half2_n ? `${p.half2_n} ไม้ · ชนะ ${p.half2_win}%` : null}</Sub>
                  </td>
                  <td className={`num ${tone(p.last100_net)}`}>
                    {pts(p.last100_net)}
                    {p.last100_win !== undefined && p.n ? <Sub>{p.last100_n ? `${p.last100_n} ไม้ · ` : ''}ชนะ {p.last100_win}%</Sub> : null}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="table-total">
                <td>
                  <strong>รวมทุกแผน</strong>
                  <div className="tiny faint">ชนะ · PF · Max DD คิดจากทุกไม้รวมกัน (เข้าไม้พร้อมกันได้)</div>
                </td>
                <td className="num">{sum('n').toLocaleString()}</td>
                <td className="num">{s.win}%</td>
                <td className={`num ${tone(s.net)}`}>
                  <strong>{pts(s.net)}</strong>
                </td>
                <td className="num">{s.pf ?? '—'}</td>
                <td className="num text-red">{s.maxdd ? pts(-s.maxdd) : '—'}</td>
                <td className={`num ${tone(sum('half1'))}`}>
                  {pts(Math.round(sum('half1') * 10) / 10)}
                  <Sub>{nw(sum('half1_n'), halfW('half1'))}</Sub>
                </td>
                <td className={`num ${tone(sum('half2'))}`}>
                  {pts(Math.round(sum('half2') * 10) / 10)}
                  <Sub>{nw(sum('half2_n'), halfW('half2'))}</Sub>
                </td>
                <td className={`num ${tone(sum('last100_net'))}`}>{pts(Math.round(sum('last100_net') * 10) / 10)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <div className="card section">
        <div className="card-header">
          <h3>กำไรรายเดือน (12 เดือนล่าสุด · จุด)</h3>
          <span className="tiny faint">ใต้ตัวเลข = จำนวนไม้ · % ชนะ</span>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>แผน</th>
                {months.map((m) => (
                  <th key={m} className="num">
                    {m.slice(2)}
                  </th>
                ))}
                <th className="num">รวม</th>
              </tr>
            </thead>
            <tbody>
              {data.plans.map((p) => (
                <tr key={p.key}>
                  <td>{planDisplay(p.name)}</td>
                  {months.map((m) => {
                    const v = p.monthly?.[m];
                    const tl = p.trades_m?.[m];
                    const cell = (
                      <>
                        {v === undefined ? '·' : pts(v)}
                        <Sub>{mN(p, m) ? `${mN(p, m)} · ${Math.round((mW(p, m) / mN(p, m)) * 100)}%` : null}</Sub>
                      </>
                    );
                    return (
                      <td key={m} className={`num tiny ${tone(v || 0)}`}>
                        {tl?.length ? (
                          <RuleTip icon={false} width={480} estH={tl.length * 22 + 70} text={<TradeList title={`${planDisplay(p.name)} · ${m}`} trades={tl} />}>
                            <span style={{ display: 'block' }}>{cell}</span>
                          </RuleTip>
                        ) : (
                          cell
                        )}
                      </td>
                    );
                  })}
                  <td className={`num small ${tone(planYear(p))}`}>
                    <strong>{pts(Math.round(planYear(p) * 10) / 10)}</strong>
                    <Sub>{nw(...planYearNW(p))}</Sub>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="table-total">
                <td>
                  <strong>รวมทุกแผน</strong>
                </td>
                {months.map((m) => (
                  <td key={m} className={`num tiny ${tone(monthTotal(m))}`}>
                    <strong>{pts(Math.round(monthTotal(m) * 10) / 10)}</strong>
                    <Sub>{monthNW(m)[0] ? `${monthNW(m)[0]} · ${Math.round((monthNW(m)[1] / monthNW(m)[0]) * 100)}%` : null}</Sub>
                  </td>
                ))}
                <td className={`num small ${tone(grandYear)}`}>
                  <strong>{pts(Math.round(grandYear * 10) / 10)}</strong>
                  <Sub>{nw(...grandNW)}</Sub>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <div className="section">
        <Alert type="gold">
          <strong>
            <ShieldAlert size={14} style={{ verticalAlign: '-2px' }} /> เงื่อนไขการทดสอบ
          </strong>
          <ul style={{ margin: '6px 0 0 18px', padding: 0 }}>
            {data.assumptions.map((a) => (
              <li key={a} className="small">
                {a}
              </li>
            ))}
          </ul>
        </Alert>
      </div>
    </div>
  );
}
