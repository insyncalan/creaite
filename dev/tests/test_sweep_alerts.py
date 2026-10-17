"""Tests for the mail, calendar and alerts sprint: the sweep ignore list (BL-97), VIPs (BL-99) and meeting prep
(BL-98).

Run: python3 dev/tests/test_sweep_alerts.py
Each class builds a throwaway vault and runs the real scripts there with fictional messages and invites. No Microsoft 365.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

NOW = "2026-10-08 09:30"


def run(v, script, *args, now=NOW, check=True):
    r = subprocess.run([sys.executable, str(v.root / "system/scripts" / script), *args], cwd=v.root,
                       capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": now})
    if check and r.returncode:
        raise AssertionError(f"{script} {args}: {r.stdout}{r.stderr}")
    return r


def email(subject="[ABC] SOW", sender="Jane Doe <jane@client.example>", link="abc1"):
    return (f"Email · From: {sender} · Subject: {subject} · Sent: 2026-10-07 09:12 · "
            f"Link: https://outlook.office365.com/owa/?ItemID={link}")


def settings(v, change):
    cfg = v.root / "system/config/settings.json"
    d = json.loads(cfg.read_text())
    change(d)
    cfg.write_text(json.dumps(d, indent=2))


class IgnoreTests(unittest.TestCase):
    """BL-97: the rules at every point they apply (ignore, stage, calendar), with the counts."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.drafts = self.v.root / "system/staging/drafts"
        self.drafts.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.v.cleanup()

    def ignore(self, messages, **spec):
        f = self.drafts / "messages.json"
        f.write_text(json.dumps({"messages": messages, **spec}))
        return json.loads(run(self.v, "sweep.py", "ignore", str(f)).stdout)

    def test_shipped_rules_and_case(self):
        got = self.ignore([
            {"kind": "calendar", "subject": "TODO: book flights"},                         # begins with, any case
            {"kind": "mail", "subject": "ToDo list for ABC"},
            {"kind": "mail", "subject": "ABC todo"},                                       # doesn't begin with it
            {"kind": "mail", "subject": "RE: FW: [ABC] todo: chase"},                      # past RE:, FW: and tags
            {"kind": "mail", "from": "HR <Hr@Brightwater.Example>", "subject": "[ABC] payroll"},
            {"kind": "teams", "from": "hr@brightwater.example", "subject": "x"},      # mail only
            {"kind": "mail", "subject": "[ABC] SOW", "sensitivity": "Private"},
            {"kind": "teams", "subject": "", "sensitivity": "personal"},
            {"kind": "calendar", "subject": "Dentist", "private": True},
            {"kind": "calendar", "subject": "Info: office closed Friday"},                 # Alan, 2026-10-09
            {"kind": "calendar", "subject": "FYI: new expenses policy"},
            {"kind": "mail", "subject": "Info: newsletter"},                               # calendar only
            {"kind": "mail", "subject": "[ABC] SOW", "sensitivity": "normal"}])
        self.assertEqual(got["keep"], [2, 5, 11, 12])
        self.assertEqual(got["ignored"], {"ToDo invites": 3, "humancapital": 1, "Anything marked private": 3,
                                          "Info: entries": 1, "FYI: entries": 1})

    def test_each_match_type_and_rules_off(self):
        rules = [
            {"name": "contains", "where": ["mail"], "field": "subject", "how": "contains", "text": "Newsletter", "on": True},
            {"name": "equals", "where": ["mail"], "field": "subject", "how": "equals", "text": "out of office", "on": True},
            {"name": "domain", "where": ["mail", "teams"], "field": "sender", "how": "domain", "text": "@noise.example", "on": True},
            {"name": "channel", "where": ["teams"], "field": "channel", "how": "begins", "text": "random", "on": True},
            {"name": "off", "where": ["mail"], "field": "subject", "how": "contains", "text": "keep me", "on": False}]
        settings(self.v, lambda d: d["sweep"].__setitem__("ignore", rules))
        got = self.ignore([
            {"kind": "mail", "subject": "The weekly NEWSLETTER"},
            {"kind": "mail", "subject": "Out of  Office"},                                # spaces folded
            {"kind": "mail", "subject": "Out of office: back Monday"},                    # not equal
            {"kind": "mail", "from": "a@mail.noise.example"},                              # a subdomain is the domain
            {"kind": "mail", "from": "a@notnoise.example"},
            {"kind": "teams", "channel": "Random chatter"},
            {"kind": "mail", "subject": "keep me please"},                                 # its rule is off
            {"kind": "mail", "subject": "x", "sensitivity": "private"}])                  # private rule restored, off
        self.assertEqual(got["keep"], [2, 4, 6, 7])
        self.assertEqual(sorted(got["ignored"]), ["channel", "contains", "domain", "equals"])

    def test_a_named_thread_is_never_ignored(self):
        got = self.ignore([{"kind": "mail", "subject": "ToDo: sign off"}], named=True)
        self.assertEqual((got["keep"], got["ignored"]), ([0], {}))

    def test_window_lists_the_rules_in_force(self):
        settings(self.v, lambda d: d["sweep"]["ignore"][2].__setitem__("on", False))
        w = json.loads(run(self.v, "sweep.py", "window").stdout)
        self.assertEqual([r["name"] for r in w["ignore"]], ["Anything marked private", "ToDo invites", "Info: entries",
                                                             "FYI: entries"])

    def stage(self, items, **spec):
        f = self.drafts / "sweep.json"
        f.write_text(json.dumps({"window": {"start": "2026-10-07 08:00", "end": NOW}, "items": items, **spec}))
        return run(self.v, "sweep.py", "stage", str(f)).stdout

    def item(self, text, source):
        return {"table": "actions", "match": "strong", "values": {"project": "ABC", "description": text,
                                                                 "owner": "Alan Carter", "source": source}}

    def test_stage_backstop_beats_a_project_match_and_counts(self):
        out = self.stage([self.item("Send the SOW", email()),
                          self.item("Book the offsite", email(subject="[ABC] ToDo offsite", link="t1")),
                          self.item("Fill in the survey", email(sender="HR <hr@brightwater.example>", link="h1"))])
        self.assertIn("Sweep: 1 item", out)
        self.assertIn("skipped (ignore rule “ToDo invites”): Book the offsite", out)
        self.assertIn("skipped (ignore rule “humancapital”): Fill in the survey", out)
        prop = next((self.v.root / "system/staging").glob("proposed-*-sweep.json"))
        self.assertEqual([i["values"]["description"] for i in json.loads(prop.read_text())["items"]], ["Send the SOW"])
        # the run's counts, from ignore, stage and calendar together, reach the summary and the run log
        self.ignore([{"kind": "calendar", "subject": "todo: expenses"}])
        out = run(self.v, "sweep.py", "done", "--started", NOW, "--normal", "--summary", "Sweep: 1 item").stdout
        self.assertIn("Ignored 3: ToDo invites 2, humancapital 1.", out)
        log = (self.v.root / "system/staging/run-log.txt").read_text()
        self.assertIn("sweep ok (normal) | Sweep: 1 item; Ignored 3: ToDo invites 2, humancapital 1", log)
        self.assertFalse((self.v.root / "system/staging/sweep-ignored.json").exists())       # cleared for the next run
        self.assertNotIn("offsite", log)                                                       # counts only, no content

    def test_stage_named_thread_overrides(self):
        out = self.stage([self.item("Book the offsite", email(subject="ToDo offsite"))], named=True)
        self.assertIn("Sweep: 1 item", out)

    def test_calendar_drops_ignored_events(self):
        f = self.drafts / "calendar.json"
        f.write_text(json.dumps({"days": {"2026-10-08": [
            {"id": "e1", "start": "09:00", "end": "10:00", "title": "ABC steering", "teams": True},
            {"id": "e2", "start": "11:00", "end": "11:30", "title": "ToDo: ABC expenses"},          # names ABC: still ignored
            {"id": "e3", "start": "12:00", "end": "13:00", "title": "Lunch", "sensitivity": "private"},
            {"id": "e4", "start": "14:00", "end": "15:00", "title": "HR briefing", "organiser": "HR",
             "organiser_email": "hr@brightwater.example"}]}}))                              # a mail-only rule
        out = run(self.v, "sweep.py", "calendar", str(f)).stdout
        self.assertIn("Calendar saved: 2 meetings over 1 day. Ignored 2: ", out)
        saved = (self.v.root / "system/staging/calendar.json").read_text()
        self.assertEqual([e["id"] for e in json.loads(saved)["days"]["2026-10-08"]], ["e1", "e4"])
        self.assertNotIn("expenses", saved)
        self.assertNotIn("Lunch", saved)
        # and so neither Today's day view nor the Inbox's Meetings has them
        run(self.v, "build_dashboard.py")
        import re
        html = (self.v.root / "dashboard.html").read_text()
        data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        self.assertEqual([e["title"] for e in data["calendar"]["days"]["2026-10-08"]], ["ABC steering", "HR briefing"])
        self.assertEqual({m["title"] for m in data["meetings"]["rows"]}, {"ABC steering", "HR briefing"})



