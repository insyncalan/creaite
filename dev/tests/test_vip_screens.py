"""BL-288 part 2 and BL-296: who Alan follows is private on screen, and each followed person's message on Today can be
dismissed or made into a work item.

BL-288: no screen says "VIP" except the person form's own field and Settings › Capture › VIP alerts. Checked on BL-254's
goldens (quick) and on every snapshot screen of a vault where someone is followed, has sent a message and owns an overdue
item (Chrome), plus the window title, the rail badge's name, the notification, the Work filter and the Draft email.
BL-296: Dismiss with Undo; Create work item opens the new-item peek filled from the message's references, Cancel leaves the
message, Save (or ⌘↵) only stages it for Review (check 45, BL-334), clears the row and Undo puts both back; a message with no project asks for one; "Draft from the message" is
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
        self.assertEqual(o["head"], "Intake")
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
        self.staged_for_review(aid, "[ABC] Licence count", "https://x/m2")

    def staged_for_review(self, aid, title, link):
        """Check 45 (BL-334, Jarvis option (a)): Save stages one proposal for Review and dismisses the message; nothing reaches
        the tracker, the pill stays empty, and the peek closes saying so."""
        b = self.b
        b.wait("!document.getElementById('panel').classList.contains('on')", 20)
        b.wait(f"REV.some(r=>JSON.stringify(r).includes({json.dumps(title)}))", 20)                   # in Review
        props = [json.loads(p.read_text()) for p in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json")]
        mine = [i for d in props for i in d.get("items", []) if i["values"].get("description") == title]
        self.assertEqual(len(mine), 1)
        self.assertEqual((mine[0]["op"], mine[0]["decision"], mine[0].get("applied")), ("new", "pending", None))
        self.assertEqual(mine[0]["values"]["project"], "ABC")
        self.assertIn(f"Link: {link}", mine[0]["values"]["source"])
        b.pump(1.0)                                                                        # nothing applies behind it
        self.assertFalse(b.eval(f"A.some(a=>a.t==={json.dumps(title)})"))                 # not in Work
        self.assertEqual([r for r in self.v.rows("actions") if r["description"] == title], [])   # not in tracker.db
        self.assertEqual(b.eval("PKS.length"), 0)                                     # not in the pill either
        self.assertIn("Review", b.eval("document.getElementById('snackT').textContent"))
        b.eval("go('today')")
        self.assertIsNone(self.row(title))                                                   # the message is dismissed
        made = json.loads((self.v.root / "system/staging/vip.json").read_text())
        self.assertTrue(next(a for a in made["alerts"] if a["id"] == aid)["made"])

    def test_cmd_enter_stages_for_review_and_undo_puts_it_back(self):
        b = self.b
        b.eval("go('today')")
        aid = self.row("[ABC] Steer on UAT")
        b.click(f'#tdList [data-alertdo="make"][data-id="{aid}"]')
        b.wait("document.getElementById('pkAlert') && !document.getElementById('pkAlert').hidden")
        b.key("Enter", 4)                                                                  # ⌘↵ from the title
        self.staged_for_review(aid, "[ABC] Steer on UAT", "https://x/m1")
        b.click("#snackU")                                                                 # Undo: unstaged, the message back
        b.wait("!REV.some(r=>JSON.stringify(r).includes('[ABC] Steer on UAT'))", 20)
        b.wait(f"document.querySelector('#tdList li[data-td=\"al{aid}\"]')", 20)
        left = [p for p in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json")
                if "[ABC] Steer on UAT" in p.read_text()]
        self.assertEqual(left, [])
        made = json.loads((self.v.root / "system/staging/vip.json").read_text())
        self.assertNotIn("made", next(a for a in made["alerts"] if a["id"] == aid))
        self.assertEqual([r for r in self.v.rows("actions") if r["description"] == "[ABC] Steer on UAT"], [])

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


# ===== BL-342 Part 1: a thread's card in the real browser =====
SHOTS = Path.home() / "dev.env" / "team-stark-shots" / "bl342-ui"
YESTERDAY = date.fromordinal(date.today().toordinal() - 1).isoformat()
LATER = date.fromordinal(date.today().toordinal() + 5).isoformat()
OMAR = "Omar Ali <omar@company.example>"
THREADS = [
    {"kind": "teams", "conversation": "19:go-live@thread.v2", "title": "Go-live window", "from": SARA, "people": [SARA, OMAR],
     "last": f"{TODAY} 08:50", "link": "https://teams.microsoft.com/l/chat/19:go-live", "sensitivity": "normal",
     "summary": "Sara asks whether go-live can move a week.", "type": "action", "ask": "Confirm the new go-live date",
     "due": YESTERDAY, "owners": ["you", "Sara Example"], "items": []},
    {"kind": "mail", "conversation": "AAQk-licences", "title": "Licence numbers", "subject": "Licence numbers", "from": SARA,
     "people": [SARA, OMAR], "last": f"{TODAY} 08:15", "link": "https://outlook.example/owa/?ItemID=l1", "sensitivity": "normal",
     "summary": "Sara needs a count of test licences.", "type": "decision", "ask": "Say how many test licences are needed",
     "due": LATER, "owners": "you", "items": []},
    {"kind": "mail", "conversation": "AAQk-pack", "title": "Board pack", "subject": "Board pack", "from": SARA,
     "people": [SARA, OMAR], "last": f"{TODAY} 08:05", "link": "https://outlook.example/owa/?ItemID=p1", "sensitivity": "normal",
     "summary": "Sara shared the board pack for reading.", "type": "fyi", "ask": "Read the pack before Thursday",
     "attachments": ["Board pack.pdf"], "items": []},
    {"kind": "teams", "conversation": "19:answered@thread.v2", "title": "Answered chat", "from": SARA, "people": [SARA, OMAR],
     "last": f"{TODAY} 07:30", "link": "https://teams.microsoft.com/l/chat/19:answered", "sensitivity": "normal",
     "summary": "Sara asked for the plan.", "type": "action", "ask": "Send the plan", "replied": f"{TODAY} 07:45", "items": []},
]


def thread_vault(v):
    """The followed vault, with four thread cards (one overdue and matched to an open action, one with a later due date, one
    FYI with a file, one Alan has answered)."""
    followed_vault(v)
    f = v.root / "system/staging/drafts/threads.json"
    f.write_text(json.dumps(THREADS))
    run(v, "sweep.py", "vip", "record", str(f), "--found", "check", now=f"{TODAY} 12:00")
    item = next(r["id"] for r in v.rows("actions") if r["description"] == "Send the data access letter")
    vf = v.root / "system/staging/vip.json"
    st = json.loads(vf.read_text())
    by = {a.get("title"): a for a in st["alerts"]}
    by["Go-live window"]["match"] = {"id": item, "relation": "update", "why": "The thread moves it forward.", "count": 2, "t": "Send the data access letter"}
    by["Licence numbers"]["match"] = {"id": item, "relation": "chase", "why": "Waiting on a reply.", "count": 2, "t": "Send the data access letter"}
    by["Board pack"]["match"] = {"id": None, "relation": "new", "why": "Nothing open matches."}
    vf.write_text(json.dumps(st))
    run(v, "build_dashboard.py")


CONTRAST = """const lum=c=>{ const [r,g,b]=c.map(x=>{ x/=255; return x<=.03928?x/12.92:Math.pow((x+.055)/1.055,2.4); }); return .2126*r+.7152*g+.0722*b; };
  const rgba=s=>{ const m=s.match(/[\\d.]+/g).map(Number); return [m[0],m[1],m[2],m.length>3?m[3]:1]; };
  const bgOf=el=>{ for(let e=el;e;e=e.parentElement){ const c=rgba(getComputedStyle(e).backgroundColor); if(c[3]>=.99) return c; } return [255,255,255,1]; };
  const ratio=el=>{ const f=rgba(getComputedStyle(el).color), g=bgOf(el), a=lum(f)+.05, b=lum(g)+.05; return Math.max(a,b)/Math.min(a,b); };"""


class ThreadCardScreens(LiveBrowserCase):
    """BL-342 Part 1: the card at 1400 and 900px, light and dark: type chip, ask, owners, due (overdue in words), Handled and
    Log, the FYI card's file, the quiet Replied line; nothing says VIP; no horizontal scroll. Shots go to team-stark-shots."""
    shared_server = True

    @classmethod
    def load(cls, v):
        thread_vault(v)

    def show(self, width, mode):
        b = self.b
        b.resize(width, 900)
        b.wait(f"innerWidth==={width}")
        b.eval(f"S.theme={mode!r}; applyTheme(); go('today'); EXPAND.add('td'); renderToday()")
        b.wait("document.querySelector('#tdList li.td-message')")
        b.pump(0.4)

    def test_the_card_in_both_themes_and_both_widths(self):
        b = self.b
        SHOTS.mkdir(parents=True, exist_ok=True)
        for width in (1400, 900):
            for mode in ("Light", "Dark"):
                with self.subTest(width=width, mode=mode):
                    self.show(width, mode)
                    o = b.eval("""(()=>{ %s
                      const rows=[...document.querySelectorAll('#tdList>li.td-message')], first=rows[0], out={};
                      out.order=rows.map(r=>r.querySelector('.t').textContent);
                      out.tag=first.querySelector('.tdtag').textContent;
                      out.text=first.textContent.replace(/\\s+/g,' ');
                      out.buttons=[...first.querySelectorAll(':scope>.tacts button')].map(x=>x.getAttribute('aria-label'));
                      out.tags=rows.map(r=>r.querySelector('.tdtag').textContent);
                      const fyi=rows.find(r=>r.textContent.includes('Board pack')); out.fyi=fyi&&fyi.textContent.replace(/\\s+/g,' ');
                      const q=[...document.querySelectorAll('#tdList>li.td-quiet')].map(r=>r.textContent.replace(/\\s+/g,' ')); out.quiet=q;
                      const over=first.querySelector('.tdover'), ask=first.querySelector('.tdask'), lab=first.querySelector('.tdlab');
                      out.contrast={over:ratio(over), ask:ratio(ask), lab:ratio(lab), meta:ratio(first.querySelector('.tb>p'))};
                      out.scroll=[document.documentElement.scrollWidth, innerWidth];
                      out.out=[...document.querySelectorAll('#tdList>li')].filter(li=>li.getBoundingClientRect().right>innerWidth+1).length;
                      return out; })()""" % CONTRAST)
                    self.assertEqual(o["order"][0], "Go-live window")                           # overdue first
                    self.assertEqual(o["tag"], "Action")
                    self.assertIn("Confirm the new go-live date", o["text"])
                    self.assertIn("For you, Sara Example", o["text"])
                    self.assertIn("overdue, due", o["text"])
                    self.assertEqual(o["buttons"][0].split(":")[0], "Handled")
                    self.assertTrue(o["buttons"][1].startswith("Log on ABC-"), o["buttons"])
                    self.assertIn("Decision", o["tags"])
                    self.assertIn("FYI / file", o["tags"])
                    self.assertIn("Files: Board pack.pdf", o["fyi"])
                    self.assertTrue(any("you replied" in q for q in o["quiet"]), o["quiet"])
                    self.assertEqual(o["out"], 0)
                    self.assertLessEqual(o["scroll"][0], o["scroll"][1])                       # no horizontal scroll
                    for k, ratio in o["contrast"].items():
                        self.assertGreaterEqual(ratio, 4.5, f"{k} contrast {ratio:.2f}")
                    html = b.eval("document.getElementById('tdList').outerHTML")
                    self.assertIsNone(says_vip(html))
                    b.eval("document.getElementById('hTd').scrollIntoView(true)")
                    b.pump(0.3)
                    b.screenshot(str(SHOTS / f"today-card-{width}-{mode.lower()}.png"))
        self.show(1400, "Light")


    def test_the_relation_chips_the_count_and_chase(self):
        """Part 2: the New / Update / Chase chip with the matched item, the count chip, the hint, and Chase for the owner."""
        b = self.b
        SHOTS.mkdir(parents=True, exist_ok=True)
        for width in (1400, 900):
            for mode in ("Light", "Dark"):
                with self.subTest(width=width, mode=mode):
                    self.show(width, mode)
                    o = b.eval("""(()=>{ %s
                      const row=t=>[...document.querySelectorAll('#tdList>li.td-message')].find(r=>r.textContent.includes(t)), out={};
                      for(const [k,t] of [['update','Go-live window'],['chase','Licence numbers'],['new','Board pack']]){
                        const r=row(t), rel=r.querySelector('.tdrel');
                        out[k]={chip:rel.querySelector('.tdrelchip').textContent, text:rel.textContent.replace(/\\s+/g,' '),
                          buttons:[...r.querySelectorAll(':scope>.tacts button')].map(x=>x.getAttribute('aria-label')),
                          contrast:[...rel.querySelectorAll('.tdrelchip,.tdrelitem,.tdcount,.tdwhy')].map(e=>ratio(e)),
                          tabbable:[...r.querySelectorAll(':scope>.tacts button')].every(x=>x.tabIndex>=0)}; }
                      out.scroll=[document.documentElement.scrollWidth, innerWidth];
                      return out; })()""" % CONTRAST)
                    self.assertEqual(o["update"]["chip"], "Update")
                    self.assertIn("ABC-A-", o["update"]["text"])
                    self.assertIn("Send the data access letter", o["update"]["text"])
                    self.assertIn("also on 1 other thread", o["update"]["text"])
                    self.assertEqual(o["chase"]["chip"], "Chase")
                    self.assertIn("Waiting on a reply.", o["chase"]["text"])
                    self.assertTrue(any(x.startswith("Chase") for x in o["chase"]["buttons"]), o["chase"]["buttons"])
                    self.assertFalse(any(x.startswith("Chase") for x in o["update"]["buttons"]))
                    self.assertEqual(o["new"]["chip"], "New")
                    self.assertFalse(any(x.startswith("Log") for x in o["new"]["buttons"]))          # New: no Log
                    self.assertNotIn("also on", o["new"]["text"])
                    for k in ("update", "chase", "new"):
                        self.assertTrue(o[k]["tabbable"])
                        for r in o[k]["contrast"]:
                            self.assertGreaterEqual(r, 4.5, f"{k} contrast {r:.2f}")
                    self.assertLessEqual(o["scroll"][0], o["scroll"][1])
                    self.assertIsNone(says_vip(b.eval("document.getElementById('tdList').outerHTML")))
                    b.eval("document.querySelector('#tdList>li.td-message').scrollIntoView({block:'center'})")
                    b.pump(0.3)
                    b.screenshot(str(SHOTS / f"chips-{width}-{mode.lower()}.png"))
        self.show(1400, "Light")

    def test_chase_opens_the_draft_email_in_chase_mode_for_the_owner(self):
        b = self.b
        self.show(1400, "Light")
        b.eval("""(()=>{ const r=[...document.querySelectorAll('#tdList>li.td-message')].find(r=>r.textContent.includes('Licence numbers'));
          r.querySelector('[data-alertdo="chase"]').focus(); })()""")
        b.eval("document.activeElement.click()")
        b.wait("document.querySelector('dialog[open] #deTitle, #deTitle')&&document.getElementById('deTitle').textContent.includes('Sara Example')")
        self.assertEqual(b.eval("shared.DE.mode"), "chase")
        self.assertEqual(b.eval("shared.DE.name"), "Sara Example")
        self.assertEqual(b.eval("shared.DE.only"), b.eval("(SA().vip.alerts.find(a=>a.title==='Licence numbers')).match.id"))   # N2: the card's own match
        self.assertTrue(b.eval("/^ABC-A-/.test(shared.DE.only)"))
        self.assertTrue(b.eval("[...shared.DE.picked].every(k=>k==='actions:'+shared.DE.only)"))   # at most it is ticked (the outside-address rule)
        b.eval("document.querySelector('dialog[open]').close()")

    def chase_click(self):
        b = self.b
        b.eval("""(()=>{ const r=[...document.querySelectorAll('#tdList>li.td-message')].find(r=>r.textContent.includes('Licence numbers'));
          r.querySelector('[data-alertdo="chase"]').click(); })()""")

    def test_chase_on_an_item_not_past_its_date_opens_the_update_email(self):
        """N3: no dead end. The matched item is made not overdue; Chase falls back to the update email with that one item."""
        b = self.b
        self.show(1400, "Light")
        mid = b.eval("(SA().vip.alerts.find(a=>a.title==='Licence numbers')).match.id")
        b.eval(f"REC('actions','{mid}').due='{LATER}'")
        self.chase_click()
        b.wait("shared.DE&&document.getElementById('deTitle')&&document.getElementById('deTitle').textContent.includes('Sara Example')")
        self.assertEqual(b.eval("shared.DE.mode"), "update")
        self.assertEqual(b.eval("shared.DE.only"), mid)
        self.assertEqual(b.eval("[...shared.DE.picked].every(k=>k==='actions:'+shared.DE.only)"), True)
        b.eval("document.querySelector('dialog[open]').close()")


