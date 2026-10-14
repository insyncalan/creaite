"""BL-258: a change asked for in ask creaite is shown on ONE card with the exact before and after, and Approve writes it to the tracker
at once. The real live server with a stand-in `claude` that prepares a cx-edit spec and ends with `CHANGE: <file> | <title>`.

- The card is built from propose.py preview on the server's own snapshot, never the model's words; the page never sees the snapshot.
- Approve stages it and applies it through tracker.py apply, only that change: nothing else pending in staging is applied.
- Reject stages nothing and changes nothing; an answered card can't be used again.
- Undo last apply reverses an approved change.
- A validation failure can't be approved and stages nothing; a pending proposal for the same item offers Stage for review instead.
- The prompts say so; BL-141's file-change card is a different card (its own tests are unchanged).
- In the browser: the card shows each field before → after, Approve writes it, the page's data updates, Undo puts it back.

Run: python3 dev/tests/test_ask_change_card.py   (the browser test needs Google Chrome; skipped otherwise)
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
from live_browser import LiveBrowserCase, theme_names  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
message = args[args.index("-p") + 1].split("\n")[0]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-card"})
words = message.split()
if message.startswith("change"):                 # change <ID> <field> <value>
    spec = {"items": [{"op": "update", "table": "actions", "id": words[1], "changes": {words[2]: " ".join(words[3:])}}]}
    os.makedirs("system/staging/drafts", exist_ok=True)
    with open("system/staging/drafts/close.json", "w") as f:
        json.dump(spec, f)
    text = "Here is the change.\nCHANGE: system/staging/drafts/close.json | Change " + words[1]
elif message.startswith("outside"):
    text = "CHANGE: system/config/settings.json | Not a draft"
else:
    text = "Nothing to change."
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "result": text, "session_id": "sess-card"})
'''


# Each before and after value's text against its own band: 4.5:1 or more (the failures, as text)
CONTRAST = r"""[...document.querySelectorAll('#chLog .edcard .eddel, #chLog .edcard .edadd')].map(el=>{
  const P=s=>{ const m=s.match(/rgba?\(([^)]+)\)/); if(m) return m[1].split(/[ ,\/]+/).filter(Boolean).map(Number).slice(0,3);
    const c=s.match(/color\(srgb ([^)]+)\)/); return c[1].split(/[ \/]+/).filter(Boolean).map(Number).slice(0,3).map(v=>v*255); };
  const lum=c=>{ const f=v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }; return 0.2126*f(c[0])+0.7152*f(c[1])+0.0722*f(c[2]); };
  const cs=getComputedStyle(el), a=lum(P(cs.color)), b=lum(P(cs.backgroundColor)), r=(Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
  return r<4.5?`${el.className} ${r.toFixed(2)}`:""; })"""


def load_fake(v):
    from test_dashboard import populate
    populate(v)
    fake = v.root / "fake_claude.py"
    fake.write_text(FAKE)
    fake.chmod(0o755)


class ChangeCardServer(LiveBrowserCase):
    """The server's side, over HTTP (a browser is opened by the base class but not needed)."""
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

    def card(self, message):
        evs = self.post("/api/ask", {"message": message}, stream=True)
        cards = [e for e in evs if e["type"] == "editcard"]
        self.assertEqual(len(cards), 1, evs)
        texts = " ".join(e.get("text", "") for e in evs if e["type"] == "text")
        self.assertNotIn("CHANGE:", texts)                         # the line itself is never shown
        return cards[0]

    def action(self, aid):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/tracker.py"), "read", "actions", "--id", aid],
                           capture_output=True, text=True, cwd=self.v.root)
        return json.loads(r.stdout)[0]

    def staged(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json"))

    def test_the_card_shows_the_preview_and_nothing_is_written_until_approve(self):
        before = self.staged()
        c = self.card("change ABC-A-001 status Closed")
        self.assertTrue(c["valid"])
        self.assertIn("ABC-A-001 · Status: Open → Closed", c["lines"])              # propose.py preview's own line
        self.assertNotIn("_data", c)
        self.assertNotIn("_fingerprint", c)
        self.assertEqual(self.action("ABC-A-001")["status"], "Open")
        self.assertEqual(self.staged(), before)                                     # nothing staged yet
        self.assertFalse((self.v.root / "system/staging/drafts/close.json").exists())   # the server holds the snapshot
        r = self.post("/api/edit/approve", {"card": c["card"]})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["ids"], ["ABC-A-001"])
        self.assertIn("ABC-A-001", r["message"])
        self.assertEqual(self.action("ABC-A-001")["status"], "Closed")
        self.assertEqual(self.staged(), before)                                     # its proposal went to applied/
        again = self.post("/api/edit/approve", {"card": c["card"]})                 # used once
        self.assertFalse(again["ok"])
        u = self.post("/api/undo", {"apply_id": r["apply_id"]})                     # Undo last apply reverses it
        self.assertTrue(u["ok"], u)
        self.assertEqual(self.action("ABC-A-001")["status"], "Open")

    def test_undo_leaves_nothing_in_review_and_asking_again_gives_an_approvable_card(self):
        """BL-289 (v1.7.0 hand check 3): Undo used to put the card's change back into Review as pending, so asking again
        gave a card that could only stage it."""
        before = self.staged()
        c = self.card("change ABC-A-001 status Closed")
        r = self.post("/api/edit/approve", {"card": c["card"]})
        self.assertTrue(r["ok"], r)
        u = self.post("/api/undo", {"apply_id": r["apply_id"]})
        self.assertTrue(u["ok"], u)
        self.assertIn("not returned to Review", u["message"])
        self.assertEqual(self.action("ABC-A-001")["status"], "Open")
        self.assertEqual(self.staged(), before)                                     # nothing left in Review
        again = self.card("change ABC-A-001 status Closed")
        self.assertEqual(again["clash"], [])                                        # the same approvable card
        r2 = self.post("/api/edit/approve", {"card": again["card"]})
        self.assertTrue(r2["ok"], r2)
        self.assertEqual(self.action("ABC-A-001")["status"], "Closed")
        self.post("/api/undo", {"apply_id": r2["apply_id"]})
        self.assertEqual(self.action("ABC-A-001")["status"], "Open")
        self.assertEqual(self.staged(), before)

    def test_a_change_staged_for_review_is_not_marked_as_the_cards(self):
        """Only Approve marks a proposal as the card's; one staged for Review undoes back into Review, as before."""
        c = self.card("change ABC-A-001 status Closed")
        before = set(self.staged())
        s = self.post("/api/edit/stage", {"card": c["card"]})
        self.assertTrue(s["ok"], s)
        new = set(self.staged()) - before
        self.assertEqual(len(new), 1)
        f = self.v.root / "system/staging" / new.pop()
        self.assertNotIn("applied_on_card", json.loads(f.read_text()))
        f.unlink()

    def test_approve_applies_only_its_own_change(self):
        other = self.v.root / "system/staging/proposed-2026-10-12-090000-edit.json"
        other.write_text(json.dumps({"source_run": "cx-edit", "files": [], "items": [
            {"n": 1, "op": "update", "table": "actions", "id": "ABC-A-002", "changes": {"owner": "Alan Carter"},
             "match": "strong", "flags": [], "decision": "approved"}]}))
        pending = (self.v.root / "system/staging/proposed-pending.json").read_text()
        try:
            c = self.card("change ABC-A-001 priority High")
            r = self.post("/api/edit/approve", {"card": c["card"]})
            self.assertTrue(r["ok"], r)
            self.assertEqual(self.action("ABC-A-002")["owner"], "Sara Example")      # the other approved change waits for its apply
            self.assertTrue(other.exists())
            self.assertEqual((self.v.root / "system/staging/proposed-pending.json").read_text(), pending)
            self.post("/api/undo", {"apply_id": r["apply_id"]})
        finally:
            other.unlink(missing_ok=True)

    def test_reject_leaves_staging_and_the_tracker_as_they_were(self):
        before = self.staged()
        c = self.card("change ABC-A-001 status Closed")
        r = self.post("/api/edit/reject", {"card": c["card"]})
        self.assertTrue(r["ok"])
        self.assertIn("nothing was staged", r["message"])
        self.assertEqual(self.action("ABC-A-001")["status"], "Open")
        self.assertEqual(self.staged(), before)
        self.assertFalse(self.post("/api/edit/approve", {"card": c["card"]})["ok"])
        self.assertIsNone(self.post("/api/edit/pending", {})["card"])

    def test_a_validation_failure_cannot_be_approved_and_stages_nothing(self):
        before = self.staged()
        c = self.card("change ABC-A-001 status Nonsense")
        self.assertFalse(c["valid"])
        self.assertTrue(c["problems"], c)
        r = self.post("/api/edit/approve", {"card": c["card"]})
        self.assertFalse(r["ok"])
        self.assertEqual(self.staged(), before)
        self.assertEqual(self.action("ABC-A-001")["status"], "Open")
        self.post("/api/edit/reject", {"card": c["card"]})

    def test_a_pending_change_to_the_same_item_offers_stage_for_review(self):
        other = self.v.root / "system/staging/proposed-2026-10-12-091000-edit.json"
        other.write_text(json.dumps({"source_run": "cx-edit", "files": [], "items": [
            {"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"priority": "Low"},
             "match": "strong", "flags": [], "decision": "pending"}]}))
        try:
            c = self.card("change ABC-A-001 status Closed")
            self.assertEqual(c["clash"], ["ABC-A-001"])
            r = self.post("/api/edit/approve", {"card": c["card"]})
            self.assertFalse(r["ok"])
            self.assertEqual(r["clash"], ["ABC-A-001"])
            before = set(self.staged())
            s = self.post("/api/edit/stage", {"card": c["card"]})
            self.assertTrue(s["ok"], s)
            new = set(self.staged()) - before
            self.assertEqual(len(new), 1)
            staged = json.loads((self.v.root / "system/staging" / new.pop()).read_text())
            self.assertEqual([i["decision"] for i in staged["items"]], ["pending"])     # for Review, not approved
            self.assertEqual(self.action("ABC-A-001")["status"], "Open")
            for f in (self.v.root / "system/staging").glob("proposed-*-edit.json"):
                f.unlink()
        finally:
            other.unlink(missing_ok=True)

    def test_a_change_file_outside_the_drafts_is_refused(self):
        c = self.card("outside")
        self.assertIsNone(c["card"])
        self.assertIn("system/staging/drafts", c["refused"])

    def test_the_prompts_send_record_changes_to_the_card(self):
        src = (self.v.root / "system/scripts/live_server.py").read_text()
        self.assertIn("CHANGE: system/staging/drafts/<name>.json | <short title>", src)
        self.assertIn("Never stage it or run tracker.py apply yourself", src)
        self.assertIn("goes on the change card instead", src)


