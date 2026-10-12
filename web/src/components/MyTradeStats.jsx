'use client';

import { useCallback, useEffect, useState } from 'react';
import { BarChart3, Target, TrendingUp, Trophy } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { StatCard } from './ui';
import { formatUsd } from '../lib/format';
import { planDisplay } from '../lib/plans';

/** ผลการเทรดของผู้ใช้รายแผน (/api/user/stats · ซิงค์จากโปรแกรมเมื่อออเดอร์ปิด) — แสดงในหน้าพอร์ตสด */
export default function MyTradeStats() {
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

  const o = stats?.overall;
  return (
    <div className="section">
      <div className="section-title">
        <div>
          <h2>ผลการเทรดของคุณ</h2>
          <p>ซิงค์จากโปรแกรม Gold Bot 24 เมื่อออเดอร์ปิด</p>
        </div>
      </div>
      <div className="grid grid-4">
        <StatCard icon={Target} label="ออเดอร์ทั้งหมด" value={o ? o.trades : '—'} loading={!stats} />
        <StatCard icon={Trophy} label="Win Rate" value={o ? `${o.winRate.toFixed(1)}%` : '—'} tone="gold" sub={o ? `ชนะ ${o.win} · แพ้ ${o.loss}` : undefined} loading={!stats} />
        <StatCard
          icon={TrendingUp}
          label="กำไรสุทธิ"
          value={o ? formatUsd(o.profit, { sign: true }) : '—'}
          tone={o && o.profit > 0 ? 'green' : o && o.profit < 0 ? 'red' : undefined}
          loading={!stats}
        />
        <StatCard icon={BarChart3} label="แผนที่มีการเทรด" value={stats ? stats.plans.filter((p) => p.trades > 0).length : '—'} sub={`จาก ${stats ? stats.plans.length : 6} แผน`} loading={!stats} />
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
              {(stats?.plans || []).map((p) => (
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
              {!stats &&
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
