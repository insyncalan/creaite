"""v2.5.1 (#239): property tests of the client export path, part of the split described in test_client_output_properties.py
(v2.5.3 gate: four files, each well under run_tests.py's 900 s --file-timeout on a CI shard): file names, a posted page, pictures, logos and repeat exports (P9, P10, P13, P13shared, P14, P15, P24; P25's placeholder).
The data is fictional; the harness, SIZES and MUTANTS are dev/tests/client_output_props_case.py, the properties
dev/tests/client_output_props.py.

Run: python3 dev/tests/test_client_output_properties_pictures.py                 smoke: 50 cases a property, seed 239
     CREAITE_PROPS_FULL=1 python3 dev/tests/test_client_output_properties_pictures.py   full: 2000 (fewer where the list says)
     CREAITE_PROPS_MUTANTS=1 ...    also the mutation proofs of this file's properties (each goes red with its guard off)
     PROP_SEED=<n> replays another seed. PDF cases need Chrome.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client_output_props_case as C  # noqa: E402


class Properties(C.Properties):
    PROPS = ("P9", "P10", "P13", "P13shared", "P14", "P15", "P24")

    def test_P09_file_names(self): self.check("P9")

    def test_P10_a_posted_page_is_never_the_source(self): self.check("P10")

    def test_P13_pictures(self): self.check("P13")

    def test_P13_shared_images_store_known_gap_C(self):
        """Known gap C, closed in step 2: a picture added for the internal report is never drawn into a client report (a client
        report's own pictures are `_images/client-<name>`, drawn only as its snapshot's picture table records them)."""
        self.check("P13shared")

    def test_P14_logos(self): self.check("P14")

    @unittest.skipUnless(C.S.HAVE_CHROME, "an SVG logo is drawn by Chrome: P15 needs it")
    def test_P15_uploaded_logos(self): self.check("P15")

    def test_P24_repeat_exports(self): self.check("P24")

    @unittest.skip("P25 is the browser tier: it runs in test_client_output_p25.py (Chrome; v2.5.1 step 3)")
    def test_P25_bulk_match_adds_no_section(self): pass

    @unittest.skipUnless(C.MUTANTS_ON, "the mutation proofs run with CREAITE_PROPS_MUTANTS=1")
    def test_mutation_proofs_each_property_goes_red_without_its_guard(self): self.mutation_proofs()


if __name__ == "__main__":
    unittest.main(verbosity=2)
