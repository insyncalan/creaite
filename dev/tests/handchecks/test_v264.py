"""creaite 2.6.4's hand checks, automated against a vault made from the release zip (the fictional demo portfolio: Falcon Data
Platform and the rest). One check per item, `test_cNN_...`, its docstring quoting what the item must do. DRAFT, written from the issue
texts and Team Cap's findings of 24-10-2026 while the plain notes (dev/release-notes/2.6.4-plain.md) were not posted; brought up to
v264-line 7e10355b (#334 off by default, #352 Today's stale line gone, M1 fixed by the 345 diff, H1 fixed: the singular milestone
message, #351 b: no follow-up under a past day's meetings): the numbers are the
items in order and the PM can number them in; the wording of the plain-words checks (11, 12) follows dev/PLAIN-WORDS.md and the Help
diff, and is to be confirmed against the plain notes.

   1  #337  Settings: a tick-box row keeps a label at least 220 px wide at 900 and 1400 px
   2  #337  Activity: the By column does not wrap (one line, rows no taller than 52 px) at 900 and 1400 px
   3  #337  Cockpit: the edit pencils are 3:1 or better in light and dark, 24 px targets; chart text is 12 px or more
   4  #337  People at 900 and 1400 px: the table fits its box and Overdue (the sort column) is on screen
   5  #337  People at 900 and 1400 px: no word breaks in the middle                                  EXPECTED FAILURE (M2)
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
  33  #343  Show the waiting tail, tick a waiting meeting, Hide it: the bar says "0 selected, 1 hidden" and Later and Not needed
            because... do not move the hidden meeting                                  EXPECTED FAILURE (Team Cap #343 H1; own vault, Chrome)
  34  #343  People's Organisation and Role columns (headings included) keep a word on one line at 900 and 1400 px; a sibling of
            check 5, narrowed to the two columns                                                  EXPECTED FAILURE (Team Cap #343 M1)

How a check is wired (every class that changes data has a vault of its own, made from the zip, so nothing a check changes reaches another):
  Design264, Words264, Figures264, Today264  the shared hand-check vault and Chrome; nothing is changed (Today264 sets the page's own data and puts it back)
  Item264, Profile264, Card264, UsageOff264, PastDay264, TickFold264  a vault of its own, its server and Chrome (UsageOff264: the budget never switched on;
                                   PastDay264, TickFold264: a fictional calendar of the past day and today, with every transcript state)
  Routes264, Budget264             a vault of its own and its live server (the page's own token), no browser; Budget264's Claude is a stand-in
                                   (the budget is OFF by default: its checks switch it on the way Settings does; check 28 leaves it off)
  Commands264, Extraction264, Runs264, Rules264  a vault of its own and the engine's own code run in it (Runs264: a stand-in for the thread and the process)

The guarded parts (#345, #346, #334 and the reach.py entries) are the 2.6.4 chain: dev/proposals/GUARDED-2.6.4.chain is empty on the
line until the list is cut, so the checks that need a guarded change read the repository's own files for it. A check that needs a change
this tree does not have is an EXPECTED FAILURE (the convention of test_v262.py and test_v263.py): red for the right reason, and an
unexpected success (flagged) the moment the change is in. A check marked EXPECTED FAILURE (a finding of Team Cap's) is one the line
still fails; fixed, it becomes an unexpected success and loses its mark. CREAITE_HC_SHOW_XFAIL=1 runs every one of them as a plain check,
to see why it fails.

Run them (from the repository root; a release zip is built from this checkout first):
  python3 dev/tests/handchecks/test_v264.py                         all, with the committed tree (or --dirty: uncommitted engine files)
  python3 dev/tests/handchecks/test_v264.py Routes264.test_c16_...  one check
  python3 dev/tools/handcheck.py v2.6.4 [--dirty] [--only 1,4]      the runner (Results table, run folder); --no-sheet skips the screenshots
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

KIND = {n: "scriptable" for n in range(1, 35)}
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

class Engine264(HandcheckCase):
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
        Engine264._n += 1
        day = self.day()
        name = f"proposed-{day}-{10 + Engine264._n:02d}00-sweep-hc264-{Engine264._n}.json"
        due = (date.fromisoformat(day) + timedelta(days=30)).isoformat()
        mail = ("Email · From: Priya Nair <priya.nair@meridian.example> · Subject: Harbour works · Sent: %s 09:00 · "
                "Link: https://outlook.example.test/owa/?ItemID=hc264-%d" % (day, Engine264._n))
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
        data.update(source_run="cx-minutes", meeting={"key": f"fal-steering-{day}-{Engine264._n}", "title": "Steering", "project": "FAL",
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
        spec = self.staging("drafts/hc264-meeting.json")
        spec.write_text(json.dumps({"title": title, "date": day, "projects": ["FAL"], "transcript": transcript,
                                    "minutes": {"start": "10:00", "end": "11:00", "summary": ["The committee met."], "chat": False},
                                    "items": [new, *extra_items]}), encoding="utf-8")
        before = set(hcbase.pending_proposals(self.vault))
        code, out = self.run_in_vault("minutes.py", "stage", "system/staging/drafts/hc264-meeting.json")
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

class Design264(HandcheckCase):
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

    @known("Team Cap M2: #v-people in style.css puts overflow-wrap:anywhere on every cell, so ordinary words break in the middle")
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

    @known("Team Cap #343 M1: People's Organisation and Role columns break words mid-word at 900 px, and the Organisation heading reads 'ORGANISATIO/N' at 1400 px")
    def test_c34_people_organisation_and_role_do_not_break_in_the_middle(self):
        """34. (#343 M1) People at 900 px and at 1400 px: the Organisation and Role columns, their headings included, keep a word on one
        line (the heading was "ORGANISATIO/N" at 1400 px). A sibling of check 5, which looks at every word of the table; this one
        looks at the two columns Team Cap named and says which column broke."""
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


class Words264(HandcheckCase):
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


class Commands264(Engine264):
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


class Item264(HandcheckCase):
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

class Figures264(HandcheckCase):
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


class Extraction264(Engine264):
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


class Routes264(Engine264):
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


class Runs264(Engine264):
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
        ls.Run('r-failed264', 'hello', None, None, None, fresh=True)
        raised = False
    except RuntimeError:
        raised = True
    out = {'raised': raised, 'in_table': 'r-failed264' in ls.RUNS, 'busy': bool(ls.current_run() and not ls.current_run().done),
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
out({"type": "result", "result": "Stand-in reply.", "session_id": "sess-hc264"})
'''


class Budget264(Engine264):
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
        return sum(1 for ln in p.read_text().splitlines() if "--" in json.loads(ln) and "hc264-ask" in json.loads(ln)[json.loads(ln).index("--") + 1]) \
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
        return self.post("/api/ask", dict({"message": "hc264-ask hello"}, **req))

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
        self.assertNotIn("hc264-ask", json.dumps(res), "the message is not echoed")
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
        for text in ("hc264", "Sara", "Harbour", "/", "message", "prompt"):
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
    ok, why = reach.hook_decision(tool, inp, mode, 'r-hc264')
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


class Card264(HandcheckCase):
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
        b.eval("(()=>{ const t=document.getElementById('chIn'); t.value='hc264 what is due'; t.dispatchEvent(new Event('input',{bubbles:true})); return true; })()")
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
        b.eval("(()=>{ const t=document.getElementById('chIn'); t.value='hc264 what is due'; t.dispatchEvent(new Event('input',{bubbles:true})); return true; })()")
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


class UsageOff264(HandcheckCase):
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
        b.eval("(()=>{ const t=document.getElementById('chIn'); t.value='hc264 what is due'; t.dispatchEvent(new Event('input',{bubbles:true})); return true; })()")
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

class Profile264(HandcheckCase):
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

class Today264(HandcheckCase):
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


class PastWorld264(HandcheckCase):
    """The base of checks 31 and 33. A vault of its own with a fictional calendar of about ten Teams meetings on the day before today and
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



class PastDay264(PastWorld264):
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


class TickFold264(PastWorld264):
    """Check 33. The past-day world's Intake, for the tick bar and a folded waiting tail."""

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

    @known("Team Cap #343 H1: TickBar does not redraw on a fold")
    def test_c33_the_tick_bar_does_not_act_on_a_meeting_the_fold_has_hidden(self):
        """33. (#343 H1) Show the waiting tail, tick a waiting meeting, press Hide: the bar says "0 selected, 1 hidden", and Later and
        Not needed because... do not move the hidden meeting (the bar was drawn for the tick and kept its buttons)."""
        b = self.b
        self.world()
        self.intake()
        problems, said = [], {}
        for action in ("later", "reason"):
            self.intake()                                # a fresh page: the tail folded, nothing ticked
            self.open_fold("show")
            mid = self.waiting_ids()[0 if action == "later" else 1]
            b.click(f'#v-intake-review input.irtick[data-irtick-box="{mid}"]')
            b.wait("(document.querySelector('[data-irtickbar]')||{innerText:''}).innerText.indexOf('1 selected')>=0", 10)
            self.release_fold("show")                    # Hide
            self.assertEqual(self.buttons()["waiting"], 0, "the tail folded")
            bar = said[action] = self.tick_bar()
            if not (bar and "0 selected" in bar and "1 hidden" in bar):
                problems.append(f"after Hide the bar says {bar!r}, not '0 selected, 1 hidden'")
            if bar:
                if action == "later":
                    b.eval("(()=>{ const x=document.querySelector('[data-ira=laterall]'); if (x && !x.disabled) x.click(); })()")
                else:
                    b.eval("(()=>{ const x=document.querySelector('[data-ira=reasonall]'); if (x && !x.disabled) x.click(); })()")
                    b.pump(0.4)
                    b.eval("(()=>{ const x=document.querySelector('.cxmenu .pkopt'); if (x) x.click(); })()")
                if self.moved(mid):
                    problems.append(f"{'Later' if action == 'later' else 'Not needed because'} moved the hidden meeting")
        self.note(33, f"tick a waiting meeting, Hide the tail: the bar says {said['later']!r}")
        self.assertEqual(problems, [], "; ".join(problems))


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


class Rules264(Engine264):
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
