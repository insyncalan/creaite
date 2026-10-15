# Sprint: Thread cards for people Alan follows (BL-342)

> **Write-up only (15-10-2026).** This step builds nothing. It is the plan for issue #86 (insyncalan/creaite-plan); its Done-when is "written up with a Done-when per part, and the open points decided". The build sprint takes the parts below.
>
> **Privacy (BL-288).** Nobody is called or labelled a VIP in anything shown or shared. Here "followed" means a person in the people register's VIP field; the word stays only in that field, the setting names (`vip.*`) and file names that already exist.
>
> **UX baseline first (BL-157).** Before it is called done, every screen this sprint touches (Today's alert cards, the Review page for the logged update) is checked in the real browser against the ten checks in `dev/BUILD.md` › Sprint ux › UX baseline, at 1400px and 1100px, light and dark, in at least two themes, with ask creaite open and closed. The report lists the checks made, with screenshots.

**Goes into:** v2.1.0. Branch `sprint-vip-thread-cards`, worktree `../creaite-vip-thread-cards`, from the tip of `main` (it has BL-334, v1.9.5), then it joins the v2.1.0 integration. Size L, labels sonnet and review (Jarvis reviews the live_server.py diff before it is pushed).

**Cutting it:** not cut by this sprint; the v2.1.0 release does it.

## Goal

Today shows **one card per mail or Teams thread** from people Alan follows, built around what he must do: a **type** (Action, Decision, FYI/file or Risk), a **due date** and **owners**. The thread is matched to open work first (New, Update or Chase). The card stays until Alan acts: **Handled**, or his reply showing in Sent Items (or his own message in the Teams chat). A card can be **logged on the matched item** in one click, which stages an update for Review. Confidential threads get a real summary in creaite's own words and stay internal. A cheap ID-only check runs on the timer; a thread is summarised only when it has new messages.

## What exists (BL-334, v1.9.5)

Read from `main`, so the plan builds on it rather than repeating it:

- `VIP_PROMPT`, `vip_check` and `vip_timer` in `system/scripts/live_server.py`: one `claude -p` call every `vip.check_minutes` (30), read-only tools (`VIP_TOOLS`: email search, chat message search, calendar search, `read_resource`), reply a JSON array, one object per conversation (`kind`, `conversation`, `title`, `from`, `people`, `last`, `link`, `sensitivity`, `attachments`, `summary` up to 300 characters, `items` of action, decision or risk with owner and due).
- `sweep.py`: `vip_record` → `conv_record` / `conv_key` / `conv_content` / `conv_finish`; the card is an alert in `system/staging/vip.json` keyed by a hash of kind plus conversation ID, updated in place ("updated HH:MM"); wait-for-quiet (`QUIET_WAIT`, 15 minutes); `vip_project` (title, then people, then signals); candidates with `n`, `made` and dismissed state; `summarised()` so the sweep skips a conversation already on a card; `vip_make` stages one proposal (`proposed-…-dashboard.json`, `op: new`); `CONFIDENTIAL_MADE` keeps a made item internal and labelled Sensitive.
- Routes `/api/alerts/dismiss`, `/undo`, `/prefill`, `/draft`, `/make` (live_server.py); the card is in `system/templates/dashboard/src/today.js` (built into `system/templates/dashboard.html`).
- Tests: `test_vip_conversations.py`, `test_alert_actions.py`, `test_sweep_alerts.py`, `test_vip_confidential.py`, `test_vip_private.py`, `test_vip_screens.py`.
- vip.json holds references and Claude's own words, never message text. No schema change.

What BL-334 does not have: a thread-level type, due date or owners; a match to an existing item; a Handled state or closing on Alan's reply; a way to log the thread on an item; any split between "is there anything new" and "summarise it". Every 30 minutes the one call does both.

## Decisions on the three open points

Technical points are Jarvis's call; the product-cost point is Alan's. Each below has a recommendation, so the build can start on the recommendation while the owner confirms.

### a. Thread grouping when mail search results lack conversationId (decides: Jarvis)

**What BL-334 does today.** The prompt tells Claude to find messages by search, then "read each conversation … by its conversation ID" and return it as `conversation`. Claude can only get a mail `conversationId` by `read_resource` on a message; search results do not carry it. `conv_key` hashes `kind` plus the supplied ID and, when none comes back, falls back to the message `link`, then to title plus sorted people. Teams chats have a chat ID, so Teams works. **What works:** Teams (stable chat ID); mail when Claude does the `read_resource` step. **What does not:** when Claude skips that step the key is the link or a title-and-people hash, and a different run can use a different fallback for the same thread, which gives two cards for one thread, and the fallback is never reconciled later.

**Options.**
1. **Read every hit with `read_resource`** to get the ID. Always right, but one read per hit, so it costs most in the check that runs most often.
2. **A stable local key:** normalised subject (strip `Re:`, `Fw:`, `FW:`, tags in brackets, case and spaces) plus the sorted set of participant addresses, hashed. No extra reads. Wrong when two threads share a subject and people (a weekly "Status" mail), or the subject is edited mid-thread.
3. **Both, with aliases (recommended).** Each card stores every key it has been seen under: `conv` (the ID, when known) and `keys` (the local key, and the link). A thread matches a card if **any** key matches. Stage 1 asks `read_resource` only for a hit whose message ID, link or local key is not already on a card, so a known thread costs no read, and a new one costs one. When the ID turns up later it is added to `keys`; two cards that turn out to be one (same ID) are merged, newest summary kept, Handled state kept if either was handled.

**Recommendation: option 3.** Same-subject collisions are handled by requiring the people overlap and a message-ID check in stage 2, and by the merge. **The live fact to confirm first** (the dev repository cannot reach Microsoft 365): a one-off probe by Jarvis or Alan in a live vault that (i) `read_resource` on a mail returns `conversationId`, (ii) a Teams chat search result carries the chat ID, (iii) Sent Items can be searched by subject. If (i) fails, option 2 alone is the fallback and the plan still holds (the merge becomes a no-op).

### b. How a staged update from a card reaches Review (decides: Jarvis)

**Options.**
1. **The card's own staging, like `vip_make` (recommended).** The "Log on <item>" click calls a route that writes `proposed-YYYY-MM-DD-HHMMSS-dashboard.json` with one `op: update` item (the format BL-297 and BL-219 already use: `changes: {"latest_update": …}`, `based_on` the row's `updated_at`, `why`, `source` the thread link, `suggested` marker `{"feature": "thread"}`), `decision: "pending"`. Alan sees it in Review as any proposal; a conflict is detected by `based_on`. If a pending card proposal for that item already exists (several threads for one item), the new line is **added** to that proposal's `latest_update` rather than a second file, so Review shows one update per item. `latest_update` only is routine in bulk approval, so nothing new in `review.individual_only`.
2. **Through `sweep.py stage`** with a sweep spec update (BL-297). Gets the sweep's checks, but sets `source_run: "sweep"`, runs the staging as if a sweep had run, and mixes card clicks with sweep batches in Review's grouping. No gain.
3. **A second queue** (not Review) for logged updates. A new surface, and it breaks "nothing reaches the tracker except through Review".

