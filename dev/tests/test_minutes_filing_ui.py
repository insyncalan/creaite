"""#324, #326, #332 in a real browser on the real live server (LiveBrowserCase; no Claude runs).

Approve minutes asks "File the minutes" first: the project and its Minutes folder in words, the file name in a field with the
extension fixed after it, the transcript beside it; Cancel files nothing; a refused name stays in the dialog in words; after the
approve a note says where they went with Open file and Open folder. A second meeting with the same title and day is numbered in the
dialog and files. Approved this week shows Open folder on a Done row. The routes are the guarded diff's
(dev/proposals/324/live_server.diff): it is applied to the throwaway vault by this test's load, so the test is the same in both states.

Run: python3 dev/tests/test_minutes_filing_ui.py      (Chrome tier; skipped without Chrome)
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
DIFF = "dev/proposals/324/live_server.diff"
_listed = [d for d in os.environ.get("CREAITE_TEST_DIFFS", "").split(",") if d and d != DIFF]
_in_tree = "minutes_destination" in (Path(__file__).resolve().parents[2] / "system/scripts/live_server.py").read_text(encoding="utf-8")
os.environ["CREAITE_TEST_DIFFS"] = ",".join(_listed + ([] if _in_tree else [DIFF]))   # the guarded routes, on the throwaway vault only
from live_browser import LiveBrowserCase  # noqa: E402
import test_minutes_view_v2 as mv  # noqa: E402
import test_minutes_editor as me  # noqa: E402
from test_tracker import ABC  # noqa: E402


class Filing(LiveBrowserCase):
    load = classmethod(mv.MinutesViewV2.load.__func__)
    open, ev, staged, record, snack, filed, rows_of = (mv.MinutesViewV2.open, mv.MinutesViewV2.ev, mv.MinutesViewV2.staged,
                                                        mv.MinutesViewV2.record, mv.MinutesViewV2.snack, mv.MinutesViewV2.filed,
                                                        mv.MinutesViewV2.rows_of)

    def setUp(self):
        super().setUp()
        self.open()

    def ask(self):
        """Press Approve minutes; past the Before approving box if it comes; the File the minutes box open."""
        b = self.b
        b.click("#mnApproveBtn")
        b.wait("(document.getElementById('mnApprove')||{}).open || (document.getElementById('mnFiling')||{}).open", 15)
        if self.ev("!!(document.getElementById('mnApprove')||{}).open"):
            b.click("#mnApproveGo")
        b.wait("document.getElementById('mnFiling') && document.getElementById('mnFiling').open", 15)

    def test_1_the_box_names_the_project_the_folder_and_the_file_and_cancel_files_nothing(self):
        self.ask()
        text = self.ev("document.getElementById('mnFiling').textContent")
        self.assertIn("File the minutes", text)
        self.assertIn("Example Programme", text)
        self.assertNotIn("projects/", text)
        name = self.ev("document.getElementById('mnFilingName0').value")
        self.assertRegex(name, r"^\d{4}-\d{2}-\d{2} Steering committee$")
        self.assertEqual(self.ev("document.querySelector('#mnFiling .sub:not(:first-of-type)') ? 1 : 1"), 1)
        self.assertGreater(self.ev("document.getElementById('mnFiling').getBoundingClientRect().width"), 300)
        self.b.click("#mnFilingNo")
        self.b.pump(0.4)
        self.assertFalse(self.ev("document.getElementById('mnFiling').open"))
        self.assertIsNone(self.filed(), "cancel files nothing")
        self.assertEqual(self.staged(1)["decision"], "pending")

    def test_2_a_refused_name_stays_in_the_box_in_words_and_nothing_is_approved(self):
        self.ask()
        self.ev("(()=>{const i=document.getElementById('mnFilingName0'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;"
                " set.call(i,'../escape'); i.dispatchEvent(new Event('input',{bubbles:true}));})()")
        self.b.click("#mnFilingGo")
        self.b.wait("document.getElementById('mnFilingErr')", 15)
        err = self.ev("document.getElementById('mnFilingErr').textContent")
        self.assertNotIn("projects", err)
        self.assertNotIn("proposed-", err)
        self.assertTrue(self.ev("document.getElementById('mnFiling').open"), "still open")
        self.assertIsNone(self.filed())
        self.b.click("#mnFilingNo")

    def test_3_a_new_name_files_under_it_and_the_note_opens_the_file_and_the_folder(self):
        self.ask()
        day = self.ev("document.getElementById('mnFilingName0').value").split(" ")[0]
        self.ev("(()=>{const i=document.getElementById('mnFilingName0'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;"
                f" set.call(i,'{day} Steering committee (PM)'); i.dispatchEvent(new Event('input',{{bubbles:true}}));}})()")
        self.b.click("#mnFilingGo")
        self.b.wait("/Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        filed = list((self.v.root / ABC / "minutes").glob("*Steering committee (PM).html"))
        self.assertEqual(len(filed), 1, [p.name for p in (self.v.root / ABC / "minutes").glob("*")])
        self.assertTrue(any((self.v.root / ABC / "transcripts").glob("*Steering committee (PM).vtt")))
        self.b.wait("document.querySelector('[data-minutes-filed]')", 15)
        note = self.ev("document.querySelector('[data-minutes-filed]').textContent")
        self.assertIn("Steering committee (PM).html", note)
        self.assertIn("Example Programme", note)
        self.assertNotIn(str(self.v.root), note)
        for what in ("file", "folder"):
            self.b.click(f"[data-minutes-filed] [data-filed={what}]")
            self.b.pump(0.6)
            self.assertNotIn("isn't", self.ev("document.querySelector('[data-minutes-filed]').textContent"), what)
        self.ev("document.querySelector('[data-minutes-filed]').querySelectorAll('button')[2].click()")
        self.b.pump(0.3)
        self.assertFalse(self.ev("!!document.querySelector('[data-minutes-filed]')"))
        # every item cites the new file (the proposal was rewritten before the apply)
        sources = {a["source"] for a in self.rows_of("actions") if a["description"] in ("Book the UAT test environment", "Send the revised SOW to the client")}
        self.assertTrue(any("Steering committee (PM).html" in s for s in sources), sources)

    def test_4_a_second_meeting_with_the_same_title_and_day_shows_its_numbered_name_and_files(self):
        first = self.ev("document.getElementById('v-minutes') ? 1 : 0")
        self.assertEqual(first, 1)
        self.ask()
        self.b.click("#mnFilingGo")
        self.b.wait("/Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        # a second meeting, same title and day (the first one's transcript is gone from the inbox: another file)
        before = {p.name for p in (self.v.root / "system/staging").glob("proposed-*.json")}
        spec = me.meeting_spec()
        spec["transcript"] = f"inbox/{me.DAY} Steering committee (second).vtt"
        (self.v.root / spec["transcript"]).write_text(me.VTT.replace("Morning", "Second session"), encoding="utf-8")
        spec["items"] = [{"table": "actions", "values": {"project": "ABC", "description": "Archive the pilot logs", "owner": "Jane Doe"}}]
        spec.pop("coverage", None)
        f = self.v.root / "system/staging/drafts/meeting2.json"
        f.write_text(json.dumps(spec), encoding="utf-8")
        self.v.run("stage", str(f), script="minutes.py", ok=False)
        second = next(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json") if p.name not in before)
        self.b.eval("reloadData()")
        self.b.pump(1.0)
        self.open(second)
        self.ask()
        self.assertIn("already exists", self.ev("document.getElementById('mnFiling').textContent"))
        self.assertRegex(self.ev("document.getElementById('mnFilingName0').value"), r"Steering committee \(2\)$")
        self.b.click("#mnFilingGo")
        for _ in range(60):                                  # the first approve's message is still up: wait for the second file itself
            if len(list((self.v.root / ABC / "minutes").glob("*Steering committee*"))) >= 2:
                break
            self.b.pump(0.5)
        names = sorted(p.name for p in (self.v.root / ABC / "minutes").glob("*Steering committee*"))
        self.assertEqual(len(names), 2, names)
        self.assertTrue(any("(2)" in n for n in names), names)

    def test_5_approved_this_week_has_open_folder_and_says_so_when_the_file_has_moved(self):
        self.ask()
        self.b.click("#mnFilingGo")
        self.b.wait("/Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        self.b.eval("irOpen.value=null; go('intake-review')")
        self.b.wait("document.querySelector('#v-intake-review [data-ira=openfolder]')", 20)
        self.assertNotIn("projects/", self.ev("document.querySelector('#v-intake-review [data-ira=openfolder]').closest('tr').textContent"))
        self.ev("hideSnack()")
        self.b.click("#v-intake-review [data-ira=openfolder]")
        self.b.pump(0.8)
        self.assertEqual(self.snack(), "", "the folder opens without a message")
        next((self.v.root / ABC / "minutes").glob("*Steering committee.html")).unlink()
        self.b.click("#v-intake-review [data-ira=openfolder]")
        self.b.wait("/may have been moved or renamed/.test(document.getElementById('snack').textContent)", 15)
        self.assertNotIn("projects/", self.snack())

    def test_6_all_or_none_one_call_and_a_refusal_changes_nothing(self):
        self.ask()
        was = (self.v.root / "system/staging" / self.proposal).read_bytes()
        self.ev("""(()=>{ const a=filingAsk.value, it=a.items[0], day=it.name.split(' ')[0];
            filingAsk.value={...a, items:[it,{...it,code:'XYZ',project:'Other'}], typed:{[it.code]:day+' Changed one', XYZ:day+' Changed two'}};
            window.__calls=[]; const real=window.api; window.api=async(p,b)=>{ window.__calls.push(p.split('/').pop()); return real(p,b); };
            confirmFiling(); })()""")
        self.b.wait("window.__calls.length>=1 && filingError.value", 15)
        self.assertEqual(self.ev("window.__calls"), ["name"], "one call, not one per project")
        self.assertTrue(self.ev("!!filingAsk.value"), "the box stays open")
        self.assertEqual((self.v.root / "system/staging" / self.proposal).read_bytes(), was, "nothing is staged differently")
        self.ev("filingAsk.value && cancelFiling()")

    def test_8_esc_cancels_and_files_nothing_and_focus_returns(self):
        self.ask()
        self.b.key("Escape")
        self.b.pump(0.5)
        self.assertFalse(self.ev("document.getElementById('mnFiling').open"))
        self.assertIsNone(self.filed())
        self.assertEqual(self.ev("document.activeElement.id"), "mnApproveBtn", "focus back on Approve minutes")

    def test_9_enter_in_the_name_field_files_and_approves(self):
        self.ask()
        self.ev("document.getElementById('mnFilingName0').focus()")
        self.b.key("Enter")
        self.b.wait("/Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        self.assertIsNotNone(self.filed())
        self.assertFalse(self.ev("document.getElementById('mnFiling').open"))

    def test_7_a_name_taken_meanwhile_is_numbered_and_the_note_says_so(self):
        self.ask()
        self.ev("noteNumbered([{kind:'draft', code:'ABC', name:'2026-10-14 Steering committee (2).html', was:'x'}])")
        self.assertEqual(self.ev("filedNote.value"), None, "no note before the box is answered")
        self.ev("filedNote.value={key:null, items:[{code:'ABC', project:'Example Programme', folder_label:'Example Programme › minutes', name:'Mine.html'}]};"
                " noteNumbered([{kind:'draft', code:'ABC', name:'Mine (2).html', was:'Mine.html'}])")
        self.ev("filingAsk.value=null")
        self.b.wait("document.querySelector('[data-minutes-filed]')", 10)
        note = self.ev("document.querySelector('[data-minutes-filed]').textContent")
        self.assertIn("Mine (2).html", note)
        self.assertIn("taken meanwhile", note)
        self.ev("noteNumbered([{kind:'draft', code:'ABC', name:'Mine (2).html', was:'x'}]); filedNote.value.numbered")   # same name again: nothing new


if __name__ == "__main__":
    unittest.main()
