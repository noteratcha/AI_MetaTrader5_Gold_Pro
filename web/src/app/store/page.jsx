'use client';

import React, { useState, useEffect } from 'react';
import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import { 
  ShoppingBag, 
  Sparkles, 
  QrCode, 
  CheckCircle2, 
  Copy, 
  Check, 
  Clock, 
  ShieldCheck, 
  ArrowRight,
  Flame,
  Crown,
  Zap,
  Info
} from 'lucide-react';

const PACKAGES = [
  {
    id: 1,
    name: 'Starter 50',
    hours: 50,
    bonus: 0,
    price: 50,
    badge: null,
    desc: 'เหมาะสำหรับทดลองรันบอททองคำจริง 2-3 วันต่อเนื่อง',
    icon: Zap,
    color: '#38bdf8'
  },
  {
    id: 2,
    name: 'Popular 100',
    hours: 100,
    bonus: 0,
    price: 100,
    badge: 'ขายดี 🔥',
    desc: 'ยอดนิยม รันได้ตลอด 1 สัปดาห์เต็ม ไม่พลาดทุกรอบสวิง H1',
    icon: Flame,
    color: '#f97316'
  },
  {
    id: 3,
    name: 'Value 300',
    hours: 300,
    bonus: 20,
    price: 300,
    badge: 'แถมฟรี 20 ชม. ✨',
    desc: 'สุดคุ้ม ได้เวลาเพิ่มพิเศษ 20 ชม. รวม 320 ชั่วโมงเต็ม',
    icon: Sparkles,
    color: '#10b981'
  },
  {
    id: 4,
    name: 'Marathon 500',
    hours: 500,
    bonus: 50,
    price: 500,
    badge: 'แถมฟรี 50 ชม. 👑',
    desc: 'สำหรับมืออาชีพ ได้เวลาเพิ่มพิเศษ 50 ชม. รวม 550 ชั่วโมง',
    icon: Crown,
    color: '#fbbf24'
  }
];

// ฟังก์ชันสร้าง Product Key สุ่ม 24 หลัก 6 กลุ่ม
function generateSecureProductKey() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let result = '';
  for (let g = 0; g < 6; g++) {
    let group = '';
    for (let i = 0; i < 4; i++) {
      group += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    result += (g === 0 ? '' : '-') + group;
  }
  return result;
}

