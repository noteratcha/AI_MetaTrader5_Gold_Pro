'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { AlertTriangle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { formatHHMM } from '../lib/format';
import { LOW_HOURS } from '../lib/hours';

/** แถบเตือนใต้เมนูเมื่อชั่วโมงเหลือไม่เกิน 5 ชม. หรือหมดแล้ว (ชั่วโมงดึงใหม่ทุก 60 วินาทีจาก AuthContext) */
export default function LowHoursBanner() {
  const { user } = useAuth();
  const pathname = usePathname();
  if (!user) return null;
  const hours = Number(user.hoursRemaining) || 0;
  if (hours > LOW_HOURS) return null;
  const out = hours <= 0;
  return (
    <div className={`low-hours-banner ${out ? 'is-out' : ''}`} role="status">
      <div className="container low-hours-inner">
        <span className="row" style={{ gap: 8 }}>
          <AlertTriangle size={16} />
          {out ? (
            <span>
              <strong>ชั่วโมงใช้งานหมดแล้ว</strong> บอทหยุดทำงาน เติมชั่วโมงเพื่อเทรดต่อ
            </span>
          ) : (
            <span>
              <strong>เวลาใช้งานใกล้หมด</strong> เหลือ {formatHHMM(hours)} ชม. เมื่อหมดบอทจะหยุดเอง
            </span>
          )}
        </span>
        <span className="row" style={{ gap: 8 }}>
          {pathname !== '/store' && (
            <Link href="/store" className="btn btn-primary btn-sm">ซื้อชั่วโมง</Link>
          )}
          {pathname !== '/redeem' && (
            <Link href="/redeem" className="btn btn-secondary btn-sm">เติมคีย์</Link>
          )}
        </span>
      </div>
    </div>
  );
}
