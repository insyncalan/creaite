# Client-output review kit (#239)

Every client-leak repro and probe written during the v2.5.0 review, with one runner. Not part of creaite's runtime.

- `run_all.sh <checkout> [group,...|all|list]` (`KIT_ONLY=<id>` runs one probe): runs one probe at a time on copies of the scripts, rewrites hard-coded checkout paths, 600 s watchdog on its own PID (never `pkill -f`), a timeout, crash or vacuous run is ERROR, never PASS. Groups: images, audience, header, race, page, rename, picture, logos, svg, matchgate, e2e.
- `probes.tsv` (66 probes), `INDEX.md` (what each proves, how to run it, known result), `CHECKLIST.md` (the six design rules, the routes that change, the 18 invariants I1 to I18, each with the probes that exercise it), `classify.py` (turns a log into PASS / LEAK / ERROR), `src/` (the scripts, paths sanitised).
- Before running: `export REPO_ROOT=<this repo's checkout used for the tree under test>` and `export KIT_SCRATCH=<a writable scratch directory>`; the scripts and the runner refer to both. Where a probe needs a helper that was removed (`tiny_png`), the runner restores it in memory. Set `KIT_SVG_CLEAN=module.function` if step 1 names the SVG rebuild differently.
- Known results on `v250-audience4` 9ce10957: 66 probes, 50 PASS, 11 LEAK, 5 ERROR (see the #239 comment).
