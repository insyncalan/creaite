# Help review (v2.2.0, UI + docs)

Product Manager, 16-10-2026. Alan decides before anything is built. Mockup: `dev/mockups/help-options-mockup.html`.

## The answer

Help is accurate in most places and too long to use. It is **33,700 words**: Start here 1,100, How do I… 10,600, Reference 22,400, across 70 pages (6, 32 and 32), and 16 pages are over 600 words. Nobody reads a 1,200-word "Review and approve proposals". The same fact is also written in two or three places (Notes autosave is in three), so it drifts, and a few places already contradict each other. The fix is mostly editing, not new features:

1. **Rewrite and cut** (Haiku, docs): short task pages, one home for each fact, no developer words. Target about 14,000 words.
2. **Make it findable** (Sonnet, UI): one search over all of Help, a home of the jobs people do most, a What's new tab, a Help button on each screen.

Recommendation: do both, in that order, as one item with two phases (below). Rewriting first matters because a good search over bad pages is still bad.

## What is wrong, by part

### Start here (6 pages)

| Page | Finding |
|---|---|
| The loop | Says "Apply writes what you approved". Where things are says "every edit you make on the dashboard is … applied at once, with Undo". Both are true (edits apply at once, approved proposals apply on Apply) but a first-time reader sees a contradiction. Needs one plain sentence on the difference. |
| Your first hour | Install line (`python3 ~/Downloads/creaite-{version}.zip`) works but is the only place in Help that tells the reader to run a zip. "Live server", "launcher", "vault" are used before anyone has explained them. The checklist and **Settings › Health › Set-up** are both described in one dense item. |
| Every day | Good. Needs "Close the day" in the rhythm (it is the evening step and has a page of its own). |
| Where things are | Lists eight views and misses **More** (Intake, Files, Activity, Settings) and the sidebar changes in #156. The first sentence repeats the live-server rule. |
| Say this | Fine. Uses `ABC` as the example; Help should say once that `ABC` stands for your own project code. |
| **Four rules** | **Wrong.** "Local only: … never cloud folders, never shared" is no longer true: projects may live in the company OneDrive, and the daily backup zip is copied there (locations setting, BL-85 and BL-323). The rule must say what stays local (the database, the engine, the history) and what may sit in OneDrive. This is the one accuracy fault I would fix first. |

### How do I… (32 pages)

Too long to use as steps. A step list should be a list you can follow with one hand on the mouse.

