'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bot, ShoppingBag, Key, BarChart3, Shield, Clock, LogIn, UserPlus, LogOut, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const pathname = usePathname();
  const { user, openAuthModal, logout } = useAuth();

  const baseNavItems = [
    { href: '/', label: 'เรดาร์พอร์ต MT5', icon: Bot },
    { href: '/store', label: 'ซื้อชั่วโมง (1 บ./ชม.)', icon: ShoppingBag, badge: 'QR PromptPay' },
    { href: '/my-keys', label: 'คีย์ของฉัน', icon: Key },
    { href: '/dashboard', label: 'กระเป๋าเวลา & สถิติ', icon: BarChart3 },
  ];

  // ต้อง login ด้วย user admin เท่านั้น ถึงจะแสดงส่วน Admin Analytics
  const isAdmin = user && (user.role === 'admin' || user.isAdmin === true || user.email?.toLowerCase().startsWith('admin'));

  const navItems = isAdmin
    ? [...baseNavItems, { href: '/admin/analytics', label: 'Admin Analytics', icon: Shield, badge: 'Admin' }]
    : baseNavItems;

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      backdropFilter: 'blur(16px)',
      backgroundColor: 'rgba(7, 9, 14, 0.85)',
      borderBottom: '1px solid var(--border-subtle)',
      padding: '0.75rem 1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '1rem',
      flexWrap: 'wrap'
    }}>
      {/* Brand Logo */}
      <Link href="/" style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.6rem',
        textDecoration: 'none',
        color: 'var(--text-primary)'
      }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '10px',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1.5px solid rgba(251, 191, 36, 0.5)',
          boxShadow: '0 0 15px rgba(251, 191, 36, 0.4)',
          background: '#0d131a'
        }}>
          <img src="/store_logo.png" alt="GoldBot24 Logo" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: '1rem', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ color: '#fbbf24' }}>GoldBot24</span>
            <span style={{ fontSize: '0.65rem', background: 'rgba(251, 191, 36, 0.15)', color: '#fbbf24', border: '1px solid rgba(251, 191, 36, 0.3)', padding: '1px 6px', borderRadius: '4px' }}>AI Commander Pro</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
            100% Pure Gold Specialist (XAUUSD)
          </div>
        </div>
      </Link>

      {/* Nav Links */}
      <nav style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.45rem 0.85rem',
                borderRadius: '8px',
                fontSize: '0.82rem',
                fontWeight: isActive ? 600 : 500,
                textDecoration: 'none',
                color: isActive ? '#fbbf24' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'rgba(251, 191, 36, 0.12)' : 'transparent',
                border: isActive ? '1px solid rgba(251, 191, 36, 0.25)' : '1px solid transparent',
                transition: 'all 0.2s ease'
              }}
            >
              <Icon size={15} color={isActive ? '#fbbf24' : '#94a3b8'} />
              <span>{item.label}</span>
              {item.badge && (
                <span style={{
                  fontSize: '0.65rem',
                  padding: '1px 5px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(16, 185, 129, 0.15)',
                  color: '#10b981',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  fontWeight: 600
                }}>
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Right Quick Action: Auth & Launcher */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Link
              href="/dashboard"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.35rem 0.75rem',
                borderRadius: '8px',
                backgroundColor: 'rgba(251, 191, 36, 0.12)',
                border: '1px solid rgba(251, 191, 36, 0.3)',
                color: '#fbbf24',
                fontSize: '0.78rem',
                fontWeight: 700,
                textDecoration: 'none'
              }}
              title="ไปยังกระเป๋าเวลา & แดชบอร์ด"
            >
              <User size={13} />
              <span>{user.displayName || user.email.split('@')[0]}</span>
              <span style={{
                backgroundColor: '#fbbf24',
                color: '#07090e',
                padding: '1px 6px',
                borderRadius: '4px',
                fontSize: '0.72rem',
                fontWeight: 800
              }}>
                {(user.hoursRemaining || 0).toFixed(2)} ชม.
              </span>
            </Link>
            <button
              onClick={logout}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                padding: '0.35rem 0.6rem',
                borderRadius: '8px',
                backgroundColor: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.25)',
                color: '#f43f5e',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
              title="ออกจากระบบ"
            >
              <LogOut size={13} />
              <span>ออก</span>
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <button
              onClick={() => openAuthModal('login')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.35rem 0.7rem',
                borderRadius: '8px',
                backgroundColor: 'transparent',
                border: '1px solid rgba(251, 191, 36, 0.4)',
                color: '#fbbf24',
                fontSize: '0.78rem',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              <LogIn size={13} />
              <span>เข้าสู่ระบบ</span>
            </button>
            <button
              onClick={() => openAuthModal('register')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.35rem 0.7rem',
                borderRadius: '8px',
                backgroundColor: '#fbbf24',
                border: 'none',
                color: '#07090e',
                fontSize: '0.78rem',
                fontWeight: 800,
                cursor: 'pointer',
                boxShadow: '0 0 10px rgba(251, 191, 36, 0.3)'
              }}
            >
              <UserPlus size={13} />
              <span>สมัครสมาชิก</span>
            </button>
          </div>
        )}

        <a
          href="/run_gui.bat"
          download
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            padding: '0.35rem 0.65rem',
            borderRadius: '8px',
            fontSize: '0.75rem',
            fontWeight: 600,
            textDecoration: 'none',
            color: '#00f2fe',
            backgroundColor: 'rgba(0, 242, 254, 0.08)',
            border: '1px solid rgba(0, 242, 254, 0.25)',
          }}
          title="ดาวน์โหลดตัวเปิดโปรแกรมสำหรับ Windows"
        >
          <Clock size={12} />
          <span>Desktop</span>
        </a>
      </div>
    </header>
  );
}
