'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  CircleDollarSign,
  Clock,
  Gauge,
  Layers,
  LineChart,
  MonitorDown,
  Radar,
  RefreshCw,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { EmptyState, PageHeader, PageLoading, StatCard } from '../components/ui';
import { cleanText, formatPrice, formatThaiDateTime, formatUsd, secondsSince, timeAgo } from '../lib/format';
import { PLAN_LIST } from '../lib/packages';
import { planDisplay } from '../lib/plans';
import { CandleCard, DailyPnlCard, NewsImpactCard, OutlookCard } from '../components/LiveInsights';
import TradeHistory from '../components/TradeHistory';
import MyTradeStats from '../components/MyTradeStats';
import { NextNewsCard, useCalendar } from '../components/EconCalendar';

export default function HomePage() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <PageLoading />;
  return user ? <LiveMonitor /> : <Landing />;
}

/* =============================================================================
   Live Portfolio Monitor (ผู้ใช้ที่ล็อกอินแล้ว)
   ============================================================================= */
const POLL_MS = 5000;

function LiveMonitor() {
  const { apiFetch } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const calendar = useCalendar();

  const load = useCallback(async () => {
    try {
      const res = await apiFetch('/api/user/telemetry');
      setData(res);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }, [apiFetch]);

  useEffect(() => {
    load();
    const id = setInterval(() => {
      if (document.visibilityState === 'visible') load();
    }, POLL_MS);
    return () => clearInterval(id);
  }, [load]);

  const manualRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  // หลายบัญชี MT5 (หลาย Profile) — เลือกดูทีละบัญชี หรือภาพรวมทุกบัญชีที่ออนไลน์
  const accounts = data?.accounts || [];
  const onlineAccounts = accounts.filter((a) => secondsSince(a.last_heartbeat) < 60);
  const multi = accounts.length >= 2;
  const [selected, setSelected] = useState(() => {
    try {
      return localStorage.getItem('live_account') || 'all';
    } catch {
      return 'all';
    }
  });
  const choose = (v) => {
    setSelected(v);
    try {
      localStorage.setItem('live_account', v);
    } catch {}
  };
  const selAcc = accounts.find((a) => String(a.login) === selected);
  const overview = multi && !selAcc;
  const t = !multi ? data?.telemetry : selAcc || aggregate(onlineAccounts.length ? onlineAccounts : accounts);
  const isOnline = t && secondsSince(t.last_heartbeat) < 60;
  const isPaused = isOnline && String(t.status || '').startsWith('PAUSED');
  const positions = t?.open_positions || [];
  const radar = (t?.radar_signals || [])[0];
  const loading = data === null && !error;

  return (
    <div className="container container-wide page">
      <PageHeader
        eyebrow="Live Portfolio"
        icon={Activity}
        title="พอร์ต MT5 แบบเรียลไทม์"
        description="ข้อมูลส่งตรงจากโปรแกรม Gold Bot 24 บนเครื่องของคุณทุก 5 วินาที"
        actions={
          <>
            <BotStatus online={isOnline} paused={isPaused} heartbeat={t?.last_heartbeat} hasData={Boolean(t)} />
            <button className="btn btn-secondary btn-sm" onClick={manualRefresh} disabled={refreshing}>
              <RefreshCw size={14} className={refreshing ? 'spin' : ''} /> รีเฟรช
            </button>
          </>
        }
      />

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}

      {multi && <AccountSwitcher accounts={accounts} selected={overview ? 'all' : selected} onChange={choose} onlineCount={onlineAccounts.length} />}

      {!overview && radar?.account && (
        <div className="card account-strip">
          <span className="account-strip-title">
            <MonitorDown size={15} className="text-gold" /> บัญชี MT5 ที่เชื่อมต่อ
          </span>
          <span className="mono">
            <strong>#{radar.account.login}</strong>
          </span>
          <span>{radar.account.server}</span>
          {radar.account.name && <span className="muted">{radar.account.name}</span>}
          <span className={`badge ${radar.account.mode === 'REAL' ? 'badge-gold' : 'badge-sky'}`}>{radar.account.mode === 'REAL' ? 'บัญชีจริง' : 'บัญชีทดลอง (Demo)'}</span>
          {radar.account.leverage ? <span className="muted">Leverage 1:{Number(radar.account.leverage).toLocaleString('en-US')}</span> : null}
          {radar.account.lot ? <span className="muted">ขนาดไม้ {Number(radar.account.lot).toFixed(2)} lot</span> : null}
        </div>
      )}

      {!loading && !t ? (
        <div className="card">
          <EmptyState
            icon={MonitorDown}
            title="ยังไม่มีข้อมูลจากโปรแกรม Gold Bot 24"
            action={
              <Link href="/dashboard" className="btn btn-primary">
                ไปที่กระเป๋าเวลา <ArrowRight size={16} />
              </Link>
            }
          >
            เปิดโปรแกรม Gold Bot 24 บนเครื่องที่ติดตั้ง MetaTrader 5 แล้วเข้าสู่ระบบด้วยบัญชีเดียวกับเว็บนี้ จากนั้นกด “เริ่มบอท” ข้อมูลพอร์ตจะแสดงที่นี่อัตโนมัติ
          </EmptyState>
        </div>
      ) : (
        <>
          <div className="grid grid-4">
            <StatCard icon={Wallet} label="Balance" value={formatUsd(t?.balance)} loading={loading} />
            <StatCard icon={CircleDollarSign} label="Equity" value={formatUsd(t?.equity)} tone="sky" loading={loading} />
            <StatCard
              icon={(t?.floating_profit || 0) >= 0 ? TrendingUp : TrendingDown}
              label="กำไร/ขาดทุนลอยตัว"
              value={formatUsd(t?.floating_profit, { sign: true })}
              tone={(t?.floating_profit || 0) > 0 ? 'green' : (t?.floating_profit || 0) < 0 ? 'red' : undefined}
              sub={`${positions.length} ออเดอร์ที่เปิดอยู่`}
              loading={loading}
            />
            <StatCard icon={Gauge} label="หลักประกันว่าง" value={formatUsd(t?.margin_free)} tone="gold" sub="1 ไม้ ต่อหลักประกัน 100 (Lot 0.01 · ปัดขึ้น)" loading={loading} />
          </div>

          <div className="grid grid-main-side section">
            <PositionsCard positions={positions} loading={loading} showAccount={overview} />
            <RadarCard radar={radar} loading={loading} />
          </div>

          {/* ข้อมูลชุดเดียวกับโปรแกรม Gold Bot 24: AI คาดการณ์ · แท่งเทียน M15 · กำไรรายวัน · ข่าวพร้อมผลต่อทอง */}
          <div className="grid grid-2 section" style={{ alignItems: 'start' }}>
            <OutlookCard outlook={radar?.outlook} />
            <CandleCard candles={radar?.candles} price={radar?.price} />
          </div>
          <div className="grid grid-2 section" style={{ alignItems: 'start' }}>
            <DailyPnlCard rows={radar?.daily_pnl} />
            <NewsImpactCard news={radar?.news} />
          </div>

          <MyTradeStats />

          <div className="grid grid-main-side section" style={{ alignItems: 'start' }}>
            <TradeHistory />
            <NextNewsCard events={calendar.events} />
          </div>
        </>
      )}
    </div>
  );
}

