# v191-ask-claims: BL-314 parts (a) and (b), for Team 1

Branch `v191-ask-claims`, from `origin/main` (2c4c42f). Not pushed.

## Built

**(a) Claims checked.** `system/scripts/claims.py` (new, library only, standard library, Python 3.9). `Run._on_assistant` in `live_server.py` passes each chat text block through `claims.check` before it is emitted or kept in the chat history:
- every work-item ID (`ABC-A-001`, RAID `ABC-001`, `ABC-D-001`, milestones, promises) is looked up through tracker.py's read functions (`connect_or_raise`, `item_row`, `fetch`), one read-only connection per block;
- a title given beside the ID (after `·`, `—`, `–`, `:`, ` - `, in brackets, or a table's title column) that doesn't match gets `(⚠ doesn't match the tracker: <real title>)`. Matching is lenient (a shortening, `…`, or a close paraphrase passes) so only a clearly different title is flagged. The 12-10 case, "FAL-A-007 · Set up weekly cadence", is a test;
- an owner given beside it (`owner X`, `owned by X`, a register name or alias in its own piece or brackets, a table's Owner column) that isn't the item's owner (full, first name or alias) is corrected inline: `Sara Khan (corrected from the tracker: the reply said Omar)`;
- an ID of a registered project that isn't in the tracker gets `(⚠ not in the tracker)`;
- the `text` event carries `checked: [{id, kind, said, real}]` only when something changed. The page (`claimsNote`) adds a quiet line, "Checked against the tracker: 1 title didn't match.". The debug log keeps IDs and kinds only.
- Only `kind "ask"` runs. Text in a ``` fence is skipped. Any fault shows the text unchanged.

**Streaming.** The server runs `claude -p --output-format stream-json` without `--include-partial-messages`, so each `assistant` event's text part is a whole content block, never a fragment. That block is the safe boundary: it is checked whole and then emitted, so nothing unchecked reaches the page and an ID is never split across chunks. The `result` text isn't shown as text, so it needs no check.

**(b) The plain "I can't".** The things the panel can never do, whatever is confirmed: Microsoft 365 actions (send, forward or reply to mail; post in Teams; create, move or answer invites; SharePoint or OneDrive changes online) and starting or stopping the live server, the app or the login agent.
- `claims.cant(title, body)`: a `CONFIRM:` asking for one of these isn't offered as Go ahead. A `cant` event `{what, line, go}` goes in its place.
- `claims.cant_denied(denials)`: a refused tool call of the same kind (an M365 action tool, `live_server.py`, `launch.py`, `launchctl`) leads the `denied` lines with the same event.
- The page (`cantCard`) shows one sentence and a button to where it can be done: **Draft email to <name>** (`openDraftEmail`, chase mode when the request says chase or nudge), else **Open People**, **Open Today**, **Open Files**, **Open Settings** (› Live server). The sentence is kept in the chat history.
- `ASK_PROMPT` gained two sentences: copy titles and owners from the tracker (they're checked), and say "I can't" first and never CONFIRM these.

**Not built (as instructed):** routing chat changes through the dashboard's own actions (BL-314's "Same actions"). That is a guard decision for Alan.

## BL-141 unchanged

`claims.py` only changes words and offers. It decides nothing about what is allowed. `reach.py`, the hook, `filechange.py`, `permissions.py`, `DENY_TOOLS`, `READ_TOOLS`, `WRITE_TOOLS` and `SCRIPT_COMMANDS` are untouched. `claims.py` has no command line, so BL-267's list needs no entry. These pass unchanged: `test_guard_pinned`, `test_reach`, `test_record_commands`, `test_script_policy`, `test_ask_access`, `test_admin_card` and `test_run_read_pinned` (its pinned events are unchanged, because a reply with no IDs or no mismatch emits exactly what it did before).

## Files

`system/scripts/claims.py` (new), `system/scripts/live_server.py` (`_checked`, `_cant`, `_cant_of`, two hooks in `_end_answered`, `ASK_PROMPT`), `system/templates/dashboard/src/ask.js` (`claimsNote`, `cantCard`, `cantGo`), `style.css`, `core/globals.json`, the rebuilt `dashboard.html`, `system/templates/help.md` (two bullets under ask creaite), `dev/dashboard-spec.md` (two bullets after BL-201's refused step), `system/creaite-rules.md` (folder map lists `claims.py`), `dev/tests/test_tracker.py` (`make_vault` copies `claims.py`), and `dev/tests/test_ask_claims.py` (new, 19 tests, quick tier).

## For Team 1

- Run the full suite on Actions. Locally I ran 30 files at `-j 2` and all passed. No Chrome test draws the new `cant` card or the checked line. A hand check in the panel would confirm the look (`.msg.a.cant`, `.step.checked`).
- Possible follow-ups: owner claims on a following line (`- Owner: Omar` under the item) aren't checked; due dates and statuses beside an ID aren't checked.
