"""#233 L7 (Team Cap, review of p240-h3, low): /api/fs may create a CLAUDE.md only in an existing project's own folder.

Today a write to projects/<anything>/CLAUDE.md creates the file under 99 Archive, _portfolio, a name that is no project, or a hidden
folder. This test FAILS against the current live_server.py and passes once the diff in dev/proposals/233b-fs-newfile.md is applied.
Until then it is skipped, so the suite stays green; FS_NEWFILE_FORCE=1 runs it anyway.

Run (with the diff applied): python3 dev/tests/test_fs_newfile.py
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_reports import ABC, ReportRoutes  # noqa: E402

SERVER = (Path(__file__).resolve().parents[2] / "system" / "scripts" / "live_server.py").read_text(encoding="utf-8")
APPLIED = "existing_project_folder" in SERVER or bool(os.environ.get("FS_NEWFILE_FORCE"))

def raw(case, body):
    """POST /api/fs and return (status, json) whatever the status (the shared post() raises on 4xx)."""
    import json
    import urllib.error
    import urllib.request
    req = urllib.request.Request(case.base + "/api/fs", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "X-Creaite-Token": case.token})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


@unittest.skipUnless(APPLIED, "skipped: the fs-newfile diff (dev/proposals/233b-fs-newfile.md) is not applied to live_server.py yet")
class FsNewFile(unittest.TestCase):
    setUpClass = classmethod(ReportRoutes.setUpClass.__func__)
    tearDownClass = classmethod(ReportRoutes.tearDownClass.__func__)

    def test_no_claude_md_is_created_under_an_odd_folder(self):
        root = self.v.root
        for name in ("99 Archive", "_portfolio", "nope", ".hidden", "Zzz Not A Project"):
            status, out = raw(self, {"op": "write", "path": f"projects/{name}/CLAUDE.md", "text": "# x\n"})
            self.assertFalse(out.get("ok"), (name, out))
            self.assertFalse((root / "projects" / name / "CLAUDE.md").exists(), name)

    def test_an_existing_project_file_is_still_written_and_a_missing_one_in_a_project_folder_is_created(self):
        rel = f"{ABC}/CLAUDE.md"
        f = self.v.root / rel
        now = f.read_text(encoding="utf-8")
        self.assertTrue(raw(self, {"op": "write", "path": rel, "text": now})[1]["ok"])
        f.unlink()
        self.assertTrue(raw(self, {"op": "write", "path": rel, "text": now})[1]["ok"])      # the project's own folder: allowed
        self.assertEqual(f.read_text(encoding="utf-8"), now)


if __name__ == "__main__":
    unittest.main()