function BotStatus({ online, paused, heartbeat, hasData }) {
  if (!hasData) return <span className="badge badge-muted"><span className="dot" /> ไม่มีสัญญาณ</span>;
  if (paused) return <span className="badge badge-gold"><span className="dot dot-gold" /> หยุดชั่วคราว</span>;
  if (online) return <span className="badge badge-green"><span className="dot dot-live" /> บอทออนไลน์</span>;
  return (
    <span className="badge badge-red" title={heartbeat ? `อัปเดตล่าสุด ${formatThaiDateTime(heartbeat)}` : undefined}>
      <span className="dot dot-red" /> ออฟไลน์ · {timeAgo(heartbeat)}
    </span>
  );
}

/** รวมหลายบัญชีเป็นภาพรวม: ยอดเงินรวม + ไม้ทุกบัญชี (ติดป้ายเลขบัญชี) · ข้อมูลตลาด/AI ใช้ของบัญชีที่อัปเดตล่าสุด */
function aggregate(list) {
  if (!list.length) return null;
  const sum = (k) => list.reduce((a, x) => a + (Number(x[k]) || 0), 0);
  const latest = [...list].sort((a, b) => new Date(b.last_heartbeat) - new Date(a.last_heartbeat))[0];
  return {
    status: list.every((a) => String(a.status || '').startsWith('PAUSED')) ? latest.status : `ONLINE ${String(latest.status || '').split(' ')[1] || ''}`.trim(),
    balance: sum('balance'),
    equity: sum('equity'),
    floating_profit: sum('floating_profit'),
    margin_free: sum('margin_free'),
    open_positions: list.flatMap((a) => (a.open_positions || []).map((p) => ({ ...p, _account: a.login, _profile: a.profile }))),
    radar_signals: latest.radar_signals,
    last_heartbeat: latest.last_heartbeat,
  };
}

