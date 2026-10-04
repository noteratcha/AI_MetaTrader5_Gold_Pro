import { redirect } from 'next/navigation';

// หน้าเดิม — ย้ายไปที่ /admin
export default function LegacyAdminAnalytics() {
  redirect('/admin');
}
