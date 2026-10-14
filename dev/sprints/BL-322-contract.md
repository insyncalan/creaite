# BL-322 Sneak peek: the server contract (v1.9.3)

Changed (14-10-2026, additions only, nothing renamed): `refused` also carries `where` (the place in words, for the card);
the route can answer `{"ok": false, "busy": true, "message"}` while an apply holds the tracker (try again); a link's `@n`
is the new item's place in `stage.items` (`@1` unless an update to the open item comes first, then `@2`).

Team 2, branch `v193-sneak-peek-server`. The screen (branch `v193-sneak-peek-ui`) builds against this. Read with
`git show v193-sneak-peek-server:dev/sprints/BL-322-contract.md`. If this changes, a "Changed:" line goes at the top.

## In one paragraph

The box sends what Alan typed to **one read route**, `POST /api/sneak/read`, on every pause in typing and on Enter. The server
reads it in plain code (no model call, nothing written) and answers with what it understood, the changes as from → to, any task,
whether a confirm is needed, whether Claude is needed, a pick list, problems, or a refusal with where to go instead. It also hands
back **the exact proposal items to stage** (`stage.items`). The screen makes a change the way the peek already does: it writes
those items as one dashboard proposal (`source_run: "dashboard"`, already approved, the peek's own file name and `peek` meta) and
applies it at once with the peek's apply (`/api/apply` with no `hold_peek`), then offers Undo (`/api/undo {apply_id}`). Claude
parts go through the existing AI drafts route, `/api/draft`. Quick facts come back from the read route itself.

## 1. `POST /api/sneak/read`

Token-checked like every POST (`X-Creaite-Token`, Host 127.0.0.1/localhost). Read only: never writes a file or the database.

**Request**

```json
{"id": "FAL-A-009", "text": "owner to Sam and due Friday", "picks": {"sam": "Sam Patel"}}
```

- `id` (required): the item open in the peek: an action (`ABC-A-001`), RAID item (`ABC-001`), decision (`ABC-D-001`),
  milestone (`ABC-M-001`) or promise (`ABC-P-001`).
- `text` (required): the box's text, up to 1000 characters. `@Sam Patel` works like `Sam Patel`.
- `picks` (optional): answers to an earlier `choices`, as `{<the word typed, lower case>: <full name>}`.

**Reply** (always HTTP 200 with JSON; `ok: false` only for a bad request or an item that isn't in the tracker, with `message`)

```json
{
  "ok": true,
  "item": {"id": "FAL-A-009", "kind": "action", "table": "actions", "project": "FAL", "title": "Share the Northgate UAT plan",
           "type": null, "updated_at": "2026-10-12 09:14:03.512"},
  "by": "code",
  "understood": [{"start": 0, "end": 12, "what": "Owner: Sam Patel"}, {"start": 17, "end": 27, "what": "Due: Friday 16-10-2026"}],
  "changes": [
    {"field": "owner", "label": "Owner", "from": "Tom B", "to": "Sam Patel", "from_shown": "Tom B", "to_shown": "Sam Patel",
     "confirm": false},
    {"field": "due_date", "label": "Due", "from": "2026-10-17", "to": "2026-10-16", "from_shown": "17-10-2026",
     "to_shown": "Friday 16-10-2026", "confirm": false}
  ],
  "task": null,
  "stage": {"label": "FAL-A-009 owner, due date updated (Sneak peek)",
            "items": [{"op": "update", "table": "actions", "id": "FAL-A-009",
                       "changes": {"owner": "Sam Patel", "due_date": "2026-10-16"}, "based_on": "2026-10-12 09:14:03.512"}]},
  "confirm": false,
  "needs_claude": false,
  "choices": null,
  "problems": [],
  "refused": null,
  "offer_closing_update": false
}
```

Fields:

- `item.kind`: `action`, `raid`, `decision`, `milestone` or `promise`. `item.type` is the RAID type (`Risk`, `Issue`, …).
- `by`: `code`, or `claude` when the card should say "Read by Claude" (only once a Claude draft has been used; the read route
  itself is always `code`).
- `understood`: the stretches of `text` read, as **UTF-16 offsets** (JavaScript string indexes; `end` exclusive) with what
  each meant. For Todoist-style marks; a click that takes a word back out simply edits `text` and reads again.
- `changes`: one row per field changed on the open item, in the order typed. `field` is the **tracker column**
  (`owner`, `made_by`, `promised_to`, `due_date`, `needed_by`, `forecast_date`, `priority`, `impact`, `likelihood`, `status`,
  `latest_update`, `response_action`, `workstream`, `milestone`, `labels`, `client_visible`, `description`, `decision`, `name`,
  `revisit`, `type`, `state`, `state_reason`, `date`). `from`/`to` are stored values (dates YYYY-MM-DD, `client_visible` 0/1,
  `labels` a list); `from_shown`/`to_shown` are for the card (dates DD-MM-YYYY with the weekday on the new one, "Yes"/"No",
  labels joined). A RAID impact or likelihood change adds a row `{"field": "priority", "derived": true, ...}`: show it, it is
  worked out by the tracker (never staged). `confirm: true` marks the rows from the confirm list.
- `task`: null, or one of (section 3) `link`, `action`, `risk`, `promise`, `chase`, `goto`, `facts`, `draft`.
- `stage`: null when there is nothing to stage (a task that isn't a change, a refusal, a problem that stops it, a choice
  waiting, a Claude-only draft); otherwise `{label, items}`: **the exact proposal items**, in order (section 2).
- `confirm`: false, or `{why}`: the change can only be made with ⌘⏎ or a click, never plain Enter.
- `needs_claude`: false, or `{kind, why, off, optional, request}`: see section 4. `off: true` means AI drafts are off for it;
  `why` then says so, and `request` is null.
- `choices`: null, or `{field, typed, options: [{value, label}]}` when a name matches two or more people. Nothing is staged
  until a pick comes back in `picks`. A name that matches no one: no change, and a `problems` line says so.
- `problems`: plain sentences for the card (an unknown workstream, a date it couldn't read, a status that kind doesn't have,
  the reason a better-than-dates milestone state needs, client-visible without its message…). When there are problems and no
  changes, `stage` is null. When some clauses were read and some weren't, the read ones are staged and the rest listed here.
- `refused`: null, or `{why, point_to}` for the Never list (section 5). `point_to` is one of `draft_chase`, `ask`, `cx_edit`,
  `milestone_form`, `project_page`, `settings`, `people`. Nothing is staged.
- `offer_closing_update`: true when an action is being closed or cancelled with no update typed: offer "Add a closing update".
  The screen resends with the update typed (`close it, add an update: …`), which the server reads in the same text.

## 2. Making the change (the existing save path; no new write route)

Exactly as the peek's own save (`pkWrite` in `src/panel.js`):

1. Write one proposal file through `/api/fs {op:"write", path:"system/staging/<pkFile()>", text}` with
   `{"created", "source_run": "dashboard", "files": [], "peek": <meta>, "items": stage.items numbered from 1, each with
   "match": "strong", "flags": [], "decision": "approved"}` (the peek's own envelope; `peek` meta as `pkWrite` builds it, with
   `label` = `stage.label`, so the staged pill and the feed show it).
2. Apply at once: `applyNow({peek: true})` (that is `POST /api/apply {}`), as the peek's ⌘↵ does (BL-306: one step).
3. Undo: `POST /api/undo {"apply_id": <the apply's apply_id>}` (the existing Undo; refused when a later apply exists).
   One proposal, one apply, one Undo, even for a new item with its link (below).

The items `stage.items` can hold:

| What | Item |
|------|------|
| Fields of the open item (one update, all fields together) | `{"op": "update", "table": <table>, "id": <id>, "changes": {...}, "based_on": <updated_at>}` (`based_on` makes a change made elsewhere since a conflict, as everywhere) |
| A label added or removed | in the same update: `"changes": {"labels": [<the full new set>]}` |
| Link it | `{"op": "new", "table": "links", "values": {"from_item": "FAL-012", "to_item": "FAL-A-009", "source": "..."}}` |
| A follow-on action | item 1 `{"op": "new", "table": "actions", "values": {"project", "description", "owner", "due_date", "priority", "status": "Open", "raised", "source"}}`, item 2 `{"op": "new", "table": "links", "values": {"from_item": "@1", "to_item": <id>, "source"}}` |
| A risk from an action | item 1 `{"op": "new", "table": "raid", "values": {"project", "type": "Risk", "description", "owner", "impact": "Medium", "likelihood": "Medium", "status": "Open", "raised", "source"}}`, item 2 link `{"from_item": "@1", "to_item": <the action>}` |
| A promise | item 1 `{"op": "new", "table": "promises", "values": {"project", "promised_by": <Alan>, "promised_to", "description", "due_date", "status": "Open", "raised", "source"}}`, item 2 link `{"from_item": <id>, "to_item": "@1"}` |

**`"@1"` (new in tracker.py for BL-322):** in a link's `from_item` or `to_item`, `@n` means the ID tracker.py gives item `n`
of the same proposal, which must be a new action, RAID item, decision, milestone or promise written before it. That is how a
new item and its link go in one apply and come out with one Undo. Nothing else in the file format changes.

New items' `source` is `"<Alan's name> (Sneak peek on <id>), YYYY-MM-DD"`; `raised` is today.

The tracker's own rules decide: the read route already runs the staged items through the tracker's dry run (the same one
`tracker.py validate` and apply use) and returns any refusal in `problems` (with `stage` null), so an Enter that is offered
is one the apply accepts. The apply still checks again.

## 3. Tasks (`task`)

- `{"kind": "link", "from_item", "to_item", "other": {"id", "title"}}`: "blocked by FAL-012", "this blocks FAL-M-003". Both
  ends must exist; staged as the links item above.
- `{"kind": "action" | "risk" | "promise", "values": {...the new item's values...}, "link": {"from_item", "to_item"}}`: the
  card shows "New action (ID given when applied)". Staged as two items above. A risk only from an action.
- `{"kind": "chase", "pane": {"id", "tone": 0 | 1 | 2 | null, "to": <full name> | null}}`: open Draft chase (BL-298) with
  `POST /api/chase/pane` and that body (tone 0 First, 1 Second, 2 Firmer; null = from the chase count). Nothing is sent.
- `{"kind": "goto", "target": "source" | "milestone" | "project" | "ask", "ref", "path"}`: `source`: `ref` is the source
  text and `path` a vault-relative file when the source names one (open it with `POST /api/open {path}`); `milestone`: `ref`
  the milestone ID; `project`: `ref` the code; `ask`: open ask creaite with the item attached.
- `{"kind": "facts", "topic": "chased" | "source" | "links", "rows": [{"label", "text"}]}`: read only, from the tracker and
  `chases.json`. Shown as the answer card; nothing to stage.
- `{"kind": "draft", "field", "draft_kind"}`: a Claude draft; `needs_claude` carries the request (section 4).

## 4. Claude parts (`needs_claude`), through `/api/draft`

`needs_claude.request` is the body to send to the existing `POST /api/draft` (streamed like every draft: a `sources` event,
then a `draft` event with `{ok, text, sentences, ...}`; see `drafts.py`). Show Claude's version beside Alan's with **Use this**
or **Keep mine**, count it with `POST /api/draft/stat {feature, event}` as the drafts module does, and on Use stage
`{"op": "update", "table", "id", "changes": {<field>: <text>}, "based_on"}` and apply as in section 2.

| Alan types | `needs_claude.kind` | `request` | On Use, field |
|------------|---------------------|-----------|---------------|
| "write a client message" | `client` (existing) | `{"kind": "client", "id"}` | `client_message` |
| "draft the reasoning" / "draft the options" (decisions) | `thinking` (existing) | `{"kind": "thinking", "id", "field": "reasoning" \| "options"}` | `reasoning` / `options` |
| "tidy the update" (actions) | `sneak-update` (new) | `{"kind": "sneak-update", "id", "mode": "tidy"}` | `latest_update` |
| "… because <reason>" (actions) | `sneak-update` (new), `optional: true` | `{"kind": "sneak-update", "id", "mode": "reason", "text": "<reason>"}` | `latest_update` |

For "… because": plain code already puts the reason into the update it stages (works with AI drafts off); `optional: true`
means Claude can word it better if Alan asks. With AI drafts off (`settings.json drafting.<feature>` false: `client`,
`thinking`, `update`), `off: true`, `request: null`, and `why` says which switch is off; the plain-code changes still work.

## 5. Never in this box (`refused`)

| Typed | `point_to` |
|-------|-----------|
| email, Teams, send, message someone (not "client message") | `draft_chase` |
| all / every / each … (more than one existing item) | `ask` (or cx-edit) |
| health, project details | `project_page` |
| settings | `settings` |
| the people register, add a person | `people` |
| the baseline date | `milestone_form` (a rebaseline records a decision) |
| project, ID, source, raised, closed date, delete | `cx_edit` |
| a question beyond the item's own facts | `ask` |

## 6. The confirm list (`confirm` and the row's `confirm: true`)

Rewording the description, a milestone's name or the decision (old and new both in the row); cancel (actions, RAID), withdraw
(decisions), drop (promises); decision made (with its date, today, and who made it); client-visible on (refused with a problem
and a `client` draft offer when the client message isn't complete); removing Sensitive; a milestone's state (and its status
Done or Cancelled), with the reason required when it is better than the dates suggest; a risk becoming an issue ("this has
happened": the response stays and becomes its resolution).

## 7. Dates in Alan's words (Europe-agnostic, the server's local day; tests pin it with `CREAITE_NOW`)

"today", "tomorrow", "Friday" (the next Friday after today; on a Friday, a week today), "next Tuesday" (next week's Tuesday),
"next week" (+7 days), "end of the month", "in 3 days", "in 2 weeks", "20-10" (this year), "20-10-2026", "20/10/26",
"push it out a week", "push it back 2 days", "bring it forward a week" (from the item's current date; today when it has none).
Stored YYYY-MM-DD; shown DD-MM-YYYY.
