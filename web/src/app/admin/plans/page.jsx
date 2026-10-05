'use client';

import { useCallback, useEffect, useState } from 'react';
import { ToggleRight } from 'lucide-react';
import AdminShell from '../../../components/admin/AdminShell';
import { Alert, Spinner } from '../../../components/ui';
import { useAuth } from '../../../context/AuthContext';
import { PLAN_LIST } from '../../../lib/packages';
import { formatThaiDateTime, formatUsd } from '../../../lib/format';

export default function AdminPlansPage() {
  const { apiFetch, isAdmin } = useAuth();
  const [data, setData] = useState(null);
  const [draft, setDraft] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await apiFetch('/api/admin/plans');
      setData(res);
      setDraft(res.plans);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }, [apiFetch]);

  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin, load]);

  const dirty = data && draft && PLAN_LIST.some((p) => data.plans[p.key] !== draft[p.key]);
  const enabledCount = draft ? PLAN_LIST.filter((p) => draft[p.key]).length : 0;

  const save = async () => {
    setSaving(true);
    try {
      const res = await apiFetch('/api/admin/plans', { method: 'PUT', body: JSON.stringify({ plans: draft }) });
      setData(res);
      setDraft(res.plans);
      setNotice({ type: 'success', message: 'บันทึกแล้ว — บอททุกเครื่องจะใช้ค่าใหม่ภายในประมาณ 5 นาที (ออเดอร์ที่เปิดอยู่ยังถูกบริหารตามปกติ)' });
    } catch (err) {
      setNotice({ type: 'error', message: err.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <AdminShell
      title="เปิด/ปิดแผนการเทรด"
      description="ปิดแผนที่ไม่ต้องการให้บอทของลูกค้าทุกคนเข้าไม้ใหม่ — ไม่กระทบออเดอร์ที่เปิดอยู่แล้ว (ยังปิดไม้/ล็อกกำไรตามปกติ)"
      actions={
        <button className="btn btn-primary btn-sm" onClick={save} disabled={!dirty || saving}>
          {saving && <Spinner />} บันทึกการเปลี่ยนแปลง
        </button>
      }
    >
      {error && <Alert type="error">{error}</Alert>}
      {notice && (
        <div style={{ marginBottom: 14 }}>
          <Alert type={notice.type}>{notice.message}</Alert>
        </div>
      )}
      {draft && enabledCount === 0 && (
        <div style={{ marginBottom: 14 }}>
          <Alert type="error">ปิดทุกแผนแล้ว — บอทจะไม่เข้าไม้ใหม่เลย</Alert>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>
            <ToggleRight size={17} className="text-gold" /> แผนเทรดทองคำ ({enabledCount}/{PLAN_LIST.length} เปิดอยู่)
          </h3>
          {data?.updatedAt && (
            <span className="tiny faint">
              แก้ไขล่าสุด {formatThaiDateTime(data.updatedAt)}
              {data.updatedBy ? ` โดย ${data.updatedBy}` : ''}
            </span>
          )}
        </div>
        {!draft ? (
          <div className="card-body">
            <div className="skeleton" style={{ height: 200 }} />
          </div>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>แผน</th>
                  <th className="num">ผู้ใช้ที่เคยเทรด</th>
                  <th className="num">ออเดอร์รวม</th>
                  <th className="num">Win Rate</th>
                  <th className="num">กำไรรวมของลูกค้า</th>
                  <th style={{ textAlign: 'right' }}>สถานะ</th>
                </tr>
              </thead>
              <tbody>
                {PLAN_LIST.map((p) => {
                  const perf = data.perf?.[p.key] || {};
                  const on = draft[p.key];
                  return (
                    <tr key={p.key} style={{ opacity: on ? 1 : 0.6 }}>
                      <td>
                        <div style={{ fontWeight: 700 }}>{p.label}</div>
                        <div className="tiny faint">{p.tag}</div>
                      </td>
                      <td className="num">{perf.users ?? 0}</td>
                      <td className="num">{perf.trades ?? 0}</td>
                      <td className="num text-gold">{(perf.winRate ?? 0).toFixed(1)}%</td>
                      <td className={`num ${(perf.profit ?? 0) >= 0 ? 'text-green' : 'text-red'}`}>{formatUsd(perf.profit ?? 0, { sign: true })}</td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="row" style={{ justifyContent: 'flex-end', gap: 10 }}>
                          <span className={`small ${on ? 'text-green' : 'faint'}`}>{on ? 'เปิด' : 'ปิด'}</span>
                          <button
                            type="button"
                            className={`switch ${on ? 'is-on' : ''}`}
                            role="switch"
                            aria-checked={on}
                            aria-label={`เปิด/ปิด ${p.label}`}
                            onClick={() => setDraft((d) => ({ ...d, [p.key]: !d[p.key] }))}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminShell>
  );
}
