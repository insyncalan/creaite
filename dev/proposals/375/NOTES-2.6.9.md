# #375 notes for the 2.6.9 release notes (draft; not the release notes themselves)

## Plain statement

Saved calendars are cleaned and stamped once, at the first start-up after the update. This covers the live file
(`system/staging/calendar.json`) only. Older copies are not re-cleaned: dashboard history snapshots, Prep pages already written, and the
backup zips keep what they held (Alan: "next release only").

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

Numbers after the merge (3,000 bodies, default seeds, 26-10-2026): leak bodies localised 53, digit_styles 30, html_split 0, phones 2,
noise 67, phrasing 52; the 2.6.8 scrub alone leaked 1636, 75, 677, 1157, 752 and 141 on the same sets.
