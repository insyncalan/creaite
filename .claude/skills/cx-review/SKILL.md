---
name: cx-review
description: creaite review and approval. Shows everything pending (draft minutes, proposed items, Excel edits) grouped by project, records Alan's decisions, applies them through tracker.py, and can undo the last apply. Use when Alan says "review", "review ABC", "review minutes", "what's pending", "approve…", "reject…", gives an edit like "4 owner is Sara", "9 is DEF", "apply", "undo last apply", or "import excel".
---

# cx-review

The single gate between proposals and the record. Show, record decisions, then apply when told.

**Projects by name (BL-101):** refer to a project by its full name in everything Alan reads (summaries, tables, messages, file names, drafts). The short code appears only inside a work item's ID (`ABC-A-003`) and in a command he can type; `tracker.project_label(code)` gives the name.

Read `dev/staging-format.md` first. Only `system/scripts/tracker.py` writes. This skill never edits the database or project files directly.

`system/scripts/review.py` does the listing and records decisions, and enforces the bulk rule itself. Show its output to Alan as a table (dates are already DD-MM-YYYY). Numbers refer to the last `review.py list`; list again whenever proposals may have changed.

| Alan says | Run |
|-----------|-----|
| "what's pending" | `review.py pending` |
| "review", "review ABC", "review minutes" | `review.py list`, `review.py list ABC`, `review.py list minutes` |
| "approve 1–6", "approve 3, 8" | `review.py approve 1-6` / `review.py approve 3,8` |
| "reject 7" | `review.py reject 7` |
| "approve all", "approve ABC", "approve all strong" | `review.py bulk`, `review.py bulk ABC`, `review.py bulk --strong` |
| "4 is an update to FAL-A-007", "make 4 an update to the SOW action" | BL-297: `review.py retarget 4 FAL-A-007` (an open item of the same project and kind; `review.py candidates 4` lists them, best matches first). Undo with `review.py unmerge 4` (also undoes a merge) |
| "is 6 already in the tracker?" | Find the existing item by its words with `python3 system/scripts/tracker.py read <table> --project CODE --search "SOW"` (case-insensitive; add `--status open` for open items only), never by reading a whole table and filtering it (BL-252). If more than one matches, list them and ask |
| "9 is DEF" | `review.py assign 9 DEF` (any pending new item, BL-200); then, if the item carries `signals`, offer once to remember one (below). Moving it back to its first project restores the milestone and workstream the move cleared (BL-281) |
| "minutes 3 is DEF", "move these minutes to DEF" | BL-200: first `review.py assign 3 DEF --dry-run` and show its line ("Move 9 items from Example Programme to DEF") and notes; on Alan's yes, `review.py assign 3 DEF`. Minutes filed under several projects: ask which project's items to move, then add `--from=ABC`. Items already moved on their own stay unless Alan says to move all (`--all`) |
| "4: owner is Sara, due 15-10-2026" | Resolve the owner first (below), then `review.py edit 4 "owner=Sara Example" due_date=15-10-2026` |
| "keep 5" / "override 5" (a conflict) | `review.py keep 5` / `review.py override 5` |
| "add the workstream for 6" / "6 without a workstream" | `review.py workstream 6 add [--lead=… --keywords=… --aliases=… --channel=…]` / `review.py workstream 6 skip` |
| "approve minutes for ABC steering" | find its number in the list, then `review.py approve <n>` |

## Triggers

| Alan says | Do |
|-----------|----|
| "what's pending" | One-line count by project: drafts, items needing a project, conflicts, decisions and risks, routine items, stale items |
| "review", "review ABC", "review minutes" | Show the review (everything, one project, or draft minutes only) |
| Decisions (see below) | Record them in the proposal files; nothing is written yet |
| "import excel" | Run `system/scripts/run excel_sync.py import`, then show the review |
| "apply" | Run `system/scripts/run tracker.py apply` for every proposal with decided items |
| "undo last apply" | Confirm first, then run `system/scripts/run tracker.py undo` |

