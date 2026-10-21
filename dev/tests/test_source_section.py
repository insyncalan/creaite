"""#296: an item's source note names its section "— Actions" (it said "— Action Items" before 2.6.0). Notes already in the tracker
keep the old words (no migration), so an old note and a new one both resolve to the same section and the same file, and a
spec still written in the old words is written in the new."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import drafts  # noqa: E402
import minutes  # noqa: E402
import search  # noqa: E402
import status_checks  # noqa: E402

FILE = "projects/ABC Example Programme/minutes/2026-10-06 Steering.html"
OLD, NEW = f"{FILE} — Action Items", f"{FILE} — Actions"


class SourceSectionTests(unittest.TestCase):
    def test_written_in_the_new_words(self):
        self.assertEqual(minutes.SECTIONS["actions"], "Actions")
        self.assertEqual(minutes.section_name("Action Items"), "Actions")
        self.assertEqual(minutes.section_name("Decisions"), "Decisions")
        self.assertEqual(minutes.source_words(OLD), NEW)
        self.assertEqual(minutes.source_words(NEW), NEW)
        self.assertEqual(minutes.source_words("Email · Subject: SOW"), "Email · Subject: SOW")

    def test_old_and_new_notes_resolve_to_the_same_section(self):
        self.assertEqual(minutes.source_section(OLD), "actions")
        self.assertEqual(minutes.source_section(NEW), "actions")
        self.assertEqual(minutes.source_section(f"{FILE} — Decisions"), "decisions")
        self.assertEqual(minutes.source_section(f"{FILE} — {minutes.RAID_HEADING}"), "raid")
        self.assertIsNone(minutes.source_section(f"{FILE} — Not covered in this meeting"))
        self.assertIsNone(minutes.source_section("Email · Subject: SOW"))

    def test_old_and_new_notes_name_the_same_file_and_meeting(self):
        docx_old, docx_new = OLD.replace(".html", ".docx"), NEW.replace(".html", ".docx")
        self.assertEqual(status_checks.source_path(docx_old), status_checks.source_path(docx_new))
        self.assertTrue(status_checks.source_path(docx_new).endswith("Steering.docx"))
        self.assertEqual(drafts._source_meeting(OLD), drafts._source_meeting(NEW))
        self.assertEqual(drafts._source_meeting(NEW), ("2026-10-06", "Steering"))

    def test_minutes_read_either_actions_heading(self):
        for heading in ("Action Items", "Actions"):
            lines = ["Decisions", "Go ahead", minutes.RAID_HEADING, "Risk: data late", heading, "Owner | Task | Deadline",
                     "Omar Ali | Send the SOW | 16-10-2026", "Open Questions / Escalations", "Who signs?"]
            self.assertEqual(minutes._section(lines, minutes.ACTION_HEADINGS, "Open Questions / Escalations"),
                             ["Owner | Task | Deadline", "Omar Ali | Send the SOW | 16-10-2026"], heading)
            self.assertEqual(minutes._section(lines, minutes.RAID_HEADING, minutes.ACTION_HEADINGS), ["Risk: data late"], heading)

    def test_search_knows_either_heading(self):
        for heading in ("Action Items", "Actions"):
            paras = search.paragraphs(f"Decisions\nGo ahead.\n\n{heading}\nSara to chase the CIO.")
            self.assertIn((heading, "Sara to chase the CIO."), paras, heading)


if __name__ == "__main__":
    unittest.main()
