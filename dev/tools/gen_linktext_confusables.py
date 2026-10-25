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


def stale():
    """None when the committed file is what the table gives, else why."""
    if not OUT.exists() or OUT.read_text() != text():
        return f"{OUT.relative_to(ROOT)} is not what dev/tools/gen_linktext_confusables.py writes (run it)"
    return None


if __name__ == "__main__":
    if "--check" in sys.argv:
        why = stale()
        print(why or "sentConfusables.js: up to date")
        sys.exit(1 if why else 0)
    OUT.write_text(text())
    print(f"wrote {OUT.relative_to(ROOT)}: {sum(len(v) for v in table().values())} characters")
