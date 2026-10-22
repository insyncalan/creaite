# #283: Read again (Re-extract) as its own run kind — design

**Status: PROPOSED (2.6.1).** Alan's direction on #264 (20-10-2026): a long job started from the dashboard is its own run kind;
ask creaite only on request or genuine need. #268's Minutes view v2 shipped Re-extract as "open ask creaite with the request
written, not sent" and logged it on #264 as the follow-up. This is that follow-up.

**Sizing answer for #283:** not "only a button". The existing re-extract (`minutes.py refresh`) rebuilds items from an edited
**Word** draft and does nothing for a minutes record (the Minutes view's only format). Reading the transcript again needs a new
route, a new guarded mode and a way to replace a pending draft. So, per #283's rule, it is Alan's call for the release: it is
built here as far as it can be without touching a guarded file.

## What Alan sees

1. The Minutes view's refresh icon is now **Read the transcript again** (plain words: never "re-extract", dev/PLAIN-WORDS.md).
2. Pressing it asks on the bar: "Draft these minutes again from the transcript? Your edits here are set aside; Undo brings them
   back." **Read again** / **Cancel**. ask creaite never opens and nothing is written into it.
3. While it runs the bar says "Reading the transcript again: <step>" with **Stop**; Approve minutes waits.
4. At the end:
   - **Done:** the new draft opens. Toast: "Read again: 7 items found in the meeting (2 new, 1 no longer there); your choices
     kept on 4. Your earlier version is set aside: Undo brings it back." with **Undo**.
   - **Stop, a failure, nothing new, or a question:** the earlier minutes stay, exactly as they were. Toast: "Stopped: your
     earlier minutes are back as they were." / "Needs you: <question> Your earlier minutes are back as they were." / "Couldn't
     finish: …".
5. Activity › Usage counts it as its own kind, **Read again**. The run shows plainly in Runs creaite started (BL-326).

## The flow (server owns every move; the model only stages)

```
page                         live server (guarded)                 reextract.py (plain code)            run (mode "reextract")
Read again ──POST /api/minutes/reextract {proposal, run}──▶ foreign_origin? 403
                                                            validate_request ──────────────────────▶ checks (below)
                                                            START_LOCK: busy? 409
                                                              hold(ctx, run) ──────────────────────▶ proposal → staging/reextract/<run>/
                                                              Run(kind="reextract", files=[transcript],
                                                                  closer, lines)  ── start_run: run.json {mode, files, before, made}
                                                                                                                cx-minutes: read
                                                                                                                transcript, Write spec
                                                                                                                in drafts, minutes.py
                                                                                                                stage <spec>
◀── SSE: run, step…, reextract, closure, done ───────────── closer → finish("done") ─────────────────▶ new draft takes the place,
                                                            Stop/fail → _ended → finish("stopped"/"failed")  Track carried; or put back
Undo ──POST /api/minutes/reextract/undo {run}──▶ 403 / 409 / reextract.undo ───────────────────────▶ earlier back, new set aside
server start ──▶ recover_reextract() ──────────────────────────────────────────────────────────────▶ any "held": settled as failed
```

**Why set the earlier proposal aside before the run** (rather than stage beside it and swap after): `minutes.py stage` numbers a
meeting's filed names against every pending proposal (`staged_targets`) and the record's draft name against drafts/, so a second
pending proposal for the same meeting would file its minutes as "… (2).html" and keep two drafts in Review. With the earlier one
held, the run stages exactly as a first Process would: the same filed names, the same meeting key. The earlier **record** stays in
drafts during the run (so the new record never reuses its name and its version history), and joins the hold only once the new one
has taken the place.

## Run kind and fence

| | Process (#264) | Read again (#283) |
|---|---|---|
| Route | `POST /api/intake/process` | `POST /api/minutes/reextract`, `POST /api/minutes/reextract/undo` |
| Kind / hook mode / usage kind | `process` | `reextract` (reach `PROCESS_MODES = ("process", "reextract")`) |
| Files in `run.json` | 1–20 checked Intake files | exactly the one transcript of the pending record (server-chosen) |
| R1 record | `before`, `made`, `prints`, `pending` (round 3: a print only from the PostToolUse) | the same (shared code; the PostToolUse is registered for both modes) |
| `--tools` | Read, Grep, Glob, Bash, Write, Edit, Skill; `--strict-mcp-config` | the same |
| `--add-dir` | the projects folder only | the same (never the home folder) |
| Prompt | KIND_PROMPTS["process"] | KIND_PROMPTS["reextract"]: one transcript, record only, skip enrich |
| Cards | none (NO_CARD_KINDS) | none |

**Allowed (hook mode "reextract"), and only these:**
- Read, Grep, Glob, LS inside the vault and the projects folder (Process's `process_reach_problem`).
- creaite read commands (`SCRIPT_COMMANDS` READ, not `HELD_NOT_READ`): `minutes.py transcript|key|filename|filedate|expected|
  agenda|done-candidates`, `tracker.py` reads, `search.py` reads…
- `Write`/`Edit` of a new `.json` directly in `system/staging/drafts/`, or one this run made (R1).
- `system/scripts/run minutes.py stage system/staging/drafts/<its own spec>.json` where the spec's `"transcript"` is the run's one
  file, it has a `"minutes"` record and **no** `"draft"`.
- `system/scripts/run propose.py people map system/staging/drafts/<its own spec>.json`.
- `system/scripts/run tracker.py validate <a proposal this run staged>`.

**Refused (on top of everything a plain chat refuses):** `docx_tools.py fill` (no Word draft), `search.py enrich` (the meeting
keeps its summary; Process never replaces one), `minutes.py refresh` and `carry`, `tracker.py apply|undo`, `review.py
approve|reject|bulk`, `propose.py stage`, `sweep.py stage`, `report.py`, `filechange.py`, any other file's spec, a spec with a
note, a Word draft or no record, any write outside its own drafts `.json` (proposals, the hold, `run.json`, the records,
`processed.txt`, project and Intake files), the home folder, Microsoft 365, the web, cards and permission offers. A `reextract`
hook never takes another mode's `run.json` as its own (`_process_record` compares the record's mode with the hook's).

## What is recorded

- `system/guard/run.json` (server and hook only): `run`, `mode: "reextract"`, `files: [transcript]`, `before`, `made`, `prints`,
  `pending` (R1 and #264 round 3, shared code: the PostToolUse hook, `reach.py hook --mode reextract --event post`, records a
  print for the run's own file once its tool has returned; `post_tool` takes the hook's mode, so it records only on a run of
  its own mode).
- `system/staging/reextract/<run>/hold.json` (reextract.py only): run, state (`held` → `replaced` | `put_back` | `needs` |
  `failed` | `kept_aside` → `undone`), the earlier proposal's name, its record's stored path, the transcript, date, title,
  projects, times, and once settled the new proposal and record, the counts and the closure line. Beside it: the earlier
  proposal while held (and after a replace), `record.html` (the earlier record after a replace) and `unused/` (a draft the run
  made that didn't take the place). The newest 20 ended holds are kept, never one `kept_aside` (it still holds the earlier
  proposal); nothing is ever deleted otherwise.
- `system/staging/run-usage.jsonl`: kind `reextract` (counts only).
- Debug log: `reextract` lines with run IDs and proposal names, never text.
- Runs creaite started (BL-326 history chat): the plain ask "Read a meeting's transcript again" and the closure line.

## Failure, Stop, Undo, crash

| When | What happens |
|---|---|
| The request fails a check | 400 with one plain line; nothing moved |
| Another run is going | 409 busy; nothing moved |
| The proposal can't be moved | 200 `ok: false` "couldn't be set aside"; nothing moved |
| Claude Code can't start (any fault, review L1) | put back at once (`state: failed`) |
| Stop, the unwatched timeout | `_ended` → `finish("stopped")`: anything the run staged set aside in `unused/`, the earlier one back |
| The run fails | the same, `finish("failed")` |
| Finished, nothing staged | earlier one back: "Nothing new came back from the transcript…" |
| Finished with `QUESTION:` for its transcript | earlier one back; "Needs you: <question>…" |
| Finished, staged | the newest new draft takes the place; any other set aside; Track carried; earlier record into the hold |
| Finished, but the new draft names another project, date or title, or its record isn't in drafts (review M1) | refused: every new draft set aside in `unused/`, the earlier one back; "Not used: the new draft names a different project from your earlier minutes. Your earlier minutes are back as they were." |
| A fault while settling a finished run (review L2) | settled as failed: the earlier one back (and its record, if it had moved) |
| Undo | only while none of the new draft's items is saved or approved and the earlier names are free: the new draft (and its record) into `unused/`, the earlier record and proposal back |
| The server dies mid-run | at the next start `recover_reextract()` settles every `held` hold as failed (earlier one back) |
| The earlier name is taken at put back | `kept_aside`: the earlier proposal stays in the hold; the line says so (Settings › Diagnostics) |

A new draft can take the earlier proposal's **file name** (proposal names are to the minute); the code never tells them apart by
name (the earlier one is in the hold), only by place.

## The Track choices and the draft (minutes_record.py)

The Track column's choices live in the record's `layout.track` ({item number: "y" | "n" | ""}); a row removed in the view is an
item with `decision: "rejected"`. Numbers change when the meeting is read again, so choices are carried **by item**:

- an update (`op: "update"`) matches the new update to the same item ID (whatever the words);
- a new item matches a new item of the same table worded alike, with `minutes.match` and refresh's cut-offs (actions 0.75,
  decisions and RAID 0.6);
- only choices Alan made are carried (an explicit Track choice; else a removed row is a cross); a default is recomputed on the
  new draft;
- the carried choices are written into the new record's `layout.track` in one saved version (`minutes_record.save_record`, a
  filechange edit, undoable as any page save); `#275`'s server-side Track rules then apply them at approval, from the view or
  from Review, exactly as for any record.

**Not carried (by design, the point of reading again):** text edits to the summary, updates, rows or headings, coverage choices,
milestone notes. The earlier record is kept whole in the hold, and Undo brings it back.

**Refused while** any item of the draft is applied, or approved and waiting to be saved (a Track or row change is fine).

## Tests

- `dev/tests/test_reextract.py` (quick tier, 21 tests; 6 are expected failures until the guarded diffs are applied, all pass with
  them):
  - **Helpers** (plain code, unguarded): the request checks and plain words; what stops a read again; the fixed prompt and label;
    hold then nothing back puts it back (settled once); the new draft takes the place with the Track choices (counts, line,
    record, hold contents) and Undo (once; the new one kept aside); Undo waits when the new one is approved; Stop sets the new
    one aside and puts the earlier one back (the event carries no words); a question; recovery at start; the usage kind; a new
    draft naming another project, date or title is refused and the earlier one comes back (review M1); a fault in the closer
    settles as failed (L2); a `kept_aside` hold is never pruned (L4).
  - **ThePage** (static): the button calls `reLive`, never `ckAsk` or the chat box; its words are plain; the page is rebuilt.
  - **Fence** (needs the diffs): the steps pass; everything else refused (Word-draft spec, no-record spec, another file, fill,
    enrich, refresh, apply, undo, approve, reject, propose stage, filechange, writing a proposal, the hold, the record, another
    draft, the home folder); a fill from the run's own values file is refused by Read again's own rule (Process may); Process is
    unchanged and a `reextract` hook never takes a Process record as its own.
  - **ThroughTheServer** (needs the diffs): the real route with a stand-in Claude and the real `minutes.py stage`: replaced, the
    closure and link, nothing applied, the run's own hook refuses apply/fill/refresh, its arguments (mode, `--strict-mcp-config`,
    the deny and allow lists, no home folder), the PostToolUse in mode `reextract` and Edit of its own spec allowed once its
    print is recorded (round 3, H1), usage kind, Undo; 403 for a forged token, Host or Origin (both routes); 400 for a
    bad proposal; one run at a time (409 Undo while running) and Stop puts it back.
