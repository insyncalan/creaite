"""BL-228 part D (sprint-escaping): hostile text from outside creaite stays text on every screen.

Items carrying `<img src=x onerror=…>`, `"><svg onload=…>` and `' autofocus onfocus=…` are applied in an action's description
and owner, a risk, a decision, a project's health reason, a milestone name and a source line, and an inbox file is given a
hostile name. The test then opens every view, every item, ⌘K search, Review's pending proposals, Files, Activity and a chat
reply rendered from markdown (and, since BL-231 step 4, Settings' and Help's tabs, the milestones page, Work's filter and
display menus, Review's display menu, the item panel's pickers and the rail's menu), and checks that no payload ran, no
injected element or handler was ever added to the page (a MutationObserver watches from before the page's own script),
and that the payload is shown as literal text.

Run: python3 dev/tests/test_hostile_text.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_chat_and_sweep import FAKE_CLAUDE  # noqa: E402
from test_dashboard import d, new, populate  # noqa: E402
from test_tracker import action  # noqa: E402

P1 = "<img src=x onerror=PWNED.push(1)>"
P2 = '"><svg onload=PWNED.push(2)>'
P3 = "' autofocus onfocus=PWNED.push(3) x='"
ALL = f"{P1} {P2} {P3}"

# Watches from document start: any element added with a payload's handler, an img pointing at "x", or any attribute that
# carries a payload, is recorded even if a later render removes it again.
WATCH = r"""(()=>{ window.PWNED=[]; window.INJECTED=[];
  const bad=e=>e.nodeType===1&&((e.tagName==="IMG"&&e.getAttribute("src")==="x")||(e.tagName.toLowerCase()==="svg"&&e.hasAttribute("onload"))||
    [...e.attributes].some(a=>/^on/i.test(a.name)&&/PWNED/.test(a.value))||(e.hasAttribute("onfocus")&&e.hasAttribute("autofocus")));
  const scan=n=>{ if(n.nodeType!==1) return; if(bad(n)) INJECTED.push(n.outerHTML.slice(0,200)); n.querySelectorAll&&n.querySelectorAll("*").forEach(c=>{ if(bad(c)) INJECTED.push(c.outerHTML.slice(0,200)); }); };
  new MutationObserver(ms=>ms.forEach(m=>{ m.addedNodes.forEach(scan); if(m.type==="attributes") scan(m.target); }))
    .observe(document,{childList:true,subtree:true,attributes:true}); })();"""


class HostileText(LiveBrowserCase):
    shared_server = True
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        src = f"Email · From: {P1} · Subject: [ABC] {P2} · Sent: 2026-10-01 09:00 · {P3}"
        v.propose("hostile", [
            new("milestones", 1, project="ABC", name=f"Milestone {ALL}", baseline_date=d(12), forecast_date=d(14),
                source="Alan (cx-edit)"),
            action(2, description=f"Hostile action {ALL}", owner=f"Mallory {P1}", due_date=d(2), source=src),
            new("raid", 3, project="ABC", type="Risk", description=f"Hostile risk {ALL}", impact="High",
                likelihood="High", raised=d(-1), source=src),
            new("decisions", 4, project="ABC", decision=f"Hostile decision {ALL}", made_by=f"Eve {P2}", date=d(-1),
                source=src),
            {"n": 5, "op": "update", "table": "projects", "id": "ABC",
             "changes": {"health": "At risk", "health_reason": f"Hostile reason {ALL}"}, "decision": "approved"},
        ])
        v.run("apply")
        for name in (f"{P1}.vtt", f"{P2} sync.vtt", f"{P3}.vtt"):
            (v.root / "inbox" / name).write_bytes(b"WEBVTT hostile")
        v.propose("pending-hostile", [{**action(1, description=f"Pending hostile {ALL}", owner=f"Trudy {P3}", source=src),
                                       "decision": "pending"}],
                  meeting={"key": "hk", "title": f"Meeting {ALL}", "projects": ["ABC"], "draft": None,
                           "minutes_decision": "pending", "file_ops": []})
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def setUp(self):
        super().setUp()
        self.b.call("Page.addScriptToEvaluateOnNewDocument", source=WATCH)
        self.b.reload("typeof go==='function' && LIVE")
        self.b.wait("A.some(x=>x.t.startsWith('Hostile action'))", 20)

    # ----- checks -----
    def assert_clean(self, where):
        b = self.b
        b.pump(0.3)
        state = b.eval("""(()=>{ const live=[...document.querySelectorAll('img[src="x"],svg[onload],[onfocus][autofocus]')].map(e=>e.outerHTML.slice(0,200));
            const on=[...document.querySelectorAll('*')].filter(e=>[...e.attributes].some(a=>/^on/i.test(a.name)&&/PWNED/.test(a.value))).map(e=>e.outerHTML.slice(0,200));
            return {pwned:PWNED.slice(), injected:INJECTED.slice(), live:[...live,...on]}; })()""")
        self.assertEqual(state, {"pwned": [], "injected": [], "live": []}, f"hostile text became markup in {where}")

    def shows(self, selector, text, where):
        got = self.b.eval(f"(()=>{{ const e=document.querySelector({json.dumps(selector)}); return e?e.innerText:''; }})()")
        self.assertIn(text, got, f"{where}: the hostile text is not shown literally")

    def view(self, v, arg=None):
        self.b.eval(f"go({json.dumps(v)},{json.dumps(arg)})")
        self.b.pump(0.4)
        self.assert_clean(f"view {v}{' ' + str(arg) if arg else ''}")

    # ----- the views -----
    def test_every_view_and_item(self):
        b = self.b
        for v in ("today", "projects", "people", "intake-review", "files", "activity", "settings", "help"):
            with self.subTest(view=v):
                self.view(v)
        self.view("cockpit", "ABC")
        self.shows("#v-cockpit", "Hostile reason " + P1, "the project page")
        self.view("person", f"Mallory {P1}")
        for wt in ("actions", "raid", "decisions", "all"):
            with self.subTest(work=wt):
                b.eval(f"WT={json.dumps(wt)}; go('work')")
                b.pump(0.4)
                for lay in b.eval("[...document.querySelectorAll('#wlay [data-lay]')].filter(e=>e.offsetParent).map(e=>e.dataset.lay)"):
                    b.click(f'#wlay [data-lay="{lay}"]')
                    b.pump(0.4)
                    self.assert_clean(f"work {wt} ({lay})")
        b.eval("WT='actions'; go('work')")
        b.pump(0.4)
        self.shows("#v-work", "Hostile action " + P1, "Work")
        for k, ids in (("actions", "A"), ("raid", "R"), ("decisions", "DEC")):
            for id_ in b.eval(f"{ids}.map(x=>x.id)"):
                with self.subTest(item=id_):
                    b.eval(f"WT={json.dumps(k)}; go('work'); openRecord({json.dumps(k)},{json.dumps(id_)})")
                    b.pump(0.3)
                    self.assert_clean(f"item {id_}")
        hostile = b.eval("A.find(x=>x.t.startsWith('Hostile action')).id")
        b.eval(f"WT='actions'; go('work'); openRecord('actions',{json.dumps(hostile)})")
        b.pump(0.3)
        self.shows("#panel", "Hostile action " + P1, "the item panel")
        self.shows("#panel", P3, "the item panel's source")
        for ms in b.eval("P.flatMap(p=>p.ms.map(m=>m[3]))"):
            with self.subTest(milestone=ms):
                b.eval(f"closePanel(true); openMilestone({json.dumps(ms)})")
                b.pump(0.3)
                self.assert_clean(f"milestone {ms}")

    def test_the_screens_converted_in_v180(self):
        """BL-231 step 4: the screens whose last sinks moved to html: Settings' tabs, Help's tabs, the milestones page, Work's
        filter menus and display menu, Review's display menu, the item panel's pickers and date popover, the rail's menu."""
        b = self.b
        for t in ("general", "work", "health", "capture", "people", "system"):
            with self.subTest(settings=t):
                self.view("settings", t)
        for t in ("start", "howto", "reference"):
            with self.subTest(help=t):
                self.view("help", t)
        for v in ("plan", "move"):
            with self.subTest(milestones=v):
                b.eval(f"MVAUD='int'; mvOpenPage('ABC',{json.dumps(v)})")
                b.pump(0.4)
                self.assert_clean(f"the milestones page ({v})")
        self.shows("#v-milestones", "Milestone " + P1, "the milestones page")
        b.eval("WT='actions'; go('work')")
        b.pump(0.4)
        for btn in b.eval("[...document.querySelectorAll('#wfilters [data-open-fk],#wfilters #moreBtn')].filter(e=>e.offsetParent).map(e=>e.id)"):
            with self.subTest(filter=btn):
                b.click(f"#{btn}")
                b.pump(0.3)
                self.assert_clean(f"Work's filter menu {btn}")
                b.click("#v-work h1")
        b.click("#ownBtn")
        b.pump(0.3)
        self.shows("#ownMenu", "Mallory " + P1, "Work's owner filter")
        b.click("#v-work h1")
        b.click("#dispBtn")
        b.pump(0.3)
        self.assert_clean("Work's display menu")
        b.click("#v-work h1")
        hostile = b.eval("A.find(x=>x.t.startsWith('Hostile action')).id")
        b.eval(f"openRecord('actions',{json.dumps(hostile)})")
        b.pump(0.3)
        for f in b.eval("[...document.querySelectorAll('#panel [data-pkp]')].filter(e=>e.offsetParent).map(e=>e.dataset.pkp)"):
            with self.subTest(picker=f):
                b.click(f'#panel [data-pkp="{f}"]')
                b.pump(0.3)
                self.assert_clean(f"the panel's {f} picker")
                b.key("Escape")
                b.pump(0.2)
        b.eval("closePanel(true); go('intake-review')")      # #232 C2: Review's display menu went with the old page
        b.pump(0.3)
        self.assert_clean("the Intake page")
        b.eval("go('today')")
        if b.eval("!!document.getElementById('railMore') && !!document.getElementById('railMore').offsetParent"):
            b.click("#railMore")
            b.pump(0.3)
            self.assert_clean("the rail's menu")

    def test_the_html_helper(self):
        cases = {
            "html`<b>${'<i>&\"\\''}</b>`": "<b>&lt;i&gt;&amp;&quot;&#39;</b>",
            f"html`<p title='${{{json.dumps(P3)}}}'>${{{json.dumps(P1)}}}</p>`":
                "<p title='&#39; autofocus onfocus=PWNED.push(3) x=&#39;'>&lt;img src=x onerror=PWNED.push(1)&gt;</p>",
            "html`<ul>${['a<','b'].map(x=>html`<li>${x}</li>`)}</ul>`": "<ul><li>a&lt;</li><li>b</li></ul>",
            "html`${['<x>',raw('<y>'),['<z>']]}`": "&lt;x&gt;<y>&lt;z&gt;",
            "html`<div>${html`<i>${'<'}</i>`}</div>`": "<div><i>&lt;</i></div>",
            "html`${raw(ic('x'))}`": "__ICON__",
            "html`[${null}|${undefined}|${false}|${0}|${''}|${true}]`": "[|||0||true]",
            "html`no values`": "no values",
            "String(raw(raw('<b>')))": "<b>",
            "'a'+html`<b>${'<'}</b>`": "a<b>&lt;</b>",
            "(()=>{ const d=document.createElement('div'); d.innerHTML=html`<span>${'<img src=x>'}</span>`; return d.innerHTML; })()":
                "<span>&lt;img src=x&gt;</span>",
        }
        icon = self.b.eval("ic('x')")
        for js, want in cases.items():
            with self.subTest(js=js):
                self.assertEqual(self.b.eval(f"String({js})"), icon if want == "__ICON__" else want)
        self.assertTrue(self.b.eval("html`a` instanceof SafeHTML && raw('a') instanceof SafeHTML"))
        self.assert_clean("the helper's unit test")

    def test_the_check_catches_a_hole(self):
        self.b.eval(f"document.body.insertAdjacentHTML('beforeend',{json.dumps(P1 + P2)})")
        with self.assertRaises(AssertionError):
            self.assert_clean("a deliberate hole")

    def test_intake_files_and_activity_show_it_as_text(self):
        n = self.b.eval("REV.find(r=>r.rec.t.startsWith('Pending hostile')).n")
        self.view("intake-review", n)                                 # the meeting that holds the proposal opens
        self.shows("#v-intake-review", "Pending hostile " + P1, "Intake (a proposal)")
        self.shows("#v-intake-review", P1 + ".vtt", "Intake (a file)")
        self.view("files")
        self.view("activity")
        self.shows("#v-activity", "Hostile", "Activity")

    def test_search(self):
        b = self.b
        b.eval("openCk()")
        for q in ("Hostile", "PWNED", "Mallory"):
            with self.subTest(q=q):
                b.eval(f"$('#cmdkIn').value={json.dumps(q)}; $('#cmdkIn').dispatchEvent(new Event('input'))")
                b.pump(1.0)
                self.assert_clean(f"⌘K search {q}")
        b.eval("$('#cmdkIn').value='Hostile action'; $('#cmdkIn').dispatchEvent(new Event('input'))")
        b.pump(0.6)
        self.shows("#cmdkList", "Hostile action " + P1, "⌘K")
        b.eval("$('#cmdk').close()")

    def test_a_chat_reply(self):
        b = self.b
        b.eval("openChat()")
        b.pump(0.3)
        reply = f"**Found** {P1}\n\n- {P2}\n- `{P3}`\n\n| a | b |\n|---|---|\n| {P1} | {P2} |"
        b.eval(f"send({json.dumps('ECHO:' + reply)})")
        b.wait("!BUSY", 30)
        b.pump(0.3)
        self.assert_clean("a chat reply")
        self.shows("#chLog", P1, "the chat reply")
        self.shows("#chLog", P3, "the chat reply")


if __name__ == "__main__":
    unittest.main()
