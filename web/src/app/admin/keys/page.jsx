'use client';

import { useCallback, useEffect, useState } from 'react';
import { KeyRound, Search, Sparkles } from 'lucide-react';
import AdminShell from '../../../components/admin/AdminShell';
import { Alert, CopyButton, EmptyState, Modal, Pager, Spinner } from '../../../components/ui';
import { useAuth } from '../../../context/AuthContext';
import { formatThaiDateTime, formatThb } from '../../../lib/format';

const FILTERS = [
  ['unused', 'ยังไม่ใช้งาน'],
  ['redeemed', 'เติมแล้ว'],
  ['promo', 'แอดมินสร้าง'],
  ['pending', 'ยังไม่ชำระ'],
  ['paid', 'ชำระแล้ว'],
];

export default function AdminKeysPage() {
  const { apiFetch, isAdmin } = useAuth();
  const [filter, setFilter] = useState('unused');
  const [q, setQ] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPromo, setShowPromo] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ filter, page: String(page), pageSize: '20', q: query });
      setData(await apiFetch(`/api/admin/keys?${params}`));
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiFetch, filter, page, query]);

  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin, load]);

  const isOrders = filter === 'pending' || filter === 'paid';
  const items = data?.items || [];

  return (
    <AdminShell
      title="คีย์ & คำสั่งซื้อ"
      description="Product Key จากการซื้อ, Promo Key ที่แอดมินสร้าง และคำสั่งซื้อทั้งหมด"
      actions={
        <button className="btn btn-primary btn-sm" onClick={() => setShowPromo(true)}>
          <Sparkles size={15} /> สร้าง Promo Key
        </button>
      }
    >
      <div className="toolbar">
        <div className="segmented" style={{ minWidth: 560 }}>
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
              {data?.counts && <span className="mono faint"> {data.counts[v]}</span>}
            </button>
          ))}
        </div>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setQuery(q.trim());
          }}
        >
          <span className="input-icon">
            <Search size={16} />
            <input className="input" style={{ height: 38 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder={isOrders ? 'เลขคำสั่งซื้อ / คีย์' : 'ค้นหาคีย์'} />
          </span>
        </form>
      </div>

      {error && <Alert type="error">{error}</Alert>}

      <div className="card">
        {!data ? (
          <div className="card-body">
            <div className="skeleton" style={{ height: 160 }} />
          </div>
        ) : items.length === 0 ? (
          <EmptyState icon={KeyRound} title="ไม่มีรายการในหมวดนี้" />
        ) : isOrders ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>คำสั่งซื้อ</th>
                  <th>ผู้ซื้อ</th>
                  <th className="num">ยอด</th>
                  <th className="num">ชั่วโมง</th>
                  <th>สถานะ</th>
                  <th>Product Key</th>
                  <th>เวลา</th>
                </tr>
              </thead>
              <tbody>
                {items.map((o) => (
                  <tr key={o.orderId}>
                    <td className="mono tiny">{o.orderId}</td>
                    <td className="small">{o.owner || '—'}</td>
                    <td className="num text-gold">{formatThb(o.amount)}</td>
                    <td className="num">{o.hours}</td>
                    <td>
                      <span className={`badge ${o.status === 'PAID' ? 'badge-green' : o.status === 'PROCESSING' ? 'badge-sky' : 'badge-gold'}`}>
                        {o.status === 'PAID' ? 'ชำระแล้ว' : o.status === 'PROCESSING' ? 'กำลังออกคีย์' : 'รอชำระ'}
                      </span>
                    </td>
                    <td className="mono tiny">{o.keyCode || '—'}</td>
                    <td className="tiny faint">
                      {formatThaiDateTime(o.createdAt)}
                      {o.paidAt && <div>ชำระ {formatThaiDateTime(o.paidAt)}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>คีย์</th>
                  <th>ประเภท</th>
                  <th className="num">ชั่วโมง</th>
                  <th>สถานะ</th>
                  <th>ผู้ซื้อ / ผู้สร้าง</th>
                  <th>ผู้เติม</th>
                  <th>เวลา</th>
                </tr>
              </thead>
              <tbody>
                {items.map((k) => (
                  <tr key={`${k.source}-${k.keyCode}`}>
                    <td>
                      <div className="row" style={{ gap: 6 }}>
                        <span className="key-code tiny">{k.keyCode}</span>
                        <CopyButton text={k.keyCode} label="" className="btn btn-ghost btn-icon" />
                      </div>
                    </td>
                    <td>{k.source === 'promo' ? <span className="badge badge-sky">Promo</span> : <span className="badge badge-gold">ซื้อ {formatThb(k.price)}</span>}</td>
                    <td className="num">{k.hours}</td>
                    <td>
                      {k.status === 'REDEEMED' ? (
                        <span className="badge badge-muted">เติมแล้ว</span>
                      ) : k.expiresAt && new Date(k.expiresAt) < new Date() ? (
                        <span className="badge badge-red">หมดอายุ</span>
                      ) : (
                        <span className="badge badge-green">ยังไม่ใช้</span>
                      )}
                    </td>
                    <td className="small">{k.owner || '—'}</td>
                    <td className="small">{k.redeemedBy || '—'}</td>
                    <td className="tiny faint">
                      {formatThaiDateTime(k.createdAt)}
                      {k.redeemedAt && <div>เติม {formatThaiDateTime(k.redeemedAt)}</div>}
                      {k.expiresAt && !k.redeemedAt && <div>หมดอายุ {formatThaiDateTime(k.expiresAt)}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && <Pager page={data.page} totalPages={data.totalPages} total={data.total} onChange={setPage} loading={loading} />}
      </div>

      {showPromo && (
        <PromoModal
          onClose={() => setShowPromo(false)}
          onCreated={() => {
            setFilter('promo');
            setPage(1);
            load();
          }}
        />
      )}
    </AdminShell>
  );
}

function PromoModal({ onClose, onCreated }) {
  const { apiFetch } = useAuth();
  const [hours, setHours] = useState(100);
  const [expiresInDays, setExpiresInDays] = useState(30);
  const [created, setCreated] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const generate = async () => {
    setBusy(true);
    setError('');
    try {
      const res = await apiFetch('/api/admin/promo-key', { method: 'POST', body: JSON.stringify({ hours: Number(hours), expiresInDays: Number(expiresInDays) }) });
      setCreated(res);
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="สร้าง Promo Key" onClose={onClose} width={440}>
      <div className="stack" style={{ gap: 12 }}>
        {error && <Alert type="error">{error}</Alert>}
        <div className="grid grid-2" style={{ gap: 12 }}>
          <label className="field">
            <span className="label">จำนวนชั่วโมง</span>
            <input className="input" type="number" min="1" max="2000" value={hours} onChange={(e) => setHours(e.target.value)} />
          </label>
          <label className="field">
            <span className="label">หมดอายุใน</span>
            <select className="input" value={expiresInDays} onChange={(e) => setExpiresInDays(e.target.value)}>
              <option value={7}>7 วัน</option>
              <option value={30}>30 วัน</option>
              <option value={90}>90 วัน</option>
              <option value={0}>ไม่หมดอายุ</option>
            </select>
          </label>
        </div>
        <button className="btn btn-primary btn-block" onClick={generate} disabled={busy}>
          {busy ? <Spinner /> : <KeyRound size={16} />} สร้างคีย์
        </button>
        {created && (
          <div className="key-row" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
            <div className="tiny faint">
              +{created.hours} ชม. {created.expiresAt ? `· หมดอายุ ${formatThaiDateTime(created.expiresAt)}` : '· ไม่หมดอายุ'}
            </div>
            <div className="key-code">{created.keyCode}</div>
            <CopyButton text={created.keyCode} label="คัดลอกคีย์" />
          </div>
        )}
      </div>
    </Modal>
  );
}
