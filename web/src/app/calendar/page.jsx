'use client';

import { useState } from 'react';
import { CalendarDays } from 'lucide-react';
import { PageHeader } from '../../components/ui';
import { EconCalendarList, InvestingWidget, NextNewsCard, useCalendar } from '../../components/EconCalendar';

export default function CalendarPage() {
  const { events, error, updatedAt, reload } = useCalendar();
  const [tab, setTab] = useState('native');

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
          <EconCalendarList events={events} error={error} updatedAt={updatedAt} onReload={reload} />
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
