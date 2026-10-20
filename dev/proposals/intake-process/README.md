# Proposal #264: Intake's Process as its own run kind (a guarded-file change: Alan's to approve)

**This is a proposal, not an edit.** `system/scripts/live_server.py` and `system/scripts/reach.py` are guarded files: nothing on
this branch changes them. The two diffs here do, once Alan (or Jarvis, on his say) applies them. Everything else for #264 (the
dashboard, the plain-code helpers, the tests) is already on the branch `v253-intake-process` and does nothing harmful without the
diffs: Process then says it couldn't start (the route isn't there), and the tests that need the diffs are expected failures.

## Apply, check, undo

From the repo root:

```
git apply --check dev/proposals/intake-process/reach.diff dev/proposals/intake-process/live_server.diff
git apply dev/proposals/intake-process/reach.diff dev/proposals/intake-process/live_server.diff
```

Checked against `origin/v253-release` de0de94e and its newer tip df417f7d (20-10-2026): `git apply --check` is clean for both, in either order. Undo:
`git apply -R` with the same two files (or `git checkout -- system/scripts/live_server.py system/scripts/reach.py` before committing).

Verify after applying (one at a time; each takes minutes on a loaded machine):

```
python3 dev/tests/test_intake_process.py         # 25 tests: helpers, the guard mode, the route (all pass, none expected to fail)
python3 dev/tests/test_intake_process_ui.py      # 2 tests in Chrome: Process on the 3 sample files; a question on its row
python3 dev/tests/test_transcripts_ui.py         # the meetings' Process selected goes through the same route
python3 dev/tools/check.py                       # check: OK
```

## What Alan will notice (plain words)