- `dev/tests/test_minutes_stage_client_flags.py` (review M2, unguarded `minutes.py`): a spec never stages `client_visible` or
  `client_message` on a new item; both are Alan's alone.
- `dev/tests/test_minutes_view_v2.py` (Chrome tier): the icon's label; the ask and Cancel never touch ask creaite; the run on
  the bar (step, Stop, Approve waits), the new draft opened and Undo through the seams.
- Regression with the diffs applied (one at a time, all OK): intake_process 29, intake_process_round2 8, intake_process_minutes
  11, calendar_refresh 24, reach 18, guard_pinned 2, minutes_stage_spec_hook 6, record_commands 10, permission_panel 14,
  script_policy 11, run_read_pinned 1, vip_tools_pinned 9, usage_log 43, usage_wiring 5, held_bash_arg_forms 7,
  ask_reports_refused 6, enrich_guard 10, guard_174 25, copy_source_link 3, live_server 22; `check.py`: OK.

## Risks

- **MEDIUM (design choice): the earlier draft leaves Review during the run.** Shown as "Reading the transcript again" on the
  bar only; Review simply doesn't list it for a minute or two. Settled on every end and on the next server start.
- **LOW: a second creaite flow writing the same transcript's proposal during the run** would be taken as the new draft (one run
  at a time makes this a hand-run `minutes.py stage` from Terminal only).
