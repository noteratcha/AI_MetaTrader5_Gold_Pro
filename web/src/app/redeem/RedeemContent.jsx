'use client';

import Link from 'next/link';
import { Clock, Gift, Lock, ShoppingBag, Ticket } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { AuthGate, PageHeader, PageLoading } from '../../components/ui';
import RedeemCard from '../../components/RedeemCard';
import { formatHHMM } from '../../lib/format';

export default function RedeemContent() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <PageLoading />;
  if (!user) {
    // ลิงก์ /redeem?key=... ยังอยู่ใน URL หลังเข้าสู่ระบบ คีย์จึงถูกกรอกให้อัตโนมัติ
    return <AuthGate icon={Lock} title="เข้าสู่ระบบเพื่อเติมคีย์" description="เติมชั่วโมงใช้งานด้วย Product Key หรือคีย์โปรโมชัน ชั่วโมงจะเข้าบัญชีของคุณทันที" />;
  }
  return (
    <div className="container container-narrow page">
      <PageHeader
        eyebrow="Redeem"
        icon={Ticket}
        title="เติมคีย์"
        description="ได้คีย์จากโปรโมชันหรือจากการซื้อ กรอกที่นี่เพื่อเติมชั่วโมงเข้าบัญชีด้วยตัวเอง"
      />
      <div className="card card-pad row" style={{ gap: 14, marginBottom: 18, alignItems: 'center' }}>
        <span className="icon-chip text-gold" style={{ width: 38, height: 38 }}>
          <Clock size={18} />
        </span>
        <div>
          <div className="tiny faint">ชั่วโมงคงเหลือตอนนี้</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>{formatHHMM(user.hoursRemaining)} ชม.</div>
        </div>
      </div>
      <RedeemCard />
      <div className="card card-pad" style={{ marginTop: 18 }}>
        <div className="stat-label" style={{ marginBottom: 10 }}>
          <span className="icon-chip text-gold">
            <Gift size={16} />
          </span>
          วิธีใช้คีย์
        </div>
        <ul className="small muted" style={{ paddingLeft: 18, lineHeight: 1.8 }}>
          <li>คีย์มี 24 ตัวอักษร (6 กลุ่ม) พิมพ์หรือวางได้เลย ระบบใส่ขีดให้เอง</li>
          <li>ชั่วโมงบวกเพิ่มจากยอดเดิมทันที และใช้ได้ทั้งบนเว็บและในโปรแกรม AI Gold Commander Pro</li>
          <li>คีย์แต่ละรหัสใช้ได้ครั้งเดียว คีย์โปรโมชันบางรหัสมีวันหมดอายุ</li>
          <li>
            ยังไม่มีคีย์? <Link href="/store" className="text-sky">ซื้อชั่วโมง</Link> หรือดูคีย์ที่ซื้อไว้ที่{' '}
            <Link href="/my-keys" className="text-sky">คีย์ของฉัน</Link>
          </li>
        </ul>
        <Link href="/store" className="btn btn-secondary btn-sm" style={{ marginTop: 6 }}>
          <ShoppingBag size={15} /> ไปหน้าซื้อชั่วโมง
        </Link>
      </div>
    </div>
  );
}
