'use client';

import { Gift, Timer } from 'lucide-react';
import { ONLINE_DISCOUNT_DAYS, ONLINE_DISCOUNT_PCT, ONLINE_GOAL_HOURS } from '../lib/onlineReward';

const fmtDate = (iso, withTime = false) =>
  new Date(iso).toLocaleString('th-TH', {
    timeZone: 'Asia/Bangkok', day: 'numeric', month: 'short',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  });

/** รางวัลออนไลน์: ความคืบหน้ารอบปัจจุบัน (ครบ 100 ชม. เริ่มรอบใหม่ทันที) + ส่วนลดที่ได้รับ (online จาก /api/auth/me) */
export default function OnlineRewardCard({ online }) {
  if (!online) return null;
  const hours = online.minutes / 60;
  const goal = online.goalMinutes / 60 || ONLINE_GOAL_HOURS;
  const pct = Math.min(100, (hours / goal) * 100);
  const d = online.discount;
  const reached = online.minutes >= online.goalMinutes;
  return (
    <div className={`card card-pad ${d ? 'card-gold' : ''}`} style={{ marginBottom: 18 }}>
      <div className="row-between wrap" style={{ gap: 12, marginBottom: 10 }}>
        <div className="row" style={{ gap: 12 }}>
          <span className="icon-chip text-gold" style={{ width: 38, height: 38 }}>
            {d ? <Gift size={18} /> : <Timer size={18} />}
          </span>
          <div>
            <div style={{ fontWeight: 700 }}>
              ออนไลน์ครบ {ONLINE_GOAL_HOURS} ชม. รับส่วนลด {ONLINE_DISCOUNT_PCT}%
            </div>
            <div className="tiny muted">
              นับเฉพาะเวลาที่บอททำงานและถูกหักชั่วโมง · ใช้ได้กับการซื้อครั้งถัดไป 1 รายการ ภายใน {ONLINE_DISCOUNT_DAYS} วัน
              (เมื่อได้รับส่วนลดเก็บเพื่อรอใช้งานแล้ว ระบบจะเริ่มนับชั่วโมงใหม่ทันที)
            </div>
          </div>
        </div>
        {d && (
          <span className="badge badge-green" style={{ fontSize: '0.85rem', padding: '6px 12px' }}>
            มีส่วนลด {d.percent}% · ใช้ได้ถึง {fmtDate(d.expiresAt, true)} น.
          </span>
        )}
      </div>
      <div className="row-between tiny" style={{ marginBottom: 6 }}>
        <span className="muted">{d ? 'ความคืบหน้ารอบใหม่' : 'ความคืบหน้ารอบปัจจุบัน'}</span>
        <span className="mono" style={{ fontWeight: 700, color: reached ? 'var(--green)' : 'var(--gold)' }}>
          {hours.toFixed(1)} / {goal} ชม.{reached ? ' · ครบแล้ว' : ` · อีก ${(goal - hours).toFixed(1)} ชม.`}
        </span>
      </div>
      <div style={{ height: 10, borderRadius: 999, background: 'var(--border, #262B36)', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', borderRadius: 999, background: reached ? 'var(--green)' : 'var(--gold)', transition: 'width .4s' }} />
      </div>
    </div>
  );
}
