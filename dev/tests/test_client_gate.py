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

    def test_a_flag_in_the_middle_of_an_earlier_line_takes_no_allowance(self):
        prop, draft = self.stage()
        block = json.loads(prop.read_text())["report"]
        R.edit_docx(draft, REASON, "Delivery is behind plan")               # the real health line no longer holds the reason
        R.edit_docx(draft, "Not yet reviewed.", f"Not yet reviewed. Was OFF TRACK: {REASON}.")   # an earlier line, flag mid-line
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


LINK_VARIANTS = (                                   # #127: step C's link shape, with its words edited; ABC-A-001 isn't client-visible
    ("inline", "[the vendor thing](creaite:item/ABC-A-001)"),
    ("title", '[the vendor thing](creaite:item/ABC-A-001 "Internal vendor thing")'),
    ("angle brackets", "[the vendor thing](<creaite:item/ABC-A-001>)"),
    ("case and spacing", "[the vendor thing](creaite:item/abc a 001)"),
    ("encoded ID", "[the vendor thing](creaite:item/ABC%2DA%2D001)"),
    ("encoded address", "[the vendor thing](creaite%3Aitem%2FABC-A-001)"),
    ("reference", "See [the vendor thing][1].\n\n[1]: creaite:item/ABC-A-001"),
    ("image", "![the vendor thing](creaite:item/ABC-A-001)"),
    ("auto link", "<creaite:item/ABC-A-001>"),
    # the review of 21d54d1 (findings 3 and the survivors): each must go whole and be found by the document gate
    ("double encoding", "[the vendor thing](creaite:item/ABC%252DA%252D001)"),
    ("triple encoding", "[the vendor thing](creaite%25253Aitem%25252FABC-A-001)"),
    ("triple-encoded ID", "[the vendor thing](creaite:item/ABC%25252DA%25252D001)"),
    ("upper-case scheme, spaced ID", "[the vendor thing](CREAITE:ITEM/abc a 001)"),
    ("line break in the address", "[the vendor thing](creaite:\nitem/ABC-A-001)"),
    ("HTML link", '<a href="creaite&#58;item/ABCA001">the vendor thing</a>'),
    ("two slashes", "[the vendor thing](creaite://item/ABC-A-001)"),
    ("items", "[the vendor thing](creaite:items/ABC-A-001)"),
    ("query", "[the vendor thing](creaite:item?id=ABC-A-001)"),
    ("backslash", "[the vendor thing](creaite:item\\ABC-A-001)"))
ITEM = "ABC-A-001"
SAFE_LINK = "[the signed paperwork](creaite:item/ABC-A-002)"        # client-visible: kept, words and all


