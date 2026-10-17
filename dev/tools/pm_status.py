#!/usr/bin/env python3
"""Product Manager status (read only): branch and unpushed commits, board items
waiting on a mockup or brief (gh, read only), mockups and briefs newer than the
last release, and the no-real-names test. Changes nothing."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOARD = "insyncalan/creaite-plan"


def run(*cmd):
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:  # missing tool, timeout
        return 1, str(e)


def section(title):
    print(f"\n== {title} ==")


def main():
    section("Branch")
    _, branch = run("git", "branch", "--show-current")
    print(branch or "(detached)")
    _, dirty = run("git", "status", "--short")
    print("uncommitted:", dirty if dirty else "none")
    rc, ahead = run("git", "log", "--oneline", "@{u}..HEAD")
    print("unpushed commits:" if rc == 0 else "no upstream set; recent commits:")
    print(ahead if rc == 0 and ahead else "  none" if rc == 0 else run("git", "log", "--oneline", "-5")[1])

    section("Board items waiting on a mockup or brief (gh read only)")
    rc, out = run("gh", "issue", "list", "--repo", BOARD, "--state", "open",
                  "--limit", "200", "--json", "number,title,body,labels")
    if rc != 0:
        print("gh unavailable:", out.splitlines()[0] if out else "no output")
    else:
        # The board has no mockup, brief or design label (labels: bug,
        # enhancement, sonnet, opus, review, UI). Pick by the UI label, or by
        # a mockup, brief, Needs decision or Idea mention in the title or body.
        # The project's State field is not read (gh project is not allowed).
        words = ("mockup", "brief", "needs decision", "idea")
        found = False
        for i in json.loads(out):
            names = [l["name"].lower() for l in i["labels"]]
            text = (i["title"] + " " + (i.get("body") or "")).lower()
            hit = [w for w in words if w in text] + (["UI label"] if "ui" in names else [])
            if hit:
                print(f"  #{i['number']} {i['title']}  [{', '.join(hit)}]")
                found = True
        if not found:
            print("  none found")

    section("Mockups and briefs newer than the last release")
    _, tag = run("git", "describe", "--tags", "--abbrev=0")
    since = tag if tag and " " not in tag else None
    print("last release tag:", since or "none found (listing the last 10 days)")
    args = ["git", "log", "--name-only", "--format="]
    args += [f"{since}..HEAD"] if since else ["--since=10 days ago"]
    args += ["--", "dev/mockups", "dev/sprints"]
    _, files = run(*args)
    for f in sorted(set(files.splitlines())):
        print(" ", f)

    section("No real names")
    rc, out = run(sys.executable, "dev/tests/test_no_real_names.py")
    print("PASS" if rc == 0 else "FAIL\n" + out[-800:])


if __name__ == "__main__":
    main()
