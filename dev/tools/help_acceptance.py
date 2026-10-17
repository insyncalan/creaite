"""Acceptance checks for the Help rewrite (Phase A), read only, standard library only.

Run (from the repo root):
python3 dev/tools/help_acceptance.py [--help-md system/templates/help.md] [--brief dev/sprints/help-phase-a-brief.md] [--strict]

Why: a rewrite of about 60 pages is slow to review by eye. This reads system/templates/help.md and reports, per check, what passes
and what to look at: each page against its word target in the brief, the total budget, banned words, the house style (the three
parts, ### groups, "Where:", numbered steps, "Or say:"), "Settings ›" paths against settings_catalogue.py, and links that resolve.
It changes nothing. With --strict it exits 1 on any failure (a baseline of the current Help is expected to fail).
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BANNED = [r"\bcx-", r"\bBL-\d", r"/api/", r"\.json\b", r"\bstaging\b", r"system/", r"\bAlan\b", r"To decide", r"press Esc twice",
          r"\b320\b", r"\b640\b", r"high-contrast", r"\bWindows\b", r"\bCtrl\b", r"this rewrite", r"this base"]
PARTS = ["Start here", "How do I…", "Reference"]
SETTINGS_TOP = {"Essentials", "People and projects", "Advanced", "Health"}
TOLERANCE = 0.15            # a page may run this far over its target before it is flagged


def words(text):
    """The number of words in a page, with link, emphasis and table marks stripped."""
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`>|#-]+", " ", text)
    return len(re.findall(r"[\w'’]+", text))


def parse_pages(md):
    """The pages of help.md: part, title and body lines (How do I... group headings are title-less and dropped)."""
    md = re.sub(r"\A<!--.*?-->", "", md, count=1, flags=re.S)
    pages, part, cur = [], None, None
    for line in md.split("\n"):
        if re.match(r"^# ", line):
            part = line[2:].strip(); cur = None
        elif re.match(r"^## ", line):
            cur = {"part": part, "title": line[3:].strip(), "lines": [], "group": None}; pages.append(cur)
        elif line.startswith("### ") and part == "How do I…":
            cur = None; group = line[4:].strip()
            pages.append({"part": part, "title": None, "group": group, "lines": []}); cur = None
        elif cur is not None:
            if line.strip() == "---":
                cur = None          # a part's footer is not part of the last page
                continue
            cur["lines"].append(line)
    return [p for p in pages if p["title"]]


def parse_targets(brief):
    """The word target of each page from the brief's table, keyed by lower-case title."""
    t = {}
    for line in brief.split("\n"):
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 5 and c[0] in ("Start here", "How do I…", "Reference") and re.match(r"^\d+$", c[3]):
            t[re.sub(r"^→\s*|^NEW\s*", "", c[1]).strip().lower()] = int(c[3])
    return t


def slug(title):
    """The id the dashboard gives a page title."""
    return re.sub(r"[^\w]+", "-", re.sub(r"['’]", "", title.lower())).strip("-")


def check_budget(pages, targets):
    """Check 1: each page against its target and the total against the budget."""
    total = 0; rows = []; bad = 0
    for p in pages:
        n = words("\n".join(p["lines"]) + " " + p["title"]); p["n"] = n; total += n
        tg = targets.get(p["title"].lower())
        if tg and n > tg * (1 + TOLERANCE):
            bad += 1; rows.append(f"- {p['part']} › {p['title']}: {n} words, target {tg} (+{n - tg})")
    budget = 14791
    rows.insert(0, f"- {len(pages)} pages, {total} words; budget {budget}" + ("" if total <= budget else f" (over by {total - budget})"))
    if total > budget: bad += 1
    missing = [t for t in targets if t not in {p['title'].lower() for p in pages}]
    if missing:
        more = " …" if len(missing) > 12 else ""
        rows.append(f"- not yet present ({len(missing)}): " + "; ".join(sorted(missing)[:12]) + more)
    return rows, bad


def check_banned(pages):
    """Check 2: banned words in reader text ("Or say:" lines and code spans may hold phrases, so look outside backticks)."""
    rows = []; bad = 0
    for p in pages:
        for line in p["lines"]:
            plain = re.sub(r"``[^`]*``|`[^`]*`", "", line)
            for pat in BANNED:
                if re.search(pat, plain):
                    bad += 1; rows.append(f"- {p['title']}: /{pat}/ in “{line.strip()[:90]}”")
    return rows, bad


