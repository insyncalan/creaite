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

### Step 0 result (the live probe, 15-10-2026)

Alan ran `dev/tools/vip_probe.py --since-days 3` in his own vault (4 followed addresses; read-only, prints ids, dates, counts and costs only). Team Cap read the output; Jarvis decided on it (issue #86).

- **The three facts of point a all hold:** `read_resource` on a mail returns its conversation ID (3 of 3); Teams search results carry the chat ID (6 of 6); Sent Items can be searched by subject (1 result). Option 3 stands.
- **Haiku fails the ID test.** Every long mail conversation ID Haiku returned had a one-character slip against Sonnet's (Sonnet's matched what `read_resource` gave); Teams chat IDs (`19:…`) agreed. A mis-copied ID cannot be a key, so cards would split.
- **Haiku's times were exactly 4 hours early** on every thread both models found: UTC given as if local (the laptop is UTC+4). Not a model error as such, but the prompt never said which zone.
- **Haiku reported two last-message dates in the future** (calendar invites read as messages).
- **Cost of the run:** Haiku $0.023 (22 threads), Sonnet **$0.594** (18 threads) for a three-day window. A real check looks back 30 minutes, so its cost is far smaller; Alan reruns the probe with a short window for the per-check figure (see Part 3, step 5). Part 3 does not wait for it.

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
| live_server.py runs (the check and its prompts) | **Yes** | Part 3 only: four hunks (the prompts, `vip_call`, `vip_check`, `vip_wait_seconds`; Part 3 step 7). **Opus.** Jarvis reviews. |
| live_server.py routes (not runs) | **Yes** | Part 1 (`/api/alerts/handled`, `/api/alerts/log`). Sonnet; Jarvis reviews. |
| `reach.py`, the guard hook | No | `sweep.py vip` is already `DERIVED`; no new script command. |
| `permissions.py`, `.claude/settings.json` | No | The check keeps its own allow list. |
| `filechange.py` | No | Nothing creates or changes a project file. |
| `tracker.py`, `schema.sql` | No | Staging only, through the existing proposal format. |

If the build finds it needs any "No" row, it stops and goes back to Jarvis.

## Order

0. **Live probe and measurement** (Jarvis or Alan, in a live vault; Sonnet cannot do this): confirm the three facts in point a, run stage 1's prompt by hand on Haiku and Sonnet and read the cost from `usage.py` (needs BL-343 phase A on the branch used). **Done 15-10-2026** (Step 0 result, above): the facts hold; stage 1 on Sonnet. The short-window rerun for the per-check cost is still to come and does not hold up Part 3.
1. **Part 1 data and card** (Sonnet): shape, Handled, Replied, Log, routes, UI. With a stand-in claude and the existing prompt.
2. **Part 2 matching** (Sonnet): needs Part 1's card shape in sweep.py, so it follows Part 1.
3. **Part 4** (Sonnet): small, rides on Part 1's shape; can run beside Part 2.
4. **Part 3** (Opus): the two prompts and two calls, the setting and the vip.json lock; last, after `bl342-fixes` lands, so the prompts carry every field from Parts 1, 2 and 4 (Part 3, step 8). Jarvis reviews it before push.
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
