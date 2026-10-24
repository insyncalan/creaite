"""Size of what every run loads (#338 N1), read only.

    python3 dev/tools/size_report.py [--root DIR] [--json]

Lists bytes and estimated tokens (bytes / 4) of the root CLAUDE.md, system/creaite-rules.md, the project memory template and each
.claude/skills/*/SKILL.md. Sizes only: nothing is read for its text beyond the byte count.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def files(root) -> list:
    """The (group, relative path) pairs that are loaded or may be loaded into a run."""
    root = Path(root)
    out = [("claude_md", "CLAUDE.md"), ("rules", "system/creaite-rules.md"),
           ("memory", "system/templates/project-CLAUDE-template.md"), ("vault_claude_md", "system/templates/vault-CLAUDE-template.md")]
    skills = root / ".claude" / "skills"
    if skills.is_dir():
        out += [("skill", str(p.relative_to(root))) for p in sorted(skills.glob("*/SKILL.md"))]
    return out


def measure(root=ROOT) -> list:
    """One dict per file that exists: group, path, bytes, tokens (bytes / 4, rounded up)."""
    root = Path(root)
    rows = []
    for group, rel in files(root):
        p = root / rel
        if p.is_file():
            n = p.stat().st_size
            rows.append({"group": group, "path": rel, "bytes": n, "tokens": -(-n // 4)})
    return rows


def table(rows) -> str:
    """A text table of measure()."""
    lines = [f"{'Bytes':>8}{'~Tokens':>9}  File"]
    lines += [f"{r['bytes']:>8}{r['tokens']:>9}  {r['path']}" for r in rows]
    skills = [r for r in rows if r["group"] == "skill"]
    lines.append(f"{sum(r['bytes'] for r in skills):>8}{sum(r['tokens'] for r in skills):>9}  all {len(skills)} skills (loaded when named)")
    return "\n".join(lines)


def main(argv=None) -> int:
    """Print the sizes."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rows = measure(a.root)
    print(json.dumps(rows, separators=(",", ":")) if a.json else table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
