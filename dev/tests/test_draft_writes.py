"""BL-271 and BL-268.

BL-271: the command lines that write a file never bypass filechange.py.
- docx_tools.py fill, build-adhoc and clean write only inside system/staging/drafts/: a project path (or clean in place on a
  project's Word file) is refused, exit 2, nothing written, with how to make the change instead.
- prep_page.py build saves the page through filechange.py: a new page is a logged, undoable create; creaite's own unchanged page
  for the same meeting is replaced as an edit with a backup; in a run that has read outside content it is a sensitive change,
  recorded for the card, and nothing is written. (The live server's own write, prep_page.save, is unchanged.)

BL-268: "refresh calendar" works in a plain chat. Every step of cx-sweep's calendar step passes the guard hook in ask mode
(and confirmed), including a script named by the vault's full path; a command that isn't a creaite script (ls, cat, cd …) is
still refused, and so is a full path to scripts outside this vault. Then sweep.py calendar saves the calendar from the
drafts file.

Run: python3 dev/tests/test_draft_writes.py     (quick tier: no Chrome)
"""
import json
import os
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_prep_page_content as P  # noqa: E402  (its Vaulted fixture: a meeting today called "ABC weekly")
import test_dashboard  # noqa: E402
import test_decisions_prep  # noqa: E402
from test_tracker import ABC, Vault, make_draft  # noqa: E402

FIXED = date(2026, 10, 9)
for _m in (P, test_dashboard, test_decisions_prep):    # the fixture's dates are d(n) from each module's TODAY
    _m.TODAY = FIXED
os.environ["CREAITE_NOW"] = f"{FIXED} 08:30"
KEY = "09:00|ABC weekly"
REPLY = {"notes": [{"text": "The client asked about the go-live date.", "source": "S1"}], "questions": ["Is UAT booked?"]}


def py(v, code):
    """Run Python in the vault with its scripts on the path; (exit code, stdout)."""
    r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts'); " + code], cwd=v.root,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return r.stdout


class DocxDraftsOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        cls.project_doc = cls.v.root / ABC / "documents" / "Plan.docx"
        cls.project_doc.parent.mkdir(parents=True, exist_ok=True)
        make_draft(cls.project_doc)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def docx(self, *args):
        return self.v.run(*args, script="docx_tools.py", ok=False, cwd=self.v.root)

    def test_fill_and_build_adhoc_outside_drafts_are_refused(self):
        values = self.v.root / "system/staging/drafts/values.json"
        values.parent.mkdir(parents=True, exist_ok=True)
        values.write_text("{}", encoding="utf-8")
        spec = self.v.root / "system/staging/drafts/spec.json"
        spec.write_text(json.dumps({"title": "T"}), encoding="utf-8")
        for args, out in ((("fill", "system/templates/minutes-template.docx", str(values)), f"{ABC}/minutes/x.docx"),
                          (("build-adhoc", "system/templates/adhoc-template.docx", str(spec)), f"{ABC}/documents/y.docx"),
                          (("build-adhoc", "system/templates/adhoc-template.docx", str(spec)), str(self.v.root / "z.docx")),
                          (("build-adhoc", "system/templates/adhoc-template.docx", str(spec)), "system/staging/drafts/../w.docx")):
            with self.subTest(out):
                r = self.docx(*args, out)
                self.assertEqual(r.returncode, 2, r.stdout)
                self.assertIn("writes only inside system/staging/drafts/", r.stdout)
                self.assertIn("filechange.py edit", r.stdout)
                self.assertFalse((self.v.root / out).exists())

    def test_build_adhoc_into_drafts_works(self):
        spec = self.v.root / "system/staging/drafts/spec2.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"title": "Register"}), encoding="utf-8")
        r = self.docx("build-adhoc", "system/templates/adhoc-template.docx", str(spec), "system/staging/drafts/reg.docx")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.v.root / "system/staging/drafts/reg.docx").is_file())

    def test_clean_in_place_on_a_project_file_is_refused_and_leaves_it_alone(self):
        before = self.project_doc.read_bytes()
        for args in ((str(self.project_doc),), (f"{ABC}/documents/Plan.docx",),
                     ("system/staging/drafts/any.docx", f"{ABC}/documents/Plan.docx")):
            with self.subTest(args):
                r = self.docx("clean", *args)
                self.assertEqual(r.returncode, 2, r.stdout)
                self.assertEqual(self.project_doc.read_bytes(), before)

    def test_clean_of_a_draft_works(self):
        draft = self.v.root / "system/staging/drafts/d.docx"
        make_draft(draft)
        r = self.docx("clean", str(draft))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Accepted", r.stdout)


