# edit_ai.py: proposed combination (v220-editor-base + ai-117-selection-bar)

PROPOSAL ONLY. Nothing applied, committed or pushed. Base: origin/v220-editor-base 8c58db2d. Incoming: origin/ai-117-selection-bar 1c3e3ee1. Merge base be86e9a2.
Files: `edit_ai-combined.diff` (edit_ai.py, base → proposal), `edit_ai-combined-tests.diff` (dev/tests/test_ai_117.py, ai-117's version → proposal).

## Verdict on client safety
**No client-gated place sees anything new.** The A4 sheet's places (`report` (the client and weekly sheets, ClientView.jsx:101 / WeeklyView), `minutes`, `readonly`) keep their v2.1.0 option sets, format, Markdown rule and prompt. Checked: `context()` output for every report and minutes option is byte-identical to the base version; `readonly` still refuses everything. drafts.py `section_task` (client report section redraft) reads only `OPTIONS[polish|shorter|executive]`, which are unchanged. `project_facts` is untouched (its known gap, all open IDs and owners, remains as shipped; that is #123's `client` place, not this merge).

## What is client-gated
- `PLACES/FORMATS/FORMAT_RULES` for `report`, `minutes`, `readonly`; `OPTIONS` polish, shorter, executive, custom (also used by drafts.py for client report sections).
- New in the proposal: `SHEET_PLACES = ("report","minutes","readonly")`, the named list of places frozen as shipped.

## What ai-117 adds (kept, none reaches a sheet place)
- `notes` option (Format notes) and `_needs_blocks` (refuses one-paragraph Format notes); only notes and current offer it.
- Spelling option removed; every reshape gets the `SPELLING` sentence (except custom).
- Renamed `format` ("Add headings and bold") and `checklist` ("Pull out the tasks"); not offered on sheets.
- Per-place `FORMAT_RULES` (`_MARKDOWN`, `_PLAIN`, `_LINE`), Current state heading shift (`HEAD_SHIFT`, `relevel`, applied in `result()`); relevel is a no-op for sheet places.
- `plain` loses `longer` (narrows). `AI_GROUPS` / `AI_PLACE_TABLE` are JS-only (aiEdit.js).

## Hunk decisions
1. **OPTIONS conflict:** keep both: base `polish` + ai-117 `notes`. (`spelling` removal and the two renames auto-merge from ai-117; no sheet place uses them.)
2. **PLACES/FORMATS conflict:** ai-117's five editor places + base's `report`, `minutes`, `readonly` verbatim; base `FORMATS` (all eight). Then `SHEET_PLACES`, ai-117's `SPELLING`, `_MARKDOWN/_PLAIN/_LINE`, and a new `_SHEET_MARKDOWN` = the shipped markdown rule word for word (tasks empty).
3. **FORMAT_RULES (auto-merged, would have broken):** ai-117 re-keyed it by place and `context()` reads `FORMAT_RULES[place]`, so the merged file would KeyError on report/minutes. Added `report`/`minutes` → `_SHEET_MARKDOWN`, `readonly` → `_PLAIN` (identical to shipped plain).
4. **context() spelling sentence (auto-merged, would have widened the prompt):** ai-117 appended `SPELLING` to every non-custom option, including the sheet's. **Flagged and gated:** `if option != "custom" and place not in SHEET_PLACES`. Not a data leak, but a change to the shipped client-sheet prompt; kept out.
5. Comment block above PLACES: notes the sheet places and SHEET_PLACES.
Other conflicts (dashboard.html, Menu.jsx, aiEdit.js, guide-how-to.html) left alone.

## aiEdit.js must change to stay in step (not edited; lines are ai-117's file, merge-in-progress lines in brackets)
- **AI_OPTIONS (l.28-29 [28-36]):** take ai-117's renamed `format`/`checklist`, drop `spelling`, **keep base `polish`**, keep `notes`.
- **AI_PLACES (l.38-45 [46-61]):** union: ai-117's five + base `report`, `minutes`, `readonly` lines verbatim (test_ai_select parity).
- **AI_GROUPS (l.47-53):** add `report: [["Improve", ["shorter","executive","polish"]]]`, `minutes` the same, `readonly: []`. Without them AiSelect.jsx l.85 falls back to `AI_GROUPS.plain` and would show Rewrite clearly on a sheet (server refuses it, but the UI would offer an unshipped option).
- **AI_PLACE_TABLE (l.60-66):** add `report`, `minutes`, `readonly`: `{ai:true, turnInto:false, formatNotes:false, improveOnly:false}`. Without them `aiPlaceOn` is false and `aiAttach` (l.139) / Alt+/ (l.189) return early: **the sheets lose their AI bar and Find the source** (a regression, not a leak).
- **Names:** the grouped bar uses `AI_OPTIONS[id][0]` (AiSelect.jsx l.85-86), not base's `AI_NAMES` ("Shorten" on sheets, [l.89]); either route the groups through AI_NAMES or accept "Shorter" there (test_report_editor AiPlaceTests pins `aiItems` names, which still use AI_NAMES, [l.148]).
- Keep `turnOn` (AiSelect l.80) gated on `features === "notes"`; sheets never get Turn into.

## Tests (diff, not applied)
test_ai_117.py: PLACES now eight; spelling test skips SHEET_PLACES; new `test_the_sheets_places_stay_exactly_as_v210_shipped` (option sets, formats, exact shipped rule, no spelling sentence, every #117 option refused on sheets, no relevel); place-table browser test allows the three sheet rows and asserts them on with no Turn into/Format notes.

## Verification (scratch copy in a throwaway worktree, CREAITE_NOW="2026-10-16 09:30", one at a time; worktree then reset and removed)
test_ai_117.TheServerSide 7 OK; test_ai_select.TheScript 8 OK; test_drafts_report 20 OK; test_client_leak 14 OK; test_client_item_links 9 OK (8 skipped). Browser tests (Bar117, AiOnSelection, test_report_editor AiPlaceTests) not run: aiEdit.js and dashboard.html are still conflicted. TheScript's JS parity check passed only because both conflict sides of aiEdit.js were present; it needs the union above once JS is resolved.
