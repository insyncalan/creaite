"""#358 (v2.6.5): say what the mail check is doing. Page only; no guarded file.

Run: python3 dev/tests/test_mail_check.py     (needs Node for the classifier, Google Chrome for the browser tests; each skipped otherwise)

1. The classifier (src/core/mailCheck.js) under Node: every label kind, an allow-list on whole labels, Found N, the closing line,
   and mutants (each must fail the tests).
2. The pin: the page's marker equals live_server.PANEL_SWEEP_STEP, read as text by a regex (never imported).
3. The permanent leak gate (never relaxed): no subject, sender, command or other label text reaches the line, the badge, the live
   node, the closing line or the steps list. Static (every string the module draws is fixed) and in a browser.
4. A browser against the real live server with a stand-in `claude` that streams real tool labels: the line replaces the quip for a
   mail check only, no total or percentage, the end line, Found N from the check's own file, the badge with the chat closed, the
   announcement count, and the same at 900 px.
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
MC = REPO / "system/templates/dashboard/src/core/mailCheck.js"
LIVE = REPO / "system/scripts/live_server.py"
SECRET = "Zebra Quarterly Budget Teams Mail Calendar Channel"      # a subject that holds the words a loose match would hit

SCRIPT = """
const f = await import(%s); const out = {};
const L = ["Microsoft 365: outlook email search", "Microsoft 365: chat message search", "Microsoft 365: teams list chats",
  "Microsoft 365: teams list channel messages", "Microsoft 365: outlook calendar search", "Microsoft 365: read resource",
  "Microsoft 365: sharepoint search", "Searching mail", "Searching Teams chats", "Reading Teams chats", "Reading Teams channels",
  "Reading the calendar", "Reading a meeting, a message or a chat", "Searching SharePoint and OneDrive", "Staging what the sweep found",
  "ToolSearch", "Using cx-sweep", "Read SKILL.md", "Write followed.json", "Running sweep.py followed --out x",
  "Running tracker.py mail Teams Calendar Channel", "Microsoft 365: send mail", "Microsoft 365: outlook send mail", "", null, 7];
out.kinds = L.map(l => f.mcClassify(l));
let s = f.mcNew();
out.start = f.mcLine(s);
for (const l of L) s = f.mcStep(s, l);
out.after = s; out.line = f.mcLine(s); out.badge = f.mcBadge(s); out.places = f.mcPlaces(s);
let t = f.mcNew(); t = f.mcStep(t, "Microsoft 365: teams list chats"); t = f.mcStep(t, "Microsoft 365: outlook email search");
out.order = t.places; out.teamsFirstBadge = f.mcBadge(f.mcStep(f.mcNew(), "Microsoft 365: teams list chats"));
let u = f.mcStep(f.mcNew(), "Microsoft 365: read resource"); out.readOnly = [u, f.mcLine(u)];
let one = f.mcStep(f.mcStep(f.mcNew(), "Searching mail"), "Reading a meeting, a message or a chat"); out.one = f.mcLine(one);
out.isRun = [f.mcIsRun({sweep: true}), f.mcIsRun({kind: "sweep"}), f.mcIsRun({sweep: false, kind: "chat"}), f.mcIsRun(null)];
out.stamp = ["proposed-2026-10-25-0905-sweep.json", "proposed-2026-10-25-0905-sweep-3.json", "proposed-2026-10-25-0905-dashboard.json",
  "x/proposed-2026-10-25-0905-sweep.json", "proposed-2026-10-25-0905-sweepx.json", null].map(f.mcFileStamp);
const rows = [{file: "proposed-2026-10-25-0905-sweep.json", p: "ABC"}, {file: "proposed-2026-10-25-0905-sweep.json", p: ""},
  {file: "proposed-2026-10-25-0906-sweep-2.json", p: null}, {file: "proposed-2026-10-25-0905-dashboard-x.json", p: ""},
  {file: "proposed-2026-10-25-0850-sweep.json", p: ""}, {file: "proposed-2026-10-25-0920-sweep.json", p: ""}, {file: "m.docx", p: ""}];