class PrepPageThroughFilechange(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        P.Vaulted.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def tearDown(self):
        py(self.v, "import reach; reach.end_run('r-1')")

    def build(self):
        reply = self.v.root / "system/staging/drafts/prep-reply.json"
        reply.parent.mkdir(parents=True, exist_ok=True)
        reply.write_text(json.dumps(REPLY), encoding="utf-8")
        r = self.v.run("build", KEY, str(reply), script="prep_page.py", ok=False, cwd=self.v.root)
        return r, reply

    def log(self):
        f = self.v.root / "system/config/files-log.jsonl"
        return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []

    def pages(self):
        folder = self.v.root / ABC / "agendas"
        return sorted(p.name for p in folder.glob("*.html")) if folder.exists() else []

    def test_1_a_new_page_is_a_logged_undoable_create(self):
        r, reply = self.build()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Created", r.stdout)
        self.assertFalse(reply.exists())                                    # BL-118: the reply has done its job
        self.assertEqual(self.pages(), [f"{FIXED} Prep - ABC weekly.html"])
        last = self.log()[-1]
        self.assertEqual((last["op"], last["path"]), ("create", f"{ABC}/agendas/{FIXED} Prep - ABC weekly.html"))
        self.assertEqual(list((self.v.root / "system/staging/drafts").glob("prep-page*.html")), [])   # its draft is gone
        reg = json.loads((self.v.root / "system/staging/prep-pages.json").read_text(encoding="utf-8"))
        self.assertIn(f"{ABC}/agendas/{FIXED} Prep - ABC weekly.html", reg)

    def test_2_its_own_unchanged_page_is_replaced_as_an_edit_with_a_backup(self):
        r, _ = self.build()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Changed", r.stdout)
        self.assertEqual(self.pages(), [f"{FIXED} Prep - ABC weekly.html"])
        last = self.log()[-1]
        self.assertEqual(last["op"], "edit")
        self.assertTrue((self.v.root / last["backup"]).is_file())

    def test_3_a_page_alan_edited_is_never_overwritten(self):
        page = self.v.root / ABC / "agendas" / f"{FIXED} Prep - ABC weekly.html"
        page.write_text(page.read_text(encoding="utf-8") + "<!-- Alan's note -->", encoding="utf-8")
        r, _ = self.build()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Alan's note", page.read_text(encoding="utf-8"))
        self.assertIn(f"{FIXED} Prep - ABC weekly (2).html", self.pages())

    def test_4_after_reading_outside_content_it_waits_on_the_card(self):
        py(self.v, "import reach; reach.start_run('r-1', 'ask', {}); reach.mark('r-1', 'read a transcript')")
        before, logged = self.pages(), len(self.log())
        r, reply = self.build()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("Needs approval", r.stdout)
        self.assertIn("on the card", r.stdout)
        self.assertEqual(self.pages(), before)                              # nothing written
        self.assertEqual(len(self.log()), logged)
        reqs = list((self.v.root / "system/staging/changes").glob("r-1-*.json"))
        self.assertEqual(len(reqs), 1)
        req = json.loads(reqs[0].read_text(encoding="utf-8"))
        self.assertTrue((self.v.root / req["from"]).is_file())              # the page waits in drafts for the card

    def test_5_the_server_write_is_unchanged(self):
        out = py(self.v, f"import prep_page, json; rel, _ = prep_page.build({KEY!r}, {json.dumps(json.dumps(REPLY))}); print(rel)")
        self.assertTrue(out.strip().splitlines()[-1].startswith(f"{ABC}/agendas/{FIXED} Prep - ABC weekly"), out)


class CalendarStepInAPlainChat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def decide(self, calls, mode):
        code = ("import json, reach; print(json.dumps([reach.hook_decision(t, i, " + repr(mode) + ", 'r-1') for t, i in "
                + repr(calls) + "]))")
        return json.loads(py(self.v, code))

    def steps(self, root):
        drafts = "system/staging/drafts/calendar.json"
        return [("Bash", {"command": "system/scripts/run sweep.py calendar-window"}),
                ("Write", {"file_path": drafts, "content": "{}"}),
                ("Write", {"file_path": f"{root}/{drafts}", "content": "{}"}),
                ("Bash", {"command": f"system/scripts/run sweep.py calendar {drafts}"}),
                ("Bash", {"command": f"python3 system/scripts/sweep.py calendar {root}/{drafts}"}),
                ("Bash", {"command": f"{root}/system/scripts/run sweep.py calendar {root}/{drafts}"}),
                ("Bash", {"command": f"python3 {root}/system/scripts/sweep.py calendar {drafts}"}),
                ("Bash", {"command": "system/scripts/run sweep.py transcripts todo"}),
                ("Bash", {"command": "system/scripts/run sweep.py transcripts record system/staging/drafts/facts.json"})]

    def test_every_step_passes_the_guard_in_either_mode(self):
        for root in (str(self.v.root), os.path.realpath(self.v.root)):
            for mode in ("ask", "confirmed"):
                calls = self.steps(root)
                for (_tool, inp), (ok, why) in zip(calls, self.decide(calls, mode)):
                    with self.subTest(mode=mode, call=inp):
                        self.assertTrue(ok, why)

    def test_what_is_not_a_creaite_script_is_still_refused(self):
        root = str(self.v.root)
        calls = [("Bash", {"command": "ls system/staging/drafts"}),
                 ("Bash", {"command": "cat system/staging/drafts/calendar.json"}),
                 ("Bash", {"command": f"cd {root} && system/scripts/run sweep.py calendar system/staging/drafts/calendar.json"}),
                 ("Bash", {"command": "python3 /tmp/elsewhere/system/scripts/sweep.py calendar x.json"}),
                 ("Bash", {"command": "/tmp/elsewhere/system/scripts/run sweep.py calendar x.json"}),
                 ("Bash", {"command": f"python3 {root}/system/scripts/permissions.py list"}),
                 ("Bash", {"command": f"python3 {root}/system/scripts/tracker.py apply"}),
                 ("Bash", {"command": f"python3 {root}/system/scripts/sweep.py calendar x.json | tail"})]
        for (_tool, inp), (ok, _why) in zip(calls, self.decide(calls, "ask")):
            with self.subTest(inp["command"]):
                self.assertFalse(ok, inp["command"])

    def test_the_calendar_is_saved_from_the_drafts_file(self):
        f = self.v.root / "system/staging/drafts/calendar.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"days": {"2026-10-12": [{"id": "e1", "start": "09:00", "end": "09:30", "title": "ABC weekly",
                                                          "where": "Teams", "teams": True, "organiser": True}]}}), encoding="utf-8")
        r = self.v.run("calendar", "system/staging/drafts/calendar.json", script="sweep.py", ok=False, cwd=self.v.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        saved = json.loads((self.v.root / "system/staging/calendar.json").read_text(encoding="utf-8"))
        self.assertIn("ABC weekly", json.dumps(saved))
        self.assertFalse(f.exists())                                        # BL-118: the input has done its job


if __name__ == "__main__":
    unittest.main()
