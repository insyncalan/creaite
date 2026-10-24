# #338 — slim `creaite-rules.md` by half (part C of #327)

For Alan's approval: the exact diff of a guarded file. Nothing is weakened; the long reference moves to a file a run reads only when it needs it.

## Size (bytes; tokens = bytes ÷ 4, the estimate `usage_log.py` uses)

| | Before | After | Cut |
|---|---|---|---|
| Rules on `origin/v262-line` | 62,721 B (about 15,680 tokens) | 31,282 B (about 7,820 tokens) | 50.1% |
| Rules on main 799da01c (the 2.6.2 and 2.6.3 chains in; the 2.6.4 chain does not touch the file) | 66,315 B (about 16,580 tokens) | 32,736 B (about 8,180 tokens) | 50.6% |

Every run loads the rules file, so each run starts about 7,900 tokens lighter. That is the size of this lever (about 3% of a 503k ask start, as #327 says); the 60k and 150k run targets come mostly from part B (fresh sessions).
The moved text is in the new `system/templates/creaite-reference.md` (62 KB, read by section only when a task needs it; it ships because `system/templates/` is part of the engine). Nothing is deleted from the project: the reference holds the old wording of every section I shortened, word for word.

## What to approve

Two diffs of one change, apply the one that matches the file you have:
- `creaite-rules.diff` against the file on `origin/v262-line` (before the VIP/follow rules diff).
- `creaite-rules.after-chain.diff` against the file after the 2.6.2 chain (`GUARDED-2.6.2.chain`, last entries: `draft-delivery/rules-and-skill.diff`, then `vip-follow-rules/creaite-rules.md.diff`). **Apply order: the 2.6.2 chain first, then this diff.** The two slimmed files differ only in the wording those chain diffs change (VIP/follow, Create drafts in Outlook).

Both were checked with `git apply --check`, applied forward, compared byte for byte with the slimmed file, then applied in reverse back to the original. The after-chain diff was also checked against the real chain: the 12 diffs of `GUARDED-2.6.2.chain` applied in order on a scratch tree, then this diff, equals the slimmed file byte for byte. The line diff only slims; it carries none of the chain's wording (Follow check, Create draft in Outlook). Do not edit the tree file by hand; the diff is the approval.

## Section by section

| Section | Result | Where the full text is |
|---|---|---|
| Header, Development guard, intro | Kept; one sentence added pointing to the reference | — |
| **Non-negotiables** (all 10 bullets) | **Kept word for word** (the Local, Approval, administrator, Open, Sensitive, Never, One writer, Schema, Source, Confidential bullets) | — |
| Folder map | Kept as a shorter table. Rules kept: stored paths, `99 System` reserved, 99 Archive moved only by `tracker.py apply` and never touched by ask creaite, staging and logs hold references and counts only (never text, join links, passcodes), `system/guard/` written only by server and hook, `tracker.py` the only writer | Reference, Folder map (the long cells for staging files, scripts, project folder, locations, archive) |
| Starting a session | All steps kept (0 to 5, the quoted reminder lines, First thing); steps 1 and 5 tightened | Reference, Starting a session |
| Skills and commands | Every trigger phrase kept (the dashboard reads them); every "never" kept (bulk approval never covers minutes, new decisions or new risks; never sends; ask creaite never drafts, stages or writes a report) | Reference, Skills and commands |
| Scheduled tasks | One sentence | Reference |
| Dashboard editing | Kept: what the dashboard writes, live mode, apply, the guard hook's refusals, sweep mode, marked runs and the one card, permission files, editors and notes, assistant (reading open, Microsoft 365 actions off, no skip-permissions) | Reference, Dashboard editing (hook argument forms, BL-267 detail, Prep page, Intake Process, Follow check, Draft email delivery, project settings categories, AI on text) |
| Updates | Kept in one paragraph | Reference |
| Project documents | Kept; the notes-passive rule stated once instead of twice | Reference |
| Portability rules | Kept: no pip, one interpreter, relative paths, root files, launchctl, Windows, OneDrive | Reference (tiers 1 to 3, macOS conveniences, login agent, interpreter detail) |
| Memory rules | Kept (compressed layout only) | Reference |
| Retention | Kept: Tidy up limits, restore, archiving deletes nothing, Delete note, never from ask creaite | Reference (the backup schedule and counts) |
| Conventions | Kept (dates DD-MM-YYYY / YYYY-MM-DD, projects by name, BL-288 VIP/follow); the "projects by name" bullet shortened | Reference |

**Removed:** only duplicates (the notes-are-passive rule, the Delete note rule and the guard hook list were each said twice; the standalone Apply bullet was folded into Live mode). Nothing else is deleted. Enforcement stays in code (`reach.py`, the guard hook, `filechange.py`, the live server), which this change does not touch.

## Proof

`dev/tests/test_rules_retained_338.py` (25 tests):
- **Non-negotiables and Development guard: byte for byte** as in the original.
- **Every other section, whole sentences**, one test per section (Header, Folder map, Starting a session, Skills, Dashboard editing, Updates, Project documents, Portability, Memory, Retention, Conventions): 144 rule-bearing sentences (any sentence with never, only, must, may, off, not, stay, refuse, nothing, every, approve, confirm, flagged, client and the like) are asserted whole, never as fragments and never matched both ways. State-specific wording (before and after the 2.6.2 follow diff) is kept apart.
- **Every "never" clause of the original** is accounted for: inside a fixture sentence, present verbatim (six words or more), or in one of two lists: REWORDED (9 whole original clauses and the whole shorter clause that now carries each) and MAPPED (24 clauses that only describe what a record holds or how code or the launcher behaves, each kept word for word in the reference, with its reason and a pointer line that stays in the rules).
- **Permanent mutants:** 44 named mutants (46 after the chain), covering the 28 the second review found green plus more (BL-267, "runs only read commands", the sweep refusals, `Only flagged items`, `off by default`, `four` images, the permission-file checks, "nothing the model can read or run holds", "or one Alan edited", the client-safety rules and others), each edits a copy of the slimmed rules and must turn the check red. In addition every fixture sentence is deleted and flipped automatically (304 more mutants), and each REWORDED and MAPPED entry is removed.
- Also: the rules are at most half the original, the line diff adds no chain wording, the diffs apply forward and reverse, the skills table rows and both date formats survive.
- Run in four states: the line file, the line file slimmed, the file after the real chain, and that slimmed.

## Review notes dealt with (24-10-2026)

The note-exemption limit, the accurate staging exceptions (calendar.json invite bodies, vip.json gist, usage-reviews notes, the confidential-meeting rule), the images rule, the sweep refusals and plain-chat rule, the Find updates rule, `only the version he confirmed`, the 99 System rule and the restore rule are back in the rules file. "Runs on a Mac" now reads "with the things below and nothing else", so it no longer clashes with the Windows line.

Second review (24-10-2026): the two client-safety rules (a partner's name reaches a client only as its logo picture; client report files are made only from the checked copy, #239) are back in the rules, the Prep page keeps "or one Alan edited" and the cx-prep command-line rule (BL-271), "never a chat" is limited to the run kinds, vip.json is listed as "a gist and Claude's own summary, never message text", and the reasons on the moved clauses are corrected.

## Risks

- The reference is only read if a run chooses to; the rules say when. Everything a run needs every time is still in the rules. If a run misses a mechanism detail it can still not do anything the code refuses.
- The reference has the 2.6.2 wording (follow flag, Create drafts in Outlook); on a tree without the chain it describes slightly more than is built. Apply the chain first.
- Root `CLAUDE.md` (0.7 KB) and the new-vault template (0.7 KB) are already tiny; nothing to trim there.

## Fixed after the 2.6.4 review (24-10-2026)

Two small things were put back in the slimmed file: "`system/` is never hidden" in the Other paths cell, and `calendar.json` again says "never join
links or passcodes" in the staging row (it is 58 bytes longer than before; the cut is 50.6%). The retained-rules test holds both
(a whole-sentence check and the MAPPED entry for the table's closing bar). The diff was regenerated against main 799da01c.

