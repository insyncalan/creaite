"""v2.5.0 sbsfix (Team Cap's provisional client-leak verdict on editable Side by side, #135 comment 6254920560). Real Chrome on the real
live server (no Claude runs); desktop only; fictional words only.

Brief item -> test:
  (1) Match internal runs the client gate BEFORE it copies; the client pane never holds unsaved internal words
      the check route (read only, findings per document) ........ MatchCheckRoute.test_each_needle_is_a_finding_and_clean_words_are_not
                                                                   MatchCheckRoute.test_the_route_writes_nothing_and_refuses_a_bad_request
      one section, internal EDIT not saved ...................... MatchGate.test_a_section_with_internal_wording_is_held_and_named
      a clean section matches ................................... MatchGate.test_a_clean_section_matches
      Match all (the hub's button, data-crmatchall) copies the clean ones only
                                                                   MatchGate.test_match_all_copies_the_clean_sections_only
      the client page when the check cannot run ................. MatchGate.test_nothing_is_copied_when_the_check_cannot_run
  (2) a pane without its own AI shows none; Find the source is per pane, no fallback
                                                                   PaneAi.test_the_right_pane_without_its_own_ai_has_no_ai_bar
                                                                   PaneAi.test_find_the_source_on_the_right_pane_never_calls_the_left_handler

  (3) one Match internal for every section control only (the sheet's own bar button was dead and is gone)
                                                                   OneMatchAll.test_one_control_in_each_view
                                                                   OneMatchAllFixture.test_the_sheets_own_bar_never_carries_one

Run: python3 dev/tests/test_sbs_matchgate.py      (Chrome tier; skipped without Chrome)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reporting_hub as H  # noqa: E402  (its fixture: Hub, the pinned clock Friday 09-10-2026)
import test_sbs_panes as S  # noqa: E402  (its helpers; only the module is used, its tests are not collected here)
import test_report_editor as E  # noqa: E402  (the sheet fixture)

INT, CLI, WEEK = S.INT, S.CLI, S.WEEK
# What must never sit on the client's draft: an owner's name (owns only items a client can't see), the word "confidential", the title
# of an item that is not client-visible, a line the project's memory marks "Client-safe: no".
NEEDLES = ("Omar Ali", "confidential", "Confirm tester names", "Budget overrun on phase one is being absorbed")
HOSTILE = "Zanzibarinternal: Omar Ali to Confirm tester names. This is confidential. Budget overrun on phase one is being absorbed."
CLEAN = "Quincebrook is on plan for the week."


class Base(H.Hub):
    shared_server = False                                      # each test has its own vault: they save drafts
    open_side = S.SideBySideEditing.open_side
    focus_in = S.SideBySideEditing.focus_in
    write = S.SideBySideEditing.write
    text_of = S.SideBySideEditing.text_of
    saved = S.SideBySideEditing.saved

    def client_draft(self):
        return self.api("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})["doc"]

    def staging_files_text(self):
        """Every client draft file in staging, as text (the saved draft is a file there)."""
        out = ""
        for f in (self.v.root / "system/staging/drafts").glob("*lient*"):
            if f.is_file():
                out += f.read_text(encoding="utf-8", errors="ignore")
        return out

    def held_dialog(self):
        return self.q("(()=>{const d=document.getElementById('crHeldDlg'); return d && d.open ? d.innerText : ''})()")

    def match_btn(self, sec):
        return f"{CLI} section[data-id={sec}] .sheet-match .linkbtn"

    def assert_client_clean(self, why=""):
        """The client pane, the saved client draft (after the autosave would have run) and the files in staging hold no needle."""
        self.b.pump(2.6)
        self.assertNotIn("Zanzibarinternal", self.q(f"document.querySelector('{CLI}').innerText"), why)
        for n in NEEDLES:
            self.assertNotIn(n.lower(), self.q(f"document.querySelector('{CLI}').innerText").lower(), why)
        blob = json.dumps(self.client_draft()) + self.staging_files_text()
        for n in NEEDLES + ("Zanzibarinternal",):
            self.assertNotIn(n.lower(), blob.lower(), f"{why}: the client draft holds {n!r}")


class MatchCheckRoute(Base):
    def test_each_needle_is_a_finding_and_clean_words_are_not(self):
        self.open_hub()
        base = self.client_draft()

        def with_summary(text):
            d = json.loads(json.dumps(base))
            next(s for s in d["sections"] if s["id"] == "summary")["text"] = text
            return d
        docs = [base, with_summary(CLEAN)] + [with_summary(f"Words with {n} in them.") for n in NEEDLES] + [with_summary(HOSTILE)]
        r = self.api("/api/report/match-check", {"docs": docs})
        self.assertTrue(r["ok"], r)
        f = r["findings"]
        self.assertEqual(f[0], [], "the fixture's own client draft is clean")
        self.assertEqual(f[1], [], "clean words are not a finding")
        for n, found in zip(NEEDLES, f[2:2 + len(NEEDLES)]):
            self.assertTrue(found, f"{n!r} is a finding")
        self.assertTrue(f[-1])

    def test_the_route_writes_nothing_and_refuses_a_bad_request(self):
        self.open_hub()
        before = self.staging_files_text()
        d = self.client_draft()
        self.api("/api/report/match-check", {"docs": [d]})
        self.assertEqual(self.staging_files_text(), before)
        self.assertFalse(self.api("/api/report/match-check", {"docs": "no"})["ok"])
        self.assertFalse(self.api("/api/report/match-check", {"docs": [d] * 61})["ok"])
        internal = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})["doc"]
        self.assertFalse(self.api("/api/report/match-check", {"docs": [internal]})["ok"], "only a client report has this check")


class MatchGate(Base):
    def type_internal(self, text, sec="summary"):
        """An internal EDIT, typed in the left pane and not saved by anything but the autosave timer (1.5 s) the test does not wait for."""
        self.write(INT, text, sec)

    def test_a_section_with_internal_wording_is_held_and_named(self):
        self.open_side()
        self.type_internal(HOSTILE)
        self.b.wait(f"!!document.querySelector({json.dumps(self.match_btn('summary'))})", 10)
        before = self.text_of(CLI)
        self.press(self.match_btn("summary"))
        self.b.wait("(()=>{const d=document.getElementById('crHeldDlg'); return !!d && d.open})()", 10)
        shown = self.held_dialog()
        self.assertIn("Not matched: Summary", shown, "the section is named")
        self.assertIn("internal wording", shown)
        self.assertRegex(shown.lower(), r"confidential|omar ali|tester names|budget overrun", "the findings are listed")
        self.assertEqual(self.text_of(CLI), before, "the client section is as it was")
        self.assert_client_clean("Match internal on one section")

    def test_a_clean_section_matches(self):
        self.open_side()
        self.type_internal(CLEAN)
        self.b.wait(f"!!document.querySelector({json.dumps(self.match_btn('summary'))})", 10)
        self.press(self.match_btn("summary"))
        self.b.wait(f"document.querySelector('{CLI} section[data-id=summary]').innerText.includes('Quincebrook')", 10)
        self.assertEqual(self.held_dialog(), "", "nothing was held")
        self.assertIn("Quincebrook", self.saved("client", has="Quincebrook"), "and the client pane saves what it was given")

    def two_sections(self):
        self.open_side()
        self.type_internal(HOSTILE, "summary")
        self.type_internal(CLEAN, "next_week")
        self.b.wait(f"!!document.querySelector({json.dumps(self.match_btn('next_week'))})", 10)

    def after_match_all(self):
        self.b.wait("(()=>{const d=document.getElementById('crHeldDlg'); return !!d && d.open})()", 15)
        shown = self.held_dialog()
        self.assertIn("Not matched: Summary", shown)
        self.assertNotIn("Not matched: Next week", shown, "the clean section is not held")
        self.assertIn("Next week", shown, "and is named as matched")
        self.b.wait(f"document.querySelector('{CLI} section[data-id=next_week]').innerText.includes('Quincebrook')", 10)
        self.assertNotIn("Zanzibarinternal", self.text_of(CLI, "summary"))
        self.assert_client_clean("Match internal for every section")
        self.assertIn("Quincebrook", self.saved("client", "next_week", has="Quincebrook"), "the clean section was copied and saved")

    def test_match_all_copies_the_clean_sections_only(self):
        self.two_sections()
        self.q("document.querySelector('[data-crmatchall]').scrollIntoView({block:'center'})")
        self.b.click("[data-crmatchall]")                     # the hub's own button
        self.after_match_all()

    def test_nothing_is_copied_when_the_check_cannot_run(self):
        self.open_side()
        self.type_internal(CLEAN)
        self.b.wait(f"!!document.querySelector({json.dumps(self.match_btn('summary'))})", 10)
        self.q("""(()=>{const f=window.fetch.bind(window); window.fetch=(u,o)=>String(u).endsWith('/api/report/match-check')?Promise.resolve(new Response('{"ok":false,"message":"down"}',{status:500,headers:{'Content-Type':'application/json'}})):f(u,o);})()""")
        self.press(self.match_btn("summary"))
        self.b.wait("(()=>{const d=document.getElementById('crHeldDlg'); return !!d && d.open})()", 10)
        self.assertIn("nothing was copied", self.held_dialog().lower())
        self.assertNotIn("Quincebrook", self.text_of(CLI), "failing closed: no copy")


COUNT = "[...document.querySelectorAll('#v-reporting button, #v-reporting a')].filter(e=>/Match internal for every section/i.test(e.textContent)).length"


class OneMatchAll(Base):
    def test_one_control_in_each_view(self):
        self.open_hub()
        for view, want in (("client", 1), ("side", 1)):          # the hub's button, above the client page, and nothing else
            self.b.click(f"#hubSeg [data-hv='{view}']")
            self.b.wait("!!document.querySelector('[data-crmatchall]')", 20)
            self.b.pump(0.5)
            self.assertEqual(self.q(COUNT), want, f"{view}: Match internal for every section controls")
            self.assertEqual(self.q("document.querySelectorAll('[data-crmatchall]').length"), want, view)
            self.assertEqual(self.q("document.querySelectorAll('.sheet-matchall').length"), 0, view)
            self.assertEqual(self.q("document.querySelectorAll('.sheet-bar [data-crmatchall]').length"), 0, view)


class OneMatchAllFixture(E.SheetCase):
    def test_the_sheets_own_bar_never_carries_one(self):
        # the sheet's default bar (no renderBar) with an editable partner: the only way the old button could draw
        self.b.eval("""(() => { const p = JSON.parse(JSON.stringify(SH.doc)); p.audience = 'client';
          SH.partner = {doc: p, label: 'Client', baseVersion: 1, scrollKey: 'p', onChange: (d, why) => { SH.partner.doc = d; SH.draw(); }, onSave: async r => ({ok: true, version: 2})};
          SH.draw = () => { mount(Sheet, {doc: SH.doc, baseVersion: SH.base, scrollKey: SH.key, partner: SH.partner,
            onChange: (d, why) => { SH.doc = d; SH.draw(); }, onSave: async r => ({ok: true, version: 9}), onEvent: e => {}}, SH.el); return true; };
          SH.draw(); })()""")
        self.b.wait("document.querySelectorAll('#shFix .sheet-a4 > .page').length===2")
        self.assertEqual(self.b.eval("document.querySelectorAll('#shFix .sheet-bar').length"), 1)
        self.assertEqual(self.b.eval("document.querySelectorAll('#shFix .sheet-matchall').length"), 0)
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#shFix .sheet-bar button')].filter(e=>/Match internal for every/i.test(e.textContent)).length"), 0)


class PaneAi(E.SheetCase):
    """The sheet fixture, side by side, the left pane with an AI account and the right without one."""
    def setUp(self):
        super().setUp()
        self.b.eval("""(() => { const p = JSON.parse(JSON.stringify(SH.doc)); p.audience = 'client'; p.client = 'Kestrel Group';
          SH.partner = {doc: p, label: 'Client', baseVersion: 1, scrollKey: 'p', onChange: (d, why) => { SH.partner.doc = d; SH.draw(); },
            onSave: async r => ({ok: true, version: 2})};
          SH.ai = {place: 'report', project: () => 'ABC'}; SH.leftFind = []; SH.onSel = async (id, sel) => { SH.leftFind.push(id); return {found: []}; };
          SH.draw = () => { mount(Sheet, {doc: SH.doc, baseVersion: SH.base, scrollKey: SH.key, ai: SH.ai, onSelectAction: SH.onSel, partner: SH.partner,
            onChange: (d, why) => { SH.doc = d; SH.draw(); }, onSave: async r => ({ok: true, version: 9}), onEvent: e => {}}, SH.el); return true; };
          SH.draw(); })()""")
        self.b.wait("document.querySelectorAll('#shFix .sheet-a4 > .page').length===2")

    def select_in(self, pane):
        ed = f"document.querySelectorAll('#shFix .sheet-a4 > .page')[{pane}].querySelector('section[data-id=summary] .sheet-rich.ProseMirror')"
        self.b.wait(f"!!{ed}", 10)
        self.b.eval(f"{ed}.scrollIntoView({{block:'center'}})")
        r = self.b.eval(f"(()=>{{const r={ed}.getBoundingClientRect(); return [r.left+20, r.top+10]}})()")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):        # a real click into the words, as a person starts
            self.b.call("Input.dispatchMouseEvent", type=kind, x=r[0], y=r[1], button="left", clickCount=1)
        self.b.pump(0.4)
        self.b.eval(f"(()=>{{const e={ed}; e.cxed.editor.chain().focus().selectAll().run()}})()")
        self.b.pump(0.6)

    def bar_in(self, pane):
        """Whether the AI bar belongs to the editor of this pane."""
        return self.b.eval(f"(()=>{{const b=aiBar.value; return !!b && document.querySelectorAll('#shFix .sheet-a4 > .page')[{pane}].contains(b.h.el)}})()")

    def test_the_right_pane_without_its_own_ai_has_no_ai_bar(self):
        self.select_in(0)
        self.b.wait("!!document.querySelector('#aiLayer .aispark')", 10)          # the left pane has its own account: it shows
        self.assertTrue(self.bar_in(0))
        self.select_in(1)
        self.assertFalse(self.bar_in(1), "the right pane has no AI of its own and never borrows the left pane's")

    def test_find_the_source_on_the_right_pane_never_calls_the_left_handler(self):
        self.b.eval("SH.partner.ai = {place: 'report', project: () => 'ABC'}; SH.draw();")      # an AI account, but no onSelectAction of its own
        self.select_in(1)
        self.b.wait("!!document.querySelector('#aiLayer .aispark')", 10)
        self.b.eval("document.querySelector('#aiLayer .aispark').click()")
        self.b.wait("!!document.querySelector('#aiLayer [data-ai=source]')", 10)
        self.b.eval("document.querySelector('#aiLayer [data-ai=source]').click()")
        self.b.wait("!!document.querySelector('#shFix .sheet-found')", 10)
        self.assertIn("isn't available", self.b.eval("document.querySelector('#shFix .sheet-found').innerText"))
        self.assertEqual(self.b.eval("SH.leftFind"), [], "the left pane's handler was not called")
        self.select_in(0)                                                                         # the left pane still finds its own
        self.b.wait("!!document.querySelector('#aiLayer .aispark')", 10)
        self.b.eval("document.querySelector('#aiLayer .aispark').click()")
        self.b.wait("!!document.querySelector('#aiLayer [data-ai=source]')", 10)
        self.b.eval("document.querySelector('#aiLayer [data-ai=source]').click()")
        self.b.wait("SH.leftFind.length===1", 10)


if __name__ == "__main__":
    unittest.main()