class ChangeCardBrowser(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        load_fake(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def test_approve_on_the_card_writes_it_and_the_dashboard_updates_and_undo_puts_it_back(self):
        b = self.b
        b.eval("openChat(); $('#chIn').value='change ABC-A-001 status Closed'; send()", wait=False)
        b.wait("document.querySelector('#chLog .edcard [data-ed=approve]')", 20)
        self.assertEqual(b.eval("document.querySelector('#chLog .edcard .eddel').textContent"), "Open")
        self.assertEqual(b.eval("document.querySelector('#chLog .edcard .edadd').textContent"), "Closed")
        self.assertEqual(b.eval("[...document.querySelectorAll('#chLog .edcard [data-ed]')].map(x=>x.textContent)"), ["Reject", "Approve"])
        self.assertEqual(b.eval("A.find(x=>x.id==='ABC-A-001').st"), "Open")
        bad = []
        for palette in theme_names():                                                      # the before and after read in every theme
            for mode in ("light", "dark"):
                b.eval(f"document.documentElement.dataset.palette='{palette}'; document.documentElement.dataset.theme='{mode}'")
                bad += [f"{palette} {mode} {x}" for x in b.eval(CONTRAST) if x]
        self.assertEqual(bad, [])
        b.eval("document.documentElement.dataset.palette='creaite'; document.documentElement.dataset.theme='light'")
        b.click("#chLog .edcard [data-ed=approve]")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Applied: ABC-A-001'))", 30)
        b.wait("A.find(x=>x.id==='ABC-A-001').st==='Closed'", 20)                    # the dashboard's data, reloaded
        self.assertIn("Approved", b.eval("document.querySelector('#chLog .edcard .acts').textContent"))
        b.click("#chLog [data-edundo]")
        b.wait("A.find(x=>x.id==='ABC-A-001').st==='Open'", 20)


if __name__ == "__main__":
    unittest.main()
