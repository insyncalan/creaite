# Bundled Python libraries

These are pure-Python copies, so no pip install is needed and creaite runs anywhere Python 3.9 or later is installed. Licences are in `licenses/`, one file per library and version; all are permissive: MIT or BSD, and typing_extensions under the PSF licence (PSF-2.0, accepted for BL-275: permissive, notice kept in `licenses/`).

| Library | Licence | Used by |
|---------|---------|---------|
| openpyxl 3.1.5, plus its dependency et_xmlfile 2.0.0 | MIT (et_xmlfile has parts under PSF-2.0) | `excel_sync.py` (the Excel export and import) |
| jinja2 3.1.6, plus its dependency markupsafe 3.0.3 | BSD-3-Clause | `build_dashboard.py` and the report templates |
| pypdf 6.19.0 (6.20.1, with security fixes, to be taken once it is two weeks old, on or after 26-10-2026; Alan, 14-10-2026) | BSD-3-Clause | `tracker.py`: PDF text for the search index (BL-275). Its optional libraries (cryptography, PyCryptodome, Pillow, brotli) are not bundled: AES-encrypted PDFs and images are skipped |
| typing_extensions 4.15.0, pypdf's dependency (imported only on Python 3.9 and 3.10) | PSF-2.0 | pypdf |

Every script starts with `import paths`. `system/scripts/paths.py` puts this folder first on the import path and defines every other location in the vault.

Upgrade only deliberately: replace a folder, run `python3 dev/tools/vendor_manifest.py` to rebuild `manifest.json`, run `python3 system/scripts/doctor.py`, and commit the library and the manifest together.

`manifest.json` (BL-239) holds the SHA-256 of every file here; doctor's "Bundled libraries match their manifest" check fails on a missing, changed or extra file.
