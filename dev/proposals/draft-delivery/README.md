# #183 Draft email delivery: the guarded half (proposal for Jarvis)

**Status: a proposal. `live_server.py`, `system/creaite-rules.md` are guarded; nothing here is applied.** Both diffs pass
`patch -p1 --dry-run` and `git apply --check` against `origin/main` (dcd8a7b6, 20-10-2026), in either order; the review fixes
(M1, L1, L2, the rebased rules hunk) are on branch `v26-draft-delivery-fix`, off f17a5b8f (#183 review, 20-10-2026). Brief: `origin/pm-intake-briefs:dev/sprints/183-draft-delivery-brief.md`
(locked by Alan, 19-10-2026).

## What is in this folder

| File | What |
|---|---|
| `live_server.diff` | The two routes: `POST /api/email/draft` (create, copied) and `POST /api/email/outlook-access` (the Settings Check). One block, after `/api/chase/pane`. |
| `rules-and-skill.diff` | `system/creaite-rules.md` ("Microsoft 365 actions stay off" gets its one exception; cx-client-report's row; the Assistant paragraph; a new Draft email delivery bullet; `drafted.json` and `draft_delivery.py` in the folder map) and `.claude/skills/cx-client-report/SKILL.md` ("never creates email drafts" rewritten: the skill still never does; the popup may, with the setting on). |
| `RULES-FOR-ALAN.md` | The rules changes in plain words, before and after, with why. |
| (`dev/tests/test_draft_route.py`) | The route's tests, now in `dev/tests/`; they apply `live_server.diff` to a throwaway vault copy when the routes are absent. |

## Review fixes (#183 independent review, 20-10-2026)

| Finding | Fix | Proved by |
|---|---|---|
| **M1** (security): the draft run inherited `.claude/settings.json`'s allow rules, including the Microsoft 365 reading tools, so injected text in an email could make it read mail, Teams or SharePoint and put that in a draft | `live_server.diff`: `draft_run_deny` adds `permissions.M365_READ` (the access run keeps only `get_granted_scopes`, because a deny beats an allow and `allowed` is left out); `draft_run` starts in `neutral_cwd()` (an empty folder outside the vault) with `NO_CONTEXT_ARGS` (`--setting-sources ""`, no session saved, `--model sonnet`), `NO_CONTEXT_ENV` and `NARROW_BUILTINS` (`--tools ToolSearch`); MCP is not strict because it needs the connector (probed: with `--setting-sources ""` the Microsoft 365 tools are still listed). The send, update and delete tools stay denied by name. The rules bullet says so | `test_draft_route.py::test_neither_run_can_read_microsoft_365_and_neither_loads_the_vaults_context`: every name in `M365_READ` (`outlook_email_search` first) is denied in both runs but `get_granted_scopes` in the access run; `--setting-sources ""`, `--tools ToolSearch`, a working folder outside the vault |
| **L1**: `email_draft_route` built `body` without `action`, so `request()` and the `copied` command always ran the markup check; "a copy is never refused" was false through the route | `live_server.diff`: `body` carries `action`; `draft_delivery.py copied` forces `action: "copied"` itself | `test_draft_route.py::test_a_copy_is_never_refused_for_markup_but_a_draft_is` (POST copied with `<p><span>x</span></p>` accepted; create refused before any run); `test_draft_delivery.py::CopiedCommand` (the command line) |
| **L2**: `ALLOWED_TAGS` had `s`; Outlook's list names only `strike` | `s` removed from `ALLOWED_TAGS` in `draft_delivery.py` (the builder emits neither) | `test_draft_delivery.py::Markup::test_s_is_not_on_outlooks_list_and_strike_is` |
| `rules-and-skill.diff` did not apply (the client report row, after main's "ask creaite does not write reports" clause) | Rebased onto `origin/main` keeping that clause; the Draft email bullet also names the reading-tool deny and the empty working folder | `patch -p1 --dry-run` and `git apply --check` clean for both diffs |

**Round 2 (Opus delta re-check of 932ef492, 20-10-2026).** L-a: the L1 `body = …` line was 159 characters and put `live_server.py` 25 lines
over the 140-character limit (the limit is 24); it is wrapped. Verified by applying both diffs to a scratch copy of `origin/main`
(dcd8a7b6), in either order, and running `python3 dev/tools/check.py`: `check: OK` (before the wrap: 1 problem). L-b:
`test_draft_delivery.py::test_an_injected_cc_bcc_or_changed_subject_or_to_is_never_reported_as_success` (a Cc, a Bcc, an empty Bcc, a
changed subject or To in the tool call: `check()` refuses, `made` stays true). L-c: `test_draft_route.py` starts the server with the
vault as its working folder (as `launch.py` does) and asserts the run's folder is neither the vault nor under it.
**Follow-up for Jarvis (no code here):** this machine's account also connects Gmail, Google Drive, Google Calendar and Vercel, none in
`permissions.NON_M365_MCP_DENY`. In this route's run they are stopped by headless default-deny and by `check()`; the same gap exists for
the VIP/alert check and the other runs on main, which deny only the servers in that list.

**Apply order (rebuilt on `v261-line2`, 23-10-2026):** `live_server.diff` (guarded; applies to line2 and on top of the whole GUARDED-2.6.1.md chain), then
`rules-and-skill.diff` (the rules file and cx-client-report's SKILL.md, regenerated for line2: the old one did not apply). The rules diff is
`#183` first: `fetch-transcripts/creaite-rules.diff` (#250) applies only after it (both edit the staging row), and if the VIP-follow rules
diff (`origin/v261-vip-rules`) lands first, use `fetch-transcripts/creaite-rules.after-vip.diff` instead. #183 and the VIP diff apply in either
order. Every diff was checked with `git apply --check`, applied, and reversed (`-R --check`, `-R`) on line2 and on line2 with the guarded chain.
`RULES-FOR-ALAN.md` is the plain-words before/after of each rules change. `dev/tests/test_draft_route.py` runs in both states: with the
diff absent it applies it to a throwaway vault copy.

## What the branch already has (unguarded, committed)

- `draft_email.outlook_drafts` (off) in `settings-defaults.json`, the catalogue and Settings › Essentials › **Draft email** (label, help
  text and the **Outlook access** Check row word for word from the brief).
- `system/scripts/draft_delivery.py`: plain code, no Microsoft 365 call, no `subprocess`, no send tool named anywhere (a test walks its
  AST). `request` (payload → the one create-draft call, refused while the setting is off), `prompt`, `check` (the run's stream-json
  events), `record_created`, `record_copied`, `match_sent`, `access`, a JSON-on-stdin command line.
- The popup (drafts.js): Off unchanged; On as the brief's table. It calls `/api/email/draft`; until this diff is applied the old
  server answers 404 and the popup shows the refusal ("Outlook would not create the draft (The live server is older than this dashboard…)")
  with Copy it instead, so nothing breaks while the setting is off (the default).
- `sweep.py stage` reads `sent_items` and calls `draft_delivery.match_sent`; cx-sweep's skill says what to pass (subject, To, time).

## The guard inputs

**The write tool.** `mcp__claude_ai_Microsoft_365__outlook_create_draft` (`draft_delivery.CREATE_TOOL`). Arguments, exactly:
`{"subject": str (1 line, ≤255), "body": str (the preview's HTML, ≤500,000), "bodyType": "html", "to": [address, …] (omitted when
there is no address; ≤50)}`. Never `cc` or `bcc`. It answers the draft's `id` and `webLink`; `check` keeps a link only on
`outlook.office.com`, `outlook.office365.com` or `outlook.live.com`.

**The only caller.** `email_draft_route` → `draft_run(prompt, draft_delivery.allowed_tools())`, a `claude -p --output-format stream-json
--verbose --no-session-persistence` run whose `--allowedTools` is exactly `[outlook_create_draft, ToolSearch]` and whose
`--disallowedTools` is `draft_run_deny(allowed)`: `DENY_TOOLS` + every Microsoft 365 action (`draft_delivery.denied_tools()`,
`outlook_send_draft`, `outlook_send_mail`, `outlook_update_draft`, `outlook_delete_draft` among them) + every Microsoft 365 reading
tool (`permissions.M365_READ`, #183 review M1) + `run_deny_extras()` + `VIP_BUILTIN_DENIES` (every built-in but ToolSearch: no Bash,
Read, Write or Edit), minus the two allowed. It also starts in `neutral_cwd()` with `NO_CONTEXT_ARGS`, `NO_CONTEXT_ENV` and
`--tools ToolSearch`, so it loads no settings file (none of the vault's allow rules), no CLAUDE.md and no session-start rule. No
`--add-dir`, no guard hook: the run can touch nothing in the vault and read nothing in Microsoft 365. **Cap's M1 (22-10-2026), prevention before the call:** the run is started with `--settings` carrying its own PreToolUse hook (`draft_delivery.hook_settings`, matcher `*`, started by the same wrapper as the guard hook): `draft_delivery.py hook <request file>` lets ToolSearch through, refuses every other call (exit 2), and for `outlook_create_draft`, once and only with `tool_input` equal to the request's arguments, prints `hookSpecificOutput {hookEventName: PreToolUse, permissionDecision: allow}`. **Fail closed (Cap's review, 23-10-2026):** the run's `--allowedTools` is `ToolSearch` only; the create tool is not on it, and `draft_run_deny` leaves it off the deny list only when a hook file is given. The hook is the only path that can allow the tool, so with no hook, a hook that never runs, errors, times out or returns no decision, headless default-deny refuses it and nothing is made (tests: `test_with_no_hook_the_create_tool_is_not_allowed_and_nothing_is_made`, `test_a_hook_that_gives_no_decision_makes_nothing`, the argv assertion `--allowedTools == ToolSearch`); the request is written to `system/staging/drafts/draft-hook-*.json` (the wrapper refuses an argument outside the vault) and removed when the run ends. An injected To, Cc, Bcc, a changed subject or body, or a second draft is refused before anything is made; the words say so ("nothing was made"), or, if a draft already exists, to delete it unsent. `check` stays as the backstop: it requires exactly one create-draft call, with arguments equal to the
request, and no other tool but ToolSearch, before anything is recorded. The route is token-checked (`authorised()` in `do_POST`), refuses in
the development repository, holds one run at a time (`DRAFT_RUN_LOCK`) and writes `chases.json` and `drafted.json` only through
`draft_delivery.py created|copied` under `LOCK`.

**permissions.py: keep as it is.** `outlook_create_draft` stays in `M365_ACTIONS`, so `m365_problem` still refuses an allow rule for
it in any settings file and `DENY_TOOLS` still denies it to every other run (ask creaite, the VIP check, Prep, Shape, drafts, the sweep).
The allow lives only in code, in the route's own run. Optional, for the reader: a comment beside `M365_ACTIONS` naming the route as the
one exception.

**reach.py: keep refusing.** `draft_delivery.py` must stay out of `SCRIPT_COMMANDS`, so an ask creaite chat, a held run or a confirmed
request is refused it (fails closed today: unknown script). `system/staging/drafted.json` is already a never-write for ask creaite
(`system/staging/*.json`). The `sweep` mode's `sweep.py stage` now also marks drafted chases sent from the spec's `sent_items`: that
writes only `drafted.json` and `chases.json` through the script, never text; a run that invents a Sent Items row could at worst mark a
chase sent or record one (references only, undoable by hand), which is within what a staging run may already do.

**The doctor check (suggested, `draft_delivery` in doctor.py).** Fail when any of these is false:
1. `draft_delivery.allowed_tools() == [CREATE_TOOL, "ToolSearch"]`;
2. `set(draft_delivery.denied_tools()) == set(permissions.m365_action_tools()) - {CREATE_TOOL}`;
3. `CREATE_TOOL` is still in `permissions.m365_action_tools()` and in `live_server.DENY_TOOLS`;
4. no settings file allows `outlook_create_draft` or the whole Microsoft 365 server (`m365_problem`, as today);
5. `"draft_delivery.py" not in reach.SCRIPT_COMMANDS`;
6. the string `outlook_create_draft` (or `CREATE_TOOL`) appears in `live_server.py` only inside the `#183` block;
7. `draft_email.outlook_drafts` is a boolean (warn otherwise; `draft_delivery.enabled` treats anything but `true` as off).

## Why

Alan, 19-10-2026: some people can write to Outlook and some cannot; the setting switches between a draft in Outlook and copy and paste,
off where they cannot. A draft only: creaite never sends.

## Risk

- **Outlook's HTML allowlist (decided: Alan, 19-10-2026).** The tool's description says an HTML body with anything outside its allowlist
  (headings, paragraphs, links, lists, b/i/strong/em/strike, code, tables, br/hr, div, pre; it names span, font, blockquote, images,
  scripts, event handlers and comments) is **rejected, not stripped**. The builder (drafts.js `draftEmail`) now writes only that subset,
  in the preview, Copy email and the draft alike: a due date's red or amber (and bold when overdue) is on its own `<td>`; a muted line
  (Response, Latest update, Chased, a decision's owner) is `<i style="font-style:normal;color:…">` (`deMuted`); anchors carry `href`
  and `style` only. Never span, font, class, id, data- attributes, comments, style or script blocks, CSS variables or images. The editor's
  email run (core/editor.js `emailSpan`) reads and writes the same `<i>`, so an edited email stays in the subset. `draft_delivery.request`
  refuses a draft body outside it before any run (`markup_problem`: "The email has formatting Outlook won't take (a <span> element):
  copy it instead."); a copy is never refused. Still a live check: whether Outlook keeps the inline `style` attributes and the table's
  `cellpadding`, `cellspacing`, `border` and `align` (the description lists tags only).
- The run is a model call carrying the email; `check` compares the tool call's arguments to the request, so a changed body is never
  reported as success (the popup says to check the Drafts folder, since a draft may exist).
- Graph drafts carry no Outlook signature, and the tool stamps an X-AI-Generated header.
- Refusal reasons are fixed words (permission, formatting, rate limit, not connected, or "n characters held back"); the tool's own
  text is never shown or logged. The debug log gets counts only.

## How to test

1. `git apply dev/proposals/draft-delivery/live_server.diff && git apply dev/proposals/draft-delivery/rules-and-skill.diff`
2. `git mv dev/proposals/draft-delivery/test_draft_route.py dev/tests/` and run `python3 dev/tests/test_draft_route.py` (7 tests:
   a draft made with create-draft only and the chase recorded; a refusal records nothing; off refuses before any run, no token 403;
   a copy keeps references only; the access Check reads the granted scopes only; neither run can read Microsoft 365 or load the
   vault's context; a copy is never refused for markup).
3. Also `python3 dev/tests/test_draft_delivery.py`, `test_draft_delivery_popup.py`, `test_drafts_email.py`, `test_ask_access.py`,
   `test_vip_tools_pinned.py`, `test_permissions_mcp.py`, and `python3 dev/tools/check.py` (verified: `check: OK` with the diff applied in a
   scratch copy).
4. By hand, in a live vault with Microsoft 365 connected: Settings › Essentials › Draft email › Check; turn it on; Draft email for a
   person with an overdue item › Create draft in Outlook; the draft is in Outlook's Drafts folder, unsent; the next sweep marks it sent
   after you send it.
