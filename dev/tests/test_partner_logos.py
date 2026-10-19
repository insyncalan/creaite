"""#228 part B: a logo for each partner organisation (backend). Naming, validation, backward compatibility, dynamic kinds and the logo routes.

Run: python3 dev/tests/test_partner_logos.py

The partners are the project's CLAUDE.md line `- **Partners:** Org A; Org B`. A partner's logo kind is `partner:<slug>` and its file
`<CODE>-partner-<slug>.<ext>` in system/branding/logos/. The old `<CODE>-partner.<ext>` is still read as the FIRST partner's logo when that
partner has no file of its own (and as "the partner" when there is no Partners line); a bare `partner` in a layout or the memory line means
every partner. Removing a partner from the line never deletes its file.
"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import build_dashboard as bd  # noqa: E402
from test_client_report_setting import JPG, PNG, SVG, b64, folder_with  # noqa: E402
from test_reports import ABC, ReportRoutes  # noqa: E402


class Remote:
    """A module of the throwaway vault's own scripts, called in a subprocess (report_doc reads the vault it lives in, not this repository)."""

    def __init__(self, vault, module):
        self.vault, self.module = vault, module

    def __getattr__(self, name):
        def call(*args):
            code = ("import sys, json; sys.path.insert(0, sys.argv[1]); import %s as m; "
                    "r = getattr(m, sys.argv[2])(*json.loads(sys.argv[3])); print(json.dumps(r, default=str))" % self.module)
            out = subprocess.run([sys.executable, "-c", code, str(self.vault.root / "system/scripts"), name, json.dumps(args)],
                                 capture_output=True, text=True, cwd=str(self.vault.root))
            if out.returncode:
                raise AssertionError(out.stderr)
            return json.loads(out.stdout)
        return call


class Naming(unittest.TestCase):
    """The slug function and the Partners line."""

    def slugs(self, line):
        return [p["slug"] for p in bd.partners_of(f"- **Partners:** {line}\n")]

    def test_a_plain_name_is_lower_case_and_hyphenated(self):
        self.assertEqual(self.slugs("Acme Labs; Beta Works"), ["acme-labs", "beta-works"])

    def test_punctuation_and_unicode_fold_to_letters_and_digits(self):
        self.assertEqual(self.slugs("Müller & Söhne GmbH; Café   Zoë (UK) Ltd.; R&D 3M"),
                         ["muller-sohne-gmbh", "cafe-zoe-uk-ltd", "r-d-3m"])     # #228 C: R&D/3M had a slash, which a name may no longer hold

    def test_a_repeat_or_a_slug_collision_is_left_out_not_renamed(self):      # #228 C: was numbered -2, -3; "acme!" has a name character that is refused
        self.assertEqual(self.slugs("Acme; ACME; acme!; Beta"), ["acme", "beta"])
        self.assertEqual(self.slugs("Acme; A.C.M.E; Café; Cafe"), ["acme", "cafe"])

    def test_a_name_with_no_letters_gets_a_stable_code_not_an_empty_slug(self):
        a, b = self.slugs("日本語; 中文")
        self.assertTrue(re.fullmatch(r"x[0-9a-f]{6}", a) and a != b)
        self.assertEqual(self.slugs("日本語")[0], a, "stable: the same name, the same slug")

    def test_a_slug_is_at_most_40_characters(self):
        s = self.slugs("A" * 60)[0]
        self.assertEqual(len(s), 40)
        self.assertEqual(self.slugs("A" * 61), [], "a name over 60 characters is left out")
        self.assertEqual(self.slugs("B" * 45 + "1; " + "B" * 45 + "2"), ["b" * 40], "the same 40 characters: the second is left out, not renamed")

    def test_a_name_can_not_collide_with_another_partners_original_file(self):
        s = self.slugs("Acme; Acme Original; Original")
        self.assertTrue(all(not re.search(r"(^|-)original$", x) for x in s), s)
        self.assertEqual(len(set(s)), 3)

    def test_empty_items_and_extra_space_are_dropped_and_the_line_is_capped(self):
        self.assertEqual([p["name"] for p in bd.partners_of("- **Partners:**  Acme   Labs ;; ; Beta \n")], ["Acme Labs", "Beta"])
        self.assertEqual(bd.partners_of("- **Partners:** \n"), [])
        self.assertEqual(bd.partners_of("nothing here"), [])
        self.assertEqual(len(bd.partners_of("- **Partners:** " + "; ".join(f"P{i}" for i in range(40)))), bd.PARTNERS_MAX)

    def test_a_line_shown_as_an_example_is_not_the_setting(self):
        self.assertEqual(bd.partners_of("> - **Partners:** Quoted\n```\n- **Partners:** Fenced\n```\n"), [])


