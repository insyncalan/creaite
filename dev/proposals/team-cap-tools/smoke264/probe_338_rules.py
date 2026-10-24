"""#338 (lighter runs part C): the rules file is slimmed by half and the detail moves to a reference file, with no rule lost.

  python3 -I probe_338_rules.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]

Checks, from the two zips and from a scratch vault updated from BASE to NEW:
  1  the new system/creaite-rules.md is at most half the size of the base's;
  2  system/templates/creaite-reference.md is in the new zip and the rules' opening note points to it;
  3  the Non-negotiables section is byte-identical to the base's;
  4  every sentence of the base rules that contains "never" appears verbatim in the new rules or the reference;
  5  update.py inspect lists the reference file as added; after the install it is in the vault, the engine files are in step
     and the vault's root CLAUDE.md imports only the rules file (the update never touched it);
  6  a fresh vault made from the new zip imports only the rules file, has the reference file, and doctor.py reports 0 failed.
Expected on 2.6.4 (base 2.6.3): all PASS (rules 32,736 bytes against 66,315; 81 of 81 "never" sentences kept, as this script splits sentences).
"""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import D, rec  # noqa: E402

REF = "system/templates/creaite-reference.md"


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def sentences(text):
    """Sentences (and table cells / bullets) that contain 'never', whitespace-normalised."""
    out = []
    for block in re.split(r"\n\s*\n|\n(?=[-|>#*])", text):
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z*`(])", block):
            s = norm(s)
            if re.search(r"\bnever\b", s, re.I):
                out.append(s)
    return out


def section(text, title):
    m = re.search(r"^## %s\n(.*?)(?=^## |\Z)" % re.escape(title), text, re.S | re.M)
    return m.group(0) if m else ""


def main():
    a = C.parse(__doc__)
    zb, zn = zipfile.ZipFile(a.base_zip), zipfile.ZipFile(a.new_zip)
    old = zb.read("system/creaite-rules.md").decode("utf-8")
    new = zn.read("system/creaite-rules.md").decode("utf-8")
    ref = zn.read(REF).decode("utf-8") if REF in zn.namelist() else ""
    ob, nb = len(old.encode()), len(new.encode())
    rec("1 rules file at most half the base's size", nb * 2 <= ob, f"{a.label}: {nb} bytes; {a.base_label}: {ob} bytes ({nb / ob:.1%})")
    rec("2 reference file in the zip and the rules point to it", bool(ref) and REF in new, f"{REF}: {len(ref.encode())} bytes; named in the rules: {REF in new}")
    o_nn, n_nn = section(old, "Non-negotiables"), section(new, "Non-negotiables")
    rec("3 Non-negotiables section byte-identical to the base", bool(o_nn) and o_nn == n_nn, f"{len(o_nn.encode())} bytes in the base, {len(n_nn.encode())} in the new")
    kept_from = norm(new + "\n" + ref)
    olds = sentences(old)
    missing = [s for s in olds if s not in kept_from]
    rec("4 every 'never' sentence of the base rules is kept (rules or reference)", bool(olds) and not missing,
        f"{len(olds) - len(missing)} of {len(olds)} found verbatim; missing: {[m[:70] for m in missing[:3]]}")

    v = C.V("r338", identity=None, calendar=False, install=False)
    try:
        plan = v.inspect_new()
        if not a.control:
            v.install_new()
        rec("5a update.py inspect lists the reference file as added", REF in plan.get("added", []),
            f"{plan.get('from')} -> {plan.get('to')}; added {plan.get('added')}")
        claude = (v.vault / "CLAUDE.md").read_text(encoding="utf-8") if (v.vault / "CLAUDE.md").exists() else ""
        imports = re.findall(r"^@(\S+)", claude, re.M)
        rec("5b updated vault: reference file present, rules in step, root CLAUDE.md imports only the rules",
            (v.vault / REF).is_file() and (v.vault / "system/creaite-rules.md").read_bytes() == new.encode() and imports == ["system/creaite-rules.md"],
            f"reference in vault {(v.vault / REF).is_file()}; rules bytes equal to the zip's {(v.vault / 'system/creaite-rules.md').read_bytes() == new.encode()}; imports {imports}")
        fresh = v.r.dir / "fresh"
        c, o = D.sh([sys.executable, "-I", a.new_zip, fresh], v.r.dir, v.r.env, check=False)
        fc = (fresh / "CLAUDE.md").read_text(encoding="utf-8") if (fresh / "CLAUDE.md").exists() else ""
        fi = re.findall(r"^@(\S+)", fc, re.M)
        c2, d = D.sh([fresh / "system/scripts/run", "doctor.py"], fresh, v.r.env, check=False)
        m = re.search(r"(\d+) passed, (\d+) failed", d)
        rec("6 fresh vault: imports only the rules, reference present, doctor 0 failed",
            c == 0 and fi == ["system/creaite-rules.md"] and (fresh / REF).is_file() and bool(m) and m.group(2) == "0",
            f"imports {fi}; reference {(fresh / REF).is_file()}; doctor exit {c2}: {m.group(0) if m else d[-150:]}; VERSION {(fresh / 'VERSION').read_text().strip() if (fresh / 'VERSION').exists() else '?'}")
    finally:
        v.close()
    return C.finish(a)


if __name__ == "__main__":
    C.run(main)
