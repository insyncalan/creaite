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

Checked on this branch's base (`origin/v253-release` 0874dff1): `git apply --check` is clean for both, in either order. Undo:
`git apply -R` with the same two files (or `git checkout -- system/scripts/live_server.py system/scripts/reach.py` before committing).

Verify after applying (one at a time; each takes minutes on a loaded machine):

```
python3 dev/tests/test_intake_process.py         # 17 tests: helpers, the guard mode, the route (all pass, none expected to fail)
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

`project` is optional (a code in the tracker's projects table); a plain list of path strings is accepted too. The server, never the
model, checks each path (`intake_process.validate_request`): directly in `inbox/`, a plain file (no link, no second hard link, not
hidden), `.vtt .docx .txt .md .pdf`, 1 byte to 25 MB, a name of the characters an upload gets, each once, at most 20, and none
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
7. **Odd names in the prompt.** A path with a line break, back-quote, colon or any character outside the upload's own set is refused
   by the route, so a file name can't add a `QUESTION:` line or a new instruction line to the prompt.

Residual (not fixed, small, for the record):
- **Check-then-use on the spec.** The hook reads the spec when it checks `minutes.py stage`, just before the call runs. Changing
  the spec in between would need a second write running at the same moment (not checked here). The worst case is a pending
  proposal for another file in reach, waiting in Review, never applied.
- **A file name can still carry words** ("ignore the rules and …" is a valid name). It can only steer the model inside the fence.
- **`search.py enrich set`** may attach a summary to any path in the search index (a plain chat may too). It changes what search
  shows, never a file or the record.
- **`run.json` holds one run.** The hook reads the Process files from the run record without comparing the run ID; there is only
  ever one run, and a record that isn't a Process run's gives no files (fail closed).
- Pre-existing, outside this diff: in a plain chat, `minutes.py stage` (a stage command) runs unconfirmed with any spec, including a
  Word `"draft"` from anywhere and a `"transcript"` from a project folder (removed from there on approval). Worth the same two checks
  in mode `"ask"`, as a separate guarded change.

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

On the branch, without the diffs: `python3 dev/tests/test_intake_process.py` → `OK (expected failures=6)`; the 6 are the route
(Process on the three sample files ends in Review with no go-ahead; a question on its row; refusals) and the mode-only fence checks.
`dev/tests/test_intake_process_ui.py` (2) and two tests in `test_transcripts_ui.py` are expected failures too.

With the diffs applied (a scratch worktree of the branch's HEAD, `git apply` of both files): `test_intake_process.py` → `OK`
(17, no expected failures), and the related suites listed in the report pass.

Security tests in `test_intake_process.py`: a path outside Intake, `..`, a subfolder, a link, a second hard link, a 21st file, a
type Intake doesn't take, a hidden or empty file, odd characters; a forged `kind`/`files`/`mode` marker in an ordinary ask message
and a model-worded "Process these Intake files…" stay a plain unconfirmed chat (mode `ask`); in mode `"process"`: `tracker.py apply`
and `undo`, `review.py approve`, `reject` and `bulk`, `propose.py stage`, `filechange.py`, `sweep.py stage`, `minutes.py refresh` and
`carry`, `report.py`, a derived command, a spec for another file or a note or with a Word draft outside drafts, a write outside drafts,
an `.html` write or a change to an older draft are refused, and the real hook in the real run refuses the record (the stand-in
`claude` asks it, as Claude Code does).
