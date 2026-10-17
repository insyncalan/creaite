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

    def assert_linear(self, out):
        """Each {name: [seconds at size n, seconds at 4n]} grows linearly (#127 round 6: growth, not wall-clock seconds, so a loaded
        machine doesn't fail it): 4n takes under 8 times n (linear is about 4, quadratic 16) or under a second, and under 30 s."""
        for name, (small, large) in out.items():
            self.assertLess(large, 30.0, name)
            self.assertLess(large, max(8 * small, 1.0), (name, small, large))


# The timing tests' prelude: took(run) is the best of two runs, so one slow moment under load doesn't count.
TIMER = ("import time\ndef took(run):\n    best = None\n    for _ in range(2):\n        t0 = time.perf_counter(); run()\n"
         "        best = min(best, time.perf_counter() - t0) if best is not None else time.perf_counter() - t0\n    return best\n")


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
        """Review finding 4: 100 KB of one long token grows linearly (the old patterns took tens of seconds)."""
        code = (TIMER + "out = {}\nfor name, u, k in (('[', '[', 100000), ('](', '](', 50000), ('creaite', 'creaite', 15000),"
                " ('[a](', '[a](', 25000), ('[a](creaite:', '[a](creaite:', 9000)):\n"
                "    def run(s): client_leak.drop_item_links('ABC', s); "
                "client_leak.text_findings(client_leak.connect(), 'ABC', client_leak.with_addresses(s))\n"
                "    out[name] = [took(lambda: run(u * (k // 4))), took(lambda: run(u * k))]\n"
                "print(json.dumps(out))")
        self.assert_linear(self.py(code))

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
        code = (TIMER + "import docx_tools\ncon = client_leak.connect()\nout = {}\n"
                "def doc(s):\n    d = report_doc.client_doc('ABC')\n"
                "    next(x for x in d['sections'] if x['id'] == 'summary')['text'] = s\n    return d\n"
                "RUNS = (('findings', lambda s, d: client_leak.findings(d)), ('plain', lambda s, d: client_leak.plain_findings(con, 'ABC', s)),"
                " ('client_problems', lambda s, d: edit_ai.client_problems('ABC', s)), ('md_runs', lambda s, d: docx_tools.md_runs(s)))\n"
                "for name, u, k in (('[', '[', 100000), ('[a](', '[a](', 25000), ('![a](', '![a](', 20000)):\n"
                "    small, large = u * (k // 4), u * k\n    ds, dl = doc(small), doc(large)\n"
                "    for f, run in RUNS:\n"
                "        out[name + ' ' + f] = [took(lambda: run(small, ds)), took(lambda: run(large, dl))]\n"
                "print(json.dumps(out))")
        self.assert_linear(self.py(code))

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


PAD = "a" * 2100                                              # longer than the gate reads of one address (LONG_TOKEN)
TOO_LONG = "a link address too long to check"


