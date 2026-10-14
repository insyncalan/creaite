"""BL-255: the dashboard's hash-based script policy, in report-only mode.

Run: python3 dev/tests/test_script_policy.py   (the browser part needs Google Chrome; skipped otherwise)
The hashes are taken from the page actually served and change when it changes; every HTML page carries
Content-Security-Policy-Report-Only with them, beside BL-212's unchanged headers; /csp-report counts reports in the debug log
by directive and kind only, refuses a request that isn't local and is rate-limited; live_mode.script_policy "off" drops the
header. In Chrome the page raises no violation, and report-only blocks nothing: an inline script added at run time still runs
and is only reported.
"""
import base64
import hashlib
import http.client
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import proc_guard  # noqa: E402
import live_server  # noqa: E402
from live_browser import LiveBrowserCase, free_port  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

HEADER = "Content-Security-Policy-Report-Only"
BL212 = {"Content-Security-Policy": "frame-ancestors 'none'", "X-Frame-Options": "DENY",
         "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}
SECRET = "Confidential-Merger-Plan"            # page text a report could carry, which must never reach the log


def sha(text):
    """The CSP source for `text`, computed here independently of live_server."""
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode() + "'"


def blocks(html):
    """The executed scripts' and the style elements' text, found the plain way (the page has no comments); styles are looked
    for with the scripts taken out, as a "<style>" in a script's string is not an element."""
    found = list(re.finditer(r"<script([^>]*)>(.*?)</script>", html, re.S))
    scripts = [m.group(2) for m in found if "application/json" not in m.group(1)]
    rest = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
    return scripts, re.findall(r"<style>(.*?)</style>", rest, re.S)


def directive(policy, name):
    """One directive's sources from a policy header."""
    for part in policy.split(";"):
        bits = part.split()
        if bits and bits[0] == name:
            return bits[1:]
    return None


class Hashes(unittest.TestCase):
    def test_blocks_found_as_the_browser_parses_them(self):
        page = ('<!doctype html><script type="application/json" id="data">{"a":"<\\/script>"}</script>'
                '<!-- <script>not run</script> --><style>b{c:d}</style><script src="/x.js"></script>'
                '<script>const s = "<style>.x{}</style>";</script><script type="module">m()</script>')
        h = live_server.csp_hashes(page)
        self.assertEqual(h["script"], [sha('const s = "<style>.x{}</style>";'), sha("m()")])
        self.assertEqual(h["style"], [sha("b{c:d}")])          # the "<style>" in the script's string is not a style element
        self.assertEqual(live_server.csp_hashes("<script>a()\r\nb()</script>")["script"], [sha("a()\nb()")])

    def test_the_hashes_follow_the_page(self):
        one, two = "<style>p{}</style><script>go()</script>", "<style>p{}</style><script>go(1)</script>"
        a, b = live_server.csp_policy(one), live_server.csp_policy(two)
        self.assertNotEqual(directive(a, "script-src"), directive(b, "script-src"))
        self.assertEqual(directive(a, "style-src"), ["'self'", "'unsafe-inline'"])     # BL-255: style="" attributes stay
        self.assertEqual(directive(a, "style-src-elem"), ["'self'", sha("p{}")])    # Alan: style hashes once no run-time <style>
        self.assertEqual(directive(a, "style-src-attr"), ["'unsafe-inline'"])          # style="" attributes stay allowed
        self.assertIsNone(directive(live_server.csp_policy(one, strict_styles=False), "style-src-elem"))
        self.assertEqual(directive(live_server.csp_policy("<p>no script</p>"), "script-src"), ["'none'"])

    def test_reports_become_a_directive_and_a_kind(self):
        classic = json.dumps({"csp-report": {"effective-directive": "script-src-elem", "blocked-uri": "inline",
                                             "document-uri": "http://127.0.0.1:8765/?q=" + SECRET, "script-sample": SECRET}})
        self.assertEqual(live_server.csp_reports(classic.encode(), "application/csp-report"), [("script-src-elem", "inline")])
        api = json.dumps([{"type": "csp-violation", "body": {"effectiveDirective": "img-src", "blockedURL": "https://x.example/" + SECRET}},
                          {"type": "deprecation", "body": {}}])
        self.assertEqual(live_server.csp_reports(api.encode(), "application/reports+json"), [("img-src", "external")])
        kinds = {"data:image/png;base64,AAA": "data", "blob:http://127.0.0.1/1": "blob", "http://127.0.0.1:8765/sw.js": "self",
                 "eval": "eval", "": "other", "chrome-extension://abc": "other"}
        for blocked, kind in kinds.items():
            self.assertEqual(live_server.csp_kind(blocked), kind, blocked)
        self.assertEqual(live_server.csp_directive("<script>alert(1)</script>"), "unknown")

    def test_reports_are_rate_limited(self):
        saved = dict(live_server.CSP_REPORTS)
        self.addCleanup(live_server.CSP_REPORTS.update, saved)
        live_server.CSP_REPORTS.update(since=time.time(), n=0, dropped=0)
        self.assertEqual(live_server.csp_take(live_server.CSP_REPORT_LIMIT - 5), live_server.CSP_REPORT_LIMIT - 5)
        self.assertEqual(live_server.csp_take(10), 5)
        self.assertEqual(live_server.csp_take(1), 0)
        self.assertEqual(live_server.CSP_REPORTS["dropped"], 6)

    def test_only_this_machine_may_report(self):
        class Fake:
            def __init__(self, addr, headers):
                self.client_address, self.headers = (addr, 1), headers

            def host_ok(self):
                return live_server.host_name(self.headers.get("Host")) in ("127.0.0.1", "localhost", "::1")
        ok = {"Host": "127.0.0.1:8765"}
        self.assertTrue(live_server.csp_local(Fake("127.0.0.1", ok)))
        self.assertTrue(live_server.csp_local(Fake("127.0.0.1", {**ok, "Origin": "http://127.0.0.1:8765"})))
        for addr, headers in (("192.168.1.5", ok), ("127.0.0.1", {"Host": "evil.example"}),
                              ("127.0.0.1", {**ok, "Origin": "https://evil.example"}), ("127.0.0.1", {**ok, "Origin": "null"}),
                              ("127.0.0.1", {**ok, "Sec-Fetch-Site": "cross-site"})):
            self.assertFalse(live_server.csp_local(Fake(addr, headers)), (addr, headers))


class Template(unittest.TestCase):
    """The committed dashboard template (BL-231's bundle), as BL-255 assumes it: one executed inline script and the JSON data
    block, nothing external, no inline handlers, no `javascript:`, no string evaluation, so a hash-only script-src holds."""

    @classmethod
    def setUpClass(cls):
        cls.page = (Path(__file__).resolve().parents[2] / "system/templates/dashboard.html").read_text(encoding="utf-8")

    def test_one_app_script_and_its_hash_is_the_one_sent(self):
        tags = re.findall(r"<script\b([^>]*)>", self.page, re.I)
        self.assertEqual(len(tags), 2, tags)                                   # the data block and the bundle
        self.assertEqual(sum("application/json" in t for t in tags), 1, tags)
        self.assertFalse([t for t in tags if re.search(r"\bsrc\s*=", t, re.I)], tags)
        scripts, styles = blocks(self.page)
        self.assertEqual(len(scripts), 1)
        self.assertNotRegex(scripts[0], r"(?i)</script")                       # the block ends where the bundle ends
        self.assertEqual(live_server.csp_hashes(self.page)["script"], [sha(scripts[0])])
        self.assertEqual(live_server.csp_hashes(self.page)["style"], [sha(s) for s in styles])

    def test_nothing_a_hash_only_policy_would_stop(self):
        from html.parser import HTMLParser
        found = []

        class Tags(HTMLParser):
            def handle_starttag(self, tag, attrs):
                for k, v in attrs:
                    if k.startswith("on") or (k in ("href", "src", "action") and (v or "").strip().lower().startswith("javascript:")):
                        found.append((tag, k))
                    if k in ("href", "src") and re.match(r"(?i)\s*(https?:)?//", v or "") and not (tag == "a"):
                        found.append((tag, k, v))
        Tags().feed(self.page)
        self.assertEqual(found, [])                                            # no on*=, no javascript:, nothing external
        app = blocks(self.page)[0][0]
        for pat in (r"\son[a-z]+=[\"'$]", r"(?<![.\w$])eval\s*\(", r"\bnew\s+Function\s*\(",
                    r"set(?:Timeout|Interval)\s*\(\s*[\"'`]", r"(?i)javascript:"):
            self.assertIsNone(re.search(pat, app), pat)                        # nor in the markup the app writes


class Served(unittest.TestCase):
    """The real server in a throwaway vault, without a browser."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.addClassCleanup(cls.v.cleanup)
        populate(cls.v)
        cls.port = free_port()
        cls.proc = proc_guard.spawn([sys.executable, str(cls.v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "CREAITE_PORT": str(cls.port)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.addClassCleanup(proc_guard.stop, cls.proc, 10)
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{cls.port}/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)

    def raw(self, method, path, headers=None, body=None, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            c.putrequest(method, path, skip_host=True)
            c.putheader("Host", host or f"127.0.0.1:{self.port}")
            for k, v in (headers or {}).items():
                c.putheader(k, v)
            c.putheader("Content-Length", str(len(body or b"")))
            c.endheaders(body or None)
            r = c.getresponse()
            return r.status, dict(r.getheaders()), r.read()
        finally:
            c.close()

    def log_text(self):
        return "".join(p.read_text(encoding="utf-8") for p in sorted((self.v.root / "system/logs").glob("debug-*.log")))

    def test_each_page_names_its_own_blocks(self):
        for path in ("/", "/offline"):
            status, headers, body = self.raw("GET", path)
            self.assertEqual(status, 200, path)
            policy = headers.get(HEADER)
            self.assertTrue(policy, path)
            scripts, styles = blocks(body.decode("utf-8"))
            self.assertTrue(scripts and styles, path)
            self.assertEqual(directive(policy, "script-src"), [sha(s) for s in scripts], path)
            self.assertEqual(live_server.csp_hashes(body.decode("utf-8"))["style"], [sha(s) for s in styles], path)
            self.assertEqual(directive(policy, "style-src-elem"), ["'self'"] + [sha(s) for s in styles], path)
            for name, want in (("worker-src", ["'self'"]), ("default-src", ["'self'"]), ("report-uri", ["/csp-report"]),
                               ("style-src", ["'self'", "'unsafe-inline'"]), ("object-src", ["'none'"])):
                self.assertEqual(directive(policy, name), want, (path, name))
            for k, v in BL212.items():                                    # BL-212's enforced headers are unchanged
                self.assertEqual(headers.get(k), v, (path, k))
        for path in ("/health", "/sw.js", "/manifest.webmanifest"):        # only pages carry it
            self.assertNotIn(HEADER, self.raw("GET", path)[1], path)

    def test_the_report_endpoint_counts_and_refuses(self):
        report = json.dumps({"csp-report": {"effective-directive": "script-src-elem", "blocked-uri": "inline",
                                            "document-uri": f"http://127.0.0.1:{self.port}/?q={SECRET}",
                                            "script-sample": SECRET}}).encode()
        kind = {"Content-Type": "application/csp-report"}
        self.assertEqual(self.raw("POST", "/csp-report", kind, report)[0], 204)
        self.assertEqual(self.raw("POST", "/csp-report", {**kind, "Origin": "https://evil.example"}, report)[0], 403)
        self.assertEqual(self.raw("POST", "/csp-report", {**kind, "Sec-Fetch-Site": "cross-site"}, report)[0], 403)
        self.assertEqual(self.raw("POST", "/csp-report", kind, report, host="evil.example")[0], 403)
        self.assertEqual(self.raw("POST", "/csp-report", {"Content-Type": "text/plain"}, report)[0], 415)
        self.assertEqual(self.raw("POST", "/csp-report", kind, b"{" + b" " * 20000 + b"}")[0], 413)
        self.assertEqual(self.raw("POST", "/csp-report", kind, b"not json")[0], 400)
        end = time.time() + 10
        while "report-only violation" not in self.log_text() and time.time() < end:
            time.sleep(0.1)
        text = self.log_text()
        lines = [x for x in text.splitlines() if " csp " in x and "violation" in x]
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].endswith("report-only violation: script-src-elem inline"), lines[0])
        self.assertNotIn(SECRET, text)
        self.assertNotIn("document-uri", text)
        before = sorted(p.name for p in (self.v.root / "system").rglob("*") if p.is_file() and "logs" not in p.parts)
        self.raw("POST", "/csp-report", kind, report)
        after = sorted(p.name for p in (self.v.root / "system").rglob("*") if p.is_file() and "logs" not in p.parts)
        self.assertEqual(before, after)                                  # no other write
        out = subprocess.run([sys.executable, str(self.v.root / "system/scripts/doctor.py")], capture_output=True, text=True,
                             timeout=120)
        self.assertRegex(out.stdout, r"Script policy \(report-only\) — [1-9]\d* violations? in 7 days \(\d+ × script-src-elem inline\)")

    def test_the_setting_turns_it_off(self):
        settings = self.v.root / "system/config/settings.json"
        saved = settings.read_text(encoding="utf-8")
        self.addCleanup(settings.write_text, saved, encoding="utf-8")
        data = json.loads(saved)
        self.assertEqual(data["live_mode"].get("script_policy", "report-only"), "report-only")
        data["live_mode"]["script_policy"] = "off"
        settings.write_text(json.dumps(data), encoding="utf-8")
        status, headers, _ = self.raw("GET", "/")
        self.assertEqual(status, 200)
        self.assertNotIn(HEADER, headers)
        self.assertEqual(headers.get("Content-Security-Policy"), "frame-ancestors 'none'")   # BL-212's header stays
        settings.write_text(saved, encoding="utf-8")
        self.assertIn(HEADER, self.raw("GET", "/")[1])


class InChrome(LiveBrowserCase):
    """The policy in a real browser: the page raises nothing, and report-only blocks nothing."""
    shared_server = True

    def log_text(self):
        return "".join(p.read_text(encoding="utf-8") for p in sorted((self.v.root / "system/logs").glob("debug-*.log")))

    def test_page_raises_nothing_and_report_only_blocks_nothing(self):
        self.b.call("Page.addScriptToEvaluateOnNewDocument", source="""window.__csp=[];
          document.addEventListener('securitypolicyviolation', e => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));""")
        self.b.reload("typeof go==='function' && LIVE")
        self.b.pump(1.0)
        self.assertTrue(self.b.eval("navigator.serviceWorker.getRegistrations().then(r=>r.length)"))   # worker-src 'self'
        screens = ["go('today')", "go('projects')", "go('cockpit','ABC')", "go('people')", "go('mine')",
                   "go('work')", "openRecord('actions',A[0].id)", "go('review')", "go('inbox')", "go('files')",
                   "go('activity')", *[f"go('settings','{c}')" for c, _ in self.b.eval("SETCATS")],
                   *[f"go('help','{t}')" for t in self.b.eval("D.help.tabs.map(t=>t.id)")]]
        for js in screens:                                                 # every screen (V190-BL255-CHECK-NOTE)
            self.b.eval(js + "; 1")
            self.b.pump(0.4)
            self.assertEqual(self.b.eval("window.__csp"), [], js)         # the served hashes match: nothing to report
        self.assertEqual(self.b.eval("document.querySelectorAll('style').length"), 1)   # no <style> added at run time
        self.b.eval("const s=document.createElement('script'); s.textContent='window.__ran=1'; document.body.appendChild(s); 1")
        self.b.wait("window.__ran===1")                                    # report-only: the unlisted script still ran
        self.b.wait("window.__csp.length>0")
        self.assertTrue(self.b.eval("window.__csp[0]").startswith("script-src-elem inline"), self.b.eval("window.__csp"))
        end = time.time() + 15                                             # Chrome's own report reaches the endpoint
        while "report-only violation: script-src-elem inline" not in self.log_text() and time.time() < end:
            time.sleep(0.2)
        self.assertIn("report-only violation: script-src-elem inline", self.log_text())


if __name__ == "__main__":
    unittest.main()
