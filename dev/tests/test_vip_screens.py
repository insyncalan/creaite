"""BL-288 part 2 and BL-296: who Alan follows is private on screen, and each followed person's message on Today can be
dismissed or made into a work item.

BL-288: no screen says "VIP" except the person form's own field and Settings › Capture › VIP alerts. Checked on BL-254's
goldens (quick) and on every snapshot screen of a vault where someone is followed, has sent a message and owns an overdue
item (Chrome), plus the window title, the rail badge's name, the notification, the Work filter and the Draft email.
BL-296: Dismiss with Undo; Create work item opens the new-item peek filled from the message's references, Cancel leaves the
message, Save stages and applies it and clears the row; a message with no project asks for one; "Draft from the message" is
refused for a confidential message.

Run: python3 dev/tests/test_vip_screens.py
"""
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_sweep_alerts import record, run  # noqa: E402
from test_tracker import action  # noqa: E402

WORD = re.compile(r"\bVIP\b")
SNAPSHOTS = HERE / "snapshots"


def without_allowed(html):
    """The HTML without the two places allowed to say VIP: Settings › VIP alerts (#vipSet) and the person form's field."""
    m = re.search(r'<div[^>]*\bid="vipSet"', html)
    if m:
        depth, i = 0, m.start()
        for t in re.finditer(r"<(/?)div\b[^>]*>", html[m.start():]):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                i = m.start() + t.end()
                break
        html = html[:m.start()] + html[i:]
    return re.sub(r'<(label|select)[^>]*class="pdvip"[^>]*>.*?</\1>', "", html, flags=re.S)


def says_vip(html):
    m = WORD.search(without_allowed(html))
    return None if not m else html[max(0, m.start() - 100):m.end() + 60]


class Goldens(unittest.TestCase):
    """Quick: BL-254's goldens say VIP only in the two allowed places."""

    def test_no_golden_says_vip(self):
        files = sorted(SNAPSHOTS.glob("*.html"))
        self.assertTrue(files)
        for f in files:
            with self.subTest(f.name):
                self.assertIsNone(says_vip(f.read_text(encoding="utf-8")))

    def test_the_check_finds_one(self):
        self.assertIsNotNone(says_vip('<p>Owned by a VIP</p><div class="card" id="vipSet"><h2>VIP alerts</h2></div>'))
        self.assertIsNone(says_vip('<div class="card" id="vipSet"><div><h2>VIP alerts</h2></div></div>'
                                   '<label for="pd_vip" class="pdvip">VIP</label>'))


TODAY = date.today().isoformat()
REGISTER = ("# People register\n\n## People\n\n| Full name | Email | Aliases | Organisation | Role | Hidden | VIP |\n"
            "|---|---|---|---|---|---|---|\n| Sara Example | sara@example.com | Sara | Client | Sponsor | | client |\n")
SARA = "Sara Example <sara@example.com>"
MESSAGES = [
    {"kind": "mail", "from": SARA, "subject": "[ABC] Steer on UAT", "sent": f"{TODAY} 08:10", "link": "https://x/m1",
     "gist": "Wants a steer on UAT."},
    {"kind": "mail", "from": SARA, "subject": "[ABC] Licence count", "sent": f"{TODAY} 08:20", "link": "https://x/m2"},
    {"kind": "mail", "from": SARA, "subject": "Lunch plans", "sent": f"{TODAY} 08:30", "link": "https://x/m3"},
    {"kind": "mail", "from": SARA, "subject": "[ABC] Personal note", "sent": f"{TODAY} 08:40", "link": "https://x/m4",
     "sensitivity": "confidential"},
]


