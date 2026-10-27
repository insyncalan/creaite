"""creaite doctor — health and portability check.

Usage: python3 system/scripts/doctor.py [--read-only] [--json]
Prints PASS or FAIL per check and exits non-zero on any failure. Read-only, apart from
creating and deleting one test file in each writable folder; --read-only checks those folders'
permissions instead and creates nothing (Settings › Health, BL-320). --json prints one JSON object.
"""
import json
import os
import re
import sqlite3
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402  (also puts system/scripts/vendor/ first on the import path)

# Absolute paths that must never be stored: macOS/Linux home and volume paths, Windows drives, file:// URLs
ABSOLUTE = re.compile(r"(?<![\w.])/(?:Users|home|Volumes|private|var|tmp)/[^\s\"'<>|]+"
                      r"|\b[A-Za-z]:\\[^\s\"'<>|]+|file:///[^\s\"'<>|]+")
TABLES = ("projects", "milestones", "workstreams", "actions", "raid", "decisions", "promises", "links", "labels",
          "item_labels", "updates", "applies", "change_log", "rejected", "vault_search")

results = []


# ===== BL-320 (v192-settings-server): read-only runs and JSON for Settings › Health =====
READ_ONLY = False         # --read-only: the write probes below look at permissions instead of writing a test file
AS_JSON = False           # --json: one JSON object at the end instead of the PASS/WARN/FAIL lines
found = []                # [{id, name, status, detail}] in order, for --json


def can_write(folder):
    """True if `folder` can be written to: a test file made and removed, or, in a read-only run, the folder's permissions
    (creating nothing; a folder that doesn't exist yet counts as writable when its nearest existing parent is)."""
    folder = Path(folder)
    if READ_ONLY:
        here = folder
        while not here.exists() and here != here.parent:
            here = here.parent
        return os.access(here, os.W_OK)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".doctor-write-test"
        probe.write_text("ok")
        probe.unlink()
        return True
    except OSError:
        return False
# ===== end BL-320 =====


def check(name, fn):
    """Run one health check and print PASS, WARN or FAIL; `fn` returns (ok, detail), where ok None is a warning."""
    crashed = False
    try:
        ok, detail = fn()
    except Exception as e:  # a crashing check is a failed check (#242: marked, and never dismissable in Health)
        ok, detail, crashed = False, f"{type(e).__name__}: {e}", True
    results.append(ok is not False)           # None is a warning: shown, never a failure
    status = "pass" if ok else "warn" if ok is None else "fail"
    found.append({"id": fn.__name__, "name": name, "status": status, "detail": detail or "",
                  **({"crashed": True} if crashed else {})})
    if not AS_JSON:
        print(f"{status.upper()}  {name}" + (f" — {detail}" if detail else ""))


def python_version():
    """Check Python is 3.9 or later, and warn about Rosetta or an old launcher (BL-248)."""
    v = sys.version_info
    shown = f"Python {v.major}.{v.minor}.{v.micro}"
    if v < (3, 9):
        return False, shown
    # ===== BL-248 (sprint-portability): Rosetta, the run's python3, and an old creaite.app =====
    warn = []
    try:
        import launch as launcher
        import shutil
        if launcher.under_rosetta():
            warn.append("running under Rosetta (as an Intel program): start creaite from Terminal or make the launcher again")
        found = shutil.which("python3", path=launcher.run_path())
        if found and os.path.realpath(found) != os.path.realpath(sys.executable):
            warn.append(f"python3 on a run's PATH is {found}, not this Python (system/scripts/run uses CREAITE_PYTHON first)")
        for app in (Path.home() / "Applications" / "creaite.app", Path("/Applications/creaite.app")):
            plist = app / "Contents" / "Info.plist"
            if plist.is_file() and "LSArchitecturePriority" not in plist.read_text(encoding="utf-8", errors="replace"):
                warn.append(f"{app} is an old launcher that may run under Rosetta: make it again "
                            "(system/scripts/run launch.py make-launcher)")
    except Exception as e:  # noqa: BLE001  the check itself must never fail the doctor
        warn.append(f"couldn't check how Python runs ({type(e).__name__})")
    return (None, f"{shown}; " + "; ".join(warn)) if warn else (True, shown)
    # ===== end BL-248 =====


# ===== BL-305 (sprint-launch-apply): the launcher opens this vault =====
def launcher_vault():
    """Warn when this vault's launcher (creaite.app, or "creaite (dev).app" in the development repository) opens another vault."""
    import launch as launcher
    name = launcher.launcher_name()
    warn = []
    for app in (Path.home() / "Applications" / f"{name}.app", Path("/Applications") / f"{name}.app"):
        other = launcher.launcher_elsewhere(app)
        if other:
            warn.append(f"{app} opens another vault ({other}), not this one: make this vault's launcher with "
                        "system/scripts/run launch.py make-launcher --replace")
    return (None, "; ".join(warn)) if warn else (True, f"{name}.app opens this vault, or there is none (it's optional)")
# ===== end BL-305 =====


