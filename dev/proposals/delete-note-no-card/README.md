# Delete note with no approval card (#255)

A proposal for Jarvis, with a plain summary for Alan. Built 20-10-2026 on branch `v26-delete-note-card`. This changes a guard,
so it was built as one and then attacked as one (see "Second review" below).

## For Alan: what changes

- **Delete note** on the Notes tab now just does it. You still get the confirm box ("Delete “…”?", Cancel is the default).
  Press **Delete note** in it and the note moves into the project's archive at once. **There is no approval card** in
  ask creaite any more. Your click is the approval.
- The message that follows says "Moved “…” to the archive" and has **Undo**, which brings the note straight back.
- **Move back** of a deleted note (Files › Archived) also works at once, with Undo, and no card. It still never replaces a
  note that has taken the old name: it comes back as "<name>-2".
- The confirm box's small print now says "It moves as soon as you press Delete note, and the message that follows has Undo."
- Nothing else changes. Moving a **report or minutes** back, and **archiving or restoring a project**, still go on the card.

## For Alan: what stays safe

- It is still the same move, never a real delete. One `.md` note goes from its notes folder into that folder's own
  `_Archive` (a name already taken there gets -2, -3…). Its bytes and its file date are kept exactly, and Undo or Move back
  restores it exactly (tested).
- Only the note you saw moves. If the note was changed after you opened it (another window, say), nothing moves and you are
  told so in plain words: "Not deleted: the note changed since you opened it. Open it again and try once more."
- Nothing else is saved while the note is checked and moved (the same locks as before: no save, draft or rename lands in
  between). If another job is writing just then, nothing moves and you are asked to try again in a moment.
- As before, it waits while ask creaite is working on mail, Teams or a document.
- Inside creaite the move is still made the guarded way. The server builds the move itself, the database's one writer
  makes it, and only with a one-time approval the server writes for exactly that move. A file someone drops into staging by hand
  never moves a note.
- It is recorded twice: in the applies record (Activity, where Undo lives), and as one line in the files log
  (`system/config/files-log.jsonl`, "note-archive" or "note-back"). The files-log line is only a record, so there is still
  just one Undo.

## For Alan: what ask creaite still cannot do

- It cannot delete or archive a note by any route. Moving a note into `_Archive` with `filechange.py` is refused outright
  (never). Deleting a note with `filechange.py` goes on the card, as before ("a note moved by ask creaite stays a card"). A
  CHANGE card with a note's move is refused. It cannot stage or apply one either.
- It cannot use the new button's route. The route only answers the open dashboard: the page's secret token, this
  machine's own address, and the browser's own "same page" marks. ask creaite has no way to make a web request at all: web
  fetches and `curl` are denied, its guard runs only creaite's own scripts, and none of those calls the server. The token is in
  no file and in no environment ask creaite's runs get (tested).
- It can still only *ask* for any other change. You approve those on the card, as now.

## Decisions taken (defaults; one line for Alan each)

1. **Move back of a deleted note: also no card.** Alan's rule of thumb (a reversal of his own delete is no card). It goes
   through its own button route. The old card route now refuses a note's Move back, so there is one path. *Alan: keep it like
   this, or keep Move back on the card?*
2. **Confirm box kept, plus the Undo toast.** The issue allowed the button's own confirmation. Delete note already had a confirm
   box, so it stays as the one question. The Undo toast was already there after Approve and now follows the click.
3. **The files log gets a record-only line.** filechange.py never lists or undoes it, so Activity › What ask creaite changed
   doesn't show it, and Undo stays the applies record's alone. A second Undo for the same move would compete with the first.
4. **#124's card route `/api/notes/delete` is removed.** A page older than the server gets "the live server is older/newer"
   (reload). The page in this branch tries the new route first and, on a server from before #255, falls back to the card.
   So the branch is safe to run either way.

## What is in this folder

