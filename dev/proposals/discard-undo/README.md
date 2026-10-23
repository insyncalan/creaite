# #307 path 12: Undo for Intake's Discard

Discard (`review.py reject N --discard`) set a held proposal aside in `system/staging/discarded/` with no way back. Now it has one.

## Apply order (each `git apply --check` and `-R --check` verified on line2, and after the GUARDED-2.6.1.chain, in this order)
1. `review.py.diff` (shared engine, not guarded; its own small diff): `review.py restore-discarded <file>`. Discard's marker also keeps the staging name (`"name"`), so a `-2` name goes back under its own. Restore takes a bare `proposed-*.json` name from `discarded/` only (no path, no `..`), refuses a name already waiting in staging, a file Discard didn't write and an unreadable one; each in words, exit 2, nothing moved. It removes only the marker, so the file is back byte for byte; nothing touches the tracker.
2. `reach.py.diff` (guarded): `"restore-discarded": RECORD` in `SCRIPT_COMMANDS["review.py"]`, so a run Alan hasn't confirmed refuses it (`test_record_commands` fails until this is in).
3. `live_server.py.diff` (guarded): `POST /api/review/restore-discarded {file}`. Token and Host from `do_POST`; `page_call` (403); a bad body 400; the development copy refuses; the job lock waited for 10 seconds at most (a plain refusal after); reply is review.py's words.

Page (committed, no guarded file): `review.js` `heldDiscard` toast gets Undo, which calls the route and says "Put back: <title> is waiting in Intake again."; without the route diff the Undo says what the server answered.
