# #250 Fetch transcripts as they appear: build plan for 2.6.10

Planning note, no code. Written 26-10-2026 on origin/main 286b03c1 (published 2.6.8, which carries #365's frozen diffs). It replaces the older note on `v27-250-plan` (2.7.0), which predates #365/#371 and the 26-10 decisions.

## 1. What #250 delivers

Issue #250 (creaite-plan, split from #181 C2, Alan 19-10-2026): "fetch meeting transcripts as they appear, as a sweep step ... a setting, off by default (`sweep.fetch_transcripts`); skips confidential meetings only; read only, no AI, nothing written to the tracker."

In plain words: with the setting on, a sweep that run from the dashboard (Close the day, a panel sweep) writes each finished Teams meeting's transcript into `inbox/` by itself, so Intake shows it ready and Alan only presses Process. Off, nothing changes. Nothing is extracted, staged or sent to `tracker.db`. It uses only the two reading tools Load already uses (`outlook_calendar_search`, `read_resource`).

Acceptance (from the issue and its reviews, Cap 20-10 to 24-10):
- Switch off by default (`settings.json`, defaults, Advanced > Transcripts; Reset turns it off; only the exact value true turns it on); off = nothing fetched or written.
- A confidential meeting's transcript is never written, in any order of reads, in any spelling of the join URL, when its event is not read in the run, and when a run is stopped, times out or fails (Cap H1/M2, 24-10).
- The transcript text comes from the server's own copy of the tool result, never from Claude's text, never from a file path Claude names; wrong meeting = nothing; `open(..., "x")`, no overwrite, no partial file.
- No script command writes `inbox/`; nothing reaches `tracker.db` or staging; debug log has counts only; no VIP wording.
- Held transcripts show a short reason, never a confidential title (decision 4 below).
- Review: Cap's Full review if back, else a fresh Opus review plus a second hostile run. "If the leak is not closed in time, defer, never ship a known leak" (Alan, 26-10, accepting the six #250 recommendations).

Alan's six answers (26-10-2026, comment on #250), taken as the design: (1) hold source = the saved calendar plus the live event when read; (2) the fetched count as a line after the run; (3) a short reason for held transcripts, no confidential title; (4) over-holds accepted as fail-safe; (5) Cap Full review, else Opus waiver + second hostile run; (6) defer rather than ship a known leak. Every guarded diff still needs his approval of the exact bytes (hash) and a Full review.

## 2. State of the code and what has to move

- **Not on main.** `system/scripts/transcripts.py` on main (689 lines) has Job, `calendar_rows`, `todo`, `record`, and #365's `take_event`/`diagnosis`/`no_event`. The fetch (`SweepFetch`, `meeting_key`, `observe`, `fetch_one`; 1,026 lines) lives on `origin/v262-250b` (f1b631e6) and the read-order commit on local `team-stark-250-readorder` (d3db0561, base c041c841). `dev/tests/test_fetch_transcripts.py` is not on main; `sweep.fetch_transcripts` exists on main only in a hand-check test string. Step 1 is therefore a **port**, not a merge.
- **Both guarded diffs on file no longer apply to main** (`git apply --check`, checked 26-10): `dev/proposals/fetch-transcripts/live_server.diff` (observer hook) and the #365 follow-up pair (`live_server-365-followup.diff`, recoverable from b09ee32d; run_dirs hunk, changed by #339 A, is rejected). Both need a rebase and, for the follow-up, Alan's word again.
- **Open from Cap's last verdict (24-10)**: H1 order c (confidential event saved with `teams=False`, never read in the run, so nothing marks it held); M1 `finish()` before `sweep.py done` cannot be built (done is Claude's own Bash step); M2 stopped/failed runs are order c by construction; L1 silent holds; L2 `meeting_key` over-merges on `@`/`_`; L3 `[` in a URL raises after `held.add`; L4 `finish()` drops reads on an exception, no switch re-check, no cap on queued text; L5 `"x"`-to-`"w"` and idempotence mutants survive, partial .vtt.

## 3. The #365 follow-up pair, #371 and the failed loads

