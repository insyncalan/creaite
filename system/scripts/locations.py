"""creaite locations helper — setup for a projects folder outside the vault (BL-85; standard library only).

creaite's engine and record (database, staging, backups, history, search index, git) stay in the local vault. The engagement
folders and the portfolio folder may live in the company OneDrive: the `locations` setting (settings.json) says where.

Commands (all read-only unless stated; none touches a real folder except the one you name):
  check <folder>           is this folder acceptable as the projects folder? JSON: its `~` form, whether it exists, its kind
                           (company OneDrive, personal OneDrive, another sync service, or a plain local folder), and
                           `refuse` (a reason) for personal cloud storage and other sync services. Warnings, not refusals,
                           for a OneDrive path that names no tenant
  inspect <folder>         check, plus: the engagement folders (each could become a project), the template (from
                           `_Templates/_Skeleton`, else the first engagement) and the `folders` mapping proposed from it
                           (with the candidates where a name is ambiguous), and whether `_Portfolio` exists
  portfolio-spec           print a cx-edit spec that creates the portfolio folder in the configured projects folder
                           (PORTFOLIO.md, the two registers, the cross-project minutes and transcripts folders), only what is
                           missing; stage it with `propose.py stage`. Needs `locations.projects_root` set first
  tilde <path>             the path written with ~ for the home folder (how projects_root is stored)

Setting it up is the cx-setup "Projects folder" step: check, inspect (shown to Alan), `propose.py setting locations.projects_root`
and `locations.folders`, portfolio-spec, then `minutes.py baseline` per project.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

OTHER_SYNC = re.compile(r"/(iCloud Drive[^/]*|Mobile Documents|Dropbox[^/]*|Google Drive[^/]*|GoogleDrive[^/]*|Box[^/]*|pCloud[^/]*)(/|$)", re.I)
ONEDRIVE = re.compile(r"/(OneDrive[^/]*)(/|$)", re.I)
KINDS = {                       # folder name patterns for the `folders` mapping, in the order they are tried
    "transcripts": r"transcript", "minutes": r"minutes?\b", "weekly_reports": r"weekly",
    "adhoc_documents": r"ad[ _-]?hoc"}


def tilde(path) -> str:
    """The path written with ~ for the home folder, as locations.projects_root is stored (BL-85)."""
    home = Path(os.path.expanduser("~")).resolve()
    p = Path(os.path.expanduser(str(path))).resolve()
    try:
        return "~/" + p.relative_to(home).as_posix()
    except ValueError:
        return p.as_posix()


def check(folder) -> dict:
    """Whether a folder is acceptable as the projects folder: its ~ form, whether it exists, its kind (company
    OneDrive, personal OneDrive, other sync or local), a reason to refuse it and any warnings (BL-85).
    """
    p = Path(os.path.expanduser(str(folder)))
    posix = p.resolve().as_posix() if p.exists() else p.as_posix()
    out = {"folder": tilde(p), "exists": p.is_dir(), "kind": "local", "tenant": None, "refuse": None, "warnings": []}
    one = ONEDRIVE.search(posix)
    if OTHER_SYNC.search(posix):
        out.update(kind="other-sync", refuse="This folder is managed by a personal or other sync service. Only the company OneDrive "
                                              "(or a plain local folder) may hold project files: never personal cloud storage.")
    elif one:
        name = one.group(1)
        tenant = name.split("-", 1)[1] if "-" in name else ""
        out["tenant"] = tenant or None
        if re.fullmatch(r"personal", tenant, re.I) or (not tenant and name.lower() == "onedrive"):
            out.update(kind="personal-onedrive", refuse="This is a personal OneDrive (OneDrive-Personal). Only the company OneDrive "
                                                         "(a folder named OneDrive-<company>) may hold project files.")
        else:
            out["kind"] = "company-onedrive"
    if not p.is_dir():
        out["warnings"].append(f"{out['folder']} isn't reachable right now: is OneDrive running and signed in?")
    return out


def engagements(root: Path) -> list:
    """Engagement folders: every folder under the root except hidden ones, those starting with _ (_Templates, _Portfolio) and the skipped ones (99 Archive, 99 System)."""
    if not root.is_dir():
        return []
    return sorted(d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))
                  and not paths.is_skipped(d.name))                    # BL-09, #252: never 99 Archive (or the old _Archive, zz Archive)


def subfolders(base: Path, depth=3) -> list:
    """The folders under `base`, as relative paths, to `depth` levels; hidden ones left out."""
    out = []
    for d in sorted(base.rglob("*")):
        rel = d.relative_to(base)
        if d.is_dir() and len(rel.parts) <= depth and not any(part.startswith(".") for part in rel.parts):
            out.append(rel.as_posix())
    return out


def propose_mapping(template: Path) -> dict:
    """{kind: {"path": best guess or None, "candidates": [...]}} from a template folder's own subfolders."""
    subs = subfolders(template)
    out = {}
    for kind, pat in KINDS.items():
        found = [s for s in subs if re.search(pat, Path(s).name, re.I)]
        if kind in ("weekly_reports", "adhoc_documents"):          # reports live under a reporting folder
            found = [s for s in found if len(Path(s).parts) > 1 or not re.search(r"transcript|minutes", s, re.I)]
        out[kind] = {"path": found[0] if len(found) == 1 else None, "candidates": found}
    # Alan's decision (2026-10-08): client reports file with the weekly reports; a steering-committee folder is separate and creaite never
    # writes to it. Current-state images go to <Reporting>/Content, which creaite creates the first time (the skeleton may lack it).
    out["client_reports"] = {"path": out["weekly_reports"]["path"], "candidates": out["weekly_reports"]["candidates"],
                             "note": "with the weekly reports; a steering folder is left alone"}
    reporting = next((s for s in subs if "/" not in s and re.search(r"report", s, re.I)), None)
    out["images"] = {"path": f"{reporting}/Content" if reporting else "creaite images", "candidates": [],
                     "note": "created the first time an image is filed" if reporting else None}
    return out


