"""#234 review (EARLY HIGH): a left-out row's eye asks the tracker for the row (/api/report/reshow); if another report opens before the answer
comes back, the answer must land nowhere. Real Chrome on the real live server (no Claude runs); fictional words only.

  - the eye in the internal pane of Side by side, the answer held 6 s, ABC switched to DEF: DEF's internal pane, weeklyDoc, crInternal,
    DEF's client draft and DEF's saved files hold nothing from ABC ........ test_internal_eye_then_switch_lands_nowhere
  - the same with the eye in the client pane ............................... test_client_eye_then_switch_lands_nowhere
  - control, no switch: the row comes back with the tracker's words ........ test_no_switch_the_row_comes_back
  - the same eye, then another week of ABC opened ........................... test_internal_eye_then_week_switch_lands_nowhere
  - review (b), (d): a row saved shown with empty cells says Left out, comes back from the tracker, and the HTML export is still
    the styled page ........................................................ BlankRowSaved.*

Run: python3 dev/tests/test_reshow_switch.py      (Chrome tier; skipped without Chrome)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate, new  # noqa: E402

INT = "#v-reporting .page[data-audience=internal]"
CLI = "#v-reporting .page[data-audience=client]"
ABC_WORDS = ("Escalate data access", "Example Programme", "Sign the scope letter", "The scope letter is signed")
CLIENT_MSG = ("What it is: The scope letter is signed this week.\nWhat it means for you: Work can start.\n"
              "What is being done: We sent the letter.")
DELAY = """(()=>{const f=window.fetch.bind(window); window.fetch=(u,o)=>String(u).endsWith('/api/report/reshow')
  ? new Promise(r=>setTimeout(r,6000)).then(()=>f(u,o)) : f(u,o);})()"""


class Base(LiveBrowserCase):
    shared_server = False                        # each test saves drafts

    @classmethod
    def load(cls, v):
        populate(v)
        from test_tracker import ABC
        v.propose("clientrow", [new("actions", 1, project="ABC", description="Sign the scope letter", owner="Jane Doe",
                                    due_date="2026-01-05", raised="2026-01-01", client_visible=1, client_message=CLIENT_MSG,
                                    source=f"{ABC}/minutes/2026-01-01 Steering.docx — Actions")])
        v.run("apply")

    def api(self, path, body):
        return self.b.eval(f"""fetch({json.dumps(path)},{{method:'POST',headers:{{'Content-Type':'application/json','X-Creaite-Token':D.token}},
          body:JSON.stringify({json.dumps(body)})}}).then(r=>r.json())""")

    def leave_out(self, kind, blank=False):
        """Save the ABC report of `kind` with every overdue row left out (each is saved as its reference only) and return a ref whose item
        the saved report no longer holds. `blank`: instead the first row is saved shown with empty cells (turned back on before the fix)."""
        d = self.api("/api/report/draft", {"kind": kind, "code": "ABC"})
        doc = d["doc"]
        sec = next(s for s in doc["sections"] if s["id"] == "overdue")
        if blank:
            row = next(r for r in sec["rows"] if r.get("ref"))
            row.update(shown=True, cells={})
        else:
            for r in sec["rows"]:
                r["shown"] = False
        saved = self.api("/api/report/save", {"doc": doc, "base_version": doc.get("version")})
        self.assertTrue(saved.get("ok"), saved)
        if blank:
            return row["ref"]
        back = self.api("/api/report/draft", {"kind": kind, "code": "ABC"})["doc"]
        rows = next(s for s in back["sections"] if s["id"] == "overdue")["rows"]
        return next(r["ref"] for r in rows if r.get("ref") and r["ref"] not in (back.get("items") or {}))

    def open_side(self, code="ABC"):
        self.b.reload("typeof go==='function' && LIVE")
        for _ in range(4):
            self.b.eval("(()=>{ for (const c of ['ABC','DEF']) { const p=P.find(p=>p.code===c); if (p) p.cr=true; } crTick.value++; })()")
            self.b.pump(0.3)
        self.b.eval(f"go('reporting','{code}')")
        self.b.wait("document.querySelector('#v-reporting .page')", 25)
        self.b.click("#hubSeg [data-hv='side']")
        self.b.wait("document.querySelectorAll('#v-reporting .page').length==2", 20)
        self.b.pump(0.5)

    def bare(self, page, ref):
        return f"{page} [data-id=overdue] tr.wr-bare[data-ref='{ref}']"

    def switch_and_check(self, page, ref):
        self.b.wait(f"document.querySelector(\"{self.bare(page, ref)}\")", 10)
        self.b.eval(DELAY)
        self.b.eval(f"document.querySelector(\"{self.bare(page, ref)} .wr-eye\").click()")
        self.b.pump(0.3)
        self.b.eval("go('reporting','DEF')")
        self.b.wait("weeklyDoc.value && weeklyDoc.value.project==='DEF' && document.querySelector('#v-reporting .page')", 25)
        self.b.pump(9)                           # the held answer arrives (6 s) and any autosave runs
        if self.b.eval("!!document.querySelector('[data-crmatchall]')"):     # the reviewer's path: Match internal on DEF afterwards
            self.b.eval("window.confirm=()=>true; setTimeout(()=>document.querySelector('[data-crmatchall]').click(),10); 1")
            self.b.pump(6)
        state = self.b.eval("""({wk: weeklyDoc.value && weeklyDoc.value.project, ci: crInternal.value && crInternal.value.project,
          cd: crDoc.value && crDoc.value.project, page: document.querySelector('#v-reporting').innerText,
          blob: JSON.stringify([weeklyDoc.value, crInternal.value, crDoc.value])})""")
        self.assertEqual(state["wk"], "DEF")
        self.assertIn(state["ci"], (None, "DEF"))
        self.assertIn(state["cd"], (None, "DEF"))
        for w in ABC_WORDS:
            if w != "Example Programme":         # the hub's project switcher names every project
                self.assertNotIn(w, state["page"], f"DEF's page shows {w!r}")
            self.assertNotIn(w, state["blob"], f"DEF's documents on the page hold {w!r}")
        for kind in ("weekly", "client"):
            d = self.api("/api/report/draft", {"kind": kind, "code": "DEF"})
            if d.get("ok"):
                for w in ABC_WORDS[:1] + ABC_WORDS[2:]:
                    self.assertNotIn(w, json.dumps(d["doc"]), f"DEF's {kind} draft holds {w!r}")
        for f in (self.v.root / "system/staging/drafts").glob("*Digital Enablement*"):
            text = f.read_text(encoding="utf-8", errors="ignore")
            for w in ABC_WORDS[:1] + ABC_WORDS[2:]:
                self.assertNotIn(w, text, f"{f.name} holds {w!r}")

class ReshowSwitch(Base):
    def test_internal_eye_then_switch_lands_nowhere(self):
        ref = self.leave_out("weekly")
        self.open_side()
        self.switch_and_check(INT, ref)

    def test_client_eye_then_switch_lands_nowhere(self):
        ref = self.leave_out("client")
        self.open_side()
        self.switch_and_check(CLI, ref)

    def test_no_switch_the_row_comes_back(self):
        ref = self.leave_out("weekly")
        a = next(r for r in self.v.rows("actions") if r["id"] == ref)
        self.open_side()
        self.b.wait(f"document.querySelector(\"{self.bare(INT, ref)}\")", 10)
        self.b.eval(DELAY)
        self.b.eval(f"document.querySelector(\"{self.bare(INT, ref)} .wr-eye\").click()")
        row = f"{INT} [data-id=overdue] tr[data-ref='{ref}']:not(.hidrow)"
        self.b.wait(f"document.querySelector(\"{row}\")", 15)
        self.assertIn(a["description"], self.b.eval(f"document.querySelector(\"{row}\").innerText"))
        self.assertEqual(self.b.eval("weeklyDoc.value.project"), "ABC")


    def test_internal_eye_then_week_switch_lands_nowhere(self):
        ref = self.leave_out("weekly")
        self.open_side()
        self.b.wait(f"document.querySelector(\"{self.bare(INT, ref)}\")", 10)
        week = self.b.eval("weeklyDoc.value.date")
        self.b.eval(DELAY)
        self.b.eval(f"document.querySelector(\"{self.bare(INT, ref)} .wr-eye\").click()")
        self.b.pump(0.3)
        self.b.eval("loadHub('ABC','2026-10-02')")
        self.b.wait("weeklyDoc.value && weeklyDoc.value.date==='2026-10-02'", 25)
        self.b.pump(9)
        self.assertEqual(self.b.eval("weeklyDoc.value.date"), "2026-10-02", f"the {week} answer replaced the other week's report")
        self.assertIn(self.b.eval("crInternal.value && crInternal.value.date"), (None, "2026-10-02"))


class BlankRowSaved(Base):
    """Review (b), (d): a row saved shown with empty cells is drawn left out (never "Click to write"), its eye fills it from the tracker,
    and the report's own styled page is still what the HTML export writes."""
    from test_report_export_page import ExportPage as _E
    export, saved, drafts = _E.export, _E.saved, _E.drafts
    del _E

    def ev(self, js):
        return self.b.eval(js)

    def test_a_blank_row_says_left_out_and_comes_back_from_the_tracker(self):
        ref = self.leave_out("weekly", blank=True)
        a = next(r for r in self.v.rows("actions") if r["id"] == ref)
        self.open_side()
        self.b.click("#hubSeg [data-hv='internal']")
        self.b.wait("document.querySelectorAll('#v-reporting .page').length==1", 20)
        row = f"#v-reporting [data-id=overdue] tr[data-ref='{ref}']"
        self.b.wait(f"document.querySelector(\"{row}\")", 10)
        text = self.ev(f"document.querySelector(\"{row}\").textContent")
        self.assertNotIn("Click to write", text)
        self.assertIn("Left out", text)
        self.ev(f"document.querySelector(\"{row} .wr-eye\").click()")
        self.b.wait(f"document.querySelector(\"{row}:not(.hidrow)\")", 15)
        self.assertIn(a["description"], self.ev(f"document.querySelector(\"{row}\").innerText"))

    def test_a_blank_row_still_exports_the_styled_page(self):
        ref = self.leave_out("weekly", blank=True)
        self.open_side()
        self.b.click("#hubSeg [data-hv='internal']")
        self.b.wait("document.querySelectorAll('#v-reporting .page').length==1", 20)
        self.ev("document.querySelector('#v-reporting #hubExp').click()")
        self.b.wait("document.querySelector('#v-reporting .sheet-exported') && !document.querySelector('#v-reporting .wr-eye')", 10)
        self.b.pump(0.5)
        html = self.export("html").read_text(encoding="utf-8")
        self.assertIn('class="wr-r"', html, "the styled page, not the plain renderer")
        self.assertNotIn(ref, html)
        self.assertNotRegex(html, r"<tr[^>]*>(\s*<td[^>]*>\s*</td>)+\s*</tr>")


if __name__ == "__main__":
    unittest.main()
