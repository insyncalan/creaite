"""BL-293 (sprint-today-days-ui): Today moves between the calendar's days, the screens.

Run: python3 dev/tests/test_today_days_ui.py   (Chrome tier; skipped without Chrome)
Over test_today_days's fixture calendar (Monday 12-10-2026 to Tuesday 20-10-2026, a Sunday meeting, a confidential board, a
private slot) with both clocks on Tuesday 13-10-2026 at 11:05: the day line (every day, the chosen one written out, "Next week",
today marked, nothing hinting a key or the swipe), moving by click, ← → Home End, [ ] and T (never while typing), a two-finger
swipe (one day a gesture, again after a pause, on a piece the redraw removed) and a touch drag, the ends, what changes with the
day (only the band), a past day's follow-up (Minutes made, Draft in Review, Transcript ready with Process, No transcript, Not
checked yet with Check), Prep and Prepare on later days, a confidential meeting, BL-287's Open icon, a reload opening on today,
and 320 px with nothing scrolling sideways (BL-217).
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_today_days as fx  # noqa: E402  (fixes CREAITE_NOW and the fixture's TODAY on import)
fx.LONG = {"2026-10-12": "Monday 12th October"}
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402

TABS = "[...document.querySelectorAll('#todayDate [role=tab]')]"
SEL = "document.querySelector('#todayDate [aria-selected=\"true\"]')"
COLS = "[...document.querySelectorAll('#dayMeets .dm')]"


class TodayFixture(LiveBrowserCase):
    """The fixture calendar, both clocks pinned, on Today."""
    shared_server = True

    @classmethod
    def load(cls, v):
        fx.world(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": fx.NOW}

    def setUp(self):
        super().setUp()
        self.b.call("Emulation.setFocusEmulationEnabled", enabled=True)
        pin_page_clock(self.b, fx.NOW)
        self.b.eval("go('today')")
        self.b.wait(f"{TABS}.length>1")

    def chosen(self):
        return self.b.eval(f"{SEL}.dataset.tab")

    def pick_past(self, iso):
        """Choose an earlier day from the history icon's menu (#147), as a pointer or the keyboard would."""
        b = self.b
        b.click("#todayDate .dypastbtn")
        b.wait("document.querySelector('#todayDate [role=menu]')")
        b.eval(f"[...document.querySelectorAll('#todayDate [role=menuitem]')].find(i=>i.dataset.id==={json.dumps(iso)} || i.textContent.includes({json.dumps(fx.LONG[iso])})).click()")


