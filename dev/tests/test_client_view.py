"""v2.1.0 P8 (BL-336): the client view of the week's report, and the check of what is left out before every export.

Two parts, both on test_reports' fictional fixture and its fixed clock (Friday 09-10-2026):
- ClientCheckRoutes: /api/report/check on a live server (read only: it writes nothing). It lists what the report leaves out and
  why (not client-visible, Sensitive), offers rows that became client-visible, finds internal wording, and says whether the
  internal week is approved. The export route runs the same check before every client export and answers with it; an export is
  refused when the check finds a leak, and the internal health reason never reaches the exported page.
- ClientView: the view in a real browser (LiveBrowserCase; no Claude runs). The client health popover needs a reason, Match
  internal copies a section (and says so), the eyes show and hide rows, "Not in this report" lists what the report leaves out,
  Side by side shows the internal page read only, and Check and export opens the left-out check before any export.

Run: python3 dev/tests/test_client_view.py      (the browser part is skipped without Chrome)
Screenshots: CREAITE_SHOTS=<folder> python3 dev/tests/test_client_view.py ClientBrowser.test_zz_screenshots
"""
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture: populate, ReportVault, NOW)
from live_browser import LiveBrowserCase  # noqa: E402

VISIBLE_MSG = ("What it is: The vendor may leave the market.\nWhat it means for you: Testing could slip.\n"
               "What is being done: A second vendor is being lined up.")


def post(base, token, path, body):
    import urllib.request
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "X-Creaite-Token": token})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def section(doc, sid):
    return next(s for s in doc["sections"] if s["id"] == sid)


