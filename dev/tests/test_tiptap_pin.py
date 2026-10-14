"""BL-301 part A: the pinned Tiptap packages (dev/tools/tiptap.py) refuse a tarball whose hash differs and leave nothing
behind; a tarball with the pinned hash is unpacked to the cache with its stamp; an unsafe tarball is refused.

Run: python3 dev/tests/test_tiptap_pin.py   (quick tier: no network, no browser)

The download is faked: `fetch` returns a tarball built here. The cache is a temporary folder, never dev/.cache/.
"""
import hashlib
import io
import re
import shutil
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import tiptap  # noqa: E402

FILES = {"package/package.json": b'{"name": "fake"}\n', "package/dist/index.js": b"export const x = 1;\n"}


def tarball(files=FILES, link=None):
    """A gzipped tarball holding `files` ({member name: bytes}), as the npm registry would serve it; `link` adds a
    symbolic link member of that name."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, body in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))
        if link:
            info = tarfile.TarInfo(link)
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            tar.addfile(info)
    return buf.getvalue()


def pin(data, name="@tiptap/fake"):
    """A one-package pin list for `data`."""
    return ((name, "9.9.9", hashlib.sha256(data).hexdigest()),)


class TiptapPinTest(unittest.TestCase):
    """The hash check, the unpacking and the refusals, with a faked download."""

    def setUp(self):
        """A private cache folder for each test."""
        self.cache = Path(tempfile.mkdtemp(prefix="creaite-tiptap-"))
        self.addCleanup(shutil.rmtree, self.cache, True)
        p = mock.patch.object(tiptap, "CACHE", self.cache)
        p.start()
        self.addCleanup(p.stop)

    def files(self):
        """Every file under the private cache."""
        return [p for p in self.cache.rglob("*") if p.is_file()]

    def test_changed_tarball_is_refused_and_nothing_is_left(self):
        """A tampered tarball (not the pinned hash) raises and writes nothing."""
        pins = pin(tarball())
        tampered = tarball(dict(FILES, **{"package/dist/index.js": b"steal();\n"}))
        with self.assertRaisesRegex(tiptap.TiptapError, "not the pinned"):
            tiptap.ensure(pins, fetch=lambda url: tampered)
        self.assertEqual(self.files(), [])

    def test_good_tarball_is_unpacked_with_its_stamp(self):
        """A tarball with the pinned hash is unpacked under node_modules/<name>/ without npm's package/ prefix, with
        the stamp; a second ensure downloads nothing."""
        data = tarball()
        pins = pin(data)
        fetch = mock.Mock(return_value=data)
        root = tiptap.ensure(pins, fetch=fetch)
        self.assertEqual(tiptap.ensure(pins, fetch=fetch), root)
        self.assertEqual(fetch.call_count, 1, "an unpacked package is not downloaded again")
        fetch.assert_called_with("https://registry.npmjs.org/@tiptap/fake/-/fake-9.9.9.tgz")
        pkg = root / "@tiptap" / "fake"
        self.assertEqual((pkg / "dist" / "index.js").read_bytes(), FILES["package/dist/index.js"])
        self.assertEqual((pkg / tiptap.STAMP).read_text(), pins[0][2])
        self.assertEqual(sorted(p.relative_to(pkg).as_posix() for p in self.files()),
                         [tiptap.STAMP, "dist/index.js", "package.json"])

    def test_half_unpacked_package_is_fetched_again(self):
        """A package folder without its stamp (an unpack that was cut short) is replaced, not trusted."""
        data = tarball()
        pins = pin(data)
        stale = tiptap.modules_dir() / "@tiptap" / "fake"
        stale.mkdir(parents=True)
        (stale / "leftover.js").write_text("old")
        tiptap.ensure(pins, fetch=lambda url: data)
        self.assertFalse((stale / "leftover.js").exists())
        self.assertTrue(tiptap.is_unpacked(stale, pins[0][2]))

    def test_unsafe_tarballs_are_refused_and_leave_nothing(self):
        """A member climbing out with .., an absolute path or a symbolic link is refused; nothing is written."""
        for bad in (tarball({"package/../../evil.js": b"x"}), tarball({"/abs/evil.js": b"x"}),
                    tarball(link="package/dist/link.js")):
            with self.subTest(), self.assertRaisesRegex(tiptap.TiptapError, "unsafe|not a plain file"):
                tiptap.ensure(pin(bad), fetch=lambda url, d=bad: d)
            self.assertEqual(self.files(), [])
            self.assertEqual([p for p in self.cache.rglob(".part-*")], [], "no temporary folder is left")


class PinsTest(unittest.TestCase):
    """The pins written in the script."""

    def test_pins(self):
        """Every pin is a 64-character lowercase SHA-256, names are unique, every Tiptap package is the pinned version,
        and the tarball address drops a scope from the file name."""
        names = [n for n, _, _ in tiptap.PACKAGES]
        self.assertEqual(len(names), len(set(names)))
        for name, version, sha in tiptap.PACKAGES:
            self.assertRegex(sha, r"^[0-9a-f]{64}$", name)
            self.assertRegex(version, r"^\d+\.\d+\.\d+$", name)
            if name.startswith("@tiptap/"):
                self.assertEqual(version, tiptap.PINNED, name)
        self.assertIn("@tiptap/markdown", names)
        self.assertEqual(tiptap.tarball_url("marked", "17.0.6"), "https://registry.npmjs.org/marked/-/marked-17.0.6.tgz")
        self.assertTrue(re.fullmatch(r"\d{4}-\d{2}-\d{2}", tiptap.CUTOFF))


if __name__ == "__main__":
    unittest.main()
