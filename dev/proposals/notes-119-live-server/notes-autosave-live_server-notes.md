# notes-autosave-page-guarded (449209eb): live_server.py hunks for #119. NOT to be merged; Alan reviews.
Base: origin/v220-editor-base 8c58db2d. Diff: notes-autosave-live_server.diff (1 file, +22 -48).

As the page branch wrote them (7 hunks):
1. Route comment block (~l.7030): `/api/notes/draft` line gone; save is `{path, body?, changes?, base, session?}`; text says the file is written as Alan types, one backup per editing session.
2. `NOTE_SESSION` regex (UUID-like id, 8-64 chars of A-Za-z0-9-).
3. `notes_get_route`: no `draft` in the reply, no stale flag; `images` read from the body only.
4. `notes_draft_route` removed; `/api/notes/draft` leaves `NOTES_ROUTES` (the URL now 404s).
5. `notes_save_route`: reads `session`; if valid passes `session: "<rel>:<id>"` to filechange.perform (filechange keeps one backup per session); a conflict no longer saves a draft; no drop_draft after a save.
6. Comment above rename/relink (draft wording replaced).
7. `notes_relink`: no "has typing not yet saved" skip; `notes_rename_route`: no drop_draft.

Adapted to the new base (3 hunks, #124 delete code that still called the removed draft helpers; notes.py in branch A no longer has read_draft/drop_draft):
8. `note_card_apply`: drop `notes.drop_draft(...)` after a delete card applies.
9. `note_changed`: delete refused only when the file changed, no longer also when a draft exists.
10. `notes_delete_route`: removed the "typing not yet saved" refusal (the page flushes before asking; a changed file is still refused by `base`).
Also: the base's `notes_draft_route` had a #124 lock/exists check; it goes with the route.

Route behaviour: POST /api/notes/draft removed. POST /api/notes/save takes optional `session`; without one, a backup per save as before. Conflict now writes nothing and keeps nothing server-side.
Visibility: nothing here touches ask creaite's reach, the guard hook, client-safe output, reports or search; notes stay internal and passive. The only data change is that no draft files are written under system/staging/drafts/notes/ any more.
