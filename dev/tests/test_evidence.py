"""BL-207: evidence on hover for the executive Current state.

Run: python3 dev/tests/test_evidence.py   (the browser half needs Google Chrome; skipped otherwise)
The facts sheet numbers its lines (F1, F2, …); a drafted Current state ends each sentence with the facts it rests on ({F3, F7});
the page takes the marks out, wraps each sentence, and the check route maps the IDs to rows and quotes. Claude is a stand-in that
prints a fixed, marked reply. The clock is fixed; the data is fictional.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_status_facts import FactsCase  # noqa: E402

NOW = "2026-10-09 13:00"

FAKE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
message = args[args.index("-p") + 1]
open(__file__ + ".prompt", "w", encoding="utf-8").write(message)
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-x"})
if message.startswith("Rewrite"):
    reply = "**Off track: UAT start slipped 14 days.** {F1}\n\n- Morale is excellent across the whole team this week. {}"
else:
    reply = ("**Off track: UAT start slipped 14 days.** {F1, F4}\n\n- **Risk.** Data access is delayed, so UAT slips. {F8}\n"
             "- **Ask.** Sara Example to book the UAT environment by 14-10-2026. {F12}\n"
             "- The team remains upbeat about the next phase overall. {}\n\nSOURCES:\n- ABC-003")
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-x"})
'''


def check(v, payload, *args):
    r = subprocess.run([sys.executable, str(v.root / "system/scripts/status_checks.py"), "check", "ABC", *args], input=json.dumps(payload),
                       cwd=v.root, capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": NOW})
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return json.loads(r.stdout)


class FactIds(FactsCase):
    """The facts sheet's IDs and the evidence they map to (plain code, no model)."""

    def test_every_line_has_an_id_in_order_and_the_text_shows_it(self):
        f = self.facts()
        ids = [ln["fid"] for p in f["parts"] for ln in p["lines"]]
        self.assertEqual(ids, [f"F{i}" for i in range(1, len(ids) + 1)])
        self.assertIn("- [F1] Health now:", f["text"])
        self.assertEqual(f, self.facts())                                    # deterministic: the check finds the same IDs

    def ids_for(self, f, start):
        return next(ln["fid"] for p in f["parts"] for ln in p["lines"] if ln["text"].startswith(start))

    def test_a_marked_claim_maps_to_its_rows_and_a_quoted_line(self):
        f = self.facts()
        blocker, numbers = self.ids_for(f, "Blocker: Client delivers"), self.ids_for(f, "Handling time is down 11%")
        out = check(self.v, {"draft": "x", "claims": [{"n": 1, "text": "The client's data extract holds UAT.", "ids": [blocker]},
                                                    {"n": 2, "text": "Handling time is down 11%.", "ids": [numbers]}]},
                    "--from", "2026-10-01", "--to", "2026-10-09")
        ev = out["evidence"]
        self.assertEqual([c["how"] for c in ev["claims"]], ["marked", "marked"])
        rows = {r["id"]: r for r in ev["facts"][blocker]["rows"]}
        dep = next(r for r in rows.values() if r["kind"] == "raid")
        self.assertEqual(set(rows), {dep["id"], "ABC-M-001"})
        self.assertEqual((dep["title"], dep["due"], dep["status"]), ("Client delivers the UAT data extract", "2026-11-10", "Open"))
        files = ev["facts"][numbers]["files"]
        self.assertEqual(files[0]["text"], "The pilot finished. Handling time is down 11% against an 8% target.")
        self.assertEqual(files[0]["line"], 3)
        self.assertTrue(files[0]["path"].endswith("minutes/2026-10-06 Steering.md"))
        self.assertNotIn("unsourced", {n["id"] for n in out["notes"]})

    def test_an_unsupported_sentence_is_flagged_and_an_unknown_id_is_not_a_source(self):
        out = check(self.v, {"draft": "x", "claims": [{"n": 1, "text": "Everyone loves the new colour scheme.", "ids": []},
                                                    {"n": 2, "text": "Something.", "ids": ["F999"]}]})
        self.assertEqual([c["how"] for c in out["evidence"]["claims"]], ["none", "none"])
        self.assertIn("No source found for 2 sentences", {n["id"]: n["note"] for n in out["notes"]}["unsourced"])

    def test_an_edited_sentence_loses_its_mark_and_is_rechecked_by_its_words(self):
        f = self.facts("--from", "2026-10-01", "--to", "2026-10-09")
        blocker = self.ids_for(f, "Blocker: Client delivers")
        out = check(self.v, {"draft": "x", "claims": [
            {"n": 1, "text": "The client delivers the UAT data extract late, due 10-11-2026.", "ids": [blocker], "edited": True},
            {"n": 2, "text": "Morale is wonderful.", "ids": [blocker], "edited": True}]}, "--from", "2026-10-01", "--to", "2026-10-09")
        c1, c2 = out["evidence"]["claims"]
        self.assertEqual(c1["how"], "rechecked")
        self.assertIn(blocker, c1["ids"])
        self.assertEqual((c2["how"], c2["ids"]), ("none", []))             # the old mark is not kept for an edited sentence

    def test_the_marks_never_reach_the_saved_text_and_a_client_sheet_has_only_client_sources(self):
        import status_checks
        md = "**At risk.** {F1, F3}\n\n- Data is late. {F8}\n- Keep going. {}\n"
        clean = status_checks.strip_marks(md)
        self.assertNotRegex(clean, r"\{|F\d")
        self.assertEqual(status_checks.split_claims(md), [("At risk.", ["F1", "F3"]), ("Data is late.", ["F8"]), ("Keep going.", [])])
        client = self.facts(audience="client")
        import sqlite3
        with sqlite3.connect(self.v.root / "system/tracker.db") as con:
            visible = {r[0] for t in ("actions", "raid", "decisions") for r in con.execute(f"SELECT id FROM {t} WHERE client_visible = 1")}
            internal = {r[0] for t in ("actions", "raid", "decisions") for r in con.execute(f"SELECT id FROM {t} WHERE client_visible = 0")}
        self.assertTrue(client["sources"] and set(client["sources"]) <= visible, client["sources"])
        out = check(self.v, {"draft": "x", "claims": [{"n": 1, "text": "x", "ids": [ln["fid"] for p in client["parts"] for ln in p["lines"]]}]},
                    "--audience", "client")
        rows = {r["id"] for x in out["evidence"]["facts"].values() for r in x["rows"]}
        self.assertTrue(rows and rows <= visible and not rows & internal, rows)

    def test_the_prompts_ask_for_marks(self):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        for name in ("current-state-prompt.md", "current-state-rewrite-prompt.md"):
            text = (Path(__file__).resolve().parents[2] / "system/templates" / name).read_text(encoding="utf-8")
            self.assertIn("{{F3, F7}}", text)                                # doubled for .format
            self.assertEqual(text.format(code="ABC", name="n", start="s", end="e", context="c", note="", audience_rule="a",
                                         length="L", words=1, style="s", facts="f", text="t").count("{F3, F7}"), 1)


