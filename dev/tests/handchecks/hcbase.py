"""BL-341: the base class for a release's automated hand checks (dev/tests/handchecks/test_v<release>.py).

`HandcheckCase` is a LiveBrowserCase pointed at the hand-check vault that dev/tools/handcheck.py made from the release zip
(the demo portfolio, the registers, the stand-in Claude, a calendar, CREAITE_NOW pinned; the CREAITE_HC_* variables say where).
Run on its own (python3 dev/tests/handchecks/test_v195.py), the module makes that vault itself first, the same way.

Writing a check (one method per check, so the Results table can be filled):
- name it `test_cNN_<words>` (NN the check's number, two digits) and quote the check in its docstring;
- put the checks of one group in one class, so agents working on different groups never touch the same lines;
- `self.note(NN, "…")` adds a short note to the check's Results row (what was measured);
- a judgement check takes its screenshots with `self.sheet(NN, screen, …)` and passes once they are taken: the Results row
  says "judgement: on the screenshot sheet", never Pass or Fail;
- a check that changes data sets `own_vault = True` on its class: the class gets a fresh vault and server of its own;
- the module's KIND says each check's kind (scriptable, measurable, judgement, live only), and LIVE_ONLY gives the reason
  for each check that can only be done by hand.
"""
import json
import os
import shutil
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import measure  # noqa: E402
import sheet as sheetmod  # noqa: E402
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402

NOTES = {}                     # check number: note, read by handcheck.py
_SESSION = []                  # the session this module made itself (a standalone run)


def session():
    """The hand-check session: handcheck.py's (from CREAITE_HC_*), or one made now for a standalone run."""
    import handcheck
    if not os.environ.get("CREAITE_HC_BASE") and not _SESSION:
        s = handcheck.Session().open()
        _SESSION.append(s)
        unittest.addModuleCleanup(lambda: (s.close(), shutil.rmtree(s.dir, ignore_errors=True)))   # a standalone run leaves nothing
    return _SESSION[0] if _SESSION else None


def only():
    raw = os.environ.get("CREAITE_HC_ONLY", "")
    return {int(x) for x in raw.split(",") if x.strip().isdigit()}


def phase2(reason="phase 2: not automated yet"):
    """A check not written yet: skipped, and its Results row says so."""
    def wrap(fn):
        def test(self):
            self.skipTest(reason)
        test.__doc__, test.__name__ = fn.__doc__, fn.__name__
        test.phase2 = reason
        return test
    return wrap


# The screens, in the demo vault: go() call and what says it is drawn
SCREENS = {
    "today": ("go('today')", "!document.getElementById('v-today').hidden && document.querySelector('#v-today h2')"),
    "work": ("go('work')", "document.querySelector('#workTbl tbody tr')"),
    # 2.6.0 (#232 C2): the old Review and Intake pages are retired; their names open the one Intake page (nav.go), so the
    # older checks' "review" and "intake" land there too
    "intake-review": ("irOpen.value=null; go('intake-review')", "VIEW==='intake-review' && !document.getElementById('v-intake-review').hidden"),
    "review": ("irOpen.value=null; go('review')", "VIEW==='intake-review' && !document.getElementById('v-intake-review').hidden"),
    "intake": ("irOpen.value=null; go('inbox')", "VIEW==='intake-review' && !document.getElementById('v-intake-review').hidden"),
    "files": ("go('files')", "!document.getElementById('v-files').hidden"),
    "activity": ("go('activity')", "!document.getElementById('v-activity').hidden"),
    "projects": ("go('projects')", "!document.getElementById('v-projects').hidden"),
    "cockpit": ("go('cockpit','FAL')", "!document.getElementById('v-cockpit').hidden"),
    "milestones": ("MVAUD='int'; mvOpenPage('FAL','plan')", "VIEW==='milestones'"),
    "people": ("go('people')", "!document.getElementById('v-people').hidden"),
    "person": ("go('person','Sara Khan')", "!document.getElementById('v-person').hidden"),
    "help": ("go('help')", "!document.getElementById('v-help').hidden"),
    "settings-essentials": ("go('settings','essentials')", "!!document.querySelector('#set-essentials .srow')"),
    "project-settings": ("go('psettings','FAL')", "!!document.getElementById('psArchive')"),   # the Settings line: Archive's home
    "settings-advanced": ("go('settings','advanced')", "!!document.querySelector('#settingsBody [data-sec=thresholds] .srow')"),   # v2.6 (#246)
    "settings-work": ("go('settings','work')", "!!document.querySelector('#settingsBody [data-sec=views] .srow')"),
    "settings-health": ("go('settings','health')", "!!document.querySelector('#healthCard')"),
}


