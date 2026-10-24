"""BL-314 (v1.9.1, routing): a change to fields of existing items asked for in ask creaite runs through the dashboard's own action.
The real live server with a stand-in `claude` that ends its reply with `EDIT: <item ID> | <field> | <new value>` lines.

- The server checks each line against the tracker (an unknown ID, a field the item doesn't have, a value outside its choices, a
  made decision going back to pending) and sends one "fieldcard": propose.py preview's own before → after lines and, per item,
  the patch in the dashboard's field names. Nothing is staged or written by the run; the EDIT line is never shown.
- The model gains no command: no new route, and the guard's lists are untouched (test_guard_pinned covers them).
- The CHANGE card (BL-258) is unchanged for a cx-edit spec.
- In the browser: Go ahead saves the change as the Work bulk bar does (one proposal, source_run "dashboard", applied at once
  with auto-apply), the page's data updates, Undo puts it back; Cancel writes nothing.

Run: python3 dev/tests/test_ask_field_card.py   (the browser test needs Google Chrome; skipped otherwise)
"""
import json
import re
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
message = args[args.index("--") + 1].split("\n")[0]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-field"})
if message.startswith("edit "):                 # edit <ID> | <field> | <value> ; <ID> | <field> | <value> ...
    lines = ["EDIT: " + part.strip() for part in message[5:].split(";")]
    text = "I'll make that change.\n" + "\n".join(lines)
elif message.startswith("spec "):              # the BL-258 card, unchanged
    words = message.split()
    spec = {"items": [{"op": "update", "table": "actions", "id": words[1], "changes": {words[2]: " ".join(words[3:])}}]}
    os.makedirs("system/staging/drafts", exist_ok=True)
    with open("system/staging/drafts/spec.json", "w") as f:
        json.dump(spec, f)
    text = "Here is the change.\nCHANGE: system/staging/drafts/spec.json | Change " + words[1]
