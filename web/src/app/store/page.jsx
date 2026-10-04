'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, Check, Clock, Crown, Flame, ImageUp, QrCode, ShieldCheck, ShoppingBag, Sparkles, X, Zap } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Alert, CopyButton, PageHeader, Spinner } from '../../components/ui';
import { PACKAGES } from '../../lib/packages';
import { formatThb } from '../../lib/format';
import { markLocalKeyRedeemed, rememberLocalKey } from '../../lib/localKeys';

const ACCENTS = {
  sky: { color: 'var(--sky)', icon: Zap },
  orange: { color: 'var(--orange)', icon: Flame },
  emerald: { color: 'var(--green)', icon: Sparkles },
  gold: { color: 'var(--gold)', icon: Crown },
};

// ข้อมูลผู้รับเงิน (แสดงประกอบ QR)
const PAYEE = {
  name: 'นาย รัชวุฒิ เพิ่มมหา...',
  promptpay: '088-123-2388',
  bank: 'กสิกรไทย 119-8-69683-4',
};

const PAY_WINDOW_SEC = 15 * 60;

export default function StorePage() {
  const { user, openAuthModal } = useAuth();
  const [checkoutPkg, setCheckoutPkg] = useState(null);

  const buy = (pkg) => {
    if (!user) {
      openAuthModal('login');
      return;
    }
    setCheckoutPkg(pkg);
  };

  return (
    <div className="container page">
      <PageHeader
        eyebrow="Store"
        icon={ShoppingBag}
        title="เติมชั่วโมงใช้งาน"
        description="1 บาท ต่อ 1 ชั่วโมง · ไม่มีรายเดือน · ชั่วโมงไม่มีวันหมดอายุ และบวกสะสมจากยอดเดิมเสมอ"
      />

      <div className="grid grid-3" style={{ marginBottom: 28 }}>
        {[
          { icon: Clock, title: 'ตัดเวลาเฉพาะตอนบอททำงาน', text: 'กดหยุดหรือปิดโปรแกรม มิเตอร์หยุดทันที' },
          { icon: QrCode, title: 'จ่ายผ่าน PromptPay', text: 'สแกนด้วยแอปธนาคารใดก็ได้ แนบสลิปรับคีย์อัตโนมัติ' },
          { icon: ShieldCheck, title: 'ตรวจสลิปอัตโนมัติ', text: 'ระบบ SlipOK ตรวจยอดและสลิปซ้ำให้ภายในไม่กี่วินาที' },
        ].map(({ icon: Icon, title, text }) => (
          <div key={title} className="card card-pad row" style={{ alignItems: 'flex-start', gap: 14 }}>
            <span className="icon-chip text-gold" style={{ width: 38, height: 38 }}>
              <Icon size={18} />
            </span>
            <div>
              <div style={{ fontWeight: 600 }}>{title}</div>
              <div className="small muted">{text}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-4">
        {PACKAGES.map((pkg) => {
          const accent = ACCENTS[pkg.accent] || ACCENTS.gold;
          const Icon = accent.icon;
          const total = pkg.hours + pkg.bonus;
          return (
            <div key={pkg.id} className={`card card-pad card-interactive pkg ${pkg.featured ? 'card-gold pkg-featured' : ''}`}>
              {pkg.badge && <span className="badge badge-gold pkg-badge">{pkg.badge}</span>}
              <div className="row" style={{ marginBottom: 18 }}>
                <span className="icon-chip" style={{ color: accent.color, width: 38, height: 38 }}>
                  <Icon size={18} />
                </span>
                <span style={{ fontWeight: 700 }}>{pkg.name}</span>
              </div>
              <div className="row" style={{ alignItems: 'baseline', gap: 6 }}>
                <span className="mono" style={{ fontSize: '2.4rem', fontWeight: 700, lineHeight: 1 }}>
                  {total}
                </span>
                <span className="muted">ชั่วโมง</span>
              </div>
              <div className="tiny" style={{ minHeight: 20, marginTop: 6, color: 'var(--green)' }}>
                {pkg.bonus > 0 ? `${pkg.hours} + โบนัส ${pkg.bonus} ชม.` : ''}
              </div>
              <p className="small muted" style={{ margin: '10px 0 22px', minHeight: 44 }}>
                {pkg.desc}
              </p>
              <div className="row-between" style={{ marginTop: 'auto', marginBottom: 14 }}>
                <span className="faint small">ราคา</span>
                <span className="mono text-gold" style={{ fontSize: '1.35rem', fontWeight: 700 }}>
                  {formatThb(pkg.price)}
                </span>
              </div>
              <button className={`btn btn-block ${pkg.featured ? 'btn-primary' : 'btn-secondary'}`} onClick={() => buy(pkg)}>
                ซื้อแพ็กเกจนี้ <ArrowRight size={16} />
              </button>
            </div>
          );
        })}
      </div>

      {checkoutPkg && <CheckoutModal pkg={checkoutPkg} onClose={() => setCheckoutPkg(null)} />}
    </div>
  );
}

/** ย่อรูปสลิปเป็น JPEG ไม่เกิน 1600px ก่อนอัปโหลด (กันไฟล์ใหญ่เกินลิมิต) */
async function compressSlip(file) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.88);
}

function CheckoutModal({ pkg, onClose }) {
  const { user, apiFetch, redeemKey } = useAuth();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState('');
  const [remaining, setRemaining] = useState(PAY_WINDOW_SEC);
  const [verifying, setVerifying] = useState(false);
  const [slipError, setSlipError] = useState('');
  const [productKey, setProductKey] = useState(null);
  const [redeemState, setRedeemState] = useState(null);
  const fileRef = useRef(null);

  // สร้างคำสั่งซื้อ
  useEffect(() => {
    let cancelled = false;
    apiFetch('/api/checkout/create-qr', { method: 'POST', body: JSON.stringify({ package_id: pkg.id }) })
      .then((res) => !cancelled && setOrder(res))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [apiFetch, pkg.id]);

  // นับถอยหลัง
  useEffect(() => {
    if (!order || productKey) return;
    const id = setInterval(() => setRemaining((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [order, productKey]);

  // ตรวจสถานะการชำระเงิน (กรณีชำระผ่าน Webhook)
  useEffect(() => {
    if (!order || productKey) return;
    const id = setInterval(async () => {
      try {
        const res = await apiFetch(`/api/checkout/check-status?order_id=${encodeURIComponent(order.order_id)}`);
        if (res.is_paid && res.generated_key_code) onPaid(res.generated_key_code);
      } catch {
        /* ลองใหม่รอบถัดไป */
      }
    }, 5000);
    return () => clearInterval(id);
  }, [order, productKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  function onPaid(key) {
    setProductKey(key);
    rememberLocalKey(user.email, {
      keyCode: key,
      packageName: pkg.name,
      hours: pkg.hours + pkg.bonus,
      price: pkg.price,
      orderId: order?.order_id,
    });
  }

  const onSlipSelected = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file || !order) return;
    setSlipError('');
    setVerifying(true);
    try {
      const dataUrl = await compressSlip(file);
      const res = await apiFetch('/api/checkout/verify-slip', {
        method: 'POST',
        body: JSON.stringify({ order_id: order.order_id, slip_base64: dataUrl, mime: 'image/jpeg' }),
      });
      onPaid(res.product_key);
    } catch (err) {
      setSlipError(err.message || 'ตรวจสลิปไม่สำเร็จ');
    } finally {
      setVerifying(false);
    }
  };

  const redeemNow = async () => {
    setRedeemState({ loading: true });
    try {
      const res = await redeemKey(productKey);
      markLocalKeyRedeemed(user.email, productKey);
      setRedeemState({ type: 'success', message: res.message });
    } catch (err) {
      setRedeemState({ type: 'error', message: err.message });
    }
  };

  const mm = String(Math.floor(remaining / 60)).padStart(2, '0');
  const ss = String(remaining % 60).padStart(2, '0');

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && !verifying && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="checkout-title" style={{ maxWidth: 460 }}>
        <button className="btn btn-ghost btn-icon modal-close" onClick={onClose} aria-label="ปิด" disabled={verifying}>
          <X size={18} />
        </button>

        <div style={{ padding: '28px 26px 26px' }}>
          {productKey ? (
            <div className="center">
              <div className="empty-icon" style={{ background: 'var(--green-soft)', color: 'var(--green)' }}>
                <Check size={28} />
              </div>
              <h2 id="checkout-title" style={{ fontSize: '1.3rem', fontWeight: 700 }}>
                ชำระเงินสำเร็จ
              </h2>
              <p className="small muted" style={{ marginBottom: 18 }}>
                ได้รับ <strong className="text-gold">+{pkg.hours + pkg.bonus} ชั่วโมง</strong> · คีย์ถูกเก็บไว้ในหน้า “คีย์ของฉัน” แล้ว
              </p>
              <div className="card" style={{ padding: 16, background: 'var(--surface)' }}>
                <div className="tiny faint" style={{ marginBottom: 6 }}>
                  Product Key
                </div>
                <div className="key-code" style={{ fontSize: '1.05rem' }}>
                  {productKey}
                </div>
              </div>
              {redeemState?.message && (
                <div style={{ marginTop: 14 }}>
                  <Alert type={redeemState.type}>{redeemState.message}</Alert>
                </div>
              )}
              <div className="grid grid-2" style={{ marginTop: 16, gap: 10 }}>
                <CopyButton text={productKey} label="คัดลอกคีย์" className="btn btn-secondary btn-block" />
                {redeemState?.type === 'success' ? (
                  <Link href="/dashboard" className="btn btn-primary btn-block">
                    ไปกระเป๋าเวลา
                  </Link>
                ) : (
                  <button className="btn btn-primary btn-block" onClick={redeemNow} disabled={redeemState?.loading}>
                    {redeemState?.loading ? <Spinner /> : <Sparkles size={16} />} เติมเข้าบัญชีเลย
                  </button>
                )}
              </div>
            </div>
          ) : (
            <>
              <div className="center" style={{ marginBottom: 18 }}>
                <span className="eyebrow">PromptPay QR</span>
                <h2 id="checkout-title" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                  {pkg.name} · {pkg.hours + pkg.bonus} ชั่วโมง
                </h2>
              </div>

              {error ? (
                <Alert type="error">{error}</Alert>
              ) : !order ? (
                <div className="center" style={{ padding: 40 }}>
                  <Spinner size={24} />
                  <div className="small muted" style={{ marginTop: 10 }}>
                    กำลังสร้างคำสั่งซื้อ...
                  </div>
                </div>
              ) : (
                <div className="stack" style={{ gap: 16 }}>
                  <div className="qr-box">
                    <img src={order.qr_image_url} alt={`PromptPay QR ${formatThb(order.amount_thb)}`} width={210} height={210} />
                  </div>

                  <div className="row-between card" style={{ padding: '12px 16px', background: 'var(--surface)' }}>
                    <div>
                      <div className="tiny faint">ยอดชำระ</div>
                      <div className="mono text-gold" style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                        {formatThb(order.amount_thb)}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div className="tiny faint">ชำระภายใน</div>
                      <div className={`mono ${remaining < 120 ? 'text-red' : ''}`} style={{ fontSize: '1.15rem', fontWeight: 600 }}>
                        {mm}:{ss}
                      </div>
                    </div>
                  </div>

                  <div className="small muted stack" style={{ gap: 4 }}>
                    <div className="row-between">
                      <span className="faint">ผู้รับเงิน</span>
                      <span>{PAYEE.name}</span>
                    </div>
                    <div className="row-between">
                      <span className="faint">พร้อมเพย์</span>
                      <span className="mono">{PAYEE.promptpay}</span>
                    </div>
                    <div className="row-between">
                      <span className="faint">บัญชีธนาคาร</span>
                      <span className="mono">{PAYEE.bank}</span>
                    </div>
                    <div className="row-between">
                      <span className="faint">เลขคำสั่งซื้อ</span>
                      <span className="mono tiny">{order.order_id}</span>
                    </div>
                  </div>

                  {slipError && <Alert type="error">{slipError}</Alert>}

                  {remaining === 0 ? (
                    <Alert type="error">หมดเวลาชำระเงินแล้ว กรุณาปิดหน้าต่างและสั่งซื้อใหม่ (หากโอนแล้ว ยังแนบสลิปได้ภายใน 24 ชั่วโมง)</Alert>
                  ) : null}

                  <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={onSlipSelected} />
                  <button className="btn btn-primary btn-lg btn-block" onClick={() => fileRef.current?.click()} disabled={verifying}>
                    {verifying ? <Spinner /> : <ImageUp size={18} />}
                    {verifying ? 'กำลังตรวจสลิป...' : 'โอนแล้ว · แนบสลิปเพื่อรับคีย์'}
                  </button>
                  <p className="tiny faint center">โอนยอดให้ตรงตามจำนวน แล้วแนบรูปสลิปจากแอปธนาคาร ระบบจะออก Product Key ให้อัตโนมัติ</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
