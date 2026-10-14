# Sprint: Chat bubbles and a fresh dashboard after the sweep (BL-108, BL-109, BL-110)

Branch `sprint-chat-sweep`, worktree `../creaite-chat-sweep`, made from the tip of `main` when it starts. Read BL-108, BL-109 and BL-110 in `dev/BACKLOG.md` first; they hold Alan's requests and the defaults to take where one says "assumed".

## Goal

- Every ask creaite chat bubble shows when it happened (BL-108).
- ask creaite's replies are drawn as formatted markdown, safely (BL-109).
- After a sweep, `dashboard.html` is rebuilt by the sweep itself, and a dashboard that is already open notices and shows the new Review items without a manual reload (BL-110).

## When it can start

The chat code and the live server are being changed by other sprints, so check `dev/archive/sprints/STATUS.md` first.

- **Item 1 (the sweep rebuild)** touches `sweep.py`, `minutes.py` and `build_dashboard.py` only at their tails: it can start any time, beside the others.
- **Items 2 to 4** change the chat panel in `dashboard.html` and `live_server.py`, which sprint 4b, Sprint 5 (the lower-case "ask creaite" pass, BL-105) and debug log part 2 are also editing. **Start them after sprint 4b has merged.** If Alan wants them sooner, follow the rules for working beside another sprint in `debug-log-2.md` (marked blocks, one-line additions, wrappers where another sprint has rewritten a function, and whoever merges second brings `main` in first).
- **Don't rename "Ask creaite" to "ask creaite" here.** That pass is Sprint 5's (BL-105); keep the wording as you find it.

## Order

Commit each item separately.

### 1. The sweep rebuilds the dashboard (BL-110 part 1)

- `build_dashboard.py`: a `rebuild()` helper that calls `build()` and returns quietly; the page is written to a temporary file and renamed, so a reader never sees half a page. A build already running is waited for briefly or skipped (say so in one line).
- `sweep.py`: `stage`, `calendar`, `done` and `fail` call `rebuild()` as their last step. An error in the rebuild is printed as one line (and written to the debug log if `log.py` is in use) and **never changes the command's exit code or result**. `minutes.py stage` does the same.
- `.claude/skills/cx-sweep/SKILL.md`: the end of the flow says `done` rebuilds the dashboard.
- Nothing else in the sweep changes, and approval before writes is untouched (a rebuild reads the database; it writes only the dashboard file, its snapshot and the daily flow snapshot).

### 2. The open page refreshes itself (BL-110 part 2)

