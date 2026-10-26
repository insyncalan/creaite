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
    def test_a_read_that_fails_is_a_503_with_a_plain_message(self):
        for exc in (OSError("busy"), ValueError("half a file")):
            with self.subTest(type(exc).__name__), mock.patch.object(settings_catalogue, "catalogue", side_effect=exc), \
                    mock.patch.object(live_server, "debuglog"):
                h = FakeHandler()
                live_server.settings_catalogue_route(h, {})
            code, body, extra = h.sent
            self.assertEqual(code, 503)
            self.assertFalse(body["ok"])
            self.assertEqual(body["message"], "Settings are being saved. Try again in a moment.")
            self.assertEqual(extra, {"Retry-After": "1"})

    def test_a_good_read_is_unchanged(self):
        h = FakeHandler()
        live_server.settings_catalogue_route(h, {})
        self.assertEqual(h.sent[0], 200)
        self.assertTrue(h.sent[1]["ok"])

    def test_another_error_is_still_a_500_by_the_dispatcher(self):
        with mock.patch.object(settings_catalogue, "catalogue", side_effect=KeyError("x")):
            with self.assertRaises(KeyError):
                live_server.settings_catalogue_route(FakeHandler(), {})


if __name__ == "__main__":
    unittest.main()
