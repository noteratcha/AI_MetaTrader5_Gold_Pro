'use client';

import { useCallback, useEffect, useState } from 'react';
import { Banknote, Key, RefreshCw, Shield, ShieldAlert, Sparkles, Target, TrendingUp, Users } from 'lucide-react';
import { useAuth } from '../../../context/AuthContext';
import { Alert, AuthGate, CopyButton, EmptyState, PageHeader, PageLoading, Spinner, StatCard } from '../../../components/ui';
import { formatHHMM, formatThaiDateTime, formatThb, formatUsd } from '../../../lib/format';

export default function AdminAnalyticsPage() {
  const { user, isLoading, isAdmin } = useAuth();
  if (isLoading) return <PageLoading />;
  if (!user) return <AuthGate icon={Shield} title="สำหรับผู้ดูแลระบบเท่านั้น" description="กรุณาเข้าสู่ระบบด้วยบัญชี Admin" />;
  if (!isAdmin) {
    return (
      <div className="container container-narrow page">
        <div className="card">
          <EmptyState icon={ShieldAlert} title="ไม่มีสิทธิ์เข้าถึงหน้านี้">
            บัญชี {user.email} ไม่ใช่ผู้ดูแลระบบ
          </EmptyState>
        </div>
      </div>
    );
  }
  return <AdminDashboard />;
}

