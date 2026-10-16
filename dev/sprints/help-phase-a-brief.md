# Help Phase A: rewrite brief (#158)

Product Manager, 16-10-2026, for Team Stark (Haiku writes, a second agent reviews). Decisions are Alan's, approved 16-10-2026 on #158 (Option 2). Source files: `system/templates/help.md` (the one source), then `python3 dev/tools/build_guides.py` and `python3 dev/tools/run_tests.py test_help`. The review note with the ten sample rewrites and the findings is `dev/sprints/help-review-2026-10-16.md`: read it first.

## The decisions the text must record

1. **Option 2:** shorter pages, one home for each fact. Reference says what a feature is; How do I… says how to do a job; neither repeats the other (link instead).
2. **Budget:** Help ends under 15,000 words (this table totals 14,791: Start here 830, How do I… 6,744, Reference 7,217). No How do I… page over about 500 words, no Reference page over about 600.
3. **Printed guides** become a one-page first-day card and a two-page top-12 card (Phase B); the full Help stays on screen. For Phase A, keep `build_guides.py` working.
4. **Mac only:** write ⌘ and Return, drop Ctrl and Windows; drop every narrow-window, 320 and 640 pixel and high-contrast promise (desktop and 900 px only, Alan, 15-10-2026).
5. **Four rules** say what stays on the laptop and what may sit in the company OneDrive (the projects, and the daily backup zip). Not "never cloud folders".
6. **Screen Help:** pressing ? opens a panel for the screen, a quiet "Press ? for help with <screen>" line, a once-only first-visit line, and a link in each empty state. Phase B builds it; Phase A adds, to each screen's pages, the two to five jobs it lists (see "Screen lists" below).
7. **Ask creaite answering from Help** is later, not in 2.2.0. Say nothing about it.

## House style (plain British English, no real names)

