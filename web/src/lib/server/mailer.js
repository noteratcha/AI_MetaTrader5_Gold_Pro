import nodemailer from 'nodemailer';

// ส่งอีเมลผ่าน SMTP (เช่น Gmail + App Password) — ตั้งค่าด้วย env:
//   SMTP_HOST (ค่าเริ่มต้น smtp.gmail.com), SMTP_PORT (465), SMTP_USER, SMTP_PASS, MAIL_FROM
const SMTP_USER = process.env.SMTP_USER || '';
const SMTP_PASS = process.env.SMTP_PASS || '';

let transporter = null;

export function isMailConfigured() {
  return Boolean(SMTP_USER && SMTP_PASS);
}

function getTransporter() {
  if (!transporter) {
    const port = Number(process.env.SMTP_PORT || 465);
    transporter = nodemailer.createTransport({
      host: process.env.SMTP_HOST || 'smtp.gmail.com',
      port,
      secure: port === 465,
      auth: { user: SMTP_USER, pass: SMTP_PASS },
    });
  }
  return transporter;
}

const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

function wrap(title, bodyHtml) {
  return `
  <div style="font-family:Tahoma,Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;background:#0a0b0f;color:#eceef3;border-radius:16px">
    <h2 style="margin:0 0 8px;color:#f2c14e">GoldBot24 · ${title}</h2>
    ${bodyHtml}
  </div>`;
}

const codeBox = (code) =>
  `<div style="font-size:34px;font-weight:700;letter-spacing:10px;text-align:center;padding:16px;background:#14171e;border:1px solid #5a4519;border-radius:12px;color:#f2c14e">${code}</div>`;

async function send(to, subject, text, html) {
  const from = process.env.MAIL_FROM || `GoldBot24 <${SMTP_USER}>`;
  await getTransporter().sendMail({ from, to, subject, text, html });
}

export async function sendResetCodeEmail(to, code, displayName) {
  const name = escapeHtml(displayName || to.split('@')[0]);
  const html = wrap(
    'รีเซ็ตรหัสผ่าน',
    `<p style="margin:0 0 16px;color:#a3abba">สวัสดีคุณ ${name}<br/>รหัสยืนยันสำหรับตั้งรหัสผ่านใหม่ของคุณคือ</p>
    ${codeBox(code)}
    <p style="margin:16px 0 0;color:#a3abba;font-size:13px">รหัสนี้ใช้ได้ภายใน 15 นาที และใช้ได้ครั้งเดียว<br/>หากคุณไม่ได้ขอรีเซ็ตรหัสผ่าน ไม่ต้องทำอะไร บัญชีของคุณยังปลอดภัย</p>`
  );
  await send(
    to,
    `GoldBot24 รหัสยืนยัน ${code} สำหรับตั้งรหัสผ่านใหม่`,
    `รหัสยืนยันสำหรับตั้งรหัสผ่านใหม่ของ GoldBot24: ${code}\nใช้ได้ภายใน 15 นาที หากคุณไม่ได้ขอ ไม่ต้องทำอะไร`,
    html
  );
}

export async function sendRegisterCodeEmail(to, code, displayName) {
  const name = escapeHtml(displayName || to.split('@')[0]);
  const html = wrap(
    'ยืนยันอีเมลสมัครสมาชิก',
    `<p style="margin:0 0 16px;color:#a3abba">สวัสดีคุณ ${name}<br/>รหัสยืนยันสำหรับสร้างบัญชี GoldBot24 ของคุณคือ</p>
    ${codeBox(code)}
    <p style="margin:16px 0 0;color:#a3abba;font-size:13px">รหัสนี้ใช้ได้ภายใน 15 นาที และใช้ได้ครั้งเดียว<br/>หากคุณไม่ได้สมัครสมาชิก ไม่ต้องทำอะไร จะไม่มีการสร้างบัญชี</p>`
  );
  await send(
    to,
    `GoldBot24 รหัสยืนยัน ${code} สำหรับสมัครสมาชิก`,
    `รหัสยืนยันสำหรับสมัครสมาชิก GoldBot24: ${code}\nใช้ได้ภายใน 15 นาที หากคุณไม่ได้สมัคร ไม่ต้องทำอะไร`,
    html
  );
}

/** มีคนพยายามสมัครด้วยอีเมลที่มีบัญชีอยู่แล้ว → แจ้งเจ้าของอีเมลแทนการบอกบนหน้าเว็บ (กันสุ่มหาอีเมลสมาชิก) */
export async function sendAlreadyRegisteredEmail(to, displayName, siteUrl) {
  const name = escapeHtml(displayName || to.split('@')[0]);
  const resetUrl = `${siteUrl}/forgot-password?email=${encodeURIComponent(to)}`;
  const html = wrap(
    'มีการขอสมัครด้วยอีเมลของคุณ',
    `<p style="margin:0 0 12px;color:#a3abba">สวัสดีคุณ ${name}<br/>มีผู้พยายามสมัครสมาชิกด้วยอีเมลนี้ แต่อีเมลนี้มีบัญชี GoldBot24 อยู่แล้ว</p>
    <p style="margin:0 0 12px;color:#a3abba">หากเป็นคุณ ให้เข้าสู่ระบบด้วยบัญชีเดิม หรือหากลืมรหัสผ่าน ตั้งใหม่ได้ที่<br/>
    <a href="${resetUrl}" style="color:#f2c14e">${escapeHtml(resetUrl)}</a></p>
    <p style="margin:0;color:#a3abba;font-size:13px">หากไม่ใช่คุณ ไม่ต้องทำอะไร บัญชีของคุณยังปลอดภัย</p>`
  );
  await send(
    to,
    'GoldBot24 · อีเมลนี้มีบัญชีอยู่แล้ว',
    `มีผู้พยายามสมัครสมาชิก GoldBot24 ด้วยอีเมลนี้ แต่อีเมลนี้มีบัญชีอยู่แล้ว\nหากลืมรหัสผ่าน ตั้งใหม่ได้ที่ ${resetUrl}\nหากไม่ใช่คุณ ไม่ต้องทำอะไร`,
    html
  );
}