def check_style(pages, md):
    """Check 3: the three parts, and Where:, numbered steps and Or say: on every How do I... page."""
    rows = []; bad = 0
    parts_found = re.findall(r"^# (.+)$", md, flags=re.M)
    if parts_found[:3] != PARTS: bad += 1; rows.append(f"- parts are {parts_found[:3]}, expected {PARTS}")
    for p in pages:
        if p["part"] != "How do I…": continue
        body = "\n".join(p["lines"])
        for need, rx in (("Where:", r"^\s*Where:"), ("numbered steps", r"^\s*1\. "), ("Or say:", r"^\s*Or say:")):
            if not re.search(rx, body, flags=re.M): bad += 1; rows.append(f"- {p['title']}: no {need}")
        if "I'm" in body or "we " in body.lower().split(): rows.append(f"- {p['title']}: first person wording")
    return rows, bad


SETTINGS_PATH = r"Settings\s*›\s*([^\s›.,;:)]+(?: [^\s›.,;:)]+){0,3})(?:\s*›\s*([^.,;:)\n]{2,40}))?"


def settings_path_row(title, m, cat):
    """(row, is_failure) for one Settings › path match, or None when the path is fine."""
    top = next((t for t in SETTINGS_TOP if m.group(1).startswith(t)), None)
    if not top:
        return f"- {title}: “Settings › {m.group(1)}”: no such section", True
    sub = m.group(2)
    if sub and not any(w.lower() in cat for w in [sub.strip(), " ".join(sub.split()[:3])]):
        return f"- {title}: “… › {sub.strip()}” not found in settings_catalogue.py (check by hand)", False
    return None


def check_settings(pages, cat):
    """Check 4: Settings › paths against the known sections and settings_catalogue.py."""
    rows = []; bad = 0
    for p in pages:
        for m in re.finditer(SETTINGS_PATH, re.sub(r"\*\*", "", "\n".join(p["lines"]))):
            hit = settings_path_row(p["title"], m, cat)
            if hit:
                rows.append(hit[0]); bad += hit[1]
    return rows, bad


def check_links(pages):
    """Check 5: every ](#...) link resolves to a page or a part."""
    ids = {slug(p["title"]) for p in pages} | {slug(x) for x in PARTS} | {"how-do-i", "start-here", "reference"}
    rows = []; bad = 0
    for p in pages:
        for m in re.finditer(r"\]\(#([^)]+)\)", "\n".join(p["lines"])):
            if m.group(1) not in ids: bad += 1; rows.append(f"- {p['title']}: link #{m.group(1)} does not resolve")
    return rows, bad


def check_unique(pages):
    """Check 6: page ids are unique (the dashboard prefixes ids with the part, so one title in two parts is fine)."""
    rows = []; seen = {}; bad = 0
    for p in pages:
        s = (p["part"], slug(p["title"]))
        if s in seen: bad += 1; rows.append(f"- duplicate page id in {s[0]}: {s[1]}")
        seen[s] = 1
    return rows, bad


def section(out, name, result):
    """Add one check's heading and rows to the report; returns 1 if it failed, else 0."""
    rows, bad = result
    out.append(f"\n## {name}: {'PASS' if not bad else 'FAIL, ' + str(bad)}")
    out.extend(rows[:40])
    if len(rows) > 40: out.append(f"- … and {len(rows) - 40} more")
    return 1 if bad else 0


def main():
    """Read help.md and the brief, run the six checks, print the report; with --strict exit 1 on any failure."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--help-md", default=str(ROOT / "system/templates/help.md"))
    ap.add_argument("--brief", default=str(ROOT / "dev/sprints/help-phase-a-brief.md"))
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    md = Path(a.help_md).read_text(encoding="utf-8")
    pages = parse_pages(md)
    targets = parse_targets(Path(a.brief).read_text(encoding="utf-8")) if Path(a.brief).exists() else {}
    catalogue = (ROOT / "system/scripts/settings_catalogue.py")
    cat = catalogue.read_text(encoding="utf-8").lower() if catalogue.exists() else ""
    out = []
    fails = section(out, "Word budget", check_budget(pages, targets))
    fails += section(out, "Banned words and promises", check_banned(pages))
    fails += section(out, "House style (How do I… pages: Where:, numbered steps, Or say:)", check_style(pages, md))
    fails += section(out, "Settings paths", check_settings(pages, cat))
    fails += section(out, "Links inside Help", check_links(pages))
    fails += section(out, "Unique page ids", check_unique(pages))
    print("# Help acceptance report\n\n" + f"Source: {a.help_md}")
    print("\n".join(out))
    print(f"\n{'ALL CHECKS PASS' if not fails else str(fails) + ' check(s) need attention'}")
    sys.exit(1 if (a.strict and fails) else 0)


if __name__ == "__main__":
    main()
