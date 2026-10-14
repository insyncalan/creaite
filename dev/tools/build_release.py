"""Build a creaite release zip (BL-36): the engine files only, with a manifest of checksums.

Usage: python3 dev/tools/build_release.py [--tag v1.2.0] [--notes notes.md] [--out DIR] [--dirty]

Takes the engine files git tracks (paths.ENGINE and paths.ENGINE_MERGED), never data, branding, .creaite-dev or the
dashboard's source (system/templates/dashboard/: the built dashboard.html goes instead, and a stale one is refused), and
writes creaite-<VERSION>.zip, with settings.json taken from system/templates/settings-defaults.json (never this repo's
own settings) and dev/tools/release_main.py as __main__.py, so the zip runs: python3 creaite-X.Y.Z.zip [folder] with creaite-release.json (version, release date, notes, the SHA-256 of every file).
--tag must match VERSION (the GitHub workflow passes the release tag). --out defaults to dev/releases/ (not in git).
Refuses uncommitted changes in engine files unless --dirty (local test builds: the working files as they are,
new ones included).
Run by .github/workflows/release.yml when a release is published on GitHub; system/scripts/update.py installs it.
"""
import argparse
import json
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(REPO / "dev" / "tools"))
import paths  # noqa: E402
import split_dashboard  # noqa: E402
import update  # noqa: E402


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def refuse_stale_dashboard():
    """BL-231 step 2a: a release carries the built dashboard.html, never one out of date with its source."""
    stale = split_dashboard.stale()
    if stale:
        raise update.UpdateError(stale)


def build(tag=None, notes="", out=None, dirty=False):
    version = paths.VERSION_FILE.read_text(encoding="utf-8").strip()
    update.version_tuple(version)
    if tag and tag != f"v{version}":
        raise update.UpdateError(f"The tag {tag} doesn't match VERSION ({version}); expected v{version}.")
    scope = list(paths.ENGINE) + list(paths.ENGINE_MERGED)
    listed = git("ls-files", "-z", *(["--cached", "--others", "--exclude-standard"] if dirty else []), "--", *scope)
    files = sorted({f for f in listed.split("\0") if f and not update.SKIP.search(f) and (REPO / f).is_file()})
    refused = [f for f in files if not update.is_engine(f) or f == ".creaite-dev" or f.startswith("system/branding/")]
    if refused:
        raise update.UpdateError("Refused: not engine files: " + ", ".join(refused))
    if "VERSION" not in files:
        raise update.UpdateError("VERSION isn't committed.")
    refuse_stale_dashboard()
    changed = git("status", "--porcelain", "--", *scope).strip()
    if changed and not dirty:
        raise update.UpdateError("Engine files have uncommitted changes; commit them first:\n" + changed)
    content = {f: (REPO / f).read_bytes() for f in files}
    # New vaults and new settings keys get clean defaults, never this repo's own trial values
    content["system/config/settings.json"] = (paths.TEMPLATES / "settings-defaults.json").read_bytes()
    content[update.BOOTSTRAP] = (REPO / "dev" / "tools" / "release_main.py").read_bytes()   # python3 <zip> [folder]
    manifest = {"product": "creaite", "version": version, "released": date.today().isoformat(),
                "notes": notes.strip(), "files": {f: update.sha256(d) for f, d in content.items()}}
    out = Path(out or REPO / "dev" / "releases")
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"creaite-{version}.zip"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in [(paths.RELEASE_MANIFEST, (json.dumps(manifest, indent=2) + "\n").encode())] + \
                          sorted(content.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if name == update.WRAPPER else 0o644) << 16    # BL-237: the wrapper runs
            z.writestr(info, data)
    return dest, manifest


def main(argv):
    ap = argparse.ArgumentParser(description="Build a creaite release zip.")
    ap.add_argument("--tag")
    ap.add_argument("--notes", help="a file with the release notes")
    ap.add_argument("--out")
    ap.add_argument("--dirty", action="store_true", help="allow uncommitted engine changes (test builds only)")
    a = ap.parse_args(argv)
    notes = Path(a.notes).read_text(encoding="utf-8") if a.notes else ""
    try:
        dest, manifest = build(a.tag, notes, a.out, a.dirty)
    except (update.UpdateError, subprocess.CalledProcessError) as e:
        print(e, file=sys.stderr)
        return 1
    print(f"Built {dest.name}: creaite {manifest['version']}, {len(manifest['files'])} files.")
    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