- **What #371 is:** "Load the transcript: retry once automatically on a 0-step failure, and say what happened" (split from #370; Alan agreed 25-10). Replace "The meeting's calendar event couldn't be read" (wrong when the event is fine) with "Microsoft 365 wasn't available to this run; I tried again" / "press Load again"; log the refusal reason and the tool list at start; compare a failing and a succeeding load. Moved to **2.6.9** by Jarvis (26-10, "goes with the #365 follow-up pair"). The 2.6.8 notes say the same: "a structural rewrite ... come in 2.6.9, together with two follow-ups to Load the transcript (starting the run without any context, and a limit on its searches)". But Jarvis's 2.6.9 list (E1 #375, paths #374, #366) does not name them. **Open question 1.**
- **The pair:** (a) `CONTEXTLESS_JOBS = ("check","load")`: start in an empty folder, `--setting-sources ""`, no session saved, no `--add-dir` (so no vault CLAUDE.md and no session-start rule; the M365 connector is account-level and stays; the held hook stays via `--settings`); (b) the load prompt searches one hour either side, then the whole day, then the exact start and end, three searches at most, takes only the event whose id is exactly the asked one.
- **Root cause of the failed loads: still unproven.** Evidence (#365/#370): 6 of 10 loads failed in a week; five ended in 4 to 7 s with 0 steps and the same message; the same 1,395-character prompt later loaded on the fifth try; an ask run read the same event fine. Leading hypothesis (Cap M-a): the run started in the vault, the vault CLAUDE.md imported "run session.py start first", the held guard refused it, the model gave up before any M365 call. 2.6.8's prompt change removes the instruction but not the CLAUDE.md load; the pair removes the load itself. Second hypothesis (#371): the M365 tools were not yet connected at the start of the run (fails then succeeds seconds later). Only logging separates them: today's log has counts of tool results, not the init event. 2.6.8 logs now exist (tool, ok/error, length) but a 0-step failure produces none.
- **Recommendation: fold into the #250 guarded chain only if 2.6.9 does not ship them; build them as separate diffs with separate bytes and hashes either way.** All three touch the same transcript area of `live_server.py` and the #250 server hook is useless if loads (the same Job/`Run` machinery) still fail at start. Chain order: (1) pair rebase, (2) #371 server logging, (3) #250 observer/finish. If 2.6.9 takes (1) and (2), drop them from the 2.6.10 chain and rebase (3) on them.
- **Split of #371 to keep the guarded part small:** the retry-once and the new wording are ordinary files (the page retries `jobLive("/api/transcripts/load")` once when the result says no Microsoft 365 call was made: `core/intakeApi.js`, `components/intakeReview/actions.js`; wording in `Job.no_event`). Guarded: log the `system` init event's MCP status and the count of Microsoft 365 tools, names and counts only (`live_server.py` near line 3261), the diagnostic that proves the root cause.

## 4. Design for 2.6.10 (closing the leak)

1. **Hold set from independent data (H1).** Before and during the run, the server's observer holds a transcript if (a) the event read in this run is not `normal`; (b) its `meeting_key` equals that of any confidential event read in the run, in either order (queue reads, settle at the end); (c) **calendar rule** from the saved `calendar.json`, which keeps id, day, start, end and sensitivity for confidential events even though `teams=False`: `calendar_hold(row, found, rows)` holds when a transcript's created time falls within [closed.start - 15 min, closed.end) on a closed row's day, or its created time is unreadable, or a closed row has unreadable times within a day. `same_meeting` tightens to [row.start - 30 min, row.end]; a missing created time = another meeting. Fail closed: calendar file missing or corrupt holds everything. Sensitivity other than `normal` or missing counts as confidential.
2. **Residual gap:** a confidential event not in `calendar.json` (ignored by a sweep rule, older than the saved days, declined). `sweep.py calendar` keeps a stub `{id, day, start, end, sensitivity}` for an ignored confidential event; declined ones stay a documented gap (needs a mention in the rules text and the notes).
3. **Settle at run end, server-side (M1/M2).** `finish()` is called from `Run.read()` after `proc.wait()`, before `_done()`, in try/except (logged by name). Only a run that ended **answered** settles; stopped, timed-out and failed runs drop the queue and count "left" (Process still works). The count is a **server-side closure line** ("2 transcripts fetched, 1 held back: a confidential meeting at that time, 1 left: Process to load it"); `sweep.py done` and `sweep-fetched.json` are not used (drops the M1 problem and the guarded `done` ordering).
4. **Cap's LOWs:** `@` rule only outside the first path segment; `urlsplit` wrapped so a bad URL blocks first; each read settled in its own try; `fetch_on()` re-checked at settle; queued text capped at 25 MB; `"x"` mode and a removed partial .vtt (also in `Job.write`, shared with Load); visible outcome for every held read; the two over-holds (case-only join ids, series occurrences) stay, now with a reason.

## 5. Files and the guarded split

**Ordinary (normal commits):** `system/scripts/transcripts.py` (SweepFetch port, `calendar_hold`, tightened `same_meeting`, `Job.write` "x" mode, `no_event` wording), `sweep.py` (calendar stub; cx-sweep text; `done` unchanged), `settings_catalogue.py`, `system/templates/settings-defaults.json`, `system/config/settings.json` (new key only), dashboard source (Settings section `settings.js`, Intake retry in `core/intakeApi.js` and `components/intakeReview/actions.js`; rebuild `dashboard.html`), `.claude/skills/cx-sweep/SKILL.md` (text only; `.claude/skills` is not guarded), help text and release note, tests (below). `reach.py` is **not** edited: the plan keeps the write in the server (a `SCRIPT_COMMANDS` test proves no transcripts command is DERIVED and writes).

**GUARDED, travel only as patch files under `dev/proposals/GUARDED-2.6.10.chain`, none edited directly:**

| # | Patch | File | Content |
|---|---|---|---|
| G1 | `dev/proposals/365/live_server-365-followup.rebased.diff` + `tests-followup.diff` | `live_server.py` | CONTEXTLESS_JOBS, 3-search prompt; rebased on main (needs Alan's word on the new bytes) |
| G2 | `dev/proposals/371/live_server-371.diff` | `live_server.py` | log init MCP status and M365 tool count (counts only) |
| G3 | `dev/proposals/250/live_server-250.diff` | `live_server.py` | `Run.fetch` for sweep runs, `_fetch_observe`, `_fetch_finish` in `read()`, live event sensitivity at settle, closure line; helpers extracted so `Run.__init__` (CC 18) and `_on_tool_result` (CC 15) stay within limits |
| G4 | `dev/proposals/250/creaite-rules.diff` | `system/creaite-rules.md` | the transcripts paragraph: setting, the server's inbox write, the hold, the residual gap (short; the file was halved in #338) |

No change to `.claude/settings*`, `permissions.py`, `backup.py`, `client_leak.py`, `tracker.py`, `filechange.py`, `update.py`, `edit_ai.py`, `draft_delivery.py`. No tool, `--add-dir` or allow-rule is added.

## 6. Slices for five agents

| Slice | Owns | Interface it fixes or uses | Tests it owns | Depends on | Size (agent-days) |
|---|---|---|---|---|---|
| **A Port + observer** | `transcripts.py` SweepFetch/meeting_key/observe/settle, port of 250b + readorder, restore `test_fetch_transcripts.py` | `SweepFetch.observe(name, input, text, is_error)`, `finish(answered: bool) -> counts`, `fetch_text(counts)` (the contract G3 calls) | the 30 + 121 + 22 ported tests; LOW tests (`"x"` mode, partial file, idempotent finish, switch off mid-run, `[` URL, `@` rule, cap) | none | 1.5 (1 to 2.5) |
| **B Calendar hold** | `calendar_hold`, `same_meeting`, calendar stub in `sweep.py`, `fetch_text` reasons | `calendar_hold(row, found, rows) -> "held"|None` (pure; A calls it in `settle`) | order c held; back-to-back fetched; double-booked held; missing created held; empty-times closed row; private row; TZ=Europe/London; pinned day; Cap's 125 cases committed as `dev/tests/test_fetch_transcripts_hostile.py`, only the two documented over-holds failing-by-design (now asserted held with a reason) | A's skeleton (can start on the pure function) | 1.5 (1 to 2) |
| **C Guarded diffs** | G1 rebase, G2, G3, G4 as patch files + `GUARDED-2.6.10.chain` + README with hashes | consumes A's contract; `Run.read()` end-of-run hook | `test_guarded_chain` (new chain lines), mutants for G3 (no call; call in `_on_tool_result`; settle on stop/timeout/fail; finish outside try; non-sweep kind gets fetch; counts missing from closure), `check.py` clean with each applied; tests-followup | A's contract | 1.5 (1 to 2.5) |
| **D Page, setting, #371 front end** | Settings section, defaults, catalogue, Intake retry-once, `no_event` wording, cx-sweep text, help, release note | `sweep.fetch_transcripts` default false; `Job.no_event` kinds | `test_settings_page`, `test_settings_catalogue`, `test_dashboard_split`/`split_dashboard.py stale`, retry test in `dev/tests` (one retry only, never on a real error), `test_no_real_names`, plain-words ratchet | none (wording after C names the closure line) | 1.0 (0.7 to 1.5) |
| **E Verification** | `test_v2610_fetch.py` hand-check automation, mutation run, second hostile run, privacy sweep | all of the above | see section 8 | A, B, C landed | 1.0 (1 to 2) |

Dependencies: A and D start at once; B starts on its pure function; C starts G1/G2 at once (they do not need A) and G3/G4 once A's contract is fixed; E last. Merge order: A, B, D, then the guarded chain G1 to G4 (applied by the chain, not by hand). Agents commit only; the main session pushes.

## 7. Estimate

About **6.5 builder-days of agent work (range 5 to 9)**, which is the earlier "about 5 d (4 to 8)" plus the rebase of the two guarded diffs and #371 logging. With five agents in parallel: **3 to 4 calendar days** to a clean candidate, plus review: Alan's approval of each exact diff (G1 to G4), Cap's Full review or the Opus waiver, a second hostile run, and a fix round (0.5 to 2 days). Plan on 5 to 6 calendar days end to end, 8 if the review finds anything in the hold.

## 8. Risks

- **Privacy: confidential transcript text in `inbox/`** is the one content rule. The residual gap (confidential event not in the saved calendar) and any unfolded URL spelling stay; mitigations: off by default, fail closed, calendar rule, hostile suite. The real Teams transcript URL form (base64 vs thread id) is unchecked: one live run is needed to confirm `meeting_key` and the created-time window.
- **Transcript text handling:** it is held in server memory until the run ends (cap 25 MB); written only via `open(..., "x")`; the debug log and closure line carry counts only; the closure line and reasons never name a confidential title (the load prompt's day search already puts other titles in a run's context, which 2.6.8 told Alan).
- **Held-run hook rules:** the observer writes `inbox/` as the server's own write. In sweep mode the hook must keep refusing Write/Edit into `inbox/` and `transcripts.json`; `filechange.py` into `inbox/` in a marked run stays on the card. Test that nothing in G3 widens `KIND_TOOLS["sweep"]`. G1's context-less start must keep the held hook (`--settings`) and refuse Bash (Cap's probe: it does).
- **M365 read-only boundary:** only `outlook_calendar_search` and `read_resource`, exact names (no lookalike); no M365 action tool; tested against `permissions.M365_READ` / `DENY_TOOLS`.
- **Run-end hook:** `Run.read()` end is the only safe sync point; `_done()` must still emit if `finish` raises. Complexity limits (CC 18 and 15) in `live_server.py`.
- **Port drops a main fix:** run the whole suite and `check.py`; the two fetch-era test files were removed on main.
- **Shared writer:** `Job.write` serves Load too; the "x" mode changes Load's duplicate-name behaviour (already handled by `unique()`; re-test Load).
- **Root cause of failed loads may not be the CLAUDE.md load**; G2 is the diagnostic. Do not claim a cause in the notes until a log shows it.
- **Schedule:** if the hold is not closed and reviewed in time, #250 defers to 2.7.1 (Alan's rule); the unguarded parts can still ship with the setting hidden only if Alan agrees (recommended: no; keep it whole).

## 9. Tests (automated) and hand checks

Automated: ported `test_fetch_transcripts` (30), hostile (121) and Cap's 125-case file; `test_transcripts`; new order-c, calendar-hold, stop/timeout/failed-run, idempotent finish, switch-off, partial file, `[`/`@` cases; `test_job_followup_365` (3) and `test_job_prompts_365`/`test_job_tools_365`/`test_held_edit_deny` (the 2.6.8 frozen red: its HELD list must stop expecting Read/Grep/Glob for check and load; own test change, own bytes); `test_guarded_chain` with the new chain; `test_reach` (no transcripts script command writes inbox); `test_settings_page`, `test_settings_catalogue`, `test_session_sweep`, `test_panel_sweep`; `test_no_real_names`; mutation run (switch default on, hold skipped, `"x"` to `"w"`, `finish()` not clearing, call in the wrong place, settle on stop: all red); `check.py`, `build_guides.py --check`, `split_dashboard.py stale`; `test_v2610_fetch.py` for the walk-through's automatable steps (setting default, nothing in `tracker.db`, nothing staged).

Hand checks (Alan, live Microsoft 365, throwaway meetings): (1) switch off: a sweep fetches nothing; (2) on: a normal ended meeting appears in Intake and the closure line counts it; (3) a confidential meeting is not fetched and the reason is shown without its title; (4) two meetings naming one Teams meeting, one confidential: held in either order; (5) Stop a sweep mid-run: nothing written, "left" counted; (6) a failed Load retries once and says which way it failed; (7) nothing in `tracker.db`, nothing in Review.

## 10. Open questions

For Alan:
1. Do the #365 follow-up pair and #371 ship in 2.6.9 (as the 2.6.8 notes promise) or ride in the 2.6.10 chain? Recommend: whichever release is first, as separate diffs with separate hashes; either way the rebased bytes need his word again.
2. May the Intake page retry a 0-step Load once automatically (a second run of the same fenced kind, Alan not asked)? Recommend yes.
3. One live-account check for the real transcript URL form before release (a throwaway meeting)? Recommend yes; it decides whether `meeting_key` needs a change.
4. Documented gap (a confidential event dropped by an ignore rule or declined): accept with a stub for ignored ones only? Recommend yes.

For Jarvis:
5. Cap Full review available for 2.6.10, or the fresh-Opus waiver plus a second hostile run (Alan's rule)? Cap's `hostile_250_final.py` exists only in a scratchpad and on the issue: ask Cap to commit it.
6. Does `GUARDED-2.6.10.chain` pin G1 to G4 only after Alan's word (as 2.6.8's chain was left unpinned)? And who owns the `test_held_edit_deny` fix?
7. Is the `team-stark-250-readorder` branch still the agreed starting point, or does the port start from `v262-250b` plus the readorder commit as two cherry-picks?
