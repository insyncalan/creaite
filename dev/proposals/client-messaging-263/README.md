# Proposal #263: AI on the Client messaging field gets the client rules

> **Apply in this order: #186's diff, then this one, then #262's `edit_ai-after-263.diff`.** #262 and #263 both change `result()`. If
> #262's plain `edit_ai.diff` is already in, this diff fails one hunk (patch exits 1 and leaves a `.rej`): do not keep going. In that
> case `edit_ai.py` also refuses to load ("#263 is applied over #262's plain diff…"), so every AI suggestion stops rather than the
> Client messaging field getting the bar without its reply check. Take #262 out (`patch -R`), then apply in the order above.

Alan said yes to this on 20-10-2026 (with #186's decisions). `edit_ai.py` is guarded-adjacent and `live_server.py` is the server, so
neither is changed on this branch: `edit_ai.diff` is the change. It applies **on top of #186's diff**, so apply #186 first. The page
part is on the branch and does nothing new until this diff is applied.

## What is wrong today

An item that is client-visible has a **Client messaging** field in its panel (Work › an item › the details): the plain words a client
sees about it in client reports and client-safe one-pagers. That field has the AI bar like the other longer fields, as the `plain`
place, so Ask gives Claude **every open item ID and every owner's name**, and Claude's reply gets **no client check**.

Worked example (fictional). Example Programme has ABC-A-002 "Sign the statement of work" (client-visible, owner Jane Doe) and ABC-A-004
"Confirm tester names" (internal, owner Omar Ali). In ABC-A-002's Client messaging you select "We need the signed paperwork by Friday"
and press Rewrite. Claude may reply "Omar Ali is still confirming testers (ABC-A-004), so we need the signed paperwork by Friday". If you
press Use, that sentence is saved as the client wording. The client report's end gate would catch the ID at approval, but the
suggestion itself was never checked, and a paraphrase with no ID or name would not be caught later.

## What changes

1. **The page names the field.** A request from the Client messaging field says `field: "client_message"` (with the `plain` place, the
   field's own).
2. **The server applies the client rules for that field** (`edit_ai.client_field`), exactly as on the client sheet (#123):
   - Claude is told only the **client-visible items** a client report may show, and **no people**, plus "This text is for the client…";
   - words you select that already hold an internal item (in any spelling) are refused before anything goes to Claude;
   - a reply that brings in an internal item, a name that isn't the text's or a client-visible owner's, the internal health reason or
     an internal-only marker is **dropped** with "The suggestion was dropped: it held something that isn't client-safe. Try again."
   - `result()` decides again from the request itself, never only from what the context says.
3. **The field comes only with its own place.** `field: "client_message"` with any other place, or any other field name, is refused:
   "That field isn't one creaite can check, so nothing was sent to Claude."
4. **The bar stays off on that field until the server says it does this.** `/api/edit/ai/caps` now lists `client_fields:
   ["client_message"]`. Before the diff is applied the server doesn't list it, so the Client messaging field has **no AI bar** (the other
   longer fields keep theirs); a no is asked again after a minute.

## What you will see

- Client messaging: Improve (Rewrite clearly, Shorter, Make it executive) and Ask…, as now. Suggestions use client-visible items only.
- If your selection holds an internal item: "This text already holds something that isn't client-safe. Fix it first; nothing was sent to
  Claude."
- If a suggestion leaks: "The suggestion was dropped: it held something that isn't client-safe. Try again."
- Until the diff is applied: no AI bar on Client messaging.

## What can still go wrong

- **A tampered page.** The server can't see which field is open: a page changed on purpose could send a Client messaging selection as a
  plain field with no `field`, and get the full facts (the same limit #123 named for the client sheet). The binding protects against
  page mistakes, not against someone editing the page in the browser.
- **The same limits as the client checks (#127):** odd spellings (`A B C - A - 0 0 4`, "ABC A zero zero four"), "O. Ali" or a paraphrase of
  the health reason are not caught in a reply. Claude is never told those facts for this field, which is the main protection.
- **Your own words** (a name, the health reason) already in the selection still go to Claude, as on the client sheet; only an internal
  item ID stops the request.
- **No project.** A new item with no project yet: the request is refused ("There's no project to check this text against"), as on the
  client sheet.

## Review fixes (e8198a48)

- A `field` that isn't text (a list, an object, a number) is refused like an unknown field, never a crash.
- A selection holding the word VIP is refused before Claude for this field (the client check), pinned by a test.
- The stack guard above (the wrong order fails loudly), with a test that applies #186, #262's plain diff and then this one.

## Decisions for Alan

1. **Bar off until applied.** Recommended: yes. Until the diff is in, Client messaging has no AI bar (today it has one with full facts).
2. **Refuse, not make safe** (as #186). Recommended: yes.

## How to apply and undo

- Apply, from the repo root, after #186: `patch -p0 < dev/proposals/client-messaging-263/edit_ai.diff` (`-p0`: no `a/` or `b/` prefix).
- Undo: `patch -R -p0 < dev/proposals/client-messaging-263/edit_ai.diff` (before undoing #186). The page then turns the field's bar off
  by itself (caps no longer lists the field).
- Tests: `python3 dev/tests/test_client_messaging_263.py` (patches a scratch copy with #186 then this diff). `CM_263_UNPATCHED=1` gives
  the copy #186 only (the field tests go red); `CM_263_MUTATE=<name>` breaks one piece of the diff and must go red.

## Size and risk

- Size: **S.** About 30 lines in `edit_ai.py` (`CLIENT_FIELDS`, `client_field`, `_client_reply`, two lines in `context` and `result`) and
  8 in `live_server.py` (`field` in the allowed keys, passed through as text of 40 characters at most, and `client_fields` in caps). Page:
  about 25 lines (`aiClientFieldOn` in `stores/aiEdit.js`, `pkClientMsg` and the field's `ai` options in `panel.js`, the `field` in the
  request).
- Risk: low. It only narrows facts and adds checks for one field, and refuses anything it can't place.
- Needs: an independent client-safe review of the diff.
