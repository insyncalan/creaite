"""#232-0 (v2.5.0): Intake's folding rules and live counts (src/core/irFold.js), run under Node: no browser.
One click opens a meeting with proposals and one closes it; one open at a time; an apply never closes it; Later and Not needed
start folded; the stage counts are a filter; Approve routine never reaches the first group; Esc closes the peek first."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

FOLD = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core/irFold.js"

MODEL = {"meetings": [{"id": "m1", "stage": "drafted", "state": "proposals", "groups": {"needs": [1, 2], "routine": [3, 4]}},
                      {"id": "m2", "stage": "drafted", "state": "proposals", "groups": {"needs": [], "routine": [5]}},
                      {"id": "m3", "stage": "arrived", "state": "ready", "groups": {"needs": [], "routine": []}},
                      {"id": "m4", "stage": "arrived", "state": "waiting", "groups": {"needs": [], "routine": []}},
                      {"id": "m5", "stage": "approved", "state": "done", "groups": {"needs": [], "routine": []}}],
         "mail": {"needs": [6], "routine": [7]}, "other": {"needs": [], "routine": []}, "later": [], "not_needed": [], "counts": {}}

SCRIPT = """
const f = await import(%s); const M = %s; const none = () => false, d = s => n => s.includes(n);
const out = {};
out.open1 = f.irToggle(null, "m1", M); out.close1 = f.irToggle("m1", "m1", M); out.switch = f.irToggle("m1", "m2", M);
out.noopen = f.irToggle(null, "m3", M); out.noopenKeeps = f.irToggle("m1", "m5", M);
out.keep = f.irKeepOpen("m1", M); out.keepAllDone = f.irKeepOpen("m2", M); out.gone = f.irKeepOpen("m9", M); out.none = f.irKeepOpen(null, M);
out.groups = f.irGroupsShown(M.meetings[0].groups, none); out.groupsAfter = f.irGroupsShown(M.meetings[0].groups, d([1, 2]));
out.groupsEmpty = f.irGroupsShown(M.meetings[1].groups, d([5]));
out.bulk = f.irBulk(M.meetings[0].groups, d([3])); out.bulkMail = f.irBulk(M.mail, none);
out.stage = [f.irStageClick("all", "drafted"), f.irStageClick("drafted", "drafted"), f.irStageClick("drafted", "all"), f.irStageClick("all", "bogus")];
out.filtered = f.irFiltered(M, "arrived").map(m => m.id);
out.fold = [f.irIsFolded({}, "later"), f.irIsFolded({}, "not_needed"), f.irIsFolded({}, "mail"), f.irIsFolded({}, "meetings")];
const f1 = f.irFoldClick({}, "later"), f2 = f.irFoldClick(f1, "later"), f3 = f.irFoldClick({}, "mail");
out.foldClicks = [f.irIsFolded(f1, "later"), f.irIsFolded(f2, "later"), f.irIsFolded(f3, "mail")];
out.counts = f.irCounts(M, none); out.countsAfter = f.irCounts(M, d([5, 6]));
const up = (path, ft) => ({ id: "u" + path, src: "upload", path, ft, stage: "arrived", state: "ready", groups: { needs: [], routine: [] } });
const U = { ...M, meetings: [...M.meetings, up("inbox/a.docx", "")] };
out.unsureCounts = f.irCounts(U, none); out.chosenCounts = f.irCounts(U, none, { "inbox/a.docx": "minutes" });
out.kinds = [f.irKindOf(up("p", "transcript")), f.irKindOf(up("p", "transcript"), { p: "minutes" }), f.irKindOf(up("p", "")), f.irKindOf({ src: "calendar" })];
out.esc = [f.irEsc({peek: 3, open: "m1"}), f.irEsc({peek: null, open: "m1"})];
out.views = [f.irViewNorm("board"), f.irViewNorm("two"), f.irViewNorm("nonsense"), f.irViewNorm(null)];
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "needs Node")
class FoldRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        js = SCRIPT % (json.dumps(FOLD.as_uri()), json.dumps(MODEL))
        r = subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        cls.o = json.loads(r.stdout)

    def test_one_click_opens_one_closes_one_at_a_time(self):
        o = self.o
        self.assertEqual((o["open1"], o["close1"], o["switch"]), ("m1", None, "m2"))
        self.assertIsNone(o["noopen"])                          # nothing to check: it never opens
        self.assertEqual(o["noopenKeeps"], "m1")                # a click on such a row leaves the open one open

    def test_an_apply_or_refresh_never_closes_the_open_meeting(self):
        self.assertEqual((self.o["keep"], self.o["keepAllDone"]), ("m1", "m2"))
        self.assertIsNone(self.o["gone"])                       # only when it has left the list
        self.assertIsNone(self.o["none"])

    def test_groups_needs_first_then_routine_and_empty_ones_left_out(self):
        self.assertEqual(self.o["groups"], [{"kind": "needs", "ns": [1, 2], "open": True}, {"kind": "routine", "ns": [3, 4], "open": True}])
        self.assertEqual(self.o["groupsAfter"], [{"kind": "routine", "ns": [3, 4], "open": True}])
        self.assertEqual(self.o["groupsEmpty"], [])

    def test_approve_routine_never_covers_the_first_group(self):
        self.assertEqual(self.o["bulk"], [4])
        self.assertEqual(self.o["bulkMail"], [7])

    def test_stage_counts_are_a_filter(self):
        self.assertEqual(self.o["stage"], ["drafted", "all", "all", "all"])
        self.assertEqual(self.o["filtered"], ["m3", "m4"])

    def test_later_and_not_needed_start_folded_and_toggle(self):
        self.assertEqual(self.o["fold"], [True, True, False, False])
        self.assertEqual(self.o["foldClicks"], [False, True, True])

    def test_live_counts_follow_decisions_on_the_page(self):
        self.assertEqual(self.o["counts"], {"arrived": 2, "ready": 1, "drafted": 2, "approved": 1, "to_approve": 7, "badge": 8, "all": 5, "need_type": 0})
        self.assertEqual(self.o["countsAfter"], {"arrived": 2, "ready": 1, "drafted": 1, "approved": 2, "to_approve": 5, "badge": 6, "all": 5, "need_type": 0})        # Show all: every meeting and file, whatever its stage

    def test_a_file_that_is_not_sure_is_not_ready(self):
        o = self.o
        self.assertEqual((o["unsureCounts"]["ready"], o["unsureCounts"]["need_type"], o["unsureCounts"]["badge"]), (1, 1, 8))      # m3 is a file of unknown kind
        self.assertEqual((o["chosenCounts"]["ready"], o["chosenCounts"]["need_type"]), (2, 0))                              # its chosen kind makes it ready
        self.assertEqual(o["kinds"], ["transcript", "minutes", "", "transcript"])

    def test_esc_closes_the_peek_first_then_the_meeting(self):
        self.assertEqual(self.o["esc"], [{"peek": None, "open": "m1"}, {"peek": None, "open": None}])

    def test_the_view_choice_is_made_safe(self):
        self.assertEqual(self.o["views"], ["board", "two", "list", "list"])


if __name__ == "__main__":
    unittest.main()
