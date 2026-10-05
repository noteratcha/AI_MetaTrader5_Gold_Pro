import crypto from 'crypto';

// Webhook ของ LINE OA — ใช้หา userId / groupId สำหรับตั้งค่า LINE_ADMIN_TO
//   พิมพ์ "id" ในแชทกับ OA (หรือในกลุ่มที่เชิญ OA เข้าไป) → บอทตอบ ID กลับมา
// ตรวจลายเซ็น x-line-signature ด้วย LINE_CHANNEL_SECRET เสมอ
export const config = { api: { bodyParser: false } };

async function readRaw(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(typeof chunk === 'string' ? Buffer.from(chunk) : chunk);
  return Buffer.concat(chunks);
}

function validSignature(raw, signature) {
  const secret = process.env.LINE_CHANNEL_SECRET;
  if (!secret || !signature) return false;
  const expected = crypto.createHmac('sha256', secret).update(raw).digest('base64');
  const a = Buffer.from(expected);
  const b = Buffer.from(String(signature));
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

async function reply(replyToken, text) {
  if (!process.env.LINE_CHANNEL_ACCESS_TOKEN || !replyToken) return;
  await fetch('https://api.line.me/v2/bot/message/reply', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${process.env.LINE_CHANNEL_ACCESS_TOKEN}` },
    body: JSON.stringify({ replyToken, messages: [{ type: 'text', text }] }),
  }).catch((err) => console.error('[webhook/line] reply failed:', err.message));
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(200).send('ok');
  const raw = await readRaw(req);
  if (!validSignature(raw, req.headers['x-line-signature'])) return res.status(401).send('invalid signature');

  let body = {};
  try {
    body = JSON.parse(raw.toString('utf8'));
  } catch {
    return res.status(400).send('bad json');
  }

  for (const ev of body.events || []) {
    const src = ev.source || {};
    const id = src.groupId || src.roomId || src.userId;
    const kind = src.groupId ? 'Group ID' : src.roomId ? 'Room ID' : 'User ID';
    const text = String(ev.message?.text || '').trim().toLowerCase();
    if (ev.type === 'join' || (ev.type === 'message' && (text === 'id' || text === '/id'))) {
      await reply(ev.replyToken, `${kind} สำหรับ LINE_ADMIN_TO:\n${id}`);
    }
  }
  return res.status(200).send('ok');
}
