"""Milestone editing (BL-23) and images in the Current state editor (BL-12, BL-63) from the project page, end to end.

Run: python3 dev/tests/test_dashboard_milestones.py   (needs Google Chrome; skipped otherwise)

Same approach as test_dashboard_editing.py: the real dashboard in headless Chrome with an in-memory file layer.
The page adds, edits, marks done, rebaselines and removes milestones; the proposals it writes are then applied
with tracker.py and checked in the database. One operation per milestone, as two unapplied edits of the same row
are a conflict by design.
"""
import json
import re
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_result import page_result  # noqa: E402
from test_dashboard import CHROME, new, populate, today  # noqa: E402
from test_tracker import Vault  # noqa: E402


def d(n):
    return (today() + timedelta(days=n)).isoformat()


def ddmm(iso):
    return f"{iso[8:10]}-{iso[5:7]}-{iso[:4]}"


SCRIPT = r"""
<script>
(async()=>{
  const FILES=JSON.parse(document.getElementById("seed").textContent), wait=ms=>new Promise(r=>setTimeout(r,ms)), set=(id,v)=>{ document.getElementById(id).value=v; }, out={errors:[]};
  VW={ async read(p){ if(!(p in FILES)) throw new Error("not found: "+p); return FILES[p]; }, async write(p,t){ FILES[p]=t; },
       async remove(p){ delete FILES[p]; }, async exists(p){ return p in FILES; }, async append(p,t){ FILES[p]=(FILES[p]||"")+t; },
       async upload(p,blob){ FILES[p]="base64:"+await new Promise(r=>{ const fr=new FileReader(); fr.onload=()=>r(String(fr.result).split(",")[1]); fr.readAsDataURL(blob); }); } };
  VSTATE="ok"; needVault=async()=>true;   /* the page's own vault check can finish late and reset the fake vault (slow CI) */
  try{
    // BL-186: the cockpit card shows the Plan; its pencil opens the page, and the editor (#mvPeek) saves each change on its own
    const chg=(id,v)=>{ const e=document.getElementById(id); e.value=v; e.dispatchEvent(new Event("change",{bubbles:true})); };
    MVAUD="int";   /* BL-244 made Client the first-visit view; this test edits in Internal view (Movement, internal milestones), as BL-186's did */
    go("cockpit","ABC");
    out.rows=[...new Set([...document.querySelectorAll("#v-cockpit [data-mvedit]")].map(e=>e.dataset.mvedit))];
    out.addPencil=!!document.querySelector('#v-cockpit [data-msnew]');
    out.pencil=document.getElementById("mvPencil").getAttribute("aria-label");
    // add: the page opens with an empty editor; the name saves it, then its agreed date (a calendar pick) and description
    openNewMilestone("DEF"); await wait(60); out.addOpen=!!MV.add&&document.activeElement.id==="mvName";
    set("mvName","Go-live"); await mvAddCommit(); await wait(1100);   /* the next proposal file sorts after this one (names are by the second) */
    mvDatePicked("mvAgr",toIso("%NEWDATE%")); await MVQ; out.descArea=document.getElementById("mvDesc").tagName;
    chg("mvDesc","First line\nSecond line"); await MVQ;
    // edit: rename, description, progress (a figure set by hand)
    openMilestone("ABC-M-004"); await wait(60); out.baseShown=document.getElementById("mvPeek").textContent.includes("Agreed (the baseline)");
    out.descBefore=document.getElementById("mvDesc").value; chg("mvName","Training delivered"); await MVQ;
    chg("mvDesc","  All trainers signed off\n\nAnd the sandbox is ready  "); await MVQ; chg("mvNum","40"); await MVQ;
    // Achieved (no forecast date: today, and 100%)
    openMilestone("ABC-M-003"); await wait(60); mvSetState(mvGet("ABC","ABC-M-003"),"achieved"); await mvAct("flok"); await MVQ;
    // rebaseline from Movement: who agreed it and why are required; it is staged for Review (approved here, as Review would)
    mvOpenPage("DEF","move"); await wait(60); MV.sel="DEF-M-001"; MV.rb={id:"DEF-M-001",date:toIso("%REBASE%"),why:"",with:[]}; renderMilestones();
    await mvRebaseline(); out.noReason=document.getElementById("mvRbErr").textContent;
    MV.rb.with=["Sara Example"]; renderMilestones(); set("mvRbWhy","Client moved the pilot window"); await mvRebaseline(); await wait(20);
    for(const [k,t] of Object.entries(FILES)) if(k.includes("dashboard")&&t.includes('"rebaseline"')) FILES[k]=t.replace(/"decision": "pending"/g,'"decision": "approved"');
    // cancel: linked actions are unlinked, with Undo
    openMilestone("ABC-M-001"); await wait(60); out.cancelPeek=MV.peek; await mvAct("cancel"); await VQ; await wait(50);
    go("cockpit","ABC"); out.after=[...document.querySelectorAll("#v-cockpit [data-mvedit]")].map(e=>e.dataset.mvedit);
    out.unlinked=A.filter(a=>a.p==="ABC"&&a.ms==="ABC-M-001").length;
    // Images in the editor (BL-63): inserted after the paragraph holding the caret, captioned, one removed again
    const png=Uint8Array.from(atob("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="),c=>c.charCodeAt(0));
    const file=n=>new File([png],n,{type:"image/png"});
    out.noPanel=!document.querySelector('[data-addimg]'); go("cockpit","ABC"); startCurEdit("ABC"); await wait(20);
    const ed=document.getElementById("curEd"), first=ed.querySelector("p"), r=document.createRange(); r.selectNodeContents(first); r.collapse(false); getSelection().removeAllRanges(); getSelection().addRange(r);
    await insertImage(file("Arch diagram.png")); const cap=ed.querySelector('figure[data-ref^="new:"] figcaption'); cap.textContent="Target architecture"; cap.dispatchEvent(new Event("input",{bubbles:true}));
    await insertImage(file("Scrap.png")); const scrap=[...ed.querySelectorAll('figure[data-ref^="new:"]')].pop(); scrap.querySelector(".cimgdel").click();
    await insertImage(new File(["x"],"notes.txt",{type:"text/plain"}));          // refused
    out.edMd=htmlToMd(ed); out.badType=document.getElementById("snackT").textContent;
    needVault=async()=>true;   // the page's own vault check finishes late and can reset the fake vault's state mid-save
    await saveCurEdit(); await VQ; await wait(50);
    out.imgs=document.querySelectorAll("#v-cockpit .curtext .cimg img").length;
    out.order=[...(document.querySelector("#v-cockpit .curtext .curpane[data-pane='1'] .curin")||document.querySelector("#v-cockpit .curtext")).children].map(e=>e.tagName==="FIGURE"?"img:"+e.querySelector("figcaption").textContent:e.tagName);
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  out.files=FILES;
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
</script>
"""


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
class MilestoneEditingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        v.propose("more-milestones", [
            new("milestones", 1, project="ABC", name="Go-live", source="Alan (cx-edit)"),          # no dates
            new("milestones", 2, project="ABC", name="Training", baseline_date=d(40), forecast_date=d(40),
                source="Alan (cx-edit)")])
        v.run("apply")
        v.run(script="build_dashboard.py")
        cls.newdate, cls.rebase = d(60), d(45)
        html = (v.root / "dashboard.html").read_text(encoding="utf-8")
        script = SCRIPT.replace("%NEWDATE%", ddmm(cls.newdate)).replace("%REBASE%", ddmm(cls.rebase))
        harness = v.root / "harness.html"
        seed = {"projects/ABC Example Programme/CLAUDE.md":
                (v.root / "projects/ABC Example Programme/CLAUDE.md").read_text(encoding="utf-8")}
        seed_tag = '<script type="application/json" id="seed">' + json.dumps(seed).replace("</", "<\\/") + "</script>"
        harness.write_text(html.replace("</body>", seed_tag + script + "</body>"), encoding="utf-8")
        # dev-test-steadiness: in real time, waiting for the result (a virtual-time budget ran out under load)
        cls.result = json.loads(page_result(harness.as_uri()))
        import base64
        for path, body in cls.result["files"].items():
            target = v.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if body.startswith("base64:"):
                target.write_bytes(base64.b64decode(body[7:]))
            else:
                target.write_text(body, encoding="utf-8")
        cls.apply_out = v.run("apply").stdout

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def ms(self):
        return {m["id"]: m for m in self.v.rows("milestones")}

    def test_page(self):
        r = self.result
        self.assertEqual(r["errors"], [])
        self.assertIn("ABC-M-002", r["rows"])
        self.assertFalse(r["addPencil"])                              # BL-186: the pencil opens the page; it no longer adds
        self.assertEqual(r["pencil"], "Open milestones: Plan and Movement")
        self.assertTrue(r["addOpen"] and r["baseShown"])
        self.assertEqual(r["descArea"], "TEXTAREA")                   # a multiline field
        self.assertEqual(r["descBefore"], "")
        self.assertIn("Choose who agreed it", r["noReason"])
        self.assertNotIn("ABC-M-001", r["after"])                     # gone from the page at once
        self.assertEqual(r["unlinked"], 0)

    def test_applied(self):
        self.assertNotIn("conflict", self.apply_out.lower())
        ms = self.ms()
        added = next(m for m in ms.values() if m["project"] == "DEF" and m["name"] == "Go-live")
        self.assertEqual((added["baseline_date"], added["forecast_date"], added["status"]), (self.newdate, self.newdate, "Planned"))
        self.assertEqual((ms["ABC-M-004"]["name"], ms["ABC-M-004"]["percent_complete"]), ("Training delivered", 40))   # BL-29
        self.assertEqual((ms["ABC-M-003"]["status"], ms["ABC-M-003"]["actual_date"], ms["ABC-M-003"]["percent_complete"]),
                         ("Done", today().isoformat(), 100))                              # Achieved: today and 100% (BL-186)
        self.assertIsNone(added["percent_complete"])                                          # not set
        self.assertEqual(added["description"], "First line\nSecond line")                     # multiline, kept as typed
        self.assertEqual(ms["ABC-M-004"]["description"], "All trainers signed off\n\nAnd the sandbox is ready")   # trimmed
        self.assertIsNone(ms["ABC-M-003"]["description"])                                     # untouched milestones stay empty
        self.assertEqual(ms["DEF-M-001"]["baseline_date"], self.rebase)
        self.assertEqual(ms["ABC-M-001"]["status"], "Cancelled")       # never deleted
        self.assertEqual([a["id"] for a in self.v.rows("actions") if a["milestone"] == "ABC-M-001"], [])

    def test_images_in_the_editor(self):
        r = self.result
        self.assertTrue(r["noPanel"])                                     # the Add image panel has gone (BL-63)
        md = r["edMd"]
        self.assertRegex(md, r"^[^\n]+\n\n!\[Target architecture\]\(new:[a-z0-9]+\)\n\n")   # right after the first paragraph
        self.assertEqual(md.count("!["), 3)              # the sample's two (one file missing) and the new one; the removed one gone
        self.assertIn("only PNG or JPEG", r["badType"])
        self.assertEqual(r["imgs"], 2)                                    # shown in place at once
        self.assertEqual(r["order"][:2], ["P", "img:Target architecture"])
        name = f"{today().isoformat()}-target-architecture.png"
        folder = self.v.root / "projects/ABC Example Programme"
        self.assertTrue((folder / "images" / name).read_bytes().startswith(b"\x89PNG"))
        memory = (folder / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertRegex(memory, r"Escalation is planned for [^\n]+\n\n!\[Target architecture\]\(images/" + re.escape(name) +
                         r"\)\n\nUAT preparation")                          # where it was placed, not at the end
        self.assertEqual(memory.count("![Delivery plan](images/plan.png)"), 1)
        self.assertEqual(list((self.v.root / "system/staging/uploads").glob("*")), [])   # staged copy removed
        self.v.run(script="build_dashboard.py")
        html = (self.v.root / "dashboard.html").read_text(encoding="utf-8")
        data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S).group(1))
        abc = next(p for p in data["projects"] if p["code"] == "ABC")
        self.assertIn("Target architecture", [i["alt"] for i in abc["images"]])

    def test_rebaseline_reason_logged(self):
        notes = [r for r in self.v.rows("change_log") if r["item_id"] == "DEF-M-001" and r["field"] == "note"]
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0]["new_value"].startswith("Client moved the pilot window. Agreed with Sara Example. Decision DEF-D-"))   # BL-186
        self.assertTrue(any(d["made_by"] == "Sara Example" and d["project"] == "DEF" for d in self.v.rows("decisions")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
