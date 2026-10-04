'use client';

import { useState } from 'react';
import { AlertCircle, Check, CheckCircle2, Copy, Info, Loader2, LogIn, UserPlus } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function Spinner({ size = 16 }) {
  return <Loader2 size={size} className="spin" aria-hidden="true" />;
}

export function Alert({ type = 'info', children }) {
  const Icon = type === 'error' ? AlertCircle : type === 'success' ? CheckCircle2 : Info;
  return (
    <div className={`alert alert-${type}`} role={type === 'error' ? 'alert' : 'status'}>
      <Icon size={16} />
      <div>{children}</div>
    </div>
  );
}

export function PageHeader({ eyebrow, icon: Icon, title, description, actions }) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && (
          <div className="eyebrow">
            {Icon && <Icon size={14} />}
            {eyebrow}
          </div>
        )}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="row wrap">{actions}</div>}
    </div>
  );
}

export function StatCard({ icon: Icon, label, value, sub, tone, loading }) {
  const color = tone === 'green' ? 'var(--green)' : tone === 'red' ? 'var(--red)' : tone === 'gold' ? 'var(--gold)' : tone === 'sky' ? 'var(--sky)' : 'var(--text)';
  return (
    <div className="card stat">
      <div className="stat-label">
        {Icon && (
          <span className="icon-chip" style={{ color }}>
            <Icon size={16} />
          </span>
        )}
        {label}
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 30, width: '70%', marginTop: 10 }} />
      ) : (
        <div className="stat-value" style={{ color }}>
          {value}
        </div>
      )}
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="empty">
      {Icon && (
        <div className="empty-icon">
          <Icon size={26} />
        </div>
      )}
      <h3>{title}</h3>
      {children && <p className="small" style={{ maxWidth: 420, margin: '0 auto' }}>{children}</p>}
      {action && <div style={{ marginTop: 18 }}>{action}</div>}
    </div>
  );
}

export function CopyButton({ text, label = 'คัดลอก', className = 'btn btn-secondary btn-sm' }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard ถูกบล็อก */
    }
  };
  return (
    <button type="button" className={className} onClick={onCopy}>
      {copied ? <Check size={14} /> : <Copy size={14} />}
      {copied ? 'คัดลอกแล้ว' : label}
    </button>
  );
}

/** หน้าจอให้ล็อกอินก่อนใช้งาน */
export function AuthGate({ icon: Icon, title, description }) {
  const { openAuthModal } = useAuth();
  return (
    <div className="container container-narrow page">
      <div className="card card-gold card-pad center" style={{ padding: '44px 28px' }}>
        {Icon && (
          <div className="empty-icon" style={{ background: 'var(--gold-soft)', color: 'var(--gold)' }}>
            <Icon size={26} />
          </div>
        )}
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 8 }}>{title}</h1>
        <p className="muted" style={{ maxWidth: 460, margin: '0 auto 24px' }}>
          {description}
        </p>
        <div className="row wrap" style={{ justifyContent: 'center' }}>
          <button className="btn btn-primary" onClick={() => openAuthModal('login')}>
            <LogIn size={16} /> เข้าสู่ระบบ
          </button>
          <button className="btn btn-secondary" onClick={() => openAuthModal('register')}>
            <UserPlus size={16} /> สมัครฟรี รับ 48 ชม.
          </button>
        </div>
      </div>
    </div>
  );
}

export function PageLoading() {
  return (
    <div className="container page">
      <div className="skeleton" style={{ height: 34, width: 280, marginBottom: 12 }} />
      <div className="skeleton" style={{ height: 18, width: 420, marginBottom: 28 }} />
      <div className="grid grid-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="skeleton" style={{ height: 108 }} />
        ))}
      </div>
    </div>
  );
}
