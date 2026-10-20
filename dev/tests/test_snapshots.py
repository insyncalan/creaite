"""BL-254: screen snapshots. Every screen of the sample vault, and the main states of some (Work with an item's panel
open, ⌘K, ask creaite's panel, each Settings tab), is rendered in headless Chrome at a fixed date and time, and the
HTML of its main region is compared with the saved golden in dev/tests/snapshots/. Any difference fails, with a unified
diff of the screen that changed. The Chrome tests check behaviours one by one; this notices a screen whose markup
changed quietly (a step lost from inside drawPanel, a section that no longer renders).

Run: python3 dev/tests/test_snapshots.py              (Chrome tier)
Update the goldens deliberately: python3 dev/tools/run_tests.py --update-snapshots [screen …]
    and say in the commit why each one changed. A sprint that changes a screen on purpose commits its new goldens with it.

Fixed, so it passes on any machine and any day (a fresh clone, Linux): the sample vault's dates (populate's TODAY), the
server's clock (CREAITE_NOW), the page's clock (pin_page_clock), the time zone (UTC, server and page), the locale (en-GB),
the platform (a Mac: the shortcuts show ⌘), the server's home folder (empty: no launcher, no update zip in Downloads)
and the window size. Masked: the vault's path, the server's port, tokens and IDs that differ per run, "… ago" and
measured sizes in inline styles. The history's and rows' stamps, which tracker.py apply takes from the real clock, are
moved to the fixed day when the vault is built, and so are the times of the inbox and project files. A screen with no golden yet is listed, not failed; the goldens are recorded once the
screens settle (see dev/BUILD.md).
"""
import difflib
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard  # noqa: E402
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402

FIXED = date(2026, 10, 9)                               # a Friday, as in test_steerco and test_prep_context_pinned
NOW = f"{FIXED} 09:00"
LAST_VISIT = f"{FIXED - timedelta(days=1)} 17:00"           # Today's "Resolved since": unpinned, it falls back to the vault's real build time
test_dashboard.TODAY = FIXED                            # the sample vault's dates are d(n) from this TODAY
SNAPSHOTS = Path(os.environ.get("CREAITE_SNAPSHOT_DIR") or Path(__file__).resolve().parent / "snapshots")
ACTUAL = SNAPSHOTS / "actual"                           # what a failing run saw, for a closer look (git-ignored)
UPDATE = os.environ.get("CREAITE_UPDATE_SNAPSHOTS") == "1"
ONLY = {s for s in os.environ.get("CREAITE_SNAPSHOT_ONLY", "").split(",") if s}
META = 4
MAC_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 "
          "Safari/537.36")                                  # the platform the goldens were recorded on, on any machine

# BL-320 (v1.9.2): four places; v2.6 (#246): tabs. Essentials, Advanced (its first sub-tab), AI drafts (the counts card,
# which Advanced held before) and Health. The Settings line retired the People and projects sections (their old address opens
# the People page, whose golden is "people")
SETTINGS_TABS = ("essentials", "advanced", "ai", "health")
# Health's check runs doctor, whose answer depends on the machine (a launcher, Rosetta, OneDrive): the golden shows a fixed one.
HEALTH_ANSWER = {"ok": True, "checked": "2026-10-09 09:00", "fine": 22, "fine_names": ["Database", "Backups"], "read_only": True,
                 "problems": [{"id": "offsite_backup", "title": "No copy of the backup in OneDrive yet", "check": "OneDrive copy",
                               "severity": "warn", "detail": "Made after the next daily backup",
                               "fix": {"kind": "offsite", "button": "Make it now", "would_run": "", "waits_for": "",
                                       "how": "It is made after the next daily backup, at the first session of the day", "built": False}}],
                 "stopped": [],
                 "standalone": [{"id": "m365", "kind": "m365", "title": "Microsoft 365 isn't connected", "button": "Open connector settings",
                                 "does": "Open Claude's connector settings, where you reconnect Microsoft 365 yourself.", "built": True,
                                 "url": "https://claude.ai/settings/connectors", "how": "", "would_run": "", "waits_for": ""}]}


