"""v2.5.1 (#239): property P25 of Team Cap's list (dev/proposals/props239/PROPERTIES.md on origin/v251-properties), the browser tier.
Real Chrome on the real live server (no Claude runs); desktop only; fictional words only.

P25. For any internal report and client sheet (any sections, rows), a bulk Match ("Match internal for every section") adds no
section that is not already on the client side, leaves each client section's left-out state as it was, and the client report it
leaves passes the gate (/api/report/match-check finds nothing); the slash menu of a client text section offers no item row.
Generator (seeded, PROP_SEED, default 239): which text sections of the internal report hold words, drawn from clean and hostile
pools; which client sections are left out; 0 to 20 rows in the internal report's risks table. Smoke 20 cases, CREAITE_PROPS_FULL=1
200. A failure prints the seed, the case and what it drew.
Mutation proof: with the page's Match gate answered "no findings" whatever the text (a fetch stub for /api/report/match-check),
the same property goes red (test_mutant_*).

Run: python3 dev/tests/test_client_output_p25.py      (Chrome tier; skipped without Chrome)
"""
import json
import os
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_sbs_matchgate as M  # noqa: E402  (its fixture: the hub on the real live server, side by side)

INT, CLI, WEEK = M.INT, M.CLI, M.WEEK
SEED = int(os.environ.get("PROP_SEED") or 239)
CASES = 200 if os.environ.get("CREAITE_PROPS_FULL") == "1" else 20
CLEAN = ("Quincebrook is on plan for the week.", "Thistledown testing starts on Monday.", "The harbour cutover went to plan.",
         "Marigold training is booked for both teams.", "")
HOSTILE = (M.HOSTILE, "Omar Ali to Confirm tester names before the review.", "This line is confidential: keep it inside.",
           "Budget overrun on phase one is being absorbed.", "Quincebrook is on plan, but this is confidential.")
TEXT_SECTIONS = ("summary", "this_week", "next_week")
ITEM_ROW = r"\b[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3}\b|Work item|Add from the tracker|Overdue action|Risk or issue"
STUB_GATE = ("""(()=>{const f=window.fetch.bind(window); window.fetch=(u,o)=>{ if(String(u).endsWith('/api/report/match-check')){
  const n=(JSON.parse(o.body).docs||[]).length; return Promise.resolve(new Response(JSON.stringify({ok:true,findings:Array(n).fill([])}),
  {status:200,headers:{'Content-Type':'application/json'}})); } return f(u,o); };})()""")


