"""#90 (v2.1.0): POST /api/draft takes the kinds "report-section" and "minutes-section" through the real live server and the run engine
(a stand-in Claude, drafts_fake.py: no model). The stream carries the sources, then one "draft" event that names the section it was
asked for; nothing is written; the offered count is the server's, counts only.

Run: python3 dev/tests/test_drafts_report_route.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drafts_fake  # noqa: E402
from test_drafts_update import DraftCase  # noqa: E402

WEEKLY = {"kind": "report-section", "report": "weekly", "code": "ABC", "section": "this_week", "heading": "This week",
          "text": "The wave plan holds.", "action": "shorter",
          "document": {"kind": "weekly", "code": "ABC", "week_ending": ""}}      # #127: the report the section is in


class Route(DraftCase):
    def test_a_weekly_section_is_drafted_and_names_its_section(self):
        reply, events = self.draft(WEEKLY)
        self.assertIsNone(reply, reply)
        src = next(e for e in events if e["type"] == "sources")
        self.assertEqual(src["draft_kind"], "report-section")
        d = next(e for e in events if e["type"] == "draft")
        self.assertTrue(d["ok"])
        self.assertEqual(d["section"], "this_week")
        self.assertEqual(d["action"], "shorter")
        self.assertTrue(d["text"].startswith("A fresh draft of the section"))
        # #90 review F5: the reply's checks come back with it, for the page to show
        self.assertIsInstance(d.get("notes"), list)
        self.assertTrue(d.get("sentences") and all("unsourced" in x for x in d["sentences"]), d)
        p = drafts_fake.prompt(self.fake)
        self.assertIn("The wave plan holds.", p)
        self.assertIn("shorter, about half", p)
        self.assertEqual(self.stats()["report-section"]["offered"], 1)
        raw = (self.v.root / "system/staging/draft-stats.json").read_text(encoding="utf-8")
        self.assertNotIn("fresh draft", raw)

    def test_nothing_is_asked_when_the_request_is_refused_and_a_kind_is_still_checked(self):
        reply, _ = self.draft({**WEEKLY, "action": "custom"})                       # no instruction
        self.assertFalse(reply["ok"] and not reply.get("message"))
        self.assertIn("Say what you want", reply["message"])
        reply, _ = self.draft({"kind": "poem"})
        self.assertIn("Not a kind", reply["message"])

    def test_the_stat_route_counts_used_and_rejected_for_both_kinds(self):
        for feature in ("report-section", "minutes-section"):
            for event in ("used", "rejected"):
                got = self.b.eval("""(async()=>{ const r=await fetch('/api/draft/stat',{method:'POST',headers:{'Content-Type':'application/json','X-Creaite-Token':D.token},
                    body:JSON.stringify({feature:%s,event:%s})}); return r.json(); })()""" % (json.dumps(feature), json.dumps(event)))
                self.assertTrue(got["ok"], got)
        s = self.stats()
        self.assertEqual((s["report-section"]["used"], s["minutes-section"]["rejected"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
