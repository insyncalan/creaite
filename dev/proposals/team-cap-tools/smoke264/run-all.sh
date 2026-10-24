#!/bin/sh
# Run every smoke264 probe in turn (one at a time: each builds its own throwaway vault and stops what it started).
#
#   sh run-all.sh NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]
#
# Prints one line per probe and a summary; exit 0 only if every probe exited 0 (a probe's exit 2 is a harness problem, not a pass).
# Needs: python3 (3.9+), Google Chrome, lsof. Nothing is installed, downloaded or sent anywhere.
set -u
here=$(cd "$(dirname "$0")" && pwd)
[ $# -ge 3 ] || { sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
py=""
for c in python3.14 python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$c" >/dev/null 2>&1; then py=$(command -v "$c"); break; fi
done
[ -n "$py" ] || { echo "run-all.sh: no python3 on PATH" >&2; exit 2; }
fail=0
summary=""
for p in probe_338_rules probe_345_expect probe_334_budget probe_346_runsetup probe_discard_rollback \
         probe_ui_today probe_ui_layout probe_ui_profile probe_ui_milestones_drawer probe_ui_words; do
  echo "=== $p"
  "$py" -I "$here/$p.py" "$@"
  code=$?
  summary="$summary
$p: exit $code"
  [ "$code" -eq 0 ] || fail=1
done
echo
echo "=== summary$summary"
exit $fail
