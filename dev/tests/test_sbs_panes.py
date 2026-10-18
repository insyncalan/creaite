"""p241-sbs (Alan, 18-10-2026: "yes, both must be editable"): the Reporting hub's Side by side view, with BOTH reports editable at once, each
pane its own report. Real Chrome on the real live server (no Claude runs). Desktop only. Fictional words only.

Brief item -> test (the PM maps the hand-check sheet from this list):
  (a) each pane saves its own report (own autosave, own dirty state, own Approve / Edit again rules)
        .......................................... SideBySideEditing.test_sbs_a_each_pane_saves_its_own_report
        .......................................... SideBySideEditing.test_sbs_a_each_pane_has_its_own_dirty_state_and_status
        .......................................... SideBySideEditing.test_sbs_a_an_approved_internal_report_locks_only_its_own_pane
  (b) no cross-talk between the panes
        the section menu, move, add a text section ... SideBySideEditing.test_sbs_b_no_cross_talk_section_menu
        zoom (one shared control)  ................ SideBySideEditing.test_sbs_b_no_cross_talk_zoom_is_one_shared_control
        the active editor and its toolbar ......... SideBySideEditing.test_sbs_b_no_cross_talk_active_editor
        the AI bar (each pane's own report) ....... SideBySideEditing.test_sbs_b_no_cross_talk_ai_bar
        two pickers ............................... SideBySideEditing.test_sbs_b_no_cross_talk_two_pickers
        shortcuts apply to the focused pane ....... SideBySideEditing.test_sbs_b_no_cross_talk_shortcuts_apply_to_the_focused_pane
        no duplicate DOM ids ...................... SideBySideEditing.test_sbs_b_no_duplicate_ids_with_everything_open
  (c) Esc closes only the active pane's menu, picker or bar
        .......................................... SideBySideEditing.test_sbs_c_escape_closes_only_the_active_pane
  (d) the two panes scroll together (one scroller)
        .......................................... SideBySideEditing.test_sbs_d_scroll_together
  (e) the client output never has the internal pane's edits
        .......................................... SideBySideEditing.test_sbs_e_internal_edits_never_reach_client_output

Run: python3 dev/tests/test_sbs_panes.py      (Chrome tier; skipped without Chrome)
"""
import json
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reporting_hub as H  # noqa: E402  (its fixture: Hub, the pinned clock Friday 09-10-2026)

INT = "#v-reporting .page[data-audience=internal]"
CLI = "#v-reporting .page[data-audience=client]"
WEEK = "2026-10-09"


def ed(page, sec="summary"):
    """The rich editor of a section on a page."""
    return f"{page} section[data-id={sec}] .sheet-ed.ProseMirror"


