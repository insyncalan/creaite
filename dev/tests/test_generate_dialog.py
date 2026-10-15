"""#110 part A: the Generate dialog, redesigned, and the fold after a draft.

736px wide (460 x 1.6) at desktop and at 900px; Generate always in view; four quiet settings in one strip, each opening the
Picker block's menu (keyboard: Tab, arrows, Enter, Esc); Dates... shows its two boxes only when chosen; one hint line; Steer it
as the body with three starters that append and never fill or send; Draw on a folded line with a two-column list, and the
Client-safe state; the footer's buttons and the ⌘↵ hint; after a draft the setup folds to one summary line with Change
settings, and closing, discarding or a failure puts it back. Every handler acts by id or data attribute (the strip is
reversed in one test and the controls still work), so a redraw loses nothing.

Run: python3 dev/tests/test_generate_dialog.py   (needs Google Chrome; skipped otherwise)
A stand-in Claude (drafts_fake.py) words the facts, so no model is called.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import drafts_fake  # noqa: E402
from test_drafts_forms import secret_world  # noqa: E402
from test_drafts_update import DraftCase  # noqa: E402

STARTERS = {"risks": "Lead with risks", "decisions": "Lead with decisions needed", "plain": "Plain words, no jargon"}
CONTRAST = """(()=>{ const rgb=c=>{ const m=c.match(/[\\d.]+/g).map(Number); return m.length>3&&m[3]===0?null:m.slice(0,3); };
  const lum=c=>{ const f=v=>{ v/=255; return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4); }; return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2]); };
  const ratio=(a,b)=>{ const x=lum(a),y=lum(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); };
  const bgOf=el=>{ for(let e=el;e;e=e.parentElement){ const c=rgb(getComputedStyle(e).backgroundColor); if(c) return c; } return [255,255,255]; };
  return (sel,bg)=>{ const el=document.querySelector(sel); const cs=getComputedStyle(el); return ratio(rgb(cs.color), bg?rgb(getComputedStyle(document.querySelector(bg)).backgroundColor):bgOf(el)); }; })()"""


class GenerateDialog(DraftCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        secret_world(v)
        cls.fake = drafts_fake.install(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake), "CREAITE_NOW": "2026-10-09 13:00"}

    def setUp(self):
        super().setUp()
        self.b.eval("openGen('ABC')")
        self.b.wait("document.getElementById('genDlg').open")

    def pick(self, trigger, label):
        b = self.b
        b.click(trigger)
        b.wait("document.querySelector('.pkpop [role=option]')")
        b.eval(f"[...document.querySelectorAll('.pkpop [role=option]')].find(o=>o.textContent.trim().startsWith({label!r})).click()")

    def rect(self, sel):
        return self.b.eval(f"(()=>{{ const r=document.querySelector({sel!r}).getBoundingClientRect(); return {{l:r.left,t:r.top,r:r.right,b:r.bottom,w:r.width,h:r.height}}; }})()")

    def visible(self, sel):
        return self.b.eval(f"(()=>{{ const e=document.querySelector({sel!r}); return !!e&&e.getClientRects().length>0&&getComputedStyle(e).visibility!=='hidden'; }})()")

    def hold_drafts(self):
        """Hold /api/draft until released, and count what is sent (to see the state while a draft is being written)."""
        self.b.eval("""(()=>{ window.__sent=0; window.__f=window.fetch; window.fetch=(u,o)=>{ if(String(u).includes('/api/draft')){ window.__sent++;
          if(window.__hold) return new Promise(r=>{ window.__rel=()=>r(window.__f(u,o)); }); } return window.__f(u,o); }; window.__hold=true; })()""")

    # ── the frame ──
    def test_it_is_736px_wide_at_desktop_and_at_900px_and_nothing_overflows(self):
        b = self.b
        self.assertEqual(self.rect("#genDlg")["w"], 736)                         # 460 x 1.6
        self.pick("#genAud", "Steering committee")
        self.pick("#genFormKind", "Three-line update")                            # the longest words in the strip
        for w, h in ((1400, 900), (900, 800)):
            b.resize(w, h)
            b.pump(0.2)
            self.assertEqual(self.rect("#genDlg")["w"], 736, f"{w}px")
            over = b.eval("""(()=>{ const d=document.getElementById('genDlg'), out=[];
              for(const e of d.querySelectorAll('.genbody, .gv, .genhint, .gensteer, .genfoot')){ if(e.scrollWidth>e.clientWidth+1) out.push(e.className||e.id); }
              const r=d.getBoundingClientRect(); if(r.left<0||r.right>innerWidth) out.push('dialog'); return out; })()""")
            self.assertEqual(over, [], f"{w}px")
        self.assertEqual(b.errors, [])

    def test_generate_stays_in_view_at_900_wide_and_800_tall_even_in_the_tallest_state(self):
        b = self.b
        b.resize(900, 800)
        b.pump(0.2)
        states = [lambda: None,                                                    # the default
                  lambda: b.eval("document.getElementById('genSrcBtn').click()"),   # Draw on open
                  lambda: self.pick("#genAud", "Client-safe")]                      # Client-safe: the note as well
        for set_up in states:
            set_up()
            b.pump(0.1)
            go, dlg = self.rect("#genGo"), self.rect("#genDlg")
            self.assertGreaterEqual(go["t"], 0)
            self.assertLessEqual(go["b"], 800)
            self.assertLessEqual(dlg["b"], 800)
            self.assertGreaterEqual(dlg["t"], 0)
            self.assertEqual(go["h"], 32)                                           # ordinary 32px buttons
            self.assertEqual(self.rect("#genCancel")["h"], 32)

    def test_a_short_window_scrolls_the_body_and_keeps_the_footer(self):
        b = self.b
        b.eval("document.getElementById('genSrcBtn').click()")
        b.resize(900, 520)
        b.pump(0.2)
        self.assertLessEqual(self.rect("#genGo")["b"], 520)
        self.assertGreater(b.eval("(()=>{ const e=document.querySelector('.genbody'); return e.scrollHeight-e.clientHeight; })()"), 0)

    # ── the strip ──
    def test_four_quiet_fields_with_their_labels_options_and_defaults(self):
        b = self.b
        self.assertEqual(b.eval("[...document.querySelectorAll('.genstrip label')].map(x=>x.textContent)"), ["Period", "Form", "Audience", "Length"])
        self.assertEqual(b.eval("[...document.querySelectorAll('.genstrip .genq')].map(x=>[x.id,x.querySelector('.gv').textContent,x.dataset.v])"),
                         [["genDays", "Last 7 days", "7"], ["genFormKind", "Current state", "current"], ["genAud", "Internal", "internal"], ["genLen", "Standard", "standard"]])
        lists = {}
        for trig in ("#genDays", "#genFormKind", "#genAud", "#genLen"):
            b.click(trig)
            b.wait("document.querySelector('.pkpop [role=option]')")
            lists[trig] = b.eval("[...document.querySelectorAll('.pkpop [role=option]')].map(x=>x.textContent.trim())")
            self.assertEqual(b.eval(f"document.querySelector({trig!r}).getAttribute('aria-expanded')"), "true")
            b.key("Escape")
        self.assertEqual(lists, {"#genDays": ["Last 7 days", "Last 14 days", "Last 30 days", "Dates…"],
                                 "#genFormKind": ["Current state", "Steering note", "Three-line update", "Email paragraph", "Teams message"],
                                 "#genAud": ["Internal", "Client-safe", "Steering committee", "Sponsor"], "#genLen": ["Short", "Standard", "Fuller"]})
        self.assertTrue(b.eval("document.getElementById('genDlg').open"))           # Esc closed the menu, not the dialog

    def test_a_field_shows_a_hairline_only_when_pointed_at_or_focused(self):
        b = self.b
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('genAud')).borderTopColor"), "rgba(0, 0, 0, 0)")
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('genAud')).backgroundColor"), "rgba(0, 0, 0, 0)")
        b.eval("document.getElementById('genFormKind').focus()")
        b.key("Tab")                                                                                  # a keyboard arrival, so the focus ring and the hairline show
        self.assertEqual(b.eval("document.activeElement.id"), "genAud")
        self.assertNotEqual(b.eval("getComputedStyle(document.getElementById('genAud')).borderTopColor"), "rgba(0, 0, 0, 0)")
        self.assertNotEqual(b.eval("getComputedStyle(document.getElementById('genAud')).backgroundColor"), "rgba(0, 0, 0, 0)")
        self.assertNotEqual(b.eval("getComputedStyle(document.getElementById('genAud')).outlineStyle"), "none")             # visible focus
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('genDays')).borderTopColor"), "rgba(0, 0, 0, 0)")

    def test_the_menus_work_from_the_keyboard(self):
        b = self.b
        b.eval("document.getElementById('genDays').focus()")
        b.key("Enter")
        b.wait("document.querySelector('.pkpop [role=option]')")
        self.assertEqual(b.eval("document.activeElement.textContent.trim()"), "Last 7 days")      # focus on the chosen option
        b.key("ArrowDown")
        self.assertEqual(b.eval("document.activeElement.textContent.trim()"), "Last 14 days")
        b.key("End")
        self.assertEqual(b.eval("document.activeElement.textContent.trim()"), "Dates…")
        b.key("Escape")
        self.assertEqual(b.eval("!!document.querySelector('.pkpop')"), False)
        self.assertEqual(b.eval("document.activeElement.id"), "genDays")                             # focus back on the field, visible
        self.assertTrue(b.eval("document.getElementById('genDlg').open"))
        b.key("ArrowDown")                                                                            # a down arrow opens it too
        b.wait("document.querySelector('.pkpop [role=option]')")
        b.key("ArrowDown")
        b.key("Enter")                                                                                # pick Last 14 days
        self.assertEqual(b.eval("GEN.days"), 14)
        self.assertEqual(b.eval("document.querySelector('#genDays .gv').textContent"), "Last 14 days")
        self.assertEqual(b.eval("document.activeElement.id"), "genDays")
        b.key("Tab")
        self.assertEqual(b.eval("document.activeElement.id"), "genFormKind")                         # the strip is one Tab stop per field
        b.key("Escape")                                                                               # no menu open: Esc closes the dialog, as before
        self.assertFalse(b.eval("document.getElementById('genDlg').open"))

    def test_dates_shows_two_boxes_only_when_chosen_and_a_bad_date_is_refused(self):
        b = self.b
        self.assertFalse(self.visible("#genCustom"))
        self.pick("#genDays", "Dates")
        self.assertTrue(self.visible("#genCustom"))
        self.assertEqual(b.eval("document.activeElement.id"), "genFrom")
        self.assertEqual(b.eval("[...document.querySelectorAll('#genCustom input')].map(x=>x.placeholder)"), ["DD-MM-YYYY", "DD-MM-YYYY"])
        self.hold_drafts()
        self.pick("#genFormKind", "Teams message")
        b.eval("document.getElementById('genFrom').value='31/02/2026'")
        b.click("#genGo")
        b.wait("document.querySelector('#snack.on')")
        self.assertIn("Not a date creaite knows", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(b.eval("window.__sent"), 0)                                                  # refused as before: nothing started
        self.assertTrue(b.eval("document.getElementById('genSum').hidden"))                          # and the setup did not fold
        self.pick("#genDays", "Last 30")
        self.assertFalse(self.visible("#genCustom"))

    def test_one_hint_line_follows_the_form_and_the_audience(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelectorAll('#genDlg #genHint').length"), 1)
        self.assertEqual(b.eval("document.getElementById('genFormNote')||document.getElementById('genAudNote')"), None)
        hint = lambda: b.eval("document.getElementById('genHint').textContent")                       # noqa: E731
        self.assertEqual(hint(), "Into the editor, for you to edit and save. Candid: the internal view of every item.")
        self.pick("#genAud", "Client-safe")
        self.assertEqual(hint(), "Into the editor, for you to edit and save. Only items marked client-visible, in their client wording. Nothing else from the vault is used.")
        self.pick("#genFormKind", "Email paragraph")
        self.assertTrue(hint().startswith("Shown here to copy; never saved. Only items marked client-visible"))

    def test_length_dims_for_the_forms_that_fix_it_with_the_reason_on_hover(self):
        b = self.b
        for label, reason in (("Three-line update", "Three lines, at most 60 words"), ("Email paragraph", "One paragraph, at most 120 words"),
                              ("Teams message", "At most 50 words")):
            self.pick("#genFormKind", label)
            self.assertEqual(b.eval("document.getElementById('genLen').getAttribute('aria-disabled')"), "true", label)
            self.assertEqual(b.eval("document.getElementById('genLen').title"), reason, label)
            self.assertLess(float(b.eval("getComputedStyle(document.getElementById('genLen')).opacity")), 1, label)
            b.eval("document.getElementById('genLen').click()")
            self.assertFalse(b.eval("!!document.querySelector('.pkpop')"), label)                    # it does not open
        for label in ("Steering note", "Current state"):
            self.pick("#genFormKind", label)
            self.assertIsNone(b.eval("document.getElementById('genLen').getAttribute('aria-disabled')"), label)
            self.assertEqual(b.eval("document.getElementById('genLen').title"), "", label)

    def test_every_handler_acts_by_id_or_data_attribute_and_survives_a_redraw(self):
        b = self.b
        b.eval("window.__fields=[...document.querySelectorAll('.genq')]")
        # the strip is reversed: nothing finds a field by its place
        b.eval("(()=>{ const s=document.querySelector('.genstrip'); [...s.children].reverse().forEach(c=>s.appendChild(c)); })()")
        self.pick("#genLen", "Fuller")
        self.assertEqual(b.eval("GEN.len"), "fuller")
        self.pick("#genAud", "Sponsor")
        self.assertEqual(b.eval("GEN.aud"), "sponsor")
        b.click("#genFormKind")
        b.wait("document.querySelector('.pkpop')")
        self.assertEqual(b.eval("document.querySelector('.pkpop [role=listbox]').getAttribute('aria-label')"), "Form")
        b.key("Escape")
        self.assertEqual(b.eval("window.__fields.length===4&&window.__fields.every(f=>document.getElementById(f.id)===f)"), True)   # a pick redraws the words, never the fields
        # the starters, by their own keys: change their words and add a leading button; the click still finds its sentence
        b.eval("document.querySelector('[data-gstart=decisions]').textContent='Something else'")
        b.eval("document.getElementById('genStart').prepend(Object.assign(document.createElement('button'),{type:'button',textContent:'x'}))")
        b.click("[data-gstart=decisions]")
        self.assertEqual(b.eval("document.getElementById('genNote').value"), "Lead with decisions needed.")
        # opened again: new buttons, same behaviour
        b.eval("openGen('ABC')")
        b.click("[data-gstart=plain]")
        self.assertEqual(b.eval("document.getElementById('genNote').value"), "Lead with decisions needed.\nPlain words, no jargon.")
        self.assertEqual(b.errors, [])

    # ── Steer it ──
    def test_steer_it_is_full_width_about_six_lines_and_resizable(self):
        b = self.b
        t, body = self.rect("#genNote"), self.rect(".gensteer")
        self.assertGreaterEqual(t["h"], 148)
        self.assertGreaterEqual(t["w"], body["w"] - 1)
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('genNote')).resize"), "vertical")
        self.assertEqual(b.eval("document.getElementById('genNote').rows"), 6)
        self.assertIn("Say what to lead with, what to leave out, or the tone.", b.eval("document.querySelector('.gensteer label').textContent"))

    def test_the_starters_append_a_sentence_and_never_fill_or_send(self):
        b = self.b
        self.hold_drafts()
        self.assertEqual(b.eval("[...document.querySelectorAll('#genStart [data-gstart]')].map(x=>[x.dataset.gstart,x.textContent])"), [list(x) for x in STARTERS.items()])
        b.click("[data-gstart=risks]")
        self.assertEqual(b.eval("document.getElementById('genNote').value"), "Lead with risks.")      # an empty box gets the sentence
        b.eval("document.getElementById('genNote').value='Mention the pilot results'")
        b.click("[data-gstart=decisions]")
        self.assertEqual(b.eval("document.getElementById('genNote').value"), "Mention the pilot results\nLead with decisions needed.")
        b.click("[data-gstart=plain]")
        self.assertEqual(b.eval("document.getElementById('genNote').value"),
                         "Mention the pilot results\nLead with decisions needed.\nPlain words, no jargon.")
        self.assertEqual(b.eval("document.activeElement.id"), "genNote")
        self.assertEqual(b.eval("window.__sent"), 0)                                                  # nothing was sent
        self.assertTrue(b.eval("document.getElementById('genSum').hidden"))
        self.assertTrue(b.eval("document.getElementById('genDlg').open"))

    # ── Draw on ──
    def test_draw_on_is_one_folded_line_that_opens_two_columns(self):
        b = self.b
        self.assertEqual(b.eval("document.getElementById('genSrcSum').textContent"), "Drawing on 5 sources")
        self.assertEqual(b.eval("document.getElementById('genSrcNames').textContent"),
                         "· tracker, minutes and transcripts, reports, weekly updates, swept mail and Teams")
        self.assertEqual(b.eval("document.getElementById('genSrcBtn').getAttribute('aria-expanded')"), "false")
        self.assertFalse(self.visible("#genSrc"))
        b.click("#genSrcBtn")
        self.assertTrue(self.visible("#genSrc"))
        self.assertEqual(b.eval("document.getElementById('genSrcBtn').getAttribute('aria-expanded')"), "true")
        self.assertEqual(len(b.eval("getComputedStyle(document.getElementById('genSrc')).gridTemplateColumns").split()), 2)
        self.assertEqual(b.eval("[...document.querySelectorAll('#genSrc input')].map(i=>[i.value,i.checked])"),
                         [["tracker", True], ["minutes", True], ["reports", True], ["updates", True], ["swept", True], ["documents", False]])   # documents off
        b.click("#genSrc input[value=documents]")
        self.assertEqual(b.eval("document.getElementById('genSrcSum').textContent"), "Drawing on 6 sources")
        b.click("#genSrcBtn")
        self.assertFalse(self.visible("#genSrc"))

    def test_client_safe_reads_client_visible_items_with_the_ticks_off_and_the_warm_note(self):
        b = self.b
        b.click("#genSrcBtn")
        b.click("#genSrc input[value=documents]")
        self.assertFalse(self.visible("#genOff"))
        self.pick("#genAud", "Client-safe")
        self.assertEqual(b.eval("document.getElementById('genSrcSum').textContent"), "Drawing on client-visible items")
        self.assertEqual(b.eval("document.getElementById('genSrcNames').textContent"), "")
        self.assertTrue(b.eval("[...document.querySelectorAll('#genSrc input')].every(i=>i.disabled)"))
        self.assertTrue(self.visible("#genOff"))
        self.assertEqual(b.eval("document.getElementById('genOff').textContent"),
                         "Client-safe uses only client-visible items, in their client wording. The sources are switched off.")
        self.pick("#genAud", "Internal")                                                              # back: the ticks are as they were left
        self.assertFalse(self.visible("#genOff"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#genSrc input')].some(i=>i.disabled)"), False)
        self.assertEqual(b.eval("document.querySelector('#genSrc input[value=documents]').checked"), True)
        self.assertEqual(b.eval("document.getElementById('genSrcSum').textContent"), "Drawing on 6 sources")

    def test_client_safe_sends_the_audience_and_no_internal_words(self):
        b = self.b
        self.pick("#genAud", "Client-safe")
        self.pick("#genFormKind", "Email paragraph")
        b.click("#genGo")
        b.wait("document.querySelector('#genOut .drcard, #genOut .drnone')", 30)
        prompt = Path(str(self.fake) + ".prompt").read_text(encoding="utf-8") if Path(str(self.fake) + ".prompt").exists() else ""
        self.assertNotIn("renegotiate", prompt)
        self.assertNotIn("Confidential", prompt)

    # ── the footer ──
    def test_the_footer_has_the_sweep_note_two_ordinary_buttons_and_the_key_hint(self):
        b = self.b
        self.assertIn("Mail and Teams", b.eval("document.getElementById('genSweep').textContent"))
        self.assertEqual(b.eval("[...document.querySelectorAll('.genfoot .btn')].map(x=>[x.id,x.querySelector('#genGoT')?x.querySelector('#genGoT').textContent:x.textContent,x.classList.contains('primary')])"),
                         [["genCancel", "Cancel", False], ["genGo", "Generate", True]])
        self.assertEqual(b.eval("document.getElementById('genKbd').textContent"), b.eval("MOD")+"↵")
        self.assertEqual(self.rect("#genGo")["h"], 32)
        self.pick("#genFormKind", "Teams message")
        self.assertEqual(b.eval("document.getElementById('genGoT').textContent"), "Write it")

    def test_cmd_enter_generates_here(self):
        b = self.b
        self.pick("#genFormKind", "Teams message")
        b.eval("document.getElementById('genNote').focus()")
        b.key("Enter", modifiers=4)
        b.wait("document.querySelector('#genOut .drcard')", 30)
        self.assertTrue(b.eval("!document.getElementById('genSum').hidden"))
        self.assertTrue(b.eval("document.getElementById('genDlg').open"))

    # ── the fold ──
    def test_while_writing_the_setup_folds_to_one_line_and_generate_again_waits(self):
        b = self.b
        self.hold_drafts()
        self.pick("#genFormKind", "Email paragraph")
        b.click("#genGo")
        b.wait("window.__sent===1")
        self.assertTrue(b.eval("document.getElementById('genSetup').hidden"))
        self.assertTrue(self.visible("#genSum"))
        self.assertEqual(b.eval("document.getElementById('genSumTxt').textContent"), "Email paragraph · last 7 days · Internal · 5 sources")
        self.assertEqual(b.eval("document.querySelector('#genSumTxt b').textContent"), "Email paragraph")
        self.assertEqual(b.eval("document.getElementById('genDlg').querySelector('h2').textContent"), "Write an email paragraph")
        self.assertEqual(b.eval("document.getElementById('genChange').textContent"), "Change settings")
        self.assertTrue(self.visible("#genOut .drstatus [data-drstop]"))                              # Stop, as today
        self.assertEqual(b.eval("document.getElementById('genCancel').textContent"), "Close")
        self.assertEqual(b.eval("document.getElementById('genGoT').textContent"), "Generate again")
        self.assertEqual(b.eval("document.getElementById('genGo').getAttribute('aria-disabled')"), "true")
        self.assertFalse(b.eval("document.getElementById('genGo').classList.contains('primary')"))
        b.eval("document.getElementById('genNote').focus()")
        b.key("Enter", modifiers=4)                                                                    # ⌘↵ while writing starts nothing more
        b.pump(0.2)
        self.assertEqual(b.eval("window.__sent"), 1)
        b.eval("window.__hold=false; window.__rel()")
        b.wait("document.querySelector('#genOut .drcard')", 30)
        self.assertIsNone(b.eval("document.getElementById('genGo').getAttribute('aria-disabled')"))   # Generate again is ready
        self.assertEqual(b.eval("[...document.querySelectorAll('#genDlg .btn.primary')].map(x=>x.textContent)"), ["Copy"])   # Copy is the one primary

    def test_change_settings_gives_the_setup_back_and_drops_the_draft(self):
        b = self.b
        self.pick("#genFormKind", "Teams message")
        self.pick("#genAud", "Sponsor")
        b.click("#genGo")
        b.wait("document.querySelector('#genOut .drcard')", 30)
        self.assertEqual(b.eval("document.getElementById('genSumTxt').textContent"), "Teams message · last 7 days · Sponsor · 5 sources")
        b.click("#genChange")
        self.assertTrue(self.visible("#genSetup"))
        self.assertFalse(self.visible("#genSum"))
        self.assertEqual(b.eval("document.getElementById('genOut').innerHTML"), "")
        self.assertEqual(b.eval("[document.getElementById('genCancel').textContent,document.getElementById('genGoT').textContent,document.getElementById('genGo').classList.contains('primary')]"),
                         ["Cancel", "Write it", True])
        self.assertEqual(b.eval("document.activeElement.id"), "genDays")
        self.assertEqual(b.eval("[GEN.form,GEN.aud]"), ["teams", "sponsor"])                          # the choices are kept
        for _ in range(50):
            if (self.stats().get("forms") or {}).get("rejected") == 1:
                break
            b.pump(0.1)
        self.assertEqual((self.stats().get("forms") or {}).get("rejected"), 1)                          # an unused draft counts as rejected, as Discard does

    def test_discard_and_closing_reset_the_fold(self):
        b = self.b
        self.pick("#genFormKind", "Teams message")
        b.click("#genGo")
        b.wait("document.querySelector('#genOut .drcard')", 30)
        b.click("#genOut [data-gfdo=discard]")
        self.assertTrue(self.visible("#genSetup"))
        self.assertFalse(self.visible("#genSum"))
        self.assertEqual(b.eval("document.getElementById('genOut').innerHTML"), "")
        b.click("#genGo")
        b.wait("document.querySelector('#genOut .drcard')", 30)
        b.click("#genCancel")                                                                         # Close (it says so after a draft)
        self.assertFalse(b.eval("document.getElementById('genDlg').open"))
        b.eval("openGen('ABC')")
        b.wait("document.getElementById('genDlg').open")
        self.assertTrue(self.visible("#genSetup"))
        self.assertFalse(self.visible("#genSum"))
        self.assertEqual(b.eval("document.getElementById('genOut').innerHTML"), "")
        self.assertEqual(b.eval("[document.getElementById('genCancel').textContent,document.getElementById('genGo').classList.contains('primary')]"), ["Cancel", True])
        self.assertFalse(self.visible("#genSrc"))                                                     # Draw on is folded again
        for _ in range(50):
            if (self.stats().get("forms") or {}).get("rejected") == 2:
                break
            b.pump(0.1)
        self.assertEqual((self.stats().get("forms") or {}).get("rejected"), 2)                          # discard, then close: each counted once

    def test_a_copied_draft_is_used_and_closing_it_is_not_counted_as_rejected(self):
        b = self.b
        self.pick("#genFormKind", "Teams message")
        b.click("#genGo")
        b.wait("document.querySelector('#genOut .drcard')", 30)
        b.eval("window.__clip=[]; navigator.clipboard.writeText=async t=>{ window.__clip.push(t); };")
        b.click("#genOut [data-gfdo=plain]")
        b.wait("window.__clip.length===1")
        b.click("#genCancel")
        for _ in range(50):
            if (self.stats().get("forms") or {}).get("used") == 1:
                break
            b.pump(0.1)
        self.assertEqual((self.stats().get("forms") or {}).get("used"), 1)
        self.assertFalse((self.stats().get("forms") or {}).get("rejected"))

    def test_a_failed_draft_gives_the_setup_back(self):
        b = self.b
        b.eval("""(()=>{ const f=window.fetch; window.fetch=(u,o)=>String(u).includes('/api/draft')?Promise.resolve(new Response(JSON.stringify({ok:false,message:'No draft today'}),
          {status:500,headers:{'Content-Type':'application/json'}})):f(u,o); })()""")
        self.pick("#genFormKind", "Teams message")
        b.click("#genGo")
        b.wait("document.querySelector('#snack.on')")
        self.assertTrue(self.visible("#genSetup"))
        self.assertFalse(self.visible("#genSum"))
        self.assertIsNone(b.eval("document.getElementById('genGo').getAttribute('aria-disabled')"))

    def test_current_state_still_closes_the_dialog_and_opens_the_editor(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.eval("openGen('ABC')")
        b.click("#genGo")
        b.wait("document.getElementById('curEd')", 30)
        self.assertFalse(b.eval("document.getElementById('genDlg').open"))
        self.assertTrue(b.eval("document.getElementById('genSum').hidden"))                           # the fold is for the forms shown here

    # ── light and dark ──
    def test_text_is_readable_in_light_and_dark(self):
        b = self.b
        b.eval("document.getElementById('genSrcBtn').click()")
        failures = []
        for theme in ("light", "dark"):
            b.eval(f"document.documentElement.dataset.theme={theme!r}")
            b.pump(0.1)
            for sel in (".genf label", "#genDays .gv", ".genhint", ".gensteer label", ".gensteer label .sub", ".genlink", "#genSrcSum", "#genSrcNames",
                        "#genSrc label", ".genfoot .sub", "#genGo", "#genCancel", "#genWho"):
                r = b.eval(f"{CONTRAST}({sel!r})")
                if r < 4.5:
                    failures.append((theme, sel, round(r, 2)))
            r = b.eval(f"{CONTRAST}('#genNote')")
            if r < 4.5:
                failures.append((theme, "#genNote", round(r, 2)))
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
