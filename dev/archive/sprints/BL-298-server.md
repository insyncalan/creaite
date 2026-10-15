# Sprint: draft-chase-server (BL-298, the server and Python side)

**Goes into:** v1.9.0. Branch `sprint-draft-chase-server`, worktree `../creaite-chase-server`, from the tip of `main`. The dashboard (the peek's envelope, key C, the pane, the email's HTML) is a later part: `system/templates/dashboard/` is being converted to modules, so nothing here touches it.

## What was built

- `drafts.py` (block `BL-298 (sprint-draft-chase)`):
  - `CHASE_WORDING`: the subjects, openings and asks for the three modes and three tones, copied from BL-298 › As accepted (help, decision) and from `DE_CHASE` (chase, unchanged; a test compares it with the JS). The page may reuse these strings rather than keep its own copy.
  - `chase_draft(facts, opts)`: the email as parts (`subject`, `greeting`, `opening`, `need_label`, `need`, `row`, `ask`, `sign_off`, `from`) and as `text` (Copy as text). Pure: no model, no file, no database.
  - `chase_mode`, `chase_defaults` (reply by two working days ahead using `work.weekend_days`; tone `min(n, 2)` from `chases.json`; latest update on), `working_days_ahead`, `due_words`, `mode_line`.
  - `chase_recipients(facts)`: named in the item or its latest update, then who raised it (a mail or Teams sender, anyone named in the source), then the source meeting's attendees (`calendar.json`, matched by the minutes file's date and title), then the project's stakeholders (the sponsor, the register's Key and Shared stakeholders). Resolved through the people register, Alan left out, deduplicated with the first reason kept, the project by name, never a VIP label. `chase_anyone()`: the register less Alan and hidden people.
  - `chase_facts(id)`: read only; refuses a closed item, a decision not pending, an unknown ID and anything confidential, restricted or from `documents/`.
  - `chase_record` takes the modes `help` and `decision`; `chase_counts` counts chase, help and decision records (update and followup records are kept but not counted, as before).
  - Command line: `drafts.py chase-pane` (JSON on stdin); `chase record --mode help|decision`.
  - Fixed on the way: `attendees_of` passed `people_register_text()`'s tuple to `people_parse`, so a follow-up never filled a missing address from the register.
- `live_server.py`: `POST /api/chase/pane`; `POST /api/chases` accepts `help` and `decision` (any other mode is still recorded as `chase`).
- `help.md`: How-to "Chase one item, or ask for help with your own" and a line in the Draft email reference; guides rebuilt.

## What the peek pane must call

1. **Open the pane** (envelope or C, on an open action, risk, issue or pending decision; hidden for closed or cancelled items and proposals): `api("/api/chase/pane", {id, hour: new Date().getHours()})`. The reply:
   `{ok, id, mode: "chase"|"help"|"decision", mode_tag, mode_line, project, code, to: {name, email, first}, suggestions: [{name, email, org, role, why, known, project}], anyone: [{name, email, org, role}], defaults: {reply_by, tone, include_update, chased: {n, last}}, draft, wording}`; `{ok: false, message}` when the item can't be chased (show the message).
   - Mode line: `mode_tag` is the tag, `mode_line` the sentence.
   - **To**: `to` (a chip with the name, the email beside it). For `help`, `suggestions` are the buttons under it, each with its `why` ("named in the item", "raised it", "at the meeting", "project stakeholder"); `anyone` fills **+ Anyone**.
   - Controls start from `defaults`: Reply by `reply_by`, Tone `tone` (0 First, 1 Second, 2 Firmer), Include the latest update `include_update`.
   - For `help`, **To get … done** starts from `draft.outcome` and **What I need from you** from `draft.need` (filled from the item; send `outcome` and `need` back once Alan types). For `decision`, `draft.unblocks` is what the opening says it is needed for.
2. **As Alan types**, either call the route again with his choices, `{id, to, tone, reply_by, include_update, outcome, need, unblocks, cover, hour}` (read only, about 100 ms), or rebuild in the page from `wording` and `draft.row` with the same rules. The email's HTML (Calibri, the Draft email palette, `deTd`/`deTh`/`deP`) is the page's: `draft.row` has `id`, `label` ("Decision needed:", "Risk:"), `item`, `owner` ("Owner: Alan Carter" for help), `response` (RAID), `update` (empty when off), `due_label` ("Due" or "Needed by"), `due`, `due_words`, `overdue` (red and bold when true), `priority`. The highlighted line is `draft.need_label` + `draft.need` (help only). Subject `draft.subject`; plain text `draft.text`.
3. **Polish** (when Settings › AI drafts allows it): the existing `draftAsk({kind: "polish", text: draft.opening, tone})`; pass the chosen text back as `cover`.
4. **I sent it**: `api("/api/chases", {ids: [id], mode})` with the pane's `mode`. The reply's `chases` replaces `SA().chases`; the result line: "Recorded: chased <first> on <DD-MM-YYYY>. The next one will be a <second|firmer> reminder." Copying records nothing.

## Questions for Alan

- Decision mode's sign-off: the mockup has "Thank you." after the ask and "Thanks, Alan". Built as "Thank you," + Alan (as help) to avoid thanking twice.
- Greeting: the mockup says "Hi Dana,"; built with the Draft email's own "Good morning, Dana," (by the hour).
- Chase mode keeps DE_CHASE's plural wording ("the items below") for one item, as "unchanged" says; the mockup shows a singular version. The subject is `[CODE] Reminder: <item>` (BL-101) rather than BL-224's `ABC-A-001 · Reminder`.
- "What it unblocks" for a decision has no field: it is the first item the decision blocks (links), else the project's next milestone, else "the next steps on <project>".

## Tests

`dev/tests/test_draft_chase.py` (25): each mode's wording per tone, the row, the defaults (two working days over a weekend, a Friday–Saturday weekend), the mode from whose item it is, the recipient ranking and "Anyone" (no VIP label), the pane for each mode and the refusals, `/api/chases` recording chase, help and decision as IDs, a date and the mode only, and chase mode unchanged.
