"""#370 slice 3 (D3): a page that left mid-request is one info line from the server's own handle_error, never a traceback.
Skips unless the guarded patch is applied. Run: python3 dev/tests/test_handle_error_370.py"""
import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import live_server  # noqa: E402

APPLIED = hasattr(live_server, "RUN_LIMITS_370")


def raise_in_handler(server, exc):
    try:
        raise exc
    except Exception:
        server.handle_error(None, ("127.0.0.1", 1))


@unittest.skipUnless(APPLIED, "the #370 slice 3 patch is not applied")
class HandleError(unittest.TestCase):
    def setUp(self):
        self.server = object.__new__(live_server.LocalServer)

    def test_client_left_is_info_and_prints_nothing(self):
        for exc in (BrokenPipeError(), ConnectionResetError()):
            with self.subTest(type(exc).__name__), redirect_stderr(io.StringIO()) as err, \
                    mock.patch.object(live_server, "debuglog") as log:
                raise_in_handler(self.server, exc)
            self.assertEqual(err.getvalue(), "")
            log.info.assert_called_once()
            self.assertIn("client left", log.info.call_args[0][1])
            log.error.assert_not_called()

    def test_another_error_keeps_the_standard_traceback(self):
        with redirect_stderr(io.StringIO()) as err, mock.patch.object(live_server, "debuglog"):
            raise_in_handler(self.server, ValueError("boom"))
        self.assertIn("Traceback", err.getvalue())


if __name__ == "__main__":
    unittest.main()
