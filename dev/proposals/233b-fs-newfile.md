# live_server.py: /api/fs creates a CLAUDE.md only in an existing project's folder (proposal, #233 L7)

**Status: a proposal for Alan's yes. `live_server.py` is a guarded file; nothing here is applied.**

## README

Team Cap's review (finding L7): `FS_RULES` lets `/api/fs` write `projects/[^/]+/CLAUDE\.md`, and a write creates the file when it
is missing. So a call with the token created a `CLAUDE.md` under `_Archive`, `_portfolio`, a name that is no project (`nope`) and a
hidden folder (`.hidden`). The setting write only ever edits a project's existing memory file, so nothing legitimate needs this.

The diff adds one rule: a write that would **create** `projects/<name>/CLAUDE.md` is refused unless `<name>` is an existing
project folder (the folder is already there, does not start with `.` or `_`, and is not one of the register's `never_index`
folders). Writing an existing file, or re-creating a missing `CLAUDE.md` inside a real project folder, works as before.

## The exact diff (against `system/scripts/live_server.py`)

```diff
@@ -675,6 +675,13 @@ def undo_note_move():
 # ===== end #124 =====


+def existing_project_folder(name):
+    """True when `name`, a folder directly under projects/, is an existing project's own folder: not hidden, not _Archive or
+    _portfolio (a leading underscore), not one the register never indexes, and already there."""
+    never = {str(n) for n in (paths.locations().get("never_index") or [])}
+    return not name.startswith((".", "_")) and name not in never and paths.resolve(f"projects/{name}").is_dir()
+
+
 def allowed(op, rel):
@@ -1265,6 +1272,8 @@ class Handler(BaseHTTPRequestHandler):
         if op == "upload":
             return self.fs_upload(p, req)
+        if op == "write" and not p.exists() and re.fullmatch(r"projects/[^/]+/CLAUDE\.md", rel) and not existing_project_folder(rel.split("/")[1]):
+            return self.send(403, {"ok": False, "message": f"{rel} can be created only in an existing project's folder"})
         clash = settings_notes_clash(p, req.get("text", "")) if op == "write" and p == paths.SETTINGS else None
```

## The test

`dev/tests/test_fs_newfile.py` (a live server in a throwaway vault): writes to `projects/_Archive|_portfolio|nope|.hidden|Zzz Not A
Project/CLAUDE.md` are refused and create nothing; an existing project's file is still written and a missing one in the project's own
folder is created.

- It is **skipped** until the diff is applied, so the suite stays green.
- Against the current file it fails: `FS_NEWFILE_FORCE=1 python3 dev/tests/test_fs_newfile.py` ends with `FAILED (failures=1)`.
- With the diff applied it passes (5 tests, checked on the change in the worktree, then put back).
