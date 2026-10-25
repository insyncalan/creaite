"""#328 security review (2.6.7, Wanda on #353): the matcher and the learn offer fail closed. Each fix is pinned with a mutant: the
same check run on the source with the fix removed must fail.

Run: python3 dev/tests/test_328_security.py   (no browser, no model)
M1: a remembered series never overrides attendees who point to another project; the Not sure buttons say a pick is kept for every
    meeting with this title.  M2: a public mail provider (and its sub-domains), a value with , ; ( or a space, and an unset own
    domain are never offered or learnt.  LOW: Process all ready treats a calendar row with no level as needing a project.
"""
import sys
import tempfile
import types
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system/scripts"))
import mail_domains as md  # noqa: E402
import meeting_match as mm  # noqa: E402


def row(code, name, **kw):
    b = {"code": code, "name": name, "aliases": [], "people": [], "domains": [], "channels": [], "keywords": [], "senders": [],
         "exclude": []}
    return {**b, **kw}


ROWS = [row("ABC", "Harbour Upgrade", domains=["harbourco.example"]), row("DEF", "Orchard Rollout", domains=["delta.example"])]


def mutant(path, old, new):
    """A module built from `path`'s source with `old` replaced by `new` (it must be there)."""
    src = Path(path).read_text()
    assert old in src, old
    mod = types.ModuleType("mutant_" + Path(path).stem)
    mod.__file__ = str(path)
    exec(compile(src.replace(old, new, 1), str(path), "exec"), mod.__dict__)
    return mod


class SeriesVsAttendees(unittest.TestCase):
    ATT = [{"email": "a@delta.example"}]

    def test_series_does_not_override_attendees_for_another_project(self):
        r = mm.match_meeting("Weekly sync", self.ATT, ROWS, "ABC")
        self.assertEqual((r["p"], r["level"], r["cands"]), (None, "unsure", ["ABC", "DEF"]))

    def test_series_alone_or_with_its_own_attendees_still_matches(self):
        self.assertEqual(mm.match_meeting("Weekly sync", [], ROWS, "ABC")["level"], "matched")
        self.assertEqual(mm.match_meeting("Weekly sync", [{"email": "a@harbourco.example"}], ROWS, "ABC")["p"], "ABC")

    def test_mutant_without_the_rule_leaks(self):
        m = mutant(mm.__file__, "if mem and set(medium) - {mem}:", "if False:")
        self.assertEqual(m.match_meeting("Weekly sync", self.ATT, ROWS, "ABC")["p"], "ABC")        # the leak the fix closes

    def test_intake_row_does_not_keep_the_remembered_project(self):
        import build_dashboard as bd
        import capture
        orig = capture.register
        capture.register = lambda: {"projects": ROWS, "shared": set()}
        try:
            projects = [{"code": "ABC", "name": "Harbour Upgrade"}, {"code": "DEF", "name": "Orchard Rollout"}]
            ev = {"title": "Weekly sync", "attendees": self.ATT}
            code, how, _ = bd._inbox_match("Weekly sync", ev, False, False, projects, {"weekly sync": "ABC"})
            self.assertEqual((code, how), (None, "unsure"))                      # Process on the row would otherwise send ABC
            code, how, _ = bd._inbox_match("Weekly sync", {"title": "x"}, False, False, projects, {"weekly sync": "ABC"})
            self.assertEqual((code, how), ("ABC", "remembered"))
        finally:
            capture.register = orig


class Wording(unittest.TestCase):
    rows = (REPO / "system/templates/dashboard/src/components/intakeReview/rows.jsx").read_text()

    def test_buttons_say_a_pick_is_kept_for_the_title(self):
        self.assertIn("Your pick is kept for every meeting with this title.", self.rows)
        self.assertIn("for every meeting with this title`}", self.rows)
        built = (REPO / "system/templates/dashboard.html").read_text()
        self.assertIn("Your pick is kept for every meeting with this title.", built)

    def test_what_the_click_does_is_what_the_words_say(self):
        acts = (REPO / "system/templates/dashboard/src/components/intakeReview/actions.js").read_text()
        body = acts.split("export async function irChooseProject")[1].split("/** Yes to the offer")[0]
        self.assertIn("[m.series]: code", body)                                  # keyed by the title's series, so every meeting with that title
        self.assertIn('"prep.series"', body)


