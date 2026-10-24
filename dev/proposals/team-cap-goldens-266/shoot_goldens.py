#!/usr/bin/env python3
"""Before/after screenshots of the snapshot screens, for a goldens sign-off.

It reuses dev/tests/test_snapshots.py of each tree (sample vault, fixed clock and zone, locale, user agent, how each screen is
reached and when it is ready), so every picture shows exactly the screen its golden is of. Fictional sample data only.

  python3 shoot_goldens.py --before <sha|worktree> --after <sha|worktree> --out DIR [--screens a,b,c] [--widths 1400,900]
                           [--keep-trees]

A sha is checked out as a detached worktree under .claude/worktrees/ (g266-shoot-before/-after) and removed afterwards
(non-forced); a path to an existing worktree is used as it is. Re-runnable. Writes DIR/<width>/<screen>-before.png and
-after.png, plus DIR/dom/<screen>-before.html and -after.html (the normalised region, as the golden is) for diffing.
Run from the main repository (or any checkout of it); it never pushes or touches the live vault.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_SCREENS = ("activity,ask,cockpit,files,intake-review,milestones,people,projects,settings-advanced,settings-ai,"
                   "settings-essentials,settings-health,work")


def git(*a, cwd=None, check=True):
    return subprocess.run(["git", *a], cwd=cwd, check=check, capture_output=True, text=True).stdout.strip()


def worker(tree, out, side, screens, widths):
    """Runs inside the tree's own test_snapshots (imported from tree/dev/tests): one server, one Chrome, every screen."""
    sys.path.insert(0, str(Path(tree) / "dev" / "tests"))
    sys.path.insert(0, str(Path(tree) / "dev" / "tools"))
    import unittest
    import test_snapshots as ts

    class Shoot(ts.Snapshots):
        def test_every_screen_matches_its_golden(self):          # the parent's check is not wanted here
            pass

        def full_height(self, w):
            """Make the window as tall as the tallest scrolling area (up to 3200 px), so the picture shows the whole screen."""
            h = self.b.eval("(()=>{let m=document.documentElement.scrollHeight;"
                            "for(const e of document.querySelectorAll('*')){const o=getComputedStyle(e).overflowY;"
                            "if((o==='auto'||o==='scroll')&&e.scrollHeight>e.clientHeight&&e.clientHeight>300)"
                            "m=Math.max(m,e.scrollHeight+e.getBoundingClientRect().top);}return Math.round(m);})()")
            h = max(1000, min(3200, int(h or 1000)))
            self.b.resize(w, h)
            self.b.pump(0.4)

        def test_shoot(self):
            for name in screens:
                if name not in ts.SCREENS:
                    print(f"[{side}] {name}: this tree has no such screen", file=sys.stderr)
            dom = Path(out) / "dom"
            dom.mkdir(parents=True, exist_ok=True)
            for w in widths:
                (Path(out) / str(w)).mkdir(parents=True, exist_ok=True)
                for name in ts.SCREENS:        # the test's own order, all of them: some screens depend on what was opened before
                    if name not in screens:
                        if w == widths[0]:
                            self.capture(name)
                        continue
                    self.b.resize(w, 1000)       # the capture's own height; the picture is taken tall, then it goes back
                    html = self.capture(name)                    # the test's own route to the screen and its settle loop
                    if w == widths[0]:
                        (dom / f"{name}-{side}.html").write_text(html, encoding="utf-8")
                    self.b.pump(0.3)
                    self.full_height(w)
                    self.b.screenshot(Path(out) / str(w) / f"{name}-{side}.png")
                    print(f"[{side}] {w} {name}", flush=True)

    suite = unittest.TestSuite([Shoot("test_shoot")])
    res = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if res.wasSuccessful() else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before"), ap.add_argument("--after"), ap.add_argument("--out")
    ap.add_argument("--screens", default=DEFAULT_SCREENS)
    ap.add_argument("--widths", default="1400,900")
    ap.add_argument("--keep-trees", action="store_true")
    ap.add_argument("--worker", nargs=2, metavar=("TREE", "SIDE"))
    a = ap.parse_args()
    screens = [s for s in a.screens.split(",") if s]
    widths = [int(w) for w in a.widths.split(",") if w]
    if a.worker:
        sys.exit(worker(a.worker[0], a.out, a.worker[1], screens, widths))
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    top = Path(git("rev-parse", "--git-common-dir")).resolve().parent     # the main checkout, from any worktree
    made, rc = [], 0
    try:
        for side, spec in (("before", a.before), ("after", a.after)):
            if Path(spec).is_dir():
                tree = Path(spec).resolve()
            else:
                tree = top / ".claude" / "worktrees" / f"g266-shoot-{side}"
                sha = git("rev-parse", spec + "^{commit}", cwd=top)
                git("worktree", "add", "--detach", str(tree), sha, cwd=top)
                made.append(tree)
            print(f"{side}: {git('rev-parse', 'HEAD', cwd=tree)}", flush=True)
            rc |= subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", str(tree), side, "--out", str(out),
                                  "--screens", ",".join(screens), "--widths", ",".join(map(str, widths))],
                                 cwd=tree).returncode
    finally:
        if not a.keep_trees:
            for t in made:
                subprocess.run(["git", "worktree", "remove", str(t)], cwd=top)
    sys.exit(rc)


if __name__ == "__main__":
    main()
