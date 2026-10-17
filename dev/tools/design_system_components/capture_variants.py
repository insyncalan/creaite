"""Part of the design system pipeline (dev/design-system/README.md): each screen at 900 px wide, and in the Cursor palette (the two palettes the
theme tests cover), light and dark; and a date field with a typed mistake. Run from the dev repo root:
    DS_REPO=<checkout of the release line> python3 dev/tools/design_system_components/capture_variants.py
Output goes to dev/design-system/shots/ and components/. Development only."""
import base64
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
DSOUT = str(HERE / "design-system") + "/"
DSREPO = Path(os.environ.get("DS_REPO", str(HERE.parent))).resolve()
sys.path[:0] = [str(DSREPO / "dev/tools"), str(DSREPO / "dev/tests")]
import proc_guard  # noqa: E402
import ui_audit  # noqa: E402
from cdp import Browser  # noqa: E402

VIEWS = [("today", "go('today')"), ("work", "go('work')"), ("review", "go('review')"), ("projects", "go('projects')"), ("intake", "go('inbox')"),
         ("files", "go('files')"), ("people", "go('people')"), ("activity", "go('activity')"), ("settings", "go('settings')"), ("help", "go('help')")]
v, proc, base = ui_audit.start_server()


def tm(b, pal, mode):
    b.eval("(()=>{const r=document.documentElement;r.dataset.palette=%s;r.dataset.theme=%s;return true})()" % (json.dumps(pal), json.dumps(mode)))


res = {}
try:
    b = Browser(900, 800)
    try:
        b.goto(base + "/")
        b.wait("typeof go==='function' && LIVE", timeout=30)
        b.call("Page.setBypassCSP", enabled=True)
        for name, js in VIEWS:
            tm(b, "creaite", "light")
            b.eval(js)
            time.sleep(0.6)
            b.screenshot(DSOUT + f"shots/{name}-900-light.png")
        b.resize(1400, 1000)
        for mode in ("light", "dark"):
            for name, js in VIEWS:
                tm(b, "Cursor", mode)
                b.eval(js)
                time.sleep(0.6)
                b.screenshot(DSOUT + f"shots/{name}-cursor-{mode}.png")
        # a date field with a typed mistake
        tm(b, "creaite", "light")
        b.eval("go('files')")
        time.sleep(0.5)
        b.eval("(()=>{const i=document.getElementById('fsFrom');i.focus();i.value='31-02-26';i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}));i.blur()})()")
        time.sleep(0.5)
        for mode in ("light", "dark"):
            tm(b, "creaite", mode)
            r = b.eval("(()=>{const e=document.querySelector('#v-files .toolbar');const r=e.getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()")
            x, y, w, h = r
            d = b.call("Page.captureScreenshot", format="png", clip={"x": x - 8, "y": y - 8, "width": w + 16, "height": h + 76, "scale": 2})["data"]
            Path(DSOUT + f"components/date-invalid-{mode}.png").write_bytes(base64.b64decode(d))
        print("ok", list(b.errors)[:3])
    finally:
        b.close()
finally:
    proc_guard.stop(proc, grace=10)
    v.cleanup()
