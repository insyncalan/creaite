# Sprint: Draft email (BL-83)

Branch `sprint-draft-email`, worktree `../creaite-draft-email`, made from the tip of `main`. Before starting, run `git worktree list` and `git status` in the worktree; nothing else should be editing the person page. Read BL-83 in `dev/BACKLOG.md` first; it holds Alan's decisions. BL-55 (people register), BL-56 (person pages and Hand over), BL-68 (person rows) and BL-74 (the calendar popup options) are already built.

## Goal

On a person's page, **Draft email** replaces **Prep 1:1**. It opens a popup with a well-formatted email to that person: a time-of-day greeting, the open items by project with colour for overdue and due soon, a kind request for an update, and a proposed subject with the project code. Alan copies it and pastes it into Outlook. creaite never sends mail and never creates an Outlook draft.

## Order

Commit each item separately, in this order. The first has no screen, so it can be tested on its own.

### 1. The email builder (no screen)

One pure function, in its own marked section `/* ===== Draft email (BL-83) ===== */` in `dashboard.html`, taking the person, the options and the time, and returning `{to, subject, html, text, items}`. Nothing in it reads the page.

- **Greeting by the time generated:** "Good morning" before 12:00, "Good afternoon" from 12:00 to 17:59, "Good evening" from 18:00, then the person's first name (from the people register; their full name's first word if the register has none).
- **Opening and closing:** fixed wording in a template, British English, no model call. Opening: a kind "I hope you're well" and a request for a brief update on each item. Closing: ask where each one stands and what is blocking them or needed from Alan, then thanks. If a **reply-by** date is set, add one polite sentence with it as DD-MM-YYYY.
- **Items:** the person's open actions and open risks and issues, across all their projects, one block per project headed by its code and name, in this order: overdue (oldest first), due soonest, undated last. Columns: ID, the item, due date, priority; risks and issues also show their type and the response needed.
- **Colour, never alone:** overdue rows have the due date in dark red and bold plus "n days overdue"; due within 7 days (the dashboard's due-soon setting) in amber plus "due in n days"; Urgent priority bold. Take the colours from one small table of values at the top of the section, so contrast can be tested:
  - red `#B3261E` and amber `#8A5A00` on white (both at least 4.5:1);
  - normal text `#1E1F1E`, header row `#F1F3F4`, rules `#D9D9E0`.
- **Built for Outlook's Word engine, so only simple HTML:** inline styles on every element, a table with `cellpadding`, `cellspacing` and a bottom border on each cell, `font-family:Calibri,Arial,sans-serif` at 11pt, no flexbox, no CSS variables, no classes, no images, no web fonts. The email is always drawn on white, whichever dashboard theme is on.
- **Subject:** the project code (or codes, sorted, joined with " / ") first: `ORX · Update request: 4 open items (1 overdue)`; for one item `ORX-A-003 · Update request`. Use the middle dot as shown.
- **Sign-off:** "Kind regards," and Alan's first name from `identity` (Alan's Outlook signature follows when he pastes).
- **Plain text version:** the same content, with the table as aligned lines, for the clipboard's plain-text copy.
- **Selection:** the builder takes the set of ticked items; the default set follows the safeguard in item 2.

### 2. The popup and copying