- **Pressing Process stages the files.** The three sample files (two transcripts and Lena Park's minutes) go to Review as drafts with
  their proposed items, and the rows say "Draft ready — in Review". No "I've drafted them but haven't staged them", no go-ahead to
  type, and ask creaite doesn't open.
- **Progress and Stop are on the row** ("Processing… Reading the minutes", and a Stop link). The run is counted in Activity › Usage
  as its own kind, "Intake processing" (counts only).
- **A question goes on the row.** If the run can't finish a file without Alan (which project, not a meeting), that row says
  **Needs you** with the question, and **Ask creaite about this** opens ask creaite with the question typed in, for Alan to send or
  change. Nothing opens or is sent by itself.
- The meetings' **Process selected** (Calendar import) uses the same route for the transcript it loaded.

## The contract (for #232's Intake page, which calls the same route)

`POST /api/intake/process`, token-checked like every route (header `X-Creaite-Token`), body:

```
{"files": [{"path": "inbox/<name>", "project": "ABC"}, ...], "run": "<id, optional>"}
```

`project` is optional (a code in the tracker's projects table, or `_portfolio` for the portfolio); the page sends it only when
Alan chose it (Calendar import's picker, or remembered for the series), never a match from the title. A plain list of path strings
is accepted too. The server, never the model, checks each path (`intake_process.validate_request`): directly in `inbox/`, a plain
file (no link, no second hard link, not hidden), `.vtt .docx .txt .md .pdf`, 1 byte to 25 MB, named exactly as Intake lists it,
a name `minutes.stem` can give (so "Jane’s check-in" and "Q4 – kickoff!" are fine; no control, bidi/format or line-separator
character, back-quote, colon, path separator or `* ? " < > |`), each once ignoring case and Unicode form, at most 20, and none
already waiting in Review. A refusal is `400 {"ok": false, "message": "<path>: <why>"}`; a run already going is `409 {"busy": true}`.

The answer is the run engine's event stream (`data: {...}` lines: `step`, `closure`, `done`, `stopped`, `error`...), with one
extra event before the closure:

```
{"type": "intake", "files": [{"path": "inbox/...", "state": "staged" | "needs" | "not_staged", "question": "..."}],
 "staged": 2, "needs": 1}
```

`question` is the run's own short sentence about one of its files (one line, at most 300 characters, only for a file it was
given), never the file's text. Stop is `POST /api/ask/stop {"run": "<id>"}`, as for every run.

## What changes, file by file

**`reach.py` (the guard hook):** a new mode, `"process"`.
- `start_run` keeps the run's checked Intake files in `system/guard/run.json` (only the server writes it; the folder is on the
  never list).
- In mode `"process"` a creaite script runs only if it is a read command (`SCRIPT_COMMANDS`, minus the "read" ones that delete or
  write their input) or one of Process's four steps: `minutes.py stage <a .json directly in drafts whose "transcript" is one of the
  run's files>` (no quick note; a Word `"draft"` only from drafts), `propose.py people map <its own draft>`, `docx_tools.py fill
  system/templates/minutes-template.docx <values in drafts> <.docx in drafts>`, and `search.py enrich set`. Everything else is
  refused, failing closed (anything unknown is refused).
- A direct Write or Edit in this mode may only create a `.json` directly in `system/staging/drafts/`, or change one this run wrote.
- "This run's" file, everywhere in the mode: one that didn't exist, or was last written after the run started (`_older_than_run`,
  from `started` in `run.json`; fails closed). So `fill` writes only a new `.docx` from the run's own values file (which `fill`
  deletes) with no pictures; a spec's Word `"draft"` is one this run filled; `people map` maps only the run's own spec; `tracker.py
  validate` (it writes its findings into the file) runs only on a proposal this run staged; and `search.py enrich set` takes only
  `--path`/`--summary`/`--tags`, each path the `to` of a copy in a proposal this run staged, never one that already has a summary.
- Every check a plain chat already has still runs first (one script on its own, no shell characters, the never list, reports).

**`live_server.py`:**
- The route `POST /api/intake/process` (above), started under `START_LOCK` so two clicks never start two runs.
- The run kind `"process"`: guarded (the hook above, plus `--held 1`, so a confidential note is never read), its own allow list
  (the read tools without Microsoft 365, the four steps, writes in drafts), a deny list beside the hook (apply, undo, approve,
  reject, bulk, `propose.py stage`, `filechange.py`, `minutes.py refresh`, the web and Microsoft 365), `--strict-mcp-config` (no MCP
  server at all), `--add-dir` for the projects folder only (not the home folder), and its own system prompt.
- It is shown plainly (BL-326: the ask "Process 3 Intake files", the steps, one closure line), never as a chat, and its reply never
  offers a card (no CONFIRM, CHANGE, EDIT or permission card).
- `USAGE_KIND["process"]`, `PLAIN_ASK["process"]`.

**Not changed:** `permissions.py`, `filechange.py`, `tracker.py`, `schema.sql`, `client_leak.py`, the settings files, the rules.

## What stays safe

- Process can only **stage** proposals for the files Alan ticked. Staging is not the record: every item is `pending` until Alan
  approves it in Review, and the hook refuses `tracker.py apply`, `undo`, `review.py approve`, `reject` and `bulk` in this run.
- It can't change, move or delete any file outside its own `.json` inputs in drafts (no `filechange.py`, no direct writes elsewhere);
  the Intake files themselves are moved only when Alan approves the minutes, by `tracker.py apply`, as today.
- It never reaches Microsoft 365 or the web, and never the home folder's files.
- The server decides what Process is, from its own route and its own checks of the paths. A message to ask creaite that says
  "process", carries `kind: process` or copies the Process prompt is still an ordinary, unconfirmed chat (tested).

## What ask creaite still cannot do

Nothing about ask creaite changes. A chat still can't stage minutes proposals or map names without Alan's CONFIRM, can't apply, and
can't call the Process route (it has no network tool; the route needs the page's token). The new mode is used only by the run the
route starts.

## Today's path was over-privileged (found while building this)

Today `processInbox` sends `askLive("process …", "Process … into draft minutes and proposed items")`: the second argument is the
`confirmed` title, so today's Process is a **confirmed** ask creaite run, with the confirmed tools (`tracker.py apply`, `undo`,
`review.py *`, `filechange.py *`, writes anywhere in staging) and the BL-306 auto-apply of anything `propose.py` stages. The model's
reply then asked for a go-ahead anyway (the prompt it gets says proposals from meetings need a CONFIRM). This proposal replaces that
path with a run that has far less.

## Adversarial review of the diff (trying to make the route confirm more than staging Intake files)

Fixed in the diffs:
1. **A spec staging another file.** `minutes.py stage` is allowed in a plain chat today for any spec. In mode `"process"` the spec's
   `"transcript"` must be one of the run's files exactly, and a quick note (`"note"`, filed as approved) is refused.
2. **A Word draft from anywhere.** A spec's `"draft"` is copied into the project's minutes folder on approval; a draft outside drafts
   (a project document, a file in the home folder) would be filed as minutes. Refused in this mode: only a `.docx` in drafts.
3. **Overwriting another flow's draft.** A plain chat may write anything in drafts, including another meeting's minutes waiting in
   Review (`.html`/`.docx`), a note's draft or a sweep's input. A Process run may only create `.json` files there, or change its own.
4. **Two runs at once.** The busy check and the start are under `START_LOCK`, so a double click can't start a second run whose file
   list would replace the first's in `run.json`.
5. **A card from the reply.** A Process run's reply never offers a CONFIRM, CHANGE, EDIT or permission card, so nothing staged by it
   can be turned into a record change from its own words.
6. **A guessed project presented as Alan's.** The page sends no project for an uploaded file (Intake's "likely project" is a guess);
   the prompt says "as set in Intake" for a project the page does send (a meeting row's picker).
7. **Odd names in the prompt.** A path with a line break, back-quote, colon, a bidi or other format character, a line separator or
   any character a file name can't hold is refused by the route; the prompt numbers the files and gives each path as a JSON string
   after `path: `, and says a name is only a name. A file name can't add a `QUESTION:` line or a new instruction line.

## Independent review (20-10-2026: READY WITH NOTES) and how each finding was fixed

The review's probe (`attack264.py`) and mutants (`mutate264.py`, `mutate264b.py`) were re-run against a scratch tree of
`origin/v253-release` with this branch merged and both diffs applied.

| Finding | Fix | Test (`dev/tests/test_intake_process.py`) |
|---|---|---|
| **M1** (medium): `docx_tools.py fill` could write over another flow's Word draft in drafts (a steerco one-pager, an ad hoc document, Word minutes awaiting approval), and a spec's `"draft"` could name one, to be filed as these minutes | `fill` only into a `.docx` that is new or this run's, from this run's own values file; a spec's `"draft"` only one this run made (`reach.py` `_process_fill_problem`, `_process_stage_problem`) | `Fence.test_it_never_writes_over_another_flows_draft_or_summary` (fill over the one-pager, from an older values file, a spec naming the one-pager); `test_it_may_read_draft_and_stage_its_own_files` (its own new draft still stages) |
| **M2** (medium): `search.py enrich set --path <any path>` could replace any file's summary (a client report, another project's minutes) | Only `--path`, `--summary` and `--tags`; each path the `to` of a `copy` in a proposal this run staged, and never one that already had a summary before the run (`_process_enrich_problem`) | same test: a client report, another project's path, a path with an older summary, a mix, another option; its own copy allowed |
| **F1** (regression): Calendar import's Process selected sent `_portfolio`, refused as a code; a loaded transcript's name (`minutes.stem`: – ’ ! # @ ; = $) was refused with "rename it" | `_portfolio` accepted (prompt: "the portfolio, _portfolio, as set in Intake"); names checked by what `minutes.stem` can give, refusing only control, format, separator, surrogate/private/unassigned characters, back-quote, colon, path separators and `* ? " < > \|`; the prompt quotes each path as JSON in a numbered list | `Helpers.test_a_loaded_transcripts_name_is_an_intake_name`, `test_the_portfolio_is_a_project_alan_can_choose`, `test_the_prompt_is_fixed_and_lists_the_files`; `test_transcripts_ui.py` (the loaded file in the prompt) |
| **S6**: the page sent a guessed project (matched from the title, or the portfolio guess) as if Alan chose it | `intake.js` `mtgProcessFile`: the project goes only when `how` is `"remembered"` (the picker sets it too) | `test_meetings.py` (a matched ABC meeting goes without a project; the five cases of `mtgProcessFile`) |
| LOW: a spec whose `"transcript"` is a list crashed the check (TypeError; the hook failed closed) | a plain refusal | `Fence.test_a_spec_whose_transcript_is_a_list_is_refused_plainly` |
| LOW: bidi and format characters in a question or a name | stripped from the question (`intake_process.plain`); refused in a name | `test_questions_are_only_for_the_runs_own_files_one_line`, the F1 test |
| LOW: two names for one file on APFS (case, Unicode form) | duplicates compared case-folded in NFC; a name must be exactly as Intake lists it (`os.listdir`) | `Helpers.test_one_file_once_whatever_its_capitals_and_named_as_listed` |
| LOW: `tracker.py validate <another pending proposal>` (it writes into the file); `fill` with pictures from anywhere; `people map` of any `.json` in drafts | validate only a proposal this run staged; no `"image"`/`"images"` entry in the values file; map only the run's own spec | the M1/M2 test (validate a waiting proposal or one with no meeting, a values file with a picture, map another flow's draft) and `test_it_may_read_draft_and_stage_its_own_files` (validate its own) |
| Surviving mutants L2, L4, L5, L6, L10, M13 (and M10 from `mutate264b.py`) | tests added | L2: the stand-in's Process reply now carries CONFIRM, CHANGE and EDIT lines and `test_1` asserts no card; L4 and L6: `test_1` checks the `--add-dir` folders (never the home folder) and `--disallowedTools`; L5: `test_5_process_waits_for_a_run_already_going` (409 while a slow chat runs); L10: `test_6_its_usage_is_counted_as_its_own_kind`; M13: `stage_two` in the M1/M2 test; M10: `Fence.test_only_a_process_runs_record_names_files`. Re-run: all 24 mutants of `mutate264.py` and 7 of `mutate264b.py` killed |