FAKE_VAULT = """const FILES={}, LOG=[];
  VW={ async read(p){ if(!(p in FILES)) throw new Error("not found: "+p); return FILES[p]; },
       async write(p,t){ FILES[p]=t; LOG.push(p); }, async remove(p){ delete FILES[p]; }, async exists(p){ return p in FILES; },
       async append(p,t){ FILES[p]=(FILES[p]||"")+t; } };
  VSTATE="ok"; needVault=async()=>true; window.confirm=()=>true;
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
"""


class IgnoreSettingsTests(unittest.TestCase):
    """BL-97: Settings › Sweep lists the rules; add, edit, switch off and delete write sweep.ignore."""

    @classmethod
    def setUpClass(cls):
        from test_insight import chrome
        cls.v = v = Vault()
        v.run("init")
        run(v, "build_dashboard.py")
        cfg = (v.root / "system/config/settings.json").read_text()
        cls.out, cls.errors = chrome(v, FAKE_VAULT + "FILES['system/config/settings.json']=" + json.dumps(cfg) + ";" + """
  const out={}, saved=()=>JSON.parse(FILES['system/config/settings.json']).sweep.ignore, click=s=>document.querySelector(s).click();
  go("settings","capture"); await wait(50);
  out.rows=[...document.querySelectorAll('#ignMgr .igrow b')].map(b=>b.textContent);
  out.privateDelete=!!document.querySelector('#ignMgr .igrow:first-child [data-ig="del"]');
  click('[data-ig="add"]'); document.getElementById('igName').value='Newsletters';
  document.querySelector('[data-igw="teams"]').checked=true; const f=document.getElementById('igField'); f.value='sender';
  f.dispatchEvent(new Event('change',{bubbles:true})); out.senderHows=[...document.getElementById('igHow').options].map(o=>o.value);
  document.getElementById('igHow').value='domain'; document.getElementById('igText').value='news.example';
  click('[data-ig="save"]'); await wait(200); out.added=saved().slice(-1)[0];
  const sw=document.querySelector('[data-igon="1"]'); sw.checked=false; sw.dispatchEvent(new Event('change',{bubbles:true})); await wait(200);
  out.todoOn=saved()[1].on;
  click('[data-ig="edit"][data-i="5"]'); document.getElementById('igText').value='mail.news.example'; click('[data-ig="save"]'); await wait(200);
  out.edited=saved()[5].text;
  click('[data-ig="del"][data-i="2"]'); await wait(200); out.after=saved().map(r=>r.name);
  out.logged=(FILES['system/config/settings-log.jsonl']||'').split('\\n').filter(Boolean).length;
  window.OUT=out;""", "ignore-settings")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_list_add_switch_edit_delete(self):
        o = self.out
        self.assertEqual(self.errors, [])
        self.assertNotIn("error", o or {}, o)
        self.assertEqual(o["rows"], ["Anything marked private", "ToDo invites", "humancapital", "Info: entries", "FYI: entries"])
        self.assertFalse(o["privateDelete"])                                                   # built in: no Delete
        self.assertEqual(o["senderHows"], ["address", "domain", "begins", "contains", "equals"])
        self.assertEqual(o["added"], {"name": "Newsletters", "where": ["mail", "teams"], "field": "sender",
                                      "how": "domain", "text": "news.example", "on": True})
        self.assertFalse(o["todoOn"])
        self.assertEqual(o["edited"], "mail.news.example")
        self.assertEqual(o["after"], ["Anything marked private", "ToDo invites", "Info: entries", "FYI: entries", "Newsletters"])
        self.assertEqual(o["logged"], 4)                                                       # every change logged