class TheReviewOf199ac40(Base):
    """#127 review of 199ac40: an address longer than the gate reads, or holding a quote, is read to where Word's link ends or
    fails closed; no quadratic pattern is left; names are found however they are spaced; a label check is reported only for the
    labels; a creaite: link with a space after its colon, or encoded six times, is dropped."""

    def plain(self, text):
        return self.py(f"print(json.dumps(client_leak.plain_findings(client_leak.connect(), 'ABC', {text!r})))")

    def both(self, text):
        return self.findings(f"Progress. {text}"), self.plain(f"Progress. {text}")

    def test_an_address_longer_than_the_gate_reads_fails_closed(self):
        tails = ("/ZEBRAINTERNAL%20vendor%20is%20failing%20to%20deliver", "?who=Quentin%20Marlow", "/internal%2Donly",
                 "?r=ABC%2DA%2D004")
        for tail in tails:
            address = f"https://x.example.com/{PAD}{tail}"
            for text in (f"[s]({address})", address, f'<a href="{address}">s</a>'):
                for got in self.both(text):
                    self.assertTrue(any(f.startswith(TOO_LONG) for f in got), (tail, text[:30], got))
        underscores = f"[s](https://x.example.com/{'_' * 2100}{tails[1]})"   # the words drop the underscores; Word shows them
        for got in self.both(underscores):
            self.assertTrue(any(f.startswith(TOO_LONG) for f in got), got)
        got = self.py("import docx_tools\nprint(json.dumps(docx_tools.plain(" + repr(f"[s](https://x.example.com/{PAD}{tails[1]})") + ")))")
        self.assertTrue(got.endswith("Quentin%20Marlow)"), got[-40:])               # what Word shows: the whole address
        for got in self.both(f"A long word {PAD} and a short [link](https://x.example.com/page)."):
            self.assertEqual(got, [])                                                # control: a long word holding no link

    def test_an_address_with_a_quote_or_an_angle_is_read_to_where_words_link_ends(self):
        for text, why in (('[s](https://x.example.com/"Quentin%20Marlow)', f"{PERSON} is named"),
                          ('[s](https://x.example.com/"ZEBRAINTERNAL%20vendor%20is%20failing%20to%20deliver)',
                           "it holds the internal health reason"),
                          ("[s](https://x.example.com/<Quentin%20Marlow>)", f"{PERSON} is named"),
                          ('[s](https://x.example.com/"ABC%2DA%2D004")', f"{INTERNAL_ID} isn't client-visible"),
                          ("[s](https://x.example.com/it's/ABC%2DA%2D004)", f"{INTERNAL_ID} isn't client-visible")):
            for got in self.both(text):
                self.assertTrue(any(f.startswith(why) for f in got), (text, got))
        for got in self.both("[plan](https://client.example.com/it's/\"q\"/plan.pdf)"):
            self.assertEqual(got, [])                                                # control: a quote in a client-safe address

    def test_emphasis_and_images_are_linear(self):
        """100 KB of "![", "*a " or "_a " took up to 15 s in md_runs and creaite_doc._plain (the old unbounded patterns)."""
        code = (TIMER + "import docx_tools\ncon = client_leak.connect()\nout = {}\n"
                "def doc(s):\n    d = report_doc.client_doc('ABC')\n"
                "    next(x for x in d['sections'] if x['id'] == 'summary')['text'] = s\n    return d\n"
                "RUNS = (('findings', lambda s, d: client_leak.findings(d)), ('plain', lambda s, d: client_leak.plain_findings(con, 'ABC', s)),"
                " ('client_problems', lambda s, d: edit_ai.client_problems('ABC', s)), ('md_runs', lambda s, d: docx_tools.md_runs(s)))\n"
                "for name, p in (('![', '!['), ('*a ', '*a '), ('_a ', '_a ')):\n"
                "    small, large = (p * 50000)[:25000], (p * 50000)[:100000]\n    ds, dl = doc(small), doc(large)\n"
                "    for f, run in RUNS:\n"
                "        out[name + ' ' + f] = [took(lambda: run(small, ds)), took(lambda: run(large, dl))]\n"
                "out['_plain 300 KB'] = [took(lambda: creaite_doc._plain('![' * 37500)), took(lambda: creaite_doc._plain('![' * 150000))]\n"
                "print(json.dumps(out))")
        self.assert_linear(self.py(code))
        got = self.py("import docx_tools\nprint(json.dumps([docx_tools.plain(t) for t in ('**Bold** and _italic_ and *it* and ~~gone~~',"
                      " 'snake_case_word stays', '2 * 3 * 4')]))")
        self.assertEqual(got, ["Bold and italic and it and gone", "snake_case_word stays", "2 * 3 * 4"])     # unchanged

    def test_a_name_is_found_however_it_is_spaced(self):
        found = f"{PERSON} is named but owns only items a client report can't show"
        for text in ("Waiting on Quentin  Marlow.", "Waiting on Quentin\nMarlow for sign-off.", "Waiting on Quentin Marlow.",
                     "Waiting on Quentin\tMarlow.", "Waiting on Quen​tin Marlow.", "Waiting on Quentin​ Marlow.",
                     "See [the auditor](https://x.example.com/%28Quentin%20Marlow%29).",
                     "See [the auditor](https://x.example.com/%28Quentin%C2%A0%20Marlow%29)."):
            for got in self.both(text):
                self.assertIn(found, got, repr(text))
            self.assertIn(f"{PERSON} isn't named in the text",
                          self.py(f"print(json.dumps(edit_ai.client_problems('ABC', {text!r})))"), repr(text))
        got = self.py("print(json.dumps(sorted(client_leak.named('Waiting on Quentin Marlow.', ['Quentin\u00a0 Marlow', 'Ada\u200b Vale']))))")
        self.assertEqual(got, ["Quentin\u00a0 Marlow"])                          # a name stored oddly spaced is read the same way
        for got in self.both("Waiting on Quentin Marlowe's team."):
            self.assertEqual(got, [])                                                # control: a longer name isn't this one

    def test_a_creaite_link_with_a_space_after_its_colon_is_dropped_whole(self):
        for link in (f"creaite: item/{INTERNAL_ID}", f"[p](creaite: item/{INTERNAL_ID})", f"CREAITE :item/{INTERNAL_ID}",
                     f"creaite: item/{INTERNAL_ID}", "creaite: note/7", "[the auditor](creaite: person/Quentin%20Marlow)"):
            text = f"Before. {link} After."
            self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {text!r})))").split(),
                             ["Before.", "After."], repr(link))
        prose = "Text creaite: notes/ are kept"
        self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {prose!r})))"), prose)

    def test_an_address_encoded_past_what_the_gate_decodes_fails_closed(self):
        six, seven = "creaite%25252525253a", "creaite%2525252525253a"     # "creaite:" %-encoded six and seven times
        for link in (f"[p]({seven}item/{INTERNAL_ID})", f"<{seven}item/{INTERNAL_ID}>", f"{seven}item/{INTERNAL_ID}",
                     f'<a href="{seven}item/{INTERNAL_ID}">p</a>', f"[p]({seven}note/7)", f"[p]({six}item/{INTERNAL_ID})"):
            for got in self.both(link):
                self.assertTrue(any(f.startswith("a link address encoded more than") for f in got), (link, got))
            text = f"Before. {link} After."
            got = self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {text!r})))")
            self.assertNotIn("004", got, link)
            self.assertNotIn("note", got, link)
        five = "creaite%252525253a"                              # five times: read, and a client-visible item's link stays
        text = f"See [p]({five}item/ABC-A-002)."
        self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {text!r})))"), text)
        self.assertEqual(self.findings(text), [])

    def client_findings(self, setup=""):
        if not (self.v.root / "system/staging/drafts/probe-client.html").exists():     # the draft, made while the labels work
            self.py("from pathlib import Path\nd = report_doc.client_doc('ABC')\n"
                    f"next(s for s in d['sections'] if s['id'] == 'summary')['text'] = 'See {INTERNAL_ID}.'\n"
                    "p = Path('system/staging/drafts/probe-client.html'); p.parent.mkdir(parents=True, exist_ok=True)\n"
                    "p.write_text(creaite_doc.dumps(d))\nprint(1)")
        return self.py("import review, tracker\np = 'system/staging/drafts/probe-client.html'\nclosed = []\nreal = tracker.connect\n"
                       "class Con:\n    def __init__(s): s.c = real()\n    def execute(s, *a): return s.c.execute(*a)\n"
                       "    def close(s): closed.append(1); s.c.close()\n    def __getattr__(s, n): return getattr(s.c, n)\n"
                       "tracker.connect = Con\n" + setup +
                       "out = {}\nfor name, blk in (('doc', {'draft': p, 'project': 'ABC'}), ('word', {'draft': 'x.docx', 'project': 'ABC'})):\n"
                       f"    review.draft_lines = lambda _p: ['See {INTERNAL_ID}.']\n"
                       "    out[name] = review.client_findings(blk)\nout['closed'] = len(closed)\nprint(json.dumps(out))")

    def test_a_label_check_failure_is_reported_only_for_the_labels_and_keeps_the_other_findings(self):
        ok = self.client_findings()
        self.assertEqual(ok["closed"], 2)                                             # the connection is closed each time
        for k in ("doc", "word"):
            self.assertEqual(ok[k], [f"{INTERNAL_ID} isn't client-visible but its ID appears"], k)
        got = self.client_findings("import sqlite3\nfor f in ('findings', 'plain_findings'):\n"
                                   "    setattr(client_leak, f, lambda *a: (_ for _ in ()).throw(sqlite3.OperationalError('no such table: actions')))\n")
        for k in ("doc", "word"):
            self.assertEqual(len(got[k]), 1, got[k])
            self.assertTrue(got[k][0].startswith("Couldn't check the client report against the tracker"), got[k])
            self.assertIn("no such table: actions", got[k][0])
        self.assertEqual(got["closed"], 2)
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:     # a test vault: break the labels directly
            con.execute("DROP TABLE labels")
            con.execute("CREATE VIEW labels AS SELECT name FROM item_labels")
            con.commit()
        got = self.client_findings()
        for k in ("doc", "word"):
            self.assertTrue(got[k][0].startswith("Couldn't check the label exclusions"), got[k])
            self.assertIn(f"{INTERNAL_ID} isn't client-visible but its ID appears", got[k][1:])
        self.assertEqual(got["closed"], 2)


