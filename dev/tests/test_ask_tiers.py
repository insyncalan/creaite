"""BL-194: risk tiers on ask creaite's approval card, the rollback line, and the tier in the log.

Run: python3 dev/tests/test_ask_tiers.py   (the Chrome part needs Google Chrome; skipped otherwise)
A temporary vault and a temporary home folder (HOME), with test_admin_card's stand-in `claude` (it runs the real guard hook before
each tool call). Nothing reaches Microsoft 365. The tier is display and logging only: these tests also check that it never makes a
change that BL-141 refuses, nor refuses one it allows.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from live_browser import TEST_PALETTES, TEST_PALETTES_JS  # noqa: E402
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_admin_card as admin  # noqa: E402
from test_onedrive_projects import touch  # noqa: E402
from test_tracker import Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

# Extra scenarios for the stand-in: one Sensitive and one High-risk change on one card; a settings file edited with and without a
# permission key changed.
EXTRA = r'''elif message.startswith("tier both"):
    write("system/staging/drafts/plan.md", "the plan\n")
    bash('python3 system/scripts/filechange.py create ~/Documents/plan.md --from system/staging/drafts/plan.md --why "Alan asked"')
    write("system/staging/drafts/settings.json", settings_with("WebSearch"))
    bash('python3 system/scripts/filechange.py edit .claude/settings.json --from system/staging/drafts/settings.json --why "Alan asked"')
elif message.startswith("tier config perm"):
    c = json.loads((vault / "system/config/settings.json").read_text())
    c.setdefault("assistant", {})["additionalDirectories"] = ["~/Documents"]
    write("system/staging/drafts/cfg.json", json.dumps(c, indent=2) + "\n")
    bash('python3 system/scripts/filechange.py edit system/config/settings.json --from system/staging/drafts/cfg.json --why "x"')
elif message.startswith("tier config plain"):
    c = json.loads((vault / "system/config/settings.json").read_text())
    c.setdefault("assistant", {})["run_timeout_minutes"] = 17
    write("system/staging/drafts/cfg.json", json.dumps(c, indent=2) + "\n")
    bash('python3 system/scripts/filechange.py edit system/config/settings.json --from system/staging/drafts/cfg.json --why "x"')
elif message.startswith("tier plain note"):
    write("system/staging/drafts/note.md", "tidied\n")
    bash(f'python3 system/scripts/filechange.py edit "{NOTE}" --from system/staging/drafts/note.md --why "tidy"')
elif message.startswith("ask a rule"):'''
FAKE = admin.FAKE.replace('elif message.startswith("ask a rule"):', EXTRA, 1)
ROLLBACK = "python3 system/scripts/filechange.py undo"


def tiered_server():
    s = admin.Server()
    fake = s.root / "fake_claude.py"                     # the server runs the stand-in afresh each time: add the scenarios
    fake.write_text(FAKE)
    return s


class DetectorTests(unittest.TestCase):
    """reach.permission_change and reach.tier, in a temporary vault and home folder."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="creaite-home-")).resolve()
        self.v = Vault()
        self.root = self.v.root.resolve()
        self.env = {**os.environ, "HOME": str(self.home)}

    def tearDown(self):
        self.v.cleanup()
        shutil.rmtree(self.home, ignore_errors=True)

    def py(self, code):
        src = f"import sys, json; sys.path.insert(0, {str(self.root / 'system/scripts')!r})\nimport reach\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir(), env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_detector_compares_only_the_permission_keys(self):
        old = {"permissions": {"allow": ["Read"], "deny": ["Bash(rm *)"], "ask": []}, "model": "x", "env": {"A": "1"}}
        cases = {
            "added": ({**old, "permissions": {**old["permissions"], "allow": ["Read", "WebSearch"]}}, True),
            "removed": ({**old, "permissions": {**old["permissions"], "deny": []}}, True),
            "ask": ({**old, "permissions": {**old["permissions"], "ask": ["Bash(ls *)"]}}, True),
            "dirs": ({**old, "permissions": {**old["permissions"], "additionalDirectories": ["~/x"]}}, True),
            "mode": ({**old, "permissions": {**old["permissions"], "defaultMode": "acceptEdits"}}, True),
            "hooks": ({**old, "hooks": {"PreToolUse": []}}, True),
            "nested": ({**old, "assistant": {"allow": ["Bash"]}}, True),
            "other keys": ({**old, "model": "y", "env": {"A": "2"}, "statusLine": {}}, False),
            "reordered": ({**old, "permissions": {"ask": [], "deny": ["Bash(rm *)"], "allow": ["Read"]}}, False),
            "same": (old, False),
        }
        out = self.py(f"cases = {json.dumps({k: v[0] for k, v in cases.items()})}\nold = {json.dumps(old)!r}\n"
                      "print(json.dumps({k: reach.permission_change(old, json.dumps(v)) for k, v in cases.items()}))")
        for name, (_new, changed) in cases.items():
            self.assertEqual(out[name]["changed"], changed, name)
        self.assertEqual(out["added"]["added"], ["permissions.allow: WebSearch"])
        self.assertEqual(out["removed"]["removed"], ["permissions.deny: Bash(rm *)"])
        self.assertEqual(out["mode"]["keys"], ["permissions.defaultMode"])
        self.assertEqual(out["hooks"]["keys"], ["hooks"])

    def test_text_that_is_not_json_has_no_permission_keys_and_empty_is_an_empty_file(self):
        out = self.py("print(json.dumps([reach.permission_change('# notes', '# notes, more'), "
                      "reach.permission_change(b'', b'{\"permissions\": {\"allow\": [\"X\"]}}'), "
                      "reach.permission_change(None, '{}')]))")
        self.assertEqual((out[0]["changed"], out[0]["json"]), (False, False))
        self.assertEqual(out[1]["added"], ["permissions.allow: X"])
        self.assertFalse(out[2]["changed"])

    def test_a_permission_file_is_high_risk_and_a_settings_file_is_sensitive_unless_a_permission_key_changes(self):
        out = self.py(
            "cfg = b'{\"assistant\": {}}'\n"
            "perm = b'{\"assistant\": {\"additionalDirectories\": [\"~/Documents\"]}}'\n"
            "plain = b'{\"assistant\": {\"run_timeout_minutes\": 17}}'\n"
            "print(json.dumps({"
            "'claude': reach.tier('.claude/settings.json', 'change', b'{}', b'{}'),"
            "'local': reach.tier('.claude/settings.local.json', 'create', b'', b'{}'),"
            "'home': reach.tier('~/.claude/settings.json', 'change'),"
            "'mcp': reach.tier('.mcp.json', 'change'),"
            "'cfg perm': reach.tier('system/config/settings.json', 'change', cfg, perm),"
            "'cfg plain': reach.tier('system/config/settings.json', 'change', cfg, plain),"
            "'schedules': reach.tier('system/config/schedules.md', 'change', b'a', b'b'),"
            "'outside': reach.tier('~/Documents/plan.md', 'create', b'', b'the plan'),"
            "'move onto': reach.tier('system/staging/drafts/x.json', 'move', to='.claude/settings.json'),"
            "'skills': reach.tier('.claude/skills/x/SKILL.md', 'change', b'a', b'b')}))")
        self.assertEqual({k: v[0] for k, v in out.items()},
                         {"claude": "high", "local": "high", "home": "high", "mcp": "high", "cfg perm": "high", "cfg plain": "sensitive",
                          "schedules": "sensitive", "outside": "sensitive", "move onto": "high", "skills": "sensitive"})
        self.assertIn("additionalDirectories", out["cfg perm"][1])

    def test_the_tier_never_changes_what_is_allowed(self):
        """classify gives the same verdicts as before for the files the tier looks at: the tier is a label, never a gate."""
        out = self.py("print(json.dumps([reach.classify(p, 'change') for p in ('.claude/settings.json', 'system/config/settings.json', "
                      "'system/scripts/reach.py', 'system/tracker.db', '~/.ssh/config')]))")
        self.assertEqual([k for k, _ in out], ["sensitive", "sensitive", "never", "never", "never"])


