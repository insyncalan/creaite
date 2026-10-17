"""Part of the design system pipeline (dev/design-system/README.md). Run from the dev repo root:
    DS_REPO=<checkout of the release line> python3 dev/tools/design_system_components/capture_composites.py
DS_REPO is the checkout whose app is photographed (default: this repo). Output goes to dev/design-system/. Development only."""
import os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[2]            # dev/
DSOUT = str(HERE / "design-system") + "/"
DSREPO = Path(os.environ.get("DS_REPO", str(HERE.parent))).resolve()
import time, json, base64
R=str(DSREPO)+"/"
sys.path.insert(0, R+"dev/tools"); sys.path.insert(0, R+"dev/tests")
import ui_audit, proc_guard
from cdp import Browser
OUT=DSOUT + "components/"
v, proc, base = ui_audit.start_server()
UNION="""(sels)=>{let L=1e9,T=1e9,R=-1,B=-1;for(const s of sels){const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();if(r.width<2)return null;L=Math.min(L,r.left);T=Math.min(T,r.top);R=Math.max(R,r.right);B=Math.max(B,r.bottom)}return [L,T,R-L,B-T]}"""
ITEMS=[("filter-bar","go('work')",["#v-work .toolbar","#wapplied"]),
("queue-group","go('review')",["#reviewBody .rgroup","#reviewBody .tbl"]),
("brief-band","go('today')",[".dayband .bandin"]),
("brief-section","go('today')",["#setupList"]),
("settings-group","go('settings')",["#settingsBody .card"]),
("detail-health","location.hash='#cockpit=ABC'",["#v-cockpit .card:nth-of-type(2)"]),
("milestone-card","location.hash='#milestones=ABC'",["#v-milestones .card"]),
("page-head-crumb","location.hash='#cockpit=ABC'",["#v-cockpit .crumb","#v-cockpit h1"]),
("notes-two-pane","location.hash='#notes=ABC'",["#v-notes .wrapmax"]),
("report-bar","location.hash='#weekly=ABC&week=2026-10-16'",["#v-weekly"]),
]
res={}
try:
    b=Browser(1400,1000)
    try:
        b.goto(base+"/"); b.wait("typeof go==='function' && LIVE", timeout=30); b.call("Page.setBypassCSP", enabled=True)
        for mode in ("light","dark"):
            for name,js,sels in ITEMS:
                try:
                    b.eval("(()=>{const r=document.documentElement;r.dataset.palette='creaite';r.dataset.theme=%s;return true})()"%json.dumps(mode))
                    b.eval(js); time.sleep(1.0)
                    r=b.eval("(%s)(%s)"%(UNION,json.dumps(sels)))
                    if not r: res.setdefault(name,{})[mode]="missing"; continue
                    x,y,w,h=r; pad=8; h=min(h,520)
                    d=b.call("Page.captureScreenshot",format="png",clip={"x":max(0,x-pad),"y":max(0,y-pad),"width":min(w,1120)+2*pad,"height":h+2*pad,"scale":1.5})["data"]
                    open(OUT+"comp-%s-%s.png"%(name,mode),"wb").write(base64.b64decode(d)); res.setdefault(name,{})[mode]=[round(w),round(h)]
                except Exception as e: res.setdefault(name,{})[mode]="ERR "+str(e)[:60]
        print(json.dumps(res)); print(list(b.errors)[:3])
    finally: b.close()
finally:
    proc_guard.stop(proc, grace=10); v.cleanup()
