# live_server.py: /api/fs refuses a write over a file that changed since the page read it (proposal, #233 L5)

**Status: a proposal for Alan's yes. `live_server.py` is a guarded file; nothing here is applied.**

## README

Team Cap's review of the client report setting writes (finding L5): the page changes a project's `CLAUDE.md` by reading it, making a
backup, and writing the edited text back. Two browser tabs can do this at once, and the second write silently replaces the first
tab's change (Cap lost an update in 30 of 30 parallel runs). The page now reads the file again just before it writes and refuses
when it differs (the window between that read and the write is small but not zero). This proposal closes that window on the server.

The page already sends `expect_text` with the write: the text the file held when it was read. With this diff the server compares it
with the file under its own lock and answers 409 with a plain sentence, writing nothing, when they differ. A write with no
`expect_text` behaves exactly as before; a server without this diff ignores the key, so the page works either way.

## The exact diff (against `system/scripts/live_server.py`, in `Handler.fs`, just before the `settings_notes_clash` line)

```diff
@@ -1265,6 +1272,12 @@ class Handler(BaseHTTPRequestHandler):
         if op == "upload":
             return self.fs_upload(p, req)
+        expect = req.get("expect_text")
+        if op == "write" and isinstance(expect, str) and p.is_file():
+            with LOCK:                             # #233 L5: a file that changed since the page read it is never written over
+                with open(p, encoding="utf-8", newline="") as fh:
+                    changed = fh.read() != expect
+                if not changed:
+                    paths.write_text_atomic(p, req.get("text", ""))
+            if changed:
+                return self.send(409, {"ok": False, "message": f"{rel} changed since it was read, so nothing was saved; try again"})
+            return self.send(200, {"ok": True})
         clash = settings_notes_clash(p, req.get("text", "")) if op == "write" and p == paths.SETTINGS else None
```

(Only the vault-relative path is in the message, never an absolute one. `LOCK` is the module's existing lock; it is not held
anywhere else in `fs` at this point, so it cannot nest.)

## The test

`dev/tests/test_fs_check.py` (a live server in a throwaway vault): a write with `expect_text` over a file another tab changed is
refused with 409, the file keeps the other tab's text; the same write with the current text goes through; a write with no
`expect_text` is as before.

- It is **skipped** (with the reason shown) until the diff is applied, so the suite stays green.
- Against the current file it fails: `FS_CHECK_FORCE=1 python3 dev/tests/test_fs_check.py` ends with `FAILED (failures=1)`.
- With the diff applied: `python3 dev/tests/test_fs_check.py` passes (5 tests, checked on the change in the worktree, then put back).