REGISTER = """# People register

## People

| Full name | Email | Aliases | Organisation | Role | Hidden | VIP |
|---|---|---|---|---|---|---|
| Mia Hale | mia@client.example, m.hale@client-group.example | Mia | Client | Sponsor | | client |
| Ben Ito | ben@brightwater.example | Ben | Brightwater | Director | | management |
| Omar Ali | omar@brightwater.example | Omar | | | | |
"""
MIA2 = "Mia Hale <m.hale@client-group.example>"


def vip_vault():
    v = Vault()
    v.run("init")
    (v.root / "projects/_portfolio/people-register.md").write_text(REGISTER)
    (v.root / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
    return v


TZ = "+04:00"                     # BL-342 Part 3 B: the laptop's zone in the server tests (CREAITE_TZ_OFFSET)


def zoned(found):
    """A stand-in check's reply as the prompt asks for it: every time with the zone's offset (a bare time is dropped)."""
    def one(m):
        out = dict(m)
        for k in ("last", "sent", "replied"):
            t = str(out.get(k) or "")
            if len(t) == 16 and t[10] in " T":
                out[k] = f"{t[:10]}T{t[11:]}{TZ}"
        return out
    return [one(m) if isinstance(m, dict) else m for m in found]


def fast_checks(v):
    """Let a test's server check about every second: the vault's own copy of sweep.py gets a lower floor (the constant the
    real one holds at 10 minutes; tests change the copy, never an environment variable)."""
    f = v.root / "system/scripts/sweep.py"
    text = f.read_text()
    assert "VIP_MIN_MINUTES, VIP_MAX_MINUTES = 10, 240" in text
    f.write_text(text.replace("VIP_MIN_MINUTES, VIP_MAX_MINUTES = 10, 240", "VIP_MIN_MINUTES, VIP_MAX_MINUTES = 0.01, 240"))


def check_since(v, since="2026-10-08 07:00"):
    """The window the first check reads from (vip.json's last_check), so a fixture's earlier messages are inside it."""
    f = v.root / "system/staging/vip.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"last_check": since, "alerts": []}))


def record(v, messages, how="sweep"):
    f = v.root / "system/staging/drafts/found.json"
    f.write_text(json.dumps(messages))
    return run(v, "sweep.py", "vip", "record", str(f), "--found", how).stdout


def vip_file(v):
    return json.loads((v.root / "system/staging/vip.json").read_text())


class VipTests(unittest.TestCase):
    """BL-99: the register's VIPs, the check (bypassing matching and ignore rules), and the alerts."""

    def setUp(self):
        self.v = vip_vault()

    def tearDown(self):
        self.v.cleanup()

    def test_addresses_include_every_address_and_the_second_maps_to_the_name(self):
        got = json.loads(run(self.v, "sweep.py", "vip", "addresses").stdout)
        self.assertEqual(got["addresses"], {"mia@client.example": "Mia Hale", "ben@brightwater.example": "Ben Ito",
                                            "m.hale@client-group.example": "Mia Hale"})
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'system/scripts'); import propose; "
                            "p, o = propose.people_pool(); print(propose.resolve_person('M.Hale@client-group.example', p, o)['name'])"],
                           cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "Mia Hale")

    def test_a_vip_message_is_alerted_with_no_project_never_twice_and_no_text(self):
        msgs = [{"kind": "mail", "from": MIA2, "subject": "Quick question", "sent": "2026-10-08 08:50",
                 "link": "https://outlook.office365.com/owa/?ItemID=m1", "gist": "Asks whether go-live can move a week. " * 8,
                 "body": "SECRET BODY TEXT"},
                {"kind": "mail", "from": "Omar Ali <omar@brightwater.example>", "subject": "Not a VIP", "sent": "2026-10-08 09:00",
                 "link": "x2"},
                {"kind": "teams", "from": "ben@brightwater.example", "subject": "[ABC] steer", "sent": "2026-10-08 09:05",
                 "link": "t1", "sensitivity": "Confidential", "gist": "confidential message"},
                {"kind": "calendar", "from": "Ben Ito <ben@brightwater.example>", "subject": "ToDo: 1:1", "sent": "2026-10-08 09:10",
                 "link": "c1", "sensitivity": "private", "gist": "private meeting"}]
        out = record(self.v, msgs)
        self.assertIn("VIP: 3 new alerts", out)
        alerts = vip_file(self.v)["alerts"]
        self.assertEqual([(a["who"], a["p"], a["marker"]) for a in alerts],
                         [("Mia Hale", None, None), ("Ben Ito", "ABC", "confidential"), ("Ben Ito", None, "private")])
        self.assertEqual(len(alerts[0]["gist"]), 140)
        self.assertNotIn("SECRET", (self.v.root / "system/staging/vip.json").read_text())   # no message text
        self.assertIn("VIP: 0 new alerts", record(self.v, msgs))                             # never alerted twice
        run(self.v, "sweep.py", "vip", "seen", alerts[0]["id"])
        self.assertEqual(len(json.loads(run(self.v, "sweep.py", "vip", "list").stdout)), 2)
        self.assertIn("VIP: 0 new alerts", record(self.v, msgs))                             # seen stays seen

    def test_ignore_rules_never_hide_a_vip(self):
        f = self.v.root / "system/staging/drafts/messages.json"
        f.write_text(json.dumps({"messages": [
            {"kind": "mail", "from": MIA2, "subject": "ToDo: sign the SOW", "sensitivity": "private"},
            {"kind": "mail", "from": "Omar Ali <omar@brightwater.example>", "subject": "x", "sensitivity": "private"},
            {"kind": "calendar", "from": "ben@brightwater.example", "subject": "ToDo: catch-up"}]}))
        got = json.loads(run(self.v, "sweep.py", "ignore", str(f)).stdout)
        self.assertEqual(got, {"keep": [0, 2], "ignored": {"Anything marked private": 1}})
        cal = self.v.root / "system/staging/drafts/calendar.json"
        cal.write_text(json.dumps({"days": {"2026-10-08": [
            {"id": "e1", "start": "10:00", "end": "10:30", "title": "Private chat", "private": True,
             "organiser": "Mia Hale", "organiser_email": "mia@client.example"}]}}))
        self.assertIn("Calendar saved: 1 meeting", run(self.v, "sweep.py", "calendar", str(cal)).stdout)

    def test_a_vip_proposal_is_flagged(self):
        f = self.v.root / "system/staging/drafts/sweep.json"
        f.write_text(json.dumps({"items": [
            {"table": "actions", "values": {"project": "ABC", "description": "Send the plan", "owner": "Alan Carter",
                                            "source": email()}},
            {"table": "actions", "values": {"project": "ABC", "description": "Confirm the go-live date", "owner": "Alan Carter",
                                            "source": email(sender=MIA2, link="m9")}}]}))
        run(self.v, "sweep.py", "stage", str(f))
        prop = next((self.v.root / "system/staging").glob("proposed-*-sweep.json"))
        self.assertEqual([("vip" in i["flags"]) for i in json.loads(prop.read_text())["items"]], [False, True])

    def test_no_vips_when_switched_off(self):
        settings(self.v, lambda d: d["vip"].__setitem__("enabled", False))
        self.assertEqual(json.loads(run(self.v, "sweep.py", "vip", "addresses").stdout)["addresses"], {})


