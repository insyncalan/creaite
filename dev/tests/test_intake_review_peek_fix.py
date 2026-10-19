"""#232-B review fixes (v2.5.0), against the peek on Intake and Review.
1. Esc with a menu open in the peek (the Type list) closes only the menu; a second Esc closes the peek. The peek's Esc listener
   uses the same exemptions as the panel's own (panel.js pkEscMenu / pkEscBusy), so it no longer closes the peek over an open popup.
2. Saving in the peek recomputes the row's `hold` by the server's rule (review.hold_reason; the page's mirror is core/irFold.js
   irHold, compared here with the server on the same cases). A routine Issue turned into a Risk leaves the Routine group and
   Approve routine never approves it; a hold cleared by an edit may stay where it is.

Run: python3 dev/tests/test_intake_review_peek_fix.py   (the browser tests need Google Chrome; the mirror test needs Node)
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import intake_review_support as S  # noqa: E402
import review  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

FOLD = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core/irFold.js"
ROW = "#v-intake-review tr.irprop"
ISSUE = "Supplier portal is down for the pilot"


def click_row(b, text):
    b.eval(f"[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icttl').textContent.includes({text!r})).querySelector('.icttl').click()")


def raid(n, typ, **extra):
    return {"n": n, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "pending", **extra,
            "values": {"project": "ABC", "type": typ, "description": ISSUE, "owner": "Omar", "impact": "High", "likelihood": "Medium", "source": S.TEAMS}}


def upd(table, change, ident, **extra):
    return {"n": 9, "op": "update", "table": table, "id": ident, "match": "strong", "flags": [], "decision": "pending",
            "changes": change, "why": "x", "source": S.MAIL, **extra}


def row_of(item):
    """The Review row's parts the mirror reads (build_dashboard.queue_item / item_record): project, kind, op, rec, flags, hold."""
    v = item.get("values") or {}
    project = None if review.needs_project(item) else review.project_of(item)
    ch = item.get("changes") or {}
    field = next(iter(ch), "")
    if item["op"] == "new":
        kind, rec = item["table"], {"type": v.get("type")}
    else:
        kind, rec = "update", {"target": item.get("id"), "field": field, "to": ch.get(field)}
    return {"p": project, "kind": kind, "op": item["op"], "rec": rec, "flags": list(item.get("flags", [])), "hold": review.hold_reason(item) or ""}


def edited(item, **change):
    """The same item after an edit in the peek: values (or changes) updated, and a project set through match strong."""
    e = json.loads(json.dumps(item))
    if "project" in change:
        e["values"]["project"] = change["project"]
        e["match"] = "strong"
    for k in ("type",):
        if k in change:
            e["values"][k] = change[k]
    if "status" in change:
        e["changes"]["status"] = change["status"]
    return e


def as_edit(before, after):
    """(row before, row after the edit as the peek leaves it: rec updated, p set, the old hold kept for the mirror to recompute)."""
    r0, r1 = row_of(before), row_of(after)
    r1["hold"] = r0["hold"]
    return r1, review.hold_reason(after) or ""


CASES = {
    "issue to risk": (raid(1, "Issue"), {"type": "Risk"}),
    "risk to issue": (raid(1, "Risk"), {"type": "Issue"}),
    "issue stays": (raid(1, "Issue"), {}),
    "new decision stays": ({"n": 2, "op": "new", "table": "decisions", "match": "strong", "flags": [],
                            "values": {"project": "ABC", "decision": "Approve it", "made_by": "Sara Example", "source": S.MAIL}}, {}),
    "possible match, project set": (raid(1, "Issue", match="possible"), {"project": "ABC"}),
    "no project, project set": ({**raid(1, "Issue"), "values": {**raid(1, "Issue")["values"], "project": None}}, {"project": "ABC"}),
    "possible match, still none": (raid(1, "Issue", match="possible"), {}),
    "conflict stays": (raid(1, "Issue", flags=["conflict"]), {}),
    "invalid stays": (raid(1, "Issue", flags=["invalid"]), {}),
    "action reopened from closing": (upd("actions", {"status": "Closed"}, "ABC-A-001"), {"status": "Open"}),
    "action update to closing": (upd("actions", {"status": "Open"}, "ABC-A-001"), {"status": "Closed"}),
    "raid update to closing": (upd("raid", {"status": "Open"}, "ABC-001"), {"status": "Closed"}),
    "date update stays routine": (upd("actions", {"due_date": "2026-12-01"}, "ABC-A-001"), {}),
}

SCRIPT = """
const f = await import(%s); const cases = %s;
console.log(JSON.stringify(Object.fromEntries(Object.entries(cases).map(([k, r]) => [k, f.irHold(r)]))));
"""


