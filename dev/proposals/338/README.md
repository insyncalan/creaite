# #338 — slim `creaite-rules.md` by half (part C of #327)

For Alan's approval: the exact diff of a guarded file. Nothing is weakened; the long reference moves to a file a run reads only when it needs it.

## Size (bytes; tokens = bytes ÷ 4, the estimate `usage_log.py` uses)

| | Before | After | Cut |
|---|---|---|---|
| Rules on `origin/v262-line` | 62,721 B (about 15,680 tokens) | 31,116 B (about 7,780 tokens) | 50.4% |
| Rules after the 2.6.2 VIP/follow chain | 66,315 B (about 16,580 tokens) | 32,509 B (about 8,130 tokens) | 51.0% |

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

`dev/tests/test_rules_retained_338.py`:
- A fixture lists, with exact words taken from the current file, 93 full-clause rules that must stay in the imported rules, 7 rules reworded shorter (both wordings checked), and 27 "never" clauses that only describe what a record holds or how code enforces a rule (kept word for word in the reference, each with a pointer line that stays in the rules). A further check extracts every "never" clause of the original and fails if one is in none of these and is not a 6-word-or-longer clause present verbatim in the rules.
- It also checks the note limits, the images rule, `only the version he confirmed`, the sweep refusals and the staging exceptions, which contain no "never". It applies the right diff to a scratch copy (or reverses it if already applied), checks every fixture phrase is in the unslimmed file, that the rules are at most half the size, that the line diff adds no chain wording, that all ten non-negotiable bullets are present, that the skills table rows and both date formats survive, and that the diffs apply forward and reverse.
- Mutants: deleting the line that holds any rule, turning a "never" into "may", or deleting a moved clause from the reference each make it fail (checked for all of them in the test, and by hand on the tree).
- Run on three states: the line file, the file after the chain, and each slimmed file in place.

Also run with the line diff applied on a scratch tree: the tests that read the rules file (see the handover note for the list and results).

## Review notes dealt with (24-10-2026)

The note-exemption limit, the accurate staging exceptions (calendar.json invite bodies, vip.json gist, usage-reviews notes, the confidential-meeting rule), the images rule, the sweep refusals and plain-chat rule, the Find updates rule, `only the version he confirmed`, the 99 System rule and the restore rule are back in the rules file. "Runs on a Mac" now reads "with the things below and nothing else", so it no longer clashes with the Windows line.

## Risks

- The reference is only read if a run chooses to; the rules say when. Everything a run needs every time is still in the rules. If a run misses a mechanism detail it can still not do anything the code refuses.
- The reference has the 2.6.2 wording (follow flag, Create drafts in Outlook); on a tree without the chain it describes slightly more than is built. Apply the chain first.
- Root `CLAUDE.md` (0.7 KB) and the new-vault template (0.7 KB) are already tiny; nothing to trim there.
