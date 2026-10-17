"""#175: what Notes' undo steps (core/undoSteps.js) depend on in the vendored prosemirror-history, checked cheaply (no browser).

Run: python3 dev/tests/test_notes_undo_shape.py

Two things rest on the history's internals, and a Tiptap upgrade must fail here, loudly, before it fails only in Chrome:
  - the slash menu's deletion and its row's insert are one step because the insert carries the composition id the history already holds
    (`prevComposition`): the history groups a change with the one before it when the ids are equal, whatever the time and adjacency;
  - the stash of a closed note's history reads and rebuilds the history plugin's state (found by its key "history$…", HistoryState's
    five fields, the Branch's `items` and `eventCount`).
Read from the committed vendor bundle (system/templates/vendor/tiptap/tiptap.module.js); the names are minified, so the shapes are matched
by regular expressions that ignore them. test_notes_undo_browser then runs the same facts in the real editor.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = (REPO / "system" / "templates" / "vendor" / "tiptap" / "tiptap.module.js").read_text(encoding="utf-8")
UNDO = (REPO / "system" / "templates" / "dashboard" / "src" / "core" / "undoSteps.js").read_text(encoding="utf-8")
V = r"[\w$]+"


class HistoryShape(unittest.TestCase):
    def found(self, pattern, what):
        self.assertTrue(re.search(pattern, SRC), f"the vendored prosemirror-history no longer has: {what} ({pattern})")

    def test_the_history_plugin_key_is_history(self):
        self.found(rf'=new {V}\("history"\)', "the history plugin's key is PluginKey('history') (its string is 'history$…')")
        self.assertIn("/^history\\$/", UNDO, "undoSteps.js finds the plugin by that key")

    def test_history_state_has_the_five_fields_in_order(self):
        self.found(r"this\.done=\w+,this\.undone=\w+,this\.prevRanges=\w+,this\.prevTime=\w+,this\.prevComposition=\w+\}", 'shape')

    def test_equal_composition_ids_beat_time_and_adjacency(self):
        # newGroup = prevTime == 0 || (!appended && prevComposition != composition && (too late || not adjacent))
        self.found(rf'getMeta\("composition"\),{V}={V}\.prevTime==0\|\|!{V}&&{V}\.prevComposition!={V}&&\({V}\.prevTime<\({V}\.time\|\|0\)-{V}\.newGroupDelay\|\|!{V}\(', 'shape')

    def test_a_change_with_no_composition_id_keeps_the_previous_one(self):
        self.found(rf"{V}\?\?{V}\.prevComposition\)", "a change with no composition id keeps the previous one")

    def test_close_history_resets_the_composition_to_minus_one(self):
        self.found(rf"getMeta\({V}\)&&\(({V})=new {V}\(\1\.done,\1\.undone,null,0,-1\)\)", 'shape')
        self.found(rf"new {V}\({V}\.empty,{V}\.empty,null,0,-1\)", "a new history starts with prevComposition -1")

    def test_a_branch_has_items_and_an_event_count(self):
        self.found(r"this\.items=\w+,this\.eventCount=\w+\}", 'shape')

    def test_the_bundle_exports_close_history(self):
        self.found(r"closeHistory", 'shape')


if __name__ == "__main__":
    unittest.main()
