"""The Settings page (BL-115, sprint-settings): categories on the left, the settings on the right, one list of sections.
BL-320 (v1.9.2): four categories; test_settings_calmer.py covers the new parts. v2.6 (#246, Alan 19-10-2026): eight tabs
(Essentials, Work and reports, Sweep and Intake, Reports and minutes, AI drafts, Look and help, Advanced with five sub-tabs,
Health). People and projects has left Settings (the Settings line): its old addresses open the People page, the Projects
page or the project's settings page.

Run: python3 dev/tests/test_settings_page.py   (needs Google Chrome; skipped otherwise)

The real live server in a throwaway vault with fictional data, and the real dashboard in headless Chrome.
"""
import json
import os
import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES, TEST_PALETTES_JS, LiveBrowserCase  # noqa: E402
from test_dashboard import now, populate  # noqa: E402
from test_tracker import action  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import settings_catalogue  # noqa: E402

CATS = ["essentials", "work", "sweep", "reports", "ai", "look", "advanced", "health"]
SUBS = ["review", "state", "arch", "folders", "server"]
ADVANCED = ["thresholds", "warnings", "more-review"]              # Advanced opens on Review and warnings
WANT = {"essentials": ["essentials"], "work": ["views", "board", "projpage", "files", "more-work"],
        "sweep": ["transcripts", "sweep", "more-sweep", "closeday"], "reports": ["more-reports", "reminders"], "ai": ["drafts", "more-ai"],
        "look": ["appearance", "help", "more-look"], "advanced": ADVANCED,
        "health": ["health", "more-health", "live", "setup", "diag", "version", "danger"],
        "state": ["more-state"], "arch": ["more-arch"], "folders": ["more-folders"], "server": ["more-server"]}
PAGES = CATS + SUBS[1:]                                         # every tab and every other Advanced sub-tab


def server_day():
    """The live server's day: CREAITE_NOW when it is set (the server reads it too), else the machine's."""
    return now().date().isoformat()