- Write to someone who started today. Short sentences. One job per page. Steps start with a verb and name the button in bold.
- Plain words: say "save" and "approve", not "stage" or "apply" unless the page is about applying; say "Claude", not "cx-minutes"; say "the live server" only after the glossary or Start here has explained it.
- Banned in reader text: `cx-`, `BL-` numbers, `/api/`, `.json`, `staging`, file paths under `system/`, "Alan", "Alan's decision", and the old section name "To decide" (renamed Intake and Review by #168). The only code-style text is the phrases in "Or say:" and the Say this table, and keys as [[K]].
- Every "Settings › …" path must exist: check each against `system/scripts/settings_catalogue.py` (Essentials, People and projects, Advanced, Health).
- Dates shown DD-MM-YYYY in examples; people and projects are the fictional demo ones (Example Programme, Falcon Data Platform, Sara Example).
- Keep the renderer conventions in the comment at the top of help.md (the three H1 parts, ### groups, Where:, numbered steps, Or say:).
- **Write nothing about the run itself:** no "this rewrite", "this base", no status notes.
- Keep every page's id (its title in lower case with hyphens) unless the table says merge or split. For a merged or removed page, keep its old id as a redirect in `help.js` so `#help-howto-…` addresses and ⌘K entries still work.

## Order of work

1. **Batch 1, now (no dependencies):** Start here (6 pages); every How do I… page marked Keep, Trim, Edit, Rewrite or Split without a WAIT; the new pages Archive a project, Why isn't my meeting in Intake, See what changed on a project, Find a person's open work, Glossary; Reference: Keyboard shortcuts, Opening the dashboard, Working with lists, How saving works, Early warnings, Meeting prep, Updates from meetings, Review, Intake, Files, Milestones, Activity, Workstreams, Search, Settings, Client messaging, Dates, Sources, What ask creaite can and can't do, Commands for Claude, Updating creaite, Open creaite as an app, Live server and backups, Troubleshooting.
2. **Batch 2, after the review round on batch 1 (Jarvis, 16-10-2026: no page waits for a cut):** the pages marked WAIT. Write each against what is built today, and add a short "Changes in v2.x" line list at the foot of the page's working notes (not the reader text) for each later item, so only a sentence waits, never a page: Notes and Capture a note and Find updates (#115, #122 in v2.1.0; #117, autosave #119 and focus mode #136 in v2.2.0: say what exists today), Where creaite can draft for you and AI drafts (#117), Chase someone for an update (#153, #154, v2.3.0: merge the two pages for today's behaviour), Today and the Week ahead page (#138, #140, #147, #150, #168 and #105, not #112, which is an idea), Customise the side bar and What the icons mean (#139, #156), Project page and Update a project's state (#133, #134).
3. **Review round (L, mandatory):** a second agent compares every rewritten page with the old text and the code, page by page: nothing true is lost, every route, button name and file name exists (the identity check from HOW-WE-WORK), no banned word, every internal link resolves, the page is within its budget. Report the count of pages changed and any fact removed on purpose.
4. **Finish:** rebuild the guides, run `test_help`, add the tests listed under Tests, commit, hand Jarvis the branch.

## Tests (Phase A adds them, so Phase B and later releases stay clean)

- Word budget per page and in total (the numbers above, a small margin).
- Banned words in reader text, with an allow-list for "Or say" commands. Include "To decide".
- A check that no page says to press Esc twice (#161 makes it one press).
- Every "Settings › …" path exists in the settings catalogue.
- Every [text](#id) link resolves to a page id or a redirect.
- Every page has a "Checked against X.Y.Z" line, which the release step sets.

## Screen lists (for Phase B's ? panel)

Add a line to help.md for each screen: `Screen: Review → approve-what-creaite-found, reject-with-a-reason, fix-the-wrong-project, keys-in-review`. Screens: Today, Work, Review, Projects (list and a project's page), People, Notes, Intake, Files. Two to five jobs each, in the order people need them.

## Page by page

Targets are for the finished page. "→" rows are the pages a split makes. "WAIT" means do it in batch 2.

| Part | Page | Words now | Target | What to do | Note |
|---|---|---:|---:|---|---|
| Start here | The loop | 209 | 180 | Trim | Add the one sentence: edits you make yourself save at once; Apply is for what Claude proposed. |
| Start here | Your first hour | 210 | 170 | Rewrite | Explain vault, launcher and live server in a clause each, or link to the glossary. |
| Start here | Every day | 101 | 110 | Edit | Add Close the day to the rhythm. |
| Start here | Where things are | 149 | 130 | Rewrite | Add More (Intake, Files, Activity, Settings); drop the repeated server rule; side bar words after #156. |
| Start here | Say this | 197 | 150 | Trim | Say once that ABC stands for your own project code. |
| Start here | Four rules | 80 | 90 | Rewrite (wrong) | Use the wording in the review note: what stays on the laptop, what may be in OneDrive. |
| How do I… | Start the day | 118 | 90 | Trim |  |
| How do I… | Close the day | 504 | 170 | Rewrite | Four steps. No file names. |
| How do I… | Review and approve proposals | 1198 | – | Split into 5 (below) |  |
| How do I… | → Approve what creaite found | – | 220 | New (from the split) | The short way, then One at a time. |
| How do I… | → Reject, with a reason | – | 150 | New (from the split) | Includes undoing a reject. |
| How do I… | → Fix the wrong project | – | 120 | New (from the split) |  |
| How do I… | → When it looks like something you have | – | 170 | New (from the split) | Looks like, Merge, Update an existing item instead. |
| How do I… | → When creaite says Looks done | – | 90 | New (from the split) |  |
| How do I… | Find anything | 98 | 90 | Keep | Becomes the target of the search work in Phase B. |
| How do I… | Change an item in words | 714 | 290 | Merge: ⌘K change + Sneak peek | Two pages become one: ⌘K for anywhere, // for an open item. |
| How do I… | Turn a meeting into minutes | 192 | 170 | Edit | Move the agenda-coverage step to its own line. |
| How do I… | Capture a note | 247 | 140 | Rewrite | WAIT for #115/#122 (autosave 2 s, header). |
| How do I… | Keep notes on a project | 265 | 210 | Rewrite | WAIT for #115/#117/#122. |
| How do I… | Turn a note into tracker changes | 240 | 170 | Trim | WAIT for #117. |
| How do I… | Get ready for a meeting | 1111 | – | Split into 4 (below) |  |
| How do I… | → Get ready for a meeting | – | 190 | New (from the split) | The brief. |
| How do I… | → The prep page | – | 130 | New (from the split) | Open prep page, and the page inside creaite. |
| How do I… | → Shape the meeting around one thing | – | 160 | New (from the split) |  |
| How do I… | → Draft an agenda | – | 160 | New (from the split) | Spell out POAD once. |
| How do I… | Follow a meeting from invite to follow-up | 198 | 150 | Trim |  |
| How do I… | Move work on the board | 287 | 170 | Trim |  |
| How do I… | Change an item | 805 | – | Split into 3 (below) |  |
| How do I… | → Change an item | – | 200 | New (from the split) | List, item, words, dates, weekend date. |
| How do I… | → Add an item | – | 120 | New (from the split) |  |
| How do I… | → What staged means | – | 100 | New (from the split) | Staged vs applied, reloads, leaving early. |
| How do I… | Raise, record or withdraw a decision | 356 | 220 | Trim |  |
| How do I… | Update a project's state and health | 265 | 200 | Edit | WAIT for #133/#134 (editor chrome). |
| How do I… | Where creaite can draft for you | 923 | 220 | Rewrite as a table | Replaces Let creaite draft the wording. WAIT for #117 and Polish folding in. |
| How do I… | Manage milestones | 254 | 170 | Trim |  |
| How do I… | Hand over someone's work | 49 | 50 | Keep |  |
| How do I… | Chase someone for an update | 591 | 260 | Merge: Ask someone for an update + Chase one item | WAIT for #153/#154. |
| How do I… | Write the weekly report | 85 | 85 | Keep |  |
| How do I… | Write a client report | 90 | 90 | Keep |  |
| How do I… | Draft a steering-committee one-pager | 148 | 100 | Trim |  |
| How do I… | Make a one-off Word document | 59 | 59 | Keep |  |
| How do I… | Add a project or a person | 122 | 100 | Keep |  |
| How do I… | Change a project's code or name | 148 | 100 | Trim |  |
| How do I… | Be told when someone important writes | 669 | 260 | Rewrite (was Never miss a VIP) | Keep the word VIP only here and in the register, per the rules. |
| How do I… | Keep noise out of the sweep | 116 | 100 | Keep |  |
| How do I… | Undo a mistake | 102 | 90 | Keep |  |
| How do I… | Update creaite | 111 | 90 | Keep |  |
| How do I… | Fix a stopped server and other problems | 256 | 220 | Rewrite as a table by symptom | Absorbs Troubleshooting (Reference). |
| How do I… | NEW Week ahead | – | 130 | New | WAIT for #138, #140, #147, #150, #168. |
| How do I… | NEW Customise the side bar | – | 100 | New | WAIT for #156. |
| How do I… | NEW Archive a project | – | 100 | New | From the Settings reference. |
| How do I… | NEW Why isn't my meeting in Intake? | – | 130 | New | Symptom table. |
| How do I… | NEW See what changed on a project | – | 100 | New |  |
| How do I… | NEW Find a person's open work | – | 90 | New |  |
| How do I… | NEW Glossary | – | 220 | New | Proposal, tracker, vault, sweep, live server, staged, applied, peek, RAID, POAD. |
| Reference | Keyboard shortcuts | 899 | 320 | Rewrite | One short table per screen; fix the repeated [ / ] row; ⌘ only. |
| Reference | What the icons mean | 582 | 370 | Edit | Say what each does, not its shape. WAIT for #139/#156. |
| Reference | Opening the dashboard | 97 | 60 | Trim |  |
| Reference | Working with lists | 2257 | 390 | Rewrite | Delete the 320 px, narrow-window and high-contrast promises. |
| Reference | How saving works | 467 | 170 | Trim | Move the motion paragraph to Settings. |
| Reference | Today | 1497 | 340 | Rewrite | WAIT for #138, #140, #147, #150, #168 (Week ahead, day band, Intake and Review). |
| Reference | Project page | 1963 | 390 | Rewrite | WAIT for #133/#134 (Current state editor). |
| Reference | Notes (with Capture a note and Find updates folded in) | 1659 | 410 | Merge three pages into one | WAIT for #115/#117/#122. |
| Reference | Early warnings | 294 | 220 | Trim |  |
| Reference | Meeting prep | 1191 | 290 | Rewrite |  |
| Reference | Updates from meetings | 291 | 170 | Trim |  |
| Reference | AI drafts | 388 | 220 | Rewrite | WAIT for #117. |
| Reference | Review | 1268 | 340 | Rewrite |  |
| Reference | Intake | 792 | 240 | Trim |  |
| Reference | Files | 372 | 220 | Trim |  |
| Reference | Milestones: Plan and Movement | 534 | 320 | Trim |  |
| Reference | Activity | 488 | 220 | Trim |  |
| Reference | People (with People and projects from 2.1.0) | 1313 | 340 | Rewrite | Resume if #103 returns. |
| Reference | Workstreams | 210 | 140 | Trim |  |
| Reference | Search | 487 | 220 | Trim | Updated by Phase B. |
| Reference | Settings (with Archiving) | 1282 | 290 | Rewrite | Fix every path. |
| Reference | Minutes view, report sheet, client view (v2.1.0 additions) | – | 340 | Fold in from origin/v210-docs* | Check against the code on main when you start. |
| Reference | Client messaging | 78 | 78 | Keep |  |
| Reference | Dates | 127 | 100 | Trim |  |
| Reference | Sources | 29 | 29 | Keep |  |
| Reference | What ask creaite can and can't do | 2532 | 370 | Rewrite | Previously Word documents and permissions in ask creaite. No Alan, no filechange.py. |
| Reference | Commands for Claude | 231 | 140 | Trim |  |
| Reference | Updating creaite | 130 | 100 | Trim |  |
| Reference | Open creaite as an app | 288 | 160 | Trim |  |
| Reference | Live server and backups | 419 | 220 | Trim |  |
| Reference | Troubleshooting | 115 | – | Delete (into Fix a stopped server) |  |

Targets already include the 13% trim on How do I… and 3.5% on Reference that bring the total under 15,000 words. If a page cannot meet its target without losing a true fact, keep the fact and cut elsewhere on the same page; do not exceed the part's total.

## Hand-offs

- Models: Haiku writes (docs, HOW-WE-WORK); the review round is a Sonnet agent. Size L, `haiku` label, the `review` round is mandatory.
- Ask Jarvis (not Alan) about anything that changes behaviour; Help words follow the code on main, not the other way round.
- Phase B (search, jobs home, What's new, ? panel, first-visit line, first-day cards) follows once batch 2 is reviewed; it needs the new page ids, so do not rename them afterwards.
