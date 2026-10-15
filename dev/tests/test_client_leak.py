"""Tests for v2.1.0 P3's client leak check on the data (system/scripts/client_leak.py, report_doc.py; BL-336).

Run: python3 dev/tests/test_client_leak.py
Nothing that isn't client-visible, is Sensitive or is partner-only reaches a client report: not its items, rows, tags or milestone
list, not its file, not an approval. A client report is approved only after that week's internal report, and its facts then lock
to the approved week. test_reports' fixture and fixed clock (Friday 09-10-2026); the data is fictional.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture: populate, ReportVault, NOW)

HEAD = "import sys, json; sys.path.insert(0, 'system/scripts')\nimport report_doc, creaite_doc, client_leak\n"
APPROVE_WEEK = """
d = report_doc.weekly_doc("ABC")
for s in d["sections"]:
    if s["id"] == "health":
        s["text"] = "UAT start slipped two weeks."
r = report_doc.save_draft(d)
p = report_doc.stage_weekly(r["path"])
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.v = R.ReportVault()
        R.populate(self.v)

    def tearDown(self):
        self.v.cleanup()

    def py(self, code, ok=True):
        """Run Python in the vault on the fixed clock; returns the last line printed, read as JSON."""
        r = subprocess.run([sys.executable, "-c", HEAD + code], cwd=self.v.root, env={**os.environ, "CREAITE_NOW": R.NOW},
                           capture_output=True, text=True)
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = r.stdout.strip().splitlines()
        return json.loads(lines[-1]) if ok else r

    def label(self, item_id, name="Sensitive"):
        self.v.propose(f"lab-{item_id}-{name.replace(' ', '')}", [
            {"n": 1, "op": "new", "table": "item_labels", "match": "strong", "flags": [], "decision": "approved",
             "values": {"item_id": item_id, "label": name, "reason": "kept from the client"}}])
        self.v.run("apply")

    def approve_week(self):
        self.py(APPROVE_WEEK + "print(json.dumps(p.name))")
        self.v.at("apply", script="tracker.py")


class ItemsNeverReachTheClient(Base):
    def test_client_report_holds_only_client_visible_items(self):
        doc = self.py("print(json.dumps(report_doc.client_doc('ABC')))")
        self.assertEqual(sorted(doc["items"]), ["ABC-006", "ABC-A-002", "ABC-D-007"])
        text = json.dumps(doc)
        for internal in ("ABC-005", "Vendor exits the market", "ABC-D-008", "Absorb the phase one overrun", "Confirm tester names"):
            self.assertNotIn(internal, text)
        self.assertNotIn("Test licences not ordered", text)                   # an item's internal wording never; its client wording only
        self.assertIn("Test licences are not yet ordered.", text)

    def test_a_sensitive_item_is_never_shown_even_when_client_visible(self):
        self.label("ABC-006")
        doc = self.py("print(json.dumps(report_doc.client_doc('ABC')))")
        self.assertNotIn("ABC-006", doc["items"])
        self.assertNotIn("ABC-006", json.dumps(doc["sections"]))
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "risks = next(s for s in d['sections'] if s['id'] == 'risks')\n"
                      "risks['rows'].append({'ref': 'ABC-006', 'shown': True, 'cells': {'type': 'Issue', 'risk': 'Licences'}})\n"
                      "d['items']['ABC-006'] = {'table': 'raid', 'id': 'ABC-006', 'title': 'Licences'}\n"
                      "safe, removed = client_leak.make_safe(d)\n"
                      "print(json.dumps({'found': client_leak.findings(d), 'removed': removed, 'safe': client_leak.findings(safe),"
                      " 'items': sorted(safe['items'])}))")
        self.assertIn("ABC-006 is Sensitive: never in a client report", got["found"])
        self.assertEqual(got["removed"], ["ABC-006 is Sensitive: never in a client report"])
        self.assertEqual(got["safe"], [])
        self.assertNotIn("ABC-006", got["items"])

    def test_a_partner_only_item_never_appears(self):
        self.v.propose("partner-label", [{"n": 1, "op": "new", "table": "labels", "match": "strong", "flags": [],
                                          "decision": "approved", "values": {"name": "Partner only", "colour": "grey"}}])
        self.v.run("apply")
        self.label("ABC-D-007", "Partner only")
        doc = self.py("print(json.dumps(report_doc.client_doc('ABC')))")
        self.assertNotIn("ABC-D-007", json.dumps(doc))
        got = self.py("print(json.dumps(client_leak.item_problem(client_leak.connect(), 'ABC-D-007')))")
        self.assertEqual(got, "ABC-D-007 is partner-only: never in a client report")

    def test_saving_a_client_report_drops_an_item_that_isnt_client_visible(self):
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "risks = next(s for s in d['sections'] if s['id'] == 'risks')\n"
                      "risks['rows'].append({'ref': 'ABC-005', 'shown': True, 'cells': {'type': 'Risk', 'risk': 'Vendor exits'}})\n"
                      "r = report_doc.save_draft(d)\n"
                      "back = creaite_doc.read(r['path'])\n"
                      "print(json.dumps({'removed': r['removed'], 'refs': sorted(client_leak.refs(back))}))")
        self.assertEqual(got["removed"], ["ABC-005 isn't client-visible"])
        self.assertNotIn("ABC-005", got["refs"])
        filed = (self.v.root / "system/staging/drafts/2026-10-09 Client report - Example Programme (Example Client Ltd).html")
        self.assertNotIn("Vendor exits", filed.read_text(encoding="utf-8"))

    def test_internal_wording_in_the_text_is_found(self):
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "s = next(s for s in d['sections'] if s['id'] == 'summary')\n"
                      "s['text'] = 'We will absorb the phase one overrun internally. Budget overrun on phase one is being absorbed.'\n"
                      "print(json.dumps(client_leak.findings(d)))")
        self.assertTrue(any(f.startswith("ABC-D-008 isn't client-visible but its wording appears") for f in got), got)
        self.assertTrue(any(f.startswith("memory line marked Client-safe: no appears") for f in got), got)

    def test_an_internal_report_is_never_checked_or_changed(self):
        got = self.py("d = report_doc.weekly_doc('ABC')\n"
                      "print(json.dumps({'f': client_leak.findings(d), 'same': client_leak.make_safe(d)[0] is d}))")
        self.assertEqual(got, {"f": [], "same": True})


