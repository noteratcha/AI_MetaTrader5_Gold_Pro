'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Download } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { PLAN_LIST } from '../lib/packages';
import { LINE_ID, LINE_URL } from '../lib/contact';

export default function Footer() {
  const { isAdminView } = useAuth();
  const [release, setRelease] = useState(null);

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
              <li><Link href="/store">ซื้อชั่วโมง</Link></li>
              <li><Link href="/my-keys">คีย์ของฉัน</Link></li>
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
            <div className="footer-title">โปรแกรม AI Gold Commander Pro</div>
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

        <div className="footer-bottom">
          <span>© {new Date().getFullYear()} GoldBot24 · AI MetaTrader 5 Gold Pro</span>
          <span>การเทรดมีความเสี่ยง ผลตอบแทนในอดีตไม่ได้รับประกันผลในอนาคต</span>
        </div>
      </div>
    </footer>
  );
}
