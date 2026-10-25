"""#375 E1, slice S2: the invite fixtures (dev/tests/fixtures/invites/) run through S1's filter once it exists.

Run: python3 dev/tests/test_invite_fixtures_ready.py      (quick tier: plain code)

`system/scripts/invite_filter.py` is imported lazily; while it is missing every test is skipped ("invite_filter not built yet").
With it: for every fixture, lines = invite_blocks.to_lines(body); kept = invite_filter.keep_lines(lines); then
  * no planted secret appears in the kept text (substring, after removing zero-width characters from both sides);
  * every line of the fixture's `must_keep` list is among the kept lines;
  * kept is a subsequence of lines, and filtering twice changes nothing.
"""
import importlib
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
import invite_blocks as B  # noqa: E402

FIX = HERE / "fixtures" / "invites"
INVISIBLE = dict((ord(c), None) for c in "​‌‍⁠﻿­")


def load_filter():
    try:
        return importlib.import_module("invite_filter")
    except ImportError:
        return None


def read(path):
    with open(str(path), encoding="utf-8", newline="") as fh:
        return fh.read()


def cases():
    for meta in sorted(FIX.glob("*.json")):
        src = [p for p in FIX.glob(meta.stem + ".*") if p.suffix in (".html", ".txt")][0]
        yield meta.stem, read(src), json.loads(meta.read_text(encoding="utf-8"))


def subsequence(small, big):
    it = iter(big)
    return all(any(x == y for y in it) for x in small)


class FixturesThroughTheFilter(unittest.TestCase):
    def setUp(self):
        self.F = load_filter()
        if self.F is None or not hasattr(self.F, "keep_lines"):
            self.skipTest("invite_filter not built yet")

    def test_planted_secrets_are_removed(self):
        for name, body, meta in cases():
            kept = "\n".join(self.F.keep_lines(B.to_lines(body))).translate(INVISIBLE)
            for secret in meta["planted_secrets"]:
                with self.subTest(fixture=name, secret=secret):
                    self.assertNotIn(secret.translate(INVISIBLE), kept)

    def test_must_keep_lines_survive(self):
        for name, body, meta in cases():
            kept = self.F.keep_lines(B.to_lines(body))
            for line in meta["must_keep"]:
                with self.subTest(fixture=name, line=line):
                    self.assertIn(line, kept)

    def test_subset_and_idempotent(self):
        for name, body, _meta in cases():
            lines = B.to_lines(body)
            kept = self.F.keep_lines(lines)
            with self.subTest(fixture=name):
                self.assertTrue(subsequence(kept, lines))
                self.assertEqual(self.F.keep_lines(kept), kept)


if __name__ == "__main__":
    unittest.main()