class WorkItemLinks(Base):
    """#127 (Team Stark, Jarvis): the gate reads a work-item link's ADDRESS, not only its words, on every client path; and the
    client Current state given to a draft holds no link to an item a client may not see. Fixtures are raw Markdown of step C's
    shape: [words](creaite:item/<ID>)."""

    def with_summary(self, text, then):
        return self.py(f"d = report_doc.client_doc('ABC')\nnext(s for s in d['sections'] if s['id'] == 'summary')['text'] = {text!r}\n"
                       + then)

    def test_every_variant_is_found_by_the_gate_and_a_client_visible_link_is_not(self):
        for name, link in LINK_VARIANTS:
            got = self.findings(f"Progress continues. {link}")
            self.assertTrue(any(ITEM in f for f in got), (name, got))
        for link, why in (("[the other ledger](creaite:item/DEF-A-001)", "DEF-A-001 belongs to another project"),
                          ("[a date](creaite:item/ABC-M-001)", "ABC-M-001 isn't client-visible"),
                          ("[a promise](creaite:item/abc-p-001)", "ABC-P-001 isn't an item"),
                          ("[odd](creaite:item/nothing-here)", "a link to a work item creaite can't read")):
            self.assertTrue(any(f.startswith(why) for f in self.findings(f"Progress. {link}")), link)
        for ok in (SAFE_LINK, "[Example](https://example.com/item/123)", "See creaite:items and the creaite: item list.",
                   "[the plan](https://example.com/creaite/item/7)"):
            self.assertEqual(self.findings(f"Progress continues. {ok}"), [], ok)

    def test_every_other_link_address_is_read_too(self):
        """Review finding 1: an https, mailto, creaite:person or relative address is read (decoded) by the ID, names and wording
        checks. Internal means: it holds an item a client may not see, the name of someone who owns only such items, or a vault
        path (documents/); or it is a creaite: link other than an item or a person. Ordinary external links pass."""
        for link, why in (("[the vendor thing](https://intranet.example.com/items/ABC-A-001)", f"{ITEM} isn't client-visible"),
                          ("[the auditor](mailto:quentin.marlow@example.com)", f"{PERSON} is named"),
                          ("[the auditor](creaite:person/Quentin%20Marlow)", f"{PERSON} is named"),
                          ("[the auditor](https://intranet.example.com/people/Quentin-Marlow)", f"{PERSON} is named"),
                          ("[a note](creaite:note/7)", "a creaite link a client can't open"),
                          ("[the plan](documents/Plan%20v2.pdf)", "contains “documents/”"),
                          ("[ref][2]\n\n[2]: https://intranet.example.com/x?item=abc-a-001", f"{ITEM} isn't client-visible"),
                          ("<https://intranet.example.com/items/ABC-A-001>", f"{ITEM} isn't client-visible"),
                          ("![chart](https://intranet.example.com/ABC-A-001.png)", f"{ITEM} isn't client-visible")):
            got = self.findings(f"Progress. {link}")
            self.assertTrue(any(f.startswith(why) for f in got), (link, got))
        for ok in ("[Example](https://example.com/a_(b))", "[the client site](https://client.example.com/documents/plan.pdf)",
                   "[Jane](creaite:person/Jane%20Doe)", "[help](mailto:help@example.com)", "Mail help@example.com today.",
                   "[w](https://example.com/?q=a%20b)"):
            self.assertEqual(self.findings(f"Progress continues. {ok}"), [], ok)

    def test_a_link_in_the_current_state_panes_is_found_at_approve_and_export(self):
        self.approve_week()
        link = "Build is two weeks behind. [the vendor thing](creaite:item/ABC-A-001)"
        for pane in (0, 1):
            put = ("cs = next(s for s in d['sections'] if s['id'] == 'current_state')\n"
                   "cs['panes'] = (cs['panes'] + [{'title': '', 'text': ''}])[:2]\n"
                   f"cs['panes'][{pane}]['text'] = {link!r}\n")
            exp = self.py("import client_check\nd = report_doc.client_doc('ABC')\n" + put
                          + "print(json.dumps(client_check.left_out(d)['findings']))")
            self.assertTrue(any(ITEM in f for f in exp), (pane, exp))
            got = self.py("d = report_doc.client_doc('ABC')\n" + put + "r = report_doc.save_draft(d)\ntry:\n"
                          "    report_doc.stage_client(r['path'])\n    print(json.dumps('staged'))\n"
                          "except BaseException as e:\n    print(json.dumps(str(e)))")
            self.assertIn(ITEM, got, pane)

    def test_word_shows_a_creaite_links_words_never_its_markdown(self):
        text = "See [the signed paperwork](creaite:item/ABC-A-002) and [Jane](creaite:person/Jane%20Doe); [site](https://example.com/a)."
        got = self.py("import docx_tools\n"
                      f"print(json.dumps([docx_tools.plain({text!r}), [r[4] for r in docx_tools.md_runs({text!r})]]))")
        self.assertEqual(got[0], "See the signed paperwork and Jane; site (https://example.com/a).")
        self.assertEqual([u for u in got[1] if u], ["https://example.com/a"])    # control: an https link stays a hyperlink

    def test_a_link_in_a_table_cell_or_a_heading_is_found(self):
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "s = next(s for s in d['sections'] if s['id'] == 'summary')\n"
                      "s['heading'] = 'Update on [the vendor thing](creaite:item/ABC%2DA%2D001)'\n"
                      "print(json.dumps(client_leak.findings(d)))")
        self.assertTrue(any(ITEM in f for f in got), got)
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      "t = next(s for s in d['sections'] if s.get('rows'))\n"
                      "k = next(iter(t['rows'][0]['cells']))\n"
                      "t['rows'][0]['cells'][k] = 'Done: [the vendor thing](creaite%3Aitem%2FABC-A-001)'\n"
                      "print(json.dumps(client_leak.findings(d)))")
        self.assertTrue(any(ITEM in f for f in got), got)

    def approve_week(self):
        import test_client_leak as L
        self.py(L.APPROVE_WEEK + "print(json.dumps(p.name))")
        self.v.at("apply", script="tracker.py")

    def test_approve_and_export_refuse_an_edited_words_link_and_take_a_client_visible_one(self):
        self.approve_week()
        stage = "r = report_doc.save_draft(d)\ntry:\n    report_doc.stage_client(r['path'])\n    print(json.dumps('staged'))\n" \
                "except BaseException as e:\n    print(json.dumps(str(e)))"
        got = self.with_summary("Progress continues. [the vendor thing](creaite:item/ABC-A-001)", stage)
        self.assertNotEqual(got, "staged")
        self.assertIn(ITEM, got)
        exp = self.with_summary("Progress continues. [the vendor thing](creaite:item/ABC-A-001)",
                                "import client_check\nprint(json.dumps(client_check.left_out(d)['findings']))")
        self.assertTrue(any(ITEM in f for f in exp), exp)
        self.assertEqual(self.with_summary(f"Progress continues. {SAFE_LINK}",
                                           "import client_check\nprint(json.dumps(client_check.left_out(d)['findings']))"), [])
        self.assertEqual(self.with_summary(f"Progress continues. {SAFE_LINK}", stage), "staged")   # control: it files

    def test_a_word_draft_and_a_steerco_one_pager_with_a_link_are_stopped(self):
        prop, draft = WordDraftsGetTheWholeGate.stage(self)
        block = json.loads(prop.read_text())["report"]
        R.edit_docx(draft, "Phase two is being prepared.",
                    "Phase two is being prepared. [the vendor thing](creaite%3Aitem%2FABC%2DA%2D001)")
        for b in (block, {**block, "kind": "steerco", "version": "client"}):
            got = self.py(f"import review\nprint(json.dumps(review.client_findings({b!r})))")
            self.assertTrue(any(ITEM in f for f in got), (b["kind"], got))

    def test_a_section_draft_with_a_link_is_refused_for_the_client(self):
        link = "[the vendor thing](creaite%3Aitem%2FABC-A-001)"
        self.assertIn("isn't client-safe", self.ctx({**SECTION, "document": DOC, "text": f"Progress. {link}"}).get("refused", ""))
        self.assertNotIn("refused", self.ctx({**SECTION, "document": DOC, "text": f"Progress. {SAFE_LINK}"}))

    def test_the_client_current_state_given_to_a_draft_holds_no_internal_link(self):
        memory = self.v.root / R.ABC / "CLAUDE.md"
        text = memory.read_text(encoding="utf-8")
        panes = "\n\n".join(link for _n, link in LINK_VARIANTS) + "\n\nPaperwork: " + SAFE_LINK + ".\n\n"
        memory.write_text(text.replace("Build is two weeks behind.", "Build is two weeks behind. " + panes), encoding="utf-8")
        ctx = lambda aud: self.py(f"import report\nprint(json.dumps(report.current_context('ABC', audience={aud!r})))")
        client, internal = ctx("client"), ctx("internal")
        self.assertIn("the vendor thing", internal)                         # control: the marker is in the internal context
        current = client[client.index("## Current state now"):]
        for gone in ("the vendor thing", "Internal vendor thing", "ABC-A-001", "ABC%2DA%2D001", "abc a 001", "[1]:", "A-001", "<a "):
            self.assertNotIn(gone, current, gone)
        self.assertIn(SAFE_LINK, current)                                  # a client-visible link stays, with its words
        self.assertIn("Build is two weeks behind.", current)

    def test_the_right_pane_is_filtered_too(self):
        marker = "<!-- creaite: second pane -->"                          # docx_tools.PANE_MARKER
        memory = self.v.root / R.ABC / "CLAUDE.md"
        text = memory.read_text(encoding="utf-8")
        right = f"\n\n{marker}\n\nRight: [the vendor thing](creaite:item/ABC-A-001) and {SAFE_LINK}.\n\n"
        memory.write_text(text.replace("![Delivery plan](images/plan.png)\n", "![Delivery plan](images/plan.png)" + right),
                          encoding="utf-8")
        client = self.py("import report\nprint(json.dumps(report.current_context('ABC', audience='client')))")
        internal = self.py("import report\nprint(json.dumps(report.current_context('ABC', audience='internal')))")
        self.assertIn("right pane", internal)
        self.assertIn("the vendor thing", internal[internal.index("right pane"):])        # control: the marker is there
        tail = client[client.index("right pane"):]
        self.assertNotIn("the vendor thing", tail)
        self.assertIn(SAFE_LINK, tail)

    def test_the_filter_and_the_gate_are_linear(self):
        """Review finding 4: 100 KB of one long token takes well under a second (the old patterns took tens of seconds)."""
        code = ("import time\nout = {}\nfor name, s in (('[', '[' * 100000), ('](', '](' * 50000), ('creaite', 'creaite' * 15000),"
                " ('[a](', '[a](' * 25000), ('[a](creaite:', '[a](creaite:' * 9000)):\n"
                "    t0 = time.time(); client_leak.drop_item_links('ABC', s)\n"
                "    client_leak.text_findings(client_leak.connect(), 'ABC', client_leak.with_addresses(s)); out[name] = time.time() - t0\n"
                "print(json.dumps(out))")
        for name, took in self.py(code).items():
            self.assertLess(took, 1.0, name)

    def test_the_filter_takes_each_link_out_whole(self):
        for name, link in LINK_VARIANTS + (("other project", "[the other ledger](creaite:item/DEF-A-001)"),):
            got = self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {'Before. ' + link + chr(10) + 'After.'!r})))")
            self.assertNotIn("vendor", got, name)
            self.assertNotIn("ledger", got, name)
            self.assertNotIn("[1]", got, name)                              # a reference link's definition goes too
            self.assertNotIn("creaite", got.lower().replace("creaite:item/abc-a-002", ""), name)
            self.assertTrue(got.startswith("Before.") and "After." in got, (name, got))
            for remnant in ("A-001", "001)", "<a ", "href"):
                self.assertNotIn(remnant, got, (name, remnant))
        for name, link in (("unreadable", "[odd](creaite:item/nothing-here)"), ("a person", "[the auditor](creaite:person/Quentin)")):
            got = self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {'Before. ' + link + ' After.'!r})))")
            self.assertEqual(got, "Before.  After.", name)                   # a creaite: link naming no item goes too
        for ok in (SAFE_LINK, "[Example](https://example.com/item/123)", "[Example](https://example.com/a_(b))", "creaite is the tool."):
            self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {ok!r})))"), ok)


