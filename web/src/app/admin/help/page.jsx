'use client';

// ประวัติการถามผู้ช่วย (FAB) — ใช้หาคำถามที่ยังตอบไม่ได้ / คำตอบที่ไม่ช่วย แล้วเพิ่มใน lib/helpKb.js หรือปรับโปรแกรม/เว็บ
import { useCallback, useEffect, useState } from 'react';
import { HelpCircle, MessageSquare, RefreshCw, ThumbsDown, ThumbsUp } from 'lucide-react';
import AdminShell from '../../../components/admin/AdminShell';
import { Alert, Pager, StatCard } from '../../../components/ui';
import { useAuth } from '../../../context/AuthContext';
import { formatThaiDateTime } from '../../../lib/format';

const n = (v) => Number(v || 0).toLocaleString();
const PER_PAGE = 10;
const pageOf = (list, page) => {
  const pages = Math.max(1, Math.ceil(list.length / PER_PAGE));
  const p = Math.min(Math.max(1, page), pages);
  return { items: list.slice((p - 1) * PER_PAGE, p * PER_PAGE), page: p, pages, total: list.length };
};
const TABS = [
  ['unanswered', 'ยังตอบไม่ได้'],
  ['disliked', 'คำตอบไม่ช่วย 👎'],
  ['top', 'คำถามยอดนิยม'],
  ['topics', 'หัวข้อที่ถูกถาม'],
  ['recent', 'ล่าสุด'],
];
const DAYS = [7, 30, 90, 365];

export default function AdminHelpPage() {
  const { apiFetch, isAdmin } = useAuth();
  const [days, setDays] = useState(30);
  const [tab, setTab] = useState('unanswered');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await apiFetch(`/api/admin/help?days=${days}`));
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiFetch, days]);
  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin, load]);
  useEffect(() => setPage(1), [tab, days]);

  const s = data?.summary;
  const busy = !data && !error;
  const list = pageOf(data?.[tab] || [], page);
  const pct = (a, b) => (b ? `${Math.round((a / b) * 100)}%` : '—');

  return (
    <AdminShell
      title="ผู้ช่วยตอบคำถาม (FAB)"
      description="คำถามที่ผู้ใช้ถามผู้ช่วยบนเว็บ — ใช้หาคำถามที่ยังตอบไม่ได้ แล้วเพิ่มคำตอบใน web/src/lib/helpKb.js หรือปรับปรุงโปรแกรม/เว็บ"
      actions={
        <div className="row" style={{ gap: 6 }}>
          {DAYS.map((d) => (
            <button key={d} className={`btn btn-sm ${d === days ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setDays(d)}>
              {d === 365 ? '1 ปี' : `${d} วัน`}
            </button>
          ))}
          <button className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> รีเฟรช
          </button>
        </div>
      }
    >
      {error && (
        <div style={{ marginBottom: 16 }}>
          <Alert type="error">{error}</Alert>
        </div>
      )}
      <div className="grid grid-4">
        <StatCard icon={MessageSquare} label="คำถามทั้งหมด" value={s ? n(s.asks) : '—'} tone="gold" sub={s ? `${n(s.sessions)} แชท` : undefined} loading={busy} />
        <StatCard icon={HelpCircle} label="ตอบได้" value={s ? pct(s.found, s.asks) : '—'} tone="green" sub={s ? `ตอบไม่ได้ ${n(s.asks - s.found)} คำถาม` : undefined} loading={busy} />
        <StatCard icon={ThumbsUp} label="ช่วยได้" value={s ? n(s.up) : '—'} tone="sky" loading={busy} />
        <StatCard icon={ThumbsDown} label="ไม่ช่วย" value={s ? n(s.down) : '—'} tone="red" loading={busy} />
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header">
          <div className="row wrap" style={{ gap: 6 }}>
            {TABS.map(([k, label]) => (
              <button key={k} className={`btn btn-sm ${k === tab ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTab(k)}>
                {label}
                {data && k !== 'recent' ? ` (${n((data[k] || []).length)})` : ''}
              </button>
            ))}
          </div>
        </div>
        <div className="card-body">
          <div className="table-wrap">
            <table className="table">
              <thead>
                {tab === 'topics' ? (
                  <tr><th>หัวข้อคำตอบ</th><th className="right">ถูกตอบ</th><th className="right">👍</th><th className="right">👎</th></tr>
                ) : tab === 'top' || tab === 'unanswered' ? (
                  <tr><th>คำถาม</th><th className="right">ครั้ง</th><th>ตอบด้วย</th><th>ล่าสุด</th></tr>
                ) : tab === 'disliked' ? (
                  <tr><th>คำถาม</th><th>คำตอบที่ได้</th><th>ผู้ใช้</th><th>เวลา</th></tr>
                ) : (
                  <tr><th>คำถาม</th><th>ผลลัพธ์</th><th>หน้า</th><th>ผู้ใช้</th><th>เวลา</th></tr>
                )}
              </thead>
              <tbody>
                {list.items.map((r, i) =>
                  tab === 'topics' ? (
                    <tr key={r.top || i}><td>{r.t || r.top}</td><td className="right mono">{n(r.n)}</td><td className="right mono">{n(r.up)}</td><td className="right mono" style={{ color: r.down ? 'var(--red)' : undefined }}>{n(r.down)}</td></tr>
                  ) : tab === 'top' || tab === 'unanswered' ? (
                    <tr key={r.q + i}><td>{r.q}</td><td className="right mono">{n(r.n)}</td><td className="small muted">{r.ok ? r.t : <span style={{ color: 'var(--red)' }}>ไม่พบคำตอบ</span>}</td><td className="small muted nowrap">{formatThaiDateTime(r.last)}</td></tr>
                  ) : tab === 'disliked' ? (
                    <tr key={r.at + i}><td>{r.q}</td><td className="small muted">{r.top}</td><td className="small muted">{r.email || 'ไม่ได้ล็อกอิน'}</td><td className="small muted nowrap">{formatThaiDateTime(r.at)}</td></tr>
                  ) : (
                    <tr key={r.at + i}>
                      <td>{r.q}</td>
                      <td className="small" style={{ color: r.ok ? 'var(--green)' : 'var(--red)' }}>{r.ok ? `${r.t} (${r.s})` : `ไม่พบ (${r.s})`}</td>
                      <td className="small muted mono">{r.page}</td>
                      <td className="small muted">{r.email || 'ไม่ได้ล็อกอิน'}</td>
                      <td className="small muted nowrap">{formatThaiDateTime(r.at)}</td>
                    </tr>
                  ),
                )}
                {data && !list.items.length && (
                  <tr><td colSpan={5} className="muted center">ยังไม่มีข้อมูลในช่วงนี้</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {data && <Pager page={list.page} totalPages={list.pages} total={list.total} onChange={setPage} />}
        </div>
      </div>
    </AdminShell>
  );
}
