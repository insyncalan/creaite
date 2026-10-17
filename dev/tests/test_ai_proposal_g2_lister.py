"""#132 round 1, G2 (proposal, not applied): the HTTPS call that asks a provider which models a key can use.

Run: python3 dev/tests/test_ai_proposal_g2_lister.py

No real provider and no network: a fake HTTPS server on 127.0.0.1 with a certificate made for the test (openssl), trusted only
by the context the test passes in. g1-key-store.diff then g2-model-list.diff are applied to a throwaway vault
(ai_proposal_support) and HttpsLister is called there, in its own process.

Done when:
- creaite's own lister calls only https://api.openai.com and https://api.anthropic.com, verifies TLS (1.2 or later) and backend()
  uses it on a Mac (built() is then true);
- the key travels in one request header only (OpenAI: Authorization: Bearer; Anthropic: x-api-key with anthropic-version), never
  in the address; one GET per call;
- 401, 403 and 429 are KeyRefused(status); a 5xx, a redirect (to another host or the same one: never followed), an answer over
  the size cap, a timeout, an untrusted certificate, plain http and an answer that isn't a model list are ProviderUnreachable;
  no error holds the key or the answer's body, or chains to one that might;
- a proxy set in the environment is not used;
- the debug log gets the host and the status only, never the key;
- the live server's /api/ai/test answers the models, a refusal or "couldn't reach" in plain words, never the key.
"""
import http.server
import json
import shutil
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_proposal_support as S  # noqa: E402

KEY = "fake-good-0123456789abcdefTESTONLY"
OPENSSL = shutil.which("openssl")


