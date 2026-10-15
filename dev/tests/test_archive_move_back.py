"""BL-331: move one archived report back (after v1.9.5; Alan, 14-10-2026).

Run: python3 dev/tests/test_archive_move_back.py     (one live server; the last class needs Google Chrome, skipped otherwise)

What is covered, with the clock pinned (CREAITE_NOW), after BL-03's archive has moved old reports and minutes into _Archive:
- Files lists the files the archive moved, marked archived, each with Move back, and only those: the ordinary list never has them;
- Move back goes on the approval card ("Move file … → …"), and Approve moves the file back through tracker.py apply;
- the stored path still opens the file, it is indexed and found by search again, and it leaves the archived list;
- undo puts it back in _Archive (not indexed again, listed as archived again);
- refused when its place is taken (never overwritten), for a file the archive didn't move, and for any other shape (another
  engagement, another folder, a transcript, the portfolio's transcripts, `..`): reach.archive_move_problem's "reports_back" is
  exactly the reverse of the approved "reports" shape;
- ask creaite still can't read or move anything in _Archive: classify() says never, a CHANGE card with a move back is refused, and
  propose.py stage refuses one from anywhere but the live server's own snapshot.
Everything is fictional and temporary.
"""
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_onedrive_projects import touch  # noqa: E402
from test_tracker import Vault  # noqa: E402

DAY = "2026-10-14 09:00"
ENV = {"CREAITE_NOW": DAY}
DUE = ["minutes/2025-09-30 Steering committee.md", "reports/2025-10-03 Weekly report - Example Programme.docx",
       "reports/Steerco/2025-02-01 Example Programme Steerco one-pager.docx"]
PORTFOLIO = "minutes/2025-06-01 Portfolio sync.md"


def run_in(root, *args, script, ok=True, test=None):
    r = subprocess.run([sys.executable, str(root / "system/scripts" / script), *args], capture_output=True, text=True,
                       cwd=root, env={**os.environ, **ENV})
    if ok and r.returncode != 0:
        raise AssertionError(f"{script} {args}: {r.stdout}{r.stderr}")
    return r


def archive_old_files(root):
    """Make the old files, then archive them as BL-03 does (archive.py reports, staged, applied). The ABC folder."""
    abc = next(d for d in (root / "projects").iterdir() if d.name.startswith("ABC "))
    for f in DUE:
        touch(abc / f, f"{f}: the numbat budget line\n")
    touch(abc / "transcripts/2024-01-01 Steering.vtt")
    touch(root / "projects/_portfolio" / PORTFOLIO, "the quokka review\n")
    spec = run_in(root, "reports", script="archive.py").stdout
    f = root / "system/staging/drafts/r.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(spec, encoding="utf-8")
    run_in(root, "stage", str(f), script="propose.py")
    run_in(root, "apply", script="tracker.py")
    return abc


