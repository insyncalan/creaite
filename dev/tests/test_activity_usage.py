"""#238 Activity › Usage (v2.5.1): a third tab beside Changes and Quality. Read only, counts only.

Fixture: usage_fixture.py (fictional; its sums are worked by hand there). The page needs no route: the figures are in the page's
own data (D.usage, built from usage_report.py). Where the live server has GET /api/usage the page refreshes from it
(UsageRoute, which applies dev/proposals/usage-monitor/live_server.diff to the throwaway vault's copy of live_server.py).

Run: python3 dev/tests/test_activity_usage.py   (needs Google Chrome; skipped otherwise). Desktop width only (1400 and 900).
"""
import json
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import usage_fixture as fx  # noqa: E402
from live_browser import TEST_PALETTES_JS, LiveBrowserCase  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PROPOSAL = REPO / "dev" / "proposals" / "usage-monitor" / "live_server.diff"

PANEL = "document.querySelector('#actUsage')"
TEXT = f"({PANEL}.innerText||'').replace(/\\s+/g,' ')"


def poisoned_runs():
    """The fixture's runs with text where text must never be read, plus one old line that is all text."""
    rows = [dict(r) for r in fx.RUNS]
    rows[0].update(label=fx.POISON, model=fx.POISON, note=fx.POISON, prompt=fx.POISON)       # fields the page must never read
    rows.append(dict(fx.run("2026-08-01T10:00:00", "ask", 9.0, 9999, skills=[fx.POISON]), kind=fx.POISON, label=fx.POISON))
    return rows


def poisoned_context():
    rows = [dict(r) for r in fx.CONTEXT]
    rows[0]["note"] = fx.POISON
    rows.append({"date": "2026-10-19", "file": fx.POISON, "bytes": 1, "tokens": 1})
    rows.append({"date": "2026-10-19", "file": "rules", "bytes": fx.POISON, "tokens": 1})
    return rows


