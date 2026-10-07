'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Key, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Alert, Spinner } from './ui';
import { formatKeyInput } from '../lib/format';

/** กล่องเติม Product Key / คีย์โปรโมชัน — ใช้ทั้งหน้า /redeem และ /dashboard · รับ ?key= จากลิงก์โปรโมชัน */
export default function RedeemCard() {
  const { redeemKey } = useAuth();
  const [key, setKey] = useState('');
  const [status, setStatus] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const prefill = new URLSearchParams(window.location.search).get('key');
    if (prefill) setKey(formatKeyInput(prefill));
  }, []);

  const complete = key.length === 29;

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!complete) return;
    setSubmitting(true);
    setStatus(null);
    try {
      const res = await redeemKey(key);
      setStatus({ type: 'success', message: res.message });
      setKey('');
    } catch (err) {
      setStatus({ type: 'error', message: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card card-pad">
      <div className="stat-label" style={{ marginBottom: 6 }}>
        <span className="icon-chip text-gold">
          <Key size={16} />
        </span>
        เติม Product Key
      </div>
      <p className="small muted" style={{ marginBottom: 18 }}>
        กรอกรหัส 24 หลักจากหน้าซื้อชั่วโมงหรือคีย์โปรโมชัน ชั่วโมงจะถูกบวกเพิ่มจากยอดเดิมทันที
      </p>
      <form onSubmit={onSubmit} className="stack" style={{ gap: 14 }}>
        {status && <Alert type={status.type}>{status.message}</Alert>}
        <input
          className="input input-key"
          value={key}
          onChange={(e) => setKey(formatKeyInput(e.target.value))}
          placeholder="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"
          aria-label="Product Key"
          autoComplete="off"
          spellCheck={false}
        />
        <div className="row-between tiny faint">
          <span>{key.replace(/-/g, '').length}/24 ตัวอักษร</span>
          <Link href="/my-keys" className="text-sky">
            ดูคีย์ของฉัน
          </Link>
        </div>
        <button type="submit" className="btn btn-primary btn-block" disabled={!complete || submitting}>
          {submitting ? <Spinner /> : <Sparkles size={16} />}
          {submitting ? 'กำลังตรวจสอบ...' : 'เติมชั่วโมงเข้าบัญชี'}
        </button>
      </form>
    </div>
  );
}
