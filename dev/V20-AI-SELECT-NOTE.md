# v20-ai-select: BL-301 part D, AI on selected text (handover to Team 2)

Branch `v20-ai-select`, from `origin/v20-base`. Started by Team 1 on 14-10-2026; **handed over to Team 2 mid-part** (WIP).
Read BL-301 D in `git show origin/dev-archive-security:dev/BACKLOG.md` and the brief's rules first.

## Done

- **Server.** `system/scripts/edit_ai.py` (new): the options (`OPTIONS`), each place's options (`PLACES`: `current`, `plain`,
  `notes`, `email`), the prompt (`context`: the selected text, the option, and the project's name, owners of its open items and
  its open item IDs; nothing else), the reply parser (`<<<SUGGESTION … SUGGESTION>>>`, else the whole reply) and BL-106's
  plain-code check (`check`: dates and numbers via `status_checks.kept`, item IDs, people-register names and new capitalised
  names, lost or added). Prompt template `system/templates/drafts/edit-ai.md`; Make it executive adds `report.style_guide()`.
- **Route.** `POST /api/edit/ai {option, text, code, place, instruction, run}` in `live_server.py` (`edit_ai_route`, on
  `DRAFT_ROUTES`), through the run engine (one run at a time, Stop via `data-drstop`), `EditJob` (a `DraftJob` whose `SCRIPT` is
  `edit_ai.py`, `quiet`), ending in a `draft` event `{text, notes}`. Debug log: option, place and length only.
- **Page.** `core/editor.js`: `ED_HOOKS.ai`, the `ai` option of `creaiteEditor` (`{place, project(), confidential(), key()}`),
  `edRange`, `edSelection` (a run inside one textblock is inline; across blocks it widens to whole blocks; Markdown by the exact
  writer), `edReplace` (one transaction, refused if the range's text changed). `stores/aiEdit.js` (bar, suggestion, Accept,
  Discard, Try again, Show changes word diff, confidential asks once per `key()`, counts `offered`/`used`/`rejected` under feature
  `edit` via `/api/draft/stat`). `components/AiSelect.jsx`: `AiBar` (Menu block + "Or say what you want…" box), `AiSuggestion`,
  `AiLayer` (`#aiLayer` on the body, fixed), `AiMenu`/`mountAiMenu`, `bootAiSelect` (called first in `main.js`). Keys: select
  (⌘A for all) then Alt+/ opens the menu; Esc in the card discards. CSS block at the end of `style.css` (tokens only).
- **Places wired:** Current state's two panes (`current`); the peek's multi-line fields (`plain`, the item's project); the Prep
  page's notes and questions (`TextEditor`'s new `ai` prop, `plain`, the meeting's project). **Make it executive**: Current
  state's own button is gone; it is the "Make it executive" item of **AI ▾** beside Save (`#curAi`, `data-exec` on the item),
  which still runs the BL-106 whole-text flow (facts, evidence); the other AI ▾ items select the whole pane and use the new route.
- **Tests:** `dev/tests/test_ai_select.py`, 14 tests, **all pass** locally (6 script, 8 Chrome against the live server with a
  stand-in Claude that records its argv). `test_tracker.make_vault` copies `edit_ai.py`. `test_status_live_browser` and
  `test_evidence` updated to open AI ▾ before `[data-exec]` (**not yet re-run**). `check.py` OK, typecheck 0, globals regenerated,
  dashboard.html rebuilt.

## Finished by Team 2 (14-10-2026)

- **Wired:** the Prep popup's shaped notes (`PrepShape.jsx`: `plain`, the meeting's project `prepNow().m.p`, confidential when the
  shaping or the invite says so, asked once per meeting); Prep page's boxes now also ask first for a confidential meeting; **the
  peek's title** (place `line`, below).
- **The title stays one line (Alan's decision):** a new place `line` (Rewrite clearly, Shorter, Make it executive, Fix spelling,
  Or say what you want) with its own format rule ("one line of plain text only"); `edit_ai.py result` folds any line break the
  reply has into a space, and `edReplace` does the same for any `multiline: false` editor, so Accept never breaks the line.
- **Part E's seam:** `stores/aiEdit.js` `aiAction({id, name, line?, icon?, places?, run(range, h, ai)})` registers an item on the
  bar's menu, listed before "Or say what you want…"; picking it hands over the selection (no Claude run, no counts). Not on
  Current state's whole-text AI ▾. `AI_ACTIONS` holds them.
- **Tests:** `test_block_ai_select.py` (AiBar and AiSuggestion on a fixture: ARIA, keys, focus, escaping, Accept and ⌘Z, one-line,
  the refused Accept, the part E seam), `test_ai_select` + the title test and the `line` script test, `test_prep_shape` + the
  popup's notes (and the confidential ask). `aiDiff`'s locals renamed (test_dashboard_split read `A` as data.js's).
- **Docs:** Help (step 9 of "Let creaite draft the wording", the AI drafts reference, Alt+/ in Keyboard shortcuts, Make it
  executive's move), `dev/dashboard-spec.md` (its own section, and Make it executive's line), `creaite-rules.md` (`edit_ai.py` in
  the folder map; a Dashboard editing bullet for the route and the run kind), the release notes, COMPONENTS.md's row.
- **Still open:** Notes (part B) pass `ai: {place: "notes", project, confidential: () => note.confidential, key: () => path}`; the
  Draft email's `email` place waits on Part A's option (b). Programmatic focus-then-select (item 6 of the old list) not looked at.

## Alan's decisions (14-10-2026, to Team 2)

- **The security changes are approved as they are:** the `/api/edit/ai` route, the tool-less `edit-ai` run kind and `edit_ai.py`
  READ in `SCRIPT_COMMANDS`. Not to be widened.
- **Two executive paths, accepted as built:** a selection uses the quick route; the whole Current state keeps BL-106's full flow.
- **Peek title: AI on a selection there too,** one line: the suggestion stays one line and Accept never inserts a line break
  (tested).
- **No Settings switch.** None built.

## Security changes (approved by Alan, 14-10-2026)

- **New route** `POST /api/edit/ai` (token-checked like every POST; local only).
- **New run kind `edit-ai`, with no tools at all:** `KIND_TOOLS["edit-ai"] = []` (empty allow list); `KIND_DENIES["edit-ai"]` =
  Read, Grep, Glob, Bash, Write, Edit, NotebookEdit, WebFetch, WebSearch, Task, Agent, Skill and every Microsoft 365 reading
  tool, on top of the usual denies; new `KIND_ARGS["edit-ai"] = ["--tools", "", "--strict-mcp-config"]` (no built-in tools, no
  MCP servers) added to the `claude` command in `Run.__init__`; `TOOLLESS_KINDS` gives it no `--add-dir`. Not guarded (nothing to
  guard), not chat history. No Bash, no writes. The test checks the real argv.
- **`reach.SCRIPT_COMMANDS`:** `edit_ai.py` `context`, `result`, `options` as READ (BL-267's list must classify every script).
- Unchanged: `reach.py` rules, the hook, `permissions.py`, `.claude/settings.json`, BL-267's gate, `test_guard_pinned`.
- Known limit: the run's working directory is still the vault, so Claude Code loads the vault's `CLAUDE.md` into its context;
  with no tools it can't read anything else. A temporary empty directory as cwd would avoid that (it would still load
  `~/.claude/CLAUDE.md`).

## Open questions for Alan

All three answered (above).
