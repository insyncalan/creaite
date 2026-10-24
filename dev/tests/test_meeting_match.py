"""#328: the calendar meeting matcher (meeting_match.py).

Run: python3 dev/tests/test_meeting_match.py   (no browser, no model)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
import meeting_match as mm  # noqa: E402


def row(code, name, **kw):
    base = {"code": code, "name": name, "aliases": [], "people": [], "domains": [], "channels": [], "keywords": [],
            "senders": [], "exclude": []}
    return {**base, **kw}


ROWS = [row("ABC", "Harbour Upgrade", aliases=["harbour"], domains=["harbourco.example"], keywords=["quay", "berth"],
            people=["Mia Hale"], senders=["mia@harbourco.example"], exclude=["canteen"]),
        row("DEF", "Orchard Rollout", domains=["orchard.example", "partner.example"], keywords=["crate", "grove"]),
        row("GHI", "Meadow Review", domains=["partner.example"])]


def m(title, att=(), **kw):
    return mm.match_meeting(title, [{"email": a, "name": "Someone"} for a in att], ROWS, **kw)


class Matcher(unittest.TestCase):
    def test_code_and_name_in_title_match(self):
        self.assertEqual((m("[ABC] Weekly sync")["p"], m("[ABC] Weekly sync")["level"]), ("ABC", "matched"))
        self.assertEqual(m("Orchard Rollout steering")["level"], "matched")

    def test_one_keyword_is_unsure(self):
        r = m("Quay inspection")
        self.assertEqual((r["p"], r["level"], r["cands"]), (None, "unsure", ["ABC"]))

    def test_two_keywords_likely(self):
        r = m("Quay and berth plan")
        self.assertEqual((r["p"], r["level"]), ("ABC", "likely"))

    def test_attendee_domain_likely_never_matched(self):
        r = m("Catch-up", ["sam@orchard.example"])
        self.assertEqual((r["p"], r["level"]), ("DEF", "likely"))

    def test_listed_sender_likely(self):
        self.assertEqual(m("Catch-up", ["mia@harbourco.example"])["p"], "ABC")

    def test_own_domain_never_counts(self):
        rows = [row("ABC", "Harbour Upgrade", domains=["mine.example"], senders=["me@mine.example"])]
        r = mm.match_meeting("Catch-up", [{"email": "me@mine.example"}], rows, own_domains=["mine.example"])
        self.assertEqual(r["level"], "unsure")

    def test_shared_domain_is_no_evidence(self):
        r = m("Catch-up", ["x@partner.example"])
        self.assertEqual((r["p"], r["level"], r["cands"]), (None, "unsure", []))

    def test_conflict_between_title_and_people(self):
        r = m("[ABC] Sync", ["x@orchard.example"])
        self.assertEqual(r["p"], "ABC")              # a code is strong; a medium signal elsewhere does not overrule it
        r = m("Quay and berth plan", ["x@orchard.example"])
        self.assertEqual((r["p"], r["level"], r["cands"]), (None, "unsure", ["ABC", "DEF"]))

    def test_exclude_word_rules_out(self):
        self.assertNotEqual(m("[ABC] Canteen review")["p"], "ABC")

    def test_code_beats_remembered_series(self):          # Cap H1
        r = m("[DEF] Weekly sync", remembered_code="ABC")
        self.assertEqual((r["p"], r["level"], r["cands"]), (None, "unsure", ["ABC", "DEF"]))
        self.assertEqual(m("Weekly sync", remembered_code="ABC")["level"], "matched")
        self.assertEqual(m("[ABC] Weekly sync", remembered_code="ABC")["p"], "ABC")

    def test_names_alone_are_no_evidence(self):           # Cap M3: addresses only
        r = mm.match_meeting("Catch-up", [{"name": "Mia Hale", "email": ""}], ROWS)
        self.assertEqual(r["level"], "unsure")

    def test_confidential_uses_title_only(self):
        r = m("Catch-up", ["sam@orchard.example"], confidential=True)
        self.assertEqual(r["level"], "unsure")

    def test_reason_names_no_address_or_domain(self):
        for r in (m("Catch-up", ["sam@orchard.example"]), m("[ABC] x", ["mia@harbourco.example"]),
                  m("Quay and berth plan", ["x@orchard.example"])):
            self.assertNotIn("@", r["reason"])
            self.assertNotIn("example", r["reason"])

    def test_candidates_at_most_three(self):
        rows = [row(c, c + " thing", keywords=["zed"]) for c in ("AAA", "BBB", "CCC", "DDD")]
        self.assertEqual(len(mm.match_meeting("zed", [], rows)["cands"]), 3)

    def test_no_vip_word(self):
        self.assertNotIn("vip", open(mm.__file__).read().lower())



class PrepMatchH1(unittest.TestCase):
    """Cap H1: in build_dashboard.prep_match a code in the title beats the remembered series."""

    def test_code_beats_memory(self):
        import build_dashboard as bd
        projects = [{"code": "ABC", "name": "Harbour Upgrade"}, {"code": "DEF", "name": "Orchard Rollout"}]
        mem = {"weekly sync": "ABC"}
        self.assertEqual(bd.prep_match("[DEF] Weekly sync", projects, mem), (None, "unsure"))
        self.assertEqual(bd.prep_match("[ABC] Weekly sync", projects, mem), ("ABC", "remembered"))
        self.assertEqual(bd.prep_match("Weekly sync", projects, mem), ("ABC", "remembered"))


if __name__ == "__main__":
    unittest.main()
