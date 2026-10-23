"""creaite 2.6.0's hand checks (dev/handchecks/v2.6.0.md: the Product Manager's draft of 19-10-2026 numbers 1 to 27; Team Stark's
scaffolding adds 28 to 82; 83 to 99, 21-10-2026, add #268, #275, #264/#265, #255 and Help), automated against a vault made from
this checkout's release zip. Every check names the 2.6 item it needs (@needs); while that item is not in the vault (or, for a check that only calls tests, the checkout) the check SKIPS with the
reason, so the file runs on any head and nothing fails for code that has not landed. A class with nothing to run in a browser
starts no vault, server or Chrome.

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.6.0
Run this file on its own (it makes the vault itself):                 python3 dev/tests/handchecks/test_v260.py
Run a check with its item absent, to see it red:                      CREAITE_HC_260_FORCE=1 python3 dev/tests/handchecks/test_v260.py

  Intake232    1 to 12    #232 Intake (Team Cap's): placeholders with the PM's words, written when it lands (phase 2)
  Work241      13 to 26   #241 Work items v2 (v26-work-items-abc; 20 needs v26-work-items-d and its guarded route): marks, density,
                          grouping, the Client-visible states, tags level, row heights, the layout fixture on the hand-check vault,
                          plus Team Stark's own tests, called
  Draft183     27 to 39   #183 Draft email delivery (v26-draft-delivery). 27 and 39 live only (a real Outlook, with Alan); 37 needs
                          Jarvis's live_server.diff (the draft route; its test is still under dev/proposals); 38 judgement
  Settings246  40 to 45   #246 Settings clean-up and tabs (v26-settings-tabs, being built): the tab list, Advanced's five sub-tabs, what
                          went, search reaches every key, one tab per key, saved values never rewritten; 45 judgement
  Project247   46 to 52   #247 Project settings v2 (v26-project-settings-v2, being built): anchors not tabs, the sticky list, Archive
                          and close set apart, the People columns, Workstreams, the Followed star on this page only; 52 judgement
  People248    53 to 57   #248 People page v2 (no branch yet): tabs, columns, nothing that must not be there, needs details; 57 judgement.
                          Its selectors are read from the spec (text, roles), not a build: confirm them when it lands
  Fetch250     58 to 63   #250 fetch transcripts (v26-fetch-transcripts): 58 off by default (direct), 59 to 62 the builder's tests, called;
                          63 live only (a real sweep fetching a real transcript)
  Fetch250Review 64 to 68 #250's independent review (Team Cap, 20-10-2026), H1 to H5, each in a throwaway vault (no browser): a
                          result with no created date, a path inside a result file, record's reach class, another meeting's
                          transcript, a confidential meeting with no sensitivity saved. Red until the review's fixes land
  Markup183    69         #183's Outlook-safe markup on a chase built from the hand-check vault
  SettingsLine 70         the Settings line (v26-settings-line): the old People, Projects and Workstreams addresses
  Quiet97      71 to 74   #97 step 1 quiet hours (v26-quiet-hours; skip until vip.quiet_overnight exists); 74 needs its live_server.diff
  Archive252   75 to 82   #252 99 Archive (landed in 2.5.3 as no rename and no migration: test_archive_99, called); 80 needs its
                          guarded diffs; 82 live only
  Minutes268   83 to 89   #268 Minutes view v2 (v26-minutes-view-v2): the Track column, aligned tables, editing in place, the
                          transcript and the sheet, Export, one-click Approve; the builder's Chrome tests, called (the hand-check
                          vault stages no minutes); 89 judgement, by hand
  TrackReview275 90 to 92 #275 Track from Review (v26-track-from-review): Review's Approve follows the Track column; called
  IntakeJobs   93, 94     #264 Process and #265 Refresh as their own jobs (in 2.5.3; test_v253 drives them): called; 95 live only
  DeleteNote255 96, 97    #255 Delete note with no card: 96 in a vault of its own (moves a note, Undo), 97 the builder's tests
  Help26       98, 99     Help's 2.6 lines (v26-help-text): the words for each item in the vault, old places gone; 99 judgement

Adding a check is one small function in its item's class:
  @needs("<item>")                       the item it waits for (FEATURES; a new item is one entry there)
  def test_cNN_<words>(self):            NN the sheet's number
      \"\"\"NN. the check's words\"\"\"
      ...assertions on the hand-check vault (self.b, self.vault, self.py), then optionally self.called(NN, *CALLS)
or, for a direct check that makes its own throwaway vault (no browser): @needs(...) then @offline on the function;
or, for a check that only runs Team Stark's own tests (no browser, no vault):
  @needs("<item>")
  @calls(("test_file", ["Class", "Class.test_name", "test_name"], "the branch that brings it"))
  def test_cNN_<words>(self): \"\"\"NN. ...\"\"\"
Then add NN to KIND (or LIVE_ONLY) and its line to the sheet.

Never Microsoft 365, never a real model: Claude is the hand-check vault's stand-in. Fictional data only (the demo portfolio's people).
"""
import hashlib
import json
import os
import re
import sys
import time
import unittest
from functools import wraps
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # dev/tests
import hcbase  # noqa: E402
from hcbase import NOTES, SCREENS, phase2  # noqa: E402
from test_v230 import V230Case  # noqa: E402
from test_v240 import resolve, run_named  # noqa: E402  (Team Stark's tests, called as the 2.4.0 checks call them)

REPO = Path(__file__).resolve().parents[3]
FORCE = os.environ.get("CREAITE_HC_260_FORCE") == "1"
NOCALL = os.environ.get("CREAITE_HC_260_NOCALL") == "1"     # a quick run: the direct checks only, Team Stark's tests not called
READY = "typeof go==='function' && LIVE"

KIND = {**{n: "scriptable" for n in (*range(1, 10), 12, *range(13, 23), 26, *range(28, 38), *range(40, 45), *range(46, 52),
                                     *range(53, 57), *range(58, 63), *range(64, 82), *range(83, 88), *range(90, 95),
                                     *range(96, 99))},
        **{n: "measurable" for n in (23, 24, 25, 88)},
        **{n: "judgement" for n in (10, 11, 38, 45, 52, 57, 89, 99)}}
LIVE_ONLY = {
    27: "with Alan, after release: turn on Create drafts in Outlook, draft a chase with an overdue date, a table and a project heading, "
        "open the draft in Outlook: colours, table and heading survive, subject and body match the Copy version; a person with no email "
        "still gets the draft with nothing in To (Jarvis asked for it; nothing here may call Microsoft 365)",
    39: "the Outlook access Check against a real mailbox (one that can write drafts, and one that cannot); the app side is check 29",
    63: "a real sweep with the setting on fetches a real ended meeting's transcript once, and Intake shows it Transcript ready",
    82: "with Alan: the real company OneDrive archive folder renamed to 99 Archive once (Health's Rename on the card); other people's "
        "files inside are untouched and still there, and the Files page and search find them",
    95: "a real Process on a real Teams transcript (a real Claude run: progress and Stop on the row, the draft in Review) and a real "
        "Refresh of Alan's calendar (Microsoft 365): the meetings appear and the saved calendar holds no join link or passcode",
}

NOTES.clear()          # test_v230 (imported for its helpers) put its own notes here
NOTES.update({
    16: "PARTIAL: the underlines are not measured; the menu and keys are the builders' tests",
    20: "waits for v26-work-items-d and Jarvis's live_server.diff (/api/item/history)",
    37: "waits for Jarvis's live_server.diff; its test is dev/proposals/draft-delivery/test_draft_route.py until it moves into dev/tests",
    42: "every catalogue key with a tab, found by its own label under its tab's name (at most 4 found by text only)",
    56: "PARTIAL: the Needs attention filter's options (No email, No organisation, No role) are not driven yet",
})

# The items, and what says each one is in a vault (or the checkout): (path, regex or None for "the file exists").
# "dashboard.html" is the vault's built page; in the checkout it is system/templates/dashboard.html.
FEATURES = {
    "232": ("#232 Intake (Team Cap)", [("dashboard.html", r"Drop to add files")]),
    "241": ("#241 Work items v2 A to C (v26-work-items-abc)", [("dashboard.html", r"creaite-density")]),
    "241d": ("#241 D, the complete history (v26-work-items-d and its live_server.diff)",
             [("system/scripts/item_history.py", None), ("system/scripts/live_server.py", r"/api/item/history")]),
    "183": ("#183 Draft email delivery (v26-draft-delivery)", [("system/scripts/draft_delivery.py", None)]),
    "183r": ("#183's draft route (Jarvis's live_server.diff)", [("system/scripts/live_server.py", r"/api/email/draft")]),
    "246": ("#246 Settings tabs (v26-settings-tabs)", [("system/scripts/settings_catalogue.py", r"ADVANCED_SUBS")]),
    "247": ("#247 Project settings v2 (v26-project-settings-v2)", [("dashboard.html", r"psPeopleRows")]),
    "248": ("#248 People page v2", [("dashboard.html", r"\"Everyone\"\][\s\S]{0,80}?\"Nothing assigned\"")]),
    "250": ("#250 fetch transcripts (v26-fetch-transcripts)", [("system/scripts/settings_catalogue.py", r"sweep\.fetch_transcripts")]),
    "line": ("the Settings line (v26-settings-line)", [("dashboard.html", r"setMoved")]),
    "97": ("#97 step 1 quiet hours (v26-quiet-hours)", [("system/scripts/settings_catalogue.py", r"vip\.quiet_overnight")]),
    "97w": ("#97's alert-check wiring (its live_server.diff)", [("system/scripts/live_server.py", r"vip_schedule")]),
    "252": ("#252 the 99 Archive name (v26-archive-name-proposal)", [("system/scripts/paths.py", r'ARCHIVE = "99 Archive"')]),
    "252g": ("#252's guarded moves (its reach.py and live_server.py diffs)", [("system/scripts/reach.py", r"99 Archive")]),
    "268": ("#268 Minutes view v2 (v26-minutes-view-v2)", [("dashboard.html", r"kept in the minutes only")]),
    "275": ("#275 Track from Review (v26-track-from-review)", [("system/scripts/review.py", r"def track_minutes")]),
    "275g": ("#275's guarded tracker.py refusal (tracker-track-problems.diff)", [("system/scripts/tracker.py", r"def track_problems")]),
    "264": ("#264 Intake Process as its own job", [("system/scripts/intake_process.py", None)]),
    "265": ("#265 Calendar refresh as its own job", [("system/scripts/calendar_refresh.py", None)]),
    "255": ("#255 Delete note with no card (its guarded diffs)", [("system/scripts/reach.py", r"PAGE_MOVES"),
                                                                ("system/scripts/live_server.py", r"/api/notes/delete/now")]),
    "help": ("Help's 2.6 lines (v26-help-text)", [("system/templates/help.md", r"Pause alert checks on weekend days")]),
}

SCREENS.update({
    "settings-tabs": ("go('settings','essentials')", "VIEW==='settings' && document.querySelectorAll('#settingsBody [data-sec]').length>0"),
    "psettings": ("go('psettings','FAL')", "VIEW==='psettings' && !!document.querySelector('#psBody [data-pssec]')"),
})


def has(item, root, checkout):
    """Whether `item` is in `root` (a vault, or the checkout when `checkout`)."""
    for rel, rx in FEATURES[item][1]:
        p = root / ("system/templates/dashboard.html" if checkout and rel == "dashboard.html" else rel)
        if not p.exists():
            return False
        if rx and not re.search(rx, p.read_text(encoding="utf-8", errors="ignore")):
            return False
    return True


def needs(*items):
    """The check waits for these items: it skips, with the reason, until each is in the vault (or the checkout)."""
    def wrap(fn):
        @wraps(fn)
        def test(self):
            self.need(*items)
            return fn(self)
        test.needs = items
        return test
    return wrap


