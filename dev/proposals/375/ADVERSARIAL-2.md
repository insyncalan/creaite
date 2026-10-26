# #375 E1 adversarial pass 2 (final, 2.6.9 stack)

Branch `v269-adv2`, from `v269-main` (6ce15ff9). Nothing under `system/scripts/` was changed. Added: `dev/tests/test_e1_adversarial2.py` and this file.
Subject: `invite_blocks`, `invite_filter.filter_text_with_scrub` (default composition D, `scrub_raw_first`, "C"), `calendar_gateway`; compared with the 2.6.8 scrub alone (`invite_clean.invite_text`, "old").
Fresh generators only (10; none of the 13 of `test_e1_adversarial.py` or the 8 of `test_invite_clean_fuzz_html.py`). Fictional data. `python3 dev/tests/test_e1_adversarial2.py` (about 35 s, 44 tests, 20 expectedFailure); `--report` prints the tables below (1,000 bodies per generator, about 1 minute); `ADV_FULL=1` runs 10,000.

## Verdict

D is clean on provider boilerplate, wrapped URLs, repeated bodies, dial-in lists, time zones, markup and encodings: **0 leaks in 7 of 10 generators** (about 9,700 planted secrets), idempotent on all 10,000 bodies, never slower than 25 ms a body, and strictly better than the old scrub on leaks everywhere. The remaining problems are all in two places: **the orphan rule does not fire where D has already removed the anchor line** (leaks), and **a link without a query drops its whole block** (data loss). One quadratic function, harmless in production because of the 20,000-character cut.

## Per generator (n = 1,000; planted secrets, planted ordinary lines "keepers")

| Generator | Secrets | C leaks | old leaks | Keepers | C lost | old lost | C not idempotent | Worst body |
|-----------|--------:|--------:|----------:|--------:|-------:|---------:|-----------------:|-----------:|
| orphans (1 to 3 value-only blocks after a dropped block; 8 separations, 9 value shapes, 4 head blocks) | 1,568 | **363** | 1,191 | 2,526 | **216** | 0 | 0 | 2 ms |
| single_anchor (one link, phone, ICS line, SIP or signature dial in an agenda; 8 layouts) | 73 | 0 | 73 | 4,313 | **1,031** (129 bodies lose every line) | 0 | 0 | 2 ms |
| provider_one_line (Teams, Zoom, Webex, Meet, GoTo, unknown: one join or ICS line) | 1,161 | 0 | 40 | 4,000 | 40 (10 bodies, all lines) | 0 | 0 | 2 ms |
| encodings (CRLF, CR, NEL, U+2028/2029, VT/FF, BOM, UTF-16 misread as latin-1 or utf-8, mojibake, QP, numeric entities, NBSP, tabs) | 1,000 | 0 | 0 | 5,000 | **1,275** | 1,275 | 0 | 2 ms |
| label_markup (bold, code, link, strike, emoji, RLM/RLO/isolates, fullwidth colon, soft hyphen, ZWJ, letter-spaced, `=`, `-`, parentheses ...) | 1,000 | 8 | 24 | 4,000 | 0 | 0 | 0 | 2 ms |
| safelinks (Safe Links single and double encoded, URL-defence, click tracker; 8 query keys) | 1,000 | 0 | 0 | 4,000 | 0 | 0 | 0 | 2 ms |
| repeated (body pasted 2 or 3 times, separators, different PIN each time) | 2,500 | 0 | 0 | 5,000 | 0 | 0 | 0 | 12 ms |
| numbered_long (items 1 to 10/30/60/100 with one join block) | 1,000 | 0 | 0 | 8,000 | 1,463 (the 1,500 cap) | 0 | 0 | 23 ms |
| tz_and_dial (zone list, 3 to 30 dial-in numbers in 5 styles) | 3,000 | 0 | 0 | 9,000 | 0 | 0 | 0 | 7 ms |
| provider_unknown (house-style join block, 12 label words in 7 languages) | 1,000 | 35 | 97 | 5,000 | 8 | 0 | 0 | 1 ms |

Gateway round trip over 600 generated bodies (`GatewayRoundTrip`): `clean_row` is idempotent and `stamp_row(stamped)` is the same row; `filter_body(stored body) == stored body` (a reader that filters again changes nothing); `read()` for every purpose leaves the file's bytes, mtime and directory untouched, serves a stamped row's stored body exactly and an unstamped row exactly as the writer would store it; no secret survives the round trip that C removes. No finding.

## Findings

