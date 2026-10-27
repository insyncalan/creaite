"""#375 option (c), order of the layers (2.6.9): filter_text_with_scrub(order="anchors_first"|"scrub_first"|"scrub_raw_first"). Pins, for BOTH orders:
the output is a subsequence of the converted lines (blank lines aside), idempotence on the fuzz corpus (8 generators x PER bodies, seed
369; FUZZ_FULL=1 for 25,000 each), the fixtures' planted secrets gone and their must_keep lines kept (with the one documented window loss
in anchors_first), the default, and an unknown order refused. Fictional data only."""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "scripts"))
sys.path.insert(0, str(ROOT / "dev" / "tests"))
import invite_blocks as B  # noqa: E402
import invite_filter as F  # noqa: E402
import test_invite_clean_fuzz_html as Z  # noqa: E402

FIX = ROOT / "dev" / "tests" / "fixtures" / "invites"
PER = 5000 if os.environ.get("FUZZ_FULL") != "1" else 25000
# lines the scrub's label window removes in anchors_first (a label whose value the anchor layer already dropped)
WINDOW_LOSS = {"anchors_first": {"label_same_cell_br": ("Room 204", "Notes are kept on the team page.")}, "scrub_first": {}, "scrub_raw_first": {}}
# the scrub reads the raw body, so its lines are not invite_blocks' lines: no subset check, and it keeps what the scrub alone keeps
RAW = "scrub_raw_first"


def fixtures():
    for j in sorted(FIX.glob("*.json")):
        meta = json.loads(j.read_text())
        src = [p for p in (j.with_suffix(".html"), j.with_suffix(".txt")) if p.exists()]
        if src:
            yield j.stem, src[0].read_text(), meta


def converted(body):
    return B.to_lines(body) if B.looks_like_html(body) else body.replace("\r\n", "\n").replace("\r", "\n").split("\n")


class Order(unittest.TestCase):
    def test_default_is_one_of_the_orders(self):
        self.assertIn(F.DEFAULT_ORDER, F.ORDERS)
        self.assertEqual(set(F.ORDERS), {"anchors_first", "scrub_first", "scrub_raw_first"})

    def test_unknown_order_refused(self):
        with self.assertRaises(ValueError):
            F.filter_text_with_scrub("a\nb", order="parallel")

    def test_default_equals_named_default(self):
        for _, body, _ in fixtures():
            self.assertEqual(F.filter_text_with_scrub(body), F.filter_text_with_scrub(body, order=F.DEFAULT_ORDER))

    def test_fixtures_secrets_gone_and_must_keep(self):
        for order in F.ORDERS:
            n = 0
            for name, body, meta in fixtures():
                out = F.filter_text_with_scrub(body, order=order)
                lines = out.split("\n")
                for s in meta.get("planted_secrets", []):
                    self.assertNotIn(s, out, (order, name))
                for ln in meta.get("must_keep", []):
                    if order == RAW:
                        continue
                    if ln in WINDOW_LOSS[order].get(name, ()):
                        continue
                    n += 1
                    self.assertIn(ln, lines, (order, name))
            self.assertGreater(n, 50 if order != RAW else -1)

    def test_subset_and_idempotence_on_the_fuzz_corpus(self):
        for order in F.ORDERS:
            bodies = 0
            for name, gen in Z.GENERATORS:
                for body, _ in Z.cases(name, gen, PER):
                    bodies += 1
                    conv = set(converted(body))
                    once = F.filter_text_with_scrub(body, order=order)
                    for ln in once.split("\n") if order != RAW else ():
                        self.assertTrue(ln == "" or ln in conv, (order, name, ln))
                    self.assertEqual(F.filter_text_with_scrub(once, order=order), once, (order, name, body))
            self.assertEqual(bodies, 8 * PER)

    def test_blank_lines_tidy_in_scrub_first(self):
        out = F.filter_text_with_scrub("Budget review\n\nTeams PIN\nOther\n60967443\n\nNotes", order="scrub_first")
        self.assertNotIn("\n\n\n", out)
        self.assertFalse(out.startswith("\n") or out.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
