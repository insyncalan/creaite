"""#122 step C: work-item links in Current state on the client path (report_doc, report, docx_tools; with v2.1.0 P3's leak check).

Run: python3 dev/tests/test_client_item_links.py   (skipped where client_leak.py or report_doc.client_item_links is not in the tree: they land with #123 / v2.1.0)
A Current state may link `[ABC-A-001 · Action: title](creaite:item/ABC-A-001)`. Taken into a client report, a link to an item that is
not client-visible must not get through, whatever its words: the leak check reads a section's words with the address cut off
(creaite_doc._plain), so a link whose words were edited ('the vendor thing') would pass it, and its address stay in the stored
text. report_doc.client_item_links takes such a link out whole (words and address) before the check; a link to a client-visible item
is kept as it is.

Routes tested: the client document built from a Current state (client_leak.findings), save_draft (the dashboard's edit), approve
(stage_client), the export check (client_check.left_out), the Word draft's check (review.client_findings: text only), the
redraft request (drafts.report_request), what a client draft is shown (report.current_context, drafts.client_report_facts,
status_facts) and Word (docx_tools).
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
try:
    import client_leak  # noqa: F401
    import report_doc
    if not hasattr(report_doc, "client_item_links"):          # the gate is here but the link wiring (Cap's #123 follow-up) is not
        raise ImportError("report_doc.client_item_links")
    import test_client_leak as T
    import test_reports as R
    BASE = T.Base
except ImportError:                                           # this tree has no client gate yet
    T = R = None
    BASE = unittest.TestCase

INTERNAL = "ABC-A-001"                                        # Escalate data access: not client-visible
SEEN = "ABC-A-002"                                            # Sign the statement of work: client-visible
IWORDS = "ABC-A-001 · Action: Internal vendor thing"
SWORDS = "ABC-A-002 · Action: Sign the statement of work"
ILINK = f"[{IWORDS}](creaite:item/{INTERNAL})"
SLINK = f"[{SWORDS}](creaite:item/{SEEN})"
EDITED = f"[the vendor thing we discussed](creaite:item/{INTERNAL})"      # the words no longer name the item
DRAFT = "system/staging/drafts/2026-10-09 Client report - Example Programme (Example Client Ltd).html"


def state(link):
    return f"### Position\n\nWaiting on {link} before {SLINK} can close."


@unittest.skipIf(T is None, "client_leak.py is not in this tree")
class ClientPath(BASE):
    def setUp(self):
        super().setUp()
        self.approve_week()

    def put_state(self, text):
        m = self.v.root / R.ABC / "CLAUDE.md"
        m.write_text(m.read_text(encoding="utf-8").replace("Build is two weeks behind.", text), encoding="utf-8")

    def doc_pane(self, code):
        return self.py(code + "\nprint(json.dumps(next(s for s in d['sections'] if s['id'] == 'current_state')['panes'][0]['text']))")

    def approve(self, text):
        """(returncode, stderr) of building a client report whose Current state is `text`, saving it and approving it."""
        r = self.py(f"d = report_doc.client_doc('ABC', spec={{'current_state': {text!r}}})\n"
                    "r = report_doc.save_draft(d)\nreport_doc.stage_client(r['path'])", ok=False)
        return r

    # ---- a link whose words name the item: the gate already finds it, on every route --------------------------------------

    def test_the_gate_finds_a_link_that_names_the_item_on_every_route(self):
        got = self.py(f"""import client_check, drafts, review, tracker
con = tracker.connect()
st = {state(ILINK)!r}
d = report_doc.client_doc('ABC')
next(s for s in d['sections'] if s['id'] == 'current_state')['panes'][0]['text'] = st        # as an edit that skipped the filter
res = {{'findings': client_leak.findings(d), 'left_out': client_check.left_out(d)['findings'],
        'word': client_leak.text_findings(con, 'ABC', st)}}
try:
    drafts.report_request(con, {{'code': 'ABC', 'report': 'client', 'section': 'current_state', 'text': st, 'action': 'polish'}})
    res['redraft'] = 'allowed'
except Exception as e:
    res['redraft'] = str(e)
