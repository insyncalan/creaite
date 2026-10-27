"""#374 piece 3: Project settings' Folder row shows where the folder really is. One source, #385's: build_dashboard.own_folders()["where"]
(the page reads it as place.where in ProjectSettings.jsx); there is no second map.

Run: python3 dev/tests/test_folder_real_location.py     (quick tier: no Chrome)

In the vault it is the stored form (projects/<folder>); in a projects folder under the home folder it starts with ~ and never
holds the home folder's own name. Everything is fictional and temporary.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_onedrive_projects import OneDriveCase, ENGAGEMENTS, ROOT_SETTING  # noqa: E402
from test_tracker import Vault  # noqa: E402


class ExternalRoot(OneDriveCase):
    def real(self, code):
        return self.py("import paths, build_dashboard as b\n"
                       f"print(json.dumps(b.own_folders({{{code!r}: paths.project_dir({code!r})}})['where'][{code!r}]))")

    def test_the_real_location_starts_with_a_tilde_and_never_holds_the_home_folder(self):
        for code, name in ENGAGEMENTS.items():
            got = self.real(code)
            self.assertEqual(got, f"{ROOT_SETTING.rstrip('/')}/{name}")
            self.assertTrue(got.startswith("~/"), got)
            self.assertNotIn(str(self.home), got)


class InTheVault(unittest.TestCase):
    def test_a_folder_in_the_vault_has_no_where_so_the_row_shows_the_stored_form(self):
        v = Vault()
        self.addCleanup(v.cleanup)
        src = (f"import sys, json; sys.path.insert(0, {str(v.root / 'system/scripts')!r})\n"
               "import paths, build_dashboard as b\n"
               "print(json.dumps([b.own_folders({'ABC': paths.project_dir('ABC')})['where'], paths.project_dir('ABC').name]))")
        import subprocess
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        import json
        got, name = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got, {})        # the page then shows projects/<folder>
        self.assertNotIn("folders_real", (Path(__file__).resolve().parents[2] / "system/scripts/build_dashboard.py").read_text())


if __name__ == "__main__":
    unittest.main()
