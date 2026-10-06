'use client';

import { useState } from 'react';
import { BarChart3, BrainCircuit, CandlestickChart, Newspaper } from 'lucide-react';
import { formatThaiDateTime } from '../lib/format';

// ข้อมูลทั้งหมดในไฟล์นี้มาจากโปรแกรม Desktop (Telemetry) — ชุดเดียวกับที่โปรแกรมแสดง

const GREEN = 'var(--green)';
const RED = 'var(--red)';
const GOLD = 'var(--gold)';
const MUTED = 'var(--text-muted, #a3abba)';
const TH_MONTHS = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];

const money = (v) => (Math.abs(v) < 0.005 ? '$0' : `${v > 0 ? '+' : '-'}$${Math.abs(v).toFixed(2)}`);
const thDate = (iso) => {
  const d = new Date(`${iso}T00:00:00`);
  return `${d.getDate()} ${TH_MONTHS[d.getMonth()]}`;
};
const thTime = (iso) =>
  new Date(iso).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', weekday: 'short', hour: '2-digit', minute: '2-digit' });

function Waiting({ text = 'รอข้อมูลจากโปรแกรม Desktop' }) {
  return <p className="small muted" style={{ padding: '24px 0', textAlign: 'center' }}>{text}</p>;
}

/* ---------------------------------------------------------------- AI คาดการณ์ */
export function OutlookCard({ outlook }) {
  const o = outlook;
  const main = o?.horizons?.[o.horizons.length - 1];
  const tone = main?.direction > 0 ? GREEN : main?.direction < 0 ? RED : GOLD;
  return (
    <div className="card">
      <div className="card-header">
        <h3>
          <BrainCircuit size={17} className="text-gold" /> AI คาดการณ์ทิศทางทอง
        </h3>
        {o?.updated_at && <span className="tiny faint">อัปเดต {formatThaiDateTime(o.updated_at)}</span>}
      </div>
      <div className="card-body">
        {!o ? (
          <Waiting text="รอข้อมูลจากโปรแกรม Desktop (เปิดแท็บ AI คาดการณ์ในโปรแกรม)" />
        ) : (
          <>
            <div style={{ fontWeight: 700, color: tone, marginBottom: 12 }}>{o.summary}</div>
            <div className="grid grid-3" style={{ gap: 10 }}>
              {o.horizons.map((h) => {
                const c = h.direction > 0 ? GREEN : h.direction < 0 ? RED : GOLD;
                const up = Math.round(h.p_up * 100);
                return (
                  <div key={h.key} className="card" style={{ padding: 12, background: 'var(--bg-elevated)', borderColor: h.direction ? c : undefined }}>
                    <div className="tiny faint">อีก {h.label}</div>
                    <div style={{ fontWeight: 700, fontSize: '1.15rem', color: c }}>
                      {h.direction > 0 ? '▲ ขึ้น' : h.direction < 0 ? '▼ ลง' : `ไม่ชัด (เอียง${h.lean > 0 ? 'ขึ้น' : 'ลง'})`}
                    </div>
                    <div className="tiny">
                      ขึ้น {up}% · ลง {100 - up}%
                    </div>
                    <div className="mini-bar" style={{ marginTop: 6, height: 6 }}>
                      <span style={{ width: `${up}%`, background: GREEN }} />
                      <span style={{ width: `${100 - up}%`, background: RED }} />
                    </div>
                    <div className="tiny faint" style={{ marginTop: 6 }}>
                      แม่นในอดีต {Math.round(h.hist_acc)}%{h.trend_agree && h.direction ? ' · เทรนด์ยืนยัน' : ''}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="stack" style={{ gap: 6, marginTop: 14 }}>
              {o.factors.map((f) => (
                <div key={f.name} className="row small" style={{ gap: 8, alignItems: 'baseline' }}>
                  <span style={{ color: f.dir > 0 ? GREEN : f.dir < 0 ? RED : MUTED, width: 14 }}>{f.dir > 0 ? '▲' : f.dir < 0 ? '▼' : '•'}</span>
                  <span style={{ minWidth: 0, flex: '0 0 auto' }}>{f.name}</span>
                  <span className="tiny muted">{f.detail}</span>
                </div>
              ))}
            </div>
            {o.news?.length > 0 && (
              <div className="tiny" style={{ marginTop: 10, color: GOLD }}>
                ข่าว USD ผลกระทบสูงใน 24 ชม.: {o.news.map((n) => `${n.time} ${n.title}`).join(' · ')}
              </div>
            )}
            <div className="tiny faint" style={{ marginTop: 10 }}>{o.note}</div>
          </>
        )}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- แท่งเทียน M15 */
export function CandleCard({ candles, price }) {
  const [hover, setHover] = useState(null);
  const cs = candles || [];
  const W = 640;
  const H = 240;
  const L = 8;
  const R = 62;
  const T = 10;
  const B = 22;
  let body = <Waiting />;
  if (cs.length) {
    const vals = cs.flatMap((c) => [c.high, c.low, c.ma5, c.ma13]).filter((v) => typeof v === 'number');
    let hi = Math.max(...vals);
    let lo = Math.min(...vals);
    const pad = Math.max((hi - lo) * 0.08, 0.5);
    hi += pad;
    lo -= pad;
    const y = (v) => T + ((hi - v) / (hi - lo)) * (H - T - B);
    const slot = (W - L - R) / cs.length;
    const bw = Math.max(3, Math.min(22, slot * 0.62));
    const x = (i) => L + slot * (i + 0.5);
    const line = (k) =>
      cs
        .map((c, i) => (typeof c[k] === 'number' ? `${x(i).toFixed(1)},${y(c[k]).toFixed(1)}` : null))
        .filter(Boolean)
        .join(' ');
    const last = cs[cs.length - 1].close;
    const ticks = Array.from({ length: 5 }, (_, k) => lo + ((hi - lo) * k) / 4);
    body = (
      <>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }} onMouseLeave={() => setHover(null)}>
          {ticks.map((v) => (
            <g key={v}>
              <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="#1e232c" />
              <text x={W - R + 6} y={y(v) + 3} fontSize="10" fill="#8a93a3">
                {v.toFixed(2)}
              </text>
            </g>
          ))}
          <polyline points={line('ma5')} fill="none" stroke="#60a5fa" strokeWidth="2" />
          <polyline points={line('ma13')} fill="none" stroke="#e0a92b" strokeWidth="2" />
          {cs.map((c, i) => {
            const up = c.close >= c.open;
            const col = up ? '#34d399' : '#f87171';
            const y1 = y(Math.max(c.open, c.close));
            const y2 = Math.max(y(Math.min(c.open, c.close)), y1 + 1);
            const live = i === cs.length - 1;
            return (
              <g key={c.time} onMouseEnter={() => setHover(c)}>
                <rect x={x(i) - slot / 2} y={T} width={slot} height={H - T - B} fill="transparent" />
                <line x1={x(i)} x2={x(i)} y1={y(c.high)} y2={y(c.low)} stroke={col} />
                <rect x={x(i) - bw / 2} y={y1} width={bw} height={y2 - y1} fill={col} stroke={live ? '#f2c14e' : col} strokeWidth={live ? 2 : 1} />
                {(i % 3 === 0 || live) && (
                  <text x={x(i)} y={H - 6} fontSize="10" textAnchor="middle" fill={live ? '#f2c14e' : '#8a93a3'}>
                    {live ? 'ตอนนี้' : c.label}
                  </text>
                )}
              </g>
            );
          })}
          <line x1={L} x2={W - R} y1={y(last)} y2={y(last)} stroke="#8a93a3" strokeDasharray="3 3" />
          <rect x={W - R + 2} y={y(last) - 8} width={R - 4} height={16} rx="3" fill="#f2c14e" />
          <text x={W - R + 6} y={y(last) + 4} fontSize="10" fontWeight="700" fill="#111">
            {last.toFixed(2)}
          </text>
        </svg>
        <div className="tiny muted" style={{ minHeight: 18, marginTop: 4 }}>
          {hover
            ? `${hover.label} น. · O ${hover.open.toFixed(2)} H ${hover.high.toFixed(2)} L ${hover.low.toFixed(2)} C ${hover.close.toFixed(2)} (${(hover.close - hover.open >= 0 ? '+' : '') + (hover.close - hover.open).toFixed(2)})`
            : 'เส้นฟ้า MA5 · เส้นทอง MA13 · ชี้ที่แท่งเพื่อดูราคา'}
        </div>
      </>
    );
  }
  return (
    <div className="card">
      <div className="card-header">
        <h3>
          <CandlestickChart size={17} className="text-gold" /> XAUUSD · M15
        </h3>
        {price ? <span className="mono text-gold">{Number(price).toFixed(2)}</span> : null}
      </div>
      <div className="card-body">{body}</div>
    </div>
  );
}

/* ---------------------------------------------------------------- กำไร/ขาดทุนรายวัน */
export function DailyPnlCard({ rows }) {
  const [hover, setHover] = useState(null);
  const data = rows || [];
  const W = 640;
  const H = 220;
  const L = 52;
  const R = 8;
  const T = 18;
  const B = 22;
  const total = data.reduce((t, r) => t + r.profit, 0);
  let body = <Waiting />;
  if (data.length) {
    let vmax = Math.max(0, ...data.map((r) => r.profit));
    let vmin = Math.min(0, ...data.map((r) => r.profit));
    if (vmax - vmin < 1e-9) {
      vmax = 1;
      vmin = -1;
    }
    const pad = (vmax - vmin) * 0.12;
    if (vmax > 0) vmax += pad;
    if (vmin < 0) vmin -= pad;
    const y = (v) => T + ((vmax - v) / (vmax - vmin)) * (H - T - B);
    const slot = (W - L - R) / data.length;
    const bw = Math.max(4, Math.min(30, slot * 0.66));
    const raw = (vmax - vmin) / 5;
    const mag = 10 ** Math.floor(Math.log10(raw));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw);
    const ticks = [];
    for (let v = Math.ceil(vmin / step) * step; v <= vmax + 1e-9; v += step) ticks.push(v);
    body = (
      <>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block' }} onMouseLeave={() => setHover(null)}>
          {ticks.map((v) => (
            <g key={v}>
              <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={Math.abs(v) < 1e-9 ? '#4b5263' : '#20252f'} />
              <text x={L - 6} y={y(v) + 3} fontSize="10" textAnchor="end" fill="#8a93a3">
                {money(v).replace('.00', '')}
              </text>
            </g>
          ))}
          {data.map((r, i) => {
            const cx = L + slot * (i + 0.5);
            const v = r.profit;
            const col = v > 0 ? '#34d399' : '#f87171';
            return (
              <g key={r.date} onMouseEnter={() => setHover(r)}>
                <rect x={cx - slot / 2} y={T} width={slot} height={H - T - B} fill="transparent" />
                {Math.abs(v) < 0.005 ? (
                  <line x1={cx - bw / 2} x2={cx + bw / 2} y1={y(0)} y2={y(0)} stroke="#3a4050" strokeWidth="2" />
                ) : (
                  <>
                    <rect x={cx - bw / 2} y={Math.min(y(v), y(0))} width={bw} height={Math.abs(y(v) - y(0))} fill={col} rx="2" />
                    {slot >= 34 && (
                      <text x={cx} y={v > 0 ? y(v) - 5 : y(v) + 12} fontSize="9" fontWeight="700" textAnchor="middle" fill={col}>
                        {money(v)}
                      </text>
                    )}
                  </>
                )}
                {i % Math.max(1, Math.round(data.length / 7)) === 0 && (
                  <text x={cx} y={H - 6} fontSize="10" textAnchor="middle" fill="#8a93a3">
                    {thDate(r.date)}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
        <div className="tiny muted" style={{ minHeight: 18, marginTop: 4 }}>
          {hover
            ? `${thDate(hover.date)} · ${hover.profit > 0.005 ? 'กำไร' : hover.profit < -0.005 ? 'ขาดทุน' : 'ไม่มีกำไร/ขาดทุน'} ${money(hover.profit)} · ปิดไม้ ${hover.closed} ไม้`
            : 'ทั้งบัญชี MT5 รวม commission/swap · เวลาไทย · ชี้ที่แท่งเพื่อดูรายละเอียด'}
        </div>
      </>
    );
  }
  return (
    <div className="card">
      <div className="card-header">
        <h3>
          <BarChart3 size={17} className="text-gold" /> กำไร / ขาดทุนรายวัน (14 วัน)
        </h3>
        {data.length > 0 && <span className={`badge ${total >= 0 ? 'badge-green' : 'badge-red'}`}>รวม {money(total)}</span>}
      </div>
      <div className="card-body">{body}</div>
    </div>
  );
}

/* ---------------------------------------------------------------- ข่าว + ผลต่อทอง */
export function newsImpactText(n) {
  if (n.actual !== null && n.actual !== undefined)
    return { text: `ผลจริง ${n.actual > 0 ? '▲' : '▼'} ${n.actual > 0 ? '+' : ''}${n.actual.toFixed(2)}%`, color: n.actual > 0 ? GREEN : RED };
  const size = n.move ? `±${n.move.toFixed(2)}%` : '';
  if (n.lean > 0) return { text: `▲ ทองขึ้น ${size}`.trim(), color: GREEN };
  if (n.lean < 0) return { text: `▼ ทองลง ${size}`.trim(), color: RED };
  return { text: size ? `ขยับ ${size}` : '—', color: MUTED };
}

export function newsImpactDetail(n) {
  const parts = [n.rule];
  if (n.lean)
    parts.push(
      `ตลาดคาด ${n.forecast} เทียบครั้งก่อน ${n.previous} → ${n.lean > 0 ? 'ดอลลาร์มีแนวโน้มอ่อนลง ทองมักขึ้น' : 'ดอลลาร์มีแนวโน้มแข็งขึ้น ทองมักลง'} (ถ้าออกตามคาด)`
    );
  if (n.move)
    parts.push(
      `ทองมักขยับ ±${n.move.toFixed(2)}% (แรง ±${(n.move_big || 0).toFixed(2)}%) ใน 1 ชม. — ${
        n.move_src === 'title' ? `จากข่าวนี้ ${n.move_n} ครั้งที่ผ่านมา` : `สถิติทอง 2 ปี ช่วงวัน/เวลาเดียวกัน`
      }`
    );
  if (n.actual !== null && n.actual !== undefined) parts.push(`ผลจริง: ทองขยับ ${n.actual > 0 ? '+' : ''}${n.actual.toFixed(2)}% ใน 60 นาทีหลังข่าว`);
  return parts;
}

export function NewsImpactCard({ news }) {
  const [open, setOpen] = useState(null);
  const items = news || [];
  return (
    <div className="card">
      <div className="card-header">
        <h3>
          <Newspaper size={17} className="text-gold" /> ข่าว USD สัปดาห์นี้ · ผลต่อทอง
        </h3>
      </div>
      <div className="card-body stack" style={{ gap: 8 }}>
        {items.length === 0 ? (
          <Waiting text="รอข้อมูลจากโปรแกรม Desktop (เปิดแท็บปฏิทินเศรษฐกิจในโปรแกรม)" />
        ) : (
          items.map((n) => {
            const t = newsImpactText(n);
            const key = `${n.title}-${n.time}`;
            const past = new Date(n.time) < new Date();
            return (
              <div key={key} style={{ borderBottom: '1px solid var(--border)', paddingBottom: 8 }}>
                <button
                  type="button"
                  onClick={() => setOpen(open === key ? null : key)}
                  className="row-between small"
                  style={{ width: '100%', background: 'none', border: 0, color: 'inherit', cursor: 'pointer', padding: 0, textAlign: 'left', gap: 8 }}
                >
                  <span style={{ opacity: past ? 0.65 : 1 }}>
                    <span className="mono tiny faint">{thTime(n.time)}</span>{' '}
                    <span className={`badge ${n.impact === 'High' ? 'badge-red' : 'badge-gold'}`} style={{ fontSize: '0.65rem' }}>
                      {n.impact === 'High' ? 'สูง' : 'กลาง'}
                    </span>{' '}
                    {n.title}
                  </span>
                  <strong className="tiny" style={{ color: t.color, whiteSpace: 'nowrap' }}>
                    {t.text} ›
                  </strong>
                </button>
                {open === key && (
                  <div className="tiny muted stack" style={{ gap: 4, marginTop: 6 }}>
                    {newsImpactDetail(n).map((p) => (
                      <div key={p}>• {p}</div>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
        {items.length > 0 && <div className="tiny faint">ประเมินจากกฎเศรษฐกิจและสถิติราคาทองจริง ไม่ใช่การรับประกันทิศทางราคา</div>}
      </div>
    </div>
  );
}
