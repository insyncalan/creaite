"""creaite updates (BL-36) — install a newer engine from a release zip, keeping the vault's data.

Commands (run from anywhere; every location comes from paths.py):
  version                 print the installed version
  find                    the newest release zip in system/releases/, and in ~/Downloads (JSON)
  fetch [vX.Y.Z]          BL-238: download the newest release zip, pre-releases included (or that version), from GitHub with gh (BL-280)
                          into system/releases/, check it against its checksums, and print JSON {version, path, installed,
                          newer}. Installs nothing: inspect and install follow, shown first and confirmed. Inbound only. If gh
                          is missing or not signed in, it says so and how to download the zip by hand instead
  inspect <zip>           check a release zip and print what installing it would change (JSON). Changes nothing
  install <zip> [--reinstall]
                          back up, replace the engine files, add new settings, migrate the database, rebuild the
                          dashboard and Excel export, run doctor; then (BL-320) make this vault's launchers
                          again, refresh the app's icon for Chrome and restart the running live server, each
                          reported. Rolls back by itself if a step fails.
                          The zip is kept in system/releases/. An older or equal version needs --reinstall
  undo [--keep-database]  restore the engine, settings and database from the last update's backup. Refused if the
                          database has changed since the update, unless --keep-database (engine and settings only)
  tidy                    apply this engine's settings migrations and retire the rules it no longer ships, in place
                          (logged; nothing the second time). Run by tracker.py migrate, so an update done by an older
                          update.py still gets them
  new-vault <zip> [folder] [--projects <folder>]
                          create a new, empty vault from a release zip in a folder of your choice (asked for when
                          left out): engine, starting files, an empty database, the dashboard; then doctor. Refuses a
                          folder that isn't empty or that OneDrive, iCloud or another sync service manages: the vault
                          is always local. --projects (or asked for, optionally) names where the projects live
                          instead of the vault's own projects/ folder: the company OneDrive's Engagements folder
                          (OneDrive-<company>, never a personal one), set as locations.projects_root with the portfolio
                          folder made beside the engagements (BL-85).
                          The same as running the zip itself: python3 creaite-X.Y.Z.zip [folder]

A release zip holds the engine files at their vault paths plus creaite-release.json (version, release date, notes and
the SHA-256 of every file); dev/tools/build_release.py builds it. The engine and data lists are in paths.py: the root
CLAUDE.md and all data are never touched, and the two merged files only gain new keys and permission rules.
"""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

# Never shipped or installed: caches, and the dashboard's source (BL-231 step 2a: a release carries the built
# system/templates/dashboard.html; its source in system/templates/dashboard/ is for development only)
SKIP = re.compile(r"(^|/)(__pycache__|\.DS_Store)(/|$)|\.pyc$|^system/templates/dashboard/")
INSTALLED = paths.RELEASES / "installed.json"     # the installed release: version and the engine files it shipped
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
BOOTSTRAP = "__main__.py"                         # at a release zip's root: makes the zip runnable (new_vault); never installed
SYNCED = re.compile(r"/(OneDrive[^/]*|iCloud Drive[^/]*|Mobile Documents|Library/CloudStorage|Dropbox|Google Drive)(/|$)",
                    re.I)                          # local only: a vault never lives in a synced folder


class UpdateError(Exception):
    pass


# ── Engine and data ──────────────────────────────────────────────────────────

def under(path, entries):
    """True if the vault-relative path is one of the entries or inside one of them."""
    return any(path == e or path.startswith(e + "/") for e in entries)


def is_engine(path):
    """Whether a vault path is engine (replaced by an update) rather than data, or one of the merged files."""
    return (under(path, paths.ENGINE) and not under(path, paths.DATA)) or path in paths.ENGINE_MERGED


def engine_files(root=None):
    """Engine files present in a vault (not the merged ones), vault-relative, sorted."""
    root = Path(root or paths.ROOT)
    out = []
    for entry in paths.ENGINE:
        p = root / entry
        found = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file()) if p.is_dir() else []
        out += [q.relative_to(root).as_posix() for q in found]
    return sorted(f for f in out if not SKIP.search(f) and is_engine(f) and f not in paths.ENGINE_MERGED)


def sha256(data):
    """The SHA-256 of some bytes, as hex."""
    return hashlib.sha256(data).hexdigest()


def version_tuple(v):
    """A version such as 1.2.0 as a tuple of numbers, for comparing; raises UpdateError if it isn't one."""
    if not VERSION_RE.match(v or ""):
        raise UpdateError(f"Not a version number: {v!r} (expected e.g. 1.2.0).")
    return tuple(int(x) for x in v.split("."))


def installed_version():
    """The installed creaite version from VERSION, or 0.0.0 when there is none."""
    return paths.VERSION_FILE.read_text(encoding="utf-8").strip() if paths.VERSION_FILE.exists() else "0.0.0"


# ── Settings merge ───────────────────────────────────────────────────────────

def merge_new(current, incoming, prefix=""):
    """Add keys from incoming that current lacks (recursively); never change an existing value. Returns added keys."""
    added = []
    for k, v in incoming.items():
        if k not in current:
            current[k] = v
            added.append(prefix + k)
        elif isinstance(current[k], dict) and isinstance(v, dict):
            added += merge_new(current[k], v, prefix + k + ".")
    return added


# Rules creaite once shipped in .claude/settings.json and has since retired: an update removes exactly these from an existing
# vault (and only while the new release no longer ships them). Anything else in the file, Alan's own rules included, is kept.
RETIRED_RULES = {"deny": ["Write(.claude/settings.json)", "Write(.claude/settings.local.json)"],     # v1.2.0: Edit(...) already covers file edits
                 "allow": ["Bash(rm system/staging/drafts/sweep.json)", "Bash(rm system/staging/drafts/calendar.json)"]}   # v1.3.0: the staging commands delete their own inputs (BL-118)