def followed_vault(v):
    populate(v)
    (v.root / "projects/_portfolio/people-register.md").write_text(REGISTER, encoding="utf-8")
    v.propose("vip", [action(30, description="Send the data access letter", owner="Sara Example", due_date="2026-01-06",
                             source="projects/ABC Example Programme/minutes/x.docx — Actions")])
    v.run("apply")
    (v.root / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
    record(v, MESSAGES)
    f = v.root / "system/staging/drafts/sweep.json"
    f.write_text(json.dumps({"items": [{"table": "actions", "values": {
        "project": "ABC", "description": "Confirm the UAT window", "owner": "Alan Carter",
        "source": f"Email · From: {SARA} · Subject: [ABC] UAT · Sent: {TODAY} 07:00 · Link: https://x/m9"}}]}))
    run(v, "sweep.py", "stage", str(f))
    run(v, "build_dashboard.py")


class Screens(LiveBrowserCase):
    """BL-288: every snapshot screen, and the other surfaces, with someone followed."""
    shared_server = True

    @classmethod
    def load(cls, v):
        followed_vault(v)

    def test_no_screen_says_vip(self):
        from test_snapshots import SCREENS
        b = self.b
        for name, (go, ready, region) in SCREENS.items():
            with self.subTest(name):
                b.eval("closePanel(); typeof closeChat==='function' && closeChat(); "
                       "document.getElementById('cmdk').open && document.getElementById('cmdk').close(); go('today')")
                go(b) if callable(go) else b.eval(go)
                b.wait(ready, 15)
                b.pump(0.4)
                self.assertIsNone(says_vip(b.eval(f"(document.querySelector({region!r})||{{}}).outerHTML||''")))
        b.eval("go('person','Sara Example')")
        b.pump(0.3)
        self.assertIsNone(says_vip(b.eval("document.getElementById('v-person').outerHTML")))

    def test_today_title_badge_notification_filter_and_email(self):
        b = self.b
        o = b.eval("""(()=>{ const out={}; go('today'); renderToday();
          const msgs=[...document.querySelectorAll('#tdList>li.td-message')];   /* BL-319: messages are rows of To decide */
          out.head=document.getElementById('hTd').firstChild.textContent.trim(); out.rows=msgs.length;
          out.first=msgs[0].textContent.replace(/\\s+/g,' ')+' '+msgs[0].querySelector('.tdtag').textContent;
          out.buttons=[...msgs[0].querySelectorAll('button')].map(x=>[x.getAttribute('aria-label').split(':')[0],x.dataset.tip]);
          out.title=document.title; out.badge=document.getElementById('vipBadge').getAttribute('aria-label');
          const seen=[]; window.Notification=class{ constructor(t,o){ seen.push([t,o.body]); } static get permission(){ return 'granted'; } };
          vipNotify(VIPS().map(a=>({...a,id:a.id+'-again'}))); out.note=seen[0];
          out.filter=FDEFS.actions.find(d=>d[0]==='vip'); out.filter=[out.filter[1],...out.filter[2]().map(x=>x[1])];
          out.warn=WSIG.find(w=>w[0]==='vip_overdue')[1];
          openDraftEmail('Sara Example'); out.email=document.getElementById('deDlg').outerHTML; document.getElementById('deDlg').close();
          out.rem=[...document.querySelectorAll('#attnList li.rem')].map(l=>l.textContent).join(' | ');
          return out; })()""")
        self.assertEqual(o["head"], "To decide")
        self.assertEqual(o["rows"], 4)
        self.assertNotIn("VIP", o["first"])
        self.assertEqual(o["buttons"], [["Create work item from", "Make a work item"], ["Dismiss", "Dismiss"]])   # icons, named
        self.assertTrue(re.match(r"^\(4\) creaite", o["title"]), o["title"])
        self.assertEqual(o["badge"], "4 messages to see first")
        self.assertEqual(o["note"][0], "Sara Example")
        self.assertEqual(o["filter"], ["People I follow", "Owned by someone I follow", "Not followed"])
        self.assertEqual(o["warn"], "Overdue item owned by someone you follow closely")
        self.assertIsNone(says_vip(o["email"]))
        self.assertNotIn("VIP", o["rem"])


class AlertActions(LiveBrowserCase):
    """BL-296: Dismiss and Undo, Create work item (Cancel, Save, no project), and Draft refused for a confidential message."""

    @classmethod
    def load(cls, v):
        followed_vault(v)

    def row(self, subject):
        return self.b.eval(f"""(()=>{{ if(!EXPAND.has('td')){{ EXPAND.add('td'); renderToday(); }}   /* BL-319: every row of To decide shown */
          const li=[...document.querySelectorAll('#tdList>li.td-message')].find(l=>l.textContent.includes({json.dumps(subject)}));
          return li?li.dataset.td.slice(2):null; }})()""")

    def test_dismiss_and_undo(self):
        b = self.b
        b.eval("go('today')")
        aid = self.row("[ABC] Steer on UAT")
        self.assertTrue(aid)
        b.click(f'#tdList [data-alertdo="dismiss"][data-id="{aid}"]')
        b.wait(f"!document.querySelector('#tdList li[data-td=\"al{aid}\"]')")
        self.assertEqual(b.eval("document.getElementById('snackT').textContent"), "Message dismissed")
        self.assertTrue(b.eval("document.activeElement.matches('#tdList [data-tdact]')"))             # focus stays on the list
        b.click("#snackU")
        b.wait(f"document.querySelector('#tdList li[data-td=\"al{aid}\"]')")

    def test_create_work_item_cancel_then_save(self):
        b = self.b
        b.eval("go('today')")
        aid = self.row("[ABC] Licence count")
        b.click(f'#tdList [data-alertdo="make"][data-id="{aid}"]')
        b.wait("document.getElementById('panel').classList.contains('on') && document.getElementById('pkAlert') && !document.getElementById('pkAlert').hidden")
        o = b.eval("""(()=>({t:document.getElementById('pkTitle').textContent, p:CUR.draft.p, o:CUR.draft.o, k:CUR.k,
          due:CUR.draft.due, strip:document.getElementById('pkAlert').textContent, focus:document.activeElement.id,
          pressed:document.querySelector('#pkAlert [aria-pressed="true"]').textContent}))()""")
        self.assertEqual((o["t"], o["p"], o["k"], o["due"], o["focus"], o["pressed"]),
                         ("[ABC] Licence count", "ABC", "actions", "", "pkTitle", "Action"))
        self.assertTrue(o["o"])                                                            # Alan, from the identity
        self.assertIn("From Sara Example’s email", o["strip"])
        self.assertNotIn("VIP", o["strip"])
        b.click('#pkAlert [data-alertpeek="cancel"]')                                      # Cancel: the message stays
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.assertTrue(self.row("[ABC] Licence count"))
        b.click(f'#tdList [data-alertdo="make"][data-id="{aid}"]')
        b.wait("document.getElementById('pkAlert') && !document.getElementById('pkAlert').hidden")
        b.click('#pkAlert [data-alerttype="risk"]')                                        # the type switches
        b.wait("CUR && CUR.k==='raid' && CUR.draft.type==='Risk'")
        b.click('#pkAlert [data-alerttype="action"]')
        b.wait("CUR && CUR.k==='actions'")
        b.click('#pkAlert [data-alertpeek="save"]')
        b.wait("A.some(a=>a.t==='[ABC] Licence count')", 20)
        x = b.eval("A.find(a=>a.t==='[ABC] Licence count')")
        self.assertEqual(x["p"], "ABC")
        self.assertIn("Link: https://x/m2", x["src"])
        b.eval("go('today')")
        self.assertIsNone(self.row("[ABC] Licence count"))
        made = json.loads((self.v.root / "system/staging/vip.json").read_text())
        self.assertTrue(next(a for a in made["alerts"] if a["id"] == aid)["made"])

    def test_no_project_asks_for_one_and_confidential_has_no_draft(self):
        b = self.b
        b.eval("go('today')")
        aid = self.row("Lunch plans")
        b.click(f'#tdList [data-alertdo="make"][data-id="{aid}"]')
        b.wait("document.getElementById('pkAlert') && !document.getElementById('pkAlert').hidden")
        self.assertEqual(b.eval("CUR.draft.p"), "")
        self.assertEqual(b.eval("document.querySelector('#pkId [data-pkp=\"p\"]').textContent.trim()"), "Choose a project")
        b.click('#pkAlert [data-alertpeek="save"]')
        b.wait("document.getElementById('pkNote').textContent")
        self.assertTrue(b.eval("document.getElementById('panel').classList.contains('on')"))   # still open, nothing staged
        self.assertFalse(b.eval("CUR.staged"))
        b.click('#pkAlert [data-alertpeek="cancel"]')
        b.wait("!document.getElementById('panel').classList.contains('on')")
        self.assertTrue(self.row("Lunch plans"))
        aid = self.row("[ABC] Personal note")
        b.click(f'#tdList [data-alertdo="make"][data-id="{aid}"]')
        b.wait("document.getElementById('pkAlert') && !document.getElementById('pkAlert').hidden")
        d = b.eval("(()=>{ const x=document.querySelector('#pkAlert [data-alertdraft]'); return [x.getAttribute('aria-disabled'), x.dataset.tip]; })()")
        self.assertEqual(d, ["true", "Not for a confidential message"])


if __name__ == "__main__":
    unittest.main()
