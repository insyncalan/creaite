"""BL-286 part C: Shape the meeting, inside the Prep popup.

The instruction box and its suggestion chips; Shape through the run engine (a stand-in Claude, no model call); "creaite read this
as" with *change*; the draft notes (cited, editable, Regenerate keeping the sections Alan edited, Accept saving prep-focus.json in
the server's format, Discard counted); What's in focus ("n of N", N only the items listed; ticking out; Show everything instead;
an item opens the full peek over the popup); a confidential meeting; 320 px. Nothing reaches the tracker.

Run: python3 dev/tests/test_prep_shape.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_prep_reimagined import FAKE, world  # noqa: E402

# The stand-in Claude of test_prep_reimagined, citing the tracker item ABC-A-001 by the number the prompt gives it
FAKE = FAKE.replace('reply = (', 'import re\nm = re.search(r"\\[(S\\d+)\\] ABC-A-001:", p)\nitem = m.group(1) if m else "S2"\nreply = (').replace(
    "Agree a date for data access. [S1, S2]", 'Agree a date for data access. [S1, " + item + "]')

DLG = "document.getElementById('prepDlg')"
SHAPED = "document.querySelector('#prepShape .shdraft')"


class ShapeCase(LiveBrowserCase):
    confidential = False

    @classmethod
    def load(cls, v):
        world(v, confidential=cls.confidential)
        fake = v.root / "fake_shape.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cls.fake = fake

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake)}

    def open_shape(self):
        b = self.b
        b.eval("go('today'); renderToday(); openPrep(prepTimed()[0],TODAY)")
        b.wait(f"{DLG}.open && document.querySelector('#prepDlg [data-prepshape]')", 30)
        b.click("#prepDlg [data-prepshape]")
        b.wait(f"{DLG}.classList.contains('shaping') && document.getElementById('shapeTxt')", 30)
        # The suggestion chips come from /api/prep/chips after the panel opens and share the Shape button's row: until they are
        # in, the row can still wrap and move the button, so a click measured before then lands on empty space (seen under load).
        b.wait("document.querySelector('#prepShape button.chip.shsug')", 30)
        return b

    def shape(self, text="Focus on ABC-A-001. I want a date from Jane."):
        b = self.b
        b.eval(f"(()=>{{ const t=document.getElementById('shapeTxt'); t.value={json.dumps(text)}; t.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.click("#prepShape [data-shrun]")
        try:
            b.wait(SHAPED, 60)
        except TimeoutError:
            st = b.eval("JSON.stringify({txt:document.getElementById('shapeTxt')&&document.getElementById('shapeTxt').value, run:!!document.querySelector('#prepShape .shrun'), msg:(document.querySelector('#prepShape .wnote')||{}).textContent||'', dis:document.querySelector('#prepShape [data-shrun]').getAttribute('aria-disabled'), tip:document.querySelector('#prepShape [data-shrun]').dataset.tip})")
            calls = Path(str(self.fake) + ".calls")
            raise AssertionError(f"no draft: {st}; calls={calls.read_text().count(chr(10)) if calls.exists() else 0}") from None
        return b

    def stats(self):
        p = self.v.root / "system/staging/draft-stats.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def wait_file(self, test, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            if test():
                return True
            self.b.pump(0.1)
        return test()


class Shape(ShapeCase):
    def test_1_the_panel_the_box_and_a_chip_add_to_the_text(self):
        b = self.open_shape()
        self.assertEqual(b.eval("document.querySelector('#prepDlg [data-prepshape]').getAttribute('aria-pressed')"), "true")
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('prepBody')).display"), "none")      # the brief steps aside
        self.assertEqual(b.eval("document.activeElement.id"), "shapeTxt")
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('shapeTxt')).resize"), "vertical")   # dragged larger
        self.assertEqual(b.eval("document.getElementById('shapeTxt').tagName"), "TEXTAREA")
        b.wait("document.querySelector('#prepShape button.chip.shsug')", 30)
        label = b.eval("document.querySelector('#prepShape button.chip.shsug').getAttribute('aria-label')")
        n = b.eval("document.querySelectorAll('#prepShape button.chip.shsug').length")
        b.click("#prepShape button.chip.shsug")
        b.wait(f"document.querySelectorAll('#prepShape button.chip.shsug').length==={n - 1}", 30)
        self.assertIn("Also cover ", b.eval("document.getElementById('shapeTxt').value"))
        self.assertTrue(label.startswith("Add "), label)
        b.click("#prepShape [data-shback]")                                                             # back to the brief
        b.wait(f"!{DLG}.classList.contains('shaping') && getComputedStyle(document.getElementById('prepBody')).display!=='none'", 30)
        self.assertEqual(b.errors, [])

    def test_2_shape_reads_drafts_cites_and_accept_saves_in_the_servers_format(self):
        before = (self.v.root / "system/tracker.db").read_bytes()
        b = self.open_shape()
        self.shape()
        chips = b.eval("[...document.querySelectorAll('#prepShape .readas .chip')].map(c=>c.textContent)")
        self.assertTrue(any("ABC-A-001" in c for c in chips), chips)
        self.assertIn("A date for data access", b.eval("document.querySelector('#prepShape .readas').textContent"))
        boxes = b.eval("[...document.querySelectorAll('#prepShape .shbox')].map(t=>[t.id,t.value])")
        self.assertEqual([x[0] for x in boxes], ["shN-objective", "shN-talking_points", "shN-ask", "shN-carried_over"])
        self.assertEqual(boxes[0][1], "Agree a date for data access.")
        cite = b.eval("document.querySelector('#shC-objective [data-open]').dataset.open")
        self.assertEqual(cite, "actions:ABC-A-001")                                                     # the item's citation opens the peek
        # What's in focus: n of N, N only the items listed (Alan)
        b.wait("document.querySelector('#prepShape [data-shcount]')", 30)
        listed = b.eval("document.querySelectorAll('#prepShape .shscope section:first-child .shitem').length")
        self.assertEqual(b.eval("document.querySelector('#prepShape [data-shcount]').textContent"), f"· {listed} of {listed}")
        self.assertTrue(b.eval("document.querySelector('#prepShape .shitem .why').textContent.startsWith('Why: ')"))
        other = b.eval("[...document.querySelectorAll('#prepShape .shscope section:first-child .shitem input')].map(i=>i.getAttribute('aria-label')).find(l=>!l.endsWith('ABC-A-001'))")
        b.click(f"#prepShape .shitem input[aria-label='{other}']")
        b.wait(f"document.querySelector('#prepShape [data-shcount]').textContent==='· {listed - 1} of {listed}'", 30)
        # edit a box, then Accept
        b.eval("(()=>{ const t=document.getElementById('shN-ask'); t.value='Jane: commit to a date'; t.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.click("#prepShape [data-shaccept]")
        path = self.v.root / "system/staging/prep-focus.json"
        self.assertTrue(self.wait_file(path.exists))
        rec = next(iter(json.loads(path.read_text())["meetings"].values()))
        self.assertEqual(rec["notes"]["ask"][0]["text"], "Jane: commit to a date")
        self.assertEqual(rec["edited"], ["ask"])
        self.assertIn("ABC-A-001", [x.get("id") for x in rec["notes"]["objective"][0]["sources"]])               # citations kept
        self.assertEqual(rec["reading"]["focus"][0]["id"], "ABC-A-001")
        self.assertEqual(rec["excluded"], [other.replace("Include ", "")])
        self.assertTrue(rec["accepted_at"])
        self.assertTrue(self.wait_file(lambda: (self.stats().get("shape") or {}).get("edited") == 1))
        b.wait("document.querySelector('#prepShape .shacc')", 30)
        self.assertEqual((self.v.root / "system/tracker.db").read_bytes(), before)                    # nothing reached the tracker
        self.assertEqual(b.errors, [])

    def test_3_regenerate_keeps_an_edited_section_and_change_corrects_the_reading(self):
        b = self.open_shape()
        self.shape()
        b.eval("(()=>{ const t=document.getElementById('shN-ask'); t.value='My own ask'; t.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("document.querySelector('#prepShape .shmine')", 30)
        b.eval("(()=>{ const t=document.getElementById('shN-objective'); t.value='Throwaway'; t.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("document.querySelectorAll('#prepShape .shmine').length===2", 30)
        b.click("#prepShape .shsec:has(#shN-objective) .shmine .linkbtn")                                     # give the objective back
        b.wait("document.getElementById('shN-objective').value==='Agree a date for data access.'", 30)
        b.click("#prepShape [data-shchange]")
        b.wait("document.getElementById('shAim')", 30)
        b.eval("(()=>{ const t=document.getElementById('shAim'); t.value='A date, or masked data'; t.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.click("#prepShape .shshow input[value='focus-only']")
        b.click("#prepShape [data-shdone]")
        b.wait("document.querySelector('#prepShape .readas').textContent.includes('A date, or masked data')", 30)
        self.assertIn("show everything instead", b.eval("document.querySelector('#prepShape [data-shshow]').textContent"))
        b.click("#prepShape [data-shregen]")
        b.wait("!document.querySelector('#prepShape .shrun')", 60)
        b.wait("document.getElementById('shN-ask').value==='My own ask'", 30)
        self.assertEqual(b.eval("document.getElementById('shN-objective').value"), "Agree a date for data access.")
        calls = [json.loads(x) for x in Path(str(self.fake) + ".calls").read_text().splitlines()]
        self.assertEqual(len(calls), 2)
        self.assertEqual(b.errors, [])

    def test_4_discard_counts_a_rejection_and_an_item_opens_the_peek_over_the_popup(self):
        b = self.open_shape()
        self.shape()
        b.wait("document.querySelector('#prepShape .shitem .t[data-open]')", 30)
        first = b.eval("document.querySelector('#prepShape .shitem .t[data-open]').dataset.open")
        b.click("#prepShape .shitem .t[data-open]")
        b.wait("document.getElementById('panel').classList.contains('on') && document.getElementById('panel').classList.contains('peek')", 30)
        self.assertEqual(b.eval("CUR.id"), first.split(":")[1])
        self.assertTrue(b.eval("prepPeekList().every(o=>document.querySelector(`#prepShape [data-open='${o.k}:${o.id}']`))"))
        b.eval("document.body.focus()")
        b.key("Escape")
        b.wait(f"!document.getElementById('panel').classList.contains('on') && {DLG}.matches(':modal')", 30)
        self.assertTrue(b.eval(f"{DLG}.classList.contains('shaping')"))                                  # still shaping
        b.click("#prepShape [data-shdiscard]")
        b.wait(f"!{SHAPED}", 30)
        self.assertTrue(self.wait_file(lambda: (self.stats().get("shape") or {}).get("rejected") == 1))
        self.assertFalse((self.v.root / "system/staging/prep-focus.json").exists())
        self.assertEqual(b.errors, [])

    def test_5_at_320_px_nothing_scrolls_sideways(self):
        b = self.b
        b.resize(320, 800)
        self.open_shape()
        self.shape()
        b.wait("document.querySelector('#prepShape [data-shcount]')", 30)
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#prepShape .shscope')).gridTemplateColumns.split(' ').length"), 1)
        self.assertTrue(b.eval(f"(()=>{{ const s=document.getElementById('prepScroll'); return s.scrollWidth<=s.clientWidth+1 && {DLG}.scrollWidth<={DLG}.clientWidth+1; }})()"))

    def test_6_the_switch_in_settings_turns_it_off(self):
        b = self.b
        b.eval("S.drafting={...(S.drafting||{}),shape:false}")
        self.open_shape()
        run = "document.querySelector('#prepShape [data-shrun]')"
        self.assertEqual(b.eval(f"{run}.getAttribute('aria-disabled')"), "true")
        self.assertIn("off in Settings", b.eval(f"{run}.dataset.tip"))


class Confidential(ShapeCase):
    confidential = True

    def test_a_confidential_meeting_is_shaped_from_the_text_and_the_tracker(self):
        b = self.open_shape()
        b.wait("document.querySelector('#prepShape .shconf')", 30)
        chips = b.eval("[...document.querySelectorAll('#prepShape button.chip.shsug')].map(c=>c.getAttribute('aria-label'))")
        self.assertFalse(any("Who approves the load test plan" in c for c in chips), chips)              # no carried points
        self.shape()
        b.wait("document.querySelector('#prepShape [data-shcount]')", 30)
        self.assertIn("lists no documents", b.eval("document.querySelector('#prepShape .shscope section:last-child').textContent"))
        call = json.loads(Path(str(self.fake) + ".calls").read_text().splitlines()[-1])
        self.assertEqual(call["allowed"], "")                                                           # the run had no tools
        self.assertNotIn("Board secret", call["prompt"])
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
