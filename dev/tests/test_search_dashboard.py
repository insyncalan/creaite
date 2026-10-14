"""The Files search box and the ⌘K search row in headless Chrome (BL-07).

Run: python3 dev/tests/test_search_dashboard.py   (needs Google Chrome; skipped otherwise)
The page is served by the live server in a throwaway vault, and a script injected at the end of the page types into the
boxes and reads what the page shows (the same technique as LivePageTests in test_live_server.py).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import CHROME, populate  # noqa: E402
from test_live_server import free_port  # noqa: E402
from test_search import put  # noqa: E402
from test_search_live import FAKE_CLAUDE  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

SCRIPT = r"""
<script>
(async()=>{ const out={errors:[]}, wait=ms=>new Promise(r=>setTimeout(r,ms)), el=id=>document.getElementById(id);
  const calls=[], realFetch=window.fetch; window.fetch=(u,o)=>{ if(String(u).startsWith("/api/search")) calls.push(String(u)); return realFetch(u,o); };
  const until=async(f,n=80)=>{ for(let i=0;i<n&&!f();i++) await wait(100); };      // real work (a stand-in claude) takes real time
  const type=async(box,text,ms=700)=>{ box.value=text; box.dispatchEvent(new Event("input",{bubbles:true})); await wait(ms); };
  const rows=()=>[...document.querySelectorAll("#vsResults .vsr")].map(r=>r.querySelector(".vst").textContent.replace(/\s+/g," ").trim());
  const chips=()=>[...document.querySelectorAll("#vsChips .vschip")].map(c=>c.firstChild.textContent);
  try{
    await checkLive(); out.live=LIVE&&viaServer(); go("files"); const inp=el("vsInput");
    // a plain search: grouped, highlighted, the file list stands aside
    await type(inp,"data access");
    out.groups=[...document.querySelectorAll("#vsResults .vsh")].map(h=>h.textContent.replace(/\s+/g," ").trim());
    out.rows=rows(); out.mark=!!document.querySelector("#vsResults .vss mark"); out.listHidden=document.querySelector("#v-files .files").hidden; out.note=el("vsNote").textContent;
    // chips come from the words, and removing one searches again without it
    await type(inp,"risks ABC data"); out.chips=chips(); out.riskRows=rows();
    document.querySelector('#vsChips [data-vschip="0"]').click(); await wait(700); out.afterRemove=[chips(),rows().length>out.riskRows.length];
    // an item opens in its panel
    await type(inp,"Escalate"); const item=[...document.querySelectorAll("#vsResults .vsr")].find(r=>r.textContent.includes("ABC-A-"));
    out.itemRow=!!item; item.click(); await wait(100); out.opened=[VIEW,!!CUR,CUR&&CUR.k];
    closePanel(); go("files");
    // a meeting opens in the preview, scrolled to the match
    await type(el("vsInput"),"chase"); const meet=[...document.querySelectorAll("#vsResults .vsr")].find(r=>r.textContent.includes("Steering"));
    out.meetRow=!!meet; meet.click(); await wait(500); out.preview=[el("searchPrev").open,el("spName").textContent,!!document.querySelector("#spText mark")]; el("searchPrev").close();
    // debounce: three quick keystrokes make one request
    calls.length=0; for(const t of ["da","dat","data"]){ el("vsInput").value=t; el("vsInput").dispatchEvent(new Event("input",{bubbles:true})); await wait(40); } await wait(600); out.calls=calls.length;
    // Esc clears the box and brings the file list back
    el("vsInput").dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true})); out.cleared=[el("vsInput").value,document.querySelector("#v-files .files").hidden,el("vsResults").hidden,chips().length];
    // nothing found
    await type(el("vsInput"),"zzzqqq"); out.empty=document.querySelector("#vsResults .empty")?.textContent||"";
    el("vsInput").value=""; el("vsInput").dispatchEvent(new Event("input",{bubbles:true})); await wait(300);
    // ⌘K: a search row from three characters, with the top five results beneath the jump list
    openCk(); const ck=el("cmdkIn"); ck.value="da"; ck.dispatchEvent(new Event("input")); out.ckShort=[...document.querySelectorAll("#cmdkList button")].some(b=>b.textContent.startsWith("Search the vault"));
    ck.value="data access"; ck.dispatchEvent(new Event("input")); await wait(700);
    out.ck=[...document.querySelectorAll("#cmdkList button")].map(b=>b.textContent); out.ckGroups=[...document.querySelectorAll("#cmdkList .grp")].map(g=>g.textContent);
    const sr=[...document.querySelectorAll("#cmdkList button")].find(b=>b.textContent.startsWith("Search the vault")); sr.click(); await wait(700);
    out.ckOpened=[VIEW,el("vsInput").value,rows().length>0,document.activeElement===el("vsInput")];
    // (headless Chrome's simulated clock doesn't advance a streamed download, so the answer's stream is stood in for here;
    // the server's side of it is tested in test_search_live.py)
    const realFetch2=window.fetch; window.fetch=async(u,o)=>{ if(u!=="/api/search/ask") return realFetch2(u,o); const body=JSON.parse(o.body);
      const stream=new ReadableStream({start(c){ const enc=new TextEncoder(), send=e=>c.enqueue(enc.encode("data: "+JSON.stringify(e)+"\n\n"));
        send({type:"sources",question:body.q,sources:[{name:"2026-09-25 Steering.md",stem:"2026-09-25 Steering",path:"projects/ABC Example Programme/minutes/2026-09-25 Steering.md",kind:"minutes"},{name:"ABC-D-005",path:"",kind:"item",table:"decisions",project:"ABC"}]});
        if(body.q.includes("slowly")){ send({type:"text",text:"Looking."}); o.signal.addEventListener("abort",()=>c.error(new DOMException("aborted","AbortError"))); return; }
        send({type:"text",text:"Go-live moved because data access slipped [2026-09-25 Steering.md › Decisions]. See [ABC-D-005]."}); send({type:"done",session:"sess-search-1",chat:"sess-search-1",run:body.run}); c.close(); }});
      return new Response(stream,{status:200,headers:{"Content-Type":"text/event-stream"}}); };
    // ask creaite (BL-88): no Ask row in the results, the button beside the bar instead; Enter runs a question; citations become links; nothing is saved until Continue
    await type(el("vsInput"),"why did go-live move?"); out.askRow=[document.querySelectorAll("#vsResults [data-vsask]").length,el("vsResults").textContent.includes("Ask Claude"),el("vsAskBtn").dataset.state];
    await type(el("vsInput"),"data access"); out.askBtnPlain=el("vsAskBtn").dataset.state;
    await type(el("vsInput"),"why did go-live move?");
    el("vsInput").dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true})); await until(()=>ASKQ.done,30);
    out.answer=[!el("vsAnswer").hidden,el("vsAnswer").textContent.includes("Go-live moved because data access slipped"),[...document.querySelectorAll("#vsAnswer a.cite")].map(a=>[a.dataset.citefile||a.dataset.citeitem,a.dataset.citekind||""]),!!document.querySelector("#vsAnswer [data-vscontinue]")];
    out.chatsBefore=(await api("/api/chats")).chats.length;
    document.querySelector("#vsAnswer a.cite[data-citefile]").click(); await wait(500); out.citePreview=[el("searchPrev").open,el("spName").textContent]; el("searchPrev").close();
    document.querySelector("#vsAnswer a.cite[data-citeitem]").click(); await wait(100); out.citeItem=[VIEW,!!CUR]; closePanel(); go("files");
    document.querySelector("#vsAnswer [data-vscontinue]").click(); await wait(800);
    out.continued=[ASKCHAT,ASKSESSION,el("chat").classList.contains("on"),[...document.querySelectorAll("#chLog .msg")].map(m=>m.textContent.slice(0,40))]; closeChat();
    // Stop ends a slow answer; the answer card says so
    await type(el("vsInput"),"tell me slowly why?"); el("vsInput").dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true})); await until(()=>ASKQ.said&&ASKQ.said.length,30);
    out.running=[!!document.querySelector("#vsAnswer [data-vsstop]"),el("vsAnswer").textContent.includes("Reading your files")||el("vsAnswer").textContent.includes("Looking.")];
    document.querySelector("#vsAnswer [data-vsstop]").click(); await until(()=>ASKQ.done,30); out.stopped=[el("vsAnswer").textContent.includes("Stopped."),!!document.querySelector("#vsAnswer [data-vscontinue]")];
    document.querySelector("#vsAnswer [data-vsdismiss]").click(); out.dismissed=el("vsAnswer").hidden;
    // ⌘K offers Ask for a question
    openCk(); el("cmdkIn").value="why did go-live move?"; el("cmdkIn").dispatchEvent(new Event("input")); out.ckAsk=[...document.querySelectorAll("#cmdkList button")][0].textContent; el("cmdk").close();
    // without the live server: a plain note
    const was=LIVE; LIVE=false; vsClear(); await type(el("vsInput"),"data access",400); out.offline=el("vsNote").textContent; LIVE=was;
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre); })();
</script>
"""


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
class SearchPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        put(v, f"{ABC}/minutes/2026-09-25 Steering.md", "# Decisions\nGo-live moves because data access slipped.\n\n# Action Items\nSara to chase the CIO.")
        put(v, f"{ABC}/reports/2026-10-02 Weekly report.md", "Weekly report. Build slipping; data access is the blocker.")
        put(v, f"{ABC}/documents/Plans/2026-08-01 Plan.md", "Delivery plan. Data access request goes to the client.")
        inject = v.root / "inject.html"
        inject.write_text(SCRIPT)
        port = free_port()
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        env = {**os.environ, "CREAITE_PORT": str(port), "CREAITE_TEST_INJECT": str(inject), "CREAITE_CLAUDE": str(fake)}
        server = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
                    break
                except OSError:
                    time.sleep(0.1)
            profile = tempfile.mkdtemp(prefix="creaite-chrome-")
            cmd = [str(CHROME), "--headless", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
                   "--disable-component-update", "--disable-background-networking", "--virtual-time-budget=40000",
                   "--dump-dom", f"http://127.0.0.1:{port}/"]
            try:
                out = subprocess.run(cmd, capture_output=True, timeout=90).stdout
            except subprocess.TimeoutExpired as e:
                out = e.stdout or b""
            shutil.rmtree(profile, ignore_errors=True)
        finally:
            server.terminate()
            server.wait(timeout=10)
        m = re.search(r'<pre id="result">(.*?)</pre>', out.decode("utf-8", "ignore"), re.S)
        assert m, "the page didn't finish the scripted steps"
        cls.r = json.loads(m.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&"))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_no_script_errors(self):
        self.assertEqual(self.r["errors"], [])
        self.assertTrue(self.r["live"])

    def test_files_box_groups_results_and_hides_the_list(self):
        r = self.r
        self.assertEqual([g.split(" · ")[0].strip() for g in r["groups"]], ["Items", "Meetings", "Reports", "Documents"])
        self.assertTrue(any("2026-10-02 Weekly report" in x and "Report" in x for x in r["rows"]))
        self.assertTrue(any("2026-08-01 Plan" in x and "Document · internal" in x for x in r["rows"]))   # labelled
        self.assertTrue(r["mark"])
        self.assertTrue(r["listHidden"])
        self.assertIn("result", r["note"])

    def test_chips_are_removable(self):
        r = self.r
        self.assertEqual(r["chips"], ["Risks", "ABC"])
        self.assertEqual(len(r["riskRows"]), 1)
        self.assertEqual(r["afterRemove"], [["ABC"], True])

    def test_results_open_where_they_belong(self):
        r = self.r
        self.assertTrue(r["itemRow"])
        self.assertEqual(r["opened"], ["work", True, "actions"])
        self.assertTrue(r["meetRow"])
        self.assertEqual(r["preview"], [True, "2026-09-25 Steering.md", True])

    def test_debounce_escape_and_empty(self):
        r = self.r
        self.assertEqual(r["calls"], 1)
        self.assertEqual(r["cleared"], ["", False, True, 0])
        self.assertIn("Nothing found", r["empty"])

    def test_command_palette_row(self):
        r = self.r
        self.assertFalse(r["ckShort"])                                    # two characters: no search row
        row = r["ck"].index("Search the vault for “data access”…Files")
        self.assertGreater(row, 0)                                         # under the existing jump list
        self.assertIn("Search results", r["ckGroups"])
        self.assertTrue(0 < len(r["ck"]) - row - 1 <= 5)                   # the top five results follow it
        self.assertEqual(r["ckOpened"], ["files", "data access", True, True])

    def test_ask_row_answer_citations_continue_and_stop(self):
        r = self.r
        self.assertEqual(r["askRow"], [0, False, "question"])               # BL-88: no Ask row in the results; the button is ready for a question
        self.assertEqual(r["askBtnPlain"], "ready")                         # and available for any other text
        shown, text, cites, cont = r["answer"]
        self.assertTrue(shown and text and cont)
        self.assertEqual(cites[0], [f"{ABC}/minutes/2026-09-25 Steering.md", "minutes"])      # the file the answer cited
        self.assertTrue(any(c[0].startswith("ABC-") for c in cites))                          # and an item ID
        self.assertEqual(r["chatsBefore"], 0)                                                 # a search answer isn't a chat
        self.assertEqual(r["citePreview"], [True, "2026-09-25 Steering.md"])
        self.assertEqual(r["citeItem"], ["work", True])
        self.assertEqual(r["continued"][:3], ["sess-search-1", "sess-search-1", True])
        self.assertTrue(r["continued"][3][0].startswith("why did go-live move"))              # the question, then the answer
        self.assertTrue(r["continued"][3][1].startswith("Go-live moved because data access"))
        self.assertEqual(r["running"][0], True)
        self.assertEqual(r["stopped"], [True, False])
        self.assertTrue(r["dismissed"])
        self.assertEqual(r["ckAsk"], "ask creaite: “why did go-live move?”An answer with sources")

    def test_a_plain_note_without_the_live_server(self):
        self.assertIn("Live server needed", self.r["offline"])


if __name__ == "__main__":
    unittest.main()
