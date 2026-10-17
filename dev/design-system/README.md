# Mocking up in creaite's own look

Read `DESIGN-SYSTEM.md` first (five minutes). The short version:

1. **Copy a snapshot, do not draw from scratch.** `pages/<screen>.html` is a static copy of the real screen (today, work, review, projects, cockpit, milestones, intake, files, people, activity, settings, help), drawn by the app's own `system/templates/dashboard/style.css`; `blank.html` is the empty app shell (rail and top bar). Copy the one nearest to your idea into `dev/mockups/`, fix the two relative paths (`../../../system/…` becomes `../../system/…`, and the same for the design-system folder), and edit the content.
2. **Use the app's classes at their real sizes.** Buttons 32 px, inputs 32 px, pills 28 px, table rows with 8 × 12 px cells. If a class is not in the snapshot, search `style.css` for it before inventing one.
3. **Colours are tokens only.** Alt+D flips a snapshot to dark; a mockup that breaks in dark is wrong.
4. **Interactivity is yours to add** with a small script at the foot of the page. Snapshots carry no app script.
5. **A genuinely new component** goes in one marked block (`/* NEW: … */`), built from tokens, and the write-up says it is new.
6. **Fictional data only.** The snapshots use the tests' sample portfolio (Example Programme, Digital Enablement).

Refresh the snapshots after a release changes how a screen looks: `python3 dev/tools/design_system_snapshots.py` (it uses the UI audit's throwaway vault and headless Chrome; it never touches your vault).

Mockups in `dev/mockups/` made before 17-10-2026 draw their own CSS (a close copy of the colours and fonts, but not the real component sizes and shapes). Treat them as ideas, not as pictures of the app; rebuild one on a snapshot before it is handed to Team Cap or Team Stark as a spec.
