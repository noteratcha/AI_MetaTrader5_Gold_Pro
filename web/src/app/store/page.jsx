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
  const [packages, setPackages] = useState(PACKAGES);

  // แพ็กเกจจากฐานข้อมูล (แอดมินแก้ไขได้) — ใช้ค่าเริ่มต้นระหว่างโหลด
  useEffect(() => {
    fetch('/api/packages')
      .then((r) => r.json())
      .then((d) => d.success && Array.isArray(d.packages) && setPackages(d.packages))
      .catch(() => {});
  }, []);

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
        {packages.map((pkg) => {
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
  let bitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    throw new Error('เปิดรูปนี้ไม่ได้ (เช่นไฟล์ HEIC) กรุณาแคปหน้าจอสลิปแล้วแนบใหม่');
  }
  const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.88);
}

const STEPS = ['สแกนจ่าย', 'แนบสลิป', 'รับชั่วโมง'];

function CheckoutSteps({ step }) {
  return (
    <ol className="checkout-steps" aria-label="ขั้นตอนการชำระเงิน">
      {STEPS.map((label, i) => (
        <li key={label} className={i < step ? 'is-done' : i === step ? 'is-active' : ''}>
          <span className="checkout-step-dot">{i < step ? <Check size={12} /> : i + 1}</span>
          {label}
        </li>
      ))}
    </ol>
  );
}