@unittest.skipUnless(shutil.which("node"), "needs Node")
class HoldMirror(unittest.TestCase):
    def test_the_page_rule_equals_review_hold_reason(self):
        rows, want = {}, {}
        for name, (item, change) in CASES.items():
            rows[name], want[name] = as_edit(item, edited(item, **change))
        r = subprocess.run(["node", "--input-type=module", "-e", SCRIPT % (json.dumps(FOLD.as_uri()), json.dumps(rows))], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)
        for name in CASES:
            self.assertEqual(got[name], want[name], name)
        self.assertEqual(want["issue to risk"], "new risk")                        # the cases are not all empty
        self.assertEqual(want["possible match, project set"], "")

    def test_held_rows_move_to_needs_and_cleared_ones_stay(self):
        js = """const f = await import(%s); const g = {needs: [1], routine: [2, 3]}, held = n => n === 3;
          console.log(JSON.stringify([f.irLive(g, () => false, held), f.irLive(g, () => false), f.irBulk(g, () => false, held), f.irGroupsShown(g, () => false, held).map(x => [x.kind, x.ns])]));"""
        r = subprocess.run(["node", "--input-type=module", "-e", js % json.dumps(FOLD.as_uri())], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        live, plain, bulk, shown = json.loads(r.stdout)
        self.assertEqual(live, {"needs": [1, 3], "routine": [2]})
        self.assertEqual(plain, {"needs": [1], "routine": [2, 3]})                 # without a hold check, as before
        self.assertEqual(bulk, [2])
        self.assertEqual(shown, [["needs", [1, 3]], ["routine", [2]]])


class PeekFix(LiveBrowserCase):
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)
        p = v.propose("2026-10-08-1000-sweep", [raid(1, "Issue")])
        data = json.loads(p.read_text())
        data["source_run"] = "cx-sweep"
        p.write_text(json.dumps(data, indent=2))

    def open_issue(self):
        b = self.b
        S.open_page(b)
        click_row(b, ISSUE)
        b.wait("document.getElementById('panel').classList.contains('on') && document.getElementById('panel').classList.contains('pkprop')")

    def group_of(self, text):
        return self.b.eval(f"""(()=>{{ let t=[...document.querySelectorAll('{ROW}')].find(t=>t.querySelector('.icttl').textContent.includes({text!r}));
          while (t && !(t.classList.contains('icsubhead'))) t = t.previousElementSibling; return t ? t.dataset.irg : null; }})()""")

    def test_esc_closes_the_open_menu_first_then_the_peek(self):
        b = self.b
        self.open_issue()
        b.click("#panel [data-pkp=type]")
        b.wait("!!document.querySelector('.pkpop')")
        b.key("Escape")
        b.wait("!document.querySelector('.pkpop')")
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('on')"))      # the peek is still there
        self.assertIsNotNone(b.eval("irPeek.value"))
        b.key("Escape")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.assertIsNone(b.eval("irPeek.value"))

    def test_an_issue_turned_into_a_risk_is_not_routine(self):
        b = self.b
        S.open_page(b)
        self.assertEqual(self.group_of(ISSUE), "routine")
        self.open_issue()
        b.click("#panel [data-pkp=type]")
        b.wait("!!document.querySelector('.pkpop')")
        b.eval("[...document.querySelectorAll('.pkpop .pkopt')].find(o=>o.querySelector('span').firstChild.textContent==='Risk').click()")
        b.pump(0.3)
        b.click("#pkPSave")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        b.wait(f"[...document.querySelectorAll('{ROW}')].some(t=>t.querySelector('.icttl').textContent.includes({ISSUE!r}) && t.dataset.hold==='new risk')")
        self.assertEqual(self.group_of(ISSUE), "needs")                               # it moved to Needs your decision
        b.eval("window.__calls=[]; const f=window.fetch; window.fetch=function(u,o){ window.__calls.push(String(u)); return f.apply(this,arguments); }")
        b.eval("document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.querySelector('[data-ira=routine]').click()")
        b.wait("document.querySelector('#snackT') && /Approved/.test(document.getElementById('snackT').textContent)", 25)
        self.assertEqual(b.eval("window.__calls.filter(u=>/\\/api\\/apply/.test(u)).length"), 1)    # one apply for the others
        self.assertFalse(any(r["description"] == ISSUE for r in self.v.rows("raid")))               # the new Risk waits for Alan
        self.assertTrue(b.eval(f"[...document.querySelectorAll('{ROW}')].some(t=>t.querySelector('.icttl').textContent.includes({ISSUE!r}))"))


if __name__ == "__main__":
    unittest.main()
