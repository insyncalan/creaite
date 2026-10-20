"""#97 step 1: the alert check's quiet hours in Settings › Essentials › People I follow (the page side).

Two rows under Check every: Pause alert checks overnight (a switch, From and To, 24-hour HH:MM) and Pause alert checks on weekend
days (a switch). Both on by default, 19:00 to 07:00; each change saved like every setting (settings.json, a backup, a log line); a
time that isn't HH:MM is refused and the box goes back. Nothing on the card says VIP (BL-288).

Run: python3 dev/tests/test_quiet_hours_page.py   (needs Google Chrome; skipped otherwise)
The real live server in a throwaway vault with fictional data, and the real dashboard in headless Chrome.
"""
import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ROW = "[...document.querySelectorAll('#set-essentials .srow')].find(r=>r.querySelector('span[id]').textContent==={!r})"
NIGHT, WEEKEND = ROW.format("Pause alert checks overnight"), ROW.format("Pause alert checks on weekend days")


class QuietHoursPage(LiveBrowserCase):
    def setUp(self):
        super().setUp()
        self.b.eval("window.__errs=[]; addEventListener('error',e=>__errs.push(e.message)); addEventListener('unhandledrejection',e=>__errs.push(String(e.reason)))")
        self.b.eval("STAB='essentials'; go('settings')")
        self.b.wait(f"VIEW==='settings' && !!{NIGHT} && !!{WEEKEND}")

    def vip(self):
        return json.loads((self.v.root / "system" / "config" / "settings.json").read_text()).get("vip") or {}

    def until(self, check, timeout=10):
        end = time.time() + timeout
        while time.time() < end and not check():
            self.b.pump(0.1)
        self.assertTrue(check())

    def change(self, sel, value):
        self.b.eval(f"(()=>{{ const e={sel}; e.value={value!r}; e.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")

    def test_the_rows_sit_in_people_i_follow_after_check_every_with_their_defaults(self):
        labels = self.b.eval("[...document.querySelector('[data-ess=\"People I follow\"]').querySelectorAll('.srow span[id]')].map(s=>s.textContent)")
        night = labels.index("Pause alert checks overnight")
        self.assertEqual(labels[night + 1], "Pause alert checks on weekend days")
        self.assertLess(labels.index("Check every"), night)
        self.assertTrue(self.b.eval(f"{NIGHT}.querySelector('input.switch').checked"))
        self.assertTrue(self.b.eval(f"{WEEKEND}.querySelector('input.switch').checked"))
        self.assertEqual(self.b.eval(f"[...{NIGHT}.querySelectorAll('input[type=text]')].map(e=>e.value)"), ["19:00", "07:00"])
        self.assertIn("looks back to the last one, so nothing is missed", self.b.eval(f"{NIGHT}.textContent"))
        self.assertIn("Uses the weekend days set in Essentials › You.", self.b.eval(f"{WEEKEND}.textContent"))
        card = self.b.eval("document.querySelector('[data-ess=\"People I follow\"]').textContent")
        self.assertNotRegex(card, r"\bVIP\b")

    def test_the_times_and_switches_save_to_their_keys(self):
        self.change(f"{NIGHT}.querySelector('input[aria-label$=from]')", "20:30")
        self.until(lambda: self.vip().get("quiet_from") == "20:30")
        self.change(f"{NIGHT}.querySelector('input[aria-label$=to]')", "06:45")
        self.until(lambda: self.vip().get("quiet_to") == "06:45")
        self.b.eval(f"(()=>{{ const e={WEEKEND}.querySelector('input.switch'); e.checked=false; e.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        self.until(lambda: self.vip().get("quiet_weekend") is False)
        self.b.eval(f"(()=>{{ const e={NIGHT}.querySelector('input.switch'); e.checked=false; e.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        self.until(lambda: self.vip().get("quiet_overnight") is False)
        log = (self.v.root / "system" / "config" / "settings-log.jsonl").read_text()
        for k in ("vip.quiet_from", "vip.quiet_to", "vip.quiet_weekend", "vip.quiet_overnight"):
            self.assertIn(f'"{k}"', log)

    def test_a_time_that_isnt_hh_mm_is_refused_and_the_box_goes_back(self):
        box = f"{NIGHT}.querySelector('input[aria-label$=from]')"
        self.change(box, "8pm")
        self.b.wait(f"{box}.value==='19:00'")
        self.b.pump(0.5)
        self.assertNotIn("quiet_from", self.vip())

    def test_no_script_errors(self):
        self.assertEqual(self.b.eval("window.__errs||[]"), [])


if __name__ == "__main__":
    unittest.main()
