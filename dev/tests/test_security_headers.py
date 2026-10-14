"""BL-212: security headers on the live server, and a narrower /health.

Run: python3 dev/tests/test_security_headers.py   (the browser part needs Google Chrome; skipped otherwise)
A real server in a throwaway vault. Every response carries frame-ancestors 'none', X-Frame-Options DENY, nosniff and
no-referrer; /health says {"ok": true} and nothing else, with no cross-origin header; [::1] is accepted and an unknown Host
is still refused; a page from another origin can't frame the dashboard; the launcher still tells its own vault's server from
another's; a dashboard opened from a file still finds the server.
"""
import http.client
import http.server
import json
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from live_browser import LiveBrowserCase, free_port  # noqa: E402

WANT = {"Content-Security-Policy": "frame-ancestors 'none'", "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}


class SecurityHeaders(LiveBrowserCase):
    shared_server = True

    def raw(self, method, path, host=None, headers=None, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            c.putrequest(method, path, skip_host=True)
            c.putheader("Host", host or f"127.0.0.1:{self.port}")
            for k, v in (headers or {}).items():
                c.putheader(k, v)
            c.putheader("Content-Length", str(len(body or b"")))
            c.endheaders(body or None)
            r = c.getresponse()
            return r.status, {k: v for k, v in r.getheaders()}, r.read()
        finally:
            c.close()

    def test_every_response_carries_the_headers(self):
        cases = [("GET", "/"), ("GET", "/health"), ("GET", "/api/data"), ("GET", "/offline"), ("GET", "/sw.js"),
                 ("GET", "/manifest.webmanifest"), ("GET", "/app/icon-192.png"), ("GET", "/nothing-here"),
                 ("OPTIONS", "/health"), ("POST", "/api/apply"), ("PUT", "/")]           # PUT: the standard library's own 501
        for method, path in cases:
            status, headers, _ = self.raw(method, path)
            for k, v in WANT.items():
                self.assertEqual(headers.get(k), v, f"{method} {path} ({status}): {k}")
        status, headers, _ = self.raw("GET", "/", host="evil.example")
        self.assertEqual(status, 403)
        self.assertEqual(headers.get("X-Frame-Options"), "DENY")

    def test_health_says_only_that_it_is_up(self):
        status, headers, body = self.raw("GET", "/health")
        self.assertEqual((status, json.loads(body)), (200, {"ok": True}))
        self.assertNotIn(self.v.root.name, body.decode())
        self.assertNotIn(str(self.port), body.decode())
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        status, headers, _ = self.raw("OPTIONS", "/health", headers={"Origin": "https://evil.example",
                                                                     "Access-Control-Request-Method": "GET"})
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        status, headers, _ = self.raw("GET", "/health", headers={"Origin": "null"})
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_the_launcher_tells_its_own_vault(self):
        import live_server
        mine = live_server.vault_mark(self.v.root)
        self.assertEqual(json.loads(self.raw("GET", "/health", headers={"X-Creaite-Vault": mine})[2]), {"ok": True, "this_vault": True})
        self.assertEqual(json.loads(self.raw("GET", "/health", headers={"X-Creaite-Vault": "0" * 16})[2]), {"ok": True, "this_vault": False})
        out = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts'); import launch; print(launch.vault_mark())"],
                             cwd=self.v.root, capture_output=True, text=True, timeout=30)
        self.assertEqual(out.stdout.strip(), mine)                       # the launcher and the server agree

    def test_ipv6_loopback_accepted_unknown_host_refused(self):
        self.assertEqual(self.raw("GET", "/health", host=f"[::1]:{self.port}")[0], 200)
        self.assertEqual(self.raw("GET", "/", host=f"[::1]:{self.port}")[0], 200)
        self.assertEqual(self.raw("GET", "/", host=f"localhost:{self.port}")[0], 200)
        for host in ("evil.example", f"evil.example:{self.port}", f"[::2]:{self.port}", "[::1", "127.0.0.1.evil.example"):
            self.assertEqual(self.raw("GET", "/", host=host)[0], 403, host)
            self.assertEqual(self.raw("GET", "/health", host=host)[0], 403, host)

    def test_another_origin_cannot_frame_the_page(self):
        port = free_port()
        page = (f'<!doctype html><title>outer</title><iframe id="f" name="f" src="http://127.0.0.1:{self.port}/" width="800" height="600"></iframe>'
                f'<iframe id="ok" src="/inner" width="200" height="100"></iframe>').encode()
        inner = b"<!doctype html><title>inner</title><p id=hi>framed</p>"

        class Outer(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                data = inner if self.path == "/inner" else page
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Outer)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        self.b.goto(f"http://127.0.0.1:{port}/")         # another port: another origin (same site, so Chrome keeps the frame in this process)
        self.b.wait("document.getElementById('ok').contentDocument && document.getElementById('ok').contentDocument.getElementById('hi')")

        def frames():
            tree = self.b.call("Page.getFrameTree")["frameTree"]
            return [c["frame"] for c in tree.get("childFrames", [])]
        end = time.time() + 15                           # wait for the condition, not a fixed time (the Linux runner)
        while time.time() < end:
            dash = [f for f in frames() if f.get("name") == "f" and f.get("url") not in ("", "about:blank")]
            if dash:
                break
            time.sleep(0.1)
        self.assertTrue(dash, frames())
        # a refused frame is Chrome's error page, recording the address it wouldn't show; the dashboard never ran in it
        self.assertEqual(dash[0]["url"], "chrome-error://chromewebdata/", dash[0])
        self.assertTrue(dash[0].get("unreachableUrl", "").startswith(f"http://127.0.0.1:{self.port}/"), dash[0])

    def test_a_dashboard_opened_from_a_file_still_finds_the_server(self):
        dash = self.v.root / "dashboard.html"
        self.assertTrue(dash.exists())
        self.b.goto(dash.resolve().as_uri())
        self.b.wait("typeof checkLive==='function'")
        self.b.eval(f"S.port={self.port}; LIVELINK=false; checkLive();")
        self.b.wait("LIVELINK===true")
        self.b.eval(f"S.port={free_port()}; checkLive();")              # nothing on that port
        self.b.wait("LIVELINK===false")


if __name__ == "__main__":
    unittest.main(verbosity=2)
