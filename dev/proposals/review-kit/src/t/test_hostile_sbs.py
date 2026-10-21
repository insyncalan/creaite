import json, sys, unittest, zipfile
from pathlib import Path
sys.path.insert(0, __import__("os").environ["KIT_CK"] + "/dev/tests")
import test_sbs_panes as S
INT, CLI, WEEK = S.INT, S.CLI, S.WEEK
HOST = " Xylohostile Budget overrun on phase one is being absorbed. Confirm tester names ABC-A-005 Omar Ali confidential."

class Hostile(S.SideBySideEditing):
    def client_raw(self):
        return json.dumps(self.api("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK}))
    def files_with(self, word):
        hits = []
        for p in self.v.root.rglob("*"):
            if p.is_file() and p.suffix in (".html", ".json", ".docx", ".md"):
                try:
                    b = p.read_bytes()
                    if p.suffix == ".docx":
                        with zipfile.ZipFile(p) as z: b = z.read("word/document.xml")
                    if word.encode() in b: hits.append(str(p.relative_to(self.v.root)))
                except Exception: pass
        return hits
    def test_h1_unsaved_internal_never_saved_into_client_without_match(self):
        self.open_side(); self.spy_saves()
        self.write(INT, HOST)
        self.q("document.querySelector('#v-reporting .sheet-root').dispatchEvent(new KeyboardEvent('keydown',{key:'s',metaKey:true,bubbles:true}))")
        self.write(CLI, " Quillclient.")
        self.b.pump(4)
        self.assertIn("Quillclient", self.saved("client", has="Quillclient"))
        self.assertNotIn("Xylohostile", self.client_raw())
        hits = [h for h in self.files_with("Xylohostile") if "Client" in h or "client" in h]
        self.assertEqual(hits, [], hits)
        print("saves:", self.q("window.__saves"))
        # reload while internal dirty
        self.write(INT, " Xylotwo")
        self.b.reload("typeof go==='function' && LIVE"); self.b.pump(2)
        self.assertNotIn("Xylotwo", self.client_raw())
    def test_h2_match_all_reads_unsaved_internal_and_gate_holds(self):
        self.open_side()
        self.write(INT, HOST)
        print("matchall disabled:", self.q("document.querySelector('[data-crmatchall]').disabled")); self.q("document.querySelector('[data-crmatchall]').click()")
        self.b.pump(4)
        raw = self.client_raw()
        print("client draft holds hostile after Match all:", "Xylohostile" in raw, "ABC-A-005" in raw, "Omar" in raw)
        # approve internal then try export / approve client
        doc = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})["doc"]
        next(x for x in doc["sections"] if x["id"] == "health")["text"] = "UAT start slipped two weeks."
        self.api("/api/report/save", {"doc": doc, "base_version": doc["version"]})
        a = self.api("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "force": True}); print("int approve", a.get("ok"))
        for fmt in ("html", "docx", "pdf", "md"):
            r = self.api("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": WEEK, "fmt": fmt, "on_clash": "number"})
            print(fmt, "export ok:", r.get("ok"), str(r.get("message") or r.get("findings"))[:200])
        c = self.api("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})["doc"]
        r = self.api("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "doc": c, "base_version": c.get("version")})
        print("client approve ok:", r.get("ok"), str(r.get("message") or r.get("findings"))[:300])
        print("files with hostile:", self.files_with("Xylohostile"))
    def test_h3_add_text_global_after_right_then_left(self):
        self.open_side()
        self.focus_in(CLI); self.focus_in(INT)
        self.q("window.__n=0")
        # global entry (menus): addTextSection from the store follows the pane used last (INT)
        r = self.q("(async()=>{const m=await import('/src/stores/textSection.js').catch(()=>null); return !!m})()")
        self.b.click(f"{INT} [data-addtext]")
        self.b.pump(1)
        free = self.q(f"[...document.querySelectorAll('{INT} > section[data-id^=free_]')].map(s=>s.dataset.id)")
        self.write(INT, "Xylothree", free[0])
        self.b.pump(3)
        self.assertNotIn("Xylothree", self.client_raw())
        self.assertEqual(self.q(f"document.querySelectorAll('{CLI} section[data-id^=free_]').length"), 0)
        sec = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})["doc"]
        print("internal free audience:", [s.get("audience") for s in sec["sections"] if s["id"].startswith("free_")])

if __name__ == "__main__":
    unittest.main(defaultTest="Hostile.test_h1_unsaved_internal_never_saved_into_client_without_match Hostile.test_h2_match_all_reads_unsaved_internal_and_gate_holds Hostile.test_h3_add_text_global_after_right_then_left".split(), verbosity=2)
