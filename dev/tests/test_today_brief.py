"""Tests for the Today-as-a-brief sprint: Intake (BL-70, BL-73, BL-74), the Live indicator (BL-71), Today (BL-72).

Run: python3 dev/tests/test_today_brief.py   (the page tests need Google Chrome; skipped otherwise)
A throwaway vault with the demo data from test_dashboard.populate; the page is loaded headless and probed with
test_insight.chrome (the probe sets window.OUT).
"""
import sys
import unittest
from datetime import date, datetime
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import CHROME, populate  # noqa: E402
from test_tracker import Vault  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import build_dashboard as bd  # noqa: E402


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")

def theme_count():
    """How many named themes the dashboard has (its THEMES list), so theme checks follow new themes by themselves."""
    page = readable_page()     # BL-231: the source; the bundle reprints the code
    return len(re.findall(r'\{id:"', re.search(r"const THEMES=\[(.*?)\];", page, re.S).group(1)))

class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_insight import chrome
        cls.chrome = staticmethod(chrome)
        cls.v = Vault()
        populate(cls.v)
        cls.v.run(script="build_dashboard.py")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def probe(self, script):
        out, errors = self.chrome(self.v, script)
        self.assertEqual(errors, [])
        self.assertIsNotNone(out, "the page didn't finish")
        self.assertNotIn("error", out, out.get("error"))
        return out


class IntakeNameTests(PageTests):
    """BL-70: the screen is called Intake; the folder, ids and keys keep their names; #inbox still opens it."""

    def test_the_words_alan_reads(self):
        o = self.probe("""
          const rail=document.querySelector('.rail button[data-v=inbox]');
          go("inbox"); const h1=document.querySelector("#v-inbox h1").textContent, hint=document.querySelector("#v-inbox > .wrapmax > .sub").textContent;
          const names=ckItems("").map(i=>`${i.g}|${i.l}`), files=ckItems("recording").map(i=>`${i.g}|${i.l}`);
          go("files"); const tree=[...document.querySelectorAll("#tree button")].map(b=>b.textContent), chips=[...document.querySelectorAll("#fquick button")].map(b=>b.textContent);
          window.OUT={rail:rail.querySelector(".rl").textContent, title:rail.getAttribute("aria-label").split(",")[0], h1, hint, names, files, tree, chips, badge:document.getElementById("inboxBadge").getAttribute("aria-label"),
            drop:document.getElementById("inboxDrop").getAttribute("aria-label")};""")
        self.assertEqual((o["rail"], o["title"], o["h1"]), ("Intake", "Intake", "Intake"))
        self.assertIn("saved to the inbox folder", o["hint"])
        self.assertIn("Go to|Intake", o["names"])
        self.assertIn("Actions|Add files to Intake", o["names"])
        self.assertTrue(any(f.startswith("Intake|") for f in o["files"]))
        self.assertFalse(any("Inbox" in n.split("|")[1] for n in o["names"] if not n.startswith(("Files|", "Items|"))))
        self.assertTrue(any(t.startswith("Intake") for t in o["tree"]) and "Intake" in o["chips"])
        self.assertRegex(o["badge"], r"^\d+ new files? in Intake$")
        self.assertEqual(o["drop"], "Add files to Intake")

    def test_the_address(self):
        o = self.probe("""
          go("inbox"); const written=location.hash, parsed=[parseHash("#inbox").v, parseHash("#intake").v, parseHash("#intake").arg];
          go("today"); window.location.hash="#inbox"; await new Promise(r=>setTimeout(r,200));
          window.OUT={written, parsed, hashOfInbox:hashOf({v:"inbox"}), view:VIEW};""")
        self.assertEqual(o["written"], "#intake")                                 # the new address
        self.assertEqual(o["parsed"], ["inbox", "inbox", None])                   # both open the same view
        self.assertEqual(o["hashOfInbox"], "#intake")


class IntakeSectionsTests(PageTests):
    """BL-73: Calendar import, Upload files and Quick capture are three separate framed sections, in that order."""

    def test_three_sections_in_order_each_with_its_own_heading_purpose_and_buttons(self):
        o = self.probe("""
          go("inbox"); const secs=[...document.querySelectorAll("#v-inbox .isec")];
          const info=secs.map(s=>({id:s.id,h:s.querySelector("h2").textContent,icon:!!s.querySelector(".ish svg"),purpose:s.querySelector(".ipurpose").textContent,
            buttons:[...s.querySelectorAll("button[id]")].map(b=>b.id),labelled:s.getAttribute("aria-labelledby")===s.querySelector("h2").id}));
          const rects=secs.map(s=>s.getBoundingClientRect()), within=(s,sel)=>!!s.querySelector(sel);
          window.OUT={info,gaps:rects.slice(1).map((r,i)=>Math.round(r.top-rects[i].bottom)),stacked:rects.slice(1).every((r,i)=>r.top>=rects[i].bottom),
            widths:rects.map(r=>Math.round(r.width)),
            where:{drop:within(secs[1],"#inboxDrop"),table:within(secs[1],"#inboxTbl"),mtg:within(secs[0],"#mtgSec"),qc:within(secs[2],"#qcNotes")},
            h1s:[...document.querySelectorAll("#v-inbox h1, #v-inbox h2")].map(h=>h.textContent)};""")
        self.assertEqual([i["h"] for i in o["info"]], ["Calendar import", "Upload files", "Quick capture"])
        self.assertEqual([i["id"] for i in o["info"]], ["isecCal", "isecUp", "isecQuick"])
        self.assertTrue(all(i["labelled"] and not i["icon"] for i in o["info"]))   # BL-325: a plain sentence-case h2, as Settings, no icon
        self.assertEqual([i["purpose"] for i in o["info"]], [
            "Pick meetings from your calendar and load their transcripts.", "Drop transcripts or minutes you already have.",
            "Type rough notes from a call or conversation that has no transcript."])
        cal, up, quick = (i["buttons"] for i in o["info"])
        self.assertEqual(cal, ["mtgRefresh", "mtgNew", "mtgTx", "mtgLoad", "mtgGo"])   # Refresh, Select new, Select with transcripts, Load into inbox, Process selected (BL-119: one process button)
        self.assertIn("inboxNew", up)
        self.assertIn("inboxGo", up)
        self.assertEqual({"qcGo", "qcCancel"} <= set(quick), True)                       # Quick capture's Process and Clear
        self.assertEqual(o["where"], {"drop": True, "table": True, "mtg": True, "qc": True})
        self.assertTrue(o["stacked"])                                                    # nothing side by side
        self.assertTrue(all(g >= 24 for g in o["gaps"]), o["gaps"])                      # a visible gap between panels
        self.assertEqual(len(set(o["widths"])), 1)                                       # the same frame, the same width
        self.assertEqual(o["h1s"][:1], ["Intake"])

    def test_the_sections_use_the_themes_own_card_frame(self):
        o = self.probe("""
          go("inbox"); const out={};
          for(const pal of THEMES.map(t=>t.id)) for(const mode of ["light","dark"]){ S.palette=pal; S.theme=mode==="dark"?"Dark":"Light"; applyTheme();
            const cs=getComputedStyle(document.getElementById("isecUp")), card=getComputedStyle(document.querySelector("#v-inbox .tbl")); 
            out[pal+"|"+mode]=[cs.borderTopWidth!=="0px", cs.backgroundColor!=="rgba(0, 0, 0, 0)", cs.borderTopLeftRadius===card.borderTopLeftRadius]; }
          window.OUT={out};""")
        for key, (bordered, filled, same_radius) in o["out"].items():
            self.assertTrue(bordered and filled, key)


