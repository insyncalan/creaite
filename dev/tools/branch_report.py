"""#363: a read-only report on the creaite repo's branches and worktrees (development only). It changes, deletes and pushes nothing.

Run, from a clone of insyncalan/creaite:
     python3 dev/tools/branch_report.py               every remote branch not merged into origin/main, as JSON lines: its last
                                                      commit, ahead/behind, commits whose patch is not in main (git cherry),
                                                      whether main already holds its whole diff, the branches that hold all its
                                                      commits or share its tip, its PRs (when gh is signed in) and a suggestion
     python3 dev/tools/branch_report.py --markdown    the same as the Markdown table in dev/proposals/363/BRANCHES.md
     python3 dev/tools/branch_report.py --worktree-list FILE …   also count as checked out every branch in FILE, the output of
                                                      `git worktree list --porcelain` saved on another machine's clone (a
                                                      worktree is per clone: this clone can't see another machine's)
     python3 dev/tools/branch_report.py --worktrees   every worktree of this clone with uncommitted changes, plus any that is
                                                      locked or prunable (its folder is gone): a Markdown table

Run `git fetch --prune origin` first so the remote branches are current. Every branch not merged into origin/main is reported,
remote (origin/*) and local, and `where` says which: "remote only", "local only" or "local and remote" (a branch on both is judged
by its origin tip). A branch checked out in any worktree of this clone is never "delete", nor is a local branch with commits that
aren't on origin (Stark's re-check). `git cherry` compares single-parent commits; a merge commit on a branch is never counted
as "in main" by it, so a branch with a merge commit of its own is "in main" only by the whole-diff check (Stark's re-check).
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

ACTIVE = ("v269", "v2610", "v27", "team-", "ai-")     # live release lines and team branches (27-10-2026)
RECENT_DAYS = 3


def git(*args, inp=None, env=None):
    """A git command, its output kept (never raises). Never takes optional locks, so a report never blocks real work."""
    return subprocess.run(["git", "--no-optional-locks", *args], capture_output=True, input=inp, env=env)


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
    diff = git("diff", "--binary", base, branch, "--").stdout
    if not diff:
        return True
    env = {**os.environ, "GIT_INDEX_FILE": index}
    return git("apply", "--check", "-R", "--cached", inp=diff, env=env).returncode == 0


def branch_refs():
    """{short name: (ref to judge it by, where)} for every remote and local branch not merged into origin/main (never main): the
    origin ref when there is one."""
    remote = {b.split("/", 1)[1] for b in out("branch", "-r", "--no-merged", "origin/main", "--format=%(refname:short)").splitlines()
              if b.startswith("origin/") and not b.endswith("/HEAD")}
    local = {b for b in out("branch", "--no-merged", "origin/main", "--format=%(refname:short)").splitlines() if b and b != "main"}
    where = {**{b: "local only" for b in local}, **{b: "remote only" for b in remote}, **{b: "local and remote" for b in remote & local}}
    return {b: ("origin/" + b if b in remote else b, w) for b, w in where.items()}


def _local_ahead(short, where):
    """How many commits the local branch has that its origin branch hasn't (0 unless it is on both)."""
    if where != "local and remote":
        return 0
    return int(out("rev-list", "--count", f"origin/{short}..refs/heads/{short}", "--") or 0)


def checked_out(lists=()):
    """{branch name: [worktree path, …]} for every worktree of this clone with a branch checked out, and of each saved
    `git worktree list --porcelain` in `lists` (another machine's clone; its paths are given as "<file>: <path>")."""
    found = {}
    for label, text in [(None, None)] + [(f, open(f, encoding="utf-8").read()) for f in lists]:
        for w in worktree_entries(text):
            if w["branch"]:
                found.setdefault(w["branch"], []).append(w["path"] if label is None else f"{label}: {w['path']}")
    return found


