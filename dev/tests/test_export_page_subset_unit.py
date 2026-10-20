"""v2.5.0 page subset, unit level, as superseded by #239 step 3 (v2.5.2): a client report's posted page is never used at all, so
export_page.build refuses every client page outright (CLIENT_PAGE), the dashboard's own page and every page the 2.5.0 subset check
refused alike; the client file is only ever client_snapshot.client_export's render. No vault. Fictional data only.

Run: python3 dev/tests/test_export_page_subset_unit.py
"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import export_page as E  # noqa: E402

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
    def refused(self, html, **kw):
        with self.assertRaises(E.PageRefused) as cm:
            E.build(copy.deepcopy(DOC), page(html, **kw), "Client report")
        self.assertEqual(str(cm.exception), E.CLIENT_PAGE)

    def test_even_the_dashboards_own_page_is_never_used_for_a_client_report(self):
        self.refused(markup())

    def test_a_logo_drawn_as_its_name_or_not_is_refused_with_the_page(self):
        self.refused(markup(logos='<span class="wr-logo"><span class="sub">Harbour Partners</span></span>'))
        self.refused(markup(logos='<span class="sub">Petra Quill</span>'))

    def test_words_the_report_does_not_hold_are_refused(self):
        for risk in ("Petra Quill will renegotiate the walrus supplier rebate quietly.", "Zanzibar quokka ledger.",
                     "Quietly renegotiate the walrus rebate."):
            with self.subTest(risk=risk):
                self.refused(markup(risk=risk))
        self.refused(markup(extra="<p>Arbitrary words outside every section.</p>"))

    def test_comments_scripts_style_words_and_foreign_ids_are_refused(self):
        for extra, css in (("<!-- Petra Quill -->", ".page{color:#123}"), ("<script>1</script>", ".page{color:#123}"),
                           ("", '.page::after{content:"Petra Quill"}'), ('<p style="--petra:quill"></p>', ".page{color:#123}"),
                           ('<section data-id="zz"><p>Issue</p></section>', ".page{color:#123}"),
                           ('<p data-id="zz"></p>', ".page{color:#123}")):
            with self.subTest(extra=extra, css=css):
                self.refused(markup(extra=extra), css=css)

    def test_a_client_report_edited_to_another_audience_is_still_refused(self):
        doc = copy.deepcopy(DOC)
        doc["audience"] = "internal"                # the kind decides: a client report is a client report
        with self.assertRaises(E.PageRefused):
            E.build(doc, page(markup()), "Client report")


if __name__ == "__main__":
    unittest.main(verbosity=2)