class QuickCaptureDateTests(PageTests):
    """BL-74: the date is today whenever the form opens, can't be a future day, its calendar popup is reachable by
    keyboard; the Title box is wider. Since BL-147 the date can also be typed (in plain words), and the calendar button opens the popup."""

    def test_a_read_only_field_that_is_today_and_resets(self):
        o = self.probe("""
          const q=id=>document.getElementById(id), pad=n=>String(n).padStart(2,"0"), today=fd(TODAY);
          go("inbox"); q("qcNotes").focus(); const field=q("qcDate");
          const first=[field.readOnly, field.value, field.dataset.max, field.hasAttribute("data-noclear"), q("qcDate").closest(".dwrap").querySelector("button").getAttribute("aria-label")];
          field.closest(".dwrap").querySelector("button").click(); const pop1=!!document.querySelector(".cal");
          const days=[...document.querySelectorAll(".cal .cg button")], todayBtn=days.find(b=>b.classList.contains("today")),
            after=days.filter(b=>b.getAttribute("aria-label")>"" && toIso(b.getAttribute("aria-label"))>TODAY), before=days.filter(b=>toIso(b.getAttribute("aria-label"))<=TODAY);
          const foot=[...document.querySelectorAll(".cal .cf button")].map(b=>b.textContent);
          // a past day is chosen by clicking it
          const past=days.find(b=>toIso(b.getAttribute("aria-label"))<TODAY); let chosen=null;
          if(past){ past.click(); chosen=[field.value, !document.querySelector(".cal")]; }
          // BL-147: typing is possible; a future day is refused by Process (test_plain_dates)
          const typed=!field.readOnly;
          // Clear (the form's) and Process put it back to today; reopening does too
          q("qcCancel").click(); const afterClear=field.value; q("qcNotes").focus(); const reopened=field.value;
          if(past){ openCal(field,field.closest(".dwrap").querySelector("button")); document.querySelector(".cal .cg button:not(:disabled)").click(); }
          openCapture("note: something"); const viaCapture=field.value;
          window.OUT={today, first, pop1, offCount:after.length, offAllDisabled:after.every(b=>b.disabled&&b.classList.contains("off")), beforeEnabled:before.every(b=>!b.disabled),
            todayEnabled:todayBtn&&!todayBtn.disabled, foot, chosen, typed, afterClear, reopened, viaCapture};""")
        self.assertEqual(o["first"], [False, o["today"], "today", True, "Choose date"])   # BL-147: typed too
        self.assertTrue(o["pop1"])                                                    # the calendar button opens the popup
        self.assertEqual(o["foot"], ["Today"])                                        # no Clear for this field
        self.assertTrue(o["beforeEnabled"] and o["todayEnabled"])
        self.assertTrue(o["offAllDisabled"])                                          # later days are greyed out and disabled
        self.assertEqual((o["afterClear"], o["reopened"], o["viaCapture"]), (o["today"],) * 3)
        if o["chosen"]:
            self.assertEqual(o["chosen"][1], True)                                    # choosing a day closes the popup

    def test_future_days_cannot_be_chosen_in_any_month(self):
        o = self.probe("""
          go("inbox"); document.getElementById("qcNotes").focus(); document.querySelector('#qcap [data-cal="qcDate"]').click();
          document.querySelector('.cal [data-n="1"]').click(); const next=[...document.querySelectorAll(".cal .cg button")];
          document.querySelector('.cal [data-n="-1"]').click(); document.querySelector('.cal [data-n="-1"]').click(); const older=[...document.querySelectorAll(".cal .cg button")];
          window.OUT={nextAllOff:next.every(b=>b.disabled), nextCount:next.length, olderOn:older.every(b=>!b.disabled)};""")
        self.assertTrue(o["nextAllOff"] and o["nextCount"] >= 28)
        self.assertTrue(o["olderOn"])

    def test_keyboard_control(self):
        o = self.probe("""
          const key=(k)=>document.activeElement.dispatchEvent(new KeyboardEvent("keydown",{key:k,bubbles:true,cancelable:true})), lab=()=>document.activeElement.getAttribute("aria-label");
          go("inbox"); document.getElementById("qcNotes").focus(); const btn=document.querySelector('#qcap [data-cal="qcDate"]'); btn.focus(); btn.click();
          const start=lab(); key("ArrowRight"); const clamped=lab();             // today is the latest day: it stays
          key("ArrowLeft"); const left=lab(); key("ArrowUp"); const up=lab(); key("ArrowDown"); const down=lab(); key("ArrowDown"); const clampedDown=lab();
          key("PageUp"); const pageUp=lab(); key("Home"); const home=lab(); key("End"); const end=lab();
          const focusedIsDay=document.activeElement.closest(".cg")!==null;
          key("Escape"); const closed=!document.querySelector(".cal"), back=document.activeElement===btn;
          // opened again from the field with the keyboard
          const f=document.getElementById("qcDate"); f.focus(); f.dispatchEvent(new KeyboardEvent("keydown",{key:"ArrowDown",bubbles:true,cancelable:true})); const reopened=!!document.querySelector(".cal"); document.activeElement.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true}));
          // the same keys work in the other date fields (no latest day there)
          go("files"); const fb=document.querySelector('[data-cal="fsFrom"]'); fb.click(); const o0=lab(); key("ArrowRight"); const fwd=lab(); key("ArrowDown"); const fwd7=lab(); const hasClear=[...document.querySelectorAll(".cal .cf button")].map(b=>b.textContent);
          window.OUT={start,clamped,left,up,down,clampedDown,pageUp,home,end,focusedIsDay,closed,back,reopened,o0,fwd,fwd7,hasClear,today:fd(TODAY)};""")
        t = o["today"]
        self.assertEqual((o["start"], o["clamped"]), (t, t))
        self.assertNotEqual(o["left"], t)
        self.assertNotEqual(o["up"], o["left"])
        self.assertEqual(o["clampedDown"], t)                                        # down from yesterday is today; again stays
        self.assertTrue(o["focusedIsDay"])
        self.assertTrue(o["closed"] and o["back"])
        self.assertTrue(o["reopened"])
        self.assertNotEqual(o["fwd"], o["o0"])                                       # other date fields move forward freely
        self.assertEqual(o["hasClear"], ["Today", "Clear"])                          # and keep their Clear

    def test_the_project_list_is_filled_without_waiting_for_focus(self):
        o = self.probe("""
          go("inbox"); const q=document.getElementById("qcProj"), n=()=>[...q.options].map(o=>o.value);
          const atLoad=n(); document.getElementById("qcNotes").focus(); document.getElementById("qcCancel").click();
          const hiddenAfterClear=document.getElementById("qcMore").hidden; document.getElementById("qcNotes").click();
          const reopened=!document.getElementById("qcMore").hidden;
          P.push({code:"NEW",name:"New Project"}); refreshAll(); const afterReload=n(); P.pop();
          window.OUT={atLoad,hiddenAfterClear,reopened,afterReload};""")
        self.assertEqual(len(o["atLoad"]), 3, o)                                     # "Match from the note" and both projects, before any focus
        self.assertTrue(o["hiddenAfterClear"] and o["reopened"], o)                  # a click reopens the form while the box keeps focus
        self.assertIn("NEW", o["afterReload"], o)                                    # a data reload refreshes the list

    def test_the_title_box_is_wider(self):
        o = self.probe("""
          go("inbox"); document.getElementById("qcNotes").focus(); const t=document.getElementById("qcTitle"), w=document.getElementById("qcWho"), p=document.getElementById("qcProj");
          window.OUT={title:Math.round(t.getBoundingClientRect().width),who:Math.round(w.getBoundingClientRect().width),proj:Math.round(p.getBoundingClientRect().width),
            max:getComputedStyle(t).maxWidth};""")
        self.assertTrue(380 <= o["title"] <= 420, o)                                # about 400px, from about 160px
        self.assertEqual(o["max"], "100%")                                           # and never wider than its row
        self.assertLess(o["who"], 250)


