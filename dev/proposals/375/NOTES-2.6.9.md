# #375 notes for the 2.6.9 release notes (draft; not the release notes themselves)

## Plain statement

Saved calendars are cleaned and stamped once, at the first start-up after the update. This covers the live file
(`system/staging/calendar.json`) only. Older copies are not re-cleaned: dashboard history snapshots, Prep pages already written, and the
backup zips keep what they held (Alan: "next release only").

E1 composition D currently equals the 2.6.8 scrub on the fuzz and on loss; its added value is the join-block and dial-in anchors (provider invites 10 leaks / 516 lost lines -> 0/0) and the gateway/stamp.

## Documented limits of the invite filter (from DECISIONS-HIGH.md, ADVERSARIAL.md and the C and D reports)

Codes the filter can miss:
* A code that is a word ("Use falcon to join") or a short alphanumeric token ("Pass zqsm45"): no digit shape to anchor on.
* A bare 4-digit year used as a code (about 2 per cent of 4-digit PINs).
* An id of fewer than 7 digits behind a label we do not know.
* A remainder of five digits in two lines after the scrub took the first group with its label (`483` / `21`): joining it would take
  ordinary column numbers.
* A Meet code inside a sentence with no link; tokens of fewer than 16 characters with `.` `_` `-`; an address with 4+ digits and no
  join, meet or pin word.
* Remaining `digit_styles` renderings (30 of 3,000 generated bodies).

Ordinary text the filter can lose:
* A line that is only `one-time-use` (read as a Meet code).
* Noise collateral: lines that share a block with a secret or with the trigger line are dropped with it, by design.
* Three numbers in a row on separate lines (read as an id split over lines).
* A bare 7+ digit figure (money, order or invoice numbers) drops its block; grouped money formats are the commonest case.
* `html_split`: digit runs inside tags and entities are dropped by design.
* A stamped row is trusted as stored (finding 15, by design): a hand edit that adds the stamp skips the filter. Wrongly typed fields are
  re-filtered.

Numbers after the merge (3,000 bodies, default seeds, 26-10-2026): leak bodies localised 14, digit_styles 27, html_split 0, phones 2,
noise 67, phrasing 52; the 2.6.8 scrub alone leaked 1636, 75, 677, 1157, 752 and 141 on the same sets.

## Limits after the composition D fix pass (ADVERSARIAL-2.md, 26-10-2026)

Fixed now: orphan value blocks after a dropped block (a chain of two), a plain link as a line-level anchor, Unicode line breaks, a linear
`looks_like_html` (1 MB in 0.03 s), spaced letters and a long bare label, provider invites (0 leaks, 0 lines lost).

Stays, by design or not yet fixed:
* A third orphan value block after a dropped block can leak (5 of 1,000 in the generator).
* A `sip:` or `id@host` line takes its block with it (211 keepers lost on `single_anchor`).
* An unclosed `<script>` holding a 10-digit number takes the whole block (the `broken_html` fixture; accepted, fail-closed).
* Link-only lines are dropped by design, for example "New to GoTo? ... https://..." (accepted by Jarvis, 26-10-2026, with the unclosed script above: 3 lines of 130 on the 32-format fixtures).
* A bare label such as "Google Meet link" directly above a removed join link is removed with it (the fixture count is 82 of 130 lines kept; the 2.6.8 scrub keeps 86).
* A long numbered agenda is cut at 1,500 characters.
* Hebrew labels are not recognised.
* A9 (a plain link line is itself dropped).
* Loss ratchets re-pinned 26-10-2026 for the 2.6.8.1 scrub: phrasing 163 -> 211, innocent 3451 -> 4113.

## S4 migration: two silent regressions, now guarded

Two readers silently regressed in the S4 migration: the follow-up email lost recipient addresses from the invite, and the project match in Intake and Prep lost the attendee email-domain signal of #328, because the gateway kept only name, type and response. The golden test `test_calendar_readers_golden.py` (every migrated reader against stored 2.6.8 output) now guards it, and `test_calendar_writers_golden.py` does the same for the three writers (save, held past days, rescrub). The purpose `intake` and addresses in `agenda` and `prep_panel` fix it. Private and confidential rows never return addresses, and no address reaches the dashboard page.

## The stamp is a hash of the filter's files

`calendar_gateway.fingerprint()` is now the first 16 hex digits of the sha256 of `invite_filter.py` and `invite_clean.py` (read once per process; None, and so no row trusted, when either cannot be read). A row stamped by any earlier version of either file, a forged `clean_v` such as "f1", or a bare `clean: 1` is cleaned again on read and written back by the rescrub. Saved calendars are cleaned again at the first start-up after an update. The read cache signature includes the fingerprint.

## Limit: a word-only value several lines below a hard label (fix5, 26-10-2026)

`Weekly sync / Passcode: / Budget review for Q4 / Vendors / rukuponurif / Risks` keeps `rukuponurif`. The 2.6.8 scrub and D give the same output: a hard label's window removes only value-looking lines, and a lone word is not one. On a 5-label by 0-3-ordinary-lines matrix in plain, `<p>` and `<td>` forms the scrub and D leak the same bodies (1 line between: 16 of 30, 2: 20 of 30, 3: 30 of 30). A bare `PIN` cell (no colon) is the same shape as `PIN:`: with 1 to 3 agenda lines between, a digit or mixed value (882541, a6ad063a9, 8825) is removed in every td, row, markdown and plain form for PIN, Passcode, Password, OTP and Token, and a word-only value stays with or without the colon. Not widened; accepted limit.

**Measured claim, not "never leaks more than 2.6.8" (Cap's final verdict, 26-10-2026):** On the 3,024 word-value bodies the E1 default leaks 255 against 365 for the 2.6.8 scrub; digit values 120 -> 0. It is not true that it never leaks more: the shapes where it equals or exceeds the 2.6.8 scrub are a word-only value after a hard label's second ordinary line (equal), the bare PIN in a table cell (`<td>PIN</td><td>Any other business<br>rokimes</td>`: 2.6.8 held it only by running the cells together, the candidate leaks `rokimes`), and a word after a Unicode line break (`Passcode: 8825<NEL>zejumud`: 2.6.8 held it, the candidate leaks `zejumud`). All are word-only; digits are held in every case.
* A line such as `<p>Room key</p><p>7118</p>` on its own (no join block before it) keeps `7118`, as in 2.6.8; the "Room key" fix holds only after a join block.
* A short line followed by a three-digit line (for example "Room 204") can be lost with it; it fails safe and is a known loss.

test_v260 (old 2.6.0 hand-check file) fails identically on eb32046b and fb42d0cd; pre-existing, not in the gate set.
