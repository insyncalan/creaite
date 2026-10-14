#!/usr/bin/env python3
"""Phase C, part 2: the release plans onto the board, after board_import.py's import.

Reads dev/tools/board-update.json and brings the board on `insyncalan/creaite-plan` in line with it:
- **new issues:** each release's plan steps (and the items the backlog didn't hold), each with a Done-when checklist,
  added to the project with its fields set;
- **sub-issues:** each new issue under its parent (an imported BL item or a release issue made here), so a parent's
  progress is its sub-issues';
- **blocked by:** the stacked releases and the phase-2 parts, as GitHub's "blocked by" links;
- **field updates:** corrections to imported items (Team, Priority, State);
- **appends:** a block added once to an imported issue's text (the mockup links).

Refs in the spec are `BL-NNN` (an imported issue, matched by its "BL-NNN " title) or `key:<key>` (an issue made here,
matched by the `<!-- board-update key=<key> -->` line at the top of its text).

Commands (run from the repository root):

    python3 dev/tools/board_update.py apply --dry-run     # prints every write; reads the board to skip what exists
    python3 dev/tools/board_update.py apply               # the real thing
    python3 dev/tools/board_update.py apply --only key:v194-fast-save,key:rel-194   # a trial on a few new issues

Like board_import.py: standard library only, every GitHub call through `gh` (signed in with the `project` scope), a pause
after every write, a wait and retry when GitHub says a request came too quickly, and safe to stop and run again: an issue
whose key exists, a value already set, a sub-issue already under its parent, a link already there and an append whose
marker is already in the text are all skipped. It never closes or deletes anything, never moves a sub-issue that already
has a different parent (it reports it instead), and edits an existing issue's text only to add an append block.
"""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from board_import import GH, PROJECT_TITLE, REPO, ROOT, find_project, issue_by_bl, list_issues, project_items  # noqa: E402

SPEC = ROOT / "dev" / "tools" / "board-update.json"
KEY_RE = re.compile(r"<!-- board-update key=([\w.-]+) -->")
FIELDS = ("Priority", "State", "Release", "Size", "Team")

Q_RELATIONS = """query($ids: [ID!]!) { nodes(ids: $ids) { ... on Issue { id number parent { id number }
  blockedBy(first: 50) { nodes { id } } } } }"""


def make_body(it):
    lines = ["<!-- board-update key=%s -->" % it["key"], "", it["summary"], ""]
    if it.get("plan"):
        lines += ["**Plan:** " + it["plan"], ""]
    lines += ["## Done when", ""] + ["- [ ] " + d for d in it["done_when"]]
    return "\n".join(lines) + "\n"


def relations(gh, ids):
    out = {}
    real = [i for i in ids if not i.startswith("<")]
    for n in range(0, len(real), 50):
        chunk = real[n:n + 50]
        cmd = ["gh", "api", "graphql", "-f", "query=" + " ".join(Q_RELATIONS.split())]
        for i in chunk:
            cmd += ["-f", "ids[]=" + i]
        for node in json.loads(gh.read(cmd))["data"]["nodes"]:
            if node:
                out[node["id"]] = {"parent": (node.get("parent") or {}).get("id"),
                                   "blocked_by": {b["id"] for b in node["blockedBy"]["nodes"]}}
    return out