class LiveIndicatorTests(PageTests):
    """BL-143: the dot under Settings in the rail is gone; the red alert, the quiet top strip and Settings › System say it all."""

    def test_there_is_no_dot_in_the_rail(self):
        o = self.probe("""
          const rail=document.querySelector(".rail"), css=[...document.styleSheets].flatMap(s=>[...s.cssRules]).some(r=>r.selectorText&&r.selectorText.includes("raillive"));
          const rest=[...rail.querySelectorAll("#railFoot button:not([data-v])")];   /* BL-319: the foot holds More and its Customise sidebar… only */
          window.OUT={el:!!document.getElementById("railLive"), css, fn:[typeof railLive, typeof railLiveGo], last:[...rail.querySelectorAll("[data-v]")].pop().dataset.v, rest:rest.map(x=>x.id)};""")
        self.assertFalse(o["el"])
        self.assertFalse(o["css"])                                                                # and no style for it
        self.assertEqual(o["fn"], ["undefined", "undefined"])                                     # nor its functions
        self.assertEqual(o["last"], "settings")                                                   # Settings is the last page (in More, BL-319)
        self.assertEqual(o["rest"], ["railMore", "railCustBtn"])                                  # then only More and its Customise sidebar… (BL-319)

    def test_every_state_the_dot_showed_is_covered_by_the_alert(self):
        o = self.probe("""
          const a=document.getElementById("liveAlert"), q=()=>({on:a.classList.contains("on"), found:a.classList.contains("found"), text:a.textContent, copy:!!a.querySelector("[data-copycmd]"), check:!!a.querySelector("#checkLive")});
          LIVELINK=false; setLive(true); const running=q();                                       // server running: nothing to show
          setLive(false); const stopped=q();                                                      // stopped: the alert, with the command and Check again
          LIVELINK=true; setLive(false); const fileCopy=q();                                      // the file version of the dashboard while the server runs
          LIVELINK=false; setLive(true);
          window.OUT={running,stopped,fileCopy};""")
        self.assertFalse(o["running"]["on"])
        self.assertTrue(o["stopped"]["on"] and o["stopped"]["copy"] and o["stopped"]["check"])
        self.assertIn("Live server isn't running", o["stopped"]["text"])
        self.assertTrue(o["fileCopy"]["on"] and o["fileCopy"]["found"])
        self.assertIn("The live server is running. This copy of the dashboard is the file version", o["fileCopy"]["text"])

    def test_the_top_strip_stays_quiet_and_shows_only_what_needs_an_action(self):
        o = self.probe("""
          VSTATE="ok"; HELD=[()=>{},()=>{}]; status(); const held=document.getElementById("status").textContent.trim(); HELD=[]; VSTATE="prompt"; status(); const vault=document.getElementById("status").textContent.trim();
          VSTATE="ok"; status(); const quiet=document.getElementById("status");
          window.OUT={held,vault,quiet:[quiet.textContent.trim(),getComputedStyle(quiet).display]};""")
        self.assertEqual(o["held"], "2 held")
        self.assertEqual(o["vault"], "Reconnect vault")
        self.assertEqual(o["quiet"], ["", "none"])

    def test_the_live_server_card_says_when_mail_and_teams_were_swept(self):
        o = self.probe("""
          go("settings","live"); const card=document.getElementById("liveCard");
          window.OUT={text:card.textContent.replace(/\\s+/g," "), swept:SWEPT, data:DATA_AT, fdSwept:fd(SWEPT), fdData:fd(DATA_AT).slice(0,16)};""")
        self.assertIn("Mail, Teams and data", o["text"])
        self.assertRegex(o["text"], r"Mail and Teams (last swept \d\d-\d\d-\d{4}|never swept) · data as of ")
        self.assertIn(f"data as of {o['fdData']}", o["text"])


# ===== Today as a brief (BL-72) =====

def ev(day, start, end, title, **kw):
    return {"start": start, "end": end, "title": title, **kw}