def offline(fn):
    """A direct check that needs no browser and no hand-check vault (it makes its own throwaway vault from this checkout's code):
    treated like a called check, so a class of them starts no Chrome."""
    fn.call_only = True
    return fn


def calls(*specs):
    """A check that only runs Team Stark's own tests: specs are (file in dev/tests, [tokens], the branch that brings them). It opens
    no browser; it skips while a named test is not in this checkout."""
    def wrap(fn):
        @wraps(fn)
        def test(self):
            self.called(self.check_number(), *specs)
        test.call_only, test.specs = True, specs
        return test
    return wrap


class V260Case(V230Case):
    """V230Case (the page's API, a Python probe in the vault) plus the item detection and the called tests."""
    width, height = 1400, 1000

    @classmethod
    def runnable(cls):
        """The checks that need the browser and whose items are in this checkout (the vault is made from it): a class of only called
        checks, or of checks whose items have not landed, starts no vault, server or Chrome."""
        def ready(m):
            fn = getattr(cls, m)
            return not getattr(fn, "call_only", False) and (FORCE or all(has(i, REPO, True) for i in getattr(fn, "needs", ())))
        return [m for m in super().runnable() if ready(m)]

    def call_only(self):
        return getattr(getattr(self, self._testMethodName), "call_only", False)

    def setUp(self):
        if self.call_only():
            n = self.check_number()
            if hcbase.only() and n not in hcbase.only():
                self.skipTest("not in --only")
            self.b = None
            return
        if getattr(self, "idle", False):              # the class started nothing: its items are not in this checkout
            self.b = None
            if getattr(getattr(self, self._testMethodName), "phase2", None):
                self.skipTest(getattr(self, self._testMethodName).phase2)
            if hcbase.only() and self.check_number() not in hcbase.only():
                self.skipTest("not in --only")
            self.need(*getattr(getattr(self, self._testMethodName), "needs", ()))
            self.skipTest("nothing to run in this class")
        super().setUp()

    def tearDown(self):
        if not self.call_only():
            super().tearDown()

    def need(self, *items):
        vault = getattr(self, "vault", None)
        direct = not self.call_only() and vault is not None
        for item in items:
            if not has(item, vault if direct else REPO, not direct) and not FORCE:
                self.skipTest(f"{FEATURES[item][0]} is not in this {'vault' if direct else 'checkout'} yet; the check runs once it is "
                              "merged (CREAITE_HC_260_FORCE=1 runs it anyway)")

    def called(self, n, *specs):
        """Run the named tests (each in a fresh process, their own throwaway vault): skip while any is missing, fail if one fails.
        CREAITE_HC_260_NOCALL=1 leaves them out (a quick run of the direct checks; a check with no direct part then skips)."""
        if NOCALL:
            if self.call_only():
                self.skipTest("CREAITE_HC_260_NOCALL=1: the called tests are left out")
            self.note(n, "the called tests were left out (CREAITE_HC_260_NOCALL=1)")
            return
        found, missing = [], []
        for file, tokens, branch in specs:
            ids, gone = resolve(file, tokens)
            missing += [(g, branch) for g in gone]
            if ids:
                found.append((file, ids))
        if missing:
            self.skipTest(f"waiting for {', '.join(sorted({b for _, b in missing}))}: " + ", ".join(t for t, _ in missing[:3])
                          + (f" and {len(missing) - 3} more" if len(missing) > 3 else ""))
        failed, total = [], 0
        for file, ids in found:
            ok, msg = run_named(file, ids)
            total += len(ids)
            if not ok:
                failed.append(msg)
        self.assertEqual(failed, [], "\n".join(failed))
        self.note(n, f"{total} of Team Stark's tests called, all passed ({', '.join(sorted({f for f, _ in found}))})")

    # ── shared helpers ──

    def reset_page(self):
        """A clean browser: nothing saved for Work, Settings or People."""
        self.b.eval("localStorage.clear()")
        self.b.reload(READY)

    def wait_true(self, js, seconds=15):
        self.b.wait(js, seconds)

    def texts(self, sel):
        return self.b.eval(f"[...document.querySelectorAll({sel!r})].map(e=>e.textContent.replace(/\\s+/g,' ').trim())")

    def vault_json(self, rel):
        p = self.vault / rel
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def digest(self, *rels):
        h = hashlib.sha256()
        for rel in rels:
            p = self.vault / rel
            h.update(p.read_bytes() if p.exists() else b"-")
        return h.hexdigest()


def dig(data, key):
    """A dotted key in nested settings, or None."""
    for part in key.split("."):
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data


# ══ #232 Intake (Team Cap): placeholders, numbered as the PM's draft ════════════════════════════════════════════════════════════

WAIT232 = "phase 2: #232 is Team Cap's; written from its landed list"


class Intake232(V260Case):
    """Checks 1 to 12 (the PM's words). Written when #232 lands."""

    @phase2(WAIT232)
    def test_c01_rail_and_page_called_intake(self):
        """1. The rail entry and the page are both called Intake, with the inbox icon and one badge; the old Intake and Review addresses
        open the page."""

    @phase2(WAIT232)
    def test_c02_stage_boxes(self):
        """2. The three stage boxes (Arrived, Drafted, Approved) each have an icon and a count and are clickable; Show all is a fourth box
        with the total; there is no instructional banner."""

    @phase2(WAIT232)
    def test_c03_three_views(self):
        """3. List, Board and Two panes all work; the choice is remembered per person; List is the default."""

    @phase2(WAIT232)
    def test_c04_add_files(self):
        """4. Add files is an icon button in the toolbar of all three views and opens the file picker; dropping files anywhere on the page
        shows "Drop to add files" and adds them."""

    @phase2(WAIT232)
    def test_c05_an_added_file_row(self):
        """5. A file you add is a row in Arrived with a file icon and a likely project; Process, Later and Not needed work on it."""

    @phase2(WAIT232)
    def test_c06_a_transcript_makes_minutes(self):
        """6. A transcript says it will be turned into minutes and shows Make minutes; processing it drafts minutes and proposals."""

    @phase2(WAIT232)
    def test_c07_minutes_from_someone_else(self):
        """7. Minutes from someone else say no new minutes are drafted and show Find work items; processing gives proposals only."""

    @phase2(WAIT232)
    def test_c08_a_file_it_cannot_tell(self):
        """8. A file it cannot tell shows Transcript and Minutes buttons, is left out of Process all ready until chosen, and the type can be
        flipped on any row."""

    @phase2(WAIT232)
    def test_c09_refresh_the_calendar(self):
        """9. A refresh icon beside the counts re-reads the calendar and shows "Calendar read hh:mm"."""

    @phase2(WAIT232)
    def test_c10_the_update_peek_look(self):
        """10. A mail or Teams proposal that changes an existing item: the peek shows the whole item and each changed field was → now,
        highlighted (judgement)."""

    @phase2(WAIT232)
    def test_c11_the_latest_update_look(self):
        """11. A proposal that changes the latest update shows the old text struck through, the new highlighted, and an "If approved" line
        (judgement)."""

    @phase2(WAIT232)
    def test_c12_the_250_sheet_still_holds(self):
        """12. Everything from the 2.5.0 sheet for the combined page still holds."""


# ══ #241 Work items v2 ═══════════════════════════════════════════════════════════════════════════════════════════════════════════

ABC = "v26-work-items-abc"
LIST = "test_work_items_v2_list"
KEYS = "test_work_items_v2_keys"
DUE_GROUPS = ["Overdue", "This week", "Next week", "Later", "No date", "Closed"]
LAYOUT = {                       # every saved Work key a browser can hold (the brief's list), with values a person could have chosen
    "creaite-colwidths": {"actions|o": 220, "actions|due": 150, "raid|o": 180},
    "creaite-colorder": {"actions": ["t", "due", "o", "pr", "st"]},
    "creaite-cols": {"actions": ["t", "o", "due", "pr", "st"], "raid": ["t", "o", "due", "pr"],     # the page always stores all three
                     "decisions": ["t", "st", "by", "due", "date", "src"]},
    "creaite-worklay": {"actions": "list", "raid": "board", "decisions": "list"},
    "creaite-workgrp": {"actions": "status", "raid": "owner"},
    "creaite-listgrp": {"actions": "none", "decisions": "owner"},
    "creaite-worksub": {"decisions|list": "project", "raid|board": "none"},
    "creaite-boardhide": {"actions": True},
    "creaite-boardcoll": {"raid|owner|TBC": True},
    "creaite-boardclosedall": ["raid"],
    "creaite-listcoll": {"decisions|owner|@me": True},
    "creaite-boardw": {"raid|owner": {"@me": 320}},
}