function AccountSwitcher({ accounts, selected, onChange, onlineCount }) {
  return (
    <div className="card account-switcher" style={{ marginBottom: 16, padding: 12 }}>
      <div className="row wrap" style={{ gap: 8, alignItems: 'center' }}>
        <span className="small muted" style={{ marginRight: 4 }}>
          <MonitorDown size={15} className="text-gold" style={{ verticalAlign: '-3px' }} /> เลือกบัญชี
        </span>
        <button type="button" className={`btn btn-sm ${selected === 'all' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => onChange('all')}>
          ภาพรวมทุกบัญชี ({onlineCount} ออนไลน์)
        </button>
        {accounts.map((a) => {
          const on = secondsSince(a.last_heartbeat) < 60;
          const acc = a.radar_signals?.[0]?.account;
          return (
            <button
              key={a.login}
              type="button"
              className={`btn btn-sm ${selected === String(a.login) ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => onChange(String(a.login))}
              title={`${acc?.server || ''} · Profile ${a.profile} · อัปเดต ${timeAgo(a.last_heartbeat)}`}
            >
              <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 8, background: on ? '#34d399' : '#6b7385' }} />
              #{a.login}
              <span className="faint" style={{ fontWeight: 400 }}>
                {' '}
                · {a.profile}
                {acc?.mode ? ` · ${acc.mode === 'REAL' ? 'จริง' : 'Demo'}` : ''}
              </span>
            </button>
          );
        })}
      </div>
      <p className="tiny faint" style={{ margin: '8px 0 0' }}>
        ภาพรวมรวมยอดเงินและไม้ของทุกบัญชีที่ออนไลน์ (บัญชีเซ็นต์นับตามหน่วยของบัญชี) · ข้อมูล AI/ตลาดใช้ของบัญชีที่อัปเดตล่าสุด
      </p>
    </div>
  );
}

