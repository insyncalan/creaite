"""BL-144: in Activity, a work item's ID opens the item in the side panel and leaves the view on Activity (it used to go to Today).

Run: python3 dev/tests/test_activity_item_links.py   (needs Google Chrome; skipped otherwise)

A click on an item ID (an action, a RAID item, a decision), a milestone ID or a project name, in a real browser against the real
live server. The address names the item; Escape closes the panel and Activity is still there; Cmd-click is left to the browser and
the link's own address loads the item. The same handler is checked on another view that uses data-open (a project page).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_decisions_dashboard import load as load_decisions  # noqa: E402

META = 4


class ActivityItemLinks(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        load_decisions(v)

    def setUp(self):
        super().setUp()
        b = self.b
        # BL-327: the shared server's data is soon older than PAGE_FRESH, so each load re-reads /api/data after its first paint;
        # under load that reload redrew Activity or the project page after the set-up below, taking the probe lines (or #probe)
        # away, so the click opened nothing. Wait for it (and any pulse) first.
        b.wait("PULSE.reloads===0 && !PULSE.busy && !EVS.timer", 30)
        # one line of each kind, worded as the change log words them: "<ID> · <what changed>"
        self.ids = b.eval("""(()=>{ const a=A[0], r=R[0], d=DEC[0], m=P.flatMap(p=>p.ms).find(m=>m[3]);
          ACT=[a,r,d].map(x=>({at:"2026-10-09",what:x.id+" · changed",by:"You"})).concat([{at:"2026-10-09",what:m[3]+" · moved",by:"You"},
            {at:"2026-10-09",what:"NOSUCH-A-999 · gone",by:"You"}]); renderActivity();
          return {actions:a.id,raid:r.id,decisions:d.id,ms:m[3],proj:P[0].code}; })()""")
        b.eval("go('activity')")
        b.wait("document.querySelector('#actTbl a[data-open]')")

    def panel_open(self):
        return self.b.eval("document.getElementById('panel').classList.contains('on')")

    def view(self):
        return self.b.eval("VIEW")

    def click_id(self, selector, id_=None):
        b = self.b
        b.click(selector)
        b.wait("document.getElementById('panel').classList.contains('on')")
        if id_:                                                              # the panel is for this item, not one left open before
            b.wait(f"CUR&&CUR.id==={id_!r}", 20)

    def test_item_ids_open_the_panel_on_activity(self):
        b = self.b
        for kind in ("actions", "raid", "decisions"):
            id_ = self.ids[kind]
            self.click_id(f'#actTbl a[data-open="{kind}:{id_}"]', id_)
            self.assertEqual(self.view(), "activity", kind)
            self.assertEqual(b.eval("CUR&&CUR.id"), id_)
            self.assertIn(f"item={id_}", b.eval("location.hash"))
            self.assertTrue(b.eval("document.getElementById('v-activity').hidden===false"))
            b.key("Escape")
            b.wait("!document.getElementById('panel').classList.contains('on')")
            self.assertEqual(self.view(), "activity")
            self.assertNotIn("item=", b.eval("location.hash"))
            self.assertTrue(b.eval("!!document.querySelector('#actTbl a[data-open]')"))

    def test_milestone_and_project_stay_on_activity(self):
        b = self.b
        b.click(f'#actTbl a[data-ms="{self.ids["ms"]}"]')                   # BL-186: a milestone opens on the Milestones page, its editor open
        b.wait(f"VIEW==='milestones'&&MV.peek==='{self.ids['ms']}'")
        b.eval("history.back()")                                            # Back returns to Activity
        b.wait("VIEW==='activity'")
        # a project goes to its page, as it always did (it is a page, not a panel)
        b.eval(f"ACT=[{{at:'2026-10-09',what:'{self.ids['proj']} · health changed',by:'You'}}]; renderActivity()")
        b.click(f'#actTbl a[data-proj="{self.ids["proj"]}"]')
        b.wait("VIEW==='cockpit'")

    def test_scroll_is_kept(self):
        b = self.b
        b.eval("""(()=>{ const a=A[0]; ACT=Array.from({length:60},(_,i)=>({at:"2026-10-09",what:a.id+" · change "+i,by:"You"})); renderActivity();
          document.getElementById('v-activity').scrollTop=400; })()""")
        b.click('#actTbl tr:nth-child(12) a[data-open]')                                            # (the click scrolls its target into view)
        b.wait("document.getElementById('panel').classList.contains('on')")
        b.wait(f"CUR&&CUR.id==={self.ids['actions']!r}", 20)                                        # this item's panel, not one left open before
        before = b.eval("document.getElementById('v-activity').scrollTop")
        self.assertGreater(before, 100)
        b.key("Escape")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.assertEqual(self.view(), "activity")
        self.assertAlmostEqual(b.eval("document.getElementById('v-activity').scrollTop"), before, delta=2)

    def test_an_id_with_no_item_is_plain_text(self):
        self.assertTrue(self.b.eval("!document.querySelector('#actTbl a[data-open=\"actions:NOSUCH-A-999\"]')"))
        self.assertTrue(self.b.eval("document.getElementById('actTbl').textContent.includes('NOSUCH-A-999')"))

    def test_the_link_has_an_address_and_cmd_click_is_left_to_the_browser(self):
        b = self.b
        id_ = self.ids["actions"]
        href = b.eval(f"document.querySelector('#actTbl a[data-open=\"actions:{id_}\"]').getAttribute('href')")
        self.assertRegex(href, rf"^#work=actions(&p=[A-Z0-9]+)?&item={id_}$")
        # a Cmd-click must not be cancelled (the browser opens the address in a new tab) and must not open the panel here
        res = b.eval(f"""(()=>{{ const a=document.querySelector('#actTbl a[data-open="actions:{id_}"]'); let prevented=null;
          window.addEventListener("click",e=>{{ prevented=e.defaultPrevented; e.preventDefault(); }},{{once:true}});
          a.dispatchEvent(new MouseEvent("click",{{bubbles:true,cancelable:true,metaKey:true}})); return prevented; }})()""")
        self.assertIs(res, False)
        self.assertFalse(self.panel_open())
        # the address loads Activity's item in Work with its panel open
        b.goto(self.base + "/" + href)
        b.wait("typeof go==='function' && LIVE")
        b.wait(f"CUR&&CUR.id==={id_!r}")
        self.assertEqual(self.view(), "work")
        self.assertTrue(self.panel_open())

    def test_the_same_handler_covers_another_view(self):
        """A project page's mini list uses data-open too; an href="#" link there must not send the page to Today either."""
        b = self.b
        id_ = self.ids["actions"]
        b.eval(f"go('cockpit', REC('actions', {id_!r}).p)")
        b.eval(f"""(()=>{{ const l=document.createElement("a"); l.href="#"; l.className="hlink"; l.id="probe"; l.dataset.open="actions:{id_}"; l.textContent="probe";
          document.getElementById("v-cockpit").prepend(l); }})()""")
        self.click_id("#probe", id_)
        self.assertEqual(self.view(), "cockpit")
        self.assertNotEqual(b.eval("location.hash"), "")


if __name__ == "__main__":
    unittest.main()