class Baseline(Base):
    def test_a_client_report_is_approved_only_after_the_internal_week(self):
        r = self.py("d = report_doc.client_doc('ABC')\nr = report_doc.save_draft(d)\nreport_doc.stage_client(r['path'])", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Approve the internal weekly report for week ending 09-10-2026 first", r.stderr)
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*client*.json")), [])

    def test_facts_lock_to_the_approved_week(self):
        self.approve_week()
        self.v.propose("later", [{"n": 1, "op": "update", "table": "raid", "id": "ABC-006", "match": "strong", "flags": [],
                                  "decision": "approved", "changes": {"client_visible": 0}}])
        self.v.at("apply", script="tracker.py")
        doc = self.py("print(json.dumps(report_doc.client_doc('ABC')))")
        self.assertEqual(doc["based_on"]["path"], f"{R.ABC}/reports/2026-10-09 Weekly report - Example Programme.html")
        self.assertTrue(doc["meta"]["locked"])
        self.assertEqual(doc["meta"]["facts_week"], "2026-10-09")
        # the facts are the approved week's, but the leak check reads the tracker as it is now: no longer client-visible, so out
        self.assertNotIn("ABC-006", doc["items"])
        self.assertIn("ABC-D-007", doc["items"])

    def test_approve_refuses_a_leak_and_files_a_clean_report(self):
        self.approve_week()
        r = self.py("d = report_doc.client_doc('ABC')\n"
                    "s = next(s for s in d['sections'] if s['id'] == 'summary')\n"
                    "s['text'] = 'Notes from documents/ for the client.'\n"
                    "r = report_doc.save_draft(d)\nreport_doc.stage_client(r['path'])", ok=False)
        self.assertIn("possible internal content", r.stderr)
        self.assertIn("contains “documents/”", r.stderr)
        self.py("d = creaite_doc.read('system/staging/drafts/2026-10-09 Client report - Example Programme (Example Client Ltd).html')\n"
                "s = next(s for s in d['sections'] if s['id'] == 'summary')\n"
                "s['text'] = 'Testing starts on plan.'\n"
                "r = report_doc.save_draft(d, d['version'])\n"
                "print(json.dumps(report_doc.stage_client(r['path']).name))")
        self.v.at("apply", script="tracker.py")
        filed = self.v.root / R.ABC / "reports/2026-10-09 Client report - Example Programme (Example Client Ltd).html"
        text = filed.read_text(encoding="utf-8")
        self.assertIn('"state": "approved"', text)
        for internal in ("ABC-005", "ABC-D-008", "Vendor exits the market", "client_facts"):
            self.assertNotIn(internal, text)


class P8ClientView(Base):
    """v2.1.0 P8: what the client view's Match internal, eyes, health reason and left-out check can and can't do to the data."""

    def test_internal_rows_copied_into_the_client_report_are_dropped_at_save(self):
        """Match internal copied wholesale (what a generic sheet would do) would put internal rows on the client's page: saving removes them."""
        self.label("ABC-006")
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "risks = next(s for s in d['sections'] if s['id'] == 'risks')\n"
                      "for ref, t in (('ABC-005', 'Vendor exits the market before go-live'), ('ABC-006', 'Test licences not ordered')):\n"
                      "    risks['rows'].append({'ref': ref, 'shown': True, 'cells': {'type': 'Risk', 'risk': t}})\n"
                      "    d['items'][ref] = {'table': 'raid', 'id': ref, 'title': t}\n"
                      "r = report_doc.save_draft(d)\n"
                      "text = open(str(__import__('paths').resolve(r['path']))).read()\n"
                      "print(json.dumps({'removed': r['removed'], 'leaked': [x for x in ('ABC-005', 'ABC-006', 'Vendor exits', 'Test licences not') if x in text]}))")
        self.assertEqual(sorted(got["removed"]), ["ABC-005 isn't client-visible", "ABC-006 is Sensitive: never in a client report"])
        self.assertEqual(got["leaked"], [])

    def test_the_left_out_check_never_offers_a_sensitive_or_unseen_item(self):
        self.label("ABC-006")
        got = self.py("import client_check\nd = report_doc.client_doc('ABC')\nc = client_check.check(d)\n"
                      "print(json.dumps({'items': {x['ref']: [x['kind'], x['why']] for x in c['left_out']['items']},"
                      " 'addable': [a['row']['ref'] for a in c['addable']]}))")
        self.assertEqual(got["items"]["ABC-006"], ["sensitive", "Sensitive: never in a client report"])
        self.assertEqual(got["items"]["ABC-005"], ["blocked", "not client-visible"])
        self.assertEqual(got["addable"], [])

    def test_a_row_hidden_by_its_eye_keeps_no_wording_in_the_file(self):
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "risks = next(s for s in d['sections'] if s['id'] == 'risks')\n"
                      "risks['rows'] = [{'ref': r['ref'], 'shown': False} for r in risks['rows']]\n"
                      "r = report_doc.save_draft(d)\n"
                      "text = open(str(__import__('paths').resolve(r['path']))).read()\n"
                      "print(json.dumps('Test licences are not yet ordered' in text.split('creaite-data')[0]))")
        self.assertFalse(got)

    def test_the_health_reason_is_in_the_data_but_never_on_the_exported_page(self):
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "d['meta']['health_diff'] = {'internal': 'At risk', 'client': 'On track', 'reason': 'INTERNAL-REASON-ZED'}\n"
                      "print(json.dumps({'page': 'INTERNAL-REASON-ZED' in creaite_doc.render(d, editing=False),"
                      " 'findings': client_leak.findings(d)}))")
        self.assertEqual(got, {"page": False, "findings": []})


