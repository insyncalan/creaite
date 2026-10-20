"""v1.8.0: BL-294 (on-track milestones are green in every theme), BL-299 (On track, not "On plan") and BL-300 (Top risks and
issues: at most two lines each, #107).

Run: python3 dev/tests/test_milestone_words.py   (the BL-300 part needs Google Chrome; skipped otherwise)
"""
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
import tracker  # noqa: E402
from test_milestone_states import Case, iso, upd  # noqa: E402
from test_dashboard import CHROME, new, populate  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

STATES = ("achieved", "ontrack", "atrisk", "slipped", "overdue")
CSS = ROOT / "system/templates/dashboard/style.css"
MILESTONES_JS = ROOT / "system/templates/dashboard/src/milestones.js"


def state_accent_rules(css, js):
    """BL-294's rule: milestone and health states use only the status tokens. Returns each milestone state class drawn with
    --accent: a CSS rule whose selector names a state class (.mv-st.ontrack, .mv-mk.atrisk…), and each state's icon in mvShape."""
    bad = []
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        for one in sel.split(","):
            if re.search(r"\.(%s)\b" % "|".join(STATES), one) and "--accent" in body:
                bad.append(one.strip())
    m = re.search(r"function mvShape\(.*?\n(.*?)\[st\]", js, flags=re.S)
    assert m, "mvShape not found in milestones.js"
    for st, svg in re.findall(r"(\w+):'([^']*)'", m.group(1)):
        if st in STATES and "--accent" in svg:
            bad.append(f"mvShape {st}")
    return bad


class StateColours(unittest.TestCase):
    """BL-294: on track is the status green; no milestone state is drawn with --accent."""

    def test_no_milestone_state_uses_accent(self):
        self.assertEqual(state_accent_rules(CSS.read_text(), MILESTONES_JS.read_text()), [])

    def test_on_track_is_ok_green(self):
        css, js = CSS.read_text(), MILESTONES_JS.read_text()
        self.assertIn(".mv-st.ontrack{color:var(--ok)}", css)
        self.assertIn("ontrack:'<circle cx=\"8\" cy=\"8\" r=\"6\" fill=\"var(--ok)\"/>'", js)
        self.assertIn('stroke="var(--ok)"', re.search(r"achieved:'([^']*)'", js).group(1))   # achieved: its ringed tick

    def test_the_check_catches_accent(self):
        self.assertEqual(state_accent_rules(".mv-st.ontrack{color:var(--accent)} .mv-card.client{border:1px solid var(--accent)}",
                                            "function mvShape(st){\n const p={ontrack:'<circle fill=\"var(--accent)\"/>'}[st]"),
                         [".mv-st.ontrack", "mvShape ontrack"])


class ClientWords(Case):
    """BL-299: On track reads "On track" for a client too; no screen, report or one-pager says "On plan"."""

    def test_the_client_word_map(self):
        self.assertEqual(tracker.MS_CLIENT_WORD, {"Achieved": "Achieved", "On track": "On track", "At risk": "At risk",
                                                  "Slipped": "Expected later", "Overdue": "Late"})
        self.assertIn('MVCWORD={achieved:"Achieved",ontrack:"On track",atrisk:"At risk",slipped:"Expected later",overdue:"Late"}',
                      MILESTONES_JS.read_text())

    def test_no_text_names_on_plan(self):
        for rel in ("system/scripts/tracker.py", "system/scripts/report.py", "system/templates/dashboard/src/milestones.js",
                    "system/templates/help.md", ".claude/skills/cx-minutes/references/tracker-conventions.md",
                    ".claude/skills/cx-client-report/SKILL.md", ".claude/skills/cx-steerco/SKILL.md"):
            self.assertNotIn("On plan", (ROOT / rel).read_text(), rel)

    def test_client_report_and_one_pager_say_on_track(self):
        self.apply("cv", [upd("ABC-M-002", client_visible=1, client_message="Go-live is on the agreed date.")])
        data = lambda *a: json.loads(self.v.run(*a, script="report.py").stdout)  # noqa: E731
        ms = data("client-data", "ABC", "--since", iso(-30))["milestones"]
        self.assertEqual([(m["name"], m["state"]) for m in ms], [("Go-live", "On track")])
        one = json.dumps(data("steerco-data", "ABC", "--version", "client"))
        self.assertIn("On track", one)
        spec = self.v.root / "system/staging/drafts/cr.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"code": "ABC", "period_start": iso(-30), "summary": ["A quiet week."], "force": True}))
        self.v.run("client-stage", str(spec), script="report.py")
        text = __import__("test_reports").client_draft_text(self, self.v)        # v2.5.1: the hub's own client draft, no Word file
        self.assertIn("On track", text)
        self.assertNotIn("On plan", text)
        self.assertNotIn("On plan", one)


LONG = " ".join(f"Step {i}: agree the data-sharing terms with the client's security team and record them." for i in range(1, 30))


@unittest.skipUnless(CHROME, "needs Google Chrome")
class TopRisks(LiveBrowserCase):
    """BL-300: the text under each top risk or issue is cut at two lines with a quiet More and its full text as a tooltip."""
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        v.propose("long", [new("raid", 1, project="ABC", type="Risk", description="Data sharing terms not agreed",
                                impact="High", likelihood="High", raised=iso(-3), response_action=LONG,
                                source="Alan (cx-edit), 2026-10-05")])
        v.run("apply")

    def rows(self):
        return self.b.eval("""[...document.querySelectorAll('#v-cockpit .rkrow')].map(r=>{ const t=r.querySelector('.rk-txt');
          return {id:r.dataset.open, cut:r.classList.contains('clamped'), more:!!r.querySelector('.rk-more'), title:t.title,
                  text:t.textContent, lines:Math.round(t.clientHeight/parseFloat(getComputedStyle(t).lineHeight)),
                  clamp:getComputedStyle(t).webkitLineClamp, tab:r.tabIndex}; })""")

    def open_cockpit(self):
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("document.querySelector('#v-cockpit .rkrow')")

    def test_long_text_is_cut_at_two_lines(self):
        self.open_cockpit()
        rows = self.rows()
        long = next(r for r in rows if r["text"] == LONG)
        self.assertEqual((long["cut"], long["more"], long["title"], long["clamp"]), (True, True, LONG, "2"))
        self.assertLessEqual(long["lines"], 2)
        short = [r for r in rows if r["text"] != LONG]
        self.assertTrue(short)
        for r in short:                                       # short text is unchanged: no More, no tooltip
            self.assertEqual((r["cut"], r["more"], r["title"], r["text"]), (False, False, "", "No response yet"))
        self.assertTrue(all(r["tab"] == 0 for r in rows))

    def test_narrow_width_and_enter_opens_the_peek(self):
        self.b.resize(700, 900)
        self.open_cockpit()
        long = next(r for r in self.rows() if r["text"] == LONG)
        self.assertTrue(long["cut"] and long["more"])
        self.assertLessEqual(long["lines"], 2)
        self.b.eval(f"document.querySelector('#v-cockpit .rkrow[data-open=\"{long['id']}\"]').focus()")
        self.b.key("Enter")
        self.b.wait("document.getElementById('panel').classList.contains('on')")
        self.assertEqual(self.b.eval("CUR&&CUR.id"), long["id"].split(":")[1])
        self.assertIn(LONG[:60], self.b.eval("document.getElementById('panel').textContent"))

    def test_latest_update_first_then_the_response(self):
        self.assertEqual(self.b.eval("[rkText({upd:'Update',resp:'Response'}),rkText({upd:' ',resp:'Response'}),rkText({})]"),
                         ["Update", "Response", "No response yet"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