| File | Applies to | What |
|---|---|---|
| `reach.diff` | `system/scripts/reach.py` | `PAGE_MOVES = ("notes", "notes_back")` and the comments. `CARD_ONLY_MOVES` is **unchanged**: the mover still needs the server's one-time marker for these kinds |
| `tracker.diff` | `system/scripts/tracker.py` | `card_move_problem`'s refusal for a note's own move names Delete note / Move back instead of the card. `check_move` and `card_marks` are **unchanged**: the page's move writes the same marker, bound to its own proposal's bytes |
| `live_server.diff` | `system/scripts/live_server.py` | `POST /api/notes/delete/now` and `POST /api/files/move-back/now` (DRAFT_ROUTES: do_POST's Host and token check). Also `page_call` (loopback peer, `Sec-Fetch-Site: same-origin`, an `Origin` of this server's port on a loopback host), `note_delete_refusal` (symlink, unchanged-since-shown, the rename's rule), `page_move` (stage from `system/guard/`, `card_moves_allowed`, `tracker.py apply`, never leaves a proposal behind) and `page_move_log`. #124's `/api/notes/delete` is removed, and `/api/files/move-back` refuses a note. LOCK, then NOTES_LOCK |
| `creaite-rules.diff` | `system/creaite-rules.md` | One sentence in BL-141's "Sensitive, on one card" naming Delete note from the Notes tab (and a deleted note's Move back) as the exception. The #124 sentence under Retention is made true again |
| `tests.diff` | five existing tests | `test_notes_delete.py`, `test_card_only_moves.py` (changed only for `notes`/`notes_back`, and says so in its docstring), `test_notes_card_only_ops.py`, `test_notes_delete_browser.py`, `test_notes_row_menu_browser.py`: card steps become the button's |

`permissions.py` needs no change: no permission rule changes.

