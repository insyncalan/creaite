"""BL-255 prototype: the dashboard under a hash-based Content-Security-Policy, in report-only mode. Development only.

It changes nothing under system/. It builds the tests' sample vault (two fictional projects) in a scratch folder,
starts that vault's own live server through `serve` below, which wraps live_server.py at run time and adds
`Content-Security-Policy-Report-Only` to every HTML page and to the service worker, then visits every screen in headless
Chrome (dev/tools/cdp.py) and records each violation, by screen and by kind.

    python3.14 dev/tools/csp_proto.py run --out <scratch folder> [--policy bl255|strict]

`bl255` is BL-255's policy exactly (the app script's hash filled in); `strict` drops `'unsafe-inline'` from `style-src`
(the `<style>` block's hash instead), to count what that would take; `lean` drops `data:` and `blob:` from `img-src` and
`font-src`, to show which pages need them. Both add `'report-sample'` (it changes nothing that
is allowed, only fills in the reports) and a `report-uri`. Results: `<out>/csp-<policy>.json`, and the browser's own
reports (the service worker's included) in `<out>/reports-<policy>.jsonl`.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORT_PATH = "/csp-report"
BL255 = ("default-src 'self'; script-src {scripts} 'report-sample'; style-src 'self' 'unsafe-inline' 'report-sample'; "
         "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; "
         "form-action 'self'; frame-ancestors 'none'; report-uri " + REPORT_PATH)
STRICT = BL255.replace("'unsafe-inline' 'report-sample'", "{styles} 'report-sample'")
LEAN = BL255.replace("img-src 'self' data: blob:; font-src 'self' data:", "img-src 'self'; font-src 'self'")
POLICIES = {"bl255": BL255, "strict": STRICT, "lean": LEAN}
SCRIPT = re.compile(r"<script(\s[^>]*)?>(.*?)</script", re.S | re.I)
STYLE = re.compile(r"<style(\s[^>]*)?>(.*?)</style", re.S | re.I)
LISTEN = """(()=>{ window.__csp=[];
  const name=t=>t.tagName.toLowerCase()+(t.id?"#"+t.id:"")
    +(t.className&&typeof t.className==="string"?"."+t.className.trim().split(/\\s+/).join("."):"");
  document.addEventListener("securitypolicyviolation",e=>{ const t=e.target&&e.target.tagName?e.target:null;
    window.__csp.push({dir:e.effectiveDirective,uri:e.blockedURI,sample:(e.sample||"").slice(0,80),line:e.lineNumber,
      col:e.columnNumber,el:t?name(t):""}); },true); })();"""


def sha(text):
    """The CSP hash source for one inline block's exact text."""
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode() + "'"


def executed(attrs):
    """Whether a <script> with these attributes runs (a JSON data block does not, and needs no hash)."""
    m = re.search(r'type\s*=\s*"([^"]*)"', attrs or "", re.I)
    return not m or m.group(1).strip().lower() in ("", "text/javascript", "module", "application/javascript")


def hashes(html):
    """(script hashes, style hashes) of a page's inline blocks, as the browser sees them (each ends at the first close tag)."""
    scripts = [sha(body) for attrs, body in SCRIPT.findall(html) if executed(attrs)]
    styles = [sha(body) for _, body in STYLE.findall(html)]
    return scripts, styles


def policy_for(html, name):
    """The named policy with this page's hashes filled in ('none' when a page has no inline block of that kind)."""
    scripts, styles = hashes(html)
    return POLICIES[name].format(scripts=" ".join(scripts) or "'none'", styles=" ".join(styles))


