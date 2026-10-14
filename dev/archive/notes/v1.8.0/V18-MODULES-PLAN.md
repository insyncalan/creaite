# BL-231 step 2b: the area split for ES modules

**Status (13-10-2026, branch `v18-areas`):** done. Core and every area are ES modules in `src/`; `script/`, the
prologue and `legacy()` are gone (see "After the last area, as built" at the end). The sections between are the
record of how it was done.

From step 2a (13-10-2026, branch `v18-modules`). The dashboard's script is now 209 pieces in
`system/templates/dashboard/script/`, in today's order. This plan says which pieces go to which module, what each
module shares, and the order the agents should work in. It is drawn from the block markers and each piece's
top-level names; each agent must confirm it from the references before moving code.

## Target layout

`system/templates/dashboard/` keeps `shell.html` and `style.css`. `script/` gives way to `src/`: one module per
area below and `main.js`, which imports them all. The build bundles `main.js` with the pinned esbuild
(`dev/tools/esbuild.py`) into one IIFE in the page's single app `<script>` (`SCRIPT_SLOT`). From then on,
BL-254's snapshots are the check, not byte equality: delete `test_built_page_is_the_page_before_the_move` then.
`split_dashboard.py build` should call the bundler, so `check.py`'s `BUILT`, `build_release.py`'s refusal and
`run_tests.py`'s warning keep working without other changes.

## The areas

The ranges are the piece numbers (`NNNN-…js`).

| Module | Pieces | Size | What it holds |
|---|---|---|---|
| `core/` (several files) | 0001–0006, 0008–0024, 0042–0045, 0057, 0062, 0099, 0115–0116, 0121–0123, 0139, 0141–0142, 0152, 0156–0157, 0180 | 147 KB | `esc`, `html`, icons and tooltips, `D`, dates, `S`/`saveS`, themes, motion, the data globals (`P`, `ACT`, `PEOPLE`, `REG`), vault access, the live server (`api`, `reloadData`, `applyNow`), proposals (`writeProposal`, `save`), snacks and undo, status and `refreshAll`, navigation (`VIEW`, `go`, `navWrite`, links), sources, the calendar and date parsing, the owner combobox, ⌘↵, `addEl`, autogrow, keyboard, the tab title, pulse and the event stream, `diagHook`, the weekend note |
| `rail.js` | 0007, 0077 | 15 KB | the rail and its settings row |
| `today.js` | 0025–0028, 0159, 0164 | 40 KB | Today's brief, conflicts, set-up steps, the set-up and health card |
| `projects.js` | 0029, 0054–0056, 0058–0059, 0081–0083, 0124 | 108 KB | the cockpit, Current state (generate, executive, edit in place, header), insight claims and evidence, dependencies and flow cards, early warnings |
| `work.js` | 0030–0041, 0130–0133, 0147–0150 | 146 KB | `WT`, rows and columns, the board and the decisions board, groups, filters, saved views, person rows, highlight, cell edit, bulk, all items and people tabs |
| `panel.js` | 0046–0050, 0165–0171, 0173–0179, 0181–0183, 0194, 0197–0200 | 149 KB | the detail panel (`CUR`, `drawPanel`), the peek and its new-item form, the error banner, AI drafts in the panel's fields |
| `review.js` | 0060–0061, 0063–0067, 0193, 0195, 0209 | 98 KB | Review (`RSEL`, `applyProposal`, `decide`), filters, reasons, repeats and "probably done", moves, the context menu, review fields |
| `intake.js` | 0052–0053, 0134–0137 | 27 KB | the inbox, Calendar Import, transcripts, Clear day |
| `files.js` | 0068–0069 | 8 KB | Files |
| `activity.js` | 0070–0072, 0205 | 20 KB | Activity and Quality |
| `settings.js` | 0073–0076, 0078–0079, 0127, 0138, 0140, 0153–0155, 0163 | 100 KB | Settings, advanced, people and workstream managers, ignore rules, VIPs, Diagnostics |
| `help.js` | 0091, 0158, 0161–0162 | 12 KB | Help, the keys chip, the panel keys and the peek draft keeper |
| `ask.js` (⌘K and ask creaite) | 0080, 0085–0090, 0092–0098, 0100–0114, 0117–0120, 0207–0208 | 123 KB | search, the change and permission cards, the chat (markdown, times, queue, images, quips, `askStream`), the command palette and its targets |
| `milestones.js` | 0051, 0172, 0184–0192 | 90 KB | the milestone panel, the history feed, the milestones view, slip ranges, the add form, rebaseline |
| `meetings.js` (meetings and prep) | 0084, 0125–0126, 0143–0146, 0201, 0206 | 38 KB | prep updates, the Prep brief and page, decisions needed and in prep, steering, agendas, the meeting hub |
| `drafts.js` | 0128–0129, 0160, 0196, 0202–0204 | 57 KB | Draft email and Chase, the AI drafts scaffold, generated forms, capture chips |
| `main.js` | 0151 | 1 KB | imports every module, then runs today's start-up |