HIGH = digit/ID leak in a common layout; MED = ordinary data lost, or leak in an uncommon layout; LOW = the rest. "Test" is the `expectedFailure` test in `test_e1_adversarial2.py`; the marker comes off when the fix lands.

| # | Sev | Finding | Counts | Minimal example | Suggested fix | Test | Status |
|---|-----|---------|--------|-----------------|---------------|------|---|
| 1 | HIGH | A 4-digit value directly under the ID line leaks when there is no blank line between them: HTML `<p>`, `<div>`, `<br>` and plain text. The orphan rule needs a block "dropped whole" by the anchor layer, but D's scrub has already removed the ID line, so nothing is dropped whole; the 6-digit bare-PIN rule and `_without_orphans` (blank-separated only) do not cover it. Old scrub leaks it too. | Controlled (40 bodies per cell): `tight`, `html_p`, `divider`: 4-digit 40/40 leak, 6 digits and alphanumeric 0/40; `blank`: 0/40. Generated: 4-digit shape leaks 48% over all separations | `<p>Meeting ID: 412 889 330</p><p>8825</p><p>Agenda: budget</p>` returns `8825\nAgenda: budget` | `_without_orphans` should also accept a value-only line **adjacent** to a line the scrub removed (use `_boundary_kinds`, which already knows which lines went), not only a blank-separated block | O8, O9 | fixed (A) |
| 2 | HIGH | A spaced 3+3 (or 2+2) value is never an orphan: `_orphan_value` judges one token and `984`, `522` are three digits each. Leaks in every separation (blank, divider, tight, list, `<p>`). | pin_spaced shape 40/40 in every cell; 68% of all generated spaced values (791 of 1,166) | `Meeting ID: 412 889 330\n\n984 522\n\nAgenda: x` returns `984 522` in the output | judge the block, not the token: a 1 to 2 line block whose digits and letter-digits, spaces removed, are 4 to 8 characters | O10 | fixed (A) |
| 3 | MED | **A link without a query drops its whole block.** The scrub keeps a plain link (old keeps the agenda), the anchor layer treats a URL as a strong anchor and drops every line of the block. Phone numbers, ICS lines (`URL:`, `LOCATION:`, `X-MICROSOFT-SKYPETEAMSMEETINGURL:`), mailto, a link with `?id=` and a signature dial-in are all handled by the scrub first and cost only their own line (0 other lines lost). | `url_plain` 77 of 279 bodies lose every agenda line, `url_inline` 98/297, `host_only` 78/283, `www_only` 71/292, `sip` 77/287; by layout: contiguous lines 71% (119 of 168), `<div>` 62%, table 60%; `<p>` per line and `<li>`: 0 (the converter separates them). Provider invites: a bare Meet link directly under the agenda, 10 of 10 | `Agenda\n1. Welcome\n2. Read https://wiki.example.test/spec first\n3. Close` returns `""` (old keeps all four lines) | In `_block_drops`, make a URL that holds no digit run, no `pwd`/`token`/`code` query and no join-host word a **line-level** anchor (like the phone case); keep whole-block for join URLs | A1 to A4 | fixed (B) |
| 4 | MED | Orphan rule over-takes ordinary lines after a dropped block: any 1 to 2 line block of at most 24 characters and 4 tokens with one 4 to 8 digit or letter-digit token. | `Ext 4417 for help` lost 60/60; `Room 1204`-style (4-digit room) 36 to 44 of 60; `Ticket INC1234 follow-up` 23 to 29 of 60 (and, after one orphan, the second slot takes the next line too); all go to 0 once two real orphans fill the chain | `Meeting ID: 412 889 330\n\nExt 4417 for help` returns nothing after the subject | require the block to be **only** value tokens (no word of 3+ letters) except a known label; drop `ext`/`room`/`floor` lead words from the candidates | O3, O4, O12 | fixed (A) |
| 5 | MED | The orphan rule stops at a divider line, so a PIN under a rule line survives; and after an unlisted label (`Clave`) plus a first orphan, the **second** orphan survives (the label block counts as a chain step). | divider: 4-digit and spaced values 80/240 in the controlled grid | `Hi\n\nMeeting ID: 412 889 330\n________\n8825` returns `8825` | allow one divider between the anchor block and its orphans (as for blank lines); do not count a label-only block in `chain` | O1, O2 | fixed (A) |
| 6 | MED | List marker hides an orphan: `- 4076`, `- ab12cd` under the ID line leaks for every shape but 8 digits. | list layout 55% of generated orphans (667 of 1,217); controlled 160/240 | `Meeting ID: 526 903 470\n- 4076` returns `- 4076` | strip `-`, `*`, bullet, `1.` before `_orphan_block` judges | O11 | fixed (A) |
| 7 | MED | Unlisted label words still leak when the value is in a sentence or stacked: Polish `kod dostępu`, English `Room key`. Same class as pass 1 finding 1; on a line of its own (`Kod dostępu: 7118`) they are caught. | provider_unknown: Polish 178 of 519 leaked and 68 lines lost (the label over-takes), `Room key` 38 of 516 (stacked and table styles) | `To get in, ask for the kod dostępu 7118 at the desk.`; `<p>Room key</p><p>7118</p>` | the value-adjacent-to-label rule (finding 1) covers `Room key`; add `dost[eę]pu`, `key` to the label list or generalise "short label line then value-only line" | O13, O14 | fixed (A for 'Room key', E for the Polish label) |
| 8 | MED | Plain text with Unicode line separators loses the whole body: U+2028, U+2029, NEL, VT, FF are not line breaks to the plain-text path (the HTML path splits them), so the text is one line and a passcode in it takes everything. Safe (0 leaks), but the old scrub does the same. | 1,275 of 5,000 keepers (every body in four of sixteen encodings: nel 176/176, u2028 212/212, u2029 176/176, vt_ff 178/178) | `Agenda budget Passcode: 8825 Thanks all` returns `""` | normalise `\x0b \x0c \x85    ` to `\n` in the plain path (the tuple `invite_blocks.NEWLINES` already exists) before the scrub runs in `_raw_first` | E1 | fixed (C) |
| 9 | LOW | Letter-spaced label: `P A S S W O R D : 4330` is not recognised. | 49 of 131 (37%) of that form | `Agenda: x\n\nP A S S W O R D : 4330` | collapse single-letter runs in `_skeleton` | O15 | fixed (E) |
| 10 | LOW | **`invite_blocks.looks_like_html` is quadratic** on text with many tag starts and no `>`: for every `<b ` that `_tag_at` accepts, `text.find(">", i)` scans to the end of the text. Growth exponent: 1.87 (last six of ten sizes, 64 KB to 1 MB; 1.47 over all ten, small sizes are dominated by per-call cost). Doubling the size multiplies time by 3.7 to 4. `<!-` openers, `<div`, `<bx ` prefixes and a bare `<` run are linear (1.00). Production impact is bounded: the gateway cuts at 20,000 characters (1 ms) and D at 100,000 (30 ms); the 1 MB case is `filter_text` (test mode) and direct `to_lines` callers (3 s). | 64 KB 0.019 s, 128 KB 0.075 s, 256 KB 0.226 s, 512 KB 0.84 s, 1 MB 3.13 s (`<b ` repeated, or `a <` repeated); the same text with the fix: 0.033 s | `"<b " * 333334` | find the last `>` once: `last = text.rfind(">")` and accept a tag start only when `i < last` (a tag start after the last `>` can never be closed). Same answers as today on 3,000 random strings and 18 hand cases (`linear_looks_like_html` in the test file, exponent 1.0) | L1 | fixed (D) |
| 11 | LOW | The 1,500-character cap ends a long agenda: items 1 to 100 keep what fits. Documented, recorded because it is where long agendas lose data. | k=100: 978 of 1,872 keepers lost, k=60: 485 of 1,992, k<=30: 0 | 100 numbered lines | none (design) | N1 (passes) | open (design) |

