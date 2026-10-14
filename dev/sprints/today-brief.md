# Sprint: Today as a brief (BL-69 to BL-74, then BL-76 and BL-77)

Branch `sprint-today-brief`, worktree `../creaite-today-brief`. Nothing else is running. Read BL-69 to BL-74, BL-76 and BL-77 in `dev/BACKLOG.md` first; they hold Alan's decisions.

**Where it stands (2026-10-08):** BL-69 to BL-72, BL-73 and BL-74 are built, committed and merged into local `main` (not pushed). BL-76 and BL-77 are attached to this sprint and still to build. Before starting, bring the branch up to date in the worktree: `git merge main`.

## Goal

A quieter dashboard:
- the project page loses its Workstreams card;
- the Inbox screen becomes **Intake**, in three clearly separate sections: Calendar Import, Upload Files and Quick Capture;
- Quick Capture's date comes from a calendar, and its Title box is wider;
- the Live indicator moves to the bottom of the rail, clearing the top bar;
- Today reads like Alan's Morning Brief: one centred column of short numbered sentences with links in them, not boxes;
- two bugs are found and fixed: editing Current state with an image on the project page (BL-76), and the Work filters (BL-77).

## Order

Build in this order and commit each item separately: **BL-69, BL-70, BL-73, BL-74, BL-71, BL-72**. All six are in `dashboard.html`, so they run one after another in this one worktree. BL-73 and BL-74 follow BL-70 because they work on the same Intake screen. BL-72 comes last because it reshapes the Today screen that BL-70 and BL-71 also touch.

**Then, in this order: BL-76, BL-77.** Both are bugs with no symptom named yet, so each starts by reproducing the fault and writing it down. They touch different parts of `dashboard.html` (the Current state editor; the Work filters), so one can't block the other. BL-77 also checks the links from Today into Work, which BL-72 reshaped.

### 1. BL-69: Remove Workstreams from the project page (S)

- **Remove:** the `#wsCard` block and its "Manage workstreams ›" link.
- **Unchanged:** workstreams everywhere else.
- **Docs:** update FR-74 in the BRD and the spec.
- **Test:** change `test_workstreams.py` to check the card is absent.

### 2. BL-70: Inbox screen becomes Intake (S)

- **Defaults confirmed** (BL-70 marks them "to confirm"; take them):
  - the `inbox/` **folder keeps its name**;
  - internal ids and keys stay;
  - `#inbox` still opens the screen, with `#intake` as the new address.
- **Wording changes:** every label Alan reads, including the session-start status line in `session.py` ("N files waiting in Intake (inbox/)").
- **Hint:** the screen's hint explains where files land ("saved to the inbox folder").
- **Docs:** update the docs and skills listed in BL-70, and in `BACKLOG.md` the open items that name the Inbox page (BL-42).

### 3. BL-73: Intake in three sections (S)

- **The three panels, in order,** with the headings exactly as Alan wrote them:
  1. **Calendar Import:** today's Meetings card.
  2. **Upload Files:** the drop zone and the file table, with Select new and Process selected.
  3. **Quick Capture:** the notes box.
- **Each panel:** its own icon, one-line purpose and buttons, with clear gaps between the panels.
- **Defaults confirmed** (take them):
  - the waiting-files table stays in Upload Files;
  - the "From calendar" tag and Calendar Import's "Load into inbox" and "Load and process" buttons come with BL-42 phase 3, which isn't built. Calendar Import shows what exists now: Select new, Process selected, Refresh.
- **Narrow windows:** the panels stack.
- **Themes:** each theme's line and surface colours.

### 4. BL-74: Quick Capture date picker and a wider Title (S)

- **The date:** picked from a calendar, never typed:
  - it reuses the dashboard's existing calendar popup and makes the date field read-only;
  - it is always today when the form opens, and again after Process or Clear;
  - Clear is hidden for this field.
- **Past dates only** (default confirmed): days after today are greyed out.
- **Added to the popup as options, for every date field:** a latest selectable day, a read-only field, and keyboard control (arrow keys, Enter, Escape).
- **Title box:** about 400px wide, wrapping to full width on narrow windows.

### 5. BL-71: Live indicator at the bottom of the rail (S)

- **The indicator:** under Settings, a dot and a word: "Live" or "Stopped", each with a tooltip and an accessible label. Clicking "Stopped" checks again; clicking "Live" opens Settings › Live server and backups.
- **The red alert banner** stays as it is.
- **Top bar:** loses Live, "Swept …" and "Data …". The held count and the vault button stay, shown only when they apply.
- **Dates:** the sweep and data dates move to the indicator's tooltip (the proposal in BL-71; take it).
- **Contrast:** the dot and the word meet contrast in every theme and mode, including the Brightwater rail.
- **Test:** add one that the indicator is in the rail and follows the server's state.

### 6. BL-72: Today in the Morning Brief style (M)

**The reference, made safe first:**
- Alan's original is `~/Downloads/Morning Brief.html`. It holds **real names and client matters**, so it must never be copied into this repo, which is pushed to GitHub and holds sample data only.
- Make `dev/reference/morning-brief-style.html` from it: the same markup, styles and structure, with **every piece of text replaced by fictional content** in the style of the demo (FAL, ORX, MER and TID; Jane Doe, Omar Ali, Sara Example).
- Read the original only to copy its layout and its way of writing. Commit only the fictional copy, and check it with `grep` for any name or company from the original before committing.

