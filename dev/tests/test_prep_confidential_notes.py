"""BL-301 (v20-confidential-prep, insyncalan/creaite-plan#60): a note marked confidential is kept out of Prep, by plain code.

Run: python3 dev/tests/test_prep_confidential_notes.py     (quick tier: no Chrome)

A sample vault (the prep world: "ABC weekly" today) with two notes in the project's notes folder: an ordinary one and one marked
confidential. Covers: the context lists the ordinary note and only counts the confidential one (never its name); the research
prompt holds the ordinary note's path and the rule, never the confidential note's name or text; the shaping prompt says not to
open notes; a stand-in reply that cites the confidential note, quotes it in another finding, a question, an item's reason and the
summary is built into a page (and stored content) with the ordinary note's finding and none of the confidential one's text or
citation; a note marked confidential after the page was built is dropped from the stored page's view; and through the live server
(a stand-in Claude, no model is called) the Prep page run, its built page, the in-app view, the popup's brief, chips and focus
filter, and the dashboard's data never show the confidential note's text.
"""
import json
import os
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
import prep_page  # noqa: E402
from test_dashboard import TODAY  # noqa: E402
from test_prep_reimagined import py, world  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

KEY = "09:00|ABC weekly"
OPEN_TEXT = "The vendor will confirm the licence count by Friday"
SECRET = "The restructure plan stays under wraps until the board meets in November"
SECRET_WORD = "under wraps"
OPEN_REL = f"{ABC}/notes/Vendor call.md"
SECRET_REL = f"{ABC}/notes/Board view.md"


def note(title, body, confidential):
    return (f"---\ntitle: {title}\ncreated: {TODAY}\nupdated: {TODAY}\ntags: []\npinned: false\n"
            f"confidential: {'true' if confidential else 'false'}\n---\n\n{body}\n")


def notes_world(v):
    world(v)
    folder = v.root / ABC / "notes"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "Vendor call.md").write_text(note("Vendor call", OPEN_TEXT + ".", False), encoding="utf-8")
    (folder / "Board view.md").write_text(note("Board view", SECRET + ".", True), encoding="utf-8")


def reply():
    """A stand-in research reply: one finding from the ordinary note, and the confidential note cited, quoted and leaked everywhere."""
    return {"about": "The weekly check-in on the pilot.",
            "item_reasons": {"ABC-A-001": "Data access blocks UAT", "ABC-A-002": f"Because {SECRET.lower()}"},
            "notes": [{"text": OPEN_TEXT, "source": OPEN_REL, "date": TODAY.isoformat()},
                      {"text": "The board is weighing a reorganisation", "source": SECRET_REL, "date": TODAY.isoformat()},
                      {"text": "Mentioned in passing", "source": "Board view.md"},
                      {"text": f"Heard that {SECRET}", "source": "Email · From: Jane Doe · Subject: Catch-up · Sent: 2026-10-14"}],
            "questions": ["Is UAT booked?", f"Should we say {SECRET.lower()}?"], "m365": "searched"}


def clean(test, text, where):
    test.assertNotIn(SECRET_WORD, text, f"{where}: the confidential note's text")
    test.assertNotIn("Board view", text, f"{where}: the confidential note's name")
    test.assertNotIn("reorganisation", text, f"{where}: a finding citing the confidential note")


class Hold(unittest.TestCase):
    """hold_confidential on its own: a citation, a quote, a question, a reason and the summary."""

    HELD = [{"path": SECRET_REL.lower(), "real": "/vault/" + SECRET_REL.lower(), "name": "board view.md",
             "runs": {" ".join(prep_page._words(SECRET)[i:i + prep_page.QUOTE_WORDS])
                      for i in range(len(prep_page._words(SECRET)) - prep_page.QUOTE_WORDS + 1)}}]

    def test_cited_or_quoted_parts_are_dropped_and_the_rest_kept(self):
        r = dict(reply(), about=f"Note: {SECRET}")
        out, dropped = prep_page.hold_confidential(r, self.HELD)
        self.assertEqual([n["text"] for n in out["notes"]], [OPEN_TEXT])
        self.assertEqual(out["questions"], ["Is UAT booked?"])
        self.assertEqual(out["item_reasons"], {"ABC-A-001": "Data access blocks UAT"})
        self.assertEqual(out["about"], "")
        self.assertEqual(dropped, 6)
        self.assertEqual(len(r["notes"]), 4, "the reply given is never changed")

    def test_a_few_shared_words_are_not_a_quote(self):
        out, dropped = prep_page.hold_confidential({"notes": [{"text": "The board meets in November", "source": "ABC-A-001"}]}, self.HELD)
        self.assertEqual(dropped, 0)
        self.assertEqual(len(out["notes"]), 1)

    def test_no_confidential_notes_changes_nothing(self):
        self.assertEqual(prep_page.hold_confidential(reply(), []), (reply(), 0))


