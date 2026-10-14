# Sprint: Insight and capture (BL-51, BL-49, BL-54)

Branch `sprint-insight`, worktree `../creaite-insight`. Runs in parallel with `sprint-people` (`../creaite-people`) and `sprint-live-vault` (`../creaite-live`). Read the full item write-ups in `dev/BACKLOG.md` first; they hold Alan's decisions.

## Goal

Trouble shows before it's reported, Alan walks into each meeting knowing what's open, and conversations without a transcript still reach the tracker, all ready for the live trial.

## Items

1. **BL-51 Early warnings.** Read-only signals worked out at build time from data already held (never stored as tracker rows): an action re-dated 3 or more times (`change_log`); the same risk raised in several meetings or sweeps with no response; a milestone forecast slipping in successive weeks; actions open far longer than the project's usual. Shown as a flag on the item (reason on hover) and on the project page; feed BL-52's health evidence and the weekly report's draft (`report.py`). Each signal can be switched off and its threshold set in Settings (`settings.json` `warnings`). **Leave out** the key-person signal (it needs sprint-people's register); note it under "Hand-offs".
2. **BL-49 Meeting prep.** A Prep link on each meeting in Today's day view, opening a short brief for the meeting's project: open actions (overdue first), risks and issues with no response, decisions since the last meeting in the same series (from `processed.txt`, else 7 days), and BL-51's warnings. Match the meeting to a project by title and the register's signals; Alan can pick the project if unsure and creaite remembers the series. Portfolio meetings get a cross-project brief.
3. **BL-54 Quick capture.** A Quick capture box (Today, and "Quick capture" in ⌘K): rough notes, project (or matched), date, who was there; Process saves the note as `projects/<CODE> <Name>/minutes/YYYY-MM-DD Quick note - <title>.md` (through a new live-server route) and runs cx-minutes on it through the run engine (as the Inbox does), producing proposals in Review, with no Word minutes unless asked. Ask creaite also accepts "note: …". cx-minutes learns short notes as a source.

## Boundaries

- **Owns:** Today (day view and briefing), the project page (cockpit) warning flags, a new warnings section in `build_dashboard.py`, the quick-capture route in `system/scripts/live_server.py`, `report.py`'s draft content, cx-minutes' short-note handling, Settings' new Warnings card.
- **Don't edit:** Settings › People, the owner picker, the People view or rail, `propose.py`, the people parts of the skills (sprint-people owns them), `update.py`, `doctor.py`, `dev/tools/` (sprint-live-vault). If a change there is needed, note it under "Hand-offs".
- **Shared files** (`dashboard.html`, `build_dashboard.py`, `settings.json`, `help.md`, `dev/dashboard-spec.md`, `dev/BACKLOG.md`, `dev/BRD.md`): add new code in its own clearly marked section (`/* ===== Insight (BL-51, BL-49, BL-54) ===== */`), add new data keys at the end of `collect()`'s dict, and don't reformat or reorder existing lines. Leave `BACKLOG.md` and `BRD.md` alone; Claude in the main checkout moves items into the BRD at merge.
- Development guard: sample data only; quick-capture and prep runs are tested with the fake Claude in `dev/tests/test_live_server.py`; never real Microsoft 365.

## Done when

- Tests: each warning signal on constructed history, thresholds and switches; warnings in the health evidence and report draft; a prep brief for a matched and an unsure meeting; quick capture saving the note (name, folder, no overwrite) and starting a run; the views in headless Chrome. The full suite passes in this worktree.
- Help and `dev/dashboard-spec.md` updated; a short "Insight and capture" section added to `dev/BUILD.md`.
- Each item committed separately on `sprint-insight` with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

- BL-51's key-person signal waits for sprint-people's register (BL-55).
- **Outside the listed ownership, needed by BL-51:** repeat mentions weren't recorded anywhere, so `minutes.py stage` and `sweep.py stage` now append to `system/staging/mentions.jsonl` when they skip a duplicate of an open item (`minutes.note_mention`; `paths.MENTIONS`; folder map in `system/creaite-rules.md`). The sweep's `open_items` became a dict to carry the ID. Mentions count only from now on.
- **BL-49's "after the meeting" part is not built:** cx-minutes treating the brief's open items as expected and proposing updates for those discussed. It's in BL-49's write-up but not this sprint's brief; it touches cx-minutes beyond short notes.
- **Settings keys added:** `warnings` (BL-51) and `prep.series` (BL-49) at the end of `settings.json`; `update.py` adds them to a live vault as new keys.
- **Found, not fixed (outside this sprint):** in Work, `document.addEventListener("click",()=>{ $("#ownMenu").classList… $("#colMenu")… })` names elements that no longer exist, so every click logs an uncaught TypeError (harmless otherwise). `dev/tests/test_insight.py` ignores that one error; fix it on main (`?.` or remove the handler) and drop the exception.
- **Shared-file touches:** `dashboard.html` (one Insight section in the CSS and one before start-up; views extended by wrapping their render functions, no existing line changed), `build_dashboard.py` (Insight section at the end, three keys at the end of `collect()`), `live_server.py` (`/api/capture` on its own line after the route table, a `capture` method, `NOTE_LIMIT`), `report.py` (`project_warnings`, two added keys), the cx-weekly-report and cx-minutes skills (non-people parts), `help.md`, `dashboard-spec.md`, `BUILD.md`, the rules' folder map and command table. `BACKLOG.md` and `BRD.md` untouched.