def facts(pr=None, lists=()):
    """One dict per branch not merged into origin/main, remote or local: what git says about it (no judgement). `lists`: saved
    worktree lists from other clones (checked_out)."""
    pr = prs() if pr is None else pr
    refs, held = branch_refs(), checked_out(lists)
    names = [ref for ref, _ in refs.values()]
    tips = {b: out("rev-parse", b) for b in names}
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        index = os.path.join(tmp, "index")
        git("read-tree", "origin/main", env={**os.environ, "GIT_INDEX_FILE": index})
        for b in names:
            last = out("log", "-1", "--format=%cs|%an|%s", b, "--").split("|", 2) + ["", ""]
            ahead, behind = out("rev-list", "--left-right", "--count", f"{b}...origin/main", "--").split()
            base = out("merge-base", "origin/main", b)
            short = b.split("/", 1)[1] if b.startswith("origin/") else b
            where = refs[short][1]
            rows.append({"branch": short, "where": where, "checked_out": held.get(short, []),
                         "local_ahead": _local_ahead(short, where), "last": last[0], "author": last[1], "subject": last[2][:90],
                         "ahead": int(ahead), "behind": int(behind),
                         "commits_not_in_main": sum(1 for c in out("cherry", "origin/main", b).splitlines() if c.startswith("+")),
                         "merges": len(out("rev-list", "--merges", f"origin/main..{b}", "--").splitlines()),
                         "change_already_in_main": in_main(base, b, index),
                         "files": len(out("diff", "--name-only", base, b, "--").splitlines()),
                         "held_by": sorted(_short(m) for m in names if m != b and tips[m] != tips[b]
                                           and git("merge-base", "--is-ancestor", tips[b], tips[m]).returncode == 0),
                         "same_tip_as": sorted(_short(m) for m in names if m != b and tips[m] == tips[b]),
                         "prs": pr.get(short, [])})
    return rows


def _short(ref):
    """The branch name of a ref as facts() reads them (origin/x or a local x)."""
    return ref.split("/", 1)[1] if ref.startswith("origin/") else ref


def _own_class(r, today):
    """(class, why) from the branch alone: checked out or with local commits (never delete), in main, an open PR, a live line,
    recent, or the owner's call."""
    if r.get("checked_out"):
        return "keep", "checked out in " + ", ".join(r["checked_out"])
    if r.get("local_ahead"):
        return "keep", f"the local branch has {r['local_ahead']} commit(s) not on origin"
    if r["change_already_in_main"]:
        return "delete", "its change is already in main (main holds the whole diff)"
    if r["commits_not_in_main"] == 0 and not r.get("merges"):         # git cherry can't see a merge commit's own content
        return "delete", "its change is already in main (every commit's patch is there)"
    if any("OPEN" in p for p in r["prs"]):
        return "keep", "open PR " + ", ".join(r["prs"])
    if r["branch"].startswith(ACTIVE):
        return "keep", "a live release line or team branch"
    age = (today - datetime.date.fromisoformat(r["last"])).days if r["last"] else 9999
    if age <= RECENT_DAYS:
        return "keep-recent", f"changed {age} day(s) ago"
    return "owner decides", f"{r['commits_not_in_main']} commit(s) not in main, last {dmy(r['last'])}, no newer branch holds them"


def classify(rows, today=None):
    """Add `suggest` and `why` to each row: delete, delete if kept, keep, owner decides (the rules in BRANCHES.md)."""
    today = today or datetime.date.today()
    own = {r["branch"]: _own_class(r, today) for r in rows}
    for r in rows:
        cls, why = own[r["branch"]]
        if cls in ("owner decides", "keep-recent") and r["held_by"]:
            firm = [b for b in r["held_by"] if own.get(b, ("",))[0] == "keep"]
            if firm:
                cls, why = "delete", "every commit is also in " + ", ".join(firm[:3]) + ", which is kept"
            else:
                cls, why = "delete if kept", ("every commit is also in " + ", ".join(r["held_by"][:3])
                                              + ": delete this one only if that one is kept")
        cls = "keep" if cls == "keep-recent" else cls
        if r["same_tip_as"]:
            why += "; the same commit as " + ", ".join(r["same_tip_as"]) + " (keep one)"
        r.update(suggest=cls, why=why)
    return rows


