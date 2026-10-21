# Client-output review kit (#239, refreshed for 2.5.x in #259, extended for 2.6 by group `k26`)

Every client-leak repro and probe written during the v2.5.0 to v2.5.3 reviews, with one runner. Not part of creaite's runtime. 95 probes (71 for 2.5.x, 24 for 2.6).

## Run it (one command)

    export KIT_OUT=<a writable scratch directory>          # logs and results go here (default: <kit>/out)
    sh dev/proposals/review-kit/run_all.sh <checkout> [group[,group]|all|list]

`<checkout>` is any creaite tree with `dev/tests` and `system/scripts` (a worktree of the head under review). The kit never edits it.
Results: `$KIT_OUT/<tree-name>/SUMMARY.tsv` (script, variant, status, evidence) and `DETAIL.tsv` (one line per case); the last lines
print `PASS=n LEAK=n ERROR=n`. Whole kit about 25 to 35 minutes on a quiet Mac, one probe at a time. `KIT_ONLY=<id>[,<id>]` runs named
probes; `KIT_RECLASSIFY=1` reads the logs again after a classifier change; `KIT_MAXLOAD=55` waits while the 1-minute load is above it.

Groups: images audience header race page rename picture logos svg matchgate e2e k259 (the five 2.5.3 probes) k26 (the 24 probes of what 2.6 adds). `run_all.sh <checkout> list`
prints the probes.

## Status words

