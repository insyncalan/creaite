"""Help Phase B, "finding it" (#158): one search over all of Help, the twelve jobs, What's new, the ? key panel, the foot line,
the first-visit line and the printed cards.

Run: python3 dev/tests/test_help_finding.py   (the page tests need Google Chrome; they are skipped otherwise)

Desktop and 900 px only. The page tests build a throwaway vault with fictional data and load the real dashboard in headless
Chrome; dates never matter here, so nothing depends on the clock.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import CHROME, populate  # noqa: E402
from test_insight import chrome  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_tracker import REPO, Vault  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(REPO / "dev" / "tools"))
import build_dashboard as bd  # noqa: E402

SCREENS = ["today", "work", "review", "projects", "people", "notes", "intake", "files"]


class DataTests(unittest.TestCase):
    """help.md and whats-new.md, parsed: the Jobs block, the Screen lines and the release notes."""

    @classmethod
    def setUpClass(cls):
        cls.h = bd.help_sections()
        cls.tasks = {t["id"] for t in cls.h["tasks"]}

    def test_the_twelve_jobs_each_resolve_to_a_page(self):
        jobs = self.h["jobs"]
        self.assertEqual(len(jobs), 12)
        self.assertEqual(jobs[0]["title"], "Start the day")
        for j in jobs:
            self.assertIn(j["id"], self.tasks, j)
            self.assertTrue(j["line"], j)
        self.assertEqual(self.tab("start").count('class="hp-job"'), 12)

    def tab(self, tid):
        return next(t["html"] for t in self.h["tabs"] if t["id"] == tid)

    def test_every_screen_id_resolves_and_the_lines_are_not_on_the_page(self):
        self.assertEqual(list(self.h["screens"]), SCREENS)
        sections = {s["id"] for s in self.h["sections"]}
        for k, s in self.h["screens"].items():
            self.assertTrue(1 <= len(s["ids"]) <= 5, k)
            for i in s["ids"]:
                self.assertIn(i, self.tasks, (k, i))
            self.assertIn(s["ref"], sections, k)
        for t in self.h["tabs"]:
            self.assertNotIn("Screen:", re.sub(r"<[^>]+>", " ", t["html"]))
            self.assertNotIn("Jobs:", re.sub(r"<[^>]+>", " ", t["html"]))

    def test_a_dead_id_is_refused(self):
        self.assertEqual(bd.help_check([{"id": "nope"}], {"review": {"title": "Review", "ids": ["start-the-day", "gone"], "ref": "nope"}},
                                       self.tasks, {"review"}),
                         ["Jobs: nope", "Screen Review: gone", "Screen Review: Reference nope"])

    def test_a_broken_screen_line_is_a_build_error_naming_the_line(self):
        for bad in ("Screen: Review review-and-approve-proposals", "Screen: Review -> a, b | Reference: review extra"):
            with self.assertRaises(ValueError) as cm:
                bd.help_screens(bad + "\n")
            self.assertIn(bad, str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            bd.help_screens("Screen: Review -> a\nScreen: Review -> b\n")
        self.assertIn("second Screen line for Review", str(cm.exception))
        self.assertEqual(len(self.h["screens"]["files"]["ids"]), 1)                    # Files has one job, and the header says 1 to 5
        self.assertIn("1 to 5 how-to ids", (REPO / "system" / "templates" / "help.md").read_text(encoding="utf-8")[:4000])

    def test_an_outside_link_in_the_notes_is_a_link_that_cannot_reach_back(self):
        ctx = bd._HelpCtx("dashboard", "whatsnew", "1.0.0", [])
        h = bd._hp_inline('See [the site](https://example.com/a?b=1&c=2) and [x](https://e.com/"><script>)', ctx)
        self.assertIn('<a href="https://example.com/a?b=1&amp;c=2" target="_blank" rel="noopener noreferrer">the site</a>', h)
        self.assertNotIn("<script>", h)

    def test_whats_new_is_a_fourth_tab_newest_first(self):
        self.assertEqual([t["id"] for t in self.h["tabs"]], ["start", "howto", "reference", "whatsnew"])
        news = self.h["news"]
        self.assertGreaterEqual(len(news), 21)
        vs = [tuple(int(x) for x in n["title"].split()[-1].split(".")) for n in news]
        self.assertEqual(vs, sorted(vs, reverse=True))
        self.assertIn('class="hp-new"', self.tab("whatsnew"))

    def test_the_installed_versions_notes_are_there(self):
        import whats_new
        version = (REPO / "VERSION").read_text().strip()
        self.assertTrue(whats_new.has(version), f"system/templates/help/whats-new.md has no section for {version}")

    def test_a_release_without_its_notes_is_refused(self):
        import build_release
        import update
        with self.assertRaises(update.UpdateError):
            build_release.refuse_missing_whats_new("99.9.9")
        build_release.refuse_missing_whats_new((REPO / "VERSION").read_text().strip())

    def test_the_add_step_puts_plain_notes_on_top_and_never_overwrites(self):
        import tempfile
        import whats_new
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "9.9.9-plain.md"
            f.write_text("# 9.9.9\n\nA fictional release.\n\n- **One.** Something.\n", encoding="utf-8")
            text = whats_new.add("9.9.9", f)
            self.assertLess(text.index("## creaite 9.9.9"), text.index("## creaite 2."))
            self.assertIn("- **One.** Something.", text)
            self.assertNotIn("# 9.9.9\n", text.replace("## creaite 9.9.9", ""))
            with self.assertRaises(ValueError):
                whats_new.add("2.1.0", f)


class CardTests(unittest.TestCase):
    """The first-day card and the top-12 card are Help blocks, not copies, and are current."""

    @classmethod
    def setUpClass(cls):
        import build_guides
        cls.bg = build_guides
        cls.built = build_guides.build()
        cls.disk = {n: (REPO / "system" / "templates" / n).read_text(encoding="utf-8") for n in cls.built}

    def test_they_are_current(self):
        for n, c in self.built.items():
            self.assertEqual(self.disk[n], c, f"{n} is out of date: run python3 dev/tools/build_guides.py")

    def test_the_first_day_card_is_the_loop_the_first_hour_and_the_four_rules(self):
        h = self.disk["guide-first-day.html"]
        self.assertEqual(h.count('class="hp-stage'), 5)
        self.assertEqual(h.count('class="hp-step"'), 4)
        self.assertEqual(h.count('class="hp-rule"'), 4)
        for gone in ("hp-beat", "hp-view", "hp-phrases", "hp-jobgrid"):
            self.assertNotIn(f'class="{gone}', h)
        self.assertIn("first day", h)

    def test_the_top_12_card_lists_the_twelve_jobs_with_their_page_names(self):
        h = self.disk["guide-how-to.html"]
        self.assertEqual(h.count('class="hp-topjob"'), 12)
        sec = bd.help_sections()
        titles = {t["id"]: t["title"] for t in sec["tasks"]}
        for j in sec["jobs"]:
            self.assertIn(titles[j["id"]], h)
        self.assertIn("break-before:page", h)                                          # two pages when printed


PAGE = r"""
  const wait=ms=>new Promise(r=>setTimeout(r,ms)), $q=s=>document.querySelector(s), $a=s=>[...document.querySelectorAll(s)], out={};
  VSTATE="ok"; needVault=async()=>true;
  const key=(k,t)=>(t||document).dispatchEvent(new KeyboardEvent("keydown",{key:k,bubbles:true,cancelable:true}));
  const type=q=>{ const i=$q("#helpQ"); i.value=q; i.dispatchEvent(new Event("input",{bubbles:true})); };
  helpScreenSync.__tick=0;
