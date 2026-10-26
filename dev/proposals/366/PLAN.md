# #366 plan: the client-output review kit (kit26), what is still required

Base: origin/main a62fbb0a (2.6.8 released). Kit: branch `team-cap-reviewkit-26d` c81b2867, `dev/proposals/review-kit/`. Read-only planning; nothing was run.

## 1. Where #366 stands

- Alan, 25-10: "366 yes, 2.6.9": graduate the fast calendar-scrub and followed-people probes into `dev/tests`, keep the rest as a record on the branches, drop the obsolete group, do not delete the branch until it has landed.
- Already on main (2.6.8): `test_invite_clean_bare*.py` (bare, 20, 21, 22), `test_followed_people_probes.py`, the calendar sanitise suite. So Cap's "k26-b / k26-c obsolete" calls are now true on main, not only on the 2.6.8 line.
- Banner's local, unpushed work (per the issue): `test_track_crossed_366.py` (step 3, 7 tests, 16 s) and the step 1 audit sheet. Step 2 (`test_calendar_client_outputs.py`) and step 4 (gap fill) are not started.
- Not on main: the kit itself (80 files, 756 KB), `test_track_crossed_366.py`.

## 2. The kit, as inspected

- 101 probes in `probes.tsv` (71 for 2.5.x, 25 k26, 5 k254). About 40 Python scripts in `src/`, one POSIX runner `run_all.sh` (one probe at a time, 600 s watchdog, load gate), `classify.py` (47 KB: log to PASS, LEAK, ERROR; SKIP for k26/k254), `selftest_classify.py`, `run_mutants.sh` with three mutant lists (27 mutants, 16 files in `mutants/`), five guarded #280 diffs in `patch/280/`, INDEX.md (53 KB), CHECKLIST.md (33 KB).
- Runs where: the probes copy a checkout's `dev/tests` and `system/scripts` helpers and build throwaway vaults under `$KIT_OUT`/`work`; they import creaite modules (`python3 -I`, `KIT_CK`). Guarded diffs are applied to the vault's copy, never the checkout. A few probes need Chrome (`csp_check`, `cdp_check`, the browser-slot env `CREAITE_BROWSER_SLOTS`); k26 and k254 need none. Live server: some probes start it in-process on a throwaway vault. Network: none. Microsoft 365: none. Writes: only `$KIT_OUT` and the kit's own `work/` (git-ignored via its `.gitignore`); the checkout is untouched.
- Runtime: README says whole kit 25 to 35 min; k26 alone 15 to 25 min; Cap's 2.6.6 re-run of k26 took about 9 min, mutants 31 s (k26) plus 2 min 41 s (k254).
- Privacy scan (grep of the extracted kit): addresses are all `*.example` (brightwater, client). One path-shaped string, `/Users/pat/Clients/Harbour/...svg`, is a fictional SVG metadata fixture. `INDEX.md:5` mentions scratchpad directory names (generic). No real names or client names found; `test_no_real_names.py` scans every tracked text file, so it is the gate on landing. INDEX/CHECKLIST are long and mention branch names and worktree habits; re-read before landing.

## 3. Findings on each question

(a) Merge into main as dev-only: safe for release. `build_release.py` zips only `paths.ENGINE` + `ENGINE_MERGED` (VERSION, rules, `system/scripts`, `system/templates`, `.claude/skills`, two settings files). `dev/` is never in a release. So nothing about the kit can reach Alan's vault. Cost: 756 KB of mostly stale 2.5.x probes in a public repo, and every tracked file is scanned by test_no_real_names and linted.

(b) Test suite/CI: the useful part is already there or about to be (items in section 1). Wiring the kit itself into CI is not justified: 101 probes at 25 to 35 min would blow the Free plan budget (20 jobs, one release-line run at a time; the suite is already 17 + 3 shards), and Banner's audit puts 73 of 101 as obsolete (covered by named tests), 16 gap-fill, 7 record, 4 drop, 1 move.

(c) Keep out of the repo: not needed on privacy grounds (grep clean), but needed on hygiene grounds for the stale 2.5.x majority: many probes call APIs that have moved (`word_export` now refused without `client_snapshot.TOKEN`, `safe_css_value` lost its `client` argument, `kitshim` helpers, d280 distributed control stale, rvlogofix false LEAK). Stale probes under `dev/` would show ERROR or false LEAK as a "gate".

