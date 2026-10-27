"""#363: a read-only report on the creaite repo's branches and worktrees (development only). It changes, deletes and pushes nothing.

Run, from a clone of insyncalan/creaite:
     python3 dev/tools/branch_report.py               every remote branch not merged into origin/main, as JSON lines: its last
                                                      commit, ahead/behind, commits whose patch is not in main (git cherry),
                                                      whether main already holds its whole diff, the branches that hold all its
                                                      commits, and its PRs (when gh is signed in)
     python3 dev/tools/branch_report.py --worktrees   every worktree of this clone with uncommitted changes: its branch, counts
                                                      by status and the files (a Markdown table)

Run `git fetch --prune origin` first so the remote branches are current. Judging keep or delete is left to the reader (see
dev/proposals/363/BRANCHES.md for the rules used on 27-10-2026).
"""
import json
import os
import subprocess
import sys
import tempfile


def git(*args, inp=None, env=None):
    """A git command, its output kept (never raises)."""
    return subprocess.run(["git", *args], capture_output=True, input=inp, env=env)


def out(*args):
    """A git command's output as text, stripped."""
    return git(*args).stdout.decode("utf-8", "replace").strip()


def prs():
    """{head branch: ["#n STATE", …]} from gh, or {} when gh isn't there or isn't signed in."""
    try:
        r = subprocess.run(["gh", "pr", "list", "-R", "insyncalan/creaite", "--state", "all", "--limit", "1000",
                            "--json", "number,headRefName,state"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    found = {}
    for p in json.loads(r.stdout or "[]") if r.returncode == 0 else []:
        found.setdefault(p["headRefName"], []).append(f'#{p["number"]} {p["state"]}')
    return found


def in_main(base, branch, index):
    """Whether origin/main already holds the branch's whole diff from `base` (a reverse apply against main's tree succeeds)."""
    diff = git("diff", "--binary", base, branch).stdout
    if not diff:
        return True
    env = {**os.environ, "GIT_INDEX_FILE": index}
    return git("apply", "--check", "-R", "--cached", inp=diff, env=env).returncode == 0


def branches():
    """Print one JSON line per remote branch not merged into origin/main."""
    pr = prs()
    names = [b for b in out("branch", "-r", "--no-merged", "origin/main", "--format=%(refname:short)").splitlines()
             if b.startswith("origin/") and not b.endswith("/HEAD")]
    tips = {b: out("rev-parse", b) for b in names}
    with tempfile.TemporaryDirectory() as tmp:
        index = os.path.join(tmp, "index")
        git("read-tree", "origin/main", env={**os.environ, "GIT_INDEX_FILE": index})
        for b in names:
            last = out("log", "-1", "--format=%cs|%an|%s", b).split("|", 2) + ["", ""]
            ahead, behind = out("rev-list", "--left-right", "--count", f"{b}...origin/main").split()
            base = out("merge-base", "origin/main", b)
            held = [m.split("/", 1)[1] for m in names if m != b and tips[m] != tips[b]
                    and git("merge-base", "--is-ancestor", tips[b], tips[m]).returncode == 0]
            print(json.dumps({"branch": b.split("/", 1)[1], "last": last[0], "author": last[1], "subject": last[2][:90],
                              "ahead": int(ahead), "behind": int(behind),
                              "commits_not_in_main": sum(1 for c in out("cherry", "origin/main", b).splitlines() if c.startswith("+")),
                              "change_already_in_main": in_main(base, b, index),
                              "files": len(out("diff", "--name-only", base, b).splitlines()),
                              "held_by": sorted(held), "prs": pr.get(b.split("/", 1)[1], [])}))


def worktrees():
    """Print a Markdown table of this clone's worktrees that have uncommitted changes."""
    rows = []
    for line in out("worktree", "list", "--porcelain").splitlines():
        if not line.startswith("worktree "):
            continue
        path = line[len("worktree "):]
        status = git("-C", path, "status", "--porcelain").stdout.decode("utf-8", "replace").splitlines()
        if not status:
            continue
        counts = {}
        for s in status:
            counts[s[:2].strip() or "?"] = counts.get(s[:2].strip() or "?", 0) + 1
        branch = out("-C", path, "rev-parse", "--abbrev-ref", "HEAD")
        rows.append((path, branch, counts, [s[3:] for s in status]))
    print("| Worktree | Branch | Changes | Files |\n|---|---|---|---|")
    for path, branch, counts, files in rows:
        shown = ", ".join(files[:8]) + (f" (+{len(files) - 8} more)" if len(files) > 8 else "")
        print(f"| `{path}` | `{branch}` | {', '.join(f'{k} {v}' for k, v in sorted(counts.items()))} | {shown} |")
    if not rows:
        print("| (none) | | | |")


if __name__ == "__main__":
    worktrees() if "--worktrees" in sys.argv[1:] else branches()