function CheckoutModal({ pkg, onClose }) {
  const { user, apiFetch, redeemKey } = useAuth();
  const [order, setOrder] = useState(null);
  const [error, setError] = useState('');
  const [remaining, setRemaining] = useState(PAY_WINDOW_SEC);
  const [verifying, setVerifying] = useState(false);
  const [slip, setSlip] = useState(null); // { dataUrl } รูปที่แนบล่าสุด (แสดงตัวอย่าง + ใช้ตรวจซ้ำ)
  const [slipError, setSlipError] = useState(null); // { message, hint }
  const [retryIn, setRetryIn] = useState(0); // สลิป SCB/BBL ที่ธนาคารให้รอ → นับถอยหลังแล้วตรวจซ้ำอัตโนมัติ
  const [dragging, setDragging] = useState(false);
  const [productKey, setProductKey] = useState(null);
  const [autoRedeem, setAutoRedeem] = useState(true);
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

  // นับถอยหลังเวลาชำระ
  useEffect(() => {
    if (!order || productKey) return;
    const id = setInterval(() => setRemaining((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [order, productKey]);

  // ตรวจสถานะการชำระเงิน (กรณีชำระผ่าน Webhook / ตรวจจากอุปกรณ์อื่น)
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
    const onKey = (e) => e.key === 'Escape' && !verifying && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, verifying]);

  // วางสลิปด้วย Ctrl+V (คัดลอกรูปจากแอปธนาคาร/แคปหน้าจอ)
  useEffect(() => {
    if (!order || productKey) return;
    const onPaste = (e) => {
      const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith('image/'));
      if (!item) return;
      e.preventDefault();
      handleFile(item.getAsFile());
    };
    window.addEventListener('paste', onPaste);
    return () => window.removeEventListener('paste', onPaste);
  }, [order, productKey, verifying]); // eslint-disable-line react-hooks/exhaustive-deps

  // ตรวจซ้ำอัตโนมัติเมื่อครบเวลาที่ธนาคารกำหนด (code 1010)
  useEffect(() => {
    if (retryIn <= 0 || productKey) return;
    const id = setTimeout(() => {
      if (retryIn === 1 && slip) verify(slip.dataUrl);
      setRetryIn((s) => Math.max(0, s - 1));
    }, 1000);
    return () => clearTimeout(id);
  }, [retryIn, productKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // ได้คีย์แล้ว → เติมเข้าบัญชีให้อัตโนมัติ (ถ้าเลือกไว้)
  useEffect(() => {
    if (productKey && autoRedeem && !redeemState) redeemNow();
  }, [productKey]); // eslint-disable-line react-hooks/exhaustive-deps

  function onPaid(key) {
    setProductKey(key);
    setRetryIn(0);
    rememberLocalKey(user.email, {
      keyCode: key,
      packageName: pkg.name,
      hours: pkg.hours + pkg.bonus,
      price: pkg.price,
      orderId: order?.order_id,
    });
  }

  async function verify(dataUrl) {
    if (!order) return;
    setSlipError(null);
    setVerifying(true);
    try {
      const res = await apiFetch('/api/checkout/verify-slip', {
        method: 'POST',
        body: JSON.stringify({ order_id: order.order_id, slip_base64: dataUrl, mime: 'image/jpeg' }),
      });
      onPaid(res.product_key);
    } catch (err) {
      const data = err.data || {};
      if (data.retryAfterSec > 0) {
        setRetryIn(Math.ceil(data.retryAfterSec));
        setSlipError({ type: 'wait', message: err.message, hint: 'ไม่ต้องทำอะไร ระบบจะตรวจสลิปนี้ให้อัตโนมัติเมื่อครบเวลา' });
      } else {
        setSlipError({ type: 'error', message: err.message || 'ตรวจสลิปไม่สำเร็จ', hint: data.hint });
      }
    } finally {
      setVerifying(false);
    }
  }

  async function handleFile(file) {
    if (!file || !order || verifying || productKey) return;
    if (!file.type.startsWith('image/')) {
      setSlipError({ type: 'error', message: 'กรุณาแนบไฟล์รูปภาพสลิป (JPG, PNG)' });
      return;
    }
    setRetryIn(0);
    try {
      const dataUrl = await compressSlip(file);
      setSlip({ dataUrl });
      await verify(dataUrl);
    } catch (err) {
      setSlipError({ type: 'error', message: err.message });
    }
  }

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  async function redeemNow() {
    setRedeemState({ loading: true });
    try {
      const res = await redeemKey(productKey);
      markLocalKeyRedeemed(user.email, productKey);
      setRedeemState({ type: 'success', message: res.message });
    } catch (err) {
      setRedeemState({ type: 'error', message: err.message });
    }
  }

  const mm = String(Math.floor(remaining / 60)).padStart(2, '0');
  const ss = String(remaining % 60).padStart(2, '0');
  const step = productKey ? 3 : slip ? 1 : 0;
  const retryText = `${Math.floor(retryIn / 60)}:${String(retryIn % 60).padStart(2, '0')}`;

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && !verifying && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="checkout-title" style={{ maxWidth: 480 }}>
        <button className="btn btn-ghost btn-icon modal-close" onClick={onClose} aria-label="ปิด" disabled={verifying}>
          <X size={18} />
        </button>

        <div style={{ padding: '26px 24px 24px' }}>
          <div className="center" style={{ marginBottom: 14 }}>
            <span className="eyebrow">PromptPay QR</span>
            <h2 id="checkout-title" style={{ fontSize: '1.2rem', fontWeight: 700 }}>
              {pkg.name} · {pkg.hours + pkg.bonus} ชั่วโมง
            </h2>
          </div>
          <CheckoutSteps step={step} />

          {productKey ? (
            <div className="center" style={{ marginTop: 18 }}>
              <div className="empty-icon" style={{ background: 'var(--green-soft)', color: 'var(--green)' }}>
                <Check size={28} />
              </div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>ชำระเงินสำเร็จ</h3>
              <p className="small muted" style={{ marginBottom: 16 }}>
                {redeemState?.type === 'success' ? (
                  <>
                    เติม <strong className="text-gold">+{pkg.hours + pkg.bonus} ชั่วโมง</strong> เข้าบัญชีแล้ว · ส่งใบเสร็จไปที่อีเมลของคุณแล้ว
                  </>
                ) : (
                  <>
                    ได้รับ <strong className="text-gold">+{pkg.hours + pkg.bonus} ชั่วโมง</strong> · คีย์ถูกเก็บไว้ในหน้า “คีย์ของฉัน” แล้ว
                  </>
                )}
              </p>
              <div className="card" style={{ padding: 14, background: 'var(--surface)' }}>
                <div className="tiny faint" style={{ marginBottom: 6 }}>
                  Product Key
                </div>
                <div className="key-code" style={{ fontSize: '1.02rem' }}>
                  {productKey}
                </div>
              </div>
              {redeemState?.message && (
                <div style={{ marginTop: 12 }}>
                  <Alert type={redeemState.type}>{redeemState.message}</Alert>
                </div>
              )}
              <div className="grid grid-2" style={{ marginTop: 14, gap: 10 }}>
                <CopyButton text={productKey} label="คัดลอกคีย์" className="btn btn-secondary btn-block" />
                {redeemState?.type === 'success' ? (
                  <Link href="/dashboard" className="btn btn-primary btn-block">
                    ไปกระเป๋าเวลา
                  </Link>
                ) : (
                  <button className="btn btn-primary btn-block" onClick={redeemNow} disabled={redeemState?.loading}>
                    {redeemState?.loading ? <Spinner /> : <Sparkles size={16} />} {redeemState?.loading ? 'กำลังเติม...' : 'เติมเข้าบัญชีเลย'}
                  </button>
                )}
              </div>
            </div>
          ) : error ? (
            <div style={{ marginTop: 16 }}>
              <Alert type="error">{error}</Alert>
            </div>
          ) : !order ? (
            <div className="center" style={{ padding: 40 }}>
              <Spinner size={24} />
              <div className="small muted" style={{ marginTop: 10 }}>
                กำลังสร้างคำสั่งซื้อ...
              </div>
            </div>
          ) : (
            <div className="stack" style={{ gap: 14, marginTop: 16 }}>
              <div className="checkout-pay">
                <div className="qr-box qr-box-sm">
                  <img src={order.qr_image_url} alt={`PromptPay QR ${formatThb(order.amount_thb)}`} width={170} height={170} />
                </div>
                <div className="stack" style={{ gap: 8, minWidth: 0 }}>
                  <div>
                    <div className="tiny faint">ยอดชำระ (โอนให้ตรงยอด)</div>
                    <div className="mono text-gold" style={{ fontSize: '1.45rem', fontWeight: 700 }}>
                      {formatThb(order.amount_thb)}
                    </div>
                  </div>
                  <div>
                    <div className="tiny faint">ชำระภายใน</div>
                    <div className={`mono ${remaining < 120 ? 'text-red' : ''}`} style={{ fontSize: '1.05rem', fontWeight: 600 }}>
                      {mm}:{ss}
                    </div>
                  </div>
                  <div className="tiny muted">
                    {PAYEE.name}
                    <br />
                    พร้อมเพย์ <span className="mono">{PAYEE.promptpay}</span>
                  </div>
                </div>
              </div>
              <p className="tiny faint center" style={{ margin: 0 }}>
                มือถือ: แคปหน้าจอ QR → เปิดแอปธนาคาร → สแกนจากรูปในเครื่อง
              </p>

              {remaining === 0 && <Alert type="error">หมดเวลาชำระเงินแล้ว หากโอนแล้วยังแนบสลิปได้ภายใน 24 ชั่วโมง</Alert>}

              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  e.target.value = '';
                  handleFile(f);
                }}
              />
              <button
                type="button"
                className={`slip-drop ${dragging ? 'is-drag' : ''} ${verifying ? 'is-busy' : ''} ${slipError?.type === 'error' ? 'is-error' : ''}`}
                onClick={() => !verifying && fileRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                disabled={verifying}
              >
                {slip ? <img src={slip.dataUrl} alt="สลิปที่แนบ" className="slip-thumb" /> : <ImageUp size={26} className="text-gold" />}
                <span className="slip-drop-text">
                  {verifying ? (
                    <>
                      <strong>
                        <Spinner /> กำลังตรวจสลิป...
                      </strong>
                      <span className="tiny muted">ใช้เวลาไม่กี่วินาที</span>
                    </>
                  ) : retryIn > 0 ? (
                    <>
                      <strong>รอธนาคารยืนยัน · ตรวจอีกครั้งใน {retryText}</strong>
                      <span className="tiny muted">หรือแตะเพื่อแนบสลิปใหม่</span>
                    </>
                  ) : slip ? (
                    <>
                      <strong>แตะเพื่อเลือกสลิปใหม่</strong>
                      <span className="tiny muted">หรือวาง (Ctrl+V) / ลากรูปมาวาง</span>
                    </>
                  ) : (
                    <>
                      <strong>โอนแล้ว? แนบสลิปที่นี่</strong>
                      <span className="tiny muted">แตะเพื่อเลือกรูป · วาง Ctrl+V · หรือลากไฟล์มาวาง</span>
                    </>
                  )}
                </span>
              </button>

              {slipError && (
                <Alert type={slipError.type === 'wait' ? 'gold' : 'error'}>
                  <strong>{slipError.message}</strong>
                  {slipError.hint && <div className="small" style={{ marginTop: 4 }}>{slipError.hint}</div>}
                </Alert>
              )}

              <label className="row small muted" style={{ gap: 8, cursor: 'pointer', justifyContent: 'center' }}>
                <input type="checkbox" checked={autoRedeem} onChange={(e) => setAutoRedeem(e.target.checked)} />
                เติมชั่วโมงเข้าบัญชีของฉันทันทีเมื่อชำระสำเร็จ
              </label>
              <p className="tiny faint center" style={{ margin: 0 }}>
                ระบบตรวจสลิปอัตโนมัติด้วย SlipOK (ยอดเงิน · บัญชีผู้รับ · สลิปซ้ำ) แล้วออก Product Key + ใบเสร็จทางอีเมลทันที
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
