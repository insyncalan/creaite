# Help Phase A: the gaps behind the WAIT pages (16-10-2026)

Written from the board on 16-10-2026. It lists, for each item Phase A's batch 2 waits for, where it stands and what that does to the Help page. Source: `dev/sprints/help-phase-a-brief.md`.

## The answer

Batch 2 cannot wait for one thing. Of the five WAIT groups, only the Notes group (#115, #122) lands in v2.1.0. The rest are v2.2.0 or v2.3.0, and one names the wrong item. Recommendation: write each page against what is built, and keep a short "changes in v2.x" line list per page, so only a sentence waits, never a page.

## Gaps

| # | WAIT item | Board today | Pages waiting | Gap | Recommendation |
|---|---|---|---|---|---|
| 1 | #115, #122 (Notes header, one editor foundation) | v2.1.0, In Progress | Capture a note, Keep notes on a project, Notes (reference) | The brief expects "autosave 2 s" from these, but autosave is #119 (v2.2.0, Todo) and focus mode is #136 (v2.2.0). The Notes page can be written once v2.1.0 is cut, and it must not mention either. | Write against the v2.1.0 build. Add a v2.2.0 line for autosave and focus mode. |
| 2 | #117 (AI on selected text: sparkle, hover bar) | v2.2.0, In Progress | Turn a note into tracker changes, Where creaite can draft for you, AI drafts | It is in progress but not in v2.1.0; the pages describe a feature users do not have yet. | Write the pages as "today" in v2.1.0 (✦ on report sections, Draft buttons) and rewrite in v2.2.0 when #117 lands. |
| 3 | #133, #134 (plain profile, report sheets and Capture on the shared editor) | v2.2.0, Todo | Update a project's state and health, Project page (reference) | Not started; the Project page rewrite should not wait on editor chrome it does not mention. | Split: rewrite the Project page now, and leave the editor sentences for v2.2.0. |
| 4 | #153, #154 (Chase: "I sent it", right-click a person) | v2.3.0, Todo | Chase someone for an update (the merge of two pages) | Two releases away. The merged page would sit unwritten for months, and today's two pages are the confusing ones (Help review). | Do the merge now for today's behaviour, and add the right-click and "I sent it" lines in v2.3.0. |
| 5 | #112 (redesign Week ahead) | v2.2.0, Todo, state "Idea" | NEW Week ahead, Today (reference) | **Wrong dependency.** #112 is an idea. The Week ahead and day band are built through #138, #140, #147, #150 and #168 (renamed section and fold, now above Week ahead), plus #105 (the Week ahead fold, v2.1.0). | Point these pages at #138, #140, #147, #150, #168. Write the Today page after v2.2.0 is cut. |
| 6 | #139, #156 (rail flyouts, the left rail) | v2.2.0, Todo | NEW Customise the side bar, What the icons mean | Not started. The icons page can be written now, since it says what each does, not how it is arranged. | Write What the icons mean now; hold Customise the side bar until #156 is Ready. |

## Pages the brief does not mention that are now affected

- **Today:** #168 renames "To decide" to "Intake and Review" (v2.2.0). Any Help text saying "To decide" must change with it. Add to the banned-words test.
- **Portfolio:** #162 adds a legend and tooltip to the 8-week bars (v2.2.0), and the colour or shape of the bars may change. Do not describe the bars until Alan chooses.
- **Esc and the peek:** #161 (v2.2.0) changes Esc from two presses to one. Do not write "press Esc twice".
- **Reports:** v2.1.0 adds the Reports page and reporting space (#72). Help's Reports pages are a batch 1 candidate only if they are rewritten after the cut; the brief should say which.

## What I need from Jarvis

1. Confirm the dependency fix on the Week ahead pages (#112 to #138, #140, #147, #150, #168).
2. Decide whether batch 2 waits for v2.2.0's cut or runs per item with the per-page "changes in" lines above. My recommendation is the latter.
3. Add "To decide" to the banned words and "press Esc twice" to the checks.
