"""creaite 2.6.0's hand checks (dev/handchecks/v2.6.0.md: the Product Manager's draft of 19-10-2026 numbers 1 to 27; Team Stark's
scaffolding adds 28 to 63), automated against a vault made from this checkout's release zip. Every check names the 2.6 item it
needs (@needs); while that item is not in the vault (or, for a check that only calls tests, the checkout) the check SKIPS with the
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

Adding a check is one small function in its item's class:
  @needs("<item>")                       the item it waits for (FEATURES; a new item is one entry there)
  def test_cNN_<words>(self):            NN the sheet's number
      \"\"\"NN. the check's words\"\"\"
      ...assertions on the hand-check vault (self.b, self.vault, self.py), then optionally self.called(NN, *CALLS)
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
                                     *range(53, 57), *range(58, 63))},
        **{n: "measurable" for n in (23, 24, 25)},
        **{n: "judgement" for n in (10, 11, 38, 45, 52, 57)}}
LIVE_ONLY = {
    27: "with Alan, after release: turn on Create drafts in Outlook, draft a chase with an overdue date, a table and a project heading, "
        "open the draft in Outlook: colours, table and heading survive, subject and body match the Copy version; a person with no email "
        "still gets the draft with nothing in To (Jarvis asked for it; nothing here may call Microsoft 365)",
    39: "the Outlook access Check against a real mailbox (one that can write drafts, and one that cannot); the app side is check 29",
    63: "a real sweep with the setting on fetches a real ended meeting's transcript once, and Intake shows it Transcript ready",
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
    "248": ("#248 People page v2", [("dashboard.html", r"ptabsHost[\s\S]{0,600}?Everyone")]),
    "250": ("#250 fetch transcripts (v26-fetch-transcripts)", [("system/scripts/settings_catalogue.py", r"sweep\.fetch_transcripts")]),
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
                                 "test_people_and_projects_open_only_from_their_old_addresses_with_no_tab_chosen"], ST))

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
        self.assertEqual(self.texts("#v-people [role=tab]")[:4], ["Everyone", "With work", "Nothing assigned", "Needs attention"])
        self.assertIn("Add a person", self.b.eval("document.getElementById('v-people').innerText"))

    @needs("248")
    def test_c54_the_columns(self):
        """54. Its columns are Name, Email, Organisation, Role, Projects, Actions, RAID, Decisions, Overdue (the counts open in Work)."""
        self.open_people()
        heads = [h for h in self.texts("#v-people thead th") if h]
        self.assertEqual(heads[:9], ["Name", "Email", "Organisation", "Role", "Projects", "Actions", "RAID", "Decisions", "Overdue"])

    @needs("248")
    def test_c55_nothing_that_must_not_be_there(self):
        """55. No star or "Followed" for followed people, no merge or Fix spellings, no "Press ? for help" banner, no "Add to register"
        or "not in the register"."""
        self.open_people()
        b = self.b
        txt = b.eval("document.getElementById('v-people').innerText")
        for word in ("Followed", "VIP", "Fix spellings", "Merge", "Press ? for help", "Add to register", "not in the register"):
            self.assertNotIn(word, txt)
        self.assertEqual(b.eval("document.querySelectorAll('#v-people .pstar,#v-people [aria-label=Followed]').length"), 0)

    @needs("248")
    def test_c56_needs_details(self):
        """56. A person whose record lacks an email, organisation or role shows "needs details" (the missing parts in a tooltip) and an
        Add details button that opens the edit form; Needs attention filters No email, No organisation, No role."""
        self.open_people()
        b = self.b
        tips = b.eval("[...document.querySelectorAll('#v-people [data-needs]')].map(e=>e.title||e.dataset.tip||'')")
        self.assertTrue(tips, "premise: a demo person with something missing")
        for t in tips:
            self.assertTrue(t.startswith("Missing: "), t)
        self.assertTrue(b.eval("[...document.querySelectorAll('#v-people button')].some(x=>x.textContent.trim()==='Add details')"))

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
        b.eval("go('settings','transcripts')")
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


if __name__ == "__main__":
    unittest.main()