class WeekAheadDataTests(unittest.TestCase):
    """build_dashboard.week_ahead: the window, the weekend rule and what lands on each day (fixed dates)."""

    SETTINGS = {"reminders": {"enabled": True, "weekly_report_day": "Friday"}}

    def week(self, today, actions=(), raid=(), projects=(), files=(), cal=None, settings=None):
        return bd.week_ahead(date.fromisoformat(today), list(actions), list(raid), list(projects), list(files),
                             settings or self.SETTINGS, cal)

    @staticmethod
    def act(i, due, owner="Jane Doe", st="Open", p="ABC"):
        return {"id": f"ABC-A-{i:03d}", "p": p, "t": f"Action {i}", "o": owner, "due": due, "st": st}

    def test_the_window_runs_day_by_day_to_next_monday(self):
        """BL-319: to next Monday (a Monday looks a whole week on)."""
        for today, last, n in (("2026-10-05", "2026-10-12", 8),      # Monday: to the Monday after
                               ("2026-10-08", "2026-10-12", 5),      # Thursday
                               ("2026-10-09", "2026-10-12", 4),      # Friday
                               ("2026-10-10", "2026-10-12", 3),      # Saturday
                               ("2026-10-11", "2026-10-12", 2)):     # Sunday
            days = bd.week_window(date.fromisoformat(today))
            self.assertEqual((days[-1].isoformat(), len(days)), (last, n), today)
            self.assertEqual(days[-1].weekday(), 0)

    def test_weekends_show_only_with_a_meeting(self):
        w = self.week("2026-10-09")                                           # a Friday, no calendar
        self.assertEqual([d["dow"] for d in w["days"]], ["Friday", "Monday"])         # BL-319: to next Monday
        cal = {"days": {"2026-10-10": [ev("", "10:00", "11:00", "Offsite")]}}
        w = self.week("2026-10-09", cal=cal)
        self.assertEqual([d["dow"] for d in w["days"]][:3], ["Friday", "Saturday", "Monday"])
        self.assertEqual(w["days"][1]["meetings"][0]["title"], "Offsite")

    def test_weekend_due_items_move_to_monday_unless_there_is_a_meeting(self):
        acts = [self.act(1, "2026-10-10"), self.act(2, "2026-10-11"), self.act(3, "2026-10-12")]
        w = self.week("2026-10-09", actions=acts)
        mon = next(d for d in w["days"] if d["date"] == "2026-10-12")
        self.assertEqual(sorted((i["id"], bool(i.get("weekend"))) for i in mon["items"] if i["kind"] == "actions"),
                         [("ABC-A-001", True), ("ABC-A-002", True), ("ABC-A-003", False)])
        self.assertFalse(any(d["weekend"] for d in w["days"]))                 # no weekend day without a meeting
        cal = {"days": {"2026-10-10": [ev("", "10:00", "11:00", "Offsite")]}}
        w = self.week("2026-10-09", actions=acts, cal=cal)
        sat = next(d for d in w["days"] if d["date"] == "2026-10-10")
        self.assertEqual([i["id"] for i in sat["items"]], ["ABC-A-001"])       # the meeting keeps its own day's items
        mon = next(d for d in w["days"] if d["date"] == "2026-10-12")
        self.assertEqual(sorted(i["id"] for i in mon["items"]), ["ABC-A-002", "ABC-A-003"])

    def test_only_open_items_due_inside_the_window_land(self):
        acts = [self.act(1, "2026-10-07"), self.act(2, "2026-10-04"), self.act(3, "2026-10-12"),
                self.act(4, "2026-10-08", st="Closed"), self.act(5, None)]
        w = self.week("2026-10-05", actions=acts)                             # Monday: the window ends on Monday the 12th
        landed = [(i["id"], i.get("od")) for d in w["days"] for i in d["items"] if i["kind"] == "actions"]
        # BL-319: the overdue one leads the first day, saying how late; closed and undated ones don't land
        self.assertEqual(landed, [("ABC-A-002", 1), ("ABC-A-001", None), ("ABC-A-003", None)])

    def test_milestones_land_on_their_day_and_reports_do_not(self):
        """BL-127: the Week ahead has no weekly or client report lines; the reminders in Needs attention carry them."""
        proj = {"code": "ABC", "name": "Example Programme", "rhythm": "Weekly", "ms": [["UAT start", "2026-10-07", "", "ABC-M-001", None, None, "Planned"],
                                                           ["Done one", "2026-10-07", "done", "ABC-M-002", None, None, "Done"]]}
        files = [{"p": "ABC", "n": "2026-10-02 Client report.docx", "date": "2026-10-02", "f": "reports"}]
        w = self.week("2026-10-05", projects=[proj], files=files)
        by = {d["date"]: [(i["kind"], i["t"]) for i in d["items"]] for d in w["days"]}
        self.assertEqual(by["2026-10-07"], [("milestone", "UAT start")])
        self.assertFalse(any(i["kind"] == "report" for d in w["days"] for i in d["items"]))     # Friday, unfiled weekly; client report due 09-10
        self.assertEqual(by["2026-10-09"], [])
        # the same Friday afternoon, the reminders still ask for both reports
        now = datetime(2026, 10, 9, 14, 0)
        rem = bd.reminders(self.SETTINGS, [proj], files, date(2026, 10, 9), now)
        self.assertTrue(any(r["id"].startswith("weekly:2026-10-09") and r["cmd"].startswith("weekly report ABC") for r in rem))
        mon = bd.reminders(self.SETTINGS, [proj], files, date(2026, 10, 12), datetime(2026, 10, 12, 9, 0))
        self.assertTrue(any(r["cmd"] == "client report ABC" for r in mon))                  # last 02-10 + 7 days has passed

    def test_a_filed_weekly_report_changes_nothing_in_the_week_ahead(self):
        proj = {"code": "ABC", "name": "Example Programme", "rhythm": "", "ms": []}
        files = [{"p": "ABC", "n": "2026-10-09 Weekly report.docx", "date": "2026-10-09", "f": "reports"}]
        acts = [self.act(1, "2026-10-08")]
        w = self.week("2026-10-05", actions=acts, projects=[proj], files=files)
        self.assertEqual([i["id"] for d in w["days"] for i in d["items"]], ["ABC-A-001"])

    def test_noise_is_kept_out_and_meetings_worth_preparing_are_marked(self):
        cal = {"days": {"2026-10-07": [ev("", "09:00", "09:30", "ToDo: expenses"), ev("", "10:00", "10:30", "Info: town hall"),
                                       ev("", "11:00", "11:30", "FYI: new policy"), ev("", "12:00", "12:30", "Lunch"),
                                       ev("", "13:00", "14:00", "ABC SteerCo", p="ABC"), ev("", "15:00", "15:30", "My sync", organiser=True),
                                       ev("", "16:00", "16:30", "DEF catch-up", p="DEF"), ev("", "17:00", "17:30", "Skip me please")]}}
        rules = {**self.SETTINGS, "sweep": {"ignore": [{"name": "x", "where": ["calendar"], "field": "subject", "how": "begins",
                                                         "text": "skip me", "on": True}]}}
        acts = [self.act(1, "2026-10-01", p="DEF")]                         # DEF has overdue work
        w = self.week("2026-10-05", actions=acts, cal=cal, settings=rules)
        mts = {m["title"]: m["plan"] for d in w["days"] for m in d["meetings"]}
        self.assertEqual(set(mts), {"Lunch", "ABC SteerCo", "My sync", "DEF catch-up"})      # ToDo, Info:, FYI: and the rule gone
        self.assertIsNone(mts["Lunch"])
        self.assertEqual(mts["ABC SteerCo"], "a steering or review meeting")
        self.assertEqual(mts["My sync"], "you organise it")
        self.assertIn("1 overdue", mts["DEF catch-up"])

    def test_week_ahead_priorities_limit_the_work_items_but_not_milestones_or_meetings(self):
        acts = [dict(self.act(1, "2026-10-07"), pr="Medium"), dict(self.act(2, "2026-10-07"), pr="Urgent"),
                dict(self.act(3, "2026-10-07"), pr="High")]
        raid = [{"id": "ABC-R-001", "p": "ABC", "t": "Risk", "o": "Jane Doe", "due": "2026-10-07", "st": "Open",
                 "type": "Risk", "pr": "Low"}]
        proj = {"code": "ABC", "rhythm": "", "ms": [["UAT", "2026-10-07", "", "ABC-M-001", None, None, "Planned"]]}
        cal = {"days": {"2026-10-07": [ev("", "10:00", "11:00", "Sync")]}}
        w = self.week("2026-10-05", actions=acts, raid=raid, projects=[proj], cal=cal,
                      settings={"dashboard": {"week_ahead_priorities": ["Urgent", "High"]}})
        wed = next(d for d in w["days"] if d["date"] == "2026-10-07")
        self.assertEqual([i["id"] for i in wed["items"]], ["ABC-A-002", "ABC-A-003", "ABC-M-001"])
        self.assertEqual(len(wed["meetings"]), 1)
        w = self.week("2026-10-05", actions=acts, raid=raid, settings={"dashboard": {"week_ahead_priorities": []}})
        self.assertEqual(len(next(d for d in w["days"] if d["date"] == "2026-10-07")["items"]), 4)    # empty: everything

    # ===== BL-235 (fix-small-17): the Settings ticks read the same setting the Week ahead reads =====
    def test_the_settings_page_gets_the_week_ahead_priorities_and_none_means_all(self):
        self.assertEqual(bd.ui_settings({"dashboard": {"week_ahead_priorities": ["Urgent", "High"]}})["weekPrios"], ["Urgent", "High"])
        self.assertEqual(bd.ui_settings({"dashboard": {"week_ahead_priorities": []}})["weekPrios"], [])
        self.assertEqual(bd.ui_settings({})["weekPrios"], [])                       # missing: no ticks, which means every priority
        acts = [dict(self.act(n, "2026-10-07"), pr=pr) for n, pr in ((1, "Urgent"), (2, "High"), (3, "Medium"), (4, "Low"))]
        for setting in ({}, {"dashboard": {"week_ahead_priorities": []}}):
            w = self.week("2026-10-05", actions=acts, settings=setting)
            self.assertEqual(len(next(d for d in w["days"] if d["date"] == "2026-10-07")["items"]), 4)
    # ===== end BL-235 =====

    def test_decisions_late_work_and_milestones_at_risk_say_why(self):
        """BL-319: pending decisions needed in the window land on their day; late work (the priorities the setting lists) and
        late decisions land on the first day with `od`; a milestone carries `slip`."""
        acts = [dict(self.act(1, "2026-10-01"), pr="Urgent"), dict(self.act(2, "2026-10-02"), pr="Low")]
        decs = [{"id": "ABC-D-001", "p": "ABC", "t": "Pick a vendor", "by": "Jane Doe", "st": "Pending", "due": "2026-10-07"},
                {"id": "ABC-D-002", "p": "ABC", "t": "Late one", "by": "Jane Doe", "st": "Pending", "due": "2026-10-03"},
                {"id": "ABC-D-003", "p": "ABC", "t": "Made", "by": "Jane Doe", "st": "Made", "due": "2026-10-07"}]
        proj = {"code": "ABC", "rhythm": "", "ms": [["UAT", "2026-10-08", "slip", "ABC-M-001", None, None, "Planned"]]}
        w = bd.week_ahead(date(2026, 10, 5), acts, [], [proj], [], {"dashboard": {"week_ahead_priorities": ["Urgent"]}}, None, decs)
        by = {d["date"]: [(i["kind"], i["id"], i.get("od"), i.get("slip")) for i in d["items"]] for d in w["days"]}
        self.assertEqual(by["2026-10-05"], [("actions", "ABC-A-001", 4, None), ("decisions", "ABC-D-002", 2, None)])   # Low is left out
        self.assertEqual(by["2026-10-07"], [("decisions", "ABC-D-001", None, None)])
        self.assertEqual(by["2026-10-08"], [("milestone", "ABC-M-001", None, True)])

    def test_urgent_first_undated_urgent_and_further_ahead(self):
        acts = [dict(self.act(1, "2026-10-07"), pr="Medium"), dict(self.act(2, "2026-10-07"), pr="Urgent"),
                dict(self.act(3, None), pr="Urgent"), dict(self.act(4, "2026-10-14"), pr="High"),
                dict(self.act(5, "2026-10-15"), pr="Low"), dict(self.act(6, "2026-10-30"), pr="Urgent")]
        proj = {"code": "ABC", "rhythm": "", "ms": [["UAT", "2026-10-20", "", "ABC-M-001", None, None, "Planned"]]}
        w = self.week("2026-10-05", actions=acts, projects=[proj], settings={"reminders": {"enabled": False}})
        wed = next(d for d in w["days"] if d["date"] == "2026-10-07")
        self.assertEqual([i["id"] for i in wed["items"]], ["ABC-A-002", "ABC-A-001"])        # Urgent before Medium
        self.assertEqual([i["id"] for i in w["undated"]], ["ABC-A-003"])
        self.assertEqual(w["further_to"], "2026-10-26")                                     # two weeks after Monday the 12th
        self.assertEqual([(i["date"], i.get("id")) for i in w["further"]],
                         [("2026-10-14", "ABC-A-004"), ("2026-10-20", "ABC-M-001")])         # High and milestones; Low and later left out

    def test_the_built_page_carries_the_week(self):
        v = Vault()
        try:
            populate(v)
            v.run(script="build_dashboard.py")
            html = (v.root / "dashboard.html").read_text(encoding="utf-8")
        finally:
            v.cleanup()
        import json
        import re
        data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S).group(1))
        w = data["week"]
        self.assertEqual(w["from"], date.today().isoformat())
        self.assertEqual(date.fromisoformat(w["to"]).weekday(), 0)                         # BL-319: next Monday
        self.assertEqual(w["to"], bd.week_window(date.today())[-1].isoformat())


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
class TodayBriefTests(PageTests):
    """BL-72: Today reads as a brief. The page is probed in headless Chrome with fixtures set in the page."""

    SETUP = """
      const grp=(file,n0,rows)=>rows.map((r,i)=>({n:n0+i,p:"ABC",kind:"actions",why:"Strong match",indiv:false,flags:[],file,ref:i+1,
        rec:{t:"Task "+(n0+i)},src:"",...r}));
      window.setRev=list=>{ REV.length=0; list.forEach(x=>REV.push(x)); REMINDERS.length=0;
        A.forEach(x=>{ if(!x.o||x.o==="TBC") x.o="Jane Doe"; if(!x.due) x.due="2099-01-01"; });   /* no "missing an owner or a due date" line */
        R.forEach(r=>{ if(!r.o||r.o==="TBC") r.o="Jane Doe"; }); };
      window.visible=sel=>[...document.querySelectorAll(sel)].filter(e=>!e.hidden);
    """

    def test_the_sections_come_in_order_in_one_980px_column(self):
        o = self.probe(self.SETUP + """
          go("today"); renderToday();
          const heads=[...document.querySelectorAll("#tBrief .tsec:not(.setupsec) .th")].map(h=>h.firstChild.textContent.trim()), band=document.querySelector(".dayband"), brief=document.getElementById("tBrief");
          const cols=[document.querySelector("#v-today .bandin"),brief], view=document.getElementById("v-today"), cs=getComputedStyle(view);
          const inner=view.clientWidth-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight);
          const sheetRules=[]; for(const sh of document.styleSheets) for(const r of sh.cssRules) if(r.media&&/max-width:\\s*640px/.test(r.conditionText||r.media.mediaText)) for(const c of r.cssRules) sheetRules.push(c.cssText);
          window.OUT={heads,bandFirst:!!(band.compareDocumentPosition(brief)&Node.DOCUMENT_POSITION_FOLLOWING),
            ratios:cols.map(c=>+(c.getBoundingClientRect().width/inner).toFixed(4)), lefts:cols.map(c=>c.getBoundingClientRect().left), inner,
            narrow:sheetRules.some(t=>/\\.thome\\s*\\{[^}]*max-width:\\s*none/.test(t)), cards:document.querySelectorAll("#tBrief .card, #tBrief .col").length,
            portfolioLast:brief.lastElementChild.querySelector("h2").textContent, day:!!document.getElementById("dayLine"), mtgs:!!document.getElementById("dayMeets"),
            headline:document.getElementById("dayHead").tagName,
            overlap:[...document.querySelectorAll("#tBrief > .tsec")].filter(e=>!e.hidden).map((e,i,a)=>i&&e.getBoundingClientRect().top<a[i-1].getBoundingClientRect().bottom-0.5).filter(Boolean).length,
            listsHeight:[...document.querySelectorAll("#tBrief ol.bl")].every(o=>o.getBoundingClientRect().height>=[...o.children].reduce((h,c)=>h+c.getBoundingClientRect().height,0)-1)};""")
        # BL-319: To decide first after the band, then BL-295's First thing and BL-210's Decisions needed; BL-125 A's two inside
        # Your commitments; Resolved after the Week ahead (folded); Portfolio last (the hidden ones are in the page too)
        self.assertEqual(o["heads"], ["To decide", "First thing", "Decisions needed", "Needs attention", "Your commitments", "You owe", "Waiting on",
                                      "Week ahead", "Resolved", "Portfolio"])
        self.assertTrue(o["bandFirst"])
        self.assertAlmostEqual(o["ratios"][0], 1, delta=0.005)                     # the header at full width
        self.assertLessEqual(o["ratios"][1]*o["inner"], 980.5)                     # the sections at a 980px reading width, centred
        self.assertAlmostEqual(o["lefts"][1]-o["lefts"][0], (o["inner"]-o["ratios"][1]*o["inner"])/2, delta=1.5)
        self.assertTrue(o["narrow"])                                               # full width with gutters below 640px
        self.assertEqual(o["cards"], 0)
        self.assertEqual(o["overlap"], 0)                                          # the sections stack; none sits on another
        self.assertTrue(o["listsHeight"])
        self.assertEqual((o["portfolioLast"], o["headline"]), ("Portfolio", "H1"))
        self.assertTrue(o["day"] and o["mtgs"])

    def test_needs_attention_lists_no_proposals_they_are_in_to_decide(self):
        """BL-319 (Alan, 14-10-2026): no per-meeting groups and no Approve n routine in Needs attention; proposals are To decide's."""
        o = self.probe(self.SETUP + """
          const meet={n:1,p:"ABC",kind:"draft",why:"Draft minutes",indiv:true,file:"proposed-2026-10-05-0900.json",ref:"meeting",projects:["ABC"],rec:{t:"Draft minutes: ABC Steering"}};
          setRev([meet,...grp("proposed-2026-10-05-0900.json",2,[{}]),...grp("proposed-0000-00-01-demo.json",10,[{},{}])]); go("today"); renderToday();
          window.OUT={attn:document.getElementById("attnList").textContent, qa:document.querySelectorAll("#attnList [data-qa]").length,
            td:document.querySelectorAll("#tdList > li.td-review").length};""")
        self.assertNotIn("Review the", o["attn"])
        self.assertNotIn("routine", o["attn"])
        self.assertEqual(o["qa"], 0)
        self.assertEqual(o["td"], 4)                                                  # every proposal is a row of To decide

    def test_reminders_move_in_with_run_and_dismiss_in_a_menu(self):
        o = self.probe(self.SETUP + """
          setRev([]); REMINDERS.push({id:"weekly:2026-10-09",text:"Weekly report for week ending 09-10-2026 is due",cmd:"weekly report for week ending 09-10-2026"},
            {id:"client:ABC:2026-09-01",text:"ABC client report is due (last: 01-09-2026)",cmd:"client report ABC"});
          go("today"); renderToday(); const rem=[...document.querySelectorAll("#attnList .rem")], first=rem[0];
          first.querySelector(".dots").click(); const open=!!document.querySelector("#remMenu[role=menu]")&&first.querySelector(".dots").getAttribute("aria-expanded")==="true";
          window.OUT={n:rem.length,titles:rem.map(r=>r.querySelector("a.t").textContent),open,menu:[...document.querySelectorAll("#remMenu [role=menuitem]")].map(b=>[b.textContent,b.getAttribute("aria-disabled")==="true"]),
            old:!!document.getElementById("notes"), links:rem.map(r=>r.querySelector("a.t").dataset.cock||r.querySelector("a.t").dataset.go), label:first.querySelector(".dots").getAttribute("aria-label")};""")
        self.assertEqual(o["n"], 2)
        self.assertEqual(o["menu"][0][0], "Run report now")
        self.assertEqual([m[0] for m in o["menu"]][1:], ["Dismiss for this session", "Dismiss forever"])
        self.assertTrue(o["open"])
        self.assertFalse(o["old"])                                                  # the pill row is gone
        self.assertEqual(o["links"], ["projects", "ABC"])
        self.assertTrue(o["label"].startswith("Options: Weekly report"))

    def test_needs_attention_lists_work_with_no_owner_or_due_date(self):
        o = self.probe(self.SETUP + """
          setRev([]); A.length=0; R.length=0;
          A.push({id:"ABC-A-901",p:"ABC",t:"No owner",o:"TBC",st:"Open",due:"2026-12-01"},{id:"ABC-A-902",p:"ABC",t:"No date",o:"Jane Doe",st:"Open",due:null},
                 {id:"ABC-A-903",p:"ABC",t:"Fine",o:"Jane Doe",st:"Open",due:"2026-12-01"},{id:"ABC-A-904",p:"ABC",t:"Closed",o:"TBC",st:"Closed",due:null});
          R.push({id:"ABC-901",p:"ABC",type:"Risk",t:"Unowned risk",o:"TBC",st:"Open",due:null});
          go("today"); renderToday();
          const li=[...document.querySelectorAll("#attnList > li")].find(l=>/missing an owner/.test(l.textContent));
          const links=li?[...li.querySelectorAll("[data-gap]")].map(a=>[a.dataset.gap,a.textContent]):[];
          li.querySelector('[data-gap="ABC|due"]').click(); await new Promise(r=>setTimeout(r,50));
          window.OUT={title:li&&li.querySelector("a.t").textContent,links,view:VIEW,wt:WT};""")
        self.assertEqual(o["title"], "3 work items are missing an owner or a due date")   # the closed one doesn't count
        self.assertIn(["ABC|actions", "1 action"], o["links"])
        self.assertIn(["ABC|raid", "1 risk or issue"], o["links"])
        self.assertIn(["ABC|due", "1 action"], o["links"])
        self.assertEqual((o["view"], o["wt"]), ("work", "actions"))                      # the count opens Work, filtered

    def test_resolved_lists_items_closed_since_the_last_visit(self):
        o = self.probe(self.SETUP + """
          const a1=A[0].id, a2=A[1].id, r1=R[0].id, mk=(at,id,tbl,change,extra)=>({at,id,tbl,item:"Item "+id,change,what:"x",by:"Approved in review",undone:false,...extra});
          const read=()=>({n:document.querySelectorAll("#chgList > li").length, shown:visible("#chgList > li").length, titles:visible("#chgList > li a.t").map(a=>a.textContent),
            empty:(document.querySelector("#chgList .none")||{}).textContent, head:document.getElementById("chgTitle").textContent, foot:document.getElementById("chgMore").textContent,
            see:document.querySelector("#chgMore a").dataset.go, first:(document.querySelector("#chgList p")||{}).textContent});
          go("today");
          ACT=[mk("1999-01-01 09:00",a1,"actions","status: Open → Closed"), mk("9999-01-01 09:00",a2,"actions","status: Open → Closed"),
               mk("9999-01-01 10:00",r1,"raid","status: Open → Closed",{by:"You, in the dashboard"}), mk("9999-01-01 11:00","ABC-A-099","actions","status: Open → Closed",{undone:true}),
               mk("9999-01-01 12:00",a1,"actions","due date: 01-01-2026 → 02-01-2026"), mk("9999-01-01 13:00",a1,"actions","status: Open → Cancelled")];
          renderToday(); const some=read();
          ACT=[mk("1999-01-01 09:00",a1,"actions","status: Open → Closed")]; renderToday(); const none=read();
          ACT=[...Array(7)].map((_,i)=>mk("9999-01-01 1"+i+":00","ABC-A-1"+i,"actions","status: Open → Closed")); renderToday(); const many=read();
          window.OUT={some,none,many,last:longDate(LASTVISIT.slice(0,10))};""")
        s = o["some"]
        self.assertEqual(s["n"], 2)                                                  # not the old, undone, non-status or Cancelled ones
        self.assertTrue(all(t.startswith("Item ") for t in s["titles"]))
        self.assertIn("closed", s["first"])
        self.assertIn(o["last"], s["head"])
        self.assertEqual(s["see"], "activity")                                       # the footer link
        self.assertEqual(o["none"]["empty"], f"Nothing has been resolved since {o['last']}.")
        self.assertEqual((o["many"]["n"], o["many"]["shown"]), (7, 5))              # top five, then "+2 more"
        self.assertIn("+2 more", o["many"]["foot"])

    def test_week_ahead_draws_the_data_it_is_given(self):
        o = self.probe(self.SETUP + """
          const me=S.me;
          D.week={from:"2026-10-09",to:"2026-10-16",days:[
            {date:"2026-10-09",dow:"Friday",weekend:false,meetings:[],items:[{kind:"actions",id:"ABC-A-001",p:"ABC",t:"Mine today",o:me},{kind:"actions",id:"ABC-A-002",p:"ABC",t:"Theirs today",o:"Omar Ali"}]},
            {date:"2026-10-10",dow:"Saturday",weekend:true,meetings:[{start:"10:00",end:"11:00",title:"Offsite",p:"ABC"}],items:[]},
            {date:"2026-10-12",dow:"Monday",weekend:false,meetings:[],items:[{kind:"actions",id:"ABC-A-003",p:"ABC",t:"Over the weekend",o:"Sara Example",weekend:true},{kind:"milestone",id:"ABC-M-001",p:"ABC",t:"UAT start"}]},
            {date:"2026-10-13",dow:"Tuesday",weekend:false,meetings:[],items:[]},
            {date:"2026-10-16",dow:"Friday",weekend:false,meetings:[],items:[{kind:"actions",id:"ABC-A-004",p:"ABC",t:"Friday action",o:"Sara Example"}]}]};
          go("today"); renderToday(); const days=[...document.querySelectorAll("#weekList .wkday")];
          window.OUT={days:days.map(d=>[d.querySelector(".wkdh").textContent,false,[...d.querySelectorAll("li.wkrow")].map(x=>x.querySelector(".tb").textContent+" | "+x.querySelector(".wkwhy").textContent)]),to:document.getElementById("weekTo").textContent,note:document.querySelector("#weekList .wknote").textContent,
            acts:[...document.querySelectorAll("#weekList li.wkrow")].map(x=>[...x.querySelectorAll(".tacts button")].map(b=>b.dataset.tip))};
          D.week={from:"2026-10-09",to:"2026-10-09",days:[]}; renderToday(); window.OUT.empty=document.querySelector("#weekList .none").textContent;""")
        names = [d[0] for d in o["days"]]
        self.assertEqual(names, ["Today", "Saturday 10th October", "Monday 12th October", "Friday 16th October"])   # an empty Tuesday is skipped
        today = o["days"][0]
        self.assertFalse(any(d[1] for d in o["days"]))                           # no "one thing" / "a couple of things" counts
        self.assertIn("Theirs today", today[2][0])
        self.assertFalse(any("Mine today" in x for x in today[2]))                  # mine are under Your commitments already
        self.assertEqual(o["days"][1][2], ["10:00 Offsite — Example Programme | in your calendar"])   # a weekend day appears for its meeting
        self.assertEqual(o["days"][2][2][0], "Over the weekend — Sara Example, Example Programme | due over the weekend")   # BL-319: why it is there
        self.assertEqual(o["days"][2][2][1], "UAT start — Example Programme | due · on track")
        self.assertIn("Friday action", o["days"][3][2][0])
        self.assertEqual(o["to"], "to Friday 16th October")
        self.assertEqual(o["note"], "Work of every priority, every milestone and decision, and meetings")   # what the setting lists
        self.assertEqual(o["acts"][0], ["Draft a chase", "Move the date"])          # someone else's action: chase it, or move it
        self.assertEqual(o["acts"][3], ["Open the project"])                          # a milestone
        self.assertEqual(o["empty"], "Nothing is due or booked until Friday 9th October.")

    def test_contrast_in_every_theme_and_mode(self):
        o = self.probe(self.SETUP + r"""
          const lum=c=>{ const [r,g,b]=c.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
          const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
          REMINDERS.length=0; REMINDERS.push({id:"weekly:x",text:"Weekly report due",cmd:"weekly report"});
          const f="proposed-2026-10-05-0900.json"; REV.length=0; grp(f,1,[{}]).forEach(x=>REV.push(x));
          D.week={from:TODAY,to:TODAY,days:[{date:TODAY,dow:"Today",weekend:false,meetings:[],items:[{kind:"actions",id:"ABC-A-002",p:"ABC",t:"Task",o:"Omar Ali",weekend:true}]}]};
          const bg=el=>{ for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; if(!/rgba\(0, 0, 0, 0\)|transparent/.test(c)) return c; } return "rgb(255,255,255)"; };
          const out={}; go("today");
          for(const pal of THEMES.map(t=>t.id)) for(const mode of ["Light","Dark"]){ S.palette=pal; S.theme=mode; applyTheme(); renderToday();
            const probes={title:"#attnList a.t", number:"#attnList .n", body:"#attnList p", inlineLink:"#attnList p a.s", quiet:"#attnList button.qa", dots:"#attnList .dots",
              heading:"#tBrief h2.th", count:"#tBrief .th .cnt", late:"#mineList .late, #weekList .wkwhy", weekLine:"#weekList .wkrow .tb", dayLabel:"#weekList .wkdh", weekTag:"#weekList .wktag",
              none:"#chgList .none", headline:"#dayHead", date:"#todayDate", lead:"#briefText"};
            for(const [k,sel] of Object.entries(probes)){ const el=document.querySelector(sel); if(!el) continue; out[`${pal}|${mode}|${k}`]=ratio(getComputedStyle(el).color,bg(el)); }
            const dot=document.querySelector("#dayLine .dot"); if(dot) out[`${pal}|${mode}|dot`]=ratio(getComputedStyle(dot).fill,bg(dot)); }
          window.OUT={out,kinds:[...new Set(Object.keys(out).map(k=>k.split("|")[2]))]};""")
        self.assertGreaterEqual(len(o["kinds"]), 14)
        for key, r in o["out"].items():
            self.assertGreaterEqual(r, 4.5, key)


