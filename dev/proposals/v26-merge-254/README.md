# v26-merge-254: VERSION 2.5.3 -> 2.5.4 (a guarded file: the HOPD applies it)

`VERSION.diff` sets `VERSION` to 2.5.4, the release this branch merges (the merge kept line-4's 2.5.3). From the repo root:
`git apply --check dev/proposals/v26-merge-254/VERSION.diff && git apply dev/proposals/v26-merge-254/VERSION.diff`
(checked clean, and `git apply -R --check` on the result). Nothing else needs rebuilding: the guides already say 2.5.4
(`python3 dev/tools/build_guides.py --check` says "Out of date" with VERSION at 2.5.3 and "Guides are up to date." with 2.5.4),
and `build_dashboard_js.py globals`, `split_dashboard.py build` and `build_guides.py` change no file once it is applied.