**Recommendation: option 1.** No change to `tracker.py`, `review.py`, the schema or any guarded file; the click is the ask (BL-334 decision A: nothing goes to Review unless Alan asks). The text is Claude's own summary line plus the date and a source reference, never message text. A confidential thread logs only a neutral line ("Discussed in a confidential thread, DD-MM-YYYY"), because `latest_update` has no Sensitive label of its own; Alan can widen it in Review.

### c. The model for the ID-only check (decides: Alan, a product cost choice)

**Basis.** The check runs every `vip.check_minutes` (30), so 48 times in a 24-hour day, or 24 in a 12-hour working day. Each run is a headless `claude -p` call with the project's `CLAUDE.md` loaded, so most of the cost is fixed overhead, not the search. Prices are from `dev/tools/usage.py` `PRICES` (dollars per million tokens; this file is in BL-343's branch `bl343-usage`, not yet on `main`):

| Model | input | cache write (5 min) | cache read | output |
|-------|-------|--------------------|-----------|--------|
| Opus | 4.00 | 5.00 | 0.20 | 20.00 |
| Sonnet | 2.00 | 2.50 | 0.20 | 10.00 |
| Haiku | 0.10 | 0.125 | 0.01 | 0.50 |

**Assumed size of one ID-only check** (an estimate; step 0 replaces it with a measured figure from `usage.py`): 20,000 tokens of context written to the cache (checks are 30 minutes apart, past the 5-minute cache), 40,000 read back over two further turns, 3,000 fresh input (tool results), 600 output.