class HeaderTests(PageTests):
    """BL-81: the search stays at the left; ask creaite and the theme button sit at the right edge."""

    BAR = """(()=>{ const r=e=>document.querySelector(e).getBoundingClientRect(), bar=r(".bar"), pad=parseFloat(getComputedStyle(document.querySelector(".bar")).paddingRight);
      return {theme:Math.round(bar.right-pad-r("#themeBtn").right), askGap:Math.round(r("#themeBtn").left-r("#askBtn").right), searchLeft:Math.round(r("#searchBtn").left-bar.left),
        searchW:Math.round(r("#searchBtn").width), status:document.getElementById("status").textContent.trim(), statusRight:document.getElementById("status").offsetParent?Math.round(r("#askBtn").left-r("#status").right):null}; })()"""

    def test_the_buttons_are_at_the_right_edge_with_the_strip_empty_and_showing(self):
        o = self.probe("VSTATE='ok'; HELD=[]; status(); const quiet=" + self.BAR + "; VSTATE='prompt'; HELD=[()=>{},()=>{}]; status(); const shown=" + self.BAR +
                       "; window.OUT={quiet,shown};")
        quiet, shown = o["quiet"], o["shown"]
        self.assertEqual(quiet["status"], "")
        self.assertEqual(quiet["theme"], 0)                                      # the theme button's right edge is the bar's content edge
        self.assertEqual(quiet["askGap"], 12)                                   # ask creaite is just left of it
        self.assertNotEqual(shown["status"], "")
        self.assertEqual(shown["theme"], 0)                                      # and still is when the strip shows
        self.assertEqual(shown["statusRight"], 12)                               # the strip sits right before ask creaite
        self.assertEqual((quiet["searchLeft"], shown["searchLeft"]), (20, 20))   # the search box keeps its left edge
        self.assertGreaterEqual(quiet["searchW"], shown["searchW"])             # the search box gives way to the strip, never the other way round


