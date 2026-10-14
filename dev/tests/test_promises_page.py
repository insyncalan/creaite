"""BL-125 A, the screens: Today's You owe and Waiting on, and the Promises card on a person's page.

Run: python3 dev/tests/test_promises_page.py   (the page tests need Google Chrome; skipped otherwise)
A throwaway vault with the demo data from test_dashboard.populate plus fictional promises, built with build_dashboard.py and
loaded headless with test_insight.chrome (the probe sets window.OUT). Alan is the committed settings' identity (Alan Carter).
"""
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import CHROME, TODAY, populate  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402


def d(n):
    return (TODAY + timedelta(days=n)).isoformat()


def promise(n, by, to, text, due=None, **extra):
    v = {"project": "ABC", "promised_by": by, "promised_to": to, "description": text, "raised": d(-10),
         "source": f"{ABC}/transcripts/2026-09-29 Steering.vtt — Sara Example 00:12", **extra}
    if due:
        v["due_date"] = due
    return {"n": n, "op": "new", "table": "promises", "match": "strong", "flags": [], "decision": "approved", "values": v}


PROMISES = [
    promise(1, "Alan Carter", "Sara Example", "Send the SOW to the client", d(2)),         # you owe, due in 2 days
    promise(2, "Alan Carter", "Jane Doe", "Share the UAT plan", d(-2)),                    # you owe, 2 days late
    promise(3, "Alan Carter", "Sara Example", "Book the <b>workshop</b>"),                 # you owe, no date (and markup in text)
    promise(4, "Sara Example", "Alan Carter", "Send the data extract", d(-3)),             # waiting on, 3 days late
    promise(5, "Jane Doe", "Alan Carter", "Confirm the budget", d(-6)),                    # waiting on, 6 days late
    promise(6, "Sara Example", "Alan Carter", "Confirm the room", d(4)),                   # to Alan, not yet due: not Waiting on
    promise(7, "Sara Example", "Jane Doe", "Book the room", d(-5)),                       # between two others: nowhere
    promise(8, "Zed Nobody", "Alan Carter", "Send the vendor list", d(-1)),                # someone who owns no items
    promise(9, "Jane Doe", "Alan Carter", "Approve the plan", d(-1), status="Done"),       # kept: nowhere
]


@unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
class PromisesPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_insight import chrome
        cls.chrome = staticmethod(chrome)
        cls.v = Vault()
        populate(cls.v)
        cls.v.propose("promises", PROMISES)
        cls.v.run("apply")
        cls.v.run(script="build_dashboard.py")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def probe(self, script):
        out, errors = self.chrome(self.v, script)
        self.assertEqual(errors, [])
        self.assertIsNotNone(out, "the page didn't finish")
        self.assertNotIn("error", out, out.get("error"))
        return out

    def test_today_lists_what_you_owe_and_what_you_are_waiting_on(self):
        o = self.probe("""
          go("today"); const sec=id=>document.getElementById(id), lines=id=>[...document.querySelectorAll(`#${id} > li`)].map(li=>li.querySelector(".pt").textContent+" | "+li.querySelector("p").textContent);
          window.OUT={oweHidden:sec("tOwe").hidden, waitHidden:sec("tWait").hidden, owe:lines("oweList"), wait:lines("waitList"),
            nOwe:sec("nOwe").textContent, nWait:sec("nWait").textContent, late:[...document.querySelectorAll("#oweList .late, #waitList .late")].length,
            bold:[...document.querySelectorAll("#oweList b")].length, people:[...document.querySelectorAll("#waitList [data-person]")].map(a=>a.dataset.person),
            vip:document.querySelectorAll("#tOwe .tag.vip, #tWait .tag.vip").length, chase:sec("hWait").querySelector("a[data-nav]").dataset.nav};""")
        self.assertEqual((o["oweHidden"], o["waitHidden"]), (False, False))
        self.assertEqual(len(o["owe"]), 3)
        self.assertTrue(o["owe"][0].startswith("Share the UAT plan | To Jane Doe on Example Programme: 2 days late"), o["owe"])
        self.assertIn("Send the SOW to the client | To Sara Example on Example Programme: due in 2 days", o["owe"][1])
        self.assertIn("Book the <b>workshop</b> | To Sara Example on Example Programme: no date given", o["owe"][2])   # text, not markup
        self.assertEqual(o["bold"], 0)
        self.assertEqual(o["nOwe"], "3 · 1 overdue")
        self.assertEqual(len(o["wait"]), 3)                                   # the overdue ones made to Alan, most overdue first
        self.assertIn("Confirm the budget | From Jane Doe on Example Programme: 6 days late, quiet for 10 days", o["wait"][0])
        self.assertIn("Send the data extract | From Sara Example", o["wait"][1])
        self.assertIn("Send the vendor list | From Zed Nobody", o["wait"][2])
        self.assertEqual(o["nWait"], "3")
        self.assertEqual(o["late"], 4)                                         # one in You owe, three in Waiting on
        self.assertEqual(o["people"], ["Jane Doe", "Sara Example", "Zed Nobody"])
        self.assertFalse(any("Book the room" in x or "Confirm the room" in x or "Approve the plan" in x for x in o["owe"] + o["wait"]))
        self.assertEqual(o["vip"], 0)                                          # BL-288: people are never labelled
        self.assertEqual(o["chase"], "all:chase:")

    def test_the_sections_hide_when_there_is_nothing_and_chase_view_opens_work(self):
        o = self.probe("""
          go("today"); const keep=D.promises; D.promises=[]; renderPromises();
          const hidden=[document.getElementById("tOwe").hidden, document.getElementById("tWait").hidden];
          D.promises=keep; renderPromises(); const back=document.getElementById("tWait").hidden;
          document.querySelector("#hWait a[data-nav]").click(); await new Promise(r=>setTimeout(r,100));
          window.OUT={hidden, back, view:VIEW, wt:WT};""")
        self.assertEqual(o["hidden"], [True, True])
        self.assertFalse(o["back"])
        self.assertEqual((o["view"], o["wt"]), ("work", "all"))

    def test_a_persons_page_lists_the_promises_both_ways(self):
        o = self.probe("""
          const card=n=>{ go("person",n); const c=document.getElementById("ppPromises");
            return c?{heads:[...c.querySelectorAll("h3")].map(h=>h.textContent.replace(/\\s+/g," ").trim()),
                      rows:[...c.querySelectorAll(".li")].map(r=>r.textContent.replace(/\\s+/g," ").trim()),
                      afterWork:!!c.previousElementSibling?.querySelector("h2")?.textContent.startsWith("Open work")}:null; };
          window.OUT={sara:card("Sara Example"), zed:card("Zed Nobody"), omar:card("Omar Ali")};""")
        sara = o["sara"]
        self.assertEqual(sara["heads"], ["Sara promised you · 2", "You promised Sara · 2"])   # overdue first, then the room (not yet due)
        self.assertTrue(sara["rows"][0].startswith("Send the data extract"))
        self.assertIn("3 days late, quiet for 10 days", sara["rows"][0])
        self.assertTrue(sara["rows"][1].startswith("Confirm the room"))
        self.assertNotIn("quiet", sara["rows"][1])                          # quiet is only said of an overdue promise
        self.assertTrue(sara["rows"][2].startswith("Send the SOW to the client"))
        self.assertIn("no date given", sara["rows"][3])
        self.assertTrue(sara["afterWork"])
        self.assertEqual(o["zed"]["heads"], ["Zed promised you · 1"])          # owns no items, still has the card
        self.assertIsNone(o["omar"])                                            # no promises with Alan: no card


if __name__ == "__main__":
    unittest.main()