- **LOW: the record's version list** is per stored path; the new record never reuses the earlier record's name during the run,
  but a third Read again could reuse the first record's name once it is in the hold, and its version list would show the first
  record's old backups. Cosmetic; the content is right.
- **LOW: a transcript steering the spec** (project, items, updates to existing items) is as for Process: everything waits in
  Review; the date, title and projects are given in the message.
- **INFO: Undo is not in Activity's undo list** (it is the toast's, and `POST /api/minutes/reextract/undo` by run ID). Holds
  are kept (newest 20), so a later Undo by hand is possible.
- **INFO: live_server.diff without reach.diff** starts the run under a plain chat's hook rules for an unknown mode: no record
  command, no write outside drafts, but `minutes.py stage` of any spec and the home folder readable. Apply both together
  (README).

## Size

Built: `reextract.py` (~590 lines), the page (MinutesView.jsx, intakeApi.js, UsagePanel, style), the usage kind, one skill line,
tests (~560 lines + 1 Chrome test). Guarded: reach.diff (+42/−13), live_server.diff (+104/−6). Review and apply: about half a
day for the independent security review on the pattern of #264 round 2; no schema or rules change.

## Open decisions for Alan

1. **Release:** ship in 2.6.1 (needs the two guarded diffs applied after review), or keep #268's "opens ask creaite" until then?
2. **What is carried:** only the Track choices (and removed rows as crosses), as built; text edits are set aside (Undo brings
   them back). Or should Read again be refused once he has edited the text?
3. **The earlier draft out of Review during the run** (as built), or kept visible and greyed (needs a Review change)?
4. **The search summary:** kept as first written (as built: enrich refused). Or let Read again replace it?
5. **Review's Approve of a minutes draft** (Natasha's trap on #264): already settled by #275 (the server honours the Track
   column everywhere); nothing more here.
