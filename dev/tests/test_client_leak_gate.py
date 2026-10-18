"""Tests for v2.1.0 P3's client leak check on the data (system/scripts/client_leak.py, report_doc.py; BL-336), part 2 of 3 (the fixture is in client_leak_support.py).

Run: python3 dev/tests/test_client_leak_gate.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client_leak_support import (  # noqa: E402
    Base,
    R,
    REGISTER,
)


class TheGateAtTheEnd(Base):
    """#123 (Jarvis): client_leak.findings, the approve and export gate, also runs the tracker's internal health reason and the
    internal-only markers (drafts.internal_findings) and the names check (someone who owns only items a client can't see) on the
    client document's text, so whatever route or place a text came through, it is caught at approval and export. A clean client
    report, the names of client-visible owners and their aliases, and Alan's own name still pass."""
    REASON = "ZEBRAINTERNAL vendor is failing to deliver the build on time"

    def setUp(self):
        super().setUp()
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:     # a test vault: set directly
            con.execute("UPDATE projects SET health = 'Off track', health_reason = ? WHERE code = 'ABC'", (self.REASON,))
            con.commit()
        (self.v.root / "projects/_portfolio/people-register.md").write_text(REGISTER, encoding="utf-8")

    def findings(self, summary):
        return self.py("d = report_doc.client_doc('ABC')\n"
                       "next(s for s in d['sections'] if s['id'] == 'summary')['text'] = " + repr(summary) + "\n"
                       "print(json.dumps(client_leak.findings(d)))")

    def test_a_clean_client_report_passes(self):
        self.assertEqual(self.findings("Testing starts on plan."), [])
        for ok in ("Jane Doe signs the statement of work this week.", "Jane signs the statement of work this week.",
                   "Alan Carter sends the revised plan.", "Alan will send the revised plan.",
                   "Mia Hale joined the steering committee.",                      # a register name who owns nothing here
                   "The vendor is late."):                                         # fewer than five of the reason's words in order
            self.assertEqual(self.findings(ok), [], ok)

    def test_the_health_reason_a_marker_or_an_internal_owners_name_is_found(self):
        for text, why in (("The " + self.REASON + ".", "the internal health reason"),
                          ("We think the vendor is failing to deliver soon.", "the internal health reason"),   # a 5-word run
                          ("Internal only: the vendor.", "an internal-only marker"),
                          ("Not for the client: the vendor.", "an internal-only marker"),
                          ("Omar Ali confirms the testers.", "Omar Ali is named"),       # owns only ABC-A-004 (not client-visible)
                          ("Omar confirms the testers.", "Omar is named")):              # and his alias
            got = self.findings(text)
            self.assertTrue(any(why in f for f in got), (text, got))

    def test_approve_and_export_refuse_it(self):
        self.approve_week()
        r = self.py("d = report_doc.client_doc('ABC')\n"
                    "next(s for s in d['sections'] if s['id'] == 'summary')['text'] = 'Omar Ali confirms the testers. Internal only.'\n"
                    "r = report_doc.save_draft(d)\nreport_doc.stage_client(r['path'])", ok=False)
        self.assertIn("possible internal content", r.stderr)
        self.assertIn("Omar Ali is named", r.stderr)
        self.assertIn("an internal-only marker", r.stderr)
        got = self.py("import client_check\n"
                      "d = creaite_doc.read('system/staging/drafts/2026-10-09 Client report - Example Programme (Example Client Ltd).html')\n"
                      "print(json.dumps(client_check.left_out(d)['findings']))")             # what the export route checks first
        self.assertTrue(any("Omar Ali" in f for f in got), got)


class TheGateKeepsLegitimateReports(Base):
    """#123 review M1 to M3: the gate at the end never blocks a legitimate client report. The health reason may stand in the client
    document's own health section (a client report shows internal health: Match internal copies it there), but is still found in
    any other section; an internal-only marker is found anywhere. A first name or alias that a client-visible owner also has is
    never flagged on its own (the full name of an internal-only owner still is). Someone whose only internal items are closed is
    not an internal-only owner."""
    REASON = "UAT start slipped two weeks."            # what APPROVE_WEEK's health section sets as the tracker's health reason

    def setUp(self):
        super().setUp()
        self.approve_week()

    def findings(self, health=None, summary=None):
        code = "d = report_doc.client_doc('ABC')\n"
        for sid, text in (("health", health), ("summary", summary)):
            if text is not None:
                code += f"next(s for s in d['sections'] if s['id'] == {sid!r})['text'] = {text!r}\n"
        return self.py(code + "print(json.dumps(client_leak.findings(d)))")

    def owner(self, n, name, status=None, visible=0):
        """A new ABC action owned by `name` (closed when `status` says so); its ID."""
        import sqlite3
        from contextlib import closing
        self.v.propose(f"own-{n}", [R.new("actions", 1, project="ABC", description=f"Item for {name} number {n}", owner=name,
                                          raised="2026-10-01", client_visible=visible, source="s",
                                          **({"client_message": R.CLIENT_MSG} if visible else {}))])
        self.v.run("apply")
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            ref = con.execute("SELECT id FROM actions WHERE description = ?", (f"Item for {name} number {n}",)).fetchone()[0]
            if status:
                con.execute("UPDATE actions SET status = ?, closed = '2026-10-02' WHERE id = ?", (status, ref))
                con.commit()
        return ref

    def test_m1_the_health_reason_in_the_health_section_passes(self):
        self.assertEqual(self.findings(health=self.REASON), [])           # Side by side > Match internal puts it there verbatim
        self.assertEqual(self.findings(health="On plan. " + self.REASON), [])

    def test_m1_the_health_reason_anywhere_else_is_still_found(self):
        for health in (self.REASON, "", None):
            for summary in ("This week: " + self.REASON, "We note the UAT start slipped two weeks overall."):   # whole; a 5-word run
                got = self.findings(health=health, summary=summary)
                self.assertIn("it holds the internal health reason", got, (health, summary))

    def test_m1_a_marker_is_found_even_in_the_health_section(self):
        for health in ("Internal only: " + self.REASON, "Not for the client. On track."):
            self.assertIn("it holds an internal-only marker", self.findings(health=health), health)
        self.assertIn("it holds an internal-only marker", self.findings(health=self.REASON, summary="For internal use: the vendor."))

    def test_m2_a_shared_first_name_or_alias_is_not_flagged_but_a_full_name_is(self):
        (self.v.root / "projects/_portfolio/people-register.md").write_text(
            REGISTER.replace("| Jane, JD |", "| JD |") + "| Jane Smith | js@example.com | Jane | Example Partner | Analyst | | | |\n",
            encoding="utf-8")
        self.owner(1, "Jane Smith")                                        # an open internal action: Jane Smith is internal-only
        self.assertEqual(self.findings(summary="Jane Doe signs the statement of work."), [])   # Jane Doe owns ABC-A-002
        self.assertEqual(self.findings(summary="Jane signs the statement of work."), [])       # ambiguous: a client Jane exists
        got = self.findings(summary="Jane Smith signs the statement of work.")
        self.assertIn("Jane Smith is named but owns only items a client report can't show", got)
        self.assertIn("Omar is named but owns only items a client report can't show",           # control: an unshared alias
                      self.findings(summary="Omar confirms the testers."))

    def test_m3_an_owner_of_only_closed_internal_items_is_not_internal_only(self):
        self.owner(2, "Lena Ford", status="Closed")
        self.owner(3, "Kit Marsh", status="Cancelled")
        self.assertEqual(self.findings(summary="Lena Ford and Kit Marsh attend the review."), [])
        self.owner(4, "Ravi Bell")                                         # control: an open internal action
        self.assertIn("Ravi Bell is named but owns only items a client report can't show",
                      self.findings(summary="Ravi Bell attends the review."))
        self.owner(5, "Ravi Bell", status="Closed", visible=1)              # a closed item a client report may show: not internal-only
        self.assertEqual(self.findings(summary="Ravi Bell attends the review."), [])


if __name__ == "__main__":
    unittest.main()
