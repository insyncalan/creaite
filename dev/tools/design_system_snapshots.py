"""Refresh dev/design-system: static snapshots of each real screen, the stylesheet they were drawn with, and which version they came from.

Why: mockups start from these pages and this stylesheet, so they cannot drift from the app (dev/design-system/README.md). A snapshot is
only as right as the code it was taken from, so every file says which commit that was (SNAPSHOT.json, and a comment in each page).
Take snapshots from the RELEASE LINE the next release is built on (the integration gate, or main once a release is cut), never from an
older line. Run from any checkout; --repo names the checkout whose app is photographed (default: this one):
    python3 dev/tools/design_system_snapshots.py --repo /path/to/checkout-of-the-release-line [--out dev/design-system]
Uses the UI audit's throwaway vault and headless Chrome (cdp.py); development only, never touches a real vault."""
import argparse
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
# (name, js to open it or None, address to open it when it has no js). Meeting-bound pages (minutes, prep, client report) need a
# meeting and are not snapshotted.
VIEWS = [("today", "go('today')", None), ("work", "go('work')", None), ("review", "go('review')", None), ("projects", "go('projects')", None),
         ("cockpit", None, "#cockpit=ABC"), ("milestones", None, "#milestones=ABC"), ("intake", "go('inbox')", None), ("files", "go('files')", None),
         ("people", "go('people')", None), ("person", None, "#person=Alan%20Carter"), ("activity", "go('activity')", None),
         ("settings", "go('settings')", None), ("help", "go('help')", None), ("reports", None, "#reports"),
         ("reporting", None, "#reporting=ABC"), ("weekly", None, "#weekly=ABC&week=2026-10-16"), ("notes", None, "#notes=ABC")]
FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&family=Schibsted+Grotesk:'
         'wght@700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap">')
TOGGLE = "<script>document.addEventListener('keydown',e=>{if(e.key==='d'&&e.altKey){const r=document.documentElement;r.dataset.theme=r.dataset.theme==='dark'?'light':'dark'}})</script>"


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(HERE.parent))
    ap.add_argument("--out", default=str(HERE / "design-system"))
    ap.add_argument("--label", default="", help="the branch name to record (a detached checkout has none)")
    a = ap.parse_args()
    repo, out = Path(a.repo).resolve(), Path(a.out).resolve()
    sys.path.insert(0, str(repo / "dev" / "tools"))
    sys.path.insert(0, str(repo / "dev" / "tests"))
    import proc_guard
    import ui_audit
    from cdp import Browser
    (out / "pages").mkdir(parents=True, exist_ok=True)
    (out / "shots").mkdir(parents=True, exist_ok=True)
    css = (repo / "system/templates/dashboard/style.css").read_text()
    (out / "style.snapshot.css").write_text(css)
    info = {"commit": git(repo, "rev-parse", "--short", "HEAD"), "branch": a.label or git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
            "version_file": (repo / "VERSION").read_text().strip(), "subject": git(repo, "log", "-1", "--format=%s")[:100],
            "taken": date.today().isoformat(), "palette": "creaite", "mode": "light", "viewport": "1400x1000"}
    (out / "SNAPSHOT.json").write_text(json.dumps(info, indent=1) + "\n")
    note = ("A static snapshot of the real %s screen (creaite palette, light, fictional sample data) drawn by style.snapshot.css, taken from "
            + "commit " + info["commit"] + " (" + info["branch"] + ", VERSION file " + info["version_file"] + ") on " + info["taken"]
            + ". Alt+D toggles dark. Copy this file to start a mockup; see ../README.md.")
    v, proc, base = ui_audit.start_server()
    try:
        b = Browser(1400, 1000)
        try:
            b.goto(base + "/")
            b.wait("typeof go==='function' && LIVE", timeout=30)
            b.call("Page.setBypassCSP", enabled=True)
            theme = "(()=>{const r=document.documentElement; r.dataset.palette='creaite'; r.dataset.theme='light'; return true})()"
            b.eval(theme)
            for name, js, addr in VIEWS:
                if js:
                    b.eval(js)
                    time.sleep(0.7)
                else:
                    b.goto(base + "/" + addr)
                    b.wait("typeof go==='function' && LIVE", timeout=30)
                    time.sleep(1.5)
                    b.eval(theme)
                b.screenshot(str(out / "shots" / f"{name}-light.png"))
                b.eval("(()=>{document.documentElement.dataset.theme='dark';return true})()")
                time.sleep(0.2)
                b.screenshot(str(out / "shots" / f"{name}-dark.png"))
                b.eval(theme)
                html = b.eval("(()=>{const c=document.documentElement.cloneNode(true);"
                              "c.querySelectorAll('script,style,link[rel=stylesheet],meta').forEach(s=>s.remove());return c.outerHTML})()")
                head = '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + FONTS + \
                       '<link rel="stylesheet" href="../style.snapshot.css">'
                html = html[:html.index("<head>") + 6] + head + html[html.index("</head>"):]
                (out / "pages" / f"{name}.html").write_text("<!doctype html>\n<!-- " + (note % name) + " -->\n"
                                                            + html.replace("</body>", TOGGLE + "</body>"))
                print(name, len(html))
            print("errors:", list(b.errors)[:3])
        finally:
            b.close()
    finally:
        proc_guard.stop(proc, grace=10)
        v.cleanup()


if __name__ == "__main__":
    main()
