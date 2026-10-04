'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { Gift, Inbox, Key, Lock, ShoppingBag, Sparkles } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Alert, AuthGate, CopyButton, EmptyState, PageHeader, PageLoading, Spinner } from '../../components/ui';
import { formatThaiDateTime, formatThb } from '../../lib/format';
import { markLocalKeyRedeemed, readLocalKeys } from '../../lib/localKeys';

export default function MyKeysPage() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <PageLoading />;
  if (!user) {
    return <AuthGate icon={Lock} title="เข้าสู่ระบบเพื่อดูคีย์ของคุณ" description="Product Key ทั้งหมดที่คุณซื้อจะถูกเก็บไว้ในบัญชีอย่างปลอดภัย" />;
  }
  return <KeyVault />;
}

function KeyVault() {
  const { user, apiFetch, redeemKey } = useAuth();
  const [serverKeys, setServerKeys] = useState(null);
  const [filter, setFilter] = useState('all');
  const [busyKey, setBusyKey] = useState(null);
  const [notice, setNotice] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await apiFetch('/api/user/keys');
      setServerKeys(res.keys || []);
    } catch (err) {
      setServerKeys([]);
      setNotice({ type: 'error', message: err.message });
    }
  }, [apiFetch]);

  useEffect(() => {
    load();
  }, [load]);

  const keys = useMemo(() => {
    if (!serverKeys) return null;
    const merged = [...serverKeys];
    for (const local of readLocalKeys(user.email)) {
      if (!merged.some((k) => k.keyCode === local.keyCode)) merged.push(local);
    }
    return merged.sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));
  }, [serverKeys, user.email]);

  const visible = (keys || []).filter((k) => filter === 'all' || (filter === 'unused' ? k.status !== 'REDEEMED' : k.status === 'REDEEMED'));
  const unusedCount = (keys || []).filter((k) => k.status !== 'REDEEMED').length;

  const redeem = async (keyCode) => {
    setBusyKey(keyCode);
    setNotice(null);
    try {
      const res = await redeemKey(keyCode);
      setNotice({ type: 'success', message: res.message });
      markLocalKeyRedeemed(user.email, keyCode);
      await load();
    } catch (err) {
      setNotice({ type: 'error', message: err.message });
      if (err.status === 409) {
        markLocalKeyRedeemed(user.email, keyCode);
        await load();
      }
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className="container page">
      <PageHeader
        eyebrow="Key Vault"
        icon={Key}
        title="คีย์ของฉัน"
        description="Product Key ที่คุณซื้อ ใช้เติมชั่วโมงได้ทั้งบนเว็บและในโปรแกรม Desktop"
        actions={
          <Link href="/store" className="btn btn-primary btn-sm">
            <ShoppingBag size={15} /> ซื้อชั่วโมงเพิ่ม
          </Link>
        }
      />

      {notice && (
        <div style={{ marginBottom: 16 }}>
          <Alert type={notice.type}>{notice.message}</Alert>
        </div>
      )}

      <div className="row-between wrap" style={{ marginBottom: 16 }}>
        <div className="segmented" style={{ width: 'min(100%, 360px)' }}>
          {[
            ['all', 'ทั้งหมด'],
            ['unused', `พร้อมใช้ (${unusedCount})`],
            ['used', 'ใช้แล้ว'],
          ].map(([value, label]) => (
            <button key={value} className={filter === value ? 'is-active' : ''} onClick={() => setFilter(value)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {keys === null ? (
        <div className="stack">
          {[0, 1].map((i) => (
            <div key={i} className="skeleton" style={{ height: 110 }} />
          ))}
        </div>
      ) : visible.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={Inbox}
            title={filter === 'all' ? 'ยังไม่มี Product Key' : 'ไม่มีคีย์ในหมวดนี้'}
            action={
              filter === 'all' && (
                <Link href="/store" className="btn btn-primary">
                  ไปที่ร้านค้า
                </Link>
              )
            }
          >
            {filter === 'all' ? 'เมื่อคุณซื้อแพ็กเกจชั่วโมง คีย์ 24 หลักจะถูกเก็บไว้ที่นี่อัตโนมัติ' : null}
          </EmptyState>
        </div>
      ) : (
        <div className="stack">
          {visible.map((k) => {
            const used = k.status === 'REDEEMED';
            return (
              <div key={k.keyCode} className={`card card-pad ${used ? '' : 'card-gold'}`} style={{ opacity: used ? 0.75 : 1 }}>
                <div className="row-between wrap" style={{ alignItems: 'flex-start' }}>
                  <div>
                    <div className="row wrap" style={{ gap: 8, marginBottom: 4 }}>
                      {k.source === 'promo' ? <Gift size={16} className="text-gold" /> : <Key size={16} className="text-gold" />}
                      <strong>{k.packageName}</strong>
                      <span className={`badge ${used ? 'badge-muted' : 'badge-green'}`}>{used ? 'ใช้แล้ว' : 'พร้อมใช้'}</span>
                    </div>
                    <div className="tiny faint">
                      {formatThaiDateTime(k.createdAt)}
                      {k.orderId ? ` · ${k.orderId}` : ''}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div className="mono text-gold" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                      +{k.hours} ชม.
                    </div>
                    {k.price > 0 && <div className="tiny faint">{formatThb(k.price)}</div>}
                  </div>
                </div>

                <div className="key-row">
                  <span className="key-code" style={{ color: used ? 'var(--text-3)' : undefined }}>
                    {k.keyCode}
                  </span>
                  <div className="row">
                    <CopyButton text={k.keyCode} />
                    {!used && (
                      <button className="btn btn-primary btn-sm" onClick={() => redeem(k.keyCode)} disabled={busyKey === k.keyCode}>
                        {busyKey === k.keyCode ? <Spinner size={14} /> : <Sparkles size={14} />} เติมเข้าบัญชี
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
