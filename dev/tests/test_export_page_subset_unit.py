"""v2.5.0 page subset, unit level: export_page.check_page refuses a client page whose words the saved report doesn't hold, and keeps
the page the dashboard draws (its header, a logo drawn as its name, Markdown words, dates, tables). No vault: the tracker lookup and
the client wording check are stubbed, so the subset check is the only thing that can refuse these pages. Fictional data only.

Run: python3 dev/tests/test_export_page_subset_unit.py
"""
import copy
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import export_page as E  # noqa: E402
import paths  # noqa: E402

DOC = {
    "format": "creaite-doc", "schema": 1, "kind": "client", "audience": "client", "project": "ABC", "project_name": "Example Programme",
    "title": "Client report", "date": "2026-10-09", "client": "Example Client Ltd", "version": 3, "state": "approved",
    "layout": {"order": ["header", "summary", "risks"], "hidden": [], "headings": {}},
    "items": {},
    "sections": [
        {"id": "header", "type": "header", "heading": "Client report", "default_heading": "Client report", "hidden": False, "text": "",
         "data": {"label": "Client report", "client": "Example Client Ltd", "period_start": "2026-10-05", "period_end": "2026-10-09",
                  "logos": []}},
        {"id": "summary", "type": "text", "heading": "Summary", "default_heading": "Summary", "hidden": False,
         "text": "Testing is **on plan** this week.\n\n- Licences *ordered*\n- Data loaded"},
        {"id": "risks", "type": "table", "heading": "Risks and issues", "default_heading": "Risks and issues", "hidden": False,
         "columns": [{"key": "type", "label": "Type"}, {"key": "risk", "label": "What it is"}],
         "rows": [{"ref": "ABC-006", "shown": True, "cells": {"type": "Issue", "risk": "Test licences are not yet ordered."}},
                  {"ref": "ABC-007", "shown": False, "cells": {"type": "Risk", "risk": "Quietly renegotiate the walrus rebate."}}]},
    ],
}

HEADER = ('<header class="doc"><div><h1>Client report</h1><div class="sub">Example Programme · Example Client Ltd</div></div>'
          '<div class="sub">Client</div></header><section data-id="header"><header class="wr-hd"><div class="wr-title">'
          '<div class="wr-eb">Client report · Client</div><div class="wr-pn">Example Programme</div>'
          '<div class="wr-wk">Period 05-10-2026 to 09-10-2026 · for Example Client Ltd</div></div>'
          '<div class="wr-logos">{logos}</div></header></section>')
SUMMARY = ('<section data-id="summary"><h2>Summary</h2><div class="crsec"><div class="wr-rich "><p><span>Testing is <b>on plan</b> '
           'this week.</span></p><ul><li>Licences <i>ordered</i></li><li>Data loaded</li></ul></div></div></section>')
RISKS = ('<section data-id="risks"><h2>Risks and issues</h2><div class="crsec"><div class="wr-tbl"><table class="wr-r"><thead><tr>'
         '<th>Type</th><th>What it is</th></tr></thead><tbody><tr><td><div class="wr-rich "><p><span>Issue</span></p></div></td>'
         '<td><div class="wr-rich "><p><span>{risk}</span></p></div></td></tr></tbody></table></div></div></section>')


def markup(logos="", risk="Test licences are not yet ordered.", extra=""):
    return ('<div id="v-clientreport" class="export-view"><div class="page" data-audience="client">' + HEADER.replace("{logos}", logos)
            + SUMMARY + RISKS.replace("{risk}", risk) + extra + "</div></div>")


def page(html, css=".page{color:#123}", version=3):
    return {"html": html, "css": css, "palette": "creaite", "version": version}


class Subset(unittest.TestCase):
    def setUp(self):
        self.saved = {k: getattr(E, k) for k in ("item_lookup", "logo_names")}
        self.mod = sys.modules.get("client_leak")
        fake = types.ModuleType("client_leak")

        class Con:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        fake.connect = Con
        fake.plain_findings = lambda con, code, text: []          # the client wording check never refuses here
        sys.modules["client_leak"] = fake
        E.item_lookup = lambda ref: None
        E.logo_names = lambda code: ["Harbour Partners"]

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(E, k, v)
        if self.mod is None:
            sys.modules.pop("client_leak", None)
        else:
            sys.modules["client_leak"] = self.mod

    def check(self, html, **kw):
        """None when the page is used, else the refusal."""
        pg = page(html, **kw)
        attrs, info = [], {}
        try:
            m, text, sections, rows = E.clean_markup(pg["html"], True, attrs, info)
            css = E.clean_css(pg["css"], True)
            E.check_page(copy.deepcopy(DOC), pg, text, sections, rows, attrs, css, info)
        except E.PageRefused as e:
            return str(e)
        return None

    def test_control_the_dashboards_page_is_used(self):
        self.assertIsNone(self.check(markup()))

    def test_a_logo_drawn_as_its_name_is_not_refused(self):
        logos = ('<span class="wr-logo"><span class="sub">Firm</span></span><span class="wr-logo"><span class="sub">Client</span></span>'
                 '<span class="wr-logo"><span class="sub">Harbour Partners</span></span>')
        self.assertIsNone(self.check(markup(logos=logos)))
        self.assertIsNotNone(self.check(markup(logos='<span class="sub">Petra Quill</span>')), "a name that isn't a logo's")

    def test_words_the_report_does_not_hold_are_refused_by_the_subset_check_alone(self):
        """No hidden needle and no client wording finding here: only the subset check can refuse these."""
        for risk in ("Petra Quill will renegotiate the walrus supplier rebate quietly.", "Zanzibar quokka ledger.",
                     "Testing is on plan this week."):                   # the summary's words, under the risks section's id
            with self.subTest(risk=risk):
                self.assertIn("words the saved report doesn't", self.check(markup(risk=risk)) or "")
        self.assertIsNotNone(self.check(markup(risk="Quietly renegotiate the walrus rebate.")))     # a hidden row's (needle check)
        self.assertIsNotNone(self.check(markup(extra="<p>Arbitrary words outside every section.</p>")))

    def test_comments_scripts_style_words_and_foreign_ids_are_refused(self):
        for extra, css in (("<!-- Petra Quill -->", ".page{color:#123}"), ("<script>1</script>", ".page{color:#123}"),
                           ("", '.page::after{content:"Petra Quill"}'), ('<p style="--petra:quill"></p>', ".page{color:#123}"),
                           ('<section data-id="zz"><p>Issue</p></section>', ".page{color:#123}"),
                           ('<p data-id="zz"></p>', ".page{color:#123}")):
            with self.subTest(extra=extra, css=css):
                self.assertIsNotNone(self.check(markup(extra=extra), css=css))

    def test_a_class_no_stylesheet_rule_uses_never_reaches_the_file(self):
        out = E.clean_markup('<p class="wr-r Petra Quill"></p>', True, [], {})[0]
        self.assertEqual(out, '<p class="wr-r"></p>')

    def test_the_check_fails_closed_without_the_dashboards_stylesheet(self):
        old, cache = paths.TEMPLATES, dict(E._OWN)
        try:
            with tempfile.TemporaryDirectory() as d:
                paths.TEMPLATES = Path(d)
                E._OWN.clear()
                self.assertIsNotNone(self.check(markup()))
        finally:
            paths.TEMPLATES = old
            E._OWN.clear()
            E._OWN.update(cache)


if __name__ == "__main__":
    unittest.main(verbosity=2)
