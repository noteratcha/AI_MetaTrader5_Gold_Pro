'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, BarChart3, CalendarDays, Download, Key, LogIn, LogOut, Menu, Shield, ShoppingBag, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { formatHHMM } from '../lib/format';

const NAV_ITEMS = [
  { href: '/', label: 'พอร์ตสด', icon: Activity },
  { href: '/dashboard', label: 'กระเป๋าเวลา', icon: BarChart3 },
  { href: '/calendar', label: 'ปฏิทินข่าว', icon: CalendarDays },
  { href: '/store', label: 'ซื้อชั่วโมง', icon: ShoppingBag },
  { href: '/my-keys', label: 'คีย์ของฉัน', icon: Key },
];

export default function Navbar() {
  const pathname = usePathname();
  const { user, isAdmin, openAuthModal, logout } = useAuth();
  const [open, setOpen] = useState(false);

  useEffect(() => setOpen(false), [pathname]);

  const items = isAdmin ? [...NAV_ITEMS, { href: '/admin/analytics', label: 'Admin', icon: Shield }] : NAV_ITEMS;
  const hours = Number(user?.hoursRemaining) || 0;

  return (
    <header className="nav">
      <div className="container container-wide nav-inner">
        <Link href="/" className="nav-brand" aria-label="GoldBot24 หน้าแรก">
          <span className="logo-mark">
            <img src="/store_logo.png" alt="" />
          </span>
          <span>
            <span className="nav-brand-name">
              Gold<span className="text-gold">Bot24</span>
            </span>
            <span className="nav-brand-sub">AI Gold Commander Pro · XAUUSD</span>
          </span>
        </Link>

        <nav className={`nav-links ${open ? 'is-open' : ''}`} aria-label="เมนูหลัก">
          {items.map(({ href, label, icon: Icon }) => {
            const active = href === '/' ? pathname === '/' : pathname?.startsWith(href);
            return (
              <Link key={href} href={href} className={`nav-link ${active ? 'is-active' : ''}`} aria-current={active ? 'page' : undefined}>
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
          <div className="nav-mobile-auth">
            {user ? (
              <button className="btn btn-danger btn-block" onClick={logout}>
                <LogOut size={16} /> ออกจากระบบ
              </button>
            ) : (
              <button className="btn btn-primary btn-block" onClick={() => openAuthModal('login')}>
                <LogIn size={16} /> เข้าสู่ระบบ
              </button>
            )}
          </div>
        </nav>

        <div className="nav-actions">
          <Link href="/download" className={`btn btn-outline-gold btn-sm nav-download ${pathname === '/download' ? 'is-active' : ''}`} title="ดาวน์โหลดโปรแกรมเวอร์ชันล่าสุด">
            <Download size={15} />
            <span className="nav-download-label">ดาวน์โหลด</span>
          </Link>
          {user ? (
            <>
              <Link href="/dashboard" className="nav-user" title="กระเป๋าเวลาของฉัน">
                <span className="nav-avatar">{(user.displayName || user.email || '?').slice(0, 1).toUpperCase()}</span>
                <span className="nav-user-meta">
                  <span className="nav-user-name">{user.displayName || user.email}</span>
                  <span className={`nav-user-hours mono ${hours <= 0 ? 'text-red' : 'text-gold'}`}>{formatHHMM(hours)} ชม.</span>
                </span>
              </Link>
              <button className="btn btn-ghost btn-icon nav-desktop-only" onClick={logout} title="ออกจากระบบ" aria-label="ออกจากระบบ">
                <LogOut size={17} />
              </button>
            </>
          ) : (
            <>
              <button className="btn btn-ghost btn-sm nav-desktop-only" onClick={() => openAuthModal('login')}>
                เข้าสู่ระบบ
              </button>
              <button className="btn btn-primary btn-sm" onClick={() => openAuthModal('register')}>
                สมัครฟรี
              </button>
            </>
          )}
          <button className="btn btn-ghost btn-icon nav-toggle" onClick={() => setOpen((v) => !v)} aria-label="เปิดเมนู" aria-expanded={open}>
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

    </header>
  );
}
