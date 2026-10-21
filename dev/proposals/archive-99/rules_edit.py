"""#252: the creaite-rules.md sentences to change for the 99 Archive rename (Jarvis applies them; the file is replaced by updates).

Run: python3 dev/proposals/archive-99/rules_edit.py <path to creaite-rules.md> [--check]
Each pair is an exact sentence that must occur exactly once; nothing is written unless all of them do (--check never writes).
Works on any base (main, v252-release), unlike rules.diff, which is made against origin/main.
"""
import sys
from pathlib import Path

PAIRS = [
    ('`never_index` (`_Archive`, `_Templates`, `99 System`; the old name `zz Archive` is still skipped for one release, BL-09)',
     '`never_index` (`99 Archive`, `_Archive`, `zz Archive`, `_Templates`, `99 System`; #252, Alan, 20-10-2026: the archive folder is `99 Archive`, and the two old names `_Archive` and `zz Archive` are still read and skipped for one release, then dropped; an older saved list keeps working, `99 Archive` is added to it, nothing is renamed or migrated and Health offers no rename: Alan renames his own folders)'),
    ('| `projects/_Archive/` | Archived projects (BL-09)',
     '| `projects/99 Archive/` | Archived projects (BL-09; the folder was `_Archive` before #252, and a project already archived there is read, and can be restored, for one release)'),
    ('(`<projects root>/_Archive/<engagement folder>` with a projects root)',
     '(`<projects root>/99 Archive/<engagement folder>` with a projects root)'),
    ('Only `tracker.py apply` moves a folder into or out of `_Archive`; ask creaite never reads',
     'Only `tracker.py apply` moves a folder into or out of `99 Archive` (and, for one release, `_Archive` or `zz Archive`: out of, never into); ask creaite never reads'),
    ("maps an archived project's `projects/<folder>/…` into `_Archive`. Each engagement's own `_Archive` (BL-03)",
     "maps an archived project's `projects/<folder>/…` into `99 Archive` (or, for one release, `_Archive` or `zz Archive`; when more than one exists all are read, `99 Archive` first). Each engagement's own `99 Archive` (BL-03)"),
    ('and the spec that moves old reports and minutes into `_Archive`, shown',
     'and the spec that moves old reports and minutes into `99 Archive`, shown'),
    ('agenda and report folders, `_Archive` and `_Templates`**',
     'agenda and report folders, `99 Archive` (and the old `_Archive`, `zz Archive`) and `_Templates`**'),
    ('Never an online-only OneDrive file, `_Archive`, `_Templates` or `99 System`.',
     'Never an online-only OneDrive file, `99 Archive` (or the old `_Archive`, `zz Archive`), `_Templates` or `99 System`.'),
    ('(old reports and minutes move into `_Archive`, below)',
     '(old reports and minutes move into `99 Archive`, below)'),
    ("moved into the engagement's own `_Archive` (the portfolio's minutes into the portfolio's `_Archive`)",
     "moved into the engagement's own `99 Archive` (the portfolio's minutes into the portfolio's `99 Archive`)"),
    ('also moves into `_Archive`: one note',
     'also moves into `99 Archive`: one note'),
    ("portfolio's) `_Archive/<notes folder>/`, and back (`notes_back`, under its old name,",
     "portfolio's) `99 Archive/<notes folder>/`, and back (`notes_back`, from `99 Archive` or an older archive folder, under its old name,"),
]


def main(argv):
    """Check (and, without --check, make) the replacements in the file named first."""
    p = Path(argv[0])
    text = p.read_text(encoding="utf-8")
    bad = [old[:70] for old, _ in PAIRS if text.count(old) != 1]
    if bad:
        print("Not applied; these do not occur exactly once:\n  " + "\n  ".join(bad))
        return 1
    for old, new in PAIRS:
        text = text.replace(old, new)
    if "--check" not in argv:
        p.write_text(text, encoding="utf-8")
    print(f"{len(PAIRS)} sentences " + ("would change" if "--check" in argv else "changed"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