class SettingsPage(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        # The Week ahead runs from the server's day to a Friday; populate's dates (3 and 5 days on) both miss it on a
        # Wednesday, so "every priority" listed nothing more than "Urgent only" did (14-10-2026). A Medium action due
        # on the server's own day is always in it: on that day, or on the Monday when the day is a weekend. It is due the NEXT
        # day, not the same one: a run that crosses midnight (CI, Saturday 23:59 to Sunday 00:00, 18-10-2026) otherwise
        # reads the Week ahead a day after the seed, when the action is overdue and not listed (#112): "0 not greater than 0".
        day = server_day()
        due = (datetime.fromisoformat(day) + timedelta(days=1)).date().isoformat()
        v.propose("week", [action(1, description="Confirm the UAT room", priority="Medium", due_date=due, raised=day)])
        v.run("apply")

    def setUp(self):
        super().setUp()
        self.b.eval("window.__errs=[]; addEventListener('error',e=>__errs.push(e.message)); addEventListener('unhandledrejection',e=>__errs.push(String(e.reason)))")

    def open(self, cat="essentials"):
        """A tab, or an Advanced sub-tab by its id."""
        tab = "advanced" if cat in SUBS else cat
        self.b.eval(f"STAB={cat!r}; go('settings')")
        self.b.wait(f"VIEW==='settings' && !!document.querySelector('#settingsBody [data-sec]') && document.querySelector('#setcats [aria-selected=true]').dataset.scat==={tab!r}")
        if cat in SUBS:
            self.b.wait(f"SSUB==={cat!r} && document.querySelector('#subtabs [aria-selected=true]').dataset.ssub==={cat!r}")

    def sections(self):
        return self.b.eval("[...document.querySelectorAll('#settingsBody [data-sec]')].map(c=>c.dataset.sec)")

    def settings_file(self):
        return json.loads((self.v.root / "system" / "config" / "settings.json").read_text())

    def test_the_tabs_are_listed_on_the_left(self):          # v2.6 (#246): eight tabs, People and projects retired
        self.open()
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#setcats button')].map(b=>b.dataset.scat)"), CATS)
        self.assertEqual(self.b.eval("document.querySelectorAll('#setcats [aria-selected=true]').length"), 1)
        self.assertFalse(self.b.eval("!!document.getElementById('stabs')"))

    def test_each_category_shows_its_sections(self):
        for cat, secs in WANT.items():                                           # v2.6 (#246); BL-166: Set-up in Health
            self.open(cat)
            self.assertEqual(self.sections(), secs, cat)

    def test_advanced_has_five_sub_tabs_and_says_most_people_never_open_it(self):   # v2.6 (#246)
        self.open("advanced")
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#subtabs [role=tab]')].map(b=>b.textContent)"),
                         ["Review and warnings", "Current state", "Archiving and backups", "Folders and OneDrive", "Server, search and logs"])
        self.assertIn("most people never open this", self.b.eval("document.querySelector('#settingsBody .advnote').textContent"))
        self.b.click("#subtabs [data-ssub=arch]")
        self.b.wait("SSUB==='arch' && location.hash==='#settings/arch' && !!document.querySelector('#settingsBody [data-more=\"Archiving and backups\"]')")
        keys = self.b.eval("[...document.querySelectorAll('#settingsBody .srow')].map(r=>r.dataset.keys)")
        self.assertIn("backups.daily_days", keys)                               # the retention, with archiving: one card
        self.assertIn("archive.after_months.actions", keys)
        self.assertEqual(self.b.eval("document.querySelectorAll('#settingsBody [data-more]').length"), 1)

    def test_the_old_people_and_projects_addresses_open_their_new_homes(self):   # the Settings line: the sections left Settings
        self.open("essentials")
        self.assertIn("People page", self.b.eval("document.getElementById('setMoved').textContent"))   # the side column says where
        self.assertFalse(self.b.eval("SETSECTIONS.some(s=>['people','workstreams','projects'].includes(s.id))"))
        self.assertFalse(self.b.eval("!!document.querySelector('#peopleMgr,#wsMgr,#projArch,#projSetList,#crSet')"))
        self.b.eval("go('settings','people')")                                  # People: the People page
        self.b.wait("VIEW==='people' && location.hash.startsWith('#people')")
        for old in ("projects", "admin"):                                       # Projects and register, and the old admin tab: Projects
            self.b.eval("go('today')")
            self.b.eval(f"go('settings','{old}')")
            self.b.wait("VIEW==='projects' && location.hash==='#projects'")
        self.b.eval("go('today'); go('settings','workstreams')")               # Workstreams with no project known: Projects
        self.b.wait("VIEW==='projects'")
        self.b.eval("go('cockpit','ABC'); go('settings','workstreams')")       # from a project: its settings, at Workstreams
        self.b.wait("VIEW==='psettings' && psCode.value==='ABC' && psCat.value==='ws' && location.hash.startsWith('#project-settings=ABC')")
        self.b.eval("STAB='people'; go('settings')")                            # an old name for a tab that is gone: Essentials
        self.b.wait("VIEW==='settings' && SCAT==='essentials'")

    def test_client_report_rhythms_are_no_longer_in_reminders(self):          # v2.6 (#246): each project's settings hold them
        self.open("reports")
        self.assertFalse(self.b.eval("!!document.querySelector('#settingsBody [data-rhythm]')"))
        self.assertTrue(self.b.eval("!!document.querySelector('[data-sec=reminders] [data-k=remindersOn]') && !!document.getElementById('remRestore')"))

    def test_sections_come_from_one_list_and_the_page_has_no_wrappers(self):
        # v2.6 (#246): 33: You and People I follow joined Essentials, Everything else became each tab's More, Help joined;
        # the Settings line: 30, #250 adds Transcripts: 31 (32 with line2's sign-in section, which this count had not caught up with), as People, Workstreams and Projects and register left for their own pages
        self.assertEqual(self.b.eval("SETSECTIONS.map(s=>s.id).length"), 32)
        self.assertTrue(self.b.eval("SETSECTIONS.every(s=>s.id && SETCATS.some(c=>c[0]===catOf(s)) && typeof s.kw==='string' && (typeof s.render==='function' || typeof s.mount==='function'))"))
        self.assertEqual(self.b.eval("renderSettings.toString().includes('const rs=')"), False)

    def test_the_old_tab_names_open_a_sensible_category(self):
        for old, cat in [("prefs", "essentials"), ("general", "look"), ("work", "work"), ("capture", "sweep"),
                         ("system", "health"), ("more", "advanced"), ("review", "advanced"), ("follow", "essentials")]:
            self.b.eval(f"STAB={old!r}; go('settings')")
            self.b.wait("VIEW==='settings'")
            self.assertEqual(self.b.eval("document.querySelector('#setcats [aria-selected=true]').dataset.scat"), cat, old)
        for old, view in [("admin", "projects"), ("people", "people"), ("projects", "projects"), ("workstreams", "projects")]:
            self.b.eval(f"go('today'); go('settings',{old!r})")                  # the Settings line: they left Settings for these pages
            self.b.wait(f"VIEW==={view!r}")

    def test_the_diagnostics_link_opens_system(self):
        self.b.eval("STAB='general'; go('settings')")
        self.b.eval("var a=document.createElement('a'); a.dataset.diag=''; document.body.appendChild(a); a.click(); a.remove()")
        self.b.wait("VIEW==='settings' && !!document.getElementById('diagCard')")

    def test_stop_the_live_server_is_the_last_thing_in_health(self):
        self.open("health")
        self.assertEqual(self.sections()[-1], "danger")
        self.assertTrue(self.b.eval("!!document.querySelector('#dangerCard #liveStop')"))
        self.assertFalse(self.b.eval("!!document.querySelector('#liveCard #liveStop')"))

    def test_a_setting_saves_to_the_same_key_with_a_backup_and_a_log_entry_and_says_saved(self):
        self.open("work")                                          # v2.6 (#246): Work board is on Work and reports
        before = len(list((self.v.root / "system" / "backups").glob("settings-*.json")))
        self.b.eval("const e=document.querySelector('[data-k=boardClosedDays]'); e.value='21'; e.dispatchEvent(new Event('change',{bubbles:true}))")
        end = time.time() + 8
        while time.time() < end and self.settings_file()["work"]["board"]["closed_days"] != 21:
            time.sleep(0.1)
        self.assertEqual(self.settings_file()["work"]["board"]["closed_days"], 21)
        self.assertGreater(len(list((self.v.root / "system" / "backups").glob("settings-*.json"))), before)
        logf = self.v.root / "system" / "config" / "settings-log.jsonl"
        while time.time() < end and '"work.board.closed_days"' not in (logf.read_text() if logf.exists() else ""):   # the log line follows the file write
            time.sleep(0.1)
        log = logf.read_text()
        self.assertIn('"work.board.closed_days"', log)
        self.b.wait("!!document.querySelector('#settingsBody .saved')")
        self.assertEqual(self.b.eval("document.querySelector('#settingsBody .saved').closest('.srow').textContent.includes('Board shows closed items')"), True)

    def test_two_saves_in_one_second_keep_both_backups_and_the_first_holds_the_original(self):   # BL-266
        self.open("advanced")
        backups = self.v.root / "system" / "backups"
        original = (self.v.root / "system" / "config" / "settings.json").read_text()
        before = set(backups.glob("settings-*.json"))
        ok = self.b.eval("""(async()=>{ const R=Date, t=R.now(); window.Date=class extends R{ constructor(...a){ super(...(a.length?a:[t])); } static now(){ return t; } };
          try{ return (await writeSettings({"work.board.closed_days":31})) && (await writeSettings({"work.board.closed_days":32})); } finally{ window.Date=R; } })()""")
        self.assertTrue(ok)
        new = sorted(set(backups.glob("settings-*.json")) - before, key=lambda f: f.stat().st_mtime_ns)   # written order; a pinned server clock gives other saves the same stamp, so the name does not order them
        self.assertEqual(len(new), 2, [f.name for f in new])
        if not os.environ.get("CREAITE_NOW"):      # a pinned server clock stamps every save alike and numbers them in its own order
            self.assertEqual(new[1].name, new[0].name[:-len(".json")] + "-2.json")   # one stamp: the second gets -2
        self.assertNotEqual(new[0].name, new[1].name)
        self.assertEqual(new[0].read_text(), original)                               # the version before the first save survives
        self.assertEqual(json.loads(new[1].read_text())["work"]["board"]["closed_days"], 31)
        self.assertEqual(self.settings_file()["work"]["board"]["closed_days"], 32)

    def test_an_essential_says_saved(self):                       # BL-320: Save my changes at once is an Essential now
        self.open("essentials")
        row = ("[...document.querySelectorAll('#set-essentials .srow')].find(r=>r.querySelector('span[id]').textContent==='Save my changes at once')")
        self.b.wait(f"!!{row}")
        for _ in range(2):                                         # off and back on: the sample vault is shared
            self.b.eval(f"(()=>{{ const e={row}.querySelector('input'); e.checked=!e.checked; e.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
            self.b.wait(f"!!{row}.querySelector('.saved')")
            self.b.wait(f"!{row}.querySelector('.saved')", timeout=6)

    def test_own_email_domains_save_as_a_list(self):              # v2.6 (#246): an Essentials row in You now
        self.open("essentials")
        dom = "document.querySelector('#set-essentials .srow[data-keys=\"identity.own_domains\"] input')"
        self.b.wait(f"!!{dom}")
        self.b.eval(f"const e={dom}; e.value=' Example.com, Corp.example '; e.dispatchEvent(new Event('change',{{bubbles:true}}))")
        self.assertTrue(self.wait_file(lambda c: c["identity"]["own_domains"] == ["example.com", "corp.example"]))   # the save has landed (40 s, #89)
        self.assertEqual(self.settings_file()["identity"]["own_domains"], ["example.com", "corp.example"])
        self.b.wait("JSON.stringify(S.ownDomains)===JSON.stringify(['example.com','corp.example'])", 30)   # and the page has taken it
        self.assertEqual(self.b.eval("S.ownDomains"), ["example.com", "corp.example"])

    # ===== BL-235 (fix-small-17): the Week ahead's priorities, as ticks =====
    WA = "[...document.querySelectorAll('#set-essentials .srow')].find(r=>r.querySelector('span[id]').textContent==='Week ahead shows')"

    def ticks(self):
        self.b.wait(f"!!{self.WA}")
        return self.b.eval(f"[...{self.WA}.querySelectorAll('input')].filter(b=>b.checked).map(b=>b.getAttribute('aria-label'))")

    def tick(self, prio, want):
        """Set one tick and wait until settings.json holds what the ticks show."""
        w = str(want).lower()
        self.b.wait(f"!!{self.WA}")
        self.b.eval(f"{{ const e={self.WA}.querySelector('input[aria-label={prio}]'); if(e.checked!=={w}){{ e.checked={w}; e.dispatchEvent(new Event('change',{{bubbles:true}})); }} }}")
        shown = self.ticks()
        self.assertEqual(self.saved_prios(shown), shown)
        want = json.dumps(json.dumps(shown, separators=(",", ":")))
        self.b.wait(f"JSON.stringify(S.weekPrios)==={want}")   # the page's handler has finished saving
        self.b.eval("window.__wr=0; reloadData().then(()=>{ window.__wr=1; })")         # and the data it reloads is the new
        self.b.wait("window.__wr===1")

    def saved_prios(self, want):
        end = time.time() + 8
        while time.time() < end and (self.settings_file().get("dashboard") or {}).get("week_ahead_priorities") != want:
            time.sleep(0.1)
        return (self.settings_file().get("dashboard") or {}).get("week_ahead_priorities")

    def test_week_ahead_ticks_save_reload_and_change_the_week_ahead_and_none_means_all(self):
        orig = list((self.settings_file().get("dashboard") or {}).get("week_ahead_priorities") or [])
        try:
            self.week_ahead_ticks()
        finally:
            self.open("essentials")
            for p in ("Urgent", "High", "Medium", "Low"):
                self.tick(p, p in orig)

    def week_ahead_ticks(self):
        b = self.b
        logf = self.v.root / "system" / "config" / "settings-log.jsonl"
        self.open("essentials")
        b.wait(f"!!{self.WA}")
        self.assertEqual(b.eval(f"[...{self.WA}.querySelectorAll('input')].map(x=>x.getAttribute('aria-label'))"), ["Urgent", "High", "Medium", "Low"])
        self.tick("Medium", not self.ticks().count("Medium"))       # one real change first: a missing key shows its default
        for p in ("Urgent", "High", "Medium", "Low"):
            self.tick(p, p == "Urgent")
        self.assertEqual(self.saved_prios(["Urgent"]), ["Urgent"])
        items = "[...(D.week&&D.week.days||[]),{items:(D.week&&D.week.further)||[]}].flatMap(d=>d.items||[]).length"
        b.wait("!!D.week")
        urgent_only = b.eval(items)
        before = len(list((self.v.root / "system" / "backups").glob("settings-*.json")))
        self.tick("High", True)
        self.assertEqual(self.saved_prios(["Urgent", "High"]), ["Urgent", "High"])          # saved in the page's order
        self.assertGreater(len(list((self.v.root / "system" / "backups").glob("settings-*.json"))), before)
        end = time.time() + 8
        while time.time() < end and '"dashboard.week_ahead_priorities"' not in (logf.read_text() if logf.exists() else ""):
            time.sleep(0.1)
        self.assertIn('"dashboard.week_ahead_priorities"', logf.read_text())
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        self.open("essentials")
        self.assertEqual(self.ticks(), ["Urgent", "High"])                                  # it reloads as saved
        self.tick("Urgent", False)
        self.tick("High", False)
        self.assertEqual(self.saved_prios([]), [])                                          # none ticked is saved as []
        self.assertGreater(b.eval(items), urgent_only)                                      # and the Week ahead lists every priority
        self.assertEqual(self.ticks(), [])
    # ===== end BL-235 =====

    def test_the_follow_switches_are_essentials_and_the_sweep_card_no_longer_holds_them(self):   # BL-320; v2.6: one card
        self.open("essentials")
        self.b.wait("!!document.querySelector('#set-essentials [data-ess=\"People I follow\"] .srow')")
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#set-essentials [data-ess=\"People I follow\"] .srow')].map(r=>r.dataset.keys)"),
                         ["vip.enabled", "vip.check_minutes", "vip.notify",     # the browser notification joined the first card
                          "vip.quiet_overnight vip.quiet_from vip.quiet_to", "vip.quiet_weekend"])   # #97: quiet hours
        self.assertFalse(self.b.eval("!!document.getElementById('vipSet')"))
        self.open("sweep")
        self.assertFalse(self.b.eval("!!document.querySelector('[data-sec=sweep] [data-vipk]')"))
        self.assertTrue(self.b.eval("!!document.querySelector('[data-sec=sweep] #ignMgr .iglist')"))

    # ---- addresses (item 3) ----
    def test_a_category_has_its_own_address(self):
        for cat in CATS:
            self.b.eval(f"go('settings',{cat!r})")
            self.b.wait(f"VIEW==='settings' && SCAT==={cat!r}")
            self.assertEqual(self.b.eval("location.hash"), f"#settings/{cat}")

    def test_typing_an_address_opens_it_and_a_section_address_scrolls_to_the_section(self):
        self.b.eval("location.hash='#settings/warnings'")
        self.b.wait("VIEW==='settings' && SCAT==='advanced' && !!document.getElementById('warnSettings')")
        self.b.eval("location.hash='#settings/diagnostics'")
        self.b.wait("SCAT==='health' && !!document.getElementById('diagCard')")
        self.b.eval("location.hash='#settings/sweep'")
        self.b.wait("SCAT==='sweep' && !!document.querySelector('[data-sec=sweep]')")

    def test_a_fresh_page_opens_the_category_in_its_address_and_a_bare_settings_address_still_works(self):
        self.b.goto(self.base + "/#settings/people")                           # the Settings line: a section that left opens its page
        self.b.wait("typeof go==='function' && LIVE && VIEW==='people' && location.hash.startsWith('#people')")
        self.b.goto(self.base + "/?fresh=0#settings/server")                    # an Advanced sub-tab's address
        self.b.wait("typeof go==='function' && LIVE && VIEW==='settings' && SCAT==='advanced' && SSUB==='server'")
        self.b.goto(self.base + "/?fresh=1#settings")
        self.b.wait("typeof go==='function' && LIVE && VIEW==='settings'")
        self.assertEqual(self.b.eval("SCAT"), "essentials")
        self.b.goto(self.base + "/?fresh=2#settings/nonsense")
        self.b.wait("typeof go==='function' && LIVE && VIEW==='settings'")
        self.assertEqual(self.b.eval("SCAT"), "essentials")

    def test_back_returns_to_the_previous_category(self):
        self.b.eval("go('settings','advanced')")
        self.b.eval("go('settings','health')")
        self.b.wait("SCAT==='health'")
        self.b.eval("history.back()")
        self.b.wait("SCAT==='advanced'")

    # ---- search ----
    def type_query(self, q):
        self.b.eval(f"(()=>{{ const q=document.getElementById('setq'); q.value={q!r}; q.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")

    def test_search_finds_sections_across_categories_and_shows_where_they_are(self):
        self.open("essentials")
        self.type_query("sweep")
        self.assertIn("sweep", self.sections())
        self.assertEqual(self.b.eval("document.querySelectorAll('#setcats [aria-selected=true]').length"), 0)
        self.assertEqual(self.b.eval("document.querySelector('[data-sec=sweep]').previousElementSibling.textContent"), "Mail, Teams and Intake › Checking mail and Teams")
        own = "[...document.querySelectorAll('[data-sec=sweep] .srow:not([hidden])')].filter(r=>!r.closest('.setembed'))"
        self.assertEqual(self.b.eval(f"{own}.length"), 3)
        self.b.wait("document.querySelectorAll('[data-sec=sweep] .setembed .srow').length>=2")   # the Sweep group's rows, one card

    def test_search_matches_help_text_and_shows_only_the_matching_rows(self):
        self.open("essentials")
        self.type_query("someone you follow closely")    # BL-288: the label no longer says VIP
        self.assertEqual(self.sections(), ["warnings"])
        self.assertEqual(self.b.eval("[...document.querySelectorAll('[data-sec=warnings] .srow')].filter(r=>!r.hidden).length"), 1)
        self.type_query("fresh item")                     # a row's help text, in Project page
        self.assertEqual(self.sections(), ["projpage"])
        self.assertEqual(self.b.eval("[...document.querySelectorAll('[data-sec=projpage] .srow')].filter(r=>!r.hidden).length"), 1)

    def test_a_keyword_match_shows_the_rows_that_match_or_the_whole_section(self):
        self.open("essentials")
        self.type_query("vip")                    # "vip" is a keyword of Early warnings; no row says it (BL-288), so the whole section shows
        self.assertIn("warnings", self.sections())
        self.assertEqual(self.b.eval("[...document.querySelectorAll('[data-sec=warnings] .srow')].filter(r=>r.hidden).length"), 0)
        self.type_query("people i follow")        # the follow section, in Essentials, matches by its title: every row shows
        self.b.wait("document.querySelectorAll('#set-essentials [data-ess=\"People I follow\"] .srow').length===5")   # #97: and the two quiet-hours rows
        self.assertIn("essentials", self.sections())
        self.type_query("what creaite skips")    # the What creaite skips row matches: it shows, with its rules; the sweep's other rows don't
        self.assertIn("sweep", self.sections())
        self.assertTrue(self.b.eval("document.querySelectorAll('[data-sec=sweep] .igrow').length > 0 && ![...document.querySelectorAll('[data-sec=sweep] .igrow')].some(r=>r.offsetParent===null)"))
        self.assertEqual(self.b.eval("[...document.querySelectorAll('[data-sec=sweep] .srow')].filter(r=>r.hidden&&!r.closest('.setembed')).length"), 2)
        self.type_query("diagnostics")            # a keyword-only or title match shows the whole section
        self.assertIn("diag", self.sections())
        self.assertEqual(self.b.eval("document.querySelectorAll('[data-sec=diag] .srow[hidden]').length"), 0)

    def test_search_takes_every_word_and_ignores_case(self):
        self.open("essentials")
        self.type_query("STALE days")
        self.assertEqual(self.sections(), ["thresholds"])
        self.type_query("stale zebra")
        self.assertEqual(self.sections(), [])

    def test_no_match_says_so_and_clearing_goes_back_to_the_category(self):
        self.open("advanced")
        self.type_query("zzzqqq")
        self.assertIn("No settings match", self.b.eval("document.querySelector('#settingsBody .setnone').textContent"))
        self.b.eval("document.getElementById('setq').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
        self.b.wait("SQ===''")
        self.assertEqual(self.sections(), ADVANCED)
        self.assertEqual(self.b.eval("document.getElementById('setq').value"), "")

    def test_choosing_a_category_ends_the_search(self):
        self.open("essentials")
        self.type_query("vip")
        self.b.click("#setcats [data-scat=health]")
        self.b.wait("SCAT==='health' && SQ===''")
        self.assertEqual(self.b.eval("document.getElementById('setq').value"), "")

    def test_a_saved_row_in_search_results_still_saves_the_same_key(self):
        self.open("essentials")
        self.type_query("flow looks back")
        self.b.eval("const e=document.querySelector('[data-k=flowWeeks]'); e.value='12'; e.dispatchEvent(new Event('change',{bubbles:true}))")
        end = time.time() + 8
        while time.time() < end and self.settings_file()["dashboard"]["flow_weeks"] != 12:
            time.sleep(0.1)
        self.assertEqual(self.settings_file()["dashboard"]["flow_weeks"], 12)

    # ---- narrow windows and themes ----
    def test_under_700px_the_category_list_becomes_a_drop_down_above_the_settings(self):
        self.open("essentials")
        self.assertEqual(self.b.eval("getComputedStyle(document.getElementById('setcatsel')).display"), "none")
        self.b.resize(600, 900)
        self.b.wait("getComputedStyle(document.getElementById('setcats')).display==='none'")
        self.assertNotEqual(self.b.eval("getComputedStyle(document.getElementById('setcatsel')).display"), "none")
        sel, body = (self.b.eval(f"document.querySelector({q!r}).getBoundingClientRect().top") for q in ("#setcatsel", "#settingsBody"))
        self.assertLess(sel, body)
        self.assertLessEqual(self.b.eval("document.documentElement.scrollWidth"), 600)
        self.b.eval("const s=document.getElementById('setcatsel'); s.value='health'; s.dispatchEvent(new Event('change',{bubbles:true}))")
        self.b.wait("SCAT==='health'")
        self.assertEqual(self.b.eval("document.getElementById('setcatsel').value"), "health")

    def test_every_theme_in_light_and_dark_keeps_the_category_list_and_search_readable(self):
        js = """(()=>{ const lum=c=>{ const m=c.match(/[\\d.]+/g).map(Number); const f=v=>{ v/=255; return v<=0.03928?v/12.92:((v+0.055)/1.055)**2.4; }; return 0.2126*f(m[0])+0.7152*f(m[1])+0.0722*f(m[2]); };
          const ratio=(a,b)=>{ const x=lum(a),y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
          const bg=getComputedStyle(document.body).backgroundColor, out=[];
          for(const t of THEMES.filter(t=>TEST_PALETTES.includes(t.id))) for(const mode of ["Light","Dark"]){ S.palette=t.id; S.theme=mode; applyTheme(); renderSettings();
            const sel=document.querySelector("#setcats [aria-selected=true]"), idle=document.querySelector("#setcats [aria-selected=false]"), q=document.getElementById("setq");
            const cs=getComputedStyle(sel), ci=getComputedStyle(idle), cq=getComputedStyle(q), page=getComputedStyle(document.body).backgroundColor;
            out.push([t.id,mode,Math.round(ratio(ci.color,page)*10)/10,Math.round(ratio(cs.color,cs.backgroundColor==="rgba(0, 0, 0, 0)"?page:cs.backgroundColor)*10)/10,Math.round(ratio(cq.color,cq.backgroundColor)*10)/10,cs.borderLeftColor,page]); }
          return out; })()""".replace("TEST_PALETTES", TEST_PALETTES_JS)
        self.open("essentials")
        rows = self.b.eval(js)
        self.assertEqual(len(rows), len(TEST_PALETTES) * 2)               # every tested theme (creaite, Cursor), light and dark
        for theme, mode, idle, selected, query, border, page in rows:
            self.assertGreaterEqual(idle, 3.0, f"{theme} {mode}: an unselected category on the page")
            self.assertGreaterEqual(selected, 4.5, f"{theme} {mode}: the selected category")
            self.assertGreaterEqual(query, 4.5, f"{theme} {mode}: the search box")
            self.assertNotIn(border, ("rgba(0, 0, 0, 0)", "transparent", page), f"{theme} {mode}: the selected marker is visible")

    # ---- Advanced (item 4); since BL-320 the old card's settings are in the catalogue's rows; v2.6 (#246): each on its tab ----
    ADV_KEYS = ["assistant.run_timeout_minutes", "logging.max_mb", "logging.keep_days", "inbox.meetings_from", "dashboard.generate_days",
                "search.debounce_ms", "search.ask_budget_chars", "search.include_documents",
                "review.spot_check_every"]          # BL-208; day.close_from is an Essential since BL-320

    def more(self, key):
        return f"document.querySelector('#settingsBody .srow[data-keys=\"{key}\"]')"

    def open_key(self, key):
        """The tab (or Advanced sub-tab) the catalogue puts a setting on."""
        tab = settings_catalogue.tab_of(key)                                     # the server's catalogue says the same
        self.open(tab.split("/")[1] if tab.startswith("advanced/") else tab)
        self.b.wait(f"!!{self.more(key)}", 30)

    def adv_change(self, key, value):
        if not self.b.eval(f"!!{self.more(key)}"):
            self.open_key(key)
        self.b.wait(f"!!{self.more(key)}", 30)                                   # the row is drawn (a redraw after the last save can be late under load)
        js = (f"(()=>{{ const e={self.more(key)}.querySelector('input,select'); "
              + ("e.checked=%s;" % ("true" if value else "false") if isinstance(value, bool) else f"e.value={str(value)!r};")
              + " e.dispatchEvent(new Event('change',{bubbles:true})); })()")
        self.b.eval(js)

    def wait_file(self, test, timeout=40):
        end = time.time() + timeout
        while time.time() < end:
            if test(self.settings_file()):
                return True
            time.sleep(0.1)
        return False

    def open_more(self):
        self.open("server")
        self.b.wait("!!document.querySelector('#settingsBody [data-more] .srow')")

    def test_everything_else_holds_the_old_advanced_settings_with_their_current_values(self):
        cfg = self.settings_file()
        for k in self.ADV_KEYS:                                                  # each on its own tab now (v2.6, #246)
            self.open_key(k)
        self.open_key("logging.keep_days")
        self.assertEqual(self.b.eval(f"{self.more('logging.keep_days')}.querySelector('input').value"), str(cfg['logging']['keep_days']))
        self.assertEqual(self.b.eval(f"{self.more('search.include_documents')}.querySelector('input').checked"), cfg["search"]["include_documents"])
        self.open_key("review.spot_check_every")                                # inside Review and health: one Review card
        self.assertTrue(self.b.eval(f"!!{self.more('review.spot_check_every')}.closest('[data-sec=thresholds]')"))
        self.assertEqual(self.b.eval(f"{self.more('review.spot_check_every')}.querySelector('input').value"),
                         str(cfg.get("review", {}).get("spot_check_every", 10)))

    def test_advanced_never_offers_what_could_lock_alan_out(self):
        for page in PAGES:
            self.open(page)
            for key in settings_catalogue.FIXED:
                self.assertFalse(self.b.eval(f"!!document.querySelector('#settingsBody [data-keys=\"{key}\"] input,#settingsBody [data-keys=\"{key}\"] select,#settingsBody [data-keys=\"{key}\"] .setreset')"), key)
            self.assertNotIn("permission", self.b.eval("[...document.querySelectorAll('#settingsBody [data-more]')].map(c=>c.textContent).join(' ').toLowerCase()"))

    def test_an_advanced_change_writes_its_key_with_a_backup_and_a_log_entry(self):
        self.open_more()
        before = len(list((self.v.root / "system" / "backups").glob("settings-*.json")))
        self.adv_change("logging.keep_days", 10)
        self.assertTrue(self.wait_file(lambda c: c["logging"]["keep_days"] == 10))
        self.adv_change("search.include_documents", False)
        self.assertTrue(self.wait_file(lambda c: c["search"]["include_documents"] is False))
        self.adv_change("dashboard.generate_days", 14)
        self.assertTrue(self.wait_file(lambda c: c["dashboard"]["generate_days"] == 14))
        logf = self.v.root / "system" / "config" / "settings-log.jsonl"
        end = time.time() + 30                                                   # the backup and the log entry follow the file: wait for them
        while time.time() < end and not (len(list((self.v.root / "system" / "backups").glob("settings-*.json"))) > before
                                         and all(f'"{k}"' in (logf.read_text() if logf.exists() else "")
                                                 for k in ("logging.keep_days", "search.include_documents", "dashboard.generate_days"))):
            time.sleep(0.1)
        self.assertGreater(len(list((self.v.root / "system" / "backups").glob("settings-*.json"))), before)
        log = logf.read_text()
        for key in ("logging.keep_days", "search.include_documents", "dashboard.generate_days"):
            self.assertIn(f'"{key}"', log)
        self.b.wait("!!document.querySelector('#settingsBody [data-more] .saved')")
        for key, val in (("logging.keep_days", 7), ("search.include_documents", True), ("dashboard.generate_days", 7)):   # the vault is shared
            self.adv_change(key, val)                                            # opens the setting's tab when it isn't drawn
        self.assertTrue(self.wait_file(lambda c: c["logging"]["keep_days"] == 7 and c["search"]["include_documents"] is True
                                       and c["dashboard"]["generate_days"] == 7))

    def test_an_out_of_range_advanced_value_is_refused_and_the_file_is_untouched(self):
        self.open_more()
        keep = self.settings_file()["logging"]["keep_days"]
        self.adv_change("logging.keep_days", 500)
        self.adv_change("assistant.run_timeout_minutes", "abc")
        self.adv_change("inbox.meetings_from", "last week")
        time.sleep(0.8)
        cfg = self.settings_file()
        self.assertEqual(cfg["logging"]["keep_days"], keep)
        self.assertEqual(cfg["assistant"]["run_timeout_minutes"], 30)
        self.assertEqual(cfg["inbox"]["meetings_from"], "monday")
        self.open_key("logging.keep_days")                                       # v2.6 (#246): on Server, search and logs
        self.assertEqual(self.b.eval(f"{self.more('logging.keep_days')}.querySelector('input').value"), str(keep))

    def test_calendar_import_accepts_monday_or_a_number_of_days(self):
        self.open_more()
        self.adv_change("inbox.meetings_from", "10")
        self.assertTrue(self.wait_file(lambda c: c["inbox"]["meetings_from"] == 10))
        self.b.wait(f"{self.more('inbox.meetings_from')}.querySelector('input').value==='10'")
        self.adv_change("inbox.meetings_from", " Monday ")
        self.assertTrue(self.wait_file(lambda c: c["inbox"]["meetings_from"] == "monday"))

    def test_search_finds_a_row_in_everything_else(self):
        self.open("essentials")
        self.type_query("waits after typing")
        self.b.wait("!!document.querySelector('#set-more-server .srow')")
        self.assertEqual(self.sections(), ["more-server"])
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#set-more-server .srow')].map(r=>r.dataset.keys)"), ["search.debounce_ms"])
        self.assertEqual(self.b.eval("document.getElementById('set-more-server').previousElementSibling.textContent"),
                         "Advanced › Server, search and logs")                   # where it lives, v2.6 (#246)

    def test_search_finds_every_shown_setting_and_says_which_tab_it_is_on(self):   # v2.6 (#246)
        """Each catalogue row a card draws by its key (data-keys) is found by its own label, under its tab's name."""
        self.open("essentials")
        rows = [(r["key"], r["label"], r["tab"]) for r in settings_catalogue.catalogue(self.settings_file())["settings"] if r["tab"]]
        names = dict(self.b.eval("SETCATS"))
        names.update({f"advanced/{k}": f"Advanced › {v}" for k, v in self.b.eval("ADVSUBS")})
        find = """((key,ess)=>{ const has=x=>!x.hidden&&((x.dataset.keys||'').split(' ').includes(key)||rowKeys(x).includes(key));
          const all=[...document.querySelectorAll('#settingsBody .srow')].filter(has), r=all.find(x=>ess||!x.closest('#set-essentials'))||all[0];
          if(!r) return null; const c=r.closest('[data-sec]'), p=c&&c.previousElementSibling;
          return c.id==='set-essentials'?'Essentials':p&&p.classList.contains('setcrumb')?p.textContent:''; })"""
        checked, by_text = 0, []
        for key, label, tab in rows:
            if tab == "essentials" and key.startswith("drafting.") or key.startswith("dashboard.rail."):
                continue                                  # the rail's settings are its Customise dialog (Look and help › Appearance)
            self.type_query(label)
            got, end = None, time.time() + 15
            while time.time() < end and got is None:
                got = self.b.eval(f"{find}({key!r},{json.dumps(tab == 'essentials')})")
                if got is None:
                    time.sleep(0.1)
            if got is None:                               # a control no row names by key (the log level, the ignore rules)
                self.assertTrue(self.b.eval("document.querySelectorAll('#settingsBody .srow:not([hidden]),#settingsBody .igrow').length>0"), (key, label))
                by_text.append(key)
                continue
            checked += 1
            self.assertTrue(got.startswith(names[tab]), (key, got, tab))
        self.assertLessEqual(len(by_text), 4, by_text)
        self.assertGreater(checked, 40)

    # ---- every setting is in exactly one category ----
    # Each setting a row holds: an Essentials or Everything else row names its keys; an older card's control its short key.
    COLLECT = """(()=>{ const out=[]; document.querySelectorAll('#settingsBody [data-keys]').forEach(r=>r.dataset.keys.split(' ').forEach(k=>out.push(k)));
        document.querySelectorAll('#settingsBody [data-k],#settingsBody [data-wk],#settingsBody [data-vipk],#settingsBody [data-drsw],#settingsBody [data-setkey],#settingsBody #diagLevel').forEach(e=>{
        out.push(e.dataset.k?SKEY[e.dataset.k]:e.dataset.wk?'warnings.'+e.dataset.wk:e.dataset.vipk?'vip.'+e.dataset.vipk:e.dataset.drsw?'drafting.'+e.dataset.drsw:e.dataset.setkey?e.dataset.setkey:'logging.level'); }); return out; })()"""

    def test_every_setting_on_the_page_appears_in_exactly_one_category(self):
        seen = {}
        for cat in PAGES:                                               # v2.6 (#246): every tab and Advanced sub-tab
            self.open(cat)
            self.b.wait("document.querySelectorAll('#settingsBody [data-sec]').length>0")
            if cat in ("essentials", "state", "arch", "folders", "server"):
                self.b.wait("!!document.querySelector('#settingsBody [data-keys]')")
            for key in set(self.b.eval(self.COLLECT)):
                seen.setdefault(key, []).append(cat)
        # AI drafts: one switch in Essentials, each kind's own on the AI drafts tab (BL-320; v2.6)
        self.assertEqual({k: v for k, v in seen.items() if len(v) != 1 and not k.startswith("drafting.")}, {})
        for key in self.b.eval("Object.keys(SKEY)"):                    # every key the page saves has a home
            self.assertIn(self.b.eval(f"SKEY[{key!r}]"), seen, key)
        for sig in self.b.eval("WSIG.map(s=>s[0]+'.on')"):               # and every early warning
            self.assertIn("warnings." + sig, seen, sig)
        # every setting in the catalogue, except the three with a page of their own (the rail's Customise, the ignore
        # rules and Restore dismissed reminders), and the early warnings' numbers shown only while each is on
        quiet = ("dashboard.rail.", "sweep.ignore", "reminders.dismissed_forever", "warnings.",
                 # Legacy's old lists: kept (still read: the dashboard, propose.py, tracker.py migrate, doctor), shown nowhere (v2.6)
                 "people.added", "people.hidden", "workstreams.added", "workstreams.hidden")
        for key in settings_catalogue.flatten(settings_catalogue.defaults()):
            if not key.startswith(quiet):
                self.assertIn(key, seen, key)

    def test_every_section_has_one_id_one_category_and_keywords(self):
        ids = self.b.eval("SETSECTIONS.map(s=>s.id)")
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sorted(set(self.b.eval("SETSECTIONS.map(s=>catOf(s))"))), sorted(CATS))
        self.assertTrue(self.b.eval("SETSECTIONS.every(s=>s.kw.length>5 && s.title)"))
        # the page shows each section exactly once across the categories
        shown = []
        for cat in PAGES:
            self.open(cat)
            shown += self.sections()
        self.assertEqual(sorted(shown), sorted(ids))

    def test_the_word_label_setting_is_not_on_the_page(self):          # BL-121 removed it
        for cat in PAGES:
            self.open(cat)
            text = self.b.eval("document.getElementById('settingsBody').textContent.toLowerCase()")
            self.assertNotIn("sensitivity", text)
            self.assertNotIn("word label", text)

    def test_no_script_errors(self):
        for cat in PAGES:
            self.open(cat)
        self.assertEqual(self.b.eval("window.__errs||[]"), [])


if __name__ == "__main__":
    unittest.main()
