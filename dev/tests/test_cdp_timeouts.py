"""harness-timeout: the browser driver never waits for ever. A silent DevTools socket, a Chrome that never publishes its port, one
that exits at once and a /json that never answers each raise a TimeoutError or RuntimeError naming what was waited for, within the
timeout. Fake servers and fake processes only: no real Chrome, fast.

Run: python3 dev/tests/test_cdp_timeouts.py
"""
import socket
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import cdp  # noqa: E402


class FakeServer:
    """Accepts connections; with `ws` completes the WebSocket handshake; then says nothing at all."""

    def __init__(self, ws=False):
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(5)
        self.port = self.srv.getsockname()[1]
        self.ws, self.conns = ws, []
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            try:
                c, _ = self.srv.accept()
            except OSError:
                return
            self.conns.append(c)
            if self.ws:
                buf = b""
                while b"\r\n\r\n" not in buf:
                    buf += c.recv(4096)
                c.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n")

    def close(self):
        self.srv.close()
        for c in self.conns:
            c.close()


class Timeouts(unittest.TestCase):
    def serve(self, **kw):
        s = FakeServer(**kw)
        self.addCleanup(s.close)
        return s

    def test_a_silent_websocket_fails_the_call_within_the_timeout_and_names_the_method(self):
        s = self.serve(ws=True)
        b = cdp.Browser.__new__(cdp.Browser)
        b.n, b.events, b.errors = 0, [], []
        b.ws = cdp.WebSocket(f"ws://127.0.0.1:{s.port}/devtools/page/x", timeout=0.5)
        self.addCleanup(b.ws.close)
        t = time.time()
        with self.assertRaises(TimeoutError) as cm:
            b.call("Page.navigate", url="about:blank")
        self.assertLess(time.time() - t, 5)
        self.assertIn("Page.navigate", str(cm.exception))

    def test_a_silent_handshake_fails_within_the_timeout(self):
        s = self.serve(ws=False)          # accepts, never answers the upgrade
        t = time.time()
        with self.assertRaises(TimeoutError):
            cdp.WebSocket(f"ws://127.0.0.1:{s.port}/devtools/page/x", timeout=0.5)
        self.assertLess(time.time() - t, 5)

    def test_a_chrome_that_never_publishes_its_port_times_out_and_cleans_up(self):
        def fake_spawn(cmd, **kw):
            return cdp.subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
        with mock.patch.object(cdp, "chrome_path", return_value="/nonexistent/chrome"), \
                mock.patch.object(cdp.proc_guard, "spawn", fake_spawn), mock.patch.object(cdp, "START_TIMEOUT", 1):
            t = time.time()
            with self.assertRaises(TimeoutError) as cm:
                cdp.Browser()
        self.assertLess(time.time() - t, 15)
        self.assertIn("DevTools port", str(cm.exception))

    def test_a_chrome_that_exits_at_once_fails_at_once(self):
        def fake_spawn(cmd, **kw):
            return cdp.subprocess.Popen([sys.executable, "-c", "raise SystemExit(3)"], start_new_session=True)
        with mock.patch.object(cdp, "chrome_path", return_value="/nonexistent/chrome"), \
                mock.patch.object(cdp.proc_guard, "spawn", fake_spawn):
            t = time.time()
            with self.assertRaises(RuntimeError) as cm:
                cdp.Browser()
        self.assertLess(time.time() - t, 10)
        self.assertIn("exited with 3", str(cm.exception))

    def test_a_json_endpoint_that_never_answers_times_out(self):
        s = self.serve(ws=False)
        holder = {}

        def fake_spawn(cmd, **kw):
            p = cdp.subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
            profile = next(a.split("=", 1)[1] for a in cmd if a.startswith("--user-data-dir="))
            Path(profile, "DevToolsActivePort").write_text(f"{s.port}\n/devtools/browser/x\n")
            holder["p"] = p
            return p
        with mock.patch.object(cdp, "chrome_path", return_value="/nonexistent/chrome"), \
                mock.patch.object(cdp.proc_guard, "spawn", fake_spawn), mock.patch.object(cdp, "CALL_TIMEOUT", 1):
            t = time.time()
            with self.assertRaises(TimeoutError) as cm:
                cdp.Browser()
        self.addCleanup(lambda: holder["p"].kill())
        self.assertLess(time.time() - t, 15)
        self.assertIn("/json", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