class Setting(unittest.TestCase):
    """client_report_setting: the logos kinds follow the Partners line."""

    def setting(self, extra):
        return bd.memory(folder_with(extra))

    def test_no_partners_line_is_the_three_old_kinds(self):
        m = self.setting("")
        self.assertEqual((m["logos"], m["partners"]), (["firm", "client", "partner"], []))

    def test_every_partner_is_ticked_when_there_is_no_logos_line(self):
        m = self.setting("- **Partners:** Acme Labs; Beta Works")
        self.assertEqual(m["logos"], ["firm", "client", "partner:acme-labs", "partner:beta-works"])
        self.assertEqual(m["partners"], [{"name": "Acme Labs", "slug": "acme-labs"}, {"name": "Beta Works", "slug": "beta-works"}])

    def test_a_bare_partner_means_all_partners(self):
        m = self.setting("- **Partners:** Acme Labs; Beta Works\n- **Client report logos:** firm, partner")
        self.assertEqual(m["logos"], ["firm", "partner:acme-labs", "partner:beta-works"])

    def test_a_chosen_partner_only(self):
        m = self.setting("- **Partners:** Acme Labs; Beta Works\n- **Client report logos:** firm, client, partner:beta-works")
        self.assertEqual(m["logos"], ["firm", "client", "partner:beta-works"])

    def test_a_slug_not_in_the_line_is_dropped_and_order_is_the_lines(self):
        m = self.setting("- **Partners:** Acme Labs; Beta Works\n- **Client report logos:** partner:gone, partner:beta-works, partner:acme-labs, client")
        self.assertEqual(m["logos"], ["firm", "client", "partner:acme-labs", "partner:beta-works"])

    def test_a_slug_with_no_partners_line_is_dropped(self):
        self.assertEqual(self.setting("- **Client report logos:** firm, partner:acme")["logos"], ["firm"])


