"""BL-341 (#212): creaite 2.3.1's hand checks (the v2.3.1 patch section of the Product Manager's v2.3.0 sheet: Draft email fixes,
branch email-153-fix5), automated against a vault made from the release zip. Separate from test_v230.py (Alan, via Jarvis, 18-10-2026).

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.3.1
Run this file on its own (it makes the vault itself):                 python3 dev/tests/handchecks/test_v231.py

Until email-153-fix5 is in the line every check skips, with the reason: the vault is probed for `linktext._sent_norm`, which that
branch adds. Run against the branch merged in, all four pass; run against 2.3.0 as it stands, all four fail, so they check
something. They keep the sheet's numbers (14 to 17); a 2.3.1 sheet that numbers them from 1 only needs the names changed.
All four are scriptable: no real recipient, mailbox or model is involved (nothing is sent; the preview is read from the page).
Helpers: hcbase.HandcheckCase (screens, notes, own vaults), test_v230.V230Case (the page's API, seeding, a Python probe in the vault).

  Patch231      14 to 17            one vault of its own (the checks seed updates)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_v230 import V230Case

KIND = {n: "scriptable" for n in (14, 15, 16, 17)}
LIVE_ONLY = {}

FIX_PROBE = "_sent_norm"      # in system/scripts/linktext.py once email-153-fix5 is in the line


class V231Case(V230Case):
    """V230Case, and the probe that says whether the 2.3.1 fixes are in this vault."""

    @property
    def fixed(self):
        """Whether this vault has the 2.3.1 Draft email fixes (email-153-fix5)."""
        return FIX_PROBE in (self.vault / "system/scripts/linktext.py").read_text(encoding="utf-8")

    def need_fix(self):
        if not self.fixed:
            self.skipTest("2.3.1 patch: email-153-fix5 (Draft email fixes) is not in the line yet; this check runs once it is merged")


class Patch231(V231Case):
    """Checks 14 to 17 (the sheet's numbers): the 2.3.1 patch. Skipped until email-153-fix5 is in the line. One vault of their own."""
    own_vault = True


    CHASE = "17-10-2026: Chased Rashid Al Suwaidi by email (reminder 1); reply asked for by 19-10-2026."
    EMAILED = "17-10-2026: Emailed Rashid Al Suwaidi by message asking for an update."
    ASKED = "17-10-2026: Asked Rashid Al Suwaidi for a decision by email; reply asked for by 20-10-2026."

    def test_c14_chase_to_an_outside_recipient(self):
        """14. A Draft email chase for an outside recipient never prints who else was chased or which reminder it is; the same
        internal lines are absent from the steering and sponsor views."""
        self.need_fix()
        b = self.b
        self.seed([
            {"op": "update", "table": "actions", "id": "FAL-A-003", "changes": {"latest_update": self.CHASE + "\nWaiting on the vendor"}},
            {"op": "update", "table": "raid", "id": "FAL-006", "changes": {"response_action": self.EMAILED + "\nAgree dates with the supplier"}}])
        b.reload("typeof go==='function' && LIVE")
        # the popup, for an outside address (Rashid is at an outside organisation), with the latest update included
        b.eval("go('person','Rashid Al Suwaidi'); openDraftEmail('Rashid Al Suwaidi','chase')")
        b.wait("document.getElementById('deDlg').open&&document.querySelector('#deInc [data-deit]')", 15)
        b.eval("document.querySelectorAll('#deInc [data-deit]').forEach(i=>{ if(!i.checked) i.click(); })")
        b.eval("(()=>{ const u=document.getElementById('deUpd'); if(u && !u.checked) u.click(); })()")
        b.pump(0.8)
        mail = b.eval("document.getElementById('dePrev') ? document.getElementById('dePrev').innerText : document.getElementById('deDlg').innerText")
        for bit in ("Chased", "chased", "reminder 1", "reply asked for", "by email", "Emailed"):
            self.assertNotIn(bit, mail, bit)
        self.assertIn("Waiting on the vendor", mail, "the rest of the update is kept")
        self.assertIn("Agree dates with the supplier", mail, "the rest of the response is kept")
        b.eval("document.getElementById('deDlg').close()")
        facts = self.py("import drafts\nprint(json.dumps([drafts.chase_facts('FAL-A-003'), drafts.chase_facts('FAL-006')]))")
        self.assertNotIn("Chased", json.dumps(facts))
        self.assertNotIn("Emailed", json.dumps(facts))
        for aud in ("steering", "sponsor"):
            t = self.py(f"import status_facts\nprint(json.dumps(status_facts.facts('FAL', None, None, {aud!r})['text']))")
            self.assertNotIn("Emailed Rashid", t, aud)
        self.assertIn("Emailed Rashid", self.py("import status_facts\nprint(json.dumps(status_facts.facts('FAL', None, None, 'internal')['text']))"),
                      "the internal sheet keeps it")

    def test_c15_sent_lines_in_every_shape(self):
        """15. "I sent it" recognises lines in lower case, with bullets and with odd spaces."""
        self.need_fix()
        shapes = {"lower case": self.CHASE.replace("Chased", "chased"), "bullet": "- " + self.CHASE, "star bullet": "* " + self.EMAILED,
                  "no-break space": "17-10-2026:\u00a0Chased Rashid Al Suwaidi by email (reminder 1).",
                  "iso date": "2026-10-17: Chased Rashid Al Suwaidi by email (reminder 1).",
                  "zero-width": "17-10-2026:\u200b Chased Rashid Al Suwaidi by email (reminder 1)."}
        res = self.py("import linktext\nshapes = " + json.dumps(shapes) + "\nprint(json.dumps({k: [linktext.sent_has(v), linktext.sent_strip('Waiting on the vendor\\n' + v)] for k, v in shapes.items()}))")
        for name, (has, stripped) in res.items():
            self.assertTrue(has, name)
            self.assertEqual(stripped, "Waiting on the vendor", name)
        ordinary = self.py("import linktext\nprint(json.dumps([linktext.sent_has(t) for t in ('We chased the supplier last week', 'Chased Sara by email yesterday')]))")
        self.assertEqual(ordinary, [False, False], "ordinary text is not a sent line")
        # and in the email the page builds: every shape on an item's update, none of them in the preview of an outside address
        b = self.b
        self.seed([{"op": "update", "table": "actions", "id": "FAL-A-003",
                    "changes": {"latest_update": "Waiting on the vendor\n" + "\n".join(shapes.values())}}])
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('person','Rashid Al Suwaidi'); openDraftEmail('Rashid Al Suwaidi','update')")
        b.wait("document.getElementById('deDlg').open&&document.querySelector('#deInc [data-deit]')", 15)
        b.eval("document.querySelectorAll('#deInc [data-deit]').forEach(i=>{ if(!i.checked) i.click(); })")
        b.eval("(()=>{ const u=document.getElementById('deUpd'); if(u && !u.checked) u.click(); })()")
        b.pump(0.8)
        mail = b.eval("document.getElementById('dePrev').innerText")
        for bit in ("hased", "mailed", "by email", "reminder", "17-10-2026"):
            self.assertNotIn(bit, mail, bit)
        self.assertIn("Waiting on the vendor", mail)
        b.eval("document.getElementById('deDlg').close()")

    def test_c16_add_details_for_a_person_with_no_items(self):
        """16. A person with no items can get "Add details"."""
        self.need_fix()
        b = self.b
        for who in ("Nobody Known",):
            b.eval(f"openContextMenu(cxPerson({who!r},''),200,200,{{label:{who!r}}})")
            b.wait('!!document.querySelector(".cxmenu")', 10)
            labels = b.eval('[...document.querySelectorAll(".cxmenu [role=menuitem]")].map(x=>x.textContent.trim())')
            self.assertTrue(any(x.startswith("Add details") for x in labels), labels)
            b.eval('[...document.querySelectorAll(".cxmenu [role=menuitem]")].find(x=>x.textContent.includes("Add details")).click()')
            b.wait("document.getElementById('personDlg').open", 10)
            self.assertEqual(b.eval("VIEW"), "person")
            b.eval("document.getElementById('personDlg').close()")

    def test_c17_help_says_draft_email(self):
        """17. Help says "Draft email" where it used to say "Chase"."""
        self.need_fix()
        b = self.b
        self.screen("help")
        md = (self.vault / "system/templates/help.md").read_text(encoding="utf-8")
        for line in md.splitlines():
            if "Decisions needed" in line and ("**Decide**" in line or "Decisions needed:**" in line):
                self.assertNotRegex(line, r"\*\*Chase\*\*", line[:80])
        self.assertNotIn("**Decide**, **Chase**", md)
        b.eval("document.getElementById('helpQ').value='Chase'; document.getElementById('helpQ').dispatchEvent(new Event('input',{bubbles:true}))")
        b.pump(0.8)
        hits = b.eval("document.getElementById('helpResults') ? document.getElementById('helpResults').innerText : ''")
        self.assertNotRegex(hits, r"Decide[^\n]*\bChase\b", "no button called Chase beside Decide")


if __name__ == "__main__":
    import unittest
    unittest.main()
