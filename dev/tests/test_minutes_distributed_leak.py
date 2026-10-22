"""v2.6.0 leak guard: a Sensitive item never reaches the Distributed version of minutes, whatever its Track choice.
Run: python3 dev/tests/test_minutes_distributed_leak.py      (quick tier: no Chrome)

The bug: followup_facts ran tracked_of (a draft's Track choices applied) before withheld, and a Sensitive decision left as a
line in the minutes only (Track neither, the decision default) lost its item in the copy, so withheld never saw the flag and the
line reached the Distributed follow-up email. Approved minutes had the same hole in the stored record (Approve minutes keeps the
line and drops the item), so the Distributed export (HTML, Word) leaked it too.
Fictional demo data; item 1 is a Sensitive action, item 4 a Sensitive decision, and the rest are not. Paths covered: followup_facts
(draft and filed, both versions), distributed_of, distributed_export (HTML and Word), and the Internal version, which keeps both
by design (it is marked internal).
"""
import json
import os
import sys
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_minutes_approve as ta  # noqa: E402
from test_minutes_approve import DRAFT, FILED, Base  # noqa: E402

SECRET = {"actions": "Book the UAT environment", "decisions": "Go-live stays on 20 November"}
OPEN = "Share the training schedule"
N = {"actions": 1, "decisions": 4}
CASES = [(kind, choice) for kind in ("actions", "decisions") for choice in ("y", "n", "")]


class Sensitive(Base):
    def setUp(self):
        orig = ta.spec

        def flagged():
            s = orig()
            for i, it in enumerate(s["items"], 1):
                if i in (1, 4):
                    it["flags"] = ["sensitive"]
            s["items"].insert(0, {"table": "actions", "due_words": "Friday", "values": {
                "project": "ABC", "description": OPEN + " with the team", "owner": "Omar Ali"}})
            return s
        # the extra open action goes last so the numbers above stay put
        def spec():
            s = flagged()
            extra = s["items"].pop(0)
            s["items"].append(extra)
            return s
        ta.spec = spec
        try:
            super().setUp()
        finally:
            ta.spec = orig

    def track(self, kind, choice):
        n = N[kind]
        other = N["decisions" if kind == "actions" else "actions"]
        self.js("import creaite_doc, minutes_record\n"
                f"d = creaite_doc.read({DRAFT!r}); d.setdefault('layout', {{}})['track'] = {{{str(n)!r}: {choice!r}}}\n"
                f"r = minutes_record.save_page({DRAFT!r}, d); print(json.dumps(r['ok']))")
        return other

    def facts(self, version, path=DRAFT):
        return self.js(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({path!r}, {version!r})))")

    def test_the_draft_follow_up_never_holds_a_sensitive_item_when_distributed(self):
        for kind, choice in CASES:
            with self.subTest(kind=kind, track={"y": "ticked", "n": "crossed", "": "neither"}[choice]):
                self.track(kind, choice)
                f = self.facts("distributed")
                text = json.dumps(f, ensure_ascii=False)
                for s in SECRET.values():
                    self.assertNotIn(s, text, "no Sensitive item or line in the Distributed follow-up")
                self.assertTrue(any(OPEN in i["t"] for i in f["items"]), "the unmarked action is there")

    def test_the_internal_follow_up_keeps_both_sensitive_items_and_says_internal(self):
        f = self.facts("internal")
        self.assertTrue(f["marked_internal"])
        words = [i["t"] for i in f["items"]]
        for s in SECRET.values():
            self.assertIn(s, words, "Internal keeps a Sensitive item (only Distributed withholds)")
        for kind, choice in (("decisions", ""), ("decisions", "y"), ("actions", "")):
            self.track(kind, choice)
            self.assertIn(SECRET[kind], [i["t"] for i in self.facts("internal")["items"]], f"{kind}/{choice!r} kept in Internal")
        self.track("decisions", "n")
        self.assertNotIn(SECRET["decisions"], [i["t"] for i in self.facts("internal")["items"]], "crossed is out of Internal too")

    def test_distributed_of_a_draft_and_the_withheld_list_name_the_kept_line(self):
        self.track("decisions", "")
        out = self.js("import minutes_record\n"
                      f"from minutes_record import tracked_of, withheld, distributed_of\nimport creaite_doc\n"
                      f"d = tracked_of(creaite_doc.read({DRAFT!r}))\nh = withheld(d)\n"
                      "print(json.dumps({'held': h, 'dist': json.dumps(distributed_of(d, h))}))")
        self.assertIn("@4", out["held"], "the kept Sensitive line is withheld after tracked_of")
        self.assertNotIn(SECRET["decisions"], out["dist"])

    def test_a_kept_line_whose_sensitivity_was_not_recorded_is_withheld(self):
        """Fail closed: an older record's kept line has no `held` mark, so Distributed leaves it out."""
        self.track("decisions", "")
        out = self.js("import minutes_record\nimport creaite_doc\n"
                      f"d = minutes_record.tracked_of(creaite_doc.read({DRAFT!r}))\n"
                      "for rec in d['meta']['removed'].values(): rec.pop('held', None)\n"
                      "h = minutes_record.withheld(d)\n"
                      "print(json.dumps({'h': h, 'dist': json.dumps(minutes_record.distributed_of(d, h))}))")
        self.assertEqual(out["h"].get("@4"), "Sensitivity unknown")
        self.assertNotIn(SECRET["decisions"], out["dist"])

    def approved(self, kind, choice):
        self.track(kind, choice)
        r = self.js(f"import review\nprint(json.dumps(review.approve_minutes({self.name!r}, True, [])))")
        self.assertTrue(r["ok"], r)

    def test_filed_minutes_distributed_export_and_follow_up_hold_no_sensitive_item(self):
        for kind, choice in CASES:
            with self.subTest(kind=kind, track={"y": "ticked", "n": "crossed", "": "neither"}[choice]):
                self.tearDown()
                self.setUp()
                if choice == "y" and kind == "decisions":
                    self.track(kind, choice)
                    r = self.js(f"import review\nprint(json.dumps(review.approve_minutes({self.name!r}, True, [4])))")
                    self.assertTrue(r["ok"], r)
                else:
                    self.approved(kind, choice)
                f = self.facts("distributed", FILED)
                self.assertNotIn(SECRET[kind], json.dumps(f, ensure_ascii=False), "follow-up from the filed minutes")
                for fmt in ("html", "docx"):
                    r = self.js("import minutes_record\n"
                                f"print(json.dumps(minutes_record.export({FILED!r}, {fmt!r}, False, 'distributed')))")
                    self.assertTrue(r["ok"], r)
                    made = self.v.root / r["path"]
                    text = made.read_text(encoding="utf-8") if fmt == "html" else \
                        zipfile.ZipFile(made).read("word/document.xml").decode("utf-8")
                    self.assertNotIn(SECRET[kind], text, f"{fmt}: the Distributed export")
                    self.assertIn(OPEN, text, f"{fmt}: the unmarked action is there")


if __name__ == "__main__":
    unittest.main()