Before showing a review, if `system/scripts/run excel_sync.py changed` reports unimported edits, offer to import them first.

## Unknown workstreams (BL-58)

An item flagged `new-workstream` named a workstream its project doesn't have; staging left it blank and kept the name ("New workstream “Integration” for ORX?"). Suggest its details first (`propose.py workstreams suggest ORX "Integration"`: keywords, aliases, lead, channel) and let Alan confirm or change them. On yes, `review.py workstream <n> add --lead=… --keywords=…` puts the new workstream (approved) into the same proposal, before the item, and sets it on the item; the item is then approved as usual. Or `review.py workstream <n> skip` leaves it blank. Never add one Alan hasn't confirmed.

## Unknown owners (BL-55)

An item flagged `unknown-owner` has an owner who isn't in the people register (`projects/_portfolio/people-register.md`). Show the flag with its likely matches (`propose.py people resolve "<name>"`). Alan decides: **"4 is Sara Khan"** → `review.py edit 4 "owner=Sara Khan"`, and offer once to remember the alias (`propose.py people edit "Sara Khan" --add-alias Sara`, staged and approved); **"add Sara as a new person"** → ask for the full name (required) and the email, aliases, organisation and role if known, then `propose.py people add …`. Never choose a likely match for him, and don't block approval: an owner he leaves as written is kept as written. The same check, with the same offers, runs in the dashboard's owner picker and Review.

## Review layout: grouped by project

1. **Needs a project** (shown first): unresolved items and cx-sweep **Possible** matches. Alan assigns them ("9 is DEF"). Until he does, they can't be approved.
   - **Learn from the choice (BL-28):** after Alan sets the project of an item that carries `signals`, name one concrete signal to remember, checked first with `propose.py learn <CODE> <kind> <value> --check` (for example "Add sara.khan@northgate.example as an ORX sender?"). Yes: `propose.py learn <CODE> <kind> <value>` (staged, approved, written at apply). No: move on. Ask once per item. If the check says it already belongs to another project, offer Shared instead (`--shared`); never a single keyword or Alan's own domain.
2. **One section per project** (by code), in this order:
   1. **Draft documents:** minutes (title, date, projects to be filed under), weekly and client reports, each with a link to the draft in `system/staging/drafts/`. Approve with "approve minutes for …", "approve ABC weekly report", "approve ABC client report".
   2. **Conflicts:** an Excel edit against a newer change, shown side by side.
   3. **Individual approval only:** weekly and client reports (with links), health changes, new decisions and new risks.
   4. **Everything else:** actions, issues, assumptions, dependencies, updates to existing items, and cx-edit changes.
