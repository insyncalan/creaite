"""v2.5.1 (#239): property tests of the client export path, after Team Cap's list (dev/proposals/props239/PROPERTIES.md on
origin/v251-properties: P1..P25, generator, oracle and the finding each would have caught). The data is fictional.

Run: python3 dev/tests/test_client_output_properties.py                 smoke: 50 cases a property, seed 239 (fast, deterministic)
     CREAITE_PROPS_FULL=1 python3 dev/tests/test_client_output_properties.py   full: 2000 (fewer where the list says)
     CREAITE_PROPS_MUTANTS=1 ...                                           also the mutation proofs: each property goes red with its
                                                                           guard switched off (MUTANTS)
     PROP_SEED=<n> replays another seed. PDF cases need Chrome. If `hypothesis` is installed, P1 also runs on seeds it draws.

The generator and the properties are dev/tests/client_output_props.py (standard library only, seeded), run inside this file's
throwaway vault. Each property's docstring there states it; a failure prints its seed, case and mutation list to replay.
Not run here: P12 and P25 (browser tier: asynchronous answers racing in the page, and the bulk Match and slash menu in the
sheet). P25 runs in test_client_output_p25.py (Chrome); P12's server half is step 2's test_preview_P12_* (the answer names the
report it is of); its page half (a delayed answer landing on another report's pane) has no browser test yet.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
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
         "P20": (50, 2000), "P21": (50, 500), "P22": (50, 500), "P23": (20, 500), "P24": (20, 200)}
# the guard each property must go red without (PROPERTIES.md "Mutation proof"), as a mutant of client_output_props._mutant
MUTANTS = {"P1": "gate_off", "P2": "reread", "P3": "derive_off", "P4": "derive_off", "P5": "gate_off+allow_off", "P6": "same_report_off",
           "P7": "allow_off+facts_off", "P8": "signs_off", "P9": "names_off", "P10": "page_used+output_off", "P11": "gate_off+trust_on",
           "P13": "pictures_off+output_off+trust_on",
           "P13shared": "gap_c_off+output_off+trust_on", "P14": "logos_off+derive_off+output_off", "P15": "metadata_kept", "P16": "decoder_off", "P16out": "loose_off",
           "P17": "audience_flip", "P18": "stub_off", "P18facts": "facts_off", "P19": "output_off", "P20": "allow_off", "P21": "other_parser+gate_off", "P22": "match_raw", "P23": "gate_off+trust_on+apply_check_off"}

try:
    import hypothesis
    from hypothesis import strategies as st
except ImportError:          # not installed here or in CI: the seeded generator alone runs
    hypothesis = None


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
    """The export, approve, save, check and minutes paths in the throwaway vault (test_client_audience's harness)."""

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

    def test_P01_gate_or_clean(self): self.check("P1")
    def test_P02_one_read_and_the_render_of_it(self): self.check("P2")
    def test_P03_derived_fields_are_fixed_points(self): self.check("P3")
    def test_P04_underived_fields_change_no_byte(self): self.check("P4")
    def test_P05_every_field_path(self): self.check("P5")
    def test_P06_another_project_or_week_is_refused_and_nothing_is_written(self): self.check("P6")
    def test_P07_unknown_keys_at_any_depth(self): self.check("P7")
    def test_P08_kind_audience_route_source_table(self): self.check("P8")
    def test_P09_file_names(self): self.check("P9")
    def test_P10_a_posted_page_is_never_the_source(self): self.check("P10")
    def test_P11_a_writer_racing_the_export(self): self.check("P11")

    @unittest.skip("P12 is the browser tier (asynchronous answers racing in the page): not run by this file")
    def test_P12_answers_for_one_report_never_change_another(self): pass

    def test_P13_pictures(self): self.check("P13")

    def test_P13_shared_images_store_known_gap_C(self):
        """Known gap C, closed in step 2: a picture added for the internal report is never drawn into a client report (a client
        report's own pictures are `_images/client-<name>`, drawn only as its snapshot's picture table records them)."""
        self.check("P13shared")

    def test_P14_logos(self): self.check("P14")

    @unittest.skipUnless(S.HAVE_CHROME, "an SVG logo is drawn by Chrome: P15 needs it")
    def test_P15_uploaded_logos(self): self.check("P15")

    def test_P16_every_text_form_is_gated_as_the_plain_one(self): self.check("P16")

    def test_P16_json_escaped_form_is_gated(self):
        """The JSON-escaped form (\\u0061 for a) is read by client_leak.findings since the guarded gate diff (client-output-step1) is in."""
        self.check("P16json")

    def test_P16_output_check_reads_loose_ids_and_separators(self):
        """v2.5.3 (#259): the output check every client file passes reads an ID with its letters or digits spaced, more zeros or
        fewer, and a wording with hyphens, dots or underscores for its spaces, as the plain form."""
        self.check("P16out")

    def test_P17_internal_sections(self): self.check("P17")
    def test_P18_hidden_rows_items_tags_and_milestones(self): self.check("P18")

    def test_P18_stored_fields_are_derived_and_items_are_the_facts(self):
        """v2.5.3 (#259, K3 / I19): plain words in a stored field no output draws reach no output; a kept item is the facts'."""
        self.check("P18facts")
    def test_P19_the_post_render_check_on_its_own(self): self.check("P19")
    def test_P20_the_filed_data_block(self): self.check("P20")
    def test_P21_raw_transforms(self): self.check("P21")
    def test_P22_read_only_routes(self): self.check("P22")
    def test_P23_approve_files_the_export_and_undo_restores(self): self.check("P23")
    def test_P24_repeat_exports(self): self.check("P24")

    @unittest.skip("P25 is the browser tier: it runs in test_client_output_p25.py (Chrome; v2.5.1 step 3)")
    def test_P25_bulk_match_adds_no_section(self): pass

    @unittest.skipUnless(MUTANTS_ON, "the mutation proofs run with CREAITE_PROPS_MUTANTS=1")
    def test_mutation_proofs_each_property_goes_red_without_its_guard(self):
        for prop, mutant in MUTANTS.items():
            with self.subTest(prop=prop, mutant=mutant):
                out = self.run_prop(prop, n=min(SIZES[prop][0], 30), mutant=mutant)
                print(f"\n{prop} with {mutant}: failed={out['failed']}", file=sys.stderr)
                self.assertGreater(out["failed"], 0, f"{prop} stayed green with {mutant}: the property doesn't test its guard")

    @unittest.skipIf(hypothesis is None, "hypothesis isn't installed: the seeded generator covers the same properties")
    def test_P01_under_hypothesis(self):
        @hypothesis.settings(max_examples=10, deadline=None, database=None)
        @hypothesis.given(st.integers(min_value=0, max_value=2**31))
        def prop(seed):
            self.assertEqual(self.run_prop("P1", n=10, seed=seed)["failed"], 0)
        prop()


for _name in [n for n in dir(A.Audience) if n.startswith("test_")]:
    setattr(Properties, _name, None)                          # only this file's tests run here


class Skeleton(unittest.TestCase):
    """P16's text forms at the fold itself (pure; no vault)."""

    def test_P16a_a_disguised_word_has_the_words_skeleton(self):
        """For 2,000 seeded random words of Latin letters and digits, skeleton(disguise(w)) lower-cased equals skeleton(w) lower-cased,
        where disguise swaps letters for look-alikes from confusables.TABLE, adds zero-width and format characters, accents and
        fullwidth forms."""
        import random
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        import confusables
        rng = random.Random(SEED)
        looks = {}
        for cp, latin in confusables.TABLE.items():
            looks.setdefault(latin, []).append(chr(cp))
        zw = "​‌‍⁠­﻿"
        for _ in range(2000):
            w = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-") for _ in range(rng.randint(3, 20)))
            out = []
            for c in w:
                r = rng.random()
                if c in looks and r < 0.4:
                    c = rng.choice(looks[c])
                elif r < 0.55 and "!" <= c <= "~":
                    c = chr(ord(c) + 0xFEE0)
                elif r < 0.65 and c.isalpha():
                    c += "́"
                out.append(c + (rng.choice(zw) if rng.random() < 0.2 else ""))
            d = "".join(out)
            self.assertEqual(confusables.skeleton(d).lower(), confusables.skeleton(w).lower(), (w, d))


if __name__ == "__main__":
    unittest.main(verbosity=2)
