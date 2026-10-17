"""#197 run usage monitor, plain code: usage_log.py appends counts-only lines, usage_report.py sums them. Fixed dates only.

Run: python3 dev/tests/test_run_usage.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import usage_log  # noqa: E402
import usage_report  # noqa: E402

RESULT = {"type": "result", "subtype": "success", "result": "SECRET REPLY TEXT about Jane Doe", "num_turns": 3, "duration_ms": 4200,
          "total_cost_usd": 0.0102529, "usage": {"input_tokens": 2, "output_tokens": 40, "cache_read_input_tokens": 649,
                                                  "cache_creation_input_tokens": 2536},
          "modelUsage": {"claude-sonnet-5-5": {"costUSD": 0.01}}}
ASSISTANT = {"type": "assistant", "message": {"usage": {"input_tokens": 2, "cache_read_input_tokens": 649, "cache_creation_input_tokens": 2536}}}


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.file = self.root / "system" / "staging" / "run-usage.jsonl"
        os.environ["CREAITE_NOW"] = "2026-10-12 09:30"

    def tearDown(self):
        os.environ.pop("CREAITE_NOW", None)
        self.t.cleanup()

    def lines(self):
        return [json.loads(x) for x in self.file.read_text().splitlines()]


class UsageLog(Base):
    def test_run_usage_line_has_counts_only(self):
        usage_log.record("ask", RESULT, label="Chat", start_tokens=usage_log.start_tokens_of(ASSISTANT), seconds=4.2, root=self.root)
        (ln,) = self.lines()
        self.assertEqual(ln, {"at": "2026-10-12T09:30:00", "kind": "ask", "label": "Chat", "model": "claude-sonnet-5-5", "seconds": 4.2,
                              "turns": 3, "input": 2, "output": 40, "cache_read": 649, "cache_create": 2536, "cost_usd": 0.010253,
                              "start_tokens": 3187, "stopped": False, "skills": []})

    def test_run_usage_appended_for_each_kind(self):
        for k in usage_log.KINDS:
            usage_log.record(k, RESULT, root=self.root)
        self.assertEqual([x["kind"] for x in self.lines()], list(usage_log.KINDS))

    def test_stopped_run_still_recorded(self):
        usage_log.record("sweep", None, seconds=12, stopped=True, root=self.root)
        (ln,) = self.lines()
        self.assertTrue(ln["stopped"])
        self.assertEqual((ln["input"], ln["cost_usd"], ln["seconds"]), (0, 0.0, 12.0))

    def test_vip_cost_and_tokens_recorded(self):
        vip = {"type": "result", "result": "text", "total_cost_usd": 0.02, "num_turns": 2, "duration_ms": 3000,
               "usage": {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 0}}
        usage_log.record("vip", vip, root=self.root)
        (ln,) = self.lines()
        self.assertEqual((ln["kind"], ln["input"], ln["cache_read"], ln["cost_usd"], ln["seconds"]), ("vip", 10, 100, 0.02, 3.0))

    def test_no_text_in_the_file(self):
        usage_log.record("ask", RESULT, root=self.root)
        raw = self.file.read_text()
        self.assertNotIn("SECRET", raw)
        self.assertNotIn("Jane", raw)

    def test_not_written_in_the_dev_repo(self):
        (self.root / ".creaite-dev").write_text("")
        self.assertIsNone(usage_log.record("ask", RESULT, root=self.root))
        self.assertFalse(self.file.exists())

    def test_model_of_init_event(self):
        self.assertEqual(usage_log.model_of({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5"}), "claude-sonnet-5-5")


SKILL_EVENT = {"type": "assistant", "message": {"content": [
    {"type": "text", "text": "ok"},
    {"type": "tool_use", "name": "Skill", "input": {"skill": "cx-minutes", "args": "SECRET ARGS about Jane Doe"}},
    {"type": "tool_use", "name": "Skill", "input": {"skill": "cx-minutes"}},
    {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
    {"type": "tool_use", "name": "Skill", "input": {"skill": "cx-review"}}]}}


class Skills(Base):
    def test_skills_recorded_from_skill_tool_calls(self):
        self.assertEqual(usage_log.skills_of(SKILL_EVENT), ["cx-minutes", "cx-review"])
        usage_log.record("ask", RESULT, root=self.root, skills=usage_log.skills_of(SKILL_EVENT))
        self.assertEqual(self.lines()[0]["skills"], ["cx-minutes", "cx-review"])
        self.assertNotIn("SECRET", self.file.read_text())
        self.assertNotIn("Jane", self.file.read_text())

    def test_skills_of_none_and_malformed(self):
        self.assertEqual(usage_log.skills_of({"type": "assistant", "message": {"content": [{"type": "text", "text": "x"}]}}), [])
        for bad in (None, 5, "x", {}, {"message": None}, {"message": {"content": 7}}, {"message": {"content": [None, 3, {"name": "Skill"},
                    {"type": "tool_use", "name": "Skill", "input": None}, {"type": "tool_use", "name": "Skill", "input": {"skill": 4}}]}}):
            self.assertEqual(usage_log.skills_of(bad), [])
        usage_log.record("ask", RESULT, root=self.root)
        self.assertEqual(self.lines()[0]["skills"], [])

    def ev(self, *names, key="skill"):
        return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill", "input": {key: n}} for n in names]}}

    def test_free_text_skill_names_never_reach_the_line(self):
        typed = ["Meeting notes about Jane Doe and her pay", "projects/ABC Secret/documents/plan.docx", "../../etc/passwd",
                 "jane-doe-salary", "evil:Jane Doe", "Evil:cx-minutes", "jane-doe:salary", "x" * 500]
        got = usage_log.skills_of(self.ev(*typed, "cx-minutes"))
        self.assertEqual(got, ["cx-minutes", "other"])
        usage_log.record("ask", RESULT, root=self.root, skills=typed + ["cx-review"])
        text = self.file.read_text()
        for bad in ("Jane", "Secret", "passwd", "salary", "xxxx", "plan.docx"):
            self.assertNotIn(bad, text)
        self.assertEqual(self.lines()[0]["skills"], ["cx-review", "other"])

    def test_known_skill_names_are_kept(self):
        self.assertEqual(usage_log.skills_of(self.ev("cx-sweep", "cx-prep", "docx", "document-skills:xlsx", "creaite:cx-edit")),
                         ["cx-sweep", "cx-prep", "docx", "document-skills:xlsx", "creaite:cx-edit"])

    def test_name_is_the_fallback_key(self):
        self.assertEqual(usage_log.skills_of(self.ev("cx-edit", key="name")), ["cx-edit"])
        self.assertEqual(usage_log.skills_of(self.ev("Jane Doe's pay", key="name")), ["other"])

    def test_skill_list_is_capped_at_twenty(self):
        d = self.root / "skills"
        for i in range(30):
            (d / f"s{i:02d}").mkdir(parents=True)
        names = [f"s{i:02d}" for i in range(30)]
        got = usage_log.skills_of(self.ev(*names), skills_dir=d)
        self.assertEqual(got, names[:19] + ["other"])
        self.assertEqual(usage_log.clean_skills(names[:20], d), names[:20])      # exactly twenty: no change
        self.assertEqual(usage_log.clean_skills(names[:20] + ["free text"], d), names[:19] + ["other"])
        usage_log.record("ask", RESULT, root=self.root, skills=[f"free text {i}" for i in range(500)])      # a 500-name list
        self.assertEqual(self.lines()[0]["skills"], ["other"])

    def test_report_lists_days_since_a_skill_last_ran(self):
        skills = self.root / ".claude" / "skills"
        for n in ("cx-minutes", "cx-review", "cx-prep", "other"):
            (skills / n).mkdir(parents=True)
        rows = [{"at": "2026-10-02T08:00:00", "kind": "ask", "skills": ["cx-minutes"]},
                {"at": "2026-10-11T08:00:00", "kind": "ask", "skills": ["cx-minutes", "cx-review"]},
                {"at": "2026-10-09T08:00:00", "kind": "ask"}]        # an old line without the key
        t = {s["skill"]: s for s in usage_report.skills_table(rows, days=7, skills_dir=skills)}
        self.assertEqual((t["cx-minutes"]["runs"], t["cx-minutes"]["ever"], t["cx-minutes"]["days_since"]), (1, 2, 1))
        self.assertEqual(t["cx-review"]["days_since"], 1)
        self.assertEqual((t["cx-prep"]["runs"], t["cx-prep"]["days_since"]), (0, None))
        self.assertNotIn("other", t)
        self.assertEqual(usage_report.skills_table(rows, days=1, skills_dir=skills)[-1]["skill"], "cx-prep")


class UsageReport(Base):
    def test_report_sums_by_day_and_kind(self):
        rows = [{"at": "2026-10-12T08:00:00", "kind": "ask", "input": 1, "output": 9, "cache_read": 90, "cache_create": 0, "cost_usd": 0.1, "start_tokens": 40},
                {"at": "2026-10-12T09:00:00", "kind": "ask", "input": 1, "output": 9, "cache_read": 190, "cache_create": 0, "cost_usd": 0.2, "start_tokens": 80},
                {"at": "2026-10-11T09:00:00", "kind": "sweep", "input": 5, "output": 5, "cache_read": 0, "cache_create": 0, "cost_usd": 0.5, "start_tokens": 5},
                {"at": "2026-09-01T09:00:00", "kind": "ask", "input": 1, "output": 1, "cache_read": 0, "cache_create": 0, "cost_usd": 9, "start_tokens": 1}]
        out = usage_report.summarise(rows, days=7)
        self.assertEqual([(s["day"], s["kind"], s["runs"]) for s in out], [("2026-10-12", "ask", 2), ("2026-10-11", "sweep", 1)])
        a = out[0]
        self.assertEqual((a["tokens"], a["avg_tokens"], a["cost_usd"], a["start_min"], a["start_median"], a["start_max"]), (300, 150, 0.3, 40, 60, 80))
        self.assertEqual(a["start_share"], round(120 / 282, 2))


if __name__ == "__main__":
    unittest.main()
