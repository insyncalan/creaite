"""BL-286 part D: the prep page inside creaite, Meetings › Prep (#prep=<key>), in the Briefing layout.

Run: python3 dev/tests/test_prep_view.py   (needs Google Chrome; skipped otherwise)
A sample vault with a meeting today (ABC weekly at 09:00), its series, a weekly report and a stored prep page (built from a
fixture reply: no model is called). Covers: the address opens the view and survives a reload; the header (breadcrumb, title,
Internal, chips with DD-MM-YYYY dates and the project by name, Saved to Agendas, Open the file, the tabs); the three columns
and the outline; researched notes with their citation links; the sources as typed links (a file through /api/open, mail by
its web link, an item in the peek); the focus band read-only before shaping and editable after, saved to prep-focus.json;
the questions edited in place (kept through Refresh research, and given back);
the tabs' keys; the Invite tab with names, not addresses; one column below 1000 px; the tracker
never changes.
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import TODAY, d  # noqa: E402
from test_prep_reimagined import py, world  # noqa: E402

KEY = "09:00|ABC weekly"
DATED = f"{TODAY.isoformat()}|{KEY}"
SHOWN = TODAY.strftime("%d-%m-%Y")


class PrepView(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        world(v)
        py(v, f"import prep_page; rel, _ = prep_page.build({KEY!r}, {{'about': 'The weekly check-in.', 'notes': [{{'text': "
              f"'Licences quote due Friday', 'source': 'Email · From: Jane Doe · Subject: Quote · Sent: {d(-1)} 09:00 · "
              f"Link: https://outlook.office365.com/q', 'date': '{d(-1)}'}}, {{'text': 'Data access is still blocked', "
              f"'source': 'ABC-A-001'}}], 'questions': ['Is UAT booked?']}}); print(json.dumps(rel))")

    def open_view(self):
        b = self.b
        b.eval(f"go('prep', {json.dumps(DATED)})")
        b.wait("document.querySelector('#v-prep #ppTitle') && !document.querySelector('#v-prep .pploading')", timeout=20)

    def text(self, sel):
        return self.b.eval(f"(document.querySelector({json.dumps(sel)})||{{}}).textContent||''")

    def test_1_the_address_opens_the_view_and_a_reload_keeps_it(self):
        b = self.b
        self.open_view()
        self.assertEqual(b.eval("VIEW"), "prep")
        self.assertEqual(b.eval("location.hash"), "#prep=" + b.eval(f"encodeURIComponent({json.dumps(DATED)})"))
        self.assertEqual(b.eval(f"prepHref({json.dumps(KEY)})"), b.eval("location.hash"), "today's undated key gets its day")
        b.reload("typeof go==='function' && LIVE")
        b.wait("VIEW==='prep' && document.querySelector('#v-prep #ppTitle')", timeout=20)
        self.assertEqual(self.text("#ppTitle"), "ABC weekly")
        self.assertIn("Prep", b.eval("document.title"))
        self.assertEqual(b.eval("document.querySelector('.rail button[data-v=today]')?.getAttribute('aria-current')"), "page")

    def test_2_the_header(self):
        b = self.b
        self.open_view()
        crumb = self.text("#v-prep .crumb")
        self.assertTrue(crumb.startswith("Today") and crumb.endswith("Prep"), crumb)
        self.assertEqual(self.text("#v-prep .tag.ppint"), "Internal")
        meta = self.text("#v-prep .ppmeta")
        self.assertIn(f"{SHOWN} · 09:00", meta)                                     # DD-MM-YYYY on screen
        self.assertIn("Example Programme", meta)                                     # BL-101: by name
        self.assertNotIn("ABC ·", meta)
        self.assertIn("Every week", meta)                                             # the series chip
        self.assertRegex(meta, r"\d+ invited")
        acts = self.text("#v-prep .ppacts")
        for w in ("Change focus", "Refresh research", "Draft agenda", "Saved to Agendas · ", "Open the file", "Print"):
            self.assertIn(w, acts)
        self.assertRegex(acts, r"Saved to Agendas · \d{2}-\d{2}-\d{4} \d{2}:\d{2}")
        tabs = b.eval("[...document.querySelectorAll('#v-prep [role=tablist] [role=tab]')].map(t=>t.textContent+'|'+t.getAttribute('aria-selected'))")
        self.assertEqual([t.split("|")[0].split(" (")[0] for t in tabs], ["Prep", "Invite", "History"])
        self.assertEqual(tabs[0].split("|")[1], "true")
        self.assertNotIn("VIP", b.eval("document.querySelector('#v-prep').textContent"))   # BL-288

    def test_3_three_columns_outline_notes_questions_and_rail(self):
        b = self.b
        self.open_view()
        cols = b.eval("getComputedStyle(document.querySelector('#v-prep .ppb')).gridTemplateColumns.split(' ').length")
        self.assertEqual(cols, 3)
        outline = b.eval("[...document.querySelectorAll('#v-prep .ppoutline a')].map(a=>a.textContent)")
        self.assertEqual(outline[:6], ["Focus and notes", "Work items", "Researched notes", "Questions and asks", "Latest reporting", "Sources"])
        b.eval("[...document.querySelectorAll('#v-prep .ppoutline a')].find(a=>a.textContent==='Sources').click()")
        self.assertEqual(b.eval("location.hash.startsWith('#prep=')"), True, "the outline never changes the address")
        notes = self.text("#pp-notes")
        self.assertIn("The weekly check-in.", notes)
        self.assertIn("Licences quote due Friday", notes)
        mail = b.eval("[...document.querySelectorAll('#pp-notes a.ppcite')].find(a=>a.href.startsWith('https://outlook'))")
        self.assertIsNotNone(mail)
        self.assertEqual(b.eval("[...document.querySelectorAll('#pp-notes a.ppcite')].find(a=>a.href.startsWith('https://outlook')).target"), "_blank")
        self.assertEqual(b.eval("document.querySelector('#pp-q').value"), "Is UAT booked?")
        rep = self.text("#pp-reporting")
        self.assertRegex(rep, r"Weekly report · \d{2}-\d{2}-\d{4}")                    # dated
        self.assertIn("This series", self.text("#pp-series"))
        self.assertIn(f"{SHOWN} · this one", self.text("#pp-series"))
        self.assertIn("not covered", self.text("#pp-series"))

    def test_4_sources_are_typed_links(self):
        b = self.b
        self.open_view()
        b.eval("window.__opened=[]; window.openPath=p=>window.__opened.push(p);")
        kinds = b.eval("[...document.querySelectorAll('#pp-sources .ppsrc')].map(a=>a.tagName+':'+(a.dataset.openfile?'file':a.dataset.open?'item':a.href?'web':'text'))")
        self.assertIn("A:web", kinds)                                                # mail by its link
        self.assertIn("A:item", kinds)                                               # the tracker item
        self.assertIn("A:file", kinds)                                               # the weekly report through /api/open
        b.eval("document.querySelector('#pp-sources .ppsrc[data-openfile]').click()")
        opened = b.eval("window.__opened")
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0].startswith("projects/"), opened)
        b.eval("document.querySelector('#pp-sources .ppsrc[data-open]').click()")
        b.wait("document.querySelector('#panel.on')")
        self.assertEqual(b.eval("CUR&&CUR.id"), "ABC-A-001")

    def test_5_work_items_open_the_peek(self):
        b = self.b
        self.open_view()
        self.assertEqual(self.text("#pp-h-work"), "Work items")
        heads = b.eval("[...document.querySelectorAll('#pp-work th')].map(t=>t.textContent)")
        self.assertEqual(heads, ["ID", "Item", "Owner", "Due", "Why it's here"])
        first = b.eval("document.querySelector('#pp-work tbody td.ppid a').textContent")
        b.click("#pp-work tbody td.ppid a")
        b.wait("document.querySelector('#panel.on')")
        self.assertEqual(b.eval("CUR&&CUR.id"), first)
        self.assertRegex(self.text("#pp-work tbody"), r"\d{2}-\d{2}-\d{4}")

    def test_6_focus_band_read_only_then_editable_and_saved(self):
        b = self.b
        self.open_view()
        self.assertEqual(b.eval("document.querySelectorAll('#pp-focus .ppbox').length"), 0)
        self.assertIn("Nothing has been shaped", self.text("#pp-focus"))
        notes = {"objective": [{"text": "A date for data access", "sources": [{"type": "item", "id": "ABC-A-001", "label": "ABC-A-001"}]}],
                 "ask": [{"text": "Jane: a date", "sources": []}]}
        r = b.eval(f"api('/api/prep/focus/save',{{key:{json.dumps(KEY)},accept:true,reading:{{focus:[{{id:'ABC-A-001',text:'Data access'}}],aim:'A date',show:'focus-first'}},notes:{json.dumps(notes)},drafted:{json.dumps(notes)}}}).then(r=>r.ok)")
        self.assertTrue(r)
        b.eval(f"loadPrep({json.dumps(DATED)})")
        b.wait("document.querySelectorAll('#pp-focus .ppbox').length===4")   # every section, so an empty one can be filled
        self.assertIn("Focus: ABC-A-001 · Data access", self.text("#pp-h-focus"))
        self.assertIn("A date", self.text("#pp-focus .ppaim"))
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#pp-n-objective')).resize"), "vertical")
        self.assertIn("ABC-A-001", self.text("#pp-focus .ppcites"))
        self.assertRegex(self.text("#pp-h-work"), r"Work items in focus")
        self.assertRegex(self.text("#pp-work h2"), r"\d+ of \d+")
        b.eval("const t=document.querySelector('#pp-n-objective'); t.focus(); t.value='A committed date for data access'; t.dispatchEvent(new Event('input',{bubbles:true})); t.dispatchEvent(new FocusEvent('blur'));")   # leaving the box saves it
        stored = self.v.root / "system/staging/prep-focus.json"
        b.wait("document.querySelector('#pp-focus .ppstamp') && !/Saving/.test(document.querySelector('#pp-focus .ppstamp').textContent)")
        import time
        for _ in range(50):
            rec = next(iter(json.loads(stored.read_text())["meetings"].values()))
            if rec["notes"]["objective"][0]["text"].startswith("A committed"):
                break
            time.sleep(0.1)
        self.assertEqual(rec["notes"]["objective"][0]["text"], "A committed date for data access")
        self.assertEqual(rec["notes"]["objective"][0]["sources"][0]["id"], "ABC-A-001", "an edited line keeps its citation")
        self.assertIn("objective", rec["edited"])

    def test_7_tabs_keys_and_the_invite(self):
        b = self.b
        self.open_view()
        b.eval("document.querySelector('#v-prep [role=tab][aria-selected=true]').focus()")
        b.key("ArrowRight")
        b.wait("document.querySelector('#v-prep [role=tab][aria-selected=true]').textContent==='Invite'")
        self.assertEqual(b.eval("document.activeElement.textContent"), "Invite")
        self.assertEqual(b.eval("document.querySelector('#pp-panel-invite').hidden"), False)
        self.assertEqual(b.eval("document.querySelector('#pp-panel-prep').hidden"), True)
        inv = self.text("#pp-panel-invite")
        self.assertIn("Lucy Hart", inv)                                              # a name made from the address
        self.assertIn("not in the people register", inv)
        self.assertNotIn("lucy.hart@", inv)
        b.key("End")
        b.wait("document.querySelector('#v-prep [role=tab][aria-selected=true]').textContent.startsWith('History')")
        self.assertIn("This series", self.text("#pp-panel-history"))
        b.key("Home")
        b.wait("document.querySelector('#v-prep [role=tab][aria-selected=true]').textContent==='Prep'")

    def test_8_one_column_when_narrow(self):
        b = self.b
        self.open_view()
        b.resize(900, 900)
        b.wait("getComputedStyle(document.querySelector('#v-prep .ppb')).gridTemplateColumns.split(' ').length===1")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#v-prep .ppoutline')).display"), "none")
    def test_10_questions_are_editable_and_kept_through_refresh(self):
        b = self.b
        self.open_view()
        b.eval("const t=document.querySelector('#pp-q'); t.value='Is UAT booked?\\n\\nTom: a date for the fix'; "
               "t.dispatchEvent(new Event('input',{bubbles:true})); t.dispatchEvent(new FocusEvent('blur'));")
        b.wait("/Use creaite/.test(document.querySelector('#pp-questions .ppstamp').textContent)", timeout=20)
        rec = next(iter(json.loads((self.v.root / "system/staging/prep-focus.json").read_text())["meetings"].values()))
        self.assertEqual(rec["questions"], ["Is UAT booked?", "Tom: a date for the fix"])
        self.assertEqual(rec["edited"], [], "saving questions marks no notes section as edited")
        page = b.eval(f"api('/api/prep/view',{{key:{json.dumps(KEY)}}}).then(r=>r.saved.path)")
        self.assertIn("Tom: a date for the fix", (self.v.root / page).read_text())       # the Agendas file follows
        # Refresh research (a new reply) keeps Alan's questions
        py(self.v, f"import prep_page; prep_page.build({KEY!r}, {{'about': 'Again.', 'notes': [], 'questions': ['A new one?']}}); print(1)")
        b.eval(f"loadPrep({json.dumps(DATED)})")
        b.wait("document.querySelector('#pp-q') && /Tom: a date/.test(document.querySelector('#pp-q').value)", timeout=20)
        b.eval("[...document.querySelectorAll('#pp-questions button')].find(x=>/Use creaite/.test(x.textContent)).click()")
        b.wait("document.querySelector('#pp-q').value==='A new one?'", timeout=20)
        rec = next(iter(json.loads((self.v.root / "system/staging/prep-focus.json").read_text())["meetings"].values()))
        self.assertNotIn("questions", rec)

    def test_9_a_bad_address_is_ignored_and_the_tracker_never_changes(self):
        b = self.b
        before = (self.v.root / "system/tracker.db").read_bytes()
        self.assertIsNone(b.eval("prepKeyOf('#prep=nonsense')"))
        self.assertIsNone(b.eval("parseHash('#prep=nonsense')"))
        self.open_view()
        self.assertEqual((self.v.root / "system/tracker.db").read_bytes(), before)


class CleanQuestions(unittest.TestCase):
    def test_cleaned_and_capped(self):
        sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
        import prep_shape
        self.assertEqual(prep_shape.clean_questions(["  a \n b ", "", 3, "c" * 700] + ["q"] * 20)[:2], ["a b", "c" * 600])
        self.assertEqual(len(prep_shape.clean_questions(["q"] * 20)), 12)
        self.assertEqual(prep_shape.clean_questions("not a list"), [])
        rec = prep_shape._apply({"questions": ["x"]}, {"questions": None})
        self.assertNotIn("questions", rec)


if __name__ == "__main__":
    unittest.main()
