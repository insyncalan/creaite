# Sprint: Thread cards for people Alan follows (BL-342)

> **Write-up only (15-10-2026).** This step builds nothing. It is the plan for issue #86 (insyncalan/creaite-plan); its Done-when is "written up with a Done-when per part, and the open points decided". The build sprint takes the parts below.
>
> **Privacy (BL-288).** Nobody is called or labelled a VIP in anything shown or shared. Here "followed" means a person in the people register's VIP field; the word stays only in that field, the setting names (`vip.*`) and file names that already exist.
>
> **UX baseline first (BL-157).** Before it is called done, every screen this sprint touches (Today's alert cards, the Review page for the logged update) is checked in the real browser against the ten checks in `dev/BUILD.md` › Sprint ux › UX baseline, at 1400px and 1100px, light and dark, in at least two themes, with ask creaite open and closed. The report lists the checks made, with screenshots.

**Goes into:** v2.1.0. Branch `sprint-vip-thread-cards`, worktree `../creaite-vip-thread-cards`, from the tip of `main` (it has BL-334, v1.9.5), then it joins the v2.1.0 integration. Size L, labels sonnet and review (Jarvis reviews the live_server.py diff before it is pushed).

**Cutting it:** not cut by this sprint; the v2.1.0 release does it.

## Goal

Today shows **one card per mail or Teams thread** from people Alan follows, built around what he must do: a **type** (Action, Decision, FYI/file or Risk), a **due date** and **owners**. The thread is matched to open work first (New, Update or Chase). The card stays until Alan acts: **Handled**, or his reply showing in Sent Items (or his own message in the Teams chat). A card can be **logged on the matched item** in one click, which stages an update for Review. Confidential threads get a real summary in creaite's own words and stay internal. The timer's one check fills the card fields (Part 3 B); the two-stage split was dropped on cost (15-10-2026).

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

**Recommendation: option 3.** Same-subject collisions are handled by requiring the people overlap and a message-ID check in stage 2, and by the merge. **The live fact to confirm first** (confirmed by the step 0 probe, 15-10-2026: all three hold; the dev repository cannot reach Microsoft 365): a one-off probe by Jarvis or Alan in a live vault that (i) `read_resource` on a mail returns `conversationId`, (ii) a Teams chat search result carries the chat ID, (iii) Sent Items can be searched by subject. If (i) fails, option 2 alone is the fallback and the plan still holds (the merge becomes a no-op).

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

Stage 2 (summarising a thread with new messages) stays on the default model, assumed Sonnet class. Assuming five threads with new messages a day, batched into one call per round at about $0.10 a call, that is about **$0.50 a day**. So the two-stage total is about **$0.67 a day with Haiku** for stage 1 (or **$3.86 with Sonnet**, the decided model), against about **$4.80 a day for today's single call** on Sonnet (48 × ~$0.10, since every check also reads and summarises). With Sonnet for stage 1 the saving is small and depends on the measured per-check figure; Part 3 step 5 gives the formula and the break-even.

**Recommendation (first write-up): Haiku for stage 1, Sonnet for stage 2,** falling back to Sonnet for stage 1 if the step 0 probe showed Haiku misreports IDs or dates. Alan accepted that on 15-10-2026; the probe then triggered the fallback (below).

**Decided (Jarvis and Alan, 15-10-2026, after the probe): stage 1 runs on Sonnet.** The setting is `vip.check_model`, default **`sonnet`**; `haiku` stays selectable; empty means the default model. Stage 2 stays on the default model. Alan's levers: the model, and `vip.check_minutes` (halving the frequency halves stage 1).

**Superseded (15-10-2026, after the empty-window probe):** stage 1 on Sonnet measured $0.30 to $0.35 a check with nothing to find, so the two-stage design does not pay and there is no second call to choose a model for. Part 3 B keeps the single call on the default model and drops `vip.check_model`; the levers left are in Part 3 B, step 6.

### Step 0 result (the live probe, 15-10-2026)

Alan ran `dev/tools/vip_probe.py --since-days 3` in his own vault (4 followed addresses; read-only, prints ids, dates, counts and costs only). Team Cap read the output; Jarvis decided on it (issue #86).

- **The three facts of point a all hold:** `read_resource` on a mail returns its conversation ID (3 of 3); Teams search results carry the chat ID (6 of 6); Sent Items can be searched by subject (1 result). Option 3 stands.
- **Haiku fails the ID test.** Every long mail conversation ID Haiku returned had a one-character slip against Sonnet's (Sonnet's matched what `read_resource` gave); Teams chat IDs (`19:…`) agreed. A mis-copied ID cannot be a key, so cards would split.
- **Haiku's times were exactly 4 hours early** on every thread both models found: UTC given as if local (the laptop is UTC+4). Not a model error as such, but the prompt never said which zone.
- **Haiku reported two last-message dates in the future** (calendar invites read as messages).
- **Cost of the run:** Haiku $0.023 (22 threads), Sonnet **$0.594** (18 threads) for a three-day window. A real check looks back 30 minutes, so its cost is far smaller; Alan reran the probe with a short window: Sonnet $0.3027 and $0.3453 an empty check, which supersedes Part 3 (see Part 3 B, step 5).

**Three rules the stage 1 prompt must carry, from the probe:** (1) every time in **one named time zone**, stated in the prompt, with its offset in each value; (2) **calendar invites are not messages**: leave them out; (3) **copy IDs exactly** as `read_resource` or the search result gave them, never retyped or shortened.

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
- The prompt fields that supply `type`, `ask`, `due`, `owners` are added in Part 3 B's Opus step.

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
- The prompt gains the open-work list and the `match` field in Part 3 B's Opus step (per project, since one call cannot know a thread's project before it finds it).

**Done when:**
- a thread naming `ABC-A-007` in a mail gives Update with that ID; a thread with no similar open item gives New;
- an invented or closed ID, or another project's, becomes New, not an error;
- Chase is shown only when the owner is in the thread and Alan sent last; the same thread with a reply after is Update;
- two threads for one item show two cards and one count, and Log from both leaves one pending proposal with two lines;
- a thread with no project matched gets no list and no match, and says so.

**Tests.** `test_vip_threads.py` (matching and validation, with a fictional register); `test_alert_actions.py` (Chase opens the pane for that item). Size **M**. Model: **Sonnet** for the code; the prompt text is in Part 3.

## Part 3. Two-stage polling (superseded by cost, 15-10-2026)

> **Superseded by Part 3 B (below). Do not build this part.** Alan's empty-window probe runs (`--since-days 0.05`, issue #86, Team Cap 20:03) measured stage 1 on Sonnet at **$0.3027 and $0.3453 a check with nothing to find**, 3.4 to 3.8 times the $0.09 break-even (step 5). About 80% of it is the 1-hour cache write of the run's fixed context (61,407 and 67,464 tokens), which every call pays whatever it is asked. At 48 checks a day stage 1 alone is **$14.53 to $16.57**, against about **$4.80** for today's single call at the plan's estimate. Haiku is no way out: it mis-copied mail IDs by one character (three-day run) and returned internet message IDs instead of conversation IDs (one-day run); Teams chat IDs were right. The text below is kept as the record; Part 3 B reuses its validation rules, its prompt rules and its review checks where they still apply.


