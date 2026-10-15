---
name: cx-prep
description: creaite meeting prep page (BL-98). Builds one self-contained HTML page for one meeting today or on any later day the saved calendar holds (what it is about, the urgent, overdue and due-soon work items, the latest project reporting with links to the recent reports, researched notes with sources, suggested questions) and saves it in the project's Agendas folder. Use when Alan says "prep for the <meeting>", "prep page for the ABC steering", "make me a prep page for tomorrow's 10:00", "prep for Thursday's budget review". Read-only research; the only write is the page itself, built by prep_page.py.
---

# cx-prep

One HTML page for one meeting, for Alan only. It is marked **Internal**, never sent, never published, never emailed. Nothing reaches the tracker: if the research suggests a new action or risk, the page says so and Alan raises it himself.

**Projects by name (BL-101):** refer to a project by its full name in everything Alan reads (summaries, tables, messages, file names, drafts). The short code appears only inside a work item's ID (`ABC-A-003`) and in a command he can type; `tracker.project_label(code)` gives the name.

The dashboard's **Prep page** button (in a meeting's Prep brief, with the live server running) does all of this by itself, with progress and Stop. This skill is the same flow from Claude Code.

## In ask creaite (the dashboard panel)

The live server makes the page, never the panel (BL-98, BL-307). Find the meeting's key (step 1 below; `prep_page.py context "<key>"` checks it) and end your reply with exactly one line: `PREP: <key> | <meeting title>`. Alan gets a **Prep page** card; Go ahead runs the same research and the server's own write as the Prep brief's button. Never answer with a `CONFIRM:` line for a prep page, never write the reply file or run `prep_page.py build` from the panel. If the meeting has no project yet, say: "Choose its project in the meeting's **Prep** on Today first."

## In Claude Code

1. **Find the meeting.** Its key is the Prep brief's: `HH:MM|<title>` for today, `YYYY-MM-DD|HH:MM|<title>` for any later day, from `system/staging/calendar.json`. Every meeting from today to the last day the saved calendar holds (seven days ahead of the day it was saved) has Prep (BL-293); a past day, or one beyond the saved calendar, is refused with the reason, and private and ignored meetings have none. If the calendar is old or the day is beyond it, "refresh calendar" first (cx-sweep).
2. **Context:** `system/scripts/run prep_page.py context "<key>"`. It gives the meeting (invite text, attendees, attachment names), the items that are **Urgent, overdue or due within the "due soon" setting** (and the decisions needed by then or whose revisit date has come), with `not_listed`, the number of other open items left out on purpose; the invite ranking only adds a "why" to the listed ones. It also gives the latest weekly update, Current state and recent reports, and what to research. The page lists only those items: don't add others, but the notes and questions may mention anything relevant. If it says to choose the project, ask Alan which project (or the portfolio) and remember it for the series in the Prep brief.
3. **Research, read-only and brief,** only what bears on the invite or the listed items:
   - the minutes and transcripts it lists (`docx_tools.py text`, `minutes.py transcript`);
   - the project's documents folder (internal: label what comes from it);
   - Alan's notes listed under `research.notes` in the context, and only those (internal: label what comes from them). A note marked confidential is kept out of prep pages: the context never lists or names it (`confidential_notes_left_out` only counts them), so never open, read, search or cite any other file in a notes folder. `prep_page.py build` drops any finding, question or reason that cites or quotes a confidential note anyway;
   - Microsoft 365 mail and Teams for the project over the last 14 days, with the search tools only. If Microsoft 365 isn't available, say so.
   Never invent a finding; a section with no evidence stays empty ("Nothing found"). Never copy long passages.
4. **Reply file:** write `system/staging/drafts/prep-reply.json`:
   `{"about": "2–3 sentences", "item_reasons": {"<ID>": "why it matters here"}, "notes": [{"text", "source", "date": "YYYY-MM-DD"}], "questions": ["…"], "m365": "searched" | "unavailable: <why>"}`.
   Every note has a source: a vault path, or `Email · From … · Subject … · Sent YYYY-MM-DD`, or `Teams · Channel … · Sent …`.
5. **Build:** `system/scripts/run prep_page.py build "<key>" system/staging/drafts/prep-reply.json`; it deletes the reply file itself once the page is saved. It renders the page (one file, no outside scripts or fonts, light and dark, printable) and saves it as `<project>/<Agendas folder>/YYYY-MM-DD Prep - <title>.html`. A second page for the same meeting and day replaces creaite's own earlier one (a copy goes to `system/backups/files/`); a page Alan edited or a file creaite didn't write is never overwritten (the new one gets a number).
6. **Tell Alan** where it is, and that the Agendas folder may be shared (with projects in OneDrive, other people may see it): it is marked Internal. Offer to open it.
