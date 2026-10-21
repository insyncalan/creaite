# Client-output review kit (#239, refreshed for 2.5.x in #259)

Every client-leak repro and probe written during the v2.5.0 to v2.5.3 reviews, with one runner. Not part of creaite's runtime. 71 probes.

## Run it (one command)

    export KIT_OUT=<a writable scratch directory>          # logs and results go here (default: <kit>/out)
    sh dev/proposals/review-kit/run_all.sh <checkout> [group[,group]|all|list]

`<checkout>` is any creaite tree with `dev/tests` and `system/scripts` (a worktree of the head under review). The kit never edits it.
Results: `$KIT_OUT/<tree-name>/SUMMARY.tsv` (script, variant, status, evidence) and `DETAIL.tsv` (one line per case); the last lines
print `PASS=n LEAK=n ERROR=n`. Whole kit about 25 to 35 minutes on a quiet Mac, one probe at a time. `KIT_ONLY=<id>[,<id>]` runs named
probes; `KIT_RECLASSIFY=1` reads the logs again after a classifier change; `KIT_MAXLOAD=55` waits while the 1-minute load is above it.

Groups: images audience header race page rename picture logos svg matchgate e2e k259 (the five 2.5.3 probes). `run_all.sh <checkout> list`
prints the probes.

## Status words

- PASS: the probe ran to its end and nothing it plants reached a client output. A refusal is a PASS, shown as "refused" or HELD.
- LEAK: a client file that creaite produced (or filed) holds the planted material, or a hidden ID written loosely was not found.
- ERROR: the probe did not finish or cannot run on this tree (timeout, crash, import failure, no result line). Never PASS.

A clean refusal by creaite is HELD (counted PASS), not a leak: a probe that calls `creaite_doc.word_export` on a client document directly
is told "A client report is exported only from its checked copy ... nothing was exported" (a `DocError`). `classify.py` knows the refusal
classes (`PictureRefused`, `LogoRefused`, `PageRefused`, ...) always, and `DocError` / `SnapshotError` only with a refusal sentence
(`REFUSAL_WORDS`), so a fault such as a missing template stays an ERROR. Probes that need the renderer make the file the one way creaite
allows (`client_snapshot.TOKEN`, see `src/kitshim.py: client_word_export`), after printing the bare call's refusal as a HELD line.

## Prove the kit still sees a real leak

    sh dev/proposals/review-kit/run_mutants.sh <checkout> <scratch-dir>

Runs `selftest_classify.py` (synthetic logs: a refusal is PASS, a produced client file with hidden text is LEAK, a fault is ERROR), then
for each line of `mutants.tsv` copies the checkout to the scratch directory, appends a deliberately broken gate from `mutants/` to the
copy (apply re-check off, loose-ID reading off, every file trusted, picture gate open), runs its probe there and requires LEAK. Use a
checkout the probes pass on (v253-client-k with `dev/proposals/client-output-k/client_leak.diff` applied in a scratch copy).

## Files

`run_all.sh` (runner: copies each script, rewrites hard-coded checkout paths, 600 s watchdog on its own PID, never `pkill -f`),
`probes.tsv` (the manifest), `classify.py` (log to PASS / LEAK / ERROR), `selftest_classify.py`, `run_mutants.sh` + `mutants.tsv` +
`mutants/`, `INDEX.md` (what each probe proves, with the 2.5.3 refresh table), `CHECKLIST.md` (the six design rules, the routes, invariants
I1 to I18, and section F for the 2.5.3 classes), `src/` (the scripts; `src/k259/probe.py` is the new one), `patch/` (tolerance patches
applied to a copy). The probes find the checkout through `KIT_CK` (set by the runner); nothing refers to a particular worktree name.
Fictional data only.

## Results of the 2.5.3 refresh (71 probes, 21-10-2026)

| target | PASS | ERROR | LEAK |
|--------|------|-------|------|
| `origin/v253-client-k` 7e4d62b4 with `dev/proposals/client-output-k/client_leak.diff` applied in a scratch copy | 71 | 0 | 0 |
| `origin/v253-release` 23a9db25 | 64 | 0 | 7 |

The 7 on `v253-release` are the K-class leaks that `v253-client-k` closes: `rvlogofix-svg-fuzz` (K5: `<text>`/`<tspan>` words survive the SVG
rebuild), `ms1-fields` (K2: a section flipped to client on disk) and the five `k259-*` probes. Before the refresh the kit gave 52 PASS, 13
ERROR, 1 LEAK on `v253-client-k`; the LEAK was a refusal (see "Status words") and the ERRORs were kit code (see CHECKLIST section F).
