"""Rebuild system/scripts/vendor/manifest.json (BL-239, development only).

Run: python3 dev/tools/vendor_manifest.py [--check]
Writes the SHA-256 of every file in system/scripts/vendor/ (except the manifest and __pycache__). Run it only when a
library is deliberately upgraded: replace the folder, run this, run doctor.py, and commit the library and the manifest
together. --check writes nothing and exits 1 if the folder doesn't match (what doctor.py's check does).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import doctor  # noqa: E402
import paths  # noqa: E402


def main(argv):
    target = paths.VENDOR / doctor.VENDOR_MANIFEST
    if argv[:1] == ["--check"]:
        missing, changed, extra = doctor.vendor_problems()
        for label, names in (("missing", missing), ("changed", changed), ("extra", extra)):
            for n in names:
                print(f"{label}: {n}")
        print("vendor/ matches its manifest." if not (missing or changed or extra) else "vendor/ doesn't match its manifest.")
        return 1 if missing or changed or extra else 0
    if argv:
        print(__doc__)
        return 2
    files = doctor.vendor_files()
    target.write_text(json.dumps({"about": "SHA-256 of every bundled library file (BL-239). Rebuilt only by "
                                           "dev/tools/vendor_manifest.py when a library is deliberately upgraded.",
                                  "files": files}, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print(f"Wrote {paths.rel(target)}: {len(files)} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
