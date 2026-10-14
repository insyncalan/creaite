# BL-286 — Meeting prep, reimagined: the server side (sprint-prep-server)

The Python and live-server work behind parts A, C and D. The dashboard (popup, shaping panel, Meetings › Prep view, the peek
over the dialog) is not touched here; the dashboard sprint builds on these routes.

## Modules

- `system/scripts/prep_shape.py` (C): suggestion chips, the focus filter, the shaping sources, the reply's checks, `merge`
  (Regenerate keeps Alan's edits), and `prep-focus.json`.
- `system/scripts/prep_view.py` (A and D): typed sources, the facts line, the series chip and timeline, people as names, dated
  reporting, one page model (`assemble`), the Briefing renderer, and the stored content in `system/staging/prep/`.
- `drafts.py`: the kind `shape` (template `system/templates/drafts/shape.md`), counted under the feature `shape` in
  `draft-stats.json`.
- `prep_page.py`: `build` (the server's Prep page) and the CLI's `build` now render the **Briefing layout** and store the
  content. The classic `render` is kept, unused by build, for its existing tests. `using(d)` lets a caller collect the dashboard
  data once.

## Routes

Every route is `POST`, local, with the page token (`do_POST`'s `authorised()`), like Prep page. `key` is the Prep brief's
meeting key (`HH:MM|title` today, `YYYY-MM-DD|HH:MM|title` tomorrow or any stored day). A bad key is a 400.

| Route | Request | Response |
|---|---|---|
| `/api/prep/brief` | `{key}` | `{ok, facts: {decisions, risks, issues, overdue, since, has_last, invite_first, text}, series: {text, cadence, nth, last}, people: {organiser, invitees: [{name, initials, registered}], count, confidential}}` |
| `/api/prep/chips` | `{key}` | `{ok, chips: [{kind: invite\|overdue\|carried\|milestone, id, label, why, insert}], confidential}` (at most 6) |
| `/api/prep/shape` | `{key, instruction, reading?, current?: {notes, drafted}, clear?: true\|[sections], run?}` | Streamed like `/api/draft`: `sources` (`{sources, confidential}`), the run's steps and text, then `draft`: `{ok, checks_ok, checks: [{level: error\|warn, section, note}], reading: {focus: [{id?, text}], aim, show}, drafted, notes, kept, sources, text, sentences, unsourced, confidential}`, then `done`. Or JSON `{ok, nothing\|message}` with no run. 409 when a run is busy |
| `/api/prep/filter` | `{key, focus?: [IDs], excluded?: [IDs or paths]}` | `{ok, filter: {items, documents, n, N, docs_n, docs_N}, show?}`; without `focus`, the accepted one |
| `/api/prep/focus` | `{key}` | `{ok, focus: record \| null}` |
| `/api/prep/focus/save` | `{key, instruction?, reading?, notes?, drafted?, excluded?, questions?, accept?}` | `{ok, focus: record, page: vault path \| null}`. `accept: true` counts `used` or `edited`; any save regenerates the Agendas page when one exists |
| `/api/prep/focus/clear` | `{key}` | `{ok, cleared, page}` |
| `/api/prep/view` | `{key}` | `{ok, model, stored, saved: {path, at, at_shown} \| null, live}`; Claude is never run |

Existing routes are unchanged: `/api/prep/page` + `/api/prep/build` (now the Briefing layout, and the content is stored),
`/api/prep/open`, `/api/draft`, `/api/agenda/save`.

### Shapes

- **Filter item:** `{id, table, p, text, owner, due, status, type, why: [..], in_focus, excluded}`. Why is one of: `in focus`,
  `blocks X` / `blocked by X` (links table), `same workstream (W) as X`, `same milestone (M) as X`,
  `cited in the same minutes|transcript|mail thread|Teams chat (…) as X`.
- **Filter document:** `{path, name, why: [..], excluded}`: the file a focus item comes from, one it was raised again in
  (`mentions.jsonl`), or a document whose name shares the focus's words. None for a confidential meeting.
- **Typed source:** `{type: item, id}` · `{type: file, kind: word|excel|pdf|transcript|text|page|file, path, section?}` (open
  with `/api/open {path}`) · `{type: mail|teams, label, url?}` (`url` only when the sweep kept an `https` link) ·
  `{type: tracker|invite|alan|carried|text, label}`.
- **Page model** (`view.model`): `{id, key, internal: true, meeting: {title, day, day_shown, start, end, where, confidential,
  project, project_name, body}, port, focus (record), work: {mode: all|focus-only|focus-first, rows, n?, N?, docs_n?, docs_N?,
  documents?, not_listed}, about, notes: [{text, date, date_shown, source (typed), source_text}], questions, m365, carried,
  reporting: [{project, name, line, health, icon, week_ending, headline, points (≤3), summary, reports: [{kind, date,
  date_shown, name, online, link}]}], series: {series, meetings: [{day, day_shown, this, raised: {actions, decisions, raid},
  not_covered, minutes (typed), files, prep}]}, sources (typed), outline, brief: {series, people}}`.

## Stored formats

- **`system/staging/prep-focus.json`** (server's own write):
  `{"version": 1, "meetings": {"YYYY-MM-DD|HH:MM|title": {key, title, day, start, instruction, reading: {focus: [{id?, text}],
  aim, show}, notes: {objective|talking_points|ask|carried_over: [{text, sources: [typed]}]}, drafted: {same}, edited:
  [sections], excluded: [..], questions?: [text], accepted_at, updated_at}}}`. `questions` (BL-286 D) are Alan's edited questions and
  asks from the prep page: they replace the research's on the page and the Agendas file, survive Regenerate and Refresh research, and
  `questions: null` gives the research's back. `edited` is worked out against `drafted` on every save: a section
  whose text differs from creaite's last draft is Alan's. Regenerate (`/api/prep/shape` with `current`, or the stored
  record) keeps those sections; `clear` (true, or a list) gives them back to the draft. Limits: instruction 4,000
  characters, 12 lines a section, 600 characters a line, 12 focus entries.
- **`system/staging/prep/<YYYY-MM-DD HHMM> <hash>.json`** (beside `prep-pages.json`): `{id, key, day, title, project,
  built_at, page, context, reply}`, written by `prep_page.build` (and the CLI build once saved). The view uses the live
  context while the meeting is still today or tomorrow, else the stored one; the reply always comes from here.
- `draft-stats.json`: feature `shape`: `offered` when a draft comes back, `used`/`edited` on Accept, `rejected` from the page
  (`/api/draft/stat`).
- Agendas page: `prep_page.save` as before: creaite's own unchanged page is replaced after a backup to
  `system/backups/files/`; a page Alan edited (or any file creaite didn't write) is kept and the new one gets a number.

## Rules kept

- Research is read-only; a **confidential** meeting is shaped from Alan's text and tracker items only: no invite, ranking,
  minutes, documents or carried points in the prompt, and the run is `shape-closed` (`KIND_TOOLS`: no tools;
  `KIND_DENIES`: Read, Grep, Glob, Bash, the web and every Microsoft 365 reading tool).
- The only writes are the server's own: `prep-focus.json`, `system/staging/prep/`, the Agendas page, `draft-stats.json`.
  Nothing reaches the tracker; nothing is sent; pages are Internal.
- Dates DD-MM-YYYY on screen (`*_shown`, `line`, `text`), YYYY-MM-DD stored. Projects by name (`project_name`).
- Debug log (`prep` area): run IDs and counts only (`shape s-…: 14 sources, closed False`; `focus saved: 4 lines, 1 edited`).

## What the dashboard sprint needs to call

1. **Popup (A):** `/api/prep/brief` for the facts line, the series chip and the invited chip (avatars from `initials`).
2. **Shape (C):** `/api/prep/chips` for the chips; `/api/prep/shape` (stream it like `draftAsk`; send `current` with the
   boxes' text and `drafted` so Regenerate keeps edits, `reading` after *change*); show `checks`; `/api/prep/filter` with
   `focus` to preview "What's in focus"; Accept = `/api/prep/focus/save` with `accept: true`, `drafted` and `notes`;
   Discard = `/api/draft/stat {feature: "shape", event: "rejected"}`.
3. **Prep view (D):** `/api/prep/view` renders everything; in-place note edits go to `/api/prep/focus/save` (no `accept`);
   ticking an item out sends `excluded`. Open prep page still uses `/api/prep/page` + `/api/prep/build` to (re)research.
4. **Settings:** add `"shape"` to `drafts.FEATURES` and to the page's `DRAFTFEATURES` together (left out here because the
   Settings test counts the page's switches against `FEATURES`).

## Questions for Alan

1. Regenerate keeps edits **per section** (Objective, Talking points, Ask, Carried over), not per line. Good enough?
2. An invitee the register doesn't know is shown by the words of their address ("lucy.hart@…" → "Lucy Hart", marked
   unregistered). Or show the address?
3. The facts line counts new **issues** as well as risks ("1 new risk, 1 new issue"). Keep issues?
4. "n of N" counts every open item of the project (plus the focus items) as N. Or only those listed on the page?
