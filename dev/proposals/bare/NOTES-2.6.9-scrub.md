# Notes for 2.6.9: the 2.6.8.1 scrub candidates (H2, H4, qualified separators, label-word agenda lines)

Branch `v269-scrub`, cut from the published 2.6.8 (`286b03c1`). Only `system/scripts/invite_clean.py` and its tests changed; function names and signatures are unchanged (`invite_text`, `scrub`, `is_secret`, `flagged`, `clean_row`, `clean_calendar`, `read_calendar`, `plain_text`, `sensitivity`, `safe_address`), so `sweep.rescrub_calendar` and the guarded chain call it as before. No guarded file is touched.

## Measured against the 2.6.8 baseline (same seeds, same code paths)

| Measure | 2.6.8 | This branch |
|---|---|---|
| Existing fuzz (`test_invite_clean_fuzz_html.py`, 8 generators x 5,000 = 40,000 bodies), bodies with a leaked planted value, any class | 304 (html_table 299, blockquote 2, soft_dates 3) | 304 (same split) |
| ... of which the value holds a digit | 4 | 4 |
| Same fuzz at `FUZZ_FULL=1` (200,000 bodies) | OK | OK (same `classify()` list, nothing new) |
| Idempotence, 40,000 / 70,000 / 30,000 existing bodies and the sweeps | 0 non-fixed | 0 non-fixed |
| New generator `same_line` (H2, H4: 5,000 bodies; 40,000 at FULL) | 5,243 leaked values, 5,401 fields left unscrubbed | 0 and 0 |
| New generator `next_line` (qualified separators) | 3,826 leaked values | 0 |
| New generator `eaters` (Pin board, Token budget ... with numbers and agenda lines below) | 1,537 leaked numbers, 2,730 bodies with a lost agenda line | 0 and 0 |
| Synthetic agenda set (200 lines: 30 trap lines and 40 ordinary lines, repeated, in four layouts) | 122 kept | 135 kept |
| ... ordinary (non-trap) lines lost to a label line above them | 17 | 4 |

New idempotence and leak generators: `dev/tests/test_invite_clean_269.py` (3 generators, rows, mutants, the agenda set).

## Implemented

**H2, a numbered label with its number on the same line, no colon.** `Meeting ID below 345 678 912 345`, `Meeting ID (Teams) 987 654 321`, `Meeting number to join - 482915`, `Webinar ID for Zoom = 987 654 321`, and the same after `->`, `>`, a bar, a tab, `is`, `was`, a bracket. Rule (`SAME_LINE_NUMBER`, first half): a numbered label (the `_WITH_VALUE` list: Meeting ID, Meeting number, Webinar ID, Conference ID, Zoom ID ...), then up to eight plain words or marks, then a number of six or more digits (one run, or two to five groups of three or more digits, split by spaces or hyphens). An ISO-shaped date is not a number. Works in titles, places and organisers as well (`scrub`) because `is_secret` uses it.

**H4, a provider's name and a bare number.** `Zoom 482 915 7731`, `Teams 123 456 789`, `Webex 2552 123 4567`, `Zoom: 855 1234 5678`, `Steering (Teams 345 678 912 345)`, with a dash, bracket, bar, `=`, arrow, a glued separator or up to three plain words between. Providers: Zoom, Teams, Meet, Google Meet, Webex, Skype, GoToMeeting, GoToWebinar, BlueJeans, Whereby, Jitsi, Chime, RingCentral, join.me. Same number rule as H2.

