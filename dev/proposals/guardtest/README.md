# guardtest

`tests-yml-fetch-depth.diff` (guarded: `.github`): sets `fetch-depth: 0` on both checkouts in `.github/workflows/tests.yml`, so check 9
of `test_word_export_227.py` has history to diff against and runs in CI. Without it the shallow clone has no history. The test now
FAILS (not skips) when `CI=true` and the base commit is missing, so a CI run without this diff is red rather than quietly green.
Checked with `git apply --check` and `git apply -R --check`.

## The guarded list (check 9) and edit_ai.py

Check 9 watches eight files in `system/scripts/`: `tracker.py`, `filechange.py`, `reach.py`, `permissions.py`, `backup.py`, `update.py`,
`live_server.py` and `client_leak.py` (Jarvis, 23-10-2026). The approved chain may change them only as its pinned diffs say
(`GUARDED-2.6.1.md`). Against the v260 release commit the eight files do not differ on `origin/v261-line2`, so the check passes there with no chain.

`edit_ai.py` is NOT on the list. For Jarvis to judge, this is exactly what it does (read from the file, 23-10-2026):
- **Runs as:** a script the live server calls through `run_stdin("edit_ai.py", body, "context")` and `"result"` (`live_server.edit_ai_route`),
  and `options`. It is plain Python, and it starts no process and calls no network, shell or Claude itself.
- **Reads:** the request on stdin (the selected text, option, place, project code, an optional client-report `document`, `recipients`);
  `system/templates/drafts/edit-ai.md` (the prompt template); the tracker through `tracker.connect()` with SELECT queries only (project
  codes, open item ids and owners, whether an id exists, whether a project is known, client-visible items for the client place); the people
  register and `identity.own_domains` in settings; and, through imports, `client_leak`, `client_output`, `drafts`, `report_doc`,
  `report_server`, `creaite_doc`, `status_checks`, `confusables` and `paths`.
- **Writes:** nothing. No file, no database row (no INSERT, UPDATE or DELETE in it). It prints one JSON object. The accept counts in
  `draft-stats.json` are written by the page's `/api/draft/stat` route in `live_server.py`, not by it.
- **Executes:** nothing. The model run it feeds is built in `live_server.py` (kind `edit-ai`): `--tools ""`, `--strict-mcp-config`, an
  empty allow list, every reading, writing and Microsoft 365 tool denied by name, and no `--add-dir`. Those settings are in
  `live_server.py`, which IS on the list, so they cannot move without the check seeing it.
- **Routes:** `POST /api/edit/ai` and `POST /api/edit/ai/caps` (token-checked).
- **What a change to it could affect:** it is the client-safety gate for AI suggestions. It decides the place (never the page's claim),
  refuses selected text that already holds something a client must not see, builds the prompt (what the model is shown), and drops a
  suggestion that brings in an internal item, internal wording, a person or the word VIP (through `client_leak`, which IS on the list).
  A weakened gate would let such text reach a suggestion shown to Alan, who must accept it before anything changes, and could show the
  model more than the text, option and project facts. It cannot by itself write, run or send anything.
