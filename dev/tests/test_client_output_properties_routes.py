"""v2.5.1 (#239): property tests of the client export path, part of the split described in test_client_output_properties.py
(v2.5.3 gate: four files, each well under run_tests.py's 900 s --file-timeout on a CI shard): a racing writer, text forms, hidden rows and stored fields, the filed data block, raw transforms, read-only routes and approve (P11, P16, P16json, P16out, P18, P18facts, P20-P23; P12's placeholder).
The data is fictional; the harness, SIZES and MUTANTS are dev/tests/client_output_props_case.py, the properties
dev/tests/client_output_props.py.

Run: python3 dev/tests/test_client_output_properties_routes.py                 smoke: 50 cases a property, seed 239
     CREAITE_PROPS_FULL=1 python3 dev/tests/test_client_output_properties_routes.py   full: 2000 (fewer where the list says)
     CREAITE_PROPS_MUTANTS=1 ...    also the mutation proofs of this file's properties (each goes red with its guard off)
     PROP_SEED=<n> replays another seed. PDF cases need Chrome.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client_output_props_case as C  # noqa: E402


class Properties(C.Properties):
    PROPS = ("P11", "P16", "P16json", "P16out", "P18", "P18facts", "P20", "P21", "P22", "P23")

    def test_P11_a_writer_racing_the_export(self): self.check("P11")

    @unittest.skip("P12 is the browser tier (asynchronous answers racing in the page): not run by this file")
    def test_P12_answers_for_one_report_never_change_another(self): pass

    def test_P16_every_text_form_is_gated_as_the_plain_one(self): self.check("P16")

    def test_P16_json_escaped_form_is_gated(self):
        """The JSON-escaped form (\\u0061 for a) is read by client_leak.findings since the guarded gate diff (client-output-step1) is in."""
        self.check("P16json")

    def test_P16_output_check_reads_loose_ids_and_separators(self):
        """v2.5.3 (#259): the output check every client file passes reads an ID with its letters or digits spaced, more zeros or
        fewer, and a wording with hyphens, dots or underscores for its spaces, as the plain form."""
        self.check("P16out")

    def test_P18_hidden_rows_items_tags_and_milestones(self): self.check("P18")

    def test_P18_stored_fields_are_derived_and_items_are_the_facts(self):
        """v2.5.3 (#259, K3 / I19): plain words in a stored field no output draws reach no output; a kept item is the facts'."""
        self.check("P18facts")

    def test_P20_the_filed_data_block(self): self.check("P20")

    def test_P21_raw_transforms(self): self.check("P21")

    def test_P22_read_only_routes(self): self.check("P22")

    def test_P23_approve_files_the_export_and_undo_restores(self): self.check("P23")

    @unittest.skipUnless(C.MUTANTS_ON, "the mutation proofs run with CREAITE_PROPS_MUTANTS=1")
    def test_mutation_proofs_each_property_goes_red_without_its_guard(self): self.mutation_proofs()


if __name__ == "__main__":
    unittest.main(verbosity=2)
