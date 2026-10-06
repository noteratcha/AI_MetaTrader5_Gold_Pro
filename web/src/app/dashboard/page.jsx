'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { BarChart3, Clock, Key, Lock, RefreshCw, ShoppingBag, Sparkles, Target, TrendingUp, Trophy } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Alert, AuthGate, PageHeader, PageLoading, Spinner, StatCard } from '../../components/ui';
import { formatHHMM, formatKeyInput, formatUsd } from '../../lib/format';
import { planDisplay } from '../../lib/plans';

export default function DashboardPage() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <PageLoading />;
  if (!user) {
    return <AuthGate icon={Lock} title="เข้าสู่ระบบเพื่อดูกระเป๋าเวลา" description="จัดการชั่วโมงใช้งาน เติม Product Key และดูสถิติการเทรดแยกตามแผนของคุณ" />;
  }
  return <Dashboard />;
}

function Dashboard() {
  const { user, apiFetch, refreshUser } = useAuth();
  const [stats, setStats] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const loadStats = useCallback(async () => {
    try {
      setStats(await apiFetch('/api/user/stats'));
    } catch {
      setStats({ overall: { trades: 0, win: 0, loss: 0, profit: 0, winRate: 0 }, plans: [] });
    }
  }, [apiFetch]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const refreshAll = async () => {
    setRefreshing(true);
    await Promise.all([refreshUser(), loadStats()]);
    setRefreshing(false);
  };

  const hours = Number(user.hoursRemaining) || 0;
  const out = hours <= 0;
  const low = !out && hours < 5;
  const o = stats?.overall;

  return (
    <div className="container page">
      <PageHeader
        eyebrow="My Account"
        icon={BarChart3}
        title={`สวัสดี, ${user.displayName || user.email}`}
        description="ชั่วโมงใช้งาน การเติมคีย์ และผลการเทรดจริงจากบอทของคุณ"
        actions={
          <button className="btn btn-secondary btn-sm" onClick={refreshAll} disabled={refreshing}>
            <RefreshCw size={14} className={refreshing ? 'spin' : ''} /> อัปเดตข้อมูล
          </button>
        }
      />

      <div className="grid grid-2">
        <div className={`card card-pad ${out ? '' : 'card-gold'}`}>
          <div className="row-between" style={{ marginBottom: 14 }}>
            <span className="stat-label">
              <span className="icon-chip text-gold">
                <Clock size={16} />
              </span>
              เวลาใช้งานคงเหลือ
            </span>
            {out ? <span className="badge badge-red">เวลาหมด</span> : low ? <span className="badge badge-gold">ใกล้หมด</span> : <span className="badge badge-green">พร้อมใช้งาน</span>}
          </div>
          <div className="row" style={{ alignItems: 'baseline', gap: 10 }}>
            <span className={`mono ${out ? 'text-red' : 'text-gold'}`} style={{ fontSize: 'clamp(2.4rem, 6vw, 3.2rem)', fontWeight: 700, letterSpacing: '-0.03em' }}>
              {formatHHMM(hours)}
            </span>
            <span className="muted">ชั่วโมง.นาที</span>
          </div>
          <p className="small muted" style={{ marginTop: 6 }}>
            ตัดเวลาเฉพาะตอนบอทกำลังทำงานบนเครื่องของคุณ · 1 บาท/ชั่วโมง
          </p>
          <hr className="divider" />
          <div className="stack small" style={{ gap: 8 }}>
            <div className="row-between">
              <span className="faint">อีเมล</span>
              <span>{user.email}</span>
            </div>
            <div className="row-between">
              <span className="faint">บัญชี MT5 ที่เชื่อมต่อ</span>
              <span className="mono">{user.mt5Login ? `#${user.mt5Login}` : '—'}</span>
            </div>
          </div>
          <Link href="/store" className="btn btn-primary btn-block" style={{ marginTop: 20 }}>
            <ShoppingBag size={16} /> ซื้อชั่วโมงเพิ่ม
          </Link>
        </div>

        <RedeemCard />
      </div>

      <div className="section">
        <div className="section-title">
          <div>
            <h2>ผลการเทรดของคุณ</h2>
            <p>ซิงค์จากโปรแกรม Desktop เมื่อออเดอร์ปิด</p>
          </div>
        </div>
        <div className="grid grid-4">
          <StatCard icon={Target} label="ออเดอร์ทั้งหมด" value={o ? o.trades : '—'} loading={!stats} />
          <StatCard icon={Trophy} label="Win Rate" value={o ? `${o.winRate.toFixed(1)}%` : '—'} tone="gold" sub={o ? `ชนะ ${o.win} · แพ้ ${o.loss}` : undefined} loading={!stats} />
          <StatCard
            icon={TrendingUp}
            label="กำไรสุทธิ"
            value={o ? formatUsd(o.profit, { sign: true }) : '—'}
            tone={o && o.profit > 0 ? 'green' : o && o.profit < 0 ? 'red' : undefined}
            loading={!stats}
          />
          <StatCard icon={BarChart3} label="แผนที่มีการเทรด" value={stats ? stats.plans.filter((p) => p.trades > 0).length : '—'} sub="จาก 5 แผน" loading={!stats} />
        </div>

        <div className="card section">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>แผนเทรด</th>
                  <th className="num">ออเดอร์</th>
                  <th className="num">ชนะ</th>
                  <th className="num">แพ้</th>
                  <th style={{ minWidth: 160 }}>Win Rate</th>
                  <th className="num">กำไรสุทธิ</th>
                  <th className="num">Profit Factor</th>
                </tr>
              </thead>
              <tbody>
                {(stats?.plans || []).map((p) => (
                  <tr key={p.name}>
                    <td style={{ fontWeight: 600 }}>{planDisplay(p.name)}</td>
                    <td className="num">{p.trades}</td>
                    <td className="num text-green">{p.win}</td>
                    <td className="num text-red">{p.loss}</td>
                    <td>
                      <div className="row" style={{ gap: 10 }}>
                        <div className="progress" style={{ flex: 1, minWidth: 70 }}>
                          <span style={{ width: `${Math.min(100, p.winRate)}%`, background: 'var(--gold)' }} />
                        </div>
                        <span className="mono small" style={{ width: 48, textAlign: 'right' }}>
                          {p.winRate.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className={`num ${p.profit > 0 ? 'text-green' : p.profit < 0 ? 'text-red' : ''}`} style={{ fontWeight: 600 }}>
                      {formatUsd(p.profit, { sign: true })}
                    </td>
                    <td className="num">{p.pf.toFixed(2)}</td>
                  </tr>
                ))}
                {!stats &&
                  [0, 1, 2].map((i) => (
                    <tr key={i}>
                      <td colSpan={7}>
                        <div className="skeleton" style={{ height: 16 }} />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function RedeemCard() {
  const { redeemKey } = useAuth();
  const [key, setKey] = useState('');
  const [status, setStatus] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const prefill = new URLSearchParams(window.location.search).get('key');
    if (prefill) setKey(formatKeyInput(prefill));
  }, []);

  const complete = key.length === 29;

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!complete) return;
    setSubmitting(true);
    setStatus(null);
    try {
      const res = await redeemKey(key);
      setStatus({ type: 'success', message: res.message });
      setKey('');
    } catch (err) {
      setStatus({ type: 'error', message: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card card-pad">
      <div className="stat-label" style={{ marginBottom: 6 }}>
        <span className="icon-chip text-gold">
          <Key size={16} />
        </span>
        เติม Product Key
      </div>
      <p className="small muted" style={{ marginBottom: 18 }}>
        กรอกรหัส 24 หลักจากหน้าซื้อชั่วโมงหรือคีย์โปรโมชัน ชั่วโมงจะถูกบวกเพิ่มจากยอดเดิมทันที
      </p>
      <form onSubmit={onSubmit} className="stack" style={{ gap: 14 }}>
        {status && <Alert type={status.type}>{status.message}</Alert>}
        <input
          className="input input-key"
          value={key}
          onChange={(e) => setKey(formatKeyInput(e.target.value))}
          placeholder="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"
          aria-label="Product Key"
          autoComplete="off"
          spellCheck={false}
        />
        <div className="row-between tiny faint">
          <span>{key.replace(/-/g, '').length}/24 ตัวอักษร</span>
          <Link href="/my-keys" className="text-sky">
            ดูคีย์ของฉัน
          </Link>
        </div>
        <button type="submit" className="btn btn-primary btn-block" disabled={!complete || submitting}>
          {submitting ? <Spinner /> : <Sparkles size={16} />}
          {submitting ? 'กำลังตรวจสอบ...' : 'เติมชั่วโมงเข้าบัญชี'}
        </button>
      </form>
    </div>
  );
}
