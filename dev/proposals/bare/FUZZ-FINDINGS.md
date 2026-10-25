# Fuzz findings: HTML, lists, quotes, tables, invites (#369, against bfb65603)

Test: `dev/tests/test_invite_clean_fuzz_html.py` (8 seeded generators, 5,000 bodies each by default, 200,000 with `FUZZ_FULL=1`; seed 369).
Full run: 200,000 bodies, about 20 to 60 seconds per generator (about 1 ms a body), run in parallel. Quick tier: 40,000 bodies, 31 seconds.

**Idempotence: no failure in 200,000 bodies.** `invite_text(invite_text(x)) == invite_text(x)` held everywhere.

**No leak at all** in `mixed_invite` (Teams/Zoom/Webex shapes) and `nested_lists` (ul/ol 1 to 3 deep, labels and values at different depths).

Leaks (planted value still in the output). Classes A to F are open at bfb65603; `classify()` in the test lists them so the file passes today; delete a class there when it is fixed.

| Class | Property | Minimised example | Count in 200,000 | Status |
|---|---|---|---|---|
| A: qualified label alone on a line, value on the next line or cell (`Passcode required`, `PIN below`, `Access code - Teams`, with or without a colon; also in `<p>`, `<br>`, `> ` quotes, table cells, accents and confusables) | leak | `PIN below` / `ZQ6717` | 28,685 (with B) | KNOWN |
| B: a provider suffix on any qualified label (`Passcode is - Zoom`, `PIN to follow - Teams`, `Passcode (required) - Zoom`, `Access code - Teams:`) | leak | `Passcode is - Zoom` / `86864` | 5,684 | NEW (the same-line forms and the bare forms `Passcode is` / `PIN to follow` / `Password for the room` are removed; only the suffix leaks) |
| D: a label in a header row with other header cells, value in the first cell of the next row (HTML `<th>`/`<td>`, markdown table, tab- or space-separated columns) | leak | `<tr><th>Passcode</th><th>Other</th></tr><tr><td>4417</td><td>x</td></tr>` gives `4417 x`; also `\| Passcode \| Other \|` / `\|---\|---\|` / `\| 4417 \| x \|` | 10,727 (HTML table generator only; markdown and tab forms probed by hand) | NEW. Digits, hex, mixed and words all survive. Works when the label is the last header cell (`Room \| Passcode`) |
| E: a mixed token of 1 to 6 letters and 1 or 2 digits under a soft heading (`Secret Santa` / `Tb28`, `Password reset` / `ZQ27`, `Dress code` / `kx99`) | leak | `Code review` / `Tb98` | 13 | NEW but probably by design: it looks like Q3 or H2 (the everyday-code exemption). Needs a decision, not necessarily a fix |
| F: a word-only value after an ID label with no separator (`Meeting ID bluebird`, `Meeting ID` and `bluebird` in two table cells, `> Meeting ID kestrel`) | leak | `Meeting ID walrus` | 697 | KNOWN (listed under the lines rule in NOTES-2.6.8) |

Counts per generator (leak, class): accents A 3,479; blockquote A 4,445, F 50; html_table A 1,574, D 10,727, F 647; md_table A 2,180; qualified A 17,007, B 5,684; soft_dates E 13. Two classes C and G found while probing turned out to be A in disguise (`Passcode required:` / `Please enter` / `4417` leaks only because of A; `Passcode is:` / `Please enter` / `4417` is removed).

**Not planted by this fuzz (known, from the brief):** the date left after `Meeting ID.` (a stop mark). The generators do not use a full stop after a label.

**Not found:** dial-in numbers with `,,123456789#`, `Phone Conference ID`, `Access Code`, `Host key` in Teams, Zoom and Webex layouts (also as table rows and `<p>` per line), a date or time line between a soft heading and a digit value (the value still goes), nested blockquotes, and Cyrillic, accented, zero-width and no-break-space labels all pass, except where they sit in class A, B, D or F.

Classes are keyed on the planted value's label and layout, not on the minimised text, so a body mixing a known and a new class is reported under the label of the value that leaked.
