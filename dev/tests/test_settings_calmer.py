"""BL-320 (v1.9.2): Settings, calmer, with Health inside: the page side.

Settings opens on Essentials (the catalogue's rows, each with its line), Advanced holds the rest (the older cards under their
old names, then every remaining setting from the catalogue), a dot marks what differs from its default, Reset puts one back (through /api/settings/reset), and Health lists only what needs Alan, each with its
manual step (a Fix it button only where the fix is marked built), the rest folded into one line.

Run: python3 dev/tests/test_settings_calmer.py   (needs Google Chrome; skipped otherwise)
The real live server in a throwaway vault with fictional data, and the real dashboard in headless Chrome.
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import settings_catalogue  # noqa: E402

ESS_SECTIONS = ["You", "Your day", "Saving and review", "People I follow", "Look and help", "Safety"]

# A health answer as /api/health gives it: one failure with a command to copy, one warning a person fixes, a stopped error.
HEALTH = {"ok": True, "checked": "2026-10-09 09:00", "fine": 22, "fine_names": ["Database", "Backups"], "read_only": True,
          "problems": [
              {"id": "launcher_vault", "title": "Your launcher opens another vault", "check": "Launcher", "severity": "fail",
               "detail": "~/Applications/creaite.app starts ~/dev.env/creaite", "fix": {"kind": "launcher", "button": "Fix it",
               "would_run": "system/scripts/run launch.py make-launcher --replace", "waits_for": "x",
               "how": "In Terminal: system/scripts/run launch.py make-launcher --replace", "built": False}},
              {"id": "online_only", "title": "Some project files are online-only", "check": "OneDrive", "severity": "warn",
               "detail": "3 files", "fix": {"kind": "manual", "button": "How to fix", "would_run": "", "waits_for": "", "how": "",
               "built": False}}],
          "stopped": [{"area": "apply", "count": 39, "span": "09-10 to 10-10", "message": "apply failed"}],
          "standalone": [{"id": "icon", "kind": "icon", "title": "Chrome's copy of the app shows an old icon", "button": "Fix it",
                          "does": "Point the app's manifest at new icon addresses.", "built": True, "how": "", "would_run": "", "waits_for": ""},
                         {"id": "m365", "kind": "m365", "title": "Microsoft 365 isn't connected", "button": "Open connector settings",
                          "does": "Open Claude's connector settings.", "built": True, "url": "https://claude.ai/settings/connectors",
                          "how": "", "would_run": "", "waits_for": ""}]}


def stub_health(b, answer, fixes=None):
    """Answer /api/health (and /api/health/fix/<id>, noting the address and body) with `answer` in this page, leaving every
    other call to the server; window.open is noted instead of opening."""
    b.eval(f"""(()=>{{ const real=window.api, ans={json.dumps(answer)}; window.__fix=[]; window.__opened=[]; window.open=(u)=>{{ __opened.push(u); }};
      window.api=async(p,body)=>{{ if(p==='/api/health') return JSON.parse(JSON.stringify(ans));
        if(p.startsWith('/api/health/fix/')){{ __fix.push([p, body===undefined?null:body]); const id=p.slice(16);
          if(id==='old_archive') return {{ok:true,fix:id,card:true,message:'Shown on the approval card in ask creaite: nothing moves until you approve it.'}};
          return id==='m365'?{{ok:true,fix:id,message:'Opening the connector page',url:'https://claude.ai/settings/connectors'}}:{{ok:true,fix:id,message:'Done'}}; }}
        return real(p,body); }}; }})()""")


class SettingsReading(LiveBrowserCase):
    shared_server = True        # these only read

    def setUp(self):
        super().setUp()
        self.b.eval("window.__errs=[]; addEventListener('error',e=>__errs.push(e.message)); addEventListener('unhandledrejection',e=>__errs.push(String(e.reason)))")

    def tearDown(self):
        if getattr(self, "b", None):
            self.assertEqual(self.b.eval("__errs"), [])
        super().tearDown()

    def open(self, cat=None):
        self.b.eval(f"go('settings'{',' + repr(cat) if cat else ''})")
        self.b.wait("VIEW==='settings' && !!document.querySelector('#settingsBody [data-sec]')")

    def test_settings_opens_on_essentials_with_the_catalogue_rows(self):
        self.open()
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#setcats button')].map(b=>b.dataset.scat)"),
                         ["essentials", "work", "sweep", "reports", "ai", "look", "advanced", "health"])   # v2.6 (#246): tabs
        self.assertEqual(self.b.eval("document.querySelector('#setcats [aria-selected=true]').dataset.scat"), "essentials")
        self.b.wait("document.querySelectorAll('#set-essentials .srow').length>0")
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#set-essentials [data-ess] h2')].map(h=>h.textContent)"), ESS_SECTIONS)
        labels = self.b.eval("[...document.querySelectorAll('#set-essentials .srow')].map(r=>r.querySelector('span[id]').textContent)")
        self.assertEqual(labels, [r[1] for r in settings_catalogue.ESSENTIAL_ROWS])
        self.assertTrue(14 <= len(labels) <= 24)                                     # #97: two quiet-hours rows
        lines = self.b.eval("[...document.querySelectorAll('#set-essentials .srow small')].map(s=>s.textContent)")
        self.assertEqual(lines, [r[2] for r in settings_catalogue.ESSENTIAL_ROWS])

    def test_every_essentials_control_is_named_by_its_row(self):
        self.open()
        self.b.wait("document.querySelectorAll('#set-essentials .srow').length>0")
        unnamed = self.b.eval("""[...document.querySelectorAll('#set-essentials input,#set-essentials select')].filter(e=>{
            const by=e.getAttribute('aria-labelledby'), l=e.getAttribute('aria-label'), wrap=e.closest('label');
            if(l) return false; if(wrap&&wrap.textContent.trim()) return false;
            return !(by&&document.getElementById(by)&&document.getElementById(by).textContent.trim()); }).map(e=>e.outerHTML)""")
        self.assertEqual(unnamed, [])
        groups = self.b.eval("[...document.querySelectorAll('#set-essentials [role=group]')].map(g=>document.getElementById(g.getAttribute('aria-labelledby')).textContent)")
        self.assertEqual(groups, ["Weekend", "What the sweep reads", "Week ahead shows"])

    def test_no_vip_label_on_the_following_settings(self):            # BL-288 (the early warning and ignore rules' words are BL-288's own)
        self.open("essentials")
        self.b.wait("document.querySelectorAll('#set-essentials .srow').length>3")
        self.assertNotIn("VIP", self.b.eval("document.getElementById('set-essentials').innerText"))
        self.open("follow")                                   # v2.6 (#246): the old address opens Essentials, one People I follow card
        self.b.wait("document.querySelectorAll('#set-essentials [data-ess=\"People I follow\"] .srow').length===5")   # #97: and two quiet-hours rows
        self.assertNotIn("VIP", self.b.eval("document.querySelector('#set-essentials [data-ess=\"People I follow\"]').innerText"))
        self.assertFalse(self.b.eval("!!document.getElementById('vipSet')"))

    def test_each_tab_draws_each_catalogue_group_once_and_the_old_headings_are_gone(self):   # v2.6 (#246)
        """The old Advanced (the older cards under their old names, then Everything else) is gone: each catalogue group is drawn
        once, inside the card of the same name (Sweep, Reminders, Close the day…) or as its own card on its tab."""
        cards = {}
        for page in ("work", "sweep", "reports", "ai", "look", "review", "state", "arch", "folders", "server", "health"):
            self.open(page)
            self.b.wait("document.querySelectorAll('#settingsBody .card>h2').length>0")
            self.b.pump(0.5)
            self.assertEqual(self.b.eval("document.querySelectorAll('#settingsBody .setgroup').length"), 0, page)
            for t in self.b.eval("[...document.querySelectorAll('#settingsBody .card>h2')].map(h=>h.textContent)"):
                cards.setdefault(t, []).append(page)
        self.assertEqual({t: p for t, p in cards.items() if len(p) != 1}, {}, "a title drawn twice")
        for gone in ("Everything else", "Legacy", "You and the look", "Capture and alerts", "Safety", "Archiving", "Work and views"):
            self.assertNotIn(gone, cards)
        self.open("sweep")
        self.assertTrue(self.b.eval("!!document.querySelector('#set-closeday [data-k=catchupAfter]')"))     # Close the day: one card
        self.b.wait("!!document.querySelector('#set-sweep .setembed .srow[data-keys=\"sweep.max_lookback_days\"]')")   # Sweep: one card
        self.assertTrue(self.b.eval("!!document.querySelector('#settingsBody [data-more=\"Meeting prep and Intake\"] .srow[data-keys=\"prep.series\"]')"))
        self.open("ai")
        self.b.wait("!!document.querySelector('#set-drafts .setembed .srow[data-keys=\"drafting.agenda_style\"]')")    # AI drafts: one card
        self.assertEqual(self.b.eval("document.querySelectorAll('#settingsBody .srow[data-keys^=\"drafting.\"]').length"), 1)
        self.open("look")
        self.b.wait("!!document.querySelector('#set-appearance .setembed .srow[data-keys=\"dashboard.rail_icon_size\"]')")
        self.assertTrue(self.b.eval("!!document.querySelector('#set-help #helpAgain')"))
        self.assertFalse(self.b.eval("!!document.querySelector('#settingsBody [data-keys=\"help.start_seen\"]')"))   # a button, not a switch
        self.open("folders")
        fixed = "document.querySelector('#settingsBody .srow[data-keys=\"locations.projects_root\"]')"
        self.b.wait(f"!!{fixed}")
        self.assertFalse(self.b.eval(f"!!{fixed}.querySelector('input,select,.setreset')"))
        self.assertIn("Set at set-up", self.b.eval(f"{fixed}.textContent"))
        for page in ("work", "sweep", "review"):
            self.open(page)
            self.assertFalse(self.b.eval("!!document.querySelector('#settingsBody [data-k=me],#settingsBody [data-k=sweepDue],#settingsBody [data-k=dailyBackup]')"))

    def test_search_finds_a_setting_by_its_words_or_its_old_key(self):
        self.open()
        for q in ("keep logs", "logging.keep_days"):
            self.b.eval(f"setSearch({q!r})")
            self.b.wait("!!document.querySelector('#set-more-server .srow')")
            self.assertEqual(self.b.eval("[...document.querySelectorAll('#set-more-server .srow')].map(r=>r.dataset.keys)"), ["logging.keep_days"], q)
        self.b.eval("setSearch('morning sweep')")
        self.b.wait("document.querySelectorAll('#set-essentials .srow').length===1")
        self.assertEqual(self.b.eval("document.querySelector('#set-essentials .srow span[id]').textContent"), "Morning sweep from")
        self.b.eval("setSearch('')")

    def test_old_addresses_still_open_their_card(self):
        for old, cat in [("general", "look"), ("work", "work"), ("system", "health"), ("prefs", "essentials"),   # v2.6 (#246)
                         ("sweep", "sweep"), ("diagnostics", "health"), ("warnings", "advanced"), ("capture", "sweep")]:
            self.b.eval(f"STAB={old!r}; go('settings')")
            self.b.wait(f"VIEW==='settings' && document.querySelector('#setcats [aria-selected=true]').dataset.scat==={cat!r}")

    def test_health_lists_problems_with_their_manual_step_and_folds_the_rest(self):
        stub_health(self.b, HEALTH)
        self.open("health")
        b = self.b
        b.wait("document.querySelectorAll('#healthCard .hlist .hrow:not([data-fix])').length===3")
        self.assertEqual(b.eval("[...document.querySelectorAll('#healthCard .hrow:not([data-fix]) .t')].map(t=>t.textContent.trim())"),
                         ["Your launcher opens another vault Needs fixing", "Some project files are online-only Worth a look", "Stopped: apply 39 ×"])
        self.assertEqual(b.eval("document.querySelector('#healthCard .hfine summary').textContent"), "22 checks fine")
        self.assertEqual(b.eval("document.querySelectorAll('#healthCard .hrow:not([data-fix]) .hact .btn.primary').length"), 0, "no Fix it on a problem whose fix isn't built")
        how = "document.querySelector('#healthCard .hrow[data-check=launcher_vault] .hact button')"
        self.assertEqual(b.eval(f"{how}.textContent"), "How to fix")
        self.assertEqual(b.eval(f"{how}.getAttribute('aria-expanded')"), "false")
        b.eval(f"{how}.focus()")
        b.key("Enter")
        b.wait(f"{how}.getAttribute('aria-expanded')==='true'")
        self.assertIn("make-launcher --replace", b.eval("document.querySelector('#hhow-launcher_vault').textContent"))
        self.assertEqual(b.eval("document.querySelector('#hhow-launcher_vault button').getAttribute('aria-label')"),
                         "Copy the command: system/scripts/run launch.py make-launcher --replace")
        b.eval("document.querySelector('#healthCard .hrow[data-check=online_only] .hact button').click()")
        b.wait("!!document.getElementById('hhow-online_only')")
        self.assertIn("Only you can take this step", b.eval("document.getElementById('hhow-online_only').textContent"))
        self.assertFalse(b.eval("!!document.querySelector('#hhow-online_only button')"), "nothing to copy")
        self.assertEqual(b.eval("JSON.parse(localStorage.getItem('creaite-health-count')).n"), 2)
        # the cards that were in System follow Health
        self.assertEqual(b.eval("[...document.querySelectorAll('#settingsBody [data-sec]')].map(c=>c.dataset.sec)"),
                         ["health", "more-health", "live", "setup", "diag", "version", "danger"])   # v2.6 (#246): Health check's Reset, under Health

    def test_a_built_fix_says_what_it_does_and_posts_its_own_route_with_nothing_else(self):
        ans = json.loads(json.dumps(HEALTH))
        ans["problems"][0]["fix"].update({"built": True, "id": "launcher", "button": "Fix it",
                                          "does": "Make this vault's launcher again in ~/Applications."})
        stub_health(self.b, ans)
        self.open("health")
        btn = "document.querySelector('#healthCard .hrow[data-check=launcher_vault] .btn.primary')"
        self.b.wait(f"!!{btn}")
        self.assertIn("Make this vault's launcher again", self.b.eval("document.querySelector('#healthCard .hrow[data-check=launcher_vault] .hdoes').textContent"))
        self.assertEqual(self.b.eval(f"{btn}.getAttribute('aria-label')"), "Fix it: Your launcher opens another vault")
        self.b.eval(f"{btn}.click()")
        self.b.wait("__fix.length===1")
        self.assertEqual(self.b.eval("__fix[0]"), ["/api/health/fix/launcher", None])     # the route names the fix; no body
        self.b.wait("document.getElementById('snackT').textContent==='Done'")

    def test_a_card_fix_says_it_is_waiting_on_the_approval_card_not_done(self):
        """#94: a fix that only raises the approval card (old_archive) is never "Done": the snack and the row say it waits for Alan,
        and the row keeps saying so until a check no longer reports the problem."""
        ans = json.loads(json.dumps(HEALTH))
        ans["problems"][0]["fix"].update({"built": True, "id": "old_archive", "button": "Fix it",
                                          "does": "Show the renames on the approval card."})
        stub_health(self.b, ans)
        self.open("health")
        row = "document.querySelector('#healthCard .hrow[data-check=launcher_vault]')"
        self.b.wait(f"!!{row}.querySelector('.btn.primary')")
        self.assertFalse(self.b.eval(f"!!{row}.querySelector('.hwait')"))
        self.b.eval(f"{row}.querySelector('.btn.primary').click()")
        self.b.wait("__fix.length===1")
        self.assertEqual(self.b.eval("__fix[0]"), ["/api/health/fix/old_archive", None])
        self.b.wait("document.getElementById('snackT').textContent.startsWith('On the approval card, waiting for you')")
        self.assertNotIn("Done", self.b.eval("document.getElementById('snackT').textContent"))
        self.b.wait(f"!!{row}.querySelector('.hwait')")
        self.assertEqual(self.b.eval(f"{row}.querySelector('.hwait').textContent"), "On the approval card, waiting for you.")
        # the check runs again after the click and still reports the problem: the row keeps saying so
        self.b.eval(f"{row}.closest('#healthCard').querySelector('#healthCheck').click()")
        self.b.wait("!document.getElementById('healthCheck').disabled")
        self.assertTrue(self.b.eval(f"!!{row}.querySelector('.hwait')"))
        # once the problem is gone from the check, nothing is left waiting
        ans["problems"] = []
        stub_health(self.b, ans)
        self.b.eval("document.getElementById('healthCheck').click()")
        self.b.wait("!document.querySelector('#healthCard .hwait') && !document.querySelector('#healthCard .hrow[data-check=launcher_vault]')")

    def test_the_standalone_fixes_and_microsoft_365_opens_its_page(self):
        stub_health(self.b, HEALTH)
        self.open("health")
        self.b.wait("document.querySelectorAll('#healthCard [data-fix]').length===2")
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#healthCard [data-fix]')].map(r=>r.dataset.fix)"), ["icon", "m365"])
        self.b.eval("document.querySelector('#healthCard [data-fix=m365] .btn').click()")
        self.b.wait("__opened.length===1")
        self.assertEqual(self.b.eval("__opened[0]"), "https://claude.ai/settings/connectors")
        self.assertEqual(self.b.eval("__fix"), [["/api/health/fix/m365", None]])
        self.assertIn("After every update", self.b.eval("document.getElementById('healthCard').textContent"))

    def test_the_real_health_check_answers(self):
        self.open("health")
        self.b.wait("!!document.querySelector('#healthCard .hsum,#healthCard .hbad')", timeout=120)
        self.assertTrue(self.b.eval("!!document.querySelector('#healthCard .hfine') || !!document.querySelector('#healthCard .hbad')"))


class SettingsChanging(LiveBrowserCase):
    """Each test changes settings.json, so each has its own vault."""

    def settings_file(self):
        return json.loads((self.v.root / "system" / "config" / "settings.json").read_text())

    def until(self, check, timeout=10):
        end = time.time() + timeout
        while time.time() < end and not check():
            time.sleep(0.1)
        self.assertTrue(check())

    def open(self, cat="essentials"):
        self.b.eval(f"go('settings',{cat!r})")
        self.b.wait("VIEW==='settings' && document.querySelectorAll('#settingsBody .srow').length>0")

    def ess_row(self, label):
        return (f"[...document.querySelectorAll('#set-essentials .srow')].find(r=>r.querySelector('span[id]').textContent==={label!r})")

    def test_an_essential_saves_shows_its_dot_and_resets(self):
        self.open()
        b, row = self.b, self.ess_row("Morning sweep from")
        self.assertFalse(b.eval(f"!!{row}.querySelector('.setdot')"))
        b.eval(f"(()=>{{ const i={row}.querySelector('input'); i.value='06:30'; i.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        self.until(lambda: self.settings_file()["sweep"]["due_from"] == "06:30")
        b.wait(f"!!{row}.querySelector('.setdot') && !!{row}.querySelector('.setreset')")
        self.assertEqual(b.eval(f"{row}.querySelector('.setreset').getAttribute('aria-label')"), "Reset Morning sweep from to its default")
        b.eval(f"{row}.querySelector('.setreset').click()")
        self.until(lambda: self.settings_file()["sweep"]["due_from"] == "07:00")
        b.wait(f"!{row}.querySelector('.setdot')")
        log = (self.v.root / "system" / "config" / "settings-log.jsonl").read_text()
        self.assertIn('"new":"06:30"', log)
        self.assertEqual(b.eval("S.sweepDue"), "07:00")

    def test_a_bad_time_is_refused_and_nothing_is_written(self):
        self.open()
        before = self.settings_file()
        self.b.eval(f"(()=>{{ const i={self.ess_row('Morning sweep from')}.querySelector('input'); i.value='7am'; i.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        self.b.wait("document.getElementById('snackT').textContent.includes('HH:MM')")
        time.sleep(0.5)
        self.assertEqual(self.settings_file(), before)

    def test_ai_drafts_is_one_switch_for_every_kind(self):
        self.open()
        row = self.ess_row("AI drafts")
        self.assertTrue(self.b.eval(f"{row}.querySelector('input').checked"))        # no drafting settings: every kind on
        self.b.eval(f"(()=>{{ const i={row}.querySelector('input'); i.checked=false; i.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        keys = settings_catalogue.ESSENTIAL_ROWS[[r[1] for r in settings_catalogue.ESSENTIAL_ROWS].index("AI drafts")][3]
        self.until(lambda: all(self.settings_file().get("drafting", {}).get(k.split(".")[1]) is False for k in keys))
        self.b.wait(f"!!{row}.querySelector('.setdot')")

    def test_show_the_first_run_help_again_sets_start_seen_back(self):          # v2.6 (#246)
        self.open("look")
        self.b.wait("!!document.getElementById('helpAgain')")
        self.b.click("#helpAgain")
        self.until(lambda: self.settings_file()["help"]["start_seen"] is False)
        self.b.wait("S.helpSeen===false")
        self.b.eval("writeSettings({'help.start_seen':true}).then(()=>{ S.helpSeen=true; })")   # the vault is shared
        self.until(lambda: self.settings_file()["help"]["start_seen"] is True)

    def test_reset_on_an_older_card_and_no_show_changed_only(self):
        """#102: the "Show changed only" switch is gone; the dot and Reset stay."""
        self.open("work")                                        # v2.6 (#246): the Work board card
        b = self.b
        self.assertEqual(b.eval("document.getElementById('setChanged')"), None)
        self.assertNotIn("Show changed only", b.eval("document.getElementById('v-settings').textContent"))
        b.eval("(()=>{ const e=document.querySelector('[data-k=boardClosedDays]'); e.value='21'; e.dispatchEvent(new Event('change',{bubbles:true})); })()")
        self.until(lambda: self.settings_file()["work"]["board"]["closed_days"] == 21)
        b.wait("!!document.querySelector('[data-k=boardClosedDays]').closest('.srow').querySelector('.setdot')")
        b.eval("document.querySelector('[data-k=boardClosedDays]').closest('.srow').querySelector('.setreset').click()")
        self.until(lambda: self.settings_file()["work"]["board"]["closed_days"] == 14)
        b.wait("!document.querySelector('[data-k=boardClosedDays]').closest('.srow').querySelector('.setdot')")
        self.assertEqual(b.eval("document.querySelector('[data-k=boardClosedDays]').value"), "14")

    def test_an_everything_else_setting_saves_with_its_limits(self):
        self.open("server")                                      # v2.6 (#246): Advanced › Server, search and logs
        b = self.b
        row = "document.querySelector('#set-more-server .srow[data-keys=\"logging.keep_days\"]')"
        b.wait(f"!!{row}")
        b.eval(f"(()=>{{ const i={row}.querySelector('input'); i.value='500'; i.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        b.wait("document.getElementById('snackT').textContent.includes('from 1 to 90')")
        b.eval(f"(()=>{{ const i={row}.querySelector('input'); i.value='14'; i.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        self.until(lambda: self.settings_file()["logging"]["keep_days"] == 14)
        b.wait(f"!!{row}.querySelector('.setdot')")


if __name__ == "__main__":
    unittest.main()
