"""BL-323 (Alan, 14-10-2026): Settings › Health › Restore from a backup.

The routes (/api/backup/list, /preview, /restore) are dashboard-only: refused without the page's token, and they accept a body of
exactly {"zip": name} with a name from the server's own list (backup.choices()); anything else is refused and changes nothing.
In the page, Choose a backup lists the zips, Preview shows a confirm card with what will be replaced (a dry run: nothing changes),
and Restore puts the backup's database back, keeping the current one first.

Run: python3 dev/tests/test_backup_restore_ui.py   (needs Google Chrome; skipped otherwise)
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ROUTES = ("/api/backup/list", "/api/backup/preview", "/api/backup/restore")


class RestoreFromBackup(LiveBrowserCase):
    """One vault and server per test: a restore changes data."""
    quiet_jobs = False        # exercises backups or archiving: keeps the shipped settings

    @classmethod
    def load(cls, v):
        super().load(v)
        r = subprocess.run([sys.executable, str(v.root / "system/scripts/session.py"), "start", "--force"],
                           env={**os.environ, "CREAITE_NOW": "2026-10-14 09:00"}, capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, r.stdout + r.stderr
        assert (v.root / "system/backups/creaite-backup-2026-10-14.zip").is_file(), r.stdout

    def token(self):
        html = urllib.request.urlopen(self.base + "/").read().decode()
        return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    def post(self, path, body, token):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read() or b"{}")

    def db(self):
        return self.v.root / "system/tracker.db"

    def names(self):
        with closing(sqlite3.connect(self.db())) as con:
            return dict(con.execute("SELECT code, name FROM projects"))

    def rename_projects(self):
        with closing(sqlite3.connect(self.db())) as con:
            con.execute("UPDATE projects SET name = name || ' (changed)'")
            con.commit()

    def restore_copies(self):
        return list((self.v.root / "system/backups").glob("tracker-*-restore.db"))

    def test_refused_without_the_token(self):
        before = self.names()
        self.rename_projects()
        changed = self.names()
        for path in ROUTES:
            self.assertEqual(self.post(path, {"zip": "creaite-backup-2026-10-14.zip"}, "wrong")[0], 403, path)
        self.assertEqual(self.names(), changed)
        self.assertNotEqual(changed, before)
        self.assertEqual(self.restore_copies(), [])

    def test_refused_for_a_name_not_in_the_list_or_anything_else_in_the_body(self):
        t = self.token()
        code, got = self.post("/api/backup/list", {}, t)
        self.assertEqual(code, 200)
        self.assertEqual([z["name"] for z in got["zips"]], ["creaite-backup-2026-10-14.zip"])
        self.assertNotIn("path", got["zips"][0])                                   # the page never sees a path
        self.rename_projects()
        changed = self.names()
        outside = self.v.root / "system/backups/elsewhere.zip"
        outside.write_bytes((self.v.root / "system/backups/creaite-backup-2026-10-14.zip").read_bytes())
        for body in ({"zip": "elsewhere.zip"}, {"zip": str(outside)}, {"zip": "../backups/creaite-backup-2026-10-14.zip"},
                     {"zip": "creaite-backup-2026-10-14.zip", "claude_md": True}, {"path": "creaite-backup-2026-10-14.zip"},
                     {"zip": ["creaite-backup-2026-10-14.zip"]}, {}):
            self.assertEqual(self.post("/api/backup/restore", body, t)[0], 400, body)
        self.assertEqual(self.post("/api/backup/list", {"zip": "x"}, t)[0], 400)
        self.assertEqual(self.post("/api/backup/restore?zip=creaite-backup-2026-10-14.zip", {"zip": "creaite-backup-2026-10-14.zip"}, t)[0], 400)
        self.assertEqual(self.names(), changed)
        self.assertEqual(self.restore_copies(), [])

    def open_health(self):
        self.b.eval("go('settings','health')")
        self.b.wait("!!document.getElementById('backupList')")

    def test_preview_is_a_dry_run_and_shows_what_will_be_replaced(self):
        self.rename_projects()
        changed = self.names()
        self.open_health()
        b = self.b
        b.eval("document.getElementById('backupList').click()")
        b.wait("!!document.querySelector('#backupRestore [data-zip] button')")
        self.assertIn("14-10-2026", b.eval("document.querySelector('#backupRestore [data-zip] .t').textContent"))
        b.eval("document.querySelector('#backupRestore [data-zip] button').click()")
        b.wait("!!document.getElementById('backupConfirm')")
        text = b.eval("document.getElementById('backupConfirm').textContent")
        self.assertIn("Restore from the backup of 14-10-2026?", text)
        self.assertIn("system/tracker.db", text)
        self.assertIn("database: replaces system/tracker.db", text)
        self.assertEqual(self.names(), changed)                                     # nothing changed by the preview
        self.assertEqual(self.restore_copies(), [])
        b.eval("[...document.querySelectorAll('#backupConfirm button')].find(x=>x.textContent==='Cancel').click()")
        b.wait("!document.getElementById('backupConfirm')")

    def test_a_restore_puts_the_backup_back_and_keeps_the_current_database_first(self):
        before = self.names()
        self.rename_projects()
        self.open_health()
        b = self.b
        b.eval("document.getElementById('backupList').click()")
        b.wait("!!document.querySelector('#backupRestore [data-zip] button')")
        b.eval("document.querySelector('#backupRestore [data-zip] button').click()")
        b.wait("!!document.getElementById('backupRestoreGo')")
        b.eval("document.getElementById('backupRestoreGo').click()")
        b.wait("!document.getElementById('backupConfirm') && !!document.querySelector('#backupRestore [aria-label=\"What was restored\"]')",
               timeout=120)
        self.assertIn("Restored from the backup of 14-10-2026", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(self.names(), before)
        kept = self.restore_copies()
        self.assertEqual(len(kept), 1)
        with closing(sqlite3.connect(kept[0])) as con:                              # the database as it was, kept first
            self.assertTrue(all(n.endswith("(changed)") for _, n in con.execute("SELECT code, name FROM projects")))
        log = "".join(p.read_text() for p in (self.v.root / "system/logs").glob("debug-*.log"))
        self.assertIn("restored from creaite-backup-2026-10-14.zip (Settings › Health)", log)


if __name__ == "__main__":
    unittest.main(verbosity=2)
