# #329 shareable minutes: what the check still misses

Banner, 27-10-2026, after Cap's review and Jarvis's scope change (every shown text is checked, failing toward a warning).

## What is checked

`minutes_record.describing_lines` reads the shareable version itself (`distributed_of`, then `shown_text`): each prose line, each
shared table row (every cell), each section heading, the title, the header's lines, and the project's name and client. The guard
`NothingEscapes` in `dev/tests/test_minutes_shareable_329.py` fails if the exported HTML or Word shows a field that was not asked about.

A piece of text is asked about when it names a held item's ID or row ref (any case), or shares two significant words with it
(4 or more letters after a simple word form is taken: a final "ing", "ed", "ion", "ions", "es" or "s", else "e").

## Known limits (not fixed)

- **Synonyms and paraphrase.** "Reorganisation of the analytics group" does not match "Restructure of the client data team".
- **One shared word.** A line sharing a single significant word with the item is not asked about.
- **Short words.** Words under 4 letters ("HR", "IT", "pay") never count, nor do names inside other words.
- **Word forms.** Only the endings above; irregular forms ("ran", "went") and other endings ("-ment", "-ise") are not joined.
- **Owner, made by and deadline cells** of the held item are not part of its words (an attendee is not a description), so text
  naming only the held item's owner is not asked about.
- **Over-listing.** Text that shares two ordinary words with a held item is asked about; one answer per text, again only when its
  words change.

## Other LOWs left as they are (Cap's review)

- The AI redraft of a section is not gated on the answers (its result is checked when the next shareable copy is made).
- A Sensitive item removed from the minutes: lines held back with it stay out (fail closed), but nothing asks about lines that
  described it.
- Hand-written saves (a record edited on disk) can set `layout.carried`, `layout.reviewed` or `layout.plain` directly.
