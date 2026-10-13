'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { BarChart3, ChevronDown, ChevronUp, Clock, Key, Lock, Receipt, RefreshCw, ShoppingBag, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import RedeemCard from '../../components/RedeemCard';
import OnlineRewardCard from '../../components/OnlineRewardCard';
import MembershipCard from '../../components/MembershipCard';
import HoursHistoryCard from '../../components/HoursHistoryCard';
import KeyVault from '../../components/KeyVault';
import { Alert, AuthGate, PageHeader, PageLoading, Spinner, StatCard } from '../../components/ui';
import { formatHHMM, formatKeyInput } from '../../lib/format';
import { LOW_HOURS } from '../../lib/hours';

export default function DashboardPage() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <PageLoading />;
  if (!user) {
    return <AuthGate icon={Lock} title="เข้าสู่ระบบเพื่อดูกระเป๋าเวลา" description="จัดการชั่วโมงใช้งาน เติม Product Key และดูสถิติการเทรดแยกตามแผนของคุณ" />;
  }
  return (
    <Suspense fallback={<PageLoading />}>
      <Dashboard />
    </Suspense>
  );
}

function Dashboard() {
  const { user, refreshUser } = useAuth();
  const [refreshing, setRefreshing] = useState(false);
  // คีย์ของฉัน: ซ่อนไว้ กดปุ่มเพื่อเปิด · ลิงก์ /dashboard?keys=1 (หรือ /my-keys เดิม) เปิดให้อัตโนมัติ
  const params = useSearchParams();
  const [showKeys, setShowKeys] = useState(false);
  const keysRef = useRef(null);
  useEffect(() => {
    if (params?.get('keys') === '1') {
      setShowKeys(true);
      setTimeout(() => keysRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 150);
    }
  }, [params]);

  const refreshAll = async () => {
    setRefreshing(true);
    await refreshUser();
    setRefreshing(false);
  };

  const hours = Number(user.hoursRemaining) || 0;
  const out = hours <= 0;
  const low = !out && hours <= LOW_HOURS;

  return (
    <div className="container page">
      <PageHeader
        eyebrow="My Account"
        icon={BarChart3}
        title={`สวัสดี, ${user.displayName || user.email}`}
        description="ชั่วโมงใช้งาน ระดับสมาชิก และการเติมคีย์ — ผลการเทรดอยู่ที่หน้าพอร์ตสด"
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
            <ShoppingBag size={16} /> เติมชั่วโมงเพิ่ม
          </Link>
        </div>

        <RedeemCard />
      </div>

      <div className="section">
        {user && <MembershipCard membership={user.membership} compact onBuy={() => { window.location.href = '/store?member=1'; }} />}
        {user?.online && <OnlineRewardCard online={user.online} />}
        {user && <HoursHistoryCard />}
      </div>

      <div className="section" ref={keysRef} id="my-keys">
        <div className="row wrap" style={{ gap: 8 }}>
          <button type="button" className={`btn ${showKeys ? 'btn-secondary' : 'btn-outline-gold'}`} onClick={() => setShowKeys((v) => !v)} aria-expanded={showKeys}>
            <Key size={16} /> {showKeys ? 'ซ่อนคีย์ของฉัน' : 'ดูคีย์ของฉัน'} {showKeys ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          <Link href="/receipts" className="btn btn-ghost">
            <Receipt size={16} /> ใบเสร็จของฉัน
          </Link>
        </div>
        {showKeys && (
          <div style={{ marginTop: 16 }}>
            <KeyVault />
          </div>
        )}
      </div>

    </div>
  );
}
