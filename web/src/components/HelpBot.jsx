'use client';

// ผู้ช่วยตอบคำถาม (FAB มุมขวาล่างทุกหน้า · ผู้ใช้สั่ง 16 ต.ค. 2026)
// ค้นคำตอบจากคู่มือ/ฐานความรู้ (lib/helpKb.js + lib/helpSearch.js) — ไม่ใช้ AI ตอบได้แม้ถามด้วยคำใกล้เคียง
// ย่อ/ขยายหน้าต่างได้ · ประวัติแชทจำในเบราว์เซอร์ · ทุกคำถาม + 👍/👎 ส่งไปเก็บที่ /api/help/log → แอดมินดูที่ /admin/help
import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen, Bot, ChevronDown, Maximize2, MessageCircle, Minimize2, RotateCcw, Send, ThumbsDown, ThumbsUp, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { answerHelp } from '../lib/helpSearch';
import { resolveLive } from '../lib/helpLive';
import { SUGGESTED } from '../lib/helpKb';
import { LINE_ID, LINE_URL } from '../lib/contact';

const STORE_KEY = 'helpbot_v1';
const MAX_MSGS = 60;

function load() {
  try {
    const v = JSON.parse(localStorage.getItem(STORE_KEY) || '{}');
    return { msgs: Array.isArray(v.msgs) ? v.msgs : [], sid: v.sid || null, big: !!v.big, seen: !!v.seen };
  } catch {
    return { msgs: [], sid: null, big: false, seen: false };
  }
}
function save(state) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({ ...state, msgs: state.msgs.slice(-MAX_MSGS) }));
  } catch {
    /* โหมดส่วนตัว / ปิดที่เก็บข้อมูล */
  }
}
const newSid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);

