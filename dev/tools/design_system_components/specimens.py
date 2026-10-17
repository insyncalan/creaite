"""Part of the design system pipeline (dev/design-system/README.md). Run from the dev repo root:
    DS_REPO=<checkout of the release line> python3 dev/tools/design_system_components/specimens.py
DS_REPO is the checkout whose app is photographed (default: this repo). Output goes to dev/design-system/. Development only."""
import os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[2]            # dev/
DSOUT = str(HERE / "design-system") + "/"
DSREPO = Path(os.environ.get("DS_REPO", str(HERE.parent))).resolve()
import time, json, base64
sys.path.insert(0, str(DSREPO / "dev" / "tools"))
from cdp import Browser
R=DSOUT
SPEC=[("h1","files","#v-files h1"),("h2","today",".card h2, #v-today h2"),("h3","today","#v-today h3, .th"),("sub","files","#v-files .sub"),("crumb","cockpit",".crumb"),("hhead","projects",".hhead"),
("btn","files","#filesRefresh"),("btn-primary","weekly",".btn.primary"),("btn-quiet","activity",".btn.quiet"),("mini","review",".mini"),("ib-sm","activity",".ib.sm"),("ib-bd","work","#moreBtn"),("iconbtn","today",".iconbtn"),("seg","work","#wlay"),
("vchip","files","#fquick"),("tag","review",".tag"),("chip","cockpit",".chip"),("fchip","work",".fchip"),("badge","today",".rail .badge"),("ftype","files",".ftype"),("kbd","files","kbd"),("health","projects",".health"),
("input","files","#fsName"),("select","files","#fsType"),("dwrap","files",".dwrap"),("check","settings","input[type=checkbox]"),("switch","settings",".switch"),("srow","settings",".srow"),("setgroup","settings","#v-settings .card"),
("tabs","work","#wtabs"),("tree","files","#tree"),("card","settings","#v-settings .card"),("tbl","files","#filesTbl"),("tbl-work","work","#v-work .tbl"),("empty","activity",".empty"),("toolbar","work","#v-work .toolbar")]
GET="(sel,max)=>{const L=[...document.querySelectorAll(sel)].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&e.outerHTML.length<max});const e=L[0];if(!e)return null;const c=getComputedStyle(e),r=e.getBoundingClientRect();return {html:e.outerHTML.replace(/\\s+/g,' '),w:Math.round(r.width),h:Math.round(r.height),pad:c.padding,mar:c.margin,gap:c.gap,maxw:c.maxWidth,fs:c.fontSize,fw:c.fontWeight,br:c.borderRadius,bd:c.border.slice(0,40)}}"
b=Browser(1400,1000); out={}
try:
    cur=None
    for key,pg,sel in SPEC:
        if pg!=cur: b.goto("file://"+R+"pages/%s.html"%pg); time.sleep(0.5); cur=pg
        r=b.eval("(%s)(%s,%d)"%(GET,json.dumps(sel),9000))
        out[key]={"page":pg,"sel":sel,"d":r}
        print(key, "OK" if r else "MISSING", (r or {}).get("w"), (r or {}).get("h"))
    # container metrics
    cm={}
    for k,pg,sel in [("view","files",".view:not([hidden])"),("wrapmax","files",".view:not([hidden]) .wrapmax"),("bar","files",".bar"),("rail","files",".rail"),("tbl","files","#filesTbl"),("card","settings","#v-settings .card"),("peek","work","#panel")]:
        b.goto("file://"+R+"pages/%s.html"%pg); time.sleep(0.4)
        cm[k]=b.eval("(()=>{const e=document.querySelector(%s);if(!e)return null;const c=getComputedStyle(e),r=e.getBoundingClientRect();return {w:Math.round(r.width),h:Math.round(r.height),pad:c.padding,mar:c.margin,maxw:c.maxWidth,bg:c.backgroundColor}})()"%json.dumps(sel))
    out["_containers"]=cm
    json.dump(out,open(R+"specimens.json","w"))
    print(json.dumps(cm,indent=0)[:900]); print(list(b.errors)[:3])
finally: b.close()
