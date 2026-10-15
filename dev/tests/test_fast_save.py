"""BL-327 (v1.9.4): saves and the first load no longer wait for the slow steps.

Run: python3 dev/tests/test_fast_save.py
A throwaway vault (test_dashboard.populate) with a few dozen documents. Each Done-when point:
- the debug log times each after-apply step (offsite copy, search index, dashboard, Excel) and the page's build;
- the index is incremental: only a changed file is read again, a removed one leaves, a meeting filed twice stays one entry,
  and a full rebuild happens only for new readers, a new layout or `tracker.py index`;
- through the live server an apply answers in about 1 to 2 s with a changed document, the index catches up in the background
  within seconds (one worker, logged), and a first page load after a start is under 2 s, served from the last built data.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402

DOCS = 40


def put(v, rel, text):
    p = v.root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def log_text(v):
    d = v.root / "system/logs"
    return "".join(f.read_text(encoding="utf-8") for f in sorted(d.glob("debug-*.log"))) if d.is_dir() else ""


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        for i in range(DOCS):
            put(self.v, f"{ABC}/documents/Note {i:02}.md", f"Background note {i} " + "filler " * 300)

    def tearDown(self):
        self.v.cleanup()

    def py(self, code, env=None):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import tracker\n" + code],
                           cwd=self.v.root, capture_output=True, text=True, env={**os.environ, **(env or {})})
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def query(self, text):
        return [h["path"] for h in json.loads(self.v.run("query", text).stdout)]

    def index_lines(self):
        return re.findall(r"search index: (full|incremental) in [\d.]+s: (\d+) entr(?:y|ies) read again, (\d+) file\(s\) removed, "
                          r"(\d+) indexed", log_text(self.v))

    def test_only_what_changed_is_read_again(self):
        self.assertIn(f"Indexed {DOCS} file(s)", self.v.run("index").stdout)
        self.assertEqual(self.index_lines()[-1], ("full", str(DOCS), "0", str(DOCS)))
        self.py("tracker.build_index()")                                      # nothing changed: nothing read
        self.assertEqual(self.index_lines()[-1], ("incremental", "0", "0", str(DOCS)))
        time.sleep(0.02)
        put(self.v, f"{ABC}/documents/Note 03.md", "Rewritten with the word zebracrossing")
        (self.v.root / ABC / "documents/Note 07.md").unlink()
        put(self.v, f"{ABC}/documents/Fresh.md", "A new note about quokkas")
        self.py("tracker.build_index()")
        self.assertEqual(self.index_lines()[-1], ("incremental", "2", "1", str(DOCS)))
        self.assertEqual(self.query("zebracrossing"), [f"{ABC}/documents/Note 03.md"])
        self.assertEqual(self.query("quokkas"), [f"{ABC}/documents/Fresh.md"])
        filler = self.query("filler")
        self.assertNotIn(f"{ABC}/documents/Note 07.md", filler)               # removed
        self.assertNotIn(f"{ABC}/documents/Note 03.md", filler)               # its old text is gone
        self.assertEqual(len(filler), len(set(filler)))                        # no duplicates left behind

    def test_a_meeting_filed_twice_stays_one_entry(self):
        reg = self.v.root / "projects/_portfolio/project-register.md"
        reg.write_text(reg.read_text().replace("|  |  |  |  |  |  |  |  |",
                                               "| DEF | Digital Enablement | DEF Digital Enablement | Enable | Sam | def.example | DEF | portal |"))
        for d in (ABC, "projects/DEF Digital Enablement"):
            put(self.v, f"{d}/minutes/2026-10-01 Joint steering.md", "Joint steering about wombats")
        self.py("tracker.build_index()")
        hits = json.loads(self.v.run("query", "wombats").stdout)
        self.assertEqual(len(hits), 1)
        self.assertEqual(sorted(hits[0]["project"].split()), ["ABC", "DEF"])
        time.sleep(0.02)
        put(self.v, "projects/DEF Digital Enablement/minutes/2026-10-01 Joint steering.md", "Now only about platypus")
        self.py("tracker.build_index()")
        self.assertEqual(self.query("platypus"), ["projects/DEF Digital Enablement/minutes/2026-10-01 Joint steering.md"])
        self.assertEqual(json.loads(self.v.run("query", "wombats").stdout)[0]["project"], "ABC")

    def test_a_full_rebuild_only_for_new_readers_or_layout(self):
        self.py("tracker.build_index()")
        stamp = self.v.root / "system/search/index-built.json"
        for change in ({"readers": 2}, {"layout": None}):
            rec = json.loads(stamp.read_text(encoding="utf-8"))
            rec.update(change)
            stamp.write_text(json.dumps(rec), encoding="utf-8")
            self.assertEqual(json.loads(self.py("print(json.dumps(tracker.index_state()))"))[0], True)
            self.py("tracker.build_index()")
            self.assertEqual(self.index_lines()[-1][0], "full")
        self.assertEqual(json.loads(self.py("print(json.dumps(tracker.index_state()))")), [False, ""])

    def test_each_after_apply_step_is_timed_and_background_leaves_them_owed(self):
        self.v.propose("one", [action(1, description="Timed save")])
        self.v.run("apply")
        log = log_text(self.v)
        for step in ("offsite copy", "search index", "build_dashboard.py", "excel_sync.py export"):
            self.assertRegex(log, rf"after apply: {re.escape(step)} in \d+\.\d\ds", step)
        flag = self.v.root / "system/search/after-apply-due"
        self.assertFalse(flag.exists())
        put(self.v, f"{ABC}/documents/Note 01.md", "Now about capybaras")
        self.v.propose("two", [action(2, description="Second save")])
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/tracker.py"), "apply"], cwd=self.v.root,
                           capture_output=True, text=True, env={**os.environ, "CREAITE_AFTER_APPLY": "background"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(flag.exists())                                        # owed to the server's worker
        self.assertEqual(self.query("capybaras"), [])
        self.py("tracker.after_apply_slow()")
        self.assertEqual(self.query("capybaras"), [f"{ABC}/documents/Note 01.md"])


class PageInputsTests(unittest.TestCase):
    """The files the server writes itself at start never count as page inputs (BL-329's starting mark made the first load
    after a start build anew whenever it came before the mark was cleared)."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def test_the_servers_own_files_are_not_inputs(self):
        for name in ("live-server.json", "live-server-starting.json"):
            put(self.v, f"system/staging/{name}", '{"pid": 1, "port": 1}\n')
        put(self.v, "system/staging/proposed-x.json", "{}")
        put(self.v, "system/staging/evidence/ABC-current.json", "{}")    # BL-207: saved after the page was built
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts'); import live_server\n"
                            "print('\\n'.join(f.name for f in live_server.page_inputs()))"],
                           cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        names = r.stdout.split()
        self.assertIn("proposed-x.json", names)
        self.assertIn("ABC-current.json", names)
        self.assertNotIn("live-server.json", names)
        self.assertNotIn("live-server-starting.json", names)