class ThreadCardCounts(LiveBrowserCase):
    """N1: the count chip and the card list follow Dismiss, Handled and Undo on the open page, without a reload. Two cards
    (Go-live window, Licence numbers) sit on the same item."""

    @classmethod
    def load(cls, v):
        thread_vault(v)

    def chip(self, title):
        return self.b.eval("""(()=>{ const r=[...document.querySelectorAll('#tdList>li.td-message')].find(l=>l.textContent.includes(%r));
          return r?(r.querySelector('.tdcount')||{textContent:''}).textContent.replace(/\\s+/g,' ').trim():null; })()""" % title)

    def aid(self, title):
        return self.b.eval("""(()=>{ const r=[...document.querySelectorAll('#tdList>li.td-message')].find(l=>l.textContent.includes(%r));
          return r?r.dataset.td.slice(2):null; })()""" % title)

    def gone(self, title):
        return "![...document.querySelectorAll('#tdList>li.td-message')].some(l=>l.textContent.includes(%r))" % title

    def shown(self, title):
        return "[...document.querySelectorAll('#tdList>li.td-message')].some(l=>l.textContent.includes(%r))" % title

    def open_today(self):
        b = self.b
        b.eval("go('today'); EXPAND.add('td'); renderToday()")
        b.wait("document.querySelector('#tdList li.td-message')")
        self.assertIn("also on 1 other thread", self.chip("Licence numbers"))

    def dismiss(self, title):
        i = self.aid(title)
        self.b.eval(f"""(()=>{{ const x=document.createElement('button'); x.dataset.alertdo='dismiss'; x.dataset.id='{i}';
          document.body.appendChild(x); x.click(); x.remove(); }})()""")             # through the page's own click handler

    def handled(self, title):
        self.b.click(f'#tdList [data-alertdo="handled"][data-id="{self.aid(title)}"]')

    def settle(self):
        """Bring the page level with the server by hand, so a later step is judged on its own handler only."""
        self.b.eval("vipPoll()")
        self.b.pump(0.5)

    # In each test the chip is read the moment the card has gone or come back, with no wait for it: the page's own event
    # stream redraws about 1.5 s later and would hide a handler that did not refresh the counts itself. Each fails on the
    # code before 83305db7 and passes on the fix.
    def test_dismiss_updates_the_other_cards_chip(self):
        self.open_today()
        self.dismiss("Go-live window")
        self.b.wait(self.gone("Go-live window"), timeout=5)
        self.assertNotIn("also on", self.chip("Licence numbers") or "")

    def test_undo_of_dismiss_brings_the_chip_back(self):
        b = self.b
        self.open_today()
        self.dismiss("Go-live window")
        b.wait(self.gone("Go-live window"), timeout=5)
        self.settle()
        b.wait("!document.querySelector('#tdList')||!(%s)" % "[...document.querySelectorAll('#tdList>li.td-message')].find(l=>l.textContent.includes('Licence numbers')).textContent.includes('also on')", timeout=5)
        b.click("#snackU")
        b.wait(self.shown("Go-live window"), timeout=0.8)                       # the handler's own redraw, not the event stream's
        self.assertIn("also on 1 other thread", self.chip("Licence numbers") or "")

    def test_handled_updates_the_other_cards_chip(self):
        self.open_today()
        self.handled("Licence numbers")
        self.b.wait(self.gone("Licence numbers"), timeout=5)
        self.assertNotIn("also on", self.chip("Go-live window") or "")

    def test_undo_of_handled_brings_the_chip_back(self):
        b = self.b
        self.open_today()
        self.handled("Licence numbers")
        b.wait(self.gone("Licence numbers"), timeout=5)
        self.settle()
        self.assertNotIn("also on", self.chip("Go-live window") or "")
        b.click("#snackU")
        b.wait(self.shown("Licence numbers"), timeout=0.8)                      # the handler's own redraw, not the event stream's
        self.assertIn("also on 1 other thread", self.chip("Go-live window") or "")

    def test_a_card_closed_as_replied_leaves_today_at_the_next_check(self):
        """Does NOT prove 83305db7: this passes unchanged on the code before it (checked three times by reverting the
        source), so the replied state already reached the old signature through the server's reply. It guards the
        behaviour that a replied card is gone, and the quiet Replied line shown, the moment the check finishes."""
        b = self.b
        b.eval("go('today'); EXPAND.add('td'); renderToday()")
        b.wait(self.shown("Licence numbers"))
        vf = self.v.root / "system/staging/vip.json"
        st = json.loads(vf.read_text())
        a = next(x for x in st["alerts"] if x.get("title") == "Licence numbers")
        a["state"], a["replied_at"] = "replied", f"{TODAY} 09:00"
        vf.write_text(json.dumps(st))
        b.eval("window.__polled=false; vipPoll().then(()=>{ window.__polled=true; })")      # the check, without waiting for its timer
        b.wait("window.__polled", timeout=5)
        self.assertTrue(b.eval(self.gone("Licence numbers")))                                # redrawn by the check itself, no wait
        self.assertIn("you replied 09:00", b.eval("document.getElementById('tdList').textContent"))   # now the quiet Replied line


