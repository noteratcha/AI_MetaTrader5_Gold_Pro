'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Eye, KeyRound, LayoutDashboard, Package, Shield, ShieldAlert, ToggleRight, Users } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Alert, AuthGate, EmptyState, Modal, PageLoading, Spinner } from '../ui';

const TABS = [
  { href: '/admin', label: 'ภาพรวม', icon: LayoutDashboard, exact: true },
  { href: '/admin/users', label: 'ผู้ใช้', icon: Users },
  { href: '/admin/packages', label: 'แพ็กเกจ', icon: Package },
  { href: '/admin/keys', label: 'คีย์ & คำสั่งซื้อ', icon: KeyRound },
  { href: '/admin/plans', label: 'แผนเทรด', icon: ToggleRight },
];

/** โครงหน้าแอดมิน: ตรวจสิทธิ์ + เมนูย่อย + แจ้งเตือนรหัสผ่านอ่อน */
export default function AdminShell({ title, description, actions, children }) {
  const { user, isLoading, isAdmin, viewMode, setViewMode } = useAuth();
  const pathname = usePathname();
  const [showChangePw, setShowChangePw] = useState(false);

  if (isLoading) return <PageLoading />;
  if (!user) return <AuthGate icon={Shield} title="สำหรับผู้ดูแลระบบเท่านั้น" description="กรุณาเข้าสู่ระบบด้วยบัญชี Admin" />;
  if (!isAdmin) {
    return (
      <div className="container container-narrow page">
        <div className="card">
          <EmptyState icon={ShieldAlert} title="ไม่มีสิทธิ์เข้าถึงหน้านี้">
            บัญชี {user.email} ไม่ใช่ผู้ดูแลระบบ
          </EmptyState>
        </div>
      </div>
    );
  }
  if (viewMode === 'user') {
    return (
      <div className="container container-narrow page">
        <div className="card">
          <EmptyState icon={Eye} title="กำลังอยู่ในโหมดผู้ใช้">
            <p style={{ marginBottom: 14 }}>สลับเป็นโหมดแอดมินเพื่อเข้าหน้าจัดการระบบ</p>
            <button className="btn btn-primary" onClick={() => setViewMode('admin')}>
              <Shield size={16} /> สลับเป็นโหมดแอดมิน
            </button>
          </EmptyState>
        </div>
      </div>
    );
  }

  return (
    <div className="container container-wide page">
      <div className="page-header">
        <div>
          <div className="eyebrow">
            <Shield size={14} /> Admin · {user.email}
          </div>
          <h1>{title}</h1>
          {description && <p>{description}</p>}
        </div>
        <div className="row wrap">
          {actions}
          <button className="btn btn-ghost btn-sm" onClick={() => setShowChangePw(true)}>
            เปลี่ยนรหัสผ่าน
          </button>
        </div>
      </div>

      {user.weakPassword && (
        <div style={{ marginBottom: 16 }}>
          <Alert type="error">
            <strong>รหัสผ่านแอดมินคาดเดาง่าย</strong> — บัญชีนี้ผลิตคีย์และแก้ไขผู้ใช้ได้ทั้งหมด กรุณา{' '}
            <button className="btn btn-danger btn-sm" style={{ marginLeft: 6 }} onClick={() => setShowChangePw(true)}>
              เปลี่ยนรหัสผ่านตอนนี้
            </button>
          </Alert>
        </div>
      )}

      <nav className="admin-tabs" aria-label="เมนูแอดมิน">
        {TABS.map(({ href, label, icon: Icon, exact }) => {
          const active = exact ? pathname === href : pathname?.startsWith(href);
          return (
            <Link key={href} href={href} className={`admin-tab ${active ? 'is-active' : ''}`}>
              <Icon size={16} /> {label}
            </Link>
          );
        })}
      </nav>

      {children}
      {showChangePw && <ChangePasswordModal onClose={() => setShowChangePw(false)} />}
    </div>
  );
}

function ChangePasswordModal({ onClose }) {
  const { changePassword } = useAuth();
  const [form, setForm] = useState({ current: '', next: '', confirm: '' });
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (form.next !== form.confirm) return setStatus({ type: 'error', message: 'รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน' });
    setBusy(true);
    setStatus(null);
    try {
      const res = await changePassword(form.current, form.next);
      setStatus({ type: 'success', message: res.message });
      setTimeout(onClose, 900);
    } catch (err) {
      setStatus({ type: 'error', message: err.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="เปลี่ยนรหัสผ่าน" onClose={onClose} width={420}>
      <form className="stack" style={{ gap: 12 }} onSubmit={submit}>
        {status && <Alert type={status.type}>{status.message}</Alert>}
        <label className="field">
          <span className="label">รหัสผ่านปัจจุบัน</span>
          <input className="input" type="password" value={form.current} onChange={(e) => setForm({ ...form, current: e.target.value })} autoComplete="current-password" />
        </label>
        <label className="field">
          <span className="label">รหัสผ่านใหม่ (แอดมิน: อย่างน้อย 10 ตัว ผสมตัวอักษร)</span>
          <input className="input" type="password" value={form.next} onChange={(e) => setForm({ ...form, next: e.target.value })} autoComplete="new-password" />
        </label>
        <label className="field">
          <span className="label">ยืนยันรหัสผ่านใหม่</span>
          <input className="input" type="password" value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} autoComplete="new-password" />
        </label>
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy && <Spinner />} บันทึกรหัสผ่านใหม่
        </button>
      </form>
    </Modal>
  );
}