def open_health(b):
    """Settings › Health with /api/health answered by HEALTH_ANSWER (every other call goes to the server)."""
    import json
    b.eval(f"(()=>{{ const real=window.api, ans={json.dumps(HEALTH_ANSWER)}; window.api=async(p,body)=>p==='/api/health'?JSON.parse(JSON.stringify(ans)):real(p,body); }})()")
    b.eval("go('settings','health')")


SETTINGS_READY = {"essentials": "!!document.querySelector('#set-essentials .srow')",
                  "advanced": "!!document.querySelector('#subtabs') && !!document.querySelector('#set-thresholds .setembed .srow')",
                  "ai": "!!document.querySelector('#set-drafts .setembed .srow') && !!document.querySelector('#drStats') && document.querySelector('#drStats').textContent.trim() !== ''",   # AI drafts' counts arrive from /api/drafts after the page draws; a slow reply must not be captured empty
                  "health": "!!document.querySelector('#healthCard .hsum')"}


def open_first_item(b):
    """Work, then a real click on the first row's ID: the item's panel, as a person opens it."""
    b.eval("go('work')")
    b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
    b.click("#workTbl tbody tr[data-row] a.rowid")


def open_cmdk(b):
    b.key("k", META)



def rail_state(width, labels):
    """#156: the rail in one of its three states (188px expanded; 76px collapsed with labels; 56px icons only), reached as
    test_rail_states does: the wordmark toggle, then Labels when collapsed."""
    def step(b):
        open_health(b)                  # the badge on More and Health comes from the health answer: the fixed one, so it never depends on order
        # The stub only answers a check that runs after it is installed; a page that already checked (a shared server, an earlier
        # screen, CI with no problems) keeps its own count. Set the count the stub's answer gives, as checkHealth would.
        n = len(HEALTH_ANSWER.get("problems", []))
        b.wait(f"(healthCount.value={n}, document.getElementById('railHealthBadge') && document.getElementById('railHealthBadge').textContent.trim()==='{n}')", 15)
        def w():
            return b.eval("Math.round(document.querySelector('.rail').getBoundingClientRect().width)")
        if width == 188 and w() != 188:
            b.click("#railTog")
        if width != 188 and w() == 188:
            b.click("#railTog")
        b.wait(f"Math.round(document.querySelector('.rail').getBoundingClientRect().width)!==188 || {width}===188", 5)
        if width != 188:
            b.eval(f"railSetLabels({'true' if labels else 'false'})")
        b.wait(f"Math.round(document.querySelector('.rail').getBoundingClientRect().width)==={width}", 5)
    return step


# name: (how to get there: JavaScript, or a step that drives the browser; what to wait for; the region to keep).
SCREENS = {
    "today": ("go('today')", "!document.getElementById('v-today').hidden", "#v-today"),
    "work": ("go('work')", "document.querySelector('#workTbl tbody tr')", "#v-work"),
    "work-panel": (open_first_item, "document.getElementById('panel').classList.contains('on')", "#panel"),
    # #232 C2: Intake and Review are one page, one golden (intake-review.html replaces intake.html and review.html). The page asks for
    # BL-315's guesses (/api/review/guesses) while it is open; they show in the reject menu, not on a row, so the page is ready without them.
    "intake-review": ("go('intake-review')", "!document.getElementById('v-intake-review').hidden && !!document.querySelector('#v-intake-review h1') "
                      "&& !!document.querySelector('#v-intake-review tr')", "#v-intake-review"),
    "files": ("go('files')", "!document.getElementById('v-files').hidden", "#v-files"),
    "activity": ("go('activity')", "!document.getElementById('v-activity').hidden", "#v-activity"),
    "projects": ("go('projects')", "!document.getElementById('v-projects').hidden", "#v-projects"),
    "cockpit": ("go('cockpit','ABC')", "!document.getElementById('v-cockpit').hidden", "#v-cockpit"),
    # Internal view: the sample's milestones aren't client-visible, so the default Client view would show none.
    "milestones": ("MVAUD='int'; mvOpenPage('ABC','plan')", "VIEW==='milestones'", "#v-milestones"),
    "people": ("go('people')", "!document.getElementById('v-people').hidden", "#v-people"),
    "person": ("go('person','Sara Example')", "!document.getElementById('v-person').hidden", "#v-person"),
    "help": ("go('help')", "!document.getElementById('v-help').hidden", "#v-help"),
    **{f"settings-{t}": (open_health if t == "health" else f"go('settings','{t}')",
                         f"!document.getElementById('v-settings').hidden && {SETTINGS_READY[t]}", "#v-settings")
       for t in SETTINGS_TABS},
    "cmdk": (open_cmdk, "document.getElementById('cmdk').open", "#cmdk"),
    "ask": ("openChat()", "!document.getElementById('chat').hidden || document.getElementById('chat').classList.contains('on')",
            "#chat"),
    "rail-expanded": (rail_state(188, True), "Math.round(document.querySelector('.rail').getBoundingClientRect().width)===188", ".rail"),
    "rail-collapsed": (rail_state(76, True), "Math.round(document.querySelector('.rail').getBoundingClientRect().width)===76", ".rail"),
    "rail-icons": (rail_state(56, False), "Math.round(document.querySelector('.rail').getBoundingClientRect().width)===56", ".rail"),
}

