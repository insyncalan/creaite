"""v2.5.1 (#239): property tests of the client export path, part of the split described in test_client_output_properties.py
(v2.5.3 gate: four files, each well under run_tests.py's 900 s --file-timeout on a CI shard): unknown keys, the kind and audience table, internal sections, the post-render check and an edited filed report (P7, P8, P17, P19, P26twice).
The data is fictional; the harness, SIZES and MUTANTS are dev/tests/client_output_props_case.py, the properties
dev/tests/client_output_props.py.

Run: python3 dev/tests/test_client_output_properties_sections.py                 smoke: 50 cases a property, seed 239
     CREAITE_PROPS_FULL=1 python3 dev/tests/test_client_output_properties_sections.py   full: 2000 (fewer where the list says)
     CREAITE_PROPS_MUTANTS=1 ...    also the mutation proofs of this file's properties (each goes red with its guard off)
     PROP_SEED=<n> replays another seed. PDF cases need Chrome.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client_output_props_case as C  # noqa: E402


class Properties(C.Properties):
    PROPS = ("P7", "P8", "P17", "P19", "P26twice")

    def test_P07_unknown_keys_at_any_depth(self): self.check("P7")

    def test_P08_kind_audience_route_source_table(self): self.check("P8")

    def test_P17_internal_sections(self): self.check("P17")

    def test_P19_the_post_render_check_on_its_own(self): self.check("P19")

    def test_P26_an_edited_filed_report_is_held_on_every_export(self):
        """v2.5.3 (#259 round 2, HIGH 1): exports twice (or more, html and docx in any order) of a filed report edited on disk to
        hold a text section marked client: every one holds none of it."""
        self.check("P26twice")

    @unittest.skipUnless(C.MUTANTS_ON, "the mutation proofs run with CREAITE_PROPS_MUTANTS=1")
    def test_mutation_proofs_each_property_goes_red_without_its_guard(self): self.mutation_proofs()


if __name__ == "__main__":
    unittest.main(verbosity=2)
