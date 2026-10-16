"""Plan item #95: a search never stalls behind the start-up search-index build, and never holds the server's lock while one runs.

Run: python3 dev/tests/test_search_stall.py
Starts the live server on a free port in a throwaway vault with no index stamp, so it builds the whole index at start. The vault
holds generated PDFs, which are slow to read, so the build takes a few seconds. One second in, a search, an Ask and a route that
needs the server's lock (Review's guesses) are sent together: the search and the guesses must answer while the build is still
running (the stamp it writes at the end isn't there yet), and the search says the index is still being built. Ask waits for the
build, without the lock, and then answers from the full index. Before the fix the search took the lock and waited for the build,
and the guesses queued behind it.
"""
import json
import os
import subprocess
import sys
import threading
import time
import unittest
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_live_server import free_port  # noqa: E402
from test_search import put  # noqa: E402
from test_search_live import FAKE_CLAUDE, events  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402


def pdf_pages(n, words):
    """A valid PDF of n pages, each showing `words` (many short lines, so that reading it takes real time)."""
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [" + b" ".join(f"{3 + 2 * i} 0 R".encode() for i in range(n)) + b"] /Count " + str(n).encode() + b" >>"]
    for i in range(n):
        data = zlib.compress(b"BT /F1 12 Tf 72 720 Td 14 TL " + b" ".join(b"(" + w + b") Tj T*" for w in words) + b" ET")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {3 + 2 * n} 0 R >> >> "
                    f"/Contents {4 + 2 * i} 0 R >>".encode())
        objs.append(b"<< /Length " + str(len(data)).encode() + b" /Filter /FlateDecode >>\nstream\n" + data + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for k, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += str(k).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n" + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF\n"
    return bytes(out)


class SearchDuringBuildTests(unittest.TestCase):
    PDFS, PAGES = 60, 60

    def setUp(self):
        self.v = v = Vault()
        populate(v)
        put(v, f"{ABC}/minutes/2026-09-25 Steering.md", "# Decisions\nGo-live moves because data access slipped.")
        v.run("index")                                              # the table holds the index as it stood before
        words = [b"platform", b"migration", b"billing", b"customer", b"assistant", b"latency", b"milestone", b"vendor"] * 12
        for i in range(self.PDFS):
            put(v, f"{ABC}/documents/Contract {i}.pdf", pdf_pages(self.PAGES, words))
        self.stamp = v.root / "system/search/index-built.json"
        self.stamp.unlink()                                         # no stamp: the server builds it all again at start
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        self.base = f"http://127.0.0.1:{free_port()}"
        env = {**os.environ, "CREAITE_PORT": self.base.rsplit(":", 1)[1], "CREAITE_CLAUDE": str(fake)}
        self.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.up = None
        for _ in range(100):
            try:
                urllib.request.urlopen(self.base + "/health", timeout=1)
                self.up = time.monotonic()
                break
            except OSError:
                time.sleep(0.05)
        self.assertIsNotNone(self.up, "the server didn't start")

    def tearDown(self):
        self.proc.terminate()
        self.proc.wait(timeout=20)
        self.v.cleanup()

    def call(self, path, body=None, stream=False):
        """(status, answer, seconds taken, whether the build had finished when it answered)."""
        req = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=180) as r:
            got = events(r) if stream else json.loads(r.read())
            return r.status, got, round(time.monotonic() - t0, 2), self.stamp.exists()

    def test_a_search_answers_while_the_index_builds_and_never_holds_the_lock(self):
        self.token = self.page_token()
        time.sleep(max(0.0, 1.0 - (time.monotonic() - self.up)))
        self.assertFalse(self.stamp.exists(), "the start-up build finished before the test began: make the vault slower")
        got = {}
        calls = {"search": lambda: self.call("/api/search?" + urllib.parse.urlencode({"q": "data access"})),
                 "ask": lambda: self.call("/api/search/ask", {"q": "Why did go-live move?"}, stream=True),
                 "lock": lambda: self.call("/api/review/guesses", {})}
        threads = []
        for name, fn in calls.items():
            threads.append(threading.Thread(target=lambda n=name, f=fn: got.__setitem__(n, f())))
            threads[-1].start()
            time.sleep(0.2)
        for t in threads:
            t.join(200)
        print("\n#95 timings (seconds, build finished when answered):",
              {k: (v[2], v[3]) for k, v in got.items()}, file=sys.stderr)
        status, res, _took, finished = got["search"]
        self.assertEqual(status, 200)
        self.assertFalse(finished, "the search waited for the whole build")
        self.assertTrue(res.get("indexing"))
        self.assertEqual([x["title"] for x in res["groups"]["meetings"]], ["2026-09-25 Steering"])   # the index as it stood
        self.assertFalse(got["lock"][3], "a route needing the server's lock queued behind the build")
        self.assertTrue(got["lock"][1]["ok"])
        status, evs, _took, finished = got["ask"]
        self.assertTrue(finished)                                   # Ask waits for the build (without the lock)
        self.assertIn("2026-09-25 Steering.md", [s["name"] for e in evs if e.get("type") == "sources" for s in e["sources"]])
        self.assertTrue(json.loads(self.stamp.read_text())["entries"])

    def page_token(self):
        import re
        html = urllib.request.urlopen(self.base + "/", timeout=60).read().decode()
        return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]


if __name__ == "__main__":
    unittest.main()
