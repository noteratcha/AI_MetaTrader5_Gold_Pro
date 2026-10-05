'use client';

import { useCallback, useEffect, useState } from 'react';
import { Package, Pencil, Plus, Trash2 } from 'lucide-react';
import AdminShell from '../../../components/admin/AdminShell';
import { Alert, EmptyState, Modal, Spinner } from '../../../components/ui';
import { useAuth } from '../../../context/AuthContext';
import { formatThb } from '../../../lib/format';

const EMPTY = { name: '', hours: 100, bonus: 0, price: 100, badge: '', desc: '', accent: 'gold', featured: false, sortOrder: 10, isActive: true };
const ACCENTS = [
  ['gold', 'ทอง'],
  ['orange', 'ส้ม'],
  ['emerald', 'เขียว'],
  ['sky', 'ฟ้า'],
];

export default function AdminPackagesPage() {
  const { apiFetch, isAdmin } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(null);
  const [editing, setEditing] = useState(null); // package | 'new'
  const [deleting, setDeleting] = useState(null);

  const load = useCallback(async () => {
    try {
      setData(await apiFetch('/api/admin/packages'));
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }, [apiFetch]);

  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin, load]);

  const onSaved = (msg) => {
    setEditing(null);
    setDeleting(null);
    setNotice({ type: 'success', message: msg });
    load();
  };

  return (
    <AdminShell
      title="แพ็กเกจชั่วโมง"
      description="ราคาและชั่วโมงที่ตั้งที่นี่ใช้ทันทีกับหน้าร้านและการออกคีย์ (คำสั่งซื้อเดิมใช้ค่าตอนที่สั่งซื้อ)"
      actions={
        <button className="btn btn-primary btn-sm" onClick={() => setEditing('new')} disabled={data?.source === 'default'}>
          <Plus size={15} /> เพิ่มแพ็กเกจ
        </button>
      }
    >
      {error && <Alert type="error">{error}</Alert>}
      {data?.source === 'default' && (
        <div style={{ marginBottom: 14 }}>
          <Alert type="gold">กำลังแสดงแพ็กเกจเริ่มต้นจากโค้ด — รัน <code>supabase_admin_patch_02.sql</code> ก่อน จึงจะเพิ่ม/แก้ไขได้</Alert>
        </div>
      )}
      {notice && (
        <div style={{ marginBottom: 14 }}>
          <Alert type={notice.type}>{notice.message}</Alert>
        </div>
      )}

      <div className="card">
        {!data ? (
          <div className="card-body">
            <div className="skeleton" style={{ height: 160 }} />
          </div>
        ) : data.packages.length === 0 ? (
          <EmptyState icon={Package} title="ยังไม่มีแพ็กเกจ" />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>ลำดับ</th>
                  <th>ชื่อแพ็กเกจ</th>
                  <th className="num">ชั่วโมง</th>
                  <th className="num">โบนัส</th>
                  <th className="num">รวม</th>
                  <th className="num">ราคา</th>
                  <th className="num">บาท/ชม.</th>
                  <th>สถานะ</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.packages.map((p) => (
                  <tr key={p.id} style={{ opacity: p.isActive ? 1 : 0.55 }}>
                    <td className="mono faint">{p.sortOrder}</td>
                    <td>
                      <div className="row" style={{ gap: 6 }}>
                        <strong>{p.name}</strong>
                        {p.featured && <span className="badge badge-gold">แนะนำ</span>}
                        {p.badge && <span className="badge badge-muted">{p.badge}</span>}
                      </div>
                      <div className="tiny faint">{p.desc}</div>
                    </td>
                    <td className="num">{p.hours}</td>
                    <td className="num text-green">{p.bonus ? `+${p.bonus}` : '—'}</td>
                    <td className="num" style={{ fontWeight: 700 }}>
                      {p.hours + p.bonus}
                    </td>
                    <td className="num text-gold" style={{ fontWeight: 700 }}>
                      {formatThb(p.price)}
                    </td>
                    <td className="num faint">{(p.price / Math.max(1, p.hours + p.bonus)).toFixed(2)}</td>
                    <td>{p.isActive ? <span className="badge badge-green">เปิดขาย</span> : <span className="badge badge-muted">ปิดขาย</span>}</td>
                    <td>
                      <div className="row" style={{ gap: 6, justifyContent: 'flex-end' }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => setEditing(p)} disabled={data.source === 'default'}>
                          <Pencil size={14} /> แก้ไข
                        </button>
                        <button className="btn btn-ghost btn-icon" onClick={() => setDeleting(p)} disabled={data.source === 'default'} aria-label="ลบ">
                          <Trash2 size={15} className="text-red" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing && <PackageModal pkg={editing === 'new' ? null : editing} onClose={() => setEditing(null)} onSaved={onSaved} />}
      {deleting && <DeletePackageModal pkg={deleting} onClose={() => setDeleting(null)} onDone={onSaved} />}
    </AdminShell>
  );
}

function PackageModal({ pkg, onClose, onSaved }) {
  const { apiFetch } = useAuth();
  const [form, setForm] = useState(pkg ? { ...pkg, badge: pkg.badge || '' } : EMPTY);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k, cast = (v) => v) => (e) => setForm((f) => ({ ...f, [k]: cast(e.target.type === 'checkbox' ? e.target.checked : e.target.value) }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    const body = { ...form, hours: Number(form.hours), bonus: Number(form.bonus), price: Number(form.price), sortOrder: Number(form.sortOrder) };
    try {
      if (pkg) await apiFetch(`/api/admin/packages/${pkg.id}`, { method: 'PATCH', body: JSON.stringify(body) });
      else await apiFetch('/api/admin/packages', { method: 'POST', body: JSON.stringify(body) });
      onSaved(pkg ? `บันทึกแพ็กเกจ ${form.name} แล้ว` : `เพิ่มแพ็กเกจ ${form.name} แล้ว`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <Modal title={pkg ? `แก้ไข ${pkg.name}` : 'เพิ่มแพ็กเกจใหม่'} onClose={onClose} width={520}>
      <form className="stack" style={{ gap: 12 }} onSubmit={submit}>
        {error && <Alert type="error">{error}</Alert>}
        <label className="field">
          <span className="label">ชื่อแพ็กเกจ</span>
          <input className="input" value={form.name} onChange={set('name')} maxLength={60} required />
        </label>
        <div className="grid grid-3" style={{ gap: 12 }}>
          <label className="field">
            <span className="label">ชั่วโมง</span>
            <input className="input" type="number" min="1" value={form.hours} onChange={set('hours')} required />
          </label>
          <label className="field">
            <span className="label">โบนัส (ชม.)</span>
            <input className="input" type="number" min="0" value={form.bonus} onChange={set('bonus')} />
          </label>
          <label className="field">
            <span className="label">ราคา (บาท)</span>
            <input className="input" type="number" min="20" value={form.price} onChange={set('price')} required />
          </label>
        </div>
        <div className="grid grid-2" style={{ gap: 12 }}>
          <label className="field">
            <span className="label">ป้าย (เช่น ขายดี)</span>
            <input className="input" value={form.badge} onChange={set('badge')} maxLength={30} />
          </label>
          <label className="field">
            <span className="label">สีไอคอน</span>
            <select className="input" value={form.accent} onChange={set('accent')}>
              {ACCENTS.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="field">
          <span className="label">คำอธิบาย</span>
          <input className="input" value={form.desc} onChange={set('desc')} maxLength={200} />
        </label>
        <div className="row wrap" style={{ gap: 18 }}>
          <label className="row small">
            <input type="checkbox" checked={form.isActive} onChange={set('isActive')} style={{ width: 'auto' }} /> เปิดขาย
          </label>
          <label className="row small">
            <input type="checkbox" checked={form.featured} onChange={set('featured')} style={{ width: 'auto' }} /> แพ็กเกจแนะนำ (ไฮไลต์สีทอง)
          </label>
          <label className="row small">
            ลำดับ <input className="input" type="number" value={form.sortOrder} onChange={set('sortOrder')} style={{ width: 80, height: 34 }} />
          </label>
        </div>
        <div className="small muted">
          ลูกค้าจะได้ <strong className="text-gold">{Number(form.hours || 0) + Number(form.bonus || 0)} ชม.</strong> ในราคา{' '}
          <strong>{formatThb(form.price)}</strong>
        </div>
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy && <Spinner />} {pkg ? 'บันทึก' : 'เพิ่มแพ็กเกจ'}
        </button>
      </form>
    </Modal>
  );
}

function DeletePackageModal({ pkg, onClose, onDone }) {
  const { apiFetch } = useAuth();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [force, setForce] = useState(false);
  const del = async () => {
    setBusy(true);
    try {
      const res = await apiFetch(`/api/admin/packages/${pkg.id}${force ? '?force=1' : ''}`, { method: 'DELETE' });
      onDone(res.message || `ลบแพ็กเกจ ${pkg.name} แล้ว`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };
  return (
    <Modal title="ลบแพ็กเกจ" onClose={onClose} width={420}>
      <div className="stack" style={{ gap: 12 }}>
        {error && <Alert type="error">{error}</Alert>}
        <p className="small">
          ลบ <strong>{pkg.name}</strong> ออกจากร้านค้า? ถ้ามีคำสั่งซื้อที่อ้างอิงแพ็กเกจนี้อยู่ ระบบจะ <strong>ปิดการขาย</strong> แทนการลบ
        </p>
        <label className="row small" style={{ gap: 8, alignItems: 'flex-start', cursor: 'pointer' }}>
          <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} style={{ marginTop: 3 }} />
          <span>
            <strong className="text-red">ลบถาวร</strong> แม้มีคำสั่งซื้ออ้างอิง — คำสั่งซื้อ ยอดเงิน และคีย์เดิมยังอยู่ครบ แค่ไม่ผูกกับแพ็กเกจนี้แล้ว (ย้อนกลับไม่ได้)
          </span>
        </label>
        <button className="btn btn-danger btn-block" onClick={del} disabled={busy}>
          {busy && <Spinner />} {force ? 'ยืนยันลบถาวร' : 'ยืนยันลบ'}
        </button>
      </div>
    </Modal>
  );
}