class CardTierTests(unittest.TestCase):
    """Through the live server: each item on the one card carries its tier; Approve and Decline are as BL-141 made them."""

    @classmethod
    def setUpClass(cls):
        cls.s = tiered_server()
        cls.settings = cls.s.root / ".claude/settings.json"
        cls.config = cls.s.root / "system/config/settings.json"
        cls.original, cls.original_config = cls.settings.read_text(), cls.config.read_text()

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    def setUp(self):
        self.settings.write_text(self.original)
        self.config.write_text(self.original_config)
        touch(self.s.root / admin.NOTE, "notes\n")
        shutil.rmtree(self.s.home / "Documents", ignore_errors=True)
        (self.s.root / "system/guard/marked-sessions.json").unlink(missing_ok=True)

    def card(self, message):
        cards = [e for e in self.s.ask(message) if e["type"] == "changes"]
        self.assertEqual(len(cards), 1, cards)
        return cards[0]

    def test_one_sensitive_and_one_high_risk_item_share_one_card(self):
        c = self.card("tier both")
        tiers = {it["path"]: it["tier"] for it in c["items"]}
        self.assertEqual(tiers, {"~/Documents/plan.md": "sensitive", ".claude/settings.json": "high"})
        high = next(it for it in c["items"] if it["tier"] == "high")
        self.assertIn("permission", high["tier_reason"])
        self.assertNotIn("_fingerprint", json.dumps(c))                   # the page still never sees the fingerprint or the snapshot
        r = self.s.post("/api/changes/approve", {"card": c["card"]})      # one Approve makes both
        self.assertTrue(r["ok"], r)
        self.assertIn("WebSearch", json.loads(self.settings.read_text())["permissions"]["allow"])
        self.assertEqual((self.s.home / "Documents/plan.md").read_text(), "the plan\n")

    def test_decline_makes_neither(self):
        c = self.card("tier both")
        self.assertEqual(sorted(it["tier"] for it in c["items"]), ["high", "sensitive"])
        self.assertTrue(self.s.post("/api/changes/decline", {"card": c["card"]})["ok"])
        self.assertEqual(self.settings.read_text(), self.original)
        self.assertFalse((self.s.home / "Documents/plan.md").exists())

    def test_a_settings_edit_that_changes_a_permission_key_is_high_risk(self):
        c = self.card("tier config perm")
        self.assertEqual([(it["path"], it["tier"]) for it in c["items"]], [("system/config/settings.json", "high")])
        self.assertIn("additionalDirectories", c["items"][0]["tier_reason"])

    def test_a_settings_edit_without_one_is_sensitive(self):
        c = self.card("tier config plain")
        self.assertEqual([(it["path"], it["tier"]) for it in c["items"]], [("system/config/settings.json", "sensitive")])

    def test_a_permission_line_is_high_risk(self):
        c = self.card("ask a rule")
        self.assertEqual([it["tier"] for it in c["items"]], ["high"])

    def test_a_refused_rule_is_still_refused_whatever_its_tier(self):
        evs = self.s.ask("mail bash")
        c = next(e for e in evs if e["type"] == "changes")
        self.assertEqual(c["items"], [])
        self.assertTrue(any("Bash" in r for r in c["refused"]), c)
        self.assertEqual(self.settings.read_text(), self.original)

    def test_an_ordinary_change_has_no_card(self):
        self.assertEqual([e for e in self.s.ask("tier plain note") if e["type"] == "changes"], [])
        self.assertEqual((self.s.root / admin.NOTE).read_text(), "tidied\n")

    # ── the tier in the log (item 3) ──
    def logged(self):
        return [json.loads(x) for x in (self.s.root / "system/config/files-log.jsonl").read_text().splitlines()]

    def test_the_tier_is_in_the_log_and_the_list(self):
        c = self.card("tier both")
        self.assertTrue(self.s.post("/api/changes/approve", {"card": c["card"]})["ok"])
        self.s.ask("tier plain note")
        last = {e["path"]: e for e in self.logged()[-3:]}
        self.assertEqual({p: (e["tier"], e.get("approved", False)) for p, e in last.items()},
                         {"~/Documents/plan.md": ("sensitive", True), ".claude/settings.json": ("high", True), admin.NOTE: ("ordinary", False)})
        listed = {r["path"]: r["tier"] for r in self.s.post("/api/changes/list", {})["changes"][:3]}
        self.assertEqual(listed, {p: e["tier"] for p, e in last.items()})
        self.assertNotIn("WebSearch", json.dumps([e for e in self.logged()]))      # paths and reasons only, never contents

    def test_a_settings_edit_that_changes_a_permission_key_is_logged_high_risk(self):
        c = self.card("tier config perm")
        self.assertTrue(self.s.post("/api/changes/approve", {"card": c["card"]})["ok"])
        e = self.logged()[-1]
        self.assertEqual((e["path"], e["tier"]), ("system/config/settings.json", "high"))

    def test_undo_still_works_on_a_tiered_change(self):
        c = self.card("tier both")
        self.assertTrue(self.s.post("/api/changes/approve", {"card": c["card"]})["ok"])
        n = next(e["id"] for e in reversed(self.logged()) if e["path"] == ".claude/settings.json")
        self.assertTrue(self.s.post("/api/changes/undo", {"id": n})["ok"])
        self.assertEqual(self.settings.read_text(), self.original)