3. **Stale items** (pending more than `review.stale_after_days` in `system/config/settings.json`, default 7) are marked ⚠ and sorted to the top of their section. They never expire.
4. **VIP items first (BL-99), unlabelled (BL-288):** an item flagged `vip` (sourced from a VIP's message, set by `sweep.py stage`) is listed first in its section, ahead of stale items. The flag is for ordering only: never show `vip` in the Flags column, never label the item or its sender a VIP, and never say why it is first. The dashboard's Review does the same.

Number items continuously across the whole review, so numbers are unique.

Columns: # · Type · Description · Owner · Due · Match · Flags · Source

## Dashboard decisions and edits

- The dashboard can **edit proposals** before approval (all fields; "Save" or "Save and approve"). Edited proposals carry `"edited_in": "dashboard"`; show the edited values.
- With **auto-apply** on (`dashboard.auto_apply`, default true), every dashboard save or decision is applied straight away through the live server; Claude Code then sees it as already applied. With it off, dashboard decisions wait for "apply" as before.
- Copy-command buttons no longer exist; the bulk rule is unchanged.

## Recording decisions

| Alan says | Effect |
|-----------|--------|
| "approve 1–6", "approve 3, 8", "reject 7" | Those items |
| "4: owner is Sara, due 2026-10-15" | Edit the item, validate it, and mark it approved |
| "9 is DEF" | Set the project of any pending new item (match becomes strong; a milestone or workstream of the old project is cleared), then wait for a decision. An update item stays with its project |
| "minutes 3 is DEF" | Move every item from those minutes, and their filing (the minutes and transcript copies, `projects`), to DEF, after showing the result. Nothing moves on disk until the minutes are approved; nothing reaches the tracker until apply |
| "approve minutes for ABC steering", "reject minutes for …" | Set the meeting's `minutes_decision` (by its number in the review) |
| "keep 5", "override 5" | A conflict: keep the database version (the edit is rejected), or apply the edit over the newer change |
| "reject 4 as a duplicate of ABC-A-009", "reject 7 because not mine to track", "reject 3, 5 because covered in the steering pack" | BL-133: reject with a reason: `review.py reject 4 as a duplicate of ABC-A-009` (or `--duplicate-of=ABC-A-009`), `review.py reject 7 because not mine to track` (or `--reason="…"`). The reason is stored with the rejection, shown in Activity and read by cx-minutes and cx-sweep as guidance; a duplicate's ID must exist. Plain "reject 7" is unchanged |
| "reject 3, 5 as chatter", "reject 2-6 with their guesses", "what would you reject?" | BL-315: the seven reasons are Not an action, Duplicate, Chatter, Already done, Wrong project, Doesn't need tracking and For another team (`review.py reasons`); any case is spelt as listed, and Alan's own words still work. `review.py guesses` shows creaite's guess per pending item (Chatter: a thank-you, or scheduling with no owner; Duplicate of an open look-alike; Already done: a closed look-alike, or closing an item already closed; Doesn't need tracking: no owner named). `review.py reject 2-6 --guess` rejects each with its own guess (none: no reason) |
| "undo the reject of …", "change that reason to chatter", "approve … instead" | BL-315: name a reject by `<proposal file>#<item>` (from `review.py rejects`, newest first; pending or applied). `review.py unreject <key>` puts it back in Review, pending; `review.py rereason <key> --reason=Chatter` (or `--duplicate-of=ID`; no reason clears it) changes its reason; `review.py approve-instead <key>` undoes it and approves it, except minutes, a new decision, a new risk or anything else approved only on its own, which goes back to Review for its individual approval. An applied reject goes back to staging with its `rejected` row noted; the next apply removes or updates that row, and "undo last apply" puts it back |
| "merge 4", "keep 4 as new", "keep-new 4" | BL-221: a new item marked **Looks like ABC-A-009**: `review.py merge 4` turns it into an update to that item carrying any new due date, latest update or response (with nothing new it is rejected as its duplicate); only into an open item of the same project. `review.py keep-new 4` keeps it as a new item and drops the mark. Or `reject 4 as a duplicate of ABC-A-009` |
| "approve ABC, then apply", "approve all, then apply" | Bulk approval as below, immediately followed by apply. These are the commands the dashboard's copy buttons produce |
| "approve all", "approve all strong", "approve ABC" | **Bulk.** Routine items only (section 2.4, with a project and no conflict). **Never** draft minutes, weekly reports, client reports, health changes, new decisions or new risks |

