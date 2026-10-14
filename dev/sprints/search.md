# Sprint: Search (BL-07)

Branch `sprint-search`, worktree `../creaite-search`. Runs in parallel with `sprint-workstreams` (`../creaite-workstreams`; BL-58, BL-56 phase 2). The people register (BL-55) is on `main`. Read the BL-07 write-up in `dev/BACKLOG.md` first; it holds Alan's decisions (2026-10-06).

## Goal

One search box finds anything in the vault instantly and, when asked, answers in plain words with a link to the source for every point. It runs through the live server and keeps all data on the laptop.

## What exists

- **The index:** `vault_search` (FTS5: `path, project, kind, date, content`) and `tracker.py index` / `tracker.py query` (Step 1).
  - It indexes minutes, transcripts and documents only. Reports aren't in it, and PDFs are indexed by name only.
  - It is rebuilt only when someone runs `tracker.py index`. Nothing runs it automatically.
- **The run engine:** `Run` in `live_server.py`, with `kind`, Stop, reattach, one run at a time, timeout, and the read-only tool allow list.
- **The gather-then-prompt pattern:** `report.py current-context` plus `system/templates/current-state-prompt.md` (BL-46).
- **The UI it hangs off:** the ⌘K palette (`ckItems`), the Files view, and Ask creaite's panel and chat history.

## Items

Commit each separately.

### 1. Index: fresher and wider (`tracker.py`)

- **Reports:** index `reports/` as kind `report`, and PDF text where the standard library allows; otherwise keep indexing PDFs by name.
- **Word forms:** stem words so "slip" finds "slipped". This needs `tokenize = 'porter unicode61'` on `vault_search`.
  - It is a change to `schema.sql`, so ask Alan first, under the change control in `dev/BUILD.md`.
  - The table is a derived index, rebuilt in full each time, so the migration is: drop it, recreate it, run `index`.
  - If Alan declines, use prefix matching only.
  - `sprint-workstreams` is also changing `schema.sql` (a new table). Touch only the `vault_search` line, so the two merge cleanly.
- **Keep it fresh:**
  - `index` runs after every apply, after cx-minutes files minutes, after a report is approved, and when the live server starts.
  - The live server also runs it when a search finds the index older than the newest file in the indexed folders (a cheap check of modification times).
  - It is always a full rebuild; incremental indexing isn't worth it at this size.
- **Item records:** the tracker's own items (actions, RAID, decisions, milestones) are searched with plain SQL `LIKE` on their text fields, beside the index. Don't copy item rows into `vault_search`.

### 2. Instant search (part 1)

**The route.** `GET /api/search?q=&project=&person=&kind=&from=&to=` on the live server, read-only. It returns grouped results:
- Items, Meetings, Reports and Documents, each group capped at 20;
- for each result: a snippet with the matching words highlighted, the date shown DD-MM-YYYY, the project, and where it opens.

**Query understanding, without AI** (a small parser, in Python, with tests):
- **Projects:** project codes from the register.
- **People:** names and aliases from the people register (BL-55).
- **Types:** "risk", "issue", "action", "decision", "minutes", "transcript", "report", "document".
- **Dates:** "today", "last week", "last month", "since DD-MM-YYYY", "in September".

Each recognised term becomes a filter chip the user can remove; the remaining words are the search terms. Return the parsed chips with the results so the page shows exactly what was understood.

**The UI:**
- **Files:** a search box at the top. Results replace the file list while the box has text, and pressing Esc clears it.
- **⌘K:** a "Search the vault…" row that runs the same route once the text is three or more characters, and shows the top 5 results under the existing jump list.
- **Project page:** optionally, a project-scoped box.
- **Results open where they belong:**
  - an item opens in its panel;
  - a meeting opens in the file preview, scrolled to the match where possible;
  - a document or report opens with the system viewer, as Files does now.
- **Responsiveness:** results appear as the user types, debounced at 150 ms. Show a plain "Live server needed" note when the server is down.

### 3. Ask (part 2)

**When it appears:**
- An "Ask Claude" row tops the results when the text reads like a question: it ends in "?", or starts with what, why, how, when, who, did, has or is.
- Pressing Enter on question-like text runs Ask, and the row can also be picked for any text.

**What runs:**
- **Gather, without Claude:** `search.py context` collects the top passages from the index, with the surrounding paragraph rather than just the snippet, plus the matching tracker rows. It keeps to a size budget of about 40,000 characters.
- **Prompt:** `system/templates/search-prompt.md` tells Claude to:
  - answer from the gathered sources and, if needed, read the files they name (read-only tools only);
  - cite every point as `[file name › section]` or the item ID;
  - say plainly when the sources don't answer the question;
  - be short, in British English, with dates as DD-MM-YYYY.
