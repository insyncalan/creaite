"""#232 C2 (v2.6.0): the old Intake and Review pages are gone, and nothing imports what went with them.

Run: python3 dev/tests/test_intake_retired_names.py   (no browser)

The old pages' code (`renderReview`, the focus view, the select bar, `#v-review`/`#v-inbox` and their `boot…` steps) was removed in
2.6.0; `intake.js` and `review.js` are thinned, not deleted (Q12): every name something else imports stays, under the same name.
This test keeps it that way:
- no module imports a retired name (from any module);
- nothing imports from `intake.js` (an empty shell that only re-exports core/intakeApi.js, to be deleted in a later release);
- the shell has no `#v-review`, `#v-inbox`, `#reviewBody` or `#inboxTbl`;
- the Intake survivors (the names `intake.js` used to export that something else still needs) are exported by core/intakeApi.js.
"""
import re
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "system" / "templates" / "dashboard"

# what the old pages exported and no one needs now (a name that is still imported somewhere is a survivor, not on this list)
RETIRED = """
renderReview renderInbox renderMeetings processMeetings processInbox addInboxFiles mtgCanPick mtgState mtgTx mtgProject loadMeetings removeLoaded
mtgClear mtgRestore clrConfirm clrList clrOff clrKeys clrUnproc MCLR MSEL INSEL INRUN INSTATE MTGI MTGSHOW TXLABEL mtgHasTx mtgLoadable mtgShown
uploadedFiles inboxBadge intakeHooks
bootIntake0053 bootIntake0134 bootIntake0135 bootIntake0136 bootIntake0137
bootReview0060 bootReview0061 bootReview0063 bootReview0064 bootReview0065 bootReview0067 bootReview0193 bootReview0195 bootReview0209 bootReview0315
bootToday0027
revRow rvRender rvBar rvDock rvSel rvPaint rvOnly rvPick rvTick rvOrder rvSyncChk rvBarProps drawReviewFilters rvApplied rvRoutineBtn rvChanged
rvApproveSelected rvRejectSelected rvRoutine rvPreview rvSet rvCheck rvLearnCard rvAdvance rvMatching rvPasses rvQOK rvShown rvDef rvDate
rvEmptyHtml rvHintHtml rvAgeBanner rvOutlier rvAllOld rvAgeText rvStaleDays rvDrawDisp rvDispClose rvMoveTo rvMoveItem rvMoveMinutes rvMovePreview rvItemState
rfOpen rfClose rfAct rfDraw rfQueue rfRoutine rfKey rfSave rfFields RFF
toggleGroup approveGroup kidsOf routineKid COLLAPSED rvMovable rvLeftOut rvActive rvBlocks rvBlocks0 rvSrcLink rvSrcKind rvNeeds rvOwner
CHK RHL RVF RVNEG RVQ RVG RVO RVPK RVFIELDS RVKINDS RVORD RVSETF RVLASTUNDO RVLASTN RVLASTV RVSHOWN RVINBATCH RVWHY
cxReview cxReviewMany cxReviewFields cxGone cxPk rjGoneRow rjPlace rjKey315 rjGuessHtml rjWith
pkFollowRev rvfCount rvHold rvRestore mRowGone mFileAt
""".split()

IMPORT = re.compile(r"import\s*(?:[\w$]+\s*,\s*)?\{([^}]*)\}\s*from\s*[\"']([^\"']+)[\"']", re.S)
EXPORT_NAMES = re.compile(r"export\s+(?:async\s+)?(?:function\*?|const|let|var|class)\s+([A-Za-z_$][\w$]*)")


def sources():
    for p in sorted((SRC / "src").rglob("*")):
        if p.suffix in (".js", ".jsx"):
            yield p


WANT = {"MTG", "MRUN", "mtgBusy", "mtgLater", "mtgSkip", "mtgCheckable", "TXWHY", "UPLOAD_TYPES", "UPLOAD_MAX", "uploadInboxFile",
        "previewInbox", "removeInbox", "refreshCalendar", "checkMeeting", "jobLive", "kb", "nowHM", "intakeSeams"}


class RetiredNames(unittest.TestCase):
    def test_nothing_imports_a_retired_name(self):
        bad = []
        for p in sources():
            for m in IMPORT.finditer(p.read_text(encoding="utf-8")):
                names = {n.strip().split(" as ")[0].strip() for n in m.group(1).split(",")}
                hit = sorted(names & set(RETIRED))
                if hit:
                    bad.append(f"{p.relative_to(SRC)} imports {', '.join(hit)} from {m.group(2)}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_no_module_declares_a_retired_name_again(self):
        bad = []
        for p in sources():
            names = set(EXPORT_NAMES.findall(p.read_text(encoding="utf-8")))
            hit = sorted(names & set(RETIRED))
            if hit:
                bad.append(f"{p.relative_to(SRC)} exports {', '.join(hit)}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_nothing_imports_the_empty_intake_shell(self):
        bad = [str(p.relative_to(SRC)) for p in sources() if p.name != "intake.js"
               and any(Path(p.parent, m.group(2)).resolve() == (SRC / "src" / "intake.js").resolve() for m in IMPORT.finditer(p.read_text(encoding="utf-8")))]
        self.assertEqual(bad, [], "these still import intake.js (import core/intakeApi.js instead): " + ", ".join(bad))
        shell = (SRC / "src" / "intake.js").read_text(encoding="utf-8")
        self.assertEqual(EXPORT_NAMES.findall(shell), [], "intake.js only re-exports core/intakeApi.js")
        self.assertIn('export * from "./core/intakeApi.js"', shell)

    def test_the_shell_html_has_no_old_page(self):
        html = (SRC / "shell.html").read_text(encoding="utf-8")
        for old in ('id="v-review"', 'id="v-inbox"', 'id="reviewBody"', 'id="inboxTbl"', 'id="mtgBody"', 'id="rvbar"'):
            self.assertNotIn(old, html, old)
        self.assertIn('id="v-intake-review"', html)

    def test_the_intake_survivors_live_in_intake_api(self):
        api = (SRC / "src" / "core" / "intakeApi.js").read_text(encoding="utf-8")
        have = {n for n in WANT if re.search(r"export\s+(?:async\s+)?(?:function|const|let)\s+[^;]*?\b" + n + r"\b", api)}
        want = WANT
        self.assertEqual(sorted(want - have), [])
        # the hooks the old pages used to redraw are gone
        self.assertNotIn("intakeHooks", api)

    def test_old_addresses_still_open_the_one_page(self):
        nav = (SRC / "src" / "core" / "nav.js").read_text(encoding="utf-8")
        self.assertIn('if(v==="review"||v==="inbox"||v==="intake") v="intake-review"', nav)
        self.assertNotIn("legacy", nav)          # the Z0 option that kept drawing the old page is gone


if __name__ == "__main__":
    unittest.main()
