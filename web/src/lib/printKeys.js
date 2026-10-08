// พิมพ์ / บันทึกเป็น PDF ของ Product Key (หน้าละ 1 ใบ) พร้อมลายน้ำโลโก้ GoldBot24
// ใช้หน้าต่างพิมพ์ของเบราว์เซอร์ → เลือก "Save as PDF" เพื่อได้ไฟล์ PDF (รองรับภาษาไทยเต็มรูปแบบ)

const esc = (v) =>
  String(v ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

const thDate = (iso) =>
  iso
    ? new Date(iso).toLocaleString('th-TH', { timeZone: 'Asia/Bangkok', dateStyle: 'long', timeStyle: 'short' }) + ' น.'
    : '';

export function buildKeysHtml(list, origin) {
  const logo = `${origin}/app_icon.png`;
  const cards = list
    .map((k, i) => {
      const hours = Number(k.hours || 0).toLocaleString('en-US');
      const type = k.source === 'promo' ? 'Promo Key' : 'Product Key';
      return `
      <section class="sheet">
        <div class="wm-logo"><img src="${logo}" alt="" /></div>
        <div class="wm-text">GoldBot24</div>
        <div class="card">
          <header>
            <img class="logo" src="${logo}" alt="GoldBot24" />
            <div>
              <div class="brand">GoldBot24</div>
              <div class="sub">AI Gold Commander Pro · คีย์เติมชั่วโมงใช้งาน</div>
            </div>
            <div class="no">#${i + 1}</div>
          </header>
          <div class="type">${esc(type)}</div>
          <div class="key">${esc(k.keyCode)}</div>
          <div class="hours"><span>${esc(hours)}</span> ชั่วโมง</div>
          <table>
            <tr><th>วันที่สร้าง</th><td>${esc(thDate(k.createdAt) || '—')}</td></tr>
            <tr><th>วันหมดอายุ</th><td>${esc(k.expiresAt ? thDate(k.expiresAt) : 'ไม่มีวันหมดอายุ')}</td></tr>
            <tr><th>จำนวนชั่วโมง</th><td>${esc(hours)} ชั่วโมง</td></tr>
          </table>
          <div class="how">
            <b>วิธีใช้:</b> เข้าสู่ระบบที่ <b>goldbot24.vercel.app</b> → เมนู “คีย์ของฉัน” → กรอกคีย์ด้านบน
            ชั่วโมงจะถูกเติมเข้าบัญชีทันที (คีย์ใช้ได้ครั้งเดียว)
          </div>
          <footer>เก็บคีย์นี้เป็นความลับ · ออกโดย GoldBot24 · พิมพ์เมื่อ ${esc(thDate(new Date().toISOString()))}</footer>
        </div>
      </section>`;
    })
    .join('');

  const html = `<!doctype html><html lang="th"><head><meta charset="utf-8" />
<title>GoldBot24 Keys (${list.length})</title>
<link href="https://fonts.googleapis.com/css2?family=Anuphan:wght@400;600;700&family=JetBrains+Mono:wght@700&display=swap" rel="stylesheet" />
<style>
  @page { size: A5 landscape; margin: 0; }
  * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { margin: 0; font-family: 'Anuphan', Tahoma, sans-serif; color: #1a1406; background: #eee; }
  .sheet { position: relative; width: 210mm; height: 148mm; margin: 0 auto 8mm; background: #fffdf6; overflow: hidden;
           page-break-after: always; display: flex; align-items: center; justify-content: center; }
  .sheet:last-child { page-break-after: auto; }
  .wm-logo { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; opacity: .09; }
  /* โลโก้มีพื้นดำ → invert ให้พื้นเป็นขาว (กลืนกับกระดาษ) เหลือแต่รูปมงกุฎจาง ๆ */
  .wm-logo img { width: 105mm; height: 105mm; object-fit: contain; filter: grayscale(1) invert(1) contrast(1.4); }
  .wm-text { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; transform: rotate(-24deg);
             font-size: 64pt; font-weight: 700; color: #b8860b; opacity: .10; letter-spacing: 6px; }
  .card { position: relative; width: 186mm; border: 1.5px solid #c9a227; border-radius: 6mm; padding: 9mm 11mm; background: rgba(255,255,255,.55); }
  header { display: flex; align-items: center; gap: 4mm; border-bottom: 1px solid #e3cf8a; padding-bottom: 4mm; }
  .logo { width: 15mm; height: 15mm; object-fit: contain; }
  .brand { font-size: 20pt; font-weight: 700; color: #9a6b12; line-height: 1; }
  .sub { font-size: 10pt; color: #6b5a2e; }
  .no { margin-left: auto; font-size: 10pt; color: #9a8a5e; }
  .type { margin-top: 5mm; font-size: 10pt; letter-spacing: 2px; text-transform: uppercase; color: #9a6b12; font-weight: 700; }
  .key { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 21pt; font-weight: 700; letter-spacing: 1.5px;
         margin: 2mm 0 1mm; padding: 4mm 5mm; border: 1.5px dashed #c9a227; border-radius: 3mm; text-align: center; background: #fff8e1; }
  .hours { text-align: center; font-size: 13pt; color: #6b5a2e; margin-bottom: 3mm; }
  .hours span { font-size: 22pt; font-weight: 700; color: #1a1406; }
  table { width: 100%; border-collapse: collapse; font-size: 11pt; }
  th { text-align: left; width: 34mm; color: #6b5a2e; font-weight: 600; padding: 1.2mm 0; }
  td { padding: 1.2mm 0; font-weight: 600; }
  .how { margin-top: 3mm; font-size: 9.5pt; color: #4a3f22; background: #fbf3d6; border-radius: 2mm; padding: 2.5mm 3.5mm; }
  footer { margin-top: 3mm; font-size: 8.5pt; color: #9a8a5e; text-align: center; }
  @media print { body { background: #fff; } .sheet { margin: 0; } }
</style></head><body>${cards}
<script>
  window.addEventListener('load', function () {
    var imgs = Array.prototype.slice.call(document.images);
    Promise.all(imgs.map(function (im) { return im.complete ? 0 : new Promise(function (r) { im.onload = im.onerror = r; }); }))
      .then(function () { return document.fonts ? document.fonts.ready : 0; })
      .then(function () { setTimeout(function () { window.print(); }, 250); });
  });
</script></body></html>`;
  return html;
}

export function printKeys(keys) {
  const list = (keys || []).filter(Boolean);
  if (!list.length) return false;
  const html = buildKeysHtml(list, window.location.origin);
  const w = window.open('', '_blank');
  if (!w) return false;
  w.document.open();
  w.document.write(html);
  w.document.close();
  return true;
}