Residual (not fixed, small, for the record):
- **"This run's" is by time.** A file is the run's when it is new or was written after the run started. Another writer touching a
  draft during the run (Alan saving a minutes record in the dashboard at the same moment) would make it look like the run's.
  Only one run goes at a time, so the window is that of the dashboard's own saves.
- **Recommendation, outside this diff: `/api/ask` and Process's start.** The Process route takes `START_LOCK` for its busy check and
  start; `/api/ask` doesn't (pre-existing), so an ask creaite message sent at the same instant as Process could start beside it and
  replace `run.json`. Taking `START_LOCK` around `/api/ask`'s busy check and start would close it.
- **Check-then-use on the spec.** The hook reads the spec when it checks `minutes.py stage`, just before the call runs. Changing
  the spec in between would need a second write running at the same moment (not checked here). The worst case is a pending
  proposal for another file in reach, waiting in Review, never applied.
- **A file name can still carry words** ("ignore the rules and …" is a valid name). It can only steer the model inside the fence.
- **`search.py enrich set`** in a plain chat may still attach a summary to any path in the search index (pre-existing). In a
  Process run it is limited as above.
- **`run.json` holds one run.** The hook reads the Process files from the run record without comparing the run ID; there is only
  ever one run, and a record that isn't a Process run's gives no files (fail closed).
