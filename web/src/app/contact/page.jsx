'use client';

import { MessageCircle, ExternalLink } from 'lucide-react';
import { CopyButton, PageHeader } from '../../components/ui';
import { LINE_ID, LINE_QR, LINE_URL } from '../../lib/contact';

const TOPICS = [
  'ชำระเงินแล้วชั่วโมงไม่เข้า / ตรวจสลิปไม่ผ่าน',
  'ติดตั้งหรือเข้าสู่ระบบโปรแกรม AI Gold Commander Pro ไม่ได้',
  'บอทไม่เข้าไม้ / เชื่อมต่อ MetaTrader 5 ไม่ได้',
  'สอบถามแผนเทรด ค่าบริการ และการใช้งานทั่วไป',
];

export default function ContactPage() {
  return (
    <div className="container page">
      <PageHeader
        eyebrow="Contact"
        icon={MessageCircle}
        title="ติดต่อแอดมิน"
        description="ทักแชทผ่าน LINE Official Account ของ GoldBot24 ได้เลย"
      />

      <div className="card card-gold card-pad" style={{ display: 'flex', flexWrap: 'wrap', gap: 28, alignItems: 'center' }}>
        <img
          src={LINE_QR}
          alt={`QR Code LINE ${LINE_ID}`}
          width={200}
          height={200}
          style={{ borderRadius: 12, background: '#fff', padding: 6 }}
        />
        <div style={{ flex: '1 1 260px' }}>
          <div className="small muted">LINE Official Account</div>
          <div className="row" style={{ gap: 8, margin: '4px 0 16px' }}>
            <span className="mono text-gold" style={{ fontSize: '1.6rem', fontWeight: 700 }}>{LINE_ID}</span>
            <CopyButton text={LINE_ID} />
          </div>
          <a
            className="btn btn-sm"
            href={LINE_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{ background: '#06C755', color: '#fff', borderColor: '#06C755' }}
          >
            <ExternalLink size={15} /> เพิ่มเพื่อน / ทักแชท LINE
          </a>
          <p className="small muted" style={{ marginTop: 14 }}>
            บนมือถือกดปุ่มเพื่อเปิดแอป LINE · บนคอมพิวเตอร์สแกน QR ด้วยแอป LINE ในมือถือ
          </p>
        </div>
      </div>

      <div className="card card-pad" style={{ marginTop: 20 }}>
        <div className="footer-title" style={{ marginBottom: 10 }}>เรื่องที่ติดต่อได้</div>
        <ul className="small" style={{ paddingLeft: 18, lineHeight: 1.9 }}>
          {TOPICS.map((t) => <li key={t}>{t}</li>)}
        </ul>
        <p className="small muted" style={{ marginTop: 10 }}>
          แจ้งอีเมลที่ใช้สมัคร และแนบภาพหน้าจอ/สลิป จะช่วยให้ตรวจสอบได้เร็วขึ้น · แอดมินไม่ขอรหัสผ่านหรือรหัส MT5 ของคุณทุกกรณี
        </p>
      </div>
    </div>
  );
}
