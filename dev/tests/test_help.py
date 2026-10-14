"""Help in three tabs (BL-84): help.md is the one source for the Help page and the two standalone guides.

Run: python3 dev/tests/test_help.py   (the page tests need Google Chrome; they are skipped otherwise)

Parsing and rendering run on the repo's own system/templates/help.md. The page tests build a throwaway vault with
fictional data and load the real dashboard in headless Chrome.
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import CHROME, populate  # noqa: E402
from test_insight import chrome  # noqa: E402
from test_tracker import REPO, Vault  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import build_dashboard as bd  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402

# every ## heading of the old single-page Help, less "Guides" (replaced by a sentence in Reference's lead-in)
OLD_HEADINGS = [
    "Keyboard shortcuts", "What the icons mean", "Opening the dashboard", "Working with lists", "How saving works", "Updating creaite", "Today",
    "Project page", "Milestones: Plan and Movement", "Early warnings", "Meeting prep", "Quick capture", "Updates from meetings", "AI drafts", "Review", "Intake", "Files",
    "Activity", "People", "Workstreams", "Search", "Settings", "Client messaging", "Dates", "Sources",
    "Word documents and permissions in ask creaite", "Commands for Claude", "Open creaite as an app", "Live server and backups", "Troubleshooting"]
GROUPS = ["Every day", "Meetings", "Keeping it right", "Reporting", "Admin"]



def theme_count():
    """How many named themes the dashboard has (its THEMES list), so theme checks follow new themes by themselves."""
    page = readable_page()     # BL-231: the source; the bundle reprints the code
    return len(re.findall(r'\{id:"', re.search(r"const THEMES=\[(.*?)\];", page, re.S).group(1)))

def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


class ParseTests(unittest.TestCase):
    """help.md → three parts, and every component of the approved guides."""

    @classmethod
    def setUpClass(cls):
        cls.parts = bd.help_parse()
        cls.h = bd.help_sections()
        cls.tab = {t["id"]: t["html"] for t in cls.h["tabs"]}

    def test_three_parts_in_order(self):
        self.assertEqual([t["title"] for t in self.h["tabs"]], ["Start here", "How do I…", "Reference"])
        self.assertEqual([t["id"] for t in self.h["tabs"]], ["start", "howto", "reference"])

    def test_start_here_has_every_component(self):
        o = self.h["start"]
        self.assertEqual([(s["n"], s["label"], s["gate"]) for s in o["stages"]],
                         [(1, "In", False), (2, "Propose", False), (3, "You", True), (4, "Record", False), (5, "Out", False)])
        self.assertEqual([s["title"] for s in o["stages"]], ["Material arrives", "Claude drafts", "Review", "Apply", "See and report"])
        self.assertEqual(len(o["steps"]), 4)                                           # the first hour
        self.assertEqual(len(o["rhythm"]), 4)
        self.assertEqual(o["views"], ["Today", "Intake", "Projects", "Work", "People", "Review", "Files", "Settings"])
        self.assertGreaterEqual(len(o["say"]), 9)
        self.assertEqual(len(o["rules"]), 4)
        html = self.tab["start"]
        self.assertEqual(html.count('class="hp-stage'), 5)
        self.assertEqual(html.count('class="hp-stage hp-you"'), 1)                                      # the one gate
        self.assertIn("The only gate", html)
        self.assertEqual(html.count('class="hp-arrow"'), 4)                            # arrows between the stages
        self.assertIn('class="hp-back"', html)                                         # the return line
        self.assertIn('class="hp-keys"', html)
        self.assertIn('aria-label="creaite icon"', html)                               # the icon heads Start here
        self.assertEqual(html.count('class="hp-rule"'), 4)
        self.assertEqual(html.count('class="hp-step"'), 4)
        self.assertEqual(html.count('class="hp-beat"'), 4)
        self.assertEqual(html.count('class="hp-view"'), 8)
        self.assertIn("<thead>", html)                                                 # the phrasebook has its heading row
        self.assertIn('<span class="hp-say">process new minutes</span>', html)         # phrases are chips

    def test_how_to_has_the_tasks_in_five_groups(self):
        tasks = self.h["tasks"]
        self.assertGreaterEqual(len(tasks), 16)
        self.assertEqual(list(dict.fromkeys(t["group"] for t in tasks)), GROUPS)
        for t in tasks:
            self.assertTrue(t["where"], t["id"])
            self.assertGreaterEqual(t["steps"], 3, t["id"])
            self.assertTrue(t["say"], t["id"])                                         # an "Or say" row on every card
        html = self.tab["howto"]
        self.assertEqual(html.count('class="hp-task"'), len(tasks))
        self.assertEqual(html.count('class="hp-where"'), len(tasks))
        self.assertEqual(html.count('class="hp-or"'), len(tasks))
        self.assertEqual(html.count('<section class="hp-group"'), 5)
        self.assertIn('<nav class="hp-index"', html)
        self.assertEqual(len(re.findall(r'<li><a href="#help-howto-', html)), len(tasks))   # the grouped index links every card

    def test_draft_email_replaces_prep_1_1(self):
        ids = [t["id"] for t in self.h["tasks"]]
        self.assertIn("ask-someone-for-an-update", ids)
        for html in self.tab.values():
            self.assertNotIn("Prep 1:1", html)
        self.assertIn("Draft email", self.tab["howto"])
        self.assertIn("Draft email", self.tab["reference"])

    def test_reference_keeps_every_heading(self):
        titles = [s["title"] for s in self.h["sections"]]
        for h in OLD_HEADINGS:
            self.assertIn(h, titles)
        self.assertEqual(len(titles), len(OLD_HEADINGS))
        self.assertNotIn("Guides", titles)                                             # now inside Help
        self.assertIn("printable copy", text_of(self.tab["reference"]) .replace("A printable copy", "a printable copy"))
        for s in self.h["sections"]:
            self.assertIn(f'id="hr-{s["id"]}"', self.tab["reference"])

    def test_nothing_is_left_unrendered(self):
        for tid, html in self.tab.items():
            t = text_of(html)
            for token in ("{version}", "{you", "**", "`", "[[", "]]", "](#"):
                self.assertNotIn(token, t, (tid, token))
            self.assertNotIn("<!--", html)
        self.assertIn("[start command]", self.tab["reference"])                        # the page fills in the vault's command
        self.assertNotIn("Where:", text_of(self.tab["howto"]))
        self.assertNotIn("Or say:", text_of(self.tab["howto"]))

    def test_links_between_tasks_and_parts(self):
        html = self.tab["start"] + self.tab["howto"] + self.tab["reference"]
        self.assertIn('data-help="howto-review-and-approve-proposals"', html)
        self.assertIn('data-help="howto"', self.tab["start"])                          # Start here's footer points to How do I…
        self.assertIn('data-help="start"', self.tab["howto"])
        self.assertIn('data-help="howto-ask-someone-for-an-update"', self.tab["howto"])
        known = {t["id"] for t in self.h["tasks"]}
        for slug in re.findall(r'data-help="howto-([^"]+)"', html):
            self.assertIn(slug, known)

    def test_version_is_filled_in(self):
        version = (REPO / "VERSION").read_text().strip()
        self.assertIn(f"creaite {version} · first day", text_of(self.tab["start"]))
        self.assertIn(f"creaite-{version}.zip", text_of(self.tab["start"]))


class FontTests(unittest.TestCase):
    """The three faces embed as data URIs when their files are vendored, and are skipped (system fonts) when not."""

    def test_embedding(self):
        import base64
        import tempfile
        real = bd.paths.TEMPLATES
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "vendor").mkdir()
            (Path(d) / "vendor" / "schibsted-grotesk-800.woff2").write_bytes(b"wOF2stub")
            (Path(d) / "vendor" / "source-sans-3-400.woff2").write_bytes(b"wOF2stub2")
            bd.paths.TEMPLATES = Path(d)
            try:
                faces = bd.help_font_faces()
                everything = bd.font_faces()
            finally:
                bd.paths.TEMPLATES = real
        self.assertIn('font-family:"Schibsted Grotesk";font-style:normal;font-weight:800', faces)
        self.assertIn("data:font/woff2;base64," + base64.b64encode(b"wOF2stub").decode(), faces)
        self.assertIn('font-family:"Source Sans 3";font-style:normal;font-weight:400', faces)
        self.assertNotIn("JetBrains", faces)                                          # a missing file is skipped
        self.assertEqual(faces.count("@font-face"), 2)
        self.assertNotIn("Roboto", everything)                                        # (no Roboto in the stub folder)
        self.assertIn("Roboto", bd.font_faces())                                      # the real folder still has it

    def test_a_variable_font_is_embedded_once_with_its_weight_range(self):
        import tempfile
        real = bd.paths.TEMPLATES
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "vendor").mkdir()
            for w in (500, 700, 800):                                                  # Google serves one variable file
                (Path(d) / "vendor" / f"schibsted-grotesk-{w}.woff2").write_bytes(b"wOF2same")
            bd.paths.TEMPLATES = Path(d)
            try:
                faces = bd.help_font_faces()
            finally:
                bd.paths.TEMPLATES = real
        self.assertEqual(faces.count("@font-face"), 1)
        self.assertIn('font-family:"Schibsted Grotesk";font-style:normal;font-weight:500 800', faces)

    def test_the_fonts_and_their_licence_are_the_ones_the_guides_use(self):
        self.assertEqual(sorted({f for f, _, _ in bd.HELP_FONTS}), ["JetBrains Mono", "Schibsted Grotesk", "Source Sans 3"])
        self.assertEqual([(f, w) for f, w, _ in bd.HELP_FONTS],
                         [("Schibsted Grotesk", 500), ("Schibsted Grotesk", 700), ("Schibsted Grotesk", 800),
                          ("Source Sans 3", 400), ("Source Sans 3", 600), ("JetBrains Mono", 500)])
        self.assertTrue(all(n.endswith(".woff2") for _, _, n in bd.HELP_FONTS))


PAGE = r"""
  const wait=ms=>new Promise(r=>setTimeout(r,ms)), $q=s=>document.querySelector(s), $a=s=>[...document.querySelectorAll(s)], out={};
  VSTATE="ok"; needVault=async()=>true;   /* the page's own vault check can finish late and reset the fake vault (slow CI) */