- Pre-existing, outside this diff: in a plain chat, `minutes.py stage` (a stage command) runs unconfirmed with any spec, including a
  Word `"draft"` from anywhere and a `"transcript"` from a project folder (removed from there on approval). Worth the same two checks
  in mode `"ask"`, as a separate guarded change.

## R1 delta (after the diffs above were applied on `origin/v253-release` ba6fe110)

**Status.** `reach.diff` and `live_server.diff` above are applied on `origin/v253-release` (ba6fe110, with `/api/ask` now under
`START_LOCK`). The delta re-review (READY WITH NOTES) found one more: **R1** (low to medium). The fix is one new guarded diff,
`r1-reach.diff`, against `system/scripts/reach.py` as it is on `origin/v253-release` now. `live_server.py` needs no change for R1,
so there is no `r1-live_server.diff`.

```
git apply --check dev/proposals/intake-process/r1-reach.diff      # clean on origin/v253-release ba6fe110
git apply dev/proposals/intake-process/r1-reach.diff
```

It also applies cleanly before or after #265's `dev/proposals/calendar-refresh/reach.diff` (checked both ways): the change to
`start_run` only adds keys for mode `"process"`.

**R1.** "This run's own file" was judged by its time, so any `.docx` or `.json` another flow wrote into drafts *during* a Process run
counted as the run's. Repro: start the run, write `drafts/2026-10-20 ABC Client report.docx` and a spec with that `"draft"`, and
`minutes.py stage` was allowed (the client report export would be filed as these minutes on approval); a minutes record exported
to Word could be filled over; the export's temporary `<stamp> values.json` could be edited.

**Fix: by the run's record, never by time.**
- `start_run` writes, for mode `"process"`, `"before"` (the proposals in staging when the run starts) and `"made"` (empty) into
  `system/guard/run.json`.
- The hook records each file it lets the run create in `"made"` (`_may_make`: a file that doesn't exist yet, claimed as it is
  allowed; or one already in `"made"`). That covers a direct Write of a new `.json` in drafts, a `fill` target and a search summary.
- "The run's own" (`_runs_own`) is only what `"made"` lists. A `fill` reads only a values file the run made; a spec's Word
  `"draft"` must be one it made, and never a report (`is_report_file`); `people map` maps only its own spec; a Write changes only a
  file it made.
- The run's proposals (`_runs_proposals`, for `validate` and `enrich`) are those not in `"before"` and for one of its files: so a
  proposal Alan changes in Review during the run, or a new one he makes for another file, is never the run's.
