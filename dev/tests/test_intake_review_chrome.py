"""#232-A2 to A4 (v2.6.0): the head of the Intake page, in a real browser against the live server (the locked mockup, 19-10-2026).
The heading and the sub-line with "Calendar read hh:mm" and its refresh icon (A2), the Add files icon and the full-page "Drop to add
files" overlay (A3), the stage boxes with icons and Show all as the fourth box (A4).

Run: python3 dev/tests/test_intake_review_chrome.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from ir_intake_support import DAY, IntakeBase  # noqa: E402


class Head(IntakeBase):
    shared_server = True

    def sub(self):
        return self.b.eval("document.querySelector('#irSub').textContent.replace(/\\s+/g,' ').trim()")

    def test_the_heading_is_intake_and_the_earlier_pages_banner_is_gone(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelector('#irTitle').textContent"), "Intake")
        self.assertEqual(b.eval("!!document.querySelector('#v-intake-review .irold')"), False)
        self.assertNotIn("being built", b.eval("document.getElementById('v-intake-review').innerText"))
        self.assertEqual(b.eval("document.querySelector('.irpage [role=group][aria-label^=\"How you see\"]').getAttribute('aria-label')"), "How you see Intake")

    def test_the_sub_line_says_when_the_calendar_was_read_and_the_icon_reads_it_again(self):
        b = self.b
        self.assertRegex(self.sub(), r"^\d+ ready to process · \d+ proposals? to approve · Calendar read 07:00$")    # read today at 07:00: the time only
        self.assertEqual(b.eval("document.querySelector('#icRef').getAttribute('aria-label')"), "Refresh the calendar")
        self.assertFalse(b.eval("document.querySelector('#icRef').disabled"))

    def test_a_calendar_read_on_another_day_shows_its_date_and_none_says_so(self):
        b = self.b
        for fetched, words in (("2026-10-03 09:15", "Calendar read 03-10-2026 09:15"), (None, "No calendar yet")):
            b.eval("(f=>{ D.meetings={...D.meetings, fetched:f}; irTick.value++; })(%s)" % json.dumps(fetched))
            b.wait(f"document.querySelector('#irSub').textContent.includes({json.dumps(words)})")

    def test_refresh_runs_once_through_its_route_with_the_panel_closed_and_the_time_advances(self):
        b = self.b
        self.stage_stub()
        path = self.v.root / "system/staging/calendar.json"
        cal = json.loads(path.read_text())
        self.addCleanup(path.write_text, json.dumps(cal))                  # the server is shared: the next test reads the same calendar
        b.eval("GATE=new Promise(r=>{ window.RELEASE=r; }); 0")              # the sweep's calendar write happens in the test, before the release
        b.click("#icRef")
        b.wait("irRefreshing.value===true")
        self.assertIn("Refreshing…", self.sub())
        self.assertEqual(b.eval("document.querySelector('#icRef').getAttribute('aria-label')"), "Stop the refresh")   # #265: Stop while it runs
        self.assertEqual(b.eval("CALRUNS.length"), 1)                                                  # one run at a time
        self.assertFalse(b.eval("document.getElementById('chat') ? document.getElementById('chat').classList.contains('on') || !document.getElementById('chat').hidden && document.getElementById('chat').offsetParent!==null : false"))
        path.write_text(json.dumps({**cal, "fetched": f"{DAY} 10:42"}))
        b.eval("RELEASE()")
        b.wait("irRefreshing.value===false && document.querySelector('#irSub').textContent.includes('Calendar read 10:42')", 30)
        self.assertEqual([q for q, _ in b.eval("ASKED")], ["refresh calendar"])
        self.assertEqual(b.eval("CHAT"), [])
        self.assertFalse(b.eval("document.querySelector('#icRef').disabled"))

    def test_the_refresh_icon_waits_while_ask_creaite_works(self):
        b = self.b
        b.eval("irAsk.value=true")
        b.wait("document.querySelector('#icRef').disabled")
        b.eval("irAsk.value=false")
        b.wait("!document.querySelector('#icRef').disabled")


class AddFiles(IntakeBase):
    shared_server = True

    def drag(self, target, kind="dragover"):
        self.b.eval("""(()=>{ const dt=new DataTransfer(); dt.items.add(new File(['x'],'a.vtt'));
          document.querySelector(%s).dispatchEvent(new DragEvent(%s,{dataTransfer:dt,bubbles:true,cancelable:true})); })()""" % (json.dumps(target), json.dumps(kind)))

    def test_add_files_is_an_icon_button_with_a_hidden_file_input(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelector('[data-irpick]').textContent.trim()"), "")
        self.assertEqual(b.eval("document.querySelector('[data-irpick]').getAttribute('aria-label')"), b.eval("document.querySelector('[data-irpick]').dataset.tip"))   # BL-158: named with its tip's words (C2)
        self.assertTrue(b.eval("document.querySelector('[data-irpick]').getAttribute('aria-label')").startswith("Add files"))
        self.assertIn("drop them anywhere", b.eval("document.querySelector('[data-irpick]').dataset.tip"))
        self.assertEqual(b.eval("!!document.querySelector('[data-irpick] svg[data-iric=upload]')"), True)
        self.assertEqual(b.eval("(i=>[i.type,i.multiple,i.hidden,i.accept])(document.querySelector('#v-intake-review input[type=file]'))"),
                         ["file", True, True, ".vtt,.docx,.txt,.md,.pdf"])

    def test_a_full_page_overlay_shows_while_files_are_dragged_over_and_never_takes_the_pointer(self):
        b = self.b
        self.assertFalse(b.eval("document.querySelector('.icdrop').classList.contains('on')"))
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.icdrop')).display"), "none")
        self.drag("#v-intake-review h1")
        b.wait("document.querySelector('.icdrop').classList.contains('on')")
        self.assertEqual(b.eval("(r=>[r.width===innerWidth, r.height===innerHeight])(document.querySelector('.icdrop').getBoundingClientRect())"), [True, True])
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.icdrop')).pointerEvents"), "none")    # a drop on ask creaite's panel still reaches it
        self.assertIn("Drop to add files", b.eval("document.querySelector('.icdrop').innerText"))
        self.assertIn(".vtt, .docx, .txt, .md or .pdf, up to 25 MB", b.eval("document.querySelector('.icdrop').innerText"))
        b.eval("document.dispatchEvent(new DragEvent('dragleave',{bubbles:true}))")
        b.wait("!document.querySelector('.icdrop').classList.contains('on')")

    def test_the_overlay_stays_away_over_the_ask_panel_and_after_a_drop(self):
        b = self.b
        self.drag("#chat")
        self.assertFalse(b.eval("document.querySelector('.icdrop').classList.contains('on')"))
        self.drag("#v-intake-review h1")
        b.wait("document.querySelector('.icdrop').classList.contains('on')")
        self.drag("#v-intake-review h1", "drop")
        b.wait("!document.querySelector('.icdrop').classList.contains('on')")
        b.wait("D.intake_review.meetings.some(m=>m.title==='a.vtt' && m.src==='upload')", 30)
        (self.v.root / "inbox" / "a.vtt").unlink(missing_ok=True)

    def test_the_entry_points_other_screens_call(self):
        """irPickFiles opens the chooser from anywhere; irProcessById takes a row id, an event ID or a file path."""
        b = self.b
        b.eval("""window.PICKED=[]; window.REALCLICK=HTMLInputElement.prototype.click; HTMLInputElement.prototype.click=function(){ window.PICKED.push([this.type,this.multiple,this.accept,this.isConnected]); }; irPickFiles(); 0""")
        self.addCleanup(lambda: b.eval("HTMLInputElement.prototype.click=window.REALCLICK; 0"))
        self.assertEqual(b.eval("PICKED"), [["file", True, ".vtt,.docx,.txt,.md,.pdf", True]])
        b.eval("document.body.lastElementChild.dispatchEvent(new Event('cancel'))")
        self.assertFalse(b.eval("!!document.querySelector('body > input[type=file]')"))                    # a cancelled chooser leaves nothing behind
        ids = ("ev-1", b.eval("D.intake_review.meetings.find(m=>m.title==='ABC Steering'&&m.src!=='draft').id"))
        for i, ident in enumerate(ids):
            if i:
                self.setUp()                                                                                # a fresh page and no draft for the second id
            self.stage_stub()
            b.eval("irProcessById(%s)" % json.dumps(ident))
            b.wait("ASKED.length===1 && irBusy.value.length===0", 30)
            self.assertEqual(b.eval("ASKED[0][0]"), f"process inbox/{DAY} ABC Steering.vtt")


class StageBoxes(IntakeBase):
    shared_server = True

    def test_four_boxes_with_icons_and_show_all_after_a_rule(self):
        b = self.b
        self.assertEqual(b.eval("[...document.querySelectorAll('.icpipe .evbox')].map(x=>x.dataset.irstage)"), ["arrived", "drafted", "approved", "all"])
        self.assertEqual(b.eval("[...document.querySelectorAll('.icpipe .evbox')].map(x=>!!x.querySelector('.icbi svg'))"), [True] * 4)
        self.assertEqual(b.eval("[...document.querySelectorAll('.icpipe > *')].map(x=>x.className.split(' ')[0])"),
                         ["evbox", "ar", "evbox", "ar", "evbox", "icsep", "evbox"])
        self.assertEqual(b.eval("document.querySelector('.icpipe .icsep').getAttribute('aria-hidden')"), "true")
        self.assertFalse(b.eval("!!document.querySelector('.icpipe button.btn')"))                     # Show all is a box, not a button any more
        self.assertEqual(b.eval("document.querySelector('[data-irstage=all] .l').textContent"), "Show all")
        self.assertEqual(b.eval("document.querySelector('[data-irstage=all] .icsub').textContent"), "meetings and files")

    def test_show_all_counts_every_meeting_and_file_and_the_boxes_are_filters(self):
        b = self.b
        total = b.eval("D.intake_review.meetings.length")
        self.assertGreater(total, 3)
        self.assertEqual(b.eval("+document.querySelector('[data-irstage=all] .v').textContent"), total)
        self.assertEqual(b.eval("irLiveCounts().all"), total)
        self.assertEqual(b.eval("[...document.querySelectorAll('.icpipe .evbox')].map(x=>x.getAttribute('aria-pressed'))"), ["false", "false", "false", "true"])
        b.eval("document.querySelector('[data-irstage=arrived]').click()")
        b.wait("document.querySelector('[data-irstage=arrived]').getAttribute('aria-pressed')==='true'")
        self.assertEqual(b.eval("document.querySelector('[data-irstage=all]').getAttribute('aria-pressed')"), "false")
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-intake-review [data-irv=list] tr[data-irm]')].every(r=>r.dataset.stage==='arrived')"), True)
        b.eval("document.querySelector('[data-irstage=all]').click()")                                 # Show all shows everything again
        b.wait("document.querySelector('[data-irstage=all]').getAttribute('aria-pressed')==='true'")
        self.assertEqual(b.eval("document.querySelectorAll('#v-intake-review [data-irv=list] tr[data-irm]').length"), total)


class Gaps(IntakeBase):
    """#232-A7: the icon on each row, and Two panes' summary line, right-hand words and stage track."""
    shared_server = True

    def setUp(self):
        (self.v.root / "inbox" / "Spare notes.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nNotes\n")
        super().setUp()
        self.b.eval("reloadData().then(()=>irTick.value++)")
        self.b.wait(f"!!{self.row('Spare notes.vtt')}")

    def tearDown(self):
        (self.v.root / "inbox" / "Spare notes.vtt").unlink(missing_ok=True)
        super().tearDown()

    def test_each_row_has_the_icon_of_what_it_is(self):
        b = self.b
        self.assertEqual(b.eval(f"{self.row('ABC Steering')}.querySelector('.ki svg').dataset.iric"), "meeting")
        self.assertEqual(b.eval(f"{self.row('Spare notes.vtt')}.querySelector('.ki svg').dataset.iric"), "file")
        self.assertEqual(b.eval(f"{self.row('Busy')}.querySelector('.ki').getAttribute('aria-hidden')"), "true")        # a picture only: the words beside it carry the meaning

    def test_two_panes_summary_right_hand_words_and_the_stage_track(self):
        b = self.b
        b.eval("document.querySelector('[data-irview=two]').click()")
        b.wait("!!document.querySelector('[data-irv=two] .icsum')")
        c = b.eval("irLiveCounts()")
        self.assertEqual(b.eval("document.querySelector('[data-irv=two] .icsum').textContent"), f"Arrived {c['arrived']} → Drafted {c['drafted']} → Approved {c['approved']}")
        mid = b.eval("D.intake_review.meetings.find(m=>m.title==='ABC Steering'&&m.src==='draft').id")
        self.assertEqual(b.eval(f"document.querySelector('[data-irv=two] tr[data-irm=\"{mid}\"] .irright').textContent"), "4 proposals")
        rid = b.eval("D.intake_review.meetings.find(m=>m.title==='Weekly sync 12').id")
        self.assertEqual(b.eval(f"document.querySelector('[data-irv=two] tr[data-irm=\"{rid}\"] .irright').textContent"), "ready")
        b.eval(f"document.querySelector('[data-irv=two] tr[data-irm=\"{rid}\"]').click()")
        b.wait(f"document.querySelector('[data-irdet]').dataset.irdet==={json.dumps(rid)}")
        self.assertEqual(b.eval("document.querySelector('[data-irdet] .ictrack').dataset.irtrack"), "arrived")
        self.assertEqual(b.eval("[...document.querySelectorAll('[data-irdet] .ictrack i')].map(i=>i.className)"), ["now", "", ""])
        self.assertEqual(b.eval("document.querySelector('[data-irdet] .ictrack').textContent"), "ArrivedDraftedApproved")
        self.assertEqual(b.eval("document.querySelector('[data-irdet] .ictrack span.on').textContent"), "Arrived")
        bid = b.eval("D.intake_review.meetings.find(m=>m.title==='Busy').id")
        b.eval(f"document.querySelector('[data-irv=two] tr[data-irm=\"{bid}\"]').click()")
        b.wait(f"document.querySelector('[data-irdet]').dataset.irdet==={json.dumps(bid)}")
        self.assertIn("Waiting for the transcript. It appears here when the meeting’s transcript arrives.", b.eval("document.querySelector('[data-irdet]').innerText"))
        b.eval(f"document.querySelector('[data-irv=two] tr[data-irm=\"{mid}\"]').click()")
        b.wait(f"document.querySelector('[data-irdet]').dataset.irdet==={json.dumps(mid)}")
        self.assertEqual(b.eval("[...document.querySelectorAll('[data-irdet] .ictrack i')].map(i=>i.className)"), ["done", "now", ""])
        b.eval("document.querySelector('[data-irview=list]').click()")


if __name__ == "__main__":
    unittest.main()