MASKS = [
    (re.compile(r"127\.0\.0\.1:\d+"), "127.0.0.1:<PORT>"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "<UUID>"),
    (re.compile(r"\b[0-9a-f]{16,}\b"), "<HEX>"),
    (re.compile(r"([?&](?:t|token|v|nonce)=)[\w-]+"), r"\1<TOKEN>"),
    (re.compile(r"\b\d+ (?:seconds?|secs?|minutes?|mins?) ago\b|\bjust now\b"), "<AGO>"),
    (re.compile(r"\d\d:\d\d:\d\d(?:\.\d+)?"), "<HH:MM:SS>"),        # clock times to the second: when the page was drawn
]
STYLE = re.compile(r'style="([^"]*)"')


COUNTED_ID = re.compile(r'\bid="([A-Za-z_-]*?)(\d+)([A-Za-z_-]*)"')


def renumber_ids(html):
    """IDs a page-wide counter makes (sr1, sr63h…) depend on what was drawn before; number them afresh in order of first
    appearance in this capture, keeping their suffixes, everywhere they are used (labelledby, describedby, for…)."""
    order = {}
    for m in COUNTED_ID.finditer(html):
        prefix = m.group(1)
        key = (prefix, m.group(2))
        if key not in order:
            order[key] = sum(1 for p, _ in order if p == prefix) + 1
    for (prefix, n), k in sorted(order.items(), key=lambda kv: -len(kv[0][1])):   # longer numbers first: sr12 before sr1
        html = re.sub(rf"\b{re.escape(prefix)}{n}(?=[A-Za-z_-]*\b)", f"{prefix}#{k}", html)
    return html


def normalise(html, root):
    """The region's HTML with what varies by machine or run masked, one tag a line for a readable diff."""
    html = html.replace(str(Path(root).resolve()), "<VAULT>").replace(str(root), "<VAULT>")
    for pat, rep in MASKS:
        html = pat.sub(rep, html)
    html = renumber_ids(html)
    # whether a table overflows sideways depends on the machine's fonts (Linux CI is wider than a Mac): mask the "more columns" cue
    html = re.sub(r'<div class="xcue[^"]*"[^>]*>.*?</button>\s*</div>', "", html, flags=re.S)
    html = re.sub(r' xscroll(?: xstick)?"( data-xc="1")?( style="--xstick:[^"]*")?', '"', html)
    html = STYLE.sub(lambda m: 'style="' + re.sub(r"-?\d+(?:\.\d+)?(px|%|em|rem)", r"#\1", m.group(1)) + '"', html)
    html = re.sub(r'aria-valuenow="\d+"', 'aria-valuenow="#"', html)   # v1.9.5: a resize handle's value is the column's measured width
    html = re.sub(r">\s*<", ">\n<", re.sub(r"[ \t]+", " ", html))
    return "\n".join(ln.rstrip() for ln in html.splitlines() if ln.strip()) + "\n"


