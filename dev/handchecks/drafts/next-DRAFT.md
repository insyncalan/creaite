# DRAFT, held: hand checks for the release after 2.4.0 (editable Side by side, #230)

Written 18-10-2026 from Stark's report on branch p241-sbs (45741385). Needs Cap's client-leak re-review before it ships. Test file for the board: `dev/tests/test_sbs_panes.py` (13 tests; 12 failed on the old code). Hand checks never hold a release.

| # | Check | Kind | Test (p241-sbs, `dev/tests/test_sbs_panes.py`) |
|---|---|---|---|
| 1 | In Side by side each pane saves its own report; the save line reads "Saved · version 2 · Client: Saved · version 1" | scriptable | `test_sbs_a_*` (3) |
| 2 | No cross-talk between panes: ids are unique, the AI bar, the section menu's focus and the shortcuts belong to their own pane; zoom is one shared control | scriptable | `test_sbs_b_*` (7), `test_sbs_b_no_cross_talk_zoom_is_one_shared_control` |
| 3 | Esc closes only the active pane's menu | scriptable | the Esc test in `test_sbs_c_*` |
| 4 | The panes scroll together | scriptable | `test_sbs_d_scroll_together` |
| 5 | Nothing from the internal pane reaches client output (the client pane, its draft, HTML or Word); it arrives only through Match internal or "Add to the client report" | scriptable | `test_sbs_e_*` |
| 6 | ⌘S saves only the pane in focus (both when the focus is in the toolbar); "Add a text section below" adds to its own pane; moving a section puts focus on that pane's handle | scriptable | `test_sbs_*` (named by Stark) |
| 7 | An approved internal report does not lock the client page; after Match internal the client pane autosaves | scriptable | named by Stark |
| 8 | The ✦ in each pane works | judgement | wired, no dedicated test |