def serve(vault, reports, name):
    """Run `vault`'s own live server, unchanged, with the report-only header added and a report endpoint (runs until killed)."""
    sys.path.insert(0, str(Path(vault) / "system" / "scripts"))
    import live_server
    handler = live_server.Handler
    send, do_post = handler.send, handler.do_POST

    def send_with_policy(self, code, body, ctype="application/json", extra=None):
        """The server's own `send`, plus the policy on HTML pages and the service worker."""
        if ctype in ("text/html", "text/javascript"):
            text = body.decode("utf-8") if isinstance(body, bytes) else body
            extra = {**(extra or {}), "Content-Security-Policy-Report-Only": policy_for(text, name)}
        return send(self, code, body, ctype, extra)

    def post_with_reports(self):
        """The browser's violation reports are written to `reports`; every other POST goes to the server as before."""
        if self.path != REPORT_PATH:
            return do_post(self)
        n = int(self.headers.get("Content-Length") or 0)
        with open(reports, "a", encoding="utf-8") as f:
            f.write(self.rfile.read(n).decode("utf-8", "replace").replace("\n", " ") + "\n")
        return send(self, 204, b"", "text/plain")

    handler.send, handler.do_POST = send_with_policy, post_with_reports
    live_server.main()


def build_vault(out):
    """The tests' sample vault (dev/tests/test_dashboard.populate), made under `out` and removed when this process ends."""
    os.environ["TMPDIR"] = str(out)
    import tempfile
    tempfile.tempdir = None
    sys.path.insert(0, str(REPO / "dev" / "tests"))
    from test_dashboard import populate
    from test_tracker import Vault
    v = Vault()
    populate(v)
    return v.root


