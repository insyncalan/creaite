"""#238 usage and context monitor, plain code: usage_log.measure / append / read / changes (the daily context-size record).

Counts only, never text: a row is {date, file, bytes, tokens}, `file` one of four fixed words. Estimated tokens are bytes / 4.

Run: python3 dev/tests/test_usage_log.py     (quick tier: no Chrome, no vault)
"""
import json
import os
import signal
import stat
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import usage_log  # noqa: E402
import usage_report  # noqa: E402
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


class Alarm(unittest.TestCase):
    """A hang fails the test (SIGALRM) instead of blocking the run."""

    def setUp(self):
        def boom(*_):
            raise AssertionError("measure hung: it opened something that never answers")
        self._old = signal.signal(signal.SIGALRM, boom)
        signal.setitimer(signal.ITIMER_REAL, 15, 3)        # repeats: code that swallows the first alarm (daily) can't hang the suite
        self.addCleanup(lambda: (signal.setitimer(signal.ITIMER_REAL, 0), signal.signal(signal.SIGALRM, self._old)))
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = make_vault(Path(self.t.name))

    def rows(self):
        return {r["file"]: r for r in usage_log.measure(self.root, today="2026-10-19")}


class Hardened(Alarm):
    """Every file measure reads is a regular file, sized by stat, never read whole; anything else counts 0."""

    def test_a_fifo_named_skill_md_does_not_hang(self):
        d = self.root / ".claude" / "skills" / "cx-fifo"
        d.mkdir(parents=True)
        os.mkfifo(d / "SKILL.md")
        self.assertGreater(self.rows()["skills"]["bytes"], 100)        # the three real skills still count

    def test_a_fifo_named_like_a_counted_file_counts_zero(self):
        (self.root / "CLAUDE.md").unlink()
        os.mkfifo(self.root / "CLAUDE.md")
        (self.root / "system" / "creaite-rules.md").unlink()
        os.mkfifo(self.root / "system" / "creaite-rules.md")
        r = self.rows()
        self.assertEqual((r["claude_md"]["bytes"], r["rules"]["bytes"]), (0, 0))

    def test_a_sparse_gigabyte_skill_md_is_read_only_up_to_the_bound(self):
        d = self.root / ".claude" / "skills" / "cx-big"
        d.mkdir(parents=True)
        with open(d / "SKILL.md", "wb") as f:
            f.write(b"---\nname: cx-big\n")
            f.truncate(10 ** 9)                                         # sparse: no closing line within the bound
        read, real = [], os.read

        def counting(fd, n):
            data = real(fd, n)
            read.append(len(data))
            return data
        with mock.patch.object(usage_log.os, "read", counting):
            self.rows()
        self.assertLessEqual(sum(read), usage_log.FRONT_MAX * 4)       # the three real skills and this one: a few KB each at most
        self.assertLessEqual(max(read), usage_log.FRONT_MAX)
        self.assertEqual(usage_log._front_matter_size(d / "SKILL.md"), 0)

    def test_a_symlink_loop_counts_zero(self):
        a, b = self.root / "CLAUDE.md", self.root / "loop"
        a.unlink()
        os.symlink(b, a)
        os.symlink(a, b)
        d = self.root / ".claude" / "skills" / "cx-loop"
        d.mkdir(parents=True)
        os.symlink(d / "SKILL.md", d / "SKILL.md")
        self.assertEqual(self.rows()["claude_md"]["bytes"], 0)

    def test_a_symlink_is_followed_only_to_a_regular_file_inside_the_vault(self):
        inside = self.root / "real-rules.md"
        inside.write_text("R" * 1234)
        outside = Path(self.t.name + "-outside.md")
        outside.write_text("O" * 999)
        self.addCleanup(outside.unlink)
        rules = self.root / "system" / "creaite-rules.md"
        rules.unlink()
        os.symlink(inside, rules)
        self.assertEqual(self.rows()["rules"]["bytes"], 1234)
        rules.unlink()
        os.symlink(outside, rules)
        self.assertEqual(self.rows()["rules"]["bytes"], 0)
        rules.unlink()
        os.symlink(self.root / "projects", rules)                         # a folder
        self.assertEqual(self.rows()["rules"]["bytes"], 0)

    def test_a_directory_named_like_a_file_counts_zero(self):
        (self.root / "CLAUDE.md").unlink()
        (self.root / "CLAUDE.md").mkdir()
        self.assertEqual(self.rows()["claude_md"]["bytes"], 0)

    def test_the_front_matter_is_still_measured(self):
        d = self.root / ".claude" / "skills" / "cx-one"
        d.mkdir(parents=True)
        text = "---\nname: cx-one\ndescription: Short.\n---\n\nbody"
        (d / "SKILL.md").write_text(text)
        self.assertEqual(usage_log._front_matter_size(d / "SKILL.md"), len("---\nname: cx-one\ndescription: Short.\n---"))