class ClientCheckRoutes(unittest.TestCase):
    """/api/report/check and the export's check, on a live server in a throwaway vault."""

    @classmethod
    def setUpClass(cls):
        import socket
        import time
        import urllib.request
        cls.v = v = R.ReportVault()
        R.populate(v)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_NOW": R.NOW, "CREAITE_NO_LAUNCH": "1"}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body):
        return post(self.base, self.token, path, body)

    def client(self):
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(r["ok"], r)
        return r["doc"]

    def change(self, name, items):
        self.v.propose(name, items)
        self.v.run("apply")

    def drafts(self):
        return sorted(p.name for p in (self.v.root / "system/staging/drafts").glob("*"))

    def test_1_check_lists_what_is_left_out_and_writes_nothing(self):
        doc = self.client()
        before = self.drafts()
        c = self.post("/api/report/check", {"doc": doc})
        self.assertTrue(c["ok"], c)
        lo = c["left_out"]
        why = {x["ref"]: (x["group"], x["kind"], x["why"]) for x in lo["items"]}
        self.assertEqual(why["ABC-005"], ("risks", "blocked", "not client-visible"))
        self.assertEqual(why["ABC-D-008"], ("decisions", "blocked", "not client-visible"))
        self.assertNotIn("ABC-006", why)                                    # shown, so not left out
        self.assertFalse(lo["ready"])                                       # the internal week is not approved yet
        self.assertIn("Approve the internal weekly report", lo["not_ready"])
        self.assertEqual(lo["findings"], [])
        self.assertEqual(self.drafts(), before, "the check wrote nothing")

    def test_2_a_row_that_became_client_visible_is_offered_and_a_sensitive_one_never(self):
        doc = self.client()
        self.assertTrue(self.post("/api/report/save", {"doc": doc, "base_version": 0})["ok"])
        self.change("visible", [{"n": 1, "op": "update", "table": "raid", "id": "ABC-005",
                                 "changes": {"client_visible": 1, "client_message": VISIBLE_MSG}, "decision": "approved"}])
        c = self.post("/api/report/check", {"doc": self.client()})
        add = [a for a in c["addable"] if a["row"]["ref"] == "ABC-005"]
        self.assertEqual([a["section"] for a in add], ["risks"])
        self.assertIn("The vendor may leave the market.", json.dumps(add[0]["item"]))
        self.assertNotIn("Vendor exits the market", json.dumps(c["addable"]))        # the client wording, never the internal
        self.change("sensitive", [{"n": 1, "op": "new", "table": "item_labels", "match": "strong", "flags": [], "decision": "approved",
                                   "values": {"item_id": "ABC-005", "label": "Sensitive", "reason": "kept from the client"}}])
        c = self.post("/api/report/check", {"doc": self.client()})
        self.assertEqual([a for a in c["addable"] if a["row"]["ref"] == "ABC-005"], [])
        item = next(x for x in c["left_out"]["items"] if x["ref"] == "ABC-005")
        self.assertEqual((item["kind"], item["why"]), ("sensitive", "Sensitive: never in a client report"))

    def test_3_internal_wording_is_a_finding_that_blocks(self):
        doc = self.client()
        section(doc, "summary")["text"] = "We will absorb the phase one overrun internally."
        c = self.post("/api/report/check", {"doc": doc})
        self.assertTrue(any("ABC-D-008" in f for f in c["left_out"]["findings"]), c["left_out"]["findings"])

    def test_4_the_export_runs_the_check_and_the_health_reason_stays_internal(self):
        doc = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})["doc"]
        section(doc, "health")["text"] = "UAT start slipped two weeks."
        self.assertTrue(self.post("/api/report/save", {"doc": doc, "base_version": 0})["ok"])
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(a["ok"], a)
        doc = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "fresh": True})["doc"]
        self.assertTrue(doc["based_on"], "a draft rebuilt after the internal week is approved locks to it")
        doc["meta"]["health_diff"] = {"internal": "At risk", "client": "On track", "reason": "INTERNAL-REASON-ZED"}
        section(doc, "health")["data"]["flag"] = "On track"
        section(doc, "health")["text"] = "Testing starts on plan."
        saved = self.post("/api/report/save", {"doc": doc})
        self.assertTrue(saved["ok"], saved)
        c = self.post("/api/report/check", {"doc": doc})
        self.assertTrue(c["left_out"]["ready"], c["left_out"])
        self.assertEqual(c["left_out"]["health"], {"internal": "At risk", "client": "On track", "reason": "INTERNAL-REASON-ZED"})
        e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "fmt": "html", "on_clash": "number"})
        self.assertTrue(e["ok"], e)      # #220: the filing name is reserved while the report is unfiled, so the export is numbered
        self.assertIn("left_out", e)                                        # the check ran before the export, and says what it found
        self.assertEqual(e["left_out"]["findings"], [])
        exported = Path(e["path"] if os.path.isabs(e["path"]) else self.v.root / e["path"]).read_text(encoding="utf-8")
        self.assertNotIn("INTERNAL-REASON-ZED", exported)
        self.assertNotIn("creaite-data", exported)
        section(doc, "summary")["text"] = "Restricted: the overrun is absorbed internally."
        self.assertTrue(self.post("/api/report/save", {"doc": doc})["ok"])
        e = self.post("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "fmt": "html"})
        self.assertFalse(e["ok"])
        self.assertIn("contains “restricted”", e["left_out"]["findings"])

    def test_5_the_health_difference_and_its_reason_are_in_the_draft_and_never_in_the_filed_file(self):
        """Alan, 15-10-2026: kept only in the draft, never in the filed client file, its data block included (the whole key goes: it
        names the internal flag too). The internal report reads the difference from the draft; after filing, from the client page's
        own flag."""
        for n, reason in enumerate(("DISTINCTIVE-REASON-ONE", "DISTINCTIVE-REASON-TWO")):
            doc = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "fresh": n == 0})["doc"]
            doc["meta"]["health_diff"] = {"internal": "At risk", "client": "On track", "reason": reason}
            section(doc, "health")["data"]["flag"] = "On track"
            saved = self.post("/api/report/save", {"doc": doc, "base_version": doc.get("version") or None})
            self.assertTrue(saved["ok"], saved)
            back = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})["doc"]
            self.assertEqual(back["meta"]["health_diff"]["reason"], reason, "the draft keeps it (the internal report shows it from here)")
            a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "force": True})
            self.assertTrue(a["ok"], a)
            filed = next(f for f in (self.v.root / "projects").glob("*/reports/2026-10-09 Client report*.html")
                         if "(2)" not in f.name).read_text(encoding="utf-8")          # not test 4's numbered export
            self.assertIn('"state": "approved"', filed)
            for gone in ("health_diff", reason, "DISTINCTIVE-REASON", '"internal": "At risk"'):
                self.assertNotIn(gone, filed)
            after = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})["doc"]
            self.assertNotIn("health_diff", after["meta"])
            self.assertEqual(section(after, "health")["data"]["flag"], "On track")      # the flag difference is still readable


