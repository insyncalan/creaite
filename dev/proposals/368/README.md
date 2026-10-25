# #368: client_leak.py reads the sent-line check on every form

`client_leak.py` is guarded: `client_leak.py.diff` (against origin/main). Verify `git apply --check dev/proposals/368/client_leak.py.diff` (clean). Full review before it lands.

What: `_context_findings` also checks the text as given and the raw text, not only `as_shown(text)`, so a sent line is found in any of the three forms (fail closed). `linktext.sent_has` already reads each on its plain form, so main's behaviour is kept; this only adds forms.
Tests: `dev/tests/test_sent_lines_internal.py` and `test_sent_shapes_368.py` pass with and without the diff (the shapes are read by linktext alone); test_client_leak passes with it applied.

## Follow-up, left out of 2.6.8 (a separate fix, needs a browser)
Cap's `deSent` change in `system/templates/dashboard/src/drafts.js` (a new mode is a new send: `sendMode`) and his two additions to `dev/tests/test_sent_it_person_menu.py` (`test_fix5_switching_the_mode_mid_retry_starts_a_new_send`, `test_fix5_a_mode_changed_in_place_is_a_new_send_too`) are in 1c452612 and not taken here.

## Review of 20c7d25a: findings and what was done
| Finding | Outcome |
|---|---|
| M1 page decoded only nbsp/lt/gt/amp | Fixed: `sentUnescape` in `linkText.js` follows Python's `html.unescape` (numeric references by Python's own rules, tested for every code point 0 to 0x10FFFF; named references from a generated allow-list, `sentEntities.js`: the HTML5 names whose text is only the letters the pattern needs, digits, spaces, hyphen or colon). A name outside the list stays as written on the page; it cannot make or hide a sent line. Fixtures: `by&#32;email`, `&#x20;`, `&#58;`, `&colon;`. |
| M2 strip rewrote the whole field in normalised form | Fixed in Python and JS: matching runs on the normalised form character by character with a map back; only the sent line is cut, the rest keeps its characters (accents, Devanagari, Greek, Cyrillic). Mutant test shows a whole-field rewrite is seen. |
| LOW 4 quadratic time | Fixed in both: each scan is bounded (400 characters for the name and the text before "by", 50 for spacing); 1 MB inputs read in about a second; a name over 400 characters is no longer matched (not a real name). Mutant: dropping the bound times out. |
| M3 strip cuts to the end of the line | Accepted (fail closed). `drafts.js` writes one sent line per line, so nothing real is lost. |
| LOW 5 look-alike letters not in the page map | Recorded: the page map holds every look-alike Python maps to the letters of chased/emailed/asked/by/email/message, hyphen and colon (generated); other homoglyphs need hostile input and matter only for those letters. |
| LOW 6/7 variants such as `e-mail`, `by Teams` | Recorded as known limits: `sentLine` in `drafts.js` writes only `by email` or `by message`, so they are not added. |