class DayLine(TodayFixture):

    def meetings(self):
        return self.b.eval(f"""{COLS}.map(d=>({{t:d.querySelector('.tt').textContent, acts:[...d.querySelectorAll('.acts .chip, .acts .lk')]
            .map(x=>x.textContent||x.getAttribute('aria-label'))}}))""")

    # ---- the day line ----
    def test_the_day_line_lists_the_calendar_s_days_with_today_written_out(self):
        b = self.b
        tabs = b.eval(f"{TABS}.map(t=>[t.dataset.tab,t.textContent,t.getAttribute('aria-selected'),t.getAttribute('aria-current'),t.tabIndex])")
        self.assertEqual([t[0] for t in tabs], ["2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-18",
                                                "2026-10-19", "2026-10-20"])      # #147: today on; Monday waits behind the icon. Saturday (all day only) out, Sunday in
        self.assertEqual(tabs[0][1:], ["Tue 13 October", "true", "date", 0])
        self.assertEqual(tabs[1][1:], ["Wed 14", "false", None, -1])
        self.assertEqual(b.eval("document.querySelector('#todayDate [role=tablist]').getAttribute('aria-label')"), "Days in the calendar")
        self.assertEqual(b.eval("[...document.querySelectorAll('#todayDate .daywk')].map(e=>e.textContent+'|'+e.nextElementSibling.dataset.tab)"),
                         ["Next week|2026-10-19"])
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#v-today .dayband')).overscrollBehaviorX"), "none")
        band = b.eval("document.querySelector('#v-today .dayband').innerText")
        for hint in ("[", "]", "swipe", "Swipe", "press", "Press"):
            self.assertNotIn(hint, band)                                    # never hinted on screen (Alan, 13-10-2026)
        self.assertEqual(b.eval("document.querySelectorAll('#v-today [aria-keyshortcuts]').length"), 0)
        self.assertIsNone(b.eval("document.querySelector('#dayMeets .dayaway')"))   # today: no "as of today" line

    def test_today_is_written_short_with_its_month_at_10px_in_the_accent_colour(self):
        b = self.b
        self.assertEqual(b.eval(f"{TABS}[0].textContent"), "Tue 13 October")
        self.assertEqual(b.eval(f"getComputedStyle({TABS}[0]).fontSize"), "10px")
        self.assertEqual(b.eval(f"getComputedStyle({TABS}[0]).fontSize"), b.eval(f"getComputedStyle({TABS}[1]).fontSize"))     # like the other dates
        b.click('#todayDate [data-tab="2026-10-16"]')
        self.assertEqual(b.eval(f"{TABS}[0].textContent"), "Tue 13 October")
        self.assertEqual(b.eval(f"getComputedStyle({TABS}[0]).fontSize"), "10px")                  # still 10px when another day is chosen
        self.assertEqual(b.eval(f"getComputedStyle({SEL}).fontSize"), "10.5px")

    def test_click_another_day_then_today_s_tab_is_short_with_its_dot_and_only_the_band_changes(self):
        b = self.b
        below = "['#attnList','#mineList','#chgList','#weekList','#pfTbl','#briefText'].map(q=>document.querySelector(q).innerHTML).join('|')"
        before, head = b.eval(below), b.eval("document.getElementById('dayHead').textContent")
        b.click('#todayDate [data-tab="2026-10-16"]')
        self.assertEqual(self.chosen(), "2026-10-16")
        self.assertEqual(b.eval(f"{TABS}.map(t=>t.textContent)")[0], "Tue 13 October")
        self.assertEqual(b.eval(f"{SEL}.textContent"), "Friday 16th October")
        self.assertNotEqual(b.eval("document.getElementById('dayHead').textContent"), head)
        self.assertEqual(b.eval("document.getElementById('dayHead').textContent"), "One meeting, Alan, with the afternoon wide open.")
        self.assertEqual(b.eval(below), before)                              # everything below stays as of today
        self.assertEqual(b.eval("document.querySelector('#dayMeets .dayaway').textContent"),
                         "Showing Friday. Everything below is as of today.")
        self.assertIsNone(b.eval("document.querySelector('#dayLine .sun')"))   # no sun or Now off today
        self.assertEqual(b.eval("document.querySelectorAll('#dayLine .dot.now, #dayLine .dot.past').length"), 0)

    # ---- moving ----
    def test_keys_step_and_t_returns_to_today_never_while_typing(self):
        b = self.b
        b.key("]")
        self.assertEqual(self.chosen(), "2026-10-14")
        b.key("]"); b.key("]")
        self.assertEqual(self.chosen(), "2026-10-16")
        b.key("t")
        self.assertEqual(self.chosen(), "2026-10-13")
        for _ in range(4):
            b.key("[")
        self.assertEqual(self.chosen(), "2026-10-12")                       # the first day: it stays
        b.key("T")
        self.assertEqual(self.chosen(), "2026-10-13")
        b.eval("(()=>{ const i=document.createElement('input'); i.id='tdTyping'; document.getElementById('v-today').appendChild(i); i.focus(); })()")
        b.key("]")
        self.assertEqual(self.chosen(), "2026-10-13")                       # typing: the keys are text
        b.eval("document.getElementById('tdTyping').remove()")
        b.eval("go('work')")
        b.key("]")
        b.eval("go('today')")
        self.assertEqual(self.chosen(), "2026-10-13")                       # on Today only

    def test_arrows_home_and_end_in_the_line_move_the_focus_with_the_day(self):
        b = self.b
        b.eval(f"{SEL}.focus()")
        b.key("ArrowRight")
        self.assertEqual((self.chosen(), b.eval("document.activeElement.dataset.tab")), ("2026-10-14", "2026-10-14"))
        b.key("End")
        self.assertEqual((self.chosen(), b.eval("document.activeElement.dataset.tab")), ("2026-10-20", "2026-10-20"))
        b.key("Home")
        self.assertEqual((self.chosen(), b.eval("document.activeElement.dataset.tab")), ("2026-10-13", "2026-10-13"))   # the line starts at today (#147)
        b.key("ArrowLeft")
        self.assertEqual(self.chosen(), "2026-10-13")

    def test_two_swipes_in_a_row_without_a_click_and_the_momentum_is_ignored(self):
        b = self.b
        x, y = b.eval("(()=>{ const r=document.getElementById('dayHead').getBoundingClientRect(); return [r.x+20,r.y+10]; })()")

        def swipe(dx):
            for d in (dx * 0.6, dx, dx, dx * 0.5, dx * 0.2, dx * 0.1, dx * 0.05):     # a gesture and its momentum tail
                b.call("Input.dispatchMouseEvent", type="mouseWheel", x=x, y=y, deltaX=d, deltaY=0)
            b.pump(0.3)                                                               # a pause ends the gesture
        swipe(30)
        self.assertEqual(self.chosen(), "2026-10-14")                       # one day for one gesture, tail and all
        swipe(30)
        self.assertEqual(self.chosen(), "2026-10-15")                       # again, the pointer resting where it was
        swipe(-30)
        self.assertEqual(self.chosen(), "2026-10-14")
        prevented = b.eval("""(()=>{ const e=new WheelEvent('wheel',{deltaX:5,deltaY:0,bubbles:true,cancelable:true});
            document.getElementById('dayHead').dispatchEvent(e); return e.defaultPrevented; })()""")
        self.assertTrue(prevented)                                          # Chrome's back gesture never fires over the band

    def test_a_swipe_still_reaching_a_piece_the_redraw_removed_moves_on(self):
        b = self.b
        out = b.eval("""(async()=>{ const wait=ms=>new Promise(r=>setTimeout(r,ms)), seen=[];
            const fire=el=>{ for(const d of [30,30,30]) el.dispatchEvent(new WheelEvent('wheel',{deltaX:d,deltaY:0,bubbles:true,cancelable:true})); };
            let el=document.querySelector('#dayMeets .dm .tt'); fire(el); await wait(200); seen.push([document.querySelector('#todayDate [aria-selected="true"]').dataset.tab, el.isConnected]);
            fire(el); await wait(200); seen.push([document.querySelector('#todayDate [aria-selected="true"]').dataset.tab, el.isConnected]);
            el=document.querySelector('#dayLine svg'); fire(el); await wait(200); seen.push([document.querySelector('#todayDate [aria-selected="true"]').dataset.tab, el.isConnected]);
            fire(el); await wait(200); seen.push([document.querySelector('#todayDate [aria-selected="true"]').dataset.tab, el.isConnected]);
            return seen; })()""")
        self.assertEqual(out, [["2026-10-14", False], ["2026-10-15", False], ["2026-10-16", False], ["2026-10-18", False]])

    def test_a_touch_drag_steps_and_the_ends_hold(self):
        b = self.b
        drag = """(dx=>{ const el=document.getElementById('dayHead'), r=el.getBoundingClientRect(), o={pointerType:'touch',bubbles:true,clientY:r.y+5};
            el.dispatchEvent(new PointerEvent('pointerdown',{...o,clientX:200})); el.dispatchEvent(new PointerEvent('pointerup',{...o,clientX:200+dx})); })"""
        b.eval(f"{drag}(-120)")
        self.assertEqual(self.chosen(), "2026-10-14")
        b.eval(f"{drag}(120)"); b.eval(f"{drag}(120)"); b.eval(f"{drag}(120)")
        self.assertEqual(self.chosen(), "2026-10-12")
        b.eval(f"{drag}(-20)")
        self.assertEqual(self.chosen(), "2026-10-12")                       # a short drag is not a step
        self.assertTrue(b.eval("document.querySelector('.dayedge.l').disabled"))       # hover edges hidden at the ends
        b.click('#todayDate [data-tab="2026-10-20"]')
        self.assertTrue(b.eval("document.querySelector('.dayedge.r').disabled"))
        b.eval("document.querySelector('.dayedge.l').click()")
        self.assertEqual(self.chosen(), "2026-10-19")

    def test_a_reload_opens_on_today(self):
        b = self.b
        b.click('#todayDate [data-tab="2026-10-16"]')
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('today')")
        b.wait(f"{TABS}.length>1")
        self.assertEqual(self.chosen(), "2026-10-13")

    # ---- past days: follow-up ----
    def test_a_past_day_shows_each_meeting_s_follow_up(self):
        b = self.b
        self.pick_past("2026-10-12")
        got = {m["t"]: m["acts"] for m in self.meetings()}
        self.assertEqual(got["ABC weekly Example Programme"], ["Minutes made"])                     # processed.txt
        self.assertEqual(got["ABC steering committee Example Programme"], ["Transcript ready", "Process"])
        self.assertEqual(got["ABC design chat Example Programme"], ["No transcript"])
        self.assertEqual(got["DEF sync Digital Enablement"], ["Not checked yet", "Check"])           # Alan: offers Check
        self.assertEqual(got["Busy"], [])                                                             # private: times only
        self.assertEqual(b.eval("document.querySelectorAll('#dayMeets .preplink').length"), 0)       # no Prep on a past day
        self.assertEqual(b.eval("document.querySelectorAll('#dayLine .dot.past').length"), 5)
        b.eval("D.days.days[0].meetings[0].follow={state:'minutes',draft:true,cleared:false}; renderDay()")
        self.assertEqual({m["t"]: m["acts"] for m in self.meetings()}["ABC weekly Example Programme"][:1], ["Draft in Review"])

    # ---- today and later: Prep, in a popup on the title (#140) ----
    def popup(self, ix=0):
        """Tab-focus the title of meeting `ix` and read its popup."""
        b = self.b
        b.eval("document.activeElement && document.activeElement.blur()")
        b.eval(f"document.querySelectorAll('#dayMeets .dmti')[{ix}].focus()")
        b.wait("document.querySelector('#dayMeets .dmpop')")
        return b.eval("""(()=>{ const p=document.querySelector('#dayMeets .dmpop'); return {head:p.querySelector('h4').textContent, meta:p.querySelector('.pm').textContent,
            btns:[...p.querySelectorAll('button')].map(x=>x.textContent), text:p.textContent}; })()""")

    def test_later_days_have_no_pill_the_title_opens_a_popup_and_a_confidential_one_shows_no_project(self):
        b = self.b
        today = {m["t"]: m["acts"] for m in self.meetings()}
        self.assertEqual(today["DEF stand-up Digital Enablement"], [])                           # #140: the Prep and Prepare pills are gone
        self.assertEqual(today["ABC risk review Example Programme"], [])
        self.assertEqual(b.eval("document.querySelectorAll('#dayMeets .preplink, #dayMeets .mnote').length"), 0)
        got = self.popup(1)
        self.assertEqual((got["head"], got["btns"]), ("ABC risk review", ["Prepare"]))
        self.assertIn("Worth preparing", got["text"])                                             # a review meeting says why
        self.assertEqual(self.popup(0)["btns"], ["Prepare"])
        b.click('#todayDate [data-tab="2026-10-14"]')
        board = b.eval("""(()=>{ const d=document.querySelector('#dayMeets .dm'); return {text:d.innerText, proj:!!d.querySelector('[data-proj]'),
            wh:!!d.querySelector('.wh'), pill:!!d.querySelector('.preplink')}; })()""")
        self.assertEqual(board, {"text": board["text"], "proj": False, "wh": False, "pill": False})
        self.assertNotIn("Room 7", board["text"])                                                   # only its title and times
        conf = self.popup(0)
        self.assertEqual((conf["btns"], "Room 7" in conf["text"], "Example Programme" in conf["text"]), (["Prepare"], False, False))
        b.click('#todayDate [data-tab="2026-10-16"]')
        got = self.popup(0)
        self.assertEqual((got["head"], got["meta"].startswith("Friday 10:00"), got["btns"]), ("ABC steering", True, ["Prepare"]))
        b.click("#dayMeets .dmpop .btn.primary")
        b.wait("document.getElementById('prepDlg')&&document.getElementById('prepDlg').open")
        # the Prep popup's header (BL-286 A, joined on release-190): the day written out, the project as a chip
        self.assertEqual(b.eval("document.getElementById('prepWhen').textContent"), "Friday 16th October · 10:00 – 11:00 · Teams")
        self.assertEqual(b.eval("document.getElementById('prepTitle').textContent"), "ABC steering")
        self.assertEqual(b.eval("document.getElementById('prepProjBtn').dataset.code"), "ABC")   # three days out, its project known
        self.assertIsNone(b.eval("document.querySelector('#prepDlg [data-prepview]').getAttribute('aria-disabled')"))

    def test_a_past_day_has_no_popup_and_a_private_meeting_none(self):
        b = self.b
        self.pick_past("2026-10-12")
        self.assertEqual(b.eval("document.querySelectorAll('#dayMeets .dmti').length"), 0)
        b.click('#todayDate [data-tab="2026-10-13"]')
        b.eval("document.querySelectorAll('#dayMeets .dmti')[0].focus()")

    def test_a_saved_agenda_shows_open_agenda_prepare_again_and_open_the_file(self):
        b = self.b
        b.click('#todayDate [data-tab="2026-10-16"]')
        self.assertEqual(self.popup(0)["btns"], ["Prepare"])
        b.eval(f"SA().prep_pages={{...(SA().prep_pages||{{}}),{json.dumps(fx.FRIDAY)}:'projects/ABC Example Programme/agendas/x.html'}}; renderDay(); document.activeElement.blur()")
        got = self.popup(0)
        self.assertEqual(got["btns"], ["Open agenda", "Prepare again", "Open the file"])
        self.assertIn("Agenda saved", got["text"])
        self.assertEqual(b.eval("document.querySelector('#dayMeets .dmpop [data-prepgo]').getAttribute('aria-disabled')"), None)   # enabled with the live server
        self.assertEqual(b.eval("document.querySelector('#dayMeets .dmpop .btn.primary').textContent"), "Open agenda")
        b.key("Escape")
        b.wait("!document.querySelector('#dayMeets .dmpop')")
        self.assertTrue(b.eval("document.activeElement.classList.contains('dmti')"))

    # ---- the day line's earlier days (#147) ----
    def test_147_past_days_are_behind_one_icon_newest_first_and_the_chosen_one_shows(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelectorAll('#todayDate .dypast').length"), 1)
        self.assertEqual(b.eval("document.querySelector('#todayDate .dypastbtn').getAttribute('aria-haspopup')"), "menu")
        b.click("#todayDate .dypastbtn")
        b.wait("document.querySelector('#todayDate [role=menu]')")
        self.assertEqual(b.eval("[...document.querySelectorAll('#todayDate [role=menuitem]')].map(i=>i.textContent.replace(/ · .*/,''))"), ["Monday 12th October"])
        b.key("Escape")
        b.wait("!document.querySelector('#todayDate [role=menu]')")
        self.pick_past("2026-10-12")
        self.assertEqual(self.chosen(), "2026-10-12")
        self.assertEqual(b.eval(f"{TABS}.map(t=>t.dataset.tab)")[:2], ["2026-10-12", "2026-10-13"])      # shown in the line, today still reachable
        self.assertEqual(b.eval(f"{TABS}.map(t=>t.textContent)")[1], "Tue 13 October")
        b.click('#todayDate [data-tab="2026-10-13"]')
        self.assertEqual(b.eval(f"{TABS}.map(t=>t.dataset.tab)")[0], "2026-10-13")                     # a day not chosen leaves the line again

    def test_147_the_arrows_still_step_through_every_day(self):
        b = self.b
        b.eval("document.querySelector('.dayedge.l').click()")
        self.assertEqual(self.chosen(), "2026-10-12")
        self.assertEqual(b.eval(f"{TABS}.map(t=>t.dataset.tab)")[0], "2026-10-12")
        self.assertTrue(b.eval("document.querySelector('.dayedge.l').disabled"))

    def test_147_the_icon_works_from_the_keyboard_enter_opens_arrows_move_escape_closes_and_returns_focus(self):
        b = self.b
        b.eval("D.days.days.unshift({...D.days.days[0], date:'2026-10-11', dow:'Sunday', short:'Sun 11', long:'Sunday 11th October', meetings:[], all_day:[]}); renderDay()")
        b.wait("document.querySelector('#todayDate .dypastbtn')")
        b.eval("document.querySelector('#todayDate .dypastbtn').focus()")
        b.key("Enter")
        b.wait("document.querySelector('#todayDate [role=menu]')")
        items = "[...document.querySelectorAll('#todayDate [role=menuitem]')]"
        self.assertGreaterEqual(b.eval(f"{items}.length"), 2)
        first = b.eval(f"{items}.indexOf(document.activeElement)")
        self.assertEqual(first, 0)                                                                       # focus lands on the first item
        b.key("ArrowDown")
        self.assertEqual(b.eval(f"{items}.indexOf(document.activeElement)"), 1)
        b.key("ArrowUp")
        self.assertEqual(b.eval(f"{items}.indexOf(document.activeElement)"), 0)
        b.key("Escape")
        b.wait("!document.querySelector('#todayDate [role=menu]')")
        self.assertTrue(b.eval("document.activeElement.classList.contains('dypastbtn')"))                # focus back on the history icon

    def test_a_synthesised_day_follows_the_weekend_setting(self):
        b = self.b
        self.assertEqual(b.eval("[S.weekendDays, synthDay('2026-10-16').weekend, synthDay('2026-10-17').weekend, synthDay('2026-10-18').weekend]"),
                         [[5, 6], False, True, True])
        b.eval("S.weekendDays=[4,5]")                                                                      # Friday and Saturday
        self.assertEqual(b.eval("[synthDay('2026-10-16').weekend, synthDay('2026-10-17').weekend, synthDay('2026-10-18').weekend]"), [True, True, False])

    def test_147_the_icon_opens_on_hover_and_there_is_none_without_past_days(self):
        b = self.b
        r = b.eval("(()=>{ const e=document.querySelector('#todayDate .dypastbtn').getBoundingClientRect(); return [e.left+e.width/2, e.top+e.height/2]; })()")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=r[0], y=r[1])
        b.wait("document.querySelector('#todayDate [role=menu]')")
        b.eval("goDay('2026-10-12')")
        self.assertEqual(b.eval("document.querySelectorAll('#todayDate .dypast').length"), 1)
        # a calendar that starts today has nothing to drop down
        b.eval("D.days.days=D.days.days.filter(d=>d.date>=TODAY); renderDay()")
        self.assertEqual(b.eval("document.querySelectorAll('#todayDate .dypast').length"), 0)

    # ---- small screens ----
    def test_at_320_px_nothing_scrolls_sideways(self):
        b = self.b
        b.resize(320, 800)
        b.pump(0.3)
        for day in ("2026-10-13", "2026-10-12", "2026-10-16"):
            b.eval(f"goDay('{day}')")
            sizes = b.eval("""(()=>{ const v=document.getElementById('v-today'), d=document.scrollingElement;
                return [d.scrollWidth-d.clientWidth, v.scrollWidth-v.clientWidth]; })()""")
            self.assertEqual(sizes, [0, 0], day)


