# Proposal #186: the Draft email's AI bar, safe for people outside your company

For Alan's approval. Rounds 2 and 3: the fixes from the reviews of bba13f74 and 447a249f are in (marked "round 2" or "round 3"). `edit_ai.py` is guarded-adjacent and `live_server.py` is the server, so neither is changed on this branch.
`edit_ai.diff` is the change to both (apply from the repo root with `patch -p0 < dev/proposals/draft-email-client-facts/edit_ai.diff`).
The dashboard part is already on the branch, and it does nothing new until the diff is applied.

## What is wrong today

The Draft email has an AI bar (select some words, then Rewrite, Shorter, Longer, More formal, Warmer or Ask). When you press one, creaite
sends Claude the words you selected plus the project's facts: **every open item ID and every owner's name**, internal ones included.
Claude's reply is shown to you as it came back, with no client check.

Worked example (fictional). Example Programme has two open actions:

- ABC-A-002 "Sign the statement of work", owner Jane Doe (Example Client Ltd), **client-visible**;
- ABC-A-004 "Confirm tester names", owner Omar Ali, **internal**.

You draft a chase to jane.doe@client.example, select the opening paragraph and press Rewrite. Claude is told that ABC-A-004 and Omar Ali
exist. Its reply could be "Thanks Jane. Omar Ali is still confirming testers (ABC-A-004), so please send the signed statement of work
by Friday." If you press Use, an internal item and an internal name are in an email to the client.

Since #133 the bar is simply **switched off** whenever the recipient is outside your own domains. That is the interim this proposal
removes.

## What changes

1. **The server decides who the email is for, from the addresses.** The page now sends the email's addresses with the request (the
   person's address, or every attendee's for a follow-up). `edit_ai.py` reads them against Settings › You › Own email domains
   (`identity.own_domains`). The email counts as internal only when **every** address is a plain address on one of those domains.
   Anything else is outside. The page's own idea of inside or outside is never sent, and the server never reads it.
2. **An outside email gets the client sheet's protection** (the same checks #123 and #127 built):
   - Claude is given **only client-visible items** that a client report may show (not Sensitive, not partner-only, not excluded by a
     label), and **no people at all**;
   - if the words you selected already hold an item a client mustn't see (in any spelling: `abc a 4`, `ABC/A/004`, look-alike
     letters), nothing goes to Claude and you are told why;
   - Claude's reply is checked before you see it. If it brings in an internal item, a name that isn't yours or a client-visible
     owner's, the tracker's internal health reason, an internal-only marker or the word VIP, **the suggestion is dropped** and you see
     a plain reason. It is refused, not edited: a quietly cut sentence is easy to accept without noticing.
3. **An internal email is unchanged**: full facts, the reply as before.
3a. **Addresses come only with the Draft email (round 2).** A request that carries addresses with any other place (a note, Current
   state, an item field, a title, the weekly or minutes sheet, the client sheet) is refused, with "Addresses go only with the Draft
   email, so nothing was sent to Claude." Refusing was picked over "treat it as an email" because it is the stricter of the two: such
   a request can only come from a page that is wrong or tampered with.
4. **The AI bar comes back for outside recipients**, but only once the server says it does the above (a small check,
   `/api/edit/ai/caps`). Until the diff is applied the server doesn't answer it, so the bar stays off for outside recipients exactly
   as today, and the page never sends addresses to a server that can't check them.

## What you will see

- An email to someone on your own domains: no change.
- An email to someone outside: the AI bar is there again. The note under the subject adds "AI suggestions on this email use
  client-visible items only, and one that brings in anything internal is dropped."
- If you select words holding an internal item: "This email goes outside your company, and the text you selected already holds
  something internal (an item that isn't client-visible, or internal wording). Nothing was sent to Claude." (A name you typed
  yourself never triggers it: your own words are yours, decision 3.)
- If Claude's reply brings in something internal: "The suggestion was dropped: it held something that shouldn't go outside your
  company (an internal item, a name or internal wording). Try again, or edit the email yourself."

## How outside is decided (each fails closed, that is, counts as outside)

