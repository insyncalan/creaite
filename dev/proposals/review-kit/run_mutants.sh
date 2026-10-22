#!/bin/sh
# Mutants for the review kit: proves a REAL leak still shows as LEAK (the classifier's refusal rule must never hide one).
#   run_mutants.sh <clean-checkout> [scratch-dir]      (the checkout should be one the probes pass on, e.g. v253-client-k with client_leak.diff)
#   KIT_MUTANTS=k26|k254 KIT_TREES=<dir of trees> run_mutants.sh <any-checkout> [scratch-dir]
#       the 2.6 mutants (mutants-k26.tsv): each line names its own clean base tree (a folder of that name in $KIT_TREES, e.g. a git archive of
#       origin/v26-186), the file to break, the probe and the base; <any-checkout> is only used for the lines that name no base
# For each line of mutants.tsv (name, file, probe) the checkout is copied (without .git) to <scratch>/<name>, mutants/<name>.py is appended
# to the file in the COPY, the probe is run on the copy, and the result must be LEAK. Nothing in the checkout is edited.
# env: KIT_MAXLOAD, KIT_PYTHON as for run_all.sh.   exit 0 when every mutant shows as LEAK, 1 otherwise.
set -u
KIT=$(cd "$(dirname "$0")" && pwd)
CK=${1:-}; [ -d "$CK/dev/tests" ] || { sed -n 2,7p "$0"; exit 2; }
SCR=${2:-$KIT/work/mutants}
TAB=$(printf '\t'); bad=0
python3 "$KIT/selftest_classify.py" || bad=1
LIST=$KIT/mutants.tsv; case "${KIT_MUTANTS:-}" in k26|k254) LIST=$KIT/mutants-${KIT_MUTANTS}.tsv;; esac
while IFS=$TAB read -r name file probe base; do
  [ -n "$name" ] || continue
  CKM=$CK; if [ -n "${base:-}" ]; then CKM=${KIT_TREES:-}/$base; [ -d "$CKM/dev/tests" ] || { echo "mutant $name: base tree $CKM not found (set KIT_TREES)"; bad=1; continue; }; fi
  dir=$SCR/$name; rm -rf "$dir"; mkdir -p "$dir"
  ( cd "$CKM" && tar --exclude=.git -cf - . ) | ( cd "$dir" && tar -xf - )
  # a mutant file is appended to the copy; lines "#sub: <old>|||<new>" at its top are applied first as one exact text replacement (a mutant for a
  # script that ends in `sys.exit(main())` cannot be appended: the replacement reaches the function itself)
  python3 - "$dir/$file" "$KIT/mutants/$name.py" <<'PYEOF' || { echo "mutant $name: could not be applied"; bad=1; continue; }
import sys
target, mutant = sys.argv[1:3]
text = open(target, encoding="utf-8").read()
rest = []
for line in open(mutant, encoding="utf-8").read().split("\n"):
    if line.startswith("#sub: "):
        old, new = line[6:].split("|||", 1)
        old, new = old.replace("\\n", "\n"), new.replace("\\n", "\n")
        if text.count(old) != 1:
            sys.exit("the text to replace is not in the file exactly once: " + old[:60])
        text = text.replace(old, new)
    else:
        rest.append(line)
open(target, "w", encoding="utf-8").write(text + "\n".join(rest))
PYEOF
  out=$SCR/out-$name
  KIT_OUT=$out KIT_ONLY=$probe sh "$KIT/run_all.sh" "$dir" all > "$SCR/$name.log" 2>&1
  got=$(awk -F'\t' -v p="$probe" '$1==p {print $3}' "$out/$name/SUMMARY.tsv" | tail -n 1)
  if [ "$got" = LEAK ]; then echo "mutant $name ($probe): LEAK, as it must"; else echo "mutant $name ($probe): ${got:-no result} (expected LEAK) <-- the kit missed a real leak"; bad=1; fi
done < "$LIST"
exit $bad