class VipPageTests(unittest.TestCase):
    """BL-99: the VIP block opens Today's Needs attention, above the proposals; VIP proposals lead Review."""

    @classmethod
    def setUpClass(cls):
        from test_insight import chrome
        cls.v = v = vip_vault()
        from datetime import date
        record(v, [{"kind": "mail", "from": MIA2, "subject": "Quick word", "sent": f"{date.today().isoformat()} 07:12",
                    "link": "https://outlook.office365.com/owa/?ItemID=m1", "gist": "Asks to confirm the go-live date."}], "start-up")
        f = v.root / "system/staging/drafts/sweep.json"
        f.write_text(json.dumps({"items": [
            {"table": "actions", "values": {"project": "ABC", "description": "Send the plan", "owner": "Alan Carter",
                                            "source": email()}},
            {"table": "actions", "values": {"project": "ABC", "description": "Confirm the go-live date",
                                            "owner": "Alan Carter", "source": email(sender=MIA2, link="m9")}}]}))
        run(v, "sweep.py", "stage", str(f))
        run(v, "build_dashboard.py")
        probe = """const out={}; go("today"); renderToday();
          const msg=document.querySelector('#tdList>li.td-message'), lis=[...document.querySelectorAll('#tdList>li')];   /* BL-319: the message is a row of To decide */
          out.first=[msg.className, msg.textContent.replace(/\\s+/g,' ').trim()]; out.second=lis.filter(l=>l!==msg).map(l=>l.className).join(' ');
          out.badge=document.getElementById('vipBadge').textContent; out.title=document.title;
          go("review"); renderReview(); const rows=[...document.querySelectorAll('#reviewBody tr[data-n]')];
          out.review=rows.map(r=>r.querySelector('td.title').textContent.replace(/\\s+/g,' ').trim().slice(0,40));
          go("person","Mia Hale"); out.person=document.querySelector('#v-person h1').textContent;
          window.OUT=out;"""
        cls.out, cls.errors = chrome(v, probe, "vip-page")
        run(v, "build_dashboard.py")                                                          # a later build (a reload)
        cls.again, _ = chrome(v, "go('today'); renderToday(); window.OUT=document.querySelector('#tdList>li.td-message').className;", "vip-again")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_vip_block_leads_today_and_review(self):
        o = self.out
        self.assertEqual(self.errors, [])
        self.assertNotIn("error", o, o)
        self.assertIn("td-message", o["first"][0])                                          # BL-319: a To decide row
        self.assertIn("Mia Hale: Quick word", o["first"][1])
        self.assertNotIn("VIP", o["first"][1])                                              # BL-288: never labelled
        self.assertIn("no project", o["first"][1])
        self.assertIn("found on start-up, received today 07:12", o["first"][1])
        self.assertIn("Asks to confirm the go-live date.", o["first"][1])
        self.assertIn("td-review", o["second"])                                                # the proposals beside it, newest first
        self.assertEqual(o["badge"], "1")
        self.assertTrue(o["title"].startswith("(1) "), o["title"])                          # BL-288: a plain count
        self.assertFalse(o["review"][0].startswith("VIP"), o["review"])                        # first, unlabelled
        self.assertIn("Confirm the go-live date", o["review"][0])
        self.assertNotIn("VIP", o["person"])
        self.assertIn("td-message", self.again)                                                # still there after a reload


FAKE_VIP_CLAUDE = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
args = sys.argv[1:]
log = Path(__file__).with_name("vip-calls.txt")
log.write_text(log.read_text() + "x" if log.exists() else "x")
assert "--allowedTools" in args and "Bash" not in args[args.index("--allowedTools") + 1]     # Microsoft 365 search only
found = [{"kind": "mail", "from": "Mia Hale <mia@client.example>", "subject": "Steering pack", "sent": "2026-10-08T08:00+04:00",
          "link": "https://outlook.office365.com/owa/?ItemID=s1", "sensitivity": "normal", "gist": "Wants the steering pack today."}]