def merge_permissions(current, incoming):
    """Claude Code settings: add new allow and deny rules, keep Alan's own, remove the rules creaite has retired; other new
    keys added. Returns the changes ("allow: rule" added, "retired deny: rule" removed)."""
    added = []
    cur, inc = current.setdefault("permissions", {}), incoming.get("permissions", {})
    for kind, rules in RETIRED_RULES.items():
        for rule in rules:
            if rule in cur.get(kind, []) and rule not in inc.get(kind, []):
                cur[kind].remove(rule)
                added.append(f"retired {kind}: {rule}")
    for kind in ("allow", "deny", "ask"):
        have = cur.setdefault(kind, []) if kind in inc else cur.get(kind, [])
        for rule in inc.get(kind, []):
            if rule not in have:
                have.append(rule)
                added.append(f"{kind}: {rule}")
    merge_new(current, {k: v for k, v in incoming.items() if k != "permissions"})
    return added


# ===== Backups folder (BL-112) =====
# The closed copy of the daily backup moves from _Portfolio/creaite backups to _Portfolio/99 System/creaite backups. An update only adds
# missing settings keys, so a vault that still holds the old default is moved here, and 99 System is added to its never_index list.
# Any other offsite_backup value (Alan's own) is left alone. The old folder and its copies are never touched.
OLD_BACKUP_DIR = "_Portfolio/creaite backups"
NEW_BACKUP_DIR = "_Portfolio/99 System/creaite backups"
MIGRATED = {}            # settings key -> its value before the migration (for the settings log and the preview)


def migrate_backup_folder(settings):
    """Apply the move to the parsed settings.json, in place. Returns the keys changed (none when there is nothing to do, or the
    second time round)."""
    MIGRATED.clear()
    loc = settings.get("locations")
    if not isinstance(loc, dict):
        return []
    changed = []
    saved = loc.get("offsite_backup")
    if isinstance(saved, str) and saved.strip().strip("/") == OLD_BACKUP_DIR:
        MIGRATED["locations.offsite_backup"] = saved
        loc["offsite_backup"] = NEW_BACKUP_DIR
        changed.append("locations.offsite_backup")
    skipped = loc.get("never_index")
    if isinstance(skipped, list) and "99 System" not in skipped:
        MIGRATED["locations.never_index"] = list(skipped)
        skipped.append("99 System")
        changed.append("locations.never_index")
    return changed


# ===== _Archive and zz Archive become 99 Archive (BL-09, #252) =====
# The one time an update changes a saved value (Alan, 14-10-2026; again for #252, 20-10-2026): `_Archive` or `zz Archive` in a saved
# locations.never_index becomes `99 Archive`, in its place, every other value kept. Only the setting: no folder is renamed at update
# time (Health offers that, on the approval card). paths.skipped_names() still skips both old names for one release, and _Archive
# stays on the deny lists through paths.ALWAYS_NEVER_INDEX.
OLD_ARCHIVE_NAMES, NEW_ARCHIVE_NAME = ("_Archive", "zz Archive"), "99 Archive"


def rename_archive_folder(settings):
    """Apply the rename to the parsed settings.json, in place. Returns the changed key (none the second time round)."""
    loc = settings.get("locations")
    skipped = loc.get("never_index") if isinstance(loc, dict) else None
    if not isinstance(skipped, list) or not any(n in skipped for n in OLD_ARCHIVE_NAMES):
        return []
    MIGRATED.setdefault("locations.never_index", list(skipped))
    MIGRATED["archive.renamed"] = True
    renamed = []
    for name in skipped:
        name = NEW_ARCHIVE_NAME if name in OLD_ARCHIVE_NAMES else name
        if name not in renamed:
            renamed.append(name)
    skipped[:] = renamed
    return ["locations.never_index"]


# ===== No Word label check (BL-121) =====
# Approving a draft no longer looks for a Word sensitivity label, so the setting that switched the check on goes from an existing
# vault's settings.json (logged). Only creaite's own note text is removed with it; the section goes when nothing else is in it.
RETIRED_SETTINGS = "retired setting: "
LABEL_NOTE = "Approving a draft needs Word's sensitivity label (open, save, close in Word first)"


def retire_label_setting(settings):
    """Apply the removal to the parsed settings.json, in place. Returns the changes (none the second time round)."""
    docs = settings.get("documents")
    if not isinstance(docs, dict):
        return []
    changed = []
    if "require_sensitivity_label" in docs:
        MIGRATED["documents.require_sensitivity_label"] = docs.pop("require_sensitivity_label")
        changed.append(RETIRED_SETTINGS + "documents.require_sensitivity_label")
    if docs.get("note") == LABEL_NOTE:
        MIGRATED["documents.note"] = docs.pop("note")
        changed.append(RETIRED_SETTINGS + "documents.note")
    if changed and not docs:
        del settings["documents"]
    return changed


# ===== Five themes (BL-142) =====
# creaite standard and Minimals are gone and creaite teal is now just "creaite", the default. A saved palette with any of the three
# old names becomes "creaite" (the page maps them too, so an old value opens as creaite before this runs). Any other value is Alan's.
OLD_PALETTES = ("creaite standard", "Minimals", "creaite teal")
NEW_PALETTE = "creaite"


# The brand theme's earlier name (kept only as its SHA-256, lower-cased, so the name is never written here) is now
# "Brightwater"; a saved palette with the earlier name is renamed.
RENAMED_PALETTE = ("626858e017b57b84c2c082ba464c4e9179e65647c23ed0ea9c6926bdb753f599", "Brightwater")