SCRIPT = r"""
<script>
(async()=>{ const out={errors:[]}, wait=ms=>new Promise(r=>setTimeout(r,ms));
  const until=async(f,n=100)=>{ for(let i=0;i<n&&!f();i++) await wait(100); };
  try{
    await checkLive(); await until(()=>document.querySelector("#chLog [data-card]"));
    const card=document.querySelector("#chLog [data-card]");
    out.items=[...card.querySelectorAll("li.chgtier")].map(li=>({tier:li.dataset.tier, cls:li.className, tag:li.querySelector(".tag").textContent,
      icon:(li.querySelector(".tag svg")||{}).dataset?.icn||null, back:!!li.querySelector(".chgback"),
      backText:(li.querySelector(".chgback")||{}).textContent||"", title:li.querySelector("b").textContent}));
    out.buttons=[...card.querySelectorAll(".acts button")].map(b=>b.textContent);
    out.head=card.textContent.replace(/\s+/g," ").slice(0,300);
    // Copy: the command on the clipboard (a stand-in clipboard, as headless Chrome has none)
    let copiedText=null; Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:t=>{ copiedText=t; return Promise.resolve(); }}});
    card.querySelector("[data-chgcopy]").click(); await wait(200); out.copied=copiedText;
    // contrast of every text on each band, the tag, and the band's edge, in every theme, light and dark
    const lum=c=>{ const v=c.match(/[\d.]+/g).slice(0,3).map(x=>{ x/=255; return x<=.03928?x/12.92:Math.pow((x+.055)/1.055,2.4); }); return .2126*v[0]+.7152*v[1]+.0722*v[2]; };
    const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); };
    out.contrast={}; out.distinct={}; const root=document.documentElement;
    for(const pal of TEST_PALETTES) for(const mode of ["light","dark"]){
      root.setAttribute("data-palette",pal); root.setAttribute("data-theme",mode); await wait(30);
      const surf=getComputedStyle(card).backgroundColor, bands=[];
      for(const li of card.querySelectorAll("li.chgtier")){ const band=getComputedStyle(li).backgroundColor, tag=getComputedStyle(li.querySelector(".tag")); bands.push(band);
        const text=[tag.color, getComputedStyle(li.querySelector("b")).color, getComputedStyle(li.querySelector(".sub")).color]
          .concat(li.querySelector(".chgback")?[getComputedStyle(li.querySelector(".chgback")).color]:[]);
        out.contrast[`${pal} ${mode} ${li.dataset.tier}`]={text:Math.min(...text.map(c=>ratio(c,band)), ratio(tag.color,tag.backgroundColor)),
          edge:ratio(getComputedStyle(li).borderLeftColor,surf)}; }
      out.distinct[`${pal} ${mode}`]=bands[0]!==bands[1]; }
    root.removeAttribute("data-palette"); root.removeAttribute("data-theme");
    card.querySelector('[data-chg="yes"]').click();
    await until(()=>card.querySelector(".acts").textContent.includes("Approved"));
    await wait(300); out.after=card.querySelector(".acts").textContent;
    out.undo=(card.querySelector(".chgback code")||{}).textContent;
    go("activity"); await until(()=>document.querySelector("#achgTbl tr[data-achg]"));
    out.activity=[...document.querySelectorAll("#achgTbl tr[data-achg]")].map(tr=>[tr.dataset.tier, tr.children[1].textContent.trim(),
      (tr.children[1].querySelector("svg")||{}).dataset?.icn||null, tr.children[2].textContent.replace(/\s+/g," ").trim()]);
    out.activityHead=[...document.querySelectorAll("#achgTbl th")].map(th=>th.textContent);
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre); })();
</script>
""".replace("TEST_PALETTES", TEST_PALETTES_JS)