- **Run:** through `Run` with `kind: "search"`, so Stop, reattach and one-run-at-a-time all apply. Search runs are not saved as Ask creaite chats.

**How the answer shows:**
- Citations render as links that open the source.
- "Continue in Ask creaite" opens the assistant with the question and the answer as its first exchange.

**Documents:** included and labelled "Document". The prompt reminds Claude that documents are internal.

### 4. Enrichment (part 2)

**What cx-minutes writes.** When it files minutes, it writes a small sidecar file, `system/search/<sha256 of the path>.json`, containing `{path, summary, tags}`:
- `summary` is two lines;
- `tags` is three to eight topic tags, such as "data access", "UAT" or "vendor risk".
cx-weekly-report and cx-client-report do the same for the reports they file. Add `system/search/` to `paths.py` and `paths.DATA`.

**How it is used.** `tracker.py index` folds each file's summary and tags into its `content`, so keyword search matches them. No schema change is needed for this. Results show the summary in place of a raw snippet when there's no better match.

**Backfill.** `search.py enrich --missing` lists the indexed meetings and reports without a sidecar. cx-setup offers a one-off run in which Claude writes the missing sidecars, in batches, and asks before starting.

**Not here.** No AI runs per search for enrichment, and the live server never enriches on its own.

## Boundaries

- **Owns:**
  - new `system/scripts/search.py` and `system/templates/search-prompt.md`;
  - the search routes in `live_server.py` (add them at the end of the route map);
  - `tracker.py` `cmd_index`, `text_of` and `cmd_query`;
  - the Files view's search box;
  - the ⌘K search row;
  - the enrichment step in the cx-minutes, cx-weekly-report and cx-client-report skills;
  - cx-setup's backfill offer.
- **Don't edit:** anything `sprint-workstreams` owns (the `workstreams` table and its validation and migration in `tracker.py`, `excel_sync.py`, `propose.py`, `review.py`, workstream pickers and Settings, the project page's Workstreams card, person pages, `early_warnings`, the workstream parts of the skills); the people register code (read it, don't change it); `update.py`, `doctor.py` and `dev/tools/` (the paused live-vault sprint). Note any change needed there under "Hand-offs".
- **Shared files:** `dashboard.html`, `build_dashboard.py`, `settings.json`, `help.md` and `dev/dashboard-spec.md`.
  - Put new code in its own marked section, `/* ===== Search (BL-07) ===== */`.
  - Add new settings keys under a new `search` block: `debounce_ms`, `ask_budget_chars`, `include_documents` (default true).
  - Don't reformat or reorder existing lines.
  - Leave `BACKLOG.md` and `BRD.md` alone; they are updated at merge.
- **Rules that apply:**
  - Local only: no embedding service, and no provider other than the headless Claude Code that Ask creaite uses.
  - Search is read-only: it never writes to the database or `staging/`.
  - Development guard: sample data only, and test with temporary vaults.

## Done when

**Tests:**
- the query parser (codes, people and aliases, types, dates and their DD-MM-YYYY forms);
- the index covers reports and stays fresh after apply, and a stale index is rebuilt on search;
- stemming, if Alan agrees to it;
- `/api/search` grouping and filters;
- the size budget in search-context;
- the Ask run with a stub `claude` (as the existing live-server tests do): its citations, Stop, and that it isn't saved as a chat;
- enrichment sidecars are folded into the index, and `enrich --missing` lists them;
- the Files box and the ⌘K row in headless Chrome;
- the full suite passes in this worktree.

**Docs:** help and `dev/dashboard-spec.md` updated, and a short "Search" section added to `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-search`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)

- ✓ Done on main, 2026-10-07. **`doctor.py`:** two checks would help: `vault_search` was made with word forms (`sqlite_master` holds `porter`; otherwise run `tracker.py migrate`), and `system/search/` is writable. `tracker.index_state()` says whether the index is stale.
- **`update.py`:** nothing to change: it already runs `tracker.py migrate`, which now recreates and rebuilds the index (and the `system/search` folder is in `paths.DATA`, so it is never replaced or removed).
- ✓ Done on main, 2026-10-07. **`live_server.py` allow lists (`READ_TOOLS`):** Ask creaite's panel could also be given `Bash(python3 system/scripts/search.py query *)` so it can search the vault as the search box does. The search answer itself needs nothing: it works from the gathered context and the read tools it already has.
