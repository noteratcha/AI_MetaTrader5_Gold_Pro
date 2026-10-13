'use client';

import { useCallback, useEffect, useState } from 'react';
import { BarChart3, Target, TrendingUp, Trophy } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { StatCard } from './ui';
import { formatUsd } from '../lib/format';
import { PLAN_NAMES, planDisplay, planNumber } from '../lib/plans';

/** ผลการเทรดของผู้ใช้รายแผน (/api/user/stats · ซิงค์จากโปรแกรมเมื่อออเดอร์ปิด) — แสดงในหน้าพอร์ตสด */
/** สถิติรายแผนของบัญชี MT5 เดียว (จากโปรแกรม: radar_signals[0].plan_stats · Deal จริง 365 วัน) → รูปแบบเดียวกับ /api/user/stats */
function fromAccount(list) {
  const by = {};
  for (const p of list || []) {
    const n = planNumber(p.name);
    const key = n ? PLAN_NAMES[n] : /manual/i.test(p.name) ? 'เข้าไม้เอง' : p.name;
    const a = (by[key] ||= { name: key, trades: 0, win: 0, loss: 0, profit: 0, gp: 0, gl: 0 });
    a.trades += p.trades;
    a.win += p.win;
    a.loss += p.loss;
    a.profit += p.profit;
    a.gp += p.gp || 0;
    a.gl += p.gl || 0;
  }
  const plans = [1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => by[PLAN_NAMES[n]] || { name: PLAN_NAMES[n], trades: 0, win: 0, loss: 0, profit: 0 });
  if (by['เข้าไม้เอง']) plans.push(by['เข้าไม้เอง']);
  const rows = plans.map((p) => ({ ...p, winRate: p.win + p.loss ? (p.win / (p.win + p.loss)) * 100 : 0, pf: p.gl > 0 ? p.gp / p.gl : p.gp || 0 }));
  const t = rows.reduce((a, p) => ({ trades: a.trades + p.trades, win: a.win + p.win, loss: a.loss + p.loss, profit: a.profit + p.profit }), { trades: 0, win: 0, loss: 0, profit: 0 });
  return { overall: { ...t, winRate: t.win + t.loss ? (t.win / (t.win + t.loss)) * 100 : 0 }, plans: rows };
}

export default function MyTradeStats({ bare = false, accountStats = null, accountLabel = null }) {
  const { apiFetch } = useAuth();
  const [stats, setStats] = useState(null);

  const loadStats = useCallback(async () => {
    try {
      setStats(await apiFetch('/api/user/stats'));
    } catch {
      setStats({ overall: { trades: 0, win: 0, loss: 0, profit: 0, winRate: 0 }, plans: [] });
    }
  }, [apiFetch]);

  useEffect(() => {
    loadStats();
    const id = setInterval(() => document.visibilityState === 'visible' && loadStats(), 60000);
    return () => clearInterval(id);
  }, [loadStats]);

  const view = accountStats ? fromAccount(accountStats) : stats;
  const o = view?.overall;
  return (
    <div className={bare ? '' : 'section'}>
      {!bare && (
        <div className="section-title">
          <div>
            <h2>ผลการเทรดของคุณ</h2>
            <p>ซิงค์จากโปรแกรม Gold Bot 24 เมื่อออเดอร์ปิด</p>
          </div>
        </div>
      )}
      <p className="tiny faint" style={{ margin: '0 0 10px' }}>
        {accountStats
          ? `บัญชี MT5 #${accountLabel} · คำนวณจาก Deal จริงในบัญชีนี้ย้อนหลัง 365 วัน (อัปเดตทุก 5 นาที)`
          : 'ทุกบัญชี MT5 รวมกัน · ซิงค์จากโปรแกรมเมื่อออเดอร์ปิด'}
      </p>
      <div className="grid grid-4">
        <StatCard icon={Target} label="ออเดอร์ทั้งหมด" value={o ? o.trades : '—'} loading={!view} />
        <StatCard icon={Trophy} label="Win Rate" value={o ? `${o.winRate.toFixed(1)}%` : '—'} tone="gold" sub={o ? `ชนะ ${o.win} · แพ้ ${o.loss}` : undefined} loading={!view} />
        <StatCard
          icon={TrendingUp}
          label="กำไรสุทธิ"
          value={o ? formatUsd(o.profit, { sign: true }) : '—'}
          tone={o && o.profit > 0 ? 'green' : o && o.profit < 0 ? 'red' : undefined}
          loading={!view}
        />
        <StatCard icon={BarChart3} label="แผนที่มีการเทรด" value={view ? view.plans.filter((p) => p.trades > 0).length : '—'} sub={`จาก ${view ? view.plans.length : 6} แผน`} loading={!view} />
      </div>

      <div className="card section">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>แผนเทรด</th>
                <th className="num">ออเดอร์</th>
                <th className="num">ชนะ</th>
                <th className="num">แพ้</th>
                <th style={{ minWidth: 160 }}>Win Rate</th>
                <th className="num">กำไรสุทธิ</th>
                <th className="num">Profit Factor</th>
              </tr>
            </thead>
            <tbody>
              {(view?.plans || []).map((p) => (
                <tr key={p.name}>
                  <td style={{ fontWeight: 600 }}>{planDisplay(p.name)}</td>
                  <td className="num">{p.trades}</td>
                  <td className="num text-green">{p.win}</td>
                  <td className="num text-red">{p.loss}</td>
                  <td>
                    <div className="row" style={{ gap: 10 }}>
                      <div className="progress" style={{ flex: 1, minWidth: 70 }}>
                        <span style={{ width: `${Math.min(100, p.winRate)}%`, background: 'var(--gold)' }} />
                      </div>
                      <span className="mono small" style={{ width: 48, textAlign: 'right' }}>
                        {p.winRate.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className={`num ${p.profit > 0 ? 'text-green' : p.profit < 0 ? 'text-red' : ''}`} style={{ fontWeight: 600 }}>
                    {formatUsd(p.profit, { sign: true })}
                  </td>
                  <td className="num">{p.pf.toFixed(2)}</td>
                </tr>
              ))}
              {!view &&
                [0, 1, 2].map((i) => (
                  <tr key={i}>
                    <td colSpan={7}>
                      <div className="skeleton" style={{ height: 16 }} />
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
