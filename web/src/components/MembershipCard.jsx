'use client';

import { useState } from 'react';
import { Check, ChevronDown, Crown, History, Lock } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { MEMBERSHIP, MEMBER_PLAN_NUMBERS, MEMBER_WARN_DAYS } from '../lib/membership';
import { PLAN_NAMES } from '../lib/plans';
import { formatThb } from '../lib/format';

const fmtDate = (iso) =>
  new Date(iso).toLocaleDateString('th-TH', { timeZone: 'Asia/Bangkok', day: 'numeric', month: 'short', year: 'numeric' });

/**
 * สมาชิกรายเดือน: สถานะปัจจุบัน + ปุ่มสมัคร/ต่ออายุ (onBuy เปิดหน้าต่างชำระเงินเดิม)
 * compact = แสดงแค่สถานะ (หน้ากระเป๋าเวลา)
 */
export default function MembershipCard({ membership, onBuy, compact = false, showHistory = false }) {
  const m = membership || { active: false };
  const warn = m.active && !m.viaAdmin && m.daysLeft <= MEMBER_WARN_DAYS;
  return (
    <div className={`card card-pad ${m.active ? 'card-gold' : ''}`} style={{ marginBottom: 18 }}>
      <div className="row-between wrap" style={{ gap: 14 }}>
        <div className="row" style={{ gap: 12, alignItems: 'flex-start' }}>
          <span className="icon-chip text-gold" style={{ width: 40, height: 40 }}>
            <Crown size={19} />
          </span>
          <div>
            <div className="row wrap" style={{ gap: 8 }}>
              <span style={{ fontWeight: 700 }}>{MEMBERSHIP.name}</span>
              {m.active ? (
                <span className={`badge ${warn ? 'badge-red' : 'badge-green'}`}>
                  {m.viaAdmin ? 'แอดมิน · ใช้ได้ทุกแผน' : `ใช้งานอยู่ · ถึง ${fmtDate(m.until)} (อีก ${m.daysLeft} วัน)`}
                </span>
              ) : (
                <span className="badge">ยังไม่เป็นสมาชิก{m.until ? ` · หมดอายุ ${fmtDate(m.until)}` : ''}</span>
              )}
            </div>
            <div className="tiny muted" style={{ marginTop: 4 }}>
              ผู้ใช้ทั่วไปใช้ได้แผน P1–P5 · สมาชิกปลดล็อกทุกแผน (P1–P8) · ยังหักชั่วโมงตามการใช้งานปกติ
            </div>
            {!compact && (
              <div className="row wrap" style={{ gap: 6, marginTop: 8 }}>
                {MEMBER_PLAN_NUMBERS.map((n) => (
                  <span key={n} className="badge badge-gold">
                    {m.active ? <Check size={12} /> : <Lock size={12} />} {PLAN_NAMES[n]}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
        {onBuy && !m.viaAdmin && (
          <div className="stack" style={{ alignItems: 'flex-end', gap: 6 }}>
            <div className="row" style={{ gap: 8, alignItems: 'baseline' }}>
              <span className="mono text-gold" style={{ fontSize: '1.35rem', fontWeight: 700 }}>
                {formatThb(MEMBERSHIP.price)}
              </span>
              <span className="small muted">/ {MEMBERSHIP.days} วัน</span>
            </div>
            <span className="tiny faint">ราคาเต็ม · ส่วนลด Lv./ออนไลน์ใช้กับการเติมชั่วโมงเท่านั้น</span>
            <button className="btn btn-primary" onClick={onBuy}>
              <Crown size={16} /> {m.active ? 'ต่ออายุอีก 30 วัน' : 'สมัครสมาชิก'}
            </button>
            {m.active && <span className="tiny faint">ต่ออายุแล้วนับต่อจากวันหมดอายุเดิม</span>}
          </div>
        )}
      </div>
      {showHistory && <MembershipHistory />}
    </div>
  );
}

/** ประวัติสมาชิก: สมัคร / ต่ออายุ / แอดมินปรับ / ยกเลิก (จาก /api/user/membership) — โหลดเมื่อกดเปิด */
function MembershipHistory() {
  const { apiFetch } = useAuth();
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState(null);
  const toggle = () => {
    setOpen((v) => !v);
    if (rows === null) {
      apiFetch('/api/user/membership')
        .then((d) => setRows(d.history || []))
        .catch(() => setRows([]));
    }
  };
  return (
    <div style={{ marginTop: 12, borderTop: '1px solid var(--border)', paddingTop: 10 }}>
      <button type="button" className="btn btn-ghost btn-sm" onClick={toggle}>
        <History size={14} /> ประวัติสมาชิก <ChevronDown size={14} style={{ transform: open ? 'rotate(180deg)' : 'none' }} />
      </button>
      {open && (
        <div className="table-wrap" style={{ marginTop: 8 }}>
          {rows === null ? (
            <div className="small muted">กำลังโหลด...</div>
          ) : rows.length === 0 ? (
            <div className="small muted">ยังไม่มีประวัติ</div>
          ) : (
            <table className="table">
              <thead>
                <tr><th>วันที่ (เวลาไทย)</th><th>รายการ</th><th>โดย</th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.at + r.detail}>
                    <td className="nowrap mono small">
                      {new Date(r.at).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', dateStyle: 'medium', timeStyle: 'short' })}
                    </td>
                    <td className="small">{r.detail}</td>
                    <td className="small">{r.byAdmin ? <span className="badge badge-gold">แอดมิน</span> : <span className="badge">ระบบ</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