class ClientBrowser(LiveBrowserCase):
    """The view in a real browser, over the same fixture."""

    @classmethod
    def load(cls, v):
        R.populate(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": R.NOW, "CREAITE_NO_LAUNCH": "1"}

    def api(self, path, body):
        return post(self.base, self.token(), path, body)

    def words(self, selector, without=".crnot"):
        """What a part of the page says: its text and the words in its text boxes (a textarea's value isn't innerText), leaving out
        `without` (the "Not in this report" lists: creaite's own notes to Alan, which name internal items on purpose and are never
        part of the report or an export)."""
        return self.b.eval(f"""(e=>{{ e=e.cloneNode(true); if({json.dumps(without)}) e.querySelectorAll({json.dumps(without)}).forEach(x=>x.remove());
          const live=[...document.querySelector({json.dumps(selector)}).querySelectorAll('textarea')].map(t=>t.value);
          return e.innerText+' '+live.join(' '); }})(document.querySelector({json.dumps(selector)}))""")

    def token(self):
        return self.b.eval("D.token")

    def open_view(self, week="2026-10-09"):
        self.b.eval(f"go('clientreport',{{code:'ABC',week:'{week}'}})")
        self.b.wait("document.querySelector('#v-clientreport .wr-health')", 20)

    def approve_internal(self, summary="The internal summary, not for the client."):
        doc = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})["doc"]
        section(doc, "health")["text"] = "UAT start slipped two weeks."
        section(doc, "summary")["text"] = summary
        self.assertTrue(self.api("/api/report/save", {"doc": doc, "base_version": 0})["ok"])
        return doc

    def test_opens_with_the_clients_own_words_and_none_of_the_internal_ones(self):
        self.open_view()
        page = self.words("#v-clientreport .page")
        self.assertIn("Test licences are not yet ordered.", page)
        for internal in ("ABC-005", "Vendor exits the market", "Absorb the phase one overrun", "Confirm tester names"):
            self.assertNotIn(internal, page)
        self.assertEqual(self.b.eval("document.title.startsWith('creaite')"), True)
        self.assertEqual(self.b.eval("location.hash.startsWith('#client-report=ABC/2026-10-09/')"), True)

    def test_client_health_needs_a_reason_and_match_internal_health_takes_the_internal_flag(self):
        self.open_view()
        flag = "document.querySelector('.crflag')"
        change = "document.querySelector('[data-crflag]')"
        self.b.click("[data-crflag]")
        self.b.wait("document.querySelector('.crpop')")
        self.assertTrue(self.b.eval("document.activeElement && document.activeElement.closest('.crpop')!==null"))
        self.b.click("[data-crpick='On track']")
        self.assertTrue(self.b.eval("document.querySelector('[data-crhsave]').disabled"), "a differing flag needs a reason")
        self.b.eval("(()=>{ const t=document.getElementById('crWhy'); t.value='Testing is on plan for the client.'; t.dispatchEvent(new Event('input',{bubbles:true})); })()")
        self.b.click("[data-crhsave]")
        self.assertEqual(self.b.eval(f"{flag}.textContent"), "ON TRACK")
        self.assertTrue(self.b.eval("!!document.querySelector('[data-crdif]')"), "the page says it differs from the internal health")
        self.b.click("[data-crflag]")
        self.b.wait("document.querySelector('.crpop')")
        self.b.key("Escape")                                                           # Esc closes it, focus back on the flag
        self.b.wait("!document.querySelector('.crpop')")
        self.assertTrue(self.b.eval(f"document.activeElement === {change}"))
        self.b.click("[data-crflag]")
        self.b.click("[data-crmatchhealth]")
        internal = self.b.eval("(()=>{ const m=document.querySelector('[data-crdif]'); return m?m.textContent:'' })()")
        self.assertEqual(internal, "", "matching internal health clears the difference")

    def test_an_eye_hides_a_row_and_match_internal_copies_a_section(self):
        self.approve_internal()
        self.open_view()
        self.b.click("#v-clientreport section[data-id=risks] .rs-eye")
        self.assertTrue(self.b.eval("!!document.querySelector('#v-clientreport section[data-id=risks] tr.hidrow')"))
        self.assertIn("Showing 0 of 1", self.b.eval("document.querySelector('#v-clientreport section[data-id=risks] .wr-count').textContent"))
        self.b.click("#v-clientreport section[data-id=risks] .rs-eye")                           # back: cells rebuilt from the client item
        self.assertIn("Test licences are not yet ordered.", self.words("#v-clientreport section[data-id=risks]"))
        self.assertEqual(self.b.eval("document.querySelector('[data-match=\"summary\"] .crmstate').textContent"), "Edited for the client")
        self.b.click("[data-matchone='summary']")
        self.assertEqual(self.b.eval("document.querySelector('[data-match=\"summary\"] .crmstate').textContent"), "Matching internal")
        self.assertEqual(self.b.eval("document.querySelector('section[data-id=\"summary\"] .wr-rich').innerText.trim()"),
                         "The internal summary, not for the client.")

    def test_not_in_this_report_names_what_is_left_out_with_a_way_to_change_it(self):
        self.open_view()
        self.b.wait("document.querySelector('[data-crnot=\"risks\"]')", 15)
        self.assertEqual(self.b.eval("document.querySelector('[data-crleft=\"ABC-005\"] [data-crvisible]')!==null"), True)
        self.assertIn("not client-visible", self.b.eval("document.querySelector('[data-crleft=\"ABC-005\"]').innerText").lower())
        self.api("/api/report/check", {"doc": self.api("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})["doc"]})

    def test_side_by_side_shows_the_internal_page_read_only(self):
        self.approve_internal()
        self.open_view()
        self.b.click("[data-crmode='side']")
        self.b.wait("document.querySelectorAll('#v-clientreport .sheet-pair > .sheet-fit').length===2")
        left = "document.querySelector('#v-clientreport .sheet-pair > .sheet-fit')"
        self.assertIn("ABC-005", self.words("#v-clientreport .sheet-pair > .sheet-fit"))                    # the internal page has its own
        self.assertNotIn("ABC-005", self.words("#v-clientreport .sheet-pair > .sheet-fit + .sheet-fit"))
        self.assertTrue(self.b.eval(f"{left}.querySelectorAll('.wr-rich').length>0 && {left}.querySelectorAll('[contenteditable=true],textarea,.wr-edit').length===0"), "the internal page is read only")
        # the sheet's Match internal (partner.match) is the client-safe match: the summary comes over, never an internal row
        self.b.eval("document.querySelectorAll('#v-clientreport .sheet-pair > .sheet-fit')[1].querySelector('section[data-id=\"summary\"] .sheet-match .linkbtn').click()")
        self.b.wait("document.querySelectorAll('#v-clientreport .sheet-pair > .sheet-fit')[1].querySelector('section[data-id=\"summary\"] .wr-rich')?.innerText.includes('The internal summary')", 10)
        self.assertEqual(self.b.eval("document.querySelectorAll('#v-clientreport .sheet-pair > .sheet-fit')[1].querySelector('section[data-id=\"summary\"] .wr-rich').innerText.trim()"),
                         "The internal summary, not for the client.")
        self.b.eval("[...document.querySelectorAll('#v-clientreport .sheet-bar .btn')].find(x=>/Match internal for every section/.test(x.textContent)).click()")
        self.assertNotIn("ABC-005", self.words("#v-clientreport .sheet-pair > .sheet-fit + .sheet-fit"))

    def test_export_waits_for_the_internal_week_and_the_check_runs_before_every_export(self):
        self.approve_internal()
        self.open_view()
        self.assertTrue(self.b.eval("document.querySelector('[data-crcheck]').disabled"))
        self.assertTrue(self.b.eval("document.querySelector('[data-crapprove]').disabled"))
        a = self.api("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertTrue(a["ok"], a)
        self.open_view()
        self.b.wait("document.querySelector('[data-crcheck]:not([disabled])')", 15)     # the reload after the approval has landed
        self.b.eval("(()=>{ window.__calls=[]; const f=window.fetch; window.fetch=(u,o)=>{ window.__calls.push(String(u)); return f(u,o); }; })()")
        self.b.click("[data-crcheck]")
        self.b.wait("document.querySelector('#crLeftDlg[open] [data-crleft-list]')", 15)
        text = self.b.eval("document.querySelector('#crLeftDlg').innerText")
        self.assertIn("ABC-005 (not client-visible)", text)
        self.assertIn("Internal notes and sources", text)
        self.assertEqual(self.b.eval("window.__calls.filter(u=>u.endsWith('/api/report/check')).length>0"), True)
        self.b.click("[data-crexport='html']")
        self.b.wait("!document.querySelector('#crLeftDlg').open", 30)
        calls = self.b.eval("window.__calls")
        self.assertLess([i for i, u in enumerate(calls) if u.endswith('/api/report/check')][0],
                        [i for i, u in enumerate(calls) if u.endswith('/api/report/export')][0], "the check came first")

    @unittest.skipUnless(os.environ.get("CREAITE_SHOTS"), "set CREAITE_SHOTS=<folder> for screenshots")
    def test_zz_screenshots(self):
        out = Path(os.environ["CREAITE_SHOTS"])
        out.mkdir(parents=True, exist_ok=True)
        self.approve_internal("Testing is on plan; one risk is being watched.")
        self.api("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.open_view()
        self.b.wait("document.querySelector('[data-crnot]')", 15)
        for w, h in ((1400, 1000), (900, 900)):
            self.b.resize(w, h)
            for theme in ("light", "dark"):
                self.b.eval(f"document.documentElement.setAttribute('data-theme','{theme}')")
                self.b.pump(0.4)
                self.b.screenshot(str(out / f"client-{w}-{theme}.png"))
                self.b.eval("document.querySelector('#v-clientreport .sheet-scroll').scrollTop=0")
                if w == 1400:   # the other views once, at the desktop width
                    self.b.click("[data-crmode='side']")
                    self.b.pump(0.5)
                    self.b.screenshot(str(out / f"side-{w}-{theme}.png"))
                    self.b.click("[data-crmode='client']")
                    self.b.click("[data-crcheck]")
                    self.b.wait("document.querySelector('#crLeftDlg[open] [data-crleft-list]')", 15)
                    self.b.pump(0.3)
                    self.b.screenshot(str(out / f"leftout-{w}-{theme}.png"))
                    self.b.key("Escape")
                    self.b.pump(0.2)
                    self.b.click("[data-crflag]")
                    self.b.pump(0.3)
                    self.b.screenshot(str(out / f"health-{w}-{theme}.png"))
                    self.b.key("Escape")
        self.assertTrue(any(out.glob("client-*.png")))


# #123: the stand-in Claude for the AI bar: it keeps each prompt and its command line beside itself and answers with the selected
# text plus an item ID that isn't client-visible (ABC-A-004), so the reply check has something to drop. Never a real model call.
AI_FAKE = r'''#!/usr/bin/env python3
import json, re, sys
args = sys.argv[1:]
p = args[args.index("--") + 1] if "--" in args else args[args.index("-p") + 1]
open(__file__ + ".prompt", "w", encoding="utf-8").write(p)
open(__file__ + ".argv.json", "w", encoding="utf-8").write(json.dumps(args))
m = re.search(r"<<<TEXT\n(.*?)\nTEXT>>>", p, re.S)
reply = "<<<SUGGESTION\n" + (m.group(1) if m else "") + " See ABC-A-004.\nSUGGESTION>>>"
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-c"})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-c"})
'''


class ClientSheetAi(LiveBrowserCase):
    """#123: the client sheet's AI bar uses the client place. What reaches Claude (the stand-in keeps it) has only the items a
    client report may show and no people or health; a suggestion that brings in an internal item is dropped on the page. The
    internal weekly sheet, same selection and same reply, is the control."""
    REASON = "ZEBRAINTERNAL vendor is failing to deliver the build on time"
    open_view = ClientBrowser.open_view

    @classmethod
    def load(cls, v):
        import sqlite3
        from contextlib import closing
        R.populate(v)
        with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:          # a test vault: set directly
            con.execute("UPDATE projects SET health = 'Off track', health_reason = ? WHERE code = 'ABC'", (cls.REASON,))
            con.commit()
        cls.fake = v.root / "fake_claude.py"
        cls.fake.write_text(AI_FAKE)
        cls.fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": R.NOW, "CREAITE_NO_LAUNCH": "1", "CREAITE_CLAUDE": str(cls.fake)}

    def select_in(self, view):
        """Open the Summary's editor in `view`, give it words, and select them all, as a person would."""
        b = self.b
        sec = f"#{view} section[data-id='summary']"
        b.wait(f"document.querySelector({json.dumps(sec)})", 20)
        if not b.eval(f"!!document.querySelector({json.dumps(sec + ' .ProseMirror')})"):
            b.click(sec + " .wr-rich")
        b.wait(f"document.querySelector({json.dumps(sec + ' .ProseMirror')})")
        b.click(sec + " .ProseMirror")
        b.type(" Testing could start late.")
        b.key("a", 4)
        b.pump(0.3)
        b.wait("document.querySelector('#aiLayer .aispark')")
        b.click("#aiLayer .aispark")
        b.wait("document.querySelector('#aiLayer .aibar')")

    def suggest(self):
        """Pick Polish on the bar; (what the page shows, the prompt Claude got, the request the page sent)."""
        b = self.b
        b.eval("""window.__aiBodies = []; if (!window.__aiSpy) { window.__aiSpy = 1; const f = window.fetch;
          window.fetch = (u, o) => { if (String(u).includes('/api/edit/ai')) window.__aiBodies.push(JSON.parse(o.body)); return f(u, o); }; } true""")
        b.click("#aiLayer .aibar button[aria-haspopup]")
        b.wait("document.querySelector('#aiLayer [role=menu]')")
        b.click("#aiLayer [role=menu] [data-ai=polish]")
        b.wait("document.querySelector('#aiLayer .aisug .aitext')||document.querySelector('#aiLayer .aisug [role=alert]')", 30)
        shown = b.eval("document.querySelector('#aiLayer .aisug').textContent")
        prompt = Path(str(self.fake) + ".prompt").read_text(encoding="utf-8")
        body = b.eval("window.__aiBodies[0]")
        b.key("Escape")
        b.eval("aiBar.value = null; aiSug.value = null; true")
        return shown, prompt.replace("(such as ABC-A-003)", ""), body

    def test_the_client_sheet_sends_only_client_safe_facts_and_drops_an_internal_reply(self):
        self.open_view()
        self.select_in("v-clientreport")
        shown, prompt, body = self.suggest()
        self.assertEqual(body["place"], "client")
        self.assertEqual({k: body["document"][k] for k in ("kind", "code", "week_ending")},
                         {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertEqual(sorted(body["document"]), ["client", "code", "kind", "week_ending"])
        self.assertEqual(sorted(body), ["code", "document", "instruction", "option", "place", "run", "text"])
        self.assertIn("Its open item IDs: ABC-A-002, ABC-A-003, ABC-006\n", prompt)
        self.assertIn("Its people: none listed", prompt)
        for x in ("ABC-A-001", "ABC-A-004", "ABC-005", "ABC-M-001", "Omar Ali", "Alan Carter", "Jane Doe", "ZEBRAINTERNAL",
                  "Off track"):
            self.assertNotIn(x, prompt)
        self.assertIn("isn't client-safe", shown)
        self.assertNotIn("ABC-A-004", shown)
        args = json.loads(Path(str(self.fake) + ".argv.json").read_text())
        self.assertEqual(args[args.index("--tools") + 1], "")                       # the edit-ai run is unchanged: no tools
        self.assertIn("--strict-mcp-config", args)

    DOC = {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "client": ""}

    def raw(self, body):
        """POST /api/edit/ai from the page with `body`; (status, the answer's text)."""
        return self.b.eval("""(async()=>{ const r=await fetch('/api/edit/ai',{method:'POST',headers:{'Content-Type':'application/json','X-Creaite-Token':D.token},
            body:JSON.stringify(%s)}); return [r.status, await r.text()]; })()""" % json.dumps(body))

    def edit_ai(self, place, document=None):
        """POST /api/edit/ai from the page, as the bar does, and read its stream: the "draft" event."""
        body = {"option": "polish", "text": "Testing could start late.", "code": "ABC", "place": place}
        if document is not None:
            body["document"] = document
        Path(str(self.fake) + ".prompt").unlink(missing_ok=True)
        got = self.raw(body)[1]
        events = [json.loads(ln[6:]) for ln in got.splitlines() if ln.startswith("data: ")]
        run = next((e.get("run") for e in events if e.get("type") == "done"), None)
        if run:
            self.b.eval(f"api('/api/ask/ack',{{run:{json.dumps(run)}}})")
        return next(e for e in events if e["type"] == "draft"), Path(str(self.fake) + ".prompt").read_text(encoding="utf-8")

    def test_the_route_keeps_the_internal_place_as_it_was_and_drops_the_reply_only_in_the_client_place(self):
        """Control, on the route itself: the internal sheet's place ("report") still sends every open item and owner, and keeps the
        same reply that the client place drops."""
        self.open_view()
        draft, prompt = self.edit_ai("report")
        for x in ("ABC-A-001", "ABC-A-004", "ABC-005", "Omar Ali", "Alan Carter"):
            self.assertIn(x, prompt)
        self.assertEqual(draft["text"], "Testing could start late. See ABC-A-004.")
        draft, prompt = self.edit_ai("client", self.DOC)
        self.assertNotIn("ABC-A-004", prompt.replace("(such as ABC-A-003)", ""))
        self.assertEqual(draft["text"], "")
        self.assertIn("isn't client-safe", draft["message"])

    def test_the_server_binds_the_place_from_the_document_and_fails_closed(self):
        """#123 (Jarvis): a request that names the client report gets the client place whatever place it claims; the client place
        with no document, or a document that isn't this project's client report, is refused before Claude runs; and any key the
        route doesn't know is a 400."""
        self.open_view()
        draft, prompt = self.edit_ai("report", self.DOC)                             # a tampered page claims the internal place
        p = prompt.replace("(such as ABC-A-003)", "")
        self.assertIn("Its people: none listed", p)
        for x in ("ABC-A-001", "ABC-A-004", "ABC-005", "Omar Ali", "Alan Carter"):
            self.assertNotIn(x, p)
        self.assertEqual(draft["text"], "")                                          # and its reply is checked as a client one
        fake = Path(str(self.fake) + ".prompt")
        base = {"option": "polish", "text": "Testing could start late.", "code": "ABC"}
        for body in ({**base, "place": "client"}, {**base, "place": "client", "document": {}},
                     {**base, "place": "report", "document": {**self.DOC, "kind": "weekly"}},
                     {**base, "place": "client", "document": {**self.DOC, "code": "DEF"}},
                     {**base, "place": "client", "document": {**self.DOC, "week_ending": "not-a-date"}}):
            fake.unlink(missing_ok=True)
            status, text = self.raw(body)
            self.assertEqual(status, 200, body)
            self.assertFalse(json.loads(text)["ok"], body)
            self.assertFalse(fake.exists(), body)                                    # Claude never ran
        for body in ({**base, "place": "report", "audience": "internal"},           # a key the route doesn't know
                     {**base, "place": "report", "document": {**self.DOC, "audience": "internal"}},
                     {**base, "place": "report", "document": "client"},
                     {**base, "place": "report", "document": {**self.DOC, "client": 3}}):
            fake.unlink(missing_ok=True)
            status, text = self.raw(body)
            self.assertEqual(status, 400, body)
            self.assertFalse(fake.exists(), body)


class EditAiRouteKeys(unittest.TestCase):
    """#123: /api/edit/ai's request whitelist (live_server.edit_ai_request): known keys only, a document only as a small object of
    strings, sizes capped; anything else is None, which the route answers with a 400 before anything runs."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        import live_server
        cls.ls = live_server

    def test_the_whitelist(self):
        f = self.ls.edit_ai_request
        base = {"option": "polish", "text": "x", "code": "ABC", "place": "report"}
        self.assertEqual(f(base), {**base, "instruction": ""})
        doc = {"kind": "client", "code": "ABC", "week_ending": "2026-10-09", "client": "c" * 500}
        got = f({**base, "document": doc, "run": "d-abc123"})
        self.assertEqual(got["document"], {**doc, "client": "c" * 120})
        self.assertNotIn("run", got)
        for bad in ({**base, "audience": "internal"}, {**base, "facts": []}, {**base, "document": []},
                    {**base, "document": {**doc, "audience": "client"}}, {**base, "document": {**doc, "code": None}}, "x", None):
            self.assertIsNone(f(bad), bad)

    def test_the_route_answers_400(self):
        sent = []

        class H:
            def send(self, status, body):
                sent.append((status, body))

        self.ls.edit_ai_route(H(), {"option": "polish", "text": "x", "code": "ABC", "place": "report", "extra": 1})
        self.assertEqual(sent[0][0], 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