"""


class PageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not CHROME.exists():
            raise unittest.SkipTest("Google Chrome not installed")
        cls.v = v = Vault()
        populate(v)
        v.run(script="build_dashboard.py")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def probe(self, script):
        out, errors = chrome(self.v, PAGE + script, name="helpfind")
        self.assertEqual(errors, [])
        self.assertIsNotNone(out)
        self.assertNotIn("error", out, out)
        return out

    def test_search_finds_a_word_a_plural_and_nothing(self):
        o = self.probe("""
          go("help"); await wait(30);
          type("hand over"); out.word=[$q("#helpResults").hidden,$q("#helpPane").hidden,$a("#helpResults a.hp-r").map(a=>a.getAttribute("href")).slice(0,3),$a("#helpResults .hp-resg h3").map(h=>h.textContent),!!$q("#helpResults mark")];
          out.first=$q("#helpResults a.hp-r .hp-rt").textContent;
          const ids=q=>helpFind(q).map(r=>r.e.target);
          out.plural=[ids("milestones").slice(0,5).join()===ids("milestone").slice(0,5).join(), ids("milestone").length>0];
          out.case=ids("HAND OVER").join()===ids("hand over").join();
          out.accent=ids("hánd óver").join()===ids("hand over").join();
          out.prefix=ids("mileston").length>0&&ids("ilestone").length===0;   /* a prefix, not a part of a word */
          out.refWord=helpFind("keyboard").some(r=>r.e.tab==="reference");
          out.howWord=helpFind("approve").some(r=>r.e.tab==="howto");
          type("zzqxv"); out.none=[$q("#helpResults .hp-none")&&$q("#helpResults .hp-none").textContent,!!$q("#helpAsk"),$q("#helpPane").hidden];
          $q("#helpAsk").click(); await wait(80); out.ask=[$q("#chat").classList.contains("on"),$q("#chIn").value,$q("#helpQ").value];
          closeChat();
          type("hand over"); $q("#helpResults a.hp-r").click(); await wait(80);
          out.open=[location.hash,$q("#helpResults").hidden,$q("#helpPane").hidden,$q("#helpQ").value];
          window.OUT=out;""")
        self.assertFalse(o["word"][0])
        self.assertTrue(o["word"][1])
        self.assertIn("#help-howto-hand-over-someones-work", o["word"][2])
        self.assertEqual(o["word"][3][0], "How do I…")                                  # groups by part, how-tos first
        self.assertTrue(o["word"][4])                                                   # the matching word is marked
        self.assertEqual(o["first"], "Hand over someone's work")
        self.assertEqual(o["plural"], [True, True])
        self.assertTrue(o["case"] and o["accent"] and o["prefix"])
        self.assertTrue(o["refWord"] and o["howWord"])
        self.assertIn("Nothing in Help for “zzqxv”", o["none"][0])
        self.assertEqual(o["none"][1:], [True, True])
        self.assertEqual(o["ask"], [True, "zzqxv", ""])                                 # opens ask creaite with the words, no answer
        self.assertTrue(o["open"][0].startswith("#help-howto-"))
        self.assertEqual(o["open"][1:], [True, False, ""])

    def test_a_one_letter_word_does_not_stop_a_search(self):
        o = self.probe("""
          const n=q=>helpFind(q).length;
          out.n={undo:n("undo a mistake"),add:n("add a project"),plan:n("plan a meeting"),vip:n("what is a vip"),plain:n("undo mistake"),only:n("a"),mark:helpMark("Undo a mistake now","undo a mistake")};
          out.top=helpFind("undo a mistake").slice(0,3).map(r=>r.e.target);
          window.OUT=out;""")
        for k in ("undo", "add", "plan", "vip", "plain"):
            self.assertGreater(o["n"][k], 0, k)
        self.assertEqual(o["n"]["only"], 0)
        self.assertIn("howto-undo-a-mistake", o["top"])
        self.assertIn("<mark>Undo</mark>", o["n"]["mark"])

    def test_the_question_mark_does_nothing_while_a_dialog_is_open(self):
        o = self.probe("""
          go("review"); openCk(); const b=document.createElement("button"); $q("#cmdk").append(b); b.focus();
          b.dispatchEvent(new KeyboardEvent("keydown",{key:"?",bubbles:true,cancelable:true}));
          out.open=[$q("#cmdk").open,$q("#helpPanel").classList.contains("on"),VIEW];
          $q("#cmdk").close(); document.activeElement.blur(); key("?"); out.after=$q("#helpPanel").classList.contains("on");
          window.OUT=out;""")
        self.assertEqual(o["open"], [True, False, "review"])
        self.assertTrue(o["after"])

    def test_slash_focuses_the_search_in_help_and_is_ask_creaite_elsewhere(self):
        o = self.probe("""
          go("today"); key("/"); out.today=[$q("#chat").classList.contains("on"),document.activeElement.id==="helpQ"]; closeChat();
          go("help"); key("/"); out.help=[$q("#chat").classList.contains("on"),document.activeElement.id==="helpQ"];
          type("review"); key("Escape",$q("#helpQ")); out.esc=[$q("#helpQ").value,$q("#helpResults").hidden,$q("#helpPane").hidden];
          window.OUT=out;""")
        self.assertEqual(o["today"], [True, False])
        self.assertEqual(o["help"], [False, True])
        self.assertEqual(o["esc"], ["", True, False])

    def test_cmdk_lists_how_tos_by_title_and_the_best_three_by_line(self):
        o = self.probe("""
          const help=q=>ckItems(q).filter(i=>i.g==="Help");
          out.title=help("hand over someone").map(i=>[i.l,i.h]).slice(0,1);
          const lines=help("approve").filter(i=>i.h.includes("›"));
          out.lines=[lines.length>0,lines.length<=3,lines.every(i=>i.l.startsWith("Help: ")),help("approve").length];
          out.notitle=help("zzqxv").length;
          const sameIndex=ckItems("approve").some(i=>i.g==="Help");
          out.same=sameIndex;
          const it=lines[0]; it.fn(); await wait(60); out.went=[VIEW,HELPARG===it.l];
          window.OUT=out;""")
        self.assertEqual(o["title"], [["Help: Hand over someone's work", "How do I…"]])
        self.assertTrue(o["lines"][0] and o["lines"][1] and o["lines"][2])
        self.assertEqual(o["notitle"], 0)
        self.assertEqual(o["went"][0], "help")

    def test_the_jobs_grid_and_every_screen_id_resolve_in_the_page(self):
        o = self.probe("""
          go("help","start"); const jobs=$a("#helpPane .hp-job").map(a=>a.dataset.help);
          out.jobs=[jobs.length,jobs.every(j=>helpNorm(j)===j)];
          const bad=[]; for(const j of jobs){ helpGo(j); if(!$q("#ht-"+j.slice(6))) bad.push(j); }
          for(const [k,s] of Object.entries(HD.screens)){ for(const id of s.ids){ helpGo("howto-"+id); if(!$q("#ht-"+id)) bad.push(k+":"+id); } helpGo("reference-"+s.ref); if(!$q("#hr-"+s.ref)) bad.push(k+":ref:"+s.ref); }
          out.bad=bad; out.screens=Object.keys(HD.screens);
          window.OUT=out;""")
        self.assertEqual(o["jobs"], [12, True])
        self.assertEqual(o["bad"], [])
        self.assertEqual(o["screens"], SCREENS)

    def test_the_question_mark_panel_opens_closes_with_esc_and_never_sits_with_ask_creaite(self):
        o = self.probe("""
          go("review"); const btn=$q("#themeBtn"); btn.focus(); key("?");
          const p=$q("#helpPanel");
          out.open=[p.classList.contains("on"),p.textContent.includes("Help · Review"),$a("#helpPanel .hpn-jobs li").length,!!$q("#helpPanel [data-hpn^=reference]"),!!$q("#hpnFind"),VIEW];
          openChat(); out.exclusive=[p.classList.contains("on"),$q("#chat").classList.contains("on")];
          key("?"); out.back=[p.classList.contains("on"),$q("#chat").classList.contains("on")];
          key("Escape"); out.esc=[p.classList.contains("on"),$q("#chat").classList.contains("on")]; btn.focus(); await wait(10);
          key("?"); key("Escape"); out.focus=[p.classList.contains("on"),document.activeElement===btn];
          key("?"); $q("#helpPanel [data-hpn]").click(); out.link=[p.classList.contains("on"),VIEW,HELPARG.startsWith("howto-")];
          key("?"); out.helpView=[VIEW,p.classList.contains("on")];
          go("settings"); key("?"); out.noList=[VIEW,p.classList.contains("on")];
          go("work"); key("?"); $q("#hpnFind").click(); await wait(30); out.find=[VIEW,document.activeElement.id,p.classList.contains("on")];
          window.OUT=out;""")
        self.assertEqual(o["open"], [True, True, 2, True, True, "review"])
        self.assertEqual(o["exclusive"], [False, True])                                 # ask creaite closes the panel
        self.assertEqual(o["back"], [True, False])                                      # and the panel closes ask creaite
        self.assertEqual(o["esc"], [False, False])
        self.assertEqual(o["focus"], [False, True])                                     # Esc puts the focus back
        self.assertEqual(o["link"], [False, "help", True])
        self.assertEqual(o["helpView"], ["help", False])
        self.assertEqual(o["noList"], ["help", False])                                  # no list: Help, on the tab used last
        self.assertEqual(o["find"], ["help", "helpQ", False])

    def test_the_foot_line_is_on_the_eight_screens(self):
        o = self.probe("""
          const names={today:"Today",work:"Work",review:"Review",projects:"Projects",people:"People",notes:"Notes",intake:"Intake",files:"Files"};
          const view={today:["today"],work:["work"],review:["review"],projects:["projects"],people:["people"],notes:["notes",P[0].code],intake:["inbox"],files:["files"]};
          const res={};
          for(const k of Object.keys(names)){ go(...view[k]); await wait(20); helpScreenSync(); const f=$q("#hFoot");
            res[k]=[f.hidden,f.textContent.trim(),f.closest(".view")&&f.closest(".view").id]; }
          go("activity"); helpScreenSync(); res.activity=$q("#hFoot").hidden;
          out.res=res; window.OUT=out;""")
        names = {"today": "Today", "work": "Work", "review": "Review", "projects": "Projects", "people": "People",
                 "notes": "Notes", "intake": "Intake", "files": "Files"}
        for k, n in names.items():
            self.assertEqual(o["res"][k][:2], [False, f"Press ? for help with {n}"], k)
        self.assertTrue(o["res"]["activity"])

    def test_the_empty_state_links_to_how_the_screen_works(self):
        o = self.probe("""
          out.link=howLink("review"); go("review"); await wait(20);
          const a=document.createElement("a"); a.innerHTML=out.link; document.body.append(a); a.firstElementChild.click(); await wait(30);
          out.went=[VIEW,HELPARG];
          window.OUT=out;""")
        self.assertIn("How Review works", o["link"])
        self.assertEqual(o["went"], ["help", "reference-review"])

    def test_the_first_visit_line(self):
        o = self.probe("""
          const line=()=>$q("#hFirst"), shown=()=>!line().hidden, seen=[];
          try{ [...Object.keys(localStorage)].filter(k=>k.startsWith("creaite-help-line-")).forEach(k=>localStorage.removeItem(k)); }catch(e){}
          S.helpLine=true;
          go("today"); await wait(20); helpScreenSync();
          out.today=[shown(),line().previousElementSibling&&line().previousElementSibling.id,line().textContent.trim()];
          // a key clears it and is not eaten: a later listener still sees it, undefaulted
          let got=null; const l=e=>{ got=[e.key,e.defaultPrevented]; }; document.addEventListener("keydown",l);
          document.dispatchEvent(new KeyboardEvent("keydown",{key:"x",bubbles:true,cancelable:true})); document.removeEventListener("keydown",l);
          out.keyAtOnce=shown(); await wait(20); out.key=[shown(),got];   /* the key does its job first, then the line goes */
          go("review"); helpScreenSync(); out.review=shown();
          // a click clears it, and the click still reaches its target
          let clicked=0; const b=$q("#themeBtn"); const h=()=>clicked++; b.addEventListener("click",h);
          b.dispatchEvent(new PointerEvent("pointerdown",{bubbles:true})); out.downKeeps=shown(); b.click(); out.clickAtOnce=shown(); await wait(20); b.removeEventListener("click",h); out.click=[shown(),clicked];
          go("today"); helpScreenSync(); out.once=shown();
          go("work"); helpScreenSync(); out.work=shown();
          // not over an open item, a dialog, ask creaite, the ? panel, or while typing; it waits
          $q("#panel").classList.add("on"); helpScreenSync(); out.item=!shown(); $q("#panel").classList.remove("on"); helpScreenSync(); out.itemAfter=shown();
          go("files"); helpScreenSync(); out.files=shown(); openCk(); helpScreenSync(); out.dlg=[document.querySelector("dialog[open]")!=null,!shown()];
          $q("#cmdk").close(); document.activeElement.blur(); helpScreenSync(); out.dlgAfter=shown();
          go("people"); helpScreenSync(); out.people=shown(); openChat(); helpScreenSync(); out.chat=!shown(); closeChat(); helpScreenSync(); out.chatAfter=shown();
          go("projects"); helpScreenSync(); out.proj=shown(); openHelpPanel("projects"); helpScreenSync(); out.hp=!shown(); closeHelpPanel(); helpScreenSync(); out.hpAfter=shown();
          go("inbox"); helpScreenSync(); out.intake=shown(); const q=document.createElement("input"); document.body.append(q); q.focus(); helpScreenSync(); out.typing=!shown(); q.blur(); q.remove(); helpScreenSync(); out.typingAfter=shown();
          window.OUT=out;""")
        self.assertEqual(o["today"], [True, "dayHead", "Press ? for help with Today"])
        self.assertTrue(o["keyAtOnce"])
        self.assertEqual(o["key"], [False, ["x", False]])
        self.assertTrue(o["downKeeps"] and o["clickAtOnce"])                           # nothing moves under a press
        self.assertTrue(o["review"])                                                  # once per screen, not once overall
        self.assertEqual(o["click"], [False, 1])
        self.assertFalse(o["once"])
        self.assertTrue(o["work"])
        self.assertTrue(o["item"] and o["itemAfter"])
        self.assertTrue(o["files"])
        self.assertEqual(o["dlg"], [True, True])
        self.assertTrue(o["dlgAfter"])
        self.assertTrue(o["people"] and o["chat"] and o["chatAfter"])
        self.assertTrue(o["proj"] and o["hp"])
        self.assertFalse(o["hpAfter"])                                                # opening the panel is using the line: it stays cleared
        self.assertTrue(o["intake"] and o["typing"] and o["typingAfter"])

    def test_the_question_mark_clears_the_line_and_opens_the_panel(self):
        o = self.probe("""
          try{ localStorage.removeItem("creaite-help-line-review"); }catch(e){}
          S.helpLine=true; go("review"); helpScreenSync(); out.before=!$q("#hFirst").hidden;
          key("?"); helpScreenSync(); out.after=[$q("#hFirst").hidden,$q("#helpPanel").classList.contains("on")];
          closeHelpPanel(); helpScreenSync(); out.later=$q("#hFirst").hidden;
          window.OUT=out;""")
        self.assertTrue(o["before"])
        self.assertEqual(o["after"], [True, True])
        self.assertTrue(o["later"])

    def test_storage_failure_means_once_per_page_load_and_the_setting_turns_it_off(self):
        o = self.probe("""
          Storage.prototype.setItem=function(){ throw new Error("full"); }; Storage.prototype.getItem=function(){ throw new Error("blocked"); };
          S.helpLine=true; go("today"); helpScreenSync(); out.first=!$q("#hFirst").hidden;
          document.dispatchEvent(new KeyboardEvent("keydown",{key:"x",bubbles:true})); await wait(20); go("review"); go("today"); helpScreenSync(); out.again=!$q("#hFirst").hidden;
          S.helpLine=false; go("work"); helpScreenSync(); out.off=$q("#hFirst").hidden; out.footStays=!$q("#hFoot").hidden;
          const st=getComputedStyle($q("#hFirst")); out.anim=[st.animationName,st.transitionDuration];
          window.OUT=out;""")
        self.assertTrue(o["first"])
        self.assertFalse(o["again"])
        self.assertTrue(o["off"] and o["footStays"])
        self.assertEqual(o["anim"], ["none", "0s"])

    def test_whats_new_tab_shows_the_plain_notes_newest_first_and_has_no_dot(self):
        o = self.probe("""
          go("help"); const tabs=$a("#helpTabs button").map(b=>b.textContent);
          helpGo("whatsnew"); await wait(30);
          const vs=$a("#helpPane .hp-new").map(a=>a.dataset.ver);
          out.tab=[tabs,location.hash,vs.length,vs[0],$a("#helpPane .hp-new h2")[0].textContent,$a("#helpPane .hp-new li").length>20,$a("#helpTabs .dot, #helpTabs [data-dot]").length];
          helpGo("whatsnew-2-1-0"); await wait(60); out.deep=[HELPARG,location.hash];
          type("weekly report"); out.search=helpFind("client report").some(r=>r.e.tab==="whatsnew");
          window.OUT=out;""")
        self.assertEqual(o["tab"][0], ["Start here", "How do I…", "Reference", "What’s new"])
        self.assertEqual(o["tab"][1], "#help-whatsnew")
        self.assertGreaterEqual(o["tab"][2], 21)
        newest = re.search(r"^## creaite (\d+\.\d+\.\d+)", (REPO / "system/templates/help/whats-new.md").read_text(encoding="utf-8"), re.M).group(1)
        self.assertEqual(o["tab"][3], newest)
        self.assertEqual(o["tab"][4], "creaite " + newest)
        self.assertTrue(o["tab"][5])
        self.assertEqual(o["tab"][6], 0)
        self.assertEqual(o["deep"], ["whatsnew-2-1-0", "#help-whatsnew-2-1-0"])
        self.assertTrue(o["search"])


class RealClickTests(LiveBrowserCase):
    """The first-visit line with real clicks (CDP): going to another screen shows that screen's line, not a cleared one."""
    shared_server = True
    width, height = 900, 900

    def line(self):
        self.b.pump(0.4)
        return self.b.eval("(()=>{ const l=document.getElementById('hFirst'); return [!l.hidden, l.dataset.k||'', "
                           "localStorage.getItem('creaite-help-line-work'), localStorage.getItem('creaite-help-line-today')]; })()")

    def test_a_rail_click_to_another_screen_shows_that_screens_line(self):
        b = self.b
        b.eval("S.helpLine=true; go('today')")
        b.pump(0.4)
        b.eval("localStorage.removeItem('creaite-help-line-today'); localStorage.removeItem('creaite-help-line-work'); helpScreenSync()")
        self.assertEqual(self.line()[:2], [True, "today"])
        b.click(".rail #railMain [data-v=work]")
        shown, key, work, today = self.line()
        self.assertEqual((shown, key), (True, "work"))                                  # Work's line is up and not yet marked seen
        self.assertIsNone(work)
        self.assertEqual(today, "1")                                                    # Today's was cleared by the click
        b.click("#v-work h1")                                                            # a click on the page clears Work's
        self.assertEqual(self.line()[:3], [False, "work", "1"])


if __name__ == "__main__":
    unittest.main()
