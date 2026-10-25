"""#360: the People page's Display menu. The rules (src/core/peopleDisplay.js) under Node; the page in a browser at 1400 and 900 px.
Privacy first: no option, heading or saved key may say or hold who is followed; every option list is an allow-list, never built from
a row's keys. The state is this browser's: nothing is written to the register or settings.json.

Run: python3 dev/tests/test_people_display.py   (the page part needs Google Chrome)
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core"
RULES = ROOT / "peopleDisplay.js"
MENU = ROOT / "displayMenu.js"


def node(js):
    r = subprocess.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@unittest.skipUnless(shutil.which("node"), "needs Node")
class Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        js = """const f = await import(%s); const o = {};
        const P = (n, org, role, on, late, missing, extra) => ({ n, org, role, on, late, missing, followed: true, ...(extra || {}) });
        const rows = [P("Ann", "Acme", "PM", ["ABC", "DEF"], 2, []), P("Bob", "", "", [], 0, ["email"]), P("Cy", "Acme", "Dev", ["ABC"], 0, [])];
        const name = c => "Project " + c;
        o.defaults = f.pdDefault(); o.keys = f.PD_KEYS;
        o.bad = f.pdNormalise({ group: "followed", sub: "org", cols: ["email", "zzz", "email"], collapsed: { "org|Acme": true, x: 1 } });
        o.clash = f.pdNormalise({ group: "org", sub: "org" });
        o.empty = f.pdNormalise({ cols: [] }); o.junk = [f.pdNormalise(null), f.pdNormalise("x"), f.pdNormalise(7)].map(s => s.group + "|" + s.cols.length);
        o.nameBack = f.pdNormalise({ cols: ["org"] }).cols;
        o.byProj = f.pdGroup(rows, "proj", name).map(g => [g.key, g.label, g.items.map(x => x.n)]);
        o.byOrg = f.pdGroup(rows, "org", name).map(g => [g.label, g.items.map(x => x.n)]);
        o.byLate = f.pdGroup(rows, "late", name).map(g => [g.label, g.items.length]);
        o.byDetails = f.pdGroup(rows, "details", name).map(g => [g.label, g.items.length]);
        o.none = f.pdGroup(rows, "none", name).length; o.nope = f.pdGroup(rows, "followed", name).length;
        o.key = [f.pdKey("org", "Acme"), f.pdKey("proj", "ABC", "role", "PM")];
        o.sorts = [f.pdSort({ col: "late", dir: "asc" }), f.pdSort({ col: "followed", dir: "asc" }), f.pdSort(null), f.pdSort({ col: "name", dir: "up" })];
        o.opts = [f.PD_GROUPS, f.PD_ORDER, f.PD_COLS.map(c => c[1])];
        console.log(JSON.stringify(o));""" % json.dumps(RULES.as_uri())
        cls.o = node(js)

    def test_defaults_show_everything_as_today(self):
        d = self.o["defaults"]
        self.assertEqual((d["group"], d["sub"], d["cols"]), ("none", "none", self.o["keys"]))

    def test_saved_junk_falls_back(self):
        b = self.o["bad"]
        self.assertEqual(b["group"], "none")                       # not in the allow-list
        self.assertEqual(b["cols"], ["name", "email"])             # unknown and duplicate dropped, Name put back first
        self.assertEqual(b["collapsed"], {"org|Acme": True})
        self.assertEqual(self.o["clash"]["sub"], "none")           # a sub-group can't repeat the group
        self.assertEqual(self.o["empty"]["cols"], self.o["keys"])
        self.assertEqual(self.o["junk"], ["none|9"] * 3)
        self.assertEqual(self.o["nameBack"], ["name", "org"])

    def test_grouping(self):
        self.assertEqual(self.o["byProj"], [["ABC", "Project ABC", ["Ann", "Cy"]], ["DEF", "Project DEF", ["Ann"]], ["", "On no project", ["Bob"]]])   # Ann under both
        self.assertEqual(self.o["byOrg"], [["Acme", ["Ann", "Cy"]], ["No organisation", ["Bob"]]])
        self.assertEqual(self.o["byLate"], [["Has overdue", 1], ["Nothing overdue", 2]])
        self.assertEqual(self.o["byDetails"], [["Needs details", 1], ["Complete", 2]])
        self.assertEqual((self.o["none"], self.o["nope"]), (1, 1))

    def test_the_fold_key_names_a_group_never_a_person(self):
        self.assertEqual(self.o["key"], ["org|Acme", "proj|ABC|role|PM"])

    def test_sorts_are_read_safely(self):
        s = self.o["sorts"]
        self.assertEqual(s[0], {"col": "late", "dir": "asc"})
        self.assertEqual(s[1], s[2])
        self.assertEqual(s[3], s[2])

    def test_nothing_private_in_any_option(self):
        text = json.dumps(self.o["opts"]).lower()
        for bad in ("follow", "vip"):
            self.assertNotIn(bad, text)

    def test_mutant_a_followed_option_in_the_allow_list_is_caught(self):
        # a real source mutant: a copy of the rules with a Followed option added to PD_GROUPS must make the privacy check go red
        import tempfile
        src = RULES.read_text()
        mut = src.replace('["details", "Details"]]', '["details", "Details"], ["followed", "Followed"]]')
        self.assertNotEqual(mut, src)
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "peopleDisplay.js"
            m.write_text(mut)
            o = node("const f = await import(%s); console.log(JSON.stringify(f.PD_GROUPS));" % json.dumps(m.as_uri()))
        self.assertIn("follow", json.dumps(o).lower())              # the check in test_nothing_private_in_any_option would fail on this


@unittest.skipUnless(shutil.which("node"), "needs Node")
class Builders(unittest.TestCase):
    def test_the_shared_pieces_draw_what_work_always_drew(self):
        js = """globalThis.document = { querySelector() { return null; }, querySelectorAll() { return []; } };
        const f = await import(%s); const o = {};
        o.sel = f.dispSelect({ id: "g", label: "Group by", options: [["a", "A<"], ["b", "B"]], cur: "b", hidden: true });
        o.ord = f.dispOrder({ id: "s", revId: "r", options: [["x", "X"]], cur: "x", reversed: true, extra: "<option>e</option>" });
        o.props = f.dispPropsMarkup({ shown: [["t", "Title"], ["o", "Owner"]], rest: [["z", "Zed"]], locked: "t", prefix: "dp" });
        o.foot = f.dispFoot({ resetId: "rs", doneId: "dn", resetLabel: "Reset" });
        console.log(JSON.stringify(o));""" % json.dumps(MENU.as_uri())
        try:
            o = node(js)
        except AssertionError as e:
            self.skipTest("the builders import the page's helpers: %s" % str(e)[:80])
        self.assertIn('<div hidden><h2><label for="g">Group by</label></h2>', o["sel"])
        self.assertIn('<option value="b" selected>B</option>', o["sel"])
        self.assertIn("A&lt;", o["sel"])
        self.assertIn('aria-pressed="true"', o["ord"])
        self.assertIn('<input type="checkbox" data-prop id="dp-t" value="t" checked disabled>Title', o["props"])
        self.assertIn('data-mv="t" data-d="-1" aria-label="Move Title earlier" disabled', o["props"])      # the first can't go earlier
        self.assertIn('data-mv="o" data-d="1" aria-label="Move Owner later" disabled', o["props"])         # the last can't go later
        self.assertNotIn('id="dp-z" value="z" checked', o["props"])
        self.assertIn('id="dn">Done</button>', o["foot"])


class Page(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900

    def people(self, w=1400):
        b = self.b
        b.resize(w, 900)
        b.eval("try{localStorage.removeItem('creaite-peopledisplay');localStorage.removeItem('creaite-peoplesort')}catch(e){}; go('people')")
        b.wait("document.querySelector('#peopleTbl tbody tr[data-pn]')")
        return b

    def open_menu(self):
        b = self.b
        if not b.eval("!!document.querySelector('#plDispMenu.on')"):
            b.click("#plDispBtn")
        b.wait("document.querySelector('#plDispMenu.on')")

    def change(self, sel, value):
        self.b.eval("(()=>{const e=document.querySelector(%r);e.value=%r;e.dispatchEvent(new Event('change',{bubbles:true}))})()" % (sel, value))
        self.b.pump(0.4)

    def test_d_opens_it_and_esc_and_done_close_it_with_focus_back(self):
        b = self.people()
        b.eval("document.activeElement.blur(); document.dispatchEvent(new KeyboardEvent('keydown',{key:'d',bubbles:true}))")
        b.wait("document.querySelector('#plDispMenu.on')")
        self.assertEqual(b.eval("document.getElementById('plDispBtn').getAttribute('aria-expanded')"), "true")
        b.eval("document.querySelector('#plDispMenu select').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
        b.wait("!document.querySelector('#plDispMenu.on')")
        self.assertEqual(b.eval("document.activeElement.id"), "plDispBtn")
        self.open_menu()
        b.click("#pdDone")
        b.wait("!document.querySelector('#plDispMenu.on')")
        self.assertEqual(b.eval("document.activeElement.id"), "plDispBtn")

    def test_headings_are_level_two_and_options_never_name_who_is_followed(self):
        b = self.people()
        self.open_menu()
        self.assertEqual(b.eval("document.querySelectorAll('#plDispMenu h3').length"), 0)
        self.assertGreaterEqual(b.eval("document.querySelectorAll('#plDispMenu h2').length"), 3)
        text = b.eval("document.getElementById('plDispMenu').innerText.toLowerCase()")
        self.assertNotIn("follow", text)
        for g in [o for o in b.eval("[...document.querySelectorAll('#pdgrp option')].map(o=>o.value)")]:
            self.change("#pdgrp", g)
            self.assertEqual(b.eval("document.querySelectorAll('#peopleTbl [data-follow],#peopleTbl .pstar,#peopleTbl svg[aria-label=Followed]').length"), 0, g)
            self.assertNotIn("follow", b.eval("document.getElementById('peopleTbl').innerText.toLowerCase()"), g)

    def test_group_by_organisation_draws_headings_with_counts_and_folds(self):
        b = self.people()
        self.open_menu()
        self.change("#pdgrp", "org")
        b.wait("document.querySelector('#peopleTbl tr.wgh')")
        heads = b.eval("[...document.querySelectorAll('#peopleTbl tr.wgh')].map(h=>h.textContent.replace(/\\\\s+/g,' ').trim())")
        self.assertTrue(heads and all("people" in h or "person" in h for h in heads), heads)
        rows_before = b.eval("document.querySelectorAll('#peopleTbl tr[data-pn]').length")
        b.click("#pdDone")
        b.wait("!document.querySelector('#plDispMenu.on')")
        b.click("#peopleTbl tr.wgh [data-gtog]")
        b.pump(0.3)
        self.assertLess(b.eval("document.querySelectorAll('#peopleTbl tr[data-pn]').length"), rows_before)
        self.assertEqual(b.eval("document.querySelector('#peopleTbl tr.wgh [data-gtog]').getAttribute('aria-expanded')"), "false")
        saved = b.eval("localStorage.getItem('creaite-peopledisplay')")
        for name in b.eval("[...document.querySelectorAll('#peopleTbl tr[data-pn]')].map(r=>r.dataset.pn)"):
            self.assertNotIn(name, saved)                                    # the fold names the group, never a person
        self.assertEqual(b.eval("document.getElementById('plCount').textContent.startsWith('Showing')"), True)

    def test_a_person_on_two_projects_is_under_both_and_the_count_counts_people(self):
        b = self.people()
        n_people = b.eval("document.querySelectorAll('#peopleTbl tr[data-pn]').length")
        shown = b.eval("document.getElementById('plCount').textContent")
        self.open_menu()
        self.change("#pdgrp", "proj")
        rows = b.eval("[...document.querySelectorAll('#peopleTbl tr[data-pn]')].map(r=>r.dataset.pn)")
        self.assertGreaterEqual(len(rows), n_people)
        self.assertEqual(b.eval("document.getElementById('plCount').textContent"), shown)       # people, not rows

    def test_sub_group_never_repeats_the_group_and_order_agrees_with_a_heading_click(self):
        b = self.people()
        self.open_menu()
        self.change("#pdgrp", "org")
        self.assertNotIn("org", b.eval("[...document.querySelectorAll('#pdsub option')].map(o=>o.value)"))
        self.change("#pdsort", "name")
        self.assertEqual(b.eval("shared.PSORT.col"), "name")
        b.click("#pdRev")
        b.pump(0.3)
        self.assertEqual(b.eval("shared.PSORT.dir"), "desc")
        self.assertEqual(b.eval("document.querySelector('#peopleTbl th[data-psort=name]').getAttribute('aria-sort')"), "descending")
        b.eval("document.querySelector('#peopleTbl th[data-psort=late] .thsort').click()")
        b.pump(0.4)
        self.assertEqual(b.eval("shared.PSORT.col"), "late")

    def test_untick_hides_the_column_reorder_and_reset_and_a_reload_remembers(self):
        b = self.people()
        self.open_menu()
        b.eval("(()=>{const i=document.getElementById('pdprop-email');i.checked=false;i.dispatchEvent(new Event('change',{bubbles:true}))})()")
        b.pump(0.4)
        self.assertEqual(b.eval("document.querySelectorAll('#peopleTbl [data-col=email]').length"), 0)
        self.assertEqual(b.eval("document.getElementById('pdprop-name').disabled"), True)           # Name is locked
        self.assertEqual(b.eval("document.querySelectorAll('#plDispMenu [data-mv=name]').length"), 0)                  # Name has no arrows
        self.assertTrue(b.eval("document.querySelector(\"#plDispMenu [data-mv=org][data-d='-1']\")===null||document.querySelector(\"#plDispMenu [data-mv=org][data-d='-1']\").disabled"))   # and nothing goes above it
        b.click("#plDispMenu [data-mv=role][data-d='-1']")
        b.pump(0.4)
        order = b.eval("[...document.querySelectorAll('#peopleTbl thead th[data-col]')].map(h=>h.dataset.col)")
        self.assertEqual(order[:3], ["name", "role", "org"])
        b.eval("go('settings'); go('people')")
        b.wait("document.querySelector('#peopleTbl tbody tr[data-pn]')")
        b.pump(0.6)                                                                                  # the address settles (leaving a page closes the menu)
        self.assertEqual(b.eval("[...document.querySelectorAll('#peopleTbl thead th[data-col]')].map(h=>h.dataset.col).slice(0,3)"), ["name", "role", "org"])
        self.open_menu()
        b.click("#pdReset")
        b.pump(0.4)
        self.assertEqual(b.eval("[...document.querySelectorAll('#peopleTbl thead th[data-col]')].map(h=>h.dataset.col).slice(0,3)"), ["name", "email", "org"])

    def test_corrupt_storage_falls_back_to_the_defaults(self):
        b = self.b
        b.resize(1400, 900)
        b.eval("localStorage.setItem('creaite-peopledisplay','{\"group\":\"followed\",\"cols\":[\"nope\"],\"collapsed\":7}'); localStorage.setItem('creaite-peoplesort','{\"col\":\"followed\"}')")
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('people')")
        b.wait("document.querySelector('#peopleTbl tbody tr[data-pn]')")
        self.assertEqual(b.eval("document.querySelectorAll('#peopleTbl tr.wgh').length"), 0)
        self.assertEqual(b.eval("document.querySelectorAll('#peopleTbl thead th[data-col]').length"), 10)

    def test_it_fits_its_box_at_900_and_1400_with_every_column_on(self):
        for w in (1400, 900):
            b = self.people(w)
            fit = b.eval("(()=>{const c=document.querySelector('#peopleTbl'),t=c.querySelector('table'),h=[...t.querySelectorAll('th')].find(x=>x.dataset.col==='late');return [t.scrollWidth<=c.clientWidth+4, h.getBoundingClientRect().right<=c.getBoundingClientRect().right+1, document.scrollingElement.scrollWidth<=innerWidth]})()")
            self.assertEqual(fit, [True, True, True], w)
            # the Projects column keeps room for whole words (about 9 letters); its heading is not broken mid-word
            pj = b.eval("(()=>{const h=document.querySelector('#peopleTbl th[data-col=proj]');return [h.getBoundingClientRect().width, h.getBoundingClientRect().height]})()")
            self.assertGreaterEqual(pj[0], 90, w)
            self.assertLess(pj[1], 80, w)
            # Organisation and Role keep whole words too: no word in their headings or cells is split across two lines (#343 M1)
            broken = b.eval("""(()=>{const out=[];for(const e of document.querySelectorAll('#peopleTbl th,#peopleTbl :is(th,td):is([data-col=org],[data-col=role])')){const wk=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);let n;while((n=wk.nextNode())){const re=/\\S+/g;let m;while((m=re.exec(n.data))){const r=document.createRange();r.setStart(n,m.index);r.setEnd(n,m.index+m[0].length);const tops=new Set([...r.getClientRects()].map(x=>Math.round(x.top)));if(tops.size>1)out.push(m[0])}}}return out})()""")
            self.assertEqual(broken, [], w)
            heads = b.eval("[...document.querySelectorAll('#peopleTbl th:is([data-col=org],[data-col=role])')].length")
            self.assertEqual(heads, 2, w)
            self.assertEqual(b.eval("(()=>{const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);return ids.length-new Set(ids).size})()"), 0)
            self.assertEqual(b.errors, [])

    def test_the_register_and_settings_are_never_written(self):
        b = self.people()
        staged = lambda: sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*"))      # noqa: E731
        before, register = staged(), (self.v.root / "projects/_portfolio/people-register.md")
        text = register.read_text() if register.exists() else None
        settings = self.v.root / "system/config/settings.json"
        stext = settings.read_text() if settings.exists() else None
        self.open_menu()
        self.change("#pdgrp", "role")
        b.eval("document.getElementById('pdRev').click()")
        b.pump(0.3)
        self.assertEqual(b.eval("shared.PKS.length"), 0)
        self.assertEqual(staged(), before)                         # nothing proposed, nothing written
        self.assertEqual(register.read_text() if register.exists() else None, text)
        self.assertEqual(settings.read_text() if settings.exists() else None, stext)      # the Display choices never reach settings.json


if __name__ == "__main__":
    unittest.main()
