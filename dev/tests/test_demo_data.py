"""BL-292: dev/tools/demo_data.py runs end to end on a scratch vault. Its Word files are built in system/staging/drafts/
(BL-271: docx_tools.py writes nowhere else) and filed into the project folders by the demo's own apply, and purge's undo
takes them away again.

Run: python3 dev/tests/test_demo_data.py
"""
import json
import shutil
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import REPO, Vault  # noqa: E402


class DemoData(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        tools = self.v.root / "dev" / "tools"
        tools.mkdir(parents=True)
        shutil.copy2(REPO / "dev" / "tools" / "demo_data.py", tools / "demo_data.py")
        (self.v.root / ".creaite-dev").write_text("")

    def tearDown(self):
        self.v.cleanup()

    def demo(self, cmd):
        r = subprocess.run([sys.executable, str(self.v.root / "dev" / "tools" / "demo_data.py"), cmd], cwd=self.v.root,
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def projects(self):
        with closing(sqlite3.connect(self.v.root / "system" / "tracker.db")) as con:
            return {r[0] for r in con.execute("SELECT code FROM projects")}

    def test_load_files_the_word_files_through_the_apply_and_purge_removes_them(self):
        out = self.demo("load")
        self.assertIn("Demo loaded", out)
        self.assertTrue({"FAL", "ORX", "MER", "TID"} <= self.projects())
        steer = next((self.v.root / "projects").glob("FAL */minutes/* Steering committee.docx"))
        self.assertEqual(steer.read_bytes()[:2], b"PK")                       # a real Word file, in the project
        drafts = self.v.root / "system" / "staging" / "drafts"
        self.assertEqual(sorted(p.name for p in drafts.glob("demo-*.docx")), [])   # the build drafts are gone
        applied = json.loads((self.v.root / "system/staging/applied/proposed-0000-00-00-demo.json").read_text())
        ops = applied["file_changes"]["file_ops"]
        self.assertTrue(ops and all(o["op"] == "copy" and o["from"].startswith("system/staging/drafts/") for o in ops))
        self.demo("purge")
        self.assertFalse(steer.exists())
        self.assertFalse({"FAL", "ORX", "MER", "TID"} & self.projects())
        self.assertFalse(list((self.v.root / "projects").glob("FAL *")))


if __name__ == "__main__":
    unittest.main()
