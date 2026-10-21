"""Does Chrome fetch the beacon from an exported page whose CSS ends in an unclosed url(? Fictional data only.
python3 -I csp_check.py <checkout>"""
import sys, threading, http.server, socketserver, unittest
from pathlib import Path
ROOT = Path(sys.argv.pop(1))
sys.path.insert(0, str(ROOT / "dev" / "tests")); sys.path.insert(0, str(ROOT / "dev" / "tools")); sys.path.insert(0, str(ROOT / "system" / "scripts"))
from test_export_page import LeakFix, page  # noqa
from cdp import Browser  # noqa
HITS = []
class H(http.server.BaseHTTPRequestHandler):
    PAGE = b""
    def do_GET(self):
        if self.path.startswith("/page"):
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(H.PAGE)
        else:
            HITS.append(self.path); self.send_response(200); self.send_header("Content-Type", "image/png"); self.end_headers()
    def log_message(self, *a): pass
class T(LeakFix):
    def test_csp(self):
        srv = socketserver.TCPServer(("127.0.0.1", 0), H); port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        css = f".page{{color:#123}} .page{{background:url(http://127.0.0.1:{port}/beacon.png"
        out, why = self.build(self.client(), page(css=css))
        print("\n### build:", why or "KEPT", flush=True)
        if out:
            import re, time
            html = out if isinstance(out, str) else out.decode()
            has_csp = "Content-Security-Policy" in html
            print("### page has CSP meta:", has_csp, "| css kept in page:", "beacon.png" in html, flush=True)
            for label, doc in (("WITH the page as built", html), ("CONTROL, CSP meta removed", re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', "", html))):
                del HITS[:]
                H.PAGE = doc.encode()
                b = Browser()
                try:
                    b.goto(f"http://127.0.0.1:{port}/page")
                    time.sleep(2)
                finally:
                    b.close()
                print(f"### {label}: beacon hits in Chrome = {len(HITS)}", flush=True)
        srv.shutdown()
if __name__ == "__main__":
    unittest.main(argv=["x", "T.test_csp"], verbosity=0)
