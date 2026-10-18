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
    drafts.report_request(con, {{'code': 'ABC', 'report': 'client', 'section': 'current_state', 'text': st, 'action': 'polish',
                                 'document': {{'kind': 'client', 'code': 'ABC', 'week_ending': '2026-10-09'}}}})
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

    # ---- #123: hostile, and failing closed ----------------------------------------------------------------------------------

    def internal_rows(self):
        """[(ID, owner, title)] of every item of ABC a client report may not show (the controls: they are real rows)."""
        return self.py("import tracker, client_leak\ncon = tracker.connect()\nb = client_leak.blocking_labels(con)\nout = []\n"
                       "for t, o, w in (('actions', 'owner', 'description'), ('raid', 'owner', 'description'), "
                       "('decisions', 'made_by', 'decision')):\n"
                       "    for i, ow, tt in con.execute(f'SELECT id, {o}, {w} FROM {t} WHERE project = ?', ('ABC',)):\n"
                       "        if client_leak.item_problem(con, i, b):\n"
                       "            out.append([i, ow or '', tt or ''])\n"
                       "print(json.dumps(out))")

    def test_every_text_of_a_saved_client_draft_loses_an_internal_link_in_any_form(self):
        rows = self.internal_rows()
        self.assertIn(INTERNAL, [r[0] for r in rows])
        forms = [f"[{r[0]} · {r[2]}](creaite:item/{r[0]})" for r in rows] + [
            f"[the thing](CREAITE:item/{INTERNAL})", f"[the thing](creaite:item/{INTERNAL.lower()})",
            f"[the thing](creaite%3Aitem/{INTERNAL})", f"<a href=\"creaite:item/{INTERNAL}\">the thing</a>"]                  # (a bare address: refused, below)
        hostile = "Plan. " + " ".join(forms) + f" Then {SLINK} closes."
        got = self.py(f"d = report_doc.client_doc('ABC', spec={{'summary': {hostile!r}, 'current_state': {hostile!r}}})\n"
                      f"for s in d['sections']:\n"
                      f"    for r in s.get('rows') or []:\n"
                      f"        r['cells'] = {{k: (v + ' ' + {hostile!r}) for k, v in r['cells'].items()}}\n"
                      "r = report_doc.save_draft(d)\n"
                      "print(json.dumps({'removed': r['removed'], 'saved': creaite_doc.read(r['path']), 'found': client_leak.findings("
                      "creaite_doc.read(r['path']))}))")
        saved = json.dumps(got["saved"]["sections"], ensure_ascii=False)
        for i, _owner, title in rows:
            self.assertNotIn(i, saved)
            self.assertNotIn(i.lower(), saved.lower())
            if len(title) > 8:
                self.assertNotIn(title, saved)
        self.assertNotIn("the thing", saved)
        self.assertIn(SWORDS, saved)                                                    # the client-visible link stays
        self.assertEqual(got["found"], [])                                              # the gate at the end agrees
        self.assertTrue(any(INTERNAL in x for x in got["removed"]), got["removed"])

    def test_each_form_of_an_internal_link_on_its_own_is_taken_out(self):
        forms = [f"[the thing](CREAITE:item/{INTERNAL})", f"[the thing](creaite%3Aitem/{INTERNAL})",
                 f"[the thing](creaite&#58;item/{INTERNAL})", f"[the thing](creaite\u200b:item/{INTERNAL})",
                 f"[the thing](creaite :item/{INTERNAL})"]
        got = self.py(f"out = []\nfor f in {forms!r}:\n"
                      "    d = report_doc.client_doc('ABC', spec={'summary': 'Plan. ' + f + ' Then.'})\n"
                      "    out.append(next(s for s in d['sections'] if s['id'] == 'summary')['text'])\n"
                      "print(json.dumps(out))")
        for f, text in zip(forms, got):
            self.assertNotIn(INTERNAL.lower(), text.lower(), f)
            self.assertNotIn("the thing", text, f)

    # ---- review of 6e5de819: never part-strip a link; leave a string with nothing taken out exactly as it was -----------------

    PARTS = ["Plan. [Absorb the phase one overrun\ninternally](creaite:item/ABC-D-008) Then.",
             "Plan. [Escalate data access to the client\nCIO](creaite:item/ABC-A-001) Then.",
             "Plan. [Confirm tester\nnames](creaite:item/ABC-A-004) Then.",
             "Plan. [the [x] thing](creaite:item/ABC-A-001) Then.",                                    # nested brackets
             "Plan. [the vendor thing][] Then.\n\n[the vendor thing]: creaite:item/ABC-A-001",      # a collapsed reference
             "Plan. [the vendor thing] Then.\n\n[the vendor thing]: creaite:item/ABC-A-001",        # a shortcut reference
             # delta re-review of 9908556a: spaces in the parentheses, labels Markdown matches loosely, balanced but wrong, HTML
             "Plan. [Escalate data access\nto the CIO]( creaite:item/ABC-A-001 ) Then.",
             "Plan. [Escalate data access\nto the CIO](   creaite:item/abc-a-001\t) Then.",
             "Plan. [Escalate data access to the\nCIO] Then.\n\n[Escalate data access to the CIO]: creaite:item/ABC-A-001",
             "Plan. [escalate DATA access  to the cio] Then.\n\n[Escalate data access to the CIO]: creaite:item/ABC-A-001",
             "Plan. [Escalate data access to the client CIO][r] Then.\n\n[r]:\n  creaite:item/ABC-A-001",
             "Plan. [Escalate data access to the client CIO][R] Then.\n\n[r]: creaite:item/ABC-A-001",
             "Plan. [Escalate data access to the\nCIO](creaite:item/ABC-A-001)[ see notes] Then.",
             "Plan. [Escalate data access to the\r\nCIO](creaite:item/ABC-A-001)[x] Then.",
             'Plan. <a href="creaite:item/ABC-A-001">Escalate data <b>access</b> to the client CIO</a> Then.',
             "Plan. <A HREF='creaite:item/ABC-A-001'>Escalate data <i>access</i>\nto the client CIO</a> Then.",
             "Plan. creaite:item/ABC-A-001 Then.",                                                     # a bare address: no words
             "Plan. [Escalate data access to the client CIO](creaite%3Aitem/ABC-A-001 ) Then.\n[x](creaite:item/ABC-A-001"]

    def test_a_link_that_cant_be_taken_out_whole_is_refused_and_never_filed(self):
        # end to end, as the page's Approve does it (report_server: save_draft, then stage_client): whatever save_draft lets
        # through, approve still refuses; nothing part-stripped is ever saved
        for text in self.PARTS:
            got = self.py(f"d = report_doc.client_doc('ABC')\n"
                          f"next(s for s in d['sections'] if s['id'] == 'summary')['text'] = {text!r}\n"
                          "try:\n    r = report_doc.save_draft(d)\nexcept report_doc.ReportError as e:\n"
                          "    print(json.dumps(['save refused', str(e)]))\n    raise SystemExit\n"
                          "saved = next(s for s in creaite_doc.read(r['path'])['sections'] if s['id'] == 'summary')['text']\n"
                          "try:\n    report_doc.stage_client(r['path'])\n    print(json.dumps(['staged', saved]))\n"
                          "except report_doc.ReportError as e:\n    print(json.dumps(['approve refused', saved]))")
            self.assertNotEqual(got[0], "staged", (text, got))
            if got[0] == "save refused":
                self.assertFalse((self.v.root / DRAFT).exists(), text)
                self.assertIn("couldn't be taken out whole", got[1])
            r = self.py(f"report_doc.client_doc('ABC', spec={{'current_state': {text!r}}})", ok=False)   # the spec route too
            self.assertNotEqual(r.returncode, 0, text)
            self.assertIn("ReportError", r.stderr)

    def test_the_second_check_refuses_a_hidden_items_wording_left_behind(self):
        # the first check (every hidden address inside a whole link) taken away: what is left still may not hold the item's words
        text = 'Plan. <a href="creaite:item/ABC-A-001">Escalate data access to the client CIO<b></b></a> Then.'
        r = self.py("report_doc._whole_or_refuse = lambda s, code, con: {'ABC-A-001'}\n"
                    f"d = report_doc.client_doc('ABC')\n"
                    f"next(s for s in d['sections'] if s['id'] == 'summary')['text'] = {text!r}\n"
                    "report_doc.save_draft(d)", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("couldn't be taken out whole", r.stderr)
        self.assertFalse((self.v.root / DRAFT).exists())

    def test_a_string_with_no_link_taken_out_is_kept_exactly(self):
        for text in ("Plan [phase 1] and (scope) [see](https://example.com/a) done.", "Rates: [a] b] [c (d) e).",
                     f"Paperwork: {SLINK}; [the plan][p]\n\n[p]: https://example.com/p",
                     f"Two lines\n[{SWORDS}](creaite:item/{SEEN}) and [x]",
                     "R&amp;D at creaite:item/ABC-A-002 and &lt;b&gt;x&lt;/b&gt;", "We use creaite: notes/ here, &amp; more",
                     f"Waiting on {SLINK}, R&amp;D &lt;b&gt;"):
            got = self.py(f"d = report_doc.client_doc('ABC')\n"
                          f"next(s for s in d['sections'] if s['id'] == 'summary')['text'] = {text!r}\n"
                          "r = report_doc.save_draft(d)\n"
                          "print(json.dumps([r['removed'], next(s for s in creaite_doc.read(r['path'])['sections'] "
                          "if s['id'] == 'summary')['text']]))")
            self.assertEqual(got, [[], text], text)
            (self.v.root / DRAFT).unlink()

    def test_client_item_links_fails_closed_when_the_tracker_cant_be_read(self):
        r = self.py("import client_leak\n"
                    "def boom(*a, **k): raise RuntimeError('tracker unreadable')\n"
                    "d = report_doc.client_doc('ABC')\n"
                    f"next(s for s in d['sections'] if s['id'] == 'current_state')['panes'][0]['text'] = {state(EDITED)!r}\n"
                    "client_leak.drop_item_links = boom\n"
                    "report_doc.save_draft(d)", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ReportError", r.stderr)
        self.assertFalse((self.v.root / DRAFT).exists())                                # nothing saved
        r = self.py("import client_leak\n"
                    "def boom(*a, **k): raise RuntimeError('tracker unreadable')\n"
                    "client_leak.drop_item_links = boom\n"
                    f"report_doc.client_doc('ABC', spec={{'current_state': {state(EDITED)!r}}})", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ReportError", r.stderr)

    def test_the_client_place_sends_no_internal_id_owner_or_title_and_none_when_the_items_cant_be_read(self):
        rows = self.internal_rows()
        got = self.py("import edit_ai, client_leak\n"
                      "ok = edit_ai.project_facts('ABC', client=True)\n"
                      "def boom(*a, **k): raise RuntimeError('tracker unreadable')\n"
                      "client_leak.item_problem = boom\n"
                      "print(json.dumps({'ok': ok, 'broken': edit_ai.project_facts('ABC', client=True), "
                      "'internal': edit_ai.project_facts('ABC')}))")
        sent = json.dumps(got["ok"])
        self.assertEqual(got["ok"]["people"], [])
        self.assertIn(SEEN, got["ok"]["ids"])
        for i, owner, title in rows:
            self.assertNotIn(i, sent)
            if owner and owner != "TBC":
                self.assertNotIn(owner, sent)
            self.assertNotIn(title, sent)
        self.assertEqual(got["broken"]["ids"], [])                                      # fails closed: no IDs, no people
        self.assertEqual(got["broken"]["people"], [])
        self.assertIn(INTERNAL, got["internal"]["ids"])                                 # control: the internal place has them


class ClientSheetOffersNoItems(unittest.TestCase):
    """#123 (Alan's decision 8): the client sheet offers no work item, so no internal one: its editor has no `#` picker, no `/` menu
    (whose Work item row needs that host) and draws no chips."""

    def test_the_sheet_editor_has_no_item_picker_slash_menu_or_chips(self):
        src = Path(__file__).resolve().parents[2] / "system" / "templates" / "dashboard" / "src" / "components" / "report"
        # names written in parts: whole, they would be page names a test uses (dashboard_split's globals list)
        for name in ("Sheet" + "Text.jsx", "Client" + "View.jsx", "Client" + "Parts.jsx", "Sheet" + "Page.jsx", "Sheet.jsx",
                     "sheet" + "Lib.js", "client" + "Doc.js"):
            f = src / name
            if not f.exists():
                continue
            code = f.read_text(encoding="utf-8")
            for hook in ("attach" + "ItemPick", "insert" + "Hash", "item" + "Chip", "attach" + "Slash", "item" + "Options"):
                self.assertNotIn(hook, code, f"{name} wires {hook}: a client sheet would offer or draw work items")


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
