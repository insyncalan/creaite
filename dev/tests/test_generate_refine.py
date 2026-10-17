"""#110 part B: Steer it further (Refine and versions) under a form's result in the Generate dialog, and under the unsaved
Current state draft in the cockpit editor.

A box, four starters that only append, Refine (⌘↵). Each refine is a new version written on the run engine from the same facts, the
version shown and the change; "Version 2 of 2", Back and On move between versions; Discard, Change settings and closing drop them all;
nothing is saved or sent (the editor's Save is the only save). Draft stats count a refine as an edit of the same draft.

Two groups. The page's own behaviour is tested against a stand-in for /api/draft (the requests it sends are recorded and each answer
is made up here), so it does not depend on the server. The confidentiality tests run the real server with the stand-in Claude
(drafts_fake.py) and need drafts.py's refine support (`drafts.refine_note`); without it they are skipped, and the page tests still run.

Run: python3 dev/tests/test_generate_refine.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import drafts_fake  # noqa: E402
from test_drafts_forms import secret_world  # noqa: E402
from test_drafts_update import DraftCase  # noqa: E402
from test_tracker import ABC, action  # noqa: E402

SCRIPTS = Path(__file__).resolve().parents[2] / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import drafts  # noqa: E402

SOURCES = [{"id": "F1", "ref": "S1", "text": "Tracker: UAT data is late"}, {"id": "F2", "ref": "S2", "text": "Weekly report: escalated to the CIO"}]
V1 = "Quick update: UAT is at risk because data access is late."
V2 = "UAT is at risk; the CIO escalation is the decision this week."
V3 = "Decision needed: the CIO escalation."


def draft(text, form="teams", audience="internal", loose=0, notes=None):
    """A made-up /api/draft result: the text as one sentence per line with its source, `loose` of them with none."""
    lines = [x for x in text.split("\n") if x.strip()]
    sentences = [{"text": ln, "refs": [] if i >= len(lines) - loose else ["S1"], "unsourced": i >= len(lines) - loose} for i, ln in enumerate(lines)]
    return {"text": text, "sentences": sentences, "sources": SOURCES, "unsourced": loose, "words": len(text.split()), "lines": len(lines),
            "length_notes": notes or [], "form": form, "audience": audience}


STUB = """(()=>{ window.__bodies=[]; window.__replies=[]; window.__hold=false; window.__f=window.fetch;
  window.fetch=(u,o)=>{ if(!/[/]api[/]draft$/.test(String(u))||!o||!o.body) return window.__f(u,o);
    const body=JSON.parse(o.body), refine=!!body.text, first=!refine&&window.__first;
    if(!refine&&!first) return window.__f(u,o);
    window.__bodies.push(body); const r=first&&!refine?window.__first:window.__replies.shift();
    const go=()=>{ if(r&&r.__fail) return new Response(JSON.stringify({ok:false,message:r.__fail}),{status:500,headers:{'Content-Type':'application/json'}});
      const ev=t=>'data: '+JSON.stringify(t)+'\\n\\n';
      return new Response(new Blob([ev({type:'step'}),ev({type:'draft',...r}),ev({type:'done',run:body.run})]).stream(),{status:200,headers:{'Content-Type':'text/event-stream'}}); };
    return window.__hold?new Promise(res=>{ window.__rel=()=>res(go()); }):Promise.resolve(go()); }; })()"""


class RefineDialog(DraftCase):
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
        self.b.eval(STUB)

    # helpers
    def pick(self, trigger, label):
        b = self.b
        b.click(trigger)
        b.wait("document.querySelector('.pkpop [role=option]')")
        b.eval(f"[...document.querySelectorAll('.pkpop [role=option]')].find(o=>o.textContent.trim().startsWith({label!r})).click()")

    def memory(self):
        return (self.v.root / ABC / "CLAUDE.md").read_text()

    def first(self, d, form="Teams message"):
        """Write the first draft (made up) in the dialog."""
        b = self.b
        b.eval(f"window.__first={json.dumps(d)}")
        self.pick("#genFormKind", form)
        b.click("#genGo")
        b.wait("document.querySelector('#genOut .drcard')", 30)

    def reply(self, *drafts_):
        self.b.eval(f"window.__replies.push(...{json.dumps(list(drafts_))})")

    def refine(self, text):
        b = self.b
        b.eval(f"(()=>{{ const t=document.getElementById('genRefineNote'); t.value={text!r}; t.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        n = b.eval("window.__bodies.length")
        b.click("#genRefineGo")
        b.wait(f"window.__bodies.length>{n}")

    def visible(self, sel):
        return self.b.eval(f"(()=>{{ const e=document.querySelector({sel!r}); return !!e&&e.getClientRects().length>0&&getComputedStyle(e).visibility!=='hidden'; }})()")

    def shown(self):
        return self.b.eval("document.querySelector('#genOut .drtext').innerText.replace(/\\s*S\\d+/g,'').trim()")

    def vers(self):
        return self.b.eval("(document.querySelector('#genOut .vers')||{textContent:''}).textContent")

    def rect(self, sel):
        return self.b.eval(f"(()=>{{ const r=document.querySelector({sel!r}).getBoundingClientRect(); return {{t:r.top,b:r.bottom,w:r.width,h:r.height}}; }})()")

    def stats(self):
        return (super().stats().get("forms")) or {}

    def stat(self, name, want, tries=50):
        """The forms count `name`, once it is `want` (the page posts it after the event)."""
        for _ in range(tries):
            if (self.stats().get(name) or 0) == want:
                break
            self.b.pump(0.1)
        return self.stats().get(name) or 0

    # ── where it is, and what it is ──
    def test_steer_it_further_appears_under_every_forms_result_and_not_before(self):
        b = self.b
        self.assertTrue(b.eval("document.getElementById('genRefineHost').hidden"))
        self.assertEqual(b.eval("!!document.getElementById('genRefine')"), False)
        for form in ("Steering note", "Three-line update", "Email paragraph", "Teams message"):
            self.first(draft(V1, form=form), form)
            self.assertTrue(b.eval("!document.getElementById('genRefineHost').hidden"), form)
            self.assertTrue(b.eval("document.querySelector('#genOut').compareDocumentPosition(document.getElementById('genRefine'))&Node.DOCUMENT_POSITION_FOLLOWING"), form)   # under the card
            self.assertEqual(b.eval("document.querySelector('#genRefine label').firstChild.textContent.trim()"), "Steer it further", form)
            self.assertIn("Each change makes a new version. Nothing is saved or sent.", b.eval("document.querySelector('#genRefine label').textContent"))
            self.assertEqual(b.eval("[...document.querySelectorAll('#genRefine [data-rstart]')].map(x=>[x.dataset.rstart,x.textContent])"),
                             [["shorter", "Shorter"], ["plainer", "Plainer words"], ["decision", "Lead with the decision"], ["risks", "Add the risks"]], form)
            t = self.rect("#genRefineNote")
            self.assertGreaterEqual(t["h"], 60, form)
            self.assertEqual(b.eval("getComputedStyle(document.getElementById('genRefineNote')).resize"), "vertical")
            self.assertEqual(b.eval("document.getElementById('genRefineGo').textContent"), "Refine" + b.eval("MOD") + "↵")
            self.assertEqual(b.eval("document.getElementById('genRefineGo').classList.contains('primary')"), False)         # Copy stays the one primary
            b.click("#genChange")                                                                                              # back to the setup for the next form
        self.assertEqual(b.errors, [])

    def test_the_starters_append_a_sentence_and_never_fill_or_send(self):
        b = self.b
        self.first(draft(V1))
        n = b.eval("window.__bodies.length")
        b.click("[data-rstart=shorter]")
        self.assertEqual(b.eval("document.getElementById('genRefineNote').value"), "Make it shorter.")
        b.eval("document.getElementById('genRefineNote').value='Mention the CIO'")
        b.click("[data-rstart=risks]")
        b.click("[data-rstart=plainer]")
        self.assertEqual(b.eval("document.getElementById('genRefineNote').value"), "Mention the CIO Add the risks. Use plainer words.")
        self.assertEqual(b.eval("document.activeElement.id"), "genRefineNote")
        self.assertEqual(b.eval("window.__bodies.length"), n)                                                                # nothing sent
        self.assertEqual(self.vers(), "")                                                                                    # no new version
        # by the starter's own key, not its words
        b.eval("document.querySelector('[data-rstart=decision]').textContent='Other words'")
        b.eval("document.getElementById('genRefineNote').value=''")
        b.click("[data-rstart=decision]")
        self.assertEqual(b.eval("document.getElementById('genRefineNote').value"), "Lead with the decision.")

    def test_refine_with_nothing_typed_asks_for_the_change_and_sends_nothing(self):
        b = self.b
        self.first(draft(V1))
        n = b.eval("window.__bodies.length")
        b.click("#genRefineGo")
        b.wait("document.querySelector('#snack.on')")
        self.assertIn("Say what to change", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(b.eval("window.__bodies.length"), n)

    # ── a new version ──
    def test_refine_writes_version_2_from_the_same_facts_the_previous_version_and_the_change(self):
        b = self.b
        memory = self.memory()
        self.pick("#genAud", "Sponsor")
        self.pick("#genDays", "Last 14")
        b.eval("document.getElementById('genNote').value='Focus on the pilot'")
        self.first(draft(V1, audience="sponsor"))
        self.assertEqual(self.vers(), "")                                                       # the first draft's card is as it was
        self.reply(draft(V2, audience="sponsor"))
        b.eval("window.__hold=true")
        self.refine("Shorter, and lead with the decision.")
        self.assertEqual(b.eval("document.querySelector('#genRefineWork .drstatus').textContent.replace(/Stop$/,'').trim()"), "Refining version 1 into version 2…")
        self.assertTrue(b.eval("!!document.querySelector('#genRefineWork [data-drstop]')"))                                  # Stop, as Generate has
        self.assertEqual(b.eval("document.getElementById('genRefineGo').getAttribute('aria-disabled')"), "true")
        self.assertEqual(b.eval("document.getElementById('genGo').getAttribute('aria-disabled')"), "true")
        b.key("Enter", modifiers=4)                                                                                           # ⌘↵ while it writes sends nothing more
        b.pump(0.2)
        self.assertEqual(b.eval("window.__bodies.length"), 2)
        b.eval("window.__hold=false; window.__rel()")
        b.wait("/Version 2 of 2/.test(document.querySelector('#genOut .vers').textContent)", 20)
        req = b.eval("window.__bodies[1]")
        self.assertEqual({k: v for k, v in req.items() if k != "run"},
                         {"kind": "status-form", "code": "ABC", "from": req["from"], "to": req["to"], "audience": "sponsor", "length": "standard", "form": "teams",
                          "text": V1, "note": "Shorter, and lead with the decision. (The first steer was: Focus on the pilot)"})
        self.assertEqual(req["from"], b.eval("window.__bodies[0].from"))                                                       # the same period as the first draft
        self.assertEqual(self.shown(), V2)
        self.assertEqual(self.vers(), "Version 2 of 2 · Back to version 1")
        self.assertEqual(b.eval("document.getElementById('genRefineNote').value"), "")                                        # ready for the next change
        self.assertEqual(b.eval("document.activeElement.id"), "genRefineNote")                                                # focus stays in the box
        self.assertEqual(self.memory(), memory)                                                                                # nothing saved
        self.assertEqual(b.eval("window.__bodies.length"), 2)
        self.assertEqual(self.stat("edited", 1), 1)                                                                           # counts only: an edit of the same draft
        self.assertEqual(b.errors, [])

    def test_versions_back_and_on_and_a_refine_from_an_earlier_one(self):
        b = self.b
        self.first(draft(V1))
        self.reply(draft(V2), draft(V3))
        self.refine("Shorter")
        b.wait("document.querySelector('#genOut .vers')")
        self.assertEqual(self.vers(), "Version 2 of 2 · Back to version 1")
        b.click("[data-gver=back]")
        self.assertEqual(self.shown(), V1)
        self.assertEqual(self.vers(), "Version 1 of 2 · On to version 2")
        self.refine("Lead with the decision")                                                                                   # from version 1
        self.assertEqual(b.eval("window.__bodies[2].text"), V1)
        b.wait("/Version 3 of 3/.test(document.querySelector('#genOut .vers').textContent)", 20)
        self.assertEqual(self.shown(), V3)
        self.assertEqual(self.vers(), "Version 3 of 3 · Back to version 2")
        b.click("[data-gver=back]")
        self.assertEqual(self.shown(), V2)
        self.assertEqual(self.vers(), "Version 2 of 3 · Back to version 1 · On to version 3")
        b.click("[data-gver=next]")
        self.assertEqual(self.shown(), V3)
        self.assertEqual(self.stat("edited", 1), 1)                                                                           # one draft, edited once

    def test_every_version_has_its_own_sources_marks_and_length_note(self):
        b = self.b
        self.first(draft(V1))
        self.reply(draft("UAT is at risk.\nThe sponsor wants a weekly checkpoint.", loose=1, notes=["2 lines: this form takes 3."]))
        self.refine("Add the risks")
        b.wait("document.querySelector('#genOut .vers')")
        self.assertEqual(b.eval("document.querySelectorAll('#genOut .drtag').length"), 1)                                      # the no-source mark
        self.assertIn("1 sentence has no source", b.eval("document.querySelector('#genOut .drnote').textContent"))
        self.assertIn("this form takes 3", b.eval("document.querySelector('#genOut div.drnote[role=note]').textContent"))
        self.assertEqual(b.eval("document.querySelectorAll('#genOut sup.drref').length"), 1)
        b.click("[data-gver=back]")
        self.assertEqual(b.eval("document.querySelectorAll('#genOut .drtag').length"), 0)                                      # version 1 has none
        self.assertEqual(b.eval("document.querySelector('#genOut .drnote').textContent.trim()"), f"{len(V1.split())} words.")

    def test_copy_copies_the_version_shown_and_a_refine_before_it_is_not_a_rejection(self):
        b = self.b
        self.first(draft(V1))
        self.reply(draft(V2))
        self.refine("Shorter")
        b.wait("document.querySelector('#genOut .vers')")
        b.eval("window.__clip=[]; navigator.clipboard.writeText=async t=>{ window.__clip.push(t); };")
        b.click("#genOut [data-gfdo=plain]")
        b.wait("window.__clip.length===1")
        self.assertEqual(b.eval("window.__clip[0]"), V2)
        b.click("#genCancel")
        self.assertEqual((self.stat("used", 1), self.stat("edited", 1), self.stats().get("rejected") or 0), (1, 1, 0))

    def test_cmd_enter_in_the_box_refines_and_does_not_generate_again(self):
        b = self.b
        self.first(draft(V1))
        self.reply(draft(V2))
        b.eval("(()=>{ const t=document.getElementById('genRefineNote'); t.value='Shorter'; t.focus(); })()")
        b.key("Enter", modifiers=4)
        b.wait("/Version 2 of 2/.test((document.querySelector('#genOut .vers')||{}).textContent||'')", 20)
        self.assertEqual(b.eval("window.__bodies.map(x=>!!x.text)"), [False, True])                                           # the second is the refine, not a new draft

    def test_a_failed_refine_keeps_the_versions_and_the_box(self):
        b = self.b
        self.first(draft(V1))
        self.reply({"__fail": "No draft today"})
        self.refine("Shorter")
        b.wait("document.querySelector('#snack.on')")
        self.assertIn("No draft today", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(self.shown(), V1)
        self.assertEqual(self.vers(), "")
        self.assertEqual(b.eval("document.getElementById('genRefineNote').value"), "Shorter")                                 # what was typed is kept
        self.assertIsNone(b.eval("document.getElementById('genRefineGo').getAttribute('aria-disabled')"))
        self.assertIsNone(b.eval("document.getElementById('genGo').getAttribute('aria-disabled')"))
        self.assertEqual(self.stats().get("edited") or 0, 0)

    def test_a_draft_too_long_to_refine_is_refused_before_anything_is_sent(self):
        b = self.b
        self.first(draft("Word " * 400, form="steering"), "Steering note")
        n = b.eval("window.__bodies.length")
        b.eval("(()=>{ const t=document.getElementById('genRefineNote'); t.value='Shorter'; })()")
        b.click("#genRefineGo")
        b.wait("document.querySelector('#snack.on')")
        self.assertIn("more than a refine can take", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(b.eval("window.__bodies.length"), n)

    def test_length_fixed_forms_keep_their_limits_in_the_request(self):
        b = self.b
        self.pick("#genLen", "Fuller")
        self.first(draft(V1, form="three"), "Three-line update")
        self.reply(draft(V2, form="three"))
        self.refine("Plainer words")
        b.wait("document.querySelector('#genOut .vers')")
        req = b.eval("window.__bodies[1]")
        self.assertEqual((req["form"], req["length"]), ("three", "fuller"))                                                   # the server holds the form to its 3 lines and 60 words
        self.assertEqual(b.eval("document.getElementById('genLen').getAttribute('aria-disabled')"), "true")

    # ── dropping them ──
    def test_discard_change_settings_and_closing_drop_every_version(self):
        b = self.b
        for how in ("discard", "change", "close"):
            self.first(draft(V1))
            self.reply(draft(V2))
            self.refine("Shorter")
            b.wait("document.querySelector('#genOut .vers')")
            if how == "discard":
                b.click("#genOut [data-gfdo=discard]")
            elif how == "change":
                b.click("#genChange")
            else:
                b.click("#genCancel")
                b.eval("openGen('ABC')")
                b.wait("document.getElementById('genDlg').open")
            self.assertEqual(b.eval("document.getElementById('genOut').innerHTML"), "", how)
            self.assertEqual(b.eval("document.getElementById('genRefineHost').innerHTML"), "", how)
            self.assertTrue(b.eval("document.getElementById('genRefineHost').hidden"), how)
            b.eval(f"window.__first={json.dumps(draft(V1))}")
            b.click("#genGo")
            b.wait("document.querySelector('#genOut .drcard')", 30)
            self.assertEqual(self.vers(), "", how)                                                                              # a new draft starts again at version 1
            b.click("#genChange")
        self.assertEqual(b.errors, [])

    def test_refine_is_in_view_at_900_wide_and_800_tall(self):
        b = self.b
        b.resize(900, 800)
        b.pump(0.2)
        self.first(draft(V1))
        self.reply(draft(V2))
        self.refine("Shorter")
        b.wait("document.querySelector('#genOut .vers')")
        self.assertEqual(self.rect("#genDlg")["w"], 736)
        self.assertLessEqual(self.rect("#genDlg")["b"], 800)
        self.assertLessEqual(self.rect("#genGo")["b"], 800)                                                                    # the footer stays
        b.eval("document.getElementById('genRefineGo').scrollIntoView({block:'nearest'})")
        r = self.rect("#genRefineGo")
        self.assertTrue(0 <= r["t"] and r["b"] <= 800)
        over = b.eval("[...document.querySelectorAll('#genDlg .genbody, #genDlg .genref, #genDlg .genrow, #genDlg .drhead')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.className)")
        self.assertEqual(over, [])

    def test_cmd_enter_from_the_result_card_after_a_refine_does_not_regenerate_or_drop_versions(self):
        b = self.b
        self.first(draft(V1))
        self.reply(draft(V2))
        self.refine("Shorter")
        b.wait("document.querySelector('#genOut .vers')")
        n = b.eval("window.__bodies.length")
        b.eval("document.querySelector('#genOut .drcard').focus()")
        b.key("Enter", modifiers=4)
        b.wait("document.querySelector('#snack.on')")
        self.assertIn("Press Generate again to start over", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(b.eval("window.__bodies.length"), n)                                                                   # nothing sent
        self.assertEqual(self.vers(), "Version 2 of 2 · Back to version 1")                                                      # nothing dropped

    def test_generate_again_takes_the_refine_box_away_while_the_new_draft_is_written(self):
        b = self.b
        self.first(draft(V1))
        b.eval("document.getElementById('genRefineNote').value='half typed'")
        b.eval("window.__hold=true")
        b.click("#genGo")                                                                                                       # Generate again
        b.wait("window.__bodies.length===2")
        self.assertTrue(b.eval("document.getElementById('genRefineHost').hidden"))
        self.assertEqual(b.eval("document.getElementById('genRefineHost').innerHTML"), "")
        b.eval("window.__hold=false; window.__rel()")
        b.wait("document.querySelector('#genOut .drcard')", 30)
        self.assertEqual(b.eval("document.getElementById('genRefineNote').value"), "")                                          # a fresh box for the new draft
        self.assertEqual(self.vers(), "")

    def test_a_change_over_300_characters_is_refused_with_a_message_and_300_is_sent(self):
        b = self.b
        self.first(draft(V1))
        n = b.eval("window.__bodies.length")
        b.eval(f"document.getElementById('genRefineNote').value={'x' * 301!r}")
        b.click("#genRefineGo")
        b.wait("document.querySelector('#snack.on')")
        self.assertEqual(b.eval("document.getElementById('snackT').textContent.replace(/Undo$/,'').trim()"), "A change can be 300 characters at most; yours is 301. Shorten it.")
        self.assertEqual(b.eval("window.__bodies.length"), n)
        self.assertEqual(len(b.eval("document.getElementById('genRefineNote').value")), 301)                                      # what was typed is kept
        self.reply(draft(V2))
        b.eval(f"document.getElementById('genRefineNote').value={'x' * 300!r}")
        b.click("#genRefineGo")
        b.wait(f"window.__bodies.length>{n}")
        self.assertEqual(b.eval("window.__bodies[%d].note" % n), "x" * 300)                                                      # exactly 300 goes through whole

    def test_exactly_1500_characters_is_refined_and_1501_is_refused_with_the_reason(self):
        b = self.b
        self.first(draft("x" * 1500, form="email"), "Email paragraph")
        self.reply(draft("y" * 1501, form="email"))
        self.refine("Shorter")
        b.wait("document.querySelector('#genOut .vers')")
        self.assertEqual(len(b.eval("window.__bodies[1].text")), 1500)                                                           # the limit itself is allowed
        n = b.eval("window.__bodies.length")
        self.refine_text("Plainer words")
        b.wait("document.querySelector('#snack.on')")
        self.assertIn("This draft is over 1500 characters, more than a refine can take. Shorten it first.", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(b.eval("window.__bodies.length"), n)

    def test_a_fuller_steering_note_over_the_limit_is_refused_honestly(self):
        b = self.b
        self.pick("#genLen", "Fuller")
        self.first(draft(("A fuller steering note sentence. " * 50).strip(), form="steering"), "Steering note")        # about 1,650 characters
        n = b.eval("window.__bodies.length")
        b.eval("document.getElementById('genRefineNote').value='Shorter'")
        b.click("#genRefineGo")
        b.wait("document.querySelector('#snack.on')")
        self.assertIn("more than a refine can take", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(b.eval("window.__bodies.length"), n)
        self.assertEqual(self.vers(), "")

    def refine_text(self, text):
        self.b.eval(f"(()=>{{ const t=document.getElementById('genRefineNote'); t.value={text!r}; }})()")
        self.b.click("#genRefineGo")

    def test_a_refine_that_lands_after_change_settings_never_shows(self):
        b = self.b
        self.first(draft(V1))
        self.reply(draft(V2))
        b.eval("window.__hold=true")
        self.refine("Shorter")
        b.click("#genChange")                                                                                                   # Change settings, mid-refine: the draft and its versions go
        b.eval("window.__hold=false; window.__rel()")
        b.pump(0.6)
        self.assertEqual(b.eval("document.getElementById('genOut').innerHTML"), "")                                              # the late version is not drawn
        self.assertTrue(self.visible("#genSetup"))
        self.assertEqual(b.eval("document.getElementById('genRefineHost').innerHTML"), "")
        self.assertEqual(self.stats().get("edited") or 0, 0)                                                                    # and it was not an edit of anything

    def test_a_reply_with_nothing_left_says_how_many_sentences_were_left_out(self):
        b = self.b
        self.first(draft(V1, audience="client"))
        self.reply({"text": "", "sentences": [], "sources": SOURCES, "unsourced": 0, "words": 0, "lines": 0, "form": "teams", "audience": "client",
                    "length_notes": ["2 sentences have no source, so they were left out of this version."]})
        self.refine("Add the internal risks")
        b.wait("document.querySelector('#snack.on')")
        self.assertEqual(b.eval("document.getElementById('snackT').textContent.replace(/Undo$/,'').trim()"),
                         "2 sentences have no source, so they were left out of this version. No new version was made.")
        self.assertEqual(self.shown(), V1)
        self.assertEqual(self.vers(), "")

    def test_a_client_safe_draft_is_not_offered_a_refine_and_says_why(self):
        b = self.b
        self.pick("#genAud", "Client-safe")
        self.first(draft(V1, audience="client"))
        self.assertTrue(b.eval("!document.getElementById('genRefineHost').hidden"))
        self.assertEqual(b.eval("document.querySelector('#genRefineHost .drnote').textContent"), "Steer it further is not available for a Client-safe draft yet.")
        self.assertEqual(b.eval("!!document.getElementById('genRefineNote')||!!document.getElementById('genRefineGo')"), False)     # no box, no button
        self.assertEqual(b.eval("document.querySelectorAll('#genDlg [data-rstart]').length"), 0)
        self.assertEqual(b.errors, [])

    def test_text_is_readable_in_light_and_dark(self):
        b = self.b
        self.first(draft(V1))
        self.reply(draft(V2))
        self.refine("Shorter")
        b.wait("document.querySelector('#genOut .vers')")
        contrast = """(()=>{ const rgb=c=>{ const m=c.match(/[\\d.]+/g).map(Number); return m.length>3&&m[3]===0?null:m.slice(0,3); };
          const lum=c=>{ const f=v=>{ v/=255; return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4); }; return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2]); };
          const bg=el=>{ for(let e=el;e;e=e.parentElement){ const c=rgb(getComputedStyle(e).backgroundColor); if(c) return c; } return [255,255,255]; };
          return sel=>{ const el=document.querySelector(sel), a=lum(rgb(getComputedStyle(el).color)), c=lum(bg(el)); return (Math.max(a,c)+.05)/(Math.min(a,c)+.05); }; })()"""
        bad = []
        for theme in ("light", "dark"):
            b.eval(f"document.documentElement.dataset.theme={theme!r}")
            b.pump(0.1)
            for sel in ("#genRefine label", "#genRefine label .sub", "#genRefine .genrow .sub", "[data-rstart=shorter]", "#genRefineNote", "#genRefineGo", "#genOut .vers", "[data-gver=back]"):
                r = b.eval(f"({contrast})({sel!r})")
                if r < 4.5:
                    bad.append((theme, sel, round(r, 2)))
        self.assertEqual(bad, [])


class RefineEditor(DraftCase):
    """The unsaved Current state draft in the cockpit editor."""
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
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit .curcard [data-gen]')")
        b.eval(STUB)

    def memory(self):
        return (self.v.root / ABC / "CLAUDE.md").read_text()

    def generate(self, text="Falcon is off track. Data access is late. UAT starts in November."):
        b = self.b
        marked = text.replace(".", ". {F1}", 1).replace("late.", "late. {F2}").replace("November.", "November. {F1}")        # the fact marks a drafted Current state carries
        b.eval(f"genDraft('ABC',{json.dumps(marked)},'',{{audience:'internal',length:'standard',from:'2026-10-02',to:'2026-10-09',note:''}})")
        b.wait("document.getElementById('curEd')&&document.getElementById('curRefine')", 30)

    def editor(self):
        return self.b.eval("document.getElementById('curEd').innerText.trim()")

    def reply(self, *drafts_):
        self.b.eval(f"window.__replies.push(...{json.dumps(list(drafts_))})")

    def refine(self, text):
        b = self.b
        b.eval(f"(()=>{{ const t=document.getElementById('curRefineNote'); t.value={text!r}; t.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        n = b.eval("window.__bodies.length")
        b.click("#curRefineGo")
        b.wait(f"window.__bodies.length>{n}")

    def vers(self):
        return self.b.eval("document.getElementById('curVers').textContent")

    def editor_says(self, text):
        """The editor's words (spaces and paragraphs as one), once it shows them: it is drawn a moment after a version is loaded."""
        self.b.wait(f"document.getElementById('curEd')&&document.getElementById('curEd').innerText.split(/\\s+/).join(' ').trim()==={json.dumps(text)}", 20)
        return text

    def stats(self):
        return (super().stats().get("forms")) or {}

    def stat(self, name, want, tries=50):
        for _ in range(tries):
            if (self.stats().get(name) or 0) == want:
                break
            self.b.pump(0.1)
        return self.stats().get(name) or 0

    def test_it_appears_under_a_drafted_current_state_and_not_under_a_hand_edit(self):
        b = self.b
        b.click("#v-cockpit .curcard [data-edcur]")                                                                          # a plain edit is not a draft
        b.wait("document.getElementById('curEd')")
        self.assertEqual(b.eval("!!document.getElementById('curRefine')"), False)
        b.click('[data-cure="cancel"]')
        self.generate()
        self.assertEqual(b.eval("document.querySelector('#curRefine label').firstChild.textContent.trim()"), "Steer it further")
        self.assertIn("Nothing is saved until you press Save.", b.eval("document.querySelector('#curRefine label').textContent"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#curRefine [data-rstart]')].map(x=>x.dataset.rstart)"), ["shorter", "plainer", "decision", "risks"])
        self.assertGreaterEqual(b.eval("document.getElementById('curRefineNote').getBoundingClientRect().height"), 60)
        self.assertEqual(b.eval("document.getElementById('curVers').textContent"), "")                                      # version 1: no bar yet
        self.assertEqual(b.eval("document.querySelector('.curacts [data-cure=save]').classList.contains('primary')"), True)    # Save stays the editor's primary

    def test_a_client_safe_current_state_draft_is_not_offered_a_refine_and_says_why(self):
        b = self.b
        b.eval("genDraft('ABC','Falcon is on track. {F1}','',{audience:'client',length:'standard',from:'2026-10-02',to:'2026-10-09',note:''})")
        b.wait("document.getElementById('curEd')&&document.getElementById('curRefine')", 30)
        self.assertEqual(b.eval("document.querySelector('#curRefine .drnote').textContent"), "Steer it further is not available for a Client-safe draft yet.")
        self.assertEqual(b.eval("!!document.getElementById('curRefineNote')||!!document.getElementById('curRefineGo')"), False)
        self.assertEqual(b.errors, [])

    def test_the_starters_append_only(self):
        b = self.b
        self.generate()
        n = b.eval("window.__bodies.length")
        before = self.editor()
        b.click("#curRefine [data-rstart=decision]")
        b.click("#curRefine [data-rstart=risks]")
        self.assertEqual(b.eval("document.getElementById('curRefineNote').value"), "Lead with the decision. Add the risks.")
        self.assertEqual((b.eval("window.__bodies.length"), self.editor()), (n, before))

    def test_refine_makes_version_2_in_the_editor_with_marks_and_nothing_is_saved(self):
        b = self.b
        memory = self.memory()
        self.generate()
        self.reply(draft("Falcon is off track.\n\nThe CIO escalation is the decision this week.", form="current", loose=1))
        b.eval("window.__hold=true")
        self.refine("Shorter, and lead with the decision.")
        self.assertEqual(b.eval("document.querySelector('#curRefineWork .drstatus').textContent.replace(/Stop$/,'').trim()"), "Refining version 1 into version 2…")
        b.eval("window.__hold=false; window.__rel()")
        b.wait("/Version 2 of 2/.test(document.getElementById('curVers').textContent)", 20)
        req = b.eval("window.__bodies[0]")
        self.assertEqual((req["kind"], req["form"], req["code"], req["audience"], req["length"]), ("status-form", "current", "ABC", "internal", "standard"))
        self.assertEqual(req["text"], "Falcon is off track. Data access is late. UAT starts in November.")                   # the version shown, no marks
        self.assertEqual(req["note"], "Shorter, and lead with the decision.")
        self.assertEqual(self.editor_says("Falcon is off track. The CIO escalation is the decision this week."), "Falcon is off track. The CIO escalation is the decision this week.")
        self.assertEqual(self.vers(), "Version 2 of 2 · Back to version 1")
        self.assertTrue(b.eval("!!document.getElementById('curEd')"))                                                          # still unsaved, still editing
        self.assertEqual(b.eval("CURED.dirty"), True)
        self.assertEqual(self.memory(), memory)                                                                                # Save is the only save
        self.assertEqual(b.eval("document.getElementById('curRefineNote').value"), "")
        self.assertEqual(self.stat("edited", 1), 1)
        # the sources and the no-source marks are worked out again for the new version: the sourced sentence carries its fact, the other has none
        b.wait("CURED.claims&&Object.keys(CURED.claims).length>0", 20)
        marks = b.eval("[...document.querySelectorAll('#curEd .claim')].map(x=>x.dataset.c)")
        self.assertTrue(marks)
        self.assertEqual(b.eval("Object.values(CURED.claims).map(c=>c.ids.length>0)"), [True, False])
        self.assertEqual(b.errors, [])

    def test_back_restores_the_first_draft_with_its_fact_marks(self):
        b = self.b
        self.generate()
        b.eval("(()=>{ const e=document.getElementById('curEd'); e.focus(); })()")
        self.reply(draft("Falcon is off track.", form="current"))
        self.refine("Shorter")
        b.wait("/Version 2 of 2/.test(document.getElementById('curVers').textContent)", 20)
        b.click("[data-cver=back]")
        self.assertEqual(self.editor_says("Falcon is off track. Data access is late. UAT starts in November."), "Falcon is off track. Data access is late. UAT starts in November.")
        self.assertEqual(self.vers(), "Version 1 of 2 · On to version 2")
        self.assertEqual(b.eval("Object.values(CURED.claims).filter(c=>c.ids.length).length"), 3)                             # the first draft's marks are back
        b.click("[data-cver=next]")
        self.assertEqual(self.editor_says("Falcon is off track."), "Falcon is off track.")
        self.assertEqual(b.eval("CURED.vers.length"), 2)

    def type_at_end(self, text):
        """A hand edit in the editor, as typing at the end of the text is."""
        self.b.eval(f"CURED.ed1.editor.chain().focus('end').insertContent({text!r}).run()")
        self.b.pump(1.0)                                                                                                       # the editor re-reads its sentences a moment after a change

    def states(self):
        return self.b.eval("Object.values(CURED.claims).map(c=>claimState(c))")

    def test_back_after_a_hand_edit_keeps_the_edit_and_the_sources_of_the_untouched_sentences(self):
        b = self.b
        self.generate()
        self.type_at_end(" Plus one new sentence of my own.")                                                                 # a hand edit before the refine
        self.reply(draft("Falcon is off track.", form="current"))
        self.refine("Shorter")
        b.wait("/Version 2 of 2/.test(document.getElementById('curVers').textContent)", 20)
        b.click("[data-cver=back]")
        self.editor_says("Falcon is off track. Data access is late. UAT starts in November. Plus one new sentence of my own.")
        self.assertEqual(self.states(), ["ok", "ok", "ok", "none"])                                                            # the untouched sentences keep their sources
        b.eval("document.querySelector('[data-cure=save]').click()")                                                           # Save waits on the one new sentence only
        b.wait("/One sentence has no source/.test(document.getElementById('snackT').textContent)")
        self.assertTrue(b.eval("!!document.getElementById('curEd')"))

    def test_a_hand_edit_typed_while_a_refine_is_written_stays_in_its_version(self):
        b = self.b
        self.generate()
        self.reply(draft("Falcon is off track.", form="current"))
        b.eval("window.__hold=true")
        self.refine("Shorter")
        self.type_at_end(" MY LATE EDIT.")                                                                                    # typed while it is written
        b.eval("window.__hold=false; window.__rel()")
        b.wait("/Version 2 of 2/.test(document.getElementById('curVers').textContent)", 20)
        self.editor_says("Falcon is off track.")
        b.click("[data-cver=back]")
        self.editor_says("Falcon is off track. Data access is late. UAT starts in November. MY LATE EDIT.")                   # not lost

    def test_a_redraw_of_the_editor_during_a_refine_keeps_the_progress_stop_and_busy_button(self):
        b = self.b
        self.generate()
        self.reply(draft("Falcon is off track.", form="current"))
        b.eval("window.__hold=true")
        self.refine("Shorter")
        self.assertTrue(b.eval("!!document.querySelector('#curRefineWork [data-drstop]')"))
        b.eval("mountCurEdit()")                                                                                              # the editor is drawn again mid-write
        self.assertEqual(b.eval("document.querySelector('#curRefineWork .drstatus').textContent.replace(/Stop$/,'').trim()"), "Refining version 1 into version 2…")
        self.assertTrue(b.eval("!!document.querySelector('#curRefineWork [data-drstop]')"))
        self.assertEqual(b.eval("document.getElementById('curRefineGo').getAttribute('aria-disabled')"), "true")
        b.eval("window.__hold=false; window.__rel()")
        b.wait("/Version 2 of 2/.test(document.getElementById('curVers').textContent)", 20)
        self.assertEqual(b.eval("document.getElementById('curRefineWork').innerHTML"), "")
        self.assertIsNone(b.eval("document.getElementById('curRefineGo').getAttribute('aria-disabled')"))

    def test_what_the_server_left_out_is_shown_with_its_version_in_the_editor(self):
        b = self.b
        self.generate()
        self.reply(draft("Falcon is off track.", form="current", notes=["1 sentence has no source, so it was left out of this version."]))
        self.refine("Shorter")
        b.wait("/Version 2 of 2/.test(document.getElementById('curVers').textContent)", 20)
        self.assertEqual(b.eval("document.querySelector('#curRefineMsg .drnote').textContent"), "1 sentence has no source, so it was left out of this version.")
        b.click("[data-cver=back]")
        self.editor_says("Falcon is off track. Data access is late. UAT starts in November.")
        b.wait("document.getElementById('curRefineMsg').innerHTML===''", 20)
        self.assertEqual(b.eval("document.getElementById('curRefineMsg').innerHTML"), "")                                       # version 1 has no such note
        b.click("[data-cver=next]")
        b.wait("/left out of this version/.test(document.getElementById('curRefineMsg').textContent)", 20)                       # drawn a moment after the click
        self.assertIn("left out of this version", b.eval("document.getElementById('curRefineMsg').textContent"))

    def test_an_all_unsourced_reply_says_how_many_were_left_out_and_changes_nothing(self):
        b = self.b
        self.generate()
        before = self.editor()
        self.reply({"text": "", "sentences": [], "sources": SOURCES, "unsourced": 0, "words": 0, "lines": 0, "form": "current", "audience": "internal",
                    "length_notes": ["3 sentences have no source, so they were left out of this version."]})
        self.refine("Add the internal risks")
        b.wait("document.querySelector('#snack.on')")
        self.assertIn("3 sentences have no source, so they were left out of this version. No new version was made.", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual((self.editor(), self.vers()), (before, ""))

    def test_the_typed_change_survives_the_editor_being_drawn_again(self):
        b = self.b
        self.generate()
        b.eval("(()=>{ const t=document.getElementById('curRefineNote'); t.value='Plainer words please'; t.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.eval("mountCurEdit()")
        self.assertEqual(b.eval("document.getElementById('curRefineNote').value"), "Plainer words please")
        b.click("#curRefine [data-rstart=shorter]")                                                                           # and the starters still work after it
        self.assertEqual(b.eval("document.getElementById('curRefineNote').value"), "Plainer words please Make it shorter.")

    def test_cmd_enter_in_the_box_refines_it_does_not_save(self):
        b = self.b
        memory = self.memory()
        self.generate()
        self.reply(draft("Falcon is off track.", form="current"))
        b.eval("(()=>{ const t=document.getElementById('curRefineNote'); t.value='Shorter'; t.dispatchEvent(new Event('input',{bubbles:true})); t.focus(); })()")
        b.key("Enter", modifiers=4)
        b.wait("/Version 2 of 2/.test(document.getElementById('curVers').textContent)", 20)
        self.assertTrue(b.eval("!!document.getElementById('curEd')"))
        self.assertEqual(self.memory(), memory)

    def test_cancel_drops_every_version_and_a_new_draft_starts_again(self):
        b = self.b
        self.generate()
        self.reply(draft("Falcon is off track.", form="current"))
        self.refine("Shorter")
        b.wait("/Version 2 of 2/.test(document.getElementById('curVers').textContent)", 20)
        b.click('[data-cure="cancel"]')
        b.eval("document.querySelector('#discardBar [data-dis=go]').click()")
        b.wait("!document.getElementById('curEd')")
        self.assertEqual(b.eval("CURED"), None)
        self.generate()
        self.assertEqual(self.vers(), "")
        self.assertEqual(b.eval("CURED.vers.length"), 1)

    def test_a_failed_refine_leaves_the_editor_as_it_was(self):
        b = self.b
        self.generate()
        before = self.editor()
        self.reply({"__fail": "No draft today"})
        self.refine("Shorter")
        b.wait("document.querySelector('#snack.on')")
        self.assertEqual((self.editor(), self.vers()), (before, ""))
        self.assertEqual(b.eval("document.getElementById('curRefineNote').value"), "Shorter")


# ── the server rules, in plain code (no browser) ──
class RefineRules(unittest.TestCase):
    """drafts.py's refine: the sentences kept by position, the character cap, the Client-safe refusal, the first draft unchanged."""
    SRC = [{"ref": "S1", "id": "F1", "text": "x"}]

    def build(self, **req):
        import sqlite3
        from unittest import mock
        import status_facts
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE projects (code TEXT)")
        con.execute("INSERT INTO projects VALUES ('ABC')")
        sheet = {"name": "Example", "start": "2026-10-01", "end": "2026-10-08", "parts": [{"title": "Position", "lines": [{"fid": "F1", "text": "UAT is late."}]}]}
        try:
            with mock.patch.object(status_facts, "facts", return_value=sheet) as facts, mock.patch.object(status_facts, "settings", return_value={"length_words": {}}):
                got = drafts.build_status_form(con, {"code": "ABC", "form": "email", "audience": "internal", **req})
        finally:
            con.close()
        return got, facts

    def test_an_unsourced_sentence_is_removed_at_its_own_place_not_the_first_equal_text(self):
        reply = "We are escalating it this week. [S1]\nescalating it this week.\nLast one. [S1]"
        kept, gone = drafts.refine_keep_sourced(reply, self.SRC)
        self.assertEqual((kept, gone), ("We are escalating it this week. [S1]\nLast one. [S1]", 1))

    def test_the_first_the_middle_and_the_last_unsourced_sentence_each_go_with_one_break(self):
        for reply, want in (("Bad.\nA. [S1]\nB. [S1]", "A. [S1]\nB. [S1]"), ("A. [S1]\nBad.\nB. [S1]", "A. [S1]\nB. [S1]"),
                            ("A. [S1]\nB. [S1]\nBad.", "A. [S1]\nB. [S1]"), ("A. [S1] Bad one. B. [S1]", "A. [S1] B. [S1]")):
            self.assertEqual(drafts.refine_keep_sourced(reply, self.SRC), (want, 1), reply)

    def test_a_repeated_unsourced_sentence_is_counted_and_removed_each_time(self):
        kept, gone = drafts.refine_keep_sourced("Bad.\nA. [S1]\nBad.", self.SRC)
        self.assertEqual((kept, gone), ("A. [S1]", 2))

    def test_the_parsed_text_and_sentences_agree_after_the_filter(self):
        ctx = {"sources": self.SRC, "extra": {"form": "email", "audience": "steering", "words": 120, "lines": 1, "refine": True}}
        got = drafts.parse_status_form("We are escalating it this week. [S1]\nescalating it this week.", ctx)
        self.assertEqual(got["text"], "We are escalating it this week.")
        self.assertEqual([x["text"] for x in got["sentences"]], ["We are escalating it this week."])
        self.assertEqual(got["length_notes"], ["1 sentence has no source, so it was left out of this version."])

    def test_a_previous_version_of_exactly_1500_characters_is_taken_and_1501_is_refused_not_cut(self):
        got, _ = self.build(text="x" * 1500, note="Shorter")
        self.assertIn("x" * 1500, got.values["note"])
        with self.assertRaises(drafts.Refused) as why:
            self.build(text="x" * 1501, note="Shorter")
        self.assertIn("1500", str(why.exception))

    def test_the_previous_version_is_stripped_before_it_is_counted_and_used(self):
        got, _ = self.build(text="  \n" + "x" * 1500 + " \n ", note="Shorter")                                                  # padding does not count towards the 1500
        self.assertIn("--- PREVIOUS VERSION ---\n" + "x" * 1500 + "\n--- END OF THE PREVIOUS VERSION ---", got.values["note"])
        self.assertTrue(got.extra["refine"])
        blank, _ = self.build(text=" \n  ", note="Lead with risks")                                                           # only white space is no previous version
        self.assertFalse(blank.extra["refine"])
        self.assertEqual(blank.values["note"], "Alan's steer: Lead with risks\n")

    def test_the_refine_prompt_says_a_change_can_never_add_a_fact(self):
        got, _ = self.build(text="UAT is late.", note="Add the internal risks.")
        self.assertIn("a change can never add a fact that is not in them", got.values["note"])
        self.assertIn("THIS IS A REFINEMENT", got.values["note"])

    def test_an_unknown_source_reference_is_not_a_source(self):
        kept, gone = drafts.refine_keep_sourced("Made up. [S9]\nTrue. [S1]\nBoth. [S1, S9]", self.SRC)
        self.assertEqual((kept, gone), ("True. [S1]\nBoth. [S1, S9]", 1))                                                      # one good reference is enough; none is not

    def test_the_filter_cuts_where_sentences_cuts(self):
        """The filter splits a reply by its own copy of the pattern: it must agree with `sentences` (digits, decimals, dates, abbreviations)."""
        import random
        bits = ["UAT is late", "Q3 2026. Next steps agreed", "The fee is 3.5 percent", "2026-10-09 is the date", "Dr. Smith agreed", "e.g. Falcon",
                "v2.1 is out", "It is 10.30. 12 people came", "\"Quoted.\" Then more", "Done (really.) (Next)", "- a bullet", "!", "Why? 3 reasons",
                "ok. 4. five", "Wait... Then", "Cost [S1] first. 2 more"]
        rng, bad = random.Random(7), []
        for _ in range(200):
            parts = []
            for _ in range(rng.randint(1, 6)):
                parts.append(rng.choice(bits) + rng.choice(["", ".", ". [S1]", " [S1]", "?", "! [S1]"]))
                parts.append(rng.choice([" ", " ", "\n", "\n\n", "  "]))
            reply = "".join(parts).strip()
            for src in ([], self.SRC):
                want = sum(1 for m in drafts.marked(reply, src) if m["unsourced"])
                kept, gone = drafts.refine_keep_sourced(reply, src)
                if gone != want or [m["text"] for m in drafts.marked(kept, src)] != [m["text"] for m in drafts.marked(reply, src) if not m["unsourced"]]:
                    bad.append((reply, src, gone, want))
        self.assertEqual(bad[:3], [])

    def test_a_client_safe_refine_is_refused_before_any_facts_are_built(self):
        from unittest import mock
        with mock.patch.object(drafts, "REFINE_NOT_CLIENT", "STOP"), self.assertRaises(drafts.Refused) as why:
            self.build(audience="client", text="UAT is late.", note="Shorter")
        self.assertEqual(str(why.exception), "STOP")
        got, facts = self.build(audience="client")                                                                              # a first Client-safe draft is as before
        facts.assert_called_once()
        self.assertNotIn("REFINEMENT", got.values["note"])

    def test_a_first_draft_prompt_is_unchanged_and_a_refine_names_the_previous_version(self):
        first, _ = self.build(note="Lead with risks")
        self.assertEqual(first.values["note"], "Alan's steer: Lead with risks\n")
        self.assertFalse(first.extra["refine"])
        refined, _ = self.build(text="UAT is late.", note="Shorter")
        self.assertIn("--- PREVIOUS VERSION ---\nUAT is late.", refined.values["note"])
        self.assertTrue(refined.extra["refine"])

    def test_current_is_a_form_for_a_refine(self):
        got, _ = self.build(form="current", text="Falcon is off track.", note="Shorter")
        self.assertEqual(got.values["form_name"], "Current state")


# ── confidentiality: the real server and the stand-in Claude ──
NEEDS_SERVER = unittest.skipUnless(hasattr(drafts, "refine_note"), "drafts.py has no refine support yet (#110 B needs it)")


def client_world(v):
    secret_world(v)
    msg = "What it is: A delay in testing\nWhat it means for you: Testing starts later\nWhat is being done: We are escalating it"
    v.propose("client", [action(31, description="Agree the UAT dates with the client", client_visible=1, client_message=msg, due_date="2026-10-20")])
    v.run("apply")


@NEEDS_SERVER
class RefineConfidentiality(DraftCase):
    """A refine draws on exactly the same sources and audience as the first draft: an instruction can't bring in what the facts don't hold.
    The Client-safe audience is not offered a refine yet (follow-up C2), so the server refuses it before any sheet is built."""
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        client_world(v)
        cls.fake = drafts_fake.install(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake), "CREAITE_NOW": "2026-10-09 13:00"}

    def prompt(self):
        return Path(str(self.fake) + ".prompt").read_text(encoding="utf-8")

    def ask(self, **body):
        got, events = self.draft({"kind": "status-form", "code": "ABC", **body})
        self.assertIsNone(got)
        return next(e for e in events if e["type"] == "draft")

    def refused(self, **body):
        """The reason a /api/draft request was refused: the run never starts, so no model is asked."""
        before = Path(str(self.fake) + ".prompt").read_text(encoding="utf-8") if Path(str(self.fake) + ".prompt").exists() else ""
        got, events = self.draft({"kind": "status-form", "code": "ABC", **body})
        self.assertFalse([e for e in events if e["type"] == "draft"])
        after = Path(str(self.fake) + ".prompt").read_text(encoding="utf-8") if Path(str(self.fake) + ".prompt").exists() else ""
        self.assertEqual(before, after)
        return json.dumps(got) + json.dumps(events)

    def test_a_client_safe_refine_is_refused_with_a_plain_message_and_no_model_is_asked(self):
        first = self.ask(form="email", audience="client")                                                                       # a first draft is as before
        self.assertTrue(first["text"])
        why = self.refused(form="email", audience="client", text=first["text"], note="Add the internal risks.")
        self.assertIn(drafts.REFINE_NOT_CLIENT, why)
        self.assertNotIn("THIS IS A REFINEMENT", self.prompt())
        self.assertNotIn("Health now", why)                                                                                     # and nothing of the sheet

    def test_a_steering_committee_refine_holds_the_same_rule(self):
        first = self.ask(form="three", audience="steering")
        refined = self.ask(form="three", audience="steering", text=first["text"], note="Add the internal risks.")
        self.assertNotIn("supplier", refined["text"])
        self.assertNotIn("renegotiate", self.prompt())
        self.assertTrue(any("left out of this version" in n for n in refined["length_notes"]))

    def test_an_internal_refine_keeps_an_unsourced_sentence_marked_not_removed(self):
        first = self.ask(form="email", audience="internal")
        refined = self.ask(form="email", audience="internal", text=first["text"], note="Add the internal risks.")
        self.assertIn("supplier", refined["text"])
        self.assertTrue(any(s["unsourced"] for s in refined["sentences"]))                                                      # shown with its no-source mark
        self.assertFalse(any("left out" in n for n in refined["length_notes"]))                                                 # nothing is removed for Internal

    def test_a_fixed_length_form_is_checked_again_on_the_new_version(self):
        refined = self.ask(form="three", audience="internal", text=V1, note="Add two more lines of detail.")
        self.assertEqual(refined["lines"], 1)
        self.assertEqual(refined["length_notes"], [])
        too_long = drafts.result({}, {"kind": "status-form", "sources": [{"ref": "S1", "id": "F1", "text": "x"}],
                                      "extra": {"form": "three", "audience": "internal", "words": 60, "lines": 3, "refine": True}},
                                 "One. [S1]\nTwo. [S1]\nThree. [S1]\nFour. [S1]")
        self.assertEqual(too_long["length_notes"], ["4 lines: this form takes 3."])

    def test_a_first_draft_is_unchanged_without_text(self):
        got = self.ask(form="teams", audience="internal", note="Focus on UAT")
        self.assertIn("Alan's steer: Focus on UAT", self.prompt())
        self.assertNotIn("REFINEMENT", self.prompt())
        self.assertEqual(got["form"], "teams")

    def test_the_current_state_form_is_a_form_for_a_refine(self):
        got = self.ask(form="current", audience="internal", text="Falcon is off track.", note="Shorter")
        self.assertEqual(got["form"], "current")
        self.assertIn("FORM: current (Current state)", self.prompt())


if __name__ == "__main__":
    unittest.main()
