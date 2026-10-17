"""Copy a release's plain notes into Help's What's new (development only; #158 Help Phase B).

Run: python3 dev/tools/whats_new.py add X.Y.Z     copy dev/release-notes/X.Y.Z-plain.md into system/templates/help/whats-new.md
     python3 dev/tools/whats_new.py check [X.Y.Z]  say whether the notes for the installed (or the given) version are there

The app never reads dev/ at run time: the notes travel inside the release in system/templates/help/whats-new.md, newest first,
one `## creaite X.Y.Z` section each. The plain notes file is a short lead-in line and bullets (a leading `# ...` or
`## creaite X.Y.Z` heading in it is dropped). build_release.py refuses a release whose version has no section.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import paths  # noqa: E402

NEWS = paths.TEMPLATES / "help" / "whats-new.md"


def has(version, text=None):
    """True when whats-new.md has a section for this version."""
    text = NEWS.read_text(encoding="utf-8") if text is None else text
    return re.search(rf"^## creaite {re.escape(version)}\s*$", text, re.M) is not None


def add(version, notes_file=None):
    """Insert the version's plain notes above the newest section. Returns the new text; never overwrites an existing section."""
    src = Path(notes_file or REPO / "dev" / "release-notes" / f"{version}-plain.md")
    if not src.exists():
        raise FileNotFoundError(f"{src} is missing: the plain notes are written before the release")
    text = NEWS.read_text(encoding="utf-8")
    if has(version, text):
        raise ValueError(f"whats-new.md already has creaite {version}")
    body = [ln for ln in src.read_text(encoding="utf-8").strip().splitlines() if not re.match(r"#{1,2} ", ln)]
    section = f"## creaite {version}\n\n" + "\n".join(body).strip() + "\n\n"
    at = re.search(r"^## creaite ", text, re.M)
    return text[:at.start()] + section + text[at.start():] if at else text.rstrip() + "\n\n" + section


def main(argv):
    """The command line: add, check; anything else prints the help."""
    if len(argv) >= 2 and argv[0] == "add":
        NEWS.write_text(add(argv[1]), encoding="utf-8")
        print(f"Added creaite {argv[1]} to {NEWS.relative_to(REPO)}. Rebuild: python3 dev/tools/build_guides.py && "
              "python3 dev/tools/split_dashboard.py build")
        return 0
    if argv and argv[0] == "check":
        v = argv[1] if len(argv) > 1 else paths.VERSION_FILE.read_text(encoding="utf-8").strip()
        print(f"creaite {v}: " + ("notes present." if has(v) else "NOT in whats-new.md."))
        return 0 if has(v) else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
