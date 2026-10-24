# smoke264: post-release probes for the 2.6.4 items (fixed issues only)

Reusable probes written for the creaite 2.6.4 post-release smoke. Each one proves a 2.6.4 item that is **closed on the board** and
shipped in the published release. They sit beside the earlier upgrade smoke in `../smoke/` (which they reuse; nothing is copied).
Items that are still open are not here (see "Left out").

Written against: **v2.6.4 (29abe51c)**, base **v2.6.3**. Every probe takes the zips and a work folder as arguments; the version
appears only in labels (`--label`, default read from the zip's manifest), never in a check's logic. If a later release rewords a
string a probe matches (the three #345 refusals, the plain-words strings), update the string before reading a FAIL as a regression;
the probe's docstring says which checks are wording-specific.

## Prerequisites

- Python 3.9 or later, standard library only. Run with `python3 -I` (the scripts add their own folder to the path).
- Google Chrome (the page probes drive one headless Chrome through `../smoke/lib/cdp.py`), `lsof`, `sh`.
- Two release zips, **not committed** (no zip is stored here). Fetch them with the GitHub command-line tool, from the public repo:

  ```
  gh release download v2.6.4 --repo OWNER/REPO --pattern 'creaite-*.zip' --dir DIR/dl264 --clobber
  gh release download v2.6.3 --repo OWNER/REPO --pattern 'creaite-*.zip' --dir DIR/dl263 --clobber
  ```

  or download them by hand from the release page. Check the zip against the release's digest if you care which bytes you tested.
- Nothing touches a live vault, Microsoft 365, git or the network. Each probe builds a throwaway vault in its own run folder under
  the work folder, with fictional data only (the greeting name is Sam; people are fictional; mail is `*.example`), points the vault's
  `claude` at a stand-in that only logs a call, and removes the run folder when it ends (`--keep` keeps it for a look).

## Rebuilding the 2.6.3 base

The base is the previous release, rebuilt by every probe on each run: `python3 -I creaite-2.6.3.zip NEWVAULT` makes a vault from the
zip (as a user would), then `../smoke/lib/demo_data.py` loads the repository's fictional demo portfolio (four projects: FAL, ORX, MER, TID) through the vault's own `tracker.py apply`, and the zip under test is installed over it with the vault's own
`update.py inspect` and `install`. To build one by hand: `python3 -I creaite-2.6.3.zip /path/to/scratch-vault`. For a later
release, pass that release's previous zip as the base; the probes need nothing else of the number.

## Usage

```
python3 -I probe_X.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]
sh run-all.sh NEW_ZIP BASE_ZIP WORK_DIR [same options]      # every probe in turn, one at a time, with a summary
```

`--control` skips the install and runs the same checks on the base. The checks that target the fix are then expected to FAIL (that
shows the check discriminates); the output says which. `--help` on any probe prints its docstring without starting anything.
Exit codes: 0 all checks passed (or `--control` finished), 1 a check failed, 2 a harness problem (nothing was proved). The last
line is `RESULT: PASS`, `RESULT: FAIL` or `RESULT: CONTROL DONE`.

Run times on a laptop are between about 10 seconds (`probe_338_rules.py`) and a minute or two for the page probes.

## What each one proves

| Script | Item (closed) | What it proves | Control on 2.6.3 |
|---|---|---|---|
| `probe_338_rules.py` | #338 | `creaite-rules.md` is at most half the base's size (32,736 against 66,315 bytes), `creaite-reference.md` is added and named in the rules, the Non-negotiables section is byte-identical, every "never" sentence of the old rules is still in the rules or the reference (81 of 81 as this script splits sentences), `update.py inspect` lists the reference as added, the updated vault's root `CLAUDE.md` still imports only the rules, a fresh vault from the zip passes doctor (36 passed, 0 failed). | 1 FAIL (the reference file is not in the vault); the zip-only checks pass because they read the new zip |
| `probe_345_expect.py` | #345 | `expect` (the row fingerprint) is required on reject, approve-instead, repeat, retarget, assign and Approve minutes: missing, malformed (`not-a-fingerprint`, short hex, a number) and stale are refused in plain words, the staged file is byte-identical and the tracker counts do not move; a two-row reject with one stale row is all or none; correct fingerprints work (controls); undo of a reject, retarget undo and the assign preview need none; through the open Intake page, Approve on an item changed behind it is turned away. 18 checks. | 12 FAIL (2.6.3 accepts a missing `expect`; later checks cascade because earlier requests were accepted). The one page-level check passes on both |
| `probe_334_budget.py` | #334 | The weekly AI budget is off by default (settings, the zip's defaults, and with $60 used); off holds nothing; on and over budget in confirm mode answers HTTP 429 with `can_continue` true and starts nothing; Run anyway runs; stop mode refuses even Run anyway; a confirmed request, a typed "sweep" and a Review route are never held; 80% warns without holding; the Usage tab and Settings show it (the week's end date is worked out from today); the guard hook refuses Edit/Write of `settings.json` and the usage log and `propose.py setting`, and `filechange.py edit` of `settings.json` from a run needs approval. 17 checks. | 1 FAIL, then the rest are skipped (the base has no budget) |
| `probe_346_runsetup.py` | #346 | A run whose set-up fails leaves no guard record (`system/guard/run.json`) and ends its process, and the next ask is not "busy". Part (a) uses the real server and passes on the base as well; part (b) imports the vault's `live_server.py` in a child process with a stand-in Popen and a run table that refuses entries, and is the check that discriminates. | (b) FAILS: run.json left behind, process not ended |
| `probe_discard_rollback.py` | 2.6.4 Review items | Discard of held minutes sets them aside and writes nothing; Undo restores the file byte for byte; a second Undo, a taken name and a planted file are refused; the route answers only the open page's own call (HTTP 403 otherwise). A failing `item_events` insert makes `tracker.py apply` and `undo` exit 1 and change nothing; with the fault removed they work. 11 checks. | none FAIL: regression checks, the behaviour is in 2.6.3 too |
| `probe_ui_today.py` | #352, #351 (b) | Today has no stale-actions line, no "no update for" text and no Draft updates button; Work's bulk bar still offers Draft updates; a past day shows times, titles and organiser only (no follow-up chips, no Check or Process); a title hover on today opens the Prep peek; a later day lists its meetings; Intake still offers Check and Process. | 2 FAIL (#352 and the past-day chips) |
| `probe_ui_layout.py` | #337 | At 1400 and 900 px: People's Overdue column is on screen with no sideways scroll; Settings tick-row label columns are at least 150 px and on one line, tick labels keep room; Activity's "Rejected in review" is on one line. 10 checks. | 4 FAIL (People at both widths, label column and By column at 900) |
| `probe_ui_profile.py` | #312, #348 | First run shows "About you" with a "Not now" that survives a reload; Settings search finds Your profile; a pipe in the saved name is not stored; three saves of details leave one register row. When the name matches a colleague in the register, the card shows her details as "Not set", the button says "Add my details", pressing it asks "Is that row you?", and her row is unchanged. | 1 FAIL (the colleague's details are shown as yours) |
| `probe_ui_milestones_drawer.py` | milestones wording, #321 | Client view says "The milestone is not shown to the client yet" (one hidden) or "None of the N milestones are shown to the client yet" (several), never "0 achieved, 0 to come"; Internal view still lists them. The note drawer is 440 px by default, 464 / 560 / 536 on Left / Shift+Left / Right, the full width on End, 440 on Enter, widens on a real drag, and Reset width shows only when changed, at 1400 and 900 px. | 2 FAIL (the wording); the drawer arrived in 2.6.2 and passes |
| `probe_ui_words.py` | #292, #293 | A sample of the plain words: Today's "Mail and Teams not checked yet today" with Check now, Settings' "Daily check time", Intake's "suggestion", Help's "creaite folder" and "project record", and the three new health strings in the zip. Prints, for information, where the older words still appear. | 2 FAIL (the two Help phrases) |

The earlier scripts in `../smoke/` still apply to 2.6.4: `sh ../smoke/smoke-261.sh NEW_ZIP --old BASE_ZIP --chain` does the upgrade
chain (inspect, install, migrate, doctor, pages at 1400 and 900 px, undo byte for byte, reinstall, fresh vault), and `smoke_post.py`
and `smoke_intake.py` check first-click Approve and held buttons (`python3 -I ../smoke/smoke_post.py NEW_ZIP BASE_ZIP WORK_DIR`).
Their step labels still say 2.6.0 in places; read the result lines. Both ended `RESULT: PASS` on 2.6.4 against 2.6.3 when run for this folder.

## Expected result on 2.6.4 (29abe51c, against 2.6.3)

Every probe ends `RESULT: PASS` and exits 0, run by `run-all.sh` (see the summary table printed at the end). Counts of checks:
`probe_338_rules` 7, `probe_345_expect` 18, `probe_334_budget` 17, `probe_346_runsetup` 2, `probe_discard_rollback` 11,
`probe_ui_today` 7, `probe_ui_layout` 10, `probe_ui_profile` 8, `probe_ui_milestones_drawer` 5, `probe_ui_words` 8. No product failure was found in
2.6.4 by any of them; the console showed 0 errors on every page probe.

## Stopping a probe's own processes

A probe stops what it started when it ends, and on Ctrl-C (`proc_guard` also runs a watchdog that stops a leftover group if the
probe itself is killed). Each probe prints its own PIDs as it starts a server or a browser:

```
[pToday] live server pid 31664 on http://127.0.0.1:50339
[pToday] Chrome pid 31674 (own process group)
```

If one is left behind (a killed run), stop **only those PIDs**: `kill PID`, then check with `ps -p PID`. Do not use `pkill`
or `killall` on a shared machine. Each is the leader of its own process group, so `kill -- -PID` ends the group (the server and
anything it started, or Chrome and its helpers). The run folder is `WORK_DIR/<name>-<pid of the probe>/`; it carries a
`.smoke-run` marker and may be deleted by hand once nothing uses it (`--keep` leaves it for you).

## Known limits

- Desktop widths 1400 and 900 px only; nothing at 320 px or on a phone.
- A stand-in `claude` and no Microsoft 365: nothing here shows what a real model or a real mailbox does. Run counts (the budget
  probe) are counts of stand-in calls.
- `probe_ui_today.py` builds its calendar from the real today (last weekday before, today, next weekday after) and was only run on
  a Saturday; the day menu and week strip were not exercised on other weekdays. A run in the first minutes of a Monday can
  straddle the budget week's boundary in `probe_334_budget.py` (it works the week's end from today's date).
- Wording-specific checks (#345's three refusals, the plain-words strings, #334's Usage text, the milestones sentences) track 2.6.4's text.
- The Discard / rollback group passes on the base too, so it guards against regression only; the #346 part (a) and a few
  controls inside the other probes do the same, and say so in their output.
- Not covered: #337's pencil colour, 12 px chart text and 24 px targets; the Discard and Undo buttons themselves (the Undo route is
  called from the page with `fetch`); a second open Review tab after a rename; Windows; any live vault; the shared-database work.
- The probes drive pages by element ids and classes of 2.6.4 (`#dayMeets`, `#capDrawer`, `#actTbl`, `#workTbl`, `data-ira`, ...). A
  later page rewrite may break a selector without any product fault; check which before reporting.
- The `.example` addresses and names are fictional. The throwaway vault's `claude` is only a logging stand-in; nothing is sent.

## Left out (and why)

- **Typed chat words** ("check my mail", "check my mail and Teams", "check mail for FAL", "check my mail the last 7 days", and "... and
  apply everything" staying a plain chat): these exercise `panel_sweep` and the chat command words, which #347 (open) changes next
  (guarded, "check my mail", "save", "undo last save"). Kept out until #347 closes. The 2.6.4 smoke saw them start a sweep-mode run.
- **The Help text that still shows the older command words** and the Help line that says past days show follow-up: both are known
  stale lines called out in the 2.6.4 notes ("Not in 2.6.4"), so the probe does not assert them. The residual-word counts in
  `probe_ui_words.py` are printed only.
- **Fetching transcripts as they appear (#250, open)** and anything touching it (the transcript status file is only fixture data
  for the Today page here); none of the working probes exercised it, nothing for it is included.
- **Exploration scripts** (nine small look-around scripts, plus one on the minutes header, where long dates such as "21 October 2026" are
  still shown and "1 turn" has no assertion, so nothing fixed would be proved). They had no assertions.
- **`pages.py`** (every page drawn at 1400 and 900 px with no console errors) and **`chain.py`** (the upgrade chain): `../smoke/smoke-261.sh --chain`
  already does both, so they would duplicate it. The #338 parts of `chain.py` are in `probe_338_rules.py`.
- **`shoot.py`** (Today screenshots): already in `../screens-351/`.
- **Separate 2.6.3 variants** of the probes: replaced by `--control`.
- Nothing from a live vault, no downloaded zip, no screenshot or work file from the smoke run is committed.
