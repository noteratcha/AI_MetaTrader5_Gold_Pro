"""
แปลงข้อความ stdout ของบอทให้อ่านง่ายบน Console ของ Desktop App
- ซ่อนข้อความที่ไม่จำเป็น (ตัวนับถอยหลัง, เส้นคั่น, log ภายใน)
- ย่อบล็อกแดชบอร์ดการสแกน (10 บรรทัด) เหลือ 1 บรรทัด
- จัดหมวด + สีตามความสำคัญ และกรองข้อความซ้ำ
ระดับ: "key" = แสดงเสมอ, "detail" = แสดงเมื่อเปิด "รายละเอียดการสแกน"
"""
import re
import time

# สีของแต่ละหมวด (Hex สำหรับ Tk เท่านั้น)
TAG_COLORS = {
    "time": "#6E7687",
    "buy": "#34D399",
    "sell": "#F87171",
    "profit": "#34D399",
    "loss": "#F87171",
    "close": "#F2C14E",
    "exit": "#FB923C",
    "lock": "#60A5FA",
    "error": "#F87171",
    "warn": "#E0A92B",
    "system": "#A78BFA",
    "scan": "#A3ABBA",
    "position": "#60A5FA",
    "muted": "#6E7687",
    "text": "#D8DCE4",
}

DEDUPE_SECONDS = 300

_HIDE_PATTERNS = [
    re.compile(r"^[=\-─]{10,}$"),
    re.compile(r"^\[AI SCANNER\]"),
    re.compile(r"^\[SIGNAL LOGGED\]"),
    re.compile(r"^\*{3} AI SIGNAL ALERT"),
    re.compile(r"^->\s(?!SL:)"),  # รายการใน AI SIGNAL ALERT (แต่เก็บบรรทัด "-> SL: | TP:" ของออเดอร์ใหม่)
    re.compile(r"^\[LOCK (THROTTLE|BUFFER)\]"),
    re.compile(r"^\[STREAM\]"),
]

# (regex, tag, level, ซ้ำได้หรือไม่)
_RULES = [
    (re.compile(r"^\[SUCCESS - AUTO TRADE\].*Opened BUY"), "buy", "key"),
    (re.compile(r"^\[SUCCESS - AUTO TRADE\].*Opened SELL"), "sell", "key"),
    (re.compile(r"^-> SL:"), "muted", "key"),
    (re.compile(r"^\[SIGNAL\].*SENDING BUY"), "buy", "key"),
    (re.compile(r"^\[SIGNAL\].*SENDING SELL"), "sell", "key"),
    (re.compile(r"^\[FAILED"), "error", "key"),
    (re.compile(r"^\[(ERROR|BOT ENGINE ERROR)\]"), "error", "key"),
    (re.compile(r"^\[(WARNING|WARN)\]"), "warn", "key"),
    (re.compile(r"^\[TP HIT\]"), "profit", "key"),
    (re.compile(r"^\[SL HIT\]"), "loss", "key"),
    (re.compile(r"^\[ORDER CLOSED\]"), "close", "key"),
    (re.compile(r"^\[(PLAN 1 EXIT|PLAN 2 EXIT|AI REVERSAL)\]"), "exit", "key"),
    (re.compile(r"^\[(PROFIT LOCK|DYNAMIC TP|SL/TP UPDATED)"), "lock", "key"),
    (re.compile(r"^\[CIRCUIT BREAKER\]"), "error", "key"),
    (re.compile(r"^\[TAKE PROFIT \$\]"), "profit", "key"),
    (re.compile(r"^\[LOSS BLOCK CLEARED\]"), "profit", "key"),
    (re.compile(r"^\[LOSS BLOCK\]"), "warn", "key"),
    (re.compile(r"^\[PLAN DISABLED\]"), "warn", "key"),
    (re.compile(r"^\[MARKET CLOSED\]"), "warn", "key"),
    (re.compile(r"^\[MARKET OPEN\]"), "profit", "key"),
    (re.compile(r"^\[P4 WAIT CONFIRM\]"), "system", "key"),
    (re.compile(r"^\[P4 CONFIRMED\]"), "lock", "key"),
    (re.compile(r"^\[P4 CONFIRM EXPIRED\]"), "warn", "key"),
    (re.compile(r"^\[(AI TRAINING|AI QUALITY|OK|AI READY|ACCOUNT|SUCCESS|LICENSE|STOP|\*)\]"), "system", "key"),
    (re.compile(r"^\[(AI BOT|ASSET FOCUS|ACTIVE PLANS|RISK/RRR|DATA RETENTION)\]"), "system", "detail"),
    (re.compile(r"^\[REQUOTE RETRY"), "warn", "detail"),
    (re.compile(r"^\[(COOLDOWN|PLAN BLOCK|FAKE SIGNAL FILTER|H4 CONFLUENCE FILTER|MAX POSITIONS|SIDEWAY GUARD)\]"), "warn", "detail"),
    (re.compile(r"^\[NEW H[14] BAR\]"), "scan", "detail"),
    (re.compile(r"^\[POSITION\]"), "position", "detail"),
]