(d) Classifier as a gate: not reliable on today's main. Known: (1) `k26-b-outputs` ERROR from a clock mismatch (fixed in 26d by pinning `CREAITE_NOW`); (2) `atk-other-paths` would ERROR (bare client export refused); (3) d280 CTRL-FAIL (distributed export needs approved internal minutes); (4) `rvlogofix-route-logo` false LEAK (a project's own logo path is stored by design); (5) `only_prefix_dropped` mutant cannot apply (anchor now occurs 4 times); (6) `kitshim` not on the path when a probe is run alone; (7) SKIP depends on the probe reading the source, so a renamed feature turns into a silent SKIP; (8) several probes sample (idpass: every 7th of 5,760) so a miss is possible but deterministic; timing: 600 s watchdog plus load gate means a loaded box shows ERROR, not LEAK. It is a good human review aid (self-test and 12 of 12 mutants show LEAK), not a CI gate.

(e) What Cap's review and Banner's audit say is missing (gap-fill, none a known leak on main):
- outside-email path: no test drops the followed-person word (reply or selection); 4 of 32 ID spellings; about 13 address spoofs and 10 place spellings untested.
- k254-d: nothing checks that the held reason or transcript-name word is absent from the debug log, Excel, DB, reports, search, drafts (mutant `held_reason_logged` survives). k254-e: 5 of 40 hostile `only` values. k254-a: only match-check of 6 routes. k254-c: Internal tag, "never sent", overwrite rules on a no-project page.
- k26-b literal forms (title/place, letter-only body values, attendee/attachment names, private and odd-sensitivity meetings through `sweep.py calendar`).
- k259-p16 loose ID forms (`ABC-A-001／1`, `12 ABC-A-001`) on Word-body and AI-draft surfaces; a client Word `.rels` outside address; more `bad_refs`.
- Standing gap: several covering test files are Chrome tier and skipped by `--quick` (186, followed people, track review, save_not_blocked, held_missing_source, match_check, sweep_alerts, client_view), so these run once per commit in CI only on the browser shards.
- Open product decision from the 2.6.6 re-run: `k26-b-bare` (`Password swordfish`) was raised as a separate defect; bare19 to bare22 tests on main pin or fix it. Confirm that issue's state before claiming the kit's one LEAK is closed.

## 4. Recommendation

1. Do NOT merge the whole kit into main, and do not wire it into CI. Follow Alan's approved scope: graduate into `dev/tests`; keep the kit as a record.
2. Required for 2.6.9: Banner's steps 2, 3 and 4 as tests only, with step 1's audit as the posted record (the audit is done; the issue has the sheet).
3. Keep the kit as a record, outside `main`'s tests: add one small archive commit only if Alan wants it findable: `dev/archive/review-kit/` holding README, probes.tsv, classify.py, selftest, run_all.sh, mutants lists and the k26/k254/k259 scripts (about 300 KB), dropping the stale 2.5.x image/CSS/SVG scripts. Otherwise leave it on `team-cap-reviewkit-26d` (do not delete until the PR lands). Recommended: leave on the branch plus a tag-free note in the issue; archive only on Alan's yes (private `creaite-confidential` is the alternative and equally clean, grep found nothing to hide).
4. The full 101 probes remain a manual pre-release step run by Cap on a quiet box (about 10 to 30 min), not a gate; classifier fixes in section 3(d) only if that run is to continue.
5. Nothing guarded is touched.

## 5. Files to add (all under `dev/`, no guarded file)