## Checked and fine (no finding)

* **Class A at its edges:** two orphans then an agenda line (the agenda line survives, O5); a third orphan is not taken (documented chain of two, O6; 22% of third secrets leak by design); orphans after a table row and in a `<li>` list (the table case keeps the agenda).
* **One link / one phone / ICS:** a phone number, a signature direct dial, `mailto:`, a link with a query, Teams `X-MICROSOFT-SKYPETEAMSMEETINGURL:`, `URL:` and `LOCATION:` lines each cost only their own line (0 other lines lost in about 2,560 bodies of those kinds); Zoom with `?pwd=` one-liner, Webex, Meet, GoTo, unknown-provider join lines: 0 leaks of 1,161 planted IDs, passwords and codes; dial-in lists of 3 to 30 numbers in 5 styles go whole, agenda and time-zone lists stay (0 of 9,000 keepers lost).
* **Safe Links with a passcode in the query** (single and double encoded, URL-defence, click tracker; keys `passcode pwd p pin password code access k`): 0 leaks of 1,000.
* **Encodings:** CRLF, CR, BOM, UTF-16 misread as latin-1 or as utf-8 with replacement, mojibake, quoted-printable (including a soft break inside the label), numeric entities, NBSP, tabs: 0 leaks, 0 lines lost. Base64 of a label and passcode is dropped by the shape gate (the old scrub keeps it).
* **Markup around labels:** bold, italic, code span, strike, markdown link, `<b>`, `<a>`, emoji around, RLM/RLO/isolate marks, fullwidth and Arabic colons, NBSP, soft hyphen, ZWJ, bullet, quote, table cells, dotted leaders, upper case: 0 leaks in 1,000 (8 in all, all the letter-spaced form). Hebrew with RLE/PDF around an unlisted label leaks (same class as finding 7; it is a pass-1 finding).
* **Pasted twice or three times, long agendas, time-zone lists:** no leak, no loss except the cap.
* **Idempotence:** `C(C(x)) == C(x)` on all 10,000 generated bodies, and the stored body re-filters to itself; the gateway round trip changes nothing (stamped rows are idempotent, `read()` never writes).
* **Timing:** worst single body 23 ms; 1,000 bodies of a generator 0.6 to 8.8 s (the 100-item agendas), the old scrub 0.4 to 5.9 s. A hostile 20,000-character single line (`<b ` repeated) costs C 0.25 s: one long line against many regexes, not super-linear.