- **Popup:** a dialog in the style of the existing prep dialog (`prepdlg`), titled "Draft email: <name>", in this order:
  - **To:** the person's email from the register with a Copy button; "No email recorded" when there is none.
  - **Subject:** the proposed subject in its own box with a Copy button, editable.
  - **Include:** a tick box per item (all ticked by default), grouped by project; "Include latest update" (off); **Please reply by** with the calendar picker (BL-74's read-only field).
  - **Preview:** the email as it will look, **editable in place** (greeting, wording, a personal line), on a white card whatever the theme.
  - **Buttons:** Copy email, Copy as plain text, Close. "Copied" confirms each one.
- **Reply-by date picker:** only today and later can be chosen, the opposite of Quick Capture. BL-74 added a latest-selectable-day option to the popup; add the matching **earliest selectable day** option, so other screens can use both.
- **Copying:** Copy email writes the preview's current HTML and its plain text together with `navigator.clipboard.write([new ClipboardItem({"text/html": …, "text/plain": …})])`, so Outlook pastes the table and the colours. If the browser refuses (no secure context or no permission), select the preview and say "Press ⌘C to copy"; never fail silently. The popup copies what is on screen, so Alan's edits go with it.
- **The safeguard for people outside the company:**
  - the page needs `identity.own_domains` (it is in `settings.json` and used by `propose.py`, but not passed to the page): add it to the dashboard's data in `build_dashboard.py` (`collect()` and `live_data()`), so a refresh keeps it;
  - when the person's email is not on one of those domains, items not flagged client-visible are **unticked** and tagged "internal", and Alan can tick them. With no email on record the person is treated as outside.
  - **never added:** anything from a project's `documents/`, anything marked confidential or restricted, an item's source, and the latest update unless the box is ticked.
- **Nothing is written:** no proposal, tracker row or Activity entry. Opening and copying do not change any file.
- **Empty case:** with nothing open, the person's page shows the button disabled with "Nothing open for <name>, so no email is needed."

### 3. Replace Prep 1:1

- On a person's page, swap the **Prep 1:1** button (`#pp1`) for **Draft email**, in the same place beside Hand over and Edit details.
- **Remove** `p1Dlg()`, `openP1()` and the `#pp1` click branch, plus their style if nothing else uses it. **Keep `P1_DAYS`:** the "Closed in the last 14 days" card uses it. Keep Hand over, the closed-in-14-days card, the warnings on rows and the key-person note.
- **Search for other references** (the ⌘K list, the Today or Review text, Help, the spec, the tests) with `grep -n "Prep 1:1\|openP1\|p1Dlg\|pp1"` and update each.
- **Docs:** `system/templates/help.md` and `dev/dashboard-spec.md` describe Draft email in place of Prep 1:1. Leave `BACKLOG.md` and `BRD.md` alone: they are updated at merge (FR-73's mention of Prep 1:1 becomes Draft email).

## Boundaries

- **Owns:** in `dashboard.html`, the new "Draft email" section, the person page's button row and the removal of Prep 1:1; `build_dashboard.py`'s data (only to pass `own_domains`); `help.md`; the people dashboard tests.
- **Don't edit:** `tracker.py`, `schema.sql`, `excel_sync.py`, the skills, `live_server.py` or the Review code. There is no schema change.
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`): put new code in its own marked section; remove Prep 1:1 in place without reformatting the code around it, so the merge stays readable.
- **Development guard:** sample data only; test with temporary vaults and fictional people. Never connect to Microsoft 365.
- **Rules kept:** local only (nothing leaves the laptop but what Alan pastes); creaite never sends or drafts mail; internal items stay out of an email to an outside address unless Alan ticks them.

## Done when

**Tests (headless Chrome, in `dev/tests/test_people_dashboard.py`, with a fixed clock):**
- the greeting at 09:00 "Good morning", 13:00 "Good afternoon" and 19:00 "Good evening", with the person's first name;
- the subject for one project, for several (codes sorted, joined with " / "), and for a single item;
- the project code and name in each block of the body;
- overdue shown in red and bold with "n days overdue"; due soon in amber with its words; Urgent bold; and the colour pairs meet 4.5:1 on white;
- every element carries its own inline style (no classes, no variables), so the HTML survives Outlook;
- for an address on an own domain, all items ticked; for an outside address, items not client-visible unticked and tagged "internal", and ticking one adds it; no address behaves as outside;
- documents, confidential items, sources and (unticked) latest updates never appear;
- the reply-by picker refuses past dates and adds the sentence with a DD-MM-YYYY date;
- Copy email puts both `text/html` and `text/plain` on a stubbed clipboard, and the refused-clipboard path shows its message; the preview's edits are what is copied;
- nothing open: the button is disabled with its message; no file is written by opening or copying;
- the button row has Draft email and no Prep 1:1, and Hand over still selects and reassigns rows with undo;
- the existing person-page, Work and Today tests pass unchanged.

The full suite passes: `python3 dev/tools/run_tests.py`.

**Alan checks, once, by hand:** paste a copied email into Outlook desktop and Outlook on the web: the table, the red and amber, the bold and the font hold up; the Subject copies on its own; and the wording reads right to him.

**Docs:** Help and `dev/dashboard-spec.md` updated, and a short "Draft email (BL-83)" section added to `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-draft-email`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)
