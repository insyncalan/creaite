"""#375 E1, S1: mutation checks for `system/scripts/invite_filter.py`.

Run: python3 dev/tests/test_invite_filter_mutants.py      (quick tier: plain code)

Each mutant is a copy of the module with one thing broken (MUTANT-A to H in test_invite_filter_spec.py, L1 to L8 in
test_invite_filter_labels_spec.py). The named spec classes are run against the copy and at least one test must fail. L9 (an
edit of the kept lines) cannot be written against an index API and is covered by MUTANT-G on keep_lines. The sanity test
runs the same classes on the unbroken copy: they must pass, so a "red" mutant means the mutant, not the harness.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE))
import test_invite_filter_labels_spec as LAB    # noqa: E402
import test_invite_filter_props as PROPS        # noqa: E402
import test_invite_filter_spec as SPEC          # noqa: E402


def fresh():
    """A private copy of invite_filter (its own globals), so a mutant never leaks into the real module."""
    spec = importlib.util.spec_from_file_location("invite_filter_mutant", SCRIPTS / "invite_filter.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def failures(mutant, targets):
    """Run the named classes ((module, class name), ...) with the mutant as `F`; return how many tests failed or errored."""
    suite = unittest.TestSuite()
    old = (SPEC.F, LAB.F, PROPS.F)
    SPEC.F = LAB.F = PROPS.F = mutant
    try:
        for mod, name in targets:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(getattr(mod, name)))
        res = unittest.TestResult()
        suite.run(res)
    finally:
        SPEC.F, LAB.F, PROPS.F = old
    return len(res.failures) + len(res.errors)


# --- label-layer mutants written out in full (they replace drop_labelled_values)

def labels_original_neighbours(m):
    """L8: a label's successor is the next non-blank line of the ORIGINAL list, not of what is left."""
    def fn(lines):
        n = len(lines)
        skel = [m._skeleton(x) for x in lines]
        dead = set()
        for i, s in enumerate(skel):
            if s and m._same_line(s):
                dead.add(i)
        for i, s in enumerate(skel):
            if s and i not in dead and m._ends_with_label(s):
                j = i + 1
                while j < n and not skel[j]:
                    j += 1
                if j < n and j not in dead and m._is_value_token(m._first_token(skel[j])):
                    dead.update((i, j))
        return [i for i in range(n) if i not in dead]
    return fn


def labels_two_lines(m, real):
    """L5: a label takes the next TWO non-blank lines when they are value-shaped."""
    def fn(lines):
        keep = real(lines)
        gone = set(range(len(lines))) - set(keep)
        for i in sorted(gone):
            if not lines[i].strip() or not m._ends_with_label(m._skeleton(lines[i])):
                continue
            seen = 0
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    seen += 1
                    if seen == 2 and m._is_value_token(m._first_token(m._skeleton(lines[j]))):
                        gone.add(j)
                    if seen == 2:
                        break
        return [i for i in range(len(lines)) if i not in gone]
    return fn


def labels_soft_window(m, real):
    """L6: 'Joining details' drops the next three non-blank lines."""
    def fn(lines):
        keep = set(real(lines))
        for i, ln in enumerate(lines):
            if m._skeleton(ln).startswith(("joining details", "security notes", "login information", "credentials", "dial-in details")):
                for j in range(i + 1, min(len(lines), i + 4)):
                    keep.discard(j)
        return sorted(keep)
    return fn


