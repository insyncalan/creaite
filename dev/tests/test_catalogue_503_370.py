"""#370 slice 3 (D1): the catalogue route answers 503 with a plain JSON message when settings.json (or its log) can't be read at
that moment, instead of a 500. Skips unless the guarded patch is applied. Run: python3 dev/tests/test_catalogue_503_370.py"""
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import live_server  # noqa: E402
import settings_catalogue  # noqa: E402

APPLIED = hasattr(live_server, "RUN_LIMITS_370")


class FakeHandler:
    def __init__(self):
        self.sent = None

    def send(self, code, body, *a, **k):
        self.sent = (code, body, k.get("extra"))


@unittest.skipUnless(APPLIED, "the #370 slice 3 patch is not applied")
class Catalogue503(unittest.TestCase):
    def setUp(self):
        live_server.CATALOGUE_FAILS.clear()

    def call(self, exc):
        with mock.patch.object(settings_catalogue, "catalogue", side_effect=exc), \
                mock.patch.object(live_server, "debuglog") as log:
            h = FakeHandler()
            live_server.settings_catalogue_route(h, {})
        return h.sent, log

    def test_one_oserror_is_a_503_and_a_warn(self):
        (code, body, extra), log = self.call(OSError("busy"))
        self.assertEqual((code, extra), (503, {"Retry-After": "1"}))
        self.assertEqual(body["message"], "Settings are being saved. Try again in a moment.")
        log.warn.assert_called_once()
        self.assertIn("OSError", log.warn.call_args[0][1])
        log.error.assert_not_called()

    def test_a_valueerror_is_a_500_and_an_error(self):
        (code, body, _), log = self.call(ValueError("half a file"))
        self.assertEqual(code, 500)
        self.assertEqual(body["message"], "Settings can't be read. See Settings > Health.")
        log.error.assert_called_once()
        self.assertNotIn("half a file", log.error.call_args[0][1])

    def test_three_oserrors_in_a_minute_escalate(self):
        codes = [self.call(OSError("busy"))[0][0] for _ in range(3)]
        self.assertEqual(codes, [503, 503, 500])
        _, log = self.call(OSError("busy"))
        log.error.assert_called_once()

    def test_failures_older_than_a_minute_do_not_count(self):
        live_server.CATALOGUE_FAILS[:] = [live_server.time.monotonic() - 120] * 5
        self.assertEqual(self.call(OSError("busy"))[0][0], 503)

    def test_success_resets_the_count(self):
        self.call(OSError("busy"))
        self.call(OSError("busy"))
        h = FakeHandler()
        live_server.settings_catalogue_route(h, {})
        self.assertEqual(h.sent[0], 200)
        self.assertEqual(live_server.CATALOGUE_FAILS, [])
        self.assertEqual(self.call(OSError("busy"))[0][0], 503)

    def test_another_error_is_still_raised_to_the_dispatcher(self):
        with mock.patch.object(settings_catalogue, "catalogue", side_effect=KeyError("x")):
            with self.assertRaises(KeyError):
                live_server.settings_catalogue_route(FakeHandler(), {})


if __name__ == "__main__":
    unittest.main()
