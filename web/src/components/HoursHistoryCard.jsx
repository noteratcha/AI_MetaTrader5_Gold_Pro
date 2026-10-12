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
const ACC_COLORS = ['#f2c14e', '#60a5fa', '#34d399', '#f472b6', '#a78bfa', '#fb923c'];
const OTHER = '#4b5263'; // นาทีที่ไม่มีเลขบัญชี (ก่อนเริ่มแยกตามบัญชี / โปรแกรมรุ่นเก่า)
const hrs = (m) => (m / 60).toLocaleString('th-TH', { maximumFractionDigits: 1 });
const fmtDay = (d) => new Date(`${d}T00:00:00+07:00`).toLocaleDateString('th-TH', { timeZone: 'Asia/Bangkok', day: 'numeric', month: 'short' });
const dot = (color) => <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 3, marginRight: 8, background: color }} />;

/** ประวัติการสะสมชั่วโมง (เวลาที่บอททำงานและถูกหักจริง) รายวัน แยกสีตามบัญชี MT5 — /api/user/hours-history */
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

  // เติมวันที่ไม่มีข้อมูลเป็น 0 · แยกนาทีตามบัญชี (ส่วนที่ไม่มีเลขบัญชี = other) · เกิน 62 วันรวมเป็นรายสัปดาห์
  const series = useMemo(() => {
    if (!data?.rows) return [];
    const map = Object.fromEntries(data.rows.map((r) => [r.day, r.minutes]));
    const byDay = {};
    for (const r of data.accounts?.days || []) {
      byDay[r.day] = byDay[r.day] || {};
      byDay[r.day][r.login] = (byDay[r.day][r.login] || 0) + r.minutes;
    }
    const out = [];
    const today = new Date(Date.now() + 7 * 3600000);
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(today.getTime() - i * 86400000).toISOString().slice(0, 10);
      const parts = { ...(byDay[d] || {}) };
      const known = Object.values(parts).reduce((a, x) => a + x, 0);
      const total = Math.max(map[d] || 0, known);
      if (total - known > 0.5) parts.other = total - known;
      out.push({ day: d, hours: total / 60, parts });
    }
    if (days <= 62) return out;
    const weeks = [];
    for (let i = 0; i < out.length; i += 7) {
      const chunk = out.slice(i, i + 7);
      const parts = {};
      chunk.forEach((x) => Object.entries(x.parts).forEach(([k, v]) => (parts[k] = (parts[k] || 0) + v)));
      weeks.push({ day: chunk[0].day, to: chunk[chunk.length - 1].day, hours: chunk.reduce((a, x) => a + x.hours, 0), parts });
    }
    return weeks;
  }, [data, days]);

  const total = series.reduce((a, x) => a + x.hours, 0);
  const max = Math.max(1, ...series.map((x) => x.hours));
  const active = series.filter((x) => x.hours > 0).length;
  const lv = data?.online?.level;
  const accList = data?.accounts?.list || [];
  const colorOf = (k) => {
    if (k === 'other') return OTHER;
    const i = accList.findIndex((a) => String(a.login) === String(k));
    return i >= 0 ? ACC_COLORS[i % ACC_COLORS.length] : OTHER;
  };
  const otherInRange = series.reduce((a, x) => a + (x.parts.other || 0), 0);
  const h = hover !== null ? series[hover] : null;
  const label = (k) => (k === 'other' ? 'ไม่ระบุ' : `#${k}`);

  return (
    <div className="card section">
      <div className="card-header">
        <h3>
          <History size={17} className="text-gold" /> ประวัติการสะสมชั่วโมง
        </h3>
        <div className="row wrap" style={{ gap: 6 }}>
          {RANGES.map(([v, text]) => (
            <button key={v} type="button" className={`btn btn-sm ${days === v ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setDays(v)}>
              {text}
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
                <div className="mono text-gold" style={{ fontSize: '1.3rem', fontWeight: 700 }}>
                  {total.toLocaleString('th-TH', { maximumFractionDigits: 1 })} ชม.
                </div>
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

            <div
              style={{ position: 'relative', display: 'flex', alignItems: 'flex-end', gap: series.length > 40 ? 1 : 3, height: 140, borderBottom: '1px solid var(--border, #262B36)' }}
              onMouseLeave={() => setHover(null)}
            >
              {series.map((x, i) => (
                // คอลัมน์สูงเต็มกราฟ = พื้นที่ชี้เมาส์ (ชี้วันที่ไม่มีชั่วโมงได้ด้วย) · แท่งจริงอยู่ด้านล่าง
                <div key={x.day} onMouseEnter={() => setHover(i)} style={{ flex: 1, height: '100%', display: 'flex', alignItems: 'flex-end', cursor: 'default' }}>
                  <div
                    style={{
                      width: '100%',
                      height: `${Math.max(x.hours > 0 ? 3 : 1, (x.hours / max) * 100)}%`,
                      display: 'flex',
                      flexDirection: 'column-reverse',
                      background: x.hours > 0 ? 'transparent' : 'var(--border, #262B36)',
                      borderRadius: '3px 3px 0 0',
                      overflow: 'hidden',
                      opacity: hover === null || hover === i ? 1 : 0.55,
                    }}
                  >
                    {x.hours > 0 && Object.entries(x.parts).map(([k, m]) => <div key={k} style={{ height: `${(m / 60 / x.hours) * 100}%`, background: colorOf(k) }} />)}
                  </div>
                </div>
              ))}
              {h && (
                <div
                  role="tooltip"
                  style={{
                    position: 'absolute',
                    bottom: 'calc(100% - 8px)',
                    ...(hover / series.length > 0.6
                      ? { right: `${100 - ((hover + 1) / series.length) * 100}%` }
                      : { left: `${(hover / series.length) * 100}%` }),
                    minWidth: 190,
                    padding: '10px 12px',
                    background: '#14171e',
                    border: '1px solid var(--gold, #f2c14e)',
                    borderRadius: 10,
                    boxShadow: '0 10px 30px rgba(0,0,0,.45)',
                    pointerEvents: 'none',
                    zIndex: 5,
                    fontSize: 12,
                    lineHeight: 1.55,
                    whiteSpace: 'nowrap',
                  }}
                >
                  <div style={{ fontWeight: 700, color: 'var(--gold, #f2c14e)', marginBottom: 4 }}>
                    {fmtDay(h.day)}
                    {h.to ? ` – ${fmtDay(h.to)}` : ''}
                  </div>
                  <div className="row-between" style={{ gap: 16 }}>
                    <span className="muted">รวม</span>
                    <strong className="mono">{h.hours.toLocaleString('th-TH', { maximumFractionDigits: 1 })} ชม.</strong>
                  </div>
                  {Object.entries(h.parts).map(([k, m]) => (
                    <div key={k} className="row-between" style={{ gap: 16 }}>
                      <span>
                        {dot(colorOf(k))}
                        {k === 'other' ? 'ไม่ระบุบัญชี' : `#${k}`}
                      </span>
                      <span className="mono">
                        {hrs(m)} ชม. <span className="faint">({h.hours > 0 ? Math.round((m / 60 / h.hours) * 100) : 0}%)</span>
                      </span>
                    </div>
                  ))}
                  {h.hours === 0 && <div className="faint">บอทไม่ได้ทำงาน</div>}
                </div>
              )}
            </div>
            <div className="row-between tiny faint" style={{ marginTop: 6, gap: 8 }}>
              <span>{series[0] ? fmtDay(series[0].day) : ''}</span>
              <span style={{ textAlign: 'center' }}>
                {h
                  ? `${fmtDay(h.day)}${h.to ? ` – ${fmtDay(h.to)}` : ''} · ${h.hours.toFixed(1)} ชม.${Object.entries(h.parts)
                      .map(([k, m]) => ` · ${label(k)} ${hrs(m)}`)
                      .join('')}`
                  : days > 62
                    ? 'รวมรายสัปดาห์ · สีตามบัญชี MT5'
                    : 'รายวัน (เวลาไทย) · สีตามบัญชี MT5'}
              </span>
              <span>วันนี้</span>
            </div>

            {(accList.length > 0 || otherInRange > 0) && (
              <div className="table-wrap" style={{ marginTop: 16 }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>บัญชี MT5</th>
                      <th>โบรกเกอร์ / Profile</th>
                      <th className="num">ช่วงนี้</th>
                      <th className="num">สัดส่วน</th>
                      <th className="num">สะสมทั้งหมด</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accList.map((a) => (
                      <tr key={a.login}>
                        <td className="mono nowrap">
                          {dot(colorOf(a.login))}#{a.login}
                        </td>
                        <td className="small muted">
                          {[a.server, a.profile && `Profile ${a.profile}`, a.mode && (a.mode === 'REAL' ? 'บัญชีจริง' : 'Demo')].filter(Boolean).join(' · ') || '—'}
                        </td>
                        <td className="num mono">{hrs(a.minutesInRange)} ชม.</td>
                        <td className="num mono">{total > 0 ? ((a.minutesInRange / 60 / total) * 100).toFixed(0) : 0}%</td>
                        <td className="num mono text-gold">{hrs(a.minutesTotal)} ชม.</td>
                      </tr>
                    ))}
                    {otherInRange > 0 && (
                      <tr>
                        <td className="nowrap">
                          {dot(OTHER)}ไม่ระบุบัญชี
                        </td>
                        <td className="small faint">ก่อนเริ่มแยกตามบัญชี / โปรแกรมรุ่นเก่า</td>
                        <td className="num mono">{hrs(otherInRange)} ชม.</td>
                        <td className="num mono">{total > 0 ? ((otherInRange / 60 / total) * 100).toFixed(0) : 0}%</td>
                        <td className="num faint">—</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
