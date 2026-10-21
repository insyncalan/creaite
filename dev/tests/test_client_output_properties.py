"""v2.5.1 (#239): property tests of the client export path, after Team Cap's list (dev/proposals/props239/PROPERTIES.md on
origin/v251-properties: P1..P25, generator, oracle and the finding each would have caught). The data is fictional.

v2.5.3 gate: split in four files, each well under run_tests.py's 900 s --file-timeout on a CI shard (one file had run over it):
  test_client_output_properties.py           P1-P6 (the gate, one read, derived fields, every field path, another report),
                                             P16a (the fold), and the files' coverage of every property and mutant
  test_client_output_properties_pictures.py  P9, P10, P13, P13shared, P14, P15, P24 (and P25's placeholder)
  test_client_output_properties_sections.py  P7, P8, P17, P19, P26twice
  test_client_output_properties_routes.py    P11, P16, P16json, P16out, P18, P18facts, P20-P23 (and P12's placeholder)
The harness, SIZES and MUTANTS are dev/tests/client_output_props_case.py; the generator and the properties are
dev/tests/client_output_props.py (standard library only, seeded), run inside each file's throwaway vault.

Run: python3 dev/tests/test_client_output_properties.py                 smoke: 50 cases a property, seed 239 (fast, deterministic)
     CREAITE_PROPS_FULL=1 python3 dev/tests/test_client_output_properties.py   full: 2000 (fewer where the list says)
     CREAITE_PROPS_MUTANTS=1 ...                                           also the mutation proofs: each of the file's properties
                                                                           goes red with its guard switched off (MUTANTS); run
                                                                           all four files for every property
     PROP_SEED=<n> replays another seed. PDF cases need Chrome. If `hypothesis` is installed, P1 also runs on seeds it draws.
Not run here: P12 and P25 (browser tier: asynchronous answers racing in the page, and the bulk Match and slash menu in the
sheet). P25 runs in test_client_output_p25.py (Chrome); P12's server half is step 2's test_preview_P12_* (the answer names the
report it is of); its page half (a delayed answer landing on another report's pane) has no browser test yet.
"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client_output_props_case as C  # noqa: E402
import test_client_output_properties_pictures as PIC  # noqa: E402
import test_client_output_properties_routes as ROU  # noqa: E402
import test_client_output_properties_sections as SEC  # noqa: E402

try:
    import hypothesis
    from hypothesis import strategies as st
except ImportError:          # not installed here or in CI: the seeded generator alone runs
    hypothesis = None


class Properties(C.Properties):
    PROPS = ("P1", "P2", "P3", "P4", "P5", "P6")

    def test_P01_gate_or_clean(self): self.check("P1")
    def test_P02_one_read_and_the_render_of_it(self): self.check("P2")
    def test_P03_derived_fields_are_fixed_points(self): self.check("P3")
    def test_P04_underived_fields_change_no_byte(self): self.check("P4")
    def test_P05_every_field_path(self): self.check("P5")
    def test_P06_another_project_or_week_is_refused_and_nothing_is_written(self): self.check("P6")

    @unittest.skipUnless(C.MUTANTS_ON, "the mutation proofs run with CREAITE_PROPS_MUTANTS=1")
    def test_mutation_proofs_each_property_goes_red_without_its_guard(self): self.mutation_proofs()

    @unittest.skipIf(hypothesis is None, "hypothesis isn't installed: the seeded generator covers the same properties")
    def test_P01_under_hypothesis(self):
        @hypothesis.settings(max_examples=10, deadline=None, database=None)
        @hypothesis.given(st.integers(min_value=0, max_value=2**31))
        def prop(seed):
            self.assertEqual(self.run_prop("P1", n=10, seed=seed)["failed"], 0)
        prop()


class Coverage(unittest.TestCase):
    """The four files together check every property and prove every mutant, each in exactly one file (pure; no vault)."""

    def test_every_property_and_mutant_is_in_exactly_one_file(self):
        classes = [Properties, PIC.Properties, SEC.Properties, ROU.Properties]
        props = [p for c in classes for p in c.PROPS]
        self.assertEqual(len(props), len(set(props)), "a property is in two files")
        self.assertEqual(sorted(props), sorted(C.SIZES), "the files' properties are SIZES' keys")
        self.assertLessEqual(set(C.MUTANTS), set(props), "every mutant's property is in a file")
        for c in classes:
            names = [n for n in dir(c) if n.startswith("test_") and callable(getattr(c, n))]
            self.assertIn("test_mutation_proofs_each_property_goes_red_without_its_guard", names, c.__module__)
            for p in c.PROPS:
                checked = [n for n in names if f'self.check("{p}")' in _source(c, n)]
                self.assertTrue(checked, f"{c.__module__}: no test checks {p}")


def _source(cls, name):
    import inspect
    try:
        return inspect.getsource(getattr(cls, name))
    except (OSError, TypeError):
        return ""


class Skeleton(unittest.TestCase):
    """P16's text forms at the fold itself (pure; no vault)."""

    def test_P16a_a_disguised_word_has_the_words_skeleton(self):
        """For 2,000 seeded random words of Latin letters and digits, skeleton(disguise(w)) lower-cased equals skeleton(w) lower-cased,
        where disguise swaps letters for look-alikes from confusables.TABLE, adds zero-width and format characters, accents and
        fullwidth forms."""
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        import confusables
        rng = random.Random(C.SEED)
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
