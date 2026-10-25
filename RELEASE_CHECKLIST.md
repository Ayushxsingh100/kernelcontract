# Pre-publication checklist

Before publishing or announcing this project:

- [x] Check PyPI project endpoints for normalized name `kernelcontract`: Query to `https://pypi.org/pypi/kernelcontract/json` returned HTTP 404 Not Found on 2026-10-25; `/simple/kernelcontract/` returned 404. Note: A 404 status indicates no current published package under this name, but does not guarantee registration rights or trademark clearance.
- [ ] Review name and trademark conflicts; do not imply the working name is legally cleared.
- [x] Create a public GitHub repository at https://github.com/Ayushxsingh100/kernelcontract.
- [x] Run automated test suite on Windows and Linux CI (59 tests passed in Python 3.10, 3.11, 3.12, 3.13 across Ubuntu and Windows).
- [x] Test stale kernelspecs, malformed kernelspecs, and notebooks with missing/malformed kernel metadata.
- [ ] Validate widget warnings against authoritative docs and real supported JupyterLab/ipywidgets version combinations in production setups.
- [x] Review subprocess behavior and ensure non-control kernel executables remain opt-in with bounded timeouts and safe args.
- [x] Verify JSON schema stability and exit-code semantics (exit 0 on pass/info/warn; exit 1 on warn in strict mode; exit 1 on fail).
- [x] Review the MIT license choice and package metadata.
- [x] Build sdist and wheel distributions (`python -m build`), then validate with `python -m twine check --strict dist/*`.
- [x] Install the wheel into a clean virtual environment and verify `--version`, `--help`, `doctor`, and notebook checks.
- [x] Prepare dedicated GitHub Actions Trusted Publishing workflow (`.github/workflows/publish-to-pypi.yml`) with OIDC tokens, release triggers, and environment protection.
- [x] PyPI Pending Publisher: Configured by repository owner under PyPI Account Settings -> Publishing:
  - PyPI Project Name: `kernelcontract`
  - Owner: `Ayushxsingh100`
  - Repository name: `kernelcontract`
  - Workflow name: `publish-to-pypi.yml`
  - Environment name: `pypi`
- [x] Configure GitHub environment `pypi` via GitHub REST API: required reviewer `Ayushxsingh100` (ID: 192797874), self-review permitted (`prevent_self_review: false`), administrator bypass disabled (`can_admins_bypass: false`), and deployment restricted to tag pattern `v*`.
- [x] Publish candidate `0.1.0a2` as a clearly marked GitHub pre-release (https://github.com/Ayushxsingh100/kernelcontract/releases/tag/v0.1.0a2).
- [ ] Prepare candidate `0.1.0a3` for PyPI publication (do not create or push tag `v0.1.0a3` until manual setup is complete).
- [ ] Verify `pip install kernelcontract` in a clean environment after PyPI publication.
- [x] Add documentation and changelog notes explaining known limitations, security implications, and the opt-in `--probe-python` behavior.
