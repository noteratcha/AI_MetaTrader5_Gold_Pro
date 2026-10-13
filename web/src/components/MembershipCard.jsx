'use client';

import { useState } from 'react';
import { Check, ChevronDown, Crown, History, Lock, Star } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { MEMBERSHIP, MEMBERSHIP_PLANS, MEMBER_PLAN_NUMBERS, MEMBER_WARN_DAYS } from '../lib/membership';
import { PLAN_NAMES } from '../lib/plans';
import { formatThb } from '../lib/format';

// ราคาสมาชิก: ทศนิยม 2 ตำแหน่งเมื่อมีเศษ (฿1,128.60) · จำนวนเต็มไม่แสดงทศนิยม (฿99)
const baht = (v) => `฿${Number(v).toLocaleString('en-US', { minimumFractionDigits: Number(v) % 1 ? 2 : 0, maximumFractionDigits: 2 })}`;

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
    <div id="membership" className={`card card-pad ${m.active ? 'card-gold' : ''}`} style={{ marginBottom: 18, scrollMarginTop: 90 }}>
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
        {onBuy && compact && (
          <button className="btn btn-primary" onClick={() => onBuy(null)}>
            <Crown size={16} /> {m.active && !m.viaAdmin ? 'ต่ออายุสมาชิก' : 'สมัครสมาชิก'}
          </button>
        )}
      </div>
      {onBuy && !compact && <PlanPicker renew={m.active && !m.viaAdmin} onBuy={onBuy} />}
      {showHistory && <MembershipHistory />}
    </div>
  );
}

/** เลือกแพ็กเกจสมาชิก 30 / 90 / 180 / 360 วัน (360 วันลด 5%) แล้วกดสมัคร — แสดงกับทุกบัญชี (แอดมินสมัครได้เพื่อทดสอบ) */
function PlanPicker({ renew, onBuy }) {
  const featured = MEMBERSHIP_PLANS.find((p) => p.featured) || MEMBERSHIP_PLANS[0];
  const [sel, setSel] = useState(featured.id);   // เลือกแพ็กเกจแนะนำไว้ก่อน
  const chosen = MEMBERSHIP_PLANS.find((p) => p.id === sel) || featured;
  const perMonth = (p) => baht(Math.round((p.price / p.days) * 30 * 100) / 100);
  return (
    <div style={{ marginTop: 14 }}>
      <div className="member-plans">
        {MEMBERSHIP_PLANS.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`member-plan ${p.featured ? 'is-featured' : ''} ${p.id === sel ? 'is-active' : ''}`}
            onClick={() => setSel(p.id)}
            aria-pressed={p.id === sel}
          >
            {p.featured && (
              <span className="member-plan-ribbon">
                <Star size={11} fill="currentColor" /> แนะนำ · คุ้มที่สุด
              </span>
            )}
            {p.discountPct > 0 && <span className="badge badge-green member-plan-badge">ลด {p.discountPct}%</span>}
            <span className="member-plan-days">{p.label}</span>
            <span className="mono member-plan-price">{baht(p.price)}</span>
            <span className="tiny faint">
              {p.discountPct > 0 && <span style={{ textDecoration: 'line-through', marginRight: 6 }}>{baht(p.fullPrice)}</span>}
              ตกเดือนละ {perMonth(p)}
            </span>
            {p.discountPct > 0 && (
              <span className="member-plan-save">ประหยัด {baht(Math.round((p.fullPrice - p.price) * 100) / 100)} · ใช้ได้ทั้งปีไม่ต้องต่ออายุ</span>
            )}
          </button>
        ))}
      </div>
      <div className="row-between wrap" style={{ gap: 10, marginTop: 12 }}>
        <span className="tiny faint">
          นับตามวันปฏิทิน (วันที่ชำระ = วันที่ 1) · {renew ? 'ต่ออายุแล้วบวกต่อจากวันสุดท้ายเดิม · ' : ''}ส่วนลด Lv./ออนไลน์ใช้กับการเติมชั่วโมงเท่านั้น
        </span>
        <button className="btn btn-primary" onClick={() => onBuy(chosen)}>
          <Crown size={16} /> {renew ? 'ต่ออายุ' : 'สมัครสมาชิก'} {chosen.label} · {baht(chosen.price)}
        </button>
      </div>
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