| Page | Words | Finding |
|---|---|---|
| Review and approve proposals | 1,198 | 14 steps, several 150 words. It is five jobs in a trench coat: approve, edit one, reject, wrong project, looks-like-a-duplicate. Split. |
| Prepare for a meeting | 1,111 | Step 1 alone is about 300 words. Brief, Shape this meeting, Draft agenda (POAD) and the prep page inside creaite are four different jobs. "POAD" is never spelled out until step 5. Split into three. |
| Let creaite draft the wording | 923 | A catalogue of every AI feature (10 steps), not a job. It repeats the AI drafts reference. Becomes a one-screen table: where you will see Draft, what it needs, how to turn it off. |
| Add or change an item | 805 | 9 steps. Step 5 explains weekends and quotes `work.weekend_days` in `settings.json`; step 6 mixes staged changes and list changes; step 8 is about reloading. Split New / Change / What "staged" means. |
| Close the day | 504 | 8 steps mixing how the card works, what the files record (`system/staging/day-closed.json`) and settings. The reader's job is "do it every evening": four steps. |
| Never miss a VIP | 674 | Right to use the word here (the one place the rules allow it), but it is the longest "Admin" page and explains the card design before saying how to set it up. Rename "Be told when someone important writes". |
| Capture a note / Keep notes on a project / Turn a note into tracker changes | 3 pages | Stale against v2.1.0 and v2.2.0: "written when you leave the note or after 30 seconds" (now 2 seconds); "the toolbar shows while the cursor is in the note" (becomes the one-line grouped toolbar, #122); the AI menu (#117, spelling folds into every rewrite). Rewrite after #115/#117/#122 land, not before. |
| Ask someone for an update / Chase one item | 2 pages | Two screens for one job (the person page popup and the item pane, BL-83/224 and BL-298). Merge into "Chase someone for an update" with one section for "from a person" and one "from an item". Polish is described as a separate step and will be stale in 2.2.0. |
| Change an item from ⌘K / Change an item in words (Sneak peek) | 2 pages | Same idea twice. Merge, with the Sneak peek as the fast version. |
| Fix a stopped server and other problems | 1 page | Good, but the first symptom list is a paragraph. A table by symptom (red dot, "Reconnect vault", error banner, nothing happens) is faster. |
| Missing | | **Week ahead**, **Customise the side bar**, **Find a person's open work**, **Archive a project**, **See what changed on a project** and **Why isn't my meeting in Intake?** have no task page. |

### Reference (32 pages, 22,400 words)

Reference is where Help stops being help. It reads like the spec. Examples:

- **Word documents and permissions in ask creaite** (2,532 words, 25 bullets): the longest page, and the one with the most developer words (`filechange.py undo`, the live server's memory, "High-risk" tiers). It says "Alan's decision, 10-10-2026" to a reader who may not be Alan. Cut to what a user does: what ask creaite can read, what needs your Approve, what it never does.
- **Working with lists** (2,257): 20 bullets. Promises behaviour down to 320 pixels ("nothing scrolls the page sideways … down to 320 pixels") and Windows high-contrast, which we have decided not to support or test (desktop only, 15-10-2026). Delete those claims.
- **Project page** (1,963): 14 bullets of about 140 words each. Current state's two panes are described to the pixel; this will change with #133/#134. Cut to what the page shows and one line per card.
- **Today** (1,497), **People** (1,313), **Settings** (1,282), **Review** (1,268), **Meeting prep** (1,191): each repeats its How do I… page. Reference should say what a thing is and what it is not, not the steps again.
- **Keyboard shortcuts**: `[ / ]` appears twice (project switcher, then Today's day line) with no label on the first; `/ /` renders as a slash gap; one row (Cmd/Ctrl + Enter) is about 200 words. Needs one short table per screen.
- **What the icons mean**: 30 rows, useful, but "T", "Spark", "Envelope with an arrow" are described by shape not meaning, and it will be wrong after the rail work (#139/#156).
- **How saving works**: includes 120 words on motion and reduced motion. Move to Settings.

### Across the whole of Help

- **Developer words reach the reader:** `cx-minutes` and `cx-edit` (10 times), `BL-286` and `BL-298` (shown to the reader), `/api/edit/ai`, `draft-stats.json`, `system/staging/…` paths, "apply" (50 times, used for three different things), "stage", "approval card", "live server", "peek". Each needs a plain word or a one-line glossary entry.
- **Wrong or inconsistent Settings paths:** "Settings › Health and warnings", "Settings › Work and views › Today", "Settings › Health › Advanced › Review spot-check", "Settings › Essentials › Look and help". Settings now has four places (Essentials, People and projects, Advanced, Health). A test that checks every `Settings › …` path against `settings_catalogue.py` would catch this each release.
- **"Cmd/Ctrl" and Windows hints** (18 places): Mac only is supported. Say ⌘ and drop Ctrl.
- **Dates:** the rule is DD-MM-YYYY shown; several examples are written 15-10 or "16-10-2026" mixed; fine, but one consistent example style would help.
- **No glossary.** Terms a new reader meets before they are explained: proposal, tracker, vault, sweep, live server, staged, applied, RAID, POAD, peek.
- **No sense of what's current.** Nothing says when a page was last checked or which version it describes.

### The two printable guides

`guide-first-day.html` (157 KB) and `guide-how-to.html` (222 KB) are generated from help.md by `build_guides.py`, so they are only as good as it. Two extra faults: the how-to guide prints all 32 tasks, including 1,100-word ones, so it is not a quick reference; and each release must rebuild them or `test_help` fails (a cost on every release). Proposal: print a **one-page "first day" card** and a **two-page "top 12 jobs" card**, and leave the full Help on screen.

## The worst ten, with proposed rewrites

Wording is plain British English, no real names, and short enough to show the style. Items marked (after #115/#117/#122) wait for those items to land.

**1. Four rules** (wrong)

> **Four rules that never bend**
> - **Your data stays yours.** The tracker, the engine and your history live in one folder on this laptop. Project files can live in your company OneDrive if you choose. creaite also makes one closed backup zip a day and copies it to that same OneDrive folder. Nothing goes to any other service.
> - **You approve every change.** creaite proposes; nothing reaches the tracker until you approve. Scheduled runs only propose.
> - **Every item has a source.** The meeting, email or chat it came from is always shown.
> - **Clients see only what you mark.** A client report shows only items you marked client-visible. Confidential material stays out.

**2. The loop** (the contradiction)

Add one sentence under step 4: "Edits you make yourself, such as changing a due date, are saved at once and can be undone. Apply is for what Claude proposed."

**3. Review and approve proposals** (1,198 words → about 350, three pages)

> **Approve what creaite found** — *Nothing reaches the tracker until you approve it. About two minutes on a normal day.*
> 1. Open **Review**. Proposals are grouped by project; items from minutes sit under their minutes.
> 2. Press **Approve routine** (the double tick). It shows what it will approve before it does. Minutes, new decisions, new risks and anything that closes an item are never included: approve those one at a time.
> 3. Open anything you want to check. Change what's wrong, then **Save and approve**.
> 4. **Reject** anything that isn't right and pick a reason. creaite uses reasons to do better next time.
>
> *Not sure about one?* Press **One at a time**: one proposal with its source beside it, guesses first.
> Or say: `review` · `approve minutes for the Falcon steering` · `reject 3, 5 as chatter`
>
> Then: *Reject, with a reason* · *Fix the wrong project* · *When it looks like something you already have*.

**4. Prepare for a meeting** (1,111 words → three pages of about 200)

> **Get ready for a meeting** — *Today › Prep, under the meeting.*
> 1. Press **Prep** on the meeting (on today or a later day in the day line). A short brief opens: what changed since last time, then the project's open actions, risks without a response, recent decisions and decisions still needed.
> 2. Press any line to open it and update it there. Esc brings the brief back.
> 3. Want more? **Open prep page** has Claude read the invite, minutes, mail, Teams and your notes, and builds one page you can print. It is saved in the project's Agendas folder and marked Internal.
>
> Next: *Shape the meeting around one thing* · *Draft an agenda* (the invite text and a timed list, ready to paste into the invite).

**5. Let creaite draft the wording** (923 words → a table)

> **Where creaite can draft for you**
> | Where | What you press | What you get |
> |---|---|---|
> | An action | **Draft** by Latest update | One or two lines of what has happened since |
> | A decision or risk | **Suggest** | Reasoning, options, a response |
> | A project's status | **Generate** | A short executive status with a source on every sentence |
> | A meeting | **Draft agenda** | Invite text and a timed list |
> | An email | **Polish** (in 2.2.0: built in) | A tidier opening paragraph |
>
> A draft is only a suggestion: nothing is saved until you press **Use this**. Turn them off in **Settings › Advanced › AI drafts**.

**6. Keep notes on a project** (after #115/#117/#122)

> **Keep notes on a project** — *Projects › a project › Notes.*
> 1. Open the project's **Notes** tab and press **New note**. Pick a template (Blank, Stakeholder, Lessons learned, Working session).
> 2. Just type. creaite saves about two seconds after you stop; the header says **Saved**.
> 3. Type `/` for headings, checklists and tables, `@` for a person, `#` for a work item.
> 4. Select text and press the sparkle to improve it or turn it into a checklist. Spelling is checked every time.
> 5. Press **Find updates** when you want the actions and decisions turned into tracker changes (next page).

**7. Chase someone for an update** (merge of two pages)

> **Chase someone for an update** — *From an item, press the envelope. From a person, press Draft email.*
> 1. **Chase one item:** open it and press the envelope (or `C`). creaite works out whose it is and drafts the chase. For your own item it drafts a request for help instead.
> 2. **Chase everything a person owes:** open their page, press **Draft email**, untick anything you don't want.
> 3. Press **Copy for Outlook** and paste. creaite never sends anything.
> 4. After you send it, press **I sent it**, so the next reminder is firmer.

**8. Close the day** (8 steps → 4)

> **Close the day** — *The door icon at the top of Today, or ⌘K "close the day". About three minutes.*
> 1. **Catch up.** A quick sweep of your inbox and Teams runs while you read on. It only proposes items; nothing changes.
> 2. **Today.** What moved and what you promised.
> 3. **Loose ends.** Give each open thing a place: **Review now**, **First thing tomorrow** or **Leave**.
> 4. **Tomorrow.** The next day's meetings, with a button to make each prep page.
>
> Press **Close the day**. Tomorrow, **First thing** heads Today with what you left there.

**9. Add or change an item** (805 words → 3 short pages)

> **Change an item** — *Work › any item.*
> - **In the list:** click a value and pick another. It saves at once; **Undo** is in the message.
> - **In the item:** click its ID. Change several things; press **Apply** (or ⌘↵) to save them together.
> - **In words:** press `//` and type "owner to Tom" or "due Friday".
> - **Dates:** type `fri`, `next week` or `+3d`; the field shows what it understood before you save.
> - **A weekend date:** creaite says so and offers the Friday or the Monday.

**10. Word documents and permissions in ask creaite** (2,532 words → about 400)

> **What ask creaite can and can't do**
> - **Read:** anything in the vault, your project files and your home folder, except passwords, keys and the system.
> - **Change files:** a new file, your notes and drafts, or files you named. Each change is backed up and can be undone from **Activity › What ask creaite changed**.
> - **Ask first:** deleting or moving files, anything outside your projects, other people's documents, more than ten files, or anything after reading mail or a web page. These come as **one card**; **Approve** makes them all, **Decline** none.
> - **Never:** send mail or Teams messages, change meetings, or touch passwords and the system.

## Helping Help work better: options

Mockup with five screens: `dev/mockups/help-options-mockup.html`.

| | Option 1: Words only | **Option 2: Words, and find it fast (recommended)** | Option 3: Everything |
|---|---|---|---|
| Rewrites the worst ten, splits long pages, removes developer words | Yes | Yes | Yes |
| One search over all of Help (matching line shown) | No | **Yes** | Yes |
| Home of the 12 jobs people do most | No | **Yes** | Yes |
| What's new tab, with a dot after an update | No | **Yes** | Yes |
| Help button on each screen | No | **Yes, last step** | Yes |
| Ask creaite answers "how do I…" from Help | No | No | Yes |
| One-page first-day card (replaces the long printed guides) | No | Yes | Yes |
| Size | L, Haiku | L Haiku + M Sonnet | L + L, needs a model call per question |
| Risk | Rots again | Low: search runs in the page over text already loaded | Medium: answers can be wrong; sources must be shown |

**Why Option 2.** The pain is that a reader cannot find the page and then cannot get through it. Rewrites fix the second; search, the jobs home and the screen button fix the first, and all of it is cheap and local. Option 3's ask-creaite answer is a good later step once Help is short enough to quote from.

### The four additions, in detail

1. **Search (the biggest win).** Today ⌘K finds a Help page by its title only, and Help's own box filters Reference only. Make one box at the top of Help that searches every page's text, shows the matching line with the word marked, groups results (How do I…, Reference, What's new) and puts the best match first. Open with `/` on Help. Local, instant, nothing sent anywhere. ⌘K uses the same index so "chase" in ⌘K now lists the how-to as well as screens.
2. **A home of jobs.** Replace the long Start here body with the first-day essentials, then a grid of the twelve jobs by the words people use ("Chase someone", "Write a note and find the actions"). Order by how often each is used; the list is a Help file, not code.
3. **What's new.** A fourth tab that renders the plain release notes (`dev/release-notes/<version>-plain.md`, already written for 2.1.0) newest first, with a green dot on **?** and the tab until opened once after an update. The notes already shown in Settings › Health › creaite version stay as they are.
4. **Help for this screen.** A small **? Help** button beside each page title (Today, Work, Review, Projects, People, Notes, Intake, Files) opens a short list of two to five jobs for that screen and a link to its Reference page. Each screen's list is a line in `help.md`, so it is edited with the words, and a test fails when a link points nowhere.

### Keeping it right once it is right

- **One home for each fact.** Reference says what a feature is; How do I… says how to do a job; neither repeats the other. Where a fact is needed twice, it links.
- **A word budget:** no task over about 500 words, no Reference page over about 600, checked by `test_help`.
- **Paths and labels checked:** a test that every "Settings › …" path exists in the settings catalogue, and every button name quoted in bold exists in the dashboard source (a list of exceptions is allowed). It would have caught the four wrong paths above.
- **Banned in reader text:** `cx-`, `BL-`, `/api/`, `.json`, `staging`, "Alan". A test, with a short allow-list (the commands in "Or say").
- **A "checked against" line** per page (version and date), set by the release step.
- **A short glossary** page (one screen): proposal, tracker, vault, sweep, live server, staged, applied, peek, RAID, POAD.
- **Mac only:** ⌘ throughout; drop Ctrl, Windows and narrow-window promises (Alan, 15-10-2026).

## The board item

**Title:** Help: rewrite it short, and make it findable (v2.2.0)

**Problem.** Help is 33,700 words across 70 pages (6, 32 and 32). People cannot find the job they want and cannot get through the pages they find. Parts are wrong (Four rules says "never cloud folders"), stale (Notes autosave, the AI bar, the Chase pages), contradictory (apply vs saved at once), and full of developer words (`cx-minutes`, BL numbers, file paths).

**Design.** Option 2 above, with the mockup. Two phases so the words are right before they are searched.

- **Phase A: the words (Haiku, size L, `haiku` label, review round recommended).** Rewrite the worst ten; split the long tasks; merge the duplicate pairs (the two chase pages, ⌘K and Sneak peek); cut Reference to about 14,000 words in total; add the missing task pages (Week ahead, Customise the side bar, Archive a project, Why isn't my meeting in Intake, See what changed on a project); fix the Four rules; fix every Settings path; ⌘ only; add a glossary. Notes, AI and Chase pages are written after #115, #117, #122 and #153/#154 land (or reviewed against them).
- **Phase B: finding it (Sonnet, size M, `sonnet` and `review` labels).** One search over all of Help (and from ⌘K); a jobs home; a What's new tab with the dot; **? Help** beside each page title (Today, Work, Review, Projects, People, Notes, Intake, Files); the one-page first-day card replacing the long printed guides.
- **Phase C: tests (inside A and B).** Word budget, banned words, Settings paths, button names, links resolve.

**Done when.**
- [ ] No How do I… page is over about 500 words and no Reference page over about 600; Help is under 15,000 words in all.
- [ ] Four rules says what stays on the laptop and what may be in OneDrive.
- [ ] No `cx-`, `BL-`, `/api/`, `.json`, `staging` or "Alan" in reader text (allow-list for "Or say" commands).
- [ ] Every "Settings › …" path in Help exists (test).
- [ ] Notes, AI and Chase pages describe what is shipped in 2.2.0.
- [ ] One search box finds a word anywhere in Help and shows the matching line; ⌘K shows the same how-tos.
- [ ] Help opens on the jobs home; What's new shows the plain notes and its dot clears once opened.
- [ ] A **? Help** button on the eight screens lists their jobs; every link resolves (test).
- [ ] Printed guides are replaced by a one-page first-day card and a two-page top-12 card; `build_guides.py` and `test_help` pass.
- [ ] Desktop and 900 px only; no narrow-window or Windows promises in the words.

**Files.** `system/templates/help.md` (rewrite), `system/templates/help/` (glossary, screen lists, optional), `system/templates/dashboard/src/help.js` and `src/core/` (search, tabs), the page headers for the Help button, `dev/tools/build_guides.py`, `dev/tests/test_help*.py`, the two guides.

**Risks.**
- A big rewrite can lose a true detail. Mitigation: the review round checks each rewritten page against the old text's facts and the code, and the old text is kept in the PR for comparison.
- Phase A touches words that #115/#117/#122/#153/#154/#156 also change. Mitigation: order it after them or have the Notes, AI, Chase and side-bar pages checked last.
- A search over a rewritten Help is only as good as the rewrite, which is why A is first.
- Stable page and tab ids must be kept so existing `#help-howto-…` addresses and ⌘K entries still work (add redirects for merged pages).

**Dependencies.** #115, #117, #122, #153/#154, #156 (words about Notes, the AI bar, Chase and the side bar); #112 (Week ahead); the release notes file `dev/release-notes/<version>-plain.md` (the What's new tab reads it).

**Size and model.** A: L, Haiku (docs, per HOW-WE-WORK). B: M, Sonnet, `review`. Whole item: L.

**Open questions for Alan, with recommendations.**
1. **Option 1, 2 or 3?** Recommend 2.
2. **Printed guides:** replace with a one-page first-day card and a two-page top-12 card? Recommend yes; the full Help stays on screen.
3. **Cut Reference to about 14,000 words (from 33,700)?** Recommend yes; Reference keeps what a feature is, How do I… keeps the steps.
4. **Drop the Windows and narrow-window words?** Recommend yes (matches 15-10-2026).
5. **Where does the first-day Start here go?** Recommend keep it as the first tab, shortened to one screen, with the jobs grid under it.
6. **Ask creaite answering "how do I…" from Help (Option 3)?** Recommend later, once Help is short; not in 2.2.0.
