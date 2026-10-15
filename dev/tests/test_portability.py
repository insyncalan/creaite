"""Sprint portability (BL-237 to BL-242): one interpreter wrapper, gh downloads, the vendor manifest, the Brewfile, the CI matrix.

Run: python3 dev/tests/test_portability.py
Nothing here runs a real `gh`, `brew`, `pip` or `launchctl`, or contacts GitHub: a stand-in `gh` is put first on PATH.
"""
import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def shipped_settings():
    """The committed permission template, never Alan's dev copy in the working tree (it carries rules he added)."""
    out = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:.claude/settings.json"], capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else (REPO / ".claude/settings.json").read_text(encoding="utf-8")
sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import update  # noqa: E402


# ===== BL-240 (sprint-portability) =====
class Brewfile(unittest.TestCase):
    def test_the_brewfile_lists_the_development_tools(self):
        text = (REPO / "dev" / "Brewfile").read_text(encoding="utf-8")
        brews = re.findall(r'^brew "([^"]+)"', text, re.M)
        self.assertIn("gh", brews)
        self.assertIn("git", brews)
        self.assertTrue(any(b.startswith("python@3.") for b in brews), brews)

    def test_it_is_development_only_and_never_in_a_release(self):
        self.assertFalse(update.is_engine("dev/Brewfile"))
        self.assertFalse(any("dev/Brewfile".startswith(e) for e in paths.ENGINE + paths.ENGINE_MERGED))
        self.assertIn("Brewfile", (REPO / "dev" / "README.md").read_text(encoding="utf-8"))
# ===== end BL-240 =====