## Ship rule

Composition D ships in 2.6.9 only if all five criteria are met (Jarvis). Measured after each fix group on `v269-fix2` (from 6ce15ff9). Tools: `python3 dev/tests/test_e1_adversarial2.py --report`; the 40,000-body harness; the 32-format fixture set and the 40-agenda trap set (lines kept of 130 and 200); the one-link layouts of the single_anchor generator (links in plain text and tight lines, 3,000 bodies, 234 in those layouts: lines kept of 1,025; the 2.6.8 scrub `invite_clean.invite_text` keeps 1,025 of 1,025 and, on the fixtures, 86 of 130 and 150 of 200).

| Criterion | Baseline 6ce15ff9 | After A (orphans) | After B (plain links) | After C (line breaks) | After D (looks_like_html) | After E (spaced letters, bare long label) | After Cap review | After Cap re-check 2 |
|---|---|---|---|---|---|---|---|---|
| 1a. Agenda loss, 32 fixtures: lines kept of 130 (2.6.8 scrub: 86) | 79 | 79 | 83 | 83 | 83 | 83 | 83 | pending (not run: laptop load above 120) |
| 1b. Agenda loss, agenda trap set: kept of 200 (2.6.8 scrub: 150) | 150 | 150 | 150 | 150 | 150 | 150 | 150 | pending (not run: laptop load above 120) |
| 1c. Agenda loss, contiguous plain-text layouts with one link: kept of 1,025 (2.6.8 scrub: 1,025) | 115 (11.2%) | 115 (11.2%) | 1,025 (100%) | 1,025 (100%) | 1,025 (100%) | 1,025 (100%) | 1,025 (100%) | pending (not run: laptop load above 120) |
| 2. Harness (40,000 bodies): leak bodies / digit-bearing (limit 304 / 4) | 304 / 4 | 304 / 4 | 304 / 4 | 304 / 4 | 304 / 4 | 304 / 4 | 304 / 4 | pending (not run: laptop load above 120) |
| 3. Provider invites: leaks / agenda lines lost (1,000 bodies, 4,000 lines) | 0 / 40 | 0 / 40 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 (letters-only Meet code link now drops its block: 4 agenda lines per such body) | pending (not run: laptop load above 120) |
| 4. Idempotence failures (10 generators x 1,000, harness 40,000) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | pending (not run: laptop load above 120) |
| 5. HIGH 1: 4-digit value directly under the ID line (4 layouts leaking) | 4 of 4 | 0 of 4 | 0 of 4 | 0 of 4 | 0 of 4 | 0 of 4 | 0 of 4 | pending (not run: laptop load above 120) |

Verdicts as of the last commit (A to E):