- Fails closed: a record that isn't a Process run's makes nothing the run's (even if it lists files); a record that can't be
  written means a new file can't be claimed, so it is refused; a record without `"before"` gives no proposals.

**Tests** (`dev/tests/test_intake_process.py`; `needs_r1`: expected failures until `r1-reach.diff` is applied, and on this branch):
- `Fence.test_r1_a_file_another_flow_writes_during_the_run_is_never_the_runs`: the review's repro (a client report export named as
  the draft), a minutes export named as the draft or filled over, a fill into a new report-named file, the export's values file
  filled from, edited or mapped; and its own report-named file as a draft.
- `Fence.test_r1_what_the_run_creates_becomes_its_own`: a fill's new target is recorded, so its spec stages; a new `.json` too.
- `Fence.test_r1_nothing_is_the_runs_without_a_process_record_or_when_it_cant_be_told` (N11, N10, and a record without "before").
- `Fence.test_a_proposal_alan_makes_during_the_run_isnt_the_runs` (N12; it passes on the applied diffs too, so it is `needs_diff`).

**Mutants.** The review's N10, N11 and N12 targeted the time-based helper (`_older_than_run`), which R1 removes; their equivalents in
the new code, with the rest of the delta's branches, are in `scratchpad/mutate264r1.py` (15 mutants): 14 killed. The survivor, a
`fill` into a report-named file without the `is_report_file` check, is equivalent: the hook's report rule (v2.5.1) refuses any
command naming a report file first, so the extra check is belt and braces. The review's `mutate264d.py` against the same tree: every
mutant whose code is still there is killed except M4 (a spec's `"draft"` outside drafts), now equivalent: such a draft is never one
the run made, so the R1 check refuses it; its N1, N2, N4, N6, N9, N10, N11 and N13 target the removed time-based code (pattern not
found).

**Residual.** A file the run is allowed to create is claimed when the hook allows the call, before the tool runs; a call that then
fails leaves a claim for a file that doesn't exist, which only lets the run create that same name later.

## Audit: other dashboard buttons that send an ask message for a routine job

`askLive(` callers in `system/templates/dashboard/src/`:
- `intake.js` processInbox (Upload files › Process): **moved** to the route (this proposal).
- `intake.js` processMeetings (Calendar import › Process selected, after the load): **moved** to the route.
- `intake.js` refreshCalendar (Calendar import › Refresh): still `askLive("refresh calendar", "Refresh the calendar for Intake and
  Today")`. Its second argument is a `confirmed` title too, so it runs as a confirmed chat (apply allowed), and because it is
  confirmed BL-309's sweep recogniser never sees it. Recommended next: a direct job like the catch-up sweep, or at least
  `askLive("refresh calendar", null)` so it runs under the sweep mode (stage only). Not changed here.
- `ask.js` the panel's own send and the confirm card's Go ahead: Alan's own chat, as designed.

## Tests (fail-first evidence)

On the branch, without the diffs: `python3 dev/tests/test_intake_process.py` → `OK (expected failures=11)`; the 11 are the route
(Process on the three sample files ends in Review with no go-ahead; a question on its row; refusals; one run at a time; the usage
kind) and the mode-only fence checks (one: a run record that isn't a Process run's names no files, mutant M10).
`dev/tests/test_intake_process_ui.py` (2) and two tests in `test_transcripts_ui.py` are expected failures too.

With the diffs applied (a scratch worktree of `origin/v253-release` with this branch merged, `git apply` of both files):
`test_intake_process.py` → `OK` (25, no expected failures), and the related suites listed in the report pass.

Security tests in `test_intake_process.py`: a path outside Intake, `..`, a subfolder, a link, a second hard link, a 21st file, a
type Intake doesn't take, a hidden or empty file, odd characters; a forged `kind`/`files`/`mode` marker in an ordinary ask message
and a model-worded "Process these Intake files…" stay a plain unconfirmed chat (mode `ask`); in mode `"process"`: `tracker.py apply`
and `undo`, `review.py approve`, `reject` and `bulk`, `propose.py stage`, `filechange.py`, `sweep.py stage`, `minutes.py refresh` and
`carry`, `report.py`, a derived command, a spec for another file or a note or with a Word draft outside drafts, a write outside drafts,
an `.html` write or a change to an older draft are refused, and the real hook in the real run refuses the record (the stand-in
`claude` asks it, as Claude Code does).