**Qualified separators (the 72 of Cap's probe).** A qualified hard label now stands alone (its value is on the next line) when the qualifier follows a comma, a slash or a semicolon, starts `, - Zoom`, ends in `. , ; ! ?`, ends in `was`/`were`, or holds `1:1`. Examples: `Passcode, for dial-in:`, `PIN for the weekly 1:1:`, `Meeting ID / dial-in`, `PIN for dial-in;`, `Meeting ID, (Teams)`, `Meeting number required.`. Code: `_QPHRASE`, `_QCOMMA`, `_QWORD` (adds `1:1`), the trailing mark in `QUALIFIED_ALONE`, `_ONE_TO_ONE` in `_label_alone`.

**Label-word agenda lines that ate the lines below them.** `Pin board`, `Token budget`, `Pin the roadmap`, `Secret Santa party`: a line that STARTS with PIN, token, secret, OTP or API key and a plain word that is not an instruction word (for, to, below, required, number, sent, from, other, details ... see `_INSTR`) is no longer a qualified label whose value is next. It is still removed (as before) but it now opens a soft window like a soft heading: the next three lines lose only what looks like a value (a number, an ID, a mixed token), so `Pin board` / `4417` still goes and `Pin board` / `Training dates` / `Sign-off` keeps both. `PIN below`, `Token for the build`, `OTP to follow`, `PIN number`, `PIN (Teams)`, `Token - Zoom` keep the full hard rule. A table header row such as `Teams PIN` + `Other` is an instruction word too (so the thead case is not weakened: the html_table leak count is unchanged at 299). Also `Password reset - ABC` and `Code review - ABC` (a dash and a project code) are a finished soft phrase: the heading stays, nothing below it is eaten, and a number right under it still goes (`_SOFT_RUN`, `_BARE_END`). Code: `_AMBIG`, `_INSTR`, `_soft_qualified`, `_soft_heading`, `_Reader._advance`.

Tests and mutants for each rule: `test_invite_clean_269.py` (`Rows`, `Mutants`). Ten mutants, all killed: same-line rule off, provider half off, number rule that takes any digits, comma/slash/semicolon lead off, trailing mark off, `1:1` rule off, soft-qualified rule off, soft window off, instruction words off, project-code suffix off. Mutant anchors in `test_invite_clean_bare.py`, `_bare21.py` and `_bare22.py` follow the reworded source lines.

## Costs and limits of what was implemented (honest)

- H2/H4 remove a line with a provider name or numbered label and a run of six or more digits: `Zoom licences 100 200` is lost (a fail-closed false positive; two three-digit groups look like a meeting ID). Years, dates, `Teams 365`, `Zoom 2026`, `Q3 2026 Teams rollout`, `Meet 12 Nov 2026`, `Meeting number of attendees 12` and `Meeting ID card renewal 2026` stay (rows).
- A word-only value after a provider or a numbered label is not covered (H2/H4 are about numbers).
- Under `Pin board` / `Token budget` / `Pin the roadmap` / `Secret Santa party`, a WORD-ONLY value on the next line stays (like a soft heading, option B). A number, an ID or a mixed token goes. `PIN issued separately`-style qualifiers whose first word is not in `_INSTR` are in the same class: add the word to `_INSTR` if a probe finds one.
- The qualified-label trailing `.` means `Meeting ID required.` followed by a one- or two-word line now loses that line (the same cost as the colon form).

## Deferred or rejected, with the numbers

- **"Password for the HR portal" / "PIN for the card reader" eating the 1 to 3 lines below (function-word qualifiers).** Not changed. The instruction words are what separates "PIN for the room" (a label) from "Pin board". Measured experiment: treat the function words (for, to, of, in, on, at, as, with, by, from, via, and, or) as plain words, and Password as ambiguous too: the existing fuzz leaked 942 bodies instead of 304 (blockquote 2 -> 117, qualified 0 -> 432, accents 0 -> 91; all word-only values), to keep ONE more agenda line (135 -> 136 of 200). Rejected.
- **"Dress code for visitors" and "Cost code changes".** Measured: they do not eat the lines below (0 lost in the plain and numbered agendas); only the line itself is removed (by the bare-`code` rule, as in 2.6.8). They are the one label-word shape where a number right below the line STAYS (`Cost code changes` / `700716` keeps the number, in 2.6.8 as well). Cheap to close in principle (open the soft window after any removed `code X` line), but it changes which lines are removed after every removed phrase, so it is left for E1 (#375). Not a regression.
- **Word-only values for H2/H4, and a provider written with no digits.** Not covered, as before.
- **Titles and places for the soft window.** Unchanged: a title has no next line.

## Risk to the 2.6.8 guarantees

- Idempotence: the soft window is opened on the first pass by a removed line and leaves a `None` placeholder, so the second pass sees no heading and removes nothing more; 0 non-fixed in every existing and new generator (the first draft put the placeholder block in the wrong place in `_Reader._advance` and broke the "Password reset for" chain, which the existing 40,000-body idempotence test caught; fixed).
- Digit leaks: existing fuzz unchanged (4 digit-bearing bodies, all already known); new generators 0.
- Timing: the new patterns are bounded (at most eight tokens, no nested open repeat); `test_invite_clean_timing.py` and `test_invite_clean_expansion.py` pass.
- Public surface unchanged; `dev/tools/check.py` clean (two ratchets needed attention: line length and one function's complexity, both fixed by wrapping and a helper).
