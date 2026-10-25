# Team Cap hand-over (25-10-2026)

Cap is moving to remote work (Jarvis, #99, 25-10-2026 11:30). Work still comes the same way: the board (insyncalan/creaite-plan), #99 (channel) and #199 (Cap's list). Findings only; Cap never merges into main or a release line (Jarvis does, on Alan's rules).

## Branches (all on origin; nothing deleted)
Keep as a record unless marked "merge candidate". Merging is Jarvis's call.

| Branch | What it is |
|---|---|
| team-cap-tools | Probes and tooling: H-1 exploit, M1 probe, matrix probe, smoke/, screens-351 (Today screenshots v2.1.0 to v2.6.3), smoke264 (post-release smoke for 2.6.4; re-usable for 2.6.5/2.6.6 zips). Record + tooling. |
| team-cap-usage-87 | dev/tools/usage.py + test_usage.py (#87 phase A: claude-code usage report). Merge candidate for main. |
| team-cap-goldens-266 | The 2.6.6 goldens sign-off pictures (14 screens x 1400/900, before 2f2acdc2, after ab39f6c1) and shoot_goldens.py (re-runnable on any two SHAs). Record; the script is a tool worth keeping. |
| team-cap-tests-266 | Two test-only additions on v266-release: drawer open-path typing test (#343) and test_inbox_confidential_row.py (#328). Merge candidate for 2.6.7. |
| team-cap-series-362-test | Test for #362 (code in the title vs remembered series). On the 2.6.6 line its three expectedFailure cases now pass: remove the FIXME marks on adoption. Merge candidate for 2.6.7. |
| team-cap-v265-sheet | My 42-check hand-check sheet for 2.6.5 (dev/handchecks/v2.6.5.md + test_v265.py; 38 pass, 4 expected failures 10, 13, 15, 26). Record; the sheet is useful as an extra walk. |
| team-cap-v266-sheet | Draft 2.6.6 notes and sheet module (superseded by Stark's v266-ver). Record only, not for merge. |
| team-cap-v264b-handchecks, -2 | 36 hand checks for 2.6.4b (30 pass, 6 expected failures). Record. |
| team-cap-v264-handchecks, -2; team-cap-v264-notes, -2, -3; team-cap-v264-sheet, -2, -3 | 2.6.4 notes, sheets and checks (partly merged by Jarvis into v264-release). Record. |
| team-cap-v262-handchecks, -2, -3, -4 | 2.6.2 hand checks. Record. |

## Open findings (all posted on the board; summary)
- #343 (2.6.6): final verdict MERGE WITH NOTES on v266-release ab39f6c1. Open LOW: People fit not reproduced on Verdana (-4 px inside the table); browser fit test does not catch a revert; item 8 two-line .docx rows need Alan's confirmation (L-4); the drawer open-path test is unguarded (fix in team-cap-tests-266); "Late milestones: 14 days" accessible name vs visible "Slip" on Today (WCAG 2.5.3); notes say a code "always wins" (not true for a remembered No project / two codes); 4 expected failures in my sheet (10, 13, 15, 26).
- #362: M2 two codes drop a remembered _portfolio; Intake rows still carry p/how for a confidential row (screen only); prep_invite copies body and attendees if calendar.json holds them; a common-word leading code beats a remembered choice; Prep header for a confidential "[DEF] ..." never takes another project; ev_shown_p mutant.
- #358: L1 drift test pins lists not the 120 cap or code rule; L2 i/I-dot Unicode edge; the saved-steps patch (guarded) is undecided for the 2.6.7 chain and turns check.py red; DESIGN.md "model prose accepted" needs Alan's explicit yes.
- #341: L-1 sub-grouping folds lost; L-3 "Nothing flagged" only in the golden; M5 Two panes; L-4 (above).
- #347: Alan approved the rules wording only (Jarvis quote, blob 0046d5ba). Not approved (not read as approved): live_server.py.diff and skills.diff; README approval sentence still pasteable.
- #339 (2.6.7, guarded): v267-339d dd843264 READY WITH NOTES for the server code (deadlock fixed, no race, queued refresh keeps reason). Not ready as a set: "(Alan's decision pending)" placeholder in creaite-rules.diff and hardcoded in test_rules_retained_338 (INSERT_339); the one-page summary dev/proposals/guarded-2.6.7-summary.md is stale (old calendar-route bytes, no 358); 358 undecided; no GUARDED-2.6.7 chain entries yet (simulated CHAIN pin for the 4 diffs: eb4403611bf69c3342be377d78726c0679c4bfea061e98b20522c3fc83a617b5; it changes with any diff); a test that pins fullmatch in panel_kind; the fallback of the page against an old server is untested once the pins land.
- #328 (2.6.7): v267-328 c08cf244 / bb2e8fcd NOT READY: one chip click teaches a whole generic series and "Process all ready" then files other clients' meetings (H-A); a lower-case tag still files under the remembered project (H1, prep_match_ev); the Process all ready filter is a deny-list and skips remembered _portfolio rows; Likely treated as chosen in Prep/hub; Q9 is not in Alan's own words. Keep it out of any release until these are fixed.
- #353: Wanda's pre-gate list: "model prose accepted" needs Alan's yes.

## What Stark or Romanoff must pick up
- Stark: the #339 round-6 (placeholder + INSERT_339 + summary + 358 decision + chain files + the fullmatch test); #328 fixes; fold in team-cap-tests-266 and team-cap-series-362-test when 2.6.7 is cut.
- Romanoff: Alan's approvals list (Cap's 08:00 list on #99) and the scope of "347 approve"; Q9 in Alan's words; item 8 confirmation.
- Jarvis: merge only on a green CI plus the verdict above; the Free-plan CI patch is Natasha's.

## Scratch (not branches)
hc262 and hc262b worktrees hold the released 2.6.2 chain applied for testing (reproducible from the chain file; nothing to save).
