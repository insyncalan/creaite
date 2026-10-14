"""BL-256: the vendored Preact and signals (system/templates/vendor/preact/) match their manifest, the pins and licences
are recorded, and the build maps each library import to a vendored file only.

Run: python3 dev/tests/test_vendor_preact.py
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "dev" / "tools"))
import build_dashboard_js as bj  # noqa: E402
import vendor_preact as vp  # noqa: E402

MANIFEST = json.loads(vp.MANIFEST.read_text(encoding="utf-8"))


class VendoredFiles(unittest.TestCase):
    def test_every_file_matches_its_hash_and_nothing_else_is_there(self):
        self.assertEqual(vp.problems(), [])

    def test_a_changed_file_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "preact"
            for name in [*MANIFEST["files"], "manifest.json"]:
                (dest / name).parent.mkdir(parents=True, exist_ok=True)
                (dest / name).write_bytes((vp.VENDOR / name).read_bytes())
            self.assertEqual(vp.problems(dest), [])
            (dest / "preact/dist/preact.module.js").write_text("// changed\n", encoding="utf-8")
            (dest / "stray.js").write_text("", encoding="utf-8")
            self.assertEqual(vp.problems(dest), ["changed: preact/dist/preact.module.js", "extra: stray.js"])

    def test_the_manifest_is_the_pins(self):
        for pkg, (folder, version, tgz, sha, released) in vp.PINS.items():
            m = MANIFEST["packages"][pkg]
            self.assertEqual((m["folder"], m["version"], m["sha256"], m["released"], m["licence"]),
                             (folder, version, sha, released, "MIT"))
            self.assertEqual(m["tarball"], f"https://registry.npmjs.org/{pkg}/-/{tgz}")
            self.assertIn(f"{folder}/LICENSE", MANIFEST["files"])
            self.assertIn("MIT License", (vp.VENDOR / folder / "LICENSE").read_text(encoding="utf-8"))
        self.assertEqual(MANIFEST["modules"], vp.MODULES)

    def test_each_hash_is_the_file_s_sha256(self):
        for name, h in MANIFEST["files"].items():
            self.assertEqual(hashlib.sha256((vp.VENDOR / name).read_bytes()).hexdigest(), h, name)


class Build(unittest.TestCase):
    def test_the_build_maps_each_library_import_to_a_vendored_file(self):
        flags = bj.preact_flags()
        self.assertIn("--jsx=automatic", flags)
        self.assertIn("--jsx-import-source=preact", flags)
        aliases = dict(f[len("--alias:"):].split("=", 1) for f in flags if f.startswith("--alias:"))
        self.assertEqual(set(aliases), set(vp.MODULES))
        for spec, path in aliases.items():
            self.assertEqual(Path(path), vp.VENDOR / vp.MODULES[spec], spec)

    def test_signals_bundle_from_the_vendored_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "dashboard"
            (folder / "src").mkdir(parents=True)
            (folder / "src" / "main.js").write_text(
                'import { signal } from "@preact/signals";\nexport const n = signal(1);\n', encoding="utf-8")
            iife, names = bj.bundle(folder)
            self.assertEqual(names, ["n"])
            self.assertIn("vendor/preact/signals/dist/signals.module.js", iife)
            self.assertIn("vendor/preact/signals-core/dist/signals-core.module.js", iife)


if __name__ == "__main__":
    unittest.main()
