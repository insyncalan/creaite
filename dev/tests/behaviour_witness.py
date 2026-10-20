"""#89: writes dev/tests/behaviour_witness.json, the screen (or dialog script) whose run must reach each popup site in the code.

The keys test runs in three files (KEYS_PARTS in test_shared_behaviour.py). "Every popup in the code is reached by some screen" cannot
be asked of a part that sees only its own screens, so each site is judged in the part that holds its witness. Run each part with
SB_WITNESS=<file> (it writes what each of its screens and dialog scripts reached), then give the three files here:

    SB_WITNESS=/tmp/a.json python3 dev/tests/test_shared_behaviour.py SharedBehaviour
    SB_WITNESS=/tmp/b.json python3 dev/tests/test_shared_behaviour_b.py
    SB_WITNESS=/tmp/c.json python3 dev/tests/test_shared_behaviour_c.py
    python3 dev/tests/behaviour_witness.py /tmp/a.json /tmp/b.json /tmp/c.json

The witness of a site is the first screen, in SCREENS' order and then the dialog scripts', that reaches it (every site that shares
its name, where two do). A site no screen reaches has none: it belongs in behaviour_expected_failures.json as "unreached".
Not a test (no test_ prefix).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
import test_shared_behaviour as sb  # noqa: E402


def main(files):
    by_unit = {}
    for f in files:
        by_unit.update(json.loads(Path(f).read_text(encoding="utf-8")))
    order = [u for u in sb.SCREENS if u in by_unit] + [k[1] for k in sb.Keys.KEYED if k[1] in by_unit]
    missing = [u for u in list(sb.SCREENS) + [k[1] for k in sb.Keys.KEYED] if u not in by_unit]
    if missing:
        sys.exit(f"No run reported: {', '.join(missing)}. Give the files of all the parts.")
    sites = {}
    for s in sb.inventory():
        sites.setdefault(sb.site_name(s), []).append(s)
    out, unreached = {}, []
    for name in sorted(sites):
        hit = next((u for u in order if all(sb.reached(s, by_unit[u]) for s in sites[name])), None)
        if hit:
            out[name] = hit
        else:
            unreached.append(name)
    sb.WITNESS_FILE.write_text(json.dumps(out, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(out)} sites have a witness; {len(unreached)} reached by no screen (they belong in "
          f"{sb.EXPECTED_FILE.name} as unreached):")
    for n in unreached:
        print("  unreached:", n)


if __name__ == "__main__":
    main(sys.argv[1:])
