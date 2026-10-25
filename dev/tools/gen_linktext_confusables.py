#!/usr/bin/env python3
"""#368: write system/templates/dashboard/src/core/sentConfusables.js from the table Python reads (edit_ai.LOOK_ALIKE), so the page's
"I sent it" recognition (core/linkText.js) and linktext.py cannot drift apart.

Only the characters that can matter are kept: those the table maps to a letter in the words the sent-line pattern needs
(Chased / Emailed / Asked, by, email, message), either case, or to a hyphen or colon. One string per target.

  python3 dev/tools/gen_linktext_confusables.py            write the file
  python3 dev/tools/gen_linktext_confusables.py --check    exit 1 if the committed file differs
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "scripts"))
OUT = ROOT / "system" / "templates" / "dashboard" / "src" / "core" / "sentConfusables.js"
NEEDED = set("chasedmilkbyg")                    # the letters of chased emailed asked by email message (lower case; either case kept)


def table():
    """{plain character: every look-alike character Python reads as it}, for the characters that matter."""
    import edit_ai
    by = {}
    for k, v in edit_ai.LOOK_ALIKE.items():
        ch = chr(k)
        if len(v) == 1 and (v.lower() in NEEDED or v in "-:"):
            by.setdefault(v, []).append(ch)
    return {t: "".join(sorted(cs)) for t, cs in sorted(by.items())}


def text():
    """The file's whole text."""
    t = table()
    return ("// generated: do not edit. Written by dev/tools/gen_linktext_confusables.py from edit_ai.LOOK_ALIKE (#368).\n"
            "// `--check` fails when this file differs.\n"
            "// Each key is the plain character; its value is every look-alike character that Python's check reads as that character.\n"
            "export const SENT_CONFUSABLES = " + json.dumps(t, ensure_ascii=True, indent=0).replace("\n", "") + ";\n")


def entities():
    """(the named-entity allow-list, the numeric exceptions) the page decodes as html.unescape does.

    Allow-list: the HTML5 names whose text, read the way the sent-line check reads it, is made only of the letters the pattern needs,
    digits, spaces, hyphens or colons (so &colon;, &hyphen;, &NewLine;, &eacute; and the like). Every other name is left as written
    by the page and decoded by Python; neither can make or hide a sent line, because what it gives is outside those characters."""
    import html
    import html.entities
    import edit_ai
    named = {}
    for n, v in html.entities.html5.items():
        t = edit_ai.normal(v.replace("\u00a0", " "))
        if t and all(c.lower() in NEEDED or c in " \t\n-:0123456789" for c in t):
            named[n] = v
    ranges, prev = [], None
    for cp in sorted(html._invalid_codepoints):
        if prev is not None and cp == prev[1] + 1:
            prev[1] = cp
        else:
            prev = [cp, cp]
            ranges.append(prev)
    return named, {str(k): v for k, v in sorted(html._invalid_charrefs.items())}, ranges


def entities_text():
    """The entity file's whole text."""
    named, charrefs, ranges = entities()
    dump = lambda o: json.dumps(o, ensure_ascii=True, sort_keys=True).replace("\n", "")   # noqa: E731
    return ("// generated: do not edit. Written by dev/tools/gen_linktext_confusables.py from Python's html module (#368).\n"
            "// `--check` fails when this file differs. The named entities the page decodes (an allow-list: see the generator),\n"
            "// the numeric\n"
            "// references Python replaces (SENT_CHARREFS) and the code points it drops (SENT_DROPPED, as [first, last] ranges).\n"
            f"export const SENT_NAMED = {dump(named)};\n"
            f"export const SENT_CHARREFS = {dump(charrefs)};\n"
            f"export const SENT_DROPPED = {dump(ranges)};\n")


FILES = {OUT: text, OUT.with_name("sentEntities.js"): entities_text}


def stale():
    """None when the committed files are what the tables give, else why."""
    for path, make in FILES.items():
        if not path.exists() or path.read_text() != make():
            return f"{path.relative_to(ROOT)} is not what dev/tools/gen_linktext_confusables.py writes (run it)"
    return None


if __name__ == "__main__":
    if "--check" in sys.argv:
        why = stale()
        print(why or "sentConfusables.js and sentEntities.js: up to date")
        sys.exit(1 if why else 0)
    for path, make in FILES.items():
        path.write_text(make())
        print(f"wrote {path.relative_to(ROOT)}")
