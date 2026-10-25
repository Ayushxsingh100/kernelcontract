# Changelog

## 0.1.0a4 — unreleased

- Synchronized project documentation and release metadata with PyPI.
- Updated README to a modern open-source developer-tool landing page featuring genuine badges, concrete problem scenarios, terminal demonstrations, and a two-column capability summary table.
- Clarified local execution guarantees, zero-telemetry policy, and security boundaries for `--probe-python`.
- Verified and documented primary PyPI installation with `--pre` flag and alternative Git installation.
- Release candidate strictly updates documentation and packaging metadata; no software behavior or runtime changes are introduced.

## 0.1.0a3 — 2026-10-25

- Prepared PyPI Trusted Publishing GitHub Actions workflow (`.github/workflows/publish-to-pypi.yml`) using OIDC authentication, release triggers, and environment protection.
- Resolved repository URL placeholders in documentation and established verified Git-based installation instructions.
- Added package distribution build and validation with `python -m build` and `python -m twine check --strict`.
- Documented required PyPI Pending Publisher and GitHub Environment manual configurations.

## 0.1.0a2 — 2026-10-25

- Hardened cross-platform executable resolution: normalized path separators and added explicit Windows `PATHEXT` (`.COM`, `.EXE`, `.BAT`, `.CMD`) extension checking for kernelspec argv commands, ensuring reliable discovery on Windows across Python 3.10 through 3.13.
- Improved symlink tolerance in test assertions to ensure canonical interpreter resolution passes reliably on Linux/Ubuntu distributions.
- Modernized GitHub Actions CI workflows to `actions/checkout@v7` and `actions/setup-python@v7` targeting native Node.js 24 runner support.
- Hardened kernelspec discovery against malformed JSON root types (e.g. empty arrays, null, primitive types, missing or non-dict 'kernelspecs' fields) to produce structured errors instead of unhandled exceptions.

## 0.1.0a1 — 2026-10-25

- Initial read-only Jupyter kernelspec and Python interpreter diagnostics.
- JSON output and strict exit mode for CI integration.
- Notebook metadata check for unavailable or renamed kernels.
- Hardened kernelspec executable resolution on Windows: support paths without explicit `.exe` via PATHEXT and handle quoted executable paths with spaces.
- Added validation for missing kernelspec resource directories, missing `kernel.json` files, and malformed kernelspec JSON.
- Fixed unhandled exception (`TypeError: unhashable type: 'list'`) when inspecting notebooks with malformed kernelspec metadata.
- Made console output encoding-safe on Windows by using standard ASCII hyphen instead of unicode em-dash.
- Protected subprocess outputs from `UnicodeDecodeError` on non-UTF-8 console code pages using `encoding="utf-8", errors="replace"`.
- Improved Python probe robustness with a unique sentinel marker to isolate JSON from noisy interpreter banners and logs.
- Added automatic test environment bootstrap for standard unittest discovery without requiring manual `PYTHONPATH`.
- Expanded automated unit test suite from 16 to 52 tests covering all diagnostic, discovery, CLI, and edge cases.
