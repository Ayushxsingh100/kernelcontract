# Build status — 0.1.0a1 alpha

## Implemented

- CLI commands: `kernelcontract doctor` and `kernelcontract notebook PATH`.
- Human-readable and versioned JSON reports.
- Stable check identifiers and `PASS` / `INFO` / `WARN` / `FAIL` statuses.
- Default non-zero exit on failures; `--strict` also fails on warnings.
- Jupyter kernelspec discovery using `jupyter kernelspec list --json`.
- Read-only validation that each kernelspec has a resolvable executable.
- Current/control interpreter probe and optional explicit `--server-python` probe.
- Safe default for probing: separate Python kernel executables are not executed without `--probe-python`.
- Python `ipykernel` check when a kernel is probed.
- Server/control-vs-kernel environment drift messages with limitations explained.
- Narrow check for presence of `jupyterlab_widgets` when the control environment contains JupyterLab and a probed kernel has `ipywidgets`.
- Notebook metadata check for missing/unavailable kernels and changed display names.
- Tests, packaging metadata, MIT license, contributor/security notes, and GitHub Actions CI.

## Validation completed in the build environment

- `python -m unittest discover -s tests -v`: **52 tests passed** (including discovery, diagnostics, edge cases, malformed JSON, and CLI suites).
- `python -m compileall -q src tests`: successful.
- `kernelcontract --version`: successful.
- `kernelcontract doctor` & `kernelcontract notebook <sample .ipynb> --json`: verified against fixture notebooks and clean test reports.
- Wheel built successfully (`pip wheel . --no-deps -w dist`) and installed into a clean virtual environment (`.venv_test`).
- Installed CLI `kernelcontract --help`, `doctor`, and `notebook` verified inside the isolated virtual environment.
- Windows execution verified: PATHEXT resolution without `.exe`, quoted executable paths, console output encoding safety, and subprocess decode safety.

## Not yet done

- No public GitHub repository has been created.
- The package has **not** been published to PyPI.
- The name remains provisional; registry availability is not trademark or legal clearance.
- No external maintainers or Jupyter users have tested it yet.
- macOS testing has not been performed in an actual macOS runner.
- Widget version compatibility is not certified; only companion-package presence is checked.
- The tool does not infer a running Jupyter server's process/interpreter automatically.
- A clean environment without Jupyter correctly cannot enumerate kernelspecs; users must run it where the `jupyter` command is available.
- The MVP does not execute notebooks, install packages, or mutate environments.
