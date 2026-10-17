"""Part of the design system pipeline (dev/design-system/README.md). Run from the dev repo root:
    DS_REPO=<checkout of the release line> python3 dev/tools/design_system_components/capture_states.py
DS_REPO is the checkout whose app is photographed (default: this repo). Output goes to dev/design-system/. Development only."""
import os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[2]            # dev/
DSOUT = str(HERE / "design-system") + "/"
DSREPO = Path(os.environ.get("DS_REPO", str(HERE.parent))).resolve()
import time, json, base64
sys.path.insert(0, str(DSREPO / "dev" / "tools"))
from cdp import Browser
OUT=DSOUT
P="file://"+OUT+"pages/%s.html"
# (key, page, selector, states) ; 'disabled' sets the attribute, others force pseudo classes
SPEC=[("btn","files","#filesRefresh",["default","hover","focus","active","disabled"]),
("btn-primary","weekly",".btn.primary",["default","hover","focus","active","disabled"]),
("btn-quiet","files","#filesRefresh",["default","hover","focus","active"]),
("mini","today",".mini",["default","hover","focus","active","disabled"]),
("ib","activity",".ib.sm",["default","hover","focus","active"]),
("ib-bd","work","#moreBtn",["default","hover","focus","active"]),
("vchip","files","#fquick .vchip[aria-pressed=false]",["default","hover","focus","active"]),
("vchip-on","files","#fquick .vchip[aria-pressed=true]",["default","hover","focus"]),
("input","files","#fsName",["default","hover","focus","disabled"]),
("select","files","#fsType",["default","hover","focus","disabled"]),
("tree-row","files","#tree button.l1",["default","hover","focus"]),
("table-row","files","#filesTbl tbody tr",["default","hover"]),
("rail-item","files",".rail .nv:not([aria-current])",["default","hover","focus"]),
("rail-item-current","today",".rail .nv[aria-current=page]",["default","hover"]),
("tab","work",".tabs button[aria-selected=false]",["default","hover","focus"]),
("tab-on","work",".tabs button[aria-selected=true]",["default","hover","focus"]),
("link","files","#filesTbl a",["default","hover","focus"])]
ONLY=sys.argv[1:]
if ONLY: SPEC=[x for x in SPEC if x[0] in ONLY]
b=Browser(1400,1000); res={}
def pseudo(nid,states):
    f=[]
    if "hover" in states: f.append("hover")
    if "focus" in states: f+=["focus","focus-visible"]
    if "active" in states: f.append("active")
    b.call("CSS.forcePseudoState",nodeId=nid,forcedPseudoClasses=f)
try:
    for mode in ("light","dark"):
        cur=None
        for key,pg,sel,states in SPEC:
            if pg!=cur:
                b.goto(P%pg); time.sleep(0.8); cur=pg
                b.eval("(()=>{const r=document.documentElement;r.dataset.theme=%s;return true})()"%json.dumps(mode)); time.sleep(0.2)
                b.call("DOM.enable"); b.call("CSS.enable"); b.call("DOM.getDocument",depth=0)
            if key=='btn-quiet': b.eval("document.querySelector('#filesRefresh').classList.add('quiet')")
            tagged=b.eval("(()=>{document.querySelectorAll('[data-dsx]').forEach(e=>e.removeAttribute('data-dsx'));const e=[...document.querySelectorAll(%s)].find(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0});if(!e)return false;e.setAttribute('data-dsx','1');return true})()"%json.dumps(sel))
            if not tagged: res.setdefault(key,{})[mode]='missing'; continue
            doc=b.call("DOM.getDocument",depth=0)["root"]["nodeId"]
            sel0=sel; sel='[data-dsx]'
            q=b.call("DOM.querySelector",nodeId=doc,selector=sel)
            nid=q.get("nodeId")
            if not nid: res.setdefault(key,{})[mode]="missing"; continue
            b.eval("document.querySelector(%s).scrollIntoView({block:'center'})"%json.dumps(sel)); time.sleep(0.1)
            for st in states:
                dis = st=="disabled"
                if dis: b.eval("document.querySelector(%s).disabled=true;document.querySelector(%s).setAttribute('aria-disabled','true')"%(json.dumps(sel),json.dumps(sel)))
                else: b.eval("document.querySelector(%s).disabled=false;document.querySelector(%s).removeAttribute('aria-disabled')"%(json.dumps(sel),json.dumps(sel)))
                pseudo(nid,[] if dis or st=="default" else [st]); time.sleep(0.12)
                r=b.eval("(()=>{const e=document.querySelector(%s);const r=e.getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()"%json.dumps(sel))
                x,y,w,h=r; pad=8
                d=b.call("Page.captureScreenshot",format="png",clip={"x":max(0,x-pad),"y":max(0,y-pad),"width":min(w,520)+2*pad,"height":min(h,80)+2*pad,"scale":2})["data"]
                open(OUT+"components/state-%s-%s-%s.png"%(key,st,mode),"wb").write(base64.b64decode(d))
                pseudo(nid,[])
            b.eval("document.querySelector(%s).disabled=false;document.querySelector(%s).removeAttribute('aria-disabled')"%(json.dumps(sel),json.dumps(sel)))
            res.setdefault(key,{})[mode]=states
    old=json.load(open(OUT+"states-data.json")) if ONLY else {}; old.update(res); json.dump(old,open(OUT+"states-data.json","w")); print(res); print(list(b.errors)[:3])
finally: b.close()