out.found = f.mcFound(rows, "2026-10-25T09:04:10", "2026-10-25T09:10:59"); out.foundNone = f.mcFound([], "2026-10-25T09:04:10", "2026-10-25T09:10:59");
const two = f.mcStep(f.mcStep(f.mcNew(), "Searching mail"), "Reading Teams channels");
out.ends = [f.mcEnd("done", two, {n: 7, need: 4}), f.mcEnd("done", two, {n: 1, need: 1}), f.mcEnd("done", two, {n: 0, need: 0}), f.mcEnd("done", two, null),
  f.mcEnd("stopped", two, {n: 2, need: 1}), f.mcEnd("early", two, {n: 2, need: 2}), f.mcEnd("stopped", two, {n: 0, need: 0}), f.mcEnd("early", f.mcNew(), {n: 0, need: 0}),
  f.mcEnd("stopped", two, null)];
out.stepText = ["Sweeping (stages proposals only)", "Microsoft 365: outlook email search", "Searching mail", "Running sweep.py followed --subject Q3", "Write followed-x.json", "Running tracker.py x", "ToolSearch", "Microsoft 365: nonsense"].map(f.mcStepText);
out.marker = f.MC_MARKER;
console.log(JSON.stringify(out));
"""


def run_node(path=MC, script=SCRIPT):
    src = Path(path).read_text(encoding="utf-8")
    tmp = HERE / ".mc_tmp"
    tmp.mkdir(exist_ok=True)
    f = tmp / "mailCheck.mjs"
    f.write_text(src, encoding="utf-8")
    r = subprocess.run(["node", "--input-type=module", "-e", script % json.dumps(f.as_uri())], capture_output=True, text=True, timeout=60)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def mutant(old, new):
    """Run the unit script against mailCheck.js with one change; returns the output."""
    src = MC.read_text(encoding="utf-8")
    assert old in src, old
    tmp = HERE / ".mc_mut"
    tmp.mkdir(exist_ok=True)
    f = tmp / "m.mjs"
    f.write_text(src.replace(old, new, 1), encoding="utf-8")
    r = subprocess.run(["node", "--input-type=module", "-e", SCRIPT % json.dumps(f.as_uri())], capture_output=True, text=True, timeout=60)
    shutil.rmtree(tmp, ignore_errors=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


@unittest.skipUnless(shutil.which("node"), "needs Node")
class Classifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = run_node()

    def test_every_label_kind(self):
        k = self.o["kinds"]
        S = lambda p: {"kind": "search", "place": p}
        self.assertEqual(k[:15], [S("mail"), S("teams"), S("teams"), S("teams"), S("calendar"), {"kind": "read"}, S(None),
                                  S("mail"), S("teams"), S("teams"), S("teams"), S("calendar"), {"kind": "read"}, S(None), None])
        # a Bash label, ToolSearch, Read and Write, the followed-people command, a send tool, nothing at all: nothing
        self.assertEqual(k[15:], [None] * 11)

    def test_an_allow_list_on_whole_labels_a_subject_changes_nothing(self):
        self.assertEqual(self.o["kinds"][20], None)               # "Running tracker.py mail Teams Calendar Channel"
        self.assertEqual(self.o["after"], {"places": ["mail", "teams", "calendar"], "searches": 12, "reads": 2})

    def test_the_line_has_no_total_no_percentage_and_no_claim_of_finished(self):
        self.assertEqual(self.o["start"], "Starting")
        self.assertEqual(self.o["line"], "Looked in so far: Outlook mail, Teams, calendar · 12 searches, 2 items read")
        self.assertNotRegex(self.o["line"], r"\bof \d|%|Done|Finished|\d/\d")
        self.assertEqual(self.o["one"], "Looked in so far: Outlook mail · 1 search, 1 item read")

    def test_places_are_a_set_in_a_fixed_order_and_a_read_is_never_a_place(self):
        self.assertEqual(self.o["order"], ["mail", "teams"])      # Teams first, mail second: still mail, Teams
        self.assertEqual(self.o["teamsFirstBadge"], "Mail check: Teams")
        self.assertEqual(self.o["readOnly"][0], {"places": [], "searches": 0, "reads": 1})
        self.assertEqual(self.o["readOnly"][1], "Starting")

    def test_the_badge_and_the_live_node_carry_places_only_never_a_counter(self):
        self.assertEqual(self.o["badge"], "Mail check: mail, Teams, calendar")
        self.assertEqual(self.o["places"], "Looked in so far: Outlook mail, Teams, calendar")
        self.assertFalse(re.search(r"\d", self.o["badge"] + self.o["places"]))

    def test_it_knows_a_mail_check_from_the_run_record(self):
        self.assertEqual(self.o["isRun"], [True, True, False, False])

    def test_found_n_counts_only_the_checks_own_files_inside_the_window(self):
        self.assertEqual(self.o["stamp"], ["2026-10-25T09:05", "2026-10-25T09:05", None, "2026-10-25T09:05", None, None])
        self.assertEqual(self.o["found"], {"n": 3, "need": 2})    # not the dashboard row, not 08:50 or 09:20, not a docx
        self.assertEqual(self.o["foundNone"], {"n": 0, "need": 0})

    def test_the_closing_lines(self):
        e = self.o["ends"]
        self.assertEqual(e[0], "Finished. Looked in Outlook mail, Teams. Found 7 new, 4 need a project.")
        self.assertEqual(e[1], "Finished. Looked in Outlook mail, Teams. Found 1 new, 1 needs a project.")
        self.assertEqual(e[2], "Finished. Nothing new to review.")           # never "Found 0"
        self.assertEqual(e[3], "Finished. Open Review to see what it found.")
        self.assertEqual(e[4], "Stopped. Looked in Outlook mail, Teams. Found 2 new so far, 1 needs a project.")
        self.assertEqual(e[5], "Stopped early. Looked in Outlook mail, Teams. Found 2 new so far, 2 need a project.")
        self.assertEqual(e[6], "Stopped. Looked in Outlook mail, Teams. Nothing saved yet.")
        self.assertEqual(e[7], "Stopped early. Nothing saved yet.")
        self.assertEqual(e[8], "Stopped. Looked in Outlook mail, Teams.")

    def test_the_steps_list_shows_fixed_phrases_only(self):
        self.assertEqual(self.o["stepText"], ["Sweeping (stages proposals only)", "Microsoft 365: outlook email search", "Searching mail",
                                              "A creaite step", "A creaite step", "A creaite step", "A creaite step", "A creaite step"])

    def test_mutants_fail(self):
        def broke(old, new, fn):
            o = mutant(old, new)
            self.assertTrue(o is None or fn(o), f"mutant survived: {old!r}")
        # a classifier that scans free text: the subject case must fail
        broke("return Object.prototype.hasOwnProperty.call(PLAIN, label) ? { kind: \"search\", place: PLAIN[label] } : null;",
              "return /mail/i.test(label) ? { kind: \"search\", place: \"mail\" } : null;", lambda o: o["kinds"][20] is not None or o["kinds"] != self.o["kinds"])
        # the highest index instead of a set: Teams before mail must fail
        broke("PLACE_ORDER.filter(p => p === c.place || s.places.includes(p))", "[c.place]", lambda o: o["order"] != ["mail", "teams"])
        # read_resource counted as a place
        broke("if (tool === READ_CHAT) return { kind: \"read\" };", "if (tool === READ_CHAT) return { kind: \"search\", place: \"mail\" };",
              lambda o: o["readOnly"][0]["places"] != [])
        # a total
        broke("return `Looked in so far: ${placeList(s, PLACE_NAMES)} · ${plural(s.searches, \"search\", \"searches\")}",
              "return `Looked in so far: ${placeList(s, PLACE_NAMES)} · 1 of 4 · ${plural(s.searches, \"search\", \"searches\")}", lambda o: o["line"] != self.o["line"])
        # a counter on the badge
        broke("`Mail check: ${placeList(s, PLACE_SHORT)}`", "`Mail check: ${placeList(s, PLACE_SHORT)} ${s.searches}`", lambda o: o["badge"] != self.o["badge"])
        # a dashboard row counted
        broke("sweep(?:-\\d+)?\\.json$", "(?:sweep|dashboard-x)(?:-\\d+)?\\.json$", lambda o: o["found"] != self.o["found"])
        # the raw label in the steps list
        broke("return c ? String(label) : \"A creaite step\";", "return String(label);", lambda o: o["stepText"] != self.o["stepText"])
        # "Found 0"
        broke("found.n ? `Finished.${looked}", "true ? `Finished.${looked}", lambda o: o["ends"][2] != self.o["ends"][2])


class Pin(unittest.TestCase):
    def test_the_page_marker_equals_the_servers_marker(self):
        """Read as text, never imported (importing live_server would run it): a changed letter on either side fails."""
        server = re.search(r'^PANEL_SWEEP_STEP = "([^"\n]*)"$', LIVE.read_text(encoding="utf-8"), re.M)
        page = re.search(r'^export const MC_MARKER = "([^"\n]*)";', MC.read_text(encoding="utf-8"), re.M)
        self.assertTrue(server and page, "both constants must be plain strings on one line")
        self.assertEqual(page.group(1), server.group(1))
        self.assertEqual(server.group(1), "Sweeping (stages proposals only)")

    def test_the_pin_catches_a_one_letter_change_on_either_side(self):
        a = 'PANEL_SWEEP_STEP = "Sweeping (stages proposals only)"'
        for text, rx in ((a.replace("Sweeping", "Sweepinq"), r'^PANEL_SWEEP_STEP = "([^"\n]*)"$'),):
            self.assertNotEqual(re.search(rx, text, re.M).group(1), "Sweeping (stages proposals only)")


class LeakGate(unittest.TestCase):
    """Permanent. The module draws only fixed phrases and whole numbers; this is never relaxed."""

    def test_no_label_text_is_ever_returned_by_a_drawing_function(self):
        src = MC.read_text(encoding="utf-8")
        for fn in ("mcLine", "mcBadge", "mcPlaces", "mcEnd", "mcStepText"):
            body = src[src.index(f"export function {fn}") if f"export function {fn}" in src else src.index(f"export const {fn}"):]
            body = body[:body.index("\n}\n") if "\n}\n" in body[:900] else 400]
            self.assertNotRegex(body, r"\blabel\b.*\$\{|\$\{[^}]*label", f"{fn} must not interpolate a label")

    def test_a_vip_word_is_in_no_new_string(self):
        self.assertNotRegex(MC.read_text(encoding="utf-8").lower(), r"\bvip\b")

    @unittest.skipUnless(shutil.which("node"), "needs Node")
    def test_hostile_labels_leave_no_trace_in_any_output(self):
        script = """
