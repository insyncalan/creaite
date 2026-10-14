# BL-288 part 2: the dashboard surfaces (sprint-vip-private)

Part 1 (this branch) removed the label from everything outside the dashboard: `report.py`'s outputs (through
`build_dashboard.early_warnings`' `vip_overdue` text and `prep_rank`'s reason), the prep page, the Excel export's Review
sheet, the skills (cx-weekly-report, cx-review, cx-sweep), `creaite-rules.md`, ask creaite's prompts (`VIP_PRIVATE_RULE`
in `live_server.py`, on `ASK_PROMPT` and `CONFIRMED_PROMPT`; `VIP_PROMPT`'s gists) and Help. Test:
`dev/tests/test_vip_private.py`. Part 2 does the screens, in `system/templates/dashboard/` once the ES-module work has
landed (the file names below are the split blocks on main on 13-10-2026 and will move).

## Surfaces left for part 2

| Surface | File (`system/templates/dashboard/script/`) | Function | What shows today |
|---|---|---|---|
| Work: owner and maker cells, list and board (and a person's lists) | `0034-after-bl-160-js.js` | `cell` | `<span class="tag vip" title="VIP: kind">VIP</span>` |
| Work: the filter | `0140-after-bl-152.js` | `FDEFS[t].push(["vip","VIP",…])` | field "VIP"; values "Owned by a VIP", "Made by a VIP", "Not a VIP" (keep the `vip=` address key) |
| Today: the alert block | `0138-sweep-and-alerts-bl-97-bl-99-bl-98.js` | `vipItems` (fed into `attentionItems`, `0026-today-brief-bl-72.js`) | a VIP chip on each message |
| Today: the weekly report reminder | `0026-today-brief-bl-72.js` | `attentionItems` (reminder line) | chip and "n VIP messages about it not yet seen: check them first." |
| Rail badge and window title | `0138-…js` `vipBadge`; `0139-bl-152-sprint-ux.js` `tabTitle` | | aria-label "n VIP alerts"; title "(n VIP) creaite…" |
| Browser notification | `0140-after-bl-152.js` | `vipNotify` | notification title "VIP: <who>" (shows on screen and in Notification Centre) |
| Seen snack | `0140-after-bl-152.js` | the Seen handler after `vipPoll` | "VIP alert cleared" |
| Review | `0060-review.js` | `renderReview` | chip on a `vip`-flagged proposal's title (keep the sort first) |
| A person's page | `0079-people-bl-55-bl-56.js` | `renderPerson` | chip after the name |
| Settings › People | `0079-people-bl-55-bl-56.js` | `renderPeopleMgr` | chip in the table (the person form's VIP field, `0140-…js` `#pd_vip`, stays) |
| Draft email | `0129-bl-224-sprint-drafts-writing.js` | `openDraftEmail` | `.devip` note "<name> is a VIP (kind). Check the tone…" |
| Settings › Early warnings | `0140-after-bl-152.js` | `WSIG.push(["vip_overdue", …])` | "Overdue item owned by a VIP" |
| Settings search keywords | `0075-after-bl-214.js` | the settings index (`warnings`, `people` entries' `kw`) | "vip" keyword (harmless; Settings › VIP alerts keeps the word) |
| Style | `style.css` | `.tag.vip` | remove once unused |

Kept as they are: Settings › Capture and alerts › VIP alerts (`vipSectionHtml`), the person form's VIP field, the
register's VIP column, `/api/vip` and the `vip` event part. Tests that assert the chip today
(`dev/tests/test_sweep_alerts.py`, `VipEverywhereTests.test_work_draft_email_today_settings` and the Today alert tests)
and BL-254's snapshots need updating with it.

## Open wording questions for Alan

1. **Work's filter name: approved by Alan (13-10-2026): "People I follow".** Values as suggested: "Owned by someone I follow" / "Made by someone I follow" / "Not followed".
2. **Today's alert block heading**: suggested "Messages to see first".
3. **The weekly reminder line**: suggested "n message(s) about it not yet seen: check them first."
4. **Early warning label in Settings**: suggested "Overdue item owned by someone you follow closely". Part 1 already made the warning's own text neutral by dropping "(VIP)": "Overdue 3 days; owned by Sara Example".
5. **Rail badge, window title and browser notification**: suggested "n messages to see first" for the badge's label, "(n) creaite…" for the title, and the sender's name alone as the notification title.
6. **Draft email note**: drop it, or a neutral "Check the tone and what's included before you send it." with no reason given.
7. **cx-weekly-report's chat line to Alan** (part 1 used it; confirm): "2 messages about ABC you haven't marked seen yet: check them first?"

## Added 13-10-2026 (Alan, via the Product Manager)

- **The window title's "(2 VIP) " prefix** (`vipBadge` in `system/templates/dashboard/script/0138-…js`), which shows in the Dock, the tab and screen shares, and the rail badge's spoken name are also in scope. Alan chooses between a plain count ("(2) creaite…") and nothing: ask him when you reach it.
- **BL-296 is part of this sprint** (the same rows): each followed person's message in Today › Needs attention gets **Dismiss** (replacing Seen, with Undo) and **Create work item**, which opens the new-item peek prefilled from the alert's references only (subject, project, owner Alan, a source in the sweep's format with the link), with an optional "Draft from the message" through a Microsoft 365 read. Saving stages the item, dismisses the alert and records the made ID. See "### BL-296" in dev/BACKLOG.md.

## BL-296 server side: what the rows call (sprint-vip-p2-server, 13-10-2026)

Built in `live_server.py` (`alert_*_route`, beside `vip_seen_route`) and `sweep.py` (`vip_dismiss`, `vip_undismiss`,
`vip_prefill`, `vip_make`, `vip_made_refresh`). Test: `dev/tests/test_alert_actions.py`. Every route is a token POST; nothing
any of them returns says "VIP" (the words are "message" and "Needs attention"), so the rows can show `message` as it comes.

| Row action | Route and body | Answer |
|---|---|---|
| **Dismiss** (replaces Seen; `vipSeen`) | `/api/alerts/dismiss {ids: [id]}` (or `{id}`, `{all: true}`) | `{ok, dismissed, ids, at, message}`; the alert stays in `vip.json` with `seen` set. `/api/vip/seen` is kept for older pages |
| **Undo** in the Dismiss snack | `/api/alerts/undo {ids: [id]}` | `{ok, restored, ids, message}`; also undoes a Seen; a made item whose proposal was removed unapplied is forgotten |
| **Create work item**: open the peek | `/api/alerts/prefill {id, type}` (`type`: `action` default, `risk`, `issue`, `decision`; call again when the type changes) | `{ok, prefill}`: `type`, `table`, `project` (code, or null), `project_name`, `needs_project` (true: show the picker), `values` (`description` or `decision`, `owner` or `made_by` = identity name, `due_date` or `needed_by` null, `type` for RAID), `raised` (the sent date), `source` (sweep format with `Link:`), `link`, `who`, `sent`, `kind`, `marker`, `made` |
| **Draft from the message** | `/api/alerts/draft {id, type, run}`, streamed like `/api/draft` (send `X-Creaite-Seq: 1` for numbered events; Stop is `/api/ask/stop {run}`) | Refused before any run as `{ok: false, off?, message}`: the development repository, AI drafts off (`drafting.sharpen`), a private or confidential message, or a run going (409). Otherwise events `step`…, one `draft` `{ok, prefill}` (the prefill with the drafted title in `values`, a stated date in `due_date`/`needed_by`, `detail`: one or two sentences for the page to place, `drafted: true`), then `done`. The raw reply isn't streamed. Nothing is written |
| **Save** (⌘↵) | `/api/alerts/make {id, type, values}`; `values` takes the form's fields (`project`, `description`/`decision`, `owner`/`made_by`, `due_date`/`needed_by`, `priority`, `workstream`, `latest_update`, `milestone`, `impact`, `likelihood`, `response_action`, `options`, `reasoning`, `status` for a decision); anything else is ignored, and `raised` and `source` are always the prefill's | `{ok, proposal, n, table, values, made: {proposal, n, id: null, state: "staged"}, message}`, or `{ok: false, message}` ("Choose a project for it first.", "Give it a description.", "Not staged: <validation>"), with the alert left as it was. On ok the alert is dismissed and `made` recorded. The file is `proposed-…-dashboard.json` (`source_run: dashboard`, approved), so the page can add it to the peek's staged list (`PKS`) and apply it as usual (auto-apply included): the route never applies |
| "Made FAL-A-014" | `/api/vip` fills `made.id` once an apply has written it (from the proposal's `result_id`); `prefill.made.state` is `staged`, `applied` or `gone` | |

The Microsoft 365 read is the run engine's `only` allow list (`ALERT_DRAFT_TOOLS`: `outlook_email_search`,
`chat_message_search`, `read_resource`) plus `ONLY_DENIES` (Bash, Write, Edit, NotebookEdit, WebFetch, WebSearch) on top of
the usual denies; no guard hook (not a chat), no change to `reach.py`, `permissions.py` or any existing allow list.
