"""#238 usage and context monitor, plain code: usage_log.measure / append / read / changes (the daily context-size record).

Counts only, never text: a row is {date, file, bytes, tokens}, `file` one of four fixed words. Estimated tokens are bytes / 4.

Run: python3 dev/tests/test_usage_log.py     (quick tier: no Chrome, no vault)
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import usage_log  # noqa: E402
from usage_fixture import CONTEXT, POISON  # noqa: E402

ALLOWED = {"date", "file", "bytes", "tokens"}
FILES = {"rules", "claude_md", "memory", "skills"}


def make_vault(root: Path, secret="SECRET TEXT about Jane Example"):
    """A throwaway vault: the rules, CLAUDE.md, two projects with memory, the portfolio files and three skills."""
    (root / "system" / "staging").mkdir(parents=True)
    (root / "system" / "creaite-rules.md").write_text("R" * 4000 + secret)
    (root / "CLAUDE.md").write_text("C" * 400)
    for name, size in (("ABC Example Programme", 1000), ("DEF Sample Rollout", 500)):
        (root / "projects" / name).mkdir(parents=True)
        (root / "projects" / name / "CLAUDE.md").write_text("M" * size + secret)
        (root / "projects" / name / "notes.md").write_text("not always loaded " * 100)      # not counted
    pf = root / "projects" / "_portfolio"
    pf.mkdir(parents=True)
    (pf / "PORTFOLIO.md").write_text("P" * 300)
    (pf / "project-register.md").write_text("G" * 200)
    (pf / "people-register.md").write_text("E" * 100)
    for n, desc in (("cx-minutes", "Turns transcripts into minutes."), ("cx-sweep", "Searches mail."), ("cx-edit", "Changes items.")):
        d = root / ".claude" / "skills" / n
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"---\nname: {n}\ndescription: {desc}\n---\n\n# {n}\n" + ("body " * 2000))     # the body is not always loaded
    return root


class Measure(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = make_vault(Path(self.t.name))

    def tearDown(self):
        self.t.cleanup()

    def rows(self):
        return {r["file"]: r for r in usage_log.measure(self.root, today="2026-10-19")}

    def test_four_fixed_files_with_bytes_tokens_and_date(self):
        r = self.rows()
        self.assertEqual(set(r), FILES)
        self.assertEqual(r["rules"]["bytes"], 4000 + len("SECRET TEXT about Jane Example"))
        self.assertEqual(r["claude_md"]["bytes"], 400)
        self.assertEqual({x["date"] for x in r.values()}, {"2026-10-19"})

    def test_tokens_are_bytes_over_four(self):
        for x in self.rows().values():
            self.assertEqual(x["tokens"], (x["bytes"] + 2) // 4)         # bytes / 4, halves up
        self.assertEqual(usage_log.estimate_tokens(0), 0)
        self.assertEqual(usage_log.estimate_tokens(4000), 1000)
        self.assertEqual(usage_log.estimate_tokens(4001), 1000)
        self.assertEqual(usage_log.estimate_tokens(4002), 1001)

    def test_memory_is_project_memory_and_the_registers_only(self):
        secret = len("SECRET TEXT about Jane Example")
        self.assertEqual(self.rows()["memory"]["bytes"], (1000 + secret) + (500 + secret) + 300 + 200 + 100)

    def test_skills_are_names_and_descriptions_not_the_bodies(self):
        b = self.rows()["skills"]["bytes"]
        self.assertGreater(b, 100)
        self.assertLess(b, 400)            # three front matters, not the 30 KB of bodies

    def test_a_missing_file_counts_zero_and_a_missing_folder_does_not_raise(self):
        (self.root / "CLAUDE.md").unlink()
        import shutil
        shutil.rmtree(self.root / ".claude")
        r = self.rows()
        self.assertEqual((r["claude_md"]["bytes"], r["skills"]["bytes"]), (0, 0))

    def test_no_text_is_ever_in_a_row(self):
        raw = json.dumps(usage_log.measure(self.root, today="2026-10-19"))
        for word in ("SECRET", "Jane", "Example", "ABC", "Sample Rollout", "cx-minutes", "Turns transcripts"):
            self.assertNotIn(word, raw)
        for r in usage_log.measure(self.root, today="2026-10-19"):
            self.assertEqual(set(r), ALLOWED)
            self.assertIn(r["file"], FILES)
            self.assertIsInstance(r["bytes"], int)
            self.assertIsInstance(r["tokens"], int)


class AppendRead(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.file = self.root / "system" / "staging" / "context-size.jsonl"
        self.rows = [{"date": "2026-10-19", "file": f, "bytes": 400, "tokens": 100} for f in ("rules", "claude_md")]

    def tearDown(self):
        self.t.cleanup()

    def test_append_writes_one_line_a_row_and_read_gives_them_back(self):
        self.assertEqual(usage_log.append(self.rows, root=self.root), 2)
        self.assertEqual(len(self.file.read_text().splitlines()), 2)
        self.assertEqual(usage_log.read(self.file), self.rows)

    def test_a_second_append_the_same_day_adds_nothing(self):
        usage_log.append(self.rows, root=self.root)
        self.assertEqual(usage_log.append(self.rows, root=self.root), 0)
        self.assertEqual(len(usage_log.read(self.file)), 2)
        later = [dict(self.rows[0], date="2026-10-20", bytes=800, tokens=200)]
        self.assertEqual(usage_log.append(later, root=self.root), 1)
        self.assertEqual(len(usage_log.read(self.file)), 3)

    def test_a_missing_file_reads_as_empty(self):
        self.assertEqual(usage_log.read(self.file), [])

    def test_a_corrupt_line_is_skipped(self):
        self.file.parent.mkdir(parents=True)
        good = json.dumps(self.rows[0])
        self.file.write_text("not json at all\n" + good + "\n{\"date\": \n[1,2]\n\n" + json.dumps(self.rows[1]) + "\n")
        self.assertEqual(usage_log.read(self.file), self.rows)

    def test_a_row_with_text_or_an_unknown_file_is_dropped_or_cleaned(self):
        self.file.parent.mkdir(parents=True)
        bad = [dict(self.rows[0], note=POISON),                                   # an extra key: removed
               dict(self.rows[1], file="projects/ABC Example Programme/CLAUDE.md"),      # a name: the row is dropped
               dict(self.rows[0], bytes="lots"), dict(self.rows[0], date="yesterday"), dict(self.rows[0], bytes=-5)]
        self.file.write_text("".join(json.dumps(b) + "\n" for b in bad))
        got = usage_log.read(self.file)
        self.assertEqual(got, [self.rows[0]])
        self.assertNotIn("POISON", json.dumps(got))

    def test_append_refuses_text_in_a_row(self):
        usage_log.append([dict(self.rows[0], note=POISON), dict(self.rows[1], file="Jane Example")], root=self.root)
        raw = self.file.read_text()
        self.assertNotIn("POISON", raw)
        self.assertNotIn("Jane", raw)
        self.assertEqual({tuple(sorted(json.loads(x))) for x in raw.splitlines()}, {tuple(sorted(ALLOWED))})

    def test_not_written_in_the_dev_repo(self):
        (self.root / ".creaite-dev").write_text("")
        self.assertEqual(usage_log.append(self.rows, root=self.root), 0)
        self.assertFalse(self.file.exists())

    def test_daily_measures_and_appends_once_a_day_and_never_raises(self):
        make_vault(self.root)
        first = usage_log.daily(root=self.root, today="2026-10-19")
        self.assertEqual(len(first), 4)
        self.assertEqual(usage_log.daily(root=self.root, today="2026-10-19"), [])         # the same day: nothing more
        self.assertEqual(len(usage_log.daily(root=self.root, today="2026-10-20")), 4)
        self.assertEqual(len(usage_log.read(self.file)), 8)
        self.assertEqual(usage_log.daily(root=self.root / "nowhere", today="2026-10-19"), [])


class Change(unittest.TestCase):
    def by(self, rows, today="2026-10-19"):
        return {c["file"]: c for c in usage_log.changes(rows, today=today)}

    def test_thirty_day_change_uses_the_latest_row_on_or_before_thirty_days_ago(self):
        c = self.by(CONTEXT)["rules"]
        self.assertEqual((c["bytes"], c["tokens"], c["date"]), (53000, 13250, "2026-10-19"))
        self.assertEqual((c["change_bytes"], c["change_tokens"], c["since"]), (3000, 750, "2026-09-19"))

    def test_without_a_row_that_old_the_oldest_row_in_the_window_is_the_baseline(self):
        c = self.by(CONTEXT)["claude_md"]
        self.assertEqual((c["change_bytes"], c["since"]), (0, "2026-10-12"))

    def test_a_single_row_has_no_earlier_measure(self):
        for f in ("memory", "skills"):
            c = self.by(CONTEXT)[f]
            self.assertIsNone(c["change_bytes"])
            self.assertIsNone(c["since"])

    def test_empty_gives_nothing_and_order_is_the_fixed_one(self):
        self.assertEqual(usage_log.changes([], today="2026-10-19"), [])
        self.assertEqual([c["file"] for c in usage_log.changes(CONTEXT, today="2026-10-19")], ["rules", "claude_md", "memory", "skills"])

    def test_a_shrink_is_negative(self):
        rows = [{"date": "2026-10-01", "file": "rules", "bytes": 53000, "tokens": 13250},
                {"date": "2026-10-19", "file": "rules", "bytes": 40000, "tokens": 10000}]
        self.assertEqual(self.by(rows)["rules"]["change_bytes"], -13000)


if __name__ == "__main__":
    unittest.main()