class P25(M.Base):
    def draw(self, i):
        """One case: {internal: {section: words}, left_out: [client section], rows: n}."""
        r = random.Random(SEED * 1000 + i)
        words = {s: r.choice(HOSTILE if r.random() < .5 else CLEAN) for s in TEXT_SECTIONS if r.random() < .8}
        return {"i": i, "internal": words, "left_out": [s for s in TEXT_SECTIONS + ("risks", "decisions") if r.random() < .25],
                "rows": r.randint(0, 20)}

    def arrange(self, case):
        """The case's internal report and client sheet, saved through the routes before the page opens."""
        w = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})
        doc = w["doc"]
        for s in doc["sections"]:
            if s["id"] in case["internal"]:
                s["text"] = case["internal"][s["id"]]
            if s["id"] == "risks" and s.get("type") == "table":
                row = (s.get("rows") or [{"ref": "", "shown": True, "cells": {}}])[0]
                s["rows"] = [dict(row, cells={**(row.get("cells") or {}), "risk": f"Row {n} of the internal risks"})
                             for n in range(case["rows"])]
        self.assertTrue(self.api("/api/report/save", {"doc": doc, "base_version": w["version"]})["ok"])
        c = self.api("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        cdoc = c["doc"]
        for s in cdoc["sections"]:
            s["hidden"] = s["id"] in case["left_out"] or (s.get("hidden") and s["id"] not in TEXT_SECTIONS)
        cdoc["layout"]["hidden"] = [s["id"] for s in cdoc["sections"] if s.get("hidden")]
        self.assertTrue(self.api("/api/report/save", {"doc": cdoc, "base_version": c["version"]})["ok"])
        return self.shape()

    def shape(self):
        doc = self.client_draft()
        return [(s["id"], bool(s.get("hidden"))) for s in doc["sections"]], doc

    def match_all(self, stub=False):
        self.open_side()
        if stub:
            self.q(STUB_GATE)
        self.b.wait("!!document.querySelector('[data-crmatchall]')", 15)
        self.q("document.querySelector('[data-crmatchall]').scrollIntoView({block:'center'})")
        self.b.click("[data-crmatchall]")
        self.b.pump(3.5)                                       # the matches, the held dialog, and the client sheet's autosave (1.5 s)
        self.q("(()=>{const d=document.getElementById('crHeldDlg'); if(d&&d.open) d.close();})()")
        self.b.pump(2.0)

    def property_holds(self, case, stub=False):
        """[] when P25 holds for the case, else what failed."""
        before, _doc = self.arrange(case)
        self.match_all(stub)
        after, doc = self.shape()
        failed = []
        if [i for i, _h in after] != [i for i, _h in before]:
            failed.append(f"client sections changed: {[i for i, _h in before]} -> {[i for i, _h in after]}")
        if after != before:
            failed.append(f"a client section's left-out state changed: {before} -> {after}")
        found = self.api("/api/report/match-check", {"docs": [doc]})
        if not found.get("ok") or found["findings"][0]:
            failed.append(f"the client report the Match left fails the gate: {found}")
        text = (self.q(f"document.querySelector('{CLI}').innerText") or "").lower()
        failed += [f"the client pane holds {n!r}" for n in M.NEEDLES if n.lower() in text]
        return failed

    def test_P25_bulk_match_adds_no_section_and_leaves_a_client_report_the_gate_passes(self):
        print(f"PROP_SEED={SEED} P25 cases={CASES}", file=sys.stderr)
        fails = []
        for i in range(CASES):
            case = self.draw(i)
            got = self.property_holds(case)
            if got:
                fails.append({"seed": SEED, "case": case, "failed": got})
        self.assertEqual(fails, [], json.dumps(fails, indent=1)[:4000])

    def test_P25_the_client_slash_menu_offers_no_item_row(self):
        """The `/` menu belongs to a text section (type "freetext": the Notes editor with the textsection profile); the built-in sections
        (summary and the rest) have none. So the client report gets a client text section of its own first."""
        c = self.api("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        doc = c["doc"]
        doc["sections"] = doc["sections"] + [{"id": "free_p25", "type": "freetext", "heading": "Notes", "default_heading": "",
                                              "hidden": False, "text": "Ready.", "audience": "client"}]
        self.assertTrue(self.api("/api/report/save", {"doc": doc, "base_version": c["version"]})["ok"])
        self.open_side()
        self.focus_in(CLI, "free_p25")
        self.b.type(" /")
        self.b.wait("!!document.querySelector('.slashroot [role=option]')", 8)
        rows = self.q("[...document.querySelectorAll('.slashroot [role=option]')].map(x=>x.textContent)")
        self.assertTrue(rows, "the slash menu opened")
        self.assertNotRegex(" | ".join(rows), ITEM_ROW, rows)
        self.b.key("Escape")

    def test_mutant_P25_goes_red_when_the_match_gate_answers_nothing(self):
        case = {"i": -1, "internal": {"summary": M.HOSTILE}, "left_out": [], "rows": 0}
        self.assertEqual(self.property_holds(case), [], "control: the real gate holds the hostile section")
        self.assertNotEqual(self.property_holds(case, stub=True), [], "with the gate stubbed out the property must go red")


if __name__ == "__main__":
    unittest.main()
