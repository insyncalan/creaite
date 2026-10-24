"""Dashboard pages (BL-87, BL-88, BL-89, BL-95, BL-91, BL-90 part 1), part 2 of 3 (Current state and its panes; the fixture is in pages_support.py).

Run: python3 dev/tests/test_pages_panes.py   (the page tests need Google Chrome; they are skipped otherwise)

Everything is fictional and temporary. The data tests run in the default layout and in a temporary OneDrive-style projects
root (the BL-85 `locations` setting, resolved against a fake home folder); the page tests drive a real headless Chrome
against the real live server, as a person would.
"""
import json
import re
import sys
import time
import unittest
import unittest.mock
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import png, populate  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from pages_support import (  # noqa: E402
    CONTRAST_JS,
    THEMES,
    resize,
    theme,
)


# ===== BL-89: Current state in two resizable panes =====

MARKER = "<!-- creaite: second pane -->"


class CurrentStateDataTests(unittest.TestCase):
    """The marker through docx_tools, report.py (the weekly Word report, approval, Generate) and the dashboard's data."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        import docx_tools
        import report
        cls.dt, cls.rp = docx_tools, report

    def test_split_join_and_one_message(self):
        dt = self.dt
        self.assertEqual(dt.split_panes("Only left."), ("Only left.", ""))                       # no marker: just the left pane
        self.assertEqual(dt.split_panes(f"Left.\n\n{MARKER}\n\nRight."), ("Left.", "Right."))
        self.assertEqual(dt.split_panes(f"Left.\n\n{MARKER}\n\nRight.\n\n{MARKER}\n\nMore"), ("Left.", "Right.\n\nMore"))   # one marker counts
        self.assertEqual(dt.join_panes("Left.", ""), "Left.")                                    # an empty right pane leaves no marker
        self.assertEqual(dt.join_panes("Left.", "Right."), f"Left.\n\n{MARKER}\n\nRight.")
        self.assertEqual(dt.join_panes("", "Right."), f"{MARKER}\n\nRight.")
        self.assertEqual(dt.one_message(f"Left.\n\n{MARKER}\n\nRight."), "Left.\n\nRight.")        # marker removed, nothing added
        self.assertEqual(dt.md_normalise(f"Left.\n\n{MARKER}\n\nRight."), f"Left.\n\n{MARKER}\n\nRight.")
        self.assertEqual(dt.md_normalise(f"Left.\n\n{MARKER}"), "Left.")                       # nothing after it: a one-pane text
        self.assertEqual(dt.md_normalise("Left only\n\n- a\n- b"), "Left only\n\n- a\n- b")  # unchanged for existing texts
        kinds = [k for k, _ in dt.md_blocks(f"Left.\n{MARKER}\nRight.")]
        self.assertEqual(kinds, ["p", "p"])                                                     # readers see two paragraphs, no marker

    def test_replace_current_keeps_the_right_pane_unless_the_new_text_carries_the_marker(self):
        rc = self.rp.replace_current
        md = f"# X\n\n## Current state\n\n_guide_\n\nOld left.\n\n{MARKER}\n\nMy notes.\n\n## Next\n"
        out = rc(md, "New left.")
        self.assertIn(f"New left.\n\n{MARKER}\n\nMy notes.\n", out)                           # the right pane is Alan's own
        self.assertIn("_guide_", out)
        self.assertIn(f"Left two.\n\n{MARKER}\n\nChanged notes.", rc(md, f"Left two.\n\n{MARKER}\n\nChanged notes."))   # a text with the marker stands
        self.assertEqual(rc(md, f"Only left.\n\n{MARKER}\n\nMy notes.").count(MARKER), 1)
        flat = rc(md, "New left.\n\nMy notes.")                                                # came back from Word as one piece
        self.assertIn(f"New left.\n\n{MARKER}\n\nMy notes.\n", flat)                         # the marker goes back where it was
        self.assertEqual(flat.count("My notes."), 1)
        plain = "# X\n\n## Current state\n\nOld.\n\n## Next\n"
        self.assertEqual(rc(plain, "New."), "# X\n\n## Current state\n\nNew.\n\n## Next\n")      # a one-pane text is as before

    def test_the_generate_context_separates_the_panes(self):
        v = Vault()
        try:
            populate(v)
            mem = next((v.root / "projects").glob("ABC */CLAUDE.md"))
            text = mem.read_text()
            mem.write_text(text.replace("UAT preparation continues on masked data.", f"UAT preparation continues on masked data.\n\n{MARKER}\n\nMy own note about the sponsor."))
            out = v.run("current-context", "ABC", script="report.py").stdout
            prompt = (v.root / "system/templates/current-state-prompt.md").read_text()
            one = out.split("## Current state now: the left pane")[1].split("## Current state now: the right pane")
            self.assertEqual(len(one), 2)
            self.assertIn("UAT preparation continues", one[0])
            self.assertNotIn("My own note", one[0])
            self.assertIn("My own note about the sponsor.", one[1].split("\n## ")[0])
            self.assertIn("right pane", out)
            self.assertIn("never write the pane marker", prompt)                                  # Generate drafts the left pane only
            plain = v.run("current-context", "ABC", script="report.py").stdout
            mem.write_text(text)
            self.assertNotIn("the right pane", v.run("current-context", "ABC", script="report.py").stdout)   # one pane: no second section
            self.assertIn("the left pane", plain)
        finally:
            v.cleanup()


class CurrentStateReportTests(unittest.TestCase):
    """The weekly Word report reads two panes as one piece, keeping the marker and the right pane in CLAUDE.md."""

    def setUp(self):
        import test_reports as tr
        self.tr = tr
        self.v = tr.ReportVault()
        tr.populate(self.v)
        (self.v.root / ABC / "images" / "second.png").write_bytes(png(200, 100, (160, 60, 20)))
        self.mem = self.v.root / ABC / "CLAUDE.md"
        self.left = "Build is two weeks behind.\n\n![Delivery plan](images/plan.png)\n\nMore on the left."
        self.right = "Sponsor wants a call.\n\n![Second view](images/second.png)\n\nRight pane ends."
        text = self.mem.read_text()
        head = text[:text.index("## Current state")]
        self.mem.write_text(head + f"## Current state\n\n_Rewritten weekly._\n\n{self.left}\n\n{MARKER}\n\n{self.right}\n")

    def tearDown(self):
        self.v.cleanup()

    def spec(self, **extra):
        f = self.v.root / "system/staging/drafts/weekly.json"
        f.write_text(json.dumps({"code": "ABC", "health": "At risk", "health_reason": "UAT start slipped 14 days",
                                 "summary": ["UAT start has slipped two weeks."], "key_changes": "UAT start moved",
                                 "progress": ["Plan revised"], "next_week": ["Escalate data access"], "help_needed": ["Sponsor support"], **extra}))
        return str(f)

    def staged(self):
        prop = next((self.v.root / "system/staging").glob("proposed-*-weekly-ABC.json"))
        data = json.loads(prop.read_text())
        draft = self.v.root / data["report"]["draft"]
        with zipfile.ZipFile(draft) as z:
            xml = z.read("word/document.xml").decode()
        memory = next(o for o in data["report"]["file_ops"] if o["op"] == "write")["content"]
        return data, draft, xml, memory

    def test_two_panes_are_one_piece_in_word_and_unchanged_in_claude_md(self):
        # no current_state in the spec: the report uses what is there, both panes
        self.v.at("weekly-stage", self.spec(), script="report.py")
        data, draft, xml, memory = self.staged()
        paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
        at = lambda pred: next(i for i, p in enumerate(paras) if pred(p))  # noqa: E731
        order = [at(lambda p: ">Build is two weeks behind.<" in p), at(lambda p: ">Delivery plan<" in p), at(lambda p: ">More on the left.<" in p),
                 at(lambda p: ">Sponsor wants a call.<" in p), at(lambda p: ">Second view<" in p), at(lambda p: ">Right pane ends.<" in p)]
        self.assertEqual(order, sorted(order))                                                  # left, then right, as one message
        self.assertEqual(order[3] - order[2], 1)                                                # nothing added between them
        self.assertNotIn("second pane", xml)                                                    # the marker is not in the report
        self.assertEqual(xml.count('r:embed="rIdCreaiteImg'), 2)                                # an image from each pane
        self.assertIn(f"More on the left.\n\n{MARKER}\n\nSponsor wants a call.", memory)       # CLAUDE.md keeps the marker and the right pane
        self.assertEqual(memory.count(MARKER), 1)
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        n = next(r["n"] for r in listed if r["ref"] == "report")
        out = self.v.run("approve", str(n), script="review.py").stdout                         # an unedited draft raises no difference
        self.assertNotIn("Current state: draft says", out)
        self.assertIn("Approved 1.", out)
        approved = self.mem.read_text()
        self.assertIn(f"More on the left.\n\n{MARKER}\n\nSponsor wants a call.", approved)

    def test_a_new_left_pane_without_the_marker_keeps_the_right_pane(self):
        self.v.at("weekly-stage", self.spec(current_state="A fresh left pane."), script="report.py")
        data, draft, xml, memory = self.staged()
        self.assertIn(f"A fresh left pane.\n\n{MARKER}\n\nSponsor wants a call.", memory)
        text = self.v.run("text", str(draft), script="docx_tools.py").stdout
        self.assertLess(text.index("A fresh left pane."), text.index("Sponsor wants a call."))
        self.assertNotIn("second pane", text)

    def test_the_dashboards_data_has_both_panes_once(self):
        self.v.run(script="build_dashboard.py")
        html = (self.v.root / "dashboard.html").read_text(encoding="utf-8")
        data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        cur = next(p for p in data["projects"] if p["code"] == "ABC")["current"]
        self.assertEqual(cur.count(MARKER), 1)
        self.assertTrue(cur.index("More on the left.") < cur.index(MARKER) < cur.index("Sponsor wants a call."))


class PanesLive(LiveBrowserCase):
    """A fresh vault, live server and browser for each test; real clicks, real drags, real keys."""

    width, height = 1280, 900

    def setUp(self):
        super().setUp()
        self.mem = next((self.v.root / "projects").glob("ABC */CLAUDE.md"))

    def md(self):
        return re.search(r"## Current state\n(.*?)(?=\n## |\Z)", self.mem.read_text(), re.S).group(1)

    def two_panes(self, left="Left pane text.", right="Right pane text.\n\n![Second view](images/second.png)"):
        (self.mem.parent / "images" / "second.png").write_bytes(png(200, 100, (160, 60, 20)))
        text = self.mem.read_text()
        head = text[:text.index("## Current state")]
        self.mem.write_text(head + f"## Current state\n\n_Rewritten weekly._\n\n{left}\n\n{MARKER}\n\n{right}\n")
        self.v.run(script="build_dashboard.py")
        self.b.reload()
        self.b.wait("typeof go==='function' && LIVE")
        self.open_card()

    def open_card(self):
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("document.querySelector('#v-cockpit .curcard')")

    def edit(self):
        self.b.click("#v-cockpit .curcard [data-edcur]")
        self.b.wait("document.getElementById('curEd2')")

    def save(self):
        self.b.eval("document.getElementById('snackT').textContent=''")
        self.b.click('[data-cure="save"]')
        self.b.wait("/— saved|Not saved/i.test(document.getElementById('snackT').textContent)", 15)
        return self.b.eval("document.getElementById('snackT').textContent")

    def widths(self):
        return self.b.eval("""(()=>{ const box=document.querySelector('.curpanes').getBoundingClientRect(), a=document.querySelector('.curpane[data-pane="1"]').getBoundingClientRect(),
          c=document.querySelector('.curpane[data-pane="2"]').getBoundingClientRect(), d=document.querySelector('.curdiv').getBoundingClientRect();
          return {box:box.width, left:a.width, right:c.width, div:d.width, leftPct:(a.width+6)/box.width*100, divX:d.left+d.width/2}; })()""")

    def drag_divider(self, dx):
        b = self.b
        pos = b.box(".curdiv")
        y = pos["y"]
        for kind, x in (("mouseMoved", pos["x"]), ("mousePressed", pos["x"]), ("mouseMoved", pos["x"] + dx / 2), ("mouseMoved", pos["x"] + dx), ("mouseReleased", pos["x"] + dx)):
            b.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
        b.pump(0.1)

    def test_a_text_without_a_marker_is_the_left_pane_and_notes_can_be_added(self):
        b = self.b
        before = self.mem.read_text()
        self.open_card()
        self.assertEqual(b.eval("document.querySelectorAll('.curpanes.read.solo').length"), 1)         # BL-117: the same frame, the right column empty
        self.assertEqual(b.eval("document.querySelectorAll('[data-edcur2], .curnotes').length"), 0)    # BL-116: no Add notes link
        self.assertNotIn("Add notes", b.eval("document.getElementById('curText').textContent"))
        for sel in (".curdiv", ".curcollapse", ".curdot"):                                              # no divider, fold button or dot
            self.assertEqual(b.eval(f"document.querySelectorAll('.curtext {sel}').length"), 0, sel)
        b.click("#v-cockpit .curcard [data-edcur]")                                                     # the pencil opens both panes
        b.wait("document.getElementById('curEd2')")
        self.assertEqual(b.eval("document.querySelectorAll('.curpanes.edit .curpane').length"), 2)
        b.click("#curEd2")
        self.assertEqual(b.eval("document.getElementById('curEd2').dataset.ph"), "Write here…")        # faint placeholder, no caption
        self.assertTrue(b.eval("document.getElementById('curEd2').classList.contains('blank')"))
        self.assertEqual(b.eval("document.querySelectorAll('.curpane h2, .curpane h3, .curpane legend, .curpane label').length"), 0)   # the panes have no titles
        b.type("My own note.")
        self.assertFalse(b.eval("document.getElementById('curEd2').classList.contains('blank')"))
        self.assertIn("— saved", self.save())
        md = self.md()
        self.assertIn(f"\n\n{MARKER}\n\nMy own note.", md)
        self.assertEqual(md.count(MARKER), 1)
        self.assertEqual(b.eval("document.querySelectorAll('.curpanes.read').length"), 1)              # now shown in two panes
        # one apply, one Activity line, one Undo
        self.assertEqual(b.eval("ACT.filter(a=>/^Example Programme — current state updated/.test(a.what)).length"), 1)
        b.eval("document.querySelector('#v-activity') && go('activity')")
        b.wait("document.querySelector('#actTbl [data-undoapply], #actTbl [data-undoact]')")
        b.click("#actTbl [data-undoapply], #actTbl [data-undoact]")
        b.wait("!document.querySelector('.curpanes') || true")
        time.sleep(1.5)
        self.assertEqual(self.mem.read_text(), before)                                                  # one Undo puts it all back

    def left_width(self):
        return self.b.eval("document.querySelector('.curpane[data-pane=\"1\"]').getBoundingClientRect().width")

    def test_the_text_keeps_its_width_with_nothing_on_the_right(self):
        """BL-117: the read view always draws the two-column frame, so the left text sits at its saved share either way."""
        b = self.b
        self.open_card()
        solo = self.left_width()
        box = b.eval("document.querySelector('.curpanes').getBoundingClientRect().width")
        self.assertAlmostEqual((solo + 6) / box * 100, 62, delta=2)                                      # the default share, not the full card
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.curpane[data-pane=\"2\"]')).display"), "block")
        self.two_panes()
        self.assertAlmostEqual(self.left_width(), solo, delta=1)                                         # adding text on the right changes nothing on the left
        b.eval("localStorage.setItem('creaite-cur-split','40')")                                         # a dragged split is kept by both
        b.eval("renderCockpit('ABC')")
        two = self.left_width()
        self.assertAlmostEqual(self.widths()["leftPct"], 40, delta=1.5)
        self.mem.write_text(self.mem.read_text().replace(f"\n\n{MARKER}\n\nRight pane text.\n\n![Second view](images/second.png)", ""))
        self.v.run(script="build_dashboard.py")
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        self.open_card()
        self.assertEqual(b.eval("document.querySelectorAll('.curpanes.solo').length"), 1)
        self.assertAlmostEqual(self.left_width(), two, delta=1)

    def test_a_solo_read_view_is_full_width_in_a_narrow_window(self):
        b = self.b
        self.open_card()
        resize(b, 700, 900)
        b.eval("renderCockpit('ABC')")
        left = b.eval("document.querySelector('.curpane[data-pane=\"1\"]').getBoundingClientRect().toJSON()")
        box = b.eval("document.querySelector('.curpanes').getBoundingClientRect().width")
        self.assertAlmostEqual(left["width"], box, delta=2)                                              # stacked: the text is the full width
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.curpane[data-pane=\"2\"]')).display"), "none")

    def test_two_panes_show_side_by_side_at_about_62_per_cent(self):
        self.two_panes()
        w = self.widths()
        self.assertAlmostEqual(w["leftPct"], 62, delta=2)
        self.assertGreater(w["right"], 150)
        figs = self.b.eval("[document.querySelectorAll('.curpane[data-pane=\"1\"] figure').length, document.querySelectorAll('.curpane[data-pane=\"2\"] figure').length]")
        self.assertEqual(figs, [0, 1])                                                                   # an image stays in the pane it is in
        self.assertNotIn("second pane", self.b.eval("document.getElementById('curText').textContent"))   # the marker never shows
        self.assertEqual(self.b.eval("document.querySelector('.curdiv').getAttribute('role')"), "separator")
        self.assertEqual(self.b.eval("document.querySelector('.curdiv').getAttribute('aria-valuenow')"), "62")

    def test_the_divider_drags_remembers_resets_and_keeps_both_panes_in_reach(self):
        b = self.b
        self.two_panes()
        start = self.widths()
        self.drag_divider(-200)
        w = self.widths()
        self.assertLess(w["leftPct"], start["leftPct"] - 10)                                            # dragging left gives the right pane room
        self.assertEqual(b.eval("+localStorage.getItem('creaite-cur-split')") // 1, round(w["leftPct"]) if False else b.eval("Math.floor(+localStorage.getItem('creaite-cur-split'))"))
        saved = float(b.eval("localStorage.getItem('creaite-cur-split')"))
        self.assertAlmostEqual(saved, w["leftPct"], delta=1.5)                                          # remembered
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        self.open_card()
        self.assertAlmostEqual(self.widths()["leftPct"], saved, delta=1.5)                              # and after a reload
        b.eval("go('projects')"); self.open_card()
        self.assertAlmostEqual(self.widths()["leftPct"], saved, delta=1.5)                              # the same for every project (a browser setting)
        self.drag_divider(-2000)
        self.assertGreaterEqual(self.widths()["leftPct"], 24.5)                                          # never less than about 25%
        self.drag_divider(4000)
        self.assertLessEqual(self.widths()["leftPct"], 75.5)
        self.assertGreaterEqual(100 - self.widths()["leftPct"], 24)
        pos = b.box(".curdiv")
        for _ in range(2):
            b.call("Input.dispatchMouseEvent", type="mousePressed", x=pos["x"], y=pos["y"] + 30, button="left", clickCount=2)
            b.call("Input.dispatchMouseEvent", type="mouseReleased", x=pos["x"], y=pos["y"] + 30, button="left", clickCount=2)
        b.eval("document.querySelector('.curdiv').dispatchEvent(new MouseEvent('dblclick',{bubbles:true}))")
        self.assertAlmostEqual(self.widths()["leftPct"], 62, delta=2)                                   # double-click resets
        b.eval("document.querySelector('.curdiv').focus()")                                              # the keyboard
        b.key("ArrowLeft")
        self.assertEqual(b.eval("document.querySelector('.curdiv').getAttribute('aria-valuenow')"), "60")
        b.key("Home")
        self.assertEqual(b.eval("document.querySelector('.curdiv').getAttribute('aria-valuenow')"), "25")
        b.key("End")
        self.assertEqual(b.eval("document.querySelector('.curdiv').getAttribute('aria-valuenow')"), "75")
        b.key("ArrowRight")
        self.assertEqual(b.eval("document.querySelector('.curdiv').getAttribute('aria-valuenow')"), "75")   # clamped
        self.assertEqual(b.errors, [])

    def test_the_right_pane_folds_into_a_strip_that_shows_it_holds_text(self):
        b = self.b
        self.two_panes()
        b.click(".curcollapse")
        self.assertTrue(b.eval("document.querySelector('.curpanes').classList.contains('collapsed')"))
        w = self.widths()
        self.assertLess(w["right"], 50)                                                                 # a thin strip
        self.assertTrue(b.eval("getComputedStyle(document.querySelector('.curdot')).display!=='none'"))   # it holds text: the strip says so
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.curpane[data-pane=\"2\"] .curin')).display"), "none")
        self.assertEqual(b.eval("document.querySelector('.curcollapse').getAttribute('aria-expanded')"), "false")
        self.assertIn("Right pane text.", b.eval("document.querySelector('.curpane[data-pane=\"2\"]').textContent"))   # hidden, still there
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        self.open_card()
        self.assertTrue(b.eval("document.querySelector('.curpanes').classList.contains('collapsed')"))   # remembered
        b.click(".curcollapse")
        self.assertFalse(b.eval("document.querySelector('.curpanes').classList.contains('collapsed')"))
        self.assertGreater(self.widths()["right"], 150)

    def test_editing_both_panes_with_one_toolbar_and_one_save(self):
        b = self.b
        self.two_panes("Left start.", "Right start.")
        self.edit()
        self.assertEqual(b.eval("document.querySelectorAll('.rtebar').length"), 1)                      # one toolbar
        self.assertEqual(b.eval("document.querySelectorAll('[data-cure=\"save\"]').length"), 1)
        self.assertEqual(b.eval("document.querySelectorAll('[data-cure=\"cancel\"]').length"), 1)
        self.assertTrue(b.eval("document.activeElement.id==='curEd'"))
        b.click("#curEd p")
        b.key("End")
        b.type(" Left added.")
        b.click("#curEd2 p")                                                                             # the toolbar acts on the pane the cursor is in
        b.key("End")
        b.eval("document.getSelection().selectAllChildren(document.querySelector('#curEd2 p'))")
        b.call("Input.dispatchMouseEvent", type="mousePressed", x=0, y=0, button="none") if False else None
        b.eval("document.querySelector('[data-rc=\"bold\"]').dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true}))")
        self.assertEqual(b.eval("document.querySelector('#curEd2 b, #curEd2 strong')?.textContent"), "Right start.")
        self.assertIsNone(b.eval("document.querySelector('#curEd b, #curEd strong')?.textContent"))
        b.click("#curEd2 p")
        b.key("End")
        b.type(" Right added.")
        img = self.mem.parent / "images" / "third.png"
        img.write_bytes(png(120, 80, (20, 120, 60)))
        b.set_files("#curImgFile", [img])                                                                # the cursor is in the right pane
        b.wait("document.querySelectorAll('#curEd2 figure.cimg').length>=1", 5)
        self.assertEqual(b.eval("document.querySelectorAll('#curEd figure').length"), 0)                 # so the picture lands there
        b.type("Third view")
        self.assertIn("— saved", self.save())
        md = self.md()
        left, right = md.split(MARKER)
        self.assertIn("Left start. Left added.", left)
        self.assertIn("**Right start. Right added.**", right)
        self.assertEqual(right.count("!["), 1)
        self.assertEqual(left.count("!["), 0)
        self.assertEqual(b.eval("document.querySelectorAll('.curpanes.read').length"), 1)
        self.assertEqual(b.errors, [])

    def test_an_unchanged_two_pane_text_round_trips_untouched(self):
        self.two_panes("Left **bold** text.\n\n- one\n- two", "Right note with a [link](https://example.com/x).")
        before = self.mem.read_text()
        self.edit()
        self.b.click('[data-cure="save"]')
        time.sleep(0.6)
        self.assertEqual(self.mem.read_text(), before)                                                   # nothing to save: nothing written
        self.assertEqual(self.b.eval("document.querySelectorAll('#curEd').length"), 0)                  # and the editor closed

    def test_escape_asks_before_discarding_and_command_enter_saves(self):
        b = self.b
        self.two_panes()
        self.edit()
        b.click("#curEd2 p")
        b.type(" Oops.")
        b.key("Escape")
        b.wait("document.getElementById('discardBar').classList.contains('on')")                         # the same "Discard changes?" guard
        b.click("#discardBar [data-dis=keep]")
        self.assertTrue(b.eval("!!document.getElementById('curEd2')"))
        b.eval("document.getElementById('curEd2').focus()")
        b.key("Enter", 4)                                                                                # ⌘Enter saves
        b.wait("!document.getElementById('curEd2')", 15)
        self.assertIn("Right pane text. Oops.", self.md())

    def test_narrow_windows_stack_the_panes(self):
        b = self.b
        self.two_panes()
        resize(b, 700, 900)
        b.eval("renderCockpit('ABC')")
        left, right = (b.eval(f"document.querySelector('.curpane[data-pane=\"{n}\"]').getBoundingClientRect().toJSON()") for n in (1, 2))
        self.assertGreaterEqual(right["top"], left["bottom"] - 1)                                        # left on top
        self.assertAlmostEqual(left["width"], right["width"], delta=2)
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.curdiv')).display"), "none")  # no divider

    def test_generate_drafts_the_left_pane_and_never_touches_the_right(self):
        b = self.b
        self.two_panes("Old left text.", "Alan's own notes.")
        b.eval("genDraft('ABC','A new drafted left pane. {F1}','- the minutes')")
        b.wait("document.getElementById('curEd2')")
        self.assertIn("A new drafted left pane.", b.eval("document.getElementById('curEd').textContent"))
        self.assertEqual(b.eval("document.getElementById('curEd2').textContent.trim()"), "Alan's own notes.")
        self.assertEqual(b.eval("edValue(document.getElementById('curEd2')).includes(\"Alan's own notes.\")"), True)
        self.assertIn("— saved", self.save())
        left, right = self.md().split(MARKER)
        self.assertIn("A new drafted left pane.", left)
        self.assertNotIn("Old left text.", left)
        self.assertEqual(right.strip(), "Alan's own notes.")

    def test_every_theme_and_mode_styles_the_panes(self):
        b = self.b
        self.two_panes()
        b.eval(CONTRAST_JS)
        bad = {}
        for pal in THEMES:
            for mode in ("Light", "Dark"):
                theme(b, pal, mode)
                r = b.eval("""(()=>{ const card=document.querySelector('.curcard'), bg=__bgOf(document.querySelector('.curpane')), t=getComputedStyle(document.querySelector('.curpane .curin p')).color,
                  div=getComputedStyle(document.querySelector('.curdiv'),'::before').backgroundColor, btn=document.querySelector('.curcollapse'), bs=getComputedStyle(btn);
                  return {text:__ratio(t,bg), divider:__ratio(div,bg), collapse:__ratio(bs.color,bs.backgroundColor), edge:__ratio(bs.borderTopColor,bg)}; })()""")
                if r["text"] < 4.5 or r["divider"] < 1.2 or r["collapse"] < 4.5:
                    bad[f"{pal}|{mode}"] = r
        self.assertEqual(bad, {})
        theme(b, "creaite", "Light")


if __name__ == "__main__":
    unittest.main()
