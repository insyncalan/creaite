"""BL-77: the Work filters, second review, in a real browser against the real live server.

Run: python3 dev/tests/test_work_filters_live.py   (needs Google Chrome; skipped otherwise)

The first fix (BL-62) was tested by calling the page's own functions, which never noticed that a filter menu closed the
instant it opened. These tests click through the controls as a person does (real mouse clicks, the real address,
reload, Back) in a vault with about 60 actions, 30 RAID items and 12 decisions, and check every result against an
oracle written in Python (work_data.expected_ids) that shares no code with the page.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

BTN = {"o": "own", "p": "proj", "pr": "pri"}


class WorkCase(LiveBrowserCase):
    shared_server = True            # the data is read-only here

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.data = {t: cls.v.rows(t) for t in ("actions", "raid", "decisions")}
        for r in cls.data["raid"]:                                   # a RAID item's priority comes from impact and likelihood
            i, l = r["impact"], r["likelihood"]
            r["priority"] = "Urgent" if i == l == "High" else "High" if "High" in (i, l) else "Low" if i == l == "Low" else "Medium"

    def setUp(self):
        super().setUp()
        # BL-327: the shared server's data is soon older than PAGE_FRESH, so each load re-reads /api/data after its first paint,
        # and that redraw closes and replaces an open filter menu; under load it landed between opening a menu and the tick.
        self.b.wait("PULSE.reloads===0 && !PULSE.busy && !EVS.timer", 30)

    # ── driving the page as a person does ──
    def open_work(self, tab="actions", view=None):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty')")
        if tab != "actions":
            b.click(f'#wtabs button[data-t="{tab}"]')
            b.wait(f"WT==='{tab}'")
        if view:
            self.pick_view(view)
        return self

    def pick_view(self, view):
        """BL-131: a view that isn't on the chip row (Overdue on Actions, or one that doesn't fit) is under More views."""
        b = self.b
        if not b.eval(f"(()=>{{ const c=document.querySelector('#wviews .vwrap [data-wv=\"{view}\"]'); return !!(c&&c.offsetWidth); }})()"):
            b.click("#vmore")
            b.click(f'#vmoreMenu [data-wv="{view}"]')
        else:
            b.click(f'#wviews .vwrap [data-wv="{view}"]')

    def ids(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row).sort()")

    def count_text(self):
        return self.b.eval("document.getElementById('wcount').textContent")

    def chips(self):
        return self.b.eval("[...document.querySelectorAll('#wapplied .fchip')].map(c=>c.firstChild.textContent.trim())")

    def remove_all_chips(self):
        while self.b.eval("document.querySelectorAll('#wapplied .fchip button').length"):
            self.b.click("#wapplied .fchip button")

    def menu_id(self, k, more=False):
        return "moreMenu" if more else f"{BTN.get(k, k)}Menu"

    def open_menu(self, k, more=False):
        b = self.b
        mid = self.menu_id(k, more)
        if not b.eval(f"document.getElementById('{mid}').classList.contains('on')"):
            b.click("#moreBtn" if more else f"#{BTN.get(k, k)}Btn")
        b.wait(f"document.getElementById('{mid}').classList.contains('on')", 3)
        if more and b.eval(f"FPK!=={k!r}"):                                  # BL-130: "+ Filter" is a field picker; choose the field first
            b.click(f'#moreMenu [data-fpk="{k}"]')
            b.wait(f"FPK==={k!r}", 3)
        return mid

    def tick(self, k, value, more=False):
        mid = self.open_menu(k, more)
        self.b.click(f'#{mid} input[data-fk="{k}"][value={json.dumps(value)}]')

    def menu_open(self, k, more=False):
        return self.b.eval(f"document.getElementById('{self.menu_id(k, more)}').classList.contains('on')")

    def menu_counts(self, k, more=False):
        mid = self.open_menu(k, more)
        return self.b.eval(f"""Object.fromEntries([...document.querySelectorAll('#{mid} label')].filter(l=>l.querySelector('[data-fk="{k}"]'))
          .map(l=>[l.querySelector('input').value, +l.querySelector('small').textContent]))""")

    def click_away(self):
        self.b.click("#v-work h1")

    def expected(self, table="actions", **kw):
        return W.expected_ids(self.data[table], table, **kw)

    def assertShows(self, table, msg="", **kw):
        got, want = self.ids(), self.expected(table, **kw)
        self.assertEqual(got, want, f"{msg}: the page shows {len(got)}, the oracle {len(want)}")
        total = len(self.data[table])
        self.assertEqual(self.count_text(), f"Showing {len(want)} of {total}", msg)


class WorkToolbarFilters(WorkCase):
    def test_a_filter_menu_opens_stays_open_and_closes_on_a_click_elsewhere(self):
        self.open_work()
        for k in ("st", "due", "o", "p", "pr"):
            self.open_menu(k)
            self.assertTrue(self.menu_open(k), k)
            self.assertTrue(self.b.eval(f"document.getElementById('{self.menu_id(k)}').getBoundingClientRect().height")>0, k)   # and is visible
            self.b.click(f"#{BTN.get(k, k)}Btn")                                       # the same button again closes it
            self.assertFalse(self.menu_open(k), k)
        self.open_menu("st")
        self.b.click("#ownBtn")                                                        # opening another closes the first
        self.assertEqual([self.menu_open("st"), self.menu_open("o")], [False, True])
        self.click_away()
        self.assertFalse(self.menu_open("o"))
        self.assertEqual(self.b.errors, [])

    def test_each_option_of_each_toolbar_filter_shows_exactly_what_it_should(self):
        self.open_work()
        self.remove_all_chips()
        self.assertShows("actions", "no filters")
        kw = {"st": ("status", ["Open", "Delayed", "Closed", "Cancelled"]),
              "due": ("due", ["overdue", "soon", "none", "later"]),
              "o": ("owner", [o for o in W.OWNERS]),
              "p": ("project", ["ABC", "DEF"]),
              "pr": ("priority", W.PRIORITIES)}
        for k, (arg, options) in kw.items():
            for value in options:
                self.tick(k, value)
                chosen = {value}
                if k == "o" and value in ("Alan Carter", "Alan"):
                    chosen = {value}
                self.assertShows("actions", f"{k}={value}", **{arg: chosen})
                self.tick(k, value)                                                       # untick: back to everything
                self.assertShows("actions", f"{k}={value} removed")
            self.click_away()
        self.assertEqual(self.b.errors, [])

    def test_filters_combine_and_within_one_filter_they_widen(self):
        self.open_work()
        self.remove_all_chips()
        self.tick("st", "Open")
        self.tick("st", "Delayed")
        self.assertShows("actions", "two statuses", status={"Open", "Delayed"})            # within a filter: OR
        self.tick("pr", "Urgent")
        self.tick("pr", "High")
        self.assertShows("actions", "status and priority", status={"Open", "Delayed"}, priority={"Urgent", "High"})
        self.tick("p", "DEF")
        self.assertShows("actions", "and project", status={"Open", "Delayed"}, priority={"Urgent", "High"}, project={"DEF"})
        self.tick("due", "overdue")
        self.tick("due", "soon")
        self.assertShows("actions", "and due", status={"Open", "Delayed"}, priority={"Urgent", "High"}, project={"DEF"}, due={"overdue", "soon"})
        self.tick("o", "Omar Ali")
        self.tick("o", "Sara Example")
        self.assertShows("actions", "and owner", status={"Open", "Delayed"}, priority={"Urgent", "High"}, project={"DEF"},
                         due={"overdue", "soon"}, owner={"Omar Ali", "Sara Example"})

    def test_closed_items_are_never_due_and_a_closed_item_is_found_by_status(self):
        self.open_work()
        self.remove_all_chips()
        self.tick("due", "overdue")
        self.tick("due", "soon")
        self.tick("due", "later")
        shown = self.ids()
        closed = {r["id"] for r in self.data["actions"] if r["status"] in ("Closed", "Cancelled")}
        self.assertFalse(set(shown) & closed)                                              # BL-62: closed isn't overdue, soon or later
        self.assertShows("actions", "due kinds", due={"overdue", "soon", "later"})

    def test_the_owner_menu_offers_me_first_and_only_me_selects_every_spelling_of_me(self):
        self.open_work()
        self.remove_all_chips()
        mid = self.open_menu("o")
        labels = self.b.eval(f"[...document.querySelectorAll('#{mid} label')].map(l=>l.textContent.replace(/\\d+$/,''))")
        self.assertTrue(labels[0].startswith("Me"), labels)                                  # Me first
        self.b.click(f'#{mid} [data-ma="me"]')
        self.assertShows("actions", "only me", owner={"Alan Carter", "Alan"})
        self.assertEqual(self.chips(), ["Owner: Me"])
        self.assertEqual(self.b.eval("document.getElementById('ownBtn').textContent"), "Me")
        self.assertTrue(self.menu_open("o"))                                                 # still open after the choice
        self.b.click(f'#{mid} [data-ma="clear"]')
        self.assertShows("actions", "owner cleared")

    def test_select_all_and_clear_in_a_menu_use_only_what_the_search_leaves(self):
        self.open_work()
        self.remove_all_chips()
        mid = self.open_menu("o")
        self.b.click(f"#{mid} .mq")
        self.b.type("sara")
        self.assertEqual(self.b.eval(f"[...document.querySelectorAll('#{mid} label')].map(l=>l.textContent.replace(/\\d+$/,''))"), ["Sara Example"])
        self.b.click(f'#{mid} [data-ma="all"]')
        self.assertShows("actions", "select all of a searched menu", owner={"Sara Example"})   # not everyone
        self.assertEqual(self.b.eval(f"document.querySelector('#{mid} .mq').value"), "sara")        # BL-62: the search text is kept
        self.assertTrue(self.b.eval(f"document.activeElement===document.querySelector('#{mid} .mq')"))   # and so is the focus

    def test_menu_counts_match_the_rows_each_option_would_show(self):
        self.open_work()
        self.remove_all_chips()
        self.tick("pr", "Urgent")                                   # counts are given the other filters
        self.tick("p", "ABC")
        for k, arg in (("st", "status"), ("due", "due"), ("o", "owner")):
            counts = self.menu_counts(k)
            for value, n in counts.items():
                want = len(self.expected("actions", priority={"Urgent"}, project={"ABC"}, **{arg: {value}}))
                self.assertEqual(n, want, f"{k}={value}")
            self.click_away()


class WorkMoreFilters(WorkCase):
    """"+ Filter": workstream (with "No workstream"), source, client-visible, type, response, due between."""

    def test_actions_extra_filters_each_option(self):
        self.open_work()
        self.remove_all_chips()
        for k, arg, options in (("ws", "ws", ["", "Build", "Test", "Change"]), ("src", "src", ["Minutes", "Mail", "Teams", "Dashboard", "Excel", "cx-edit"]),
                                ("cv", "cv", ["yes", "no"])):
            for value in options:
                self.tick(k, value, more=True)
                self.assertShows("actions", f"{k}={value!r}", **{arg: {value}})
                self.assertTrue(self.b.eval("document.getElementById('moreMenu').classList.contains('on')"), f"{k}: the + Filter menu stays open after a tick")
                self.tick(k, value, more=True)
                self.assertShows("actions", f"{k}={value!r} removed")
        self.click_away()
        self.assertEqual(self.b.errors, [])

    def test_no_workstream_can_be_chosen_and_its_chip_says_so(self):
        self.open_work()
        self.remove_all_chips()
        self.tick("ws", "", more=True)
        self.assertEqual(self.chips(), ["Workstream: No workstream"])
        self.assertTrue(all(not r["workstream"] for r in self.data["actions"] if r["id"] in self.ids()))

    def test_due_between_takes_dates_as_shown_and_refuses_what_is_not_a_date(self):
        b = self.b
        self.open_work()
        self.remove_all_chips()
        b.click("#moreBtn")
        b.click('#moreMenu [data-fpk="dr"]')                               # BL-130: the range is a field in the picker
        lo, hi = W.d(0), W.d(7)
        b.click('#moreMenu [data-dr="from"]')
        b.type(W.shown_date(lo))
        b.key("Tab")
        b.click('#moreMenu [data-dr="to"]') if b.eval("!!document.querySelector('#moreMenu [data-dr=\"to\"]')") else None
        b.type(W.shown_date(hi))
        b.key("Tab")
        self.assertShows("actions", "due between", between=(lo, hi))
        self.assertEqual(self.chips(), [f"Due: {W.shown_date(lo)} to {W.shown_date(hi)}"])
        # not a date: refused with a message, and nothing changes
        b.eval("document.getElementById('snackT').textContent=''")
        b.click('#moreMenu [data-dr="to"]')
        b.key("A", modifiers=4)
        b.type("someday")                                                    # BL-147: 31/12/2026 and words are dates now
        b.key("Tab")
        self.assertIn("Not a date creaite knows", b.eval("document.getElementById('snackT').textContent"))
        self.assertShows("actions", "still the same range", between=(lo, hi))

    def test_raid_filters(self):
        self.open_work("raid")
        self.remove_all_chips()
        self.assertShows("raid", "no filters")
        for k, arg, options, more in (("st", "status", ["Open", "Closed", "Cancelled"], False), ("due", "due", ["overdue", "soon", "none", "later"], False),
                                      ("o", "owner", W.OWNERS, False), ("p", "project", ["ABC", "DEF"], False), ("pr", "priority", W.PRIORITIES, False),
                                      ("ty", "typ", ["Risk", "Issue", "Assumption", "Dependency"], True), ("rs", "resp", ["yes", "none"], True),
                                      ("ws", "ws", ["", "Build"], True), ("src", "src", ["Minutes", "Mail", "Teams", "Dashboard", "Excel", "cx-edit"], True),
                                      ("cv", "cv", ["yes", "no"], True)):
            for value in options:
                self.tick(k, value, more=more)
                self.assertShows("raid", f"raid {k}={value!r}", **{arg: {value}})
                self.tick(k, value, more=more)
            self.click_away()

    def test_decisions_filters(self):
        self.open_work("decisions")
        self.remove_all_chips()
        self.assertShows("decisions", "no filters")
        for k, arg, options in (("o", "owner", W.OWNERS), ("p", "project", ["ABC", "DEF"]), ("cv", "cv", ["yes", "no"]),
                                ("src", "src", ["Minutes", "Mail", "Teams", "Dashboard", "Excel", "cx-edit"])):
            for value in options:
                self.tick(k, value, more=(k == "src"))
                self.assertShows("decisions", f"decisions {k}={value!r}", **{arg: {value}})
                self.tick(k, value, more=(k == "src"))
            self.click_away()
        for n in ("7", "14", "30"):                                         # BL-62: "last N days" excludes the future
            self.tick("dt", n)
            self.assertShows("decisions", f"last {n} days", last_days={int(n)})
            self.tick("dt", n)


class WorkSearchChipsAndViews(WorkCase):
    def search(self, text):
        b = self.b
        b.click("#workQ")
        b.eval("document.getElementById('workQ').select()")
        b.type(text) if text else b.key("Backspace")

    def test_search_matches_every_word_in_any_order_in_ids_text_owner_project_and_dates_as_shown(self):
        self.open_work()
        self.remove_all_chips()
        for q in ("alpha", "beta number", "NUMBER 07", "abc-a-0", "sara", "digital enablement", W.shown_date(W.d(-3)), "zzzz"):
            self.search(q)
            self.b.wait("true", 1)
            got = self.ids()
            want = self.expected("actions", query=q)
            self.assertEqual(got, want, f"search {q!r}")
        self.search("zzzz")
        self.assertIn("Nothing in this view matches", self.b.eval("document.querySelector('#workTbl .empty').textContent"))
        self.assertEqual(self.chips(), ["Search: “zzzz”"])

    def test_search_combines_with_filters_and_its_chip_clears_it(self):
        self.open_work()
        self.remove_all_chips()
        self.tick("p", "DEF")
        self.click_away()
        self.search("alpha")
        self.assertEqual(self.ids(), self.expected("actions", project={"DEF"}, query="alpha"))
        self.b.click('#wapplied [data-clr="q"]')
        self.assertEqual(self.ids(), self.expected("actions", project={"DEF"}))
        self.assertEqual(self.b.eval("document.getElementById('workQ').value"), "")

    def test_the_slash_key_opens_ask_creaite_even_on_work(self):
        # "/" is always ask creaite, on every page (Alan, 2026-10-09); Work's search is clicked instead
        self.open_work()
        self.b.click("#v-work h1")
        self.b.key("/")
        self.assertFalse(self.b.eval("document.activeElement.id==='workQ'"))
        self.assertTrue(self.b.eval("document.getElementById('chat').classList.contains('on')"))

    def test_each_chip_removes_only_its_own_filter(self):
        self.open_work()
        self.remove_all_chips()
        self.tick("st", "Open")
        self.tick("pr", "Urgent")
        self.tick("p", "ABC")
        self.click_away()
        self.assertEqual(len(self.chips()), 3)
        self.b.click('#wapplied [data-clr="pr"]')
        self.assertShows("actions", "priority chip removed", status={"Open"}, project={"ABC"})
        self.b.click('#wapplied [data-clr="st"]')
        self.assertShows("actions", "status chip removed", project={"ABC"})
        self.assertEqual(self.b.eval("document.getElementById('projBtn').textContent"), "Example Programme")      # the name (BL-101)

    def test_clear_all_returns_to_all_open_with_no_search_and_no_project(self):
        self.open_work()
        self.remove_all_chips()
        self.tick("pr", "Low")
        self.tick("p", "DEF")
        self.click_away()
        self.search("alpha")
        self.b.click("#clearF")
        self.assertShows("actions", "after Clear all", status={"Open"})            # All open is Open only (Alan, 11-10-2026)
        self.assertEqual([self.b.eval("WVIEW"), self.b.eval("document.getElementById('workQ').value")], ["open", ""])
        self.assertEqual(self.b.eval("document.getElementById('projBtn').textContent"), "All projects")

    def test_clear_all_lands_on_all_open_even_when_the_tab_opens_on_another_view(self):
        b = self.b
        b.eval("S.defActionView='overdue'")                                         # Settings › Opening views: Overdue
        try:
            self.open_work(view="overdue")
            self.tick("pr", "Urgent")
            self.click_away()
            b.click("#clearF")
            self.assertEqual(b.eval("WVIEW"), "open")                              # the first view, not the opening one
            self.assertShows("actions", "after Clear all", status={"Open"})
            self.assertEqual(b.eval("document.querySelector('#wviews [data-wv=\"open\"]').getAttribute('aria-pressed')"), "true")
        finally:
            b.eval("S.defActionView='open'")

    def test_the_delayed_view_lists_only_delayed_actions_and_all_open_none(self):
        self.open_work()
        self.pick_view("delayed")
        self.assertShows("actions", "actions/delayed", status={"Delayed"})
        delayed = self.ids()
        self.assertTrue(delayed, "the sample has delayed actions")
        self.assertEqual(set(self.b.eval("rows().map(x=>x.st)")), {"Delayed"})
        self.pick_view("open")
        self.assertFalse(set(delayed) & set(self.ids()), "All open lists no delayed action")

    def test_every_built_in_view_shows_what_its_name_says(self):
        me = {"Alan Carter", "Alan"}
        views = {"actions": {"open": dict(status={"Open"}), "mine": dict(status={"Open"}, owner=me),          # Open only (Alan, 11-10-2026)
                             "soon": dict(status={"Open"}, due={"soon"}), "overdue": dict(status={"Open", "Delayed"}, due={"overdue"}),
                             "delayed": dict(status={"Delayed"}), "closed": dict(status={"Closed", "Cancelled"})},
                 "raid": {"open": dict(status={"Open"}), "urgent": dict(status={"Open"}, priority={"Urgent", "High"}),
                          "nomit": dict(status={"Open"}, resp={"none"}), "soon": dict(status={"Open"}, due={"soon"}),
                          "mine": dict(status={"Open"}, owner=me), "closed": dict(status={"Closed", "Cancelled"})},
                 "decisions": {"all": {}, "recent": dict(last_days={14}), "client": dict(cv={"yes"})}}
        for tab, vs in views.items():
            self.open_work(tab)
            for view, kw in vs.items():
                self.pick_view(view)
                self.assertShows(tab, f"{tab}/{view}", **kw)
                self.assertEqual(self.b.eval(f"document.querySelector('#wviews [data-wv=\"{view}\"]').getAttribute('aria-pressed')"), "true")

    def test_changing_a_filter_off_a_view_marks_it_changed_and_back_on_it_says_the_view(self):
        self.open_work(view="overdue")
        self.tick("pr", "Urgent")
        self.click_away()
        self.assertEqual(self.b.eval("[WVIEW, !!document.querySelector('#wviews [data-wv=\"overdue\"] .vdot')]"), [None, True])   # BL-131: the dot, not "Custom"
        self.b.click('#wapplied [data-clr="pr"]')
        self.assertEqual(self.b.eval("[WVIEW, !!document.querySelector('#wviews .vdot'), !!document.querySelector('#wviews .custom')]"), ["overdue", False, False])

    def test_each_tab_keeps_its_own_filters(self):
        self.open_work()
        self.remove_all_chips()
        self.tick("pr", "Urgent")
        self.click_away()
        self.b.click('#wtabs button[data-t="raid"]')
        self.assertShows("raid", "raid has its own default", status={"Open"})
        self.tick("ty", "Risk", more=True)
        self.click_away()
        self.b.click('#wtabs button[data-t="actions"]')
        self.assertShows("actions", "actions kept its filter", priority={"Urgent"})
        self.b.click('#wtabs button[data-t="raid"]')
        self.assertShows("raid", "raid kept its filter", status={"Open"}, typ={"Risk"})

    def test_save_a_view_it_is_kept_in_settings_and_can_be_deleted(self):
        b = self.b
        self.open_work()
        self.remove_all_chips()
        self.tick("pr", "Urgent")
        self.tick("p", "DEF")
        self.click_away()
        b.click("#saveView")
        b.click("#viewName")
        b.type("Urgent on DEF")
        b.click("#viewSave")
        b.wait("document.querySelector('#wviews [data-wv=\"saved:Urgent on DEF\"]')", 5)
        self.assertEqual(b.eval("WVIEW"), "saved:Urgent on DEF")
        saved = json.loads((self.v.root / "system/config/settings.json").read_text())["work"]["saved_views"]["actions"]
        self.assertEqual([x["name"] for x in saved], ["Urgent on DEF"])
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        self.open_work()
        b.click('#wviews [data-wv="saved:Urgent on DEF"]')
        self.assertShows("actions", "the saved view after a reload", priority={"Urgent"}, project={"DEF"})
        b.click('#wviews [data-vmenu="Urgent on DEF"]')                  # BL-131: delete is in the view's menu
        b.click('#vmenuPop [data-vm="delete"]')
        b.wait("!document.querySelector('#wviews [data-wv=\"saved:Urgent on DEF\"]')", 5)
        saved = json.loads((self.v.root / "system/config/settings.json").read_text())["work"]["saved_views"]["actions"]
        self.assertEqual(saved, [])


class WorkAddressAndHistory(WorkCase):
    """Back, forward, refresh and a copied address bring back the same filters."""

    def state(self):
        return self.b.eval("[WT, WVIEW, [...PROJF].sort(), WQ, snapshot(), SORT[WT]||null]")

    def reopen_address(self):
        """What pasting the address in a new tab does: load the page afresh at the current address."""
        url = self.b.eval("location.href")
        self.b.goto("about:blank")
        self.b.goto(url)
        self.b.wait("typeof go==='function' && LIVE")
        self.b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty')")

    def test_refresh_and_a_copied_address_restore_the_filters(self):
        scenarios = {
            "a view": lambda: self.pick_view("overdue"),
            "custom filters": lambda: (self.remove_all_chips(), self.tick("pr", "Urgent"), self.tick("pr", "High"), self.tick("p", "DEF"), self.click_away()),
            "no filters at all": lambda: self.remove_all_chips(),
            "closed items": lambda: self.b.click('#wviews [data-wv="closed"]'),
            "a search": lambda: (self.b.click("#workQ"), self.b.type("alpha")),
            "extra filters and a range": lambda: (self.remove_all_chips(), self.tick("ws", "", more=True), self.tick("cv", "yes", more=True), self.click_away()),
        }
        for name, act in scenarios.items():
            with self.subTest(name):
                self.open_work()
                self.b.click('#wviews [data-wv="open"]')
                act()
                before, rows = self.state(), self.ids()
                self.b.reload()
                self.b.wait("typeof go==='function' && LIVE")
                self.b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty')")
                self.assertEqual(self.state(), before, f"{name}: the state after a refresh")
                self.assertEqual(self.ids(), rows, f"{name}: the rows after a refresh")
                self.reopen_address()
                self.assertEqual(self.ids(), rows, f"{name}: the rows from a copied address")

    def test_each_tab_is_in_the_address_and_comes_back(self):
        for tab in ("raid", "decisions"):
            self.open_work(tab)
            self.assertIn(f"work={tab}", self.b.eval("location.hash"))
            rows = self.ids()
            self.reopen_address()
            self.assertEqual(self.b.eval("WT"), tab)
            self.assertEqual(self.ids(), rows)

    def test_back_and_forward_bring_the_filters_back(self):
        b = self.b
        self.open_work()
        self.remove_all_chips()
        self.tick("pr", "Urgent")
        self.click_away()
        rows = self.ids()
        b.eval("go('today')")
        b.wait("!document.getElementById('v-today').hidden")
        b.eval("history.back()")
        b.wait("VIEW==='work'")
        self.assertEqual(self.ids(), rows)
        b.eval("history.forward()")
        b.wait("VIEW==='today'")
        b.eval("history.back()")
        b.wait("VIEW==='work'")
        self.assertEqual(self.ids(), rows)

    def test_a_sorted_list_is_sorted_the_same_after_a_refresh(self):
        b = self.b
        self.open_work()
        b.click('#workTbl th[data-col="due"]')
        order = b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)")
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        b.wait("document.querySelector('#workTbl tbody tr')")
        self.assertEqual(b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)"), order)


class WorkSorting(WorkCase):
    def order(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)")

    def test_a_header_sorts_then_reverses_then_returns_to_the_default(self):
        b = self.b
        self.open_work()
        default = self.order()
        due = {r["id"]: r["due_date"] or "9999" for r in self.data["actions"]}
        b.click('#workTbl th[data-col="due"]')
        asc = self.order()
        self.assertEqual([due[i] for i in asc], sorted(due[i] for i in asc))
        b.click('#workTbl th[data-col="due"]')
        self.assertEqual([due[i] for i in self.order()], sorted((due[i] for i in asc), reverse=True))
        b.click('#workTbl th[data-col="due"]')
        self.assertEqual(self.order(), default)
        self.assertEqual(sorted(self.order()), sorted(default))


class WorkLinksIntoWork(WorkCase):
    """A link from a project page, Today or a person opens Work with exactly the filter it claims, and the same count."""

    def work_rows(self):
        self.b.wait("VIEW==='work'||VIEW==='mine'")
        self.b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty')")
        return self.ids()

    def test_the_project_pages_figures_open_work_with_the_same_count(self):
        b = self.b
        for code in ("ABC", "DEF"):
            b.eval(f"go('cockpit','{code}')")
            b.wait("document.querySelector('#v-cockpit .evbox')")
            n = b.eval("document.querySelectorAll('#v-cockpit .evbox[data-nav]').length")
            for i in range(n):
                b.eval(f"go('cockpit','{code}')")
                b.wait("document.querySelector('#v-cockpit .evbox')")
                label = b.eval(f"document.querySelectorAll('#v-cockpit .evbox[data-nav]')[{i}].querySelector('.l').textContent")
                shown = int(b.eval(f"document.querySelectorAll('#v-cockpit .evbox[data-nav]')[{i}].querySelector('.v').textContent"))
                b.eval(f"document.querySelectorAll('#v-cockpit .evbox[data-nav]')[{i}].scrollIntoView({{block:'center'}})")
                pos = b.eval(f"(()=>{{ const r=document.querySelectorAll('#v-cockpit .evbox[data-nav]')[{i}].getBoundingClientRect(); return [r.left+r.width/2, r.top+r.height/2]; }})()")
                for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
                    b.call("Input.dispatchMouseEvent", type=kind, x=pos[0], y=pos[1], button="left", clickCount=1)
                self.assertEqual(len(self.work_rows()), shown, f"{code} {label}: the figure says {shown}")

    def test_the_project_pages_all_n_links_and_headings_open_work_with_that_many(self):
        b = self.b
        checked = 0
        for code in ("ABC", "DEF"):
            b.eval(f"go('cockpit','{code}')")
            b.wait("document.querySelector('#v-cockpit .evbox')")
            n = b.eval("document.querySelectorAll('#v-cockpit a[data-nav]').length")
            for i in range(n):
                b.eval(f"go('cockpit','{code}')")
                b.wait("document.querySelector('#v-cockpit .evbox')")
                info = b.eval(f"""(()=>{{ const a=document.querySelectorAll('#v-cockpit a[data-nav]')[{i}]; a.scrollIntoView({{block:'center'}}); const r=a.getBoundingClientRect(), h=a.closest('h2');
                  return {{text:a.textContent.trim(), nav:a.dataset.nav, x:r.left+r.width/2, y:r.top+r.height/2, count:h?+((h.textContent.match(/·\\s*(\\d+)/)||[])[1]||-1):-1}}; }})()""")
                for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
                    b.call("Input.dispatchMouseEvent", type=kind, x=info["x"], y=info["y"], button="left", clickCount=1)
                rows = len(self.work_rows())
                import re
                m = re.match(r"All (\d+) ", info["text"])
                if m:
                    self.assertEqual(rows, int(m.group(1)), f"{code}: {info['text']} ({info['nav']})")
                    checked += 1
                elif info["count"] >= 0:
                    self.assertEqual(rows, info["count"], f"{code}: the heading {info['text']!r} says {info['count']} ({info['nav']})")
                    checked += 1
        self.assertGreater(checked, 4)

    def test_all_mine_on_today_shows_my_commitments_and_nothing_left_over_from_before(self):
        b = self.b
        self.open_work()
        self.remove_all_chips()
        self.tick("p", "DEF")
        self.click_away()
        b.click("#workQ")
        b.type("alpha")
        b.eval("go('today')")
        b.wait("!document.getElementById('v-today').hidden")
        b.click('#hMine a[data-go="mine"]')
        rows = self.work_rows()
        mine = self.expected("actions", status={"Open"}, owner={"Alan Carter", "Alan"})
        self.assertEqual(rows, mine, "All mine shows my open actions, whatever Work was left filtered to")
        self.assertEqual(self.chips(), ["Status: Open", "Owner: Me"])

    def test_the_person_pages_see_all_link_lists_that_persons_open_items_and_says_so(self):
        b = self.b
        b.eval("go('person','Sara Example')")
        b.wait("document.querySelector('#v-person [data-seeall=\"actions\"]')")
        open_n = b.eval("document.querySelectorAll('#v-person .ppcard')[0] ? 1 : 0")
        b.click('#v-person [data-seeall="actions"]')
        rows = self.work_rows()
        self.assertEqual(rows, self.expected("actions", status={"Open", "Delayed"}, owner={"Sara Example"}))
        self.assertIn("Owner: Sara Example", self.chips())


class FilesFilters(LiveBrowserCase):
    """The Files list: the tree, the quick views, the name box, the type, From and To, all against the folders on disk."""

    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        root = v.root / "projects"
        abc, defn = next(root.glob("ABC *")), next(root.glob("DEF *"))
        spec = {abc: {"minutes": ["Steering", "Kickoff"], "transcripts": ["Steering", "Kickoff"], "reports": ["Weekly report", "Client report"],
                      "documents": ["Plan", "Budget"]},
                defn: {"minutes": ["Pilot"], "transcripts": ["Pilot"], "reports": ["Weekly report"], "documents/Commercial": ["SOW", "Budget"]}}
        types = ["docx", "pdf", "vtt", "xlsx", "md", "txt"]
        n = 0
        for folder, kinds in spec.items():
            for kind, names in kinds.items():
                for name in names:
                    for k, ago in enumerate((1, 9, 40)):
                        n += 1
                        f = folder / kind / f"{W.d(-ago)} {name} {k}.{types[n % len(types)]}"
                        f.parent.mkdir(parents=True, exist_ok=True)
                        f.write_bytes(b"x" * (n * 300))
        (v.root / "inbox" / f"{W.d(-2)} Weekly sync.vtt").write_bytes(b"WEBVTT")
        (v.root / "projects/_portfolio/minutes").mkdir(parents=True, exist_ok=True)
        (v.root / "projects/_portfolio/minutes" / f"{W.d(0)} Portfolio review.docx").write_bytes(b"x")
        cfg = v.root / "system/config/settings.json"                 # BL-87: documents are set aside by default; these tests cover them too
        data = json.loads(cfg.read_text())
        data["dashboard"]["files_show_documents"] = True
        cfg.write_text(json.dumps(data, indent=2))
        v.run(script="build_dashboard.py")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.files = []
        root = cls.v.root
        import re
        def add(p, kind, f, sub=""):
            if f.name.startswith((".", "~$")) or not f.is_file():
                return
            m = re.match(r"\d{4}-\d{2}-\d{2}", f.name)
            cls.files.append({"p": p, "f": kind, "n": f.name, "sub": sub, "type": f.suffix.lstrip(".").lower(), "date": m.group() if m else "",
                              "path": str(f.relative_to(root))})
        for folder in sorted((root / "projects").iterdir()):
            code = folder.name.split()[0]
            if code == "_portfolio":
                for kind in ("minutes", "transcripts"):
                    for f in sorted((folder / kind).rglob("*")):
                        add("_portfolio", kind, f)
                continue
            for kind in ("minutes", "transcripts", "documents", "reports"):
                for f in sorted((folder / kind).rglob("*")) if (folder / kind).is_dir() else []:
                    rel = f.relative_to(folder / kind).parts
                    add(code, kind, f, " › ".join(rel[:-1]) if kind == "documents" else "Weekly" if kind == "reports" else "")   # BL-87: a report's folder
        for f in sorted((root / "inbox").iterdir()):
            add("inbox", "", f)

    def open_files(self):
        self.b.eval("go('files')")
        self.b.wait("document.querySelector('#filesTbl tbody tr')")

    def shown(self):
        return sorted(self.b.eval("[...document.querySelectorAll('#filesTbl a[data-openfile]')].map(a=>a.dataset.openfile)"))

    def want(self, p="All", f="All", sub="", name="", typ="All", frm="", to=""):
        out = [x["path"] for x in self.files if (p == "All" or x["p"] == p) and (f == "All" or x["f"] == f) and (not sub or x["sub"] == sub)
               and (not name or name.lower() in x["n"].lower()) and (typ == "All" or x["type"] == typ) and (not frm or x["date"] >= frm) and (not to or x["date"] <= to)]
        return sorted(out)

    def test_every_tree_node_shows_what_is_in_that_folder_and_its_count_is_right(self):
        b = self.b
        self.open_files()
        for code in ("ABC", "DEF"):
            b.click(f'#tree button[data-p="{code}"][data-f="All"]')
        nodes = b.eval("[...document.querySelectorAll('#tree button')].map(x=>[x.dataset.p,x.dataset.f,x.dataset.s||'',+x.querySelector('.n').textContent])")
        self.assertGreater(len(nodes), 8)
        for p, f, sub, n in nodes:
            sel = f'#tree button[data-p="{p}"][data-f="{f}"]' + (f'[data-s="{sub}"]' if sub else ":not([data-s])")
            b.click(sel)
            want = self.want(p=p, f=f, sub=sub)
            self.assertEqual(self.shown(), want, f"{p}/{f}/{sub}")
            self.assertEqual(n, len(want), f"the count shown beside {p}/{f}/{sub}")
            for c in ("ABC", "DEF"):                                         # clicking a tree node may have collapsed the other
                if not b.eval(f"!!document.querySelector('#tree button[data-p=\"{c}\"][data-f=\"minutes\"]')"):
                    b.click(f'#tree button[data-p="{c}"][data-f="All"]')

    def test_the_quick_views(self):
        b = self.b
        self.open_files()
        b.click('#tree button[data-p="inbox"]')                        # #192: Intake is a folder in the tree, once
        self.assertEqual(self.shown(), self.want(p="inbox"))
        b.click('#fquick [data-q="all"]')
        self.assertEqual(self.shown(), self.want())
        b.click('#fquick [data-q="week"]')
        monday = (W.TODAY - W.timedelta(days=W.TODAY.weekday())).isoformat()
        self.assertEqual(self.shown(), sorted(x["path"] for x in self.files if x["f"] in ("minutes", "transcripts") and x["date"] >= monday))
        b.click('#fquick [data-q="latest"]')
        latest = []
        for code in ("ABC", "DEF"):                                   # BL-87: the newest in each report folder, not by file name
            for folder in ("Weekly", "Adhoc", "Steerco"):
                c = sorted((x for x in self.files if x["p"] == code and x["f"] == "reports" and x["sub"] == folder), key=lambda x: x["date"], reverse=True)
                if c:
                    latest.append(c[0]["path"])
        self.assertEqual(self.shown(), sorted(latest))

    def test_name_type_and_dates_filter_alone_and_together_with_the_tree(self):
        b = self.b
        self.open_files()
        b.click("#fmBtn")                              # #192: Type and the dates are in the Filter menu
        for t in ("docx", "pdf", "vtt", "xlsx"):
            b.click(f"#fmenu input[name=fsType][value={t}]")
            self.assertEqual(self.shown(), self.want(typ=t), t)
        b.click("#fmenu input[name=fsType][value=All]")
        lo, hi = W.d(-12), W.d(-1)
        b.click("#fsFrom")
        b.type(W.shown_date(lo))
        self.assertEqual(self.shown(), self.want(frm=lo))
        b.click("#fsTo")
        b.type(W.shown_date(hi))
        self.assertEqual(self.shown(), self.want(frm=lo, to=hi))
        b.click('#tree button[data-p="ABC"][data-f="All"]')
        self.assertEqual(self.shown(), self.want(p="ABC", frm=lo, to=hi))
        b.click('#fquick [data-q="all"]')              # a pill replaces the folder; the filter stays
        self.assertEqual(self.shown(), self.want(frm=lo, to=hi))

    def test_the_from_and_to_calendars_set_the_range(self):
        b = self.b
        self.open_files()
        b.click("#fmBtn")
        b.click('[data-cal="fsFrom"]')
        b.wait("document.querySelector('.cal .cg button:not(.off):not([disabled])')", 3)
        pick = b.eval("""(()=>{ const days=[...document.querySelectorAll('.cal .cg button')].filter(x=>x.getAttribute('aria-label')); const d=days.find(x=>!x.disabled&&!x.classList.contains('off')&&x.textContent.trim()==='1'); return d?d.getAttribute('aria-label'):null; })()""")
        self.assertTrue(pick)
        b.eval(f"""[...document.querySelectorAll('.cal .cg button')].find(x=>x.getAttribute('aria-label')==={json.dumps(pick)}).scrollIntoView()""")
        b.click(f'.cal .cg button[aria-label={json.dumps(pick)}]')
        frm = b.eval("document.getElementById('fsFrom').value")
        self.assertRegex(frm, r"^\d{2}-\d{2}-\d{4}$")
        iso = f"{frm[6:]}-{frm[3:5]}-{frm[:2]}"
        self.assertEqual(self.shown(), self.want(frm=iso))


class PeopleList(WorkCase):
    """People: the counts are the open items each person owns, and the headers sort (you first, always)."""

    def table(self):
        return self.b.eval("""(()=>{ const col=k=>[...document.querySelectorAll('#peopleTbl thead th')].findIndex(th=>th.dataset.psort===k);   /* by heading: BL-138 added Decisions waiting */
          return [...document.querySelectorAll('#peopleTbl tbody tr')].map(r=>{ const t=[...r.children].map(c=>c.textContent.trim()), v=k=>t[col(k)]==='—'?0:+t[col(k)];
          return {name:r.dataset.pp, oa:v('oa'), or:v('or'), late:v('late')}; }); })()""")

    def test_the_counts_are_the_open_items_each_person_owns(self):
        self.b.eval("go('people')")
        self.b.wait("document.querySelector('#peopleTbl tbody tr')")
        rows = {r["name"]: r for r in self.table()}
        for owner in ("Sara Example", "Omar Ali", "Jane Doe", "Priya Nair"):
            if owner not in rows:
                continue
            oa = [r for r in self.data["actions"] if r["owner"] == owner and r["status"] == "Open"]      # Open actions: Open only, as All open
            orr = [r for r in self.data["raid"] if r["owner"] == owner and r["status"] == "Open"]
            od = [r for r in self.data["actions"] if r["owner"] == owner and r["status"] in ("Open", "Delayed")]   # Overdue keeps Delayed
            late = [r for r in od if r["due_date"] and r["due_date"] < W.TODAY.isoformat()] + \
                   [r for r in orr if r["due_date"] and r["due_date"] < W.TODAY.isoformat()]
            self.assertEqual((rows[owner]["oa"], rows[owner]["or"], rows[owner]["late"]), (len(oa), len(orr), len(late)), owner)

    def test_each_header_sorts_and_reverses_with_you_always_first(self):
        b = self.b
        b.eval("go('people')")
        b.wait("document.querySelector('#peopleTbl tbody tr')")
        for col, key in (("oa", "oa"), ("or", "or"), ("late", "late")):
            b.click(f'#peopleTbl th[data-psort="{col}"]')
            vals = [r[key] for r in self.table()][1:]                     # the first row is you
            first = vals[:]
            b.click(f'#peopleTbl th[data-psort="{col}"]')
            vals2 = [r[key] for r in self.table()][1:]
            self.assertEqual(sorted(first, reverse=True), first, col)         # a number sorts high to low first
            self.assertEqual(sorted(vals2), vals2, col)                       # and low to high when pressed again
        b.click('#peopleTbl th[data-psort="name"]')
        names = [r["name"] for r in self.table()][1:]
        self.assertEqual(names, sorted(names, key=str.lower))
        self.assertTrue(self.b.eval("isMe(document.querySelector('#peopleTbl tbody tr').dataset.pp)"))


if __name__ == "__main__":
    unittest.main()
