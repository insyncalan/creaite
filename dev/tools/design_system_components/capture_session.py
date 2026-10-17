"""Part of the design system pipeline (dev/design-system/README.md). Needs a vault with a meeting and a stand-in Claude, so it uses the
hand-check Session of the checkout DS_REPO (the same one the hand checks use): the Prep page, the client report, an AI suggestion card
and ask creaite while it works. Run from the dev repo root:
    DS_REPO=<checkout of the release line> python3 dev/tools/design_system_components/capture_session.py
Output goes to dev/design-system/. Development only."""
import base64
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
DSOUT = str(HERE / "design-system") + "/"
DSREPO = Path(os.environ.get("DS_REPO", str(HERE.parent))).resolve()
sys.path[:0] = [str(DSREPO / "dev/tools"), str(DSREPO / "dev/tests"), str(DSREPO / "dev/tests/handchecks")]
import handcheck  # noqa: E402
from cdp import Browser  # noqa: E402

snap = json.loads((Path(DSOUT) / "SNAPSHOT.json").read_text())
FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&family=Schibsted+Grotesk:'
         'wght@700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap">')
TOGGLE = "<script>document.addEventListener('keydown',e=>{if(e.key==='d'&&e.altKey){const r=document.documentElement;r.dataset.theme=r.dataset.theme==='dark'?'light':'dark'}})</script>"
note = ("A static snapshot of the real %s screen (creaite palette, light, fictional sample data) drawn by style.snapshot.css, taken from commit "
        + snap["commit"] + " (" + snap["branch"] + ", VERSION file " + snap["version_file"] + ") on " + snap["taken"] + ". Alt+D toggles dark.")
theme = "(()=>{const r=document.documentElement;r.dataset.palette='creaite';r.dataset.theme='light';return true})()"
s = handcheck.Session(keep=False)
res = {}


def save_page(b, name):
    html = b.eval("(()=>{const c=document.documentElement.cloneNode(true);c.querySelectorAll('script,style,link[rel=stylesheet],meta').forEach(s=>s.remove());return c.outerHTML})()")
    head = '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + FONTS + '<link rel="stylesheet" href="../style.snapshot.css">'
    html = html[:html.index("<head>") + 6] + head + html[html.index("</head>"):]
    (Path(DSOUT) / "pages" / f"{name}.html").write_text("<!doctype html>\n<!-- " + (note % name) + " -->\n" + html.replace("</body>", TOGGLE + "</body>"))
    b.screenshot(DSOUT + f"shots/{name}-light.png")
    b.eval("document.documentElement.dataset.theme='dark'")
    time.sleep(0.2)
    b.screenshot(DSOUT + f"shots/{name}-dark.png")
    b.eval(theme)


def clip(b, sel, path, pad=10):
    b.eval("(()=>{const e=document.querySelector(%s);if(e)e.scrollIntoView({block:'center'})})()" % json.dumps(sel))
    time.sleep(0.3)
    r = b.eval("(()=>{const e=document.querySelector(%s);if(!e)return null;const r=e.getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()" % json.dumps(sel))
    if not r or r[2] < 2:
        return None
    x, y, w, h = r
    d = b.call("Page.captureScreenshot", format="png", clip={"x": max(0, x - pad), "y": max(0, y - pad), "width": w + 2 * pad, "height": min(h, 700) + 2 * pad, "scale": 2})["data"]
    Path(path).write_bytes(base64.b64decode(d))
    return [round(w), round(h)]


try:
    s.open()
    b = Browser(1400, 1000)
    try:
        def load(h):
            b.goto(s.base + "/" + h)
            b.wait("typeof go==='function' && LIVE", timeout=40)
            b.call("Page.setBypassCSP", enabled=True)
            time.sleep(2.0)
            b.eval(theme)
        load("")
        b.eval("[...document.querySelectorAll('button')].filter(e=>/^Prep$/.test(e.textContent.trim()))[0].click()")
        time.sleep(2.0)
        save_page(b, "prep")
        res["prep"] = b.eval("location.hash")
        load("#client-report=FAL/2026-10-16/Northgate%20Energy")
        save_page(b, "clientreport")
        # the minutes view: stage a meeting as cx-minutes does, then open its draft by its address
        import subprocess
        from datetime import date, timedelta
        import test_v210
        day = (date.today() - timedelta(days=2)).isoformat()
        (s.vault / "inbox" / f"{day} FAL Steering committee.vtt").write_text(test_v210.VTT, encoding="utf-8")
        (s.vault / "system/staging/drafts/meeting.json").write_text(json.dumps(test_v210.meeting_spec(day, 2)), encoding="utf-8")
        r = subprocess.run([sys.executable, "-I", "system/scripts/minutes.py", "stage", "system/staging/drafts/meeting.json"], cwd=s.vault, capture_output=True, text=True)
        res["minutes-stage"] = r.returncode
        from urllib.parse import quote
        load("#minutes=" + quote(f"system/staging/drafts/{day} Steering committee.html", safe=""))
        res["minutes-view"] = b.eval("VIEW")
        if res["minutes-view"] == "minutes":
            save_page(b, "minutes")
        # a real error in the debug log, so the error banner shows
        subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0,'system/scripts'); import log; log.error('server','Example failure for the design system')"], cwd=s.vault, capture_output=True, text=True)
        load("")
        time.sleep(2.0)
        for mode in ("light", "dark"):
            b.eval("document.documentElement.dataset.theme=%s" % json.dumps(mode))
            time.sleep(0.2)
            res.setdefault("error-banner", {})[mode] = clip(b, "#errBanner:not([hidden])", DSOUT + f"components/error-banner-{mode}.png", 8)
        b.eval(theme)
        # an AI suggestion card (the stand-in answers)
        load("#weekly=FAL&week=2026-10-16")
        n = b.eval("document.querySelectorAll('.sheet-spark').length")
        for i in range(n):
            b.eval("document.querySelectorAll('.sheet-spark')[%d].click()" % i)
            time.sleep(3.0)
            txt = b.eval("(()=>{const e=document.querySelector('.sheet-redraft');return e?e.innerText:''})()")
            if txt and "no words" not in txt:
                for mode in ("light", "dark"):
                    b.eval("document.documentElement.dataset.theme=%s" % json.dumps(mode))
                    time.sleep(0.2)
                    res.setdefault("ai-suggestion", {})[mode] = clip(b, ".sheet-redraft", DSOUT + f"components/ai-suggestion-{mode}.png")
                b.eval(theme)
                break
            b.eval("(()=>{const e=document.querySelector('.sheet-redraft button');if(e)e.click()})()")
            time.sleep(0.3)
        # ask creaite while it works (the stand-in's slow mode)
        (s.vault / "fake_mode.txt").write_text("slow")
        load("")
        b.eval("document.getElementById('askBtn').click()")
        time.sleep(0.6)
        b.eval("(()=>{const t=document.getElementById('chIn');t.value='What is overdue on Falcon?';t.dispatchEvent(new Event('input',{bubbles:true}));document.getElementById('chSend').click()})()")
        time.sleep(3.0)
        for mode in ("light", "dark"):
            b.eval("document.documentElement.dataset.theme=%s" % json.dumps(mode))
            time.sleep(0.2)
            res.setdefault("ask-running", {})[mode] = clip(b, "#chat", DSOUT + f"components/ask-running-{mode}.png", 0)
        b.eval(theme)
        print(json.dumps(res), list(b.errors)[:3])
    finally:
        b.close()
finally:
    try:
        s.close()
    except Exception as e:
        print("close", e)
