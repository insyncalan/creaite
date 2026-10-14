"""creaite release zip launcher: built into each release zip as __main__.py by dev/tools/build_release.py.

Run the zip to create a new vault:  python3 creaite-X.Y.Z.zip [folder] [--projects <folder>]
(asks for the folder when left out; --projects, or a question at a terminal, says where the projects live if not in the vault:
the company OneDrive's Engagements folder). To update an existing vault, say "update creaite" in it instead.
"""
import sys
from pathlib import Path

ZIP = Path(sys.argv[0]).resolve()
sys.path.insert(0, str(ZIP / "system" / "scripts"))       # update.py and paths.py, read from inside the zip
import update  # noqa: E402

if __name__ == "__main__":
    args = sys.argv[1:]
    projects = None
    if "--projects" in args:
        i = args.index("--projects")
        projects = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    if len(args) > 1 or projects == "" or (args and args[0] in ("-h", "--help")):
        print(__doc__)
        sys.exit(2)
    sys.exit(update.new_vault_cli(str(ZIP), args[0] if args else None, projects))
