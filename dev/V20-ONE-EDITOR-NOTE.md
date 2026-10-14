# v20-one-editor: BL-301 part A, the one editor

For Team 1 (taking v2.0.0 over). Branch `v20-one-editor`, from `origin/release-192`, with `origin/v20-tiptap-vendor`
merged (a66c6e4). Team 2 started it on 14-10-2026. **This is the handover document; it is kept up to date at each
commit.**

## State at this commit

| | |
|---|---|
| The gate | **Passes.** Round-trip gate on the vendored module: current 7/7, fixtures 18/18 (new group), minutes 25/25, constructs 25/25, hard 69/69, stable 17/17. Through the dashboard's own wrapper: every sample and fixture pane given back unchanged, and written by the exact writer to the same bytes once edited |
| Current state | **Switched** to the one editor (both panes) |
| Peek text fields | **Switched** (plain text): title, latest update / response / reasoning, source, options considered, revisit, client messaging |
| Prep focus notes and questions | **Switched** (plain text, the `TextEditor` block): the Prep page's notes per section and questions, and the Prep popup's shaped notes |
| Draft email preview | **Not switched: option (a), a plain contenteditable, until Alan decides** (below) |
| check.py | OK |
| Tests | `test_block_texteditor` new; the Part A set run and passing (below); test_snapshots: `settings-advanced` fails from the Notes server branch, not Part A |

**Handed over to Team 1 on 14-10-2026; finished by Team 1 on branch `v20-a-finish` the same day.** Left for Part A:
1. **Alan's call on the Draft email preview.** For now it is option (a): `#dePrev` stays a plain `contenteditable`
   (stated in `dev/dashboard-spec.md` and `system/creaite-rules.md`). Option (b) is built only if he chooses it.
2. **Alan's agreement to the changed golden (`work-panel`)** and to keeping plain-text fields plain (both below).
3. Re-run the gate over Alan's real Current states with the dashboard's wrapper (read-only, on laptop 1:
   `python3 dev/tools/tiptap_roundtrip.py --vault <vault> --private --vendored`).