print(json.dumps({"type": "result", "result": "Here they are: " + json.dumps(found)}))
'''


class VipLiveTests(unittest.TestCase):
    """BL-99: the live server checks on start-up and on its timer (a stub Claude), serves the alerts, Seen clears one,
    and the checks stop with the server."""

    def test_timer_route_seen_and_stop(self):
        import time
        import urllib.request
        from test_live_server import free_port
        v = vip_vault()
        try:
            settings(v, lambda d: d["vip"].__setitem__("check_minutes", 0.02))                # every ~1 s
            fast_checks(v)
            check_since(v)
            fake = v.root / "fake_vip.py"
            fake.write_text(FAKE_VIP_CLAUDE)
            fake.chmod(0o755)
            port = free_port()
            base = f"http://127.0.0.1:{port}"
            proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(port), "CREAITE_CLAUDE": str(fake),
                                         "CREAITE_NOW": "2026-10-08 09:30", "CREAITE_TZ_OFFSET": TZ},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(100):
                    try:
                        urllib.request.urlopen(base + "/health", timeout=1)
                        break
                    except OSError:
                        time.sleep(0.1)
                import re
                html = urllib.request.urlopen(base + "/").read().decode()
                token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

                def post(path, body):
                    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                                                 headers={"Content-Type": "application/json", "X-Creaite-Token": token})
                    with urllib.request.urlopen(req, timeout=30) as r:
                        return json.loads(r.read())
                calls = v.root / "vip-calls.txt"
                for _ in range(80):
                    if calls.exists() and len(calls.read_text()) >= 2:
                        break
                    time.sleep(0.1)
                self.assertGreaterEqual(len(calls.read_text()), 2)                            # start-up, then the timer
                got = post("/api/vip", {})
                self.assertEqual([(a["who"], a["found"]) for a in got["alerts"]], [("Mia Hale", "start-up")])
                self.assertIsNotNone(got["last_check"])
                self.assertEqual(post("/api/vip/seen", {"ids": [got["alerts"][0]["id"]]})["seen"], 1)
                time.sleep(1.5)                                                               # another check: not alerted again
                self.assertEqual(post("/api/vip", {})["alerts"], [])
            finally:
                proc.terminate()
                proc.wait(timeout=10)
            time.sleep(1.5)                                                                   # a check already started may finish
            n = len(calls.read_text())
            time.sleep(2.5)
            self.assertEqual(len(calls.read_text()), n)                                       # no new checks: stopped with the server
        finally:
            v.cleanup()



class PrepTests(unittest.TestCase):
    """BL-98 part 1: the calendar keeps the invite (never a join link, never a confidential body), and the brief ranks
    what the invite makes relevant first, with reasons, losing nothing."""

    @classmethod
    def setUpClass(cls):
        from datetime import date, timedelta
        from test_dashboard import populate
        from test_insight import chrome
        cls.v = v = Vault()
        populate(v)
        today, tomorrow = date.today(), date.today() + timedelta(days=1)
        cls.today, cls.tomorrow = today.isoformat(), tomorrow
        f = v.root / "system/staging/drafts/calendar.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"days": {
            today.isoformat(): [
                {"id": "t1", "start": "09:00", "end": "10:00", "title": "ABC weekly", "teams": True, "organiser": "Jane Doe",
                 "organiser_email": "jane@client.example", "recurrence": "weekly",
                 "body": "<p>Agenda</p><ol><li>Test licences</li><li>Readiness for the UAT start</li></ol>"
                         "<div>Microsoft Teams meeting</div><a href='https://teams.microsoft.com/l/meetup-join/1'>Join</a>"
                         "<div>Meeting ID: 312 456 789</div><div>Passcode: aB3cD4</div>",
                 "attendees": [{"name": "Sara Example", "email": "sara@example.com", "type": "required", "response": "accepted"},
                               {"name": "Omar Ali <omar@def.example>", "type": "optional"}],
                 "attachments": [{"name": "UAT plan v2.xlsx"}]},
                {"id": "t2", "start": "11:00", "end": "11:30", "title": "ABC board prep", "sensitivity": "confidential",
                 "body": "Board pack secrets", "attendees": ["ceo@example.com"]},
                {"id": "t3", "start": "15:00", "end": "15:30", "title": "Dentist", "private": True}],
            tomorrow.isoformat(): [{"id": "m1", "start": "10:00", "end": "10:30", "title": "ABC test licences"}]}}))
        now = f"{today.isoformat()} 08:00"
        cls.saved_out = run(v, "sweep.py", "calendar", str(f), now=now).stdout
        cls.saved = json.loads((v.root / "system/staging/calendar.json").read_text())
        run(v, "build_dashboard.py", now=now)
        import re
        html = (v.root / "dashboard.html").read_text()
        cls.html = html
        cls.D = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        cls.out, cls.errors = chrome(v, """const out={}; go("today"); renderToday();
          const ev=prepTimed().find(e=>e.title==="ABC weekly"); openPrep(ev,TODAY);
          const secs=[...document.querySelectorAll('#prepBody .prepsec')];
          out.acts=[...secs[0].querySelectorAll('.wlist>div')].map(d=>[d.dataset.open,(d.querySelector('.prepwhy')||{}).textContent||""]);
          out.nOpen=A.filter(x=>x.p==="ABC"&&CREAITE.open(x)).length;
          out.inv=document.querySelector('#prepDlg details.prepinv').textContent;
          out.intro=document.getElementById('prepFacts').textContent;
          document.getElementById('prepDlg').close(); renderToday();
          const wk=document.querySelector('.wkchip[data-prepgoday]'); out.tomorrowLink=!!wk; if(wk){ const day=wk.dataset.prepgoday, ev=(D.calendar.days[day]||[]).find(x=>!x.all_day&&`${day}|${x.start}|${x.title}`===wk.dataset.prepgo); openPrep(ev,day); await new Promise(r=>setTimeout(r,50)); out.tomorrowWhen=document.getElementById('prepWhen').textContent; }   /* the header is a component: it redraws a moment later */
          window.OUT=out;""", "prep-rank")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_calendar_keeps_the_invite_but_no_join_details(self):
        ev = self.saved["days"][self.today][0]
        self.assertIn("Test licences", ev["body"])
        self.assertIn("Readiness for the UAT start", ev["body"])
        for gone in ("teams.microsoft.com", "Meeting ID", "Passcode", "312 456 789", "aB3cD4", "Join"):
            self.assertNotIn(gone, json.dumps(self.saved))
        self.assertEqual([(a["name"], a["type"], a["response"]) for a in ev["attendees"]],
                         [("Sara Example", "required", "accepted"), ("Omar Ali", "optional", "none")])
        self.assertEqual((ev["organiser_email"], ev["recurrence"], ev["attachments"]),
                         ("jane@client.example", "weekly", ["UAT plan v2.xlsx"]))

    def test_a_confidential_event_keeps_no_body_and_a_private_one_is_gone(self):
        conf = self.saved["days"][self.today][1]
        self.assertEqual(conf["sensitivity"], "confidential")
        self.assertNotIn("body", conf)
        self.assertNotIn("attendees", conf)
        self.assertNotIn("Board pack", json.dumps(self.saved))
        self.assertEqual(len(self.saved["days"][self.today]), 2)                                # the private one dropped
        self.assertFalse(any("Dentist" in k for k in self.D["prep"]["meetings"]))              # so no Prep for it

    def test_the_page_embeds_bodies_only_in_todays_prep(self):
        for evs in self.D["calendar"]["days"].values():
            for ev in evs:
                self.assertFalse({"body", "attendees", "attachments", "organiser_email"} & set(ev))
        m = self.D["prep"]["meetings"]["09:00|ABC weekly"]
        self.assertIn("Test licences", m["invite"]["body"])
        self.assertTrue(self.D["prep"]["meetings"]["11:00|ABC board prep"]["invite"]["confidential"])

    def test_ranking_puts_the_relevant_first_with_reasons(self):
        rank = self.D["prep"]["meetings"]["09:00|ABC weekly"]["rank"]
        self.assertIn("“test", rank["raid"]["ABC-004"][1])                                     # Test licences not ordered
        self.assertIn("invite names the UAT start milestone", rank["actions"]["ABC-A-002"][1] + rank["actions"]["ABC-A-001"][1])
        self.assertIn("Sara Example is invited", rank["actions"]["ABC-A-002"][1])
        self.assertGreater(rank["actions"]["ABC-A-002"][0], rank["actions"]["ABC-A-001"][0])  # invited owner and milestone

    def test_title_only_fallback_for_tomorrow(self):
        key = next(k for k in self.D["prep"]["meetings"] if k.endswith("|10:00|ABC test licences"))
        rank = self.D["prep"]["meetings"][key]["rank"]
        self.assertEqual(list(rank.get("raid", {})), ["ABC-004"])
        self.assertEqual(rank["raid"]["ABC-004"][1], "invite mentions “test licences”")

    def test_the_brief_in_chrome(self):
        o = self.out
        self.assertEqual(self.errors, [])
        self.assertNotIn("error", o, o)
        self.assertEqual(o["acts"][0][0], "actions:ABC-A-002")
        self.assertIn("Sara Example is invited", o["acts"][0][1])
        self.assertEqual(len(o["acts"]), o["nOpen"])                                           # nothing lost
        self.assertIn("Invited: Sara Example", o["inv"])
        self.assertIn("Attached: UAT plan v2.xlsx", o["inv"])
        self.assertIn("the invite points to", o["intro"])                                     # BL-286 A: the facts line
        self.assertTrue(o["tomorrowLink"])
        self.assertTrue(o["tomorrowWhen"].startswith("Tomorrow · "), o["tomorrowWhen"])          # BL-286 A: the date line
        self.assertIn(" · 10:00 – ", o["tomorrowWhen"])



FAKE_PREP_CLAUDE = r'''#!/usr/bin/env python3
import json, sys, time
from pathlib import Path
args = sys.argv[1:]
message = args[args.index("--") + 1]
allowed = args[args.index("--allowedTools") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-p"})
assert message.startswith("creaite prep page") and "Write(" not in allowed      # read-only research
if Path(__file__).with_name("slow-prep").exists():
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Started."}]}})
    time.sleep(30)
    sys.exit(0)
out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "r1", "name": "Read",
     "input": {"file_path": "projects/ABC Example Programme/minutes/x.docx"}}]}})
