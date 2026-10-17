"""Refresh dev/design-system/pages and shots: a static snapshot of each real screen (creaite palette, light, fictional sample data).

Why: mockups start from these pages and the real style.css, so they cannot drift from the app (dev/design-system/README.md).
Run from the dev repo root after a release changes how a screen looks:  python3 dev/tools/design_system_snapshots.py
Uses the UI audit's throwaway vault and headless Chrome (cdp.py); development only, never touches the dev repo's own vault."""
import sys, time, json
from pathlib import Path
DEV = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEV / "tools"))
sys.path.insert(0, str(DEV / "tests"))
import ui_audit, proc_guard
from cdp import Browser
ROOT=str(DEV / "design-system") + "/"
VIEWS=[("today","go('today')"),("work","go('work')"),("review","go('review')"),("projects","go('projects')"),("cockpit",None),("milestones",None),("intake","go('inbox')"),("files","go('files')"),("people","go('people')"),("activity","go('activity')"),("settings","go('settings')"),("help","go('help')")]
HEAD='''<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&family=Schibsted+Grotesk:wght@700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="../../../system/templates/dashboard/style.css">'''
v, proc, base = ui_audit.start_server()
try:
    b = Browser(1400, 1000)
    try:
        b.goto(base + "/"); b.wait("typeof go==='function' && LIVE", timeout=30); b.call("Page.setBypassCSP", enabled=True)
        b.eval("(()=>{const r=document.documentElement; r.dataset.palette='creaite'; r.dataset.theme='light'; return true})()")
        for name, js in VIEWS:
            if js: b.eval(js); time.sleep(0.7)
            else:
                b.goto(base + ("/#cockpit=ABC" if name=="cockpit" else "/#milestones=ABC")); b.wait("typeof go==='function' && LIVE", timeout=30); time.sleep(1.2)
                b.eval("(()=>{const r=document.documentElement; r.dataset.palette='creaite'; r.dataset.theme='light'; return true})()")
            b.screenshot(ROOT+"shots/%s-light.png"%name)
            html = b.eval("""(()=>{const c=document.documentElement.cloneNode(true);c.querySelectorAll('script,style,link[rel=stylesheet],meta').forEach(s=>s.remove());
              c.querySelectorAll('#snack,.ask-panel').forEach(s=>{});return c.outerHTML})()""")
            head_end = html.index("</head>") if "</head>" in html else None
            if head_end is not None:
                html = html[:html.index("<head>")+6] + HEAD + html[head_end:]
            toggle = "<script>document.addEventListener('keydown',e=>{if(e.key==='d'&&e.altKey){const r=document.documentElement;r.dataset.theme=r.dataset.theme==='dark'?'light':'dark'}})</script>"
            html = "<!doctype html>\n<!-- A static snapshot of the real %s page (creaite palette, light, fictional sample data), drawn by the app's own style.css. Alt+D toggles dark. Copy this file to start a mockup; see ../README.md. -->\n"%name + html.replace("</body>", toggle+"</body>")
            open(ROOT+"pages/%s.html"%name, "w").write(html)
            print(name, len(html))
        print("errors:", list(b.errors)[:3])
    finally:
        b.close()
finally:
    proc_guard.stop(proc, grace=10); v.cleanup()