class Fake(http.server.BaseHTTPRequestHandler):
    """The fake provider. Its behaviour is the server's `mode`; every request is kept in `seen`."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        srv = self.server
        srv.seen.append({"path": self.path, "headers": dict(self.headers), "method": "GET"})
        mode = srv.mode
        if mode == "slow":
            time.sleep(2)
        if mode in ("401", "403", "429", "500"):
            body = json.dumps({"error": f"bad key {self.headers.get('Authorization') or self.headers.get('x-api-key')}"})
            return self.answer(int(mode), body.encode())
        if mode == "redirect-other":
            return self.answer(302, b"", {"Location": "https://other.invalid/v1/models"})
        if mode == "redirect-same":
            return self.answer(301, b"", {"Location": "/v1/models/elsewhere"})
        if mode == "big":
            return self.answer(200, json.dumps({"data": [{"id": "m" * 100}] * 50}).encode())
        if mode == "notjson":
            return self.answer(200, b"<html>hello</html>")
        return self.answer(200, json.dumps({"data": [{"id": "fake-flagship"}, {"id": "fake-small"}, {"no": "id"},
                                                     {"id": "x" * 300}]}).encode())

    def answer(self, code, body, headers=None):
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def serve(cert=None, key=None):
    srv = Server(("127.0.0.1", 0), Fake)
    srv.seen, srv.mode = [], "ok"
    if cert:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


CALL = r'''
import ssl, providers as pv
a = json.loads(%r)
ctx = ssl.create_default_context(cafile=a["cert"]) if a.get("cert") else None
L = pv.HttpsLister(base={"openai": a["base"], "claude": a["base"]}, context=ctx, timeout=a.get("timeout", 5),
                   cap=a.get("cap", pv.LIST_CAP))
try:
    r = ["ok", L.models(a["provider"], a["key"])]
except pv.KeyRefused as e:
    r = ["refused", e.status, str(e), e.__cause__ is None and (e.__context__ is None or e.__suppress_context__)]
except pv.ProviderUnreachable as e:
    r = ["unreachable", str(e), e.__cause__ is None and (e.__context__ is None or e.__suppress_context__)]
print(json.dumps(r))'''


@unittest.skipUnless(OPENSSL, "needs openssl to make the fake provider's certificate")
class Lister(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = S.vault("g1-key-store", "g2-model-list")
        cls.tmp = Path(tempfile.mkdtemp(prefix="creaite-tls-"))
        cls.cert, cls.key = str(cls.tmp / "cert.pem"), str(cls.tmp / "key.pem")
        subprocess.run([OPENSSL, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", cls.key, "-out", cls.cert,
                        "-days", "2", "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1"],
                       check=True, capture_output=True)
        cls.srv = serve(cls.cert, cls.key)
        cls.base = f"https://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def call(self, mode="ok", provider="openai", env=None, **kw):
        self.srv.mode = mode
        self.srv.seen.clear()
        args = {"cert": self.cert, "base": self.base, "provider": provider, "key": KEY, **kw}
        return S.run_py(self.root, CALL % json.dumps(args), env=env)

    def test_openai_list_with_the_key_in_one_header_only(self):
        out = self.call()
        self.assertEqual(out, ["ok", ["fake-flagship", "fake-small"]], "ids only; an entry with no id or a 300-character one dropped")
        self.assertEqual(len(self.srv.seen), 1)
        req = self.srv.seen[0]
        self.assertEqual((req["method"], req["path"]), ("GET", "/v1/models"))
        holding = [k for k, v in req["headers"].items() if KEY in v]
        self.assertEqual(holding, ["Authorization"])
        self.assertEqual(req["headers"]["Authorization"], f"Bearer {KEY}")
        self.assertNotIn(KEY, req["path"])

    def test_anthropic_list_with_its_own_headers(self):
        out = self.call(provider="claude")
        self.assertEqual(out[0], "ok")
        req = self.srv.seen[0]
        self.assertEqual(req["path"], "/v1/models?limit=1000")
        self.assertEqual([k for k, v in req["headers"].items() if KEY in v], ["X-Api-Key"])
        self.assertEqual(req["headers"]["Anthropic-Version"], "2023-06-01")
        self.assertNotIn("Authorization", req["headers"])

    def test_a_refused_key_is_its_status_and_never_the_key_or_body(self):
        for status in ("401", "403", "429"):
            out = self.call(status)
            self.assertEqual(out[:2], ["refused", int(status)], status)
            self.assertEqual(out[2], f"refused ({status})")
            self.assertNotIn(KEY, json.dumps(out))
            self.assertTrue(out[3], "no chained exception")

    def test_unreachable_answers_name_the_host_only(self):
        cases = {"500": "answered 500", "redirect-other": "answered 302", "redirect-same": "answered 301",
                 "notjson": "wasn't a model list"}
        for mode, words in cases.items():
            out = self.call(mode)
            self.assertEqual(out[0], "unreachable", mode)
            self.assertIn("127.0.0.1", out[1])
            self.assertIn(words, out[1], mode)
            self.assertNotIn(KEY, json.dumps(out), mode)
            self.assertTrue(out[2], mode)
            self.assertEqual(len(self.srv.seen), 1, f"{mode}: one request; a redirect is never followed")

    def test_the_size_cap(self):
        out = self.call("big", cap=1000)
        self.assertEqual(out[0], "unreachable")
        self.assertIn("too large", out[1])

    def test_the_timeout(self):
        t0 = time.monotonic()
        out = self.call("slow", timeout=0.5)
        self.assertEqual(out[0], "unreachable")
        self.assertIn("couldn't be reached", out[1])
        self.assertLess(time.monotonic() - t0, 1.9 + 3, "the call gave up at its timeout")

    def test_tls_is_verified(self):
        out = self.call(cert=None)                         # the system's trust store: the test's certificate isn't in it
        self.assertEqual(out[0], "unreachable")
        self.assertEqual(self.srv.seen, [], "nothing was sent: the handshake failed before any request")

    def test_plain_http_is_refused_before_anything_is_sent(self):
        plain = serve()
        try:
            out = self.call(base=f"http://127.0.0.1:{plain.server_address[1]}")
            self.assertEqual(out[0], "unreachable")
            self.assertIn("only https", out[1])
            self.assertEqual(plain.seen, [])
        finally:
            plain.shutdown()
            plain.server_close()

    def test_a_proxy_in_the_environment_is_not_used(self):
        trap = serve()
        try:
            url = f"http://127.0.0.1:{trap.server_address[1]}"
            out = self.call(env={"HTTPS_PROXY": url, "https_proxy": url, "ALL_PROXY": url, "all_proxy": url})
            self.assertEqual(out[0], "ok")
            self.assertEqual(trap.seen, [])
        finally:
            trap.shutdown()
            trap.server_close()

    def test_the_debug_log_has_host_and_status_only(self):
        self.call("401")
        self.call()
        logs = "".join(f.read_text(encoding="utf-8") for f in (self.root / "system" / "logs").glob("debug-*.log"))
        self.assertIn("127.0.0.1 model list: 401", logs)
        self.assertIn("127.0.0.1 model list: 200", logs)
        self.assertNotIn(KEY, logs)
        self.assertNotIn("fake-good", logs)

    def test_the_route_answers_without_the_key(self):
        res = {}
        for mode in ("ok", "401", "500"):
            self.srv.mode = mode
            res[mode] = S.run_py(self.root, r'''
import ssl, live_server as L, providers as pv
a = json.loads(%r)
pv._BACKEND["pair"] = (pv.MemoryStore(), pv.HttpsLister(base={"openai": a["base"]},
                                                         context=ssl.create_default_context(cafile=a["cert"])))
sent = []
class H:
    def send(self, code, body): sent.append([code, body])
L.ai_test_route(H(), {"provider": "openai", "key": a["key"]})
print(json.dumps(sent[0]))''' % json.dumps({"base": self.base, "cert": self.cert, "key": KEY}))
        self.assertEqual(res["ok"][1]["ok"], True)
        self.assertEqual([m["id"] for m in res["ok"][1]["models"]], ["fake-flagship", "fake-small"])
        self.assertEqual((res["401"][1]["reason"], res["401"][1]["status"]), ("refused", 401))
        self.assertIn("did not accept this key (401)", res["401"][1]["message"])
        self.assertEqual(res["500"][1]["reason"], "network")
        self.assertIn("Couldn't reach OpenAI", res["500"][1]["message"])
        self.assertNotIn(KEY, json.dumps(res))


class Production(unittest.TestCase):
    """What creaite itself uses: the two hosts, TLS verified, and the lister in backend() on a Mac."""

    @classmethod
    def setUpClass(cls):
        cls.root = S.vault("g1-key-store", "g2-model-list")

    def test_only_the_two_hosts_and_tls_verified(self):
        out = S.run_py(self.root, r'''
import ssl, providers as pv
L = pv.HttpsLister()
pv._BACKEND.clear(); sys.platform = "darwin"
store, lister = pv.backend()
print(json.dumps({"base": L.base, "verify": L.context.verify_mode == ssl.CERT_REQUIRED, "host": L.context.check_hostname,
                  "min": L.context.minimum_version >= ssl.TLSVersion.TLSv1_2, "timeout": L.timeout, "cap": L.cap,
                  "backend": [type(store).__name__, type(lister).__name__], "built": pv.built(),
                  "headers": [sorted(pv.key_headers("openai", "k")), sorted(pv.key_headers("claude", "k"))]}))''')
        self.assertEqual(out["base"], {"openai": "https://api.openai.com", "claude": "https://api.anthropic.com"})
        self.assertTrue(out["verify"] and out["host"] and out["min"])
        self.assertEqual((out["timeout"], out["cap"]), (10, 1_000_000))
        self.assertEqual(out["backend"], ["KeychainStore", "HttpsLister"])
        self.assertTrue(out["built"])
        self.assertEqual(out["headers"], [["Authorization"], ["anthropic-version", "x-api-key"]])

    def test_a_provider_without_a_list_or_a_malformed_key_never_calls(self):
        out = S.run_py(self.root, r'''
import providers as pv
L = pv.HttpsLister(base={"openai": "https://127.0.0.1:9"})
res = []
for prov, key in (("deepseek", "fake-good-0123456789"), ("openai", "bad key with spaces"), ("openai", "x\r\nHost: evil")):
    try: L.models(prov, key); res.append("called")
    except ValueError: res.append("no list")
    except pv.KeyRefused as e: res.append(f"refused {e.status}")
print(json.dumps(res))''')
        self.assertEqual(out, ["no list", "refused 400", "refused 400"], "a key that could break the header is never sent")


if __name__ == "__main__":
    unittest.main()
