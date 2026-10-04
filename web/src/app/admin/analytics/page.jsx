'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Navbar from '../../../components/Navbar';
import Footer from '../../../components/Footer';
import { useAuth } from '../../../context/AuthContext';
import { 
  Shield, 
  BarChart3, 
  Users, 
  DollarSign, 
  Key, 
  TrendingUp, 
  CheckCircle2, 
  Sparkles, 
  Copy, 
  Check, 
  Download,
  AlertTriangle,
  Lock,
  ArrowRight
} from 'lucide-react';

export default function AdminAnalyticsPage() {
  const { user, isLoading, openAuthModal, logout } = useAuth();
  const isAdmin = user && (user.role === 'admin' || user.isAdmin === true || user.email?.toLowerCase().startsWith('admin'));

  const [promoHours, setPromoHours] = useState(100);
  const [generatedPromoKey, setGeneratedPromoKey] = useState(null);
  const [copied, setCopied] = useState(false);

  // ข้อมูลสถิติภาพรวมทุก User & ทุกแผน (Mock / Ready for Supabase API)
  const systemMetrics = {
    totalUsers: 48,
    totalRevenueThb: 14500,
    totalHoursSold: 14500,
    totalSystemTrades: 382,
    systemWinRate: 67.2,
    systemNetProfitUsd: 4892.50
  };

  const planBreakdown = [
    { name: 'Plan 0: SMC-LiquidityHunt', trades: 94, win: 68, loss: 26, winRate: 72.3, profit: 1420.00, pf: 2.35 },
    { name: 'Plan 1: SR-SwingBounce', trades: 82, win: 48, loss: 34, winRate: 58.5, profit: 890.50, pf: 1.70 },
    { name: 'Plan 3: BB-H1-Reversion', trades: 64, win: 51, loss: 13, winRate: 79.7, profit: 1340.00, pf: 3.80 },
    { name: 'Plan 4: MA-Cross-Trend (M15)', trades: 78, win: 45, loss: 33, winRate: 57.7, profit: 620.00, pf: 1.45 },
    { name: 'Plan 5: MA-Cross-H1-Trend (H1)', trades: 64, win: 45, loss: 19, winRate: 70.3, profit: 1122.00, pf: 2.60 }
  ];

  const userList = [
    { email: 'trader.alex@gmail.com', hoursLeft: '142.30', trades: 45, winRate: 71.1, profit: 680.50, status: 'Active' },
    { email: 'somchai.invest@fbs.com', hoursLeft: '88.15', trades: 38, winRate: 65.8, profit: 450.20, status: 'Active' },
    { email: 'goldpro.vip@yahoo.com', hoursLeft: '320.00', trades: 62, winRate: 74.2, profit: 1120.00, status: 'Active (Shared)' },
    { email: 'newbie.trader@hotmail.com', hoursLeft: '24.45', trades: 12, winRate: 50.0, profit: 85.00, status: 'Active' },
    { email: 'demo.user@aitrade24.local', hoursLeft: '48.00', trades: 8, winRate: 62.5, profit: 95.40, status: 'Demo' }
  ];

  const handleGeneratePromoKey = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let result = '';
    for (let g = 0; g < 6; g++) {
      let group = '';
      for (let i = 0; i < 4; i++) {
        group += chars.charAt(Math.floor(Math.random() * chars.length));
      }
      result += (g === 0 ? '' : '-') + group;
    }
    setGeneratedPromoKey({
      code: result,
      hours: promoHours,
      createdAt: new Date().toLocaleTimeString('th-TH')
    });
  };

  const handleCopy = (text) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  if (isLoading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar />
        <main style={{ maxWidth: '600px', margin: '8rem auto', textAlign: 'center', padding: '2rem' }}>
          <div style={{ color: '#fbbf24', fontSize: '1.1rem', fontWeight: 600 }}>กำลังตรวจสอบสิทธิ์ Admin...</div>
        </main>
        <Footer />
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar />
        <main style={{ maxWidth: '640px', margin: '4.5rem auto', padding: '2rem 1.5rem', width: '100%' }}>
          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1.5px solid rgba(244, 63, 94, 0.4)',
            borderRadius: '20px',
            padding: '2.5rem',
            textAlign: 'center',
            boxShadow: '0 0 35px rgba(244, 63, 94, 0.15)'
          }}>
            <div style={{
              width: '68px',
              height: '68px',
              borderRadius: '18px',
              backgroundColor: 'rgba(244, 63, 94, 0.12)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.5rem auto'
            }}>
              <Shield size={34} color="#f43f5e" />
            </div>

            <h1 style={{ fontSize: '1.6rem', fontWeight: 800, marginBottom: '0.75rem', color: '#fff' }}>
              ต้อง Login ด้วย User Admin เท่านั้น
            </h1>
            
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '2rem' }}>
              หน้านี้สงวนสิทธิ์เฉพาะผู้ดูแลระบบ (Admin Analytics & คลังโปรโมชั่น) เท่านั้น<br />
              {user ? (
                <span style={{ color: '#f87171', display: 'inline-block', marginTop: '0.5rem', fontWeight: 600 }}>
                  บัญชีปัจจุบันของคุณ ({user.email}) ไม่มีสิทธิ์ระดับ Admin
                </span>
              ) : (
                <span>กรุณาเข้าสู่ระบบด้วยบัญชีผู้ดูแลระบบเพื่อเข้าใช้งาน</span>
              )}
            </p>

            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              {user ? (
                <button
                  onClick={() => { logout(); openAuthModal('login'); }}
                  style={{
                    backgroundColor: '#f43f5e',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '0.75rem 1.5rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}
                >
                  <Shield size={16} />
                  สลับบัญชีเป็น Admin
                </button>
              ) : (
                <button
                  onClick={() => openAuthModal('login')}
                  style={{
                    backgroundColor: '#fbbf24',
                    color: '#07090e',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '0.75rem 1.75rem',
                    fontWeight: 800,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    boxShadow: '0 0 20px rgba(251, 191, 36, 0.4)'
                  }}
                >
                  <Shield size={16} />
                  เข้าสู่ระบบแอดมิน (Admin Login)
                </button>
              )}

              <Link
                href="/"
                style={{
                  backgroundColor: 'rgba(255, 255, 255, 0.06)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '10px',
                  padding: '0.75rem 1.5rem',
                  fontWeight: 600,
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                กลับหน้าเรดาร์พอร์ต
              </Link>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '2.5rem 1.5rem', width: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2.5rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fbbf24', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>
              <Shield size={16} />
              <span>GoldBot24 • ศูนย์ผู้ดูแลระบบ & วิเคราะห์ผลงาน (Admin Analytics)</span>
            </div>
            <h1 style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
              แดชบอร์ดผู้ดูแลระบบ & ภาพรวมผลงานทุกลูกค้า
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '4px' }}>
              ตรวจสอบสถิติการเข้าไม้ของทุกลูกค้า อัตรากำไรสุทธิ และผลิตรหัส Product Key สำหรับแจกโปรโมชั่น
            </p>
          </div>
        </div>

        {/* 4 System Metric Cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1rem',
          marginBottom: '2.5rem'
        }}>
          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '14px', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>จำนวนลูกค้าทั้งหมด</div>
            <div style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>{systemMetrics.totalUsers} <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>คน</span></div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '14px', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>รายได้รวม (ชั่วโมงละ 1 บาท)</div>
            <div style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#fbbf24' }}>฿{systemMetrics.totalRevenueThb.toLocaleString()} <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>THB</span></div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '14px', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>อัตราการชนะรวมระบบ (Win Rate)</div>
            <div style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#10b981' }}>{systemMetrics.systemWinRate}%</div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '14px', padding: '1.25rem' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>กำไรสุทธิที่ลูกค้าได้รับรวม (USD)</div>
            <div style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>+${systemMetrics.systemNetProfitUsd.toLocaleString()}</div>
          </div>
        </div>

        {/* Section 1: 5 Plans Performance Comparison Table */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '16px',
          padding: '1.75rem',
          marginBottom: '2.5rem'
        }}>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: '0.3rem' }}>
            📊 เปรียบเทียบผลงาน 5 แผนการเทรดเฉพาะทองคำ (All Users Aggregate)
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            จัดอันดับแผนการเทรดที่สร้างกำไรสูงสุดและมีความแม่นยำสูงสุดในตลาดจริง
          </p>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-secondary)', textAlign: 'left' }}>
                  <th style={{ padding: '0.8rem 1rem' }}>แผนการเทรดทองคำ</th>
                  <th style={{ padding: '0.8rem 1rem' }}>การเข้าไม้รวม (Trades)</th>
                  <th style={{ padding: '0.8rem 1rem' }}>ชนะ (Win)</th>
                  <th style={{ padding: '0.8rem 1rem' }}>แพ้ (Loss)</th>
                  <th style={{ padding: '0.8rem 1rem' }}>Win Rate %</th>
                  <th style={{ padding: '0.8rem 1rem' }}>กำไรสุทธิรวม ($ USD)</th>
                  <th style={{ padding: '0.8rem 1rem' }}>Profit Factor</th>
                </tr>
              </thead>
              <tbody>
                {planBreakdown.map((p, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '0.9rem 1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{p.name}</td>
                    <td style={{ padding: '0.9rem 1rem', fontFamily: 'var(--font-mono)' }}>{p.trades}</td>
                    <td style={{ padding: '0.9rem 1rem', fontFamily: 'var(--font-mono)', color: '#10b981' }}>{p.win}</td>
                    <td style={{ padding: '0.9rem 1rem', fontFamily: 'var(--font-mono)', color: '#f43f5e' }}>{p.loss}</td>
                    <td style={{ padding: '0.9rem 1rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#10b981' }}>{p.winRate.toFixed(1)}%</td>
                    <td style={{ padding: '0.9rem 1rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#fbbf24' }}>+${p.profit.toFixed(2)}</td>
                    <td style={{ padding: '0.9rem 1rem', fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>{p.pf.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 2: Promo Key Generator & User List */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
          gap: '1.5rem'
        }}>
          {/* Card 1: Key Generator */}
          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid rgba(251, 191, 36, 0.3)',
            borderRadius: '16px',
            padding: '1.75rem',
            background: 'linear-gradient(135deg, rgba(251, 191, 36, 0.05), transparent)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fbbf24', marginBottom: '0.4rem' }}>
              <Key size={18} />
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>ผลิต Product Key แจกโปรโมชั่น (Admin Generator)</h3>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1.2rem' }}>
              ผลิตรหัสบัตรเติมเวลา 24 หลักตามจำนวนชั่วโมงที่กำหนดเพื่อมอบให้ลูกค้าพิเศษ
            </p>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                จำนวนชั่วโมงที่ต้องการสร้าง:
              </label>
              <select
                value={promoHours}
                onChange={(e) => setPromoHours(parseInt(e.target.value))}
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(0,0,0,0.4)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-primary)',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  outline: 'none'
                }}
              >
                <option value={24}>24 ชั่วโมง (ทดลอง 1 วัน)</option>
                <option value={50}>50 ชั่วโมง (Starter 50)</option>
                <option value={100}>100 ชั่วโมง (Popular 100)</option>
                <option value={300}>300 ชั่วโมง (Value 300)</option>
                <option value={500}>500 ชั่วโมง (Marathon 500)</option>
                <option value={1000}>1,000 ชั่วโมง (VIP Grand Promo 👑)</option>
              </select>
            </div>

            <button
              onClick={handleGeneratePromoKey}
              style={{
                width: '100%',
                padding: '0.8rem',
                borderRadius: '10px',
                backgroundColor: '#fbbf24',
                color: '#07090e',
                border: 'none',
                fontWeight: 700,
                fontSize: '0.88rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.4rem',
                marginBottom: '1rem',
                boxShadow: '0 4px 15px rgba(251, 191, 36, 0.25)'
              }}
            >
              <Sparkles size={16} />
              <span>ผลิต Product Key เดี๋ยวนี้</span>
            </button>

            {generatedPromoKey && (
              <div style={{
                backgroundColor: 'rgba(0,0,0,0.5)',
                border: '1px solid rgba(251, 191, 36, 0.4)',
                borderRadius: '10px',
                padding: '1rem',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>
                  คีย์โปรโมชั่น (+{generatedPromoKey.hours} ชม.):
                </div>
                <div style={{
                  fontSize: '1.05rem',
                  fontWeight: 800,
                  fontFamily: 'var(--font-mono)',
                  color: '#fbbf24',
                  marginBottom: '0.6rem'
                }}>
                  {generatedPromoKey.code}
                </div>
                <button
                  onClick={() => handleCopy(generatedPromoKey.code)}
                  style={{
                    padding: '0.45rem 1rem',
                    borderRadius: '8px',
                    backgroundColor: copied ? '#10b981' : 'rgba(255,255,255,0.1)',
                    color: '#ffffff',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '0.78rem',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.3rem'
                  }}
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                  <span>{copied ? 'คัดลอกแล้ว!' : 'คัดลอกรหัส'}</span>
                </button>
              </div>
            )}
          </div>

          {/* Card 2: User List Overview */}
          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '16px',
            padding: '1.75rem'
          }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.3rem' }}>
              👤 ลูกค้าที่กำลังใช้งานล่าสุด (Active Users)
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1.2rem' }}>
              ตรวจสอบชั่วโมงคงเหลือและกำไรสุทธิของลูกค้าแต่ละคน
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {userList.map((u, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem 1rem',
                    borderRadius: '10px',
                    backgroundColor: 'rgba(0,0,0,0.3)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '0.82rem'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{u.email}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                      คงเหลือ: <strong style={{ color: '#fbbf24' }}>{u.hoursLeft} ชม.</strong> • {u.trades} ไม้
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 700, color: '#10b981', fontFamily: 'var(--font-mono)' }}>
                      +${u.profit.toFixed(2)}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      WR {u.winRate}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
