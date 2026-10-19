# #195 Usage and context monitor (for 2.5.1) — brief

Mockup: `dev/mockups/usage-monitor-mockup.html` (a third Activity tab, **Usage**). Fictional numbers. Approved by Alan 19-10-2026.

## Why
Alan wants to watch his production instance over time: what each Claude run costs, and what every run loads before it starts (the rules file is about 53 KB). Builds on #197 (landed 2.2.0) and overlaps #87.

## Scope
Read-only view over data creaite already records. Counts only, never text of mail, notes, names or chats.

1. **Summary cards**: cost, runs, tokens loaded at start, cost of an average run; each with change on the previous week.
2. **Chart**: cost per day (bars) and median start load (line), last 14 days.
3. **By kind of run**: runs, average tokens, start load (median), cost, share of cost. Source: `system/staging/run-usage.jsonl` through `usage_report.py` (extend it with `--json`).
4. **What every run loads**: size of the always-loaded files (rules, CLAUDE.md, project memory and registers, skill names), measured once a day and appended to `system/staging/context-size.jsonl` (file, bytes, estimated tokens, date). Change in 30 days shown beside each.
5. **Skills**: runs, cost, last used; "never in this period" flagged.
6. **Your reviews**: Alan's own dated notes (what he saw, what he decided), saved as small records; Download as CSV.

## Rules
- Internal only; nothing leaves the laptop; never in the development repo's data.
- One writer: the live server's daily job writes `context-size.jsonl`; the page only reads. No new guarded file without Jarvis agreeing.
- Tokens are estimates (bytes ÷ 4); say so on the page.
- Desktop and 900 px only.

## Tests (Stark)
Fixture jsonl gives the expected cards, rows and the 30-day change; no text fields are ever written; an empty record shows a plain "No runs yet" state.

## Out of scope
Trimming the rules file (#87). Alerts or budgets (later, once Alan has a baseline).
