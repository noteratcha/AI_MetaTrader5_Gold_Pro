'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { Activity, Banknote, Clock, KeyRound, MessageCircle, RefreshCw, Target, TrendingUp, Users } from 'lucide-react';
import AdminShell from '../../components/admin/AdminShell';
import { Alert, Pager, StatCard } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import { formatThaiDateTime, formatThb, formatUsd } from '../../lib/format';
import { ACTIVITY_LABELS } from '../../lib/adminLabels';

export default function AdminOverviewPage() {
  const { apiFetch, isAdmin } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [lineStatus, setLineStatus] = useState(null);
  const [activity, setActivity] = useState(null); // { items, page, totalPages, total }
  const [activityPage, setActivityPage] = useState(1);
  const [activityLoading, setActivityLoading] = useState(false);

  const loadActivity = useCallback(
    async (page) => {
      setActivityLoading(true);
      try {
        setActivity(await apiFetch(`/api/admin/activity?page=${page}`));
      } catch {
        /* แสดงข้อมูลเดิมไว้ */
      } finally {
        setActivityLoading(false);
      }
    },
    [apiFetch]
  );

  useEffect(() => {
    if (isAdmin) loadActivity(activityPage);
  }, [isAdmin, activityPage, loadActivity]);
  const [lineBusy, setLineBusy] = useState(false);

  const testLine = async (path = '/api/admin/line-test') => {
    setLineBusy(true);
    setLineStatus(null);
    try {
      const res = await apiFetch(path, { method: 'POST' });
      setLineStatus({ type: 'success', message: res.message });
    } catch (err) {
      setLineStatus({ type: 'error', message: err.message });
    } finally {
      setLineBusy(false);
    }
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await apiFetch('/api/admin/overview'));
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);

  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin, load]);

  const m = data?.metrics;
  const t = m?.trades;
  const tradeTotal = t ? t.tp + t.sl + t.botClose + t.manualClose : 0;

  return (
    <AdminShell
      title="ภาพรวมระบบ"
      description="สรุปผู้ใช้ รายได้ คีย์ และผลการเทรดของทุกบัญชี"
      actions={
        <>
          <button className="btn btn-ghost btn-sm" onClick={() => testLine()} disabled={lineBusy} title="ส่งข้อความทดสอบไปที่ LINE OA">
            <MessageCircle size={14} /> {lineBusy ? 'กำลังส่ง...' : 'ทดสอบ LINE'}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => testLine('/api/cron/daily-summary')} disabled={lineBusy} title="ส่งสรุปยอดของวันนี้ไปที่ LINE ทันที (ปกติส่งอัตโนมัติ 21:00 น.)">
            <TrendingUp size={14} /> ส่งสรุปวันนี้
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => { load(); loadActivity(activityPage); }} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} /> รีเฟรช
          </button>
        </>
      }
    >
      {lineStatus && (
        <div style={{ marginBottom: 16 }}>
          <Alert type={lineStatus.type}>{lineStatus.message}</Alert>
        </div>
      )}
      {error && (
        <div style={{ marginBottom: 16 }}>
          <Alert type="error">{error}</Alert>
        </div>
      )}
      {data?.setupRequired && (
        <div style={{ marginBottom: 16 }}>
          <Alert type="gold">ยังไม่ได้รัน <code>supabase_admin_patch_02.sql</code> — สรุปการเทรดและ Log กิจกรรมจะแสดงหลังรันไฟล์นี้</Alert>
        </div>
      )}

      <div className="grid grid-4">
        <StatCard icon={Users} label="ผู้ใช้ทั้งหมด" value={m ? m.totalUsers.toLocaleString() : '—'} sub={m ? `ระงับ ${m.disabledUsers} · เวลาใกล้หมด ${m.lowHoursUsers}` : undefined} loading={!data && !error} />
        <StatCard icon={Activity} label="บอทออนไลน์ตอนนี้" value={m ? m.onlineBots : '—'} tone="green" sub="ส่งสัญญาณภายใน 2 นาทีล่าสุด" loading={!data && !error} />
        <StatCard icon={Banknote} label="รายได้รวม" value={m ? formatThb(m.revenueThb) : '—'} tone="gold" sub={m ? `${m.paidOrders} คำสั่งซื้อ · รอชำระ ${m.pendingOrders}` : undefined} loading={!data && !error} />
        <StatCard icon={Clock} label="ชั่วโมงคงเหลือรวม" value={m ? Math.round(m.hoursOutstanding).toLocaleString() : '—'} tone="sky" sub={m ? `คีย์ยังไม่ใช้ ${m.unusedKeys} ใบ` : undefined} loading={!data && !error} />
      </div>

      <div className="grid grid-main-side section" style={{ alignItems: 'start' }}>
        <div className="card">
          <div className="card-header">
            <h3>
              <Target size={17} className="text-gold" /> การปิดออเดอร์ทั้งระบบ
            </h3>
            {t && <span className={`badge ${t.netProfit >= 0 ? 'badge-green' : 'badge-red'}`}>สุทธิ {formatUsd(t.netProfit, { sign: true })}</span>}
          </div>
          <div className="card-body">
            {!t ? (
              <div className="skeleton" style={{ height: 120 }} />
            ) : (
              <>
                <div className="grid grid-4" style={{ gap: 12 }}>
                  {[
                    ['เปิดไม้', t.opens, 'var(--text)'],
                    ['ชน TP', t.tp, 'var(--green)'],
                    ['ชน SL', t.sl, 'var(--red)'],
                    ['บอทปิด / ปิดเอง', `${t.botClose} / ${t.manualClose}`, 'var(--orange)'],
                  ].map(([label, value, color]) => (
                    <div key={label} className="card" style={{ padding: 14, background: 'var(--bg-elevated)' }}>
                      <div className="tiny faint">{label}</div>
                      <div className="mono" style={{ fontSize: '1.4rem', fontWeight: 700, color }}>
                        {value}
                      </div>
                    </div>
                  ))}
                </div>
                {tradeTotal > 0 && (
                  <>
                    <div className="mini-bar" style={{ marginTop: 18, height: 10 }}>
                      <span style={{ width: `${(t.tp / tradeTotal) * 100}%`, background: 'var(--green)' }} />
                      <span style={{ width: `${(t.sl / tradeTotal) * 100}%`, background: 'var(--red)' }} />
                      <span style={{ width: `${(t.botClose / tradeTotal) * 100}%`, background: 'var(--orange)' }} />
                      <span style={{ width: `${(t.manualClose / tradeTotal) * 100}%`, background: 'var(--sky)' }} />
                    </div>
                    <div className="tiny faint" style={{ marginTop: 8 }}>
                      อัตราชน TP เทียบ SL: <strong className="text-gold">{t.tpRate.toFixed(1)}%</strong>
                    </div>
                  </>
                )}
                <div className="row wrap" style={{ marginTop: 18 }}>
                  <Link href="/admin/users" className="btn btn-secondary btn-sm">
                    <Users size={14} /> ดูรายผู้ใช้
                  </Link>
                  <Link href="/admin/plans" className="btn btn-secondary btn-sm">
                    <TrendingUp size={14} /> ผลงานรายแผน
                  </Link>
                  <Link href="/admin/keys" className="btn btn-secondary btn-sm">
                    <KeyRound size={14} /> คีย์ & คำสั่งซื้อ
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>กิจกรรมล่าสุด</h3>
            {activity?.total ? <span className="badge badge-muted">{activity.total} รายการ</span> : null}
          </div>
          <div className="card-body stack" style={{ gap: 12, opacity: activityLoading ? 0.6 : 1 }}>
            {!activity ? (
              <div className="skeleton" style={{ height: 160 }} />
            ) : activity.items.length === 0 ? (
              <p className="small muted">ยังไม่มีกิจกรรม</p>
            ) : (
              activity.items.map((a) => (
                <div key={a.id} className="small" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 10 }}>
                  <div className="row-between">
                    <span className={`badge ${ACTIVITY_LABELS[a.event]?.badge || 'badge-muted'}`}>{ACTIVITY_LABELS[a.event]?.label || a.event}</span>
                    <span className="tiny faint">{formatThaiDateTime(a.created_at)}</span>
                  </div>
                  <div style={{ marginTop: 4 }}>{a.email || a.actor || '—'}</div>
                  {a.detail && <div className="tiny muted">{a.detail}</div>}
                </div>
              ))
            )}
          </div>
          {activity && activity.totalPages > 1 && (
            <div style={{ padding: '0 16px 14px' }}>
              <Pager page={activity.page} totalPages={activity.totalPages} onChange={setActivityPage} loading={activityLoading} />
            </div>
          )}
        </div>
      </div>
    </AdminShell>
  );
}