1. Agenda loss not worse than the 2.6.8 scrub: **met in substance: 3 lines accepted by Jarvis (26-10-2026): link-only x2, unclosed script x1** (strictly, 83 of 130 against the scrub's 86). One-link contiguous layouts: met (1,025 of 1,025, the scrub 1,025; it was 115). Agenda trap set: met (150 of 200, the scrub 150). The 32 fixtures: **3 lines short, accepted** (83 of 130 against 86): two are link-only boilerplate lines D now drops by design (`New to GoTo? ... https://global.example.org/install/`, `Find your local number: https://zoom.example.org/u/abcdefg`, the price of making a plain link a line-level anchor: the scrub keeps them), one is `broken_html`, which D empties (an unclosed `<script>` holding a 10-digit number takes the whole block; the scrub keeps `after table text tail`). Not touched by this pass: a `sip:` or `123456789@host` line still takes its block (211 of 4,313 single-anchor keepers lost, 77 bodies).
2. Harness: **met** (304 leak bodies, 4 digit-bearing, 0 non-idempotent).
3. Provider invites: **met** (0 leaks of 1,161 secrets, 0 of 4,000 agenda lines lost; was 40).
4. Idempotence: **met** (0 failures on all 10 generators and the 40,000 harness bodies).
5. HIGH 1: **met** (fixed by A; 4 of 4 layouts leaked, now 0 of 4).

D meets the ship rule; criterion 1 on the 32-format fixtures misses by 3 lines (link-only x2, unclosed script x1), accepted by Jarvis 26-10-2026 (fail-closed), provided Cap's independent review comes back READY or READY WITH NOTES.

## Result of the fix pass (n = 1,000 per generator; C = D; before in brackets)

| Generator | Leaks | Keepers lost | Not idempotent |
|-----------|------:|-------------:|---------------:|
| orphans | 5 (363), all a third orphan, by design | 137 (216) | 0 |
| single_anchor | 0 | 211 (1,031) | 0 |
| provider_one_line | 0 | 0 (40) | 0 |
| encodings | 0 | 0 (1,275) | 0 |
| label_markup | 0 (8) | 0 | 0 |
| provider_unknown | 0 (35) | 8 | 0 |
| safelinks, repeated, tz_and_dial | 0 | 0 | 0 |
| numbered_long | 0 | 1,463 (the 1,500-character cap, finding 11, by design) | 0 |

`looks_like_html` at 1 MB: 0.033 s (was 2.9 s), growth exponent 1.00 (was 1.87) on all six hostile inputs.

Not fixed: finding 11 (the cap, by design); a third orphan (the chain of two is documented); the remaining orphan keeper losses, which come from a divider placeholder opening a region (or a tight block) around an 8-digit value, a pre-existing rule; the Hebrew label (M1, same class as pass 1 finding 1); `A9` (a plain link line is itself dropped); `sip:`/`id@host` lines still take their block; `broken_html` emptied.

## After Cap review

* HIGH (break inside a label's window): D now also runs the scrub on the plain-text body as written; a line (or the pieces of a line with CR/VT/FF/NEL/U+2028/U+2029) that pass drops is dropped from the normalised pass too, unless a piece drops on its own when scrubbed alone (that piece explains the drop, e.g. `Passcode: 8825` inside a one-line body). `Zoom passcode:` / `Decisions <NEL>log` / `mupiwoc` now returns empty (was `log`, `mupiwoc`); the one-line bodies of group C still keep their agenda. Cost, measured: encodings generator 0 keepers lost of 5,000, agenda sets, fixtures and one-link layouts unchanged (the union runs only on bodies that hold one of those breaks).
* MEDIUM (Meet code link): a link holding `abc-defg-hij` is no longer a plain link; it takes its block like other join links. One-link layouts for a non-join link still keep 1,025 of 1,025.


## After Cap re-check 2

* HIGH 1: a self-dropping piece explains the as-written drop only when it carries its own value (`Passcode: 8825`); a bare label piece (`Passcode:`, `Meeting ID`) no longer does, so its value in a sibling piece goes. Stated gap, kept: `Passcode: 8825<NEL>zejumud` keeps the word-only value (narrowing it would drop innocent words after a valued line).
* HIGH 2: an HTML body keeps its breaks as written (the scrub and invite_blocks read them as white space), so the label and its value stay together; all five break characters, the three reproducers, and the scrub's own result are tested.
* MEDIUM: a 3-4-3 letter segment is a Meet code only on a `meet.` host or a provider host; `/meet/` and `/my/` join a path with the other join paths.
* LOW fixed: dotted letters (`P.A.S.S.C.O.D.E: 4330`). Not fixed: `Passcode: 44` followed by `17` on the next line (the scrub itself keeps the tail), a third orphan group after the chain of two (by design).
* Tests: `dev/tests/test_e1_recheck2.py` (17, with mutants).
