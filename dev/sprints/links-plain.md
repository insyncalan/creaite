# Links in plain text (#121, v2.2.0)

A link in a plain-text field is kept as `[words](address)` and read, wherever the text goes, as the words, as a link where a link can work. #120's one
address validator (`core/linkUrl.js`: http, https and mailto, nothing else, in no disguise) is the only judge of an address in the dashboard. An
address it refuses is not a link: `[words](address)` stays the literal characters, in every place below.

## The form

`[` words `](` address `)`. In the words `[`, `]` and `\` are written `\[`, `\]` and `\\`; an address has no space and its brackets balance one
level deep (`a_(b)`), else they are written `%28` `%29`. Written by `core/linkText.js` (dashboard) and `system/scripts/linktext.py` (everything else).
`linktext.py` cannot call JavaScript, so it holds the validator's rules again for the Python side; it is only ever stricter, and
`test_editor_links_plain.py` (Chrome) runs both on one set of cases to keep it so. Nothing else in Python decides whether an address is a link.

## Where a link can be made (the Link control)

The corner button (while the cursor is in the field), Cmd/Ctrl+Shift+K and a paste, with the same popover as the rich editors. A plain field has
no `/` menu, so that way in does not apply.

| Field | Link control | Why |
|---|---|---|
| Latest update, Response / Resolution, Reasoning (the peek's longer text) | yes | free text |
| Options considered (Details) | yes | free text |
| Client messaging (Details) | yes | free text; the client-safe checks read the address |
| Prep notes and questions (Prep page, the Prep popup's shaped notes) | yes | free text |
| Find updates' one-line value boxes | yes | the same fields |
| Title (the peek's heading) | no | a short label, used as a key in lists, the palette and search |
| Revisit, Source | no | a date or trigger; a reference |
| Owner, status, dates, IDs, labels | no | not text boxes (pickers) or keys |
| Milestone wording, Current state, Notes | n/a | their own editors (#120) |

## Where the text is shown or exported, and how a link reads

| Place | How a link reads | Where | Test |
|---|---|---|---|
| Work tables: the update under an action's title, a risk's Response column | anchor, new tab (`rel="noopener noreferrer"`); a click on it does nothing else | `work.js` `linkHtml` | `test_editor_links_plain.Places` |
| Work sort by Response | the words | `work.js` | " |
| Project page, top risks and issues | anchor | `projects.js` | " |
| Review: a proposed risk's response | anchor | `review.js` | " |
| Review: a proposed change (before → after), the peek's history, Find updates (before → after) | the words | `review.py` `describe`, `panel.js` `pkShort`, `FindUpdates.jsx` | `test_link_text.Places`, `test_editor_links_plain.Places` |
| Today: the "Latest:" line (cut at 140 characters) | the words | `today.js` | `test_editor_links_plain.Places` |
| The peek itself, the Prep boxes | the field's own link (a click shows the popover, never navigates) | `core/editor.js` | `test_editor_links_plain.Editor` |
| Draft email, rich copy | anchor with its colour written in (a mail program drops classes) | `drafts.js` `deLinks` | `test_editor_links_plain.Places` |
| Draft email, plain copy | `words (address)` | `drafts.js` `deTextRows` | " |
| Word reports and client reports (any value filled by `docx_tools.py fill`) | a real hyperlink (the address is in the document's relationships) | `docx_tools.py` `esc_links`, `finish_links` | `test_link_text.WordHyperlinks` |
| Word text preview (`docx_tools.py text`) and the draft checks (`review.draft_lines`) | `words (address)`: the address is read like the words | `docx_tools.py` `show_links` | " |
| One-off Word tables (`report.py adhoc`) | `words (address)` | `report.py` `_adhoc_cell` | `test_link_text.Places` |
| HTML: the prep page | anchor; printed, the address follows the words | `prep_view.py` | " |
| Excel export | the cell holds the words with a hyperlink on it; with several links, `words (address)` and no hyperlink | `excel_sync.py` | `test_link_text.Excel` |
| Excel import | a cell that still says what the export wrote is not a change; a hyperlink is never read | `excel_sync.py` | " |
| Search (`search.py`) | the words are matched, the address never is; Ask's lines show the words | `search.py` | `test_link_text.Search` |
| Activity | the words | `build_dashboard.py` `_act_change` | `test_link_text.Places` |
| Status facts (the executive Current state) | the words | `status_facts.py` | " |
| ask creaite | reads the stored form (it reads files and the tracker); its replies are checked by `claims.py`, not changed here | (not changed) | |

## Client-safe

The confidentiality checks read the stored text, so the address is read like the words: `drafts.secret`, `status_facts.SENSITIVE` and
`review.client_findings` (which reads `review.draft_lines`, now with each hyperlink's address after its words). `test_link_text.Format` shows a
marker in an address is found. Nothing was loosened and no guarded file was changed.

## Not done here

- `live_server.py`'s own text preview of an inbox Word file shows a hyperlink's words only (guarded file).
- A hyperlink in a Word value is made only for a value filled through `docx_tools.py fill` (the report templates); `md_paras` (Current state) still
  writes `words (address)` as text, as #120 left it.