class MoveBack(unittest.TestCase):
    """The projects in the vault (projects/ABC Example Programme/…)."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.abc = archive_old_files(self.v.root)
        self.base = f"projects/{self.abc.name}"

    def tearDown(self):
        self.v.cleanup()

    def run_at(self, *args, script, ok=True):
        return run_in(self.v.root, *args, script=script, ok=ok)

    def py(self, code):
        src = f"import sys, json; sys.path.insert(0, 'system/scripts')\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=self.v.root, env={**os.environ, **ENV})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def files(self):
        return self.py("import build_dashboard as bd; v = bd.files_view(); "
                       "print(json.dumps([[f['path'] for f in v['files']], v['archived']]))")

    def spec(self, stored):
        return self.py(f"import archive; print(json.dumps(archive.back_spec({stored!r})))")

    def stage_from_guard(self, spec):
        """Stage a spec as the live server's card does: its snapshot in system/guard/ (which only the server writes)."""
        f = self.v.root / "system/guard/edit-test.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(spec), encoding="utf-8")
        return self.run_at("stage", str(f), script="propose.py", ok=False)

    def apply_as_card(self, staged):
        """tracker.py apply of the card's own proposal (the stage's output names it) inside the markers the live server writes on
        Approve (live_server.card_moves_allowed, #124 F3), as edit_apply does; asserts it applied and left no marker behind."""
        name = Path(re.search(r"Staged and approved: (\S+\.json)", staged.stdout).group(1)).name
        code, out, left = self.py(
            "import os, subprocess, live_server as ls, paths\n"
            f"with ls.card_moves_allowed({name!r}):\n"
            f"    r = subprocess.run([sys.executable, 'system/scripts/tracker.py', 'apply', {name!r}], capture_output=True, text=True)\n"
            "print(json.dumps([r.returncode, r.stdout + r.stderr, sorted(f.name for f in paths.GUARD.glob('move-*'))]))")
        self.assertEqual(code, 0, out)
        self.assertEqual(left, [])
        return out

    def where(self, stored):
        """[where the stored path opens, ask creaite's read verdict, the files the search index reads]."""
        return self.py(f"import paths, reach, tracker; print(json.dumps([str(paths.resolve({stored!r})), "
                       f"reach.classify({stored!r}, 'read')[0], [str(f) for f, _, _ in tracker.index_files()]]))")

    def search(self, word):
        return self.run_at("query", word, "--no-parse", script="search.py").stdout

    def test_files_lists_the_archived_files_apart_each_marked(self):
        listed, archived = self.files()
        want = {f"{self.base}/{f}" for f in DUE} | {f"projects/_portfolio/{PORTFOLIO}"}
        self.assertEqual({a["path"] for a in archived}, want)
        self.assertTrue(all(a["archived"] is True for a in archived))
        self.assertFalse(want & set(listed))                                   # never in the ordinary list
        self.assertFalse(any(f.startswith(f"{self.base}/_Archive") for f in listed))
        kinds = {a["n"]: (a["p"], a["f"], a["sub"]) for a in archived}
        self.assertEqual(kinds["2025-09-30 Steering committee.md"], ("ABC", "minutes", ""))
        self.assertEqual(kinds["2025-10-03 Weekly report - Example Programme.docx"], ("ABC", "reports", "Weekly"))
        self.assertEqual(kinds["2025-02-01 Example Programme Steerco one-pager.docx"], ("ABC", "reports", "Steerco"))
        self.assertEqual(kinds["2025-06-01 Portfolio sync.md"], ("_portfolio", "minutes", ""))
        built = self.py("import build_dashboard as bd; d = bd.collect(); print(json.dumps(len(d['files_archived'])))")
        self.assertEqual(built, 4)

    def test_move_back_through_apply_is_indexed_again_and_undo_archives_it_again(self):
        stored = f"{self.base}/{DUE[0]}"
        self.assertNotIn(DUE[0].split("/")[-1], self.search("numbat"))      # archived: not indexed
        spec, why = self.spec(stored)
        self.assertIsNone(why)
        fc = spec["file_changes"]
        self.assertEqual((fc["archive"], fc["title"]), ("reports_back", "Move back 2025-09-30 Steering committee.md"))
        self.assertEqual(fc["file_ops"], [{"op": "move", "from": f"{self.base}/_Archive/{DUE[0]}", "to": stored}])
        r = self.stage_from_guard(spec)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"Move file {self.base}/_Archive/{DUE[0]} → {stored}", r.stdout)
        self.apply_as_card(r)                                                 # #124 F3: as Approve on the card applies it
        self.assertTrue((self.abc / DUE[0]).is_file())
        self.assertFalse((self.abc / "_Archive" / DUE[0]).exists())
        o = self.where(stored)
        self.assertEqual(o[0], str((self.abc / DUE[0]).resolve()))           # its stored path opens it in place
        self.assertNotEqual(o[1], "never")
        self.assertTrue(any(f.endswith(DUE[0].split("/")[-1]) for f in o[2]))     # indexed again
        self.assertIn("2025-09-30 Steering committee.md", self.search("numbat"))  # and found by search
        listed, archived = self.files()
        self.assertIn(stored, listed)
        self.assertNotIn(stored, [a["path"] for a in archived])
        self.assertEqual(self.spec(stored)[0], None)                           # nothing left to move back
        out = self.run_at("undo", script="tracker.py").stdout
        self.assertNotIn("skipped", out)
        self.assertFalse((self.abc / DUE[0]).exists())                       # back in _Archive
        self.assertTrue((self.abc / "_Archive" / DUE[0]).is_file())
        self.assertIn(stored, [a["path"] for a in self.files()[1]])
        o = self.where(stored)
        self.assertEqual(o[0], str((self.abc / "_Archive" / DUE[0]).resolve()))
        self.assertEqual(o[1], "never")
        self.assertFalse(any("/_Archive/" in f for f in o[2]))

    def test_a_moved_back_file_is_never_offered_again(self):
        stored = f"{self.base}/{DUE[1]}"
        r = self.stage_from_guard(self.spec(stored)[0])
        self.assertEqual(r.returncode, 0)
        self.apply_as_card(r)
        self.assertTrue((self.abc / DUE[1]).is_file())
        touch(self.abc / "minutes/2025-08-01 Another old one.md")             # a new old file is still offered
        r = self.run_at("reports", script="archive.py")
        moves = [o["from"] for o in json.loads(r.stdout)["file_changes"]["file_ops"]]
        self.assertEqual(moves, [f"{self.base}/minutes/2025-08-01 Another old one.md"])
        (self.abc / "minutes/2025-08-01 Another old one.md").unlink()
        self.assertEqual(self.run_at("reports", script="archive.py", ok=False).returncode, 1)   # nothing else: never offered again
        self.assertEqual(self.py("import archive; print(json.dumps(archive.status()['reports']['due']))"), 0)
        self.run_at("undo", script="tracker.py")                              # undoing the move back: in _Archive again
        self.assertTrue((self.abc / "_Archive" / DUE[1]).is_file())
        self.assertEqual(self.py("import archive; print(json.dumps(sorted(archive.moved_back())))"), [])

    def test_portfolio_minutes_move_back_into_the_portfolio(self):
        stored = f"projects/_portfolio/{PORTFOLIO}"
        spec, why = self.spec(stored)
        self.assertIsNone(why)
        r = self.stage_from_guard(spec)
        self.assertEqual(r.returncode, 0)
        self.apply_as_card(r)
        pf = self.v.root / "projects/_portfolio"
        self.assertTrue((pf / PORTFOLIO).is_file())
        self.assertFalse((pf / "_Archive" / PORTFOLIO).exists())

    def test_refused_when_its_place_is_taken(self):
        stored = f"{self.base}/{DUE[1]}"
        spec, _ = self.spec(stored)
        touch(self.abc / DUE[1], "a newer file with the same name\n")
        spec2, why = self.spec(stored)
        self.assertIsNone(spec2)
        self.assertIn("already in its place", why)
        r = self.stage_from_guard(spec)                                      # the card made before it was taken
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already exists", r.stdout)
        self.v.propose("taken", [], file_changes={**spec["file_changes"], "file_changes_decision": "approved"})
        r = self.run_at("apply", "proposed-taken.json", script="tracker.py", ok=False)   # named: a full apply leaves it (#124 F3)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("never overwrites", r.stdout)
        self.assertEqual((self.abc / DUE[1]).read_text(), "a newer file with the same name\n")    # never overwritten
        self.assertTrue((self.abc / "_Archive" / DUE[1]).is_file())

    def test_refused_for_a_file_the_archive_didnt_move(self):
        name = "minutes/2025-01-01 Never archived.md"
        touch(self.abc / "_Archive" / name)                                  # put there by hand, not by the archive
        stored = f"{self.base}/{name}"
        spec, why = self.spec(stored)
        self.assertIsNone(spec)
        self.assertIn("isn't one the archive moved", why)
        self.assertNotIn(stored, [a["path"] for a in self.files()[1]])      # not listed as archived either
        fc = {"title": "x", "archive": "reports_back", "file_changes_decision": "approved",
              "file_ops": [{"op": "move", "from": f"{self.base}/_Archive/{name}", "to": stored}]}
        self.v.propose("hand", [], file_changes=fc)
        r = self.run_at("apply", "proposed-hand.json", script="tracker.py", ok=False)    # named: a full apply leaves it (#124 F3)
        self.assertIn("isn't a file the archive moved there", r.stdout)
        self.assertTrue((self.abc / "_Archive" / name).is_file())
        self.assertEqual(self.spec(f"{self.base}/../x/{name}")[1], "that isn't a stored project path")

    def test_only_the_exact_reverse_of_the_archive_shape(self):
        b, a = self.base, f"{self.base}/_Archive/{DUE[0]}"
        (self.v.root / "projects/DEF Other/minutes").mkdir(parents=True)
        touch(self.abc / "_Archive/transcripts/2024-01-01 Old.vtt")
        touch(self.v.root / "projects/_portfolio/_Archive/transcripts/2025-06-01 Portfolio sync.vtt")
        cases = {
            "another engagement": (a, f"projects/DEF Other/{DUE[0]}"),
            "another folder": (a, f"{b}/reports/2025-09-30 Steering committee.md"),
            "deeper": (a, f"{b}/minutes/x/2025-09-30 Steering committee.md"),
            "the engagement root": (a, f"{b}/2025-09-30 Steering committee.md"),
            "a transcript": (f"{b}/_Archive/transcripts/2024-01-01 Old.vtt", f"{b}/transcripts/2024-01-01 Old.vtt"),
            "the portfolio's transcripts": ("projects/_portfolio/_Archive/transcripts/2025-06-01 Portfolio sync.vtt",
                                            "projects/_portfolio/transcripts/2025-06-01 Portfolio sync.vtt"),
            "a folder": (f"{b}/_Archive/minutes", f"{b}/minutes2"),
            "dot dot": (f"{b}/_Archive/minutes/../{DUE[0]}", f"{b}/{DUE[0]}"),
            "into the archive (the other way)": (f"{b}/{DUE[0]}", a),
        }
        o = self.py("import reach; c = " + json.dumps(cases) + "\n"
                    "print(json.dumps({k: reach.archive_move_problem(x, y, 'reports_back') for k, (x, y) in c.items()}))")
        for k, why in o.items():
            self.assertTrue(why, k)
        self.assertIsNone(self.py(f"import reach; print(json.dumps(reach.archive_move_problem({a!r}, {(b + '/' + DUE[0])!r}, "
                                  "'reports_back')))"))

    def test_ask_creaite_still_cant_read_or_move_anything_there(self):
        arch = self.abc / "_Archive" / DUE[0]
        o = self.py(f"import reach; print(json.dumps([reach.classify({str(arch)!r}, op)[0] for op in "
                    "('read', 'change', 'move', 'delete', 'create')]))")
        self.assertEqual(set(o), {"never"})
        spec, _ = self.spec(f"{self.base}/{DUE[0]}")
        f = self.v.root / "system/staging/drafts/back.json"                 # where ask creaite writes a change
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(spec), encoding="utf-8")
        r = self.run_at("stage", str(f), script="propose.py", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("moved back from Files", r.stdout)
        self.assertFalse(list((self.v.root / "system/staging").glob("proposed-*-edit.json")))
        card = self.py("import live_server as ls\n"
                       "class Run:\n    id, chat, session = 'r1', None, None\n    events = []\n"
                       "    def emit(self, kind, **k): self.events.append([kind, k])\n"
                       "r = Run(); ls.build_edit_card(r, 'Done.\\nCHANGE: system/staging/drafts/back.json | Move it back')\n"
                       "print(json.dumps(r.events))")
        self.assertEqual(card[0][0], "editcard")
        self.assertIsNone(card[0][1]["card"])
        self.assertIn("never from ask creaite", card[0][1]["refused"])
        self.assertTrue(arch.is_file())


class MoveBackRoute(unittest.TestCase):
    """POST /api/files/move-back {path}: token-checked; it only puts the move on the card; Approve moves the file back."""

    @classmethod
    def setUpClass(cls):
        from test_health_fixes import free_port
        cls.v = Vault()
        cls.v.run("init")
        cls.abc = archive_old_files(cls.v.root)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, **ENV, "CREAITE_PORT": str(cls.port)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        page = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body, token=True):
        headers = {"Content-Type": "application/json", **({"X-Creaite-Token": self.token} if token else {})}
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return {"status": e.code, **json.loads(e.read() or b"{}")}

    def test_refused_then_on_the_card_then_moved_back(self):
        route, stored = "/api/files/move-back", f"projects/{self.abc.name}/{DUE[2]}"
        self.assertEqual(self.post(route, {"path": stored}, token=False)["status"], 403)
        self.assertEqual(self.post(route, {"path": stored, "to": "x"})["status"], 400)
        self.assertEqual(self.post(route, {"path": 3})["status"], 400)
        got = self.post(route, {"path": f"projects/{self.abc.name}/transcripts/2024-01-01 Steering.vtt"})
        self.assertFalse(got["ok"])
        self.assertIn("isn't one the archive moved", got["message"])
        req = urllib.request.Request(self.base + "/api/files", headers={"X-Creaite-Token": self.token})
        files = json.loads(urllib.request.urlopen(req).read())
        self.assertIn(stored, [a["path"] for a in files["archived"]])
        got = self.post(route, {"path": stored})
        self.assertTrue(got["ok"] and got["card"], got)
        self.assertTrue((self.abc / "_Archive" / DUE[2]).is_file())          # nothing moves before Approve
        card = self.post("/api/edit/pending", {})["card"]
        self.assertEqual(card["title"], "Move back 2025-02-01 Example Programme Steerco one-pager.docx")
        self.assertEqual(card["lines"], [f"Move file projects/{self.abc.name}/_Archive/{DUE[2]} → {stored}"])
        self.assertTrue(card["valid"])
        done = self.post("/api/edit/approve", {"card": card["card"]})
        self.assertTrue(done["ok"], done)
        self.assertTrue((self.abc / DUE[2]).is_file())
        self.assertFalse((self.abc / "_Archive" / DUE[2]).exists())
        files = json.loads(urllib.request.urlopen(req).read())
        self.assertNotIn(stored, [a["path"] for a in files["archived"]])
        self.assertIn(stored, [f["path"] for f in files["files"]])


