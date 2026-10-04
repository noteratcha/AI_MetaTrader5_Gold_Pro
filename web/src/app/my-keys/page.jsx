'use client';

import React, { useState, useEffect } from 'react';
import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import Link from 'next/link';
import { 
  Key, 
  Copy, 
  Check, 
  Clock, 
  ShoppingBag, 
  ShieldCheck, 
  ArrowRight, 
  Sparkles,
  Inbox,
  Lock,
  LogIn,
  UserPlus
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { getSupabase } from '../../lib/supabase';

export default function MyKeysPage() {
  const { user, isLoading, openAuthModal, redeemKey } = useAuth();
  const [keys, setKeys] = useState([]);
  const [copiedKey, setCopiedKey] = useState(null);
  const [redeemingKey, setRedeemingKey] = useState(null);
  const [redeemSuccess, setRedeemSuccess] = useState(null);

  useEffect(() => {
    if (user && user.email) {
      loadUserKeys();
    }
  }, [user]);

  const loadUserKeys = async () => {
    try {
      // 1. โหลดคีย์ที่บันทึกใน LocalStorage จากการสั่งซื้อ
      const stored = JSON.parse(localStorage.getItem('my_product_keys') || '[]');
      
      // 2. ดึงคีย์จริงเพิ่มเติมจาก Supabase Cloud
      const supabase = getSupabase();
      if (supabase && user && user.email) {
        const { data: cloudKeys } = await supabase
          .from('product_keys')
          .select('*')
          .order('purchased_at', { ascending: false });

        if (cloudKeys && cloudKeys.length > 0) {
          // รวมและคัดกรองเฉพาะคีย์ที่เกี่ยวข้อง
          const merged = [...stored];
          for (const ck of cloudKeys) {
            if (!merged.find(k => k.keyCode === ck.key_code)) {
              merged.push({
                keyCode: ck.key_code,
                hours: Number(ck.hours) || 0,
                price: Number(ck.price_thb) || 0,
                orderId: ck.order_id || 'PROD-KEY',
                packageName: `${ck.hours} Hours`,
                status: ck.is_used || ck.status === 'REDEEMED' ? 'REDEEMED' : 'UNUSED',
                purchasedAt: ck.purchased_at ? new Date(ck.purchased_at).toLocaleString('th-TH') : '-'
              });
            }
          }
          setKeys(merged);
          return;
        }
      }
      setKeys(stored);
    } catch (e) {
      console.warn('Error loading keys:', e);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(text);
    setTimeout(() => setCopiedKey(null), 2500);
  };

  const handleInstantRedeem = async (keyCode) => {
    setRedeemingKey(keyCode);
    setRedeemSuccess(null);
    try {
      const res = await redeemKey(keyCode);
      setRedeemSuccess(`เติมคีย์ ${keyCode} สำเร็จ! ได้รับ +${res.hoursAdded} ชม.`);
      // อัปเดตสถานะในรายการ
      setKeys(prev => prev.map(k => k.keyCode === keyCode ? { ...k, status: 'REDEEMED' } : k));
      const stored = JSON.parse(localStorage.getItem('my_product_keys') || '[]');
      const updated = stored.map(k => k.keyCode === keyCode ? { ...k, status: 'REDEEMED' } : k);
      localStorage.setItem('my_product_keys', JSON.stringify(updated));
    } catch (err) {
      alert(err.message || 'ไม่สามารถเติมคีย์ได้');
    } finally {
      setRedeemingKey(null);
    }
  };

  // ถ้ายังไม่ Login ให้แสดงหน้าจอบังคับ Login ก่อนเข้าถึงคลังคีย์
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
              เข้าสู่ระบบเพื่อดูคลัง Product Key
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6', marginBottom: '2rem' }}>
              รหัสบัตรเติมชั่วโมงและประวัติการสั่งซื้อของคุณจะถูกเก็บรักษาอย่างปลอดภัยในบัญชีของคุณ กรุณาเข้าสู่ระบบเพื่อตรวจสอบ
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
                <span>สมัครสมาชิกใหม่ฟรี</span>
              </button>
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

      <main style={{ maxWidth: '1080px', margin: '0 auto', padding: '2.5rem 1.5rem', width: '100%' }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '2.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              width: '52px',
              height: '52px',
              borderRadius: '14px',
              overflow: 'hidden',
              border: '1.5px solid rgba(251, 191, 36, 0.5)',
              boxShadow: '0 0 15px rgba(251, 191, 36, 0.3)',
              background: '#0d131a',
              flexShrink: 0
            }}>
              <img src="/app_icon.png" alt="AI Gold Commander Pro" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fbbf24', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>
                <Key size={16} />
                <span>GoldBot24 • Product Key Vault (AI Gold Commander Pro)</span>
              </div>
              <h1 style={{ fontSize: '2rem', fontWeight: 800, letterSpacing: '-0.02em', margin: 0 }}>
                คลัง Product Key ของคุณ ({user?.displayName || user?.email})
              </h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: '4px', margin: 0 }}>
                รหัส 24 หลักทั้งหมดที่คุณเคยสั่งซื้อ สามารถนำไปกรอกบน Desktop GUI หรือกดเติมเวลาเข้าบัญชีนี้ได้ทันที
              </p>
            </div>
          </div>

          <Link
            href="/store"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.65rem 1.1rem',
              borderRadius: '10px',
              backgroundColor: '#fbbf24',
              color: '#07090e',
              textDecoration: 'none',
              fontWeight: 700,
              fontSize: '0.85rem',
              boxShadow: '0 0 15px rgba(251, 191, 36, 0.3)',
              transition: 'all 0.2s'
            }}
          >
            <ShoppingBag size={16} />
            <span>+ สั่งซื้อชั่วโมงเพิ่ม</span>
          </Link>
        </div>

        {redeemSuccess && (
          <div style={{
            padding: '0.85rem 1.2rem',
            borderRadius: '10px',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            color: '#10b981',
            fontSize: '0.88rem',
            fontWeight: 600,
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <Sparkles size={16} />
            <span>{redeemSuccess}</span>
          </div>
        )}

        {/* Product Keys List */}
        {keys.length === 0 ? (
          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '16px',
            padding: '4rem 2rem',
            textAlign: 'center',
            color: 'var(--text-secondary)'
          }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: '50%',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.25rem auto'
            }}>
              <Inbox size={32} color="var(--text-muted)" />
            </div>
            <h3 style={{ color: '#fff', fontSize: '1.2rem', fontWeight: 700, marginBottom: '0.5rem' }}>
              ยังไม่มี Product Key ในคลังของคุณ
            </h3>
            <p style={{ fontSize: '0.88rem', maxWidth: '420px', margin: '0 auto 1.75rem auto', lineHeight: '1.5' }}>
              เมื่อคุณสั่งซื้อแพ็กเกจชั่วโมงจากหน้าร้านค้า รหัส Product Key 24 หลักจะถูกนำมาเก็บไว้ที่นี่อัตโนมัติ
            </p>
            <Link
              href="/store"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.5rem',
                borderRadius: '10px',
                backgroundColor: '#fbbf24',
                color: '#07090e',
                fontWeight: 800,
                fontSize: '0.88rem',
                textDecoration: 'none'
              }}
            >
              <span>ไปที่ร้านค้าเพื่อสั่งซื้อแพ็กเกจ</span>
              <ArrowRight size={16} />
            </Link>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {keys.map((k, idx) => {
              const isUsed = k.status === 'REDEEMED';
              return (
                <div
                  key={idx}
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: isUsed ? '1px solid var(--border-subtle)' : '1px solid rgba(251, 191, 36, 0.4)',
                    borderRadius: '14px',
                    padding: '1.5rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '1rem',
                    position: 'relative',
                    overflow: 'hidden',
                    boxShadow: isUsed ? 'none' : '0 0 20px rgba(251, 191, 36, 0.08)'
                  }}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    flexWrap: 'wrap',
                    gap: '1rem'
                  }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
                        <span style={{ fontWeight: 800, fontSize: '1.1rem', color: '#fff' }}>
                          แพ็กเกจ {k.packageName}
                        </span>
                        <span style={{
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '6px',
                          backgroundColor: isUsed ? 'rgba(255, 255, 255, 0.06)' : 'rgba(16, 185, 129, 0.15)',
                          color: isUsed ? 'var(--text-muted)' : '#10b981',
                          border: isUsed ? '1px solid var(--border-subtle)' : '1px solid rgba(16, 185, 129, 0.3)'
                        }}>
                          {isUsed ? 'REDEEMED (ใช้งานแล้ว)' : 'UNUSED (พร้อมใช้งาน)'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        คำสั่งซื้อ: {k.orderId} • สั่งซื้อเมื่อ: {k.purchasedAt}
                      </div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>
                        +{k.hours} ชม.
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        ราคา ฿{k.price.toFixed(2)} THB
                      </div>
                    </div>
                  </div>

                  {/* Key Display & Actions */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '10px',
                    padding: '0.75rem 1rem',
                    flexWrap: 'wrap',
                    gap: '0.75rem'
                  }}>
                    <div style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '1.05rem',
                      fontWeight: 700,
                      color: isUsed ? 'var(--text-muted)' : '#fbbf24',
                      letterSpacing: '0.05em'
                    }}>
                      {k.keyCode}
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        onClick={() => copyToClipboard(k.keyCode)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          padding: '0.45rem 0.85rem',
                          borderRadius: '8px',
                          backgroundColor: copiedKey === k.keyCode ? '#10b981' : 'rgba(255, 255, 255, 0.08)',
                          color: copiedKey === k.keyCode ? '#fff' : 'var(--text-primary)',
                          border: '1px solid var(--border-subtle)',
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                          transition: 'all 0.2s'
                        }}
                      >
                        {copiedKey === k.keyCode ? <Check size={14} /> : <Copy size={14} />}
                        <span>{copiedKey === k.keyCode ? 'คัดลอกแล้ว!' : 'คัดลอกคีย์'}</span>
                      </button>

                      {!isUsed && (
                        <button
                          onClick={() => handleInstantRedeem(k.keyCode)}
                          disabled={redeemingKey === k.keyCode}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            padding: '0.45rem 0.85rem',
                            borderRadius: '8px',
                            backgroundColor: '#fbbf24',
                            color: '#07090e',
                            border: 'none',
                            fontSize: '0.8rem',
                            fontWeight: 700,
                            cursor: 'pointer',
                            boxShadow: '0 0 10px rgba(251, 191, 36, 0.2)'
                          }}
                        >
                          <span>{redeemingKey === k.keyCode ? 'กำลังเติม...' : 'เติมเข้าบัญชีนี้'}</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
