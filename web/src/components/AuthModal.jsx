'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Gift, Lock, Mail, ShieldCheck, User, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Alert, Spinner } from './ui';

export default function AuthModal() {
  const { isAuthModalOpen, closeAuthModal, authModalTab, setAuthModalTab, login, register } = useAuth();
  const [form, setForm] = useState({ email: '', password: '', confirm: '', displayName: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const isRegister = authModalTab === 'register';

  useEffect(() => {
    if (!isAuthModalOpen) return;
    setError('');
    const onKey = (e) => e.key === 'Escape' && closeAuthModal();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isAuthModalOpen, closeAuthModal]);

  if (!isAuthModalOpen) return null;

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const switchTab = (tab) => {
    setAuthModalTab(tab);
    setError('');
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) return setError('กรุณากรอกอีเมลที่ถูกต้อง');
    if (form.password.length < 6) return setError('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร');
    if (isRegister && form.password !== form.confirm) return setError('รหัสผ่านยืนยันไม่ตรงกัน');

    setSubmitting(true);
    try {
      if (isRegister) await register(form.email.trim(), form.password, form.displayName.trim());
      else await login(form.email.trim(), form.password);
      setForm({ email: '', password: '', confirm: '', displayName: '' });
    } catch (err) {
      setError(err.message || 'เกิดข้อผิดพลาด กรุณาลองใหม่');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && closeAuthModal()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <button className="btn btn-ghost btn-icon modal-close" onClick={closeAuthModal} aria-label="ปิด">
          <X size={18} />
        </button>

        <div style={{ padding: '32px 28px 28px' }}>
          <div className="center" style={{ marginBottom: 22 }}>
            <span className="logo-mark" style={{ display: 'flex', width: 52, height: 52, margin: '0 auto 12px', borderRadius: 14 }}>
              <img src="/store_logo.png" alt="" />
            </span>
            <h2 id="auth-title" style={{ fontSize: '1.3rem', fontWeight: 700 }}>
              {isRegister ? 'สร้างบัญชี GoldBot24' : 'ยินดีต้อนรับกลับมา'}
            </h2>
            <p className="small muted">{isRegister ? 'ใช้บัญชีเดียวกันทั้งเว็บและโปรแกรม Desktop' : 'เข้าสู่ระบบเพื่อดูพอร์ตและจัดการชั่วโมงใช้งาน'}</p>
          </div>

          <div className="segmented" role="tablist">
            <button role="tab" aria-selected={!isRegister} className={!isRegister ? 'is-active' : ''} onClick={() => switchTab('login')}>
              เข้าสู่ระบบ
            </button>
            <button role="tab" aria-selected={isRegister} className={isRegister ? 'is-active' : ''} onClick={() => switchTab('register')}>
              สมัครสมาชิก
            </button>
          </div>

          <form onSubmit={onSubmit} className="stack" style={{ gap: 14, marginTop: 18 }} noValidate>
            {isRegister && (
              <div className="alert alert-gold">
                <Gift size={16} />
                <div>สมัครวันนี้รับเวลาใช้งานฟรี 48 ชั่วโมง</div>
              </div>
            )}
            {error && <Alert type="error">{error}</Alert>}

            {isRegister && (
              <label className="field">
                <span className="label">ชื่อที่แสดง</span>
                <span className="input-icon">
                  <User size={16} />
                  <input className="input" value={form.displayName} onChange={set('displayName')} placeholder="เช่น Gold Trader" maxLength={40} autoComplete="nickname" />
                </span>
              </label>
            )}

            <label className="field">
              <span className="label">อีเมล</span>
              <span className="input-icon">
                <Mail size={16} />
                <input className="input" type="email" value={form.email} onChange={set('email')} placeholder="you@example.com" autoComplete="email" autoFocus />
              </span>
            </label>

            <label className="field">
              <span className="label">รหัสผ่าน</span>
              <span className="input-icon">
                <Lock size={16} />
                <input
                  className="input"
                  type="password"
                  value={form.password}
                  onChange={set('password')}
                  placeholder="อย่างน้อย 6 ตัวอักษร"
                  autoComplete={isRegister ? 'new-password' : 'current-password'}
                />
              </span>
            </label>

            {!isRegister && (
              <div style={{ textAlign: 'right', marginTop: -6 }}>
                <Link href="/forgot-password" className="small text-sky" onClick={closeAuthModal}>
                  ลืมรหัสผ่าน?
                </Link>
              </div>
            )}

            {isRegister && (
              <label className="field">
                <span className="label">ยืนยันรหัสผ่าน</span>
                <span className="input-icon">
                  <ShieldCheck size={16} />
                  <input className="input" type="password" value={form.confirm} onChange={set('confirm')} placeholder="พิมพ์รหัสผ่านอีกครั้ง" autoComplete="new-password" />
                </span>
              </label>
            )}

            <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={submitting} style={{ marginTop: 4 }}>
              {submitting ? <Spinner /> : null}
              {submitting ? 'กำลังดำเนินการ...' : isRegister ? 'สร้างบัญชี' : 'เข้าสู่ระบบ'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
