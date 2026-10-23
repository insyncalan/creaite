"""2.6.2 (B): /api/inbox/upload turns a file-system error into plain words, on a real live server over a throwaway vault.

The route's catch is the guarded diff dev/proposals/inbox-upload-oserror/live_server.diff. Until it is applied to this tree the vault
copy gets it (git apply to the throwaway copy only), so the same checks pass either way. A name of 300 characters says the name is too long;
any other error says the file couldn't be saved; neither shows an exception's text or a path; a name with a NUL byte and a name that is
already a folder in inbox/ are saved under a clean or numbered name. Mutant: the catch removed from the copy, and the checks go red.

Run: python3 dev/tests/test_inbox_upload_oserror.py
"""
import base64
import json
import resource
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL = ROOT / "dev/proposals/inbox-upload-oserror/live_server.diff"
MARK = "except OSError as e:                       # 2.6.2"


def has_catch():
    return MARK in (ROOT / "system/scripts/live_server.py").read_text()


class Server:
    def __init__(self, mutate=False, fsize=None):
        self.home = Path(tempfile.mkdtemp(prefix="creaite-b262-")).resolve()
        self.v = Vault()
        d = self.v.root
        if not has_catch():
            subprocess.run(["git", "init", "-q", str(d)], check=True)
            subprocess.run(["git", "apply", str(PROPOSAL)], cwd=d, check=True)
        if mutate:
            f = d / "system/scripts/live_server.py"
            t = f.read_text()
            a = t.index("        import errno\n        try:\n")
            b = t.index("        return self.send(200", a)
            body = t[a:b]
            inner = body[body.index("            paths.INBOX.mkdir"):body.index("        except OSError")]
            f.write_text(t[:a] + "\n".join(l[4:] for l in inner.splitlines()) + "\n" + t[b:])
        self.v.run("init")
        (d / ".creaite-dev").unlink(missing_ok=True)
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.base = f"http://127.0.0.1:{self.port}"
        env = {**os.environ, "HOME": str(self.home), "CREAITE_PORT": str(self.port), "CREAITE_NO_LAUNCHCTL": "1"}
        limit = (lambda: resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))) if fsize else None      # a write past it fails (EFBIG), as a full disk does
        self.proc = subprocess.Popen([sys.executable, str(d / "system/scripts/live_server.py")], env=env, preexec_fn=limit,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(150):
            try:
                urllib.request.urlopen(self.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(self.base + "/").read().decode()
        self.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.v.cleanup()
        shutil.rmtree(self.home, ignore_errors=True)

    def upload(self, name, data=b"WEBVTT\n"):
        body = json.dumps({"name": name, "data": base64.b64encode(data).decode()}).encode()
        req = urllib.request.Request(self.base + "/api/inbox/upload", data=body, method="POST", headers={
            "Content-Type": "application/json", "X-Creaite-Token": self.token, "Sec-Fetch-Site": "same-origin", "Origin": self.base})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            with e:
                try:
                    return e.code, json.loads(e.read() or b"{}")
                except ValueError:
                    return e.code, {}
        except OSError:
            return 0, {}


def plain(msg, root):
    assert msg and "Errno" not in msg and "OSError" not in msg and "/" not in msg and str(root) not in msg, msg


class Checks:
    @staticmethod
    def too_long(s):
        code, r = s.upload("a" * 300 + ".txt")
        assert code == 400 and r.get("ok") is False, (code, r)
        assert r["message"] == "The file name is too long. Rename it and add it again.", r
        plain(r["message"], s.v.root)

    @staticmethod
    def generic(s):
        inbox = s.v.root / "inbox"
        inbox.mkdir(exist_ok=True)
        os.chmod(inbox, 0o500)
        try:
            code, r = s.upload("notes.txt")
        finally:
            os.chmod(inbox, 0o700)
        assert code == 500 and r.get("ok") is False, (code, r)
        assert r["message"] == "That file couldn't be saved. Try again.", r
        plain(r["message"], s.v.root)

    @staticmethod
    def truncated(s):
        """Cap's note 2: a write that fails part-way leaves nothing behind, so a retry is saved under the same name, not "x (2)"."""
        inbox = s.v.root / "inbox"
        inbox.mkdir(exist_ok=True)
        (inbox / "kept.vtt").write_bytes(b"WEBVTT\nkept\n")
        code, r = s.upload("big.vtt", b"x" * 400000)
        assert code == 500 and r.get("ok") is False, (code, r)
        left = sorted(p.name for p in inbox.iterdir())
        assert left == ["kept.vtt"], left
        assert (inbox / "kept.vtt").read_bytes() == b"WEBVTT\nkept\n"
        code, r = s.upload("kept.vtt", b"y" * 400000)                      # a file this call did not create is never removed
        assert code == 500 and sorted(p.name for p in inbox.iterdir()) == ["kept.vtt"], (code, r)
        assert (inbox / "kept.vtt").read_bytes() == b"WEBVTT\nkept\n"
        code, r = s.upload("small.vtt", b"WEBVTT\n")
        assert code == 200 and r["name"] == "small.vtt", (code, r)

    @staticmethod
    def odd_names(s):
        inbox = s.v.root / "inbox"
        inbox.mkdir(exist_ok=True)
        (inbox / "folder.txt").mkdir()
        for name, want in (("a\x00b.txt", "a b.txt"), ("folder.txt", "folder (2).txt")):
            code, r = s.upload(name)
            assert code == 200 and r.get("ok") and r["name"] == want, (name, code, r)
            assert (inbox / want).is_file()


@unittest.skipIf(os.geteuid() == 0, "root ignores a read-only folder")
class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Server()

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    def test_name_too_long(self):
        Checks.too_long(self.s)

    def test_other_error(self):
        Checks.generic(self.s)

    def test_nul_and_folder_names(self):
        Checks.odd_names(self.s)


@unittest.skipIf(os.geteuid() == 0, "root ignores a file size limit")
class Truncated(unittest.TestCase):
    def test_a_failed_write_leaves_no_partial_file(self):
        s = Server(fsize=150000)
        try:
            Checks.truncated(s)
        finally:
            s.close()


class Mutant(unittest.TestCase):
    def test_without_the_catch_the_checks_go_red(self):
        s = Server(mutate=True)
        try:
            for check in (Checks.too_long, Checks.generic):
                with self.assertRaises(AssertionError, msg=check.__name__):
                    check(s)
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main(verbosity=1)
