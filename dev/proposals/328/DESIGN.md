# #328 One matcher for calendar meetings: first step and design

Stark, 25-10-2026. Reading only; no code changed.

## Finding

**The calendar path does call a matcher, but a thin one.** It is not the matcher in `project-matching.md`.

- Calendar import rows are built in `system/scripts/build_dashboard.py` `inbox_meetings` (line 2791). Line 2822 calls `prep_match(title, projects, remembered)` (line 2516) for every meeting that is not private.
- `prep_match` does three things only: the series remembered in settings (`prep.series`, set by `choosePrep`, `meetings.js:94`) gives "remembered"; `project_hits` (line 2507) on the **title alone** gives "matched" when exactly one project is named; two or more hits, or the word "portfolio", gives the portfolio; nothing gives `(None, "unsure")`.
- `project_hits` reads a code token, the project name and the register's alias and keyword cells (`register_signals`, line 495: name, aliases column 3, keywords column 7). A single keyword is enough to "match". The skill's rule says never a guess from a single keyword.
- **Not used for calendar meetings:** attendee addresses and domains, the people register's organisations, the register's client and partner domains, senders, stakeholders, the Exclude column, the Shared table, the conflict case. `calendar.json` already holds attendees (`sweep.py` `invite_attendees` line 1203, kept by `calendar_row` line 807 except for private and confidential meetings), so the data is there and nothing reads it for this.
- The one place that does match on people is `sweep.py` `conv_project` (line 1426), with `people_hits` (1453) and `row_names` (1474), for conversation alerts. It matches senders, domains and stakeholders, ignores Alan's own domains, and takes one hit only. This is the nearest thing to the wanted matcher and is the code to share, not copy.
- Three more callers use `prep_match` with the same limits: `meeting_project` (3223, the Today and day views), the prep entry (2566) and the week line (3921).
- The row model drops the reason: `_ir_calendar` (2961) passes `p` only. `how` (remembered, matched, portfolio, unsure) is built at 2822 but never reaches the row. In the page, `rows.jsx:138` and `:186` and `views.jsx:78` show a name or the words "Not sure". No chip, no reason, no candidates. `intakeApi.js:89` (`mtgProcessFile`) is the only reader of `how`, and it checks for "remembered" only.
- **Learning:** `propose.py` `learn_check` (463) and `cmd_learn` (518) are the BL-28 flow (sender, domain, channel, alias, stakeholder; refuses a single keyword and Alan's own domains; shared signals go to the Shared table; undoable). The calendar choice does not use it: choosing a project on a meeting only remembers the series (`prep.series`). No signal is ever offered for learning from a calendar meeting.
- Nothing is filed or read because of the guess today: the project only labels the row and fills the project passed on when Process is pressed for a remembered series.

**First fix, as the issue says:** the matcher exists, so the first fix is to widen it (people and domains, a conflict state, a reason) and to show its answer. A new engine is not needed.

## Design for the Wanted list

### 1. One matcher in plain code

New small module `system/scripts/meeting_match.py` (not guarded). One function:

`match_meeting(title, attendees, organiser, projects, register, remembered, own_domains, confidential) -> {p, level, reason, candidates}`

- Signals, strongest first, using the skill's table:
  - Strong: remembered series; a `[CODE]` or code token in the title; the project's full name in the title.
  - Medium: an alias or client name in the title; attendee domains (not Alan's own) listed for exactly one project; attendee addresses listed as a sender for exactly one project; a key stakeholder named; the people register's organisation of an attendee tied to one project; two or more keywords from one project.
  - Weak: one keyword only. It adds a candidate but never sets a project.
- Conflict: strong or medium signals pointing at different projects gives level "none" with the candidates listed.
- The register's Exclude word rules a project out. A workstream word used by more than one project is no evidence.
- Own domains (`identity.own_domains`) and Shared-table signals never count.
- Reuse, do not copy: lift `people_hits` and `row_names` out of `sweep.py` into the new module (sweep.py then imports them), and call `project_hits` for the title.
- A confidential meeting is matched on its title only (it holds no attendees). A private "Busy" meeting is not matched.
- Levels: **matched** (a strong signal, or a remembered series), **likely** (medium signals agreeing on one project), **unsure** (none, one weak keyword, or a conflict).
- The portfolio result (several projects named) stays as it is.

### 2. Chip and reason

- Row model: `_ir_calendar` passes `level`, `reason` (one plain sentence, built from fixed phrases such as "Named in the title", "Attendees from the client's organisation", "You chose this for the series before", "Two projects fit: A and B") and `cands` (at most three codes). Reasons name people and organisations only as the register already shows them; no signal names, no paths.
- Page: one small component beside the project name in the List, the Board card and the Two panes' detail (`rows.jsx` 138 and 186, `views.jsx` 78). Chip words **Matched**, **Likely**, **Not sure**, each with an icon (tick, tilde, question mark) and a colour, so colour is never alone. The reason sits under it in the existing `why` line. Not sure rows show the candidates as buttons.
- Confidential meetings show the chip and a reason built from the title only; no attendee text.

### 3. Correcting teaches

- Choosing a project on a Likely or Not sure row keeps today's series memory and then offers once, in one line with one button: "Remember <signal> for <project name>?" The signal offered is the strongest concrete one that was on the meeting (an attendee domain, an organiser address, a stakeholder), checked with the existing `learn_check`; a single keyword or Alan's own domain is never offered. A signal already held by another project offers the Shared move, as the skill says.
- Yes calls the existing learn route (`propose.py learn`), which is undoable. No answer leaves nothing behind. The offer is remembered per signal so it is not asked twice.

### 4. Never silent

- A Matched row shows its project name as a control: one click opens the project list. Changing it does the same series memory and learn offer.
- Nothing is filed, loaded or read because of a Matched or Likely guess. Process still shows the project it will use and takes it from the row Alan sees; Likely and Not sure rows ask for a choice before Process, as an unsure upload does today. The existing `mtgProcessFile` rule (pass the project only when remembered) stays the same or becomes stricter, never looser.
- No AI call anywhere in the matcher.

### 5. Desktop and 900 px only.

## Guarded files and chain diff outline

Guarded files needed: **`system/scripts/build_dashboard.py`** and **`system/scripts/sweep.py`**. No rules text change. `propose.py` is probably not needed (the learn route exists); if the offer must pass a new kind such as an organiser address, `propose.py` `LEARN_COLUMN` would be a third guarded file. Confirm against the register columns before building. The dashboard source files and the built `dashboard.html` are not guarded.

Outline:

- `build_dashboard.py`
  - `prep_match` (2516, about 10 lines): keep its return shape for the three other callers; add `prep_match_full(...)` that calls `meeting_match` and returns the level, reason and candidates. About +25 lines.
  - `inbox_meetings` (2791 to 2840): pass attendees, organiser and own domains in; add `level`, `reason`, `cands` to each row. About +12 lines.
  - `_ir_calendar` (2961): pass the three new fields through. About +4 lines.
  - `meeting_project` (3223): optional, give the Today view the same level. About +4 lines.
- `sweep.py`
  - Move `people_hits` and `row_names` (1453 to 1480) into `meeting_match.py` and import them back. Net about -25 lines in `sweep.py`, +5 for the import. Behaviour unchanged, covered by the existing conversation tests.
- Not guarded: new `meeting_match.py` (about 150 lines); `rows.jsx`, `views.jsx`, a new chip component, the project picker and the learn offer (about 120 lines); `style.css` (chip, about 20 lines); `globals.json` entry.

## Tests

- `test_meeting_match.py`: title code, name, alias; one keyword gives Not sure; two keywords from one project give Likely; attendee domain for one project gives Likely; Alan's own domain never counts; a domain shared by two projects gives Not sure with both candidates; a conflict between title and attendees gives Not sure; Exclude word; remembered series gives Matched; confidential meeting uses the title only and no attendee text reaches the row; private meeting is not matched.
- Row model: `level`, `reason`, `cands` present, no signal names or paths in the reason.
- Learn offer: Likely and Not sure rows offer it, Matched rows do not until changed; a keyword and an own domain are never offered; undo restores the register.
- Never silent: a guess does not load a transcript, start minutes or write any file; Process on an unsure row asks first.
- Chip: words, icon and colour all present; 900 px layout; no "VIP" word anywhere.
- Existing: conversation matching (`conv_project`) unchanged after the move; `test_plain_words.py`, `test_ask_creaite_name.py`, `test_no_real_names.py`, `check.py`.

## Size

M, as the issue says. About 3 agent-days for Stark; Cap's review about 1.5. The module and tests are two thirds of it; the page is the rest.

## Questions for Alan

1. Attendee domain alone: is one client domain enough for Likely, or should it need a second signal (the title or a known person)? The design says one domain is Likely and never Matched.
2. A meeting with a client domain and a partner domain from two projects: Not sure with both offered (the design), or the portfolio?
3. Should the people register's organisation of an attendee count as a signal even when the project register lists no domain for it? The design says yes, as Likely.
4. Do Today and the day view show the chip too, or the Calendar import rows only? The design starts with Calendar import and the Prep popup stays as it is.
5. A recurring meeting remembered once: should one correction be remembered at once (as today), or only after two matching choices?
