"""#238 delta (v2.5.3): Your reviews on Activity › Usage, in real Chrome against the real live server (fictional notes).

The list (newest first, dates DD-MM-YYYY), Download as CSV (the same cells as usage_reviews.csv_text) and the inline form.
Saving needs POST /api/usage/review, which the live server gets from dev/proposals/usage-reviews/live_server.diff (guarded):
- before the diff (this branch): "Add a review note" is held, with the reason as its tooltip (ReviewsHeld), and the route tests
  (ReviewsSave) are expected failures;
- with the diff applied (a scratch copy of the tree; the README says how), ReviewsHeld is skipped and ReviewsSave passes.

Run: python3 dev/tests/test_usage_reviews_browser.py   (needs Google Chrome; skipped otherwise). Desktop width only (1400 and 900).
"""
import json
import os
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import usage_fixture as fx  # noqa: E402
import usage_reviews  # noqa: E402
from live_browser import TEST_PALETTES_JS, LiveBrowserCase  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
ROUTE_IN = "usage_reviews.routes(LOCK)" in (REPO / "system" / "scripts" / "live_server.py").read_text(encoding="utf-8")
until_applied = (lambda f: f) if ROUTE_IN else unittest.expectedFailure     # the route tests pass once the diff is in

PANEL = "document.querySelector('#actUsage')"
ROWS = "[...document.querySelectorAll('#actUsage table[aria-label=\"Your reviews\"] tbody tr')].map(tr=>[...tr.children].map(c=>c.textContent))"
NOTES = [
    {"date": "2026-10-12", "saw": "Start load about 21,000 tokens a run", "decided": "Trim the rules file first",
     "name": "POISONED Jane Example", "path": "projects/ABC Example/notes/secret.md"},           # extra fields: dropped
    {"date": "2026-10-19", "saw": '=HYPERLINK("http://example.invalid") and "quotes", commas', "decided": "@watch it"},
]
CAPTURE = """(()=>{ window.__csv=[]; const mk=URL.createObjectURL.bind(URL);
  URL.createObjectURL=b=>{ window.__csv.push({blob:b}); return mk(b); };
  HTMLAnchorElement.prototype.click=function(){ const c=window.__csv[window.__csv.length-1]; if(c){ c.name=this.download; c.href=this.href; } };
  return true; })()"""
READ_CSV = "(async()=>{ const c=window.__csv[0]; return c?{name:c.name, type:c.blob.type, text:await c.blob.text(), n:window.__csv.length}:null; })()"


