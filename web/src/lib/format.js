// ฟังก์ชันจัดรูปแบบตัวเลข/เวลา ที่ใช้ร่วมกันทุกหน้า

/** ชั่วโมงทศนิยม → "ชั่วโมง.นาที" (HH.MM) ตามมาตรฐานระบบ */
export function formatHHMM(hoursDecimal) {
  const totalMins = Math.max(0, Math.round((Number(hoursDecimal) || 0) * 60));
  const h = Math.floor(totalMins / 60);
  const m = totalMins % 60;
  return `${h}.${String(m).padStart(2, '0')}`;
}

export function formatUsd(value, { sign = false } = {}) {
  const n = Number(value) || 0;
  const abs = Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (!sign) return `${n < 0 ? '-' : ''}$${abs}`;
  return `${n > 0 ? '+' : n < 0 ? '-' : ''}$${abs}`;
}

export function formatThb(value) {
  return `฿${(Number(value) || 0).toLocaleString('th-TH', { maximumFractionDigits: 2 })}`;
}

export function formatPrice(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n) || n === 0) return '—';
  return n.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function parseDate(value) {
  if (!value) return null;
  const s = String(value).replace(' ', 'T');
  const d = new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(s) ? s : `${s}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** เวลาไทย (Asia/Bangkok) */
export function formatThaiDateTime(value) {
  const d = parseDate(value);
  if (!d) return '—';
  return d.toLocaleString('th-TH', {
    timeZone: 'Asia/Bangkok',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function timeAgo(value) {
  const d = parseDate(value);
  if (!d) return '—';
  const sec = Math.max(0, Math.round((Date.now() - d.getTime()) / 1000));
  if (sec < 60) return `${sec} วินาทีที่แล้ว`;
  if (sec < 3600) return `${Math.floor(sec / 60)} นาทีที่แล้ว`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} ชั่วโมงที่แล้ว`;
  return `${Math.floor(sec / 86400)} วันที่แล้ว`;
}

export function secondsSince(value) {
  const d = parseDate(value);
  return d ? (Date.now() - d.getTime()) / 1000 : Infinity;
}

export function formatKeyInput(value) {
  const clean = String(value || '').replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 24);
  return clean.match(/.{1,4}/g)?.join('-') || '';
}
