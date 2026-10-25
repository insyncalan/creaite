# Goldens sign-off pictures for the 2.6.6 candidate

Before/after pictures of the 14 screens that `dev/tests/test_snapshots.py` reports red on `origin/v266-release`, at 1400 and 900 px wide, plus `CHANGES.md` (one line per screen).

- before: `2f2acdc21fdbed3fabef168f829d97299453179d` (Merge branch 'v265-358-build' into v266-line, before #341)
- after: `ab39f6c1759e7257b5609fb9dfe9bcb72d8d4a6b` (tip of `origin/v266-release`: the goldens re-recorded once, after the origin/main merge and the People fit). The set Alan approved ('2.6.6 screens - all approved') was shot on `cb1d99b5c1a4a7ef8804748cb5987ce87c64d3bb`; the pictures here are the re-shoot on ab39f6c1, and 'Re-recorded on ab39f6c1' in CHANGES.md lists every difference between the two sets (earlier set: 330d1171 on `v266-line`)

The screen list is the red list of `python3 dev/tests/test_snapshots.py` on cb1d99b5 (14 screens; `today` is new beside the earlier 13); on ab39f6c1 that test is green. Re-run (from any checkout of the repository; give two commits or two existing worktrees; a fix is just a new `--after`; about 8 minutes when the machine is busy):

    python3 dev/proposals/team-cap-goldens-266/shoot_goldens.py --before 2f2acdc2 --after origin/v266-release \
        --out dev/proposals/team-cap-goldens-266 \
        --screens today,work,intake-review,files,activity,projects,cockpit,milestones,people,settings-essentials,settings-advanced,settings-ai,settings-health,ask

It checks each commit out as a temporary detached worktree, runs that commit's own `test_snapshots.py` set-up (sample vault, fixed clock, zone, locale, user agent, the same route to each screen and the same settle rule, all screens in the test's own order), and saves `<out>/<width>/<screen>-before.png` and `-after.png`. Pictures are taken as tall as the screen's scrolling area (to 3200 px). `--screens a,b` and `--widths 1400,900` narrow it. It also writes the normalised HTML of each screen to `<out>/dom/` (the same text a golden holds; not committed here) for diffing. Fictional sample data only; headless Chrome is stopped by the test harness.
