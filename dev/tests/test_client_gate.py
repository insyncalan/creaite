"""#127: the client gate on every client path (Team Stark's review of #123). The data is fictional.

Run: python3 dev/tests/test_client_gate.py      (quick tier: no Chrome, no model)
1. The ✦ on a report section takes its audience from the report the request names (edit_ai.document_audience, as /api/edit/ai's
   place), never from the page's claim; no report named is refused.
2. A Word client report and the client-safe steerco one-pager get the whole gate at approval (client_leak.plain_findings: items
   by ID, wording, the internal health reason or a marker, names), and so does an approval from Excel; cx-document refuses a client
   audience.
3. client_leak.text_findings finds an ID however it is written, and milestones, promises and another project's items too.
4. A people register that is missing or can't be read fails closed, with a plain message.
Each marker is checked both ways: missing from client output, present where the internal path should have it.
"""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture: populate, ReportVault, NOW, new, edit_docx)

HEAD = "import sys, json; sys.path.insert(0, 'system/scripts')\nimport client_leak, creaite_doc, drafts, edit_ai, report_doc\n"
INTERNAL_ID, MIXED_ID, MILESTONE_ID, PROMISE_ID, OTHER_ID = "ABC-A-004", "abc-a-004", "ABC-M-001", "ABC-P-001", "DEF-A-001"
PERSON = "Quentin Marlow"                                    # owns only an open internal action
REASON = "ZEBRAINTERNAL vendor is failing to deliver the build on time"
DOC = {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "client": ""}
WEEKLY_DOC = {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"}
SECTION = {"kind": "report-section", "code": "ABC", "section": "summary", "heading": "Summary", "action": "polish",
           "text": "Phase two can start once the paperwork is signed."}


class Base(unittest.TestCase):
    def setUp(self):
        self.v = R.ReportVault()
        R.populate(self.v)
        self.v.propose("def", [{"n": 1, "op": "new", "table": "projects", "match": "strong", "flags": [], "decision": "approved",
                                "values": {"code": "DEF", "name": "Other Programme"}}])
        self.v.run("apply")
        self.v.propose("seed127", [
            R.new("actions", 1, project="DEF", description="Migrate the other ledger", owner="Jane Doe (Example Client Ltd)",
                  raised="2026-10-01", client_visible=1, client_message=R.CLIENT_MSG, source="s"),      # client-visible, but DEF's
            R.new("actions", 2, project="ABC", description="Line up the quiet audit", owner=PERSON, raised="2026-10-01",
                  source="s")])
        self.v.run("apply")
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:   # a test vault: set directly
            con.execute("INSERT INTO promises (id, project, promised_by, promised_to, description, raised, source) "
                        "VALUES (?, 'ABC', 'Alan Carter', 'Jane Doe', 'Send the pricing sheet', '2026-10-01', 's')", (PROMISE_ID,))
            con.execute("UPDATE projects SET health = 'Off track', health_reason = ? WHERE code = 'ABC'", (REASON,))
            con.commit()
            ids = {r[0] for r in con.execute("SELECT id FROM actions WHERE project = 'DEF'")}
        self.assertEqual(ids, {OTHER_ID})

    def tearDown(self):
        self.v.cleanup()

    def py(self, code):
        r = subprocess.run([sys.executable, "-c", HEAD + code], cwd=self.v.root, env={**os.environ, "CREAITE_NOW": R.NOW},
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def findings(self, summary, kind="client"):
        make = "report_doc.client_doc('ABC')" if kind == "client" else "report_doc.weekly_doc('ABC')"
        return self.py(f"d = {make}\nnext(s for s in d['sections'] if s['id'] == 'summary')['text'] = {summary!r}\n"
                       "print(json.dumps(client_leak.findings(d)))")

    def ctx(self, req):
        return self.py(f"print(json.dumps(drafts.context({req!r}), ensure_ascii=False))")


class TheSectionAudienceIsBoundOnTheServer(Base):
    """Part 1: drafts.report_request binds the audience from the report named, as edit_ai.bound_place does."""

    def test_a_page_claiming_weekly_for_the_client_report_gets_the_client_audience(self):
        ctx = self.ctx({**SECTION, "report": "weekly", "document": DOC})
        self.assertEqual(ctx["extra"]["audience"], "client")
        self.assertNotIn("Vendor exits the market", ctx["prompt"])           # an internal risk's wording
        self.assertNotIn(PERSON, ctx["prompt"])

    def test_a_page_claiming_client_for_the_weekly_report_gets_the_internal_audience(self):
        ctx = self.ctx({**SECTION, "report": "client", "document": WEEKLY_DOC})
        self.assertEqual(ctx["extra"]["audience"], "internal")
        self.assertIn("Vendor exits the market", ctx["prompt"])              # control: the marker is real, and internal here

    def test_no_report_named_another_project_or_an_unknown_kind_is_refused(self):
        for req, why in (({**SECTION, "report": "client"}, "Say which report"),
                         ({**SECTION, "document": {**DOC, "code": "DEF"}}, "don't agree"),
                         ({**SECTION, "document": {**DOC, "kind": "steerco"}}, "isn't a report"),
                         ({**SECTION, "document": {**DOC, "week_ending": "soon"}}, "isn't a report"),
                         ({**SECTION, "document": {**DOC, "audience": "internal"}}, "isn't a report")):
            got = self.ctx(req)
            self.assertIn(why, got.get("refused", ""), (req, got))

    def test_a_saved_client_report_that_reads_as_internal_is_refused(self):
        got = self.py("d = report_doc.client_doc('ABC')\nr = report_doc.save_draft(d)\n"
                      "doc = creaite_doc.read(r['path'])\ndoc['audience'] = 'internal'\n"
                      "open(report_doc.paths.resolve(r['path']), 'w', encoding='utf-8').write(creaite_doc.dumps(doc))\n"
                      f"print(json.dumps(drafts.context({{**{SECTION!r}, 'document': {DOC!r}}})))")
        self.assertIn("isn't a report", got.get("refused", ""), got)

    def test_a_client_reply_bringing_in_any_marker_is_dropped_and_the_internal_one_keeps_it(self):
        client = self.ctx({**SECTION, "document": DOC})
        internal = self.ctx({**SECTION, "document": WEEKLY_DOC})
        for marker in (MIXED_ID, MILESTONE_ID, PROMISE_ID, OTHER_ID, PERSON):
            reply = f"Phase two can start once the paperwork is signed; see {marker}. [S1]"
            req = {**SECTION, "document": DOC}
            got = self.py(f"print(json.dumps(drafts.result({req!r}, {client!r}, {reply!r})))")
            self.assertEqual(got["text"], "", marker)
            self.assertIn("isn't client-safe", got["message"])
            kept = self.py(f"print(json.dumps(drafts.result({req!r}, {internal!r}, {reply!r})))")
            self.assertIn(marker, kept["text"])                              # control: the internal audience keeps it

    def test_a_client_section_already_holding_a_marker_is_refused(self):
        for marker in (MIXED_ID, MILESTONE_ID, OTHER_ID):
            got = self.ctx({**SECTION, "document": DOC, "text": f"Phase two waits on {marker}."})
            self.assertIn("isn't client-safe", got.get("refused", ""), marker)
            self.assertNotIn("refused", self.ctx({**SECTION, "document": WEEKLY_DOC, "text": f"Phase two waits on {marker}."}))


class TextFindingsMatchesEveryId(Base):
    """Part 3: an ID written any way, a milestone, a promise and another project's item are found in a client document."""

    def test_each_marker_is_found_in_a_client_report_and_not_checked_in_an_internal_one(self):
        for marker, why in ((MIXED_ID, f"{INTERNAL_ID} isn't client-visible but its ID appears"),
                            ("ABC\u2011A\u2011004", f"{INTERNAL_ID} isn't client-visible but its ID appears"),
                            (MILESTONE_ID, f"{MILESTONE_ID} isn't client-visible, but its ID appears"),
                            (PROMISE_ID, f"{PROMISE_ID} isn't an item a client report can show, but its ID appears"),
                            (OTHER_ID.lower(), f"{OTHER_ID} belongs to another project, but its ID appears")):
            got = self.findings(f"Progress continues ({marker}).")
            self.assertIn(why, got, marker)
            self.assertEqual(self.findings(f"Progress continues ({marker}).", kind="weekly"), [], marker)

    def test_a_client_visible_id_and_a_code_with_a_number_still_pass(self):
        self.assertEqual(self.findings("Progress continues (ABC-006); ABC 100 users are ready."), [])

    def test_more_ways_of_writing_an_id_are_found(self):
        """#127 review: other separators, brackets, O for zero, no zero padding, Cyrillic and Greek look-alikes in the code, an
        underscore, and Arabic-Indic digits, all through edit_ai's one normaliser."""
        why = f"{INTERNAL_ID} isn't client-visible but its ID appears"
        for written in ("ABC/A/004", "ABC:A:004", "ABC (A) 004", "ABC-A-OO4", "abc-a-o04", "ABC-A-4", "ABC A 04",
                        "\u0410\u0412\u0421-\u0410-004", "\u0391\u0392C-A-004", "ABC_A_004", "abc_a_004",
                        "ABC-A-\u0660\u0660\u0664"):
            self.assertIn(why, self.text(f"Progress continues ({written})."), written)   # the raw text (a doc's text is tidied)

    def test_whole_numbers_dates_and_ordinary_text_are_not_ids(self):
        for text in ("Progress continues (ABC-A-40).", "Progress continues (ABC-A-041).",       # never ABC-A-004
                     "Progress continues (ABC-A-0041).", "ABC A 4/10 is the review day.", "ABC A 4.5 is the release.",
                     "ABC goes live on 2026-10-09, signed 09/10/2026.", "ABC A 10/09 is the review day.",
                     "The A/B test ran; ABC A/B results are in.", "ABC at 10:30 on 04/11."):
            self.assertEqual(self.findings(text), [], text)
            self.assertEqual(self.text(text), [], text)

    def text(self, text):
        """client_leak.text_findings on a raw text, as review (Word), edit_ai and the ✦ call it."""
        return self.py(f"print(json.dumps(client_leak.text_findings(client_leak.connect(), 'ABC', {text!r})))")


class WordDraftsGetTheWholeGate(Base):
    """Part 2: a Word client report (cx-client-report) and the client-safe steerco one-pager are checked at approval with
    plain_findings; an approval from Excel goes through the same check; cx-document refuses a client audience."""

    def stage(self):
        spec = self.v.root / "system/staging/drafts/client.json"
        spec.write_text(json.dumps({"code": "ABC", "summary": ["Phase two is being prepared."], "progress": ["Plan revised"],
                                    "next_steps": ["Sign the statement of work"], "input_needed": ["Signature by 16-10"],
                                    "period_start": "2026-10-01"}))
        self.v.at("client-stage", str(spec), script="report.py")
        prop = next((self.v.root / "system/staging").glob("proposed-*-client-ABC.json"))
        return prop, self.v.root / json.loads(prop.read_text())["report"]["draft"]

    def word_findings(self, block):
        return self.py(f"import review\nprint(json.dumps(review.client_findings({block!r})))")

    def test_every_marker_in_a_word_client_report_is_found_and_the_health_line_is_allowed(self):
        prop, draft = self.stage()
        block = json.loads(prop.read_text())["report"]
        self.assertIn(REASON, self.v.run("text", str(draft), script="docx_tools.py").stdout)   # the health line holds the reason
        self.assertEqual(self.word_findings(block), [])                     # M1 kept: a clean report passes
        R.edit_docx(draft, "Phase two is being prepared.",
                    f"Phase two is being prepared. See {MIXED_ID}, {MILESTONE_ID}, {PROMISE_ID} and {OTHER_ID}. {PERSON} helps. "
                    f"Internal only. The {REASON}.")
        got = self.word_findings(block)
        for why in (f"{INTERNAL_ID} isn't client-visible but its ID appears", f"{MILESTONE_ID} isn't client-visible",
                    f"{PROMISE_ID} isn't an item", f"{OTHER_ID} belongs to another project",
                    f"{PERSON} is named but owns only items a client report can't show",
                    "it holds an internal-only marker", "it holds the internal health reason"):
            self.assertTrue(any(f.startswith(why) for f in got), (why, got))
        steerco = {**block, "kind": "steerco", "version": "client"}
        self.assertEqual(self.word_findings(steerco), got)                  # the client-safe one-pager: the same check
        self.assertTrue(self.py("import review\nprint(json.dumps([review.client_block(b) for b in "
                                f"({steerco!r}, {{**{steerco!r}, 'version': 'internal'}}, {block!r})]))") == [True, False, True])
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        n = next(r["n"] for r in listed if r["ref"] == "report")
        out = self.v.run("approve", str(n), script="review.py").stdout
        self.assertIn("possible internal content", out)
        self.assertIn(f"{PERSON} is named", out)

    def test_excel_cannot_approve_a_client_report_that_holds_a_marker(self):
        prop, draft = self.stage()
        R.edit_docx(draft, "Phase two is being prepared.", f"Phase two is being prepared. See {MILESTONE_ID}.")
        code = ("import excel_sync\nfrom openpyxl import Workbook\n"
                "def wb():\n    w = Workbook(); ws = w.active; ws.title = 'Review'\n"
                "    ws.append(['File'] + ['x'] * 10)\n"
                f"    ws.append([{prop.name!r}, 'report'] + [''] * 7 + ['Approve', None])\n    return w\n"
                "notes = []\nn = excel_sync.apply_review_decisions(wb(), notes)\n"
                f"d = json.load(open('system/staging/{prop.name}'))\n"
                "print(json.dumps({'n': n, 'notes': notes, 'decision': d['report'].get('report_decision')}))")
        got = self.py(code)
        self.assertEqual((got["n"], got["decision"]), (0, "pending"), got)
        self.assertIn("may hold internal content", got["notes"][0])
        R.edit_docx(draft, f" See {MILESTONE_ID}.", "")                    # control: the clean report is approved from Excel
        got = self.py(code)
        self.assertEqual((got["n"], got["decision"]), (1, "approved"), got)

    def test_excel_cannot_approve_a_client_safe_steerco_one_pager_that_holds_a_marker(self):
        f = self.v.root / "system/staging/drafts/steerco.json"
        f.write_text(json.dumps({"code": "ABC", "version": "client", "summary": ["Phase two is being prepared."], "force": True}))
        self.v.at("steerco-stage", str(f), script="report.py")
        prop = sorted((self.v.root / "system/staging").glob("proposed-2*-steerco*.json"))[-1]
        block = json.loads(prop.read_text())["report"]
        self.assertEqual((block["kind"], block["version"]), ("steerco", "client"))
        draft = self.v.root / block["draft"]
        self.assertEqual(self.word_findings(block), [])                     # its own health line is allowed (M1)
        R.edit_docx(draft, "Phase two is being prepared.", f"Phase two is being prepared. See {MILESTONE_ID}.")
        code = ("import excel_sync\nfrom openpyxl import Workbook\n"
                "w = Workbook(); ws = w.active; ws.title = 'Review'\nws.append(['File'] + ['x'] * 10)\n"
                f"ws.append([{prop.name!r}, 'report'] + [''] * 7 + ['Approve', None])\n"
                "notes = []\nn = excel_sync.apply_review_decisions(w, notes)\n"
                f"d = json.load(open('system/staging/{prop.name}'))\n"
                "print(json.dumps({'n': n, 'notes': notes, 'decision': d['report'].get('report_decision')}))")
        got = self.py(code)
        self.assertEqual((got["n"], got["decision"]), (0, "pending"), got)
        R.edit_docx(draft, f" See {MILESTONE_ID}.", "")                    # control: the clean one-pager is approved from Excel
        self.assertEqual(self.py(code)["decision"], "approved")

    def test_the_health_reason_is_allowed_only_on_the_reports_own_health_line(self):
        prop, draft = self.stage()
        block = json.loads(prop.read_text())["report"]
        self.assertEqual(self.word_findings(block), [])                     # on the flagged health line: allowed
        R.edit_docx(draft, REASON, "Delivery is behind plan")               # a health line without the reason, which then
        R.edit_docx(draft, "Phase two is being prepared.", f"Phase two is being prepared. The {REASON}.")   # sits in the summary
        self.assertIn("it holds the internal health reason", self.word_findings(block))
        R.edit_docx(draft, "OFF TRACK", "")                                 # no health line at all: the reason has nowhere to stand
        R.edit_docx(draft, f"Phase two is being prepared. The {REASON}.", "Phase two is being prepared.")
        R.edit_docx(draft, "Delivery is behind plan", REASON)
        self.assertIn("it holds the internal health reason", self.word_findings(block))

    def test_cx_document_refuses_a_client_audience(self):
        spec = {"title": "Open actions", "sections": [{"heading": "Actions", "paragraphs": ["A list."]}]}
        f = self.v.root / "system/staging/drafts/adhoc.json"
        f.write_text(json.dumps({**spec, "audience": "client"}))
        r = self.v.at("adhoc", str(f), script="report.py", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("internal only", r.stdout + r.stderr)
        f.write_text(json.dumps(spec))                                      # control: the internal document is built
        self.assertIn("Wrote system/staging/drafts/", self.v.at("adhoc", str(f), script="report.py").stdout)


class TheRegisterFailsClosed(Base):
    """Part 4: a people register that is missing, can't be decoded or has no People table makes every names check refuse, with a
    plain message; a readable one checks the names (the control)."""
    REGISTER = Path("projects/_portfolio/people-register.md")

    def broken(self):
        reg = self.v.root / self.REGISTER
        good = reg.read_bytes()
        yield "missing", lambda: reg.unlink()
        yield "not text", lambda: reg.write_bytes(b"\xff\xfe\x00broken")
        yield "no People table", lambda: reg.write_text("# People register\n\nNothing here.\n", encoding="utf-8")
        reg.write_bytes(good)

    def test_the_gate_the_client_place_and_the_section_draft_refuse(self):
        summary = "Phase two can start once the paperwork is signed."
        self.assertEqual(self.findings(summary), [])                        # control: a readable register, a clean report
        self.assertIn(f"{PERSON} is named but owns only items a client report can't show", self.findings(f"{PERSON} helps."))
        for what, breaks in self.broken():
            breaks()
            got = self.findings(summary)
            self.assertTrue(any("people register couldn't be read" in f for f in got), (what, got))
            req = {"option": "polish", "text": "Testing could start late.", "code": "ABC", "place": "client", "document": DOC}
            ctx = self.py(f"try:\n    print(json.dumps(edit_ai.context({req!r})))\n"
                          "except edit_ai.Refused as e:\n    print(json.dumps({'refused': str(e)}))")
            self.assertIn("people register couldn't be read", ctx.get("refused", ""), (what, ctx))
            sec = self.ctx({**SECTION, "document": DOC})
            self.assertIn("people register couldn't be read", sec.get("refused", ""), (what, sec))
            if what != "not text":              # (an undecodable register already stops the internal facts elsewhere: not #127's)
                self.assertNotIn("refused", self.ctx({**SECTION, "document": WEEKLY_DOC}), what)   # internal: no names check
        self.assertEqual(self.findings(summary), [])                        # restored: passes again


if __name__ == "__main__":
    unittest.main()
