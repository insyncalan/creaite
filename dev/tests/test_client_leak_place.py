"""Tests for v2.1.0 P3's client leak check on the data (system/scripts/client_leak.py, report_doc.py; BL-336), part 3 of 3 (the fixture is in client_leak_support.py).

Run: python3 dev/tests/test_client_leak_place.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client_leak_support import (  # noqa: E402
    Base,
    REGISTER,
)


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

    def test_numbers_after_a_code_and_a_spaced_v_ip_are_not_ids_or_vip(self):
        """#123 review L: the loose ID match flags only an ID the tracker holds (that a client may not see); a code followed by a
        number that isn't an item, and V IP across a space, pass. The exact ID form and real items written any way still drop."""
        self.v.propose("def", [{"n": 1, "op": "new", "table": "projects", "match": "strong", "flags": [], "decision": "approved",
                                "values": {"code": "DEF", "name": "Other"}}])
        self.v.run("apply")                                                           # a second code for "def 100"
        ctx = self.context()
        for ok in ("Testing could start late; ABC 100 users are ready.", "The ABC 300-day plan is agreed.",
                   "ABC 100.5 is the new release.", "The def 100 users are trained.", "Phase V IP telephony goes live.",
                   "The V IP lounge opens; vipers aside."):
            with self.subTest(ok=ok):
                self.assertEqual(self.result(ctx, ok)["text"], ok)
        for bad in ("Testing could start late (abc a 004).", "Testing could start late (abc 005).",     # exist, not client-visible
                    "Testing could start late (ABC-100).",                                            # the exact form: as before
                    "Testing could start late; the V. I. P. knows.", "Testing could start late; the V-I-P knows."):
            self.assertEqual(self.result(ctx, bad)["text"], "", bad)

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
