"""BL-307: ask creaite offered "Go ahead: Prep page", then refused it ("the panel doesn't write prep pages"). A prep page asked for
in the chat now goes to the Prep page route (BL-98): the model names the meeting with a `PREP: <key> | <title>` line, the server
checks it is one of today's or tomorrow's meetings with a project and sends a `prep` event, and the page's Prep page card runs the
same read-only research and the server's own write as the Prep brief's button. The model never writes the page.

- A CONFIRM for a prep page is never offered as Go ahead; the chat says where the Prep page is instead. Other CONFIRMs are unchanged.
- A PREP line becomes one `prep` event with the meeting's own title; the line itself is never shown. A meeting that isn't in the
  calendar gives the reason, and no card.
- The prompts and cx-prep say so; neither tells the panel it can't make the page, and neither lets it build the page itself.
- In the browser: Go ahead on the card makes the page through /api/prep/page and /api/prep/build, in the Agendas folder.

Run: python3 dev/tests/test_ask_prep_offer.py   (the browser test needs Google Chrome; skipped otherwise)
"""
import json
import re
import sys
import unittest
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

REPO = Path(__file__).resolve().parents[2]

FAKE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
message = args[args.index("--") + 1]
allowed = args[args.index("--allowedTools") + 1] if "--allowedTools" in args else ""
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-prep"})
if message.startswith("creaite prep page"):            # the Prep page route's own research run: read only
    assert "Write(" not in allowed and "prep_page.py build" not in allowed
    text = json.dumps({"about": "The weekly ABC check-in.", "item_reasons": {}, "notes": [], "questions": [],
                       "m365": "searched"})
else:
    first = message.split("\n")[0]
    assert "prep_page.py build" not in allowed          # the panel never builds the page
    if first == "confirm prep":
        text = "I can make it.\nCONFIRM: Prep page | Research ABC weekly and save the page in its Agendas folder"
    elif first == "prep":
        text = "The ABC weekly is at 09:00.\nPREP: 09:00|ABC weekly | ABC weekly"
    elif first == "prep gone":
        text = "PREP: 09:00|Not a meeting | Not a meeting"
    elif first == "apply":
        text = "Three changes are approved.\nCONFIRM: Apply | Write the approved changes to the tracker"
    else:
        text = "Nothing to do."
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "result": text, "session_id": "sess-prep"})
'''


def load(v):
    from test_dashboard import populate
    populate(v)
    day = date.today().isoformat()
    (v.root / "system/staging/calendar.json").write_text(json.dumps({"fetched": f"{day} 07:00", "days": {day: [
        {"id": "t1", "start": "09:00", "end": "10:00", "title": "ABC weekly", "where": "Teams", "teams": True,
         "organiser": "Jane Doe", "all_day": False, "private": False, "sensitivity": "normal",
         "body": "Agenda: test licences; UAT readiness", "attendees": []}]}}))
    fake = v.root / "fake_claude.py"
    fake.write_text(FAKE)
    fake.chmod(0o755)


class PrepOfferServer(LiveBrowserCase):
    """The server's side, over HTTP (a browser is opened by the base class but not needed)."""
    shared_server = True
    width, height = 1000, 700

    @classmethod
    def load(cls, v):
        load(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def token(self):
        html = urllib.request.urlopen(self.base + "/").read().decode()
        return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    def ask(self, message):
        req = urllib.request.Request(self.base + "/api/ask", data=json.dumps({"message": message}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token()})
        with urllib.request.urlopen(req, timeout=90) as r:
            return [json.loads(x.decode()[6:]) for x in r if x.decode().startswith("data: ")]

    @staticmethod
    def texts(evs):
        return " ".join(e.get("text", "") for e in evs if e["type"] == "text")

    def test_a_prep_page_confirm_is_never_offered_as_go_ahead(self):
        evs = self.ask("confirm prep")
        self.assertEqual([e for e in evs if e["type"] == "confirm"], [])            # the defect: "Go ahead: Prep page"
        self.assertNotIn("CONFIRM:", self.texts(evs))
        self.assertIn("press Prep page", self.texts(evs))

    def test_other_confirms_are_unchanged(self):
        evs = self.ask("apply")
        conf = [e for e in evs if e["type"] == "confirm"]
        self.assertEqual([(c["title"], c["body"]) for c in conf], [("Apply", "Write the approved changes to the tracker")])

    def test_a_prep_line_is_offered_as_the_prep_page_route(self):
        evs = self.ask("prep")
        prep = [e for e in evs if e["type"] == "prep"]
        self.assertEqual(len(prep), 1, evs)
        self.assertEqual(prep[0]["key"], "09:00|ABC weekly")
        self.assertEqual(prep[0]["title"], "ABC weekly")
        self.assertEqual(prep[0]["project"], "Example Programme")
        self.assertEqual([e for e in evs if e["type"] == "confirm"], [])
        self.assertNotIn("PREP:", self.texts(evs))                                    # the line itself is never shown
        self.assertFalse(list(self.v.root.rglob("*Prep - ABC weekly*.html")))          # nothing written by the chat

    def test_a_meeting_not_in_the_calendar_gives_the_reason_and_no_card(self):
        evs = self.ask("prep gone")
        self.assertEqual([e for e in evs if e["type"] == "prep"], [])
        self.assertIn("isn't in the saved calendar for", self.texts(evs))   # BL-293: any day the calendar holds

    def test_the_prompt_and_cx_prep_send_a_prep_page_to_the_route(self):
        src = (REPO / "system/scripts/live_server.py").read_text()
        self.assertIn("PREP: <key> | <meeting title>", src)
        self.assertIn("never a CONFIRM", src)
        skill = (REPO / ".claude/skills/cx-prep/SKILL.md").read_text()
        panel = skill.split("## In ask creaite")[1].split("## In Claude Code")[0]
        self.assertNotIn("can't write", panel)
        self.assertIn("PREP: <key> | <meeting title>", panel)
        self.assertIn("never write the reply file or run `prep_page.py build` from the panel", panel)


class PrepOfferBrowser(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        load(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def test_go_ahead_on_the_card_makes_the_page_through_the_route(self):
        b = self.b
        b.eval("openChat(); $('#chIn').value='prep'; send()", wait=False)
        b.wait("[...document.querySelectorAll('#chLog .confirm')].some(c=>c.textContent.includes('Prep page')&&c.querySelector('.primary'))", 20)
        card = b.eval("[...document.querySelectorAll('#chLog .confirm')].pop().textContent")
        self.assertIn("ABC weekly", card)
        self.assertIn("Go ahead", card)
        b.eval("[...document.querySelectorAll('#chLog .confirm')].pop().querySelector('.primary').click()")
        import time
        page = self.v.root / f"projects/ABC Example Programme/agendas/{date.today().isoformat()} Prep - ABC weekly.html"
        for _ in range(400):
            if page.exists():
                break
            time.sleep(0.1)
        self.assertTrue(page.exists(), b.eval("document.body.innerText.slice(-400)"))
        self.assertIn("The weekly ABC check-in.", page.read_text())


if __name__ == "__main__":
    unittest.main()