@unittest.skipUnless(admin.CHROME.exists(), "Google Chrome not installed")
class CardPageTests(unittest.TestCase):
    """The page: one Sensitive and one High-risk change on the card, each with a word and an icon on its band, the rollback line
    with Copy under the High-risk one only, readable in every theme, and BL-141's one Approve."""

    @classmethod
    def setUpClass(cls):
        cls.s = s = tiered_server()
        inject = s.root / "inject.html"
        inject.write_text(SCRIPT)
        s.proc.terminate()
        s.proc.wait(timeout=10)
        s.env["CREAITE_TEST_INJECT"] = str(inject)
        s.proc = subprocess.Popen([sys.executable, str(s.root / "system/scripts/live_server.py")], env=s.env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(80):
            try:
                urllib.request.urlopen(s.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(s.base + "/").read().decode()
        s.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        evs = s.ask("tier both")
        s.post("/api/ask/ack", {"run": next(e for e in evs if e["type"] == "done")["run"]})
        sys.path.insert(0, str(REPO / "dev/tools"))
        from cdp import Browser
        try:
            with Browser() as b:
                b.goto(s.base + "/", wait_for="!!document.getElementById('result')", timeout=240)
                out = b.eval("document.getElementById('result').textContent")
        except (TimeoutError, RuntimeError):
            out = ""
        assert out, "the page didn't finish the scripted steps"
        cls.r = json.loads(out)

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    def test_no_script_errors(self):
        self.assertEqual(self.r["errors"], [])

    def test_each_tier_has_a_word_and_an_icon_on_its_band(self):
        got = {it["tier"]: it for it in self.r["items"]}
        self.assertEqual(set(got), {"sensitive", "high"})
        self.assertEqual((got["sensitive"]["tag"], got["sensitive"]["icon"]), ("Sensitive", "alert"))
        self.assertEqual((got["high"]["tag"], got["high"]["icon"]), ("High-risk", "shield"))
        self.assertIn("tier-sens", got["sensitive"]["cls"])
        self.assertIn("tier-high", got["high"]["cls"])
        self.assertIn("1 is High-risk", self.r["head"])

    def test_the_rollback_line_is_under_the_high_risk_item_only_and_copies(self):
        got = {it["tier"]: it for it in self.r["items"]}
        self.assertFalse(got["sensitive"]["back"])
        self.assertTrue(got["high"]["back"])
        self.assertIn("Undo it from Activity › What ask creaite changed".lower(), got["high"]["backText"].lower())
        self.assertIn(ROLLBACK, got["high"]["backText"])
        self.assertEqual(self.r["copied"], ROLLBACK)

    def test_one_approve_and_one_decline_and_after_approve_the_line_names_the_change(self):
        self.assertEqual(self.r["buttons"], ["Decline", "Approve"])
        self.assertIn("Approved", self.r["after"])
        self.assertRegex(self.r["undo"], r"^python3 system/scripts/filechange\.py undo \d+$")
        self.assertIn("WebSearch", json.loads((self.s.root / ".claude/settings.json").read_text())["permissions"]["allow"])

    def test_activity_shows_each_change_with_its_tier(self):
        self.assertEqual(self.r["activityHead"][:3], ["When", "Tier", "Change"])
        rows = {r[3].replace(" approved on the card", ""): r[:3] for r in self.r["activity"]}
        self.assertEqual(rows.get("Changed settings"), ["high", "High-risk", "shield"], self.r["activity"])
        self.assertEqual(rows.get("Created plan"), ["sensitive", "Sensitive", "alert"], self.r["activity"])

    def test_both_tiers_are_readable_and_distinct_in_every_theme(self):
        self.assertEqual(len(self.r["contrast"]), 2 * 2 * len(TEST_PALETTES))
        for name, c in self.r["contrast"].items():
            self.assertGreaterEqual(c["text"], 4.5, name)
            self.assertGreaterEqual(c["edge"], 3.0, name)
        self.assertTrue(all(self.r["distinct"].values()), self.r["distinct"])


if __name__ == "__main__":
    unittest.main()