function PositionsCard({ positions, loading, showAccount }) {
  return (
    <div className="card">
      <div className="card-header">
        <h3>
          <Layers size={17} className="text-gold" /> ออเดอร์ที่เปิดอยู่
        </h3>
        <span className="badge badge-muted">{positions.length} ไม้</span>
      </div>
      {loading ? (
        <div className="card-body stack">
          <div className="skeleton" style={{ height: 18 }} />
          <div className="skeleton" style={{ height: 18, width: '80%' }} />
        </div>
      ) : positions.length === 0 ? (
        <EmptyState icon={Layers} title="ไม่มีออเดอร์ค้าง">บอทกำลังรอสัญญาณที่เข้าเงื่อนไขแผนเทรด</EmptyState>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                {showAccount && <th>บัญชี</th>}
                <th>ฝั่ง</th>
                <th>แผน</th>
                <th className="num">Lot</th>
                <th className="num">ราคาเปิด</th>
                <th className="num">SL</th>
                <th className="num">TP</th>
                <th className="num">กำไร</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={`${p._account || ''}-${p.ticket}`}>
                  {showAccount && <td className="small mono">#{p._account}</td>}
                  <td>
                    <span className={`badge ${p.type === 'BUY' ? 'badge-green' : 'badge-red'}`}>{p.type}</span>
                  </td>
                  <td className="small">{planDisplay(p.plan)}</td>
                  <td className="num">{Number(p.volume).toFixed(2)}</td>
                  <td className="num">{formatPrice(p.price_open)}</td>
                  <td className="num faint">{formatPrice(p.sl)}</td>
                  <td className="num faint">{Number(p.tp) > 0 ? formatPrice(p.tp) : 'รันเทรนด์'}</td>
                  <td className={`num ${p.profit >= 0 ? 'text-green' : 'text-red'}`} style={{ fontWeight: 600 }}>
                    {formatUsd(p.profit, { sign: true })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RadarCard({ radar, loading }) {
  const up = Math.round((Number(radar?.up_prob) || 0.5) * 100);
  const down = 100 - up;
  const h4 = String(radar?.h4_trend || '');
  const h4Tone = h4.startsWith('BULL') ? 'badge-green' : h4.startsWith('BEAR') ? 'badge-red' : 'badge-sky';
  const h1 = String(radar?.h1_trend || '');
  // H1 = เทรนด์ที่ Plan 1 ใช้ (MA100/150/200 เรียงตัว) — โปรแกรมเวอร์ชันเก่ายังส่งแค่ h1_trend
  const stack = radar?.h1_stack_dir;
  const h1Tone =
    stack === undefined
      ? h1.startsWith('UP') ? 'badge-green' : h1.startsWith('DOWN') ? 'badge-red' : 'badge-muted'
      : Number(stack) === 1 ? 'badge-green' : Number(stack) === -1 ? 'badge-red' : 'badge-gold';
  const h1Label =
    stack === undefined
      ? h1.startsWith('UP') ? h1.replace('UPTREND', '▲ ขาขึ้น') : h1.startsWith('DOWN') ? h1.replace('DOWNTREND', '▼ ขาลง') : ''
      : Number(stack) === 1 ? '▲ ขาขึ้น · MA100>150>200' : Number(stack) === -1 ? '▼ ขาลง · MA100<150<200' : '◆ ไม่เรียงตัว';
  const status = cleanText(radar?.status) || '[WAIT OUTSIDE ZONE]';
  // สภาวะตลาด (MA50/100/150 เรียงตัว) — โปรแกรมเวอร์ชันใหม่ส่ง h1_cond / h4_cond มา
  const condBadge = (c) => (Number(c) === 1 ? ['▲ ขาขึ้น', 'badge-green'] : Number(c) === -1 ? ['▼ ขาลง', 'badge-red'] : ['◆ ไซด์เวย์', 'badge-sky']);
  const [h1CondLabel, h1CondTone] = radar?.h1_cond !== undefined ? condBadge(radar.h1_cond) : [h1Label, h1Tone];
  const [h4CondLabel, h4CondTone] = radar?.h4_cond !== undefined ? condBadge(radar.h4_cond) : [h4, h4Tone];

  return (
    <div className="card">
      <div className="card-header">
        <h3>
          <Radar size={17} className="text-gold" /> AI Radar · XAUUSD
        </h3>
        {radar?.in_zone ? <span className="badge badge-gold">เข้าโซน</span> : <span className="badge badge-muted">รอโซน</span>}
      </div>
      <div className="card-body stack" style={{ gap: 18 }}>
        {loading ? (
          <div className="skeleton" style={{ height: 120 }} />
        ) : (
          <>
            <div className="row-between">
              <span className="muted small">ราคาทองคำ</span>
              <span className="mono" style={{ fontSize: '1.5rem', fontWeight: 700 }}>
                {formatPrice(radar?.price)}
              </span>
            </div>
            <div>
              <div className="row-between small" style={{ marginBottom: 6 }}>
                <span className="text-green">AI ขึ้น {up}%</span>
                <span className="text-red">ลง {down}%</span>
              </div>
              <div className="progress" style={{ background: 'var(--red-soft)' }}>
                <span style={{ width: `${up}%`, background: 'var(--green)' }} />
              </div>
            </div>
            <div className="row-between">
              <span className="muted small">เทรนด์ H1</span>
              <span className={`badge ${h1CondTone}`}>{h1CondLabel || 'กำลังวิเคราะห์'}</span>
            </div>
            <div className="row-between">
              <span className="muted small">เทรนด์ H4</span>
              <span className={`badge ${h4CondTone}`}>{h4CondLabel || 'กำลังวิเคราะห์'}</span>
            </div>
            <div className="row-between">
              <span className="muted small">แนวรับ – ต้าน H1</span>
              <span className="mono small">
                {Number(radar?.h1_support) > 0 && Number(radar?.h1_resistance) > 0 ? (
                  <>
                    <span className="text-green" title={radar?.h1_sup_h4_conf ? 'H4 Confluence ยืนยัน' : ''}>
                      {formatPrice(radar.h1_support)}
                      {radar?.h1_sup_stars ? <span style={{ fontSize: '0.72rem', color: '#f59e0b', marginLeft: 3 }}>★{Number(radar.h1_sup_stars).toFixed(1)}</span> : null}
                      {radar?.h1_sup_h4_conf && <span className="badge badge-gold" style={{ fontSize: '0.62rem', padding: '1px 4px', marginLeft: 3 }}>👑 H4</span>}
                    </span>
                    {' – '}
                    <span className="text-red" title={radar?.h1_res_h4_conf ? 'H4 Confluence ยืนยัน' : ''}>
                      {formatPrice(radar.h1_resistance)}
                      {radar?.h1_res_stars ? <span style={{ fontSize: '0.72rem', color: '#f59e0b', marginLeft: 3 }}>★{Number(radar.h1_res_stars).toFixed(1)}</span> : null}
                      {radar?.h1_res_h4_conf && <span className="badge badge-gold" style={{ fontSize: '0.62rem', padding: '1px 4px', marginLeft: 3 }}>👑 H4</span>}
                    </span>
                  </>
                ) : (
                  '—'
                )}
              </span>
            </div>
            <div className="row-between">
              <span className="muted small">แนวรับ – ต้าน H4</span>
              <span className="mono small">
                {Number(radar?.h4_support) > 0 && Number(radar?.h4_resistance) > 0 ? (
                  <>
                    <span className="text-green">
                      {formatPrice(radar.h4_support)}
                      {radar?.h4_sup_stars ? <span style={{ fontSize: '0.72rem', color: '#f59e0b', marginLeft: 3 }}>★{Number(radar.h4_sup_stars).toFixed(1)}</span> : null}
                    </span>
                    {' – '}
                    <span className="text-red">
                      {formatPrice(radar.h4_resistance)}
                      {radar?.h4_res_stars ? <span style={{ fontSize: '0.72rem', color: '#f59e0b', marginLeft: 3 }}>★{Number(radar.h4_res_stars).toFixed(1)}</span> : null}
                    </span>
                  </>
                ) : (
                  '—'
                )}
              </span>
            </div>
            {radar?.h1_focus_action ? (
              <div style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: 6, padding: '5px 8px', fontSize: '0.72rem', color: 'var(--gold)' }}>
                🎯 {radar.h1_focus_action}
              </div>
            ) : null}
            <div className="radar-status mono small">{status}</div>
          </>
        )}
      </div>
    </div>
  );
}

/* =============================================================================
   Landing (ผู้เยี่ยมชม)
   ============================================================================= */
const FEATURES = [
  { icon: BrainCircuit, title: 'AI วิเคราะห์ทิศทาง', text: 'โมเดล Random Forest 16 ฟีเจอร์ รีเทรนทุก 24 ชั่วโมงตามพฤติกรรมทองคำล่าสุด' },
  { icon: LineChart, title: 'กรองเทรนด์หลายไทม์เฟรม', text: 'H4 กำหนดทิศ · H1 กำหนดโซน · M15 จับจังหวะ ไม่เทรดสวนเทรนด์ใหญ่' },
  { icon: ShieldCheck, title: 'คุมความเสี่ยงอัตโนมัติ', text: 'SL 0.75 ATR · ล็อกกำไรที่ 70% · Circuit Breaker หยุดพักเมื่อแพ้ติดกัน' },
  { icon: Clock, title: 'จ่ายเท่าที่ใช้', text: '1 บาท/ชั่วโมง ตัดเวลาเฉพาะตอนบอททำงาน กดหยุดเมื่อไหร่ มิเตอร์หยุดทันที' },
];

const STEPS = [
  { n: '1', title: 'สมัครสมาชิก', text: 'รับเวลาใช้งานฟรี 48 ชั่วโมงทันที' },
  { n: '2', title: 'ติดตั้งโปรแกรม', text: 'รันคู่กับ MetaTrader 5 บน Windows หรือ VPS' },
  { n: '3', title: 'กดเริ่มบอท', text: 'ติดตามพอร์ตและสถิติแบบเรียลไทม์ผ่านเว็บนี้' },
];

function Landing() {
  const { openAuthModal } = useAuth();
  return (
    <>
      <section className="hero">
        <div className="container hero-inner">
          <span className="badge badge-gold" style={{ marginBottom: 18 }}>
            XAUUSD Gold Specialist · MetaTrader 5
          </span>
          <h1 className="hero-title">
            บอทเทรดทองคำด้วย AI
            <br />
            <span className="text-gold">ที่รู้ว่าเมื่อไหร่ไม่ควรเทรด</span>
          </h1>
          <p className="hero-sub">
            5 แผนเทรดเฉพาะทาง ผสานการกรองเทรนด์ H4 แบบเข้มงวด และระบบบริหารความเสี่ยงอัตโนมัติ — คิดค่าบริการตามชั่วโมงที่ใช้งานจริง
          </p>
          <div className="row wrap" style={{ justifyContent: 'center', gap: 12 }}>
            <button className="btn btn-primary btn-lg" onClick={() => openAuthModal('register')}>
              เริ่มใช้ฟรี 48 ชั่วโมง <ArrowRight size={18} />
            </button>
            <Link href="/store" className="btn btn-secondary btn-lg">
              ดูแพ็กเกจราคา
            </Link>
          </div>
          <div className="hero-stats">
            <div>
              <div className="mono text-gold hero-stat-value">1 ฿</div>
              <div className="faint small">ต่อชั่วโมงใช้งาน</div>
            </div>
            <div>
              <div className="mono hero-stat-value">5</div>
              <div className="faint small">แผนเทรดทองคำ</div>
            </div>
            <div>
              <div className="mono hero-stat-value">1:1.5</div>
              <div className="faint small">Risk : Reward</div>
            </div>
          </div>
        </div>
      </section>

      <section className="container section" style={{ marginTop: 0 }}>
        <div className="grid grid-4">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="card card-pad card-interactive">
              <span className="icon-chip" style={{ color: 'var(--gold)', width: 40, height: 40, borderRadius: 12, marginBottom: 14 }}>
                <Icon size={20} />
              </span>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 6 }}>{title}</h3>
              <p className="small muted">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="container section" style={{ marginTop: 56 }}>
        <div className="grid grid-main-side" style={{ alignItems: 'start' }}>
          <div className="card">
            <div className="card-header">
              <h3>แผนเทรดที่ทำงานอยู่</h3>
              <span className="badge badge-muted">5 แผน · XAUUSD</span>
            </div>
            <div className="table-wrap">
              <table className="table">
                <tbody>
                  {PLAN_LIST.map((p) => (
                    <tr key={p.key}>
                      <td style={{ fontWeight: 600 }}>{p.label}</td>
                      <td className="muted small" style={{ textAlign: 'right' }}>
                        {p.tag}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="card card-gold card-pad">
            <h3 style={{ fontWeight: 700, marginBottom: 16 }}>เริ่มต้นใน 3 ขั้นตอน</h3>
            <div className="stack" style={{ gap: 16 }}>
              {STEPS.map((s) => (
                <div key={s.n} className="row" style={{ alignItems: 'flex-start', gap: 14 }}>
                  <span className="step-num">{s.n}</span>
                  <div>
                    <div style={{ fontWeight: 600 }}>{s.title}</div>
                    <div className="small muted">{s.text}</div>
                  </div>
                </div>
              ))}
            </div>
            <button className="btn btn-primary btn-block" style={{ marginTop: 22 }} onClick={() => openAuthModal('register')}>
              สมัครสมาชิกฟรี
            </button>
          </div>
        </div>
      </section>
      <div style={{ height: 56 }} />
    </>
  );
}