class SideBySideEditing(H.Hub):
    # ---- helpers ----------------------------------------------------------------------------------------------------
    def open_side(self, w=1400, h=1000):
        self.open_hub(w, h)
        self.b.click("#hubSeg [data-hv='side']")
        self.b.wait("document.querySelectorAll('#v-reporting .page').length==2", 20)
        self.b.pump(0.5)

    def focus_in(self, page, sec="summary"):
        """A real click into a section's words (the report opens its editor on a click; a text section's is always open), then the end of its text."""
        e = json.dumps(ed(page, sec))
        if not self.q(f"!!document.querySelector({e})"):
            self.b.wait(f"!!document.querySelector({json.dumps(f'{page} section[data-id={sec}] .wr-rich.wr-edit')})", 15)
            self.b.click(f"{page} section[data-id={sec}] .wr-rich.wr-edit")
        self.b.wait(f"!!document.querySelector({e}) && document.querySelector({e}).isContentEditable", 10)
        self.b.eval(f"document.querySelector({e}).cxed.editor.commands.focus('end')")
        self.b.pump(0.1)

    def write(self, page, text, sec="summary"):
        self.focus_in(page, sec)
        self.b.type(text)

    def text_of(self, page, sec="summary"):
        return self.q(f"document.querySelector({json.dumps(f'{page} section[data-id={sec}]')}).innerText")

    def editable(self, page, sec="summary"):
        return f"!!document.querySelector({json.dumps(f'{page} section[data-id={sec}] .wr-edit, {page} section[data-id={sec}] .sheet-ed.ProseMirror')})"

    def saved(self, kind, sec="summary", has=None, timeout=12):
        """The saved draft's text for a section, once it holds `has` (the sheet saves 1.5 s after the last change)."""
        text = ""
        for _ in range(int(timeout / 0.5)):
            doc = self.api("/api/report/draft", {"kind": kind, "code": "ABC", "week_ending": WEEK})["doc"]
            text = next((s.get("text", "") for s in doc["sections"] if s["id"] == sec), "")
            if has is None or has in text:
                break
            self.b.pump(0.5)
        return text

    def order(self, page):
        return self.q(f"[...document.querySelectorAll('{page} > section[data-id]')].map(s=>s.dataset.id)")

    def spy_saves(self):
        self.q("""window.__saves=[]; (()=>{const f=window.fetch.bind(window); window.fetch=(u,o)=>{
          if(String(u).endsWith('/api/report/save')){ try{ window.__saves.push(JSON.parse(o.body).doc.audience||'internal'); }catch(e){} }
          return f(u,o); };})()""")

    def status(self):
        return self.q("document.querySelector('#v-reporting .sheet-status').innerText")

    # ---- (a) ------------------------------------------------------------------------------------------------------
    def test_sbs_a_each_pane_saves_its_own_report(self):
        self.open_side()
        self.write(INT, " Plumtree internal words.")
        self.write(CLI, " Quillfeather client words.")
        self.assertIn("Plumtree", self.saved("weekly", has="Plumtree"), "the internal pane saved the internal report")
        self.assertIn("Quillfeather", self.saved("client", has="Quillfeather"), "the client pane saved the client report")
        self.assertNotIn("Quillfeather", self.saved("weekly"), "the client words are not in the internal report")
        self.assertNotIn("Plumtree", self.saved("client"), "the internal words are not in the client report")
        self.assertIn("Plumtree", self.text_of(INT))
        self.assertNotIn("Plumtree", self.text_of(CLI))

    def test_sbs_a_each_pane_has_its_own_dirty_state_and_status(self):
        self.open_side()
        self.spy_saves()
        self.write(INT, " Hazelnut.")
        self.assertIn("Unsaved", self.status(), "the internal pane is dirty")
        self.assertNotIn("Client:", self.status(), "the client pane is not")
        self.b.wait("window.__saves.length>=1", 10)
        self.b.pump(0.3)
        self.assertEqual(self.q("window.__saves"), ["internal"], "only the internal report was saved")
        self.assertIn("Saved", self.status())
        self.write(CLI, " Walnut.")
        self.b.wait("window.__saves.length>=2", 10)
        self.assertEqual(self.q("window.__saves"), ["internal", "client"])
        self.assertRegex(self.status(), r"Saved.*Client: Saved", "each pane has its own save line")

    def test_sbs_a_an_approved_internal_report_locks_only_its_own_pane(self):
        doc = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})["doc"]
        next(x for x in doc["sections"] if x["id"] == "health")["text"] = "UAT start slipped two weeks."
        self.assertTrue(self.api("/api/report/save", {"doc": doc, "base_version": 0})["ok"])
        a = self.api("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        self.open_side()
        self.b.wait(self.editable(CLI), 15)
        self.assertEqual(self.q(f"document.querySelectorAll('{INT} .wr-edit, {INT} .sheet-hbtn').length"), 0, "the approved internal pane is read only")
        self.assertEqual(self.q("document.querySelector('.hubstat[data-k=internal]').innerText.trim()"), "Approved")
        self.write(CLI, " Cranberry.")
        self.assertIn("Cranberry", self.saved("client", has="Cranberry"), "the client pane stays editable and saves")
        self.b.click("#hubEdit")                                  # Edit again: the internal pane opens for editing
        self.b.wait(self.editable(INT), 10)
        self.write(INT, " Gooseberry.")
        self.assertIn("Gooseberry", self.saved("weekly", has="Gooseberry"))

    # ---- (b) ------------------------------------------------------------------------------------------------------
    def menu_btn(self, page, sec="summary"):
        return f"{page} section[data-id={sec}] .sheet-hbtn"

    def pick_menu(self, text):
        self.b.wait(f"[...document.querySelectorAll('.rsmenu [role^=menuitem]')].some(e=>e.textContent.includes({json.dumps(text)}))", 10)
        self.q(f"[...document.querySelectorAll('.rsmenu [role^=menuitem]')].find(e=>e.textContent.includes({json.dumps(text)})).setAttribute('data-pick','1')")
        self.press("[data-pick='1']")

    def test_sbs_b_no_cross_talk_section_menu(self):
        self.open_side()
        self.b.wait(f"!!document.querySelector({json.dumps(self.menu_btn(INT))})", 15)
        before_i, before_c = self.order(INT), self.order(CLI)
        # the internal pane's menu: opens for the internal pane only, and moves only the internal section
        self.press(self.menu_btn(INT))
        self.assertEqual(self.q(f"document.querySelector({json.dumps(self.menu_btn(INT))}).getAttribute('aria-expanded')"), "true")
        self.assertEqual(self.q(f"document.querySelector({json.dumps(self.menu_btn(CLI))}).getAttribute('aria-expanded')"), "false")
        self.pick_menu("Move down")
        self.b.pump(0.3)
        self.assertNotEqual(self.order(INT), before_i)
        self.assertEqual(self.order(CLI), before_c, "the client report did not move")
        self.assertTrue(self.q(f"!!document.activeElement.closest({json.dumps(INT)}) && document.activeElement.dataset.grip==='summary'"),
                        "the focus stays on the internal pane's handle")
        # the client pane's menu: moves only the client section, and the focus stays in the client pane
        after_i = self.order(INT)
        self.press(self.menu_btn(CLI))
        self.pick_menu("Move down")
        self.b.pump(0.3)
        self.assertEqual(self.order(INT), after_i, "the internal report did not move")
        self.assertNotEqual(self.order(CLI), before_c)
        self.assertTrue(self.q(f"!!document.activeElement.closest({json.dumps(CLI)}) && document.activeElement.dataset.grip==='summary'"),
                        "the focus stays on the client pane's handle")
        # Add a text section below, from the client pane: it lands in the client report only
        n_i, n_c = len(self.order(INT)), len(self.order(CLI))
        self.press(self.menu_btn(CLI, "glance"))
        self.pick_menu("Add a text section below")
        self.b.pump(0.4)
        self.assertEqual(len(self.order(CLI)), n_c + 1, "the client report got the text section")
        self.assertEqual(len(self.order(INT)), n_i, "the internal report did not")
        self.press(self.menu_btn(INT, "glance"))
        self.pick_menu("Add a text section below")
        self.b.pump(0.4)
        self.assertEqual(len(self.order(INT)), n_i + 1)
        self.assertEqual(len(self.order(CLI)), n_c + 1)

    def test_sbs_b_no_cross_talk_zoom_is_one_shared_control(self):
        self.open_side()
        self.assertEqual(self.q("document.querySelectorAll('#zIn').length"), 1, "one zoom control for both")
        w0 = self.q(f"[document.querySelector('{INT}').getBoundingClientRect().width, document.querySelector('{CLI}').getBoundingClientRect().width]")
        self.b.click("#zOut")
        self.b.pump(0.4)
        w1 = self.q(f"[document.querySelector('{INT}').getBoundingClientRect().width, document.querySelector('{CLI}').getBoundingClientRect().width]")
        self.assertLess(w1[0], w0[0])
        self.assertLess(w1[1], w0[1])
        self.assertAlmostEqual(w1[0] / w0[0], w1[1] / w0[1], places=2, msg="both panes zoom by the same factor")
        self.focus_in(CLI)                                        # a shortcut from either pane zooms both
        self.b.key("0", 4)
        self.b.pump(0.4)
        w2 = self.q(f"[document.querySelector('{INT}').getBoundingClientRect().width, document.querySelector('{CLI}').getBoundingClientRect().width]")
        self.assertAlmostEqual(w2[0], w0[0], delta=2)
        self.assertAlmostEqual(w2[1], w0[1], delta=2)

    def test_sbs_b_no_cross_talk_active_editor(self):
        self.open_side()
        self.focus_in(INT)
        self.b.wait(f"document.querySelectorAll('{INT} .sheet-rtebar').length===1", 10)
        self.assertEqual(self.q(f"document.querySelectorAll('{CLI} .sheet-rtebar').length"), 0, "the client pane shows no toolbar")
        self.focus_in(CLI)
        self.b.wait(f"document.querySelectorAll('{CLI} .sheet-rtebar').length===1", 10)
        self.assertEqual(self.q(f"document.querySelectorAll('{INT} .sheet-rtebar').length"), 0, "the toolbar followed the focus")
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .sheet-rtebar').length"), 1)

    def test_sbs_b_no_cross_talk_ai_bar(self):
        self.open_side()
        probe = """(()=>{const b=aiBar.value; if(!b) return null; const d=b.ai.document?b.ai.document():null;
          return {inside:[...document.querySelectorAll('#v-reporting .page')].map(p=>p.contains(b.h.el)), place:b.ai.place, kind:d&&d.kind, key:b.ai.key&&b.ai.key()}})()"""
        seen = {}
        for name, page in (("internal", INT), ("client", CLI)):
            self.focus_in(page)
            self.q(f"document.querySelector({json.dumps(ed(page))}).cxed.editor.chain().focus().selectAll().run()")
            self.b.wait(f"(()=>{{const b=aiBar.value; return !!b && document.querySelector({json.dumps(page)}).contains(b.h.el)}})()", 10)
            seen[name] = self.q(probe)
        self.assertEqual(seen["internal"]["inside"], [True, False])
        self.assertEqual(seen["internal"]["place"], "report", "the internal pane asks as the internal report")
        self.assertEqual(seen["internal"]["kind"], None, "the internal report has no client document")
        self.assertEqual(seen["client"]["inside"], [False, True])
        self.assertEqual(seen["client"]["place"], "client")
        self.assertEqual(seen["client"]["kind"], "client")
        self.assertNotEqual(seen["internal"]["key"], seen["client"]["key"], "the same section in the two panes is not the same text")

    def open_picker(self, page, sec="risks"):
        self.q(f"document.querySelector('{page} section[data-id={sec}] .rs-pick-open').scrollIntoView({{block:'center'}})")
        self.b.click(f"{page} section[data-id={sec}] .rs-pick-open")
        self.b.wait(f"!!document.querySelector('{page} section[data-id={sec}] .rs-picker .rs-pick-list')", 10)

    def test_sbs_b_no_cross_talk_two_pickers(self):
        self.open_side()
        self.b.wait(f"!!document.querySelector('{INT} section[data-id=risks] .rs-pick-open')", 15)
        self.open_picker(INT)
        self.open_picker(CLI)
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .rs-picker').length"), 2, "both pickers open at once")
        self.b.click(f"{INT} section[data-id=risks] .rs-pick-search")
        self.b.type("zzzz")
        self.assertEqual(self.q(f"document.querySelector('{INT} .rs-pick-search').value"), "zzzz")
        self.assertEqual(self.q(f"document.querySelector('{CLI} .rs-pick-search').value"), "", "the other picker's search is its own")
        n = self.q(f"document.querySelectorAll('{CLI} section[data-id=risks] .rs-pick-row input').length")
        if n:
            self.b.click(f"{CLI} section[data-id=risks] .rs-pick-row input")
            self.assertEqual(self.q(f"document.querySelectorAll('{INT} .rs-pick-row input:checked').length"), 0, "a tick in one picker is not a tick in the other")
            self.assertEqual(self.q(f"document.querySelectorAll('{CLI} .rs-pick-row input:checked').length"), 1)

    def add_free(self, page):
        """A text section added at the foot of a pane (its editor is always open); returns its id."""
        n = self.q(f"document.querySelectorAll('{page} > section[data-id]').length")
        self.b.click(f"{page} [data-addtext]")
        self.b.wait(f"document.querySelectorAll('{page} > section[data-id]').length=={n + 1}", 10)
        sec = self.q(f"[...document.querySelectorAll('{page} > section[data-id]')].pop().dataset.id")
        self.b.wait(f"!!document.querySelector({json.dumps(ed(page, sec))})", 10)
        return sec

    def test_sbs_b_no_cross_talk_shortcuts_apply_to_the_focused_pane(self):
        self.open_side()
        fi, fc = self.add_free(INT), self.add_free(CLI)           # a text section in each pane: two editors open at once
        self.write(INT, "Aaaa", fi)
        self.write(CLI, "Bbbb", fc)
        self.assertIn("Aaaa", self.text_of(INT, fi))
        self.assertIn("Bbbb", self.text_of(CLI, fc))
        self.focus_in(CLI, fc)
        self.b.key("z", 4)                                        # undo, in the pane that has the focus
        self.b.pump(0.2)
        self.assertNotIn("Bbbb", self.text_of(CLI, fc), "undo took the client pane's typing back")
        self.assertIn("Aaaa", self.text_of(INT, fi), "and left the internal pane's alone")
        # strike-through (the editor's own shortcut) lands in the focused pane only
        self.focus_in(INT, fi)
        self.q(f"document.querySelector({json.dumps(ed(INT, fi))}).cxed.editor.chain().focus().selectAll().run()")
        self.b.key("x", 4 | 8)
        self.b.pump(0.2)
        self.assertTrue(self.q(f"!!document.querySelector({json.dumps(ed(INT, fi))}).querySelector('s,del,strike')"))
        self.assertFalse(self.q(f"!!document.querySelector({json.dumps(ed(CLI, fc))}).querySelector('s,del,strike')"))
        # Command S saves the pane that has the focus now, not both
        self.b.pump(2.5)                                          # what is pending is saved first
        self.spy_saves()
        self.write(CLI, " Cccc", fc)
        self.write(INT, " Dddd", fi)
        self.b.key("s", 4)
        self.b.wait("window.__saves.length>=1", 3)
        self.assertEqual(self.q("window.__saves"), ["internal"], "Command S saved the focused pane; the other waits for its own timer")

    def test_sbs_b_no_duplicate_ids_with_everything_open(self):
        self.open_side()
        self.b.wait(f"!!document.querySelector('{INT} section[data-id=risks] .rs-pick-open')", 15)
        self.open_picker(INT)
        self.open_picker(CLI)
        self.focus_in(INT)
        self.focus_in(CLI)
        self.q(f"document.querySelector({json.dumps(ed(CLI))}).cxed.editor.chain().focus().selectAll().run()")
        self.b.pump(0.3)
        self.press(self.menu_btn(INT, "glance"))
        dup = self.q("""(()=>{const m={};document.querySelectorAll('[id]').forEach(e=>{m[e.id]=(m[e.id]||0)+1});return Object.entries(m).filter(([k,v])=>v>1)})()""")
        self.assertEqual(dup, [], "no id appears twice on the page")

    # ---- (c) ------------------------------------------------------------------------------------------------------
    def test_sbs_c_escape_closes_only_the_active_pane(self):
        self.open_side()
        self.b.wait(f"!!document.querySelector('{INT} section[data-id=risks] .rs-pick-open')", 15)
        # the section menu of one pane: Esc closes it and puts the focus back on that pane's button
        self.press(self.menu_btn(INT))
        self.b.wait("!!document.querySelector('.rsmenu')", 10)
        self.b.key("Escape")
        self.b.wait("!document.querySelector('.rsmenu')", 10)
        self.assertTrue(self.q(f"document.activeElement===document.querySelector({json.dumps(self.menu_btn(INT))})"))
        # two pickers and the AI bar: each Esc closes the one the focus is in
        self.open_picker(INT)
        self.open_picker(CLI)
        self.focus_in(INT)
        self.q(f"document.querySelector({json.dumps(ed(INT))}).cxed.editor.chain().focus().selectAll().run()")
        self.b.key("/", 1)                                         # Alt + / opens the AI bar's menu
        self.b.wait("!!aiBar.value && aiBar.value.shown", 10)
        self.b.key("Escape")
        self.b.wait("!aiBar.value || !aiBar.value.shown", 10)
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .rs-picker').length"), 2, "the bar's Esc left both pickers open")
        self.b.click(f"{CLI} section[data-id=risks] .rs-pick-search")
        self.b.key("Escape")
        self.b.pump(0.2)
        self.assertEqual(self.q(f"document.querySelectorAll('{CLI} .rs-picker').length"), 0, "Esc closed the picker the focus was in")
        self.assertEqual(self.q(f"document.querySelectorAll('{INT} .rs-picker').length"), 1, "and the other pane's picker stayed")
        self.b.click(f"{INT} section[data-id=risks] .rs-pick-search")
        self.b.key("Escape")
        self.b.pump(0.2)
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .rs-picker').length"), 0)

    # ---- (d) ------------------------------------------------------------------------------------------------------
    def test_sbs_d_scroll_together(self):
        for w, h in H.WIDTHS:
            with self.subTest(width=w):
                self.open_side(w, h)
                self.write(INT, " " + "Longwinded sentence about nothing at all. " * 12)
                self.b.pump(0.5)
                self.assertEqual(self.q("document.querySelectorAll('#v-reporting .sheet-scroll').length"), 1, "one scroller for both editable panes")
                self.q("document.querySelector('#v-reporting .sheet-scroll').scrollTop=500")
                self.b.pump(0.3)
                tops = self.q("[...document.querySelectorAll('#v-reporting .page')].map(x=>Math.round(x.getBoundingClientRect().top))")
                self.assertEqual(tops[0], tops[1], "scrolled together")
                heights = self.q(f"['{INT}','{CLI}'].map(p=>Math.round(document.querySelector(p+' section[data-id=summary]').getBoundingClientRect().height))")
                self.assertEqual(heights[0], heights[1], "a section is as tall in both panes, so they stay level while you type")
                top = self.q("document.querySelector('#v-reporting .sheet-scroll').scrollTop")
                self.focus_in(CLI)
                self.b.type(" more words")
                self.b.pump(0.3)
                self.assertAlmostEqual(self.q("document.querySelector('#v-reporting .sheet-scroll').scrollTop"), top, delta=60, msg="typing does not jump the scroll")

    # ---- (e) ------------------------------------------------------------------------------------------------------
    def test_sbs_e_internal_edits_never_reach_client_output(self):
        self.open_side()
        self.write(INT, " Zanzibarinternal secret.")
        self.focus_in(INT)
        self.b.click(f"{INT} [data-addtext]")                     # an internal text section, with its own words
        self.b.wait(f"document.querySelectorAll('{INT} > section[data-id^=free_]').length===1", 10)
        free = self.q(f"document.querySelector('{INT} > section[data-id^=free_]').dataset.id")
        self.write(INT, "Marzipaninternal note.", free)
        self.assertIn("Zanzibarinternal", self.saved("weekly", has="Zanzibarinternal"))
        self.assertIn("Marzipaninternal", self.saved("weekly", free, has="Marzipaninternal"))
        # nothing reached the client pane or the client document
        self.assertNotIn("Zanzibarinternal", self.q(f"document.querySelector('{CLI}').innerText"))
        self.assertNotIn("Marzipaninternal", self.q(f"document.querySelector('{CLI}').innerText"))
        self.assertEqual(self.q(f"document.querySelectorAll('{CLI} section[data-id={free}]').length"), 0, "an internal text section stays internal")
        self.assertIn("Internal only", self.q(f"document.querySelector('{INT} section[data-id={free}] .sheet-match').textContent"))
        client = json.dumps(self.api("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})["doc"])
        self.assertNotIn("Zanzibarinternal", client)
        self.assertNotIn("Marzipaninternal", client)
        # the client export (HTML and Word), once the internal week is approved, has none of it
        a = self.api("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"], a)
        self.open_side()
        self.b.wait(self.editable(CLI), 15)
        self.write(CLI, " Quillfeather for the client.")
        self.assertIn("Quillfeather", self.saved("client", has="Quillfeather"))
        for fmt in ("html", "docx"):
            r = self.api("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": fmt, "on_clash": "overwrite"})
            self.assertTrue(r.get("ok"), r)
            path = self.v.root / r["path"]
            if fmt == "docx":
                with zipfile.ZipFile(path) as z:
                    body = z.read("word/document.xml").decode("utf-8")
            else:
                body = path.read_text(encoding="utf-8")
            self.assertIn("Quillfeather", body, f"{fmt}: the client's own words are in")
            self.assertNotIn("Zanzibarinternal", body, f"{fmt}: no internal edit")
            self.assertNotIn("Marzipaninternal", body, f"{fmt}: no internal text section")
        # Match internal still works, and only when pressed
        self.open_side()
        self.b.wait(f"!!document.querySelector('{CLI} section[data-id=summary] .sheet-match')", 15)
        self.assertIn("Edited for the client", self.q(f"document.querySelector('{CLI} section[data-id=summary] .sheet-match').textContent"))
        self.assertNotIn("Zanzibarinternal", self.text_of(CLI))


if __name__ == "__main__":
    unittest.main()
