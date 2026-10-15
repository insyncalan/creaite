"""#83: the live server binds without a reverse DNS lookup.

Run: python3 dev/tests/test_live_server_bind.py
http.server's server_bind calls socket.getfqdn(host); on GitHub's macOS runner that stalled for 30 s or more, so the
live server started but never answered /health in time. The check runs in a throwaway vault, in its own process,
with getfqdn made to fail: binding must not call it.
"""
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

CODE = """
import socket, sys
sys.path.insert(0, 'system/scripts')
def no_lookup(*a, **k):
    raise AssertionError('getfqdn called at bind')
socket.getfqdn = no_lookup
import live_server
srv = live_server.LocalServer(('127.0.0.1', 0), live_server.Handler)
try:
    assert srv.server_name == '127.0.0.1', srv.server_name
    assert srv.server_port == srv.server_address[1] > 0
finally:
    srv.server_close()
print('ok')
"""


class BindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.v.root, ignore_errors=True)

    def test_bind_does_no_dns_lookup(self):
        r = subprocess.run([sys.executable, "-c", CODE], cwd=self.v.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ok", r.stdout)

    def test_main_uses_local_server(self):
        src = (Path(__file__).resolve().parents[2] / "system/scripts/live_server.py").read_text()
        self.assertIn('httpd = LocalServer(("127.0.0.1", port), Handler)', src)
        self.assertNotIn("ThreadingHTTPServer((", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
