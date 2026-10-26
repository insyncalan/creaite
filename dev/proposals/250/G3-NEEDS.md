# #250 G3: what the guarded `live_server.py` still needs (Cap's review, 26-10-2026)

One change, in the guarded file `live_server-250.diff`; the ordinary side cannot close it.

**Case: exit 0 with no final answer still writes.** `Run._fetch_finish` sets `answered = ended_well and proc.returncode == 0`. A Claude
process that exits 0 without a `result` event (or whose `result` event has `is_error: true`) counts as answered, so `SweepFetch.finish(True)`
settles and writes. `SweepFetch` only sees `read_resource` results (`observe`), never the stream's `result` event, so it cannot tell.
The ordinary code stays fail-closed for everything it can see (`finish(False)` writes nothing, and a transcript it cannot tie to one
meeting is held), but whether the run answered is the server's fact.

**The line** (in `_fetch_finish`, `live_server-250.diff` line 72):

```
-            answered = ended_well and proc.returncode == 0
+            result = getattr(self, "usage_result", None)           # the stream's result event, set by _on_result
+            answered = (ended_well and proc.returncode == 0 and isinstance(result, dict) and not result.get("is_error") and bool(final))
```

`self.usage_result` is set only by `_on_result` (live_server.py `_on_result`, `self.usage_result = ev`), so it is None when no `result`
event arrived; `final` is already passed to `_fetch_finish(proc, final)` and is the result text. Both are available at that point.
Needs: a mutant in `test_live_fetch_250` (exit 0 with no result event writes nothing; a result with `is_error` writes nothing).
Complexity: `_fetch_finish` stays under the limit if the condition is moved into a small helper `_answered(proc, final)`.