else:
    text = "Nothing to change."
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "result": text, "session_id": "sess-field"})
'''


def load_fake(v):
    from test_dashboard import populate
    populate(v)
    fake = v.root / "fake_claude.py"
    fake.write_text(FAKE)
    fake.chmod(0o755)


class FieldCardServer(LiveBrowserCase):
    """The server's side, over HTTP."""
    width, height = 1000, 700

    @classmethod
    def load(cls, v):
        load_fake(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def token(self):
        html = urllib.request.urlopen(self.base + "/").read().decode()
        return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    def post(self, path, body, stream=False):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token()})
        try:
            r = urllib.request.urlopen(req, timeout=90)
        except urllib.error.HTTPError as e:
            return json.loads(e.read() or b"{}")
        if stream:
            return [json.loads(x.decode()[6:]) for x in r if x.decode().startswith("data: ")]
        return json.loads(r.read())

    def ask(self, message):
        return self.post("/api/ask", {"message": message}, stream=True)

    def card(self, message):
        evs = self.ask(message)
        cards = [e for e in evs if e["type"] == "fieldcard"]
        self.assertEqual(len(cards), 1, evs)
        self.assertEqual([e for e in evs if e["type"] == "editcard"], [])
        texts = " ".join(e.get("text", "") for e in evs if e["type"] == "text")
        self.assertNotIn("EDIT:", texts)                            # the line itself is never shown
        return cards[0]

    def read(self, table, iid):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/tracker.py"), "read", table, "--id", iid],
                           capture_output=True, text=True, cwd=self.v.root)
        return json.loads(r.stdout)[0]

    def rows(self, table):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/tracker.py"), "read", table],
                           capture_output=True, text=True, cwd=self.v.root)
        return json.loads(r.stdout)

    def staged(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json"))

    def test_the_card_shows_the_preview_and_the_dashboards_patch_and_nothing_is_written(self):
        before = self.staged()
        c = self.card("edit ABC-A-001 | status | done ; ABC-A-001 | due date | 20-11-2026")
        self.assertTrue(c["valid"], c)
        self.assertEqual(c["problems"], [])
        self.assertEqual(len(c["items"]), 1)
        it = c["items"][0]
        self.assertEqual((it["id"], it["k"]), ("ABC-A-001", "actions"))
        self.assertEqual(it["patch"], {"st": "Closed", "due": "2026-11-20"})        # the dashboard's own field names
        self.assertTrue(any("Status: Open → Closed" in ln for ln in c["lines"]), c["lines"])   # propose.py preview's own line
        self.assertTrue(any("20-11-2026" in ln for ln in c["lines"]), c["lines"])
        self.assertEqual(self.read("actions", "ABC-A-001")["status"], "Open")     # nothing written
        self.assertEqual(self.staged(), before)                                     # nothing staged

    def test_several_items_go_on_one_card(self):
        c = self.card("edit ABC-A-001 | priority | High ; ABC-A-002 | owner | Alan Carter")
        self.assertTrue(c["valid"], c)
        self.assertEqual(sorted(i["id"] for i in c["items"]), ["ABC-A-001", "ABC-A-002"])
        self.assertEqual(c["title"], "Change 2 items")

    def test_problems_are_named_and_the_card_cannot_go_ahead(self):
        c = self.card("edit ABC-A-001 | status | Nonsense")
        self.assertFalse(c["valid"])
        self.assertEqual(c["items"], [])
        self.assertTrue(any("Status can be" in p for p in c["problems"]), c)
        c = self.card("edit ABC-A-999 | status | Closed")
        self.assertFalse(c["valid"])
        self.assertIn("ABC-A-999 isn't in the tracker", c["problems"])
        c = self.card("edit ABC-A-001 | workstream | Delivery")
        self.assertFalse(c["valid"])
        self.assertTrue(any("isn't a field the dashboard edits" in p for p in c["problems"]), c)
        c = self.card("edit ABC-A-001 | due date | 31-02-2026")
        self.assertFalse(c["valid"])
        self.assertTrue(any("isn't a real date" in p for p in c["problems"]), c)

    def test_a_made_decision_cannot_go_back_to_pending(self):
        made = [d for d in self.rows("decisions") if d["status"] == "Made"]
        if not made:
            self.skipTest("no made decision in the sample")
        c = self.card(f"edit {made[0]['id']} | status | Pending")
        self.assertFalse(c["valid"])
        self.assertTrue(any("can't go back to pending" in p for p in c["problems"]), c)

    def test_a_value_it_already_has_changes_nothing(self):
        cur = self.read("actions", "ABC-A-001")["priority"]
        evs = self.ask(f"edit ABC-A-001 | priority | {cur}")
        self.assertEqual([e for e in evs if e["type"] == "fieldcard"], [])
        self.assertTrue(any("Nothing to change" in e.get("text", "") for e in evs if e["type"] == "text"), evs)

    def test_the_change_card_for_a_spec_is_unchanged(self):
        evs = self.ask("spec ABC-A-001 status Closed")
        self.assertEqual(len([e for e in evs if e["type"] == "editcard"]), 1, evs)
        self.assertEqual([e for e in evs if e["type"] == "fieldcard"], [])

    def test_no_new_route_and_the_prompt_says_how(self):
        src = (self.v.root / "system/scripts/live_server.py").read_text()
        self.assertIn("EDIT: <item ID> | <field> | <new value>", src)
        self.assertNotIn("/api/field", src)                         # the page's own save routes, nothing new
        routes = re.findall(r'"(/api/[a-z/_-]+)"', src)
        self.assertFalse([r for r in routes if "field" in r], routes)


class FieldCardBrowser(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        load_fake(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def proposals(self):
        out = []
        for d in ("system/staging", "system/staging/applied"):
            out += sorted((self.v.root / d).glob("proposed-*dashboard*.json"))
        return out

    def test_go_ahead_saves_through_the_dashboards_own_save_and_undo_puts_it_back(self):
        b = self.b
        before = set(self.proposals())
        b.eval("openChat(); $('#chIn').value='edit ABC-A-001 | status | Closed ; ABC-A-001 | priority | Urgent'; send()", wait=False)
        b.wait("document.querySelector('#chLog [data-fcard] [data-fc=go]')", 20)
        self.assertEqual(b.eval("[...document.querySelectorAll('#chLog [data-fcard] [data-fc]')].map(x=>x.textContent)"),
                         ["Cancel", "Go ahead"])
        self.assertEqual(b.eval("A.find(x=>x.id==='ABC-A-001').st"), "Open")
        self.assertEqual(set(self.proposals()), before)                             # nothing before Go ahead
        b.click("#chLog [data-fcard] [data-fc=go]")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Saved: ABC-A-001'))", 30)
        b.wait("A.find(x=>x.id==='ABC-A-001').st==='Closed'", 20)
        self.assertEqual(b.eval("A.find(x=>x.id==='ABC-A-001').pr"), "Urgent")
        new = set(self.proposals()) - before
        self.assertEqual(len(new), 1, new)                                          # one proposal, as the bulk bar writes
        data = json.loads(new.pop().read_text())
        self.assertEqual(data["source_run"], "dashboard")
        self.assertEqual([(i["op"], i["table"], i["id"]) for i in data["items"]], [("update", "actions", "ABC-A-001")])
        self.assertEqual(data["items"][0]["changes"]["status"], "Closed")
        self.assertTrue(data["items"][0]["changes"].get("closed"))                  # the dashboard's rule: closing fills the date
        b.click("#chLog [data-edundo]")
        b.wait("A.find(x=>x.id==='ABC-A-001').st==='Open'", 20)

    def test_cancel_writes_nothing(self):
        b = self.b
        before = set(self.proposals())
        b.eval("openChat(); $('#chIn').value='edit ABC-A-002 | priority | Low'; send()", wait=False)
        b.wait("document.querySelector('#chLog [data-fcard] [data-fc=cancel]')", 20)
        was = b.eval("A.find(x=>x.id==='ABC-A-002').pr")
        b.click("#chLog [data-fcard] [data-fc=cancel]")
        b.wait("document.querySelector('#chLog [data-fcard] .acts').textContent==='Cancelled'", 10)
        self.assertEqual(set(self.proposals()), before)
        self.assertEqual(b.eval("A.find(x=>x.id==='ABC-A-002').pr"), was)

    def test_a_card_with_problems_offers_only_cancel(self):
        b = self.b
        b.eval("openChat(); $('#chIn').value='edit ABC-A-999 | status | Closed'; send()", wait=False)
        b.wait("document.querySelector('#chLog [data-fcard] [data-fc=cancel]')", 20)
        self.assertEqual(b.eval("[...document.querySelectorAll('#chLog [data-fcard] [data-fc]')].map(x=>x.dataset.fc)"), ["cancel"])
        self.assertIn("isn't in the tracker", b.eval("document.querySelector('#chLog [data-fcard] .edprob').textContent"))


if __name__ == "__main__":
    unittest.main()
