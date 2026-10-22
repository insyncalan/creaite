# C-CONTRACT: what C provides and what C expects from A and B (#232, release 2.6, 20-10-2026)

Agreed once, so A, B and C can build in parallel without touching each other's files. C owns `core/intakeApi.js`, `intake.js`, `review.js`, `ask.js`, `today.js`, `core/nav.js`, `core/keys.js`, `core/motion.js`, `core/server.js`, `files.js`, `activity.js`, `main.js`, `shell.html`.

## 1. `core/intakeApi.js` (C, built; part 1)

No DOM of the old pages. Same names and behaviour as before; `intake.js` re-exports every one, so an existing `import ... from "./intake.js"` keeps working until C2.

| Export | What it is |
|---|---|
| `MTG()` | the saved calendar's meeting rows (`D.meetings.rows`) |
| `MRUN` | per-meeting run state by calendar id (`"loading"`, `"processing"`, `"checking"`, `"draft"`, `"skipped:..."`, `"failed:..."`) |
| `nowHM`, `mtgLater(m)` | the clock (replaceable in tests through `apiSeams.nowHM`) and "has not ended yet" |
| `mtgBusy()` | a run is going (`shared.RUN` or `shared.BUSY`) |
| `mtgCheckable(m)`, `mtgSkip(m)`, `TXWHY` | can a transcript be looked up; why a meeting is skipped; the words |
| `jobLive(url, body)` | a transcript job through the run engine, not a chat (stub with `apiSeams.jobLive`) |
| `checkMeeting(m)` | look the transcript up again |
| `UPLOAD_TYPES`, `UPLOAD_MAX`, `uploadInboxFile(file)` | the upload rules and call: `{r, ext}`, `null` (skipped, a snack says why) or `false` (server too old) |
| `previewInbox(path)`, `removeInbox(path)` | the preview dialog (`#inPrev`, in `PageDialogs.jsx`) and the remove with Undo |
| `refreshCalendar({chat})` | `askLive("refresh calendar")`; `chat:false` keeps ask creaite's panel closed and adds no message; resolves `true` when it ran, `false` when blocked (no live server, or a run is going: a snack says so) |
| `intakeHooks` | the old pages' redraw functions; no-ops unless `intake.js` sets them. Goes with the old page in C2 |
| `apiSeams` | test seams (`intake.js` still exports it as `intakeSeams`) |

## 2. What C expects from A (`components/intakeReview/actions.js`)

```
irPickFiles()          // open the hidden file input (Add files; the palette's "Add files to Intake")
irAddFiles(files)      // FileList or File[]: upload each through uploadInboxFile, then reloadData; the one upload path
irProcessAll()         // Process all ready (skips private, confidential and unsure files; says how many were left out)
irProcessById(id)      // Process one meeting by its calendar id (Today's day line; the palette's "Intake: process meeting ...")
irRefreshCalendar()    // refreshCalendar({chat:false}) with the irBlocked guard
```

C rewires to these in C2: `ask.js` (palette: `irPickFiles`, `irProcessAll`, `irProcessById`) and `today.js` (`dayProcess` -> `irProcessById`, `[data-refcal]` -> `irRefreshCalendar`). Until A's names exist, C keeps calling `intake.js` (`processMeetings`, `renderMeetings`, `#inboxFile`).

`stores/intakeReview.js` keeps exporting `irLiveCounts()` (`ready`, `to_approve`, `badge`, `all`), `irTarget` and `irReveal` (Today, Close the day, First thing and the palette use them). `irReady` must exclude unsure files and `irLiveCounts().badge` must follow the same rule (the rail, Today's line, the tab title and the palette show that one number).

## 3. What C expects from B

`panel.js` keeps exporting what `review.js` thinning keeps (`decide`, `isMin`, `rejectMinutes`, `rjMenuFor` and the other names `proposals.jsx`, `work.js`, `core/keys.js` import from `review.js`). B's "Open Intake" snacks in `panel.js` call `go("intake-review")` (or `go("review")`, which redirects).

## 4. Names C has already changed (C1, part 1)

Rail title "Intake" (id `review`, button `data-v="review"`, badge `#revBadge` unchanged), icon `inbox` (the mockup's tray; `ICONS.inbox` and `RailIcon` both), `TABNAME["intake-review"]` = "Intake", Go to "Intake", "Add files to Intake", "Intake: process meeting ...", Today's heading "Intake", Help screen key `intake` (reference `intake`), the page's `<h1>` is A's (`#v-intake-review h1`, "Intake"; C's help-screen title lookup uses that selector, not an id).