class Work241(V260Case):
    """Checks 13 to 26, on the shared hand-check vault (nothing here changes the record; layouts are this browser's own)."""

    def open_work(self, tab="actions"):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty, #workBoard .bcol')", 15)
        if b.eval("WT") != tab:
            b.click(f'#wtabs button[data-t="{tab}"]')
            b.wait(f"WT==='{tab}'")
        b.pump(0.3)
        return b

    def groups(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tr.wgh.lv1')].map(r=>r.querySelector('.wgn').textContent)")

    def heights(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].slice(0,20).map(r=>Math.round(r.getBoundingClientRect().height))")

    def stored(self, keys):
        return self.b.eval(f"(()=>{{ const o={{}}; {json.dumps(keys)}.forEach(k=>{{ const v=localStorage.getItem(k); o[k]=v===null?null:JSON.parse(v); }}); return o; }})()")

    @staticmethod
    def modal(hs):
        return max(set(hs), key=hs.count) if hs else None

    @needs("241")
    def test_c13_status_and_priority_are_marks(self):
        """13. Status and priority are marks in the list (words in the tooltip and for screen readers); Status and Priority are still
        available as columns in Display."""
        self.reset_page()
        b = self.open_work()
        rows = b.eval("""[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>({id:r.dataset.row,
          marks:r.querySelectorAll('td.title .wkm svg').length, words:(r.querySelector('td.title .wkm .vh')||{}).textContent||'',
          pr:(REC('actions',r.dataset.row)||{}).pr||'', st:(REC('actions',r.dataset.row)||{}).st||''}))""")
        self.assertTrue(rows, "premise: the demo's Work list has rows")
        for r in rows:
            self.assertEqual(r["marks"], 2 if r["pr"] else 1, r)
            self.assertTrue(r["words"].startswith(r["st"]), r)
        b.click("#dispBtn")
        b.wait("!!document.getElementById('dprop-st') && !!document.getElementById('dprop-pr')")
        self.note(13, f"{len(rows)} rows carry their marks and words; Status and Priority stay in Display")
        self.called(13, (LIST, ["test_status_and_priority_marks_beside_the_columns_with_words"], ABC))

    @needs("241")
    def test_c14_compact_by_default_comfortable_remembered(self):
        """14. The default row is a single line with the ID beside the title; Comfortable (today's two lines) is one icon beside the list
        and board icons; the choice is remembered."""
        self.reset_page()
        b = self.open_work()
        self.assertTrue(b.eval("document.getElementById('workWrap').classList.contains('cmp')"))
        self.assertEqual(b.eval("document.getElementById('wdens').nextElementSibling.id"), "wlay")
        self.assertEqual(b.eval("document.querySelector('#wdens [data-dens=cmp]').getAttribute('aria-pressed')"), "true")
        self.assertIsNone(self.stored(["creaite-density"])["creaite-density"], "nothing is written unasked")
        b.wait("!!document.querySelector('#workTbl tr[data-row] td.title > .x.xup')")        # the ID on the title's line
        b.click('#wdens [data-dens="cmf"]')
        b.wait("document.getElementById('workWrap').classList.contains('cmf')")
        self.assertEqual(self.stored(["creaite-density"])["creaite-density"], "cmf")
        b.reload(READY)
        self.open_work()
        self.assertTrue(b.eval("document.getElementById('workWrap').classList.contains('cmf')"), "remembered after a reload")
        self.called(14, (LIST, ["test_compact_by_default_comfortable_on_request_row_height_only"], ABC),
                    ("test_work_density_widths", ["DensityWidths"], ABC))

    @needs("241")
    def test_c15_default_grouping(self):
        """15. Actions are grouped Overdue, This week, Next week, Later, No date, with Closed folded; RAID by priority; Decisions Pending
        then Made; an explicit "no grouping" you chose earlier is kept."""
        self.reset_page()
        b = self.open_work()
        g = self.groups()
        self.assertTrue(g, "premise: the actions are grouped where nothing is saved")
        self.assertEqual(g, [x for x in DUE_GROUPS if x in g], g)
        b.eval("applyFilters({st:['Open','Closed']}); renderWork()")
        head = "document.querySelector('#workTbl tr.wgh[data-gk=\"actions|due|closed\"]')"
        b.wait(head)
        self.assertEqual(self.groups()[-1], "Closed")
        self.assertTrue(b.eval(head + ".classList.contains('coll')"), "Closed starts folded")
        self.open_work("raid")
        g = self.groups()
        self.assertTrue(g)
        self.assertEqual(g, [x for x in ["Urgent", "High", "Medium", "Low"] if x in g], g)
        self.open_work("decisions")
        g = self.groups()
        self.assertTrue(g and set(g) <= {"Pending", "Made", "Withdrawn"}, g)
        self.assertEqual(g[0], "Pending" if "Pending" in g else "Made")
        b.eval("localStorage.setItem('creaite-listgrp', JSON.stringify({actions:'none'}))")
        b.reload(READY)
        self.open_work()
        self.assertEqual(self.groups(), [], "an explicit no grouping is kept")
        self.called(15, (LIST, ["test_default_grouping_per_tab_where_nothing_is_saved", "test_closed_comes_last_folded_where_nothing_is_saved",
                                "test_no_grouping_is_kept_as_a_choice_and_reset_returns_to_the_default"], ABC))

    @needs("241")
    @calls(("test_context_menu", ["test_keyboard_opens_and_drives_it", "test_board_person_and_item_links"], "main"),
           ("test_person_menu", ["test_right_click_a_name_in_work_opens_the_menu_and_draft_email_opens_the_person_popup_on_that_item",
                                 "test_keyboard_shift_f10_arrows_enter_and_esc_returns_focus"], "main"))
    def test_c16_underlines_and_the_context_menu(self):
        """16. The owner and ID keep their underlines; the owner opens their page, the ID opens the peek; right-click, the Menu key and
        Shift+F10 open the context menu with Draft email and Chase."""

    @needs("241")
    @calls((KEYS, ["test_arrows_move_open_and_close_and_left_opens_the_menu",
                   "test_a_click_selects_and_opens_only_while_the_peek_is_open_over_the_page"], ABC))
    def test_c17_keys_move_open_and_close(self):
        """17. Up and Down move; Right or Enter opens the peek; Left closes it, or opens the context menu when no peek is open; a click
        outside the peek closes it; while it is open, a single click on another row swaps it; double-click opens it."""

    @needs("241")
    @calls((KEYS, ["test_s_o_p_t_open_the_cell_editors_on_the_cursor_row", "test_s_uses_the_menu_for_a_hidden_column_and_the_peek_picker_when_open",
                   "test_a_key_on_a_selection_is_the_bulk_change", "test_c_closes_the_cursor_row_with_undo",
                   "test_decisions_have_no_priority_and_are_not_closed", "test_v_and_the_menu_switch_a_row_with_undo_and_the_tag_follows"], ABC))
    def test_c18_property_keys(self):
        """18. S, O, P and T open the status, owner, priority and due date pickers on the cursor row; C closes with an Undo; V toggles
        Client-visible."""

    @needs("241")
    def test_c19_client_visible_switch(self):
        """19. In today's peek, the eye in the bar turns Client-visible on or off in one click (tinted when on), with a badge beside the
        ID, a Client tag in the list, and Undo."""
        self.reset_page()
        b = self.open_work()
        on, off = b.eval("[ (A.find(x=>x.client&&x.st==='Open')||{}).id||null, (A.find(x=>!x.client&&x.st==='Open')||{}).id||null ]")
        self.assertTrue(off, "premise: an open item that is not client-visible")
        for id_, want in ((on, True), (off, False)):
            if not id_:
                continue
            tag = b.eval(f"!!document.querySelector('#workTbl tr[data-row=\"{id_}\"] td.title .tg[data-tg=cv]')")
            self.assertEqual(tag, want, f"{id_}: the Client tag in the list")
            b.eval(f"openRecord('actions',{id_!r})")
            b.wait(f"pkOn()&&CUR&&CUR.id==={id_!r}")
            self.assertEqual(b.eval("document.getElementById('pkCv').getAttribute('aria-pressed')"), str(want).lower(), id_)
            self.assertEqual(b.eval("document.getElementById('pkCv').dataset.key"), "V")
            self.assertEqual(b.eval("!!document.querySelector('#pkId .cv')"), want, f"{id_}: the badge beside the ID")
            if want:
                self.assertNotEqual(b.eval("getComputedStyle(document.getElementById('pkCv')).backgroundColor"),
                                    b.eval("getComputedStyle(document.getElementById('pkLink')).backgroundColor"), "tinted when on")
            b.eval("closePanel()")
        self.note(19, f"states read on {on or 'no client-visible item (on state from the builders tests only)'} and {off}")
        self.called(19, (KEYS, ["test_the_peek_eye_shows_and_switches_client_visible",
                                "test_turning_on_without_messaging_opens_the_peek_and_saves_nothing"], ABC))

    @needs("241d")
    @calls(("test_item_history", ["Matrix", "Single"], "v26-work-items-d"),
           ("test_item_history_route", ["HistoryRoute"], "v26-work-items-d and its live_server.diff"))
    def test_c20_complete_history(self):
        """20. The peek's Activity is a complete history: change a field through the peek, a cell, the bulk bar, the context menu and
        Review, and each shows one event with who, via where, before and after; an undo strikes the original event through and adds
        its own."""

    @needs("241")
    @calls(("test_work_filter_picker", ["Picker"], "main"), ("test_filter_panel_room", ["Room"], "main"),
           ("test_work_filters_live", ["WorkToolbarFilters"], "main"))
    def test_c21_filter_panel_as_today(self):
        """21. The Filter panel and the five quick filters work as today (Find a field, is / is not, counts, Result, Clear all, Done)."""

    @needs("241")
    def test_c22_tags_sit_level(self):
        """22. The tags in a row (Raised again, Client, workstream) sit level on one line."""
        self.reset_page()
        b = self.open_work()
        spread = b.eval("""[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>{
          const els=[...r.querySelectorAll('td.title .wkm, td.title .tg, td.title .tag')].filter(e=>e.getClientRects().length);
          if(els.length<2) return null; const c=els.map(e=>{ const q=e.getBoundingClientRect(); return (q.top+q.bottom)/2; });
          return [r.dataset.row, Math.round((Math.max(...c)-Math.min(...c))*10)/10]; }).filter(Boolean)""")
        self.assertTrue(spread, "premise: rows with a mark and a tag")
        off = [s for s in spread if s[1] > 3]
        self.assertEqual(off, [], f"tags more than 3 px off the line: {off[:5]}")
        self.note(22, f"{len(spread)} rows with tags, worst {max(s[1] for s in spread)} px")

    @needs("241")
    def test_c23_row_heights(self):
        """23. Compact rows are about 40 px high and Comfortable about 57 px."""
        self.reset_page()
        b = self.open_work()
        compact = self.modal(self.heights())
        b.click('#wdens [data-dens="cmf"]')
        b.wait("document.getElementById('workWrap').classList.contains('cmf')")
        b.pump(0.3)
        comfy = self.modal(self.heights())
        self.assertTrue(compact and 38 <= compact <= 42, compact)
        self.assertTrue(comfy and 55 <= comfy <= 59, comfy)
        self.note(23, f"compact {compact} px, comfortable {comfy} px (the commonest row)")

    @needs("241")
    def test_c24_saved_layout_comes_back_unchanged(self):
        """24. With saved column widths, order and visibility, grouping, board collapse and saved views set, run the update and reload:
        every one comes back unchanged."""
        b = self.b
        self.reset_page()
        for k, v in LAYOUT.items():
            b.eval(f"localStorage.setItem({k!r}, {json.dumps(json.dumps(v))})")
        b.reload(READY)
        for tab in ("actions", "raid", "decisions"):
            self.open_work(tab)
        self.open_work("actions")
        heads = b.eval("[...document.querySelectorAll('#workTbl thead th[data-col]')].map(t=>t.dataset.col)")
        self.assertEqual(heads, LAYOUT["creaite-colorder"]["actions"], "the saved order and visibility")
        self.assertEqual(self.groups(), [], "the saved no grouping")
        for _ in range(2):
            b.reload(READY)
            self.open_work("raid")
            self.open_work("actions")
        self.assertEqual(self.stored(sorted(LAYOUT)), LAYOUT, "every saved key comes back unchanged")
        extra = b.eval(f"Object.keys(localStorage).filter(k=>/^creaite-(col|work|board|list|dens)/.test(k)&&!{json.dumps(sorted(LAYOUT))}.includes(k))")
        self.assertEqual(extra, [], "nothing added unasked")
        self.note(24, f"{len(LAYOUT)} keys through the release build and two reloads; the update step itself is the builders' test")
        self.called(24, ("test_work_layout_survives", ["test_every_saved_key_survives_the_new_build_and_a_reload"], ABC))

    @needs("241")
    @calls(("test_work_layout_survives", ["test_a_board_column_collapse_survives_a_reload"], ABC), ("test_work_board", ["BoardLayout"], "main"))
    def test_c25_board_resize_and_collapse_survive(self):
        """25. A board resize and a column collapse survive an update."""

    @needs("241")
    @calls(("test_work_layout_survives", ["test_a_list_column_resize_survives_a_reload_with_its_order_and_visibility"], ABC))
    def test_c26_list_column_resize_survives(self):
        """26. Resize a list column (mouse and keyboard), reload: the width is kept; double-click puts it back."""


# ══ #183 Draft email delivery ════════════════════════════════════════════════════════════════════════════════════════════════════

DD = "v26-draft-delivery"
DDH = ("Off: creaite builds the email and you copy and paste it into Outlook. On: creaite puts it in your Outlook Drafts folder, ready "
       "for you to check and send. It never sends anything. Turn it off if you can't write to Outlook.")


class Draft183(V260Case):
    """Checks 28 to 38 (27 and 39 are live only). Reads only."""

    @needs("183")
    def test_c28_the_setting_is_off_by_default(self):
        """28. Settings › Essentials has a Draft email card with "Create drafts in Outlook" (draft_email.outlook_drafts), off by default,
        its help text as the brief, and the Outlook access row with Check; with it off a draft request is refused."""
        self.assertIn(dig(self.vault_json("system/config/settings.json"), "draft_email.outlook_drafts"), (None, False))
        self.assertIs(dig(self.vault_json("system/templates/settings-defaults.json"), "draft_email.outlook_drafts"), False)
        b = self.b
        b.eval("go('settings','essentials')")
        row = "document.querySelector('[data-keys=\"draft_email.outlook_drafts\"]')"
        b.wait(f"!!{row}", 15)
        self.assertEqual(b.eval(f"{row}.querySelector('span[id]').textContent"), "Create drafts in Outlook")
        self.assertEqual(b.eval(f"{row}.querySelector('small').textContent"), DDH)
        self.assertFalse(b.eval(f"{row}.querySelector('input[type=checkbox]').checked"))
        self.assertEqual(b.eval("document.querySelector('#ddAcc span[id]').textContent"), "Outlook access")
        self.assertEqual(b.eval("document.getElementById('ddCheck').textContent"), "Check")
        self.assertIn("Draft email", self.texts("#settingsBody [data-ess] h2"))
        self.called(28, ("test_draft_delivery_popup", ["EssentialsCard.test_the_draft_email_card_is_second_with_its_words_and_off"], DD),
                    ("test_draft_delivery", ["SettingAndRequest.test_the_setting_is_off_by_default_and_a_request_is_refused_while_off"], DD))

    @needs("183")
    @calls(("test_draft_delivery_popup", ["EssentialsCard.test_check_says_yes_with_the_time_or_no_and_turns_the_setting_off"], DD),
           ("test_draft_delivery", ["Access"], DD))
    def test_c29_the_outlook_access_check(self):
        """29. Check says "You can create drafts in Outlook (checked hh:mm)." or "Outlook says you can't write here, so drafts stay copy
        and paste." and turns the setting off; read-only access, a refusal or no answer never count as yes."""

    @needs("183")
    @calls(("test_draft_delivery_popup", ["Popup.test_off_is_todays_popup"], DD))
    def test_c30_off_is_todays_popup(self):
        """30. With the setting off the Draft email popup is today's: "Nothing is sent: copy it and paste it into Outlook", Copy email,
        Copy as plain text, I sent it (chase only), Close."""

    @needs("183")
    @calls(("test_draft_delivery_popup", ["Popup.test_on_offers_create_draft_first_keeps_the_copies_and_drops_i_sent_it"], DD))
    def test_c31_on_offers_create_draft(self):
        """31. With it on: the header says creaite puts a draft in your Outlook Drafts folder; Create draft in Outlook is first, Copy email
        and Copy as plain text stay, there is no I sent it."""

    @needs("183")
    @calls(("test_draft_delivery_popup", ["Popup.test_the_draft_body_is_the_previews_html_and_the_copys_html",
                                          "Popup.test_the_email_is_markup_outlook_takes_in_the_copy_and_the_draft_edited_or_not"], DD),
           ("test_draft_delivery", ["SettingAndRequest.test_the_body_is_the_previews_html_byte_for_byte_with_the_subject_and_to_as_shown",
                                    "Markup"], DD))
    def test_c32_the_draft_is_the_previews_email(self):
        """32. The draft's body is the preview's own HTML as edited (colours, table, project heading, overdue dates in red), the same as
        Copy email, in markup Outlook takes; subject and To as shown."""

    @needs("183")
    @calls(("test_draft_delivery_popup", ["Popup.test_no_address_on_record_says_so_and_still_offers_the_draft"], DD),
           ("test_draft_delivery", ["SettingAndRequest.test_no_address_on_record_still_makes_the_draft_with_nothing_in_to"], DD))
    def test_c33_no_address_on_record(self):
        """33. A person with no email address on record: the popup says so before and after, and the draft is still created with nothing
        in To; the chase is still recorded."""

    @needs("183")
    @calls(("test_draft_delivery_popup", ["Popup.test_after_the_draft_is_made_the_button_reads_draft_created_and_the_chase_is_recorded"], DD),
           ("test_draft_delivery", ["ChaseRecords.test_a_draft_created_records_the_chase_without_i_sent_it",
                                    "ChaseRecords.test_drafted_json_holds_references_and_fingerprints_only"], DD))
    def test_c34_draft_created_and_the_chase_recorded(self):
        """34. After the draft: "Draft created in Outlook (your Drafts folder)…" with Open in Outlook, the button reads Draft created, and
        the chase is recorded without I sent it (references only)."""

    @needs("183")
    @calls(("test_draft_delivery_popup", ["Popup.test_a_refusal_keeps_the_email_records_nothing_and_offers_copy_it_instead"], DD),
           ("test_draft_delivery", ["Check", "ChaseRecords.test_a_refused_draft_records_nothing"], DD))
    def test_c35_a_refusal_keeps_the_email(self):
        """35. If Outlook refuses: "Outlook would not create the draft (reason). Nothing was sent and nothing was recorded." with Copy it
        instead and a pointer to the setting; the email is kept."""

    @needs("183")
    @calls(("test_draft_delivery", ["SentItems", "SweepStage"], DD),
           ("test_draft_delivery_popup", ["Popup.test_a_copy_with_the_setting_on_leaves_the_references_for_the_sweep"], DD))
    def test_c36_sent_items_mark_it_sent(self):
        """36. A drafted chase is marked sent once a sweep finds it in Sent Items (a copied one is recorded then too); another subject,
        recipient or time does not match."""

    @needs("183", "183r")
    @calls(("test_draft_route", ["Route"], "Jarvis's live_server.diff (test from dev/proposals/draft-delivery)"),
           ("test_draft_delivery", ["NeverSends"], DD))
    def test_c37_the_route_and_the_guard(self):
        """37. The live server's token-checked route makes the draft with create-draft only, refuses while off and without the token,
        records nothing on a refusal; nothing can send."""

    @needs("183")
    def test_c38_the_card_and_popup_look(self):
        """38. The Draft email card, its Outlook access row and the popup read cleanly, light and dark, 1400 and 900 px (judgement)."""
        k = self.sheet(38, "settings-essentials", widths=(1400, 900),
                       prepare=lambda b: b.eval("document.getElementById('ddAcc')?.scrollIntoView({block:'center'})"))
        self.note(38, f"{k} screenshots of the card; the popup is the builders' Popup and Popup900 tests")


# ══ #246 Settings clean-up and tabs ══════════════════════════════════════════════════════════════════════════════════════════════

ST = "v26-settings-tabs"
SPAGE = "test_settings_page"
TABS = ["Essentials", "Work and reports", "Sweep and Intake", "Reports and minutes", "AI drafts", "Look and help", "Advanced", "Health"]
SUBS = ["Review and warnings", "Current state", "Archiving and backups", "Folders and OneDrive", "Server, search and logs"]


class Settings246(V260Case):
    """Checks 40 to 45. Reads only (44 proves it)."""

    def open_tab(self, cat):
        b = self.b
        b.eval(f"go('settings',{cat!r})")
        b.wait("VIEW==='settings' && document.querySelectorAll('#settingsBody [data-sec]').length>0", 15)
        b.pump(0.3)

    def query(self, q):
        self.b.eval(f"(()=>{{ const e=document.getElementById('setq'); e.value={q!r}; e.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")

    def every_page(self):
        cats = [c for c, _ in self.b.eval("SETCATS")]
        for c in cats:
            self.open_tab(c)
            if c == "advanced":
                for s, _ in self.b.eval("ADVSUBS"):
                    self.open_tab(s)
        return cats

    @needs("246")
    def test_c40_the_tab_list(self):
        """40. Settings is tabs: Essentials, Work and reports, Sweep and Intake, Reports and minutes, AI drafts, Look and help, Advanced,
        Health; Advanced has five sub-tabs (Review and warnings, Current state, Archiving and backups, Folders and OneDrive, Server,
        search and logs) and a line saying most people never open it."""
        self.open_tab("essentials")
        self.assertEqual(self.texts("#setcats button"), TABS)
        self.assertEqual(self.b.eval("document.querySelectorAll('#setcats [aria-selected=true]').length"), 1)
        self.open_tab("advanced")
        self.assertEqual(self.texts("#subtabs [role=tab]"), SUBS)
        self.assertIn("most people never open", self.b.eval("document.querySelector('#settingsBody .advnote').textContent"))
        self.called(40, (SPAGE, ["test_the_tabs_are_listed_on_the_left", "test_advanced_has_five_sub_tabs_and_says_most_people_never_open_it"], ST))

    @needs("246")
    def test_c41_what_went(self):
        """41. People and projects and Legacy are on no tab; the per-project client report rhythms are gone from Reminders (each project's
        settings hold them); Reminders on and Dismissed reminders stay."""
        self.open_tab("essentials")
        self.assertNotIn("People and projects", self.texts("#setcats button"))
        seen = set()
        for c in self.every_page():
            secs = self.b.eval("[...document.querySelectorAll('#settingsBody [data-sec]')].map(s=>s.dataset.sec)")
            seen.update(secs)
            self.assertNotIn("Legacy", self.texts("#settingsBody h2"), c)
        self.assertFalse({"people", "workstreams", "projects"} & seen, sorted(seen))
        self.open_tab("reports")
        self.assertFalse(self.b.eval("!!document.querySelector('#settingsBody [data-rhythm]')"))
        self.assertTrue(self.b.eval("!!document.querySelector('[data-sec=reminders] [data-k=remindersOn]')"))
        self.called(41, (SPAGE, ["test_client_report_rhythms_are_no_longer_in_reminders",
                                 "test_the_old_people_and_projects_addresses_open_their_new_homes"], ST))

    @needs("246")
    def test_c42_search_reaches_every_key(self):
        """42. Settings search finds every setting by its own label and says which tab it is on (Advanced › its sub-tab)."""
        rows = self.py("import settings_catalogue as c; print(json.dumps([(r['key'], r['label'], r['tab']) for r in c.catalogue()['settings'] if r['tab']]))")
        self.open_tab("essentials")
        b = self.b
        names = dict(b.eval("SETCATS"))
        names.update({f"advanced/{k}": f"Advanced › {v}" for k, v in b.eval("ADVSUBS")})
        find = """((key,ess)=>{ const has=x=>!x.hidden&&((x.dataset.keys||'').split(' ').includes(key)||(typeof rowKeys==='function'&&rowKeys(x).includes(key)));
          const all=[...document.querySelectorAll('#settingsBody .srow')].filter(has), r=all.find(x=>ess||!x.closest('#set-essentials'))||all[0];
          if(!r) return null; const c=r.closest('[data-sec]'), p=c&&c.previousElementSibling;
          return c.id==='set-essentials'?'Essentials':p&&p.classList.contains('setcrumb')?p.textContent:''; })"""
        checked, by_text, wrong = 0, [], []
        for key, label, tab in rows:
            if (tab == "essentials" and key.startswith("drafting.")) or key.startswith("dashboard.rail."):
                continue                  # the AI drafts shortcut, and the rail's Customise dialog
            self.query(label)
            got, end = None, time.time() + 10
            while got is None and time.time() < end:
                got = b.eval(f"{find}({key!r},{json.dumps(tab == 'essentials')})")
                if got is None:
                    time.sleep(0.1)
            if got is None:
                self.assertTrue(b.eval("document.querySelectorAll('#settingsBody .srow:not([hidden]),#settingsBody .igrow').length>0"), (key, label))
                by_text.append(key)
                continue
            checked += 1
            if not got.startswith(names[tab]):
                wrong.append((key, got, tab))
        self.assertEqual(wrong, [])
        self.assertLessEqual(len(by_text), 4, by_text)
        self.note(42, f"{checked} keys found under their tab, {len(by_text)} by text ({', '.join(by_text)})")
        self.called(42, (SPAGE, ["test_search_finds_every_shown_setting_and_says_which_tab_it_is_on"], ST))

    @needs("246")
    def test_c43_every_setting_on_one_tab(self):
        """43. Every setting has one home: each catalogue key is on one tab or Advanced sub-tab, and only Legacy has none."""
        out = self.py("import settings_catalogue as c; k=c.catalogue(); print(json.dumps({'rows':[(r['key'],r['group'],r['tab']) for r in k['settings']],"
                      "'tabs':[t[0] for t in k['tabs']],'subs':[t[0] for t in k['advanced_subs']]}))")
        homes = set(out["tabs"]) | {f"advanced/{s}" for s in out["subs"]}
        bad = [(k, g, t) for k, g, t in out["rows"] if (t is None and g != "Legacy") or (t is not None and t not in homes)]
        self.assertEqual(bad, [])
        self.note(43, f"{len(out['rows'])} keys")
        self.called(43, (SPAGE, ["test_every_setting_on_the_page_appears_in_exactly_one_category"], ST))

    @needs("246")
    def test_c44_saved_values_never_rewritten(self):
        """44. Opening every tab and sub-tab and searching never rewrites a saved value: settings.json and its log are unchanged."""
        files = ("system/config/settings.json", "system/config/settings-log.jsonl")
        before = self.digest(*files)
        cats = self.every_page()
        self.query("sweep")
        self.b.pump(0.5)
        self.assertEqual(self.digest(*files), before)
        self.note(44, f"{len(cats)} tabs and the Advanced sub-tabs visited")

    @needs("246")
    def test_c45_settings_look(self):
        """45. The tabs, a card per group and Advanced's sub-tabs read cleanly, light and dark, 1400 and 900 px (judgement)."""
        k = self.sheet(45, "settings-tabs", widths=(1400, 900))
        self.note(45, f"{k} screenshots")


# ══ #247 Project settings v2 ═════════════════════════════════════════════════════════════════════════════════════════════════════

PS = "v26-project-settings-v2"
PSV2 = "test_project_settings_v2"
PSECTIONS = ["general", "people", "ws", "miles", "rep", "arch"]
PLABELS = ["Project", "People and partners", "Workstreams", "Milestones", "Client report and logos", "Archive and close"]
FOLLOWED = """[...document.querySelectorAll('.pstar,[aria-label=Followed],#peFollow')].filter(e=>!e.closest('#v-psettings,#personEditHost')&&e.getClientRects().length).length
  + ([...document.querySelectorAll('.view:not([hidden])')].filter(v=>v.id!=='v-psettings').some(v=>/\\bFollowed\\b/.test(v.innerText))?100:0)"""


class Project247(V260Case):
    """Checks 46 to 52 on Falcon Data Platform. Reads only."""

    def open_ps(self, cat="general"):
        b = self.b
        b.eval(f"go('psettings','FAL'); psCat.value={cat!r}; navWrite(false)")
        b.wait("VIEW==='psettings' && !!document.querySelector('#psBody [data-pssec=arch]') && !!document.querySelector('#psPeopleRows')", 15)
        b.pump(0.6)

    @needs("247")
    def test_c46_one_scrolling_page_with_anchors(self):
        """46. Project settings is one scrolling page: sections Project, People and partners, Workstreams, Milestones, Client report and
        logos, Archive and close, in that order; a sticky side list of anchors marks where you are; no tabs, no summary header."""
        self.open_ps()
        b = self.b
        self.assertEqual(b.eval("[...document.querySelectorAll('#psBody [data-pssec]')].map(s=>s.dataset.pssec)"), PSECTIONS)
        self.assertEqual(self.texts("#pscats [data-pscat]"), PLABELS)
        self.assertEqual(b.eval("document.querySelectorAll('#v-psettings [role=tab],#v-psettings [role=tablist]').length"), 0)
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#v-psettings .setside')).position"), "sticky")
        self.assertEqual(b.eval("document.querySelector('#pscats [aria-current=true]').dataset.pscat"), "general")
        self.called(46, (PSV2, ["Page.test_one_scrolling_page_with_the_sections_in_order_and_no_tabs", "Page.test_scrolling_marks_where_you_are"], PS))

    @needs("247")
    def test_c47_an_anchor_goes_to_its_section(self):
        """47. A click on an anchor scrolls to its section, marks it and writes the address (#project-settings=FAL&c=ws); the list stays
        in view."""
        self.open_ps()
        b = self.b
        b.eval("document.querySelector('#pscats [data-pscat=ws]').click()")
        b.wait("location.hash==='#project-settings=FAL&c=ws'", 10)
        b.wait("document.querySelector('#pscats [aria-current=true]')?.dataset.pscat==='ws'", 10)
        self.assertGreaterEqual(b.eval("document.querySelector('#pscats').getBoundingClientRect().top"), 0)
        self.called(47, (PSV2, ["Page.test_an_anchor_scrolls_to_its_section_marks_it_and_writes_the_address",
                                "Page.test_the_address_opens_at_its_section_and_the_old_names_still_work"], PS))

    @needs("247")
    def test_c48_archive_and_close_set_apart(self):
        """48. Archive and close is last, set apart with a red-tinted border, with Archive and Close each asking first."""
        self.open_ps("arch")
        b = self.b
        self.assertEqual(b.eval("document.querySelector('#s-arch h2').textContent"), "Archive and close")
        self.assertTrue(b.eval("!!document.querySelector('#s-arch .psdanger #psArchive') && !!document.querySelector('#s-arch .psdanger #psClose')"))
        red, plain = b.eval("[getComputedStyle(document.querySelector('#s-arch .card')).borderTopColor, getComputedStyle(document.querySelector('#s-miles .card')).borderTopColor]")
        self.assertNotEqual(red, plain)

    @needs("247")
    def test_c49_people_on_the_project(self):
        """49. People on this project: the columns Name, Email, Organisation · role, Aliases, Actions, RAID; one entry per person; needs
        details with what is missing (never "not in the register" or "Add to register")."""
        self.open_ps("people")
        b = self.b
        self.assertEqual(self.texts("#psPeople thead th")[:6], ["Name", "Email", "Organisation · role", "Aliases", "Actions", "RAID"])
        names = b.eval("[...document.querySelectorAll('#psPeopleRows tr[data-pn]')].map(r=>r.dataset.pn)")
        self.assertTrue(names, "premise: Falcon has people")
        self.assertEqual(len(names), len(set(names)), "one entry per person")
        page = b.eval("document.querySelector('#s-people').textContent")
        self.assertNotIn("not in register", page.lower())
        self.assertNotIn("Add to register", page)
        for t in b.eval("[...document.querySelectorAll('#psPeopleRows [data-needs]')].map(e=>e.title)"):
            self.assertTrue(t.startswith("Missing: "), t)
        self.note(49, f"{len(names)} people on Falcon")
        self.called(49, (PSV2, ["People"], PS))

    @needs("247")
    def test_c50_workstreams_section(self):
        """50. Workstreams are a section of the project's settings (Workstream, Lead, Keywords, Open items), with no "Fix spellings" or
        "Show retired" footers."""
        self.open_ps("ws")
        self.assertEqual(self.texts("#psWs thead th")[:4], ["Workstream", "Lead", "Keywords", "Open items"])
        txt = self.b.eval("document.querySelector('#s-ws').textContent")
        self.assertNotIn("Fix spellings", txt)
        self.assertNotIn("Show retired", txt)
        self.called(50, (PSV2, ["Workstreams"], PS))

    @needs("247")
    def test_c51_followed_star_on_this_page_only(self):
        """51. A followed person has a star named "Followed" (never "VIP") beside the name here, and no marker anywhere else (Today, Work,
        People, their page, Review, Intake, the project page, Projects)."""
        self.open_ps("people")
        b = self.b
        for label in b.eval("[...document.querySelectorAll('#psPeopleRows .pstar')].map(e=>e.getAttribute('aria-label'))"):
            self.assertEqual(label, "Followed")
        self.assertNotIn("VIP", b.eval("document.querySelector('#s-people').textContent"))
        stars = b.eval("document.querySelectorAll('#psPeopleRows .pstar').length")
        for js, ready in (("go('today')", "VIEW==='today'"), ("go('work')", "VIEW==='work'"), ("go('people')", "VIEW==='people'"),
                          ("go('person','Rashid Al Suwaidi')", "VIEW==='person'"), ("go('review')", "VIEW==='review'"),
                          ("go('inbox')", "VIEW==='inbox'"), ("go('cockpit','FAL')", "VIEW==='cockpit'"), ("go('projects')", "VIEW==='projects'")):
            b.eval(js)
            b.wait(ready, 15)
            b.pump(0.3)
            self.assertEqual(b.eval(FOLLOWED), 0, js)
        self.note(51, f"{stars} star(s) on Falcon's People; none on 8 other screens")
        self.called(51, (PSV2, ["FollowedIsPrivate", "People.test_a_followed_person_has_a_star_named_followed_and_the_form_has_the_tick"], PS))

    @needs("247")
    def test_c52_project_settings_look(self):
        """52. The page reads as one page: the side list, the sections and Archive and close set apart, light and dark, 1400 and 900 px
        (judgement)."""
        k = self.sheet(52, "psettings", widths=(1400, 900))
        self.note(52, f"{k} screenshots")


# ══ #248 People page v2 (selectors from the spec: confirm when it lands) ═════════════════════════════════════════════════════════

class People248(V260Case):
    """Checks 53 to 57. Reads only."""

    def open_people(self):
        self.b.eval("go('people')")
        self.b.wait("!document.getElementById('v-people').hidden && !!document.querySelector('#v-people table')", 15)
        self.b.pump(0.4)

    @needs("248")
    def test_c53_the_tabs(self):
        """53. The People page has the tabs Everyone, With work, Nothing assigned, Needs attention, and Add a person."""
        self.open_people()
        tabs = [re.sub(r"\s*\d+$", "", x) for x in self.texts("#v-people [role=tab]")]            # each tab carries its count
        self.assertEqual(tabs[:4], ["Everyone", "With work", "Nothing assigned", "Needs attention"])
        self.assertIn("Add a person", self.b.eval("document.getElementById('v-people').innerText"))

    @needs("248")
    def test_c54_the_columns(self):
        """54. Its columns are Name, Email, Organisation, Role, Projects, Actions, RAID, Decisions, Overdue (the counts open in Work)."""
        self.open_people()
        heads = [re.sub(r"\s*[▲▼]$", "", h) for h in self.texts("#v-people thead th") if h]       # the sorted column's arrow
        self.assertEqual(heads[:9], ["Name", "Email", "Organisation", "Role", "Projects", "Actions", "RAID", "Decisions", "Overdue"])

    @needs("248")
    def test_c55_nothing_that_must_not_be_there(self):
        """55. No star or "Followed" for followed people, no merge or Fix spellings, no permanent "Press ? for help" banner (the
        first-visit line, as on every page, may show once), no "Add to register" or "not in the register"."""
        self.open_people()
        b = self.b
        self.assertFalse(b.eval("(()=>{ const f=document.getElementById('hFoot'); return !!f&&!f.hidden&&f.getClientRects().length>0; })()"),
                         "the permanent foot line is dropped on People")
        txt = b.eval("(()=>{ const f=document.querySelector('#v-people #hFirst'); "
                     "return document.getElementById('v-people').innerText.replace(f?f.innerText:'',''); })()")
        for word in ("Followed", "VIP", "Fix spellings", "Merge", "Press ? for help", "Add to register", "not in the register"):
            self.assertNotIn(word, txt)
        self.assertEqual(b.eval("document.querySelectorAll('#v-people .pstar,#v-people [aria-label=Followed]').length"), 0)

    @needs("248")
    def test_c56_needs_details(self):
        """56. A person whose record lacks an email, organisation or role shows "needs details" (the missing parts in a tooltip) and an
        quiet flag (No email and so on) that opens the edit form; Needs attention filters No email, No organisation, No role."""
        self.open_people()
        b = self.b
        tips = b.eval("[...document.querySelectorAll('#v-people [data-needs]')].map(e=>e.title||e.dataset.tip||'')")
        self.assertTrue(tips, "premise: a demo person with something missing")
        for t in tips:
            self.assertTrue(t.startswith("Missing: "), t)
        self.assertTrue(b.eval("[...document.querySelectorAll('#v-people button')].some(x=>x.hasAttribute('data-pl-details')&&/^No /.test(x.textContent.trim()))"))

    @needs("248")
    def test_c57_people_look(self):
        """57. The People page reads cleanly, light and dark, 1400 and 900 px (judgement)."""
        k = self.sheet(57, "people", widths=(1400, 900))
        self.note(57, f"{k} screenshots")


# ══ #250 fetch transcripts ═══════════════════════════════════════════════════════════════════════════════════════════════════════

FT = "v26-fetch-transcripts"
FTH = ("Off: creaite fetches a transcript when you press Process. On: each sweep fetches the transcripts of meetings that have ended, so they "
       "are ready when you open Intake. It only reads: no AI runs and nothing is written to the tracker. Confidential meetings are never fetched.")


class Fetch250(V260Case):
    """Checks 58 to 62 (63 is live only)."""

    @needs("250")
    def test_c58_off_by_default(self):
        """58. Settings › Sweep and Intake has "Fetch transcripts as they appear" (sweep.fetch_transcripts), off by default, with the
        brief's help text."""
        self.assertIn(dig(self.vault_json("system/config/settings.json"), "sweep.fetch_transcripts"), (None, False))
        self.assertIs(dig(self.vault_json("system/templates/settings-defaults.json"), "sweep.fetch_transcripts"), False)
        b = self.b
        b.eval("go('settings','sweep')")                                        # Sweep and Intake (v2.6 tabs)
        row = "[...document.querySelectorAll('#settingsBody .srow')].find(r=>r.querySelector('span[id]')?.textContent==='Fetch transcripts as they appear')"
        b.wait(f"!!{row}", 15)
        self.assertEqual(b.eval(f"{row}.querySelector('small').textContent"), FTH)
        self.assertFalse(b.eval(f"{row}.querySelector('input[type=checkbox]').checked"))
        self.called(58, ("test_fetch_transcripts", ["Fetch.test_the_setting_is_off_by_default"], FT))

    @needs("250")
    @calls(("test_fetch_transcripts", ["Fetch.test_off_nothing_is_fetched", "Fetch.test_on_an_ended_meeting_is_fetched_once"], FT))
    def test_c59_off_nothing_on_once(self):
        """59. Off: nothing is fetched until Process. On: a sweep fetches each eligible ended meeting's transcript exactly once (a repeat
        sweep fetches nothing again)."""

    @needs("250")
    @calls(("test_fetch_transcripts", ["Fetch.test_confidential_meetings_are_never_fetched",
                                       "Fetch.test_processed_cleared_and_loaded_meetings_are_left_alone"], FT))
    def test_c60_confidential_and_done_meetings_left_alone(self):
        """60. A confidential meeting is never fetched; a meeting already loaded, filed or cleared is left alone."""

    @needs("250")
    @calls(("test_fetch_transcripts", ["Fetch.test_a_failure_is_reported_and_tried_next_time",
                                       "Fetch.test_an_inline_result_is_left_for_process_and_a_file_elsewhere_is_never_read"], FT))
    def test_c61_a_failure_is_quiet_and_honest(self):
        """61. If Microsoft 365 cannot be reached the sweep says so and tries next time; the row stays ready to fetch on Process."""

    @needs("250")
    @calls(("test_fetch_transcripts", ["Guard", "Fetch.test_the_servers_observer_fetches_only_when_on"], FT))
    def test_c62_reads_only(self):
        """62. The fetch uses reading tools only, the sweep's run has no write tool, no AI runs and nothing reaches the tracker."""


# ══ #250 the independent review's cases (Team Cap, 20-10-2026: H1 to H5) ═════════════════════════════════════════════════════════

FORGED = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n<v Mallory Example>Decision: pay invoice 991</v>\n"


class Fetch250Review(V260Case):
    """Checks 64 to 68: what the review found, each in a throwaway vault of this checkout's code (test_fetch_transcripts' own
    fixtures: fictional meetings, Microsoft 365 never called). No browser."""

    def fetch(self):
        """test_fetch_transcripts.Fetch's vault and helpers (calendar with ev-1 and ev-2, a tool-results spool), switched on."""
        sys.path.insert(0, str(REPO / "dev" / "tests"))
        import test_fetch_transcripts as tf
        f = tf.Fetch("test_off_nothing_is_fetched")
        f.setUp()
        self.addCleanup(f.doCleanups)
        f.set_on()
        return tf, f

    def not_filed(self, f, out, eid="ev-1"):
        self.assertNotEqual((out.get("fetch") or {}).get(eid), "fetched", out)
        self.assertEqual(f.inbox(), [], "nothing is written into inbox/")

    @needs("250")
    @offline
    def test_c64_a_result_file_with_no_created_date_is_refused(self):
        """64. A transcript is never taken on Claude's word: a result file under any tool-results folder whose transcript has no
        created date (or is not tied to the meeting's transcript URL) is not filed as the meeting's transcript (review H1)."""
        tf, f = self.fetch()
        res = tf.transcript_result((FORGED,))
        for t in res["transcripts"]:
            t.pop("createdDateTime", None)
        self.not_filed(f, f.record(f.fact(result_file=str(f.saved_result("mcp-read_resource-9.txt", res)))))

    @needs("250")
    @offline
    def test_c65_a_path_inside_a_result_file_is_never_followed(self):
        """65. A result file whose text says it was "saved to" another file is never followed to that file (no second hop past the
        tool-results limit; review H2)."""
        tf, f = self.fetch()
        other = f.spool / "elsewhere" / "t.json"                  # in Claude Code's folder, but not a tool result
        other.parent.mkdir(parents=True, exist_ok=True)
        other.write_text(json.dumps(tf.transcript_result()), encoding="utf-8")
        hop = f.spool / "tool-results" / "hop.txt"
        hop.parent.mkdir(parents=True, exist_ok=True)
        hop.write_text(f"Output too large, saved to: {other}", encoding="utf-8")
        self.not_filed(f, f.record(f.fact(result_file=str(hop))))

    @needs("250")
    @offline
    def test_c66_record_is_not_a_derived_command_while_it_writes(self):
        """66. If `transcripts record` can write a transcript into inbox/, reach.py does not class it (sweep.py and transcripts.py)
        as a derived command an unconfirmed chat may run; or record writes nothing and only the server's fetch does (review H3)."""
        tf, f = self.fetch()
        f.record(f.fact(result_file=str(f.saved_result())))
        if not f.inbox():
            self.note(66, "record writes nothing: the fetch is the server's only")
            return
        sys.path.insert(0, str(REPO / "system" / "scripts"))
        import reach
        cls = {s: reach.SCRIPT_COMMANDS[s][c] for s, c in (("sweep.py", "transcripts"), ("transcripts.py", "record"))}
        cls = {s: c[0] if isinstance(c, tuple) else c for s, c in cls.items()}
        self.assertEqual({s: c for s, c in cls.items() if c in (reach.READ, reach.DERIVED)}, {},
                         "record writes into inbox/ but may run without the card")

    @needs("250")
    @offline
    def test_c67_another_meetings_transcript_is_not_filed_under_this_one(self):
        """67. Another meeting's transcript from the same day (ev-2's, Weekly sync 12, at 15:00) is never filed under ev-1's title
        (review H4)."""
        tf, f = self.fetch()
        res = tf.transcript_result()
        res["meeting"] = {"id": "m2", "subject": "Weekly sync 12"}
        for t in res["transcripts"]:
            t["createdDateTime"] = f"{tf.DAY}T15:00:30Z"
            t["endDateTime"] = f"{tf.DAY}T15:29:00Z"
        self.not_filed(f, f.record(f.fact(result_file=str(f.saved_result("mcp-read_resource-7.txt", res)))))

    @needs("250")
    @offline
    def test_c68_confidential_never_fetched_even_with_no_sensitivity_saved(self):
        """68. A confidential meeting is never fetched, even when the saved calendar has no sensitivity for it: the live event's own
        sensitivity, read in the same run, is checked before the transcript is written (review H5)."""
        tf, f = self.fetch()
        cal_p = f.v.root / "system/staging/calendar.json"
        cal = json.loads(cal_p.read_text())
        row = next(e for e in cal["days"][tf.DAY] if e.get("id") == "ev-1")
        self.assertNotIn("sensitivity", row, "premise: the saved calendar says nothing about its sensitivity")
        ev = tf.event()
        ev["sensitivity"] = "confidential"
        steps = [("calendar:///events/ev-1", ev), (tf.URI, tf.transcript_result())]
        code = ("import json, sys; sys.path.insert(0,'system/scripts'); import transcripts as T; j = T.SweepFetch(); "
                f"steps = json.loads({json.dumps(json.dumps(steps))}); "
                "[j.observe(T.M365 + 'read_resource', {'uri': u}, json.dumps(r)) for u, r in steps]; print(json.dumps(j.outcomes))")
        import subprocess
        r = subprocess.run([sys.executable, "-c", code], cwd=f.v.root, capture_output=True, text=True, env=f.env)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        self.not_filed(f, {"fetch": json.loads(r.stdout)})


# ══ #183 the Outlook-safe markup, on the hand-check vault ═════════════════════════════════════════════════════════════════════════

OVERDUE_OWNER = """(()=>{ const t=new Date().toISOString().slice(0,10), c={};
  A.filter(x=>x.st==='Open'&&x.o&&x.o!==S.me&&x.due&&x.due<t).forEach(x=>{ c[x.o]=(c[x.o]||0)+1; });
  return (Object.entries(c).sort((a,b)=>b[1]-a[1])[0]||[null])[0]; })()"""


class Markup183(V260Case):
    """Check 69. Reads only: the popup is opened and closed, nothing is copied or recorded."""

    @needs("183")
    def test_c69_the_email_is_markup_outlook_takes(self):
        """69. A chase built on the hand-check vault (a person's overdue actions: the project heading, the table, the due date in
        red) is only the markup Outlook's create-draft takes (no span, font, class, id, data-, style element, comment or CSS
        variable), with the overdue colour on its cell; the same HTML is what Copy email and the draft carry."""
        b = self.b
        who = b.eval(OVERDUE_OWNER)
        self.assertTrue(who, "premise: someone else in the demo vault owns an overdue open action")
        b.eval(f"openDraftEmail({who!r},'chase')")
        b.wait("document.getElementById('deDlg')&&document.getElementById('deDlg').open", 15)
        b.eval("document.querySelectorAll('#deInc [data-deit]').forEach(i=>{ if(!i.checked) i.click(); })")
        b.wait("!!document.querySelector('#dePrev table')", 10)
        html = b.eval("deHtml()")
        try:
            problem = self.py(f"import draft_delivery as d; print(json.dumps(d.markup_problem({html!r})))")
            self.assertIsNone(problem, problem)
            self.assertIn("<table", html)
            self.assertRegex(html, r'<td style="[^"]*color:#B3261E', "the overdue date in red, on its cell")
            self.assertNotRegex(html, r"<span\b|<font\b|\sclass=|\sid=|<style|<script|\sdata-|<!--|var\(")
        finally:
            b.eval("document.getElementById('deDlg')?.close()")
        self.note(69, f"a chase to {who}: {len(html)} characters of HTML, all in Outlook's subset")


# ══ the Settings line: the old addresses ════════════════════════════════════════════════════════════════════════════════════════

class SettingsLine(V260Case):
    """Check 70. Reads only."""

    @needs("246", "line")
    def test_c70_old_settings_addresses_open_the_new_homes(self):
        """70. People, Workstreams and Projects have left Settings: the old addresses open the People page, Projects, and (from a
        project) its settings at Workstreams; the side column says where they went."""
        b = self.b
        b.eval("go('settings','essentials')")
        b.wait("VIEW==='settings' && !!document.getElementById('setMoved')", 15)
        self.assertIn("People page", b.eval("document.getElementById('setMoved').textContent"))
        self.assertFalse(b.eval("SETSECTIONS.some(s=>['people','workstreams','projects'].includes(s.id))"))
        b.eval("go('settings','people')")
        b.wait("VIEW==='people' && location.hash.startsWith('#people')", 10)
        b.eval("go('today'); go('settings','projects')")
        b.wait("VIEW==='projects'", 10)
        b.eval("go('cockpit','FAL'); go('settings','workstreams')")
        b.wait("VIEW==='psettings' && psCode.value==='FAL' && psCat.value==='ws'", 10)
        self.called(70, (SPAGE, ["test_the_old_people_and_projects_addresses_open_their_new_homes"], "v26-settings-line"))


# ══ #97 step 1: quiet hours for the alert check ══════════════════════════════════════════════════════════════════════════════════

QH = "v26-quiet-hours"
QROW = "[...document.querySelectorAll('#set-essentials .srow')].find(r=>r.querySelector('span[id]')?.textContent==={!r})"


class Quiet97(V260Case):
    """Checks 71 to 74. Reads only (the saving is the builder's page test)."""

    @needs("97")
    def test_c71_the_rows_and_their_defaults(self):
        """71. Settings › Essentials › People I follow has "Pause alert checks overnight" (on, 19:00 to 07:00) and "Pause alert checks
        on weekend days" (on), after Check every, with the brief's words and never the word VIP."""
        d = dig(self.vault_json("system/templates/settings-defaults.json"), "vip")
        self.assertEqual({k: d.get(k) for k in ("quiet_overnight", "quiet_from", "quiet_to", "quiet_weekend")},
                         {"quiet_overnight": True, "quiet_from": "19:00", "quiet_to": "07:00", "quiet_weekend": True})
        b = self.b
        b.eval("go('settings','essentials')")
        night, wknd = QROW.format("Pause alert checks overnight"), QROW.format("Pause alert checks on weekend days")
        b.wait(f"!!{night} && !!{wknd}", 15)
        labels = b.eval("[...document.querySelector('[data-ess=\"People I follow\"]').querySelectorAll('.srow span[id]')].map(s=>s.textContent)")
        self.assertLess(labels.index("Check every"), labels.index("Pause alert checks overnight"))
        saved = dig(self.vault_json("system/config/settings.json"), "vip") or {}
        want_night = saved.get("quiet_overnight", True) is not False
        self.assertEqual(b.eval(f"{night}.querySelector('input.switch').checked"), want_night)
        self.assertEqual(b.eval(f"[...{night}.querySelectorAll('input[type=text]')].map(e=>e.value)"),
                         [saved.get("quiet_from", "19:00"), saved.get("quiet_to", "07:00")])
        self.assertIn("looks back to the last one, so nothing is missed", b.eval(f"{night}.textContent"))
        self.assertIn("Uses the weekend days set in Essentials › You.", b.eval(f"{wknd}.textContent"))
        self.assertNotRegex(b.eval("document.querySelector('[data-ess=\"People I follow\"]').textContent"), r"\bVIP\b")
        self.called(71, ("test_quiet_hours_page", ["test_the_rows_sit_in_people_i_follow_after_check_every_with_their_defaults",
                                                   "test_the_times_and_switches_save_to_their_keys"], QH),
                    ("test_vip_quiet_hours", ["SettingsAndCatalogue"], QH))

    @needs("97")
    @calls(("test_vip_quiet_hours", ["QuietNow", "NextDue", "LookBack", "DaylightSaving"], QH))
    def test_c72_quiet_time_and_the_look_back(self):
        """72. No check falls between 19:00 and 07:00 or on a weekend day; the first check after reads back to the last one (Friday's
        last on a Monday), daylight saving and a window inside one day included; both switches off is never quiet."""

    @needs("97")
    @calls(("test_quiet_hours_page", ["test_a_time_that_isnt_hh_mm_is_refused_and_the_box_goes_back", "test_no_script_errors"], QH))
    def test_c73_a_bad_time_is_refused(self):
        """73. A time that isn't 24-hour HH:MM is refused with a message and the box goes back; nothing is saved."""

    @needs("97", "97w")
    @calls(("test_vip_quiet_hours", [f"Wiring.{n}" for n in ("test_first_start_after_the_laptop_slept_through_the_weekend",
                                   "test_no_check_in_quiet_time", "test_nothing_the_skip_prints_or_logs_says_vip",
                                   "test_the_first_check_after_quiet_time_looks_back_to_the_last_check",
                                   "test_the_settings_off_restore_todays_behaviour")], QH + " and its live_server.diff"))
    def test_c74_the_alert_check_skips_quiet_time(self):
        """74. With the server's wiring in: no Claude run in quiet time, the first check after it looks back to the last check, the
        switches off restore today's behaviour, and nothing printed or logged says VIP."""


# ══ #252 the archive folder is 99 Archive ═══════════════════════════════════════════════════════════════════════════════════════

AR = "v253-release (#252, merged as no rename and no migration)"
A99 = "test_archive_99"


class Archive252(V260Case):
    """Checks 75 to 81 (82 is live only). Reads only. #252 landed in 2.5.3 as "no rename, no migration" (the old names are read and
    left alone; Health offers nothing), so 78 and 79 check that rather than the draft's Rename offer."""

    @needs("252")
    def test_c75_the_name_is_99_archive(self):
        """75. The archive folder is called 99 Archive: the constants, the never-read default and the saved setting say so; the old
        _Archive and zz Archive are still never read for one release."""
        o = self.py("import paths; print(json.dumps([paths.ARCHIVE, list(paths.OLD_ARCHIVES), paths.LOCATION_DEFAULTS['never_index']]))")
        self.assertEqual(o[0], "99 Archive")
        self.assertEqual(o[1], ["_Archive", "zz Archive"])
        self.assertIn("99 Archive", o[2])
        saved = dig(self.vault_json("system/config/settings.json"), "locations.never_index")
        if saved is not None:
            self.assertIn("99 Archive", saved)
        self.called(75, (A99, ["Names", "OldNamesAreStillSkipped"], AR))

    @needs("252")
    @calls((A99, ["Resolve", "AfterAHandRename", "FollowRules"], AR))
    def test_c76_stored_paths_resolve_under_each_name(self):
        """76. Stored paths never change: an archived project, report or deleted note resolves under 99 Archive, _Archive or zz Archive,
        and a folder renamed by hand is followed (99 Archive wins when two hold the same path)."""

    @needs("252")
    @calls((A99, ["AlwaysTheNewName", "NewMovesGoToTheNewName"], AR))
    def test_c77_moves_go_to_99_archive(self):
        """77. A project archive, the 12-month reports move and Delete note go into 99 Archive only, beside an old folder too; a name
        taken in any of the three is numbered, never shared."""

    @needs("252")
    @calls((A99, ["NoMigrationNoOffer"], AR))
    def test_c78_no_migration_and_no_offer(self):
        """78. Nothing is renamed or migrated: old _Archive and zz Archive folders stay as they are, and Health says nothing about
        them."""

    @needs("252")
    @calls((A99, ["HandRenamed", "HandRenamedProject", "RestoreFromAnOldArchive.test_the_live_server_does_not_treat_the_archive_as_a_project_folder"], AR))
    def test_c79_a_hand_rename_is_followed_and_99_archive_is_never_a_project(self):
        """79. A folder Alan renames by hand is followed (Files lists and opens it, Move back and Undo work, a project restores from
        it); 99 Archive is never taken for a project."""

    @needs("252", "252g")
    @calls((A99, ["MoveRules", "RestoreFromAnOldArchive.test_archive_goes_to_99_archive_then_an_old_name_restore_works_with_undo"], AR))
    def test_c80_the_guarded_moves(self):
        """80. The guarded move rules: a new move goes only into 99 Archive, a restore or move back comes from any of the three names,
        look-alikes are not the archive, the rename kind is gone, and a project archived in _Archive restores with Undo."""

    @needs("252")
    def test_c81_the_page_says_99_archive(self):
        """81. The dashboard and Help say 99 Archive wherever they name the archive folder; _Archive appears only as an old name."""
        page = (self.vault / "dashboard.html").read_text(encoding="utf-8", errors="ignore")
        self.assertTrue("99 Archive" in page, "the dashboard never names 99 Archive")
        help_md = (self.vault / "system/templates/help.md").read_text(encoding="utf-8")
        self.assertTrue("99 Archive" in help_md, "Help never names 99 Archive")
        old = [ln.strip()[:120] for ln in help_md.splitlines() if "_Archive" in ln and "99 Archive" not in ln]
        self.assertEqual(old, [], "a Help line names only the old folder")


# ══ #268 Minutes view v2 ═════════════════════════════════════════════════════════════════════════════════════════════════════════

MV = "v26-minutes-view-v2"
MV2 = "test_minutes_view_v2"
MOPS = "test_minutes_track_ops"


class Minutes268(V260Case):
    """Checks 83 to 89 (89 judgement, by hand). The hand-check vault stages no minutes, so these call the builder's tests: a
    fictional steering committee staged in their own throwaway vault, in real Chrome on a real live server (no Claude runs)."""

    @needs("268")
    @calls((MV2, ["test_01_three_states_their_defaults_clearing_and_the_summary"], MV),
           (MOPS, ["TrackJs.test_the_defaults_follow_the_plan"], MV))
    def test_c83_the_track_column(self):
        """83. Every table's first column is Track: tick registers a work item, cross removes the line, neither keeps it in the minutes
        untracked; actions and issues start ticked, decisions and risks neither; a pressed button clears; the bar says "n work items
        to register · n kept in the minutes only · n removed"; the choice survives a reload."""

    @needs("268")
    @calls((MV2, ["test_02_aligned_tables_one_heading_per_column", "test_03_inline_edit_saves_on_enter_and_esc_puts_it_back",
                  "test_04_owner_priority_and_workstream_dropdowns_in_the_row",
                  "test_05_due_opens_the_deadline_popover_with_words_quick_picks_and_a_calendar"], MV),
           (MOPS, ["RaidWorkstream"], MV))
    def test_c84_aligned_tables_and_editing_in_place(self):
        """84. One heading per column (Track, the item, Owner, and Due, Priority, Workstream where they apply); the words and the
        summary are edited where they stand (Enter or a click away saves, Esc puts them back); Owner, Priority and Workstream are
        drop-downs in the row (a risk takes only the project's own workstreams); Due opens the deadline box."""

    @needs("268")
    @calls((MV2, ["test_06_hover_lights_both_ways",
                  "test_07_the_transcript_choice_rescales_survives_a_reload_and_applies_to_another_meeting",
                  "test_08_the_header_slims_on_scroll_and_shows_the_title", "test_09_ctrl_wheel_zooms_from_50_to_250_and_the_buttons_stay",
                  "test_09b_fit_to_width_stops_at_100_and_centres_the_page_and_zoom_still_goes_past",
                  "test_16_the_full_template_on_one_continuous_sheet_with_a_thin_page_marker",
                  "test_16b_the_page_marker_never_crosses_a_row_or_a_line", "test_17_section_headings_with_their_counts_beside_them"], MV))
    def test_c85_the_transcript_and_the_sheet(self):
        """85. Hovering a row lights its transcript turn and a turn its rows; hiding the transcript widens the page and is remembered
        (after a reload and for another meeting); the header slims on scroll with the title; zoom 50% to 250%, fitted to the width
        but never past 100%; one continuous sheet with a thin page marker that never crosses a row; headings carry their counts."""

    @needs("268")
    @calls((MV2, ["test_10_one_version_icon_tools_and_the_export_menu"], MV), (MOPS, ["TrackChoicesReachOutputs"], MV))
    def test_c86_one_version_and_export(self):
        """86. One version only (no Internal + distributed switch); the bar's tools are icon buttons; Export has Word, PDF, HTML and
        Draft the follow-up email; a crossed line is left out of the follow-up and the exports, and a kept line is marked."""

    @needs("268")
    @calls((MV2, ["test_11_approve_with_a_problem_asks_first_then_registers_the_ticked_items",
                  "test_12_approve_with_no_problem_is_one_click_and_a_cross_removes_the_line",
                  "test_13_approve_with_nothing_ticked_files_the_minutes_with_no_items"], MV),
           (MOPS, ["TrackOps", "RowlessPromise", "TrackJs.test_neither_on_an_update_decided_one_by_one_leaves_it_in_review",
                   "TrackJs.test_a_ticked_closure_is_approved_with_the_minutes",
                   "TrackJs.test_a_kept_line_ticked_is_restored_and_crossed_is_restored_then_removed"], MV))
    def test_c87_approve_minutes_is_one_click(self):
        """87. Approve minutes is one click: "Before approving" only when a ticked item has a real problem (needs details, a possible
        duplicate); "Minutes approved · n work items registered" with Undo; nothing ticked files the minutes with no items (#261);
        Approve, Undo, Approve again gives the same result and nothing leaks to Review."""

    @needs("268")
    @calls((MV2, ["test_14_at_1400_one_row_at_900_two_and_the_transcript_beside_the_sheet",
                  "test_18_dark_theme_the_white_paper_keeps_light_state_colours", "test_19_a_sensitive_item_shows_a_read_only_tag",
                  "test_15_esc_on_ai_keeps_the_words_and_re_extract_keeps_unsent_ask_text"], MV))
    def test_c88_widths_dark_and_the_small_things(self):
        """88. At 1400 px the bar is one row and at 900 px two, with the transcript beside the sheet; in dark the paper stays white with
        light state colours; a sensitive item shows a read-only tag; Esc on AI keeps the words and Re-extract keeps unsent ask text."""

    @phase2("judgement, by hand: the hand-check vault stages no minutes; open any drafted minutes (test_minutes_view_v2's fixture or "
            "a demo transcript processed in Intake) at 1400 and 900 px, light and dark")
    def test_c89_the_minutes_view_look(self):
        """89. The minutes view reads as one page: the Track column, the aligned tables, the icon bar and the transcript beside the
        sheet, light and dark, 1400 and 900 px (judgement)."""


# ══ #275 Track from Review ═══════════════════════════════════════════════════════════════════════════════════════════════════════

TR = "v26-track-from-review"
MTR = "test_minutes_track_review"


class TrackReview275(V260Case):
    """Checks 90 to 92: approving minutes from Review follows the Track column (the builder's tests, called)."""

    @needs("268", "275")
    @calls((MTR, ["test_01_approve_from_review_applies_the_track_column_and_undo_puts_the_minutes_back",
                  "test_02_approve_all_from_these_minutes_applies_the_track_column_too"], TR))
    def test_c90_approve_from_review_follows_the_track_column(self):
        """90. Approve on the minutes in Review, and Approve all from these minutes, do what Approve minutes does: the ticked item is
        registered, the crossed one leaves the minutes, neither stays in the minutes untracked; Undo puts the apply and the minutes
        back exactly."""

    @needs("268", "275")
    @calls((MTR, ["test_03_a_ticked_item_worth_a_look_opens_the_minutes_with_the_before_approving_box",
                  "test_04_the_bulk_paths_never_register_a_crossed_or_neither_row",
                  "test_05_undo_of_approve_n_routine_puts_the_crosses_back_too", "TwoProjects", "RowlessPromiseFromReview"], TR))
    def test_c91_the_bulk_paths_and_the_edges(self):
        """91. A ticked item worth a look opens the minutes with the Before approving box; Approve routine, the bar's Approve and the
        group tick never register a crossed or neither row; Undo of Approve n routine puts the crosses back; under one project of
        minutes covering several only its ticked items are registered; a promise (no row) waits in Review."""

    @needs("275")
    @offline
    def test_c92_the_server_honours_the_track_column(self):
        """92. review.py approve (the minutes or an item) and review.py bulk honour the Track column on the server; approve_minutes never
        registers a crossed item whatever it is sent; tracker.py apply refuses a crossed item approved by hand (that last part once
        the guarded tracker diff, dev/proposals/track-from-review/tracker-track-problems.diff, is in)."""
        server = [f"ServerTrack.{n}" for n in ("test_review_py_approve_on_the_minutes_honours_the_crosses",
                                               "test_review_py_approve_and_bulk_refuse_an_item_crossed_or_left_with_neither",
                                               "test_approve_minutes_never_registers_a_crossed_item_whatever_it_is_sent")]
        if has("275g", REPO, True) or FORCE:
            server.append("ServerTrack.test_apply_refuses_a_crossed_item_approved_by_hand")
        else:
            self.note(92, "PARTIAL: tracker.py's refusal waits for the guarded tracker-track-problems.diff")
        self.called(92, (MTR, server, TR))


# ══ #264 and #265: Intake's Process and Refresh as their own jobs ══════════════════════════════════════════════════════════════════

IJ = "v253-release (#264, #265)"


class IntakeJobs(V260Case):
    """Checks 93 and 94 (95 is live only). Both landed in 2.5.3 (dev/tests/handchecks/test_v253.py drives them on a stand-in Claude); here
    the builders' tests are called so the 2.6 line is proved to keep them."""

    @needs("264")
    @calls(("test_intake_process", ["Helpers", "Fence", "ThroughTheServer"], IJ), ("test_intake_process_round2", ["Round2", "Queue",
           "ProcessSelectedMeetings"], IJ), ("test_intake_process_ui", ["IntakeProcessPage"], IJ))
    def test_c93_process_is_its_own_job(self):
        """93. Intake's Process runs as its own job (progress and Stop on the row, one run at a time): the ticked files end in Review
        with no go-ahead, a question goes on its row and ask creaite opens only when asked (or when a transcript has to be loaded);
        the route takes only Intake files; the run stages only its own files and never touches the record."""

    @needs("265")
    @calls(("test_calendar_refresh", ["Helpers", "Fence", "ThroughTheServer", "SweepCalendarSave"], IJ),
           ("test_calendar_refresh_ui", ["CalendarRefreshPage"], IJ), ("test_calendar_sanitise", ["BodyAndFields", "Timing", "Sensitivity",
                                                                                                "SavedCalendar"], IJ))
    def test_c94_refresh_is_its_own_job(self):
        """94. Calendar import's Refresh reads the calendar as its own job (Stop while it works, "Calendar read…" after) and saves the
        calendar and nothing else; only the page's own request, one at a time and never during a sweep; the saved calendar keeps no
        join link, meeting key or PIN, and a confidential meeting keeps only its title and times; a bad reply never wipes it."""


# ══ #255 Delete note with no card ════════════════════════════════════════════════════════════════════════════════════════════════

DN = "v253-release (#255)"
DNC = "test_delete_note_no_card"


class DeleteNote255(V260Case):
    """Check 96, in a vault of its own (it moves a note and puts it back); 97 calls the builder's tests."""
    own_vault = True

    @needs("255")
    def test_c96_delete_note_moves_it_at_once_and_undo_brings_it_back(self):
        """96. Notes › a note's ⋯ › Delete note…, then Delete note in the box: the note moves into the project's archive folder at once,
        with no approval card and ask creaite shut; one files-log line; Undo brings back the same bytes and file date."""
        b, title = self.b, "Hand check delete"
        b.eval("go('notes','FAL')")
        b.wait("!!document.getElementById('notesNew')", 15)
        b.click("#notesNew")
        b.wait("document.getElementById('newNoteDlg').open")
        b.eval(f"(()=>{{ const i=document.getElementById('nnTitle'); i.value={json.dumps(title)}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.eval("document.querySelector('#newNoteDlg input[value=\"blank\"]').click()")
        b.click("#nnMake")
        b.wait(f"noteCur.value&&noteCur.value.note.title==={json.dumps(title)}&&!!document.querySelector('.nbody.ProseMirror')", 15)
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)
        notes = next(p for p in (self.vault / "projects").iterdir() if p.name.startswith("FAL "))
        f = notes / "notes" / f"{title}.md"
        self.assertTrue(f.is_file(), "premise: the note is on disk")
        before, mtime = f.read_bytes(), f.stat().st_mtime_ns
        b.click(".nmorewrap .nmore")
        b.wait("!!document.querySelector('.nmorewrap [role=menu] .bad')")
        b.click(".nmorewrap [role=menu] .bad")
        b.wait("document.getElementById('noteDelDlg').open")
        b.click("#ndelGo")
        b.wait("document.querySelector('.snack') && document.querySelector('.snack').textContent.includes('archive')", 20)
        self.assertEqual(b.eval("[...document.querySelectorAll('#chLog .edcard')].length"), 0, "no approval card")
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"), "ask creaite stays shut")
        self.assertFalse(f.exists(), "the note left its folder")
        moved = [x for x in (notes / "99 Archive").rglob(f"{title}*.md")] if (notes / "99 Archive").exists() else []
        self.assertEqual(len(moved), 1, "the note is in the project's 99 Archive")
        log = self.vault / "system/config/files-log.jsonl"
        lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if title in ln and "note-archive" in ln] if log.exists() else []
        self.assertEqual(len(lines), 1, "one files-log line for the delete")
        b.eval("[...document.querySelectorAll('.snack button')].find(x=>/Undo/.test(x.textContent)).click()")
        for _ in range(150):
            if f.exists():
                break
            b.pump(0.1)
        self.assertTrue(f.exists(), "Undo puts the note back")
        self.assertEqual((f.read_bytes(), f.stat().st_mtime_ns), (before, mtime), "the same bytes and file date")
        self.note(96, "moved at once into 99 Archive, no card; Undo gave back the same bytes and date")

    @needs("255")
    @calls((DNC, ["DeleteNoteNoCard", "Mutations"], DN))
    def test_c97_only_the_page_can_and_only_one_note(self):
        """97. Only the page's own call moves a note (not without the token, another Host, or a hand-staged proposal); ask creaite can't
        move, delete, stage or card one; a note changed since it was shown is refused; a taken name gets -2; Move back is direct; a
        report's Move back and a project's archive keep their card; any other shape (a folder, two files, a symlink, .., another case
        or Unicode form, a line break, a linked archive) is refused; every safeguard's mutant goes red."""