| The recipients | Read as |
|---|---|
| `sam.patel@brightwater.example`, `SAM.PATEL@BRIGHTWATER.EXAMPLE`, `sam+chase@brightwater.example`, `Sam Patel <sam.patel@brightwater.example>` | inside |
| No address on record, no attendees, an empty address, a list with one outside address, `a@brightwater.example, b@client.example` | outside |
| `"sam.patel@brightwater.example" <jane@client.example>` (the name says inside, the address isn't) | outside |
| A display name that isn't plain words (round 2): another address in it (`x@client.example Sam <sam@brightwater.example>`), a line break, a tab or another control character, brackets (`Sam (x@client.example) <…>`), a colon | outside |
| Group syntax: `undisclosed-recipients:;`, `Team: sam@brightwater.example;` | outside |
| Old source-routing forms on an own domain: `x%out.example@brightwater.example`, `out!x@brightwater.example` | inside: the address is on your own domain, so mail goes to your own mail server, which doesn't relay it onwards; in practice it goes nowhere outside |
| An `own_domains` (in any spelling) sent with the request | refused by the server; edit_ai.py reads the domains only from settings |
| `jane@mail.brightwater.example` (a subdomain), `jane@brightwater.example.client.example`, `jane@brightwater.example.` | outside |
| A look-alike or punycode domain (`brіghtwater.example` with a Cyrillic і, `xn--…`), a full-width `＠`, two `@` | outside |
| No own domains set, or settings that can't be read | everyone outside |
| More than 50 recipients, or anything that isn't a list of text | refused by the server with a plain message ("That email has too many recipients for a suggestion (50 at most)…", "The email's addresses couldn't be read…") |
| Own email domains saved as text instead of a list | everyone outside; the debug log says "identity.own_domains is not a list" and `/api/edit/ai/caps` reports `own_domains: "not a list"` (round 2; never the domains themselves) |
| Own email domains a list with no domain in it (`[1]`, `[""]`) | everyone outside; `/api/edit/ai/caps` reports `own_domains: "no usable domain"` (round 3) |

## Which places can reach a client (round 2)

| Place | Where | Can reach a client? | Facts with this proposal |
|---|---|---|---|
| `email` | Draft email | yes | client facts unless every address is on an own domain; no addresses at all = outside |
| `client` | the client report sheet | yes | client facts, bound on the server from the report (#123) |
| `minutes` | the minutes sheet (Internal version only; the Distributed version is read-only) | indirectly: the Distributed version is made from it, leaving out Internal only lines and withheld items | full facts, as today (not changed here; decision 6) |
| `notes`, `current`, `plain`, `line`, `report`, `readonly` | notes, Current state, item fields and Prep boxes, titles, the weekly sheet | no (internal pages; the client report has its own place) | full facts, as today; refused if addresses are sent with them |

## What can still go wrong

- **Cc and Bcc, and changes in Outlook.** The Draft email has only To. creaite judges the addresses it shows you; anyone you add in
  Outlook after copying is not seen. Likewise a suggestion made for an internal email and then forwarded to a client is not checked.
- **Words you typed yourself.** A name, the health reason or an internal-only marker that is already in the words you select goes to
  Claude (they are yours, as on the client sheet); only new ones in the reply are blocked. An internal **item ID** you select is
  refused.
- **Internal minutes follow-up.** That email is marked Internal today and its bar was on. With this change the server looks at the
  attendees: if any is outside, it gets client facts. Safer, but a suggestion may be less specific.
- **Several projects in one email.** Claude gets the first project's client facts. The checks read every project: an item of another
  project (even a client-visible one) in the words you select or in the reply is refused (#127's other-project rule). Strict, so
  Ask may be refused on a multi-project email; it never lets another project's internal item through.
- **Odd spellings the checks don't read (inherited from #127).** In the words you select, `A B C - A - 0 0 4` and `ABC 5` are not read
  as item IDs. In Claude's reply, "O. Ali", "Health: At risk", a paraphrase of the health reason, `ABC-A-0004` or "ABC A zero zero
  four" are not caught. Claude is never told about internal items, owners or the health reason for an outside email, which is the
  main protection; the reply check is a second layer.
- **No project.** An outside email with no project behind it (rare: a follow-up with no project code) is refused, as the client
  sheet does, because there is nothing to check against.
- **Check limits from #127 still apply** to the reply check: it is plain code, so a cleverly paraphrased internal fact with no ID,
  name or the health reason's words in it is not caught. The facts Claude is given are the main protection: it is never told
  about internal items or people.

## Decisions: Alan answered YES to all, 20-10-2026

1. **Exact domain only:** yes. A subdomain of an own domain (`mail.brightwater.example`) counts as outside.
2. **Refuse, not make safe:** yes. A reply that leaks is dropped with a reason, never edited quietly.
3. **Your own words in the selection** (names, the health reason, markers) still go to Claude, as on the client sheet; only an
   internal item ID in the selection stops the request: yes, keep it so.
4. **Internal minutes follow-up** with outside attendees gets client facts: yes.
5. **Cc/Bcc:** yes, creaite judges only the To addresses it shows (it has no Cc or Bcc), and the help says so: Help › How do I… ›
   Ask someone for an update (under step 5), and the AI on selected text paragraph in Reference (`system/templates/help.md`).
6. **The minutes sheet's AI reply** checked the way a client email's is: yes, as its own item (#262, a separate proposal).
- Also yes: the item panel's **Client messaging** field gets a client place (#263, a separate proposal; see the end of this file).

## How to apply and undo

- Apply: from the repo root, `patch -p0 < dev/proposals/draft-email-client-facts/edit_ai.diff` (`-p0`: the diff's file names have
  no `a/` or `b/` prefix, so `git apply` needs `-p0` too), then run the tests below.
- Undo: `patch -R -p0 < dev/proposals/draft-email-client-facts/edit_ai.diff`. The page then falls back by itself (the caps check
  gets no answer, so the bar is off for outside recipients again).
- Tests: `python3 dev/tests/test_email_client_facts_186.py` (before applying it patches a scratch copy; after, it checks the real
  files). `EMAIL_186_UNPATCHED=1` shows the defect (the outside tests go red); `EMAIL_186_MUTATE=<name>` breaks one piece of the
  diff and must go red. Also run `test_ai_117`, `test_ai_select`, `test_edit_ai_client_place`, `test_editor_plain`.

## Size and risk

- Size: **M, and two pieces.** The server part is `edit_ai.diff` (about 95 lines in `edit_ai.py`, 50 in `live_server.py`); the page
  part (about 35 lines in `drafts.js`, `aiEdit.js`, `editor.js`, `server.js`) is on the branch. They can be reviewed apart: the page part
  is inert until the server part is applied.
- Risk: low for leaks (it only adds checks and narrows facts; every doubt counts as outside). The usability risk is suggestions
  refused more often on outside emails, which is the point.
- `live_server.py` change: `recipients` added to the request's allowed keys (passed whole, never cut: a list over 50, of non-text,
  or with a place other than the email is a 400 with a plain message), and the `/api/edit/ai/caps` route (it also says whether the
  own-domains setting is usable). The page asks caps once; a no (an older server's 404) is kept for a minute, so redraws don't
  ask again. No change to how runs start, tools or approvals.
- Needs: an independent review of the diff (client-safe), as #127 had.

## Found while reviewing, a separate item (not fixed here)

The item panel's **Client messaging** field (`system/templates/dashboard/src/panel.js`, around line 728: `row("msg","Client messaging",…)`
with `data-pkml="1"`) is wired to the AI bar as the `plain` place (`panel.js` around line 709: `ai:{place:el.dataset.pkml?"plain":"line",…}`).
So Ask on that field gives Claude the **full facts** (every open item ID and owner) and its reply gets **no client check**, yet that text
is the item's client wording and goes into client reports and client-safe one-pagers. The end gate (`client_leak.findings` at approve
and export) still catches an internal ID or name later, but the suggestion itself is unchecked. Suggested fix, its own item: give
that field a client place (client facts, `client_problems` on the reply), bound on the server from the field name, never the page's
word. Found by the delta review of 447a249f.
