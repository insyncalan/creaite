"""BL-286 part D: the prep page inside creaite, Meetings › Prep (#prep=<key>), in the Briefing layout.

Run: python3 dev/tests/test_prep_view.py   (needs Google Chrome; skipped otherwise)
A sample vault with a meeting today (ABC weekly at 09:00), its series, a weekly report and a stored prep page (built from a
fixture reply: no model is called). Covers: the address opens the view and survives a reload; the header (breadcrumb, title,
Internal, chips with DD-MM-YYYY dates and the project by name, Saved to Agendas, Open the file, the tabs); the three columns
and the outline; researched notes with their citation links; the sources as typed links (a file through /api/open, mail by
its web link, an item in the peek); the aim as three stacked editors saved as you type to prep-focus.json, one Shape control, In play with Raise, Note and Skip;
the questions edited in place (kept through Refresh research, and given back);
the tabs' keys; the Invite tab with names, not addresses; one column below 1000 px and nothing sideways at 320 px; the tracker
never changes.
"""
import json
import time
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from live_browser import TEST_PALETTES, LiveBrowserCase  # noqa: E402
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
        for w in ("Refresh research", "Draft agenda", "Saved to Agendas · ", "Open the file", "Print"):
            self.assertIn(w, acts)
        self.assertNotIn("Change focus", acts, "#111 A: Shape is on the page, not a popup")
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
        self.assertEqual(outline[:6], ["Your aim", "In play", "What research found", "Questions to ask", "Latest reporting", "Sources"])
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

    def test_5_in_play_items_open_the_peek(self):
        b = self.b
        self.open_view()
        self.assertIn("In play", self.text("#pp-h-work"))
        self.assertRegex(self.text("#pp-h-work"), r"\d+ of \d+ open items")
        self.assertEqual(b.eval("[...document.querySelectorAll('#pp-work .ppitem')][0].querySelectorAll('.ppsel button').length"), 3)
        self.assertEqual(b.eval("[...document.querySelectorAll('#pp-work .ppitem')][0].querySelector('.ppsel .on').textContent"), "Note")
        first = b.eval("document.querySelector('#pp-work .ppitem .ppid').textContent")
        b.click("#pp-work .ppitem .ppid")
        b.wait("document.querySelector('#panel.on')")
        self.assertEqual(b.eval("CUR&&CUR.id"), first)
        self.assertRegex(self.text("#pp-work .ppitem"), r"due \d{2}-\d{2}-\d{4}")

    def test_6_the_aim_is_three_stacked_editors_saved_as_you_type(self):
        b = self.b
        self.open_view()
        self.assertEqual(b.eval("[...document.querySelectorAll('#pp-focus .ppbox')].map(e=>e.id)"), ["pp-n-objective", "pp-n-talking_points", "pp-n-ask"])
        ys = b.eval("[...document.querySelectorAll('#pp-focus .ppbox')].map(e=>Math.round(e.getBoundingClientRect().top))")
        self.assertEqual(ys, sorted(ys), "one under the other")
        self.assertEqual(b.eval("document.querySelectorAll('#pp-focus [data-ppshape]').length"), 1, "ONE Shape control")
        self.assertEqual(self.text("#pp-shape-btn"), "Shape")
        self.assertNotIn("Shape this meeting", b.eval("document.querySelector('#v-prep').textContent"))
        notes = {"objective": [{"text": "A date for data access", "sources": [{"type": "item", "id": "ABC-A-001", "label": "ABC-A-001"}]}],
                 "ask": [{"text": "Jane: a date", "sources": []}], "carried_over": [{"text": "Who approves the load test plan", "sources": []}]}
        r = b.eval(f"api('/api/prep/focus/save',{{key:{json.dumps(KEY)},accept:true,reading:{{focus:[{{id:'ABC-A-001',text:'Data access'}}],aim:'A date',show:'focus-first'}},notes:{json.dumps(notes)},drafted:{json.dumps(notes)}}}).then(r=>r.ok)")
        self.assertTrue(r)
        b.eval(f"loadPrep({json.dumps(DATED)})")
        b.wait("document.querySelector('#pp-n-objective') && document.querySelector('#pp-n-objective').value==='A date for data access'")
        self.assertEqual(self.text("#pp-shape-btn"), "Shape again")
        self.assertIn("A date", self.text("#pp-focus .ppaim"))
        self.assertIn("Focus: ABC-A-001 · Data access", self.text("#pp-focus .ppfocustxt"))
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#pp-n-objective')).resize"), "vertical")
        self.assertIn("ABC-A-001", self.text("#pp-focus .ppcites"))
        self.assertIn("Who approves the load test plan", self.text("#pp-carried"), "Carried over is in the right rail")
        self.assertRegex(self.text("#pp-work h2"), r"\d+ of \d+")
        # typing alone saves, a moment after it stops (no need to leave the box)
        b.eval("const t=document.querySelector('#pp-n-objective'); t.focus(); t.value='A committed date for data access'; t.dispatchEvent(new Event('input',{bubbles:true}));")
        stored = self.v.root / "system/staging/prep-focus.json"
        import time
        for _ in range(80):
            rec = next(iter(json.loads(stored.read_text())["meetings"].values()))
            if rec["notes"]["objective"][0]["text"].startswith("A committed"):
                break
            time.sleep(0.1)
        self.assertEqual(rec["notes"]["objective"][0]["text"], "A committed date for data access")
        self.assertEqual(rec["notes"]["objective"][0]["sources"][0]["id"], "ABC-A-001", "an edited line keeps its citation")
        self.assertEqual(rec["notes"]["carried_over"][0]["text"], "Who approves the load test plan", "the rail's lines are carried through")
        self.assertIn("objective", rec["edited"])
        b.wait("!/Saving/.test(document.querySelector('#pp-focus .ppstamp').textContent)")
        self.assertEqual(self.text("#pp-focus .ppstamp"), "Saved as you type")

    def test_6a_saved_is_announced_by_one_polite_live_region_and_typing_is_silent(self):
        """#111 piece A: one persistent polite region says "Saved" after each save; it is empty while typing."""
        b = self.b
        self.open_view()
        q = "document.querySelectorAll('#pp-saved')"
        self.assertEqual(b.eval(f"{q}.length"), 1)
        self.assertEqual(b.eval("document.getElementById('pp-saved').getAttribute('aria-live')"), "polite")
        self.assertEqual(b.eval("document.getElementById('pp-saved').getAttribute('role')"), "status")
        b.eval("window.__ppReg = document.getElementById('pp-saved')")
        self.assertEqual(b.eval("document.getElementById('pp-saved').textContent"), "")
        for text in ("First line", "Second line"):
            b.eval(f"(()=>{{ const t=document.querySelector('#pp-n-objective'); t.focus(); t.value={json.dumps(text)}; t.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
            self.assertEqual(b.eval("document.getElementById('pp-saved').textContent"), "", "typing announces nothing")
            b.wait("document.getElementById('pp-saved').textContent==='Saved'", 15)
            self.assertEqual(b.eval(f"{q}.length"), 1)
            self.assertTrue(b.eval("window.__ppReg === document.getElementById('pp-saved')"), "the same element, not re-created per save")

    def test_6b_raise_note_skip_n_of_n_and_show_the_rest_never_touch_the_tracker(self):
        b = self.b
        before = (self.v.root / "system/tracker.db").read_bytes()
        self.open_view()
        ids = b.eval("[...document.querySelectorAll('#pp-work .ppitem')].map(e=>e.dataset.id)")
        self.assertGreaterEqual(len(ids), 1)
        one = ids[0]
        b.click(f"#pp-work .ppitem[data-id='{one}'] [data-play=raise]")
        b.wait(f"document.querySelector(\"#pp-work .ppitem[data-id='{one}'] .ppsel .on\").textContent==='Raise'", 30)
        rec = next(iter(json.loads((self.v.root / "system/staging/prep-focus.json").read_text())["meetings"].values()))
        self.assertEqual([f.get("id") for f in rec["reading"]["focus"]], [one], "Raise names it in the focus")
        self.assertRegex(self.text("#pp-h-work"), r"\d+ of \d+ open items")
        self.assertIn("Raise puts it in the agenda", self.text("#pp-work"))
        b.click(f"#pp-work .ppitem[data-id='{one}'] [data-play=skip]")
        b.wait(f"!document.querySelector(\"#pp-work .ppitem[data-id='{one}'] [data-play=raise].on\")", 30)
        rec = next(iter(json.loads((self.v.root / "system/staging/prep-focus.json").read_text())["meetings"].values()))
        self.assertEqual(rec["reading"]["focus"], [])
        self.assertEqual(rec["excluded"], [one], "Skip ticks it out of the focus")
        b.click(f"#pp-work .ppitem[data-id='{one}'] [data-play=note]")
        for _ in range(60):
            rec = next(iter(json.loads((self.v.root / "system/staging/prep-focus.json").read_text())["meetings"].values()))
            if rec["excluded"] == []:
                break
            time.sleep(0.1)
        self.assertEqual(rec["excluded"], [])
        # Show the rest / Hide the rest
        b.click("#pp-work [data-ppmore]")
        b.wait("/Show the rest/.test(document.querySelector('#pp-work [data-ppmore]').textContent)", 30)
        rec = next(iter(json.loads((self.v.root / "system/staging/prep-focus.json").read_text())["meetings"].values()))
        self.assertEqual(rec["reading"]["show"], "focus-only")
        b.click("#pp-work [data-ppmore]")
        b.wait("/Hide the rest/.test(document.querySelector('#pp-work [data-ppmore]').textContent)", 30)
        self.assertEqual((self.v.root / "system/tracker.db").read_bytes(), before, "Raise, Note and Skip never touch the tracker")

    def test_6c_desktop_and_900_light_dark_both_palettes(self):
        """#111 A: the page reads in creaite and Cursor palettes, light and dark, at desktop width and 900 px: the Raise, Note and
        Skip buttons keep a readable contrast and nothing reaches sideways."""
        import os
        b = self.b
        self.open_view()
        js = """(()=>{ const lum=c=>{ const v=c.match(/[\\d.]+/g).slice(0,3).map(x=>{ x/=255; return x<=.03928?x/12.92:Math.pow((x+.055)/1.055,2.4); }); return .2126*v[0]+.7152*v[1]+.0722*v[2]; };
          const ratio=(a,c)=>{ const x=lum(a), y=lum(c); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); };
          const on=document.querySelector('#pp-work .ppsel button.on'), off=document.querySelector('#pp-work .ppsel button:not(.on)');
          const bg=e=>getComputedStyle(e).backgroundColor, fg=e=>getComputedStyle(e).color;
          const wide=[...document.querySelectorAll('#v-prep *')].filter(e=>e.getBoundingClientRect().right>document.documentElement.clientWidth+1&&e.getClientRects().length).length;
          return [ratio(fg(on),bg(on)), ratio(fg(off),bg(off)), wide]; })()"""
        for width in (1280, 900):
            b.resize(width, 900)
            for pal in TEST_PALETTES:
                for mode in ("light", "dark"):
                    b.eval(f"(()=>{{ const r=document.documentElement; r.setAttribute('data-palette',{json.dumps(pal)}); r.setAttribute('data-theme','{mode}'); }})()")
                    b.pump(0.1)
                    on, off, wide = b.eval(js)
                    self.assertGreaterEqual(on, 3.0, f"{pal} {mode} {width}: the chosen button reads")
                    self.assertGreaterEqual(off, 4.5, f"{pal} {mode} {width}: the other buttons read")
                    self.assertEqual(wide, 0, f"{pal} {mode} {width}: nothing sideways")
                    folder = os.environ.get("SHOTS")
                    if folder:
                        Path(folder).mkdir(parents=True, exist_ok=True)
                        b.screenshot(str(Path(folder) / f"prep-111a-{pal}-{mode}-{width}.png"))
        b.eval("(()=>{ const r=document.documentElement; r.removeAttribute('data-palette'); r.removeAttribute('data-theme'); })()")

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

    def test_8_one_column_when_narrow_and_nothing_sideways_at_320(self):
        b = self.b
        self.open_view()
        b.resize(900, 900)
        b.wait("getComputedStyle(document.querySelector('#v-prep .ppb')).gridTemplateColumns.split(' ').length===1")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#v-prep .ppoutline')).display"), "none")
        b.resize(320, 800)
        b.wait("document.documentElement.clientWidth<=320")
        wide = b.eval("[...document.querySelectorAll('#v-prep *')].filter(e=>e.getBoundingClientRect().right>document.documentElement.clientWidth+1&&e.getClientRects().length).map(e=>e.tagName+'.'+e.className).slice(0,5)")
        self.assertEqual(wide, [], "nothing in the prep page reaches past the window")
        self.assertLessEqual(b.eval("document.querySelector('#v-prep').scrollWidth"), b.eval("document.querySelector('#v-prep').clientWidth"))

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

    def test_11_the_project_chip_is_a_picker_remembered_for_the_series(self):
        """#279: the projects and "No project (general meeting)"; the choice is saved in settings prep.series."""
        b = self.b
        self.open_view()
        sel = "#v-prep .ppmeta select[data-ppproject]"
        self.assertEqual(b.eval(f"document.querySelector({json.dumps(sel)}).value"), "ABC")
        self.assertIn("No project (general meeting)", b.eval(f"[...document.querySelector({json.dumps(sel)}).options].map(o => o.text)"))

        def choose(code):
            b.eval(f"(() => {{ const s = document.querySelector({json.dumps(sel)}); s.value = {json.dumps(code)}; "
                   f"s.dispatchEvent(new Event('change', {{bubbles: true}})); }})()")
            b.wait(f"document.querySelector({json.dumps(sel)}) && document.querySelector({json.dumps(sel)}).value==={json.dumps(code)}"
                   " && !document.querySelector('#v-prep .pploading')", timeout=20)

        choose("_portfolio")
        time.sleep(2)
        saved = json.loads((self.v.root / "system/config/settings.json").read_text())["prep"]["series"]
        self.assertEqual(saved.get("abc weekly"), "_portfolio", saved)
        choose("ABC")
        time.sleep(2)
        saved = json.loads((self.v.root / "system/config/settings.json").read_text())["prep"]["series"]
        self.assertEqual(saved.get("abc weekly"), "ABC")

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
