'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { PageLoading } from '../../components/ui';

// คีย์ของฉันย้ายไปอยู่ในหน้ากระเป๋าเวลา (12 ต.ค. 2026) — ลิงก์เดิมพาไปเปิดส่วนคีย์ให้อัตโนมัติ
export default function MyKeysRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/dashboard?keys=1');
  }, [router]);
  return <PageLoading />;
}
