# v1.9.3: BL-275, readable PDFs in search (pypdf)

Branch `sprint-search-pdf-eml` (built earlier by Team 2, parked), brought up to date with `origin/release-191` and finished for v1.9.3 (Alan, 14-10-2026).

## Version taken

- **pypdf 6.19.0** (BSD-3-Clause), as built on the branch: **Alan's decision, 14-10-2026**, keeping his rule that a library version is taken only once it is two weeks old (DECISIONS-FOR-ALAN item 36). Pure Python, `Requires-Python >=3.9`; its optional libraries (cryptography, PyCryptodome, Pillow, brotli) are not bundled, so AES-encrypted PDFs and images are skipped.
- **To do: pypdf 6.20.1** (security fixes: limits on how much work one PDF can cause; cyclic page trees) is to be taken once it is two weeks old, **on or after 26-10-2026**: replace `vendor/pypdf/` and its licence file, rebuild `manifest.json`, and change the version in the README and in `test_search_pdf.py` and `test_update.py`. 6.20.1 was tried on this branch first (commit 37cf5df): every test passed on it, and its licence text is the same as 6.19.0's.
- **typing_extensions 4.15.0** stays. pypdf (6.19.0 and 6.20.1 alike) imports it on Python 3.9 and 3.10 (`Self`, `TypeAlias`, `TypeGuard`, outside `TYPE_CHECKING`), so it can't be dropped while creaite supports 3.9. Checked: on the system Python 3.9.6, `pypdf` and `typing_extensions` load from `system/scripts/vendor/` and `test_search_pdf.py` passes.

## Licences

- `system/scripts/vendor/licenses/pypdf-6.19.0-LICENSE.txt` and `typing_extensions-4.15.0-LICENSE.txt` (PSF-2.0).
- **typing_extensions' PSF licence, settled:** recorded the way the bundled libraries are recorded (there is no other licence list): its own file in `licenses/`, and the vendor README's table now has a **Licence** column for every library (openpyxl and et_xmlfile MIT, et_xmlfile with parts under PSF-2.0, which was already the case; jinja2 and markupsafe BSD-3-Clause; pypdf BSD-3-Clause; typing_extensions PSF-2.0). The README's opening line says all are permissive: MIT or BSD, and PSF-2.0 for typing_extensions. `manifest.json` holds hashes only and was rebuilt (`dev/tools/vendor_manifest.py`, 292 files; `--check` passes).

## What was reconciled with release-191

- **BL-276 (.eml) shipped in v1.9.0** as `sprint-search-eml` (`8390afd`). release-191's `eml_text`, `log_path` and `dev/tests/test_search_eml.py` are kept; this branch's identical copy of `eml_text`/`log_path` and its email tests are removed. `tracker.py` now has a BL-275 block (`mostly_letters`, `pdf_text` with pypdf, `pdf_text_stdlib` fallback) and release-191's BL-276 block.
- **`INDEX_READERS` is 3** (BL-276 made it 2 in v1.9.0), so a vault on 1.9.0 to 1.9.2 rebuilds its index once and reads its PDFs with pypdf. `test_search_eml.py`'s stamp check now reads the value from `tracker` instead of a fixed 2.
- **Tests:** `dev/tests/test_search_pdf_eml.py` renamed `test_search_pdf.py`, PDF and vendor tests only. Added: a scanned (image-only) PDF is indexed by name with no error; a long PDF is cut at the limit and its later pages are never read; an online-only PDF is never read. `test_update.py` checks the release zip carries pypdf, typing_extensions, their licences and the vendor manifest.
- **Release notes:** the branch's line in `dev/release-notes/1.9.0.md` is gone (release-191's 1.9.0 notes kept). The 1.9.3 notes live on `dev-release-notes-19x`; suggested line for them:
  > **Search reads PDFs** (BL-275): PDFs exported from Word or PowerPoint, which search found by name only, are read with the bundled pypdf 6.19.0 (with typing_extensions 4.15.0 on Python 3.9 and 3.10). A scanned, password-protected or damaged PDF is still found by its name, with a debug line giving only its path. The search index is rebuilt once to read existing PDFs.
- `help.md`: the branch's single "What it reads" line (Office files, transcripts, text, PDFs and .eml) replaces release-191's separate "Saved emails" line.
- doctor's bundled-libraries import check includes `pypdf` (from the branch).

## Behaviour checked

- A text PDF (Word-style ToUnicode fonts, compressed and uncompressed) is found by a word from its body.
- A scanned or image-only PDF gives "" and is found by its name.
- An encrypted, truncated or junk PDF gives "", a debug line with its path only, and never stops the build; pypdf's warnings never reach the terminal.
- Large PDFs: the existing `limit` (400,000 characters) applies, and pages after it are not read.
- Online-only OneDrive files are left out by `paths.project_files` before `text_of` is called.
- Without pypdf, the standard-library reader is used.
