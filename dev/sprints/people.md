# Sprint: People (BL-55, BL-56)

Branch `sprint-people`, worktree `../creaite-people`. Runs in parallel with `sprint-insight` (`../creaite-insight`) and `sprint-live-vault` (`../creaite-live`). Read the full item write-ups in `dev/BACKLOG.md` first; they hold Alan's decisions.

## Goal

Everyone who owns an item is a known person with one full name, so owners come out consistent from minutes, sweeps and edits from day one of the live trial, and Alan can see each person's open work.

## Items

1. **BL-55 People register.** `projects/_portfolio/people-register.md` (beside `project-register.md`; a data file, not a setting): full name, email, aliases, organisation, role. Settings › People reads and edits it (add, edit, rename and merge as now; a merge adds the old name as an alias). Wherever an unknown name is entered as an owner (dashboard owner picker, cx-edit, a proposal in Review), creaite offers likely matches ("Is 'Sara' Sara Khan?") and otherwise asks for the person's details. cx-minutes, cx-sweep and cx-edit read the register every run and map aliases and email addresses to the full name; unknown names are flagged in Review, never guessed. Existing `settings.json` `people.added` names migrate into the register once (cx-setup offers it). Edits go through proposals (`file_changes`), so they're logged and undoable.
2. **BL-56 Person pages and People list.** A People view (rail button, list with counts) and a page per person: open actions and RAID items they own across projects, overdue first; decisions they made recently; workstreams they lead if known. Links both ways (an owner name in Work, the panel or Review opens their page).

## Boundaries

- **Owns:** Settings › People, the owner picker (`comboDraw` and friends), the new People view and its rail button, `system/scripts/propose.py`, the people parts of `.claude/skills/` (cx-minutes and cx-sweep conventions, cx-edit, cx-review, cx-setup's migration offer), one added entry in `paths.py` for the register path and its place in `paths.DATA`.
- **Don't edit:** Today, the project page (cockpit), Work's filter code, `system/scripts/live_server.py` routes, `report.py`, the warnings or quick-capture code (sprint-insight owns them), `update.py`, `doctor.py`, `dev/tools/` (sprint-live-vault). If a change there is needed, note it under "Hand-offs".
- **Shared files** (`dashboard.html`, `build_dashboard.py`, `settings.json`, `help.md`, `dev/dashboard-spec.md`, `dev/BACKLOG.md`, `dev/BRD.md`): add new code in its own clearly marked section (`/* ===== People (BL-55, BL-56) ===== */`), add new data keys at the end of `collect()`'s dict, and don't reformat or reorder existing lines. Leave `BACKLOG.md` and `BRD.md` alone; Claude in the main checkout moves items into the BRD at merge.
- Development guard: sample data only; test with temporary vaults.

## Done when

- Tests: register parse and write round trip; alias and email mapping; the new-person prompt; Settings edits as proposals and undo; the People view and a person page in headless Chrome; migration from `people.added`. The full suite passes in this worktree.
- Help and `dev/dashboard-spec.md` updated; a short "People" section added to `dev/BUILD.md`.
- Each item committed separately on `sprint-people` with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)

- **`live_server.py` (`FS_RULES`):** allow `read` (and so `exists`) of `projects/_portfolio/people-register.md`. Without it the live dashboard can't read the register through `/api/fs`; the page then edits it from the text it was built with (`D.people_register.text`) and the apply refuses the change if the file has moved on ("changed since this proposal was made"), so nothing is lost, but a stale page needs a reload first. Writes need no rule: the register is written by `tracker.py apply` from a proposal.
- **`update.py`:** after an update, offer the one-off migration of `settings.json` `people.added` / `people.hidden` into the register (today only cx-setup offers it: `propose.py people migrate`, run again after "apply" to clear the old lists).
- **`doctor.py`:** a check that `people-register.md` exists and parses (`propose.people_parse`), and a note when `settings.json` still holds `people.added` names.
- **Overlap to expect at merge** (shared dashboard code, single-token edits): `go()`, `parseHash`, `hashOf`, `navState`, `refreshAll`, `OPENERS`, the Work owner and Made by cells, `viewVal`, `revDetail`'s owner names, `ckItems`, the rail, and the end of `collect()` (`people_register`, `leads`). New code is in the `/* ===== People (BL-55, BL-56) ===== */` blocks.

**Done at merge (2026-10-07):** all three, in the main checkout's merge: the live server may read the register; `doctor.py` checks it ("People register": fails only when the file has no People table; notes names still in `settings.json`); `update.py` passes that note on after an install. Tests in `test_people.py` (`HandOffs`).
