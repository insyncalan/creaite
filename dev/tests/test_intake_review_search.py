"""#232-A6 (v2.6.0): the Search box on the Intake page (client side). It filters the meeting and file rows by title and project name and
the mail, Teams and other proposals by title, project name and source; every word typed must match; Esc clears it; a private or
confidential meeting is found by its title only.

Run: python3 dev/tests/test_intake_review_search.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

MAIL = "#v-intake-review [data-irsec=mail]"


class Search(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval("irQuery.value=''; irOpen.value=null; irSetView('list'); irStage.value='all'")
        S.open_page(self.b)

    def type(self, text):
        self.b.eval("(t=>{ const el=document.querySelector('#irQ'); el.value=t; el.dispatchEvent(new Event('input',{bubbles:true})); })(%s)" % json.dumps(text))
        self.b.wait(f"irQuery.value===({json.dumps(text)})")

    def mail_titles(self):
        return self.b.eval(f"[...document.querySelector('{MAIL}').parentElement.querySelectorAll('tr.irprop .icttl')].map(x=>x.textContent)")

    def meetings(self):
        return self.b.eval("[...document.querySelectorAll('#v-intake-review [data-irv=list] tr[data-irm]')].map(r=>r.querySelector('.icmeethd').textContent)")

    def test_a_search_box_sits_first_in_the_toolbar(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelector('.rvtools').firstElementChild.id"), "irQ")
        self.assertEqual(b.eval("document.querySelector('#irQ').getAttribute('aria-label')"), "Search")
        self.assertEqual(b.eval("document.querySelectorAll('#rvQ').length"), 0)                       # the earlier Review page (and its #rvQ) is gone; its id is not reused
        self.assertEqual(len(self.mail_titles()), 4)

    def test_typing_filters_meetings_by_title_and_mail_rows_by_title(self):
        self.type("pilot")
        self.b.wait("document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.querySelectorAll('tr.irprop').length===1")
        self.assertEqual(self.mail_titles(), ["Share the pilot plan with the client"])
        self.assertEqual(self.meetings(), [])
        self.assertIn("Nothing matches your search.", self.b.eval("document.querySelector('[data-irv=list] .empty').textContent"))
        self.type("steering")
        self.b.wait("document.querySelectorAll('#v-intake-review [data-irv=list] tr[data-irm]').length===2")
        self.assertEqual(sorted(self.meetings()), ["ABC Steering", "Example steering"])                  # a file's name is its title too
        self.type("weekly SYNC")                                                                         # any case, every word
        self.b.wait("document.querySelectorAll('#v-intake-review [data-irv=list] tr[data-irm]').length===1")
        self.assertEqual(self.meetings(), ["ABC weekly sync.vtt"])

    def test_mail_rows_are_found_by_their_source_and_by_the_project_name(self):
        self.type("residency")                                                                         # the subject of three mails, though only one title says it
        self.b.wait("document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.querySelectorAll('tr.irprop').length===3")
        self.assertIn("Confirm data residency with legal", self.mail_titles())
        self.assertNotIn("Supplier may miss the November delivery", self.mail_titles())                # a Teams chat
        self.type("teams omar")                                                                        # every word must match, in any field
        self.b.wait("document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.querySelectorAll('tr.irprop').length===1")
        self.assertEqual(self.mail_titles(), ["Supplier may miss the November delivery"])
        self.type("example programme")                                                                 # the project's name
        self.b.wait("document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.querySelectorAll('tr.irprop').length===4")
        self.assertIn("Example steering", self.meetings())

    def test_esc_clears_it_and_the_stage_counts_stay_whole(self):
        b = self.b
        before = b.eval("document.querySelector('[data-irstage=all] .v').textContent")
        self.type("zzzz")
        b.wait("document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.querySelectorAll('tr.irprop').length===0")
        self.assertIn("Nothing from mail or Teams matches your search.", b.eval("document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.innerText"))
        self.assertEqual(b.eval("document.querySelector('[data-irstage=all] .v').textContent"), before)
        b.eval("document.querySelector('#irQ').focus(); document.querySelector('#irQ').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}))")
        b.wait("irQuery.value===''")
        self.assertEqual(b.eval("document.querySelector('#irQ').value"), "")
        self.assertEqual(len(self.mail_titles()), 4)

    def test_a_confidential_meeting_is_found_by_its_title_only(self):
        b = self.b
        mid = b.eval("D.intake_review.meetings.find(m=>m.title==='Example steering').id")
        b.eval("(id=>{ D.intake_review={...D.intake_review, meetings: D.intake_review.meetings.map(m=>m.id===id?{...m,confidential:true,p:'ABC'}:m)}; irTick.value++; })(%s)" % json.dumps(mid))
        self.type("example programme")                                                                 # its project's name does not find it
        self.b.wait("document.querySelector('#v-intake-review [data-irsec=mail]').parentElement.querySelectorAll('tr.irprop').length===4")
        self.assertNotIn("Example steering", self.meetings())
        self.type("steering")                                                                          # its title does
        self.b.wait("document.querySelectorAll('#v-intake-review [data-irv=list] tr[data-irm]').length===2")
        self.assertIn("Example steering", self.meetings())


if __name__ == "__main__":
    unittest.main()