class TodayHeadingTests(PageTests):
    """BL-325 (Alan, 14-10-2026; was BL-79's bold 13px capitals): the six section headings on Today (five, and BL-210's Decisions
    needed) are the one shared section heading, in every theme and mode: sentence case, the size, weight, face and spacing any
    h2 has in that theme (as Settings' and Intake's), on one line, with the count beside them light."""

    def test_the_headings_are_the_shared_h2_in_every_theme_and_mode(self):
        o = self.probe("""
          const out={}; go("today"); const ref=document.createElement("h2"); ref.textContent="Reference"; document.body.append(ref);
          const sig=c=>[c.fontWeight, c.fontSize, c.fontFamily, c.letterSpacing, c.textTransform];
          for(const pal of THEMES.map(t=>t.id)) for(const mode of ["Light","Dark"]){ S.palette=pal; S.theme=mode; applyTheme();
            out[pal+"|"+mode]={ref:sig(getComputedStyle(ref)),rows:[...document.querySelectorAll("#tBrief .tsec:not(.setupsec) h2.th")].map(h=>{
              const n=h.querySelector(".cnt"), cc=n?getComputedStyle(n):null;
              return [sig(getComputedStyle(h)), cc&&cc.fontWeight, h.getBoundingClientRect().height, h.firstChild.textContent.trim()]; })}; }
          ref.remove(); window.OUT={out};""")
        self.assertEqual(len(o["out"]), theme_count() * 2)                       # every theme × 2 modes
        for key, v in o["out"].items():
            self.assertEqual(len(v["rows"]), 8, key)                                   # BL-319's To decide and BL-295's First thing too; BL-125 A's You owe and Waiting on are h3 sub-headings
            for sig, count, height, text in v["rows"]:
                self.assertEqual(sig, v["ref"], key)                                       # exactly the shared h2
                self.assertEqual(sig[4], "none", key)                                      # no capitals
                self.assertEqual(text[:1] + text[1:].lower(), text, key)                  # sentence case in the words themselves
                self.assertIn(count, (None, "400"), key)                                   # the count beside it stays light
                self.assertLess(height, 30, key)                                           # one line