# #127 round 4: characters Word shows as nothing (format characters, variation selectors, fillers), as code points
UNSEEN = [0x2065, 0x2066, 0x2067, 0x2068, 0x2069, 0x206A, 0x206F, 0x061C, 0x034F, 0xFE00, 0xFE0F, 0xE0041, 0xE0020, 0x17B4,
          0x17B5, 0x115F, 0x3164, 0xFFF9, 0x0600, 0x1D173, 0x200B]
NAMED = f"{PERSON} is named but owns only items a client report can't show"
HIDDEN = f"{INTERNAL_ID} isn't client-visible but its ID appears"


class TheReviewOf55967e3(Base):
    """#127 round 4 (review of 55967e3): an invisible character hides no name, ID or marker; %- or entity-encoded words outside
    any address are read; a name is found however its words are joined; the long-address check counts only the address and words
    its finding for what it found; the prompt filter drops more forms of a creaite: link, and the gate flags creaite:\\note."""

    def gate(self, texts):
        """{text: [findings, plain_findings, client_problems]}, each after "Progress. ", in one run."""
        return dict(zip(texts, self.py(
            "con = client_leak.connect()\nout = []\n"
            f"for t in {texts!r}:\n"
            "    t = 'Progress. ' + t\n    d = report_doc.client_doc('ABC')\n"
            "    next(s for s in d['sections'] if s['id'] == 'summary')['text'] = t\n"
            "    out.append([client_leak.findings(d), client_leak.plain_findings(con, 'ABC', t), edit_ai.client_problems('ABC', t)])\n"
            "print(json.dumps(out))")))

    def assert_found(self, cases, kinds=(0, 1, 2)):
        """Each text gets a finding starting with its reason on every path in `kinds` (0 the document, 1 plain, 2 the ✦)."""
        got = self.gate([t for t, _ in cases])
        for text, why in cases:
            for k in kinds:
                want = why if k < 2 else {NAMED: f"{PERSON} isn't named", HIDDEN: f"{INTERNAL_ID} isn't client-visible"}.get(
                    why, why.replace("it holds ", ""))             # the ✦'s own words
                self.assertTrue(any(f.startswith(want) for f in got[text][k]), (repr(text), k, want, got[text][k]))

    def test_an_invisible_character_hides_no_name_id_or_marker(self):
        cases = []
        for cp in UNSEEN:
            ch = chr(cp)
            cases += [(f"Waiting on Quen{ch}tin Marlow.", NAMED), (f"Blocked by ABC-A-0{ch}04.", HIDDEN),
                      (f"Note: internal{ch}-only.", "it holds an internal-only marker"), (f"A confi{ch}dential note.", "contains")]
        self.assert_found(cases)
        got = self.py("con = client_leak.connect()\nd = report_doc.client_doc('ABC')\n"     # a marker where the reason may stand
                      "next(s for s in d['sections'] if s.get('type') == 'health')['text'] = 'Behind plan. internal\\u2066-only.'\n"
                      "print(json.dumps([client_leak.findings(d), client_leak.plain_findings(con, 'ABC', "
                      "'OFF TRACK internal\\u2066-only.\\nProgress.')]))")
        for g in got:
            self.assertIn("it holds an internal-only marker", g)
        self.assertEqual(self.py("print(json.dumps(drafts.internal_findings(client_leak.connect(), 'ABC', "
                                 "'internal\\u200b-only', 'internal-only')))"), [])      # the original held it: not added
        for got in self.gate(["The build is on time️ and the paperwork is signed."]).values():
            self.assertEqual(got, [[], [], []])                    # control: an emoji's selector in client-safe text

    def test_encoded_words_outside_any_address_are_read(self):
        reason = "it holds the internal health reason"
        pad = "a" * 1000
        self.assert_found([
            ("See Quentin%20Marlow.", NAMED), ("See ABC%2DA%2D004.", HIDDEN), ("See internal%2Donly.", "it holds an internal-only marker"),
            ("See ZEBRAINTERNAL%20vendor%20is%20failing%20to%20deliver%20the%20build%20on%20time.", reason),
            ("[s](https://x.example.com/ ?who=Quentin%20Marlow)", NAMED),
            ("[s](https://x.example.com/　?r=ABC%2DA%2D004)", HIDDEN),
            ("See Quentin&#32;Marlow and nothing else.", NAMED), ("See ABC&#45;A&#45;004.", HIDDEN),
            ("See x.example.com/?who=Quentin%20Marlow", NAMED),
            ("See [a](https://x.example.com/Quentin&#37;20Marlow).", NAMED),
            (f"[s](https://x.example.com/{pad}\u0085{pad}a?who=Quentin%20Marlow)", NAMED),
            (f"[s](https://x.example.com/{pad}　{pad}a?who=Quentin%20Marlow)", NAMED)])
        for got in self.gate(["Phase two is 95% complete & tested; see https://client.example.com/a%20plan."]).values():
            self.assertEqual(got, [[], [], []])                    # control: a % and an & that hide nothing

    def test_a_name_is_found_however_its_words_are_joined(self):
        self.assert_found([(t, NAMED) for t in (
            "Waiting on Quentin-Marlow.", "Waiting on Quentin_Marlow.", "Waiting on Quentin.Marlow.", "Waiting on QuentinMarlow.",
            "Waiting on Quentin­Marlow.", "Mail quentin.marlow@example.com today.", "Waiting on Marlow, Quentin.",
            "Waiting on Quentín Marlow.", "Waiting on Quentin Marlów.", "See [a](https://x.example.com/QuentinMarlow).",
            "Waiting on **Quentin** Marlow.", "Waiting on [Quentin](https://x.example.com/) Marlow.",
            "Waiting _on Quentin Marlow_.")])
        got = self.py("print(json.dumps([sorted(client_leak.named(t, ['Max Well', 'Ada Vale', 'Quentin Marlow'])) for t in "
                      "('maxwell and adavale', 'Max-Well', 'Quentin Marlowe', 'QuentinMarlowe', 'xQuentinMarlow', 'Ada, Vale')]))")
        self.assertEqual(got, [[], ["Max Well"], [], [], [], []])  # short names never run together; a longer word isn't a name

    def test_the_long_address_check_reads_only_the_address_and_says_what_it_found(self):
        base = "https://x.example.com/"
        got = self.py("print(json.dumps([client_leak.unreadable_findings(t) for t in " + repr([
            f"[s]({base}{'a' * (2000 - len(base))})", f"[the plan]({base}{'a' * (2000 - len(base))}).",
            f"[s]({base}{'a' * (2001 - len(base))})", "%41" * 700, "&#65;" * 500, f"[s]({'a' * 2001})",
            "documents/" + "a" * 2001, "x" * 2500, "进度良好，完成率95%。" * 200]) + "]))")
        self.assertEqual(got[:2], [[], []])                        # an address of exactly 2000 characters, its label not counted
        self.assertTrue(got[2][0].startswith(TOO_LONG), got[2])
        for g in got[3:5]:                                          # a run of only %XX or only entities: not a link, still unread
            self.assertEqual(len(g), 1, g)
            self.assertTrue(g[0].startswith("text too long to check"), g)
        for g in got[5:7]:                                          # a relative address, in a link or bare
            self.assertTrue(g and g[0].startswith(TOO_LONG), g)
        self.assertEqual(got[7:], [[], []])                         # a long word, and a paragraph whose % encodes nothing

    def test_the_prompt_filter_drops_more_forms_and_the_gate_flags_a_note(self):
        links = [f"creaite:item/{w}{INTERNAL_ID}" for w in (" ", "\t", " ", "　", "\n", " ", "  ", " \n ")] + [
            f"[p](creaite:item/ {INTERNAL_ID})", f"creaite⁦:item/{INTERNAL_ID}", f"creaite:/ /item/{INTERNAL_ID}",
            f"creaite: item/ {INTERNAL_ID}", f"creaite\u2066: item/ {INTERNAL_ID}", "creaite:\\note/7", "creaite:\\\\note/7"]
        got = self.py("print(json.dumps([client_leak.drop_item_links('ABC', 'Before. ' + t + ' After.') for t in "
                      f"{links!r}]))")
        for link, g in zip(links, got):
            self.assertEqual(g.split(), ["Before.", "After."], repr(link))
        kept = ["Text creaite: notes/ are kept", "See [p](creaite://item/ABC-A-002)."]
        self.assertEqual(self.py(f"print(json.dumps([client_leak.drop_item_links('ABC', t) for t in {kept!r}]))"), kept)
        self.assert_found([("See creaite:\\note/7 now.", "a creaite link a client can't open"),
                           ("See creaite:\\\\note/7 now.", "a creaite link a client can't open")], (0, 1))