class RecordFiles(Alarm):
    """#238 review: the two record files (run-usage.jsonl, context-size.jsonl) are read bounded, as regular files only, per line."""

    GOOD = '{"date":"2026-10-19","file":"%s","bytes":5,"tokens":1}\n'
    RUN = '{"at":"2026-10-19T09:00:00","kind":"ask","cost_usd":0.5}\n'

    def setUp(self):
        super().setUp()
        self.ctx = self.root / "system" / "staging" / "context-size.jsonl"
        self.run = self.root / "system" / "staging" / "run-usage.jsonl"

    def test_a_fifo_reads_as_empty_and_never_hangs(self):
        os.mkfifo(self.ctx)
        os.mkfifo(self.run)
        self.assertEqual(usage_log.read(self.ctx), [])
        self.assertEqual(usage_report.load(self.run), [])
        self.assertEqual(usage_log.read_lines(self.ctx), [])

    def test_daily_and_append_leave_a_fifo_alone(self):
        import time
        os.mkfifo(self.ctx)
        t0 = time.monotonic()
        self.addCleanup(lambda: self.assertLess(time.monotonic() - t0, 5, "append or daily waited on the FIFO"))      # the alarm is swallowed inside
        self.assertEqual(usage_log.append([{"date": "2026-10-19", "file": "rules", "bytes": 5, "tokens": 1}], root=self.root), 0)
        self.assertEqual(usage_log.daily(root=self.root, today="2026-10-19"), [])

    def test_a_directory_or_a_link_reads_as_empty(self):
        self.ctx.mkdir()
        self.assertEqual(usage_log.read(self.ctx), [])
        real = self.root / "real.jsonl"
        real.write_text(self.RUN)
        os.symlink(real, self.run)
        self.assertEqual(usage_report.load(self.run), [])

    def _sparse(self, f, head, tail, size):
        with open(f, "wb") as fh:
            fh.write(head)
            fh.truncate(size)                       # sparse: the middle is nothing but zeros
        with open(f, "ab") as fh:
            fh.write(b"\n" + tail)                  # the zeros end the way a cut line would; the recent lines follow

    def test_a_huge_sparse_file_is_read_only_up_to_the_cap_and_keeps_the_recent_lines(self):
        import tracemalloc
        cap = 1024 * 1024
        self._sparse(self.run, self.RUN.encode(), (self.RUN.replace("0.5", "0.7") * 3).encode(), 300 * 10 ** 6)
        self._sparse(self.ctx, (self.GOOD % "rules").encode(), (self.GOOD % "memory").encode(), 300 * 10 ** 6)
        read, real = [], os.pread

        def counting(fd, n, off):
            data = real(fd, n, off)
            read.append(len(data))
            return data
        tracemalloc.start()
        try:
            with mock.patch.object(usage_log, "MAX_READ", cap), mock.patch.object(usage_log.os, "pread", counting):
                runs, ctx = usage_report.load(self.run), usage_log.read(self.ctx)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertEqual([r["cost_usd"] for r in runs], [0.7] * 3)          # the old line is beyond the cap, the recent ones survive
        self.assertEqual([r["file"] for r in ctx], ["memory"])
        self.assertLessEqual(sum(read), 2 * cap)
        self.assertLess(peak, 20 * cap)

    def test_the_cap_is_documented_and_sane(self):
        self.assertTrue(1024 * 1024 <= usage_log.MAX_READ <= 64 * 1024 * 1024)

    def test_one_bad_byte_loses_only_its_own_line(self):
        self.ctx.write_bytes(b"\xff\n" + (self.GOOD % "rules").encode() + b'{"date":"2026-10-19","file":"memory","bytes":5,"tokens":1,"x":"\xff"}\n')
        self.run.write_bytes(b"\xff\n" + self.RUN.encode() + b"\xfe\xfd\n" + self.RUN.encode())
        self.assertEqual([r["file"] for r in usage_log.read(self.ctx)], ["rules", "memory"])
        self.assertEqual(len(usage_report.load(self.run)), 2)

    def test_daily_does_not_append_again_when_the_file_holds_a_bad_byte(self):
        body = b"\xff\n" + "".join(self.GOOD % f for f in ("rules", "claude_md", "memory", "skills")).encode()
        self.ctx.write_bytes(body)
        for _ in range(2):
            self.assertEqual(usage_log.daily(root=self.root, today="2026-10-19"), [])
        self.assertEqual(self.ctx.read_bytes(), body)