Two areas are added to the list in BL-231: `panel` (the detail panel and the peek are shared by Work, Review and
milestones, and are the largest single block of code) and `drafts`. People stay in `work` (the page) and `settings`
(the register).

## Shared state

*As built, the object is `shared` (`shared.WT`), not `st`: `st` is a local name for a status in about 70 places, so
`st.X` would be hidden inside those functions. core/state.js lists every field (114: core's 21, and each area's,
reserved for it, measured as a top-level `let` named outside its own area or by a test).*

ES module bindings are read-only to importers, so the 46 top-level `let`s that another piece reassigns move to one
`core/state.js` object, `st`, read and written as `st.X`. Measured on today's pieces (owner first, then the pieces that
assign it):

- **Used widely:** `WT` (work; 0022, 0026, 0034, 0080, 0096, 0119, 0120, 0130), `RSEL` (review; 0014, 0063, 0064,
  0123, 0193, 0195), `CUR` (panel; 0048, 0050, 0051, 0056, 0167), `SHOWN` (ask; 0101, 0103, 0108).
- **Two or three users:** `UNDO`, `DR`, `LAYCHOSEN`, `RF`, `CHATFROM`, `RUN`, `CK`, `RVA`, `CE`.
- **One other user:** `LOADING`, `ACT`, `REG`, `OWNPOST`, `LIVE`, `COLORD`, `RZ`, `XCQ`, `HLALL`, `PANELF`, `CURED`,
  `DRH`, `PKDRC`, `PDBASE`, `MREVLEFT`, `MNEWIO`, `RVINBATCH`, `FSEL`, `ACTF`, `SCAT`, `PSORT`, `MCREATED`, `PKS`,
  `CHSTARTED`, `WSNEW`, `HAND`, `MKEYHELD`, `MTGSHOW`, `ALLC`, `PKQ`, `PKNEWIDS`, `DRF`, `CKPICK`.

A `let` only its own area assigns stays in that module. `const` objects that are mutated, not reassigned (`D`, `S`,
`CAL`, `COMBO`, `SRCH`), are plain exports. Each agent re-measures its own module before it starts; the list above is a
regex count and may hold a false positive.

**What every area imports from core:** `esc`/`html`, `ic`, `D`, `S`/`saveS`, `P`/`pName`, dates (`fd`, `toIso`,
`parseWhen`), `api`, `save`/`writeProposal`, `snack`, `go`/`navWrite`/`VIEW`, `refreshAll`/`reloadData`, `addEl`,
`st`. Areas also call each other (Work, Review and milestones open the panel; most views open ⌘K or the chat), so
there will be import cycles. They are safe for function declarations, which are hoisted, but not for a `const` read
while the modules load.

## Load order

Today the script runs top to bottom, and some pieces do things at load (bind listeners, fill `const`s from `D`,
the start-up in 0151). Grouping by area changes that order. So:

1. The core agent first lists each piece's top-level statements that run at load (not declarations).
2. Anything that reads another area's binding at load, or whose order matters, moves into an exported `init…()`
   that `main.js` calls in today's order.
3. Plain listener bindings may stay at module top level.

## Who does what

1. **Core, alone, first:** `core/`, `state.js`, `main.js`, the esbuild build in `split_dashboard.py build`, and the
   bundler wiring in the test runner and `build_release.py`. Every other module is still a transitional "rest of the
   pieces" file, imported in today's order, and the snapshots pass.
2. **Areas in parallel**, one agent each, each owning only its module and the pieces it removes from the rest file:
   Work with Rail; panel; Review; projects with Today; ⌘K and ask creaite; settings with Help; milestones; Intake,
   Files and Activity; meetings and prep with drafts. `main.js` and `state.js` belong to the coordinator: an agent asks
   for a new `st` field or init call rather than editing them, so two agents never edit one file.
3. **Each area's check:** `check.py`, then `test_snapshots` (no golden changes) and the Chrome tests that mention its
   functions. Commit by area.

## Core, as built (13-10-2026)

**The page's one app `<script>`** (`dev/tools/build_dashboard_js.py`, called by `split_dashboard.py build`):
1. **The IIFE:** `src/main.js` and everything it imports, bundled by the pinned esbuild (`var CREAITE=(()=>{…})();`).
   esbuild runs in `src/`, so the same source gives the same bytes anywhere; the build fails on any esbuild error.
