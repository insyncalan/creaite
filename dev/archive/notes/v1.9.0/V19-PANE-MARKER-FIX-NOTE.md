# v19-pane-marker-fix: a quoted pane marker no longer splits Current state

For the Scrum Master. Branch `v19-pane-marker-fix`, from `origin/main` at `0af493b` (v1.8.0). Not pushed.

## The bug

Found by BL-301's round-trip gate (`dev/DEV-NOTES-TIPTAP-NOTE.md`, on `dev-notes-tiptap`). Current state is stored as two panes split by `<!-- creaite: second pane -->` (BL-89). `system/templates/project-CLAUDE-template.md`'s guidance comment quotes that marker inside itself, so both splitters cut the comment in two: every project made from the template opened with half a comment in each pane.

## The rule (Alan, 13-10-2026)

A marker inside another HTML comment is text, not a split. Only a marker outside every comment counts. The scanner counts comments as they open and close, so the quoted marker's own `-->` doesn't close the comment around it. A stray `-->` can't hide a real marker. An unclosed `<!--` hides any marker after it, as HTML would. Splitting at the first real marker, joining, and dropping further real markers all work as before. For text with no comments, nothing changes, byte for byte. The template text is unchanged, so projects already made from it are fixed too.

## Both splitters, identically

- `system/scripts/docx_tools.py`: new `pane_markers(text)` (where each real marker starts) and `pane_lines(text)` (the lines that are a real marker on their own). `split_panes` uses them. `md_blocks` drops only real marker lines. `md_normalise` no longer treats a paragraph that happens to equal the marker as a trailing marker.
- `system/scripts/report.py`: `current_entries` (the Word report) uses `pane_lines`. `replace_current` decides "the new text carries the marker" with `pane_markers`, not `in`.
- `system/templates/dashboard/src/panel.js`: `paneMarkers`, `paneLines`, and `splitPanes` and `mdBlocks` changed the same way. `joinPanes` is unchanged. `core/globals.json` now lists them for the tests (`build_dashboard_js.py globals`), and `dashboard.html` is rebuilt.
- `dev/dashboard-spec.md`: one sentence on the rule.

Every other place that finds the marker goes through these functions (I checked with grep).

## Tests

- New `dev/tests/test_pane_marker.py`:
  - Python: a quoted marker is ignored; a normal one still splits; the template's own text is one whole left pane, and a real marker after it splits correctly; split then join and `md_normalise` are byte-identical; `md_blocks`, `current_entries` and `replace_current` keep a quoted marker as text.
  - Chrome: the page's `splitPanes` and `paneMarkers` give the same result as Python on the same table of cases; round-trips match; `mdBlocks` has no pane block for a quoted marker; ABC's Current state set to the template's text shows as one pane (`.curpanes.solo`).
- Run and passing: `test_pane_marker` (9), `test_pages` CurrentStateDataTests, CurrentStateReportTests and PanesLive (18), `test_reports` (15), `test_current_state_live` (16), `test_current_state_title`, `test_dashboard_split` (16), `test_snapshots`.
- BL-254 snapshots: no change. No golden shows a template-made Current state.
- `python3.14 dev/tools/check.py`: `check: OK`.

## Release

**Alan (13-10-2026): in v1.9.0** (changed from v1.8.0 the same evening, as v1.8.0 was already being released). It's a small, contained fix, and every project made from the template is affected.