class HandcheckCase(LiveBrowserCase):
    """One class of hand checks against the hand-check vault (shared), or a fresh one of its own (`own_vault`)."""
    shared_server = True
    own_vault = False
    width, height = 1400, 1000

    @classmethod
    def runnable(cls):
        """The class's checks that will run: written (not phase 2) and, with --only, asked for."""
        names = [m for m in dir(cls) if m.startswith("test_c") and not getattr(getattr(cls, m), "phase2", None)]
        return [m for m in names if not only() or (m[6:8].isdigit() and int(m[6:8]) in only())]

    @classmethod
    def setUpClass(cls):
        cls.idle = not cls.runnable()          # nothing to run: no vault, server or Chrome for this class
        if not cls.idle:
            super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        if not cls.idle:
            super().tearDownClass()

    @classmethod
    def start_server(cls):
        s = session()
        if cls.own_vault:
            import handcheck
            s = s or handcheck.Session(os.environ["CREAITE_HC_DIR"])
            if not s.zip and os.environ.get("CREAITE_HC_ZIP"):
                s.zip = Path(os.environ["CREAITE_HC_ZIP"])
            cls._hc = s
            cls.vault = s.make_vault(f"vault-{cls.__name__}")
            cls.proc, cls.base = s.start_server(cls.vault)
        else:
            cls._hc, cls.proc = None, None
            cls.vault = Path(os.environ["CREAITE_HC_VAULT"])
            cls.base = os.environ["CREAITE_HC_BASE"]
        cls.now = os.environ.get("CREAITE_HC_NOW") or (s.now if s else None)
        cls.v = None

    @classmethod
    def stop_server(cls):
        if getattr(cls, "_hc", None) and getattr(cls, "proc", None):
            cls._hc.stop_server(cls.proc)
        cls.proc = None

    def setUp(self):
        n = self.check_number()
        reason = getattr(getattr(self, self._testMethodName), "phase2", None)
        if reason:
            self.skipTest(reason)
        if only() and n not in only():
            self.skipTest("not in --only")
        super().setUp()
        if self.now:
            pin_page_clock(self.b, self.now)

    def check_number(self):
        name = self._testMethodName
        return int(name[6:8]) if name.startswith("test_c") and name[6:8].isdigit() else None

    # ── helpers ──

    def note(self, n, text):
        NOTES[n] = "; ".join(x for x in (NOTES.get(n), text) if x)

    def screen(self, name, settle=0.4):
        """Go to a screen and wait until it is drawn."""
        go, ready = SCREENS[name]
        self.b.eval(go)
        self.b.wait(ready, 15)
        self.b.pump(settle)

    def run_in_vault(self, *args, env=None):
        """A creaite script in the vault through its run wrapper, with the session's clock; returns (exit code, output)."""
        import subprocess
        r = subprocess.run([str(self.vault / "system/scripts/run"), *map(str, args)], cwd=self.vault, capture_output=True,
                           text=True, env={**os.environ, "CREAITE_NOW": self.now or "", **(env or {})})
        return r.returncode, r.stdout + r.stderr

    def sheet(self, n, screen, palettes=None, modes=("light", "dark"), widths=(1400, 320), prepare=None):
        """Screenshots of `screen` for the judgement sheet: every palette (or those given) × modes × widths. `prepare(b)`
        runs after the screen is drawn (open a dialog, scroll to a section). Returns how many were taken."""
        if not sheetmod.enabled():
            return 0
        b, k = self.b, 0
        palettes = palettes or measure.themes(b)
        was = b.eval("[S.palette, S.theme]")
        try:
            for w in widths:
                measure.width(b, w, 1000 if w > 600 else 800)
                for p in palettes:
                    for m in modes:
                        measure.theme(b, p, m)
                        self.screen(screen, settle=0.3)
                        if prepare:
                            prepare(b)
                            b.pump(0.2)
                        path = sheetmod.shot_path(n, screen, p, m, w)
                        measure.shot(b, path)
                        sheetmod.record(n, screen, p, m, w, path)
                        k += 1
        finally:
            measure.width(b, self.width, self.height)
            b.eval("(()=>{ S.palette=%s; S.theme=%s; applyTheme(); return true; })()" % tuple(json.dumps(x) for x in was))
        return k