**Build:** as BL-72 describes:
- one centred column, 80% wide (full width with gutters below 640px);
- the order: headline band and day line, **Needs attention**, **Your commitments**, **Resolved**, **Week ahead** (to Friday; 8 days on a Friday; weekends only with a meeting, otherwise their due items show on Monday as "due over the weekend"), then **Portfolio**;
- numbered sentence items with bold linked titles and links inside the sentence;
- small uppercase section headings, hairlines between items, no cards;
- the theme's own colours.

Details:
- **Needs attention:** worded from templates in the page, with no model call. Review items are grouped by meeting or sweep. Reminders move in, with their run and dismiss options in a "…" menu. The quiet Approve applies to routine items only. It shows the top five, then "+n more".
- **Data:** `build_dashboard.py` adds what the Week ahead needs: items due per day, milestones, reports due, and the weekend rule. Meetings come from the saved calendar.

**Unchanged:**
- the day line and meeting list;
- the Today ⌘K entry;
- Quick capture, which stays on Intake;
- the schema.

### 7. BL-76: Bug: editing Current state and adding an image (S–M)

Read BL-76 in `dev/BACKLOG.md`; it lists the steps and the cases to cover.
- **First:** reproduce it end to end with the live server running and a real image file, and write down what goes wrong before changing code.
- **Cases:** a large screenshot (over the 2 MB limit), `.png` and `.jpg`, a `.gif`, `.webp` or HEIC (a clear message, not silence), names with spaces or capitals, two images with the same name, and a project with no `images/` folder.
- **Fix rules:** a failure shows a plain message in the editor and keeps Alan's text; nothing is lost on Save or Cancel; the saved text and images match what the card showed, after a reload too.
- **Test:** add one that uses the real live server and a real image file (the existing tests use a stand-in for the file layer).

### 8. BL-77: Bug: Work filters, second review (S–M)

Read BL-77 in `dev/BACKLOG.md`; it lists every filter surface and FR-68's promises.
- **First:** click through each filter surface in the real page, write each fault down, then fix them one at a time.
- **Includes:** the links into Work from Today (the Overdue count and the Needs attention and Your commitments links BL-72 added), a project page, a person and "Open in Work": each lands on the filter it claims, with the same count.
- **State:** Back, forward, refresh and a copied address restore the same filters.
- **Tests:** one per fault, clicking through the real controls (chips, menus, ×, Back); update FR-68 if a promise changes.

## Boundaries

- **Shared files:** this sprint may edit `dashboard.html`, `build_dashboard.py`, `session.py`, `help.md`, `dev/dashboard-spec.md`, `system/creaite-rules.md` (the dashboard wording only) and the skills' wording. For BL-76 and BL-77 also `live_server.py` (the upload route and file rules), `tracker.py` and `docx_tools.py` only if the apply or the Word step is at fault, and the existing dashboard tests. Put new code in marked sections, `/* ===== Today brief (BL-72) ===== */` and so on. Don't reformat unrelated lines.
- **Development guard:** sample data only. Nothing from Alan's real Morning Brief, or any real vault, goes into the repo.
- **Docs:** leave `BACKLOG.md` and `BRD.md` alone except where an item above says to change them (BL-77 may change FR-68). They are updated at merge.

## Done when

**Tests:**
- BL-69: the card is gone, and Settings › Workstreams still works.
- BL-70:
  - the Intake label, rail entry and ⌘K entry;
  - `#inbox` opens Intake;
  - the session-start wording.
- BL-73: the three sections in order, each with its own heading, purpose line and buttons.
- BL-74:
  - the date field is a read-only picker, set to today on every open;
  - future days are greyed out;
  - keyboard control works;
  - the Title box is wider.
- BL-71: the indicator is in the rail and shows Live or Stopped as the server changes; the top bar no longer shows the dates.
- BL-72, in headless Chrome:
  - the section order and the 80% column;
  - Needs attention groups Review items by meeting or sweep, and caps at five plus "+n more";
  - Quick Approve only on routine items;
  - Resolved lists closed items since the last visit;
  - Week ahead covers through Friday, 8 days on a Friday, weekends only with a meeting, and moves weekend due items to Monday.

  Use a fixed date for these: `CREAITE_NOW` where the build supports it, otherwise fixture dates.
- BL-76: a test with the real live server and a real image covers the edit, add image, Save, reload, apply and Undo path, and each unsupported file gives a plain message.
- BL-77: each fault found has a test that clicks through the real controls; the links into Work land on the filter they claim, with matching counts.
- Contrast holds for the new text and the dot in every theme and mode.
- The full suite passes: `python3 dev/tools/run_tests.py`.

**Docs:** Help and the spec updated, and a short "Today as a brief" section added to `dev/BUILD.md` (done for BL-69 to BL-74; add a line each for BL-76 and BL-77 and any Help or spec change).

**Commits:** each item committed separately on `sprint-today-brief`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

- **Real data:** BL-77 asks for a review against real data, but this repo holds sample data only and the development guard forbids using a real vault. Claude reviews against the sample vault (and a larger fictional copy of it) and lists what only a live vault can show. Alan then checks those points in the live dashboard and reports any fault left.
- **BL-76:** Alan hasn't said what goes wrong. If it can't be reproduced with the sample vault, Claude says so and asks for the steps instead of guessing.