const f = await import(%s); const bad = [%s, "Running sweep.py followed --subject " + %s, "Microsoft 365: " + %s, %s + " Searching mail", "Write " + %s];
let s = f.mcNew(); for (const l of bad) s = f.mcStep(s, l);
const outs = [f.mcLine(s), f.mcBadge(s), f.mcPlaces(s), f.mcEnd("done", s, {n: 1, need: 1}), f.mcEnd("early", s, null), ...bad.map(f.mcStepText)];
console.log(JSON.stringify({s, outs}));
""" % ("%s", json.dumps(SECRET), json.dumps(SECRET), json.dumps(SECRET), json.dumps(SECRET), json.dumps(SECRET))
        o = run_node(script=script)
        self.assertEqual(o["s"], {"places": [], "searches": 0, "reads": 0})
        for out in o["outs"]:
            self.assertNotIn("Zebra", out)


# ── the browser ──

FAKE = r'''#!/usr/bin/env python3
import json, sys, time
from datetime import datetime
from pathlib import Path
args = sys.argv[1:]
message = args[args.index("--") + 1]
root = Path.cwd()
out = lambda o: print(json.dumps(o), flush=True)
M = "mcp__claude_ai_Microsoft_365__"
n = [0]
def call(name, inp=None, error=False, pause=0.35):
    n[0] += 1
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{n[0]}", "name": name, "input": inp or {}}]}})
    time.sleep(pause)
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{n[0]}", "is_error": error, "content": "x"}]}})
out({"type": "system", "subtype": "init", "session_id": "sess-1"})
low = message.lower()
if low.startswith(("sweep", "refresh")):
    slow = (root / "slow-sweep").exists()
    if low.startswith("refresh"):
        call(M + "outlook_calendar_search")
        reply = "Calendar refreshed."
    else:
        call("Bash", {"command": "system/scripts/run sweep.py followed --subject SECRETSUBJECT Zebra Quarterly Budget Teams Mail Calendar Channel"})
        call(M + "outlook_email_search")
        call("ToolSearch")
        call(M + "outlook_email_search", error=True)
        call(M + "outlook_email_search")
        call(M + "chat_message_search")
        call(M + "read_resource")
        if slow:
            time.sleep(40)
        if (root / "fail-sweep").exists():
            sys.stderr.write("the stand-in claude failed\n")
            sys.exit(3)
        call(M + "teams_list_channel_messages")
        call(M + "read_resource")
        call(M + "outlook_calendar_search")
        call(M + "sharepoint_search")
        call("Bash", {"command": "system/scripts/run sweep.py stage x"})
        now = datetime.now()
        item = lambda n, proj: {"n": n, "op": "new", "table": "actions", "match": "strong" if proj else "none", "flags": [], "decision": "pending",
                                "values": {"project": proj, "description": f"Share the plan {n}", "owner": "Alan Carter", "raised": now.strftime("%Y-%m-%d"),
                                           "source": "Email · Subject: Zebra"}}
        (root / "system/staging" / f"proposed-{now:%Y-%m-%d-%H%M}-sweep.json").write_text(json.dumps(
            {"created": now.strftime("%Y-%m-%dT%H:%M:00"), "source_run": "cx-sweep", "files": [], "items": [item(1, "ABC"), item(2, "")]}))
        reply = "Swept."
else:
    reply = "All done."
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-1"})
'''

FIXED_STEPS = {"Sweeping (stages proposals only)", "A creaite step", "Microsoft 365: outlook email search", "Microsoft 365: chat message search",
               "Microsoft 365: teams list channel messages", "Microsoft 365: outlook calendar search", "Microsoft 365: read resource",
               "Microsoft 365: sharepoint search"}


def _live_cls():
    from live_browser import LiveBrowserCase

    class MailCheckBrowser(LiveBrowserCase):
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

        def begin(self, message, chat_open=True):
            b = self.b
            b.eval("openChat()" if chat_open else "closeChat()")
            b.eval(f"window.P=askLive({message!r},null).catch(()=>{{}}); 0")
            if not chat_open:
                b.eval("closeChat()")
            b.wait("RB.state==='running'", 20)

        def finish(self, timeout=90):
            self.b.wait("window.P&&RB.state!=='running'", timeout)
            self.b.pump(0.6)

        def text_of(self, sel):
            return self.b.eval(f"[...document.querySelectorAll({sel!r})].map(e=>e.textContent).join(' | ')")

        def everything(self):
            return self.b.eval("""document.body.innerText+' '+[...document.querySelectorAll('[title],[aria-label]')].map(e=>(e.title||'')+' '+(e.getAttribute('aria-label')||'')).join(' ')+' '+
              [...document.querySelectorAll('#chLog details li')].map(e=>e.textContent).join(' ')""")

        def test_the_true_line_replaces_the_quip_and_ends_with_found_n(self):
            b = self.b
            self.begin("sweep")
            b.wait("!!document.querySelector('#chLog .mcline')&&/Looked in so far: Outlook mail/.test(document.querySelector('#chLog .mcline').textContent)", 40)
            self.assertEqual(b.eval("document.querySelectorAll('#chLog .step.working .quip').length"), 0)       # the quip is replaced for a mail check
            seen = []
            for _ in range(120):
                seen.append(b.eval("(document.querySelector('#chLog .mcline')||{}).textContent||''"))
                if b.eval("RB.state")!="running":
                    break
                b.pump(0.25)
            line = [x for x in seen if x][-1]
            self.assertRegex(line, r"^Looked in so far: Outlook mail, Teams, calendar · \d+ searches, \d+ items read$")
            self.assertNotRegex(" ".join(seen), r"\bof \d|%|Finished|Done")
            self.finish()
            end = b.eval("[...document.querySelectorAll('#chLog .msg.runend')].pop().textContent")
            self.assertEqual(end, "Finished. Looked in Outlook mail, Teams, calendar. Found 2 new, 1 needs a project.")
            # the permanent leak gate: nothing from the labels reaches the page
            every = self.everything()
            for bad in ("SECRETSUBJECT", "Zebra", "followed"):
                self.assertNotIn(bad, every)
            steps = b.eval("[...document.querySelectorAll('#chLog .step.steps li')].map(e=>e.textContent)")
            self.assertTrue(steps and set(steps) <= FIXED_STEPS, steps)

        def test_only_a_mail_check_loses_the_quip(self):
            b = self.b
            self.begin("hello")
            self.assertEqual(b.eval("document.querySelectorAll('#chLog .mcline').length"), 0)
            self.finish()
            self.assertEqual(b.eval("document.querySelectorAll('#chLog .msg.runend').length"), 0)

        def test_refresh_calendar_ends_with_nothing_new(self):
            self.begin("refresh calendar")
            self.finish()
            end = self.b.eval("[...document.querySelectorAll('#chLog .msg.runend')].pop().textContent")
            self.assertEqual(end, "Finished. Nothing new to review.")

        def test_the_badge_with_the_chat_closed_shows_places_only_and_fits(self):
            b = self.b
            b.eval("window.AN=[]; for (const [id,n] of [['rbL','badge'],['askLive','live'],['mcLive','node'],['chLog','log']]) { let last=document.getElementById(id).textContent; "
                   "new MutationObserver(()=>{ const t=document.getElementById(id).textContent; if(t!==last){ last=t; AN.push([n,t]); } }).observe(document.getElementById(id),{childList:true,characterData:true,subtree:true}); } 0")
            self.begin("sweep", chat_open=False)
            b.wait("/Mail check: mail/.test(document.getElementById('rbL').textContent)", 40)
            o = b.eval("(()=>{ const l=document.getElementById('rbL'), r=document.getElementById('runBadge').getBoundingClientRect(); return {text:l.textContent, title:l.title, clipped:l.scrollWidth>l.clientWidth, inside:r.left>=0&&r.right<=innerWidth}; })()")
            self.assertFalse(re.search(r"\d", o["text"]))                       # never a counter in the badge
            self.assertTrue(o["inside"])
            self.finish()
            an = b.eval("AN")
            places = [t for n, t in an if n == "badge" and t.startswith("Mail check")]
            self.assertLessEqual(len(places), 3, places)                                # at most three place changes on the badge
            self.assertLessEqual(len([1 for n, t in an if n == "node" and t]), 3)
            self.assertEqual(self.b.eval("document.getElementById('mcLive').textContent"), "")
            live = [t for n, t in an if n == "live"]
            self.assertEqual(len(live), 1)                                      # one end announcement, with Found N once
            self.assertIn("Found 2 new, 1 needs a project", live[0])
            self.assertEqual(len([1 for n, t in an if n == "badge" and t.startswith("took")]), 1)

        def test_with_the_chat_open_the_closing_line_is_readable_and_the_node_is_not_the_log(self):
            b = self.b
            self.assertEqual(b.eval("(()=>{ const n=document.getElementById('mcLive'); return n.closest('#chat')!==null && !n.closest('#chLog'); })()"), True)
            self.begin("sweep")
            self.finish()
            self.assertEqual(b.eval("[...document.querySelectorAll('#chLog .msg.runend')].pop().closest('[aria-hidden=true]')"), None)
            self.assertEqual(b.eval("document.getElementById('askLive').textContent"), "")

        def test_a_reload_mid_run_rebuilds_the_line_from_the_run_record(self):
            b = self.b
            (self.v.root / "slow-sweep").write_text("")
            self.begin("sweep")
            b.wait("/Looked in so far: Outlook mail, Teams/.test(document.querySelector('#chLog .mcline')?.textContent||'')", 40)
            want = "Looked in so far: Outlook mail, Teams · 3 searches, 1 item read"     # the failed search is not counted
            b.wait(f"document.querySelector('#chLog .mcline').textContent==={want!r}", 40)
            b.reload("typeof go==='function' && LIVE")
            b.eval("openChat()")
            b.wait(f"(document.querySelector('#chLog .mcline')||{{}}).textContent==={want!r}", 40)
            after = b.eval("document.querySelector('#chLog .mcline').textContent")
            self.assertEqual(after, want)                                       # the same places and counts, replayed from the start
            self.assertEqual(b.eval("document.querySelectorAll('#chLog .step.working .quip').length"), 0)
            b.eval("stopAsk()")
            b.pump(1.0)
            (self.v.root / "slow-sweep").unlink()

        def test_stopped_and_failed_endings(self):
            b = self.b
            (self.v.root / "slow-sweep").write_text("")
            self.begin("sweep")
            b.wait("/Looked in so far: Outlook mail, Teams/.test(document.querySelector('#chLog .mcline')?.textContent||'')", 40)
            b.eval("stopAsk()")
            self.finish(60)
            end = b.eval("[...document.querySelectorAll('#chLog .msg.runend')].pop().textContent")
            self.assertRegex(end, r"^Stopped\. Looked in Outlook mail, Teams\. Nothing saved yet\.$")
            (self.v.root / "slow-sweep").unlink()
            for _ in range(40):
                if b.eval("api('/api/ask/running').then(r=>!(r.ok&&r.run&&!r.run.done))"):
                    break
                b.pump(0.25)
            (self.v.root / "fail-sweep").write_text("")
            self.begin("sweep")
            self.finish()
            end = b.eval("[...document.querySelectorAll('#chLog .msg.runend')].pop().textContent")
            self.assertRegex(end, r"^Stopped early\. Looked in Outlook mail, Teams\. ")
            (self.v.root / "fail-sweep").unlink()

    return MailCheckBrowser


try:
    import live_browser  # noqa: F401
    _have = True
except Exception:
    _have = False

if _have:
    _Base = _live_cls()

    class MailCheck1400(_Base):
        width, height = 1400, 900

    class MailCheck900(_Base):
        width, height = 900, 800

    del _Base

if __name__ == "__main__":
    unittest.main()
