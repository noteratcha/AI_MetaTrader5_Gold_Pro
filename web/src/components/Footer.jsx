'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Bot, Download, Eye } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { PLAN_LIST } from '../lib/packages';
import { LINE_ID, LINE_URL } from '../lib/contact';

export default function Footer() {
  const { isAdminView } = useAuth();
  const [release, setRelease] = useState(null);

  const [counts, setCounts] = useState(null);

  // นับการเข้าชมเว็บ 1 ครั้งต่อการเปิดแท็บ (sessionStorage) + โหลดตัวเลขสะสม
  useEffect(() => {
    try {
      if (!sessionStorage.getItem('gb24_visit')) {
        sessionStorage.setItem('gb24_visit', '1');
        fetch('/api/track', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ event: 'web_visit' }) }).catch(() => {});
      }
    } catch {}
    fetch('/api/public-stats')
      .then((r) => r.json())
      .then((d) => d.success && setCounts(d))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch('/api/release')
      .then((r) => r.json())
      .then((d) => setRelease(d.release || null))
      .catch(() => {});
  }, []);

  return (
    <footer className="footer">
      <div className="container container-wide">
        <div className="footer-grid">
          <div>
            <div className="row" style={{ marginBottom: 12 }}>
              <span className="logo-mark">
                <img src="/store_logo.png" alt="" />
              </span>
              <strong style={{ fontSize: '1.05rem' }}>
                Gold<span className="text-gold">Bot24</span>
              </strong>
            </div>
            <p className="small muted" style={{ maxWidth: 320 }}>
              บอทเทรดทองคำ (XAUUSD) ด้วย AI เชื่อมต่อ MetaTrader 5 · คิดค่าบริการตามจริง 1 บาท/ชั่วโมง เฉพาะเวลาที่บอททำงาน
            </p>
            <a href={LINE_URL} target="_blank" rel="noopener noreferrer" className="small" style={{ color: '#06C755', fontWeight: 600 }}>
              ติดต่อแอดมิน LINE {LINE_ID}
            </a>
          </div>

          <div>
            <div className="footer-title">เมนู</div>
            <ul className="footer-links">
              <li><Link href="/">พอร์ตสด</Link></li>
              <li><Link href="/dashboard">กระเป๋าเวลา & สถิติ</Link></li>
              <li><Link href="/calendar">ปฏิทินเศรษฐกิจ</Link></li>
              <li><Link href="/backtest">แผนเทรด &amp; ผลทดสอบย้อนหลัง</Link></li>
              <li><Link href="/store">เติมชั่วโมง</Link></li>
              <li><Link href="/dashboard?keys=1">คีย์ของฉัน</Link></li>
              <li><Link href="/guide">คู่มือการใช้งาน</Link></li>
              <li><Link href="/contact">ติดต่อแอดมิน</Link></li>
              {isAdminView && <li><Link href="/admin">Admin</Link></li>}
            </ul>
          </div>

          <div>
            <div className="footer-title">แผนเทรดทองคำ</div>
            <ul className="footer-links">
              {PLAN_LIST.map((p) => (
                <li key={p.key} className="row-between">
                  <span>{p.label}</span>
                  <span className="faint tiny">{p.tag}</span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <div className="footer-title">โปรแกรม Gold Bot 24</div>
            <p className="small muted" style={{ marginBottom: 12 }}>
              ติดตั้งบน Windows 10/11 หรือ VPS ใช้งานคู่กับ MetaTrader 5
              {release?.version && (
                <>
                  {' '}· เวอร์ชันล่าสุด <span className="mono text-gold">v{release.version}</span>
                </>
              )}
            </p>
            <Link className="btn btn-outline-gold btn-sm" href="/download">
              <Download size={15} /> ดาวน์โหลดโปรแกรม
            </Link>
          </div>
        </div>

        {counts && (counts.botRuns !== null || counts.webVisits !== null) && (
          <div className="row wrap" style={{ gap: 24, justifyContent: 'center', padding: '14px 0', borderTop: '1px solid var(--border, #262B36)' }}>
            {counts.botRuns !== null && (
              <span className="row small" style={{ gap: 8 }}>
                <Bot size={16} className="text-gold" />
                <span className="muted">รันบอทแล้ว</span>
                <strong className="mono text-gold">{counts.botRuns.toLocaleString('th-TH')}</strong>
                <span className="muted">ครั้ง</span>
              </span>
            )}
            {counts.webVisits !== null && (
              <span className="row small" style={{ gap: 8 }}>
                <Eye size={16} className="text-sky" />
                <span className="muted">เข้าชมเว็บ</span>
                <strong className="mono">{counts.webVisits.toLocaleString('th-TH')}</strong>
                <span className="muted">ครั้ง</span>
              </span>
            )}
          </div>
        )}

        <div className="footer-bottom">
          <span>© {new Date().getFullYear()} GoldBot24 · AI MetaTrader 5 Gold Pro</span>
          <span>การเทรดมีความเสี่ยง ผลตอบแทนในอดีตไม่ได้รับประกันผลในอนาคต</span>
        </div>
      </div>
    </footer>
  );
}
