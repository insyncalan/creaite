"""M1 (Team Cap's review of the client report setting writes): /api/fs must hand a file back with its own line endings, so that the
page's read, backup and write of a project's CLAUDE.md keeps a CRLF file CRLF and the backup is byte-identical to the original.

This test FAILS against the current live_server.py (read_text turns CRLF into LF) and passes once the diff in
dev/proposals/fs-newline.md is applied. Until then it is skipped, with the reason below, so the suite stays green.
To see it fail on the current file, run it with the environment variable FS_NEWLINE_FORCE=1.

Run (with the diff applied): python3 dev/tests/test_fs_newline.py
"""
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_reports import ABC, ReportRoutes  # noqa: E402

SERVER = (Path(__file__).resolve().parents[2] / "system" / "scripts" / "live_server.py").read_text(encoding="utf-8")
APPLIED = 'open(p, encoding="utf-8", newline="")' in SERVER or bool(os.environ.get("FS_NEWLINE_FORCE"))


@unittest.skipUnless(APPLIED, "skipped: the fs-newline diff (dev/proposals/fs-newline.md) is not applied to live_server.py yet")
class FsNewline(unittest.TestCase):
    setUpClass = classmethod(ReportRoutes.setUpClass.__func__)
    tearDownClass = classmethod(ReportRoutes.tearDownClass.__func__)
    post = ReportRoutes.post

    def test_a_crlf_claude_md_is_read_back_with_crlf_and_a_write_of_it_is_byte_identical(self):
        rel = f"{ABC}/CLAUDE.md"
        f = self.v.root / rel
        original = re.sub(r"\r?\n", "\r\n", f.read_text(encoding="utf-8")).encode("utf-8")
        f.write_bytes(original)
        got = self.post("/api/fs", {"op": "read", "path": rel})
        self.assertTrue(got["ok"], got)
        self.assertIn("\r\n", got["text"], "the text comes back with its CRLF")
        backup = f.with_name("backup-copy.md")        # what the page does: a copy of the text it read, then the new text
        backup.write_bytes(got["text"].encode("utf-8"))
        self.assertEqual(backup.read_bytes(), original, "the backup is byte-identical to the original")
        edited = got["text"].replace("- **Client report rhythm:** fortnightly", "- **Client report rhythm:** weekly")
        self.assertTrue(self.post("/api/fs", {"op": "write", "path": rel, "text": edited})["ok"])
        after = f.read_bytes()
        self.assertEqual(after, original.replace(b"fortnightly", b"weekly"), "only the changed value differs; every line ending is still CRLF")
        self.assertEqual(after.count(b"\n"), after.count(b"\r\n"))
        backup.unlink()


if __name__ == "__main__":
    unittest.main()
