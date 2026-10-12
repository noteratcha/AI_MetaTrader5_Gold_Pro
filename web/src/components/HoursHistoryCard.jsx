'use client';

import { useEffect, useMemo, useState } from 'react';
import { History } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const RANGES = [
  [7, '7 วัน'],
  [30, '30 วัน'],
  [90, '90 วัน'],
  [365, '1 ปี'],
];
const fmtDay = (d) => new Date(`${d}T00:00:00+07:00`).toLocaleDateString('th-TH', { timeZone: 'Asia/Bangkok', day: 'numeric', month: 'short' });

/** ประวัติการสะสมชั่วโมง (เวลาที่บอททำงานและถูกหักจริง) รายวัน — /api/user/hours-history */
export default function HoursHistoryCard() {
  const { apiFetch } = useAuth();
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    let alive = true;
    apiFetch(`/api/user/hours-history?days=${days}`)
      .then((d) => alive && setData(d))
      .catch(() => alive && setData({ rows: [], available: false }));
    return () => {
      alive = false;
    };
  }, [apiFetch, days]);

  // เติมวันที่ไม่มีข้อมูลเป็น 0 ให้กราฟต่อเนื่อง · เกิน 62 วันรวมเป็นรายสัปดาห์
  const series = useMemo(() => {
    if (!data?.rows) return [];
    const map = Object.fromEntries(data.rows.map((r) => [r.day, r.minutes]));
    const out = [];
    const today = new Date(Date.now() + 7 * 3600000);
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(today.getTime() - i * 86400000).toISOString().slice(0, 10);
      out.push({ day: d, hours: (map[d] || 0) / 60 });
    }
    if (days <= 62) return out;
    const weeks = [];
    for (let i = 0; i < out.length; i += 7) {
      const chunk = out.slice(i, i + 7);
      weeks.push({ day: chunk[0].day, to: chunk[chunk.length - 1].day, hours: chunk.reduce((a, x) => a + x.hours, 0) });
    }
    return weeks;
  }, [data, days]);

  const total = series.reduce((a, x) => a + x.hours, 0);
  const max = Math.max(1, ...series.map((x) => x.hours));
  const active = series.filter((x) => x.hours > 0).length;
  const lv = data?.online?.level;

  return (
    <div className="card section">
      <div className="card-header">
        <h3>
          <History size={17} className="text-gold" /> ประวัติการสะสมชั่วโมง
        </h3>
        <div className="row wrap" style={{ gap: 6 }}>
          {RANGES.map(([v, label]) => (
            <button key={v} type="button" className={`btn btn-sm ${days === v ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setDays(v)}>
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="card-body">
        {data && !data.available ? (
          <p className="muted small" style={{ margin: 0 }}>ระบบประวัติรายวันยังไม่เปิดใช้งาน (รอแอดมินอัปเดตฐานข้อมูล)</p>
        ) : (
          <>
            <div className="row wrap" style={{ gap: 20, marginBottom: 12 }}>
              <div>
                <div className="tiny faint">สะสมในช่วงนี้</div>
                <div className="mono text-gold" style={{ fontSize: '1.3rem', fontWeight: 700 }}>{total.toLocaleString('th-TH', { maximumFractionDigits: 1 })} ชม.</div>
              </div>
              <div>
                <div className="tiny faint">{days > 62 ? 'สัปดาห์ที่บอททำงาน' : 'วันที่บอททำงาน'}</div>
                <div className="mono" style={{ fontSize: '1.3rem', fontWeight: 700 }}>
                  {active} / {series.length}
                </div>
              </div>
              {lv && (
                <div>
                  <div className="tiny faint">สะสมทั้งหมด (ระดับสมาชิก)</div>
                  <div className="mono" style={{ fontSize: '1.3rem', fontWeight: 700 }}>
                    {lv.totalHours.toLocaleString('th-TH')} ชม. · <span className="text-gold">Lv.{lv.level}</span>
                  </div>
                </div>
              )}
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: series.length > 40 ? 1 : 3, height: 140, borderBottom: '1px solid var(--border, #262B36)' }}>
              {series.map((x, i) => (
                <div
                  key={x.day}
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                  title={`${fmtDay(x.day)}${x.to ? ` – ${fmtDay(x.to)}` : ''}: ${x.hours.toFixed(1)} ชม.`}
                  style={{
                    flex: 1,
                    height: `${Math.max(x.hours > 0 ? 3 : 1, (x.hours / max) * 100)}%`,
                    background: x.hours > 0 ? (hover === i ? 'var(--gold)' : 'linear-gradient(180deg, var(--gold), #9a6b12)') : 'var(--border, #262B36)',
                    borderRadius: '3px 3px 0 0',
                    cursor: 'default',
                  }}
                />
              ))}
            </div>
            <div className="row-between tiny faint" style={{ marginTop: 6 }}>
              <span>{series[0] ? fmtDay(series[0].day) : ''}</span>
              <span>{hover !== null && series[hover] ? `${fmtDay(series[hover].day)}${series[hover].to ? ` – ${fmtDay(series[hover].to)}` : ''} · ${series[hover].hours.toFixed(1)} ชม.` : days > 62 ? 'รวมรายสัปดาห์' : 'รายวัน (เวลาไทย)'}</span>
              <span>วันนี้</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
