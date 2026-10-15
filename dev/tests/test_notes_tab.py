"""BL-301 B (v20-notes-tab): the Notes tab's server side, /api/notes/* on a live server over a throwaway vault.

Run: python3 dev/tests/test_notes_tab.py

  - a note is created from each template in the project's notes folder (made on the first note) through filechange.py, logged
    as a dashboard change and undoable; a taken title gets a number;
  - a save writes the file once through filechange.py (front matter kept, `updated` stamped); an unchanged save writes nothing;
    a note changed outside creaite since it was opened is never overwritten; no draft is kept (#119: the draft route is gone);
  - the list carries front matter and references (links, items, people), never text; portfolio notes are listed too;
  - the dashboard's data carries each project's notes and the templates; Files lists notes as their own folder (the portfolio's too);
  - paths outside a notes folder are refused;
  - #119: saves naming one editing session keep one backup, and one Undo puts back the text from before it; a save without a
    session, or with a malformed one, is backed up on its own.
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system/scripts"))
from test_tracker import ABC, Vault  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class NotesServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port)}
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(150):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        cls.token = cls.data["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()                  # our own server only, by its process
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"status": e.code, **json.loads(e.read().decode())}

    def folder(self):
        return self.v.root / ABC / "notes"

    def log(self):
        p = self.v.root / "system/config/files-log.jsonl"
        return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []

    def test_1_templates_make_notes_through_filechange(self):
        made = {}
        for tpl in ("blank", "stakeholder", "lessons-learned", "working-session"):
            r = self.post("/api/notes/new", {"code": "ABC", "template": tpl, "title": f"T {tpl}", "date": "2026-10-13",
                                             "with": ["Omar Ali"]})
            self.assertTrue(r["ok"], r)
            made[tpl] = r
            self.assertTrue((self.v.root / r["note"]["path"]).is_file())
        self.assertIn("## Role and influence", made["stakeholder"]["body"])
        self.assertEqual(made["working-session"]["meta"]["date"], "2026-10-13")
        self.assertEqual(made["working-session"]["note"]["kind"], "Working session")
        self.assertTrue(self.folder().is_dir())
        created = [e for e in self.log() if e.get("op") == "create" and "/notes/" in e["path"]]
        self.assertEqual(len(created), 4)
        self.assertTrue(all(e["via"] == "dashboard" for e in created))
        again = self.post("/api/notes/new", {"code": "ABC", "template": "blank", "title": "T blank"})
        self.assertTrue(again["note"]["file"].startswith("T blank-2"), again["note"]["file"])

    def test_2_save_once_and_undo(self):
        r = self.post("/api/notes/new", {"code": "ABC", "template": "blank", "title": "Data access"})
        rel, base = r["note"]["path"], r["base"]
        p = self.v.root / rel
        before = p.read_text()
        body = "See [[Data access]] and [ABC-A-001](creaite:item/ABC-A-001), with @[Sara Example](creaite:person/Sara%20Example).\n"
        gone = self.post("/api/notes/draft", {"path": rel, "body": body, "base": base})
        self.assertEqual(gone["status"], 404, "#119: no draft route")
        self.assertNotIn("draft", self.post("/api/notes/get", {"path": rel}))
        n_before = len(self.log())
        s = self.post("/api/notes/save", {"path": rel, "body": body, "changes": {"tags": ["data"], "pinned": True}, "base": base})
        self.assertTrue(s["ok"], s)
        self.assertEqual(len(self.log()), n_before + 1, "one change per editing session")
        text = p.read_text()
        self.assertIn("tags: [data]", text)
        self.assertIn("pinned: true", text)
        self.assertTrue(text.endswith(body))
        self.assertEqual(s["note"]["items"], ["ABC-A-001"])
        self.assertEqual(s["note"]["links"], ["Data access"])
        self.assertEqual(s["note"]["people"], ["Sara Example"])
        self.assertFalse((self.v.root / "system/staging/drafts/notes").is_dir(), "no draft is kept")
        same = self.post("/api/notes/save", {"path": rel, "body": body, "base": s["base"]})
        self.assertTrue(same.get("unchanged"))
        self.assertEqual(len(self.log()), n_before + 1)
        undo = subprocess.run([sys.executable, str(self.v.root / "system/scripts/filechange.py"), "undo", str(s["change"])],
                              cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(undo.returncode, 0, undo.stdout + undo.stderr)
        self.assertEqual(p.read_text(), before)

    def test_3_changed_outside_is_never_overwritten(self):
        r = self.post("/api/notes/new", {"code": "ABC", "template": "blank", "title": "Outside"})
        rel = r["note"]["path"]
        p = self.v.root / rel
        p.write_text(p.read_text() + "Typed in Finder.\n")
        s = self.post("/api/notes/save", {"path": rel, "body": "mine\n", "base": r["base"]})
        self.assertFalse(s["ok"])
        self.assertTrue(s["conflict"])
        self.assertIn("Typed in Finder.", p.read_text())
        self.assertNotIn("draft", s["message"])
        self.assertFalse((self.v.root / "system/staging/drafts/notes").is_dir(), "no draft is kept")

    def test_4_list_portfolio_and_refusals(self):
        self.post("/api/notes/new", {"code": "_portfolio", "template": "blank", "title": "Across projects"})
        L = self.post("/api/notes/list", {"code": "_portfolio"})
        self.assertEqual([n["title"] for n in L["notes"]], ["Across projects"])
        self.assertNotIn("body", L["notes"][0])
        self.assertEqual(self.post("/api/notes/list", {"code": "nope"})["status"], 400)
        self.assertEqual(self.post("/api/notes/get", {"path": f"{ABC}/CLAUDE.md"})["status"], 404)
        self.assertEqual(self.post("/api/notes/save", {"path": "projects/../x.md", "body": "x", "base": ""})["status"], 404)

    def test_5_dashboard_data_and_files(self):
        self.post("/api/notes/new", {"code": "ABC", "template": "blank", "title": "For the data"})
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        html = urllib.request.urlopen(self.base + "/").read().decode()
        data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        self.assertIn("For the data", [n["title"] for n in data["notes"]["ABC"]])
        self.assertIn("## Purpose", data["note_templates"]["working-session"])
        kinds = {(f["p"], f["f"]) for f in data["files"]}
        self.assertIn(("ABC", "notes"), kinds)
        self.assertIn(("_portfolio", "notes"), kinds)

    def test_6_saves_in_one_editing_session_keep_one_backup(self):
        # #119: the page names its editing session; filechange.py keeps one backup per session, one per save without it
        r = self.post("/api/notes/new", {"code": "ABC", "template": "blank", "title": "Autosaved"})
        rel, base = r["note"]["path"], r["base"]
        p = self.v.root / rel
        before = p.read_text()
        n = len(self.log())
        sid = "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0"
        for i in range(4):
            s = self.post("/api/notes/save", {"path": rel, "body": f"typed {i}\n", "base": base, "session": sid})
            self.assertTrue(s["ok"], s)
            base = s["base"]
        edits = [e for e in self.log()[n:] if e.get("op") == "edit"]
        self.assertEqual(len(edits), 4)
        self.assertEqual(len({e["backup"] for e in edits}), 1, "one backup for the session")
        self.assertNotIn(sid, (self.v.root / "system/config/files-log.jsonl").read_text(), "the session id is never logged")
        for bad in ("short", "x" * 65, "has space in it", 12345678, None):
            s = self.post("/api/notes/save", {"path": rel, "body": f"bad {bad}\n", "base": base, "session": bad})
            self.assertTrue(s["ok"], s)
            base = s["base"]
        tail = [e for e in self.log()[n:] if e.get("op") == "edit"][4:]
        self.assertEqual(len({e["backup"] for e in tail}), 5, "no session, or a malformed one: a backup for each save")
        self.assertTrue(all("session" not in e for e in tail))
        for _ in tail:
            self.assertEqual(subprocess.run([sys.executable, str(self.v.root / "system/scripts/filechange.py"), "undo"],
                                            cwd=self.v.root, capture_output=True, text=True).returncode, 0)
        u = subprocess.run([sys.executable, str(self.v.root / "system/scripts/filechange.py"), "undo"], cwd=self.v.root,
                           capture_output=True, text=True)
        self.assertEqual(u.returncode, 0, u.stdout + u.stderr)
        self.assertEqual(p.read_text(), before, "one Undo puts back the text from before the session")


if __name__ == "__main__":
    unittest.main()
