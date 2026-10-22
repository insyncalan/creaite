# guardtest

`tests-yml-fetch-depth.diff` (guarded: `.github`): sets `fetch-depth: 0` on both checkouts in `.github/workflows/tests.yml`, so check 9
of `test_word_export_227.py` has history to diff against and runs in CI. Without it the shallow clone has no history. The test now
FAILS (not skips) when `CI=true` and the base commit is missing, so a CI run without this diff is red rather than quietly green.
Checked with `git apply --check` and `git apply -R --check`.