class Kinds(unittest.TestCase):
    """report_doc: the dynamic kinds, the layout, the files (a throwaway vault)."""
    setUpClass = classmethod(ReportRoutes.setUpClass.__func__)
    tearDownClass = classmethod(ReportRoutes.tearDownClass.__func__)

    def setUp(self):
        self.report_doc, self.client_check = Remote(self.v, "report_doc"), Remote(self.v, "client_check")
        self.d = self.v.root / "system/branding/logos"
        self.d.mkdir(parents=True, exist_ok=True)
        for f in self.d.glob("*"):
            f.unlink()
        self.mem = self.v.root / ABC / "CLAUDE.md"
        self.text0 = re.sub(r"- \*\*(Partners|Client report logos):\*\*[^\n]*\n", "", self.mem.read_text())
        self.partners("")

    def partners(self, line, logos=None):
        text = self.text0 + (f"- **Partners:** {line}\n" if line else "") + (f"- **Client report logos:** {logos}\n" if logos else "")
        self.mem.write_text(text)

    def put(self, name, data=PNG):
        (self.d / name).write_bytes(data)

    def kinds(self, wanted=None):
        return [x["kind"] for x in (self.report_doc.logos("ABC") if wanted is None else self.report_doc.logos("ABC", wanted))]

    def test_kinds_come_from_the_partners_line(self):
        self.assertEqual(self.report_doc.logo_kinds("ABC"), ["firm", "client", "partner"])
        self.partners("Acme Labs; Beta Works")
        self.assertEqual(self.report_doc.logo_kinds("ABC"), ["firm", "client", "partner:acme-labs", "partner:beta-works"])

    def test_file_naming(self):
        self.partners("Acme Labs; Beta Works")
        self.put("ABC-partner-beta-works.png")
        self.assertEqual(Path(self.report_doc.logo_file("ABC", "partner:beta-works")).name, "ABC-partner-beta-works.png")
        self.assertIsNone(self.report_doc.logo_file("ABC", "partner:acme-labs"))

    def test_the_old_partner_file_is_the_first_partners_logo_only(self):
        self.put("ABC-partner.png")
        self.partners("Acme Labs; Beta Works")
        self.assertEqual(self.kinds(), ["partner:acme-labs"])
        self.assertEqual(Path(self.report_doc.logo_file("ABC", "partner:acme-labs")).name, "ABC-partner.png")
        self.assertIsNone(self.report_doc.logo_file("ABC", "partner:beta-works"))

    def test_a_partner_file_of_its_own_beats_the_old_file(self):
        self.put("ABC-partner.png")
        self.put("ABC-partner-acme-labs.svg", SVG)
        self.partners("Acme Labs")
        self.assertEqual([Path(x["path"]).name for x in self.report_doc.logos("ABC")], ["ABC-partner-acme-labs.svg"])

    def test_with_no_partners_line_the_old_file_is_the_partner(self):
        self.put("ABC-partner.png")
        self.assertEqual(self.kinds(), ["partner"])

    def test_order_is_firm_client_then_partners_in_line_order(self):
        self.partners("Beta Works; Acme Labs")
        for n in ("firm.png", "ABC-client.png", "ABC-partner-acme-labs.png", "ABC-partner-beta-works.png"):
            self.put(n)
        self.assertEqual(self.kinds(), ["firm", "client", "partner:beta-works", "partner:acme-labs"])

    def test_wanted_accepts_the_slug_form_and_a_bare_partner_is_all(self):
        self.partners("Acme Labs; Beta Works")
        for n in ("ABC-partner-acme-labs.png", "ABC-partner-beta-works.png"):
            self.put(n)
        self.assertEqual(self.kinds(["partner:beta-works"]), ["partner:beta-works"])
        self.assertEqual(self.kinds(["partner"]), ["partner:acme-labs", "partner:beta-works"])
        self.assertEqual(self.kinds(["client"]), [])

    def test_a_removed_partners_file_stays_but_is_not_drawn(self):
        self.partners("Acme Labs; Beta Works")
        self.put("ABC-partner-beta-works.png")
        self.partners("Acme Labs")
        self.assertEqual(self.kinds(), [])
        self.assertTrue((self.d / "ABC-partner-beta-works.png").is_file())

    def test_layout_validation_keeps_slugs_and_drops_nonsense(self):
        lay = self.report_doc.normal_layout("weekly", {"logos": ["firm", "partner:acme-labs", "partner:Bad Slug", "partner:", "../x", "partner:acme-labs"]})
        self.assertEqual(lay["logos"], ["firm", "partner:acme-labs"])
        self.assertEqual(self.report_doc.normal_layout("weekly", {"logos": ["partner", "client", "firm"]})["logos"], ["firm", "client", "partner"])

    def test_layout_for_resolves_against_the_project(self):
        self.partners("Acme Labs; Beta Works")
        self.assertEqual(self.report_doc.layout_for("ABC", "weekly")["logos"], ["firm", "client", "partner:acme-labs", "partner:beta-works"])
        self.partners("Acme Labs; Beta Works", "firm, partner:beta-works")
        self.assertEqual(self.report_doc.layout_for("ABC", "weekly")["logos"], ["firm", "partner:beta-works"])

    def test_unticked_logos_lists_a_partner_left_out(self):
        self.partners("Acme Labs; Beta Works")
        for n in ("ABC-partner-acme-labs.png", "ABC-partner-beta-works.png", "ABC-client.png"):
            self.put(n)
        doc = {"project": "ABC", "layout": {"logos": ["firm", "client", "partner:acme-labs"]}}
        self.assertEqual(self.client_check._unticked_logos(doc), ["partner Beta Works"])
        self.assertEqual(self.client_check._unticked_logos({"project": "ABC", "layout": {"logos": ["firm", "partner"]}}), ["client"])
        self.assertEqual(self.client_check._unticked_logos({"project": "ABC", "layout": {}}), [])

    def test_unticked_logos_old_shape_is_unchanged(self):
        self.put("ABC-partner.png")
        self.put("ABC-client.png")
        self.assertEqual(self.client_check._unticked_logos({"project": "ABC", "layout": {"logos": ["firm", "client"]}}), ["partner"])


