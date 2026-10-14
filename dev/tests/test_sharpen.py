"""BL-220 (sprint-drafts-extraction): sharpen on capture. Chips come from plain code with no model call and set one field only when
clicked; Sharpen is offered only for a vague title (under four words or no verb) and is a suggestion beside the original; staging marks
a vague new action as shaky for Review.

Run: python3 dev/tests/test_sharpen.py
The real live server in a throwaway vault; Claude is a stand-in (drafts_fake.py), so no model is called.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
from test_drafts_update import DraftCase  # noqa: E402
from test_tracker import Vault  # noqa: E402

import extraction  # noqa: E402

EMAIL = ("Email · From: Jane Doe <jane.doe@client.com> · Subject: [ABC] data · Sent: 2026-10-07 09:12 · "
         "Link: https://outlook.office365.com/owa/?ItemID=sh1")


class VagueTest(unittest.TestCase):
    def test_the_vague_test_is_plain_code(self):
        self.assertEqual(extraction.vague("look into data"), "under four words")
        self.assertEqual(extraction.vague("the data thing for the cut-over"), "no verb")
        self.assertIsNone(extraction.vague("Confirm who owns the cut-over data extract"))
        self.assertIsNone(extraction.vague("Sara sends the revised SOW to Jane"))


class Staging(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.v.run("init")

    def drafts(self, body):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/drafts.py"), "context"], cwd=self.v.root,
                           input=json.dumps(body), capture_output=True, text=True)
        return json.loads(r.stdout)

    def test_staging_marks_a_vague_action_shaky_and_leaves_a_clear_one(self):
        spec = self.v.root / "system/staging/drafts/sweep.json"
        spec.write_text(json.dumps({"items": [
            {"table": "actions", "values": {"project": "ABC", "description": "look into data", "source": EMAIL}},
            {"table": "actions", "values": {"project": "ABC", "description": "Confirm who owns the data extract", "source": EMAIL}}]}))
        subprocess.run([sys.executable, str(self.v.root / "system/scripts/sweep.py"), "stage", str(spec)], cwd=self.v.root,
                       env={**os.environ, "CREAITE_NOW": "2026-10-08 09:00"}, capture_output=True, text=True, check=True)
        items = json.loads(next((self.v.root / "system/staging").glob("proposed-*-sweep.json")).read_text())["items"]
        self.assertEqual(items[0]["inferred"][0]["field"], "description")
        self.assertIn("under four words", items[0]["inferred"][0]["why"])
        self.assertNotIn("inferred", items[1])

    def test_sharpen_is_offered_only_for_a_vague_title_and_asks_no_model_otherwise(self):
        clear = self.drafts({"kind": "sharpen", "title": "Confirm who owns the cut-over data extract", "code": "ABC"})
        self.assertIn("already clear", clear["refused"])
        vague = self.drafts({"kind": "sharpen", "title": "look into data", "code": "ABC"})
        self.assertTrue(vague["prompt"].startswith("Sharpen one vague action"))
        self.assertIn("The action as written: “look into data”", vague["prompt"])
        self.assertIn("The project: Example Programme", vague["prompt"])


class Page(DraftCase):
    def test_chips_come_from_plain_code_and_set_one_field_only_when_clicked(self):
        b = self.b
        b.eval("openNew('actions')")
        b.wait("CUR&&CUR.mode==='new'")
        b.eval("const t=document.getElementById('pkTitle'); t.focus(); t.textContent='Sara Example to send the data extract by friday, urgent'; "
               "t.dispatchEvent(new Event('input'))")
        b.wait("document.querySelectorAll('#pkChips .capchip').length>=3")
        labels = b.eval("[...document.querySelectorAll('#pkChips .capchip')].map(x=>x.textContent)")
        self.assertIn("+ Owner: Sara Example", labels)
        self.assertTrue(any(x.startswith("+ Due: ") for x in labels), labels)
        self.assertIn("+ Priority: Urgent", labels)
        self.assertNotEqual(b.eval("CUR.draft.o"), "Sara Example")                     # nothing is set without a click
        self.assertFalse(b.eval("(e=>!!e&&!e.hidden)(document.querySelector('#pkChips [data-draft=sharpen]'))"))   # a clear title: no Sharpen
        before = b.eval("JSON.stringify({...CUR.draft,o:undefined,t:undefined})")
        b.eval("[...document.querySelectorAll('#pkChips .capchip')].find(x=>x.textContent.includes('Owner')).click()")
        b.wait("CUR.draft.o==='Sara Example'")
        self.assertEqual(b.eval("JSON.stringify({...CUR.draft,o:undefined,t:undefined})"), before)   # one field changed
        self.assertEqual(b.errors, [])

    def test_a_vague_title_offers_sharpen_and_use_fills_the_title_beside_the_original(self):
        b = self.b
        b.eval("openNew('actions')")
        b.wait("CUR&&CUR.mode==='new'")
        b.eval("const t=document.getElementById('pkTitle'); t.focus(); t.textContent='look into data'; t.dispatchEvent(new Event('input')); t.blur()")
        b.wait("document.querySelector('#pkChips [data-draft=sharpen]')")
        b.click("#pkChips [data-draft=sharpen]")
        b.wait("document.querySelector('#pkAiDraft .drcard')", 30)
        card = b.eval("document.querySelector('#pkAiDraft .drcard').innerText")
        self.assertIn("Confirm who owns the cut-over data extract", card)
        self.assertIn("As written: look into data", card)
        b.click("#pkAiDraft [data-drdo=use]")
        b.wait("document.getElementById('pkTitle').textContent.startsWith('Confirm who owns')")
        self.assertEqual(self.stats().get("sharpen", {}).get("offered"), 1)
        self.assertEqual(b.errors, [])

    def test_cmdk_add_an_action_shows_chips(self):
        b = self.b
        b.eval("openCk(); const i=document.getElementById('cmdkIn'); i.value='add an action for ABC: I will send the plan by friday'; "
               "i.dispatchEvent(new Event('input'))")
        b.wait("document.querySelector('#cmdk [data-ckchip]')")
        labels = b.eval("[...document.querySelectorAll('#cmdk [data-ckchip]')].map(x=>x.textContent)")
        self.assertTrue(any("Owner: " in x for x in labels), labels)
        b.eval("[...document.querySelectorAll('#cmdk [data-ckchip]')].find(x=>x.textContent.includes('Owner')).click()")
        b.wait("CK[CKI].change.new.o&&CK[CKI].change.new.o!=='TBC'")
        b.eval("document.getElementById('cmdk').close()")
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
