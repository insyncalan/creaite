"""AI drafts, the shared scaffold (sprint-drafts-fields): the counts file, the feature switches, the live server's draft routes and
Settings › General › AI drafts.

Run: python3 dev/tests/test_drafts_scaffold.py
No model is ever called: these tests never reach a run (the draft kinds' own tests use a stand-in Claude).
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_tracker import Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def features():
    """drafts.FEATURES, read from the source (the switches every sprint adds to: drafts-fields, drafts-extraction, …)."""
    import ast
    tree = ast.parse((REPO / "system/scripts/drafts.py").read_text())
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "FEATURES")
    return [k.value for k in node.value.keys]


def drafts(v, *args, stdin=None):
    r = subprocess.run([sys.executable, str(v.root / "system/scripts/drafts.py"), *args], cwd=v.root, capture_output=True, text=True,
                       input=stdin)
    return r.returncode, r.stdout.strip()


class Counts(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)

    def stats(self):
        return json.loads((self.v.root / "system/staging/draft-stats.json").read_text())

    def test_each_event_is_counted_per_feature_and_the_file_holds_only_counts(self):
        for ev in ("offered", "offered", "used", "edited", "rejected"):
            self.assertEqual(drafts(self.v, "stat", "update", ev)[0], 0)
        self.assertEqual(drafts(self.v, "stat", "client", "offered", "3")[0], 0)
        s = self.stats()
        self.assertEqual(s["update"], {"offered": 2, "used": 1, "edited": 1, "rejected": 1})
        self.assertEqual(s["client"]["offered"], 3)
        for feature, row in s.items():
            if feature.startswith("_"):
                continue
            self.assertTrue(all(isinstance(n, int) for n in row.values()), row)

    def test_text_never_gets_into_the_counts(self):
        code, out = drafts(self.v, "stat", "update", "Sara said the SOW is late")
        self.assertNotEqual(code, 0)
        code, out = drafts(self.v, "stat", "Sara said the SOW is late", "used")
        self.assertNotEqual(code, 0)
        self.assertFalse((self.v.root / "system/staging/draft-stats.json").exists())

    def test_features_are_on_unless_switched_off(self):
        rows = json.loads(drafts(self.v, "features", "--json")[1])
        self.assertEqual([r["id"] for r in rows][:4], ["update", "client", "thinking", "reason"])
        self.assertTrue(all(r["on"] for r in rows))
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["drafting"] = {"client": False}
        cfg.write_text(json.dumps(data))
        rows = {r["id"]: r["on"] for r in json.loads(drafts(self.v, "features", "--json")[1])}
        self.assertEqual(rows["client"], False)
        self.assertEqual(rows["update"], True)

    def test_an_unknown_kind_is_refused_without_a_model(self):
        out = json.loads(drafts(self.v, "context", stdin=json.dumps({"kind": "poem"}))[1])
        self.assertIn("refused", out)

    def test_the_defaults_name_every_feature(self):
        defaults = json.loads((REPO / "system/templates/settings-defaults.json").read_text())
        self.assertEqual({k for k, v in defaults["drafting"].items() if not k.startswith("_") and isinstance(v, bool)},
                         set(features()))   # each sprint adds its own switches (drafts-writing's agenda_style is a choice, not one)

    def test_a_drafted_proposal_is_never_approved_in_bulk_and_its_decision_is_counted(self):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        try:
            import importlib
            import review
            importlib.reload(review)
            item = {"op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"latest_update": "Booked."},
                    "drafted": "update", "drafted_text": "Booked."}
            self.assertEqual(review.individual_only(item), "drafted update")
            self.assertIsNone(review.individual_only({k: v for k, v in item.items() if not k.startswith("drafted")}))
        finally:
            sys.path.remove(str(self.v.root / "system/scripts"))


class Routes(LiveBrowserCase):
    shared_server = True

    def api(self, path, body):
        return self.b.eval(f"api({json.dumps(path)},{json.dumps(body)})")

    def test_the_routes_refuse_an_unknown_kind_count_events_and_list_the_features(self):
        r = self.api("/api/draft", {"kind": "poem"})
        self.assertFalse(r["ok"])
        r = self.api("/api/draft/stat", {"feature": "update", "event": "used"})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["counts"]["used"], 1)
        self.assertFalse(self.api("/api/draft/stat", {"feature": "update", "event": "liked"})["ok"])
        st = self.api("/api/drafts", {})
        self.assertTrue(st["ok"])
        self.assertEqual([f["id"] for f in st["features"]][:4], ["update", "client", "thinking", "reason"])
        self.assertEqual(st["stats"]["update"]["used"], 1)

    def test_settings_lists_the_switches_and_a_switch_saves_with_its_log_line(self):
        b = self.b
        b.eval("go('settings','drafts')")
        b.wait("document.querySelector('#settingsBody [data-sec=drafts] [data-drsw=update]')")
        labels = b.eval("[...document.querySelectorAll('#settingsBody [data-sec=drafts] .srow')].map(r=>r.firstElementChild.textContent)")
        self.assertTrue(any(l.startswith("Draft the latest update") for l in labels), labels)
        self.assertEqual(len(labels), len(features()))
        b.click("#settingsBody [data-drsw=thinking]")
        log = self.v.root / "system/config/settings-log.jsonl"
        b.wait("!document.querySelector('#settingsBody [data-drsw=thinking]').checked && S.drafting.thinking===false")
        for _ in range(100):
            if log.exists() and '"drafting.thinking"' in log.read_text():
                break
            b.pump(0.05)
        self.assertIs(json.loads((self.v.root / "system/config/settings.json").read_text())["drafting"]["thinking"], False)
        self.assertIn("off in Settings", b.eval("draftWhyNot('thinking-x')||draftWhyNot('thinking')"))
        b.click("#settingsBody [data-drsw=thinking]")
        b.wait("S.drafting.thinking===true")
        self.assertEqual(b.errors, [])

    def test_the_draft_button_says_why_it_is_greyed(self):
        b = self.b
        html = b.eval("draftBtn('update','Draft','Draft the latest update')")
        self.assertIn('data-draft="update"', html)
        self.assertIn("Draft", html)
        b.eval("DRAFTKIND.update='update'; S.drafting={...(S.drafting||{}),update:false}")
        self.assertIn('aria-disabled="true"', b.eval("draftBtn('update','Draft','Draft the latest update')"))
        b.eval("S.drafting.update=true")

    def test_the_search_finds_the_section(self):
        b = self.b
        b.eval("go('settings')")
        b.wait("document.getElementById('setq')")
        b.eval("const q=document.getElementById('setq'); q.value='client wording'; q.dispatchEvent(new Event('input'))")
        b.wait("document.querySelector('#settingsBody [data-sec=drafts]')")


if __name__ == "__main__":
    unittest.main()