class Review(Alarm):
    """#238 review: a link to the outside, a link as a skill folder, a huge cost and a future date."""

    def skills_bytes(self):
        return self.rows()["skills"]["bytes"]

    def test_a_skill_md_that_links_outside_the_vault_counts_zero(self):
        base = self.skills_bytes()
        outside = Path(self.t.name + "-outside.md")
        outside.write_text("---\nname: cx-out\ndescription: " + "x" * 200 + "\n---\n")
        self.addCleanup(outside.unlink)
        d = self.root / ".claude" / "skills" / "cx-link"
        d.mkdir(parents=True)
        os.symlink(outside, d / "SKILL.md")
        self.assertEqual(usage_log._front_matter_size(d / "SKILL.md", self.root), 0)
        self.assertEqual(self.skills_bytes(), base)

    def test_a_skill_folder_that_is_a_link_is_not_followed(self):
        base = self.skills_bytes()
        out = Path(self.t.name + "-outdir")
        out.mkdir()
        self.addCleanup(lambda: [p.unlink() for p in out.iterdir()] and out.rmdir() or (out.exists() and out.rmdir()))
        (out / "SKILL.md").write_text("---\nname: cx-out\ndescription: " + "x" * 200 + "\n---\n")
        skills = self.root / ".claude" / "skills"
        os.symlink(out, skills / "outdir")                         # leaves the vault
        os.symlink(skills / "cx-edit", skills / "cx-inside")       # stays in the vault, still a link
        self.assertEqual(self.skills_bytes(), base)

    def test_a_huge_finite_cost_is_clamped(self):
        self.assertEqual(usage_log._money(1e300), float(usage_log.MAX_COUNT))
        self.assertEqual(usage_log._money(-1e300), 0.0)
        line = usage_log.line_for("ask", {"total_cost_usd": 1e300})
        self.assertEqual(line["cost_usd"], float(usage_log.MAX_COUNT))

    def test_days_since_is_never_negative_for_a_future_line(self):
        rows = [{"at": "2026-10-25T09:00:00", "kind": "ask", "skills": ["cx-edit"]}]
        t = usage_report.skills_table(rows, days=7, today=__import__("datetime").date(2026, 10, 19), skills_dir=self.root / ".claude" / "skills")
        self.assertEqual({s["skill"]: s["days_since"] for s in t}["cx-edit"], 0)


class Rows(unittest.TestCase):
    """Rows read back are real: ASCII dates that exist, finite bounded integers."""

    def clean(self, **kw):
        return usage_log._clean_row(dict({"date": "2026-10-19", "file": "rules", "bytes": 5, "tokens": 1}, **kw))

    def test_dates_must_be_real_ascii_iso_dates(self):
        for bad in ("9999-99-99", "2026-13-01", "2026-02-30", "\u0662\u0660\u0662\u0666-\u0661\u0660-\u0661\u0669", "2026-10-19 ", "2026-1-9", "", None, 20261019):
            self.assertIsNone(self.clean(date=bad), repr(bad))
        self.assertIsNotNone(self.clean(date="2026-02-28"))

    def test_numbers_must_be_bounded_integers(self):
        for bad in (10 ** 30, -1, 1.5, float("inf"), float("nan"), True, "5", None, usage_log.MAX_COUNT + 1):
            self.assertIsNone(self.clean(bytes=bad), repr(bad))
            self.assertIsNone(self.clean(tokens=bad), repr(bad))
        self.assertIsNotNone(self.clean(bytes=usage_log.MAX_COUNT))

    def test_a_file_with_such_rows_reads_the_good_ones(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        f = Path(t.name) / "c.jsonl"
        f.write_text('{"date":"2026-10-19","file":"rules","bytes":1e999,"tokens":1}\n'
                     '{"date":"9999-99-99","file":"rules","bytes":5,"tokens":1}\n'
                     '{"date":"2026-10-19","file":"rules","bytes":NaN,"tokens":1}\n'
                     '{"date":"2026-10-19","file":"rules","bytes":5,"tokens":1}\n')
        self.assertEqual(usage_log.read(f), [{"date": "2026-10-19", "file": "rules", "bytes": 5, "tokens": 1}])


class Daily(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = make_vault(Path(self.t.name))
        self.file = self.root / "system" / "staging" / "context-size.jsonl"

    def test_the_file_is_created_private(self):
        usage_log.daily(root=self.root, today="2026-10-19")
        self.assertEqual(stat.S_IMODE(self.file.stat().st_mode), 0o600)

    def test_when_todays_rows_exist_nothing_is_measured_or_read(self):
        usage_log.daily(root=self.root, today="2026-10-19")
        with mock.patch.object(usage_log, "measure", wraps=usage_log.measure) as m, mock.patch.object(usage_log, "_size", wraps=usage_log._size) as sz:
            self.assertEqual(usage_log.daily(root=self.root, today="2026-10-19"), [])
        self.assertEqual((m.call_count, sz.call_count), (0, 0))         # not measured, no file touched

    def test_a_truncated_last_line_does_not_swallow_the_next_row(self):
        self.file.write_text('{"date":"2026-10-18","file":"rules","bytes":5,"tokens":1}\n{"date":"2026-10-18","file":"cla')
        usage_log.append([{"date": "2026-10-19", "file": "rules", "bytes": 7, "tokens": 2}], root=self.root)
        got = usage_log.read(self.file)
        self.assertEqual([(r["date"], r["bytes"]) for r in got], [("2026-10-18", 5), ("2026-10-19", 7)])


if __name__ == "__main__":
    unittest.main()
