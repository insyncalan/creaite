"""Part of the design system pipeline (dev/design-system/README.md). Run from the dev repo root:
    DS_REPO=<checkout of the release line> python3 dev/tools/design_system_components/capture_live.py
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
OUT=DSOUT
v, proc, base = ui_audit.start_server()
data={"icons":[], "outlines":{}, "dyn":{}}
def clip(b, sel, path, pad=10, scale=2):
    r=b.eval("(()=>{const e=document.querySelector(%s);if(!e)return null;const r=e.getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()"%json.dumps(sel))
    if not r or r[2]<2 or r[3]<2: return None
    x,y,w,h=r; x=max(0,x-pad); y=max(0,y-pad); w+=2*pad; h+=2*pad
    d=b.call("Page.captureScreenshot",format="png",clip={"x":x,"y":y,"width":w,"height":h,"scale":scale})["data"]
    open(path,"wb").write(base64.b64decode(d)); return [round(w),round(h)]
def tm(b,mode): b.eval("(()=>{const r=document.documentElement; r.dataset.palette='creaite'; r.dataset.theme=%s; return true})()"%json.dumps(mode))
try:
    b = Browser(1400, 1000)
    try:
        b.goto(base + "/"); b.wait("typeof go==='function' && LIVE", timeout=30); b.call("Page.setBypassCSP", enabled=True)
        # icons
        names=b.eval("Object.keys(ICONS)")
        for n in names: data["icons"].append([n, b.eval("ic(%s)"%json.dumps(n))])
        # outlines of each view
        OUTL="""(root,maxd)=>{const walk=(e,d)=>{const kids=[...e.children].filter(c=>!['SCRIPT','STYLE'].includes(c.tagName)&&!c.hidden);const t=e.tagName.toLowerCase()+(e.id?'#'+e.id:'')+(typeof e.className==='string'&&e.className?'.'+e.className.trim().split(/\\s+/).slice(0,3).join('.'):'');if(d>=maxd)return {t,n:kids.length};const out=[];let last=null,rep=0;for(const k of kids){const kt=k.tagName+(typeof k.className==='string'?k.className.trim().split(/\\s+/)[0]:'');if(last===kt){rep++;continue}if(rep){out[out.length-1].x=rep+1;rep=0}last=kt;out.push(walk(k,d+1))}if(rep)out[out.length-1].x=rep+1;return {t,c:out}};return walk(document.querySelector(root),0)}"""
        for view,js in [("today","go('today')"),("work","go('work')"),("review","go('review')"),("projects","go('projects')"),("intake","go('inbox')"),("files","go('files')"),("people","go('people')"),("activity","go('activity')"),("settings","go('settings')"),("help","go('help')")]:
            b.eval(js); time.sleep(0.6)
            vid={"intake":"v-inbox"}.get(view,"v-"+view)
            data["outlines"][view]=b.eval("(%s)(%s,4)"%(OUTL,json.dumps("#"+vid)))
        for mode in ("light","dark"):
            tm(b,mode); time.sleep(0.3)
            # full page dark/light shots for each pattern page
            for view,js in [("today","go('today')"),("work","go('work')"),("review","go('review')"),("projects","go('projects')"),("intake","go('inbox')"),("files","go('files')"),("people","go('people')"),("activity","go('activity')"),("settings","go('settings')"),("help","go('help')")]:
                b.eval(js); time.sleep(0.5); b.screenshot(OUT+"shots/%s-%s.png"%(view,mode))
            b.eval("go('work')"); time.sleep(0.6)
            def dyn(name,setup,sel,teardown="document.body.click()",pad=10):
                try:
                    b.eval(setup); time.sleep(0.45)
                    r=clip(b,sel,OUT+"components/%s-%s.png"%(name,mode),pad)
                    data["dyn"].setdefault(name,{})[mode]=r
                except Exception as e: data["dyn"].setdefault(name,{})[mode]="ERR "+str(e)[:80]
                try: b.eval(teardown); time.sleep(0.25)
                except Exception: pass
            dyn("menu-list","go('work');document.getElementById('stBtn').click()","#stMenu")
            dyn("menu-filter","go('work');document.getElementById('moreBtn').click()","#moreMenu")
            dyn("peek-panel","go('work');(document.querySelector('#v-work .tbl a[data-id]')||document.querySelector('#v-work .tbl tbody tr a')).click()","#panel","document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))",0)
            dyn("toast","snack('Saved. Undo is open for 10 seconds.',()=>{})","#snack")
            dyn("calendar-popup","go('files');document.querySelector('[data-cal=fsFrom]').click()",".cal")
            dyn("dialog-customise-sidebar","document.getElementById('railCust').showModal()","#railCust","document.getElementById('railCust').close()",0)
            dyn("command-palette","document.getElementById('cmdk').showModal()","#cmdk","document.getElementById('cmdk').close()",0)
            dyn("dialog-board","go('work');document.getElementById('boardDlg').showModal()","#boardDlg","document.getElementById('boardDlg').close()",0)
            dyn("dialog-generate","document.getElementById('genDlg').showModal()","#genDlg","document.getElementById('genDlg').close()",0)
            dyn("ask-panel","document.getElementById('askBtn').click()","#chat","document.getElementById('chatClose').click()",0)
            dyn("live-alert","go('today');document.getElementById('liveAlert').classList.add('on')","#liveAlert","document.getElementById('liveAlert').classList.remove('on')")
            dyn("dialog-person","document.getElementById('personDlg').showModal()","#personDlg","document.getElementById('personDlg').close()",0)
        tm(b,"light")
        json.dump(data,open(OUT+"live-data.json","w"))
        print("icons",len(data["icons"])); print(json.dumps(data["dyn"],indent=0)[:1800]); print(list(b.errors)[:3])
    finally: b.close()
finally:
    proc_guard.stop(proc, grace=10); v.cleanup()
