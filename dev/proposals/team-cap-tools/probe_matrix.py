#!/usr/bin/env python3
"""Sensitive matrix (fixed in 2.6.1). The controls are made client-visible AFTER Approve with cx-edit (propose.py stage + tracker.py apply),
because minutes.py stage no longer takes client_visible / client_message from a spec. Works on 2.6.0 (already client-visible: skipped).

Leak matrix: Sensitive item x Track {tick, cross, neither, default} x kind {action, decision, risk}, with a Sensitive item that
is also client-visible and an ordinary control in every cell, checked against every DISTRIBUTED output reachable through code.

Usage:  python3 -I probe_matrix.py <checkout> [--mutant NAME] [--json OUT] [--keep]
  <checkout>  a checkout of creaite (read only: the probe builds a throwaway vault with dev/tests/test_tracker.make_vault,
              under $TMPDIR or the system temp folder; the checkout is never written).
Mutants (applied to the throwaway vault's script copies only, so the probe can be seen to go red):
  no-withheld      minutes_record.withheld returns {}                    -> ticked Sensitive cells must go LEAK
  no-sensitive     minutes_record._blocking returns {} (no label blocks)  -> ticked Sensitive cells must go LEAK
  no-track         minutes_record.tracked_of returns the record as it is  -> draft-phase crossed controls appear (UNEXPECTED)

Track on a tree without the Track column (before #268, e.g. 2.5.4): tick = leave the row, cross = Remove, neither = Remove with
"keep its line" (the same record changes track.js makes), default = N/A.

Outputs (columns):
  D-facts  draft: minutes_record.followup_facts(draft, "distributed")   (Track choices in layout.track only, tracked_of)
  D-js     draft: drafts.js deFollowup on those facts, mapped as openMinutesFollowup(version "distributed") maps them
  F-facts  filed: minutes_record.followup_facts(filed, "distributed")
  F-js     filed: drafts.js deFollowup (the full email body, HTML + text + subject + To)
  F-docx   filed: minutes_record.export(filed, "docx", version="distributed")   (distributed_export -> creaite_doc.export)
  F-html   filed: minutes_record.export(filed, "html", version="distributed")
  F-pdf    filed: minutes_record.export(filed, "pdf",  version="distributed"): creaite_doc.print_pdf intercepted, the exact HTML
           page Chrome would print is checked (no browser)
  F-polish filed: drafts.context({"kind": "polish", text: the follow-up's cover}) prompt + sources (the follow-up's only AI kind)
  H-js     filed: the meeting hub's follow-up (BL-224): the meeting's applied items as tracker rows (hub_produced: result_id),
           deItem -> deBarred -> deDefaults(outside attendees) -> deFollowup, plus drafts.py followup (summary) on the
           distributed Word file
Cell values: Sensitive rows PASS / LEAK; control rows ok / MISSING (expected, absent) / UNEXPECTED (crossed, present); n/a.
No model, no Microsoft 365, no browser.
"""
import json, os, re, shutil, sqlite3, subprocess, sys, tempfile, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = Path(sys.argv[1]).resolve()
ARGS = sys.argv[2:]
MUTANT = ARGS[ARGS.index("--mutant") + 1] if "--mutant" in ARGS else None
JSON_OUT = ARGS[ARGS.index("--json") + 1] if "--json" in ARGS else None
KEEP = "--keep" in ARGS

TMP = Path(tempfile.mkdtemp(prefix="probe-matrix-")).resolve()
os.environ["TMPDIR"] = str(TMP)
tempfile.tempdir = str(TMP)
NOW = "2026-10-14 12:00"
os.environ["CREAITE_NOW"] = NOW
sys.path.insert(0, str(WT / "dev/tests"))
from test_tracker import ABC, Vault  # noqa: E402

DAY, TITLE = "2026-10-14", "[ABC] Steering committee"
DRAFT = "system/staging/drafts/2026-10-14 Steering committee.html"
FILED = f"{ABC}/minutes/2026-10-14 Steering committee.html"
TRACK_JS = WT / "system/templates/dashboard/src/components/minutes/track.js"
SRC = WT / "system/templates/dashboard/src"
KINDS = {"A": "action", "D": "decision", "R": "risk"}
TRACKS = {"TICK": "y", "CROSS": "n", "NEITHER": "", "DEFAULT": None}
VARS = {"SENS": "Sensitive", "SENSCV": "Sensitive + client-visible", "CTRL": "control (ordinary, client-visible)"}
COLS = ["D-facts", "D-js", "F-facts", "F-js", "F-docx", "F-html", "F-pdf", "F-polish", "H-js"]
VTT = ("WEBVTT\n\n00:00:01.000 --> 00:00:06.000\n<v Alan Carter>Morning all.</v>\n\n"
       "00:00:06.000 --> 00:00:12.000\n<v Jane Doe>We agreed the plan.</v>\n")
PEOPLE = ("# People register\n\n## People\n\n| Full name | Email | Aliases | Organisation | Role | Hidden | VIP | Labels |\n"
          "|---|---|---|---|---|---|---|---|\n| Jane Doe | jane@client.example | Jane | Example Client Ltd | Sponsor | | | |\n"
          "| Omar Ali | omar@brightwater.example | Omar | Brightwater | Lead | | | |\n"
          "| Alan Carter | alan@brightwater.example | Alan | Brightwater | PM | | | |\n")


def marker(k, t, v):
    return f"{'PLAIN' if v == 'CTRL' else 'ZEBRA'}-{k}-{t}-{v}-{'1001' if v == 'CTRL' else '4471'}"


def cells():
    return [(k, t, v) for k in KINDS for t in TRACKS for v in VARS]


