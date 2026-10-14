# Sprint: Panel and header (BL-78 to BL-82)

Branch `sprint-panel-header`, worktree `../creaite-panel-header`. It starts from the tip of `sprint-today-brief` (which holds BL-69 to BL-77) plus `main`'s backlog, so merging this branch also brings BL-76 and BL-77. Nothing else is running. Read BL-78 to BL-82 in `dev/BACKLOG.md` first; they hold Alan's decisions.

## Goal

Quieter, more comfortable editing and a tidier frame:
- the side panel saves and closes with ⌘/Ctrl+Enter, and widens to half the page while editing;
- the header keeps the search left and puts Ask creaite and the theme button at the right edge;
- the rail's Live indicator is the dot alone, with the hover text kept;
- the Today headings are bold.

## Order

Build in this order and commit each item separately: **BL-81, BL-82, BL-79, BL-78, BL-80**. All five are in `dashboard.html`, so they run one after another in this one worktree.
- BL-81, BL-82 and BL-79 are small CSS changes in the frame and on Today. BL-81 and BL-82 come first because BL-81 fixes a side effect of BL-71 and BL-82 changes BL-71's indicator.
- BL-78 and BL-80 are the side panel. BL-78 first, because after BL-78 a successful save closes the panel, and BL-80 then only has to widen it while editing and put it back.

## Items

### 1. BL-81: Header buttons at the right edge (S)

- **The cause (found by reading the styles):** `.status` carried `margin-left: auto`; BL-71 hides it when empty (`.status:empty{display:none}`), so Ask creaite and the theme button follow the search box.
- **The change:** `#askBtn` gets `margin-left: auto`, so the group sits at the right edge with or without the strip. When the strip shows it goes just before Ask creaite, and the group's auto margin belongs to the strip, not to both (`.status:not(:empty) + #askBtn{margin-left:0}`), so the free space isn't split in two.
- **Unchanged:** the search box (left, grows to 520px, ⌘K hint), the bar's height and colours, the alert banner. On a window too narrow for all three the bar wraps and the buttons stay right-aligned.
- **Test:** in `test_today_brief.py`, the theme button's right edge is the bar's right edge with the strip empty and with it showing, Ask creaite sits just left of it, and the search box's left edge is unchanged.
- **Docs:** the spec's BL-71 line about the top bar.

### 2. BL-82: Live indicator is the dot alone (S)

- **The dot:** about 12px, centred under Settings, no word. Remove `.rlw` and the line in `railLive()` that sets it.
- **Not colour alone:** solid dot (`--ok`) when running, hollow ring (`--bad` outline, transparent centre) when stopped. The accessible label and the hover text are exactly as BL-71 set them.
- **Click and keyboard:** unchanged (red checks again, green opens Settings › Live server and backups; Enter and Space work; focus ring). The target stays as wide as the rail's buttons and at least 30px tall.
- **Contrast:** 3:1 for the dot and the ring against the rail in every theme and mode.
- **Tests:** change the BL-71 tests in `test_today_brief.py` that read the word. They check the accessible label, the hover text, no visible word, the shape (filled or hollow) and the contrast.
- **Docs:** the spec's BL-71 section says "always with the word"; change it.

### 3. BL-79: Today headings bold (S)

- **The cause:** in Brightwater a general rule (`:root[data-palette="Brightwater"] h2`, weight 500) outranks `.th` (600); Minimals sets `h2` to 600.
- **The change:** the five headings use weight 700 in every theme and mode, by a rule that is more specific than the theme rules. Size, capitals and letter-spacing stay. Counts, links and sentences stay.
- **Check by eye in Brightwater** (the design system says ABC Diatype has no bold cut): if 700 looks smeared, use the heaviest real weight with the larger size and full-strength ink, and say so in the commit message.
- **Contrast and layout:** unchanged contrast; a bold heading doesn't wrap its count at narrow widths.
- **Test:** the computed weight of each Today heading is 700 under each theme, light and dark, in `test_today_brief.py`.
- **Docs:** the spec's Today headings.

