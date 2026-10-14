"""BL-249 (fix-field-names): ask creaite guessed milestone field names. The unknown-field message names the valid fields
and suggests the right one; `propose.py fields <table>` lists them and writes nothing; cx-edit's SKILL.md carries the
list generated from schema.sql (a docs-shape test); ASK_PROMPT says to preview before a spec is ready.

Run: python3 dev/tests/test_spec_fields.py
"""
import json
import re
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "system" / "scripts"))
from test_tracker import Vault, action  # noqa: E402
import propose  # noqa: E402
import tracker  # noqa: E402

SKILL = ROOT / ".claude" / "skills" / "cx-edit" / "SKILL.md"


def schema_cols(table):
    """Read schema.sql on its own (not through propose.py), so the docs-shape test checks against the source."""
    con = sqlite3.connect(":memory:")
    con.executescript((ROOT / "system" / "scripts" / "schema.sql").read_text(encoding="utf-8"))
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
    con.close()
    return cols


class DocsShapeTests(unittest.TestCase):
    def skill_rows(self):
        text = SKILL.read_text(encoding="utf-8")
        a, b = text.find(propose.SKILL_START), text.find(propose.SKILL_END)
        self.assertTrue(a >= 0 and b > a, "cx-edit's SKILL.md has no BL-249 fields block")
        rows = {}
        for line in text[a:b].splitlines():
            m = re.match(r"\| (\w+) \| (`.*) \|$", line)
            if m:
                rows[m.group(1)] = [f.strip("`*") for f in m.group(2).split(", ")]
        return text[a:b + len(propose.SKILL_END)], rows

    def test_skill_fields_match_schema(self):
        block, rows = self.skill_rows()
        self.assertEqual(sorted(rows), sorted(propose.FIELD_TABLES))
        for t, fields in rows.items():
            want = [c for c in schema_cols(t) if c not in ("id", "updated_at")]
            self.assertEqual(fields, want, f"cx-edit's {t} fields differ from schema.sql: run dev/tools/skill_fields.py")
        self.assertEqual(block, propose.fields_block())
        self.assertIn("`name`*, `description`", block)               # the milestone fields ask creaite guessed

    def test_every_editable_table_is_listed(self):
        self.assertEqual(set(propose.FIELD_TABLES), set(tracker.TABLES) - {"item_labels", "updates"})

    def test_generator_check(self):
        r = subprocess.run([sys.executable, str(ROOT / "dev" / "tools" / "skill_fields.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_skill_says_run_fields_and_preview(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("propose.py fields <table>", text)
        self.assertIn("Run `preview` before saying a spec is ready", text)

    def test_ask_prompt_and_read_tools(self):
        import live_server
        self.assertIn("Bash(python3 system/scripts/propose.py fields*)", live_server.READ_TOOLS)
        self.assertNotIn("Bash(python3 system/scripts/propose.py fields*)", live_server.WRITE_TOOLS)
        self.assertIn("run `propose.py preview` on it and fix any problem it reports before asking Alan",
                      live_server.ASK_PROMPT)


class MessageTests(unittest.TestCase):
    def test_hint_without_a_database(self):
        msg = tracker.unknown_fields_message("milestones", {"title", "note"}, schema_cols("milestones"))
        self.assertIn("unknown field(s) for milestones: note, title. Valid: project, name, description, baseline_date", msg)
        self.assertIn("Did you mean: note → description, title → name?", msg)
        self.assertNotIn("id,", msg.split("Valid:")[1].split(".")[0])
        msg = tracker.unknown_fields_message("actions", {"due"}, schema_cols("actions"))
        self.assertIn("due → due_date", msg)
        msg = tracker.unknown_fields_message("actions", {"zzz"}, schema_cols("actions"))
        self.assertNotIn("Did you mean", msg)


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", [action(1)])
        self.v.run("apply")

    def tearDown(self):
        self.v.cleanup()

    def spec(self, items):
        f = self.v.root / "system/staging/drafts/spec.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"items": items}))
        return str(f)

    def test_preview_names_the_valid_fields(self):
        s = self.spec([{"op": "new", "table": "milestones",
                        "values": {"project": "ABC", "title": "UAT complete", "note": "End to end",
                                   "forecast_date": "2026-11-20", "source": "Alan (cx-edit), 2026-10-12"}}])
        r = self.v.run("preview", s, script="propose.py", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("unknown field(s) for milestones: note, title. Valid: project, name, description", r.stdout)
        self.assertIn("note → description, title → name", r.stdout)
        self.assertEqual(sorted((self.v.root / "system/staging").glob("proposed-*-edit.json")), [])

    def test_update_names_the_valid_fields(self):
        s = self.spec([{"op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"notes": "chased"}}])
        r = self.v.run("preview", s, script="propose.py", ok=False)
        self.assertIn("unknown field(s) for actions: notes. Valid: project, description", r.stdout)
        self.assertIn("notes → description", r.stdout)
        s = self.spec([{"op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"id": "ABC-A-009"}}])
        self.assertIn("these fields can't be changed: id", self.v.run("preview", s, script="propose.py", ok=False).stdout)

    def test_fields_writes_nothing(self):
        def state():
            return {p.relative_to(self.v.root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
                    for p in self.v.root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        before = state()
        out = self.v.run("fields", "milestones", script="propose.py").stdout
        for f in ("name *", "description", "baseline_date", "forecast_date", "state", "percent_complete", "owner",
                  "actual_date"):
            self.assertIn(f"  {f}", out)
        self.assertIn("(Planned, Done, Cancelled)", out)
        self.assertEqual(self.v.run("fields", script="propose.py").returncode, 0)
        self.assertEqual(self.v.run("fields", "nonsense", script="propose.py", ok=False).returncode, 2)
        self.assertEqual(state(), before)


if __name__ == "__main__":
    unittest.main()
