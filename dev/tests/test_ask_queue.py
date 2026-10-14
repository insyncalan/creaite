"""BL-257: messages sent while ask creaite is working are queued and run in order when it finishes. A real browser against the real
live server, with a stand-in `claude` whose runs can be held part-way (a "gated" message waits for a release file in the vault).

- A message sent mid-run shows as Queued (under the log, not in it) and runs when the run ends; two run in order.
- Edit puts a queued message back in the box and takes it out of the queue; Remove takes it out.
- A run that ends with a question holds the queue; Run now (or Alan's own next message) lets it go on.
- Stop clears the queue, and says so.
- The queue is kept by the live server with the chat (system/staging/ask/queue/), so a reload keeps it.

Run: python3 dev/tests/test_ask_queue.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, os, sys, time
args = sys.argv[1:]
message = args[args.index("-p") + 1].split("\n")[0]
session = args[args.index("--resume") + 1] if "--resume" in args else "sess-" + os.urandom(4).hex()
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": session})
name = message.split()[-1]
if message.startswith("gated"):
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Working on " + name + "."}]}})
    for _ in range(600):
        if os.path.exists("release-" + name):
            break
        time.sleep(0.1)
    text = "Finished " + name + "."
elif message.startswith("question"):
    time.sleep(2)
    text = "Which project do you mean?"
else:
    text = "Reply to: " + message
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
out({"type": "result", "result": text, "session_id": session})
'''


class AskQueue(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    def setUp(self):
        super().setUp()
        self.b.eval("openChat()")

    def release(self, name):
        (self.v.root / f"release-{name}").write_text("go")

    def send(self, text):
        self.b.eval(f"$('#chIn').value={json.dumps(text)}; send()", wait=False)

    def has_reply(self, text):
        return f"[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes({json.dumps(text)}))"

    def queued(self):
        return self.b.eval("[...document.querySelectorAll('#chQueue .chqitem .chqtext')].map(e=>e.textContent)")

    def replies(self):
        return self.b.eval("[...document.querySelectorAll('#chLog .msg.a')].map(e=>e.textContent.trim()).filter(t=>t.startsWith('Reply to'))")

    def start_gated(self, name):
        self.send(f"gated {name}")
        self.b.wait(self.has_reply(f"Working on {name}"), 20)

    def queue_file(self):
        f = self.v.root / "system/staging/ask/queue/queue.json"
        return json.loads(f.read_text()) if f.is_file() else None

    def test_a_message_sent_mid_run_is_queued_and_runs_when_the_run_ends(self):
        b = self.b
        self.start_gated("a")
        self.send("quick one")
        b.wait("document.querySelectorAll('#chQueue .chqitem').length===1", 10)
        self.assertEqual(self.queued(), ["quick one"])
        self.assertEqual(b.eval("document.querySelector('#chQueue .chqitem .tag').textContent"), "Queued")
        self.assertEqual(b.eval("$('#chIn').value"), "")                                     # the box is free again
        self.assertFalse(b.eval("[...document.querySelectorAll('#chLog .msg.u')].some(m=>m.textContent.includes('quick one'))"))
        self.assertEqual([i["text"] for i in self.queue_file()["items"]], ["quick one"])      # kept by the server, with the chat
        self.send("quick two")
        b.wait("document.querySelectorAll('#chQueue .chqitem').length===2", 10)
        self.release("a")
        b.wait(self.has_reply("Reply to: quick two") + " && !RUN", 30)
        self.assertEqual(self.replies(), ["Reply to: quick one", "Reply to: quick two"])      # in order, one at a time
        self.assertTrue(b.eval("document.getElementById('chQueue').hidden"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#chLog .msg.u')].map(m=>m.firstChild.textContent.trim()).slice(-2)"),
                         ["quick one", "quick two"])
        self.assertIsNone(self.queue_file())

    def test_edit_and_remove(self):
        b = self.b
        self.start_gated("e")
        self.send("quick keep")
        self.send("quick drop")
        self.send("quick fix")
        b.wait("document.querySelectorAll('#chQueue .chqitem').length===3", 10)
        b.eval("document.querySelectorAll('#chQueue [data-qrm]')[1].click()")
        b.wait("document.querySelectorAll('#chQueue .chqitem').length===2", 10)
        b.eval("document.querySelectorAll('#chQueue [data-qedit]')[1].click()")
        b.wait("document.querySelectorAll('#chQueue .chqitem').length===1", 10)
        self.assertEqual(b.eval("$('#chIn').value"), "quick fix")                             # back in the box to change
        self.assertEqual(self.queued(), ["quick keep"])
        b.eval("$('#chIn').value=''")
        self.release("e")
        b.wait(self.has_reply("Reply to: quick keep") + " && !RUN", 30)
        b.pump(1.0)
        self.assertEqual(self.replies(), ["Reply to: quick keep"])

    def test_a_question_holds_the_queue_until_run_now(self):
        b = self.b
        self.send("question q")
        b.wait("!!RUN && !!document.querySelector('#chLog .step.working')", 10)        # the server has the run
        self.send("quick after")
        b.wait(self.has_reply("Which project") + " && !RUN", 20)
        b.pump(1.0)
        self.assertEqual(self.replies(), [])                                                  # held: Alan hasn't answered
        self.assertEqual(self.queued(), ["quick after"])
        self.assertTrue(self.queue_file()["held"])
        self.assertIn("waiting for your answer", b.eval("document.querySelector('#chQueue .chqhead').textContent"))
        b.eval("document.querySelector('#chQueue [data-qgo]').click()")
        b.wait(self.has_reply("Reply to: quick after") + " && !RUN", 20)
        self.assertEqual(self.queued(), [])

    def test_stop_clears_the_queue_and_says_so(self):
        b = self.b
        self.start_gated("s")
        self.send("quick never")
        b.wait("document.querySelectorAll('#chQueue .chqitem').length===1", 10)
        b.eval("stopAsk()")
        b.wait("!RUN", 20)
        self.assertTrue(b.eval("document.getElementById('chQueue').hidden"))
        self.assertIn("1 queued message was removed", b.eval("$('#chLog').textContent"))
        b.pump(1.0)
        self.assertEqual(self.replies(), [])
        self.assertIsNone(self.queue_file())

    def test_a_reload_keeps_the_queue_and_it_still_runs(self):
        b = self.b
        self.start_gated("r")
        self.send("quick kept")
        b.wait("document.querySelectorAll('#chQueue .chqitem').length===1", 10)
        b.reload("typeof go==='function' && LIVE")
        b.eval("openChat()")
        b.wait("document.querySelectorAll('#chQueue .chqitem').length===1", 10)
        self.assertEqual(self.queued(), ["quick kept"])
        self.release("r")
        b.wait(self.has_reply("Reply to: quick kept") + " && !RUN", 30)
        self.assertEqual(self.replies(), ["Reply to: quick kept"])


if __name__ == "__main__":
    unittest.main()