class InTheVault(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        notes_world(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def context(self):
        return py(self.v, f"import prep_page; print(json.dumps(prep_page.context({KEY!r})))")

    def test_1_the_context_lists_the_ordinary_note_and_only_counts_the_confidential_one(self):
        res = self.context()["research"]
        self.assertEqual(res["notes"], [OPEN_REL])
        self.assertEqual(res["confidential_notes_left_out"], 1)
        clean(self, json.dumps(self.context()), "context")

    def test_2_the_research_prompt_has_the_rule_and_never_the_confidential_note(self):
        p = py(self.v, f"import prep_page; print(json.dumps(prep_page.prompt(prep_page.context({KEY!r}))))")
        self.assertIn(OPEN_REL, p)
        self.assertIn("read only the notes listed under research", p)
        self.assertIn("Never open, read, search or cite any other file in a notes folder", p)
        clean(self, p, "prompt")

    def test_3_the_shaping_prompt_says_not_to_open_notes(self):
        r = subprocess.run([sys.executable, "system/scripts/drafts.py", "context"], cwd=self.v.root, capture_output=True, text=True,
                           input=json.dumps({"kind": "shape", "key": KEY, "instruction": "Focus on ABC-A-001."}))
        ctx = json.loads(r.stdout)
        self.assertIn("Never open, read or search a file in a notes folder", ctx["prompt"])
        clean(self, ctx["prompt"], "shaping prompt")
        self.assertFalse(any("/notes/" in json.dumps(s) for s in ctx["sources"]), ctx["sources"])

    def test_4_the_built_page_and_its_stored_content_keep_the_ordinary_note_only(self):
        rel = py(self.v, f"import prep_page; rel, _ = prep_page.build({KEY!r}, {json.dumps(reply())!r}); print(json.dumps(rel))")
        page = (self.v.root / rel).read_text(encoding="utf-8")
        self.assertIn(OPEN_TEXT, page)
        self.assertIn("Vendor call.md", page)                                     # the ordinary note is cited
        self.assertIn("Is UAT booked?", page)
        self.assertIn("Data access blocks UAT", page)
        clean(self, page, "page")
        for f in (self.v.root / "system/staging/prep").glob("*.json"):
            clean(self, f.read_text(encoding="utf-8"), f"stored content {f.name}")
        mo = py(self.v, f"import prep_view; print(json.dumps(prep_view.view({KEY!r})))")["model"]
        self.assertEqual([n["text"] for n in mo["notes"]], [OPEN_TEXT])
        clean(self, json.dumps(mo), "in-app view")

    def test_5_a_note_marked_confidential_later_is_dropped_from_the_stored_page(self):
        v = Vault()
        try:
            notes_world(v)
            (v.root / OPEN_REL).write_text(note("Vendor call", OPEN_TEXT + ".", False), encoding="utf-8")
            py(v, f"import prep_page; rel, _ = prep_page.build({KEY!r}, {json.dumps({'notes': reply()['notes'][:1]})!r}); print(1)")
            first = py(v, f"import prep_view; print(json.dumps(prep_view.view({KEY!r})))")["model"]
            self.assertEqual([n["text"] for n in first["notes"]], [OPEN_TEXT])
            (v.root / OPEN_REL).write_text(note("Vendor call", OPEN_TEXT + ".", True), encoding="utf-8")
            later = py(v, f"import prep_view; print(json.dumps(prep_view.view({KEY!r})))")["model"]
            self.assertEqual(later["notes"], [])
            self.assertNotIn(OPEN_TEXT, json.dumps(later))
        finally:
            v.cleanup()


FAKE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
p = args[args.index("-p") + 1]
open(__file__ + ".calls", "a", encoding="utf-8").write(json.dumps({"prompt": p}) + "\n")
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-p"})
reply = open(__file__ + ".reply", encoding="utf-8").read()
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-p"})
'''


class ThroughTheServer(unittest.TestCase):
    """The Prep page button's run and build, the in-app view and the popup's routes, with a stand-in Claude."""

    @classmethod
    def setUpClass(cls):
        import re
        from test_live_server import free_port
        cls.v = v = Vault()
        notes_world(v)
        fake = v.root / "fake_prep.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        Path(str(fake) + ".reply").write_text(json.dumps(reply()), encoding="utf-8")
        cls.calls = Path(str(fake) + ".calls")
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        cls.html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', cls.html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body, stream=False):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read().decode()
        if stream:
            return [json.loads(ln[6:]) for ln in raw.splitlines() if ln.startswith("data: ")]
        return json.loads(raw)

    def test_1_the_prep_page_run_and_build(self):
        evs = self.post("/api/prep/page", {"key": KEY, "run": "p-conf-notes"}, stream=True)
        self.assertTrue(any(e.get("type") == "done" for e in evs), evs[-3:])
        prompt = json.loads(self.calls.read_text().splitlines()[-1])["prompt"]
        self.assertIn(OPEN_REL, prompt)
        clean(self, prompt, "the prompt Claude was given")
        built = self.post("/api/prep/build", {"run": "p-conf-notes"})
        self.assertTrue(built["ok"], built)
        self.assertIn(OPEN_TEXT, built["html"])
        clean(self, built["html"], "the page the server built")
        clean(self, (self.v.root / built["path"]).read_text(encoding="utf-8"), "the Agendas file")
        opened = self.post("/api/prep/open", {"path": built["path"]})
        clean(self, opened["html"], "/api/prep/open")
        v = self.post("/api/prep/view", {"key": KEY})
        self.assertTrue(v["ok"] and v["stored"], v)
        self.assertEqual([n["text"] for n in v["model"]["notes"]], [OPEN_TEXT])
        clean(self, json.dumps(v), "/api/prep/view")

    def test_2_the_popup_and_the_dashboard_data_never_show_it(self):
        for path, body in (("/api/prep/brief", {"key": KEY}), ("/api/prep/chips", {"key": KEY}),
                           ("/api/prep/filter", {"key": KEY, "focus": ["ABC-A-001"]}), ("/api/prep/focus", {"key": KEY})):
            with self.subTest(path):
                clean(self, json.dumps(self.post(path, body)), path)
        import re
        data = re.search(r'id="data">(.*?)</script>', self.html, re.S).group(1)
        self.assertNotIn(SECRET_WORD, data, "the dashboard's data")
        self.assertNotIn("restructure plan", data.lower(), "the dashboard's data")


if __name__ == "__main__":
    unittest.main()
