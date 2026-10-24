"""Dev speed: a seeded test vault is built once per class and each test gets a copy-on-write clone of it, instead of every test
building its own (vault files, `init`, the seed proposals and their `apply` runs are the setUp cost). Not a test file.

clone(template) copies the folder with the file system's own cloning where there is one (`cp -c` on a Mac's APFS, `cp --reflink=auto`
with GNU cp on Linux) and a plain copy otherwise, into a new temp folder named like make_vault's (so the runner's leak check and
BL-172's cleanup still see it). The clone is a whole independent vault: changing it never touches the template or another clone.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_tracker as T  # noqa: E402


def _copy(src, dst):
    """src's contents into the existing folder dst, cloned if the file system can, else copied."""
    attempts = ([["cp", "-c", "-R", f"{src}/.", str(dst)]] if sys.platform == "darwin"
                else [["cp", "--reflink=auto", "-R", f"{src}/.", str(dst)]])
    for cmd in attempts:
        if subprocess.run(cmd, capture_output=True).returncode == 0:
            return "clone"
        for p in Path(dst).iterdir():                   # a half copy is removed before the fallback
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink()
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return "copy"


_TEMPLATES = {}                  # (key, vault class, clock, stamp day) -> the seeded template Vault, built once per process


def populated(v, key, build):
    """Make the fresh vault `v` hold what build(vault) puts in a vault, from a clone of a template built once per process.

    The speed-up for every test that makes a vault and calls populate() in its setUp: build() runs once per process (on a template of
    the same class as `v`), and each later call just clones it (copy-on-write where the file system has it). `v` is changed in place:
    its folder is replaced by the clone, so the caller's `v` and `v.root` afterwards are the clone's. A vault that is not fresh (it already
    has a database) is built directly, and CREAITE_NO_CLONE=1 builds every time as before. The key includes the clock the data is dated
    from (CREAITE_NOW, CREAITE_STAMP_DAY), so a test that changes the clock gets its own template."""
    if os.environ.get("CREAITE_NO_CLONE") or (v.root / "system" / "tracker.db").exists():
        return build(v)
    k = (key, type(v).__name__, os.environ.get("CREAITE_NOW"), os.environ.get("CREAITE_STAMP_DAY"))
    if k not in _TEMPLATES:
        tpl = type(v)()
        build(tpl)
        _TEMPLATES[k] = tpl
    old, v.root = v.root, clone(_TEMPLATES[k].root)
    shutil.rmtree(old, ignore_errors=True)


def clone(template):
    """A new vault folder that is a copy of `template` (a Path). Remembered for cleanup like make_vault's."""
    tmp = Path(tempfile.mkdtemp(prefix=T.vault_prefix()))
    T.MADE_VAULTS.append(tmp)
    _copy(template, tmp)
    return tmp
