'use client';

// ชวนเพื่อน (Referral · ผู้ใช้สั่ง 16 ต.ค. 2026): ลิงก์แนะนำของฉัน · แชร์ LINE · เพื่อนที่สมัครผ่านลิงก์ (ชื่อ/อีเมลปิดบางส่วน) · ชั่วโมงที่ได้
import { useCallback, useEffect, useState } from 'react';
import { Gift, RefreshCw, Share2, Users } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { CopyButton, Pager } from './ui';
import { REF_STORAGE_KEY, normalizeRefCode, referralLink } from '../lib/referral';
import { formatThaiDateTime } from '../lib/format';

const PER_PAGE = 5;
function statusOf(f, run) {
  if (f.status === 'rewarded') return { text: '+48 ชม. ✓', color: 'var(--green)' };
  if (f.status === 'blocked') return { text: `ไม่ได้ชั่วโมง${f.why ? ` · ${f.why}` : ''}`, color: 'var(--text-3)' };
  return { text: `รันบอทแล้ว ${f.progress} / ${run} ชม.`, color: 'var(--gold)', pct: Math.min(100, (f.progress / run) * 100) };
}

/** จำรหัสผู้แนะนำจากลิงก์ ?ref= (ทุกหน้า · 30 วัน · คนแรกที่แนะนำไม่ถูกทับภายในอายุ) */
export function RefCapture() {
  useEffect(() => {
    try {
      const code = normalizeRefCode(new URLSearchParams(window.location.search).get('ref'));
      if (!code) return;
      const cur = JSON.parse(localStorage.getItem(REF_STORAGE_KEY) || 'null');
      if (cur && cur.code && Date.now() - cur.at < 30 * 86400000) return;
      localStorage.setItem(REF_STORAGE_KEY, JSON.stringify({ code, at: Date.now() }));
    } catch {
      /* ข้าม */
    }
  }, []);
  return null;
}

export default function ReferralCard() {
  const { apiFetch } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await apiFetch('/api/user/referral'));
      setError('');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);
  useEffect(() => {
    load();
  }, [load]);

  const origin = typeof window !== 'undefined' ? window.location.origin : 'https://goldbot24.vercel.app';
  const link = data ? referralLink(data.code, origin) : '';
  const share = `สมัคร Gold Bot 24 บอทเทรดทองอัตโนมัติ รับฟรี 48 ชั่วโมง ผ่านลิงก์นี้ ${link}`;
  const friends = data?.friends || [];
  const pages = Math.max(1, Math.ceil(friends.length / PER_PAGE));
  const p = Math.min(page, pages);
  const shown = friends.slice((p - 1) * PER_PAGE, p * PER_PAGE);

  return (
    <div className="card ref-card">
      <div className="card-header">
        <h3>
          <Gift size={17} className="text-gold" /> ชวนเพื่อน รับ {data?.rewardHours || 48} ชม. ต่อคน
        </h3>
        <button className="btn btn-secondary btn-sm" onClick={load} disabled={loading} aria-label="รีเฟรช">
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
        </button>
      </div>
      <div className="card-body stack" style={{ gap: 14 }}>
        <p className="small muted" style={{ margin: 0 }}>
          ส่งลิงก์นี้ให้เพื่อน เมื่อเพื่อนสมัครผ่านลิงก์และ<strong>รันบอทครบ {data?.runHours || 48} ชม.</strong> คุณได้ชั่วโมงเพิ่ม {data?.rewardHours || 48} ชม. ต่อคน (เพื่อนรับฟรี 48 ชม. ตอนสมัครตามปกติ)
        </p>
        {error && <div className="small" style={{ color: 'var(--red)' }}>{error}</div>}
        <div className="ref-link">
          <code className="mono">{link || 'กำลังโหลด…'}</code>
          <div className="row" style={{ gap: 6 }}>
            {link && <CopyButton text={link} label="คัดลอกลิงก์" className="btn btn-primary btn-sm" />}
            {link && (
              <a className="btn btn-secondary btn-sm" href={`https://line.me/R/share?text=${encodeURIComponent(share)}`} target="_blank" rel="noreferrer">
                <Share2 size={14} /> แชร์ LINE
              </a>
            )}
          </div>
        </div>
        <div className="ref-stats">
          <div>
            <span className="ref-num">{data ? data.invited : '—'}</span>
            <span className="tiny muted">เพื่อนที่สมัคร</span>
          </div>
          <div>
            <span className="ref-num" style={{ color: 'var(--green)' }}>{data ? data.rewarded : '—'}</span>
            <span className="tiny muted">ได้รับชั่วโมงแล้ว · รอ {data ? data.pending : '—'}</span>
          </div>
          <div>
            <span className="ref-num" style={{ color: 'var(--gold)' }}>{data ? `+${data.hours}` : '—'}</span>
            <span className="tiny muted">ชั่วโมงที่ได้ทั้งหมด</span>
          </div>
        </div>
        <div>
          <div className="row" style={{ gap: 6, marginBottom: 6 }}>
            <Users size={15} className="text-gold" />
            <strong className="small">เพื่อนที่สมัครผ่านลิงก์ของคุณ</strong>
          </div>
          {data && !friends.length && <div className="small muted">ยังไม่มีเพื่อนสมัคร — เริ่มแชร์ลิงก์ได้เลย</div>}
          {shown.length > 0 && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>เพื่อน</th><th>สมัครเมื่อ</th><th className="right">ผล</th></tr>
                </thead>
                <tbody>
                  {shown.map((f, i) => (
                    <tr key={`${f.email}${i}`}>
                      <td>
                        <div>{f.name}</div>
                        <div className="tiny muted mono">{f.email}</div>
                      </td>
                      <td className="small muted nowrap">{f.at ? formatThaiDateTime(f.at) : '—'}</td>
                      <td className="right small" style={{ color: statusOf(f, data.runHours).color, minWidth: 140 }}>
                        {statusOf(f, data.runHours).text}
                        {statusOf(f, data.runHours).pct !== undefined && (
                          <div className="ref-bar"><i style={{ width: `${statusOf(f, data.runHours).pct}%` }} /></div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {friends.length > PER_PAGE && <Pager page={p} totalPages={pages} total={friends.length} onChange={setPage} />}
        </div>
        <p className="tiny faint" style={{ margin: 0 }}>
          เงื่อนไข: เพื่อนต้องสมัครใหม่ผ่านลิงก์ (จำไว้ 30 วัน) · ยืนยันอีเมล · รันบอทจริงครบ {data?.runHours || 48} ชม. · ใช้บัญชี MT5 คนละบัญชีกับคุณ · ไม่ใช้อีเมลชั่วคราว · ได้สูงสุด {data?.monthlyCap || 20} คนต่อ 30 วัน · ห้ามสร้างบัญชีปลอม แอดมินยกเลิกชั่วโมงที่ได้จากการโกงได้
        </p>
      </div>
    </div>
  );
}