def item_spec(k, t, v):
    m = marker(k, t, v)
    base = {"project": "ABC"}
    if v in ("SENSCV", "CTRL"):
        base["client_visible"] = 1
    if v in ("SENS", "SENSCV"):
        base["labels"] = ["Sensitive"]
    cm3 = f"What it is: {m}-CM.\nWhat it means for you: little.\nWhat is being done: work continues."
    if k == "A":
        val = {**base, "description": f"Arrange item {m}", "owner": "Alan Carter"}
        if base.get("client_visible"):
            val["client_message"] = cm3
        return {"table": "actions", "due_words": "Friday", "values": val}
    if k == "D":
        val = {**base, "decision": f"Agreed item {m}", "made_by": "Jane Doe"}
        if base.get("client_visible"):
            val["client_message"] = f"Agreed {m}-CM."
        return {"table": "decisions", "values": val}
    val = {**base, "type": "Risk", "description": f"Exposure item {m}", "priority": "High"}
    if base.get("client_visible"):
        val["client_message"] = cm3
    return {"table": "raid", "values": val}


def spec():
    return {"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": "inbox/2026-10-14 Steering committee.vtt",
            "minutes": {"start": "10:00", "end": "11:00",
                        "attendees": "Jane Doe (Example Client Ltd); Alan Carter, Omar Ali (Brightwater)",
                        "summary": ["The committee met and agreed the plan."], "chat": False},
            "items": [item_spec(*c) for c in cells()] + EXTRA_ITEMS}


UPD_A, UPD_D = "PLAIN-UPDA-1001", "PLAIN-UPDD-1001"     # ADDED (9501f2cd): markers in the existing tracker items an update row names
EXTRA_ITEMS = [
    {"op": "update", "table": "actions", "id": "ABC-A-001", "set": {"due_date": "2026-10-30"}, "why": "Omar said so"},
    {"op": "update", "table": "decisions", "id": "ABC-D-003", "set": {"status": "Made", "reasoning": "Closest site"}, "why": "Jane decided"},
]


MUTANTS = {
    "no-withheld": ("minutes_record.py", "    labels = item_labels(doc, con) if labels is None else labels\n",
                    "    return {}\n    labels = item_labels(doc, con) if labels is None else labels\n"),
    "no-sensitive": ("minutes_record.py", '    out = {client_leak.SENSITIVE: "Sensitive", ',
                     '    return {}\n    out = {client_leak.SENSITIVE: "Sensitive", '),
    "no-track": ("minutes_record.py", '    if doc.get("state") != "draft":\n        return doc\n    try:\n        data = json.loads(',
                 '    return doc\n    if doc.get("state") != "draft":\n        return doc\n    try:\n        data = json.loads('),
}


