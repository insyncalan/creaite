"""#375 E1: the production default is composition D (scrub_raw_first), never the E1-only strict mode.

invite_filter.filter_text (anchors + shape gate with second_layer, no scrub) is a TEST mode on the trunk. Every production path
(calendar_gateway.read / clean_row / filter_body, the sweep's stamping, the start-up rescrub) must run filter_text_with_scrub with its
default order, composition D. Run: python3 dev/tests/test_e1_default_is_d.py   (quick tier)
"""
import re
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import calendar_gateway as G  # noqa: E402
import invite_filter as F  # noqa: E402

BODY = "Agenda\n1. Budget review\n2. Risks\nSecret word: swordfish\nPasscode 4417 for the room\nThanks"


class DefaultIsD(unittest.TestCase):
    def setUp(self):
        G.clear_cache()

    def test_defaults(self):
        self.assertEqual(F.DEFAULT_ORDER, "scrub_raw_first")
        self.assertIsNone(G.FILTER)                       # no hook installed: the lazy default is used
        self.assertEqual(F.filter_text_with_scrub(BODY), F.filter_text_with_scrub(BODY, order="scrub_raw_first"))

    def test_gateway_default_filter_is_d_not_strict(self):
        d = F.filter_text_with_scrub(BODY, order="scrub_raw_first")
        strict = F.filter_text(BODY)
        self.assertNotEqual(d, strict)                    # the sample tells them apart: strict keeps the labelled secret
        self.assertIn("swordfish", strict)
        self.assertNotIn("swordfish", d)
        self.assertEqual(G.filter_body(BODY), d)
        self.assertEqual(G._filter_fn()(BODY), d)

    def test_clean_row_uses_d(self):
        row = G.clean_row({"id": "a", "start": "09:00", "end": "10:00", "title": "Review", "sensitivity": "normal", "body": BODY})
        self.assertEqual(row["body"], F.filter_text_with_scrub(BODY, order="scrub_raw_first"))
        self.assertNotIn("swordfish", row["body"])
        self.assertNotIn("4417", row["body"])

    def test_production_code_never_uses_the_strict_paths(self):
        """No script outside invite_filter calls filter_text or keep_lines/keep_indices, or passes second_layer, extras or an order."""
        bad = []
        for f in sorted(SCRIPTS.glob("*.py")):
            if f.name == "invite_filter.py":
                continue
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("#")[0]
                if re.search(r"invite_filter\.(filter_text|keep_lines|keep_indices)\b|\bsecond_layer\s*=|\bextras\s*=\s*False|\border\s*=\s*[\"']", code):
                    bad.append("%s:%d %s" % (f.name, n, line.strip()[:100]))
        self.assertEqual(bad, [])


class SweepRowsAreWellFormed(unittest.TestCase):
    def test_organiser_flag_is_kept_and_a_sweep_row_is_well_formed(self):
        """The sweep writes organiser as a flag (True or False); the gateway must treat that row as well formed and keep the flag."""
        row = {"id": "a", "start": "09:00", "end": "10:00", "all_day": False, "title": "Review", "where": "", "teams": False,
               "private": False, "organiser": True, "sensitivity": "normal", "body": "Hello", "clean": G.CLEAN}
        self.assertTrue(G._well_formed(row))
        self.assertIs(G.view(row, "day")["organiser"], True)
        for org in (False, "Mia Hale"):                    # the other two forms the sweep writes
            self.assertTrue(G._well_formed({**row, "organiser": org}))
            self.assertEqual(G.view({**row, "organiser": org}, "day")["organiser"], org)
        self.assertFalse(G._well_formed({**row, "organiser": 3}))


if __name__ == "__main__":
    unittest.main()
