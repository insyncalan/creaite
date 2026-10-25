# Leak fix: persisted and sent paths for a confidential meeting's project (2.6.5)

Question (Jarvis, 25-10-2026): does anything persisted or sent take a project from the guess in `prep_entry` for a confidential meeting?
`prep_entry` keeps the guess so Alan's own Prep screen can be shaped from the text and the tracker (BL-301). Each row below was
checked against the 2.6.5 code (and by `test_confidential_persisted.py`, `test_confidential_paths.py`,
`test_confidential_end_to_end.py`). A project counts for a confidential meeting only when Alan chose it (a remembered series).

| Path | Persisted or sent | Uses the guess | Result |
|------|-------------------|----------------|--------|
| Today, Prep screen, Week ahead (`D.prep.meetings`), `dashboard.html` and `system/history/` snapshots | screen, local only, never synced or sent | yes, shown to Alan | accepted: the files hold every project's data anyway; `build_dashboard.py` also guesses a project by name for every calendar row it saves to the page (local only) |
| `prep_page.context` (everything below goes through it) | built on demand | no: `_project_of` | **fixed**: a guess gives the all-projects view, `chosen` false |
| Prep page file in the Agendas folder (`prep_page.save`, `place`; may be shared OneDrive) | persisted | no | **was a leak, fixed**: files in the portfolio folder |
| Agenda file (`prep_page.save_agenda`) | persisted | no | **was a leak, fixed**: portfolio folder |
| `prep-pages.json`, `agendas.json` | persisted, local | no | fixed with the files |
| Stored content (`prep_view.store`: `project`, context, reply; staging) | persisted, local | no | fixed |
| Research prompt (`live_server.prep_run`), Shape the meeting, agenda and one-pager drafts (`drafts.py`) | sent to Claude | no | **changed**: Claude gets the all-projects view and is not told which project the meeting is; that view lists every project's items and names, as it does for any meeting with no project. A confidential note stays held back as before |
| Prep popup "Draft the one-pager" and "client-safe one-pager" (`projects.js`) | sent to Claude, filed on approval | no | **fixed**: not offered for a confidential meeting unless the project is remembered or chosen; Alan can still say it in the chat |
| "Note for this meeting" (`capture.meeting`) | the note is filed in the chosen project's notes folder | no | **fixed** (this branch): title and date only, no project, no people |
| Hub records (`meeting_hub`), next-day list (`day_close`), set-aside lists (`_ir_aside_lists`) | shown in lists; day_close keeps references only | no | **fixed** (this branch): `ev_project`, `ev_shown_p`, `row` give none for a confidential meeting |
| Follow-up email draft (`drafts.js`), which takes its project codes from the hub | screen | no, through the hub | follows the hub fix |
| Search index, tracker, staging proposals, Excel export | not written from the entry | no | none |

Known and left: a project's ranking (`prep_page._prep_items`) still uses the invite's words for the all-projects view, so a
confidential title can give an item a reason ("invite mentions ...") in the prompt and the page (Cap's L1); and if
`calendar.json` held an invite body and attendees for a confidential meeting, the context would carry them (today the sweep
stores only title and times, Cap's L3).

No guarded file was needed: all consumers go through `prep_page.context`, so `live_server.py` needs no patch.
