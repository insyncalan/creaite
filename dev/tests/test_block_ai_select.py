"""BL-301 D (dev/COMPONENTS.md §3, §6): AiBar and AiSuggestion, the building blocks of AI on selected text, on a small fixture
(two editors of its own: many lines and one line), with no Claude run: the suggestion is put in the store by hand.

AiBar: a named toolbar over the selection; AI ▾ is the Menu block with the place's options ("Or say what you want…" last, part E's
registered items just before it); Alt+/ opens the menu with focus in it; "Or say what you want…" becomes a box with focus in it and
Esc goes back to the text. AiSuggestion: a non-modal dialog named by its heading; focus to the first thing to press for each state
(ask, running, failed, ready); Esc discards with focus back to the text; Show changes is a toggle (aria-pressed) showing <del> and
<ins>; the check's notes are a named list; its text is text, never markup; Accept is one transaction ⌘Z undoes, and a one-line
field stays one line (Alan, 14-10-2026).

Run: python3 dev/tests/test_block_ai_select.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META, ALT = 4, 1
MANY = "Sara to send the plan.\nOmar to book the room."

MOUNT = """(t=>{ document.getElementById('aiFix')?.remove(); const box=document.createElement('div'); box.id='aiFix';
  box.style.cssText='position:fixed;top:80px;left:80px;width:420px;z-index:100;background:var(--surface)';
  document.body.appendChild(box); const a=document.createElement('div'), o=document.createElement('div'); a.id='aiMany'; o.id='aiOne';
  box.append(a,o); aiSug.value=null; aiBar.value=null;
  window.AIM=creaiteEditor(a,{features:'plain',text:t,ai:{place:'plain',project:()=>'ABC'}});
  window.AIO=creaiteEditor(o,{features:'plain',text:'Data access late',multiline:false,ai:{place:'line',project:()=>'ABC'}});
  return true; })"""
LAYER = "#aiLayer"


class AiBlocks(LiveBrowserCase):
    shared_server = True        # nothing it does is written

    def setUp(self):
        super().setUp()
        self.b.eval(f"{MOUNT}({json.dumps(MANY)})")
        self.b.wait("!!document.querySelector('#aiMany.ProseMirror') && !!document.querySelector('#aiOne.ProseMirror')")
        self.addCleanup(lambda: self.b and self.b.eval(
            "aiSug.value=null; aiBar.value=null; AIM.destroy(); AIO.destroy(); document.getElementById('aiFix')?.remove(); true"))

    def select_all(self, sel):
        b = self.b
        b.click(sel)
        b.key("a", META)
        b.wait(f"document.querySelector('{LAYER} .aibar')")

    def sug(self, h, status, **more):
        """Put a suggestion for all of `h`'s text in the store, as a run would."""
        extra = json.dumps(more)
        self.b.eval(f"""(()=>{{ const h={h}; h.editor.commands.selectAll(); const r=edSelection(h);
          aiSug.value={{h, ai:{{place:'plain'}}, range:r, option:'rewrite', instruction:'', label:'Rewrite clearly', status:{status!r},
            top:120, left:120, ...{extra}}}; return true; }})()""")
        self.b.wait(f"document.querySelector('{LAYER} .aisug')")

    # ----- AiBar -----

    def test_the_bar_is_a_named_toolbar_with_the_menu_block_and_the_places_options(self):
        b = self.b
        self.select_all("#aiMany")
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .aibar').getAttribute('role')"), "toolbar")
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .aibar').getAttribute('aria-label')"), "AI on the selected text")
        btn = f"{LAYER} .aibar button[aria-haspopup]"
        self.assertEqual(b.eval(f"document.querySelector('{btn}').getAttribute('aria-expanded')"), "false")
        b.click(btn)
        b.wait(f"document.querySelector('{LAYER} [role=menu]')")
        self.assertEqual(b.eval(f"[...document.querySelectorAll('{LAYER} [role=menu] [data-ai]')].map(e=>e.dataset.ai)"),
                         ["rewrite", "shorter", "longer", "executive", "spelling", "custom"])
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} [role=menu]').getAttribute('aria-label')"), "AI on the selected text")
        b.key("Escape")                                                           # the Menu block: Esc closes, focus to its button
        b.wait(f"!document.querySelector('{LAYER} [role=menu]')")
        self.assertTrue(b.eval(f"document.activeElement===document.querySelector('{btn}')"))

    def test_a_one_line_field_offers_the_one_line_options(self):
        b = self.b
        self.select_all("#aiOne")
        b.click(f"{LAYER} .aibar button[aria-haspopup]")
        b.wait(f"document.querySelector('{LAYER} [role=menu]')")
        self.assertEqual(b.eval(f"[...document.querySelectorAll('{LAYER} [role=menu] [data-ai]')].map(e=>e.dataset.ai)"),
                         ["rewrite", "shorter", "executive", "spelling", "custom"])
        b.key("Escape")

    def test_alt_slash_opens_the_menu_with_focus_in_it(self):
        b = self.b
        self.select_all("#aiMany")
        b.key("/", ALT)
        b.wait(f"document.querySelector('{LAYER} [role=menu]') && document.activeElement.closest('[role=menu]')")
        b.key("Escape")

    def test_say_what_you_want_is_a_named_box_and_esc_goes_back_to_the_text(self):
        b = self.b
        self.select_all("#aiMany")
        b.click(f"{LAYER} .aibar button[aria-haspopup]")
        b.wait(f"document.querySelector('{LAYER} [role=menu]')")
        b.click(f"{LAYER} [role=menu] [data-ai=custom]")
        b.wait(f"document.activeElement && document.activeElement.matches('{LAYER} .aiask input')")
        self.assertEqual(b.eval("document.activeElement.getAttribute('aria-label')"), "Say what you want done with the selected text")
        self.assertEqual(b.eval("document.activeElement.maxLength"), 400)
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .aiask [type=submit]').getAttribute('aria-disabled')"), "true")
        b.key("Escape")
        b.wait("document.activeElement===document.getElementById('aiMany')")

    def test_part_e_items_go_before_say_what_you_want_and_get_the_selection(self):
        b = self.b
        b.eval("window.GOT=null; aiAction({id:'mkact', name:'Make this an action…', places:['plain'], run:(r,h,ai)=>{ GOT=[r.text, ai.place, h===AIM]; }})")
        self.addCleanup(lambda: self.b and self.b.eval("AI_ACTIONS.splice(0); true"))
        self.select_all("#aiMany")
        b.click(f"{LAYER} .aibar button[aria-haspopup]")
        b.wait(f"document.querySelector('{LAYER} [role=menu]')")
        ids = b.eval(f"[...document.querySelectorAll('{LAYER} [role=menu] [data-ai]')].map(e=>e.dataset.ai)")
        self.assertEqual(ids[-2:], ["mkact", "custom"])
        b.click(f"{LAYER} [role=menu] [data-ai=mkact]")
        b.wait("GOT")
        self.assertEqual(b.eval("GOT"), [MANY, "plain", True])
        self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aisug')"))   # no Claude run, no suggestion
        self.assertEqual(b.eval("aiItems('line').map(x=>x.id).includes('mkact')"), False)   # only where it said
        self.assertEqual(b.eval("(aiAction({id:'rewrite',name:'x',run:()=>{}}), AI_ACTIONS.length)"), 1)   # never an option's id

    # ----- AiSuggestion -----

    def test_the_suggestion_is_a_named_dialog_and_each_state_focuses_its_first_button(self):
        b = self.b
        for status, first, more in (("ask", "Send to Claude", {}), ("running", "Stop", {}),
                                    ("failed", "Try again", {"message": "No suggestion came back"}),
                                    ("ready", "Accept", {"text": "Sara sends the plan.", "notes": []})):
            self.sug("AIM", status, **more)
            card = f"{LAYER} .aisug"
            self.assertEqual(b.eval(f"document.querySelector('{card}').getAttribute('role')"), "dialog")
            self.assertEqual(b.eval(f"document.querySelector('{card}').getAttribute('aria-modal')"), "false")
            self.assertEqual(b.eval(f"document.getElementById(document.querySelector('{card}').getAttribute('aria-labelledby')).textContent"),
                             "Rewrite clearly")
            b.wait(f"document.activeElement && document.activeElement.textContent.includes({first!r})")
            if status == "failed":
                self.assertEqual(b.eval(f"document.querySelector('{card} [role=alert]').textContent"), "No suggestion came back")
            if status == "running":
                self.assertTrue(b.eval(f"document.querySelector('{card} [role=status]').textContent.includes('it sees only this text')"))
            b.eval("aiSug.value=null")
            b.wait(f"!document.querySelector('{card}')")

    def test_esc_discards_and_focus_goes_back_to_the_text(self):
        b = self.b
        self.sug("AIM", "ready", text="Changed.", notes=[])
        b.wait("document.activeElement && document.activeElement.textContent==='Accept'")
        b.key("Escape")
        b.wait(f"!document.querySelector('{LAYER} .aisug')")
        b.wait("document.activeElement===document.getElementById('aiMany')")
        self.assertEqual(b.eval("AIM.value()"), MANY)                            # nothing changed

    def test_show_changes_is_a_toggle_and_the_notes_are_a_named_list(self):
        b = self.b
        self.sug("AIM", "ready", text="Sara to send the plan.\nOmar books the room.",
                 notes=[{"id": "names-lost", "note": "It leaves out Omar."}])
        tog = f"{LAYER} .aisug button[aria-pressed]"
        self.assertEqual(b.eval(f"document.querySelector('{tog}').getAttribute('aria-pressed')"), "false")
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .ainotes').getAttribute('aria-label')"), "Check it")
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .ainotes li').textContent"), "It leaves out Omar.")
        b.click(tog)
        b.wait(f"document.querySelector('{tog}').getAttribute('aria-pressed')==='true'")
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .aitext').getAttribute('aria-label')"), "The changes")
        self.assertIn("to book", b.eval(f"[...document.querySelectorAll('{LAYER} .aitext del')].map(e=>e.textContent).join('')"))
        self.assertIn("books", b.eval(f"[...document.querySelectorAll('{LAYER} .aitext ins')].map(e=>e.textContent).join('')"))
        b.click(tog)
        b.wait(f"!document.querySelector('{LAYER} .aitext del')")
        self.sug("AIM", "ready", text=MANY, notes=[])
        self.assertIn("Keeps your dates, numbers, names and item IDs", b.eval(f"document.querySelector('{LAYER} .aisug').textContent"))

    def test_its_text_is_text_never_markup(self):
        b = self.b
        self.sug("AIM", "ready", text="<b>bold</b> <img src=x onerror=alert(1)>", notes=[{"id": "x", "note": "<i>not italic</i>"}],
                 label="<em>Label</em>")
        self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aitext b, {LAYER} .aisug img, #aiSugH em, {LAYER} .ainotes i')"))
        self.assertIn("<b>bold</b>", b.eval(f"document.querySelector('{LAYER} .aitext').textContent"))
        self.assertEqual(b.eval("document.getElementById('aiSugH').textContent"), "<em>Label</em>")

    def test_accept_is_one_transaction_and_one_undo_takes_it_back(self):
        b = self.b
        self.sug("AIM", "ready", text="Sara sends the plan.\nOmar books the room.", notes=[])
        b.click(f"{LAYER} .aisug [data-aifirst]")
        b.wait(f"!document.querySelector('{LAYER} .aisug')")
        self.assertEqual(b.eval("AIM.value()"), "Sara sends the plan.\nOmar books the room.")
        b.key("z", META)
        b.wait(f"AIM.value()==={json.dumps(MANY)}")

    def test_a_one_line_field_stays_one_line_whatever_the_suggestion(self):
        b = self.b
        self.sug("AIO", "ready", text="Data access\nis late\n\nagain", notes=[])
        b.click(f"{LAYER} .aisug [data-aifirst]")
        b.wait(f"!document.querySelector('{LAYER} .aisug')")
        self.assertEqual(b.eval("[AIO.value(), document.querySelectorAll('#aiOne p').length]"), ["Data access is late again", 1])

    def test_accept_refuses_when_the_text_changed_meanwhile(self):
        b = self.b
        self.sug("AIM", "ready", text="Replaced.", notes=[])
        b.eval("AIM.editor.commands.insertContentAt(1,'X'); true")
        b.click(f"{LAYER} .aisug [data-aifirst]")
        b.pump(0.2)
        self.assertEqual(b.eval("AIM.value()"), "X" + MANY)                       # nothing replaced
        self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} .aisug')"))
        self.assertIn("changed since you asked", b.eval("document.getElementById('snack').textContent"))


if __name__ == "__main__":
    unittest.main()