### 4. BL-78: ⌘/Ctrl+Enter saves and closes the side panel (S)

- **One handler** on `document` (keydown): ⌘+Enter on a Mac, Ctrl+Enter elsewhere, while the panel is open and in a form (`EDITING && CUR`), from any field in the panel. It ignores key repeat and a save already running (`CUR.saving`), and it never fires from the Ask creaite box, the Current state editor, a dialog or ⌘K.
- **It runs the panel's own Save,** with the same checks, then closes the panel (`savePanel(approve, closeAfter)`):
  - **Record** (action, RAID item, decision): after a successful save, or with nothing changed, the panel closes instead of returning to its read view. The button's behaviour is unchanged.
  - **New item, proposal, health, milestone (edit, add, rebaseline):** they already close on success.
  - **A failed check** (missing field, bad date, closed workstream) or a question (a new owner, a new workstream) leaves the panel open with the message and the cursor on the field.
  - **A proposal in Review:** Save only, never "Save and approve".
- **Plain Enter keeps its meaning:** a new line in a text area; picking the highlighted person in the owner combo box (the combo ignores Enter when ⌘ or Ctrl is held, so the shortcut saves).
- **Not in the read view.** Nothing happens before Edit.
- **Footer hint:** "⌘↵ saves and closes · Esc cancels" ("Ctrl↵" on Windows) under the buttons in every editing form. Help's keyboard list and the ⌘K shortcut list include it.
- **Tests:** `test_dashboard_editing.py` and `test_dashboard_milestones.py` (one per kind of panel: it saves and closes; a failed check leaves it open; no change just closes; a second press doesn't save twice), plus a real-browser test (`dev/tools/cdp.py`) that presses the real key.

### 5. BL-80: The side panel widens to half the page while editing (S)

- **The change:** while the panel shows a form (`EDITING`), it takes the class `wide`: width `max(420px, 50vw)` (`max(360px, 50vw)` under 1100px). Reading stays 420px (360px). `drawPanel` sets and removes the class (so Edit, Cancel, Save and a new item all follow), and `closePanel` removes it. The existing 0.15s width transition is reused; the panel's inner width follows it.
- **The list beside it** narrows to the left half and keeps its place; the selected row stays in view.
- **Ask creaite open too:** the chat is a fixed panel on the right edge; when it is open the wide panel sits to its left (`body:has(#chat.on) .panel.wide{margin-right:var(--chatw)}`), so neither covers the other.
- **Not changed:** the read view, the Current state editor on the project page, the form's fields and order.
- **Tests:** in a real browser (`dev/tools/cdp.py`): the panel is 420px reading and half the window editing for each kind of panel; it returns on Save, Cancel and Esc; the width at 1400px, 1000px and 700px; and with the chat open, the two don't overlap.
- **Docs:** the spec's side-panel section.

## Boundaries

- **Shared files:** this sprint may edit `dashboard.html`, `help.md`, `dev/dashboard-spec.md` and the dashboard tests. It doesn't touch the scripts, the schema or `creaite-rules.md`.
- **Development guard:** sample data only; temp vaults for tests.
- **Docs:** `BACKLOG.md` and `BRD.md` stay as they are; they are updated at merge. Add a short "Panel and header" section to `dev/BUILD.md`.
- **Don't reformat unrelated lines.** New code goes in marked sections (`/* BL-78 */` and so on).

## Done when

**Tests:** each item's tests above pass in headless Chrome, in all three themes and both modes where colour is involved; the full suite passes: `python3 dev/tools/run_tests.py`.

**Docs:** the spec, Help and `dev/BUILD.md` updated.

**Commits:** each item committed separately on `sprint-panel-header`, with the attribution line from the session's instructions. Never push or merge.

## Hand-offs

- **BL-79 in Brightwater:** if the bold looks wrong in ABC Diatype, Alan decides between 700 and the heaviest real weight.
- **BL-80 below 640px:** the panel keeps `max(360px, 50vw)`; whether it should take the whole width on a phone-sized window is left open.