# ===== BL-239 (sprint-portability) =====
class VendorManifest(unittest.TestCase):
    def setUp(self):
        import shutil
        import tempfile
        import doctor
        self.doctor = doctor
        self.tmp = Path(tempfile.mkdtemp(prefix="creaite-test-portability-"))
        self.vendor = self.tmp / "vendor"
        shutil.copytree(paths.VENDOR, self.vendor, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def problems(self):
        return self.doctor.vendor_problems(self.vendor)

    def test_a_clean_vendor_folder_passes(self):
        self.assertEqual(self.problems(), ([], [], []))
        (self.vendor / "openpyxl" / "__pycache__").mkdir(exist_ok=True)              # Python's own caches don't count
        (self.vendor / "openpyxl" / "__pycache__" / "x.cpython-314.pyc").write_bytes(b"x")
        self.assertEqual(self.problems(), ([], [], []))

    def test_every_vendored_file_is_listed(self):
        listed = json.loads((paths.VENDOR / "manifest.json").read_text(encoding="utf-8"))["files"]
        self.assertEqual(set(listed), set(self.doctor.vendor_files()))
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{64}", v) for v in listed.values()))
        self.assertTrue(any(n.startswith("openpyxl/") for n in listed) and any(n.startswith("jinja2/") for n in listed))

    def test_a_changed_file_fails(self):
        f = self.vendor / "jinja2" / "__init__.py"
        f.write_text(f.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
        self.assertEqual(self.problems(), ([], ["jinja2/__init__.py"], []))

    def test_a_missing_file_fails(self):
        (self.vendor / "markupsafe" / "__init__.py").unlink()
        self.assertEqual(self.problems(), (["markupsafe/__init__.py"], [], []))

    def test_an_extra_file_fails(self):
        (self.vendor / "openpyxl" / "sneaky.py").write_text("import os\n", encoding="utf-8")
        self.assertEqual(self.problems(), ([], [], ["openpyxl/sneaky.py"]))

    def test_doctor_reports_it_in_a_vault(self):
        from test_tracker import Vault
        v = Vault()
        try:
            v.run("init")
            out = v.run(script="doctor.py", ok=False).stdout
            self.assertIn("PASS  Bundled libraries match their manifest", out)
            self.assertRegex(out, r"Bundled libraries match")
            (v.root / "system/scripts/vendor/openpyxl/extra.py").write_text("x = 1\n", encoding="utf-8")
            r = v.run(script="doctor.py", ok=False)
            self.assertIn("FAIL  Bundled libraries match their manifest — extra: openpyxl/extra.py", r.stdout)
            self.assertNotEqual(r.returncode, 0)
        finally:
            v.cleanup()

    def test_doctor_has_38_checks(self):
        text = (REPO / "system/scripts/doctor.py").read_text(encoding="utf-8")
        main = text[text.index("def main():"):]
        self.assertEqual(len(re.findall(r"^    check\(", main, re.M)), 38)   # #124: notes have a folder of their own; BL-328: the sweep lock; BL-09: folders still called zz Archive, and the skeleton's; BL-10: archiving of old items; BL-03: old reports and minutes; BL-323: restore check, Tidy up; BL-260: staged minutes have their Word draft; BL-252: refused commands; BL-267: record changes refused; BL-255: script policy reports; BL-305: the launcher
# ===== end BL-239 =====


# ===== BL-238 (sprint-portability) =====
FAKE_GH = r"""#!/usr/bin/env python3
import json, os, shutil, sys
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a") as f:
    f.write(json.dumps(args) + "\n")
if args[:2] == ["auth", "status"]:
    sys.exit(0 if os.environ.get("FAKE_GH_SIGNED_IN") == "1" else 1)
if args[:2] == ["release", "list"]:                     # BL-280: as GitHub has it, every release a pre-release
    print(os.environ.get("FAKE_GH_RELEASES") or json.dumps([
        {"tagName": "v1.6.1", "isDraft": False, "isPrerelease": True},
        {"tagName": "v9.9.9", "isDraft": False, "isPrerelease": True},
        {"tagName": "v1.7.0", "isDraft": False, "isPrerelease": True}]))
    sys.exit(0)
if args[:2] == ["release", "download"]:
    if len(args) < 3 or args[2].startswith("-"):        # no tag means "latest", which never includes a pre-release
        print("release not found", file=sys.stderr)
        sys.exit(1)
    if os.environ.get("FAKE_GH_FAIL"):
        print("HTTP 404: release not found", file=sys.stderr)
        sys.exit(1)
    d = args[args.index("--dir") + 1]
    for z in os.environ["FAKE_GH_ZIPS"].split(os.pathsep):
        shutil.copy(z, os.path.join(d, os.path.basename(z)))
    sys.exit(0)
sys.exit(3)
"""


class FetchWithGh(unittest.TestCase):
    """update.py fetch with a stand-in gh first on PATH: never the real gh, never GitHub."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        import test_update
        cls.tmp = Path(tempfile.mkdtemp(prefix="creaite-test-portability-gh-"))
        cls.zip = test_update.remake(test_update.build_release(), cls.tmp / "creaite-9.9.9.zip", version="9.9.9")
        (cls.tmp / "bad").mkdir()
        cls.bad = test_update.remake(cls.zip, cls.tmp / "bad" / "creaite-9.9.9.zip", corrupt="system/scripts/paths.py")
        cls.bin = cls.tmp / "bin"
        cls.bin.mkdir()
        (cls.bin / "gh").write_text(FAKE_GH, encoding="utf-8")
        (cls.bin / "gh").chmod(0o755)

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        from test_tracker import Vault
        self.v = Vault()
        (self.v.root / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        self.log = self.v.root / "gh-log.jsonl"

    def tearDown(self):
        self.v.cleanup()

    def fetch(self, *args, signed_in=True, zips=None, fail=False, releases=None):
        import os
        import subprocess
        env = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ.get('PATH', '')}", "FAKE_GH_LOG": str(self.log),
               "FAKE_GH_SIGNED_IN": "1" if signed_in else "0", "FAKE_GH_ZIPS": os.pathsep.join(str(z) for z in (zips or [self.zip]))}
        if fail:
            env["FAKE_GH_FAIL"] = "1"
        if releases is not None:
            env["FAKE_GH_RELEASES"] = json.dumps(releases)
        return subprocess.run([sys.executable, str(self.v.root / "system/scripts/update.py"), "fetch", *args], cwd=self.v.root,
                              env=env, capture_output=True, text=True)

    def calls(self):
        return [json.loads(x) for x in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_it_downloads_checks_and_keeps_the_newest_release(self):
        r = self.fetch()
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual((out["version"], out["path"], out["installed"], out["newer"], out["kept"]),
                         ("9.9.9", "system/releases/creaite-9.9.9.zip", "1.0.0", True, True))
        self.assertTrue((self.v.root / "system/releases/creaite-9.9.9.zip").is_file())
        self.assertEqual([x.name for x in (self.v.root / "system/releases").iterdir()], ["creaite-9.9.9.zip"])   # no temp left
        dl = next(c for c in self.calls() if c[:2] == ["release", "download"])
        self.assertEqual(dl[dl.index("--repo") + 1], "insyncalan/creaite")
        self.assertEqual(dl[dl.index("--pattern") + 1], "creaite-*.zip")
        self.assertFalse(any(c[:1] not in (["auth"], ["release"]) for c in self.calls()))       # inbound only: nothing else
        self.assertEqual((self.v.root / "VERSION").read_text().strip(), "1.0.0")              # fetched, never installed

    def test_with_no_tag_it_finds_the_newest_release_including_pre_releases(self):
        # BL-280: `gh release download` with no tag skips pre-releases, and every creaite release was one
        r = self.fetch()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["version"], "9.9.9")
        calls = [c[:2] for c in self.calls()]
        self.assertLess(calls.index(["release", "list"]), calls.index(["release", "download"]))
        lst = next(c for c in self.calls() if c[:2] == ["release", "list"])
        self.assertEqual(lst[lst.index("--repo") + 1], "insyncalan/creaite")
        self.assertIn(["release", "download", "v9.9.9"], [c[:3] for c in self.calls()])

    def test_the_newest_tag_is_chosen_by_version_without_drafts(self):
        rel = lambda t, draft=False, pre=True: {"tagName": t, "isDraft": draft, "isPrerelease": pre}   # noqa: E731
        self.assertEqual(update.newest_tag([rel("v1.9.0"), rel("v1.10.0"), rel("v1.6.1", pre=False)]), "v1.10.0")
        self.assertEqual(update.newest_tag([rel("v1.7.0"), rel("v2.0.0", draft=True), rel("nightly"), rel("v1.8.0rc1")]), "v1.7.0")
        self.assertIsNone(update.newest_tag([]))
        self.assertIsNone(update.newest_tag([rel("nightly"), "junk", rel("v3.0.0", draft=True)]))

    def test_no_release_listed_falls_back(self):
        r = self.fetch(releases=[])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("No creaite release was found", r.stderr)
        self.assertIn("by hand", r.stderr)
        self.assertNotIn(["release", "download"], [c[:2] for c in self.calls()])

    def test_a_tag_is_passed_on_and_checked(self):
        self.assertEqual(self.fetch("v9.9.9").returncode, 0)
        self.assertIn(["release", "download", "v9.9.9"], [c[:3] for c in self.calls()])
        r = self.fetch("v9.9.8")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("holds creaite 9.9.9", r.stderr)
        for bad in ("latest; rm -rf ~", "--repo=evil/x", "9.9.9"):
            r = self.fetch(bad)
            self.assertIn("isn't a release tag", r.stderr, bad)

    def test_not_signed_in_says_so_and_falls_back_to_the_manual_download(self):
        r = self.fetch(signed_in=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not signed in", r.stderr)
        self.assertIn("by hand", r.stderr)
        self.assertNotIn(["release", "download"], [c[:2] for c in self.calls()])
        self.assertFalse((self.v.root / "system/releases/creaite-9.9.9.zip").exists())

    def test_gh_missing_says_so_and_falls_back(self):
        from unittest import mock
        with mock.patch.object(update.shutil, "which", return_value=None), mock.patch.object(update, "GH_FALLBACKS", ()):
            self.assertIsNone(update.gh_path())
            with self.assertRaises(update.UpdateError) as e:
                update.fetch()
        self.assertIn("isn't installed", str(e.exception))
        self.assertIn("by hand", str(e.exception))

    def test_a_damaged_zip_is_refused_and_not_kept(self):
        r = self.fetch(zips=[self.bad])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("checksum", r.stderr)
        self.assertEqual(list((self.v.root / "system/releases").iterdir()), [])

    def test_a_failed_download_falls_back(self):
        r = self.fetch(fail=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("404", r.stderr)
        self.assertIn("by hand", r.stderr)

    def test_a_second_fetch_keeps_the_first_copy(self):
        self.assertTrue(json.loads(self.fetch().stdout)["kept"])
        self.assertFalse(json.loads(self.fetch().stdout)["kept"])

    def test_no_general_gh_rule_anywhere(self):
        import live_server
        rules = json.loads(shipped_settings())["permissions"]["allow"]
        for r in rules + live_server.READ_TOOLS + live_server.WRITE_TOOLS + live_server.OPEN_TOOLS:
            self.assertFalse(re.match(r"Bash\((\S*/)?gh\b", r), r)
# ===== end BL-238 =====



# ===== BL-237 (sprint-portability) =====
import os  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

import permissions  # noqa: E402
import reach  # noqa: E402

WRAPPER = REPO / "system" / "scripts" / "run"
ESCAPES = (                      # each must be refused by the hook, whatever the allow rules say
    "system/scripts/run -c 'import os; os.system(\"id\")'", "system/scripts/run -m http.server", "system/scripts/run",
    "system/scripts/run /bin/sh", "system/scripts/run ../../../bin/sh", "system/scripts/run system/scripts/tracker.py read actions",
    "system/scripts/run ./tracker.py", "system/scripts/run TRACKER.py read actions", "system/scripts/run run", "system/scripts/run nope.py",
    "system/scripts/run tracker.py read actions; id", "system/scripts/run tracker.py read actions && rm -rf ~",
    "system/scripts/run tracker.py read actions | sh", "system/scripts/run tracker.py read $(id)", "system/scripts/run tracker.py `id`",
    "system/scripts/run tracker.py read actions > /tmp/x", "system/scripts/run tracker.py read actions\nid",
    "system/scripts/run permissions.py apply 'Bash(*)' --why x", "system/scripts/run live_server.py", "system/scripts/run launch.py agent install",
    "system/scripts/run propose.py setting sweep.due_from 06:00", "PYTHONPATH=/tmp system/scripts/run tracker.py read actions",
    "./system/scripts/run tracker.py read actions", "system/scripts//run tracker.py read actions",
    "/bin/sh system/scripts/run tracker.py read actions", "sh system/scripts/run tracker.py read actions",
    "system/scripts/run  tracker.py read actions", "system/scripts/run \"tracker.py\" read actions", "system/scripts/run.py tracker.py",
    "python3 system/scripts/run tracker.py", "system/scripts/run tracker.py read ~/.ssh/id_rsa",
    "system/scripts/run reach.py wrap /bin/sh",
)


class WrapperHookShape(unittest.TestCase):
    """reach.bash_problem: the wrapper has exactly the shape of `python3 system/scripts/<name>.py …`, with every check kept."""

    def test_the_plain_wrapper_call_is_one_creaite_script(self):
        for cmd in ("system/scripts/run tracker.py read actions --project ABC", "system/scripts/run doctor.py",
                    'system/scripts/run filechange.py edit "projects/ABC Example Programme/notes/a.md" --from system/staging/drafts/a.md --why "tidy"',
                    'system/scripts/run propose.py new-project --code DEF --name "X" --out p.json'):
            self.assertIsNone(reach.bash_problem(cmd), cmd)

    def test_every_escape_through_the_wrapper_is_refused_by_the_hook(self):
        for cmd in ESCAPES:
            ok, why = reach.hook_decision("Bash", {"command": cmd}, "confirmed", "no-run")
            self.assertFalse(ok, cmd)
            self.assertTrue(why, cmd)

    def test_the_wrapper_is_judged_exactly_as_the_python3_spelling(self):
        for rest in ("tracker.py read actions", "filechange.py edit ~/.zshrc --from x --why y", "tracker.py read ~/.ssh/id_rsa",
                     "permissions.py list", "propose.py setting a b", "nope.py", "tracker.py read actions; id",
                     "update.py install ~/Downloads/creaite-9.9.9.zip", "live_server.py"):
            a = reach.hook_decision("Bash", {"command": f"python3 system/scripts/{rest}"}, "confirmed", "no-run")
            b = reach.hook_decision("Bash", {"command": f"system/scripts/run {rest}"}, "confirmed", "no-run")
            self.assertEqual(a[0], b[0], rest)

    def test_the_python3_shape_is_unchanged(self):
        self.assertIsNone(reach.bash_problem("python3 system/scripts/tracker.py read actions"))
        self.assertIn("permissions.py", reach.bash_problem("python3 system/scripts/permissions.py list"))
        self.assertIn("permissions.py", reach.bash_problem("system/scripts/run permissions.py list"))

    def test_without_the_wrapper_file_its_shape_is_refused(self):
        from unittest import mock
        with mock.patch.object(reach.paths, "ROOT", Path(tempfile.gettempdir()) / "no-such-vault"):
            self.assertTrue(reach.bash_problem("system/scripts/run tracker.py read actions"))


class WrapperItself(unittest.TestCase):
    """system/scripts/run run for real in a throwaway vault: it runs one creaite script and nothing else."""

    @classmethod
    def setUpClass(cls):
        from test_tracker import Vault
        cls.v = Vault()
        cls.v.run("init")
        cls.home = Path(tempfile.mkdtemp(prefix="creaite-test-portability-home-"))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()
        shutil.rmtree(cls.home, ignore_errors=True)

    def run_(self, *args, path=None, cwd=None, via_sh=True):
        env = {**os.environ, "HOME": str(self.home)}
        env.pop("CREAITE_PYTHON", None)                                      # BL-248: PATH alone here; WrapperBarePath sets it
        if path is not None:
            env["PATH"] = path
        cmd = (["/bin/sh", "system/scripts/run"] if via_sh else ["system/scripts/run"]) + list(args)
        return subprocess.run(cmd, cwd=cwd or self.v.root, env=env, capture_output=True, text=True, timeout=120)

    def test_it_is_executable_in_the_repo_and_in_a_vault(self):
        self.assertTrue(os.access(WRAPPER, os.X_OK))
        self.assertTrue(os.access(self.v.root / "system/scripts/run", os.X_OK))
        out = subprocess.run(["git", "ls-files", "-s", "system/scripts/run"], cwd=REPO, capture_output=True, text=True).stdout
        if out:
            self.assertTrue(out.startswith("100755"), out)

    def test_it_runs_one_script_with_its_arguments_and_exit_code(self):
        r = self.run_("tracker.py", "read", "projects", via_sh=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ABC", r.stdout)
        r = self.run_("reach.py", "classify", "projects/x.md", "read")
        self.assertEqual(json.loads(r.stdout)["kind"], "ordinary")
        r = self.run_("update.py", "nonsense")
        self.assertEqual(r.returncode, 2)                                    # the script's own exit code comes through
        r = subprocess.run([str(self.v.root / "system/scripts/run"), "reach.py", "classify", "projects/x.md", "read"],
                           cwd=tempfile.gettempdir(), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)                          # from any folder

    def test_it_refuses_anything_but_a_creaite_script_and_runs_nothing(self):
        canary = self.home / "canary"
        attempts = (["-c", f"open({str(canary)!r}, 'w')"], ["-m", "http.server"], ["-E", "tracker.py"], ["-"], [],
                    ["/bin/sh", "-c", f"touch {canary}"], ["../../../../bin/sh"], ["system/scripts/tracker.py"], ["./tracker.py"],
                    ["TRACKER.py"], ["run"], ["nope.py"], ["tracker.py;touch"], [".hidden.py"], ["..py"], ["tracker"],
                    ["tracker.pyc"], ["vendor/jinja2/__init__.py"], ["reach.py", "wrap", "/bin/sh"],
                    ["tracker.py", "read", str(Path.home() / ".ssh" / "id_rsa")], ["tracker.py", "read", "~/.aws/credentials"],
                    ["filechange.py", "edit", "/etc/hosts", "--from", "x", "--why", "y"])
        for argv in attempts:
            r = self.run_(*argv)
            self.assertEqual(r.returncode, 2, (argv, r.stdout, r.stderr))
            self.assertIn("creaite: system/scripts/run", r.stderr, argv)
            self.assertFalse(canary.exists(), argv)

    def stub(self, folder, name, version_ok=True):
        """A stand-in python on PATH: answers the version check, then records what it was asked to run (and runs nothing)."""
        log = folder / "ran.log"
        f = folder / name
        f.write_text("#!/bin/sh\n"
                     f'case "$1" in -c) exit {0 if version_ok else 1} ;; esac\n'
                     f'echo "{name} $*" >> "{log}"\n')
        f.chmod(0o755)
        return log

    def test_it_picks_the_newest_python_3_9_or_later(self):
        d = Path(tempfile.mkdtemp(prefix="creaite-test-portability-py-"))
        self.addCleanup(shutil.rmtree, d, True)
        old, new = d / "old", d / "new"
        old.mkdir()
        new.mkdir()
        log = self.stub(new, "python3.27")
        self.stub(new, "python3.29", version_ok=False)                      # answers "too old": skipped
        self.stub(old, "python3")
        r = self.run_("doctor.py", "--x", path=f"{old}{os.pathsep}{new}{os.pathsep}/usr/bin:/bin")
        self.assertEqual(r.returncode, 0, r.stderr)
        ran = log.read_text().split()
        self.assertEqual(ran[:4], ["python3.27", "-E", "-s", str((self.v.root / "system/scripts/reach.py").resolve())])
        self.assertEqual(ran[4:], ["wrap", "doctor.py", "--x"])             # still through reach.py's check

    def test_a_python_found_through_a_relative_path_entry_is_never_used(self):
        d = Path(tempfile.mkdtemp(prefix="creaite-test-portability-rel-"))
        self.addCleanup(shutil.rmtree, d, True)
        planted = self.stub(d, "python3.30")
        r = subprocess.run(["/bin/sh", str(self.v.root / "system/scripts/run"), "reach.py", "classify", "x.md", "read"], cwd=d,
                           env={**os.environ, "HOME": str(self.home), "PATH": f".{os.pathsep}{os.environ.get('PATH', '')}"},
                           capture_output=True, text=True, timeout=120)
        self.assertFalse(planted.exists(), "a python3.30 in the current folder ran")
        self.assertEqual(r.returncode, 0, r.stderr)                          # a real Python further along PATH ran it

    def test_no_python_fails_closed(self):
        d = Path(tempfile.mkdtemp(prefix="creaite-test-portability-none-"))
        self.addCleanup(shutil.rmtree, d, True)
        self.stub(d, "python3", version_ok=False)
        r = self.run_("doctor.py", path=str(d))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no Python 3.9 or later", r.stderr)

    def test_the_hook_runs_through_the_wrapper_and_still_refuses(self):
        import live_server  # noqa: F401  (the same command the server gives Claude Code)
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        cmd = json.loads(subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); "
                                         "import live_server; print(live_server.guard_settings('run-1', 'confirmed'))"],
                                        cwd=self.v.root, capture_output=True, text=True, check=True).stdout)
        hook = cmd["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertTrue(hook.startswith("/bin/sh "), hook)
        self.assertIn("system/scripts/run reach.py hook --run run-1 --mode confirmed", hook.replace("'", ""))

        def decide(tool, inp):
            return subprocess.run(hook, shell=True, cwd=self.v.root, capture_output=True, text=True, timeout=120,
                                  input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": inp})).returncode
        self.assertEqual(decide("Bash", {"command": "system/scripts/run tracker.py read actions"}), 0)
        self.assertEqual(decide("Bash", {"command": "python3 system/scripts/tracker.py read actions"}), 0)
        for c in ESCAPES[:6] + ("system/scripts/run tracker.py read actions; id", "system/scripts/run permissions.py list"):
            self.assertEqual(decide("Bash", {"command": c}), 2, c)
        self.assertEqual(decide("Read", {"file_path": str(Path.home() / ".ssh/id_rsa")}), 2)
        self.assertEqual(decide("Write", {"file_path": str(self.v.root / "system/scripts/run"), "content": "x"}), 2)
        self.assertEqual(decide("Bash", {"command": "{ not json"}), 2)                  # a call it can't check is refused


class WrapperRules(unittest.TestCase):
    """permissions.py, the allow lists and the shipped template name the wrapper, and nothing wider."""

    def test_a_wrapper_rule_for_one_script_is_addable_and_a_wildcard_one_never(self):
        r = permissions.check_full("Bash(system/scripts/run locations.py check *)", {"permissions": {"allow": [], "deny": []}})
        self.assertEqual((r["ok"], r["state"]), (True, "addable"))
        for rule in ("Bash(system/scripts/run *)", "Bash(system/scripts/run)", "Bash(system/scripts/run -c *)",
                     "Bash(system/scripts/run ../x.py *)", "Bash(./system/scripts/run *)", "Bash(/x/system/scripts/run *)",
                     "Bash(system/scripts/run permissions.py *)"):
            self.assertEqual(permissions.check_full(rule, {"permissions": {"allow": [], "deny": []}})["state"], "out_of_bounds", rule)
            self.assertTrue(permissions.rule_refusal(rule), rule)
        self.assertIsNone(permissions.rule_refusal("Bash(system/scripts/run report.py adhoc *)"))
        self.assertFalse(permissions.check_full("Bash(system/scripts/run nope.py *)", {"permissions": {}})["ok"])

    def test_the_wrapper_is_protected_like_the_engine(self):
        self.assertIn("system/scripts/run", permissions.PROTECTED_PATHS)
        self.assertTrue(permissions.rule_refusal("Edit(system/scripts/run)"))
        self.assertEqual(reach.classify(WRAPPER, "change")[0], "never")
        before = {"permissions": {"allow": [], "deny": ["Bash(system/scripts/run permissions.py *)"]}}
        self.assertIn("safety entry", permissions.settings_problem("claude", before, {"permissions": {"allow": [], "deny": []}}))
        self.assertIn("refused", permissions.settings_problem("claude", {"permissions": {}},
                                                              {"permissions": {"allow": ["Bash(system/scripts/run *)"]}}))

    def test_the_allow_lists_carry_a_wrapper_twin_for_each_script_rule(self):
        import live_server
        for name in ("READ_TOOLS", "WRITE_TOOLS", "OPEN_TOOLS", "DENY_TOOLS"):
            rules = getattr(live_server, name)
            for r in rules:
                m = re.fullmatch(r"Bash\(python3 system/scripts/(.+)\)", r)
                if m:
                    self.assertIn(f"Bash(system/scripts/run {m.group(1)})", rules, name)
                if r.startswith("Bash(system/scripts/run"):
                    self.assertRegex(r, r"^Bash\(system/scripts/run [a-z0-9_]+\.py\b", name)
        self.assertIn("Bash(system/scripts/run permissions.py*)", live_server.DENY_TOOLS)
        self.assertFalse([r for r in live_server.READ_TOOLS + live_server.WRITE_TOOLS + live_server.OPEN_TOOLS
                          if "permissions.py" in r or "live_server.py" in r or "launch.py" in r])
        denies = live_server.never_denies()
        for d in ("Bash(sh *)", "Bash(bash *)", "Bash(python3 -c*)", "Bash(python -c*)"):
            self.assertIn(d, denies)                                        # the shells stay denied: the wrapper isn't `sh …`

    def test_the_template_names_each_script_once_through_the_wrapper(self):
        perms = json.loads(shipped_settings())["permissions"]
        allow = perms["allow"]
        self.assertFalse([r for r in allow if r.startswith("Bash(python system/scripts/")])
        for r in allow:
            m = re.fullmatch(r"Bash\(python3 system/scripts/(.+)\)", r)
            if m:
                self.assertIn(f"Bash(system/scripts/run {m.group(1)})", allow)
            if r.startswith("Bash("):
                self.assertTrue(permissions.runs_one_script(r[5:-1]), r)
                self.assertIsNone(permissions.rule_refusal(r), r)
        self.assertIn("Bash(system/scripts/run permissions.py *)", perms["deny"])
        for d in ("Bash(python3 system/scripts/permissions.py *)", "Bash(python system/scripts/permissions.py *)"):
            self.assertIn(d, perms["deny"])                                  # existing safety entries all kept

    def test_an_update_adds_the_wrapper_rules_and_keeps_the_old_ones(self):
        current = {"permissions": {"allow": ["Bash(python system/scripts/tracker.py *)", "Bash(python3 system/scripts/tracker.py *)"],
                                   "deny": []}}
        incoming = json.loads(shipped_settings())
        update.merge_permissions(current, incoming)
        allow = current["permissions"]["allow"]
        self.assertIn("Bash(python system/scripts/tracker.py *)", allow)
        self.assertIn("Bash(system/scripts/run tracker.py *)", allow)

    def test_the_docs_show_the_wrapper_only_in_allowed_shapes(self):
        docs = sorted((REPO / ".claude/skills").glob("*/SKILL.md")) + sorted((REPO / ".claude/skills").glob("*/references/*.md")) + [
            REPO / "system/creaite-rules.md"]
        span = re.compile(r"`(system/scripts/run [^`]+)`")
        bad = re.compile(r"(?:\s>>?\s*\S|2>&1|&&|<<|\$\(|\s\|\s+(?:python|grep|head|tail|jq|tee|cat|sort|wc)\b|/tmp/)")
        found, wrong = 0, []
        for f in docs:
            for m in span.finditer(f.read_text(encoding="utf-8")):
                found += 1
                if bad.search(m.group(1)) or not re.match(r"system/scripts/run [a-z0-9_]+\.py\b", m.group(1)):
                    wrong.append(f"{f.relative_to(REPO)}: {m.group(1)[:90]}")
        self.assertGreater(found, 20)
        self.assertEqual(wrong, [])


class WrapperShipped(unittest.TestCase):
    def test_the_messages_people_read_name_the_wrapper(self):
        # BL-282: the login agent's "Remove it any time" and new-vault's "Next" still printed python3 system/scripts/…
        launch = (REPO / "system/scripts/launch.py").read_text(encoding="utf-8")
        self.assertIn('print("Remove it any time: system/scripts/run launch.py agent remove")', launch)
        upd = (REPO / "system/scripts/update.py").read_text(encoding="utf-8")
        self.assertIn('&& system/scripts/run live_server.py', upd)
        self.assertNotIn('&& python3 system/scripts/live_server.py', upd)

    def test_install_new_vault_and_tidy_make_it_executable(self):
        d = Path(tempfile.mkdtemp(prefix="creaite-test-portability-x-"))
        self.addCleanup(shutil.rmtree, d, True)
        w = d / "system/scripts/run"
        w.parent.mkdir(parents=True)
        w.write_bytes(WRAPPER.read_bytes())                                  # as zipfile writes it: no execute bit
        w.chmod(0o644)
        self.assertTrue(update.wrapper_executable(d))
        self.assertTrue(os.access(w, os.X_OK))
        self.assertEqual(w.stat().st_mode & 0o777, 0o755)
        self.assertFalse(update.wrapper_executable(d))                       # nothing the second time

    def test_the_release_zip_marks_it_executable(self):
        import zipfile
        import test_update
        with zipfile.ZipFile(test_update.build_release()) as z:
            info = z.getinfo("system/scripts/run")
            self.assertEqual((info.external_attr >> 16) & 0o777, 0o755)
            self.assertEqual(z.getinfo("system/scripts/reach.py").external_attr >> 16 & 0o777, 0o644)
# ===== end BL-237 =====


# ===== BL-248 (sprint-portability): the right Python under creaite.app's bare PATH =====
BARE = "/usr/bin:/bin"                    # launchd's PATH, as creaite.app gets it (less /usr/sbin:/sbin)


class WrapperBarePath(unittest.TestCase):
    """The wrapper and the hook started from a bare PATH: CREAITE_PYTHON (set by the server's run_env) makes them work; without
    it and with no Python on PATH they say it is a creaite fault and still fail closed."""

    @classmethod
    def setUpClass(cls):
        from test_tracker import Vault
        cls.v = Vault()
        cls.v.run("init")
        cls.home = Path(tempfile.mkdtemp(prefix="creaite-test-portability-home-"))
        cls.empty = Path(tempfile.mkdtemp(prefix="creaite-test-portability-nopy-"))   # a PATH folder with no Python at all

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()
        shutil.rmtree(cls.home, ignore_errors=True)
        shutil.rmtree(cls.empty, ignore_errors=True)

    def env(self, path, python=None):
        env = {k: v for k, v in os.environ.items() if k != "CREAITE_PYTHON"}
        env.update(HOME=str(self.home), PATH=path)
        if python:
            env["CREAITE_PYTHON"] = python
        return env

    def run_(self, *args, path=BARE, python=None):
        return subprocess.run(["/bin/sh", "system/scripts/run", *args], cwd=self.v.root, env=self.env(path, python),
                              capture_output=True, text=True, timeout=120)

    def recorder(self):
        """A CREAITE_PYTHON that notes each call, then runs the real Python with the same arguments."""
        d = Path(tempfile.mkdtemp(prefix="creaite-test-portability-cp-"))
        self.addCleanup(shutil.rmtree, d, True)
        f, log = d / "python3", d / "used.log"
        f.write_text(f'#!/bin/sh\necho "$1" >> "{log}"\nexec "{sys.executable}" "$@"\n')
        f.chmod(0o755)
        return str(f), log

    def test_with_creaite_python_it_works_from_a_bare_or_empty_path(self):
        for path in (BARE, str(self.empty)):
            r = self.run_("reach.py", "classify", "projects/x.md", "read", path=path, python=sys.executable)
            self.assertEqual(r.returncode, 0, (path, r.stderr))
            self.assertEqual(json.loads(r.stdout)["kind"], "ordinary")

    def test_creaite_python_is_used_first(self):
        fake, log = self.recorder()
        r = self.run_("reach.py", "classify", "x.md", "read", python=fake)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("-E", log.read_text().split())                          # it started reach.py wrap, as the PATH one would

    def test_an_unusable_creaite_python_falls_back_to_path(self):
        d = Path(tempfile.mkdtemp(prefix="creaite-test-portability-old-"))
        self.addCleanup(shutil.rmtree, d, True)
        old = d / "python3"
        old.write_text("#!/bin/sh\nexit 1\n")                                 # answers "too old"
        old.chmod(0o755)
        here = str(Path(sys.executable).parent)
        for bad in (str(old), "python3", str(d / "missing")):                 # too old, not absolute, not there
            r = self.run_("reach.py", "classify", "x.md", "read", path=here, python=bad)
            self.assertEqual(r.returncode, 0, (bad, r.stderr))

    def test_every_refusal_holds_with_creaite_python_set(self):
        canary = self.home / "canary"
        for argv in (["-c", f"open({str(canary)!r}, 'w')"], ["-m", "http.server"], ["/bin/sh"], ["../x.py"], ["nope.py"],
                     ["tracker.py", "read", str(Path.home() / ".ssh" / "id_rsa")], ["reach.py", "wrap", "/bin/sh"]):
            r = self.run_(*argv, python=sys.executable)
            self.assertEqual(r.returncode, 2, (argv, r.stderr))
            self.assertIn("creaite: system/scripts/run", r.stderr)
            self.assertFalse(canary.exists())

    def test_no_python_anywhere_is_a_creaite_fault_and_fails_closed(self):
        r = self.run_("reach.py", "classify", "x.md", "read", path=str(self.empty))
        self.assertEqual(r.returncode, 2)
        self.assertIn("no Python 3.9 or later", r.stderr)
        self.assertIn("creaite start-up fault, not a fault on this Mac", r.stderr)
        self.assertNotRegex(r.stderr, r"(?i)\brun sudo|xcode-select --|install python")
        import live_server
        self.assertIsNotNone(live_server.prestart_fault(r.stderr))            # and the panel would call it creaite's fault

    def hook(self):
        cmd = json.loads(subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); "
                                         "import live_server; print(live_server.guard_settings('run-1', 'ask'))"],
                                        cwd=self.v.root, capture_output=True, text=True, check=True).stdout)
        return cmd["hooks"]["PreToolUse"][0]["hooks"][0]["command"]

    def decide(self, hook, env, tool, inp):
        return subprocess.run(hook, shell=True, cwd=self.v.root, env=env, capture_output=True, text=True, timeout=120,
                              input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": inp}))

    def test_the_hook_works_from_a_bare_path_with_creaite_python(self):
        hook = self.hook()
        env = self.env(BARE, sys.executable)
        r = self.decide(hook, env, "Bash", {"command": "system/scripts/run tracker.py read actions"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.decide(hook, env, "Bash", {"command": "system/scripts/run tracker.py read actions; id"}).returncode, 2)
        self.assertEqual(self.decide(hook, env, "Read", {"file_path": str(Path.home() / ".ssh/id_rsa")}).returncode, 2)

    def test_the_hook_with_no_python_fails_closed_and_says_why(self):
        r = self.decide(self.hook(), self.env(str(self.empty)), "Bash", {"command": "system/scripts/run tracker.py read actions"})
        self.assertEqual(r.returncode, 2)
        self.assertIn("creaite start-up fault", r.stderr)


class RunEnv(unittest.TestCase):
    def test_run_env_puts_this_python_first_and_names_it(self):
        import live_server
        old = os.environ.get("PATH")
        os.environ["PATH"] = BARE
        try:
            env = live_server.run_env()
        finally:
            os.environ["PATH"] = old
        parts = env["PATH"].split(os.pathsep)
        self.assertEqual(parts[0], str(Path(sys.executable).parent))
        for d in ("/opt/homebrew/bin", "/usr/local/bin", str(Path.home() / ".local/bin"), "/usr/bin", "/bin"):
            self.assertIn(d, parts)
        self.assertLess(parts.index("/usr/local/bin"), parts.index("/usr/bin"))   # never Apple's stub before a real Python
        self.assertEqual(len(parts), len(set(parts)))
        self.assertEqual(env["CREAITE_PYTHON"], sys.executable)
        found = shutil.which("python3", path=env["PATH"])
        if (Path(sys.executable).parent / "python3").exists():
            self.assertEqual(os.path.realpath(found), os.path.realpath(sys.executable))

    def test_every_child_the_server_starts_gets_it(self):
        src = (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
        launches = re.findall(r'claude_path\(\), "-p".*?(subprocess\.(?:Popen|run)\((?:[^()]|\([^()]*\))*\))', src, re.S)
        self.assertEqual(len(launches), 2)                                      # ask runs and the VIP check
        for call in launches:                                                   # each launch passes the run environment
            self.assertRegex(call, r"\benv=(?:env|run_env\([^()]*\))(?=[,)\s])")
        self.assertEqual(len(re.findall(r"\benv\s*=\s*run_env\(", src)), 2)    # BL-328, #60: run_env() or run_env(kind)

    def test_a_script_that_never_started_is_named_a_creaite_fault(self):
        import live_server
        f = live_server.prestart_fault
        self.assertTrue(f("xcrun: error: unable to load libxcrun (have 'arm64,arm64e', need 'x86_64')"))
        self.assertTrue(f("ModuleNotFoundError: No module named 'paths'"))
        self.assertTrue(f("sh: python3: command not found"))
        self.assertIsNone(f("Problem: ABC-A-099 doesn't exist\nNo module named x"))  # creaite's own Problem line: the script ran
        self.assertIsNone(f('{"kind": "ordinary"}'))
        note = live_server.FAULT_NOTE.format(line="xcrun: error")
        self.assertIn("creaite fault", note)
        self.assertIn("Diagnostics", note)
        self.assertIn("never suggest sudo, xcode-select", live_server.ASK_PROMPT)


class LauncherArchitecture(unittest.TestCase):
    def test_the_app_asks_for_arm64_and_finds_this_python(self):
        import plistlib
        import launch
        dest = Path(tempfile.mkdtemp(prefix="creaite-apps-"))
        self.addCleanup(shutil.rmtree, dest, True)
        r = subprocess.run([sys.executable, str(REPO / "system/scripts/launch.py"), "make-launcher", "--dest", str(dest)],
                           cwd=REPO, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        app = dest / f"{launch.launcher_name()}.app"                           # BL-305: "creaite (dev)" in this repository
        info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
        self.assertEqual(info["LSArchitecturePriority"], ["arm64", "x86_64"])
        script = (app / "Contents/MacOS/creaite").read_text(encoding="utf-8")
        self.assertIn(f"export PATH={Path(sys.executable).parent}:", script.replace("'", ""))
        self.assertNotIn(sys.executable, script)                               # a folder, never a Python baked in
        self.assertEqual("/usr/bin/arch -arm64 /bin/sh" in script, launch.apple_silicon())
        self.assertIn("system/scripts/run launch.py", script)

    def test_rosetta_is_detected_without_failing(self):
        import launch
        self.assertIn(launch.under_rosetta(), (True, False))
        if sys.platform != "darwin":
            self.assertFalse(launch.apple_silicon())

    def test_doctor_warns_about_an_old_launcher(self):
        import doctor
        home = Path(tempfile.mkdtemp(prefix="creaite-test-portability-home-"))
        self.addCleanup(shutil.rmtree, home, True)
        plist = home / "Applications/creaite.app/Contents/Info.plist"
        plist.parent.mkdir(parents=True)
        plist.write_text("<plist><dict><key>CFBundleName</key><string>creaite</string></dict></plist>")
        old = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
        try:
            ok, detail = doctor.python_version()
            self.assertIsNone(ok)
            self.assertIn("old launcher", detail)
            plist.write_text("<plist><dict><key>LSArchitecturePriority</key></dict></plist>")
            ok, detail = doctor.python_version()
            self.assertNotIn("old launcher", detail)
        finally:
            os.environ["HOME"] = old
# ===== end BL-248 =====


if __name__ == "__main__":
    unittest.main()
