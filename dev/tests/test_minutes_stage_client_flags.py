"""#283 review M2: a meeting's spec never makes an item client-visible.

`client_visible` is off by default and only Alan sets it (cx-edit, the item panel, Excel); `client_message` is his wording
(tracker-conventions.md). A spec is written by Claude from a transcript, whose text could ask for either, so `minutes.py stage`
drops both from every new item it stages: once approved (and bulk approval can cover new actions) the item would otherwise reach
a client report.

Run: python3 dev/tests/test_minutes_stage_client_flags.py
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import Vault  # noqa: E402


class StageDropsClientFlags(unittest.TestCase):

    def setUp(self):
        from test_dashboard import populate
        self.v = Vault()
        populate(self.v)

    def tearDown(self):
        self.v.cleanup()

    def test_a_spec_never_sets_client_visible_or_its_wording(self):
        import test_minutes_editor as me
        spec = me.meeting_spec()
        for it in spec["items"]:
            it["values"].update(client_visible=1, client_message="What it is: x\nWhat it means for you: y\nWhat is being done: z")
        (self.v.root / "inbox" / f"{me.DAY} Steering committee.vtt").write_text(me.VTT, encoding="utf-8")
        f = self.v.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps(spec), encoding="utf-8")
        before = {p.name for p in (self.v.root / "system/staging").glob("proposed-*.json")}
        self.v.run("stage", str(f), script="minutes.py")
        new = [p for p in (self.v.root / "system/staging").glob("proposed-*.json") if p.name not in before]
        self.assertEqual(len(new), 1)
        items = [i for i in json.loads(new[0].read_text(encoding="utf-8"))["items"] if i.get("op") == "new"]
        self.assertTrue(items, "the meeting's new items were staged")
        for it in items:
            with self.subTest(it["values"].get("description") or it["values"].get("decision")):
                self.assertNotIn("client_visible", it["values"])
                self.assertNotIn("client_message", it["values"])


if __name__ == "__main__":
    unittest.main()
