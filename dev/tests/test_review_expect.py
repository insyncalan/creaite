"""2.6.2 (#314): review.py `approve|reject|keep|override N --expect <fp>`: act only if item N is still the item the caller meant.

The fingerprint is the page's (build_dashboard.item_fp, 12 hex). The change is the shared-engine diff
dev/proposals/review-expect/review.py.diff; until it is applied to this tree the throwaway vault copy gets it (git apply to the
copy only), so the same checks pass both ways. Cases: a match is decided (and only that item); a mismatch is refused in one plain line,
exit 2, nothing decided; an item taken out and renumbered (the page's number now names another item); a number that is not in the
list; two identical items (position decides: each is its own number); a bad fingerprint; both argument forms; calls without --expect
unchanged. Mutant: the comparison removed, and the mismatch check goes red.

Run: python3 dev/tests/test_review_expect.py
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
from test_tracker import Vault  # noqa: E402
import build_dashboard  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "dev/proposals/review-expect/review.py.diff"
HAS = "_main_with_expect" in (ROOT / "system/scripts/review.py").read_text()


def item(n, text):
    return {"n": n, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
            "values": {"project": "ABC", "description": text, "owner": "Alan Carter", "due_date": "2027-01-15",
                       "source": "projects/ABC Example/minutes/2026-10-01 Steering.docx — Actions"}}


class Base(unittest.TestCase):
    mutate = False

    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.v.run("init")
        if not HAS:
            subprocess.run(["git", "init", "-q", str(self.v.root)], check=True)
            subprocess.run(["git", "apply", str(PROPOSAL)], cwd=self.v.root, check=True)
        if self.mutate:
            f = self.v.root / "system/scripts/review.py"
            t = f.read_text()
            old = ") != want:"
            assert old in t
            f.write_text(t.replace(old, ") == '':", 1))
        self.name = self.v.propose("2026-10-21-0900-x", [item(1, "Alpha item"), item(2, "Bravo item"), item(3, "Charlie item")]).name

    def listing(self):
        return json.loads(self.v.run("list", "--json", script="review.py").stdout)

    def number(self, ref):
        return next(r["n"] for r in self.listing() if r["file"] == self.name and r["ref"] == ref)

    def fp(self, ref):
        data = json.loads((self.v.root / "system/staging" / self.name).read_text())
        return build_dashboard.item_fp(next(i for i in data["items"] if i["n"] == ref))

    def decisions(self):
        data = json.loads((self.v.root / "system/staging" / self.name).read_text())
        return {i["n"]: i["decision"] for i in data["items"]}

    def review(self, *args):
        r = self.v.run(*args, script="review.py", ok=False)
        return r.returncode, r.stdout + r.stderr


class Expect(Base):
    def test_a_match_is_decided_and_only_that_item(self):
        n, fp = self.number(2), self.fp(2)
        code, out = self.review("approve", str(n), f"--expect={fp}")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.decisions(), {1: "pending", 2: "approved", 3: "pending"})

    def test_a_mismatch_is_refused_in_one_plain_line(self):
        n, other = self.number(2), self.fp(1)
        for cmd in ("approve", "reject"):
            code, out = self.review(cmd, str(n), "--expect", other)
            self.assertEqual(code, 2, out)
            self.assertIn("has changed since you looked at it", out)
            self.assertNotIn("Traceback", out)
        self.assertEqual(self.decisions(), {1: "pending", 2: "pending", 3: "pending"})

    def test_renumbered_under_the_caller(self):
        """The page looked at Bravo (number 2); Alpha is taken out; number 2 is now Charlie."""
        n, bravo = self.number(2), self.fp(2)
        p = self.v.root / "system/staging" / self.name
        data = json.loads(p.read_text())
        data["items"] = [i for i in data["items"] if i["values"]["description"] != "Alpha item"]
        for k, it in enumerate(data["items"], 1):
            it["n"] = k
        p.write_text(json.dumps(data))
        code, out = self.review("reject", str(n), f"--expect={bravo}")
        self.assertEqual(code, 2, out)
        self.assertEqual(self.decisions(), {1: "pending", 2: "pending"})

    def test_a_missing_number_or_applied_item(self):
        self.listing()
        code, out = self.review("approve", "99", f"--expect={self.fp(1)}")
        self.assertEqual(code, 2, out)
        self.assertIn("isn't in the last review", out)
        p = self.v.root / "system/staging" / self.name
        data = json.loads(p.read_text())
        data["items"][0]["applied"] = True
        p.write_text(json.dumps(data))
        code, out = self.review("approve", "1", f"--expect={'0' * 12}")
        self.assertEqual(code, 2, out)
        self.assertEqual({k: v for k, v in self.decisions().items() if k != 1}, {2: "pending", 3: "pending"})

    def test_two_identical_items_are_told_apart_by_position(self):
        self.name = self.v.propose("2026-10-21-0905-y", [item(1, "Twin item"), item(2, "Twin item")]).name
        n1, n2, fp = self.number(1), self.number(2), self.fp(1)
        self.assertEqual(fp, self.fp(2))
        code, out = self.review("approve", str(n2), f"--expect={fp}")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.decisions(), {1: "pending", 2: "approved"})
        self.assertNotEqual(n1, n2)

    def test_a_bad_fingerprint_or_shape_is_refused(self):
        n = self.number(1)
        for args in ((str(n), "--expect=zzz"), (str(n), "--expect"), (str(n), "--expect", "ABCDEF123456"), (f"{n},{n + 1}", f"--expect={self.fp(1)}"),
                     (f"--expect={self.fp(1)}",)):
            code, out = self.review("approve", *args)
            self.assertEqual(code, 2, (args, out))
            self.assertIn("--expect goes with", out)
        code, out = self.review("list-all", f"--expect={self.fp(1)}")
        self.assertNotEqual(code, 0)
        self.assertEqual(self.decisions(), {1: "pending", 2: "pending", 3: "pending"})

    def test_a_block_taken_out_under_the_caller_is_a_mismatch_not_a_traceback(self):
        """Cap's note 3: a writer that doesn't take the server's lock removes the `meeting` block between the list and the decision;
        the answer is the same plain line (exit 2), never a traceback or a path."""
        self.name = self.v.propose("2026-10-21-0910-z", [item(1, "Delta item")], meeting={"title": "Steering", "date": "2026-10-01",
                                   "projects": ["ABC"], "draft": "projects/ABC Example/minutes/2026-10-01 Steering.docx"}).name
        n = self.number("meeting")
        fp = build_dashboard.block_fp(json.loads((self.v.root / "system/staging" / self.name).read_text())["meeting"])
        p = self.v.root / "system/staging" / self.name
        data = json.loads(p.read_text())
        del data["meeting"]
        p.write_text(json.dumps(data))
        for cmd in ("approve", "reject"):
            code, out = self.review(cmd, str(n), f"--expect={fp}")
            self.assertEqual(code, 2, out)
            self.assertIn("has changed since you looked at it", out)
            self.assertNotIn("Traceback", out)
            self.assertNotIn(str(self.v.root), out)

    def test_without_expect_nothing_changes(self):
        code, out = self.review("approve", str(self.number(3)))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.decisions(), {1: "pending", 2: "pending", 3: "approved"})


class Mutant(Base):
    mutate = True

    def test_without_the_comparison_a_mismatch_goes_through(self):
        n, other = self.number(2), self.fp(1)
        code, _ = self.review("approve", str(n), f"--expect={other}")
        self.assertEqual(code, 0, "the mutant must act on the wrong item, so the real mismatch test would go red")
        self.assertEqual(self.decisions()[2], "approved")


if __name__ == "__main__":
    unittest.main(verbosity=1)
