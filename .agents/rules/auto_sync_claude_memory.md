# Claude Memory & Context Auto-Sync Rule

> คำสั่งบังคับสำหรับ AI (Gemini / Antigravity): ก่อนเริ่มงานพัฒนาโค้ดหรือตอบคำถามในโปรเจกต์นี้ทุกครั้ง
> ให้ใช้บริบท, กฎเหล็ก, สไตล์, และ Memory ที่ซิงค์มาจาก Claude Code ด้านล่างนี้เป็นแนวทางเดียวกัน 100%

## 1. กฎเหล็กและ Memory ที่บันทึกไว้ในโปรเจกต์ (Claude Memory Snapshot)

### `MEMORY.md`
```markdown
- [User language: Thai](user-language-thai.md) — reply in Thai; every task summary MUST be in Thai
- [Bump version on every change](feedback-bump-version-every-change.md) — run tools/bump_version.py (YYYY.MMDD.HHMM) before each commit
- [Beam rejected — use SlipOK](project-beam-payment-pending.md) — Beam/Omise restrict forex/trading; SlipOK slip flow is the payment path
- [Plan 1 only](project-plan1-focus.md) — only edit Plan 1 (MA M15) until user names another plan
- [Dry runs: stub mt5.login](feedback-dryrun-mt5-login.md) — legacy credentials.json gets copied in; a failed login logs out the user's MT5
```

### `feedback-bump-version-every-change.md`
```markdown
---
name: feedback-bump-version-every-change
description: Every code change must bump the app version (YYYY.MMDD.HHMM) before committing
metadata:
  node_type: memory
  type: feedback
  originSessionId: 50c7f82d-3e3e-4389-a142-3305a0fca4d6
  modified: 2026-10-04T15:40:21.817Z
---

Every time code is changed (desktop bot/GUI or web), bump the version number to the current time in `YYYY.MMDD.HHMM` format before committing — run `python tools/bump_version.py` (single source of truth: `version.py`).

**Why:** User asked explicitly on 2026-10-04 ("ทุกการปรับโค้ด ต้องการให้อัปเดตเลขของเวอร์ชันด้วย"); the project's AGENTS.md versioning rule uses timestamp versions and the desktop update check compares them.

**How to apply:** After edits and before `git commit`, run the bump script, mention the new version in the commit message and in the reply. If a build/release is made, the ZIP/release tag must use the bumped version. Related: [[user-language-thai]]
```