class PublicMail(unittest.TestCase):
    def test_public_providers_and_subdomains(self):
        for d in ("gmail.com", "mail.yahoo.co.uk", "x.y.gmail.com", "hotmail.co.uk", "hotmail.fr", "gmx.de", "mx.gmx.net", "Outlook.com"):
            self.assertTrue(md.is_public_mail(d), d)
        for d in ("client.example", "notgmail.com", "gmail.com.evil.example", "yahoo.example"):
            self.assertFalse(md.is_public_mail(d), d)

    def test_domain_shape(self):
        for d in ("evil.com,gmail.com", "a.com;b.com", "a.com (x)", "a b.com", "nodot", "", "-a.com", "a" * 130 + ".com"):
            self.assertFalse(md.valid_domain(d), d)
        self.assertTrue(md.valid_domain("client-one.example"))

    def test_offer_refuses_them(self):
        att = lambda *a: [{"email": x} for x in a]                                  # noqa: E731
        own = ["mine.example"]
        self.assertIsNone(mm.offer_signal(att("b@mail.yahoo.co.uk", "c@x.hotmail.co.uk"), ROWS, own))
        self.assertIsNone(mm.offer_signal(att("a@evil.com,gmail.com"), ROWS, own))
        self.assertIsNone(mm.offer_signal(att("a@new.example"), ROWS, []), "nothing while own domains are not set")
        self.assertEqual(mm.offer_signal(att("a@new.example"), ROWS, own), {"kind": "domain", "value": "new.example"})

    def test_mutants_for_the_offer(self):
        m = mutant(mm.__file__, "and not mail_domains.is_public_mail(d)", "")
        self.assertEqual(m.offer_signal([{"email": "b@mail.yahoo.co.uk"}], ROWS, ["mine.example"])["value"], "mail.yahoo.co.uk")
        m = mutant(mm.__file__, "if confidential or not own:", "if confidential:")
        self.assertIsNotNone(m.offer_signal([{"email": "a@mine.example2"}], ROWS, []))


class LearnCheck(unittest.TestCase):
    def setUp(self):
        import paths
        import propose
        self.propose, self.paths = propose, paths
        text = (REPO / "projects/_portfolio/project-register.md").read_text()
        self.tmp = Path(tempfile.mkdtemp()) / "register.md"
        self.tmp.write_text(text)
        self.orig = (paths.REGISTER, propose.own_domains)
        paths.REGISTER = self.tmp
        propose.own_domains = lambda: ["mine.example"]

    def tearDown(self):
        self.paths.REGISTER, self.propose.own_domains = self.orig

    def test_refused(self):
        for v in ("mail.yahoo.co.uk", "x.gmail.com", "evil.com,gmail.com", "a.com;b.com", "a.com (x)", "gmail.com"):
            r = self.propose.learn_check("ABC", "domain", v)
            self.assertFalse(r["ok"], v)
        self.assertTrue(self.propose.learn_check("ABC", "domain", "newclient.example")["ok"])

    def test_a_listed_sender_at_a_public_provider_is_still_allowed(self):
        self.assertTrue(self.propose.learn_check("ABC", "sender", "sam@gmail.com")["ok"])           # an address, not a whole domain

    def test_mutant(self):
        m = mutant(self.propose.__file__, "if mail_domains.is_public_mail(bare):", "if False:")
        # the mutant module reads paths.REGISTER at call time (shared module), so the refusal alone differs
        m.own_domains = lambda: ["mine.example"]
        self.assertTrue(m.learn_check("ABC", "domain", "mail.yahoo.co.uk")["ok"])


class ProcessAllFailsClosed(unittest.TestCase):
    acts = (REPO / "system/templates/dashboard/src/components/intakeReview/actions.js").read_text()

    def test_a_missing_level_needs_a_project(self):
        line = [ln for ln in self.acts.splitlines() if ln.startswith("export const irNeedsProject")][0]
        self.assertIn('m.level !== "matched"', line)
        self.assertNotIn('"likely"', line)                                      # the old fail-open test
        self.assertIn('m.p === "_portfolio" ? m.how !== "remembered"', line)   # a portfolio row has no level: it runs only when Alan chose it
        self.assertIn('m.src === "calendar"', line)

    def test_mutant(self):
        line = [ln for ln in self.acts.splitlines() if ln.startswith("export const irNeedsProject")][0]
        old = line.replace('m.level !== "matched"', '(m.level === "likely" || m.level === "unsure")')
        self.assertNotIn('m.level !== "matched"', old)                          # the fail-open form would fail the check above


if __name__ == "__main__":
    unittest.main()
