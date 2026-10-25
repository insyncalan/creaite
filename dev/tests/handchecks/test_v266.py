"""creaite 2.6.5's hand checks, automated against a vault made from the release zip (the fictional demo portfolio: Falcon Data
Platform and the rest). One check per item, `test_cNN_...`, its docstring quoting what the item must do. Checks 1 to 36 are the 2.6.4
sheet (2.6.5 contains all of 2.6.4), as it stood on the 2.6.4b line (hand-check work of Team Cap, e80fccf1) and brought up to the
2.6.5 line head 591eed66: checks 35 and 36 (a tick left behind a folded waiting meeting by Esc in the search box and by Group by None)
are fixed there and are plain checks now. Checks 37 to 42 are what 2.6.5 adds (dev/release-notes/2.6.5-plain.md).

   1  #337  Settings: a tick-box row keeps a label at least 220 px wide at 900 and 1400 px
   2  #337  Activity: the By column does not wrap (one line, rows no taller than 52 px) at 900 and 1400 px
   3  #337  Cockpit: the edit pencils are 3:1 or better in light and dark, 24 px targets; chart text is 12 px or more
   4  #337  People at 900 and 1400 px: the table fits its box and Overdue (the sort column) is on screen
   5  #337  People at 900 and 1400 px: no word breaks in the middle                                  (fixed on the line at 72de4a6a; was M2)
   6  #337  Milestones, Client view with several hidden milestones: "None of the N milestones are shown to the client yet", page and card
   7  #337  Milestones, Client view with ONE hidden milestone says it is NOT shown                    (fixed on the line; was H1)
   8  #292  Walk Today, Work, Intake, Files, Activity, Projects, a cockpit, People and every Settings tab: no file path, script name, "sweep"
         or Tier 2 word (proposal, staged, vault, live server, extract) in the words on screen
   9  #293  Help: the key renamed words are there and the old ones are gone
  10  #292  A change to an item that waits for Save does not say "Saved for Review"                   EXPECTED FAILURE (H2)
  11  #293  Chat commands: the old words still start the same jobs; the plain ones are taught
  12  #333  The figure check: a date shown as 20-11-2026 is said by "20th of November"; a different day is flagged
  13  #333  The figure check: a wrong year with the day and month in words is flagged                  EXPECTED FAILURE (L5)
  14  #333  Another project's item is marked a possible duplicate only on a close match
  15  #333  The toast counts the items the apply wrote, not the rows ticked                           EXPECTED FAILURE (deferred, guarded)
  16  #345  expect on every deciding route: reject, Approve instead, repeat, retarget and Approve minutes refuse a missing or stale one
  17  #345  /api/review/assign names the item (expect)                                                (fixed in the 345 diff; Team Cap M1)
  18  #346  The day's "Runs creaite started" chat carries nothing into a fresh run
  19  #346  A run that fails to set up leaves no record and the server is not left "busy"
  20  #334  Over budget (confirm): the card appears and the typed ask is refused plainly; Run anyway goes through; nothing is echoed
  21  #334  Over budget (stop): refused even with Run anyway; a confirmed request, Review, Apply and Undo are never blocked
  22  #334  The week runs Monday to Monday, 80% warns, 100% holds; the Usage figures are counts and dates only
  23  #334  An ask run cannot raise its own budget (settings, the usage log and the setting command are all refused to it)
  24  #334  In the ask panel: the Weekly AI budget card, Cancel starts nothing, Run anyway runs                 (Chrome)
  25  #348  The profile card with the name set to a colleague in the register shows nothing of theirs as yours
  26  #292  No file path is on screen (Files' tooltip, the project's Settings page, Health's detail lines)  EXPECTED FAILURE
  27  #334  The new report scripts (ai_budget.py, start_tokens_report.py) are classified read only in reach.py (test_record_commands)
  28  #334  The budget is OFF by default: over any use, in confirm and in stop, nothing is held, warned or refused
  29  #334  The Usage tab says the budget is off; in the ask panel a typed request is sent with no budget card or line (Chrome)
  30  #352  Today shows no stale-updates line and no Draft updates button, at 1400 and 900 px; the draft stays in Work
  31  #351  A past day on Today shows no follow-up chips and no Check or Process links under its meetings; today's Prep peek and
            Intake's Check and Process are unchanged once the waiting tail is opened (#340 folds it: opened by Show, the Arrived box,
            Show: Waiting or a search; folded without, folded again when released)                       (own vault, Chrome)
  32  #338  The rules file every run reads is at most 60% of its 2.6.3 size, the reference file is there and the rules point to it, and
            every never clause survives; a mutant that drops one turns the check red                          (own vault, no browser)
  33  #343  Show the waiting tail, tick a waiting meeting, Hide it: nothing is ticked, no tick bar is shown, and Later and Not needed
            because... do not move the hidden meeting          (fixed on the line at 72de4a6a, which clears the ticks on a fold; own vault, Chrome)
  34  #343  People's Organisation and Role columns (headings included) keep a word on one line at 900 and 1400 px; a sibling of
            check 5, narrowed to the two columns                                                  (fixed on the line at 72de4a6a; was M1)
  35  #343  Tick a waiting meeting found by search, press Esc in the search box: the tail folds, no tick may stay behind it (no bar saying
            "1 selected") and Later does not move it; also covers M-1, the click-time guard   (fixed at 591eed66; was M-2; own vault, Chrome)
  36  #343  Group by Day, tick a waiting meeting, Group by None: same assertions                   (fixed at 591eed66; was M-2; own vault, Chrome)
  37  #360  People's Display menu: D opens it; Group by Role/Organisation/Project/Overdue/Details draws headings with "n people", "Showing x of y" still
            counts people, Order by and the reverse, Properties (Email off, Role moved, Name first), remembered after a reload, Reset;
            no option or star about following anyone (BL-288); settings.json and the people register byte-identical; fits at 900 px
  38  #357  Save from a panel: "Saved 1 change" in the ok tint with one Undo, the backup line as hover text; another change brings the waiting
            bar back and the message becomes "The earlier save can still be undone in Activity"                       (own vault, Chrome)
  39  #359  The focused ask creaite box has a plain accent border: no animation, no gradient, no turning rule left in the stylesheet
  40  #356  A clear Intake: the sentence and one next job (refresh the calendar, check mail and Teams, open tomorrow's meetings, or none); greyed out
            with a reason when busy or offline (not the tomorrow one); fits at 900 px; nothing while there is work
  41  #340  Intake leads with the work in List, Board and Two panes: the waiting tail starts folded, Show and Hide, mail and Teams shows five then
            "Show all n" and back, Approve routine counts the rows shown, the List puts mail before the tail     (own vault, Chrome)
  42  #343  Work's List has no "Show: Empty groups" (the Board keeps it); Files says Word, Transcript, Excel; the cockpit's top risks show the
            owner ("You" or "No owner"); help buttons 24 px; nothing under 12 px on the cockpit

How a check is wired (every class that changes data has a vault of its own, made from the zip, so nothing a check changes reaches another):
  Design266, Words266, Figures266, Today266, People266, Page266  the shared hand-check vault and Chrome; nothing is changed (Today266 sets the page's own data and puts it back)
  Item266, Profile266, Card266, UsageOff266, PastDay266, TickFold266, Calm266, Lead266  a vault of its own, its server and Chrome (UsageOff266: the budget never switched on;
                                   PastDay266, TickFold266, Lead266 (checks 33, 35, 36, 41): a fictional calendar of the past day and today, with every transcript state)
  Routes266, Budget266             a vault of its own and its live server (the page's own token), no browser; Budget266's Claude is a stand-in
                                   (the budget is OFF by default: its checks switch it on the way Settings does; check 28 leaves it off)
  Commands266, Extraction266, Runs266, Rules266  a vault of its own and the engine's own code run in it (Runs266: a stand-in for the thread and the process)

The guarded parts (#345, #346, #334 and the reach.py entries) shipped in 2.6.4, so the checks that need a guarded change find it in the
repository's own files and are plain checks here. A check that needs a change this tree does not have would be an EXPECTED FAILURE (the convention of test_v262.py and test_v263.py): red for the right reason, and an
unexpected success (flagged) the moment the change is in. A check marked EXPECTED FAILURE (a finding of Team Cap's) is one the line
still fails; fixed, it becomes an unexpected success and loses its mark. CREAITE_HC_SHOW_XFAIL=1 runs every one of them as a plain check,
to see why it fails.

Run them (from the repository root; a release zip is built from this checkout first):
  python3 dev/tests/handchecks/test_v266.py                         all, with the committed tree (or --dirty: uncommitted engine files)
  python3 dev/tests/handchecks/test_v266.py Routes266.test_c16_...  one check
  python3 dev/tools/handcheck.py v2.6.5 [--dirty] [--only 1,4]      the runner (Results table, run folder); --no-sheet skips the screenshots
Standalone, the module builds the zip itself, with the uncommitted engine files when the tree has any (the chain applied but not
committed), and removes its run folder at the end (CREAITE_HC_KEEP=1 keeps it). Safe at -j 3: every vault, port and folder is new, and
every server and Chrome is stopped by its own process group (proc_guard), never by name. Desktop (1400 px) and 900 px only.

Never Microsoft 365, never a real model: Claude is the stand-in. Fictional data only (the demo's people).
Live only: a real ask run over a real week's budget (check 24 uses the stand-in), and Alan's own walk of the screens in light and dark.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))                  # dev/tests, for the helpers this borrows
import hcbase  # noqa: E402
import measure  # noqa: E402
from hcbase import NOTES, HandcheckCase, db_rows, only  # noqa: E402,F401  (NOTES: read by handcheck.py)

NOTES.clear()

REPO = HERE.parents[2]
SCRIPTS = REPO / "system/scripts"
DASH = REPO / "system/templates/dashboard/src"

KIND = {n: "scriptable" for n in range(1, 76)}
LIVE_ONLY = {}        # check 24 runs on the stand-in; a real model over a real week's use is Alan's own


def _src(name):
    p = SCRIPTS / name
    return p.read_text(encoding="utf-8") if p.is_file() else ""


# What this tree has of the guarded 2.6.4 chain (read from the repository's own files, which the zip is built from)
HAS = {
    "expect": "def expect_refusal" in _src("live_server.py"),
    "runs": 'startswith("runs-")' in _src("live_server.py"),
    "setup": "RUNS.pop(run_id" in _src("live_server.py"),
    "budget": "def budget_gate" in _src("live_server.py") and (SCRIPTS / "ai_budget.py").is_file(),
    "reach": '"ai_budget.py"' in _src("reach.py"),
}
CHAIN = {"expect": "345/live_server.diff", "runs": "346/live_server.diff", "setup": "346/live_server.diff",
         "budget": "334/live_server.diff (and ai_budget.py)", "reach": "line-reach/reach.diff"}


def needs(key):
    """A check that needs a change of the guarded 2.6.4 chain: an expected failure while this tree lacks it, a plain check once it has it."""
    def wrap(fn):
        if HAS[key] or os.environ.get("CREAITE_HC_SHOW_XFAIL"):          # CREAITE_HC_SHOW_XFAIL=1: run it as a plain check to see why it fails
            return fn
        fn.__doc__ = (fn.__doc__ or "") + f" [expected failure: dev/proposals/{CHAIN[key]} is not in this tree]"
        return unittest.expectedFailure(fn)
    return wrap


def known(why):
    """A finding of Team Cap's the line still has (24-10-2026): an expected failure with its reason. Fixed, the check passes, which
    unittest reports as an unexpected success: take the mark off then."""
    def wrap(fn):
        if os.environ.get("CREAITE_HC_SHOW_XFAIL"):
            return fn
        fn.__doc__ = (fn.__doc__ or "") + f" [expected failure: {why}]"
        return unittest.expectedFailure(fn)
    return wrap


@contextmanager
def width(case, w, h=900):
    """The window at `w` x `h` for the block, put back at the class's size after."""
    measure.width(case.b, w, h)
    try:
        yield
    finally:
        measure.width(case.b, case.width, case.height)


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# The engine without a browser (as test_v262.py's Engine262: the same members, so a check reads the same in both)
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class Engine266(HandcheckCase):
    """Checks that need the vault (and sometimes its server) but not a browser. Own vault; no server unless `with_server`."""
    own_vault = True
    with_server = False
    claude = None                        # the path of a stand-in Claude for the server (default: the hand-check vault's)

    @classmethod
    def start_server(cls):
        import handcheck
        s = hcbase.session() or handcheck.Session(os.environ["CREAITE_HC_DIR"])
        if not s.zip and os.environ.get("CREAITE_HC_ZIP"):
            s.zip = Path(os.environ["CREAITE_HC_ZIP"])
        cls._hc, cls.v, cls.proc, cls.base = s, None, None, None
        cls.vault = s.make_vault(f"vault-{cls.__name__}")
        cls.now = os.environ.get("CREAITE_HC_NOW") or s.now
        cls.prepare()
        if cls.with_server:
            cls.proc, cls.base = cls.spawn()

    @classmethod
    def prepare(cls):
        """Anything to put in the vault before its server starts."""

    @classmethod
    def spawn(cls):
        """The live server on a free port, as Session.start_server starts it, with this class's own Claude."""
        import time
        import proc_guard
        from live_browser import free_port
        s, root = cls._hc, cls.vault
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        env = {**os.environ, **s.server_env(root, port)}
        if cls.claude:
            env["CREAITE_CLAUDE"] = str(cls.claude)
        with open(s.dir / f"server-{root.name}.log", "ab") as logf:
            proc = proc_guard.spawn([sys.executable, str(root / "system/scripts/live_server.py")], cwd=root, env=env, stdout=logf,
                                    stderr=subprocess.STDOUT)
        deadline = time.time() + 40
        while True:
            try:
                urllib.request.urlopen(base + "/health", timeout=1)
                return proc, base
            except OSError:
                if time.time() > deadline or proc.poll() is not None:
                    proc_guard.stop(proc, grace=5)
                    raise RuntimeError("the live server didn't answer; see " + str(s.dir / f"server-{root.name}.log")) from None
                time.sleep(0.2)

    def setUp(self):                                                 # no browser
        n = self.check_number()
        if only() and n not in only():
            self.skipTest("not in --only")

    def run_py(self, code, env=None):
        """Python in the vault (its system/scripts on the path, the clock pinned), isolated; (exit code, output)."""
        r = subprocess.run([sys.executable, "-I", "-c", "import sys, json\nsys.path.insert(0, 'system/scripts')\n" + code], cwd=self.vault,
                           capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": self.now or "", "TZ": "UTC", **(env or {})})
        return r.returncode, r.stdout + r.stderr

    def py(self, code, env=None):
        """The JSON the code prints (its last line)."""
        rc, out = self.run_py(code, env)
        self.assertEqual(rc, 0, out[-600:])
        return json.loads(out.strip().splitlines()[-1])

    def sql(self, query, *args):
        return db_rows(self.vault, query, *args)

    def staging(self, name=""):
        return self.vault / "system/staging" / name

    def page_token(self):
        """The token the open page carries (the server writes it into the page)."""
        html = urllib.request.urlopen(self.base + "/", timeout=30).read().decode("utf-8")
        return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    def post(self, path, body=None, token=True, page=True):
        """POST as the open page does: (HTTP status, JSON answer). A fault gives its status, never an exception."""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Creaite-Token"] = self.page_token()
        if page:
            headers["Sec-Fetch-Site"] = "same-origin"
            headers["Origin"] = self.base
        req = urllib.request.Request(self.base + path, data=json.dumps(body if body is not None else {}).encode(), method="POST",
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
                try:
                    return r.status, json.loads(raw or b"{}")
                except ValueError:                       # a server-sent stream (an ask that ran): the lines, not one document
                    return r.status, {"stream": raw.decode("utf-8", "replace")}
        except urllib.error.HTTPError as e:
            with e:
                raw = e.read()
            try:
                return e.code, json.loads(raw or b"{}")
            except ValueError:
                return e.code, {}

    def set_setting(self, *path_and_value):
        """Set a nested setting in the vault's settings.json (the server reads it at each call); returns what it was."""
        *path, value = path_and_value
        f = self.vault / "system/config/settings.json"
        cfg = json.loads(f.read_text(encoding="utf-8"))
        node = cfg
        for k in path[:-1]:
            node = node.setdefault(k, {})
        was = node.get(path[-1], "__absent__")
        node[path[-1]] = value
        f.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        return was

    # ── pending proposals of the check's own (what cx-sweep and cx-minutes stage) ──

    _n = 0

    def day(self):
        return (self.now or str(date.today()))[:10]

    def mail_proposal(self, descs, project="FAL"):
        """A pending mail proposal, one new action per description, numbered 1..n. Returns its name."""
        Engine266._n += 1
        day = self.day()
        name = f"proposed-{day}-{10 + Engine266._n:02d}00-sweep-hc266-{Engine266._n}.json"
        due = (date.fromisoformat(day) + timedelta(days=30)).isoformat()
        mail = ("Email · From: Priya Nair <priya.nair@meridian.example> · Subject: Harbour works · Sent: %s 09:00 · "
                "Link: https://outlook.example.test/owa/?ItemID=hc266-%d" % (day, Engine266._n))
        items = [{"n": k, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
                  "values": {"project": project, "description": d, "owner": "Sara Khan", "due_date": due, "source": mail}}
                 for k, d in enumerate(descs, 1)]
        self.staging(name).write_text(json.dumps({"created": f"{day}T09:00:00", "source_run": "cx-sweep", "files": [], "items": items}, indent=2),
                                      encoding="utf-8")
        return name

    def minutes_proposal(self, descs):
        """A pending minutes proposal (a meeting block and one new action per description). Returns its name."""
        name = self.mail_proposal(descs)
        p = self.staging(name)
        data = json.loads(p.read_text(encoding="utf-8"))
        day = self.day()
        data.update(source_run="cx-minutes", meeting={"key": f"fal-steering-{day}-{Engine266._n}", "title": "Steering", "project": "FAL",
                                                      "projects": ["FAL"], "date": day, "minutes_decision": "pending", "file_ops": [],
                                                      "draft": f"system/staging/drafts/{day} Steering.html"})
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return name

    def minutes_record(self, extra_items, title="Harbour review"):
        """Minutes as cx-minutes stages them (minutes.py stage, a creaite minutes page): one new action and `extra_items`. Returns the name."""
        day = self.day()
        transcript = f"inbox/{day} {title}.vtt"
        (self.vault / transcript).write_text("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning all, first the supplier.</v>\n\n"
                                             "00:00:05.000 --> 00:00:09.000\n<v Sara Khan>I will send the revised plan next week.</v>\n", encoding="utf-8")
        new = {"table": "actions", "values": {"project": "FAL", "description": "Chase the supplier", "owner": "Sara Khan", "due_date": "2030-06-10"}}
        spec = self.staging("drafts/hc266-meeting.json")
        spec.write_text(json.dumps({"title": title, "date": day, "projects": ["FAL"], "transcript": transcript,
                                    "minutes": {"start": "10:00", "end": "11:00", "summary": ["The committee met."], "chat": False},
                                    "items": [new, *extra_items]}), encoding="utf-8")
        before = set(hcbase.pending_proposals(self.vault))
        code, out = self.run_in_vault("minutes.py", "stage", "system/staging/drafts/hc266-meeting.json")
        self.assertEqual(code, 0, out[-500:])
        found = sorted(set(hcbase.pending_proposals(self.vault)) - before)
        self.assertEqual(len(found), 1, out[-300:])
        return found[0]

    def decisions(self, name):
        return {i["n"]: i["decision"] for i in json.loads(self.staging(name).read_text(encoding="utf-8"))["items"]}

    def fingerprint(self, name, ref):
        """The 12-hex fingerprint the page sends as `expect`: of item `ref`, or of the meeting block when ref is "meeting"."""
        return self.py("import build_dashboard as b, json\nd = json.load(open('system/staging/%s'))\n"
                       "ref = %s\nprint(json.dumps(b.block_fp(d[ref]) if isinstance(ref, str) else "
                       "b.item_fp(next(i for i in d['items'] if i['n'] == ref))))" % (name, json.dumps(ref)))

    def minutes_body(self, name, own=()):
        """What the page sends with Approve minutes (#345): the minutes' fingerprint (`expect`) and one for every item it will approve
        (`expects`, {number as text: fingerprint}): the group's and the ticked ones in `own`."""
        return self.py("import build_dashboard as b, review, json\nd = json.load(open('system/staging/%s'))\nown = %s\n"
                       "print(json.dumps({'expect': b.block_fp(d['meeting']), 'expects': {str(i['n']): b.item_fp(i) for i in d['items'] "
                       "if review.minutes_group(i) == 'group' or i['n'] in own}}))" % (name, json.dumps(list(own))))

    def take_out(self, name, text):
        """Take an item out of a proposal and number the rest again (the list moves on under an open page)."""
        f = self.staging(name)
        d = json.loads(f.read_text(encoding="utf-8"))
        d["items"] = [i for i in d["items"] if i["values"]["description"] != text]
        for k, it in enumerate(d["items"], 1):
            it["n"] = k
        f.write_text(json.dumps(d), encoding="utf-8")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# The page (the shared hand-check vault and Chrome)
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class Design266(HandcheckCase):
    """Checks 1 to 7: #337, the design fixes, measured in the live app at 900 and 1400 px."""

    def test_c01_settings_tick_labels_keep_room(self):
        """1. (#337) Settings rows with tick-box groups (Weekend, What the check reads, Week ahead shows) keep a label at least 220 px wide
        at 900 px as at 1400 px (they were 116 and 42 px at 900)."""
        b, seen = self.b, {}
        for w in (900, 1400):
            with width(self, w):
                got = []
                for tab in ("settings-essentials", "settings-work", "settings-advanced"):
                    self.screen(tab)
                    got += b.eval("[...document.querySelectorAll('.setticks')].filter(t=>t.getClientRects().length)"
                                  ".map(t=>Math.round(t.closest('.srow').firstElementChild.getBoundingClientRect().width))")
                seen[w] = got
                self.assertTrue(got, f"no tick-box row was drawn at {w} px")
                self.assertGreaterEqual(min(got), 220, f"a tick-box row's label is {min(got)} px wide at {w} px: {got}")
        self.note(1, f"{len(seen[900])} tick rows: narrowest label {min(seen[900])} px at 900, {min(seen[1400])} px at 1400")

    LINES = """((col)=>[...document.querySelectorAll('#actTbl tbody tr[data-row]')].slice(0, 40).map(r=>{ const c=r.children[col];
      const g=document.createRange(); g.selectNodeContents(c); const t=[...g.getClientRects()].filter(x=>x.width>1).map(x=>x.top);
      const lines=t.length&&Math.max(...t)-Math.min(...t)>8?2:1;       // one line: every piece of text starts within 8 px of the others
      return {lines, row:Math.round(r.getBoundingClientRect().height), text:c.innerText.trim()}; }))"""

    def test_c02_activity_by_column_does_not_wrap(self):
        """2. (#337) On Activity the By column stays on one line at 900 px and at 1400 px, "Rejected in review" among them (it wrapped, so
        the rows were 57 px tall instead of 49); a row whose description is one line is no taller than 52 px."""
        b = self.b
        tall = {}
        for w in (900, 1400):
            with width(self, w):
                self.screen("activity")
                b.wait("document.querySelector('#actTbl tbody tr[data-row]')", 15)
                self.assertEqual(b.eval("getComputedStyle(document.querySelector('#actTbl tbody tr td:nth-child(4)')).whiteSpace"), "nowrap")
                by = b.eval(self.LINES + "(3)")
                what = b.eval(self.LINES + "(2)")
                self.assertTrue(by)
                self.assertTrue(all(x["lines"] == 1 for x in by), f"the By cell wraps at {w} px: {[x['text'] for x in by if x['lines'] > 1]}")
                b.eval("(()=>{ const c=document.querySelector('#actTbl tbody tr[data-row]').children[3]; window.__by=c.innerHTML; c.textContent='Rejected in review'; return true; })()")
                self.assertEqual(b.eval(self.LINES + "(3)")[0]["lines"], 1, f"'Rejected in review' wraps at {w} px")
                b.eval("document.querySelector('#actTbl tbody tr[data-row]').children[3].innerHTML=window.__by; true")
                single = [x["row"] for x in what if x["lines"] == 1]
                self.assertTrue(single, "no row has a one-line description")
                self.assertLessEqual(max(single), 52, f"a one-line row is {max(single)} px tall at {w} px")
                tall[w] = max(single)
        self.note(2, f"By stays on one line, 'Rejected in review' too; one-line rows {tall[900]} px at 900, {tall[1400]} px at 1400")

    def test_c03_pencils_contrast_targets_and_chart_text(self):
        """3. (#337) On the cockpit the edit pencils reach 3:1 against what is behind them in light and dark (2.49:1 before), are 24 px
        targets, and no chart text is under 12 px (rendered)."""
        b = self.b
        worst = {}
        for mode in ("light", "dark"):
            measure.theme(b, "creaite", mode)
            self.screen("cockpit")
            b.wait("document.querySelector('.card.edt .pencil')", 15)
            rows = measure.paint_contrast(b, ".card.edt .pencil", "color") or []
            rows = [r for r in rows if r.get("ratio")]
            self.assertTrue(rows, "no pencil was drawn")
            worst[mode] = min(r["ratio"] for r in rows)
            self.assertGreaterEqual(worst[mode], 3.0, f"a pencil is {worst[mode]}:1 in {mode} mode")
            small = b.eval("[...document.querySelectorAll('.card.edt .pencil')].filter(e=>e.getBoundingClientRect().width)"
                           ".map(e=>e.getBoundingClientRect()).filter(r=>r.width<24||r.height<24).length")
            self.assertEqual(small, 0, "a pencil is under 24 px")
            sizes = b.eval("[...document.querySelectorAll('#v-cockpit svg text')].filter(e=>e.getBoundingClientRect().width)"
                           ".map(e=>Math.round(parseFloat(getComputedStyle(e).fontSize)*e.getScreenCTM().a*100)/100)")
            self.assertTrue(sizes, "no chart text was drawn")
            self.assertGreaterEqual(min(sizes), 12, f"chart text is {min(sizes)} px in {mode} mode")
        measure.theme(b, "creaite", "light")
        self.note(3, f"pencil {worst['light']}:1 light, {worst['dark']}:1 dark; targets 24 px; chart text 12 px or more")

    def people(self, w):
        """The People table drawn at `w` px: the box and the table's sizes."""
        b = self.b
        self.screen("people")
        b.wait("document.querySelector('#peopleTbl table tbody tr')", 15)
        return b.eval("(()=>{ const c=document.querySelector('#peopleTbl'), t=c.querySelector('table'), h=[...t.querySelectorAll('th')].find(x=>/Overdue/.test(x.textContent));"
                      "return {table:t.scrollWidth, box:c.clientWidth, overdue:h?Math.round(h.getBoundingClientRect().right-c.getBoundingClientRect().left):null,"
                      "page:document.scrollingElement.scrollWidth-innerWidth}; })()")

    def test_c04_people_fits_and_overdue_is_on_screen(self):
        """4. (#337) People at 900 px and at 1400 px: the table fits its box (no sideways scroll, it was 1392 px wide in a 775 px box) and
        Overdue, the column it sorts by, is on screen."""
        out = {}
        for w in (900, 1400):
            with width(self, w):
                m = self.people(w)
                self.assertIsNotNone(m["overdue"], "no Overdue column")
                self.assertLessEqual(m["table"], m["box"] + 1, f"the table is {m['table']} px in a {m['box']} px box at {w} px")
                self.assertLessEqual(m["overdue"], m["box"], f"Overdue ends {m['overdue']} px in, past the {m['box']} px box at {w} px")
                self.assertLessEqual(m["page"], 0, f"the page scrolls sideways at {w} px")
                out[w] = m
        self.note(4, f"table {out[900]['table']} of {out[900]['box']} px at 900, {out[1400]['table']} of {out[1400]['box']} px at 1400; Overdue on screen")

    BROKEN_WORDS = """(()=>{ const out=[], root=document.querySelector('#peopleTbl');
      const w=document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      for (let n; (n=w.nextNode()); ) {
        if (!n.parentElement.getClientRects().length) continue;
        const re=/[^\\s]+/g; let m;
        while ((m=re.exec(n.data))) {
          if (/[-\\/@.:,;()]/.test(m[0]) || m[0].length<5) continue;          // a word with its own break point, or too short to break
          const r=document.createRange(); r.setStart(n,m.index); r.setEnd(n,m.index+m[0].length);
          const rects=[...r.getClientRects()]; if (rects.length<2) continue;
          if (Math.max(...rects.map(x=>x.top))-Math.min(...rects.map(x=>x.top))>4) out.push(m[0]);
        } }
      return out; })()"""

    def test_c05_people_words_do_not_break_in_the_middle(self):
        """5. (#337) People at 900 px and at 1400 px is readable: no ordinary word is broken across two lines in the middle ("Programm/e",
        "Spon/sor", "organisatio/n")."""
        found = {}
        for w in (900, 1400):
            with width(self, w):
                self.people(w)
                found[w] = self.b.eval(self.BROKEN_WORDS)
        self.note(5, f"words broken in the middle: {len(found[900])} at 900, {len(found[1400])} at 1400 ({', '.join(sorted(set(found[900]))[:4])})")
        self.assertEqual(found, {900: [], 1400: []}, f"words broken in the middle: {found}")

    ORG_ROLE_WORDS = """(()=>{ const t=document.querySelector('#peopleTbl table'), heads=[...t.querySelectorAll('th')];
      const cols=['Organisation','Role'].map(n=>({n, i:heads.findIndex(h=>h.textContent.trim().toLowerCase().indexOf(n.toLowerCase())===0)}));
      const out=[], seen=[];
      const broken=(node, tag)=>{ const re=/[^\\s]+/g; let m;
        while ((m=re.exec(node.data))) {
          if (/[-\\/@.:,;()]/.test(m[0]) || m[0].length<5) continue;
          const r=document.createRange(); r.setStart(node,m.index); r.setEnd(node,m.index+m[0].length);
          const rects=[...r.getClientRects()]; if (rects.length<2) continue;
          if (Math.max(...rects.map(x=>x.top))-Math.min(...rects.map(x=>x.top))>4) out.push(tag+': '+m[0]);
        } };
      for (const c of cols) { if (c.i<0 || !heads[c.i].getClientRects().length) continue; seen.push(c.n);
        for (const cell of [heads[c.i], ...[...t.querySelectorAll('tbody tr')].map(r=>r.children[c.i]).filter(Boolean)]) {
          const w=document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
          for (let n; (n=w.nextNode()); ) if (n.parentElement.getClientRects().length) broken(n, c.n); } }
      return {seen, out}; })()"""

    def test_c34_people_organisation_and_role_do_not_break_in_the_middle(self):
        """34. (#343 M1) People at 900 px and at 1400 px: the Organisation and Role columns, their headings included, keep a word on one
        line (the heading was "ORGANISATIO/N" at 1400 px). A sibling of check 5, which looks at every word of the table; this one
        looks at the two columns Team Cap named and says which column broke. (Fixed on the line at 72de4a6a; a plain check.)"""
        found = {}
        for w in (900, 1400):
            with width(self, w):
                self.people(w)
                got = self.b.eval(self.ORG_ROLE_WORDS)
                self.assertEqual(sorted(got["seen"]), ["Organisation", "Role"], f"the two columns are on screen at {w} px: {got}")
                found[w] = got["out"]
        self.note(34, f"Organisation and Role words broken in the middle: {len(found[900])} at 900, {len(found[1400])} at 1400 ({', '.join(sorted(set(found[900] + found[1400]))[:4])})")
        self.assertEqual(found, {900: [], 1400: []}, f"words broken in the middle in Organisation or Role: {found}")

    def milestones_client(self, code, hidden):
        """The Client view of project `code`'s Milestones page and its cockpit card with its milestones cut down to `hidden` (all of them
        internal), as the page's own data: returns (the page's message, the card's message). The data is put back after."""
        b = self.b
        b.eval(f"window.__ms = P.find(x=>x.code==={code!r}).ms; P.find(x=>x.code==={code!r}).ms = window.__ms.slice(0, {hidden}).map(m=>m.slice()); true")
        try:
            b.eval("MVAUD='cli'; try{ localStorage.setItem('creaite.cockpit.milestones.view','cli'); }catch(e){} true")
            b.eval(f"mvOpenPage({code!r},'plan')")
            b.wait("VIEW==='milestones'&&document.querySelector('#v-milestones .mv-card')", 15)
            page = b.eval("(document.querySelector('#v-milestones .mv-none')||{}).textContent||''").strip()
            b.eval(f"MVAUD='cli'; go('cockpit',{code!r})")
            b.wait("document.getElementById('mvCard')", 15)
            card = b.eval("(document.querySelector('#mvCard .mv-none')||{}).textContent||''").strip()
            return page, card
        finally:
            b.eval(f"P.find(x=>x.code==={code!r}).ms = window.__ms; MVAUD='int'; true")

    def test_c06_client_view_with_several_hidden_milestones_says_so(self):
        """6. (#337) The Client view of a project whose milestones are all internal says "None of the N milestones are shown to the client
        yet. Switch to Internal view to see them." on the Milestones page and on the cockpit card, not "0 achieved, 0 to come." over an
        empty line; the Internal view still draws the plan."""
        b = self.b
        total = b.eval("P.find(x=>x.code==='FAL').ms.filter(m=>m[3]).length")
        self.assertGreaterEqual(total, 2, "the demo's FAL has several milestones")
        page, card = self.milestones_client("FAL", total)
        want = f"None of the {total} milestones are shown to the client yet. Switch to Internal view to see them."
        self.assertTrue(page.startswith(want), page)
        self.assertTrue(card.startswith(want), card)
        self.assertNotIn("0 achieved", b.eval("document.querySelector('#v-cockpit').textContent"))
        two, _ = self.milestones_client("FAL", 2)
        self.assertTrue(two.startswith("None of the 2 milestones are shown"), two)
        b.eval("MVAUD='int'; mvOpenPage('FAL','plan')")
        b.wait("VIEW==='milestones'&&document.querySelector('#v-milestones .mv-card')", 15)
        self.assertFalse(b.eval("!!document.querySelector('#v-milestones .mv-none')"), "the Internal view draws the plan")
        self.note(6, f"{total} hidden milestones: '{page[:60]}…' on the page and the card; two: 'None of the 2 milestones…'")

    def test_c07_client_view_with_one_hidden_milestone_says_it_is_not_shown(self):
        """7. (#337) With ONE milestone, all internal, the Client view says it is NOT shown ("The milestone is not shown to the client yet.
        Switch to Internal view to see it."), on the page and on the cockpit card. (Team Cap H1 found it reading "is shown"; fixed on the
        line at 7e10355b, so this is a plain check.)"""
        page, card = self.milestones_client("FAL", 1)
        self.note(7, f"page says: '{page[:70]}'")
        for where, text in (("page", page), ("card", card)):
            self.assertTrue(text, f"no message on the {where}")
            self.assertRegex(text, r"(?i)\b(isn['’]t|is not|not)\b[^.]*\bshown to the client", f"on the {where}: {text}")
            self.assertNotRegex(text, r"(?i)milestone is shown", f"on the {where}: {text}")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# Plain words (#292, #293)
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

# What a person must never read on screen (dev/PLAIN-WORDS.md "Banned in user-visible text"), outside Diagnostics and the stopped alert.
# A name the user typed or a file they own (an item called "Confirm tester access to staging", a transcript called "….vtt") is their
# data, not creaite's words, so the file-name and "staging" patterns of the glossary are not applied to what is on screen.
BANNED = [
    ("a script or skill name", r"\b(?:cx-[a-z]+|tracker\.py|review\.py|live_server|filechange|propose\.py|system/scripts/run)\b"),
    ("sweep", r"\bswe(?:ep|ept|eping)\b"),
    ("proposal", r"\bproposals?\b|\bproposed\b"),
    ("staged", r"\bstaged\b|\bStage for\b"),
    ("vault", r"\bvault\b"),
    ("live server", r"\blive server\b"),
    ("extraction", r"\bextract(?:ion|ed|ing)?\b|\bre-extract"),
    ("apply (the app's own word)", r"\bApply (?:stopped|n )|\bApplied\b(?! to)|\bApply\b(?! to\b)"),
]
PATHS = r"\b(?:system|projects|inbox)/[\w.-]|(?:^|\s)\.claude/|_portfolio"
# Walked: the pages Alan's checklist names (#292), each as the shared hand-check vault draws it
WALK = ["today", "work", "intake-review", "files", "activity", "projects", "cockpit", "milestones", "people", "person",
        "project-settings", "settings-essentials", "settings-work", "settings-advanced", "settings-health"]
# Where the words are allowed: the stopped alert and Settings › Diagnostics (PLAIN-WORDS "glossary exception"), found by their ids
DIAG = "#diagCard, #diagnostics, [data-sec=diagnostics], #liveAlert, #staleAlert, .diag"


class Words266(HandcheckCase):
    """Checks 8, 9 and 11: #292 and #293, plain words."""

    TEXT = """((skip, only)=>{ const roots=only?[...document.querySelectorAll(only)]:[document.body], seen=[], skipEls=skip?[...document.querySelectorAll(skip)]:[];
      const visible=e=>e.getClientRects().length>0 && !skipEls.some(s=>s.contains(e)), within=e=>roots.some(r=>r.contains(e));
      for (const root of roots) { const w=document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        for (let n; (n=w.nextNode()); ) { const t=n.data.trim(); if (t && n.parentElement && !/^(SCRIPT|STYLE)$/.test(n.parentElement.tagName) && visible(n.parentElement)) seen.push(t); } }
      for (const e of document.querySelectorAll('[data-tip],[aria-label],[title],[placeholder]')) if (visible(e) && within(e))
        for (const a of ['data-tip','aria-label','title','placeholder']) { const v=e.getAttribute(a); if (v) seen.push(v); }
      return seen; })"""
    # Settings › Health: #292 asks for plain titles, summaries, buttons and "what it does" lines; a check's detail line (.d) is the doctor's own text
    HEALTH_PLAIN = "#healthCard .hsum, #healthCard .hrow .t, #healthCard .hrow .hdoes, #healthCard .hrow button, #healthCard .hhead"

    def walk(self, rules, details=False):
        """The offending pieces of text on the walked screens: [“screen: rule: text”], and how many pieces were read. Health's detail
        lines are read only with `details`."""
        b, bad, drawn = self.b, [], 0
        for name in WALK:
            self.screen(name)
            b.pump(0.3)
            only = self.HEALTH_PLAIN if name == "settings-health" and not details else None
            texts = b.eval(self.TEXT + "(%s, %s)" % (json.dumps(DIAG), json.dumps(only)))
            drawn += len(texts)
            for t in texts:
                for label, rx in rules:
                    m = re.search(rx, t)
                    if m:
                        bad.append(f"{name}: {label}: “{t[max(0, m.start() - 30):m.end() + 30]}”")
        return bad, drawn

    def test_c08_the_words_on_screen_are_plain(self):
        """8. (#292) Walk Today, Work, Intake, Files, Activity, Projects, a cockpit, a milestones page, People, a person, a project's
        Settings and every Settings tab (Health: its titles, summary and buttons): in the words on screen, in its tips and labels, there is no script or skill name, no "sweep", and
        none of proposal, staged, vault, live server, extract or Apply as the app's own word. (The stopped alert and Settings ›
        Diagnostics are the glossary exception; a name or a file the user typed or owns is theirs.)"""
        bad, drawn = self.walk(BANNED)
        self.note(8, f"{len(WALK)} screens, {drawn} pieces of text read; {len(bad)} offending")
        self.assertEqual(bad, [], "words a person should not read:\n  " + "\n  ".join(bad[:25]))

    @known("#292's checklist (no file path anywhere on screen): Files' tooltip on the portfolio folder says projects/_portfolio, the "
           "project's Settings page prints projects/<folder>, and Health's detail lines name system/scripts/run … commands")
    def test_c26_no_file_path_is_on_screen(self):
        """26. (#292) On the same screens no file path is shown (nothing like projects/…, system/… or inbox/…, in text, tips or labels)."""
        bad, drawn = self.walk([("a file path", PATHS)], details=True)
        self.note(26, f"{drawn} pieces of text read; paths: {bad}")
        self.assertEqual(bad, [], "file paths on screen:\n  " + "\n  ".join(bad))

    RENAMED = [  # (the new words, the old ones): Help's source and its page (dev/PLAIN-WORDS.md, the 2.6.4 Help diff)
        ("Review and approve suggestions", "Review and approve proposals"),
        ("Mail and Teams not checked yet today", "Sweep due since 07:00"),
        ("Check now", "Run sweep"),
        ("Run the first check", "Run the first sweep"),
        ("Search everything", "Search the vault"),
        ("Turn a note into project record changes", "Turn a note into tracker changes"),
        ("Daily check time", "Sweep time"),
        ("your project record", "the tracker"),
    ]

    def test_c09_help_uses_the_new_words_and_not_the_old_ones(self):
        """9. (#293) Help (its text in the vault, and the page) has the plain words (Review and approve suggestions, Mail and Teams not
        checked yet today, Check now, Run the first check, Search everything, Turn a note into project record changes, Daily check time,
        your project record) and none of the old (…proposals, Sweep due since 07:00, Run sweep, Run the first sweep, Search the vault,
        …tracker changes, Sweep time, the tracker). The commands `sweep`, `apply` and `process new minutes` stay in their command table."""
        b = self.b
        md = (self.vault / "system/templates/help.md").read_text(encoding="utf-8") if (self.vault / "system/templates/help.md").is_file() else \
            (REPO / "system/templates/help.md").read_text(encoding="utf-8")
        self.screen("help")
        page = b.eval("document.getElementById('v-help').textContent")
        missing, left = [], []
        for new, old in self.RENAMED:
            if new not in md:
                missing.append(new)
            for where, text in (("help.md", md), ("the page", page)):
                if old in text and not (old == "the tracker" and where == "help.md"):      # the file's developer notes may name the old words
                    left.append(f"{where}: {old}")
        self.assertEqual(missing, [], f"Help lacks the new words: {missing}")
        self.assertEqual(left, [], f"Help still has the old words: {left}")
        for cmd in ("process new minutes", "`sweep`", "`apply`"):
            self.assertIn(cmd, md, f"the old command {cmd} is still in the command table")
        self.note(9, f"{len(self.RENAMED)} renamed words found, none of the old left, in the file and on the page")


class Commands266(Engine266):
    """Check 11. The server's own wording code, run in the vault."""

    def test_c11_old_chat_commands_still_start_their_jobs_and_the_plain_ones_are_taught(self):
        """11. (#293) ask creaite still takes the old words for a mail and Teams check (`sweep`, `sweep mail for ABC`, `refresh calendar`)
        as a plain check that runs at once, and takes the plain ones too (`check my mail`, `check my mail and Teams`, `check mail for
        ABC`); a question is not a check; the server decides this from the words, never the model; and Help teaches the plain words."""
        r = self.py("""
import live_server as ls
words = ["sweep", "sweep mail", "sweep mail for ABC", "refresh calendar", "check my mail", "check my mail and Teams", "check mail for ABC",
         "what is due on Friday", "check my mail and approve everything", "check my mail for urgent"]
print(json.dumps({w: bool(ls.panel_sweep(w, [], None)) for w in words}))""")
        for w in ("sweep", "sweep mail", "sweep mail for ABC", "refresh calendar", "check my mail", "check my mail and Teams", "check mail for ABC"):
            self.assertTrue(r[w], f"“{w}” no longer starts the check: {r}")
        for w in ("what is due on Friday", "check my mail and approve everything", "check my mail for urgent"):
            self.assertFalse(r[w], f"“{w}” is treated as a plain check: {r}")
        md = (self.vault / "system/templates/help.md").read_text(encoding="utf-8")
        self.assertIn("`check my mail`", md, "Help does not teach the plain words")
        for old in ("`sweep`", "`apply`", "`process new minutes`"):
            self.assertIn(old, md, f"the old command {old} left Help's command table")
        self.note(11, "sweep, sweep mail, refresh calendar, check my mail and check my mail and Teams all start the check; a question and 'and approve' do not")


class Item266(HandcheckCase):
    """Check 10. A vault of its own: the edit stages a change."""
    own_vault = True

    @known("Team Cap H2: panel.js pkLast (and pkSaving) says 'Saved for Review' for an edit that is already approved and waits for the Save button")
    def test_c10_an_edit_that_waits_for_save_does_not_say_saved_for_review(self):
        """10. (#292) Change the priority of an open work item: the panel says the change is waiting to be saved ("1 change waiting to be
        saved … Nothing is saved until you press Save"), and the header does not say "Saved for Review" while nothing is saved."""
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')", 15)
        id_ = b.eval("A.find(a=>a.p==='FAL'&&OPENST(a.st)&&a.pr!=='Low').id")
        b.eval(f"openRecord('actions', {id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')", 15)
        b.pump(0.3)
        b.click('#panel [data-pkp="pr"]')
        b.wait("document.querySelector('.pkpop')", 10)
        b.eval("[...document.querySelectorAll('.pkpop .pkopt')].find(o=>o.querySelector('span').firstChild.textContent==='Low').click()")
        b.wait("PKS.length===1", 15)
        b.pump(0.4)
        head = b.eval("(document.getElementById('pkSave')||{}).textContent||''").strip()
        bar = b.eval("(document.getElementById('pkStage')||{}).textContent||''").strip()
        self.note(10, f"header: '{head}'; bar: '{' '.join(bar.split())[:90]}'")
        self.assertIn("Nothing is saved until you press Save", bar, "the bar says the change waits for Save")
        self.assertNotIn("Saved for Review", head, f"the header says '{head}' while nothing is saved")
        self.assertNotIn("Saved for Review", b.eval("(document.getElementById('pkLast')||{}).textContent||''"))


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# #333: the minutes flow's low-severity bundle
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class Figures266(HandcheckCase):
    """Checks 12 and 13: the figure check (minutesDoc.js figuresMissing), run in the page."""

    def figs(self, text, said):
        """figuresMissing(text, said), the page's own function (minutesDoc.js, as the zip is built from this checkout), run in the browser."""
        js = (DASH / "components/minutes/minutesDoc.js").read_text(encoding="utf-8")
        code = js[js.index("const FIGURE ="):js.index("\n}\n", js.index("export function figuresMissing")) + 3].replace("export function", "function")
        return self.b.eval("(()=>{ %s\nreturn figuresMissing(%s, %s); })()" % (code, json.dumps(text), json.dumps(said)))

    def test_c12_a_date_said_in_words_is_not_flagged_and_another_day_is(self):
        """12. (#333) A minutes line with the date 20-11-2026 is not flagged when the transcript says "the 20th of November" or "November
        20" or the date in numbers; it is flagged, as one figure (never split into 20, 11 and 2026), when the transcript says another day
        or none; other figures are still checked."""
        self.assertEqual(self.figs("Send the pack by 20-11-2026", "I'll send it by the 20th of November"), [])
        self.assertEqual(self.figs("Send the pack by 20-11-2026", "by November 20"), [])
        self.assertEqual(self.figs("Send the pack by 20-11-2026", "by 20-11-2026"), [])
        self.assertEqual(self.figs("Send the pack by 20-11-2026", "by the 21st of November"), ["20-11-2026"])
        self.assertEqual(self.figs("Send the pack by 20-11-2026", "sometime soon"), ["20-11-2026"])
        self.assertEqual(self.figs("Budget 45 by 20-11-2026", "40, the 20th of November"), ["45"])
        self.note(12, "20th of November and November 20 say 20-11-2026; the 21st and 'soon' do not; 45 against 40 is flagged")

    @known("Team Cap L5: figuresMissing never checks the year when the day and month are said in words; 'may' (the verb) counts as the month")
    def test_c13_a_wrong_year_with_the_day_and_month_in_words_is_flagged(self):
        """13. (#333) A date whose day and month the transcript says in words but whose year it does not say is not taken as said:
        20-11-2027 against "the 20th of November" (the page's date has a year the speaker never gave) is flagged, and so is 05-05-2026
        against "we may need 5 testers" ("may" is a verb there, not the month)."""
        a = self.figs("Send the pack by 20-11-2027", "I'll send it by the 20th of November, 2026")
        b = self.figs("Review on 05-05-2026", "we may need 5 testers")
        self.note(13, f"20-11-2027 vs '20th of November, 2026': {a}; 05-05-2026 vs 'we may need 5 testers': {b}")
        self.assertEqual(a, ["20-11-2027"], "a year the speaker did not say passes")
        self.assertEqual(b, ["05-05-2026"], "'may' counted as the month")


class Extraction266(Engine266):
    """Check 14: the duplicate mark, the engine's own code in the vault."""

    def test_c14_another_projects_item_is_marked_a_possible_duplicate_only_on_a_close_match(self):
        """14. (#333) An item that shares some words with an open item in the same project is marked as a possible duplicate from
        score 0.5; the same score on an item of another project is not marked (only a close match, 0.75 or more, is)."""
        r = self.py("import extraction as e\nprint(json.dumps({'same_possible': e.worth_marking(True, 0.55), 'other_possible': "
                    "e.worth_marking(False, 0.55), 'other_close': e.worth_marking(False, 0.8), 'same_low': e.worth_marking(True, 0.3), "
                    "'very': e.VERY, 'possible': e.POSSIBLE}))")
        self.assertTrue(r["same_possible"], "same project, shared words: marked")
        self.assertFalse(r["other_possible"], "another project, shared words only: not marked")
        self.assertTrue(r["other_close"], "another project, a close match: marked")
        self.assertFalse(r["same_low"])
        self.assertLess(r["possible"], r["very"])
        self.note(14, f"possible from {r['possible']} in the same project, {r['very']} across projects")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# #345 and #346: guarded live_server.py
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

MISSING = "This page didn't say which item it meant"
CHANGED = "has changed since you looked at it"
BAD = "can't check which item that is"


class Routes266(Engine266):
    """Checks 16 and 17. A vault and its live server: pending proposals of the check's own, decided through the routes."""
    with_server = True

    def declined(self, res, which, what):
        self.assertFalse(res.get("ok"), f"{what}: {res}")
        self.assertIn(which, res.get("message", ""), f"{what}: {res}")
        self.assertNotRegex(res.get("message", ""), r"Traceback|\.py\b|proposed-|\.json", f"{what}: words a person can read")

    @needs("expect")
    def test_c16_every_route_that_decides_an_item_needs_its_fingerprint(self):
        """16. (#345) /api/review/reject, Approve instead (/api/review/rejected), /api/review/repeat, /api/review/retarget and
        /api/minutes/approve each refuse a request without `expect` (Approve minutes: also without `expects`, one for every item it
        approves), with a malformed one and with another item's (the list moved on) in one plain sentence, deciding nothing; the right one goes through to review.py; Undo and a new reason need none; several rows
        are all or none."""
        # reject
        name = self.mail_proposal(["Alpha lantern check", "Bravo anchor weigh", "Charlie gazebo paint"])
        fp = {k: self.fingerprint(name, k) for k in (1, 2, 3)}
        rows = [{"file": name, "ref": 1, "expect": fp[1]}, {"file": name, "ref": 2}]                 # one row has none
        code, res = self.post("/api/review/reject", {"rows": rows, "reason": "Chatter"})
        self.declined(res, MISSING, "reject, one row without expect")
        for bad, which in (("zz", BAD), (fp[1], CHANGED)):
            code, res = self.post("/api/review/reject", {"rows": [{"file": name, "ref": 2, "expect": bad}], "reason": "Chatter"})
            self.declined(res, which, f"reject with {bad}")
        self.assertEqual(self.decisions(name), {1: "pending", 2: "pending", 3: "pending"}, "nothing was decided")
        code, res = self.post("/api/review/reject", {"rows": [{"file": name, "ref": 1, "expect": fp[1]}, {"file": name, "ref": 3, "expect": fp[3]}],
                                                    "reason": "Chatter"})
        self.assertTrue(res.get("ok"), res)
        self.assertEqual(self.decisions(name), {1: "rejected", 2: "pending", 3: "rejected"})
        # Approve instead: needs the item's fingerprint; Undo needs none
        for row, which in (({"file": name, "ref": 1}, MISSING), ({"file": name, "ref": 1, "expect": "nope"}, BAD),
                           ({"file": name, "ref": 1, "expect": fp[2]}, CHANGED)):
            code, res = self.post("/api/review/rejected", {"rows": [row], "how": "approve"})
            self.declined(res, which, f"approve instead {row}")
            self.assertEqual(self.decisions(name)[1], "rejected")
        code, res = self.post("/api/review/rejected", {"rows": [{"file": name, "ref": 3}], "how": "undo"})
        self.assertTrue(res.get("ok"), f"Undo needs no expect: {res}")
        code, res = self.post("/api/review/rejected", {"rows": [{"file": name, "ref": 1, "expect": fp[1]}], "how": "approve"})
        self.assertTrue(res.get("ok"), res)
        self.assertEqual(self.decisions(name)[1], "approved")
        # repeat and retarget
        name2 = self.mail_proposal(["Delta kettle review", "Echo harbour survey"])
        before = self.staging(name2).read_bytes()
        fp2 = self.fingerprint(name2, 2)
        for path, extra in (("/api/review/repeat", {"how": "keep"}), ("/api/review/repeat", {"how": "merge"}),
                            ("/api/review/retarget", {"id": "FAL-A-001"})):
            self.declined(self.post(path, dict(file=name2, ref=2, **extra))[1], MISSING, path)
            self.declined(self.post(path, dict(file=name2, ref=2, expect="zz", **extra))[1], BAD, path)
            self.declined(self.post(path, dict(file=name2, ref=2, expect=self.fingerprint(name2, 1), **extra))[1], CHANGED, path)
        self.assertEqual(self.staging(name2).read_bytes(), before, "nothing changed")
        for path, extra in (("/api/review/repeat", {"how": "keep"}), ("/api/review/retarget", {"id": "FAL-A-001"})):
            res = self.post(path, dict(file=name2, ref=2, expect=fp2, **extra))[1]
            for words in (MISSING, CHANGED, BAD):
                self.assertNotIn(words, res.get("message", ""), (path, res))            # review.py answers (not a repeat; no such item)
        # Approve minutes: the minutes' fingerprint and one for every item it approves
        name3 = self.minutes_proposal(["Foxtrot ladder count"])
        before = self.staging(name3).read_bytes()
        body = {"file": name3, "group": True, "own": []}
        good = self.minutes_body(name3)
        self.assertTrue(good["expects"], "the minutes have a group item to name")
        self.declined(self.post("/api/minutes/approve", body)[1], MISSING, "approve minutes")
        self.declined(self.post("/api/minutes/approve", dict(body, expect="x", expects=good["expects"]))[1], BAD, "approve minutes")
        self.declined(self.post("/api/minutes/approve", dict(body, expect=self.fingerprint(name3, 1), expects=good["expects"]))[1], CHANGED,
                      "approve minutes, an item's")
        self.declined(self.post("/api/minutes/approve", dict(body, expect=good["expect"]))[1], MISSING, "approve minutes, no fingerprint for the item")
        self.declined(self.post("/api/minutes/approve", dict(body, expect=good["expect"], expects={k: "zz" for k in good["expects"]}))[1], BAD,
                      "approve minutes, a malformed item fingerprint")
        self.declined(self.post("/api/minutes/approve", dict(body, expect=good["expect"], expects={k: self.fingerprint(name3, "meeting") for k in good["expects"]}))[1],
                      CHANGED, "approve minutes, another's item fingerprint")
        self.assertEqual(self.staging(name3).read_bytes(), before, "the minutes were not touched")
        res = self.post("/api/minutes/approve", dict(body, **good))[1]
        for words in (MISSING, CHANGED, BAD):
            self.assertNotIn(words, res.get("message", ""), f"the minutes' own checks answer: {res}")
        # the list moved on under an open page: Bravo's number now names Charlie
        name4 = self.mail_proposal(["Golf meadow plan", "Hotel boat count", "India roof survey"])
        hotel = self.fingerprint(name4, 2)
        self.take_out(name4, "Golf meadow plan")
        code, res = self.post("/api/review/reject", {"rows": [{"file": name4, "ref": 2, "expect": hotel}], "reason": "Chatter"})
        self.declined(res, CHANGED, "reject after the list moved on")
        self.assertEqual(self.decisions(name4), {1: "pending", 2: "pending"}, "the item now in that place is not touched")
        self.note(16, "reject, Approve instead, repeat, retarget and Approve minutes: missing, malformed and another item's expect all refused "
                      "in plain words, nothing decided; the right one reaches review.py")

    @needs("expect")
    def test_c17_assign_names_the_item(self):
        """17. (#345) /api/review/assign, which moves a pending item to another project, refuses a request without `expect` and one with
        another item's, like the other routes: it moves nothing."""
        name = self.mail_proposal(["Juliet bell tower", "Kilo market stall"])
        fp1 = self.fingerprint(name, 1)
        for body, what in (({"file": name, "ref": 2, "code": "ORX"}, "no expect"), ({"file": name, "ref": 2, "code": "ORX", "expect": fp1}, "another item's")):
            code, res = self.post("/api/review/assign", body)
            projects = {i["n"]: i["values"]["project"] for i in json.loads(self.staging(name).read_text(encoding="utf-8"))["items"]}
            self.note(17, f"{what}: ok {res.get('ok')}; projects {projects}")
            self.assertFalse(res.get("ok"), f"assign with {what} moved the item: {res}")
            self.assertEqual(projects, {1: "FAL", 2: "FAL"}, f"assign with {what} moved an item")


    @known("#333 item 1, deferred by Stark (guarded review.py): _tick counts the rows ticked, not the items the apply wrote")
    def test_c15_the_toast_counts_the_items_the_apply_wrote(self):
        """15. (#333) After Approve minutes in which a ticked row is held back by the apply (an update to an item that is not there), the
        answer, which the toast reads ("n work items registered"), counts the items the apply wrote (1), not the rows that were ticked
        (2)."""
        name = self.minutes_record([{"op": "update", "table": "actions", "id": "FAL-A-001", "set": {"due_date": "2030-07-01"}, "why": "Sara said so"}])
        f = self.staging(name)
        d = json.loads(f.read_text(encoding="utf-8"))
        d["items"][1]["id"] = "FAL-A-999"                              # gone by the time of the apply
        f.write_text(json.dumps(d), encoding="utf-8")
        before = self.sql("SELECT count(*) AS n FROM actions")[0]["n"]
        code, res = self.post("/api/minutes/approve", dict({"file": name, "group": True, "own": []}, **self.minutes_body(name)))
        wrote = self.sql("SELECT count(*) AS n FROM actions")[0]["n"] - before
        self.note(15, f"ticked 2, the apply wrote {wrote} new item (and held the update back); the answer says approved {res.get('approved')}")
        self.assertTrue(res.get("ok"), res)
        self.assertEqual(wrote, 1)
        self.assertIn("Held in Review", res.get("message", ""), "the apply held the second row back")
        self.assertEqual(res.get("approved"), wrote, "the toast would say '%s work items registered'" % res.get("approved"))


class Runs266(Engine266):
    """Checks 18 and 19. The run engine's own code, run in the vault with a stand-in for the thread and the process."""

    PRE = """
import live_server as ls, types
from pathlib import Path
from unittest import mock
g = Path('system/guard')
"""

    @needs("runs")
    def test_c18_the_runs_chat_carries_nothing(self):
        """18. (#346) The day's "Runs creaite started" chat (runs-YYYY-MM-DD) is never marked as having read outside content and its lines
        hold a calendar title, so a fresh run in that chat carries nothing of it, in any letter case; another chat still carries its last
        lines."""
        r = self.py(self.PRE + """
title = 'Kick-off with Contoso Ltd (confidential)'
def chat(cid, text):
    ls.chat_file(cid).parent.mkdir(parents=True, exist_ok=True)
    ls.chat_file(cid).write_text(json.dumps({'messages': [{'who': 'you', 'text': text}, {'who': 'creaite', 'text': 'Prep page made'}]}), encoding='utf-8')
chat('runs-2026-10-24', title); chat('chat-one1', 'What is due on Friday?')
out = {'runs': ls.carry_over('runs-2026-10-24'), 'upper': ls.carry_over('RUNS-2026-10-24'), 'plain': ls.carry_over('chat-one1'),
       'named_runs': ls.carry_over('my-runs-chat')}
for cid in ('runs-2026-10-24', 'chat-one1'):
    p = ls.chat_file(cid)
    if p.exists(): p.unlink()
print(json.dumps(out))""")
        self.assertEqual(r["runs"], "", "the runs chat carries its lines")
        self.assertEqual(r["upper"], "", "RUNS- in capitals carries its lines")
        self.assertIn("What is due on Friday?", r["plain"], "an ordinary chat still carries its last lines")
        self.note(18, "runs- (any case) carries nothing; an ordinary chat still carries its last lines")

    @needs("setup")
    def test_c19_a_failed_run_set_up_leaves_no_record_and_the_server_is_not_busy(self):
        """19. (#346) When a run's set-up fails after its record was written (a thread that will not start), the record in the guard folder
        is taken away, the process already started is ended, the run is not left in the table, and the next ask is not answered
        "busy" (it stayed busy until the server was restarted)."""
        r = self.py(self.PRE + """
import tempfile
tmp = Path(tempfile.mkdtemp()); (tmp / 'chats').mkdir()
class Proc:
    stdout = stderr = None; pid = 999999
ended, started = [], []
def popen(cmd, **k):
    started.append(cmd); return Proc()
with mock.patch.object(ls.reach, 'GUARD', tmp), mock.patch.object(ls.reach, 'RUN_FILE', tmp / 'run.json'), \\
     mock.patch.object(ls.reach, 'SESSIONS_FILE', tmp / 'marked.json'), mock.patch.object(ls.paths, 'ASK_CHATS', tmp / 'chats'), \\
     mock.patch.object(ls, 'run_usage', lambda *a, **k: None), mock.patch.object(ls.subprocess, 'Popen', popen), \\
     mock.patch.object(ls, 'end_process', ended.append), mock.patch.object(ls.threading, 'Thread', side_effect=RuntimeError('no thread')):
    ls.RUNS.clear()
    try:
        ls.Run('r-failed266', 'hello', None, None, None, fresh=True)
        raised = False
    except RuntimeError:
        raised = True
    out = {'raised': raised, 'in_table': 'r-failed266' in ls.RUNS, 'busy': bool(ls.current_run() and not ls.current_run().done),
           'record': (ls.reach.guard_run() or {}).get('run'), 'ended': len(ended), 'started': len(started)}
print(json.dumps(out))""")
        self.note(19, f"set-up failed: {r}")
        self.assertTrue(r["raised"], "the set-up error reaches the caller")
        self.assertFalse(r["in_table"], "the failed run stays in the table, so every later ask answers busy")
        self.assertFalse(r["busy"], "the server is left busy")
        self.assertIsNone(r["record"], "the failed run's record (system/guard/run.json) is left behind")
        self.assertEqual(r["ended"], r["started"], "the process that started is ended")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# #334: the weekly AI budget
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

# A stand-in for `claude` that answers every request with one line and notes that it was started (never a model, never the network).
FAKE = r'''#!/usr/bin/env python3
import json, os, sys
here = os.path.abspath(__file__)
open(here + ".argv", "a", encoding="utf-8").write(json.dumps(sys.argv[1:]) + "\n")
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init"})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Stand-in reply."}]}})
out({"type": "result", "result": "Stand-in reply.", "session_id": "sess-hc266"})
'''


class Budget266(Engine266):
    """Checks 20 to 23 and 28. A vault and a live server whose Claude is the stand-in above. The budget is OFF by default (#334, 96d64e70),
    so each check switches it on first the way Settings does (`switch_on`: settings_catalogue.save), sets it to 1 dollar and writes
    the week's use to the usage log (counts only, as the run monitor writes it). Check 28 leaves it off."""
    with_server = True

    @classmethod
    def prepare(cls):
        cls.claude = cls.vault / "fake_claude_budget.py"
        cls.claude.write_text(FAKE, encoding="utf-8")
        cls.claude.chmod(0o755)

    def started(self):
        p = Path(str(self.claude) + ".argv")
        return sum(1 for ln in p.read_text().splitlines() if "--" in json.loads(ln) and "hc266-ask" in json.loads(ln)[json.loads(ln).index("--") + 1]) \
            if p.exists() else 0

    def switch_on(self, **cfg):
        """Switch the weekly budget on the way Settings does (settings_catalogue.save: a backup, the file written, one log line per key).
        The budget is OFF until this is done (#334, 96d64e70)."""
        keys = {f"ai_budget.{k}": v for k, v in dict({"enabled": True}, **cfg).items()}
        self.py("import settings_catalogue as sc\nsc.save(%r)\nprint(1)" % (keys,))

    def week(self, spent, limit=1, at_limit="confirm", unit="dollars", enabled=True):
        """Set the budget and write this week's use (and last week's, which must not count) to the usage log. `enabled` False leaves the
        budget as it is by default (off) with the same limits written, to show that off holds nothing whatever the limits say."""
        if enabled:
            self.switch_on(unit=unit, weekly_dollars=limit, at_limit=at_limit)
        else:
            self.set_setting("ai_budget", {"enabled": False, "unit": unit, "weekly_dollars": limit, "at_limit": at_limit})
        now = (self.now or str(date.today()))[:10]
        monday = date.fromisoformat(now) - timedelta(days=date.fromisoformat(now).weekday())
        rows = [{"at": f"{monday.isoformat()}T09:00:00", "kind": "ask", "cost_usd": spent, "input": 1000, "output": 500},
                {"at": f"{(monday - timedelta(days=1)).isoformat()}T09:00:00", "kind": "ask", "cost_usd": 999, "input": 9, "output": 9}]
        (self.staging("run-usage.jsonl")).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    def ask(self, **req):
        return self.post("/api/ask", dict({"message": "hc266-ask hello"}, **req))

    @needs("budget")
    def test_c20_over_budget_in_confirm_mode_asks_first_and_refuses_plainly(self):
        """20. (#334) With the budget switched on, this week's use over it and "at the limit" on confirm, a typed ask is answered 429 with plain words (the
        budget used up, the Monday it starts again, "The buttons in the dashboard still work", "Run this request anyway?"), the figures
        and a can_continue flag; no run is started and the message is not echoed; with Run anyway (over_budget true, the page's own
        click) it goes through; under budget nothing is held; last week's use does not count."""
        self.week(spent=2)
        base = self.started()
        code, res = self.ask()
        self.assertEqual(code, 429, res)
        self.assertIs(res.get("ok"), False)
        self.assertTrue(res["budget"]["can_continue"], res)
        for words in ("AI budget is used up", "starts again on Monday", "The buttons in the dashboard still work", "Run this request anyway?"):
            self.assertIn(words, res["message"])
        self.assertNotRegex(res["message"], r"Traceback|\.py\b|\.json|settings\.json", "plain words")
        self.assertNotIn("hc266-ask", json.dumps(res), "the message is not echoed")
        self.assertEqual(self.started(), base, "a run was started")
        code, res = self.ask(over_budget="yes")                                            # only the boolean is the page's click
        self.assertEqual(code, 429, "a text is not a click")
        code, res = self.ask(over_budget=True)
        self.assertEqual(code, 200, res)
        self.assertEqual(res.get("stream", "").count("Stand-in reply."), 1 if res.get("stream") else 0)
        self.week(spent=0.2)
        code, res = self.ask()
        self.assertEqual(code, 200, f"under budget nothing is held: {res}")
        self.note(20, "429 with the plain words and can_continue; nothing echoed, nothing started; Run anyway runs; under budget runs")

    @needs("budget")
    def test_c21_stop_mode_refuses_but_never_the_approval_path(self):
        """21. (#334) With the budget switched on and "at the limit" on stop, a typed ask is refused even with Run anyway and says to raise the budget in Settings;
        a confirmed request (the answer to a question the run asked) goes through; Review, Apply and Undo are never blocked: a pending
        item is approved over budget."""
        self.week(spent=5, at_limit="stop")
        base = self.started()
        code, res = self.ask(over_budget=True)
        self.assertEqual(code, 429, res)
        self.assertFalse(res["budget"]["can_continue"], res)
        self.assertIn("Raise the budget in Settings", res["message"])
        self.assertEqual(self.started(), base, "a run was started")
        code, res = self.ask(confirmed="Apply these changes")
        self.assertEqual(code, 200, f"a confirmed request is never held: {res}")
        name = self.mail_proposal(["Lima beacon check"])
        code, res = self.post("/api/review", {"file": name, "ref": 1, "decision": "approved", "modes": [], "expect": self.fingerprint(name, 1)})
        self.assertTrue(res.get("ok"), f"Review is blocked over budget: {res}")
        self.assertEqual(self.decisions(name), {1: "approved"})
        self.note(21, "stop: refused with Run anyway, can_continue false; confirmed runs; Review approved an item over budget")

    def test_c22_the_week_the_warning_and_the_counts(self):
        """22. (#334) With the budget switched on, the week runs from Monday 00:00 to the next Monday 00:00; the Usage figures (ai_budget.py, GET /api/usage) say used,
        the budget and the week's end, warn from 80% and hold at 100%; they are counts and dates only (no text of a message, a name or a
        path)."""
        self.week(spent=0.5)
        st = self.py("import ai_budget\nprint(json.dumps(ai_budget.status()))")
        self.assertEqual((st["state"], st["limit"], st["used"]), ("ok", 1, 0.5), st)
        self.week(spent=0.85)
        self.assertEqual(self.py("import ai_budget\nprint(json.dumps(ai_budget.status()))")["state"], "warn", "80% warns")
        self.week(spent=1.0)
        st = self.py("import ai_budget\nprint(json.dumps(ai_budget.status()))")
        self.assertEqual(st["state"], "over", "100% holds")
        self.assertEqual(st["week_start"], (date.fromisoformat(self.day()) - timedelta(days=date.fromisoformat(self.day()).weekday())).isoformat())
        self.assertEqual(date.fromisoformat(st["resets"]).weekday(), 0, "the week starts again on a Monday")
        self.assertEqual(st["used"], 1.0, "last week's 999 dollars did not count")
        mon = self.py("import ai_budget, datetime\nprint(json.dumps(ai_budget.status(None, None, datetime.datetime(2026, 10, 26, 0, 0))))",
                      env={"CREAITE_NOW": "2026-10-26 00:00"})
        self.assertEqual(mon["used"], 0.0, "Monday 00:00 starts a new week")
        req = urllib.request.Request(self.base + "/api/usage", headers={"X-Creaite-Token": self.page_token()})
        usage = json.loads(urllib.request.urlopen(req, timeout=30).read())
        self.assertEqual(usage["budget"]["state"], "over")
        shown = json.dumps(usage["budget"]) + json.dumps(st)
        for text in ("hc266", "Sara", "Harbour", "/", "message", "prompt"):
            self.assertNotIn(text, shown.replace("/", "") if text == "/" else shown, f"'{text}' is in the budget's figures")
        self.assertRegex(usage["budget"]["line"], r"of \$1\.00 used this week; the week ends on \d\d-\d\d-\d{4}\.")
        self.note(22, f"ok/warn/over at 50/85/100%; Monday starts a new week; line: {usage['budget']['line']}")

    def test_c23_an_ask_run_cannot_raise_its_own_budget(self):
        """23. (#334) The budget (off until switched on) is a setting in settings.json and its count is the usage log. In an ask creaite run (the guard hook, which
        refuses whatever a settings file allows) a direct write of settings.json or of the usage log is refused, so is the setting
        command (a new limit, or switching the budget off), and a change through filechange.py is a sensitive change that waits on Alan's card; the budget code and its tests
        are on the never-change list. The dashboard's own Save (the page's token) is the only way."""
        r = self.py("""
import reach
def hook(tool, inp, mode):
    ok, why = reach.hook_decision(tool, inp, mode, 'r-hc266')
    return [ok, why]
set_cmd = 'system/scripts/run propose.py setting ai_budget.weekly_dollars 9999'
off_cmd = 'system/scripts/run propose.py setting ai_budget.enabled false'
out = {}
for mode in ('ask', 'confirmed'):
    out[mode] = {
      'write_settings': hook('Write', {'file_path': 'system/config/settings.json', 'content': '{}'}, mode),
      'edit_settings': hook('Edit', {'file_path': 'system/config/settings.json', 'old_string': 'a', 'new_string': 'b'}, mode),
      'write_usage': hook('Write', {'file_path': 'system/staging/run-usage.jsonl', 'content': ''}, mode),
      'setting_command': hook('Bash', {'command': set_cmd}, mode),
      'switch_off_command': hook('Bash', {'command': off_cmd}, mode),
      'edit_budget_code': hook('Write', {'file_path': 'system/scripts/ai_budget.py', 'content': ''}, mode)}
out['classify_settings'] = list(reach.classify('system/config/settings.json', 'change'))
out['classify_code'] = list(reach.classify('system/scripts/ai_budget.py', 'change'))
print(json.dumps(out))""")
        for mode in ("ask", "confirmed"):
            for what, (allowed, why) in r[mode].items():
                if mode == "confirmed" and what == "write_usage":
                    continue                                    # a confirmed request may write to staging; the usage log is checked in ask mode
                self.assertFalse(allowed, f"{mode} run: {what} is allowed")
                self.assertTrue(why, f"{mode} run: {what} is refused without a reason")
        self.assertEqual(r["classify_settings"][0], "sensitive", "a change to settings.json waits on the card")
        self.assertEqual(r["classify_code"][0], "never", "the budget's code is never changed by an ask run")
        self.note(23, "settings.json, the usage log, the setting command and ai_budget.py all refused to an ask run; settings.json is sensitive (card)")


    @needs("budget")
    def test_c28_the_budget_is_off_by_default_and_off_holds_nothing(self):
        """28. (#334) The weekly AI budget is OFF until it is switched on: the shipped default is off and in a vault that never set it
        its status says off, and with this week's use far over any limit, in confirm and in stop, a typed ask is answered (200, never 429), a
        run starts, the answer carries no budget line, and GET /api/usage reports it off with no state, so the Usage tab can say so. Review
        is untouched. Switched on (the way Settings does it) the same use holds."""
        f = self.vault / "system/config/settings.json"                              # the earlier checks switched it on: back to untouched
        cfg = json.loads(f.read_text(encoding="utf-8"))
        cfg.pop("ai_budget", None)
        f.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        shipped = json.loads((self.vault / "system/templates/settings-defaults.json").read_text(encoding="utf-8"))["ai_budget"]
        self.assertIs(shipped["enabled"], False, "the shipped default is off")
        st = self.py("import ai_budget\nprint(json.dumps(ai_budget.status()))")
        self.assertIs(st["enabled"], False, f"a vault that never touched the budget has it on: {st}")
        for at_limit in ("confirm", "stop"):
            self.week(spent=500, enabled=False, at_limit=at_limit)                  # 500 dollars against a limit of 1, but the budget is off
            base = self.started()
            code, res = self.ask()
            self.assertEqual(code, 200, f"off ({at_limit}): a typed ask was held: {res}")
            self.assertNotIn("budget", json.dumps({k: v for k, v in res.items() if k != "stream"}).lower(), res)
            self.assertNotRegex(res.get("stream", ""), r"(?i)AI budget|Heads-up", f"off ({at_limit}): a budget line was said")
            self.assertEqual(self.started(), base + 1, f"off ({at_limit}): the run did not start")
        req = urllib.request.Request(self.base + "/api/usage", headers={"X-Creaite-Token": self.page_token()})
        usage = json.loads(urllib.request.urlopen(req, timeout=30).read())["budget"]
        self.assertIs(usage["enabled"], False, usage)
        self.assertNotIn(usage.get("state"), ("warn", "over"), usage)
        name = self.mail_proposal(["Mike lighthouse check"])
        code, res = self.post("/api/review", {"file": name, "ref": 1, "decision": "approved", "modes": [], "expect": self.fingerprint(name, 1)})
        self.assertTrue(res.get("ok"), res)
        self.week(spent=500)                                                        # switched on, the same use holds
        self.assertEqual(self.ask()[0], 429, "switched on, 500 dollars against 1 holds")
        self.note(28, f"default off ({st['enabled']}); 500 dollars used, limit 1: ask answered in confirm and in stop, no line; usage says enabled {usage['enabled']}; on: 429")

    @needs("reach")
    def test_c27_the_new_report_scripts_are_classified_as_read_only(self):
        """27. (#334, #339) ai_budget.py (this week's budget figures) and start_tokens_report.py (start tokens per run kind) are listed in
        reach.py's SCRIPT_COMMANDS as read only, so an ask run that has not been confirmed may run them and dev/tests/test_record_commands.py
        passes (an unlisted script is refused in a plain chat until someone decides: it failed on the line without this)."""
        r = self.py("""
import reach
out = {}
for script in ("ai_budget.py", "start_tokens_report.py", "usage_report.py"):
    out[script] = reach.command_kind(script, [])[0]
print(json.dumps(out))""")
        for script, kind in r.items():
            self.assertEqual(kind, "read", f"{script} is not classified read only: {r}")
        self.note(27, "ai_budget.py, start_tokens_report.py and usage_report.py are read only")


class Card266(HandcheckCase):
    """Check 24. A vault of its own and Chrome: the ask panel when the week's budget is used up."""
    own_vault = True

    @needs("budget")
    def test_c24_the_ask_panel_shows_the_budget_card_and_cancel_starts_nothing(self):
        """24. (#334) With the budget switched on and over budget on confirm, sending a message in the ask panel shows the card "Weekly AI budget" (the plain words, a
        Run anyway button and Cancel); Cancel starts nothing and says it plainly once, and Run anyway runs the request."""
        b, vault = self.b, self.vault
        cfg = vault / "system/config/settings.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        data["ai_budget"] = {"enabled": True, "unit": "dollars", "weekly_dollars": 1, "at_limit": "confirm"}
        cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
        monday = date.fromisoformat(self.now[:10]) - timedelta(days=date.fromisoformat(self.now[:10]).weekday())
        (vault / "system/staging/run-usage.jsonl").write_text(json.dumps({"at": f"{monday.isoformat()}T09:00:00", "kind": "ask", "cost_usd": 3}) + "\n")
        b.eval("openChat()")
        b.wait("document.getElementById('chat').classList.contains('on')", 10)
        b.eval("(()=>{ const t=document.getElementById('chIn'); t.value='hc266 what is due'; t.dispatchEvent(new Event('input',{bubbles:true})); return true; })()")
        b.click("#chSend")
        b.wait("document.querySelector('#chLog .confirm')", 20)
        card = b.eval("document.querySelector('#chLog .confirm').innerText")
        self.assertIn("Weekly AI budget", card)
        self.assertIn("AI budget is used up", card)
        self.assertRegex(card, r"Run anyway")
        self.assertNotRegex(card, r"Traceback|\.py\b|\.json")
        b.eval("[...document.querySelectorAll('#chLog .confirm button')].find(x=>/Cancel/.test(x.textContent)).click()")
        b.pump(0.8)
        log = b.eval("document.getElementById('chLog').innerText")
        self.assertEqual(log.count("Run this request anyway?"), 1, "the question is on the card only, not asked again after Cancel")
        self.assertEqual(log.count("AI budget is used up"), 2, "after Cancel creaite says once, plainly, that nothing was run")
        self.assertEqual(b.eval("document.getElementById('chSend').dataset.tip"), "Send", "something is running after Cancel")
        self.assertFalse(b.eval("!!document.querySelector('#chLog .working')"))
        replies = b.eval("document.querySelectorAll('#chLog .msg.a').length")
        b.eval("(()=>{ const t=document.getElementById('chIn'); t.value='hc266 what is due'; t.dispatchEvent(new Event('input',{bubbles:true})); return true; })()")
        b.click("#chSend")
        b.wait("document.querySelectorAll('#chLog .confirm').length>1", 20)
        b.eval("[...[...document.querySelectorAll('#chLog .confirm')].pop().querySelectorAll('button')].find(x=>/Run anyway/.test(x.textContent)).click()")
        b.wait(f"document.querySelectorAll('#chLog .msg.a').length>{replies}", 40)
        b.wait("document.getElementById('chSend').dataset.tip==='Send'", 40)
        new = b.eval(f"[...document.querySelectorAll('#chLog .msg.a')].slice({replies}).map(e=>e.innerText.trim())")
        answers = [t for t in new if "AI budget" not in t]
        self.assertTrue(answers, f"Run anyway ran nothing: {new}")
        self.assertTrue(any(t.startswith("Over this week's AI budget") for t in new), f"after the run, a plain note says the budget is over: {new}")
        self.note(24, "card text: " + " ".join(card.split())[:110])


class UsageOff266(HandcheckCase):
    """Check 29. A vault of its own that never switched the budget on: the Usage tab and the ask panel."""
    own_vault = True

    def test_c29_the_usage_tab_says_the_budget_is_off_and_the_panel_holds_nothing(self):
        """29. (#334) With the budget as the zip gives it (off) and this week's use far over any limit, the Usage tab says the weekly AI
        budget is off, as it is until you switch it on (and where to switch it on), draws no budget bar, and a typed request in the ask
        panel is sent with no "Weekly AI budget" card and no budget line (the answer is the stand-in's). At 1400 and 900 px."""
        b, vault = self.b, self.vault
        data = json.loads((vault / "system/config/settings.json").read_text(encoding="utf-8"))
        self.assertIsNot((data.get("ai_budget") or {}).get("enabled"), True, "the vault's settings have the budget on")
        monday = date.fromisoformat(self.now[:10]) - timedelta(days=date.fromisoformat(self.now[:10]).weekday())
        (vault / "system/staging/run-usage.jsonl").write_text(json.dumps({"at": f"{monday.isoformat()}T09:00:00", "kind": "ask", "cost_usd": 500}) + "\n")
        for w in (1400, 900):
            b.resize(w, 1000)
            b.eval("go('activity')")
            b.wait("!!document.querySelector('#actTabU')", 15)
            b.click("#actTabU")
            b.wait("!!document.querySelector('#actUsage [data-budget-off]')", 20)
            text = b.eval("document.querySelector('#actUsage [data-budget-off]').textContent")
            self.assertRegex(text, r"weekly AI budget is off, as it is until you switch it on", f"at {w} px: {text}")
            self.assertRegex(text, r"Settings, Advanced", text)
            self.assertFalse(b.eval("!!document.querySelector('#actUsage .ubudget')"), f"a budget bar is drawn at {w} px")
            self.assertTrue(b.eval("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1"), f"sideways scroll at {w} px")
        b.resize(1400, 1000)
        b.eval("openChat()")
        b.wait("document.getElementById('chat').classList.contains('on')", 10)
        b.eval("(()=>{ const t=document.getElementById('chIn'); t.value='hc266 what is due'; t.dispatchEvent(new Event('input',{bubbles:true})); return true; })()")
        b.click("#chSend")
        b.wait("document.querySelectorAll('#chLog .msg.a').length>0", 40)
        b.wait("document.getElementById('chSend').dataset.tip==='Send'", 40)
        self.assertFalse(b.eval("!!document.querySelector('#chLog .confirm')"), "a budget card was shown with the budget off")
        log = b.eval("document.getElementById('chLog').innerText")
        self.assertNotRegex(log, r"(?i)AI budget|Heads-up", log[:300])
        self.note(29, "Usage: 'The weekly AI budget is off, as it is until you switch it on…' at 1400 and 900; 500 dollars used, a typed request runs with no card or line")



# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# #348: the profile card
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class Profile266(HandcheckCase):
    """Check 25. A vault of its own: the name is set in the page to a colleague who is in the people register."""
    own_vault = True

    def test_c25_a_colleagues_details_are_not_shown_as_yours(self):
        """25. (#348) With the name set to a colleague who is in the people register (Sara Khan), Settings › Essentials › Your profile shows
        none of her email, organisation or role as yours and offers "Add my details", not "Edit my details"; once the row is claimed as
        yours the card shows it."""
        b = self.b
        self.screen("settings-essentials")
        sara = b.eval("(()=>{ const p=shared.REG.find(x=>x.name==='Sara Khan'); return p?{email:p.email,org:p.org,role:p.role}:null; })()")
        self.assertTrue(sara and sara["email"], f"the demo's register has Sara Khan with an email: {sara}")
        b.eval("(()=>{ try{ localStorage.removeItem('creaite-profile-claimed'); }catch(e){} S.me='Sara Khan'; S.meSet=true; profileRedraw(); return true; })()")
        b.pump(0.3)
        card = b.eval("document.getElementById('profileCard').innerText")
        for field in ("email", "org", "role"):
            if sara[field]:
                self.assertNotIn(sara[field], card, f"her {field} is shown as yours: {card[:200]}")
        button = b.eval("document.getElementById('pfEdit').textContent.trim()")
        self.assertNotRegex(button, r"(?i)edit my details", f"the button says '{button}'")
        self.assertRegex(button, r"(?i)add my details")
        b.eval("(()=>{ localStorage.setItem('creaite-profile-claimed', JSON.stringify(['sara khan'])); profileRedraw(); return true; })()")
        b.pump(0.3)
        self.assertIn(sara["email"], b.eval("document.getElementById('profileCard').innerText"), "claimed, the row is shown as yours")
        self.note(25, f"not claimed: no email, organisation or role shown, button '{button}'; claimed: her details shown")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# #352: Today's stale-updates line
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class Today266(HandcheckCase):
    """Check 30. The shared hand-check vault and Chrome; the page's own data is set (nothing is saved) so every open action is stale."""

    def test_c30_today_has_no_stale_updates_line_and_the_draft_stays_in_work(self):
        """30. (#352) With every open action stale (no update for more than the stale threshold), Today's My Commitments shows no
        "N open actions have had no update for 7 days" line and no "Draft updates" button, at 1400 and 900 px, with no sideways scroll;
        the draft stays: selecting two actions in Work offers Draft updates in the bulk bar."""
        b, seen = self.b, {}
        b.wait("PULSE.reloads===0 && !PULSE.busy && !EVS.timer", 30)
        try:
            for w in (1400, 900):
                with width(self, w, 1000):
                    b.eval("window.__upd = A.map(x=>x.upd_at); A.forEach(x=>x.upd_at='2026-01-01'); true")
                    try:
                        self.screen("today")
                        b.eval("renderToday(); true")
                        b.pump(0.8)
                        seen[w] = b.eval("({stale:!!document.querySelector('#drStale, #v-today [data-drstale]'), "
                                         "line:/had no update for/.test(document.getElementById('v-today').textContent), "
                                         "btn:[...document.querySelectorAll('#v-today button, #v-today a')].some(e=>/^\\s*Draft updates\\s*$/.test(e.textContent)), "
                                         "open:A.filter(x=>OPENST(x.st)).length, "
                                         "side:document.documentElement.scrollWidth>document.documentElement.clientWidth+1})")
                    finally:
                        b.eval("A.forEach((x,i)=>{ x.upd_at=window.__upd[i]; }); true")
                    self.assertGreater(seen[w]["open"], 0, "the demo has open actions")
                    self.assertFalse(seen[w]["stale"], f"the stale block is on Today at {w} px")
                    self.assertFalse(seen[w]["line"], f"'had no update for' is on Today at {w} px")
                    self.assertFalse(seen[w]["btn"], f"a Draft updates button is on Today at {w} px")
                    self.assertFalse(seen[w]["side"], f"Today scrolls sideways at {w} px")
        finally:
            b.eval("HL.clear(); hlPaint(); hlBar(); true")
        self.screen("work")
        b.eval("WT='actions'; renderWork(); true")
        b.wait("document.querySelector('#workTbl tr[data-row]')", 15)
        ids = b.eval("A.filter(x=>OPENST(x.st)).slice(0, 2).map(x=>x.id)")
        b.eval("HL.clear(); %s.forEach(i=>HL.set(i,'actions')); hlPaint(); hlBar(); true" % json.dumps(ids))
        b.wait("document.querySelector('#wbulk [data-drbulk]')", 15)
        self.assertIn("Draft updates", b.eval("document.querySelector('#wbulk [data-drbulk]').textContent"))
        b.eval("HL.clear(); hlPaint(); hlBar(); true")
        self.note(30, f"Today at 1400 and 900 px with {seen[1400]['open']} stale open actions: no line, no Draft updates button, no sideways scroll; Work's bulk bar still has Draft updates")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# #351 b: a past day on Today
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

FOLLOW_UP_WORDS = ("No transcript", "Transcript ready", "Not checked yet", "Minutes made", "Draft in Review")
MEETING_TIMES = [("09:00", "09:30", "Weekly sync", True), ("09:45", "10:30", "Project kickoff", True), ("10:30", "11:15", "Budget review", True),
                 ("11:30", "12:15", "Demo day", True), ("12:15", "12:45", "Lunch and learn", True), ("13:00", "14:00", "Steering committee", True),
                 ("14:00", "14:30", "Retro", True), ("14:30", "15:15", "Design review", True), ("15:30", "16:00", "Vendor check-in", True),
                 ("16:00", "16:30", "Planning huddle", True)]


class PastWorld266(HandcheckCase):
    """The base of checks 31, 33, 35 and 36. A vault of its own with a fictional calendar of about ten Teams meetings on the day before today and
    on today, and every state the old follow-up chips showed (transcript ready, none, not transcribed, minutes made, not checked yet).
    No checks of its own."""
    own_vault = True

    def world(self):
        """Write the calendar, what the check found and what was processed; widen the calendar import so the past day is in it."""
        vault, today = self.vault, date.fromisoformat(self.now[:10])
        past = today - timedelta(days=1)
        cfg = vault / "system/config/settings.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        data.setdefault("inbox", {})["meetings_from"] = 7             # not "monday": on a Monday there would be no past day
        cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")
        days, checked, processed = {}, {}, []
        for d in (past, today):
            iso, rows = d.isoformat(), []
            for i, (start, end, title, teams) in enumerate(MEETING_TIMES, 1):
                eid = f"evt-{iso[8:]}-{i:02d}"
                rows.append({"id": eid, "start": start, "end": end, "title": title, "where": "Microsoft Teams Meeting", "all_day": False,
                             "private": False, "teams": teams, "organiser": "Riley Stone", "organiser_email": "", "sensitivity": "normal",
                             "recurrence": "", "body": "", "attendees": [{"name": f"Guest {k}", "email": "", "type": "required", "response": "accepted"}
                                                                          for k in range(3)], "attachments": []})
                state = {1: "available", 6: "available", 7: "none", 8: "not_transcribed"}.get(i)
                if state:
                    checked[eid] = {"status": state, "checked": f"{today.isoformat()} 08:05"}
            days[iso] = rows
            processed.append(f"{iso} | calendar:evt-{iso[8:]}-02 | {iso} Project kickoff.docx | 4")
        cal = {"fetched": f"{today.isoformat()} 08:05", "to": (today + timedelta(days=3)).isoformat(), "days": days}
        st = vault / "system/staging"
        (st / "calendar.json").write_text(json.dumps(cal, indent=1), encoding="utf-8")
        (st / "transcripts.json").write_text(json.dumps({"checked": checked, "version": 1}, indent=1), encoding="utf-8")
        (vault / "system/processed.txt").write_text("\n".join(processed) + "\n", encoding="utf-8")
        code, out = self.run_in_vault("build_dashboard.py")
        self.assertEqual(code, 0, out[-400:])
        self.b.reload("typeof go==='function' && LIVE")
        return past.isoformat(), today.isoformat()

    def intake(self):
        """Intake, freshly drawn, as a person finds it: the waiting tail folded (the page's own start)."""
        b = self.b
        self.screen("intake-review")
        b.wait("document.querySelector('#v-intake-review [data-ira=process]')", 20)
        b.pump(0.3)

    BUTTONS = """({process:document.querySelectorAll('#v-intake-review [data-ira=process]:not([disabled])').length,
        check:document.querySelectorAll('#v-intake-review [data-ira=check]').length,
        open:document.querySelectorAll('#v-intake-review [data-ira=open]').length,
        waiting:document.querySelectorAll('#v-intake-review tr.irmeet[data-stage=arrived][data-state=waiting]').length,
        head:(()=>{ const h=document.querySelector('#v-intake-review [data-irsec=waiting] h2'), k=h&&h.querySelector('[data-irfold=waiting]');
          return h?{text:h.textContent.replace(/\\s+/g,' ').trim(), button:k?k.textContent.trim():null, expanded:k?k.getAttribute('aria-expanded'):null}:null; })()})"""

    def buttons(self):
        return self.b.eval(self.BUTTONS)

    def open_fold(self, how, term="Retro"):
        """Open the waiting tail the way a person does: how is 'show' (the Show link on the Waiting for the transcript heading), 'arrived'
        (the Arrived box), 'filter' (Show: Waiting for the transcript) or 'search' (a word of a waiting meeting's title in the search)."""
        b = self.b
        if how == "show":
            b.click("#v-intake-review [data-irfold=waiting]")
        elif how == "arrived":
            b.click("#v-intake-review [data-irstage=arrived]")
        elif how == "filter":
            b.eval("(()=>{ const s=document.querySelector('#v-intake-review [data-irshow]'); s.value='waiting'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        elif how == "search":
            b.click("#irQ")
            b.type(term)
        b.pump(0.4)

    def release_fold(self, how):
        """Let go of the opener the way a person does: the Hide link, the Arrived box again, Show: All meetings, the search cleared."""
        b = self.b
        if how == "show":
            b.click("#v-intake-review [data-irfold=waiting]")
        elif how == "arrived":
            b.click("#v-intake-review [data-irstage=arrived]")
        elif how == "filter":
            b.eval("(()=>{ const s=document.querySelector('#v-intake-review [data-irshow]'); s.value='all'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        elif how == "search":
            b.eval("(()=>{ const q=document.querySelector('#irQ'); q.value=''; q.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.pump(0.4)

    def pick(self, iso):
        b = self.b
        b.eval("go('today')")
        b.wait("document.querySelectorAll('#todayDate [role=tab]').length>1", 30)
        if iso == self.today_iso:
            b.click(f'#todayDate [data-tab="{iso}"]')
        else:
            b.click("#todayDate .dypastbtn")
            b.wait("document.querySelector('#todayDate [role=menu]')", 10)
            day = date.fromisoformat(iso)
            want = f"^{day.strftime('%A')} {day.day}(st|nd|rd|th) "           # the menu writes the day out: "Friday 23rd October"
            b.eval(f"[...document.querySelectorAll('#todayDate [role=menuitem]')].find(i=>new RegExp({json.dumps(want)}).test(i.textContent.trim())).click()")
        b.wait(f"(document.querySelector('#todayDate [aria-selected=\"true\"]')||{{}}).dataset&&document.querySelector('#todayDate [aria-selected=\"true\"]').dataset.tab==={json.dumps(iso)}", 15)
        b.wait("document.querySelectorAll('#dayMeets .dm').length>0", 15)
        b.pump(0.4)



class PastDay266(PastWorld266):
    """Check 31, in the past-day world."""

    def test_c31_a_past_day_on_today_has_no_follow_up_chips_or_links_and_intake_keeps_them(self):
        """31. (#351 b) On a past day, Today lists the meetings with their times, titles and projects and nothing under them: none of "No
        transcript", "Transcript ready", "Not checked yet", "Minutes made" (or "Draft in Review"), and no Check or Process link, at 1400
        and 900 px with no sideways scroll. Today is unchanged (a title still opens the Prep peek on hover) and Intake still offers
        Process and Check again for the same meetings: the meetings waiting for a transcript start folded in Intake (#340), so Check again
        is not in view until the person opens them (the Show link on the Waiting for the transcript heading, the Arrived box, Show:
        Waiting for the transcript, or a search that finds one); without that it is folded, and it folds again when the opener is
        released."""
        b = self.b
        past, today = self.world()
        self.today_iso = today
        meets = "document.querySelectorAll('#dayMeets .dm')"
        seen = {}
        for w in (1400, 900):
            with width(self, w, 1000):
                self.pick(past)
                seen[w] = b.eval(f"""({{n:{meets}.length, acts:document.querySelectorAll('#dayMeets .acts, #dayMeets .chip, #dayMeets .lk').length,
                    text:document.getElementById('dayMeets').textContent,
                    links:[...document.querySelectorAll('#dayMeets button, #dayMeets a')].map(e=>(e.textContent||'').trim()).filter(t=>/^(Check|Process|Review)$/.test(t)),
                    side:document.documentElement.scrollWidth>document.documentElement.clientWidth+1 || document.getElementById('dayMeets').scrollWidth>document.getElementById('dayMeets').clientWidth+1}})""")
                self.assertEqual(seen[w]["n"], len(MEETING_TIMES), f"the past day's meetings are all there at {w} px")
                self.assertEqual(seen[w]["acts"], 0, f"a follow-up chip or link is under a past meeting at {w} px")
                self.assertEqual(seen[w]["links"], [], f"a Check, Process or Review link is on the past day at {w} px")
                for word in FOLLOW_UP_WORDS:
                    self.assertNotIn(word, seen[w]["text"], f"'{word}' is on the past day at {w} px")
                self.assertFalse(seen[w]["side"], f"the past day scrolls sideways at {w} px")
        # today is unchanged: nothing under the meeting, and the title opens the Prep peek on a real pointer rest
        self.pick(today)
        self.assertEqual(b.eval("document.querySelectorAll('#dayMeets .acts').length"), 0)
        self.assertEqual(b.eval("document.querySelector('#dayMeets .dayaway')"), None, "today: no 'as of today' line")
        c = b.box("#dayMeets .dmti")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=c["x"] - 40, y=c["y"] - 40)
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=c["x"], y=c["y"])
        b.wait("document.querySelector('#dayMeets .dmpop')", 15)
        self.assertIn("Open the prep page", b.eval("document.querySelector('#dayMeets .dmpop').textContent"))
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5)
        # Intake keeps the jobs (#340: the waiting tail starts folded, so Check again is in view only once the person opens the fold)
        self.intake()
        folded = self.buttons()
        self.assertGreaterEqual(folded["process"], 2, f"Intake offers Process for the meetings with a transcript ready: {folded}")
        self.assertGreaterEqual(folded["open"], 1, f"Intake offers Check them for the meeting whose suggestions are waiting (work stays up): {folded}")
        self.assertEqual(folded["check"], 0, f"the waiting meetings are folded when Intake opens, so no Check again is in view: {folded}")
        self.assertEqual(folded["waiting"], 0, f"no waiting row is drawn while the tail is folded: {folded}")
        self.assertIsNotNone(folded["head"], "the folded tail still has its Waiting for the transcript heading")
        self.assertRegex(folded["head"]["text"], r"Waiting for the transcript\s+\d+")
        self.assertEqual((folded["head"]["button"], folded["head"]["expanded"]), ("Show", "false"), folded)
        seen_open, term = {}, ""
        for how, words in (("show", "the Show link"), ("arrived", "the Arrived box"), ("filter", "Show: Waiting for the transcript"),
                           ("search", "a search for a waiting meeting")):
            self.open_fold(how, term)
            got = seen_open[how] = self.buttons()
            if how == "show":                         # the search then looks for a meeting that offers Check again (a title the demo has)
                term = b.eval("(()=>{ const r=document.querySelector('#v-intake-review [data-ira=check]').closest('tr[data-irm]'); return D.intake_review.meetings.find(m=>m.id===r.dataset.irm).title; })()")
            self.assertGreaterEqual(got["check"], 1, f"Intake offers Check again for a meeting still waiting for its transcript once {words} opens the fold: {got}")
            self.assertGreater(got["waiting"], 0, f"the waiting rows are drawn ({words}): {got}")
            self.assertLessEqual(got["check"], got["waiting"], f"Check again is on waiting rows only ({words}): {got}")
            if how in ("show", "arrived"):            # the Show link adds the tail to the work, and the Arrived box keeps the ready rows beside it
                self.assertGreaterEqual(got["process"], 2, f"Process is still offered ({words}): {got}")
            self.release_fold(how)
            back = self.buttons()
            self.assertEqual((back["check"], back["waiting"]), (0, 0), f"the tail folds again when {words} is released: {back}")
            self.assertGreaterEqual(back["process"], 2, f"Process is still offered after {words} is released: {back}")
            self.assertEqual((back["head"] or {}).get("button"), "Show", back)
        # the Hide link folds it again after Show
        self.open_fold("show")
        self.assertEqual(self.buttons()["head"]["button"], "Hide")
        self.release_fold("show")
        self.assertEqual(self.buttons()["check"], 0)
        self.note(31, f"past day {past} at 1400 and 900 px: {seen[1400]['n']} meetings, no chip, no Check or Process, no sideways scroll; "
                      f"today's title opens the Prep peek; Intake: waiting tail folded ({folded['process']} Process, 0 Check again, Show on the heading), "
                      f"opened by Show / the Arrived box / Show: Waiting / a search it shows {seen_open['show']['check']} Check again and "
                      f"{seen_open['show']['process']} Process, and folds again when released; {folded['open']} Check them stays up throughout")


class TickFold266(PastWorld266):
    """Checks 33, 35 and 36. The past-day world's Intake, for the tick bar and a folded waiting tail."""

    def tick_bar(self):
        return self.b.eval("(()=>{ const t=document.querySelector('[data-irtickbar]'); return t?t.innerText.replace(/\\s+/g,' ').trim():null; })()")

    def waiting_ids(self):
        return self.b.eval("D.intake_review.meetings.filter(m=>m.stage==='arrived'&&m.state==='waiting'&&m.src!=='draft').map(m=>m.id)")

    def moved(self, mid):
        """Whether the meeting has been set aside (Later or Not needed): it has left the list, or the server wrote it to the cleared file."""
        self.b.pump(1.5)
        gone = self.b.eval(f"!D.intake_review.meetings.some(m=>m.id==={json.dumps(mid)})")
        f = self.vault / "system/staging/intake-cleared.json"
        return gone or (f.is_file() and mid in f.read_text(encoding="utf-8"))

    def tick_waiting_behind(self, mid):
        """Tick the waiting meeting `mid` (its row must be on the page) and wait until the bar says it is selected."""
        self.b.click(f'#v-intake-review input.irtick[data-irtick-box="{mid}"]')
        self.b.wait("(document.querySelector('[data-irtickbar]')||{innerText:''}).innerText.indexOf('1 selected')>=0", 10)

    def after_the_fold(self, mid, problems, route):
        """The tail is folded with `mid` ticked behind it. Nothing may stay ticked, so no tick bar may be shown; and if one is, Later
        (and Not needed because... where the bar has it) must not move the hidden meeting. Returns the bar's words, or None."""
        b = self.b
        self.assertEqual(self.buttons()["waiting"], 0, f"{route}: the tail folded")
        bar = self.tick_bar()
        if bar:
            problems.append(f"{route}: after the fold the tick bar still says {bar!r}, with a tick behind it on a hidden meeting")
            b.eval("(()=>{ const x=document.querySelector('[data-ira=laterall]'); if (x && !x.disabled) x.click(); })()")
            if self.moved(mid):
                problems.append(f"{route}: Later moved the hidden meeting")
        return bar

    def test_c33_the_tick_bar_does_not_act_on_a_meeting_the_fold_has_hidden(self):
        """33. (#343 H1, to the spec of 72de4a6a: folding the tail clears the ticks) Show the waiting tail, tick a waiting meeting, press
        Hide: nothing is ticked and no tick bar is shown; and Later and Not needed because... (the bar's buttons, if a bar were shown)
        do not move the hidden meeting. A folded row has no element, so the keys H and N have nothing to be pressed on; the bar's
        buttons are the route to it. A plain check (the bar was left standing with "0 selected, 1 hidden" before the fix)."""
        b = self.b
        self.world()
        self.intake()
        problems, said = [], {}
        for action in ("later", "reason"):
            self.intake()                                # a fresh page: the tail folded, nothing ticked
            self.open_fold("show")
            mid = self.waiting_ids()[0 if action == "later" else 1]
            self.tick_waiting_behind(mid)
            self.release_fold("show")                    # Hide
            self.assertEqual(self.buttons()["waiting"], 0, "the tail folded")
            bar = said[action] = self.tick_bar()
            if bar:
                problems.append(f"after Hide the tick bar is still shown and says {bar!r}")
                if action == "later":
                    b.eval("(()=>{ const x=document.querySelector('[data-ira=laterall]'); if (x && !x.disabled) x.click(); })()")
                else:
                    b.eval("(()=>{ const x=document.querySelector('[data-ira=reasonall]'); if (x && !x.disabled) x.click(); })()")
                    b.pump(0.4)
                    b.eval("(()=>{ const x=document.querySelector('.cxmenu .pkopt'); if (x) x.click(); })()")
                if self.moved(mid):
                    problems.append(f"{'Later' if action == 'later' else 'Not needed because'} moved the hidden meeting")
        self.note(33, f"tick a waiting meeting, Hide the tail: the tick bar is {said['later'] or 'not shown'!r}")
        self.assertEqual(problems, [], "; ".join(problems))

    def test_c35_esc_in_the_search_box_leaves_no_tick_behind_a_folded_row(self):
        """35. (#343 M-2, fixed on the line at 591eed66; and M-1 the click-time guard: this check covers M-1, so there is no separate one) Show the waiting tail by
        searching for a waiting meeting's title, tick it, press Esc in the search box (it clears the search, and the tail folds again,
        but irClearTicks is not called: IntakeReviewPage.jsx onKeyDown): afterwards no tick may stay on the hidden row, so the tick bar
        must not be shown (it must not say "1 selected"), and Later must not move the hidden meeting (M-1: a click on Later with a
        tick behind the fold must do nothing to it)."""
        b = self.b
        self.world()
        self.intake()
        mid = self.waiting_ids()[0]
        title = b.eval(f"D.intake_review.meetings.find(m=>m.id==={json.dumps(mid)}).title")
        self.open_fold("search", term=title)
        self.tick_waiting_behind(mid)
        b.click("#irQ")
        b.key("Escape")
        b.pump(0.5)
        self.assertEqual(b.eval("document.querySelector('#irQ').value"), "", "Esc cleared the search")
        problems = []
        bar = self.after_the_fold(mid, problems, "Esc in the search box")
        self.note(35, f"tick a waiting meeting found by search, Esc in the search box: the tick bar is {bar or 'not shown'!r}")
        self.assertEqual(problems, [], "; ".join(problems))

    def test_c36_group_by_none_leaves_no_tick_behind_a_folded_row(self):
        """36. (#343 M-2, fixed on the line at 591eed66) Group by Day (the waiting rows are on the page), tick a waiting meeting, then Group by None (irSetGroup,
        stores/intakeReview.js: it does not clear ticks, and the tail folds again): afterwards no tick may stay on the hidden row, so
        the tick bar must not be shown (it must not say "1 selected"), and Later must not move the hidden meeting."""
        b = self.b
        self.world()
        self.intake()
        group = "(v)=>{ const s=document.querySelector('#v-intake-review [data-irgroupby]'); s.value=v; s.dispatchEvent(new Event('change',{bubbles:true})); }"
        try:
            b.eval(f"({group})('day')")
            b.pump(0.5)
            mid = b.eval("(()=>{ const r=document.querySelector('#v-intake-review tr.irmeet[data-stage=arrived][data-state=waiting]'); "
                         "const i=r&&r.querySelector('input.irtick'); return i?i.getAttribute('data-irtick-box'):null; })()")
            self.assertTrue(mid, "with Group by Day a waiting meeting is on the page to tick")
            self.tick_waiting_behind(mid)
            b.eval(f"({group})('none')")
            b.pump(0.5)
            problems = []
            bar = self.after_the_fold(mid, problems, "Group by None")
        finally:
            b.eval(f"({group})('none')")                 # the browser remembers the grouping: put it back
        self.note(36, f"tick a waiting meeting under Group by Day, then Group by None: the tick bar is {bar or 'not shown'!r}")
        self.assertEqual(problems, [], "; ".join(problems))


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 2.6.5: what the 2.6.4 sheet did not have (checks 37 to 42). #360 People's Display menu, #357 the calm save, #359 the plain border,
# #356 the next job, #340 the work-first Intake in all three views with the mail cap, #343 the design batch (Work, Files, the cockpit)
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

class People266(HandcheckCase):
    """Check 37. The shared hand-check vault; the Display state is the browser's own (localStorage) and is cleared at the end."""
    KEYS = ("creaite-peopledisplay", "creaite-peoplesort")
    GROUPS = ["None", "Organisation", "Project", "Role", "Overdue", "Details"]

    def digest(self):
        import hashlib
        files = [self.vault / "system/config/settings.json", *sorted(self.vault.glob("projects/_portfolio/people-register.md"))]
        return {str(f.relative_to(self.vault)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files if f.is_file()}

    def fresh(self):
        """People, drawn again from a browser with no saved Display state."""
        b = self.b
        b.eval("(" + json.dumps(list(self.KEYS)) + ").forEach(k=>localStorage.removeItem(k)); 0")
        b.reload("typeof go==='function' && LIVE")
        self.screen("people")
        b.wait("document.querySelector('#plRows tr')", 15)

    ROWS = "[...document.querySelectorAll('#plRows tr:not(.wgh)')].filter(r=>r.querySelector('td[data-col=name]'))"
    NAMES = "(" + ROWS + ").map(r=>r.querySelector('td[data-col=name]').innerText.split('\\n')[0].trim())"
    HEADS = "[...document.querySelectorAll('#plRows tr.wgh')].map(h=>({label:h.querySelector('.wgn').textContent.trim(), text:h.querySelector('.sub').textContent.trim()}))"
    COUNT = "((document.getElementById('plApplied')||{}).textContent||'').replace(/\\s+/g,' ').trim()"

    def choose(self, sel, value):
        self.b.eval(f"(()=>{{ const s=document.querySelector({sel!r}); s.value={value!r}; s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        self.b.pump(0.4)

    def test_c37_people_display_menu_groups_orders_and_keeps_to_this_browser(self):
        """37. (#360) On People press D (or the sliders button): the Display menu opens with Group by (None, Organisation, Project, Role,
        Overdue, Details), Sub-group, Order by (Overdue is the default) with the reverse button, Properties (Name always stays first) and
        Reset to the default; Esc closes it and focus returns to its button. Group by Role puts everyone under a heading ("n people"); by
        Project a person on two projects is under both and "Showing x of y" still counts people. Order by Name sorts, ⇅ reverses.
        Unticking Email removes the column; moving a column changes the order. Reload: it is remembered; Reset puts it back. No option,
        heading, column or star anywhere speaks of following a person (BL-288). It is browser-only: settings.json and the people register
        are byte-for-byte unchanged. At 900 px the menu and the grouped table fit with no sideways scroll."""
        b = self.b
        before = self.digest()
        self.assertTrue(before, "the files compared were found")
        notes = []
        try:
            for w in (1400, 900):
                with width(self, w):
                    self.fresh()
                    count0 = b.eval(self.COUNT)
                    names0 = b.eval(self.NAMES)
                    self.assertTrue(names0 and "Showing" in count0, f"People has rows and a count line: {count0!r}")
                    # D opens the menu, as on Work
                    b.eval("document.activeElement&&document.activeElement.blur(); 0")
                    b.key("d")
                    b.wait("document.querySelector('#plDispMenu.on')", 10)
                    self.assertTrue(b.eval("document.getElementById('plDispMenu').contains(document.activeElement)"), "focus moved into the menu")
                    groups = b.eval("[...document.querySelectorAll('#pdgrp option')].map(o=>o.textContent.trim())")
                    self.assertEqual(groups, self.GROUPS)
                    order = b.eval("[...document.querySelectorAll('#pdsort option')].map(o=>o.textContent.trim())")
                    self.assertIn("Overdue (default)", order)
                    self.assertTrue(b.eval("!!document.getElementById('pdRev') && !!document.getElementById('pdReset') && !!document.getElementById('pdDone')"))
                    self.assertTrue(b.eval("document.getElementById('pdprop-name').disabled"), "Name is locked on")
                    self.assertFalse(re.search(r"follow", b.eval("document.getElementById('plDispMenu').textContent"), re.I), "no follow option in the menu")
                    fits = b.eval("(()=>{ const r=document.getElementById('plDispMenu').getBoundingClientRect(); return r.left>=0 && r.right<=innerWidth+1; })()")
                    self.assertTrue(fits, f"the menu fits the window at {w} px")
                    # Esc closes and returns focus to the button
                    b.key("Escape")
                    b.pump(0.3)
                    self.assertFalse(b.eval("!!document.querySelector('#plDispMenu.on')"), "Esc closed the menu")
                    self.assertEqual(b.eval("document.activeElement&&document.activeElement.id"), "plDispBtn")
                    # every Group by: the count line does not move, nobody is followed on screen
                    b.click("#plDispBtn")
                    b.wait("document.querySelector('#plDispMenu.on')", 10)
                    for g in ("org", "proj", "role", "late", "details"):
                        self.choose("#pdgrp", g)
                        heads = b.eval(self.HEADS)
                        self.assertTrue(heads, f"Group by {g}: headings are drawn")
                        self.assertEqual(b.eval(self.COUNT), count0, f"Group by {g}: 'Showing x of y' still counts people")
                        self.assertFalse(re.search(r"follow", b.eval("document.getElementById('v-people').innerText"), re.I), f"Group by {g}: nothing about following")
                        self.assertEqual(b.eval("document.querySelectorAll('#peopleTbl .star, #peopleTbl [data-followed]').length"), 0)
                        rows = b.eval(f"({self.ROWS}).length")
                        shown = sum(int(re.match(r"(\d+)", h["text"]).group(1)) for h in heads if re.match(r"\d+", h["text"]))
                        self.assertEqual(rows, shown, f"Group by {g}: the heading counts add up to the rows drawn")
                        if g == "proj":
                            notes.append(f"{w}px by Project: {len(names0)} people, {rows} rows")
                            self.assertGreaterEqual(rows, len(set(names0)), "a person on two projects is under both")
                    # Order by Name, then reversed (no Group by, so the plain list)
                    self.choose("#pdgrp", "none")
                    self.choose("#pdsort", "name")
                    asc = b.eval(self.NAMES)
                    self.assertEqual(b.eval("document.querySelector('#plRows tr.wgh')"), None)
                    self.assertTrue(all(asc[i - 1].lower() <= asc[i].lower() for i in range(2, len(asc))), f"sorted by name: {asc}")      # you stay first
                    b.click("#pdRev")
                    b.pump(0.3)
                    desc = b.eval(self.NAMES)
                    self.assertTrue(all(desc[i - 1].lower() >= desc[i].lower() for i in range(2, len(desc))), f"reversed: {desc}")
                    # Properties: take Email off, move Role earlier
                    b.click("#pdprop-email")
                    b.pump(0.3)
                    heads = b.eval("[...document.querySelectorAll('#peopleTbl thead th')].map(t=>t.dataset.col)")
                    self.assertNotIn("email", heads)
                    self.assertEqual(heads[0], "name", "Name stays first")
                    b.click('#plDispMenu [data-mv="role"][data-d="-1"]')
                    b.pump(0.3)
                    heads2 = b.eval("[...document.querySelectorAll('#peopleTbl thead th')].map(t=>t.dataset.col)")
                    self.assertLess(heads2.index("role"), heads2.index("org"), f"Role moved before Organisation: {heads2}")
                    # grouped by Organisation: the table still fits
                    self.choose("#pdgrp", "org")
                    self.assertFalse(b.eval("(()=>{ const t=document.getElementById('peopleTbl'); return t.scrollWidth>t.clientWidth+1; })()"), f"the grouped table fits at {w} px")
                    self.assertLessEqual(b.eval("document.scrollingElement.scrollWidth"), b.eval("innerWidth"), f"no sideways scroll at {w} px")
                    stored = b.eval("localStorage.getItem('creaite-peopledisplay')")
                    self.assertIn("org", stored or "")
                    b.click("#pdDone")
                    b.pump(0.3)
                    # remembered after a reload, then Reset
                    b.reload("typeof go==='function' && LIVE")
                    self.screen("people")
                    b.wait("document.querySelector('#plRows tr.wgh')", 15)
                    self.assertNotIn("email", b.eval("[...document.querySelectorAll('#peopleTbl thead th')].map(t=>t.dataset.col)"), "the column choice is remembered")
                    b.click("#plDispBtn")
                    b.wait("document.querySelector('#plDispMenu.on')", 10)
                    b.click("#pdReset")
                    b.pump(0.4)
                    self.assertEqual(b.eval("document.querySelectorAll('#plRows tr.wgh').length"), 0, "Reset removed the grouping")
                    self.assertIn("email", b.eval("[...document.querySelectorAll('#peopleTbl thead th')].map(t=>t.dataset.col)") if w >= 1100 else ["email"])
                    b.key("Escape")
        finally:
            self.b.eval("(" + json.dumps(list(self.KEYS)) + ").forEach(k=>localStorage.removeItem(k)); 0")
            self.b.reload("typeof go==='function' && LIVE")
        self.assertEqual(self.digest(), before, "settings.json and the people register are unchanged")
        self.note(37, "; ".join(notes) + "; settings.json and the people register byte-identical")


class Calm266(HandcheckCase):
    """Check 38. A vault of its own: it saves."""
    own_vault = True

    def stage(self, label):
        b = self.b
        b.click('#panel [data-pkp="pr"]')
        b.wait("document.querySelector('.pkpop')", 10)
        b.eval(f"[...document.querySelectorAll('.pkpop .pkopt')].find(o=>o.querySelector('span').firstChild.textContent==={label!r}).click()")

    def test_c38_a_save_from_the_panel_is_confirmed_calmly_with_one_undo(self):
        """38. (#357) Change an item's priority in its panel (the bar at the foot says "1 change waiting to be saved") and press Save: the
        bar goes and a message in the soft "ok" tint says "Saved 1 change" with exactly one Undo; the line "A backup was taken first" is
        its hover text, not part of what it says. Change something else while it shows: the waiting bar comes back and the message becomes
        "The earlier save can still be undone in Activity" (no ok tint, no Undo)."""
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')", 15)
        id_ = b.eval("A.find(a=>a.p==='FAL'&&OPENST(a.st)&&a.pr!=='Low'&&a.pr!=='High').id")
        b.eval(f"openRecord('actions', {id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')", 15)
        b.pump(0.3)
        self.stage("Low")
        b.wait("PKS.length===1", 15)
        b.pump(0.3)
        self.assertIn("1 change waiting to be saved", b.eval("document.getElementById('pkStN').textContent"))
        b.click("#pkApply")
        b.wait("document.querySelector('#snack.on.ok')", 20)
        b.pump(0.3)
        text = " ".join(b.eval("document.getElementById('snack').innerText").split())
        self.assertRegex(text, r"^Saved 1 change\b", text)
        self.assertNotIn("backup", text.lower(), "the backup line is hover text, not part of the message")
        self.assertIn("A backup was taken first", b.eval("document.getElementById('snack').title"))
        self.assertEqual(b.eval("document.querySelectorAll('#snack button').length"), 1, "exactly one Undo")
        self.assertEqual(b.eval("document.querySelector('#snack button').textContent.trim()"), "Undo")
        self.assertTrue(b.eval("document.getElementById('pkStage').hidden"), "the waiting bar is gone")
        tint = b.eval("(()=>{ const p=document.createElement('i'); p.style.background='var(--ok-soft)'; document.body.appendChild(p); const a=getComputedStyle(p).backgroundColor; p.remove(); "
                      "return [getComputedStyle(document.getElementById('snack')).backgroundColor, a]; })()")
        self.assertEqual(tint[0], tint[1], "the message is in the soft ok tint")
        # another change while it shows
        self.stage("High")
        b.wait("PKS.length===1", 15)
        b.pump(0.4)
        after = " ".join(b.eval("document.getElementById('snack').innerText").split())
        self.assertIn("The earlier save can still be undone in Activity", after)
        self.assertFalse(b.eval("document.getElementById('snack').classList.contains('ok')"), "no ok tint on the pointer to Activity")
        self.assertFalse(b.eval("document.getElementById('pkStage').hidden"), "the waiting bar is back")
        self.note(38, f"toast: {text!r}, then {after!r}")


class Page266(HandcheckCase):
    """Checks 39, 40 and 42. The shared hand-check vault and Chrome; the page's own data is set in memory and the page reloaded after."""
    EMPTY = "{v:1,meetings:[],mail:{needs:[],routine:[]},other:{needs:[],routine:[]},later:[],not_needed:[],counts:{}}"

    def test_c39_the_focused_ask_creaite_box_has_a_plain_border(self):
        """39. (#359) Click into the ask creaite box: its border is the accent colour, drawn once; nothing turns (no animation, no
        gradient, and the stylesheet no longer has the turning rule). The dots on the ask button are unchanged."""
        b = self.b
        b.eval("openChat(); 0")
        b.wait("document.getElementById('chIn') && document.getElementById('chIn').getClientRects().length", 10)
        reduced = b.eval("document.documentElement.hasAttribute('data-reduced')")
        b.call("Emulation.setFocusEmulationEnabled", enabled=True)            # a headless page has no focus of its own: :focus needs it
        try:
            b.eval("document.documentElement.removeAttribute('data-reduced'); document.getElementById('chIn').focus(); 0")
            b.pump(0.3)
            r = b.eval("(()=>{ const e=document.getElementById('chIn'), c=getComputedStyle(e), p=document.createElement('i'); p.style.color='var(--accent)'; document.body.appendChild(p); "
                       "const acc=getComputedStyle(p).color; p.remove(); return {anim:c.animationName, border:c.borderTopColor, acc, img:c.backgroundImage, focus:document.activeElement===e}; })()")
            self.assertTrue(r["focus"], "the box has focus")
            self.assertEqual(r["anim"], "none", "nothing turns")
            self.assertEqual(r["border"], r["acc"], "the border is the accent")
            self.assertNotIn("gradient", r["img"])
            rules = b.eval("[...document.styleSheets].flatMap(s=>{ try { return [...s.cssRules].map(x=>x.cssText); } catch(e) { return []; } }).filter(t=>/--mang|@keyframes mang/.test(t)).length")
            self.assertEqual(rules, 0, "the turning-border rules are gone from the stylesheet")
        finally:
            if reduced:
                b.eval("document.documentElement.setAttribute('data-reduced','')")
            b.eval("document.getElementById('chIn').blur(); 0")
            b.call("Emulation.setFocusEmulationEnabled", enabled=False)
        self.note(39, f"focused border {r['border']} = accent {r['acc']}, animation {r['anim']}")

    def intake(self, js_data):
        b = self.b
        b.eval("go('intake-review')")
        b.pump(0.8)                                  # opening the page reloads its data; set ours after
        b.eval(js_data)
        b.pump(0.5)

    def job(self):
        return self.b.eval("(()=>{ const l=document.querySelector('[data-irnext]'); if(!l) return null; const k=l.querySelector('button'); "
                           "return {job:l.dataset.irnext, text:l.querySelector('span').textContent.replace(/\\s+/g,' ').trim(), button:k?k.textContent.trim():null, disabled:k?k.disabled:null, title:k?k.title:null}; })()")

    def test_c40_a_clear_intake_names_the_next_job_with_one_button(self):
        """40. (#356) With nothing ready and nothing to approve, Intake says "Nothing is ready to process or approve." and one next job with one
        button, chosen from state: calendar not read today, "Next: refresh the calendar." (Refresh calendar); read today and the mail check
        due, "Next: check mail and Teams." (Check now); neither and tomorrow is in the saved calendar, "Next: open tomorrow's meetings."
        (Open tomorrow's meetings); none of these, the sentence alone. Later and Not needed are not drawn while they hold nothing. The first two are greyed out with a reason when ask creaite is busy
        or creaite isn't running; the third only moves to Today and is not. Nothing is shown while there is work to do. At 900 px the line
        fits and the button is 24 px or more."""
        b = self.b
        base = ("REV.splice(0); D.inbox=[]; D.dev=false; D.calendar=D.calendar||{days:{}}; D.intake_review=%s; shared.BUSY=false; shared.RUN=null; S.srcCalendar=true; " % self.EMPTY)
        tomorrow = "window.plusDays=n=>{const d=new Date(TODAY+'T12:00:00');d.setDate(d.getDate()+n);return d.toISOString().slice(0,10)}; "
        try:
            b.eval(tomorrow)
            self.intake(base + "D.sweep_due={due:true}; D.meetings=Object.assign({},D.meetings,{fetched:'2000-01-01 08:00'}); irTick.value++; 0")
            j = self.job()
            self.assertEqual((j or {}).get("job"), "refresh", j)
            self.assertEqual(j["text"], "Nothing is ready to process or approve. Next: refresh the calendar.")
            self.assertEqual(j["button"], "Refresh calendar")
            b.eval("window.__live=shared.LIVE; shared.LIVE=false; irTick.value++; 0")
            b.wait("document.querySelector('[data-irnext] button').disabled", 10)
            self.assertIn("isn", self.job()["title"])
            b.eval("shared.LIVE=window.__live; shared.BUSY=true; irTick.value++; 0")
            b.wait("document.querySelector('[data-irnext] button').disabled", 10)
            self.assertIn("busy", self.job()["title"])
            b.eval("shared.BUSY=false; irTick.value++; 0")
            for w in (900, 1400):
                with width(self, w):
                    b.pump(0.3)
                    fits = b.eval("(()=>{ const l=document.querySelector('[data-irnext]'), r=l.getBoundingClientRect(), k=l.querySelector('button').getBoundingClientRect(); "
                                  "return r.right<=innerWidth && document.scrollingElement.scrollWidth<=innerWidth && k.height>=24; })()")
                    self.assertTrue(fits, f"the line fits and the button is 24 px at {w}")
            fresh = "D.meetings=Object.assign({},D.meetings,{fetched:TODAY+' 08:00'}); D.days={days:[synthDay(TODAY)]}; "
            self.intake(base + "D.last_sweep='2000-01-01 07:00'; D.sweep_due={due:true}; " + fresh + "irTick.value++; 0")
            j = self.job()
            self.assertEqual((j or {}).get("job"), "mail", j)
            self.assertEqual((j["text"], j["button"]), ("Nothing is ready to process or approve. Next: check mail and Teams.", "Check now"))
            self.intake(base + "D.sweep_due={due:false}; " + fresh.replace("synthDay(TODAY)]", "synthDay(TODAY),synthDay(plusDays(1))]") + "irTick.value++; 0")
            j = self.job()
            self.assertEqual((j or {}).get("job"), "tomorrow", j)
            self.assertEqual((j["text"], j["button"]), ("Nothing is ready to process or approve. Next: open tomorrow’s meetings.", "Open tomorrow’s meetings"))
            b.eval("shared.BUSY=true; irTick.value++; 0")
            b.pump(0.3)
            self.assertFalse(self.job()["disabled"], "opening tomorrow is never greyed out for busy")
            b.eval("shared.BUSY=false; 0")
            self.intake(base + "D.sweep_due={due:false}; " + fresh + "irTick.value++; 0")
            j = self.job()
            self.assertEqual((j or {}).get("job"), "none", j)
            self.assertEqual((j["text"], j["button"]), ("Nothing is ready to process or approve.", None))
            self.assertEqual(b.eval("document.querySelectorAll('#v-intake-review [data-irsec=later], #v-intake-review [data-irsec=not_needed]').length"), 0,
                             "Later and Not needed are not drawn when they hold nothing")
            b.eval("go('intake-review'); 0")
            b.pump(1.0)
            self.assertEqual(b.eval("document.querySelectorAll('[data-irnext]').length"), 0, "nothing is shown while there is work to do")
        finally:
            b.reload("typeof go==='function' && LIVE")
        self.note(40, "refresh, mail, tomorrow and none read in turn; busy and offline grey out the first two with a reason")

    def test_c42_the_design_batch_work_files_and_the_cockpit(self):
        """42. (#343) Work's List has no "Show: Empty groups" (the Board still has it); Files says Word, Transcript, Excel for a file's type
        rather than the extension, in the list and in the Type filter; the cockpit's Top risks and issues rows show the owner after a dash
        ("You" for your own, or "No owner"); the help (?) button is at least 24 px; no text on the cockpit is under 12 px."""
        b = self.b
        # Work: List without, Board with
        try:
            b.eval("go('work')")
            b.click('#wtabs [data-t="actions"]')
            b.click('#wlay [data-lay="list"]')
            b.pump(0.3)
            b.eval("openDisp(); 0")
            self.assertFalse(b.eval("(()=>{ const e=document.getElementById('wshowempty'); return !!e && !!(e.offsetWidth||e.offsetHeight||e.getClientRects().length); })()"),
                             "the List's Display menu has no 'Empty groups' tick")
            b.eval("closeDisp(); 0")
            b.click('#wlay [data-lay="board"]')
            b.pump(0.3)
            b.eval("openDisp(); 0")
            self.assertTrue(b.eval("(()=>{ const e=document.getElementById('wshowempty'); return !!e && !!(e.offsetWidth||e.offsetHeight||e.getClientRects().length); })()"),
                            "the Board keeps 'Show: Empty groups'")
            b.eval("closeDisp(); 0")
        finally:
            b.click('#wlay [data-lay="list"]')
        # Files
        self.screen("files")
        types = b.eval("[...document.querySelectorAll('#filesTbl .ftype')].map(e=>e.textContent.trim())")
        self.assertTrue(types, "Files lists files")
        raw = [t for t in types if re.fullmatch(r"(?i)docx?|xlsx?|vtt|pptx?", t)]
        self.assertEqual(raw, [], f"a file's type is said in words, not as an extension: {sorted(set(types))}")
        self.assertTrue(set(types) & {"Word", "Transcript", "Excel", "PDF", "Note", "Text", "Web page", "Email", "PowerPoint"}, sorted(set(types)))
        # The cockpit
        self.screen("cockpit")
        owners = b.eval("[...document.querySelectorAll('#v-cockpit .rkrow .rk-o')].map(e=>e.textContent.trim())")
        self.assertTrue(owners, "the cockpit lists top risks")
        self.assertTrue(all(o and o != "you" for o in owners), owners)
        small = b.eval("[...document.querySelectorAll('#v-cockpit *')].filter(e=>e.childNodes.length&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&e.getClientRects().length&&parseFloat(getComputedStyle(e).fontSize)<12).length")
        self.assertEqual(small, 0, "no text on the cockpit is under 12 px")
        self.screen("today")
        sizes = b.eval("[...document.querySelectorAll('#v-today .legbtn')].filter(e=>e.getClientRects().length).map(e=>Math.round(Math.min(e.getBoundingClientRect().width,e.getBoundingClientRect().height)))")
        self.assertTrue(all(s >= 24 for s in sizes), f"the help buttons on Today are 24 px or more: {sizes}")
        self.note(42, f"files types {sorted(set(types))}; cockpit owners {sorted(set(owners))}; Today help buttons {sizes}")


def write_mail_proposal(vault, now, count):
    """A pending mail proposal of `count` new actions (what a mail check stages), for the mail cap. Returns its name."""
    day = (now or str(date.today()))[:10]
    name = f"proposed-{day}-1130-sweep-hc266-cap.json"
    due = (date.fromisoformat(day) + timedelta(days=30)).isoformat()
    mail = "Email · From: Priya Nair <priya.nair@meridian.example> · Subject: Harbour works · Sent: %s 09:00 · Link: https://outlook.example.test/owa/?ItemID=hc266-cap" % day
    items = [{"n": k, "op": "new", "table": "actions", "match": "strong", "flags": [], "decision": "pending",
              "values": {"project": "FAL", "description": f"Check item {k} of the harbour works", "owner": "Sara Khan", "due_date": due, "source": mail}}
             for k in range(1, count + 1)]
    (vault / "system/staging" / name).write_text(json.dumps({"created": f"{day}T09:00:00", "source_run": "cx-sweep", "files": [], "items": items}, indent=2), encoding="utf-8")
    return name


class Lead266(PastWorld266):
    """Check 41. The past-day world's Intake with seven mail suggestions staged."""
    N_MAIL = 7

    def waiting_ids(self):
        return self.b.eval("D.intake_review.meetings.filter(m=>m.stage==='arrived'&&m.state==='waiting'&&m.src!=='draft').map(m=>m.id)")

    def on_page(self, ids):
        return self.b.eval(f"{json.dumps(ids)}.filter(id=>document.querySelector('#v-intake-review [data-irm=\"'+id+'\"]')).length")

    def view(self, v):
        b = self.b
        b.eval(f"irOpen.value=null; document.querySelector('[data-irview={v}]').click(); 0")
        b.wait(f"irView.value==='{v}'", 10)
        b.pump(0.3)

    MAIL_ROWS = ("(()=>{ const h=document.querySelector('#v-intake-review [data-irsec=mail]'); const t=h&&h.nextElementSibling; "
                 "return t?t.querySelectorAll('tr.irprop').length:0; })()")

    def test_c41_intake_leads_with_the_work_in_all_three_views_and_mail_shows_five(self):
        """41. (#340) In the List, the Board and Two panes the waiting tail ("Waiting for the transcript") starts folded: none of those meetings
        is on the page, the heading shows their count and Show; Show brings all of them and Hide folds them again. In the List the mail and
        Teams section comes before that tail. Mail and Teams shows five suggestions and "Show all n", which shows all n and then "Show the
        first 5"; Approve routine (n) counts only the rows shown."""
        b = self.b
        write_mail_proposal(self.vault, self.now, self.N_MAIL)
        self.world()
        self.intake()
        waiting = self.waiting_ids()
        self.assertGreaterEqual(len(waiting), 2, "the world has meetings waiting for a transcript")
        seen = []
        for v in ("list", "board", "two"):
            self.view(v)
            self.assertEqual(self.on_page(waiting), 0, f"{v}: the waiting tail starts folded")
            head = b.eval("(()=>{ const h=document.querySelector('#v-intake-review [data-irsec=waiting] h2'); return h?h.textContent.replace(/\\s+/g,' ').trim():null; })()")
            self.assertTrue(head and head.startswith("Waiting for the transcript") and str(len(waiting)) in head, f"{v}: {head!r}")
            b.click("#v-intake-review [data-irfold=waiting]")
            b.wait(f"{json.dumps(waiting)}.every(id=>document.querySelector('#v-intake-review [data-irm=\"'+id+'\"]'))", 10)
            b.click("#v-intake-review [data-irfold=waiting]")
            b.wait(f"{json.dumps(waiting)}.every(id=>!document.querySelector('#v-intake-review [data-irm=\"'+id+'\"]'))", 10)
            # mail: five, then all
            self.assertEqual(b.eval(self.MAIL_ROWS), 5, f"{v}: mail and Teams shows five")
            btn = b.eval("(document.querySelector('#v-intake-review [data-ira=mailall]')||{textContent:''}).textContent.trim()")
            m = re.fullmatch(r"Show all (\d+)", btn)
            self.assertTrue(m and int(m.group(1)) >= self.N_MAIL, f"{v}: {btn!r}")
            total = int(m.group(1))
            routine = b.eval("(()=>{ const k=[...document.querySelectorAll('#v-intake-review button')].find(x=>/^Approve routine \\(\\d+\\)/.test(x.textContent.trim())); "
                             "return k?+k.textContent.match(/\\((\\d+)\\)/)[1]:null; })()")
            if routine is not None:
                self.assertLessEqual(routine, 5, f"{v}: Approve routine counts only the rows shown")
            b.click("#v-intake-review [data-ira=mailall]")
            b.wait(f"({self.MAIL_ROWS})=={total}", 10)
            self.assertEqual(b.eval("document.querySelector('#v-intake-review [data-ira=mailall]').textContent.trim()"), "Show the first 5", v)
            b.click("#v-intake-review [data-ira=mailall]")
            b.wait(f"({self.MAIL_ROWS})==5", 10)
            seen.append(v)
        # the List: the work comes before the waiting tail
        self.view("list")
        order = b.eval("(()=>{ const m=document.querySelector('#v-intake-review [data-irsec=mail]'), a=document.querySelector('#v-intake-review [data-irsec=waiting]'); "
                       "return !!(m && a && (m.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING)); })()")
        self.assertTrue(order, "in the List, mail and Teams comes before the waiting tail")
        self.note(41, f"views {seen}: {len(waiting)} waiting meetings folded and shown; mail 5 of {total}")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# #338: the lighter rules file (check 32)
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

RULES_SHARE = 0.6            # the shipped rules may be at most this share of their 2.6.3 size (they are about half)
RULES_2_6_3 = 66315          # bytes of system/creaite-rules.md in 2.6.3 (dev/proposals/338/README.md)


def rules_problems(slim, ref, orig, chain):
    """What is wrong with a slimmed rules file, as plain sentences (an empty list is clean). `slim` and `ref` are the shipped rules and
    reference text, `orig` the 2.6.3 rules. Reuses the retained-rules test's own helpers (dev/tests/test_rules_retained_338.py)."""
    import test_rules_retained_338 as keep
    out = []
    if len(slim.encode()) > RULES_SHARE * len(orig.encode()):
        out.append(f"the rules are {len(slim.encode())} bytes: more than {int(RULES_SHARE * 100)}% of {len(orig.encode())}")
    if not ref.strip():
        out.append("the reference file is missing or empty")
    if keep.REF_PATH not in slim:
        out.append("the rules do not point to the reference file")
    out += ["lost: " + s[:90] for s in keep.missing(slim, ref, orig, chain)]
    out += ["never clause lost: " + c[:90] for c in keep.unaccounted(orig, slim, chain)]
    return out


class Rules266(Engine266):
    """Check 32. The vault's own copy of the rules and the reference file (the release zip's), against the 2.6.3 rules."""

    def test_c32_the_rules_are_half_the_size_the_reference_is_there_and_every_never_survives(self):
        """32. (#338) system/creaite-rules.md in the release is at most 60% of its 2.6.3 size (66,315 bytes); system/templates/
        creaite-reference.md is in the release and the rules point to it; the Non-negotiables (the never list and the approval rules)
        are unchanged and every other "never" clause of the 2.6.3 rules is in the short file or, word for word, in the reference. Four
        mutants (a never clause dropped, the `.git` clause changed, the reference gone, the pointer gone) each turn the check red."""
        import test_rules_retained_338 as keep
        orig, _slim = keep.states()
        chain = keep.CHAIN_MARK in orig
        self.assertEqual(len(orig.encode()), RULES_2_6_3, "the 2.6.3 baseline moved: update RULES_2_6_3 with the README of #338")
        slim = (self.vault / "system/creaite-rules.md").read_text(encoding="utf-8")
        ref_file = self.vault / "system/templates/creaite-reference.md"
        self.assertTrue(ref_file.is_file(), "the release has no system/templates/creaite-reference.md")
        ref = ref_file.read_text(encoding="utf-8")
        self.assertEqual(rules_problems(slim, ref, orig, chain), [], "the shipped rules lost something")
        # mutants: each must be seen
        never_edit = "Never edit `system/tracker.db` with ad-hoc SQL"
        git_clause = "(shell start-up files, LaunchAgents, `.git`)"
        for what, s, r in (("a never clause dropped", slim.replace(never_edit, "Edit `system/tracker.db` with ad-hoc SQL", 1), ref),
                           ("the .git clause changed", slim.replace(git_clause, "(shell start-up files, LaunchAgents)", 1), ref),
                           ("the reference file gone", slim, ""),
                           ("the pointer to the reference gone", slim.replace(keep.REF_PATH, "system/templates/other.md"), ref),
                           ("the rules back at full size", slim + "x" * (len(orig.encode()) - len(slim.encode())), ref)):
            if s == slim and r == ref:
                self.fail("the mutant does not apply: " + what)
            self.assertTrue(rules_problems(s, r, orig, chain), "the check stays green when: " + what)
        self.note(32, f"rules {len(slim.encode())} bytes against {len(orig.encode())} in 2.6.3 ({len(slim.encode()) * 100 // len(orig.encode())}%); "
                      f"reference {len(ref.encode())} bytes; no never clause lost; 5 mutants turn it red")


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 2.6.6: the release cut (checks 43 to 48), #341 (49 to 67), #358 (68 to 72) and #362 (73 to 75)
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

NODE = shutil.which("node")
CSS_FILE = REPO / "system/templates/dashboard/style.css"
SIDE_TAB_JS = """(()=>{ const r=[]; for(const e of document.querySelectorAll('body *')){ if(!e.getClientRects().length) continue; const c=getComputedStyle(e);
  const l=parseFloat(c.borderLeftWidth); if(l>=3&&c.borderLeftStyle!=='none'&&parseFloat(c.borderRightWidth)<l&&parseFloat(c.borderTopWidth)<l) r.push(e.tagName+'.'+e.className);
  if(/inset -?[2-9]px 0px 0px/.test(c.boxShadow)) r.push('SHADOW '+e.tagName+'.'+e.className); } return r.slice(0,20); })()"""
# the words the plain notes and What's new may not use (test_plain_words's list, plus the private word and the followed-person field)
OLD_WORDS = r"\bRAID\b|\bMilestone slip\b|\bFlow\b"


def node_run(path, script):
    """Run `script` under Node with `f` = the ES module at `path`; the JSON its last line prints."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix="hc266-") as d:
        m = Path(d) / "m.mjs"
        m.write_text((REPO / path).read_text(encoding="utf-8"), encoding="utf-8")
        r = subprocess.run([NODE, "--input-type=module", "-e", "const f = await import(%s);\n%s" % (json.dumps(m.as_uri()), script)],
                           capture_output=True, text=True, timeout=90)
    if r.returncode:
        raise RuntimeError(r.stderr[-800:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class Static266(HandcheckCase):
    """Checks that read the repository's own files, or run its pure code under Node or Python: no vault, server or browser."""
    shared_server = False

    @classmethod
    def setUpClass(cls):
        cls.idle = not cls.runnable()

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        n = self.check_number()
        if only() and n not in only():
            self.skipTest("not in --only")

    def py_repo(self, code):
        """The JSON the code prints (its last line), run in the repository with its system/scripts on the path, isolated."""
        r = subprocess.run([sys.executable, "-I", "-c", "import sys, json\nsys.path.insert(0, 'system/scripts')\n" + code], cwd=REPO,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    # ── the cut ──

    @known("VERSION is still 2.6.5 on v266-line: VERSION is a guarded file, raised by the cut, not by the notes and sheet")
    def test_c43_version(self):
        """43. VERSION is a version the tooling accepts and is 2.6.6."""
        v = read_repo("VERSION").strip()
        self.assertRegex(v, r"^\d+\.\d+\.\d+$")
        self.assertEqual(v, "2.6.6")

    def test_c44_notes(self):
        """44. What's new has the 2.6.6 section above 2.6.5 and names #341, #358 and #362; the plain notes and this sheet exist; the plain
        notes and What's new use none of the words the plain-words test bans, nor the private word, nor a capital A in ask creaite."""
        wn = read_repo("system/templates/help/whats-new.md")
        heads = re.findall(r"^## creaite (\d+\.\d+\.\d+)\s*$", wn, re.M)
        self.assertEqual(heads[:2], ["2.6.6", "2.6.5"])
        sec = wn.split("## creaite 2.6.5\n")[0]
        for n in ("341", "358", "362"):
            self.assertIn(f"(#{n})", sec, f"What's new does not mention #{n}")
        self.assertTrue((REPO / "dev/handchecks/v2.6.6.md").exists())
        plain = read_repo("dev/release-notes/2.6.6-plain.md")
        import test_plain_words as tpw
        for name, pat in tpw.PATTERNS.items():
            for text, where in ((plain, "plain notes"), (sec, "What's new")):
                self.assertIsNone(pat.search(text), f"{where}: the banned word ({name}): {pat.search(text) and pat.search(text).group(0)}")
        for text in (plain, sec):
            self.assertNotRegex(text, r"(?i)\bvip\b|followed (person|people)")
            self.assertNotIn("Ask creaite", text)

    @known("the guides still carry 2.6.5: they are raised with VERSION by the cut")
    def test_c45_guides(self):
        """45. Both guides carry 2.6.6 and no 2.6.5 string."""
        for g in ("guide-first-day.html", "guide-how-to.html"):
            t = read_repo(f"system/templates/{g}")
            self.assertIn("creaite 2.6.6 ·", t)
            self.assertNotIn("2.6.5", t)

    def test_c46_guarded_unchanged(self):
        """46. No guarded file differs from the v2.6.4 release (2.6.5 and 2.6.6 have no guarded change) and the 2.6.4 chain list is unchanged."""
        def git(*a):
            return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True)
        if git("rev-parse", "-q", "--verify", "v2.6.4").returncode:
            self.skipTest("no v2.6.4 tag here")
        guarded = ["system/creaite-rules.md", "system/scripts/tracker.py", "system/scripts/filechange.py", "system/scripts/reach.py",
                   "system/scripts/permissions.py", "system/scripts/backup.py", "system/scripts/update.py", "system/scripts/live_server.py",
                   "system/scripts/client_leak.py", "system/scripts/edit_ai.py", "system/scripts/draft_delivery.py", ".claude/settings.json"]
        d = git("diff", "--name-only", "v2.6.4", "HEAD", "--", *guarded).stdout.split()
        self.assertEqual(d, [], f"guarded files changed since 2.6.4: {d}")
        old = [x for x in git("show", "v2.6.4:dev/proposals/GUARDED-2.6.4.chain").stdout.splitlines() if x and not x.startswith("#")]
        new = [x for x in read_repo("dev/proposals/GUARDED-2.6.4.chain").splitlines() if x and not x.startswith("#")]
        self.assertEqual(old, new, "the 2.6.4 chain list changed")

    def test_c47_the_2_6_5_work_is_still_there(self):
        """47. What 2.6.5 added is still in the source: the waiting tail and Show all (#340), the next job and tomorrow (#356), "Saved N changes"
        (#357), the plain border on the ask box (#359), People's Display menu on D (#360), Word, Transcript and Excel in Files (#343)."""
        t = tree_js("components/intakeReview") + tree_js("core") + tree_js("stores")
        self.assertIn("Waiting for the transcript", t)
        self.assertIn("Show all", t)
        self.assertRegex(tree_js("components") + tree_js("stores") + tree_js("core"), r"(?i)next job")
        self.assertRegex(read_repo("system/templates/dashboard/src/components/today/WeekAhead.jsx"), r"(?i)tomorrow")
        self.assertRegex(read_repo("system/templates/dashboard/src/components/Toast.jsx") + read_repo("system/templates/dashboard/src/panel.js"), r"Saved \$\{\w+\} change")
        self.assertRegex(read_repo("system/templates/dashboard/style.css"), r"(?s)#askIn[^{}]*:focus[^{}]*\{[^}]*border-color|ask[^{}]*:focus[^{}]*\{[^}]*border-color")
        for f in ("core/displayMenu.js", "core/peopleDisplay.js", "stores/peopleDisplay.js", "components/people/PeopleDisplay.js"):
            self.assertTrue((DASH / f).exists(), f)
        self.assertRegex(read_repo("system/templates/dashboard/src/core/keys.js"), r"""['"]d['"]|\bKeyD\b|key\s*===\s*['"]d['"]""")
        files = read_repo("system/templates/dashboard/src/files.js")
        for w in ("Word", "Transcript", "Excel"):
            self.assertIn(w, files)

    def test_c48_355_followups(self):
        """48. A failed Track change clears the Filed note and renaming minutes follows an update item's source (#355; its own test, no browser)."""
        r = subprocess.run([sys.executable, str(REPO / "dev/tests/test_355_followups.py")], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])

    # ── #341 that needs no page ──

    def test_c67_amber_is_a_list_and_nothing_else(self):
        """67. (#341 item 17) Amber is a list for Alan to decide on, not a change: the list is there, says nothing is changed by it, covers the
        meanings of --warn, and the stylesheet still defines --warn."""
        t = read_repo("dev/proposals/341/AMBER-USES.md")
        self.assertIn("Nothing is changed by this list", t)
        self.assertRegex(t, r"Keep amber \(at risk\)")
        self.assertRegex(t, r"(?m)^\| Change to teal")
        self.assertIn("--warn:", read_repo("system/templates/dashboard/style.css"))

    # ── #358 ──

    @unittest.skipUnless(NODE, "needs Node")
    def test_c68_the_true_line_has_places_and_counts_and_no_total(self):
        """68. (#358) The line a mail check shows reads "Looked in so far: Outlook mail, Teams · 2 searches, 1 item read": the places it has
        searched, in a fixed order, and counts of searches and reads; "Starting" before the first search; no total, no "of n", no
        percentage, nothing "finished"; the badge says the places and never a counter; a mail subject that holds the words mail, Teams or
        Calendar changes nothing."""
        o = node_run("system/templates/dashboard/src/core/mailCheck.js", """
let s = f.mcNew(); const out = {start: f.mcLine(s)};
s = f.mcStep(s, "Microsoft 365: teams list chats"); s = f.mcStep(s, "Microsoft 365: outlook email search"); s = f.mcStep(s, "Microsoft 365: read resource");
out.line = f.mcLine(s); out.badge = f.mcBadge(s); out.places = f.mcPlaces(s);
const hostile = f.mcStep(s, "Running tracker.py Zebra Quarterly Budget Teams Mail Calendar Channel"); out.same = JSON.stringify(hostile) === JSON.stringify(s);
const many = ["Searching mail","Searching mail","Reading Teams chats","Reading the calendar","Reading a meeting, a message or a chat"].reduce(f.mcStep, f.mcNew());
out.many = f.mcLine(many); out.badgeStart = f.mcBadge(f.mcNew());
console.log(JSON.stringify(out));""")
        self.assertEqual(o["start"], "Starting")
        self.assertEqual(o["line"], "Looked in so far: Outlook mail, Teams · 2 searches, 1 item read")
        self.assertEqual(o["many"], "Looked in so far: Outlook mail, Teams, calendar · 4 searches, 1 item read")
        self.assertEqual(o["badge"], "Mail check: mail, Teams")
        self.assertEqual(o["badgeStart"], "Mail check: starting")
        self.assertEqual(o["places"], "Looked in so far: Outlook mail, Teams")
        self.assertTrue(o["same"], "a label that is not a fixed Microsoft 365 step changes nothing")
        for text in (o["line"], o["many"], o["badge"]):
            self.assertNotRegex(text, r"\bof \d|%|[Ff]inished|[Dd]one")
        self.assertFalse(re.search(r"\d", o["badge"]), "no counter in the badge")

    @unittest.skipUnless(NODE and shutil.which("python3"), "needs Node")
    def test_c69_a_mail_check_loses_the_quip_and_ends_with_found_n_in_the_page(self):
        """69. (#358) In the page, against the live server and a stand-in Claude that streams real tool labels (the line's own test_mail_check.py,
        run with its own server and Chrome, at 1400 and 900 px): a mail check shows the true line in place of the quip and ends "Finished.
        Looked in Outlook mail, Teams, calendar. Found 2 new, 1 needs a project."; only a mail check loses the quip; Stop and a failed run
        end with "Stopped. ... Nothing saved yet." and "Stopped early. ..."; no mail subject, command or label text reaches the page."""
        tests = [f"MailCheck1400.{t}" for t in ("test_the_true_line_replaces_the_quip_and_ends_with_found_n", "test_only_a_mail_check_loses_the_quip",
                                                  "test_stopped_and_failed_endings")] + ["MailCheck900.test_the_true_line_replaces_the_quip_and_ends_with_found_n"]
        env = {k: v for k, v in os.environ.items() if not k.startswith(("CREAITE_HC", "CREAITE_NOW", "CREAITE_PORT", "CREAITE_CLAUDE"))}
        r = subprocess.run([sys.executable, str(REPO / "dev/tests/test_mail_check.py"), *tests], cwd=REPO, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, (r.stdout + r.stderr)[-2500:])
        self.note(69, "test_mail_check.py: " + (r.stderr.strip().splitlines() or [""])[-1])

    @unittest.skipUnless(NODE, "needs Node")
    def test_c70_found_n_counts_new_items_from_the_checks_own_files(self):
        """70. (#358) Found N counts the new items in the check's own saved suggestions (a file named proposed-DATE-HHMM-sweep[-n]) made between
        the minute the check started and the minute it ended; an update to an item you already have, a file made on the dashboard, a file
        outside the window and an item with no kind are not counted; the closing line reads "Found 7 new, 4 need a project." (or "1 needs a
        project"); a check that finds nothing says "Nothing new to review."; a check that could not read Review says to open it."""
        o = node_run("system/templates/dashboard/src/core/mailCheck.js", """
const N="new", U="update", sw="proposed-2026-10-25-0905-sweep.json";
const rows = [{file: sw, op: N, p: "ABC"}, {file: sw, op: N, p: ""}, {file: "proposed-2026-10-25-0906-sweep-2.json", op: N, p: null},
  {file: "proposed-2026-10-25-0905-dashboard-x.json", op: N, p: ""}, {file: "proposed-2026-10-25-0850-sweep.json", op: N, p: ""},
  {file: "proposed-2026-10-25-0920-sweep.json", op: N, p: ""}, {file: "m.docx", op: N, p: ""},
  {file: sw, op: U, p: ""}, {file: "proposed-2026-10-25-0906-sweep-2.json", op: U, p: "ABC"}, {file: sw, p: ""}];
const out = {found: f.mcFound(rows, "2026-10-25T09:04:10", "2026-10-25T09:10:59"), updatesOnly: f.mcFound(rows.filter(r => r.op === U), "2026-10-25T09:04:10", "2026-10-25T09:10:59")};
const two = f.mcStep(f.mcStep(f.mcNew(), "Searching mail"), "Reading Teams channels");
out.ends = [f.mcEnd("done", two, {n: 7, need: 4}), f.mcEnd("done", two, {n: 1, need: 1}), f.mcEnd("done", two, {n: 0, need: 0}), f.mcEnd("done", two, null),
  f.mcEnd("stopped", two, {n: 2, need: 1}), f.mcEnd("early", two, {n: 2, need: 2}), f.mcEnd("stopped", two, {n: 0, need: 0})];
console.log(JSON.stringify(out));""")
        self.assertEqual(o["found"], {"n": 3, "need": 2}, "new items only, inside the window, from the check's own files")
        self.assertEqual(o["updatesOnly"]["n"], 0, "an update is not a new item")
        self.assertEqual(o["ends"], [
            "Finished. Looked in Outlook mail, Teams. Found 7 new, 4 need a project.",
            "Finished. Looked in Outlook mail, Teams. Found 1 new, 1 needs a project.",
            "Finished. Nothing new to review.",
            "Finished. Open Review to see what it found.",
            "Stopped. Looked in Outlook mail, Teams. Found 2 new so far, 1 needs a project.",
            "Stopped early. Looked in Outlook mail, Teams. Found 2 new so far, 2 need a project.",
            "Stopped. Looked in Outlook mail, Teams. Nothing saved yet."])

    @unittest.skipUnless(NODE, "needs Node")
    def test_c71_close_the_day_rows_tick_from_their_own_searches(self):
        """71. (#358) Close the day's rows Mail, Teams chats and Teams channels tick only from a finished step with exactly that job (its fixed
        label); a label that merely holds the words (a mail subject with "Teams" in it, a command naming mail, Teams and a channel, a
        longer or shorter label) ticks nothing; the calendar and a script step tick nothing; "Matching to projects" is never ticked by a
        step; before the first step no row shows as the one in progress, and then the first row not yet ticked does."""
        o = node_run("system/templates/dashboard/src/core/closeDayRows.js", """
const good = ["Searching mail", "Microsoft 365: outlook email search", "Searching Teams chats", "Reading Teams chats", "Microsoft 365: teams list chats",
  "Microsoft 365: chat message search", "Reading Teams channels", "Microsoft 365: teams list channel messages"];
const hostile = ["Running sweep.py stage mail Teams channel", "Zebra Quarterly Budget Teams Mail Calendar Channel", "Searching mail and Teams", "searching mail",
  "Microsoft 365: outlook email search extra", "Reading Teams", "Reading the calendar", "Staging what the sweep found", "Matching to projects", "", null, 7];
console.log(JSON.stringify({good: good.map(f.cdSourceOf), hostile: hostile.map(f.cdSourceOf),
  now: [f.cdNow({steps: 0, done: []}), f.cdNow({steps: 1, done: []}), f.cdNow({steps: 3, done: [0, 1]}), f.cdNow({steps: 4, done: [0, 1, 2]})]}));""")
        self.assertEqual(o["good"], [0, 0, 1, 1, 1, 1, 2, 2])
        self.assertEqual(o["hostile"], [-1] * 12, "a hostile label ticks nothing")
        self.assertEqual(o["now"], [-1, 0, 2, -1])

    @known("#358 M2 (Stark): a check that saved only updates to existing items ends 'Finished. Nothing new to review.', which reads as if nothing was found")
    @unittest.skipUnless(NODE, "needs Node")
    def test_c72_a_check_that_found_only_updates_does_not_say_nothing_new(self):
        """72. (#358) When a check saved only updates to items you already have (Found 0 new), its closing line does not say "Nothing new to
        review."; it says what it did find."""
        o = node_run("system/templates/dashboard/src/core/mailCheck.js", """
const rows = [{file: "proposed-2026-10-25-0905-sweep.json", op: "update", p: "ABC"}, {file: "proposed-2026-10-25-0905-sweep.json", op: "update", p: "ABC"}];
const found = f.mcFound(rows, "2026-10-25T09:04:10", "2026-10-25T09:10:59"), s = f.mcStep(f.mcNew(), "Searching mail");
console.log(JSON.stringify({found, end: f.mcEnd("done", s, found)}));""")
        self.assertEqual(o["found"]["n"], 0)
        self.assertNotIn("Nothing new to review", o["end"], o["end"])

    # ── #362 ──

    PROJECTS = '[{"code": "ABC", "name": "Harbour Upgrade"}, {"code": "DEF", "name": "Orchard Rollout"}, {"code": "ORX", "name": "Quay Works"}, {"code": "ORX2C", "name": "Quay Works Two"}]'

    def matches(self, cases):
        """[(title, memory)] -> [[code, how]]: build_dashboard.prep_match, the one matcher."""
        return self.py_repo("import build_dashboard as bd\nP = json.loads(%r)\nprint(json.dumps([list(bd.prep_match(t, P, m)) for t, m in json.loads(%r)]))"
                            % (self.PROJECTS, json.dumps(cases)))

    def test_c73_a_code_in_the_title_beats_the_remembered_series(self):
        """73. (#362) A project code in a meeting's title wins over the series Alan chose before: "[DEF] Weekly sync" is DEF although "weekly sync"
        was remembered as ABC; the tag in any case ("[def]", "[ def ]") and the code alone as a word ("DEF Weekly sync") do the same; codes
        match whole (ORX is not ORX2C); with no code in the title the remembered series is still used; a tag that is no project's code is no
        code; the "no project" choice for a series still stands; the matched code is the same as the remembered one when they agree."""
        mem = {"weekly sync": "ABC"}
        got = self.matches([["[DEF] Weekly sync", mem], ["[def] Weekly sync", mem], ["[ def ] Weekly sync", mem], ["DEF Weekly sync", {"def weekly sync": "ABC"}],
                            ["[ORX2C] Weekly sync", {"weekly sync": "ORX"}], ["[ORX] Weekly sync", {"weekly sync": "ORX2C"}],
                            ["Weekly sync", mem], ["[ABC] Weekly sync", mem], ["[ZZZ] Weekly sync", mem], ["[ABC] Weekly sync", {"weekly sync": "_portfolio"}]])
        self.assertEqual(got, [["DEF", "matched"], ["DEF", "matched"], ["DEF", "matched"], ["DEF", "matched"], ["ORX2C", "matched"], ["ORX", "matched"],
                               ["ABC", "remembered"], ["ABC", "remembered"], ["ABC", "remembered"], ["_portfolio", "remembered"]])

    def test_c74_two_different_codes_win_nothing(self):
        """74. (#362) A title that names two different projects gives "Not sure" (no project, "unsure") whatever was remembered, in either order,
        in any case and with the second code written as a word; nothing is chosen for the person."""
        titles = ["[ABC] [DEF] Weekly sync", "[abc][def] Weekly sync", "[DEF] Weekly sync with ABC", "[DEF][ABC] Weekly sync"]
        got = self.matches([[t, m] for t in titles for m in ({"weekly sync": "ABC"}, {})])
        self.assertEqual(got, [[None, "unsure"]] * len(got))

    def test_c75_a_confidential_meeting_shows_no_project_data(self):
        """75. (#362) A confidential meeting's Intake row carries no project, name, code, domain, reason or match level, even when its title holds
        a code; the same meeting not confidential keeps its project."""
        o = self.py_repo("""import build_dashboard as bd
from datetime import date
def row(**kw):
    m = {"id": "e1", "title": "[DEF] Catch-up", "day": "2026-10-20", "start": "10:00", "end": "11:00", "confidential": True, "p": "DEF", "how": "matched",
         "level": "likely", "reason": "Orchard Rollout fits orchard.example", "cands": ["DEF"], "offer": {"kind": "domain", "value": "orchard.example"}, "series": "catch up"}
    m.update(kw)
    return bd._ir_calendar(m, {}, date.today(), 7)
c, n = row(), row(confidential=False)
print(json.dumps({"p": c["p"], "text": json.dumps(c), "open_p": n["p"]}))""")
        self.assertIsNone(o["p"])
        for leak in ("DEF", "Orchard", "orchard.example", "likely", "fits"):
            self.assertNotIn(leak, o["text"].replace("[DEF] Catch-up", ""), leak)
        self.assertEqual(o["open_p"], "DEF")


def read_repo(p):
    return (REPO / p).read_text(encoding="utf-8")


def tree_js(sub):
    return "\n".join(f.read_text(encoding="utf-8") for f in sorted((DASH / sub).rglob("*")) if f.suffix in (".js", ".jsx"))


class Look266(HandcheckCase):
    """Checks 49 to 66: #341's design decisions, measured in the live app (the shared hand-check vault and Chrome; nothing is changed
    for good: a check that moves the page's own state puts it back, and each check starts on a page of its own)."""

    def test_c49_no_side_tab_accents(self):
        """49. (#341 item 1) No note, tip, status or quote has a thick coloured bar down its left side: the stylesheet has no one-sided border
        of 3 px or more (the A4 preview's quote keeps its 3 px edge) and no inset bar of 2 px or more (the column drop marker keeps its 3 px);
        the three icons that replace them exist; and on Today, Work, Intake, Files, Activity, Projects, a cockpit, Milestones, People, Help
        and three Settings tabs no element on screen has a left edge of 3 px or more thicker than its other sides."""
        css = CSS_FILE.read_text(encoding="utf-8")
        thick = [n for n in re.findall(r"border-left:\s*(\d+)px\s+solid", css) if int(n) >= 3]
        self.assertEqual(thick, ["3"], "only the A4 preview's quote may keep a 3 px edge")
        bars = [n for n in re.findall(r"box-shadow:inset (\d+)px 0 0", css) if int(n) >= 2]
        self.assertEqual(bars, ["3"], "only the column drop marker may keep a side bar")
        b, found = self.b, {}
        for name in ("--ic-info", "--ic-alert", "--ic-quote"):
            self.assertTrue(b.eval("getComputedStyle(document.documentElement).getPropertyValue(%s).trim().startsWith('url(')" % json.dumps(name)), name)
        for sc in ("today", "work", "intake-review", "files", "activity", "projects", "cockpit", "milestones", "people", "help",
                   "settings-essentials", "settings-advanced", "settings-health"):
            self.screen(sc)
            hit = b.eval(SIDE_TAB_JS)
            if hit:
                found[sc] = hit
        self.assertEqual(found, {}, "elements with a side tab")

    def test_c50_reviews_what_changes_line_is_as_big_as_the_title(self):
        """50. (#341 item 2) In Intake, the line that says what a suggestion changes is 14 px, the same as the title above it, and stands out
        by weight (600 or more), not by size."""
        self.screen("intake-review")
        r = self.b.eval("({chg:[...document.querySelectorAll('#v-intake-review .icchg')].map(e=>[getComputedStyle(e).fontSize,+getComputedStyle(e).fontWeight]),"
                        " ttl:[...document.querySelectorAll('#v-intake-review .icttl')].map(e=>getComputedStyle(e).fontSize)})")
        self.assertTrue(r["chg"] and r["ttl"], r)
        for size, weight in r["chg"]:
            self.assertEqual(size, "14px")
            self.assertGreaterEqual(weight, 600)
        self.assertEqual(set(r["ttl"]), {"14px"})
        self.note(50, f"{len(r['chg'])} what-changes lines, 14 px, weight {r['chg'][0][1]}")

    def test_c51_projects_dates_counts_and_a_health_that_is_not_set(self):
        """51. (#341 items 3 to 5) On Projects: the next milestone's date is DD-MM-YYYY with "(in n days)", never written out; the Evidence
        column shows only the figures above zero (no "Overdue 0", "Urgent risks 0", "Warnings 0" or "Slip none"); a project with all of
        them zero shows "Nothing flagged"; a project whose health is Not set gives its reason and "Next: open the project and choose a
        health." (or, with no reason, "No update has set a health yet. Next: ..."). Today's own table keeps the written-out date and
        its figures."""
        b = self.b
        self.screen("projects")
        rows = b.eval("[...document.querySelectorAll('#v-projects tbody tr')].map(r=>r.innerText.replace(/\\s+/g,' ').trim())")
        self.assertGreaterEqual(len(rows), 3)
        for r in rows:
            self.assertRegex(r, r"\b\d{2}-\d{2}-\d{4} \((in \d+ days?|\d+ days? ago|today|tomorrow|yesterday)\)", r)
            self.assertNotRegex(r, r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\b", r)
            self.assertNotRegex(r, r"(Overdue|No date|Urgent risks|Warnings) 0\b|Slip none", r)
        got = b.eval("""(()=>{ const strip=h=>h.replace(/<[^>]+>/g,' ').replace(/\\s+/g,' ').trim(), o=[P[3].health,P[3].reason];
          const r={nothing:strip(evidence({code:'ZZZ',slip:0},true)), today:strip(evidence({code:'ZZZ',slip:0},false))};
          P[3].health=''; const a=strip(portfolioTable('pj')); P[3].reason=''; const c=strip(portfolioTable('pj')); const d=strip(portfolioTable('pf'));
          P[3].health=o[0]; P[3].reason=o[1];
          r.withReason=a.slice(a.indexOf('Tide')); r.noReason=c.slice(c.indexOf('Tide')); r.todayRow=d.slice(d.indexOf('Tide')); return r; })()""")
        self.assertEqual(got["nothing"], "Nothing flagged")
        self.assertRegex(got["today"], r"Overdue 0 · No date 0 · Urgent risks 0 · Slip none · Warnings 0")
        self.assertRegex(got["withReason"], r"Not set .* Next: open the project and choose a health\.")
        self.assertRegex(got["noReason"], r"Not set No update has set a health yet\. Next: open the project and choose a health\.")
        self.assertRegex(got["todayRow"], r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) \d+(st|nd|rd|th) \w+ \(in \d+ days?\)", "Today's table keeps its own date")
        self.note(51, f"{len(rows)} projects; not set: {got['noReason'][:90]}")

    def test_c52_work_has_no_glyphs_before_a_title(self):
        """52. (#341 item 6) In Work (Actions, Risks and issues, Decisions and All) no half-circle or signal-bar mark stands before a title; the
        status and priority are still said, for screen readers, in words ("Open, High priority: ")."""
        b = self.b
        self.screen("work")
        seen = 0
        for tab in ("actions", "raid", "decisions", "all"):
            if b.eval("!document.querySelector('#wtabs [data-t=%s]')" % tab):
                continue
            b.click('#wtabs [data-t="%s"]' % tab)
            b.pump(0.4)
            r = b.eval("({n:document.querySelectorAll('#workTbl td.title .wkm').length, svg:document.querySelectorAll('#workTbl td.title .wkm svg').length,"
                       " vh:[...document.querySelectorAll('#workTbl td.title .wkm .vh')].slice(0,3).map(e=>e.textContent), w:[...document.querySelectorAll('#workTbl td.title .wkm')].slice(0,3).map(e=>e.getBoundingClientRect().width)})")
            self.assertEqual(r["svg"], 0, f"{tab}: a mark is drawn before a title")
            if r["n"]:
                seen += 1
                self.assertTrue(all(v.strip() for v in r["vh"]), f"{tab}: the status is said in words: {r['vh']}")
                self.assertTrue(all(w < 2 for w in r["w"]), f"{tab}: the empty wrapper takes no room: {r['w']}")
        self.assertGreaterEqual(seen, 2, "Work lists items")

    def _look(self, js_pick):
        """The background and bar of an element picked by `js_pick` (an expression for the row's first cell)."""
        return self.b.eval("(()=>{ const td=%s; if(!td) return null; const c=getComputedStyle(td); return {bg:c.backgroundColor, shadow:c.boxShadow, cls:td.parentElement.className}; })()" % js_pick)

    def test_c53_a_ticked_and_an_open_meeting_share_one_look_in_the_list(self):
        """53. (#341 item 7) In Intake's List, a ticked meeting (a file you added, ticked) and the open meeting have the same look: the soft accent
        tint with a 2 px accent line above and below, and the tick before a ticked title."""
        b = self.b
        self.screen("intake-review")
        b.eval("irOpen.value=null; document.querySelector('[data-irview=list]').click(); 0")
        b.pump(0.4)
        b.eval("document.querySelector('#v-intake-review tr.irmeet input.irtick').click(); 0")
        b.pump(0.3)
        ticked = self._look("document.querySelector('#v-intake-review tr.irmeet.hl td')")
        b.eval("document.querySelector('#v-intake-review tr.irmeet input.irtick').click(); 0")        # untick
        b.pump(0.3)
        b.eval("document.querySelector('#v-intake-review tr.irmeet .icmeethd').click(); 0")
        b.pump(0.5)
        opened = self._look("document.querySelector('#v-intake-review tr.irmeet.icopen td')")
        self.assertTrue(ticked and opened, f"ticked {ticked}, open {opened}")
        for k in ("bg", "shadow"):
            self.assertEqual(ticked[k], opened[k], f"the ticked and the open meeting differ in {k}")
        self.assertEqual(len(re.findall(r"\b2px\b", ticked["shadow"].replace("0px", ""))), 2, ticked["shadow"])     # a line above and one below
        self.note(53, f"tint {opened['bg']}, bars {opened['shadow'][:60]}")

    @known("#341 M5 (Stark): Two panes' selected meeting is a plain tint (the generic selected-row rule) with no line above and below, so it does not look like the List's")
    def test_c54_two_panes_selected_meeting_looks_the_same(self):
        """54. (#341 item 7) In Two panes, the selected meeting in the left list has the same look as the List's open meeting: the same tint and
        the 2 px accent line above and below."""
        b = self.b
        self.screen("intake-review")
        b.eval("irOpen.value=null; document.querySelector('[data-irview=list]').click(); 0")
        b.pump(0.4)
        b.eval("document.querySelector('#v-intake-review tr.irmeet .icmeethd').click(); 0")
        b.pump(0.5)
        want = self._look("document.querySelector('#v-intake-review tr.irmeet.icopen td')")
        b.eval("irOpen.value=null; document.querySelector('[data-irview=two]').click(); 0")
        b.pump(0.6)
        two = self._look("document.querySelector('#v-intake-review tr.sel td')")
        self.assertTrue(want and two, f"list {want}, two panes {two}")
        self.assertEqual((two["bg"], two["shadow"]), (want["bg"], want["shadow"]))

    def test_c55_a_file_row_is_one_line_of_facts(self):
        """55. (#341 item 8) In Intake's List a file you added is its name and ONE line of facts (when it was added, its likely project, its
        state and what it is: "Added today · Likely project: ... · File ready · Teams transcript · 1 KB"): one line of facts under the name,
        nothing else under it, and the kind of file is asked for only when it needs a choice."""
        b = self.b
        self.screen("intake-review")
        b.eval("irOpen.value=null; document.querySelector('[data-irview=list]').click(); 0")
        b.pump(0.4)
        r = b.eval("(()=>{ const row=[...document.querySelectorAll('#v-intake-review tr.irmeet')].find(x=>x.querySelector('[data-irki=file]')); if(!row) return null; const td=row.querySelector('td.title');"
                   " return {kids:[...td.children].map(e=>e.tagName+'.'+e.className), why:[...td.querySelectorAll('.why')].map(e=>e.textContent.replace(/\\s+/g,' ').trim()), tall:Math.round(td.getBoundingClientRect().height)}; })()")
        self.assertTrue(r, "Intake lists a file you added")
        self.assertEqual(len(r["why"]), 1, f"one line of facts: {r}")
        self.assertRegex(r["why"][0], r"^Added .* · Likely project: .* · ")
        self.assertEqual([k.split(".")[0] for k in r["kids"]], ["INPUT", "SPAN", "B", "DIV"], f"name then one line: {r['kids']}")
        self.note(55, f"{r['why'][0][:90]}; row {r['tall']} px")

    def test_c56_the_audience_switch_is_quieter_than_the_view_switch(self):
        """56. (#341 item 9) On the milestones page, the Internal view / Client view switch is smaller than the Plan / Movement switch (26 px
        tall against 34, a smaller type), still a target of at least 24 px, the one in use is a soft fill (not the dark one of the view
        switch) and is also bolder, so colour is not its only cue."""
        self.screen("milestones")
        r = self.b.eval("""(()=>{ const f=e=>({h:Math.round(e.getBoundingClientRect().height), fs:parseFloat(getComputedStyle(e).fontSize), w:+getComputedStyle(e).fontWeight, bg:getComputedStyle(e).backgroundColor});
          const view=[...document.querySelectorAll('.mv-seg:not(.aud) button')].map(f), aud=[...document.querySelectorAll('.mv-seg.aud button')].map(f);
          const on=document.querySelector('.mv-seg.aud button[aria-pressed=true]'), off=document.querySelector('.mv-seg.aud button[aria-pressed=false]');
          return {view, aud, on:f(on), off:f(off), viewOn:f(document.querySelector('.mv-seg:not(.aud) button[aria-pressed=true]'))}; })()""")
        self.assertEqual(len(r["aud"]), 2)
        self.assertGreaterEqual(min(a["h"] for a in r["aud"]), 24)
        self.assertLess(max(a["h"] for a in r["aud"]), min(v["h"] for v in r["view"]))
        self.assertLess(max(a["fs"] for a in r["aud"]), min(v["fs"] for v in r["view"]))
        self.assertNotEqual(r["on"]["bg"], r["viewOn"]["bg"], "not the dark fill of the view switch")
        self.assertGreater(r["on"]["w"], r["off"]["w"], "bolder as well as filled")
        self.note(56, f"audience {r['on']['h']} px {r['on']['fs']} px weight {r['on']['w']}; view {r['viewOn']['h']} px")

    def test_c57_people_has_one_link_style(self):
        """57. (#341 item 10) In a People row the name, the projects and the counts are links in one style: the same dotted underline, in the
        text colour (an overdue count keeps its red), the accent colour only on hover or focus."""
        b = self.b
        self.screen("people")
        r = b.eval("""(()=>{ const p=document.createElement('i'); p.style.color='var(--ink)'; document.body.appendChild(p); const ink=getComputedStyle(p).color; p.remove();
          const rows=[...document.querySelectorAll('#peopleTbl tbody tr')].slice(0,4);
          const L=rows.flatMap(r=>[...r.querySelectorAll('td a, td .plink, td .pcode')]).map(e=>({t:e.textContent.trim(), dec:getComputedStyle(e).textDecorationLine+' '+getComputedStyle(e).textDecorationStyle, col:getComputedStyle(e).color, late:!!e.closest('td.late')}));
          return {ink, L}; })()""")
        self.assertGreaterEqual(len(r["L"]), 6, r)
        self.assertEqual({x["dec"] for x in r["L"]}, {"underline dotted"}, [x for x in r["L"] if x["dec"] != "underline dotted"])
        self.assertEqual([x for x in r["L"] if x["col"] != r["ink"] and not x["late"]], [], "a link in a colour other than the text colour")
        self.note(57, f"{len(r['L'])} links, all underline dotted")

    def test_c58_the_plain_words_are_there(self):
        """58. (#341 item 11) A project's cockpit says "Late milestones" (not "Milestone slip"; its link names it too) and "Progress over time"
        (not "Flow"); People's heading is "Risks and issues" and a count there is read as "open risks and issues" (not "RAID")."""
        b = self.b
        self.screen("cockpit")
        r = b.eval("({labels:[...document.querySelectorAll('#v-cockpit .evbox .l')].map(e=>e.textContent.trim()), heads:[...document.querySelectorAll('#v-cockpit h2')].map(e=>e.textContent.trim()),"
                   " jump:[...document.querySelectorAll('#v-cockpit [data-msjump]')].map(e=>e.getAttribute('aria-label'))})")
        self.assertIn("Late milestones", r["labels"])
        self.assertNotIn("Milestone slip", r["labels"])
        self.assertTrue(any(h.startswith("Progress over time") for h in r["heads"]), r["heads"])
        self.assertFalse(any(re.match(r"Flow\b", h) for h in r["heads"]), r["heads"])
        self.assertTrue(r["jump"] and all(j.startswith("Late milestones") for j in r["jump"]), r["jump"])
        self.screen("people")
        q = b.eval("({heads:[...document.querySelectorAll('#peopleTbl thead th')].map(e=>e.textContent.trim()), labels:[...document.querySelectorAll('#peopleTbl td[data-col=or] a')].slice(0,6).map(e=>e.getAttribute('aria-label')||e.title||'')})")
        self.assertIn("Risks and issues", q["heads"])
        self.assertNotIn("RAID", q["heads"])
        self.assertTrue(q["labels"] and all(re.search(r"open risks? (and issues? )?owned|open risks and issues owned|open risk or issue owned", x) and "RAID" not in x for x in q["labels"]), q["labels"])

    @known("#341 M4 (Stark): the old words 'RAID', 'Milestone slip' and 'Flow' remain in Help, in Settings (for example 'RAID board groups by'), in the Projects page's figure links and in screen-reader labels")
    def test_c59_the_old_words_are_gone_everywhere(self):
        """59. (#341 item 11) Nowhere a person reads or hears is "RAID", "Milestone slip" or "Flow" left: not in Help, not in a Settings tab, not
        in the Projects page, not in a label, tip or hover."""
        b, hits = self.b, {}
        words = re.compile(OLD_WORDS)
        help_md = read_repo("system/templates/help.md")
        for m in words.finditer(help_md):
            hits.setdefault("help", []).append(m.group(0))
        for sc in ("projects", "cockpit", "people", "settings-essentials", "settings-work", "settings-advanced", "settings-health"):
            self.screen(sc)
            txt = b.eval("document.body.innerText+' '+[...document.querySelectorAll('[title],[aria-label],[data-tip],[placeholder]')].map(e=>[e.title,e.getAttribute('aria-label'),e.getAttribute('data-tip'),e.placeholder].join(' ')).join(' ')")
            found = words.findall(txt)
            if found:
                hits[sc] = found[:5]
        self.assertEqual(hits, {}, "old words still on screen")

    def test_c60_the_cockpits_right_column_is_two_fifths(self):
        """60. (#341 item 12) A project's cockpit gives the right-hand column (risks, decisions, warnings) two fifths of the width at 1400 px (it
        was a third) and stacks the two columns on a narrow window (900 px)."""
        b = self.b
        self.screen("cockpit")
        wide = b.eval("(()=>{ const c=document.querySelector('#v-cockpit .cock'); const w=[...c.children].map(x=>x.getBoundingClientRect().width); return w; })()")
        self.assertEqual(len(wide), 2)
        share = wide[1] / sum(wide)
        self.assertTrue(0.38 <= share <= 0.42, f"the right column is {share:.2f} of the width: {wide}")
        with width(self, 900):
            self.screen("cockpit")
            two = b.eval("(()=>{ const c=document.querySelector('#v-cockpit .cock'); return [...c.children].map(x=>{ const r=x.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.bottom)]; }); })()")
            self.assertEqual(two[0][0], two[1][0], f"stacked at 900 px: {two}")
            self.assertGreaterEqual(two[1][1], two[0][2], f"the second column starts below the first: {two}")
        self.note(60, f"right column {share:.2f} of the width at 1400 px; stacked at 900 px")

    def folder(self):
        """Press the first report folder in Files' tree."""
        self.b.eval("document.querySelector('#tree button[data-f=reports][data-s]').click(); 0")
        self.b.pump(0.3)

    def count(self):
        return self.b.eval("document.getElementById('filesCount').textContent.trim()")

    def view(self, v):
        self.b.eval("document.getElementById('fmBtn').click(); 0")
        self.b.pump(0.2)
        self.b.eval("document.querySelector('#fmenu input[name=fsView][value=%s]').click(); 0" % v)
        self.b.pump(0.4)

    def test_c61_files_has_two_ways_to_narrow_the_list(self):
        """61. (#341 item 13) Files narrows by the folder tree and by Filter only: the row of view buttons is gone; Filter holds View (All files,
        Latest reports, This week's meetings, Archived) above Type and the dates; choosing a view narrows the list, shows a "View: ..."
        chip and counts 1 on the Filter button; choosing a view clears the folder you were in; removing the chip, or Clear, returns to
        all files."""
        b = self.b
        self.screen("files")
        self.assertFalse(b.eval("!!document.getElementById('fquick') || !!document.querySelector('#v-files .vchip')"), "the view buttons are gone")
        self.assertTrue(b.eval("!!document.getElementById('tree') && document.querySelectorAll('#tree button').length>3"))
        total = self.count()
        n_all = int(re.match(r"(\d+) of", total).group(1))
        b.eval("document.getElementById('fmBtn').click(); 0")
        b.pump(0.2)
        legends = b.eval("[...document.querySelectorAll('#fmenu legend')].map(e=>e.textContent.trim())")
        self.assertEqual(legends[:2], ["View", "Type"], legends)
        self.assertEqual(b.eval("[...document.querySelectorAll('#fmenu input[name=fsView]')].map(e=>e.parentElement.textContent.trim())"),
                         ["All files", "Latest reports", "This week's meetings", "Archived"])
        b.eval("document.getElementById('fmBtn').click(); 0")
        self.folder()
        in_folder = int(re.match(r"(\d+) of", self.count()).group(1))
        self.assertLess(in_folder, n_all)
        self.view("latest")
        self.assertEqual(b.eval("document.getElementById('fchips').innerText.replace(/\\s+/g,' ').trim()"), "View: Latest reports ✕")
        self.assertEqual(b.eval("(document.querySelector('#fmBtn .fcount')||{}).textContent"), "1")
        latest = int(re.match(r"(\d+) of", self.count()).group(1))
        self.assertTrue(0 < latest <= n_all and latest != in_folder, f"latest {latest}, folder {in_folder}, all {n_all}")
        self.assertEqual(b.eval("document.querySelectorAll('#tree button[aria-pressed=true]').length"), 1, "the folder is cleared, All is chosen")
        b.eval("document.querySelector('#fchips [data-fclr=view]').click(); 0")
        b.pump(0.4)
        self.assertEqual(self.count(), total)
        self.view("week")
        b.eval("document.getElementById('fmClear').click(); 0")
        b.pump(0.4)
        self.assertEqual(self.count(), total)
        self.note(61, f"{n_all} files; folder {in_folder}; latest reports {latest}")

    @known("#341 M1 (Stark): Files' empty message is the same for every view ('No files match. Clear the filters.') and does not say which view is empty")
    def test_c62_an_empty_view_says_which_view_is_empty(self):
        """62. (#341 item 13) When a view of the Filter has nothing in it (Archived, in a project with nothing archived), the list says so in its
        own words (it names the view) rather than the one message every filter gives."""
        b = self.b
        self.screen("files")
        self.view("archived")
        self.assertEqual(self.count().split(" ")[0], "0")
        msg = b.eval("document.getElementById('filesTbl').innerText.replace(/\\s+/g,' ').trim()")
        self.assertRegex(msg, r"(?i)archived", msg)

    @known("#341 M2 (Stark, as read from the brief): in Filter, 'All files' is already chosen while you are in a folder, so choosing it again changes nothing and the folder stays; the old All files button cleared the folder")
    def test_c63_all_files_in_filter_leaves_the_folder(self):
        """63. (#341 item 13) With a folder chosen in the tree, choosing View: All files in Filter shows every file again and puts the tree back on
        All."""
        b = self.b
        self.screen("files")
        total = self.count()
        self.folder()
        self.assertNotEqual(self.count(), total)
        self.view("all")
        self.assertEqual(self.count(), total)

    def test_c64_the_search_button_says_ask_creaite(self):
        """64. (#341 item 14) In Files, the search box's ask button shows the words "ask creaite" beside its mark (lower case), at 1400 and 900 px,
        inside the window and not clipped."""
        b = self.b
        for w in (1400, 900):
            with width(self, w):
                self.screen("files")
                r = b.eval("(()=>{ const bt=document.getElementById('vsAskBtn'), l=bt.querySelector('.asklab'); const r=bt.getBoundingClientRect();"
                           " return {disp:getComputedStyle(l).display, text:l.textContent.trim(), inside:r.left>=0&&r.right<=innerWidth, clipped:bt.scrollWidth>bt.clientWidth+1}; })()")
                self.assertNotEqual(r["disp"], "none", f"{w}: the label is hidden")
                self.assertEqual(r["text"], "ask creaite")
                self.assertTrue(r["inside"] and not r["clipped"], f"{w}: {r}")

    def test_c65_activity_select_all_ticks_only_what_can_be_undone(self):
        """65. (#341 item 15) Activity has a tick in the header that selects every change you can see that can be undone, leaves the ones that
        cannot (their tick is greyed out) alone, says how many are selected, shows the partly-ticked state when you tick some yourself, and
        un-ticks them all when pressed again."""
        b = self.b
        self.screen("activity")
        r0 = b.eval("({all:!!document.getElementById('actAll'), undoable:document.querySelectorAll('#actTbl tr[data-row]').length, rows:document.querySelectorAll('#actTbl tbody tr').length,"
                    " off:document.querySelectorAll('#actTbl tbody tr input[disabled]').length})")
        self.assertTrue(r0["all"], "the header has a select-all tick")
        self.assertTrue(0 < r0["undoable"] < r0["rows"], r0)
        b.eval("document.getElementById('actAll').click(); 0")
        b.pump(0.3)
        r1 = b.eval("({hl:document.querySelectorAll('#actTbl tr.hl').length, ticked:[...document.querySelectorAll('#actTbl tbody input')].filter(x=>x.checked).length,"
                    " offTicked:[...document.querySelectorAll('#actTbl tbody input[disabled]')].filter(x=>x.checked).length, head:document.getElementById('actAll').checked, bar:document.getElementById('actBar').innerText.replace(/\\s+/g,' ').trim()})")
        self.assertEqual(r1["hl"], r0["undoable"])
        self.assertEqual(r1["ticked"], r0["undoable"])
        self.assertEqual(r1["offTicked"], 0, "a change that cannot be undone is never ticked")
        self.assertTrue(r1["head"])
        self.assertRegex(r1["bar"], rf"^{r0['undoable']} selected")
        b.eval("document.getElementById('actAll').click(); 0")
        b.pump(0.3)
        self.assertEqual(b.eval("document.querySelectorAll('#actTbl tr.hl').length"), 0)
        b.eval("document.querySelector('#actTbl tr[data-row] input').click(); 0")
        b.pump(0.2)
        self.assertEqual(b.eval("document.getElementById('actAll').indeterminate"), True, "partly ticked")
        self.note(65, f"{r0['undoable']} of {r0['rows']} changes can be undone and were ticked; {r0['off']} greyed out")

    def test_c66_settings_has_no_help_and_documentation_card(self):
        """66. (#341 item 16) None of Settings' tabs has the "Help and documentation" card or its "Open help" button; Help is still there."""
        b = self.b
        for sc in ("settings-essentials", "settings-work", "settings-advanced", "settings-health"):
            self.screen(sc)
            r = b.eval("({card:document.getElementById('v-settings').innerText.includes('Help and documentation'), btn:!!document.querySelector('#v-settings [data-go=help]')})")
            self.assertEqual(r, {"card": False, "btn": False}, sc)
        self.screen("help")
        self.assertTrue(b.eval("!document.getElementById('v-help').hidden"))


# ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

def _uncommitted_engine():
    r = subprocess.run(["git", "status", "--porcelain", "--", "system", ".claude"], cwd=REPO, capture_output=True, text=True)
    return bool(r.stdout.strip())


def _main():
    """Standalone: build the zip once (with the uncommitted engine files when there are any), make the shared vault and server for the
    classes that only read, and point the classes that change data at the zip (each makes a vault of its own)."""
    if not os.environ.get("CREAITE_HC_BASE"):
        import atexit
        import handcheck
        s = handcheck.Session(dirty=_uncommitted_engine())
        s.open()
        if not os.environ.get("CREAITE_HC_KEEP"):
            atexit.register(shutil.rmtree, s.dir, ignore_errors=True)       # registered first, so it runs after the servers are stopped
        atexit.register(s.close)
    unittest.main()


if __name__ == "__main__":
    _main()