4. Coordinate with BL-304 (`v194-instant`, the peek's optimistic saves) and BL-325 (`v195-design-scale`, shared styles)
   when they land: the peek's fields keep their old commit-on-leave and only the CSS added here touches styles.

Done on `v20-a-finish`:
- `dev/tests/test_block_texteditor.py` (11, Chrome, on a fixture): `TextEditor` is a named textbox
  (`aria-multiline`, `aria-labelledby`, placeholder) on the one editor in its plain form; its text is text, one paragraph
  a line, given back as given; typing fires `onInput`, leaving fires `onCommit`; Enter, ⌘Z and ⌘⇧Z; a one-line box
  refuses Enter; setting `value` by code is quiet; a new value from the store never lands under the cursor. And
  `creaiteEditor` itself: it mounts on the element given and keeps its names; an untouched Markdown text comes back byte
  for byte; an edit fires `input` and is written as Markdown; `edSet` is quiet; `destroy`; `plain` keeps Markdown as text.
  `TextEditor` is now exported from `main.js` (so tests reach it); `globals.json`'s tests list regenerated.
- `TextEditor` added to COMPONENTS.md's blocks table (§ 3).
- `system/creaite-rules.md`'s "One editor" line in Dashboard editing corrected: it named the Draft email preview as on
  Tiptap; it now says the preview stays a plain editable box pending Alan's decision.
- `dev/release-notes/2.0.0.md` created with Part A's line.
- **Tests run here (one Chrome at a time), all pass:** test_work_item_peek, test_cell_edit, the eight test_drafts_*,
  test_help, test_help_loop, test_motion, test_ui_sweep, test_one_editor, test_one_editor_gate, test_prep_view,
  test_prep_shape, test_dashboard_split, test_block_texteditor; check.py OK; typecheck 0.
- **test_snapshots:** `work-panel` passes (its golden was re-recorded on `v20-one-editor`, below). `settings-advanced`
  fails, and **not because of Part A**: the Notes server branch (merged into `v20-base`) added the "Notes folder" setting
  row (`locations.folders.notes`), which renumbers the rows after it. Its golden belongs to that part; not re-recorded here.

### The `work-panel` golden, for Alan

Only the markup of the peek's three text fields changed, and it is the editor's: the title (`#pkTitle`), the source
(`#pkSrcIn`) and the latest update (`#pkDesc`) were `contenteditable="plaintext-only"` holding the bare text; they are
now ProseMirror roots (`class="tiptap … ProseMirror"`, `contenteditable="true"`, `translate="no"`, `tabindex="0"`) with a
`<p>` per line (an empty field is one `<p>` with ProseMirror's `<br class="ProseMirror-trailingBreak">`, and the class
`blank` shows its placeholder). Ids, classes, `data-…` and `aria-…` are unchanged. **Nothing visual moved:** the same
item's peek on the release-192 page and on this one, same vault, at 1400×1000, has every field at the same position and
size to the pixel (title, latest update, labels, chips, Details, tabs, feed), and the screenshots match by eye, focused
and not. The one difference in style: the editor turns off font ligatures (`font-variant-ligatures:none`, Tiptap's
essentials), so a pair like "fi" in a title is drawn as two letters, not joined.

## What was built

- **The wrapper:** `system/templates/dashboard/src/core/editor.js`, `creaiteEditor(el, {features, markdown | html | text, multiline, imageSrc, editorProps, extensions})`.
  - ProseMirror mounts **on the element given** (`{mount: el}`), so its id, classes, `data-…` and `aria-…` stay, and the code and tests that find it keep working.
  - Every change to the document fires an `input` event on it (as a contenteditable did), so each place's own handlers (dirty flags, staging, claim tracking) are unchanged. A quiet change (`ED_QUIET` meta: claim marks put on as it opens, a value set by code) fires nothing and isn't an edit.
  - `value()`: a text nobody changed is given back **as it came**; an edited one is written by the exact writer (`markdownOf`), inside its envelope (line ending, blank lines around it). Claim marks are taken out first.
  - `"plain"` features: paragraphs only, one a line, no Markdown and no marks (for plain-text fields); `multiline: false` makes a one-line field (Enter is the place's own).
  - Helpers: `edOf(el)`, `edValue(el)`, `edSet(el, v)`, `edClaim(el, runs)` (BL-207 marks on text already there), `curDrop()` (ends Current state editing and destroys its editors; the one way `shared.CURED` is cleared).
  - `ClaimMark`: BL-207's sentence marks as a ProseMirror mark (`span.claim[data-c]`), with a mark view that ignores the page's painting (classes, title), so `claimPaint` and the evidence panel work unchanged.
  - Pictures (BL-63): the image node drawn as before (`figure.cimg`, an editable caption that is the alt text, ×).
- **The bundle:** `dev/tiptap/editor.js` exports `Extension, Mark, Node, mergeAttributes, Plugin, PluginKey` too, `createEditor` takes `html`, `json`, `extensions` and Tiptap's own options, and there is a `plain` feature set. Rebuilt with `tiptap.py vendor` (499.1 KiB, 157.8 KiB gzipped); `vendor --check` and the gate pass.
- **The page:** `build_dashboard_js.py` maps `"tiptap"` to the vendored module (beside `dashboard/`, as Preact is) and writes Tiptap's one `"</body>"` string as `"<\/body>"`, so the page has one `</body>` (test helpers find the page's end by it). Page size: about 2.8 MB (was about 2.3 MB).
- **Current state** (`projects.js`):
  - Each pane is the one editor (`curAttach`), made from its Markdown (`shared.CURED.src1`, `src2`) and **kept across re-renders** (moved into the redrawn card), so undo history survives Check, Make it executive and the evidence panel.
  - Save path unchanged (`saveCurEdit` → `saveCurrent`); the text is `joinPanes(edValue(left), edValue(right))`, so an unchanged pane saves byte for byte (before, `htmlToMd` rewrote it).
  - Toolbar on Tiptap commands (`RTE_RUN`); link box as before; ⌘↵, Esc, ⌘K, ⌘⇧X, Tab and ⇧Tab in lists unchanged; ⌘B, ⌘I, ⌘Z, ⌘⇧Z are the editor's.
  - Paste keeps only what Current state supports (`transformPastedHTML` through `htmlToMd`/`mdHtml`, as before); pasted or dropped pictures go through `insertImage`, now an editor insert.
  - Generate and "Use this version" load the draft into the editor (`curLoad`), and `claimsInit("ed")` wraps the claims in a template and gives it back to the editor quietly. `claimsMatch` and `claimsAdopt` put marks on existing text with `edClaim` (no re-parse, so the written forms stay).
  - HTML comments (the pane marker, the template's guidance) are kept by the hidden node, byte for byte, and hidden by CSS.
- **CSS:** Tiptap's essentials (its stylesheet isn't injected), hidden comments, `.pked.blank` placeholder.

## Tests

- New `dev/tests/test_one_editor_gate.py`: the gate on the vendored module (current, fixtures, hard) and through the dashboard's wrapper. **If it fails, no editor may switch.**
- New gate group `fixtures` and `--vendored` in `dev/tools/tiptap_roundtrip.py`.
- Updated: `test_dashboard_editing` (sets the editor's content, not `innerHTML`), `test_pages` (reads the right pane with `edValue`), `test_dashboard_split` (copies `vendor/tiptap` beside the source).
- Passing at this commit: test_current_state_live, test_evidence, test_dashboard_editing, test_pages, test_current_state_title, test_status_live_browser, test_vendor_tiptap, test_tiptap_roundtrip, test_dashboard_split, test_one_editor_gate.
- New `dev/tests/test_one_editor.py` (10, Chrome against the live server): Current state's panes are the one editor and named for screen readers; opening and saving unchanged writes nothing; a small edit saves everything else byte for byte (italic with `*`, an entity, a nested numbered list, a bare link, a hidden comment, the pane marker); ⌘Z and ⌘⇧Z; ⌘B and the list button; Esc asks first; 320px, dark theme, reduced motion; every peek text field is the one editor as plain text; the latest update is staged exactly as typed, with Undo in the field; Enter ends the title and Esc puts it back.
- Also updated: `test_work_item_peek` (the title is the one editor), `test_prep_view` and `test_prep_shape` (the boxes are `.ppbox` and `.shbox`, not textareas).
- **Golden changed (needs Alan's agreement, COMPONENTS.md § 6):** `dev/tests/snapshots/work-panel.html` only: the peek's title, source and latest update are now the editor's markup (`contenteditable="true"`, `class="tiptap … ProseMirror"`, a `<p>` per line).
- Passing at this commit: test_one_editor, test_one_editor_gate, test_current_state_live, test_current_state_title, test_work_item_peek, test_cell_edit, test_drafts_agenda, test_drafts_client, test_drafts_email, test_drafts_forms, test_drafts_reason, test_drafts_scaffold, test_drafts_thinking, test_drafts_update, test_dashboard_editing, test_snapshots, test_dashboard_split, test_help, test_help_loop, test_motion, test_ui_sweep, test_panel_drafts, test_evidence, test_prep_view, test_prep_shape, test_prep_popup, test_chat_and_sweep, test_dashboard_milestones, test_status_live_browser, test_pages, test_vendor_tiptap, test_tiptap_roundtrip. Help and `dev/dashboard-spec.md` updated.

## Decision needed: the Draft email preview (option (a) for now)

`#dePrev` (drafts.js) is **not Markdown**: it is the email as styled HTML (inline styles, a table of actions per owner),
and Copy email puts that HTML on the clipboard so Outlook pastes the table and the colours. Tiptap's schema keeps
neither inline styles nor that table, so switching it as it is would change what is copied. Options: (a) leave it a
plain contenteditable (as now) until BL-224 is redrawn; (b) a Tiptap "email" feature set whose nodes keep their `style`
and a table node, with getHTML on copy. Left as (a) here.

## A call made here, for Alan to confirm: plain-text fields stay plain text

The peek's fields and Prep's boxes are stored as plain text and shown as plain text everywhere else (Work's table, the
Word reports, the Agendas page). Read as Markdown, a `*` or a leading `1. ` would display as formatting nowhere else
honours. So they use the one editor (the same keys, Undo, screen-reader names and, later, part D's AI bar) in its
`plain` form: one paragraph a line, saved exactly as typed. Making them Markdown is a later, separate change.

## Every editor in the dashboard (the inventory)

| Place | Kind | Part A |
|---|---|---|
| Current state, left and right panes (`#curEd`, `#curEd2`, projects.js) | Markdown, rich | **switched** |
| Peek: title (`#pkTitle`), latest update / response / reasoning (`#pkDesc`), source (`#pkSrcIn`), options considered, revisit, client messaging (`.pk-vtext`) (panel.js `pkEdMount`) | plain text | **switched** |
| Prep page: focus notes per section (`pp-n-…`), questions and asks (`pp-q`) (PrepPage.jsx); Prep popup's shaped notes (`shN-…`, PrepShape.jsx) | plain text, one a line | **switched** (`components/TextEditor.jsx`) |
| Draft email preview (`#dePrev`, drafts.js) | styled HTML for Outlook | decision needed |
| Settings text areas | none takes Markdown (only the read-only diagnostics report) | n/a |
| Single-line inputs, chat input, steer notes, milestone notes and descriptions, Shape, Chase pane, Quick capture | plain textareas or inputs, not rich text | not in Part A (Quick capture is replaced by part C) |

## Left for parts B to E

- B: Notes on the project page use `creaiteEditor(el, {features: "notes"})` (the `notes` feature set is in the bundle and gated by the `stable` group).
- C: the capture drawer, the same editor.
- D: AI on selected text: a selection bar over the editor (`editor.state.selection`), suggestions applied as one undoable transaction.
- E: Find updates: reads a note's paragraphs from the document.
