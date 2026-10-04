'use client';

import { useCallback, useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, History, RefreshCw } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { EmptyState } from './ui';
import { formatPrice, formatThaiDateTime, formatUsd } from '../lib/format';

const PAGE_SIZE = 5;

function describe(action, profit) {
  switch (action) {
    case 'OPEN_BUY':
      return { label: 'เปิด BUY', badge: 'badge-green' };
    case 'OPEN_SELL':
      return { label: 'เปิด SELL', badge: 'badge-red' };
    case 'TP_HIT':
      return { label: 'ปิด · ชน TP', badge: 'badge-green' };
    case 'SL_HIT':
      return { label: 'ปิด · ชน SL', badge: 'badge-red' };
    case 'CLOSE':
      return { label: 'ปิดโดยบอท', badge: profit > 0 ? 'badge-green' : profit < 0 ? 'badge-red' : 'badge-muted' };
    default:
      return { label: action, badge: 'badge-muted' };
  }
}

/** ประวัติการเข้าไม้/ปิดไม้ แบ่งหน้าละ 5 รายการ */
export default function TradeHistory() {
  const { apiFetch } = useAuth();
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(
    async (p) => {
      setLoading(true);
      try {
        const res = await apiFetch(`/api/user/trades?page=${p}&pageSize=${PAGE_SIZE}`);
        setData(res);
        setError('');
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [apiFetch]
  );

  useEffect(() => {
    load(page);
    const id = setInterval(() => document.visibilityState === 'visible' && load(page), 30000);
    return () => clearInterval(id);
  }, [load, page]);

  const totalPages = data?.totalPages || 1;
  const items = data?.items || [];

  return (
    <div className="card">
      <div className="card-header">
        <h3>
          <History size={17} className="text-gold" /> ประวัติการเข้าไม้ / ปิดไม้
        </h3>
        <div className="row">
          {data && <span className="badge badge-muted">{data.total} รายการ</span>}
          <button className="btn btn-ghost btn-icon" onClick={() => load(page)} title="รีเฟรช" aria-label="รีเฟรช">
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
          </button>
        </div>
      </div>

      {error && !data ? (
        <EmptyState icon={History} title="โหลดประวัติไม่สำเร็จ">
          {error}
        </EmptyState>
      ) : !data ? (
        <div className="card-body stack">
          {Array.from({ length: PAGE_SIZE }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 22 }} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState icon={History} title="ยังไม่มีประวัติการเทรด">
          เมื่อบอทเปิดหรือปิดออเดอร์ รายการจะแสดงที่นี่อัตโนมัติ
        </EmptyState>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>เวลา</th>
                <th>เหตุการณ์</th>
                <th>แผน</th>
                <th className="num">ราคา</th>
                <th className="num">Lot</th>
                <th className="num">SL / TP</th>
                <th className="num">กำไร/ขาดทุน</th>
              </tr>
            </thead>
            <tbody>
              {items.map((t) => {
                const d = describe(t.action, t.profit);
                const isOpen = t.action.startsWith('OPEN_');
                return (
                  <tr key={t.id}>
                    <td className="small faint">{formatThaiDateTime(t.time)}</td>
                    <td>
                      <span className={`badge ${d.badge}`}>{d.label}</span>
                    </td>
                    <td className="small">{t.plan || '—'}</td>
                    <td className="num">{formatPrice(t.price)}</td>
                    <td className="num">{t.lot ? t.lot.toFixed(2) : '—'}</td>
                    <td className="num faint small">{isOpen ? `${formatPrice(t.sl)} / ${t.tp > 0 ? formatPrice(t.tp) : 'รันเทรนด์'}` : '—'}</td>
                    <td className={`num ${t.profit > 0 ? 'text-green' : t.profit < 0 ? 'text-red' : 'faint'}`} style={{ fontWeight: 600 }}>
                      {isOpen ? '—' : formatUsd(t.profit, { sign: true })}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {data && data.total > 0 && (
        <div className="pager">
          <button className="btn btn-secondary btn-sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1 || loading}>
            <ChevronLeft size={15} /> ใหม่กว่า
          </button>
          <span className="small muted">
            หน้า <strong className="mono">{page}</strong> / <span className="mono">{totalPages}</span>
          </span>
          <button className="btn btn-secondary btn-sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages || loading}>
            เก่ากว่า <ChevronRight size={15} />
          </button>
        </div>
      )}
    </div>
  );
}