| Option | Per check | Per day, 48 checks | Per day, 24 checks | Notes |
|--------|-----------|--------------------|--------------------|-------|
| Opus | $0.132 | **$6.34** | $3.17 | No gain for a list of IDs. |
| Sonnet | $0.070 | **$3.36** | $1.68 | Reliable; about today's cost per call for the search half. |
| Haiku | $0.0035 | **$0.17** | $0.08 | One-twentieth of Sonnet. Needs the step 0 probe to show it fills the ID fields correctly. |
| No model | $0 | **$0** | $0 | **Not possible today.** The only way to Microsoft 365 is the Claude connector, which only a Claude run can call; creaite holds no Microsoft token and must not (local-only rule). Only a longer `vip.check_minutes` removes cost without a model. |

Stage 2 (summarising a thread with new messages) stays on the default model, assumed Sonnet class. Assuming five threads with new messages a day, batched into one call per round at about $0.10 a call, that is about **$0.50 a day**. So the two-stage total is about **$0.67 a day with Haiku** for stage 1 (or $3.86 with Sonnet), against about **$4.80 a day for today's single call** on Sonnet (48 × ~$0.10, since every check also reads and summarises). The saving comes from two-stage, not only the model.

**Recommendation: Haiku for stage 1 (setting `vip.check_model`, default `haiku`, empty means the default model), Sonnet for stage 2.** Fall back to Sonnet for stage 1 on its own if the step 0 probe shows Haiku misreports IDs or dates; the rest of the plan does not change. Alan's levers: the model, and `vip.check_minutes` (halving the frequency halves stage 1).

## Part 1. The card

**Behaviour.**
- **One card per thread** (mail thread or Teams chat). A new message updates the same card ("updated HH:MM"), as BL-334.
- **Type:** the one thing Alan must do: `action`, `decision`, `fyi` (shown "FYI / file", and attachment names listed) or `risk`. One type per card, set by Claude from the whole thread; a nothing-actionable thread stays BL-334's quiet line (type `fyi`, no buttons). BL-334's per-item candidates stay under the card for Create work item.
- **Due date:** where stated or clearly implied (`YYYY-MM-DD`, shown as in Conventions); otherwise none. The code drops anything that is not a real date. Overdue cards sort first, then by due date, then by last message.
- **Owners:** the people named to act, by full name (a register name where known); "you" when the ask is of Alan. Also one line, `ask`: what Alan must do, in creaite's words, up to 140 characters.
- **Handled:** a button on every card, same effect as Dismiss (out of Needs attention, kept in vip.json, Undo available), recorded as `handled` with a time. Dismiss is relabelled Handled on thread cards; the routes and Undo stay; Activity › Quality can tell the two apart.
- **Closing on Alan's reply:** stage 1 also looks, for each open card, for a message from Alan in that thread after the card's `last` (mail: Sent Items; Teams: his own message in the chat). Found: the card closes as `replied` with that time, and shows in a quiet "Replied" line. A later message from someone else reopens it (updated in place). A reply does not mark the matched work item done.
- **Log on the matched item:** on a card with a match (Part 2), one click, "Log on ABC-A-007", stages an update for Review (decision b). The button never appears without a match, and the click is the only way anything is staged.
- **Followed people only for now;** cards stay until Alan acts.

