'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Ban, Clock, KeyRound, LockOpen, Pencil, ScrollText, Trash2, UserCheck } from 'lucide-react';
import AdminShell from '../../../../components/admin/AdminShell';
import { Alert, EmptyState, Modal, Pager, Spinner } from '../../../../components/ui';
import { useAuth } from '../../../../context/AuthContext';
import { formatHHMM, formatPrice, formatThaiDateTime, formatUsd, timeAgo } from '../../../../lib/format';
import { ACTIVITY_LABELS, TRADE_ACTION_LABELS } from '../../../../lib/adminLabels';

const PLAN_ROWS = [
  'Plan 1: SMC-LiquidityHunt',
  'Plan 2: SR-SwingBounce',
  'Plan 3: BB-H1-Reversion',
  'Plan 4: MA-Cross-Trend',
  'Plan 5: MA-Cross-H1-Trend',
];

export default function AdminUserDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { apiFetch, isAdmin } = useAuth();
  const [user, setUser] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(null);
  const [modal, setModal] = useState(null); // 'hours' | 'name' | 'password' | 'delete'

  const load = useCallback(async () => {
    try {
      const res = await apiFetch(`/api/admin/users/${id}`);
      setUser(res.user);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }, [apiFetch, id]);

  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin, load]);

  const patch = async (body, okMessage) => {
    const res = await apiFetch(`/api/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
    setUser(res.user);
    setNotice({ type: 'success', message: okMessage });
    setModal(null);
  };

  const locked = user?.isAdmin;
  const [unlocking, setUnlocking] = useState(false);
  const unlockLogin = async () => {
    setUnlocking(true);
    try {
      const res = await apiFetch(`/api/admin/users/${id}/unlock`, { method: 'POST' });
      setUser(res.user);
      setNotice({ type: 'success', message: res.message });
    } catch (err) {
      setNotice({ type: 'error', message: err.message });
    } finally {
      setUnlocking(false);
    }
  };

  return (
    <AdminShell
      title={user ? user.displayName : 'รายละเอียดผู้ใช้'}
      description={user?.email}
      actions={
        <Link href="/admin/users" className="btn btn-ghost btn-sm">
          <ArrowLeft size={15} /> กลับรายชื่อ
        </Link>
      }
    >
      {error && <Alert type="error">{error}</Alert>}
      {notice && (
        <div style={{ marginBottom: 14 }}>
          <Alert type={notice.type}>{notice.message}</Alert>
        </div>
      )}
      {user?.loginLock?.locked && (
        <div style={{ marginBottom: 14 }}>
          <Alert type="error">
            <strong>บัญชีถูกล็อกการเข้าสู่ระบบ</strong> — ใส่รหัสผิด {user.loginLock.failed} ครั้งใน 15 นาที · ปลดล็อกเองอัตโนมัติ{' '}
            {formatThaiDateTime(user.loginLock.unlockAt)}
            <button className="btn btn-primary btn-sm" style={{ marginLeft: 10 }} onClick={unlockLogin} disabled={unlocking}>
              {unlocking ? <Spinner /> : <LockOpen size={14} />} ปลดล็อกตอนนี้
            </button>
          </Alert>
        </div>
      )}
      {locked && (
        <div style={{ marginBottom: 14 }}>
          <Alert type="info">บัญชีผู้ดูแลระบบ — ดูข้อมูลได้อย่างเดียว ไม่สามารถแก้ไขหรือลบจากหน้านี้</Alert>
        </div>
      )}

      {!user ? (
        !error && <div className="skeleton" style={{ height: 220 }} />
      ) : (
        <>
          <div className="grid grid-main-side" style={{ alignItems: 'start' }}>
            <div className="card card-pad">
              <div className="row wrap" style={{ gap: 8, marginBottom: 14 }}>
                {user.isAdmin && <span className="badge badge-gold">Admin</span>}
                {user.disabled ? <span className="badge badge-red">ถูกระงับ</span> : <span className="badge badge-green">ใช้งานได้</span>}
                {user.loginLock?.locked && <span className="badge badge-red">🔒 ล็อกการเข้าสู่ระบบ</span>}
                {!user.loginLock?.locked && user.loginLock?.failed > 0 && (
                  <span className="badge badge-gold">รหัสผิด {user.loginLock.failed}/5 ครั้ง</span>
                )}
                {user.bot?.online ? (
                  <span className="badge badge-green">
                    <span className="dot dot-live" /> บอท{user.bot.paused ? 'พัก' : 'ออนไลน์'}
                  </span>
                ) : (
                  <span className="badge badge-muted">บอทออฟไลน์{user.bot?.lastHeartbeat ? ` · ${timeAgo(user.bot.lastHeartbeat)}` : ''}</span>
                )}
              </div>
              <div className="grid grid-3" style={{ gap: 12 }}>
                <Info label="ชั่วโมงคงเหลือ" value={`${formatHHMM(user.hoursRemaining)} ชม.`} color={user.hoursRemaining <= 5 ? 'var(--red)' : 'var(--gold)'} />
                <Info label="Balance (ล่าสุด)" value={user.bot ? formatUsd(user.bot.balance) : '—'} />
                <Info label="ออเดอร์เปิดอยู่" value={user.bot ? user.bot.openPositions : '—'} />
              </div>
              <div className="small muted" style={{ marginTop: 14 }}>
                สมัครเมื่อ {user.registeredAt ? formatThaiDateTime(user.registeredAt) : '—'} · ID <span className="mono">{user.id}</span>
              </div>
            </div>

            <div className="card card-pad">
              <div style={{ fontWeight: 700, marginBottom: 12 }}>จัดการบัญชี</div>
              <div className="stack" style={{ gap: 8 }}>
                <button
                  className="btn btn-secondary btn-block"
                  disabled={unlocking || !(user.loginLock?.locked || user.loginLock?.failed > 0)}
                  onClick={unlockLogin}
                  title="ล้างตัวนับรหัสผิด ให้ผู้ใช้เข้าสู่ระบบได้ทันที"
                >
                  {unlocking ? <Spinner /> : <LockOpen size={15} />} ปลดล็อกการเข้าสู่ระบบ
                </button>
                <button className="btn btn-primary btn-block" disabled={locked} onClick={() => setModal('hours')}>
                  <Clock size={15} /> เพิ่ม / ลด / ตั้งชั่วโมง
                </button>
                <button className="btn btn-secondary btn-block" disabled={locked} onClick={() => setModal('name')}>
                  <Pencil size={15} /> แก้ไขชื่อที่แสดง
                </button>
                <button className="btn btn-secondary btn-block" disabled={locked} onClick={() => setModal('password')}>
                  <KeyRound size={15} /> รีเซ็ตรหัสผ่าน
                </button>
                <button
                  className={`btn btn-block ${user.disabled ? 'btn-secondary' : 'btn-danger'}`}
                  disabled={locked}
                  onClick={() => patch({ disabled: !user.disabled }, user.disabled ? 'เปิดใช้งานบัญชีแล้ว' : 'ระงับบัญชีแล้ว — ผู้ใช้จะถูกออกจากระบบและเริ่มบอทไม่ได้')}
                >
                  {user.disabled ? <UserCheck size={15} /> : <Ban size={15} />} {user.disabled ? 'เปิดใช้งานบัญชี' : 'ระงับบัญชี'}
                </button>
                <button className="btn btn-ghost btn-block text-red" disabled={locked} onClick={() => setModal('delete')}>
                  <Trash2 size={15} /> ลบผู้ใช้
                </button>
              </div>
            </div>
          </div>

          <div className="grid grid-4 section">
            <Info card label="เปิดไม้" value={user.trades.opens} />
            <Info card label="ชน TP / ชน SL" value={`${user.trades.tp} / ${user.trades.sl}`} color="var(--green)" />
            <Info card label="บอทปิด / ปิดเอง" value={`${user.trades.botClose} / ${user.trades.manualClose}`} color="var(--orange)" />
            <Info card label="กำไรสุทธิ" value={formatUsd(user.trades.netProfit, { sign: true })} color={user.trades.netProfit >= 0 ? 'var(--green)' : 'var(--red)'} />
          </div>

          <div className="card section">
            <div className="card-header">
              <h3>การใช้แผนการเทรด</h3>
            </div>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>แผน</th>
                    <th className="num">ออเดอร์</th>
                    <th className="num">ชนะ</th>
                    <th className="num">แพ้</th>
                    <th style={{ minWidth: 140 }}>สัดส่วนการใช้</th>
                    <th className="num">กำไรสุทธิ</th>
                  </tr>
                </thead>
                <tbody>
                  {PLAN_ROWS.map((name) => {
                    const p = user.plans.find((x) => x.name === name) || { trades: 0, win: 0, loss: 0, profit: 0 };
                    const totalTrades = user.plans.reduce((s, x) => s + x.trades, 0);
                    const share = totalTrades ? (p.trades / totalTrades) * 100 : 0;
                    return (
                      <tr key={name}>
                        <td style={{ fontWeight: 600 }}>{name}</td>
                        <td className="num">{p.trades}</td>
                        <td className="num text-green">{p.win}</td>
                        <td className="num text-red">{p.loss}</td>
                        <td>
                          <div className="row" style={{ gap: 8 }}>
                            <div className="mini-bar" style={{ flex: 1 }}>
                              <span style={{ width: `${share}%`, background: 'var(--gold)' }} />
                            </div>
                            <span className="mono tiny" style={{ width: 40, textAlign: 'right' }}>
                              {share.toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td className={`num ${p.profit > 0 ? 'text-green' : p.profit < 0 ? 'text-red' : 'faint'}`}>{formatUsd(p.profit, { sign: true })}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <UserLogs userId={id} />
        </>
      )}

      {modal === 'hours' && user && <HoursModal user={user} onClose={() => setModal(null)} onSave={patch} />}
      {modal === 'name' && user && <NameModal user={user} onClose={() => setModal(null)} onSave={patch} />}
      {modal === 'password' && user && <PasswordModal onClose={() => setModal(null)} onSave={patch} />}
      {modal === 'delete' && user && (
        <DeleteModal
          user={user}
          onClose={() => setModal(null)}
          onDeleted={() => router.push('/admin/users')}
        />
      )}
    </AdminShell>
  );
}

function Info({ label, value, color, card }) {
  const body = (
    <>
      <div className="tiny faint">{label}</div>
      <div className="mono" style={{ fontSize: '1.3rem', fontWeight: 700, color: color || 'var(--text)' }}>
        {value}
      </div>
    </>
  );
  return card ? <div className="card stat">{body}</div> : <div>{body}</div>;
}

// ---------------------------------------------------------------------------
// Log ของผู้ใช้
// ---------------------------------------------------------------------------
const LOG_TABS = [
  ['activity', 'กิจกรรมบัญชี'],
  ['trades', 'การเทรด'],
  ['signals', 'สัญญาณ'],
  ['risk', 'ความเสี่ยง'],
];

function UserLogs({ userId }) {
  const { apiFetch } = useAuth();
  const [type, setType] = useState('activity');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiFetch(`/api/admin/users/${userId}/logs?type=${type}&page=${page}&pageSize=15`)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setData({ items: [], total: 0, totalPages: 1, page: 1 }))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [apiFetch, userId, type, page]);

  const items = data?.items || [];

  return (
    <div className="card section">
      <div className="card-header wrap" style={{ gap: 10 }}>
        <h3>
          <ScrollText size={17} className="text-gold" /> Log ของผู้ใช้
        </h3>
        <div className="segmented" style={{ width: 'min(100%, 460px)' }}>
          {LOG_TABS.map(([v, label]) => (
            <button
              key={v}
              className={type === v ? 'is-active' : ''}
              onClick={() => {
                setType(v);
                setPage(1);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {data?.notice && (
        <div className="card-body" style={{ paddingBottom: 0 }}>
          <Alert type="gold">{data.notice}</Alert>
        </div>
      )}
      {!data ? (
        <div className="card-body">
          <div className="skeleton" style={{ height: 120 }} />
        </div>
      ) : items.length === 0 ? (
        <EmptyState icon={ScrollText} title="ยังไม่มีรายการ" />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <tbody>
              {items.map((r) => (
                <LogRow key={`${type}-${r.id}`} type={type} r={r} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pager page={data.page} totalPages={data.totalPages} total={data.total} onChange={setPage} loading={loading} />}
    </div>
  );
}

function LogRow({ type, r }) {
  if (type === 'activity') {
    const l = ACTIVITY_LABELS[r.event] || { label: r.event, badge: 'badge-muted' };
    return (
      <tr>
        <td className="small faint">{formatThaiDateTime(r.created_at)}</td>
        <td>
          <span className={`badge ${l.badge}`}>{l.label}</span>
        </td>
        <td className="small" style={{ whiteSpace: 'normal' }}>
          {r.detail || '—'}
        </td>
        <td className="tiny faint">{r.actor ? `โดย ${r.actor}` : r.ip || ''}</td>
      </tr>
    );
  }
  if (type === 'trades') {
    const l = TRADE_ACTION_LABELS[r.action] || { label: r.action, badge: 'badge-muted' };
    const profit = Number(r.profit) || 0;
    return (
      <tr>
        <td className="small faint">{formatThaiDateTime(r.time)}</td>
        <td>
          <span className={`badge ${l.badge}`}>{l.label}</span>
        </td>
        <td className="small">{r.plan || '—'}</td>
        <td className="num">{formatPrice(r.price)}</td>
        <td className="num">{Number(r.lot) ? Number(r.lot).toFixed(2) : '—'}</td>
        <td className={`num ${profit > 0 ? 'text-green' : profit < 0 ? 'text-red' : 'faint'}`}>{r.action.startsWith('OPEN') ? '—' : formatUsd(profit, { sign: true })}</td>
        <td className="tiny faint" style={{ whiteSpace: 'normal' }}>
          {r.comment}
        </td>
      </tr>
    );
  }
  if (type === 'signals') {
    return (
      <tr>
        <td className="small faint">{formatThaiDateTime(r.time)}</td>
        <td>
          <span className={`badge ${r.signal_type === 'ENTRY_SIGNAL' ? 'badge-gold' : 'badge-muted'}`}>{r.signal_type}</span>
        </td>
        <td className="small">
          {r.plan} · <span className={r.direction === 'BUY' ? 'text-green' : r.direction === 'SELL' ? 'text-red' : ''}>{r.direction}</span>
        </td>
        <td className="num">{formatPrice(r.price)}</td>
        <td className="tiny">
          AI ↑{Number(r.ai_up).toFixed(0)}% ↓{Number(r.ai_down).toFixed(0)}%
        </td>
        <td className="tiny faint" style={{ whiteSpace: 'normal' }}>
          {r.status} · {r.detail}
        </td>
      </tr>
    );
  }
  return (
    <tr>
      <td className="small faint">{formatThaiDateTime(r.time)}</td>
      <td>
        <span className="badge badge-red">{r.event_type}</span>
      </td>
      <td className="small">{r.direction}</td>
      <td className="small" style={{ whiteSpace: 'normal' }}>
        {r.message}
      </td>
      <td className="num text-red">{Number(r.loss_amount) ? formatUsd(r.loss_amount) : ''}</td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Modals
// ---------------------------------------------------------------------------
function useSubmit(onSave) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const run = async (body, message) => {
    setBusy(true);
    setError('');
    try {
      await onSave(body, message);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return { error, busy, run };
}

function HoursModal({ user, onClose, onSave }) {
  const [mode, setMode] = useState('add');
  const [value, setValue] = useState(mode === 'add' ? 10 : user.hoursRemaining);
  const { error, busy, run } = useSubmit(onSave);
  const preview = mode === 'add' ? user.hoursRemaining + Number(value || 0) : Number(value || 0);

  return (
    <Modal title="ปรับชั่วโมงใช้งาน" onClose={onClose} width={420}>
      <div className="stack" style={{ gap: 12 }}>
        {error && <Alert type="error">{error}</Alert>}
        <div className="segmented">
          <button className={mode === 'add' ? 'is-active' : ''} onClick={() => { setMode('add'); setValue(10); }}>
            เพิ่ม / ลด
          </button>
          <button className={mode === 'set' ? 'is-active' : ''} onClick={() => { setMode('set'); setValue(user.hoursRemaining); }}>
            ตั้งค่าใหม่
          </button>
        </div>
        <label className="field">
          <span className="label">{mode === 'add' ? 'จำนวนชั่วโมง (ใส่ค่าติดลบเพื่อหัก)' : 'ชั่วโมงคงเหลือใหม่'}</span>
          <input className="input" type="number" step="0.5" value={value} onChange={(e) => setValue(e.target.value)} />
        </label>
        <div className="small muted">
          ปัจจุบัน <strong>{formatHHMM(user.hoursRemaining)}</strong> → หลังบันทึก{' '}
          <strong className={preview < 0 ? 'text-red' : 'text-gold'}>{preview < 0 ? 'ติดลบไม่ได้' : formatHHMM(preview)}</strong> ชม.
        </div>
        <button
          className="btn btn-primary btn-block"
          disabled={busy || preview < 0}
          onClick={() => run(mode === 'add' ? { addHours: Number(value) } : { hours: Number(value) }, `บันทึกชั่วโมงแล้ว: ${formatHHMM(preview)} ชม.`)}
        >
          {busy && <Spinner />} บันทึก
        </button>
      </div>
    </Modal>
  );
}

function NameModal({ user, onClose, onSave }) {
  const [name, setName] = useState(user.displayName);
  const { error, busy, run } = useSubmit(onSave);
  return (
    <Modal title="แก้ไขชื่อที่แสดง" onClose={onClose} width={420}>
      <div className="stack" style={{ gap: 12 }}>
        {error && <Alert type="error">{error}</Alert>}
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} maxLength={40} />
        <button className="btn btn-primary btn-block" disabled={busy || !name.trim()} onClick={() => run({ displayName: name }, 'บันทึกชื่อแล้ว')}>
          {busy && <Spinner />} บันทึก
        </button>
      </div>
    </Modal>
  );
}

function PasswordModal({ onClose, onSave }) {
  const [pw, setPw] = useState('');
  const { error, busy, run } = useSubmit(onSave);
  return (
    <Modal title="รีเซ็ตรหัสผ่านผู้ใช้" onClose={onClose} width={420}>
      <div className="stack" style={{ gap: 12 }}>
        {error && <Alert type="error">{error}</Alert>}
        <input className="input" type="text" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="รหัสผ่านใหม่ (อย่างน้อย 6 ตัว)" />
        <p className="tiny faint">แจ้งรหัสใหม่ให้ผู้ใช้ทางช่องทางที่ปลอดภัย และแนะนำให้เปลี่ยนหลังเข้าสู่ระบบ</p>
        <button className="btn btn-primary btn-block" disabled={busy || pw.length < 6} onClick={() => run({ newPassword: pw }, 'รีเซ็ตรหัสผ่านแล้ว')}>
          {busy && <Spinner />} ตั้งรหัสผ่านใหม่
        </button>
      </div>
    </Modal>
  );
}

function DeleteModal({ user, onClose, onDeleted }) {
  const { apiFetch } = useAuth();
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const del = async () => {
    setBusy(true);
    setError('');
    try {
      await apiFetch(`/api/admin/users/${user.id}`, { method: 'DELETE', body: JSON.stringify({ confirmEmail: confirm }) });
      onDeleted();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };
  return (
    <Modal title="ลบผู้ใช้" onClose={onClose} width={440}>
      <div className="stack" style={{ gap: 12 }}>
        {error && <Alert type="error">{error}</Alert>}
        <Alert type="error">
          การลบไม่สามารถย้อนกลับได้ ชั่วโมงคงเหลือ <strong>{formatHHMM(user.hoursRemaining)}</strong> ชม. จะหายไป (ประวัติการเทรด/คำสั่งซื้อยังเก็บไว้)
        </Alert>
        <label className="field">
          <span className="label">
            พิมพ์อีเมล <strong>{user.email}</strong> เพื่อยืนยัน
          </span>
          <input className="input" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </label>
        <button className="btn btn-danger btn-block" disabled={busy || confirm.trim().toLowerCase() !== user.email} onClick={del}>
          {busy && <Spinner />} ลบผู้ใช้ถาวร
        </button>
      </div>
    </Modal>
  );
}