print(json.dumps(res))""")
        self.assertIn(f"{INTERNAL} isn't client-visible but its ID appears", got["findings"])       # the document check (approve runs it)
        self.assertIn(f"{INTERNAL} isn't client-visible but its ID appears", got["left_out"])       # the export check
        self.assertTrue(any(INTERNAL in f for f in got["word"]), got["word"])           # a Word draft is checked as raw text
        self.assertIn("isn't client-safe", got["redraft"])                              # the redraft request refuses the raw section

    def test_approve_refuses_a_link_that_reached_the_draft_some_other_way(self):
        # a draft file written without save_draft (the filter is not in its way): stage_client refuses it, edited words or not
        for link in (ILINK, EDITED):
            r = self.py(f"d = report_doc.client_doc('ABC')\n"
                        f"next(s for s in d['sections'] if s['id'] == 'current_state')['panes'][0]['text'] = {state(link)!r}\n"
                        f"creaite_doc.save({DRAFT!r}, d, 'test', via='test')\nreport_doc.stage_client({DRAFT!r})", ok=False)
            self.assertNotEqual(r.returncode, 0, link)
            self.assertIn("possible internal content", r.stderr)
            self.assertIn(INTERNAL, r.stderr)
            (self.v.root / DRAFT).unlink()

    # ---- the words were edited: only the address names the item --------------------------------------------------------------

    def test_a_link_with_edited_words_is_taken_out_whole_and_the_client_visible_one_stays(self):
        for text in (state(EDITED), state(ILINK)):
            pane = self.doc_pane(f"d = report_doc.client_doc('ABC', spec={{'current_state': {text!r}}})")
            self.assertNotIn(INTERNAL, pane)
            self.assertNotIn("vendor thing", pane)
            self.assertIn(f"before {SLINK} can close.", pane)                           # the client-visible link, words and all

    def test_save_draft_and_approve_keep_an_edited_internal_link_out_of_the_filed_report(self):
        r = self.approve(state(EDITED))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.v.at("apply", script="tracker.py")
        filed = (self.v.root / R.ABC / "reports/2026-10-09 Client report - Example Programme (Example Client Ltd).html").read_text("utf-8")
        self.assertNotIn(INTERNAL, filed)
        self.assertNotIn("vendor thing", filed)
        self.assertIn(SWORDS, filed)

    def test_an_edit_in_the_dashboard_is_cleaned_by_save_draft(self):
        got = self.py(f"d = report_doc.client_doc('ABC')\n"
                      f"next(s for s in d['sections'] if s['id'] == 'current_state')['panes'][0]['text'] = {state(EDITED)!r}\n"
                      "r = report_doc.save_draft(d)\n"
                      "print(json.dumps({'removed': r['removed'], 'file': open(r['path']).read() if False else "
                      "creaite_doc.read(r['path'])['sections']}))")
        self.assertTrue(any(INTERNAL in x for x in got["removed"]), got["removed"])
        self.assertNotIn(INTERNAL, json.dumps(got["file"]))

    # ---- what a client draft is shown ------------------------------------------------------------------------------------------

    def test_a_client_draft_is_not_shown_the_internal_link_and_the_internal_draft_is(self):
        self.put_state(state(EDITED))
        got = self.py("import report\n"
                      "print(json.dumps({'client': report.current_context('ABC', audience='client'),"
                      " 'internal': report.current_context('ABC', audience='internal')}))")
        self.assertNotIn(INTERNAL, got["client"])
        self.assertNotIn("vendor thing", got["client"])
        self.assertIn(SWORDS, got["client"])
        self.assertIn(INTERNAL, got["internal"])                                        # internal readers keep the whole text

    def test_the_facts_a_client_draft_rests_on_never_hold_the_link(self):
        self.put_state(state(ILINK))
        got = self.py("import drafts, status_facts, tracker\n"
                      "src = drafts.client_report_facts(tracker.connect(), 'ABC', '2026-10-09')[0]\n"
                      "f = status_facts.facts('ABC', '2026-10-05', '2026-10-09', 'client')\n"
                      "print(json.dumps(json.dumps(src) + json.dumps(f)))")
        self.assertNotIn(INTERNAL, got)
        self.assertNotIn("Internal vendor thing", got)

    # ---- Word shows the words only ---------------------------------------------------------------------------------------------

    def test_word_shows_the_words_of_a_link_and_drop_item_links_is_exact(self):
        got = self.py(f"import docx_tools\nst = {state(ILINK)!r}\n"
                      "print(json.dumps({'runs': [x[0] for x in docx_tools.md_runs(st)],"
                      " 'dropped': docx_tools.drop_item_links(st, lambda i: i != 'ABC-A-001'),"
                      " 'kept': docx_tools.drop_item_links(st, lambda i: True)}))")
        self.assertIn(IWORDS, got["runs"])
        self.assertEqual(got["dropped"], f"### Position\n\nWaiting on before {SLINK} can close.")
        self.assertEqual(got["kept"], state(ILINK))


class DropItemLinks(unittest.TestCase):
    """The helper on its own (docx_tools.drop_item_links): no vault, so it runs in every tree."""

    def test_a_refused_link_goes_whole_with_the_space_before_it_and_a_kept_link_stays(self):
        import docx_tools
        st = state(ILINK)
        self.assertEqual(docx_tools.drop_item_links(st, lambda i: i != INTERNAL), f"### Position\n\nWaiting on before {SLINK} can close.")
        self.assertEqual(docx_tools.drop_item_links(st, lambda i: True), st)
        self.assertEqual(docx_tools.drop_item_links(state(EDITED), lambda i: i == SEEN), f"### Position\n\nWaiting on before {SLINK} can close.")
        self.assertEqual(docx_tools.drop_item_links("plain [a link](https://example.com) stays", lambda i: False), "plain [a link](https://example.com) stays")
        self.assertEqual(docx_tools.drop_item_links(None, lambda i: False), "")


if __name__ == "__main__":
    unittest.main()