class EditGroundTests(PageTests):
    """BL-80: the side panel keeps its normal (white, in light mode) ground while editing, in every theme and mode (BL-176: the
    peek's ground and a new item's form are the same)."""

    def test_the_ground_is_the_same_reading_and_editing_and_the_banner_reads(self):
        o = self.probe(r"""
          const lum=c=>{ const [r,g,b]=c.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
          const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
          const ground=el=>{ for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; if(!/rgba\(0, 0, 0, 0\)|transparent/.test(c)) return c; } return "none"; };
          const out={}; go("work"); const id=A[0].id;
          for(const pal of THEMES.map(t=>t.id)) for(const mode of ["Light","Dark"]){ S.palette=pal; S.theme=mode; applyTheme();
            openRecord("actions",id); const read=ground(document.getElementById("pkScroll")); closePanel();   /* BL-176: the peek's ground */
            openProject("ABC","health"); const edit=ground(document.getElementById("pBody")), b=document.getElementById("editBanner");   /* a form (BL-179: New is the peek; BL-186: a milestone is its editor; project health keeps its form) */
            out[pal+"|"+mode]={read,edit,banner:ratio(getComputedStyle(b).color,edit),shown:getComputedStyle(b).display,edit_token:getComputedStyle(document.documentElement).getPropertyValue("--edit").trim()};
            closePanel(); }
          window.OUT={out};""")
        self.assertEqual(len(o["out"]), theme_count() * 2)                       # every theme × 2 modes
        for key, r in o["out"].items():
            self.assertEqual(r["read"], r["edit"], key)                        # no tint while editing
            self.assertEqual(r["edit_token"], "", key)                         # and no token to bring it back
            self.assertEqual(r["shown"], "block", key)                         # the banner is how editing shows
            self.assertGreaterEqual(r["banner"], 4.5, key)
            if key.endswith("Light"):
                self.assertEqual(r["edit"], "rgb(255, 255, 255)", key)         # white in light mode, in every theme