class FilesMoveBack(LiveBrowserCase):
    """In the browser: Files' Archived chip lists them, each with Move back (no other row has it); Move back opens the card."""

    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        archive_old_files(v.root)

    @classmethod
    def server_env(cls):
        return dict(ENV)

    def test_move_back_only_on_archived_files_and_it_comes_back(self):
        b = self.b
        b.eval("go('files')")
        b.wait("document.querySelector('#fquick [data-q=\"archived\"]')")
        b.wait("document.querySelector('#filesTbl tr[data-fp]')")
        self.assertEqual(b.eval("document.querySelectorAll('#filesTbl [data-moveback]').length"), 0)    # All files: none
        b.eval("document.querySelector('#fquick [data-q=\"archived\"]').click()")
        b.wait("document.querySelector('#filesTbl [data-moveback]')")
        rows = b.eval("[...document.querySelectorAll('#filesTbl tr[data-fp]')].map(tr=>[tr.dataset.fp, "
                      "!!tr.querySelector('[data-moveback]'), !!tr.querySelector('.tag') && tr.textContent.includes('Archived')])")
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r[1] and r[2] for r in rows), rows)
        stored = f"{next(r[0] for r in rows if r[0].endswith(DUE[0].split('/')[-1]))}"
        b.eval(f"document.querySelector('#filesTbl [data-moveback=\"{stored}\"]').click()")
        b.wait("document.querySelector('#chLog .edcard [data-ed=\"approve\"]')")
        self.assertIn("Move back 2025-09-30 Steering committee.md", b.eval("document.querySelector('#chLog .edcard b').textContent"))
        b.eval("document.querySelector('#chLog .edcard [data-ed=\"approve\"]').click()")
        abc = next(d for d in (self.v.root / "projects").iterdir() if d.name.startswith("ABC "))
        for _ in range(200):
            if (abc / DUE[0]).is_file():
                break
            time.sleep(0.1)
        self.assertTrue((abc / DUE[0]).is_file())
        self.assertFalse((abc / "_Archive" / DUE[0]).exists())


if __name__ == "__main__":
    unittest.main()
