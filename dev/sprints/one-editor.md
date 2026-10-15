# One editor, everywhere

**Status:** design note, confirmed by Alan 15-10-2026 ("confirm these two profiles"). Written by the Product Manager session. Mockups: `dev/mockups/notes-editor-mockup.html`, `notes-ai-bar-mockup.html`, `editor-link-mockup.html`, `notes-header-mockup.html`.

## The rule

Every place the dashboard edits text uses one editor, `creaiteEditor` (core/editor.js). It has two profiles. A feature that is in a profile works the same in every place that profile is used (Alan: "all editors should be consistent; the positive things in Notes need to be everywhere").

## The profiles

**Rich** (code profiles `notes` and `current`): Notes and the capture drawer; Current state (two panes); the weekly and client report sheets where a field is rich (`SheetText.jsx` already calls `creaiteEditor` with `current`).
**Plain** (code profile `plain`): the item panel's free-text fields, Prep notes, draft boxes (`panel.js`, `TextEditor.jsx`).
**Outside both:** the minutes view's own line editing (it feeds work items); fields that are keys or short labels (IDs, dates, titles used as keys).

## Feature matrix

| Feature | Rich | Plain | Item |
|---|---|---|---|
| Formatting bar: H1 to H3, B, I, S, lists, checklist, quote, link, `[[` `@` `#` | Yes | No | foundation |
| `/` menu at the caret, grouped, filtered, with descriptions | Yes | No | foundation |
| Aligned checklist (18px box on the first line) | Yes | n/a | foundation |
| Heading 1 to 3 | Yes | n/a | foundation |
| Work-item link as `ID · Designation: title` (only the ID linked) | Yes | n/a | foundation |
| Selected-text bar: margin sparkle, hover groups, Ask | Yes | Yes (Improve and Ask only) | #117 |
| Turn into (instant, no AI, Undo) and Format notes | Yes | No | #117 |
| Link control (button, `/`, Cmd+Shift+K, paste) | Yes | Yes (corner button, paste, key) | #120; plain: v2.2.0 item |
| Expand to focus (modal over the page) | Yes | No | #115 |
| Autosave about 2 s, "Saved 14:02" | Notes only | n/a | #119 |
| Save and proposal flow | Current state, sheets keep theirs | item fields keep theirs | unchanged |
| Find updates | Notes only | n/a | unchanged |

## Build sequence (all touch core/editor.js: not in parallel)

1. Foundation: the profiles, toolbar, `/` menu, aligned checklist, headings, item links (v2.1.0).
2. Selected-text bar, rich profile (#117, v2.1.0); the plain profile's Improve and Ask follow (v2.2.0 if needed, Alan accepts).
3. Links (#120, v2.1.0 rich) and focus mode (#115).
4. v2.2.0: the plain profile's bar and links, and any sheet that needs more than it gets.

## Risks (to be checked against Team Stark's engineering input)

- Current state and the sheets save through proposals or their own save: the new bar and `/` menu must not change when or how they save.
- The sheets set their own frame (`ED_QUIET`, `editorProps`): the toolbar, `/` menu and selection bar must not fight it.
- Heading levels and the Markdown round trip (BL-301's gate); the Find updates line mapping reads headings and links.
- Plain fields store plain text: links there are v2.2.0 and need every place that shows text to render them (see the v2.2.0 links item).
