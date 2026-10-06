'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Gift, Lock, Mail, MailCheck, ShieldCheck, User, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Alert, Spinner } from './ui';

export default function AuthModal() {
  const { isAuthModalOpen, closeAuthModal, authModalTab, setAuthModalTab, login, register } = useAuth();
  const [form, setForm] = useState({ email: '', password: '', confirm: '', displayName: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  // ขั้นยืนยันอีเมลตอนสมัคร: null = กรอกข้อมูล, { message } = รอกรอกรหัส 6 หลัก
  const [verify, setVerify] = useState(null);
  const [code, setCode] = useState('');
  const [notice, setNotice] = useState('');
  const [cooldown, setCooldown] = useState(0);
  const isRegister = authModalTab === 'register';

  useEffect(() => {
    if (!isAuthModalOpen) return;
    setError('');
    const onKey = (e) => e.key === 'Escape' && closeAuthModal();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isAuthModalOpen, closeAuthModal]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(id);
  }, [cooldown]);

  if (!isAuthModalOpen) return null;

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const switchTab = (tab) => {
    setAuthModalTab(tab);
    setError('');
    setVerify(null);
    setCode('');
    setNotice('');
  };

  const requestCode = async () => {
    const res = await register(form.email.trim(), form.password, form.displayName.trim());
    setVerify(res);
    setNotice(res.message);
    setCode('');
    setCooldown(60);
  };

  const resend = async () => {
    setError('');
    setSubmitting(true);
    try {
      await requestCode();
    } catch (err) {
      setError(err.message || 'ส่งรหัสไม่สำเร็จ');
    } finally {
      setSubmitting(false);
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (isRegister && verify) {
      if (code.length !== 6) return setError('กรุณากรอกรหัสยืนยัน 6 หลักจากอีเมล');
      setSubmitting(true);
      try {
        await register(form.email.trim(), form.password, form.displayName.trim(), code);
        setForm({ email: '', password: '', confirm: '', displayName: '' });
        setVerify(null);
        setCode('');
        setNotice('');
      } catch (err) {
        setError(err.message || 'ยืนยันรหัสไม่สำเร็จ');
      } finally {
        setSubmitting(false);
      }
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) return setError('กรุณากรอกอีเมลที่ถูกต้อง');
    if (form.password.length < 6) return setError('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร');
    if (isRegister && form.password !== form.confirm) return setError('รหัสผ่านยืนยันไม่ตรงกัน');

    setSubmitting(true);
    try {
      if (isRegister) {
        await requestCode();
      } else {
        await login(form.email.trim(), form.password);
        setForm({ email: '', password: '', confirm: '', displayName: '' });
      }
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
            <p className="small muted">{isRegister ? 'ใช้บัญชีเดียวกันทั้งเว็บและโปรแกรม AI Gold Commander Pro' : 'เข้าสู่ระบบเพื่อดูพอร์ตและจัดการชั่วโมงใช้งาน'}</p>
          </div>

          <div className="segmented" role="tablist">
            <button role="tab" aria-selected={!isRegister} className={!isRegister ? 'is-active' : ''} onClick={() => switchTab('login')}>
              เข้าสู่ระบบ
            </button>
            <button role="tab" aria-selected={isRegister} className={isRegister ? 'is-active' : ''} onClick={() => switchTab('register')}>
              สมัครสมาชิก
            </button>
          </div>

          {isRegister && verify ? (
            <form onSubmit={onSubmit} className="stack" style={{ gap: 14, marginTop: 18 }} noValidate>
              <div className="alert alert-gold">
                <MailCheck size={16} />
                <div>
                  {notice}
                  <div className="small muted" style={{ marginTop: 4 }}>
                    ส่งไปที่ <b>{form.email.trim()}</b>
                  </div>
                </div>
              </div>
              {error && <Alert type="error">{error}</Alert>}
              <label className="field">
                <span className="label">รหัสยืนยัน 6 หลัก</span>
                <input
                  className="input input-key"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="••••••"
                  autoFocus
                />
              </label>
              <button type="submit" className="btn btn-primary btn-lg btn-block" disabled={submitting || code.length !== 6}>
                {submitting ? <Spinner /> : null}
                {submitting ? 'กำลังตรวจสอบ...' : 'ยืนยันและสร้างบัญชี'}
              </button>
              <div className="row-between small">
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setVerify(null); setError(''); setCode(''); }}>
                  แก้ไขข้อมูล
                </button>
                <button type="button" className="btn btn-ghost btn-sm" disabled={cooldown > 0 || submitting} onClick={resend}>
                  {cooldown > 0 ? `ส่งรหัสอีกครั้งได้ใน ${cooldown} วินาที` : 'ส่งรหัสอีกครั้ง'}
                </button>
              </div>
            </form>
          ) : (
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
              {submitting ? 'กำลังดำเนินการ...' : isRegister ? 'ส่งรหัสยืนยันทางอีเมล' : 'เข้าสู่ระบบ'}
            </button>
          </form>
          )}
        </div>
      </div>
    </div>
  );
}