MARKER = "it holds an internal-only marker"


class TheReviewOf62593f6(Base):
    """#127 round 5 (review of 62593f6): every default-ignorable character is unseen, assigned or not, and the braille blank is a
    space; combining and enclosing marks hide no ID, marker or name; decoded text keeps its punctuation for the marker; more ways
    of writing a name and a backslash-escaped ID."""
    gate, assert_found = TheReviewOf55967e3.gate, TheReviewOf55967e3.assert_found

    def test_every_default_ignorable_character_is_unseen(self):
        cps = [cp for a, b in ((0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5),
                               (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164),
                               (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3),
                               (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF)) for cp in (a, (a + b) // 2, b)]
        cps += [0xE0080, 0xE0100, 0xE01EF, 0xE01F0]               # the reviewer's, and the variation selectors supplement
        got = self.py(f"print(json.dumps([edit_ai.unseen('a' + chr(cp) + 'b') for cp in {cps + [0x2800]!r}]))")
        self.assertEqual(got[:-1], ["ab"] * len(cps), [hex(c) for c, g in zip(cps, got) if g != "ab"])
        self.assertEqual(got[-1], "a b")                          # the braille blank draws as a space
        self.assert_found([(f"Waiting on Quen{chr(0xFFF0)}tin Marlow.", NAMED), (f"Blocked by ABC-A-0{chr(0xE0080)}04.", HIDDEN),
                           (f"Note: internal{chr(0xE01F0)}-only.", MARKER), (f"Waiting on Quentin{chr(0x2800)}Marlow.", NAMED),
                           (f"Blocked by ABC-A-0{chr(0xE0100)}04.", HIDDEN)])
        got = self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', 'Before. creaite' + chr(0xFFF0) + "
                      f"':item/{INTERNAL_ID} After.')))")
        self.assertEqual(got.split(), ["Before.", "After."])

    def test_combining_marks_hide_no_id_marker_or_name(self):
        self.assert_found([(f"Blocked by ABC-A-0{chr(0x301)}04.", HIDDEN), (f"Note: internal{chr(0x336)}-only.", MARKER),
                           (f"Blocked by ABC-A-0{chr(0x20DD)}04.", HIDDEN), (f"Waiting on Quen{chr(0x20DD)}tin Marlow.", NAMED)])
        hindi = "\u0905\u0928\u093f\u0932 \u0915\u0941\u092e\u093e\u0930"          # a name whose vowels are marks, both folded
        got = self.py("print(json.dumps([sorted(client_leak.named(t, [" + repr(hindi) + ", 'Zo\u00eb Kent'])) for t in "
                      + repr([f"Met {hindi} today.", "Met Zoe\u0308 Kent today.", "Met Zoe Kent today.", "Met Zo Kent."]) + "]))")
        self.assertEqual(got, [[hindi], ["Zo\u00eb Kent"], ["Zo\u00eb Kent"], []])
        got = self.py("import sqlite3\nc = sqlite3.connect('system/tracker.db')\n"   # a test vault: an accented health reason
                      "c.execute(\"UPDATE projects SET health_reason = 'R\u00e9sum\u00e9 d\u00e9lay\u00e9' WHERE code = 'ABC'\")\n"
                      "c.commit()\nprint(json.dumps(drafts.internal_findings(client_leak.connect(), 'ABC', "
                      "'The R\u00e9sum\u00e9 d\u00e9lay\u00e9.')))")
        self.assertEqual(got, ["the internal health reason"])

    def test_decoded_text_keeps_its_punctuation_for_the_marker(self):
        oks = ["Costs are internal, only the licence is external &amp; billed separately.",   # "internal, only" isn't the marker
               "See https://client.example.com/documents%2Fplan for the plan."]           # an external page's path isn't creaite's
        for got in self.gate(oks).values():
            self.assertEqual(got, [[], [], []])
        self.assert_found([("Note: health%5Fdiff.", MARKER), ("Note: internal%2Donly.", MARKER)])
        link = "See [plan](https://client.example.com/documents/plan) and more"         # the documents/ safeguard, decoded too
        self.assertEqual(self.findings(f"Progress. {link} &amp; less."), [])
        got = self.py("d = report_doc.client_doc('ABC')\n"                 # an encoded marker where the reason may stand
                      "next(s for s in d['sections'] if s.get('type') == 'health')['text'] = 'Behind plan. internal%2Donly.'\n"
                      "print(json.dumps(client_leak.findings(d)))")
        self.assertIn(MARKER, got)

    def test_a_name_however_written_and_a_backslash_escaped_id(self):
        self.assert_found([(t, NAMED) for t in (
            "Waiting on Quentin J. Marlow.", "Waiting on Quentin J Marlow.", "Waiting on Marlow Quentin.", "Waiting on Quentin/Marlow.",
            "Waiting on Quentin|Marlow.", "Waiting on Quentin;Marlow.", "Waiting on Quentin\\Marlow.")] + [
            ("Blocked by ABC\\-A\\-004.", HIDDEN)])
        got = self.py("print(json.dumps([sorted(client_leak.named(t, [\"Ada O'Neill\", 'Ida O\u2019Hare', 'Al Mortimer', 'Al Lee', "
                      "'Quentin Marlow'])) "
                      "for t in ('Met Ada O\u2019Neill.', \"Met Ida O'Hare.\", 'see almortimer', 'Al Mortimer', 'Lee Al', "
                      "'Quentin Smarlow', 'Quentin a. Marlowe')]))")
        self.assertEqual(got, [["Ada O'Neill"], ["Ida O\u2019Hare"], [], ["Al Mortimer"], [], [], []])   # controls: short, longer



class TheReviewOfce5d66b(Base):
    """#127 round 6 (review of ce5d66b): control characters and noncharacters are read as Word draws them (gone, or a line break
    where a Word export breaks the line), and docx_tools.esc never writes one XML doesn't allow."""
    gate, assert_found = TheReviewOf55967e3.gate, TheReviewOf55967e3.assert_found

    def test_control_characters_and_noncharacters_are_unseen(self):
        gone = ["\x00", "\x07", "\x1b", "\x1f", "\x7f", "\x80", "\x9d", "\ufdd0", "\ufdef", "\ufffe", "\uffff", "\U0001fffe",
                "\U0010ffff"]
        breaks = ["\x0b", "\x0c", "\x1c", "\x1e", "\x85"]
        cases = gone + breaks + ["\t", "\r"]
        got = self.py(f"print(json.dumps([edit_ai.unseen('a' + c + 'b') for c in {cases!r}]))")
        self.assertEqual(got, ["ab"] * len(gone) + ["a\nb"] * len(breaks) + ["a\tb", "a\rb"])
        self.assert_found([("Waiting on Quen\x9dtin Marlow.", NAMED), ("Waiting on Quen\x07tin Marlow.", NAMED),
                           ("Note: internal\x9d-only.", MARKER), ("Note: internal\x07-only.", MARKER),
                           ("Blocked by ABC-A-0\ufdd004.", HIDDEN), ("Blocked by ABC-A-0\x0004.", HIDDEN)])

    def test_esc_writes_only_characters_xml_allows(self):
        got = self.py("import docx_tools, xml.etree.ElementTree as ET\nout = []\n"
                      "for c in ['\\x00', '\\x07', '\\x0b', '\\x0c', '\\x1f', '\\ufffe', '\\uffff', '\\ud800']:\n"
                      "    x = '<t>' + docx_tools.esc('a' + c + 'b<&>') + '</t>'\n"
                      "    out.append(ET.fromstring(x.encode('utf-8')).text)\n"
                      "print(json.dumps(out))")
        self.assertEqual(got, ["ab<&>", "ab<&>", "a b<&>", "a b<&>", "ab<&>", "ab<&>", "ab<&>", "ab<&>"])


    def test_common_word_names_are_not_read_in_prose(self):
        """Finding 1: the surname first without a comma counts only with both words capitalised, and an initial only in capitals."""
        reg = ["Will Price", "Grace Day", "Mark Field", "Rose Hill", "Quentin Marlow"]
        prose = ["The price will rise after the contract review.", "A 30 day grace period applies.", "Field mark-up is due on Friday.",
                 "Hill rose to the occasion.", "Will a price cap apply?", "Waiting on Quentin j. Marlow.", "Waiting on marlow quentin."]
        names = ["Waiting on Marlow, Quentin.", "Waiting on Quentin J. Marlow.", "Waiting on MARLOW Quentin.",
                 "Waiting on Marlow Quentin.", "Waiting on quentin marlow.", "Price Will signed it."]
        got = self.py(f"print(json.dumps([sorted(client_leak.named(t, {reg!r}, every=True)) for t in {prose + names!r}]))")
        self.assertEqual(got, [[]] * len(prose) + [["Quentin Marlow"]] * 5 + [["Will Price"]])

    def test_a_comma_reads_the_same_decoded_and_every_name_is_reported(self):
        """Finding 5: "Quentin,Marlow" is a name and "Quentin, Marlow" a list, with an &amp; elsewhere or not; every register name
        that matches is reported on the gate's paths (Quentin and Quentin Marlow)."""
        got = self.py("print(json.dumps([sorted(client_leak.named(client_leak.with_decoded(t), ['Quentin Marlow'])) for t in "
                      "('Waiting on Quentin,Marlow.', 'Waiting on Quentin,Marlow &amp; co.', 'Waiting on Quentin, Marlow.', "
                      "'Waiting on Quentin, Marlow &amp; co.')]))")
        self.assertEqual(got, [["Quentin Marlow"], ["Quentin Marlow"], [], []])
        got = self.py("con = client_leak.connect()\n"
                      "client_leak.people = lambda con, code, blocking=None: (set(), {'Quentin', 'Quentin Marlow'})\n"
                      "edit_ai._register_names = lambda: ['Quentin', 'Quentin Marlow']\n"
                      "t = 'Waiting on Quentin; Marlow.'\n"
                      "print(json.dumps([client_leak.name_findings(con, 'ABC', t), edit_ai.client_problems('ABC', t), "
                      "sorted(edit_ai.names(t, ['Quentin', 'Quentin Marlow'])), edit_ai.client_problems('ABC', t, t)]))")
        self.assertEqual([sorted(f.split(" is")[0] for f in got[0]), sorted(f.split(" isn")[0] for f in got[1] if "named" in f),
                          got[2]], [["Quentin", "Quentin Marlow"], ["Quentin", "Quentin Marlow"], ["Quentin Marlow"]])
        self.assertEqual([f for f in got[3] if "named" in f], [])          # the original names both: neither is new

    def test_sentence_punctuation_keeps_the_marker_apart_and_spaced_marks_join_it(self):
        """Findings 3 and 4: in the words form "internal. Only" (any of . ; ! ? : with an &amp; elsewhere) is prose; "internal ; only",
        "internal . only" and "internal:only" are the marker with or without one; an underscore joins it when decoded."""
        oks = ["Planning is internal. Only their PMO attends &amp; signs.", "Costs are internal; only the licence &amp; support.",
               "Planning is internal! Only the PMO &amp; sponsor.", "Is it internal? Only the PMO &amp; sponsor know.",
               "Costs are internal: only the licence &amp; support are external.", "Costs are internal; only the licence is billed.",
               "Planning is internal. Only their PMO attends."]
        for text, got in self.gate(oks).items():
            self.assertEqual(got, [[], [], []], text)
        self.assert_found([(t, MARKER) for t in ("Note: internal ; only.", "Note: internal . only.", "Note: internal:only.",
                                                 "Note: internal ; only &amp; more.", "Note: internal:only &amp; more.")])
        self.assert_found([("Note: internal_only &amp; more.", MARKER)], kinds=(0, 1))

    def test_every_apostrophe_folds(self):
        got = self.py("print(json.dumps([sorted(client_leak.named(t, [\"Ada O'Neill\"])) for t in "
                      "('Met Ada O\u2018Neill.', 'Met Ada O\u02bcNeill.', 'Met Ada O\u2032Neill.', 'Met Ada O\u2019Neill.')]))")
        self.assertEqual(got, [["Ada O'Neill"]] * 4)


    def test_emphasis_marks_hide_no_marker_wording_or_id(self):
        """The coordinator's finding: the exports take Markdown's marks off ("internal _only_" shows "internal only"), so the gate
        reads the text as they show it too (client_leak.as_shown), nested marks, strike-through and backticks included."""
        wraps = ["_{}_", "*{}*", "**{}**", "~~{}~~", "`{}`", "**_{}_**", "**~~{}~~**", "_**{}**_"]
        cases = [(f"Note: internal {w.format('only')} now.", MARKER) for w in wraps]
        cases += [(f"Note: {w.format('internal')}-only now.", MARKER) for w in wraps]
        cases += [(f"Blocked by {w.format(INTERNAL_ID)} now.", HIDDEN) for w in ("~~{}~~", "**_{}_**", "`{}`")]
        self.assert_found(cases)
        wording = [f"Note: Line up the {w.format('quiet')} audit." for w in wraps]
        for text, got in self.gate(wording).items():
            for k in range(3):
                self.assertTrue(any("wording appears" in f for f in got[k]), (text, k, got[k]))
        got = self.py("d = report_doc.client_doc('ABC')\n"                 # a marker where the reason may stand
                      "next(s for s in d['sections'] if s.get('type') == 'health')['text'] = 'Behind plan. internal ~~only~~.'\n"
                      "print(json.dumps(client_leak.findings(d)))")
        self.assertIn(MARKER, got)
        for got in self.gate(["The *quick* review and the _snake_case_ field are **done**."]).values():
            self.assertEqual(got, [[], [], []])                          # control: emphasis on client-safe words


class TheReviewOfc39f6c4(Base):
    """#127 round 7 (review of c39f6c4): no check reads from one form of a text into the next (as written, as shown, decoded); a
    shorter name inside an allowed one is not someone else; an initial in any script; one rule for the punctuated marker; emphasis
    inside a word and nesting of any depth read as the HTML and PDF exports show them; a lone surrogate hides nothing."""
    gate, assert_found = TheReviewOf55967e3.gate, TheReviewOf55967e3.assert_found

    def assert_clean(self, texts, gate=None):
        for text, got in (gate or self.gate)(texts).items():
            self.assertEqual(got, [[], [], []], text)

    def gate_as_is(self, texts):
        """gate, with each text as the whole summary (no "Progress. " before it): where it starts matters here."""
        return dict(zip(texts, self.py(
            "con = client_leak.connect()\nout = []\n"
            f"for t in {texts!r}:\n"
            "    d = report_doc.client_doc('ABC')\n"
            "    next(s for s in d['sections'] if s['id'] == 'summary')['text'] = t\n"
            "    out.append([client_leak.findings(d), client_leak.plain_findings(con, 'ABC', t), edit_ai.client_problems('ABC', t)])\n"
            "print(json.dumps(out))")))

    def test_no_check_reads_across_two_forms_of_a_text(self):
        """Finding 1: the as-written text ends "…internal", its shown or decoded copy starts "Only…": not the marker; nor a name
        ending one form and starting the next. The marker hidden by emphasis is still found."""
        self.assert_clean(["Only _two_ reviewers are needed; the rest of the review is internal",
                           "Only **approved** figures go to the board; drafts stay internal",
                           "Only the `export` file changes. The rest stays internal",
                           "Only A &amp; B go out; the rest stays internal",
                           "Marlow said **yes** to Quentin", "Marlow said yes &amp; thanks to Quentin"], gate=self.gate_as_is)
        self.assert_found([("Note: internal _only_.", MARKER), ("Note: _internal-only_.", MARKER)])
        for text, got in self.gate(["See creaite:item/\nABC-A-004 now."]).items():     # the join is never shown in a finding
            self.assertTrue(got[0] and got[1], text)
            self.assertFalse([f for k in got for f in k if "qqjoinqq" in f], got)

    def test_a_shorter_name_inside_an_allowed_one_is_not_another_person(self):
        """Finding 2: Sam Patel may be shown; "Sam" is another person's alias. "Sam Patel will run it" names only Sam Patel; a Sam
        standing on its own still counts."""
        got = self.py("client_leak.people = lambda con, code, blocking=None: ({'Sam Patel'}, set())\n"
                      "edit_ai._register_names = lambda: ['Sam Patel', 'Sam Jones', 'Sam']\n"
                      "print(json.dumps([[f for f in edit_ai.client_problems('ABC', t) if 'named' in f] for t in "
                      "('Sam Patel will run the rehearsal.', 'Waiting on Sam Patel.', 'Sam Patel and Sam will run it.')]))")
        self.assertEqual(got, [[], [], ["Sam isn't named in the text"]])

    def test_a_list_separator_inside_an_allowed_name_hides_no_one(self):
        """Round 8: an allowed name's match joined by ; / | or a full stop after a word is two people, so it hides neither."""
        texts = ["We met Sam. Patel will run the rehearsal.", "Thanks to Sam; Patel signs off.", "Ask Sam / Patel for it.",
                 "Ask Sam | Patel for it.", "Sam; Patel; Khan attend.", "Ali; Khan attend.", "Sam Patel will run the rehearsal.",
                 "Sam-Patel will run it.", "Sam P. Patel will run it.", "Sam Patel and Sam will run it."]
        got = self.py("client_leak.people = lambda con, code, blocking=None: ({'Sam Patel', 'Ali Khan'}, set())\n"
                      "edit_ai._register_names = lambda: ['Sam Patel', 'Ali Khan', 'Sam', 'Patel', 'Khan', 'Ali']\n"
                      f"print(json.dumps([sorted(f.split(' isn')[0] for f in edit_ai.client_problems('ABC', t) if 'named' in f) "
                      f"for t in {texts!r}]))")
        self.assertEqual(got, [["Patel", "Sam"]] * 4 + [["Khan", "Patel", "Sam"], ["Ali", "Khan"], [], [], [], ["Sam"]])

    def test_an_initial_in_any_script(self):
        """Finding 3: a capital initial outside Latin-1, and a single letter in a script with no case, between a name's words."""
        reg = ["Quentin Marlow", "\u0418\u0432\u0430\u043d \u041f\u0435\u0442\u0440\u043e\u0432", "\u738b \u660e"]
        texts = ["Waiting on Quentin \u0141. Marlow.", "Waiting on \u0418\u0432\u0430\u043d \u0411. \u041f\u0435\u0442\u0440\u043e\u0432.",
                 "\u738b \u5c0f \u660e", "Waiting on Quentin \u0142. Marlow.", "Will a price cap apply?"]
        got = self.py(f"print(json.dumps([sorted(client_leak.named(t, {reg + ['Will Price']!r}, every=True)) for t in {texts!r}]))")
        self.assertEqual(got, [[reg[0]], [reg[1]], [reg[2]], [], []])

    def test_an_ideographic_character_is_an_initial_only_in_an_ideographic_name_or_with_a_dot(self):
        """Round 8: "Mark 中 Field" and "Mark の Field" are not Mark Field (a CJK or kana character is a word, not an initial),
        "Mark 中. Field" is; between the words of a name in that script it may still stand alone ("王 小 明" for 王 明)."""
        reg = ["Mark Field", "王 明", "山田 太郎"]
        texts = ["Mark 中 Field items.", "Mark の Field items.", "Mark 中. Field items.", "王 小 明",
                 "山田 の 太郎", "Mark ب Field items."]
        got = self.py(f"print(json.dumps([sorted(client_leak.named(t, {reg!r}, every=True)) for t in {texts!r}]))")
        self.assertEqual(got, [[], [], [reg[0]], [reg[1]], [reg[2]], [reg[0]]])

    def test_one_rule_for_the_punctuated_marker(self):
        """Finding 4: up to three of . : ; , with no space is the marker, unless "Only" starts a sentence or the word runs on into a
        file name, domain or address; with a space before, only when nothing but punctuation follows "only"."""
        self.assert_clean(["See internal.only.yaml for it.", "Host internal.only.example.org is up.",
                           "Mail internal.only@example.com today.", "Keep it internal.Only the totals go.",
                           "Costs are internal : only licences go.", "Note: internal ; Only the totals."])
        self.assert_found([(f"Note: {t}.", MARKER) for t in ("internal ; only", "internal . only", "internal:only", "internal;only",
                                                             "internal,only", "internal::only", "internal..only", "internal;;only",
                                                             "INTERNAL.ONLY")])

    def test_the_marker_exceptions_need_a_sentence_or_a_lower_case_run_on(self):
        """Round 8: "Only" starts a sentence only with a space and a lower-case word after it, and a file name, domain, address or
        path runs on only in lower case (a path only inside one); a marker standing alone as a status is the marker."""
        self.assert_found([(t, MARKER) for t in (
            "Internal.Only", "Internal:Only", "Internal;Only", "INTERNAL:Only", "Note: internal.Only.", "**Internal.Only**",
            "Status: internal . Only", "Note: internal ;\nOnly", "INTERNAL.ONLY.DRAFT", "Label: internal.only.Do not forward.",
            "internal.only.Final", "Status: internal:only/draft", "Status: internal.only/v2", "Note: internal.only\\draft",
            "Status: internal ; only do not forward", "Keep it internal:Only.", "Keep it internal ; Only.",
            "Note: INTERNAL.ONLY@ACME", "Note: internal.only@")])
        self.assert_clean(["Config lives in internal.only.yaml in the repo.", "Point DNS at internal.only.example.org today.",
                           "Write to internal.only@example.com for access.", "Keep it internal. Only the totals go.",
                           "The path is /srv/internal.only/data on the server.", "Version internal.only.v2 is the public label.",
                           "Item: Internal . Only the board signs.", "Scope remains internal ; only the training is shared.",
                           "Data is internal:Only aggregated data leaves.", "The path internal.only/config holds it."])
        bare = ["internal.only\\draft", "Internal.Only", "INTERNAL.ONLY.DRAFT", "internal.only.Final", "Status: internal . Only"]
        self.assertEqual(self.py(f"print(json.dumps([client_leak.marked(t) for t in {bare!r}]))"), [True] * len(bare))

    def test_emphasis_inside_a_word_and_any_depth_of_nesting(self):
        """Finding 5: the HTML and PDF exports draw emphasis inside a word ("inter*nal*-only" shows "internal-only"), and nesting
        is undone until nothing changes; an underscore inside a word and "2*3*4" stay as they are."""
        self.assert_found([("Note: inter*nal*-only.", MARKER), ("Note: inter****nal-only.", MARKER),
                           ("Note: ~~**__*_internal_*__**~~-only.", MARKER), ("Blocked by ABC-A-0*0*4 now.", HIDDEN),
                           ("Waiting on Quen*tin* Marlow.", NAMED)])
        self.assert_found([(t, MARKER) for t in ("Note: inter~~nal~~-only.", "Note: inter~~nal-only.", "Note: in~~ter~~nal~~-only.",
                                                 "Note: inter~~nal~~~~-only.", "Note: inter~~nal~~-o~~nly")])   # round 8: ~~ too
        for text, got in self.gate(["Note: Line up the q*uie*t audit."]).items():
            for k in range(3):
                self.assertTrue(any("wording appears" in f for f in got[k]), (text, k, got[k]))
        self.assert_clean(["Ratio 2*3*4 holds.", "The snake_case_field and my_internal_value are done."])

    def test_the_shown_form_is_worked_out_once(self):
        """Round 8, speed: a text with no emphasis inside a word is shown once, not twice, and the same text read by several
        checks is worked out once; the result is the same."""
        got = self.py("calls = []\nreal = client_leak._plain_shown\n"
                      "client_leak._plain_shown = lambda t: calls.append(t) or real(t)\n"
                      "a = client_leak.as_shown('Note: **bold** text.')\nb = client_leak.as_shown('Note: **bold** text.')\n"
                      "c = client_leak.as_shown('Note: inter*nal*-only.')\nn = len(calls)\n"
                      "client_leak.named('Quen*tin* Marlow', ['Quentin Marlow'])\nclient_leak.named('Quen*tin* Marlow', ['Quentin Marlow'])\n"
                      "print(json.dumps([n, a == b, c.split(client_leak.JOIN), client_leak._words_shown.cache_info().hits]))")
        self.assertEqual(got, [3, True, ["Note: inter*nal*-only.", "Note: internal-only."], 1])

    def test_a_lone_surrogate_is_unseen(self):
        """Finding 6: docx_tools.esc drops a lone surrogate, so the check does too."""
        self.assertEqual(self.py("print(json.dumps(edit_ai.unseen('a\\ud800b\\udfffc')))"), "abc")
        self.assert_found([("Waiting on Quen\ud800tin Marlow.", NAMED), ("Blocked by ABC-A-0\udfff04.", HIDDEN),
                           ("Note: internal\ud800-only.", MARKER)])


if __name__ == "__main__":
    unittest.main()