function AdminDashboard() {
  const { apiFetch } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [slipok, setSlipok] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [overview, slip] = await Promise.all([apiFetch('/api/admin/overview'), apiFetch('/api/checkout/slipok-status').catch(() => null)]);
      setData(overview);
      setSlipok(slip);
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);

  useEffect(() => {
    load();
  }, [load]);

  const m = data?.metrics;

  return (
    <div className="container container-wide page">
      <PageHeader
        eyebrow="Admin"
        icon={Shield}
        title="ภาพรวมระบบ"
        description="ลูกค้า รายได้ คีย์ และผลการเทรดรวมของทุกบัญชี"
        actions={
          <>
            {slipok && (
              <span className={`badge ${slipok.connected ? 'badge-green' : 'badge-red'}`}>
                <span className={`dot ${slipok.connected ? 'dot-live' : 'dot-red'}`} /> SlipOK {slipok.connected ? 'เชื่อมต่อแล้ว' : 'ไม่พร้อม'}
              </span>
            )}
            <button className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'spin' : ''} /> รีเฟรช
            </button>
          </>
        }
      />

      {error && (
        <div style={{ marginBottom: 16 }}>
          <Alert type="error">{error}</Alert>
        </div>
      )}

      <div className="grid grid-4">
        <StatCard icon={Users} label="ลูกค้าทั้งหมด" value={m ? m.totalUsers.toLocaleString() : '—'} loading={!data && !error} />
        <StatCard icon={Banknote} label="รายได้รวม" value={m ? formatThb(m.revenueThb) : '—'} tone="gold" sub={m ? `${m.paidOrders} คำสั่งซื้อ · ${m.hoursSold.toLocaleString()} ชม.` : undefined} loading={!data && !error} />
        <StatCard icon={Key} label="Product Key ที่ออก" value={m ? m.productKeysIssued.toLocaleString() : '—'} sub={m ? `เติมแล้ว ${m.productKeysRedeemed}` : undefined} loading={!data && !error} />
        <StatCard
          icon={TrendingUp}
          label="กำไรรวมของลูกค้า"
          value={m ? formatUsd(m.systemProfitUsd, { sign: true }) : '—'}
          tone={m && m.systemProfitUsd >= 0 ? 'green' : 'red'}
          sub={m ? `${m.systemTrades} ออเดอร์ · WR ${m.systemWinRate.toFixed(1)}%` : undefined}
          loading={!data && !error}
        />
      </div>

      <div className="card section">
        <div className="card-header">
          <h3>
            <Target size={17} className="text-gold" /> ผลงานรายแผน (ทุกบัญชี)
          </h3>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>แผน</th>
                <th className="num">ออเดอร์</th>
                <th className="num">ชนะ</th>
                <th className="num">แพ้</th>
                <th className="num">Win Rate</th>
                <th className="num">กำไรสุทธิ</th>
              </tr>
            </thead>
            <tbody>
              {(data?.plans || []).map((p) => (
                <tr key={p.name}>
                  <td style={{ fontWeight: 600 }}>{p.name}</td>
                  <td className="num">{p.trades}</td>
                  <td className="num text-green">{p.win}</td>
                  <td className="num text-red">{p.loss}</td>
                  <td className="num text-gold">{p.winRate.toFixed(1)}%</td>
                  <td className={`num ${p.profit >= 0 ? 'text-green' : 'text-red'}`}>{formatUsd(p.profit, { sign: true })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-main-side section">
        <div className="card">
          <div className="card-header">
            <h3>
              <Users size={17} className="text-gold" /> บัญชีที่อัปเดตล่าสุด
            </h3>
          </div>
          {data?.recentUsers?.length ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>ผู้ใช้</th>
                    <th>สิทธิ์</th>
                    <th className="num">ชั่วโมงคงเหลือ</th>
                    <th>อัปเดตล่าสุด</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recentUsers.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{u.displayName}</div>
                        <div className="tiny faint">{u.email}</div>
                      </td>
                      <td>{u.role === 'admin' ? <span className="badge badge-gold">Admin</span> : <span className="badge badge-muted">User</span>}</td>
                      <td className={`num ${u.hoursRemaining <= 0 ? 'text-red' : ''}`}>{formatHHMM(u.hoursRemaining)}</td>
                      <td className="small faint">{formatThaiDateTime(u.updatedAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState icon={Users} title={data ? 'ยังไม่มีผู้ใช้' : 'กำลังโหลด...'} />
          )}
        </div>

        <PromoGenerator recent={data?.promoKeys || []} onCreated={load} />
      </div>
    </div>
  );
}

function PromoGenerator({ recent, onCreated }) {
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
      const res = await apiFetch('/api/admin/promo-key', { method: 'POST', body: JSON.stringify({ hours, expiresInDays }) });
      setCreated(res);
      onCreated?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card card-gold card-pad">
      <div className="stat-label" style={{ marginBottom: 6 }}>
        <span className="icon-chip text-gold">
          <Sparkles size={16} />
        </span>
        สร้าง Promo Key
      </div>
      <p className="small muted" style={{ marginBottom: 16 }}>
        คีย์จะถูกบันทึกลงฐานข้อมูลทันที ลูกค้าใช้เติมได้ครั้งเดียว
      </p>

      <div className="grid grid-2" style={{ gap: 12 }}>
        <label className="field">
          <span className="label">จำนวนชั่วโมง</span>
          <select className="input" value={hours} onChange={(e) => setHours(Number(e.target.value))}>
            {[24, 50, 100, 300, 500, 1000].map((h) => (
              <option key={h} value={h}>
                {h} ชั่วโมง
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="label">หมดอายุใน</span>
          <select className="input" value={expiresInDays} onChange={(e) => setExpiresInDays(Number(e.target.value))}>
            <option value={7}>7 วัน</option>
            <option value={30}>30 วัน</option>
            <option value={90}>90 วัน</option>
            <option value={0}>ไม่หมดอายุ</option>
          </select>
        </label>
      </div>

      <button className="btn btn-primary btn-block" style={{ marginTop: 16 }} onClick={generate} disabled={busy}>
        {busy ? <Spinner /> : <Key size={16} />} สร้างคีย์
      </button>

      {error && (
        <div style={{ marginTop: 12 }}>
          <Alert type="error">{error}</Alert>
        </div>
      )}

      {created && (
        <div className="key-row" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
          <div className="tiny faint">
            +{created.hours} ชม. {created.expiresAt ? `· หมดอายุ ${formatThaiDateTime(created.expiresAt)}` : ''}
          </div>
          <div className="key-code">{created.keyCode}</div>
          <CopyButton text={created.keyCode} label="คัดลอกคีย์" />
        </div>
      )}

      {recent.length > 0 && (
        <>
          <hr className="divider" />
          <div className="tiny faint" style={{ marginBottom: 8 }}>
            Promo Key ล่าสุด
          </div>
          <div className="stack" style={{ gap: 8 }}>
            {recent.slice(0, 6).map((p) => (
              <div key={p.key_code} className="row-between small">
                <span className="mono" style={{ fontSize: '0.78rem' }}>
                  {p.key_code}
                </span>
                {p.used ? <span className="badge badge-muted">ใช้แล้ว</span> : <span className="badge badge-green">{p.hours} ชม.</span>}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
