# Client-output review kit (#239, refreshed for 2.5.x in #259, extended for 2.6 by group `k26` and for what 2.5.4 changed by group `k254`)

Every client-leak repro and probe written during the v2.5.0 to v2.5.3 reviews, with one runner. Not part of creaite's runtime. 101 probes (71 for 2.5.x, 25 for 2.6, 5 for what 2.5.4 changed).

## Run it (one command)

    export KIT_OUT=<a writable scratch directory>          # logs and results go here (default: <kit>/out)
    sh dev/proposals/review-kit/run_all.sh <checkout> [group[,group]|all|list]

`<checkout>` is any creaite tree with `dev/tests` and `system/scripts` (a worktree of the head under review). The kit never edits it.
Results: `$KIT_OUT/<tree-name>/SUMMARY.tsv` (script, variant, status, evidence) and `DETAIL.tsv` (one line per case); the last lines
print `PASS=n LEAK=n ERROR=n`. Whole kit about 25 to 35 minutes on a quiet Mac, one probe at a time. `KIT_ONLY=<id>[,<id>]` runs named
probes; `KIT_RECLASSIFY=1` reads the logs again after a classifier change; `KIT_MAXLOAD=55` waits while the 1-minute load is above it.

Groups: images audience header race page rename picture logos svg matchgate e2e k259 (the five 2.5.3 probes) k26 (the 25 probes of what 2.6 adds) k254 (the 5 probes of what 2.5.4 changed, for the merged 2.6 head). `run_all.sh <checkout> list`
prints the probes.

## Status words

