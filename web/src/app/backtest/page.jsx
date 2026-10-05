'use client';

import { useEffect, useMemo, useState } from 'react';
import { FlaskConical, LineChart, ShieldAlert, Target, TrendingDown, TrendingUp } from 'lucide-react';
import { Alert, EmptyState, PageHeader, PageLoading, StatCard } from '../../components/ui';

const PLAN_COLORS = { 1: '#f2c14e', 2: '#60a5fa', 3: '#34d399', 4: '#f472b6', 5: '#a78bfa' };

// หลักการของแต่ละแผน (ตรงกับกฎในโปรแกรมเวอร์ชันล่าสุด)
const PLAN_INFO = {
  1: {
    type: 'ตามเทรนด์ · M15',
    rules: [
      'เทรนด์ H1: MA100 < MA150 < MA200 = ขาลง (SELL) · MA100 > MA150 > MA200 = ขาขึ้น (BUY)',
      'จุดเข้า: MA5 ตัด MA13 บนแท่ง M15 ที่ปิดแล้ว ตามทิศเทรนด์',
      'SL 0.75 ATR · เลื่อน SL ทุกกำไร $5 ครั้งละ 40% · ปิดเมื่อ MA5 ตัด MA13 กลับ (ไม่ตั้ง TP)',
    ],
  },
  2: {
    type: 'ตามเทรนด์ · H1',
    rules: [
      'เทรนด์ H4: MA10/MA30 + ความชัน MA5 + ราคาอยู่ฝั่งเดียวกับ MA200',
      'จุดเข้า: MA5 ตัด MA10 บนแท่ง H1 ที่ปิดแล้ว ตามทิศเทรนด์',
      'SL 0.75 ATR (H1) · ปิดเมื่อ MA5 ตัด MA10 กลับ (ไม่ตั้ง TP · ปล่อยกำไรวิ่ง)',
    ],
  },
  3: {
    type: 'กวาดสภาพคล่อง · M15',
    rules: [
      'ราคาทะลุแนวรับ/ต้าน H1 (โซนกลับตัว 500 แท่ง) แล้วดึงกลับ พร้อมไส้เทียนยาว ≥ 0.3 ATR',
      'ต้องตามเทรนด์ H1 และ AI ยืนยันทิศ ≥ 50% (มี Divergence ≥ 48%)',
      'SL 0.75 ATR · TP 1.125 ATR (RRR 1:1.5) · ล็อกกำไรที่ 70% ของเป้า',
    ],
  },
  4: {
    type: 'เด้งแนวรับ/ต้าน · M15',
    rules: [
      'ราคาเข้าใกล้แนวรับ/ต้าน H1 (500 แท่ง) ไม่เกิน 1 ATR + แท่งปฏิเสธราคา',
      'ต้องมี RSI Divergence และ AI ยืนยันทิศ ≥ 51%',
      'SL 0.75 ATR · TP 1.125 ATR (RRR 1:1.5) · ล็อกกำไรที่ 70% ของเป้า',
    ],
  },
  5: {
    type: 'กลับตัวขอบ Bollinger · H1',
    rules: [
      'ราคาหลุดขอบ Bollinger Bands H1 (20, 2 SD) แล้วปิดกลับเข้ากรอบ + ไส้เทียน ≥ 0.2 ATR',
      'ต้องมี RSI Divergence + MACD H1 เริ่มหมดแรง และ AI ยืนยันทิศ ≥ 50%',
      'SL 0.75 ATR · TP 1.125 ATR (RRR 1:1.5)',
    ],
  },
};
const pts = (v) => (v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${Number(v).toLocaleString('th-TH', { maximumFractionDigits: 1 })}`);
const tone = (v) => (v > 0 ? 'text-green' : v < 0 ? 'text-red' : 'muted');

/** กราฟกำไรสะสม (SVG) — รวมทุกแผน + แยกรายแผน */
function EquityChart({ equity, plans, visible }) {
  const W = 900;
  const H = 260;
  const P = 36;
  const series = useMemo(() => {
    const lines = [{ key: 'total', color: '#eceef3', width: 2.4, values: equity.map((e) => e.total) }];
    for (const p of plans) {
      if (visible[p.key]) lines.push({ key: p.key, color: PLAN_COLORS[p.key], width: 1.4, values: equity.map((e) => e.plans?.[String(p.key)] ?? 0) });
    }
    return lines;
  }, [equity, plans, visible]);
  if (!equity.length) return null;
  const all = series.flatMap((s) => s.values);
  const min = Math.min(0, ...all);
  const max = Math.max(0, ...all);
  const span = max - min || 1;
  const x = (i) => P + (i / Math.max(1, equity.length - 1)) * (W - P * 2);
  const y = (v) => H - P - ((v - min) / span) * (H - P * 2);
  const path = (vals) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const ticks = [min, (min + max) / 2, max];
  const dates = [0, Math.floor(equity.length / 2), equity.length - 1];
  return (
    <div className="table-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', minWidth: 520, height: 'auto' }} role="img" aria-label="กราฟกำไรสะสม">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={P} x2={W - P} y1={y(t)} y2={y(t)} stroke="#262b36" strokeDasharray="4 4" />
            <text x={4} y={y(t) + 4} fill="#6b7385" fontSize="11">
              {Math.round(t)}
            </text>
          </g>
        ))}
        <line x1={P} x2={W - P} y1={y(0)} y2={y(0)} stroke="#3a4150" />
        {series.map((s) => (
          <path key={s.key} d={path(s.values)} fill="none" stroke={s.color} strokeWidth={s.width} strokeLinejoin="round" />
        ))}
        {dates.map((i) => (
          <text key={i} x={x(i)} y={H - 10} fill="#6b7385" fontSize="11" textAnchor={i === 0 ? 'start' : i === equity.length - 1 ? 'end' : 'middle'}>
            {equity[i]?.date}
          </text>
        ))}
      </svg>
    </div>
  );
}

export default function BacktestPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [visible, setVisible] = useState({ 1: true, 2: true, 3: false, 4: false, 5: false });

  useEffect(() => {
    fetch('/backtest.json', { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('ยังไม่มีผล Backtest'))))
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  const months = useMemo(() => {
    if (!data) return [];
    const set = new Set();
    data.plans.forEach((p) => Object.keys(p.monthly || {}).forEach((m) => set.add(m)));
    return [...set].sort().slice(-12);
  }, [data]);

  if (error) {
    return (
      <div className="container page">
        <div className="card">
          <EmptyState icon={FlaskConical} title="ยังไม่มีผล Backtest">
            {error}
          </EmptyState>
        </div>
      </div>
    );
  }
  if (!data) return <PageLoading />;
  const s = data.summary;

  return (
    <div className="container container-wide page">
      <PageHeader
        eyebrow="Trading Plans"
        icon={FlaskConical}
        title="แผนเทรดทองคำ (XAUUSD)"
        description={`หลักการเข้า-ออกของบอททั้ง 5 แผน พร้อมผลทดสอบย้อนหลัง ${data.period[0]} ถึง ${data.period[1]} (กฎเวอร์ชัน v${data.app_version})`}
      />

      <div className="grid grid-3" style={{ marginBottom: 24 }}>
        {data.plans.map((p) => {
          const info = PLAN_INFO[p.key] || { type: '', rules: [p.rule] };
          return (
            <div key={p.key} className="card card-pad" style={{ borderTop: `3px solid ${PLAN_COLORS[p.key]}` }}>
              <div className="row-between" style={{ marginBottom: 8, gap: 8 }}>
                <strong>
                  {p.label} · {p.name}
                </strong>
                <span className="badge badge-muted">{info.type}</span>
              </div>
              <ul className="small muted" style={{ margin: '0 0 12px 18px', padding: 0 }}>
                {info.rules.map((r) => (
                  <li key={r} style={{ marginBottom: 4 }}>
                    {r}
                  </li>
                ))}
              </ul>
              <div className="row wrap small" style={{ gap: 12 }}>
                <span>
                  ย้อนหลัง <strong className={tone(p.net)}>{pts(p.net)} จุด</strong>
                </span>
                <span className="muted">PF {p.pf ?? '—'}</span>
                <span className="muted">ชนะ {p.n ? `${p.win}%` : '—'}</span>
                <span className="muted">{p.n ?? 0} ไม้</span>
              </div>
            </div>
          );
        })}
      </div>

      <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '8px 0 12px' }}>ผลทดสอบย้อนหลังรวมทุกแผน</h2>

      <div className="grid grid-4">
        <StatCard icon={TrendingUp} label="กำไรสุทธิรวม (0.01 lot)" value={`${pts(s.net)} จุด`} tone={s.net >= 0 ? 'green' : 'red'} sub={`≈ $${Math.round(s.net).toLocaleString()}`} />
        <StatCard icon={Target} label="จำนวนไม้ / ชนะ" value={s.trades.toLocaleString()} tone="gold" sub={`อัตราชนะ ${s.win}%`} />
        <StatCard icon={LineChart} label="Profit Factor" value={s.pf ?? '—'} tone="sky" sub="กำไรรวม ÷ ขาดทุนรวม" />
        <StatCard icon={TrendingDown} label="Max Drawdown" value={`${pts(-s.maxdd)} จุด`} tone="red" sub="ช่วงที่พอร์ตลดลงหนักสุด" />
      </div>

      <div className="card section">
        <div className="card-header">
          <h3>
            <LineChart size={17} className="text-gold" /> กำไรสะสม (จุด)
          </h3>
          <div className="row wrap" style={{ gap: 6 }}>
            {data.plans.map((p) => (
              <button
                key={p.key}
                type="button"
                className={`btn btn-sm ${visible[p.key] ? 'btn-secondary' : 'btn-ghost'}`}
                onClick={() => setVisible((v) => ({ ...v, [p.key]: !v[p.key] }))}
                style={{ borderColor: visible[p.key] ? PLAN_COLORS[p.key] : undefined }}
              >
                <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 3, background: PLAN_COLORS[p.key] }} /> {p.label}
              </button>
            ))}
          </div>
        </div>
        <div className="card-body">
          <EquityChart equity={data.equity} plans={data.plans} visible={visible} />
          <p className="tiny faint" style={{ marginTop: 6 }}>เส้นขาว = รวมทุกแผน · กดปุ่มด้านบนเพื่อแสดง/ซ่อนเส้นของแต่ละแผน</p>
        </div>
      </div>

      <div className="card section">
        <div className="card-header">
          <h3>ผลแยกตามแผน</h3>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>แผน</th>
                <th className="num">ไม้</th>
                <th className="num">ชนะ</th>
                <th className="num">กำไรสุทธิ</th>
                <th className="num">PF</th>
                <th className="num">Max DD</th>
                <th className="num">ครึ่งแรก</th>
                <th className="num">ครึ่งหลัง</th>
                <th className="num">100 ไม้ล่าสุด</th>
              </tr>
            </thead>
            <tbody>
              {data.plans.map((p) => (
                <tr key={p.key}>
                  <td>
                    <div className="row" style={{ gap: 8 }}>
                      <span style={{ width: 10, height: 10, borderRadius: 3, background: PLAN_COLORS[p.key], flexShrink: 0 }} />
                      <div>
                        <strong>
                          {p.label} · {p.name}
                        </strong>
                        <div className="tiny faint">{p.rule}</div>
                      </div>
                    </div>
                  </td>
                  <td className="num">{p.n ?? 0}</td>
                  <td className="num">{p.n ? `${p.win}%` : '—'}</td>
                  <td className={`num ${tone(p.net)}`}>
                    <strong>{pts(p.net)}</strong>
                  </td>
                  <td className="num">{p.pf ?? '—'}</td>
                  <td className="num text-red">{p.maxdd ? pts(-p.maxdd) : '—'}</td>
                  <td className={`num ${tone(p.half1)}`}>{pts(p.half1)}</td>
                  <td className={`num ${tone(p.half2)}`}>{pts(p.half2)}</td>
                  <td className={`num ${tone(p.last100_net)}`}>
                    {pts(p.last100_net)}
                    {p.last100_win !== undefined && p.n ? <div className="tiny faint">ชนะ {p.last100_win}%</div> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card section">
        <div className="card-header">
          <h3>กำไรรายเดือน (12 เดือนล่าสุด · จุด)</h3>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>แผน</th>
                {months.map((m) => (
                  <th key={m} className="num">
                    {m.slice(2)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.plans.map((p) => (
                <tr key={p.key}>
                  <td>{p.label}</td>
                  {months.map((m) => {
                    const v = p.monthly?.[m];
                    return (
                      <td key={m} className={`num tiny ${tone(v || 0)}`}>
                        {v === undefined ? '·' : pts(v)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section">
        <Alert type="gold">
          <strong>
            <ShieldAlert size={14} style={{ verticalAlign: '-2px' }} /> เงื่อนไขการทดสอบ
          </strong>
          <ul style={{ margin: '6px 0 0 18px', padding: 0 }}>
            {data.assumptions.map((a) => (
              <li key={a} className="small">
                {a}
              </li>
            ))}
          </ul>
        </Alert>
      </div>
    </div>
  );
}
