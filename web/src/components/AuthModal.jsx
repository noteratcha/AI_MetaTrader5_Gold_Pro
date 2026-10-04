'use client';

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { X, Lock, Mail, User, ShieldCheck, Sparkles, AlertCircle, Loader2 } from 'lucide-react';

export default function AuthModal() {
  const { isAuthModalOpen, closeAuthModal, authModalTab, setAuthModalTab, login, register } = useAuth();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!email || !email.includes('@')) {
      setErrorMsg('กรุณากรอกอีเมลที่ถูกต้อง');
      return;
    }

    if (!password || password.length < 6) {
      setErrorMsg('รหัสผ่านต้องมีความยาวอย่างน้อย 6 ตัวอักษร');
      return;
    }

    if (authModalTab === 'register') {
      if (password !== confirmPassword) {
        setErrorMsg('รหัสผ่านยืนยันไม่ตรงกัน');
        return;
      }
    }

    setIsSubmitting(true);
    try {
      if (authModalTab === 'login') {
        await login(email, password);
      } else {
        await register(email, password, displayName);
      }
      // Reset form
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setDisplayName('');
    } catch (err) {
      setErrorMsg(err.message || 'เกิดข้อผิดพลาดในการดำเนินการ');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      zIndex: 100,
      backgroundColor: 'rgba(5, 7, 10, 0.85)',
      backdropFilter: 'blur(12px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1rem'
    }}>
      <div style={{
        backgroundColor: '#0d131c',
        border: '1px solid rgba(251, 191, 36, 0.4)',
        boxShadow: '0 0 40px rgba(251, 191, 36, 0.25), 0 20px 40px rgba(0, 0, 0, 0.8)',
        borderRadius: '20px',
        width: '100%',
        maxWidth: '460px',
        overflow: 'hidden',
        position: 'relative'
      }}>
        {/* Top Glow Ribbon */}
        <div style={{
          height: '4px',
          background: 'linear-gradient(90deg, #fbbf24 0%, #10b981 50%, #38bdf8 100%)'
        }}></div>

        {/* Close Button */}
        <button
          onClick={closeAuthModal}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '50%',
            width: '32px',
            height: '32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
          title="ปิด"
        >
          <X size={16} />
        </button>

        <div style={{ padding: '2rem' }}>
          {/* Brand & Title */}
          <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
            <div style={{
              width: '54px',
              height: '54px',
              borderRadius: '14px',
              overflow: 'hidden',
              margin: '0 auto 0.75rem auto',
              border: '1.5px solid rgba(251, 191, 36, 0.5)',
              boxShadow: '0 0 20px rgba(251, 191, 36, 0.3)',
              background: '#07090e'
            }}>
              <img src="/store_logo.png" alt="GoldBot24" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fff', margin: 0, letterSpacing: '-0.02em' }}>
              GoldBot24 <span style={{ color: '#fbbf24' }}>Passport</span>
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              เข้าสู่ระบบเพื่อควบคุมบอทเทรด MT5 และจัดการกระเป๋าเวลา
            </p>
          </div>

          {/* Switch Tabs (Login / Register) */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '6px',
            backgroundColor: 'rgba(255, 255, 255, 0.04)',
            padding: '4px',
            borderRadius: '10px',
            marginBottom: '1.5rem',
            border: '1px solid rgba(255, 255, 255, 0.06)'
          }}>
            <button
              type="button"
              onClick={() => { setAuthModalTab('login'); setErrorMsg(''); }}
              style={{
                padding: '8px',
                borderRadius: '8px',
                border: 'none',
                fontWeight: authModalTab === 'login' ? 700 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer',
                backgroundColor: authModalTab === 'login' ? 'rgba(251, 191, 36, 0.15)' : 'transparent',
                color: authModalTab === 'login' ? '#fbbf24' : 'var(--text-secondary)',
                boxShadow: authModalTab === 'login' ? '0 0 10px rgba(251, 191, 36, 0.2)' : 'none',
                transition: 'all 0.2s'
              }}
            >
              เข้าสู่ระบบ (Login)
            </button>
            <button
              type="button"
              onClick={() => { setAuthModalTab('register'); setErrorMsg(''); }}
              style={{
                padding: '8px',
                borderRadius: '8px',
                border: 'none',
                fontWeight: authModalTab === 'register' ? 700 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer',
                backgroundColor: authModalTab === 'register' ? 'rgba(251, 191, 36, 0.15)' : 'transparent',
                color: authModalTab === 'register' ? '#fbbf24' : 'var(--text-secondary)',
                boxShadow: authModalTab === 'register' ? '0 0 10px rgba(251, 191, 36, 0.2)' : 'none',
                transition: 'all 0.2s'
              }}
            >
              สมัครสมาชิก (Register)
            </button>
          </div>

          {/* Bonus Banner for Register */}
          {authModalTab === 'register' && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              borderRadius: '8px',
              backgroundColor: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#10b981',
              fontSize: '0.78rem',
              fontWeight: 600,
              marginBottom: '1.2rem'
            }}>
              <Sparkles size={14} />
              <span>โควต้าต้อนรับ: สมัครวันนี้รับทันที 48 ชั่วโมงเต็ม!</span>
            </div>
          )}

          {/* Error Alert */}
          {errorMsg && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              borderRadius: '8px',
              backgroundColor: 'rgba(244, 63, 94, 0.15)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              color: '#f43f5e',
              fontSize: '0.8rem',
              marginBottom: '1.2rem'
            }}>
              <AlertCircle size={15} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {authModalTab === 'register' && (
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '5px' }}>
                  ชื่อเทรดเดอร์ / Display Name
                </label>
                <div style={{ position: 'relative' }}>
                  <User size={15} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="เช่น Gold Master Aom"
                    style={{
                      width: '100%',
                      padding: '10px 12px 10px 36px',
                      borderRadius: '8px',
                      backgroundColor: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid var(--border-subtle)',
                      color: '#fff',
                      fontSize: '0.85rem',
                      outline: 'none'
                    }}
                  />
                </div>
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '5px' }}>
                อีเมล (Email)
              </label>
              <div style={{ position: 'relative' }}>
                <Mail size={15} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="yourname@gmail.com"
                  style={{
                    width: '100%',
                    padding: '10px 12px 10px 36px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--border-subtle)',
                    color: '#fff',
                    fontSize: '0.85rem',
                    outline: 'none'
                  }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '5px' }}>
                รหัสผ่าน (Password)
              </label>
              <div style={{ position: 'relative' }}>
                <Lock size={15} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="อย่างน้อย 6 ตัวอักษร"
                  style={{
                    width: '100%',
                    padding: '10px 12px 10px 36px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--border-subtle)',
                    color: '#fff',
                    fontSize: '0.85rem',
                    outline: 'none'
                  }}
                />
              </div>
            </div>

            {authModalTab === 'register' && (
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '5px' }}>
                  ยืนยันรหัสผ่าน (Confirm Password)
                </label>
                <div style={{ position: 'relative' }}>
                  <ShieldCheck size={15} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="พิมพ์รหัสผ่านอีกครั้ง"
                    style={{
                      width: '100%',
                      padding: '10px 12px 10px 36px',
                      borderRadius: '8px',
                      backgroundColor: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid var(--border-subtle)',
                      color: '#fff',
                      fontSize: '0.85rem',
                      outline: 'none'
                    }}
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                width: '100%',
                padding: '12px',
                borderRadius: '10px',
                backgroundColor: '#fbbf24',
                color: '#07090e',
                border: 'none',
                fontWeight: 800,
                fontSize: '0.9rem',
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
                opacity: isSubmitting ? 0.7 : 1,
                marginTop: '0.5rem',
                boxShadow: '0 0 20px rgba(251, 191, 36, 0.3)',
                transition: 'all 0.2s'
              }}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>กำลังดำเนินการ...</span>
                </>
              ) : authModalTab === 'login' ? (
                <span>เข้าสู่ระบบ (Login)</span>
              ) : (
                <span>สร้างบัญชีผู้ใช้งาน (Register)</span>
              )}
            </button>
          </form>

          {/* Footer Helper */}
          <div style={{ marginTop: '1.2rem', textAlign: 'center', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {authModalTab === 'login' ? (
              <span>
                ยังไม่มีบัญชีใช้งาน?{' '}
                <button
                  type="button"
                  onClick={() => { setAuthModalTab('register'); setErrorMsg(''); }}
                  style={{ background: 'none', border: 'none', color: '#fbbf24', fontWeight: 700, cursor: 'pointer', padding: 0 }}
                >
                  สมัครสมาชิกใหม่ฟรี
                </button>
              </span>
            ) : (
              <span>
                มีบัญชี GoldBot24 อยู่แล้ว?{' '}
                <button
                  type="button"
                  onClick={() => { setAuthModalTab('login'); setErrorMsg(''); }}
                  style={{ background: 'none', border: 'none', color: '#fbbf24', fontWeight: 700, cursor: 'pointer', padding: 0 }}
                >
                  เข้าสู่ระบบที่นี่
                </button>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
