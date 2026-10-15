"""BL-264: Settings › People's filter. One funnel and picker as on Work (project, how they're involved, organisation, people
Alan follows, in the register, needs attention, removed), a search box, chips, the count line and its hints, Work's empty
state, and the filters remembered until cleared (the search is not). VIP stays private (BL-288): nothing on the card says it.

Run: python3 dev/tests/test_people_filters.py   (needs Google Chrome; skipped otherwise)

The people and items are put in the page's memory (fictional), over the sample vault's projects ABC and DEF.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

PEOPLE = [
    {"name": "Lena Fischer", "email": "lena@brightwater.example", "aliases": ["Lena"], "org": "Brightwater", "role": "Data lead"},
    {"name": "Rashid Al Suwaidi", "email": "rashid@northgate.example", "aliases": ["Rashid", "RAS"], "org": "Northgate Energy",
     "role": "Sponsor", "extra": {"VIP": "Client"}},
    {"name": "Karim Saleh", "email": "", "aliases": ["Karim"], "org": "Northgate Energy", "role": "CIO office"},
    {"name": "Hannah Brooks", "email": "hannah@northgate.example", "aliases": [], "org": "Northgate Energy", "role": "PMO lead",
     "hidden": True},
    {"name": "Mei Tan", "email": "", "aliases": ["Mei"], "org": "Orbit Retail", "role": "Test manager"},
]
SETUP = """(()=>{ const reg=%s.map(p=>({email:"",aliases:[],org:"",role:"",hidden:false,extra:{},...p}));
  REG.splice(0,REG.length,...reg); PEOPLE.added.splice(0); PEOPLE.hidden.splice(0);   /* the sample's names still in settings.json */
  const it=(id,p,o)=>({id,p,o,t:"Item "+id,st:"Open",pr:"Medium",due:null});
  A.splice(0,A.length,it("ABC-A-001","ABC","Lena Fischer"),it("ABC-A-002","ABC","Rashid Al Suwaidi"),it("ABC-A-003","ABC","Hannah Brooks"),
    it("ABC-A-004","ABC","Alan Carter"),it("DEF-A-001","DEF","Mei Tan"),it("DEF-A-002","DEF","Tom"));
  R.splice(0,R.length,it("ABC-R-001","ABC","Rashid Al Suwaidi"),it("DEF-R-001","DEF","Chris Doyle"));
  DEC.splice(0,DEC.length); D.stakeholders={ABC:["Rashid Al Suwaidi","Karim Saleh"],DEF:["Mei"]};
  go("settings","people"); return true; })()""" % json.dumps(PEOPLE)
ROWS = "[...document.querySelectorAll('#pmRows tr[data-pn]')].map(t=>t.dataset.pn)"
SET = "(k,vals,neg)=>{ PF.f[k]=new Set(vals); if(neg) PF.neg.add(k); else PF.neg.delete(k); pfDraw(); }"


class PeopleFilters(LiveBrowserCase):
    shared_server = True

    def setUp(self):
        super().setUp()
        self.b.eval("try{ localStorage.removeItem('creaite-people-filters'); }catch(e){}")
        # BL-327: the shared server's data is soon older than PAGE_FRESH, so each load re-reads /api/data after its first paint;
        # under load that reload landed after SETUP and put the sample's people and items back. Wait for it (and any pulse) first.
        self.b.wait("PULSE.reloads===0 && !PULSE.busy && !EVS.timer", 30)
        self.b.eval(SETUP)
        self.b.wait("document.querySelector('#pmRows tr[data-pn]')")

    def rows(self):
        return self.b.eval(ROWS)

    def search(self, text):
        self.b.eval(f"(q=>{{ q.value={json.dumps(text)}; q.dispatchEvent(new Event('input',{{bubbles:true}})); }})(document.getElementById('pmQ'))")

    def set(self, k, vals, neg=False):
        self.b.eval(f"({SET})({json.dumps(k)},{json.dumps(vals)},{json.dumps(neg)})")

    def test_default_hides_removed_people_with_its_chip_and_hint(self):
        b = self.b
        self.assertEqual(self.rows(), ["Alan Carter", "Chris Doyle", "Karim Saleh", "Lena Fischer", "Mei Tan", "Rashid Al Suwaidi", "Tom"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#pmApplied .fchip')].map(c=>[c.className,c.textContent])"),
                         [["fchip def", "Removed: hidden"]])
        count = b.eval("document.getElementById('pmCount').textContent")
        self.assertIn("Showing 7 of 8 people", count)
        self.assertIn("1 removed hidden", count)
        self.assertIsNone(b.eval("document.getElementById('pmClearF')"))           # nothing beyond the default
        self.assertIsNone(b.eval("document.querySelector('#pmFBtn .dot')"))
        self.assertEqual(b.eval("document.getElementById('pmFBtn').getAttribute('aria-label')"), "Filter people")
        b.click("#pmCount [data-pfquick=showrem]")
        self.assertIn("Hannah Brooks", self.rows())
        self.assertEqual(b.eval("PF.rem"), "show")
        self.assertIsNotNone(b.eval("document.getElementById('pmClearF')"))
        # × on the chip, from hidden: shows them too; Removed only through the picker
        b.eval("PF.rem='hide'; pfDraw()")
        b.click("#pmApplied [data-pfclr=rem]")
        self.assertEqual(b.eval("PF.rem"), "show")
        b.eval("pfOpen('rem')")
        b.click("#pmFMenu [data-pfrem=only]")
        self.assertEqual(self.rows(), ["Hannah Brooks"])
        self.assertIn("Removed only", b.eval("document.getElementById('pmApplied').textContent"))
        self.assertEqual(b.eval("document.querySelector('#pmFBtn .dot').textContent"), "1")

    def test_vip_is_never_labelled(self):
        b = self.b
        b.eval("PF.rem='show'; pfOpen('vip')")
        text = b.eval("document.getElementById('peopleMgr').textContent")
        self.assertNotRegex(text, r"\bVIP\b")
        self.assertEqual(b.eval("[...document.querySelectorAll('#pmFMenu .fpopts label')].map(l=>l.firstChild.nextSibling.textContent)"),
                         ["Followed", "Not followed"])
        self.assertEqual(b.eval("document.getElementById('pmFph').textContent"), "People I follow")
        self.set("vip", ["yes"])
        self.assertEqual(self.rows(), ["Rashid Al Suwaidi"])
        self.assertIn("People I follow: Followed", b.eval("document.getElementById('pmApplied').textContent"))
        self.assertNotRegex(b.eval("document.getElementById('peopleMgr').textContent"), r"\bVIP\b")

    def test_only_existing_fields_and_choices_are_offered_with_counts(self):
        b = self.b
        b.eval("pfOpen('org')")
        fields = b.eval("[...document.querySelectorAll('#pmFMenu [data-pfk]')].map(x=>x.dataset.pfk)")
        self.assertEqual(fields, ["proj", "inv", "org", "vip", "reg", "att", "rem"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#pmFMenu .fsec2')].map(x=>x.textContent)"), ["Who", "Tidy up"])
        opts = b.eval("[...document.querySelectorAll('#pmFMenu .fpopts label')].map(l=>[l.firstChild.nextSibling.textContent,l.querySelector('small').textContent])")
        self.assertEqual(opts, [["Brightwater", "1"], ["Northgate Energy", "2"], ["Orbit Retail", "1"], ["No organisation", "3"]])
        self.assertEqual(b.eval("document.activeElement.dataset.pfv"), "Brightwater")      # focus lands on the first choice
        # with nobody removed, following nobody and everyone in the register, those fields are not offered
        b.eval("REG.forEach(p=>{ p.hidden=false; p.extra={}; }); A.splice(A.findIndex(a=>a.o==='Tom'),1); R.splice(R.findIndex(r=>r.o==='Chris Doyle'),1); pfDraw()")
        fields = b.eval("[...document.querySelectorAll('#pmFMenu [data-pfk]')].map(x=>x.dataset.pfk)")
        self.assertEqual(fields, ["proj", "inv", "org", "att"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#pmApplied .fchip')].length"), 0)     # no Removed: hidden chip either

    def test_project_from_items_and_stakeholders_and_its_counts(self):
        b = self.b
        self.set("proj", ["ABC"])
        self.assertEqual(self.rows(), ["Alan Carter", "Karim Saleh", "Lena Fischer", "Rashid Al Suwaidi"])
        self.assertEqual(b.eval("document.getElementById('pmHA').textContent"), "Actions · this project")
        self.assertIn("named in the project", b.eval("document.querySelector('#pmRows tr[data-pn=\"Karim Saleh\"] td').textContent"))
        self.assertEqual(b.eval("document.querySelector('#pmRows tr[data-pn=\"Rashid Al Suwaidi\"] td.num a').dataset.nav"),
                         "actions:open:ABC:st=&o=Rashid%20Al%20Suwaidi")
        self.assertIn("Project: ", b.eval("document.getElementById('pmApplied').textContent"))
        # How they're involved follows the chosen projects
        self.set("inv", ["stake"])
        self.assertEqual(self.rows(), ["Karim Saleh", "Rashid Al Suwaidi"])
        self.set("inv", ["own"])
        self.assertEqual(self.rows(), ["Alan Carter", "Lena Fischer", "Rashid Al Suwaidi"])
        self.set("inv", [])
        # the stakeholder by alias (Mei) counts for DEF; two projects: the counts and the link cover both
        self.set("proj", ["DEF"])
        self.assertEqual(self.rows(), ["Chris Doyle", "Mei Tan", "Tom"])
        self.set("proj", ["ABC", "DEF"])
        self.assertEqual(b.eval("document.getElementById('pmHA').textContent"), "Actions · 2 projects")
        b.click("#pmRows tr[data-pn=\"Rashid Al Suwaidi\"] td.num a")
        b.wait("VIEW==='work'")
        self.assertEqual(b.eval("[...PROJF].sort()"), ["ABC", "DEF"])

    def test_is_not_and_combining_fields(self):
        b = self.b
        b.eval("pfOpen('proj')")
        b.click("#pmFMenu [data-pfv=ABC]")
        b.click("#pmFMenu [data-neg='1']")
        self.assertEqual(self.rows(), ["Chris Doyle", "Mei Tan", "Tom"])
        chip = b.eval("[...document.querySelectorAll('#pmApplied .fchip')].map(c=>[c.className,c.textContent])")
        self.assertTrue(chip[0][1].startswith("Project: not "))
        self.assertEqual(chip[0][0], "fchip neg")
        self.assertEqual(b.eval("document.getElementById('pmHA').textContent"), "Actions")    # is not: every project's counts
        self.set("proj", [])
        self.set("org", ["Northgate Energy", "Orbit Retail"])
        self.assertEqual(self.rows(), ["Karim Saleh", "Mei Tan", "Rashid Al Suwaidi"])
        self.set("reg", ["out"])
        self.assertIn("Nobody matches", b.eval("document.getElementById('pmRows').textContent"))
        self.set("org", [])
        self.assertEqual(self.rows(), ["Chris Doyle", "Tom"])

    def test_needs_attention_show_and_search(self):
        b = self.b
        self.assertIn("4 need attention", b.eval("document.getElementById('pmCount').textContent"))
        b.click("#pmCount [data-pfquick=att]")
        self.assertEqual(sorted(b.eval("[...PF.f.att]")), ["email", "orgrole"])
        self.assertEqual(self.rows(), ["Chris Doyle", "Karim Saleh", "Mei Tan", "Tom"])
        self.set("att", ["orgrole"])
        self.assertEqual(self.rows(), ["Chris Doyle", "Tom"])
        self.set("att", [])
        # search: name, alias, email or role, marked; Esc clears it
        b.click("#pmQ")
        b.type("ras")
        self.assertEqual(self.rows(), ["Rashid Al Suwaidi"])
        self.assertIn("<mark>", b.eval("document.querySelector('#pmRows tr[data-pn]').innerHTML"))
        self.assertIn("Search: “ras”", b.eval("document.getElementById('pmApplied').textContent"))
        self.search("test manager")
        self.assertEqual(self.rows(), ["Mei Tan"])
        self.search("northgate.example")
        self.assertEqual(self.rows(), ["Rashid Al Suwaidi"])
        b.key("Escape")
        self.assertEqual(b.eval("PF.q"), "")
        self.assertEqual(len(self.rows()), 7)

    def test_empty_state_names_each_filter_and_removes_one(self):
        b = self.b
        self.set("proj", ["ABC"])
        self.set("org", ["Orbit Retail"])
        self.assertEqual(self.rows(), [])
        e = b.eval("document.querySelector('#pmRows .wempty').textContent")
        self.assertIn("Nobody matches these 2 filters", e)
        rel = b.eval("[...document.querySelectorAll('#pmRows .relax > div')].map(d=>[d.querySelector('b').textContent,d.querySelector('.sub').textContent])")
        self.assertEqual(rel[1], ["Organisation: Orbit Retail", "4 people"])
        self.assertEqual(rel[0][1], "1 person")
        b.click("#pmRows [data-relax=proj]")
        self.assertEqual(self.rows(), ["Mei Tan"])
        self.set("proj", ["ABC"])
        b.click("#pmRows [data-relax=all]")
        self.assertEqual(len(self.rows()), 7)
        self.assertEqual(b.eval("PF.rem"), "hide")

    def test_keyboard_chips_and_focus(self):
        b = self.b
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("F")
        b.wait("document.getElementById('pmFMenu').classList.contains('on')")
        self.assertEqual(b.eval("document.getElementById('pmFBtn').getAttribute('aria-expanded')"), "true")
        b.eval("document.querySelector('#pmFMenu [data-pfk]').focus()")
        b.key("ArrowDown")
        self.assertEqual(b.eval("document.activeElement.dataset.pfk"), "inv")
        b.key("ArrowRight")
        self.assertEqual(b.eval("document.activeElement.dataset.pfv"), "own")
        b.key("ArrowLeft")
        self.assertEqual(b.eval("document.activeElement.dataset.pfk"), "inv")
        b.key("Escape")
        self.assertFalse(b.eval("document.getElementById('pmFMenu').classList.contains('on')"))
        self.assertEqual(b.eval("document.activeElement.id"), "pmFBtn")
        # a chip's words open the picker at its field; Done closes it and returns focus to the funnel
        self.set("org", ["Brightwater"])
        b.click("#pmApplied [data-pfedit=org]")
        self.assertEqual(b.eval("PF.pk"), "org")
        self.assertTrue(b.eval("document.getElementById('pmFMenu').classList.contains('on')"))
        self.assertEqual(b.eval("document.getElementById('pmFpResult').textContent"), "Showing 1 of 8")
        b.click("#pmFpDone")
        self.assertEqual(b.eval("document.activeElement.id"), "pmFBtn")
        self.assertEqual(b.eval("document.getElementById('pmFBtn').getAttribute('aria-label')"), "Filter people: 1 on")
        # a click outside closes it
        b.eval("pfOpen()")
        b.click("#pmRows tr[data-pn] td")
        self.assertFalse(b.eval("PF.open"))
        # / goes to the search here (elsewhere it is ask creaite)
        b.eval("document.activeElement.blur()")
        b.key("/")
        self.assertEqual(b.eval("document.activeElement.id"), "pmQ")
        self.assertFalse(b.eval("document.getElementById('chat').classList.contains('on')"))

    def test_remembered_until_cleared_but_not_the_search(self):
        b = self.b
        self.set("proj", ["ABC"])
        self.search("lena")
        saved = b.eval("JSON.parse(localStorage.getItem('creaite-people-filters'))")
        self.assertEqual(saved["proj"], ["ABC"])
        self.assertNotIn("q", saved)
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('settings','people')")
        b.wait("document.querySelector('#pmRows')")
        self.assertEqual(b.eval("[...PF.f.proj]"), ["ABC"])
        self.assertEqual(b.eval("document.getElementById('pmQ').value"), "")
        self.assertIn("Project: ", b.eval("document.getElementById('pmApplied').textContent"))
        b.click("#pmClearF")
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('settings','people')")
        b.wait("document.querySelector('#pmRows')")
        self.assertEqual(b.eval("PF.f.proj.size"), 0)
        self.assertEqual(b.eval("PF.rem"), "hide")

    def test_phone_width_has_no_sideways_scroll(self):
        b = self.b
        b.resize(390, 800)
        # the rail turns to icons on the media query's change event, which Chrome sends at the next frame, not on the resize;
        # under load the check ran first, with the 212px rail still pushing the People card (and its menu) to the right
        b.wait("innerWidth===390 && document.documentElement.classList.contains('railicons')")
        b.eval("pfOpen('org')")
        b.wait("document.getElementById('pmFMenu').classList.contains('on')")
        r = b.eval("(()=>{ const m=document.getElementById('pmFMenu').getBoundingClientRect(); return [m.left,m.right,innerWidth,document.documentElement.scrollWidth]; })()")
        self.assertGreaterEqual(r[0], 0)
        self.assertLessEqual(r[1], r[2])
        self.assertLessEqual(r[3], r[2])


if __name__ == "__main__":
    unittest.main()
