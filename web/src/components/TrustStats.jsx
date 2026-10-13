'use client';

import { useEffect, useState } from 'react';
import { Bot, Clock, Eye, ShieldCheck } from 'lucide-react';

// ตัวเลขสะสมเพื่อความน่าเชื่อถือ (/api/public-stats): ชั่วโมงที่บอททำงานสะสม · จำนวนครั้งที่รันบอท · จำนวนครั้งที่เข้าชมเว็บ
let cache = null;
let pending = null;
function useTrustStats() {
  const [d, setD] = useState(cache);
  useEffect(() => {
    if (cache) return;
    pending ||= fetch('/api/public-stats').then((r) => r.json()).catch(() => null);
    pending.then((x) => {
      if (x?.success) {
        cache = x;
        setD(x);
      }
    });
  }, []);
  return d;
}

/** นับการเข้าชมเว็บ 1 ครั้งต่อการเปิดแท็บ */
export function useCountVisit() {
  useEffect(() => {
    try {
      if (sessionStorage.getItem('gb24_visit')) return;
      sessionStorage.setItem('gb24_visit', '1');
      fetch('/api/track', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ event: 'web_visit' }) }).catch(() => {});
    } catch {}
  }, []);
}

const n = (v) => Number(v).toLocaleString('th-TH');
const ITEMS = (d) =>
  [
    d.totalHours !== null && { key: 'hours', icon: Clock, value: n(d.totalHours), unit: 'ชม.', label: 'ชั่วโมงที่บอทของผู้ใช้ทำงานสะสม', color: 'var(--gold, #f2c14e)' },
    d.botRuns !== null && { key: 'runs', icon: Bot, value: n(d.botRuns), unit: 'ครั้ง', label: 'จำนวนครั้งที่รันบอท (นับทุกบอท)', color: 'var(--green, #34d399)' },
    d.webVisits !== null && { key: 'visits', icon: Eye, value: n(d.webVisits), unit: 'ครั้ง', label: 'จำนวนครั้งที่เข้าชมเว็บ', color: 'var(--sky, #60a5fa)' },
  ].filter(Boolean);

/** แถบตัวเลขสะสมท้ายเว็บ */
export function TrustStrip() {
  const d = useTrustStats();
  if (!d) return null;
  return (
    <div className="row wrap" style={{ gap: 24, justifyContent: 'center', padding: '14px 0', borderTop: '1px solid var(--border, #262B36)' }}>
      {ITEMS(d).map(({ key, icon: Icon, value, unit, label, color }) => (
        <span key={key} className="row small" style={{ gap: 8 }} title={label}>
          <Icon size={16} style={{ color }} />
          <span className="muted">{label}</span>
          <strong className="mono" style={{ color }}>
            {value}
          </strong>
          <span className="muted">{unit}</span>
        </span>
      ))}
    </div>
  );
}

/** การ์ดตัวเลขสะสมขนาดใหญ่ (หน้าแรก) */
export function TrustCards() {
  const d = useTrustStats();
  if (!d) return null;
  const items = ITEMS(d);
  if (!items.length) return null;
  return (
    <section className="container" style={{ margin: '8px auto 40px' }}>
      <div className="row" style={{ gap: 8, justifyContent: 'center', marginBottom: 14 }}>
        <ShieldCheck size={18} className="text-gold" />
        <strong>ใช้งานจริง ตัวเลขสะสมจากระบบ</strong>
      </div>
      <div className={`grid grid-${items.length}`}>
        {items.map(({ key, icon: Icon, value, unit, label, color }) => (
          <div key={key} className="card card-pad" style={{ textAlign: 'center', borderTop: `3px solid ${color}` }}>
            <Icon size={22} style={{ color, marginBottom: 6 }} />
            <div className="mono" style={{ fontSize: 'clamp(1.6rem, 4vw, 2.2rem)', fontWeight: 700, color }}>
              {value} <span style={{ fontSize: '1rem' }}>{unit}</span>
            </div>
            <div className="small muted">{label}</div>
          </div>
        ))}
      </div>
      <p className="tiny faint" style={{ textAlign: 'center', marginTop: 10 }}>
        นับอัตโนมัติจากการใช้งานจริงของผู้ใช้ทุกคน · อัปเดตทุก 5 นาที
      </p>
    </section>
  );
}