def retire_old_palette(settings):
    """Apply the rename to the parsed settings.json, in place. Returns the changed key (none the second time round)."""
    dash = settings.get("dashboard")
    pal = dash.get("palette") if isinstance(dash, dict) else None
    if isinstance(pal, str) and hashlib.sha256(pal.lower().encode("utf-8")).hexdigest() == RENAMED_PALETTE[0]:
        MIGRATED["dashboard.palette.renamed"] = RENAMED_PALETTE[1]
        dash["palette"] = RENAMED_PALETTE[1]
        return ["dashboard.palette"]
    if isinstance(dash, dict) and dash.get("palette") in OLD_PALETTES:
        MIGRATED["dashboard.palette"] = dash["palette"]
        dash["palette"] = NEW_PALETTE
        return ["dashboard.palette"]
    return []


def migration_note():
    """What the migration changes, in words, for the update's preview ('' when nothing)."""
    lines = []
    if "dashboard.palette" in MIGRATED:
        lines.append(f"The theme {MIGRATED['dashboard.palette']} is retired: your saved theme becomes {NEW_PALETTE}.")
    if "dashboard.palette.renamed" in MIGRATED:
        lines.append(f"Your saved theme is renamed {MIGRATED['dashboard.palette.renamed']}; it looks the same.")
    if "documents.require_sensitivity_label" in MIGRATED:
        lines.append("A draft is approved without any Word sensitivity label: the setting documents.require_sensitivity_label is removed.")
    if "locations.offsite_backup" in MIGRATED:
        lines.append(f"The backup copy moves to {NEW_BACKUP_DIR} (it was {MIGRATED['locations.offsite_backup']}). "
                     "The old folder and its copies stay where they are.")
    if "locations.never_index" in MIGRATED and "99 System" not in MIGRATED["locations.never_index"]:
        lines.append("99 System is added to the folders creaite never lists, indexes or reads (locations.never_index).")
    if "archive.renamed" in MIGRATED:                     # BL-09, #252
        lines.append("The archive folder's name is now 99 Archive in the folders creaite never lists, indexes or reads "
                     "(locations.never_index); every other value is kept. No folder is renamed: folders still called "
                     "_Archive or zz Archive keep working and stay skipped, and Settings › Health offers to rename them.")
    return ("\n\n" + "\n".join(lines)) if lines else ""


def merged_changes(rel, current_text, incoming_text):
    """The merged text and what it adds, for one of the merged files."""
    current = json.loads(current_text) if current_text else {}
    incoming = json.loads(incoming_text)
    added = merge_permissions(current, incoming) if rel == ".claude/settings.json" else merge_new(current, incoming)
    if rel == "system/config/settings.json":
        added += migrate_backup_folder(current)          # BL-112 (clears MIGRATED first)
        added += retire_label_setting(current)           # BL-121
        added += retire_old_palette(current)             # BL-142
        added += [k for k in rename_archive_folder(current) if k not in added]    # BL-09
    return json.dumps(current, indent=2, ensure_ascii=False) + "\n", added


# ── Inspect ──────────────────────────────────────────────────────────────────

def read_release(zip_path):
    """Open and check a release zip; return (manifest, {path: bytes}). Raises UpdateError on anything wrong."""
    try:
        z = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as e:
        raise UpdateError(f"Can't open {Path(zip_path).name} as a zip ({e}).")
    with z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        if paths.RELEASE_MANIFEST not in names:
            raise UpdateError(f"{Path(zip_path).name} isn't a creaite release: it has no {paths.RELEASE_MANIFEST}. "
                              "GitHub's \"Source code (zip)\" is the whole repository; download creaite-X.Y.Z.zip.")
        manifest = json.loads(z.read(paths.RELEASE_MANIFEST))
        if manifest.get("product") != "creaite":
            raise UpdateError(f"{Path(zip_path).name} isn't a creaite release.")
        version_tuple(manifest.get("version"))
        files = manifest.get("files") or {}
        stray = [n for n in names if n != paths.RELEASE_MANIFEST and n not in files]
        missing = [n for n in files if n not in names]
        unsafe = [n for n in names + list(files) if n not in (paths.RELEASE_MANIFEST, BOOTSTRAP) and
                  (n.startswith("/") or "\\" in n or ".." in n.split("/") or not is_engine(n))]
        if stray or missing or unsafe:
            raise UpdateError("Refused: the zip doesn't match its manifest or reaches outside the engine ("
                              + "; ".join(f"{label}: {', '.join(sorted(set(v))[:5])}" for label, v in
                                          (("not listed", stray), ("missing", missing), ("outside the engine", unsafe))
                                          if v) + ").")
        if "VERSION" not in files or z.read("VERSION").decode("utf-8").strip() != manifest["version"]:
            raise UpdateError("Refused: the zip's VERSION file doesn't match its manifest.")
        content = {}
        for n, digest in files.items():
            data = z.read(n)
            if sha256(data) != digest:
                raise UpdateError(f"Refused: {n} doesn't match its checksum; the zip is damaged or was changed. "
                                  "Download it again.")
            content[n] = data
    content.pop(BOOTSTRAP, None)                   # checked like the rest, but never installed
    return manifest, content


def plan(zip_path, reinstall=False):
    """What installing this zip would change. Raises UpdateError if it can't be installed."""
    manifest, content = read_release(zip_path)
    old, new = installed_version(), manifest["version"]
    if version_tuple(new) <= version_tuple(old) and not reinstall:
        which = "the version installed" if new == old else f"older than the installed {old}"
        raise UpdateError(f"creaite {new} is {which}. Say \"reinstall\" to install it anyway.")
    root = paths.ROOT
    have = set(engine_files())
    incoming = {n for n in content if n not in paths.ENGINE_MERGED}
    added = sorted(incoming - have)
    replaced = sorted(n for n in incoming & have if (root / n).read_bytes() != content[n])
    shipped = installed_files()          # only files an earlier release shipped are removed; Alan's own stay
    removed = sorted((have - incoming) & shipped)
    left = sorted(have - incoming - shipped)
    settings = {}
    for rel in paths.ENGINE_MERGED:
        if rel in content:
            target = root / rel
            _, adds = merged_changes(rel, target.read_text(encoding="utf-8") if target.exists() else "",
                                     content[rel].decode("utf-8"))
            if adds:
                settings[rel] = adds
    return {"from": old, "to": new, "released": manifest.get("released", ""), "notes": (manifest.get("notes", "") + migration_note()).strip(),
            "added": added, "replaced": replaced, "removed": removed, "left": left,
            "unchanged": len(incoming & have) - len(replaced), "settings": settings}, content


