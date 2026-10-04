'use client';

import React, { useState, useEffect } from 'react';
import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import Link from 'next/link';
import { 
  Clock, 
  Key, 
  CheckCircle2, 
  AlertCircle, 
  BarChart3, 
  Monitor, 
  RefreshCw, 
  TrendingUp, 
  TrendingDown,
  Sparkles,
  ShoppingBag,
  ArrowRight,
  Shield,
  Lock,
  LogIn,
  UserPlus,
  Loader2,
  User
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function UserDashboardPage() {
  const { user, isLoading, openAuthModal, redeemKey, refreshUser } = useAuth();

  const [keyCodeInput, setKeyCodeInput] = useState('');
  const [redeemStatus, setRedeemStatus] = useState(null); // { type: 'success'|'error', message }
  const [isSubmittingKey, setIsSubmittingKey] = useState(false);
  const [activeScreens, setActiveScreens] = useState(1);
  const [allowShared, setAllowShared] = useState(false);

  // สถิติการเทรดจริงเฉพาะทองคำ
  const [planStats, setPlanStats] = useState({
    overall: {
      total_trades: 0,
      win_trades: 0,
      loss_trades: 0,
      win_rate_pct: 0.0,
      total_profit_usd: 0.00,
      profit_factor: 0.00
    },
    plans: [
      { name: 'Plan 0: SMC-LiquidityHunt', trades: 0, win: 0, loss: 0, winRate: 0.0, profit: 0.00, pf: 0.00 },
      { name: 'Plan 1: SR-SwingBounce', trades: 0, win: 0, loss: 0, winRate: 0.0, profit: 0.00, pf: 0.00 },
      { name: 'Plan 3: BB-H1-Reversion', trades: 0, win: 0, loss: 0, winRate: 0.0, profit: 0.00, pf: 0.00 },
      { name: 'Plan 4: MA-Cross-Trend (M15)', trades: 0, win: 0, loss: 0, winRate: 0.0, profit: 0.00, pf: 0.00 },
      { name: 'Plan 5: MA-Cross-H1-Trend (H1)', trades: 0, win: 0, loss: 0, winRate: 0.0, profit: 0.00, pf: 0.00 }
    ]
  });

  useEffect(() => {
    // อ่านค่า query string 'key' ถ้ามีส่งมาจากหน้า store หรือ my-keys
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const prefillKey = urlParams.get('key');
      if (prefillKey) {
        setKeyCodeInput(formatKey(prefillKey));
      }
    }
  }, []);

  const formatKey = (val) => {
    const clean = (val || '').replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 24);
    const chunks = [];
    for (let i = 0; i < clean.length; i += 4) {
      chunks.push(clean.slice(i, i + 4));
    }
    return chunks.join('-');
  };

  const handleKeyInputChange = (e) => {
    setKeyCodeInput(formatKey(e.target.value));
  };

  const handleRedeem = async (e) => {
    e.preventDefault();
    setRedeemStatus(null);

    if (keyCodeInput.length < 29) {
      setRedeemStatus({ type: 'error', message: 'กรุณากรอกรหัสให้ครบ 24 หลัก (6 กลุ่ม)!' });
      return;
    }

    setIsSubmittingKey(true);
    try {
      const res = await redeemKey(keyCodeInput);
      setRedeemStatus({
        type: 'success',
        message: `🎉 ${res.message}`
      });
      setKeyCodeInput('');
    } catch (err) {
      setRedeemStatus({
        type: 'error',
        message: err.message || 'ไม่สามารถเติมคีย์ได้'
      });
    } finally {
      setIsSubmittingKey(false);
    }
  };

  const formatHHMM = (hoursDecimal) => {
    const totalMins = Math.round((Number(hoursDecimal) || 0) * 60);
    const h = Math.floor(totalMins / 60);
    const m = totalMins % 60;
    return `${h}.${m < 10 ? '0' : ''}${m}`;
  };

  // 1. ถ้ายังไม่ได้ Login ให้แสดงหน้าจอบังคับ Login ก่อนเข้าถึงแดชบอร์ด
  if (!isLoading && !user) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar />

        <main style={{ maxWidth: '620px', margin: 'auto', padding: '4rem 1.5rem', width: '100%' }}>
          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid rgba(251, 191, 36, 0.4)',
            borderRadius: '20px',
            padding: '3rem 2rem',
            textAlign: 'center',
            boxShadow: '0 0 35px rgba(251, 191, 36, 0.15)'
          }}>
            <div style={{
              width: '68px',
              height: '68px',
              borderRadius: '18px',
              backgroundColor: 'rgba(251, 191, 36, 0.12)',
              border: '1.5px solid rgba(251, 191, 36, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.5rem auto'
            }}>
              <Lock size={32} color="#fbbf24" />
            </div>

            <h1 style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fff', marginBottom: '0.6rem', letterSpacing: '-0.02em' }}>
              เข้าสู่ระบบเพื่อใช้งานแดชบอร์ด
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6', marginBottom: '2rem' }}>
              หน้านี้สำหรับสมาชิก <strong>GoldBot24</strong> ในการจัดการกระเป๋าเวลา เติมคีย์สะสมชั่วโมง และดูสถิติการเทรดจริง กรุณาเข้าสู่ระบบหรือสมัครสมาชิกเพื่อเริ่มต้นใช้งาน
            </p>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => openAuthModal('login')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '12px 26px',
                  borderRadius: '10px',
                  backgroundColor: '#fbbf24',
                  color: '#07090e',
                  fontWeight: 800,
                  fontSize: '0.92rem',
                  border: 'none',
                  cursor: 'pointer',
                  boxShadow: '0 0 20px rgba(251, 191, 36, 0.3)'
                }}
              >
                <LogIn size={16} />
                <span>เข้าสู่ระบบ (Login)</span>
              </button>
              <button
                onClick={() => openAuthModal('register')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(255, 255, 255, 0.08)',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: '0.92rem',
                  border: '1px solid var(--border-subtle)',
                  cursor: 'pointer'
                }}
              >
                <UserPlus size={16} />
                <span>สมัครสมาชิกใหม่ฟรี (+48 ชม.)</span>
              </button>
            </div>
          </div>
        </main>

        <Footer />
      </div>
    );
  }

  const hoursRemainingNum = Number(user?.hoursRemaining) || 0.0;
  const isOutOfHours = hoursRemainingNum <= 0;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '2.5rem 1.5rem', width: '100%' }}>
        {/* Header */}
        <div style={{ marginBottom: '2.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fbbf24', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>
            <BarChart3 size={16} />
            <span>GoldBot24 • กระเป๋าเวลา & สถิติส่วนตัว (Customer Dashboard)</span>
          </div>
          <h1 style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.02em', margin: 0 }}>
            สวัสดี, <span style={{ color: '#fbbf24' }}>{user?.displayName || user?.email}</span>
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '6px' }}>
            ตรวจสอบชั่วโมงคงเหลือแบบเรียลไทม์ เติม Product Key สะสมเวลา และดูผลงานการเทรดจริงแยกตามแผน
          </p>
        </div>

        {/* Top 2 Management Cards: Hours & Redeem */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2.5rem'
        }}>
          {/* Card 1: Hours & Sessions */}
          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '16px',
            padding: '1.75rem',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>
                  กระเป๋าเวลาของฉัน (Active Balance)
                </span>
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '6px',
                  backgroundColor: isOutOfHours ? 'rgba(244, 63, 94, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                  color: isOutOfHours ? '#f43f5e' : '#10b981',
                  border: `1px solid ${isOutOfHours ? 'rgba(244, 63, 94, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`
                }}>
                  {isOutOfHours ? '🔴 เวลาหมดแล้ว' : '🟢 พร้อมใช้งาน'}
                </span>
              </div>

              {/* Big Hours Meter */}
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '3.2rem',
                  fontWeight: 800,
                  color: isOutOfHours ? '#f43f5e' : '#fbbf24',
                  letterSpacing: '-0.03em'
                }}>
                  {formatHHMM(hoursRemainingNum)}
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '1rem', fontWeight: 600 }}>
                  ชั่วโมง (HH.MM)
                </span>
              </div>

              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                คิดเวลาตามจริงเฉพาะช่วงเวลาที่บอทเปิดทำงานบนคอมพิวเตอร์ของคุณ
              </div>

              {/* Account Details Box */}
              <div style={{
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '10px',
                padding: '0.85rem 1rem',
                fontSize: '0.82rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>อีเมลผู้ใช้งาน:</span>
                  <span style={{ fontWeight: 600, color: '#fff' }}>{user?.email}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>พอร์ต MT5 ที่ผูก:</span>
                  <span style={{ fontWeight: 600, color: '#38bdf8' }}>#{user?.mt5Login || '106584946'}</span>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
              <Link
                href="/store"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.4rem',
                  flex: 1,
                  padding: '0.75rem 1rem',
                  borderRadius: '10px',
                  backgroundColor: '#fbbf24',
                  color: '#07090e',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  textDecoration: 'none'
                }}
              >
                <ShoppingBag size={15} />
                <span>สั่งซื้อชั่วโมงเพิ่ม (1 บาท/ชม.)</span>
              </Link>
              <button
                onClick={refreshUser}
                style={{
                  padding: '0.75rem 1rem',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid var(--border-subtle)',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer'
                }}
                title="รีเฟรชยอดเวลาล่าสุด"
              >
                <RefreshCw size={15} />
              </button>
            </div>
          </div>

          {/* Card 2: Redeem Product Key */}
          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '16px',
            padding: '1.75rem',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between'
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
                <Key size={18} color="#fbbf24" />
                <h2 style={{ fontSize: '1.2rem', fontWeight: 800, margin: 0 }}>
                  เติม Product Key สะสมเวลา (+)
                </h2>
              </div>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '1.2rem' }}>
                กรอกรหัสบัตรเติมชั่วโมง 24 หลักที่ได้รับจากหน้าสั่งซื้อ หรือกดคัดลอกมาจากหน้ารวมคีย์
              </p>

              {redeemStatus && (
                <div style={{
                  padding: '0.75rem 1rem',
                  borderRadius: '10px',
                  marginBottom: '1rem',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  backgroundColor: redeemStatus.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                  color: redeemStatus.type === 'success' ? '#10b981' : '#f43f5e',
                  border: `1px solid ${redeemStatus.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`
                }}>
                  {redeemStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                  <span>{redeemStatus.message}</span>
                </div>
              )}

              <form onSubmit={handleRedeem}>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                    รหัส Product Key (24 หลัก):
                  </label>
                  <input
                    type="text"
                    value={keyCodeInput}
                    onChange={handleKeyInputChange}
                    placeholder="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"
                    style={{
                      width: '100%',
                      padding: '0.75rem 1rem',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '1rem',
                      fontWeight: 700,
                      borderRadius: '10px',
                      backgroundColor: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(251, 191, 36, 0.4)',
                      color: '#fbbf24',
                      outline: 'none',
                      letterSpacing: '0.05em'
                    }}
                  />
                </div>

                <div style={{
                  backgroundColor: 'rgba(251, 191, 36, 0.05)',
                  border: '1px solid rgba(251, 191, 36, 0.2)',
                  borderRadius: '8px',
                  padding: '0.75rem',
                  fontSize: '0.78rem',
                  color: 'var(--text-secondary)',
                  marginBottom: '1.25rem'
                }}>
                  ✨ <strong>ระบบคิดเวลาแบบบวกเพิ่ม (+)</strong>: ชั่วโมงที่ได้จะถูกบวกเพิ่มจากของเดิมที่คุณมีทันที ไม่มีวันหมดอายุ
                </div>

                <button
                  type="submit"
                  disabled={isSubmittingKey || keyCodeInput.length < 29}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    width: '100%',
                    padding: '0.75rem 1rem',
                    borderRadius: '10px',
                    backgroundColor: keyCodeInput.length >= 29 ? '#fbbf24' : 'rgba(255, 255, 255, 0.08)',
                    color: keyCodeInput.length >= 29 ? '#07090e' : 'var(--text-muted)',
                    fontWeight: 800,
                    fontSize: '0.85rem',
                    border: 'none',
                    cursor: keyCodeInput.length >= 29 && !isSubmittingKey ? 'pointer' : 'not-allowed',
                    transition: 'all 0.2s'
                  }}
                >
                  {isSubmittingKey ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>กำลังตรวจสอบคีย์...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles size={16} />
                      <span>ยืนยันเติมชั่วโมงเข้าบัญชีนี้</span>
                    </>
                  )}
                </button>
              </form>
            </div>

            <div style={{ marginTop: '1rem', textAlign: 'center', fontSize: '0.78rem' }}>
              <Link href="/my-keys" style={{ color: '#38bdf8', textDecoration: 'none' }}>
                ดูประวัติ Product Key ทั้งหมดของคุณ ➔
              </Link>
            </div>
          </div>
        </div>

        {/* Section 2: 5 Plans Gold Specialist Performance Table */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '16px',
          padding: '1.75rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 800, margin: 0 }}>
                สถิติการเทรดเฉพาะทองคำ 5 แผน (XAUUSD Real-time)
              </h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                สถิติการเข้าออเดอร์จริงที่บอทรันในคอมพิวเตอร์ของคุณ
              </p>
            </div>
            <div style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <CheckCircle2 size={14} />
              <span>Real Trading Engine Active</span>
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-secondary)', textAlign: 'left' }}>
                  <th style={{ padding: '0.75rem 1rem' }}>แผนการเทรดทองคำ</th>
                  <th style={{ padding: '0.75rem 1rem' }}>เข้าไม้รวม</th>
                  <th style={{ padding: '0.75rem 1rem' }}>ชนะ (Win)</th>
                  <th style={{ padding: '0.75rem 1rem' }}>แพ้ (Loss)</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Win Rate %</th>
                  <th style={{ padding: '0.75rem 1rem' }}>กำไรสุทธิ ($ USD)</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Profit Factor</th>
                </tr>
              </thead>
              <tbody>
                {planStats.plans.map((p, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '0.85rem 1rem', fontWeight: 600, color: '#fff' }}>{p.name}</td>
                    <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)' }}>{p.trades}</td>
                    <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', color: '#10b981' }}>{p.win}</td>
                    <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', color: '#f43f5e' }}>{p.loss}</td>
                    <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: '#fbbf24' }}>
                      {p.winRate.toFixed(1)}%
                    </td>
                    <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: p.profit >= 0 ? '#10b981' : '#f43f5e' }}>
                      {p.profit >= 0 ? `+$${p.profit.toFixed(2)}` : `-$${Math.abs(p.profit).toFixed(2)}`}
                    </td>
                    <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)' }}>{p.pf.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