REGISTER = ("# People register\n\n## People\n\n| Full name | Email | Aliases | Organisation | Role | Hidden | VIP | Labels |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| Jane Doe | jane@example.com | Jane, JD | Example Client Ltd | Sponsor | | | |\n"
            "| Omar Ali | omar@example.com | Omar | Example Client Ltd | Tester | | | |\n"
            "| Mia Hale | mia@example.com | Mia | Example Partner | Adviser | | | |\n")


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


class ReviewReadsTheData(Base):
    def test_client_findings_reads_a_creaite_draft_from_its_data(self):
        got = self.py("import review\n"
                      "d = report_doc.client_doc('ABC')\n"
                      "d['sections'][3]['text'] = 'Restricted: absorb the phase one overrun internally.'\n"
                      "d['items']['ABC-005'] = {'table': 'raid', 'id': 'ABC-005', 'title': 'x'}\n"
                      "p = 'system/staging/drafts/check.html'\n"
                      "open(p, 'w').write(creaite_doc.dumps(d))\n"
                      "print(json.dumps(review.client_findings({'draft': p, 'project': 'ABC'})))")
        self.assertIn("ABC-005 isn't client-visible", got)
        self.assertIn("contains “restricted”", got)
        self.assertTrue(any("ABC-D-008" in f for f in got), got)


