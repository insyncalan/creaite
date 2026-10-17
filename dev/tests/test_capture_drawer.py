"""BL-301 C: the capture drawer (⌘⇧N). The project guessed from the register's signals with its reason (capture.py, the rules
cx-minutes uses), the draft kept as Alan types, the note written through filechange.py on Done (Unfiled when nothing names a
project), "Note for this meeting", "note: …" in ask creaite, and the drawer itself in a real browser against the live server.

Run: python3 dev/tests/test_capture_drawer.py   (the browser tests need Google Chrome; skipped otherwise)
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
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, free_port  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402
import notes_find_fixture as fx  # noqa: E402

META, SHIFT = 4, 8
TODAY = date.today().isoformat()
PORTFOLIO_NOTES = "projects/_portfolio/notes"


def calendar(v):
    """Today's saved calendar: an ABC meeting with attendees, a private one, a confidential one."""
    (v.root / "system/staging/calendar.json").write_text(json.dumps({"fetched": TODAY + " 07:00", "days": {TODAY: [
        {"start": "09:00", "end": "09:30", "title": "ABC Steering", "where": "Teams", "organiser": True,
         "attendees": [{"name": "Alan Carter"}, {"name": "Jane Doe"}, {"name": "Omar Ali"}]},
        {"start": "11:00", "end": "12:00", "title": "Dentist", "private": True},
        {"start": "14:00", "end": "15:00", "title": "Board pay review", "sensitivity": "confidential",
         "attendees": [{"name": "Someone Secret"}]}]}}), encoding="utf-8")


def load_vault(v):
    populate(v)
    calendar(v)
    v.run(script="build_dashboard.py")