def dmy(iso):
    """YYYY-MM-DD as DD-MM-YYYY (the format people read), "" for none."""
    return "-".join(reversed(iso.split("-"))) if iso else ""


def cell(text):
    """Text safe inside a Markdown table cell."""
    return str(text).replace("|", "\\|").replace("\n", " ")


ORDER = {"delete": 0, "delete if kept": 1, "owner decides": 2, "keep": 3}


def markdown(rows):
    """The classified rows as BRANCHES.md's table (most deletable first)."""
    lines = ["| Suggest | Branch | Where | Last commit | Author | Ahead/behind main | Commits not in main | Files | PR | Why |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (ORDER[r["suggest"]], r["branch"])):
        lines.append("| " + " | ".join(cell(x) for x in (
            r["suggest"], f"`{r['branch']}`", r.get("where", ""), dmy(r["last"]), r["author"], f"{r['ahead']}/{r['behind']}",
            r["commits_not_in_main"], r["files"], ", ".join(r["prs"]), r["why"])) + " |")
    return "\n".join(lines)


WT_FLAGS = {"locked": "locked", "prunable": "its folder is gone"}


def _entry_line(cur, line):
    """Fill worktree entry `cur` from one porcelain line (branch, detached, locked, prunable)."""
    if line.startswith("branch "):
        cur["branch"] = re.sub(r"^refs/heads/", "", line[len("branch "):])
    elif line == "detached":
        cur["detached"] = True
    else:
        key = line.split(" ", 1)[0]
        if key in WT_FLAGS:
            cur[key] = line[len(key) + 1:] or WT_FLAGS[key]


def worktree_entries(text=None):
    """[{path, branch, detached, locked, prunable}] from `git worktree list --porcelain` (this clone's, or `text` saved elsewhere)."""
    entries, cur = [], None
    for line in (out("worktree", "list", "--porcelain") if text is None else text).splitlines() + [""]:
        if line.startswith("worktree "):
            cur = {"path": line[len("worktree "):], "branch": "", "detached": False, "locked": None, "prunable": None}
        elif cur is not None and line:
            _entry_line(cur, line)
        elif cur is not None:
            entries.append(cur)
            cur = None
    return entries


def _worktree_state(w):
    """"detached", "locked (why)" and "prunable (why)", as they apply."""
    parts = ["detached"] if w["detached"] else []
    parts += [f"{k} ({w[k]})" for k in ("locked", "prunable") if w[k]]
    return ", ".join(parts)


def _worktree_row(w):
    """A table row for worktree entry `w`, or None when it is clean, unlocked and still there."""
    state = _worktree_state(w)
    status = [] if w["prunable"] else git("-C", w["path"], "status", "--porcelain").stdout.decode("utf-8", "replace").splitlines()
    if not status and not w["locked"] and not w["prunable"]:
        return None
    counts = {}
    for s in status:
        counts[s[:2].strip() or "?"] = counts.get(s[:2].strip() or "?", 0) + 1
    files = [s[3:] for s in status]
    listed = ", ".join(files[:8]) + (f" (+{len(files) - 8} more)" if len(files) > 8 else "")
    return "| " + " | ".join(cell(x) for x in (f"`{w['path']}`", f"`{w['branch'] or '(detached)'}`", state,
                                               ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), listed)) + " |"


def worktrees():
    """Print a Markdown table of this clone's worktrees that have uncommitted changes, or are locked or prunable."""
    rows = [r for r in (_worktree_row(w) for w in worktree_entries()) if r]
    print("| Worktree | Branch | State | Changes | Files |\n|---|---|---|---|---|")
    print("\n".join(rows) if rows else "| (none) | | | | |")


def _lists(argv):
    """The FILE after each --worktree-list."""
    return [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "--worktree-list"]


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--worktrees" in args:
        worktrees()
    elif "--markdown" in args:
        print(markdown(classify(facts(lists=_lists(args)))))
    else:
        for row in classify(facts(lists=_lists(args))):
            print(json.dumps(row))
