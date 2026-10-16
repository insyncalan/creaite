"""Acceptance checks for the Help rewrite (Phase A), read only, standard library only.

Run (from the repo root): python3 dev/tools/help_acceptance.py [--help-md system/templates/help.md] [--brief dev/sprints/help-phase-a-brief.md] [--strict]

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
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`>|#-]+", " ", text)
    return len(re.findall(r"[\w'’]+", text))


def parse_pages(md):
    md = re.sub(r"\A<!--.*?-->", "", md, count=1, flags=re.S)
    pages, part, cur = [], None, None
    for line in md.split("\n"):
        if re.match(r"^# ", line):
            part = line[2:].strip(); cur = None
        elif re.match(r"^## ", line):
            cur = {"part": part, "title": line[3:].strip(), "lines": [], "group": None}; pages.append(cur)
        elif line.startswith("### ") and part == "How do I…":
            cur = None; group = line[4:].strip()
            for p in pages[::-1]:
                break
            pages.append({"part": part, "title": None, "group": group, "lines": []}); cur = None
        elif cur is not None:
            if line.strip() == "---":
                cur = None          # a part's footer is not part of the last page
                continue
            cur["lines"].append(line)
    return [p for p in pages if p["title"]]


def parse_targets(brief):
    t = {}
    for line in brief.split("\n"):
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 5 and c[0] in ("Start here", "How do I…", "Reference") and re.match(r"^\d+$", c[3]):
            t[re.sub(r"^→\s*|^NEW\s*", "", c[1]).strip().lower()] = int(c[3])
    return t


def slug(title):
    return re.sub(r"[^\w]+", "-", re.sub(r"['’]", "", title.lower())).strip("-")


def main():
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
    fails = 0
    out = []

    def section(name, rows, bad):
        nonlocal fails
        out.append(f"\n## {name}: {'PASS' if not bad else 'FAIL, ' + str(bad)}")
        out.extend(rows[:40])
        if len(rows) > 40: out.append(f"- … and {len(rows) - 40} more")
        fails += 1 if bad else 0

    # 1 word budget
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
    if missing: rows.append(f"- not yet present ({len(missing)}): " + "; ".join(sorted(missing)[:12]) + (" …" if len(missing) > 12 else ""))
    section("Word budget", rows, bad)

    # 2 banned words (reader text; "Or say:" lines and code spans are allowed to hold phrases, so check outside backticks)
    rows = []; bad = 0
    for p in pages:
        for i, line in enumerate(p["lines"]):
            plain = re.sub(r"``[^`]*``|`[^`]*`", "", line)
            for pat in BANNED:
                if re.search(pat, plain):
                    bad += 1; rows.append(f"- {p['title']}: /{pat}/ in “{line.strip()[:90]}”")
    section("Banned words and promises", rows, bad)

    # 3 house style
    rows = []; bad = 0
    parts_found = re.findall(r"^# (.+)$", md, flags=re.M)
    if parts_found[:3] != PARTS: bad += 1; rows.append(f"- parts are {parts_found[:3]}, expected {PARTS}")
    for p in pages:
        if p["part"] != "How do I…": continue
        body = "\n".join(p["lines"])
        for need, rx in (("Where:", r"^\s*Where:"), ("numbered steps", r"^\s*1\. "), ("Or say:", r"^\s*Or say:")):
            if not re.search(rx, body, flags=re.M): bad += 1; rows.append(f"- {p['title']}: no {need}")
        if "I'm" in body or "we " in body.lower().split(): rows.append(f"- {p['title']}: first person wording")
    section("House style (How do I… pages: Where:, numbered steps, Or say:)", rows, bad)

    # 4 settings paths
    rows = []; bad = 0
    for p in pages:
        for m in re.finditer(r"Settings\s*›\s*([^\s›.,;:)]+(?: [^\s›.,;:)]+){0,3})(?:\s*›\s*([^.,;:)\n]{2,40}))?", "\n".join(p["lines"])):
            top = next((t for t in SETTINGS_TOP if m.group(1).startswith(t)), None)
            if not top: bad += 1; rows.append(f"- {p['title']}: “Settings › {m.group(1)}”: no such section")
            elif m.group(2) and m.group(2).strip().lower() not in cat: rows.append(f"- {p['title']}: “… › {m.group(2).strip()}” not found in settings_catalogue.py (check by hand)")
    section("Settings paths", rows, bad)

    # 5 links
    ids = {slug(p["title"]) for p in pages} | {slug(x) for x in PARTS} | {"how-do-i", "start-here", "reference"}
    rows = []; bad = 0
    for p in pages:
        for m in re.finditer(r"\]\(#([^)]+)\)", "\n".join(p["lines"])):
            if m.group(1) not in ids: bad += 1; rows.append(f"- {p['title']}: link #{m.group(1)} does not resolve")
    section("Links inside Help", rows, bad)

    # 6 page ids unique
    rows = []; seen = {}; bad = 0
    for p in pages:
        s = (p["part"], slug(p["title"]))          # the dashboard prefixes ids with the part, so the same title in two parts is fine
        if s in seen: bad += 1; rows.append(f"- duplicate page id in {s[0]}: {s[1]}")
        seen[s] = 1
    section("Unique page ids", rows, bad)

    print("# Help acceptance report\n\n" + f"Source: {a.help_md}")
    print("\n".join(out))
    print(f"\n{'ALL CHECKS PASS' if not fails else str(fails) + ' check(s) need attention'}")
    sys.exit(1 if (a.strict and fails) else 0)


if __name__ == "__main__":
    main()