function Answer({ m, onAsk, onVote, openAuthModal }) {
  if (!m.found) {
    return (
      <div className="hb-card">
        <div className="hb-card-title">ยังไม่พบคำตอบที่ตรงกับคำถามนี้</div>
        <p className="hb-text">ทีมงานบันทึกคำถามไว้แล้วเพื่อเพิ่มในคู่มือ ลองพิมพ์คำอื่น หรือสอบถามแอดมินได้โดยตรง</p>
        {m.related?.length > 0 && (
          <div className="hb-related">
            <span className="hb-related-label">หัวข้อที่อาจเกี่ยวข้อง</span>
            {m.related.map((r) => (
              <button key={r.id} type="button" className="hb-chip" onClick={() => onAsk(r.t)}>
                {r.t}
              </button>
            ))}
          </div>
        )}
        <a className="hb-link" href={LINE_URL} target="_blank" rel="noreferrer">
          <MessageCircle size={14} /> ถามแอดมินทาง LINE {LINE_ID}
        </a>
      </div>
    );
  }
  return (
    <div className="hb-card">
      <div className="hb-card-title">
        {m.t}
        {m.live && <span className="hb-live">ข้อมูลล่าสุด</span>}
      </div>
      <p className="hb-text">{m.a}</p>
      {m.needLogin && openAuthModal && (
        <button type="button" className="hb-chip" style={{ width: 'fit-content' }} onClick={() => openAuthModal('login')}>
          เข้าสู่ระบบ
        </button>
      )}
      {m.href && (
        <Link className="hb-link" href={m.href}>
          <BookOpen size={14} /> {m.href.startsWith('/guide') ? 'อ่านต่อในคู่มือ' : 'ไปที่หน้านี้'} ›
        </Link>
      )}
      {m.related?.length > 0 && (
        <div className="hb-related">
          <span className="hb-related-label">หัวข้อใกล้เคียง</span>
          {m.related.map((r) => (
            <button key={r.id} type="button" className="hb-chip" onClick={() => onAsk(r.t)}>
              {r.t}
            </button>
          ))}
        </div>
      )}
      <div className="hb-vote">
        {m.vote ? (
          <span className="hb-vote-done">{m.vote === 'up' ? 'ขอบคุณครับ ดีใจที่ช่วยได้' : 'ขอบคุณครับ ทีมงานจะปรับปรุงคำตอบนี้'}</span>
        ) : (
          <>
            <span>คำตอบนี้ช่วยได้ไหม?</span>
            <button type="button" aria-label="ช่วยได้" onClick={() => onVote(m, 'up')}>
              <ThumbsUp size={14} />
            </button>
            <button type="button" aria-label="ไม่ช่วย" onClick={() => onVote(m, 'down')}>
              <ThumbsDown size={14} />
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function HelpBot() {
  const { apiFetch, user, openAuthModal } = useAuth();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [big, setBig] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const [sid, setSid] = useState(null);
  const [seen, setSeen] = useState(true);
  const [text, setText] = useState('');
  const [typing, setTyping] = useState(false);
  const listRef = useRef(null);
  const inputRef = useRef(null);
  const ready = useRef(false);

  useEffect(() => {
    const s = load();
    setMsgs(s.msgs);
    setBig(s.big);
    setSeen(s.seen);
    setSid(s.sid || newSid());
    ready.current = true;
  }, []);
  useEffect(() => {
    if (ready.current) save({ msgs, sid, big, seen });
  }, [msgs, sid, big, seen]);
  useEffect(() => {
    if (open && listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [msgs, typing, open]);
  useEffect(() => {
    if (!open) return undefined;
    const t = setTimeout(() => inputRef.current?.focus(), 120);
    const onKey = (e) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => {
      clearTimeout(t);
      window.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const post = useCallback(
    (body) => {
      apiFetch('/api/help/log', { method: 'POST', body: JSON.stringify({ ...body, sid }) }).catch(() => {});
    },
    [apiFetch, sid],
  );

  const ask = useCallback(
    (raw) => {
      const q = String(raw || '').trim().slice(0, 300);
      if (!q || typing) return;
      setText('');
      const id = Date.now();
      setMsgs((m) => [...m, { id, role: 'user', text: q }]);
      setTyping(true);
      const r = answerHelp(q);
      const best = r.best?.doc;
      const reply = {
        id: id + 1,
        role: 'bot',
        q,
        found: r.found,
        top: best?.id || '',
        t: r.found ? best.t : '',
        a: r.found ? best.a : '',
        href: r.found ? best.href : '',
        related: r.related.map((x) => ({ id: x.doc.id, t: x.doc.t })),
      };
      post({ kind: 'ask', q, top: best?.id || '', t: best?.t || '', s: r.best?.score || 0, ok: r.found, page: pathname || '' });
      const started = Date.now();
      const done = (rep) =>
        setTimeout(() => {
          setMsgs((m) => [...m, rep]);
          setTyping(false);
        }, Math.max(0, 380 - (Date.now() - started)));
      if (r.found && best.live) {
        // ข้อมูลสดจากหน้าเว็บ (ผล Backtest · เวอร์ชัน · แพ็กเกจ · ข่าว · ชั่วโมง/สมาชิกของฉัน)
        resolveLive(best.live, q, { user }).then((lv) => done({ ...reply, ...lv, live: true }));
        return;
      }
      done(reply);
    },
    [typing, post, pathname, user],
  );

  const vote = useCallback(
    (m, v) => {
      setMsgs((list) => list.map((x) => (x.id === m.id ? { ...x, vote: v } : x)));
      post({ kind: 'feedback', q: m.q, top: m.top, v });
    },
    [post],
  );

  const clearChat = () => {
    setMsgs([]);
    setSid(newSid());
  };

  const toggle = () => {
    setOpen((o) => !o);
    setSeen(true);
  };

  return (
    <>
      {open && (
        <section className={`hb-panel ${big ? 'is-big' : ''}`} role="dialog" aria-label="ผู้ช่วย Gold Bot 24">
          <header className="hb-head">
            <span className="hb-avatar" aria-hidden="true">
              <Bot size={20} />
            </span>
            <div className="hb-head-text">
              <strong>ผู้ช่วย Gold Bot 24</strong>
              <span>ตอบจากคู่มือโปรแกรมและเว็บ</span>
            </div>
            <div className="hb-head-actions">
              {msgs.length > 0 && (
                <button type="button" title="เริ่มแชทใหม่" aria-label="เริ่มแชทใหม่" onClick={clearChat}>
                  <RotateCcw size={16} />
                </button>
              )}
              <button type="button" title={big ? 'ย่อหน้าต่าง' : 'ขยายหน้าต่าง'} aria-label={big ? 'ย่อหน้าต่าง' : 'ขยายหน้าต่าง'} onClick={() => setBig((b) => !b)} className="hb-only-desktop">
                {big ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
              </button>
              <button type="button" title="ย่อเก็บ" aria-label="ย่อเก็บ" onClick={() => setOpen(false)}>
                <ChevronDown size={18} />
              </button>
            </div>
          </header>

          <div className="hb-body" ref={listRef}>
            <div className="hb-msg is-bot">
              <div className="hb-card hb-welcome">
                <div className="hb-card-title">สวัสดีครับ มีอะไรให้ช่วยไหม?</div>
                <p className="hb-text">ถามเรื่องการใช้โปรแกรม แผนเทรด ค่าบริการ หรือเว็บไซต์ได้เลย พิมพ์ภาษาพูดได้ตามสะดวก</p>
                <div className="hb-related">
                  {SUGGESTED.map((s) => (
                    <button key={s} type="button" className="hb-chip" onClick={() => ask(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            {msgs.map((m) =>
              m.role === 'user' ? (
                <div key={m.id} className="hb-msg is-user">
                  <div className="hb-bubble">{m.text}</div>
                </div>
              ) : (
                <div key={m.id} className="hb-msg is-bot">
                  <Answer m={m} onAsk={ask} onVote={vote} openAuthModal={openAuthModal} />
                </div>
              ),
            )}
            {typing && (
              <div className="hb-msg is-bot">
                <div className="hb-typing" aria-label="กำลังค้นคำตอบ">
                  <i />
                  <i />
                  <i />
                </div>
              </div>
            )}
          </div>

          <form
            className="hb-input"
            onSubmit={(e) => {
              e.preventDefault();
              ask(text);
            }}
          >
            <input
              ref={inputRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="พิมพ์คำถาม เช่น ต้องมีทุนเท่าไหร่"
              maxLength={300}
              aria-label="พิมพ์คำถาม"
            />
            <button type="submit" disabled={!text.trim() || typing} aria-label="ส่งคำถาม">
              <Send size={17} />
            </button>
          </form>
          <div className="hb-foot">คำตอบเป็นข้อมูลทั่วไป ไม่ใช่คำแนะนำการลงทุน · คำถามถูกเก็บไว้เพื่อปรับปรุงบริการ</div>
        </section>
      )}

      <button type="button" className={`hb-fab ${open ? 'is-open' : ''}`} onClick={toggle} aria-label={open ? 'ปิดผู้ช่วย' : 'ถามผู้ช่วย'} aria-expanded={open}>
        {open ? <X size={24} /> : <Bot size={26} />}
        {!open && !seen && <span className="hb-fab-dot" aria-hidden="true" />}
        {!open && <span className="hb-fab-label">ถามผู้ช่วย</span>}
      </button>
    </>
  );
}
