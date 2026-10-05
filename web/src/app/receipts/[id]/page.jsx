'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, Lock, Mail, Printer, Receipt } from 'lucide-react';
import { useAuth } from '../../../context/AuthContext';
import { Alert, AuthGate, EmptyState, PageLoading, Spinner } from '../../../components/ui';
import { formatThb } from '../../../lib/format';

const fullDate = (v) =>
  v ? new Date(v).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', dateStyle: 'long', timeStyle: 'short' }) : '—';

export default function ReceiptPage() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <PageLoading />;
  if (!user) return <AuthGate icon={Lock} title="เข้าสู่ระบบเพื่อดูใบเสร็จ" description="ใบเสร็จดูได้เฉพาะเจ้าของบัญชีที่ซื้อ" />;
  return <ReceiptView />;
}

function ReceiptView() {
  const { apiFetch } = useAuth();
  const params = useParams();
  const id = decodeURIComponent(String(params?.id || ''));
  const [receipt, setReceipt] = useState(null);
  const [error, setError] = useState('');
  const [status, setStatus] = useState(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    apiFetch(`/api/user/receipts?id=${encodeURIComponent(id)}`)
      .then((res) => setReceipt(res.receipt))
      .catch((err) => setError(err.message));
  }, [apiFetch, id]);

  const resend = async () => {
    setSending(true);
    setStatus(null);
    try {
      const res = await apiFetch('/api/user/receipts', { method: 'POST', body: JSON.stringify({ id: receipt.receiptNo }) });
      setStatus({ type: 'success', message: res.message });
    } catch (err) {
      setStatus({ type: 'error', message: err.message });
    } finally {
      setSending(false);
    }
  };

  if (error) {
    return (
      <div className="container container-narrow page">
        <div className="card">
          <EmptyState icon={Receipt} title="ไม่พบใบเสร็จ">
            {error}
          </EmptyState>
        </div>
      </div>
    );
  }
  if (!receipt) return <PageLoading />;
  const s = receipt.seller || {};

  return (
    <div className="container container-narrow page">
      <div className="row-between wrap no-print" style={{ marginBottom: 16, gap: 8 }}>
        <Link href="/receipts" className="btn btn-ghost btn-sm">
          <ArrowLeft size={15} /> ใบเสร็จทั้งหมด
        </Link>
        <div className="row wrap" style={{ gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={resend} disabled={sending}>
            {sending ? <Spinner /> : <Mail size={15} />} ส่งอีเมลอีกครั้ง
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => window.print()}>
            <Printer size={15} /> พิมพ์ / บันทึก PDF
          </button>
        </div>
      </div>
      {status && (
        <div className="no-print" style={{ marginBottom: 16 }}>
          <Alert type={status.type}>{status.message}</Alert>
        </div>
      )}

      <article className="card receipt-paper">
        <header className="receipt-head">
          <div>
            <div className="receipt-seller">{s.name}</div>
            {s.address && <div className="small muted">{s.address}</div>}
            {s.taxId && <div className="small muted">เลขประจำตัวผู้เสียภาษี {s.taxId}</div>}
            {s.contact && <div className="small muted">{s.contact}</div>}
          </div>
          <div style={{ textAlign: 'right' }}>
            <div className="receipt-title">ใบเสร็จรับเงิน</div>
            <div className="small muted">Receipt</div>
          </div>
        </header>

        <dl className="receipt-meta">
          <div>
            <dt>เลขที่</dt>
            <dd className="mono">{receipt.receiptNo}</dd>
          </div>
          <div>
            <dt>วันที่</dt>
            <dd>{fullDate(receipt.issuedAt)}</dd>
          </div>
          <div>
            <dt>ผู้ซื้อ</dt>
            <dd>
              {receipt.customerName}
              <div className="small muted">{receipt.email}</div>
            </dd>
          </div>
          <div>
            <dt>เลขที่คำสั่งซื้อ</dt>
            <dd className="mono small">{receipt.orderId}</dd>
          </div>
        </dl>

        <table className="table receipt-items">
          <thead>
            <tr>
              <th>รายการ</th>
              <th className="num">จำนวน</th>
              <th className="num">จำนวนเงิน</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{receipt.itemName}</td>
              <td className="num">1</td>
              <td className="num">{formatThb(receipt.amountThb)}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={2} className="receipt-total-label">ยอดชำระทั้งสิ้น</td>
              <td className="num receipt-total">{formatThb(receipt.amountThb)}</td>
            </tr>
          </tfoot>
        </table>

        <dl className="receipt-meta receipt-pay">
          <div>
            <dt>ช่องทางชำระ</dt>
            <dd>{receipt.paymentMethod}</dd>
          </div>
          {receipt.paymentRef && (
            <div>
              <dt>อ้างอิงการชำระ</dt>
              <dd className="mono small">{receipt.paymentRef}</dd>
            </div>
          )}
          {receipt.productKey && (
            <div>
              <dt>Product Key</dt>
              <dd className="mono small">{receipt.productKey}</dd>
            </div>
          )}
          <div>
            <dt>สถานะ</dt>
            <dd>
              <span className="badge badge-green">ชำระเงินแล้ว</span>
            </dd>
          </div>
        </dl>

        <p className="tiny faint" style={{ marginTop: 18 }}>
          เอกสารนี้ออกโดยระบบอัตโนมัติ · {receipt.emailedAt ? `ส่งสำเนาทางอีเมลเมื่อ ${fullDate(receipt.emailedAt)}` : 'ยังไม่ได้ส่งสำเนาทางอีเมล'}
        </p>
      </article>
    </div>
  );
}
