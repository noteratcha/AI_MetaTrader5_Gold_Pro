'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { KeyRound, Lock, Mail, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Alert, Spinner } from '../../components/ui';

async function post(path, body) {
  const res = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.success === false) throw new Error(data.error || `เกิดข้อผิดพลาด (HTTP ${res.status})`);
  return data;
}

export default function ForgotPasswordPage() {
  const router = useRouter();
  const { completeLogin } = useAuth();
  const [step, setStep] = useState('email'); // email | code | done
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    const prefill = new URLSearchParams(window.location.search).get('email');
    if (prefill) setEmail(prefill);
  }, []);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(id);
  }, [cooldown]);

  const requestCode = async (e) => {
    e?.preventDefault();
    setBusy(true);
    setStatus(null);
    try {
      const res = await post('/api/auth/forgot-password', { email: email.trim() });
      setStatus({ type: 'success', message: res.message });
      setStep('code');
      setCooldown(60);
    } catch (err) {
      setStatus({ type: 'error', message: err.message });
    } finally {
      setBusy(false);
    }
  };

  const resetPassword = async (e) => {
    e.preventDefault();
    if (pw !== pw2) return setStatus({ type: 'error', message: 'รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน' });
    setBusy(true);
    setStatus(null);
    try {
      const res = await post('/api/auth/reset-password', { email: email.trim(), code, newPassword: pw });
      completeLogin(res.token, res.user);
      setStep('done');
      setStatus({ type: 'success', message: 'ตั้งรหัสผ่านใหม่สำเร็จ และเข้าสู่ระบบให้แล้ว' });
      setTimeout(() => router.push('/dashboard'), 1500);
    } catch (err) {
      setStatus({ type: 'error', message: err.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container container-narrow page">
      <div className="card card-pad" style={{ maxWidth: 460, margin: '0 auto', padding: '32px 28px' }}>
        <div className="center" style={{ marginBottom: 20 }}>
          <div className="empty-icon" style={{ background: 'var(--gold-soft)', color: 'var(--gold)' }}>
            <KeyRound size={26} />
          </div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700 }}>ลืมรหัสผ่าน</h1>
          <p className="small muted">
            {step === 'email' && 'กรอกอีเมลที่ใช้สมัคร เราจะส่งรหัสยืนยัน 6 หลักไปให้'}
            {step === 'code' && `กรอกรหัสยืนยันที่ส่งไปที่ ${email} และตั้งรหัสผ่านใหม่`}
            {step === 'done' && 'กำลังพาไปหน้ากระเป๋าเวลา...'}
          </p>
        </div>

        {status && (
          <div style={{ marginBottom: 14 }}>
            <Alert type={status.type}>{status.message}</Alert>
          </div>
        )}

        {step === 'email' && (
          <form className="stack" style={{ gap: 14 }} onSubmit={requestCode}>
            <label className="field">
              <span className="label">อีเมล</span>
              <span className="input-icon">
                <Mail size={16} />
                <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" autoFocus required />
              </span>
            </label>
            <button className="btn btn-primary btn-lg btn-block" disabled={busy || !email.includes('@')}>
              {busy && <Spinner />} ส่งรหัสยืนยัน
            </button>
          </form>
        )}

        {step === 'code' && (
          <form className="stack" style={{ gap: 14 }} onSubmit={resetPassword}>
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
            <label className="field">
              <span className="label">รหัสผ่านใหม่</span>
              <span className="input-icon">
                <Lock size={16} />
                <input className="input" type="password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="อย่างน้อย 6 ตัวอักษร" autoComplete="new-password" />
              </span>
            </label>
            <label className="field">
              <span className="label">ยืนยันรหัสผ่านใหม่</span>
              <span className="input-icon">
                <ShieldCheck size={16} />
                <input className="input" type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} autoComplete="new-password" />
              </span>
            </label>
            <button className="btn btn-primary btn-lg btn-block" disabled={busy || code.length !== 6 || pw.length < 6}>
              {busy && <Spinner />} ตั้งรหัสผ่านใหม่
            </button>
            <div className="row-between small">
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setStep('email'); setStatus(null); }}>
                เปลี่ยนอีเมล
              </button>
              <button type="button" className="btn btn-ghost btn-sm" disabled={cooldown > 0 || busy} onClick={requestCode}>
                {cooldown > 0 ? `ส่งรหัสอีกครั้งได้ใน ${cooldown} วินาที` : 'ส่งรหัสอีกครั้ง'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