### `feedback-dryrun-mt5-login.md`
```markdown
---
name: feedback-dryrun-mt5-login
description: Bot dry runs must stub mt5.login — app_paths copies an old credentials.json (with a stale MT5 password) from the project folder into any fresh APPDATA
metadata:
  node_type: memory
  type: feedback
  originSessionId: 50c7f82d-3e3e-4389-a142-3305a0fca4d6
  modified: 2026-10-07T15:47:28.157Z
---

When running `multi_asset_ai_bot.main()` in a test/dry run, stub `mt5.login` (and `send_order`/`close_position`/`modify_position`/`mt5.order_send`, `supabase_sync` in BOTH the bot module AND `stats_manager` (it imports supabase_sync itself and writes `user_trade_history.csv`/`user_stats_store.json` in the PROJECT folder), `sound_manager`, telemetry thread) BEFORE calling main.

**Why:** On 7 Oct 2026 a dry run redirected APPDATA to a scratch folder; `app_paths.data_path` migrated the legacy `credentials.json` (old MT5 password, gitignored, in the project root) into it, main() called `mt5.login(#106584946)` with that stale password, the login failed and the user's MT5 terminal was logged out ("Terminal: Authorization failed"), stopping their live bot.

Also 8 Oct 2026: the close-detection pass recorded a real closed deal via stats_manager → a `local_user` row reached Supabase `user_plan_stats` and the two project files got committed. Run `git status` before committing after any dry run.

**How to apply:** Never let test code call `mt5.login`. If MT5 `initialize()` returns -6 Authorization failed, tell the user to log back in via MT5 (File → Login to Trade Account); never try passwords. Also: pylint/pyflakes do NOT catch use-before-assignment inside the bot's `while` loop, nor a missing `module.NAME` in another module — before EVERY release that touches any .py the bot imports (plan_config, stats_manager, thai_time…), run the cross-module `hasattr` check AND dry-run the scan loop (forced entry branches). 8 Oct 2026: deleting a block in plan_config also removed MIN_BALANCE_USD → v2026.1008.0710 bot crashed 3×/stopped. Related: [[feedback-bump-version-every-change]]
```

### `project-beam-payment-pending.md`
```markdown
---
name: project-beam-payment-pending
description: Beam REJECTED GoldBot24 on 2026-10-05 (forex/trading category); Omise has the same restriction — SlipOK slip verification is the payment path
metadata:
  node_type: memory
  type: project
  originSessionId: 50c7f82d-3e3e-4389-a142-3305a0fca4d6
  modified: 2026-10-05T04:32:40.599Z
---

Beam (beamcheckout.com) rejected the GoldBot24 merchant application on 2026-10-05: "ยังไม่รองรับธุรกิจประเภทนี้". Their restricted list prohibits "stocks, securities, financial products, and foreign currency exchange" and "gold futures"; a gold/forex trading bot falls under it. Omise/Opn lists the same restriction (financial products, foreign currency exchange), so the earlier "Omise as fallback" plan is unlikely to pass either. `CHECKLIST_BEAM.md` is obsolete.

**Why:** Payment gateways classify trading-bot software sold to forex/gold traders as high-risk financial products. Do not suggest disguising the business category to get approved.

**How to apply:** Treat SlipOK slip verification (already live: PromptPay QR → upload slip → auto-verify, `log: true` + amount check) as the main payment flow and improve its UX rather than chasing gateways. A no-slip option realistically needs a bank direct QR API with payment callback (e.g. KBank K-API / SCB API), which normally requires a registered company (นิติบุคคล). Bump version per [[feedback-bump-version-every-change]].
```

### `project-plan1-focus.md`
```markdown
---
name: project-plan1-focus
description: From 2026-10-06 only Plan 1 (MA M15) may be changed; Plans 2–5 stay untouched until the user says otherwise
metadata:
  node_type: memory
  type: project
  originSessionId: 50c7f82d-3e3e-4389-a142-3305a0fca4d6
  modified: 2026-10-06T11:36:32.878Z
---

Since 2026-10-06 the user is improving **Plan 1 (MA-Cross-Trend, M15) only**. Do not change Plans 2–5 (rules, SL, filters, enable/disable) unless the user explicitly asks; they said they will tell me when another plan should be edited.

**Why:** the user wants to tune one plan at a time and keep the others as a stable baseline.

**How to apply:** suggestions for other plans (e.g. Plan 4 SR-Bounce losing in backtest) may be mentioned as observations, but don't edit them. Plan 1 state as of v2026.1006.0842: H1 MA100/150/200 stack + M15 MA5×MA13 cross, fake-signal filter (RSI 50–70 / 30–50 + close vs M15 MA50), SL fixed 1.0 ATR (P1_SL_ATR_MULT), step trailing every 5 pts moving 40%, exit on reverse cross. On 2026-10-06 the user also explicitly asked for Plan 5 (BB-H1) step trailing ($5 / 40%) — done in v2026.1006.1725; that was a one-off request, other Plan 5 changes still need the user to ask. Always backtest before changing (tools/backtest_all.py), see [[feedback-bump-version-every-change]].
```

### `user-language-thai.md`
```markdown
---
name: user-language-thai
description: Always write replies and every end-of-task summary in Thai (code identifiers/terms can stay English)
metadata:
  node_type: memory
  type: user
  originSessionId: 50c7f82d-3e3e-4389-a142-3305a0fca4d6
  modified: 2026-10-05T07:49:15.276Z
---

User communicates in Thai and the project docs (AGENTS.md, SKILL.md) are Thai-first. Reply in Thai, keeping trading/code terms (ATR, RRR, SL/TP, function names) in English.

**Every summary must be in Thai** — the user has asked "อธิบายเป็นภาษาไทย" several times after English summaries (2026-10-05) and then explicitly said "อธิบายเป็นภาษาไทยทุกครั้งที่สรุป". Never write the final report / recap of a task in English, even after long English tool work.
```

## 2. ประวัติการสั่งงานล่าสุดจาก Claude Code (Latest Session)
- **ไฟล์ Session ล่าสุด**: `50c7f82d-3e3e-4389-a142-3305a0fca4d6.jsonl`
- **ข้อความล่าสุดที่ผู้ใช้สั่งการไว้**:
  - `[2026-10-08T15:36:16.110Z]` คอมไพ และ deploy
  - `[2026-10-08T15:43:40.291Z]` [Image: source: C:\Users\AomNote\AppData\Local\Temp\claude\d---------AI-MetaTrader5-FBS\50c7f82d-3e3e-4389-a142-3305a0fca4d6\images\68.png]
  - `[2026-10-08T15:44:58.586Z]` ทำไมโปรแกรมเวอร์ชันไหม่ถึงโหลดไม่เจอ
  - `[2026-10-08T15:46:30.737Z]` <task-notification> <task-id>bxocburoe</task-id> <tool-use-id>toolu_01MfApfE94TFLV5aCh6wq1hZ</tool-use-id> <output-file>C:\Users\AomNote\AppData\Local\Temp\claude\d---------AI-MetaTrader5-FBS\50c7f82d-3e3e-4389-a142-3305a0fca4d6\tasks\bxocburoe.output</output-file> <status>completed</status> <summar
  - `[2026-10-08T23:15:22.879Z]` วิเคราะห์ไม้ล่าสุด ควรปรับปรุงอะไร

---
*ไฟล์นี้สร้างและอัปเดตอัตโนมัติโดย tools/sync_claude_memory.py*