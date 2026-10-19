#!/bin/sh
# Review kit for the client-output review of #239 (run one probe at a time; nothing is written in the checkout).
#
#   run_all.sh <checkout-path> [group[,group...]|all|list]
#
# groups: images audience header race page rename picture logos svg matchgate e2e   (default: all; "list" prints the probes)
# env:    KIT_TIMEOUT   seconds per probe (default 600)        KIT_MAXLOAD  wait while the 1-minute load is above this (default 40)
#         KIT_PYTHON    python to use (default python3)         KIT_PDF      0 = skip the PDF export in the msweep1 probes (default 1)
#         KIT_OUT       output root (default <kit>/out)         KIT_ONLY     run only the probe ids named here (comma list)
#         KIT_RECLASSIFY=1  do not run anything: read the logs already in <KIT_OUT>/<tree-name>/ again (after a classifier change)
# output: <KIT_OUT>/<tree-name>/<id>.log   one log per probe        SUMMARY.tsv  script, variant, status, evidence (one line per probe)
#         DETAIL.tsv  one line per case inside a probe (CSS case, mutation, page case ...)
# status: PASS = the probe ran to its end and nothing reached the client output;  LEAK = something did;
#         ERROR = the probe did not finish or could not be read (timeout, crash, import failure): never PASS.
# POSIX sh only: no arrays, no pkill -f; the only processes stopped are this script's own probe and the processes it started
# (recorded as PID + start time every 5 s while it runs), by PID.
set -u
# zsh (when somebody runs `zsh run_all.sh`) must split words the way sh does
if [ -n "${ZSH_VERSION:-}" ]; then emulate sh; setopt SH_WORD_SPLIT 2>/dev/null; fi
KIT=$(cd "$(dirname "$0")" && pwd)
CK_ARG=${1:-}
GROUP=${2:-all}
[ -n "$CK_ARG" ] || { sed -n '2,13p' "$0"; exit 2; }
[ -d "$CK_ARG/dev/tests" ] || { echo "not a creaite checkout: $CK_ARG" >&2; exit 2; }
CK=$(cd "$CK_ARG" && pwd)
TREE=$(basename "$CK")
PY=${KIT_PYTHON:-python3}
TIMEOUT=${KIT_TIMEOUT:-600}
MAXLOAD=${KIT_MAXLOAD:-40}
OUT=${KIT_OUT:-$KIT/out}/$TREE
WORK=$KIT/work/$TREE
ONLY=${KIT_ONLY:-}
MAN=$KIT/probes.tsv

if [ "$GROUP" = list ]; then
  awk -F'\t' '!/^#/ && NF>=8 {printf "%-24s %-34s %s %s\n", $1, $2, $4, $8}' "$MAN"; exit 0
fi

mkdir -p "$OUT" "$WORK"
export CREAITE_BROWSER_SLOTS=4
export PYTHONDONTWRITEBYTECODE=1
export KIT_CK="$CK"
export KIT_PDF=${KIT_PDF:-1}
SUMMARY=$OUT/SUMMARY.tsv
DETAIL=$OUT/DETAIL.tsv
printf 'script\tvariant\tstatus\tevidence\n' > "$SUMMARY"
printf 'script\tcase\tstatus\tevidence\n' > "$DETAIL"

load1() { sysctl -n vm.loadavg 2>/dev/null | awk '{gsub(/[{}]/,""); print int($1)}'; }

wait_load() {
  n=0
  while :; do
    l=$(load1); l=${l:-0}
    [ "$l" -le "$MAXLOAD" ] && return 0
    n=$((n+1)); [ $n -gt 60 ] && { echo "  (load $l still above $MAXLOAD after 10 minutes: going on)"; return 0; }
    echo "  (load $l above $MAXLOAD: waiting 10 s)"; sleep 10
  done
}

# every descendant PID of $1 (not $1 itself), from ps; no process is matched by name
descendants() {
  ps -A -o pid=,ppid= | awk -v root="$1" '
    { kid[$2] = kid[$2] " " $1 }
    function walk(p,   a, n, i) { n = split(kid[p], a, " "); for (i = 1; i <= n; i++) { print a[i]; walk(a[i]) } }
    END { walk(root) }'
}

kill_tree() {
  pids=$(descendants "$1")
  kill -TERM $pids "$1" 2>/dev/null
  sleep 3
  kill -KILL $pids "$1" 2>/dev/null
  return 0
}

in_group() {   # $1 = comma list of the probe's groups
  [ "$GROUP" = all ] && return 0
  old=$IFS; IFS=,
  for want in $GROUP; do
    for have in $1; do [ "$want" = "$have" ] && { IFS=$old; return 0; }; done
  done
  IFS=$old; return 1
}

in_only() {
  [ -z "$ONLY" ] && return 0
  old=$IFS; IFS=,
  for w in $ONLY; do [ "$w" = "$1" ] && { IFS=$old; return 0; }; done
  IFS=$old; return 1
}

