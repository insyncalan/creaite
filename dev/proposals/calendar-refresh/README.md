# Proposal #265: Calendar import's Refresh as its own run kind (a guarded-file change: Alan's to approve)

**This is a proposal, not an edit.** `system/scripts/live_server.py` and `system/scripts/reach.py` are guarded files: nothing on
this branch changes them. The two diffs here do, once Alan (or Jarvis, on his say) applies them. They are made against
`origin/v253-release` 3d6922dc, which already holds #264's guarded diffs and its R1. Everything else for #265 (the dashboard,
`calendar_refresh.py`, the usage kind, the `sweep.py` and `transcripts.py` fixes, the tests) is on the branch
`v253-calendar-refresh-2` and does nothing harmful without the diffs: Refresh then says it couldn't start (the route isn't
there), and the tests that need the diffs are expected failures.

**Closing #265 needs one decision from Alan: Today's Sweep button.** It stays as it is (BL-295's catch-up sweep, which also
reads the calendar) and is out of this change; #265 stays open for that decision.

## Apply, check, undo

From the repo root (#264's diffs are already in the release):

```
git apply --check dev/proposals/calendar-refresh/reach.diff dev/proposals/calendar-refresh/live_server.diff
git apply dev/proposals/calendar-refresh/reach.diff dev/proposals/calendar-refresh/live_server.diff
```

Checked on `origin/v253-release` 3d6922dc: `git apply --check` is clean, the result is byte for byte the tested copy, and
`git apply -R --check` is clean too. Undo: `git apply -R` with the same two files.

**Optional third diff, `strict-mcp.diff` (review L6; Jarvis asked for `--strict-mcp-config` on this kind).** It adds
`--strict-mcp-config` to `KIND_ARGS["calendar"]`, on top of `live_server.diff` (`git apply --check` clean there). It is kept
separate on purpose: the CLI's own help says the flag means "only use MCP servers from --mcp-config, ignoring all other MCP
configurations", and this repo's comments (Process, Search, edit-ai) treat it as "no MCP server at all". The calendar refresh
needs the Microsoft 365 connector, so with this flag it would most likely read nothing and save nothing. **Probe it before
applying it** (start a `claude -p --strict-mcp-config --output-format stream-json --verbose` run and check that the init event
still lists `mcp__claude_ai_Microsoft_365__outlook_calendar_search`). Without it the run is still fenced from the other
connectors: `live_server.diff` now denies them by name (`permissions.run_deny_extras()`: the other connectors as whole servers,
and the acting and writing built-ins), the allow list names only the two calendar tools, and the hook refuses any other tool.

Verify after applying (one at a time):

```
python3 dev/tests/test_calendar_refresh.py       # 12 tests: helpers, the guard mode, the route (all pass, none expected to fail)
python3 dev/tests/test_calendar_refresh_ui.py    # 1 test in Chrome: Refresh, and the meetings appear
python3 dev/tests/test_meetings.py               # Refresh calls the route, with progress and Stop on the button
python3 dev/tests/test_intake_process.py         # #264 unchanged
python3 dev/tools/check.py                       # check: OK
```

## What Alan will notice (plain words)

- **Refresh just refreshes.** Pressing Refresh in Intake's Calendar import (or Refresh calendar on Today) reads the calendar and
  the meetings appear. ask creaite doesn't open and nothing is said in it.
- **Progress and Stop are on the button.** The "Calendar read" line says "Refreshing… Reading the calendar" while it runs, and
  the Refresh button says **Stop**. At the end one line says what was saved ("Calendar saved: 9 meetings over 6 days.").
- It is counted in Activity › Usage as its own kind, **Calendar refresh** (counts only).
- Typing "refresh calendar" in ask creaite, and Today's Sweep, are unchanged (BL-309's sweep, BL-295's catch-up). Today's Sweep
  button is still #265-open: Alan decides whether it keeps the catch-up sweep or gets the plain refresh.
- **Stop after the save says it was saved** ("Stopped after the calendar was saved: 9 meetings over 6 days."), never "nothing
  was saved"; Stop before it says "Stopped: the calendar was not saved. Press Refresh to start again."
- **An empty reply never wipes the calendar.** If the run's spec holds no meetings at all and the saved calendar still has
  meetings today or later, the save is refused: "The reply held no meetings; kept the saved calendar." An empty week with
  nothing ahead saved is saved as it is.

## The contract

`POST /api/calendar/refresh`, token-checked like every route (header `X-Creaite-Token`, a local Host), and refused (403) with
another site's `Origin` or `Sec-Fetch-Site: cross-site`. Body: `{"run": "<id, optional>"}`. Nothing else in the body is read:
the run's message is `calendar_refresh.build_prompt()`, fixed. `400 {"ok": false, "message"}` in the development repository or
when the calendar source is off (Settings › Sweep › Sources); `409 {"busy": true}` while a run is going or a sweep holds its lock.

The answer is the run engine's event stream (`step`, `closure`, `done`, `stopped`, `error`...), with one extra event before the
closure: `{"type": "calendar", "saved": bool, "meetings": n, "days": n, "transcripts": bool}` (counts only). Stop is
`POST /api/ask/stop {"run": "<id>"}`, as for every run.

## What changes, file by file

**`reach.py` (the guard hook):** a new mode, `"calendar"`, tighter than the sweep mode:
- **Tools** (`calendar_tool_problem`): only Read, Bash, Write, Edit, ToolSearch, `outlook_calendar_search` and `read_resource`.
  No Grep, Glob, Skill, MultiEdit, web, other Microsoft 365 tool, other connector or subagent.
- **Reads:** only the cx-sweep skill's folder and its own two input files.
- **Writes** (direct): only `system/staging/drafts/calendar.json` and `system/staging/drafts/transcripts.json`, never a link,
  never a file with a second hard link, never through a drafts folder that is a link.
- **Commands** (`calendar_gate`): exactly one of `sweep.py calendar-window`, `calendar system/staging/drafts/calendar.json`,
  `transcripts todo`, `transcripts show`, `transcripts record system/staging/drafts/transcripts.json` (as `system/scripts/run …`
  or `python3 system/scripts/…`). Everything else is refused, read commands included, failing closed.
- Every check a plain chat already has still runs too (the never list, one creaite script on its own, no shell characters,
  reports), and the confidential-note check (`--held 1`).

**`live_server.py`:**
- The route `POST /api/calendar/refresh` (above), started under `START_LOCK`, so two clicks never start two runs.
- The run kind `"calendar"`: guarded (the hook above, `--held 1`), its own allow list (Read, the two calendar tools, the five
  commands, the two files), a deny list beside the hook (the web, every other Microsoft 365 reading tool, tracker.py, review.py,
  propose.py, minutes.py, filechange.py, report.py and the rest, sweep.py stage, lock, unlock, done, fail, vip, ignore,
  expected, done-candidates), `--tools Read,Bash,Write,Edit,ToolSearch`, no `--add-dir` (no project or home folder), its own
  system prompt.
- Shown plainly (BL-326: the ask "Refresh the calendar", the steps, one closure line), never as a chat; its reply never offers a
  card, and (new here, for #264's Process too) never a permission offer: a `PERMISSION:` line is ignored for these kinds.
- `USAGE_KIND["calendar"]`, `PLAIN_ASK["calendar"]`. The route sits in #264's route table (no new branch in `do_POST`), and the
  permission check moved into `_rule_item`, so neither function grows past check.py's limit.

**`sweep.py` and `transcripts.py` (not guarded; on the branch):**
- `sweep.py calendar` writes `calendar.json` atomically (`paths.write_text_atomic`: a new file and a rename).
- It refuses a spec with no meetings when the saved calendar holds meetings today or later (above).
- A confidential meeting keeps only its ID, title and times: no place, organiser, organiser's address, recurrence, Teams flag,
  body, attendees or attachments (BL-98's rule, now enforced in the save rather than relying on the model).
- An invite's body loses every line with a link that carries a key (`pwd=`, `passcode=`, `pin=`, `tk=`, `token=`, any
  provider) and every PIN or passcode line ("PIN 4321", "Conference PIN: …", "Passcode: …").
- `transcripts record` checks each fact: only the keys `id, online, uri, count, error, start, end, thread` (a body or a
  passcode field refuses it), an ID, `online` true or false, `uri` and `thread` short strings with no spaces or key, `count` a
  whole number or null, `error` one of permission, notfound, other. A refused fact is named under `"refused"` and not kept.
- Not done: no subject or body marker ("Confidential", "Restricted") is read as confidential; the existing code has no such
  rule for meetings, so only Outlook's own sensitivity counts.

**Not changed:** `permissions.py`, `filechange.py`, `tracker.py`, `schema.sql`, `client_leak.py`, the settings files, the rules,
the cx-sweep skill.

## What the run can write

Only through the sweep's own commands and its two input files: `system/staging/calendar.json` (`sweep.py calendar`, which also
deletes its input file, adds the ignore rules' counts to `system/staging/sweep-ignored.json` and rebuilds the dashboard),
`system/staging/transcripts.json` (`transcripts todo` and `record`), the two files in drafts and the debug log. No proposal, no
tracker row, no project or Intake file, no settings.

## Adversarial review of the diff (trying to make the run write or stage anything beyond calendar.json)

Fixed in the diffs (each has a test):
1. **A hard link in drafts.** `transcripts.json` hard-linked to a project file passed the path check (its real path is the
   draft's), so a Write would have changed the project file. Refused now (`st_nlink > 1`), and so is the command on it.
2. **A permission offer.** A `PERMISSION:` line in the reply still emitted a `permission` event (information only) for a kind
   with no card. Now no permission handling at all for these kinds.
3. **The sweep's other commands.** The sweep mode allows `sweep.py stage`, `lock`, `done` and `vip record`; this mode allows
   none of them (only the five calendar commands, exact words).
4. **The other Microsoft 365 tools.** The sweep mode reaches mail, Teams and SharePoint; this one only the two calendar calls,
   refused in the hook as well as denied by name.
5. **Words from the request.** The body's text is never read; a forged `message`, `kind` or `mode` in an ordinary ask message,
   or the refresh's own prompt typed in, stays a plain unconfirmed chat (tested).
6. **Another site.** The route also refuses another site's Origin and a cross-site fetch (403), beside the token and the Host.
7. **A run beside a sweep.** Refused (409) while a sweep holds its lock, so the two never both save the calendar.

The independent review (verdict READY with notes) and what was done, each with a test that failed first:
- **L1** the sweep-lock 409 had no test: `test_3b_not_while_a_sweep_holds_its_lock` (fails with the branch taken out).
- **L2** the drafts-folder-is-a-link check had no test: `test_a_drafts_folder_that_is_a_link_is_refused` builds a vault whose
  drafts folder links elsewhere; writes, reads and both commands are refused (all five fail with the check taken out).
- **L3** atomic save (`test_the_save_is_atomic`) and the Stop line (`test_the_stop_line_says_whether_the_calendar_was_saved`,
  and through the server `test_3c_stop_after_the_save_says_it_was_saved`: Run's `lines["stopped"]` may now be a function of the
  run, used only by this kind).
- **L4** `test_an_empty_reply_keeps_a_saved_calendar_with_meetings_ahead` (and its pair, which saves an empty week).
- **L5** `test_a_confidential_meeting_keeps_only_its_title_and_times`, `test_keyed_links_and_pin_lines_never_reach_a_saved_body`,
  `test_transcripts_record_keeps_only_well_formed_facts`.
- **L6** `reach.CALENDAR_M365` is built from `permissions.M365`; the deny list adds `run_deny_extras()` (asserted in test 1);
  `--strict-mcp-config` is the optional `strict-mcp.diff` (above).
- **L7** this README: closing #265 needs Alan's decision on Today's Sweep button.

Residual (not fixed, small, for the record):
- **`read_resource` reads any resource it is given a URI for** (mail and chats too, not only events and transcripts). The calendar
  steps need it, and the hook can't tell an event's URI from a message's without a list of URI shapes nobody has written down.
  What it reads can only go into the run's own two input files, and from there only the fields `sweep.py calendar` keeps
  (a meeting's body for Prep, up to 20,000 characters, on the laptop), never out of the laptop. The sweep mode has the same.
- **An invite's text can steer the model** inside the fence: wrong meetings in calendar.json at worst, which the next refresh
  replaces.
- **The ignore counts carry over.** Without a `done` step (as with a typed "refresh calendar" today), the counts `sweep.py
  calendar` adds to `sweep-ignored.json` appear in the next sweep's summary.
- **A sweep from Alan's own Claude Code session that starts after the refresh** isn't stopped; the later save wins, as today.
- **Check-then-use on the input files.** The hook checks the file when the call is made; changing it between the check and the
  command would need a second writer running at that moment.

## Tests (fail-first evidence)

On the branch, without the diffs: `python3 dev/tests/test_calendar_refresh.py` gives `OK (expected failures=8)`: the fence's
refusals (two) and the six route tests. `dev/tests/test_calendar_refresh_ui.py` is an expected failure. The helper tests failed
before `calendar_refresh.py` and the usage kind existed (`ModuleNotFoundError`, `'calendar' not found in KINDS`), and
`test_meetings`' new Refresh assertions failed on the old page (Refresh went to `askLive`).

With the diffs applied (on `origin/v253-release` 3d6922dc): `test_calendar_refresh.py` gives `OK` (22, none expected to fail), `test_calendar_refresh_ui.py` `OK`, and `test_intake_process`, `test_panel_sweep`, `test_run_usage`,
`test_record_commands`, `test_draft_writes`, `test_vip_tools_pinned`, `test_guard_174`, `test_ai_117`, `test_run_tools_explicit`
and `test_search_tools_pinned` pass; `check.py` gives `check: OK`. Findings 1 and 2 were shown failing first: with the fixes
taken out, `write_hard_link`, `record_hard_link` and the `permission` event fail.