_FRIENDLY = [
    (re.compile(r"Market closed|\(Code: 10018\)"), "  → ตลาดปิด (นอกเวลาเทรด/วันหยุด) บอทจะเข้าไม้ใหม่เมื่อตลาดเปิด"),
    (re.compile(r"\(Code: 10019\)|No money|Not enough money"), "  → มาร์จิ้นไม่พอ"),
    (re.compile(r"\(Code: 10027\)|AutoTrading disabled"), "  → กรุณาเปิดปุ่ม Algo Trading ใน MT5"),
]

_BLOCK_KEYS = {
    "Gold Price": "price",
    "H4 Regime": "h4",
    "AI Predict": "ai",
    "Status": "status",
}
_BLOCK_LINE = re.compile(r"^(Gold Price|H4 Regime|AI Predict|S&R Zone H1|Bollinger H1|MA\(5/10\) M15|MA\(5/10\) H1|Status)\s*:\s*(.*)$")
_BLOCK_START = re.compile(r"^\[TIME:\s*(\d{2}:\d{2}:\d{2})\]")
_ONE_LINE_SCAN = re.compile(
    r"^\[(\d{2}:\d{2}:\d{2})\].*?Price:\s*([\d.,]+).*?\|\s*(\[H4:[^\]]*\]).*?AI: UP ([\d.]+%) \| DOWN ([\d.]+%) \| (\[[^\]]+\])"
)


class ConsoleFormatter:
    def __init__(self):
        self._buffer = ""
        self._block = None
        self._last_seen = {}
        self._last_status = None

    # ------------------------------------------------------------------
    def feed(self, text: str) -> list:
        """รับข้อความดิบ (อาจตัดกลางบรรทัด) → [(ข้อความที่จะแสดง, tag, level), ...]"""
        self._buffer += text
        parts = re.split(r"[\r\n]", self._buffer)
        self._buffer = parts.pop()  # ส่วนท้ายที่ยังไม่จบบรรทัด
        out = []
        for raw in parts:
            out.extend(self._handle_line(raw.strip()))
        return out

    # ------------------------------------------------------------------
    def _stamp(self):
        return time.strftime("%H:%M:%S")

    def _is_duplicate(self, line: str) -> bool:
        key = re.sub(r"[\d.,:+-]+", "#", line)
        now = time.time()
        last = self._last_seen.get(key)
        self._last_seen[key] = now
        if len(self._last_seen) > 500:
            self._last_seen = {k: v for k, v in self._last_seen.items() if now - v < DEDUPE_SECONDS}
        return last is not None and now - last < DEDUPE_SECONDS

    def _handle_line(self, line: str) -> list:
        if not line:
            return []

        # บล็อกแดชบอร์ดการสแกน → ย่อเหลือ 1 บรรทัด
        m = _BLOCK_START.match(line)
        if m:
            self._block = {"time": m.group(1)}
            return []
        if self._block is not None:
            m = _BLOCK_LINE.match(line)
            if m:
                key = _BLOCK_KEYS.get(m.group(1))
                if key:
                    self._block[key] = m.group(2).strip()
                if m.group(1) == "Status":
                    return [self._block_summary()]
                return []
            if line.startswith("[POSITION]"):
                return [(f"   {line.replace('[POSITION] ', '📌 ')}\n", "position", "key")]
            if any(p.match(line) for p in _HIDE_PATTERNS):
                return []
            self._block = None

        for pattern in _HIDE_PATTERNS:
            if pattern.match(line):
                return []

        m = _ONE_LINE_SCAN.match(line)
        if m:
            t, price, h4, up, down, status = m.groups()
            h4_clean = h4.strip("[]").replace("H4: ", "H4 ")
            return [(f"📡 {t}  {price} · AI ↑{up} ↓{down} · {h4_clean} · {status}\n", "scan", "detail")]

        tag, level = "text", "detail"
        for pattern, rule_tag, rule_level in _RULES:
            if pattern.match(line):
                tag, level = rule_tag, rule_level
                break

        if level == "detail" and self._is_duplicate(line):
            return []

        result = [(f"{self._stamp()}  ", "time", level), (f"{line}\n", tag, level)]
        for pattern, hint in _FRIENDLY:
            if pattern.search(line):
                result.append((f"{hint}\n", "warn", level))
                break
        return result

    def _block_summary(self):
        b = self._block or {}
        self._block = {"_done": True}  # รอรับ [POSITION] ที่ตามมา
        price = (b.get("price") or "").split("|")[0].strip()
        ai = (b.get("ai") or "").replace("UP ", "↑").replace("DOWN ", "↓").replace(" | ", " ")
        h4 = (b.get("h4") or "").split("|")[0].strip()
        h4 = re.sub(r"\s*\[[~^v]\]", "", h4)
        status = b.get("status") or ""
        tag = "buy" if "BUY" in status else ("sell" if "SELL" in status else "scan")
        # แสดงเป็นข้อความสำคัญเฉพาะเมื่อสถานะเปลี่ยน — สถานะเดิมซ้ำทุก 20 วินาทีถือเป็นรายละเอียด
        level = "key" if status != self._last_status else "detail"
        self._last_status = status
        return (f"📡 {b.get('time', self._stamp())}  {price} · AI {ai} · H4 {h4} · {status}\n", tag, level)
