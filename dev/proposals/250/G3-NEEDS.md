# #250 G3: status of Cap's review finding (26-10-2026)

**Implemented in G3 revision 2** (`live_server-250.diff`, see `README-guarded.md` for the hash). The history below is kept.

**Case (rev 1): exit 0 with no final answer still wrote.** `Run._fetch_finish` set `answered = ended_well and proc.returncode == 0`, so a Claude
process that exited 0 without a `result` event (or with `is_error: true`, or empty text) counted as answered and `SweepFetch.finish(True)` wrote.
`SweepFetch` sees only `read_resource` results, never the stream's `result` event, so only the server could tell.

**The fix (rev 2):** `_fetch_finish` calls a small helper, `Run._answered(proc, final)`:

```
ended_well = not (self.stop or timed_out or failed)
result = getattr(self, "usage_result", None)      # set only by _on_result
return bool(ended_well and proc.returncode == 0 and isinstance(result, dict) and not result.get("is_error") and final)
```

Tests: `test_live_fetch_250` (exit 0 with an error result, with no result event, with an empty final: `finish(False)`; a good result and a final:
`finish(True)`; the helper itself) and one mutant per clause (all killed).
