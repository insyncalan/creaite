"""BL-231 phase 2: controls bound before their function is wrapped run the full function, as the keyboard does.

Run: python3 dev/tests/test_early_bound_controls.py   (needs Google Chrome; skipped otherwise)
The real live server in a throwaway vault; Claude is a stand-in (drafts_fake.py), so no model is called.
Before this, the panel's Close button and the search button were bound at load to the first `closePanel` and `openCk`, so a click
skipped every later step (dev/archive/notes/v1.8.0/V18-HANDLERS-NOTE.md): Close kept an unused health-reason draft (BL-226) and left focus in the closed
panel (BL-176); a click on Search kept an earlier "which one?" pick (BL-205), while Enter, ⌘K and Cancel all ran the full function.
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from test_drafts_update import DraftCase  # noqa: E402


class EarlyBoundControls(DraftCase):
    def wait_stat(self, kind, event, n, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            if self.stats().get(kind, {}).get(event, 0) >= n:
                return True
            time.sleep(0.1)
        return False

    def test_close_drops_an_unused_reason_draft_and_leaves_no_focus_in_the_panel(self):
        b = self.b
        b.eval("go('cockpit','ABC'); openProject('ABC','health')")
        b.wait("document.querySelector('#hDraft [data-drhealth]')")
        b.eval("document.getElementById('f_health').value='At risk'; document.getElementById('f_health').dispatchEvent(new Event('change'))")
        b.click("#hDraft [data-drhealth]")
        b.wait("document.querySelector('#hDraft .drcard')", 30)
        rejected = self.stats().get("reason", {}).get("rejected", 0)
        b.eval("document.getElementById('pClose').focus()")
        b.click("#pClose")
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.assertIsNone(b.eval("DRH"))                                              # BL-226: the draft is forgotten …
        self.assertTrue(self.wait_stat("reason", "rejected", rejected + 1))          # … and counted as rejected
        self.assertFalse(b.eval("document.getElementById('panel').contains(document.activeElement)"))   # BL-176
        b.eval("openProject('ABC','health')")
        b.wait("document.querySelector('#hDraft [data-drhealth]')")
        self.assertIsNone(b.eval("document.querySelector('#hDraft .drcard')"))      # it doesn't come back
        self.assertEqual(b.errors, [])

    def test_a_click_on_search_starts_without_an_earlier_pick(self):
        b = self.b
        b.eval(f"CKPICK={json.dumps({'the vendor': 'Sara Example'})}")
        b.click("#searchBtn")
        b.wait("document.getElementById('cmdk').open")
        self.assertEqual(b.eval("JSON.stringify(CKPICK)"), "{}")                     # BL-205, as Enter and ⌘K already did
        b.eval("document.getElementById('cmdk').close()")
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