- PASS: the probe ran to its end and nothing it plants reached a client output. A refusal is a PASS, shown as "refused" or HELD.
- LEAK: a client file that creaite produced (or filed) holds the planted material, or a hidden ID written loosely was not found.
- ERROR: the probe did not finish or cannot run on this tree (timeout, crash, import failure, no result line). Never PASS.
- SKIP (`k26`): every case of the probe is about a feature the tree has not got (before #186 or #275, say). Not a pass, not an error: it says what the probe could not test.

A clean refusal by creaite is HELD (counted PASS), not a leak: a probe that calls `creaite_doc.word_export` on a client document directly
is told "A client report is exported only from its checked copy ... nothing was exported" (a `DocError`). `classify.py` knows the refusal
classes (`PictureRefused`, `LogoRefused`, `PageRefused`, ...) always, and `DocError` / `SnapshotError` only with a refusal sentence
(`REFUSAL_WORDS`), so a fault such as a missing template stays an ERROR. Probes that need the renderer make the file the one way creaite
allows (`client_snapshot.TOKEN`, see `src/kitshim.py: client_word_export`), after printing the bare call's refusal as a HELD line.

## The 2.6 run (group `k26`)

    export KIT_OUT=<scratch>                                         # a git archive of the head under review is enough (no .git needed)
    sh dev/proposals/review-kit/run_all.sh <checkout-of-the-assembled-line> k26      # 24 probes, about 15 to 25 minutes, one at a time
    KIT_ONLY=k26-b-scrub,k26-b-save sh dev/proposals/review-kit/run_all.sh <checkout> k26     # named probes
    KIT_MUTANTS=k26 KIT_TREES=<dir of archives of origin/v26-186, v253-release, v26-track-from-review-2> sh dev/proposals/review-kit/run_mutants.sh <any-checkout> <scratch>

Four scripts in `src/k26/`, one per area: `a186.py` (Draft email AI bar for an outside recipient, #186/#262/#263), `b232.py` (calendar saves behind
the Process and Refresh routes, #232/#264/#265), `c236.py` (followed people, #236), `d275.py` (Track from Review, #275/#268). Each prints
`### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence`. A probe finds out by itself whether the tree has the feature (it reads the source,
never the branch name) and SKIPs when it has not, so one command works on any tree from 2.5.3 to the assembled line. The three guarded
proposals the probes cover (`draft-ai-186/live_server.diff`, `track-from-review/tracker-track-problems.diff`, `followed-needs/vip-api.diff`) are applied to the
**vault's copy** inside the probe (never to the checkout), first judging the tree as it is and then, for the last two, with the diff in. The mutants
(`mutants-k26.tsv`) each name their own clean base tree: `email_outside_off` (v26-186), `scrub_letters_kept` and `sensitivity_off` (v253-release),
`track_off` (v26-track-from-review-2); all four must show LEAK. A mutant file may start with `#sub: <old>|||<new>` lines (one exact replacement) for a
script that ends in `sys.exit(main())`. CHECKLIST section G says which probe needs which branch merged and what is expected on each tree today.

### Results of the 2.6 run (21-10-2026; trees are `git archive` copies of the heads named)

| probe | v253-release 76fe0d39 | v26-line-2 e9911257 | v26-186 ece270df | v26-232-next bea9de16 | v26-236-next 4fdf0065 | v26-track-from-review-2 ff96eda8 | v26-review-fixes 4468986f |
|---|---|---|---|---|---|---|---|
| `k26-a-ids` | SKIP | PASS | PASS | SKIP | SKIP | SKIP | SKIP |
| `k26-a-names` | SKIP | PASS | PASS | SKIP | SKIP | SKIP | SKIP |
| `k26-a-spoof` | SKIP | PASS | PASS | SKIP | SKIP | SKIP | SKIP |
| `k26-a-keys` | SKIP | PASS | PASS | SKIP | SKIP | SKIP | SKIP |
| `k26-a-place` | SKIP | PASS | PASS | SKIP | SKIP | SKIP | SKIP |
| `k26-b-scrub` | PASS | LEAK | PASS | PASS | PASS | PASS | LEAK |
| `k26-b-body` | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `k26-b-bare` | LEAK | LEAK | LEAK | LEAK | LEAK | LEAK | LEAK |
| `k26-b-save` | PASS | LEAK | PASS | PASS | PASS | PASS | LEAK |
| `k26-b-outputs` | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `k26-c-client` | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `k26-c-reports` | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `k26-c-exports` | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `k26-c-api` | SKIP | LEAK | SKIP | SKIP | LEAK | SKIP | SKIP |
| `k26-c-drafts` | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `k26-c-prep` | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `k26-c-search` | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `k26-c-log` | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `k26-d-followup` | SKIP | PASS | SKIP | SKIP | SKIP | PASS | SKIP |
| `k26-d-export` | SKIP | PASS | SKIP | SKIP | SKIP | PASS | SKIP |
| `k26-d-server` | SKIP | PASS | SKIP | SKIP | SKIP | PASS | SKIP |
| `k26-d-items` | SKIP | PASS | SKIP | SKIP | SKIP | PASS | SKIP |
| `k26-d-apply` | SKIP | LEAK | SKIP | SKIP | SKIP | LEAK | SKIP |
| `k26-d-promise` | SKIP | PASS | SKIP | SKIP | SKIP | PASS | SKIP |
| **total** | PASS 11, LEAK 1, SKIP 12 | PASS 19, LEAK 5 | PASS 16, LEAK 1, SKIP 7 | PASS 11, LEAK 1, SKIP 12 | PASS 11, LEAK 2, SKIP 11 | PASS 16, LEAK 2, SKIP 6 | PASS 9, LEAK 3, SKIP 12 |

No ERROR anywhere. What the LEAKs are:
- `k26-b-scrub` and `k26-b-save`, on `v26-line-2` and `v26-review-fixes`: **a real product finding (HIGH)**, `invite_clean.scrub` as changed in `4468986f` keeps a value that has no
  digit: `Steering Passcode: kqZxyw` becomes `Steering kqZxyw`, `Meeting ID 123 456 789 Passcode abcdef` becomes `abcdef`, `Weekly sync zoom.us 98765432101`
  becomes `Weekly sync 98765432101` (50 of 94 scrub cases; 16 of 31 saved-calendar cases; title, place and organiser, a confidential meeting's title too). 2.5.3 drops the whole field.
- `k26-b-bare`, every tree: **pre-existing on 2.5.3** (not part of the 2.6 regression): a label that needs a digit (`Password swordfish`, `PIN abcd`, a table row `PIN` / `kqzxyw`).
- `k26-c-api`, `v26-236-next` and `v26-line-2`: the page's `/api/vip` poll returns each followed row's `sigs` (page-only, LOW); closed by `followed-needs/vip-api.diff` (the probe shows it HELD with the diff in the vault's copy).
- `k26-d-apply`, `v26-track-from-review-2` and `v26-line-2`: a crossed item approved by hand is registered by `tracker.py apply` until `tracker-track-problems.diff` (guarded) is applied (HELD with it).

## Prove the kit still sees a real leak

    sh dev/proposals/review-kit/run_mutants.sh <checkout> <scratch-dir>

Runs `selftest_classify.py` (synthetic logs: a refusal is PASS, a produced client file with hidden text is LEAK, a fault is ERROR), then
for each line of `mutants.tsv` copies the checkout to the scratch directory, appends a deliberately broken gate from `mutants/` to the
copy (apply re-check off, loose-ID reading off, every file trusted, picture gate open), runs its probe there and requires LEAK. Use a
checkout the probes pass on (v253-client-k with `dev/proposals/client-output-k/client_leak.diff` applied in a scratch copy).

## Files

`src/k26/` (the 2.6 scripts), `mutants-k26.tsv`, `run_all.sh` (runner: copies each script, rewrites hard-coded checkout paths, 600 s watchdog on its own PID, never `pkill -f`),
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
