# #186: the Draft email's AI bar for outside recipients, the guarded part

For Alan's approval. The design and his six answers (20-10-2026) are in `origin/proposal-186`
(`dev/proposals/draft-email-client-facts/README.md`); this branch builds it on top of the landed #262/#263 work.

## What is already on this branch (not guarded)

- `system/scripts/edit_ai.py`: the server decides who the email is for from its addresses (`email_outside`, against
  Settings › You › Own email domains). An outside email, or one creaite can't read as plain own-domain addresses, gets the client
  facts only (client-visible items, no people), the selection refused before Claude when it holds an internal item, and a
  suggestion that brings in anything internal dropped with a plain reason. Addresses sent with any other place are refused.
  #263's Client messaging and #262's minutes rules are unchanged.
- The page (`drafts.js`, `aiEdit.js`, `editor.js`, `server.js`) and the help text. The page asks `/api/edit/ai/caps` once; until
  the server says yes it keeps the bar off for outside recipients (#133's interim) and sends no addresses.

## What this diff does (guarded: `live_server.py`)

`live_server.diff` lets `recipients` through to edit_ai.py (whole, never cut: more than 50, non-text, over 320 characters, or with
any place but the email is a 400 with a plain message), and adds `/api/edit/ai/caps` (says the server decides the audience, and
whether the own-domains setting is usable; never the domains). It is the server half of the reviewed proposal (Team Cap's delta
review of a0ec6a2f and 53e0f0be), unchanged.

**Until it is applied:** the bar stays off for outside recipients, as today. An internal email's request carries no addresses, so
edit_ai.py counts it as outside (fails closed): internal emails get client facts and the client check until the diff lands.

## Apply and undo

- Apply, from the repo root: `git apply --check -p0 dev/proposals/draft-ai-186/live_server.diff`, then
  `git apply -p0 dev/proposals/draft-ai-186/live_server.diff`.
- Undo: `git apply -R -p0 dev/proposals/draft-ai-186/live_server.diff`. The page falls back by itself (caps gets a 404).
- Order: after `client-output-k` (`client_leak.py`, no overlap) and the other `live_server.py` proposals; it touches only the
  `/api/edit/ai` block (`EDIT_AI_KEYS`, `edit_ai_request`, `edit_ai_route`, `DRAFT_ROUTES`) and the route list in the module
  docstring. Do **not** also apply `origin/proposal-186`'s `edit_ai.diff`, `proposal-263` or `proposal-262`: their edit_ai.py part
  is already here.
- Tests: `python3 dev/tests/test_email_client_facts_186.py` (27; it patches a scratch copy of the server until the diff is in the
  repo, then checks the real file). `EMAIL_186_MUTATE=<name>` breaks one piece and must go red (23 mutations, all red).
