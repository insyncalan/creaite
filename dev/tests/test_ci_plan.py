"""Dev speed: dev/tools/ci_plan.py sizes the CI matrix to the plan's concurrent-job limit.

Run: python3 dev/tests/test_ci_plan.py   (quick tier)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import ci_plan  # noqa: E402


class Plan(unittest.TestCase):
    def test_the_free_plan_is_filled_exactly(self):
        self.assertEqual(ci_plan.shards_314(False), 17)                   # 17 + 3 (Python 3.9) = 20
        self.assertEqual(ci_plan.shards_314(True), 14)                    # 14 + 3 + 3 (macOS) = 20
        for mac in (False, True):
            m = ci_plan.matrix(mac)["include"]
            self.assertEqual(len(m) + (ci_plan.MAC_SHARDS if mac else 0), ci_plan.LIMIT)

    def test_other_plans(self):
        self.assertEqual(ci_plan.shards_314(False, 40), 37)               # Pro
        self.assertEqual(ci_plan.shards_314(True, 60), 54)                # Team

    def test_never_fewer_than_one_shard(self):
        self.assertEqual(ci_plan.shards_314(True, 5), 1)

    def test_each_shard_is_numbered_once_and_knows_its_count(self):
        inc = ci_plan.matrix(False)["include"]
        for py, count, scope in (("3.14", 17, ""), ("3.9", 3, "--quick")):
            mine = [x for x in inc if x["python"] == py]
            self.assertEqual(sorted(x["shard"] for x in mine), list(range(1, count + 1)))
            self.assertTrue(all(x["shards"] == count and x["scope"] == scope for x in mine))

    def test_the_command_prints_json_and_writes_the_output_file(self):
        out = Path(tempfile.mkdtemp()) / "out"
        r = subprocess.run([sys.executable, str(TOOLS / "ci_plan.py"), "--macos"], capture_output=True, text=True,
                           env={**os.environ, "GITHUB_OUTPUT": str(out)})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), ci_plan.matrix(True))
        self.assertEqual(out.read_text().strip(), "matrix=" + r.stdout.strip())

    def test_a_shard_split_exists_for_every_count_the_plan_can_make(self):
        sys.path.insert(0, str(TOOLS))
        import run_tests
        files = sorted(Path(run_tests.TESTS).glob("test_*.py"))
        for n in (ci_plan.shards_314(False), ci_plan.shards_314(True)):
            seen = []
            for i in range(1, n + 1):
                seen += [f.name for f in run_tests.apply_shard(files, (i, n))]
            self.assertEqual(sorted(seen), sorted(f.name for f in files), n)


if __name__ == "__main__":
    unittest.main()
