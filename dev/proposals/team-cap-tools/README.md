# Team Cap review tooling (fixed issues only)

Scripts used in review for issues that are **already fixed in the published 2.6.1** (tag `v2.6.1`). Each one is expected to pass on 2.6.1 and to fail on a tree where the fix is missing.

Exploit scripts are committed for fixed issues only. Probes for issues that are not yet fixed are posted to the coordinator as issue comments, not committed.

All scripts are standard library only, take a checkout (or a release zip) as an argument, build throwaway fictional vaults under `$TMPDIR` (or the system temp folder), never write to the checkout and need no Microsoft 365. Run them with `python3 -I`.

Written against: v2.6.1 (5bf7da29)

| Script | What it proves | Usage | Expected on 2.6.1 |
|---|---|---|---|
| `h1_exploit.py` | A hostile `hold.json` planted in `system/staging/reextract/<run>/` cannot make `reextract.recover()` move files into the engine or outside the vault, plant a proposal or a record, or take pending minutes out of Review (H-1). | `python3 -I h1_exploit.py <checkout>` | Prints `EXPLOIT STOPPED`; exit 0 (1 = exploit worked, 2 = harness problem). The guard refuses every planting write. |
| `m1_probe.py` | A malformed top-level `note`, or an item's `values` as a string, in a proposal never rolls back the apply, and the item history still reads (M1). | `python3 -I m1_probe.py <checkout>` | Six lines ending `ok`, then `M1 FIXED`; exit 0 (1 = open). |
| `probe_matrix.py` | A Sensitive item never reaches any distributed output (draft and filed follow-up facts and email, Word, HTML, PDF, polish prompt, meeting hub), whatever the Track choice or kind, and ordinary controls still appear. Optional `--mutant no-withheld\|no-sensitive\|no-track` turns it red on purpose; `--json OUT` and `--keep` are also accepted. | `python3 -I probe_matrix.py <checkout>` | `LEAK cells: 0`, `MISSING cell values: 0`, `UNEXPECTED cell values: 0`; exit 0 (1 = a leak, 2 = harness error). |
| `smoke/smoke-261.sh` (`smoke_driver.py`) | The upgrade path: a vault from 2.6.0 takes the release zip with `update.py`, migrates without losing rows, passes doctor, draws the main pages in headless Chrome, undoes byte for byte, reinstalls and builds a fresh vault. | `sh smoke/smoke-261.sh <creaite-2.6.1.zip \| v2.6.1> [--old <zip\|tag>] [--chain] [--keep] [--work DIR] [--report FILE]` (needs Chrome; to download by tag it needs `gh` and `CREAITE_GH_REPO=OWNER/REPO`) | All steps PASS; exit 0. |
| `smoke/smoke_intake.py` | Through the real page over a 2.6.0 vault: `/api/autostart/status` and `/api/item/history` answer, and Intake Approve of a staged row saves. | `python3 -I smoke/smoke_intake.py <new zip> <old zip>` | Ends `RESULT: PASS` (always exits 0; read the last line). |
| `smoke/smoke_post.py` | First-click Approve saves for an action and a risk without `raised`, and a held button never saves its neighbour after the staged file is renumbered, with and without a records refresh. | `python3 -I smoke/smoke_post.py <new zip> <old zip> <work dir>` | Ends `RESULT: PASS` (always exits 0; read the last line). |

`smoke/lib/` holds the four helper modules the smoke scripts import, copied unchanged from the repository's `dev/tools` at the commit in `SOURCE-COMMIT` (the smoke runs are pinned to them). The smoke work folder defaults to `creaite-smoke-work` in the system temp folder.

Written against: v2.6.1 (5bf7da29). On a later tree, a failure may be a real regression or a change in the scripts' assumptions (file names, page markup); check which before reporting it.
