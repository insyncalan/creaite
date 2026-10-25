"""BL-231: the pinned esbuild (dev/tools/esbuild.py) refuses a tarball whose hash differs and leaves nothing behind;
a tarball with the pinned hash is unpacked to the cache, executable; an unsupported platform is refused.

Run: python3 dev/tests/test_esbuild_pin.py   (quick tier: starts no Chrome, no network)

The download is faked: `fetch` returns a tarball built here, and the pinned hash is pointed at it for the good case.
The cache is a temporary folder, never dev/.cache/.
"""
import hashlib
import io
import os
import shutil
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import esbuild  # noqa: E402

BODY = b"#!/bin/sh\necho fake esbuild\n"


def tarball(body=BODY, name=esbuild.MEMBER):
    """A gzipped tarball holding `body` at `name`, as the npm registry would serve it."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name)
        info.size = len(body)
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(body))
    return buf.getvalue()


class EsbuildPinTest(unittest.TestCase):
    """The hash check, the unpacking and the platform check, with a faked download."""

    def setUp(self):
        """A private cache folder for each test, and this machine's key pinned to a known platform."""
        self.cache = Path(tempfile.mkdtemp(prefix="creaite-esbuild-"))
        self.addCleanup(shutil.rmtree, self.cache, True)
        for p in (mock.patch.object(esbuild, "CACHE", self.cache),
                  mock.patch.object(esbuild, "platform_key", return_value="linux-x64")):
            p.start()
            self.addCleanup(p.stop)

    def files(self):
        """Every file under the private cache."""
        return [p for p in self.cache.rglob("*") if p.is_file()]

    def test_changed_tarball_is_refused_and_nothing_is_left(self):
        """A tampered tarball (not the pinned hash) raises and writes nothing, not even a partial file."""
        with mock.patch.object(esbuild, "fetch", return_value=tarball(BODY + b"# tampered\n")):
            with self.assertRaisesRegex(esbuild.EsbuildError, "not the pinned"):
                esbuild.binary()
        self.assertEqual(self.files(), [])

    def test_good_tarball_is_unpacked_executable(self):
        """A tarball with the pinned hash gives package/bin/esbuild in the cache, executable, and only that."""
        data = tarball()
        pins = dict(esbuild.SHA256, **{"linux-x64": hashlib.sha256(data).hexdigest()})
        with mock.patch.object(esbuild, "fetch", return_value=data) as fetch, mock.patch.object(esbuild, "SHA256", pins):
            path = esbuild.binary()
            self.assertEqual(esbuild.binary(), path)
        self.assertEqual(fetch.call_count, 1, "a cached binary is not downloaded again")
        self.assertEqual(path, self.cache / esbuild.PINNED / "linux-x64" / "esbuild")
        self.assertEqual(path.read_bytes(), BODY)
        self.assertTrue(os.access(path, os.X_OK))
        self.assertEqual(self.files(), [path])

    def test_tarball_without_binary_is_refused(self):
        """A tarball with the pinned hash but no package/bin/esbuild is refused and leaves nothing."""
        data = tarball(name="package/README.md")
        pins = dict(esbuild.SHA256, **{"linux-x64": hashlib.sha256(data).hexdigest()})
        with mock.patch.object(esbuild, "fetch", return_value=data), mock.patch.object(esbuild, "SHA256", pins):
            with self.assertRaisesRegex(esbuild.EsbuildError, "has no"):
                esbuild.binary()
        self.assertEqual(self.files(), [])


class PlatformTest(unittest.TestCase):
    """Only the three pinned platforms are accepted."""

    def test_platforms(self):
        """macOS arm64, Linux x86-64 and Linux arm64 map to their packages; Windows, Intel Macs and other chips are refused clearly."""
        self.assertEqual(esbuild.platform_key("darwin", "arm64"), "darwin-arm64")
        self.assertEqual(esbuild.platform_key("linux", "x86_64"), "linux-x64")
        self.assertEqual(esbuild.platform_key("linux", "aarch64"), "linux-arm64")      # the cloud boxes (CAX, 25-10-2026)
        self.assertEqual(esbuild.platform_key("linux", "arm64"), "linux-arm64")
        for system, machine in (("win32", "AMD64"), ("darwin", "x86_64"), ("linux", "riscv64"), ("linux", "ppc64le")):
            with self.assertRaisesRegex(esbuild.EsbuildError, "pinned only for"):
                esbuild.platform_key(system, machine)

    def test_pins_are_sha256(self):
        """All three pins are 64 lowercase hex characters and the URL names the pinned version."""
        for key, value in esbuild.SHA256.items():
            self.assertRegex(value, r"^[0-9a-f]{64}$")
            self.assertTrue(esbuild.tarball_url(key).endswith(f"/{key}-{esbuild.PINNED}.tgz"))


if __name__ == "__main__":
    unittest.main()
