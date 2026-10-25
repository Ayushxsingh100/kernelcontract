# Pre-publication checklist

Before publishing or announcing this project:

- [x] Check PyPI project endpoint for normalized name `kernelcontract`: Query to `https://pypi.org/pypi/kernelcontract/json` returned HTTP 404 Not Found on 2026-10-25. Note: A 404 status indicates no current published package under this name, but does not guarantee registration permission or trademark clearance.
- [ ] Review name and trademark conflicts; do not imply the working name is legally cleared.
- [ ] Create a public GitHub repository and configure the repository URL in project metadata and README.
- [x] Run automated test suite on Windows (52 tests passed in Python 3.12); CI configured for multi-version Linux.
- [x] Test stale kernelspecs, malformed kernelspecs, and notebooks with missing/malformed kernel metadata.
- [ ] Validate widget warnings against authoritative docs and real supported JupyterLab/ipywidgets version combinations in production setups.
- [x] Review subprocess behavior and ensure non-control kernel executables remain opt-in with bounded timeouts and safe args.
- [x] Verify JSON schema stability and exit-code semantics (exit 0 on pass/info/warn; exit 1 on warn in strict mode; exit 1 on fail).
- [x] Review the MIT license choice and package metadata.
- [x] Build a clean wheel, then install and test the wheel in a clean virtual environment.
- [ ] Configure PyPI Trusted Publishing only after the repository and release workflow are ready.
- [ ] Publish as `0.1.0a1` or another clearly marked pre-release first; do not claim stable status prematurely.
- [ ] Verify `pip install kernelcontract` in a clean environment after publication.
- [x] Add documentation and changelog notes explaining known limitations and the opt-in `--probe-python` behavior.
