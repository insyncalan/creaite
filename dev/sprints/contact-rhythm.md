# Design brief: contact rhythm and the 1:1 prep page (BL-204)

**Status:** design brief, not scheduled (low priority). Mockup: `dev/mockups/contact-rhythm-mockup.html` (open it from the file system; fictional sample-vault people, today 12-10-2026). When it is built: branch `sprint-rhythm`, from the tip of `main`, with the UX baseline (BL-157) checked before it is called done. The promises part of the prep page waits for BL-125 stage A (v1.9.0).

## Goal

A person's page (BL-56) says how long since Alan last spoke to them against his usual rhythm with them, and one button makes a 1:1 prep page for that person.

## The screens

1. **Person page, Contact card** (beside Open work): a private marker; a bar chart of contacts per week for the last eight weeks; "Usual rhythm: weekly"; "Last contact: 21-09-2026 · ORX weekly 1:1"; "21 days since last contact" in amber, with a triangle, when the gap is more than twice the usual one, and a **Prepare a 1:1** link. A switch, **Count mail and Teams too**, adds the references the sweep recorded (shown as a lighter part of each bar).
2. **Thin history:** under about four contacts in eight weeks the card says "Not enough history yet: 2 contacts in eight weeks" and shows no chart, rhythm or gap.
3. **Making the page:** **1:1 prep page** in the person header runs the Prep page engine (BL-98) for the person: the steps with progress, Stop, one run at a time; the live server saves the page and shows where ("Saved in Orbit Customer App › Agendas › 2026-10-13 1-1 Sara Khan.html · Open").
4. **The 1:1 prep page** (prep_page.py's look, marked Internal, never sent): their open and overdue items with why each matters; promises both ways (once BL-125 A exists); last meetings together (including one they missed); the contact gap; three talking points, each with its source; Sources.

## In

- Contacts from meetings both attended (the saved calendar and the minutes' attendees); mail and Teams only where the sweep recorded a reference, behind the switch.
- Usual rhythm as the median gap between contacts, in words (weekly, fortnightly, monthly).
- Private by rule: the person page is the only place. No report, client output, one-pager, Excel export or ask creaite answer reads it.
- A person variant of `prep_page.py` and the cx-prep skill; no new run engine.

## Out

- Scores, ratings or "relationship health". Counts and a gap only.
- Reminders or Today alerts about a gap (could come later, once it has been used).
- Scheduling the 1:1 or sending anything.
- Reading message text: references only, as the sweep keeps today.

## Questions for Alan

1. **What counts as a contact:** meetings only (recommended to start), or mail and Teams too by default? The switch in the mockup shows the difference: Sara is 21 days on meetings, 6 days with mail.
2. **Where a person on several projects is filed:** the project with most of their open items (recommended), or the portfolio folder?
3. **The amber rule:** twice the usual gap, or a fixed number of days per rhythm (weekly: 14, fortnightly: 28)?
4. **Who gets the card:** everyone in the register, or only people you choose (for example your team and sponsors)?
5. **The 1:1 time:** use the next 1:1 in the calendar with that person when there is one, else "tomorrow, no time"?

## Files it touches

`system/templates/dashboard.html` (the Contact card on the person page, the switch, the button; a marked block), `system/scripts/build_dashboard.py` (contacts per person from `calendar.json`, minutes attendees and the sweep's references), `system/scripts/live_server.py` and `system/scripts/prep_page.py` (the person variant: context, prompt, render, filing), `.claude/skills/cx-prep/`, `system/templates/help.md`, `dev/dashboard-spec.md`, `dev/tests/` (rhythm from fixture meetings; nothing on thin history; the gap flags correctly; the person page is filed where expected and never overwrites an edited one; nothing in any report or export).

## Size

**M**, about three days: one for the contact data and the card, one and a half for the person variant of the prep page and its filing, half for tests and the UX baseline. Add half a day if mail and Teams count by default (matching people in the sweep's references).