- `live_server.py`, in its own marked block: `POST /api/pulse` (token-checked like the other routes) returns `{v, pending, swept}`: `v` is a short hash of file stamps only (the names and modification times of `system/staging/proposed-*.json` and `drafts/`, `last-sweep.txt`, `calendar.json`, and the database's last write); `pending` is the count of items waiting in Review; `swept` the last sweep time. It builds nothing, so it is cheap.
- `dashboard.html`, in its own marked block: the page asks `/api/pulse` with its health check (`S.healthSecs`) and straight away when the window or tab becomes visible. When `v` has changed it calls `reloadData()` and shows a quiet snack "3 new items in Review" only when `pending` rose.
- **The edit guard:** don't reload while Alan is editing: the side panel's form is open (`EDITING`), the Current state editor is open, a dialog is open, or a text field has focus. Show a small chip in the top bar, "New items arrived: refresh", instead; the reload happens when the edit ends or the chip is clicked. Unsaved input is never lost.
- No polling when the page isn't served by the live server or the server is down.

### 3. Markdown in the chat (BL-109)

- A marked `mdChat` section in `dashboard.html`, separate from `mdHtml` (which Current state keeps using, unchanged). **Escape every character first**, then recognise: headings, paragraphs (a single newline stays a line break), bullet and numbered lists (nested), block quotes, horizontal rules, fenced code (with a Copy button), GitHub-style tables (scroll sideways inside the bubble), bold, italic, strikethrough, inline code and links.
- **Links:** `https:`, `http:` and `mailto:` only, `target="_blank" rel="noopener"`; any other scheme stays text. Images in a reply show their alt text. An item ID (use the existing `ITEMID` pattern) becomes a link that opens the item; a path under `projects/` or `inbox/` that is in the Files list opens the file through the existing open route.
- **Use it** for creaite's live replies (the stream's `text` events: today `say()` types them as plain text; keep the typewriter only for the greeting, and render markdown for replies), for replies loaded by `loadChat`, and nowhere else (Alan's own bubbles stay plain; the Files search answer card is left alone). Close an unfinished fence or table for display while a reply streams.
- `white-space: pre-wrap` on `.msg` is for plain text: rendered replies use normal wrapping (single newlines become `<br>`), so the look of ordinary text replies doesn't change.
- Styles in every theme and mode for code, quotes, tables and links, with contrast kept.

### 4. Timestamps on bubbles (BL-108)

- `live_server.py` `remember_chat`: add `at` to each message (Alan's: when sent; creaite's: when the reply started, kept on later updates) and `done_at` when a reply finishes. ISO date and time to the second, the laptop's clock.
- `dashboard.html`: bubbles are made by one helper (extend `addEl` or add `addMsg(who, html, at)`) that adds a `<time datetime>` line under the bubble on its own side: `14:32` today, `08-10 14:32` for an earlier day, full `08-10-2026 14:32:05` on hover; creaite's shows its `done_at` (nothing while it is still running). Day dividers ("Today", "Yesterday", "08-10-2026") where a chat crosses midnight. Live bubbles use the clock at creation. Steps, confirm cards and the greeting have no time. A chat saved before this change shows no per-bubble time (its divider uses `started`).

## Boundaries

- **Owns:** a marked `mdChat` section, the chat bubble helper and the pulse block in `dashboard.html`; a marked block in `live_server.py` (the pulse route, `remember_chat`'s extra fields); the tails of `sweep.py`, `minutes.py` and `build_dashboard.py`; the cx-sweep skill's last step; the tests.
- **Don't edit:** `READ_TOOLS`, `DENY_TOOLS`, the assistant prompts, the Files search answer card, Current state's renderer, or the wording "Ask creaite" / "ask creaite" (see above).
- **Shared files** (`dashboard.html`, `live_server.py`, `sweep.py`): put new code in its own marked block; add lines, don't reformat or move existing ones. Leave `BACKLOG.md` and `BRD.md` alone (updated at merge).
- **Development guard:** sample data and temporary vaults only; the real chat uses a stand-in `claude` that prints markdown; never connect to Microsoft 365.

## Done when

**Tests** (a new `test_chat_and_sweep.py`, real browser for the page parts, the live server for the rest):
- **Sweep:** after `sweep.py stage` (with a staged sample) `dashboard.html` contains the new items; a rebuild that fails leaves the sweep's exit code and result unchanged and prints one line; `minutes.py stage` rebuilds too; a half-written dashboard is never visible (atomic write).
- **Pulse:** `/api/pulse` needs the token; `v` changes when a proposal is staged, when `last-sweep.txt` changes and after an apply, and does not change when nothing does; `pending` matches the review count.
- **Refresh:** with the page open, staging a sweep from outside makes the Review badge and the Review list show the new items within one health-check interval (set short in the test) and a "3 new items in Review" message; with the side panel's form open it does **not** reload, shows the chip, and reloads when the form is closed; an unsaved field's text survives; a dashboard opened as a file never polls.
- **Markdown:** golden inputs for every block and inline form give the expected HTML; **hostile inputs** (`<script>`, `<img onerror>`, `[x](javascript:alert(1))`, `[x](data:…)`, an attribute break-out in a link, a 10,000-character unbroken word) render inert and nothing executes; a half-finished fence while streaming; a table without a separator is plain text; item IDs and Files-list paths link, other paths don't; a history reload renders the same HTML as the live stream; Alan's bubbles are still plain.
- **Timestamps:** a bubble's time is its send time, a reply's its finish time and none while running; an earlier day shows `08-10 14:32` and the full time on hover; a chat over two days has a divider; an old chat shows no per-bubble time; the stored chat has `at` and `done_at`.
- The existing chat, Ask creaite and dashboard tests pass.

The full suite passes: `python3 dev/tools/run_tests.py` (run it when no other session is running tests: the browser tests drop their connection when the machine is busy).

**Docs:** a "Chat and sweep" section in `dev/BUILD.md`, `dev/dashboard-spec.md`, `system/templates/help.md` (the formatting and the timestamps; "new items arrive on their own"), and the cx-sweep skill.

**Commits:** each item committed separately on `sprint-chat-sweep`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)