class Probe:
    def __init__(self):
        self.v = Vault()
        self.root = self.v.root
        self.track_mode = TRACK_JS.is_file()
        self.res = {c: {} for c in cells()}
        self.notes = []
        self.out = TMP / f"out-{os.getpid()}"
        self.out.mkdir(exist_ok=True)

    # ---- plumbing ----
    def py(self, code, ok=True):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts')\n" + code],
                           cwd=self.root, capture_output=True, text=True, env=os.environ.copy())
        if ok and r.returncode != 0:
            raise RuntimeError(code[:200] + "\n" + r.stdout[-2000:] + r.stderr[-3000:])
        return r

    def pj(self, code, ok=True):
        r = self.py(code, ok)
        if r.returncode != 0:
            return {"ok": False, "message": "ERR " + r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "ERR"}
        return json.loads(r.stdout.strip().splitlines()[-1])

    def node(self, script, data=None):
        f = self.out / "in.json"
        f.write_text(json.dumps(data or {}), encoding="utf-8")
        h = self.out / "h.mjs"
        h.write_text(script, encoding="utf-8")
        r = subprocess.run(["node", str(h), str(f)], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("node: " + r.stderr[-2000:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def mutate(self):
        if not MUTANT:
            return
        if MUTANT == "no-debarred-sens":
            return
        f, old, new = MUTANTS[MUTANT]
        p = self.root / "system/scripts" / f
        s = p.read_text(encoding="utf-8")
        if old not in s:
            raise SystemExit(f"mutant {MUTANT}: anchor not found in {f} on this tree")
        p.write_text(s.replace(old, new, 1), encoding="utf-8")

    # ---- the drafts.js builder, from the source text (its imports are DOM-bound; the pure functions are lifted) ----
    def js_lib(self):
        _t = (SRC / "drafts.js").read_text(encoding="utf-8")
        if MUTANT == "no-debarred-sens":      # ADDED mutant: deBarred ignores i.sens (the hub/page rule of 93870871)
            assert "(outside&&!!i.sens)" in _t
            _t = _t.replace("||(outside&&!!i.sens)", "", 1)
        src = _t.split("\n")
        out, i = [], 0
        while i < len(src):
            m = re.match(r"export (?:const|function|let) (\w+)", src[i])
            if m and (m.group(1).startswith(("de", "DE_")) or m.group(1) == "draftEmail"):
                block = [src[i][len("export "):]]
                i += 1
                while i < len(src) and src[i][:1] in (" ", "\t"):
                    block.append(src[i])
                    i += 1
                out.append("\n".join(block))
                continue
            i += 1
        page = (SRC / "core/page.js").read_text(encoding="utf-8")
        fd = re.search(r"^export const fd=.*$", page, re.M).group(0)[len("export "):]
        u = lambda p: (SRC / p).as_uri()  # noqa: E731
        return (f'import fs from "fs";\nimport {{ esc }} from "{u("core/dom.js")}";\n'
                f'import {{ linkSegments, linkWithAddress, sentStrip }} from "{u("core/linkText.js")}";\n'
                f'import {{ linkUrl }} from "{u("core/linkUrl.js")}";\n'
                'const S={ownDomains:["brightwater.example"],me:"Alan Carter",dueSoon:7};\n'
                'const DATE=/^\\d{4}-\\d{2}-\\d{2}$/;\n' + fd + "\n" + "\n".join(out) + "\n")

    def js_email(self, reqs):
        """reqs: [{mode: "minutes", facts} | {mode: "hub", items, attendees, summary, title, day, codes}] -> [{subject,to,html,text,cover}]"""
        body = r'''
const R=JSON.parse(fs.readFileSync(process.argv[2],"utf8")), now=new Date("2026-10-14T12:00:00"), out=[];
for(const q of R){ let o;
  if(q.mode==="minutes"){ const r=q.facts, version="distributed";   // drafts.js openMinutesFollowup, as written
    const all=(r.items||[]).map(x=>({...x,p:(r.codes||[])[0]||"",due:x.due||null,pr:"",client:version==="distributed",noid:/^@/.test(x.id),by:x.by||"",o:x.o||x.by||""})), ok=all.filter(i=>!deBarred(i));
    const owners=new Set(ok.map(i=>i.o)), att=r.attendees||[];
    o={mode:"followup",title:r.title,day:r.day,codes:r.codes||[],items:ok,attendees:att,lead:(att.find(a=>owners.has(a.name))||{}).name||"",summary:r.summary||"",
       picked:new Set(ok.map(i=>i.k+":"+i.id)),internal:false,now,today:"2026-10-14",dueSoon:7,from:"Alan Carter",cover:""};
  } else {                                                           // drafts.js openFollowup + deFollowFacts, as written
    const all=q.items.map(x=>deItem(x.k,x)), ok=all.filter(i=>!deBarred(i)), outside=deOutsideAll(q.attendees);
    const owners=new Set(ok.map(i=>i.o));
    o={mode:"followup",title:q.title,day:q.day,codes:q.codes,items:ok,attendees:q.attendees,lead:(q.attendees.find(a=>owners.has(a.name))||{}).name||"",
       summary:q.summary||"",picked:deDefaults(ok,outside),now,today:"2026-10-14",dueSoon:7,from:"Alan Carter",cover:""};
  }
  const e=draftEmail(o); out.push({subject:e.subject,to:e.to,html:e.html,text:e.text,cover:(e.text.split("\n")[2]||"").trim()}); }
console.log(JSON.stringify(out));
'''
        return self.node(self.js_lib() + body, reqs)

    # ---- set-up ----
    def setup(self):
        self.v.run("init")
        self.mutate()
        from test_tracker import action  # noqa: E402  ADDED: the existing items the two update rows name
        self.v.propose("2026-10-13-0900", [
            action(1, description=f"Send the revised SOW to the client {UPD_A}", due_date="2026-10-20"),
            {"n": 3, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
             "values": {"project": "ABC", "decision": f"Choose the pilot site {UPD_D}", "status": "Pending",
                        "source": f"{ABC}/minutes/2026-10-01 Steering.docx — Decisions"}}])
        self.v.run("apply")
        (self.root / "projects/_portfolio/people-register.md").write_text(PEOPLE, encoding="utf-8")
        (self.root / "inbox/2026-10-14 Steering committee.vtt").write_text(VTT, encoding="utf-8")
        f = self.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps(spec()), encoding="utf-8")
        self.v.run("stage", str(f), script="minutes.py")
        self.name = next((self.root / "system/staging").glob("proposed-*.json")).name
        data = json.loads((self.root / "system/staging" / self.name).read_text(encoding="utf-8"))
        self.n_of = {}
        for it in data["items"]:
            v = it.get("values") or {}
            txt = v.get("description") or v.get("decision") or ""
            c = next((c for c in cells() if marker(*c) in txt), None)
            if c:
                self.n_of[c] = it["n"]
        self.upd_n = {it["id"]: it["n"] for it in data["items"] if it.get("op") == "update"}
        missing = [marker(*c) for c in cells() if c not in self.n_of]
        if missing:
            raise RuntimeError(f"not staged: {missing}")
        self.plan = {i["n"]: i["group"] for i in self.pj(
            f"import review\nprint(json.dumps(review.minutes_plan(json.load(open('system/staging/{self.name}')))))")["items"]}

    def choice(self, c):
        return TRACKS[c[1]]

    # ---- phases ----
    def draft_phase(self):
        if self.track_mode:
            choices = {str(self.n_of[c]): self.choice(c) for c in cells() if self.choice(c) is not None}
            choices.update({str(n): "" for n in self.upd_n.values()})        # ADDED: both updates "Remove, keep its line"
            r = self.pj("import creaite_doc, minutes_record\n"
                        f"d = creaite_doc.read({DRAFT!r}); d.setdefault('layout', {{}})['track'] = {choices!r}\n"
                        f"r = minutes_record.save_page({DRAFT!r}, d); r.pop('doc', None); print(json.dumps(r))")
            assert r.get("ok"), r
        else:
            for c in cells():
                t = self.choice(c)
                if t in ("n", ""):
                    op = {"op": "remove", "n": self.n_of[c], "keep_line": t == ""}
                    r = self.pj("import minutes_record\n"
                                f"r = minutes_record.change({DRAFT!r}, {op!r}); r.pop('doc', None); print(json.dumps(r))")
                    assert r.get("ok"), (op, r)
        facts = self.pj(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({DRAFT!r}, 'distributed')))")
        self.mark("D-facts", json.dumps(facts), "minutes_record.followup_facts(draft,'distributed')")
        em = self.js_email([{"mode": "minutes", "facts": facts}])[0]
        self.mark("D-js", json.dumps(em), "drafts.js openMinutesFollowup map -> deFollowup")
        r = self.pj(f"import minutes_record\nprint(json.dumps(minutes_record.export({DRAFT!r}, 'docx', True, version='distributed')))", ok=False)
        self.notes.append(f"draft distributed Word export: {'made' if r.get('ok') else 'refused: ' + str(r.get('message'))[:120]}")
        self.draft_facts = facts

    def approve(self):
        if self.track_mode:
            v = self.pj("import minutes_record\n"
                        f"r = minutes_record.view(file={self.name!r})\nprint(json.dumps({{'doc': r['doc'], 'plan': r['plan']['items']}}))")
            script = (f"import * as T from {json.dumps(TRACK_JS.as_uri())};\nimport fs from 'fs';\n"
                      "const v=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));\n"
                      "console.log(JSON.stringify({ops:T.reconcileOps(v.doc,v.plan),args:T.approveArgs(v.doc,v.plan),"
                      "states:Object.fromEntries(T.trackRows(v.doc).map(r=>[r.n,T.trackOf(v.doc,r,v.plan)]))}));")
            got = self.node(script, v)
            self.track_states = got["states"]
            for op in got["ops"]:
                r = self.pj("import minutes_record\n"
                            f"r = minutes_record.change({DRAFT!r}, {op!r}); r.pop('doc', None); print(json.dumps(r))")
                assert r.get("ok"), (op, r)
            args = got["args"]
        else:
            own = [self.n_of[c] for c in cells() if self.choice(c) == "y" and self.plan.get(self.n_of[c]) == "own"]
            args = {"group": True, "own": own}
            self.track_states = {}
        r = self.pj(f"import review\nprint(json.dumps(review.approve_minutes({self.name!r}, {args['group']!r}, {list(args['own'])!r})))")
        assert r.get("ok"), r
        self.approved = r
        assert (self.root / FILED).is_file(), "minutes not filed"

    # ---- ADDED (line2, #283 M2): the controls become client-visible the way the real flow does it ----
    def client_visible_after_approval(self):
        """Since #283 M2 `minutes.py stage` drops a client_visible / client_message set by the model (a spec is written from a
        transcript's text; both are Alan's alone). So the SENSCV and CTRL items reach the tracker NOT client-visible. Alan makes an
        applied item client-visible with cx-edit ("make ABC-A-005 client-visible"): `propose.py stage <spec>` writes an approved
        update proposal (changes: client_visible 1 + the client wording), `tracker.py apply` writes it. Same here, in the THROWAWAY
        vault only, for every applied SENSCV / CTRL row. An item already client-visible (a tree before M2, e.g. 2.6.0) needs no edit."""
        ap = self.root / "system/staging/applied" / self.name
        data = json.loads((ap if ap.is_file() else self.root / "system/staging" / self.name).read_text(encoding="utf-8"))
        items, self.cv_set, self.cv_already = [], [], []
        for it in data["items"]:
            v = it.get("values") or {}
            txt = v.get("description") or v.get("decision") or ""
            c = next((c for c in cells() if marker(*c) in txt), None)
            if not c or c[2] not in ("SENSCV", "CTRL") or not it.get("result_id") or it.get("table") not in ("actions", "decisions", "raid"):
                continue
            want = item_spec(*c)["values"]
            cur = self.pj("import sqlite3\ncon = sqlite3.connect('system/tracker.db')\n"
                          f"r = con.execute('select client_visible, client_message from {it['table']} where id = ?', ({it['result_id']!r},)).fetchone()\n"
                          "print(json.dumps(r))")
            if cur and cur[0] == 1 and (cur[1] or "") == want["client_message"]:
                self.cv_already.append(it["result_id"])
                continue
            items.append({"op": "update", "table": it["table"], "id": it["result_id"],
                          "changes": {"client_visible": 1, "client_message": want["client_message"]}})
            self.cv_set.append(it["result_id"])
        if items:
            f = self.root / "system/staging/drafts/make-client-visible.json"
            f.write_text(json.dumps({"source_run": "cx-edit", "items": items}), encoding="utf-8")
            self.v.run("stage", str(f), script="propose.py")        # cx-edit: stage the approved update proposal
            self.v.run("apply")                                      # tracker.py apply: the only writer
        n = self.pj("import sqlite3\ncon = sqlite3.connect('system/tracker.db')\n"
                    "print(json.dumps(sum(con.execute('select count(*) from ' + t + ' where client_visible = 1').fetchone()[0] for t in ('actions','decisions','raid'))))")
        self.notes.append(f"client-visible after approval (cx-edit stage + apply): set {len(self.cv_set)} rows, already client-visible {len(self.cv_already)}, "
                          f"client-visible rows in the tracker now: {n}")

    def dump_filed(self):
        r = self.pj("import minutes_record, json as J\n"
                    f"rel, d = minutes_record.record_at({FILED!r})\n"
                    "rem = (d.get('meta') or {}).get('removed')\n"
                    "kept = [(s['id'], r.get('was'), str(r.get('cells'))[:80]) for s in d['sections'] for r in s.get('rows', []) if r.get('kept_line')]\n"
                    "print(json.dumps({'removed_present': rem is not None, 'removed': {k: {'held': v.get('held', '<<absent>>'), 'kept_line': v.get('kept_line')} for k, v in (rem or {}).items()}, 'kept': kept, 'state': d.get('state'),\n"
                    "  'upd_rows': [{'sec': s['id'], **{k: v for k, v in r.items() if k != 'cells'}, 'cells': r.get('cells')} for s in d['sections'] for r in s.get('rows', []) if 'ABC-A-001' in json.dumps(r.get('cells')) or 'ABC-D-003' in json.dumps(r.get('cells')) or 'Updates' in str(r.get('does'))]}, default=str))")
        self.filed_dump = r

    def filed_phase(self):
        facts = self.pj(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({FILED!r}, 'distributed')))")
        self.mark("F-facts", json.dumps(facts), "minutes_record.followup_facts(filed,'distributed')")
        # exports (PDF: print_pdf intercepted, the page it prints kept)
        cap = self.out / "pdf-page.html"
        code = ("import minutes_record, creaite_doc, shutil\n"
                f"def fake(page, out):\n    shutil.copy(page, {str(cap)!r}); open(out, 'wb').write(b'%PDF-1.4 probe')\n"
                "creaite_doc.print_pdf = fake\nres = {}\n"
                "for fmt in ('docx', 'html', 'pdf'):\n"
                f"    try:\n        res[fmt] = minutes_record.export({FILED!r}, fmt, True, version='distributed')\n"
                "    except Exception as e:\n        res[fmt] = {'ok': False, 'message': repr(e)}\n"
                "print(json.dumps(res))")
        ex = self.pj(code)
        self.exports = ex
        for fmt, col in (("docx", "F-docx"), ("html", "F-html"), ("pdf", "F-pdf")):
            r = ex.get(fmt) or {}
            if not r.get("ok"):
                self.na(col, f"export refused: {r.get('message')}")
                continue
            p = self.root / (r.get("path") or "")
            if fmt == "docx":
                with zipfile.ZipFile(p) as z:
                    txt = " ".join(re.sub(r"<[^>]+>", "", z.read(n).decode("utf-8", "ignore")) for n in z.namelist() if n.endswith(".xml"))
            elif fmt == "html":
                txt = p.read_text(encoding="utf-8", errors="ignore")
            else:
                txt = cap.read_text(encoding="utf-8", errors="ignore") if cap.is_file() else ""
            self.mark(col, txt, f"minutes_record.export(filed,'{fmt}',version='distributed')")
        # applied items as tracker rows (the hub's items)
        ap = self.root / "system/staging/applied" / self.name           # still in staging when items wait in Review
        data = json.loads((ap if ap.is_file() else self.root / "system/staging" / self.name).read_text(encoding="utf-8"))
        # ADAPTED (93870871): the page's hub rows are the dashboard's own records (REC(k,id) -> deItem), which since 93870871 carry
        # sens (build_dashboard.mark_held). Take them from build_dashboard.records_of instead of synthesising them from raw rows.
        ids = [it["result_id"] for it in data["items"] if it.get("result_id") and it.get("table") in ("actions", "decisions")]
        tabs = {it["result_id"]: it["table"] for it in data["items"] if it.get("result_id") and it.get("table") in ("actions", "decisions")}
        recs = self.pj("import build_dashboard, sqlite3\n"
                       "con = sqlite3.connect('system/tracker.db'); con.row_factory = sqlite3.Row\n"
                       f"out, miss = build_dashboard.records_of(con, {ids!r})\n"
                       "print(json.dumps({'out': out, 'miss': miss}, default=str))")
        self.hub_rows_dump = recs
        hub = []
        for t in ("actions", "decisions"):
            for x in (recs.get("out") or {}).get(t, []):
                hub.append({**x, "k": t, "p": x.get("p") or "ABC"})
        dist_docx = (ex.get("docx") or {}).get("path")
        files = [p for p in [(ex.get("docx") or {}).get("filed") if isinstance((ex.get("docx") or {}).get("filed"), str) else None,
                             dist_docx] if p]
        body = {"key": "x", "eid": "", "day": DAY, "start": "10:00", "title": TITLE, "files": files}
        r = subprocess.run([sys.executable, "system/scripts/drafts.py", "followup"], input=json.dumps(body), cwd=self.root,
                           capture_output=True, text=True, env=os.environ.copy())
        hubfacts = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {}
        att = [{"name": "Jane Doe", "email": "jane@client.example"}, {"name": "Omar Ali", "email": "omar@brightwater.example"}]
        ems = self.js_email([{"mode": "minutes", "facts": facts},
                             {"mode": "hub", "items": hub, "attendees": att, "summary": hubfacts.get("summary") or "",
                              "title": TITLE, "day": DAY, "codes": ["ABC"]}])
        self.mark("F-js", json.dumps(ems[0]), "drafts.js openMinutesFollowup map -> deFollowup")
        self.mark("H-js", json.dumps(ems[1]) + json.dumps(hubfacts), "hub_produced rows -> deItem/deBarred/deDefaults(outside) -> deFollowup")
        pol = self.pj("import drafts\n"
                      f"c = drafts.context({{'kind': 'polish', 'text': {ems[0]['cover']!r}, 'tone': 'neutral'}})\n"
                      "print(json.dumps({k: c.get(k) for k in ('prompt', 'sources', 'refused', 'nothing')}))", ok=False)
        if pol.get("refused") or pol.get("ok") is False:
            self.na("F-polish", f"polish: {pol.get('refused') or pol.get('message')}")
        else:
            self.mark("F-polish", json.dumps(pol), "drafts.context(kind='polish')")
        self.hub_n = len(hub)

    # ---- ADDED (9501f2cd): extra FILED-path checks ----
    def filed_texts(self):
        """The filed record's Distributed outputs again (facts, email body, Word, HTML, PDF page), as {col: text}; no marking."""
        facts = self.pj(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({FILED!r}, 'distributed')))")
        out = {"F-facts": json.dumps(facts), "F-js": json.dumps(self.js_email([{"mode": "minutes", "facts": facts}])[0])}
        cap = self.out / "pdf-page2.html"
        code = ("import minutes_record, creaite_doc, shutil\n"
                f"def fake(page, out):\n    shutil.copy(page, {str(cap)!r}); open(out, 'wb').write(b'%PDF-1.4 probe')\n"
                "creaite_doc.print_pdf = fake\nres = {}\n"
                "for fmt in ('docx', 'html', 'pdf'):\n"
                f"    try:\n        res[fmt] = minutes_record.export({FILED!r}, fmt, True, version='distributed')\n"
                "    except Exception as e:\n        res[fmt] = {'ok': False, 'message': repr(e)}\n"
                "print(json.dumps(res))")
        ex = self.pj(code)
        for fmt, col in (("docx", "F-docx"), ("html", "F-html"), ("pdf", "F-pdf")):
            r = ex.get(fmt) or {}
            if not r.get("ok"):
                out[col] = None
                continue
            pth = self.root / (r.get("path") or "")
            if fmt == "docx":
                with zipfile.ZipFile(pth) as z:
                    out[col] = " ".join(re.sub(r"<[^>]+>", "", z.read(n).decode("utf-8", "ignore")) for n in z.namelist() if n.endswith(".xml"))
            elif fmt == "html":
                out[col] = pth.read_text(encoding="utf-8", errors="ignore")
            else:
                out[col] = cap.read_text(encoding="utf-8", errors="ignore") if cap.is_file() else ""
        out["_facts"] = facts
        return out

    def label(self, item_id):
        self.pj("import sqlite3\n"
                "con = sqlite3.connect('system/tracker.db')\n"
                "con.execute(\"INSERT OR IGNORE INTO labels (name, builtin) VALUES ('Sensitive', 1)\")\n"
                f"con.execute(\"INSERT INTO item_labels (item_id, label) VALUES (?, 'Sensitive')\", ({item_id!r},))\n"
                "con.commit(); print(json.dumps(1))")

    def extras(self):
        X = self.extra = {}
        rows = (self.filed_dump or {}).get("upd_rows") or []
        kept_upd = [r for r in rows if r.get("kept_line") and "ABC-A-001" in json.dumps(r.get("cells"))]
        kept_upd_d = [r for r in rows if r.get("kept_line") and "ABC-D-003" in json.dumps(r.get("cells"))]
        self.notes.append("update rows in the filed record: " + json.dumps(rows, default=str)[:600])
        UA = "ABC-A-001: due 30-10-2026"
        # --- L1: an ordinary UPDATE line kept with 'Remove, keep its line' is not a new item in the distributed follow-up ---
        base = self.filed_texts()
        facts = base["_facts"]
        in_items = [i for i in facts.get("items") or [] if "ABC-A-001" in json.dumps(i) or "ABC-D-003" in json.dumps(i) or UA in json.dumps(i)]
        in_js = "ABC-A-001: due" in base["F-js"] or "due 30-10-2026" in base["F-js"]
        dfacts = self.draft_facts
        in_d = [i for i in dfacts.get("items") or [] if "ABC-A-001" in json.dumps(i) or "ABC-D-003" in json.dumps(i)]
        if not kept_upd:
            X["L1 kept ordinary UPDATE line is not a new item (filed follow-up)"] = ("N-A", "no kept update line was created in the filed record: " + json.dumps(rows, default=str)[:300])
        else:
            ok = not in_items and not in_js and not in_d
            X["L1 kept ordinary UPDATE line is not a new item (filed follow-up)"] = (
                "PASS" if ok else "FAIL",
                f"kept update row present (was={kept_upd[0].get('was')}, held={kept_upd[0].get('held', '<<absent>>')!r}); "
                f"F-facts items naming it: {len(in_items)}; F-js email body names it: {in_js}; D-facts items naming it: {len(in_d)}"
                + ("" if ok else " items=" + json.dumps(in_items + in_d)[:300]))
            shown = [c for c in ("F-docx", "F-html", "F-pdf") if base[c] and UA in base[c]]
            X["L1b kept ordinary update line still shown in the distributed minutes themselves (not over-withheld)"] = (
                "PASS" if len(shown) == 3 else "FAIL", f"UA line present in: {shown}")
        if kept_upd_d:
            X["L1c decision UPDATE kept line is not a new item"] = ("PASS" if not [i for i in facts.get('items') or [] if 'ABC-D-003' in json.dumps(i)] else "FAIL", "")
        else:
            X["L1c decision UPDATE kept line is not a new item"] = ("N-A", "the decision update (status Made) is not a kept line in the record (own tick row; no kept row to test)")
        # --- stale-held (a): kept UPDATE line, its target later labelled Sensitive, after filing ---
        if kept_upd:
            pre = base
            self.label("ABC-A-001")
            post = self.filed_texts()
            still = [c for c in ("F-facts", "F-js", "F-docx", "F-html", "F-pdf") if post[c] and UA in post[c]]
            X["S1 stale-held: kept UPDATE line whose target gets Sensitive AFTER filing is withheld (filed outputs)"] = (
                "PASS" if not still else "FAIL",
                f"the update line {UA!r} (a kept row with held={kept_upd[0].get('held', '<<absent>>')!r}, was={kept_upd[0].get('was')}) "
                f"appears in {still or 'none'} after ABC-A-001 is labelled Sensitive; before the label it was in "
                f"{[c for c in ('F-facts', 'F-js', 'F-docx', 'F-html', 'F-pdf') if pre[c] and UA in pre[c]]}")
        else:
            X["S1 stale-held: kept UPDATE line whose target gets Sensitive AFTER filing is withheld (filed outputs)"] = ("N-A", "no kept update line")
        # --- stale-held (b): kept NEW line: its item was rejected, so there is no tracker row a label can later be put on ---
        rej = self.pj("import sqlite3\ncon = sqlite3.connect('system/tracker.db')\n"
                      "n = {}\nfor t in ('actions','decisions','raid'):\n"
                      f"    n[t] = con.execute('select count(*) from ' + t + ' where ' + ('decision' if t=='decisions' else 'description') + ' like ?', ('%PLAIN-' + 'A-NEITHER-CTRL%',)).fetchone()[0]\n"
                      "print(json.dumps(n))")
        X["S2 stale-held: kept NEW line labelled Sensitive after filing"] = (
            "N-A", f"a kept new line's item is rejected on Approve, not stored in the tracker (rows with the NEITHER control text: {rej}), "
                   "so no label can be added to it afterwards; the label route that exists is the draft (S3)")
        # --- stale-held (c): ticked ordinary controls (real tracker rows) labelled Sensitive after filing ---
        ap = self.root / "system/staging/applied" / self.name
        data = json.loads((ap if ap.is_file() else self.root / "system/staging" / self.name).read_text(encoding="utf-8"))
        tid = {}
        for it in data["items"]:
            txt = (it.get("values") or {}).get("description") or (it.get("values") or {}).get("decision") or ""
            for k in KINDS:
                if marker(k, "TICK", "CTRL") in txt and it.get("result_id"):
                    tid[k] = it["result_id"]
        pre = self.filed_texts()
        for k, i in tid.items():
            self.label(i)
        post = self.filed_texts()
        for k, i in tid.items():
            mk = marker(k, "TICK", "CTRL")
            before = [c for c in ("F-facts", "F-js", "F-docx", "F-html", "F-pdf") if pre[c] and mk in pre[c]]
            after = [c for c in ("F-facts", "F-js", "F-docx", "F-html", "F-pdf") if post[c] and mk in post[c]]
            exp_before = [c for c in ("F-facts", "F-js") if k in "AD"] + ["F-docx", "F-html", "F-pdf"]
            X[f"S3 stale-held: ticked ordinary {KINDS[k]} ({i}) labelled Sensitive AFTER filing is withheld"] = (
                "PASS" if not after and set(before) >= set(exp_before) else "FAIL",
                f"present before the label in {before}; after the label in {after or 'none'}")
        # --- stale-held (d): in the draft, a kept line whose item is restored, labelled Sensitive, then kept again ---
        self.draft_stale()

    def pj_in(self, q, _id):
        """Which of the filed Distributed outputs of q's vault hold the update line."""
        UA = "ABC-A-001: due 30-10-2026"
        saved = (self.root, self.out)
        self.root, self.out = q.root, q.out
        try:
            t = self.filed_texts()
        finally:
            self.root, self.out = saved
        return [c for c in ("F-facts", "F-js", "F-docx", "F-html", "F-pdf") if t[c] and UA in t[c]]

    def draft_stale(self):
        """The one way a label can reach a line after it was kept: restore it, edit it to Sensitive, keep its line again (fresh vault)."""
        X = self.extra
        import sys as _s
        q = Probe.__new__(Probe)
        q.v = type(self.v)()
        q.root, q.track_mode = q.v.root, self.track_mode
        q.res, q.notes = {c: {} for c in cells()}, []
        q.out = TMP / f"out2-{os.getpid()}"
        q.out.mkdir(exist_ok=True)
        try:
            q.setup()
            n = q.n_of[("A", "NEITHER", "CTRL")]
            def ch(op):
                return q.pj("import minutes_record\n"
                            f"try:\n    r = minutes_record.change({DRAFT!r}, {op!r}); r.pop('doc', None)\nexcept Exception as e:\n    r = {{'ok': False, 'message': repr(e)[:120]}}\n"
                            "print(json.dumps(r))")
            r1 = ch({"op": "remove", "n": n, "keep_line": True})
            held1 = q.pj("import minutes_record, creaite_doc\n"
                         f"d = creaite_doc.read({DRAFT!r}); print(json.dumps([r.get('held', '<<absent>>') for s in d['sections'] for r in s.get('rows', []) if r.get('kept_line') and r.get('was') == '@{n}']))")
            # (i) edit the removed item's labels while it is only a kept line
            r2 = ch({"op": "edit", "n": n, "values": {"labels": ["Sensitive"]}})
            # (ii) restore, label, keep again
            r3 = ch({"op": "restore", "n": n})
            r4 = ch({"op": "edit", "n": n, "values": {"labels": ["Sensitive"]}})
            r4b = ch({"op": "edit", "n": n, "values": {"sensitive": True}}) if not r4.get("ok") else r4
            r5 = ch({"op": "remove", "n": n, "keep_line": True})
            held2 = q.pj("import minutes_record, creaite_doc\n"
                         f"d = creaite_doc.read({DRAFT!r}); print(json.dumps([r.get('held', '<<absent>>') for s in d['sections'] for r in s.get('rows', []) if r.get('kept_line') and r.get('was') == '@{n}']))")
            mk = marker("A", "NEITHER", "CTRL")
            q.pj(f"import creaite_doc, minutes_record\nd = creaite_doc.read({DRAFT!r}); d.setdefault('layout', {{}})['track'] = {{{str(n)!r}: ''}}\n"
                 f"r = minutes_record.save_page({DRAFT!r}, d); print(json.dumps(r['ok']))")
            f1 = q.pj(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({DRAFT!r}, 'distributed')))")
            appr = q.pj(f"import review\nprint(json.dumps(review.approve_minutes({q.name!r}, True, [])))")
            f2 = q.pj(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({FILED!r}, 'distributed')))")
            hit1, hit2 = mk in json.dumps(f1), mk in json.dumps(f2)
            if not r4.get("ok") and not r4b.get("ok"):
                X["S2/S3d draft route: kept line, item restored then labelled Sensitive, kept again, filed"] = (
                    "N-A", f"the route does not exist: a label or Sensitive mark cannot be added from the minutes (labels: {r4.get('message')}; "
                           f"sensitive value: {r4b.get('message')}); edit of a removed line: {r2.get('message')}")
            else:
              X["S2/S3d draft route: kept line, item restored then labelled Sensitive, kept again, filed"] = (
                "PASS" if not hit1 and not hit2 and appr.get("ok") else "FAIL",
                f"edit while only a kept line: ok={r2.get('ok')} ({str(r2.get('message'))[:70]}); restore ok={r3.get('ok')}; "
                f"edit labels ok={r4.get('ok')}; keep again ok={r5.get('ok')}; kept row held at first keep={held1}, after relabel={held2}; "
                f"line in draft follow-up={hit1}, in filed follow-up={hit2}")
            # S1b: the same kept update line, but the target is ALREADY Sensitive when the line is kept (fresh vault)
            q.v.cleanup(); shutil.rmtree(q.out, ignore_errors=True)
            q.v = type(self.v)(); q.root = q.v.root; q.out.mkdir(exist_ok=True)
            q.setup()
            q.label("ABC-A-001")
            q.pj(f"import creaite_doc, minutes_record\nd = creaite_doc.read({DRAFT!r}); d.setdefault('layout', {{}})['track'] = {{{str(q.upd_n['ABC-A-001'])!r}: ''}}\n"
                 f"r = minutes_record.save_page({DRAFT!r}, d); print(json.dumps(r['ok']))")
            g1 = q.pj(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({DRAFT!r}, 'distributed')))")
            appr = q.pj(f"import review\nprint(json.dumps(review.approve_minutes({q.name!r}, True, [])))")
            g2 = self.pj_in(q, "ABC-A-001")
            X["S1b same kept UPDATE line, target already Sensitive when kept: withheld (filed outputs)"] = (
                "PASS" if not g2 and appr.get("ok") else "FAIL", f"update line in filed outputs: {g2 or 'none'}")
        except Exception as e:  # noqa: BLE001
            X["S2/S3d draft route: kept line, item restored then labelled Sensitive, kept again, filed"] = ("N-A", f"could not drive: {type(e).__name__}: {str(e)[:200]}")
        finally:
            q.v.cleanup()
            shutil.rmtree(q.out, ignore_errors=True)

    # ---- judging ----
    def expected(self, col, c):
        """Whether a control's marker should be in this output."""
        t = self.choice(c)
        if t is None:                      # default: actions ticked, decisions and new risks neither (track.js defaultTrack)
            t = "y" if c[0] == "A" else ""
        if col == "F-polish":
            return False                   # the cover paragraph never carries items
        if col == "H-js":
            return t == "y" and c[0] in ("A", "D")      # only applied actions and decisions reach the hub
        if c[0] == "R" and col in ("D-facts", "D-js", "F-facts", "F-js"):
            return False                   # the follow-up lists decisions and actions only
        return t != "n"

    def mark(self, col, text, where):
        (self.out / f"{col}.txt").write_text(text, encoding="utf-8")
        for c in cells():
            if c[1] == "DEFAULT" and not self.track_mode:
                self.res[c][col] = "n/a"
                continue
            hit = marker(*c) in text
            if c[2] == "CTRL":
                exp = self.expected(col, c)
                self.res[c][col] = ("ok" if hit else "MISSING") if exp else ("UNEXPECTED" if hit else "ok")
            else:
                self.res[c][col] = "LEAK" if hit else "PASS"

    def na(self, col, why):
        self.notes.append(f"{col}: {why}")
        for c in cells():
            self.res[c][col] = "n/a"

    def run(self):
        self.setup()
        self.draft_phase()
        self.approve()
        self.client_visible_after_approval()
        self.dump_filed()
        self.filed_phase()
        try:
            self.extras()
        except Exception as e:  # noqa: BLE001
            self.extra = getattr(self, "extra", {})
            self.extra["EXTRAS ERROR"] = ("ERROR", f"{type(e).__name__}: {e}")
        return self

    def table(self):
        head = "| Kind | Track | Item | " + " | ".join(COLS) + " |\n|" + "---|" * (3 + len(COLS)) + "\n"
        rows = []
        for c in cells():
            r = self.res[c]
            rows.append(f"| {KINDS[c[0]]} | {c[1].lower()} | {VARS[c[2]]} | " +
                        " | ".join(("**" + r.get(x, "-") + "**") if r.get(x) in ("LEAK", "MISSING", "UNEXPECTED") else r.get(x, "-")
                                   for x in COLS) + " |")
        return head + "\n".join(rows)