class ReviewsBase(LiveBrowserCase):
    width, height = 1400, 1000
    notes = NOTES

    @classmethod
    def load(cls, v):
        super().load(v)
        fx.write_jsonl(v.root / "system" / "staging" / "run-usage.jsonl", fx.RUNS)
        fx.write_jsonl(v.root / "system" / "staging" / "context-size.jsonl", fx.CONTEXT)
        if cls.notes:
            fx.write_jsonl(v.root / "system" / "staging" / "usage-reviews.jsonl", cls.notes)

    @classmethod
    def setUpClass(cls):
        cls._now = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = fx.NOW                 # the server's clock and the page's (live_browser pins the page from this)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if cls._now is None:
            os.environ.pop("CREAITE_NOW", None)
        else:
            os.environ["CREAITE_NOW"] = cls._now

    def open_usage(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("!!document.querySelector('#actTabU')")
        b.click("#actTabU")
        b.wait(f"!{PANEL}.hidden && !!document.querySelector('#uRevCsv')")
        return b


class ReviewsList(ReviewsBase):
    shared_server = True

    def test_the_list_is_newest_first_with_dates_shown(self):
        b = self.open_usage()
        self.assertIn("Your reviews", b.eval(f"{PANEL}.innerText"))
        self.assertEqual(b.eval(ROWS), [["19-10-2026", NOTES[1]["saw"], "@watch it"],
                                        ["12-10-2026", "Start load about 21,000 tokens a run", "Trim the rules file first"]])
        self.assertEqual(b.eval("[...document.querySelectorAll('#actUsage table[aria-label=\"Your reviews\"] thead th')].map(t=>t.textContent)"),
                         ["Date", "What you saw", "What you decided"])

    def test_other_fields_never_reach_the_page(self):
        b = self.open_usage()
        whole = b.eval("document.documentElement.outerHTML + JSON.stringify(D.usage)")
        for word in ("POISONED", "Jane Example", "secret.md"):
            self.assertNotIn(word, whole)
        self.assertEqual([sorted(r) for r in b.eval("D.usage.reviews")], [["date", "decided", "saw"]] * 2)

    def test_download_as_csv_is_the_notes_with_dates_shown_and_formulas_neutralised(self):
        b = self.open_usage()
        b.eval(CAPTURE)
        b.click("#uRevCsv")
        b.wait("window.__csv.length===1")
        got = b.eval(READ_CSV)
        self.assertEqual(got["name"], "2026-10-19 creaite usage reviews.csv")
        self.assertTrue(got["type"].startswith("text/csv"), got["type"])
        text = got["text"].lstrip("﻿")
        self.assertEqual(text, usage_reviews.csv_text(usage_reviews.load(self.v.root)))       # the page and the module agree
        self.assertEqual(text.split("\r\n")[1], "\"19-10-2026\",\"'=HYPERLINK(\"\"http://example.invalid\"\") and \"\"quotes\"\", commas\",\"'@watch it\"")
        self.assertNotIn("POISONED", got["text"])

    def test_the_section_fits_at_900_in_both_palettes_and_modes(self):
        b = self.open_usage()
        b.resize(900, 900)
        o = b.eval("""(()=>{ const out={};
          for(const pal of TEST_PALETTES) for(const mode of ["Light","Dark"]){ S.palette=pal; S.theme=mode; applyTheme();
            const t=document.querySelector('#actUsage table[aria-label="Your reviews"]'), btn=document.querySelector('#uRevCsv');
            out[pal+'|'+mode]={over:document.documentElement.scrollWidth>innerWidth, right:t.getBoundingClientRect().right<=innerWidth,
              ink:getComputedStyle(btn).color, bg:getComputedStyle(btn).backgroundColor}; }
          return out; })()""".replace("TEST_PALETTES", TEST_PALETTES_JS))
        for k, v in o.items():
            self.assertFalse(v["over"], k)
            self.assertTrue(v["right"], k)
            self.assertNotEqual(v["ink"], v["bg"], k)


class ReviewsEmpty(ReviewsBase):
    shared_server = True
    notes = []

    def test_no_notes_says_so_and_csv_is_held(self):
        b = self.open_usage()
        self.assertIn("No review notes yet.", b.eval(f"{PANEL}.innerText"))
        self.assertEqual(b.eval("document.querySelector('#uRevCsv').getAttribute('aria-disabled')"), "true")
        b.eval(CAPTURE)
        b.click("#uRevCsv")
        b.eval("new Promise(r=>setTimeout(r,300))")
        self.assertEqual(b.eval("window.__csv.length"), 0)


@unittest.skipIf(ROUTE_IN, "the route is in live_server.py: ReviewsSave covers saving")
class ReviewsHeld(ReviewsBase):
    """Before the guarded diff: the page says saving needs the next server update and never posts."""
    shared_server = True

    def test_add_is_held_with_the_reason_as_its_tooltip(self):
        b = self.open_usage()
        self.assertIs(b.eval("D.usage.reviews_save"), False)
        add = "document.querySelector('#uRevAdd')"
        self.assertEqual(b.eval(f"{add}.getAttribute('aria-disabled')"), "true")
        self.assertIn("next server update", b.eval(f"{add}.getAttribute('data-tip')"))
        b.eval("window.__posts=[]; const f=window.fetch; window.fetch=function(u,o){ if(o&&o.method==='POST'&&/usage/.test(String(u))) window.__posts.push(String(u)); return f.apply(this,arguments); }; true")
        b.click("#uRevAdd")
        b.eval("new Promise(r=>setTimeout(r,300))")
        self.assertFalse(b.eval("!!document.querySelector('#uRevForm')"))
        self.assertEqual(b.eval("window.__posts"), [])


class ReviewsSave(ReviewsBase):
    """With dev/proposals/usage-reviews/live_server.diff applied: the form saves through the route, token-checked."""
    notes = NOTES[:1]

    def post(self, body, token):
        req = urllib.request.Request(self.base + "/api/usage/review", data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **({"X-Creaite-Token": token} if token else {})})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    @until_applied
    def test_the_form_saves_one_note_through_the_route(self):
        b = self.open_usage()
        self.assertIs(b.eval("D.usage.reviews_save"), True)
        b.click("#uRevAdd")
        b.wait("!!document.querySelector('#uRevForm')")
        self.assertEqual(b.eval("document.querySelector('#uRevDate').value"), "19-10-2026")       # today, as shown
        self.assertEqual(b.eval("document.activeElement.id"), "uRevSaw")
        b.eval("""(()=>{ const set=(s,v)=>{ const e=document.querySelector(s); e.value=v; e.dispatchEvent(new Event('input',{bubbles:true})); };
          set('#uRevDate','18-10-2026'); set('#uRevSaw','Cost up 117% on last week\\nmostly the sweep'); set('#uRevDec','Move the sweep to 08:00'); return true; })()""")
        b.click("#uRevSave")
        b.wait("!document.querySelector('#uRevForm')")
        self.assertEqual(b.eval(ROWS)[0], ["18-10-2026", "Cost up 117% on last week mostly the sweep", "Move the sweep to 08:00"])
        lines = [json.loads(x) for x in (self.v.root / "system" / "staging" / "usage-reviews.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(lines[-1], {"date": "2026-10-18", "saw": "Cost up 117% on last week mostly the sweep", "decided": "Move the sweep to 08:00"})
        self.assertEqual(b.eval("document.activeElement.id"), "uRevAdd")
        b.reload("typeof go==='function' && LIVE")                       # kept: the page's next build reads the file
        b.eval("go('activity')")
        b.click("#actTabU")
        b.wait(f"{ROWS}.length===2")

    @until_applied
    def test_a_bad_date_is_said_and_nothing_is_saved(self):
        b = self.open_usage()
        b.click("#uRevAdd")
        b.wait("!!document.querySelector('#uRevForm')")
        b.eval("""(()=>{ const e=document.querySelector('#uRevDate'); e.value='31-02-2026'; e.dispatchEvent(new Event('input',{bubbles:true}));
          const s=document.querySelector('#uRevSaw'); s.value='x'; s.dispatchEvent(new Event('input',{bubbles:true})); return true; })()""")
        b.click("#uRevSave")
        b.wait("/DD-MM-YYYY/.test(document.querySelector('#uRevMsg').textContent)")
        self.assertEqual(len(usage_reviews.load(self.v.root)), 1)
        b.key("Escape")
        b.wait("!document.querySelector('#uRevForm')")

    @until_applied
    def test_the_route_needs_the_token_and_keeps_only_the_three_fields(self):
        token = self.b.eval("(go('activity'), D.token)")
        self.assertEqual(self.post({"date": "2026-10-19", "saw": "x"}, None)[0], 403)
        self.assertEqual(self.post({"date": "2026-10-19", "saw": "x"}, "wrong")[0], 403)
        self.assertEqual(len(usage_reviews.load(self.v.root)), 1)
        code, got = self.post({"date": "2026-10-19", "saw": "y" * 300, "decided": "Keep", "who": "Jane Example"}, token)
        self.assertEqual((code, got["ok"]), (200, True))
        self.assertEqual(got["reviews"][-1], {"date": "2026-10-19", "saw": "y" * 200, "decided": "Keep"})
        self.assertNotIn("Jane", (self.v.root / "system" / "staging" / "usage-reviews.jsonl").read_text(encoding="utf-8"))
        code, got = self.post({"date": "19-10-2026", "saw": "x"}, token)
        self.assertEqual((code, got["ok"]), (200, False))


if __name__ == "__main__":
    unittest.main()
