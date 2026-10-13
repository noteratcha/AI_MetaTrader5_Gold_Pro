'use client';

// การ์ดชุดเดียวกับโปรแกรม Gold Bot 24 (ข้อมูลจาก Telemetry radar_signals[0] — เว็บไม่คำนวณซ้ำ)
// สภาวะตลาด H1/H4 · เงื่อนไขเข้าไม้รายแผน P1–P10 · AI วิเคราะห์ไม้ที่ถืออยู่
import { useState } from 'react';
import { Activity, Brain, ListChecks } from 'lucide-react';
import { EmptyState } from './ui';
import { planDisplay } from '../lib/plans';

const fmt = (v) => (v === null || v === undefined ? '—' : Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
const TREND = {
  1: { text: '▲ Uptrend', color: 'var(--green, #34d399)', order: '50 > 100 > 150' },
  [-1]: { text: '▼ Downtrend', color: 'var(--red, #f87171)', order: '50 < 100 < 150' },
  0: { text: '◆ Sideway', color: 'var(--sky, #60a5fa)', order: 'สลับกัน' },
};

function Waiting({ text }) {
  return <EmptyState icon={Activity} title="รอข้อมูลจากโปรแกรม">{text}</EmptyState>;
}

/** สภาวะตลาด H1/H4: ลำดับ MA50/100/150 (แท่งปิด) + ระยะห่าง % + MA200 */
export function MarketCard({ market }) {
  return (
    <div className="card">
      <div className="card-header">
        <h3>
          <Activity size={17} className="text-gold" /> สภาวะตลาด
        </h3>
        <span className="tiny faint">MA50 / 100 / 150 จากแท่งที่ปิดแล้ว</span>
      </div>
      {!market || (!market.H1 && !market.H4) ? (
        <Waiting text="อัปเดตโปรแกรมเป็นเวอร์ชันล่าสุดเพื่อแสดงสภาวะตลาด" />
      ) : (
        <div className="card-body stack" style={{ gap: 12 }}>
          {['H1', 'H4'].map((tf) => {
            const m = market[tf];
            if (!m) return null;
            const t = TREND[m.dir] || TREND[0];
            return (
              <div key={tf} style={{ padding: '10px 12px', borderRadius: 10, background: 'var(--surface-2, #171b23)' }}>
                <div className="row-between" style={{ gap: 8 }}>
                  <span className="row" style={{ gap: 10 }}>
                    <span className="badge badge-muted mono">{tf}</span>
                    <strong style={{ color: t.color }}>{t.text}</strong>
                  </span>
                  <span className="mono small" style={{ color: t.color }}>
                    {t.order} · {m.pct > 0 ? '+' : ''}
                    {m.pct.toFixed(2)}%
                  </span>
                </div>
                <div className="row wrap tiny muted mono" style={{ gap: 14, marginTop: 6 }}>
                  <span>ปิด {fmt(m.close)}</span>
                  <span>MA50 {fmt(m.ma50)}</span>
                  <span>MA100 {fmt(m.ma100)}</span>
                  <span>MA150 {fmt(m.ma150)}</span>
                  <span>MA200 {fmt(m.ma200)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/** เงื่อนไขเข้าไม้รายแผน (เรียลไทม์) — คลิกแผนเพื่อดูรายการเงื่อนไขพร้อมค่าจริง */
export function PlanConditionsCard({ plans }) {
  const keys = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9', 'P10'].filter((k) => plans?.[k]);
  const [open, setOpen] = useState(null);
  return (
    <div className="card">
      <div className="card-header">
        <h3>
          <ListChecks size={17} className="text-gold" /> เงื่อนไขเข้าไม้รายแผน
        </h3>
        <span className="tiny faint">คลิกแผนเพื่อดูรายละเอียด</span>
      </div>
      {!keys.length ? (
        <Waiting text="อัปเดตโปรแกรมเป็นเวอร์ชันล่าสุดเพื่อแสดงเงื่อนไขเข้าไม้" />
      ) : (
        <div className="card-body stack" style={{ gap: 6 }}>
          {keys.map((k) => {
            const p = plans[k];
            const full = p.total > 0 && p.matched === p.total;
            const pct = p.total ? (p.matched / p.total) * 100 : 0;
            const color = full ? 'var(--green, #34d399)' : pct >= 50 ? 'var(--gold, #f2c14e)' : 'var(--text-3, #94a3b8)';
            const isOpen = open === k;
            return (
              <div key={k} style={{ borderRadius: 10, background: 'var(--surface-2, #171b23)', opacity: p.enabled === false ? 0.55 : 1 }}>
                <button
                  type="button"
                  onClick={() => setOpen(isOpen ? null : k)}
                  className="row-between"
                  style={{ width: '100%', padding: '9px 12px', background: 'none', border: 0, color: 'inherit', cursor: 'pointer', gap: 10 }}
                  aria-expanded={isOpen}
                >
                  <span className="row" style={{ gap: 10 }}>
                    <strong className="mono">{k}</strong>
                    <span className="small muted">{p.label}</span>
                    {p.enabled === false && <span className="badge badge-muted">ปิดอยู่</span>}
                  </span>
                  <span className="row" style={{ gap: 10 }}>
                    <span className="small" style={{ color: p.side === 'BUY' ? 'var(--green, #34d399)' : 'var(--red, #f87171)' }}>
                      {p.side === 'BUY' ? '▲ BUY' : '▼ SELL'}
                    </span>
                    <span className="badge mono" style={{ color, borderColor: color, background: 'transparent', border: '1px solid' }}>
                      {full ? '★ ' : ''}
                      {p.matched}/{p.total}
                      {full ? ' ครบ' : ''}
                    </span>
                  </span>
                </button>
                {isOpen && (
                  <ul style={{ listStyle: 'none', margin: 0, padding: '0 12px 10px' }}>
                    {(p.items || []).map((it, i) => (
                      <li key={i} className="row small" style={{ gap: 8, padding: '3px 0', alignItems: 'flex-start' }}>
                        <span className={`badge ${it.ok ? 'badge-green' : 'badge-red'}`} style={{ minWidth: 58, justifyContent: 'center' }}>
                          {it.ok ? '✓ ผ่าน' : '✗ ไม่ผ่าน'}
                        </span>
                        <span>
                          <strong>{it.name}</strong> <span className="muted">{it.desc}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const VERDICT = {
  hold: { cls: 'badge-green', color: 'var(--green, #34d399)' },
  caution: { cls: 'badge-gold', color: 'var(--gold, #f2c14e)' },
  close: { cls: 'badge-red', color: 'var(--red, #f87171)' },
};

/** AI วิเคราะห์ไม้ที่ถืออยู่: ถือต่อ / ระวัง / ควรปิด + เหตุผล (คำแนะนำเท่านั้น บอทไม่ปิดไม้ตามนี้) */
export function AdvisorCard({ advice }) {
  if (!advice?.length) return null;
  return (
    <div className="card section">
      <div className="card-header">
        <h3>
          <Brain size={17} className="text-gold" /> AI วิเคราะห์ไม้ที่ถืออยู่ · ถือต่อหรือปิด?
        </h3>
        <span className="tiny faint">คำแนะนำประกอบการตัดสินใจ ไม่รับประกันผล</span>
      </div>
      <div className="card-body stack" style={{ gap: 12 }}>
        {advice.map((a) => {
          const v = VERDICT[a.verdict] || VERDICT.caution;
          return (
            <div key={a.ticket} style={{ padding: '10px 12px', borderRadius: 10, background: 'var(--surface-2, #171b23)', borderLeft: `3px solid ${v.color}` }}>
              <div className="row-between wrap" style={{ gap: 8, marginBottom: 6 }}>
                <span className="row wrap" style={{ gap: 8 }}>
                  <span className={`badge ${v.cls}`}>{a.verdict_text}</span>
                  <span className="small mono">
                    #{a.ticket} · {a.side} · {planDisplay(a.plan)}
                  </span>
                </span>
                <span className="tiny muted mono">
                  คะแนน {a.score > 0 ? '+' : ''}
                  {a.score} · กำไร {a.profit > 0 ? '+' : ''}
                  {fmt(a.profit)}
                </span>
              </div>
              <div className="small" style={{ color: v.color, marginBottom: 6 }}>
                {a.advice}
              </div>
              <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {(a.reasons || []).map((r, i) => (
                  <li key={i} className="row tiny" style={{ gap: 8, padding: '2px 0', alignItems: 'flex-start' }}>
                    <span className={`badge ${r.w > 0 ? 'badge-green' : r.w < 0 ? 'badge-red' : 'badge-muted'}`} style={{ minWidth: 52, justifyContent: 'center' }}>
                      {r.w > 0 ? '▲ หนุน' : r.w < 0 ? '▼ สวน' : '• กลาง'}
                    </span>
                    <span className="muted">{r.text}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