| File | Slice | Notes |
|---|---|---|
| `dev/tests/test_calendar_client_outputs.py` | A | k26-b-outputs: fixture vault, `CREAITE_NOW` pinned, canaries in title, place, organiser, body, attachment and attendee; asserts absent from client report draft, export (HTML, Word), filed report, `steerco-data`, steerco-stage docx, `drafts.py context` (status-form, polish, client wording). Records `followup_facts` attendees as by design. Full tier (client leak). |
| `dev/tests/test_track_crossed_366.py` | A (Banner's, local `team-banner-366-track` 01150426/685d9637) | land as is; needs a different reviewer. 16 s, quick tier. |
| gap fills in `test_email_client_facts_186.py`, `test_invite_clean_bare*.py` / `test_calendar_sanitise.py`, `test_held_missing_source.py`, `test_save_not_blocked.py`, `test_prep_no_project.py`, `test_report_picture_paths.py` | B | cases (a) to (o) in Banner's step 4 list; no new file over 30 lines unless unavoidable. |
| `dev/archive/review-kit/` (optional) | C | only on Alan's yes. |

## 6. Slices (two agents)

- Slice A (agent 1, about 1.25 builder-days): land step 3 (rebase onto main, rerun with `--changed`), then step 2. Step 2 starts after #375/E1 has settled `invite_clean`; the main-line bare22 means it can start now if E1 is in 2.6.9 or earlier; check first.
- Slice B (agent 2, about 1 day): gap-fill in this order of value: (j) held reason absent from logs and exports plus its mutant; (b) followed word in outside email; (k) 40 `only` values; (f, g, h) calendar literal forms and private meetings; (d, e) spoofs and places; (m, n, o) cheap 2.5.x extras. Stop at 3 hours of CPU-light work per item; skip any item whose probe case is already green on main after a diff.
- Slice C (either, 0.25 d): post the record note on the issue; archive step if approved; delete nothing.
- Reviewer: a separate agent (Full tier for A and for (j); Standard for the rest).

Size: about 3 builder-days (range 2 to 4.5; 2 if gap fill is cut to (j), (b) and (k); 4.5 if archive and classifier fixes are added). Cap's estimate was 2.5 from the 2.6.8 line; main now carries bare19 to 22, which removes the rebase risk.

## 7. Tests and runtime

- Every new file quick tier where it needs no Chrome, so it runs in `--quick` (Python 3.9 shards); mark Chrome-tier only what needs a browser. Add `test_wrappers_inventory`/shard test run (`test_run_tests_shard`) to confirm the new files are in exactly one shard.
- Expected added runtime: step 3 16 s; step 2 about 30 to 60 s (fixture vault); gap fills about 30 s combined. Total under 2 min across all shards, no new CI job.
- Mutants: `track_rowed` (rowless promise allowed) must fail step 3; `held_reason_logged` must fail (j); `email_outside_off` must fail (b); the others already caught.
- Not run by this plan: the kit's 101 probes.

## 8. Risks

- Churn: `invite_clean.py` may change again (E1 #375); step 2 depends on it.
- Python 3.9 floor: new tests must run on 3.9 (CI runs the quick tier there).
- Stale helpers: copying kit code (`kitshim`) pulls in removed APIs; use `test_report_exports.tiny_png` and current signatures.
- No real names: fixtures fictional only (`*.example`, Brightwater); `test_no_real_names` runs on every tracked file.
- Chrome-tier skips make `--quick` look green; assert tier of each new file.
- The kit left on a branch may be garbage-collected; keep until the PR lands (Alan's rule).
- test_portability fails one check on Banner's box (`/usr/bin` Python): the box, not the change.

## 9. Guarded files

None. `tracker.py` and `review.py` are only mutated on the vault's copy inside tests; `invite_clean.py`, `client_leak.py`, `report.py`, `live_server.py` are read, not changed. Any guarded diff found (for example a `k254-d` log fix) goes through Jarvis as a diff, not in this slice.

## 10. Open questions

1. Alan: archive the kit's record subset in `dev/archive/review-kit/` (public, about 300 KB, grep-clean), put it in `creaite-confidential`, or leave it on the branch only? Recommended: leave on the branch, archive only if wanted.
2. Alan/Jarvis: is the manual full-kit run a named pre-release step for 2.7 and later, and who owns it (Cap)?
3. Jarvis: state of the `k26-b-bare` defect (separate issue) before the record says "closed".
4. Jarvis: does Banner's local `team-banner-366-track` get pushed for review now (push rule), and which reviewer takes Full tier?
5. Gap-fill scope: all of (a) to (o), or only the three with a surviving mutant ((j), (b), (k))?
