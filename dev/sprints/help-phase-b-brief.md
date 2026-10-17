# Help Phase B: finding it (brief for Team Stark, #158)

Product Manager, 17-10-2026. Sonnet, size M, labels `sonnet` and `review`. Phase A (the words) is on help-158a; Phase B builds on its page ids, so do not rename a page in this phase. Decisions are Alan's, approved on #158 (Option 2, 16-10-2026) and answered since (the ? key, the first-visit line, 17-10-2026). Mockups: `dev/mockups/help-options-mockup.html` (home, search, a task page, What's new) and `dev/mockups/help-screen-options-mockup.html` (the ? key panel and screen 4, the first-visit line). The Phase A review note is `dev/sprints/help-review-2026-10-16.md`.

## The decisions the build must record

1. **One search over all of Help**, local and instant, nothing sent anywhere. ⌘K uses the same index.
2. **No "? Help" button beside page titles.** The ? key opens a side panel on the jobs for the current screen. A quiet foot line says "Press ? for help with <screen>".
3. **A first-visit line**, once per screen, under the title (rules below).
4. **A home of jobs** and **a What's new tab**.
5. **The printed guides are replaced** by a one-page first-day card and a two-page top-12 card; the full Help stays on screen.
6. **Ask creaite answering from Help is later**, not in v2.2.0. Say nothing about it.
7. **Mac only, desktop and 900 px**; no Windows or narrow-window words.

## The parts

**1. Search.** One box at the top of Help, focused by `/` while Help is open. It searches every page's text (How do I…, Reference, What's new), shows each result as the page title, its part and the matching line with the word marked, best match first, groups by part, and opens the page scrolled to the match. The match is whole words and prefixes, case and accent blind; a plural finds the singular. An empty result says "Nothing in Help for 'x'" and offers "Ask creaite" (opens ask creaite with the words, no answer from Help). The index is built in the page from the text already loaded (no new request). Today's `#helpQ` (Reference only) and ⌘K's title-only Help rows are replaced: ⌘K lists matching how-tos by title and the best three by line, under "Help". Keep every existing address (`#help-howto-<id>`) and ⌘K entry working.

**2. The jobs home.** Help opens on Start here. After the loop and your first hour, add **The twelve jobs**: a grid of cards, each a job in the words people use, linking to its page. Start with these (edit the order and words in help.md, not in code): Start the day, Review and approve proposals, Turn a meeting into minutes, Prepare for a meeting, Capture a note, Add or change an item, Ask someone for an update, Close the day, Write the weekly report, Write a client report, Find anything, Undo a mistake. The list is a Help file: a new `Jobs:` block under Start here, parsed like the other blocks, with a test that every link resolves.

**3. What's new.** A fourth tab, **What's new**, newest first. It renders the plain release notes for each shipped version (`dev/release-notes/<version>-plain.md` is the source). Decide how they reach the app: copy the plain notes into `system/templates/help/whats-new.md` at release (a step in the release checklist and a test that the installed version's notes are there), never reading `dev/` at run time. A small dot on the **?** key's tab and on the What's new tab shows after an update until the tab has been opened once for that version (remembered per browser, try/catch). The notes in Settings › Health › creaite version stay as they are.

**4. The ? key panel.**
- **?** opens a panel on the right (the same side as ask creaite; not both: opening one closes the other). It lists **two to five jobs for the screen** you are on, a link to that screen's Reference page, and "Search all of Help". Esc closes it and returns focus to where you were. On a screen with no list, ? opens Help's home.
- **The lists are lines in help.md**, edited with the words: `Screen: Review → review-and-approve-proposals, reject-with-a-reason, fix-the-wrong-project, when-it-looks-like-something-you-have, when-creaite-says-looks-done` (ids are page ids). Add the parser for `Screen:` lines (they are not shown on the Help page), and a test that every id resolves. Starting lists: Today (start-the-day, close-the-day, prepare-for-a-meeting), Work (add-or-change-an-item, move-work-on-the-board, change-an-item-from-k, hand-over-someones-work), Review (the five above), Projects and a project's page (update-a-projects-state-and-health, manage-milestones, write-the-weekly-report, keep-notes-on-a-project), People (find-a-persons-open-work, ask-someone-for-an-update, hand-over-someones-work), Notes (capture-a-note, keep-notes-on-a-project, turn-a-note-into-tracker-changes), Intake (turn-a-meeting-into-minutes, why-isnt-my-meeting-in-intake), Files (find-anything).
- **The foot line:** a quiet "Press ? for help with <screen>" at the foot of each of those eight screens. It is text, not a button, and stays.
- **Empty states:** a "How <screen> works" link in each empty state (Review: "Nothing waiting. How Review works").
- Today ? opens Help on the last tab used; keep that for a screen with no list.

**5. The first-visit line (Alan, 17-10-2026).** One quiet line directly under the page title, accent left edge, "Press ? for help with <screen>", once per screen (Today, Work, Review, Projects, People, Notes, Intake, Files). Any key or click clears it and still does its normal job (never swallowed); pressing ? clears it and opens the panel. Never shown over an open item, a dialog or ask creaite (it waits until they close), nor while typing in a field. Remembered per screen in this browser (localStorage in try/catch; if storage fails, once per page load). A setting under Settings › Essentials › Look and help, "Show the Press ? line on each screen", on by default, turns it off. No animation under reduced motion. Test: shows once per screen, clears on a key or click without eating it, never shows over an open item or dialog.

**6. The first-day cards.** Replace `guide-first-day.html` and `guide-how-to.html` with a one-page **first-day card** (the loop, your first hour, the four rules) and a two-page **top-12 card** (the twelve jobs, one line and the page name each). `dev/tools/build_guides.py` builds them from help.md (a card is a Help block, not a copy); `test_help` checks they are current. Keep the release build's guide check working, and remove the two long guides only after the cards pass.

## Tests

A search test (a word on a Reference page, a word on a how-to, a plural, no result); ⌘K shows the same how-tos; the jobs grid links resolve; every `Screen:` id resolves; the ? panel opens and closes with Esc and returns focus; the first-visit line rules above; What's new shows the plain notes and its dot clears once; the cards are current. Desktop and 900 px, light and dark. Existing `test_help` and `test_help_loop` pass (the page titles and part structure they pin stay).

## Files

`system/templates/help.md` (the `Jobs:` and `Screen:` blocks), `system/templates/help/` (What's new), `system/templates/dashboard/src/help.js` and `src/core/` (search, tabs, the panel, the first-visit line), the eight pages' foot lines and empty states, `settings_catalogue.py` and `settings-defaults.json` (the new setting), `dev/tools/build_guides.py`, `dev/dashboard-spec.md`, tests.

## Dependencies and risks

- **Phase A merged first** (the page ids are stable after it). The Phase A pages that wait on builds (Week ahead, the side bar, Chase) are written when those land; search finds whatever is there.
- **#161 (one Esc to close a peek)** and #143 (the hover standard): the ? panel's Esc follows the shared layers, so it closes before the peek.
- **Search quality is the words' quality**: a result list full of near-duplicates means a Phase A page repeats a fact; log those rather than hiding them.
- **Keep addresses**: any renamed or merged page keeps its old id as a redirect.
- **Not in scope:** ask creaite answering from Help, a "? Help" button beside titles, Windows or narrow-window text.