class Routes(unittest.TestCase):
    """The logo routes with the slug form (a live server in a throwaway vault)."""
    setUpClass = classmethod(ReportRoutes.setUpClass.__func__)
    tearDownClass = classmethod(ReportRoutes.tearDownClass.__func__)
    post = ReportRoutes.post

    def setUp(self):
        self.d = self.v.root / "system/branding/logos"
        self.d.mkdir(parents=True, exist_ok=True)
        for f in self.d.glob("*"):
            f.unlink()
        self.mem = self.v.root / ABC / "CLAUDE.md"
        self.text0 = re.sub(r"- \*\*(Partners|Client report logos):\*\*[^\n]*\n", "", self.mem.read_text())
        self.partners("Acme Labs; Beta Works")

    def partners(self, line):
        self.mem.write_text(self.text0 + (f"- **Partners:** {line}\n" if line else ""))

    def save(self, kind, ext="png", original=PNG, drawn=None):
        return self.post("/api/report/logo/save", {"code": "ABC", "kind": kind, "ext": ext, "original": b64(original),
                                                   **({"drawn": b64(drawn)} if drawn else {})})

    def remove(self, kind):
        return self.post("/api/report/logo/remove", {"code": "ABC", "kind": kind})

    def files(self):
        return sorted(f.name for f in self.d.glob("*"))

    def test_save_a_partner_logo_under_its_slug(self):
        r = self.save("partner:beta-works")
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.files(), ["ABC-partner-beta-works.png"])
        self.assertEqual([x["kind"] for x in r["logos"]], ["partner:beta-works"])

    def test_two_partners_two_files_and_the_read_route_lists_both_in_line_order(self):
        self.save("partner:beta-works")
        self.save("partner:acme-labs", "svg", SVG)
        got = self.post("/api/report/logo", {"code": "ABC"})
        self.assertEqual([x["kind"] for x in got["list"]], ["partner:acme-labs", "partner:beta-works"])
        self.assertEqual(len(got["logos"]), 2)
        self.assertEqual([p["slug"] for p in got["partners"]], ["acme-labs", "beta-works"])

    def test_the_trimmed_copy_and_original_pair_up_per_partner(self):
        self.assertTrue(self.save("partner:acme-labs", "jpg", JPG, drawn=PNG)["ok"])
        self.assertEqual(self.files(), ["ABC-partner-acme-labs-original.jpg", "ABC-partner-acme-labs.png"])
        self.assertTrue(self.save("partner:beta-works", "jpg", JPG, drawn=PNG)["ok"])
        self.assertTrue(self.remove("partner:acme-labs")["ok"])
        self.assertEqual(self.files(), ["ABC-partner-beta-works-original.jpg", "ABC-partner-beta-works.png"], "only that partner's files go")

    def test_a_slug_not_in_the_line_is_refused_in_plain_words(self):
        for kind in ("partner:gone", "partner:../x", "partner:", "partner:ACME-LABS"):
            r = self.save(kind)
            self.assertFalse(r["ok"], kind)
            self.assertEqual(self.files(), [])
        r = self.save("partner:gone")
        self.assertIn("Partners", r["message"])
        self.assertNotIn(str(self.v.root), r["message"])
        self.assertFalse(self.remove("partner:gone")["ok"])

    def test_the_bare_kind_is_refused_when_partners_are_listed_and_a_slug_when_there_are_none(self):
        r = self.save("partner")
        self.assertFalse(r["ok"])
        self.assertIn("Acme Labs", r["message"])
        self.partners("")
        r = self.save("partner:acme-labs")
        self.assertFalse(r["ok"])
        self.assertIn("Partners", r["message"])
        self.assertTrue(self.save("partner")["ok"], "no Partners line: the old single partner still works")
        self.assertEqual(self.files(), ["ABC-partner.png"])

    def test_changing_the_first_partner_replaces_the_old_file(self):
        (self.d / "ABC-partner.png").write_bytes(PNG)
        self.assertTrue(self.save("partner:acme-labs", "svg", SVG)["ok"])
        self.assertEqual(self.files(), ["ABC-partner-acme-labs.svg"], "the old file is replaced, so Remove can not bring it back")
        self.assertTrue(self.remove("partner:acme-labs")["ok"])
        self.assertEqual(self.files(), [])

    def test_removing_the_first_partners_logo_removes_the_old_file_it_stood_for(self):
        (self.d / "ABC-partner.png").write_bytes(PNG)
        self.assertEqual([x["kind"] for x in self.post("/api/report/logo", {"code": "ABC"})["list"]], ["partner:acme-labs"])
        self.assertTrue(self.remove("partner:acme-labs")["ok"])
        self.assertEqual(self.files(), [])

    def test_the_old_file_is_not_the_second_partners(self):
        (self.d / "ABC-partner.png").write_bytes(PNG)
        self.assertTrue(self.save("partner:beta-works")["ok"])
        self.assertEqual(self.files(), ["ABC-partner-beta-works.png", "ABC-partner.png"])
        self.assertTrue(self.remove("partner:beta-works")["ok"])
        self.assertEqual(self.files(), ["ABC-partner.png"])

    def test_removing_a_partner_from_the_line_deletes_no_file(self):
        self.save("partner:beta-works")
        self.partners("Acme Labs")
        self.assertEqual(self.files(), ["ABC-partner-beta-works.png"])
        self.assertEqual([x["kind"] for x in self.post("/api/report/logo", {"code": "ABC"})["list"]], [])

    def test_a_partner_named_original_is_kept_apart_from_anothers_original(self):
        self.partners("Acme; Acme Original")
        self.assertTrue(self.save("partner:acme", "jpg", JPG, drawn=PNG)["ok"])
        slug = bd.partners_of("- **Partners:** Acme; Acme Original")[1]["slug"]
        self.assertTrue(self.save("partner:" + slug)["ok"])
        self.assertTrue(self.remove("partner:" + slug)["ok"])
        self.assertEqual(self.files(), ["ABC-partner-acme-original.jpg", "ABC-partner-acme.png"])

    def test_the_draft_header_carries_every_ticked_partner_logo_in_line_order(self):
        self.partners("Beta Works; Acme Labs")
        self.save("partner:acme-labs")
        self.save("partner:beta-works")
        r = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        self.assertEqual([x["kind"] for x in r["logos"]], ["partner:beta-works", "partner:acme-labs"])
        hdr = [s for s in r["doc"]["sections"] if s["id"] == "header"][0]
        self.assertEqual([Path(x["path"]).name for x in hdr["data"]["logos"]], ["ABC-partner-beta-works.png", "ABC-partner-acme-labs.png"])


if __name__ == "__main__":
    unittest.main()