TAB=$(printf '\t')
count=0
while IFS=$TAB read -r id groups mode target args envs cls variant note; do
  case "$id" in ''|'#'*) continue;; esac
  in_group "$groups" || continue
  in_only "$id" || continue
  count=$((count+1))
  if [ "${KIT_RECLASSIFY:-0}" = 1 ]; then
    if [ -f "$OUT/$id.log" ]; then
      "$PY" "$KIT/classify.py" "$id" "$cls" "$variant" "$OUT/$id.log" "$SUMMARY" "$DETAIL" auto "" || printf '%s\t%s\tERROR\tclassifier failed\n' "$id" "$variant" >> "$SUMMARY"
    else
      printf '%s\t%s\tERROR\tno log (probe not run)\n' "$id" "$variant" >> "$SUMMARY"
    fi
    tail -n 1 "$SUMMARY"; continue
  fi
  wd=$WORK/$id; rm -rf "$wd"; mkdir -p "$wd"
  # copy (never edit the originals), then point the hard-coded checkout paths at this checkout
  cp "$KIT/src/$target" "$wd/" ; cp "$KIT/src/kitshim.py" "$KIT/src/kitrun.py" "$wd/"
  base=$(basename "$target")
  sed "s#${REPO_ROOT}/.claude/worktrees/[^/\"']*#$CK#g" "$wd/$base" > "$wd/$base.tmp" && mv "$wd/$base.tmp" "$wd/$base"
  [ "$envs" = - ] && envs=
  [ "$args" = - ] && args=
  # a probe-specific tolerance patch (patch/<script>.sed), applied to the copy only
  if [ -f "$KIT/patch/$base.sed" ]; then sed -f "$KIT/patch/$base.sed" "$wd/$base" > "$wd/$base.tmp" && mv "$wd/$base.tmp" "$wd/$base"; fi
  a=$(printf '%s' "$args" | sed "s#{CK}#$CK#g")
  log=$OUT/$id.log
  echo "[$id] $mode $base $a ${envs:+($envs)}"
  wait_load
  : > "$log"
  start=$(date +%s)
  if [ "$mode" = module ]; then
    mod=${base%.py}
    ( cd "$wd" && exec env ${envs:+$envs} "$PY" kitrun.py module "$mod" $a ) > "$log" 2>&1 &
  else
    ( cd "$wd" && exec env ${envs:+$envs} "$PY" kitrun.py script "$base" $a ) > "$log" 2>&1 &
  fi
  pid=$!
  # watchdog on the probe's own PID: after $TIMEOUT s stop it and its descendants; every 5 s note its descendants (PID|start time)
  : > "$wd/started.txt"
  (
    i=0
    while [ $i -lt "$TIMEOUT" ] && kill -0 "$pid" 2>/dev/null; do
      if [ $((i % 5)) -eq 0 ]; then
        for p in $(descendants "$pid"); do echo "$p|$(ps -o lstart= -p "$p" 2>/dev/null)"; done >> "$wd/started.txt"
      fi
      sleep 1; i=$((i+1))
    done
    if kill -0 "$pid" 2>/dev/null; then
      echo "### kit: TIMEOUT after ${TIMEOUT}s: stopping pid $pid" >> "$log"
      kill_tree "$pid"
    fi
  ) &
  wdpid=$!
  wait "$pid"; rc=$?
  kill "$wdpid" 2>/dev/null; wait "$wdpid" 2>/dev/null
  # a process the probe started and did not stop (same PID, same start time) is stopped now
  left=0
  for rec in $(sort -u "$wd/started.txt" | tr ' ' '_'); do
    p=${rec%%|*}; was=$(printf '%s' "${rec#*|}" | tr '_' ' ')
    now=$(ps -o lstart= -p "$p" 2>/dev/null)
    if [ -n "$now" ] && [ "$now" = "$was" ]; then kill -TERM "$p" 2>/dev/null; left=$((left+1)); fi
  done
  if [ $left -gt 0 ]; then sleep 2; echo "### kit: stopped $left process(es) the probe left running" >> "$log"; fi
  secs=$(( $(date +%s) - start ))
  echo "### kit: exit $rc after ${secs}s" >> "$log"
  "$PY" "$KIT/classify.py" "$id" "$cls" "$variant" "$log" "$SUMMARY" "$DETAIL" "$rc" "$a" || \
    printf '%s\t%s\tERROR\tclassifier failed\n' "$id" "$variant" >> "$SUMMARY"
  tail -n 1 "$SUMMARY"
done < "$MAN"

echo "ran $count probe(s) on $TREE; results: $SUMMARY"
awk -F'\t' 'NR>1 {n[$3]++} END {for (k in n) printf "%s=%d ", k, n[k]; print ""}' "$SUMMARY"