export default function StorePage() {
  const [selectedPkg, setSelectedPkg] = useState(null);
  const [orderModalOpen, setOrderModalOpen] = useState(false);
  const [orderState, setOrderState] = useState('PENDING'); // PENDING, PAID
  const [countdown, setCountdown] = useState(600); // 10 mins
  const [currentOrder, setCurrentOrder] = useState(null);
  const [copied, setCopied] = useState(false);
  const [isVerifyingSlip, setIsVerifyingSlip] = useState(false);
  const [slipMessage, setSlipMessage] = useState('');

  // Countdown timer
  useEffect(() => {
    let timer = null;
    if (orderModalOpen && orderState === 'PENDING' && countdown > 0) {
      timer = setInterval(() => {
        setCountdown((prev) => prev - 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [orderModalOpen, orderState, countdown]);

  // Polling order payment status from Supabase
  useEffect(() => {
    if (!orderModalOpen || orderState !== 'PENDING' || !currentOrder?.orderId) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/checkout/check-status?order_id=${currentOrder.orderId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.is_paid && data.generated_key_code) {
            const existingKeys = JSON.parse(localStorage.getItem('my_product_keys') || '[]');
            const keyAlreadyExists = existingKeys.some(k => k.keyCode === data.generated_key_code);
            if (!keyAlreadyExists) {
              const newKeyRecord = {
                keyCode: data.generated_key_code,
                hours: currentOrder.totalHours,
                price: currentOrder.amount,
                orderId: currentOrder.orderId,
                packageName: currentOrder.package?.name || 'Package',
                status: 'UNUSED',
                purchasedAt: new Date().toLocaleString('th-TH')
              };
              existingKeys.unshift(newKeyRecord);
              localStorage.setItem('my_product_keys', JSON.stringify(existingKeys));
            }
            setCurrentOrder(prev => ({
              ...prev,
              generatedKey: data.generated_key_code,
              paidAt: new Date().toLocaleString('th-TH')
            }));
            setOrderState('PAID');
          }
        }
      } catch (err) {
        console.error('Polling check-status error:', err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [orderModalOpen, orderState, currentOrder?.orderId]);

  const handleSelectPackage = async (pkg) => {
    setSelectedPkg(pkg);
    setOrderState('PENDING');
    setCountdown(600);
    setOrderModalOpen(true);

    try {
      const res = await fetch('/api/checkout/create-qr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          package_id: pkg.id,
          amount_thb: pkg.price,
          hours_to_add: pkg.hours + pkg.bonus
        })
      });
      const data = await res.json();
      if (data.success) {
        setCurrentOrder({
          orderId: data.order_id,
          package: pkg,
          totalHours: pkg.hours + pkg.bonus,
          amount: pkg.price,
          qrImageUrl: data.qr_image_url,
          createdTime: data.created_at
        });
      } else {
        const fallbackId = 'ORD-' + Math.floor(100000 + Math.random() * 900000);
        setCurrentOrder({
          orderId: fallbackId,
          package: pkg,
          totalHours: pkg.hours + pkg.bonus,
          amount: pkg.price,
          qrImageUrl: `https://promptpay.io/0812345678/${pkg.price}.png`,
          createdTime: new Date().toISOString()
        });
      }
    } catch (e) {
      console.error('Failed to create order via API:', e);
      const fallbackId = 'ORD-' + Math.floor(100000 + Math.random() * 900000);
      setCurrentOrder({
        orderId: fallbackId,
        package: pkg,
        totalHours: pkg.hours + pkg.bonus,
        amount: pkg.price,
        qrImageUrl: `https://promptpay.io/0812345678/${pkg.price}.png`,
        createdTime: new Date().toISOString()
      });
    }
  };

  const handleSimulatePayment = async () => {
    if (!currentOrder) return;
    try {
      const res = await fetch('/api/webhook/payment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: currentOrder.orderId,
          payment_ref: 'DEMO-TXN-' + Math.floor(100000 + Math.random() * 900000),
          status: 'SUCCESS'
        })
      });
      const data = await res.json();
      const generatedKey = data.product_key || generateSecureProductKey();

      // บันทึก Product Key ลง LocalStorage ให้แสดงใน /my-keys
      const existingKeys = JSON.parse(localStorage.getItem('my_product_keys') || '[]');
      const newKeyRecord = {
        keyCode: generatedKey,
        hours: currentOrder.totalHours,
        price: currentOrder.amount,
        orderId: currentOrder.orderId,
        packageName: currentOrder.package.name,
        status: 'UNUSED',
        purchasedAt: new Date().toLocaleString('th-TH')
      };
      existingKeys.unshift(newKeyRecord);
      localStorage.setItem('my_product_keys', JSON.stringify(existingKeys));

      setCurrentOrder((prev) => ({
        ...prev,
        generatedKey,
        paidAt: new Date().toLocaleString('th-TH')
      }));
      setOrderState('PAID');
    } catch (e) {
      console.error('Error simulating payment:', e);
      const generatedKey = generateSecureProductKey();
      const existingKeys = JSON.parse(localStorage.getItem('my_product_keys') || '[]');
      const newKeyRecord = {
        keyCode: generatedKey,
        hours: currentOrder.totalHours,
        price: currentOrder.amount,
        orderId: currentOrder.orderId,
        packageName: currentOrder.package.name,
        status: 'UNUSED',
        purchasedAt: new Date().toLocaleString('th-TH')
      };
      existingKeys.unshift(newKeyRecord);
      localStorage.setItem('my_product_keys', JSON.stringify(existingKeys));

      setCurrentOrder((prev) => ({
        ...prev,
        generatedKey,
        paidAt: new Date().toLocaleString('th-TH')
      }));
      setOrderState('PAID');
    }
  };

  const handleUploadSlip = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !currentOrder?.orderId) return;

    setIsVerifyingSlip(true);
    setSlipMessage('กำลังส่งตรวจสลิปผ่าน SlipOK...');

    try {
      const formData = new FormData();
      formData.append('order_id', currentOrder.orderId);
      formData.append('slip', file);

      const res = await fetch('/api/checkout/verify-slip', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      if (data.success && data.product_key) {
        setSlipMessage('✅ ตรวจสลิปสำเร็จ! ออกรหัส Product Key เรียบร้อย');
        const existingKeys = JSON.parse(localStorage.getItem('my_product_keys') || '[]');
        const keyAlreadyExists = existingKeys.some(k => k.keyCode === data.product_key);
        if (!keyAlreadyExists) {
          const newKeyRecord = {
            keyCode: data.product_key,
            hours: currentOrder.totalHours,
            price: currentOrder.amount,
            orderId: currentOrder.orderId,
            packageName: currentOrder.package?.name || 'Package',
            status: 'UNUSED',
            purchasedAt: new Date().toLocaleString('th-TH')
          };
          existingKeys.unshift(newKeyRecord);
          localStorage.setItem('my_product_keys', JSON.stringify(existingKeys));
        }

        setTimeout(() => {
          setCurrentOrder(prev => ({
            ...prev,
            generatedKey: data.product_key,
            paidAt: new Date().toLocaleString('th-TH')
          }));
          setOrderState('PAID');
        }, 600);
      } else {
        setSlipMessage('❌ ' + (data.error || 'สลิปไม่ถูกต้อง หรือยอดเงินไม่ตรงกับแพ็กเกจ'));
      }
    } catch (err) {
      setSlipMessage('❌ เกิดข้อผิดพลาดในการเชื่อมต่อ SlipOK');
    } finally {
      setIsVerifyingSlip(false);
    }
  };

  const handleCopyKey = (key) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const formatTimer = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />

      <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '2.5rem 1.5rem', width: '100%' }}>
        {/* Header Hero */}
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1.2rem', marginBottom: '1.2rem' }}>
            <div style={{
              width: '68px',
              height: '68px',
              borderRadius: '18px',
              overflow: 'hidden',
              border: '2px solid rgba(251, 191, 36, 0.6)',
              boxShadow: '0 0 25px rgba(251, 191, 36, 0.35)',
              background: '#0d131a',
              transition: 'transform 0.2s ease'
            }}>
              <img src="/store_logo.png" alt="GoldBot24 Store Logo" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
            <div style={{ fontSize: '1.3rem', color: 'rgba(251, 191, 36, 0.6)', fontWeight: 600 }}>✦</div>
            <div style={{
              width: '68px',
              height: '68px',
              borderRadius: '18px',
              overflow: 'hidden',
              border: '2px solid rgba(251, 191, 36, 0.6)',
              boxShadow: '0 0 25px rgba(251, 191, 36, 0.35)',
              background: '#0d131a',
              transition: 'transform 0.2s ease'
            }}>
              <img src="/app_icon.png" alt="AI Gold Commander Pro Icon" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
          </div>

          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.35rem 1rem',
            borderRadius: '9999px',
            backgroundColor: 'rgba(251, 191, 36, 0.1)',
            border: '1px solid rgba(251, 191, 36, 0.3)',
            color: '#fbbf24',
            fontSize: '0.82rem',
            fontWeight: 600,
            marginBottom: '1rem'
          }}>
            <Sparkles size={14} />
            <span>Fair Metering Model • ชั่วโมงละ 1 บาท ตัดเวลาตามจริงเฉพาะตอนเปิดบอท</span>
          </div>

          <h1 style={{ fontSize: '2.4rem', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '0.75rem' }}>
            GoldBot24 <span style={{ color: '#fbbf24' }}>Store</span> • แพ็กเกจ AI Gold Commander Pro
          </h1>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '650px', margin: '0 auto', fontSize: '0.95rem', lineHeight: '1.6' }}>
            ไม่มีค่าธรรมเนียมรายเดือน สแกนจ่ายผ่าน Dynamic PromptPay QR Code รับรหัส Product Key 24 หลักทันที นำไปกรอกเติมเวลาสะสมเพิ่ม (+) บนตัวโปรแกรมได้ตลอดเวลา
          </p>
        </div>

        {/* Feature Highlights Banner */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '1rem',
          marginBottom: '2.5rem'
        }}>
          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '12px',
            padding: '1.2rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.85rem'
          }}>
            <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
              <Clock size={20} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.92rem', marginBottom: '0.2rem' }}>ตัดเวลาเฉพาะตอนเปิดบอท</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                เมื่อคุณกด Pause หรือปิดโปรแกรม มิเตอร์เวลาจะหยุดนับทันที ไม่กินเวลาทิ้ง
              </div>
            </div>
          </div>

          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '12px',
            padding: '1.2rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.85rem'
          }}>
            <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', color: '#10b981' }}>
              <ShieldCheck size={20} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.92rem', marginBottom: '0.2rem' }}>เวลาเดิมไม่หาย บวกเพิ่มสะสม</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                เติมเวลาได้ตลอด ชั่วโมงใหม่จะถูก + บวกเพิ่มจากยอดคงเหลือเดิมเสมอ
              </div>
            </div>
          </div>

          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '12px',
            padding: '1.2rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.85rem'
          }}>
            <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(251, 191, 36, 0.15)', color: '#fbbf24' }}>
              <QrCode size={20} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.92rem', marginBottom: '0.2rem' }}>ระบบ PromptPay อัตโนมัติ</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                สแกนผ่านแอปธนาคารใดก็ได้ เงินเข้าปุ๊บ ระบบจ่าย Product Key ทันทีใน 3 วินาที
              </div>
            </div>
          </div>
        </div>

        {/* 4 Package Cards Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: '1.5rem',
          marginBottom: '3rem'
        }}>
          {PACKAGES.map((pkg) => {
            const Icon = pkg.icon;
            const isHighlight = pkg.id === 2 || pkg.id === 4;
            return (
              <div
                key={pkg.id}
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: isHighlight ? '2px solid rgba(251, 191, 36, 0.4)' : '1px solid var(--border-subtle)',
                  borderRadius: '16px',
                  padding: '1.75rem',
                  display: 'flex',
                  flexDirection: 'column',
                  position: 'relative',
                  boxShadow: isHighlight ? '0 10px 30px -10px rgba(251, 191, 36, 0.15)' : 'none',
                  transition: 'transform 0.2s ease, border-color 0.2s ease',
                }}
              >
                {/* Badge if present */}
                {pkg.badge && (
                  <div style={{
                    position: 'absolute',
                    top: '-12px',
                    right: '18px',
                    backgroundColor: '#fbbf24',
                    color: '#07090e',
                    fontSize: '0.72rem',
                    fontWeight: 800,
                    padding: '3px 10px',
                    borderRadius: '9999px',
                    boxShadow: '0 2px 10px rgba(251, 191, 36, 0.3)'
                  }}>
                    {pkg.badge}
                  </div>
                )}

                {/* Package Title & Icon */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.85rem' }}>
                  <div style={{
                    padding: '8px',
                    borderRadius: '10px',
                    backgroundColor: `rgba(${pkg.color === '#fbbf24' ? '251, 191, 36' : pkg.color === '#f97316' ? '249, 115, 22' : pkg.color === '#10b981' ? '16, 185, 129' : '56, 189, 248'}, 0.15)`,
                    color: pkg.color
                  }}>
                    <Icon size={20} />
                  </div>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 700 }}>{pkg.name}</h3>
                </div>

                {/* Hours Display */}
                <div style={{ marginBottom: '1.2rem' }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.3rem' }}>
                    <span style={{ fontSize: '2.5rem', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>
                      {pkg.hours + pkg.bonus}
                    </span>
                    <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>ชั่วโมง</span>
                  </div>
                  {pkg.bonus > 0 && (
                    <div style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>
                      (ชั่วโมงหลัก {pkg.hours} + โบนัสแถม {pkg.bonus} ชม.)
                    </div>
                  )}
                </div>

                <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', lineHeight: '1.5', minHeight: '40px', marginBottom: '1.5rem' }}>
                  {pkg.desc}
                </p>

                {/* Price & Buy Button */}
                <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1rem' }}>
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>ราคาชำระ</span>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '1.4rem', fontWeight: 800, color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>
                        ฿{pkg.price}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: '4px' }}>THB</span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleSelectPackage(pkg)}
                    style={{
                      width: '100%',
                      padding: '0.75rem 1rem',
                      borderRadius: '10px',
                      backgroundColor: isHighlight ? '#fbbf24' : 'rgba(255, 255, 255, 0.08)',
                      color: isHighlight ? '#07090e' : '#f0f4fc',
                      border: isHighlight ? 'none' : '1px solid var(--border-subtle)',
                      fontWeight: 700,
                      fontSize: '0.88rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <span>สั่งซื้อผ่าน QR Code</span>
                    <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </main>

      {/* QR Payment & Key Revelation Modal */}
      {orderModalOpen && currentOrder && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '1rem'
        }}>
          <div style={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '18px',
            width: '100%',
            maxWidth: '460px',
            padding: '2rem',
            position: 'relative',
            boxShadow: '0 20px 50px rgba(0,0,0,0.7)'
          }}>
            {/* Close Button */}
            <button
              onClick={() => setOrderModalOpen(false)}
              style={{
                position: 'absolute',
                top: '16px',
                right: '16px',
                background: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                fontSize: '1.2rem',
                cursor: 'pointer',
                padding: '4px 8px'
              }}
            >
              ✕
            </button>

            {orderState === 'PENDING' ? (
              <div>
                <div style={{ textAlign: 'center', marginBottom: '1.2rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#fbbf24', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    PromptPay Dynamic QR Code
                  </div>
                  <h3 style={{ fontSize: '1.3rem', fontWeight: 800, marginTop: '4px' }}>
                    ชำระเงินค่าแพ็กเกจ {currentOrder.package.name}
                  </h3>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    เลขอ้างอิง: <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{currentOrder.orderId}</span>
                  </div>
                </div>

                {/* QR Code Container Simulation */}
                <div style={{
                  backgroundColor: '#ffffff',
                  borderRadius: '14px',
                  padding: '1.2rem',
                  maxWidth: '240px',
                  margin: '0 auto 1.2rem auto',
                  textAlign: 'center',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
                }}>
                  {/* PromptPay Header */}
                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                    <div style={{ width: '18px', height: '18px', background: '#003d79', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '10px', fontWeight: 800 }}>
                      PP
                    </div>
                    <span style={{ color: '#003d79', fontSize: '12px', fontWeight: 800, letterSpacing: '0.02em' }}>พร้อมเพย์</span>
                  </div>

                  {/* QR Image Graphic (Live Bank Scannable PromptPay QR) */}
                  <div style={{
                    width: '200px',
                    height: '200px',
                    margin: '0 auto',
                    background: '#ffffff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden',
                    position: 'relative'
                  }}>
                    {currentOrder.qrImageUrl ? (
                      <img
                        src={currentOrder.qrImageUrl}
                        alt={`PromptPay QR ฿${currentOrder.amount}`}
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'contain'
                        }}
                        onError={(e) => {
                          e.target.style.display = 'none';
                        }}
                      />
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                        <QrCode size={120} color="#0f172a" />
                        <span style={{ fontSize: '10px', fontWeight: 600, color: '#475569', marginTop: '4px' }}>
                          สแกนจ่าย ฿{currentOrder.amount}.00
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Amount & Countdown */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.75rem 1rem',
                  backgroundColor: 'rgba(0,0,0,0.3)',
                  borderRadius: '10px',
                  border: '1px solid var(--border-subtle)',
                  marginBottom: '1.2rem'
                }}>
                  <div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>ยอดชำระสุทธิ</div>
                    <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>
                      ฿{currentOrder.amount}.00
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>เวลาชำระคงเหลือ</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 700, color: countdown < 120 ? '#f43f5e' : '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                      ⏱️ {formatTimer(countdown)}
                    </div>
                  </div>
                </div>

                {/* Account Details Box */}
                <div style={{
                  padding: '0.75rem 1rem',
                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '10px',
                  marginBottom: '1rem',
                  fontSize: '0.78rem',
                  lineHeight: '1.5'
                }}>
                  <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span>💳 ช่องทางรับเงิน (นาย รัชวุฒิ เพิ่มมหา...)</span>
                    <span style={{ fontSize: '0.68rem', color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>SlipOK Active ✅</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '3px 8px', color: 'var(--text-secondary)' }}>
                    <span>• พร้อมเพย์ / TrueMoney:</span>
                    <strong style={{ color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>088-123-2388</strong>
                    <span>• ธ.กสิกรไทย (KBank):</span>
                    <strong style={{ color: '#10b981', fontFamily: 'var(--font-mono)' }}>119-8-69683-4</strong>
                  </div>
                </div>

                {/* SlipOK Bank Slip Upload Box */}
                <div style={{
                  padding: '1.1rem',
                  backgroundColor: 'rgba(251, 191, 36, 0.05)',
                  borderRadius: '14px',
                  border: '1.5px dashed rgba(251, 191, 36, 0.6)',
                  marginBottom: '1rem',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '0.92rem', fontWeight: 800, color: '#fbbf24', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}>
                    <span>🧾 ขั้นตอนสุดท้าย: แนบสลิปเพื่อรับคีย์ทันที</span>
                  </div>
                  
                  <div style={{
                    fontSize: '0.76rem',
                    color: 'var(--text-secondary)',
                    marginBottom: '0.85rem',
                    lineHeight: '1.5',
                    textAlign: 'left',
                    background: 'rgba(0,0,0,0.25)',
                    padding: '0.65rem 0.85rem',
                    borderRadius: '8px'
                  }}>
                    <div><strong style={{ color: '#10b981' }}>1. โอนเงิน:</strong> สแกนจ่าย ฿{currentOrder.amount}.00 ผ่าน QR หรือเลขบัญชีด้านบน</div>
                    <div><strong style={{ color: '#fbbf24' }}>2. แนบสลิป:</strong> กดปุ่มสีทองด้านล่างเพื่อเลือกรูปสลิปจากอัลบั้ม</div>
                    <div><strong style={{ color: '#38bdf8' }}>3. รับคีย์ทันที:</strong> SlipOK ตรวจสอบเสร็จจะแสดง Product Key อัตโนมัติ (1-2 วินาที)</div>
                  </div>

                  <label style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.6rem',
                    padding: '0.85rem 1.4rem',
                    borderRadius: '10px',
                    backgroundColor: '#fbbf24',
                    color: '#07090e',
                    border: 'none',
                    fontSize: '0.92rem',
                    fontWeight: 800,
                    cursor: isVerifyingSlip ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s',
                    width: '100%',
                    boxShadow: '0 4px 20px rgba(251, 191, 36, 0.35)'
                  }}>
                    {isVerifyingSlip ? (
                      <span>⏳ กำลังส่งตรวจสลิปผ่าน SlipOK...</span>
                    ) : (
                      <>
                        <span style={{ fontSize: '1.1rem' }}>📸</span>
                        <span>คลิกเพื่อแนบรูปสลิปธนาคาร (รับคีย์ทันที)</span>
                      </>
                    )}
                    <input
                      type="file"
                      accept="image/*"
                      style={{ display: 'none' }}
                      disabled={isVerifyingSlip}
                      onChange={handleUploadSlip}
                    />
                  </label>
                  {slipMessage && (
                    <div style={{
                      fontSize: '0.76rem',
                      marginTop: '0.6rem',
                      fontWeight: 600,
                      color: slipMessage.includes('✅') ? '#10b981' : '#f43f5e'
                    }}>
                      {slipMessage}
                    </div>
                  )}
                </div>

                {/* Test Payment Simulation Trigger */}
                <button
                  onClick={handleSimulatePayment}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    borderRadius: '10px',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    color: '#10b981',
                    border: '1px solid rgba(16, 185, 129, 0.4)',
                    fontWeight: 700,
                    fontSize: '0.82rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem'
                  }}
                >
                  <CheckCircle2 size={16} />
                  <span>⚡ จำลองการตรวจสลิปผ่านทันที (Test Simulation)</span>
                </button>
              </div>
            ) : (
              /* Success / Key Revelation */
              <div style={{ textAlign: 'center' }}>
                <div style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '50%',
                  backgroundColor: 'rgba(16, 185, 129, 0.15)',
                  color: '#10b981',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 1rem auto'
                }}>
                  <CheckCircle2 size={32} />
                </div>

                <h3 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '0.2rem' }}>
                  ชำระเงินสำเร็จเรียบร้อย!
                </h3>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '1.2rem' }}>
                  คุณได้รับเวลา <strong style={{ color: '#fbbf24' }}>+{currentOrder.totalHours} ชั่วโมง</strong> สำหรับ AI Gold Pro
                </p>

                {/* Key Box */}
                <div style={{
                  backgroundColor: 'rgba(0,0,0,0.4)',
                  border: '1px solid rgba(251, 191, 36, 0.3)',
                  borderRadius: '12px',
                  padding: '1rem',
                  marginBottom: '1.2rem'
                }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                    รหัส PRODUCT KEY 24 หลักของคุณ (บันทึกใน /my-keys แล้ว):
                  </div>
                  <div style={{
                    fontSize: '1.15rem',
                    fontWeight: 800,
                    fontFamily: 'var(--font-mono)',
                    color: '#fbbf24',
                    letterSpacing: '0.05em',
                    padding: '0.5rem',
                    backgroundColor: 'rgba(251, 191, 36, 0.08)',
                    borderRadius: '8px',
                    userSelect: 'all'
                  }}>
                    {currentOrder.generatedKey}
                  </div>
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: '0.6rem' }}>
                  <button
                    onClick={() => handleCopyKey(currentOrder.generatedKey)}
                    style={{
                      flex: 1,
                      padding: '0.75rem',
                      borderRadius: '10px',
                      backgroundColor: copied ? '#10b981' : 'rgba(255, 255, 255, 0.1)',
                      color: '#ffffff',
                      border: '1px solid var(--border-subtle)',
                      fontWeight: 600,
                      fontSize: '0.85rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.4rem'
                    }}
                  >
                    {copied ? <Check size={16} /> : <Copy size={16} />}
                    <span>{copied ? 'คัดลอกสำเร็จ!' : 'คัดลอกรหัส'}</span>
                  </button>

                  <a
                    href="/dashboard"
                    style={{
                      flex: 1,
                      padding: '0.75rem',
                      borderRadius: '10px',
                      backgroundColor: '#fbbf24',
                      color: '#07090e',
                      textDecoration: 'none',
                      fontWeight: 700,
                      fontSize: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.4rem'
                    }}
                  >
                    <span>ไปหน้าเติมเวลา</span>
                    <ArrowRight size={16} />
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <Footer />
    </div>
  );
}