def arrows_hold_still(case, width=None):
    """Click › through every day without moving the mouse, then ‹ back: both arrows keep the same box on every day (Alan,
    13-10-2026), and at an end the arrow is there, disabled and dimmed, never removed."""
    b = case.b
    if width:
        b.resize(width, 900)
        b.pump(0.3)
    box = "(s=>{ const r=document.querySelector(s).getBoundingClientRect(); return [r.x,r.y,r.width,r.height]; })"
    first = [b.eval(f"{box}('.dayedge.l')"), b.eval(f"{box}('.dayedge.r')")]
    case.assertGreater(first[1][2], 0)
    days = b.eval(f"{TABS}.length")
    b.eval("goDay(dayList()[0].date)")
    x, y = first[1][0] + first[1][2] / 2, first[1][1] + first[1][3] / 2
    seen, heights = [], set()
    for _ in range(days + 1):                                  # one more than needed: the last click is at the end
        seen.append([b.eval(f"{box}('.dayedge.l')"), b.eval(f"{box}('.dayedge.r')")])
        heights.add(b.eval("Math.round(document.querySelector('#v-today .dayband').getBoundingClientRect().height)"))
        for t in ("mousePressed", "mouseReleased"):
            b.call("Input.dispatchMouseEvent", type=t, x=x, y=y, button="left", clickCount=1)
        b.pump(0.35)
    case.assertEqual(case.chosen(), "2026-10-20")                    # the clicks reached the last day
    case.assertGreater(len(heights), 1, "the fixture's days change the band's height")
    case.assertEqual(seen, [first] * len(seen))
    end = b.eval("(()=>{ const r=document.querySelector('.dayedge.r'); return [r.disabled, getComputedStyle(r).display, +getComputedStyle(r).opacity<0.3]; })()")
    case.assertEqual(end, [True, "grid", True])
    b.eval("goDay(dayList()[0].date)")
    case.assertEqual(b.eval("document.querySelector('.dayedge.l').disabled"), True)
    case.assertEqual(b.eval(f"{box}('.dayedge.l')"), first[0])


class ArrowsStayPut(TodayFixture):
    """The arrows' boxes, with reduced motion (the class default) and at a narrow width."""

    def test_the_arrows_never_move(self):
        arrows_hold_still(self)

    def test_the_arrows_never_move_at_320_px(self):
        arrows_hold_still(self, 320)


class ArrowsStayPutWithMotion(TodayFixture):
    reduced_motion = False

    def test_the_arrows_never_move_with_motion_on(self):
        arrows_hold_still(self)


if __name__ == "__main__":
    unittest.main()
