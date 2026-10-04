'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '../context/AuthContext';
import { 
  Bot, 
  ShoppingBag, 
  Key, 
  BarChart3, 
  Shield, 
  Sparkles, 
  CheckCircle2, 
  Clock, 
  ArrowUpRight
} from 'lucide-react';

export default function Footer() {
  const { user } = useAuth();
  const isAdmin = user && (user.role === 'admin' || user.isAdmin === true || user.email?.toLowerCase().startsWith('admin'));
  return (
    <footer style={{
      backgroundColor: '#05070a',
      borderTop: '1px solid rgba(251, 191, 36, 0.15)',
      marginTop: 'auto',
      padding: '3rem 1.5rem 2rem 1.5rem',
      color: 'var(--text-secondary)',
      fontSize: '0.85rem'
    }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* Top Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '2.5rem',
          marginBottom: '2.5rem'
        }}>
          {/* Col 1: Brand & Mission */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '12px',
                overflow: 'hidden',
                border: '1.5px solid rgba(251, 191, 36, 0.5)',
                boxShadow: '0 0 15px rgba(251, 191, 36, 0.3)',
                background: '#0d131a'
              }}>
                <img src="/store_logo.png" alt="GoldBot24 Logo" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
              <div>
                <div style={{ fontWeight: 800, fontSize: '1.1rem', color: '#fff', letterSpacing: '-0.02em' }}>
                  GoldBot24 <span style={{ color: '#fbbf24', fontSize: '0.8rem', fontWeight: 600 }}>• AI Gold Commander Pro</span>
                </div>
                <div style={{ fontSize: '0.72rem', color: '#fbbf24' }}>
                  100% Pure Gold Specialist (XAUUSD)
                </div>
              </div>
            </div>

            <p style={{ fontSize: '0.8rem', lineHeight: '1.6', color: 'var(--text-muted)', marginBottom: '1.2rem' }}>
              ระบบเทรดทองคำ AI อัตโนมัติเชื่อมต่อ MetaTrader 5 (FBS Broker) มุ่งเน้น Win Rate สูงสุด ด้วยโมเดล Fair Metering 1 บาทต่อ 1 ชั่วโมง คิดเวลาเฉพาะตอนเปิดบอท
            </p>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                fontSize: '0.72rem',
                padding: '3px 8px',
                borderRadius: '6px',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                color: '#10b981',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                fontWeight: 600
              }}>
                <CheckCircle2 size={12} />
                SlipOK Verified (#77585)
              </span>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                fontSize: '0.72rem',
                padding: '3px 8px',
                borderRadius: '6px',
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                fontWeight: 600
              }}>
                <Sparkles size={12} />
                Supabase Cloud Live
              </span>
            </div>
          </div>

          {/* Col 2: Navigation Links */}
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: '0.9rem', marginBottom: '1rem', letterSpacing: '0.02em' }}>
              เมนูนำทาง (Quick Links)
            </div>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
              <li>
                <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', textDecoration: 'none', transition: 'color 0.2s' }}>
                  <Bot size={14} color="#38bdf8" />
                  <span>เรดาร์พอร์ต MT5 สด (Live Telemetry)</span>
                </Link>
              </li>
              <li>
                <Link href="/store" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', textDecoration: 'none', transition: 'color 0.2s' }}>
                  <ShoppingBag size={14} color="#fbbf24" />
                  <span>ร้านค้าสั่งซื้อชั่วโมง (1 บาท/ชม.)</span>
                </Link>
              </li>
              <li>
                <Link href="/my-keys" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', textDecoration: 'none', transition: 'color 0.2s' }}>
                  <Key size={14} color="#10b981" />
                  <span>คลัง Product Key ของฉัน (Vault)</span>
                </Link>
              </li>
              <li>
                <Link href="/dashboard" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', textDecoration: 'none', transition: 'color 0.2s' }}>
                  <BarChart3 size={14} color="#a855f7" />
                  <span>กระเป๋าเวลา & สถิติรายแผน</span>
                </Link>
              </li>
              {isAdmin && (
                <li>
                  <Link href="/admin/analytics" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', textDecoration: 'none', transition: 'color 0.2s' }}>
                    <Shield size={14} color="#f43f5e" />
                    <span>Admin Analytics & คลังโปรโม</span>
                  </Link>
                </li>
              )}
            </ul>
          </div>

          {/* Col 3: 5 Gold Specialist Plans */}
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: '0.9rem', marginBottom: '1rem', letterSpacing: '0.02em' }}>
              5 แผนเทรดทองคำ (Gold Plans)
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.78rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span>⚡ Plan 0: SMC-LiquidityHunt</span>
                <span style={{ color: '#10b981', fontWeight: 600 }}>H1 S&R</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span>🎯 Plan 1: SR-SwingBounce</span>
                <span style={{ color: '#fbbf24', fontWeight: 600 }}>Divergence</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span>🌊 Plan 3: BB-H1-Reversion</span>
                <span style={{ color: '#38bdf8', fontWeight: 600 }}>2 STD Band</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span>📈 Plan 4: MA-Cross-Trend</span>
                <span style={{ color: '#a855f7', fontWeight: 600 }}>M15 / MA5x10</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0' }}>
                <span>👑 Plan 5: MA-Cross-H1-Trend</span>
                <span style={{ color: '#ffd700', fontWeight: 600 }}>H1 / H4 Anchor</span>
              </div>
            </div>
          </div>

          {/* Col 4: Desktop Application */}
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: '0.9rem', marginBottom: '1rem', letterSpacing: '0.02em' }}>
              ตัวโปรแกรมเทรด (Desktop Bot)
            </div>
            <div style={{
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(251, 191, 36, 0.25)',
              borderRadius: '12px',
              padding: '1rem',
              marginBottom: '0.85rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
                <Clock size={16} color="#fbbf24" />
                <span style={{ fontWeight: 700, color: '#fff', fontSize: '0.85rem' }}>AI_Gold_Commander_Pro</span>
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                เวอร์ชัน v2026.1003.0025 ติดตั้งลงบนคอมพิวเตอร์ Windows 10/11 หรือ VPS รันคู่กับ MT5 FBS
              </div>
            </div>

            <a
              href="/run_gui.bat"
              download
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.4rem',
                width: '100%',
                padding: '0.65rem 1rem',
                borderRadius: '8px',
                backgroundColor: 'rgba(251, 191, 36, 0.15)',
                color: '#fbbf24',
                border: '1px solid rgba(251, 191, 36, 0.4)',
                fontWeight: 700,
                fontSize: '0.82rem',
                textDecoration: 'none',
                transition: 'all 0.2s'
              }}
            >
              <span>ดาวน์โหลด Desktop Launcher</span>
              <ArrowUpRight size={14} />
            </a>
          </div>
        </div>

        {/* Bottom Bar */}
        <div style={{
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          paddingTop: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          fontSize: '0.78rem',
          color: 'var(--text-muted)'
        }}>
          <div>
            © 2026 <strong>GoldBot24</strong>. All rights reserved. • AI MetaTrader 5 Commander (FBS)
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
            <span>Fair Metering Model (1 THB / 1 Hour)</span>
            <span>•</span>
            <span style={{ color: '#fbbf24' }}>XAUUSD Gold Specialist</span>
            <span>•</span>
            <span>Build v2026.1003.0025</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
