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

## Engineering input (Team Stark, 15-10-2026, #117 comment 6199944717) and what it changes

- **The chrome is page-owned.** `core/editor.js` shares only the schema, load and save, claim marks, the image figure and the AI hook. The toolbar, `/` menu, pickers, item chips and link control belong to each host, in two separate copies (Notes: `NoteEditor.jsx`; Current state: `projects.js`). The foundation therefore lifts the chrome into a shared layer, driven by a host-level *chrome profile* (`rich`, `plain`, `sheet`, `none`) kept separate from the schema profile. Changing a schema means rebuilding the vendored Tiptap bundle (`dev/tiptap/editor.js`).
- **Current state is stored under `## Current state` in the project CLAUDE.md** and read to the next `## `; Word renders only `###`. Headings there need a level mapping (open question 1).
- **Plain fields are plain text** in tracker.db, Excel and reports: headings, checklists and links need a storage and rendering change (v2.2.0).
- **The `/` menu bug** (from code, not reproduced): its height is measured from `.ndoc` but it is placed inside `.ned`, so it drops by the header's height and never flips; fix by placing it fixed, as the AI bar does.
- **Cmd+K and Cmd+Shift+K both belong to the command palette**; the link shortcut in the mockup will not work as drawn. Current state already has Link and Unlink (https, http, mailto only); its tooltip "(Cmd+K)" is wrong today.
- **Draft email is not on the editor** (a raw contenteditable); the `email` AI place has no host.
- **Client-safe leak on the client sheet (v2.1.0 branches):** the AI facts send every open item ID and owner, not only client-visible ones. Separate opus item raised by Jarvis; every new AI action widens it, so a client-safe AI place comes first.
- **Build order** (one stream, each step touches core/editor.js): A profiles, toolbar and checklist; B `/` menu and headings; C item links; then the selection bar (#117); then links (#120); then focus mode (#115). The plain profile, Draft email and any sheet needing more go to v2.2.0.
- **Fragile things to keep green:** the round trip (`value()` returns the original when untouched; chrome must not dispatch a non-quiet transaction on mount), Cmd+Enter, the Esc layers, Alt+/, Cmd+Z with the Undo toast, autosize, claim marks (no text nodes inside `.ProseMirror`), paste, the forced-colours rules.

## Decisions for Alan (recommendations in each)

1. **Current state headings:** three levels stored as `###`, `####`, `#####` (Word learns the two deeper ones). *Recommended.* Alternative: one level.
2. **Plain fields:** links stored as Markdown in the existing text; every place that shows text renders them (v2.2.0 item). Headings and checklists stay out of plain fields. *Recommended.*
3. **Checklist in Current state:** yes, in v2.2.0 (needs a bundle rebuild and Word rendering).
4. **Report sheets:** the selection bar and Turn into in v2.1.0; the full toolbar and `/` menu in v2.2.0; the client sheet gets a client-safe AI place first (client-visible items only, no owners).
5. **Capture drawer:** the rich chrome (toolbar, `/`, pickers) in v2.1.0 because the shared layer makes it cheap; its AI bar in v2.2.0.
6. **Link shortcut:** keep Cmd+K as the palette; make the palette ignore Shift and use Cmd+Shift+K for links inside editors.
7. **Focus mode:** Notes and Current state (the long-form editors), not the item fields.
8. **`#` text:** the same `ID · Designation: title` in every rich editor; Word and the export write it as plain text; the client sheet offers client-visible items only.
