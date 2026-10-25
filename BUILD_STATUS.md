# Build status — 0.1.0a3 alpha (candidate)

## Implemented

- CLI commands: `kernelcontract doctor` and `kernelcontract notebook PATH`.
- Human-readable and versioned JSON reports.
- Stable check identifiers and `PASS` / `INFO` / `WARN` / `FAIL` statuses.
- Default non-zero exit on failures; `--strict` also fails on warnings.
- Jupyter kernelspec discovery using `jupyter kernelspec list --json`.
- Read-only validation that each kernelspec has a resolvable executable.
- Hardened cross-platform executable resolution: normalized path separators and explicit Windows `PATHEXT` (`.COM`, `.EXE`, `.BAT`, `.CMD`) checking across Python 3.10–3.13.
- Symlink tolerance for canonical interpreter path resolution on Linux/Ubuntu.
- Structured validation of JSON root structures and `kernelspecs` objects in discovery.
- Current/control interpreter probe and optional explicit `--server-python` probe.
- Safe default for probing: separate Python kernel executables are not executed without `--probe-python`.
- Python `ipykernel` check when a kernel is probed.
- Server/control-vs-kernel environment drift messages with limitations explained.
- Narrow check for presence of `jupyterlab_widgets` when the control environment contains JupyterLab and a probed kernel has `ipywidgets`.
- Notebook metadata check for missing/unavailable kernels and changed display names.
- Modernized GitHub Actions CI workflow using `actions/checkout@v7` and `actions/setup-python@v7` targeting Node.js 24 runners.
- Dedicated GitHub Actions PyPI Trusted Publishing workflow (`.github/workflows/publish-to-pypi.yml`) using OIDC authentication, release triggers, and environment protection.
- Tests, packaging metadata, MIT license, contributor/security notes, and multi-OS CI.

## Validation completed in the build and CI environments

- `python -m unittest discover -s tests -v`: **59 tests passed** (including discovery, diagnostics, edge cases, malformed JSON, and CLI suites).
- `python -m pytest -q`: **59 passed**.
- `python -m compileall -q src tests`: clean syntax compilation.
- `kernelcontract --version`: verified (`0.1.0a3`).
- `kernelcontract doctor` & `kernelcontract notebook <sample .ipynb> --json`: verified against fixture notebooks and clean test reports.
- Sdist and wheel built successfully (`python -m build`) and validated with `python -m twine check --strict dist/*`.
- Wheel installed into clean virtual environment; CLI `--help`, `doctor`, and `notebook` verified inside isolated virtual environments.
- Windows execution verified: PATHEXT resolution without `.exe`, quoted executable paths, console output encoding safety, and subprocess decode safety.
- Public GitHub repository live at `https://github.com/Ayushxsingh100/kernelcontract`.
- Remote GitHub Actions CI verified: all 8 matrix jobs passed across Ubuntu and Windows on Python 3.10, 3.11, 3.12, and 3.13.
- Git installation verified: `pip install "git+https://github.com/Ayushxsingh100/kernelcontract.git@v0.1.0a2"`.
- PyPI endpoints audited (`/pypi/kernelcontract/json` returned 404).

## Not yet done (manual account & publication blockers)

- Tag `v0.1.0a2` is published on GitHub as an alpha pre-release.
- Candidate `0.1.0a3` is under development; tag `v0.1.0a3` will only be created and pushed after release candidate verification and manual PyPI configuration.
- Manual PyPI Trusted Publisher configuration: Maintainer must configure a Pending Publisher in PyPI account settings pointing to repo `Ayushxsingh100/kernelcontract`, workflow `publish-to-pypi.yml`, and environment `pypi`.
- The package has **not** been published to PyPI or TestPyPI.
- The name remains provisional; registry availability is not trademark or legal clearance.
- No external maintainers or Jupyter users have tested it yet.
- macOS testing has not been performed in an actual macOS runner.
- Widget version compatibility is not certified; only companion-package presence is checked.
- The tool does not infer a running Jupyter server's process/interpreter automatically.
- A clean environment without Jupyter correctly cannot enumerate kernelspecs; users must run it where the `jupyter` command is available.
- The MVP does not execute notebooks, install packages, or mutate environments.
