"""BL-214: every visible input, select and textarea has a name a screen reader can read (not only a placeholder), in every
view and every Settings category, the Files filters first.

Run: python3 dev/tests/test_field_names.py   (needs Google Chrome; skipped otherwise)
A real browser and server on the sample data. The name is worked out as a browser does for these elements: aria-labelledby,
aria-label, a <label> (for= or wrapping), then title; a placeholder alone doesn't count.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

# The fields on screen that have no name, each as "where: id/class [placeholder]"
UNNAMED = r"""((where,root,all)=>{
  const named=el=>{ const by=(el.getAttribute('aria-labelledby')||'').split(/\s+/).filter(Boolean).map(i=>document.getElementById(i)).filter(Boolean);
    if(by.some(e=>e.textContent.trim())) return true;
    if((el.getAttribute('aria-label')||'').trim()) return true;
    if(el.labels&&[...el.labels].some(l=>l.textContent.trim())) return true;
    return !!(el.getAttribute('title')||'').trim(); };
  const out=[];
  for(const el of (root||document).querySelectorAll('input,select,textarea')){
    if(['hidden','file'].includes(el.type)&&el.type!=='file') continue;
    if(el.type==='hidden') continue;
    const r=el.getBoundingClientRect(), cs=getComputedStyle(el);
    if(el.type==='file'&&el.hidden) continue;
    if(!all&&(!r.width||!r.height||cs.visibility==='hidden'||el.closest('[hidden],[aria-hidden="true"]'))) continue;
    if(!named(el)) out.push(`${where}: ${el.tagName.toLowerCase()}${el.id?'#'+el.id:''}${el.className?'.'+String(el.className).split(' ')[0]:''} [${el.placeholder||el.type||''}]`);
  }
  return out;
})"""


class FieldNames(LiveBrowserCase):
    maxDiff = None
    shared_server = True

    def unnamed(self, where):
        return self.b.eval(f"{UNNAMED}({where!r})")

    def test_the_files_filters(self):
        self.b.eval("go('files')")
        self.b.wait("VIEW==='files'&&document.getElementById('fsName')")
        names = self.b.eval("""['fsName','fsType','fsFrom','fsTo'].map(id=>{ const el=document.getElementById(id);
          return el.getAttribute('aria-label')||[...(el.labels||[])].map(l=>l.textContent.trim()).join(' '); })""")
        self.assertEqual(names, ["Search file names", "File type", "From", "To"])
        self.assertEqual(self.b.eval("document.getElementById('fsName').placeholder"), "Search file names")   # kept as the example
        self.assertEqual(self.unnamed("files"), [])

    def test_every_settings_category(self):
        cats = self.b.eval("SETCATS.map(c=>c[0])")
        self.assertGreaterEqual(len(cats), 4)            # BL-320: Essentials, People and projects, Advanced, Health
        bad = []
        for cat in cats:
            self.b.eval(f"go('settings'); STAB='{cat}'; renderSettings();")
            self.b.wait(f"VIEW==='settings'&&SCAT==='{cat}'")
            self.b.pump(0.2)
            bad += self.unnamed(f"settings/{cat}")
        self.assertEqual(bad, [])

    def test_a_settings_row_ties_its_label_to_its_field(self):
        self.b.eval("go('settings'); STAB='general'; renderSettings();")
        self.b.wait("VIEW==='settings'&&document.querySelector('#v-settings .srow')")
        tied = self.b.eval("""[...document.querySelectorAll('#v-settings .srow')].filter(r=>r.querySelectorAll('input:not([type=hidden]),select,textarea').length===1)
          .map(r=>{ const f=r.querySelector('input:not([type=hidden]),select,textarea'), ids=(f.getAttribute('aria-labelledby')||'').split(' ');
            const l=r.querySelector(':scope>div:first-child>span[id]'); return !!f.getAttribute('aria-label')||[...(f.labels||[])].length>0||(!!l&&ids.includes(l.id)); })""")
        self.assertTrue(tied)
        self.assertTrue(all(tied))

    def test_no_settings_field_is_named_by_its_internal_key(self):
        """BL-279: the "Apply edits automatically" switch was named `autoApply`, its settings key. Every Settings field's
        accessible name is words, and that switch's is its row's label."""
        names = []
        for cat in self.b.eval("SETCATS.map(c=>c[0])"):
            self.b.eval(f"go('settings'); STAB='{cat}'; renderSettings();")
            self.b.wait(f"VIEW==='settings'&&SCAT==='{cat}'")
            if cat == "essentials":
                self.b.wait("!!document.querySelector('#set-essentials .srow')")
            self.b.pump(0.2)
            names += self.b.eval(r"""[...document.querySelectorAll('#v-settings input,#v-settings select,#v-settings textarea')].map(el=>{
              const by=(el.getAttribute('aria-labelledby')||'').split(/\s+/).filter(Boolean).map(i=>document.getElementById(i)).filter(Boolean);
              return [el.dataset.k||el.id||'', by.length?by.map(e=>e.textContent.trim()).join(' '):(el.getAttribute('aria-label')||'')]; })""")
        keys = [n for k, n in names if k and n == k or re.fullmatch(r"[a-z]+[A-Z]\w*", n or "")]
        self.assertEqual(keys, [])
        self.assertIn("Save my changes at once", [n for _, n in names])      # BL-320: the switch is an Essential, named by its row

    def test_the_dialogs(self):
        """The page's own dialogs (Person, Generate, Move a card…), open or not: every field in them has a name."""
        self.assertGreaterEqual(self.b.eval("document.querySelectorAll('dialog').length"), 3)
        bad = self.b.eval(f"[...document.querySelectorAll('dialog')].flatMap(d=>{UNNAMED}('dialog#'+d.id,d,true))")
        self.assertEqual(bad, [])

    def test_every_view(self):
        views = self.b.eval("[...document.querySelectorAll('.rail button[data-v]')].map(b=>b.dataset.v)")
        self.assertIn("files", views)
        bad = []
        for v in views:
            self.b.eval(f"go({v!r})")
            self.b.wait(f"VIEW==={v!r}")
            self.b.pump(0.3)
            bad += self.unnamed(v)
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("VIEW==='cockpit'")
        bad += self.unnamed("cockpit")
        for kind in ("actions", "raid", "decisions", "all"):
            self.b.eval("go('work')")
            self.b.click(f'#wtabs [data-t="{kind}"]')
            self.b.wait(f"document.querySelector('#wtabs [data-t=\"{kind}\"]').getAttribute('aria-selected')==='true'")
            self.b.pump(0.3)
            bad += self.unnamed(f"work/{kind}")
            if self.b.eval("document.querySelector('#wlay [data-lay=board]').getBoundingClientRect().width>0"):
                self.b.click("#wlay [data-lay=board]")                     # the Board's fields too, where there is one
                self.b.pump(0.3)
                bad += self.unnamed(f"work/{kind}/board")
                self.b.click("#wlay [data-lay=list]")
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
