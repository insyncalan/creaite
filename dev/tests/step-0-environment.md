# Step 0 — Environment check

Run 2026-10-04 on Alan's Mac (macOS 26 / Darwin 25.6), dev repo `~/dev.env/creaite`. Nothing installed.

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | Python ≥ 3.9, `sqlite3`, FTS5 | **Pass** | Python 3.14.7 (python.org build, `/Library/Frameworks/…`); SQLite 3.50.4; FTS5 table created and a quoted `"ABC-A-003"` search matched |
| 2 | Bundled libraries import | **Pass** | openpyxl 3.1.5, et_xmlfile 2.0.0, jinja2 3.1.6, markupsafe 3.0.3, all loaded from `system/scripts/vendor/` via `paths.py`; workbook save/load and autoescaped template render work. Vendored packages have no dist metadata, so `markupsafe.__version__` raises — `doctor.py` must not read `__version__` |
| 3 | Run scripts in this folder | **Pass** | `python3 system/scripts/paths.py` runs; `system/staging/` writable; `settings.json` loads |
| 4 | Microsoft 365 mail, Teams, calendar | **Pass, one gap** | One-off read-only test, approved by Alan; no content recorded. Mail search in Inbox and Sent Items, Teams chat search and calendar search all return results. `teams_list_teams` fails: the connector lacks `Team.ReadBasic.All` (admin consent needed), so channels can't be listed by team. Whether search returns channel posts was not confirmed (see below) |
| 5 | Teams transcript and meeting chat | **Not confirmed** | `OnlineMeetingTranscript.Read.All` and `OnlineMeetingArtifact.Read.All` are granted, but reading an event and its transcript was blocked by Claude Code's auto-mode personal-data check before it reached Microsoft. Until Alan runs it himself, cx-minutes falls back to "download the transcript to `inbox/`" |
| 6 | docx skill fills `minutes-template.docx` (edit route) | **Pass, with gaps** | Copy unpacked, all 16 `{{…}}` placeholders filled, action row repeated, repacked; zip and XML well-formed; `textutil` reads it correctly. The skill's helper scripts (`merge_runs.py`, `validate.py`) need `defusedxml`, and pandoc, LibreOffice, Poppler and Node are not installed — so no XSD validation, no PDF render, and **no `accept_changes.py`** (needed in Step 3 to accept tracked changes before filing) |
| 7 | Chrome folder access | **Pass (03-10-2026)** | Chrome 154.0.8037.97 installed, same version as the recorded pass. Edge not installed |
| 8 | `claude` CLI, signed in | **Pass** | `~/.local/bin/claude`, Claude Code 2.1.288, logged in via claude.ai |
| 9 | Headless Claude Code reaches Microsoft 365 | **Pass (tools visible)** | `claude mcp list`: Microsoft 365 Connected. `claude -p … --output-format json` lists the mail, chat, calendar and `read_resource` tools; the email-subject read was not run. Headless warned the workspace is **not trusted**, so it ignores the allow rules in `.claude/settings.json` — accept the trust dialog once interactively (needed for Steps 4c and 6). The warning prints before the JSON on the same output, so `live_server.py` must parse stdout only |

**Gate (items 1–4 and 6): passed.** Gaps to resolve: Team.ReadBasic.All consent (or discover channels from search results), transcript retrieval (item 5), and tracked-change acceptance without LibreOffice (Step 3).

**Microsoft 365 permissions granted:** Calendars.Read(.Shared), Channel.ReadBasic.All, ChannelMessage.Read.All, Chat.Read(Basic), ChatMember.Read, ChatMessage.Read, Files.Read(.All), Mail.Read(.Shared), Mail.ReadBasic, MailboxFolder.Read, MailboxItem.Read, OnlineMeeting* (AiInsight, Artifact, Recording, Transcript, Meetings).Read, Sites.Read.All, User.Read, User.ReadBasic.All. Read-only throughout.

## Repo notes

- `core.hooksPath` set to `dev/hooks` (it was not set, so the pre-commit hook was not active for the initial commit; that commit was checked by hand and holds no vault data).
- `.claude/settings.json` denies `git push` and `curl` for Claude, so pushes are run by Alan.

## Decisions from Step 0

- Alan's address is `alan.carter@brightwater.example`. Some of his own calendar items show `alan.carter@brightwater.example` as organiser; treat that as an alias when matching his items in cx-sweep. `settings.json` `identity` has no email field yet: add one (default empty in this repo) when settings are wired in Step 4b, and set it in the live vault in Step 7.
- Dates: shown and typed DD-MM-YYYY; stored YYYY-MM-DD in the database, staging, sources and settings; file names `YYYY-MM-DD Title`. Confirmed by Alan 2026-10-04.
