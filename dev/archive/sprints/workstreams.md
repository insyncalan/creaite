# Sprint: Workstreams (BL-58, BL-56 phase 2)

Branch `sprint-workstreams`, worktree `../creaite-workstreams`. Runs in parallel with `sprint-search` (`../creaite-search`). Read the BL-58 and BL-56 write-ups in `dev/BACKLOG.md` first; they hold Alan's decisions.

## Goal

Workstreams become part of each project, like milestones: each has a lead, keywords and aliases. Items match the right workstream, and the same name can be used in two projects safely. Person pages are finished: Prep 1:1, handover, warnings, and the key-person signal.

## Items

Commit each separately, in this order.

### 1. BL-58 Workstreams table (schema change; Alan agreed the table on 2026-10-06)

**The schema change.** Follow the change control in `dev/BUILD.md`, keeping these in step: `schema.sql`, `tracker.py`, `excel_sync.py`, the dashboard, `tracker-conventions.md` and `BUILD.md`.

**The table.** A `workstreams` table with these columns:
- `project` and `name` (unique together);
- `lead` (a full name from the people register);
- `keywords` and `aliases` (comma-separated);
- `channel` (Teams, optional);
- `status` (`Active` or `Closed`);
- `created` and `source`.

Show the exact DDL to Alan before writing it.

**Validation in `tracker.py`.**
- An action or RAID item whose workstream isn't Active in its project is rejected, with a plain message.
- A blank workstream is still allowed.
- Workstreams themselves are new, changed and closed through proposals (a new `table: "workstreams"`), so every change is logged and can be undone.

**Migration.** `tracker.py migrate`:
- seeds each project's workstreams from the project and workstream pairs already on items;
- seeds from the per-project `settings.json` `workstreams` keys too (the `CODE|name` keys from BL-57);
- leaves leads and keywords empty;
- loses no data, and running it twice changes nothing.

After that, the old settings keys are retired (cx-setup offers to clear them, like the people migration). `update.py` already runs `migrate`.

**Matching** (cx-minutes, cx-sweep, `project-matching.md`, `tracker-conventions.md`):
- Match the project first, then the workstream from that project's list only, by name, keyword, alias, lead or channel.
- An unknown workstream is left blank and flagged in Review with a suggestion ("New workstream 'Integration' for ORX?"). It is never invented.
- A workstream name used in more than one project is never evidence for a project; one unique to a project is a weak signal.

**Creating one.** Possible from the picker ("Add workstream to ORX"), Settings, cx-edit and Review. creaite always suggests keywords, aliases, lead and channel from the items and sources that mention the name, and Alan confirms. Same pattern as the new-person prompt in BL-55.

**Where workstreams show.**
- **Settings › Workstreams:** reads the table, and its edits become proposals.
- **The project page:** a Workstreams card listing each workstream with its lead and open counts.
- **The Work filter.**
- **Person pages:** "workstreams they lead", from the table rather than `D.leads`' current guess.
- **Excel:** the export gains a Workstreams sheet, read-only, or editable through the existing import if it's simple.

### 2. BL-56 phase 2: Person pages

- **Prep 1:1:** on a person's page, opens a brief like meeting prep (BL-49): what they owe, by project, overdue first; recent decisions; warnings on their items; workstreams they lead.
- **Handover:** select a person's open items and reassign them to someone in the register, in one proposal (logged, undoable). The owner prompt from BL-55 applies.
- **On the person page:** early-warning flags (BL-51) on their items, and items closed in the last 14 days.
- **Key-person signal (BL-51's last signal):**
  - **When it fires:** one person owns more than `warnings.key_person.share` (default 50%) of a project's open items, with at least `warnings.key_person.min_items` (default 6).
  - **How it works:** worked out in `build_dashboard.early_warnings`, never stored.
  - **Where it shows:** on the project page and in the health evidence.
  - **Settings:** switched off or tuned in Settings › Warnings.
- Counts only, never scores. Never in client reports.

## Boundaries

- **Owns:**
  - in `schema.sql`, the new table only;
  - in `tracker.py`, validation, apply and `migrate` for workstreams;
  - `excel_sync.py`;
  - `propose.py`;
  - `review.py`;
  - the workstream picker, Settings › Workstreams, the project page's Workstreams card, the person page and People view;
  - in `build_dashboard.py`, `early_warnings` and `workstream_leads`;
  - the workstream parts of the cx-minutes, cx-sweep, cx-edit, cx-review and cx-setup skills and their references.
- **Don't edit** (sprint-search owns these):
  - in `tracker.py`, `cmd_index`, `text_of`, `fts_terms` and `cmd_query`;
  - the `vault_search` line in `schema.sql`;
  - the search routes in `live_server.py`;
  - the Files view and the ⌘K search row;
  - the enrichment step in the skills.

  Also leave alone `update.py` beyond what `migrate` needs, `doctor.py` and `dev/tools/` (the paused live-vault sprint). Note any change needed there under "Hand-offs".
- **Shared files** (`dashboard.html`, `build_dashboard.py`, `settings.json`, `help.md`, `dev/dashboard-spec.md`, the cx-minutes skill):
  - put new code in its own marked section, `/* ===== Workstreams (BL-58, BL-56) ===== */`;
  - add new data keys at the end of `collect()`'s dict;
  - don't reformat or reorder existing lines;
  - leave `BACKLOG.md` and `BRD.md` alone: they are updated at merge.
- **Development guard:** sample data only, and test with temporary vaults.

## Done when

**Tests:**
- schema and migration: seeded from items and from settings, run twice with no change, nothing lost;
- validation rejects an undefined workstream;
- new, rename and close as proposals, with undo;
- extraction matches only within the project, and an unknown workstream is flagged;
- Excel round trip;
- the picker, Settings › Workstreams and the project page card in headless Chrome;
- Prep 1:1, handover with undo, and the key-person signal;
- the full suite passes in this worktree.

**Docs:** help and `dev/dashboard-spec.md` updated, and a short "Workstreams" section added to `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-workstreams`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)

- ✓ Done on main, 2026-10-07. **`dev/tools/demo_data.py` (sprint-live-vault):** its demo proposals set workstreams (FAL Commercial, ORX Testing, Cut-over, Data) that no workstream row defines, so since BL-58 those items are refused at apply. It should add the projects' workstreams first (a `table: "workstreams"` item per name, or run `tracker.py migrate` after loading items directly).
- **`update.py`:** no change needed; it already runs `tracker.py migrate`, which now also seeds the workstreams. cx-setup then offers `propose.py workstreams retire-settings`.
