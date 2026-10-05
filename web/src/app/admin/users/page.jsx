'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { RefreshCw, Search, UserPlus, Users } from 'lucide-react';
import AdminShell from '../../../components/admin/AdminShell';
import { Alert, EmptyState, Modal, Pager, Spinner } from '../../../components/ui';
import { useAuth } from '../../../context/AuthContext';
import { formatHHMM, formatUsd, timeAgo } from '../../../lib/format';
import { PLAN_SHORT } from '../../../lib/adminLabels';

const FILTERS = [
  ['all', 'ทั้งหมด'],
  ['low', 'เวลาใกล้หมด (≤5 ชม.)'],
  ['disabled', 'ถูกระงับ'],
  ['admin', 'แอดมิน'],
];

export default function AdminUsersPage() {
  const { apiFetch, isAdmin } = useAuth();
  const router = useRouter();
  const [q, setQ] = useState('');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), pageSize: '20', filter, q: query });
      setData(await apiFetch(`/api/admin/users?${params}`));
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiFetch, page, filter, query]);

  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin, load]);

  const search = (e) => {
    e.preventDefault();
    setPage(1);
    setQuery(q.trim());
  };

  return (
    <AdminShell
      title="จัดการผู้ใช้"
      description="ค้นหา เพิ่ม แก้ไขชั่วโมง ระงับ หรือลบบัญชีผู้ใช้ทั่วไป และดูภาพรวมการใช้งานของแต่ละคน"
      actions={
        <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
          <UserPlus size={15} /> เพิ่มผู้ใช้
        </button>
      }
    >
      <div className="toolbar">
        <form onSubmit={search} className="row" style={{ flex: 1, minWidth: 260 }}>
          <span className="input-icon" style={{ flex: 1, maxWidth: 360 }}>
            <Search size={16} />
            <input className="input" style={{ height: 38 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="ค้นหาด้วยอีเมล" />
          </span>
          <button className="btn btn-secondary btn-sm">ค้นหา</button>
        </form>
        <div className="segmented" style={{ minWidth: 420 }}>
          {FILTERS.map(([v, label]) => (
            <button
              key={v}
              className={filter === v ? 'is-active' : ''}
              onClick={() => {
                setFilter(v);
                setPage(1);
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <button className="btn btn-ghost btn-icon" onClick={load} title="รีเฟรช" aria-label="รีเฟรช">
          <RefreshCw size={15} className={loading ? 'spin' : ''} />
        </button>
      </div>

      {error && <Alert type="error">{error}</Alert>}

      <div className="card">
        {!data ? (
          <div className="card-body stack">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="skeleton" style={{ height: 28 }} />
            ))}
          </div>
        ) : data.users.length === 0 ? (
          <EmptyState icon={Users} title="ไม่พบผู้ใช้">
            ลองเปลี่ยนคำค้นหาหรือตัวกรอง
          </EmptyState>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>ผู้ใช้</th>
                  <th>บอท</th>
                  <th className="num">ชั่วโมงคงเหลือ</th>
                  <th className="num">เปิดไม้</th>
                  <th className="num">TP</th>
                  <th className="num">SL</th>
                  <th className="num">บอทปิด</th>
                  <th className="num">ปิดเอง</th>
                  <th className="num">กำไรสุทธิ</th>
                  <th>แผนที่ใช้มากสุด</th>
                </tr>
              </thead>
              <tbody>
                {data.users.map((u) => (
                  <tr key={u.id} className="clickable-row" onClick={() => router.push(`/admin/users/${u.id}`)}>
                    <td>
                      <div className="row" style={{ gap: 6 }}>
                        <strong>{u.displayName}</strong>
                        {u.isAdmin && <span className="badge badge-gold">Admin</span>}
                        {u.disabled && <span className="badge badge-red">ระงับ</span>}
                        {u.loginLock?.locked && <span className="badge badge-red">🔒 ถูกล็อก</span>}
                      </div>
                      <div className="tiny faint">{u.email}</div>
                    </td>
                    <td>
                      {u.bot?.online ? (
                        <span className="badge badge-green">
                          <span className="dot dot-live" /> {u.bot.paused ? 'พัก' : 'ออนไลน์'}
                        </span>
                      ) : (
                        <span className="tiny faint">{u.bot?.lastHeartbeat ? timeAgo(u.bot.lastHeartbeat) : 'ยังไม่เคยเชื่อมต่อ'}</span>
                      )}
                    </td>
                    <td className={`num ${u.hoursRemaining <= 5 ? 'text-red' : 'text-gold'}`} style={{ fontWeight: 600 }}>
                      {formatHHMM(u.hoursRemaining)}
                    </td>
                    <td className="num">{u.trades.opens}</td>
                    <td className="num text-green">{u.trades.tp}</td>
                    <td className="num text-red">{u.trades.sl}</td>
                    <td className="num" style={{ color: 'var(--orange)' }}>
                      {u.trades.botClose}
                    </td>
                    <td className="num text-sky">{u.trades.manualClose}</td>
                    <td className={`num ${u.trades.netProfit > 0 ? 'text-green' : u.trades.netProfit < 0 ? 'text-red' : 'faint'}`}>{formatUsd(u.trades.netProfit, { sign: true })}</td>
                    <td>
                      <div className="row wrap" style={{ gap: 4 }}>
                        {u.plans.slice(0, 2).map((p) => (
                          <span key={p.name} className="badge badge-muted">
                            {PLAN_SHORT[p.name] || p.name} · {p.trades}
                          </span>
                        ))}
                        {u.plans.length === 0 && <span className="tiny faint">—</span>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && <Pager page={data.page} totalPages={data.totalPages} total={data.total} onChange={setPage} loading={loading} />}
      </div>

      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onCreated={(u) => {
            setShowCreate(false);
            router.push(`/admin/users/${u.id}`);
          }}
        />
      )}
    </AdminShell>
  );
}

function CreateUserModal({ onClose, onCreated }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState({ email: '', displayName: '', password: '', hours: 48 });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const res = await apiFetch('/api/admin/users', { method: 'POST', body: JSON.stringify({ ...form, hours: Number(form.hours) }) });
      onCreated(res.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="เพิ่มผู้ใช้ใหม่" onClose={onClose}>
      <form className="stack" style={{ gap: 12 }} onSubmit={submit}>
        {error && <Alert type="error">{error}</Alert>}
        <label className="field">
          <span className="label">อีเมล</span>
          <input className="input" type="email" value={form.email} onChange={set('email')} required />
        </label>
        <label className="field">
          <span className="label">ชื่อที่แสดง</span>
          <input className="input" value={form.displayName} onChange={set('displayName')} maxLength={40} />
        </label>
        <div className="grid grid-2" style={{ gap: 12 }}>
          <label className="field">
            <span className="label">รหัสผ่านเริ่มต้น</span>
            <input className="input" type="text" value={form.password} onChange={set('password')} minLength={6} required />
          </label>
          <label className="field">
            <span className="label">ชั่วโมงเริ่มต้น</span>
            <input className="input" type="number" min="0" max="9999" step="1" value={form.hours} onChange={set('hours')} />
          </label>
        </div>
        <p className="tiny faint">แจ้งรหัสผ่านเริ่มต้นให้ผู้ใช้ และแนะนำให้เปลี่ยนหลังเข้าสู่ระบบครั้งแรก</p>
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy && <Spinner />} สร้างบัญชี
        </button>
      </form>
    </Modal>
  );
}