> **Planned 15-10-2026 (Team Stark, Opus); built after `bl342-fixes` lands** (Parts 1, 2 and 4 with Team Cap's review fixes), because it changes `sweep.py`'s VIP code and reads the card shape that branch settles. It also needs #91 (`fix-dash-prompt`: `prompt_last`, the prompt after `--`) on its base. Branch `bl342-part3` from the tip of `bl342-fixes` once #91 is merged into it.

**Behaviour.** The timer's check becomes two calls.
- **Stage 1 (IDs only, `vip.check_model`, default Sonnet):** one read-only call (the same `VIP_TOOLS`) lists, for messages sent by followed addresses since the last check, one object per thread: `kind`, `conversation`, `msg` (newest message ID), `from`, `last`, `subject`, `link`; and, for each open card and each thread it lists, the time of Alan's newest message in it (`replied`). It reads nothing else and summarises nothing; no body text.
- **Code decides what is new** (`vip_diff`): a thread whose newest message is later than its card's `last`, or that has no card, joins a **queue** in vip.json; the rest are left alone; replies close cards (Part 1).
- **Stage 2 (summarise, the default model):** the oldest five queued threads that are quiet (wait-for-quiet, 15 minutes), in **one call**, each read whole as BL-334 does, with the Part 1, 2 and 4 fields. Threads beyond five stay queued and a drain round runs a minute later (stage 2 only).
- **Nothing new → no stage 2 call.** The sweep skip, the development-repository skip and the sweep-running skip are unchanged. A stage 1 failure changes nothing (not `last_check`, not the queue). A stage 2 failure keeps its threads queued; a thread stage 2 cannot read twice is dropped (counted, never a card).

### Step 1. Stage 1: the ID-only check

**The prompt** (`STAGE1_PROMPT` in live_server.py; the build may tighten words, never drop a rule):

> creaite follow check, stage 1 (IDs only). Read-only: change nothing, write nothing, send nothing. Search Alan's Microsoft 365 for Outlook Inbox mail and Teams chat and channel messages SENT BY these addresses since {since} ({zone}): {addresses}. **Leave out calendar invites, meeting requests, meeting updates and replies to them (accepted, declined, tentative, cancelled): they are not messages.** For each mail message found, call read_resource on it once to get its conversation ID; read nothing else. Do not summarise and do not quote anything. **Copy every ID exactly as the tool gave it, character for character; never retype, shorten or guess one; give null if you do not have it.** **Give every time in {zone} as YYYY-MM-DDTHH:MM{offset}, never in any other zone.** Then, for each thread you list and each OPEN thread below, find Alan's newest message in it after its time (mail: search Sent Items for its subject; Teams: his own message in that chat) and give its time, or null. Reply with ONLY this JSON: {"threads": [{"kind": "mail"|"teams", "conversation": "…"|null, "msg": "…", "from": "the sender's address", "last": "YYYY-MM-DDTHH:MM{offset}", "subject": "the mail subject or chat topic, or null", "link": "the web link"}], "replied": [{"conversation": "…", "at": "YYYY-MM-DDTHH:MM{offset}"|null}]}. OPEN: {open}. Never use the word VIP. Reply {"threads": [], "replied": []} if there is nothing.

- **The three probe rules** are the bold sentences: one named zone with its offset in every value; calendar invites left out; IDs copied exactly.
- **The zone.** There is no time-zone setting in creaite (settings-defaults.json has none). The zone is the laptop's, read at each check (`sweep.local_zone()`: `datetime.now().astimezone()`, giving the name and the offset, so a clock change is followed); `{zone}` is written as "Alan's local time, UTC+04:00", `{offset}` as `+04:00`. Tests fix it with `CREAITE_TZ_OFFSET` (as `CREAITE_NOW` fixes the clock). *For Jarvis:* confirm the laptop zone rather than a new `identity.time_zone` setting (recommended: no new setting; the times are compared with the laptop's own clock).
- **`{open}`:** the open and replied cards (`state` open or replied, not seen), at most 20, newest first, each `{conversation, kind, subject (mail only), last}` in the same zone. These are references vip.json already holds.
- **Why every new mail gets a `read_resource`:** a search hit carries no conversation ID, and a new message never carries a key a card already has (its message ID and link are new), so point a's "read only when unknown" saves nothing in practice. The window is 30 minutes, so this is usually 0 to 3 reads.

**The reply's validation** (`sweep.vip_stage1_clean(reply, since, zone)`, plain code; every drop is counted by reason for the debug log, never logged with text):
- The reply must be an object with a `threads` list (and optionally `replied`); anything else is a stage 1 failure.
- **Kind:** `mail` or `teams` only. `calendar`, `event`, `meeting` or anything else is dropped (`invite`). Backstop for rule 2: a mail whose subject starts `Accepted:`, `Declined:`, `Tentative:`, `Canceled:`, `Cancelled:`, `Invitation:` or `Updated invitation` is dropped (`invite`).
- **IDs:** a Teams `conversation` must look like a chat ID (`19:` then `[A-Za-z0-9._:@-]`, at most 300); a mail one must be an opaque ID (`[A-Za-z0-9+/=_-]`, 16 to 300 characters). A malformed one becomes null (`bad_id`); the thread is then keyed by its link and local key (point a's fallback), never by the malformed text. `msg` must be ID-shaped, else null.
- **Sender:** `from` must be a followed address (`sweep.vip_addresses()`), else dropped (`not_followed`).
- **Times:** `last` must parse as ISO 8601 **with an offset**; no offset → dropped (`no_zone`), because a bare time is exactly the 4-hour slip. A valid offset other than the named one is converted to local and counted (`other_zone`). After conversion: later than now plus 2 minutes → dropped (`future`); earlier than `since` minus 10 minutes → dropped (`old`, a search hit outside the window). Stored as local `YYYY-MM-DD HH:MM`, as vip.json stores every time.
- **Duplicates:** one object per conversation; when the model gives two, the newest `last` wins.
- **Size:** at most 50 threads (more is a fault: the first 50 by time, counted `over`).
- **`replied`:** kept only for a conversation that is listed in this reply or is an open card's (by any key); the time is validated as above (future dropped).

**Model flag.** Stage 1 gets `--model <vip.check_model>` when the value is set and passes `^(sonnet|haiku|opus|claude-[a-z0-9.-]{3,60})$`; empty or anything else gives no flag (the default model), and a bad value is logged once by name. The value is never put in argv unchecked.

**How `vip_diff` decides** (`sweep.vip_diff(st, threads, replied)`; reads `st`, changes only the `queue` and card states it is given, under the lock, step 4):
- For each clean thread: `keys = conv_keys(t)` (`id:`, `link:`, `loc:`), then the card is found by **any** key with a **read-only** lookup (`card_lookup`, the matching half of `card_find`, without merging; merging stays in record).
- **Changed:** no card; or `t.last` later than the card's `last`; or the card is already queued (its queue entry takes the newer `last`). This includes handled, replied and private cards: stage 2 decides what they become (Part 1's `conv_finish` rules: a replied card reopens, a handled one comes back only with an ask).
- **Unchanged:** `t.last` not later than the card's `last`. Nothing is written for it.
- **Replied:** for an open card with a `replied` time at or after its `last`, `replied_set` (Part 1). Kept on the queue entry too (`replied`), as evidence for Chase (step 2).
- Queue entry: `{key, kind, conversation, msg, from, last, subject, link, replied, since, tries, at}`, keyed by the card's id when there is a card, else `conv_key(t)`. **`vip_state()` must carry `queue`** (today it returns only `last_check`, `alerts` and `held`, so an unknown key would be lost on the next save).
- `last_check` is set to the time **stage 1 started**, not when it ended, so a message sent during the call is caught next time. It advances even while a thread is held or queued, because the queue keeps them (BL-334's "not past a held conversation" rule is replaced by the queue).

**Files.** `system/scripts/live_server.py` (`STAGE1_PROMPT`; guarded, step 7); `system/scripts/sweep.py` (`local_zone`, `vip_stage1_clean`, `card_lookup`, `vip_diff`, `vip_stage1_record`, `queue` in `vip_state`).

**Done when:** a fixture with each probe failure (step 6) is dropped or converted as listed; a quiet window enqueues nothing and writes only `last_check`; a known thread with nothing newer is untouched; a reply in Sent Items closes the card; no field from stage 1 holds message text.

### Step 2. Stage 2: summarise only the changed threads

**The call.** One call, at most **five** threads (`VIP_STAGE2_MAX = 5`), the oldest queued first, skipping a thread still talking (`still_talking`, 15 minutes, as now). No `--model` (the default model). Timeout 300 s, as today.

**The prompt** (`VIP_PROMPT`, kept under that name, extended; the BL-334 wording stays):
- It names the threads by ID instead of searching: "Read each of these conversations by its ID: everyone's messages since its time, not only theirs, plus a few earlier ones for context; its title, its participants and any attachment names. Read nothing else." Each thread is given as `{conversation, kind, since, subject, candidates}`.
- **Part 1 fields:** `type` (`action`|`decision`|`fyi`|`risk`: the one thing Alan must do), `ask` (what he must do, own words, at most 140 characters, or ""), `due` (`YYYY-MM-DD` where stated or clearly implied, else null), `owners` (full names of those named to act; "you" for Alan).
- **Part 2 fields:** `candidates` per thread is `vip_open_items(project, thread)` cut to `{id, t, owner, due}` (at most 15), for the project the card already has, else `vip_project` on the stage 1 subject and sender. The reply's `match` is `{"id": one of that thread's candidate IDs or null, "relation": "update"|"chase"|"new", "why": "own words, at most 140 characters"}`. `last_from` is the **address** of whoever sent the conversation's newest message.
- **Part 4 rule:** a confidential conversation is summarised like any other, in creaite's own words, never quoted, with `sensitivity: "confidential"`; a private one gives only `"summary": "private"` and no items, type, owners or match.
- **The probe rules again:** times in the named zone with the offset; `conversation` copied exactly as given; a conversation that cannot be read is returned as `{"conversation": "…", "unreadable": true}`. Never the word VIP.

**The reply and recording** (`sweep.vip_stage2_record(found, batch, how)`, under the lock):
- Each object must name a requested conversation **exactly** (or any key of the requested card); anything else is dropped (`unasked`). A thread stage 2 leaves out or marks `unreadable` gets `tries + 1`; at 2 it leaves the queue, counted `unreadable`, and no card is ever made for it (this is the defence against an invented stage 1 ID: stage 1 alone never makes a card).
- Times are validated as in step 1; a future `last` is replaced by stage 1's validated `last`.
- Each kept object is merged with its queue entry (stage 1's `msg`, `link` and `subject` fill gaps; stage 1's `replied` is passed on) and recorded through the existing `vip_record` → `conv_record` path, so Part 1's fields, Part 2's `vip_match` and Part 4's `conv_content` apply unchanged. The entry then leaves the queue.
- **Chase evidence from stage 1, not prose** (Team Cap's note on F3): `found["last_from"]` given to `vip_match` is Alan's own address only when stage 1's `replied` time for that thread is later than the others' newest message; otherwise it is stage 2's value, kept only if it is an address among the thread's people. So Chase still needs `_alan_wrote` (F3's address rule) and, in addition, stage 1's evidence.

**Files.** `system/scripts/live_server.py` (`VIP_PROMPT`; guarded); `system/scripts/sweep.py` (`vip_queue_take`, `vip_queue_failed`, `vip_stage2_record`, the batch's candidates).

**Done when:** six changed threads give one stage 1 and one stage 2 with five, and a drain round summarises the sixth about a minute later; a stage 2 failure keeps all five queued with `tries` 1; a thread unreadable twice is dropped without a card; an object for an unrequested or one-character-different conversation is dropped; a confidential thread's card has type, ask, due and owners and the neutral `why`; a private one has none.

### Step 3. The setting `vip.check_model`

- `system/templates/settings-defaults.json`: `"vip": {…, "check_model": "sonnet"}`, and the `_about` line gains "check_model: the model for the quick check that looks for new messages (Sonnet; Haiku is cheaper but mis-copied mail IDs in the 15-10-2026 probe); empty means the default model". `update.py merge_new` adds the key to a live vault and keeps any value Alan set.
- `system/scripts/settings_catalogue.py`: an **Advanced** row, `"vip.check_model": ("People I follow", "Model for the quick check", "Which model looks for new messages between summaries.", "Sonnet: in the probe of 15-10-2026 Haiku mis-copied mail IDs, which would split one thread into two cards; Haiku is cheaper.")`. Not an Essential.
- **Settings UI** (`system/templates/dashboard/src/settings.js`, the People I follow section, `vipSectionHtml`, and the built `dashboard.html`): a select, "Sonnet (recommended)", "Haiku (cheaper, less reliable IDs)", "Default model" (saved as ""). Saved through the existing settings save (backup and log). If `test_settings_catalogue` or the settings coverage check asks for it, the key goes in the section's keys, not `COVERED_KEYS`.
- `live_server.py` `SAFE_SETTINGS` gains `"vip.check_model"` so Copy diagnostics shows it (an allow-list line, not a run).
- **The `--model` flag and the fallback:** step 1's rule: a valid value → `--model <value>` on stage 1 only; empty or invalid → no flag, so `claude` uses its default model; stage 2 never gets the flag.

**Done when:** an old vault's settings gain `check_model: "sonnet"` on update and keep their own `check_minutes`; the catalogue test passes (every default key has a row); the select saves `haiku` and `""`; stage 1's argv has `--model sonnet`, `--model haiku` or none accordingly, and stage 2's never has one.

### Step 4. The run in live_server.py

- **One launch helper**, `vip_call(prompt, model=None)`, used by both stages:
  `cmd = prompt_last([claude_path(), "-p", *(["--model", model] if model else []), "--output-format", "json", "--allowedTools", ",".join(VIP_TOOLS), "--disallowedTools", ",".join(DENY_TOOLS)], prompt)`, then `subprocess.run(cmd, cwd=paths.ROOT, capture_output=True, text=True, timeout=300, env=run_env())`. Returns `(result text, cost, why)`; `cost` is the reply's `total_cost_usd` (else none). One helper keeps `test_prompt_after_dashdash`'s count of `prompt_last(` at three and its "an option follows `-p`" pin true, and keeps the **portability pin**: `claude_path()` (CREAITE_CLAUDE, the run's PATH, `~/.local/bin`), `-p` first, the prompt after `--`, `run_env()` (PATH with this Python first, `CREAITE_PYTHON`, `CREAITE_HEADLESS_RUN`), `cwd` the vault root.
- **`vip_check(how)`**: the same skips in the same order (development repository, off or nobody followed, a sweep running, a check running: `VIP_LOCK`). Then:
  1. Stage 1 when it is due (start-up, or `vip.check_minutes` since `last_check`, or the queue is empty); `started = sweep.now()`. On failure: the existing error line in `VIP_STATUS["last_error"]`, nothing written, return. On success: `with VIP_WRITE: sweep.vip_stage1_record(clean, replied, started)`.
  2. `with VIP_WRITE: batch = sweep.vip_queue_take(VIP_STAGE2_MAX)`. Empty → the note, return (one call made).
  3. Stage 2. On failure: `with VIP_WRITE: sweep.vip_queue_failed(batch)`, error line. On success: `with VIP_WRITE: new = sweep.vip_stage2_record(found, batch, how)`; the note as now (`vip_note`, "n new or updated", "n waiting to go quiet", plus "n queued").
  4. The debug log (BL-102): one `info("vip", …)` line per check with counts, durations and dollars only: threads, changed, replied, dropped by reason, queued, summarised, seconds and cost per stage. Never a subject, address, ID or text.
- **`vip_wait_seconds`** gains the drain: when the queue holds a thread that is not still talking, come back in 60 s (stage 2 only); a held one keeps today's rule.
- **`vip_timer`** is unchanged in shape; the floor on the interval is in `sweep.vip_settings()` (step 5).
- **`VIP_TOOLS` and `DENY_TOOLS` do not change** and both calls pass exactly them; `test_vip_conversations.py` pins the lists and each call's argv.
- **The lock.** `VIP_WRITE` is a `threading.Lock`, so it only orders writers inside the server. Every vip.json read-modify-write must hold **one lock across processes**: a new `sweep.vip_lock()`, an `fcntl.flock` on `system/staging/vip.lock` (as `drafts.py` already does), re-entrant within a thread (a depth counter, so `vip_log` → `vip_update_stage` cannot deadlock), waiting at most 10 s and then raising (the route's existing fault line; the CLI prints it and exits 1; the check logs it and retries next round); where `fcntl` is missing (Windows, best effort) it is a no-op. It is applied as a decorator inside sweep.py to **every function that reads vip.json and saves it**: `vip_record`, `vip_seen`, `vip_dismiss` (and `cand_dismiss` through it), `vip_undismiss`, `vip_handled`, `vip_replied`, `vip_made_refresh`, `vip_make` (with `mark_made`), `vip_log` / `vip_update_stage`, and the new `vip_stage1_record`, `vip_queue_take`, `vip_queue_failed`, `vip_stage2_record`. **Lock order: `LOCK` → `VIP_WRITE` → `vip_lock`, never the reverse**; nothing holding `vip_lock` takes `LOCK` or calls the server, and no lock is held while `claude` runs. `VIP_WRITE` stays (cheap, and the routes already hold it). The fixed temporary name in `vip_save` (`vip.tmp`) is safe once every save is inside the lock.
- **vip.json writers outside `VIP_WRITE` today** (checked on `bl342-fixes`; every server call site already holds `VIP_WRITE`): only the command line, `sweep.py vip record` (→ `vip_record`) and `sweep.py vip seen` (→ `vip_seen`), run by cx-sweep in Alan's Claude Code session, by the session-start check (`--found start-up`), by the panel sweep (BL-309, a child of the live server, `KIND_TOOLS["sweep"]`) and by a confirmed ask creaite chat (`WRITE_TOOLS` allows `sweep.py *`). The CLI has no dismiss, undismiss, handled or replied command (its choices are `addresses`, `record`, `seen`, `list`), so the note in this file's review section names more than exists; those functions are reached only through routes that hold `VIP_WRITE`. The new file lock covers all of them in any process.
- **How `vip_update_stage` (Part 2) fits:** called only through `vip_log`, from `/api/alerts/log`, which holds `LOCK` then `VIP_WRITE`; `vip_log` takes `vip_lock` (re-entrant for `vip_update_stage` inside). It writes a proposal file under `LOCK`, as `vip_make` does. Nothing in Part 3 changes it.
- **The sweep:** `summarised()` treats a queued, not yet summarised thread as not summarised (the sweep summarises it itself); after any `vip_record`, a queue entry whose card's `last` is at or after the entry's `last` is removed (the sweep got there first).

**Done when:** a quiet interval makes **one** call; a changed thread makes two; both calls have exactly `VIP_TOOLS` and `DENY_TOOLS`, `-p` followed by an option, the prompt after `--`, `run_env()`; a `sweep.py vip seen` run while the server records keeps both changes; Log, Handled and Make still work and do not deadlock.

### Step 5. Cost

**The formula.** Per day = (H × 60 / M) × C1 + R × C2, where H is the hours the live server is open, M is `vip.check_minutes`, C1 is stage 1's cost per check, R is the stage 2 calls a day and C2 the cost of one (about $0.10; five threads a day gives R about 5).

| Case | Stage 1 | Stage 2 | Per day, 24 h (48 checks) | Per day, 12 h (24 checks) |
|------|---------|---------|---------------------------|---------------------------|
| Today (one call does both) | | | **$4.80** (48 × ~$0.10) | $2.40 |
| Sonnet stage 1, the plan's estimate C1 = $0.070 | $3.36 | $0.50 | **$3.86** | $2.18 |
| Haiku stage 1 (not chosen) | $0.17 | $0.50 | $0.67 | $0.58 |
| One start-up catch-up after three days away | ~$0.59 once (the probe's Sonnet figure) | | | |

- **Break-even:** two-stage on Sonnet beats today only while C1 < ($4.80 − $0.50) / 48 = **$0.090 a check**. The saving at the estimate is about $0.94 a day (20%); most of it now comes from not summarising quiet intervals, not from the model.
- **Using the measured figure.** (i) Alan's rerun of the probe with a short window gives C1 for a 30-minute-ish window; it goes into this table in place of the estimate. **The probe cannot take `--since-days 0.05` as written:** its argument is `type=int` (`dev/tools/vip_probe.py`, `bl342-probe` 2b666c54), so argparse refuses `0.05`; it needs `type=float` first (a one-line fix on that branch, before Alan reruns). (ii) The built check logs each stage's `total_cost_usd` (step 4), so Settings › Diagnostics and `usage.py` (BL-343) show the real per-check and per-day figure after a day's use; the review round reads one day's log. (iii) **Rule:** C1 at or under $0.07, keep 30 minutes; between $0.07 and $0.09, keep and note it; over $0.09 (dearer than today), put to Alan: `check_minutes` 60 (halves stage 1) or Haiku once IDs are made safe.
- **The guard on `vip.check_minutes`:** `sweep.vip_settings()` reads a value under 10 as 10 and over 240 as 240 (`VIP_MIN_MINUTES`, `VIP_MAX_MINUTES`), and the Settings field takes 10 to 240, so a slip cannot run stage 1 every minute (48 checks at $0.07 is $3.36 a day; 1,440 would be about $100). Tests that need a fast timer set `CREAITE_VIP_MIN_MINUTES` (test only, like `CREAITE_NOW`); *for Jarvis:* confirm that override, or the tests call `vip_check` through a test hook instead. A drain round (step 4) is stage 2 only, so it adds no stage 1 cost.
- A further lever, **not in this plan**: most of C1 is the fixed context of a `claude -p` run in the vault (CLAUDE.md and the rules). Running the check with a smaller context would change the run's settings and permission sources, which is a guarded change of its own; raise it with Jarvis if C1 comes in over the break-even.

### Step 6. Tests

New `dev/tests/test_vip_two_stage.py`, with the repository's stand-in claude (the `FAKE` pattern of `test_vip_conversations.py`, reading the prompt after `--`, telling stage 1 from stage 2 by the prompt's first words, recording each call's argv, replying from a list per stage) and fictional people only. **The probe's failure modes as fixtures, each rejected or dropped:**
- **UTC times:** `last` with no offset (`"2026-10-08 05:16"`) → dropped `no_zone`; `"2026-10-08T05:16Z"` with `+04:00` named → kept as 09:16 local and counted `other_zone`; a fixture that would otherwise make the thread "changed" by four hours does not.
- **Future dates:** `last` 20-10 against a clock of 08-10 → dropped `future`; a future `replied` → ignored; a future stage 2 `last` → stage 1's time kept.
- **Invented IDs:** a mail ID with a space or one character outside the alphabet → null, keyed by link and local key, never the text; a well-formed ID stage 2 marks `unreadable` twice → dropped, no card, counted; a stage 2 object whose conversation differs by one character from the one asked → dropped `unasked`.
- **A calendar invite:** `kind: "calendar"` → dropped; `kind: "mail"` with subject `Accepted: Steering` or `Updated invitation: …` → dropped.
- Also: a sender who is not followed → dropped; two objects for one conversation → one, the newest.
- **The run:** quiet interval one call; changed thread two calls; six changed → five, then a drain round; stage 1 failure → `last_check` and queue unchanged, error line; stage 2 failure → queued, `tries` 1; `--model sonnet`, `--model haiku`, none for `""` and for `"--dangerously-skip-permissions"`; stage 2 never has `--model`; both calls' argv pinned (`claude_path()`, `-p`, option next, `--` then the prompt, `VIP_TOOLS`, `DENY_TOOLS`, `run_env()`'s `CREAITE_HEADLESS_RUN`).
- **Identity:** a merge between stage 1 and stage 2 (two cards found to share an ID) → stage 2 for either conversation updates the survivor, one card; a card handled between the stages stays handled unless the thread asks something; a stage 1 thread known only by its link matches its card; a thread whose card later gets its ID keeps one card.
- **The lock:** a test holds `vip_lock`, starts `sweep.py vip seen --all` in a subprocess, records a stage 2 result, releases: both changes are in vip.json; `vip_log` inside the route does not deadlock; a held lock past 10 s gives the clean error.
- **Privacy:** a fixture `body` field (message text) never reaches vip.json, the queue, the page data or the debug log; the word VIP is in no stored field; the debug log line has numbers only.
- Updated: `test_vip_conversations.py` (two stages, the tool-list pin), `test_prompt_after_dashdash.py` (still three `prompt_last(`), `test_live_server.py` if it pins the single call, `test_settings_catalogue.py` and the settings tests (`vip.check_model`), `test_vip_threads.py` (stage 1's `replied` and `last_from` evidence), `test_vip_probe.py` (its tool list still equals `VIP_TOOLS`).

### Step 7. Guarded areas, precisely

**live_server.py hunks that are a run (Opus; Jarvis reviews the diff before push):**
1. The VIP block's constants: `STAGE1_PROMPT` (new), `VIP_PROMPT` (extended), `VIP_STAGE2_MAX`, the model check pattern. Jarvis reads both prompts word for word: read-only, the three probe rules, the Part 4 rule, never the word VIP, no instruction to write, send or run anything.
2. `vip_call` (new): the only launch; the argv, `run_env()`, `cwd`, the timeout, `prompt_last`, `--model` only from the checked setting.
3. `vip_check`: the two stages, what each failure leaves, the lock order, the log line.
4. `vip_wait_seconds`: the drain round.

**live_server.py hunks that are not a run** (Sonnet could write them; they ride in the same diff): `SAFE_SETTINGS` gains `vip.check_model`; the module docstring's VIP line. **Unchanged, and the review checks they are:** `VIP_TOOLS`, `DENY_TOOLS`, `VIP_LOCK`, `VIP_WRITE`, `LOCK`, `claude_path`, `run_env`, `prompt_last`, `vip_timer`, every route.

**Not touched (confirmed):** `reach.py` (`sweep.py vip` stays `DERIVED`; no new script command: the queue functions are library calls from the server), the guard hook, `permissions.py`, `.claude/settings.json`, `filechange.py`, `tracker.py`, `schema.sql`, `review.py`. If the build finds it needs any of them, it stops and goes back to Jarvis. `system/creaite-rules.md`'s VIP check line is updated in the dev repository to say "two calls" (an engine file an update ships; not a guarded area).

### Step 8. Build order and estimate

1. **`vip_lock` and `queue` in `vip_state`** (sweep.py, with the lock test): independent of the prompts, and closes the pre-existing lost-update risk, so it goes first.
2. **Stage 1 validation and `vip_diff`** (sweep.py, unit tests with the fixtures).
3. **The setting** (defaults, catalogue, Settings UI, `SAFE_SETTINGS`).
4. **The run** (live_server.py guarded hunks 1 to 4).
5. **Stage 2 recording** (sweep.py) and the end-to-end tests with the stand-in claude.
6. **Cost logging,** the rules line, `check.py`, then Jarvis's review.

**Estimate:** M, about a day of Opus build plus one review round. Model: **Opus** for the whole part (Alan's rule for runs in live_server.py).

**Review-round checks for Part 3:**
- **Identity and keying:** a stage 1 thread matches a card by **any** of its keys (`id:`, `link:`, `loc:`, the card id); `vip_diff` never merges (it uses `card_lookup`); merging happens only in record, under the lock.
- **A thread whose card was merged meanwhile:** stage 2's object is recorded through `card_find`, which finds the survivor through the union of keys; a request keyed by the dropped card's id still lands (the survivor keeps the dropped id in `ids`, and `card_find` must match on it: the review checks this case, and the build adds `ids` to the lookup if it is missing).
- **Two conversation IDs for one link** stay two cards (`same_thread`, Alan's Part 1 decision); stage 2 cannot rename a thread's ID.
- No card is ever made from stage 1 alone; a thread stage 2 cannot read is dropped after two tries.
- A stage 1 failure leaves vip.json byte for byte as it was; a stage 2 failure changes only `tries`.
- The lock order holds everywhere (`LOCK` → `VIP_WRITE` → `vip_lock`); no lock is held while `claude` runs.
- The debug log and vip.json hold no message text, subject, address in a log line, or the word VIP.

**Done when (Part 3 as a whole):**
- with a stand-in claude, a quiet interval makes **one** call (stage 1) and no stage 2; a changed thread makes two; six changed threads make one stage 1 and one stage 2 with five, and the sixth is summarised in the drain round;
- every probe failure fixture is dropped or converted (step 6);
- the stage 1 reply holds no message text, and the stage 1 call has `--model sonnet` by default (`haiku` when chosen, none when the setting is empty);
- a stage 1 failure changes nothing and shows the existing error line; a stage 2 failure keeps the threads queued;
- both calls use exactly `VIP_TOOLS` and `DENY_TOOLS`; neither can write;
- every vip.json read-modify-write, in the server or the command line, holds `vip_lock`;
- the sweep still skips a summarised thread; "updated HH:MM" still works;
- the debug log gets counts, durations and costs only (BL-102);
- `test_no_real_names.py` and `check.py` pass.

**Tests.** `test_vip_two_stage.py` (new), `test_vip_conversations.py` (updated), `test_vip_threads.py`, `test_prompt_after_dashdash.py`, `test_live_server.py`, `test_settings_catalogue.py`, `test_vip_probe.py`. Size **M**. Model: **Opus**.

## Part 3 B. One call, with the card fields (replaces Part 3)

> **Planned 15-10-2026 (Team Stark, Opus); plan only, nothing built.** Built after `bl342-fixes` lands (Parts 1, 2 and 4 with Team Cap's review fixes, N1 and N2 included), on a base that also has `prompt_last` (#91; on `main`, not yet on `bl342-fixes`). Branch `bl342-part3b` from that tip.

**Behaviour.** The timer's check stays **one `claude -p` call** (`vip_check` in live_server.py, as on `main`), on the default model. What changes is what the call is asked and what code accepts from it:
- The reply carries the Part 1 fields (`type`, `ask`, `due`, `owners`), the Part 2 `match` and `last_from`, and Alan's newest reply in each thread (`replied`), so the cards Parts 1, 2 and 4 built are filled by the real check, not only by the stand-in claude.
- **Calendar invites are left out** (Alan's yes, 15-10-2026, a BL-99 change). Invites from followed people no longer make cards.
- Times come back in one named zone; IDs are copied exactly; code checks every field before `vip_record` sees it.
- Nothing else changes: the same tools, the same skips, the same timer, the same `vip_record` → `conv_record` path, no queue, no second call, no new setting.

### Step 1. The prompt

**`VIP_PROMPT` (live_server.py), extended; the BL-334 wording stays where it is not replaced.** New and changed sentences (the build may tighten words, never drop a rule):

1. **Sources.** "Search … for messages SENT BY these addresses since {since} ({zone}): Outlook Inbox mail and Teams chats and channel messages. **Leave out calendar invites, meeting requests, meeting updates and replies to them (accepted, declined, tentative, cancelled): they are not messages.**" `kind` becomes `"teams"|"mail"` only. Built behind a module constant, `VIP_INVITES = False`: when `True`, the BL-334 sentence ("and calendar invites or updates", `kind` `"calendar"`) is used instead and the code drop in step 2 is off. A constant, not a setting, so flipping it is a one-line reviewed change (Alan's decision, not a dial).
2. **Time zone (probe rule 1).** "Give every time in {zone} as YYYY-MM-DDTHH:MM{offset}, never in any other zone." `{zone}` is the laptop's own, read at each check: `sweep.local_zone()` (`datetime.now().astimezone()`: name and offset, so a clock change is followed), written "Alan's local time, UTC+04:00"; `{offset}` is `+04:00`. Tests fix it with `CREAITE_TZ_OFFSET`, as `CREAITE_NOW` fixes the clock. No `identity.time_zone` setting: every time is compared with the laptop's own clock.
3. **IDs (probe rule 3).** "For each mail message found, call read_resource on it once to get its **conversation ID**. **Copy every ID exactly as the tool gave it, character for character; never retype, shorten or guess one; give null if you do not have it. For mail, `conversation` is the conversation ID from read_resource, never the message's internet message ID (the one that looks like `<…@…>`).**" The Haiku runs gave both failure kinds (a one-character slip, and internet message IDs); Sonnet, the default model, gave neither, and code still checks (step 2).
4. **Part 1 fields.** `"type": "action"|"decision"|"fyi"|"risk"` (the one thing Alan must do), `"ask"` (what he must do, own words, at most 140 characters, or ""), `"due"` (`YYYY-MM-DD` where stated or clearly implied, else null), `"owners"` (full names of those named to act; "you" when the ask is of Alan).
5. **Part 2 fields.** `"last_from"`: the address of whoever sent the conversation's newest message (anyone's, Alan's included). `"match": {"id": one ID from OPEN WORK for this conversation's project, or null, "relation": "update"|"chase"|"new", "why": "own words, at most 140 characters"}`. **OPEN WORK** is given in the prompt as `{open_work}` (below).
6. **Replies (Part 1, closing on Alan's reply).** "For each conversation you report and each OPEN conversation below, find Alan's newest message in it after its time (mail: search Sent Items for its subject; Teams: his own message in that chat) and give it as `"replied": "YYYY-MM-DDTHH:MM{offset}"` or null. For an OPEN conversation with nothing new from anyone else, give only `{"conversation", "kind", "replied"}`." **OPEN** is `{open}` (below).
7. **Part 4 rule** (BL-334's, extended): a confidential conversation is summarised like any other in creaite's own words, never quoted, `sensitivity: "confidential"`, **with its type, ask, due, owners and match**; a private one gives only `"summary": "private"` and no items, type, ask, due, owners or match.
8. Unchanged: read-only, change nothing, write nothing, send nothing; one object per conversation; never the word VIP; `[]` when there is nothing.

**What code puts in the prompt** (`sweep.vip_prompt_parts()`, plain code, returns the strings; the server only formats them):
- `{open}`: the open and replied cards (`state` open or replied, not seen), at most 20, newest first, each `{conversation, kind, subject (mail only), last}` in the named zone. References vip.json already holds.
- `{open_work}`: for each active project, its open actions from `vip_open_items`' source (`_open_actions`), cut to `{id, t (at most 80 characters), owner, due}`, overdue first then by due date, **at most 15 a project, 60 in all**. A single call cannot know a new thread's project before it finds the thread, so the list is per project, not per thread; code still decides the project (`vip_project`) and keeps a match only when the ID is an open action of that card's project (`_checked_match`, unchanged). The titles are the vault's own data, sent to the same read-only call that already reads the mail; nothing new leaves the laptop beyond that call. *For Jarvis:* items labelled Sensitive stay in the list (the call is internal; nothing from it is client-facing); say if they should be left out.

### Step 2. The reply's validation (code)

`sweep.vip_clean(found, since, zone, open_cards, invites=False)`, plain code, run before `vip_record`; each drop is counted by reason for the debug log, never logged with text. What still applies from the two-stage plan:
- **Shape.** A JSON array of objects; anything else is the existing "didn't finish" failure. At most 50 objects (more is a fault: the first 50 by time, counted `over`); one object per conversation (two → the newest `last`).
- **Kind and invites.** `mail` or `teams` only; `calendar`, `event`, `meeting` or anything else → dropped (`invite`). Backstop: a mail whose subject or title starts `Accepted:`, `Declined:`, `Tentative:`, `Canceled:`, `Cancelled:`, `Invitation:` or `Updated invitation` → dropped (`invite`). With `VIP_INVITES = True` both drops are off.
- **Well-formed IDs.** Teams: `19:` then `[A-Za-z0-9._:@-]`, at most 300. Mail: an opaque ID, `[A-Za-z0-9+/=_-]`, 16 to 300 characters; **anything with `@`, `<` or `>` is an internet message ID and is not a conversation ID** (`bad_id`). A malformed ID becomes null and the thread is keyed by its link and local key (decision a's fallback), never by the malformed text.
- **Times.** `last` and `replied` must parse as ISO 8601 **with an offset**; no offset → dropped (`no_zone`), because a bare time is exactly the 4-hour slip of the three-day probe. Another valid offset → converted to local and counted (`other_zone`). After conversion: later than now plus 2 minutes → dropped (`future`; a future `replied` is ignored, not the thread); `last` earlier than `since` minus 10 minutes → kept only if it is an OPEN card's conversation (a reply-only object), else dropped (`old`). Stored as local `YYYY-MM-DD HH:MM`, as vip.json stores every time.
- **Fields.** `type` outside the four → `fyi`; `ask` and `why` cut to 140 characters; `due` that is not a real date → null (Part 1's rule, unchanged); `owners` a list of strings, at most 6.
- **A reply for a thread that wasn't asked is dropped.** An object is kept only if its `from` is a followed address (`sweep.vip_addresses()`, a new thread found by search) **or** its conversation matches an OPEN card by any key (`card_lookup`: `id:`, `link:`, `loc:`, the card id and its `ids`). Anything else → dropped (`unasked`). A `replied` time is used only for such a kept object. A reply-only object (no `summary`) never makes a card: it can only close or leave an existing one.
- **Chase evidence** (Team Cap's F3 note): `last_from` is kept only if it is an address among the thread's people or Alan's own; `_alan_wrote` (F3's address rule) still decides, and a `replied` later than the thread's other newest message counts as "Alan wrote last".

### Step 3. The lock

**No: Part 3 B does not need the new cross-process `sweep.vip_lock`.** The two-stage plan needed it because it added a queue in vip.json written in three places per check (stage 1 record, take, stage 2 record) on top of the existing writers. Part 3 B adds no new writer and no new state: one `vip_record` per check, under `VIP_WRITE`, as today. The writers outside `VIP_WRITE` (Team Cap's review note) are the command line's `sweep.py vip record` (cx-sweep, the session-start check, the panel sweep, a confirmed ask creaite chat) and `sweep.py vip seen`; the race with them is pre-existing, and its window is the milliseconds of a save, not the minutes of the call.
- **One cheap step inside the guarded `vip_check`:** after the call returns, check `sweep_running()` again; if a sweep began during the call, drop the check's result and leave `last_check` alone (the sweep records the same people itself). That closes the likeliest overlap (the panel or session sweep starting mid-check) without a new lock.
- **The file lock stays a recommendation, as its own small item** (sweep.py only, not guarded, S, Sonnet): an `fcntl.flock` on `system/staging/vip.lock` around every vip.json read-modify-write, as the superseded step 4 specified. It hardens `vip seen` against a dashboard Seen or Handled at the same moment. Not a blocker for Part 3 B; raise as a backlog item if Jarvis agrees.

### Step 4. The run, guarded hunks and review

**live_server.py hunks that are a run (Opus; Jarvis reviews the diff word for word before push):**
1. The VIP constants: `VIP_PROMPT` (extended), `VIP_INVITES` (new, `False`), and the two-variant source sentence. Jarvis reads the prompt: read-only, the three probe rules, invites out, the Part 1, 2 and 4 fields, never the word VIP, no instruction to write, send or run anything.
2. `vip_check`: `prompt_last` (the prompt after `--`), the prompt filled from `sweep.vip_prompt_parts()` and `sweep.local_zone()`; `sweep.vip_clean` before `vip_record`; the second `sweep_running()` check (step 3); one debug log line per check (BL-102), `info("vip", …)` with counts, seconds and dollars only: conversations returned, kept, dropped by reason, new or updated, replied, and the reply's `total_cost_usd`. Never a subject, address, ID or text. That cost line is what measures today's real per-check figure (step 5).

**Not a run, same diff:** the module docstring's VIP line ("invites" removed).

**Unchanged, and the review checks they are:** `VIP_TOOLS` (calendar search stays in it, so flipping `VIP_INVITES` needs no tool change; *for Jarvis:* removing it would be tighter but breaks the flip), `DENY_TOOLS`, `VIP_LOCK`, `VIP_WRITE`, `LOCK`, `claude_path`, `run_env`, `prompt_last`, `vip_timer`, `vip_wait_seconds`, every route, `SAFE_SETTINGS`. **No `--model` flag and no `vip.check_model` setting:** there is no second call, so there is no model to choose for it; the single call reads and summarises, which needs the default model, and the probe showed the cheap model fails mail IDs. One call on one model also keeps `test_prompt_after_dashdash`'s count of `prompt_last(` at three.

**Not touched (confirmed):** `reach.py` (`sweep.py vip` stays `DERIVED`; the new sweep.py functions are library calls from the server, no new script command), the guard hook, `permissions.py`, `.claude/settings.json`, `filechange.py`, `tracker.py`, `schema.sql`, `review.py`, `settings-defaults.json`, `settings_catalogue.py`. If the build finds it needs any of them, it stops and goes back to Jarvis. `system/creaite-rules.md`'s VIP check line loses "invites" (dev repository; an engine file, not a guarded area).

**Model for the build: Opus** for the live_server.py hunks (Alan's rule for runs); the sweep.py code (`local_zone`, `vip_prompt_parts`, `vip_clean`, `card_lookup`) is plain code and may be Sonnet, but one Opus agent doing the whole part is simpler and it is small.

### Step 5. Cost per day

**The formula.** Per day = (H × 60 / M) × C, where H is the hours the live server is open, M is `vip.check_minutes` and C is one check's cost. One call, so no stage 2 term. C is the call's `total_cost_usd`; from the probe's token counts, C = (cache write × $4.00 + cache read × $0.20 + input × $2.00 + output × $10.00) / 1,000,000 on Sonnet (`usage.py` `PRICES`; the probe's writes are 1-hour cache writes at 2 × input, which is what makes the figures add up exactly: 61,407 × 4.00 + 155,768 × 0.20 + 2,590 × 10.00 + 8 × 2.00 = $0.3027).

| Case | C per check | 24 checks (12 h at 30 min) | 48 checks (24 h, the plan's basis) |
|------|-------------|----------------------------|------------------------------------|
| Today, the plan's estimate (~$0.10 a check) | $0.10 | $2.40 | **$4.80** |
| Part 3 B (today plus ~$0.01, below) | $0.11 | $2.64 | **$5.28** |
| Two-stage on Sonnet, measured empty stage 1 | $0.30 to $0.35 (measured) | $7.26 to $8.29, plus stage 2 | **$14.53 to $16.57**, plus stage 2 (≥ $0.50) |

- **Two-stage arithmetic.** 48 × $0.3027 = $14.53; 48 × $0.3453 = $16.57; that is about $14 to $17 a day before any stage 2 call, against the break-even of $0.09 a check (48 × $0.09 + $0.50 = $4.82). Measured C1 is 3.4 to 3.8 times the threshold, so the split costs about three times today.
- **Part 3 B's added text.** The new prompt sentences are about 450 words (≈ 600 tokens); `{open}` at most 20 × ~40 = 800 tokens; `{open_work}` at most 60 × ~30 = 1,800 tokens; about **3,200 tokens** more input at most (less on a normal day: 3 to 4 projects, few open cards). The prompt is written to the cache once (3,200 × $4.00 = $0.013) and read back on each later turn (3 turns × 3,200 × $0.20 = $0.002); the output grows by the new fields, about 80 tokens a conversation ($0.0008 each). So about **+$0.01 a check** at the cap, +$0.48 a day on 48 checks (+$0.24 on 24). The cache write of the run's fixed context (61,000 to 67,000 tokens, about 80% of an empty check's cost) dominates; the added text is about 5% of it.
- **The figure that needs measuring: today's own C.** The empty Sonnet stage 1 ($0.30 to $0.35) carried the same fixed context as today's call (the vault's `CLAUDE.md`, the rules, the tool definitions), and today's call does more (it reads and summarises). So today's real C is very likely **at least $0.30**, not $0.10, which would put today at about **$7.20 a day (12 h) or $14.40 (24 h)**, and Part 3 B at about $0.31 a check. That does not change the decision (two-stage costs at least today's fixed context twice on a busy round, so it never pays while the fixed context dominates); it changes the size of the levers below. The step 4 cost line gives the real figure after one day's use; read it in the review round.
- **Where the money goes.** Laptop 2's day on 15-10-2026 was **$406** (the BL-343 baseline). The check at the plan's $4.80 is **1.2%** of it; at the likely real figure ($7.20 to $14.40) it is **1.8% to 3.5%**. Either way the VIP check is not where the money goes: the build agents are.
- **The guard on `vip.check_minutes`** (unchanged from the superseded plan, still worth having): today the Settings field takes **5 or more** (Essentials.jsx), and the server has no floor of its own (the timer sleeps at least 1 second), so a value of 1 in settings.json would run 720 checks in 12 hours (about $72 at $0.10, $216 at $0.30). `sweep.vip_settings()` reads a value under 10 as 10 and over 240 as 240 (`VIP_MIN_MINUTES`, `VIP_MAX_MINUTES`), and the field takes 10 to 240. sweep.py and the settings source only; not guarded; Sonnet.

### Step 6. The cheaper levers, for Alan's choice

Per day at 12 hours, with today's C as the plan's $0.10 and, in brackets, the likely real $0.30.

| Lever | Per day (12 h) | Trade-off |
|-------|----------------|-----------|
| **(a) `check_minutes` 60** | $1.32 ($3.72) | Half the cost; a card can be up to an hour late. The start-up check still catches up at once. |
| **(a) `check_minutes` 120** | $0.66 ($1.86) | A quarter; up to two hours late, which defeats "first thing at the top of Today" for people Alan follows. Bounds proposed: 10 to 240 (step 5). |
| **(b) The check with less context** | Estimate $0.03 to $0.08 a check, so $0.72 to $1.92 (to measure) | A guarded change of its own in `vip_check`'s launch (Opus; Jarvis reviews): run the call from a neutral working folder (for example `system/staging/vip-run/`, empty, outside git) so it loads no `CLAUDE.md`, no rules and no git status, with `--allowedTools` and `--disallowedTools` passed exactly as now. Two gains: a far smaller fixed context, and a stable prefix, so the 1-hour cache written by one check is **read** by the next one 30 minutes later (cache read is one twentieth of a 1-hour write). Risks to check first, with the probe, not in the build: the Microsoft 365 connector must still load (it is a claude.ai connector, so `--strict-mcp-config` with a local MCP file may drop it: do not use that flag without a probe run); the project `.claude/settings.json` deny rules would no longer apply, so `DENY_TOOLS` alone must cover them (it does today for this call; the review checks it); `--bare` or a slimmer system prompt only if `claude --help` on the installed version offers it. Needs Alan's yes, then a probe run with a `--cwd` variant to measure it. |
| **(c) Haiku for Teams, Sonnet for mail** | Not possible in one call | One `claude -p` call runs on one model. Splitting by source means two calls, each paying the fixed context (about $0.30 on Sonnet, $0.01 on Haiku), which is the two-stage cost again: about $7.50 a day at 12 h. Not recommended. |
| **(d) Do nothing** | $2.40 at the estimate, $2.64 with Part 3 B ($7.20 to $7.44) | About 0.6% to 1.8% of laptop 2's day ($406). The simplest; the card fields arrive with it. |

**Recommendation:** build Part 3 B (it is what fills the cards), keep 30 minutes, add the 10 to 240 guard, and let the step 4 cost line measure today's real C for a day. If C is $0.30 or more, take lever (b) as a probe first, then a guarded change; (a) at 60 minutes is the fallback that needs no code.

### Step 7. Tests

New `dev/tests/test_vip_single_call.py`, with the repository's stand-in claude (the `FAKE` pattern of `test_vip_conversations.py`, reading the prompt after `--`), fictional people only:
- **Prompt:** holds the zone sentence with the fixed offset, the invite exclusion, the exact-ID and no-internet-message-ID rules, the Part 1, 2 and 4 fields, `{open}` and `{open_work}` filled (60 rows at most, 15 a project), never "VIP"; with `VIP_INVITES = True` the BL-334 sentence instead.
- **Probe failures as fixtures:** no offset → dropped `no_zone`; `Z` with `+04:00` named → converted, `other_zone`; `last` in the future → dropped; a future `replied` → ignored; a mail `conversation` of `<abc@example.outlook.com>` form → null, keyed by link and local key; one character outside the alphabet → null; `kind: "calendar"` and a mail `Accepted: Steering` → dropped (and kept with `VIP_INVITES = True`).
- **Unasked:** a sender who is not followed and no OPEN match → dropped; a reply-only object for an OPEN card closes it as Replied; a reply-only object for an unknown conversation → dropped, no card.
- **Run:** one call per check; argv pinned (`claude_path()`, `-p` then an option, `--` then the prompt, `VIP_TOOLS`, `DENY_TOOLS`, no `--model`, `run_env()`'s `CREAITE_HEADLESS_RUN`); a sweep starting during the call → nothing recorded, `last_check` unchanged; the debug log line has numbers only, including the cost.
- **Identity:** a reply ID matches a card by any of its keys (`id:`, `link:`, `loc:`, the card id, a merged card's `ids`); a thread whose card was merged by a sweep between the call and the record lands on the survivor, one card.
- Updated: `test_vip_conversations.py` (the prompt pin, kinds without `calendar`), `test_vip_threads.py` (the real fields from the call, `last_from`, `replied`), `test_vip_confidential.py` and `test_vip_private.py` (confidential with fields; private none; no label), `test_prompt_after_dashdash.py` (still three), `test_vip_probe.py` (its tool list still equals `VIP_TOOLS`), `test_settings*` (the 10 to 240 guard).

### Step 8. Build order, size and review-round checks

1. `sweep.local_zone`, `vip_prompt_parts`, `card_lookup`, `vip_clean` (sweep.py) with the fixture tests.
2. The guarded hunks in live_server.py (`VIP_PROMPT`, `VIP_INVITES`, `vip_check`), then the end-to-end tests with the stand-in claude.
3. The `check_minutes` guard (sweep.py and the Settings field), the rules line, `check.py`, then Jarvis's review.

**Size S to M:** about half a day of Opus build plus one review round. Model: **Opus**.

**Review-round checks:**
- **Identity and keying:** a reply object matches a card by **any** of its keys (`id:`, `link:`, `loc:`, the card id, `ids`); `vip_clean` never merges (`card_lookup` is the read-only half of `card_find`); merging happens only in `vip_record`, under `VIP_WRITE`.
- **A merge between the call and the recording:** the only other merger is a command-line `vip record` (a sweep), and the second `sweep_running()` check drops the result when a sweep ran meanwhile; if one slips through, `card_find` at record time re-reads vip.json and finds the survivor through its `ids` (the review checks `card_find` matches on `ids`, and the build adds it if missing).
- Two conversation IDs for one link stay two cards (`same_thread`, Part 1's rule); a reply cannot rename a thread's ID.
- An internet message ID never becomes a key; a reply-only object never makes a card.
- No invite card while `VIP_INVITES` is `False`; flipping it restores BL-334's behaviour and the tests show both.
- The debug log and vip.json hold no message text, no subject or address in a log line, and not the word VIP.
- The diff to live_server.py is the two run hunks and the docstring line only.

**Done when (Part 3 B as a whole):**
- with a stand-in claude, one check makes **one** call with exactly `VIP_TOOLS` and `DENY_TOOLS`, no `--model`, the prompt after `--`;
- the prompt names the laptop's zone with its offset, leaves invites out and asks for the Part 1, 2 and 4 fields with `{open}` and `{open_work}`;
- every probe failure fixture is dropped or converted as in step 2; an unasked thread is dropped;
- a reply in Sent Items closes the card as Replied; a confidential card has type, ask, due, owners and the neutral match reason; a private one has none;
- the debug log gets counts, seconds and the dollar cost per check (BL-102);
- `check_minutes` under 10 is read as 10;
- `test_no_real_names.py` and `check.py` pass.

## Part 4. Confidential mail

**Behaviour (as BL-334, extended to the new fields).**
- A confidential thread gets a real summary in creaite's own words, with its type, due, owners and ask, shown on the card in Today, marked Confidential. Never quoted.
- It never reaches a client report, a client-safe one-pager or a prep page's client copy: vip.json is not a report source; an item made from the card is internal and labelled Sensitive (`CONFIDENTIAL_MADE`, unchanged); a **logged update** from the card carries only the neutral line (decision b).
- A **private** thread keeps BL-334's neutral line only: no type, due, owners or match.
- The open-work list in the check (Part 3 B) sends a confidential thread's content to the model in the same call as any other (a read-only call on the laptop, no new destination); the reply is kept as words only.

**Files.** `system/scripts/sweep.py` (`conv_content` gives confidential threads the new fields, private ones none; `vip_log` writes the neutral line); the prompt wording is in Part 3 B's Opus step; `system/templates/dashboard/src/today.js` / `dashboard.html` (the Confidential marker next to the new chips). No guarded area.

**Done when:**
- a confidential thread card shows a summary, type, due and owners; the client report and client-safe one-pager built from the same database contain nothing from it;
- its Log click stages a neutral line, not the summary; Create work item still makes an internal, Sensitive item;
- a private thread shows only its neutral line;
- nothing in vip.json, the card, the page data or the route results holds message text or the word VIP.

**Tests.** Extend `test_vip_confidential.py` (card fields, neutral log line, client report and one-pager exclude), `test_vip_private.py`. Size **S**. Model: **Sonnet**.

## Guarded areas, in one place

| Area | Touched? | Where |
|------|----------|-------|
| live_server.py runs (the check and its prompt) | **Yes** | Part 3 B only: two hunks (`VIP_PROMPT` with `VIP_INVITES`, and `vip_check`; Part 3 B step 4). **Opus.** Jarvis reviews. |
| live_server.py routes (not runs) | **Yes** | Part 1 (`/api/alerts/handled`, `/api/alerts/log`). Sonnet; Jarvis reviews. |
| `reach.py`, the guard hook | No | `sweep.py vip` is already `DERIVED`; no new script command. |
| `permissions.py`, `.claude/settings.json` | No | The check keeps its own allow list. |
| `filechange.py` | No | Nothing creates or changes a project file. |
| `tracker.py`, `schema.sql` | No | Staging only, through the existing proposal format. |

If the build finds it needs any "No" row, it stops and goes back to Jarvis.

## Order

0. **Live probe and measurement** (Jarvis or Alan, in a live vault; Sonnet cannot do this): confirm the three facts in point a, run stage 1's prompt by hand on Haiku and Sonnet and read the cost from `usage.py` (needs BL-343 phase A on the branch used). **Done 15-10-2026** (Step 0 result, above): the facts hold; stage 1 on Sonnet. The short-window rerun gave $0.30 to $0.35 an empty check on Sonnet, which supersedes Part 3 by Part 3 B.
1. **Part 1 data and card** (Sonnet): shape, Handled, Replied, Log, routes, UI. With a stand-in claude and the existing prompt.
2. **Part 2 matching** (Sonnet): needs Part 1's card shape in sweep.py, so it follows Part 1.
3. **Part 4** (Sonnet): small, rides on Part 1's shape; can run beside Part 2.
4. **Part 3 B** (Opus): the one prompt extended, the reply's validation, the cost line and the `check_minutes` guard; last, after `bl342-fixes` lands, so the prompt carries every field from Parts 1, 2 and 4 (Part 3 B, step 8). Jarvis reviews it before push. (Part 3, two-stage, is superseded by cost.)
5. **Integration pass** (Sonnet): the whole run end to end with the stand-in claude, the real-browser screens, the UX baseline, the sample-vault goldens.

Parts 1 and 2 can be split between two Sonnet agents only if they agree the card shape first (both edit sweep.py).

## Estimate

| Part | Size | Model |
|------|------|-------|
| 1 The card | M | Sonnet |
| 2 Matching | M | Sonnet |
| 3 B One call with the card fields (Part 3 superseded) | S to M | Opus |
| 4 Confidential mail | S | Sonnet |
| Step 0 probe, integration, UX baseline | S | Jarvis / Sonnet |
| **Total** | **L** | |

## Rules for this sprint

- Nothing in the sample data, tests or docs uses a real name; fictional people only (as `test_vip_conversations.py`).
- The check stays read-only on Microsoft 365; nothing is sent, replied to or changed there. Chase only opens the existing draft pane.
- Nothing reaches the tracker without Alan's approval in Review. The only write the card makes is a pending proposal he clicked for.
- No schema change and no new setting (Part 3 B drops `vip.check_model`).
- No message text is kept: vip.json, the card, the debug log and the staged update hold Claude's own words, references and counts.

## Tests

Run in the review round: `test_vip_threads.py` (new), `test_vip_conversations.py`, `test_alert_actions.py`, `test_sweep_alerts.py`, `test_vip_confidential.py`, `test_vip_private.py`, `test_vip_screens.py`, `test_live_server.py`, `test_settings*`, `test_no_real_names.py`, and `dev/tools/check.py` (no figure may rise; the dashboard source and built `dashboard.html` are committed together).

## Review-round checks

1. The diff to live_server.py is Part 3 B's two hunks and the two routes only; `VIP_TOOLS` and `DENY_TOOLS` are unchanged and a test pins them.
2. No call from either stage can write (allow list, no Bash).
3. One call per check, on the default model, with no `--model` flag.
4. A thread keeps one card across a reply, a late ID and a restart; two cards for one ID are merged.
5. No "VIP" or message text anywhere shown, stored or logged; `grep -ri vip` on the page data and route results is clean.
6. A staged update has `based_on`, is pending, is one proposal per item, and a confidential one is the neutral line.
7. The Chase rule is code, not the model's say-so; an invalid match falls to New.
8. Handled and Replied are not confused with done: no work item changes status from a card.
9. The UX baseline's ten checks, with screenshots; the card's due date, type and owners read at 1100px in dark.
10. An old vault keeps its own `vip` values; `check_minutes` outside 10 to 240 is read at the bound.
11. `test_no_real_names.py` and `check.py` pass.

## Report

To be written by the build sprint: what was built per part, the step 0 figures and the measured cost per check and per day from Part 3 B's cost line, which UX checks were made, and anything Jarvis changed in review.