**Files.**
- `system/scripts/sweep.py`: card shape (`type`, `ask`, `due`, `owners`, `keys`, `state` of open, handled or replied, `replied_at`), `conv_content` / `conv_finish`, `vip_handled`, `vip_replied`, `vip_log` (decision b), the merge of two cards with one ID, sort order. No reach.py or schema change: `sweep.py vip` is already classed `DERIVED`.
- `system/scripts/live_server.py`: **routes only** (`/api/alerts/handled`, `/api/alerts/log`, their entries in `SWEEP_ALERT_ROUTES`). **Guarded-area mark: live_server.py (routes, not a run). Jarvis reviews.** Sonnet may write them.
- `system/templates/dashboard/src/today.js` and the built `system/templates/dashboard.html` (type chip, due, owners, ask, Handled, Replied, Log button); `system/scripts/build_dashboard.py` (the card's fields in the page data).
- The prompt fields that supply `type`, `ask`, `due`, `owners` are added in Part 3's Opus step.

**Done when:**
- a stand-in claude returns a three-message chat; the page data has one card with a type, a due date, owners and an ask, and a quiet greeting thread has type `fyi`, no buttons;
- a due date that is not a date is dropped; overdue cards sort first;
- Handled settles the card, stages nothing, and Undo puts it back;
- a reply found in Sent Items closes the card as Replied; a later message from someone else reopens it;
- Log on the matched item stages exactly one `update` proposal, pending, with `based_on`, and the card shows it as logged; clicking again stages nothing new; a second thread for the same item adds a line to the same pending proposal;
- no "VIP" in any card text, route result or page data (BL-288); vip.json holds no message text.

**Tests.** New `dev/tests/test_vip_threads.py` (stand-in claude, as `test_vip_conversations.py`); extend `test_alert_actions.py` (Handled, Undo, Log), `test_vip_screens.py` (card in the real browser, 1400 and 1100px, light and dark), `test_vip_private.py` (no label anywhere, including the new fields and routes). Size **M**. Model: **Sonnet** (the routes are not runs; Jarvis reviews them).

## Part 2. Matching a thread to open work

**Behaviour.** The card says **New**, **Update** or **Chase**, or lists several threads against one item.
- **New:** nothing open matches; BL-334's candidates and Create work item apply unchanged.
- **Update:** the thread moves an open item forward (a date, a decision, a reply). Offers Log on the item (Part 1).
- **Chase:** the item is owed to Alan by someone in the thread, and Alan wrote last with no reply since. Offers Draft email in its Chase mode (BL-224, BL-298's pane) for that item; nothing is sent. Chase is accepted by code only when the item's owner is in the thread and the thread's last message is Alan's; otherwise it is shown as Update.
- **Several threads, one item:** each thread keeps its own card (one card per thread), each showing the same item; the item's chip on Today shows the count; logging each adds a line to one pending proposal (Part 1).

**How it matches (code first, the model suggests).** After stage 1 names the changed threads, plain code picks the project (`vip_project`: title, then people, then signals) and builds a short list of that project's open items for each thread, at most 15, ranked by the Part 2 signals: an ID named in the thread, title-word overlap, same owner as a participant, due soon (reusing `extraction.py`'s repeat matching, as BL-221). That list (ID, title, owner, due) goes into the stage 2 prompt. The model returns `match: {"id", "relation": "update"|"chase"|"new", "why"}`. Code validates it: the ID exists, is open, is in the thread's project, else the match becomes New. No open-item list leaves the laptop beyond that one stage 2 call, which already runs with the vault's own data.

**Files.**
- `system/scripts/sweep.py`: `vip_open_items(project, thread)` (candidate list), `vip_match(alert, found)` (validation, Chase rule), the `match` field on the card; reads the tracker through `tracker.py read`'s existing read path or `paths`' read-only connection, **never writes it**.
- `system/scripts/extraction.py` only if its matcher needs a small public wrapper (plain code; not guarded).
- `system/templates/dashboard/src/today.js` / `dashboard.html`: the New / Update / Chase chip, the item link, the count chip, the Chase button into the existing Draft email.
- The stage 2 prompt gains the item list and the `match` field in Part 3's Opus step.

**Done when:**
- a thread naming `ABC-A-007` in a mail gives Update with that ID; a thread with no similar open item gives New;
- an invented or closed ID, or another project's, becomes New, not an error;
- Chase is shown only when the owner is in the thread and Alan sent last; the same thread with a reply after is Update;
- two threads for one item show two cards and one count, and Log from both leaves one pending proposal with two lines;
- a thread with no project matched gets no list and no match, and says so.

**Tests.** `test_vip_threads.py` (matching and validation, with a fictional register); `test_alert_actions.py` (Chase opens the pane for that item). Size **M**. Model: **Sonnet** for the code; the prompt text is in Part 3.

## Part 3. Two-stage polling

**Behaviour.** The timer's check becomes two calls.
- **Stage 1 (ID-only, cheap model, no summarising):** one read-only call (the same `VIP_TOOLS`) returns, for messages from followed addresses since the last check, one compact object per thread: `kind`, `conversation` (when known), `key` (subject and people), `msg` (newest message ID), `last`, `link`, `subject`, `people`; and, for each open card, whether Alan has a newer message in that thread (`replied: "YYYY-MM-DD HH:MM"` or null). It reads, summarises and returns nothing else; no body text.
- **Code decides what is new:** a thread whose newest message is later than the card's `last` (or that has no card) goes to stage 2; everything else is left alone; replies close cards (Part 1). `read_resource` is asked for only to learn an unknown mail thread's ID (point a).
- **Stage 2 (summarise, default model):** only the changed threads, in **one call, at most five** (the rest next round), each read whole as BL-334 does. The prompt is `VIP_PROMPT` extended with the Part 1 fields, the Part 2 item list and `match`, and the confidential rule (Part 4). Reply and recording are as BL-334's.
- **Nothing new → no stage 2 call.** Wait-for-quiet (15 minutes), the sweep skip, `vip_lock` / `VIP_WRITE`, the development-repository skip and the sweep-running skip are unchanged. A stage 1 failure leaves `last_check` where it was (nothing lost). A stage 2 failure keeps those threads queued for the next round.
- **Setting:** `vip.check_model` (default `haiku`; empty = the default model), passed as `--model` to stage 1 only.

**Files (this part holds all the prompt and run changes, so it goes to Opus).**
- `system/scripts/live_server.py`: **`VIP_PROMPT` split into a stage 1 prompt and a stage 2 prompt, `vip_check` made two calls, `vip_timer` unchanged in timing; `--model`. This is a change to a run in live_server.py: Opus, and Jarvis reviews the diff.** `VIP_TOOLS` and `DENY_TOOLS` must not change (read-only; the test pins them). No change to the guard hook, `reach.py` or `permissions.py`: the check is not an ask creaite run, has its own allow list and no Bash.
- `system/scripts/sweep.py`: `vip_diff(found_ids)` (which threads changed), `vip_record` accepting the stage 1 shape, queue of threads waiting for stage 2.
- `system/templates/settings-defaults.json`, `system/scripts/settings_catalogue.py` (the `vip.check_model` row with its reason), `system/scripts/build_dashboard.py` / `settings.js` only if the row needs a custom control (a plain choice needs none).
- `dev/tests/test_vip_conversations.py` (the prompt is now two; keeps the tool-list pin).

**Done when:**
- with a stand-in claude, a quiet interval makes **one** call (stage 1) and no stage 2; a changed thread makes two; six changed threads make one stage 1 and one stage 2 with five, and the sixth is summarised next round;
- the stage 1 reply holds no message text and the stage 1 call has `--model haiku` (and none when the setting is empty);
- a stage 1 failure changes nothing and shows the existing error line; a stage 2 failure keeps the threads queued;
- both calls use exactly `VIP_TOOLS` and the disallowed list; neither can write;
- the sweep still skips a summarised thread; "updated HH:MM" still works;
- the debug log gets counts only (checks, changed, replied, durations), no text (BL-102).

**Tests.** `test_vip_conversations.py` (updated), `test_vip_threads.py` (stages, queue, failures, model flag), `test_live_server.py` if it pins the old single call. Size **M**. Model: **Opus** (Alan's rule for runs in live_server.py).

## Part 4. Confidential mail

**Behaviour (as BL-334, extended to the new fields).**
- A confidential thread gets a real summary in creaite's own words, with its type, due, owners and ask, shown on the card in Today, marked Confidential. Never quoted.
- It never reaches a client report, a client-safe one-pager or a prep page's client copy: vip.json is not a report source; an item made from the card is internal and labelled Sensitive (`CONFIDENTIAL_MADE`, unchanged); a **logged update** from the card carries only the neutral line (decision b).
- A **private** thread keeps BL-334's neutral line only: no type, due, owners or match.
- The match list in stage 2 sends a confidential thread's content to the model in the same call as any other (a read-only call on the laptop, no new destination); the reply is kept as words only.

**Files.** `system/scripts/sweep.py` (`conv_content` gives confidential threads the new fields, private ones none; `vip_log` writes the neutral line); the stage 2 prompt wording is in Part 3's Opus step; `system/templates/dashboard/src/today.js` / `dashboard.html` (the Confidential marker next to the new chips). No guarded area.

**Done when:**
- a confidential thread card shows a summary, type, due and owners; the client report and client-safe one-pager built from the same database contain nothing from it;
- its Log click stages a neutral line, not the summary; Create work item still makes an internal, Sensitive item;
- a private thread shows only its neutral line;
- nothing in vip.json, the card, the page data or the route results holds message text or the word VIP.

**Tests.** Extend `test_vip_confidential.py` (card fields, neutral log line, client report and one-pager exclude), `test_vip_private.py`. Size **S**. Model: **Sonnet**.

## Guarded areas, in one place

| Area | Touched? | Where |
|------|----------|-------|
| live_server.py runs (the check and its prompts) | **Yes** | Part 3 only. **Opus.** Jarvis reviews. |
| live_server.py routes (not runs) | **Yes** | Part 1 (`/api/alerts/handled`, `/api/alerts/log`). Sonnet; Jarvis reviews. |
| `reach.py`, the guard hook | No | `sweep.py vip` is already `DERIVED`; no new script command. |
| `permissions.py`, `.claude/settings.json` | No | The check keeps its own allow list. |
| `filechange.py` | No | Nothing creates or changes a project file. |
| `tracker.py`, `schema.sql` | No | Staging only, through the existing proposal format. |

If the build finds it needs any "No" row, it stops and goes back to Jarvis.

## Order

0. **Live probe and measurement** (Jarvis or Alan, in a live vault; Sonnet cannot do this): confirm the three facts in point a, run stage 1's prompt by hand on Haiku and Sonnet and read the cost from `usage.py` (needs BL-343 phase A on the branch used). Confirms or replaces the per-day figures.
1. **Part 1 data and card** (Sonnet): shape, Handled, Replied, Log, routes, UI. With a stand-in claude and the existing prompt.
2. **Part 2 matching** (Sonnet): needs Part 1's card shape in sweep.py, so it follows Part 1.
3. **Part 4** (Sonnet): small, rides on Part 1's shape; can run beside Part 2.
4. **Part 3** (Opus): the two prompts and two calls, the setting; last, so the prompts carry every field from Parts 1, 2 and 4. Jarvis reviews it before push.
5. **Integration pass** (Sonnet): the whole run end to end with the stand-in claude, the real-browser screens, the UX baseline, the sample-vault goldens.

Parts 1 and 2 can be split between two Sonnet agents only if they agree the card shape first (both edit sweep.py).

## Estimate

| Part | Size | Model |
|------|------|-------|
| 1 The card | M | Sonnet |
| 2 Matching | M | Sonnet |
| 3 Two-stage polling | M | Opus |
| 4 Confidential mail | S | Sonnet |
| Step 0 probe, integration, UX baseline | S | Jarvis / Sonnet |
| **Total** | **L** | |

## Rules for this sprint

- Nothing in the sample data, tests or docs uses a real name; fictional people only (as `test_vip_conversations.py`).
- The check stays read-only on Microsoft 365; nothing is sent, replied to or changed there. Chase only opens the existing draft pane.
- Nothing reaches the tracker without Alan's approval in Review. The only write the card makes is a pending proposal he clicked for.
- No schema change; a new key in `settings-defaults.json` only (`update.py merge_new` adds it to a live vault).
- No message text is kept: vip.json, the card, the debug log and the staged update hold Claude's own words, references and counts.

## Tests

Run in the review round: `test_vip_threads.py` (new), `test_vip_conversations.py`, `test_alert_actions.py`, `test_sweep_alerts.py`, `test_vip_confidential.py`, `test_vip_private.py`, `test_vip_screens.py`, `test_live_server.py`, `test_settings*`, `test_no_real_names.py`, and `dev/tools/check.py` (no figure may rise; the dashboard source and built `dashboard.html` are committed together).

## Review-round checks

1. The diff to live_server.py is Part 3 and the two routes only; `VIP_TOOLS` and `DENY_TOOLS` are unchanged and a test pins them.
2. No call from either stage can write (allow list, no Bash).
3. One call on a quiet interval; two on a busy one; never more than five threads in stage 2.
4. A thread keeps one card across a reply, a late ID and a restart; two cards for one ID are merged.
5. No "VIP" or message text anywhere shown, stored or logged; `grep -ri vip` on the page data and route results is clean.
6. A staged update has `based_on`, is pending, is one proposal per item, and a confidential one is the neutral line.
7. The Chase rule is code, not the model's say-so; an invalid match falls to New.
8. Handled and Replied are not confused with done: no work item changes status from a card.
9. The UX baseline's ten checks, with screenshots; the card's due date, type and owners read at 1100px in dark.
10. `settings-defaults.json` and the catalogue row agree; an old vault keeps its own `vip` values.
11. `test_no_real_names.py` and `check.py` pass.

## Report

To be written by the build sprint: what was built per part, the step 0 figures (measured cost per check and per day), which UX checks were made, and anything Jarvis changed in review.

## Notes for Part 3 (from review)

- Team Cap's review of `bl342-p1p2` found that `vip.json` is also written by the command line (`sweep.py vip ...`: record, seen, dismiss, undismiss, handled, replied and the like) outside the live server's `VIP_WRITE` lock. This is pre-existing, not introduced by Parts 1, 2 or 4, and the same lost-update risk applies: a CLI write between a route's read and its save is overwritten.
- Part 3's `vip_lock` should cover those CLI paths as well as the routes, so every read-modify-write of `vip.json` (`vip_state` then `vip_save`) holds one lock, not only the ones the server makes. Opus should judge `vip.json`'s writers as a whole, including `vip_save` (which now also recomputes each match's count) and the `sweep.py vip record` path run by the VIP check.

## UX baseline (15-10-2026, Team Stark; desktop and 900px only, Alan's change)

Today's card with the New, Update, Chase, count, Handled, Log, Replied and Confidential marks, looked at in the real dashboard at 1400 and 900px, light and dark, in creaite and Brightwater, with ask creaite open and closed (16 shots in `~/dev.env/team-stark-shots/bl342-ux/`, plus the Logged chip). Measured each time: no horizontal scroll, no card past the window's right edge, contrast of at least 4.5 on every chip and line (lowest 5.24), title `creaite · Today`. Checks: 1, 2, 3, 6 and 8 do not apply (the card has no text box, date field, typed input, empty state or form); 4 passes (Chase opens BL-224's draft in the app, falling back to the update email when the item is not past its date); 5 passes as BL-173 words it (ask creaite opens over the page; at 900px the card's right-hand buttons sit under it until it is closed); 7 passes; 9 passes (no permanent hint; each button has an aria-label); 10 passes (the Today of the card looked at in the real app before and after).

## Part 5 as built (16-10-2026, Team Cap; for the 2.1.0 known-issues list)

Built on `bl342-part5` from `bl342-part3b-v3`, per the plan's Part 5 (on `bl342-part3b-plan2`) and Alan's three answers of 15-10-2026: no switch of its own (the kept suggestion follows Spot items that are probably done; Activity › Quality counts the feature `promise`), Alan's own promises only, a confidential thread's promise staged as "Follow up on a confidential thread". Tests: `dev/tests/test_vip_promises.py`, `MergePinTests` in `test_vip_single_call.py`, `ThreadCardPromise` in `test_vip_screens.py`. The 2.1.0 hand checks (`dev/handchecks/v2.1.0.md`) are on the v2.1.0 branches, not this one: carry these lines into their "Known issues and not built" at integration.

- **Only Alan's newest message is read for a promise.** Code accepts a promise only when its time is the reply's `replied`, or the newest message's when Alan sent it, so a promise in an earlier message of his in the same thread is never offered (counted `not_alan`). By design: code can't check any other time.
- **A replied card's close is still hidden.** A card with a promise or a kept promise now stays a full card on Today when Alan replied last (his promise is usually in that reply). Part 3 B's "Looks done: close" on a card closed as replied is not shown (the card is the quiet Replied line); not changed here.
- **A second staged kept from a merged card** is carried in `kept_more`: Undo on the kept card takes both back, but the card shows only its own.
- **A name the register doesn't know** (as `to`) is kept as written and the staged promise is flagged `unknown-owner` for Review; a first name the register has as an alias ("Sara") becomes the full name.