class ClientPlaceForAiOnSelection(Base):
    """#123: the client sheet's AI bar (edit_ai.py, place "client") gives Claude only what a client report may show: the open items
    client_leak passes, no people, no health; and a suggestion that brings in anything else is dropped. The internal sheet's place
    ("report") still has every open item and owner (the control)."""
    REASON = "ZEBRAINTERNAL vendor is failing to deliver the build on time"
    INTERNAL_IDS = ("ABC-A-001", "ABC-A-004", "ABC-005", "ABC-M-001", "ABC-A-003")   # not client-visible, or excluded by a label
    OWNERS = ("Alan Carter", "Omar Ali", "Jane Doe")

    def setUp(self):
        super().setUp()
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:     # a test vault: set directly
            con.execute("UPDATE projects SET health = 'Off track', health_reason = ? WHERE code = 'ABC'", (self.REASON,))
            con.commit()
        self.v.propose("board-label", [{"n": 1, "op": "new", "table": "labels", "match": "strong", "flags": [],
                                        "decision": "approved", "values": {"name": "Board only", "colour": "grey",
                                                                           "behaviour": "exclude"}}])
        self.v.run("apply")
        self.label("ABC-A-003", "Board only")                                         # client-visible, but a label excludes it

    DOC = {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "client": ""}   # the client sheet's report (#123)

    def context(self, place="client", text="Testing could start late.", option="polish", document=..., code="ABC"):
        """edit_ai.context on a request; by default the client place names its report, as the client sheet does."""
        req = {"option": option, "text": text, "code": code, "place": place}
        if document is ...:
            document = self.DOC if place == "client" else None
        if document is not None:
            req["document"] = document
        return self.py("import edit_ai\ntry:\n    print(json.dumps(edit_ai.context(" + repr(req) + ")))\n"
                       "except edit_ai.Refused as e:\n    print(json.dumps({'refused': str(e)}))")

    def result(self, ctx, reply):
        return self.py("import edit_ai\nprint(json.dumps(edit_ai.result(" + repr(
            {"context": ctx, "reply": "<<<SUGGESTION\n" + reply + "\nSUGGESTION>>>"}) + ")))")

    def test_the_client_prompt_holds_only_client_safe_items_and_no_people(self):
        ctx = self.context()
        p = ctx["prompt"].replace("(such as ABC-A-003)", "")                     # the template's own example ID
        self.assertIn("Its open item IDs: ABC-A-002, ABC-006\n", p)                   # client-visible, open, not excluded
        self.assertIn("Its people: none listed", p)
        for x in self.INTERNAL_IDS + self.OWNERS + ("ZEBRAINTERNAL", "Off track", "Vendor exits", "Confirm tester names"):
            self.assertNotIn(x, p)
        self.assertEqual(ctx["people"], [])

    def test_the_internal_sheet_still_has_every_open_item_and_owner(self):
        p = self.context(place="report")["prompt"].replace("(such as ABC-A-003)", "")   # control: the seeds are real
        for x in self.INTERNAL_IDS + ("Omar Ali", "Alan Carter"):
            self.assertIn(x, p)

    def test_a_suggestion_bringing_in_internal_content_is_dropped(self):
        ctx = self.context()
        for reply in ("Testing could start late (ABC-A-004).",                       # an item that isn't client-visible
                      "Testing could start late; see ABC-A-003.",                    # a client-visible item a label excludes
                      "Testing could start late: " + self.REASON + ".",              # the tracker's internal health reason
                      "Testing could start late. Internal only: the vendor.",        # an internal-only marker
                      "Testing could start late, says Omar Ali.",                    # a person the text doesn't name
                      "Testing could start late; the VIP knows.",                    # the word VIP
                      "Testing could start late; absorb the phase one overrun internally."):  # internal wording
            got = self.result(ctx, reply)
            self.assertEqual(got["text"], "", reply)
            self.assertIn("isn't client-safe", got["message"])

    def test_a_client_safe_suggestion_comes_back(self):
        reply = "Testing may start late (ABC-006); Jane Doe signs the statement of work (ABC-A-002)."   # her item is client-visible
        self.assertEqual(self.result(self.context(), reply)["text"], reply)

    def test_the_same_reply_on_the_internal_sheet_is_not_dropped(self):
        got = self.result(self.context(place="report"), "Testing could start late (ABC-A-004).")
        self.assertEqual(got["text"], "Testing could start late (ABC-A-004).")      # control: only the client place drops it

    def test_selected_text_already_holding_internal_content_is_refused(self):
        for text in ("Testing could start late (ABC-A-004).", "We will absorb the phase one overrun internally."):
            self.assertIn("isn't client-safe", self.context(text=text).get("refused", ""), text)
        got = self.context(text="Hello there.", code="", document={**self.DOC, "code": ""})
        self.assertIn("refused", got)                                                # no project: nothing to check against

    # ── #123 (Jarvis): the server binds the place from the document; the page's `place` is never trusted ──

    def test_a_request_claiming_the_report_place_with_the_client_report_gets_the_client_place(self):
        for claimed in ("report", "minutes", "notes", "readonly", "made-up"):
            ctx = self.context(place=claimed, document=self.DOC)
            self.assertEqual(ctx.get("place"), "client", claimed)
            p = ctx["prompt"].replace("(such as ABC-A-003)", "")
            self.assertIn("Its open item IDs: ABC-A-002, ABC-006\n", p)
            self.assertIn("Its people: none listed", p)
            for x in self.INTERNAL_IDS + self.OWNERS + ("ZEBRAINTERNAL", "Off track"):
                self.assertNotIn(x, p)
            got = self.result(ctx, "Testing could start late (ABC-A-004).")             # and its reply is checked as a client one
            self.assertEqual(got["text"], "", claimed)

    def test_the_client_place_without_a_document_is_refused(self):
        for doc in (None, "", {}):
            got = self.context(document=doc)
            self.assertIn("client report wasn't named", got.get("refused", ""), doc)

    def test_a_document_that_isnt_this_projects_client_report_is_refused(self):
        bad = ({**self.DOC, "kind": "weekly"},                    # not a client report
               {**self.DOC, "kind": ""},
               {**self.DOC, "code": "DEF"},                       # another project's
               {**self.DOC, "week_ending": "2026-13-45"},         # a date creaite can't read
               {**self.DOC, "extra": "x"},                        # a key a document doesn't have
               {**self.DOC, "client": 7},
               "client", ["client"])
        for doc in bad:
            for place in ("client", "report"):
                self.assertIn("refused", self.context(place=place, document=doc), (doc, place))
        unknown = {"kind": "client", "code": "ZZZ", "week_ending": "2026-10-09", "client": ""}   # a project the tracker hasn't
        self.assertIn("refused", self.context(code="ZZZ", document=unknown))

    def draft_at(self):
        """The stored path of the ABC client report's draft for the week (where the server looks first)."""
        return self.py("import report_server\nprint(json.dumps(report_doc.draft_path('client', 'ABC', '2026-10-09', "
                       "report_server.project_client('ABC'))))")

    def test_a_saved_client_report_is_read_and_one_that_cant_be_or_isnt_a_client_one_is_refused(self):
        self.py("r = report_doc.save_draft(report_doc.client_doc('ABC'))\nprint(json.dumps(r['path']))")
        self.assertEqual(self.context(place="report", document=self.DOC).get("place"), "client")   # control: a real saved one
        f = self.v.root / self.draft_at()
        self.assertTrue(f.is_file(), f)
        good = f.read_text(encoding="utf-8")
        f.write_text("<html>not a creaite document</html>", encoding="utf-8")                        # unreadable
        self.assertIn("refused", self.context(place="report", document=self.DOC))
        self.assertIn("refused", self.context(document=self.DOC))
        f.write_text(good.replace('"audience": "client"', '"audience": "internal"'), encoding="utf-8")   # not a client audience
        self.assertIn("refused", self.context(place="report", document=self.DOC))
        f.write_text(good.replace('"project": "ABC"', '"project": "DEF"'), encoding="utf-8")          # another project's file
        self.assertIn("refused", self.context(place="report", document=self.DOC))

    def test_a_report_place_with_no_document_is_as_before(self):
        for place in ("report", "notes"):                                              # the weekly sheet and Notes: unchanged
            ctx = self.context(place=place, document=None, option="shorter")
            self.assertEqual(ctx.get("place"), place, ctx)
            self.assertIn("ABC-A-004", ctx["prompt"])

    def test_items_only_the_item_check_catches_are_dropped(self):
        """#123 review: cases text_findings doesn't see (it reads actions, risks and decisions by ID): a partner-only label that only
        warns, a milestone that isn't client-visible, a promise and another project's item. Only item_problem drops these."""
        self.v.propose("partner-label", [{"n": 1, "op": "new", "table": "labels", "match": "strong", "flags": [],
                                          "decision": "approved", "values": {"name": "Partner only", "colour": "grey",
                                                                             "behaviour": "warn"}}])
        self.v.run("apply")
        self.label("ABC-006", "Partner only")
        ctx = self.context()
        for ref in ("ABC-006", "ABC-M-001", "ABC-P-001", "DEF-A-001"):
            got = self.result(ctx, f"Testing could start late ({ref}).")
            self.assertEqual(got["text"], "", ref)
            self.assertIn("isn't client-safe", got["message"], ref)

    def test_the_prompt_carries_the_client_rule(self):
        import importlib
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        edit_ai = importlib.import_module("edit_ai")
        self.assertIn(edit_ai.CLIENT_RULE, self.context()["prompt"])
        self.assertNotIn(edit_ai.CLIENT_RULE, self.context(place="report", document=None)["prompt"])   # control

    def test_aliases_of_client_visible_owners_pass_and_other_register_names_dont(self):
        (self.v.root / "projects/_portfolio/people-register.md").write_text(REGISTER, encoding="utf-8")
        ctx = self.context()
        ok = "Jane signs the statement of work (ABC-A-002)."                        # Jane Doe's alias: she owns a client item
        self.assertEqual(self.result(ctx, ok)["text"], ok)
        for bad in ("Testing could start late, says Omar.",                        # an internal owner's alias
                    "Testing could start late, says Mia Hale."):                    # a register name the text doesn't give
            self.assertEqual(self.result(ctx, bad)["text"], "", bad)

    def test_no_project_and_an_unreadable_tracker_have_their_own_messages(self):
        got = self.context(code="", document=None, place="client")                  # refused before the checks: no document
        self.assertIn("refused", got)
        got = self.py("import edit_ai\nprint(json.dumps([edit_ai.refusal(edit_ai.client_problems('', 'Hello there.')),"
                      " edit_ai.refusal(edit_ai.client_problems('', 'Hello.'), True)]))")
        self.assertIn("no project to check", got[0])
        self.assertIn("no project to check", got[1])
        got = self.py("import edit_ai, tracker\n"
                      "def boom():\n    raise OSError('locked')\n"
                      "tracker.connect = boom\n"
                      "print(json.dumps([edit_ai.refusal(edit_ai.client_problems('ABC', 'Hello there.')),"
                      " edit_ai.result({'context': {'place': 'client', 'code': 'ABC', 'original': 'Hi.'},"
                      " 'reply': '<<<SUGGESTION\\nHi there.\\nSUGGESTION>>>'})['message']]))")
        for msg in got:
            self.assertIn("couldn't check", msg)
            self.assertNotIn("isn't client-safe", msg)
        ctx = self.context()
        self.assertIn("isn't client-safe", self.result(ctx, "Late (ABC-A-004).")["message"])   # control: a real leak keeps its words

    def test_ids_and_vip_written_any_way_are_still_caught(self):
        ctx = self.context()
        for reply in ("Testing could start late, see abc-a-004.", "Testing could start late, seeABC-A-004.",
                      "Testing could start late (ABC A 004).", "Testing could start late (ABC\u2011A\u2011004).",
                      "Testing could start late (ABC\u2013A\u2013004).", "Testing could start late (ABC-\u200bA-004).",
                      "Testing could start late (\uff21\uff22\uff23-\uff21-\uff10\uff10\uff14).", "Testing could start late (abc.a.004).",
                      "Testing could start late; the V\u0399P knows.", "Testing could start late; the V\u200bIP knows.",
                      "Testing could start late; the V.I.P. knows.", "Testing could start late; the vips know."):
            got = self.result(ctx, reply)
            self.assertEqual(got["text"], "", reply)
        ok = "Testing could start late (ABC-006); vipers and 1,004 users aside."     # control: a client-visible ID, no VIP
        self.assertEqual(self.result(ctx, ok)["text"], ok)

    def test_names_the_model_invents_are_only_a_names_added_note(self):
        """Documents today's behaviour (Jarvis, #123): a name in neither the people register nor the project's owners isn't one the
        client check knows, so the suggestion comes back, with the plain-code check's 'names-added' note under it. Not changed here."""
        for place in ("client", "report"):
            reply = "Testing could start late, says Zara Quillfeather."             # invented: not in the register, not an owner
            got = self.result(self.context(place=place), reply)
            self.assertEqual(got["text"], reply, place)
            self.assertEqual([n["id"] for n in got["notes"]], ["names-added"], (place, got["notes"]))
            self.assertIn("Zara", got["notes"][0]["note"])


if __name__ == "__main__":
    unittest.main()