def free_port():
    """A port nothing on this machine is using."""
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(vault, port, reports, name):
    """Start `serve` for `vault` in its own process and wait for /health."""
    import proc_guard
    proc = proc_guard.spawn([sys.executable, __file__, "serve", str(vault), str(reports), name],
                            env={**os.environ, "CREAITE_PORT": str(port)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
            return proc
        except OSError:
            time.sleep(0.1)
    proc_guard.stop(proc)
    raise RuntimeError("the live server didn't start")


def screens(settings, helps):
    """Every screen and main state, as (name, JavaScript that shows it). Settings categories and Help tabs come from the page."""
    out = [("Today", 'go("today")'), ("Projects", 'go("projects")'), ("Project page (ABC)", 'go("cockpit","ABC")'),
           ("Milestones", 'go("milestones")'), ("Milestone editor", 'go("milestones"); openMilestone("ABC-M-001")'),
           ("People", 'go("people")'), ("Person", 'go("person","Sara Example")'),
           ("Work: actions", 'WT="actions"; go("work")'), ("Work: action panel", 'WT="actions"; go("work"); openRecord("actions",A[0].id)'),
           ("Work: RAID panel", 'WT="raid"; go("work"); openRecord("raid",R[0].id)'),
           ("Work: decisions panel", 'WT="decisions"; go("work"); openRecord("decisions",DEC[0].id)'),
           ("Review", 'go("review")'), ("Intake", 'go("inbox")'), ("Files", 'go("files")'), ("Activity", 'go("activity")')]
    out += [(f"Settings: {title}", f'go("settings","{cat}")') for cat, title in settings]
    out += [(f"Help: {t}", f'go("help","{t}")') for t in helps]
    out += [("Command palette (Cmd+K)", 'go("today"); openCk(); $("#cmdkIn").value="a"; $("#cmdkIn").dispatchEvent(new Event("input"))'),
            ("ask creaite panel", '$("#cmdk").open&&$("#cmdk").close(); openChat()')]
    return out


def take(b):
    """The violations the page has recorded since the last call, and clears them."""
    return b.eval("(()=>{ const v=window.__csp||[]; window.__csp=[]; return v; })()") or []


def attach_image(b, out):
    """Attach a small PNG in ask creaite's panel (BL-100), which previews it through a blob: URL."""
    from test_dashboard import png
    pic = out / "attach.png"
    pic.write_bytes(png(64, 48, (11, 110, 127)))
    b.set_files("#chFile", [str(pic)])
    b.pump(1.5)
    return {"error": None, "violations": take(b)}


def visit(b, base, out):
    """Load the page, then show each screen; {screen: {"error": …, "violations": […]}}."""
    b.call("Page.addScriptToEvaluateOnNewDocument", source=LISTEN)
    b.goto(base + "/")
    b.wait("typeof go==='function' && LIVE", timeout=20)
    b.pump(1.5)
    found = {"Page load": {"error": None, "violations": take(b)}}
    cats = b.eval("SETCATS") or []
    helps = b.eval("HTABS") or []
    for name, js in screens(cats, helps):
        err = b.eval(f"(()=>{{ try {{ {js}; return null; }} catch(e) {{ return String(e); }} }})()")
        b.pump(0.8)
        found[name] = {"error": err, "violations": take(b)}
    found["ask creaite: image attached"] = attach_image(b, out)
    b.goto(base + "/offline")                     # the installed app's offline page (BL-86), served with its own policy
    b.pump(0.8)
    found["Offline page"] = {"error": None, "violations": take(b)}
    return found


def kind(v):
    """A plain name for what a violation is about."""
    d, uri, sample = v.get("dir", ""), v.get("uri", ""), v.get("sample", "")
    if sample.startswith("javascript:"):
        return "javascript: link"
    return {"script-src-attr": "inline handler (on*=)", "style-src-attr": "style= attribute",
            "style-src-elem": "<style> element" if uri == "inline" else "stylesheet",
            "script-src-elem": "inline <script>" if uri == "inline" else "script"}.get(d, f"{d} {uri.split(':')[0]}")


def summarise(found):
    """Counts by screen and by kind, with the distinct violations (deduplicated by kind, element and sample)."""
    by_screen, by_kind, distinct = {}, Counter(), {}
    for screen, r in found.items():
        by_screen[screen] = len(r["violations"])
        for v in r["violations"]:
            k = kind(v)
            by_kind[k] += 1
            distinct.setdefault((k, v.get("el", ""), v.get("sample", "")), {"kind": k, **v, "first_screen": screen})
    return {"by_screen": by_screen, "by_kind": dict(by_kind), "distinct": list(distinct.values()),
            "errors": {s: r["error"] for s, r in found.items() if r["error"]}}


def static_counts(html):
    """What the served page's source holds that a policy can see: inline blocks, style= and on*= attributes, javascript:."""
    scripts, styles = hashes(html)
    return {"executed_inline_scripts": len(scripts), "inline_style_blocks": len(styles), "script_hashes": scripts,
            "style_attr_in_source": len(re.findall(r'\sstyle=["\\]', html)),
            "on_attr_in_source": len(re.findall(r'\son[a-z]+=["\']', html)), "javascript_urls": html.count("javascript:")}


def run(out, name):
    """Build the vault, serve it under the policy, visit every screen, and write the results."""
    sys.path.insert(0, str(REPO / "dev" / "tools"))
    import proc_guard
    from cdp import Browser
    out.mkdir(parents=True, exist_ok=True)
    reports = out / f"reports-{name}.jsonl"
    reports.unlink(missing_ok=True)
    vault, port = build_vault(out), free_port()
    proc = start_server(vault, port, reports, name)
    try:
        page = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode("utf-8")
        with Browser(1400, 1000) as b:
            found = visit(b, f"http://127.0.0.1:{port}", out)
        time.sleep(1)
    finally:
        proc_guard.stop(proc, grace=5)
    result = {"policy": policy_for(page, name)[:400], "static": static_counts(page), **summarise(found), "raw": found,
              "reports_received": sum(1 for _ in reports.open()) if reports.exists() else 0}
    (out / f"csp-{name}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("by_kind", "by_screen", "errors", "reports_received", "static")}, indent=1))


def main():
    """`run` (the prototype) or `serve` (the wrapped live server it starts)."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", required=True, type=Path)
    r.add_argument("--policy", choices=sorted(POLICIES), default="bl255")
    s = sub.add_parser("serve")
    s.add_argument("vault")
    s.add_argument("reports")
    s.add_argument("policy", choices=sorted(POLICIES))
    a = ap.parse_args()
    if not (REPO / ".creaite-dev").exists():
        sys.exit("Development repository only.")
    if a.cmd == "serve":
        serve(a.vault, a.reports, a.policy)
    else:
        run(a.out.resolve(), a.policy)


if __name__ == "__main__":
    main()