# ── BL-10: the clock and the record (checks 23 to 29) ──

def months_on(now, months):
    """`now` ("YYYY-MM-DD HH:MM") moved on by whole months, the day kept (or the month's last day): "today plus 7 months"."""
    import calendar
    from datetime import datetime
    t = datetime.strptime(now, "%Y-%m-%d %H:%M")
    y, m = divmod(t.month - 1 + months, 12)
    y, m = t.year + y, m + 1
    return t.replace(year=y, month=m, day=min(t.day, calendar.monthrange(y, m)[1])).strftime("%Y-%m-%d %H:%M")


def shown(day):
    """YYYY-MM-DD (or a longer stamp) as DD-MM-YYYY, as creaite shows dates."""
    s = str(day)
    return f"{s[8:10]}-{s[5:7]}-{s[0:4]}"


def db_rows(vault, sql, *args):
    """Rows of a read-only query on the vault's tracker.db, as dicts (the check reads the record; it never writes it)."""
    import sqlite3
    con = sqlite3.connect(f"file:{Path(vault) / 'system/tracker.db'}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, args)]
    finally:
        con.close()


def pending_proposals(vault):
    """The proposal files waiting in the vault's staging (what Review lists), by name."""
    return sorted(p.name for p in (Path(vault) / "system/staging").glob("proposed-*.json"))


def xlsx_text(path):
    """Every worksheet's XML in an .xlsx, joined (enough to see whether an ID is in the Excel export)."""
    import zipfile
    with zipfile.ZipFile(path) as z:
        return " ".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.startswith("xl/") and n.endswith(".xml"))
# ── BL-334 and BL-316 (checks 42 to 50) ──────────────────────────────────────

