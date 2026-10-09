"""
สคริปต์ซิงค์ข้อมูล Memory และบริบทการพัฒนาจาก Claude Code เข้าสู่โปรเจกต์อัตโนมัติ
แหล่งข้อมูล:
  - C:\\Users\\AomNote\\.claude\\projects\\d---------AI-MetaTrader5-FBS\\memory\\*.md
  - C:\\Users\\AomNote\\.claude\\projects\\d---------AI-MetaTrader5-FBS\\*.jsonl
ปลายทาง:
  - .agents/rules/auto_sync_claude_memory.md
"""
import glob
import json
import os
import sys

# ป้องกัน UnicodeEncodeError บน Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CLAUDE_PROJECT_DIR = r"C:\Users\AomNote\.claude\projects\d---------AI-MetaTrader5-FBS"
CLAUDE_MEMORY_DIR = os.path.join(CLAUDE_PROJECT_DIR, "memory")
TARGET_RULE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".agents",
    "rules",
    "auto_sync_claude_memory.md",
)


def read_claude_memories():
    memories = []
    if not os.path.exists(CLAUDE_MEMORY_DIR):
        return memories

    for file_path in glob.glob(os.path.join(CLAUDE_MEMORY_DIR, "*.md")):
        name = os.path.basename(file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                memories.append({"filename": name, "content": content})
        except Exception as e:
            memories.append({"filename": name, "content": f"Error reading: {e}"})
    return memories


def get_latest_session_summary():
    if not os.path.exists(CLAUDE_PROJECT_DIR):
        return None

    jsonl_files = glob.glob(os.path.join(CLAUDE_PROJECT_DIR, "*.jsonl"))
    if not jsonl_files:
        return None

    # เอาไฟล์ที่แก้ไขล่าสุด
    jsonl_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    latest_file = jsonl_files[0]

    last_user_msgs = []
    try:
        with open(latest_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        for line in lines:
            try:
                obj = json.loads(line)
                if obj.get("type") == "user" and "message" in obj:
                    c = obj["message"].get("content")
                    ts = obj.get("timestamp", "")
                    if isinstance(c, str):
                        last_user_msgs.append((ts, c.strip()))
                    elif isinstance(c, list):
                        for item in c:
                            if isinstance(item, dict) and item.get("type") == "text":
                                last_user_msgs.append((ts, item.get("text", "").strip()))
            except Exception:
                continue
    except Exception as e:
        return f"Error reading session: {e}"

    return {
        "file": os.path.basename(latest_file),
        "recent_messages": last_user_msgs[-5:],
    }


def generate_rule_content(memories, session_info):
    lines = [
        "# Claude Memory & Context Auto-Sync Rule",
        "",
        "> คำสั่งบังคับสำหรับ AI (Gemini / Antigravity): ก่อนเริ่มงานพัฒนาโค้ดหรือตอบคำถามในโปรเจกต์นี้ทุกครั้ง",
        "> ให้ใช้บริบท, กฎเหล็ก, สไตล์, และ Memory ที่ซิงค์มาจาก Claude Code ด้านล่างนี้เป็นแนวทางเดียวกัน 100%",
        "",
        "## 1. กฎเหล็กและ Memory ที่บันทึกไว้ในโปรเจกต์ (Claude Memory Snapshot)",
        "",
    ]

    for m in sorted(memories, key=lambda x: x["filename"]):
        lines.append(f"### `{m['filename']}`")
        lines.append("```markdown")
        lines.append(m["content"])
        lines.append("```")
        lines.append("")

    if session_info:
        lines.append("## 2. ประวัติการสั่งงานล่าสุดจาก Claude Code (Latest Session)")
        lines.append(f"- **ไฟล์ Session ล่าสุด**: `{session_info['file']}`")
        lines.append("- **ข้อความล่าสุดที่ผู้ใช้สั่งการไว้**:")
        for ts, msg in session_info.get("recent_messages", []):
            if msg:
                clean_msg = msg[:300].replace("\n", " ")
                lines.append(f"  - `[{ts}]` {clean_msg}")
        lines.append("")

    lines.append("---")
    lines.append("*ไฟล์นี้สร้างและอัปเดตอัตโนมัติโดย tools/sync_claude_memory.py*")
    return "\n".join(lines)


def main():
    print("[SYNC] กำลังดึงข้อมูล Memory จาก Claude...")
    memories = read_claude_memories()
    session_info = get_latest_session_summary()

    content = generate_rule_content(memories, session_info)
    os.makedirs(os.path.dirname(TARGET_RULE_FILE), exist_ok=True)
    with open(TARGET_RULE_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

    print(f"[SUCCESS] บันทึก Memory สำเร็จแล้วที่: {TARGET_RULE_FILE}")
    print(f"   - พบไฟล์ Memory {len(memories)} ไฟล์")
    if session_info:
        print(f"   - ซิงค์บริบทจาก Session ล่าสุด: {session_info['file']}")


if __name__ == "__main__":
    main()
