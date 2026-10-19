"""v2.5.0 race fix (independent review, HIGH): Match internal awaits the client gate's check (/api/report/match-check) and then copies into
the open client report. If another report was opened while the check was in flight, the first project's internal words were copied into
the second project's client report and saved, and every later gate judged them against the second project, so they passed. Real Chrome
on the real live server (no Claude runs); fictional words and projects only.

  the match is dropped when another project's report opens during the check ... Race.test_a_match_never_lands_in_another_project
  an edit on the same report during the combined check is kept ............... Race.test_an_edit_during_the_check_is_not_lost
  control: no switch, the clean section is copied ............................ Race.test_without_a_switch_the_clean_section_is_copied

Run: python3 dev/tests/test_match_internal_race.py      (Chrome tier; skipped without Chrome)
"""
import json
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_sbs_matchgate as M  # noqa: E402  (its fixture and helpers; its tests are not collected here)
from test_workstreams import add_project  # noqa: E402

INT, CLI, WEEK = M.INT, M.CLI, M.WEEK
WORD = "Zebracrossing"
# Delay the n-th call to /api/report/match-check (1 = the per-section check, 2 = the combined re-check) by `ms`.
DELAY = """((nth, ms)=>{const f=window.fetch.bind(window); let n=0; window.__mc=0; window.fetch=(u,o)=>{ if(String(u).endsWith('/api/report/match-check')){
  window.__mc++; if(++n===nth) return new Promise(r=>setTimeout(()=>r(f(u,o)),ms)); } return f(u,o); };})"""


class Race(M.Base):
    @classmethod
    def load(cls, v):
        M.H.R.populate(v)
        add_project(v, "DEF", "Quiet Project")
        v.run("init")

    def draft(self, code, kind="client"):
        return self.api("/api/report/draft", {"kind": kind, "code": code, "week_ending": WEEK})

    def type_internal(self, text):
        self.write(INT, " " + text)
        self.b.wait(f"document.querySelector({json.dumps(INT)}).innerText.includes({json.dumps(text.split()[0])})", 10)
        self.saved("weekly", has=text.split()[0])

    def test_a_match_never_lands_in_another_project(self):
        self.open_side()
        self.type_internal(f"{WORD} plan for the other client only.")
        self.q(DELAY + "(1, 4000)")
        self.q("document.querySelector('[data-crmatchall]').click()")
        self.b.wait("window.__mc===1", 10)
        self.q("(()=>{ const p=P.find(p=>p.code==='DEF'); if(p) p.cr=true; go('reporting','DEF'); })()")
        self.b.wait("location.hash.includes('DEF')", 10)
        self.b.wait(f"!!document.querySelector({json.dumps(CLI)})", 25)
        self.b.pump(6)                                           # the delayed check answers, and an autosave would have run
        self.assertIn("DEF", self.q("location.hash"))
        self.assertNotIn(WORD, self.q(f"(document.querySelector({json.dumps(CLI)})||{{innerText:''}}).innerText"), "DEF's client pane")
        d = self.draft("DEF")
        self.assertNotIn(WORD, json.dumps(d.get("doc")), "DEF's saved client draft")
        self.assertNotIn(WORD, self.staging_files_text(), "the client draft files in staging")
        self.assertNotIn(WORD, json.dumps(self.draft("ABC").get("doc")), "ABC's client draft: the dropped match copied nothing")
        # DEF's own exports: approve DEF's internal week, then export the client report in both formats
        w = self.draft("DEF", "weekly")["doc"]
        next(x for x in w["sections"] if x["id"] == "health")["text"] = "Quiet week."
        self.assertTrue(self.api("/api/report/save", {"doc": w, "base_version": w.get("version")}).get("ok"))
        self.api("/api/report/approve", {"kind": "weekly", "code": "DEF", "week_ending": WEEK, "force": True})
        for fmt in ("html", "docx"):
            r = self.api("/api/report/export", {"kind": "client", "code": "DEF", "week_ending": WEEK, "fmt": fmt, "on_clash": "number"})
            if not r.get("ok"):
                continue                                     # nothing written is clean too
            f = self.v.root / r["path"]
            b = f.read_bytes()
            if f.suffix == ".docx":
                with zipfile.ZipFile(f) as z:
                    b = z.read("word/document.xml")
            self.assertNotIn(WORD.encode(), b, f"DEF's {fmt} export")

    def client_text_sections(self):
        return self.q(f"[...document.querySelectorAll('{CLI} section[data-id]')].filter(s=>s.querySelector('.wr-rich.wr-edit, .sheet-ed')).map(s=>s.dataset.id)")

    def test_an_edit_during_the_check_is_not_lost(self):
        self.open_side()
        self.type_internal(M.CLEAN)
        other = "next_week"                                     # a plain text section of the client report, not the one matched
        self.q(DELAY + "(2, 4000)")                              # the combined re-check is slow
        self.q("document.querySelector('[data-crmatchall]').click()")
        self.b.wait("window.__mc===2", 15)
        self.write(CLI, " Yarrowfield note kept.", sec=other)    # Alan edits another section of the same report meanwhile
        self.b.pump(5.5)
        self.assertIn("Yarrowfield", self.text_of(CLI, other), "the edit made during the check is kept")
        self.assertIn("Quincebrook", self.text_of(CLI), "the clean section was still copied")
        doc = self.draft("ABC")["doc"]
        blob = json.dumps(doc)
        for _ in range(16):
            if "Yarrowfield" in blob and "Quincebrook" in blob:
                break
            self.b.pump(0.5)
            blob = json.dumps(self.draft("ABC")["doc"])
        self.assertIn("Yarrowfield", blob)
        self.assertIn("Quincebrook", blob)

    def test_without_a_switch_the_clean_section_is_copied(self):
        self.open_side()
        self.type_internal(M.CLEAN)
        self.q(DELAY + "(1, 1500)")
        self.q("document.querySelector('[data-crmatchall]').click()")
        self.b.wait(f"document.querySelector({json.dumps(CLI)}).innerText.includes('Quincebrook')", 15)


if __name__ == "__main__":
    unittest.main()
