# Alan's morning list, 17-10-2026 (updated 07:00)

v2.1.0 is published: you approved F1, the client gate fix (127d), the Reports icon and the Help patch went in, and your hand checks passed. Nothing gates a release this morning. These are the only things waiting on you, one line each with my recommendation.

## Guarded changes that only you can approve (nothing is applied until you do)

1. **#117, the combined edit_ai.py** (branch edit-ai-proposal 4762f76f). Team Stark merged the 2.1.0 side (the client-gated report, minutes and read-only places) with the selection bar's additions as a diff only. Their claim: no client-gated place sees anything new, every report and minutes option builds a byte-identical prompt, and a new test pins the sheet places. Recommend: approve, once Jarvis confirms the byte-identical claim on the diff.
2. **#119, notes autosave: one scope ruling and three guard points.** The page half is ready; the server half (branch notes-119-proposal, +22/-48 in live_server.py, one backup per editing session in filechange.py) needs you.
   - **Scope:** Team Cap's review says the pair also carries focus mode (#136: the expand icon, the scrim, the Leave dialog and the closing rules, about 300 lines), which the brief said to leave out. Recommend: keep it. #136 is in 2.2.0 anyway, and taking it out is rework.
   - **The approval limit:** with an ask run in progress, the 11th note save in a row returns "Needs approval" and your typing stays unsaved until the run ends. The smallest safe fix is own=True on the notes save route. Recommend: yes, otherwise autosave stops working during any ask run.
   - **Three smaller points before you approve the filechange hunk:** one Undo undoes a whole editing session (no cap on its length), every autosave still adds an Activity row, and old draft files are never cleaned up. Recommend: approve, and put the session cap and the clean-up in a follow-up.
   - **The save line:** "Saving…" while you type, not "Editing". Recommend: keep "Saving…". Also yes or no on a leave-the-page warning if something is unsaved (Cap's beforeunload guard): recommend yes.
3. **#146, one line in live_server.py (SAFE_SETTINGS):** add sweep.max_lookback_days beside sweep.first_run_lookback_days, so ask creaite can change your three-day sweep cap. Recommend: yes, it is a plain number.

## Scope

4. **#158, Help's word budget.** Help is at 23,260 words (33,506 at the start) against your 14,791 target, and the pages left are at the floor: cutting more drops true facts. Recommend: relax the target to about 22,000 for 2.2.0 and trim the biggest Reference pages in 2.2.1.

## Quick picks (no rush)

5. **Work filters** (the UX review's finding 1): open dev/mockups/work-filters-mockup.html. A is a views row plus one refine row; B is one row with the view in a menu. Recommend A.
6. **Review's "Stale · 12 days" on every row** (finding 2): open dev/mockups/review-stale-mockup.html. A shows age quietly and flags only the outlier; B groups by age. Recommend A.
7. **#172, the UX review item:** Jarvis will ask whether "log it as backlog, low priority" meant the whole review (one umbrella item) or only part of it. Recommend: the whole review, as one item.
8. **The Capture drawer still says "Draft saved":** keep the drawer's draft, or drop it too, as with notes? Recommend: keep it (a drawer note can be abandoned, a note is a file).