out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "r1", "content": "ok"}]}})
reply = {"about": "The weekly ABC check-in: test licences and readiness for UAT.",
         "item_reasons": {"ABC-003": "UAT readiness depends on data access"},
         "notes": [{"text": "Licences quote expected Friday", "source": "Email · From: Jane Doe <jane@client.example> · Subject: Licences · Sent: 2026-10-06", "date": "2026-10-06"},
                   {"text": "Budget line agreed", "source": "projects/ABC Example Programme/documents/Budget.xlsx", "date": "2026-09-30"}],
         "questions": [], "m365": "searched"}
out({"type": "assistant", "message": {"content": [{"type": "text", "text": json.dumps(reply)}]}})
out({"type": "result", "result": "done", "session_id": "sess-p"})
'''


class PrepPageTests(unittest.TestCase):
    """BL-98 part 2: the Prep page through the live server: a self-contained, internal page in the Agendas folder;
    a second press replaces only creaite's own unchanged page (with a backup); an edited one gets a number; Stop."""

    @classmethod
    def setUpClass(cls):
        import time
        import urllib.request
        from datetime import date
        from test_dashboard import populate
        from test_live_server import free_port
        cls.v = v = Vault()
        populate(v)
        cls.day = date.today().isoformat()
        (v.root / "system/staging/calendar.json").write_text(json.dumps({"fetched": f"{cls.day} 07:00", "days": {cls.day: [
            {"id": "t1", "start": "09:00", "end": "10:00", "title": "ABC weekly", "where": "Teams", "teams": True,
             "organiser": "Jane Doe", "all_day": False, "private": False, "sensitivity": "normal",
             "body": "Agenda: test licences; UAT readiness", "attendees": [{"name": "Sara Example", "type": "required",
                                                                            "response": "accepted"}]}]}}))
        fake = v.root / "fake_prep.py"
        fake.write_text(FAKE_PREP_CLAUDE)
        fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        import re
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body, stream=False):
        import urllib.request
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        r = urllib.request.urlopen(req, timeout=60)
        if stream:
            return r
        with r:
            return json.loads(r.read())

    def events(self, r):
        out = []
        with r:
            for line in r:
                line = line.decode().strip()
                if line.startswith("data: "):
                    out.append(json.loads(line[6:]))
                    if out[-1]["type"] == "done":
                        break
        return out

    def press(self, run):
        evs = self.events(self.post("/api/prep/page", {"key": "09:00|ABC weekly", "run": run}, stream=True))
        return evs, self.post("/api/prep/build", {"run": run})

    def test_1_page_built_internal_self_contained_in_agendas(self):
        evs, got = self.press("p-test-1")
        self.assertIn("step", [e["type"] for e in evs])
        self.assertTrue(got["ok"], got)
        self.assertEqual(got["path"], f"projects/ABC Example Programme/agendas/{self.day} Prep - ABC weekly.html")
        page = (self.v.root / got["path"]).read_text()
        self.assertEqual(page, got["html"])
        self.assertIn("Internal", page.split("\n")[1])                                       # in its first lines
        self.assertIn('<span class="internal">Internal</span>', page)
        for external in ("<script", "<link", 'src="http', "@import", "url("):
            self.assertNotIn(external, page)                                                  # one file, nothing fetched
        self.assertIn("@media print", page)
        self.assertIn("prefers-color-scheme:dark", page)
        self.assertIn("The weekly ABC check-in", page)
        self.assertIn("Licences quote expected Friday", page)
        self.assertIn("— Email · From: Jane Doe", page)                                       # every note cites its source
        self.assertIn("project document (internal)", page)                                    # documents/ labelled
        self.assertIn("Nothing found.", page)                                                 # no questions came back
        self.assertIn(f"http://127.0.0.1:{self.port}/#work=raid&amp;p=ABC&amp;item=ABC-003", page)   # links back (BL-126: the Urgent risk; ABC-004 is neither urgent nor due)
        self.assertNotIn("item=ABC-004", page)
        self.assertIn("1 other open item is not listed", page)
        self.assertIn("UAT readiness depends on data access", page)                           # Claude's meaning-based reason
        written = [p for p in self.v.root.rglob(f"*Prep - ABC weekly*.html")]
        self.assertEqual(len(written), 1)                                                     # nowhere else
        again = self.post("/api/prep/open", {"path": got["path"]})
        self.assertEqual(again["html"], page)
        self.assertNotIn("![", page)                                                           # Current state as plain text

    def test_2_second_press_replaces_own_page_with_backup_and_edited_gets_number(self):
        _, first = self.press("p-test-2a")
        _, second = self.press("p-test-2b")
        self.assertEqual(second["path"], first["path"])                                       # replaced
        backups = list((self.v.root / "system/backups/files").glob("*Prep - ABC weekly.html"))
        self.assertGreaterEqual(len(backups), 1)
        f = self.v.root / second["path"]
        f.write_text(f.read_text() + "<!-- Alan's notes -->")                                 # Alan edits it
        _, third = self.press("p-test-2c")
        self.assertTrue(third["path"].endswith(f"{self.day} Prep - ABC weekly (2).html"), third["path"])
        self.assertIn("Alan's notes", f.read_text())                                          # left alone

    def test_3_open_refuses_other_files(self):
        import urllib.error
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post("/api/prep/open", {"path": "system/config/settings.json"})
        self.assertEqual(e.exception.code, 403)
        e.exception.close()

    def test_4_stop_writes_nothing(self):
        import threading
        import time
        (self.v.root / "slow-prep").write_text("")
        try:
            before = sorted(p.name for p in (self.v.root / "projects/ABC Example Programme/agendas").glob("*")) \
                if (self.v.root / "projects/ABC Example Programme/agendas").exists() else []
            got = {}
            t = threading.Thread(target=lambda: got.update(evs=self.events(self.post(
                "/api/prep/page", {"key": "09:00|ABC weekly", "run": "p-test-stop"}, stream=True))))
            t.start()
            time.sleep(1.5)
            self.assertTrue(self.post("/api/ask/stop", {"run": "p-test-stop"})["ok"])
            t.join(timeout=20)
            self.assertIn("stopped", [e["type"] for e in got["evs"]])
            built = self.post("/api/prep/build", {"run": "p-test-stop"})
            self.assertFalse(built["ok"])
            self.assertIn("no page was written", built["message"])
            after = sorted(p.name for p in (self.v.root / "projects/ABC Example Programme/agendas").glob("*")) \
                if (self.v.root / "projects/ABC Example Programme/agendas").exists() else []
            self.assertEqual(after, before)
        finally:
            (self.v.root / "slow-prep").unlink()


class PrepPageStaticTests(unittest.TestCase):
    """BL-98 part 2: without the live server the Prep page button is refused, and nothing opens."""

    def test_refused_without_the_live_server(self):
        from datetime import date
        from test_dashboard import populate
        from test_insight import chrome
        v = Vault()
        try:
            populate(v)
            day = date.today().isoformat()
            (v.root / "system/staging/calendar.json").write_text(json.dumps({"fetched": f"{day} 07:00", "days": {day: [
                {"id": "t1", "start": "09:00", "end": "10:00", "title": "ABC weekly", "all_day": False, "private": False}]}}))
            run(v, "build_dashboard.py", now=f"{day} 08:00")
            out, errors = chrome(v, """const HOVER=true; const mm0=window.matchMedia.bind(window); window.matchMedia=q=>/hover: *hover/.test(q)?{matches:HOVER,media:q,addEventListener(){},removeEventListener(){},addListener(){},removeListener(){}}:mm0(q);   /* headless Linux Chrome reports no hover: the peek needs it (hover.js canHover) */
              let opened=0; window.open=()=>{ opened++; return null; }; let fetched=0; const f0=window.fetch; window.fetch=(...a)=>{ fetched++; return f0(...a); };
              go("today"); renderToday(); openPrep(prepTimed()[0],TODAY); const b=document.querySelector('[data-prepview]');
              const title=b.dataset.tip; b.click();   /* BL-161: the one tooltip */ await new Promise(r=>setTimeout(r,50));
              document.getElementById('prepDlg').close(); SA().prep_pages={'09:00|ABC weekly':'projects/x/agendas/a.html'}; renderToday();
              document.querySelector('#dayMeets .dmti').dispatchEvent(new PointerEvent("pointerover",{bubbles:true,pointerType:"mouse"})); await new Promise(r=>setTimeout(r,900));   /* #140, #111: the title's peek, after a rest (CARD_OPEN) */
              const g=document.querySelector('#dayMeets .dmpop [data-prepgo]'); g.click(); await new Promise(r=>setTimeout(r,50));   /* BL-287: shown, disabled */
              window.OUT={title, opened, fetched, said:document.body.textContent.includes("The Prep page needs the live server"),
                go:[g.getAttribute('aria-disabled'), g.dataset.tip, location.hash.startsWith('#prep=')]};""", "prep-static")
            self.assertEqual(errors, [])
            self.assertEqual(out, {"title": "Needs the live server", "opened": 0, "fetched": 0, "said": True,
                                   "go": ["true", "Needs the live server", False]})
        finally:
            v.cleanup()



class VipEverywhereTests(unittest.TestCase):
    """BL-99 follow-ups: the VIP chip and filter in Work, the Draft email note, the vip_overdue early warning, the
    weekly report's VIP facts and the weekly reminder's note."""

    @classmethod
    def setUpClass(cls):
        import re
        from test_dashboard import d, populate
        from test_insight import chrome
        from test_tracker import action
        cls.v = v = Vault()
        populate(v)
        (v.root / "projects/_portfolio/people-register.md").write_text(
            "# People register\n\n## People\n\n| Full name | Email | Aliases | Organisation | Role | Hidden | VIP |\n"
            "|---|---|---|---|---|---|---|\n| Sara Example | sara@example.com | Sara | Client | Sponsor | | client |\n")
        v.propose("vip", [action(30, description="Send the data access letter", owner="Sara Example", due_date="2026-10-06",   # two days before NOW (the build runs at NOW)
                                 source="projects/ABC Example Programme/minutes/x.docx — Actions")])
        v.run("apply")
        (v.root / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
        record(v, [{"kind": "mail", "from": "Sara Example <sara@example.com>", "subject": "[ABC] steer", "sent": "2026-10-08 08:00",
                    "link": "s1", "gist": "Wants a steer on UAT."}])
        run(v, "build_dashboard.py")
        cls.D = json.loads(re.search(r'id="data">(.*?)</script>', (v.root / "dashboard.html").read_text(), re.S)
                           .group(1).replace("<\\/", "</"))
        out = run(v, "report.py", "weekly-data", "ABC").stdout
        cls.weekly = json.loads(out[out.index("{"):])                                        # after any "Note:" lines
        cls.out, cls.errors = chrome(v, """const out={}; go("work"); WT="actions"; applyView("open"); renderWork();
          const rows=()=>[...document.querySelectorAll('#workTbl tbody tr')];
          out.chip=rows().filter(r=>/\\bVIP\\b/.test(r.textContent)).length; out.all=rows().length;
          FX.vip.add("yes"); workChanged(); out.filtered=rows().map(r=>r.querySelector('td[data-f="o"]').textContent.trim()); out.hash=location.hash;
          FX.vip.clear(); workChanged();
          openDraftEmail("Sara Example"); out.note=document.getElementById('deBody').textContent; document.getElementById('deDlg').close();
          go("today"); renderToday(); out.rem=[...document.querySelectorAll('#attnList li.rem')].map(l=>l.textContent).filter(t=>t.includes('Example Programme weekly'));
          go("settings","warnings"); out.wsig=!!document.querySelector('[data-wk="vip_overdue.on"]');
          window.OUT=out;""", "vip-everywhere")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_early_warning_and_reminder_data(self):
        w = [x for x in self.D["warnings"] if x["sig"] == "vip_overdue"]
        self.assertEqual([(x["id"], x["who"]) for x in w], [("ABC-A-006", "Sara Example")])
        self.assertIn("owned by Sara Example", w[0]["text"])
        self.assertNotIn("VIP", w[0]["text"])                                                  # BL-288: unlabelled
        weekly = [r for r in self.D["reminders"] if r["id"].startswith("weekly:") and r["id"].endswith(":ABC")]
        self.assertEqual(weekly[0].get("vip"), 1)

    def test_weekly_report_data(self):
        self.assertEqual(self.weekly["vip"]["owners"], [["Sara Example", "client"]])
        self.assertEqual([(a["who"], a["subject"]) for a in self.weekly["vip"]["unseen_alerts"]], [("Sara Example", "[ABC] steer")])
        self.assertNotIn("UAT", json.dumps(self.weekly["vip"]))                                # no gist or text in the report data

    def test_work_draft_email_today_settings(self):
        o = self.out
        self.assertEqual(self.errors, [])
        self.assertNotIn("error", o, o)
        self.assertEqual(o["chip"], 0)                                                         # BL-288: no chip
        self.assertTrue(o["filtered"] and all("Sara" in t for t in o["filtered"]), o["filtered"])
        self.assertLess(len(o["filtered"]), o["all"])
        self.assertIn("vip=yes", o["hash"])
        self.assertNotIn("VIP", o["note"])                                                     # BL-288: the note is dropped
        self.assertTrue(o["rem"] and "1 message about it not yet seen" in o["rem"][0], o["rem"])
        self.assertNotIn("VIP", o["rem"][0])
        self.assertTrue(o["wsig"])



class TimezoneTests(unittest.TestCase):
    """BL-107: the script converts Microsoft 365's times to the laptop's time zone (set here with TZ) and files each
    meeting under its local date; "HH:MM" already local is unchanged."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.f = self.v.root / "system/staging/drafts/calendar.json"
        self.f.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.v.cleanup()

    def save(self, days, tz="Asia/Dubai"):
        self.f.write_text(json.dumps({"days": days}))
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/sweep.py"), "calendar", str(self.f)],
                           cwd=self.v.root, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": NOW, "TZ": tz})
        return r.stdout, json.loads((self.v.root / "system/staging/calendar.json").read_text())["days"]

    def test_utc_late_evening_lands_on_the_next_local_day(self):
        out, days = self.save({"2026-10-08": [
            {"id": "u1", "title": "Late call", "start": "2026-10-08T22:30:00Z", "end": "2026-10-08T23:00:00Z"}]})
        self.assertEqual([(e["start"], e["end"]) for e in days["2026-10-09"]], [("02:30", "03:00")])   # +04:00
        self.assertNotIn("2026-10-08", days)

    def test_datetime_and_timezone_pairs(self):
        out, days = self.save({"2026-10-08": [
            {"id": "p1", "title": "Graph UTC", "start": {"dateTime": "2026-10-08T05:00:00.0000000", "timeZone": "UTC"},
             "end": {"dateTime": "2026-10-08T05:30:00.0000000", "timeZone": "UTC"}},
            {"id": "p2", "title": "London", "start": {"dateTime": "2026-10-08T09:00:00", "timeZone": "GMT Standard Time"},
             "end": {"dateTime": "2026-10-08T10:00:00", "timeZone": "Europe/London"}},
            {"id": "p3", "title": "Across midnight", "start": "2026-10-08T19:30:00Z", "end": "2026-10-08T21:00:00Z"}]})
        got = {e["title"]: (e["start"], e["end"]) for e in days["2026-10-08"]}
        self.assertEqual(got, {"Graph UTC": ("09:00", "09:30"), "London": ("12:00", "13:00"),
                               "Across midnight": ("23:30", "23:59")})

    def test_plain_local_times_and_unreadable_ones(self):
        out, days = self.save({"2026-10-08": [
            {"id": "l1", "title": "Already local", "start": "09:15", "end": "10:00"},
            {"id": "x1", "title": "Garbled", "start": "soon", "end": "later"},
            {"title": "Holiday", "all_day": True}]}, tz="Europe/London")
        self.assertEqual([(e["title"], e["start"]) for e in days["2026-10-08"]], [("Holiday", ""), ("Already local", "09:15")])
        self.assertIn("Garbled (time not readable)", out)

    def test_follows_the_laptop_zone(self):
        _, dubai = self.save({"2026-10-08": [{"id": "z", "title": "M", "start": "2026-10-08T08:00:00Z", "end": "2026-10-08T09:00:00Z"}]})
        _, london = self.save({"2026-10-08": [{"id": "z", "title": "M", "start": "2026-10-08T08:00:00Z", "end": "2026-10-08T09:00:00Z"}]},
                              tz="Europe/London")
        self.assertEqual((dubai["2026-10-08"][0]["start"], london["2026-10-08"][0]["start"]), ("12:00", "09:00"))


if __name__ == "__main__":
    unittest.main()