class EvidenceBrowser(LiveBrowserCase):
    shared_server = False

    @classmethod
    def load(cls, v):
        super().load(v)
        cls.fake = v.root / "fake_claude.py"
        cls.fake.write_text(FAKE)
        cls.fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake), "CREAITE_NOW": NOW}

    def draft(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit .curcard [data-gen]')")
        b.click("#v-cockpit .curcard [data-gen]")
        b.wait("document.getElementById('genDlg').open")
        b.click("#genGo")
        b.wait("document.querySelectorAll('#curEd .claim').length>0 && CURED.claims && Object.values(CURED.claims).every(c=>c.how)", 30)

    def states(self):
        return self.b.eval("Object.entries(CURED.claims).map(([n,c])=>[+n,claimState(c)])")

    def test_the_marks_become_claims_and_a_claim_opens_its_source(self):
        self.draft()
        b = self.b
        text = b.eval("document.getElementById('curEd').innerText")
        self.assertNotRegex(text, r"\{|F\d")                                 # the marks are gone
        self.assertNotIn("{", b.eval("htmlToMd(document.getElementById('curEd'))"))
        self.assertEqual(self.states(), [[1, "ok"], [2, "ok"], [3, "ok"], [4, "none"]])
        self.assertIn("dotted", b.eval("getComputedStyle(document.querySelector('#curEd .claim[data-c=\"1\"]')).textDecorationStyle"))
        self.assertIn("dashed", b.eval("getComputedStyle(document.querySelector('#curEd .claim[data-c=\"4\"]')).textDecorationStyle"))
        self.assertIn("No source", b.eval("getComputedStyle(document.querySelector('#curEd .claim[data-c=\"4\"]'),'::before').content"))
        self.assertEqual(b.eval("document.querySelector('#curEd .claim[data-c=\"2\"]').getAttribute('aria-description')"), "Source: 1 row")
        b.click('#curEd .claim[data-c="2"]')
        b.wait("!document.getElementById('evPanel').hidden")
        panel = b.eval("document.getElementById('evPanel').innerText")
        self.assertIn("Data access is delayed", panel)
        self.assertIn("ABC-003", panel)
        self.assertIn("Internal", panel)
        self.assertIn("Every claim in this paragraph has a source.", panel)
        self.assertTrue(b.eval("!!document.querySelector('#evPanel [data-open=\"raid:ABC-003\"]')"))
        self.assertEqual(b.errors, [])

    def test_tab_moves_between_claims_and_esc_closes_only_the_panel(self):
        self.draft()
        b = self.b
        b.click('#curEd .claim[data-c="1"]')
        b.wait("EV && EV.n===1")
        b.key("Tab")
        self.assertEqual(b.eval("EV.n"), 2)
        b.key("Tab", 8)
        b.key("Tab", 8)
        self.assertEqual(b.eval("EV.n"), 4)                                  # wraps round
        self.assertIn("No source found for this sentence", b.eval("document.getElementById('evPanel').innerText"))
        b.key("Escape")
        self.assertTrue(b.eval("document.getElementById('evPanel').hidden"))
        self.assertTrue(b.eval("!!document.getElementById('curEd')"))       # the editor is still open

    def test_save_waits_for_a_sentence_with_no_source_then_keep_with_a_note_saves_plain_text(self):
        self.draft()
        b = self.b
        b.eval("document.getElementById('snackT').textContent=''")
        b.click('[data-cure="save"]')
        b.wait("/no source/.test(document.getElementById('snackT').textContent)")
        self.assertEqual(b.eval("EV.n"), 4)
        self.assertTrue(b.eval("!!document.getElementById('curEd')"))       # not saved
        b.click("#evNote")
        b.type("Alan's own view")
        b.click('#evPanel [data-evkeep="one"]')
        self.assertEqual(self.states()[3], [4, "kept"])
        self.assertIn("Alan's own view", b.eval("document.getElementById('evPanel').innerText"))
        b.eval("document.getElementById('snackT').textContent=''")
        b.click('[data-cure="save"]')
        b.wait("/saved|applied|staged|Saving/i.test(document.getElementById('snackT').textContent) || !document.getElementById('curEd')", 15)
        b.wait("!document.getElementById('curEd')", 15)
        memory = (self.v.root / "projects").rglob("CLAUDE.md")
        text = next(p for p in memory if "ABC" in str(p) or "Example" in str(p)).read_text()
        staged = " ".join(op.get("content", "") for p in (self.v.root / "system/staging").rglob("proposed-*.json")
                          for op in (json.loads(p.read_text()).get("file_changes") or {}).get("file_ops", []))
        self.assertIn("The team remains upbeat about the next phase overall.", text)
        for body in (text, staged):
            self.assertNotRegex(body, r"\{F\d| \{\}")

    def keep_and_save(self):
        b = self.b
        b.click('[data-cure="save"]')
        b.wait("EV && EV.n===4")
        b.click('#evPanel [data-evkeep="one"]')
        b.click('[data-cure="save"]')
        b.wait("!document.getElementById('curEd')", 15)
        evf = self.v.root / "system/staging/evidence/ABC-current.json"
        for _ in range(100):
            if evf.exists():
                break
            b.pump(0.1)
        return evf

    def test_the_links_survive_save_and_a_reload_and_an_edited_sentence_loses_its_link(self):
        self.draft()
        b = self.b
        evf = self.keep_and_save()
        data = json.loads(evf.read_text())
        self.assertEqual(len(data["sentences"]), 4)                        # three sourced, one kept with a note
        raw = evf.read_text()
        self.assertNotIn("UAT slips.", raw.replace("Data access delayed → UAT slips", ""))   # hashes, not the sentences
        self.assertNotIn("upbeat", raw)
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelectorAll('#curText .claim').length>=4", 15)
        self.assertEqual(b.eval("Object.values(CURRD.set).map(claimState)"), ["ok", "ok", "ok", "kept"])
        self.assertEqual(b.eval("document.querySelector('#curText .claim[data-c=\"2\"]').getAttribute('aria-description')"), "Source: 1 row")
        b.click('#curText .claim[data-c="2"]')
        b.wait("!document.getElementById('evPanel').hidden && document.querySelector('#evPanel .evqsrc')", 15)
        self.assertIn("ABC-003", b.eval("document.getElementById('evPanel').innerText"))
        b.key("Escape")
        # reopen the editor: the links come with it; an edit drops one
        b.click("#v-cockpit .curcard [data-edcur]")
        b.wait("document.getElementById('curEd') && CURED.claims && Object.keys(CURED.claims).length===4")
        b.eval("""(()=>{ const s=document.querySelector('#curEd .claim[data-c="2"]'), w=document.createTreeWalker(s,NodeFilter.SHOW_TEXT); let t, last; while((t=w.nextNode())) last=t;
          const r=document.createRange(); r.setStart(last,last.nodeValue.length); r.collapse(true); const sel=getSelection(); sel.removeAllRanges(); sel.addRange(r); document.getElementById('curEd').focus(); })()""")
        b.type(" Badly")
        b.wait("CURED.claims[2].edited")
        b.click('[data-cure="save"]')
        b.wait("!document.getElementById('curEd')", 15)
        b.wait("Object.keys((P.find(p=>p.code==='ABC')||{}).ev||{}).length===3", 15)
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelectorAll('#curText .claim').length>=3", 15)
        self.assertEqual(len(json.loads(evf.read_text())["sentences"]), 3)
        self.assertNotIn("data-c", b.eval("[...document.querySelectorAll('#curText li')].find(l=>l.textContent.includes('Badly')).innerHTML"))
        self.assertEqual(b.errors, [])

    def test_an_edited_sentence_loses_its_mark_until_check_again(self):
        self.draft()
        b = self.b
        b.eval("""(()=>{ const s=document.querySelector('#curEd .claim[data-c="3"]'); const t=[...s.childNodes].find(n=>n.nodeType===3)||s.lastChild.firstChild||s.firstChild;
          const r=document.createRange(); const node=t.nodeType===3?t:t.firstChild; r.setStart(node,node.nodeValue.length); r.collapse(true);
          const sel=getSelection(); sel.removeAllRanges(); sel.addRange(r); document.getElementById('curEd').focus(); })()""")
        b.type(" soon")
        b.wait("CURED.claims[3].edited")
        self.assertEqual(self.states()[2], [3, "edited"])
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#curEd .claim[data-c=\"3\"]')).textDecorationLine"), "none")
        b.click('#curEd .claim[data-c="3"]')
        b.wait("!document.getElementById('evPanel').hidden")
        self.assertIn("You edited this sentence", b.eval("document.getElementById('evPanel').innerText"))
        b.click('#evPanel [data-chk]')
        b.wait("!CURED.claims[3].edited", 20)
        self.assertEqual(b.eval("CURED.claims[3].how"), "rechecked")
        self.assertEqual(self.states()[2], [3, "ok"])

    def test_the_executive_version_marks_its_own_claims(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit .curcard [data-edcur]')")
        b.click("#v-cockpit .curcard [data-edcur]")
        b.wait("document.getElementById('curEd')")
        b.eval("document.getElementById('curEd').innerHTML='<p>UAT is 14 days late.</p>'")
        b.click("[data-exec]")
        b.wait("document.querySelectorAll('#genRewrite .rwbody .claim').length===2 && CURED.rewrite.claims && Object.values(CURED.rewrite.claims).every(c=>c.how)", 30)
        self.assertNotIn("{", b.eval("document.querySelector('#genRewrite .rwbody').innerText"))
        self.assertEqual(b.eval("Object.values(CURED.rewrite.claims).map(claimState)"), ["ok", "none"])
        b.eval("document.querySelector('#genRewrite .rwbody .claim[data-c=\"1\"]').focus()")
        b.wait("EV && EV.which==='rw' && !document.getElementById('evPanel').hidden")
        b.click("[data-rw=use]")
        b.wait("CURED.claims && Object.keys(CURED.claims).length===2")
        self.assertNotIn("{", b.eval("document.getElementById('curEd').innerText"))


if __name__ == "__main__":
    unittest.main()
