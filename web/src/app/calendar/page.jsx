'use client';

import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { CalendarDays } from 'lucide-react';
import { PageHeader } from '../../components/ui';
import { EconCalendarList, InvestingWidget, NextNewsCard, useCalendar } from '../../components/EconCalendar';

export default function CalendarPage() {
  const { events, error, updatedAt, reload } = useCalendar();
  const [tab, setTab] = useState('native');
  const { user, apiFetch } = useAuth();
  const [news, setNews] = useState(null);

  // ผลวิเคราะห์ข่าวต่อทองจากโปรแกรม AI Gold Commander Pro ของผู้ใช้ (ชุดเดียวกับในโปรแกรม)
  useEffect(() => {
    if (!user) return;
    apiFetch('/api/user/telemetry')
      .then((r) => setNews((r.telemetry?.radar_signals || [])[0]?.news || []))
      .catch(() => setNews([]));
  }, [user?.id, apiFetch]); // eslint-disable-line react-hooks/exhaustive-deps

  const impacts = useMemo(
    () => (news && news.length ? new Map(news.map((n) => [`${n.title}|${new Date(n.time).getTime()}`, n])) : null),
    [news]
  );

  return (
    <div className="container container-wide page">
      <PageHeader
        eyebrow="Economic Calendar"
        icon={CalendarDays}
        title="ปฏิทินเศรษฐกิจ"
        description="ข่าวเศรษฐกิจที่มีผลต่อราคาทองคำ — ข่าว USD ผลกระทบสูง (เช่น NFP, CPI, FOMC) มักทำให้ทองผันผวนแรง"
      />

      <div className="segmented" style={{ width: 'min(100%, 380px)', marginBottom: 16 }}>
        <button className={tab === 'native' ? 'is-active' : ''} onClick={() => setTab('native')}>
          ปฏิทินรายสัปดาห์
        </button>
        <button className={tab === 'investing' ? 'is-active' : ''} onClick={() => setTab('investing')}>
          Investing.com
        </button>
      </div>

      {tab === 'native' ? (
        <div className="grid grid-main-side" style={{ alignItems: 'start' }}>
          <div className="stack" style={{ gap: 8 }}>
            <EconCalendarList events={events} error={error} updatedAt={updatedAt} onReload={reload} impacts={impacts} />
            {user && !impacts && (
              <div className="tiny faint">คอลัมน์ “ผลต่อทอง” จะแสดงเมื่อโปรแกรม AI Gold Commander Pro เปิดอยู่และส่งข้อมูลขึ้นเว็บ</div>
            )}
            {!user && <div className="tiny faint">เข้าสู่ระบบเพื่อดูการวิเคราะห์ผลกระทบของข่าวต่อราคาทอง</div>}
          </div>
          <div className="stack" style={{ gap: 16 }}>
            <NextNewsCard events={events} />
            <div className="card card-pad small muted">
              <div style={{ fontWeight: 700, color: 'var(--text)', marginBottom: 8 }}>คำแนะนำ</div>
              ช่วง 15–30 นาทีก่อนและหลังข่าวผลกระทบสูง สเปรดทองคำมักกว้างและราคาสะบัดแรง ควรติดตามออเดอร์ที่เปิดอยู่อย่างใกล้ชิด
            </div>
          </div>
        </div>
      ) : (
        <InvestingWidget />
      )}
    </div>
  );
}
