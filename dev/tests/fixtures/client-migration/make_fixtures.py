"""Make the client-output migration fixtures (#239 step 3) with the code from BEFORE the snapshot: v2.5.0's writers. The data is
fictional (test_reports.populate). Run once, against a plain copy of the v2.5.0 tree (not this one):

    git archive <v2.5.0 commit> | tar -x -C /some/empty/dir
    python3 dev/tests/fixtures/client-migration/make_fixtures.py /some/empty/dir

It starts that tree's live server in a throwaway vault (its own test harness), makes the internal week and the client report as
2.5.0 did (draft, save, approve), stages the older Word client report (report.py client-stage) and the client-safe steerco one-pager
(report.py steerco-stage), and copies what those writers wrote here, byte for byte:

  client-draft.html             the client report's saved draft (system/staging/drafts/)
  client-filed.html             the filed client report (the project's Reports folder), as 2.5.0's Approve filed it: no snapshot
  client-filed-edited.html      the same file hand-edited on disk (one shown section names a hidden action, its owner, "confidential")
  word-client-report.docx       report.py client-stage's Word draft, and its proposal (word-client-report.proposal.json)
  steerco-client.docx           report.py steerco-stage --version client's Word draft, and its proposal (steerco-client.proposal.json)
  gate-word-client-report.docx  report.py client-stage's Word draft (and gate-word-client-report.proposal.json) in the vault of
                                test_client_gate's fixture (client_gate_support.Base: the internal health reason, project DEF)
  MANIFEST.json                 the source tree's VERSION, the commit given, each file's SHA-256
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(OLD / "dev" / "tests"))
import test_reports as T  # noqa: E402  (the OLD tree's harness: its Vault copies the OLD tree)

WEEK = "2026-10-09"
CLIENT_STEM = "2026-10-09 Client report - Example Programme (Example Client Ltd)"


class Make(T.ReportRoutes):
    def runTest(self):
        pass


def gate_fixture():
    """The older Word client report as 2.5.0's client-stage made it in test_client_gate's vault (client_gate_support.Base)."""
    import client_gate_support as G

    class B(G.Base):
        def runTest(self):
            pass
    b = B()
    b.setUp()
    try:
        spec = b.v.root / "system/staging/drafts/client.json"
        spec.write_text(json.dumps({"code": "ABC", "summary": ["Phase two is being prepared."], "progress": ["Plan revised"],
                                    "next_steps": ["Sign the statement of work"], "input_needed": ["Signature by 16-10"],
                                    "period_start": "2026-10-01"}), encoding="utf-8")
        b.v.at("client-stage", str(spec), script="report.py")
        prop = next((b.v.root / "system/staging").glob("proposed-*-client-ABC.json"))
        data = json.loads(prop.read_text(encoding="utf-8"))
        return {"gate-word-client-report.docx": (b.v.root / data["report"]["draft"]).read_bytes(),
                "gate-word-client-report.proposal.json": prop.read_bytes()}
    finally:
        b.tearDown()


def main():
    Make.setUpClass()
    m = Make()
    v = m.v
    out = {}
    try:
        r = m.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})
        m.section(r["doc"], "health")["text"] = "UAT start slipped two weeks."
        assert m.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})["ok"]
        a = m.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "force": True})
        assert a["ok"], a
        r = m.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        assert r["ok"], r
        m.section(r["doc"], "summary")["text"] = "Phase two is being prepared; the plan was revised this week."
        s = m.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})
        assert s["ok"], s
        draft = v.root / "system/staging/drafts" / f"{CLIENT_STEM}.html"
        out["client-draft.html"] = draft.read_bytes()
        a = m.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        assert a["ok"], a
        filed = v.root / a["path"]
        out["client-filed.html"] = filed.read_bytes()
        text = filed.read_text(encoding="utf-8")
        old = "Phase two is being prepared; the plan was revised this week."
        assert text.count(old) >= 1
        edited = text.replace(old, "Alan Carter owns ABC-A-001 Escalate data access to the client CIO. This is confidential.")
        out["client-filed-edited.html"] = edited.encode("utf-8")
        for name, spec, script_args in (
                ("word-client-report", {"code": "ABC", "summary": ["Phase two is being prepared."], "progress": ["Plan revised"],
                                        "next_steps": ["Sign the statement of work"], "input_needed": ["Signature by 16-10"],
                                        "period_start": "2026-10-01", "force": True}, "client-stage"),
                ("steerco-client", {"code": "ABC", "version": "client", "steerco_date": WEEK, "since": "2026-10-01",
                                    "summary": ["Phase two is being prepared."], "force": True}, "steerco-stage")):
            f = v.root / "system/staging/drafts" / f"{name}.json"
            f.write_text(json.dumps(spec), encoding="utf-8")
            before = set((v.root / "system/staging").glob("proposed-*.json"))
            v.at(script_args, str(f), script="report.py")
            prop = next(iter(set((v.root / "system/staging").glob("proposed-*.json")) - before))
            data = json.loads(prop.read_text(encoding="utf-8"))
            out[f"{name}.docx"] = (v.root / data["report"]["draft"]).read_bytes()
            out[f"{name}.proposal.json"] = prop.read_bytes()
        out.update(gate_fixture())
        version = (OLD / "VERSION").read_text().strip()
        for n, b in out.items():
            (HERE / n).write_bytes(b)
        manifest = {"made_by": "dev/tests/fixtures/client-migration/make_fixtures.py", "source_version": version,
                    "source_commit": sys.argv[2] if len(sys.argv) > 2 else "",
                    "files": {n: hashlib.sha256(b).hexdigest() for n, b in sorted(out.items())}}
        (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(manifest, indent=1))
    finally:
        Make.tearDownClass()
        shutil.rmtree(OLD / "dev" / "tests" / "__pycache__", ignore_errors=True)


if __name__ == "__main__":
    main()