ENCODED_REASON = "https://x.example.com/?r=ZEBRAINTERNAL%20vendor%20is%20failing%20to%20deliver"


class TheReviewOf2a77459(Base):
    """#127 review of 2a77459: what Word shows is what the gate reads; the health reason and a marker in a link address; linear
    patterns; the scheme in any case; prose that mentions creaite: is not a link."""

    def plain(self, text):
        return self.py(f"print(json.dumps(client_leak.plain_findings(client_leak.connect(), 'ABC', {text!r})))")

    def test_text_that_plain_words_delete_but_word_shows_is_found(self):
        """Finding 1: _plain's link pattern crosses spaces and line breaks and drops a title and an image's words; the gate also
        reads the stored strings."""
        for text in (f"[t](https://x.example.com/a b {INTERNAL_ID})", f"[s](https://x.example.com/\n{INTERNAL_ID})",
                     f'[x](https://e.example.org/ "{INTERNAL_ID}")', f"![{INTERNAL_ID} for {PERSON}](images/plan.png)",
                     f"| A | B |\n|---|---|\n| [x](https://x.example.com/a | {INTERNAL_ID}) |"):
            got = self.findings(f"Progress. {text}")
            self.assertTrue(any(f.startswith(f"{INTERNAL_ID} isn't client-visible") for f in got), (text, got))
        self.assertIn(f"{PERSON} is named but owns only items a client report can't show",
                      self.findings(f"Progress. ![{PERSON}](images/plan.png)"))
        for ok in ("[the client site](https://client.example.com/documents/plan.pdf)", "![Delivery plan](images/plan.png)",
                   "[Example](https://example.com/a_(b))"):
            self.assertEqual(self.findings(f"Progress continues. {ok}"), [], ok)      # control: stored words that are client-safe

    def test_the_health_reason_and_a_marker_in_an_address_are_found_everywhere(self):
        """Finding 2: on approve and export (findings) and the plain path (plain_findings)."""
        for link, why in ((f"[s](https://x.example.com/{REASON.replace(' ', '-')})", "it holds the internal health reason"),
                          ("[s](https://x.example.com/internal-only/page)", "it holds an internal-only marker"),
                          (f"[s]({ENCODED_REASON})", "it holds the internal health reason")):
            self.assertIn(why, self.findings(f"Progress. {link}"), link)
            self.assertIn(why, self.plain(f"Progress. {link}"), link)
        self.assertEqual(self.plain("Progress. [s](https://x.example.com/page)"), [])        # control
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:   # a test vault: set directly
            con.execute("UPDATE actions SET client_message = ? WHERE id = 'ABC-A-002'",
                        (R.CLIENT_MSG.replace("The signed statement of work.", f"The [signed]({ENCODED_REASON}) statement."),))
            con.commit()
        got = self.py("print(json.dumps(client_leak.findings(report_doc.client_doc('ABC'))))")
        self.assertIn("it holds the internal health reason", got)

    def test_an_encoded_marker_in_the_health_section_and_an_items_address_are_found(self):
        marker = "[s](https://x.example.com/internal%2Donly/page)"            # only the decoded address says internal-only
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      f"next(s for s in d['sections'] if s.get('type') == 'health')['text'] = 'Behind plan. ' + {marker!r}\n"
                      "print(json.dumps(client_leak.findings(d)))")
        self.assertIn("it holds an internal-only marker", got)
        got = self.py("d = report_doc.client_doc('ABC')\nk = next(iter(d['items']))\n"
                      f"d['items'][k]['title'] = 'UAT [start]({ENCODED_REASON})'\n"
                      "print(json.dumps([k, client_leak.findings(d)]))")
        self.assertIn("it holds the internal health reason", got[1], got[0])

    def test_every_check_is_linear_on_brackets(self):
        """Finding 3: creaite_doc._plain and docx_tools.md_runs took tens of seconds on 100 KB of "["."""
        code = ("import time, docx_tools\ncon = client_leak.connect()\nout = {}\n"
                "for name, s in (('[', '[' * 100000), ('[a](', '[a](' * 25000), ('![a](', '![a](' * 20000)):\n"
                "    d = report_doc.client_doc('ABC')\n    next(x for x in d['sections'] if x['id'] == 'summary')['text'] = s\n"
                "    for f, run in (('findings', lambda: client_leak.findings(d)), ('plain', lambda: client_leak.plain_findings(con, 'ABC', s)),"
                " ('client_problems', lambda: edit_ai.client_problems('ABC', s)), ('md_runs', lambda: docx_tools.md_runs(s))):\n"
                "        t0 = time.time(); run(); out[name + ' ' + f] = time.time() - t0\n"
                "print(json.dumps(out))")
        for name, took in self.py(code).items():
            self.assertLess(took, 5.0, name)

    def test_the_scheme_in_capitals_is_found_and_dropped(self):
        link = f"[p](CREAITE:item/{INTERNAL_ID})"
        self.assertTrue(any(f.startswith(f"{INTERNAL_ID} isn't client-visible") for f in self.findings(f"Progress. {link}")))
        for link in (link, f"[p](CREAITE%3Aitem/{INTERNAL_ID})", f"[p](CREAITE:{INTERNAL_ID})"):   # (not case-folded on the way)
            self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', 'Before. {link} After.')))"),
                             "Before.  After.", link)

    def test_a_creaite_person_link_split_by_a_line_break_is_read(self):
        """SCHEME_GAP in link_addresses: without the join, the address of a split creaite:person link is only "creaite:"."""
        self.assertIn(f"{PERSON} is named but owns only items a client report can't show",
                      self.findings("Progress. [the auditor](creaite:\nperson/Quentin%20Marlow)"))

    def test_prose_mentioning_creaite_is_not_a_link(self):
        """Finding 6: ordinary prose passes and is kept; real creaite: links are still found and dropped."""
        prose = "Text creaite: notes/ are kept"
        self.assertEqual(self.findings(prose), [])
        self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {prose!r})))"), prose)
        for link in ("creaite:notes/7", "[n](creaite: note/7)", "[n](creaite:\nnote/7)", "creaite: notes/7"):
            got = self.findings(f"Progress. {link}")
            self.assertTrue(any(f.startswith("a creaite link a client can't open") for f in got), (link, got))
            text = f"Before. {link} After."
            self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {text!r})))").split(),
                             ["Before.", "After."], link)

    def test_word_shows_only_the_words_of_any_creaite_link(self):
        """Finding 5: md_runs reads the scheme as the gate does (any case, encoded) and words with [brackets] in them."""
        got = self.py("import docx_tools\nprint(json.dumps([docx_tools.plain(t) for t in ("
                      "'See [p](CREAITE:item/ABC-A-002).', 'See [p](creaite%3Aitem/ABC-A-002).', 'See [p](creaite&#58;item/ABC-A-002).', "
                      "'See [a [b] c](creaite:item/ABC-A-002).', 'See [a [b] c](https://example.com/x).')]))")
        self.assertEqual(got, ["See p.", "See p.", "See p.", "See a [b] c.", "See a [b] c (https://example.com/x)."])


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