Already on the branch (unguarded): `archive.page_move_problem` and `archive.PAGE_MOVES` (the server's last check that a spec is one
note's move and nothing else), `DeleteNote.jsx` and `files.js` (the direct calls, with the older-server fallback),
`help.md` (Notes › Delete note and Undo), the rebuilt `dashboard.html`, and the new `dev/tests/test_delete_note_no_card.py`.

## How to apply

From the repository root, on this branch:

```
git apply dev/proposals/delete-note-no-card/reach.diff dev/proposals/delete-note-no-card/tracker.diff \
          dev/proposals/delete-note-no-card/live_server.diff dev/proposals/delete-note-no-card/creaite-rules.diff \
          dev/proposals/delete-note-no-card/tests.diff
python3 dev/tools/check.py
python3 dev/tests/test_delete_note_no_card.py
python3 dev/tests/test_notes_delete.py
python3 dev/tests/test_card_only_moves.py
python3 dev/tests/test_notes_card_only_ops.py
python3 dev/tests/test_archive_move_back.py
python3 dev/tests/test_notes_delete_browser.py
python3 dev/tests/test_notes_row_menu_browser.py
```

Each diff passes `git apply --check` on `v26-delete-note-card`. Once `reach.PAGE_MOVES` exists, the new test file's
expected failures run as normal tests by themselves. Nothing has to be unmarked.

## Tests and evidence

`dev/tests/test_delete_note_no_card.py` covers the issue's (a) to (g):

- (a) the page deletes at once: no card, no marker left, one files-log line. No token, a wrong token, another Host, no browser marks, cross-site,
  another site's or port's Origin, no Origin, GET: all refused (403/404). #124's route has gone. The same move staged by hand is
  never applied.
- (b) ask creaite: `filechange.py move` refused, `filechange.py delete` in a run → exit 3 (the card), propose.py stage
  refused, CHANGE card refused, hand-staged apply refused. No HTTP tool (DENY_TOOLS, hook refuses curl, wget, nc,
  `python3 -c`, a script with a URL). No other script sends the token. The token is in no vault file and no run's
  environment. A script's plain call with the token is refused by both routes.
- (c) a note changed since it was shown: refused in plain words, left in place; an empty version refused; the new version
  then deletes. The rename's rule (outside content). The LOCK rule: while NOTES_LOCK is held the route waits with LOCK held
  and nothing staged or applied; while LOCK is held it answers busy.
- (d) -2, -3 in the archive.
- (e) Undo and Move back restore the bytes and the modification time (ns) exactly. Nothing is left in Review. A note's Move back
  never goes on the card. Move back never lands on a note that has the name.
- (f) a report's Move back and a project's archive still give a card. The direct Move back refuses a report. The lists agree
  (`PAGE_MOVES` ⊂ `CARD_ONLY_MOVES` = `propose.SERVER_CARD_ONLY`).
- (g) outside the notes folder, a folder named `x.md`, two files, an extra `to`, `..` (both kinds), a symlink, no version,
  not archived: refused by the route. The mover refuses another engagement, the portfolio, a subfolder, a non-note, a rename and a
  deeper place. `page_move_problem` refuses two files, none, an item, other kinds, a remove, `.docx`, `..`, an absolute path
  and extra keys.
- Mutations (class `Mutations`): each mutant is applied to a throwaway vault's copy of the scripts and must turn its own test
  red: let any file through (`page_move_problem` → None), skip the unchanged-since-shown check, drop the token check, let a
  non-page caller through (`page_call` → True), give ask creaite an HTTP tool (WebFetch and curl off the deny list). The
  mutant's text must exist exactly once, so a stale mutant can't pass.

Fail-first: on the branch without the diffs, `CREAITE_255_FORCE=1 python3 dev/tests/test_delete_note_no_card.py DeleteNoteNoCard`
runs the real bodies of the 11 tests that need the diff, and all 11 fail (expected failures). With the diffs applied in a scratch
copy, all 23 tests pass and all 5 mutants go red, each for its own reason (seen: "None != 403", "True is not false", "'WebFetch'
not found"). Also green there: test_notes_delete (25), test_card_only_moves (11), test_notes_card_only_ops (18),
test_archive_move_back (10), test_health_fixes (30), test_notes_delete_browser (8, real Chrome: it proves Chrome's own fetch
passes `page_call`), test_notes_row_menu_browser (18), check.py OK. On the branch itself: check.py OK, the new file OK (13
expected failures), test_no_real_names OK.

## Second review (adversarial, after building)

I tried to make ask creaite, or a stale or forged request, delete or move a note.

Found and fixed:
1. **A failed or raising apply could leave the page's proposal in staging.** Every later Apply would then show "Left in
   staging". `page_move` now removes it in a `finally` whenever the apply didn't succeed.
2. **A symlinked "note" got the misleading "changed since you opened it" answer.** It is now checked first, as "isn't a note
   that is there". `notes_target` already 404s it, so this only guards the window between the lookup and the check.
3. **The mutant for the unchanged-since-shown check silently stopped matching after a refactor.** `Mutations` caught it, because a
   mutant's text must be there exactly once. Updated.

Tried and held:
- `page_call` against odd Origins: one with a path or `@`, `localhost.<other site>`, no port, another port, `null` (a
  `file://` page): refused.
- A hand-written proposal (page `/api/fs`, Terminal, by name): refused by the mover (no marker). The full Apply leaves it.
- ask creaite through filechange.py, propose.py, a CHANGE card, a confirmed request: never, refused, or the card.
- ask creaite reaching the route: no tool can make an HTTP request. A plain client with a stolen token is still refused by
  `page_call` (no browser marks, wrong Origin). DNS rebinding: refused by the Host check.
- Replaying a captured request after the note changed: refused (version). Replaying after Undo with identical content would
  delete it again. That needs the page's token and a same-origin call, so it is the page itself. Accepted.
- A request racing a save: waits for NOTES_LOCK (tested). Racing another job: busy, nothing moved.

Residual, unchanged from #124's card (for Jarvis):
- A same-origin script injection into the dashboard (XSS) could call this route, as it could call `/api/apply`, `/api/fs`
  or Approve today. The card was no defence there either, because a script on the page can press Approve. The script policy
  is still report-only (BL-255).
- ask creaite editing the note through `filechange.py` (a separate process, ordinary) in the milliseconds between the version
  check and the move isn't blocked by NOTES_LOCK. The archived note would carry that edit, undoably. The card had the same
  window.
- The direct Move back has no unchanged-since-shown check. The archived file is in `_Archive`, which ask creaite can never touch.
- `note_card_apply`, `NO_STAGE` and `server_edit_card`'s `note` argument are now unused for notes. They are left in place to
  keep this diff small; removing them is a safe follow-up.
