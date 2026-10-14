'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '../context/AuthContext';
import { formatCountdown, useCalendar } from './EconCalendar';
import { formatHHMM } from '../lib/format';
import { LOW_HOURS } from '../lib/hours';
import { MEMBER_WARN_DAYS } from '../lib/membership';

// ข้อความวิ่งใต้เมนู (ทุกหน้า): ข่าว USD ผลกระทบสูงถัดไป · ชั่วโมงใกล้หมด · โปรแกรมยังไม่ใช่เวอร์ชันล่าสุด
// ชี้เมาส์เพื่อหยุด · คลิกข้อความเพื่อไปหน้าที่เกี่ยวข้อง
const nums = (v) => String(v || '').split('.').map((x) => Number(x) || 0);
const older = (a, b) => {
  const x = nums(a);
  const y = nums(b);
  for (let i = 0; i < Math.max(x.length, y.length); i++) if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) < (y[i] || 0);
  return false;
};
const verOf = (status) => /v(\d{4}\.\d{4}\.\d{4})/.exec(String(status || ''))?.[1] || null;
const fmtThai = (d) =>
  d.toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

export default function TopTicker() {
  const { user, apiFetch } = useAuth();
  const pathname = usePathname();
  const calendar = useCalendar();
  const [now, setNow] = useState(Date.now());
  const [latest, setLatest] = useState(null);
  const [mine, setMine] = useState([]); // [{ login, version }]

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    fetch('/api/release')
      .then((r) => r.json())
      .then((d) => setLatest(d.release?.version || null))
      .catch(() => {});
  }, []);

  // เวอร์ชันโปรแกรมที่ผู้ใช้รันอยู่ (จาก Telemetry ล่าสุด 24 ชม.) — ตรวจทุก 5 นาที
  useEffect(() => {
    if (!user) {
      setMine([]);
      return undefined;
    }
    const load = () =>
      apiFetch('/api/user/telemetry')
        .then((d) => {
          const list = (d.accounts || []).map((a) => ({ login: a.login, version: verOf(a.status) })).filter((a) => a.version);
          if (!list.length && d.telemetry) {
            const v = verOf(d.telemetry.status);
            if (v) list.push({ login: null, version: v });
          }
          setMine(list);
        })
        .catch(() => {});
    load();
    const id = setInterval(load, 5 * 60000);
    return () => clearInterval(id);
  }, [user, apiFetch]);

  const items = useMemo(() => {
    const out = [];
    if (user) {
      const hrs = Number(user.hoursRemaining) || 0;
      if (hrs <= 0) out.push({ key: 'hrs', tone: 'red', href: '/store', text: `ชั่วโมงใช้งานหมดแล้ว — บอทหยุดทำงาน · เติมชั่วโมงเพื่อใช้งานต่อ` });
      else if (hrs <= LOW_HOURS) out.push({ key: 'hrs', tone: 'gold', href: '/store', text: `ชั่วโมงใช้งานเหลือ ${formatHHMM(hrs)} ชม. — เติมชั่วโมงก่อนบอทหยุด` });
      // สมาชิกรายเดือนใกล้หมดอายุ (≤ 3 วัน) — หมดแล้วบอทเข้าไม้ด้วย P6–P11 ไม่ได้
      const mem = user.membership;
      if (mem?.active && !mem.viaAdmin && mem.daysLeft <= MEMBER_WARN_DAYS) {
        out.push({ key: 'member', tone: 'gold', href: '/store?member=1', text: `สมาชิกรายเดือนหมดอายุในอีก ${mem.daysLeft} วัน — ต่ออายุเพื่อใช้แผน P6–P11 ต่อ` });
      }
      if (latest) {
        for (const m of mine.filter((x) => older(x.version, latest))) {
          out.push({
            key: `ver-${m.login || 'x'}`,
            tone: 'red',
            href: '/download',
            text: `โปรแกรม${m.login ? `ของบัญชี #${m.login}` : 'ของคุณ'} ยังเป็น v${m.version} — อัปเดตเป็น v${latest} (เมนูผู้ใช้ → ตรวจสอบเวอร์ชันใหม่ หรือดาวน์โหลด)`,
          });
        }
      }
    }
    const news = (calendar.events || []).filter((e) => e.currency === 'USD' && e.impact === 'High' && e.at.getTime() > now - 5 * 60000).slice(0, 3);
    for (const e of news) {
      out.push({ key: `news-${e.title}-${e.date}`, tone: 'news', href: '/calendar', text: `ข่าวสำคัญ USD · ${fmtThai(e.at)} น. · ${e.title} · ${formatCountdown(e.at.getTime(), now)}` });
    }
    return out;
  }, [user, latest, mine, calendar.events, now]);

  // ไม่แสดงในหน้าแอดมิน และหน้าใบเสร็จ (ใบเสร็จต้องสะอาด ไม่มีข้อความวิ่ง)
  if (!items.length || pathname?.startsWith('/admin') || pathname?.startsWith('/receipts')) return null;
  const COLORS = { red: '#f87171', gold: '#f2c14e', news: '#e5e7eb' };
  const DOT = { red: '#f87171', gold: '#f2c14e', news: '#60a5fa' };
  const row = items.map((it) => (
    <Link key={it.key} href={it.href} className="ticker-item" style={{ color: COLORS[it.tone] }}>
      <span className="ticker-dot" style={{ background: DOT[it.tone] }} />
      {it.text}
    </Link>
  ));
  // ความเร็วคงที่ตามความยาวข้อความ
  const secs = Math.max(25, items.reduce((a, it) => a + it.text.length, 0) * 0.22);
  return (
    <div className="ticker" role="marquee" aria-label="ข่าวและการแจ้งเตือน">
      <div className="ticker-track" style={{ animationDuration: `${secs}s` }}>
        <div className="ticker-group">{row}</div>
        <div className="ticker-group" aria-hidden="true">
          {row}
        </div>
      </div>
    </div>
  );
}