def cmd_apply(args):
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    gh = GH(args.dry_run, args.pause)
    only = set(args.only.split(",")) if args.only else None
    print("%s %s onto %s and the project '%s'" % ("DRY RUN:" if args.dry_run else "Applying", SPEC.relative_to(ROOT), REPO, PROJECT_TITLE))

    _, proj = find_project(gh)
    if not proj:
        raise SystemExit("no project '%s': run board_import.py apply first" % PROJECT_TITLE)
    fields = {f["name"]: f for f in proj["fields"]["nodes"] if f}
    issues = list_issues(gh, with_body=True)
    by_bl = issue_by_bl(issues)
    by_key = {}
    for i in issues:
        m = KEY_RE.search(i.get("body") or "")
        if m:
            by_key.setdefault(m.group(1), i)

    def ref(r):
        if r.startswith("key:"):
            k = r[4:]
            return by_key.get(k) or {"id": "<ISSUE_ID:%s>" % r, "url": "<URL:%s>" % r, "number": "<%s>" % r, "body": ""}
        if r not in by_bl:
            raise SystemExit("%s is not on the board: run board_import.py apply first" % r)
        return by_bl[r]

    def wanted(r):
        return not only or r in only

    # Check the spec: every ref resolves to an imported item or a new issue, and every value is an option on the board.
    keys = {"key:" + it["key"] for it in spec["new_issues"]}
    for r in [it["parent"] for it in spec["new_issues"] if it["parent"]] + [u["ref"] for u in spec["field_updates"]] + \
             [b["ref"] for b in spec["blocked_by"]] + [x for b in spec["blocked_by"] for x in b["by"]] + [a["ref"] for a in spec["appends"]]:
        if r.startswith("key:") and r not in keys:
            raise SystemExit("spec: unknown ref " + r)
        if not r.startswith("key:"):
            ref(r)
    for it in spec["new_issues"]:
        for fname in FIELDS:
            value = it.get(fname.lower())
            opts = {o["name"] for o in (fields.get(fname) or {}).get("options") or []}
            if value and value not in opts:
                raise SystemExit("spec: %s has %s=%s, not an option on the board" % (it["key"], fname, value))

    # 1. New issues
    print("new issues")
    tmp = Path(tempfile.mkdtemp(prefix="board-update-"))
    for it in spec["new_issues"]:
        r = "key:" + it["key"]
        if not wanted(r):
            continue
        if it["key"] in by_key:
            print("  exists: #%d %s" % (by_key[it["key"]]["number"], it["title"]))
            continue
        body = tmp / ("%s.md" % it["key"])
        body.write_text(make_body(it), encoding="utf-8")
        out = gh.write(["gh", "issue", "create", "-R", REPO, "--title", it["title"], "--body-file", str(body),
                        "--milestone", it["release"]], placeholder="")
        if out:
            url = out.strip().splitlines()[-1]
            by_key[it["key"]] = json.loads(gh.read(["gh", "issue", "view", url, "--json", "id,number,title,url,body"]))

    # 2. Project items and field values (the new issues, then the field updates)
    print("project items and fields")
    in_project = project_items(gh, proj["id"])

    def set_value(label, issue, fname, value):
        entry = in_project.get(issue["url"])
        if entry:
            item_id, current = entry["item_id"], entry["values"]
        else:
            res = gh.graphql("""mutation($p: ID!, $c: ID!) { addProjectV2ItemById(input: {projectId: $p, contentId: $c}) { item { id } } }""",
                             write=True, placeholder={}, p=proj["id"], c=issue["id"])
            item_id = (((res or {}).get("data") or {}).get("addProjectV2ItemById") or {}).get("item", {}).get("id", "<ITEM_ID:%s>" % label)
            current = {}
            in_project[issue["url"]] = {"item_id": item_id, "values": current}
        if not value or current.get(fname) == value:
            return
        f = fields[fname]
        oid = next(o["id"] for o in f["options"] if o["name"] == value)
        gh.graphql("""mutation($p: ID!, $i: ID!, $f: ID!, $o: String!) { updateProjectV2ItemFieldValue(input: {projectId: $p,
                   itemId: $i, fieldId: $f, value: {singleSelectOptionId: $o}}) { projectV2Item { id } } }""",
                   write=True, p=proj["id"], i=item_id, f=f["id"], o=oid)
        current[fname] = value

    for it in spec["new_issues"]:
        r = "key:" + it["key"]
        if wanted(r):
            for fname in FIELDS:
                set_value(r, ref(r), fname, it.get(fname.lower()))
    for u in spec["field_updates"]:
        if wanted(u["ref"]):
            set_value(u["ref"], ref(u["ref"]), u["field"], u["value"])

    # 3. Sub-issues and blocked-by links
    print("sub-issues and blocked-by links")
    rel = relations(gh, [i["id"] for i in list(by_key.values()) + list(by_bl.values())])
    for it in spec["new_issues"]:
        r = "key:" + it["key"]
        if not it["parent"] or not wanted(r):
            continue
        child, parent = ref(r), ref(it["parent"])
        have = rel.get(child["id"], {}).get("parent")
        if have == parent["id"]:
            continue
        if have:
            print("  NOT MOVED: %s already has another parent; move it by hand if that's wrong" % it["title"])
            continue
        gh.graphql("""mutation($p: ID!, $c: ID!) { addSubIssue(input: {issueId: $p, subIssueId: $c}) { issue { id } } }""",
                   write=True, p=parent["id"], c=child["id"])
    for b in spec["blocked_by"]:
        if not wanted(b["ref"]):
            continue
        issue = ref(b["ref"])
        have = rel.get(issue["id"], {}).get("blocked_by", set())
        for by in b["by"]:
            blocker = ref(by)
            if blocker["id"] in have:
                continue
            gh.graphql("""mutation($i: ID!, $b: ID!) { addBlockedBy(input: {issueId: $i, blockingIssueId: $b}) { issue { id } } }""",
                       write=True, i=issue["id"], b=blocker["id"])

    # 4. Appends to imported issues' text
    print("appends")
    for a in spec["appends"]:
        if not wanted(a["ref"]):
            continue
        issue = ref(a["ref"])
        marker = "<!-- board-update append=%s -->" % a["marker"]
        body = issue.get("body") or ""
        if marker in body:
            print("  exists: %s %s" % (a["ref"], a["marker"]))
            continue
        path = tmp / ("%s-%s.md" % (a["ref"], a["marker"]))
        path.write_text(body.rstrip() + "\n\n" + marker + "\n" + a["text"] + "\n", encoding="utf-8")
        gh.write(["gh", "issue", "edit", str(issue["number"]), "-R", REPO, "--body-file", str(path)])

    print("%s %d writes" % ("would make" if args.dry_run else "made", gh.writes))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply", help="bring the board in line with board-update.json")
    a.add_argument("--dry-run", action="store_true", help="print every write without making it")
    a.add_argument("--only", help="comma-separated refs (BL-NNN or key:<key>) to limit the run to")
    a.add_argument("--pause", type=float, default=1.0, help="seconds to wait after each write (default 1)")
    args = p.parse_args(argv)
    return cmd_apply(args)


if __name__ == "__main__":
    sys.exit(main())
