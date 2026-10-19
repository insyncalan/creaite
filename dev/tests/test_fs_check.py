"""#233 L5 (Team Cap, review of p240-h3, low): /api/fs refuses a write over a file that changed since the page read it.

The page sends `expect_text` (what the file held when it read it) with a write of a project's CLAUDE.md. This test FAILS against the
current live_server.py (the write goes through) and passes once the diff in dev/proposals/233b-fs-check.md is applied. Until then it
is skipped, so the suite stays green; FS_CHECK_FORCE=1 runs it anyway.

Run (with the diff applied): python3 dev/tests/test_fs_check.py
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_reports import ABC, ReportRoutes  # noqa: E402

SERVER = (Path(__file__).resolve().parents[2] / "system" / "scripts" / "live_server.py").read_text(encoding="utf-8")
APPLIED = "expect_text" in SERVER or bool(os.environ.get("FS_CHECK_FORCE"))

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


@unittest.skipUnless(APPLIED, "skipped: the fs-check diff (dev/proposals/233b-fs-check.md) is not applied to live_server.py yet")
class FsCheck(unittest.TestCase):
    setUpClass = classmethod(ReportRoutes.setUpClass.__func__)
    tearDownClass = classmethod(ReportRoutes.tearDownClass.__func__)

    def test_a_write_over_a_changed_file_is_refused_and_a_write_over_the_same_text_goes_through(self):
        rel = f"{ABC}/CLAUDE.md"
        f = self.v.root / rel
        read = f.read_text(encoding="utf-8")
        f.write_text(read + "\nanother tab\n", encoding="utf-8")                 # the file changed after the page read it
        status, out = raw(self, {"op": "write", "path": rel, "text": read + "- mine\n", "expect_text": read})
        self.assertFalse(out.get("ok"), out)
        self.assertEqual(status, 409)
        self.assertIn("changed", out["message"])
        self.assertEqual(f.read_text(encoding="utf-8"), read + "\nanother tab\n")      # nothing was written
        now = f.read_text(encoding="utf-8")
        status, out = raw(self, {"op": "write", "path": rel, "text": now + "- mine\n", "expect_text": now})
        self.assertTrue(out.get("ok"), out)
        self.assertEqual(f.read_text(encoding="utf-8"), now + "- mine\n")

    def test_a_write_without_expect_text_is_as_before(self):
        rel = f"{ABC}/CLAUDE.md"
        f = self.v.root / rel
        now = f.read_text(encoding="utf-8")
        self.assertTrue(raw(self, {"op": "write", "path": rel, "text": now})[1]["ok"])


if __name__ == "__main__":
    unittest.main()
