"""Write cx-edit's field list (BL-249) from schema.sql into .claude/skills/cx-edit/SKILL.md (development only).

Run: python3 dev/tools/skill_fields.py [--check]
  --check  change nothing; exit 1 if the block in SKILL.md differs from schema.sql

The block sits between propose.SKILL_START and propose.SKILL_END; propose.fields_block() builds it, so the skill, the
`propose.py fields` command and the test all read one list.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system" / "scripts"))
import propose  # noqa: E402

SKILL = ROOT / ".claude" / "skills" / "cx-edit" / "SKILL.md"


def current(text):
    """The block as it stands in SKILL.md, or None."""
    a, b = text.find(propose.SKILL_START), text.find(propose.SKILL_END)
    return text[a:b + len(propose.SKILL_END)] if a >= 0 and b > a else None


def main(argv):
    text = SKILL.read_text(encoding="utf-8")
    have, want = current(text), propose.fields_block()
    if have is None:
        sys.exit(f"{SKILL}: no BL-249 fields block (add the two marker lines first)")
    if have == want:
        print("cx-edit's field list matches schema.sql.")
        return 0
    if "--check" in argv:
        print("cx-edit's field list differs from schema.sql: run python3 dev/tools/skill_fields.py")
        return 1
    SKILL.write_text(text.replace(have, want), encoding="utf-8")
    print(f"Updated the field list in {SKILL.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
