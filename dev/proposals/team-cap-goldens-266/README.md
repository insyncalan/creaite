# Goldens sign-off pictures for the 2.6.6 candidate

Before/after pictures of the 13 screens that `dev/tests/test_snapshots.py` reports red on `v266-line`, at 1400 and 900 px wide, plus `CHANGES.md` (one line per screen).

- before: `2f2acdc21fdbed3fabef168f829d97299453179d` (Merge branch 'v265-358-build' into v266-line, before #341)
- after: `330d11719b53fa19b5262129beb8129fb12458f4` (tip of `origin/v266-line` when made)

Re-run (from any checkout of the repository; give two commits or two existing worktrees; Stark's fix is just a new `--after`):

    python3 dev/proposals/team-cap-goldens-266/shoot_goldens.py --before 2f2acdc2 --after origin/v266-line \
        --out dev/proposals/team-cap-goldens-266

It checks each commit out as a temporary detached worktree, runs that commit's own `test_snapshots.py` set-up (sample vault, fixed clock, zone, locale, user agent, the same route to each screen and the same settle rule, all screens in the test's own order), and saves `<out>/<width>/<screen>-before.png` and `-after.png`. Pictures are taken as tall as the screen's scrolling area (to 3200 px). `--screens a,b` and `--widths 1400,900` narrow it. It also writes the normalised HTML of each screen to `<out>/dom/` (the same text a golden holds; not committed here) for diffing. Fictional sample data only; headless Chrome is stopped by the test harness.