class LiveTimingTests(unittest.TestCase):
    """The timed test on the sample vault, through the real live server."""

    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        for i in range(DOCS):
            put(v, f"{ABC}/documents/Note {i:02}.md", f"Background note {i} " + "filler " * 300)
        v.run("index")
        v.run("build_dashboard.py", script="build_dashboard.py")
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port)}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        t0 = time.monotonic()
        cls.html = urllib.request.urlopen(cls.base + "/", timeout=30).read().decode()
        cls.first_load = time.monotonic() - t0
        cls.data = json.loads(re.search(r'id="data">(.*?)</script>', cls.html, re.S).group(1).replace("<\\/", "</"))

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.data["token"]})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def test_1_first_load_is_quick_and_from_the_last_built_data(self):
        self.assertLess(self.first_load, 2.0)
        self.assertTrue(self.data["live"])
        self.assertIn("page_age", self.data)                                # served from the data built before the start
        self.assertRegex(log_text(self.v), r"page: data (built|cache) in [\d.]+s, render [\d.]+s")

    def test_2_apply_answers_quickly_and_the_index_catches_up(self):
        time.sleep(0.05)
        put(self.v, f"{ABC}/documents/Note 05.md", "Changed just before the save: aardvarks")
        self.v.propose("timed", [action(60, description="Timed live save")])
        t0 = time.monotonic()
        r = self.post("/api/apply", {})
        took = time.monotonic() - t0
        self.assertTrue(r["ok"], r)
        self.assertLess(took, 2.5, f"apply took {took:.2f}s")
        self.assertIn("Timed live save", [a["description"] for a in self.v.rows("actions")])
        deadline, hits = time.monotonic() + 15, []
        while time.monotonic() < deadline:
            hits = [h["path"] for h in json.loads(self.v.run("query", "aardvarks").stdout)]
            if hits:
                break
            time.sleep(0.2)
        self.assertEqual(hits, [f"{ABC}/documents/Note 05.md"])
        caught_up = time.monotonic() - t0
        self.assertLess(caught_up, 15)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and "after apply (background): done" not in log_text(self.v):
            time.sleep(0.1)
        log = log_text(self.v)
        self.assertRegex(log, r"after apply \(background\): done in [\d.]+s")
        self.assertRegex(log, r"after apply: build_dashboard\.py in [\d.]+s")
        self.assertFalse((self.v.root / "system/search/after-apply-due").exists())
        print(f"\n  BL-327 timings: first load {self.first_load:.2f}s, apply {took:.2f}s, index caught up after {caught_up:.2f}s")

    def test_3_a_second_load_uses_the_servers_own_data_until_something_changes(self):
        t0 = time.monotonic()
        urllib.request.urlopen(self.base + "/", timeout=30).read()
        self.assertLess(time.monotonic() - t0, 2.0)
        req = urllib.request.Request(self.base + "/api/data", headers={"X-Creaite-Token": self.data["token"]})
        fresh = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
        html = urllib.request.urlopen(self.base + "/", timeout=30).read().decode()
        again = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        self.assertEqual(len(again["actions"]), len(fresh["actions"]))
        self.assertIn("page: data cache in", log_text(self.v))
        self.v.propose("later", [action(61, description="Changed since")])         # staging changed: built anew
        urllib.request.urlopen(self.base + "/", timeout=30).read()
        self.assertIn("page: data new in", log_text(self.v))


if __name__ == "__main__":
    unittest.main()
