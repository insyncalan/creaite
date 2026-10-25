# #132: Cap's 23 commits, classified (25-10-2026)

Range `cdd76622..ai-models-132-apply` (head 9d2cf531), restored locally from the backup bundle. **Guarded** means a file in `dev/tests/guarded_chain.py`'s `GUARDED` list or the plan's guarded list: `live_server.py`, `reach.py`, `permissions.py`, `edit_ai.py` (it is on that list), `tracker.py`, `creaite-rules.md`, `.claude/settings*` and `dev/tests/pinned/guard/decisions.json`. No commit touches `tracker.py`, `creaite-rules.md` or `.claude/settings*`.

Summary: 12 commits touch no guarded file (ported by hand or cherry-picked), 11 touch one or more (the guarded parts are now patches 02 to 06; the unguarded parts of those commits are ported). Nothing was merged or pushed from the old branches; only code was taken, and the new commit messages are written fresh.

| # | Commit | What | Guarded files | Landed as |
|---|---|---|---|---|
| 1 | ad69aea9 | #132: providers.py, the AI models policy (providers, four kinds of job, limits, routing) w | none | ported (providers.py first cut; superseded by the whole-file port) |
| 2 | 071e64cd | #132: the AI model settings (ai.jobs, ai.accepted_weaker, ai.on_limit, ai.providers) with  | none | ported by hand (settings tabs moved) |
| 3 | 526a67ee | #132: the /api/ai/... routes (state, test, connect, forget, offer, disconnect, choose, lim | live_server.py | providers helpers ported; routes in patch 02 |
| 4 | e8ff8833 | #132: Settings › Essentials › AI models: provider cards, the connect journey, four kinds o | none | ported by hand (page, css, settings.js) |
| 5 | a6e9832d | #132: browser test for AI models (fake provider), the settings page's section count, the c | none | ported (page test, skips until patch 02) |
| 6 | ef15b3d6 | #132: AI models names its settings (data-keys), so the settings page's every-setting check | none | ported (data-keys) |
| 7 | 3fd8ff83 | #132: Help and the dashboard spec for Settings › Essentials › AI models | none | spec ported; Help line waits for the chain |
| 8 | 36e2b36f | #132: check.py clean: providers.state split into card, job_view and limit_view; docstrings | none | ported (providers split, docstrings) |
| 9 | 078f19b2 | providers.py: import paths at module level so doctor's 'Scripts take locations from paths. | none | cherry-picked -x (clean) |
| 10 | 226675f8 | Merge origin/ai-models-132-tests (#132 non-guarded build) into ai-models-132-apply | live_server.py | merge commit: not ported |
| 11 | fbe761e9 | #132: the round 1 and round 2 proposal folders and their tests, brought in to check the ap | none | old proposal folders and proposal tests: not ported (listed under next) |
| 12 | b5086271 | #132 G1: the key store in this Mac's login keychain, applied as Alan approved (17-10-2026, | live_server.py, permissions.py, reach.py | patches 03, 04 (live_server part in 02) |
| 13 | 64058af9 | #132 G1c: the never list in the runs creaite starts itself (prep, held), applied as Alan a | decisions.json, reach.py | patch 03 and 06 |
| 14 | cf360697 | #132 G2: the model list over HTTPS (api.openai.com, api.anthropic.com only, no proxy from  | none | providers.py ported; no guarded part needed |
| 15 | 311662c6 | #132 G3: the chosen model in every claude -p launch (default: today's launch), applied as  | live_server.py | patch 02 (G3) |
| 16 | a3a80753 | #132 G5: confidential material only to Claude (route_for, send_allowed; the Step down fix) | live_server.py | patch 02 (G5); providers part ported |
| 17 | 83f86c9e | #132 round 1 tests on the applied stack: two single-diff assertions read the tree's applie | none | test fix for the old proposal tests: not ported |
| 18 | 879133d4 | #132 S1: Search's answer may not read the never list's secrets and system folders, applied | live_server.py | patch 02 (S1) |
| 19 | f32ccf8b | #132 G4: the OpenAI direct call for AI on selected text (ten declared options, clean text  | edit_ai.py, live_server.py | patches 02 and 05 (G4); providers part ported |
| 20 | 511f8146 | #132 G6: Claude's limit and the Ask me card, re-based on G4, applied as Alan approved (17- | live_server.py | patch 02 (G6); providers part ported |
| 21 | 7fb994c2 | #132 G7: the quick-edit retry (once, only to a stronger model, inside the same run), appli | live_server.py | patch 02 (G7) |
| 22 | 7b1656ad | #132 G9: AI models in Settings › Health (names and counts only, never a key), applied as A | none | health.py ported (G9) |
| 23 | 9d2cf531 | #132 G10: the test-fakes switch only in the development repository or a test vault; the te | live_server.py | patch 02 (G10); providers part ported |

Two things the old commits did not have:

- 226675f8 is a merge commit that lists `live_server.py` only because it joins two branches; it adds nothing new.
- The proposal folders (`dev/proposals/ai-models/`) and the `test_ai_proposal_*` suites (fbe761e9, 83f86c9e) tested the old single diffs. They are not ported: patches 01 to 07 here replace the diffs, and the tests worth keeping (G1 key store, G2 lister, G5 gate, G6 limit, G7 retry, G10) are listed under "Next" in README.md for porting once the patches land.