@unittest.skipIf(sys.platform == "win32", "snapshots are recorded on macOS and Linux")
class Snapshots(LiveBrowserCase):
    shared_server = True
    quiet_jobs = False        # the settings screens are goldens: they show the shipped backup and archive settings
    width, height = 1400, 1000
    maxDiff = None

    @classmethod
    def load(cls, v):
        """The sample vault, then its history and updated_at stamps moved to the fixed day (tracker.py apply writes the
        real time), keeping their order, so no screen shows when the test happened to run."""
        super().load(v)
        with closing(sqlite3.connect(v.root / "system" / "tracker.db")) as con:
            con.execute(f"UPDATE change_log SET at = datetime('{FIXED} 08:00:00', '+' || rowid || ' seconds') || '.000'")
            con.execute(f"UPDATE applies SET at = datetime('{FIXED} 08:00:00', '+' || apply_id || ' minutes') || '.000'")
            for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall():
                if "updated_at" in [c[1] for c in con.execute(f"PRAGMA table_info({t})")]:
                    con.execute(f"UPDATE {t} SET updated_at = '{FIXED} 08:00:00.000'")
            con.commit()
        # The files' own times (Intake's "Added" words, the order of Latest reports) are when the vault was built: the
        # fixed day instead, so Intake doesn't show the date the test ran.
        stamp = datetime(FIXED.year, FIXED.month, FIXED.day, 8, 0, tzinfo=timezone.utc).timestamp()
        for top in ("inbox", "projects"):
            for f in (v.root / top).rglob("*"):
                if f.is_file():
                    os.utime(f, (stamp, stamp))

    @classmethod
    def server_env(cls):
        """The fixed clock and zone, and an empty home folder of its own: the server reads ~/Applications (the launcher) and
        ~/Downloads (an update zip), and a screen must never show what this machine's home holds."""
        cls.home = tempfile.mkdtemp(prefix="creaite-snap-home-")
        return {"CREAITE_NOW": NOW, "TZ": "UTC", "HOME": cls.home}

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(getattr(cls, "home", ""), ignore_errors=True)

    def setUp(self):
        super().setUp()
        self.b.call("Emulation.setTimezoneOverride", timezoneId="UTC")
        self.b.call("Emulation.setLocaleOverride", locale="en-GB")
        self.b.call("Emulation.setUserAgentOverride", userAgent=MAC_UA, platform="MacIntel")   # ⌘, not Ctrl, on Linux too
        self.b.call("Page.addScriptToEvaluateOnNewDocument", source=f"localStorage.setItem('creaite-lastvisit', JSON.stringify('{LAST_VISIT}'))")
        pin_page_clock(self.b, NOW)                         # reloads the page: MAC and the clock are read as it loads

    def capture(self, name):
        """Go to the screen and return its region's HTML once two reads 300 ms apart agree (async renders settle)."""
        go, ready, region = SCREENS[name]
        b = self.b
        b.eval("closePanel(); typeof closeChat==='function' && closeChat(); "
               "document.getElementById('cmdk').open && document.getElementById('cmdk').close(); go('today')")   # #245: Intake and Review and its fold are gone, so there is nothing to unfold
        if callable(go):
            go(b)
        else:
            b.eval(go)
        b.wait(ready, 15)
        last, html = None, None
        for _ in range(20):
            b.pump(0.3)
            html = b.eval(f"(document.querySelector({region!r})||{{}}).outerHTML||''")
            if html == last:
                break
            last = html
        return normalise(html, self.v.root)

    def test_every_screen_matches_its_golden(self):
        missing = []
        for name in SCREENS:
            if ONLY and name not in ONLY:
                continue
            with self.subTest(name):
                got = self.capture(name)
                golden = SNAPSHOTS / f"{name}.html"
                if UPDATE:
                    SNAPSHOTS.mkdir(exist_ok=True)
                    golden.write_text(got, encoding="utf-8")
                    continue
                if not golden.exists():
                    missing.append(name)
                    continue
                want = golden.read_text(encoding="utf-8")
                if got != want:
                    ACTUAL.mkdir(parents=True, exist_ok=True)
                    (ACTUAL / f"{name}.html").write_text(got, encoding="utf-8")
                    diff = list(difflib.unified_diff(want.splitlines(), got.splitlines(), f"golden/{name}.html",
                                                     f"now/{name}.html", lineterm="", n=2))
                    self.fail(f"the {name} screen changed ({len(diff)} diff lines; the whole page is in "
                              f"dev/tests/snapshots/actual/{name}.html):\n" + "\n".join(diff[:150]))
        if missing and not UPDATE:
            print(f"\nNo golden yet for {len(missing)} screen(s), not compared: {', '.join(missing)}. "
                  f"Record them with: python3 dev/tools/run_tests.py --update-snapshots", file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
