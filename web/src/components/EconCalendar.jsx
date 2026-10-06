'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { CalendarDays, ExternalLink, RefreshCw, Timer } from 'lucide-react';
import { EmptyState } from './ui';
import { newsImpactDetail, newsImpactText } from './LiveInsights';

const IMPACT = {
  High: { label: 'สูง', className: 'impact impact-high', rank: 3 },
  Medium: { label: 'กลาง', className: 'impact impact-medium', rank: 2 },
  Low: { label: 'ต่ำ', className: 'impact impact-low', rank: 1 },
  Holiday: { label: 'วันหยุด', className: 'impact impact-holiday', rank: 0 },
};

const TZ = 'Asia/Bangkok';
const dayKey = (d) => d.toLocaleDateString('en-CA', { timeZone: TZ });
const dayLabel = (d) => d.toLocaleDateString('th-TH', { timeZone: TZ, weekday: 'long', day: 'numeric', month: 'short' });
const timeLabel = (d) => d.toLocaleTimeString('th-TH', { timeZone: TZ, hour: '2-digit', minute: '2-digit' });

export function useCalendar() {
  const [state, setState] = useState({ events: null, error: '', updatedAt: null });

  const load = async () => {
    try {
      const r = await fetch('/api/calendar');
      const d = await r.json();
      if (!d.success) throw new Error(d.error);
      setState({ events: d.events.map((e) => ({ ...e, at: new Date(e.date) })), error: '', updatedAt: d.updatedAt });
    } catch (err) {
      setState((s) => ({ ...s, events: s.events || [], error: err.message || 'โหลดปฏิทินข่าวไม่สำเร็จ' }));
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 30 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  return { ...state, reload: load };
}

export function formatCountdown(target, now = Date.now()) {
  const secs = Math.floor((target - now) / 1000);
  if (secs <= 0) return 'กำลังประกาศ';
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (d) return `อีก ${d} วัน ${h} ชม.`;
  if (h) return `อีก ${h} ชม. ${m} นาที`;
  return `อีก ${m} นาที`;
}

function useNow(intervalMs = 30000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

/** การ์ด "ข่าวสำคัญถัดไป" (USD ผลกระทบสูง) พร้อมนับถอยหลัง */
export function NextNewsCard({ events }) {
  const now = useNow();
  const next = (events || []).find((e) => e.currency === 'USD' && e.impact === 'High' && e.at.getTime() > now - 5 * 60000);
  const soon = next && next.at.getTime() - now < 3600000;

  return (
    <div className="card">
      <div className="card-header">
        <h3>
          <CalendarDays size={17} className="text-gold" /> ข่าวสำคัญถัดไป (USD)
        </h3>
        <Link href="/calendar" className="btn btn-ghost btn-sm">
          ดูทั้งหมด
        </Link>
      </div>
      <div className="card-body">
        {events === null ? (
          <div className="skeleton" style={{ height: 64 }} />
        ) : !next ? (
          <p className="small muted">ไม่มีข่าว USD ผลกระทบสูงที่เหลือในสัปดาห์นี้</p>
        ) : (
          <div className="stack" style={{ gap: 6 }}>
            <span className="impact impact-high" style={{ alignSelf: 'flex-start' }}>
              ผลกระทบสูง
            </span>
            <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{next.title}</div>
            <div className="small muted">
              {dayLabel(next.at)} · {timeLabel(next.at)} น.
              {(next.forecast || next.previous) && ` · คาด ${next.forecast || '—'} · ก่อน ${next.previous || '—'}`}
            </div>
            <div className={`row ${soon ? 'text-red' : 'text-gold'}`} style={{ fontWeight: 700, marginTop: 4 }}>
              <Timer size={16} /> {formatCountdown(next.at.getTime(), now)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/** รายการปฏิทินเศรษฐกิจแบบเต็ม พร้อมตัวกรอง */
export function EconCalendarList({ events, error, updatedAt, onReload, impacts = null }) {
  const [openKey, setOpenKey] = useState(null);
  const now = useNow(60000);
  const [usdOnly, setUsdOnly] = useState(true);
  const [minImpact, setMinImpact] = useState('Medium');

  const groups = useMemo(() => {
    const floor = IMPACT[minImpact]?.rank ?? 0;
    const filtered = (events || []).filter((e) => (!usdOnly || e.currency === 'USD') && (IMPACT[e.impact]?.rank ?? 0) >= floor);
    const map = new Map();
    for (const e of filtered) {
      const k = dayKey(e.at);
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(e);
    }
    return [...map.entries()];
  }, [events, usdOnly, minImpact]);

  const todayKey = dayKey(new Date(now));

  return (
    <div className="card">
      <div className="card-header wrap" style={{ gap: 10 }}>
        <div className="row wrap" style={{ gap: 10 }}>
          <div className="segmented" style={{ width: 260 }}>
            <button className={usdOnly ? 'is-active' : ''} onClick={() => setUsdOnly(true)}>
              USD (มีผลต่อทอง)
            </button>
            <button className={!usdOnly ? 'is-active' : ''} onClick={() => setUsdOnly(false)}>
              ทุกสกุลเงิน
            </button>
          </div>
          <div className="segmented" style={{ width: 240 }}>
            {[
              ['High', 'สูง'],
              ['Medium', 'กลาง+สูง'],
              ['Low', 'ทั้งหมด'],
            ].map(([v, label]) => (
              <button key={v} className={minImpact === v ? 'is-active' : ''} onClick={() => setMinImpact(v)}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={onReload} title="โหลดใหม่">
          <RefreshCw size={14} /> โหลดใหม่
        </button>
      </div>

      {events === null ? (
        <div className="card-body stack">
          {[0, 1, 2].map((i) => (
            <div key={i} className="skeleton" style={{ height: 40 }} />
          ))}
        </div>
      ) : groups.length === 0 ? (
        <EmptyState icon={CalendarDays} title={error ? 'โหลดปฏิทินข่าวไม่สำเร็จ' : 'ไม่มีข่าวตามตัวกรอง'}>
          {error || 'ลองเปลี่ยนตัวกรองเป็น “ทุกสกุลเงิน” หรือ “ทั้งหมด”'}
        </EmptyState>
      ) : (
        <div className="cal-list">
          {groups.map(([key, list]) => (
            <div key={key}>
              <div className={`cal-day ${key === todayKey ? 'is-today' : ''}`}>
                {dayLabel(list[0].at)}
                {key === todayKey && <span className="badge badge-gold">วันนี้</span>}
              </div>
              {list.map((e, i) => {
                const past = e.at.getTime() < now;
                const imp = IMPACT[e.impact] || IMPACT.Low;
                const n = impacts?.get(`${e.title}|${e.at.getTime()}`);
                const rowKey = `${e.date}-${i}`;
                const t = n ? newsImpactText(n) : null;
                return (
                  <div key={rowKey}>
                  <div
                    className={`cal-row ${impacts ? 'has-impact' : ''} ${past ? 'is-past' : ''}`}
                    onClick={n ? () => setOpenKey(openKey === rowKey ? null : rowKey) : undefined}
                    style={n ? { cursor: 'pointer' } : undefined}
                  >
                    <span className="mono cal-time">{timeLabel(e.at)}</span>
                    <span className="cal-cur">{e.currency}</span>
                    <span className={imp.className}>{imp.label}</span>
                    <span className="cal-title">{e.title}</span>
                    <span className="cal-num">
                      <span className="faint">คาด</span> {e.forecast || '—'}
                    </span>
                    <span className="cal-num">
                      <span className="faint">ก่อน</span> {e.previous || '—'}
                    </span>
                    {impacts && (
                      <span className="cal-impact" style={{ color: t?.color }}>
                        {t ? `${t.text} ›` : ''}
                      </span>
                    )}
                  </div>
                  {n && openKey === rowKey && (
                    <div className="cal-impact-detail tiny muted">
                      {newsImpactDetail(n).map((p) => (
                        <div key={p}>• {p}</div>
                      ))}
                    </div>
                  )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
      <div className="card-body tiny faint" style={{ paddingTop: 12, borderTop: '1px solid var(--border)' }}>
        เวลาไทย (UTC+7) · ปฏิทินข่าวเศรษฐกิจรายสัปดาห์{updatedAt ? ` · อัปเดต ${new Date(updatedAt).toLocaleTimeString('th-TH', { timeZone: TZ, hour: '2-digit', minute: '2-digit' })} น.` : ''}
      </div>
    </div>
  );
}

// Widget ปฏิทินอย่างเป็นทางการของ Investing.com (สำหรับฝังในเว็บไซต์)
const INVESTING_WIDGET =
  'https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&features=datepicker,timezone,timeselector,filters&countries=5&calType=week&lang=1';

export function InvestingWidget() {
  return (
    <div className="card">
      <div className="card-header">
        <h3>Investing.com Economic Calendar</h3>
        <a className="btn btn-secondary btn-sm" href="https://th.investing.com/economic-calendar/" target="_blank" rel="noopener noreferrer">
          เปิดบน Investing.com <ExternalLink size={14} />
        </a>
      </div>
      <div className="investing-frame">
        <iframe src={INVESTING_WIDGET} title="Investing.com Economic Calendar" loading="lazy" referrerPolicy="no-referrer-when-downgrade" />
      </div>
      <div className="card-body tiny faint" style={{ paddingTop: 10 }}>
        Real Time Economic Calendar provided by{' '}
        <a href="https://www.investing.com/" target="_blank" rel="noopener noreferrer" className="text-sky">
          Investing.com
        </a>
        . หากตารางไม่แสดง (บางเบราว์เซอร์บล็อก) ให้กด “เปิดบน Investing.com”
      </div>
    </div>
  );
}
