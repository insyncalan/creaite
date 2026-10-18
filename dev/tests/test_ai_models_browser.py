"""#132: Settings › Essentials › AI models in the real page, on the real live server with the fake provider.

Run: python3 dev/tests/test_ai_models_browser.py   (needs Google Chrome; skipped otherwise)

The live server runs with CREAITE_FAKE_PROVIDERS=1: fake keys only, no network, nothing in a keychain. Checks the provider
cards (greyed ones inert), the connect journey (a wrong key keeps the box open with the reason; a good key lists the models
to tick; Done connects), the four kinds of job (recommended defaults; tool jobs keep to tool-capable models), the weaker
popup (Esc keeps the recommended model; Use it anyway is saved and remembered), the limit, and Disconnect resetting what
used the provider. Then the layout at 900px, light and dark.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

GOOD = "fake-good-browser-TESTONLY"


class AiModelsPage(LiveBrowserCase):

    @classmethod
    def server_env(cls):
        return {"CREAITE_FAKE_PROVIDERS": "1"}

    def open(self):
        self.b.eval("STAB='essentials'; go('settings')")
        self.b.wait("!!document.querySelector('#aiModels .aicard')")

    def ai(self):
        return json.loads((self.v.root / "system/config/settings.json").read_text()).get("ai", {})

    def pick(self, job, model):
        self.b.eval(f"(()=>{{ const s=document.querySelector('[data-job={job}] select'); s.value={model!r};"
                    " s.dispatchEvent(new Event('change',{bubbles:true})); })()")

    def value(self, job):
        return self.b.eval(f"document.querySelector('[data-job={job}] select').value")

    def options(self, job):
        return self.b.eval(f"[...document.querySelectorAll('[data-job={job}] option')].map(o=>o.value)")

    def connect_openai(self):
        self.b.eval("document.querySelector('[data-prov=openai] .btn.primary').click()")
        self.b.wait("document.getElementById('aiConnect') && aiConnect.open && document.activeElement && document.activeElement.id==='aiKey'")
        self.b.eval(f"aiKey.value={GOOD!r}; aiTest.click()")
        self.b.wait("!!document.getElementById('aiDone')")
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#aiConnect .aiticks input')].map(i=>i.checked)"), [True, True])
        self.b.eval("aiDone.click()")
        self.b.wait("!aiConnect.open && document.querySelector('[data-prov=openai] .aiok')")

    def test_cards_lists_and_the_journey(self):
        self.open()
        b = self.b
        self.assertEqual(b.eval("[...document.querySelectorAll('#aiModels .aicard')].map(c=>c.dataset.prov)"),
                         ["claude", "openai", "local", "hosted_free", "deepseek"])
        self.assertNotIn("Gemini", b.eval("aiModels.textContent"))
        # greyed: "Available soon", aria-disabled, the button disabled (not focusable)
        for p in ("local", "hosted_free", "deepseek"):
            self.assertEqual(b.eval(f"document.querySelector('[data-prov={p}]').getAttribute('aria-disabled')"), "true")
            self.assertTrue(b.eval(f"document.querySelector('[data-prov={p}] button').disabled"))
            self.assertIn("Available soon", b.eval(f"document.querySelector('[data-prov={p}]').textContent"))
        self.assertEqual(b.eval("aiProvLine.textContent"),
                         "Claude is connected. Add OpenAI to use it for drafting and quick edits. Anything else is on its way.")
        # four kinds, the recommended default marked; only Claude's models
        self.assertEqual({j: self.value(j) for j in ("guard", "tools", "write", "quick")},
                         {"guard": "claude:opus", "tools": "claude:sonnet", "write": "claude:sonnet", "quick": "claude:haiku"})
        self.assertEqual(b.eval("document.querySelector('[data-job=guard] option:checked').textContent"), "Claude Opus 5.5 (recommended)")
        self.assertEqual(self.options("write"), ["claude:opus", "claude:sonnet", "claude:haiku"])
        self.assertTrue(b.eval("document.querySelector('[data-limit=other] input').disabled"))
        # a wrong key keeps the box open and says why; the field is cleared
        b.eval("document.querySelector('[data-prov=openai] .btn.primary').click()")
        b.wait("aiConnect.open")
        self.assertIn("leaves your laptop", b.eval("aiConnect.textContent"))
        b.eval("aiKey.value='sk-wrong-TESTONLY'; aiTest.click()")
        b.wait("!!document.querySelector('#aiConnect .aierr')")
        self.assertIn("OpenAI did not accept this key (401)", b.eval("document.querySelector('#aiConnect .aierr').textContent"))
        self.assertTrue(b.eval("aiConnect.open && aiKey.value==='' && aiKey.getAttribute('aria-invalid')==='true'"))
        b.eval("document.querySelector('#aiConnect .btn:not(.primary)').click()")
        b.wait("!aiConnect.open")
        # a good key: the models found, ticked; Done connects
        self.connect_openai()
        self.assertIn("openai:fake-small", self.options("quick"))
        self.assertNotIn("openai:fake-flagship", self.options("tools"))
        self.assertNotIn("openai:fake-flagship", self.options("guard"))
        self.assertEqual(self.value("write"), "claude:sonnet")                  # nothing changes yet
        self.assertNotIn(GOOD, json.dumps(self.ai()))
        # a weaker choice asks; Esc keeps the recommended model
        self.pick("guard", "claude:sonnet")
        b.wait("aiWeaker.open && document.activeElement.id==='aiKeep'")
        self.assertIn("could weaken a safeguard", b.eval("aiWeaker.textContent"))
        self.assertIn("The recommended model here is Claude Opus 5.5.", b.eval("aiWeaker.textContent"))
        b.key("Escape")
        b.wait("!aiWeaker.open")
        self.assertEqual(self.value("guard"), "claude:opus")
        self.assertEqual(self.ai().get("jobs", {}).get("guard", "claude:opus"), "claude:opus")   # unchanged: the default
        # Use it anyway: saved and remembered (no popup the second time)
        self.pick("write", "openai:fake-small")
        b.wait("aiWeaker.open")
        b.eval("aiAnyway.click()")
        b.wait("!aiWeaker.open && document.querySelector('[data-job=write] select').value==='openai:fake-small'")
        self.assertEqual(self.ai()["accepted_weaker"], ["write=openai:fake-small"])
        self.pick("write", "claude:sonnet")
        b.wait("document.querySelector('[data-job=write] select').value==='claude:sonnet'")
        self.pick("write", "openai:fake-small")
        b.wait("document.querySelector('[data-job=write] select').value==='openai:fake-small'")
        self.assertFalse(b.eval("aiWeaker.open"))
        # the limit: another connected model, now that there are two providers
        b.eval("document.querySelector('[data-limit=other] input').click()")
        b.wait("document.querySelector('[data-limit=other] input').checked")
        # Disconnect: the models leave, what used them goes back, the limit goes back to Ask me
        b.eval("document.querySelector('[data-prov=openai] .linkbtn').click()")
        b.wait("aiDisconnect.open")
        b.eval("aiDisconnectGo.click()")
        b.wait("!document.querySelector('[data-prov=openai] .aiok') && document.querySelector('[data-job=write] select').value==='claude:sonnet'")
        ai = self.ai()
        self.assertEqual((ai["jobs"]["write"], ai["on_limit"], ai["providers"]), ("claude:sonnet", "ask", {}))
        self.assertTrue(b.eval("document.querySelector('[data-limit=ask] input').checked"))
        self.assertEqual(b.eval("window.__errs||[]"), [])

    def test_sign_in_again_and_layout(self):
        self.open()
        b = self.b
        b.eval("document.querySelector('[data-prov=claude] .btn').click()")
        b.wait("aiSignIn.open")
        self.assertIn("/login", b.eval("aiSignIn.textContent"))
        b.key("Escape")
        b.wait("!aiSignIn.open")
        for theme in ("light", "dark"):
            b.eval(f"document.documentElement.dataset.theme={theme!r}")
            b.resize(900, 1000)
            b.wait("innerWidth<=900")
            self.assertTrue(b.eval("document.querySelector('#v-settings').scrollWidth<=document.querySelector('#v-settings').clientWidth+1"), theme)
            self.assertEqual(b.eval("getComputedStyle(document.querySelector('.aijob')).gridTemplateColumns.split(' ').length"), 1)
            ink, bg = b.eval("[getComputedStyle(document.querySelector('.ainm')).color, getComputedStyle(document.querySelector('.aicard')).backgroundColor]")
            self.assertNotEqual(ink, bg, theme)


if __name__ == "__main__":
    unittest.main()
