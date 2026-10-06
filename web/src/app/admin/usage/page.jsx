'use client';

import { useCallback, useEffect, useState } from 'react';
import { Download, Globe, MonitorPlay, RefreshCw, Users } from 'lucide-react';
import AdminShell from '../../../components/admin/AdminShell';
import { Alert, StatCard } from '../../../components/ui';
import { useAuth } from '../../../context/AuthContext';
import { cleanText, formatThaiDateTime } from '../../../lib/format';
import { ACTIVITY_LABELS } from '../../../lib/adminLabels';

const n = (v) => Number(v || 0).toLocaleString();
const dot = (color) => ({ display: 'inline-block', width: 9, height: 9, background: color, borderRadius: 2, marginRight: 4 });

function DailyBars({ daily }) {
  const max = Math.max(1, ...daily.map((d) => Math.max(d.downloads, d.opens)));
  const bar = (v, color) => ({ width: 9, height: `${(v / max) * 120}px`, minHeight: v ? 3 : 0, background: color, borderRadius: 2 });
  return (
    <div style={{ overflowX: 'auto' }}>
      <div className="row" style={{ alignItems: 'flex-end', gap: 6, minWidth: 420 }}>
        {daily.map((d) => (
          <div
            key={d.day}
            style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}
            title={`${d.day}: ดาวน์โหลด ${d.downloads} · เปิดโปรแกรม ${d.opens} · ผู้ใช้ ${d.users} คน`}
          >
            <div className="row" style={{ alignItems: 'flex-end', gap: 2, height: 120 }}>
              <span style={bar(d.downloads, 'var(--sky)')} />
              <span style={bar(d.opens, 'var(--green)')} />
            </div>
            <span className="tiny faint">{d.day.slice(8)}</span>
          </div>
        ))}
      </div>
      <div className="row tiny muted" style={{ gap: 14, marginTop: 8 }}>
        <span>
          <span style={dot('var(--sky)')} />
          ดาวน์โหลด (เว็บ)
        </span>
        <span>
          <span style={dot('var(--green)')} />
          เปิดโปรแกรม
        </span>
      </div>
    </div>
  );
}

export default function AdminUsagePage() {
  const { apiFetch, isAdmin } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await apiFetch('/api/admin/usage'));
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

  const d = data?.downloads;
  const u = data?.usage;
  const gh = d?.github;
  const busy = !data && !error;

  return (
    <AdminShell
      title="ดาวน์โหลด & การใช้งานโปรแกรม"
      description="ยอดดาวน์โหลดตัวติดตั้ง และการเปิดโปรแกรม/เริ่มบอทของผู้ใช้ (ย้อนหลัง 30 วัน, เวลาไทย)"
      actions={
        <button className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> รีเฟรช
        </button>
      }
    >
      {error && (
        <div style={{ marginBottom: 16 }}>
          <Alert type="error">{error}</Alert>
        </div>
      )}

      <div className="grid grid-4">
        <StatCard
          icon={Download}
          label="ดาวน์โหลดจากเว็บ"
          value={d ? n(d.allTime) : '—'}
          tone="sky"
          sub={d ? `วันนี้ ${n(d.today)} · 7 วัน ${n(d.last7)} · 30 วัน ${n(d.last30)}` : undefined}
          loading={busy}
        />
        <StatCard
          icon={Globe}
          label="ดาวน์โหลดรวม (GitHub)"
          value={gh ? n(gh.total) : '—'}
          tone="gold"
          sub={gh ? `ตัวติดตั้ง ${n(gh.setup)} · ZIP ${n(gh.zip)} (ทุกช่องทาง)` : d ? 'อ่านจาก GitHub ไม่ได้' : undefined}
          loading={busy}
        />
        <StatCard
          icon={MonitorPlay}
          label="เปิดโปรแกรม (ครั้ง)"
          value={u ? n(u.opensAllTime) : '—'}
          tone="green"
          sub={u ? `วันนี้ ${n(u.opensToday)} ครั้ง · ${n(u.machines30)} เครื่องใน 30 วัน` : undefined}
          loading={busy}
        />
        <StatCard
          icon={Users}
          label="ผู้ใช้งานโปรแกรมวันนี้"
          value={u ? `${n(u.usersToday)} คน` : '—'}
          sub={u ? `7 วัน ${n(u.users7)} · 30 วัน ${n(u.users30)} คน · เริ่มบอท 7 วัน ${n(u.botStarts7)} ครั้ง` : undefined}
          loading={busy}
        />
      </div>

      <div className="grid grid-main-side section" style={{ alignItems: 'start' }}>
        <div className="stack" style={{ gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <h3>14 วันล่าสุด</h3>
            </div>
            <div className="card-body">{data ? <DailyBars daily={data.daily} /> : <div className="skeleton" style={{ height: 150 }} />}</div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>ยอดดาวน์โหลดรายเวอร์ชัน (GitHub)</h3>
            </div>
            {!gh ? (
              <div className="card-body small muted">{data ? 'ไม่มีข้อมูล' : <div className="skeleton" style={{ height: 120 }} />}</div>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>เวอร์ชัน</th>
                      <th>เผยแพร่</th>
                      <th style={{ textAlign: 'right' }}>ตัวติดตั้ง</th>
                      <th style={{ textAlign: 'right' }}>ZIP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gh.perVersion.map((v) => (
                      <tr key={v.version}>
                        <td className="mono">{v.version}</td>
                        <td className="small muted">{v.publishedAt ? formatThaiDateTime(v.publishedAt) : '—'}</td>
                        <td className="mono" style={{ textAlign: 'right' }}>
                          {n(v.setup)}
                        </td>
                        <td className="mono" style={{ textAlign: 'right' }}>
                          {n(v.zip)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div className="stack" style={{ gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <h3>เวอร์ชันที่ผู้ใช้เปิดล่าสุด</h3>
            </div>
            <div className="card-body stack" style={{ gap: 8 }}>
              {!u ? (
                <div className="skeleton" style={{ height: 80 }} />
              ) : u.versions.length === 0 ? (
                <p className="small muted">ยังไม่มีข้อมูล (เริ่มเก็บตั้งแต่โปรแกรมเวอร์ชันนี้)</p>
              ) : (
                u.versions.map((v, i) => (
                  <div key={v.version} className="row-between small">
                    <span className="mono">
                      {v.version} {i === 0 && <span className="badge badge-green">ใหม่สุด</span>}
                    </span>
                    <strong>{n(v.users)} คน</strong>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>ประวัติล่าสุด</h3>
            </div>
            <div className="card-body stack" style={{ gap: 12 }}>
              {!data ? (
                <div className="skeleton" style={{ height: 160 }} />
              ) : data.recent.length === 0 ? (
                <p className="small muted">ยังไม่มีข้อมูล</p>
              ) : (
                data.recent.map((a, i) => (
                  <div key={`${a.created_at}-${i}`} className="small" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 10 }}>
                    <div className="row-between">
                      <span className={`badge ${ACTIVITY_LABELS[a.event]?.badge || 'badge-muted'}`}>{ACTIVITY_LABELS[a.event]?.label || a.event}</span>
                      <span className="tiny faint">{formatThaiDateTime(a.created_at)}</span>
                    </div>
                    <div style={{ marginTop: 4 }}>{a.email || 'ผู้เยี่ยมชม (ไม่ได้เข้าสู่ระบบ)'}</div>
                    {a.detail && <div className="tiny muted">{cleanText(a.detail)}</div>}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </AdminShell>
  );
}
