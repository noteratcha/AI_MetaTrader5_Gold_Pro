'use client';

import { useCallback, useEffect, useState } from 'react';
import { ImagePlus, Megaphone, Pencil, Trash2 } from 'lucide-react';
import AdminShell from '../../../components/admin/AdminShell';
import { Alert, Spinner } from '../../../components/ui';
import { NewsBody } from '../../../components/Announcements';
import { useAuth } from '../../../context/AuthContext';
import { formatThaiDateTime } from '../../../lib/format';

const EMPTY = { id: null, title: '', body: '', imageUrl: '', imageData: '', linkUrl: '', linkLabel: '', active: true, popup: true, startsAt: '', endsAt: '' };

// datetime-local (เวลาไทย) ↔ ISO
const toLocal = (iso) => (iso ? new Date(new Date(iso).getTime() + 7 * 3600000).toISOString().slice(0, 16) : '');
const fromLocal = (v) => (v ? new Date(`${v}:00+07:00`).toISOString() : '');

/** ย่อรูปให้กว้างไม่เกิน 1200px (JPEG) ก่อนส่ง — กันไฟล์ใหญ่เกิน */
function readImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (file.type === 'image/gif') return resolve(reader.result);
      const img = new Image();
      img.onload = () => {
        const scale = Math.min(1, 1200 / img.width);
        const c = document.createElement('canvas');
        c.width = Math.round(img.width * scale);
        c.height = Math.round(img.height * scale);
        c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
        resolve(c.toDataURL(file.type === 'image/png' ? 'image/png' : 'image/jpeg', 0.88));
      };
      img.onerror = reject;
      img.src = reader.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function AdminAnnouncementsPage() {
  const { apiFetch, isAdmin } = useAuth();
  const [items, setItems] = useState(null);
  const [setupRequired, setSetupRequired] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await apiFetch('/api/admin/announcements');
      setItems(res.items);
      setSetupRequired(Boolean(res.setupRequired));
    } catch (err) {
      setNotice({ type: 'error', message: err.message });
    }
  }, [apiFetch]);

  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin, load]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e?.target ? (e.target.type === 'checkbox' ? e.target.checked : e.target.value) : e }));

  const pickImage = async (file) => {
    if (!file) return;
    try {
      const data = await readImage(file);
      setForm((f) => ({ ...f, imageData: data, imageUrl: '' }));
    } catch {
      setNotice({ type: 'error', message: 'อ่านไฟล์รูปไม่ได้' });
    }
  };

  const save = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const payload = { ...form, startsAt: fromLocal(form.startsAt), endsAt: fromLocal(form.endsAt) };
      if (!payload.imageData) delete payload.imageData;
      await apiFetch('/api/admin/announcements', { method: form.id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
      setNotice({ type: 'success', message: form.id ? 'บันทึกการแก้ไขแล้ว' : 'เผยแพร่ข่าวแล้ว — แสดงบนเว็บภายใน 1 นาที และในโปรแกรมภายใน 15 นาที' });
      setForm(EMPTY);
      load();
    } catch (err) {
      setNotice({ type: 'error', message: err.message });
    } finally {
      setBusy(false);
    }
  };

  const remove = async (a) => {
    if (!window.confirm(`ลบข่าว "${a.title}"?`)) return;
    try {
      await apiFetch(`/api/admin/announcements?id=${a.id}`, { method: 'DELETE' });
      load();
    } catch (err) {
      setNotice({ type: 'error', message: err.message });
    }
  };

  const toggle = async (a) => {
    try {
      await apiFetch('/api/admin/announcements', { method: 'PUT', body: JSON.stringify({ ...a, active: !a.active }) });
      load();
    } catch (err) {
      setNotice({ type: 'error', message: err.message });
    }
  };

  const preview = { ...form, imageUrl: form.imageData || form.imageUrl };

  return (
    <AdminShell title="ข่าวสารและโปรโมชัน" description="ส่งข่าวพร้อมรูปภาพถึงผู้ใช้ทุกคน — แสดงเป็นป๊อปอัปบนเว็บและในโปรแกรม Gold Bot 24 (ครั้งแรกที่ผู้ใช้ยังไม่เคยเห็น) และอยู่ในหน้า /news">
      {setupRequired && <Alert type="warning">ยังไม่ได้สร้างตารางข่าวสาร — รัน <span className="mono">supabase_announcements_patch_09.sql</span> ใน Supabase SQL Editor ก่อน</Alert>}
      {notice && <Alert type={notice.type}>{notice.message}</Alert>}

      <div className="grid grid-2 section" style={{ alignItems: 'start' }}>
        <div className="card card-pad stack" style={{ gap: 12 }}>
          <h3 style={{ margin: 0 }}>{form.id ? 'แก้ไขข่าว' : 'สร้างข่าวใหม่'}</h3>
          <label className="stack" style={{ gap: 4 }}>
            <span className="small muted">หัวข้อ *</span>
            <input className="input" value={form.title} onChange={set('title')} maxLength={160} placeholder="เช่น โปรโมชันเติมชั่วโมง ลด 20% ถึงสิ้นเดือน" />
          </label>
          <label className="stack" style={{ gap: 4 }}>
            <span className="small muted">ข้อความ</span>
            <textarea className="input" rows={5} value={form.body} onChange={set('body')} maxLength={4000} placeholder="รายละเอียดโปรโมชัน / ข่าวสาร" />
          </label>
          <div className="stack" style={{ gap: 6 }}>
            <span className="small muted">รูปภาพ (PNG / JPG / WEBP / GIF ไม่เกิน 3 MB — ย่อเหลือกว้าง 1200px อัตโนมัติ)</span>
            <div className="row wrap" style={{ gap: 8 }}>
              <label className="btn btn-secondary btn-sm" style={{ cursor: 'pointer' }}>
                <ImagePlus size={15} /> เลือกรูป
                <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" hidden onChange={(e) => pickImage(e.target.files?.[0])} />
              </label>
              {(form.imageData || form.imageUrl) && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setForm((f) => ({ ...f, imageData: '', imageUrl: '' }))}>
                  เอารูปออก
                </button>
              )}
            </div>
          </div>
          <div className="grid grid-2" style={{ gap: 10 }}>
            <label className="stack" style={{ gap: 4 }}>
              <span className="small muted">ลิงก์ปุ่ม</span>
              <input className="input" value={form.linkUrl} onChange={set('linkUrl')} placeholder="/store หรือ https://..." />
            </label>
            <label className="stack" style={{ gap: 4 }}>
              <span className="small muted">ข้อความปุ่ม</span>
              <input className="input" value={form.linkLabel} onChange={set('linkLabel')} maxLength={60} placeholder="เติมชั่วโมงเลย" />
            </label>
            <label className="stack" style={{ gap: 4 }}>
              <span className="small muted">เริ่มแสดง (เวลาไทย)</span>
              <input className="input" type="datetime-local" value={form.startsAt} onChange={set('startsAt')} />
            </label>
            <label className="stack" style={{ gap: 4 }}>
              <span className="small muted">หยุดแสดง (เว้นว่าง = ไม่หมดอายุ)</span>
              <input className="input" type="datetime-local" value={form.endsAt} onChange={set('endsAt')} />
            </label>
          </div>
          <div className="row wrap" style={{ gap: 16 }}>
            <label className="row" style={{ gap: 6 }}>
              <input type="checkbox" checked={form.active} onChange={set('active')} /> เปิดแสดง
            </label>
            <label className="row" style={{ gap: 6 }}>
              <input type="checkbox" checked={form.popup} onChange={set('popup')} /> เด้งป๊อปอัปให้ผู้ใช้ที่ยังไม่เคยเห็น
            </label>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn btn-primary" onClick={save} disabled={busy || setupRequired}>
              {busy && <Spinner />} {form.id ? 'บันทึกการแก้ไข' : 'เผยแพร่ข่าว'}
            </button>
            {form.id && (
              <button className="btn btn-ghost" onClick={() => setForm(EMPTY)}>
                ยกเลิกการแก้ไข
              </button>
            )}
          </div>
        </div>

        <div className="card card-pad">
          <div className="small muted" style={{ marginBottom: 10 }}>ตัวอย่างที่ผู้ใช้จะเห็น</div>
          <h3 style={{ marginTop: 0 }}>{form.title || 'หัวข้อข่าว'}</h3>
          <NewsBody item={preview} />
        </div>
      </div>

      <div className="card section">
        <div className="card-header">
          <h3>
            <Megaphone size={17} className="text-gold" /> ข่าวทั้งหมด
          </h3>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>หัวข้อ</th>
                <th>ช่วงแสดง</th>
                <th>สถานะ</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items === null && (
                <tr>
                  <td colSpan={4}>
                    <Spinner />
                  </td>
                </tr>
              )}
              {items?.length === 0 && (
                <tr>
                  <td colSpan={4} className="muted">
                    ยังไม่มีข่าว
                  </td>
                </tr>
              )}
              {items?.map((a) => (
                <tr key={a.id}>
                  <td>
                    <strong>{a.title}</strong>
                    {a.imageUrl && <span className="badge badge-muted" style={{ marginLeft: 8 }}>มีรูป</span>}
                    {a.popup && <span className="badge badge-sky" style={{ marginLeft: 6 }}>ป๊อปอัป</span>}
                  </td>
                  <td className="small muted nowrap">
                    {formatThaiDateTime(a.startsAt)} → {a.endsAt ? formatThaiDateTime(a.endsAt) : 'ไม่หมดอายุ'}
                  </td>
                  <td>
                    <button className={`badge ${a.active ? 'badge-green' : 'badge-muted'}`} onClick={() => toggle(a)} style={{ cursor: 'pointer', border: 'none' }}>
                      {a.active ? 'แสดงอยู่' : 'ซ่อน'}
                    </button>
                  </td>
                  <td className="nowrap" style={{ textAlign: 'right' }}>
                    <button
                      className="btn btn-ghost btn-icon"
                      title="แก้ไข"
                      onClick={() => {
                        setForm({ ...EMPTY, ...a, imageData: '', imageUrl: a.imageUrl || '', linkUrl: a.linkUrl || '', linkLabel: a.linkLabel || '', startsAt: toLocal(a.startsAt), endsAt: toLocal(a.endsAt) });
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }}
                    >
                      <Pencil size={15} />
                    </button>
                    <button className="btn btn-ghost btn-icon" title="ลบ" onClick={() => remove(a)}>
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AdminShell>
  );
}
