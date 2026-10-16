"""The Settings page (BL-115, sprint-settings): categories on the left, the settings on the right, one list of sections.
BL-320 (v1.9.2): four categories (Essentials, People and projects, Advanced, Health); test_settings_calmer.py covers the new parts.

Run: python3 dev/tests/test_settings_page.py   (needs Google Chrome; skipped otherwise)

The real live server in a throwaway vault with fictional data, and the real dashboard in headless Chrome.
"""
import json
import os
import re
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES, TEST_PALETTES_JS, LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import action  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import settings_catalogue  # noqa: E402

CATS = ["essentials", "people", "advanced", "health"]
ADVANCED = ["you", "appearance", "drafts", "closeday", "views", "board", "projpage", "files", "thresholds", "warnings", "sweep", "vip",
            "reminders", "more"]


def server_day():
    """The live server's day: CREAITE_NOW when it is set (the server reads it too), else the machine's."""
    fixed = os.environ.get("CREAITE_NOW")
    return (datetime.strptime(fixed, "%Y-%m-%d %H:%M") if fixed else datetime.now()).date().isoformat()


class SettingsPage(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        # The Week ahead runs from the server's day to a Friday; populate's dates (3 and 5 days on) both miss it on a
        # Wednesday, so "every priority" listed nothing more than "Urgent only" did (14-10-2026). A Medium action due
        # on the server's own day is always in it: on that day, or on the Monday when the day is a weekend.
        day = server_day()
        v.propose("week", [action(1, description="Confirm the UAT room", priority="Medium", due_date=day, raised=day)])
        v.run("apply")

    def setUp(self):
        super().setUp()
        self.b.eval("window.__errs=[]; addEventListener('error',e=>__errs.push(e.message)); addEventListener('unhandledrejection',e=>__errs.push(String(e.reason)))")

    def open(self, cat="essentials"):
        self.b.eval(f"STAB={cat!r}; go('settings')")
        self.b.wait(f"VIEW==='settings' && !!document.querySelector('#settingsBody [data-sec]') && document.querySelector('#setcats [aria-selected=true]').dataset.scat==={cat!r}")

    def sections(self):
        return self.b.eval("[...document.querySelectorAll('#settingsBody [data-sec]')].map(c=>c.dataset.sec)")

    def settings_file(self):
        return json.loads((self.v.root / "system" / "config" / "settings.json").read_text())

    def test_the_four_categories_are_listed_on_the_left(self):
        self.open()
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#setcats button')].map(b=>b.dataset.scat)"), CATS)
        self.assertEqual(self.b.eval("document.querySelectorAll('#setcats [aria-selected=true]').length"), 1)
        self.assertFalse(self.b.eval("!!document.getElementById('stabs')"))

    def test_each_category_shows_its_sections(self):
        want = {                                                                  # BL-320
            "essentials": ["essentials"],
            "people": ["people", "workstreams", "projects"],
            "advanced": ADVANCED,
            "health": ["health", "live", "setup", "diag", "version", "danger"],       # BL-166 (sprint-polish-2): Set-up
        }
        for cat, secs in want.items():
            self.open(cat)
            self.assertEqual(self.sections(), secs, cat)

    def test_sections_come_from_one_list_and_the_page_has_no_wrappers(self):
        self.assertEqual(self.b.eval("SETSECTIONS.map(s=>s.id).length"), 24)      # BL-320: Essentials, Health, Everything else in; Saving, Today, the old Advanced out; BL-295: Close the day
        self.assertTrue(self.b.eval("SETSECTIONS.every(s=>s.id && SETCATS.some(c=>c[0]===catOf(s)) && typeof s.kw==='string' && (typeof s.render==='function' || typeof s.mount==='function'))"))
        self.assertEqual(self.b.eval("renderSettings.toString().includes('const rs=')"), False)

    def test_the_old_tab_names_open_a_sensible_category(self):
        for old, cat in [("prefs", "essentials"), ("admin", "people"), ("people", "people"), ("projects", "people"),
                         ("general", "advanced"), ("work", "advanced"), ("capture", "advanced"), ("system", "health")]:
            self.b.eval(f"STAB={old!r}; go('settings')")
            self.b.wait("VIEW==='settings'")
            self.assertEqual(self.b.eval("document.querySelector('#setcats [aria-selected=true]').dataset.scat"), cat, old)

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
        self.open("advanced")
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
        new = sorted(set(backups.glob("settings-*.json")) - before, key=lambda f: (len(f.name), f.name))
        self.assertEqual(len(new), 2, [f.name for f in new])
        self.assertEqual(new[1].name, new[0].name[:-len(".json")] + "-2.json")       # one stamp: the second gets -2
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

    def test_own_email_domains_save_as_a_list(self):
        self.open("advanced")
        self.b.eval("const e=document.querySelector('[data-k=ownDomains]'); e.value=' Example.com, Corp.example '; e.dispatchEvent(new Event('change',{bubbles:true}))")
        end = time.time() + 8
        while time.time() < end and self.settings_file()["identity"]["own_domains"] != ["example.com", "corp.example"]:
            time.sleep(0.1)
        self.assertEqual(self.settings_file()["identity"]["own_domains"], ["example.com", "corp.example"])
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

    def test_the_follow_switches_are_essentials_and_the_sweep_card_no_longer_holds_them(self):   # BL-320
        self.open("advanced")
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#vipSet [data-vipk]')].map(e=>e.dataset.vipk)"), ["notify"])
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
        self.b.wait("SCAT==='advanced' && !!document.querySelector('[data-sec=sweep]')")

    def test_a_fresh_page_opens_the_category_in_its_address_and_a_bare_settings_address_still_works(self):
        self.b.goto(self.base + "/#settings/people")
        self.b.wait("typeof go==='function' && LIVE && VIEW==='settings' && SCAT==='people'")
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
        self.assertEqual(self.b.eval("document.querySelector('[data-sec=sweep]').previousElementSibling.textContent"), "Advanced › Sweep")
        self.assertEqual(self.b.eval("document.querySelectorAll('[data-sec=sweep] .srow:not([hidden])').length"), 3)

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
        self.type_query("people i follow")        # the follow section matches by its title: every row shows
        self.assertIn("vip", self.sections())
        self.assertEqual(self.b.eval("[...document.querySelectorAll('[data-sec=vip] .srow')].filter(r=>r.hidden).length"), 0)
        self.type_query("ignore rules")           # the Ignore rules row matches: it shows, with its rules; the sweep's other rows don't
        self.assertIn("sweep", self.sections())
        self.assertTrue(self.b.eval("document.querySelectorAll('[data-sec=sweep] .igrow').length > 0 && ![...document.querySelectorAll('[data-sec=sweep] .igrow')].some(r=>r.offsetParent===null)"))
        self.assertEqual(self.b.eval("[...document.querySelectorAll('[data-sec=sweep] .srow')].filter(r=>r.hidden).length"), 2)
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

    # ---- Advanced (item 4); since BL-320 the old card's settings are in Advanced › Everything else ----
    ADV_KEYS = ["assistant.run_timeout_minutes", "logging.max_mb", "logging.keep_days", "inbox.meetings_from", "dashboard.generate_days",
                "search.debounce_ms", "search.ask_budget_chars", "search.include_documents",
                "review.spot_check_every"]          # BL-208; day.close_from is an Essential since BL-320

    def more(self, key):
        return f"document.querySelector('#set-more .srow[data-keys=\"{key}\"]')"

    def adv_change(self, key, value):
        js = (f"(()=>{{ const e={self.more(key)}.querySelector('input,select'); "
              + ("e.checked=%s;" % ("true" if value else "false") if isinstance(value, bool) else f"e.value={str(value)!r};")
              + " e.dispatchEvent(new Event('change',{bubbles:true})); })()")
        self.b.eval(js)

    def wait_file(self, test, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            if test(self.settings_file()):
                return True
            time.sleep(0.1)
        return False

    def open_more(self):
        self.open("advanced")
        self.b.wait("!!document.querySelector('#set-more .srow')")

    def test_everything_else_holds_the_old_advanced_settings_with_their_current_values(self):
        cfg = self.settings_file()
        self.open_more()
        keys = self.b.eval("[...document.querySelectorAll('#set-more .srow')].map(r=>r.dataset.keys)")
        for k in self.ADV_KEYS:
            self.assertIn(k, keys)
        self.assertEqual(self.b.eval(f"{self.more('logging.keep_days')}.querySelector('input').value"), str(cfg['logging']['keep_days']))
        self.assertEqual(self.b.eval(f"{self.more('search.include_documents')}.querySelector('input').checked"), cfg["search"]["include_documents"])
        self.assertEqual(self.b.eval(f"{self.more('review.spot_check_every')}.querySelector('input').value"),
                         str(cfg.get("review", {}).get("spot_check_every", 10)))

    def test_advanced_never_offers_what_could_lock_alan_out(self):
        self.open_more()
        for key in settings_catalogue.FIXED:
            self.assertFalse(self.b.eval(f"!!document.querySelector('#settingsBody [data-keys=\"{key}\"] input,#settingsBody [data-keys=\"{key}\"] select,#settingsBody [data-keys=\"{key}\"] .setreset')"), key)
        self.assertNotIn("permission", self.b.eval("document.getElementById('set-more').textContent.toLowerCase()"))

    def test_an_advanced_change_writes_its_key_with_a_backup_and_a_log_entry(self):
        self.open_more()
        before = len(list((self.v.root / "system" / "backups").glob("settings-*.json")))
        self.adv_change("logging.keep_days", 10)
        self.assertTrue(self.wait_file(lambda c: c["logging"]["keep_days"] == 10))
        self.adv_change("search.include_documents", False)
        self.assertTrue(self.wait_file(lambda c: c["search"]["include_documents"] is False))
        self.adv_change("dashboard.generate_days", 14)
        self.assertTrue(self.wait_file(lambda c: c["dashboard"]["generate_days"] == 14))
        self.assertGreater(len(list((self.v.root / "system" / "backups").glob("settings-*.json"))), before)
        log = (self.v.root / "system" / "config" / "settings-log.jsonl").read_text()
        for key in ("logging.keep_days", "search.include_documents", "dashboard.generate_days"):
            self.assertIn(f'"{key}"', log)
        self.b.wait("!!document.querySelector('#set-more .saved')")
        for key, val in (("logging.keep_days", 7), ("search.include_documents", True), ("dashboard.generate_days", 7)):   # the vault is shared
            self.b.wait(f"!!{self.more(key)}")
            self.adv_change(key, val)
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
        self.b.wait("!!document.querySelector('#set-more .srow')")
        self.assertEqual(self.sections(), ["more"])
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#set-more .srow')].map(r=>r.dataset.keys)"), ["search.debounce_ms"])

    # ---- every setting is in exactly one category ----
    # Each setting a row holds: an Essentials or Everything else row names its keys; an older card's control its short key.
    COLLECT = """(()=>{ const out=[]; document.querySelectorAll('#settingsBody [data-keys]').forEach(r=>r.dataset.keys.split(' ').forEach(k=>out.push(k)));
        document.querySelectorAll('#settingsBody [data-k],#settingsBody [data-wk],#settingsBody [data-vipk],#settingsBody [data-rhythm],#settingsBody #diagLevel').forEach(e=>{
        out.push(e.dataset.k?SKEY[e.dataset.k]:e.dataset.wk?'warnings.'+e.dataset.wk:e.dataset.vipk?'vip.'+e.dataset.vipk:e.dataset.rhythm?'rhythm':'logging.level'); }); return out; })()"""

    def test_every_setting_on_the_page_appears_in_exactly_one_category(self):
        seen = {}
        for cat in CATS:
            self.open(cat)
            self.b.wait("document.querySelectorAll('#settingsBody [data-sec]').length>0")
            if cat in ("essentials", "advanced"):
                self.b.wait("!!document.querySelector('#settingsBody [data-keys]')")
            for key in set(self.b.eval(self.COLLECT)):
                seen.setdefault(key, []).append(cat)
        # AI drafts: one switch in Essentials, each kind's own in Advanced (BL-320)
        self.assertEqual({k: v for k, v in seen.items() if len(v) != 1 and not k.startswith("drafting.")}, {})
        for key in self.b.eval("Object.keys(SKEY)"):                    # every key the page saves has a home
            self.assertIn(self.b.eval(f"SKEY[{key!r}]"), seen, key)
        for sig in self.b.eval("WSIG.map(s=>s[0]+'.on')"):               # and every early warning
            self.assertIn("warnings." + sig, seen, sig)
        # every setting in the catalogue, except the three with a page of their own (the rail's Customise, the ignore
        # rules and Restore dismissed reminders), and the early warnings' numbers shown only while each is on
        quiet = ("dashboard.rail.", "sweep.ignore", "reminders.dismissed_forever", "warnings.")
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
        for cat in CATS:
            self.open(cat)
            shown += self.sections()
        self.assertEqual(sorted(shown), sorted(ids))

    def test_the_word_label_setting_is_not_on_the_page(self):          # BL-121 removed it
        for cat in CATS:
            self.open(cat)
            text = self.b.eval("document.getElementById('settingsBody').textContent.toLowerCase()")
            self.assertNotIn("sensitivity", text)
            self.assertNotIn("word label", text)

    def test_no_script_errors(self):
        for cat in CATS:
            self.open(cat)
        self.assertEqual(self.b.eval("window.__errs||[]"), [])


if __name__ == "__main__":
    unittest.main()
