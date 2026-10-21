#!/bin/sh
# Mutants for the review kit: proves a REAL leak still shows as LEAK (the classifier's refusal rule must never hide one).
#   run_mutants.sh <clean-checkout> [scratch-dir]      (the checkout should be one the probes pass on, e.g. v253-client-k with client_leak.diff)
# For each line of mutants.tsv (name, file, probe) the checkout is copied (without .git) to <scratch>/<name>, mutants/<name>.py is appended
# to the file in the COPY, the probe is run on the copy, and the result must be LEAK. Nothing in the checkout is edited.
# env: KIT_MAXLOAD, KIT_PYTHON as for run_all.sh.   exit 0 when every mutant shows as LEAK, 1 otherwise.
set -u
KIT=$(cd "$(dirname "$0")" && pwd)
CK=${1:-}; [ -d "$CK/dev/tests" ] || { sed -n 2,7p "$0"; exit 2; }
SCR=${2:-$KIT/work/mutants}
TAB=$(printf '\t'); bad=0
python3 "$KIT/selftest_classify.py" || bad=1
while IFS=$TAB read -r name file probe; do
  [ -n "$name" ] || continue
  dir=$SCR/$name; rm -rf "$dir"; mkdir -p "$dir"
  ( cd "$CK" && tar --exclude=.git -cf - . ) | ( cd "$dir" && tar -xf - )
  cat "$KIT/mutants/$name.py" >> "$dir/$file"
  out=$SCR/out-$name
  KIT_OUT=$out KIT_ONLY=$probe sh "$KIT/run_all.sh" "$dir" all > "$SCR/$name.log" 2>&1
  got=$(awk -F'\t' -v p="$probe" '$1==p {print $3}' "$out/$name/SUMMARY.tsv" | tail -n 1)
  if [ "$got" = LEAK ]; then echo "mutant $name ($probe): LEAK, as it must"; else echo "mutant $name ($probe): ${got:-no result} (expected LEAK) <-- the kit missed a real leak"; bad=1; fi
done < "$KIT/mutants.tsv"
exit $bad