def fts5():
    """Check this SQLite has full-text search (FTS5), which search needs."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
    con.execute("INSERT INTO t VALUES ('ABC-A-003 steering')")
    hit = con.execute("SELECT count(*) FROM t WHERE t MATCH '\"ABC-A-003\"'").fetchone()[0]
    return hit == 1, f"SQLite {sqlite3.sqlite_version}"


def vendored():
    """Check the bundled libraries load from system/scripts/vendor/, not from the machine."""
    out = []
    for name in ("openpyxl", "jinja2", "pypdf"):          # BL-275: pypdf reads PDFs for search
        mod = __import__(name)
        where = Path(mod.__file__).resolve()
        if paths.VENDOR not in where.parents:
            return False, f"{name} loaded from outside system/scripts/vendor/"
        out.append(name)
    return True, ", ".join(out) + " from vendor/"


# ===== BL-239 (sprint-portability): the vendor manifest =====
VENDOR_MANIFEST = "manifest.json"            # in system/scripts/vendor/: the SHA-256 of every other file there
VENDOR_SKIP = re.compile(r"(^|/)(__pycache__|\.DS_Store)(/|$)|\.pyc$")


def vendor_files(folder=None):
    """{path relative to vendor/: SHA-256} for every file in the vendor folder, except the manifest and Python's own caches."""
    import hashlib
    folder = Path(folder or paths.VENDOR)
    out = {}
    for f in sorted(folder.rglob("*")):
        rel = f.relative_to(folder).as_posix()
        if f.is_file() and rel != VENDOR_MANIFEST and not VENDOR_SKIP.search(rel):
            out[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def vendor_problems(folder=None):
    """(missing, changed, extra) against vendor/manifest.json; raises OSError or ValueError when the manifest can't be read."""
    folder = Path(folder or paths.VENDOR)
    want = json.loads((folder / VENDOR_MANIFEST).read_text(encoding="utf-8"))["files"]
    have = vendor_files(folder)
    return (sorted(set(want) - set(have)), sorted(n for n in set(want) & set(have) if want[n] != have[n]),
            sorted(set(have) - set(want)))


def vendor_manifest():
    """Check the bundled libraries match their manifest: nothing missing, changed or extra (BL-239)."""
    try:
        missing, changed, extra = vendor_problems()
    except (OSError, ValueError, KeyError, TypeError) as e:
        return False, f"system/scripts/vendor/{VENDOR_MANIFEST} can't be read ({type(e).__name__})"
    found = [(label, names) for label, names in (("missing", missing), ("changed", changed), ("extra", extra)) if names]
    if found:
        return False, ("; ".join(f"{label}: {', '.join(names[:3])}" + (f" (+{len(names) - 3} more)" if len(names) > 3 else "")
                                 for label, names in found)
                       + ". The bundled libraries don't match their manifest: reinstall this version (say \"update creaite\" "
                         "with its zip and \"reinstall\"), or, in development, rebuild it with dev/tools/vendor_manifest.py")
    return True, f"{len(vendor_files())} files match vendor/{VENDOR_MANIFEST}"
# ===== end BL-239 =====


def database():
    """Check tracker.db exists, passes SQLite's integrity check and has every table."""
    if not paths.DB.exists():
        return False, "tracker.db missing — run tracker.py init, or restore from system/backups/"
    con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
    result = con.execute("PRAGMA integrity_check").fetchone()[0]
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    missing = [t for t in TABLES if t not in names]
    if result != "ok":
        return False, result
    if missing:
        return False, "missing tables: " + ", ".join(missing)
    import tracker
    stale = tracker.outdated_tables(con)
    if stale:
        return False, f"schema changed for {', '.join(stale)} — run tracker.py migrate" + \
            (" (BL-133: rejected gains reason and duplicate_of; every row is kept)" if "rejected" in stale else "")
    return True, "integrity ok, schema up to date"


def writable():
    """Check staging, history and backups can be written (creates and deletes one test file in each)."""
    bad = [paths.rel(folder) for folder in (paths.STAGING, paths.HISTORY, paths.BACKUPS) if not can_write(folder)]
    return not bad, ("not writable: " + ", ".join(bad)) if bad else "staging, history, backups"


def extraction_scope():
    """Check nothing has been extracted from documents/ or reports/: only minutes and transcripts are."""
    if set(paths.EXTRACT_FROM) & {"documents", "reports"}:
        return False, "paths.EXTRACT_FROM includes documents or reports"
    bad = []
    if paths.PROCESSED.exists():
        for line in paths.PROCESSED.read_text(encoding="utf-8").splitlines():
            if not line.startswith("#") and re.search(r"/(documents|reports)/", line):
                bad.append("processed.txt: " + line[:80])
    for prop in paths.STAGING.glob("proposed-*.json"):
        meeting = json.loads(prop.read_text(encoding="utf-8")).get("meeting") or {}
        if re.search(r"/(documents|reports)/", meeting.get("transcript") or ""):
            bad.append(f"{prop.name}: transcript taken from documents/ or reports/")
    if paths.external():                 # BL-85: the mapped folders; a report or document folder must never be one we read from
        folders = paths.project_folders()
        ext = {d.resolve() for code, _ in folders for d in paths.extract_dirs(code)}
        rep = {d.resolve() for code, _ in folders for d in (paths.folder(code, "weekly_reports"), paths.folder(code, "client_reports"),
                                                            paths.folder(code, "adhoc_documents"), paths.folder(code, "notes"))}   # BL-301
        for e in ext:
            for r in rep:
                if e == r or e in r.parents or r in e.parents:
                    bad.append(f"locations.folders: a meeting folder and a report folder overlap ({e.name} / {r.name})")
        # Every file named in processed.txt (a line can list several, after a key that may itself hold "|") and every
        # staged transcript: none may come from a report folder. Paths from an earlier layout are left alone.
        named = []
        for ln in (paths.PROCESSED.read_text(encoding="utf-8").splitlines() if paths.PROCESSED.exists() else []):
            if not ln.startswith("#"):
                named += [(f"processed.txt: {ln[:60]}", m) for m in re.findall(r"projects/[^;|]*?\.\w{2,5}(?=\s*(?:;|\||$))", ln)]
        named += [(f"{prop.name}: transcript", (json.loads(prop.read_text(encoding="utf-8")).get("meeting") or {}).get("transcript") or "")
                  for prop in paths.STAGING.glob("proposed-*.json")]
        for label, rel in named:
            if rel.startswith("projects/"):
                where = paths.resolve(rel).resolve()
                if any(r == where or r in where.parents for r in rep):
                    bad.append(f"{label} was taken from a report folder")
    return not bad, "; ".join(bad) or "minutes and transcripts only"


def notes_folder_own():
    """#124: the notes folder is its own: never the same as, inside or around a meeting, report, Steerco, agendas or images
    folder (Delete note moves the notes folder's files into 99 Archive). The check is paths.notes_folder_clash (#128)."""
    bad = paths.notes_folder_clash()
    return (False, f"locations.folders.notes ({paths.folder_name('notes')}) is also the {', '.join(bad)} folder or holds it: "
                   "give notes a folder of their own") if bad else (True, f"notes in {paths.folder_name('notes')}, a folder of their own")


def projects_root():
    """Check the projects folder is reachable and of a kind creaite can use (BL-85)."""
    if not paths.external():
        return True, "the projects are in the vault"
    import locations
    where = locations.tilde(paths.projects_root())
    if not paths.projects_root().is_dir():
        return False, f"{where} isn't reachable: is OneDrive running and signed in? (Nothing is lost: creaite carries on from the vault)"
    kind = locations.check(paths.projects_root())
    return (None, f"{where}: {kind['refuse']}") if kind["refuse"] else (True, f"{where} ({kind['kind'].replace('-', ' ')})")


def project_folders_present():
    """Check each project's mapped minutes, transcripts and report folders exist (BL-85)."""
    if not paths.external():
        return True, "the default folders"
    missing = []
    for code, _ in paths.project_folders():
        for kind in (("minutes", "transcripts") if code == "_portfolio" else ("minutes", "transcripts", "weekly_reports", "client_reports")):
            if not paths.folder(code, kind).is_dir() and f"{code}: {paths.folder_name(kind)}" not in missing:    # (client reports share Weekly)
                missing.append(f"{code}: {paths.folder_name(kind)}")
    registered = set(paths.register_folders())
    gone = sorted(c for c in registered if not (paths.projects_root() / paths.register_folders()[c]).is_dir())
    if gone:
        missing += [f"{c}: the folder {paths.register_folders()[c]!r} isn't there" for c in gone]
    return (None, "missing: " + "; ".join(missing[:8]) + (f" (+{len(missing) - 8} more)" if len(missing) > 8 else "")
            + ". Create them, or correct locations.folders.") if missing else (True, "every registered project has its mapped folders")


def mapped_folders():
    """BL-93: the folders creaite files into (Steerco, ad hoc documents, images) are there and can be written to."""
    problems = []
    kinds = [k for k in (paths.locations().get("folders") or {})
             if k not in ("minutes", "transcripts", "notes")]          # BL-301: a notes folder is made with the first note
    for code, _ in paths.project_folders():
        if code == "_portfolio":
            continue
        for kind in kinds:
            d, label = paths.folder(code, kind), f"{code}: {paths.folder_name(kind)}"
            if label in problems or any(x.startswith(label + " ") for x in problems):
                continue                                  # client reports share the weekly folder: said once
            if not d.exists():
                if paths.external() and kind not in ("weekly_reports", "client_reports"):   # those are in "Projects folders present"
                    problems.append(f"{label} isn't there")
            elif not os.access(d, os.W_OK):
                problems.append(f"{label} is read-only")
    if not problems:
        return True, "every mapped folder is there and can be written to"
    return None, ("; ".join(problems[:6]) + (f" (+{len(problems) - 6} more)" if len(problems) > 6 else "")
                  + ". A missing one is made when creaite files something into it; a read-only one needs its sharing or permissions fixed.")


def other_connector_rules():
    """F3 follow-up: the allow rules in .claude/settings.local.json and ~/.claude/settings.json (read only; it is outside the vault)
    that permissions.connector_problem refuses: another connector, a Microsoft 365 action, a built-in that acts outside the laptop.
    Claude Code applies both files to ask creaite's runs as well."""
    import permissions
    found = []
    for name, f in ((".claude/settings.local.json", permissions.LOCAL_SETTINGS),
                    ("~/.claude/settings.json", Path.home() / ".claude" / "settings.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue                                            # missing or unreadable: the permission-file check reports it
        perms = data.get("permissions") if isinstance(data, dict) else None
        allow = perms.get("allow") if isinstance(perms, dict) else None
        for rule in allow if isinstance(allow, list) else []:
            why = permissions.connector_problem(rule)
            if why:
                found.append(f"{rule} in {name} ({why})")
    return found


def assistant_permissions():
    """BL-93, BL-96: flag a rule in .claude/settings.json broader than creaite's own (F3: and a connector or acting built-in
    allowed in settings.local.json or ~/.claude/settings.json), and a missing projects-root folder."""
    try:
        perms = json.loads(paths.CLAUDE_SETTINGS.read_text(encoding="utf-8")).get("permissions") or {}
    except (OSError, ValueError) as e:
        return False, f".claude/settings.json can't be read ({e})"
    if (paths.STAGING / "deny-lifted.json").exists():          # BL-96: a confirmed permission-file run was cut short
        return None, ("deny entries that keep the panel out of a permission file were lifted for a run that never finished: "
                      "python3 system/scripts/permissions.py recover puts them back (the live server also does this when it starts)")
    broad = []
    import permissions
    for rule in perms.get("allow") or []:
        why = permissions.connector_problem(rule)    # Sprint 4b: reading is allowed, actions are not; F3: no other connector
        if why is not None:                          # or built-in that acts outside the laptop
            if why:
                broad.append(f"{rule} ({why})")
            continue
        m = re.match(r"^(\w+)(?:\((.*)\))?$", rule)
        tool, spec = (m.group(1), m.group(2)) if m else (rule, None)
        if tool in ("Bash", "Edit", "Write", "WebFetch", "WebSearch") and (spec is None or spec.strip() in ("*", "**", "/**", "//**", "~/**", "~", "/")):
            broad.append(rule)
        elif tool in ("Edit", "Write") and spec and (spec.startswith(("//", "~")) or Path(spec).is_absolute()):
            root = str(paths.locations().get("projects_root") or "").strip().rstrip("/")
            if not (root and spec.startswith(root + "/")) and not spec.startswith(("//" + root.lstrip("/") + "/")):
                broad.append(f"{rule} (outside the vault and the projects folder)")
        elif tool == "Bash" and spec and not permissions.runs_one_script(spec):          # BL-237: or through the wrapper
            broad.append(f"{rule} (not a creaite script)")
        if tool in ("Bash", "Edit", "Write") and permissions.rule_refusal(rule) and not any(rule in b for b in broad):   # BL-141
            broad.append(f"{rule} ({permissions.rule_refusal(rule)})")
    if str(perms.get("defaultMode") or "") in ("bypassPermissions", "acceptEdits"):
        broad.append(f"defaultMode {perms['defaultMode']}")
    broad += other_connector_rules()
    root = str(paths.locations().get("projects_root") or "").strip().rstrip("/")
    dirs = [str(d).rstrip("/") for d in perms.get("additionalDirectories") or []]
    wide = [d for d in dirs if d != root and d not in ("", ".")]
    if wide:
        broad.append("additionalDirectories " + ", ".join(wide) + (" (wider than the projects folder)" if root else " (the projects are in the vault: none is needed)"))
    if broad:
        return None, ("broader than creaite asks for: " + "; ".join(broad[:5]) + (f" (+{len(broad) - 5} more)" if len(broad) > 5 else "")
                      + ". Review them with python3 system/scripts/permissions.py list; undo the ones creaite added with permissions.py undo.")
    if paths.external() and root not in dirs:
        return None, (f"Claude Code can't read {root} from a Terminal session yet: python3 system/scripts/permissions.py projects-root "
                      "--why \"read the project documents\" adds it (the dashboard's ask creaite doesn't need it)")
    return True, "the assistant's rules are as narrow as creaite sets them" + (", with the projects folder readable" if paths.external() else "")


# ===== BL-141 (sprint-admin): the guard =====
NEVER_REQUIRED = (("home", ".ssh"), ("home", ".aws"), ("home", ".gnupg"), ("home", "Library/Keychains"), ("home", "Library/Cookies"),
                  ("home", "Library/Application Support/Google/Chrome"), ("abs", "/etc"), ("abs", "/usr"), ("abs", "/System"),
                  ("vault", "system/tracker.db*"), ("vault", "system/scripts"), ("vault", "system/creaite-rules.md"), ("vault", "VERSION"),
                  ("vault", "system/releases"), ("vault", "system/backups"), ("vault", "system/guard"), ("vault", "system/staging/proposed-*"))


def assistant_guard():
    """BL-141: the never list is intact, the permission files are valid, no hook switch or stray hook is in the vault's settings,
    and nothing is left over from a run (the run's mark, requests that never reached a card)."""
    import time
    import reach
    rows = {(b, p) for b, p, _o, _w in reach.NEVER}
    missing = [p for b, p in NEVER_REQUIRED if (b, p) not in rows]
    if missing:
        return False, "the never list is missing " + ", ".join(missing) + ": reinstall the release (update creaite)"
    for rel in ("system/tracker.db", "system/scripts/tracker.py", "system/creaite-rules.md", "VERSION"):
        if reach.classify(rel, "change")[0] != "never":
            return False, f"{rel} isn't refused for changes: reinstall the release"
    if reach.classify("~/.ssh/id_rsa", "read")[0] != "never":
        return False, "~/.ssh isn't refused: reinstall the release"
    problems = []
    for f in (paths.CLAUDE_SETTINGS, paths.CLAUDE_SETTINGS.with_name("settings.local.json"), paths.SETTINGS):
        if f.exists():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                return False, f"{paths.rel(f)} isn't valid JSON ({e})"
            if f != paths.SETTINGS and (data.get("disableAllHooks") or data.get("hooks")):
                problems.append(f"{paths.rel(f)} has {'disableAllHooks' if data.get('disableAllHooks') else 'hooks'} (ask creaite's guard "
                                "is passed with each run and stays on, but a hook here runs commands in your own sessions)")
    if reach.RUN_FILE.exists():
        try:
            started = json.loads(reach.RUN_FILE.read_text(encoding="utf-8")).get("started") or 0
        except (OSError, ValueError):
            started = 0
        limit = 60 * (float((paths.load_settings().get("assistant") or {}).get("run_timeout_minutes", 30)) + 30)
        if time.time() - float(started) > limit:
            problems.append("a run's mark (system/guard/run.json) was left by a run that never finished: the live server clears it when it starts")
    reqs = paths.STAGING / "changes"
    old = [f for f in reqs.glob("*.json")] if reqs.is_dir() else []
    old = [f for f in old if time.time() - f.stat().st_mtime > 24 * 3600]
    if old:
        problems.append(f"{len(old)} change request(s) older than a day in system/staging/changes/ never reached a card: the live server clears them when it starts")
    if problems:
        return None, "; ".join(problems)
    return True, f"the never list holds {len(rows)} places; the permission files are valid; nothing is left over from a run"


def vault_not_synced():
    """Check the vault itself is not in a synced folder: the database and backups stay on this laptop."""
    import update
    where = paths.ROOT.resolve().as_posix()
    return (False, "the vault is in a synced folder (OneDrive, iCloud or similar): the database, staging, backups and git must stay on this laptop only"
            ) if update.SYNCED.search(where) else (True, "the vault is local")


def online_only():
    """Warn about online-only OneDrive files, which creaite never reads or downloads (BL-85)."""
    files = paths.online_only_files()
    if not files:
        return True, "none" if paths.external() else "not used"
    names = ", ".join(f"{code}/{f.name}" for code, _, f in files[:4]) + (f" (+{len(files) - 4} more)" if len(files) > 4 else "")
    return None, (f"{len(files)} online-only file(s), not read or indexed: {names}. In Finder, set the Engagements folder to Always keep "
                  "on this device (OneDrive); creaite never downloads them itself.")


def text_of_template(p):
    """The text of a template file; for an Office file, its XML parts joined."""
    if p.suffix.lower() in (".docx", ".xlsx", ".pptx"):
        with zipfile.ZipFile(p) as z:
            return " ".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
    return p.read_text(encoding="utf-8", errors="ignore")


def no_absolute_paths():
    """Check no absolute path is stored in the database, proposals or templates (portability)."""
    found = []
    if paths.DB.exists():
        con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
        for t in ("projects", "milestones", "actions", "raid", "decisions", "updates", "change_log", "applies"):
            for row in con.execute(f"SELECT * FROM {t}"):
                for v in row:
                    if isinstance(v, str) and ABSOLUTE.search(v):
                        found.append(f"tracker.db {t}: {ABSOLUTE.search(v).group()[:60]}")
    for prop in list(paths.STAGING.glob("proposed-*.json")) + list(paths.APPLIED.glob("proposed-*.json")):
        m = ABSOLUTE.search(prop.read_text(encoding="utf-8"))
        if m:
            found.append(f"{paths.rel(prop)}: {m.group()[:60]}")
    for tpl in paths.TEMPLATES.glob("*"):
        if tpl.is_file() and tpl.suffix.lower() in (".md", ".html", ".docx", ".xlsx", ".txt", ".json"):
            m = ABSOLUTE.search(text_of_template(tpl))
            if m:
                found.append(f"{paths.rel(tpl)}: {m.group()[:60]}")
    return not found, "; ".join(found[:5]) or "database, proposals and templates"


def config_files():
    """Check the permissions, schedules and settings files exist and parse."""
    missing = [paths.rel(p) for p in (paths.ROOT / ".claude" / "settings.json", paths.SCHEDULES, paths.SETTINGS)
               if not p.exists()]
    if missing:
        return False, "missing: " + ", ".join(missing)
    paths.load_settings()
    json.loads((paths.ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return True, ".claude/settings.json, schedules.md, settings.json"


def people_register():
    """BL-55: the register reads, and the old settings lists have been moved into it."""
    import propose
    legacy = sum(map(len, propose.people_legacy_names()))
    note = (f"; settings.json still lists {legacy} name{'s' if legacy != 1 else ''}: say \"setup\" to move them"
            if legacy else "")
    if not paths.PEOPLE_REGISTER.exists():
        return True, "not created yet: say \"setup\" to create it" + note
    text = paths.PEOPLE_REGISTER.read_text(encoding="utf-8")
    if not propose.people_table(text.splitlines()):
        return False, f"{paths.rel(paths.PEOPLE_REGISTER)} has no People table (Full name, Email, Aliases, …)"
    return True, f"{len(propose.people_parse(text))} people" + note


def search_index():
    """BL-07: the index matches word forms (porter), system/search/ is writable; a stale index is only a note, as it
    refreshes itself."""
    if not paths.DB.exists():
        return True, "no tracker.db yet"
    con = sqlite3.connect(f"file:{paths.DB}?mode=ro", uri=True)
    row = con.execute("SELECT sql FROM sqlite_master WHERE name = 'vault_search'").fetchone()
    if not row or "porter" not in row[0].lower():
        return False, "the search index doesn't match word forms yet — run tracker.py migrate"
    if not can_write(paths.SEARCH_DIR):
        return False, f"{paths.rel(paths.SEARCH_DIR)} isn't writable"
    import tracker
    stale, why = tracker.index_state()
    return True, "word forms, writable" + (f"; out of date ({why}): it refreshes itself, or run tracker.py index"
                                           if stale else ", up to date")


def workstreams_moved():
    """BL-58: the old settings.json workstream lists have been moved into the table (a note, never a failure)."""
    legacy = paths.load_settings().get("workstreams") or {}
    n = len(legacy.get("added") or []) + len(legacy.get("hidden") or [])
    return True, (f"settings.json still lists {n} workstream name{'s' if n != 1 else ''}: say \"setup\" to retire them"
                  if n else "kept in the workstreams table")


def new_vault():
    """A vault made by new-vault still waiting for its first setup: warnings with the fix, never failures."""
    import tracker
    gaps = []
    if not tracker.register_projects():
        gaps.append("no projects in the project register")
    if not (paths.load_settings().get("identity") or {}).get("name"):
        gaps.append("your name isn't set")
    claude = paths.ROOT / "CLAUDE.md"
    if claude.exists() and re.search(r"^- Role:\s*$", claude.read_text(encoding="utf-8"), re.M):
        gaps.append("your role isn't set")
    if gaps:
        return None, "; ".join(gaps) + ". Add them in Settings › Essentials"
    return True, "projects, name and role set"


def version():
    """Check the VERSION file, when there is one, holds a version such as 1.2.0."""
    if not paths.VERSION_FILE.exists():
        return True, "no VERSION file (set up before the first release)"
    v = paths.VERSION_FILE.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        return False, f"VERSION is {v!r}; expected e.g. 1.2.0"
    return True, f"creaite {v}"


def rules_imported():
    """Check the root CLAUDE.md imports system/creaite-rules.md."""
    claude_md = paths.ROOT / "CLAUDE.md"
    text = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
    if not paths.RULES.exists():
        return ("## Non-negotiables" in text,
                "rules still in CLAUDE.md (not split yet; cx-setup offers it)" if text else "CLAUDE.md missing")
    if not re.search(r"^@system/creaite-rules\.md\s*$", text, re.M):
        return False, "CLAUDE.md doesn't import the rules: add the line @system/creaite-rules.md (cx-setup offers it)"
    return True, "CLAUDE.md imports system/creaite-rules.md"


PURE_MODULES = ("invite_filter.py", "invite_blocks.py")      # #375 E1: text in, text out; no file, so no location


def scripts_use_paths():
    """Check every script imports paths.py, the one place locations are defined."""
    bad = []
    for s in (paths.ROOT / "system" / "scripts").glob("*.py"):
        if s.name == "paths.py" or s.name in PURE_MODULES:
            continue
        if not re.search(r"^import paths\b", s.read_text(encoding="utf-8"), re.M):
            bad.append(s.name)
    return not bad, ("not importing paths: " + ", ".join(bad)) if bad else "every script imports paths"


def offsite_backup():
    """The off-laptop copy of the daily backup (BL-85): only when the projects live outside the vault."""
    import tracker
    d = tracker.offsite_dir()
    if d is None:
        return True, "not used (your projects are in the creaite folder)"
    problem = offsite_unwritable(d)
    if problem:
        return None, problem
    last = tracker.last_offsite_copy()
    if not last:
        return None, f"no copy yet in {paths.locations().get('offsite_backup')}: it is made after the next daily backup"
    from datetime import date
    import backup
    age = (backup.today() - date.fromisoformat(last)).days      # BL-323: two days or more is a warning
    shown = f"{last[8:10]}-{last[5:7]}-{last[0:4]}"
    old = old_offsite_copies(d)                                               # BL-112
    tail = f"; the old folder {OLD_OFFSITE} still holds {old} copies and can be removed" if old else ""
    return (None, f"last copy {shown}, {age} days ago: is OneDrive running?{tail}") if age >= 2 else (None if tail else True, f"last copy {shown}{tail}")


# ===== BL-328: a sweep lock held with no sweep running =====
def sweep_lock():
    """The sweep lock (sweep.py lock): fine when none is held or a sweep holds it; a warning, with Release, when it is held with
    no sweep running (its run ended, or its server stopped) and would refuse the next sweep."""
    import sweep
    info = sweep.lock_info()
    state = sweep.lock_state(info)
    if state is None:
        return True, "no sweep lock held"
    since = info["started"].strftime("%d-%m-%Y %H:%M")
    if state == "running":
        return True, f"a sweep is running (since {since})"
    held_by = f" by run {info['run']}" if info.get("run") else ""
    return None, (f"a sweep lock is held{held_by} since {since} with no sweep running: the next sweep replaces it, or "
                  f"Release it (system/scripts/run sweep.py unlock --if-idle)")


# ===== BL-323: the weekly restore check and the last Tidy up, from backup.py's state (read only) =====
def backup_check():
    """The weekly restore check (backup.verify): when it last ran and what it found; a problem says what to do."""
    import backup
    from datetime import date
    v = backup.state().get("verify")
    if not v:
        return True, "not run yet: it runs with the next daily backup (or: system/scripts/run backup.py check)"
    day = v.get("day", "")
    if not v.get("ok"):
        return None, (f"{backup.shown(day)}: " + "; ".join(v.get("problems") or ["a problem"])[:400] +
                      ". Run system/scripts/run backup.py check; if it fails again, say \"setup\" in Claude Code")
    age = (backup.today() - date.fromisoformat(day)).days
    if age > backup.VERIFY_EVERY_DAYS + 1:
        return None, f"last passed {backup.shown(day)}, {age} days ago: it runs with the daily backup at the first session of the day"
    note = f"; {v['note']}" if v.get("note") else ""         # e.g. the zip's git history is one snapshot commit
    return True, f"passed {backup.shown(day)} ({', '.join(v.get('checked') or []) or 'nothing to check yet'}){note}"


def tidy_up():
    """The last automatic Tidy up of old backups (backup.tidy): counts and sizes only."""
    import backup
    t = backup.state().get("tidy")
    if not t:
        return True, "not run yet: it runs once a day after the daily backup"
    return True, f"Tidy up, {backup.shown(t['day'])}: removed {t.get('removed', 0)} files, {backup.mb(t.get('bytes', 0))}"
# ===== end BL-323 =====


OLD_OFFSITE = "_Portfolio/creaite backups"      # where the copies went before BL-112; creaite never moves or deletes them


def offsite_unwritable(d):
    """None if the backup copy's folder can be written to (or created, at the first folder that exists above it), else why not.
    Nothing is created: the daily backup makes the folders when it needs them (BL-112)."""
    here = Path(d)
    while not here.exists() and here != here.parent:
        here = here.parent
    if READ_ONLY:                                       # BL-320: Health looks, never writes
        return None if os.access(here, os.W_OK) else f"can't write to {paths.locations().get('offsite_backup')}"
    probe = here / ".creaite-write-test"
    try:
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as e:
        return f"can't write to {paths.locations().get('offsite_backup')} ({type(e).__name__}: {e})"
    return None


def old_offsite_copies(new_dir):
    """How many copies the old backup folder still holds, once the new one holds a copy of its own (else 0)."""
    old = paths.projects_root() / OLD_OFFSITE
    if not old.is_dir() or old == Path(new_dir):
        return 0
    return len([f for f in old.glob("tracker-*.db")])


def debug_log():
    """The debug log (BL-102): its folder is writable, the level is valid, and no error keeps repeating."""
    import log
    if not can_write(paths.LOGS):
        return False, f"{paths.rel(paths.LOGS)} is not writable: nothing is being logged"
    block = paths.load_settings().get("logging") or {}
    if str(block.get("level", "info")).lower() not in ("debug", "info"):
        return None, f"logging.level \"{block.get('level')}\" isn't \"info\" or \"debug\": \"info\" is used"
    # ===== BL-263 (fix-doctor-errors) ===== first and last times; only a repeat within the window warns, older ones "stopped"
    again = log.repeats(days=int(log.settings()["keep_days"]))
    live = [g for g in again if g["live"]]
    stopped = [g for g in again if not g["live"]]
    shown = lambda gs, tail: "; ".join(f"{g['count']} × {g['area']}: {log.short(g['message'])} — {log.span(g)}{tail}" for g in gs[:3])
    note = f"; stopped: {shown(stopped, ', none since')}" if stopped else ""
    if live:
        return None, f"errors that keep coming back: {shown(live, '')}{note} (see {paths.rel(paths.LOGS)})"
    return True, f"{paths.rel(paths.LOGS)}: writable, {len(log.files())} day(s) kept{note}"
    # ===== end BL-263 =====


# ===== BL-260 (fix-minutes-draft) =====
def minutes_drafts():
    """Pending minutes in staging whose Word draft was never made or has gone: a warning naming each, with the fix."""
    missing = []
    for f in sorted(paths.STAGING.glob("proposed-*.json")):
        try:
            m = json.loads(f.read_text(encoding="utf-8")).get("meeting") or {}
        except (OSError, ValueError):
            continue                       # an unreadable proposal is Review's to report, not this check's
        if not m or m.get("note") or m.get("applied") or m.get("minutes_decision", "pending") != "pending":
            continue
        if not m.get("draft") or not paths.resolve(m["draft"]).is_file():
            missing.append(f"{f.name} ({m.get('title') or 'untitled'})")
    if missing:
        return None, (f"{len(missing)} staged minutes with no Word draft: {'; '.join(missing)}. "
                      "Reject them in Review and process the meeting again")
    return True, "every staged minutes row has its Word draft"
# ===== end BL-260 =====
# ===== BL-252 (fix-small-17): ask creaite's refused commands, counted by shape =====
def refused_commands():
    """How many commands ask creaite's guard refused in the last seven days, by shape (a pipe, a redirect, cd … &&): counts
    only, never the command (BL-102). Shown for information: a rise means ask creaite's instruction isn't holding."""
    import log
    return True, f"last 7 days: {log.refusals_line(days=7)}"
# ===== end BL-252 =====
# ===== BL-267: record commands a plain chat tried =====
def record_refusals():
    """How many record-changing commands (tracker.py apply, review.py approve…) the guard refused in an unconfirmed ask creaite
    chat in the last seven days, by command: names only (BL-102). Information: each one is a change the chat tried without
    Alan's confirmation, which the guard stopped."""
    import log
    from datetime import timedelta
    counts = {}
    for e in log.entries(log.now() - timedelta(days=7)):
        if e["area"] == "guard" and e["message"].startswith("record command refused: "):
            name = e["message"][len("record command refused: "):]
            counts[name] = counts.get(name, 0) + 1
    found = ", ".join(f"{n} × {name}" for name, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    return True, f"last 7 days: {found or 'none'}"
# ===== end BL-267 =====
# ===== BL-255 (sprint-csp-report): the report-only script policy =====
def script_policy():
    """How many report-only script-policy violations the browser reported in the last seven days, by directive and kind of
    source: counts only (BL-102). Information while the policy is report-only: each one is something an enforced policy
    would stop, so the count should be zero before BL-255 is enforced."""
    import log
    from datetime import timedelta
    mode = str((paths.load_settings().get("live_mode") or {}).get("script_policy", "report-only")).strip().lower()
    if mode == "off":
        return True, "off (live_mode.script_policy)"
    counts, lead = {}, "report-only violation: "
    for e in log.entries(log.now() - timedelta(days=7)):
        if e["area"] == "csp" and e["message"].startswith(lead):
            key = e["message"][len(lead):]
            counts[key] = counts.get(key, 0) + 1
    total = sum(counts.values())
    top = ", ".join(f"{n} × {k}" for k, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3])
    return True, f"{total} violation{'' if total == 1 else 's'} in 7 days" + (f" ({top})" if top else "")
# ===== end BL-255 =====

# ===== BL-10 and BL-03: archiving (v1.9.5) =====
def archive_items():
    """The daily archiving of items closed long ago: its last run, as information (never a warning)."""
    import archive
    return True, archive.items_line(archive.status())


def archive_reports():
    """Reports and minutes older than archive.reports_after_months: a warning once a month while any are due (Health's line, with
    Fix it on the approval card); otherwise the last archive."""
    import archive
    st = archive.status()
    line = archive.reports_line(st)
    if st["reports"]["offer"]:
        return None, (f"{line}: each moves into its engagement's own 99 Archive, in the same place below it; links keep working, "
                      "nothing is deleted (Settings › Health › Archive them)")
    return True, line
# ===== end BL-10 and BL-03 =====


def main():
    """Run every check in order and print the results; exits non-zero on any failure. --read-only makes no test files;
    --json prints one JSON object ({checks: [{id, name, status, detail}], passed, failed}) instead of the lines (BL-320)."""
    global READ_ONLY, AS_JSON
    READ_ONLY, AS_JSON = "--read-only" in sys.argv[1:], "--json" in sys.argv[1:]
    if not AS_JSON:
        print(f"creaite doctor — {paths.ROOT.name}/")
    code = run_checks()
    failed = results.count(False)
    if AS_JSON:
        print(json.dumps({"checks": found, "passed": len(results) - failed, "failed": failed, "read_only": READ_ONLY},
                         ensure_ascii=False))
    else:
        print(f"{len(results) - failed} passed, {failed} failed.")
    return code


def run_checks():
    """Every check, in order; 1 if any failed, else 0."""
    check("Python 3.9 or later", python_version)
    check("Launcher opens this vault", launcher_vault)   # BL-305
    check("SQLite full-text search (FTS5)", fts5)
    check("Bundled libraries import", vendored)
    check("Bundled libraries match their manifest", vendor_manifest)   # BL-239
    check("tracker.db integrity", database)
    check("Write access", writable)
    check("Projects folder reachable", projects_root)
    check("Projects folders present", project_folders_present)
    check("Mapped folders can be filed into", mapped_folders)
    check("Notes have a folder of their own", notes_folder_own)       # #124
    check("Assistant permissions", assistant_permissions)
    check("ask creaite's reach and guard", assistant_guard)
    check("Vault is local, not synced", vault_not_synced)
    check("Online-only files", online_only)
    check("Archiving of old items", archive_items)                    # BL-10
    check("Old reports and minutes", archive_reports)                 # BL-03
    check("Extraction never reads documents/ or reports/", extraction_scope)
    check("No absolute paths stored", no_absolute_paths)
    check("Config files present", config_files)
    check("People register", people_register)
    check("Workstreams", workstreams_moved)
    check("Search index", search_index)
    check("Off-laptop backup copy", offsite_backup)
    check("Backup restore check", backup_check)            # BL-323
    check("Tidy up of old backups", tidy_up)               # BL-323
    check("Sweep lock", sweep_lock)                           # BL-328
    check("Debug log", debug_log)
    check("Staged minutes have their Word draft", minutes_drafts)   # BL-260
    check("ask creaite's refused commands", refused_commands)     # BL-252 (fix-small-17)
    check("Record changes refused in a plain chat", record_refusals)   # BL-267
    check("Script policy (report-only)", script_policy)           # BL-255
    check("First setup", new_vault)
    check("Version", version)
    check("creaite rules imported", rules_imported)
    check("Scripts take locations from paths.py", scripts_use_paths)
    return 1 if results.count(False) else 0


if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("doctor.py", main) if debuglog else main())
