# #368: client_leak.py reads the sent-line check on every form

`client_leak.py` is guarded: `client_leak.py.diff` (against origin/main). Verify `git apply --check dev/proposals/368/client_leak.py.diff` (clean). Full review before it lands.

What: `_context_findings` also checks the text as given and the raw text, not only `as_shown(text)`, so a sent line is found in any of the three forms (fail closed). `linktext.sent_has` already reads each on its plain form, so main's behaviour is kept; this only adds forms.
Tests: `dev/tests/test_sent_lines_internal.py` and `test_sent_shapes_368.py` pass with and without the diff (the shapes are read by linktext alone); test_client_leak passes with it applied.

## Follow-up, left out of 2.6.8 (a separate fix, needs a browser)
Cap's `deSent` change in `system/templates/dashboard/src/drafts.js` (a new mode is a new send: `sendMode`) and his two additions to `dev/tests/test_sent_it_person_menu.py` (`test_fix5_switching_the_mode_mid_retry_starts_a_new_send`, `test_fix5_a_mode_changed_in_place_is_a_new_send_too`) are in 1c452612 and not taken here.