if __name__ == "__main__":
    p = Probe()
    err = None
    try:
        p.run()
    except Exception as e:  # noqa: BLE001
        err = f"{type(e).__name__}: {e}"
    leaks = sorted({(KINDS[c[0]], c[1].lower(), VARS[c[2]], col) for c in cells() for col, s in p.res[c].items() if s == "LEAK"})
    head = git = subprocess.run(["git", "-C", str(WT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"# probe_matrix on {WT.name} @ {git} (mode: {'Track column' if p.track_mode else 'Remove / keep line (no Track column)'}),"
          f" mutant: {MUTANT or 'none'}")
    if err:
        print("ERROR:", err)
    print(p.table())
    print("\nNotes:", *p.notes, sep="\n- ")
    missing = sorted((KINDS[c[0]], c[1].lower(), col) for c in cells() for col, s in p.res[c].items() if s == "MISSING")
    unexp = sorted((KINDS[c[0]], c[1].lower(), col) for c in cells() for col, s in p.res[c].items() if s == "UNEXPECTED")
    print("\nExtra FILED-path checks (ADDED 9501f2cd):")
    for k, (st, why) in getattr(p, "extra", {}).items():
        print(f"  [{st}] {k}: {why}")
    print(f"\nMISSING cell values: {len(missing)}")
    for x in missing:
        print("  ", " / ".join(x))
    print(f"UNEXPECTED cell values: {len(unexp)}")
    print(f"\nLEAK cells: {len(leaks)}")
    for x in leaks:
        print("  ", " / ".join(x))
    if JSON_OUT:
        Path(JSON_OUT).write_text(json.dumps({"tree": git, "mutant": MUTANT, "error": err, "track_mode": p.track_mode,
                                              "track_states": getattr(p, "track_states", {}), "notes": p.notes, "filed_dump": getattr(p, "filed_dump", None), "hub_rows": getattr(p, "hub_rows_dump", None),
                                              "extra": getattr(p, "extra", {}), "missing": len(missing), "unexpected": len(unexp),
                                              "cells": {"/".join(c): p.res[c] for c in cells()}}, indent=1))
    if not KEEP:
        p.v.cleanup()
        shutil.rmtree(p.out, ignore_errors=True)
        shutil.rmtree(TMP, ignore_errors=True)
    else:
        print("vault kept:", p.root, "outputs:", p.out)
    sys.exit(2 if err else (1 if leaks else 0))