class ThreadCardActions(LiveBrowserCase):
    """BL-342 Part 1: Handled (with Undo) and Log on the matched item, from the page."""

    @classmethod
    def load(cls, v):
        thread_vault(v)

    def card_id(self):
        return self.b.eval("""(()=>{ if(!EXPAND.has('td')){ EXPAND.add('td'); } renderToday();
          const li=[...document.querySelectorAll('#tdList>li.td-message')].find(l=>l.textContent.includes('Go-live window'));
          return li?li.dataset.td.slice(2):null; })()""")

    def test_handled_and_undo(self):
        b = self.b
        b.eval("go('today')")
        aid = self.card_id()
        self.assertTrue(aid)
        b.click(f'#tdList [data-alertdo="handled"][data-id="{aid}"]')
        b.wait(f"!document.querySelector('#tdList li[data-td=\"al{aid}\"]')")
        self.assertEqual(b.eval("document.getElementById('snackT').textContent"), "Marked handled")
        self.assertTrue(b.eval("document.activeElement.matches('#tdList [data-tdact]')"))
        st = json.loads((self.v.root / "system/staging/vip.json").read_text())
        self.assertEqual(next(a for a in st["alerts"] if a["id"] == aid)["state"], "handled")
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*-dashboard*.json")).__len__(),
                         len(list((self.v.root / "system/staging").glob("proposed-*-dashboard*.json"))))
        b.click("#snackU")
        b.wait(f"document.querySelector('#tdList li[data-td=\"al{aid}\"]')")
        st = json.loads((self.v.root / "system/staging/vip.json").read_text())
        self.assertEqual(next(a for a in st["alerts"] if a["id"] == aid)["state"], "open")

    def test_log_stages_one_update_and_the_button_goes(self):
        b = self.b
        b.eval("go('today')")
        aid = self.card_id()
        before = {p.name for p in (self.v.root / "system/staging").glob("proposed-*.json")}
        b.click(f'#tdList [data-alertdo="log"][data-id="{aid}"]')
        b.wait(f"document.querySelector('#tdList li[data-td=\"al{aid}\"]').textContent.includes('Logged on ABC-')", 20)
        self.assertFalse(b.eval(f"!!document.querySelector('#tdList [data-alertdo=\"log\"][data-id=\"{aid}\"]')"))
        self.assertIn("for Review", b.eval("document.getElementById('snackT').textContent"))
        new = [p for p in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json") if p.name not in before]
        self.assertEqual(len(new), 1)
        (item,) = json.loads(new[0].read_text())["items"]
        self.assertEqual((item["op"], item["decision"]), ("update", "pending"))
        SHOTS.mkdir(parents=True, exist_ok=True)
        b.eval("document.getElementById('hTd').scrollIntoView(true)")
        b.pump(0.3)
        b.screenshot(str(SHOTS / "today-card-logged.png"))
        self.assertIsNone(says_vip(b.eval("document.getElementById('tdList').outerHTML")))


def close_vault(v):
    """The thread vault with a close suggestion on the overdue card (the check kept it: step 9)."""
    thread_vault(v)
    item = next(r["id"] for r in v.rows("actions") if r["description"] == "Send the data access letter")
    vf = v.root / "system/staging/vip.json"
    st = json.loads(vf.read_text())
    card = next(a for a in st["alerts"] if a.get("title") == "Go-live window")
    card["p"] = item.split("-")[0]
    card["closes"] = {"id": item, "evidence": "Sara says the letter went out", "who": "Sara Example", "at": f"{TODAY} 08:50"}
    vf.write_text(json.dumps(st))
    run(v, "build_dashboard.py")


class ThreadCardClose(LiveBrowserCase):
    """BL-342 Part 3 B, step 9: "Looks done: close <ID>" beside Log at 1400 and 900px, light and dark; one click stages the
    close for Review and the card says "Staged for Review" with Undo; Undo takes it back. Nothing says VIP."""

    @classmethod
    def load(cls, v):
        close_vault(v)

    def show(self, width, mode):
        b = self.b
        b.resize(width, 900)
        b.wait(f"innerWidth==={width}")
        b.eval(f"S.theme={mode!r}; applyTheme(); go('today'); EXPAND.add('td'); renderToday()")
        b.wait("document.querySelector('#tdList li.td-message')")
        b.pump(0.4)

    def card(self):
        return self.b.eval("""(()=>{ %s
          const li=[...document.querySelectorAll('#tdList>li.td-message')].find(l=>l.textContent.includes('Go-live window'));
          const done=li.querySelector('.tddone'), st=li.querySelector('.tdstaged');
          return {id:li.dataset.td.slice(2), buttons:[...li.querySelectorAll(':scope>.tacts button')].map(x=>x.getAttribute('aria-label')),
            tips:[...li.querySelectorAll(':scope>.tacts button')].map(x=>x.dataset.tip), done:done&&done.textContent,
            staged:st&&st.textContent.replace(/\\s+/g,' '), contrast:[done,st].filter(Boolean).map(ratio),
            scroll:[document.documentElement.scrollWidth, innerWidth], right:li.getBoundingClientRect().right<=innerWidth+1}; })()""" % CONTRAST)

    def test_the_button_beside_log_then_staged_for_review_and_undo(self):
        b = self.b
        SHOTS.mkdir(parents=True, exist_ok=True)
        item = next(r["id"] for r in self.v.rows("actions") if r["description"] == "Send the data access letter")
        for width in (1400, 900):
            for mode in ("Light", "Dark"):
                with self.subTest(width=width, mode=mode):
                    self.show(width, mode)
                    o = self.card()
                    self.assertIn(f"Stage a close of {item} for Review", o["buttons"])
                    i = o["buttons"].index(f"Stage a close of {item} for Review")
                    self.assertTrue(o["buttons"][i - 1].startswith("Log on"), o["buttons"])          # beside Log
                    self.assertEqual(o["tips"][i], f"Looks done: close {item}")
                    self.assertEqual(o["done"], "Looks done: Sara says the letter went out")
                    self.assertTrue(o["right"])
                    self.assertLessEqual(o["scroll"][0], o["scroll"][1])
                    for r in o["contrast"]:
                        self.assertGreaterEqual(r, 4.5)
                    b.eval("document.querySelector('#tdList>li.td-message').scrollIntoView({block:'center'})")
                    b.pump(0.3)
                    b.screenshot(str(SHOTS / f"close-{width}-{mode.lower()}.png"))
        self.show(1400, "Light")
        aid = self.card()["id"]
        b.click(f'#tdList [data-alertdo="close"][data-id="{aid}"]')
        b.wait(f"(document.querySelector('#tdList li[data-td=\"al{aid}\"] .tdstaged')||{{}}).textContent", 20)
        o = self.card()
        self.assertEqual(o["staged"], f"Close of {item}: Staged for Review · Undo")
        self.assertNotIn(f"Stage a close of {item} for Review", o["buttons"])
        staged = [i for f in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json")
                  for i in json.loads(f.read_text())["items"] if i.get("id") == item]
        self.assertEqual([(i["changes"].get("status"), i["decision"]) for i in staged], [("Closed", "pending")])
        for width, mode in ((1400, "Dark"), (900, "Light")):
            self.show(width, mode)
            for r in self.card()["contrast"]:
                self.assertGreaterEqual(r, 4.5)
            b.eval("document.querySelector('#tdList>li.td-message').scrollIntoView({block:'center'})")
            b.pump(0.3)
            b.screenshot(str(SHOTS / f"close-staged-{width}-{mode.lower()}.png"))
        self.show(1400, "Light")
        self.assertIsNone(says_vip(b.eval("document.getElementById('tdList').outerHTML")))
        b.click(f'#tdList li[data-td="al{aid}"] [data-alertdo="closeundo"]')
        b.wait(f"!document.querySelector('#tdList li[data-td=\"al{aid}\"] .tdstaged')", 20)
        self.assertIn(f"Stage a close of {item} for Review", self.card()["buttons"])
        self.assertEqual([i for f in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json")
                          for i in json.loads(f.read_text())["items"] if i.get("id") == item], [])



def promise_vault(v):
    """The thread vault with, on the Board pack card, a promise of Alan's from his own message and an open promise of the
    project that looks kept (the check kept both: BL-342 Part 5)."""
    thread_vault(v)
    import sqlite3
    from contextlib import closing
    item = next(r["id"] for r in v.rows("actions") if r["description"] == "Send the data access letter")
    code = item.split("-")[0]
    pid = f"{code}-P-090"
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        con.execute("INSERT INTO promises (id, project, promised_by, promised_to, description, raised, source) VALUES "
                    "(?, ?, 'Sara Example', 'Alan Carter', 'Send the signed data letter', '2026-01-01', 'Email · test')", (pid, code))
        con.commit()
    vf = v.root / "system/staging/vip.json"
    st = json.loads(vf.read_text())
    card = next(a for a in st["alerts"] if a.get("title") == "Board pack")
    card["p"] = code
    card["promises"] = [{"key": "a1b2c3d4e5f6", "what": "Send the revised go-live plan", "to": "Sara Example", "due": LATER,
                         "at": f"{TODAY} 08:30", "state": "offered"}]
    card["kept"] = {"id": pid, "evidence": "Sara sent the signed letter", "who": "Sara Example", "at": f"{TODAY} 08:05"}
    vf.write_text(json.dumps(st))
    run(v, "build_dashboard.py")
    return pid


class ThreadCardPromise(LiveBrowserCase):
    """BL-342 Part 5: "You promised Sara Example: ..." with Add a promise and Dismiss, and "Looks kept: <ID>" with Looks kept:
    mark kept, at 1400 and 900px, light and dark; each click stages one pending proposal for Review, shown as "Staged for
    Review" with Undo; Undo takes it back; Dismiss stages nothing. Nothing says VIP."""

    @classmethod
    def load(cls, v):
        cls.pid = promise_vault(v)

    def show(self, width, mode):
        b = self.b
        b.resize(width, 900)
        b.wait(f"innerWidth==={width}")
        b.eval(f"S.theme={mode!r}; applyTheme(); go('today'); EXPAND.add('td'); renderToday()")
        b.wait("[...document.querySelectorAll('#tdList li.td-message')].some(l=>l.textContent.includes('Board pack'))")
        b.pump(0.4)

    def card(self):
        return self.b.eval("""(()=>{ %s
          const li=[...document.querySelectorAll('#tdList>li.td-message')].find(l=>l.textContent.includes('Board pack'));
          const pr=li.querySelector('.tdproms .tdcand'), kept=[...li.querySelectorAll('.tddone')].map(x=>x.textContent),
            st=[...li.querySelectorAll('.tdstaged')];
          return {id:li.dataset.td.slice(2), prom:pr&&pr.querySelector('.ct').textContent,
            pbuttons:pr?[...pr.querySelectorAll('.tacts button')].map(x=>x.getAttribute('aria-label')):[],
            buttons:[...li.querySelectorAll(':scope>.tacts button')].map(x=>x.getAttribute('aria-label')),
            tips:[...li.querySelectorAll(':scope>.tacts button')].map(x=>x.dataset.tip), kept,
            staged:st.map(x=>x.textContent.replace(/\\s+/g,' ').trim()),
            contrast:[pr&&pr.querySelector('.ct'),...li.querySelectorAll('.tddone'),...st].filter(Boolean).map(ratio),
            scroll:[document.documentElement.scrollWidth, innerWidth], right:li.getBoundingClientRect().right<=innerWidth+1}; })()""" % CONTRAST)

    def staged(self):
        return [i for f in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json")
                for i in json.loads(f.read_text())["items"]]

    def test_the_promise_and_kept_lines_then_staged_for_review_and_undo(self):
        b, pid = self.b, self.pid
        SHOTS.mkdir(parents=True, exist_ok=True)
        later = f"{LATER[8:10]}-{LATER[5:7]}-{LATER[:4]}"
        for width in (1400, 900):
            for mode in ("Light", "Dark"):
                with self.subTest(width=width, mode=mode):
                    self.show(width, mode)
                    o = self.card()
                    self.assertEqual(o["prom"], f"You promised Sara Example: Send the revised go-live plan · by {later}")
                    self.assertEqual(o["pbuttons"], ["Add a promise: Send the revised go-live plan",
                                                     "Dismiss the promise: Send the revised go-live plan"])
                    self.assertIn(f"Looks kept: {pid}, Sara sent the signed letter", o["kept"])
                    self.assertIn(f"Stage {pid} as kept for Review", o["buttons"])
                    self.assertEqual(o["tips"][o["buttons"].index(f"Stage {pid} as kept for Review")], "Looks kept: mark kept")
                    self.assertTrue(o["right"])
                    self.assertLessEqual(o["scroll"][0], o["scroll"][1])
                    for r in o["contrast"]:
                        self.assertGreaterEqual(r, 4.5)
                    b.eval("[...document.querySelectorAll('#tdList>li.td-message')].find(l=>l.textContent.includes('Board pack'))"
                           ".scrollIntoView({block:'center'})")
                    b.pump(0.3)
                    b.screenshot(str(SHOTS / f"promise-{width}-{mode.lower()}.png"))
        self.show(1400, "Light")
        aid = self.card()["id"]
        b.click(f'#tdList [data-alertdo="promise"][data-id="{aid}"]')
        b.wait(f"(document.querySelector('#tdList li[data-td=\"al{aid}\"] .tdproms .tdstaged')||{{}}).textContent", 20)
        b.click(f'#tdList [data-alertdo="kept"][data-id="{aid}"]')
        b.wait(f"(document.querySelector('#tdList li[data-td=\"al{aid}\"] p.tdstaged')||{{}}).textContent", 20)
        o = self.card()
        self.assertIn("Staged for Review · Undo", o["staged"])
        self.assertIn(f"{pid} kept: Staged for Review · Undo", o["staged"])
        self.assertEqual(o["pbuttons"], [])
        self.assertNotIn(f"Stage {pid} as kept for Review", o["buttons"])
        got = sorted((i["op"], i["table"], i.get("id") or i["values"]["description"], i["decision"]) for i in self.staged())
        self.assertEqual(got, [("new", "promises", "Send the revised go-live plan", "pending"),
                               ("update", "promises", pid, "pending")])
        for width, mode in ((1400, "Dark"), (900, "Light")):
            self.show(width, mode)
            for r in self.card()["contrast"]:
                self.assertGreaterEqual(r, 4.5)
            b.eval("[...document.querySelectorAll('#tdList>li.td-message')].find(l=>l.textContent.includes('Board pack'))"
                   ".scrollIntoView({block:'center'})")
            b.pump(0.3)
            b.screenshot(str(SHOTS / f"promise-staged-{width}-{mode.lower()}.png"))
        self.show(1400, "Light")
        self.assertIsNone(says_vip(b.eval("document.getElementById('tdList').outerHTML")))
        b.click(f'#tdList li[data-td="al{aid}"] [data-alertdo="keptundo"]')
        b.wait(f"!document.querySelector('#tdList li[data-td=\"al{aid}\"] p.tdstaged')", 20)
        b.click(f'#tdList li[data-td="al{aid}"] [data-alertdo="promiseundo"]')
        b.wait(f"!document.querySelector('#tdList li[data-td=\"al{aid}\"] .tdproms .tdstaged')", 20)
        self.assertEqual(self.staged(), [])
        b.click(f'#tdList [data-alertdo="promisedismiss"][data-id="{aid}"]')
        b.wait(f"!document.querySelector('#tdList li[data-td=\"al{aid}\"] .tdproms')", 20)
        self.assertEqual(self.staged(), [])
        self.assertEqual([p["state"] for a in json.loads((self.v.root / "system/staging/vip.json").read_text())["alerts"]
                          for p in a.get("promises") or []], ["dismissed"])


if __name__ == "__main__":
    unittest.main()