2. **The prologue:** `const {a,b,…}=CREAITE;`, every name `main.js` exports except the window accessors below, so the
   pieces in `script/` see the modules' names as the global names they were.
3. **The pieces in `script/` not converted yet**, joined in file-name order (today's order), byte for byte.
When `script/` is empty, 2 and 3 go, and the script is the IIFE alone.

**Why this shape:** the pieces keep working unchanged, and converting an area touches only its own pieces, its new
module and one line of `main.js`. Each area's line in `main.js` is already there, commented out, with blank lines
between, so two branches never edit the same hunk. No shared list needs editing: `state.js` reserves each area's
fields and `globals.json` already lists their names.

**Load order is today's.** A module's declarations run when the bundle loads (before every piece); anything else a
piece did at load (listeners, first draws, `D` conversions) is in an exported `boot…()` function, and the piece's
file in `script/` is now a stub that calls it, so it runs exactly where it ran before. A piece with no load-time
steps is deleted. When `script/` is empty, `main.js` calls the boots in order (the coordinator's last step).

**Core:** `src/core/` holds dom, page, data, server, nav, fields, keys and motion (in today's order in `index.js`),
plus `state.js` (`shared`) and `globals.js` / `globals.json`. Core's modules only read each other's values at load in
that order (dom, then page, then the rest), which `test_snapshots` and the Chrome tests confirm. One cross-area
function replacement was folded: Today's BL-149 block reassigned core's `conflictChoice` at load; its version is now
core's (the chat version never ran). Core imports nothing from the areas: it calls their functions by bare name, which
the prologue resolves at run time.

**Names on window, in one place** (`src/core/globals.js`, lists in `globals.json`, applied by `publish()` at the end
of `main.js`):
- `tests`: the names `dev/tests` use (`b.eval("go('today')")`), put on window when a module exports them. Generated by
  `python3 dev/tools/build_dashboard_js.py globals`; `test_dashboard_split` fails if a test uses a name not listed.
  Already complete for every area, so converting one needs no edit.
- `live`: window accessors for `shared` (`window.VIEW` reads and writes `shared.VIEW`), for the tests (`VSTATE="ok"`)
  and the pieces (`if(VIEW==="work")`). A name a piece still declares (its own `let`, or a `var`) shadows its accessor
  until that area converts.
- `seams`: functions a test replaces (`window.api=…`, `snack=…`): core's `api`, `snack`, `needVault`, `undoApply`,
  `editProposal`, `openPath`; the areas' `decide`, `rbDraw`, `runSearch`, `send`. The owning module keeps a seam in a
  `let` and exports `<module>Seams` with its setter, so the page's own calls see the replacement.
- `not_on_window`: `open` (data.js's item test would hide `window.open`).
- Inline `on…=` attributes: there are none (the page assigns `.onclick` in code), so no list; BL-255 keeps it so.

**check.py:** the JS ratchet (innerHTML, sinks, wrappers, empty catch) and Biome read the source: each module, and the
pieces as one text. Figures unchanged (Biome's noFunctionAssign fell from 8 to 7 with `conflictChoice`). JSDUP also
fails a top-level name declared in two source files: esbuild would rename one and `export *` would drop both. The
compile check compiles the built script. `BUILT` fails a stale page or a build that fails.

**Tests that look for code in the page** read `split_dashboard.readable_page()` (the source in place of the bundle):
the bundle is esbuild's reprint, with its own spacing and quotes and no comments. Screens are checked by
`test_snapshots`, unchanged.

## How to convert an area

One agent, one area, one branch from main. Touch only the area's pieces, its new `src/<area>.js` and its line in
`src/main.js`. Never edit `state.js`, `globals.json`, `index.js` or another area's files; if you need something there,
ask the coordinator.

1. **Convert:** `python3 dev/tools/convert_area.py <area> NNNN NNNN …` with the area's pieces from the table above
   (`--dry-run` first shows what it would flag). It writes `src/<area>.js` (the pieces in order, `export` on each
   declaration, load-time steps in `boot<Area><NNNN>()`, the area's `live` lets as `shared.X`, its seams as `let` +
   `<area>Seams`, imports from core), turns the pieces into stubs (or deletes them) and uncomments the `main.js` line.
2. **Read what it flags** and fix each by hand in the module:
   - a shared name used as an object shorthand (`{WT}` must become `WT:shared.WT`);
   - a shared name declared locally (a parameter or `const WT`): it hides the shared one, check that's intended;
   - a value read while the module loads that is still a `let`/`const` in `script/`: move that use into the boot or
     a function (the piece hasn't run yet when the module loads; esbuild turns top-level `const` into `var`, so this
     reads `undefined` instead of throwing).
3. **Function replacements:** if a piece of another area reassigns one of your functions at load (`pkSetStatus=function…`,
   `openMilestone=…`: Biome's `noFunctionAssign`, 7 left), or yours reassigns another's, fold the final version into
   the owner (only if nothing captured the earlier one), as core did with `conflictChoice`. A module's function can't
   be reassigned from outside; a piece's assignment would throw against the prologue's `const`.
4. **Names from other areas** stay bare (`renderWork()`): they resolve at run time through the prologue. Don't import
   another area yet (that would change the load order); the coordinator adds those imports once `script/` is empty.
5. **Build and check:** `python3 dev/tools/split_dashboard.py build`, `python3 dev/tools/check.py`,
   `python3 dev/tests/test_dashboard_split.py`, then `test_snapshots` (never update a golden) and the Chrome tests that
   mention the area's functions, at most two Chrome tests at once (`CREAITE_CHROME_CAP=2 python3 dev/tools/run_tests.py
   -j 2 …`). Open the page and look for a load error if a test times out (a `ReferenceError … before initialization`
   means step 2's third case).
6. **Commit** the module, the stubs, `main.js`, the rebuilt `dashboard.html` and any fix. On a merge conflict in
   `dashboard.html`, take either side and rebuild; nothing else should conflict.

**Worked example: Files (0068, 0069), tried on 13-10-2026 and reverted (the Files agent does it for real).**

```
$ python3 dev/tools/convert_area.py files 0068 0069
files.js: 2 pieces, 2 with load-time steps (stubs kept), 0 deleted.
```
Nothing flagged. `src/files.js` begins:
```js
/* files.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0068-files.js, 0069-dashboard-pages-….js.
   … */
import { FILES, P, pName, WEEKSTART } from "./core/data.js";
import { $, $$, addHTML, html, ibtn, ic, putHTML, raw } from "./core/dom.js";
import { D, DDATE, fd, S, store, toIso } from "./core/page.js";
import { SERVED, snack } from "./core/server.js";
import { shared } from "./core/state.js";
/* ======================= Files ======================= */
shared.FSEL={p:"All",f:"All",sub:"",quick:"all"}; export const FOPEN=new Set(store.get("creaite-files-open",[]));
…
export function bootFiles0068(){
$("#tree").addEventListener("click",e=>{ …
```
`let FSEL` (also set by Projects' cockpit) became `shared.FSEL`, and its 25 uses `shared.FSEL`; `VIEW` (core's) became
`shared.VIEW`; `renderFiles`, `refreshFiles` and the rest are exported. `script/0068-files.js` is now:
```js
/* ===== Files ===== */
/* BL-231 step 2b: this block is now in src/files.js; what it did at load runs here, in today's order */
bootFiles0068();
```
and `main.js` has `export * from "./files.js";`. The build, check.py, `test_dashboard_split`, `test_snapshots`,
`test_agendas_files`, `test_icons`, `test_work_filters_live` and `test_pages` passed.

**After the last area (coordinator):** move the boot calls from the stubs into `main.js` in the same order, delete
`script/`, the prologue and `legacy()`, add the area-to-area imports (`build_dashboard_js.py imports FILE --all`), and
turn the remaining bare `shared` names into `shared.X`.

**After the last area, as built (13-10-2026, branch `v18-areas`):**
- The nine area branches merged; each `dashboard.html` conflict was resolved by rebuilding. Milestones' 0185 no longer
  reassigns `ceOpen` (Work's `ceOpen` holds the folded BL-178 version); `ceListPlace` is declared once, in
  `milestones.js`.
- Every module writes the shared state as `shared.X` (the last bare ones: milestones' `CUR`, `EDITING`, `CE` and
  `WT`, ask's `WT` and the like, swept with convert_area's `to_shared`). The seams' setters are `serverSeams`,
  `fieldsSeams`, `reviewSeams` and `askSeams`; convert_area.py now writes `<area>Seams` itself.
- `main.js` calls the 152 `boot…()` functions and the start-up (piece 0151, with `HADHASH` and `HASH0` now
  `shared.X`) after `publish(page)`, in the pieces' order. `script/`, the prologue and `legacy()` are deleted, and every
  module imports what it uses from core and from the other areas (`build_dashboard_js.py imports FILE`).
- **Load order:** with area imports, esbuild runs the modules in the order the imports reach them, not today's. That is
  safe while no module reads another's value (not a function) while it loads; `build_dashboard_js.py order` and
  `test_dashboard_split` check it. One read had to change: settings' `REGTEXT` read core's `REGD` at load, now
  `D.people_register` directly (the same value).
