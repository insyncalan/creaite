"""The shared harness of the client-output property tests (#239), split across test_client_output_properties*.py so each file
runs well under run_tests.py's 900 s --file-timeout on a CI shard (v2.5.3 gate). Not a test file itself (no `test_` prefix):
each test_client_output_properties*.py subclasses Properties and names its own properties and their mutation proofs.

Environment (read by every file):
     CREAITE_PROPS_FULL=1      full: 2000 cases a property (fewer where the list says); smoke (the default): 50, seed 239
     CREAITE_PROPS_MUTANTS=1   also the mutation proofs: each property goes red with its guard switched off (MUTANTS)
     PROP_SEED=<n>             replays another seed. PDF cases need Chrome.

The generator and the properties are dev/tests/client_output_props.py (standard library only, seeded), run inside each file's
throwaway vault. Each property's docstring there states it; a failure prints its seed, case and mutation list to replay.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_client_audience as A  # noqa: E402
import test_report_export_save as S  # noqa: E402
from test_dashboard import png  # noqa: E402
from test_tracker import ABC  # noqa: E402

RUNNER = Path(__file__).resolve().parent / "client_output_props.py"
SEED = int(os.environ.get("PROP_SEED") or 239)
FULL = os.environ.get("CREAITE_PROPS_FULL") == "1"
MUTANTS_ON = os.environ.get("CREAITE_PROPS_MUTANTS") == "1"
# cases per property: (smoke, full), as the list sets them
SIZES = {"P1": (50, 2000), "P2": (50, 2000), "P3": (50, 2000), "P4": (50, 2000), "P5": (1, 1), "P6": (50, 2000), "P7": (50, 2000),
         "P8": (50, 2000), "P9": (50, 2000), "P10": (50, 2000), "P11": (50, 200), "P13": (50, 2000), "P13shared": (3, 3),
         "P14": (50, 500), "P15": (6, 50), "P16": (50, 2000), "P16json": (22, 22), "P16out": (52, 2000), "P17": (50, 500), "P18": (50, 2000),
         "P18facts": (27, 500), "P19": (50, 500),
         "P20": (50, 2000), "P21": (50, 500), "P22": (50, 500), "P23": (20, 500), "P24": (20, 200),
         "P26twice": (12, 200)}
# the guard each property must go red without (PROPERTIES.md "Mutation proof"), as a mutant of client_output_props._mutant
MUTANTS = {"P1": "gate_off", "P2": "reread", "P3": "derive_off", "P4": "derive_off", "P5": "gate_off+allow_off", "P6": "same_report_off",
           "P7": "allow_off+facts_off", "P8": "signs_off", "P9": "names_off", "P10": "page_used+output_off", "P11": "gate_off+trust_on",
           "P13": "pictures_off+output_off+trust_on",
           "P13shared": "gap_c_off+output_off+trust_on", "P14": "logos_off+derive_off+output_off", "P15": "metadata_kept", "P16": "decoder_off", "P16out": "loose_off",
           "P17": "audience_flip", "P18": "stub_off", "P18facts": "facts_off", "P19": "output_off", "P20": "allow_off", "P21": "other_parser+gate_off", "P22": "match_raw", "P23": "gate_off+trust_on+apply_check_off",
           "P26twice": "launder_on"}


def setup_world(root):
    """Another project with a hidden action (X), and the planted hostile pictures (another project's logo, an internal project
    picture, a file outside the vault)."""
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(root / "system/tracker.db")) as con:
        if not con.execute("SELECT 1 FROM projects WHERE code='DEF'").fetchone():
            con.execute("INSERT INTO projects (code, name) VALUES ('DEF', 'Digital Enablement')")
        if not con.execute("SELECT 1 FROM actions WHERE id='DEF-A-001'").fetchone():
            con.execute("INSERT INTO actions (id, project, description, owner, raised, source) VALUES "
                        "('DEF-A-001', 'DEF', 'Replace the walrus vendor before renewal', 'Priya Okafor', '2026-10-01', 'test')")
        con.commit()
    (root / "system/branding/logos").mkdir(parents=True, exist_ok=True)
    (root / "system/branding/logos/DEF-client.png").write_bytes(png(31, 7, (1, 2, 3)))
    (root / ABC / "images").mkdir(parents=True, exist_ok=True)
    (root / ABC / "images/internal-org-chart.png").write_bytes(png(29, 11, (4, 5, 6)))
    outside = Path(tempfile.mkdtemp()) / "secret.png"
    outside.write_bytes(png(23, 13, (7, 8, 9)))
    pics = ["system/branding/logos/DEF-client.png", f"{ABC}/images/internal-org-chart.png", str(outside)]
    (root / "system/staging/props-pictures.json").write_text(json.dumps(pics))


class Properties(A.Audience):
    """The export, approve, save, check and minutes paths in the throwaway vault (test_client_audience's harness). A subclass
    sets PROPS, the properties its file checks: its mutation proof covers those that have a mutant, so together the files
    prove every property in MUTANTS (test_client_output_properties.py checks the files' PROPS are SIZES' keys, once each)."""
    PROPS = ()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        setup_world(cls.v.root)

    def setUp(self):
        super().setUp()
        self.fresh()

    def run_prop(self, prop, n=None, mutant="", seed=SEED):
        n = n or SIZES[prop][1 if FULL else 0]
        env = {**os.environ, "CREAITE_NOW": S.NOW, "CREAITE_NO_LAUNCH": "1"}
        r = subprocess.run([sys.executable, str(RUNNER), str(self.v.root), prop, str(seed), str(n), mutant], cwd=self.v.root, env=env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-5000:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def check(self, prop):
        out = self.run_prop(prop)
        print(f"\n{prop} seed={out['seed']} cases={out['cases']} stats={out['stats']} failed={out['failed']}", file=sys.stderr)
        self.assertEqual(out["failed"], 0, f"{prop} seed={out['seed']}: {json.dumps(out['failures'], default=str)[:3000]}")

    def mutation_proofs(self):
        """Each of this file's properties goes red with its guard switched off."""
        for prop in [p for p in self.PROPS if p in MUTANTS]:     # P16json has no mutant (as before the split)
            mutant = MUTANTS[prop]
            with self.subTest(prop=prop, mutant=mutant):
                out = self.run_prop(prop, n=min(SIZES[prop][0], 30), mutant=mutant)
                print(f"\n{prop} with {mutant}: failed={out['failed']}", file=sys.stderr)
                self.assertGreater(out["failed"], 0, f"{prop} stayed green with {mutant}: the property doesn't test its guard")


for _name in [n for n in dir(A.Audience) if n.startswith("test_")]:
    setattr(Properties, _name, None)                          # only the property files' own tests run there
