# H3 (#221): proposed wording for `system/creaite-rules.md`

`system/creaite-rules.md` is not edited by H3 (Alan's rule: never). These are the changes the Product Manager or Alan can apply when the Reporting hub is released.

## 1. Starting a session, step 4 (Reminders), the client reports line

Replace

> - **Client reports:** for each active project whose `Client report rhythm` (in its `CLAUDE.md`; default weekly) has passed since its last approved client report, say "ABC client report due (last: YYYY-MM-DD) — say client report ABC".

with

> - **Client reports:** for each active project that needs a separate client report (`Client report: on` in its `CLAUDE.md`; no line means on) and whose `Client report reminder` is not off, and whose `Client report rhythm` (default weekly) has passed since its last approved client report, say "ABC client report due (last: YYYY-MM-DD) — say client report ABC". A project with `Client report: off` has no client reminder.

(`session.py` already follows this; `build_dashboard.reminders` is the one place.)

## 2. Folder map, `projects/<CODE> <Name>/` row, or Memory rules

Add one sentence where the project's `CLAUDE.md` is described:

> A project's `CLAUDE.md` also holds its client report setting beside the rhythm: `Client report: on|off` (a missing line is on; a new project starts off), `Client report reminder: on|off` and `Client report logos: firm, client, partner` (the firm's is always shown). They are changed in the Reporting hub's Client report settings or in Settings › Projects (one setting), saved like the rhythm (a copy first, a `settings-log.jsonl` line). Turning the report off deletes nothing.

## 3. Folder map, `system/scripts/` row

Add: `report_server.py` also serves `/api/report/logo/save` and `/api/report/logo/remove` (H3: a logo added, changed or removed from the screen, in `system/branding/logos/`, through `filechange.py`; the file chosen is kept as `<name>-original.<ext>` and the trimmed copy that is drawn is `<name>.png`).

## 4. Non-negotiables: nothing changes

The logos stay in the vault's git-ignored `system/branding/logos/` and never leave the laptop.
