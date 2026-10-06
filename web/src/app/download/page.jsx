'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, Download, ExternalLink, FileArchive, MonitorDown, ShieldCheck } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { CopyButton, PageHeader } from '../../components/ui';
import { formatThaiDateTime } from '../../lib/format';

const STEPS = [
  { title: 'ดาวน์โหลดตัวติดตั้ง', text: 'กดปุ่มดาวน์โหลดด้านบน จะได้ไฟล์ GoldBot24_Setup_v….exe (ประมาณ 57 MB)' },
  {
    title: 'ติดตั้งโปรแกรม',
    text: 'ดับเบิลคลิกไฟล์ Setup → Next จนเสร็จ (ไม่ต้องใช้สิทธิ์ Admin) · ถ้า Windows ขึ้น “Windows protected your PC” ให้กด More info → Run anyway',
  },
  { title: 'เปิด MetaTrader 5', text: 'ล็อกอินบัญชี FBS ใน MT5 ค้างไว้ และเปิด Algo Trading' },
  { title: 'เปิดโปรแกรม', text: 'ดับเบิลคลิกไอคอน “AI Gold Commander Pro” บน Desktop แล้วเข้าสู่ระบบด้วยบัญชีเดียวกับเว็บนี้' },
  { title: 'เริ่มบอท', text: 'กด “เริ่มการทำงานบอท” — ติดตามพอร์ตได้ที่หน้า “พอร์ตสด” บนเว็บ' },
];

function changelogLines(text) {
  return String(text || '')
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.startsWith('- '))
    .map((l) => l.slice(2).replace(/`/g, ''))
    .slice(0, 10);
}

export default function DownloadPage() {
  const { user, openAuthModal, apiFetch } = useAuth();

  // นับยอดดาวน์โหลด (ไม่รอผล — keepalive ให้ส่งได้แม้หน้ากำลังเปลี่ยนไปดาวน์โหลด)
  const trackDownload = (file) => {
    apiFetch('/api/track', {
      method: 'POST',
      keepalive: true,
      body: JSON.stringify({ event: 'app_download', version: release?.version, file }),
    }).catch(() => {});
  };
  const [release, setRelease] = useState(null);

  useEffect(() => {
    fetch('/api/release')
      .then((r) => r.json())
      .then((d) => setRelease(d.release || {}))
      .catch(() => setRelease({}));
  }, []);

  const notes = changelogLines(release?.changelog);
  const sizeMb = release?.size_bytes ? (release.size_bytes / 1048576).toFixed(1) : null;

  return (
    <div className="container page">
      <PageHeader
        eyebrow="Download"
        icon={MonitorDown}
        title="ดาวน์โหลดโปรแกรม AI Gold Commander Pro"
        description="โปรแกรมเทรดทองคำอัตโนมัติสำหรับ Windows 10/11 ใช้งานคู่กับ MetaTrader 5"
      />

      <div className="grid grid-main-side" style={{ alignItems: 'start' }}>
        <div className="stack" style={{ gap: 16 }}>
          <div className="card card-gold card-pad">
            {release === null ? (
              <div className="skeleton" style={{ height: 120 }} />
            ) : (
              <>
                <div className="row wrap" style={{ gap: 10, marginBottom: 6 }}>
                  <FileArchive size={22} className="text-gold" />
                  <span style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                    {release.version ? `เวอร์ชัน ${release.version}` : 'เวอร์ชันล่าสุด'}
                  </span>
                  <span className="badge badge-green">ล่าสุด</span>
                </div>
                <div className="small muted" style={{ marginBottom: 20 }}>
                  {release.released_at ? `เผยแพร่ ${formatThaiDateTime(release.released_at)}` : ''}
                  {sizeMb ? ` · ขนาด ${sizeMb} MB` : ''} · Windows 10/11 (64-bit)
                </div>
                <div className="row wrap" style={{ gap: 10 }}>
                  <a
                    className="btn btn-primary btn-lg"
                    href={release.download_url || release.releases_page}
                    rel="noopener noreferrer"
                    onClick={() => trackDownload(release.is_installer ? 'Setup.exe' : 'ZIP')}
                  >
                    <Download size={18} /> ดาวน์โหลด {release.is_installer ? 'ตัวติดตั้ง (.exe)' : release.file_name ? '(.zip)' : ''}
                  </a>
                  {release.zip_url && (
                    <a
                      className="btn btn-ghost btn-lg"
                      href={release.zip_url}
                      rel="noopener noreferrer"
                      title="แบบไม่ต้องติดตั้ง: แตกไฟล์แล้วเปิด .exe"
                      onClick={() => trackDownload('ZIP')}
                    >
                      <FileArchive size={16} /> แบบ ZIP
                    </a>
                  )}
                  {release.releases_page && (
                    <a className="btn btn-secondary btn-lg" href={release.releases_page} target="_blank" rel="noopener noreferrer">
                      ทุกเวอร์ชัน <ExternalLink size={16} />
                    </a>
                  )}
                </div>
                {release.checksum_sha256 && (
                  <div className="key-row" style={{ marginTop: 18 }}>
                    <div style={{ minWidth: 0 }}>
                      <div className="tiny faint">SHA-256 (ตรวจสอบว่าไฟล์ไม่ถูกแก้ไข)</div>
                      <div className="mono tiny" style={{ wordBreak: 'break-all' }}>
                        {release.checksum_sha256}
                      </div>
                    </div>
                    <CopyButton text={release.checksum_sha256} />
                  </div>
                )}
              </>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <h3>วิธีติดตั้ง</h3>
            </div>
            <div className="card-body stack" style={{ gap: 16 }}>
              {STEPS.map((s, i) => (
                <div key={s.title} className="row" style={{ alignItems: 'flex-start', gap: 14 }}>
                  <span className="step-num">{i + 1}</span>
                  <div>
                    <div style={{ fontWeight: 600 }}>{s.title}</div>
                    <div className="small muted">{s.text}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="stack" style={{ gap: 16 }}>
          {notes.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h3>มีอะไรใหม่</h3>
              </div>
              <div className="card-body stack" style={{ gap: 10 }}>
                {notes.map((n) => (
                  <div key={n} className="row small" style={{ alignItems: 'flex-start' }}>
                    <CheckCircle2 size={16} className="text-green" style={{ flexShrink: 0, marginTop: 3 }} />
                    <span>{n}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="card card-pad">
            <div className="row" style={{ marginBottom: 8 }}>
              <ShieldCheck size={18} className="text-gold" />
              <strong>Windows SmartScreen</strong>
            </div>
            <p className="small muted">
              ครั้งแรกที่เปิด Windows อาจแสดง “Windows protected your PC” เพราะโปรแกรมยังไม่ได้ลงลายเซ็นดิจิทัล ให้กด <strong>More info → Run anyway</strong>
            </p>
          </div>

          {!user && (
            <div className="card card-pad">
              <p className="small muted" style={{ marginBottom: 12 }}>
                ต้องมีบัญชี GoldBot24 เพื่อเข้าใช้งานโปรแกรม — สมัครวันนี้รับฟรี 48 ชั่วโมง
              </p>
              <button className="btn btn-primary btn-block" onClick={() => openAuthModal('register')}>
                สมัครสมาชิกฟรี
              </button>
            </div>
          )}
          {user && (
            <Link href="/store" className="card card-pad card-interactive small" style={{ display: 'block' }}>
              <strong>เวลาใช้งานไม่พอ?</strong>
              <div className="muted">ซื้อชั่วโมงเพิ่ม 1 บาท/ชั่วโมง →</div>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
