# #362 persisted and sent paths for a confidential meeting's project

Question (Jarvis, 25-10-2026): does anything persisted or sent take the project from `prep_entry` for a confidential meeting?
`prep_entry` keeps the project guess so Alan's own Prep screen can be shaped from the text and the tracker (BL-301). Findings:

| Path | Persisted or sent | Uses the entry's project | Result |
|------|-------------------|--------------------------|--------|
| Today, Prep screen, Week ahead (`D.prep.meetings`) | screen only | yes, a guess shown to Alan | unchanged |
| `prep_page.context` | built on demand, feeds everything below | through `_project_of` | **fixed**: a confidential meeting's project counts only when Alan chose it (a remembered series, how "remembered"); a guess gives the all-projects view with `chosen` false |
| Prep page file in the project's Agendas folder (`prep_page.save`, `place`; may be shared OneDrive) | persisted | through `context` | **was a leak path, fixed**: an unchosen confidential page now files in the portfolio folder |
| `prep-pages.json` (path, key, day) | persisted, local | through the page's path | fixed with the file |
| Stored content (`prep_view.store`: `project`, context, reply; staging) | persisted, local | through `context` | fixed |
| Research prompt of the Prep page run (`live_server.prep_run`), Shape the meeting (`prep_shape`), agenda and one-pager drafts (`drafts.py`), the focus filter | sent to Claude | through `context` | fixed: an unchosen confidential meeting sends the all-projects view and no project name; the invite is title and times only; a confidential note stays held back as before |
| Prep popup "Draft the one-pager" and "client-safe one-pager" (`projects.js`; ask creaite gets `steerco one-pager <code>`, `cx-steerco` drafts to `system/staging/drafts/`, filed in the project's Steerco folder, maybe shared OneDrive, only on Alan's approval) | sent to Claude, persisted on approval | the entry's project (`m.p`) | **was a guess path, fixed**: the buttons are not offered for a confidential meeting unless Alan chose the project (`how` remembered or chosen); he can still say it in the chat |
| Hub records (`meeting_hub`), next-day list, set-aside lists, `day_close`, `capture.meeting` | persisted or shown in lists | no | `p=None` (v266-sec362) |
| Note for this meeting drawer (`capture.meeting`, `openCapture`) | shown, then saved into a project's notes folder | no | no project preselected for an unchosen confidential meeting; only a remembered series (#343) |
| `dashboard.html`, `system/history/` snapshots | persisted, local, never synced or sent | yes, the guess | accepted: they hold every project's data anyway |
| Search index, tracker, staging proposals, Excel export | not written from the entry | no | none |

No change to a guarded file was needed: all consumers go through `prep_page.context`, so `live_server.py` (guarded, read only here)
needs no patch. Tests: `dev/tests/test_confidential_persisted.py`.
