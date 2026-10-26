"""Refresh dev/design-system: static snapshots of each real screen, the stylesheet they were drawn with, and which version they came from.

Why: mockups start from these pages and this stylesheet, so they cannot drift from the app (dev/design-system/README.md). A snapshot is
only as right as the code it was taken from, so every file says which commit that was (SNAPSHOT.json, and a comment in each page).
Take snapshots from the RELEASE LINE the next release is built on (the integration gate, or main once a release is cut), never from an
older line. Run from any checkout; --repo names the checkout whose app is photographed (default: this one):
    python3 dev/tools/design_system_snapshots.py --repo /path/to/checkout-of-the-release-line [--out dev/design-system]
Also writes blank.html (the empty app shell) and gallery.html (the same shell with the curated sections of design_system_gallery.html); no
review.html: go() maps review, inbox and intake to the one Intake page.
Uses the UI audit's throwaway vault and headless Chrome (cdp.py); development only, never touches a real vault."""
import argparse
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
GALLERY_SRC = Path(__file__).resolve().with_name("design_system_gallery.html")  # the curated gallery sections, kept by hand
VIEWS = [("today", "go('today')"), ("work", "go('work')"), ("projects", "go('projects')"),
         ("cockpit", None), ("milestones", None), ("intake", "go('inbox')"), ("files", "go('files')"), ("people", "go('people')"),
         ("activity", "go('activity')"), ("settings", "go('settings')"), ("help", "go('help')")]
FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500&family=Schibsted+Grotesk:'
         'wght@700;800&family=Source+Sans+3:wght@400;500;600;700&display=swap">')
TOGGLE = ("<script>document.addEventListener('keydown',e=>{if(e.key==='d'&&e.altKey){const r=document.documentElement;"
          "r.dataset.theme=r.dataset.theme==='dark'?'light':'dark'}})</script>")


BLANK_BODY = ('<div class="wrapmax"><h1>Page title</h1><div class="sub">One line saying what this page is for.</div>'
              '<div class="toolbar" style="margin-top:8px"><button class="btn primary">Main action</button>'
              '<button class="btn">Button</button></div></div>')


def wrap(html, note, css, tail=""):
    """One snapshot file: doctype, the provenance comment, a head that links the stylesheet, and the Alt+D toggle."""
    head = '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + FONTS + \
           '<link rel="stylesheet" href="' + css + '">'
    html = html[:html.index("<head>") + 6] + head + html[html.index("</head>"):]
    return "<!doctype html>\n<!-- " + note + " -->\n" + html.replace("</body>", TOGGLE + tail + "</body>")


def git(repo, *a):
    """Run one git command in the repo and return its trimmed standard output."""
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True).stdout.strip()


def main():
    """Take the design-system snapshots of the running app (see ../README.md)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(HERE.parent))
    ap.add_argument("--out", default=str(HERE / "design-system"))
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
    info = {"commit": git(repo, "rev-parse", "--short", "HEAD"), "branch": git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
            "version_file": (repo / "VERSION").read_text().strip(), "subject": git(repo, "log", "-1", "--format=%s")[:100],
            "taken": date.today().isoformat(), "palette": "creaite", "mode": "light",
            "viewport": "1400x1000"}
    (out / "SNAPSHOT.json").write_text(json.dumps(info, indent=1) + "\n")
    note = ("A static snapshot of the real %s screen (creaite palette, light, fictional sample data) drawn by style.snapshot.css, "
            "taken from "
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
            for name, js in VIEWS:
                if js:
                    b.eval(js)
                    time.sleep(0.7)
                else:
                    b.goto(base + ("/#cockpit=ABC" if name == "cockpit" else "/#milestones=ABC"))
                    b.wait("typeof go==='function' && LIVE", timeout=30)
                    time.sleep(1.2)
                    b.eval(theme)
                b.screenshot(str(out / "shots" / f"{name}-light.png"))
                html = b.eval("(()=>{const c=document.documentElement.cloneNode(true);"
                              "c.querySelectorAll('script,style,link[rel=stylesheet],meta').forEach(s=>s.remove());return c.outerHTML})()")
                (out / "pages" / f"{name}.html").write_text(wrap(html, note % name, "../style.snapshot.css"))
                print(name, len(html))
            # blank.html and gallery.html: the same shell, the Files view shown, its content swapped (the shell is never hand-edited)
            b.eval("go('files')")
            time.sleep(0.7)
            subs = {"{commit}": info["commit"], "{version}": info["version_file"], "{taken}": info["taken"]}
            body, _, tail = GALLERY_SRC.read_text().partition("\n<!--TAIL-->\n")
            for k, val in subs.items():
                body = body.replace(k, val)
            where = (" taken from commit " + info["commit"] + " (" + info["branch"] + ", VERSION file " + info["version_file"]
                     + ") on " + info["taken"])
            for name, inner, tl, text in (
                    ("blank", BLANK_BODY, "", "A blank page in the real app shell (rail, top bar), drawn by style.snapshot.css," + where
                     + ". Copy it and build inside #v-files. Alt+D toggles dark. See DESIGN-SYSTEM.md."),
                    ("gallery", body, tail, "The design system gallery: real markup, real classes, drawn by style.snapshot.css. Shell"
                     + where + "; the gallery sections inside #v-files are curated by hand in dev/tools/design_system_gallery.html.")):
                html = b.eval("(()=>{const c=document.documentElement.cloneNode(true);"
                              "c.querySelectorAll('script,style,link[rel=stylesheet],meta').forEach(s=>s.remove());"
                              "c.querySelector('#v-files').innerHTML=" + json.dumps(inner) + ";return c.outerHTML})()")
                (out / (name + ".html")).write_text(wrap(html, text, "style.snapshot.css", tl))
                print(name, len(html))
            (out / "pages" / "review.html").unlink(missing_ok=True)  # a page that no longer exists
            print("errors:", list(b.errors)[:3])
        finally:
            b.close()
    finally:
        proc_guard.stop(proc, grace=10)
        v.cleanup()


if __name__ == "__main__":
    main()
