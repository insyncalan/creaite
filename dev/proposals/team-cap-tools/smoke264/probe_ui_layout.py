"""#337 (layout numbers from the design trial): People, Settings tick rows and the Activity By column at 1400 and 900 px.

  python3 -I probe_ui_layout.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]

Headless Chrome over a scratch vault (fictional data). One staged item is rejected through the live server and applied, so
Activity has a "Rejected in review" row. At each width:
  - People: the Overdue column is on screen and there is no sideways scroll on the page or its scrollers;
  - Settings: the label column of each tick row (Week ahead shows, Weekend ...) is at least 150 px wide and its label is on
    one line, and the tick labels themselves keep room (one line, not clipped);
  - Activity: "Rejected in review" in the By column is on one line.
Expected on 2.6.4 (base 2.6.3): all PASS. With --control the People check FAILS at both widths (on 2.6.3 Overdue sits past the
screen edge at 900 and the table scrolls sideways at 1400), the tick-row label column FAILS at 900 (42 px wide, four lines for
"What the check reads") and the By column FAILS at 900 (two lines); the tick labels and the 1400 px By column pass on both.
Not checked: pencil colour, 12 px chart text, 24 px targets (also in #337), and any width other than 1400 and 900.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import rec, action  # noqa: E402

TICKS = """[...document.querySelectorAll('#v-settings label.settick')].map(l=>{const r=l.getBoundingClientRect(); const cs=getComputedStyle(l); return {t:l.innerText.trim(), w:Math.round(r.width), h:Math.round(r.height), lh:parseFloat(cs.lineHeight)||0, sw:l.scrollWidth, cw:l.clientWidth}})"""
ROWS = """[...document.querySelectorAll('#v-settings .srow')].filter(r=>r.querySelector('.setticks')).map(r=>{const l=r.children[0]; const sp=l.querySelector('span'); const rng=document.createRange(); rng.selectNodeContents(sp); const lines=new Set([...rng.getClientRects()].map(x=>Math.round(x.top))).size; return {label:sp.innerText.trim().slice(0,30), w:Math.round(l.getBoundingClientRect().width), lines}})"""


def main():
    a = C.parse(__doc__)
    v = C.V("pLayout", identity="Sam Reid", calendar=False)
    try:
        v.start(1400, 1000)
        b = v.b
        p = v.stage("2026-10-20-0900-act", [action(1, "Reject me for the Activity page")])
        item = json.loads(p.read_text())["items"][0]
        c, r = v.pj("/api/review/reject", {"rows": [{"file": p.name, "ref": 1, "expect": v.fingerprint("item_fp", item)}], "reason": "other"})
        c2, o = v.run("tracker.py", "apply")
        print("set-up: reject", c, (r.get("message") if isinstance(r, dict) else r), "| apply exit", c2)
        v.run("build_dashboard.py")
        v.reload_page()
        for width in (1400, 900):
            b.resize(width, 1000)
            b.pump(0.8)
            b.eval("go('people')")
            b.pump(1.5)
            pp = b.eval("""(()=>{const v=document.getElementById('v-people'); const t=v.querySelector('table'); const hs=[...t.querySelectorAll('th')].filter(h=>h.getBoundingClientRect().width>0); const od=hs.find(h=>/overdue/i.test(h.innerText)); const r=od&&od.getBoundingClientRect();
              return {inner:innerWidth, docSW:document.documentElement.scrollWidth, scrollers:[v,t.parentElement].map(e=>[e.scrollWidth,e.clientWidth]), overdue:r?[Math.round(r.left),Math.round(r.right)]:null}})()""")
            ok = bool(pp["overdue"]) and pp["overdue"][1] <= pp["inner"] and pp["docSW"] <= pp["inner"] and all(x <= y + 1 for x, y in pp["scrollers"])
            rec(f"337 People at {width}px: Overdue on screen, no sideways scroll", ok, str(pp))
            b.eval("go('settings')")
            b.pump(1.2)
            seen = {}
            for q in ("Week ahead", "Weekend", ""):
                v.settings_search(q)
                tk = b.eval(TICKS)
                if q:
                    okt = bool(tk) and all(x["h"] <= (x["lh"] or 20) * 1.8 + 8 and x["sw"] <= x["cw"] + 1 and x["w"] >= 30 for x in tk)
                    rec(f"337 Settings '{q}' tick labels at {width}px keep room", okt, json.dumps(tk)[:300])
                for row in b.eval(ROWS):
                    seen[row["label"]] = row
            rec(f"337 Settings tick rows at {width}px: label column wide enough and on one line",
                bool(seen) and all(x["w"] >= 150 and x["lines"] == 1 for x in seen.values()), "; ".join(f"{k}: {x['w']} px, {x['lines']} line(s)" for k, x in seen.items()))
            b.eval("go('activity')")
            b.pump(1.5)
            by = b.eval("""[...document.querySelectorAll('#actTbl tbody tr')].filter(r=>/Rejected in review/.test(r.innerText)).slice(0,3).map(r=>{const td=r.children[3]; const rr=td.getBoundingClientRect(); const rng=document.createRange(); rng.selectNodeContents(td); const lines=new Set([...rng.getClientRects()].map(x=>Math.round(x.top))).size; return {text:td.innerText.trim(), w:Math.round(rr.width), rowh:Math.round(r.getBoundingClientRect().height), lines}})""")
            rec(f"337 Activity By column at {width}px: 'Rejected in review' on one line", bool(by) and all(x["lines"] == 1 for x in by), json.dumps(by))
        print("console errors:", b.errors[:3])
    finally:
        v.close()
    return C.finish(a)


if __name__ == "__main__":
    C.run(main)