class Mutants(unittest.TestCase):
    def check(self, name, mutate, *targets):
        m = fresh()
        mutate(m)
        n = failures(m, targets)
        self.assertGreater(n, 0, f"{name}: no test turned red")

    def test_sanity_the_unbroken_copy_is_green(self):
        every = [(SPEC, c) for c in ("Subset", "Anchors", "UnicodeDigits", "Blocks", "Regions", "LabelBlind", "Cap", "Corpus")]
        every += [(LAB, c) for c in ("Positives", "NextLine", "Negatives", "Idempotent")]
        self.assertEqual(failures(fresh(), every), 0)

    def test_a_anchors_off(self):
        self.check("A", lambda m: setattr(m, "_has_anchor", lambda s: False), (SPEC, "Anchors"), (SPEC, "Corpus"))

    def test_b_only_the_anchor_line(self):
        self.check("B", lambda m: setattr(m, "_WHOLE_BLOCK", False), (SPEC, "Blocks"), (SPEC, "Corpus"))

    def test_c_regions_off(self):
        self.check("C", lambda m: setattr(m, "_USE_REGIONS", False), (SPEC, "Regions"), (SPEC, "Corpus"))

    def test_d_a_label_word_is_needed(self):
        def mutate(m):
            real = m._has_anchor
            m._has_anchor = lambda s: real(s) and any(w in s for w in ("passcode", "meeting id", "password", "pin", "access code"))
        self.check("D", mutate, (SPEC, "LabelBlind"))

    def test_e_raw_digits(self):
        def mutate(m):
            m._skeleton = lambda line: line.lower()
        self.check("E", mutate, (SPEC, "UnicodeDigits"))

    def test_f_cap_cuts_mid_line(self):
        self.check("F", lambda m: setattr(m, "_capped", lambda lines: "\n".join(lines)[:m.CAP].split("\n")), (SPEC, "Cap"))

    def test_g_output_rewritten(self):
        def mutate(m):
            real = m.keep_lines
            m.keep_lines = lambda lines, **kw: [x.strip() for x in real(lines, **kw)]
        self.check("G", mutate, (SPEC, "Subset"), (SPEC, "Generated"))

    def test_h_second_layer_ignored(self):
        def mutate(m):
            real = m.keep_indices
            m.keep_indices = lambda lines, *, second_layer=True: real(lines, second_layer=True)
        self.check("H", mutate, (SPEC, "LabelBlind"))

    def test_l1_rule_off(self):
        self.check("L1", lambda m: setattr(m, "drop_labelled_values", lambda lines: list(range(len(lines)))), (LAB, "Positives"), (LAB, "NextLine"))

    def test_l2_any_word_is_a_value(self):
        self.check("L2", lambda m: setattr(m, "_is_value_token", lambda tok: bool(tok)), (LAB, "Negatives"))

    def test_l3_label_inside_a_word(self):
        def mutate(m):
            m._label_ends_at = lambda s, j: any(s[:j].endswith(lab) for lab in m._LABELS)
        self.check("L3", mutate, (PROPS, "Decisions"))   # the spec's near misses never END in a label: see the report

    def test_l4_short_labels_added(self):
        self.check("L4", lambda m: setattr(m, "_LABELS", m._LABELS + ("code", "key", "id")), (PROPS, "Decisions"))   # likewise the spec's near misses carry no separator after code/key/id

    def test_l5_two_lines_dropped(self):
        def mutate(m):
            m.drop_labelled_values = labels_two_lines(m, m.drop_labelled_values)
        self.check("L5", mutate, (LAB, "NextLine"))

    def test_l6_soft_heading_window(self):
        def mutate(m):
            m.drop_labelled_values = labels_soft_window(m, m.drop_labelled_values)
        self.check("L6", mutate, (LAB, "Negatives"))

    def test_l7_dates_and_times_are_values(self):
        self.check("L7", lambda m: setattr(m, "_is_datetime_token", lambda tok: False), (LAB, "Negatives"))

    def test_l8_successor_on_the_original_neighbours(self):
        def mutate(m):
            m.drop_labelled_values = labels_original_neighbours(m)
        self.check("L8", mutate, (LAB, "Idempotent"))

    def test_extra_dates_not_set_aside(self):
        """A date is a digit run too if the date shape is not matched first (decision 2)."""
        def mutate(m):
            m._DATE = type("R", (), {"sub": staticmethod(lambda f, s: s)})
        m = fresh()
        mutate(m)
        self.assertEqual(m.keep_lines(["2026-11-12 14:00 to 15:30"]), [])               # the mutant loses a date line
        self.assertEqual(fresh().keep_lines(["2026-11-12 14:00 to 15:30"]), ["2026-11-12 14:00 to 15:30"])


if __name__ == "__main__":
    unittest.main()
