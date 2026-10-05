'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Lock, Receipt, ShoppingBag } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Alert, AuthGate, EmptyState, PageHeader, PageLoading } from '../../components/ui';
import { formatThaiDateTime, formatThb } from '../../lib/format';

export default function ReceiptsPage() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <PageLoading />;
  if (!user) return <AuthGate icon={Lock} title="เข้าสู่ระบบเพื่อดูใบเสร็จ" description="ใบเสร็จการซื้อชั่วโมงทั้งหมดของคุณเก็บไว้ที่นี่" />;
  return <ReceiptList />;
}

function ReceiptList() {
  const { apiFetch } = useAuth();
  const [receipts, setReceipts] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch('/api/user/receipts')
      .then((res) => setReceipts(res.receipts || []))
      .catch((err) => {
        setReceipts([]);
        setError(err.message);
      });
  }, [apiFetch]);

  return (
    <div className="container page">
      <PageHeader
        eyebrow="Receipts"
        icon={Receipt}
        title="ใบเสร็จของฉัน"
        description="ใบเสร็จรับเงินออกอัตโนมัติทุกครั้งที่ชำระเงินสำเร็จ และส่งสำเนาไปที่อีเมลของคุณ"
        actions={
          <Link href="/store" className="btn btn-primary btn-sm">
            <ShoppingBag size={15} /> ซื้อชั่วโมงเพิ่ม
          </Link>
        }
      />
      {error && (
        <div style={{ marginBottom: 16 }}>
          <Alert type="error">{error}</Alert>
        </div>
      )}
      {!receipts ? (
        <PageLoading />
      ) : receipts.length === 0 ? (
        <div className="card">
          <EmptyState icon={Receipt} title="ยังไม่มีใบเสร็จ">
            ใบเสร็จจะแสดงที่นี่หลังจากซื้อชั่วโมงสำเร็จ
          </EmptyState>
        </div>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>เลขที่ใบเสร็จ</th>
                  <th>วันที่</th>
                  <th>รายการ</th>
                  <th className="num">ยอดชำระ</th>
                  <th>อีเมล</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {receipts.map((r) => (
                  <tr key={r.receiptNo}>
                    <td className="mono small">{r.receiptNo}</td>
                    <td className="small">{formatThaiDateTime(r.issuedAt)}</td>
                    <td className="small">{r.itemName}</td>
                    <td className="num text-gold">{formatThb(r.amountThb)}</td>
                    <td>{r.emailedAt ? <span className="badge badge-green">ส่งแล้ว</span> : <span className="badge badge-gold">ยังไม่ส่ง</span>}</td>
                    <td style={{ textAlign: 'right' }}>
                      <Link href={`/receipts/${encodeURIComponent(r.receiptNo)}`} className="btn btn-secondary btn-sm">
                        ดูใบเสร็จ
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