def inspect(folder) -> dict:
    """check(), plus the engagement folders, the template folder and the folder mapping proposed from it (BL-85)."""
    out = check(folder)
    root = Path(os.path.expanduser(str(folder)))
    out["engagements"] = engagements(root)
    skeleton = root / "_Templates" / "_Skeleton"
    template, source = (skeleton, "_Templates/_Skeleton") if skeleton.is_dir() else \
        ((root / out["engagements"][0], out["engagements"][0] + " (the first engagement)") if out["engagements"] else (None, None))
    out["template"] = source
    out["skeleton"] = "_Templates/_Skeleton" if skeleton.is_dir() else None
    out["mapping"] = propose_mapping(template) if template else {}
    out["portfolio"] = {"folder": "_Portfolio", "exists": (root / "_Portfolio").is_dir()}
    return out


def portfolio_spec() -> dict:
    """A cx-edit spec that creates whatever is missing of the portfolio folder in the projects folder
    (PORTFOLIO.md, the two registers, cross-project minutes and transcripts). Writes nothing itself.
    """
    if not paths.external():
        sys.exit("creaite locations: set locations.projects_root first (propose.py setting locations.projects_root ...).")
    templates = paths.TEMPLATES
    base = paths.portfolio_dir()
    logical = paths.LOGICAL_PORTFOLIO
    ops = []
    if not base.is_dir():
        ops.append({"op": "mkdir", "path": logical})
    for kind in ("minutes", "transcripts"):
        d = paths.folder("_portfolio", kind)
        if not d.is_dir():
            ops.append({"op": "mkdir", "path": paths.rel(d) if d.exists() else f"{logical}/{paths.folder_name(kind)}"})
    for name, tpl in (("PORTFOLIO.md", "portfolio-template.md"), ("project-register.md", "project-register-template.md"),
                      ("people-register.md", "people-register-template.md")):
        if not (base / name).is_file():
            ops.append({"op": "write", "path": f"{logical}/{name}", "content": (templates / tpl).read_text(encoding="utf-8")})
    return {"source_run": "cx-edit", "items": [],
            "file_changes": {"title": "Create the portfolio folder in the projects folder", "project": None, "file_ops": ops}}


def main(argv):
    """Run the check, inspect, portfolio-spec or tilde command in `argv` and print the result."""
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    if cmd == "check" and len(args) == 1:
        print(json.dumps(check(args[0]), indent=2, ensure_ascii=False))
    elif cmd == "inspect" and len(args) == 1:
        print(json.dumps(inspect(args[0]), indent=2, ensure_ascii=False))
    elif cmd == "portfolio-spec":
        print(json.dumps(portfolio_spec(), indent=2, ensure_ascii=False))
    elif cmd == "tilde" and len(args) == 1:
        print(tilde(args[0]))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("locations.py", main, sys.argv[1:]) if debuglog else main(sys.argv[1:]))