- PASS: the probe ran to its end and nothing it plants reached a client output. A refusal is a PASS, shown as "refused" or HELD.
- LEAK: a client file that creaite produced (or filed) holds the planted material, or a hidden ID written loosely was not found.
- ERROR: the probe did not finish or cannot run on this tree (timeout, crash, import failure, no result line). Never PASS.
- SKIP (`k26`, `k254`): every case of the probe is about a feature the tree has not got (before #186, #275 or #279, say). Not a pass, not an error: it says what the probe could not test. (In `k254` a protection that is simply missing is judged on what the tree does, so it shows LEAK, not SKIP: see below.)

A clean refusal by creaite is HELD (counted PASS), not a leak: a probe that calls `creaite_doc.word_export` on a client document directly
is told "A client report is exported only from its checked copy ... nothing was exported" (a `DocError`). `classify.py` knows the refusal
classes (`PictureRefused`, `LogoRefused`, `PageRefused`, ...) always, and `DocError` / `SnapshotError` only with a refusal sentence
(`REFUSAL_WORDS`), so a fault such as a missing template stays an ERROR. Probes that need the renderer make the file the one way creaite
allows (`client_snapshot.TOKEN`, see `src/kitshim.py: client_word_export`), after printing the bare call's refusal as a HELD line.

## The 2.6 run (group `k26`)

    export KIT_OUT=<scratch>                                         # a git archive of the head under review is enough (no .git needed)
    sh dev/proposals/review-kit/run_all.sh <checkout-of-the-assembled-line> k26      # 25 probes, about 15 to 25 minutes, one at a time
    KIT_ONLY=k26-b-scrub,k26-b-save,k26-b-idpass sh dev/proposals/review-kit/run_all.sh <checkout> k26     # named probes
    KIT_MUTANTS=k26 KIT_TREES=<dir of archives of origin/v26-186, v253-release, v26-track-from-review-2> sh dev/proposals/review-kit/run_mutants.sh <any-checkout> <scratch>

Four scripts in `src/k26/`, one per area: `a186.py` (Draft email AI bar for an outside recipient, #186/#262/#263), `b232.py` (calendar saves behind
the Process and Refresh routes, #232/#264/#265), `c236.py` (followed people, #236), `d275.py` (Track from Review, #275/#268). Each prints
`### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence`. A probe finds out by itself whether the tree has the feature (it reads the source,
never the branch name) and SKIPs when it has not, so one command works on any tree from 2.5.3 to the assembled line. The three guarded
proposals the probes cover (`draft-ai-186/live_server.diff`, `track-from-review/tracker-track-problems.diff`, `followed-needs/vip-api.diff`) are applied to the
**vault's copy** inside the probe (never to the checkout), first judging the tree as it is and then, for the last two, with the diff in. The mutants
(`mutants-k26.tsv`) each name their own clean base tree: `email_outside_off` (v26-186), `scrub_letters_kept`, `sensitivity_off` and
`idpass_kept` (v253-release), `track_off` (v26-track-from-review-2); all five must show LEAK. A mutant file may start with `#sub: <old>|||<new>` lines (one exact replacement) for a
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
- `k26-b-idpass` (added 21-10-2026; 844 cases: 21 listed, 823 sampled, every 7th of the 5760 of 8 numbered labels x 10 password words x 9 connectors x 2 values x 4 numbers): a numbered ID label then a
  password-family word then a letters-only value (`Meeting ID 85212345678 and Password abcdefg`). Name the places that keep the value: `scrub` (title, place, organiser), `clean_row`, `calendar_row` and `calendar.json`.
  `v253-release` 76fe0d39 PASS (0 of 844), `v26-line-4` 103dad21 LEAK (588), `v26-invite-h1` aca7f5f4 LEAK (323), `v26-invite-h2` 9d8e89d8 PASS (0). Takes about 3 seconds. Mutant `idpass_kept`.
- `k26-b-bare`, every tree: **pre-existing on 2.5.3** (not part of the 2.6 regression): a label that needs a digit (`Password swordfish`, `PIN abcd`, a table row `PIN` / `kqzxyw`).
- `k26-c-api`, `v26-236-next` and `v26-line-2`: the page's `/api/vip` poll returns each followed row's `sigs` (page-only, LOW); closed by `followed-needs/vip-api.diff` (the probe shows it HELD with the diff in the vault's copy).
- `k26-d-apply`, `v26-track-from-review-2` and `v26-line-2`: a crossed item approved by hand is registered by `tracker.py apply` until `tracker-track-problems.diff` (guarded) is applied (HELD with it).

## The 2.5.4 run (group `k254`)

    export KIT_OUT=<scratch>
    sh dev/proposals/review-kit/run_all.sh <checkout-of-the-merged-2.6-head> k254          # 5 probes, about 90 seconds, one at a time
    KIT_MUTANTS=k254 KIT_TREES=<dir holding a git archive of origin/v254-release, named v254-release> sh dev/proposals/review-kit/run_mutants.sh <any-checkout> <scratch>

Five scripts in `src/k254/`, one per 2.5.4 change: `a277.py` (#277, a document whose project is not a string: `creaite_doc.check` and the six report
routes), `b282.py` (#282, the "Actions" heading wording must not let Internal-only text into a distributed HTML or Word export), `c279.py` (#279, a prep
page for a meeting with no project: Internal, portfolio Agendas only, no stale research, no overwrite, same-title meetings), `d280.py` (#280, the
held-proposal texts reach only the dashboard row, the proposal file and review.py), `e280.py` (#280, `{only}` on `/api/apply`, 40 hostile values and the
planted root namesake). Each prints `### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence`. Judgement rules:

- A probe judges what the tree DOES, not its branch name. A tree without #277 shows LEAK (16 cases: `creaite_doc.check` accepts the document, `match-check`
  answers HTTP 500), because for the merged head a dropped protection must be red, not skipped. SKIP is only for a feature that cannot be exercised at
  all: `k254-c-prepnoproject` on a tree before #279 (it refuses a meeting with no project: "Choose the meeting's project in the Prep brief first").
- The two #280 probes need the guarded 2.5.4 diffs. `patch/280/*.diff` is the kit's copy of the five (`tracker.py.diff`, `tracker-held.py.diff`,
  `live_server.py.diff`, `live_server-held.py.diff`, `tracker-round5.py.diff`; also in `dev/proposals/280/` of a 2.5.4 tree, which wins). A tree that has them
  (the 2.5.4 line) runs as it is. A tree that lacks them gets them applied to the **vault's copy** (`kitshim.apply_280`, never the checkout), and the probe says so
  (`e280`: "SKIP the route takes {only}" then the cases with `live_server.py.diff` applied; `d280`: "the held flow: tracker.py diffs ... applied to the vault's
  copy"). `d280` needs the unguarded part of #280 as well (`review.hold_missing` in `review.py`, the dashboard row): a tree without it (`v26-line-4`) cannot hold a
  proposal, so the held flow is a SKIP case and only the older apply stop is scanned.
- `d280`'s allowed places for the client name (from the transcript FILE NAME) and the held words: `dashboard.html` and its history snapshot, the held proposal
  file, the draft minutes it stages (and that draft's file-change backup), plus review.py's and apply's printed output (the controls). Everything else in
  the vault is scanned file by file (zips opened): debug log, Excel export, tracker database and its backups, client report (draft, Word, HTML, filed), weekly
  report, steerco one-pager, distributed minutes export, search index, other staging files; and the printed streams (`steerco-data`, `weekly-data`, search
  queries and context, AI draft contexts). The debug log may hold a PATH (ids, paths and counts), so the transcript path alone there is information, not a
  leak; the reason sentence is a leak. A second, older proposal with an invalid approved item and a fictional name in its meeting TITLE is held on its own: its
  title may be on its Review row, in its file and in Excel's Review sheet (a pending item's source, by design), nowhere else; the validation rule text
  ("unknown field(s) for decisions: raised") in the log and Excel is noted, not judged.
- The seven mutants (`mutants-k254.tsv`, base tree `v254-release`) remove: the #277 check (`docproject_check_off`), the distributed filter (`actions_filter_dropped`;
  applying `actions_wording` BEFORE `distributed_of` is not a leak and the probe, correctly, passes it), the prep page's Internal tag and "never sent"
  (`prep_internal_off`), the stale-research guard (`prep_stale_off`), the same-meeting guard of `place` (`prep_samemeeting_off`), the log line that keeps the reason
  out (`held_reason_logged`), and the `system/staging/` prefix of `{only}` (`only_prefix_dropped`). All seven must show LEAK.

### Results of the 2.5.4 run (22-10-2026; each tree a detached worktree of the head named)

| probe | v254-release 28a3edb7 | v26-line-4 7b12ab33 | main cfe9b56c (2.5.3) | main af54e733 (2.5.4 merged) |
|---|---|---|---|---|
| `k254-a-docproject` (74 cases) | PASS | LEAK (16: check accepts 12 shapes; `match-check` HTTP 500 for list, two-item list, dict, nested list) | LEAK (same 16) | PASS |
| `k254-b-actions` (20 / 12) | PASS | PASS (heading cases SKIP: no `actions_wording`; the leak cases pass) | PASS (same) | PASS |
| `k254-c-prepnoproject` (34) | PASS | SKIP (before #279) | SKIP | PASS |
| `k254-d-heldreason` (27 / 24) | PASS | PASS (held flow SKIP: no `review.hold_missing`; the older apply stop is clean, the debug log holds the transcript path only) | PASS (same) | PASS |
| `k254-e-onlyname` (52 / 53) | PASS | PASS (SKIP then judged with `live_server.py.diff` in the vault's copy) | PASS (same) | PASS |

No ERROR anywhere. Mutants: all seven LEAK on `v254-release`.

## Prove the kit still sees a real leak

    sh dev/proposals/review-kit/run_mutants.sh <checkout> <scratch-dir>

Runs `selftest_classify.py` (synthetic logs: a refusal is PASS, a produced client file with hidden text is LEAK, a fault is ERROR), then
for each line of `mutants.tsv` copies the checkout to the scratch directory, appends a deliberately broken gate from `mutants/` to the
copy (apply re-check off, loose-ID reading off, every file trusted, picture gate open), runs its probe there and requires LEAK. Use a
checkout the probes pass on (v253-client-k with `dev/proposals/client-output-k/client_leak.diff` applied in a scratch copy).

## Files

`src/k26/` (the 2.6 scripts), `src/k254/` (the 2.5.4 scripts), `patch/280/` (the five guarded #280 diffs), `mutants-k26.tsv`, `mutants-k254.tsv`, `run_all.sh` (runner: copies each script, rewrites hard-coded checkout paths, 600 s watchdog on its own PID, never `pkill -f`),
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