- **Promises (BL-125 A):** a proposed promise shows as type Promise with "promised by → promised to" in the Owner column. A new promise is routine, like a new action, and so is an update that marks one Done or Dropped (Alan, 13-10-2026): Approve routine covers it. The exception is a **Looks done** or **Maybe done** promise (BL-218's probably done), which is judged on its evidence and approved on its own, as an action's is. Edit its people or date like an action's fields (`promised_by`, `promised_to`, `due_date`: "4: promised to is Sara Example, due 15-10-2026").
- **Validation:** run `system/scripts/run tracker.py validate <proposal>` after each edit. Show any rule failure at once ("due date must be YYYY-MM-DD"), and leave the item pending.
- **After a bulk approval,** say what was left out: "Approved 11. Still need individual approval: 2 decisions, 1 risk, 1 set of minutes, 1 weekly report."
- **Excel Review sheet:** decisions made there arrive through "import excel", under the same rules. A bulk-style approval of a new decision or risk is impossible, because the sheet works row by row.
- Decisions are written into the proposal files in `system/staging/`, so they survive between sessions.

## Edited drafts (minutes, weekly reports, client reports)

Alan may edit a draft in Word before approving it. When he approves a draft individually:
1. **Open file:** if the draft is open (a `~$` lock file exists next to it), ask him to close it and wait. Never file a half-saved copy.
1a. **No sensitivity label step** (Alan, 2026-10-09; BL-121): a draft is approved without any Word sensitivity label, and creaite never looks for one. `docx_tools.py clean` still keeps a label a draft happens to carry.
2. **Consistency check (automatic):** re-read the draft and compare it with the staged proposal.
   - **Minutes:** `review.py approve <n>` compares the draft's actions (owners, due dates), decisions and risks with the staged items. If they differ it approves nothing and lists the differences. Ask Alan "Update the staged proposal to match the draft?": yes → `review.py approve <n> --sync` (owners and due dates); no → `review.py approve <n> --as-staged`. Items added, removed or reworded in the draft need "re-extract" (`minutes.py refresh <proposal>`, which rebuilds the items from the draft and keeps decisions already made on matching items) or `--as-staged`.
   - **Weekly report:** compare health, health reason, summary and key changes with the staged `updates` row and the health change, and the current-state text with the memory `write`.

   If anything differs, show it ("Draft says Off track; staged health is At risk") and ask "Update the staged proposal to match the draft? (yes/no)". Update only on yes. "re-extract" does the same at any time.
3. **Client reports:** re-scan the edited draft for internal-only content: risks, issues or decisions not flagged `client_visible`, lines marked `Client-safe: no`, anything from `documents/`, and anything marked confidential. Flag each finding and ask before filing.
4. **Tracked changes and comments:** approving a draft accepts all tracked changes and removes all comments (`docx_tools.py clean`, standard library; LibreOffice isn't needed). Pass on its message: "Accepted 6 tracked changes and removed 2 comments".
5. Then mark the draft approved. On apply, the edited version is filed as is, with only the status line changed to "Approved by Alan on YYYY-MM-DD".

Once filed, a report is Alan's document. Later edits to the filed copy don't change the database; use cx-edit or "undo last apply" for that.

## Apply

Only on an explicit "apply":
1. Run `tracker.py apply` on each proposal with decided items. In one transaction it:
   - backs up the database;
   - writes the approved items;
   - runs file operations for approved minutes (and transcript filing);
   - records rejections;
   - logs every change under a new `apply_id`;
   - updates `system/processed.txt`.
2. `tracker.py` then rebuilds the dashboard and exports Excel. The export pauses if `tracker-view.xlsx` has unimported edits; say so.
3. Undecided items stay pending in their proposal file.
4. Summarise: "Written 14, filed 2 meetings, rejected 3, 4 still pending."

If the apply fails, nothing is written. Show the error and the item it relates to.

## Undo last apply

1. Show what the most recent apply did: items written or changed, meetings filed. Ask "Undo this?".
2. On yes, run `tracker.py undo`. It:
   - removes rows the apply inserted and restores the fields it changed (from `change_log` for that `apply_id`);
   - reverses its file operations: deletes the filed minutes and transcript copies, returns the transcript to `inbox/` and the draft to `system/staging/drafts/`, and restores the "Draft" status line;
   - returns the undone items to pending (moving the proposal back from `applied/`);
   - **skips any item changed since that apply,** and reports it rather than overwriting newer data;
   - logs the undo itself.
3. Repeating "undo last apply" steps back through earlier applies, one at a time.


## Dates

Show dates to Alan as DD-MM-YYYY; proposals and the database keep YYYY-MM-DD.
