# #236 followed-person items in Today's Needs attention (v2.6): design note

Branch `v26-followed-needs`. Alan's answers (19-10-2026): (1) the proposals the sweep pulls out of a followed person's mail
or chat, and a note about them written into a project's memory, both reach Today as `From <person>` rows linking to the
proposal or note (Review still holds the proposals); a recorded message Today missed is a bug. (2) Dismissed ones stay gone
unless a follow-up adds a genuine change to an active item or a new item. (3) Private conversations: title and times only.

Where the rows are on screen: since 8d2a1344 the `From <person>` rows and the private-conversation row are drawn in Today's
**Needs attention**; the message cards (Make a work item, Dismiss) stay in **Intake and Review** (`toDecideRows`, `#tdList`).

## 1. Linking proposals and notes to the followed person (derived, not recorded at stage time)

Nothing is added to `sweep.py stage` or `propose.py`. `sweep.followed_sync(st)` (plain code) derives the rows from what is
pending in `system/staging/proposed-*.json`:

- a pending item whose source (`Email · From: …` / `Teams · …`) is from a followed person (address in the register, else the
  `vip` flag `stage` already sets, else the register name) is a **proposal** ref `{file, ref: n, tag}`;
- a pending `file_changes` block whose `source` (same format) is from a followed person is a **note** ref
  `{file, ref: "file_changes", tag: "note"}`. `source` is a new optional key of `file_changes` (cx-edit and cx-sweep set it when
  the note comes from a message); the apply ignores it.
- refs are grouped per thread and type: one `proposal` row and one `note` row per (followed person, medium, normalised
  subject). The row ID is a hash of that, so it is stable.

The rows are entries in `vip.json`'s `alerts` (`kind: "proposal" | "note"`, `medium: mail | teams`), so the existing poll
(`/api/vip`), Dismiss, Handled and Undo routes carry them unchanged (no change to `live_server.py`). They have no `summary`, so
the check's prompt (`vip_open_cards`) never offers them to the model. They hold references only (file, item number, tag), never
message text, with one exception: a row's `sigs` and `seen_sig` (in `vip.json`) hold the first 160 normalised characters of each
staged item's description (or, for an update, the item and its changes), so a repeat can be told from a reword (`sig_similar`).
They are Claude's wording of the item, not the message's, are never sent to the page build, to the check's prompt or to the
reports, and stay on the laptop. The page reads each item's words from Review's own data. When every ref is decided or gone, the entry is dropped.
`vip_open` (reminder counts, weekly report data) ignores them: they are a pointer to Review, not an unseen message.

`followed_sync` runs in memory in `build_dashboard.sweep_alerts` and at the start of each Dismiss / Undo / Handled / Seen, and
is saved by `vip_made_refresh` (the page's 60-second poll, under the server's VIP lock).

## 2. Dismissed stays dismissed; what makes it come back

- **Proposal rows:** Dismiss stores `seen_keys` = the refs' keys (`file#ref`) at that moment. The row comes back (unseen, as new,
  `returned` time set) only when a key not in `seen_keys` is pending: a NEW staged item (new action, risk, decision, promise) or a
  staged update of an active item. A re-mention never reaches staging (`stage` already skips "already proposed" and "already in
  the tracker"), so it adds no key and changes nothing.
- **Note rows:** a note is not an item. A dismissed note row stays gone; a new note on the thread is a new ref but not a genuine
  change.
- **Conversation cards (the existing ones):** the bug found by the fail-first test: dismissing a whole card did not dismiss its
  candidates, so any later message ("thanks") merged the same candidates back as "fresh" and the card returned. Now Dismiss,
  Handled and "all settled" store `seen_sig`: the card's signature (each candidate's text, the ask for an action, decision or risk,
  the matched item, a suggested close, a kept promise). `conv_finish` brings a seen card back only when the new signature has
  something not in `seen_sig` (a new risk or action, a new match, a close or kept promise: a genuine change to an active item).
  A card seen before this change (no `seen_sig`) keeps the old rule.
  A dismissed private conversation has an empty signature, so it stays dismissed.

## 3. Private

A private conversation's row (and a proposal or note row from a thread whose card is private) shows its title (the card's
neutral title: the people in it) and times only: no `From <person>`, no tag, no project, no summary, no "private" or other
label, no items, no Make a work item; Dismiss is its only action, and its link opens the conversation. aria-labels are as plain.
A confidential one is drawn like any other, with the existing "Confidential" mark.

## 4. The recorded-but-missed bug

The invariant test records every kind (message, chat, mail thread, meeting note, private, confidential, replied, quiet,
dismissed) and asserts each unseen one has a row on Today. The causes found are in the commit that fixes them.

## 5. Counts

`VIPS()` already feeds the badge (`vipBadge`), `#tdNew`, the window title and the notification. The new entries are not quiet
and not replied, so they join `VIPS()` and `#nTd` with no other change.

## Guarded files

None needs a change: every route delegates to `sweep.vip_*`. For Jarvis: one sentence for `creaite-rules.md`, in the report.

## Known limits

- **Another wording of an item the card listed.** The card's candidate and the sweep's proposal are compared by words, so an item
  the card listed but the sweep words differently can still be staged as a second proposal: the card says "Confirm the go-live
  date" and the sweep stages "Omar to agree the production cut-over date with the client". It still needs Alan's approval, and
  staging it again is idempotent (the same wording is skipped). The same holds for a dismissed row: "Send the SOW to Mia by
  Friday" reworded lightly ("on Friday") stays gone; a synonym reword ("Share the statement of work with Mia") comes back as new.
- Two further low findings from the review (6 and 7) are known and left as they are.