def installed_files():
    """Engine files the installed release shipped (empty before the first update)."""
    return set(json.loads(INSTALLED.read_text(encoding="utf-8"))["files"]) if INSTALLED.exists() else set()


# ── Backup, restore ──────────────────────────────────────────────────────────

def copy_db(src, dest):
    """Copy a SQLite database with SQLite's backup, so the copy is consistent."""
    a, b = sqlite3.connect(src), sqlite3.connect(dest)
    with b:
        a.backup(b)
    a.close()
    b.close()


def db_digest():
    """The SHA-256 of tracker.db, or '' when there is none; tells undo whether the database changed."""
    return sha256(paths.DB.read_bytes()) if paths.DB.exists() else ""


def back_up(old, new):
    """Back up the engine, merged files and database before an update, to system/backups/update-<time>-<old>-to-<new>/,
    with its record in update.json. Returns (folder, record).
    """
    stamp = datetime.now()
    dest = paths.free_path(paths.BACKUPS, f"update-{stamp:%Y-%m-%d-%H%M%S}-{old}-to-{new}")   # BL-266
    files = engine_files() + [m for m in paths.ENGINE_MERGED if (paths.ROOT / m).exists()]
    for rel in files:
        (dest / "engine" / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(paths.ROOT / rel, dest / "engine" / rel)
    if paths.DB.exists():
        copy_db(paths.DB, dest / "tracker.db")
    if INSTALLED.exists():
        shutil.copy2(INSTALLED, dest / INSTALLED.name)
    record = {"from": old, "to": new, "at": stamp.strftime("%Y-%m-%d %H:%M:%S"), "files": files,
              "database": paths.DB.exists(), "db_after": "", "undone": ""}
    (dest / "update.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return dest, record


def restore(backup, record, database=True):
    """Put the engine, the merged files and (optionally) the database back as they were in the backup."""
    keep = set(record["files"])
    for rel in engine_files():
        if rel not in keep:
            (paths.ROOT / rel).unlink()
    for rel in keep:
        (paths.ROOT / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup / "engine" / rel, paths.ROOT / rel)
    for rel in paths.ENGINE_MERGED:
        if rel not in keep and (paths.ROOT / rel).exists():
            (paths.ROOT / rel).unlink()
    if database and record["database"]:
        copy_db(backup / "tracker.db", paths.DB)
    if (backup / INSTALLED.name).exists():
        shutil.copy2(backup / INSTALLED.name, INSTALLED)
    elif INSTALLED.exists():
        INSTALLED.unlink()
    prune_empty_dirs()


def prune_empty_dirs():
    """Remove the folders an update left empty inside the engine."""
    for entry in paths.ENGINE:
        top = paths.ROOT / entry
        if top.is_dir():
            for d in sorted((d for d in top.rglob("*") if d.is_dir()), key=lambda d: len(d.parts), reverse=True):
                if not any(d.iterdir()):
                    d.rmdir()


def last_update():
    """(backup folder, record) of the latest update not yet undone, or (None, None)."""
    for d in sorted(paths.BACKUPS.glob("update-*"), reverse=True) if paths.BACKUPS.is_dir() else []:
        rec_path = d / "update.json"
        if rec_path.exists():
            record = json.loads(rec_path.read_text(encoding="utf-8"))
            if not record.get("undone"):
                return d, record
    return None, None


# ── Install ──────────────────────────────────────────────────────────────────

def run_script(script, *args):
    """Run a creaite script in this vault; (exit code, its output)."""
    r = subprocess.run([sys.executable, str(paths.ROOT / "system" / "scripts" / script), *args],
                       cwd=paths.ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def log_settings(rel, adds, version):
    """Log the settings an update added or retired to system/config/settings-log.jsonl."""
    if rel != "system/config/settings.json" or not adds:
        return
    data = json.loads(paths.SETTINGS.read_text(encoding="utf-8"))
    at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(paths.SETTINGS_LOG, "a", encoding="utf-8") as f:
        for key in adds:
            if key.startswith(RETIRED_SETTINGS):                       # a setting that went: its old value and nothing new
                gone = key[len(RETIRED_SETTINGS):]
                f.write(json.dumps({"at": at, "key": gone, "old": MIGRATED.get(gone), "new": None, "by": f"update {version}"}) + "\n")
                continue
            node = data
            for part in key.split("."):
                node = node[part]
            f.write(json.dumps({"at": at, "key": key, "old": MIGRATED.get(key), "new": node, "by": f"update {version}"}) + "\n")


# ===== The new engine finishes its own update (v1.3.0) =====
# An update is run by the update.py already installed, so a migration added to a newer update.py never ran during the update
# that brought it (1.1.0 to 1.2.0 missed BL-112's move, 1.2.0 to 1.3.0 would miss BL-118 and BL-121). tidy() applies the
# current engine's migrations to the vault as it is; every installer runs tracker.py migrate from the new engine, which calls it.

def tidy():
    """Retire the rules and settings this engine no longer ships, and apply its settings migrations. Returns the changes
    (none the second time round, and none in the development repository). The update's own backup covers undo."""
    if (paths.ROOT / ".creaite-dev").exists():
        return []
    changes = []
    if wrapper_executable():                                  # BL-237: an older update.py wrote the wrapper without its bit
        changes.append(f"made {WRAPPER} executable")
    if paths.CLAUDE_SETTINGS.exists():
        data = json.loads(paths.CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        perms, gone = data.get("permissions") or {}, []
        for kind, rules in RETIRED_RULES.items():
            for rule in rules:
                while rule in perms.get(kind, []):
                    perms[kind].remove(rule)
                    if f"retired {kind}: {rule}" not in gone:
                        gone.append(f"retired {kind}: {rule}")
        if gone:
            paths.CLAUDE_SETTINGS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            changes += gone
    if paths.SETTINGS.exists():
        data = json.loads(paths.SETTINGS.read_text(encoding="utf-8"))
        adds = migrate_backup_folder(data)                  # clears MIGRATED first
        adds += retire_label_setting(data)
        adds += retire_old_palette(data)                    # BL-142
        adds += [k for k in rename_archive_folder(data) if k not in adds]       # BL-09
        if adds:
            paths.SETTINGS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            log_settings("system/config/settings.json", adds, installed_version())
            changes += adds
    return changes


# ===== BL-320 (v192-fixit): the steps after an update, done by update.py itself (Alan, 14-10-2026) =====
# After the update Alan approved, the new engine's launch.py makes this vault's launchers again (only those that already open
# this vault), points the app's manifest at new icon addresses (so Chrome refreshes its copy of the icon) and asks the running
# live server to restart once it is free. Each is reported; a step that fails rolls the whole update back.
AFTER_STEPS = ((("launch.py", "make-launcher", "--if-present"), "Launcher"),
               (("launch.py", "refresh-icon"), "App icon"),
               (("launch.py", "restart"), "Live server"))


def after_update():
    """Run AFTER_STEPS in order; returns one line per step. Raises UpdateError at the first that fails."""
    said = []
    for cmd, label in AFTER_STEPS:
        code, out = run_script(*cmd)
        last = (out.splitlines() or [""])[-1]
        if code:
            raise UpdateError(f"{label}: {' '.join(cmd)} failed: {last or 'no output'}")
        said.append(f"{label}: {last or 'done.'}")
    return said


def restart_hint(notes):
    """The words after the backup line: none when the after-update steps restarted the running live server, else ask Alan to."""
    restarted = any(n.startswith("Live server: The live server on port") for n in notes)
    return "" if restarted else " Restart the live server to use the new version."
# ===== end BL-320 =====


def install(zip_path, reinstall=False):
    """Install a release zip (BL-36): back up, replace the engine, merge new settings and permission rules, migrate
    the database, rebuild the dashboard and Excel export and run doctor. Rolls back by itself if a step fails; keeps
    the zip in system/releases/. An older or equal version needs `reinstall`. Returns (plan, backup, notes).
    """
    if (paths.ROOT / ".creaite-dev").exists():
        raise UpdateError("This is the development repository: use git here, not update.py.")
    p, content = plan(zip_path, reinstall)
    paths.BACKUPS.mkdir(parents=True, exist_ok=True)
    backup, record = back_up(p["from"], p["to"])
    notes = []
    try:
        for rel in p["removed"]:
            (paths.ROOT / rel).unlink()
        for rel, data in content.items():
            if rel in paths.ENGINE_MERGED:
                continue
            (paths.ROOT / rel).parent.mkdir(parents=True, exist_ok=True)
            (paths.ROOT / rel).write_bytes(data)
        prune_empty_dirs()
        wrapper_executable()                                  # BL-237
        for rel in paths.ENGINE_MERGED:
            if rel in content:
                target = paths.ROOT / rel
                text, adds = merged_changes(rel, target.read_text(encoding="utf-8") if target.exists() else "",
                                            content[rel].decode("utf-8"))
                if adds or not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(text, encoding="utf-8")
                    log_settings(rel, adds, p["to"])
        steps = ([("tracker.py", "migrate")] if paths.DB.exists() else []) + [("build_dashboard.py",)]
        for step in steps:
            code, out = run_script(*step)
            if code:
                raise UpdateError(f"{' '.join(step)} failed: {out.splitlines()[-1] if out else 'no output'}")
        if paths.DB.exists():
            code, out = run_script("excel_sync.py", "export")
            if code:
                notes.append("Excel export skipped: " + (out.splitlines()[-1] if out else "it failed")
                             + " Run it again after importing.")
        code, out = run_script("doctor.py")
        failed = [l for l in out.splitlines() if l.startswith("FAIL")]
        split = [l for l in failed if "creaite rules imported" in l]   # an older vault: cx-setup splits CLAUDE.md
        if split:
            notes.append("Your CLAUDE.md doesn't import system/creaite-rules.md yet; say \"setup\" to split it "
                         "(shown first, your own lines kept).")
        if "settings.json still lists" in out:     # BL-55: the old people lists move into the register once
            notes.append("Your people list is still in settings.json; say \"setup\" to move it into the people "
                         "register (shown first, then applied).")
        if code and (len(failed) > len(split) or not failed):
            raise UpdateError("doctor.py failed after the update: "
                              + "; ".join([l for l in failed if l not in split] or out.splitlines()[-1:]))
        notes += after_update()                               # BL-320: a failed step raises, and the update rolls back
    except Exception as e:
        restore(backup, record)
        run_script("build_dashboard.py")
        record["undone"] = "rolled back during install"
        (backup / "update.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        raise UpdateError(f"The update didn't install, and creaite {p['from']} has been restored. {e}") from e
    record["db_after"] = db_digest()
    (backup / "update.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    paths.RELEASES.mkdir(parents=True, exist_ok=True)
    kept = paths.RELEASES / Path(zip_path).name
    if not kept.exists():
        shutil.copy2(zip_path, kept)
    INSTALLED.write_text(json.dumps({"version": p["to"], "released": p["released"], "zip": kept.name,
                                     "files": sorted(n for n in content if n not in paths.ENGINE_MERGED)},
                                    indent=2) + "\n", encoding="utf-8")
    return p, paths.rel(backup), notes


def undo(keep_database=False):
    """Restore the engine, settings and database from the last update's backup (BL-36). Refused if the database
    has changed since, unless `keep_database` (engine and settings only). Rebuilds the dashboard.
    """
    backup, record = last_update()
    if not backup:
        raise UpdateError("There's no update to undo.")
    database = record["database"]
    if database and record["db_after"] and db_digest() != record["db_after"]:
        if not keep_database:
            raise UpdateError("The database has changed since the update, and undoing it would lose those changes. "
                              "Undo with --keep-database to restore only the engine and settings.")
        database = False
    restore(backup, record, database=database and not keep_database)
    code, out = run_script("build_dashboard.py")
    record["undone"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    (backup / "update.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record, database and not keep_database, code == 0


# ── Find ─────────────────────────────────────────────────────────────────────

def newest_zip(folder):
    """(version, path) of the newest creaite-X.Y.Z.zip in a folder, or None."""
    best = None
    for z in folder.glob("creaite-*.zip") if folder.is_dir() else []:
        m = re.fullmatch(r"creaite-(\d+\.\d+\.\d+)\.zip", z.name)
        if m and (best is None or version_tuple(m.group(1)) > version_tuple(best[0])):
            best = (m.group(1), z)
    return best


# ===== BL-237 (sprint-portability): the wrapper must be executable =====
# A zip doesn't carry the execute bit through Python's zipfile, so whoever writes the engine sets it: install, new-vault, and
# tidy (run by tracker.py migrate, so an update done by an older update.py gets it too). Owner, group and others may run it;
# nobody new may write it.
WRAPPER = "system/scripts/run"


def wrapper_executable(root=None):
    """Set the wrapper's execute bits; returns True when it changed anything. Nothing on Windows, or without a wrapper."""
    w = Path(root or paths.ROOT) / WRAPPER
    if os.name == "nt" or not w.is_file():
        return False
    mode = w.stat().st_mode
    if mode & 0o111 == 0o111:
        return False
    w.chmod((mode | 0o555) & 0o7755)
    return True
# ===== end BL-237 =====

# ===== BL-238 (sprint-portability): fetch a release with gh =====
# Inbound only: gh downloads the published zip into system/releases/; nothing is sent. The zip is checked exactly as a hand
# download is (read_release: its manifest and every file's SHA-256) before it is kept, and installing it stays a separate,
# confirmed step. gh runs only from here, so ask creaite's rule is still one creaite script run on its own (BL-141).
RELEASE_REPO = "insyncalan/creaite"
GH_FALLBACKS = ("~/homebrew/bin/gh", "/opt/homebrew/bin/gh", "/usr/local/bin/gh")     # a launchd or app PATH can miss Homebrew
GH_TIMEOUT = 300
MANUAL = ("Download creaite-X.Y.Z.zip by hand instead: open https://github.com/" + RELEASE_REPO + "/releases, download the "
          "attached creaite-X.Y.Z.zip (not \"Source code\") into system/releases/, then say \"update creaite\".")


def gh_path():
    """Where the GitHub CLI is (on the PATH or a usual install place), or None (BL-238)."""
    found = shutil.which("gh")
    if found:
        return found
    for c in GH_FALLBACKS:
        p = Path(c).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    return None


def newest_tag(releases):
    """BL-280: the highest vX.Y.Z tag among gh's release list (pre-releases included, drafts and other tags left out), or None.
    Every creaite release up to 1.7.0 is a pre-release, which `gh release download` with no tag never picks."""
    tags = [r.get("tagName") for r in releases if isinstance(r, dict) and not r.get("isDraft")]
    tags = [t for t in tags if isinstance(t, str) and re.fullmatch(r"v\d+\.\d+\.\d+", t)]
    return max(tags, key=lambda t: tuple(int(x) for x in t[1:].split(".")), default=None)


def latest_tag(gh):
    """BL-280: ask gh for the releases and return the newest one's tag, pre-releases included."""
    cmd = [gh, "release", "list", "--repo", RELEASE_REPO, "--exclude-drafts", "--limit", "100", "--json", "tagName,isDraft,isPrerelease"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise UpdateError(f"gh didn't list the releases ({type(e).__name__}). " + MANUAL) from e
    if r.returncode != 0:
        said = ((r.stderr or r.stdout).strip().splitlines() or ["no output"])[-1][:200]
        raise UpdateError(f"gh couldn't list the releases ({said}). " + MANUAL)
    try:
        tag = newest_tag(json.loads(r.stdout or "[]"))
    except ValueError:
        tag = None
    if not tag:
        raise UpdateError("No creaite release was found on GitHub. " + MANUAL)
    return tag


def fetch(tag=None):
    """Download a release zip with gh into system/releases/ and check it. Returns {version, path, installed, newer, kept}."""
    if tag is not None and not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise UpdateError(f"{tag} isn't a release tag: name one like v1.6.1, or leave it out for the newest.")
    gh = gh_path()
    if not gh:
        raise UpdateError("The GitHub command-line tool (gh) isn't installed, so creaite can't fetch the release itself. " + MANUAL)
    try:
        auth = subprocess.run([gh, "auth", "status"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise UpdateError(f"gh didn't answer ({type(e).__name__}). " + MANUAL)
    if auth.returncode != 0:
        raise UpdateError("gh is installed but not signed in to GitHub (run gh auth login in Terminal once). " + MANUAL)
    if tag is None:
        tag = latest_tag(gh)                                  # BL-280: the newest, pre-releases included, then that tag
    paths.RELEASES.mkdir(parents=True, exist_ok=True)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix=".fetch-", dir=paths.RELEASES))
    try:
        cmd = [gh, "release", "download", tag, "--repo", RELEASE_REPO, "--pattern", "creaite-*.zip",
               "--dir", str(tmp)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=GH_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise UpdateError(f"gh release download didn't finish ({type(e).__name__}). " + MANUAL)
        if r.returncode != 0:
            said = ((r.stderr or r.stdout).strip().splitlines() or ["no output"])[-1][:200]
            raise UpdateError(f"gh couldn't download the release ({said}). " + MANUAL)
        got = [z for z in tmp.iterdir() if re.fullmatch(r"creaite-\d+\.\d+\.\d+\.zip", z.name)]
        if len(got) != 1 or any(x not in got for x in tmp.iterdir()):
            raise UpdateError("The release didn't hold exactly one creaite-X.Y.Z.zip, so nothing was kept. " + MANUAL)
        manifest, _ = read_release(got[0])                    # its manifest and every checksum, as for a hand download
        if got[0].name != f"creaite-{manifest['version']}.zip":
            raise UpdateError(f"{got[0].name} holds creaite {manifest['version']}, so it wasn't kept.")
        if tag and tag != f"v{manifest['version']}":
            raise UpdateError(f"The {tag} release holds creaite {manifest['version']}, so it wasn't kept.")
        dest = paths.RELEASES / got[0].name
        kept = not dest.exists()
        if kept:
            os.replace(got[0], dest)
        elif dest.read_bytes() != got[0].read_bytes():
            raise UpdateError(f"system/releases/{dest.name} is already there and differs from the published one. Remove it, "
                              "or check where it came from, then fetch again.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    installed = installed_version()
    return {"version": manifest["version"], "path": paths.rel(dest), "installed": installed,
            "newer": version_tuple(manifest["version"]) > version_tuple(installed), "kept": kept}
# ===== end BL-238 =====


# ── New vault ────────────────────────────────────────────────────────────────

STARTING_FILES = {                                 # vault path: template in system/templates/ (or text)
    "CLAUDE.md": "vault-CLAUDE-template.md",
    "projects/_portfolio/project-register.md": "project-register-template.md",
    "projects/_portfolio/people-register.md": "people-register-template.md",
    "projects/_portfolio/PORTFOLIO.md": "portfolio-template.md",
    "system/config/schedules.md": "schedules-template.md",
    ".gitignore": "vault-gitignore",
}
NEW_FOLDERS = ("inbox", "projects/_portfolio/minutes", "projects/_portfolio/transcripts", "system/staging/drafts",
               "system/staging/applied", "system/staging/ask", "system/history", "system/backups", "system/releases",
               "system/search", "system/config")


def vault_folder(folder):
    """The folder a new vault goes in, checked: empty or new, and not in a synced folder."""
    target = Path(folder).expanduser().resolve()
    if SYNCED.search(target.as_posix()):
        raise UpdateError(f"{target} is in a synced folder (OneDrive, iCloud or similar). creaite keeps all data on "
                          "this laptop only: choose a folder outside it, for example ~/creaite.")
    if target.exists() and (not target.is_dir() or any(p.name != ".DS_Store" for p in target.iterdir())):
        raise UpdateError(f"{target} already exists and isn't empty. Choose a new folder, or an empty one; to update "
                          "an existing vault, say \"update creaite\" in it instead.")
    return target


def projects_folder_check(folder):
    """The projects folder for a new vault: a plain local folder or the company OneDrive, reachable; never personal cloud storage."""
    import locations
    r = locations.check(folder)
    if r["refuse"]:
        raise UpdateError(f"{folder}: {r['refuse']}")
    if not r["exists"]:
        raise UpdateError(f"{folder} isn't reachable. Is OneDrive running and signed in? Create the folder first, or leave the "
                          "projects folder out and keep projects inside the vault.")
    return Path(folder).expanduser().resolve(), r


def new_vault(zip_path, folder, projects_folder=None):
    """Create a new vault from a release zip. Returns (version, folder, doctor output). Leaves nothing behind on failure.
    projects_folder (BL-85): where the projects live instead of the vault's projects/ folder (the portfolio folder is made there)."""
    target = vault_folder(folder)
    proj = projects_folder_check(projects_folder)[0] if projects_folder else None
    manifest, content = read_release(zip_path)
    existed = target.exists()
    made = []                                          # what was created outside the vault, to take away again on failure
    try:
        for rel, data in content.items():
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            (target / rel).write_bytes(data)
        wrapper_executable(target)                            # BL-237
        cfg_path = target / "system" / "config" / "settings.json"
        loc = json.loads(cfg_path.read_text(encoding="utf-8")).get("locations") or {}
        if proj:
            import locations
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            cfg.setdefault("locations", {})["projects_root"] = locations.tilde(proj)
            cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            portfolio = proj / (loc.get("portfolio") or "_Portfolio")
            folders = loc.get("folders") or {}
        for d in NEW_FOLDERS:
            if proj and d.startswith("projects/_portfolio"):
                kind = d.rsplit("/", 1)[1]                  # minutes or transcripts: the mapped folders, in the portfolio folder
                d = None
                for p in (portfolio / (folders.get(kind) or kind),):
                    if not p.exists():
                        p.mkdir(parents=True)
                        made.append(p)
                continue
            (target / d).mkdir(parents=True, exist_ok=True)
        templates = target / "system" / "templates"
        for rel, tpl in STARTING_FILES.items():
            dest = target / rel
            if proj and rel.startswith("projects/_portfolio/"):
                dest = portfolio / rel.rsplit("/", 1)[1]
                if dest.exists():
                    continue                                # an existing portfolio folder keeps its own files
                made.append(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text((templates / tpl).read_text(encoding="utf-8"), encoding="utf-8")
        (target / "system" / "processed.txt").write_text("# date processed | file path | items created\n",
                                                          encoding="utf-8")
        kept = target / "system" / "releases" / Path(zip_path).name
        shutil.copy2(zip_path, kept)
        (target / "system" / "releases" / INSTALLED.name).write_text(json.dumps(
            {"version": manifest["version"], "released": manifest.get("released", ""), "zip": kept.name,
             "files": sorted(n for n in content if n not in paths.ENGINE_MERGED)}, indent=2) + "\n", encoding="utf-8")

        def run(script, *args):
            """Run a script in the new vault; raises UpdateError if it fails."""
            r = subprocess.run([sys.executable, str(target / "system" / "scripts" / script), *args], cwd=target,
                               capture_output=True, text=True)
            out = (r.stdout + r.stderr).strip()
            if r.returncode:
                raise UpdateError(f"{script} {' '.join(args)} failed: {out.splitlines()[-1] if out else 'no output'}")
            return out
        run("tracker.py", "init")
        run("tracker.py", "index")
        run("build_dashboard.py")
        report = run("doctor.py")
    except BaseException:
        if existed:
            for p in target.iterdir():
                shutil.rmtree(p) if p.is_dir() else p.unlink()
        else:
            shutil.rmtree(target, ignore_errors=True)
        for p in reversed(made):                           # nothing left behind in the projects folder either
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        raise
    return manifest["version"], target, report


def ask_folder():
    """Ask in Terminal which folder to make the vault in (default ~/creaite)."""
    default = Path.home() / "creaite"
    if not sys.stdin.isatty():
        raise UpdateError("Say which folder to create the vault in, e.g. ~/creaite.")
    answer = input(f"Folder for your creaite vault [{default}]: ").strip()
    return answer or str(default)


def ask_projects_folder():
    """Optional: where the projects live (asked only at a terminal). Empty keeps them inside the vault."""
    if not sys.stdin.isatty():
        return None
    answer = input("Projects folder (the company OneDrive's Engagements folder), or press Enter to keep projects inside the vault: ").strip()
    return answer or None


def new_vault_cli(zip_path, folder=None, projects=None):
    """Create a new, empty vault from a release zip and print the next steps; asks for the folders left out."""
    try:
        version, target, report = new_vault(zip_path, folder or ask_folder(), projects if projects is not None else ask_projects_folder())
    except UpdateError as e:
        print(e, file=sys.stderr)
        return 1
    warnings = [ln for ln in report.splitlines() if ln.startswith("WARN")]
    print(f"Created a creaite {version} vault in {target}.")
    for w in warnings:
        print(w)
    print("Next:\n  1. Open that folder in Claude Code (or the Code tab of the Claude app) and say \"setup\": it asks"
          " before each step (git, your name, Microsoft 365, your projects and people, memory files).\n"
          f"  2. Start the live server: cd \"{target}\" && system/scripts/run live_server.py\n"
          "  3. Open the address it prints. The dashboard is empty until your first projects and sweep.")
    return 0


def shown(d):
    """A YYYY-MM-DD date as DD-MM-YYYY; anything else unchanged."""
    return f"{d[8:10]}-{d[5:7]}-{d[0:4]}" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d or "") else d


# ── Commands ─────────────────────────────────────────────────────────────────

def main(argv):
    """Run the update command in `argv` (see the module docstring)."""
    cmd, args = (argv[0], argv[1:]) if argv else ("", [])
    try:
        if cmd == "version":
            print(f"creaite {installed_version()}")
            return 0
        if cmd == "find":
            found = {}
            for label, folder in (("releases", paths.RELEASES), ("downloads", Path.home() / "Downloads")):
                hit = newest_zip(folder)
                found[label] = {"version": hit[0], "path": str(hit[1])} if hit else None
            print(json.dumps({"installed": installed_version(), **found}, indent=2))
            return 0
        if cmd == "fetch" and len(args) <= 1:            # BL-238
            print(json.dumps(fetch(args[0] if args else None), indent=2))
            return 0
        if cmd == "inspect" and len(args) in (1, 2):
            p, _ = plan(args[0], reinstall="--reinstall" in args)
            print(json.dumps({**p, "released": shown(p["released"])}, indent=2))
            return 0
        if cmd == "install" and len(args) in (1, 2):
            p, backup, notes = install(args[0], reinstall="--reinstall" in args)
            print(f"Installed creaite {p['to']} (was {p['from']}): {len(p['replaced'])} files replaced, "
                  f"{len(p['added'])} added, {len(p['removed'])} removed.")
            if p["left"]:
                print(f"Left in place (not from a release): {', '.join(p['left'])}")
            for rel, adds in p["settings"].items():
                print(f"{rel}: added {', '.join(adds)}")
            for n in notes:
                print(n)
            print(f"Backup: {backup}." + restart_hint(notes))
            return 0
        if cmd == "new-vault" and args:
            rest, projects = list(args), None
            if "--projects" in rest:
                i = rest.index("--projects")
                projects = rest[i + 1] if i + 1 < len(rest) else ""
                del rest[i:i + 2]
            if 1 <= len(rest) <= 2 and projects != "":
                return new_vault_cli(*rest, projects=projects)       # projects None: asked for at a terminal, else left out
        if cmd == "tidy" and not args:
            changes = tidy()
            print("Tidied after the update: " + "; ".join(changes) if changes else "Nothing to tidy.")
            if {"documents.require_sensitivity_label", "locations.offsite_backup", "archive.renamed"} & set(MIGRATED):
                print(migration_note().strip())
            return 0
        if cmd == "undo" and len(args) <= 1:
            record, db, built = undo(keep_database="--keep-database" in args)
            print(f"Undone: creaite {record['from']} restored (from {record['to']})"
                  + ("" if db else "; the database was kept as it is") + "."
                  + ("" if built else " The dashboard didn't rebuild; run build_dashboard.py.")
                  + " Restart the live server.")
            return 0
    except UpdateError as e:
        print(e, file=sys.stderr)
        return 1
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        import log as debuglog  # BL-102: the debug log (not `log`: some scripts have a function of that name); a script runs without it
    except ImportError:
        debuglog = None
    sys.exit(debuglog.main("update.py", main, sys.argv[1:]) if debuglog else main(sys.argv[1:]))
