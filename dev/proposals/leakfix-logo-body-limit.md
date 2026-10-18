# live_server.py: a per-route body cap for the logo routes (proposal, LOGO 4)

**Status: a proposal for Alan's yes. `live_server.py` is a guarded file; nothing here is applied.**

## README

Team Cap's review of the logo routes (finding 4, LOW) found that `BODY_LIMIT` is 40 MB for every route. The Content-Length is checked
before the body is read, so a 41 MB request is refused. But a 30 MB base64 body for `/api/report/logo/save` is read into memory (about
100 MB transient) and only then refused by the 400 kB logo check, and a short body with a lying Content-Length leaves a handler thread
waiting for bytes that never come (other requests are still answered).

The fix is a per-route cap checked in the same place, before the read. A logo may be 400 kB, and the save carries the picture twice
(the original and the trimmed copy), so as base64 a legal request is at most about 1.07 MB. The cap is therefore **1,200,000 bytes**
for `/api/report/logo/save` (Cap suggested about 600 kB; that would refuse a legal request that has both copies near the limit) and
4 kB for `/api/report/logo/remove` (it carries a code and a kind). Every other route keeps `BODY_LIMIT`.

Not covered by this change: the lying Content-Length. It needs a socket timeout on the request handler (for example `timeout = 30` on
the handler class); that touches every route, so it is left for Alan to decide separately.

Tests to add with it (`dev/tests/test_client_report_setting.py`, class `Routes`): a 1.3 MB body to `/api/report/logo/save` answers 400
before the logo check runs; a normal logo with its trimmed copy (two 400,000-byte pictures) is still saved; `/api/report/logo/remove`
with a 5 kB body answers 400.

## The exact diff (against `system/scripts/live_server.py` on `p240-leakfix`)

```diff
@@ -218,6 +218,8 @@
 PREVIEW_CHARS = 200_000               # an inbox file's preview        # a file added to the Inbox (BL-42)
 INBOX_TYPES = (".vtt", ".docx", ".txt", ".md", ".pdf")
 BODY_LIMIT = 40 * 1024 * 1024         # any request (base64 makes a 25 MB file about 34 MB)
+ROUTE_BODY_LIMITS = {"/api/report/logo/save": 1_200_000,      # p240-leakfix LOGO 4: a logo is at most 400 kB, twice (original and
+                     "/api/report/logo/remove": 4_096}        # trimmed copy), as base64 about 1.07 MB; a remove carries two words
 CLIENT_LEFT = (BrokenPipeError, ConnectionResetError)   # the page went mid-reply (BL-263, BL-284): logged at info, never a 500
 RELEASE_LIMIT = 60 * 1024 * 1024     # a release zip (BL-36)
 RELEASE_NAME = r"creaite-\d+\.\d+\.\d+\.zip"
@@ -1129,7 +1131,7 @@
     def body(self):
         """The request's JSON body ({} when empty); ValueError when it is over BODY_LIMIT."""
         n = int(self.headers.get("Content-Length") or 0)
-        if n > BODY_LIMIT:
+        if n > ROUTE_BODY_LIMITS.get(self.path.split("?")[0], BODY_LIMIT):
             raise ValueError("request too large")
         return json.loads(self.rfile.read(n) or b"{}") if n else {}
```