# ══ Help: the 2.6 items in plain words ═══════════════════════════════════════════════════════════════════════════════════════════

HT = "v26-help-text"
HELP_WORDS = {                     # the item: words Help must have once it is in the vault (the ** of bold taken out)
    "246": ["Tabs: Essentials"], "247": ["one scrolling page", "Archive and close"], "248": ["Everyone", "needs details"],
    "241": ["S / O / P / T", "Compact"], "183": ["Create drafts in Outlook", "Create draft in Outlook"],
    "250": ["Fetch transcripts as they appear"], "97": ["Pause alert checks overnight", "Pause alert checks on weekend days"],
    "268": ["keeps it in the minutes without tracking it", "Approve minutes"], "275": ["Approving from Review does the same"],
    "255": ["with no approval card"], "252": ["99 Archive"],
}
HELP_STALE = ["Settings › Health and warnings", "Settings › Health › Advanced", "Settings › Review's number", "makes an Outlook draft"]


class Help26(V260Case):
    """Checks 98 and 99. Reads only."""

    @needs("help")
    def test_c98_help_explains_each_26_item(self):
        """98. Help explains each 2.6 item that is in the release in plain words, where a person would look, and the old places are
        gone (Settings paths, "makes an Outlook draft")."""
        text = (self.vault / "system/templates/help.md").read_text(encoding="utf-8").replace("**", "")
        present = [i for i in HELP_WORDS if i in FEATURES and has(i, self.vault, False)]
        missing = [(i, w) for i in present for w in HELP_WORDS[i] if w not in text]
        self.assertEqual(missing, [], "Help lacks the words for an item in this release")
        stale = [w for w in HELP_STALE if w in text]
        self.assertEqual(stale, [], "Help still names an old place")
        self.note(98, f"words for {len(present)} items ({', '.join('#' + i for i in present)}) found")
        self.called(98, ("test_help", ["test_the_26_items_are_explained"], HT))

    @needs("help")
    def test_c99_help_look(self):
        """99. Help's 2.6 lines read plainly, in British English, light and dark, 1400 and 900 px (judgement)."""
        k = self.sheet(99, "help", widths=(1400, 900))
        self.note(99, f"{k} screenshots")


if __name__ == "__main__":
    unittest.main()