def vip_found(vault, conversations, now):
    """Record conversations as the sweep would (`sweep.py vip record <file> --found sweep`), with the clock at `now`
    ("YYYY-MM-DD HH:MM"), the way the hand check's step does it. The file goes in the vault's staging drafts (the run wrapper
    passes only paths inside the vault). Returns (exit code, output)."""
    import subprocess
    f = Path(vault) / "system/staging/drafts/hc-found.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(conversations), encoding="utf-8")
    r = subprocess.run([str(Path(vault) / "system/scripts/run"), "sweep.py", "vip", "record", str(f), "--found", "sweep"],
                       cwd=vault, capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": now})
    return r.returncode, r.stdout + r.stderr


def behaviour_screens(milestone):
    """test_shared_behaviour's screens (the snapshot sample's), pointed at the demo vault: project ABC → FAL, its first
    milestone → `milestone` (an open one of FAL's), the sample's person → Sara Khan. Each is (go, ready, region), as there."""
    import re as _re
    import test_shared_behaviour as tsb

    def demo(s):
        if not isinstance(s, str):
            return s
        s = s.replace("ABC-M-001", milestone).replace("abc steering", "fal steering").replace("Sara Example", "Sara Khan")
        return _re.sub(r"\bABC\b", "FAL", s)
    return {name: tuple(demo(x) for x in spec) for name, spec in tsb.SCREENS.items()}


def behaviour_driver(case, screens):
    """BL-316's keyboard script and Undo check (dev/tests/test_shared_behaviour.py: Enter opens, ↑ ↓ move, Esc closes and
    returns focus, Tab closes a menu or list or stays in a dialog; a change from a menu or a list offers Undo), driven on
    `screens` (behaviour_screens) in `case`'s browser. Its methods are that test's own, unchanged; only the screens, going to
    them and the Archive prompt's project (FAL, not the sample's ABC) differ."""
    import test_shared_behaviour as tsb
    import test_shared_undo as tsu      # #89: the Undo half moved to its own file
    import test_ui_sweep as us

    class Drv(tsb.Driver):
        opened, arrows, escape, tab_closes, drive, cmdk = (tsb.SharedBehaviour.opened, tsb.SharedBehaviour.arrows,
                                                          tsb.SharedBehaviour.escape, tsb.SharedBehaviour.tab_closes,
                                                          tsb.SharedBehaviour.drive, tsb.SharedBehaviour.cmdk)
        pick = tsu.SharedUndo.pick
        # the dialog scripts no control opens (KEYED) and their helpers, as that test has them; parch is this vault's own, below
        ndel, mnapp, crleft, rail, boardask, llcompare, searchprev, railcust = (
            tsb.SharedBehaviour.ndel, tsb.SharedBehaviour.mnapp, tsb.SharedBehaviour.crleft, tsb.SharedBehaviour.rail,
            tsb.SharedBehaviour.boardask, tsb.SharedBehaviour.llcompare, tsb.SharedBehaviour.searchprev, tsb.SharedBehaviour.railcust)
        enter_on, dialog_keys, tidy = tsb.SharedBehaviour.enter_on, tsb.SharedBehaviour.dialog_keys, tsb.SharedBehaviour.tidy

        def __init__(self):
            self.b, self.seen = case.b, []

        def goto(self, name):
            go, ready, region = screens[name]
            b = self.b
            b.eval("closePanel(); typeof closeChat==='function' && closeChat(); "
                   "document.getElementById('cmdk').open && document.getElementById('cmdk').close(); "
                   "document.getElementById('prepDlg')?.open && document.getElementById('prepDlg').close(); "
                   "document.getElementById('parchDlg')?.open && document.getElementById('parchDlg').close(); "
                   "!document.getElementById('mvPeek')?.hidden && mvEdClose(true); MV.rb=null; go('today')")
            go(b) if callable(go) else b.eval(go)
            b.wait(ready, 15)
            last = None
            for _ in range(12):
                b.pump(0.25)
                html = b.eval(f"(document.querySelector({region!r})||{{}}).outerHTML||''")
                if html == last:
                    break
                last = html
            b.eval(us.PROBE + ";true")
            return region

        def settle(self, name):
            b = self.b
            for _ in range(2):
                if not b.eval("SB.popups().length"):
                    break
                self.press("Escape", 0.15)
            if b.eval("SB.reset()") or not b.eval(tsb.ON_SCREEN.get(name, screens[name][1])):
                self.goto(name)
                b.eval(tsb.PROBE + ";true")

        def openers(self, name):
            region = screens[name][2]
            return self.b.eval(f"SB.openers({json.dumps(tsb.ONLY.get(name, region))})")

        def parch(self):
            """test_shared_behaviour's parch, on FAL's Archive (the demo has no ABC)."""
            b = self.b
            self.goto("project-settings")
            b.eval(tsb.PROBE + ";true")
            sel = json.dumps("#psArchive")
            b.eval(f"(()=>{{ const e=document.querySelector({sel}); e.scrollIntoView({{block:'center'}}); e.focus(); }})()")
            self.press("Enter", 0.5)
            b.wait("!!document.getElementById('psArchiveYes')", 10)
            b.eval("document.getElementById('psArchiveYes').focus()")
            self.press("Enter", 0.5)
            try:
                b.wait("document.getElementById('parchDlg')?.open", 20)
            except TimeoutError:
                return ["Enter opens nothing"]
            self.seen.append({"ids": ["parchDlg"], "labels": [], "classes": []})
            bad = []
            if not b.eval("document.getElementById('parchDlg').contains(document.activeElement)"):
                bad.append("focus stays outside the dialog")
            self.press("Escape", 0.4)
            if b.eval("document.getElementById('parchDlg').open"):
                bad.append("Esc leaves it open")
            elif not b.eval(f"document.activeElement===document.querySelector({sel})"):
                bad.append("Esc doesn't return focus to the control")
            return bad

    return Drv()
