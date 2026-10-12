'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Megaphone } from 'lucide-react';
import { Modal } from './ui';

// ข่าวสาร/โปรโมชัน (/api/announcements) — ป๊อปอัปข่าวใหม่ที่ยังไม่เคยเห็น + ปุ่มกระดิ่งบนเมนู · จำข่าวที่เห็นแล้วในเบราว์เซอร์
const SEEN_KEY = 'gb24_seen_news';

const readSeen = () => {
  try {
    return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || '[]'));
  } catch {
    return new Set();
  }
};
const writeSeen = (set) => {
  try {
    localStorage.setItem(SEEN_KEY, JSON.stringify([...set].slice(-200)));
  } catch {}
};

let cache = null;
export function useAnnouncements() {
  const [items, setItems] = useState(cache || []);
  useEffect(() => {
    if (cache) return;
    fetch('/api/announcements')
      .then((r) => r.json())
      .then((d) => {
        cache = d.items || [];
        setItems(cache);
      })
      .catch(() => {});
  }, []);
  return items;
}

export function formatNewsDate(iso) {
  return iso ? new Date(iso).toLocaleDateString('th-TH', { timeZone: 'Asia/Bangkok', day: 'numeric', month: 'short', year: 'numeric' }) : '';
}

/** เนื้อหาข่าว 1 ชิ้น (ใช้ทั้งป๊อปอัปและหน้า /news) */
export function NewsBody({ item, onNavigate }) {
  const external = item.linkUrl && /^https?:/i.test(item.linkUrl);
  return (
    <div className="stack" style={{ gap: 12 }}>
      {item.imageUrl && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={item.imageUrl} alt={item.title} style={{ width: '100%', borderRadius: 12, display: 'block', border: '1px solid var(--border, #262B36)' }} />
      )}
      {item.body && <p style={{ whiteSpace: 'pre-line', margin: 0, lineHeight: 1.65 }}>{item.body}</p>}
      {item.linkUrl &&
        (external ? (
          <a href={item.linkUrl} target="_blank" rel="noopener noreferrer" className="btn btn-primary" onClick={onNavigate}>
            {item.linkLabel || 'ดูรายละเอียด'}
          </a>
        ) : (
          <Link href={item.linkUrl} className="btn btn-primary" onClick={onNavigate}>
            {item.linkLabel || 'ดูรายละเอียด'}
          </Link>
        ))}
    </div>
  );
}

/** ป๊อปอัปข่าวใหม่ (popup = true) ที่ยังไม่เคยเห็น — ทีละข่าว ใหม่สุดก่อน */
export function AnnouncementPopup() {
  const items = useAnnouncements();
  const pathname = usePathname();
  const [current, setCurrent] = useState(null);
  useEffect(() => {
    if (!items.length || pathname?.startsWith('/admin')) return;
    const seen = readSeen();
    setCurrent(items.find((a) => a.popup && !seen.has(a.id)) || null);
  }, [items, pathname]);
  if (!current) return null;
  const close = () => {
    const seen = readSeen();
    seen.add(current.id);
    writeSeen(seen);
    setCurrent(null);
  };
  return (
    <Modal title={current.title} onClose={close} width={560} footer={<button className="btn btn-secondary" onClick={close}>ปิด</button>}>
      <NewsBody item={current} onNavigate={close} />
    </Modal>
  );
}

/** ปุ่มข่าวสารบนเมนู + จุดแจ้งเตือนเมื่อมีข่าวที่ยังไม่ได้อ่าน */
export function NewsBell() {
  const items = useAnnouncements();
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    const seen = readSeen();
    if (pathname === '/news') {
      items.forEach((a) => seen.add(a.id));
      writeSeen(seen);
    }
    setUnread(items.filter((a) => !seen.has(a.id)).length);
  }, [items, pathname]);
  return (
    <Link href="/news" className="btn btn-ghost btn-icon news-bell" title="ข่าวสารและโปรโมชัน" aria-label="ข่าวสารและโปรโมชัน" style={{ position: 'relative' }}>
      <Megaphone size={17} />
      {unread > 0 && (
        <span
          style={{ position: 'absolute', top: 2, right: 2, minWidth: 16, height: 16, borderRadius: 8, background: 'var(--red, #f87171)', color: '#fff', fontSize: 10, fontWeight: 700, lineHeight: '16px', textAlign: 'center', padding: '0 4px' }}
        >
          {unread}
        </span>
      )}
    </Link>
  );
}
