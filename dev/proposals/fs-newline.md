# live_server.py: /api/fs keeps a file's line endings (proposal, M1)

**Status: a proposal for Alan's yes. `live_server.py` is a guarded file; nothing here is applied.**

## README

Team Cap's review of the client report setting writes (finding M1): the page changes a project's `CLAUDE.md` by reading it through
`POST /api/fs {op: "read"}`, saving a backup copy of that text, and writing the edited text back with `{op: "write"}`.
The read uses `Path.read_text`, which turns every CRLF into LF. So a `CLAUDE.md` saved with Windows line endings comes back all LF:
the file is rewritten with different line endings from the ones it had, and the backup (made from the text that was read) is
already converted, so it is not a copy of the original.

The write side already keeps what it is given on macOS (`paths.write_text_atomic` writes "\r\n" as it is). The only fault is the read.
The fix is to read with `newline=""`, which hands the text back untouched. Nothing else changes: LF files read exactly as before.

## The exact diff (against `system/scripts/live_server.py`, in `Handler.fs`)

```diff
@@ -1257,7 +1257,9 @@ class Handler(BaseHTTPRequestHandler):
         if op == "read":
             if not p.is_file():
                 return self.send(404, {"ok": False, "message": f"not found: {rel}"})
-            return self.send(200, {"ok": True, "text": p.read_text(encoding="utf-8")})
+            with open(p, encoding="utf-8", newline="") as fh:
+                text = fh.read()
+            return self.send(200, {"ok": True, "text": text})
         if op == "remove":
             p.unlink(missing_ok=True)
             return self.send(200, {"ok": True})
```

(`paths.write_text_atomic` could also open its temporary file with `newline=""` so the write is exact on every platform; it is not
a guarded file and nothing on macOS needs it, so it is left out of this proposal.)

## The test

`dev/tests/test_fs_newline.py` (a live server in a throwaway vault): it makes the project's `CLAUDE.md` all CRLF, reads it through
`/api/fs`, checks the text still has its CRLF and that the backup copy the page would make is byte-identical to the original, then writes
an edited value back and checks that only that value differs and every line ending is still CRLF.

- It is **skipped** (with the reason shown) until the diff is applied, so the suite stays green.
- Against the current file it fails: `FS_NEWLINE_FORCE=1 python3 dev/tests/test_fs_newline.py` ends with
  `AssertionError: '\r\n' not found in '# ABC ... \n ...' : the text comes back with its CRLF`.
- With the diff applied: `python3 dev/tests/test_fs_newline.py` passes (checked on a scratch copy of the change, then put back).