class NoCalendarLineTests(PageTests):
    """BL-151: with no calendar the day band is one line, "No calendar yet", with Refresh calendar beside it; a calendar
    with no meetings today keeps its line and says "No meetings today"; with meetings the band opens as before."""

    def test_no_calendar_one_line_then_a_day(self):
        o = self.probe("""
          go("today"); const out={};
          D.calendar=null; renderDay(); const band=document.querySelector("#v-today .dayband");
          out.none={line:!document.getElementById("dayLine").hidden, text:(document.querySelector("#dayMeets .daynone")||{}).textContent||"",
            btn:!!document.querySelector("#dayMeets [data-refcal]"), h:band.getBoundingClientRect().height, old:document.getElementById("dayMeets").textContent.includes("Your meetings appear here")};
          D.calendar={fetched:TODAY+"T07:00:00",days:{[TODAY]:[]}}; renderDay();
          out.empty={line:!document.getElementById("dayLine").hidden, head:document.getElementById("dayHead").textContent, h:band.getBoundingClientRect().height};
          D.calendar={fetched:TODAY+"T07:00:00",days:{[TODAY]:[{title:"Steering",start:"10:00",end:"11:00"}]}}; renderDay();
          out.day={line:!document.getElementById("dayLine").hidden, meets:document.querySelectorAll("#dayMeets .dm").length};
          window.OUT=out;""")
        self.assertFalse(o["none"]["line"])                                       # no empty timeline
        self.assertTrue(o["none"]["text"].startswith("No calendar yet"))
        self.assertIn("Refresh calendar", o["none"]["text"])
        self.assertTrue(o["none"]["btn"])
        self.assertFalse(o["none"]["old"])
        self.assertTrue(o["empty"]["line"])                                       # a calendar opens the band as before
        self.assertIn("No meetings today", o["empty"]["head"])
        self.assertLess(o["none"]["h"], o["empty"]["h"] - 60)                     # the one line is much smaller
        self.assertEqual((o["day"]["line"], o["day"]["meets"]), (True, 1))


if __name__ == "__main__":
    unittest.main()
