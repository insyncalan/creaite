# Mocking up in creaite's own look

**Open `index.html` first**: it is the design system and the guide to building a page (seven steps, ten rules, the foundations, every component with its states, nine page patterns, the keys, the words, the checklist). `DESIGN-SYSTEM.md` is the plain-text version of the numbers. Five minutes to read the first two sections. The short version:

1. **Copy a snapshot, do not draw from scratch.** `pages/<screen>.html` is a static copy of the real screen (today, work, review, projects, cockpit, milestones, intake, files, people, activity, settings, help), drawn by `style.snapshot.css`, a copy of the app's own stylesheet; `blank.html` is the empty app shell (rail and top bar). Copy the one nearest to your idea into `dev/mockups/` and change its stylesheet link from `../style.snapshot.css` to `../design-system/style.snapshot.css`, then edit the content. The stylesheet is a copy of the app's own, taken at the same moment as the snapshots; each page's first comment says which commit that was, and `SNAPSHOT.json` has the same.
2. **Use the app's classes at their real sizes.** Buttons 32 px, inputs 32 px, pills 28 px, table rows with 8 × 12 px cells. If a class is not in the snapshot, search `style.css` for it before inventing one.
3. **Colours are tokens only.** Alt+D flips a snapshot to dark; a mockup that breaks in dark is wrong.
4. **Interactivity is yours to add** with a small script at the foot of the page. Snapshots carry no app script.
5. **A genuinely new component** goes in one marked block (`/* NEW: … */`), built from tokens, and the write-up says it is new.
6. **Fictional data only.** The snapshots use the tests' sample portfolio (Example Programme, Digital Enablement).

**Which version?** Snapshots are taken from the release line the next release is built on, not from an older line; the version is on the first lines of `DESIGN-SYSTEM.md`. Refresh them when that line changes how a screen looks (the v2.2.0 cut, #198 and #193 landing): `python3 dev/tools/design_system_snapshots.py --repo <checkout of that line> --label <its branch>` (it uses the UI audit's throwaway vault and headless Chrome; it never touches your vault).

Mockups in `dev/mockups/` made before 17-10-2026 draw their own CSS (a close copy of the colours and fonts, but not the real component sizes and shapes). Treat them as ideas, not as pictures of the app; rebuild one on a snapshot before it is handed to Team Cap or Team Stark as a spec.

## How this folder is made

`index.html` is generated, never edited by hand: `python3 dev/tools/design_system_guide.py`. Its inputs are made by, in order (each takes `DS_REPO=<checkout of the release line>`): `dev/tools/design_system_snapshots.py` (pages, shots, `style.snapshot.css`, `SNAPSHOT.json`), then `dev/tools/design_system_components/capture_live.py` (menus, dialogs, peek, toast, icons, page skeletons), `capture_states.py` (forced hover, focus, active and disabled states), `capture_composites.py` (composite pieces) and `specimens.py` (real markup of each component).

## Committing pictures

Regenerated screenshots and component captures stay in git history for good, so commit them **only at a release milestone** (the v2.2.0 cut, #198 and #193 landing, and releases after), never on every edit. The scripts regenerate every picture, and only the pictures `index.html` links are kept (the rest are removed). The specimens, scripts and `index.html` are what matter day to day.