class UsageBase(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000
    runs = staticmethod(poisoned_runs)
    context = staticmethod(poisoned_context)

    @classmethod
    def load(cls, v):
        super().load(v)
        if cls.runs():
            fx.write_jsonl(v.root / "system" / "staging" / "run-usage.jsonl", cls.runs())
        if cls.context():
            fx.write_jsonl(v.root / "system" / "staging" / "context-size.jsonl", cls.context())

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": fx.NOW}

    def open_usage(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("!!document.querySelector('#actTabU')")
        b.click("#actTabU")
        b.wait(f"!{PANEL}.hidden && {TEXT}.length > 20")
        return b


class UsageTab(UsageBase):
    def test_usage_is_the_third_tab_and_shows_only_its_panel(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("!!document.querySelector('#actTabU')")
        self.assertEqual(b.eval("[...document.querySelectorAll('#actTabsHost [role=tab]')].map(t=>t.textContent.trim())"),
                         ["Changes", "Quality", "Usage"])
        self.assertTrue(b.eval(f"{PANEL}.hidden"))
        b.click("#actTabU")
        b.wait(f"!{PANEL}.hidden")
        self.assertEqual(b.eval("document.querySelector('#actTabU').getAttribute('aria-selected')"), "true")
        self.assertEqual(b.eval("document.querySelector('#actTabU').getAttribute('aria-controls')"), "actUsage")
        self.assertTrue(b.eval("document.querySelector('#actQuality').hidden"))
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#actTbl')).display"), "none")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#actTools')).display"), "none")
        b.click("#actTabCh")                                        # and back: the list returns, the panel goes
        b.wait(f"{PANEL}.hidden")
        self.assertNotEqual(b.eval("getComputedStyle(document.querySelector('#actTbl')).display"), "none")

    def test_cards_show_cost_runs_start_load_and_average_cost_with_the_change(self):
        t = self.open_usage().eval(TEXT)
        for want in ("$6.50", "Cost this week", "+117% on last week", "Runs this week", "+100% on last week",
                     "21,000", "Tokens a run loads before it starts", "+1,000 on last week",
                     "$1.63", "Cost of an average run", "+8% on last week"):
            self.assertIn(want, t)
        cards = self.b.eval("[...document.querySelectorAll('#actUsage .ucard .v')].map(e=>e.textContent)")
        self.assertEqual(cards, ["$6.50", "4", "21,000", "$1.63"])

    def test_chart_has_a_bar_a_day_for_fourteen_days_and_a_start_load_line(self):
        b = self.open_usage()
        bars = b.eval("[...document.querySelectorAll('#actUsage svg rect.ubar')].map(r=>r.querySelector('title').textContent)")
        self.assertEqual(len(bars), 14)
        self.assertEqual(bars[0], "06-10-2026: $0.00, 0 runs")
        self.assertEqual(bars[-1], "19-10-2026: $3.00, 2 runs")
        self.assertEqual(b.eval("document.querySelectorAll('#actUsage svg polyline.uline').length"), 1)
        self.assertIn("Cost per day", b.eval("document.querySelector('#actUsage svg').getAttribute('aria-label')"))
        self.assertGreater(b.eval("[...document.querySelectorAll('#actUsage svg rect.ubar')].filter(r=>+r.getAttribute('height')>0).length"), 3)
        h = b.eval("[...document.querySelectorAll('#actUsage svg rect.ubar')].map(r=>+r.getAttribute('height'))")
        self.assertEqual(h.index(max(h)), 11)               # 17-10 ($3.00 sweep) and 19-10 ($3.00 two asks) tie: the first is 11
        self.assertEqual(h[11], h[13])

    def test_by_kind_table(self):
        rows = self.open_usage().eval("[...document.querySelectorAll('#actUsage table[aria-label=\"By kind of run\"] tbody tr')]"
                                      ".map(tr=>[...tr.children].map(c=>c.textContent))")
        self.assertEqual(rows, [["ask creaite", "3", "20,667", "20,000", "$5.00", "53%"],
                                ["Sweep", "2", "23,000", "20,500", "$4.00", "42%"],
                                ["Alert check", "1", "21,000", "21,000", "$0.50", "5%"]])

    def test_what_every_run_loads_with_the_thirty_day_change(self):
        rows = self.open_usage().eval("[...document.querySelectorAll('#actUsage table[aria-label=\"What every run loads\"] tbody tr')]"
                                      ".map(tr=>[...tr.children].map(c=>c.textContent))")
        self.assertEqual(rows, [["Rules (creaite-rules.md)", "53 KB", "13,250", "+3 KB since 19-09-2026"],
                                ["Your CLAUDE.md", "0.7 KB", "175", "no change"],
                                ["Project memory and registers", "5 KB", "1,250", "no earlier measure yet"],
                                ["Skill names and descriptions", "9 KB", "2,250", "no earlier measure yet"]])

    def test_tokens_are_said_to_be_estimates(self):
        t = self.open_usage().eval(TEXT)
        self.assertRegex(t, r"estimate[sd]? \(bytes ÷ 4\)")
        self.assertIn("Counts only", t)

    def test_skills_with_runs_cost_and_last_used(self):
        rows = self.open_usage().eval("[...document.querySelectorAll('#actUsage table[aria-label=\"Skills\"] tbody tr')]"
                                      ".map(tr=>[...tr.children].map(c=>c.textContent))")
        by = {r[0]: r for r in rows}
        self.assertEqual(by["cx-minutes"], ["cx-minutes", "1", "$2.00", "today"])
        self.assertEqual(by["cx-sweep"], ["cx-sweep", "2", "$4.00", "2 days ago"])
        self.assertTrue(by["cx-steerco"][3].startswith("never in this period"), by["cx-steerco"])
        self.assertEqual(by["cx-steerco"][1:3], ["0", "$0.00"])
        self.assertNotIn("other", by)

    def test_text_in_the_files_never_reaches_the_page(self):
        b = self.open_usage()
        whole = b.eval("document.documentElement.outerHTML + ' ' + document.documentElement.innerText")
        for word in ("POISONED", "Jane Example", "confidential merger", "secret price"):
            self.assertNotIn(word, whole)
        d = json.dumps(b.eval("D.usage"))                    # nor into the data the page holds
        self.assertNotIn("POISONED", d)
        self.assertNotIn("Jane", d)

    def test_the_word_vip_is_nowhere_in_the_tab(self):
        """BL-288: nothing creaite shows says VIP (text, aria-labels, titles); the internal kind key stays `vip` in the jsonl."""
        b = self.open_usage()
        shown = b.eval(f"{PANEL}.innerText + ' ' + [...{PANEL}.querySelectorAll('[aria-label],[title]')].map(e=>(e.getAttribute('aria-label')||'')+' '+(e.getAttribute('title')||'')+' '+e.textContent).join(' ')")
        self.assertNotIn("vip", shown.lower())
        self.assertIn("Alert check", shown)

    def test_the_tab_is_read_only(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("!!document.querySelector('#actTabU')")
        b.eval("window.__calls=[]; const f=window.fetch; window.fetch=function(u,o){ window.__calls.push(((o&&o.method)||'GET')+' '+String(u).split('?')[0]); return f.apply(this,arguments); }; true")
        b.click("#actTabU")
        b.wait(f"!{PANEL}.hidden && {TEXT}.length > 20")
        b.eval("new Promise(r=>setTimeout(r,600))")
        calls = b.eval("window.__calls")
        writes = [c for c in calls if not c.startswith("GET ") and not any(p in c for p in ("/api/here", "/api/pulse", "/api/vip", "/api/ask/running"))]
        self.assertEqual(writes, [])                          # no POST, PUT or DELETE (the page's own polling excepted)
        self.assertEqual(b.eval(f"{PANEL}.querySelectorAll('button, input, select, textarea, a[href]').length"), 0)

    def test_fits_at_900_in_both_palettes_and_both_modes(self):
        b = self.open_usage()
        b.resize(900, 900)
        o = b.eval("""(()=>{ const out={};
          for(const pal of TEST_PALETTES) for(const mode of ["Light","Dark"]){ S.palette=pal; S.theme=mode; applyTheme();
            const p=document.querySelector('#actUsage'), bar=p.querySelector('rect.ubar'), line=p.querySelector('polyline.uline'), card=p.querySelector('.ucard');
            const cs=e=>getComputedStyle(e);
            out[pal+'|'+mode]={fill:cs(bar).fill, stroke:cs(line).stroke, card:cs(card).backgroundColor, ink:cs(card).color,
              over:document.documentElement.scrollWidth>innerWidth, wide:[...p.querySelectorAll('table')].some(t=>t.getBoundingClientRect().right>innerWidth)}; }
          return out; })()""".replace("TEST_PALETTES", TEST_PALETTES_JS))
        self.assertEqual(len(o), 4)
        for k, v in o.items():
            self.assertFalse(v["over"], k)
            self.assertFalse(v["wide"], k)
            self.assertNotIn(v["fill"], ("none", "rgba(0, 0, 0, 0)"), k)
            self.assertNotIn(v["stroke"], ("none", "rgba(0, 0, 0, 0)"), k)
            self.assertNotEqual(v["fill"], v["card"], k)
        self.assertNotEqual(o["creaite|Light"]["card"], o["creaite|Dark"]["card"])


class UsageEmpty(UsageBase):
    runs = staticmethod(lambda: [])
    context = staticmethod(lambda: [])

    def test_an_empty_record_says_no_runs_yet(self):
        t = self.open_usage().eval(TEXT)
        self.assertIn("No runs yet", t)
        self.assertEqual(self.b.eval(f"{PANEL}.querySelectorAll('.ucard, svg, table[aria-label=\"By kind of run\"]').length"), 0)
        self.assertIn("Not measured yet", t)                  # and no context record either
        self.assertNotIn("NaN", t)
        self.assertNotIn("undefined", t)


class UsageNoRuns(UsageBase):
    """Runs but no context record yet (the daily job has not run): the runs show, the context says so."""
    context = staticmethod(lambda: [])

    def test_runs_without_a_context_record(self):
        t = self.open_usage().eval(TEXT)
        self.assertIn("$6.50", t)
        self.assertIn("Not measured yet", t)


class UsageBadFiles(UsageBase):
    """A file that is not JSON at all: the tab opens, with the empty states, and says nothing wrong."""

    @classmethod
    def load(cls, v):
        LiveBrowserCase.load.__func__(cls, v)
        for n in ("run-usage.jsonl", "context-size.jsonl"):
            (v.root / "system" / "staging" / n).write_text("\x00\x01 not json\n{\"at\": \n", encoding="utf-8")

    def test_corrupt_files_show_the_empty_states(self):
        t = self.open_usage().eval(TEXT)
        self.assertIn("No runs yet", t)
        self.assertIn("Not measured yet", t)


@unittest.skipUnless(PROPOSAL.exists(), "dev/proposals/usage-monitor/live_server.diff not written yet")
class UsageRoute(UsageBase):
    """The proposal applied to the throwaway vault's own copy of live_server.py (never committed): GET /api/usage, token-checked."""

    @classmethod
    def load(cls, v):
        super().load(v)
        target = v.root / "system" / "scripts" / "live_server.py"
        r = subprocess.run(["patch", "--no-backup-if-mismatch", "-p0", str(target), str(PROPOSAL)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr

    def get(self, token):
        req = urllib.request.Request(self.base + "/api/usage", headers={"X-Creaite-Token": token} if token else {})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_route_needs_the_token_and_serves_the_report(self):
        self.b.eval("go('activity')")
        token = self.b.eval("D.token")
        self.assertEqual(self.get(None)[0], 403)
        self.assertEqual(self.get("wrong")[0], 403)
        code, got = self.get(token)
        self.assertEqual(code, 200)
        self.assertTrue(got["ok"])
        self.assertEqual((got["cards"]["cost"]["now"], got["days"], got["as_of"]), (6.5, 14, "2026-10-19"))
        self.assertNotIn("POISONED", json.dumps(got))

    def test_route_is_get_only(self):
        token = self.b.eval("(go('activity'), D.token)")
        req = urllib.request.Request(self.base + "/api/usage", data=b"{}", method="POST", headers={"X-Creaite-Token": token})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=10)
        self.assertIn(cm.exception.code, (400, 404, 405))

    def test_the_tab_refreshes_from_the_route(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("!!document.querySelector('#actTabU')")
        # a run recorded after the page was built: only the route knows it
        f = self.v.root / "system" / "staging" / "run-usage.jsonl"
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(fx.run("2026-10-19T09:30:00", "prep", 0.50, 21000)) + "\n")
        b.click("#actTabU")
        b.wait(f"{TEXT}.includes('$7.00')")
        self.assertIn("Prep page", b.eval(TEXT))
        # and the tab stays read only
        self.assertEqual(b.eval(f"{PANEL}.querySelectorAll('button, input').length"), 0)


if __name__ == "__main__":
    unittest.main()
