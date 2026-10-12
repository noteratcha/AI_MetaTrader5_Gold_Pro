'use client';

import { Megaphone } from 'lucide-react';
import { EmptyState, PageHeader } from '../../components/ui';
import { NewsBody, formatNewsDate, useAnnouncements } from '../../components/Announcements';

export default function NewsPage() {
  const items = useAnnouncements();
  return (
    <div className="container page" style={{ maxWidth: 820 }}>
      <PageHeader eyebrow="News & Promotions" icon={Megaphone} title="ข่าวสารและโปรโมชัน" description="ข่าวจากทีม Gold Bot 24 แสดงตรงกันทั้งบนเว็บและในโปรแกรม" />
      {items.length === 0 ? (
        <div className="card">
          <EmptyState icon={Megaphone} title="ยังไม่มีข่าวสาร">ติดตามโปรโมชันและข่าวอัปเดตได้ที่นี่</EmptyState>
        </div>
      ) : (
        <div className="stack" style={{ gap: 16 }}>
          {items.map((a) => (
            <article key={a.id} className="card card-pad">
              <div className="row-between wrap" style={{ gap: 8, marginBottom: 10 }}>
                <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0 }}>{a.title}</h2>
                <span className="tiny faint">{formatNewsDate(a.startsAt)}</span>
              </div>
              <NewsBody item={a} />
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