class Guess(unittest.TestCase):
    """The register's signals, by cx-minutes' rules: strong and medium assign, one keyword doesn't, a conflict doesn't."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        populate(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def guess(self, text, active=None):
        code = f"import json, capture\nprint(json.dumps(capture.guess({text!r}, {active!r})))"
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts')\n" + code], cwd=self.v.root,
                           capture_output=True, text=True, check=True)
        return json.loads(r.stdout)

    def test_strong_and_medium_signals_assign_with_their_reason(self):
        g = self.guess("[ABC] go-live slips a week")
        self.assertEqual((g["code"], g["strength"]), ("ABC", "strong"))
        self.assertTrue(g["reason"].startswith("guessed from “ABC”"))
        g = self.guess("Omar Ali thinks the paper can go to the board")
        self.assertEqual((g["code"], g["reason"]), ("ABC", "guessed from “Omar Ali”"))
        g = self.guess("Omar thinks so too")                             # a first name only ABC's stakeholders have
        self.assertEqual((g["code"], g["reason"]), ("ABC", "guessed from “Omar”"))
        g = self.guess("MVP scope and data access both slip")            # two keywords
        self.assertEqual(g["code"], "ABC")
        self.assertIn("“MVP”", g["reason"])
        g = self.guess("Mail from sara@client.com about it")              # a client domain
        self.assertEqual(g["code"], "ABC")
        self.assertEqual(self.guess("The Digital Enablement plan")["code"], "DEF")   # the project's name

    def test_no_guess_is_unfiled_and_says_why(self):
        g = self.guess("Lunch with the team")
        self.assertEqual((g["code"], g["candidates"]), (None, []))
        self.assertEqual(g["reason"], "nothing in the note names a project yet")
        g = self.guess("The MVP is fine")                                  # one keyword: weak
        self.assertEqual((g["code"], g["strength"], g["candidates"]), (None, "weak", ["ABC"]))
        g = self.guess("ABC and DEF both slipping")                       # a conflict
        self.assertEqual((g["code"], g["candidates"]), (None, ["ABC", "DEF"]))
        self.assertIn("Example Programme or Digital Enablement", g["reason"])
        self.assertIsNone(self.guess("[ABC] closing", active=["DEF"])["code"])   # only active projects
        self.assertIsNone(self.guess("ABCD is another thing")["code"])           # a code is a whole token

    def test_shared_names_and_exclude_words(self):
        reg = self.v.root / "projects/_portfolio/project-register.md"
        before = reg.read_text(encoding="utf-8")
        try:
            self.assertIsNone(self.guess("Example Person called")["code"])         # under Shared: never a signal
            reg.write_text(before.replace("| MVP, data access, go-live |  |  |", "| MVP, data access, go-live |  | sandbox |"),
                           encoding="utf-8")
            self.assertIsNone(self.guess("[ABC] read-only sandbox first")["code"])   # Exclude rules ABC out
        finally:
            reg.write_text(before, encoding="utf-8")


class Routes(unittest.TestCase):
    """/api/notes/capture/*: the draft, Done through filechange.py, Unfiled, a taken name, the meeting, recent notes."""

    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        load_vault(v)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "CREAITE_PORT": str(cls.port)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 30
        while True:
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                if time.time() > deadline:
                    raise
                time.sleep(0.1)
        page = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read() or b"{}")

    def log(self):
        f = self.v.root / "system/config/files-log.jsonl"
        return [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []

    def test_guess_route(self):
        st, r = self.post("/api/notes/capture/guess", {"title": "", "body": "Jane Doe wants the plan"})
        self.assertEqual((st, r["code"], r["reason"]), (200, "ABC", "guessed from “Jane Doe”"))
        st, r = self.post("/api/notes/capture/guess", {"title": "", "body": "Lunch"})
        self.assertEqual((r["code"], r["candidates"]), (None, []))

    def test_draft_kept_then_done_writes_the_note_through_filechange(self):
        st, r = self.post("/api/notes/capture/draft", {"id": "drawer-test-1", "code": "ABC", "title": "Sara on the extract tool",
                                                       "body": "She'd accept a read-only sandbox first.\n"})
        self.assertEqual(st, 200)
        draft = self.v.root / "system/staging/drafts/notes/capture-drawer-test-1.json"
        self.assertTrue(draft.exists())
        self.assertEqual(json.loads(draft.read_text())["title"], "Sara on the extract tool")
        st, rec = self.post("/api/notes/capture/recent", {})
        self.assertIn("drawer-test-1", [d["id"] for d in rec["drafts"]])
        st, r = self.post("/api/notes/capture/done", {"id": "drawer-test-1", "code": "ABC", "title": "Sara on the extract tool",
                                                      "body": "She'd accept a read-only sandbox first.\n"})
        self.assertEqual((st, r["ok"], r["code"]), (200, True, "ABC"))
        self.assertEqual(r["path"], f"{ABC}/notes/Sara on the extract tool.md")
        self.assertFalse(draft.exists())                                   # the draft goes once the note is written
        text = (self.v.root / r["path"]).read_text()
        self.assertTrue(text.startswith("---\ntitle: Sara on the extract tool\ncreated: "))
        self.assertIn("confidential: false\n---\n\nShe'd accept a read-only sandbox first.\n", text)
        last = self.log()[-1]
        self.assertEqual((last["op"], last["via"], last["path"]), ("create", "dashboard", r["path"]))   # logged, undoable
        st, again = self.post("/api/notes/capture/done", {"code": "ABC", "title": "Sara on the extract tool", "body": "Second."})
        self.assertEqual(again["path"], f"{ABC}/notes/Sara on the extract tool (2).md")   # never overwrites
        st, rec = self.post("/api/notes/capture/recent", {})
        self.assertEqual(rec["notes"][0]["title"], "Sara on the extract tool")
        out = subprocess.run([sys.executable, "system/scripts/filechange.py", "undo"], cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertFalse((self.v.root / again["path"]).exists())
        (self.v.root / r["path"]).unlink()

    def test_unfiled_auto_and_refusals(self):
        st, r = self.post("/api/notes/capture/done", {"code": "auto", "body": "Ideas for portfolio reporting\nMore later."})
        self.assertEqual((r["ok"], r["code"]), (True, "_portfolio"))
        self.assertEqual(r["path"], f"{PORTFOLIO_NOTES}/Ideas for portfolio reporting.md")   # title from the first line
        self.assertEqual(r["reason"], "nothing in the note names a project yet")
        (self.v.root / r["path"]).unlink()
        st, r = self.post("/api/notes/capture/done", {"code": "auto", "body": "Omar says the go-live is fine"})
        self.assertEqual(r["code"], "ABC")
        self.assertTrue(r["reason"].startswith("guessed from “Omar”"))
        (self.v.root / r["path"]).unlink()
        self.assertEqual(self.post("/api/notes/capture/done", {"code": "ABC", "body": "  "})[0], 400)
        self.assertEqual(self.post("/api/notes/capture/done", {"code": "ZZZ", "body": "x"})[0], 400)
        self.assertEqual(self.post("/api/notes/capture/done", {"code": "abc; rm", "body": "x"})[0], 400)
        self.assertEqual(self.post("/api/notes/capture/done", {"code": "ABC", "body": "x", "template": "nope"})[0], 400)
        self.assertEqual(self.post("/api/notes/capture/draft", {"id": "../x", "body": "x"})[0], 400)
        self.assertEqual(self.post("/api/notes/capture/done", {"code": "ABC", "body": "x" * 100001})[0], 400)

    def test_confidential_switch_marks_the_note(self):
        """Alan, 14-10-2026: the drawer's Confidential switch (off by default) is written to the note's front matter, as notes.py
        records it, so search keeps its text from Claude; the draft keeps it too. Only a real true sets it."""
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import notes
        st, r = self.post("/api/notes/capture/draft", {"id": "drawer-conf-1", "code": "ABC", "title": "Pay talks",
                                                       "body": "Private.\n", "confidential": True})
        self.assertEqual(st, 200)
        st, rec = self.post("/api/notes/capture/recent", {})
        self.assertIs(next(d for d in rec["drafts"] if d["id"] == "drawer-conf-1")["confidential"], True)
        st, r = self.post("/api/notes/capture/done", {"id": "drawer-conf-1", "code": "ABC", "title": "Pay talks",
                                                      "body": "Private.\n", "confidential": True})
        self.assertEqual((st, r["ok"]), (200, True))
        f = self.v.root / r["path"]
        self.assertIn("confidential: true\n", f.read_text())
        self.assertTrue(notes.is_confidential(f))
        f.unlink()
        for odd in ("yes", 1, "true", None):                                    # off unless the switch sent true
            st, r = self.post("/api/notes/capture/done", {"code": "ABC", "title": "Open talks", "body": "x", "confidential": odd})
            f = self.v.root / r["path"]
            self.assertIn("confidential: false\n", f.read_text())
            self.assertFalse(notes.is_confidential(f))
            f.unlink()

    def test_meeting_fills_the_working_session(self):
        st, r = self.post("/api/notes/capture/start", {"meeting": {"day": TODAY, "start": "09:00", "title": "ABC Steering"}})
        self.assertEqual((st, r["template"], r["title"], r["date"], r["code"]), (200, "working-session", "ABC Steering", TODAY, "ABC"))
        self.assertEqual(r["with"], ["Jane Doe", "Omar Ali"])                 # Alan himself left out
        self.assertIn("## Purpose", r["body"])
        st, r = self.post("/api/notes/capture/start", {"meeting": {"day": TODAY, "start": "14:00", "title": "Board pay review"}})
        self.assertEqual((st, r["with"]), (200, []))                          # confidential: title and date only
        self.assertEqual(self.post("/api/notes/capture/start", {"meeting": {"day": TODAY, "start": "11:00", "title": "Dentist"}})[0], 404)
        st, done = self.post("/api/notes/capture/done", {"code": "ABC", "title": "ABC Steering", "body": "Agreed the plan.\n",
                                                         "template": "working-session", "date": TODAY, "with": ["Jane Doe", "Omar Ali"]})
        text = (self.v.root / done["path"]).read_text()
        self.assertIn(f"date: {TODAY}\nwith: [Jane Doe, Omar Ali]\n", text)
        (self.v.root / done["path"]).unlink()

    def test_old_quick_capture_route_is_gone(self):
        self.assertEqual(self.post("/api/capture", {"notes": "x", "code": "ABC"})[0], 404)


class Drawer(LiveBrowserCase):
    """The drawer in a real browser against the live server."""

    shared_server = True

    @classmethod
    def load(cls, v):
        load_vault(v)
        cls.fake = fx.install(v)           # Done and find updates opens Find updates, which runs "Claude": never the real one

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake)}

    def open(self):
        b = self.b
        b.eval("document.body.focus()")
        b.key("N", META | SHIFT)
        b.wait("document.getElementById('capDrawer')&&!document.getElementById('capDrawer').hidden&&!!document.getElementById('capBody').cxed")
        b.wait("document.activeElement===document.getElementById('capBody')", 5)

    def notes(self, folder=f"{ABC}/notes"):
        d = self.v.root / folder
        return sorted(p.name for p in d.glob("*.md")) if d.is_dir() else []

    def tearDown(self):
        for d in (self.v.root / ABC / "notes", self.v.root / PORTFOLIO_NOTES):
            for f in d.glob("*.md") if d.is_dir() else []:
                f.unlink()
        for f in (self.v.root / "system/staging/drafts/notes").glob("capture-*.json"):      # the / menu tests leave a draft behind when they end on Esc
            f.unlink()
        super().tearDown()

    def test_shortcut_opens_from_any_page_guesses_and_done_saves(self):
        b = self.b
        b.eval("go('work')")
        b.wait("VIEW==='work'")
        self.open()
        self.assertEqual(b.eval("VIEW"), "work")                                       # the page stays where it was
        got = b.eval("""(()=>{ const d=document.getElementById('capDrawer');
          return [d.getAttribute('role'), d.getAttribute('aria-labelledby'), document.getElementById('capH').textContent,
                  document.getElementById('capProj').value, document.getElementById('capBody').getAttribute('aria-label')]; })()""")
        self.assertEqual(got, ["dialog", "capH", "New note", "", "Note"])               # Unfiled until something names a project
        b.type("Omar Ali thinks the paper can go on 21-10")
        b.wait("document.getElementById('capProj').value==='ABC'", 10)
        self.assertEqual(b.eval("document.getElementById('capWhy').textContent"), "guessed from “Omar Ali”")
        b.wait("/Saved \\d/.test(document.getElementById('capSaved').textContent)", 10)
        self.assertTrue(list((self.v.root / "system/staging/drafts/notes").glob("capture-*.json")))
        b.eval("(()=>{ const s=document.getElementById('capProj'); s.value='DEF'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("document.getElementById('capWhy').textContent==='chosen by you'")
        b.type(" with DEF")                                                            # Alan's choice stays
        b.pump(1)
        self.assertEqual(b.eval("document.getElementById('capProj').value"), "DEF")
        b.eval("(()=>{ const s=document.getElementById('capProj'); s.value='ABC'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.click("#capDone")
        b.wait("document.getElementById('capDrawer').hidden", 10)
        self.assertEqual(self.notes(), ["Omar Ali thinks the paper can go on.md"])   # the first eight words
        self.assertIn("Note saved", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(list((self.v.root / "system/staging/drafts/notes").glob("capture-*.json")), [])
        self.assertEqual(b.eval("VIEW"), "work")

    def test_escape_keeps_the_draft_and_returns_focus(self):
        b = self.b
        b.eval("go('today')")
        b.eval("document.getElementById('askBtn')&&document.getElementById('askBtn').focus()")
        opener = b.eval("document.activeElement&&document.activeElement.id")
        b.key("N", META | SHIFT)
        b.wait("document.activeElement===document.getElementById('capBody')", 10)
        b.type("Remember the budget line")
        b.key("Escape")
        b.wait("document.getElementById('capDrawer').hidden")
        self.assertEqual(b.eval("document.activeElement&&document.activeElement.id"), opener)
        b.wait("/Note kept/.test(document.getElementById('snackT').textContent)")
        b.wait("document.querySelector('#capDrawer')&&true")
        self.assertEqual(self.notes(PORTFOLIO_NOTES), [])                          # nothing written
        b.pump(0.5)
        drafts = list((self.v.root / "system/staging/drafts/notes").glob("capture-*.json"))
        self.assertEqual(len(drafts), 1)
        self.open()                                                                 # ⌘⇧N carries on
        self.assertEqual(b.eval("edValue(document.getElementById('capBody'))").strip(), "Remember the budget line")
        b.click("#capDone")
        b.wait("document.getElementById('capDrawer').hidden", 10)
        self.assertEqual(self.notes(PORTFOLIO_NOTES), ["Remember the budget line.md"])   # Unfiled
        b.key("N", META | SHIFT)
        b.wait("document.querySelectorAll('#capDrawer .caprecent .caprow').length>0", 10)
        self.assertIn("Remember the budget line", b.eval("document.querySelector('#capDrawer .caprecent').textContent"))
        self.assertIn("Unfiled", b.eval("document.querySelector('#capDrawer .caprecent').textContent"))

    NOTE_OPEN = ("VIEW==='notes'&&noteCur.value&&noteCur.value.code===%s&&noteCur.value.path===%s"
                 "&&!!document.querySelector('#v-notes .nbody.ProseMirror')&&!document.getElementById('v-notes').hidden")

    def note_open(self, code, path, find):
        """The note is open in the Notes tab (B's view), with Find updates beside it or not (E's panel)."""
        b = self.b
        b.wait(self.NOTE_OPEN % (json.dumps(code), json.dumps(path)), 20)
        self.assertTrue(b.eval("document.getElementById('v-cockpit').hidden"))      # not left on the project's Overview
        on = "document.querySelector('.nlist .ni.on')"
        self.assertEqual(b.eval(f"{on}&&{on}.textContent.includes({json.dumps(path.rsplit('/', 1)[1][:-3])})"), True)   # chosen in the list
        file = urllib.request.quote(path.rsplit("/", 1)[1], safe="")
        if find:
            b.wait("noteFind.value&&!!document.querySelector('#noteSide aside.fu')", 20)
            self.assertEqual(b.eval("document.getElementById('noteFind').getAttribute('aria-expanded')"), "true")
            b.wait(f"location.hash==={json.dumps(f'#notes={code}&n={file}&find=1')}")
        else:
            b.pump(0.5)
            self.assertFalse(b.eval("noteFind.value"))
            self.assertIsNone(b.eval("document.querySelector('#noteSide aside.fu')"))
            self.assertEqual(b.eval("location.hash"), f"#notes={code}&n={file}")

    def test_done_and_find_updates_opens_the_note_with_find_updates(self):
        b = self.b
        b.eval("go('work')")
        b.wait("VIEW==='work'")
        self.open()
        b.type("[ABC] Sara agreed the sandbox")
        b.wait("document.getElementById('capProj').value==='ABC'", 10)
        b.click("#capFind")
        b.wait("document.getElementById('capDrawer').hidden", 10)
        self.note_open("ABC", f"{ABC}/notes/ABC Sara agreed the sandbox.md", True)
        b.eval("history.back()")                                                       # Back returns to the page it came from
        b.wait("VIEW==='work'", 10)
        self.open()                                                                  # Unfiled: the portfolio's notes
        b.type("Lunch idea")
        b.pump(1)
        b.click("#capFind")
        b.wait("document.getElementById('capDrawer').hidden", 10)
        self.note_open("_portfolio", f"{PORTFOLIO_NOTES}/Lunch idea.md", True)

    def test_a_recent_note_opens_in_the_notes_tab(self):
        b = self.b
        self.open()
        b.type("[ABC] Budget line agreed")
        b.wait("document.getElementById('capProj').value==='ABC'", 10)
        b.click("#capDone")
        b.wait("document.getElementById('capDrawer').hidden", 10)
        b.eval("go('today')")
        b.wait("VIEW==='today'")
        self.open()
        row = "[...document.querySelectorAll('#capDrawer .caprecent .caprow')].find(x=>x.textContent.includes('ABC Budget line agreed'))"
        b.wait(f"!!{row}", 10)
        b.eval(f"{row}.click()")
        b.wait("document.getElementById('capDrawer').hidden", 10)
        self.note_open("ABC", f"{ABC}/notes/ABC Budget line agreed.md", False)
        self.assertEqual(b.errors, [])

    def test_note_for_this_meeting(self):
        b = self.b
        b.eval("go('today')")
        b.wait("document.querySelectorAll('#dayMeets .dm').length>0")
        self.assertEqual(b.eval("document.querySelectorAll('#dayMeets .mnote').length"), 0)   # #140: the Note link is gone from the band
        b.eval("openCapture({meeting:{day:TODAY,start:'09:00',title:'ABC Steering'}})")   # the drawer's own entry for a meeting stays
        b.wait("!document.getElementById('capDrawer').hidden&&document.getElementById('capTitle').value==='ABC Steering'", 10)
        got = b.eval("""[document.getElementById('capH').textContent, document.getElementById('capProj').value,
          document.getElementById('capWhy').textContent, document.querySelector('#capDrawer .capmeet').textContent,
          edValue(document.getElementById('capBody'))]""")
        dd = f"{TODAY[8:10]}-{TODAY[5:7]}-{TODAY[:4]}"
        self.assertEqual(got[:4], ["Note for this meeting", "ABC", "from the meeting's title", f"Working session · {dd} · with Jane Doe, Omar Ali"])
        self.assertIn("## Purpose", got[4])
        b.key("Enter", META)                                                         # ⌘↵ is Done
        b.wait("document.getElementById('capDrawer').hidden", 10)
        text = (self.v.root / ABC / "notes/ABC Steering.md").read_text()
        self.assertIn(f"date: {TODAY}\nwith: [Jane Doe, Omar Ali]", text)

    def test_note_in_ask_creaite_and_new_note_in_cmdk(self):
        b = self.b
        b.eval("handle('note: DEF portal walkthrough booked for March')")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>/Saved the note/.test(m.textContent))", 10)
        said = b.eval("[...document.querySelectorAll('#chLog .msg.a')].map(m=>m.textContent).pop()")
        self.assertIn("Saved the note “DEF portal walkthrough booked for March” in Digital Enablement", said)
        self.assertEqual(self.notes("projects/DEF Digital Enablement/notes"), ["DEF portal walkthrough booked for March.md"])
        for f in (self.v.root / "projects/DEF Digital Enablement/notes").glob("*.md"):
            f.unlink()
        self.assertIn("New note", b.eval("ckItems('note').map(i=>i.l)"))
        self.assertFalse(b.eval("!!document.getElementById('isecQuick')||!!document.getElementById('qcNotes')"))   # FR-71's form is gone

    def test_n_is_the_second_key_and_not_while_typing(self):
        """Alan, 14-10-2026: N opens the drawer too (⌘⇧N is Chrome's incognito window in an ordinary tab), but never while typing."""
        b = self.b
        b.eval("go('work')")
        b.wait("VIEW==='work'")
        b.eval("document.activeElement&&document.activeElement.blur(); document.body.focus()")
        b.key("n")
        b.wait("!document.getElementById('capDrawer').hidden&&document.activeElement===document.getElementById('capBody')", 10)
        self.assertEqual(b.eval("VIEW"), "work")
        b.key("Escape")
        b.wait("document.getElementById('capDrawer').hidden")
        b.eval("(()=>{ const i=document.createElement('input'); i.id='nTyping'; document.body.appendChild(i); i.focus(); })()")
        b.key("n")
        b.pump(0.5)
        self.assertTrue(b.eval("document.getElementById('capDrawer').hidden"))         # typing an n in a box stays typing
        b.eval("document.getElementById('nTyping').remove()")

    def test_confidential_switch_default_off_and_saved(self):
        b = self.b
        self.open()
        got = b.eval("""(()=>{ const s=document.getElementById('capConf');
          return [s.type, s.getAttribute('role'), s.checked, s.closest('label').textContent.trim()]; })()""")
        self.assertEqual(got, ["checkbox", "switch", False, "Confidential"])            # off by default, a labelled switch
        b.type("[ABC] Pay review thoughts")
        b.wait("document.getElementById('capProj').value==='ABC'", 10)
        b.click("#capConf")
        b.wait("document.getElementById('capConf').checked")
        self.assertIn("Claude reads it only if you say yes", b.eval("document.querySelector('#capDrawer .capconf').textContent"))
        b.click("#capDone")
        b.wait("document.getElementById('capDrawer').hidden", 10)
        text = (self.v.root / ABC / "notes/ABC Pay review thoughts.md").read_text()
        self.assertIn("confidential: true\n", text)
        self.open()
        self.assertFalse(b.eval("document.getElementById('capConf').checked"))          # the next note starts off again

    # ---- #122 step B: the shared / menu in the drawer -----------------------------------------------------------------

    CAP_MENU = "document.querySelector('.slashmenu')"

    def cap_menu(self):
        b = self.b
        b.type("/")
        b.wait(f"!!{self.CAP_MENU}", 5)
        b.pump(0.15)
        return b.eval(f"""(()=>{{ const v=document.getElementById('capBody').cxed.editor.view, c=v.coordsAtPos(v.state.selection.from),
          m={self.CAP_MENU}, r=m.getBoundingClientRect(), d=document.getElementById('capDrawer');
          return {{ caretBottom:c.bottom, top:r.top, left:r.left, right:r.right, bottom:r.bottom, vw:document.documentElement.clientWidth, vh:innerHeight,
            pos:getComputedStyle(m).position, z:+getComputedStyle(m.closest('.slashroot')||m).zIndex||+getComputedStyle(m).zIndex,
            drawerZ:+getComputedStyle(d).zIndex, inDrawer:d.contains(m), flipped:m.dataset.side }}; }})()""")

    def test_the_slash_menu_opens_at_the_caret_in_the_drawer_at_1400_and_900(self):
        b = self.b
        for width in (1400, 900):
            b.resize(width, 900)
            self.open()
            b.type("Line one")
            b.key("Enter")
            g = self.cap_menu()
            self.assertEqual(g["pos"], "fixed", g)
            self.assertLessEqual(abs(g["top"] - (g["caretBottom"] + 4)), 4, f"{width}: at the caret {g}")
            self.assertGreaterEqual(g["left"], 0)
            self.assertLessEqual(g["right"], g["vw"], "inside the window")
            self.assertGreater(g["z"], g["drawerZ"], "above the drawer")
            self.assertEqual(b.eval("document.querySelectorAll('.slashmenu').length"), 1)
            b.key("Escape")
            b.key("Escape")
            b.wait("document.getElementById('capDrawer').hidden", 5)
        b.resize(1400, 900)

    def test_the_drawers_rows_are_the_notes_rows_it_can_do(self):
        b = self.b
        self.open()
        self.cap_menu()
        rows = b.eval("[...document.querySelectorAll('.slashmenu [role=option][data-slash]')].map(o=>o.dataset.slash)")
        self.assertEqual(rows, ["text", "h1", "h2", "h3", "ul", "ol", "task", "quote", "codeblock", "link"],
                         "no [[ @ # lists, table, image or templates yet (step C): a row the drawer cannot do is not offered")
        b.type("head")
        b.pump(0.1)
        self.assertEqual(b.eval("[...document.querySelectorAll('.slashmenu [role=option][data-slash]')].map(o=>o.dataset.slash)"), ["h1", "h2", "h3"])

    def test_enter_inserts_and_done_saves_the_note_with_the_right_markdown(self):
        b = self.b
        self.open()
        b.type("Weekly thoughts")
        b.key("Enter")
        b.type("/head")
        b.wait(f"!!{self.CAP_MENU}", 5)
        b.key("ArrowDown")                                      # Heading 2
        b.key("Enter")
        b.wait(f"!{self.CAP_MENU}", 5)
        b.type("Risks")
        b.key("Enter")
        b.type("/check")
        b.wait(f"!!{self.CAP_MENU}", 5)
        b.key("Enter")
        b.type("call Omar")
        self.assertEqual(b.eval("edValue(document.getElementById('capBody'))").strip(), "Weekly thoughts\n\n## Risks\n\n- [ ] call Omar")
        self.assertEqual(b.eval("document.getElementById('capDrawer').hidden"), False)
        b.click("#capDone")
        b.wait("document.getElementById('capDrawer').hidden", 10)
        name = self.notes(PORTFOLIO_NOTES) + self.notes()
        self.assertEqual(len(name), 1, name)
        folder = PORTFOLIO_NOTES if self.notes(PORTFOLIO_NOTES) else f"{ABC}/notes"
        text = (self.v.root / folder / name[0]).read_text(encoding="utf-8")
        self.assertIn("## Risks\n", text)
        self.assertIn("- [ ] call Omar", text)
        self.assertNotIn("/head", text)
        self.assertNotIn("/check", text)

    def test_escape_closes_the_menu_first_and_a_second_escape_closes_the_drawer(self):
        b = self.b
        self.open()
        b.type("Keep this")
        b.key("Enter")
        self.cap_menu()
        b.key("Escape")
        b.wait(f"!{self.CAP_MENU}", 5)
        self.assertEqual(b.eval("document.getElementById('capDrawer').hidden"), False, "the first Esc only closes the menu")
        self.assertIn("/", b.eval("edValue(document.getElementById('capBody'))"), "and leaves the typed text")
        self.assertEqual(b.eval("document.activeElement===document.getElementById('capBody')"), True)
        b.key("Escape")
        b.wait("document.getElementById('capDrawer').hidden", 5)

    def test_cmd_enter_does_not_save_while_the_menu_is_open_and_does_after(self):
        b = self.b
        self.open()
        b.type("Save me")
        b.key("Enter")
        self.cap_menu()
        b.key("Enter", META)
        b.pump(0.5)
        self.assertEqual(b.eval("document.getElementById('capDrawer').hidden"), False, "⌘↵ waits while the menu is open")
        self.assertEqual(self.notes(PORTFOLIO_NOTES), [])
        b.key("Escape")
        b.wait(f"!{self.CAP_MENU}", 5)
        b.key("Enter", META)
        b.wait("document.getElementById('capDrawer').hidden", 10)
        self.assertEqual(len(self.notes(PORTFOLIO_NOTES)), 1)

    def test_the_drawer_menu_in_dark_keeps_its_colours(self):
        b = self.b
        self.open()
        b.eval("document.documentElement.dataset.theme='dark'")
        self.cap_menu()
        got = b.eval("""(()=>{ const m=document.querySelector('.slashmenu'), on=m.querySelector('.r.on'), off=m.querySelector('.r:not(.on)'), c=e=>getComputedStyle(e);
          return { bg:c(m).backgroundColor, on:c(on).backgroundColor, off:c(off).backgroundColor }; })()""")
        self.assertNotEqual(got["on"], got["off"])
        self.assertNotEqual(got["bg"], "rgb(255, 255, 255)")
        b.eval("delete document.documentElement.dataset.theme")

    def test_fits_320_and_dark(self):
        b = self.b
        b.resize(320, 700)
        self.open()
        b.type("A note on a narrow screen")
        got = b.eval("""(()=>{ const d=document.getElementById('capDrawer'), r=d.getBoundingClientRect();
          const small=[...d.querySelectorAll('button,select,input')].filter(x=>x.offsetParent&&(x.getBoundingClientRect().height<24));
          return [Math.round(r.width), document.documentElement.scrollWidth<=320, d.scrollWidth<=d.clientWidth, small.map(x=>x.id||x.className)]; })()""")
        self.assertEqual(got, [320, True, True, []])
        b.eval("document.documentElement.dataset.theme='dark'")
        bg = b.eval("getComputedStyle(document.getElementById('capDrawer')).backgroundColor")
        self.assertNotEqual(bg, "rgb(255, 255, 255)")


if __name__ == "__main__":
    unittest.main()