"""


class PageTests(unittest.TestCase):
    """The Help view in headless Chrome."""

    @classmethod
    def setUpClass(cls):
        if not CHROME.exists():
            raise unittest.SkipTest("Google Chrome not installed")
        cls.v = v = Vault()
        populate(v)
        v.run(script="build_dashboard.py")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def probe(self, script):
        out, errors = chrome(self.v, PAGE + script, name="help")
        self.assertEqual(errors, [])
        self.assertIsNotNone(out)
        self.assertNotIn("error", out, out)
        return out

    def test_tabs_addresses_back_and_forward(self):
        o = self.probe("""
          const sel=()=>$a("#helpTabs button").map(b=>b.getAttribute("aria-selected")==="true"?b.dataset.help:null).filter(Boolean)[0], titles=()=>$a("#helpTabs button").map(b=>b.textContent);
          go("help"); out.first=[VIEW,location.hash,sel(),titles()];
          $q('#helpTabs [data-help=howto]').click(); out.howto=[location.hash,sel(),!!$q("#helpPane .hp-task")];
          $q('#helpTabs [data-help=reference]').click(); out.reference=[location.hash,sel(),!!$q("#helpPane .hp-refidx")];
          history.back(); await wait(80); out.back=[location.hash,sel()];
          history.back(); await wait(80); out.back2=[location.hash,sel()];
          history.forward(); await wait(80); out.fwd=[location.hash,sel()];
          out.parse=[parseHash("#help-start").arg,parseHash("#help-howto").arg,parseHash("#help-howto-undo-a-mistake").arg,parseHash("#help-howto-nope").arg,parseHash("#help-reference-search").arg,parseHash("#help").arg,parseHash("#help-howto").v];
          restoreNav(parseHash("#help-howto-undo-a-mistake")); await wait(30); out.deep=[VIEW,HELPARG,hashOf(navState())];
          window.OUT=out;""")
        self.assertEqual(o["first"], ["help", "#help-start", "start", ["Start here", "How do I…", "Reference"]])
        self.assertEqual(o["howto"], ["#help-howto", "howto", True])
        self.assertEqual(o["reference"], ["#help-reference", "reference", True])
        self.assertEqual(o["back"], ["#help-howto", "howto"])
        self.assertEqual(o["back2"], ["#help-start", "start"])
        self.assertEqual(o["fwd"], ["#help-howto", "howto"])
        self.assertEqual(o["parse"], ["start", "howto", "howto-undo-a-mistake", "howto", "reference-search", None, "help"])
        self.assertEqual(o["deep"], ["help", "howto-undo-a-mistake", "#help-howto-undo-a-mistake"])

    def test_an_index_link_jumps_to_its_card_and_highlights_it(self):
        o = self.probe("""
          go("help"); $q('#helpTabs [data-help=howto]').click();
          const link=$q('.hp-index a[data-help="howto-hand-over-someones-work"]'); link.click(); await wait(30);
          const card=$q("#ht-hand-over-someones-work"); await wait(200); const r=card.getBoundingClientRect();
          out.rect=[r.top,r.bottom,innerHeight,scrollY,$q("#v-help").scrollTop]; out.card=[location.hash,$a(".hp-hl").map(e=>e.id),r.top<innerHeight&&r.bottom>0, getComputedStyle(card).borderTopColor!==getComputedStyle($q("#ht-start-the-day")).borderTopColor];
          $q('.hp-index a[data-help="howto-undo-a-mistake"]').click(); out.moved=$a(".hp-hl").map(e=>e.id);
          $q('#helpPane a[data-help="howto-review-and-approve-proposals"]').click(); out.inText=[VIEW,HELPARG,$a(".hp-hl").map(e=>e.id)];
          window.OUT=out;""")
        self.assertEqual(o["card"][0], "#help-howto-hand-over-someones-work")
        self.assertEqual(o["card"][1:], [["ht-hand-over-someones-work"], True, True], o["rect"])
        self.assertEqual(o["moved"], ["ht-undo-a-mistake"])
        self.assertEqual(o["inText"], ["help", "howto-review-and-approve-proposals", ["ht-review-and-approve-proposals"]])

    def test_question_mark_opens_the_last_tab_used(self):
        o = self.probe("""
          const key=k=>document.dispatchEvent(new KeyboardEvent("keydown",{key:k,bubbles:true}));
          go("today"); key("?"); out.first=[VIEW,HELPARG];
          helpGo("reference"); go("today"); key("?"); out.second=[VIEW,HELPARG,location.hash];
          document.querySelector('[data-go=help]'); go("settings"); $q('#v-settings [data-go=help]').click(); out.settings=[VIEW,HELPARG];
          window.OUT=out;""")
        self.assertEqual(o["first"], ["help", "start"])
        self.assertEqual(o["second"], ["help", "reference", "#help-reference"])
        self.assertEqual(o["settings"], ["help", "reference"])

    def test_the_vault_command_replaces_the_placeholder_and_reference_search_filters(self):
        o = self.probe("""
          go("help"); helpGo("reference"); const box=$q("#helpPane .cmdbox");
          out.cmd=[!!box, box&&box.textContent.includes("live_server.py"), $q("#helpPane").textContent.includes("[start command]")];
          const n=$a("#helpPane .hp-ref").length; const q=$q("#helpQ"); q.value="hand over"; q.dispatchEvent(new Event("input",{bubbles:true}));
          out.filtered=[n,$a("#helpPane .hp-ref:not(.hidden)").map(s=>s.dataset.ref)]; q.value=""; q.dispatchEvent(new Event("input",{bubbles:true})); out.cleared=$a("#helpPane .hp-ref.hidden").length;
          helpGo("reference-search"); await wait(200); const s=$q("#hr-search").getBoundingClientRect(); out.jump=[location.hash,s.top<innerHeight&&s.bottom>0,$q('.hp-refidx a[aria-current]')&&$q('.hp-refidx a[aria-current]').dataset.help];
          window.OUT=out;""")
        self.assertEqual(o["cmd"], [True, True, False])
        self.assertEqual(o["filtered"][0], 30)                                 # 28 with What the icons mean (BL-158); 29 with Milestones (BL-186); 30 with AI drafts
        self.assertIn("people", o["filtered"][1])
        self.assertLess(len(o["filtered"][1]), 30)
        self.assertEqual(o["cleared"], 0)
        self.assertEqual(o["jump"], ["#help-reference-search", True, "reference-search"])

    def test_command_palette_finds_help(self):
        o = self.probe("""
          const key=(k)=>document.getElementById("cmdkIn").dispatchEvent(new KeyboardEvent("keydown",{key:k,bubbles:true}));
          const labels=q=>ckItems(q).filter(i=>i.g==="Help").map(i=>i.l);
          out.empty=[labels("").length, ckItems("").some(i=>i.g==="Help")];
          out.task=ckItems("hand over someone").filter(i=>i.g==="Help").map(i=>[i.l,i.h]);
          out.section=ckItems("early warn").filter(i=>i.g==="Help").map(i=>[i.l,i.h]);
          const howdo=ckItems("how do i"), nt=HD.tasks.length; out.nt=nt; out.howdo=[howdo[0].l, howdo.slice(1,nt+1).every(i=>i.g==="Help"&&i.h==="How do I…"), howdo[1].l, howdo[nt].l];
          const help=ckItems("help"); out.help=[help.slice(0,3).map(i=>i.l), help.filter(i=>i.g==="Help").length, help.findIndex(i=>i.l==="Help: Review"), help.findIndex(i=>i.l==="Help: Review and approve proposals")];
          out.hint=ckItems("how do i…").length>0;
          // choosing one, the way the palette does: type, arrow, Enter
          go("today"); openCk(); const box=document.getElementById("cmdkIn"); box.value="hand over someone"; box.dispatchEvent(new Event("input",{bubbles:true}));
          out.shown=[...document.querySelectorAll("#cmdkList button")].map(b=>b.textContent.replace(/\\s+/g," ").trim()).filter(t=>t.startsWith("Help:"));
          key("Enter"); await wait(60); out.picked=[VIEW,HELPARG,location.hash,[...document.querySelectorAll(".hp-hl")].map(e=>e.id),document.getElementById("cmdk").open];
          openCk(); box.value="early warnings"; box.dispatchEvent(new Event("input",{bubbles:true}));
          const at=CK.findIndex(i=>i.l==="Help: Early warnings"); CKI=at; key("Enter"); await wait(60);
          out.ref=[VIEW,HELPARG,location.hash,!!document.querySelector("#hr-early-warnings"),document.getElementById("hr-early-warnings").getBoundingClientRect().top<innerHeight];
          window.OUT=out;""")
        self.assertEqual(o["empty"], [0, False])                                       # nothing from Help until you type
        self.assertEqual(o["task"], [["Help: Hand over someone's work", "How do I…"]])
        self.assertIn(["Help: Early warnings", "Reference"], o["section"])
        self.assertEqual(o["nt"], len(bd.help_sections()["tasks"]))
        self.assertEqual(o["howdo"], ["Help: How do I…", True, "Help: Start the day", "Help: Fix a stopped server and other problems"])   # the tab, then every task
        self.assertEqual(o["help"][0], ["Help: Start here", "Help: How do I…", "Help: Reference"])
        self.assertEqual(o["help"][1], 3 + o["nt"] + 30)                 # every task and reference section (BL-186: Milestones; AI drafts)
        self.assertGreater(o["help"][3], 0)
        self.assertLess(o["help"][3], o["help"][2])                                    # tasks come before reference sections
        self.assertTrue(o["hint"])
        self.assertEqual(o["shown"], ["Help: Hand over someone's workHow do I…"])
        self.assertEqual(o["picked"], ["help", "howto-hand-over-someones-work", "#help-howto-hand-over-someones-work",
                                       ["ht-hand-over-someones-work"], False])
        self.assertEqual(o["ref"][:4], ["help", "reference-early-warnings", "#help-reference-early-warnings", True])
        self.assertTrue(o["ref"][4])

    def test_contrast_in_every_theme_and_mode(self):
        o = self.probe(r"""
          const lum=c=>{ const [r,g,b]=c.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
          const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
          const bgOf=el=>{ for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; if(!/rgba\(0, 0, 0, 0\)|transparent/.test(c)) return c; } return "rgb(255,255,255)"; };
          const pairs={start:[".hp-eyebrow",".hp-lede",".hp-loophead p",".hp-stage .hp-n",".hp-stage p",".hp-stage.hp-you p",".hp-stage.hp-you .hp-n",".hp-gate",".hp-back",".hp-step .hp-n",".hp-step p",".hp-beat .hp-when",".hp-beat p",".hp-view span",".hp-keys",".hp-say",".hp-phrases th",".hp-phrases td",".hp-rule span",".hp-foot",".hp-wrap code",".hp-foot a"],
            howto:[".hp-eyebrow",".hp-where",".hp-task ol",".hp-or",".hp-or b",".hp-say",".hp-index h2",".hp-index a",".hp-task a",".hp-task h3",".hp-wrap kbd",".hp-wrap code"],
            reference:[".hp-refidx a",".hp-refgroup",".hp-reflead",".hp-ref li",".hp-ref td",".hp-ref h2",".hp-wrap code"]};
          const res={};
          for(const pal of THEMES.map(t=>t.id)) for(const mode of ["Light","Dark"]){ S.palette=pal; S.theme=mode; applyTheme(); go("help");
            for(const [tab,sels] of Object.entries(pairs)){ helpGo(tab); for(const s of sels){ const el=$q("#helpPane "+s); if(!el){ res[`${pal}|${mode}|${tab}|${s}`]=-1; continue; }
              res[`${pal}|${mode}|${tab}|${s}`]=ratio(getComputedStyle(el).color,bgOf(el)); } } }
          out.res=res; window.OUT=out;""")
        res = o["res"]
        self.assertEqual(len({k.split("|")[0] for k in res}), theme_count())             # every theme
        self.assertGreater(len(res), 3 * 2 * 40)
        self.assertEqual([k for k, r in res.items() if r == -1], [])                       # every pair was found on its page
        self.assertEqual({k: round(r, 2) for k, r in res.items() if 0 <= r < 4.5}, {})



def run_chrome(cmd):
    """Run headless Chrome and return (stdout, stderr). Chrome can linger after printing the page (seen on GitHub's
    macOS runners): use what it printed, as the other browser tests do."""
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        return r.stdout or b"", r.stderr or b""
    except subprocess.TimeoutExpired as e:
        return e.stdout or b"", e.stderr or b""

def chrome_at(v, script, address="", name="first"):
    """Like test_insight.chrome, but opens the page at an address (#review…) the way a bookmark would."""
    import html as h
    import shutil
    import subprocess
    import tempfile
    html = (v.root / "dashboard.html").read_text(encoding="utf-8")
    probe = v.root / f"{name}.html"
    probe.write_text(html.replace("</body>", "<script>window.addEventListener('load',async()=>{try{" + script +
                                  "}catch(e){window.OUT={error:String(e&&e.stack||e)}} const p=document.createElement('pre');"
                                  "p.id='out';p.textContent=JSON.stringify(window.OUT);document.body.appendChild(p);});"
                                  "</script></body>"), encoding="utf-8")
    profile = tempfile.mkdtemp(prefix="creaite-chrome-")
    cmd = [str(CHROME), "--headless", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run", "--disable-component-update",
           "--disable-background-networking", "--enable-logging=stderr", "--v=0", "--virtual-time-budget=4000", "--dump-dom",
           probe.as_uri() + address]
    try:
        stdout, stderr = run_chrome(cmd)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    m = re.search(r'<pre id="out">(.*?)</pre>', stdout.decode("utf-8", "ignore"), re.S)
    errors = [ln for ln in stderr.decode("utf-8", "ignore").splitlines() if "CONSOLE" in ln and ("Uncaught" in ln or "Error" in ln)]
    return (json.loads(h.unescape(m.group(1))) if m else None), errors


def set_start_seen(v, seen):
    cfg = v.root / "system" / "config" / "settings.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    data["help"] = {"start_seen": seen}
    cfg.write_text(json.dumps(data, indent=2), encoding="utf-8")


class FirstVisitTests(unittest.TestCase):
    """help.start_seen: a first visit opens Help › Start here once, then never again."""

    @classmethod
    def setUpClass(cls):
        if not CHROME.exists():
            raise unittest.SkipTest("Google Chrome not installed")
        cls.v = Vault()
        populate(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def load(self, seen, address="", script=""):
        set_start_seen(self.v, seen)
        self.v.run(script="build_dashboard.py")
        out, errors = chrome_at(self.v, 'const out={}; ' + script + ' out.view=[VIEW,HELPARG,location.hash,S.helpSeen]; window.OUT=out;', address)
        self.assertEqual(errors, [])
        self.assertIsNotNone(out)
        self.assertNotIn("error", out, out)
        return out

    def test_the_settings(self):
        defaults = json.loads((REPO / "system" / "templates" / "settings-defaults.json").read_text(encoding="utf-8"))
        repo = json.loads((REPO / "system" / "config" / "settings.json").read_text(encoding="utf-8"))
        self.assertIs(defaults["help"]["start_seen"], False)                           # a new vault, or one that updates, sees it once
        self.assertIs(repo["help"]["start_seen"], True)                                # this development repo does not

    def test_an_unseen_vault_opens_on_start_here(self):
        o = self.load(False)
        self.assertEqual(o["view"][:3], ["help", "start", "#help-start"])
        self.assertIs(o["view"][3], False)                                             # (nothing can be written here: no live server, no vault folder yet)

    def test_a_seen_vault_opens_on_today(self):
        o = self.load(True)
        self.assertEqual(o["view"][0], "today")
        self.assertEqual(o["view"][3], True)

    def test_an_address_is_never_overridden(self):
        o = self.load(False, "#review")
        self.assertEqual(o["view"][0], "review")

    def test_it_is_marked_seen_with_a_logged_settings_write(self):
        seed = json.dumps((self.v.root / "system/config/settings.json").read_text(encoding="utf-8"))
        o = self.load(False, script="""
          const FILES={"system/config/settings.json":%s}, LOG=[]; VW={read:async p=>{ if(!(p in FILES)) throw new Error("not found: "+p); return FILES[p]; },
            write:async(p,t)=>{ FILES[p]=t; LOG.push(p); }, remove:async p=>{ delete FILES[p]; }, exists:async p=>p in FILES, append:async(p,t)=>{ FILES[p]=(FILES[p]||"")+t; LOG.push(p); }};
          VSTATE="ok"; needVault=async()=>true;
          out.before=[S.helpSeen]; out.marked=await markHelpSeen(); await VQ;
          out.after=[S.helpSeen, JSON.parse(FILES["system/config/settings.json"]).help.start_seen, firstHelp(), await markHelpSeen()];
          out.log=FILES["system/config/settings-log.jsonl"].trim().split("\\n").map(l=>JSON.parse(l)); out.backup=LOG.some(p=>p.startsWith("system/backups/settings-"));""" % seed)
        self.assertEqual(o["before"], [False])
        self.assertTrue(o["marked"])
        self.assertEqual(o["after"], [True, True, False, False])                       # and never again
        self.assertEqual([(r["key"], r["old"], r["new"]) for r in o["log"]], [("help.start_seen", False, True)])
        self.assertTrue(o["backup"])


class GuideTests(unittest.TestCase):
    """The standalone guides are generated from help.md: current, self-contained, linked, and drawn like the Help tabs."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(REPO / "dev" / "tools"))
        import build_guides
        cls.bg = build_guides
        cls.built = build_guides.build()          # rebuilt from help.md now
        cls.ondisk = {n: (REPO / "system" / "templates" / n).read_text(encoding="utf-8") for n in cls.built}

    def test_the_files_are_up_to_date_with_help_md(self):
        for name, content in self.built.items():
            self.assertEqual(self.ondisk[name], content, f"{name} is out of date: run python3 dev/tools/build_guides.py")

    def test_they_are_self_contained(self):
        for name, html in self.ondisk.items():
            for bad in ("http://", "https://", "<link", "<script", "@import", "url(//", "src="):
                self.assertNotIn(bad, html, (name, bad))
            self.assertNotRegex(html, r"url\((?!data:)")                               # only embedded fonts, if any

    def test_they_link_to_each_other(self):
        self.assertIn('href="guide-how-to.html"', self.ondisk["guide-first-day.html"])
        self.assertIn('href="guide-first-day.html"', self.ondisk["guide-how-to.html"])
        self.assertNotIn("data-help", "".join(self.ondisk.values()))                    # file links, not dashboard tabs
        how = self.ondisk["guide-how-to.html"]
        ids = set(re.findall(r'<article class="hp-task" id="([^"]+)"', how))
        self.assertGreaterEqual(len(ids), 16)
        for target in re.findall(r'href="#([^"]+)"', how):
            self.assertIn(target, ids)                                                  # every index link reaches a card

    def test_they_draw_the_same_components_with_the_same_css(self):
        css = self.bg.components_css()
        dash = (REPO / "system" / "templates" / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn(css, dash)
        for html in self.ondisk.values():
            self.assertIn(css, html)                                                    # the very same rules as the Help tabs
        first, how = self.ondisk["guide-first-day.html"], self.ondisk["guide-how-to.html"]
        h = bd.help_sections()
        def norm(x):                                                                    # links are the only difference between modes
            return re.sub(r'\s(data-help="[^"]*"|href="[^"]*"|id="(ht-)?[^"]*")', "", x)
        self.assertIn(norm(h["tabs"][0]["html"]), norm(first))
        self.assertIn(norm(h["tabs"][1]["html"]), norm(how))
        for html in (first, how):
            self.assertIn('fill="#F2B544"', html)                                       # the saffron record
            self.assertNotIn("M340.85 171.15", html)                                    # never the old teal c
        for mark in ('class="hp-flow"', 'class="hp-steps"', 'class="hp-rhythm"', 'class="hp-views"', 'class="hp-phrases"', 'class="hp-rules"'):
            self.assertIn(mark, first)
        for mark in ('class="hp-index"', 'class="hp-tasks"', 'class="hp-where"', 'class="hp-or"'):
            self.assertIn(mark, how)
        self.assertIn("<title>creaite First Day</title>", first)
        self.assertIn("<title>creaite How-To</title>", how)
        self.assertIn("prefers-color-scheme:dark", first)                               # light and dark, as the artifacts have
        self.assertIn(':root[data-theme="dark"]', how)

    def test_they_open_in_a_browser_in_both_modes(self):
        if not CHROME.exists():
            self.skipTest("Google Chrome not installed")
        import subprocess
        import tempfile
        for name in self.built:
            probe = Path(tempfile.mkdtemp(prefix="creaite-guide-")) / name
            self.addCleanup(shutil.rmtree, probe.parent, True)      # BL-172 (sprint-polish-2)
            probe.write_text(self.ondisk[name].replace("</body>", """<script>const lum=c=>{ const [r,g,b]=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
              const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); }; const res={};
              for(const mode of ["light","dark"]){ document.documentElement.dataset.theme=mode; for(const s of [".hp-eyebrow",".hp-lede",".hp-say",".hp-foot",".hp-where",".hp-or",".hp-stage p",".hp-rule span"]){ const el=document.querySelector(s); if(!el) continue;
                let bg="rgb(255,255,255)"; for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; if(!/rgba\\(0, 0, 0, 0\\)/.test(c)){ bg=c; break; } } res[mode+"|"+s]=ratio(getComputedStyle(el).color,bg); } }
              const p=document.createElement("pre"); p.id="out"; p.textContent=JSON.stringify({res,scroll:document.documentElement.scrollWidth<=innerWidth+1}); document.body.appendChild(p);</script></body>"""))
            profile = tempfile.mkdtemp(prefix="creaite-chrome-")
            stdout, _ = run_chrome([str(CHROME), "--headless", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
                                    "--disable-background-networking", "--virtual-time-budget=3000", "--window-size=1300,900",
                                    "--dump-dom", probe.as_uri()])
            shutil.rmtree(profile, ignore_errors=True)
            m = re.search(r'<pre id="out">(.*?)</pre>', stdout.decode("utf-8", "ignore"), re.S)
            self.assertTrue(m, name)
            import html as h
            data = json.loads(h.unescape(m.group(1)))
            self.assertTrue(data["scroll"], f"{name} scrolls sideways")
            self.assertGreater(len(data["res"]), 10, name)
            self.assertEqual({k: round(v, 2) for k, v in data["res"].items() if v < 4.5}, {}, name)


if __name__ == "__main__":
    unittest.main()
